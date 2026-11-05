import httpx, json, os, time
h={'User-Agent':'Mozilla/5.0','Referer':'https://www.amfiindia.com/aum-data/average-aum'}
url='https://www.amfiindia.com/api/average-aum-schemewise'
for fy in range(1,9):
    try: meta=httpx.get(url,params={'strType':'Categorywise','fyId':fy},headers=h,timeout=120).json()
    except Exception as e: print(fy,'meta err',e); continue
    fyl=meta['data']['financial_year']
    for p in meta['data']['periods']:
        f=f"audit/aum_hist/{fy}_{p['id']}.json"
        if os.path.exists(f): continue
        for k in range(3):
            try:
                r=httpx.get(url,params={'strType':'Categorywise','fyId':fy,'periodId':p['id'],'MF_ID':'0'},headers=h,timeout=240)
                d=r.json().get('data')
                if d and sum(len(c.get('schemes',[])) for c in d)>100: break
                time.sleep(5)
            except Exception: d=None; time.sleep(5)
        rows=[(s.get('AMFI_Code'),sum(x for x in (s.get('AverageAumForTheMonth') or {}).values() if isinstance(x,(int,float)))) for c in (d or []) for s in c.get('schemes',[])]
        json.dump({'fy':fyl,'period':p['period'],'rows':rows},open(f,'w'))
        print(fyl,p['period'],len(rows),flush=True)
