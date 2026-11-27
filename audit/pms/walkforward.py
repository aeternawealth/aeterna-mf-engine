"""PMS rating research: which track-record measures, taken at a date, lined up with the next 12 months?

    python audit/pms/walkforward.py

Universe at each formation month T: discretionary equity strategies with Rs 100 cr+ at T and 24 months of returns to T
(not today's survivors: strategies that later shrank or closed count, with whatever forward months they reported).
Forward: excess return over the strategy's style index (fitted on the 24 months to T) over the next 12 months.
Rank correlation (Spearman) of each measure with the forward excess, per formation, then averaged.
"""
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
STYLE = ["NIFTY 50", "NIFTY 500", "NIFTY500 MULTICAP 50:25:25", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"]


def tri_monthly():
    t = pd.read_csv(ROOT / "audit/live/tri_me.csv.gz", index_col=0, parse_dates=True)[STYLE]
    t.index = t.index.strftime("%Y-%m")
    return (t.pct_change(fill_method=None) * 100)


def chain(x):
    return float(np.prod(1 + np.asarray(x) / 100))


def signals(r, B):
    """r: strategy monthly % (array, n); B: DataFrame of index monthly % on the same months."""
    n = len(r)
    te = {c: np.std(r - B[c].values, ddof=1) for c in B.columns}
    sty = min(te, key=te.get)
    b = B[sty].values
    ex = r - b
    out = {"style": sty}
    out["ex_ann"] = (chain(r) ** (12 / n) - chain(b) ** (12 / n)) * 100
    out["ir"] = ex.mean() * 12 / (ex.std(ddof=1) * math.sqrt(12))
    beta = np.cov(r, b)[0, 1] / np.var(b, ddof=1)
    out["beta"] = beta
    out["alpha"] = (r.mean() - beta * b.mean()) * 12
    rf = (1.065 ** (1 / 12) - 1) * 100
    dn = np.minimum(0, r - rf)
    out["sortino"] = ((chain(r) ** (12 / n) - 1) * 100 - 6.5) / (math.sqrt((dn ** 2).mean()) * math.sqrt(12))
    d = b < 0
    out["down_capture"] = r[d].sum() / b[d].sum() if d.any() else np.nan
    u = b > 0
    out["up_capture"] = r[u].sum() / b[u].sum()
    def mdd(x):
        g = np.cumprod(1 + x / 100); return (g / np.maximum.accumulate(g) - 1).min() * 100
    out["max_dd"] = mdd(r)
    out["rel_dd"] = mdd(r) - mdd(b)
    roll = [chain(r[i - 12:i]) - chain(b[i - 12:i]) for i in range(12, n + 1)]
    out["hit_12m"] = np.mean([x > 0 for x in roll])
    out["worst_12m_ex"] = min(roll) * 100
    out["hit_m"] = (ex > 0).mean()
    h = n // 2
    out["half_min"] = min(ex[:h].mean(), ex[h:].mean()) * 12
    out["vol"] = r.std(ddof=1) * math.sqrt(12)
    out["ret_1y"] = (chain(r[-12:]) - 1) * 100
    out["ex_1y"] = (chain(r[-12:]) - chain(b[-12:])) * 100
    out["te"] = ex.std(ddof=1) * math.sqrt(12)
    return out


def main():
    df = pd.read_csv(ROOT / "data/pms/apmi_monthly.csv")
    df = df[(df.type == "Equity") & (df.service == "D")]
    R = df.pivot_table(index="iaid", columns="month", values="r1m", aggfunc="first")
    A = df.pivot_table(index="iaid", columns="month", values="aum", aggfunc="first")
    names = df.groupby("iaid").strategy.last()
    T = tri_monthly()
    months = [m for m in R.columns if m >= "2023-04" and m in T.index]
    res = []
    for k in range(24, len(months) - 6):
        tm = months[k - 1]
        look, fwd = months[k - 24:k], months[k:k + 12]
        if len(fwd) < 12 and k not in (len(months) - 12,):
            pass
        for i in R.index:
            av = A.at[i, tm] if (i in A.index and tm in A.columns) else np.nan
            if pd.isna(av) or av < 100:
                continue
            r = R.loc[i, look].values.astype(float)
            if np.isnan(r).any():
                continue
            s = signals(r, T.loc[look])
            if s["beta"] < 0.5:
                continue
            fr = R.loc[i, fwd].values.astype(float)
            ok = ~np.isnan(fr)
            if ok.sum() < 6:
                continue
            fb = T.loc[fwd, s["style"]].values[ok]
            n = ok.sum()
            s["fwd_ex"] = (chain(fr[ok]) ** (12 / n) - chain(fb) ** (12 / n)) * 100
            g = np.cumprod(1 + fr[ok] / 100)
            s["fwd_dd"] = (g / np.maximum.accumulate(g) - 1).min() * 100
            s["fwd_n"] = n
            s.update(T=tm, iaid=i, aum=A.at[i, tm])
            res.append(s)
    P = pd.DataFrame(res)
    P["log_aum"] = np.log(P.aum)
    P["ex1_x_sortino"] = 0
    sig = ["ex_ann", "ir", "alpha", "sortino", "down_capture", "up_capture", "max_dd", "rel_dd", "hit_12m", "worst_12m_ex",
           "hit_m", "half_min", "vol", "beta", "te", "ret_1y", "ex_1y", "log_aum"]
    Ts = sorted(P["T"].unique())
    print("formations:", Ts[0], "to", Ts[-1], "| strategies per formation:", int(P.groupby("T").size().median()))
    print("style split at last formation:", P[P["T"] == Ts[-1]]["style"].value_counts().to_dict())
    out = []
    for target in ("fwd_ex", "fwd_dd"):
        for sg in sig:
            ics = [P[P["T"] == t][[sg, target]].corr(method="spearman").iloc[0, 1] for t in Ts]
            q = [t for t in Ts if t[5:] in ("03", "06", "09", "12")]
            out.append((target, sg, np.nanmean(ics), np.nanmean([P[P["T"] == t][[sg, target]].corr(method="spearman").iloc[0, 1] for t in q]), np.mean([x > 0 for x in ics])))
    O = pd.DataFrame(out, columns=["target", "signal", "ic_all", "ic_quarter_ends", "share_pos"])
    pd.set_option("display.width", 200)
    print(O.round(3).to_string(index=False))
    P.to_csv(ROOT / "audit/pms/panel.csv", index=False)
    return P


if __name__ == "__main__":
    main()
