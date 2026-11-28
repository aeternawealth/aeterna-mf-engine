"""Layout check across every page template, at desktop (1280px) and phone (390px) width, in a real browser.

    python tools/layout_check.py [--base http://localhost:8765]   (serves site/dist itself unless --base is given)

Flags, per page and width:
  wide-table   a table wider than its box on desktop (people have to scroll sideways to read it)
  off-screen   an element that runs past the right edge of the screen (outside scroll boxes)
  ragged-left  a heading, paragraph or card whose left edge is off the column its siblings share
  clipped      a heading, button, label or link whose text is cut off
  cramped      a table cell squeezed under 44px wide on desktop
Exit code 1 if anything is flagged.
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "site" / "dist"


def pages():
    out = ["/", "/mutual-funds/", "/mutual-funds/small-cap/", "/mutual-funds/liquid/", "/mutual-funds/arbitrage/", "/mutual-funds/index-fund/",
           "/mutual-funds/amc/", "/mutual-funds/money-flows/", "/mutual-funds/what-funds-bought-sold/", "/mutual-funds/crowded-stocks/",
           "/mutual-funds/holding/", "/compare/", "/calculators/", "/calculators/sip/", "/calculators/capital-gains-tax/", "/plan/",
           "/income-tax/", "/income-tax/calculator/", "/income-tax/slabs-fy-2026-27/", "/income-tax/deductions/", "/learn/", "/insights/",
           "/insights/category-returns-by-year/", "/insights/held-3y/", "/invest/", "/invest/mutual-funds/", "/invest/portfolio-review/", "/about/",
           "/method/", "/contact/", "/disclosures/", "/ratings-update/", "/portfolio-check/", "/pms/", "/pms/ratings/equity/",
           "/pms/ratings/debt/", "/pms/how-pms-returns-are-measured/", "/aif/", "/editorial-policy/"]
    def first(glob):
        for p in sorted(DIST.glob(glob)):
            return "/" + str(p.parent.relative_to(DIST)) + "/"
    for g in ("mutual-funds/small-cap/*/index.html", "mutual-funds/corporate-bond/*/index.html", "mutual-funds/aggressive-hybrid/*/index.html",
              "compare/*/index.html", "mutual-funds/amc/*/index.html", "mutual-funds/holding/*/index.html", "learn/*/index.html",
              "mutual-funds/small-cap/top-rated/index.html", "mutual-funds/small-cap/year-by-year/index.html", "income-tax/deductions/*/index.html"):
        u = first(g)
        if u:
            out.append(u.replace("/index.html/", "/"))
    D = json.loads((ROOT / "site/data/pms.json").read_text())
    s = next(x for x in D["strategies"] if x.get("rank") == 1 and x["group"] == "Equity")
    out.append(f"/pms/{s['mslug']}/{s['slug']}/")
    m = next(x for x in D["managers"] if len(x["ids"]) >= 3)
    out.append(f"/pms/{m['slug']}/")
    return [u for u in dict.fromkeys(out) if (DIST / u.strip("/") / "index.html").exists() or u == "/"]


JS = r"""async () => {
  for (let y = 0; y < document.body.scrollHeight; y += 400) { scrollTo(0, y); await new Promise(r => setTimeout(r, 30)); }
  scrollTo(0, 0); await new Promise(r => setTimeout(r, 900));
  document.querySelectorAll('.sr').forEach(e => e.classList.add('in'));
  const W = innerWidth, out = [], seen = new Set();
  const say = (k, e, x) => { const t = (e.innerText || e.getAttribute('aria-label') || e.tagName).trim().replace(/\s+/g, ' ').slice(0, 60); const key = k + t; if (!seen.has(key)) { seen.add(key); out.push([k, t, x]); } };
  const vis = e => { const s = getComputedStyle(e); return s.display !== 'none' && s.visibility !== 'hidden' && !e.closest('[hidden],details:not([open]) > :not(summary)') && e.getBoundingClientRect().width > 0; };
  const inScroll = e => { for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const s = getComputedStyle(p); if (/(auto|scroll|hidden)/.test(s.overflowX)) return true; } return false; };
  const main = document.querySelector('main') || document.body;
  if (W > 1000) for (const t of main.querySelectorAll('.tablewrap')) if (vis(t) && t.scrollWidth > t.clientWidth + 2) say('wide-table', t.querySelector('th') || t, `${t.scrollWidth}px in ${t.clientWidth}px`);
  for (const e of main.querySelectorAll('*')) { if (!vis(e) || inScroll(e) || e.closest('.wa-float,svg')) continue; const r = e.getBoundingClientRect(); if (r.right > W + 1 && r.width < W * 3) say('off-screen', e, `right edge ${Math.round(r.right)}px`); }
  for (const e of main.querySelectorAll('h1,h2,h3,.btn,button,summary,.pm-chip,.tier-w,th')) { if (!vis(e)) continue; const s = getComputedStyle(e); if (s.overflow !== 'visible' || s.textOverflow === 'ellipsis') { if (e.scrollWidth > e.clientWidth + 2 && !/ellipsis/.test(s.textOverflow)) say('clipped', e, `${e.scrollWidth} > ${e.clientWidth}`); } }
  for (const w of main.querySelectorAll('.wrap, .pm-sec, .mv-sec, .rs-sec, .inv-page, .prose, .inv-sec .body, .card, .pm-card, .rs-card, section > div')) {
    const ws = getComputedStyle(w); if (/(flex|grid)/.test(ws.display)) continue;
    const kids = [...w.children].filter(k => vis(k) && !/^(SCRIPT|STYLE|NAV|BR|SPAN|A|B|I|EM|SMALL|SVG)$/i.test(k.tagName) && getComputedStyle(k).position === 'static' && getComputedStyle(k).float === 'none');
    if (kids.length < 2) continue;
    const L = w.getBoundingClientRect().left + parseFloat(ws.paddingLeft) + parseFloat(ws.borderLeftWidth);
    for (const k of kids) { const s = getComputedStyle(k); if (s.textAlign === 'center' || s.marginLeft === 'auto' || /inline/.test(s.display) || k.tagName === 'LI') continue; const d = k.getBoundingClientRect().left - L; if (Math.abs(d) > 1.5 && Math.abs(d) < 60) say('ragged-left', k, `${Math.round(d)}px off the column`); }
  }
  if (W > 1000) for (const td of main.querySelectorAll('td')) { if (!vis(td) || !td.innerText.trim()) continue; const r = td.getBoundingClientRect(); if (r.width < 44 && td.innerText.trim().length > 4) say('cramped', td, `${Math.round(r.width)}px`); }
  return out;
}"""


def main():
    import subprocess
    import time
    srv = None
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    else:   # serve site/dist ourselves
        srv = subprocess.Popen([sys.executable, "-m", "http.server", "8792"], cwd=DIST, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        base = "http://localhost:8792"
    bad = 0
    with sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except Exception:   # a pre-installed browser (cloud sessions)
            b = p.chromium.launch(executable_path=str(Path("/opt/pw-browsers/chromium").resolve()), args=["--headless", "--no-sandbox"])
        for w in (1280, 390):
            pg = b.new_page(viewport={"width": w, "height": 900})
            for u in pages():
                try:
                    pg.goto(base + u, wait_until="load", timeout=60000)
                    res = pg.evaluate(JS)
                except Exception as ex:   # a page that will not load is itself a finding
                    res = [["load", str(ex)[:80], ""]]
                for k, t, x in res[:8]:
                    print(f"{w:>4} {u:<62} {k:<11} {t} ({x})")
                bad += len(res)
            pg.close()
        b.close()
    if srv:
        srv.terminate()
    print(f"\n{bad} layout findings")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
