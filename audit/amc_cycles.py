"""Do fund houses that top the return tables keep it up? (Nov 2026 study, owner's question on Quant, Bandhan, Invesco.)

At each year-end 2009-2025: every active diversified equity scheme (Regular plan, the original plan before 2013) gets its
percentile within its SEBI category on trailing 3-year return. A fund house's score = the mean percentile of its schemes
(at least 4 with data). We then follow the same schemes over the next 1 and 3 years (forward percentile within category),
and measure "herding": the mean pairwise correlation of the house's weekly returns over the category median, prior year.
Limits: categories are today's (pre-2018 funds are placed by their current category); merged or closed equity schemes are
missing from the NAV cache, which flatters houses whose weak funds were merged away.
Run: python audit/amc_cycles.py  -> audit/amc_cycles.csv and a printed summary."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CATS = {"Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value / Contra", "Dividend Yield"}
MIN_SCHEMES = 4

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


def at(d):
    return N[N.index <= d].iloc[-1] if (N.index <= d).any() else None


def cagr(d0, d1):
    a, b = at(d0), at(d1)
    return (b / a) ** (365.25 / (d1 - d0).days) - 1


def pctile(r):
    df = pd.DataFrame({"r": r, "cat": [meta[c][1] for c in r.index]}).dropna()
    return df.groupby("cat").r.transform(lambda x: x.rank(pct=True) * 100 if len(x) >= 5 else np.nan)


def herding(codes, d):
    x = W[(W.index > d - pd.Timedelta(days=365)) & (W.index <= d)]
    x = x.sub(x.median(axis=1), axis=0)[[c for c in codes if c in x.columns]]
    x = x.loc[:, x.notna().sum() > 40]
    if x.shape[1] < 3:
        return np.nan
    m = x.corr().values
    return float(np.nanmean(m[np.triu_indices(x.shape[1], 1)]))


rows = []
last = N.index.max()
for y in range(2009, 2026):
    d = pd.Timestamp(f"{y}-12-31")
    past = pctile(cagr(d - pd.DateOffset(years=3), d))
    f1 = pctile(cagr(d, d + pd.DateOffset(years=1))) if d + pd.DateOffset(years=1) <= last else None
    f3 = pctile(cagr(d, d + pd.DateOffset(years=3))) if d + pd.DateOffset(years=3) <= last else None
    df = pd.DataFrame({"past": past})
    df["amc"] = [meta[c][0] for c in df.index]
    if f1 is not None:
        df["f1"] = f1
    if f3 is not None:
        df["f3"] = f3
    g = df.groupby("amc")
    t = g.past.agg(["mean", "size"]).rename(columns={"mean": "past", "size": "n"})
    t = t[t.n >= MIN_SCHEMES]
    for k in ("f1", "f3"):
        if k in df:
            t[k] = g[k].mean()
    t["rank"] = t.past.rank(ascending=False, method="min")
    herd = {a: herding(df.index[df.amc == a], d) for a in t.index}
    t["herding"] = pd.Series(herd)
    t["year"] = y
    t["houses"] = len(t)
    rows.append(t.reset_index())
R = pd.concat(rows, ignore_index=True)
# rank of the same house 3 years later on trailing return
nxt = R.set_index(["year", "amc"])["rank"]
R["rank_3y_later"] = [nxt.get((y + 3, a)) for y, a in zip(R.year, R.amc)]
R.to_csv(ROOT / "audit/amc_cycles.csv", index=False)

top = R[R["rank"] == 1].sort_values("year")
pd.set_option("display.width", 200)
print(top[["year", "amc", "n", "past", "herding", "f1", "f3", "rank_3y_later", "houses"]].round(1).to_string(index=False))
top3 = R[R["rank"] <= 3]
print("\nTop house next 1Y percentile: mean %.1f  (50 = average)  | next 3Y: mean %.1f" % (top.f1.mean(), top.f3.mean()))
print("Top 3 houses next 1Y: %.1f | next 3Y: %.1f" % (top3.f1.mean(), top3.f3.mean()))
print("All houses next 3Y: %.1f" % R.f3.mean())
pers = R.dropna(subset=["f3"]).groupby("year").apply(lambda g: g.past.corr(g.f3, method="spearman"))
print("Persistence (rank corr, past 3Y vs next 3Y, by year):", pers.round(2).to_dict(), " mean %.2f" % pers.mean())
hi = R.herding >= R.groupby("year").herding.transform(lambda x: x.quantile(.75))
print("Next 3Y percentile, high-herding houses (top quarter): %.1f vs others %.1f" % (R[hi].f3.mean(), R[~hi].f3.mean()))
print("Among top-3 houses: high herding next 3Y %.1f vs low herding %.1f" % (top3[top3.herding >= top3.herding.median()].f3.mean(), top3[top3.herding < top3.herding.median()].f3.mean()))
