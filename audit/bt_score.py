import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json
from scipy import stats
from engine import config as C
from engine.protocols import score_group, assign_tiers
M=pd.read_csv('audit/bt_metrics.csv'); M['as_of']=pd.to_datetime(M.as_of)
import re, os
RF=0.065
M['capture_ratio_3y']=M.upside_capture_3y/M.downside_capture_3y
M['alpha_3y']=M.cagr_3y-(RF+M.beta_3y*(M.bench_cagr_3y-RF))
def _nm(x):
    x=re.sub(r'(?i)\b(direct|regular)\s*(plan)?\b|\bgrowth( option| plan)?\b|-|\(.*?\)','',str(x))
    return re.sub(r'[^a-z0-9&]+','',x.lower())
M['k']=M.name.map(_nm); M['ter']=np.nan
for t in M.as_of.unique():
    f=f"audit/ter_hist/{pd.Timestamp(t).strftime('%m-%Y')}.xlsx"
    if not os.path.exists(f): continue
    x=pd.read_excel(f); x.columns=[str(c).strip() for c in x.columns]
    reg=next(c for c in x.columns if c.startswith('Regular') and 'Total TER' in c)
    x['TER Date']=pd.to_datetime(x['TER Date'],errors='coerce'); x=x.dropna(subset=[reg]).sort_values('TER Date').groupby('Scheme Name').tail(1)
    mp=dict(zip(x['Scheme Name'].map(_nm),pd.to_numeric(x[reg],errors='coerce')))
    sel=M.as_of==t; M.loc[sel,'ter']=M.loc[sel,'k'].map(mp)
M.loc[M.ter>5,'ter']=np.nan
print('PIT TER coverage', round(M.ter.notna().mean(),3))
res=[]
for t,D in M.groupby('as_of'):
    D=D.copy()
    th=D.category.eq('Sectoral/Thematic')
    cnt=D[th].groupby('peer_group').size(); thin=set(cnt[cnt<C.THEME_MIN_RATED].index)
    D.loc[th&D.peer_group.isin(thin),'peer_group']='Thematic: Other Themes'
    for pg,g in D.groupby('peer_group'):
        if len(g)<3: continue
        sg=assign_tiers(score_group(g,C.protocol_for(g.category.iloc[0])[1]))
        # naive baseline: trailing 3Y CAGR percentile
        sg['naive_pct']=sg['cagr_3y'].rank(pct=True)
        sg['score_pct']=sg['score'].rank(pct=True)
        sg['n_peer']=len(g)
        res.append(sg)
R=pd.concat(res,ignore_index=True)
R['flags']=R['flags'].map(lambda f:', '.join(f))
R.to_csv('audit/bt_scored.csv',index=False)
out={}
order=['A+','A','B','C']
for h in (1,3,5):
    col=f'fwd_{h}y'; X=R[R[col].notna()]
    tier=X.groupby('tier')[col].agg(n='size',mean='mean',median='median',beat=lambda s:(s>0).mean()).reindex(order)
    naive=X[X.naive_pct>=0.9][col]
    # IC per date (avg of peer-group spearman, groups with >=5 funds)
    ics=[]
    for t,D in X.groupby('as_of'):
        v=[g.score.corr(g[col],method='spearman') for _,g in D.groupby('peer_group') if len(g)>=5 and g.score.notna().sum()>=5]
        nv=[g.cagr_3y.corr(g[col],method='spearman') for _,g in D.groupby('peer_group') if len(g)>=5]
        ics.append((t,np.nanmean(v),np.nanmean(nv)))
    ic=pd.DataFrame(ics,columns=['as_of','ic','naive_ic'])
    tt=stats.ttest_1samp(ic.ic.dropna(),0)
    # pooled: A+ vs Avoid/C difference test
    a=X[X.tier=='A+'][col]; lo=X[X.tier.isin(['C'])][col]
    mw=stats.mannwhitneyu(a,lo,alternative='greater') if len(a)>5 and len(lo)>5 else None
    out[h]=dict(dates=int(X.as_of.nunique()),obs=int(len(X)),tier=tier.round(4).reset_index().to_dict('records'),
        naive_top10=dict(n=int(len(naive)),mean=float(naive.mean()),beat=float((naive>0).mean())),
        all_funds=dict(mean=float(X[col].mean()),beat=float((X[col]>0).mean())),
        ic_mean=float(ic.ic.mean()),ic_t=float(tt.statistic),ic_p=float(tt.pvalue),naive_ic_mean=float(ic.naive_ic.mean()),
        ic_by_date=ic.round(3).astype(str).values.tolist(),
        aplus_vs_low_p=None if mw is None else float(mw.pvalue))
    print(f'==== {h}Y fwd | dates {out[h]["dates"]} obs {out[h]["obs"]}')
    print(tier.round(4).to_string()); print('naive top10%',out[h]['naive_top10'],'all',out[h]['all_funds'])
    print('IC mean %.3f t %.2f p %.3f | naive IC %.3f | A+>C/Avoid MW p %s'%(out[h]['ic_mean'],out[h]['ic_t'],out[h]['ic_p'],out[h]['naive_ic_mean'],out[h]['aplus_vs_low_p']))
# category-wise (3Y and 1Y)
for h in (1,3):
    col=f'fwd_{h}y'; X=R[R[col].notna()]
    X=X.assign(cat=X.category)
    cw=X.groupby('cat').apply(lambda g: pd.Series({'n':len(g),'aplus_n':(g.tier=='A+').sum(),'aplus_beat':(g[g.tier=='A+'][col]>0).mean(),
        'aplus_mean':g[g.tier=='A+'][col].mean(),'low_mean':g[g.tier.isin(['C','Avoid'])][col].mean(),'all_beat':(g[col]>0).mean(),
        'ic':np.nanmean([d.score.corr(d[col],method='spearman') for _,d in g.groupby(['as_of','peer_group']) if len(d)>=5])}))
    out[f'cat_{h}']=cw.round(3).reset_index().to_dict('records'); print(f'--- category {h}Y'); print(cw.round(3).to_string())
# metric ICs (3Y fwd and 1Y fwd)
mets=['ter','capture_ratio_3y','alpha_3y','roll3y_excess_median','roll3y_hit_rate','info_ratio_3y','downside_capture_3y','max_drawdown_3y','roll3y_excess_p10','roll1y_hit_rate','excess_cagr_1y','excess_cagr_3y','sortino_3y','upside_capture_3y','excess_cagr_5y','age_years']
mi={}
for h in (1,3):
    col=f'fwd_{h}y'; X=R[R[col].notna()]
    for m in mets:
        v=[(g[m].corr(g[col],method='spearman')) for _,g in X.groupby(['as_of','peer_group']) if len(g)>=5 and g[m].notna().sum()>=5]
        mi.setdefault(m,{})[f'{h}y']=round(float(np.nanmean(v)),3)
out['metric_ic']=mi; print(pd.DataFrame(mi).T)
# survivorship
out['closed']={'funds_closed_in_sample':int(R[R.status=='closed'].code.nunique()),'obs_closed':int((R.status=='closed').sum()),
 'aplus_closed':int(((R.status=='closed')&(R.tier=='A+')).sum())}
print(out['closed'])
json.dump(out,open('audit/bt_results.json','w'),default=str,indent=1)
