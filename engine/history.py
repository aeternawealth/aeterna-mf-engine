"""Monthly rating history for equity funds, and the reason behind each change.

Every month-end the active equity funds are rated with the same rules as the live run (rank_universe), using only
data up to that date. The first run fills the last HISTORY_MONTHS months; later runs add the months that are missing.
Kept per fund and month: rating, score, rank, group size, the 'behind the index' cap, red flags, and the fund's
percentile in its peer group on every input of its model (to explain a change).

Outputs
  outputs/rating_history.csv.gz   the history (committed by the data workflows)
  outputs/latest/rating_history.json   for the website: per fund, a list of
      [month, rating, rank, group size, score, reason or ""]
Limits: funds that have since closed are not in the past peer groups, and holdings-based checks (SEBI mandate,
closet indexing) are not applied to past months."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import time

import numpy as np
import pandas as pd

from . import config as C

HISTORY_MONTHS = 36
HIST = C.OUT / "rating_history.csv.gz"
KEEP = ["code", "category", "plan_type", "tier", "score", "peer_rank", "peer_count", "guard_capped", "flags", "market_mode"]

NAMES = {"mom_1m": "1-month return over the index", "mom_3m": "3-month return over the index", "mom_6m": "6-month return over the index",
         "mom_12m": "12-month return over the index", "style_small": "tilt towards small caps", "style_mid": "tilt towards mid caps",
         "style_mom": "tilt towards momentum stocks", "style_val": "tilt towards value stocks", "style_lowvol": "tilt towards low-volatility stocks",
         "style_qual": "tilt towards quality stocks", "style_n50": "tilt towards the Nifty 50", "upside_capture_3y": "share of market rises captured",
         "downside_capture_3y": "share of market falls taken", "capture_ratio_3y": "rises captured against falls taken", "alpha_3y": "alpha",
         "info_ratio_3y": "information ratio", "sharpe_3y": "Sharpe ratio", "sortino_3y": "Sortino ratio", "beta_3y": "beta", "vol_3y": "volatility",
         "tracking_err_3y": "tracking error", "excess_cagr_1y": "1-year return over the index", "excess_cagr_3y": "3-year return over the index",
         "excess_cagr_5y": "5-year return over the index", "roll1y_hit_rate": "share of 1-year periods ahead of the index",
         "roll1y_excess_median": "typical 1-year return over the index", "roll3y_excess_median": "typical 3-year return over the index",
         "roll3y_hit_rate": "share of 3-year periods ahead of the index", "roll3y_excess_p10": "worst 3-year periods against the index",
         "max_drawdown_3y": "deepest fall", "max_drawdown_5y": "deepest fall", "age_years": "age", "ter": "expense ratio",
         "active_share": "active share", "mandate_ok": "SEBI mandate fit", "cash_other_pct": "cash held", "turnover_1m": "portfolio turnover",
         "aum_capacity_penalty": "fund size", "beyond500_pct": "holdings outside the top 500 stocks"}
FLAG_NAMES = {"chronic_underperformer": "persistent underperformance", "risk_without_reward": "falls more without extra return",
              "deep_drawdown": "deeper falls than peers", "mandate_breach": "portfolio outside SEBI limits", "closet_indexer": "close to its index",
              "turnaround_unproven": "recent recovery not yet proven"}
ORDER = {"A+": 0, "A": 1, "B": 2, "C": 3}


def _equity(u: pd.DataFrame) -> pd.DataFrame:
    """Active equity funds: every category rated by an equity protocol."""
    ok = u["category"].map(lambda c: any(k in C.protocol_for(c)[0].lower() for k in ("equity", "small/mid", "thematic")))
    return u[ok]


def _inputs(category: str, mode: str = "normal") -> dict:
    w = {m: wt for m, (pl, wt, hib) in C.protocol_for(category)[1].items() if wt > 0}
    if mode == "after a fall" and C.EQUITY_MODEL in ("v7", "v8") and category in C.V7_CATEGORIES:   # half the model, half rebound
        r = {m: wt for m, (pl, wt, hib) in C.v7_rebound(category).items()}
        w = {m: w.get(m, 0) / 2 + r.get(m, 0) / 2 for m in set(w) | set(r)}
    return w


def _month_ends(tri: pd.DataFrame, n: int) -> list[pd.Timestamp]:
    idx = tri.dropna(how="all").index
    ends = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max().tolist()
    last = idx.max()
    if ends and ends[-1] == last and (last + pd.Timedelta(days=1)).month == last.month:   # current month not over yet
        ends = ends[:-1]
    return ends[-n:]


def _rows(out: pd.DataFrame, month: str) -> pd.DataFrame:
    o = out[out["tier"].notna()].copy()
    cols = [c for c in KEEP if c in o.columns] + [c for c in o.columns if c.startswith("p_")]
    o = o[cols].copy()
    o["month"] = month
    o["flags"] = o["flags"].map(lambda f: ",".join(f) if isinstance(f, list) else (f if isinstance(f, str) else ""))
    for c in [c for c in o.columns if c.startswith("p_")] + ["score"]:
        o[c] = pd.to_numeric(o[c], errors="coerce").round(3)
    return o


_W = {}   # what each worker process needs, shared by fork rather than pickled


def _one(t):
    from .rank import rank_universe
    w = _W
    out = rank_universe(w["eq"], w["navs"], w["tri"], as_of=t, ter=w["ter"], aum=w["aum"], log=lambda *a, **k: None, liquid=w["liquid"], bond=w["bond"])
    return _rows(out, t.strftime("%Y-%m"))


def update(u, navs, tri, current: pd.DataFrame | None = None, months: int = HISTORY_MONTHS, log=print, liquid=None, bond=None, ter=None, aum=None,
           budget_min: float | None = None) -> pd.DataFrame:
    """Add the missing month-ends (and the current run as its own month) to the history file."""
    from .rank import rank_universe
    hist = pd.read_csv(HIST, low_memory=False) if HIST.exists() else pd.DataFrame(columns=KEEP + ["month"])
    have = set(hist["month"].astype(str))
    eq = _equity(u)
    todo = [t for t in _month_ends(tri, months) if t.strftime("%Y-%m") not in have]
    if todo:
        log(f"  rating history: rating {len(todo)} past month-ends ({todo[0].date()} .. {todo[-1].date()})")
    parts = [hist]
    # newest months first, so a run that runs out of time still fills the part of the chart people see first;
    # months are rated in parallel (today's expense ratio and AUM stand in for past ones), and no new month is
    # started once the time budget is used up: the next run carries on from there
    todo = sorted(todo, reverse=True)
    _W.update(eq=eq, navs=navs, tri=tri, ter=ter, aum=aum, liquid=liquid, bond=bond)
    t0, done = time.time(), []
    budget = (budget_min or 1e9) * 60
    if todo:
        workers = max(1, min(len(todo), (os.cpu_count() or 2)))
        ctx = mp.get_context("fork") if "fork" in mp.get_all_start_methods() else None
        if ctx and workers > 1:
            with ctx.Pool(workers) as pool:
                pending = list(todo)
                while pending and time.time() - t0 < budget:
                    batch, pending = pending[:workers], pending[workers:]
                    for r in pool.map(_one, batch):
                        parts.append(r); done.append(r["month"].iloc[0] if len(r) else "")
        else:
            for t in todo:
                if time.time() - t0 >= budget: break
                r = _one(t); parts.append(r); done.append(t.strftime("%Y-%m"))
        log(f"  rating history: {len(done)} of {len(todo)} months rated in {(time.time() - t0) / 60:.1f} min"
            + ("" if len(done) == len(todo) else "; the rest on the next run"))
    if current is not None and len(current):
        cur = _rows(current[current["code"].isin(eq["code"])], pd.Timestamp(current["as_of"].iloc[0]).strftime("%Y-%m"))
        parts = [p[p["month"].astype(str) != cur["month"].iloc[0]] for p in parts] + [cur]
    hist = pd.concat(parts, ignore_index=True)
    keep = sorted(hist["month"].astype(str).unique())[-months:]
    hist = hist[hist["month"].astype(str).isin(keep)]
    HIST.parent.mkdir(parents=True, exist_ok=True)
    hist.to_csv(HIST, index=False, compression="gzip")
    return hist


def _band(p: float) -> str:
    if not np.isfinite(p): return "no figure"
    if p > 1: p = p / 100      # the engine's percentiles run 0-100
    return ("the top 10%" if p >= .9 else "the top quarter" if p >= .75 else "the upper half" if p >= .5
            else "the lower half" if p >= .25 else "the bottom quarter" if p > .1 else "the bottom 10%")


def _reason(prev: pd.Series, cur: pd.Series) -> str:
    """Plain words for why a fund's rating or rank moved between two months."""
    if cur["tier"] == "Unrated":
        return "Not rated this month: too little history, or its NAV stopped updating."
    if prev["tier"] == "Unrated":
        return "Rated for the first time: it now has enough history."
    bits = []
    sa, sb = prev.get("score"), cur.get("score")
    if cur["tier"] != prev["tier"] and pd.notna(sa) and pd.notna(sb):
        cut = {"A+": 75, "A": 65}
        need = cut.get(cur["tier"]) if ORDER.get(cur["tier"], 9) < ORDER.get(prev["tier"], 9) else cut.get(prev["tier"])
        bits.append(f"its score went from {float(sa):.0f} to {float(sb):.0f}" + (f" ({'A+' if need == 75 else 'A'} needs {need})" if need else ""))
    ma, mb = str(prev.get("market_mode") or "normal"), str(cur.get("market_mode") or "normal")
    if ma != mb and mb == "after a fall":
        bits.append("its category's index fell below its 200-day average, so the after-a-fall criteria now count for half the score")
    elif ma != mb and ma == "after a fall":
        bits.append("its category's index is back above its 200-day average, so the normal criteria apply again")
    w = _inputs(cur["category"], mb)
    moves = []
    tot = sum(w[m] for m in w if np.isfinite(cur.get("p_" + m, np.nan)))
    for m, wt in w.items():
        a, b = prev.get("p_" + m, np.nan), cur.get("p_" + m, np.nan)
        if np.isfinite(a) and np.isfinite(b) and tot:
            moves.append(((b - a) * wt / tot * 100, m, a, b))
    moves.sort(key=lambda x: -abs(x[0]))
    big = [x for x in moves[:2] if abs(x[0]) >= 1.5]
    if len(big) == 2 and all(x[1].startswith("mom_") for x in big) and (_band(big[0][2]), _band(big[0][3])) == (_band(big[1][2]), _band(big[1][3])):
        ms = sorted(int(x[1][4:-1]) for x in big)   # two momentum windows that moved together read as one
        big = [(big[0][0] + big[1][0], f"__{ms[0]}-month and {ms[1]}-month returns over the index", big[0][2], big[0][3])]
    for d, m, a, b in big:
        nm = m[2:] if m.startswith("__") else NAMES.get(m, m)
        if _band(a) == _band(b):
            bits.append(f"its {nm} {'rose' if d > 0 else 'slipped'} within {_band(b)} of the group")
        else:
            bits.append(f"its {nm} moved from {_band(a)} to {_band(b)} of the group")
    fl = lambda v: set(filter(None, v.split(","))) if isinstance(v, str) else set()   # an empty field reads back as NaN
    fa, fb = fl(prev.get("flags")), fl(cur.get("flags"))
    for f in sorted(fb - fa):
        bits.append(f"a red flag was raised: {FLAG_NAMES.get(f, f.replace('_', ' '))}")
    for f in sorted(fa - fb):
        bits.append(f"the red flag '{FLAG_NAMES.get(f, f.replace('_', ' '))}' cleared")
    gp, gc = bool(prev.get("guard_capped") is True or str(prev.get("guard_capped")) == "True"), bool(cur.get("guard_capped") is True or str(cur.get("guard_capped")) == "True")
    if gc and not gp:
        bits.append("it was held back from a higher rating because it is behind its index over 3 years, after costs")
    if gp and not gc:
        bits.append("it is no longer held back: it is ahead of its index again over 3 years")
    if not bits:
        bits.append("other funds in the group moved past it" if (cur.get("peer_rank") or 0) > (prev.get("peer_rank") or 0)
                    else "it moved past other funds in the group")
    s = "; ".join(bits)
    return s[0].upper() + s[1:] + "."


def site_json(hist: pd.DataFrame, path) -> int:
    """Per fund: [month, rating, rank, group size, score, reason]. A reason is given when the rating changes or the rank
    moves by 3 places or more."""
    out = {}
    hist = hist.sort_values(["code", "month"])
    for code, g in hist.groupby("code"):
        rows, prev = [], None
        for _, r in g.iterrows():
            rk = int(r["peer_rank"]) if pd.notna(r.get("peer_rank")) else None
            n = int(r["peer_count"]) if pd.notna(r.get("peer_count")) else None
            why = ""
            pr = prev.get("peer_rank") if prev is not None else None
            if prev is not None and (r["tier"] != prev["tier"] or (rk and pd.notna(pr) and abs(rk - pr) >= 3)):
                why = _reason(prev, r)
            rows.append([str(r["month"]), r["tier"], rk, n, None if pd.isna(r.get("score")) else float(r["score"]), why, str(r.get("market_mode") or "")])
            prev = r
        out[str(int(code))] = rows
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return len(out)
