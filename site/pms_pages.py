"""PMS (portfolio management services) and AIF pages, from site/data/pms.json (tools/pms_build.py). Standard library only.

/pms/                                  hub: what we track, peer tables, managers, how to read the numbers
/pms/ratings/<group>/                  every rated strategy in a peer group (equity, debt, hybrid and multi-asset)
/pms/<manager>/                        a portfolio manager: assets, every strategy we show (rated or not)
/pms/<manager>/<strategy>/             a strategy: returns, consistency, risk, money flows, peer ranks, rating
/pms/how-pms-returns-are-measured/     TWRR, after fees, before tax; what APMI reports; our method
/aif/                                  AIFs: categories, what is public and what is not
Rules: research framing; one general "talk to us" line; no "best"/"buy"; no distributor registration shown.
"""
import json
import math
from collections import defaultdict

GROUP_SLUG = {"Equity": "equity", "Debt": "debt", "Hybrid and multi-asset": "hybrid-and-multi-asset"}
TIER_WORD = {"A+": "Leading", "A": "Strong", "B": "In line", "C": "Lagging"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _mo(m):
    return f"{MON[int(m[5:7]) - 1]} {m[:4]}"


def _p(v, d=1, plus=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    s = f"{v:,.{d}f}%"
    return ("+" + s) if plus and v > 0 else s.replace("-", "−")


def _n(v, d=2):
    return "–" if v is None else f"{v:,.{d}f}".replace("-", "−")


def _cr(v):
    return "–" if v is None else f"₹{v:,.0f} cr"


def _cls(v):
    return "" if v is None else (" style='color:var(--good)'" if v > 0 else " style='color:var(--bad)'" if v < 0 else "")


def url_s(s):
    return f"/pms/{s['mslug']}/{s['slug']}/"


def url_m(m):
    return f"/pms/{m}/"


STYLE = """<style>
.pm-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;margin-top:24px}
.pm-kpis div{background:var(--surface);padding:14px 16px}.pm-kpis span{display:block;color:var(--ink-2);font-size:13px}.pm-kpis b{font:500 22px var(--f-mono)}
.pm-sec{margin-top:40px}.pm-sec h2{font-size:26px}.pm-sec>p.muted{margin-top:6px;font-size:14.5px;max-width:760px}
.pm-chart{margin-top:14px;border:1px solid var(--rule);border-radius:var(--r);background:var(--surface);padding:10px}
.pm-chart svg{width:100%;height:auto;display:block}.pm-leg{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:4px 4px 0}
.pm-leg i{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px}
.pm-heat{border-collapse:collapse;font:500 12.5px var(--f-mono);width:100%;min-width:640px}.pm-heat td,.pm-heat th{border:1px solid var(--rule);padding:5px 4px;text-align:center}
.pm-heat th{font:600 12px var(--f-body);color:var(--ink-2)}.pm-bar{height:8px;border-radius:4px;background:var(--rule);overflow:hidden;min-width:80px}.pm-bar i{display:block;height:100%;background:var(--teal)}
@media (max-width:700px){.pm-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.pm-kpis b{font-size:19px}}
</style>"""


def _table(head, rows, cls=""):
    th = "".join(f"<th{' class=\"l\"' if i == 0 else ''}>{h}</th>" for i, h in enumerate(head))
    return (f"<div class='tablewrap' style='margin-top:12px'><table class='{cls}'><thead><tr>{th}</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td class='{'l' if i == 0 else 'num'}'>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>")


def _line_chart(series, labels, fmt=lambda v: f"{v:,.0f}", zero=None, h=260):
    """series: [(name, colour, values)]; labels: month keys. Plain SVG, no script."""
    W, H, L, R, T, Bm = 760, h, 56, 12, 12, 28
    vals = [v for _, _, s in series for v in s if v is not None]
    if not vals:
        return ""
    lo, hi = min(vals + ([zero] if zero is not None else [])), max(vals + ([zero] if zero is not None else []))
    if hi == lo:
        hi += 1
    pad = (hi - lo) * 0.06
    lo, hi = lo - pad, hi + pad
    n = len(labels)
    x = lambda i: L + (W - L - R) * (i / max(1, n - 1))
    y = lambda v: T + (H - T - Bm) * (1 - (v - lo) / (hi - lo))
    g = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        g.append(f"<line x1='{L}' x2='{W - R}' y1='{y(v):.1f}' y2='{y(v):.1f}' stroke='var(--rule)'/>"
                 f"<text x='{L - 6}' y='{y(v) + 4:.1f}' text-anchor='end' font-size='11' fill='var(--ink-3)'>{fmt(v)}</text>")
    if zero is not None:
        g.append(f"<line x1='{L}' x2='{W - R}' y1='{y(zero):.1f}' y2='{y(zero):.1f}' stroke='var(--ink-3)' stroke-dasharray='3 3'/>")
    step = max(1, n // 6)
    for i in range(0, n, step):
        g.append(f"<text x='{x(i):.1f}' y='{H - 8}' text-anchor='middle' font-size='11' fill='var(--ink-3)'>{_mo(labels[i])}</text>")
    for name, col, s in series:
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s) if v is not None)
        g.append(f"<polyline fill='none' stroke='{col}' stroke-width='2.2' points='{pts}'/>")
    leg = "".join(f"<span><i style='background:{c}'></i>{n_}</span>" for n_, c, _ in series)
    return (f"<div class='pm-chart'><svg viewBox='0 0 {W} {H}' role='img' aria-label='{series[0][0]} chart'>{''.join(g)}</svg>"
            f"<div class='pm-leg'>{leg}</div></div>")


def _bars(labels, vals, h=200):
    W, H, L, R, T, Bm = 760, h, 56, 12, 12, 28
    v2 = [v for v in vals if v is not None]
    if not v2:
        return ""
    lo, hi = min(0, min(v2)), max(0, max(v2))
    if hi == lo:
        hi += 1
    n = len(labels)
    bw = (W - L - R) / n
    y = lambda v: T + (H - T - Bm) * (1 - (v - lo) / (hi - lo))
    g = [f"<line x1='{L}' x2='{W - R}' y1='{y(0):.1f}' y2='{y(0):.1f}' stroke='var(--ink-3)'/>"]
    for k in (lo, hi):
        g.append(f"<text x='{L - 6}' y='{y(k) + 4:.1f}' text-anchor='end' font-size='11' fill='var(--ink-3)'>{k:,.0f}</text>")
    for i, v in enumerate(vals):
        if v is None:
            continue
        y0, y1 = sorted((y(0), y(v)))
        g.append(f"<rect x='{L + i * bw + 1:.1f}' y='{y0:.1f}' width='{max(1, bw - 2):.1f}' height='{max(0.5, y1 - y0):.1f}' "
                 f"fill='{'var(--good)' if v >= 0 else 'var(--bad)'}'><title>{_mo(labels[i])}: ₹{v:,.0f} cr</title></rect>")
    step = max(1, n // 6)
    for i in range(0, n, step):
        g.append(f"<text x='{L + i * bw + bw / 2:.1f}' y='{H - 8}' text-anchor='middle' font-size='11' fill='var(--ink-3)'>{_mo(labels[i])}</text>")
    return f"<div class='pm-chart'><svg viewBox='0 0 {W} {H}' role='img' aria-label='Money in and out'>{''.join(g)}</svg></div>"


def _chain(rs):
    g = 1.0
    for r in rs:
        g *= 1 + r / 100
    return g


def _wrap(B, path, title, desc, crumbs, h1, lede, body, ld=()):
    nav = " › ".join(f"<a href='{u}'>{B.e(t)}</a>" if u != path else B.e(t) for t, u in crumbs)
    html = (STYLE + f"<section class='band' style='padding-top:28px'><div class='wrap'><nav aria-label='Breadcrumb' class='muted' style='font-size:13.5px'>{nav}</nav>"
            f"<h1 style='font-size:clamp(28px,4vw,42px);margin-top:14px'>{B.e(h1)}</h1><p class='lede' style='margin-top:12px'>{lede}</p>{body}"
            f"{_talk(B)}{_foot(B)}</div></section>")
    B.write(path, B.page(title, desc, path, html, (B.crumbs(crumbs),) + tuple(ld)))


def _talk(B):
    wa = B.wa_link("Hello Aeterna, I'd like a second opinion on a PMS.")
    return ("<div class='card row' style='justify-content:space-between;gap:16px;flex-wrap:wrap;border-left:4px solid var(--teal);margin-top:40px'>"
            "<div style='flex:1;min-width:240px'><b style='font:500 19px var(--f-display)'>Want a second opinion on a PMS?</b>"
            "<p class='muted' style='margin:4px 0 0;font-size:14px'>Whether you hold one or are considering one, talk to us: we will go through its record, "
            "its risks and how it fits with the rest of your money.</p></div>"
            f"<a class='btn primary' href='{wa}' target='_blank' rel='noopener'>Talk to us</a></div>")


def _foot(B):
    return ("<p class='muted' style='font-size:13px;margin-top:22px'>Source: APMI (Association of Portfolio Managers in India) monthly reports, "
            "which portfolio managers file as SEBI requires. Returns are time-weighted, after all fees and expenses and before the investor's tax; "
            "periods over a year are annualised. Index: Nifty 500 TRI (total return). Ratings describe past track records and are not a recommendation "
            "or a forecast; past performance does not guarantee future returns. PMS investments need at least ₹50 lakh, can lose value and carry "
            "higher fees than mutual funds; read the portfolio manager's disclosure document before investing. "
            "<a href='/pms/how-pms-returns-are-measured/'>How we measure</a> · <a href='/disclosures/'>Disclosures</a></p>")


# ------------------------------------------------------------------ strategy page
def strategy_page(B, D, s, peers, mgr_all):
    path = url_s(s)
    m, a = s["m"], s["apmi"]
    months, r, b = s["months"], s["r"], s["b"]
    tier = s.get("tier")
    g = s["group"]
    gurl = f"/pms/ratings/{GROUP_SLUG[g]}/"
    eq = g == "Equity"
    # headline
    kp = [("Assets", _cr(s["aum"])), ("3-year return a year", _p(a["r3y"])),
          ("vs Nifty 500 TRI, 3 years" if eq else "1-year return", _p(m.get("ex3y"), 1, True) if eq else _p(a["r1y"])),
          ("Worst fall (month-end)", _p(m.get("max_dd")))]
    kpis = "<div class='pm-kpis'>" + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in kp) + "</div>"
    rating = ""
    if tier:
        why = []
        pc = s.get("pct", {})
        lab = {"ex3y": "3-year return over the index", "ir": "consistency of its lead (information ratio)", "hit_12m": "share of 12-month spells ahead of the index",
               "down_capture": "protection in falling months", "max_dd": "worst fall", "worst_12m_ex": "worst 12 months against the index",
               "hit_m": "share of months ahead of the index", "ann_ret_ex": "return", "vol": "steadiness", }
        top = sorted(((v, k) for k, v in pc.items()), reverse=True)
        strong = [lab[k] for v, k in top[:2] if v >= 0.6]
        weak = [lab[k] for v, k in top[::-1][:2] if v <= 0.4]
        if strong:
            why.append("Stronger than most peers on " + " and ".join(strong) + ".")
        if weak:
            why.append("Weaker on " + " and ".join(weak) + ".")
        if s.get("flag"):
            why.append(s["flag"] + ".")
        rating = (f"<div class='card' style='margin-top:20px;display:flex;gap:16px;align-items:flex-start'>{B.tier_badge(tier)}<div>"
                  f"<b>{TIER_WORD[tier]}: {s['rank']} of {s['of']} rated {g.lower()} strategies</b>"
                  f"<p class='muted' style='margin:4px 0 0;font-size:14px'>Score {s['score']:.0f} of 100. {' '.join(why)} "
                  f"<a href='/pms/how-pms-returns-are-measured/#rating'>How the rating works</a></p></div></div>")
    # trailing returns
    per = [("1 month", "r1m"), ("3 months", "r3m"), ("6 months", "r6m"), ("1 year", "r1y"), ("2 years", "r2y"),
           ("3 years", "r3y"), ("4 years", "r4y"), ("5 years", "r5y"), ("Since launch", "rsi")]
    bl = D["bench_levels"]
    last = D["as_of"]
    ixr = {}
    for lab_, k in per:
        nm = {"r1m": 1, "r3m": 3, "r6m": 6, "r1y": 12, "r2y": 24, "r3y": 36, "r4y": 48, "r5y": 60}.get(k)
        if nm and last in bl and len(bl) > nm:
            keys = sorted(bl)
            i = keys.index(last)
            if i - nm >= 0:
                v = bl[keys[i]] / bl[keys[i - nm]]
                ixr[k] = ((v ** (12 / nm) - 1) if nm > 12 else (v - 1)) * 100
    rows = [[lab_, _p(a[k]), _p(ixr.get(k)) if eq else "–", f"<span{_cls(None if a[k] is None or ixr.get(k) is None else a[k] - ixr[k])}>"
             f"{_p(None if a[k] is None or ixr.get(k) is None else a[k] - ixr[k], 1, True)}</span>" if eq else "–"] for lab_, k in per if a.get(k) is not None]
    ret_tbl = _table(["Period", "Strategy", "Nifty 500 TRI", "Difference"], rows)
    # growth of Rs 50 lakh
    gs, gb, x1, x2 = [], [], 50.0, 50.0
    for x, y in zip(r, b):
        x1 *= 1 + x / 100
        x2 *= 1 + y / 100
        gs.append(x1)
        gb.append(x2)
    labels = months
    growth = _line_chart([(s["name"], "var(--teal)", gs), ("Nifty 500 TRI", "var(--brass)", gb)], labels, fmt=lambda v: f"₹{v:,.0f}L") if eq else \
        _line_chart([(s["name"], "var(--teal)", gs)], labels, fmt=lambda v: f"₹{v:,.0f}L")
    # rolling 12-month return vs index
    r12s, r12b, lab12 = [], [], []
    for i in range(12, len(r) + 1):
        r12s.append((_chain(r[i - 12:i]) - 1) * 100)
        r12b.append((_chain(b[i - 12:i]) - 1) * 100)
        lab12.append(months[i - 1])
    roll = _line_chart([("Strategy, 12 months to each month", "var(--teal)", r12s)] + ([("Nifty 500 TRI", "var(--brass)", r12b)] if eq else []),
                       lab12, fmt=lambda v: f"{v:,.0f}%", zero=0) if r12s else ""
    # calendar years
    cal = s.get("cal", {})
    crow = []
    for y, c in sorted(cal.items()):
        lab_ = y + (f" ({MON[int(c['from'][5:]) - 1]}–{MON[int(c['to'][5:]) - 1]})" if c["n"] < 12 else "")
        crow.append([lab_, _p(c["r"]), _p(c["b"]) if eq else "–", f"<span{_cls(c['r'] - c['b'])}>{_p(c['r'] - c['b'], 1, True)}</span>" if eq else "–"])
    cal_tbl = _table(["Year", "Strategy", "Nifty 500 TRI", "Difference"], crow) if crow else ""
    # monthly grid
    by = defaultdict(dict)
    for mo, x, y in zip(months, r, b):
        by[mo[:4]][int(mo[5:]) - 1] = (x, y)
    hrow = []
    for y in sorted(by):
        cells = []
        for k in range(12):
            if k in by[y]:
                x, yy = by[y][k]
                d = x - yy
                col = f"color-mix(in srgb,var(--{'good' if d >= 0 else 'bad'}) {min(60, 10 + abs(d) * 8):.0f}%,var(--surface))" if eq else "var(--surface)"
                cells.append(f"<td style='background:{col}' title='{MON[k]} {y}: strategy {x:.2f}%, index {yy:.2f}%'>{x:.1f}</td>")
            else:
                cells.append("<td></td>")
        hrow.append(f"<tr><th>{y}</th>{''.join(cells)}</tr>")
    heat = ("<div class='tablewrap' style='margin-top:12px'><table class='pm-heat'><thead><tr><th></th>" + "".join(f"<th>{x}</th>" for x in MON)
            + "</tr></thead><tbody>" + "".join(hrow) + "</tbody></table></div>")
    # consistency and risk
    cons = [("Months ahead of the index", _p(None if m.get("hit_m") is None else m["hit_m"] * 100, 0)),
            ("12-month spells ahead of the index", _p(None if m.get("hit_12m") is None else m["hit_12m"] * 100, 0)),
            ("Worst 12 months against the index", _p(m.get("worst_12m_ex"), 1, True)),
            ("Information ratio (consistency of the lead)", _n(m.get("ir"))),
            ("Best 12 months", _p(max(r12s) if r12s else None)), ("Worst 12 months", _p(min(r12s) if r12s else None))]
    if not eq:
        cons = [cons[4], cons[5]]
    risk = [("Worst fall, month-end to month-end", _p(m.get("max_dd"))),
            ("Months from peak to bottom", str(m.get("dd_months")) if m.get("dd_months") is not None else "–"),
            ("Months to recover", str(m.get("recovery_months")) if m.get("recovery_months") is not None else ("not yet" if (m.get("max_dd") or 0) < 0 else "–")),
            ("Share of the index's falls taken (down capture)", _p(None if m.get("down_capture") is None else m["down_capture"] * 100, 0) if eq else "–"),
            ("Share of the index's rises taken (up capture)", _p(None if m.get("up_capture") is None else m["up_capture"] * 100, 0) if eq else "–"),
            ("Volatility a year", _p(m.get("vol"))), ("Beta to Nifty 500", _n(m.get("beta")) if eq else "–"),
            ("Tracking error a year", _p(m.get("te")) if eq else "–"), ("Sharpe ratio (6.5% risk-free)", _n(m.get("sharpe"))),
            ("Sortino ratio", _n(m.get("sortino"))), ("Months with a loss", _p(None if m.get("neg_months") is None else m["neg_months"] * 100, 0)),
            ("Worst month", _p(m.get("worst_month"))), ("Best month", _p(m.get("best_month")))]
    risk = [x for x in risk if x[1] != "–"]
    kv = lambda L: "<div class='kv' style='margin-top:12px'>" + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in L) + "</div>"
    # money flows
    fl = s.get("flows", {})
    fm = [mo for mo in months if mo in fl]
    flows = ""
    if len(fm) >= 6:
        f12 = m.get("flow12_pct")
        tot12 = sum(fl[mo] for mo in fm[-12:])
        flows = (f"<div class='pm-sec'><h2>Money coming in and going out</h2><p class='muted'>Each month's change in assets that the month's return does not explain: "
                 f"new money in (green) or withdrawals (red), in ₹ crore. An estimate from APMI's month-end assets. Last 12 months: {'+' if tot12 >= 0 else '−'}₹{abs(tot12):,.0f} cr"
                 f"{f', {f12:+.0f}% of the assets a year ago' if f12 is not None else ''}.</p>{_bars(fm, [fl[mo] for mo in fm])}</div>")
    aum_hist = s.get("aum_hist", {})
    am = sorted(aum_hist)
    aum_chart = _line_chart([("Assets (₹ crore)", "var(--teal)", [aum_hist[k] for k in am])], am, fmt=lambda v: f"{v:,.0f}") if len(am) >= 6 else ""
    # peers
    pr = sorted([p for p in peers if p.get("rank")], key=lambda p: p["rank"])
    if s.get("rank"):
        i = s["rank"] - 1
        near = pr[max(0, i - 4): i + 5]
    else:
        near = pr[:8]
    prow = [[(f"<b>{B.e(p['name'])}</b>" if p is s else f"<a href='{url_s(p)}'>{B.e(p['name'])}</a>") + f"<div class='muted' style='font-size:12.5px'>{B.e(p['manager'])}</div>",
             B.tier_badge(p.get("tier")), str(p.get("rank", "–")), _p(p["apmi"].get("r3y")), _p(p["m"].get("max_dd")), _cr(p["aum"])] for p in near]
    peer_tbl = _table(["Strategy", "Rating", "Rank", "3 years a year", "Worst fall", "Assets"], prow)
    # percentile bars
    lab = {"ex3y": "3-year return over the index", "ir": "Information ratio", "hit_12m": "12-month spells ahead", "down_capture": "Protection in falling months",
           "max_dd": "Worst fall", "worst_12m_ex": "Worst 12 months vs index", "hit_m": "Months ahead", "ann_ret_ex": "Return", "vol": "Steadiness"}
    pc = s.get("pct", {})
    bars = "".join(f"<div><span>{lab[k]}</span><b style='display:flex;gap:10px;align-items:center'><span class='pm-bar'><i style='width:{v * 100:.0f}%'></i></span>{v * 100:.0f}</b></div>"
                   for k, v in pc.items())
    pct_html = (f"<p class='muted' style='font-size:14px;margin-top:10px'>Where it stands among {s.get('of', len(pr))} rated {g.lower()} strategies on each measure "
                f"(100 = best in the group).</p><div class='kv' style='margin-top:6px'>{bars}</div>") if bars else ""
    others = [x for x in mgr_all if x is not s]
    oth = ""
    if others:
        oth = ("<div class='pm-sec'><h2>Other strategies from " + B.e(s["manager"]) + "</h2>"
               + _table(["Strategy", "Rating", "3 years a year", "Assets"],
                        [[(f"<a href='{url_s(x)}'>{B.e(x['name'])}</a>" if x.get("rated") else B.e(x["name"])), B.tier_badge(x.get("tier")) if x.get("tier") else "<span class='muted'>not rated</span>",
                          _p(x["apmi"].get("r3y")), _cr(x["aum"])] for x in sorted(others, key=lambda x: -x["aum"])])
               + f"<p style='margin-top:10px'><a href='{url_m(s['mslug'])}'>All of {B.e(s['manager'])}'s strategies</a></p></div>")
    first, lastm = months[0], months[-1]
    ex3 = m.get("ex3y")
    lede = (f"{B.e(s['name'])} is a discretionary {s['type'].lower()} PMS strategy run by {B.e(s['manager'])}, with {_cr(s['aum'])} of client money "
            f"at the end of {_mo(lastm)}. Over 3 years it returned {_p(a['r3y'])} a year after fees"
            + (f", {_p(abs(ex3))} a year {'more' if ex3 >= 0 else 'less'} than Nifty 500 TRI" if eq and ex3 is not None else "") + ".")
    body = (kpis + rating
            + f"<div class='pm-sec'><h2>Returns</h2><p class='muted'>As reported to APMI for {_mo(lastm)}: after fees, before tax; over a year, a year.</p>{ret_tbl}</div>"
            + f"<div class='pm-sec'><h2>What ₹50 lakh became</h2><p class='muted'>Invested at the end of {_mo(first)}, month-end values to {_mo(lastm)}, after fees.</p>{growth}</div>"
            + (f"<div class='pm-sec'><h2>Year by year</h2>{cal_tbl}</div>" if cal_tbl else "")
            + f"<div class='pm-sec'><h2>Every month</h2><p class='muted'>Monthly return (%)." + (" Green: ahead of Nifty 500 TRI that month; red: behind." if eq else "") + f"</p>{heat}</div>"
            + (f"<div class='pm-sec'><h2>Rolling 12 months</h2><p class='muted'>The return over the 12 months to each month-end.</p>{roll}</div>" if roll else "")
            + f"<div class='grid g2 pm-sec' style='align-items:start'><div><h2>Consistency</h2>{kv(cons)}</div><div><h2>Risk</h2>{kv(risk)}</div></div>"
            + flows
            + (f"<div class='pm-sec'><h2>Assets</h2><p class='muted'>Client money in the strategy at each month-end (₹ crore).</p>{aum_chart}</div>" if aum_chart else "")
            + f"<div class='pm-sec'><h2>Against its peers</h2>{pct_html}{peer_tbl}<p style='margin-top:10px'><a href='{gurl}'>All rated {g.lower()} strategies</a></p></div>"
            + oth
            + "<div class='pm-sec'><h2>What this page cannot show</h2><p class='muted'>Holdings, fees and the fee structure (fixed or profit-sharing) are in the "
              "portfolio manager's disclosure document and monthly factsheet, not in APMI's reports. Individual clients' returns differ from the strategy's with the "
              "timing of their money and their fee plan.</p></div>")
    faq = [(f"What return has {s['name']} given?", f"{_p(a['r1y'])} over 1 year and {_p(a['r3y'])} a year over 3 years to {_mo(lastm)}, after fees and before tax, as reported to APMI."),
           (f"How big is {s['name']}?", f"{_cr(s['aum'])} of client money at the end of {_mo(lastm)}."),
           (f"What was its worst fall?", f"{_p(m.get('max_dd'))} from a month-end peak to a month-end low between {_mo(first)} and {_mo(lastm)}.")]
    from build_pages import faq_html, faq_ld
    body += faq_html(B, faq)
    title = (f"{s['name']} PMS ({s['manager']}): returns, risk and rating | Aeterna Wealth" if s.get("dup_name")
             else f"{s['name']} PMS: returns, risk and rating | Aeterna Wealth")
    desc = (f"{s['name']} ({s['manager']}): {_p(a['r3y'])} a year over 3 years after fees, worst fall {_p(m.get('max_dd'))}, assets {_cr(s['aum'])}"
            + (f"; rated {tier} ({s['rank']} of {s['of']})" if tier else "") + f". Data to {_mo(lastm)}.")
    crumbs = [("PMS", "/pms/"), (s["manager"], url_m(s["mslug"])), (s["name"], path)]
    _wrap(B, path, title, desc, crumbs, s["name"], lede, body, (faq_ld(faq),))


