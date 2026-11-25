"""Two market-wide pages from data the engine already has (Nov 2026). Standard library only (the site build has no pandas).

/mutual-funds/crowded-stocks/  which stocks active equity funds crowd into: share of each company owned by funds
    (fund value ÷ AMFI's 6-month average market cap, site/data/mcap.json), how many schemes and fund houses hold it,
    and this month's new positions and exits (each scheme's portfolio against its previous month's).
/mutual-funds/money-flows/     where new money is going: net flows by category, scheme and fund house, estimated from
    AMFI's quarterly average AUM (engine/flows.py: AUM growth not explained by returns).
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

import stock_pages as SP

ROWS = 25


def _schemes(funds):
    by = defaultdict(list)
    for f in funds:
        if f.get("pair_key"):
            by[f["pair_key"]].append(f)
    return {pk: sorted(L, key=lambda x: (x.get("plan_type") != "Regular", x["code"]))[0] for pk, L in by.items()}


def _cr(v):
    return "–" if v is None else f"{v:,.0f}"


def _page(B, path, title, desc, h1, lede, body, crumb):
    html = (f"<section class='band' style='padding-top:28px'><div class='wrap'><nav aria-label='Breadcrumb' class='muted' style='font-size:13.5px'>"
            f"<a href='/mutual-funds/'>Mutual funds</a> › {B.e(crumb)}</nav><h1 style='font-size:clamp(28px,4vw,42px);margin-top:14px'>{B.e(h1)}</h1>"
            f"<p class='lede' style='margin-top:12px'>{lede}</p>{body}</div></section>")
    B.write(path, B.page(title, desc, path, html, (B.crumbs([("Mutual funds", "/mutual-funds/"), (crumb, path)]),)))


def _table(head, rows, first_w="40%"):
    th = "".join(f"<th{' class=\"l\"' if i == 0 else ''}>{h}</th>" for i, h in enumerate(head))
    return (f"<div class='tablewrap' style='margin-top:12px'><table><thead><tr>{th}</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td class='{'l' if i == 0 else 'num'}'>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>")


# ------------------------------------------------------------------ crowded stocks
def crowded(B, funds, hold, urls, stock_url):
    root = B.S.parent
    mp = B.S / "data" / "mcap.json"
    M = json.loads(mp.read_text()) if mp.exists() else {}
    mc, period = M.get("s", {}), M.get("period", "")
    sch = {pk: f for pk, f in _schemes(funds).items() if f.get("asset_class") == "Equity" and f.get("category") != "Index Fund"}
    names, H, prev_cache = defaultdict(Counter), defaultdict(list), {}
    new, gone = Counter(), Counter()
    month = Counter()
    for pk, rows in hold.items():
        f = sch.get(pk)
        if not f:
            continue
        aum = f.get("aum_cr") if isinstance(f.get("aum_cr"), (int, float)) else None
        cur = {}
        for r in rows:
            if len(r) >= 3 and str(r[0]).startswith("INE") and isinstance(r[2], (int, float)) and r[2] > 0:
                cur[r[0]] = cur.get(r[0], 0) + float(r[2])
                names[r[0]][r[1]] += 1
        for isin, w in cur.items():
            H[isin].append((f, w, aum * w / 100 if aum else None))
        m = f.get("holdings_month")
        if m:
            month[m] += 1
            pm = SP._prev_month(m)
            if pm not in prev_cache:
                prev_cache[pm] = SP._load_weights(root, pm)
            pw = (prev_cache[pm] or {}).get(pk)
            if pw:
                for isin in cur:
                    if isin not in pw:
                        new[isin] += 1
                for isin, w in pw.items():
                    if str(isin).startswith("INE") and w > 0 and isin not in cur:
                        gone[isin] += 1
    def nm(i):
        return SP.clean_name(names[i].most_common(1)[0][0]) if names[i] else i
    def link(i):
        u = stock_url.get(i) if isinstance(stock_url, dict) else None
        return f"<a href='{u}'>{B.e(nm(i))}</a>" if u else B.e(nm(i))
    S = {}
    for i, L in H.items():
        cr = sum(x[2] or 0 for x in L)
        m = mc.get(i)
        S[i] = {"n": len(L), "amcs": len({x[0].get("amc") for x in L}), "cr": cr, "own": cr / m[1] * 100 if m and m[1] else None,
                "size": m[2] if m else None, "rank": m[0] if m else None}
    size = lambda s: {"large": "Large", "mid": "Mid", "small": "Small"}.get(s["size"], "–")
    row = lambda i: [link(i), size(S[i]), S[i]["n"], S[i]["amcs"], "–" if S[i]["own"] is None else f"{S[i]['own']:.1f}%", _cr(S[i]["cr"])]
    head = ["Stock", "Size", "Schemes", "Fund houses", "Owned by these funds", "Held, ₹ cr"]
    wide = [i for i in S if S[i]["n"] >= 10 and S[i]["own"] is not None]
    top_own = sorted(wide, key=lambda i: -S[i]["own"])[:ROWS]
    small = sorted([i for i in wide if S[i]["size"] in ("mid", "small")], key=lambda i: -S[i]["own"])[:ROWS]
    most = sorted(S, key=lambda i: -S[i]["n"])[:ROWS]
    piling = sorted([i for i in new if new[i] >= 3], key=lambda i: -(new[i] - gone[i]))[:ROWS]
    leaving = sorted([i for i in gone if gone[i] >= 3], key=lambda i: -(gone[i] - new[i]))[:ROWS]
    lead = month.most_common(1)[0][0] if month else ""
    body = (
        f"<h2 style='font-size:26px;margin-top:32px'>Most crowded: the biggest share of a company owned by these funds</h2>"
        "<p style='margin-top:8px'>When funds together own a large slice of a company, they tend to buy and sell it at the same time; that can push the price "
        "up on the way in and down hard on the way out. Stocks held by at least 10 schemes.</p>" + _table(head, [row(i) for i in top_own])
        + f"<h2 style='font-size:26px;margin-top:36px'>Crowded mid and small caps</h2>"
        "<p style='margin-top:8px'>The same measure for mid and small companies, where fewer shares trade each day, so a rush to sell weighs more.</p>"
        + _table(head, [row(i) for i in small])
        + f"<h2 style='font-size:26px;margin-top:36px'>Piling in: most new positions this month</h2>"
        + _table(["Stock", "Size", "Schemes that bought it new", "Schemes that sold out", "Schemes holding", "Owned by these funds"],
                 [[link(i), size(S[i]), new[i], gone[i], S[i]["n"], "–" if S[i]["own"] is None else f"{S[i]['own']:.1f}%"] for i in piling if i in S])
        + f"<h2 style='font-size:26px;margin-top:36px'>Heading for the exit: most schemes selling out</h2>"
        + _table(["Stock", "Schemes that sold out", "Schemes that bought it new"],
                 [[link(i) if i in S else B.e(nm(i)), gone[i], new[i]] for i in leaving])
        + f"<h2 style='font-size:26px;margin-top:36px'>Most widely held</h2>" + _table(head, [row(i) for i in most])
        + f"<p class='muted' style='font-size:12.5px;margin-top:14px'>Active equity funds only (index funds left out), each scheme counted once. Value: scheme AUM × the stock's weight, "
        f"approximate. Owned by these funds: that value ÷ the company's 6-month average market cap on AMFI's list ({B.e(period)}), so it is an estimate and leaves out "
        f"index funds, hybrid funds, ETFs and other investors. New positions and exits: each scheme's latest portfolio ({B.mon(lead) if lead else 'latest month'}) "
        "against its previous month's. Facts from fund portfolios, not a recommendation to buy or sell any stock.</p>")
    lede = (f"Which companies India's active equity funds own the most of, where many funds are buying at once, and where they are leaving. "
            f"From {len(sch)} schemes' monthly portfolios.")
    _page(B, "/mutual-funds/crowded-stocks/", "Crowded stocks: what mutual funds own most of, and are buying and selling | Aeterna Wealth",
          "The stocks Indian equity mutual funds crowd into: the share of each company funds own, crowded mid and small caps, and the stocks most funds bought or sold this month.",
          "Crowded stocks: where mutual funds are piling in", lede, body, "Crowded stocks")
    urls.append(("/mutual-funds/crowded-stocks/", "monthly", "0.7"))


# ------------------------------------------------------------------ money flows
def flows(B, funds, urls):
    sch = {pk: f for pk, f in _schemes(funds).items() if f.get("asset_class") in ("Equity", "Hybrid") and f.get("category") != "Index Fund"}
    q = Counter(f.get("flow_quarter") for f in sch.values() if f.get("flow_quarter")).most_common(1)
    qlab = q[0][0] if q else ""
    rows = []
    for pk, f in sch.items():
        a, a0 = f.get("aum_cr"), f.get("aum_1y_ago_cr")
        f1, f4 = f.get("flow_1q"), f.get("flow_4q")
        rows.append({"f": f, "aum": a if isinstance(a, (int, float)) else None,
                     "q": f1 * a / (1 + f1) if isinstance(f1, (int, float)) and isinstance(a, (int, float)) and f1 > -1 else None,
                     "y": f4 * a0 if isinstance(f4, (int, float)) and isinstance(a0, (int, float)) else None})
    def agg(key):
        g = defaultdict(lambda: {"aum": 0, "q": 0, "y": 0, "n": 0, "a0": 0})
        for r in rows:
            k = key(r["f"])
            g[k]["n"] += 1
            g[k]["aum"] += r["aum"] or 0
            g[k]["q"] += r["q"] or 0
            g[k]["y"] += r["y"] or 0
            g[k]["a0"] += (r["f"].get("aum_1y_ago_cr") or 0) if r["y"] is not None else 0
        return g
    pc = lambda a, b: "–" if not b else f"{a / b * 100:+.1f}%"
    sg = lambda v: f"{v:+,.0f}"
    cat = agg(lambda f: f["category"])
    crow = [[B.e(c), _cr(v["aum"]), sg(v["q"]), sg(v["y"]), pc(v["y"], v["a0"])] for c, v in sorted(cat.items(), key=lambda x: -x[1]["y"])]
    amc = agg(lambda f: f.get("amc") or "Other")
    arow = [[f"<a href='/mutual-funds/amc/{B.slug(a)}/'>{B.e(a)}</a>", _cr(v["aum"]), sg(v["y"]), pc(v["y"], v["a0"])]
            for a, v in sorted(amc.items(), key=lambda x: -x[1]["y"])[:ROWS]]
    fl = [r for r in rows if r["y"] is not None]
    fn = lambda r: f"<a href='{r['f']['_url']}'>{B.e(r['f']['_name'])}</a><small>{B.e(r['f']['category'])}</small>"
    inn = [[fn(r), sg(r["y"]), pc(r["y"], r["f"].get("aum_1y_ago_cr")), _cr(r["aum"])] for r in sorted(fl, key=lambda r: -r["y"])[:ROWS]]
    out = [[fn(r), sg(r["y"]), pc(r["y"], r["f"].get("aum_1y_ago_cr")), _cr(r["aum"])] for r in sorted(fl, key=lambda r: r["y"])[:15] if r["y"] < 0]
    tq, ty = sum(r["q"] or 0 for r in rows), sum(r["y"] or 0 for r in rows)
    body = (
        f"<div class='grid g3' style='margin-top:22px'><div class='card'><div class='big-fig'>₹{tq:,.0f} cr</div><p class='muted'>net new money into active equity and hybrid funds, quarter to {B.e(qlab)} (estimate)</p></div>"
        f"<div class='card'><div class='big-fig'>₹{ty:,.0f} cr</div><p class='muted'>over the last 4 quarters</p></div>"
        f"<div class='card'><div class='big-fig'>{len(sch)}</div><p class='muted'>schemes covered</p></div></div>"
        "<h2 style='font-size:26px;margin-top:36px'>By category</h2>"
        + _table(["Category", "AUM, ₹ cr", f"Net flow, quarter to {B.e(qlab)}, ₹ cr", "Net flow, 4 quarters, ₹ cr", "4 quarters, % of AUM a year ago"], crow)
        + "<h2 style='font-size:26px;margin-top:36px'>Schemes taking in the most money</h2>"
        + _table(["Scheme", "Net flow, 4 quarters, ₹ cr", "% of AUM a year ago", "AUM now, ₹ cr"], inn)
        + ("<h2 style='font-size:26px;margin-top:36px'>Schemes losing the most money</h2>" + _table(["Scheme", "Net flow, 4 quarters, ₹ cr", "% of AUM a year ago", "AUM now, ₹ cr"], out) if out else "")
        + "<h2 style='font-size:26px;margin-top:36px'>By fund house</h2>"
        + _table(["Fund house", "AUM, ₹ cr", "Net flow, 4 quarters, ₹ cr", "% of AUM a year ago"], arow)
        + "<h2 style='font-size:24px;margin-top:36px'>Does following the money work?</h2>"
        "<p style='margin-top:8px'>Not on its own. In our 2019–2025 test, the schemes with the heaviest outflows beat their index over the next 3 years "
        "52% of the time, against 51% for those with the heaviest inflows. Money tends to arrive after strong years, and a flood of it into one category "
        "or fund house is better read as a sign of popularity than as a forecast. That is why flows are shown here but are not part of our ratings.</p>"
        f"<p class='muted' style='font-size:12.5px;margin-top:14px'>Estimates from AMFI's quarterly average AUM: the growth in a scheme's assets not explained by its "
        "returns. Regular and Direct plans together, each scheme counted once; active equity and hybrid funds (index funds and debt funds left out). "
        "Quarterly averages smooth the timing, so treat figures as approximate.</p>")
    _page(B, "/mutual-funds/money-flows/", f"Mutual fund money flows: where investors are putting money ({qlab}) | Aeterna Wealth",
          "Where new money is going in Indian mutual funds: net inflows and outflows by category, scheme and fund house, estimated from AMFI data, updated each quarter.",
          "Where the money is going", f"Net new money into India's active equity and hybrid funds, by category, scheme and fund house, to {B.e(qlab)}.", body, "Money flows")
    urls.append(("/mutual-funds/money-flows/", "monthly", "0.7"))
