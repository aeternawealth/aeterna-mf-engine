"""Live-engine backtest: the production ranking code (engine.rank.rank_universe) run at every month-end from 2015 on
real data (AMFI NAVs from mfapi for Regular and Direct plans, NSE total-return indices from niftyindices.com, plus the
equity funds that later closed or merged), using only data up to each date. Runs on GitHub (the NSE site is not
reachable elsewhere).

    python audit/validate_live.py fetch          # data: TRI from 2008, NAVs, closed funds; month-end NAV/TRI files
    python audit/validate_live.py rate v7        # rate every month-end with that model (env AETERNA_EQUITY_MODEL)
Outputs (committed):
    audit/live/rated_<model>.csv.gz   per fund and month: tier, score, rank, market mode, every measure the engine computed
    audit/live/nav_me.csv.gz          month-end NAV per fund (forward returns, review-rule simulation)
    audit/live/tri_me.csv.gz          month-end TRI per index
    audit/live/funds.csv              fund list (category, plan, benchmark, open or closed)
Limits: today's expense ratios and AUM stand in for past ones (no history is published), holdings-based checks are not
applied to past months, and closed funds are only those mfapi still lists (about 15 active equity funds)."""
import os, sys, time
sys.path.insert(0, ".")
import multiprocessing as mp
from pathlib import Path

import pandas as pd

OUT = Path("audit/live")
START = "2015-01-31"


def fetch():
    from engine import config as C, ingest
    C.HISTORY_START = "01-Jan-2008"   # rolling 3-year windows over the last 3 years need 6 years before the first date
    tri = ingest.fetch_all_tri(print)
    chk = tri[["NIFTY 50", "NIFTY SMALLCAP 250"]].pct_change().corr().iloc[0, 1]
    assert chk < 0.98, f"index series look identical (corr {chk:.3f}): not real data"
    tri.to_csv(C.RAW / "tri.csv")
    navall = ingest.parse_navall(ingest.fetch_navall())
    u = ingest.build_universe(navall)
    eq = u[(u.asset_class == "Equity") & (u.category != "Index Fund")]
    ingest.fetch_navs(list(eq.code), log=print)
    os.system("python audit/fetch_dead.py")
    _month_end_files(tri)


def _universe():
    """Today's open equity funds plus the closed ones, in the engine's universe format."""
    from engine import config as C, ingest
    u = ingest.build_universe(ingest.parse_navall((C.RAW / "NAVAll.txt").read_text(encoding="utf-8")))
    u = u[(u.asset_class == "Equity") & (u.category != "Index Fund")].copy()
    u["status"] = "open"
    dm = pd.read_csv("audit/dead_meta.csv", parse_dates=["first", "last"])
    dm = dm[dm.category.notna() & (dm.category.map(lambda c: C.ASSET_CLASS.get(c, "Equity")) == "Equity") & (dm.category != "Index Fund")
            & (dm["last"] < pd.Timestamp.now() - pd.Timedelta(days=60)) & ~dm.code.isin(u.code)].copy()
    rows = []
    for r in dm.itertuples():
        p = Path(f"data/nav_dead/{r.code}.csv")
        if not p.exists(): continue
        d = pd.read_csv(p, parse_dates=["date"])
        direct = "direct" in r.name.lower()
        base = r.name.lower().replace("direct plan", "").replace("regular plan", "").replace("direct", "").replace("regular", "")
        rows.append(dict(code=int(r.code), isin="", name=r.name, plan="Direct Plan" if direct else "Regular Plan", option="Growth",
                         nav=float(d.nav.iloc[-1]), nav_date=d.date.iloc[-1], amc=r.amc, raw_category=r.raw_cat, category=r.category,
                         plan_type="Direct" if direct else "Regular", asset_class="Equity", tax="equity",
                         pair_key=f"{str(r.amc).lower().strip()}|{base.strip()}", status="closed"))
    return pd.concat([u, pd.DataFrame(rows)], ignore_index=True)


def _navs(u):
    from engine import config as C
    navs = {}
    for r in u.itertuples():
        p = (C.NAV_DIR if r.status == "open" else Path("data/nav_dead")) / f"{int(r.code)}.csv"
        if p.exists():
            navs[int(r.code)] = pd.read_csv(p, parse_dates=["date"])
    return navs


