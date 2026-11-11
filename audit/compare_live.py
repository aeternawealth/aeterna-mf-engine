"""Every candidate model, in every equity category, on the live-engine backtest (audit/validate_live.py).

Inputs: audit/live/rated_{v3,v5,v7}.csv.gz (the production engine's ratings and measures at each month-end since 2015,
Regular and Direct plans, closed funds included), nav_me / tri_me (month-end NAV and index levels), funds.csv.

Outcome of a rating: the fund's return relative to its benchmark TRI over the next 12 and 36 months (a fund that
closed or merged earns the benchmark from its last NAV on, so its record up to closure counts). A rating is
'ahead' when that relative return is above zero.

Candidates
  engine runs, exactly as the engine rates: v3 (the live model), v5, v7
  scored here with the engine's percentile and weighting rules (protocols.score_group, vectorised):
    lean, core, mandate, quality, small-cap, multi-cap, comp (ridge regression on 31 measures, refitted every year on
    earlier years only, recent years weighted more), blend (core + comp), and three plain yardsticks people use:
    3-year return over the index, rolling 3-year record, Sharpe ratio
  each in a fixed mode and in market mode (half rebound criteria when the category's index is below its 200-day average)
Tier rules
  quota: A+ top 10% (at least 3 places in a group of 15+), A to 30%, C bottom 30%   (v7)
  threshold: A+ when the score is at or above a cut (75 / 80 / 85), A at or above 65 / 70; any number of funds
  v3 rules (with the 'ahead of the index' guard and red flags) come with the v3 engine run
Decision score per category (Regular and Direct averaged, post-COVID counted twice):
  mean of: A+ ahead after 1 year, A+ ahead after 3 years, review rule ahead after 1 year and after 3 years.
Writes audit/live/compare_results.csv and prints the table and the winner per category."""
import sys, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, ".")
import numpy as np
import pandas as pd

L = "audit/live/"
CATS = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value / Contra",
        "Dividend Yield", "Sectoral/Thematic"]
SIG = ["mom_1m", "mom_3m", "mom_6m", "mom_12m", "style_small", "style_mid", "style_mom", "style_val", "style_lowvol", "style_qual", "style_n50",
       "upside_capture_3y", "downside_capture_3y", "capture_ratio_3y", "alpha_3y", "info_ratio_3y", "sharpe_3y", "sortino_3y", "beta_3y", "vol_3y",
       "tracking_err_3y", "excess_cagr_1y", "excess_cagr_3y", "excess_cagr_5y", "roll1y_hit_rate", "roll1y_excess_median", "roll3y_excess_median",
       "roll3y_hit_rate", "roll3y_excess_p10", "max_drawdown_3y", "age_years"]
G = ["month", "peer_group", "plan_type"]

# ------------------------------------------------------------------ data
R = {m: pd.read_csv(f"{L}rated_{m}.csv.gz", low_memory=False) for m in ("v7", "v3", "v5", "v8") if __import__("os").path.exists(f"{L}rated_{m}.csv.gz")}
M = R["v7"].copy()
M["cat"] = M.category.replace({"Value": "Value / Contra", "Contra": "Value / Contra"})
M = M[M.cat.isin(CATS) & M.score.notna()].reset_index(drop=True)
M["t"] = pd.PeriodIndex(M.month, freq="M").to_timestamp("M")
M = M[M.groupby(G).code.transform("size") >= 5].reset_index(drop=True)
M["fall"] = M.market_mode.eq("after a fall")

nav = pd.read_csv(L + "nav_me.csv.gz", index_col=0, parse_dates=True)
tri = pd.read_csv(L + "tri_me.csv.gz", index_col=0, parse_dates=True)
nav.index = nav.index.to_period("M").to_timestamp("M"); tri.index = tri.index.to_period("M").to_timestamp("M")
fund_b = M.groupby("code").benchmark.agg(lambda x: x.mode().iloc[0])
rel = {}
for c, b in fund_b.items():
    if str(c) not in nav or b not in tri: continue
    s = nav[str(c)] / tri[b]
    last = s.last_valid_index()
    rel[c] = s.loc[:last].ffill().reindex(tri.index).ffill()   # after closure: earns the benchmark (relative level flat)
    rel[c][tri.index > tri[b].last_valid_index()] = np.nan
