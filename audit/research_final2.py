"""Final package, v7: post-COVID data weighted twice as much, and the live tier rules applied in the test.

Periods: pre-COVID = ratings dated 2012-01 .. 2020-02, post-COVID = 2020-04 .. 2025-10 (1-year outcomes known).
Decision score for a candidate = (1 x pre-COVID + 2 x post-COVID) / 3 of the average of four results:
  A+ ahead of the benchmark next year, review rule ahead after 1 year, A+ ahead over 3 years, review rule after 3 years.
A more complex candidate must beat the core recipe by 2 points on that score to be chosen (smaller gaps are noise:
a category has 2-3 A+ funds a month).

Tiers, as on the site: rank within the peer group each month. A+ = top 10% (at least 3 places where 15+ funds) and
ahead of the benchmark both over 3 years and in the median rolling 3-year window; A = next, up to the top 30%, and
ahead on at least one of the two; C = bottom 30%; B = the rest (including funds held back by the check).
Review rule: new money to A+ funds (equal amounts); a fund is kept while rated A+ or A; once rated B or C it is
replaced, but only after it has been held 12 months.
Market mode: when the category's own index is below its 200-day average on the rating date, the score becomes half the
category model and half the rebound model (upside capture 30, beta 25, size 25, value 20). Each candidate is tested
with and without it.
Candidates (first principles):
  core       momentum over 1-12 months 55, upside capture 30, size tilt 15
  mandate    built from the category's rules (small-cap purity, value tilt, conviction, the free 25% of multi caps...)
  quality    momentum 45, upside 20, information and capture ratio 20, size 15
  comp       ridge regression on 31 measures, refitted each year on earlier data, recent years weighted more
             (half-life 3 years)
  blend      50/50 by rank of core and comp
Audit of the chosen package: tier order (A+ > A > B > C), turnover of the A+ list, results in the years large caps
led, after falls and after the market's strongest years, and the effect of each rule switched off."""
import os, warnings; warnings.filterwarnings('ignore')
GUARD = os.environ.get('GUARD', '1') == '1'   # the 'ahead of the index' check on A+ and A
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge

CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
SIG = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_mom', 'style_val', 'style_lowvol', 'style_qual', 'style_n50',
       'upside_capture_3y', 'downside_capture_3y', 'capture_ratio_3y', 'alpha_3y', 'info_ratio_3y', 'sharpe_3y', 'sortino_3y', 'beta_3y', 'vol_3y',
       'tracking_err_3y', 'excess_cagr_1y', 'excess_cagr_3y', 'excess_cagr_5y', 'roll1y_hit_rate', 'roll1y_excess_median', 'roll3y_excess_median',
       'roll3y_hit_rate', 'roll3y_excess_p10', 'max_drawdown_3y', 'age_years']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
sp = M[M.cat.isin(['Small Cap', 'Large Cap'])].groupby(['as_of', 'cat']).cagr_1y.median().unstack()
NEXT = (sp['Small Cap'] - sp['Large Cap']).shift(-12)
M = M[M.cat.isin(CATS)].copy()
RF = .065; M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y; M['alpha_3y'] = M.cagr_3y - (RF + M.beta_3y * (M.bench_cagr_3y - RF))
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
X = pd.concat([M.groupby(G)[s].rank(pct=True).fillna(.5) for s in SIG], axis=1); X.columns = SIG
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
M['period'] = np.where(M.as_of <= '2020-02-29', 'pre', np.where(M.as_of >= '2020-04-01', 'post', 'covid'))
M['fall'] = M.mkt_above_200d == 0; M['large_led'] = M.as_of.map(NEXT) < 0
hot_cut = M.groupby('as_of').mkt_12m.first().quantile(.8); M['hot'] = M.mkt_12m >= hot_cut
MOM = lambda *w: sum(X[f'mom_{x}m'] for x in w) / len(w)
UP, Q, V, CONV, BETA, YOUNG = X.upside_capture_3y, (X.info_ratio_3y + X.capture_ratio_3y) / 2, X.style_val, X.tracking_err_3y, X.beta_3y, 1 - X.age_years
SZF = (X.style_small + X.style_mid) / 2
SIZE = {c: SZF for c in CATS}; SIZE['Mid Cap'] = (X.style_small + 1 - X.style_n50) / 2; SIZE['Small Cap'] = 1 - X.style_mid; SIZE['Multi Cap'] = 1 - X.style_n50
REB = lambda c: .30 * UP + .25 * BETA + .20 * V + .25 * SIZE[c]
core = {c: .55 * MOM(1, 3, 6, 12) + .30 * UP + .15 * SIZE[c] for c in CATS}
mandate = {'Large Cap': .50 * MOM(1, 3, 6) + .35 * UP + .15 * SIZE['Large Cap'],
           'Large & Mid Cap': .45 * MOM(3, 6) + .25 * UP + .15 * V + .15 * SIZE['Large & Mid Cap'],
           'Mid Cap': .55 * MOM(3, 6, 12) + .30 * UP + .15 * SIZE['Mid Cap'],
           'Small Cap': .50 * MOM(1, 3) + .20 * BETA + .15 * YOUNG + .15 * SIZE['Small Cap'],
           'Flexi Cap': .45 * MOM(6, 12) + .20 * UP + .20 * Q + .15 * SIZE['Flexi Cap'],
           'Multi Cap': .50 * MOM(3, 6, 12) + .35 * UP + .15 * SIZE['Multi Cap'],
           'Focused': .40 * MOM(3, 6) + .25 * CONV + .20 * UP + .15 * SIZE['Focused'],
           'ELSS': .45 * MOM(1, 3, 6, 12) + .25 * UP + .15 * CONV + .15 * SIZE['ELSS'],
           'Value / Contra': .35 * V + .35 * MOM(3, 6) + .15 * UP + .15 * SIZE['Value / Contra']}
