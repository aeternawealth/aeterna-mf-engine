"""v5 search: more variables, models that retrain every year, per-category versions. Monthly panel, equity categories.

New variables, all built from each fund's own monthly returns over its benchmark up to the rating date (no look-ahead):
  hit12        share of the last 12 months the fund beat its benchmark
  ir12         average monthly excess over the last 12 months divided by its variability (a 1-year information ratio)
  vol12        variability of the monthly excess, last 12 months
  worst3_12    worst 3-month excess inside the last 12 months
  streak       months in a row ahead of the benchmark
  rank12       average peer-group percentile of the monthly excess, last 12 months (how steadily it ranks high)
  mom12_1      12-month momentum without the latest month;  mom6_1 likewise for 6 months
  accel        3-month momentum minus a quarter of the 12-month momentum (is it speeding up)
  hit36, ir36  the same over 36 months

Models. Each is refitted at the start of every test year on all data whose 1-year outcome was known by then
(expanding window), so the model that rates funds in 2023 has learned from 2012-2021:
  lean        fixed v4 weights, nothing fitted
  ridge       one linear model for all equity funds
  ridge_cat   a linear model per category
  gbm         gradient-boosted trees for all funds, with the category and the market state as inputs, so it can learn
              different rules per category and per market phase while sharing data
  gbm_cat     gradient-boosted trees per category
  lean+gbm    the average of the lean rank and the gbm rank; lean+ridge likewise
Target in every fit: the fund's percentile within its peer group on return over the benchmark in the next 12 months.

Reported for 2019-01..2025-09 (the months with a known 1-year outcome), never used to fit the model that rates them:
  fund   share of A+ funds (top 10% of the peer group) ahead of the benchmark over the next year
  basket share of months in which the A+ funds, held together in equal amounts for the next year, beat the benchmark
         (the 'buy the A+ funds, review after a year' use)
  peers  share of A+ funds ahead of the typical fund in their category over the next year"""
import sys; sys.path.insert(0, '.')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

BASE = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual',
        'style_n50', 'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y',
        'sortino_3y', 'beta_3y', 'vol_3y', 'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate',
        'roll1y_excess_median', 'roll3y_excess_median', 'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
NEW = ['hit12', 'ir12', 'vol12', 'worst3_12', 'streak', 'rank12', 'mom12_1', 'mom6_1', 'accel', 'hit36', 'ir36']
SIG = BASE + NEW
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']

M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
M = M[M.cat.isin(CATS)].sort_values(['code', 'as_of']).reset_index(drop=True)
G = ['as_of', 'cat']
# each fund's excess return in the month that ENDED at the rating date = the previous row's 'next month' return
g = M.groupby('code')
gap_ok = (M.as_of - g.as_of.shift(1)).dt.days.between(27, 32)
M['r'] = g.fwd_1m.shift(1).where(gap_ok)
M['p_r'] = M.groupby(G).r.rank(pct=True)
roll = lambda col, n, fn, mp: M.groupby('code')[col].transform(lambda s: getattr(s.rolling(n, min_periods=mp), fn)())
M['hit12'] = M.assign(x=(M.r > 0).where(M.r.notna()).astype(float)).groupby('code').x.transform(lambda s: s.rolling(12, min_periods=9).mean())
M['hit36'] = M.assign(x=(M.r > 0).where(M.r.notna()).astype(float)).groupby('code').x.transform(lambda s: s.rolling(36, min_periods=27).mean())
M['vol12'] = roll('r', 12, 'std', 9); M['ir12'] = roll('r', 12, 'mean', 9) / M.vol12
M['ir36'] = roll('r', 36, 'mean', 27) / roll('r', 36, 'std', 27)
M['r3'] = roll('r', 3, 'sum', 3); M['worst3_12'] = roll('r3', 10, 'min', 7)
M['rank12'] = roll('p_r', 12, 'mean', 9)
pos = (M.r > 0).astype(int); M['streak'] = pos.groupby([M.code, (pos != pos.groupby(M.code).shift()).cumsum()]).cumsum().where(M.r.notna())
M['mom12_1'] = M.mom_12m - M.mom_1m; M['mom6_1'] = M.mom_6m - M.mom_1m; M['accel'] = M.mom_3m - M.mom_12m / 4