# ------------------------------------------------------------------ manager page
def manager_page(B, D, mg, L):
    path = url_m(mg["slug"])
    rated = [s for s in L if s.get("rated")]
    rows = [[(f"<a href='{url_s(s)}'>{B.e(s['name'])}</a>" if s.get("rated") else B.e(s["name"]))
             + f"<div class='muted' style='font-size:12.5px'>{B.e(s['type'])} · {'discretionary' if s['service'] == 'D' else 'non-discretionary'}"
             + (f" · not rated: {B.e(s['why_unrated'].split(':')[0].lower())}" if not s.get("rated") and s.get("why_unrated") else "") + "</div>",
             B.tier_badge(s.get("tier")) if s.get("tier") else "–", _p(s["apmi"].get("r1y")), _p(s["apmi"].get("r3y")), _p(s["apmi"].get("r5y")), _cr(s["aum"])]
            for s in sorted(L, key=lambda s: -s["aum"])]
    tot = sum(s["aum"] for s in L)
    # firm-wide assets over time (strategies we show)
    hist = defaultdict(float)
    for s in L:
        for mo, v in s.get("aum_hist", {}).items():
            hist[mo] += v
    hm = sorted(hist)
    chart = _line_chart([("Assets in these strategies (₹ crore)", "var(--teal)", [hist[k] for k in hm])], hm, fmt=lambda v: f"{v:,.0f}") if len(hm) >= 6 else ""
    lede = (f"{B.e(mg['name'])} manages {_cr(mg['aum_all'])} across {mg['n_all']} PMS strategies reported to APMI for {_mo(D['as_of'])}. "
            f"{len(L)} of them hold ₹100 crore or more and are shown here; {len(rated)} have a long enough discretionary record to rate.")
    body = (f"<div class='pm-sec'><h2>Strategies</h2>{_table(['Strategy', 'Rating', '1 year', '3 years a year', '5 years a year', 'Assets'], rows)}</div>"
            + (f"<div class='pm-sec'><h2>Assets over time</h2><p class='muted'>Month-end client money in the strategies above.</p>{chart}</div>" if chart else ""))
    title = f"{mg['name']} PMS: every strategy's returns and rating | Aeterna Wealth"
    desc = f"{mg['name']}: {len(L)} PMS strategies over ₹100 crore, {_cr(tot)} in them; returns after fees, risk and ratings from APMI data to {_mo(D['as_of'])}."
    _wrap(B, path, title, desc, [("PMS", "/pms/"), (mg["name"], path)], f"{mg['name']}: PMS strategies", lede, body)


