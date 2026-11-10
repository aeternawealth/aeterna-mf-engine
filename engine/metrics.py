"""Agent 3 - Quant metrics engine (pure, deterministic Python).

All functions take a NAV series and a benchmark TRI series (both indexed by date)
and an as-of date, so the same code powers live ranking and the walk-forward backtest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

RF = 0.065          # risk-free (approx. 91-day T-bill / overnight), annual
ROLL_LOOKBACK = 3   # years of rolling-window end dates used for every fund
ROLL_MIN_COVERAGE = 0.9
W = 52              # weeks per year


def _cut(s: pd.Series, as_of, years=None):
    s = s[s.index <= as_of].dropna()
    if years is not None:
        s = s[s.index > as_of - pd.DateOffset(years=years)]
    return s


def _weekly(s: pd.Series) -> pd.Series:
    return s.resample("W-FRI").last().dropna()


def _cagr(s: pd.Series, years: float):
    if len(s) < 2:
        return np.nan
    start = s.index[-1] - pd.DateOffset(years=int(years)) if years >= 1 else s.index[-1] - pd.DateOffset(days=int(365 * years))
    base = s[s.index <= start]
    if base.empty or (start - base.index[-1]).days > 10:
        return np.nan
    return (s.iloc[-1] / base.iloc[-1]) ** (1 / years) - 1


def _roll(fw: pd.Series, bw: pd.Series, years: int, lookback_years: int, as_of):
    """Rolling `years`-CAGR on weekly data; windows ending in the last `lookback_years`."""
    k = W * years
    fr = (fw / fw.shift(k)) ** (1 / years) - 1
    br = (bw / bw.shift(k)) ** (1 / years) - 1
    ex = (fr - br).dropna()
    ex = ex[ex.index > as_of - pd.DateOffset(years=lookback_years)]
    return fr.dropna(), ex


def fund_metrics(nav: pd.Series, bench: pd.Series, as_of: pd.Timestamp) -> dict:
    nav = _cut(nav, as_of)
    bench = _cut(bench, as_of)
    m = {}
    if len(nav) < 30 or len(bench) < 30:
        return m
    m["age_years"] = (nav.index[-1] - nav.index[0]).days / 365.25
    m["nav_date"] = nav.index[-1]

    for y in (1, 3, 5):
        m[f"cagr_{y}y"] = _cagr(nav, y)
        m[f"bench_cagr_{y}y"] = _cagr(bench, y)
        m[f"excess_cagr_{y}y"] = m[f"cagr_{y}y"] - m[f"bench_cagr_{y}y"]

    fw, bw = _weekly(nav), _weekly(bench)
    j = pd.concat([fw, bw], axis=1, keys=["f", "b"]).dropna()
    # Rolling windows: every fund is measured on the SAME set of window end-dates (the last
    # ROLL_LOOKBACK years). Funds without enough history for (nearly) all of them get no rolling
    # metric rather than a metric computed on a different, shorter market period.
    need = int(W * ROLL_LOOKBACK * ROLL_MIN_COVERAGE)
    if len(j) > W * 3 + 10:
        _, ex3 = _roll(j.f, j.b, 3, ROLL_LOOKBACK, as_of)
        if len(ex3) >= need:
            m["roll3y_excess_median"] = float(ex3.median())
            m["roll3y_hit_rate"] = float((ex3 > 0).mean())
            m["roll3y_excess_p10"] = float(ex3.quantile(0.10))
            m["roll3y_windows"] = int(len(ex3))
    if len(j) > W + 10:
        _, ex1 = _roll(j.f, j.b, 1, ROLL_LOOKBACK, as_of)
        if len(ex1) >= need:
            m["roll1y_hit_rate"] = float((ex1 > 0).mean())
            m["roll1y_excess_median"] = float(ex1.median())

    # Historical range of outcomes: every 3-year holding period in the fund's life (information, not scored)
    if len(fw) > W * 3 + 26:
        r3 = ((fw / fw.shift(W * 3)) ** (1 / 3) - 1).dropna()
        m.update(hist3y_n=int(len(r3)), hist3y_median=float(r3.median()), hist3y_p10=float(r3.quantile(0.1)),
                 hist3y_p90=float(r3.quantile(0.9)), hist3y_worst=float(r3.min()), hist3y_best=float(r3.max()),
                 hist3y_pos=float((r3 > 0).mean()), hist3y_gt7=float((r3 > 0.07).mean()), hist3y_from=str(fw.index[0].date()))

    # 3Y risk block on weekly returns
    j3 = j[j.index > as_of - pd.DateOffset(years=3)]
    if len(j3) > W * 2.5:
        r = j3.pct_change().dropna()
        act = r.f - r.b
        te = act.std() * np.sqrt(W)
        m["vol_3y"] = r.f.std() * np.sqrt(W)
        m["tracking_err_3y"] = te
        m["info_ratio_3y"] = act.mean() * W / te if te > 0 else np.nan
        dd = np.minimum(r.f - RF / W, 0)
        dsd = np.sqrt((dd ** 2).mean()) * np.sqrt(W)
        ann = (j3.f.iloc[-1] / j3.f.iloc[0]) ** (W / (len(j3) - 1)) - 1
        m["sortino_3y"] = (ann - RF) / dsd if dsd > 0 else np.nan
        m["sharpe_3y"] = (ann - RF) / m["vol_3y"] if m["vol_3y"] > 0 else np.nan
        cov = np.cov(r.f, r.b)
        m["beta_3y"] = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else np.nan
        # capture ratios on monthly returns
        mo = j3.resample("ME").last().pct_change().dropna()
        up, dn = mo[mo.b > 0], mo[mo.b < 0]
        if len(up) >= 6:
            m["upside_capture_3y"] = up.f.mean() / up.b.mean() * 100
        if len(dn) >= 4:
            m["downside_capture_3y"] = dn.f.mean() / dn.b.mean() * 100
        if "upside_capture_3y" in m and "downside_capture_3y" in m and m["downside_capture_3y"] > 0:
            m["capture_ratio_3y"] = m["upside_capture_3y"] / m["downside_capture_3y"]

    if all(k in m for k in ("cagr_3y", "bench_cagr_3y", "beta_3y")) and pd.notna(m["cagr_3y"]):
        m["alpha_3y"] = m["cagr_3y"] - (RF + m["beta_3y"] * (m["bench_cagr_3y"] - RF))   # Jensen's alpha, annual
    n3 = _cut(nav, as_of, 3)
    if len(n3) > 1 and (n3.index[-1] - n3.index[0]).days > 365 * 2.9:
        m["max_drawdown_3y"] = float((n3 / n3.cummax() - 1).min())
    n5 = _cut(nav, as_of, 5)
    if len(n5) > 1 and (n5.index[-1] - n5.index[0]).days > 365 * 4.5:
        m["max_drawdown_5y"] = float((n5 / n5.cummax() - 1).min())
        b5 = _cut(bench, as_of, 5)
        m["bench_max_drawdown_5y"] = float((b5 / b5.cummax() - 1).min())
    return m


def arbitrage_metrics(nav: pd.Series, bench: pd.Series, liquid: pd.Series | None, as_of: pd.Timestamp) -> dict:
    """Arbitrage funds: return over the arbitrage index (rolling 1Y and 3Y), steadiness, and the comparison
    investors actually make: against the median liquid fund."""
    nav, bench = _cut(nav, as_of), _cut(bench, as_of)
    m = {}
    if len(nav) < 30 or len(bench) < 30:
        return m
    m["age_years"] = (nav.index[-1] - nav.index[0]).days / 365.25
    m["nav_date"] = nav.index[-1]
    for y in (1, 3, 5):
        m[f"cagr_{y}y"] = _cagr(nav, y)
        m[f"bench_cagr_{y}y"] = _cagr(bench, y)
        m[f"excess_cagr_{y}y"] = m[f"cagr_{y}y"] - m[f"bench_cagr_{y}y"]
    j = pd.concat([_weekly(nav), _weekly(bench)], axis=1, keys=["f", "b"]).dropna()
    need = int(W * ROLL_LOOKBACK * ROLL_MIN_COVERAGE)
    if len(j) > W + 10:
        _, ex1 = _roll(j.f, j.b, 1, ROLL_LOOKBACK, as_of)
        if len(ex1) >= need:
            m["roll1y_hit_rate"] = float((ex1 > 0).mean())
            m["roll1y_excess_median"] = float(ex1.median())
    n3 = _cut(nav, as_of, 3)
    if len(n3) > 1 and (n3.index[-1] - n3.index[0]).days > 365 * 2.9:
        mo = n3.resample("ME").last().pct_change().dropna()
        if len(mo) >= 30:
            m["vol_3y"] = float(mo.std() * np.sqrt(12))
            m["neg_months_3y"] = float((mo < 0).mean())
        m["max_drawdown_3y"] = float((n3 / n3.cummax() - 1).min())
    if liquid is not None:
        liq = _cut(liquid, as_of)
        for y in (1, 3):
            lc = _cagr(liq, y)
            m[f"liq_cagr_{y}y"] = lc
            m[f"excess_vs_liquid_{y}y"] = m[f"cagr_{y}y"] - lc
            m[f"excess_vs_liquid_post_tax_{y}y"] = m[f"cagr_{y}y"] * (1 - C.TAX_EQUITY_LTCG) - lc * (1 - C.TAX_SLAB_TOP)
    return m


def median_series(navs: list) -> pd.Series | None:
    """The median fund as an index level: the median daily return across funds, cumulated.
    Liquid and overnight funds publish a NAV for every calendar day, other funds only on business days. Taking the
    median day by day over both kinds counts weekend interest twice (Saturday and Sunday from one kind, the
    3-day Monday return from the other), which overstated the median liquid fund by about 1.2% a year. So every
    series is first put on one business-day calendar (a weekend's interest lands on Monday for all)."""
    navs = [s.dropna() for s in navs if s is not None and len(s.dropna()) > 1]
    if not navs:
        return None
    cal = pd.bdate_range(min(s.index[0] for s in navs), max(s.index[-1] for s in navs))
    rets = []
    for s in navs:
        s = s[~s.index.duplicated(keep="last")].sort_index()
        b = s.reindex(s.index.union(cal)).ffill().reindex(cal)
        b[(b.index < s.index[0]) | (b.index > s.index[-1])] = np.nan
        rets.append(b.pct_change())
    med = pd.concat(rets, axis=1).median(axis=1, skipna=True).fillna(0)
    return (1 + med).cumprod()


STYLE_INDEX = {"small": "NIFTY SMALLCAP 250", "mid": "NIFTY MIDCAP 150"}


def _ret_months(s: pd.Series, t, months: int):
    s = s[:t]
    a = s[:t - pd.DateOffset(months=months)]
    return s.iloc[-1] / a.iloc[-1] - 1 if len(s) and len(a) else np.nan


def lean_metrics(nav: pd.Series, bench: pd.Series, tri, as_of: pd.Timestamp) -> dict:
    """Inputs of the v4 equity score (audit/research_monthly.py, Nov 2026): momentum over 1, 3, 6 and 12 months (fund
    return minus benchmark TRI return), and the fund's tilt towards small and mid caps: the slope of its weekly return
    over the benchmark on each size index's weekly return over the benchmark, over 3 years. Same formulas as the
    research panel (audit/research_panel.py), so live ratings match what was tested."""
    m = {}
    for mo in (1, 3, 6, 12):
        m[f"mom_{mo}m"] = _ret_months(nav, as_of, mo) - _ret_months(bench, as_of, mo)
    w = lambda x: x[as_of - pd.DateOffset(years=3):as_of].resample("W-FRI").last().pct_change()
    fw, bw = w(nav), w(bench)
    for k, name in STYLE_INDEX.items():
        if tri is None or name not in tri:
            continue
        sw = w(tri[name].dropna())
        j = pd.concat([fw - bw, sw - bw], axis=1, keys=["f", "s"]).dropna()
        m[f"style_{k}"] = float(j.f.cov(j.s) / j.s.var()) if len(j) > 100 and j.s.var() > 0 else np.nan
    return m


def debt_clean(nav: pd.Series) -> pd.Series:
    """A debt fund's NAV cannot halve or double in a day: such jumps are face-value changes (e.g. Rs 1,000 to
    Rs 10 units) or data slips. The day's return is set to zero and the series rebuilt."""
    r = nav.pct_change()
    bad = (r <= -0.4) | (r >= 0.6)
    if not bad.any():
        return nav
    r[bad] = 0.0
    return nav.iloc[0] * (1 + r.fillna(0)).cumprod()


def debt_metrics(nav: pd.Series, bench: pd.Series, as_of: pd.Timestamp, rate_days=None) -> dict:
    """Debt funds against the median fund of their category and plan type: return over it (point and rolling 1Y),
    steadiness, the worst fall and the worst single day (a large one-day fall is a credit event, not rates)."""
    nav, bench = _cut(debt_clean(nav), as_of), _cut(bench, as_of)
    m = {}
    if len(nav) < 30 or len(bench) < 30:
        return m
    m["age_years"] = (nav.index[-1] - nav.index[0]).days / 365.25
    m["nav_date"] = nav.index[-1]
    for y in (1, 3, 5):
        m[f"cagr_{y}y"] = _cagr(nav, y)
        m[f"bench_cagr_{y}y"] = _cagr(bench, y)
        m[f"excess_cagr_{y}y"] = m[f"cagr_{y}y"] - m[f"bench_cagr_{y}y"]
    j = pd.concat([_weekly(nav), _weekly(bench)], axis=1, keys=["f", "b"]).dropna()
    need = int(W * ROLL_LOOKBACK * ROLL_MIN_COVERAGE)
    if len(j) > W + 10:
        _, ex1 = _roll(j.f, j.b, 1, ROLL_LOOKBACK, as_of)
        if len(ex1) >= need:
            m["roll1y_hit_rate"] = float((ex1 > 0).mean())
            m["roll1y_excess_median"] = float(ex1.median())
    # worst day against the category median on the same day: a whole category falling is interest rates,
    # one fund falling alone is its portfolio (a default or downgrade)
    nb = nav.reindex(nav.index.union(bench.index)).ffill().reindex(bench.index)   # the fund on the median's business days
    dd = pd.concat([nb.pct_change(), bench.pct_change()], axis=1, keys=["f", "b"]).dropna()
    d5 = dd[dd.index > as_of - pd.Timedelta(days=int(365.25 * 5))]
    if rate_days is not None and len(rate_days):   # days when government bonds themselves moved sharply: rates, not credit
        d5 = d5[~d5.index.isin(rate_days)]
    if len(d5) > 200:
        rel = d5.f - d5.b
        m["worst_rel_day_5y"] = float(rel.min())
        m["worst_rel_day_date"] = rel.idxmin()
    for y in (3, 5):
        n = _cut(nav, as_of, y)
        if len(n) > 1 and (n.index[-1] - n.index[0]).days > 365 * (y - .1):
            d = n.pct_change().dropna()
            m[f"worst_day_{y}y"] = float(d.min())
            m[f"max_drawdown_{y}y"] = float((n / n.cummax() - 1).min())
            if y == 3:
                mo = n.resample("ME").last().pct_change().dropna()
                if len(mo) >= 30:
                    m["vol_3y"] = float(mo.std() * np.sqrt(12))
                    m["neg_months_3y"] = float((mo < 0).mean())
    if "worst_day_5y" not in m and m["age_years"] >= 1:
        m["worst_day_5y"] = float(nav.pct_change().dropna().min())
    return m


def index_metrics(nav: pd.Series, idx: pd.Series, as_of: pd.Timestamp) -> dict:
    """Tracking metrics for an index fund vs the TRI it tracks (or a peer proxy series)."""
    m = {}
    nav, idx = _cut(nav, as_of), _cut(idx, as_of)
    j = pd.concat([nav, idx], axis=1, keys=["f", "b"]).dropna()
    if len(j) < 60:
        return m
    m["age_years"] = (nav.index[-1] - nav.index[0]).days / 365.25
    m["nav_date"] = nav.index[-1]
    for y in (1, 3, 5):
        m[f"cagr_{y}y"] = _cagr(nav, y)
    j1 = j[j.index > as_of - pd.DateOffset(years=1)]
    if len(j1) > 200:
        r = j1.pct_change().dropna()
        m["tracking_err_1y"] = (r.f - r.b).std() * np.sqrt(252) * 100   # in %
        m["tracking_diff_1y"] = ((j1.f.iloc[-1] / j1.f.iloc[0]) - (j1.b.iloc[-1] / j1.b.iloc[0])) * 100
    j3 = j[j.index > as_of - pd.DateOffset(years=3)]
    if (j3.index[-1] - j3.index[0]).days > 365 * 2.9:
        yrs = (j3.index[-1] - j3.index[0]).days / 365.25
        fc = (j3.f.iloc[-1] / j3.f.iloc[0]) ** (1 / yrs) - 1
        bc = (j3.b.iloc[-1] / j3.b.iloc[0]) ** (1 / yrs) - 1
        m["tracking_diff_3y"] = (fc - bc) * 100
    return m


# ---------------------------------------------------------------- horizon (period-wise) metrics
HORIZONS = {"6M": 0.5, "1Y": 1, "3Y": 3, "5Y": 5}
# rolling sub-window (in weeks) used for each horizon's consistency (hit-rate) measure
_HIT_WINDOW = {"6M": 4, "1Y": 13, "3Y": 52, "5Y": 156}


def horizon_metrics(nav: pd.Series, bench: pd.Series, as_of: pd.Timestamp) -> dict:
    """Metrics computed strictly inside each look-back window (6M/1Y/3Y/5Y).
    A horizon is only filled if the fund has existed for the whole window."""
    nav, bench = _cut(nav, as_of), _cut(bench, as_of)
    m = {}
    if len(nav) < 20 or len(bench) < 20:
        return m
    for h, yrs in HORIZONS.items():
        start = as_of - pd.DateOffset(months=int(yrs * 12))
        if nav.index[0] > start + pd.Timedelta(days=10):
            continue                                    # not old enough for this horizon
        j = pd.concat([nav, bench], axis=1, keys=["f", "b"]).dropna()
        base = j.index[j.index <= start]          # same base date rule as trailing CAGR: last NAV on/before start
        if len(base) == 0:
            continue
        j = j[j.index >= base.max()]
        if len(j) < 60:
            continue
        span = (j.index[-1] - j.index[0]).days / 365.25
        # one return definition everywhere: last NAV on/before (end - period) to last NAV, CAGR over the nominal years
        nb, bb = nav[nav.index <= start], bench[bench.index <= start]
        fr, br = nav.iloc[-1] / nb.iloc[-1], bench.iloc[-1] / bb.iloc[-1]
        if yrs >= 1:
            fr, br = fr ** (1 / yrs), br ** (1 / yrs)
        m[f"ret_{h}"] = fr - 1
        m[f"excess_{h}"] = fr - br
        w = j.resample("W-FRI").last().dropna()
        r = w.pct_change().dropna()
        act = r.f - r.b
        te = act.std() * np.sqrt(W)
        m[f"te_{h}"] = te * 100
        m[f"ir_{h}"] = act.mean() * W / te if te > 0 else np.nan
        dsd = np.sqrt((np.minimum(r.f - RF / W, 0) ** 2).mean()) * np.sqrt(W)
        ann = (w.f.iloc[-1] / w.f.iloc[0]) ** (W / max(len(w) - 1, 1)) - 1
        m[f"sortino_{h}"] = (ann - RF) / dsd if dsd > 0 else np.nan
        dn = r[r.b < 0]
        if len(dn) >= 4:
            m[f"dcap_{h}"] = dn.f.mean() / dn.b.mean() * 100
        m[f"mdd_{h}"] = float((j.f / j.f.cummax() - 1).min())
        k = _HIT_WINDOW[h]
        if len(w) > k + 8:
            rr = (w.f / w.f.shift(k)) - (w.b / w.b.shift(k))
            m[f"hit_{h}"] = float((rr.dropna() > 0).mean())
    return m
