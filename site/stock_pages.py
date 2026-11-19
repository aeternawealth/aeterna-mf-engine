"""'Mutual funds holding <stock>' pages: /mutual-funds/holding/<stock>/ (Nov 2026, a test with the top 100 stocks).

Built from the monthly portfolios the engine already parses (site/data/holdings.json, one list per scheme) and, for
what changed, the previous month's parsed weights (data/holdings/<YYYY-MM>/_weights.csv). Pages change only when the
portfolios do (the 11th and 16th), so the daily data commit stays the same size. Standard library only (the site build
runs without numpy/pandas).
"""
import json
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

TOP_N = 500          # Nov 2026: the 100-stock test brought search clicks ("swiggy mutual fund holding"), so widened
MIN_FUNDS = 15       # and held by at least this many schemes (fewer makes a thin page)
FILTER_JS = "<script>(()=>{const q=document.getElementById('stkq'),n=document.getElementById('stkn'),rs=[...document.querySelectorAll('#stkt tbody tr')];\nq.addEventListener('input',()=>{const t=q.value.toLowerCase().trim();let k=0;rs.forEach(r=>{const m=!t||r.cells[0].textContent.toLowerCase().includes(t);r.hidden=!m;k+=m});\nn.hidden=!t;n.textContent=k?k+' of '+rs.length+' stocks':'Not in the '+rs.length+' most widely held stocks. Smaller holdings show on each fund page.'})})()</script>"
TABLE_ROWS = 40      # holders listed in full on a page, by value; the rest are counted
BASE = "/mutual-funds/holding/"

ACRONYMS = {"HDFC", "ICICI", "SBI", "ITC", "LIC", "NTPC", "ONGC", "TCS", "HCL", "UPL", "BSE", "MCX", "IRCTC", "BHEL", "GAIL",
            "IOC", "BPCL", "HPCL", "PB", "SRF", "ABB", "DLF", "PNB", "IDFC", "AU", "REC", "PFC", "NHPC", "SJVN", "NMDC", "LTIMindtree",
            "KPIT", "CG", "IIFL", "CRISIL", "ICRA", "MRF", "TVS", "JSW", "UTI", "HDB", "NBCC", "RITES", "IRFC", "RVNL", "KEI",
            "APL", "PI", "GMR", "AIA", "SKF", "3M", "PVR", "INOX", "LT", "L&T", "M&M", "ACC", "BEL", "HAL", "BEML", "IDBI", "IEX", "CDSL"}


STK_CSS = ("<style>table.stk{width:100%;table-layout:fixed}table.stk th,table.stk td{white-space:normal}table.stk th:first-child{width:44%}"
           "@media (max-width:600px){table.stk th,table.stk td{padding:8px 4px;font-size:12.5px}table.stk th{letter-spacing:0}}</style>")


def clean_name(n):
    """'HDFC BANK LIMITED' / 'Hdfc Bank Ltd.' -> 'HDFC Bank'"""
    n = re.sub(r"\s+", " ", str(n)).strip().rstrip(".")
    n = re.sub(r"(?i)[\s,]+(limited|ltd\.?)$", "", n).strip()
    n = re.sub(r"(?i)\s*\((?:formerly|erstwhile)[^)]*\)?$", "", n).strip()
    if n.isupper():                       # shouting names from some fund houses' files
        n = " ".join(w.capitalize() if i == 0 or w.lower() not in ("of", "and", "the", "for", "in") else w.lower() for i, w in enumerate(n.split()))
    for a in ACRONYMS:                    # then put the known acronyms back
        n = re.sub(r"(?<![A-Za-z])" + re.escape(a) + r"(?![A-Za-z])", a, n, flags=re.I)
    return n


def _chg(x, added):
    if x in added:
        return "new"
    return "–" if x.get("chg") is None else f"{x['chg']:+.2f}"


def _prev_month(m):
    y, mo = int(m[:4]), int(m[5:7])
    return f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"


def _load_weights(root, month):
    """{pair_key: {isin: weight}} from that month's parsed portfolios, or None"""
    p = Path(root) / "data" / "holdings" / month / "_weights.csv"
    if not p.exists():
        return None
    out = defaultdict(dict)
    with p.open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out[r["pair_key"]][r["isin"]] = out[r["pair_key"]].get(r["isin"], 0) + float(r["weight"])
            except (KeyError, ValueError):
                continue
    return out


