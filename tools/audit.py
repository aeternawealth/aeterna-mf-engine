"""Audit after every rating run and before every publish (AGENTS.md, "Audit protocol").

    python tools/audit.py                 # data checks + rendered-page checks on site/dist
    python tools/audit.py --no-browser    # data checks only

Writes outputs/latest/audit.md and prints it. Exit code 0 always (the run log and the daily email carry the
findings); a line starting with FAIL is something a visitor would see as wrong and must be fixed before publishing.

Data checks (outputs/latest/rankings.csv, latest holdings):
  D1  a fund ranked #1 in its group, or scoring 75+, that is not rated A+: the reason must be a flag shown on its page
  D2  portfolio checks: cap-mix shortfalls that holdings missing from AMFI's list could explain (data gaps)
  D3  holdings unclassified by market cap above 5% in a cap-based category
  D4  categories with no A+ fund, and A+ counts per category
  D5  share of funds whose rating changed since the saved monthly snapshot (large swings need a reason)
  D6  rated funds with a stale NAV
Page checks (site/dist, served locally, phone 390px and desktop 1280px, dark and light):
  P1  elements still invisible after scrolling the whole page (stuck fade-ins, hidden cards)
  P2  horizontal overflow of the page body
  P3  overlapping chart labels (SVG text boxes that intersect)
  P4  'nan', 'NaN', 'undefined', 'None' or '[object' in visible text
  P5  JavaScript errors in the console
Data completeness and sanity (added 23 Nov 2026, after 20 schemes were found missing and UTI Liquid showed -89%):
  C1  a live AMFI scheme in a category we cover is missing from the site (debt index / target-maturity funds excluded)
  C2  an impossible return (a liquid fund down, an equity fund down 50% in a year): FAIL
  C3  a fund with enough history (3 years; 1 for index funds) shown as not rated
  C4  a portfolio matched to a scheme of a different category (a Midcap sheet on a Flexi Cap fund): FAIL
  C5  one scheme split in two on the site (Direct and Regular under different names)
  C6  a fund page title in capitals or with stray characters
  C7  a large active fund (Rs 3,000 cr+) with no portfolio, or one two months old
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "latest"
DIST = ROOT / "site" / "dist"
EQUITY = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value", "Contra",
          "Dividend Yield", "Sectoral/Thematic"]
lines: list[str] = []


def say(level: str, code: str, msg: str):
    lines.append(f"{level} {code} {msg}")


def data_checks():
    r = pd.read_csv(OUT / "rankings.csv", low_memory=False)
    eq = r[r.category.isin(EQUITY) & r.tier.isin(["A+", "A", "B", "C", "Watch"])]
    # D1
    top = eq[((eq.peer_rank == 1) | (eq.score >= 75)) & (eq.tier != "A+")]
    for _, f in top.iterrows():
        fl = str(f.get("flags") or "")
        why = fl if fl and fl != "nan" and fl != "[]" else ""
        if f.score < 75 and not why:
            say("INFO", "D1", f"{f['name']} ({f.plan_type}, {f.category}) is #1 with score {f.score:.1f}: A, as A+ needs 75")
        elif not why:
            say("FAIL", "D1", f"{f['name']} ({f.plan_type}, {f.category}) score {f.score:.1f}, #{int(f.peer_rank)}, rated {f.tier} with no flag to explain it")
        else:
            say("CHECK", "D1", f"{f['name']} ({f.plan_type}, {f.category}) score {f.score:.1f}, #{int(f.peer_rank)}, rated {f.tier}: {why}. Confirm the flag is real.")
    # D2, D3
    hm = sorted(p.name for p in (ROOT / "data" / "holdings").glob("20??-??") if (p / "holdings_valid.csv").exists())
    if hm:
        sys.path.insert(0, str(ROOT))
        from engine import holdings as H
        h = H.recheck_mandates(pd.read_csv(ROOT / "data" / "holdings" / hm[-1] / "holdings_valid.csv", low_memory=False))
        cat = r.drop_duplicates("pair_key").set_index("pair_key").category
        h["category"] = h.pair_key.map(cat)
        cap = h[h.category.isin(["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap"])]
        for _, x in cap.iterrows():
            u = float(x.get("unclassified_pct") or 0)
            if x.get("mandate_ok") == 0:
                say("CHECK", "D2", f"{x.pair_key.split('|')[1]}: {x.mandate_breaches} (unclassified {u:.1f}%), portfolio {hm[-1]}")
            if u > 5:
                say("INFO", "D3", f"{x.pair_key.split('|')[1]}: {u:.1f}% of holdings not in AMFI's market-cap list ({hm[-1]})")
    # D4
    reg = eq[eq.plan_type == "Regular"]
    n = reg[reg.tier == "A+"].groupby("category").size().reindex(sorted(reg.category.unique())).fillna(0).astype(int)
    say("INFO", "D4", "A+ funds (Regular): " + ", ".join(f"{c} {v}" for c, v in n.items()))
    for c, v in n.items():
        if v == 0 and c != "Sectoral/Thematic":
            say("CHECK", "D4", f"{c}: no A+ fund this month (allowed by the score rule; the category table should say so)")
    # D5
    snap = ROOT / "outputs" / "ratings_snapshot.csv"
    if snap.exists():
        s = pd.read_csv(snap)[["code", "tier"]].rename(columns={"tier": "snap"})
        m = eq.merge(s, on="code")
        ch = (m.tier != m.snap).mean() if len(m) else 0
        say("CHECK" if ch > .35 else "INFO", "D5", f"{ch:.0%} of rated equity funds differ from the saved monthly snapshot")
    # D6
    if "gate" in r.columns:
        st = r[r.gate.astype(str).str.startswith("stale") & r.tier.isin(["A+", "A", "B", "C"])]
        if len(st):
            say("FAIL", "D6", f"{len(st)} funds with a stale NAV still carry a rating")


def completeness_checks():
    fp = ROOT / "site" / "data" / "funds.json"
    if not fp.exists():
        return
    funds = json.loads(fp.read_text(encoding="utf-8"))
    sys.path.insert(0, str(ROOT))
    # C1
    try:
        from engine import ingest
        nav_t = (ROOT / "data" / "raw" / "NAVAll.txt").read_text(encoding="utf-8", errors="replace")
        mst = ROOT / "data" / "raw" / "SchemeData.csv"
        nav = ingest.fill_plan_option(ingest.parse_navall(nav_t), mst.read_text(encoding="utf-8") if mst.exists() else "")
        end = nav["nav_date"].max()
        g = nav[nav["category"].notna() & nav["option"].str.contains("growth", case=False)
                & ~nav["option"].str.contains("idcw|dividend|bonus", case=False) & (nav["nav_date"] >= end - pd.Timedelta(days=10))]
        g = g[~g["name"].str.contains(r"\bETF\b|fund of fund|FOF|segregat|bonus|unclaimed|institutional|retail|plan [a-c]\b|\bBeES\b", case=False, regex=True)]
        g = g[~g["name"].str.contains(r"SDL|IBX|gilt|g-sec|gsec|PSU|bond|CPSE|AAA|T-?Bill|debt|crisil|treasury|maturity|target|\b20[2-4][0-9]\b", case=False, regex=True)
              | ~g["category"].eq("Index Fund")]
        g = g[g["category"] != "Debt Sectoral"]
        key = lambda a, n: (str(a).lower(), re.sub(r"[^a-z0-9]+", " ", re.sub(r"(?i)\b(direct|regular)\s*plan\b|\bgrowth( option| plan)?\b|\bcash option\b", "", str(n)).lower()).strip())
        have = {(key(f.get("amc"), f["name"]), f["plan_type"]) for f in funds} | {int(f["code"]) for f in funds}
        miss = sorted({f"{r.name} ({'Direct' if 'direct' in str(r.plan).lower() else 'Regular'}, {r.category})" for r in g.itertuples()
                       if r.code not in have and (key(r.amc, r.name), "Direct" if "direct" in str(r.plan).lower() else "Regular") not in have})
        if miss:
            say("CHECK", "C1", f"{len(miss)} live AMFI plans in categories we cover are not on the site, e.g. {'; '.join(miss[:6])}")
        else:
            say("INFO", "C1", f"every live AMFI plan in the categories we cover is on the site ({len(funds)} plans)")
    except Exception as e:
        say("CHECK", "C1", f"completeness check could not run: {type(e).__name__}: {str(e)[:120]}")
    # C2
    cash = {"Liquid", "Overnight", "Money Market", "Arbitrage", "Ultra Short Term"}
    odd = []
    for f in funds:
        for k, lo, hi in (("ret_6M", -.45, 1.2), ("ret_1Y", -.5, 1.5), ("ret_3Y", -.35, .9), ("ret_5Y", -.3, .8)):
            v = f.get(k)
            if isinstance(v, (int, float)) and (v < lo or v > hi or (f.get("category") in cash and k != "ret_6M" and not 0 <= v <= .15)):
                odd.append(f"{f['name']} ({f['plan_type']}) {k[4:]} {v * 100:.1f}%")
    for o in odd[:8]:
        say("FAIL", "C2", f"impossible-looking return: {o}")
    # C3
    unr = [f for f in funds if f.get("tier") in (None, "Unrated") and (f.get("gate") in (None, "", "ok"))
           and (f.get("age_years") or 0) >= (1 if f.get("category") == "Index Fund" else 3)]
    if unr:
        say("CHECK", "C3", f"{len(unr)} plans with enough history shown as not rated, e.g. " + "; ".join(f"{f['name']} ({f['plan_type']})" for f in unr[:6]))
    # C4
    hm = sorted(p.name for p in (ROOT / "data" / "holdings").glob("20??-??") if (p / "_mapping_report.csv").exists())
    if hm:
        from engine import holdings as H
        mr = pd.read_csv(ROOT / "data" / "holdings" / hm[-1] / "_mapping_report.csv").dropna(subset=["pair_key"])
        win = mr.sort_values("score", ascending=False).drop_duplicates("pair_key")
        for x in win.itertuples():
            a, b = H._cat_words(str(x.title)), H._cat_words(x.pair_key.split("|", 1)[1])
            if a and b and a != b and x.score < 1:
                say("FAIL", "C4", f"portfolio '{x.title}' ({x.file}) is shown on {x.pair_key.split('|')[1]}: different category")
    # C5
    plans = {}
    for f in funds:
        plans.setdefault((f.get("amc"), f.get("pair_key")), set()).add(f["plan_type"])
    one = [k for k, v in plans.items() if len(v) == 1]
    norm = lambda k: re.sub(r"\b(cash|option|plan)\b|[^a-z0-9]+", "", str(k[1]).split("|")[-1])
    seen = {}
    for k in one:
        seen.setdefault((k[0], norm(k)), []).append(k[1])
    for (a, _), v in seen.items():
        if len(v) > 1:
            say("CHECK", "C5", f"one scheme shown as two funds: {' / '.join(x.split('|')[-1] for x in v)}")
    # C6
    bad = set()
    for p in (DIST / "mutual-funds").glob("*/*/index.html") if DIST.exists() else []:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", p.read_text(encoding="utf-8", errors="replace"), re.S)
        t = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
        if t and (re.search(r"\b[A-Z]{3,}\s+[A-Z]{3,}\s+[A-Z]{3,}", t) and not re.search(r"[a-z]", t.split("(")[0])
                  or re.search(r"\s{2,}|[-.]\s*\(|[-.]$", t)):
            bad.add(t)
    if bad:
        say("CHECK", "C6", f"{len(bad)} fund page titles in capitals or with stray characters, e.g. {' | '.join(sorted(bad)[:4])}")
    # C7
    hold = {}
    hp = ROOT / "site" / "data" / "holdings.json"
    if hp.exists():
        hold = json.loads(hp.read_text(encoding="utf-8"))
    lead = max((f.get("holdings_month") or "") for f in funds)
    big = [f for f in funds if f.get("plan_type") == "Regular" and f.get("asset_class") == "Equity" and f.get("category") != "Index Fund"
           and (f.get("aum_cr") or 0) >= 3000]
    none_ = [f["name"] for f in big if f.get("pair_key") not in hold]
    old = [f["name"] for f in big if f.get("pair_key") in hold and f.get("holdings_month") and lead
           and (pd.Period(lead, "M") - pd.Period(f["holdings_month"], "M")).n >= 2]
    if none_:
        say("CHECK", "C7", f"{len(none_)} large active funds have no portfolio, e.g. {'; '.join(none_[:6])}")
    if old:
        say("CHECK", "C7", f"{len(old)} large active funds show a portfolio two or more months old, e.g. {'; '.join(old[:4])}")


PAGE_JS = r"""async () => {
  for (let y = 0; y < document.body.scrollHeight; y += 300) { scrollTo(0, y); await new Promise(r => setTimeout(r, 60)); }
  scrollTo(0, 0); await new Promise(r => setTimeout(r, 1200));
  const out = {hidden: [], overflow: document.documentElement.scrollWidth > innerWidth + 1, overlap: [], text: []};
  for (const e of document.querySelectorAll('main *')) {
    const cs = getComputedStyle(e), b = e.getBoundingClientRect();
    if (cs.opacity === '0' && b.height > 30 && cs.visibility !== 'hidden' && !e.closest('[hidden]')) out.hidden.push((e.className || e.tagName) + '');
  }
  for (const svg of document.querySelectorAll('main svg')) {
    const t = [...svg.querySelectorAll('text')].filter(x => x.textContent.trim()).map(x => [x.getBoundingClientRect(), x.textContent.trim()]);
    for (let i = 0; i < t.length; i++) for (let j = i + 1; j < t.length; j++) {
      const a = t[i][0], c = t[j][0];
      if (a.width && c.width && a.left < c.right - 1 && c.left < a.right - 1 && a.top < c.bottom - 1 && c.top < a.bottom - 1) out.overlap.push(t[i][1] + ' / ' + t[j][1]);
    }
  }
  // P6 ragged right: a block that stops well short of the column its siblings use (left-aligned, not in a grid/flex row)
  out.short = [];
  for (const e of document.querySelectorAll('main p, main .card, main .note, main .lede, main .tablewrap, main figure, main .ss')) {
    const par = e.parentElement; if (!par || e.closest('header,footer,nav,[hidden],.hero-top,.prose,details,.ddmenu')) continue;
    const ps = getComputedStyle(par); if (/(flex|grid)/.test(ps.display)) continue;
    const cs = getComputedStyle(e); if (cs.display === 'inline' || cs.position === 'absolute' || cs.textAlign === 'center' || cs.marginLeft !== '0px' && cs.marginLeft === cs.marginRight) continue;
    const col = par.clientWidth - parseFloat(ps.paddingLeft) - parseFloat(ps.paddingRight), b = e.getBoundingClientRect();
    if (col < 600 || b.width < 40 || (e.tagName === 'P' && (e.innerText || '').length < 120)) continue;
    if (b.width < col * 0.85) out.short.push((e.className || e.tagName) + ' ' + Math.round(b.width) + '/' + Math.round(col) + 'px: ' + (e.innerText || '').trim().slice(0, 50).replace(/\s+/g, ' '));
  }
  const txt = document.querySelector('main') ? document.querySelector('main').innerText : '';
  for (const w of [/\bnan\b/i, /\bundefined\b/, /\[object/, /\bNone\b/]) { const m = txt.match(w); if (m) out.text.push(txt.slice(Math.max(0, m.index - 40), m.index + 30).replace(/\s+/g, ' ')); }
  return out;
}"""


def pick_pages():
    pages = ["/", "/mutual-funds/", "/calculators/", "/ratings-update/", "/invest/", "/portfolio-check/", "/mutual-funds/dynamic-term/canara-robeco-dynamic-term-fund-direct/",
             "/mutual-funds/mid-cap/", "/mutual-funds/small-cap/top-rated/", "/compare/hdfc-flexi-cap-fund-vs-parag-parikh-flexi-cap-fund/", "/mutual-funds/liquid/", "/mutual-funds/amc/", "/insights/", "/invest/mutual-funds/", "/invest/pms/", "/calculators/sip/",
             "/#method", "/#about", "/#ratings", "/#compare", "/#contact"]
    f = json.loads((ROOT / "site" / "data" / "funds.json").read_text()) if (ROOT / "site" / "data" / "funds.json").exists() else []
    urls = json.loads((DIST / "data" / "fund-urls.json").read_text()) if (DIST / "data" / "fund-urls.json").exists() else {}
    flagged = [x for x in f if x.get("flags") and str(x["code"]) in urls][:3]
    tops = [x for x in f if x.get("tier") == "A+" and str(x["code"]) in urls][:3]
    lows = [x for x in f if x.get("tier") == "C" and str(x["code"]) in urls][:2]
    for x in flagged + tops + lows:
        pages.append(urls[str(x["code"])])
    cats = sorted({u.split("/")[2] for u in urls.values() if u.count("/") >= 3})[:2]
    pages += [f"/mutual-funds/{c}/" for c in cats]
    return list(dict.fromkeys(pages))


def page_checks():
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        say("INFO", "P0", "Playwright not installed: page checks skipped")
        return
    srv = subprocess.Popen([sys.executable, "-m", "http.server", "8791"], cwd=DIST, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    try:
        with sync_playwright() as p:
            exe = Path("/opt/pw-browsers/chromium")
            try:
                b = p.chromium.launch()
            except Exception:
                b = p.chromium.launch(executable_path=str(exe.resolve()), args=["--headless", "--no-sandbox"])   # a pre-installed browser
            for path in pick_pages():
                for w, theme in ((390, "dark"), (1280, "light")):
                    pg = b.new_page(viewport={"width": w, "height": 900})
                    errs = []
                    pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
                    pg.add_init_script(f"try{{localStorage.setItem('aw-theme','{theme}')}}catch(e){{}}")
                    try:
                        pg.goto(f"http://localhost:8791{path}", wait_until="networkidle", timeout=30000)
                        res = pg.evaluate(PAGE_JS)
                    except Exception as e:
                        say("FAIL", "P0", f"{path} ({w}px) did not load: {str(e)[:100]}")
                        pg.close(); continue
                    tag = f"{path} ({w}px {theme})"
                    if res["hidden"]:
                        say("FAIL", "P1", f"{tag}: invisible after scrolling: {', '.join(sorted(set(res['hidden']))[:4])}")
                    if res["overflow"]:
                        say("FAIL", "P2", f"{tag}: page scrolls sideways")
                    if res["overlap"]:
                        say("FAIL", "P3", f"{tag}: overlapping chart labels: {'; '.join(res['overlap'][:3])}")
                    if res.get("short") and w >= 1000:
                        say("FAIL", "P6", f"{tag}: blocks that stop short of the column: {' | '.join(res['short'][:4])}")
                    if res["text"]:
                        say("FAIL", "P4", f"{tag}: suspicious text: {' | '.join(res['text'][:2])}")
                    if errs:
                        say("FAIL", "P5", f"{tag}: script error: {errs[0]}")
                    pg.close()
            b.close()
    finally:
        srv.terminate()


def history_checks():
    """H1 reasons with leftover placeholders; H2 the same band phrase for most funds (a scale or wording bug)"""
    p = OUT / "rating_history.json"
    if not p.exists():
        return
    h = json.loads(p.read_text())
    reasons = [r[5] for v in h.values() for r in v if len(r) > 5 and r[5]]
    bad = [x for x in reasons if re.search(r"\bnan\b|\bNone\b|undefined", x)]
    if bad:
        say("FAIL", "H1", f"{len(bad)} rating-change reasons contain placeholder text, e.g. '{bad[0][:90]}'")
    if reasons:
        top = sum("top 10% of the group" in x for x in reasons) / len(reasons)
        if top > .5:
            say("FAIL", "H2", f"{top:.0%} of reasons say 'top 10% of the group': the percentile scale is probably wrong")


def main():
    data_checks()
    completeness_checks()
    history_checks()
    if "--no-browser" not in sys.argv and DIST.exists():
        page_checks()
    fails = sum(l.startswith("FAIL") for l in lines)
    head = f"# Audit {time.strftime('%Y-%m-%d %H:%M')} UTC: {fails} to fix, {sum(l.startswith('CHECK') for l in lines)} to confirm\n"
    text = head + "\n".join(sorted(lines, key=lambda l: (not l.startswith("FAIL"), not l.startswith("CHECK"), l))) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "audit.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
