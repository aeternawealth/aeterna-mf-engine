"""Extra candidate metrics for the backtest (point-in-time, data <= as_of only)."""
import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np
M=pd.read_csv('audit/bt_metrics.csv',parse_dates=['as_of'])
src={}
import glob, os
for f in glob.glob('data/nav/*.csv')+glob.glob('data/nav_dead/*.csv'): src[int(os.path.basename(f)[:-4])]=f
cache={}
def nav(c):
    if c not in cache: cache[c]=pd.read_csv(src[c],parse_dates=['date']).set_index('date')['nav']
    return cache[c]
rows=[]
for r in M[['code','as_of']].itertuples(index=False):
    if r.code not in src: continue
    n=nav(r.code); n=n[n.index<=r.as_of]
    d={'code':r.code,'as_of':r.as_of}
    for k in range(5):   # non-overlapping 1-year windows ending at as_of, as_of-1y, ...
        e=r.as_of-pd.DateOffset(years=k); s=e-pd.DateOffset(years=1)
        a,b=n[n.index<=s],n[n.index<=e]
        d[f'yr{k}']=b.iloc[-1]/a.iloc[-1]-1 if len(a) and (s-a.index[-1]).days<10 else np.nan
    n5=n[n.index>r.as_of-pd.DateOffset(years=5)]
    if len(n5)>250:
        dd=n5/n5.cummax()-1; t=dd.idxmin(); peak=n5[:t].idxmax()
        rec=n5[t:][n5[t:]>=n5[peak]]
        d['recovery_days']=(rec.index[0]-peak).days if len(rec) else (r.as_of-peak).days*1.5  # not yet recovered: penalised
    rows.append(d)
X=pd.DataFrame(rows); X.to_csv('audit/bt_extra.csv',index=False); print(len(X))
