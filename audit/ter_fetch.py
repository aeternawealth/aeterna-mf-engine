import httpx,os
h={'User-Agent':'Mozilla/5.0','Referer':'https://www.amfiindia.com/ter-of-mf-schemes'}
for m in ['06-2022','12-2022','06-2023','12-2023','06-2024','12-2024','06-2025']:
    f=f'audit/ter_hist/{m}.xlsx'
    if os.path.exists(f): continue
    r=httpx.get('https://www.amfiindia.com/api/populate-te-rdata-revised',params={'MF_ID':'All','Month':m,'strCat':'-1','strType':'-1','excel':'true'},headers=h,timeout=180)
    open(f,'wb').write(r.content); print(m,len(r.content),flush=True)