# ------------------------------------------------------------------ group and hub pages
def _rated_rows(B, L, eq=True):
    return [[f"<a href='{url_s(s)}'>{B.e(s['name'])}</a><div class='muted' style='font-size:12.5px'>{B.e(s['manager'])}</div>",
             B.tier_badge(s.get("tier")), str(s.get("rank")), _p(s["apmi"].get("r3y")),
             _p(s["m"].get("ex3y"), 1, True) if eq else _p(s["apmi"].get("r1y")),
             _p(None if s["m"].get("hit_12m") is None else s["m"]["hit_12m"] * 100, 0), _p(s["m"].get("max_dd")), _cr(s["aum"])]
            for s in sorted(L, key=lambda s: s.get("rank") or 9999)]


def group_page(B, D, g, L):
    path = f"/pms/ratings/{GROUP_SLUG[g]}/"
    eq = g == "Equity"
    cnt = {t: sum(s.get("tier") == t for s in L) for t in ("A+", "A", "B", "C")}
    lede = (f"All {len(L)} discretionary {g.lower()} PMS strategies with at least ₹100 crore and 3 years of reported returns, ranked on their record to {_mo(D['as_of'])}: "
            f"{cnt['A+']} Leading (A+), {cnt['A']} Strong (A), {cnt['B']} In line (B), {cnt['C']} Lagging (C).")
    head = ["Strategy", "Rating", "Rank", "3 years a year", "vs Nifty 500 TRI" if eq else "1 year", "12-month spells ahead", "Worst fall", "Assets"]
    body = f"<div class='pm-sec'>{_table(head, _rated_rows(B, L, eq))}</div>"
    title = f"{g} PMS ratings: {len(L)} strategies ranked on returns and risk ({_mo(D['as_of'])}) | Aeterna Wealth"
    desc = f"{len(L)} {g.lower()} PMS strategies ranked on 3-year return over the index, consistency and falls; data from APMI to {_mo(D['as_of'])}."
    _wrap(B, path, title, desc, [("PMS", "/pms/"), (f"{g} ratings", path)], f"{g} PMS strategies, rated", lede, body)