quality = {c: .45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q + .15 * SIZE[c] for c in CATS}
comp = pd.Series(np.nan, index=M.index)
for Y in range(2013, 2027):
    tr = (M.as_of < pd.Timestamp(f'{Y - 1}-01-01')) & M.p_fwd.notna(); te = M.as_of.dt.year == Y
    if tr.sum() < 2000 or not te.any(): continue
    w = 0.5 ** ((Y - 1 - M.as_of[tr].dt.year) / 3)
    comp[te] = Ridge(alpha=50).fit(X[tr], M.p_fwd[tr], sample_weight=w).predict(X[te])
rk = lambda s: s.groupby([M.as_of, M.cat]).rank(pct=True)
compr = rk(comp)
CAND = {}
for c in CATS:
    CAND[c] = {'core': core[c], 'mandate': mandate[c], 'quality': quality[c], 'comp': compr, 'blend': .5 * rk(core[c]) + .5 * compr}


def tiers(score, min3=True, guard=None):
    """A+ / A / B / C from a score, per peer group and month, with the site's rules."""
    guard = GUARD if guard is None else guard
    df = pd.DataFrame({'s': score, 'as_of': M.as_of, 'cat': M.cat, 'e3': M.excess_cagr_3y, 'rm': M.roll3y_excess_median})
    df = df[df.s.notna()]
    n = df.groupby(['as_of', 'cat']).s.transform('size'); pos = df.groupby(['as_of', 'cat']).s.rank(ascending=False, method='first')
    k = np.maximum(np.ceil(.1 * n), np.where((n >= 15) & min3, 3, 1)); k30 = np.ceil(.3 * n)
    both, one = (df.e3 > 0) & (df.rm > 0), (df.e3 > 0) | (df.rm > 0)
    t = np.where(pos <= k, 'A+', np.where(pos <= k30, 'A', np.where(pos > n - np.floor(.3 * n), 'C', 'B')))
    if guard:
        t = np.where((t == 'A+') & ~both, np.where(one, 'A', 'B'), t); t = np.where((t == 'A') & ~one, 'B', t)
    return pd.Series(t, index=df.index).reindex(M.index)


DATES = sorted(M.as_of.unique())


def review(tier, c):
    m = M.cat == c; d = M[m].assign(t=tier[m])
    TT = {t: dict(zip(g.code, g.t)) for t, g in d.groupby('as_of')}; RR = {t: dict(zip(g.code, g.fwd_1m)) for t, g in d.groupby('as_of')}
    ds = sorted(TT); o12, o36 = {}, {}
    for i0, t0 in enumerate(ds):
        lots, cash = [], 1.0
        for j in range(36):
            if i0 + j >= len(ds): break
            t = ds[i0 + j]; tt, rr = TT[t], RR[t]; keep = []
            for code, v, age in lots:
                if code not in tt or (age >= 12 and tt[code] in ('B', 'C')): cash += v
                else: keep.append([code, v, age])
            lots = keep; ap = [x for x, y in tt.items() if y == 'A+']
            if cash > 0 and ap:
                for x in ap: lots.append([x, cash / len(ap), 0])
                cash = 0.0
            ok = False
            for lot in lots:
                x = rr.get(lot[0], np.nan)
                if np.isfinite(x): lot[1] *= 1 + x; ok = True
                lot[2] += 1
            if ok and j == 11: o12[t0] = cash + sum(l[1] for l in lots)
            if ok and j == 35: o36[t0] = cash + sum(l[1] for l in lots)
    return pd.Series(o12), pd.Series(o36)


