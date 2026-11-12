"""The client report (one HTML page, light by default, dark when the device asks) and the internal workings
(lot-level tax CSV). Plain English; no "best", "guaranteed" or "sell everything"."""
from __future__ import annotations

import csv
import html
from datetime import date, timedelta
from pathlib import Path

from . import config as C
from . import data as D
from .plan import Plan

e = html.escape


def rs(x) -> str:
    """₹ in Indian style: lakh / crore for large sums"""
    if x is None:
        return "–"
    x = float(x)
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:,.2f} crore"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:,.2f} lakh"
    return f"₹{x:,.0f}"


def pc(x) -> str:
    return "–" if x is None else f"{x:.0%}"


CSS = """
:root{--bg:#fbfaf7;--surface:#fff;--ink:#14231e;--ink2:#4a5a54;--rule:#e3e0d8;--teal:#0b5a46;--soft:#e7f2ee;--warn:#8a5a00;--warnbg:#fff6e0;--neg:#a12d2d;
--f-body:"Libre Franklin",system-ui,-apple-system,"Segoe UI",sans-serif;--f-display:"Source Serif 4",Georgia,serif;--f-mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0b1512;--surface:#0f1d19;--ink:#e8efec;--ink2:#a7b8b1;--rule:#21352f;--teal:#62d6b2;--soft:#12302a;--warn:#f0c674;--warnbg:#2a2210;--neg:#ff8a80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 var(--f-body)}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font:500 clamp(28px,4vw,40px)/1.15 var(--f-display);margin:6px 0 8px}h2{font:500 24px/1.25 var(--f-display);margin:40px 0 12px}
h3{font:600 15px var(--f-body);margin:20px 0 6px}.eyebrow{font:500 12px var(--f-mono);letter-spacing:.08em;text-transform:uppercase;color:var(--teal)}
.muted{color:var(--ink2)}p{margin:0 0 10px}.mono{font-family:var(--f-mono)}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:16px 18px;margin:12px 0}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.kpi b{display:block;font:500 26px/1.1 var(--f-mono)}.kpi span{font-size:13px;color:var(--ink2)}
.scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font:600 12px var(--f-body);color:var(--ink2);text-transform:uppercase;letter-spacing:.04em}td.n,th.n{text-align:right;font-family:var(--f-mono);white-space:nowrap}
.tag{display:inline-block;padding:1px 8px;border-radius:999px;font:600 12px var(--f-body);white-space:nowrap}
.t-add{background:var(--soft);color:var(--teal)}.t-hold{background:var(--rule);color:var(--ink)}.t-stop{background:var(--warnbg);color:var(--warn)}
.t-exit{background:#fde8e8;color:var(--neg)}.t-deploy{background:var(--warnbg);color:var(--warn)}
@media (prefers-color-scheme:dark){.t-exit{background:#3a1717}}
.warn{background:var(--warnbg);border-color:transparent}.thesis dt{font-weight:600;margin-top:6px}.thesis dd{margin:0 0 4px}
ol.actions li{margin:0 0 12px}.bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--rule);margin-top:6px}
.bar i{display:block;height:100%}.foot{font-size:13px;color:var(--ink2);margin-top:40px;border-top:1px solid var(--rule);padding-top:16px}
@media print{body{background:#fff}.card{break-inside:avoid}}
"""

VERB = {"add": "Add", "hold": "Hold", "stop": "Hold, no new money", "exit": "Exit", "deploy": "Move to equity"}
SLEEVE_COLOR = {"large": "#2f6f5e", "flexi": "#0b5a46", "midlm": "#5aa98f", "small": "#c79a3b", "thematic": "#8a6fb0",
                "hybrid": "#7a8a84", "debt": "#4f6da8", "parked": "#b9b3a6", "other": "#999"}


def _shape_bar(sh: dict) -> str:
    return '<div class="bar">' + "".join(f'<i style="width:{v * 100:.2f}%;background:{SLEEVE_COLOR.get(k, "#999")}" title="{e(C.BUCKET_LABEL.get(k, k))} {v:.0%}"></i>'
                                         for k, v in sorted(sh.items(), key=lambda kv: list(SLEEVE_COLOR).index(kv[0]) if kv[0] in SLEEVE_COLOR else 99) if v > 0) + "</div>"


