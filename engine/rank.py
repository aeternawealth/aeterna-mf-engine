"""Pipeline orchestration: universe -> peer groups -> metrics -> protocols -> tiers -> outputs."""
from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from . import config as C
from .metrics import arbitrage_metrics, fund_metrics, horizon_metrics, index_metrics
from .protocols import assign_tiers, score_group


def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ------------------------------------------------------------- peer groups
def assign_theme(name: str):
    low = f" {name.lower()} "
    for keys, theme, bench in C.THEME_RULES:
        if any(k in low for k in keys):
            return theme, bench
    return "Other Themes", "NIFTY 500"


def match_index(name: str, tri_cols) -> str | None:
    k = _key(name)
    best = None
    for col in tri_cols:
        ck = _key(col).replace("index", "")
        if ck and ck in k and (best is None or len(ck) > len(_key(best))):
            best = col
    return best


def index_label(name: str, amc: str) -> str:
    n = name
    amc_word = (amc or "").replace("Mutual Fund", "").strip()
    if amc_word:
        n = re.sub(re.escape(amc_word), "", n, flags=re.I)
    n = re.sub(r"(?i)\b(index fund|index|fund|direct|regular|plan|growth|option|-)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip().upper() or name


def assign_peers(u: pd.DataFrame, tri: pd.DataFrame) -> pd.DataFrame:
    u = u.copy()
    u["peer_group"] = u["category"].map(lambda c: C.MERGE_PEER_GROUPS.get(c, c))
    u["benchmark"] = u["category"].map(C.CATEGORY_BENCHMARK)
    th = u["category"] == "Sectoral/Thematic"
    # strip the AMC's own name first ("Bank of India Manufacturing Fund" is not a banking fund)
    clean = [re.sub(re.escape((a or "").replace(" Mutual Fund", "")), " ", n, flags=re.I) for n, a in zip(u.loc[th, "name"], u.loc[th, "amc"])]
    themes = pd.Series(clean, index=u.index[th]).map(assign_theme)
    u.loc[th, "theme"] = themes.map(lambda t: t[0])
    u.loc[th, "benchmark"] = themes.map(lambda t: t[1] if t[1] in tri.columns else "NIFTY 500")
    # small theme buckets -> Other Themes
    counts = u[th].groupby(["theme", "plan_type"]).size()
    small = {t for (t, p), n in counts.items() if n < C.THEME_MIN_PEERS}
    u.loc[th & u["theme"].isin(small), "theme"] = "Other Themes"
    u.loc[th & (u["theme"] == "Other Themes"), "benchmark"] = "NIFTY 500"
    u.loc[th & u["theme"].eq("International"), "benchmark"] = None
    u.loc[th, "peer_group"] = "Thematic: " + u.loc[th, "theme"]

    ix = u["category"] == "Index Fund"
    tracked = u.loc[ix, "name"].map(lambda n: match_index(n, tri.columns))
    labels = [t if isinstance(t, str) else index_label(n, a)
              for t, n, a in zip(tracked, u.loc[ix, "name"], u.loc[ix, "amc"])]
    u.loc[ix, "benchmark"] = tracked
    u.loc[ix, "peer_group"] = ["Index: " + l for l in labels]
    # arbitrage: the Nifty 50 Arbitrage index if niftyindices lists it (name matched loosely), else a peer proxy
    ar = u["category"] == "Arbitrage"
    if ar.any():
        arb = next((c for c in tri.columns if _key(c) == _key(C.CATEGORY_BENCHMARK["Arbitrage"])), None) or \
            next((c for c in tri.columns if "arbitrage" in c.lower()), None)
        u.loc[ar, "benchmark"] = arb
    return u


# ------------------------------------------------------------- metrics
def compute_metrics(u: pd.DataFrame, navs: dict, tri: pd.DataFrame, as_of: pd.Timestamp, log=print, liquid=None):
    rows = []
    liquid = liquid or {}
    # proxy benchmark for index groups without a Nifty TRI: median daily return of peers
    proxies = {}
    for pg, g in u[(u.category == "Index Fund") & u.benchmark.isna()].groupby("peer_group"):
        series = [navs[c].set_index("date")["nav"].pct_change() for c in g.code if c in navs]
        if len(series) >= 2:
            med = pd.concat(series, axis=1).median(axis=1).fillna(0)
            proxies[pg] = (1 + med).cumprod()
    arb = u[(u.category == "Arbitrage") & u.benchmark.isna()]
    if len(arb):   # no arbitrage TRI: median arbitrage fund (Regular and Direct together) as the index
        series = [navs[c].set_index("date")["nav"].pct_change() for c in arb.code if c in navs]
        if len(series) >= 2:
            proxies["Arbitrage"] = (1 + pd.concat(series, axis=1).median(axis=1).fillna(0)).cumprod()
    for n, r in enumerate(u.itertuples(index=False), 1):
        d = navs.get(r.code)
        if d is None or d.empty:
            continue
        nav = d.set_index("date")["nav"]
        if r.category == "Index Fund":
            if isinstance(r.benchmark, str) and r.benchmark in tri:
                bser, btype = tri[r.benchmark].dropna(), "TRI"
            elif r.peer_group in proxies:
                bser, btype = proxies[r.peer_group], "peer-median proxy"
            else:
                bser, btype = None, None
            m = index_metrics(nav, bser, as_of) if bser is not None else {
                "age_years": (nav.index[-1] - nav.index[0]).days / 365.25, "nav_date": nav.index[-1],
                "cagr_1y": np.nan}
            m["bench_type"] = btype
            if bser is not None:
                m.update(horizon_metrics(nav, bser, as_of))
        elif r.category == "Arbitrage":
            if isinstance(r.benchmark, str) and r.benchmark in tri:
                bser, btype = tri[r.benchmark].dropna(), "TRI"
            elif "Arbitrage" in proxies:
                bser, btype = proxies["Arbitrage"], "peer-median proxy"
            else:
                continue
            m = arbitrage_metrics(nav, bser, liquid.get(r.plan_type), as_of)
            m["bench_type"] = btype
            m.update(horizon_metrics(nav, bser, as_of))
        else:
            bname = r.benchmark if isinstance(r.benchmark, str) and r.benchmark in tri else None
            if bname is None:
                continue
            try:
                m = fund_metrics(nav, tri[bname].dropna(), as_of)
            except Exception as e:
                log(f"  metrics failed for {r.code} {r.name}: {e}")
                continue
            m["bench_type"] = "TRI"
            m.update(horizon_metrics(nav, tri[bname].dropna(), as_of))
        m["nav_latest"] = float(nav.iloc[-1])
        if len(nav) > 1:
            m["nav_prev"] = float(nav.iloc[-2]); m["nav_prev_date"] = nav.index[-2]
            m["nav_chg_1d"] = float(nav.iloc[-1] / nav.iloc[-2] - 1)
        m.setdefault("age_years", (nav.index[-1] - nav.index[0]).days / 365.25)
        m.setdefault("nav_date", nav.index[-1])
        m["code"] = r.code
        rows.append(m)
        if n % 200 == 0:
            log(f"  metrics {n}/{len(u)}")
    return pd.DataFrame(rows)


# ------------------------------------------------------------- period-wise ranking
def score_horizons(df: pd.DataFrame) -> pd.DataFrame:
    """For each horizon, rank every fund that has existed for the whole window (stale NAVs excluded)."""
    df = df.copy()
    for h in C.HORIZON_LIST:
        df[f"score_{h}"] = np.nan
        df[f"rank_{h}"] = np.nan
        df[f"peers_{h}"] = np.nan
        if f"excess_{h}" not in df.columns:
            continue
        # every fund that existed for the whole window is ranked (persistent-underperformer flags stay visible
        # next to the name; they cap the Overall tier, not what happened in a given period)
        elig = df[f"excess_{h}"].notna() & ~df["gate"].astype(str).str.startswith("stale")
        for (pg, plan), g in df[elig].groupby(["peer_group", "plan_type"]):
            sg = score_group(g, C.horizon_protocol(h, g.category.iloc[0]))
            df.loc[sg.index, f"score_{h}"] = sg["score"]
            df.loc[sg.index, f"rank_{h}"] = sg["score"].rank(ascending=False, method="min")
            df.loc[sg.index, f"peers_{h}"] = sg["score"].notna().sum()
    return df


# ------------------------------------------------------------- full ranking
def rank_universe(u, navs, tri, as_of=None, ter=None, aum=None, flags=None, holdings=None, log=print, liquid=None):
    as_of = pd.Timestamp(as_of) if as_of is not None else tri.index.max()
    u = assign_peers(u, tri)
    met = compute_metrics(u, navs, tri, as_of, log, liquid=liquid)
    df = u.drop(columns=["nav_date", "nav"], errors="ignore").merge(met, on="code", how="inner")
    if ter is not None:
        df = df.merge(ter[[c for c in ("code", "ter", "ter_date", "ter_base") if c in ter.columns]], on="code", how="left")
    if aum is not None:
        key = "code" if "code" in aum.columns else "pair_key"
        df = df.merge(aum[[key, "aum_cr"] + (["aum_asof"] if "aum_asof" in aum.columns else [])], on=key, how="left")
        df["aum_capacity_penalty"] = df["aum_cr"]
        df["aum_size"] = df["aum_cr"].clip(upper=C.ARB_AUM_CAP)
    if holdings is not None and len(holdings):
        df = df.merge(holdings, on="pair_key", how="left")
        # arbitrage funds hold stocks hedged with futures: the stock list (and active share, market-cap mix,
        # mandate checks) says nothing about their risk, so it is not used or shown
        hc = [c for c in holdings.columns if c != "pair_key" and c in df.columns]
        df.loc[df["category"].eq("Arbitrage"), hc] = np.nan

    # gates
    df["gate"] = "ok"
    stale = (as_of - pd.to_datetime(df["nav_date"])).dt.days > C.STALE_NAV_DAYS
    df.loc[stale, "gate"] = "stale NAV (merged/wound up?)"
    age = df.age_years.fillna(0)
    young_active = (df.category != "Index Fund") & (age < C.MIN_HISTORY_YEARS_ACTIVE)
    young_index = (df.category == "Index Fund") & (age < C.MIN_HISTORY_YEARS_INDEX)
    df.loc[young_active | young_index, "gate"] = "track record too short"

    # thin thematic buckets (by RATED funds) are pooled into "Thematic: Other Themes"
    th = df.category.eq("Sectoral/Thematic")
    rated = df[th & df.gate.eq("ok")].groupby(["peer_group", "plan_type"]).size()
    thin = {pg for (pg, pl), n in rated.items() if n < C.THEME_MIN_RATED}
    df.loc[th & df.peer_group.isin(thin), "peer_group"] = "Thematic: Other Themes"

    scored = []
    for (pg, plan), g in df.groupby(["peer_group", "plan_type"]):
        ok = g[g.gate == "ok"]
        rest = g[g.gate != "ok"].copy()
        proto_name, proto = C.protocol_for(g.category.iloc[0])
        if len(ok):
            ok = assign_tiers(score_group(ok, proto))
        rest["tier"] = "Unrated"
        part = pd.concat([ok, rest])
        part["protocol"] = proto_name
        scored.append(part)
    out = pd.concat(scored, ignore_index=True)
    out = score_horizons(out)
    if flags is not None:   # manual / qualitative-agent flags (manager exit, SEBI action, merger)
        f = flags.groupby("code")["flag"].apply(list)
        out["manual_flags"] = out["code"].map(f)
        hit = out["manual_flags"].notna()
        out.loc[hit & out.tier.isin(["A+", "A"]), "tier"] = "Watch"
    out["as_of"] = as_of.date().isoformat()
    return out.sort_values(["category", "peer_group", "plan_type", "score"], ascending=[True, True, True, False])


# ------------------------------------------------------------- outputs
DISPLAY_COLS = ["code", "name", "amc", "asset_class", "category", "peer_group", "plan_type", "benchmark", "bench_type",
                "tier", "score", "peer_rank", "peer_count", "flags", "gate", "guard_capped", "nav_date", "nav_latest", "nav_prev", "nav_prev_date", "nav_chg_1d", "ter_date", "age_years",
                "cagr_1y", "cagr_3y", "cagr_5y", "excess_cagr_3y", "excess_cagr_5y",
                "roll3y_excess_median", "roll3y_hit_rate", "roll3y_excess_p10", "roll1y_hit_rate",
                "info_ratio_3y", "sortino_3y", "downside_capture_3y", "upside_capture_3y",
                "max_drawdown_5y", "max_drawdown_3y", "excess_cagr_1y", "capture_ratio_3y", "alpha_3y", "sharpe_3y", "vol_3y", "beta_3y", "tracking_diff_1y", "tracking_err_1y",
                "tracking_diff_3y", "ter", "ter_base", "aum_cr", "aum_asof",
                "roll1y_excess_median", "neg_months_3y", "liq_cagr_1y", "liq_cagr_3y", "excess_vs_liquid_1y", "excess_vs_liquid_3y",
                "excess_vs_liquid_post_tax_1y", "excess_vs_liquid_post_tax_3y",
                "n_stocks", "top10_pct", "effective_n", "equity_pct", "cash_other_pct", "large_pct", "mid_pct",
                "small_pct", "beyond500_pct", "top_sector", "top_sector_pct", "active_share", "active_share_basis",
                "turnover_1m", "mandate_ok", "mandate_breaches", "holdings_month", "coverage", "pair_key", "protocol", "as_of"]


def data_meta(holdings_month=None, tri_date=None):
    """Dataset-level 'as of' labels shown in the dashboard."""
    rd = lambda f: (C.MANUAL / f).read_text().strip() if (C.MANUAL / f).exists() else None
    return {"nav_source": "AMFI daily NAV (via mfapi.in)", "tri_date": str(tri_date)[:10] if tri_date is not None else None,
            "holdings_month": holdings_month, "aum_period": rd("aum.period.txt"), "mcap_period": rd("amfi_mcap.period.txt"),
            "ter_source": "AMFI TER disclosure (latest revision per scheme)"}


def write_outputs(out: pd.DataFrame, folder, holdings_top=None, meta=None):
    folder.mkdir(parents=True, exist_ok=True)
    extra = [c for c in out.columns if c.startswith(("hist3y_", "flow_")) or c == "aum_1y_ago_cr"]
    hz = extra + [c for c in out.columns if re.match(r"^(ret|excess|ir|dcap|mdd|hit|te|sortino|score|rank|peers)_(6M|1Y|3Y|5Y)$", c)]
    cols = [c for c in DISPLAY_COLS if c in out.columns] + [c for c in out.columns if c.startswith("pillar_")] + hz
    o = out[cols].copy()
    o["flags"] = o["flags"].map(lambda f: ", ".join(f) if isinstance(f, list) else "")
    o.to_csv(folder / "rankings.csv", index=False)
    with pd.ExcelWriter(folder / "rankings.xlsx") as xw:
        for cat, g in o.groupby("category"):
            g.to_excel(xw, sheet_name=cat.replace("/", "-")[:31], index=False)
    # compact JSON for the dashboard
    j = o.replace([np.inf, -np.inf], np.nan).astype(object).where(o.notna(), None)
    recs = []
    for r in j.to_dict("records"):
        recs.append({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    payload = {"as_of": o.as_of.iloc[0], "horizons": C.HORIZON_LIST, "recommended": C.RECOMMENDED_HORIZON,
               "funds": recs, "holdings": holdings_top or {}, "meta": meta or {}}
    (folder / "rankings.json").write_text(json.dumps(payload, default=str, allow_nan=False))
    return folder