def hub_page(B, D, S, managers):
    path = "/pms/"
    rated = [s for s in S if s.get("rated")]
    eq = sorted([s for s in rated if s["group"] == "Equity"], key=lambda s: s["rank"])
    # the year in one view: medians
    med = lambda v: sorted(v)[len(v) // 2] if v else None
    r3 = med([s["apmi"]["r3y"] for s in eq])
    ix3 = eq[0]["m"].get("ix3y") if eq else None
    beat = sum((s["m"].get("ex3y") or 0) > 0 for s in eq)
    kp = [("Strategies APMI reports", f"{D['n_all']:,}"), ("Shown here (₹100 cr+)", f"{len(S)}"), ("Rated", f"{len(rated)}"),
          ("Typical equity PMS, 3 years", _p(r3) + " a year")]
    kpis = "<div class='pm-kpis'>" + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in kp) + "</div>"
    head = ["Strategy", "Rating", "Rank", "3 years a year", "vs Nifty 500 TRI", "12-month spells ahead", "Worst fall", "Assets"]
    top = _table(head, _rated_rows(B, eq[:25]))
    groups = "".join(f"<a class='btn' href='/pms/ratings/{GROUP_SLUG[g]}/'>{g} ({sum(s['group'] == g for s in rated)})</a>"
                     for g in ("Equity", "Debt", "Hybrid and multi-asset"))
    shown_m = [mg for mg in managers if mg["has_page"]]
    mlist = ("<div style='columns:3 220px;column-gap:28px;margin-top:12px;font-size:14.5px;line-height:1.9'>"
             + "".join(f"<div><a href='{url_m(mg['slug'])}'>{B.e(mg['name'])}</a></div>" for mg in shown_m) + "</div>")
    lede = (f"Every PMS strategy reports its returns to APMI each month. We take all {D['n_all']:,} of them, keep the {len(S)} with ₹100 crore or more, "
            f"and rate the {len(rated)} discretionary ones with 3 years of record: not on last year's return, but on how consistently and how safely "
            f"they beat the market over {len(eq[0]['months']) if eq else 0} months.")
    body = (kpis
            + f"<div class='pm-sec'><h2>What the record says</h2><p class='muted'>Of {len(eq)} rated equity strategies, {beat} beat Nifty 500 TRI over 3 years "
              f"(index: {_p(ix3)} a year). Even the strategies that beat it were behind the index in about half of all months: a PMS is judged over years, not quarters. "
              f"These are the strategies that grew past ₹100 crore; ones that shrank or closed are not in the count, so the industry as a whole did less well.</p></div>"
            + f"<div class='pm-sec'><h2>Equity strategies, top of the ranking</h2><p class='muted'>Ranked within the group on 3-year return over the index, "
              f"consistency (information ratio, 12-month spells ahead), protection in falling months and the worst fall.</p>{top}"
              f"<div class='row' style='gap:10px;flex-wrap:wrap;margin-top:14px'>{groups}</div></div>"
            + f"<div class='pm-sec'><h2>Portfolio managers</h2><p class='muted'>{len(shown_m)} managers with at least one strategy over ₹100 crore.</p>{mlist}</div>"
            + "<div class='pm-sec'><h2>Read more</h2><p><a href='/pms/how-pms-returns-are-measured/'>How PMS returns are measured and how we rate</a> · "
              "<a href='/aif/'>Alternative investment funds (AIFs)</a> · <a href='/mutual-funds/'>Mutual fund ratings</a></p></div>")
    title = f"PMS returns and ratings: {len(rated)} strategies ranked on their record ({_mo(D['as_of'])}) | Aeterna Wealth"
    desc = (f"PMS performance for {len(S)} strategies over ₹100 crore: returns after fees, worst falls, consistency against Nifty 500 TRI and ratings, "
            f"from APMI data to {_mo(D['as_of'])}.")
    _wrap(B, path, title, desc, [("PMS", "/pms/")], "PMS returns and ratings", lede, body)


