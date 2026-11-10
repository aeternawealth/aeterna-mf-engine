"""Diagnosis of the lean model per equity category, for the review before any change.

1. Which inputs exist per category (the mid-cap tilt is undefined for Mid Cap funds, whose benchmark is the
   Midcap 150 itself; the small-cap tilt likewise for Small Cap).
2. Signal strength per category: the average monthly rank correlation between a signal and the next year's return
   over the benchmark, in 2012-18 and in 2019-25 separately. 'Stable' = same sign and at least 0.05 in both.
3. Ablation on 2019-25: share of A+ funds ahead of the benchmark over the next year for momentum alone, momentum +
   upside capture, momentum + size tilt, and the full lean model. Nothing here is fitted."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

SIG = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_n50', 'style_mom', 'style_val', 'style_lowvol', 'style_qual',
       'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y', 'sortino_3y', 'beta_3y', 'vol_3y',
       'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate', 'roll3y_hit_rate', 'roll3y_excess_median',
       'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'}); M = M[M.cat.isin(CATS)]
RF = .065; M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y; M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in SIG: M['p_' + s] = M.groupby(G)[s].rank(pct=True)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
M['era'] = np.where(M.as_of <= '2018-12-31', '2012-18', '2019-25')

print('=== 1. share of funds with each lean input defined ===')
print(M.groupby('cat')[['mom_12m', 'style_small', 'style_mid', 'upside_capture_3y']].apply(lambda g: g.notna().mean()).round(2).loc[CATS].to_string())


def ic(d, s):
    x = d[['as_of', 'p_' + s, 'p_fwd']].dropna()
    r = x.groupby('as_of').apply(lambda g: g['p_' + s].corr(g.p_fwd) if len(g) >= 5 else np.nan).dropna()
    return r.mean() if len(r) >= 12 else np.nan


rows = []
for c in CATS:
    for s in SIG:
        a, b = ic(M[(M.cat == c) & (M.era == '2012-18')], s), ic(M[(M.cat == c) & (M.era == '2019-25')], s)
        rows.append(dict(cat=c, sig=s, ic_2012_18=a, ic_2019_25=b, stable=bool(np.isfinite([a, b]).all() and np.sign(a) == np.sign(b) and min(abs(a), abs(b)) >= .05)))
I = pd.DataFrame(rows); I.to_csv('audit/research_diagnose_ic.csv', index=False)
print('\n=== 2. signals with the same sign and |IC| >= 0.05 in both 2012-18 and 2019-25, per category ===')
for c in CATS:
    d = I[(I.cat == c) & I.stable].copy(); d['m'] = (d.ic_2012_18 + d.ic_2019_25) / 2; d = d.sort_values('m', key=abs, ascending=False)
    print(f'{c:16}', ', '.join(f"{r.sig} {r.ic_2012_18:+.2f}/{r.ic_2019_25:+.2f}" for r in d.itertuples()) or '(none)')

P = lambda f: M['p_' + f].fillna(.5)
mom = (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4; size = (P('style_small') + P('style_mid')) / 2
V = {'momentum only': mom, 'mom + upside': .7 * mom + .3 * P('upside_capture_3y'), 'mom + size': .6 * mom + .4 * size,
     'lean (mom+size+upside)': .5 * mom + .3 * size + .2 * P('upside_capture_3y'), 'size only': size}
T = M.era == '2019-25'; out = []
for k, sc in V.items():
    M['r'] = sc.groupby([M.as_of, M.cat]).rank(pct=True)
    for c in CATS:
        d = M[T & (M.cat == c)]; ap = d[d.r >= .9].fwd_1y.dropna(); out.append(dict(cat=c, model=k, aplus_1y=(ap > 0).mean(), all_1y=(d.fwd_1y.dropna() > 0).mean()))
A = pd.DataFrame(out)
print('\n=== 3. 2019-25: A+ funds ahead of the benchmark next year, by which inputs are used ===')
t = A.pivot(index='cat', columns='model', values='aplus_1y').loc[CATS, list(V)]; t['all funds'] = A.groupby('cat').all_1y.first().loc[CATS]; print(t.round(3).to_string())