REL = pd.DataFrame(rel)
END = tri.index.max()


def fwd(h):
    f = REL.shift(-h) / REL - 1
    f[f.index > END - pd.DateOffset(months=h)] = np.nan
    return f.stack().rename(f"fwd_{h}")


F = pd.concat([fwd(1), fwd(12), fwd(36)], axis=1)
F.index.names = ["t", "code"]
M = M.merge(F.reset_index(), on=["t", "code"], how="left")
M["period"] = np.where(M.t <= "2020-02-29", "pre", np.where(M.t >= "2020-04-01", "post", "covid"))
print(f"panel: {len(M)} fund-months, {M.code.nunique()} funds, {M.month.min()}..{M.month.max()}; "
      f"1y outcome known for {M.fwd_12.notna().mean():.0%}", flush=True)

M["selectivity_3y"] = M.tracking_err_3y / M.vol_3y     # Amihud & Goyenko (2013): low R-squared against the index -> this is high
M["vr_riskadj"] = M[["excess_cagr_3y", "excess_cagr_5y"]].mean(axis=1, skipna=True) + M.max_drawdown_3y.fillna(0) / 3   # VR-style: return less a fall penalty
# ------------------------------------------------------------------ engine percentiles (protocols._pct, per group)
grp = M.groupby(G)
P = {}
for s in SIG + ["ter", "selectivity_3y", "vr_riskadj"]:
    if s not in M: continue
    x = pd.to_numeric(M[s], errors="coerce")
    n = x.groupby([M[g] for g in G]).transform("count")
    r = x.groupby([M[g] for g in G]).rank(pct=True, method="average")
    P[s] = ((r * n - .5) / n * 100).where(n > 1, np.where(x.notna(), 50.0, np.nan))


def score(proto):
    """protocols.score_group: weighted mean of available percentiles; unrated below 50% coverage"""
    num = pd.Series(0.0, index=M.index); den = pd.Series(0.0, index=M.index); tot = 0
    for m, (w, hib) in proto.items():
        if m not in P or w <= 0: continue
        p = P[m] if hib else 100 - P[m]
        ok = p.notna(); num[ok] += p[ok] * w; den[ok] += w; tot += w
    return (num / den).where(den >= .5 * tot)


def size(cat):
    if cat == "Mid Cap": return {"style_small": (7.5, True), "style_n50": (7.5, False)}
    if cat == "Small Cap": return {"style_mid": (15, False)}
    if cat == "Multi Cap": return {"style_n50": (15, False)}
    return {"style_small": (7.5, True), "style_mid": (7.5, True)}


