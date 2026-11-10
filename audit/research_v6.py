"""v6: a model for each equity category, designed from its SEBI mandate, with the size tilt held at 15%.

Building blocks (percentiles within the peer group each month; higher is better unless noted)
  MOM(w)  average of the fund's return over its benchmark in the windows w (months)
  UP      share of the market's rises captured over 3 years
  Q       quality: average of the information ratio and the capture ratio (rises captured / falls taken), 3 years
  V       tilt towards value stocks (weekly slope on Nifty200 Value 30 over the benchmark)
  CONV    conviction: tracking error against the benchmark (focused funds)
  BETA    beta (small caps: staying fully exposed to the asset class)
  YOUNG   younger funds score higher (small caps: smaller, newer funds can still buy small companies)
  SIZE    the 15% size tilt, defined for the category:
            free-choice categories    tilt towards small and mid caps (average of the two)
            Large Cap                 the same, for the 20% a large-cap fund may hold outside the top 100
            Mid Cap                   drift towards small caps, and away from the Nifty 50
            Small Cap                 purity: less drift up into mid caps
            Multi Cap                 how the free 25% is used: away from the Nifty 50
Candidates per category: 'base' (momentum, upside, size), 'mandate' (built from the category's rules), and
'quality' (base plus quality). The candidate is chosen on 2012-18 only (A+ ahead of the benchmark over the next
year, and the review rule after 1 year, averaged); 2019-25 is reported as the test.
Reported: A+ ahead over the next 1 and 3 years, the A+ basket, the review rule (buy A+, hold while A or better,
replace below A after 12 months), and A+ in the years large caps led, with 'all funds' alongside."""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

CATS = ['Large Cap', 'Large & Mid Cap', 'Mid Cap', 'Small Cap', 'Flexi Cap', 'Multi Cap', 'Focused', 'ELSS', 'Value / Contra']
NEED = ['mom_1m', 'mom_3m', 'mom_6m', 'mom_12m', 'style_small', 'style_mid', 'style_n50', 'style_val', 'upside_capture_3y', 'downside_capture_3y',
        'info_ratio_3y', 'capture_ratio_3y', 'tracking_err_3y', 'beta_3y', 'age_years']
M = pd.read_csv('audit/bt_metrics_long.csv.gz', low_memory=False); M['as_of'] = pd.to_datetime(M.as_of)
M['cat'] = M.category.replace({'Value': 'Value / Contra', 'Contra': 'Value / Contra'})
sp = M[M.cat.isin(['Small Cap', 'Large Cap'])].groupby(['as_of', 'cat']).cagr_1y.median().unstack()
NEXT = (sp['Small Cap'] - sp['Large Cap']).shift(-12)          # small minus large over the following year
M = M[M.cat.isin(CATS)].copy(); M['capture_ratio_3y'] = M.upside_capture_3y / M.downside_capture_3y
G = ['as_of', 'cat']; M = M[M.groupby(G).code.transform('size') >= 5].reset_index(drop=True)
P = {s: M.groupby(G)[s].rank(pct=True).fillna(.5) for s in NEED}
M['large_led'] = M.as_of.map(NEXT) < 0
MOM = lambda *w: sum(P[f'mom_{x}m'] for x in w) / len(w)
UP, Q, V, CONV, BETA, YOUNG = P['upside_capture_3y'], (P['info_ratio_3y'] + P['capture_ratio_3y']) / 2, P['style_val'], P['tracking_err_3y'], P['beta_3y'], 1 - P['age_years']
SZ_FREE = (P['style_small'] + P['style_mid']) / 2
SIZE = {'Large Cap': SZ_FREE, 'Large & Mid Cap': SZ_FREE, 'Flexi Cap': SZ_FREE, 'Focused': SZ_FREE, 'ELSS': SZ_FREE, 'Value / Contra': SZ_FREE,
        'Mid Cap': (P['style_small'] + 1 - P['style_n50']) / 2, 'Small Cap': 1 - P['style_mid'], 'Multi Cap': 1 - P['style_n50']}
S = .15
CAND = {   # category -> name -> (score, plain description)
    'Large Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 1-12m 55, upside 30, size 15'),
                  'mandate': (.50 * MOM(1, 3, 6) + .35 * UP, 'momentum 1-6m 50 (large caps re-rate fast), upside 35, size in the 20% sleeve 15'),
                  'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
    'Large & Mid Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
                        'mandate': (.45 * MOM(3, 6) + .25 * UP + .15 * V, 'momentum 3-6m 45, upside 25, value tilt 15, size 15'),
                        'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
    'Mid Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
                'mandate': (.55 * MOM(3, 6, 12) + .30 * UP, 'momentum 3-12m 55, upside 30, drift to small caps and away from the Nifty 50 15'),
                'quality': (.45 * MOM(3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
    'Small Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, purity 15'),
                  'mandate': (.50 * MOM(1, 3) + .20 * BETA + .15 * YOUNG, 'momentum 1-3m 50, beta 20, younger/smaller fund 15, purity (less mid-cap drift) 15'),
                  'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, purity 15')},
    'Flexi Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
                  'mandate': (.45 * MOM(6, 12) + .20 * UP + .20 * Q, 'momentum 6-12m 45, upside 20, quality 20, size 15'),
                  'quality': (.40 * MOM(1, 3, 6, 12) + .15 * UP + .30 * Q, 'momentum 40, upside 15, quality 30, size 15')},
    'Multi Cap': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, away from the Nifty 50 15'),
                  'mandate': (.50 * MOM(3, 6, 12) + .35 * UP, 'momentum 3-12m 50, upside 35, the free 25% away from the Nifty 50 15'),
                  'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, away from the Nifty 50 15')},
    'Focused': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
                'mandate': (.40 * MOM(3, 6) + .25 * CONV + .20 * UP, 'momentum 3-6m 40, conviction 25, upside 20, size 15'),
                'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
    'ELSS': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
             'mandate': (.45 * MOM(1, 3, 6, 12) + .25 * UP + .15 * CONV, 'momentum 45, upside 25, conviction 15 (3-year lock-in rewards a steady view), size 15'),
             'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
    'Value / Contra': {'base': (.55 * MOM(1, 3, 6, 12) + .30 * UP, 'momentum 55, upside 30, size 15'),
                       'mandate': (.35 * V + .35 * MOM(3, 6) + .15 * UP, 'true-to-label value tilt 35, momentum 3-6m 35, upside 15, size 15'),
                       'quality': (.45 * MOM(1, 3, 6, 12) + .20 * UP + .20 * Q, 'momentum 45, upside 20, quality 20, size 15')},
}
LEAN = .5 * MOM(1, 3, 6, 12) + .3 * SZ_FREE + .2 * UP            # the lean model, for comparison
dates = sorted(M.as_of.unique())


