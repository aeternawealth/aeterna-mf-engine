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


def face_value_clean(nav: pd.Series) -> pd.Series:
    """Debt NAVs: a one-day move of -40% or +60% is a face-value change (e.g. UTI Liquid, Rs 4,700 to Rs 470 units),
    not a return. Same rule as engine.metrics.debt_clean, but scaled to today's NAV so the chart ends at the real
    current price and the history is restated in today's units."""
    s = nav.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    r = s.pct_change()
    bad = (r <= -0.4) | (r >= 0.6)
    if not bad.any():
        return s
    r[bad] = 0.0
    c = (1 + r.fillna(0)).cumprod()
    return s.iloc[-1] * c / c.iloc[-1]


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


FINE = OUT / "nav"   # daily and weekly points for the fund-page charts


def _pack(s: pd.Series, base: pd.Timestamp) -> dict:
    """{s: first date, d: day gaps, v: values}: dates as gaps in days keep the files small"""
    days = ((s.index - base).days).tolist()
    return {"s": str(base.date()), "d": [days[0]] + [b - a for a, b in zip(days, days[1:])], "v": [sig(v) for v in s.tolist()]}


def _fine(s: pd.Series, me: pd.Timestamp) -> pd.Series:
    """up to the last month end: weekly points for 3 years, daily for the last 13 months"""
    s = s[s.index <= me].dropna()
    cut = me - pd.DateOffset(months=13)
    wk = s[(s.index > me - pd.DateOffset(years=3)) & (s.index <= cut)].resample("W-FRI").last().dropna()
    return pd.concat([wk, s[s.index > cut]]).sort_index()


def fine_navs(funds, nav_dir, tri, end):
    """site/data/nav/<code>.json (to the last month end; rewritten once a month, so the repository grows little) and
    site/data/nav/recent-<category>.json + recent-bench.json (the days since; small, daily). bench.json for the indices."""
    FINE.mkdir(parents=True, exist_ok=True)
    me = (end.to_period("M") - 1).to_timestamp(how="end").normalize()
    stamp, recent, n = str(me.date()), {}, 0
    for f in funds:
        p = nav_dir / f"{int(f['code'])}.csv"
        if not p.exists():
            continue
        d = pd.read_csv(p, parse_dates=["date"]).set_index("date")["nav"].sort_index()
        d = d[~d.index.duplicated(keep="last")]
        if f.get("asset_class") == "Debt":
            d = face_value_clean(d)
        out = FINE / f"{int(f['code'])}.json"
        h = _fine(d, me)
        if len(h) >= 5:
            old = json.loads(out.read_text()) if out.exists() else {}
            if old.get("u") != stamp:
                out.write_text(json.dumps({"u": stamp, **_pack(h, h.index[0])}, separators=(",", ":")))
                n += 1
        r = d[d.index > me].dropna()
        if len(r):
            recent.setdefault(slug(f["category"]), {})[str(f["code"])] = _pack(r, me)
    for cat, body in recent.items():
        (FINE / f"recent-{cat}.json").write_text(json.dumps({"u": stamp, "nav": body}, separators=(",", ":")))
    benches = sorted({f.get("benchmark") for f in funds if f.get("benchmark") in tri.columns})
    bh, br = {}, {}
    for b in benches:
        s = tri[b].dropna().sort_index()
        h = _fine(s, me)
        if len(h) >= 5:
            bh[b] = _pack(h, h.index[0])
        r = s[s.index > me]
        if len(r):
            br[b] = _pack(r, me)
    bp = FINE / "bench.json"
    if (json.loads(bp.read_text()).get("u") if bp.exists() else None) != stamp:
        bp.write_text(json.dumps({"u": stamp, "tri": bh}, separators=(",", ":")))
    (FINE / "recent-bench.json").write_text(json.dumps({"u": stamp, "tri": br}, separators=(",", ":")))
    print(f"fine NAVs: {n} fund files rewritten (to {stamp}), {len(recent)} recent files")


WATCH_CATS = {"Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value / Contra", "Dividend Yield"}


