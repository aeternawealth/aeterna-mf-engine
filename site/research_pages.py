"""Research hub (/insights/) and the data stories behind it. Standard library only.

Data stories, recomputed with every build from the site's own data:
  /insights/category-returns-by-year/   calendar-year return of the median fund in each category (the "periodic table")
  /insights/category-falls/             the deepest fall of each category's median fund since 2008, and how long it took to recover
  /insights/five-year-odds/             every 5-year holding period since 2008: how often each category's median fund beat 7% a year
  /insights/fund-choice-gap/            within a category, how far apart the top and bottom funds ended over 3 years
The hub lists these with the daily insights (build_pages.insight_pages -> B.INSIGHT_CARDS), the market-data pages, the
PMS research, the method pages, the investor guides and the tax guides: one place for everything we publish.
Survivorship: the series hold funds that exist today, so medians flatter the past a little; each page says so.
"""
import json
import re
import statistics
from pathlib import Path

import illustrations as ILL

CATS = [  # series file, display name, category page, family
    ("large-cap", "Large Cap", "large-cap", "Equity"), ("large-mid-cap", "Large & Mid Cap", "large-and-mid-cap", "Equity"),
    ("flexi-cap", "Flexi Cap", "flexi-cap", "Equity"), ("multi-cap", "Multi Cap", "multi-cap", "Equity"),
    ("focused", "Focused", "focused", "Equity"), ("value-contra", "Value / Contra", "value-contra", "Equity"),
    ("dividend-yield", "Dividend Yield", "dividend-yield", "Equity"), ("elss", "ELSS", "elss", "Equity"),
    ("mid-cap", "Mid Cap", "mid-cap", "Equity"), ("small-cap", "Small Cap", "small-cap", "Equity"),
    ("aggressive-hybrid", "Aggressive Hybrid", "aggressive-hybrid", "Hybrid"), ("balanced-advantage", "Balanced Advantage", "balanced-advantage", "Hybrid"),
    ("multi-asset-allocation", "Multi Asset", "multi-asset-allocation", "Hybrid"), ("equity-savings", "Equity Savings", "equity-savings", "Hybrid"),
    ("corporate-bond", "Corporate Bond", "corporate-bond", "Debt"), ("short-term", "Short Duration", "short-term", "Debt"),
    ("gilt", "Gilt", "gilt", "Debt"), ("liquid", "Liquid", "liquid", "Debt")]
