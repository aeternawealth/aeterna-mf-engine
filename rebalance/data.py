"""Read-only access to the engine's data: ratings (site/data/funds.json), monthly portfolios (data/holdings/<month>/),
daily NAVs (data/nav/<code>.csv) and category NAV panels (site/data/series/<category>.json).
Nothing here writes to the engine."""
from __future__ import annotations

import difflib
import json
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

import pandas as pd

from . import config as C

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def funds() -> pd.DataFrame:
    df = pd.DataFrame(json.loads((ROOT / "site" / "data" / "funds.json").read_text()))
    df["bucket"] = df["category"].map(C.BUCKET_OF_CATEGORY)
    df.loc[df.bucket.isna() & (df.asset_class == "Debt"), "bucket"] = "debt"
    df.loc[df.bucket.isna() & (df.asset_class == "Hybrid"), "bucket"] = "hybrid"
    df["bucket"] = df["bucket"].fillna("other")
    df["_n"] = df["name"].map(_norm)
    return df.set_index("code", drop=False)


def as_of() -> str:
    m = json.loads((ROOT / "site" / "data" / "meta.json").read_text())
    return str(m.get("as_of", ""))[:10]


def _norm(s: str) -> str:
    s = str(s).lower().replace("&", " and ")
    s = re.sub(r"\b(direct|regular|plan|growth|option|fund|the|scheme|mutual|idcw|g)\b", " ", s)
    s = s.replace("midcap", "mid cap").replace("smallcap", "small cap").replace("multicap", "multi cap").replace("largecap", "large cap")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def match(name: str, plan: str | None = None, code=None, isin: str | None = None):
    """the funds.json row for a holding: by AMFI code, else by name within the plan type. None if no confident match."""
    f = funds()
    if code is not None:
        try:
            c = int(code)
            if c in f.index:
                return f.loc[c]
        except (TypeError, ValueError):
            pass
    if plan is None:
        plan = "Direct" if re.search(r"\bdirect\b", str(name), re.I) else "Regular"
    pool = f[f.plan_type == plan]
    n = _norm(name)
    exact = pool[pool._n == n]
    if len(exact):
        return exact.iloc[0]
    hit = difflib.get_close_matches(n, pool._n.tolist(), n=1, cutoff=0.86)
    return pool[pool._n == hit[0]].iloc[0] if hit else None


def other_plan(row):
    """the same scheme's other plan (Direct <-> Regular)"""
    f = funds()
    o = f[(f.pair_key == row["pair_key"]) & (f.plan_type != row["plan_type"])]
    return o.iloc[0] if len(o) else None


# ------------------------------------------------------------------ portfolios
def _latest_month() -> str | None:
    ms = sorted(p.name for p in (ROOT / "data" / "holdings").glob("20??-??") if (p / "_weights.csv").exists())
    return ms[-1] if ms else None


@lru_cache(maxsize=1)
def weights() -> dict:
    m = _latest_month()
    if not m:
        return {}
    w = pd.read_csv(ROOT / "data" / "holdings" / m / "_weights.csv")
    return {k: g.groupby("isin").weight.sum() / 100 for k, g in w.groupby("pair_key")}


@lru_cache(maxsize=1)
def port_metrics() -> pd.DataFrame:
    m = _latest_month()
    p = ROOT / "data" / "holdings" / (m or "") / "holdings_metrics.csv"
    return pd.read_csv(p).set_index("pair_key") if m and p.exists() else pd.DataFrame()


def holdings_month() -> str | None:
    return _latest_month()


def overlap(pk_a: str, pk_b: str) -> float | None:
    """share of the portfolio two funds hold in common: sum over stocks of the smaller weight (0-1)"""
    w = weights()
    if pk_a not in w or pk_b not in w:
        return None
    j = pd.concat([w[pk_a], w[pk_b]], axis=1).fillna(0)
    return float(j.min(axis=1).sum())


def mcap_mix(pk: str) -> dict | None:
    pm = port_metrics()
    if pk not in pm.index:
        return None
    r = pm.loc[pk]
    if isinstance(r, pd.DataFrame):
        r = r.iloc[0]
    return {k: float(r[k + "_pct"]) / 100 for k in ("large", "mid", "small") if pd.notna(r.get(k + "_pct"))} | {
        "other": max(0.0, 1 - sum(float(r[k + "_pct"]) / 100 for k in ("large", "mid", "small") if pd.notna(r.get(k + "_pct"))))}


# ------------------------------------------------------------------ NAVs
@lru_cache(maxsize=4096)
def nav_series(code: int) -> pd.Series | None:
    p = ROOT / "data" / "nav" / f"{int(code)}.csv"
    if not p.exists():
        return None
    s = pd.read_csv(p, parse_dates=["date"]).set_index("date")["nav"].sort_index()
    return s


def nav_on(code: int, d: date) -> float | None:
    """the NAV on date d, or the last one before it"""
    s = nav_series(code)
    if s is None:
        return None
    s = s[s.index <= pd.Timestamp(d)]
    return float(s.iloc[-1]) if len(s) else None


@lru_cache(maxsize=64)
def category_returns(slug: str) -> pd.Series:
    """monthly returns of the category's median fund (site/data/series/<slug>.json)"""
    d = json.loads((ROOT / "site" / "data" / "series" / f"{slug}.json").read_text())
    nav = pd.DataFrame(d["nav"], index=pd.PeriodIndex(d["months"], freq="M")).astype(float)
    r = nav.pct_change(fill_method=None)
    r = r[(r > -0.6) & (r < 0.6)]                       # NAV face-value changes and data errors
    med = r.median(axis=1, skipna=True)
    n = r.notna().sum(axis=1)
    return med[n >= 3].dropna()
