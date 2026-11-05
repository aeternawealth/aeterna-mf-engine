import sys; sys.path.insert(0,'.')
import pandas as pd, numpy as np, json
from engine import config as C
from engine.protocols import score_group
pd.set_option('display.width',250)
d=pd.read_csv('outputs/2026-10/rankings.csv')
tri=pd.read_csv('data/raw/tri.csv',index_col=0,parse_dates=True)
def navs(code): return pd.read_csv(f'data/nav/{code}.csv',parse_dates=['date']).set_index('date')['nav']
g=d[(d.peer_group=='Flexi Cap')&(d.plan_type=='Regular')&(d.gate=='ok')].copy()
sg=score_group(g,C.ACTIVE_EQUITY_PROTOCOL)
tw=sum(w for m,(p,w,h) in C.ACTIVE_EQUITY_PROTOCOL.items() if w>0 and m in g.columns)
out={}
for nm in ['Aditya Birla Sun Life Flexi Cap Fund','Old Bridge Flexi Cap Fund','The Wealth Company Flexi Cap Fund']:
    r=d[(d.name==nm)&(d.plan_type=='Regular')].iloc[0]
    rec={'name':nm,'code':int(r.code),'age':round(r.age_years,2),'tier':r.tier,'score':r.score,'peer_rank':r.peer_rank,'peer_count':r.peer_count,'flags':r.flags,'gate':r.gate}
    if nm in sg.name.values:
        s=sg[sg.name==nm].iloc[0]
        avail=sum(w for m,(p,w,h) in C.ACTIVE_EQUITY_PROTOCOL.items() if w>0 and m in g.columns and pd.notna(s.get('p_'+m)))
        rows=[]
        for m,(p,w,h) in C.ACTIVE_EQUITY_PROTOCOL.items():
            if w<=0 or m not in g.columns: continue
            pv=s.get('p_'+m); rows.append([p,m,s[m],None if pd.isna(pv) else round(pv,1),w,None if pd.isna(pv) else round(pv*w/avail,1)])
        rec['decomp']=rows; rec['avail_weight']=avail
    for h in ['6M','1Y','3Y','5Y']:
        rec[h]=dict(ret=r.get('ret_'+h),excess=r.get('excess_'+h),rank=r.get('rank_'+h),peers=r.get('peers_'+h),dcap=r.get('dcap_'+h),mdd=r.get('mdd_'+h),hit=r.get('hit_'+h))
    # cycles
    nav=navs(r.code); b=tri['NIFTY 500'].dropna()
    cyc={'COVID crash (19 Feb–23 Mar 2020)':('2020-02-19','2020-03-23'),'Recovery (Mar 2020–Oct 2021)':('2020-03-23','2021-10-18'),
         '2022 correction (Oct 2021–Jun 2022)':('2021-10-18','2022-06-17'),'2023–24 bull run (Jun 2022–Sep 2024)':('2022-06-17','2024-09-26'),
         'Sep 2024–Mar 2025 correction':('2024-09-26','2025-03-03'),'Mar 2025–Oct 2026':('2025-03-03','2026-10-30')}
    cy={}
    for k,(a,z) in cyc.items():
        a,z=pd.Timestamp(a),pd.Timestamp(z)
        if nav.index[0]>a+pd.Timedelta(days=5): cy[k]=None; continue
        fa,fz=nav[:a].iloc[-1],nav[:z].iloc[-1]; ba,bz=b[:a].iloc[-1],b[:z].iloc[-1]
        cy[k]=(round(fz/fa-1,4),round(bz/ba-1,4))
    rec['cycles']=cy
    # calendar years
    yrs={}
    for y in range(2019,2027):
        a,z=pd.Timestamp(f'{y-1}-12-31'),pd.Timestamp(f'{y}-12-31')
        if nav.index[0]>a+pd.Timedelta(days=5): continue
        fz=nav[:z].iloc[-1]; bz=b[:z].iloc[-1]
        yrs[y]=(round(fz/nav[:a].iloc[-1]-1,4),round(bz/b[:a].iloc[-1]-1,4))
    rec['years']=yrs
    out[nm]=rec
json.dump(out,open('audit/fund_decomp.json','w'),default=str,indent=1)
for k,v in out.items():
    print('=====',k, {x:v[x] for x in ['age','tier','score','peer_rank','peer_count','flags','gate']})
    if 'decomp' in v:
        print(pd.DataFrame(v['decomp'],columns=['pillar','metric','value','pctile','weight','contrib']).to_string(index=False)); print('avail',v['avail_weight'])
    print({h:v[h] for h in ['6M','1Y','3Y','5Y']}); print(v['cycles']); print(v['years'])