mom = lambda ms, w: {f"mom_{m}m": (w / len(ms), True) for m in ms}
PROTO = {
    "lean": lambda c: {**mom((1, 3, 6, 12), 50), "style_small": (15, True), "style_mid": (15, True), "upside_capture_3y": (20, True)},
    "core": lambda c: {**mom((1, 3, 6, 12), 55), "upside_capture_3y": (30, True), **size(c)},
    "quality": lambda c: {**mom((1, 3, 6, 12), 45), "upside_capture_3y": (20, True), "info_ratio_3y": (10, True), "capture_ratio_3y": (10, True), **size(c)},
    "small-cap": lambda c: {**mom((1, 3), 50), "beta_3y": (20, True), "age_years": (15, False), **size(c)},
    "multi-cap": lambda c: {**mom((3, 6, 12), 50), "upside_capture_3y": (35, True), **size(c)},
    "mandate": lambda c: {
        "Large Cap": {**mom((1, 3, 6), 50), "upside_capture_3y": (35, True)},
        "Large & Mid Cap": {**mom((3, 6), 45), "upside_capture_3y": (25, True), "style_val": (15, True)},
        "Mid Cap": {**mom((3, 6, 12), 55), "upside_capture_3y": (30, True)},
        "Small Cap": {**mom((1, 3), 50), "beta_3y": (20, True), "age_years": (15, False)},
        "Flexi Cap": {**mom((6, 12), 45), "upside_capture_3y": (20, True), "info_ratio_3y": (10, True), "capture_ratio_3y": (10, True)},
        "Multi Cap": {**mom((3, 6, 12), 50), "upside_capture_3y": (35, True)},
        "Focused": {**mom((3, 6), 40), "tracking_err_3y": (25, True), "upside_capture_3y": (20, True)},
        "ELSS": {**mom((1, 3, 6, 12), 45), "upside_capture_3y": (25, True), "tracking_err_3y": (15, True)},
        "Value / Contra": {"style_val": (35, True), **mom((3, 6), 35), "upside_capture_3y": (15, True)},
    }.get(c, {**mom((1, 3, 6, 12), 55), "upside_capture_3y": (30, True)}) | size(c),
    "3y return": lambda c: {"excess_cagr_3y": (1, True)},
    "rolling 3y record": lambda c: {"roll3y_excess_median": (15, True), "roll3y_hit_rate": (10, True)},
    "sharpe": lambda c: {"sharpe_3y": (1, True)},
    # published approaches (approximations from the measures the engine computes)
    "morningstar-style risk-adj": lambda c: {"sortino_3y": (50, True), "excess_cagr_3y": (25, True), "excess_cagr_5y": (25, True)},
    "valueresearch-style": lambda c: {"vr_riskadj": (1, True)},
    "crisil-style": lambda c: {"info_ratio_3y": (30, True), "excess_cagr_3y": (25, True), "downside_capture_3y": (20, False),
                               "max_drawdown_3y": (10, True), "ter": (15, False)},
    "low cost": lambda c: {"ter": (1, False)},
    "low cost + momentum": lambda c: {"ter": (40, False), **mom((3, 6, 12), 60)},
    "selectivity (low R2)": lambda c: {"selectivity_3y": (50, True), "alpha_3y": (50, True)},
    "alpha persistence": lambda c: {"alpha_3y": (1, True)},
    "information ratio": lambda c: {"info_ratio_3y": (1, True)},
    "conviction + momentum": lambda c: {"tracking_err_3y": (40, True), **mom((3, 6, 12), 60)},
    "downside protection": lambda c: {"downside_capture_3y": (50, False), "max_drawdown_3y": (30, True), "capture_ratio_3y": (20, True)},
    "consistency": lambda c: {"roll1y_hit_rate": (50, True), "roll3y_hit_rate": (50, True)},
    "momentum 12m": lambda c: {"mom_12m": (1, True)},
    "momentum 6m": lambda c: {"mom_6m": (1, True)},
    "momentum 1-12m": lambda c: mom((1, 3, 6, 12), 100),
    "momentum + upside": lambda c: {**mom((1, 3, 6, 12), 60), "upside_capture_3y": (40, True)},
    "value tilt": lambda c: {"style_val": (1, True)},
    "value + momentum": lambda c: {"style_val": (40, True), **mom((3, 6, 12), 60)},
    "value + quality": lambda c: {"style_val": (40, True), "style_qual": (30, True), "info_ratio_3y": (30, True)},
    "quality tilt": lambda c: {"style_qual": (50, True), "capture_ratio_3y": (50, True)},
    "low volatility": lambda c: {"style_lowvol": (50, True), "vol_3y": (50, False)},
    "momentum-stock tilt": lambda c: {"style_mom": (50, True), **mom((6, 12), 50)},
    "size + momentum": lambda c: {**size(c), **mom((1, 3, 6, 12), 50), "beta_3y": (20, True)},
    "high beta": lambda c: {"beta_3y": (1, True)},
    # the momentum + defence ensemble as one weighted score (how the engine would run it)
    "momentum + defence (one score)": lambda c: {**{k: (w / 3, h) for k, (w, h) in {**mom((1, 3, 6, 12), 55), "upside_capture_3y": (30, True), **size(c)}.items()},
                                                 "downside_capture_3y": (50 / 3, False), "max_drawdown_3y": (30 / 3, True),
                                                 "capture_ratio_3y": (70 / 3, True), "style_qual": (50 / 3, True)},
}
REB = lambda c: {"upside_capture_3y": (30, True), "beta_3y": (25, True), "style_val": (20, True), **{k: (v[0] / 15 * 25, v[1]) for k, v in size(c).items()}}

