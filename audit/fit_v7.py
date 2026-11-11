"""Weights of the comprehensive model used for Large & Mid Cap in v7 (audit/research_final2.py, 'comp'): a ridge
regression of the next year's peer-group percentile on the 31 measures' percentiles, all active equity funds, every
month with a known 1-year outcome, each year weighted half as much as the year after it (half-life 3 years).
Refit once a year (python audit/fit_v7.py) and commit audit/equity_models_v7.json."""
import json, warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
from sklearn.linear_model import Ridge
exec(open('audit/research_final2.py').read().split("M['p_fwd'] = ")[0])          # same data preparation as the test
M['p_fwd'] = M.groupby(G).fwd_1y.rank(pct=True)
ok = M.p_fwd.notna(); last = M.as_of[ok].max().year
w = 0.5 ** ((last - M.as_of[ok].dt.year) / 3)
co = Ridge(alpha=50).fit(X[ok], M.p_fwd[ok], sample_weight=w).coef_
tot = np.abs(co).sum()
out = {'fitted_to': str(M.as_of[ok].max().date()), 'half_life_years': 3, 'rows': int(ok.sum()),
       'weights': {s: round(float(v / tot * 100), 2) for s, v in sorted(zip(SIG, co), key=lambda x: -abs(x[1])) if abs(v / tot) >= .005}}
json.dump(out, open('audit/equity_models_v7.json', 'w'), indent=1)
print(out['fitted_to'], out['rows']); print(', '.join(f'{k} {v:+.1f}' for k, v in out['weights'].items()))
