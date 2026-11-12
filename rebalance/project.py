"""Goal projection by block bootstrap: each simulated year is a real 12-month stretch of history (all sleeves from the
same months, so they fall together as they did), drawn at random. Returns are the category median fund's, net of its
costs. Results are ranges from history, not forecasts."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C
from . import data as D
from .plan import Plan, glide

SLEEVES = ["large", "flexi", "midlm", "small", "thematic", "hybrid", "debt", "parked"]


def _history() -> pd.DataFrame:
    cols = {}
    for b in SLEEVES:
        rs = [D.category_returns(s) for s in C.PROJ_CATEGORIES[b]]
        cols[b] = pd.concat(rs, axis=1).mean(axis=1)
    h = pd.DataFrame(cols).dropna()
    return h


def simulate(plan: Plan, months: int, sip: float, weights_now: dict, sims: int = C.SIMS, seed: int = 7,
             start_value: float | None = None):
    """terminal values (today's rupees are not used here: inflation is applied to the target instead)"""
    hist = _history().to_numpy()
    idx = {b: i for i, b in enumerate(SLEEVES)}
    rng = np.random.default_rng(seed)
    n_hist = len(hist)
    start = start_value if start_value is not None else plan.portfolio.value + plan.client.lumpsum
    # sleeve weights now and for new money
    w0 = np.array([weights_now.get(b, 0) for b in SLEEVES], float)
    w0 = w0 / w0.sum() if w0.sum() else w0
    tgt = np.array([plan.target.get(b, 0) for b in SLEEVES], float)
    vals = np.tile(w0 * start, (sims, 1))
    blocks = int(np.ceil(months / C.BLOCK_MONTHS))
    starts = rng.integers(0, n_hist - C.BLOCK_MONTHS, size=(sims, blocks))
    eq_idx = [idx[b] for b in ("large", "flexi", "midlm", "small", "thematic")]
    non_eq = idx["parked"] if plan.target.get("parked", 0) >= plan.target.get("debt", 0) else idx["debt"]
    for m in range(months):
        bk, off = divmod(m, C.BLOCK_MONTHS)
        r = hist[starts[:, bk] + off]                      # (sims, sleeves)
        vals *= 1 + r
        vals += sip * tgt
        # glide path: once a year, move equity above the allowed share into the non-equity sleeve
        if plan.years is not None and m % 12 == 11:
            left = max(0, plan.years - (m + 1) // 12)
            cap = glide(left, plan.profile)
            tot = vals.sum(axis=1)
            eq = vals[:, eq_idx].sum(axis=1)
            excess = np.clip(eq - cap * tot, 0, None)
            frac = np.where(eq > 0, excess / np.where(eq > 0, eq, 1), 0)
            moved = vals[:, eq_idx] * frac[:, None]
            vals[:, eq_idx] -= moved
            vals[:, non_eq] += moved.sum(axis=1)
    return vals.sum(axis=1)


def project(plan: Plan) -> dict:
    c = plan.client
    years = plan.years if plan.years is not None else 15
    months = max(12, years * 12)
    infl = c.inflation if c.inflation is not None else C.INFLATION["education" if c.goal == "education" else "default"]
    target_nom = c.target_today * (1 + infl) ** years if c.target_today else None
    out = {"years": years, "inflation": infl, "target_nominal": target_nom, "fixed_horizon": plan.years is None}
    for label, w in (("current", plan.current), ("plan", plan.after)):
        v = simulate(plan, months, c.sip, w)
        out[label] = {"p10": float(np.percentile(v, 10)), "p50": float(np.percentile(v, 50)), "p90": float(np.percentile(v, 90)),
                      "p_success": float((v >= target_nom).mean()) if target_nom else None}
    if target_nom:
        for goal in C.SUCCESS_TARGETS:
            if out["plan"]["p_success"] is not None and out["plan"]["p_success"] >= goal:
                out[f"sip_for_{int(goal * 100)}"] = c.sip
                continue
            lo, hi = c.sip, max(c.sip * 2, 10_000)
            while (simulate(plan, months, hi, plan.after, sims=2000) >= target_nom).mean() < goal and hi < 5e7:
                lo, hi = hi, hi * 2
            for _ in range(18):
                mid = (lo + hi) / 2
                if (simulate(plan, months, mid, plan.after, sims=2000) >= target_nom).mean() >= goal:
                    hi = mid
                else:
                    lo = mid
            out[f"sip_for_{int(goal * 100)}"] = round(hi / 500) * 500
    h = _history()
    out["history"] = f"{h.index[0].strftime('%b %Y')} to {h.index[-1].strftime('%b %Y')}"
    return out
