import sys, re
from playwright.sync_api import sync_playwright
url=sys.argv[1]; pat=sys.argv[2] if len(sys.argv)>2 else 'sep|xls|zip|portfolio'
with sync_playwright() as p:
    b=p.chromium.launch(args=['--disable-blink-features=AutomationControlled']); pg=b.new_page(locale='en-IN',user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
    pg.goto(url,timeout=90000,wait_until='domcontentloaded'); pg.wait_for_timeout(6000)
    L=pg.eval_on_selector_all('a,button','els=>els.map(e=>[e.tagName,e.href||"",(e.innerText||e.title||"").trim().slice(0,70)])')
    seen=set()
    for t,h,x in L:
        k=(h,x)
        if k in seen: continue
        seen.add(k)
        if re.search(pat,h+' '+x,re.I): print(t,'|',x,'|',h[:160])
    print('TITLE',pg.title(), 'N',len(L))