def _month_end_files(tri):
    OUT.mkdir(parents=True, exist_ok=True)
    u = _universe()
    navs = _navs(u)
    me = pd.DataFrame({c: d.set_index("date")["nav"].resample("ME").last() for c, d in navs.items()})
    me.to_csv(OUT / "nav_me.csv.gz", compression="gzip")
    tri.resample("ME").last().to_csv(OUT / "tri_me.csv.gz", compression="gzip")
    from engine.rank import assign_peers
    up = assign_peers(u, tri)
    up[["code", "name", "amc", "category", "peer_group", "plan_type", "benchmark", "pair_key", "status"]].to_csv(OUT / "funds.csv", index=False)
    print(f"month-end files: {me.shape[1]} funds, {len(me)} months; {int((u.status == 'closed').sum())} closed funds", flush=True)


KEEP = ["month", "code", "category", "peer_group", "plan_type", "benchmark", "tier", "score", "peer_rank", "peer_count", "flags",
        "market_mode", "guard_capped", "protocol", "ter", "aum_cr", "cagr_1y", "cagr_3y", "bench_cagr_3y", "mom_1m", "mom_3m", "mom_6m", "mom_12m",
        "style_small", "style_mid", "style_mom", "style_val", "style_lowvol", "style_qual", "style_n50", "upside_capture_3y", "downside_capture_3y",
        "capture_ratio_3y", "alpha_3y", "info_ratio_3y", "sharpe_3y", "sortino_3y", "beta_3y", "vol_3y", "tracking_err_3y", "excess_cagr_1y",
        "excess_cagr_3y", "excess_cagr_5y", "roll1y_hit_rate", "roll1y_excess_median", "roll3y_excess_median", "roll3y_hit_rate",
        "roll3y_excess_p10", "max_drawdown_3y", "max_drawdown_5y", "age_years"]
_W = {}


def _one(t):
    from engine.rank import rank_universe
    w = _W
    try:
        out = rank_universe(w["u"], w["navs"], w["tri"], as_of=t, ter=w["ter"], aum=w["aum"], log=lambda *a, **k: None)
    except Exception as e:
        print(f"  {t.date()} failed: {type(e).__name__}: {e}", flush=True)
        return None
    out = out[out["tier"].notna() & (out["gate"] == "ok")].copy()
    out["flags"] = out["flags"].map(lambda f: ",".join(f) if isinstance(f, list) else (f if isinstance(f, str) else ""))
    out["month"] = t.strftime("%Y-%m")
    out = out[[c for c in KEEP if c in out.columns]]
    out.to_csv(w["parts"] / f"{t.date()}.csv.gz", index=False, compression="gzip")
    return t


def rate(model, budget_min=300):
    from engine import config as C, ingest
    assert C.EQUITY_MODEL == model, (C.EQUITY_MODEL, model)
    tri = ingest.load_cached_tri()
    u = _universe()
    navs = _navs(u)
    parts = Path(os.environ.get("RUNNER_TEMP", "/tmp")) / f"parts_{model}"
    parts.mkdir(parents=True, exist_ok=True)
    idx = tri.dropna(how="all").index
    ends = pd.Series(idx, index=idx).groupby([idx.year, idx.month]).max()
    ends = [t for t in ends if t >= pd.Timestamp(START) and t < pd.Timestamp.now().normalize().replace(day=1)]
    todo = [t for t in ends if not (parts / f"{t.date()}.csv.gz").exists()]
    print(f"{model}: {len(todo)} of {len(ends)} month-ends to rate, {len(u)} funds ({int((u.status == 'closed').sum())} closed)", flush=True)
    _W.update(u=u.drop(columns=["status"]), navs=navs, tri=tri, ter=ingest.load_manual("ter"), aum=ingest.load_manual("aum"), parts=parts)
    t0 = time.time()
    with mp.get_context("fork").Pool(os.cpu_count() or 2) as pool:
        for n, t in enumerate(pool.imap_unordered(_one, todo), 1):
            if n % 10 == 0:
                print(f"  {n}/{len(todo)} months in {(time.time() - t0) / 60:.1f} min", flush=True)
            if time.time() - t0 > budget_min * 60:
                print("  time budget used: the rest on the next run", flush=True)
                pool.terminate(); break
    files = sorted(parts.glob("*.csv.gz"))
    allp = pd.concat([pd.read_csv(f, low_memory=False) for f in files], ignore_index=True)
    allp.to_csv(OUT / f"rated_{model}.csv.gz", index=False, compression="gzip")
    print(f"{model}: {len(files)} months, {len(allp)} fund-months -> {OUT}/rated_{model}.csv.gz", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "fetch":
        fetch()
    else:
        rate(sys.argv[2], float(os.environ.get("BUDGET_MIN", "150")))