FAM_COL = {"Equity": "var(--teal)", "Hybrid": "var(--brass)", "Debt": "var(--t-a)"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _mo(m):
    return f"{MON[int(m[5:7]) - 1]} {m[:4]}"


def median_index(S, cat):
    """Month-end index of the category's median fund: each month, the median of the funds' monthly returns, chained."""
    p = S / "data" / "series" / f"{cat}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    months, navs = d["months"], list(d["nav"].values())
    lv, g, out = None, 100.0, {}
    for i in range(1, len(months)):
        rs = []
        for v in navs:
            a, b = v[i - 1] if i - 1 < len(v) else None, v[i] if i < len(v) else None
            if a and b and a > 0:
                r = b / a - 1
                if -0.6 < r < 0.6:
                    rs.append(r)
        if len(rs) >= 3:
            if lv is None:
                out[months[i - 1]] = 100.0
                lv = 100.0
            g = (out[max(out)] if out else 100.0) * (1 + statistics.median(rs))
            out[months[i]] = g
    return out or None


# ------------------------------------------------------------------ charts (plain SVG)
def _hbars(items, fmt, W=760, colour=None, row=32, label=""):
    if not items:
        return ""
    L, R = 190, 120
    H = row * len(items) + 8
    lo = min(0, min(v for _, v, _ in items))
    hi = max(0, max(v for _, v, _ in items)) or 1
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    g = [f"<line x1='{X(0):.1f}' x2='{X(0):.1f}' y1='0' y2='{H}' stroke='var(--ink-3)' stroke-width='1'/>"] if lo < 0 else []
    for i, (lab, v, col) in enumerate(items):
        y = 4 + i * row
        x0, x1 = sorted((X(0), X(v)))
        g.append(f"<text x='{L - 10}' y='{y + row / 2 + 4:.1f}' text-anchor='end' font-size='13' fill='var(--ink-2)'>{lab}</text>"
                 f"<rect x='{x0:.1f}' y='{y + 7}' width='{max(2, x1 - x0):.1f}' height='{row - 14}' rx='3' fill='{colour or col}'/>"
                 f"<text x='{(x1 + 8) if v >= 0 else (x0 - 8):.1f}' y='{y + row / 2 + 4:.1f}' text-anchor='{'start' if v >= 0 else 'end'}' font-size='12.5' font-weight='600' fill='var(--ink)'>{fmt(v)}</text>")
    return f"<div class='rs-chart'><svg viewBox='0 0 {W} {H}' role='img' aria-label='{label}'>{''.join(g)}</svg></div>"


def _ranges(items, W=760, row=34, label=""):
    """items: [(label, lo, q1, med, q3, hi)] min-max whisker with an inter-quartile box and the median."""
    L, R = 190, 30
    H = row * len(items) + 34
    lo = min(x[1] for x in items)
    hi = max(x[5] for x in items)
    pad = (hi - lo) * .04
    lo, hi = lo - pad, hi + pad
    X = lambda v: L + (W - L - R) * (v - lo) / (hi - lo)
    g = []
    import math
    step = 5 if hi - lo > 25 else 2
    t = math.ceil(lo / step) * step
    while t <= hi:
        g.append(f"<line x1='{X(t):.1f}' x2='{X(t):.1f}' y1='0' y2='{H - 26}' stroke='var(--rule)'/><text x='{X(t):.1f}' y='{H - 8}' text-anchor='middle' font-size='11' fill='var(--ink-3)'>{t:.0f}%</text>")
        t += step
    for i, (lab, a, q1, md, q3, b) in enumerate(items):
        y = 4 + i * row + row / 2
        g.append(f"<text x='{L - 10}' y='{y + 4:.1f}' text-anchor='end' font-size='13' fill='var(--ink-2)'>{lab}</text>"
                 f"<line x1='{X(a):.1f}' x2='{X(b):.1f}' y1='{y:.1f}' y2='{y:.1f}' stroke='var(--ink-3)' stroke-width='1.5'/>"
                 f"<rect x='{X(q1):.1f}' y='{y - 8:.1f}' width='{max(2, X(q3) - X(q1)):.1f}' height='16' rx='3' fill='var(--teal)' opacity='.85'/>"
                 f"<line x1='{X(md):.1f}' x2='{X(md):.1f}' y1='{y - 10:.1f}' y2='{y + 10:.1f}' stroke='var(--surface)' stroke-width='2.5'/>"
                 f"<circle cx='{X(a):.1f}' cy='{y:.1f}' r='3' fill='var(--bad)'/><circle cx='{X(b):.1f}' cy='{y:.1f}' r='3' fill='var(--good)'/>"
                 f"<title>{lab}: weakest {a:.1f}%, middle half {q1:.1f}% to {q3:.1f}%, strongest {b:.1f}% a year</title>")
    return f"<div class='rs-chart'><svg viewBox='0 0 {W} {H}' role='img' aria-label='{label}'>{''.join(g)}</svg></div>"


CSS = """<style>
.rs{--gap:44px}.rs-eyebrow{font:600 12px/1 var(--f-body);letter-spacing:.12em;text-transform:uppercase;color:var(--teal)}
.rs h1{font-size:clamp(30px,4.4vw,48px);line-height:1.08;margin-top:10px}.rs .lede{margin-top:12px}
.rs-hero{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:32px;align-items:start}@media (max-width:900px){.rs-hero{grid-template-columns:1fr}}
.rs-sec{margin-top:var(--gap)}.rs-sec>h2{font-size:clamp(24px,2.6vw,30px)}.rs-sec>p.muted{margin-top:6px;font-size:15px}
.rs-chart{margin-top:14px;border:1px solid var(--rule);border-radius:var(--r);background:var(--surface);padding:14px 12px 10px;overflow-x:auto}
.rs-chart svg{width:100%;height:auto;display:block;min-width:560px}
.rs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px;margin-top:16px}
.rs-card{display:flex;flex-direction:column;gap:8px;background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:18px 20px;text-decoration:none;color:inherit;min-width:0}
a.rs-card:hover{border-color:var(--teal)}.rs-card b.t{font:500 19px/1.3 var(--f-display)}.rs-card .muted{font-size:14px}
.rs-card .fig{font:500 30px/1 var(--f-display);color:var(--teal)}.rs-card .rs-tag{font:600 11.5px var(--f-body);letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.rs-feat{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:22px}.rs-feat .rs-card{border-top:4px solid var(--teal)}.rs-feat .fig{font-size:40px}
.rs-heat{border-collapse:collapse;font:500 12.5px var(--f-mono);width:100%;min-width:760px}.rs-heat td,.rs-heat th{border:1px solid var(--rule);padding:7px 5px;text-align:center}
.rs-heat th{font:600 12px var(--f-body);color:var(--ink-2);background:var(--surface)}.rs-heat td.l{text-align:left;font:600 13px var(--f-body);white-space:nowrap}
.rs-list{columns:2 300px;column-gap:28px;margin-top:12px;font-size:15px;line-height:2}.rs-list a{text-decoration:none}.rs-list a:hover{text-decoration:underline}
.rs-note{font-size:13px;color:var(--ink-3);margin-top:20px;line-height:1.65}
.rs-kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;margin-top:24px}
.rs-kpis div{background:var(--surface);padding:16px 18px}.rs-kpis span{display:block;color:var(--ink-2);font-size:13px}.rs-kpis b{display:block;font:500 24px/1.25 var(--f-mono);margin-top:4px}
@media (max-width:900px){.rs-feat{grid-template-columns:1fr}.rs-kpis{grid-template-columns:1fr}}
</style>"""


def _page(B, path, title, desc, eyebrow, h1, lede, body, as_of, crumbs, ld=()):
    nav = " › ".join(f"<a href='{u}'>{B.e(t)}</a>" if u != path else B.e(t) for t, u in crumbs)
    html = (CSS + f"<section class='band rs' style='padding-top:26px'><div class='wrap'><nav aria-label='Breadcrumb' class='muted' style='font-size:13.5px'>{nav}</nav>"
            f"<div class='rs-eyebrow' style='margin-top:16px'>{eyebrow}</div><h1>{B.e(h1)}</h1><p class='lede'>{lede}</p>"
            f"<p class='muted' style='font-size:13.5px;margin-top:8px'>Aeterna Wealth research · worked out from AMFI NAVs and our fund data · updated {B.dmy(as_of)}</p>"
            f"{body}</div></section>")
    art = {"@context": "https://schema.org", "@type": "Article", "headline": h1[:110], "description": desc[:300], "datePublished": "2026-11-27",
           "dateModified": as_of, "inLanguage": "en-IN", "author": {"@id": B.SITE + "/#org"}, "publisher": {"@id": B.SITE + "/#org"},
           "image": B.SITE + "/og.png", "mainEntityOfPage": B.SITE + path}
    B.write(path, B.page(title, desc, path, html, (art, B.crumbs(crumbs)) + tuple(ld)))


SURV = ("Each category is followed through its median fund: every month, the middle return among the category's funds, chained. The series cover "
        "funds that exist today, so funds that closed or merged are missing and the past looks slightly better than it was. Regular and Direct "
        "plans together. Describes what has happened, not what will; not a recommendation to buy or sell any fund.")


def stories(B, urls, as_of):
    S = B.S
    idx = {}
    for key, name, slug, fam in CATS:
        x = median_index(S, key)
        if x and len(x) >= 60:
            idx[key] = x
    out = []
    if not idx:
        return out
    last = min(max(v) for v in idx.values())
    # ---------- 1. calendar years
    years = sorted({m[:4] for v in idx.values() for m in v if m <= last})
    years = [y for y in years if int(y) >= 2009]
    tab = {}
    for key, name, slug, fam in CATS:
        if key not in idx:
            continue
        v = idx[key]
        row = {}
        for y in years:
            end = max((m for m in v if m.startswith(y) and m <= last), default=None)
            start = f"{int(y) - 1}-12"
            if end and start in v:
                row[y] = (v[end] / v[start] - 1) * 100
        tab[key] = row
    ytd = not last.endswith("-12")
    head = "".join(f"<th>{y}{'*' if ytd and y == years[-1] else ''}</th>" for y in years)
    rows = []
    best = {y: max((tab[k][y], k) for k in tab if y in tab[k] and dict((c[0], c[3]) for c in CATS)[k] != "Debt") for y in years if any(y in tab[k] for k in tab)}
    for key, name, slug, fam in CATS:
        if key not in tab:
            continue
        cells = []
        for y in years:
            r = tab[key].get(y)
            if r is None:
                cells.append("<td></td>")
                continue
            col = f"color-mix(in srgb,var(--{'good' if r >= 0 else 'bad'}) {min(60, 6 + abs(r) * 1.4):.0f}%,var(--surface))"
            star = " style='outline:2px solid var(--ink);outline-offset:-2px;background:%s'" % col if best.get(y, (0, ""))[1] == key else f" style='background:{col}'"
            cells.append(f"<td{star} title='{name} {y}: {r:.1f}%'>{r:.0f}</td>")
        rows.append(f"<tr><td class='l'><a href='/mutual-funds/{slug}/'>{B.e(name)}</a></td>{''.join(cells)}</tr>")
    heat = f"<div class='tablewrap' style='margin-top:14px'><table class='rs-heat'><thead><tr><th class='l'>Category (median fund)</th>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    wins = {}
    for y, (r, k) in best.items():
        wins[k] = wins.get(k, 0) + 1
    topk = max(wins, key=wins.get)
    nm = dict((c[0], c[1]) for c in CATS)
    spread = [max(tab[k][y] for k in tab if y in tab[k]) - min(tab[k][y] for k in tab if y in tab[k]) for y in years if sum(y in tab[k] for k in tab) > 5]
    body = (f"<div class='rs-kpis'><div><span>Years covered</span><b>{years[0]}–{years[-1]}</b></div><div><span>Most often the top equity category</span><b>{nm[topk]}</b>"
            f"<span>{wins[topk]} of {len(years)} years</span></div><div><span>Typical gap, top to bottom category</span><b>{statistics.median(spread):.0f} points</b><span>in a year</span></div></div>"
            "<div class='rs-sec'><h2>Every category, every year</h2><p class='muted'>Return of the median fund in each calendar year (%). Green gained, red lost; deeper colour, bigger move. "
            f"Outlined: the top equity or hybrid category that year.{' * ' + years[-1] + ' to ' + _mo(last) + '.' if ytd else ''}</p>{heat}</div>"
            "<div class='rs-sec'><h2>What it shows</h2><ul style='margin-top:10px;line-height:1.7'>"
            f"<li>Leadership rotates. No category stayed on top for long; {nm[topk]} led most often, in {wins[topk]} of {len(years)} years.</li>"
            "<li>The categories with the best years also had the worst ones: small and mid caps sit at both ends of most columns.</li>"
            "<li>Hybrid and debt categories rarely top the table but rarely lose much: they are there to cushion, not to win.</li></ul>"
            "<p style='margin-top:14px'><a class='btn' href='/mutual-funds/'>See every category, rated</a> <a class='btn' href='/plan/'>Plan your mix</a></p></div>"
            f"<p class='rs-note'>{SURV}</p>")
    path = "/insights/category-returns-by-year/"
    _page(B, path, f"Mutual fund category returns by year, {years[0]}–{years[-1]} | Aeterna Wealth insights",
          f"Calendar-year return of the median fund in every major mutual fund category from {years[0]} to {years[-1]}: large, mid, small, flexi cap, hybrid and debt, side by side.",
          "Data story", f"Mutual fund categories, year by year ({years[0]}–{years[-1]})",
          "Which kind of fund did best each year, and how often the leader changed: the median fund in every major category, every calendar year.", body, as_of,
          [("Insights", "/insights/"), ("Category returns by year", path)])
    urls.append((path, "monthly", "0.7"))
    out.append({"path": path, "fig": f"{len(years)} years", "title": "Mutual fund categories, year by year", "tag": "Categories",
                "text": f"The median fund in {len(tab)} categories, every calendar year since {years[0]}. Leadership rotates: {nm[topk]} led most often, in {wins[topk]} of {len(years)} years."})
    # ---------- 2. falls and recoveries
    falls = []
    for key, name, slug, fam in CATS:
        if key not in idx or fam == "Debt" and key == "liquid":
            continue
        v = idx[key]
        ks = sorted(m for m in v if m <= last)
        pk, pkm, worst = v[ks[0]], ks[0], (0, None, None)
        for m in ks:
            if v[m] > pk:
                pk, pkm = v[m], m
            dd = v[m] / pk - 1
            if dd < worst[0]:
                worst = (dd, pkm, m)
        rec = None
        if worst[1]:
            top = v[worst[1]]
            after = [m for m in ks if m > worst[2] and v[m] >= top]
            if after:
                a, b = after[0], worst[2]
                rec = (int(a[:4]) - int(b[:4])) * 12 + int(a[5:]) - int(b[5:])
        # the 2020 fall
        c20 = [m for m in ks if "2020-01" <= m <= "2020-12"]
        f20 = None
        if c20 and "2019-12" in v:
            f20 = (min(v[m] for m in c20) / max(v[m] for m in ks if "2019-06" <= m <= "2020-02") - 1) * 100
        falls.append((key, name, slug, fam, worst[0] * 100, worst[1], worst[2], rec, f20))
    falls.sort(key=lambda x: x[4])
    chart = _hbars([(B.e(f[1]), f[4], FAM_COL[f[3]]) for f in falls], lambda v: f"{v:.0f}%".replace("-", "−"), label="Deepest fall of each category's median fund")
    M = lambda v: f"{v:.0f}%".replace("-", "−")
    rows = "".join(f"<tr><td class='l'><a href='/mutual-funds/{f[2]}/'>{B.e(f[1])}</a></td><td class='num'>{M(f[4])}</td><td class='num'>{_mo(f[5])} to {_mo(f[6])}</td>"
                   f"<td class='num'>{f'{f[7]} months' if f[7] is not None else 'not yet'}</td><td class='num'>{'–' if f[8] is None else M(f[8])}</td></tr>"
                   for f in falls)
    tbl = ("<div class='tablewrap' style='margin-top:14px'><table><thead><tr><th class='l'>Category (median fund)</th><th>Deepest fall</th><th>Peak to bottom</th>"
           f"<th>Back to the peak</th><th>Fall in 2020</th></tr></thead><tbody>{rows}</tbody></table></div>")
    eqf = [f for f in falls if f[3] == "Equity"]
    body = (f"<div class='rs-kpis'><div><span>Deepest equity category fall</span><b>{eqf[0][4]:.0f}%</b><span>{eqf[0][1]}, {_mo(eqf[0][5])} to {_mo(eqf[0][6])}</span></div>"
            f"<div><span>Shallowest equity category fall</span><b>{eqf[-1][4]:.0f}%</b><span>{eqf[-1][1]}</span></div>"
            f"<div><span>Longest wait to recover</span><b>{max((f[7] or 0) for f in eqf)} months</b><span>month-end to month-end</span></div></div>".replace("-", "−")
            + f"<div class='rs-sec'><h2>How far each category fell</h2><p class='muted'>The deepest fall of each category's median fund since 2008, from a month-end high to a month-end low. "
              f"Green: equity; brown: hybrid; teal: debt.</p>{chart}</div>"
            + f"<div class='rs-sec'><h2>When, and how long it took to come back</h2>{tbl}</div>"
            + "<div class='rs-sec'><h2>What it shows</h2><ul style='margin-top:10px;line-height:1.7'><li>Every equity category has halved, or come close, at least once. That is the price of its long-run return, and the reason equity money needs years.</li>"
              "<li>Every one of them came back. The wait was measured in years for the deepest falls, months for the 2020 one.</li>"
              "<li>Hybrid funds fell about half as far; debt funds barely moved. How much of each you hold decides how deep your own fall is.</li></ul>"
              "<p style='margin-top:14px'><a class='btn' href='/learn/maximum-drawdown/'>What drawdown means</a> <a class='btn' href='/plan/'>Plan your mix</a></p></div>"
            + f"<p class='rs-note'>{SURV}</p>")
    path = "/insights/category-falls/"
    _page(B, path, "How far each mutual fund category fell, and how long it took to recover | Aeterna Wealth insights",
          "The deepest fall of the median fund in every major mutual fund category since 2008, when it happened, how long it took to get back, and the 2020 fall.",
          "Data story", "How far each category fell, and how long it took to recover",
          "Every major category's worst fall since 2008, month-end to month-end, and the months it took to get back to the peak.", body, as_of,
          [("Insights", "/insights/"), ("Category falls", path)])
    urls.append((path, "monthly", "0.7"))
    out.append({"path": path, "fig": f"{eqf[0][4]:.0f}%".replace("-", "−"), "title": "How far each category fell, and how long it took to recover", "tag": "Risk",
                "text": f"The deepest fall of each category's median fund since 2008. {eqf[0][1]} fell {abs(eqf[0][4]):.0f}%; every equity category came back."})
    # ---------- 3. five-year odds
    odds = []
    for key, name, slug, fam in CATS:
        if key not in idx:
            continue
        v = idx[key]
        ks = sorted(m for m in v if m <= last)
        rr = []
        for i in range(60, len(ks)):
            rr.append(((v[ks[i]] / v[ks[i - 60]]) ** (1 / 5) - 1) * 100)
        if len(rr) < 24:
            continue
        rs = sorted(rr)
        q = lambda p: rs[min(len(rs) - 1, int(p * len(rs)))]
        odds.append((key, name, slug, fam, sum(x > 7 for x in rr) / len(rr) * 100, rs[0], q(.25), statistics.median(rr), q(.75), rs[-1], len(rr), sum(x < 0 for x in rr)))
    odds.sort(key=lambda x: -x[7])
    chart = _hbars([(B.e(o[1]), o[4], FAM_COL[o[3]]) for o in odds], lambda v: f"{v:.0f}%", label="Share of 5-year periods above 7% a year")
    rng = _ranges([(B.e(o[1]), o[5], o[6], o[7], o[8], o[9]) for o in odds], label="Range of 5-year returns")
    eqo = [o for o in odds if o[3] == "Equity"]
    neg = sum(o[11] for o in eqo)
    body = (f"<div class='rs-kpis'><div><span>Equity categories: 5-year periods above 7% a year</span><b>{statistics.median([o[4] for o in eqo]):.0f}%</b><span>median across categories</span></div>"
            f"<div><span>Equity 5-year periods that lost money</span><b>{neg} of {sum(o[10] for o in eqo)}</b><span>all categories together</span></div>"
            f"<div><span>Periods tested per category</span><b>up to {max(o[10] for o in odds)}</b><span>every month-end start since 2008</span></div></div>"
            + f"<div class='rs-sec'><h2>How often 5 years beat 7% a year</h2><p class='muted'>Every 5-year holding period that started at a month-end since 2008: the share that earned more than 7% a year "
              f"(about what a bank fixed deposit paid before tax). Green: equity; brown: hybrid; teal: debt.</p>{chart}</div>"
            + f"<div class='rs-sec'><h2>The whole range</h2><p class='muted'>Return a year over each 5-year period. The line runs from the weakest period (red dot) to the strongest (green); "
              f"the box holds the middle half; the white mark is the median.</p>{rng}</div>"
            + "<div class='rs-sec'><h2>What it shows</h2><ul style='margin-top:10px;line-height:1.7'><li>Over five years, equity categories beat 7% a year most of the time, but not always: the weak periods started near market peaks.</li>"
              "<li>The spread is wide. The same category could earn single digits or more than 20% a year depending on the start date; time in the market narrows it, it does not remove it.</li>"
              "<li>Debt funds cluster tightly around their yields: little upside, little doubt.</li></ul>"
              "<p style='margin-top:14px'><a class='btn' href='/learn/rolling-returns-mutual-funds/'>What rolling returns are</a> <a class='btn' href='/calculators/sip/'>SIP calculator</a></p></div>"
            + f"<p class='rs-note'>{SURV} 7% a year is a round reference figure, not a promise from any product.</p>")
    path = "/insights/five-year-odds/"
    _page(B, path, "Held for 5 years: how often each mutual fund category beat 7% a year | Aeterna Wealth insights",
          "Every 5-year holding period since 2008 for the median fund in each mutual fund category: how often it beat 7% a year, the weakest, the strongest and the middle.",
          "Data story", "Held for 5 years: how often each category beat 7% a year",
          "Every 5-year holding period since 2008, category by category: the odds of beating a fixed-deposit-like 7% a year, and the full range of outcomes.", body, as_of,
          [("Insights", "/insights/"), ("Five-year odds", path)])
    urls.append((path, "monthly", "0.7"))
    out.append({"path": path, "fig": f"{statistics.median([o[4] for o in eqo]):.0f}%", "title": "Held for 5 years: how often each category beat 7% a year", "tag": "Patience",
                "text": "Every 5-year holding period since 2008: how often each category's median fund beat 7% a year, and the weakest and strongest periods."})
    # ---------- 4. fund choice gap
    fp = S / "data" / "funds.json"
    if fp.exists():
        funds = json.loads(fp.read_text(encoding="utf-8"))
        gap = []
        for key, name, slug, fam in CATS:
            catname = {"large-mid-cap": "Large & Mid Cap", "value-contra": "Value / Contra", "multi-asset-allocation": "Multi Asset Allocation",
                       "short-term": "Short Term"}.get(key, name)
            L = sorted(f["ret_3Y"] * 100 for f in funds if f.get("category") == catname and f.get("plan_type") == "Regular" and isinstance(f.get("ret_3Y"), (int, float)))
            if len(L) < 8:
                continue
            q = lambda p: L[min(len(L) - 1, int(p * len(L)))]
            lakh = lambda r: 10 * (1 + r / 100) ** 3
            gap.append((key, name, slug, fam, L[0], q(.25), statistics.median(L), q(.75), L[-1], len(L), lakh(q(.75)) - lakh(q(.25)), lakh(L[-1]) - lakh(L[0])))
        if gap:
            gap.sort(key=lambda x: -x[10])
            rng = _ranges([(B.e(g[1]), g[4], g[5], g[6], g[7], g[8]) for g in gap], label="Range of 3-year returns within each category")
            bars = _hbars([(B.e(g[1]), g[10], FAM_COL[g[3]]) for g in gap], lambda v: f"₹{v:.1f} lakh", label="Top-quartile minus bottom-quartile fund on ₹10 lakh")
            g0 = gap[0]
            body = (f"<div class='rs-kpis'><div><span>Largest gap, top to bottom quarter</span><b>₹{g0[10]:.1f} lakh</b><span>{g0[1]}, on ₹10 lakh over 3 years</span></div>"
                    f"<div><span>Best vs worst fund, same category</span><b>₹{g0[11]:.1f} lakh</b><span>{g0[1]}</span></div>"
                    f"<div><span>Categories compared</span><b>{len(gap)}</b><span>Regular plans, 3-year returns</span></div></div>"
                    + f"<div class='rs-sec'><h2>Every fund's 3-year return, by category</h2><p class='muted'>3-year return a year of every Regular plan in each category. The line runs from the weakest fund (red) "
                      f"to the strongest (green); the box holds the middle half; the white mark is the median.</p>{rng}</div>"
                    + f"<div class='rs-sec'><h2>What the gap is worth</h2><p class='muted'>₹10 lakh invested 3 years ago: a fund at the top of the second quarter against one at the bottom of the third.</p>{bars}</div>"
                    + "<div class='rs-sec'><h2>What it shows</h2><ul style='margin-top:10px;line-height:1.7'><li>Picking the category is half the decision. Inside one category, under the same SEBI rules and the same market, outcomes differ by several points a year.</li>"
                      f"<li>The gap is not only in the riskier categories: this year it was widest in {B.e(g0[1].lower())} funds, where managers have the most freedom to differ.</li>"
                      "<li>That is why our ratings compare each fund with its own category and index, and why a fund is judged on how consistently it was ahead, not on one good year.</li></ul>"
                      "<p style='margin-top:14px'><a class='btn' href='/mutual-funds/'>Funds rated within their category</a> <a class='btn' href='/invest/portfolio-review/'>Free portfolio review</a></p></div>"
                    + "<p class='rs-note'>Regular plans with a 3-year record, to the latest NAV; quartiles of the category's plans. Returns are after expenses. "
                      "Describes what has happened, not what will; not a recommendation to buy or sell any fund.</p>")
            path = "/insights/fund-choice-gap/"
            _page(B, path, "Same category, different results: the gap between mutual funds over 3 years | Aeterna Wealth insights",
                  "How far apart the strongest and weakest funds in each mutual fund category ended over 3 years, and what the gap was worth on ₹10 lakh.",
                  "Data story", "Same category, very different results",
                  "Inside one category, under the same rules and in the same market, how far apart the funds ended over three years, and what that gap was worth.", body, as_of,
                  [("Insights", "/insights/"), ("Fund choice gap", path)])
            urls.append((path, "monthly", "0.7"))
            out.append({"path": path, "fig": f"₹{g0[10]:.1f} lakh", "title": "Same category, very different results", "tag": "Fund choice",
                        "text": f"On ₹10 lakh over 3 years, the gap between a top-quarter and a bottom-quarter {g0[1].lower()} fund. Choosing the fund matters as much as the category."})
    return out


def _titles(DIST, sub):
    """(url, title) of every page written under /<sub>/"""
    out = []
    base = DIST / sub
    if not base.exists():
        return out
    for p in sorted(base.glob("*/index.html")):
        h = p.read_text(encoding="utf-8")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", h, re.S)
        if m:
            import html as _h
            out.append((f"/{sub}/{p.parent.name}/", _h.unescape(re.sub(r"<[^>]+>", "", m.group(1)).strip())))
    return out


def hub(B, urls, as_of, new):
    e = B.e
    cards = getattr(B, "INSIGHT_CARDS", [])
    feat = new[:3]
    TI = {"Categories": "calendar", "Risk": "fall", "Patience": "growth", "Fund choice": "dots", "Updated every weekday": "bars"}
    fc = "".join(f"<a class='rs-card' href='{c['path']}'>{ILL.icon(TI.get(c['tag'], 'lens'), 48)}<span class='rs-tag'>{e(c['tag'])}</span><span class='fig'>{e(c['fig'])}</span><b class='t'>{e(c['title'])}</b>"
                 f"<span class='muted'>{e(c['text'])}</span><span style='margin-top:auto;font-weight:600;font-size:14px;color:var(--teal)'>Read →</span></a>" for c in feat)
    rest = new[3:] + [{"path": p, "fig": f, "title": t, "text": x[:170].rsplit(" ", 1)[0] + "…", "tag": "Updated every weekday"} for p, f, t, x in cards]
    rc = "".join(f"<a class='rs-card' href='{c['path']}'>{ILL.icon(TI.get(c['tag'], 'lens'), 40)}<span class='rs-tag'>{e(c['tag'])}</span><span class='fig'>{e(c['fig'])}</span><b class='t'>{e(c['title'])}</b>"
                 f"<span class='muted'>{e(c['text'])}</span></a>" for c in rest)
    mk = [("/mutual-funds/money-flows/", "Where the money is going", "Net flows into and out of every category, fund and fund house, quarter by quarter."),
          ("/mutual-funds/what-funds-bought-sold/", "What fund managers bought and sold", "This month's biggest buys, sells, new bets and exits across every equity fund."),
          ("/mutual-funds/crowded-stocks/", "Crowded stocks", "The stocks mutual funds own most of, and the ones they are piling into together."),
          ("/mutual-funds/holding/", "Funds holding a stock", "Which funds own a stock, how much, and who bought or sold it last month."),
          ("/mutual-funds/amc/", "Fund houses compared", "Every fund house's funds, ratings and how closely its funds move together."),
          ("/ratings-update/", "This month's rating changes", "Which funds moved up or down a tier this month, and why.")]
    MI = ["coins", "bars", "people", "lens", "layers", "calendar"]
    mc = "".join(f"<a class='rs-card' href='{u}'>{ILL.icon(MI[k % 6], 40)}<b class='t'>{e(t)}</b><span class='muted'>{e(d)}</span></a>" for k, (u, t, d) in enumerate(mk))
    pm = [("/pms/", "PMS returns, risk and ratings", "Every PMS strategy over ₹100 crore, measured against the right yardstick."),
          ("/pms/ratings/equity/", "Equity PMS ratings", "Large and multi cap, and mid and small cap strategies, ranked within their style."),
          ("/pms/how-pms-returns-are-measured/", "How PMS returns are measured", "TWRR, after fees, three yardsticks, the evidence and the limits."),
          ("/aif/", "AIFs explained", "Category I, II and III; how they compare with PMS and mutual funds.")]
    PI = ["dots", "growth", "scale", "layers"]
    pc = "".join(f"<a class='rs-card' href='{u}'>{ILL.icon(PI[k % 4], 40)}<b class='t'>{e(t)}</b><span class='muted'>{e(d)}</span></a>" for k, (u, t, d) in enumerate(pm))
    guides = _titles(B.DIST, "learn")
    gl = "".join(f"<div><a href='{u}'>{e(t)}</a></div>" for u, t in guides)
    tax = [("/income-tax/", "Income tax hub"), ("/income-tax/calculator/", "Income tax calculator"), ("/income-tax/slabs-fy-2026-27/", "Income tax slabs FY 2026-27"),
           ("/income-tax/deductions/", "Deductions: 80C, 80D, HRA, NPS"), ("/income-tax/advance-tax-calculator/", "Advance tax calculator"),
           ("/calculators/capital-gains-tax/", "Capital gains tax on mutual funds")]
    tl = "".join(f"<div><a href='{u}'>{e(t)}</a></div>" for u, t in tax if (B.DIST / u.strip("/") / "index.html").exists())
    nav = "".join(f"<a class='pm-chip' href='#{i}'>{t}</a>" for i, t in [("stories", "Data stories"), ("market", "Market data"), ("pms", "PMS research"), ("method", "Method"), ("guides", "Guides"), ("tax", "Tax")])
    body = (f"<div class='pm-chips' style='display:flex;flex-wrap:wrap;gap:8px;margin-top:16px'>{nav}</div>"
            f"<div class='rs-sec' id='stories' style='margin-top:30px'><h2>Featured</h2><div class='rs-feat'>{fc}</div></div>"
            f"<div class='rs-sec'><h2>More data stories</h2><p class='muted'>Worked out from our own data; the daily ones are recomputed every weekday.</p><div class='rs-grid'>{rc}</div></div>"
            f"<div class='rs-sec' id='market'><h2>Market data, every month</h2><p class='muted'>Built from every fund's monthly portfolio and AMFI's flow data.</p><div class='rs-grid'>{mc}</div></div>"
            f"<div class='rs-sec' id='pms'><h2>PMS and AIF research</h2><p class='muted'>Portfolio management services from APMI's monthly reports; alternative investment funds explained.</p><div class='rs-grid'>{pc}</div></div>"
            "<div class='rs-sec' id='method'><h2>How we rate</h2><div class='rs-grid'><a class='rs-card' href='/method/'><b class='t'>Mutual fund ratings: method and backtest</b>"
            "<span class='muted'>The measures, the weights, every category's yardstick, and what our backtest found.</span></a>"
            "<a class='rs-card' href='/pms/how-pms-returns-are-measured/'><b class='t'>PMS ratings: method and evidence</b><span class='muted'>One yardstick per asset class, quarterly reviews, and the test behind the weights.</span></a></div></div>"
            f"<div class='rs-sec' id='guides'><h2>Investor guides</h2><p class='muted'>{len(guides)} straight answers, with figures from our data.</p><div class='rs-list'>{gl}</div>"
            "<p style='margin-top:12px'><a href='/learn/'>All guides →</a></p></div>"
            f"<div class='rs-sec' id='tax'><h2>Tax</h2><p class='muted'>Under the Income-tax Act, 2025, tax year 2026-27.</p><div class='rs-list'>{tl}</div></div>")
    path = "/insights/"
    nstory = len(new) + len(cards)
    html = (CSS + "<style>.pm-chip{display:inline-flex;border:1px solid var(--rule);background:var(--surface);border-radius:999px;padding:5px 12px;font-size:13.5px;color:var(--ink-2);text-decoration:none}.pm-chip:hover{border-color:var(--teal);color:var(--teal)}</style>"
            f"<section class='band rs' style='padding-top:26px'><div class='wrap'><div class='rs-hero'><div><div class='rs-eyebrow'>Research</div><h1>Insights and research</h1>"
            f"<p class='lede'>{nstory} data stories on Indian mutual funds, worked out from our own data, plus monthly market data, PMS research, our methods, "
            f"{len(guides)} investor guides and the tax guides: everything we publish, in one place. Last updated {B.dmy(as_of)}.</p></div>{ILL.hero('lines')}</div>{body}</div></section>")
    B.write(path, B.page("Mutual fund research and insights: data stories, market data, PMS, guides | Aeterna Wealth",
                         "Data stories on Indian mutual funds (category returns by year, falls and recoveries, 5-year odds, SIP returns, funds vs index), monthly market data, PMS research, methods and investor guides.",
                         path, html, (B.crumbs([("Insights", path)]),)))
    urls.append((path, "daily", "0.8"))


def build(B, urls, as_of):
    new = stories(B, urls, as_of)
    hub(B, urls, as_of, new)
