"""Walk-forward model selection: would 'use the best model so far' have worked, live?

For each year Y, pick using only results known by 1 January of Y (ratings up to Y-2; ratings made in Y-1 do not
have their 1-year outcome yet), then score the pick on the ratings made in Y (share of A+ funds ahead of the
benchmark 12 months later, Regular and Direct averaged). Strategies:
  per category   each category takes its own best candidate so far
  one for all    the single setup with the best average across categories so far
  fixed          a setup decided once (v3 live, v7, and the strongest simple setups)
Candidates: those in compare_results.csv without the expense ratio (today's TER leaks the past) and usable
(6+ different A+ funds after COVID, A+ funds in 90%+ of months)."""
import numpy as np, pandas as pd
pd.set_option("display.width", 250)
T = pd.read_csv("audit/live/compare_results.csv"); Y = pd.read_csv("audit/live/compare_years.csv")
K = ["model", "mode", "tiers"]
bad = T.model.isin(["low cost", "low cost + momentum", "crisil-style"])
use = T[~bad & (T.post_aplus_funds >= 6) & (T.post_cover >= .9) & (T.pre_cover.fillna(0) >= .8)][["category"] + K]
Y = Y.merge(use, on=["category"] + K)
Y["key"] = Y.model + " / " + Y["mode"] + " / " + Y.tiers
P = Y.pivot_table(index=["category", "year"], columns="key", values="aplus_1y")
years = [y for y in range(2018, 2026)]
res = {}
for y in years:
    past = P[P.index.get_level_values("year") <= y - 2]
    now = P[P.index.get_level_values("year") == y].droplevel("year")
    if now.empty: continue
    # per category
    pc = past.groupby(level="category").mean()
    per = [now.loc[c, pc.loc[c].idxmax()] for c in now.index if c in pc.index and pc.loc[c].notna().any()]
    # one for all: best average across categories (categories weighted equally)
    allbest = pc.mean().idxmax()
    res[y] = {"per category (best so far)": np.nanmean(per), "one for all (best so far)": np.nanmean(now[allbest]), "_pick": allbest}
    for k in P.columns:
        res[y][k] = np.nanmean(now[k])
R = pd.DataFrame(res).T
picks = R.pop("_pick")
R = R.astype(float)
show = ["per category (best so far)", "one for all (best so far)"] + [k for k in R.columns if k.startswith("engine")] + \
       [k for k in R.mean().sort_values(ascending=False).index if not k.startswith("engine") and "so far" not in k][:12]
out = R[show].T
out["mean"] = R[show].mean(); out["worst year"] = R[show].min(axis=1); out["2021-25"] = R.loc[R.index >= 2021, show].mean()
print(out.round(2).to_string())
print("\none-for-all pick each year:"); print(picks.to_string())