SC = {}
for k, f in PROTO.items():
    s = pd.Series(np.nan, index=M.index)
    for c in CATS:
        m = M.cat == c
        s[m] = score(f(c))[m]
    SC[k] = s
reb = pd.Series(np.nan, index=M.index)
for c in CATS:
    reb[M.cat == c] = score(REB(c))[M.cat == c]

# comp: ridge on the 31 percentiles, refitted each January on data whose 1-year outcome was known by then
from sklearn.linear_model import Ridge
X = pd.DataFrame({s: P[s] / 100 for s in SIG if s in P}).fillna(.5)
yp = M.groupby(G).fwd_12.rank(pct=True)
comp = pd.Series(np.nan, index=M.index)
for Y in range(2017, 2027):
    tr = (M.t < pd.Timestamp(f"{Y - 1}-01-01")) & yp.notna(); te = M.t.dt.year == Y
    if tr.sum() < 3000 or not te.any(): continue
    w = 0.5 ** ((Y - 1 - M.t[tr].dt.year) / 3)
    comp[te] = Ridge(alpha=50).fit(X[tr], yp[tr], sample_weight=w).predict(X[te])
SC["comp"] = comp.groupby([M[g] for g in G]).rank(pct=True) * 100
SC["blend"] = (SC["core"].groupby([M[g] for g in G]).rank(pct=True) * 50 + SC["comp"] / 2)

GR = lambda x: x.groupby([M[g] for g in G]).rank(pct=True) * 100
SC["ensemble (6 styles)"] = sum(GR(SC[k]) for k in ("core", "small-cap", "quality", "value + momentum", "low volatility", "quality tilt")) / 6
SC["ensemble (momentum + defence)"] = sum(GR(SC[k]) for k in ("core", "downside protection", "quality tilt")) / 3
SC["ensemble (momentum + value + quality)"] = sum(GR(SC[k]) for k in ("small-cap", "value + quality", "momentum + upside")) / 3
for m in ("v3", "v5", "v7", "v8"):   # engine runs: their own scores and tiers
    if m in R:
        e = R[m][["month", "code", "score", "tier"]].rename(columns={"score": f"s_{m}", "tier": f"t_{m}"})
        M = M.drop(columns=[c for c in e.columns if c not in ("month", "code") and c in M]).merge(e, on=["month", "code"], how="left")


# ------------------------------------------------------------------ tiers
def quota(s):
    df = pd.DataFrame({"s": s}).join(M[G])
    df = df[df.s.notna()]
    n = df.groupby(G).s.transform("size"); pos = df.groupby(G).s.rank(ascending=False, method="first")
    k = np.maximum(np.ceil(.1 * n), np.where(n >= 15, 3, 1)); k30 = np.maximum(k, np.ceil(.3 * n))
    t = np.where(pos <= k, "A+", np.where(pos <= k30, "A", np.where(pos > n - np.floor(.3 * n), "C", "B")))
    return pd.Series(t, index=df.index).reindex(M.index)


def thresh(s, ap, a):
    pr = s.groupby([M[g] for g in G]).rank(pct=True)
    t = np.where(s >= ap, "A+", np.where(s >= a, "A", np.where(pr <= .3, "C", "B")))
    return pd.Series(t, index=M.index).where(s.notna())