def evaluate(tier, c):
    m = M.cat == c; d = M[m].assign(t=tier[m]); r12, r36 = review(tier, c); out = {}
    for p in ('pre', 'post'):
        dp = d[d.period == p]; per = (lambda s: s[(s.index <= pd.Timestamp('2020-02-29'))] if p == 'pre' else s[(s.index >= pd.Timestamp('2020-04-01'))])
        ap = dp[dp.t == 'A+']
        out[p] = dict(aplus_1y=(ap.fwd_1y.dropna() > 0).mean(), aplus_3y=(ap.fwd_3y.dropna() > 0).mean(),
                      review_1y=(per(r12) > 1).mean(), review_3y=(per(r36) > 1).mean(),
                      **{f'{t}_1y': (dp[dp.t == t].fwd_1y.dropna() > 0).mean() for t in ('A', 'B', 'C')},
                      all_1y=(dp.fwd_1y.dropna() > 0).mean(), all_3y=(dp.fwd_3y.dropna() > 0).mean(), aplus_per_month=ap.groupby('as_of').size().mean())
        out[p]['core4'] = np.nanmean([out[p][k] for k in ('aplus_1y', 'review_1y', 'aplus_3y', 'review_3y')])
    ap = d[d.t == 'A+']
    out['stress'] = dict(large_led=(ap[ap.large_led].fwd_1y.dropna() > 0).mean(), after_fall=(ap[ap.fall].fwd_1y.dropna() > 0).mean(),
                         after_hot=(ap[ap.hot].fwd_1y.dropna() > 0).mean(), all_large_led=(d[d.large_led].fwd_1y.dropna() > 0).mean())
    out['decision'] = (out['pre']['core4'] + 2 * out['post']['core4']) / 3
    return out


rows, best = [], {}
for c in CATS:
    res = {}
    for k, sc in CAND[c].items():
        for mode in ('fixed', 'market mode'):
            s = sc if mode == 'fixed' else pd.Series(np.where(M.fall, .5 * rk(sc) + .5 * rk(REB(c)), rk(sc)), index=M.index)
            e = evaluate(tiers(s), c); res[(k, mode)] = e
            rows.append(dict(category=c, model=k, mode=mode, decision=e['decision'], **{f'{p}_{x}': e[p][x] for p in ('pre', 'post') for x in e[p]}, **e['stress']))
    base = res[('core', 'market mode')]['decision']
    pick = max(res, key=lambda x: res[x]['decision'] - (0 if x[0] == 'core' else .02))
    best[c] = pick
R = pd.DataFrame(rows); R['chosen'] = R.apply(lambda r: best[r.category] == (r.model, r['mode']), axis=1); R.to_csv('audit/research_final2_results.csv' if GUARD else 'audit/research_final2_noguard.csv', index=False)
pd.set_option('display.width', 260); pd.set_option('display.max_columns', 40)
print('=== decision score per candidate (1 x pre-COVID + 2 x post-COVID; average of A+ 1y, review 1y, A+ 3y, review 3y) ===')
print(R.pivot_table(index='category', columns=['mode', 'model'], values='decision').loc[CATS].round(3).to_string())
print('\nchosen:', {c: f'{a} / {b}' for c, (a, b) in best.items()})
C = R[R.chosen].set_index('category').loc[CATS]
cols = ['model', 'mode', 'post_aplus_1y', 'post_review_1y', 'post_aplus_3y', 'post_review_3y', 'post_all_1y', 'post_all_3y', 'pre_aplus_1y', 'pre_review_3y', 'post_aplus_per_month']
print('\n=== chosen per category: post-COVID results (and two pre-COVID ones) ===')
print(C[cols].round(2).to_string())
print('\n=== audit 1: tier order post-COVID (share ahead of the benchmark next year) ===')
print(C[['post_aplus_1y', 'post_A_1y', 'post_B_1y', 'post_C_1y', 'post_all_1y']].round(2).to_string())
print('\n=== audit 2: stress tests (A+ ahead next year) ===')
print(C[['large_led', 'all_large_led', 'after_fall', 'after_hot']].round(2).to_string())
# audit 3: each rule switched off, on the chosen models
print('\n=== audit 3: decision score of the chosen model with each rule switched off ===')
for c in CATS:
    k, mode = best[c]; sc = CAND[c][k]
    s_mode = pd.Series(np.where(M.fall, .5 * rk(sc) + .5 * rk(REB(c)), rk(sc)), index=M.index)
    s_use = s_mode if mode == 'market mode' else sc
    alts = {'as chosen': evaluate(tiers(s_use), c)['decision'], 'no 3-fund minimum': evaluate(tiers(s_use, min3=False), c)['decision'],
            'no index check' if GUARD else 'with index check': evaluate(tiers(s_use, guard=not GUARD), c)['decision'], 'other mode': evaluate(tiers(sc if mode == 'market mode' else s_mode), c)['decision']}
    print(f'  {c:16}', '  '.join(f'{a} {v:.3f}' for a, v in alts.items()))
# audit 4: turnover of the A+ list
print('\n=== audit 4: share of A+ funds still A+ or A the next month, and still A+ 12 months later ===')
for c in CATS:
    k, mode = best[c]; sc = CAND[c][k]; s = pd.Series(np.where(M.fall, .5 * rk(sc) + .5 * rk(REB(c)), rk(sc)), index=M.index) if mode == 'market mode' else sc
    t = tiers(s); d = M[M.cat == c].assign(t=t[M.cat == c]).sort_values(['code', 'as_of'])
    d['t1'] = d.groupby('code').t.shift(-1); d['t12'] = d.groupby('code').t.shift(-12); ap = d[d.t == 'A+']
    print(f'  {c:16} next month A+/A {ap.t1.dropna().isin(["A+", "A"]).mean():.0%}   A+ after 12 months {(ap.t12.dropna() == "A+").mean():.0%}')
