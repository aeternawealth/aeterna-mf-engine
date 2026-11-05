import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json
from engine import config as C
from engine.protocols import score_group
M=pd.read_csv('audit/bt_metrics.csv'); M['as_of']=pd.to_datetime(M.as_of)
RF=0.065
M['capture_ratio']=M.upside_capture_3y/M.downside_capture_3y
M['alpha_3y']=M.cagr_3y-(RF+M.beta_3y*(M.bench_cagr_3y-RF))
V={
 'v2_current': {k:v for k,v in C.ACTIVE_EQUITY_PROTOCOL.items()},
 'v3_beta_neutral': {'roll3y_excess_median':('L',15,True),'roll3y_hit_rate':('L',10,True),'info_ratio_3y':('R',15,True),
    'capture_ratio':('D',12,True),'alpha_3y':('D',8,True),'roll3y_excess_p10':('C',10,True),'roll1y_hit_rate':('C',10,True)},
 'only_long_run_excess': {'roll3y_excess_median':('L',15,True),'roll3y_hit_rate':('L',10,True)},
 'only_recent_3y_IR': {'info_ratio_3y':('R',1,True)},
 'only_downside': {'downside_capture_3y':('D',12,False),'max_drawdown_3y':('D',8,True)},
 'naive_3y_return': {'cagr_3y':('N',1,True)},
}
rows=[]
for name,proto in V.items():
    parts=[]
    for (t,pg),g in M.groupby(['as_of','peer_group']):
        if len(g)<5: continue
        s=score_group(g,proto); s['pct']=s.score.rank(pct=True); parts.append(s)
    S=pd.concat(parts)
    for h in (1,3,5):
        col=f'fwd_{h}y'; X=S[S[col].notna()]
        ic=X.groupby(['as_of']).apply(lambda D: np.nanmean([g.score.corr(g[col],method='spearman') for _,g in D.groupby('peer_group')]))
        top=X[X.pct>=0.9]; bot=X[X.pct<=0.3]
        rows.append(dict(variant=name,h=f'{h}Y',ic=round(ic.mean(),3),ic_t=round(ic.mean()/ (ic.std()/np.sqrt(len(ic))),2),
            top10_beat=round((top[col]>0).mean(),3),top10_mean=round(top[col].mean(),4),bottom30_mean=round(bot[col].mean(),4),
            spread=round(top[col].mean()-bot[col].mean(),4),n_top=len(top)))
R=pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('audit/bt_variants.csv',index=False)
# style diagnosis: beta of top-decile vs bottom by variant v2
