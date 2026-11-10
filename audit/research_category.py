"""Category-wise equity models, tested walk-forward on the monthly panel (audit/bt_metrics_long.csv.gz).

Question: does a separate set of weights for each category beat one set for all equity funds?

Fit (2012-03 .. 2017-12 only, so every 1-year outcome used ends by 2018-12):
  for each signal, the monthly rank correlation (IC) between the fund's percentile on the signal within its peer group
  and its return over the benchmark in the next 12 months. A signal is kept for a category only if its IC has the
  same sign in both halves of the fit window (2012-14 and 2015-17) and averages at least MIN_IC in size.
  Weight = the average IC. Three ways to set it:
    category : the category's own IC                                   (most flexible, most likely to overfit)
    shrunk   : half the category's IC, half the all-equity IC          (kept only where the two agree in sign)
    pooled   : the all-equity IC for every category                    (one fitted model)
Test (2019-01 .. 2026-09, never used in the fit): funds are ranked by score within the peer group each month.
  A+ = top 10%, A = next 20%, C = bottom 30%. Reported: share of A+ funds ahead of the benchmark over the next year,
  and the 'new SIPs to the current A+ funds, never sell' rule over 12 and 36 months (see research_sip_rule.py).
Compared with: Lean (the fixed v4 weights) and v3 (the live model)."""
import sys; sys.path.insert(0, '.')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from engine import config as C
from engine.protocols import score_group

SIGNALS = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual',
           'style_n50', 'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y',
           'sortino_3y', 'beta_3y', 'vol_3y', 'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate',
           'roll1y_excess_median', 'roll3y_excess_median', 'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
FIT_END, MID, TEST_START, MIN_IC = '2017-12-31', '2014-12-31', '2019-01-01', 0.03

M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
M = M[M.cat.isin(CATS)].copy()
M['grp'] = M.cat                                                  # Value and Contra ranked together, as on the site
G = ['as_of', 'grp']
M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in SIGNALS:
    M['p_' + s] = M.groupby(G)[s].rank(pct=True)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)

