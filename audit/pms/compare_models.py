"""Compare composite scores (v1: Nifty 500 for all; v2: style index) on the walk-forward panel."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "audit/pms"))
import walkforward as W

df = pd.read_csv(ROOT / "data/pms/apmi_monthly.csv")
df = df[(df.type == "Equity") & (df.service == "D")]
R = df.pivot_table(index="iaid", columns="month", values="r1m", aggfunc="first")
A = df.pivot_table(index="iaid", columns="month", values="aum", aggfunc="first")
T = W.tri_monthly()
months = [m for m in R.columns if m >= "2023-04" and m in T.index]
rows = []
for k in range(24, len(months) - 6):
    tm, look, fwd = months[k - 1], months[k - 24:k], months[k:k + 12]
    for i in R.index:
        av = A.at[i, tm] if (i in A.index and tm in A.columns) else np.nan
        if pd.isna(av) or av < 100:
            continue
        r = R.loc[i, look].values.astype(float)
        if np.isnan(r).any():
            continue
        s2 = W.signals(r, T.loc[look])
        if s2["beta"] < 0.5:
            continue
        s1 = W.signals(r, T.loc[look, ["NIFTY 500"]])
        fr = R.loc[i, fwd].values.astype(float); ok = ~np.isnan(fr)
        if ok.sum() < 6:
            continue
        n = ok.sum()
        fb = T.loc[fwd, s2["style"]].values[ok]; f5 = T.loc[fwd, "NIFTY 500"].values[ok]
        g = np.cumprod(1 + fr[ok] / 100)
        row = {"T": tm, "iaid": i, "style": s2["style"], "fwd_ex": (W.chain(fr[ok]) ** (12 / n) - W.chain(fb) ** (12 / n)) * 100,
               "fwd_ex500": (W.chain(fr[ok]) ** (12 / n) - W.chain(f5) ** (12 / n)) * 100, "fwd_dd": (g / np.maximum.accumulate(g) - 1).min() * 100}
        row.update({"v1_" + a: b for a, b in s1.items()}); row.update({"v2_" + a: b for a, b in s2.items()})
        rows.append(row)
P = pd.DataFrame(rows)
def pct(g, c, neg=False):
    x = g[c].rank(pct=True)
    return 1 - x if neg else x
MODELS = {
 "v1 (Nifty 500, current)": {"v1_ex_ann": 20, "v1_ir": 20, "v1_hit_12m": 15, "v1_down_capture": -15, "v1_max_dd": 10, "v1_worst_12m_ex": 10, "v1_hit_m": 10},
 "v1 weights, style index": {"v2_ex_ann": 20, "v2_ir": 20, "v2_hit_12m": 15, "v2_down_capture": -15, "v2_max_dd": 10, "v2_worst_12m_ex": 10, "v2_hit_m": 10},
 "v2 skill 60 / risk 40": {"v2_alpha": 15, "v2_ir": 15, "v2_hit_m": 10, "v2_hit_12m": 10, "v2_half_min": 10,
                            "v2_down_capture": -10, "v2_vol": -10, "v2_rel_dd": 10, "v2_sortino": 10},
 "v2 skill 70 / risk 30": {"v2_alpha": 20, "v2_ir": 15, "v2_hit_m": 15, "v2_hit_12m": 10, "v2_half_min": 10,
                            "v2_down_capture": -10, "v2_vol": -10, "v2_rel_dd": 10},
 "1-year return only": {"v1_ret_1y": 1},
}
out = []
for name, Wt in MODELS.items():
    sc = []
    for t, g in P.groupby("T"):
        s = sum(abs(w) * pct(g, c, w < 0) for c, w in Wt.items()) / sum(abs(w) for w in Wt.values())
        sc.append(pd.DataFrame({"T": t, "s": s, "fwd_ex": g.fwd_ex, "fwd_ex500": g.fwd_ex500, "fwd_dd": g.fwd_dd}))
    S = pd.concat(sc)
    ic = S.groupby("T").apply(lambda g: g[["s", "fwd_ex"]].corr("spearman").iloc[0, 1]).mean()
    ic5 = S.groupby("T").apply(lambda g: g[["s", "fwd_ex500"]].corr("spearman").iloc[0, 1]).mean()
    icd = S.groupby("T").apply(lambda g: g[["s", "fwd_dd"]].corr("spearman").iloc[0, 1]).mean()
    # top 30% vs rest: share beating their style index next 12 months, median forward excess
    S["top"] = S.groupby("T").s.rank(pct=True) >= 0.7
    S["bot"] = S.groupby("T").s.rank(pct=True) <= 0.3
    out.append((name, ic, ic5, icd, (S[S.top].fwd_ex > 0).mean(), S[S.top].fwd_ex.median(), S[S.bot].fwd_ex.median(), S[S.top].fwd_dd.median(), S[S.bot].fwd_dd.median()))
O = pd.DataFrame(out, columns=["model", "IC fwd excess (style)", "IC fwd excess (N500)", "IC fwd worst fall", "top30 beat share", "top30 med excess", "bottom30 med excess", "top30 med fall", "bottom30 med fall"])
pd.set_option("display.width", 250)
print(len(P), "observations,", P["T"].nunique(), "formations")
print(O.round(3).to_string(index=False))

# ---- rating stability: how many strategies change tier per review, monthly vs quarterly, with and without a buffer
Wt = MODELS["v2 skill 70 / risk 30"]
sc = []
for t, g in P.groupby("T"):
    s = sum(abs(w) * pct(g, c, w < 0) for c, w in Wt.items()) / sum(abs(w) for w in Wt.values())
    sc.append(pd.DataFrame({"T": t, "iaid": g.iaid, "p": s.rank(pct=True)}))
S = pd.concat(sc)
def tier(p, prev=None, buf=0.0):
    raw = "A+" if p >= .9 else "A" if p >= .7 else "C" if p <= .3 else "B"
    if prev is None or buf == 0:
        return raw
    order = ["C", "B", "A", "A+"]
    lo = {"A+": .9 - buf, "A": .7 - buf, "B": .3 - buf, "C": -1}[prev]     # keep the tier unless clearly below it
    hi = {"A+": 2, "A": .9 + buf, "B": .7 + buf, "C": .3 + buf}[prev]      # move up only when clearly above it
    if lo <= p < hi:
        return prev
    return raw
for step, buf in ((1, 0), (3, 0), (3, .05), (3, .08)):
    Ts = sorted(S["T"].unique())[::step]
    prev, ch = {}, []
    for t in Ts:
        g = S[S["T"] == t]
        cur = {i: tier(p, prev.get(i), buf) for i, p in zip(g.iaid, g.p)}
        common = [i for i in cur if i in prev]
        if common:
            ch.append(np.mean([cur[i] != prev[i] for i in common]))
        prev = cur
    print(f"review every {step} month(s), buffer {buf:.0%}: {np.mean(ch):.0%} of strategies change tier per review; per year {np.mean(ch) * 12 / step:.0%}")