def review(tier, mask):
    """new money each month to the A+ funds (equal amounts); a fund is kept while A+ or A, replaced once rated B or C
    after 12 months held. Result after 12 / 36 months, relative to the benchmark (above 1 = ahead)."""
    d = M.loc[mask, ["t", "code", "fwd_1"]].assign(tt=tier[mask])
    TT = {t: dict(zip(g.code, g.tt)) for t, g in d.groupby("t")}
    RR = {t: dict(zip(g.code, g.fwd_1)) for t, g in d.groupby("t")}
    ds = sorted(TT); o12, o36 = {}, {}
    for i0, t0 in enumerate(ds):
        lots, cash = [], 1.0
        for j in range(36):
            if i0 + j >= len(ds): break
            t = ds[i0 + j]; tt, rr = TT[t], RR[t]; keep = []
            for code, v, age in lots:
                if code not in tt or (age >= 12 and tt[code] in ("B", "C")): cash += v
                else: keep.append([code, v, age])
            lots = keep
            ap = [x for x, y in tt.items() if y == "A+"]
            if cash > 0 and ap:
                lots += [[x, cash / len(ap), 0] for x in ap]; cash = 0.0
            ok = False
            for lot in lots:
                x = rr.get(lot[0], np.nan)
                if np.isfinite(x): lot[1] *= 1 + x; ok = True
                lot[2] += 1
            if ok and j == 11: o12[t0] = cash + sum(l[1] for l in lots)
            if ok and j == 35: o36[t0] = cash + sum(l[1] for l in lots)
    return (pd.Series(o12, dtype=float, index=pd.DatetimeIndex(list(o12))), pd.Series(o36, dtype=float, index=pd.DatetimeIndex(list(o36))))


def evaluate(tier, c):
    out = {}
    for plan in ("Regular", "Direct"):
        mk = (M.cat == c) & (M.plan_type == plan)
        if mk.sum() < 200: continue
        r12, r36 = review(tier, mk)
        d = M[mk].assign(tt=tier[mk])
        for p in ("pre", "post"):
            dp = d[d.period == p]
            per = (lambda s: s[pd.DatetimeIndex(s.index) <= pd.Timestamp("2020-02-29")]) if p == "pre" else (lambda s: s[pd.DatetimeIndex(s.index) >= pd.Timestamp("2020-04-01")])
            ap = dp[dp.tt == "A+"]
            o = dict(aplus_1y=(ap.fwd_12.dropna() > 0).mean(), aplus_3y=(ap.fwd_36.dropna() > 0).mean(),
                     aplus_ex1y=ap.fwd_12.mean(), review_1y=(per(r12) > 1).mean(), review_3y=(per(r36) > 1).mean(),
                     all_1y=(dp.fwd_12.dropna() > 0).mean(), all_3y=(dp.fwd_36.dropna() > 0).mean(),
                     aplus_fall_1y=(ap[ap.fall].fwd_12.dropna() > 0).mean() if ap.fall.any() else np.nan, aplus_n=ap.groupby("t").size().mean() if len(ap) else 0,
                     **{f"{t}_1y": (dp[dp.tt == t].fwd_12.dropna() > 0).mean() for t in ("A", "B", "C")})
            o["core4"] = np.nanmean([o[k] for k in ("aplus_1y", "aplus_3y", "review_1y", "review_3y")])
            # robustness: how many different funds, how many months had any A+, the worst year, and the hit rate
            # counted once per fund (so one fund held A+ for years does not count as many independent picks)
            ok = ap[ap.fwd_12.notna()]
            o["aplus_funds"] = ok.code.nunique()
            o["cover"] = ap.t.nunique() / max(1, dp.t.nunique())
            yr = ok.groupby(ok.t.dt.year).fwd_12.agg(lambda x: (x > 0).mean())
            o["worst_year"] = yr[ok.groupby(ok.t.dt.year).size() >= 6].min() if len(yr) else np.nan
            o["per_fund_1y"] = ok.groupby("code").fwd_12.agg(lambda x: (x > 0).mean()).mean() if len(ok) else np.nan
            out[(plan, p)] = o
    yrs = {}
    for plan in ("Regular", "Direct"):
        mk = (M.cat == c) & (M.plan_type == plan) & (tier == "A+") & M.fwd_12.notna()
        for y, x in M[mk].groupby(M.t[mk].dt.year).fwd_12:
            yrs.setdefault(y, []).append((x > 0).mean())
    out["years"] = {y: float(np.mean(v)) for y, v in yrs.items()}
    dec = [(out[(pl, "pre")]["core4"] + 2 * out[(pl, "post")]["core4"]) / 3 for pl in ("Regular", "Direct") if (pl, "pre") in out]
    return out, float(np.nanmean(dec)) if dec else np.nan


