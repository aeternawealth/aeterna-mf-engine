"""Net-flow proxy from AMFI quarterly average AUM: flow_q = AUM_q / AUM_{q-1} - (avgNAV_q / avgNAV_{q-1}).
Point-in-time: at rating date t only quarters that ENDED at least one quarter before t are used
(AMFI publishes a quarter's AAUM ~10 days after it ends)."""
import sys; sys.path.insert(0,'.')
import json, glob, re, os
import pandas as pd, numpy as np
from engine import ingest
QEND={'April - June':'06-30','July - September':'09-30','October - December':'12-31','January - March':'03-31'}
rows=[]
for f in glob.glob('audit/aum_hist/*.json'):
    j=json.load(open(f)); per=j['period']; m=re.match(r'(.*) (\d{4})$',per)
    qe=pd.Timestamp(f"{m.group(2)}-{QEND[m.group(1)]}")
    for c,a in j['rows']:
        if c: rows.append((int(c),qe,a))
A=pd.DataFrame(rows,columns=['code','qend','aum'])
na=ingest.parse_navall(open('data/raw/NAVAll.txt',encoding='utf-8').read())
base=(na.name.str.replace(r'(?i)\b(direct|regular)\s*plan\b','',regex=True).str.replace(r'(?i)\bgrowth( option| plan)?\b','',regex=True)
      .str.replace(r'[^A-Za-z0-9&]+',' ',regex=True).str.strip().str.lower())
pk=dict(zip(na.code,na.amc.str.lower().str.strip()+'|'+base))
A['pk']=A.code.map(pk).fillna(A.code.astype(str))
P=A.groupby(['pk','qend']).aum.sum().reset_index()
M=pd.read_csv('audit/bt_metrics.csv',parse_dates=['as_of'])
M['pk']=M.code.map(pk).fillna(M.code.astype(str))
src={int(os.path.basename(f)[:-4]):f for f in glob.glob('data/nav/*.csv')+glob.glob('data/nav_dead/*.csv')}
out=[]
for code,g in M.groupby('code'):
    if code not in src: continue
    nav=pd.read_csv(src[code],parse_dates=['date']).set_index('date')['nav']
    q=P[P.pk==g.pk.iloc[0]].set_index('qend').aum.sort_index()
    if len(q)<3: continue
    avgnav=nav.groupby(pd.PeriodIndex(nav.index,freq='Q-DEC')).mean()
    qp=pd.PeriodIndex(q.index,freq='Q-DEC')
    nv=avgnav.reindex(qp).values
    fl=pd.Series(q.values[1:]/q.values[:-1]-nv[1:]/nv[:-1],index=q.index[1:])
    fl=fl.clip(-1,3)
    for t in g.as_of:
        avail=fl[fl.index<=t-pd.DateOffset(months=3)]
        last4=avail[avail.index>t-pd.DateOffset(months=15)]
        out.append(dict(code=code,as_of=t,flow_4q=last4.sum() if len(last4)>=3 else np.nan,
                        flow_2q=avail.tail(2).sum() if len(avail)>=2 else np.nan,
                        aum_cr=q[q.index<=t-pd.DateOffset(months=3)].iloc[-1]/100 if (q.index<=t-pd.DateOffset(months=3)).any() else np.nan))
F=pd.DataFrame(out); F.to_csv('audit/bt_flows.csv',index=False)
print(len(F), F.flow_4q.notna().mean().round(2)); print(F.flow_4q.describe().round(3))
