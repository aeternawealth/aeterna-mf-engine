"""site/model_backtest.json for the Method page: the v8 package as the production engine rated it at every month-end
(audit/validate_live.py -> rated_v8.csv.gz; outcomes from audit/compare_live.py, Regular and Direct averaged)."""
import json, pandas as pd
R = pd.read_csv("audit/live/compare_results_v8.csv")
R = R[(R.model == "engine v8") & (R.tiers == "engine tiers")]
NAME = {"Large & Mid Cap": "all-rounder", "Mid Cap": "mid-cap", "Small Cap": "small-cap", "Multi Cap": "momentum and defence", "Focused": "conviction"}
f = lambda x: None if pd.isna(x) else round(float(x), 3)
out = {"periods": {"pre": "Jun 2018 - Feb 2020", "post": "Apr 2020 - Oct 2025"}, "plans": "Regular and Direct", "engine": "v8", "categories": {}}
for _, r in R.iterrows():
    c = r.category
    if c == "Dividend Yield": continue
    out["categories"][c] = {"model": NAME.get(c, "core"),
        **{p: {"tiers": {t: f(r[f"{p}_{'aplus' if t == 'A+' else t}_1y"]) for t in ("A+", "A", "B", "C")}, "all_1y": f(r[f"{p}_all_1y"]),
               "all_3y": f(r[f"{p}_all_3y"]), "aplus_3y": f(r[f"{p}_aplus_3y"]), "review_1y": f(r[f"{p}_review_1y"]), "review_3y": f(r[f"{p}_review_3y"]),
               "aplus_per_month": f(r[f"{p}_aplus_n"]), "cover": f(r[f"{p}_cover"])} for p in ("pre", "post")},
        "stress": {"after_fall": f(pd.Series([r.pre_aplus_fall_1y, r.post_aplus_fall_1y]).mean())}}
json.dump(out, open("site/model_backtest.json", "w"), separators=(",", ":"))
for c, v in out["categories"].items():
    print(f"{c:18} {v['model']:20} post A+ {v['post']['tiers']['A+']} A {v['post']['tiers']['A']} B {v['post']['tiers']['B']} C {v['post']['tiers']['C']} all {v['post']['all_1y']} A+3y {v['post']['aplus_3y']} all3y {v['post']['all_3y']} rev1 {v['post']['review_1y']} rev3 {v['post']['review_3y']} n {v['post']['aplus_per_month']} cover {v['post']['cover']} fall {v['stress']['after_fall']}")
