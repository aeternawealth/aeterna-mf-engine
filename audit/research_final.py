"""The model for each equity category: lean or comprehensive, tested over 1 and 3 years and with a holding rule.

Candidates
  lean      fixed weights: momentum over 1, 3, 6, 12 months 50, small- and mid-cap tilt 30, upside capture 20
  comp_cat  comprehensive, per category: a linear model on all 31 measures, fitted on that category's own history
  comp_all  comprehensive, pooled: the same linear model fitted on every equity fund
Both comprehensive models are refitted at the start of each year on everything whose 1-year outcome was known by
then, so each rating in 2019-25 comes from a model that had not seen that year (walk-forward).

Reported per category for ratings dated 2019-01 onwards:
  fund 1y / 3y    share of A+ funds (top 10% of the peer group) ahead of the benchmark over the next 1 / 3 years
  basket 1y / 3y  share of months in which the A+ funds bought together beat the benchmark over the next 1 / 3 years
  hold 1y / 3y    the holding rule: buy the A+ funds; after a fund has been held 12 months (exit load over) check it
                  each month and move it to the current A+ funds once it is rated below A (outside the top 30%); the
                  share of start months in which the portfolio is ahead of the benchmark after 1 / 3 years. No costs
                  or tax are charged.
Choice: for each category the model with the best average of fund 1y, basket 1y and hold 1y; lean wins ties within one
point. The winner's weights for live use are then fitted on all the history (audit/equity_models.json).
Because the choice is made on the same years the results are read from, the chosen model's figures are a little
flattering; the lean column is the fairer guide to what to expect."""
import sys, json; sys.path.insert(0, '.')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge

SIG = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual',
       'style_n50', 'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y',
       'sortino_3y', 'beta_3y', 'vol_3y', 'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate',
       'roll1y_excess_median', 'roll3y_excess_median', 'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
MODELS = ['lean', 'comp_cat', 'comp_all']; ALPHA = 50

M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
M = M[M.cat.isin(CATS)].copy(); G = ['as_of', 'cat']
RF = 0.065
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y; M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
X = pd.concat([M.groupby(G)[s].rank(pct=True).fillna(.5) for s in SIG], axis=1); X.columns = SIG
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
M['s_lean'] = .5 * (X.mom_1m + X.mom_3m + X.mom_6m + X.mom_12m) / 4 + .3 * (X.style_small + X.style_mid) / 2 + .2 * X.upside_capture_3y
M['s_comp_cat'] = np.nan; M['s_comp_all'] = np.nan
for Y in range(2019, 2027):
    tr = (M.as_of < pd.Timestamp(f'{Y - 1}-01-01')) & M.p_fwd.notna(); te = M.as_of.dt.year == Y
    if not te.any(): continue
    M.loc[te, 's_comp_all'] = Ridge(alpha=ALPHA).fit(X[tr], M.p_fwd[tr]).predict(X[te])
    for c in CATS:
        a, b = tr & (M.cat == c), te & (M.cat == c)
        if b.any(): M.loc[b, 's_comp_cat'] = Ridge(alpha=ALPHA).fit(X[a], M.p_fwd[a]).predict(X[b]) if a.sum() >= 400 else M.loc[b, 's_comp_all']
T = M[M.as_of >= '2019-01-01'].copy()
for k in MODELS: T['r_' + k] = T.groupby(G)['s_' + k].rank(pct=True)
dates = sorted(T.as_of.unique())


def hold(c, k):
    """The holding rule for one category and model: relative value after 12 and 36 months, for every start month."""
    d = T[T.cat == c]; rk = {t: dict(zip(g.code, g['r_' + k])) for t, g in d.groupby('as_of')}; ret = {t: dict(zip(g.code, g.fwd_1m)) for t, g in d.groupby('as_of')}
    o12, o36 = [], []
    for i0 in range(len(dates)):
        lots, cash = [], 1.0                                    # lots: [code, value, months held]
        for j in range(36):
            if i0 + j >= len(dates): break
            t = dates[i0 + j]; r_t, x_t = rk.get(t, {}), ret.get(t, {})
            keep = []
            for code, v, age in lots:                           # review: only after 12 months, and only if it has fallen below A
                if code not in r_t or (age >= 12 and r_t[code] < .7): cash += v
                else: keep.append([code, v, age])
            lots = keep
            if cash > 0:
                ap = [code for code, r in r_t.items() if r >= .9]
                if ap:
                    for code in ap: lots.append([code, cash / len(ap), 0])
                    cash = 0.0
            for lot in lots:
                x = x_t.get(lot[0], np.nan)
                if np.isfinite(x): lot[1] *= 1 + x
                lot[2] += 1
            done = j + 1
            if done == 12 and np.isfinite(list(x_t.values())).any(): o12.append(cash + sum(l[1] for l in lots))
            if done == 36 and np.isfinite(list(x_t.values())).any(): o36.append(cash + sum(l[1] for l in lots))
    return (np.array(o12) > 1).mean() if o12 else np.nan, (np.array(o36) > 1).mean() if o36 else np.nan, len(o12), len(o36)


