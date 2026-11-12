"""Monthly shortlist pages: /mutual-funds/<category>/top-rated/ for each rated equity and hybrid category.

Different from the category page (which lists every plan): only the funds rated A+ or A, a profile of each written
from its data, what changed since last month, how much the shortlisted funds overlap, and Direct vs Regular side by
side. Wording rules: "top-rated" means rated A+/A by our method; never "best", "buy" or a forecast."""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
SKIP = {"Index Fund", "Sectoral/Thematic"}
TOP = ("A+", "A")


def _weights():
    ms = sorted(p for p in (ROOT / "data" / "holdings").glob("20??-??") if (p / "_weights.csv").exists())
    if not ms:
        return {}, None
    import csv
    w = {}
    with open(ms[-1] / "_weights.csv", newline="") as fh:
        for r in csv.DictReader(fh):
            w.setdefault(r["pair_key"], {})
            w[r["pair_key"]][r["isin"]] = w[r["pair_key"]].get(r["isin"], 0) + float(r["weight"]) / 100
    return w, ms[-1].name


def _overlap(w, a, b):
    if a not in w or b not in w:
        return None
    return sum(min(v, w[b].get(k, 0)) for k, v in w[a].items())


def _med(L, k):
    v = [f[k] for f in L if f.get(k) is not None]
    return median(v) if v else None


def _prev_tier(RH, code, month):
    h = RH.get(str(code)) or []
    prev = [x for x in h if x[0] < month]
    return prev[-1][1] if prev else None


