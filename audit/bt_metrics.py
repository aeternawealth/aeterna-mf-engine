"""Point-in-time metrics for the backtest. Every metric at date t uses only NAV/TRI data dated <= t."""
import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np
from engine import config as C, ingest
from engine.metrics import fund_metrics
from engine.rank import assign_peers, assign_theme
u=ingest.build_universe(ingest.parse_navall(open('data/raw/NAVAll.txt',encoding='utf-8').read()))
tri=ingest.load_cached_tri()
up=assign_peers(u,tri)
act=up[(up.category!='Index Fund')&(up.plan_type=='Regular')][['code','name','amc','category','peer_group','benchmark','theme']].copy()
act['status']='live'; act['src']='nav'
dm=pd.read_csv('audit/dead_meta.csv',parse_dates=['first','last'])
dm=dm[dm.category.notna()&(dm.category!='Index Fund')&(dm['last']<'2026-08-01')].copy()
dm['peer_group']=dm.category.map(lambda c: C.MERGE_PEER_GROUPS.get(c,c)); dm['benchmark']=dm.category.map(C.CATEGORY_BENCHMARK); dm['theme']=None
th=dm.category.eq('Sectoral/Thematic')
for i in dm.index[th]:
    t,b=assign_theme(dm.at[i,'name']); dm.at[i,'theme']=t; dm.at[i,'benchmark']=b if b in tri else 'NIFTY 500'; dm.at[i,'peer_group']='Thematic: '+t
dm['status']='closed'; dm['src']='nav_dead'
allf=pd.concat([act,dm[act.columns.drop(['status','src']).tolist()+['status','src']]],ignore_index=True)
allf=allf[allf.benchmark.notna()]
navs={}
for r in allf.itertuples():
    p=f'data/{r.src}/{r.code}.csv'
    try: navs[r.code]=pd.read_csv(p,parse_dates=['date']).set_index('date')['nav']
    except FileNotFoundError: pass
dates=pd.date_range('2019-06-30','2025-06-30',freq='6ME')
import os
os.makedirs('audit/bt_parts',exist_ok=True)
for t in dates:
    part=f'audit/bt_parts/{t.date()}.csv'
    if os.path.exists(part): continue
    rows=[]; n=0
    for r in allf.itertuples():
        nav=navs.get(r.code)
        if nav is None or r.benchmark not in tri: continue
        if nav.index[0] > t - pd.DateOffset(years=3) or nav.index[-1] < t - pd.Timedelta(days=10): continue   # rated & alive at t
        b=tri[r.benchmark].dropna()
        m=fund_metrics(nav,b,t)
        if not m: continue
        for h in (1,3,5):
            t1=t+pd.DateOffset(years=h)
            if t1>tri.index.max(): m[f'fwd_{h}y']=np.nan; continue
            n0=nav[:t].iloc[-1]; seg=nav[t:t1]
            if len(seg)<2: m[f'fwd_{h}y']=np.nan; m[f'fwd_{h}y_closed']=True; continue
            end=seg.index[-1]; yrs=(end-t).days/365.25
            closed=(t1-end).days>15
            bf=(b[:end].iloc[-1]/b[:t].iloc[-1])**(1/yrs)-1 if yrs>0.25 else np.nan
            ff=(seg.iloc[-1]/n0)**(1/yrs)-1 if yrs>0.25 else np.nan
            m[f'fwd_{h}y']=ff-bf; m[f'fwd_{h}y_closed']=closed
        m.update(code=r.code,name=r.name,category=r.category,peer_group=r.peer_group,status=r.status,as_of=t.date())
        rows.append(m); n+=1
    pd.DataFrame(rows).to_csv(part,index=False); print(t.date(), n, flush=True)
import glob
pd.concat([pd.read_csv(f) for f in sorted(glob.glob('audit/bt_parts/*.csv'))]).to_csv('audit/bt_metrics.csv',index=False)
