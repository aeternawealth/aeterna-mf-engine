"""A model per equity category, chosen without looking at the test years.

Candidates for each category:
  lean      the fixed v4 weights (momentum 50, size tilt 30, upside capture 20)
  category  weights fitted on the category alone
  shrunk    half the category's fitted weights, half the all-equity ones
  family    weights fitted on the category's family (large: Large Cap, Large & Mid Cap, Flexi Cap, Focused, ELSS,
            Value / Contra; small-mid: Mid Cap, Small Cap, Multi Cap)
  blend     the average of the lean score and the shrunk score (an ensemble)

Step 1, choose: fit on 2012-03..2014-12, score 2016-01..2017-12 (1-year outcomes end by 2018-12), and for each
        category keep the candidate with the highest average monthly rank correlation between score and the next
        year's return over the benchmark.
Step 2, test once: refit the fitted candidates on 2012-03..2017-12 and score 2019-01..2026-09, which neither step
        has seen. Report the chosen model against lean-for-all, category-for-all and v3.
Fitting rule as in research_category.py: a signal is kept when its IC has the same sign in both halves of the fit
window and averages at least 0.03; its weight is its IC."""
import sys; sys.path.insert(0, '.')
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from engine import config as C
from engine.protocols import score_group

SIGNALS = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual',
           'style_n50', 'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y',
           'sortino_3y', 'beta_3y', 'vol_3y', 'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate',
           'roll1y_excess_median', 'roll3y_excess_median', 'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
FAMILY = {'Large Cap': 'large', 'Large & Mid Cap': 'large', 'Flexi Cap': 'large', 'Focused': 'large', 'ELSS': 'large', 'Value / Contra': 'large',
          'Mid Cap': 'smallmid', 'Small Cap': 'smallmid', 'Multi Cap': 'smallmid'}
CATS = list(FAMILY); MIN_IC = 0.03; CAND = ['lean', 'category', 'shrunk', 'family', 'blend']

M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
M = M[M.cat.isin(CATS)].copy(); M['fam'] = M.cat.map(FAMILY)
G = ['as_of', 'cat']
M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
for s in SIGNALS: M['p_' + s] = M.groupby(G)[s].rank(pct=True)
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
P = lambda f: M['p_' + f].fillna(.5)
M['s_lean'] = .5 * (P('mom_1m') + P('mom_3m') + P('mom_6m') + P('mom_12m')) / 4 + .3 * (P('style_small') + P('style_mid')) / 2 + .2 * P('upside_capture_3y')
RF = 0.065
M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y; M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
v3 = pd.concat([score_group(g.assign(peer_group=g.cat), C.V3_ACTIVE_EQUITY_PROTOCOL) for _, g in M.groupby(G)]).sort_index()
M['s_v3'] = v3.score.values


def ic(df, col):
    x = df[['as_of', col, 'p_fwd']].dropna()
    if len(x) < 40: return np.nan
    r = x.groupby('as_of').apply(lambda g: g[col].corr(g.p_fwd) if len(g) >= 5 else np.nan).dropna()
    return r.mean() if len(r) >= 8 else np.nan


def fit(end):
    """Weights per (kind, category) from data up to `end`; the two halves split the window in the middle."""
    f = M[M.as_of <= end]; mid = f.as_of.min() + (pd.Timestamp(end) - f.as_of.min()) / 2
    def table(df):
        out = {}
        for s in SIGNALS:
            a, b, m = ic(df[df.as_of <= mid], 'p_' + s), ic(df[df.as_of > mid], 'p_' + s), ic(df, 'p_' + s)
            if np.isfinite([a, b, m]).all() and np.sign(a) == np.sign(b) and abs(m) >= MIN_IC: out[s] = m
        return out
    allw = table(f); famw = {k: table(f[f.fam == k]) for k in set(FAMILY.values())}; W = {}
    for c in CATS:
        cw = table(f[f.cat == c])
        W['category', c] = cw
        W['shrunk', c] = {s: (v + allw[s]) / 2 for s, v in cw.items() if s in allw and np.sign(v) == np.sign(allw[s])}
        W['family', c] = famw[FAMILY[c]]
    return W


def score(W, tag):
    for kind in ('category', 'shrunk', 'family'):
        sc = pd.Series(np.nan, index=M.index)
        for c in CATS:
            w = W[kind, c]; m = M.cat == c
            if not w: sc[m] = M.s_lean[m]; continue                       # nothing stable to fit: fall back to lean
            tot = sum(abs(v) for v in w.values())
            sc[m] = sum(abs(v) / tot * (P(s)[m] if v > 0 else 1 - P(s)[m]) for s, v in w.items())
        M[f's_{kind}_{tag}'] = sc
    M[f's_lean_{tag}'] = M.s_lean
    r = lambda col: M.groupby(G)[col].rank(pct=True)
    M[f's_blend_{tag}'] = (r('s_lean') + r(f's_shrunk_{tag}')) / 2


