"""Pick a model per category from audit/live/compare_results.csv without fooling ourselves.
1. Drop models that use the expense ratio: only today's TER exists, and funds that did well grew and now charge less
   (SEBI's slabs), so today's TER leaks the past result into the test.
2. Drop candidates that are not usable: fewer than 6 different A+ funds after COVID, or months without any A+ fund.
3. Out-of-sample check: choose on one period, read the result on the other (pre-COVID -> post-COVID and back).
   If choosing per category does not beat the plain v7 setup out of sample, the extra choice is noise."""
import pandas as pd, numpy as np
pd.set_option("display.width", 250)
T = pd.read_csv("audit/live/compare_results.csv")
T = T[~T.model.isin(["low cost", "low cost + momentum", "crisil-style"])]
ok = (T.post_aplus_funds >= 6) & (T.post_cover >= .9) & (T.pre_cover.fillna(0) >= .8) & (T.pre_aplus_funds.fillna(0) >= 4)
U = T[ok].copy()
rows = []
for c, t in U.groupby("category"):
    v7 = T[(T.category == c) & (T.model == "engine v7") & (T.tiers == "engine tiers")]
    v3 = T[(T.category == c) & (T.model == "engine v3") & (T.tiers == "engine tiers")]
    a = t.loc[t.pre_core4.idxmax()]; b = t.loc[t.post_core4.idxmax()]
    rows.append(dict(category=c, pick_on_pre=f"{a.model} / {a['mode']} / {a.tiers}", its_post=a.post_core4,
                     pick_on_post=f"{b.model} / {b['mode']} / {b.tiers}", its_pre=b.pre_core4,
                     v7_pre=v7.pre_core4.iloc[0] if len(v7) else np.nan, v7_post=v7.post_core4.iloc[0] if len(v7) else np.nan,
                     v3_pre=v3.pre_core4.iloc[0] if len(v3) else np.nan, v3_post=v3.post_core4.iloc[0] if len(v3) else np.nan))
R = pd.DataFrame(rows)
print(R.round(2).to_string(index=False))
print("\nmean out-of-sample: chosen-on-pre ->post", round(R.its_post.mean(), 3), "| v7 post", round(R.v7_post.mean(), 3),
      "| chosen-on-post ->pre", round(R.its_pre.mean(), 3), "| v7 pre", round(R.v7_pre.mean(), 3))
# models that are good in BOTH periods: rank by the worse of the two
U["both"] = U[["pre_core4", "post_core4"]].min(axis=1)
print("\n=== per category: best on the weaker of the two periods (top 4) ===")
for c, t in U.groupby("category"):
    t = t.sort_values("both", ascending=False).head(4)
    print(f"\n{c}"); print(t[["model", "mode", "tiers", "both", "pre_core4", "post_core4", "post_aplus_1y", "post_per_fund_1y", "post_aplus_3y",
                           "post_review_1y", "post_review_3y", "post_worst_year", "post_aplus_funds", "post_aplus_n"]].round(2).to_string(index=False))
# a single model for every category: which family is best on average (out of sample in both periods)
F = U.groupby(["model", "mode", "tiers"]).agg(n=("category", "size"), pre=("pre_core4", "mean"), post=("post_core4", "mean"), both=("both", "mean"))
print("\n=== one setup for all categories (present in 9+ categories) ===")
print(F[F.n >= 9].sort_values("both", ascending=False).head(12).round(3).to_string())