def method_page(B, D):
    path = "/pms/how-pms-returns-are-measured/"
    body = f"""<div class='prose' style='max-width:780px'>
<h2>Where the numbers come from</h2><p>SEBI requires every portfolio manager to report each strategy ("investment approach") to APMI, the Association of Portfolio Managers in India, every month: client money at the month end and returns over 1, 3 and 6 months and 1 to 5 years and since launch. APMI publishes them. We read every month's report from April 2023, when APMI's reports became complete, to {_mo(D['as_of'])}.</p>
<h2>What the returns mean</h2><ul><li><b>Time-weighted (TWRR):</b> the return of the strategy itself, not affected by when clients added or took out money. Your own return differs with your timing.</li>
<li><b>After all fees and expenses</b>, including any profit share, and <b>before your tax</b>. In a PMS you own the shares, so you pay capital gains tax on every sale the manager makes.</li>
<li><b>Periods over a year are annualised</b> (a year).</li><li><b>Discretionary</b> strategies: the manager decides and trades for every client in the same model portfolio. In <b>non-discretionary</b> ones each client approves each trade, so the reported return depends on the clients' choices; we list them but do not rate them.</li></ul>
<h2>The yardstick</h2><p>Equity strategies are measured against <b>Nifty 500 TRI</b>, the total-return index of India's 500 largest listed companies (dividends reinvested), month-end to month-end, the same months as the strategy. It moves within a few tenths of a percent of BSE 500 TRI, the index APMI shows. Debt, hybrid and multi-asset strategies are compared with each other.</p>
<h2 id='rating'>How we rate</h2><p>Strategies are rated within their group (equity, debt, hybrid and multi-asset) if they are discretionary, hold ₹100 crore or more (a strategy stays until it is below ₹75 crore) and have at least 3 years of returns and 24 months of monthly record. For equity, each measure is turned into a percentile among the group and blended:</p>
<ul><li>3-year return over Nifty 500 TRI: 20</li><li>Information ratio (how steady the lead over the index is): 20</li><li>Share of 12-month spells ahead of the index: 15</li><li>Share of the index's falling months taken (lower is better): 15</li><li>Worst fall: 10</li><li>Worst 12 months against the index: 10</li><li>Share of months ahead of the index: 10</li></ul>
<p>Leading (A+) is the top 10% of the group with a score of 70 or more and a positive 3-year return over the index; Strong (A) the top 30% with 55 or more; Lagging (C) the bottom 30%; the rest In line (B). A strategy whose clients withdrew more than 30% of its money in the last 12 months is held at B. Strategies APMI files under equity that are not stock portfolios (arbitrage, unlisted shares, special situations) are not rated.</p>
<h2>What it cannot tell you</h2><p>These ratings describe a record of at most {len(D['bench_levels']) - 1} months: one long rise and one fall in Indian shares. They say nothing about fees you will pay, the portfolio's holdings, or how the manager will do next. Read the disclosure document, and judge a PMS over years.</p></div>"""
    _wrap(B, path, "How PMS returns are measured and how we rate PMS strategies | Aeterna Wealth",
          "What APMI's PMS returns mean (time-weighted, after fees, before tax), the yardstick (Nifty 500 TRI) and how Aeterna rates PMS strategies.",
          [("PMS", "/pms/"), ("How we measure", path)], "How PMS returns are measured", "What the numbers on our PMS pages mean, and how the ratings are made.", body)


