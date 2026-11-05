"""Agent 8 - Validation. Walk-forward test: does a high score at date T predict
better benchmark-relative returns over the following 3 years?

Caveat: uses today's scheme universe, so funds merged/closed before today are
missing (survivorship bias flatters absolute numbers; rank-correlations are less affected).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from .metrics import fund_metrics
from .protocols import score_group


def forward_excess(nav, bench, t0, years=3):
    t1 = t0 + pd.DateOffset(years=years)
    n0, n1 = nav[nav.index <= t0], nav[nav.index <= t1]
    b0, b1 = bench[bench.index <= t0], bench[bench.index <= t1]
    if n0.empty or (t1 - n1.index[-1]).days > 10:
        return np.nan
    return (n1.iloc[-1] / n0.iloc[-1]) ** (1 / years) - (b1.iloc[-1] / b0.iloc[-1]) ** (1 / years)


def run_backtest(u_peers: pd.DataFrame, navs: dict, tri: pd.DataFrame, plan="Regular",
                 start="2017-06-30", step_months=6, horizon=3, log=print):
    last = tri.index.max() - pd.DateOffset(years=horizon)
    dates = pd.date_range(start, last, freq=f"{step_months}ME")
    act = u_peers[(u_peers.category != "Index Fund") & (u_peers.plan_type == plan) & u_peers.benchmark.notna()]
    res, quint = [], []
    for t in dates:
        rows = []
        for r in act.itertuples(index=False):
            d = navs.get(r.code)
            if d is None or r.benchmark not in tri:
                continue
            nav = d.set_index("date")["nav"]
            if (t - nav.index[0]).days < 365 * C.MIN_HISTORY_YEARS_ACTIVE:
                continue
            b = tri[r.benchmark].dropna()
            m = fund_metrics(nav, b, t)
            m.update(code=r.code, peer_group=r.peer_group, category=r.category,
                     fwd=forward_excess(nav, b, t, horizon))
            rows.append(m)
        if not rows:
            continue
        df = pd.DataFrame(rows)
        parts = []
        for pg, g in df.groupby("peer_group"):
            if len(g) < 5:
                continue
            parts.append(score_group(g, C.protocol_for(g.category.iloc[0])[1]))
        if not parts:
            continue
        s = pd.concat(parts).dropna(subset=["score", "fwd"])
        ic = s.groupby("peer_group").apply(lambda g: g.score.corr(g.fwd, method="spearman")).mean()
        pillar_ic = {c: s.groupby("peer_group").apply(lambda g, c=c: g[c].corr(g.fwd, method="spearman")).mean()
                     for c in s.columns if c.startswith("pillar_")}
        s["q"] = s.groupby("peer_group").score.transform(lambda x: pd.qcut(x.rank(method="first"), 5, labels=False) + 1)
        q = s.groupby("q").fwd.mean()
        res.append({"as_of": t.date(), "funds": len(s), "rank_ic": ic,
                    "top_q_fwd_excess": q.get(5), "bottom_q_fwd_excess": q.get(1),
                    "spread": q.get(5, np.nan) - q.get(1, np.nan), **pillar_ic})
        log(f"  backtest {t.date()}: n={len(s)} IC={ic:.2f} spread={res[-1]['spread']:.2%}")
    return pd.DataFrame(res)