# the live model's score, for comparison (v3 protocol)
RF = 0.065
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y
M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
v3 = pd.concat([score_group(g.assign(peer_group=g.grp), C.V3_ACTIVE_EQUITY_PROTOCOL) for _, g in M.groupby(G)])
M['s_v3'] = v3.score.reindex(M.index) if v3.index.equals(M.index) else v3.sort_index().score.values
P = lambda f: M['p_' + f].fillna(.5)
M['s_lean'] = .5 * (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4 + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')


def ic(df, s):
    """Mean of the monthly rank correlations between the signal's percentile and the next year's percentile."""
    x = df[['as_of', 'p_' + s, 'p_fwd']].dropna()
    if len(x) < 60: return np.nan
    r = x.groupby('as_of').apply(lambda g: g['p_' + s].corr(g.p_fwd) if len(g) >= 5 else np.nan).dropna()
    return r.mean() if len(r) >= 12 else np.nan


fit = M[M.as_of <= FIT_END]
h1, h2 = fit[fit.as_of <= MID], fit[fit.as_of > MID]
IC_all = {s: (ic(h1, s), ic(h2, s), ic(fit, s)) for s in SIGNALS}
W = {}                                                            # (model, category) -> {signal: weight}
rows_w = []
for c in CATS:
    f1, f2, f = h1[h1.cat == c], h2[h2.cat == c], fit[fit.cat == c]
    for s in SIGNALS:
        a, b, m = ic(f1, s), ic(f2, s), ic(f, s)
        ga, gb, gm = IC_all[s]
        stable = np.isfinite([a, b, m]).all() and np.sign(a) == np.sign(b) and abs(m) >= MIN_IC
        gstable = np.isfinite([ga, gb, gm]).all() and np.sign(ga) == np.sign(gb) and abs(gm) >= MIN_IC
        if stable: W.setdefault(('category', c), {})[s] = m
        if stable and gstable and np.sign(m) == np.sign(gm): W.setdefault(('shrunk', c), {})[s] = (m + gm) / 2
        if gstable: W.setdefault(('pooled', c), {})[s] = gm
        rows_w.append(dict(category=c, signal=s, ic_2012_14=a, ic_2015_17=b, ic_fit=m, ic_all_equity=gm, kept_category=stable,
                           kept_shrunk=bool(stable and gstable and np.sign(m) == np.sign(gm)), kept_pooled=gstable))
pd.DataFrame(rows_w).to_csv('audit/research_category_weights.csv', index=False)

for model in ('category', 'shrunk', 'pooled'):
    sc = pd.Series(np.nan, index=M.index)
    for c in CATS:
        w = W.get((model, c), {})
        if not w: continue
        m = M.cat == c
        tot = sum(abs(v) for v in w.values())
        sc[m] = sum(abs(v) / tot * (P(s)[m] if v > 0 else 1 - P(s)[m]) for s, v in w.items())
    M['s_' + model] = sc
MODELS = ['category', 'shrunk', 'pooled', 'lean', 'v3']
for k in MODELS:
    M['r_' + k] = M.groupby(G)['s_' + k].rank(pct=True)

X1 = M.set_index(['as_of', 'code']).fwd_1m
dates = sorted(M.as_of.unique())


def sip(model, c, months, start):
    sub = M[(M.cat == c)]
    pick = {t: list(g.code[g['r_' + model] >= .9]) for t, g in sub.groupby('as_of')}
    out = []
    ds = [d for d in dates if d >= pd.Timestamp(start)]
    for i0 in range(len(ds) - months):
        units, put = {}, 0.0
        for k in range(months):
            t = ds[i0 + k]; ch = pick.get(t, [])
            if ch:
                for code in ch: units[code] = units.get(code, 0) + 1 / len(ch)
                put += 1
            for code in list(units):
                r = X1.get((t, code), np.nan)
                if np.isfinite(r): units[code] *= 1 + r
        if put: out.append(sum(units.values()) / put - 1)
    return (np.array(out) > 0).mean() if out else np.nan, len(out)


res = []
for c in CATS + ['ALL']:
    for k in MODELS:
        for era, m in (('fit 2012-17', M.as_of <= FIT_END), ('unseen 2019-26', M.as_of >= TEST_START)):
            d = M[m & ((M.cat == c) if c != 'ALL' else True)]
            ap, a, cc = d[d['r_' + k] >= .9], d[(d['r_' + k] >= .7) & (d['r_' + k] < .9)], d[d['r_' + k] <= .3]
            row = dict(category=c, model=k, era=era, n_signals=len(W.get((k, c), {})) if k in ('category', 'shrunk', 'pooled') and c != 'ALL' else np.nan,
                       aplus_beat_1y=(ap.fwd_1y.dropna() > 0).mean(), aplus_n=ap.fwd_1y.notna().sum(), a_beat_1y=(a.fwd_1y.dropna() > 0).mean(),
                       c_beat_1y=(cc.fwd_1y.dropna() > 0).mean(), all_beat_1y=(d.fwd_1y.dropna() > 0).mean(),
                       aplus_beat_3y=(ap.fwd_3y.dropna() > 0).mean(), aplus_avg_excess_1y=ap.fwd_1y.mean())
            if c != 'ALL' and era.startswith('unseen'):
                row['sip12'], row['sip12_n'] = sip(k, c, 12, TEST_START); row['sip36'], _ = sip(k, c, 36, TEST_START)
            res.append(row)
R = pd.DataFrame(res); R.to_csv('audit/research_category_results.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 30)
U = R[R.era == 'unseen 2019-26']
print('\n=== unseen 2019-26: share of A+ funds ahead of the benchmark over the next year ===')
print(U.pivot(index='category', columns='model', values='aplus_beat_1y')[MODELS].round(3).to_string())
print('\nall funds (base rate):'); print(U[U.model == 'lean'].set_index('category').all_beat_1y.round(3).to_string())
print('\n=== unseen: bottom 30% (C) ahead of the benchmark next year ===')
print(U.pivot(index='category', columns='model', values='c_beat_1y')[MODELS].round(3).to_string())
print('\n=== unseen: 12-month SIPs into the current A+ funds, share of start months ahead of the index SIP ===')
print(U[U.category != 'ALL'].pivot(index='category', columns='model', values='sip12')[MODELS].round(2).to_string())
print('\n=== unseen: 36-month SIPs ===')
print(U[U.category != 'ALL'].pivot(index='category', columns='model', values='sip36')[MODELS].round(2).to_string())
print('\n=== fit window 2012-17 (in-sample, for the size of the overfit): A+ ahead next year ===')
print(R[R.era == 'fit 2012-17'].pivot(index='category', columns='model', values='aplus_beat_1y')[MODELS].round(3).to_string())
print('\nsignals kept per category:')
for c in CATS:
    for k in ('category', 'shrunk'):
        w = W.get((k, c), {}); print(f'  {c:16} {k:9}', ', '.join(f"{s}{'+' if v > 0 else '-'}{abs(v):.2f}" for s, v in sorted(w.items(), key=lambda x: -abs(x[1]))))
print('pooled:', ', '.join(f"{s}{'+' if v > 0 else '-'}{abs(v):.2f}" for s, v in sorted(W.get(('pooled', 'Flexi Cap'), {}).items(), key=lambda x: -abs(x[1]))))

# ---- Lean+: the same fixed weights, with the size tilt also read from the tilt away from the Nifty 50 ----
# In Mid Cap the mid-cap tilt is undefined (the benchmark is the Midcap 150) and in Small Cap the small-cap tilt is; a
# tilt away from the Nifty 50 is defined for every category and was among the three strongest signals in the fit window.
size = pd.concat([P('style_small').where(M.style_small.notna()), P('style_mid').where(M.style_mid.notna()), (1 - P('style_n50')).where(M.style_n50.notna())], axis=1).mean(axis=1).fillna(.5)
M['s_leanplus'] = .5 * (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4 + .3 * size + .2 * P('upside_capture_3y')
M['r_leanplus'] = M.groupby(G).s_leanplus.rank(pct=True)
rows = []
for c in CATS + ['ALL']:
    for k in ('lean', 'leanplus'):
        d = M[(M.as_of >= TEST_START) & ((M.cat == c) if c != 'ALL' else True)]; ap = d[d['r_' + k] >= .9]; cc = d[d['r_' + k] <= .3]
        row = dict(category=c, model=k, aplus_beat_1y=(ap.fwd_1y.dropna() > 0).mean(), c_beat_1y=(cc.fwd_1y.dropna() > 0).mean(), aplus_beat_3y=(ap.fwd_3y.dropna() > 0).mean())
        if c != 'ALL': row['sip12'], _ = sip(k, c, 12, TEST_START); row['sip36'], _ = sip(k, c, 36, TEST_START)
        rows.append(row)
LP = pd.DataFrame(rows); LP.to_csv('audit/research_category_leanplus.csv', index=False)
print('\n=== Lean vs Lean+ (size tilt also from the tilt away from the Nifty 50), unseen 2019-26 ===')
print(LP.pivot(index='category', columns='model', values=['aplus_beat_1y', 'c_beat_1y', 'sip12', 'sip36']).round(2).to_string())