def build(B, funds, hold, urls, as_of):
    root = B.S.parent
    by_pair = defaultdict(list)
    for f in funds:
        if f.get("pair_key"):
            by_pair[f["pair_key"]].append(f)
    scheme = {}     # pair_key -> the plan we link to (Regular first: the plan Aeterna distributes)
    for pk, L in by_pair.items():
        L = sorted(L, key=lambda x: (x.get("plan_type") != "Regular", x["code"]))
        scheme[pk] = L[0]
    names, holders = defaultdict(Counter), defaultdict(list)
    for pk, rows in hold.items():
        f = scheme.get(pk)
        if not f:
            continue
        for row in rows:
            if len(row) < 3 or not row[0] or not isinstance(row[2], (int, float)) or row[2] <= 0:
                continue
            isin, nm, w = row[0], row[1], float(row[2])
            if not str(isin).startswith("INE"):      # Indian equity only (foreign stocks and other ISINs left out)
                continue
            names[isin][nm] += 1
            aum = f.get("aum_cr")
            holders[isin].append({"f": f, "pk": pk, "w": w, "cr": (aum * w / 100) if isinstance(aum, (int, float)) else None})
    ranked = sorted((i for i, h in holders.items() if len(h) >= MIN_FUNDS),
                    key=lambda i: -sum(x["cr"] or 0 for x in holders[i]))[:TOP_N]
    # what changed: each holder's current portfolio month against the month before it
    months = Counter(scheme[pk].get("holdings_month") for pk in hold if pk in scheme)
    cache = {}

    def prev_weights(m):
        if m and m not in cache:
            cache[m] = _load_weights(root, _prev_month(m))
        return cache.get(m)

    lead_month = max((m for m in months if m), default=None)
    older = sum(n for m, n in months.items() if m and m < lead_month) if lead_month else 0
    when = (f"{B.mon(lead_month)}, or {B.mon(_prev_month(lead_month))} where a fund house's {B.mon(lead_month)} portfolio is not yet in"
            if older else B.mon(lead_month)) if lead_month else "latest month"
    made, slugs = [], set()
    for isin in ranked:
        nm = clean_name(names[isin].most_common(1)[0][0])
        s = B.slug(nm)
        if not s or s in slugs:
            s = f"{s}-{isin[-6:].lower()}"
        slugs.add(s)
        H = sorted(holders[isin], key=lambda x: -(x["cr"] or 0))
        total = sum(x["cr"] or 0 for x in H)
        added, exited, comparable = [], [], 0
        for x in H:
            pw = prev_weights(x["f"].get("holdings_month"))
            if pw is None or x["pk"] not in pw:
                x["chg"] = None
                continue
            comparable += 1
            old = pw[x["pk"]].get(isin)
            x["chg"] = None if old is None else x["w"] - old
            if old is None:
                added.append(x)
        for pk, f in scheme.items():     # funds that held it last month and no longer do
            m = f.get("holdings_month")
            pw = prev_weights(m)
            if pw and pk in pw and isin in pw[pk] and pk in hold and not any(r[0] == isin for r in hold[pk]):
                exited.append(f)
        cats = Counter(x["f"]["category"] for x in H)
        rated = [x for x in H if x["f"].get("tier") in ("A+", "A") and x["f"]["category"] not in ("Index Fund", "Arbitrage")]   # active funds only
        made.append((nm, s, isin, len(H), total, len(added), len(exited)))
        rows = "".join(
            f"<tr><td class='l'><a href='{x['f']['_url']}'>{B.e(x['f']['_name'])}</a><small class='muted' style='display:block;font-size:12px'>{B.e(x['f']['category'])}</small></td>"
            f"<td>{B.tier_badge(x['f'].get('tier'))}</td><td class='num'>{x['w']:.2f}%</td>"
            f"<td class='num'>{B.cr(x['cr']) if x['cr'] else '–'}</td>"
            f"<td class='num'>{_chg(x, added)}</td></tr>"
            for x in H[:TABLE_ROWS])
        more = f"<p class='muted' style='font-size:13px;margin-top:8px'>And {len(H) - TABLE_ROWS} more schemes with smaller holdings.</p>" if len(H) > TABLE_ROWS else ""
        top3 = ", ".join(f"{x['f']['_name']} ({x['w']:.1f}% of the fund)" for x in H[:3])
        lede = (f"{len(H)} mutual fund schemes held {B.e(nm)} shares in their latest portfolios ({B.e(when)}), "
                f"worth about {B.cr(total)} in all. The largest holders by value are {B.e(top3)}.")
        chg_txt = ""
        if comparable:
            chg_txt = (f"<p style='margin-top:10px'>Against the month before, {len(added)} scheme{'s' if len(added) != 1 else ''} added {B.e(nm)} as a new holding"
                       f" and {len(exited)} sold out of it completely.</p>")
            if added:
                chg_txt += "<p style='margin-top:6px;font-size:14.5px'><b>New holders:</b> " + ", ".join(f"<a href='{x['f']['_url']}'>{B.e(x['f']['_name'])}</a>" for x in added[:12]) + (" and others" if len(added) > 12 else "") + "</p>"
            if exited:
                chg_txt += "<p style='margin-top:6px;font-size:14.5px'><b>Sold out:</b> " + ", ".join(f"<a href='{f['_url']}'>{B.e(f['_name'])}</a>" for f in exited[:12]) + (" and others" if len(exited) > 12 else "") + "</p>"
        cat_txt = ", ".join(f"{c} ({n})" for c, n in cats.most_common(6))
        rated_txt = (f"<p style='margin-top:10px'>{len(rated)} actively managed schemes holding it are rated A+ or A on their track record, among them "
                     + ", ".join(f"<a href='{x['f']['_url']}'>{B.e(x['f']['_name'])}</a>" for x in rated[:5]) + ".</p>") if rated else ""
        faq = [(f"How many mutual funds hold {nm} shares?",
                f"{len(H)} schemes held {nm} in their latest monthly portfolios ({when}), worth about {B.cr(total)} in all."),
               (f"Which mutual fund holds the most {nm} shares?",
                f"By value, {H[0]['f']['_name']}: about {B.cr(H[0]['cr'])}, {H[0]['w']:.2f}% of the fund." if H[0]["cr"] else f"{H[0]['f']['_name']}, at {H[0]['w']:.2f}% of the fund."),
               ("Where does this data come from?",
                "From the monthly portfolios that every fund house must publish by the 10th of the following month. Values are approximate: the fund's assets under management multiplied by the stock's weight in the portfolio.")]
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">{STK_CSS}
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="{BASE}">Holdings by stock</a> › {B.e(nm)}</nav>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:14px">Mutual funds holding {B.e(nm)} shares</h1>
<p class="lede" style="margin-top:12px">{lede}</p>
{chg_txt}
<p style="margin-top:10px">By category: {B.e(cat_txt)}.</p>
{rated_txt}
<h2 style="font-size:24px;margin-top:30px">Every scheme holding {B.e(nm)}, by value</h2>
<div class="tablewrap" style="margin-top:12px"><table class="cmp stk"><thead><tr><th class="l">Scheme</th><th>Rating</th><th>% of fund</th><th>Value</th><th>Change</th></tr></thead><tbody>{rows}</tbody></table></div>{more}
<p class="muted" style="font-size:12.5px;margin-top:8px">Value: the scheme's assets under management × the stock's weight, approximate. Change: the weight against the previous month's portfolio, in percentage points; it moves with the share price as well as with buying and selling. Links go to each scheme's Regular plan.</p>
<h2 style="font-size:24px;margin-top:32px">Common questions</h2>{''.join(f'<details class="faq"><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>' for q, a in faq)}
<p class="note" style="margin-top:24px">This page lists which funds hold a stock. It is not a view on the stock or a recommendation to buy or sell it or any fund. Ratings describe past track records, not a forecast.</p>
</div></section>"""
        path = f"{BASE}{s}/"
        B.write(path, B.page(f"Mutual funds holding {nm} shares: {len(H)} schemes, {B.mon(lead_month) if lead_month else ''}".strip(" ,"),
                             f"{len(H)} mutual fund schemes hold {nm}, worth about {B.cr(total)}. See which funds hold the most, their ratings, and which added or sold the stock last month.",
                             path, body, (faq_ld, B.crumbs([("Mutual funds", "/mutual-funds/"), ("Holdings by stock", BASE), (nm, path)]))))
        urls.append((path, "monthly", "0.6"))
    # the index of stocks
    rows = "".join(f"<tr><td class='l'><a href='{BASE}{s}/'>{B.e(nm)}</a></td><td class='num'>{n}</td><td class='num'>{B.cr(t)}</td><td class='num'>{a}</td><td class='num'>{x}</td></tr>"
                   for nm, s, _, n, t, a, x in made)
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">{STK_CSS}
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › Holdings by stock</nav>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:14px">Which mutual funds hold a stock</h1>
<p class="lede" style="margin-top:12px">The {len(made)} stocks Indian mutual funds hold the most money in, from their latest monthly portfolios ({B.mon(lead_month) if lead_month else ''}). Open a stock to see every scheme that holds it, how much, and who bought or sold it last month.</p>
<input id="stkq" type="search" autocomplete="off" placeholder="Find a stock, e.g. Reliance" aria-label="Find a stock" style="width:100%;max-width:420px;margin-top:18px;padding:12px 14px;font:inherit;border:1px solid var(--rule);border-radius:8px;background:var(--surface);color:var(--ink)">
<p id="stkn" class="muted" style="font-size:13px;margin-top:8px" hidden></p>
<div class="tablewrap" style="margin-top:12px"><table class="cmp stk" id="stkt"><thead><tr><th class="l">Stock</th><th>Schemes</th><th>Held by funds</th><th>New holders</th><th>Sold out</th></tr></thead><tbody>{rows}</tbody></table></div>
{FILTER_JS}
<p class="note" style="margin-top:24px">Not a view on any stock or a recommendation to buy or sell. Values are approximate.</p>
</div></section>"""
    B.write(BASE, B.page(f"Which mutual funds hold a stock: top {len(made)} stocks, {B.mon(lead_month) if lead_month else ''}".strip(" ,"),
                         f"See which mutual fund schemes hold India's {len(made)} most widely held stocks, how much each holds, and which funds bought or sold them last month.",
                         BASE, body, (B.crumbs([("Mutual funds", "/mutual-funds/"), ("Holdings by stock", BASE)]),)))
    urls.append((BASE, "monthly", "0.6"))
    (B.DIST / "data").mkdir(parents=True, exist_ok=True)
    (B.DIST / "data" / "stocks.json").write_text(json.dumps([[nm, f"{BASE}{s}/", n] for nm, s, _, n, *_ in made], ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return {isin: f"{BASE}{s}/" for _, s, isin, *_ in made}
