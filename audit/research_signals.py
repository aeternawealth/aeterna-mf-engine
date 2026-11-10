"""Walk-forward on the real 2012-2025 quarterly panel. Train = start dates up to 2018-12, test = 2019-03 onward."""
import sys, os; sys.path.insert(0, '/home/user/aeterna-mf-engine'); os.chdir('/home/user/aeterna-mf-engine')
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
from engine import config as C
from engine.protocols import score_group, assign_tiers
OUT = 'audit/research_'
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
        parts.append(assign_tiers(score_group(g, C.protocol_for(g.category.iloc[0])[1])))
R = pd.concat(parts, ignore_index=True)
R['train'] = R.as_of <= '2018-12-31'
R['up'] = R.mkt_above_200d == 1
R.to_pickle(OUT + 'R_real.pkl')
G = ['as_of', 'peer_group']
print(f'fund-quarters {len(R)}, quarters {R.as_of.nunique()}, closed later {(R.status == "closed").sum()}')

def beat(s): return (s > 0).mean()
print('\n=== CURRENT v3 rating, all equity categories ===')
for h in (1, 3):
    c = f'fwd_{h}y'; X = R[R[c].notna()]
    t = X.groupby('tier')[c].agg(n='size', beat=beat, mean='mean').reindex(['A+', 'A', 'B', 'C'])
    print(f'next {h}Y | all funds beat {beat(X[c]):.1%}')
    for tier, r in t.iterrows(): print(f'   {tier:3s} n={int(r.n):5d} beat {r.beat:.1%} avg excess {r["mean"]*100:+.2f}%/yr')

def spear(a, b):
    m = a.notna() & b.notna()
    return a[m].rank().corr(b[m].rank()) if m.sum() >= 5 else np.nan

feats = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'excess_cagr_3y', 'excess_cagr_5y', 'roll3y_excess_median', 'roll3y_hit_rate',
         'roll3y_excess_p10', 'roll1y_hit_rate', 'roll1y_excess_median', 'info_ratio_3y', 'alpha_3y', 'sharpe_3y', 'sortino_3y',
         'treynor_3y', 'calmar_3y', 'capture_ratio_3y', 'beta_3y', 'vol_3y', 'downside_capture_3y', 'upside_capture_3y',
         'max_drawdown_3y', 'tracking_err_3y', 'age_years', 'style_mom', 'style_val', 'style_lowvol', 'style_qual', 'style_small', 'style_mid']
for f in feats: R['p_' + f] = R.groupby(G)[f].rank(pct=True)
rows = []
for f in feats:
    r = {'signal': f}
    for h in (1, 3):
        c = f'fwd_{h}y'
        for nm, m in (('train', R.train), ('test', ~R.train), ('up mkt', R.up), ('down mkt', ~R.up)):
            X = R[m & R[c].notna()]
            r[f'{h}Y {nm}'] = round(np.nanmean([spear(g[f], g[c]) for _, g in X.groupby(G)]), 3)
    rows.append(r)
T = pd.DataFrame(rows); T.to_csv(OUT + 'ic_real.csv', index=False)
print('\n=== SIGNALS: rank correlation with next-period excess return, within peer group ===')
print(T.sort_values('1Y train', ascending=False).to_string(index=False))