def build(B, by_cat, urls, as_of):
    """B = the build_site module (helpers, page(), write(), RH). Returns {category: path} for the pages made."""
    w, wmonth = _weights()
    month = (as_of or "")[:7]
    made = {}
    for c, L in by_cat.items():
        if c in SKIP or B.asset_class(c) not in ("Equity", "Hybrid"):
            continue
        reg = [f for f in L if f["plan_type"] == "Regular"]
        schemes = {}
        for f in L:
            schemes.setdefault(f.get("pair_key") or f["code"], {})[f["plan_type"]] = f
        top = [s for s in schemes.values() if any((s.get(p) or {}).get("tier") in TOP for p in ("Regular", "Direct"))]
        if len(top) < 2:
            continue
        tord = {"A+": 0, "A": 1, "B": 2, "C": 3}

        def key(s):
            r, d = s.get("Regular") or {}, s.get("Direct") or {}
            return (min(tord.get(r.get("tier"), 9), tord.get(d.get("tier"), 9)), -max(r.get("score") or 0, d.get("score") or 0))
        top.sort(key=key)
        lc = c if c == "ELSS" else c.lower()
        path = f"/mutual-funds/{B.slug(c)}/top-rated/"
        cat_path = f"/mutual-funds/{B.slug(c)}/"
        bench = B.iname(next((f.get("benchmark") for f in L if f.get("benchmark")), None))
        CBL = next((f.get("bench_label") for f in L if f.get("bench_label")), None)
        yard = (("the median fund in the category" if CBL.startswith("the median") else CBL) if CBL else
                (f"the {bench} total-return index" if bench else "its index"))
        n_rated = len([f for f in reg if f.get("tier") in ("A+", "A", "B", "C")])
        med = {k: _med(reg, k) for k in ("roll3y_hit_rate", "max_drawdown_3y", "ter", "excess_3Y", "downside_capture_3y")}
        mname = B.mon(month) if month else ""

        # ------------------------------------------------ profiles
        cards, items = [], []
        for i, s in enumerate(top, 1):
            r, d = s.get("Regular"), s.get("Direct")
            f = d or r
            main = r if (r and r.get("tier") in TOP) else d
            lines = []
            if main.get("ret_3Y") is not None and main.get("excess_3Y") is not None:
                lines.append(f"Returned {B.pct(main['ret_3Y'])} a year over 3 years ({main['plan_type']} plan), "
                             f"{B.spct(main['excess_3Y'])} a year against {B.e(yard)}"
                             + ("" if med["excess_3Y"] is None else
                                "; the median fund roughly matched it." if abs(med["excess_3Y"]) < 0.0005 else
                                f"; the median fund: {B.spct(med['excess_3Y'])}."))
            if main.get("roll3y_hit_rate") is not None:
                lines.append(f"Ahead of {B.e(yard)} in {B.pct(main['roll3y_hit_rate'], 0)} of rolling 3-year periods"
                             + (f" (median fund: {B.pct(med['roll3y_hit_rate'], 0)})." if med["roll3y_hit_rate"] is not None else "."))
            if main.get("downside_capture_3y") is not None:
                lines.append(f"In falling months it fell {B.num(main['downside_capture_3y'], 0)}% as much as the index"
                             + (f" (median fund: {B.num(med['downside_capture_3y'], 0)}%)." if med["downside_capture_3y"] is not None else "."))
            if main.get("max_drawdown_3y") is not None:
                lines.append(f"Its deepest fall in the last 3 years was {B.pct(abs(main['max_drawdown_3y']))}"
                             + (f" (median fund: {B.pct(abs(med['max_drawdown_3y']))})." if med["max_drawdown_3y"] is not None else "."))
            if f.get("n_stocks"):
                lines.append(f"Holds {int(f['n_stocks'])} stocks; the top 10 are {B.pct((f.get('top10_pct') or 0) / 100, 0)} of the portfolio"
                             + (f", the largest sector {B.e(f.get('top_sector'))} ({B.pct((f.get('top_sector_pct') or 0) / 100, 0)})." if f.get("top_sector") else "."))
            flags = str(f.get("flags") or "")
            caution = ""
            if (f.get("age_years") or 99) < 5:
                caution = f"A short record: {B.num(f.get('age_years'), 1)} years. Ratings on short records change more."
            if "mandate" in flags:
                caution = (caution + " " if caution else "") + "Its latest portfolio breaks the category rule; see its page."
            plans = []
            for p in ("Regular", "Direct"):
                x = s.get(p)
                if x:
                    rk = f" · #{int(x['peer_rank'])} of {int(x['peer_count'])}" if x.get("peer_rank") else ""
                    plans.append(f"<a href='{x['_url']}'>{p}</a> {B.tier_badge(x.get('tier'))}<span class='muted' style='font-size:13px'>{rk} · expense ratio {B.num(x.get('ter'), 2)}%</span>")
            prev = _prev_tier(B.RH, (r or d)["code"], month)
            moved = ""
            cur = (r or d).get("tier")
            if prev and prev != cur:
                moved = f" <span class='muted' style='font-size:13px'>({B.e(prev)} last month)</span>"
            cards.append(f"<article class='card' style='margin-top:14px'><div class='row' style='justify-content:space-between;gap:10px;flex-wrap:wrap'>"
                         f"<h3 style='font:500 21px/1.3 var(--f-display);margin:0'>{i}. <a href='{(r or d)['_url']}' style='color:inherit'>{B.e(f['_name'])}</a>{moved}</h3>"
                         f"<span class='muted' style='font-size:13.5px'>{B.e(f.get('amc', ''))} · AUM {B.cr(f.get('aum_cr'))} · {B.num(f.get('age_years'), 1)} years</span></div>"
                         f"<p style='margin-top:8px'>{' · '.join(plans)}</p><ul style='margin:10px 0 0;padding-left:20px'>" + "".join(f"<li>{x}</li>" for x in lines) + "</ul>"
                         + (f"<p class='muted' style='font-size:13.5px;margin-top:8px'>{B.e(caution)}</p>" if caution else "") + "</article>")
            items.append({"@type": "ListItem", "position": i, "url": B.SITE + (r or d)["_url"], "name": f["_name"]})

        # ------------------------------------------------ changes since last month
        ups, downs = [], []
        for s in schemes.values():
            x = s.get("Regular") or s.get("Direct")
            prev = _prev_tier(B.RH, x["code"], month)
            cur = x.get("tier")
            if not prev or prev == cur:
                continue
            was_top, is_top = prev in TOP, cur in TOP
            if is_top and not was_top:
                ups.append(f"<li><a href='{x['_url']}'>{B.e(x['_name'])}</a>: {B.e(prev)} → {B.e(cur)}</li>")
            elif was_top and not is_top:
                downs.append(f"<li><a href='{x['_url']}'>{B.e(x['_name'])}</a>: {B.e(prev)} → {B.e(cur)}</li>")
        change = ""
        if ups or downs:
            change = ("<h2 style='font-size:24px;margin-top:34px'>What changed since last month</h2><div class='grid g2' style='margin-top:12px'>"
                      + (f"<div class='card'><b>Joined the shortlist</b><ul style='margin:8px 0 0;padding-left:20px'>{''.join(ups)}</ul></div>" if ups else "")
                      + (f"<div class='card'><b>Left the shortlist</b><ul style='margin:8px 0 0;padding-left:20px'>{''.join(downs)}</ul></div>" if downs else "")
                      + "</div><p class='muted' style='font-size:13px;margin-top:8px'>Regular plans; ratings are revised on the 11th and 16th of each month, after fund houses publish their portfolios. "
                        "Each fund's page explains its own change.</p>")
        else:
            change = "<p class='muted' style='margin-top:20px'>No fund joined or left the shortlist since last month.</p>"

        # ------------------------------------------------ overlap among the shortlisted
        ov = []
        pk = [s.get("Regular", s.get("Direct")) for s in top]
        for a in range(len(pk)):
            for b in range(a + 1, len(pk)):
                o = _overlap(w, pk[a].get("pair_key"), pk[b].get("pair_key"))
                if o is not None:
                    ov.append((o, pk[a], pk[b]))
        ov.sort(key=lambda t: -t[0])
        ov_html = ""
        if ov and c not in ("Arbitrage",):
            ov_html = ("<h2 style='font-size:24px;margin-top:34px'>Holding two of them? Check the overlap</h2>"
                       f"<p class='muted' style='margin-top:6px'>The share of their portfolios two funds hold in common (portfolios of {B.mon(wmonth)}). "
                       "Above about half, two funds are close to one bet.</p><div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Funds</th><th>Overlap</th></tr></thead><tbody>"
                       + "".join(f"<tr><td class='fund l'>{B.e(a['_name'])} + {B.e(b['_name'])}</td><td class='num'>{B.pct(o, 0)}</td></tr>" for o, a, b in ov[:6])
                       + "</tbody></table></div><p style='margin-top:10px'><a href='/portfolio-check/'>Check the overlap of your own funds</a></p>")

        # ------------------------------------------------ FAQ
        aplus = [s.get("Regular") for s in top if (s.get("Regular") or {}).get("tier") == "A+"]
        faq = [
            (f"Which {lc} funds are rated A+ in {mname}?",
             (f"Among Regular plans: {', '.join(x['_name'] for x in aplus)}. " if aplus else f"No Regular {lc} plan is rated A+ this month. ")
             + f"{len(top)} schemes are rated A+ or A in at least one plan. Ratings compare each fund with its own category and plan type, on its record against {yard}."),
            (f"Is the top-rated {lc} fund the best one to invest in?",
             "Not necessarily. The rating describes the track record so far: return over the index, how consistently it was earned, risk, cost and portfolio. "
             "Our own backtest found that top ratings did not reliably predict the next three years. Use the shortlist to avoid weak records, then choose for your goal, "
             "the funds you already hold, and how much overlap you can accept."),
            ("Direct plan or Regular plan?",
             "The same portfolio. A Direct plan has no distributor commission, so its expense ratio is lower and its return slightly higher. A Regular plan pays a "
             "distributor such as us, through the expense ratio, for advice and service. Plans are rated separately: Regular against Regular, Direct against Direct."),
            ("How often does this list change?",
             "Returns update every weekday, but ratings change twice a month: on the 11th and the 16th, after fund houses publish their monthly portfolios."),
        ]
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        list_ld = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Top-rated {lc} funds, {mname}", "itemListElement": items}

        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="{cat_path}">{B.e(c)}</a> › Top-rated</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Top-rated {B.e(lc)} funds: {B.e(mname)}</h1>
