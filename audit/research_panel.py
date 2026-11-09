"""Research panel (run in CI, where NSE's index site is reachable): real total-return indices from 2008, NAVs of every
active equity fund (Regular) and of funds that later closed, then point-in-time metrics every quarter from 2012 to 2025
with the fund's actual next 1/3/5-year return over its benchmark. Output: audit/bt_metrics_long.csv."""
import sys, os; sys.path.insert(0, '.')
import pandas as pd
from engine import config as C, ingest
C.HISTORY_START = "01-Jan-2008"
tri = ingest.fetch_all_tri(print)
print('TRI', tri.shape, tri.index.min(), tri.index.max(), flush=True)
chk = tri[[c for c in ("NIFTY 50", "NIFTY SMALLCAP 250") if c in tri]].pct_change().corr().iloc[0, -1]
assert chk < 0.98, f"index series look identical (corr {chk:.3f}): not real data"
u0 = ingest.build_universe(ingest.parse_navall(ingest.fetch_navall()))
codes = u0[(u0.asset_class == 'Equity') & (u0.category != 'Index Fund') & (u0.plan_type == 'Regular')].code.tolist()
ingest.fetch_navs(codes, log=lambda *a: None)
os.system('python audit/fetch_dead.py')
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
import numpy as np
STYLE = {"mom": "NIFTY200 MOMENTUM 30", "val": "NIFTY200 VALUE 30", "lowvol": "NIFTY100 LOW VOLATILITY 30",
         "qual": "NIFTY100 QUALITY 30", "small": "NIFTY SMALLCAP 250", "mid": "NIFTY MIDCAP 150", "n50": "NIFTY 50"}
STYLE = {k: v for k, v in STYLE.items() if v in tri}
print("style indices available:", STYLE, flush=True)
def _ret(s, t, months):
    s = s[:t]
    if len(s) < 2: return np.nan
    a = s[:t - pd.DateOffset(months=months)]
    return s.iloc[-1] / a.iloc[-1] - 1 if len(a) else np.nan
def extra(nav, b, t):
    """Momentum over 1/3/6/12 months (fund minus benchmark), market condition, and style exposure from weekly returns
    over 3 years: each style index's return over the benchmark regressed on the fund's return over the benchmark."""
    e = {}
    for mo in (1, 3, 6, 12):
        e[f"mom_{mo}m"] = _ret(nav, t, mo) - _ret(b, t, mo)
    e["mkt_12m"] = _ret(b, t, 12)                      # market condition on the date
    bb = b[:t]; e["mkt_above_200d"] = float(bb.iloc[-1] > bb.iloc[-200:].mean()) if len(bb) > 200 else np.nan
    w = lambda x: x[t - pd.DateOffset(years=3):t].resample("W-FRI").last().pct_change()
    fw, bw = w(nav), w(b)
    for k, name in STYLE.items():
        sw = w(tri[name].dropna())
        j = pd.concat([fw - bw, sw - bw], axis=1, keys=["f", "s"]).dropna()
        e[f"style_{k}"] = float(j.f.cov(j.s) / j.s.var()) if len(j) > 100 and j.s.var() > 0 else np.nan
    return e
dates=pd.date_range('2012-03-31','2026-09-30',freq='ME')   # every month-end; forward returns left blank where the future is unknown
import os
os.makedirs('audit/bt_parts_long',exist_ok=True)
for t in dates:
    part=f'audit/bt_parts_long/{t.date()}.csv'
    if os.path.exists(part): continue
    rows=[]; n=0
    for r in allf.itertuples():
        nav=navs.get(r.code)
        if nav is None or r.benchmark not in tri: continue
        if nav.index[0] > t - pd.DateOffset(years=3) or nav.index[-1] < t - pd.Timedelta(days=10): continue   # rated & alive at t
        b=tri[r.benchmark].dropna()
        m=fund_metrics(nav,b,t)
        if not m: continue
        m.update(extra(nav,b,t))
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
        for mo in (1,3,6):   # plain (not annualised) return over the benchmark, for monthly re-rating tests
            t1=t+pd.DateOffset(months=mo)
            if t1>tri.index.max(): m[f'fwd_{mo}m']=np.nan; continue
            seg=nav[t:t1]
            if len(seg)<2: m[f'fwd_{mo}m']=np.nan; continue
            end=seg.index[-1]; m[f'fwd_{mo}m']=(seg.iloc[-1]/nav[:t].iloc[-1]-1)-(b[:end].iloc[-1]/b[:t].iloc[-1]-1)
        m.update(code=r.code,name=r.name,category=r.category,peer_group=r.peer_group,status=r.status,as_of=t.date())
        rows.append(m); n+=1
    pd.DataFrame(rows).to_csv(part,index=False); print(t.date(), n, flush=True)
import glob
pd.concat([pd.read_csv(f) for f in sorted(glob.glob('audit/bt_parts_long/*.csv'))]).to_csv('audit/bt_metrics_long.csv',index=False)
