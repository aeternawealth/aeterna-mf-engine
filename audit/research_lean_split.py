"""The lean (v4) model on unseen years 2019-26: 1-year and 3-year results for each equity category."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'}); M = M[M.cat.isin(CATS)]
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
P = lambda f: M.groupby(G)[f].rank(pct=True).fillna(.5)
M['s'] = .5 * (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4 + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')
M['r'] = M.groupby(G).s.rank(pct=True); T = M[M.as_of >= '2019-01-01']
rows = []
for c in CATS + ['ALL']:
    d = T if c == 'ALL' else T[T.cat == c]; ap = d[d.r >= .9]; a2 = d[d.r >= .7]; cc = d[d.r <= .3]
    row = dict(category=c)
    for h, col in (('1y', 'fwd_1y'), ('3y', 'fwd_3y')):
        x = ap[col].dropna(); bk = ap.dropna(subset=[col]).groupby(['as_of', 'cat'])[col].mean()
        row.update({f'aplus_fund_{h}': (x > 0).mean(), f'aplus_basket_{h}': (bk > 0).mean(), f'a_or_better_{h}': (a2[col].dropna() > 0).mean(),
                    f'c_fund_{h}': (cc[col].dropna() > 0).mean(), f'all_funds_{h}': (d[col].dropna() > 0).mean(), f'aplus_avg_excess_{h}': x.mean(), f'months_{h}': bk.index.get_level_values(0).nunique()})
    rows.append(row)
R = pd.DataFrame(rows).set_index('category'); R.to_csv('audit/research_lean_split.csv')
pd.set_option('display.width', 250)
print(R[[c for c in R if c.endswith('1y')]].round(3).to_string()); print(); print(R[[c for c in R if c.endswith('3y')]].round(3).to_string())
