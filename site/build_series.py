"""Month-end NAV and index (TRI) series for the website's real-data SIP tool, plus auto-computed insights.

Runs in the GitHub workflows after run_monthly.py, while the NAV and TRI caches (data/nav/, data/raw/tri.csv,
not committed) are on disk. Writes:
  site/data/series/<category-slug>.json  {months:[YYYY-MM...], nav:{code:[nav or null...]}, last:{code:[date, nav]}}
  site/data/series/bench.json            {months:[...], tri:{index name:[level or null...]}, last:{name:[date, level]}}
  site/data/insights.json                [{id, title, text, figure, try:{...}}]   (facts recomputed every run)
If the caches are missing (e.g. a local run without downloads), it leaves the existing files alone.
"""
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from engine import config as C  # noqa: E402

OUT = ROOT / "site" / "data"
SER = OUT / "series"
START = "2008-01"   # far enough back for 15-year SIPs; keeps files small


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def sig(v, n=6):
    if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
        return None
    return float(f"{v:.{n}g}")


def month_end(series: pd.Series, months: pd.PeriodIndex) -> list:
    s = series.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    m = s.groupby(s.index.to_period("M")).last()
    return [sig(m.get(p)) for p in months]


def sip(navs: list, start_i: int, amount=10000):
    """Monthly SIP from month index start_i at month-end NAVs, valued at the last NAV. Returns (invested, value)."""
    units = inv = 0.0
    last = None
    for v in navs[start_i:]:
        if v:
            units += amount / v
            inv += amount
            last = v
    return (inv, units * last) if last else (0.0, 0.0)