W1 = fit('2014-12-31'); score(W1, 'val')
val = M[(M.as_of >= '2016-01-01') & (M.as_of <= '2017-12-31')]
choice, vrows = {}, []
for c in CATS:
    d = val[val.cat == c]; ics = {k: ic(d, f's_{k}_val') for k in CAND}
    choice[c] = max(ics, key=lambda k: -9 if not np.isfinite(ics[k]) else ics[k]); vrows.append({"cat": c, "chosen": choice[c], **{"ic_" + k: ics[k] for k in CAND}})
V = pd.DataFrame(vrows)
W2 = fit('2017-12-31'); score(W2, 'test')
M['s_chosen'] = np.nan
for c in CATS: M.loc[M.cat == c, 's_chosen'] = M.loc[M.cat == c, f's_{choice[c]}_test']
test = M[M.as_of >= '2019-01-01'].copy()
COLS = {'chosen': 's_chosen', 'lean': 's_lean', 'category': 's_category_test', 'shrunk': 's_shrunk_test', 'family': 's_family_test', 'blend': 's_blend_test', 'v3': 's_v3'}
for k, col in COLS.items(): test['r_' + k] = test.groupby(G)[col].rank(pct=True)
X1 = M.set_index(['as_of', 'code']).fwd_1m; dates = sorted(test.as_of.unique())


def sip(k, c, months):
    pick = {t: list(g.code[g['r_' + k] >= .9]) for t, g in test[test.cat == c].groupby('as_of')}; out = []
    for i0 in range(len(dates) - months):
        units, put = {}, 0.0
        for j in range(months):
            t = dates[i0 + j]; ch = pick.get(t, [])
            if ch:
                for code in ch: units[code] = units.get(code, 0) + 1 / len(ch)
                put += 1
            for code in list(units):
                r = X1.get((t, code), np.nan)
                if np.isfinite(r): units[code] *= 1 + r
        if put: out.append(sum(units.values()) / put - 1)
    return (np.array(out) > 0).mean() if out else np.nan


rows = []
for c in CATS + ['ALL']:
    d = test if c == 'ALL' else test[test.cat == c]
    for k in COLS:
        ap, cc = d[d['r_' + k] >= .9], d[d['r_' + k] <= .3]
        row = dict(category=c, model=k, chosen=choice.get(c, ''), aplus_beat_1y=(ap.fwd_1y.dropna() > 0).mean(), c_beat_1y=(cc.fwd_1y.dropna() > 0).mean(),
                   all_beat_1y=(d.fwd_1y.dropna() > 0).mean(), aplus_excess_1y=ap.fwd_1y.mean(), aplus_beat_3y=(ap.fwd_3y.dropna() > 0).mean(), ic=ic(d, COLS[k]))
        if c != 'ALL' and k in ('chosen', 'lean', 'blend', 'v3'): row['sip12'] = sip(k, c, 12); row['sip36'] = sip(k, c, 36)
        rows.append(row)
R = pd.DataFrame(rows); R.to_csv('audit/research_category_select.csv', index=False); V.to_csv('audit/research_category_select_validation.csv', index=False)
pd.set_option('display.width', 250)
print('=== step 1: validation 2016-17 (fit 2012-14): average monthly rank IC, and the model chosen ==='); print(V.round(3).to_string(index=False))
print('\n=== step 2: unseen 2019-26, A+ ahead of the benchmark next year ===')
print(R.pivot(index='category', columns='model', values='aplus_beat_1y')[list(COLS)].round(3).to_string())
print('\nbottom 30% ahead next year:'); print(R.pivot(index='category', columns='model', values='c_beat_1y')[['chosen', 'lean', 'blend', 'v3']].round(3).to_string())
print('\naverage A+ return over the benchmark, next year:'); print(R.pivot(index='category', columns='model', values='aplus_excess_1y')[['chosen', 'lean', 'blend', 'v3']].round(4).to_string())
print('\nrank IC on unseen years:'); print(R.pivot(index='category', columns='model', values='ic')[list(COLS)].round(3).to_string())
print('\n12-month SIP rule:'); print(R[R.category != 'ALL'].pivot(index='category', columns='model', values='sip12')[['chosen', 'lean', 'blend', 'v3']].round(2).to_string())
print('\n36-month SIP rule:'); print(R[R.category != 'ALL'].pivot(index='category', columns='model', values='sip36')[['chosen', 'lean', 'blend', 'v3']].round(2).to_string())
