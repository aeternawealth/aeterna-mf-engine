"""Can A+ get to 60%+? Variants chosen on 2012-18 only, then read off 2019-25."""
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
OUT = 'audit/research_'
R = pd.read_pickle(OUT + 'R_real.pkl'); G = ['as_of', 'peer_group']
for f in ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'upside_capture_3y']:
    R['p_' + f] = R.groupby(G)[f].rank(pct=True)
P = lambda f: R['p_' + f].fillna(.5)
MOM = (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4
base = .5 * MOM + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')
pct = base.groupby([R.as_of, R.peer_group]).rank(pct=True)
absmom = (R.mom_6m > 0) & (R.mom_12m > 0)          # ahead of its benchmark over the last 6 and 12 months
broad = R.mom_3m > 0
variants = {
    'top 10%': pct >= .9,
    'top 10% + ahead of benchmark over 6M and 12M': (pct >= .9) & absmom,
    'top 20% + ahead of benchmark over 6M and 12M': (pct >= .8) & absmom,
    'top 10% + ahead over 3M, 6M and 12M': (pct >= .9) & absmom & broad,
    'top 5%': pct >= .95,
}
for h in (1, 3):
    c = f'fwd_{h}y'; print(f'\n=== next {h}Y ===')
    for name, sel in variants.items():
        out = []
        for era, m in (('2012-18', R.train), ('2019-25 unseen', ~R.train), ('rising', R.up), ('falling', ~R.up)):
            X = R[m & sel & R[c].notna()][c]; A = R[m & R[c].notna()][c]
            out.append(f'{era}: {(X > 0).mean():.1%} (+{X.mean()*100:.1f}%/yr, n={len(X)}) vs all {(A > 0).mean():.0%}')
        print(f'{name}\n   ' + '\n   '.join(out))