def amc_watch(funds, nav_dir):
    """Fund-house watch (display only; not a rating input): how far one house view drives all of a house's schemes.
    herding = mean pairwise correlation of its diversified schemes' weekly returns over the median such scheme, last
    52 weeks (audit/amc_cycles.py: Quant 0.6-0.65 in 2024-26, median house about 0.15); overlap = median share of
    portfolio two of its schemes hold in common; aum_growth = 12-month change in its equity AUM."""
    import numpy as np
    F = [f for f in funds if f["plan_type"] == "Regular" and f.get("category") in WATCH_CATS and (f.get("age_years") or 0) >= 1]
    W = {}
    for f in F:
        p = nav_dir / f"{int(f['code'])}.csv"
        if p.exists():
            d = pd.read_csv(p, parse_dates=["date"]).set_index("date")["nav"]
            W[f["code"]] = d[~d.index.duplicated()].resample("W-FRI").last().pct_change(fill_method=None)
    if not W:
        return
    R = pd.DataFrame(W)
    R = R[R.index > R.index.max() - pd.Timedelta(days=365)]
    R = R.sub(R.median(axis=1), axis=0)
    hold = json.loads((OUT / "holdings.json").read_text()) if (OUT / "holdings.json").exists() else {}
    by = {}
    for f in F:
        by.setdefault(f["amc"], []).append(f)
    out = {}
    for a, L in by.items():
        cs = [f["code"] for f in L if f["code"] in R.columns and R[f["code"]].notna().sum() > 40]
        if len(cs) < 4:
            continue
        m = R[cs].corr().values
        herd = float(np.nanmean(m[np.triu_indices(len(cs), 1)]))
        ws = [{x[0]: x[2] for x in hold[f["pair_key"]] if isinstance(x[2], (int, float))} for f in L if hold.get(f.get("pair_key"))]
        ovs = [sum(min(ws[i][k], ws[j][k]) for k in ws[i] if k in ws[j]) for i in range(len(ws)) for j in range(i + 1, len(ws))]
        now = sum(f.get("aum_cr") or 0 for f in L if f.get("aum_1y_ago_cr"))
        ago = sum(f.get("aum_1y_ago_cr") or 0 for f in L if f.get("aum_1y_ago_cr"))
        out[a] = {"herding": round(herd, 2), "schemes": len(cs), "overlap": round(float(np.median(ovs)), 1) if len(ovs) >= 3 else None,
                  "aum_growth": round(now / ago - 1, 3) if ago else None}
    if out:
        med = float(np.median([v["herding"] for v in out.values()]))
        rank = sorted(out, key=lambda a: -out[a]["herding"])
        for i, a in enumerate(rank):
            out[a]["rank"], out[a]["of"] = i + 1, len(rank)
        (OUT / "amc_watch.json").write_text(json.dumps({"median_herding": round(med, 2), "houses": out}, separators=(",", ":")))
        print("amc watch:", len(out), "houses; most herded", rank[:3])


def mcap_json():
    """site/data/mcap.json {isin: [AMFI rank, 6-month average market cap in ₹ cr, 'large'/'mid'/'small', company name]} for
    the stocks funds hold now or held in any saved month (so stocks funds sold out of keep a name), from
    data/manual/amfi_mcap.xlsx (AMFI's half-yearly list), so the site build (no pandas) can use it."""
    p = ROOT / "data" / "manual" / "amfi_mcap.xlsx"
    hp = OUT / "holdings.json"
    if not p.exists() or not hp.exists():
        return
    held = {r[0] for rows in json.loads(hp.read_text()).values() for r in rows if r and r[0]}
    for wp in (ROOT / "data" / "holdings").glob("*/_weights.csv"):
        held |= set(pd.read_csv(wp, usecols=["isin"])["isin"].astype(str).str.upper())
    raw = pd.read_excel(p, header=None)
    h = next(i for i in range(30) if any("isin" in str(v).lower() for v in raw.iloc[i]))
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c).strip().lower() for c in raw.iloc[h]]
    icol = next(c for c in df.columns if "isin" in c)
    mcol = next(c for c in df.columns if "average of all" in c)
    rcol = next(c for c in df.columns if c.startswith("sr"))
    ccol = next(c for c in df.columns if "categor" in c)
    ncol = next((c for c in df.columns if "name" in c), None)
    names = df[ncol].astype(str).str.strip() if ncol else [""] * len(df)
    out = {}
    for isin, rk, mc, cat, nm in zip(df[icol].astype(str).str.strip().str.upper(), df[rcol], df[mcol], df[ccol].astype(str).str.lower(), names):
        if isin in held and pd.notna(mc):
            out[isin] = [int(rk), round(float(mc)), next((k for k in ("large", "mid", "small") if k in cat), "small"), nm]
    period = (ROOT / "data" / "manual" / "amfi_mcap.period.txt")
    body = json.dumps({"period": period.read_text().strip() if period.exists() else "", "s": out}, separators=(",", ":"))
    mp = OUT / "mcap.json"
    if not mp.exists() or mp.read_text() != body:
        mp.write_text(body)


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
        if f.get("asset_class") == "Debt":
            d = face_value_clean(d)
        by_cat.setdefault(f["category"], {})[str(f["code"])] = month_end(d, months)
        d = d.dropna().sort_index()
        last[str(f["code"])] = [str(d.index[-1].date()), sig(d.iloc[-1])]
    fine_navs(funds, nav_dir, tri, end)
    amc_watch(funds, nav_dir)
    mcap_json()
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