def main():
    funds = json.loads((OUT / "funds.json").read_text())
    nav_dir = C.NAV_DIR
    tri_p = C.RAW / "tri.csv"
    if not nav_dir.exists() or not any(nav_dir.glob("*.csv")) or not tri_p.exists():
        print("series: NAV/TRI caches not on disk; keeping existing series and insights")
        return 0
    tri = pd.read_csv(tri_p, index_col=0, parse_dates=True)
    end = max(pd.Timestamp(f["nav_date"]) for f in funds if f.get("nav_date"))
    months = pd.period_range(START, end.to_period("M"), freq="M")
    mlist = [str(p) for p in months]
    SER.mkdir(parents=True, exist_ok=True)

    by_cat, last = {}, {}
    for f in funds:
        p = nav_dir / f"{int(f['code'])}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p, parse_dates=["date"]).set_index("date")["nav"]
        by_cat.setdefault(f["category"], {})[str(f["code"])] = month_end(d, months)
        d = d.dropna().sort_index()
        last[str(f["code"])] = [str(d.index[-1].date()), sig(d.iloc[-1])]
    sizes = {}
    for cat, nav in by_cat.items():
        body = {"months": mlist, "nav": nav, "last": {c: last[c] for c in nav}}
        path = SER / f"{slug(cat)}.json"
        path.write_text(json.dumps(body, separators=(",", ":")))
        sizes[cat] = path.stat().st_size // 1024

    benches = sorted({f.get("benchmark") for f in funds if f.get("benchmark") in tri.columns})
    btri, blast = {}, {}
    for b in benches:
        s = tri[b].dropna()
        btri[b] = month_end(s, months)
        blast[b] = [str(s.index[-1].date()), sig(s.iloc[-1])]
    (SER / "bench.json").write_text(json.dumps({"months": mlist, "tri": btri, "last": blast}, separators=(",", ":")))

    # ---------------------------------------------------------------- insights (all recomputed each run)
    ins = []
    reg = [f for f in funds if f.get("plan_type") == "Regular"]
    # 1. SIP started at the last market peak: is it under water?
    n50 = "NIFTY 50" if "NIFTY 50" in tri.columns else benches[0]
    m50 = pd.Series(month_end(tri[n50], months), index=months, dtype="float64")
    window = m50.iloc[-36:-3]            # a peak at least 3 months back, within 3 years
    if len(window) and window.notna().any():
        pk = window.idxmax()
        pk_i = list(months).index(pk)
        below_now = m50.iloc[-1] < window.max()
        for cat in ["Large Cap", "Mid Cap", "Small Cap", "Flexi Cap"]:
            fs = [f for f in reg if f["category"] == cat and str(f["code"]) in by_cat.get(cat, {})]
            res = []
            for f in fs:
                navs = by_cat[cat][str(f["code"])]
                if navs[pk_i] is None:
                    continue
                inv, val = sip(navs[:-1] + [last[str(f["code"])][1]], pk_i)
                if inv:
                    res.append(val / inv - 1)
            if len(res) >= 8:
                under = sum(r < 0 for r in res)
                ins.append({"id": f"sip-peak-{slug(cat)}", "kind": "sip_peak", "category": cat, "start": str(pk),
                            "title": f"{cat}: SIPs started at the {pk.strftime('%b %Y')} market high",
                            "figure": f"{under} of {len(res)}",
                            "text": f"In {under} of {len(res)} {cat.lower()} funds (Regular plans), a monthly SIP started in "
                                    f"{pk.strftime('%B %Y')}, when the Nifty 50 last peaked, is now worth less than the money put in. "
                                    f"The median fund's SIP is {sorted(res)[len(res) // 2] * 100:+.1f}% on the amount invested."
                                    + (" The Nifty 50 is still below that high." if below_now else ""),
                            "try": {"tool": "sipreal", "category": cat, "start": str(pk)}})
    # 2. Category scoreboard: share of funds ahead of their index over 3 and 5 years
    rows = []
    for cat in ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS"]:
        fs = [f for f in reg if f["category"] == cat]
        e3 = [f["excess_3Y"] for f in fs if f.get("excess_3Y") is not None]
        e5 = [f["excess_5Y"] for f in fs if f.get("excess_5Y") is not None]
        if len(e3) >= 5:
            rows.append({"category": cat, "beat3": sum(x > 0 for x in e3), "n3": len(e3),
                         "beat5": sum(x > 0 for x in e5), "n5": len(e5)})
    if rows:
        worst = min(rows, key=lambda r: r["beat3"] / r["n3"])
        ins.append({"id": "scoreboard", "kind": "scoreboard", "rows": rows,
                    "title": "How many active funds beat their index?",
                    "figure": f"{sum(r['beat3'] for r in rows)} of {sum(r['n3'] for r in rows)}",
                    "text": f"Across the main equity categories, {sum(r['beat3'] for r in rows)} of {sum(r['n3'] for r in rows)} "
                            f"Regular-plan funds beat their index (TRI) over the last 3 years. The weakest category was "
                            f"{worst['category'].lower()}: {worst['beat3']} of {worst['n3']}.",
                    "try": {"tool": "ratings"}})
    # 3. What Regular vs Direct costs over a long SIP
    pairs = {}
    for f in funds:
        if f.get("ter") is not None and f.get("pair_key"):
            pairs.setdefault(f["pair_key"], {})[f["plan_type"]] = f["ter"]
    gaps = sorted(p["Regular"] - p["Direct"] for p in pairs.values() if "Regular" in p and "Direct" in p)
    if len(gaps) > 50:
        g = gaps[len(gaps) // 2] / 100
        r = 0.12
        def fv(rate):
            mr = (1 + rate) ** (1 / 12) - 1
            return sum(10000 * (1 + mr) ** k for k in range(1, 241))
        diff = fv(r) - fv(r - g)
        ins.append({"id": "direct-regular", "kind": "cost", "gap": round(g * 100, 2),
                    "title": "What the Regular plan costs over 20 years",
                    "figure": f"{g * 100:.2f}%",
                    "text": f"The typical gap between a fund's Regular and Direct expense ratio is {g * 100:.2f}% a year. "
                            f"On a ₹10,000 monthly SIP for 20 years at an assumed 12%, that is about ₹{diff / 1e5:.1f} lakh. "
                            f"Regular plans pay a distributor, like us, for our service; Direct plans don't.",
                    "try": {"tool": "sip"}})
    (OUT / "insights.json").write_text(json.dumps({"as_of": str(end.date()), "items": ins}, separators=(",", ":")))
    print("series:", len(by_cat), "categories", sizes, "| bench", len(btri), "| insights", [i["id"] for i in ins])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:   # never block the data refresh: the SIP tool and insights just stay at their last version
        import traceback
        traceback.print_exc()
        print("series: FAILED (site keeps the previous series and insights)")
        sys.exit(0)