def aif_page(B):
    path = "/aif/"
    body = """<div class='prose' style='max-width:780px'>
<h2>What an AIF is</h2><p>An alternative investment fund (AIF) is a privately pooled fund registered with SEBI under the AIF Regulations, 2012, for investors putting in at least ₹1 crore (less for accredited investors and employees of the manager). Unlike a mutual fund it can invest in unlisted companies, private credit, real estate and complex strategies, and most have a lock-in.</p>
<h2>The three categories</h2><ul><li><b>Category I:</b> funds SEBI wants to encourage: venture capital, angel, SME, social impact and infrastructure funds. Usually closed-ended, 5 to 10 years.</li>
<li><b>Category II:</b> everything that is neither I nor III, without leverage except to meet day-to-day needs: private equity, private credit and debt, real estate funds, funds of funds. Closed-ended, typically 3 to 8 years.</li>
<li><b>Category III:</b> funds that trade listed shares and derivatives and may use leverage: long-only equity, long-short and hedge strategies. Can be open- or closed-ended.</li></ul>
<h2>Why we do not rank AIFs</h2><p>No one publishes returns for individual AIF schemes. SEBI's benchmarking framework (CRISIL, NSE and others) gives each AIF its own report privately and publishes only category-level averages twice a year, for March and September. Private equity and credit funds are also valued only occasionally, and their returns depend on when each investment is sold. A ranking from public data would be guesswork, so we do not make one.</p>
<h2>What to ask before investing in an AIF</h2><ul><li>The scheme's returns since its first close, as an IRR, against its category benchmark from the benchmarking agency's report.</li><li>The fees: management fee, set-up costs, the hurdle rate and the manager's share of profits.</li><li>The lock-in and when the fund expects to return money; whether you can exit early.</li><li>How your returns are taxed: Category I and II pass income through to investors; Category III is taxed in the fund.</li></ul>
<p>For listed-equity strategies with monthly reported returns, see our <a href='/pms/'>PMS ratings</a>.</p></div>"""
    _wrap(B, path, "AIF categories explained: Category I, II and III alternative investment funds | Aeterna Wealth",
          "What alternative investment funds are, SEBI's three categories, why scheme-level AIF returns are not public, and what to ask before investing.",
          [("AIFs", path)], "Alternative investment funds (AIFs)", "What they are, how SEBI classifies them, and what you can and cannot find out before investing.", body)


