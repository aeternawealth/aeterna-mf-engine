"""Agent 4/6 - Category protocols + ranking committee.

Converts raw metrics into within-peer-group percentiles, blends them into pillar
scores and a 0-100 score, applies red-flag overrides and assigns tiers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


def _pct(s: pd.Series, higher_better: bool) -> pd.Series:
    r = s.rank(pct=True, method="average")
    n = s.notna().sum()
    if n <= 1:
        return pd.Series(np.where(s.notna(), 50.0, np.nan), index=s.index)
    # map ranks to (0,100) symmetric: best = 100*(n-0.5)/n
    r = (r * n - 0.5) / n
    return (r if higher_better else 1 - r) * 100


def score_group(g: pd.DataFrame, protocol: dict) -> pd.DataFrame:
    g = g.copy()
    pillars: dict[str, list[tuple[str, float]]] = {}
    for metric, (pillar, wt, hib) in protocol.items():
        if wt <= 0 or metric not in g.columns:
            continue
        col = f"p_{metric}"
        g[col] = _pct(pd.to_numeric(g[metric], errors="coerce"), hib)
        pillars.setdefault(pillar, []).append((col, wt))

    total_w = sum(w for v in pillars.values() for _, w in v)
    num = pd.Series(0.0, index=g.index)
    den = pd.Series(0.0, index=g.index)
    for pillar, items in pillars.items():
        pn = pd.Series(0.0, index=g.index)
        pd_ = pd.Series(0.0, index=g.index)
        for col, w in items:
            ok = g[col].notna()
            pn[ok] += g.loc[ok, col] * w
            pd_[ok] += w
        g[f"pillar_{pillar}"] = (pn / pd_).where(pd_ > 0)
        num += pn
        den += pd_
    # coverage is judged on the core (non-portfolio) weights: holdings data is optional and must not unrate a fund
    core = sum(w for m, (pl, w, h) in protocol.items() if w > 0 and m in g.columns and pl != "Portfolio")
    core_den = pd.Series(0.0, index=g.index)
    for m, (pl, w, h) in protocol.items():
        if w > 0 and m in g.columns and pl != "Portfolio":
            core_den += g[f"p_{m}"].notna() * w
    g["coverage"] = core_den / core if core else 0
    g["score"] = (num / den).where(g["coverage"] >= 0.5).round(1)
    return g


def red_flags(g: pd.DataFrame) -> pd.Series:
    flags = pd.Series([[] for _ in range(len(g))], index=g.index)
    def add(mask, label):
        for i in g.index[mask.fillna(False)]:
            flags[i] = flags[i] + [label]
    if {"roll3y_hit_rate", "roll3y_excess_median"} <= set(g.columns):
        # must lag the index persistently AND sit in the bottom 40% of its peers: when a whole category trails
        # the index (common in 2018-20), an absolute test alone tagged ~30% of funds and stopped discriminating
        weak_rel = g.roll3y_excess_median.rank(pct=True) <= 0.4
        chronic = (g.roll3y_hit_rate < 0.25) & (g.roll3y_excess_median < -0.02) & weak_rel
        recent_ok = g["excess_cagr_3y"] > 0 if "excess_cagr_3y" in g.columns else False
        add(chronic & ~recent_ok, "chronic_underperformer")
        add(chronic & recent_ok, "turnaround_unproven")
    if {"downside_capture_3y", "info_ratio_3y"} <= set(g.columns):
        add((g.downside_capture_3y > 110) & (g.info_ratio_3y < 0), "risk_without_reward")
    if "max_drawdown_5y" in g.columns and g.max_drawdown_5y.notna().sum() >= 5:
        p10 = g.max_drawdown_5y.quantile(0.10)
        add(g.max_drawdown_5y < p10 - 0.05, "deep_drawdown")
    if "mandate_ok" in g.columns:
        # cap only when the portfolio is off-mandate in two consecutive monthly disclosures; a single month
        # (inflows, AMFI's half-yearly re-classification, a stock migrating between size bands) is a watch flag
        prev = g["mandate_ok_prev"] if "mandate_ok_prev" in g.columns else pd.Series(np.nan, index=g.index)
        add((g.mandate_ok == 0) & (prev == 0), "mandate_breach")
        add((g.mandate_ok == 0) & (prev != 0), "mandate_watch")
    if "excess_cagr_1y" in g.columns and g["excess_cagr_1y"].notna().sum() >= 5:
        # informational only (no tier change): recent deterioration worth watching
        q20 = g["excess_cagr_1y"].quantile(0.2)
        add((g["excess_cagr_1y"] <= q20) & (g["excess_cagr_1y"] < -0.03), "recent_underperformance")
    if "excess_vs_liquid_post_tax_3y" in g.columns:
        add(g["excess_vs_liquid_post_tax_3y"] < 0, "trails_liquid_after_tax")
    if "worst_rel_day_5y" in g.columns and "category" in g.columns:
        kind = g["category"].map(lambda c: "cash" if c in C.DEBT_CASH_LIKE else "long" if c in C.DEBT_LONG else "duration")
        thr = kind.map(C.CREDIT_EVENT_DAY)
        credit = g["category"].isin(C.DEBT_CATEGORIES) & ~g["category"].isin(C.DEBT_SOVEREIGN)   # gilts carry no credit risk
        add(credit & (g["worst_rel_day_5y"] <= thr), "credit_event")
    if "active_share" in g.columns:
        thr = g["category"].map(C.CLOSET_INDEX_BY_CATEGORY).fillna(C.CLOSET_INDEX_ACTIVE_SHARE) if "category" in g else C.CLOSET_INDEX_ACTIVE_SHARE
        no_alpha = g["excess_cagr_3y"].fillna(0) <= 0 if "excess_cagr_3y" in g.columns else True
        add((g.active_share < thr) & no_alpha, "closet_indexer")
    return flags


def assign_tiers_v7(g: pd.DataFrame) -> pd.DataFrame:
    """v7 equity tiers (audit/research_final2.py): by place in the peer group. A+ = top 10%, at least 3 places where
    the group has 15 or more funds; A = up to the top 30%; C = the bottom 30%; B = the rest. The fund's 3-year
    record against its index is shown on its page but no longer caps the rating (in the test the cap lowered
    results in every category). Statistical red flags are shown as notes; a portfolio outside SEBI's limits in two
    consecutive months still caps at B, and qualitative flags (manager exit, merger) still bring 'Watch'."""
    g = g.copy()
    s = g["score"]
    n = int(s.notna().sum())
    g["peer_rank"] = s.rank(ascending=False, method="min")
    g["peer_count"] = n
    pos = s.rank(ascending=False, method="first")
    k = max(int(np.ceil(.1 * n)), C.V7_MIN_APLUS if n >= 15 else 1)
    k30 = max(k, int(np.ceil(.3 * n)))
    bottom = n - int(np.floor(.3 * n))
    tier = pd.Series("B", index=g.index)
    if C.EQUITY_MODEL == "v8":   # by score, any number of funds: A+ at 75 or more, A at 65 or more; C = the bottom 30% below that
        tier[(pos > bottom) & (s < C.V8_A)] = "C"
        tier[s >= C.V8_A] = "A"
        tier[s >= C.V8_APLUS] = "A+"
    else:
        tier[pos <= k30] = "A"
        tier[pos <= k] = "A+"
        tier[(pos > bottom) & (pos > k30)] = "C"
    g["flags"] = red_flags(g)
    breach = g["flags"].map(lambda f: "mandate_breach" in f)
    tier[breach & tier.isin(["A+", "A"])] = "B"
    g["guard_capped"] = False
    g["behind_index_3y"] = (g["excess_cagr_3y"] < 0) if "excess_cagr_3y" in g.columns else False
    tier[s.isna()] = "Unrated"
    g["tier"] = tier
    return g


def assign_tiers(g: pd.DataFrame) -> pd.DataFrame:
    g = g.copy()
    g["peer_rank"] = g["score"].rank(ascending=False, method="min")
    g["peer_count"] = g["score"].notna().sum()
    pr = g["score"].rank(pct=True)
    tier = pd.Series("C", index=g.index)
    for label, min_pct, min_score in reversed(C.TIER_CUTS):
        tier[(pr >= min_pct) & (g["score"] >= min_score)] = label
    g["flags"] = red_flags(g)
    hard = g["flags"].map(lambda f: any(x in f for x in C.HARD_FLAGS))
    soft = g["flags"].map(lambda f: any(x in f for x in ("deep_drawdown", "mandate_breach", "closet_indexer", "turnaround_unproven", "credit_event")))
    tier[soft & tier.isin(["A+", "A"])] = "B"
    arb = g["category"].eq("Arbitrage").all() if "category" in g else False
    if C.ABSOLUTE_GUARD and arb and "excess_vs_liquid_post_tax_3y" in g.columns:
        # arbitrage: the arbitrage index has no costs, so nearly every fund trails it; the real test is the
        # alternative investors weigh, the median liquid fund, after tax (config.TAX_*). A+ must beat it over
        # 3Y and 1Y; A over 3Y or 1Y.
        e3 = g["excess_vs_liquid_post_tax_3y"]
        e1 = g["excess_vs_liquid_post_tax_1y"] if "excess_vs_liquid_post_tax_1y" in g.columns else pd.Series(np.nan, index=g.index)
        both, one = (e3 > 0) & (e1.isna() | (e1 > 0)), (e3 > 0) | (e1 > 0)
        g["guard_capped"] = (tier.eq("A+") & ~both) | (tier.eq("A") & ~one)
        tier[tier.eq("A+") & ~both] = "A"
        tier[tier.eq("A") & ~one] = "B"
    elif C.ABSOLUTE_GUARD and not arb and {"excess_cagr_3y", "roll3y_excess_median"} <= set(g.columns):
        e3, rm = g["excess_cagr_3y"], g["roll3y_excess_median"]
        idx = g["category"].eq("Index Fund") if "category" in g else False
        both = idx | ((e3 > 0) & (rm.isna() | (rm > 0)))
        one = idx | (e3 > 0) | (rm > 0)
        g["guard_capped"] = (tier.eq("A+") & ~both) | (tier.eq("A") & ~one)
        tier[tier.eq("A+") & ~both] = "A"
        tier[tier.eq("A") & ~one] = "B"
    # Audit Nov-2026: an "Avoid" override was ANTI-predictive in the 2019-25 backtest (funds it tagged beat their
    # index over the next 3Y 59% of the time vs 47% for all funds - mean reversion). Persistent laggards are now
    # capped at C ("below par on track record") with the flag shown, not labelled Avoid.
    tier[hard & tier.isin(["A+", "A", "B"])] = "C"
    tier[g["score"].isna()] = "Unrated"
    g["tier"] = tier
    return g
