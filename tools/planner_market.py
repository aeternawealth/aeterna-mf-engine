"""Monthly return history for the allocation planner's simulator (site/planner/market.json).

Real Indian market months, from mfapi.in NAV histories of long-running schemes (Growth option):
  equity : 70% UTI Nifty 50 Index Fund + 30% HDFC Mid Cap Fund (a diversified-equity proxy), from Apr 2007
  debt   : ICICI Prudential Short Term Fund
  liquid : HDFC Liquid Fund
  gold   : Nippon India Gold Savings Fund (from 2011); months before it are drawn from its own history
Scheme NAVs are after costs, so the returns are what investors actually got (Regular plans).
Run: python tools/planner_market.py
"""
import json
from pathlib import Path

import httpx
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "planner" / "market.json"
CODES = {"n50": 100822, "mid": 105758, "debt": 101758, "liquid": 100868, "gold": None}


def nav(code):
    j = httpx.get(f"https://api.mfapi.in/mf/{code}", timeout=60).json()
    d = pd.DataFrame(j["data"])
    d["date"] = pd.to_datetime(d["date"], format="%d-%m-%Y")
    d["nav"] = pd.to_numeric(d["nav"], errors="coerce")
    return j["meta"]["scheme_name"], d.dropna().set_index("date")["nav"].sort_index()


def glide_table(m, n=4000, block=12, seed=7):
    """P(ending below the amount invested) for a lump sum held y years in a mix of e equity, gold g (5% from 5 years)
    and the rest debt, from a block bootstrap of real months (12-month blocks keep crashes and recoveries intact).
    Returns {"eq": [0..90 step 5], "y": [1..30], "ploss": [[...]], "p10": [[...]] (10th-percentile CAGR)}."""
    import numpy as np
    rng = np.random.default_rng(seed)
    eq_r, de_r = m["equity"].to_numpy(), m["debt"].to_numpy()
    gold = m["gold"].dropna().to_numpy()
    gold_r = np.where(m["gold"].isna(), np.nan, m["gold"]).astype(float)
    T = len(eq_r)
    E = list(range(0, 95, 5)); Y = list(range(1, 31))
    starts = rng.integers(0, T - block, size=(n, 30 * 12 // block + 1))
    idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(n, -1)[:, :360]
    eqp, dep = eq_r[idx], de_r[idx]
    gp = gold_r[idx]; miss = np.isnan(gp); gp[miss] = rng.choice(gold, size=miss.sum())
    ploss, p10 = [], []
    for y in Y:
        mths = y * 12; g = 0.05 if y >= 5 else 0.0
        row_l, row_p = [], []
        for e in E:
            w = e / 100; wg = min(g, 1 - w); wd = 1 - w - wg
            port = w * eqp[:, :mths] + wg * gp[:, :mths] + wd * dep[:, :mths]
            end = np.prod(1 + port, axis=1)
            row_l.append(round(float((end < 1).mean()), 4))
            row_p.append(round(float(np.quantile(end, 0.10) ** (1 / y) - 1), 4))
        ploss.append(row_l); p10.append(row_p)
    return {"eq": E, "y": Y, "ploss": ploss, "p10": p10, "n": n, "block": block}


def main():
    navall = (ROOT / "data" / "raw" / "NAVAll.txt").read_text(encoding="utf-8")
    CODES["gold"] = 114616
    series, names = {}, {}
    for k, c in CODES.items():
        names[k], s = nav(c)
        series[k] = s.resample("ME").last()
    m = pd.DataFrame(series).pct_change()
    m["equity"] = 0.7 * m["n50"] + 0.3 * m["mid"]
    # NAV breaks (face-value changes, unit splits) show as impossible one-month moves in debt-like series: drop them
    for k, lim in (("liquid", 0.03), ("debt", 0.06)):
        bad = m[k].abs() > lim
        if bad.any():
            print(f"  {k}: dropped {int(bad.sum())} NAV-break month(s): {list(m.index[bad].strftime('%Y-%m'))}")
            m.loc[bad, k] = m.loc[~bad, k].median()
    m = m[["equity", "debt", "liquid", "gold"]].dropna(subset=["equity", "debt", "liquid"])
    m = m[m.index < pd.Timestamp.today().normalize().replace(day=1)]   # complete months only
    ann = lambda s: (1 + s).prod() ** (12 / len(s)) - 1
    stats = {k: {"cagr": round(ann(m[k].dropna()), 4), "vol": round(m[k].std() * 12 ** 0.5, 4), "from": m[k].dropna().index[0].strftime("%Y-%m"),
                 "worst_12m": round(((1 + m[k].dropna()).rolling(12).apply(lambda x: x.prod()) - 1).min(), 4)} for k in m}
    glide = glide_table(m)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"from": m.index[0].strftime("%Y-%m"), "to": m.index[-1].strftime("%Y-%m"), "sources": names,
                               "stats": stats, "glide": glide, "corr": m.corr().round(3).to_dict(),
                               "months": [m.index.strftime("%Y-%m").tolist()] + [[None if pd.isna(x) else round(x, 5) for x in m[k]] for k in ["equity", "debt", "liquid", "gold"]]},
                              separators=(",", ":")))
    print(f"{len(m)} months {m.index[0]:%Y-%m}..{m.index[-1]:%Y-%m}")
    print(json.dumps(stats, indent=1))
    print(m.corr().round(2))


if __name__ == "__main__":
    main()
