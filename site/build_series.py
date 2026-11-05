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
    """navs: month-end NAVs followed by today's NAV as the last element (valuation only, no instalment)."""
    units = inv = 0.0
    for v in navs[start_i:-1]:
        if v:
            units += amount / v
            inv += amount
    return (inv, units * navs[-1]) if inv and navs[-1] else (0.0, 0.0)


def xirr(flows):
    """flows: [(years_before_valuation, amount_paid)], valuation is the final value; returns yearly rate solving sum(a*(1+r)^t)=value."""
    *pays, (_, value) = flows
    lo, hi = -0.99, 2.0
    f = lambda r: sum(a * (1 + r) ** t for t, a in pays) - value
    for _ in range(100):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def lakh(x):
    return f"₹{x / 1e5:.1f} lakh" if x < 1e7 else f"₹{x / 1e7:.2f} crore"


def make_insights(funds, by_cat, last, months, m50, m50_now, end):
    """Facts for the site, recomputed every run. Each leads with what went right, and states the weak side too."""
    ins = []
    reg = [f for f in funds if f.get("plan_type") == "Regular"]
    months = list(months)
    me_dates = [p.to_timestamp(how="end").normalize() for p in months]

    def sip_results(cat, start_i):
        out = []
        for f in reg:
            if f["category"] != cat or str(f["code"]) not in by_cat.get(cat, {}) or str(f["code"]) not in last:
                continue
            navs = by_cat[cat][str(f["code"])]
            if navs[start_i] is None:
                continue
            inv, val = sip(navs + [last[str(f["code"])][1]], start_i)
            if inv:
                out.append((val / inv - 1, inv, val, f, navs))
        return sorted(out, key=lambda r: r[0])

    # 1. Long-run SIP: 10 years in the median fund of each main category
    cats = ["Flexi Cap", "Large Cap", "Mid Cap", "Small Cap"]
    if len(months) >= 121:
        si = len(months) - 120
        for cat in cats:
            res = sip_results(cat, si)
            if len(res) < 8:
                continue
            g, inv, val, f, navs = res[len(res) // 2]
            flows = [((end - me_dates[k]).days / 365.25, 10000) for k in range(si, len(months)) if navs[k]] + [(0, val)]
            r = xirr(flows)
            beat = sum(x[0] > 0 for x in res)
            ins.append({"id": f"sip-10y-{slug(cat)}", "kind": "sip_long", "category": cat, "start": str(months[si]),
                        "title": f"₹10,000 a month for 10 years in {cat.lower()} funds",
                        "figure": lakh(val),
                        "text": f"A ₹10,000 monthly SIP started in {months[si].strftime('%B %Y')} in the middle-ranked of the "
                                f"{len(res)} {cat.lower()} funds with a 10-year record (Regular plans) is worth about {lakh(val)} today, on {lakh(inv)} put in: "
                                f"about {r * 100:.0f}% a year. That decade included the 2020 crash. The weakest fund's SIP is at "
                                f"{lakh(res[0][2])} and the strongest at {lakh(res[-1][2])}.",
                        "try": {"tool": "sipreal", "category": cat, "start": str(months[si])}})

    # 1b. Patience: share of all past 3-year holding periods that ended with a gain (funds with 10+ years of weekly history)
    for cat in ["Large Cap", "Flexi Cap", "Mid Cap", "Small Cap", "ELSS"]:
        lc = cat if cat == "ELSS" else cat.lower()
        r = [f for f in reg if f["category"] == cat and f.get("hist3y_pos") is not None and (f.get("hist3y_n") or 0) >= 500]
        if len(r) < 8:
            continue
        med = lambda k: sorted(f[k] for f in r)[len(r) // 2]
        pos, gt7, worst = med("hist3y_pos"), med("hist3y_gt7"), med("hist3y_worst")
        ins.append({"id": f"held-3y-{slug(cat)}", "kind": "patience", "category": cat,
                    "title": f"Held for 3 years, {lc} funds made money {pos * 100:.0f}% of the time",
                    "figure": f"{pos * 100:.0f}%",
                    "text": f"Across {len(r)} {lc} funds with 10 or more years of history (Regular plans), the middle fund "
                            f"ended {pos * 100:.0f}% of all its 3-year holding periods with a gain, and {gt7 * 100:.0f}% with more than "
                            f"7% a year, roughly a fixed-deposit rate. That counts every weekly start date back to 2006, through the 2008 "
                            f"and 2020 crashes. Its worst 3-year stretch was {worst * 100:+.1f}% a year.",
                    "try": {"tool": "sipreal", "category": cat}})

    # 2. SIP started at the last market peak: how many are already back in profit?
    window = m50[-36:-3]            # a peak at least 3 months back, within 3 years
    vals = [v for v in window if v is not None]
    if vals:
        pk_i = len(m50) - 36 + window.index(max(vals))
        pk = months[pk_i]
        below_now = m50_now < max(vals)
        peak = []
        for cat in cats:
            res = sip_results(cat, pk_i)
            if len(res) >= 8:
                peak.append((sum(x[0] > 0 for x in res) / len(res), cat, res))
        for share, cat, res in sorted(peak, key=lambda x: -x[0]):
            up, n, med = sum(x[0] > 0 for x in res), len(res), res[len(res) // 2][0]
            when = f"{pk.strftime('%B %Y')}, when the Nifty 50 last peaked"
            if up * 2 >= n:
                title = f"{cat}: SIPs started at the {pk.strftime('%b %Y')} high are back in profit"
                text = (f"In {up} of {n} {cat.lower()} funds (Regular plans), a monthly SIP started in {when}, is already worth "
                        f"more than the money put in" + (", although the Nifty 50 itself is still below that high" if below_now else "")
                        + f". The median SIP is {med * 100:+.1f}%. Instalments made while prices were lower bought more units, "
                        f"which is how an SIP recovers before the market does.")
            else:
                title = f"{cat}: SIPs started at the {pk.strftime('%b %Y')} high"
                text = (f"In {up} of {n} {cat.lower()} funds (Regular plans), a monthly SIP started in {when}, is worth more than "
                        f"the money put in; the median is {med * 100:+.1f}%. Every instalment since then has bought units below the "
                        f"peak price, which is what lifts an SIP when markets recover.")
            ins.append({"id": f"sip-peak-{slug(cat)}", "kind": "sip_peak", "category": cat, "start": str(pk),
                        "title": title, "figure": f"{up} of {n}", "text": text,
                        "try": {"tool": "sipreal", "category": cat, "start": str(pk)}})

    # 4. Category scoreboard: where active funds beat their index
    rows = []
    for cat in ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS"]:
        fs = [f for f in reg if f["category"] == cat]
        e3 = [f["excess_3Y"] for f in fs if f.get("excess_3Y") is not None]
        e5 = [f["excess_5Y"] for f in fs if f.get("excess_5Y") is not None]
        if len(e3) >= 5:
            rows.append({"category": cat, "beat3": sum(x > 0 for x in e3), "n3": len(e3),
                         "beat5": sum(x > 0 for x in e5), "n5": len(e5)})
    big = [r for r in rows if r["n3"] >= 15] or rows
    if big:
        top = max(big, key=lambda r: r["beat3"] / r["n3"])
        low = min(big, key=lambda r: r["beat3"] / r["n3"])
        ins.append({"id": "scoreboard", "kind": "scoreboard", "rows": rows,
                    "title": "Where active funds beat their index",
                    "figure": f"{top['beat3']} of {top['n3']}",
                    "text": f"Over the last 3 years, {top['beat3']} of {top['n3']} {top['category'].lower()} funds (Regular plans) beat "
                            f"their index (TRI), the highest share among the main categories. It varies a lot: in "
                            f"{low['category'].lower()} it was {low['beat3']} of {low['n3']}, so which fund you hold matters "
                            f"as much as which category.",
                    "try": {"tool": "ratings"}})
    return ins


def insights_from_site():
    """Recompute insights.json from the published series files (no NAV cache needed)."""
    funds = json.loads((OUT / "funds.json").read_text())
    by_cat = {}
    for f in funds:
        p = SER / f"{slug(f['category'])}.json"
        if f["category"] not in by_cat and p.exists():
            by_cat[f["category"]] = json.loads(p.read_text())["nav"]
    b = json.loads((SER / "bench.json").read_text())
    L = json.loads((SER / "last.json").read_text())
    months = pd.PeriodIndex(b["months"], freq="M")
    end = pd.Timestamp(L["as_of"])
    ins = make_insights(funds, by_cat, L["nav"], months, b["tri"]["NIFTY 50"], L["tri"]["NIFTY 50"][1], end)
    (OUT / "insights.json").write_text(json.dumps({"as_of": str(end.date()), "items": ins}, separators=(",", ":")))
    return ins


def main():
    funds = json.loads((OUT / "funds.json").read_text())
    nav_dir = C.NAV_DIR
    tri_p = C.RAW / "tri.csv"
    if not nav_dir.exists() or not any(nav_dir.glob("*.csv")) or not tri_p.exists():
        print("series: NAV/TRI caches not on disk; keeping existing series and insights")
        return 0
    tri = pd.read_csv(tri_p, index_col=0, parse_dates=True)
    end = max(pd.Timestamp(f["nav_date"]) for f in funds if f.get("nav_date"))
    # completed months only: these files change once a month; today's NAVs live in last.json (tiny, daily)
    months = pd.period_range(START, end.to_period("M") - 1, freq="M")
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
        body = {"months": mlist, "nav": nav}
        path = SER / f"{slug(cat)}.json"
        path.write_text(json.dumps(body, separators=(",", ":")))
        sizes[cat] = path.stat().st_size // 1024

    benches = sorted({f.get("benchmark") for f in funds if f.get("benchmark") in tri.columns})
    btri, blast = {}, {}
    for b in benches:
        s = tri[b].dropna()
        btri[b] = month_end(s, months)
        blast[b] = [str(s.index[-1].date()), sig(s.iloc[-1])]
    (SER / "bench.json").write_text(json.dumps({"months": mlist, "tri": btri}, separators=(",", ":")))
    (SER / "last.json").write_text(json.dumps({"as_of": str(end.date()), "nav": last, "tri": blast}, separators=(",", ":")))

    # ---------------------------------------------------------------- insights (all recomputed each run)
    n50 = "NIFTY 50" if "NIFTY 50" in btri else benches[0]
    ins = make_insights(funds, by_cat, last, months, btri[n50], blast[n50][1], end)
    (OUT / "insights.json").write_text(json.dumps({"as_of": str(end.date()), "items": ins}, separators=(",", ":")))
    print("series:", len(by_cat), "categories", sizes, "| bench", len(btri), "| insights", [i["id"] for i in ins])
    return 0


if __name__ == "__main__":
    if "--insights-only" in sys.argv:   # from the committed site/data/series files
        print([i["id"] for i in insights_from_site()])
        sys.exit(0)
    try:
        sys.exit(main())
    except Exception:   # never block the data refresh: the SIP tool and insights just stay at their last version
        import traceback
        traceback.print_exc()
        print("series: FAILED (site keeps the previous series and insights)")
        sys.exit(0)
