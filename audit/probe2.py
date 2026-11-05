import sys, re, json
from playwright.sync_api import sync_playwright
name, url = sys.argv[1], sys.argv[2]
out = {'name': name, 'url': url, 'xhr': [], 'links': []}
with sync_playwright() as p:
    b = p.chromium.launch(args=['--disable-blink-features=AutomationControlled'])
    ctx = b.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36', locale='en-IN')
    pg = ctx.new_page()
    def onresp(r):
        try:
            ct = r.headers.get('content-type', '')
            if r.request.resource_type in ('xhr', 'fetch') or re.search(r'\.(xlsx?|zip)', r.url, re.I):
                body = ''
                if 'json' in ct:
                    body = r.text()[:600]
                out['xhr'].append([r.status, r.url[:220], ct[:40], body])
        except Exception:
            pass
    pg.on('response', onresp)
    try:
        pg.goto(url, timeout=90000, wait_until='domcontentloaded'); pg.wait_for_timeout(8000)
        L = pg.eval_on_selector_all('a', 'els=>els.map(e=>[e.href||"",(e.innerText||e.title||"").trim().slice(0,80)])')
        out['links'] = [l for l in L if re.search(r'portfolio|xls|zip|sep|monthly', l[0] + ' ' + l[1], re.I)][:40]
        out['title'] = pg.title()
        out['text'] = re.sub(r'\s+', ' ', pg.inner_text('body'))[:800]
    except Exception as e:
        out['err'] = str(e)[:200]
    b.close()
json.dump(out, open(f'audit/probe/{name}.json', 'w'), indent=1)
print(name, out.get('title'), 'xhr', len(out['xhr']), 'links', len(out['links']), out.get('err', ''))
