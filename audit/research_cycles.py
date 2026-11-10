"""Cycle-aware ratings: can the model adapt to what is working, using only what is known on the rating date?

1. Market state on the rating date (both known then): the market above or below its 200-day average, and the
   market's last 12 months up or down. For each state, the rank correlation (IC) of each signal with the next year's
   return over the benchmark, all equity categories pooled within category.
2. Self-adjusting model: each month every signal is weighted by its average IC over the 36 months whose outcomes
   were already known (rating dates 48 to 12 months earlier); signals with a negative trailing IC get no weight.
   Compared with the fixed base recipe (momentum 55, upside 30, size 15) on 2016-25, the years where 36 months of
   known outcomes exist.
3. State-switch model: base recipe when the market is above its 200-day average, and a defensive variant
   (momentum 40, upside 15, downside protection 30, size 15) when it is below."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
SIG = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_n50', 'style_val', 'style_mom', 'style_lowvol', 'style_qual',
       'upside_capture_3y', 'downside_capture_3y', 'info_ratio_3y', 'capture_ratio_3y', 'sharpe_3y', 'excess_cagr_3y', 'roll3y_hit_rate', 'beta_3y', 'max_drawdown_3y']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'}); M = M[M.cat.isin(CATS)].copy()
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in SIG: M['p_' + s] = M.groupby(G)[s].rank(pct=True)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)


def ics(d):
    """monthly IC per signal: DataFrame indexed by date"""
    out = {}
    for s in SIG:
        x = d[['as_of', 'cat', 'p_' + s, 'p_fwd']].dropna()
        out[s] = x.groupby(['as_of', 'cat']).apply(lambda g: g['p_' + s].corr(g.p_fwd) if len(g) >= 5 else np.nan).groupby('as_of').mean()
    return pd.DataFrame(out)


IC = ics(M)
st = M.groupby('as_of')[['mkt_above_200d', 'mkt_12m']].first()
print('=== 1. signal strength by market state on the rating date (average monthly IC) ===')
tab = pd.DataFrame({'above 200d': IC[st.mkt_above_200d.reindex(IC.index) == 1].mean(), 'below 200d': IC[st.mkt_above_200d.reindex(IC.index) == 0].mean(),
                    'last 12m up': IC[st.mkt_12m.reindex(IC.index) > 0].mean(), 'last 12m down': IC[st.mkt_12m.reindex(IC.index) <= 0].mean()})
tab['months below 200d'] = (st.mkt_above_200d == 0).sum()
print(tab.round(3).to_string())

# 2. self-adjusting weights
P = lambda s: M['p_' + s].fillna(.5)
dates = sorted(M.as_of.unique()); W = {}
for t in dates:
    lo, hi = t - pd.DateOffset(months=48), t - pd.DateOffset(months=12)
    w = IC[(IC.index > lo) & (IC.index <= hi)]
    if len(w) >= 30: W[t] = w.mean().clip(lower=0)
M['s_adapt'] = np.nan
for t, w in W.items():
    m = M.as_of == t; tot = w.sum()
    if tot > 0: M.loc[m, 's_adapt'] = sum(w[s] / tot * P(s)[m] for s in SIG if w[s] > 0)
mom = (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4; size = (P('style_small') + P('style_mid')) / 2
M['s_base'] = .55 * mom + .30 * P('upside_capture_3y') + .15 * size
defn = .40 * mom + .15 * P('upside_capture_3y') + .30 * (1 - P('downside_capture_3y')) + .15 * size
M['s_switch'] = np.where(M.as_of.map(st.mkt_above_200d) == 1, M.s_base, defn)
T = M[(M.as_of >= '2016-01-01') & M.s_adapt.notna()].copy()
for k in ('base', 'adapt', 'switch'): T['r_' + k] = T.groupby(G)['s_' + k].rank(pct=True)
rows = []
for c in CATS + ['ALL']:
    d = T if c == 'ALL' else T[T.cat == c]; row = dict(category=c, all_funds=(d.fwd_1y.dropna() > 0).mean())
    for k in ('base', 'adapt', 'switch'):
        ap = d[d['r_' + k] >= .9]; row[k + '_1y'] = (ap.fwd_1y.dropna() > 0).mean(); row[k + '_3y'] = (ap.fwd_3y.dropna() > 0).mean()
    rows.append(row)
R = pd.DataFrame(rows).set_index('category'); R.to_csv('audit/research_cycles.csv')
print('\n=== 2-3. 2016-25: A+ funds ahead of the benchmark over the next 1 and 3 years ===')
print(R[['base_1y', 'adapt_1y', 'switch_1y', 'base_3y', 'adapt_3y', 'switch_3y', 'all_funds']].round(3).to_string())
yr = T.assign(y=T.as_of.dt.year).groupby('y').apply(lambda d: pd.Series({k: (d[d['r_' + k] >= .9].fwd_1y.dropna() > 0).mean() for k in ('base', 'adapt')} | {'all': (d.fwd_1y.dropna() > 0).mean()}))
print('\nby rating year (A+ ahead next year):'); print(yr.round(2).to_string())
last = W[max(W)]; print('\nself-adjusting weights at the latest date:', ', '.join(f'{s} {v / last.sum() * 100:.0f}' for s, v in last.sort_values(ascending=False).items() if v > 0))

# 4. what the market-state table suggests: after a fall (below the 200-day average) momentum stops working and the
#    funds that rebound are high-beta, small-cap and value-leaning ones; check it held in both eras and in each
#    episode, then test a 'rebound' switch
below = st.mkt_above_200d.reindex(IC.index) == 0
for era, m in (('2012-18', IC.index <= '2018-12-31'), ('2019-25', IC.index > '2018-12-31')):
    print(f'\nbelow the 200-day average, {era} ({(below & m).sum()} months):', ', '.join(f'{s} {IC[below & m][s].mean():+.2f}' for s in ['mom_3m', 'mom_6m', 'beta_3y', 'style_small', 'style_val', 'upside_capture_3y', 'style_qual', 'style_lowvol']))
ep = (below != below.shift()).cumsum()[below]
print('episodes below the 200-day average:', ', '.join(f'{g.index.min():%b %Y}-{g.index.max():%b %Y}' for _, g in IC[below].groupby(ep)))
reb = .30 * P('upside_capture_3y') + .25 * P('beta_3y') + .20 * P('style_val') + .25 * size
M['s_rebound'] = np.where(M.as_of.map(st.mkt_above_200d) == 1, M.s_base, reb)
T2 = M[M.as_of >= '2012-01-01'].copy()
for k in ('base', 'rebound'): T2['r_' + k] = T2.groupby(G)['s_' + k].rank(pct=True)
T2['below'] = T2.as_of.map(st.mkt_above_200d) == 0
rows = []
for c in CATS + ['ALL']:
    for era, m in (('2012-18', T2.as_of <= '2018-12-31'), ('2019-25', T2.as_of > '2018-12-31')):
        d = T2[m & ((T2.cat == c) if c != 'ALL' else True)]
        row = dict(category=c, era=era)
        for k in ('base', 'rebound'):
            ap = d[d['r_' + k] >= .9]; row[k + '_1y'] = (ap.fwd_1y.dropna() > 0).mean(); row[k + '_after_fall'] = (ap[ap.below].fwd_1y.dropna() > 0).mean()
        row['all_after_fall'] = (d[d.below].fwd_1y.dropna() > 0).mean(); rows.append(row)
RB = pd.DataFrame(rows); RB.to_csv('audit/research_cycles_rebound.csv', index=False)
print('\n=== 4. rebound switch: A+ ahead next year, all months and months rated after a fall ===')
print(RB.pivot(index='category', columns='era', values=['base_1y', 'rebound_1y', 'base_after_fall', 'rebound_after_fall', 'all_after_fall']).round(2).loc[CATS + ['ALL']].to_string())

# 5. softer: after a fall, half base recipe and half rebound
M['s_blend'] = np.where(M.as_of.map(st.mkt_above_200d) == 1, M.s_base, .5 * M.s_base + .5 * reb)
T2['r_blend'] = M.loc[T2.index, 's_blend'].groupby([T2.as_of, T2.cat]).rank(pct=True)
print('\n=== 5. half-and-half after a fall: A+ ahead next year (all months / months rated after a fall) ===')
for era, m in (('2012-18', T2.as_of <= '2018-12-31'), ('2019-25', T2.as_of > '2018-12-31')):
    d = T2[m]; f = lambda k, x: (x[x['r_' + k] >= .9].fwd_1y.dropna() > 0).mean()
    print(f'  {era}: base {f("base", d):.3f} / {f("base", d[d.below]):.3f}   blend {f("blend", d):.3f} / {f("blend", d[d.below]):.3f}   rebound {f("rebound", d):.3f} / {f("rebound", d[d.below]):.3f}')