rows = []
for c in CATS:
    d = T[T.cat == c]
    for k in MODELS:
        ap = d[d['r_' + k] >= .9]; cc = d[d['r_' + k] <= .3]; row = dict(category=c, model=k)
        for h, col in (('1y', 'fwd_1y'), ('3y', 'fwd_3y')):
            x = ap[col].dropna(); bk = ap.dropna(subset=[col]).groupby('as_of')[col].mean()
            row[f'fund_{h}'] = (x > 0).mean(); row[f'basket_{h}'] = (bk > 0).mean(); row[f'c_fund_{h}'] = (cc[col].dropna() > 0).mean(); row[f'all_{h}'] = (d[col].dropna() > 0).mean()
        row['hold_1y'], row['hold_3y'], row['n_1y'], row['n_3y'] = hold(c, k)
        row['pick'] = np.mean([row['fund_1y'], row['basket_1y'], row['hold_1y']])
        rows.append(row)
R = pd.DataFrame(rows)
choice = {}
for c in CATS:
    d = R[R.category == c].set_index('model').pick; best = d.idxmax()
    choice[c] = 'lean' if d['lean'] >= d[best] - 0.01 else best
R['chosen'] = R.apply(lambda r: choice[r.category] == r.model, axis=1); R.to_csv('audit/research_final_results.csv', index=False)

# weights for live use: fitted on all history with a known 1-year outcome
known = M.p_fwd.notna(); out = {'fitted_to': str(M.as_of[known].max().date()), 'signals': SIG, 'categories': {}}
pooled = Ridge(alpha=ALPHA).fit(X[known], M.p_fwd[known]).coef_
for c in CATS:
    k = choice[c]
    if k == 'lean': out['categories'][c] = {'model': 'lean'}; continue
    co = pooled if k == 'comp_all' else Ridge(alpha=ALPHA).fit(X[known & (M.cat == c)], M.p_fwd[known & (M.cat == c)]).coef_
    tot = np.abs(co).sum(); out['categories'][c] = {'model': k, 'weights': {s: round(float(v / tot * 100), 2) for s, v in zip(SIG, co) if abs(v / tot) >= 0.005}}
json.dump(out, open('audit/equity_models.json', 'w'), indent=1)

pd.set_option('display.width', 250); f = lambda v: R.pivot(index='category', columns='model', values=v).loc[CATS, MODELS].round(3)
for v, t in (('fund_1y', 'A+ funds ahead of the benchmark, next 1 year'), ('basket_1y', 'A+ basket ahead, next 1 year'), ('hold_1y', 'holding rule ahead after 1 year'),
             ('fund_3y', 'A+ funds ahead, next 3 years'), ('basket_3y', 'A+ basket ahead, next 3 years'), ('hold_3y', 'holding rule ahead after 3 years'), ('c_fund_1y', 'bottom 30% ahead, next 1 year')):
    print(f'\n=== {t} ==='); print(f(v).to_string())
print('\nall funds ahead, 1 year / 3 years:'); print(R[R.model == 'lean'].set_index('category')[['all_1y', 'all_3y']].round(3).to_string())
print('\nchosen:', choice)
for c in CATS:
    w = out['categories'][c].get('weights')
    if w: print(f'\n{c} ({choice[c]}), weights fitted on all history:', ', '.join(f'{s} {v:+.1f}' for s, v in sorted(w.items(), key=lambda x: -abs(x[1]))[:14]))
CH = R[R.chosen].set_index('category').loc[CATS, ['model', 'fund_1y', 'basket_1y', 'hold_1y', 'fund_3y', 'basket_3y', 'hold_3y', 'all_1y', 'all_3y']]
print('\n=== the chosen model per category ==='); print(CH.round(3).to_string())

# ---- the Method page reads this: per category, the chosen model and how each rating did afterwards (walk-forward) ----
site = {'fitted_to': out['fitted_to'], 'tested_from': '2019-01', 'tested_to': str(T.as_of[T.fwd_1y.notna()].max().date())[:7], 'categories': {}}
for c in CATS:
    k = choice[c]; d = T[T.cat == c]; r = d['r_' + k]; row = R[(R.category == c) & (R.model == k)].iloc[0]
    tiers = {}
    for name, m in (('A+', r >= .9), ('A', (r >= .7) & (r < .9)), ('B', (r > .3) & (r < .7)), ('C', r <= .3)):
        tiers[name] = {'y1': round(float((d[m].fwd_1y.dropna() > 0).mean()), 3), 'y3': round(float((d[m].fwd_3y.dropna() > 0).mean()), 3)}
    site['categories'][c] = {'model': k, 'tiers': tiers, 'all': {'y1': round(float(row.all_1y), 3), 'y3': round(float(row.all_3y), 3)},
                             'basket': {'y1': round(float(row.basket_1y), 3), 'y3': round(float(row.basket_3y), 3)}, 'hold': {'y1': round(float(row.hold_1y), 3), 'y3': round(float(row.hold_3y), 3)},
                             'months': {'y1': int(row.n_1y), 'y3': int(row.n_3y)},
                             'weights': sorted(out['categories'][c].get('weights', {}).items(), key=lambda x: -abs(x[1]))[:10]}
json.dump(site, open('site/model_backtest.json', 'w'), separators=(',', ':'))
print('\nwrote site/model_backtest.json')