def hold(d, col):
    """The review rule within one category: relative value after 12 and 36 months, per start month."""
    rk = {t: dict(zip(g.code, g[col])) for t, g in d.groupby('as_of')}; ret = {t: dict(zip(g.code, g.fwd_1m)) for t, g in d.groupby('as_of')}
    ds = sorted(rk); o = {12: [], 36: []}; st = {12: [], 36: []}
    for i0, t0 in enumerate(ds):
        lots, cash = [], 1.0
        for j in range(36):
            if i0 + j >= len(ds): break
            t = ds[i0 + j]; r_t, x_t = rk[t], ret[t]; keep = []
            for code, v, age in lots:
                if code not in r_t or (age >= 12 and r_t[code] < .7): cash += v
                else: keep.append([code, v, age])
            lots = keep
            ap = [c for c, r in r_t.items() if r >= .9]
            if cash > 0 and ap:
                for c in ap: lots.append([c, cash / len(ap), 0])
                cash = 0.0
            ok = False
            for lot in lots:
                x = x_t.get(lot[0], np.nan)
                if np.isfinite(x): lot[1] *= 1 + x; ok = True
                lot[2] += 1
            if j + 1 in o and ok: o[j + 1].append(cash + sum(l[1] for l in lots)); st[j + 1].append(t0)
    return {k: pd.Series(v, index=st[k]) for k, v in o.items()}


def stats(d, col):
    ap, cc = d[d[col] >= .9], d[d[col] <= .3]; out = {}
    for h, c in (('1y', 'fwd_1y'), ('3y', 'fwd_3y')):
        out['aplus_' + h] = (ap[c].dropna() > 0).mean(); out['basket_' + h] = (ap.dropna(subset=[c]).groupby('as_of')[c].mean() > 0).mean()
        out['c_' + h] = (cc[c].dropna() > 0).mean(); out['all_' + h] = (d[c].dropna() > 0).mean()
    out['aplus_large_led'] = (ap[ap.large_led].fwd_1y.dropna() > 0).mean()
    return out


rows, chosen = [], {}
for c in CATS:
    m = M.cat == c; d0 = M[m].copy()
    models = {k: ((sc + S * SIZE[c]) if True else sc) for k, (sc, _) in CAND[c].items()}; models['lean (now)'] = LEAN
    res = {}
    for k, sc in models.items():
        d0['r'] = sc[m].groupby([d0.as_of]).rank(pct=True); h = hold(d0, 'r')
        for era, msk in (('2012-18', d0.as_of <= '2018-12-31'), ('2019-25', d0.as_of > '2018-12-31')):
            st = stats(d0[msk], 'r')
            for hz in (12, 36):
                hh = h[hz]; hh = hh[(hh.index <= pd.Timestamp('2018-12-31')) if era == '2012-18' else (hh.index > pd.Timestamp('2018-12-31'))]
                st[f'review_{hz // 12}y'] = (hh > 1).mean() if len(hh) else np.nan
            st.update(category=c, model=k, era=era, desc=CAND[c][k][1] if k in CAND[c] else 'momentum 50, size 30, upside 20'); rows.append(st); res[(k, era)] = st
    fit = {k: np.nanmean([res[(k, '2012-18')]['aplus_1y'], res[(k, '2012-18')]['review_1y']]) for k in CAND[c]}
    chosen[c] = max(fit, key=fit.get)
R = pd.DataFrame(rows); R['chosen'] = R.apply(lambda r: chosen[r.category] == r.model, axis=1); R.to_csv('audit/research_v6_results.csv', index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 110)
for c in CATS:
    print(f'\n=== {c}: chosen on 2012-18 -> {chosen[c]}: {CAND[c][chosen[c]][1]}')
    t = R[R.category == c].pivot(index='model', columns='era', values=['aplus_1y', 'review_1y', 'aplus_3y', 'review_3y', 'aplus_large_led'])
    t[('all funds 1y', '2019-25')] = R[(R.category == c) & (R.era == '2019-25')].all_1y.iloc[0]
    print(t.round(2).to_string())
