import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
OUT = 'audit/research_'
R = pd.read_pickle(OUT + 'R_real.pkl')
G = ['as_of', 'peer_group']
feats = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'upside_capture_3y', 'info_ratio_3y', 'alpha_3y',
         'excess_cagr_3y', 'max_drawdown_3y', 'vol_3y', 'ter']
for f in feats:
    if f in R: R['p_' + f] = R.groupby(G)[f].rank(pct=True)
P = lambda f: R['p_' + f].fillna(.5)
MOM = (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4
SIZE = (P('style_small') + P('style_mid')) / 2
models = {
    'Current v3 score': R.score,
    'Momentum (1-12 months)': MOM,
    'Momentum + size tilt': .6 * MOM + .4 * SIZE,
    'Momentum + size tilt + upside capture': .5 * MOM + .3 * SIZE + .2 * P('upside_capture_3y'),
    'Momentum + size + upside + 3Y alpha': .45 * MOM + .25 * SIZE + .15 * P('upside_capture_3y') + .15 * P('alpha_3y'),
}
def tiers(score):
    p = score.groupby([R.as_of, R.peer_group]).rank(pct=True)
    return pd.cut(p, [0, .3, .7, .9, 1.0001], labels=['C', 'B', 'A', 'A+'])
rows = []
for name, sc in models.items():
    T = tiers(sc)
    for h in (1, 3):
        c = f'fwd_{h}y'
        for era, m in (('2012-18 (fitted)', R.train), ('2019-25 (unseen)', ~R.train), ('rising mkt', R.up), ('falling mkt', ~R.up)):
            X = R[m & R[c].notna()]; tt = T[X.index]
            a = X[c][tt == 'A+']; aa = X[c][tt.isin(['A+', 'A'])]; cc = X[c][tt == 'C']
            rows.append(dict(model=name, h=f'{h}Y', era=era, aplus_beat=round((a > 0).mean() * 100, 1), aplus_excess=round(a.mean() * 100, 2),
                             top30_beat=round((aa > 0).mean() * 100, 1), c_beat=round((cc > 0).mean() * 100, 1), all_beat=round((X[c] > 0).mean() * 100, 1), n_aplus=len(a)))
Rz = pd.DataFrame(rows); Rz.to_csv(OUT + 'models_real.csv', index=False)
for h in ('1Y', '3Y'):
    print(f'\n######## next {h}: % of funds beating their benchmark (A+ = top 10% of peer group) ########')
    print(Rz[Rz.h == h].pivot_table(index='model', columns='era', values='aplus_beat', sort=False).to_string())
    print('-- A+ average excess return %/yr'); print(Rz[Rz.h == h].pivot_table(index='model', columns='era', values='aplus_excess', sort=False).to_string())
    print('-- A+ and A together (top 30%)'); print(Rz[Rz.h == h].pivot_table(index='model', columns='era', values='top30_beat', sort=False).to_string())
    print('-- C (bottom 30%)'); print(Rz[Rz.h == h].pivot_table(index='model', columns='era', values='c_beat', sort=False).to_string())
    print('-- all funds'); print(Rz[(Rz.h == h) & (Rz.model == 'Current v3 score')].set_index('era').all_beat.to_string())
# per category, best model, unseen period
best = models['Momentum + size tilt + upside capture']; T = tiers(best); Tv = tiers(R.score)
print('\n######## by category, 2019-25 unseen, next 1Y and 3Y: A+ beat % (new) vs (current) vs all ########')
for cat in ['Multi Cap', 'Small Cap', 'Mid Cap', 'Flexi Cap', 'Large Cap', 'Large & Mid Cap', 'ELSS', 'Focused']:
    out = [cat]
    for h in (1, 3):
        c = f'fwd_{h}y'; X = R[(~R.train) & (R.category == cat) & R[c].notna()]
        out.append(f'{h}Y new {((X[c][T[X.index] == "A+"]) > 0).mean():.0%} cur {((X[c][Tv[X.index] == "A+"]) > 0).mean():.0%} all {(X[c] > 0).mean():.0%}')
    print(' | '.join(out))
