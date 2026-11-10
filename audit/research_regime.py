"""Does the small/mid-cap tilt in the ratings fail when large caps lead, and can that be seen in advance?

Market regime from the panel itself: at each month-end, the median trailing 1-year return of Small Cap funds minus
that of Large Cap funds (positive = small caps led over the last year). The 'next-year regime' is the same spread
measured 12 months later, i.e. over the year the rating is judged on.

For the categories where managers choose their size mix (Flexi, Multi, Focused, ELSS, Value / Contra, Large Cap,
Large & Mid Cap) and both eras together, reported by regime:
  - the rank correlation of the size tilt with the next year's return over the benchmark,
  - share of A+ funds ahead of the benchmark next year for: lean (with size tilt), the same without the size tilt
    (momentum + upside capture), and a version whose size tilt is switched off when large caps led over the last
    6 months (known at the time)."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
spread = M[M.cat.isin(['Small Cap', 'Large Cap'])].groupby(['as_of', 'cat']).cagr_1y.median().unstack()
S = (spread['Small Cap'] - spread['Large Cap']).rename('trail_12m')
# 6-month version from 6-month momentum is not raw; use the change in the 12-month spread as a quicker read
S6 = S - S.shift(6)
F = S.shift(-12).rename('next_12m')                     # the spread over the following year
R = pd.concat([S, S6.rename('trail_chg6'), F], axis=1)
FREE = ['Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra', 'Large Cap', 'Large & Mid Cap']
M = M[M.cat.isin(FREE)].copy(); G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'upside_capture_3y']: M['p_' + s] = M.groupby(G)[s].rank(pct=True).fillna(.5)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
M = M.merge(R, left_on='as_of', right_index=True, how='left')
mom = (M.p_mom_1m + M.p_mom_3m + M.p_mom_6m + M.p_mom_12m) / 4; size = (M.p_style_small + M.p_style_mid) / 2
M['s_lean'] = .5 * mom + .3 * size + .2 * M.p_upside_capture_3y
M['s_nosize'] = (.5 * mom + .2 * M.p_upside_capture_3y) / .7
M['s_switch'] = np.where(M.trail_12m < 0, M.s_nosize, M.s_lean)          # size tilt off when large caps led over the last year
for k in ('lean', 'nosize', 'switch'): M['r_' + k] = M.groupby(G)['s_' + k].rank(pct=True)
M['size'] = size
print('months by regime (next 12 months):', (R.next_12m > 0).sum(), 'small caps led,', (R.next_12m < 0).sum(), 'large caps led')
print('years when large caps led over the next 12 months, by start month:',
      ', '.join(sorted({str(d.year) for d in R.index[R.next_12m < 0]})))


def ic(d, col):
    x = d[['as_of', col, 'p_fwd']].dropna()
    r = x.groupby('as_of').apply(lambda g: g[col].corr(g.p_fwd) if len(g) >= 5 else np.nan).dropna()
    return r.mean()


rows = []
for lab, m in (('next year: small caps led', M.next_12m > 0), ('next year: large caps led', M.next_12m < 0),
               ('last year: small caps led', M.trail_12m > 0), ('last year: large caps led', M.trail_12m < 0)):
    d = M[m & M.fwd_1y.notna()]
    row = dict(regime=lab, months=d.as_of.nunique(), size_tilt_ic=ic(d, 'size'))
    for k in ('lean', 'nosize', 'switch'):
        ap = d[d['r_' + k] >= .9].fwd_1y; row['aplus_' + k] = (ap > 0).mean()
    row['all_funds'] = (d.fwd_1y > 0).mean(); rows.append(row)
T = pd.DataFrame(rows); T.to_csv('audit/research_regime.csv', index=False)
pd.set_option('display.width', 220); print(T.round(3).to_string(index=False))
print('\ncorrelation between last year\'s spread and next year\'s spread:', round(R.trail_12m.corr(R.next_12m), 2))

# how much size tilt: the trade-off between small-cap-led and large-cap-led years
print('\nsize-tilt weight: A+ ahead next year (small caps led / large caps led / all years)')
for w in (0, .1, .15, .2, .3):
    sc = (.5 * mom + w * size + .2 * M.p_upside_capture_3y) / (.7 + w); M['r_w'] = sc.groupby([M.as_of, M.cat]).rank(pct=True)
    a = lambda m: (M[m & (M.r_w >= .9) & M.fwd_1y.notna()].fwd_1y > 0).mean()
    print(f'  {int(w * 100):>2}%:  {a(M.next_12m > 0):.3f} / {a(M.next_12m < 0):.3f} / {a(M.next_12m.notna()):.3f}')
