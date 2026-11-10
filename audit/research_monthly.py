"""Monthly re-rating test on the real 2012-2026 monthly panel (audit/bt_metrics_long.csv).
Models: current v3 score; lean (momentum + size tilt + upside capture); comprehensive (every signal, weights = 2012-18 rank IC).
Tests: (1) A+ funds beating their benchmark over the next 1M / 3M / 1Y; (2) a portfolio holding the current A+ funds of a
category, re-rated monthly, with and without a hold rule (keep until it drops below A) and after switching costs."""
import sys, os; sys.path.insert(0, '.')
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
from engine import config as C
from engine.protocols import score_group, assign_tiers

M = pd.read_csv('audit/bt_metrics_long.csv', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
RF = 0.065
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y
M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
M['sharpe_3y'] = (M.cagr_3y - RF) / M.vol_3y
M['treynor_3y'] = (M.cagr_3y - RF) / M.beta_3y
M['calmar_3y'] = M.cagr_3y / M.max_drawdown_3y.abs()
parts = []
for t, D in M.groupby('as_of'):
    D = D.copy(); th = D.category.eq('Sectoral/Thematic')
    cnt = D[th].groupby('peer_group').size(); thin = set(cnt[cnt < C.THEME_MIN_RATED].index)
    D.loc[th & D.peer_group.isin(thin), 'peer_group'] = 'Thematic: Other Themes'
    for pg, g in D.groupby('peer_group'):
        if len(g) < 5: continue
        parts.append(score_group(g, C.protocol_for(g.category.iloc[0])[1]))
R = pd.concat(parts, ignore_index=True)
R['train'] = R.as_of <= '2018-12-31'
G = ['as_of', 'peer_group']
FEATS = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'excess_cagr_3y', 'excess_cagr_5y', 'roll3y_excess_median', 'roll3y_hit_rate',
         'roll3y_excess_p10', 'roll1y_hit_rate', 'roll1y_excess_median', 'info_ratio_3y', 'alpha_3y', 'sharpe_3y', 'sortino_3y',
         'treynor_3y', 'calmar_3y', 'capture_ratio_3y', 'beta_3y', 'vol_3y', 'downside_capture_3y', 'upside_capture_3y',
         'max_drawdown_3y', 'tracking_err_3y', 'age_years', 'style_mom', 'style_val', 'style_lowvol', 'style_qual', 'style_small', 'style_mid']
for f in FEATS: R['p_' + f] = R.groupby(G)[f].rank(pct=True)
P = lambda f: R['p_' + f].fillna(.5)

def ic(f, h, mask):
    X = R[mask & R[h].notna()]
    v = [g[f].rank().corr(g[h].rank()) for _, g in X.groupby(G) if g[f].notna().sum() >= 5]
    return np.nanmean(v)

# comprehensive: every signal, weight = its 2012-18 rank IC against next-12-month excess (sign kept)
W = {f: ic(f, 'fwd_1y', R.train) for f in FEATS}
W = {f: w for f, w in W.items() if np.isfinite(w)}
comp = sum(P(f) * w for f, w in W.items())
MOM = (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4
lean = .5 * MOM + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')
MODELS = {'Current v3': R.score, 'Lean (momentum, size tilt, upside capture)': lean, 'Comprehensive (all 31 signals, fitted weights)': comp}
pd.Series(W).sort_values().to_csv('audit/research_monthly_weights.csv', header=['weight_ic_1y_2012_18'])

out = []
for name, sc in MODELS.items():
    pct = sc.groupby([R.as_of, R.peer_group]).rank(pct=True); R['_p'] = pct
    for h in ('fwd_1m', 'fwd_3m', 'fwd_1y', 'fwd_3y'):
        for era, m in (('2012-18', R.train), ('2019-26 unseen', ~R.train)):
            X = R[m & R[h].notna() & R._p.notna()]
            a = X[X._p >= .9][h]; c = X[X._p < .3][h]
            out.append(dict(model=name, horizon=h, era=era, aplus_beat=(a > 0).mean(), aplus_excess=a.mean(), c_beat=(c > 0).mean(), all_beat=(X[h] > 0).mean(), n=len(a)))
T = pd.DataFrame(out); T.to_csv('audit/research_monthly_tiers.csv', index=False)

# portfolio test: hold the category's A+ funds (equal weight), re-rate every month
def portfolio(name, sc, cat, hold_rule=False, cost=0.0):
    R['_p'] = sc.groupby([R.as_of, R.peer_group]).rank(pct=True)
    X = R[(R.category == cat) & R.fwd_1m.notna()].sort_values('as_of')
    held, rets, turns = set(), [], []
    for t, g in X.groupby('as_of'):
        top = set(g.loc[g._p >= .9, 'code']); okA = set(g.loc[g._p >= .7, 'code'])
        new = (top | (held & okA)) if hold_rule else top
        new = new or top
        if not new: continue
        turn = len(new - held) / max(1, len(new)) if held else 0
        r = g.loc[g.code.isin(new), 'fwd_1m'].mean() - cost * turn
        rets.append((t, r)); turns.append(turn); held = new
    s = pd.Series(dict(rets)); return s, np.mean(turns) if turns else np.nan

rows = []
for cat in ['Flexi Cap', 'Small Cap', 'Mid Cap', 'Multi Cap', 'Large Cap', 'ELSS', 'Focused', 'Large & Mid Cap']:
    for name in ('Current v3', 'Lean (momentum, size tilt, upside capture)', 'Comprehensive (all 31 signals, fitted weights)'):
        for rule, cost in (('switch monthly', 0.0), ('switch monthly, after costs', 0.01), ('hold until below A, after costs', 0.01)):
            s, turn = portfolio(name, MODELS[name], cat, hold_rule=rule.startswith('hold'), cost=cost)
            if s.empty: continue
            roll = (1 + s).rolling(12).apply(np.prod, raw=True) - 1          # 12 months of following the ratings
            for era, m in (('2012-18', roll.index <= '2018-12-31'), ('2019-26 unseen', roll.index > '2018-12-31')):
                rr = roll[m].dropna()
                rows.append(dict(category=cat, model=name, rule=rule, era=era, years_beat=(rr > 0).mean(), avg_12m_excess=rr.mean(), monthly_turnover=turn, n=len(rr)))
Pf = pd.DataFrame(rows); Pf.to_csv('audit/research_monthly_portfolio.csv', index=False)

pd.set_option('display.width', 220)
print('A+ beat rate (top 10% of peer group), by horizon')
print(T.pivot_table(index=['model'], columns=['horizon', 'era'], values='aplus_beat', sort=False).round(3).to_string())
print('\nall funds'); print(T[T.model == 'Current v3'].pivot_table(index='horizon', columns='era', values='all_beat', sort=False).round(3).to_string())
print('\nPortfolio of the A+ funds, re-rated monthly: share of 12-month periods ahead of the benchmark')
print(Pf.pivot_table(index=['category', 'model'], columns=['rule', 'era'], values='years_beat', sort=False).round(2).to_string())
print('\naverage 12-month lead over benchmark (unseen 2019-26)')
print(Pf[Pf.era == '2019-26 unseen'].pivot_table(index=['category', 'model'], columns='rule', values='avg_12m_excess', sort=False).round(4).to_string())
print('\nmonthly turnover'); print(Pf[Pf.era == '2019-26 unseen'].pivot_table(index='model', columns='rule', values='monthly_turnover', aggfunc='mean', sort=False).round(2).to_string())
print('\ncomprehensive weights (2012-18 IC):'); print(pd.Series(W).sort_values().round(3).to_string())