def build(B, urls):
    p = B.S / "data" / "pms.json"
    if not p.exists():
        return
    D = json.loads(p.read_text(encoding="utf-8"))
    D["bench_levels"] = {}
    g = 100.0
    for mo in sorted(D["bench"]["NIFTY 500"]):
        D["bench_levels"].setdefault(mo, None)
    # index levels from monthly returns, for trailing index returns (starts at the month before the first return)
    keys = sorted(D["bench"]["NIFTY 500"])
    first = f"{int(keys[0][:4]) - (1 if keys[0][5:] == '01' else 0)}-{(int(keys[0][5:]) - 2) % 12 + 1:02d}"
    lv = {first: 100.0}
    for k in keys:
        g *= 1 + D["bench"]["NIFTY 500"][k] / 100
        lv[k] = g
    D["bench_levels"] = lv
    S = D["strategies"]
    from collections import Counter
    nc = Counter(s["name"].lower() for s in S if s.get("rated"))
    for s in S:
        s["dup_name"] = nc[s["name"].lower()] > 1
    by_m = defaultdict(list)
    for s in S:
        by_m[s["mslug"]].append(s)
    for mg in D["managers"]:
        mg["has_page"] = any(s.get("rated") for s in by_m[mg["slug"]]) or sum(s["aum"] for s in by_m[mg["slug"]]) >= 500
    for g_ in GROUP_SLUG:
        L = [s for s in S if s["group"] == g_ and s.get("rated")]
        if L:
            group_page(B, D, g_, L)
            urls.append((f"/pms/ratings/{GROUP_SLUG[g_]}/", "monthly", "0.7"))
    for s in S:
        if s.get("rated"):
            strategy_page(B, D, s, [x for x in S if x["group"] == s["group"] and x.get("rated")], by_m[s["mslug"]])
            urls.append((url_s(s), "monthly", "0.6"))
    for mg in D["managers"]:
        if mg["has_page"]:
            manager_page(B, D, mg, by_m[mg["slug"]])
            urls.append((url_m(mg["slug"]), "monthly", "0.5"))
    hub_page(B, D, S, D["managers"])
    method_page(B, D)
    aif_page(B)
    urls += [("/pms/", "monthly", "0.8"), ("/pms/how-pms-returns-are-measured/", "monthly", "0.5"), ("/aif/", "monthly", "0.5")]