def render(plan: Plan, proj: dict | None) -> str:
    p, c, port = plan, plan.client, plan.portfolio
    n_before = len(port.holdings)
    keep_codes = {v.h.code for v in p.verdicts if v.action in ("add", "hold", "stop")}
    keep_codes |= {int(f["code"]) for f, a, b in p.sip} | {int(f["code"]) for f, a, b in p.deploy}
    n_after = len(keep_codes)
    exits = [v for v in p.verdicts if v.action == "exit"]
    deploys = [v for v in p.verdicts if v.action == "deploy"]
    parked = sum(v.h.value for v in deploys)
    deploy_total = sum(a for f, a, b in p.deploy)
    weeks = round(p.stp_months * 52 / 12)
    out = [f'<!doctype html><html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>Portfolio review: {e(c.name or port.investor)}</title>'
           '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Libre+Franklin:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..600;1,8..60,400&display=swap">'
           f'<style>{CSS}</style></head><body><main>']
    goal = {"growth": "Growing wealth", "retirement": "Retirement", "education": "Children's education", "house": "Buying a home"}.get(c.goal, c.goal.title())
    horizon = "no fixed date" if p.years is None else f"{p.years} years ({c.target_year})"
    out.append(f'<div class="eyebrow">Aeterna Wealth · Portfolio review · {p.as_of:%d %b %Y}</div>'
               f'<h1>{e(c.name or port.investor)}: what to keep, what to change, and why</h1>'
               f'<p class="muted">{e(goal)} · horizon {e(horizon)} · risk profile <b>{e(p.profile.replace("_", " "))}</b> · '
               f'PAN {e(port.pan_masked or "–")} · from a {e(port.source)}. Ratings as of {e(D.as_of())}; fund portfolios from {e(D.holdings_month() or "–")}.</p>')
    if port.warnings:
        out.append('<div class="card warn">' + "".join(f"<p>{e(w)}</p>" for w in port.warnings) + "</div>")

    # ---------------------------------------------------------------- summary
    out.append('<div class="grid" style="margin-top:20px">'
               f'<div class="card kpi"><b>{rs(port.value)}</b><span>portfolio today</span></div>'
               f'<div class="card kpi"><b>{n_before} → {n_after}</b><span>funds, after the changes</span></div>'
               f'<div class="card kpi"><b>{rs(c.sip)}</b><span>monthly SIP, split over {len(p.sip)} funds</span></div>'
               f'<div class="card kpi"><b>{rs(deploy_total)}</b><span>to move into equity over {p.stp_months} months</span></div></div>')
    bullets = []
    if parked:
        bullets.append(f"{rs(parked)} sits in arbitrage/liquid funds earning about what a liquid fund pays. For a {e(p.profile.replace('_', ' '))} "
                       f"profile with this horizon, it moves into equity through a weekly transfer over {p.stp_months} months.")
    if exits:
        bullets.append(f"{len(exits)} funds to exit ({rs(sum(v.sell_value for v in exits))}): rated C, breaking their category's rules, or too small to matter.")
    if p.sip:
        bullets.append("New SIPs go only to A/A+ rated funds, one per fund house: " + ", ".join(e(f["name"]) for f, a, b in p.sip) + ".")
    holds = [v for v in p.verdicts if v.action in ("hold", "stop")]
    if holds:
        bullets.append(f"{len(holds)} funds are held as they are. Selling a sound fund costs tax and buys little.")
    out.append('<div class="card"><h3 style="margin-top:0">In short</h3><ul>' + "".join(f"<li>{b}</li>" for b in bullets) + "</ul></div>")

    # ---------------------------------------------------------------- shape
    out.append('<h2>The shape of the portfolio</h2><p class="muted">How the money is split by type of fund: today, the target for this goal and risk profile, and after 12 months of the plan (before market moves).</p>')
    rows = []
    for b in [k for k in SLEEVE_COLOR if max(p.current.get(k, 0), p.target.get(k, 0), p.after.get(k, 0)) > 0.001]:
        rows.append(f"<tr><td>{e(C.BUCKET_LABEL.get(b, b))}</td><td class='n'>{pc(p.current.get(b, 0))}</td><td class='n'>{pc(p.target.get(b, 0))}</td><td class='n'>{pc(p.after.get(b, 0))}</td></tr>")
    out.append('<div class="card"><div class="scroll"><table><tr><th>Sleeve</th><th class="n">Today</th><th class="n">Target</th><th class="n">In 12 months</th></tr>'
               + "".join(rows) + "</table></div>"
               f'<p style="margin-top:12px" class="muted">Today</p>{_shape_bar(p.current)}<p style="margin-top:8px" class="muted">In 12 months</p>{_shape_bar(p.after)}</div>')
    lb, la = p.lookthrough_before, p.lookthrough_after
    if lb and la:
        out.append('<div class="card"><h3 style="margin-top:0">What the equity actually owns</h3><p class="muted">Adding up every fund\'s own portfolio:</p>'
                   '<div class="scroll"><table><tr><th>Companies</th><th class="n">Today</th><th class="n">In 12 months</th></tr>'
                   + "".join(f"<tr><td>{k.title()} caps</td><td class='n'>{pc(lb.get(k))}</td><td class='n'>{pc(la.get(k))}</td></tr>" for k in ("large", "mid", "small"))
                   + "</table></div></div>")

    # ---------------------------------------------------------------- funds
    out.append('<h2>Every fund, and what to do with it</h2><div class="card"><div class="scroll"><table><tr><th>Fund</th><th class="n">Value</th><th>Rating</th><th>Verdict</th><th>Why</th></tr>')
    order = {"exit": 0, "deploy": 1, "add": 2, "hold": 3, "stop": 4}
    for v in sorted(p.verdicts, key=lambda v: (order[v.action], -v.h.value)):
        f = v.h.fund
        rating = "–" if f is None else (f"{e(str(f['tier']))}" + (f" · {int(f['peer_rank'])}/{int(f['peer_count'])}" if f.get("peer_rank") == f.get("peer_rank") and f.get("peer_rank") is not None else ""))
        why = "; ".join(e(t) for code, t in v.reasons)
        if v.action == "exit" and v.when:
            why += f"<br><span class='muted'>When: {e(v.when)}</span>"
        out.append(f"<tr><td>{e(v.h.name)}<br><span class='muted' style='font-size:12.5px'>{e(v.h.category or '')} · {e(v.h.plan)}</span></td>"
                   f"<td class='n'>{rs(v.h.value)}</td><td class='mono'>{rating}</td><td><span class='tag t-{v.action}'>{VERB[v.action]}</span></td><td>{why}</td></tr>")
    out.append("</table></div></div>")

    # ---------------------------------------------------------------- actions
    out.append('<h2>What to do, in order</h2><ol class="actions">')
    if p.sip:
        out.append("<li><b>Start the monthly SIPs</b> (stop SIPs into any fund not listed here):<div class='scroll'><table>"
                   "<tr><th>Fund</th><th>Rating</th><th class='n'>Monthly</th></tr>"
                   + "".join(f"<tr><td>{e(f['name'])} ({e(f['plan_type'])})<br><span class='muted' style='font-size:12.5px'>{e(f['category'])} · {e(f['amc'])}</span></td>"
                             f"<td class='mono'>{e(str(f['tier']))} · {int(f['peer_rank'])}/{int(f['peer_count'])}</td><td class='n'>{rs(a)}</td></tr>" for f, a, b in p.sip)
                   + "</table></div></li>")
    if p.deploy:
        src = ", ".join(e(v.h.name) for v in deploys) or "the exit proceeds"
        out.append(f"<li><b>Move parked money into equity</b> through a weekly STP from {src}, over {p.stp_months} months "
                   f"(about {weeks} weekly transfers). Exit proceeds and any lump sum follow the same split:<div class='scroll'><table>"
                   "<tr><th>Into</th><th class='n'>Total</th><th class='n'>Each week</th></tr>"
                   + "".join(f"<tr><td>{e(f['name'])} ({e(f['plan_type'])})</td><td class='n'>{rs(a)}</td><td class='n'>{rs(a / weeks)}</td></tr>" for f, a, b in p.deploy)
                   + "</table></div><p class='muted' style='font-size:13px'>A transfer out of an arbitrage fund is a sale: units held under a year pay 20% tax on their (small) gain. "
                   "Spreading over months means buying through ups and downs instead of on one day.</p></li>")
    if exits:
        out.append("<li><b>Exit these funds</b>, at the time shown, and use the money as in step 2:<div class='scroll'><table>"
                   "<tr><th>Fund</th><th class='n'>Value</th><th>When</th><th class='n'>Tax + exit load</th></tr>"
                   + "".join(f"<tr><td>{e(v.h.name)}</td><td class='n'>{rs(v.sell_value)}</td><td>{e(v.when)}</td>"
                             f"<td class='n'>{rs(v.cost_high) if abs(v.cost_high - v.cost_low) < 1 else rs(v.cost_low) + ' – ' + rs(v.cost_high)}</td></tr>" for v in exits)
                   + "</table></div><p class='muted' style='font-size:13px'>Long-term equity gains up to ₹1.25 lakh a financial year are tax-free; "
                   "the costs above use what is left of this year's limit. Where purchase dates are unknown, the range runs from 'all units over a year old' to 'all under a year'.</p></li>")
    out.append("<li><b>Leave the rest alone.</b> Funds marked Hold stay; no new money goes to funds marked 'Hold, no new money'.</li></ol>")

    # Regular plans: say what they cost
    reg = [(f, a) for f, a, b in p.sip if f["plan_type"] == "Regular"]
    if reg:
        extra = 0.0
        for f, a in reg:
            o = D.other_plan(f)
            if o is not None and o.get("ter") == o.get("ter") and f.get("ter") == f.get("ter"):
                extra += a * 12 * (float(f["ter"]) - float(o["ter"])) / 100
        out.append(f'<div class="card"><h3 style="margin-top:0">About Regular plans</h3><p>These SIPs are in Regular plans. Aeterna is paid a commission by the fund house, '
                   f'included in the plan\'s expense ratio. After a year of SIPs that is about {rs(extra)} a year more than the Direct plans of the same funds, and it grows with the balance. '
                   f'Direct plans have no commission and no distributor service.</p></div>')

    # ---------------------------------------------------------------- theses
    if p.theses:
        out.append('<h2>Why the shape changes</h2><p class="muted">Every change of shape has a reason, a cost and a condition under which we would undo it.</p>')
        for t in p.theses:
            out.append(f'<div class="card thesis"><h3 style="margin-top:0">{e(t["title"])}</h3><dl>'
                       + (f"<dt>What changes</dt><dd>{e(t['what'])}</dd>" if t.get("what") else "")
                       + f"<dt>Why it suits this plan</dt><dd>{e(t['why'])}</dd><dt>What it costs</dt><dd>{e(t['cost'])}</dd>"
                       f"<dt>We would reverse it if</dt><dd>{e(t['reverse'])}</dd><dt>The evidence, and its limits</dt><dd>{e(t['evidence'])}</dd></dl></div>")

    # ---------------------------------------------------------------- projection
    if proj:
        cur, pl = proj["current"], proj["plan"]
        tgt = proj.get("target_nominal")
        head = (f"In {proj['years']} years" + (" (a 15-year view: this goal has no fixed date)" if proj.get("fixed_horizon") else ""))
        out.append(f'<h2>Where this could lead</h2><p class="muted">{e(head)}, with a {rs(c.sip)} monthly SIP. Each line is 5,000 simulated futures built from real 12-month stretches of '
                   f'Indian fund history ({e(proj["history"])}), using each category\'s median fund. A range from history, not a forecast.</p>'
                   '<div class="card"><div class="scroll"><table><tr><th></th><th class="n">Bad case (1 in 10)</th><th class="n">Middle</th><th class="n">Good case (1 in 10)</th>'
                   + ("<th class='n'>Chance of reaching the goal</th>" if tgt else "") + "</tr>"
                   + "".join(f"<tr><td>{lab}</td><td class='n'>{rs(r['p10'])}</td><td class='n'>{rs(r['p50'])}</td><td class='n'>{rs(r['p90'])}</td>"
                             + (f"<td class='n'>{pc(r['p_success'])}</td>" if tgt else "") + "</tr>"
                             for lab, r in (("Today's mix", cur), ("This plan", pl)))
                   + "</table></div>")
        if tgt:
            out.append(f"<p style='margin-top:10px'>Goal: {rs(c.target_today)} in today's money is about {rs(tgt)} in {c.target_year}, at {proj['inflation']:.0%} inflation a year.</p>")
            need = [(g, proj.get(f"sip_for_{g}")) for g in (70, 85)]
            if any(x and x > c.sip for g, x in need):
                out.append("<p>" + " ".join(f"A {g}% chance needs about {rs(x)} a month." for g, x in need if x) + "</p>")
        out.append("<p class='muted' style='font-size:13px'>Category medians include their costs; real results depend on the funds chosen, "
                   "on when money goes in, and on future markets, which may be worse than any period in this history.</p></div>")

    # ---------------------------------------------------------------- overlap and concentration
    if p.overlap or p.amc_share:
        out.append('<h2>Overlap and concentration</h2><div class="card">')
        if p.overlap:
            out.append("<p>Share of the portfolio two funds hold in common (above 50%, they are close to one bet):</p><div class='scroll'><table>"
                       + "".join(f"<tr><td>{e(a['name'])} + {e(b['name'])}</td><td class='n'>{pc(o)}</td></tr>" for a, b, o in p.overlap[:8]) + "</table></div>")
        out.append("<p style='margin-top:12px'>Equity by fund house after the plan: " + ", ".join(f"{e(k.replace(' Mutual Fund', ''))} {v:.0%}" for k, v in sorted(p.amc_share.items(), key=lambda kv: -kv[1])) + "</p>")
        out.append("</div>")
    other = [w for w in p.warnings if w not in port.warnings]
    if other:
        out.append('<div class="card warn">' + "".join(f"<p>{e(w)}</p>" for w in other) + "</div>")

    # ---------------------------------------------------------------- monitoring
    nxt = p.as_of + timedelta(days=365)
    out.append(f'<h2>What we watch, and when we look again</h2><div class="card"><ul>'
               f"<li>Every month (after ratings update on the 11th and 16th): any fund held falling to C, a mandate breach, a fund manager change or a merger.</li>"
               f"<li>Any sleeve more than {C.BAND_ABS:.0%} points (or {C.BAND_REL:.0%}) away from its target, checked at each review and after any 20% market move. "
               f"New money corrects it first.</li>"
               + (f"<li>The glide path: from {c.target_year - 5}, money moves from equity to debt or arbitrage each year so that a fall close to the goal does not derail it.</li>" if c.target_year else "")
               + f"<li>Next full review: {nxt:%B %Y}, or sooner if income, goals or plans change.</li></ul></div>")

    # ---------------------------------------------------------------- disclosures
    stale = (date.today() - C.TAX_CHECKED).days > 365
    out.append('<div class="foot"><p>Mutual fund investments are subject to market risks; read all scheme-related documents carefully. Ratings describe past performance '
               'and are not a forecast. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889), not a SEBI-registered investment adviser; '
               'these suggestions are incidental to distribution. Tax figures are estimates under the rules in force on '
               f'{C.TAX_CHECKED:%d %b %Y}' + (" (<b>these rules have not been re-checked for over a year</b>)" if stale else "")
               + '; confirm with your tax adviser before acting. Exit loads use typical values unless the scheme\'s own is on file.</p></div>')
    out.append("</main></body></html>")
    return "\n".join(out)


def workings_csv(plan: Plan, path: Path):
    """lot-level tax workings for every exit (internal; contains no PAN)"""
    from . import tax as T
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["fund", "code", "lot_date", "units", "basis_per_unit", "nav", "proceeds", "gain", "days", "term", "exit_load", "elss_locked"])
        for v in plan.verdicts:
            if v.action not in ("exit", "deploy"):
                continue
            h = v.h
            gf = D.nav_on(h.code, C.TAX["equity"]["grandfather_date"]) if h.code else None
            sc = T.sell(h.lots, h.units, plan.as_of, h.nav, cls=T.tax_class(h.fund), category=h.category or "", code=h.code, grandfather_nav=gf)
            for s in sc.slices:
                w.writerow([h.name, h.code, s.lot_date or "unknown", round(s.units, 3), round(s.basis, 4), round(h.nav, 4), round(s.proceeds, 2),
                            round(s.gain, 2), s.days if s.days is not None else "", s.term, round(s.load, 2), s.locked])
