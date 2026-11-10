"""Large & Mid Cap: core recipe, comprehensive model, and a 50/50 blend of the two (by rank), walk-forward.
The comprehensive model is a ridge regression on the 31 measures, refitted each year on all equity funds with a known
1-year outcome before that year (as in research_final.py). The after-fall blend is applied to all three."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge

SIG = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual', 'style_n50',
       'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y', 'sortino_3y', 'beta_3y', 'vol_3y',
       'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate', 'roll1y_excess_median', 'roll3y_excess_median',
       'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'}); M = M[M.cat.isin(CATS)].copy()
RF = .065; M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y; M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
X = pd.concat([M.groupby(G)[s].rank(pct=True).fillna(.5) for s in SIG], axis=1); X.columns = SIG
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
mom = (X.mom_1m + X.mom_3m + X.mom_6m + X.mom_12m) / 4; size = (X.style_small + X.style_mid) / 2
base = .55 * mom + .30 * X.upside_capture_3y + .15 * size
reb = .30 * X.upside_capture_3y + .25 * X.beta_3y + .20 * X.style_val + .25 * size
fall = M.mkt_above_200d == 0
M['s_base'] = np.where(fall, .5 * base + .5 * reb, base)
M['s_comp'] = np.nan
for Y in range(2013, 2027):
    tr = (M.as_of < pd.Timestamp(f'{Y - 1}-01-01')) & M.p_fwd.notna(); te = M.as_of.dt.year == Y
    if tr.sum() < 2000 or not te.any(): continue
    M.loc[te, 's_comp'] = Ridge(alpha=50).fit(X[tr], M.p_fwd[tr]).predict(X[te])
rk = lambda col: M.groupby(G)[col].rank(pct=True)
M['s_comp'] = np.where(fall, .5 * rk('s_comp') + .5 * reb, rk('s_comp'))
M['s_blend'] = .5 * rk('s_base') + .5 * rk('s_comp')
for k in ('base', 'comp', 'blend'): M['r_' + k] = rk('s_' + k)
T = M[M.s_comp.notna() & (M.as_of >= '2015-01-01')]
rows = []
for c in CATS + ['ALL']:
    for era, m in (('2015-18', T.as_of <= '2018-12-31'), ('2019-25', T.as_of > '2018-12-31')):
        d = T[m & ((T.cat == c) if c != 'ALL' else True)]; row = dict(category=c, era=era, all_1y=(d.fwd_1y.dropna() > 0).mean())
        for k in ('base', 'comp', 'blend'):
            ap = d[d['r_' + k] >= .9]; row[k + '_1y'] = (ap.fwd_1y.dropna() > 0).mean(); row[k + '_3y'] = (ap.fwd_3y.dropna() > 0).mean()
        rows.append(row)
R = pd.DataFrame(rows); R.to_csv('audit/research_blend_lmc.csv', index=False)
pd.set_option('display.width', 250)
print(R.pivot(index='category', columns='era', values=['base_1y', 'comp_1y', 'blend_1y', 'base_3y', 'comp_3y', 'blend_3y', 'all_1y']).round(2).loc[CATS + ['ALL']].to_string())

# buying the top? A+ funds whose last 3 months were the very strongest in their group (top 5%) vs other A+ funds,
# and A+ funds rated when the market itself had run up the most (last 12 months in the top fifth of all months)
T = T.copy(); T['p3'] = T.groupby(G).mom_3m.rank(pct=True); hot = T.mkt_12m >= T.mkt_12m.quantile(.8)
ap = T[T.r_base >= .9]
f = lambda x: f"{(x.fwd_1y.dropna() > 0).mean():.2f} (n={x.fwd_1y.notna().sum()})"
print('\nA+ funds ahead next year: hottest 3 months (top 5%)', f(ap[ap.p3 >= .95]), ' | other A+', f(ap[ap.p3 < .95]))
print('A+ rated after the market\'s strongest 12 months (top fifth)', f(ap[hot]), ' | other months', f(ap[~hot]), ' | all funds after strongest 12 months', f(T[hot]))
print('average return over the index next year, A+ after the strongest 12 months:', round(ap[hot].fwd_1y.mean() * 100, 1), '% vs other months', round(ap[~hot].fwd_1y.mean() * 100, 1), '%')
