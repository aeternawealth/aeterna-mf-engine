import sys; sys.path.insert(0,'.')
import pandas as pd, requests, json
from concurrent.futures import ThreadPoolExecutor
from engine.ingest import normalise_category
c=pd.read_csv('audit/dead_candidates.csv')
S=requests.Session()
def get(code):
    for i in range(3):
        try:
            j=S.get(f'https://api.mfapi.in/mf/{code}',timeout=60).json(); return code,j
        except Exception: pass
    return code,None
rows=[]
import os; os.makedirs('data/nav_dead',exist_ok=True)
with ThreadPoolExecutor(8) as ex:
    for code,j in ex.map(get,c.schemeCode):
        if not j or not j.get('data'): continue
        m=j['meta']; cat=normalise_category(f"Open Ended Schemes({m.get('scheme_category','')})")
        d=pd.DataFrame(j['data']); d['date']=pd.to_datetime(d.date,format='%d-%m-%Y'); d['nav']=pd.to_numeric(d.nav,errors='coerce')
        d=d[d.nav>0].sort_values('date')
        rows.append(dict(code=code,name=m.get('scheme_name'),amc=m.get('fund_house'),raw_cat=m.get('scheme_category'),category=cat,
                         first=d.date.min(),last=d.date.max(),n=len(d)))
        if cat: d[['date','nav']].to_csv(f'data/nav_dead/{code}.csv',index=False)
r=pd.DataFrame(rows); r.to_csv('audit/dead_meta.csv',index=False)
print(len(r)); print(r.category.value_counts(dropna=False).head(20))
e=r[r.category.notna()]; print('equity dead/other', len(e)); print(e.last.dt.year.value_counts().sort_index())