<p class="lede" style="margin-top:12px">The {len(top)} {B.e(lc)} schemes rated A+ or A on their track record this month, out of {n_rated} rated Regular plans: why each one rates well, what changed since last month, and how much they overlap. Data as of {B.dmy(as_of)}.</p>
<p style="margin-top:12px">Each fund is compared only with other {B.e(lc)} funds of the same plan type: return over {B.e(yard)}, how consistently it was earned, risk, cost and portfolio. <a href="/#method">How the ratings work</a>.</p>
{''.join(cards)}
{change}
{ov_html}
<div class="card row" style="margin-top:28px;justify-content:space-between;gap:14px;flex-wrap:wrap"><div><b style="font:500 18px var(--f-display)">Which of these suits you?</b><p class="muted" style="margin:4px 0 0;font-size:14px">That depends on your goal, your other funds and how much overlap you hold. Tell us what you have and we'll look at it with you.</p></div><a class="btn primary" href="{B.wa_link(f"Hello Aeterna, I'm looking at top-rated {c} funds and would like help choosing.")}" target="_blank" rel="noopener">Ask us on WhatsApp</a></div>
<p style="margin-top:20px"><a href="{cat_path}">All {len(L)} {B.e(lc)} plans, with every rating</a> · <a href="/mutual-funds/">Other categories</a></p>
<h2 style="font-size:24px;margin-top:34px">Common questions</h2>{''.join(f'<details class="faq"><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>' for q, a in faq)}
<p class="note" style="margin-top:28px">Ratings describe past track records and are not a recommendation to buy or sell, or a forecast. Mutual fund investments are subject to market risks; read the scheme documents before investing.</p>
</div></section>"""
        title = f"Top-rated {lc} funds, {mname}: {len(top)} rated A+ or A | Aeterna Wealth"
        desc = (f"The {len(top)} {lc} funds rated A+ or A on their track record in {mname}: why each rates well, what changed since last month, "
                f"overlap between them, Direct vs Regular. Updated monthly; not a forecast.")
        B.write(path, B.page(title, desc[:300], path, body, (faq_ld, list_ld, B.crumbs([("Mutual funds", "/mutual-funds/"), (c, cat_path), ("Top-rated", path)]))))
        urls.append((path, "weekly", "0.8"))
        made[c] = path
    return made
