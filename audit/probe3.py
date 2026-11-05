import sys, re
from playwright.sync_api import sync_playwright
url, pat = sys.argv[1], sys.argv[2]
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36')
    def onreq(r):
        if re.search(pat, r.url): print('REQ', r.method, r.url, '|', (r.post_data or '')[:400], '|', {k:v for k,v in r.headers.items() if k.lower() in ('content-type','x-requested-with')})
    pg.on('request', onreq)
    pg.goto(url, timeout=90000, wait_until='domcontentloaded'); pg.wait_for_timeout(7000)
    if len(sys.argv) > 3:
        L = pg.eval_on_selector_all('a', 'els=>els.map(e=>[e.href||"",(e.innerText||"").trim().slice(0,90)])')
        for h, t in L:
            if re.search(sys.argv[3], h + ' ' + t, re.I): print('LINK', t, '|', h[:200])
    b.close()
