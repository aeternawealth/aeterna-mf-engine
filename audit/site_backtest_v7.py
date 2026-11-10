"""site/model_backtest.json for the Method page: the v7 package as built (each category's model, market mode on, no
index cap), from audit/research_final2_noguard.csv (GUARD=0 run of audit/research_final2.py)."""
import json, pandas as pd
R = pd.read_csv('audit/research_final2_noguard.csv')
PICK = {'Large Cap': 'core', 'Large & Mid Cap': 'comp', 'Mid Cap': 'core', 'Small Cap': 'mandate', 'Flexi Cap': 'core', 'Multi Cap': 'mandate',
        'Focused': 'core', 'ELSS': 'core', 'Value / Contra': 'core'}
NAME = {'core': 'core', 'comp': 'comprehensive', 'mandate': {'Small Cap': 'small-cap', 'Multi Cap': 'multi-cap'}}
out = {'periods': {'pre': 'Jan 2012 - Feb 2020', 'post': 'Apr 2020 - Oct 2025'}, 'categories': {}}
for c, k in PICK.items():
    r = R[(R.category == c) & (R.model == k) & (R['mode'] == 'market mode')].iloc[0]
    f = lambda x: None if pd.isna(x) else round(float(x), 3)
    out['categories'][c] = {'model': NAME[k][c] if isinstance(NAME[k], dict) else NAME[k],
        **{p: {'tiers': {t: f(r[f'{p}_{"aplus" if t == "A+" else t}_1y']) for t in ('A+', 'A', 'B', 'C')}, 'all_1y': f(r[f'{p}_all_1y']), 'all_3y': f(r[f'{p}_all_3y']),
               'aplus_3y': f(r[f'{p}_aplus_3y']), 'review_1y': f(r[f'{p}_review_1y']), 'review_3y': f(r[f'{p}_review_3y']), 'aplus_per_month': f(r[f'{p}_aplus_per_month'])} for p in ('pre', 'post')},
        'stress': {'large_led': f(r.large_led), 'all_large_led': f(r.all_large_led), 'after_fall': f(r.after_fall), 'after_hot': f(r.after_hot)}}
json.dump(out, open('site/model_backtest.json', 'w'), separators=(',', ':'))
for c, v in out['categories'].items(): print(f"{c:16} {v['model']:14} post A+ {v['post']['tiers']['A+']} A {v['post']['tiers']['A']} B {v['post']['tiers']['B']} C {v['post']['tiers']['C']} all {v['post']['all_1y']}  A+3y {v['post']['aplus_3y']} rev1 {v['post']['review_1y']} rev3 {v['post']['review_3y']}")