rows, YRS = [], []
def quota20(s):
    t = quota(s); pr = s.groupby([M[g] for g in G]).rank(ascending=False, pct=True)
    return t.where(~((pr <= .2) & t.isin(["A"])), "A+")


def union(s, ap, a):
    """the quota, and on top of it any fund whose score clears the cut: never empty, never capped"""
    q, t = quota(s), thresh(s, ap, a)
    r = q.copy()
    r[(t == "A") & r.isin(["B", "C"])] = "A"
    r[t == "A+"] = "A+"
    return r


RULES = {"quota": quota, "quota+75/65": lambda s: union(s, 75, 65), "quota+80/70": lambda s: union(s, 80, 70), "quota+70/60": lambda s: union(s, 70, 60), "top 20%": quota20, "A+70/A60": lambda s: thresh(s, 70, 60), "A+80/A70": lambda s: thresh(s, 80, 70), "A+75/A65": lambda s: thresh(s, 75, 65), "A+85/A70": lambda s: thresh(s, 85, 70)}
import os
ONLY = [x for x in os.environ.get("ONLY", "").split("|") if x]
for c in CATS:
    cands = {}
    for k, s in SC.items():
        cands[(k, "fixed")] = s
        cands[(k, "market mode")] = np.where(M.fall, (s + reb.fillna(s)) / 2, s)
    for m in ("v3", "v5", "v7", "v8"):
        if f"s_{m}" in M: cands[(f"engine {m}", "as run")] = M[f"s_{m}"]
    if "s_v8" in M and "s_v3" in M:   # hedge: the momentum model with part of the old quality model, by place in the group
        r8, r3 = GR(M.s_v8), GR(M.s_v3)
        for w in (.9, .8, .7, .6, .5):
            cands[(f"v8 {int(w * 100)} / v3 {int(100 - w * 100)}", "as run")] = (w * r8 + (1 - w) * r3.fillna(r8)).where(M.s_v8.notna())
    if ONLY: cands = {kk: v for kk, v in cands.items() if kk[0] in ONLY}
    for (k, mode), s in cands.items():
        s = pd.Series(s, index=M.index).where(M.cat == c)
        rules = dict(RULES)
        if k.startswith("engine"):
            rules["engine tiers"] = lambda _s, m=k[-2:]: M[f"t_{m}"].where(M[f"t_{m}"].isin(["A+", "A", "B", "C"]))
        for rn, rf in rules.items():
            out, dec = evaluate(rf(s), c)
            if not out: continue
            YRS.extend(dict(category=c, model=k, mode=mode, tiers=rn, year=y, aplus_1y=v) for y, v in out.pop("years").items())
            kk = [k for k in out if isinstance(k, tuple)]
            po = {k2: np.nanmean([out[(pl, "post")][k2] for pl in ("Regular", "Direct") if (pl, "post") in out]) for k2 in out[kk[0]]}
            pr = {k2: np.nanmean([out[(pl, "pre")][k2] for pl in ("Regular", "Direct") if (pl, "pre") in out]) for k2 in out[kk[0]]}
            rows.append(dict(category=c, model=k, mode=mode, tiers=rn, decision=dec, **{"post_" + a: b for a, b in po.items()},
                             **{"pre_" + a: b for a, b in pr.items()}))
    print(f"  {c} done", flush=True)
T = pd.DataFrame(rows)
T.to_csv(L + os.environ.get("OUTNAME", "compare_results.csv"), index=False)
pd.DataFrame(YRS).to_csv(L + os.environ.get("OUTNAME", "compare_results.csv").replace("results", "years"), index=False)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
cols = ["model", "mode", "tiers", "decision", "post_aplus_1y", "post_aplus_3y", "post_review_1y", "post_review_3y", "post_all_1y",
        "post_aplus_n", "pre_aplus_1y", "pre_review_3y"]
for c in CATS:
    t = T[T.category == c].sort_values("decision", ascending=False)
    print(f"\n=== {c}: top 8 of {len(t)} (and the live model) ===")
    show = pd.concat([t.head(8), t[(t.model == "engine v3") & (t.tiers == "engine tiers")]])
    print(show[cols].round(3).to_string(index=False))
