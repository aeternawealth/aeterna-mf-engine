"""Backtest: should a fund-house signal cap a fund's rating at B? (Nov 2026, owner's question.)

At each year-end 2010-2024, among active diversified equity schemes (Regular plan) with 3+ years of history, take the
ones in the top 30% of their category on trailing 3-year return (a stand-in for "rated A or A+"). Split them by what the
proposed cap would have hit, and compare what happened next (percentile within category, forward 1 and 3 years).
Triggers tested:
  herd40   the house's herding >= 0.40 (mean pairwise correlation of its schemes' weekly returns over the category
           median, prior 52 weeks; >= 4 schemes)
  herdQ    the house in the top quarter of herding that year
  hot3     the house ranked top 3 on its schemes' mean 3-year percentile (the 'hot house')
  hot3h    hot3 and herd40 together
Limits: today's categories; merged/closed schemes missing; the 'top 30% on 3-year return' proxy is not the live model.
Run: python audit/bt_amc_cap.py -> audit/bt_amc_cap.csv (one row per fund and year) and a printed summary."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATS = {"Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value / Contra", "Dividend Yield"}
funds = [f for f in json.loads((ROOT / "site/data/funds.json").read_text()) if f["plan_type"] == "Regular" and f["category"] in CATS]
meta = {f["code"]: (f["amc"].replace(" Mutual Fund", ""), f["category"]) for f in funds}
nav = {}
for c in meta:
    p = ROOT / "data/nav" / f"{c}.csv"
    if p.exists():
        s = pd.read_csv(p, parse_dates=["date"]).set_index("date").nav
        nav[c] = s[~s.index.duplicated()]
N = pd.DataFrame(nav).sort_index().ffill(limit=5)
W = N.resample("W-FRI").last().pct_change(fill_method=None)
CAT = pd.Series({c: meta[c][1] for c in N.columns})
W = W - W.T.groupby(CAT).transform("median").T          # weekly return over the category median


def at(d):
    return N[N.index <= d].iloc[-1]


def cagr(d0, d1):
    return (at(d1) / at(d0)) ** (365.25 / (d1 - d0).days) - 1


def pct(r):
    df = pd.DataFrame({"r": r, "cat": CAT.reindex(r.index)}).dropna()
    return df.groupby("cat").r.transform(lambda x: x.rank(pct=True) * 100 if len(x) >= 5 else np.nan)


last = N.index.max()
rows = []
for y in range(2010, 2025):
    d = pd.Timestamp(f"{y}-12-31")
    past = pct(cagr(d - pd.DateOffset(years=3), d))
    f1 = pct(cagr(d, d + pd.DateOffset(years=1))) if d + pd.DateOffset(years=1) <= last else pd.Series(dtype=float)
    f3 = pct(cagr(d, d + pd.DateOffset(years=3))) if d + pd.DateOffset(years=3) <= last + pd.Timedelta(days=40) else pd.Series(dtype=float)
    df = pd.DataFrame({"past": past}).dropna()
    df["amc"] = [meta[c][0] for c in df.index]
    x = W[(W.index > d - pd.Timedelta(days=365)) & (W.index <= d)]
    house = {}
    for a, g in df.groupby("amc"):
        cs = [c for c in g.index if x[c].notna().sum() > 40]
        if len(g) < 4:
            continue
        h = np.nan
        if len(cs) >= 4:
            m = x[cs].corr().values
            h = float(np.nanmean(m[np.triu_indices(len(cs), 1)]))
        house[a] = (g.past.mean(), h)
    H = pd.DataFrame(house, index=["score", "herd"]).T
    H["hot_rank"] = H.score.rank(ascending=False, method="min")
    q75 = H.herd.quantile(.75)
    top = df[df.past >= 70].copy()
    top = top[top.amc.isin(H.index)]
    top["year"] = y
    top["herd"] = top.amc.map(H.herd)
    top["herd40"] = top.herd >= 0.40
    top["herdQ"] = top.herd >= q75
    top["hot3"] = top.amc.map(H.hot_rank) <= 3
    top["hot3h"] = top.hot3 & top.herd40
    top["f1"] = f1.reindex(top.index)
    top["f3"] = f3.reindex(top.index)
    rows.append(top)
R = pd.concat(rows)
R.index.name = "code"
R.to_csv(ROOT / "audit/bt_amc_cap.csv")

print(f"{len(R)} fund-years in the top 30% (proxy for A/A+), {R.year.min()}-{R.year.max()}\n")
print(f"{'trigger':8} {'capped':>7} {'next 1Y pct':>12} {'others':>7} {'next 3Y pct':>12} {'others':>7} {'fell to bottom 30% in 3Y':>26}")
for k in ("herd40", "herdQ", "hot3", "hot3h"):
    a, b = R[R[k]], R[~R[k]]
    bot = lambda z: (z.f3.dropna() <= 30).mean() * 100
    print(f"{k:8} {len(a):7d} {a.f1.mean():12.1f} {b.f1.mean():7.1f} {a.f3.mean():12.1f} {b.f3.mean():7.1f} {bot(a):12.0f}% vs {bot(b):.0f}%")
print("\nBy year (next 3Y percentile, capped vs others), herd40 and hot3h:")
for y, g in R.groupby("year"):
    s = [f"{k} {g[g[k]].f3.mean():5.1f}/{g[~g[k]].f3.mean():5.1f} (n={int(g[k].sum())})" for k in ("herd40", "hot3h")]
    print(y, " | ".join(s))
