"""Aeterna MF Engine - monthly run (pure Python, no AI tokens).

    python run_monthly.py                    # full run: data + AMC portfolios + ranking + dashboard
    python run_monthly.py --no-download      # skip AMC portfolio downloads (use files already in data/holdings)
    python run_monthly.py --offline          # reuse cached data only, no internet
    python run_monthly.py --backtest         # also run walk-forward validation (~5-10 min)
Results: outputs/<YYYY-MM>/dashboard.html, rankings.xlsx, rankings.csv, run_log.txt
"""
import argparse
import sys
from datetime import datetime

import pandas as pd

from engine import config as C
from engine import ingest

LOG = []


def log(msg=""):
    print(msg, flush=True)
    LOG.append(str(msg))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--no-download", action="store_true")
    ap.add_argument("--daily", action="store_true",
                    help="weekday-morning refresh: new NAVs/index -> returns & period ranks; Overall tiers frozen from the last monthly run")
    ap.add_argument("--fresh-tiers", action="store_true",
                    help="with --daily: re-rate Overall tiers today instead of keeping the monthly snapshot (model changes on staging)")
    ap.add_argument("--history", action="store_true",
                    help="with --daily: also fill and update the monthly rating history (the monthly run always does)")
    ap.add_argument("--backtest", action="store_true")
    ap.add_argument("--as-of", default=None)
    ap.add_argument("--holdings-month", default=None, help="YYYY-MM (default: previous calendar month)")
    a = ap.parse_args()
    from engine.rank import assign_peers, rank_universe, write_outputs
    from engine import holdings as H, dashboard

    log(f"Aeterna MF Engine run {datetime.now():%Y-%m-%d %H:%M}")
    log("[1/7] Universe (AMFI NAVAll)")
    text = (C.RAW / "NAVAll.txt").read_text(encoding="utf-8") if a.offline else ingest.fetch_navall()
    navall = ingest.parse_navall(text)
    u = ingest.build_universe(navall)
    log(f"  {len(u)} equity + index schemes (growth, Direct & Regular)")

    if not a.offline and not a.daily:
        log("[2/7] AMFI extras: TER, AUM, market-cap list")
        from engine import extras
        extras.run_all(u, log, navall)

    if a.daily and not a.offline:   # month-end AUM changes once a month; the call is cheap, so check every day
        from engine import extras
        try:
            extras.fetch_aum(u, log, navall, quarterly=False)
        except Exception as e:
            log(f"  AUM refresh failed: {type(e).__name__}: {str(e)[:160]}")

    log("[3/7] Benchmarks (Nifty TRI)")
    tri = ingest.load_cached_tri() if a.offline else ingest.fetch_all_tri(log)

    log("[4/7] NAV history (mfapi)")
    liq = ingest.liquid_universe(navall)   # yardstick for arbitrage and equity savings funds, not ranked
    bnd = ingest.liquid_universe(navall, C.BOND_CATEGORY_KEYS)   # bond-fund yardstick for the other hybrid composites
    codes = list(u.code) + [c for c in pd.concat([liq.code, bnd.code]).unique() if c not in set(u.code)]
    navs = ingest.load_cached_navs(codes) if a.offline else ingest.fetch_navs(codes, log=log)
    log(f"  {len(navs)} NAV histories ({len(liq)} of them liquid funds, the arbitrage yardstick)")
    ingest.top_up_from_navall(navs, pd.concat([u, liq, bnd], ignore_index=True), log)
    liquid = ingest.liquid_yardstick(navs, liq, as_of=tri.index.max())
    bond = ingest.liquid_yardstick(navs, bnd, as_of=tri.index.max())
    log(f"  bond-fund yardstick: {', '.join(f'{k} {len(v)} days' for k, v in bond.items()) or 'none'} ({len(bnd)} plans)")
    log(f"  liquid-fund yardstick: {', '.join(f'{k} {len(v)} days' for k, v in liquid.items()) or 'none'}")

    hmonth = a.holdings_month or (pd.Period(datetime.now(), "M") - 1).strftime("%Y-%m")
    log(f"[5/7] Holdings for {hmonth}")
    if a.daily:   # use the latest month that has holdings on disk
        done = sorted(p.name for p in (C.DATA / "holdings").glob("20??-??") if (p / "holdings_valid.csv").exists())
        hmonth = done[-1] if done else hmonth
        log(f"  daily mode: re-using holdings of {hmonth}")
    if not a.daily:
        H.merge_inbox(hmonth, log=log)   # files uploaded from the office PC for AMCs that block GitHub
    if not (a.offline or a.no_download or a.daily):
        try:
            from engine import amc_downloader
            amc_downloader.run(hmonth, log=log)
        except Exception as e:
            log(f"  downloader failed: {type(e).__name__}: {e}")
    up = assign_peers(u, tri)
    hold = H.load_cached(hmonth) if a.daily else pd.DataFrame()
    before = H.load_cached(hmonth) if not a.daily else pd.DataFrame()   # a re-run must not lose portfolios already parsed
    if not len(hold):
        hold = H.analyse(hmonth, up, prev_month=(pd.Period(hmonth) - 1).strftime("%Y-%m"), log=log)
    if not a.daily:   # AMCs publish by the 10th and some late: never rate on fewer holdings than last month
        hold, hmonth = H.with_fallback(hold, hmonth, log=log, same_month=before)
        if len(hold):
            hold = H.add_prev_mandate(hold, hmonth)   # two-month rule for the mandate cap
            H.save_cached(hold, hmonth)   # the daily refresh re-uses exactly this set

    log("[6/7] Metrics, protocols, ranking committee")
    out = rank_universe(u, navs, tri, as_of=a.as_of, ter=ingest.load_manual("ter"),
                        aum=ingest.load_manual("aum"), flags=ingest.load_manual("flags"), holdings=hold, log=log, liquid=liquid, bond=bond)
    from engine import flows as FL
    if not (a.offline or a.daily):
        try:
            FL.fetch_latest(log)
        except Exception as e:
            log(f"  flows fetch failed: {type(e).__name__}")
    fl = FL.compute(u, navall, navs)
    if len(fl):
        out = out.merge(fl, on="pair_key", how="left")
    month = "latest" if a.daily else (pd.Timestamp(a.as_of) if a.as_of else tri.index.max()).strftime("%Y-%m")
    snap = C.OUT / "ratings_snapshot.csv"
    keep = ["code", "tier", "score", "peer_rank", "peer_count", "flags", "guard_capped"] + [c for c in out.columns if c.startswith("pillar_")]
    if a.daily and snap.exists() and not a.fresh_tiers:   # Overall rating changes only monthly
        s0 = pd.read_csv(snap)
        # a category with no fund in the snapshot is new (added since the last monthly run): rate it today
        # instead of showing every fund Unrated until the next monthly run
        rated_cats = set(out.loc[out["code"].isin(s0["code"]), "category"])
        fresh = out[~out["category"].isin(rated_cats)]
        if len(fresh):
            log(f"  new categories rated today (not in the monthly snapshot): {', '.join(sorted(fresh.category.unique()))}")
        out = out[out["category"].isin(rated_cats)]
        out = out.drop(columns=[c for c in keep if c != "code" and c in out.columns]).merge(s0, on="code", how="left")
        out["tier"] = out["tier"].fillna("Unrated")
        out["flags"] = out["flags"].map(lambda f: f.split(", ") if isinstance(f, str) and f else [])
        out = pd.concat([out, fresh], ignore_index=True)
    elif not a.daily:
        o = out[[c for c in keep if c in out.columns]].copy()
        o["flags"] = o["flags"].map(lambda f: ", ".join(f) if isinstance(f, list) else "")
        C.OUT.mkdir(parents=True, exist_ok=True); o.to_csv(snap, index=False)
    from engine.rank import data_meta
    folder = write_outputs(out, C.OUT / month, holdings_top=hold.attrs.get("top") if len(hold) else None,
                           meta=data_meta(hmonth if len(hold) else None, tri.index.max()))
    if not a.daily or a.history:   # monthly rating history and the reasons behind each change, for the fund pages
        from engine import history as RH
        try:
            hist = RH.update(u, navs, tri, current=out if (not a.daily or a.fresh_tiers) else None, log=log, liquid=liquid, bond=bond,
                             ter=ingest.load_manual("ter"), aum=ingest.load_manual("aum"), budget_min=15 if a.daily else 45)
            n = RH.site_json(hist, folder / "rating_history.json")
            log(f"  rating history: {hist['month'].nunique()} months, {n} funds")
        except Exception as e:   # the history is a display feature: never fail the ratings run for it
            log(f"  rating history failed: {type(e).__name__}: {e}")
    dash = dashboard.build(folder)
    if not a.daily:   # the website always reads outputs/latest
        import shutil
        shutil.copytree(folder, C.OUT / "latest", dirs_exist_ok=True)
    log(f"  wrote {folder}")
    log(out.groupby(["category", "tier"]).size().unstack(fill_value=0).to_string())

    if a.backtest:
        log("[7/7] Walk-forward backtest")
        from engine.backtest import run_backtest
        bt = run_backtest(up, navs, tri, log=log)
        bt.to_csv(folder / "backtest.csv", index=False)
        log(bt.drop(columns="as_of").mean().round(3).to_string())

    (folder / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")
    log(f"\nDONE. Open: {dash}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
