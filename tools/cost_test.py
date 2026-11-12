import sys, json
sys.path.insert(0, '/home/user/aeterna-mf-engine')
import numpy as np, pandas as pd
from engine import config as C
d = json.load(open('/home/user/aeterna-mf-engine/outputs/latest/rankings.json'))
df = pd.DataFrame(d['funds'])
T0, T1, T2 = pd.Timestamp('2023-11-10'), pd.Timestamp('2024-11-11'), pd.Timestamp('2025-11-11')
T3 = pd.Timestamp('2026-11-11')
def nav_at(s, t):
    s = s[s.index <= t]
    return float(s.iloc[-1]) if len(s) and (t - s.index[-1]).days < 10 else np.nan
rows = []
for _, f in df.iterrows():
    name, proto = C.protocol_for(f['category'])
    if name.startswith('Index') or not any(k in proto for k in ('ter', 'ter_base')):
        continue
    fam = 'Hybrid' if name.startswith('Hybrid') else 'Arbitrage' if f['category'] == 'Arbitrage' else 'Debt'
    p = f'/home/user/aeterna-mf-engine/data/nav/{int(f["code"])}.csv'
    try:
        s = pd.read_csv(p, parse_dates=['date']).set_index('date')['nav'].sort_index()
    except Exception:
        continue
    v = [nav_at(s, t) for t in (T0, T1, T2, T3)]
    if any(np.isnan(x) for x in v):
        continue
    ter = f['ter_base'] if fam in ('Hybrid', 'Arbitrage') and pd.notna(f.get('ter_base')) else f['ter']
    rows.append(dict(fam=fam, grp=f"{f['peer_group']}|{f['plan_type']}", ter=ter,
                     r1=v[1] / v[0] - 1, r2=v[2] / v[1] - 1, r3=v[3] / v[2] - 1))
x = pd.DataFrame(rows).dropna()
for c in ('r1', 'r2', 'r3'):
    x[c + 'x'] = x[c] - x.groupby('grp')[c].transform('median')     # relative to the peer median
x = x[x.groupby('grp').grp.transform('size') >= 5]
print('funds with full history:', len(x))
def spear(g, a, b):
    return g[a].rank().corr(g[b].rank())
for fam, g in x.groupby('fam'):
    out = {}
    for past, fwd in (('r1x', 'r2x'), ('r2x', 'r3x')):
        cs_ret = g.groupby('grp').apply(lambda h: spear(h, past, fwd)).mean()
        cs_ter = g.groupby('grp').apply(lambda h: spear(h, 'ter', fwd)).mean()
        # does cost add to past returns? within-group OLS on ranks: fwd ~ past + ter
        h = g.copy()
        for c in (past, fwd, 'ter'):
            h[c + '_r'] = h.groupby('grp')[c].rank(pct=True) - 0.5
        X = np.column_stack([h[past + '_r'], h['ter_r']]); y = h[fwd + '_r']
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        out[f'{past}->{fwd}'] = (round(cs_ret, 2), round(cs_ter, 2), [round(b, 2) for b in beta])
    print(fam, len(g), 'funds |', {k: f'past→next {v[0]}, cost→next {v[1]}, joint (past, cost) {v[2]}' for k, v in out.items()})
