"""'New SIPs to the current A+ funds, never sell' on the monthly panel (audit/bt_metrics_long.csv).
Each month an investor puts one SIP instalment, split equally across the category's current A+ funds (lean model; top 10%
of the peer group, Regular plans), and keeps every unit. Each unit's value relative to the benchmark grows by
(1 + the fund's excess return that month). A period 'beats' when the SIPs end worth more than the same SIPs in the
benchmark index. Costs: none (no units are ever sold). Compared with the current v3 score and with all funds."""
import sys, os; sys.path.insert(0, '.')
import pandas as pd, numpy as np, warnings
warnings.filterwarnings('ignore')
from engine import config as C
from engine.protocols import score_group

M = pd.read_csv('audit/bt_metrics_long.csv', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M = M[M.category.isin(['Flexi Cap', 'Small Cap', 'Mid Cap', 'Multi Cap', 'Large Cap', 'ELSS', 'Focused', 'Large & Mid Cap', 'Value', 'Contra'])].copy()
RF = 0.065
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y
M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
parts = [score_group(g, C.protocol_for(g.category.iloc[0])[1]) for _, g in M.groupby(['as_of', 'peer_group']) if len(g) >= 5]
R = pd.concat(parts, ignore_index=True)
G = ['as_of', 'peer_group']
for f in ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'upside_capture_3y']:
    R['p_' + f] = R.groupby(G)[f].rank(pct=True)
P = lambda f: R['p_' + f].fillna(.5)
lean = .5 * (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4 + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')
MODELS = {'Lean': lean, 'Current v3': R.score, 'All funds': pd.Series(1.0, index=R.index)}
X1 = R.set_index(['as_of', 'code'])['fwd_1m']          # each fund's excess return in the month after each date
dates = sorted(R.as_of.unique())

def run(name, cat, months):
    sc = MODELS[name]; p = sc.groupby([R.as_of, R.peer_group]).rank(pct=True)
    pick = {t: list(R.loc[(R.as_of == t) & (R.category == cat) & ((p >= .9) if name != 'All funds' else True), 'code']) for t in dates}
    out = []
    for i0 in range(len(dates) - months):
        units = {}                                     # code -> value relative to the benchmark
        put = 0.0
        for k in range(months):
            t = dates[i0 + k]
            ch = pick[t]
            if ch:
                for c in ch: units[c] = units.get(c, 0) + 1 / len(ch)
                put += 1
            for c in list(units):                      # the month after t
                r = X1.get((t, c), np.nan)
                if np.isfinite(r): units[c] *= 1 + r   # fund missing (closed or merged): value carried unchanged
        if put: out.append((dates[i0], sum(units.values()) / put - 1))
    return pd.Series(dict(out))

rows = []
for cat in ['Flexi Cap', 'Small Cap', 'Mid Cap', 'Multi Cap', 'ELSS', 'Large Cap', 'Focused', 'Large & Mid Cap']:
    for name in MODELS:
        for months in (12, 36):
            s = run(name, cat, months)
            for era, m in (('2012-18', s.index <= '2018-12-31'), ('2019-26 unseen', s.index > '2018-12-31')):
                x = s[m]
                if len(x): rows.append(dict(category=cat, model=name, months=months, era=era, beat=(x > 0).mean(), avg_lead=x.mean(), n=len(x)))
Z = pd.DataFrame(rows); Z.to_csv('audit/research_sip_rule.csv', index=False)
pd.set_option('display.width', 200)
for months in (12, 36):
    print(f'\n=== SIPs for {months} months into the current A+ funds, never selling: share of start months ahead of the same SIPs in the index ===')
    print(Z[Z.months == months].pivot_table(index='category', columns=['model', 'era'], values='beat', sort=False).round(2).to_string())
    print('average lead over the index-SIP at the end (unseen 2019-26):')
    print(Z[(Z.months == months) & (Z.era == '2019-26 unseen')].pivot_table(index='category', columns='model', values='avg_lead', sort=False).round(4).to_string())
