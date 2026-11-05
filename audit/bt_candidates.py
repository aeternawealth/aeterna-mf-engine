import pandas as pd, numpy as np
M=pd.read_csv('audit/bt_metrics.csv',parse_dates=['as_of']); X=pd.read_csv('audit/bt_extra.csv',parse_dates=['as_of'])
S=pd.read_csv('audit/bt_scored.csv',parse_dates=['as_of'])[['code','as_of','peer_group','score']].rename(columns={'peer_group':'pg2'})
D=M.merge(X,on=['code','as_of'],how='left').merge(S,on=['code','as_of'],how='left')
D['pg']=D.pg2.fillna(D.peer_group)
RF=0.065
D['sharpe_3y']=(D.cagr_3y-RF)/D.vol_3y
# peer-relative consistency: share of last 5 yearly windows in top half of peer group
for k in range(5): D[f'r{k}']=D.groupby(['as_of','pg'])[f'yr{k}'].rank(pct=True)
R=D[[f'r{k}' for k in range(5)]]
D['peer_consistency']=(R>0.5).sum(axis=1)/R.notna().sum(axis=1)
D.loc[R.notna().sum(axis=1)<3,'peer_consistency']=np.nan
D['peer_rank_stability']=-R.std(axis=1)            # steadier percentile = higher
D.loc[R.notna().sum(axis=1)<3,'peer_rank_stability']=np.nan
D['neg_recovery_days']=-D.recovery_days
cands=['sharpe_3y','sortino_3y','info_ratio_3y','alpha_3y' if 'alpha_3y' in D else 'excess_cagr_3y','peer_consistency','peer_rank_stability','neg_recovery_days','score']
if 'alpha_3y' not in D: D['alpha_3y']=D.cagr_3y-(RF+D.beta_3y*(D.bench_cagr_3y-RF)); cands[3]='alpha_3y'
out=[]
for m in cands:
    row={'metric':m,'coverage':round(D[m].notna().mean(),2)}
    for h in (1,3):
        col=f'fwd_{h}y'; v=[]
        for (t,pg),g in D[D[col].notna()].groupby(['as_of','pg']):
            if len(g)>=5 and g[m].notna().sum()>=5: v.append(g[m].corr(g[col],method='spearman'))
        v=pd.Series(v); row[f'IC_{h}y']=round(v.mean(),3)
    # redundancy with current score
    row['corr_with_score']=round(D[[m,'score']].corr(method='spearman').iloc[0,1],2)
    out.append(row)
print(pd.DataFrame(out).to_string(index=False))