M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in SIG: M['p_' + s] = M.groupby(G)[s].rank(pct=True)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
P = lambda f: M['p_' + f].fillna(.5)
X = pd.concat([P(s) for s in SIG], axis=1); X.columns = SIG
M['s_lean'] = .5 * (X.mom_1m + X.mom_3m + X.mom_6m + X.mom_12m) / 4 + .3 * (X.style_small + X.style_mid) / 2 + .2 * X.upside_capture_3y
catd = pd.get_dummies(M.cat).astype(float); mk = M[['mkt_12m', 'mkt_above_200d']].astype(float).fillna(0)
XG = pd.concat([X, catd, mk], axis=1)
for k in ('ridge', 'ridge_cat', 'gbm', 'gbm_cat'): M['s_' + k] = np.nan
YEARS = range(2019, 2027)
for Y in YEARS:
    tr = (M.as_of <= pd.Timestamp(f'{Y - 1}-01-01') - pd.Timedelta(days=1)) & M.p_fwd.notna()      # outcome known before year Y
    te = M.as_of.dt.year == Y
    if not te.any(): continue
    M.loc[te, 's_ridge'] = Ridge(alpha=50).fit(X[tr], M.p_fwd[tr]).predict(X[te])
    gb = HistGradientBoostingRegressor(max_depth=3, max_iter=200, learning_rate=0.04, min_samples_leaf=60, l2_regularization=1.0, random_state=0)
    M.loc[te, 's_gbm'] = gb.fit(XG[tr], M.p_fwd[tr]).predict(XG[te])
    for c in CATS:
        a, b = tr & (M.cat == c), te & (M.cat == c)
        if not b.any(): continue
        if a.sum() < 400: M.loc[b, 's_ridge_cat'] = M.loc[b, 's_ridge']; M.loc[b, 's_gbm_cat'] = M.loc[b, 's_gbm']; continue
        M.loc[b, 's_ridge_cat'] = Ridge(alpha=50).fit(X[a], M.p_fwd[a]).predict(X[b])
        gc = HistGradientBoostingRegressor(max_depth=2, max_iter=120, learning_rate=0.04, min_samples_leaf=40, l2_regularization=1.0, random_state=0)
        M.loc[b, 's_gbm_cat'] = gc.fit(X[a], M.p_fwd[a]).predict(X[b])
T = M[(M.as_of >= '2019-01-01')].copy()
rk = lambda col: T.groupby(G)[col].rank(pct=True)
T['s_lean+gbm'] = (rk('s_lean') + rk('s_gbm')) / 2; T['s_lean+ridge'] = (rk('s_lean') + rk('s_ridge')) / 2
MODELS = ['lean', 'ridge', 'ridge_cat', 'gbm', 'gbm_cat', 'lean+gbm', 'lean+ridge']
for k in MODELS: T['r_' + k] = T.groupby(G)['s_' + k].rank(pct=True)
T['med'] = T.groupby(G).fwd_1y.transform('median')
rows = []
for c in CATS + ['ALL']:
    d = T if c == 'ALL' else T[T.cat == c]
    for k in MODELS:
        ap = d[(d['r_' + k] >= .9) & d.fwd_1y.notna()]; cc = d[(d['r_' + k] <= .3) & d.fwd_1y.notna()]
        bk = ap.groupby(['as_of', 'cat']).fwd_1y.mean()
        rows.append(dict(category=c, model=k, fund=(ap.fwd_1y > 0).mean(), basket=(bk > 0).mean(), peers=(ap.fwd_1y > ap.med).mean(), c_fund=(cc.fwd_1y > 0).mean(),
                         aplus_excess=ap.fwd_1y.mean(), basket_months=len(bk), fund3y=(d[d['r_' + k] >= .9].fwd_3y.dropna() > 0).mean(),
                         base=(d.fwd_1y.dropna() > 0).mean()))
R = pd.DataFrame(rows); R.to_csv('audit/research_v5_results.csv', index=False)
pd.set_option('display.width', 250)
for m, title in (('fund', 'A+ funds ahead of the benchmark next year'), ('basket', 'A+ basket held a year beats the benchmark (share of months)'),
                 ('peers', 'A+ funds ahead of the typical fund in the category next year'), ('aplus_excess', 'average A+ return over the benchmark, next year'),
                 ('c_fund', 'bottom 30% ahead of the benchmark next year')):
    print(f'\n=== unseen 2019-25: {title} ==='); print(R.pivot(index='category', columns='model', values=m)[MODELS].round(3).to_string())
print('\nall funds ahead of the benchmark next year (base rate):'); print(R[R.model == 'lean'].set_index('category').base.round(3).to_string())
# which variables matter most: rank IC on unseen years, all equity
ic = {s: T[['as_of', 'p_' + s, 'p_fwd']].dropna().groupby('as_of').apply(lambda g: g['p_' + s].corr(g.p_fwd)).mean() for s in SIG}
I = pd.Series(ic).sort_values(key=abs, ascending=False); I.to_csv('audit/research_v5_signal_ic.csv')
print('\nvariables by strength on unseen years (rank IC, all equity; * = new):'); print(', '.join(f"{'*' if s in NEW else ''}{s} {v:+.3f}" for s, v in I.items()))
