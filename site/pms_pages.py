"""PMS (portfolio management services) and AIF pages, from site/data/pms.json (tools/pms_build.py). Standard library only.

/pms/                                  hub: the market in one view, how rated strategies did, top of each peer group, managers
/pms/ratings/<group>/                  every rated strategy in a group, filterable and sortable (equity, debt, hybrid and multi-asset)
/pms/<manager>/                        a portfolio manager with 2+ strategies shown: assets, every strategy (rated or not)
/pms/<manager>/<strategy>/             a strategy: rating, returns against its own yardstick, growth, calendar, monthly grid,
                                       rolling returns, consistency, risk, money flows, assets, peers
/pms/how-pms-returns-are-measured/     TWRR, after fees, before tax; three yardsticks; scores; quarterly review
/aif/                                  AIFs: categories, what is public and what is not
Rules: research framing; one general "talk to us" line; no "best"/"buy"; no distributor registration shown.
Method: docs/thesis_pms_ratings.md (v2: one yardstick and one score per asset class, quarterly review with a buffer).
"""
import json
import math
from collections import defaultdict

import charts as C
import illustrations as ILL

GROUP_SLUG = {"Equity": "equity", "Debt": "debt", "Hybrid and multi-asset": "hybrid-and-multi-asset"}
GROUP_TXT = {"Equity": "equity", "Debt": "debt", "Hybrid and multi-asset": "hybrid and multi-asset"}
TIER_WORD = {"A+": "Leading", "A": "Strong", "B": "In line", "C": "Lagging"}
TIER_VAR = {"A+": "var(--t-ap)", "A": "var(--t-a)", "B": "var(--t-b)", "C": "var(--t-c)"}
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
PILLARS = {   # measure -> (pillar, short label)
    "alpha": ("Skill", "Alpha over its yardstick"), "ir": ("Skill", "Information ratio"), "hit_m": ("Consistency", "Months ahead"),
    "hit_12m": ("Consistency", "12-month spells ahead"), "half_min": ("Consistency", "Ahead in both halves"),
    "ex_ann": ("Skill", "Return over its yardstick"), "sortino": ("Risk", "Sortino ratio"),
    "down_capture": ("Risk", "Protection in falls"), "vol": ("Risk", "Low volatility"), "rel_dd": ("Risk", "Worst fall vs yardstick"),
    "max_dd": ("Risk", "Worst fall")}
LONG = {"alpha": "its return over its yardstick, adjusted for market exposure (alpha)", "ir": "the steadiness of its lead (information ratio)",
        "hit_m": "the share of months it was ahead", "hit_12m": "the share of 12-month spells it was ahead", "half_min": "being ahead in both halves of its record",
        "ex_ann": "its return over its yardstick", "sortino": "return per unit of downside risk", "down_capture": "protection in falling months",
        "vol": "low volatility", "rel_dd": "its worst fall compared with its yardstick's", "max_dd": "its worst fall"}


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


def _crs(v):
    """short assets: ₹4.7 lakh cr / ₹10,674 cr"""
    if v is None:
        return "–"
    return f"₹{v / 1e5:,.2f} lakh cr" if v >= 1e5 else f"₹{v:,.0f} cr"


def _cls(v):
    return "" if v is None else (" class='pos'" if v > 0 else " class='neg'" if v < 0 else "")


def _ysh(s):
    """short yardstick name"""
    y = s.get("yard", {}).get("name", "Nifty 500 TRI")
    return (y.replace(" TRI", "").replace("Nifty 500 Multicap 50:25:25", "Multicap 50:25:25").replace("median high-quality bond fund", "bond funds")
            .replace("% Nifty 500 + ", "% equity, ").replace("% bond funds", "% bonds"))


def url_s(s):
    return f"/pms/{s['mslug']}/{s['slug']}/"


MLINK = {}   # manager slug -> the page that covers the manager (filled in build)


def url_m(m):
    return MLINK.get(m) or "/pms/"


STYLE = """<style>
.pm{--gap:44px}.pm .pos{color:var(--good)}.pm .neg{color:var(--bad)}
.pm-eyebrow{font:600 12px/1 var(--f-body);letter-spacing:.12em;text-transform:uppercase;color:var(--teal)}
.pm-hero{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:32px;align-items:end}.pm-side{display:grid;gap:12px}.pm-side .ill-h{max-width:320px}
.pm-hero h1{font-size:clamp(30px,4.4vw,48px);line-height:1.08;margin-top:10px;letter-spacing:-.01em}
.pm-hero .lede{margin-top:12px}
.pm-stamp{border:1px solid var(--rule);border-radius:var(--r);background:var(--surface);padding:12px 14px;font-size:13px;color:var(--ink-2);min-width:220px;line-height:1.6}
.pm-stamp b{display:block;font:500 14px var(--f-mono);color:var(--ink)}
.pm-chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:14px}.pm-chip{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--rule);background:var(--surface);border-radius:999px;padding:5px 11px;font-size:13px;color:var(--ink-2);text-decoration:none}
a.pm-chip:hover{border-color:var(--teal);color:var(--teal)}
.pm-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;margin-top:26px}
.pm-kpis div{background:var(--surface);padding:16px 18px}.pm-kpis>div>span{display:block;color:var(--ink-2);font-size:13px}.pm-kpis b{display:block;font:500 24px/1.25 var(--f-mono);margin-top:4px}
.pm-kpis small{display:block;color:var(--ink-3);font-size:12.5px;margin-top:2px}
.pm-sec{margin-top:var(--gap);scroll-margin-top:90px}.pm-sec>h2{font-size:clamp(24px,2.6vw,30px)}.pm-sec>p.muted,.pm-sub{margin-top:6px;font-size:15px;color:var(--ink-2)}
.pm-nav{position:sticky;top:64px;z-index:5;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding:10px 0;margin-top:26px;background:var(--paper);border-bottom:1px solid var(--rule)}
.pm-nav::-webkit-scrollbar{display:none}.pm-nav a{flex:none;font-size:13.5px;font-weight:600;color:var(--ink-2);text-decoration:none;padding:6px 12px;border-radius:999px}
.pm-nav a:hover{background:var(--band);color:var(--teal)}
.pm-chart{margin-top:14px;border:1px solid var(--rule);border-radius:var(--r);background:var(--surface);padding:12px 12px 8px}
.pm-chart svg{width:100%;height:auto;display:block;overflow:visible}.pm-leg{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:6px 4px 0}
.pm-leg i{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px;border-radius:2px}.pm-leg i.dot{width:9px;height:9px;border-radius:50%}
.pm-heat{border-collapse:collapse;font:500 12.5px var(--f-mono);width:100%;min-width:640px}.pm-heat td,.pm-heat th{border:1px solid var(--rule);padding:6px 4px;text-align:center}
.pm-heat th{font:600 12px var(--f-body);color:var(--ink-2);background:var(--surface)}
.pm-bar{height:8px;border-radius:4px;background:var(--rule);overflow:hidden;min-width:70px;flex:1}.pm-bar i{display:block;height:100%;background:var(--teal);border-radius:4px}
.pm-rate{display:grid;grid-template-columns:auto minmax(0,1fr) minmax(0,1.1fr);gap:26px;align-items:center;margin-top:22px;padding:22px 24px;border:1px solid var(--rule);border-radius:calc(var(--r) + 4px);background:var(--surface);position:relative;overflow:hidden}
.pm-rate:before{content:"";position:absolute;inset:0 auto 0 0;width:5px;background:var(--tc,var(--teal))}
.pm-ring{width:112px;height:112px;position:relative}.pm-ring svg{width:112px;height:112px;transform:rotate(-90deg)}
.pm-ring b{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;font:500 30px/1 var(--f-mono)}.pm-ring b small{display:block;font:400 10.5px var(--f-body);color:var(--ink-3);margin-top:4px}
.pm-rate h3{font:500 22px/1.25 var(--f-display);margin:8px 0 6px}.pm-rate p{margin:0;font-size:14.5px;color:var(--ink-2)}
.pm-pil{display:grid;gap:10px}.pm-pil div{display:grid;grid-template-columns:150px minmax(0,1fr) 36px;gap:10px;align-items:center;font-size:13.5px;color:var(--ink-2)}.pm-pil b{font:500 13px var(--f-mono);color:var(--ink);text-align:right}
.pm-two{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:start}.pm-two>div{min-width:0}
.pm-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px;margin-top:16px}
.pm-card{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:18px 20px;text-decoration:none;color:inherit;min-width:0}
a.pm-card:hover{border-color:var(--teal)}.pm-card h3{font:500 20px/1.25 var(--f-display);margin:0}.pm-card .muted{font-size:13.5px}
.pm-tbar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--rule)}.pm-tbar i{display:block;height:100%}
.pm-tleg{display:flex;flex-wrap:wrap;gap:4px 12px;font-size:12.5px;color:var(--ink-2);margin-top:6px}.pm-tleg span:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px;background:var(--c)}
.pm-mini{list-style:none;margin:0;padding:0;font-size:14px}.pm-mini li{display:grid;grid-template-columns:22px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 0;border-top:1px dashed var(--rule)}
.pm-mini li a{text-decoration:none;color:var(--ink);font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.pm-mini li small{display:block;color:var(--ink-3);font-weight:400;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pm-mini li>span:first-child{font:500 12px var(--f-mono);color:var(--ink-3)}
.pm-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:16px;counter-reset:st}
.pm-steps>div{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:18px 20px;counter-increment:st}
.pm-steps>div:before{content:counter(st,decimal-leading-zero);font:500 13px var(--f-mono);color:var(--teal)}.pm-steps .ill-i{margin:10px 0 2px}.pm-steps h3{font:500 19px/1.3 var(--f-display);margin:6px 0}.pm-steps p{margin:0;font-size:14px;color:var(--ink-2)}
.pm-tools{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:16px}
.pm-tools input{flex:1;min-width:200px;max-width:340px;border:1px solid var(--rule);border-radius:var(--r);padding:10px 12px;font:inherit;font-size:14.5px;background:var(--surface);color:var(--ink)}
.pm-seg{display:inline-flex;flex-wrap:wrap;border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;background:var(--surface)}
.pm-seg button{border:0;background:none;padding:9px 13px;font:600 13.5px var(--f-body);color:var(--ink-2);cursor:pointer;border-right:1px solid var(--rule)}.pm-seg button:last-child{border-right:0}
.pm-seg button[aria-pressed=true]{background:var(--teal);color:var(--on-teal)}
table.pm-t th[data-k]{cursor:pointer;user-select:none;white-space:nowrap}table.pm-t th[data-k]:after{content:" ↕";opacity:.35;font-size:11px}
table.pm-t th[aria-sort=ascending]:after{content:" ↑";opacity:1}table.pm-t th[aria-sort=descending]:after{content:" ↓";opacity:1}
table.pm-t td.l a{font-weight:600}.pm td small{display:block;color:var(--ink-3);font-size:12px;font-weight:400}
.pm-dir{columns:3 240px;column-gap:28px;margin-top:14px;font-size:14.5px;line-height:1.95}.pm-dir a{text-decoration:none}.pm-dir a:hover{text-decoration:underline}
.pm-dir h4{font:600 12px var(--f-mono);color:var(--teal);margin:10px 0 2px;break-after:avoid}
.pm-cta{margin-top:48px;border-radius:calc(var(--r) + 4px);background:var(--teal);color:var(--on-teal);padding:28px 30px;display:flex;gap:20px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.pm-cta b{font:500 24px/1.25 var(--f-display)}.pm-cta p{margin:6px 0 0;opacity:.88;max-width:620px}.pm-cta .btn{background:var(--paper);color:var(--ink);border-color:var(--paper)}
.pm-ms{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px;padding-top:10px;border-top:1px dashed var(--rule)}.pm-ms span{display:block;font-size:12px;color:var(--ink-3)}.pm-ms b{font:500 15px var(--f-mono)}
.pm-note{font-size:13px;color:var(--ink-3);margin-top:22px;line-height:1.65}
@media (max-width:900px){.pm-hero{grid-template-columns:1fr}.pm-rate{grid-template-columns:auto minmax(0,1fr)}.pm-rate .pm-pil{grid-column:1/-1}.pm-two,.pm-steps{grid-template-columns:1fr!important}}
@media (max-width:700px){.pm-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.pm-kpis b{font-size:19px}.pm-kpis div{padding:13px 14px}.pm-nav{top:56px}
.pm-rate{grid-template-columns:1fr;padding:20px}.pm-pil div{grid-template-columns:120px minmax(0,1fr) 32px}.pm-cta{padding:22px}
.pm-chart{overflow-x:auto;-webkit-overflow-scrolling:touch}.pm-chart svg{min-width:620px}.pm-chart.hb svg{min-width:0}
.pm-stamp{display:flex;flex-wrap:wrap;gap:2px 8px;align-items:baseline;min-width:0}.pm-stamp b{display:inline;margin-right:6px}
.pm-seg{display:flex;width:100%}.pm-seg button{flex:1 1 auto}.pm-tools input{max-width:none}}
</style>"""

SORT_JS = """<script>(function(){var t=document.querySelector('table.pm-t');if(!t)return;var tb=t.tBodies[0],rows=[].slice.call(tb.rows),q=document.getElementById('pmQ'),st={g:'',t:''};
function apply(){var s=(q&&q.value||'').toLowerCase(),n=0;rows.forEach(function(r){var ok=(!s||r.getAttribute('data-s').indexOf(s)>=0)&&(!st.g||r.getAttribute('data-g')===st.g)&&(!st.t||r.getAttribute('data-t')===st.t);r.hidden=!ok;if(ok)n++});var c=document.getElementById('pmN');if(c)c.textContent=n}
if(q)q.addEventListener('input',apply);
[].forEach.call(document.querySelectorAll('.pm-seg'),function(seg){seg.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;[].forEach.call(seg.children,function(x){x.setAttribute('aria-pressed',x===b)});st[seg.getAttribute('data-f')]=b.getAttribute('data-v');apply()})});
[].forEach.call(t.tHead.rows[0].cells,function(th,i){if(!th.hasAttribute('data-k'))return;th.tabIndex=0;var go=function(){var d=th.getAttribute('aria-sort')==='descending'?1:-1;[].forEach.call(t.tHead.rows[0].cells,function(x){x.removeAttribute('aria-sort')});th.setAttribute('aria-sort',d>0?'ascending':'descending');
rows.sort(function(a,b){var x=parseFloat(a.cells[i].getAttribute('data-v')),y=parseFloat(b.cells[i].getAttribute('data-v'));if(isNaN(x))return 1;if(isNaN(y))return -1;return d*(x-y)});rows.forEach(function(r){tb.appendChild(r)})};
th.addEventListener('click',go);th.addEventListener('keydown',function(e){if(e.key==='Enter')go()})});
var h=decodeURIComponent(location.hash.slice(1));if(h){[].forEach.call(document.querySelectorAll('.pm-seg[data-f=g] button'),function(b){if(b.getAttribute('data-v').toLowerCase().replace(/ /g,'-')===h)b.click()})}})();</script>"""


# ------------------------------------------------------------------ building blocks
def _table(head, rows, cls=""):
    th = "".join(f"<th{' class=\"l\"' if i == 0 else ''}>{h}</th>" for i, h in enumerate(head))
    return (f"<div class='tablewrap' style='margin-top:14px'><table class='{cls}'><thead><tr>{th}</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td class='{'l' if i == 0 else 'num'}'>{c}</td>" for i, c in enumerate(r)) + "</tr>" for r in rows)
            + "</tbody></table></div>")


def _kpis(items):
    return "<div class='pm-kpis'>" + "".join(f"<div><span>{k}</span><b>{v}</b>{f'<small>{s}</small>' if s else ''}</div>" for k, v, s in items) + "</div>"


def _line_chart(series, labels, fmt=lambda v: f"{v:,.0f}", zero=None, h=300, area=False, label="chart", small=False):
    return C.line(series, labels, fmt, zero, h, area, label, small=small)


def _bars(labels, vals, h=230, fmt=lambda v: f"₹{v:,.0f} cr", label="bar chart"):
    return C.bars(labels, vals, fmt, h, label)


def _scatter(pts, xl, yl, h=440, label="scatter"):
    return C.scatter(pts, xl, yl, h, label, me_label="This strategy")


def _ticks(lo, hi, n=5):
    """round tick values between lo and hi"""
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    v = math.ceil(lo / step) * step
    out = []
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out


def _hbars(items, fmt, h_row=34, colour="var(--teal)", label="bar chart", W=760):
    """items: [(label, value)] horizontal bars, labels on the left."""
    if not items:
        return ""
    L, R = min(220, int(W * .3)), 110
    H = h_row * len(items) + 8
    mx = max(v for _, v in items) or 1
    g = []
    for i, (lab, v) in enumerate(items):
        yy = 4 + i * h_row
        w = (W - L - R) * v / mx
        g.append(f"<text x='{L - 10}' y='{yy + h_row / 2 + 4:.1f}' text-anchor='end' font-size='13' fill='var(--ink-2)'>{lab}</text>"
                 f"<rect x='{L}' y='{yy + 7}' width='{max(2, w):.1f}' height='{h_row - 14}' rx='3' fill='{colour}'/>"
                 f"<text x='{L + w + 8:.1f}' y='{yy + h_row / 2 + 4:.1f}' font-size='13' font-weight='600' fill='var(--ink)'>{fmt(v)}</text>")
    return f"<div class='pm-chart hb'><svg viewBox='0 0 {W} {H}' role='img' aria-label='{label}'>{''.join(g)}</svg></div>"


def _tierbar(L):
    cnt = {t: sum(s.get("tier") == t for s in L) for t in ("A+", "A", "B", "C")}
    n = sum(cnt.values()) or 1
    bar = "".join(f"<i style='width:{cnt[t] / n * 100:.2f}%;background:{TIER_VAR[t]}' title='{t}: {cnt[t]}'></i>" for t in cnt if cnt[t])
    leg = "".join(f"<span style='--c:{TIER_VAR[t]}'>{t} {TIER_WORD[t]} {cnt[t]}</span>" for t in cnt)
    return f"<div><div class='pm-tbar'>{bar}</div><div class='pm-tleg'>{leg}</div></div>"


def _ring(score, tier):
    c = 2 * math.pi * 48
    f = max(0, min(100, score or 0)) / 100
    return (f"<div class='pm-ring'><svg viewBox='0 0 112 112' aria-hidden='true'><circle cx='56' cy='56' r='48' fill='none' stroke='var(--rule)' stroke-width='9'/>"
            f"<circle cx='56' cy='56' r='48' fill='none' stroke='{TIER_VAR.get(tier, 'var(--teal)')}' stroke-width='9' stroke-linecap='round' "
            f"stroke-dasharray='{c * f:.1f} {c:.1f}'/></svg><b>{score:.0f}<small>score of 100</small></b></div>")


def _chain(rs):
    g = 1.0
    for r in rs:
        g *= 1 + r / 100
    return g


def _prev(m):
    y, mo = int(m[:4]), int(m[5:])
    return f"{y - 1}-12" if mo == 1 else f"{y}-{mo - 1:02d}"


def _wrap(B, path, title, desc, crumbs, hero, body, ld=(), js=""):
    nav = " › ".join(f"<a href='{u}'>{B.e(t)}</a>" if u != path else B.e(t) for t, u in crumbs)
    html = (STYLE + C.assets() + f"<section class='band pm' style='padding-top:26px'><div class='wrap'><nav aria-label='Breadcrumb' class='muted' style='font-size:13.5px'>{nav}</nav>"
            f"{hero}{body}{_talk(B)}{_foot(B)}</div></section>{js}")
    B.write(path, B.page(title, desc, path, html, (B.crumbs(crumbs),) + tuple(ld)))


def _hero(B, eyebrow, h1, lede, stamp="", chips="", art="lines"):
    st = f"<div class='pm-side'>{ILL.hero(art) if art else ''}{f'<div class=pm-stamp>{stamp}</div>' if stamp else ''}</div>" if (stamp or art) else ""
    return (f"<div class='pm-hero' style='margin-top:16px'><div><div class='pm-eyebrow'>{eyebrow}</div><h1>{B.e(h1)}</h1>"
            f"<p class='lede'>{lede}</p>{chips}</div>{st}</div>")


def _stamp(D):
    return (f"<span>APMI data to</span><b>{_mo(D['as_of'])}</b><span>Ratings reviewed on data to</span><b>{_mo(D.get('review', D['as_of']))}</b>"
            f"<span>Next review: data to {_mo(D.get('next_review', D['as_of']))}</span>")


def _talk(B):
    wa = B.wa_link("Hello Aeterna, I'd like a second opinion on a PMS.")
    return ("<div class='pm-cta'><div><b>Want a second opinion on a PMS?</b><p>Whether you hold one or are considering one, talk to us: we will go "
            "through its record, its risks and how it fits with the rest of your money.</p></div>"
            f"<a class='btn' href='{wa}' target='_blank' rel='noopener'>Talk to us</a></div>")


def _foot(B):
    return ("<p class='pm-note'>Source: APMI (Association of Portfolio Managers in India) monthly reports, which portfolio managers file as SEBI requires. "
            "Returns are time-weighted, after all fees and expenses and before the investor's tax; periods over a year are annualised. Each strategy is "
            "compared with its own yardstick: equity with the style index it tracks most closely (total-return), debt with the median high-quality bond "
            "mutual fund, hybrid with its fitted mix of the two. Ratings describe past track records and are not a recommendation or a forecast; past "
            "performance does not guarantee future returns. PMS investments need at least ₹50 lakh, can lose value and carry higher fees than mutual "
            "funds; read the portfolio manager's disclosure document before investing. "
            "<a href='/pms/how-pms-returns-are-measured/'>How we measure and rate</a> · <a href='/disclosures/'>Disclosures</a></p>")


def _peer_label(s):
    g = s.get("peer_group") or s["group"]
    return {"Large and multi cap": "large and multi cap equity", "Mid and small cap": "mid and small cap equity"}.get(g, GROUP_TXT.get(g, g.lower()))


# ------------------------------------------------------------------ strategy page
def strategy_page(B, D, s, peers, mgr_all):
    path = url_s(s)
    m, a, yr = s["m"], s["apmi"], s.get("yr", {})
    months, r, b = s["months"], s["r"], s["b"]
    tier = s.get("tier")
    g = s["group"]
    gurl = f"/pms/ratings/{GROUP_SLUG[g]}/"
    yname = s["yard"]["name"]
    ysh = _ysh(s)
    first, lastm = months[0], months[-1]
    ex3 = m.get("ex3y")
    # ---------- hero
    chips = "".join(f"<span class='pm-chip'>{c}</span>" for c in
                    [g if g != "Equity" else f"Equity · {s.get('style_group', '')}", "Discretionary", f"Yardstick: {B.e(yname)}",
                     f"Record since {_mo(first)}"])
    if url_m(s["mslug"]) not in ("/pms/", path):
        chips = f"<a class='pm-chip' href='{url_m(s['mslug'])}'>{B.e(s['manager'])} →</a>" + chips
    lede = (f"A discretionary {s['type'].lower()} PMS strategy run by {B.e(s['manager'])}, with {_cr(s['aum'])} of client money at the end of {_mo(lastm)}. "
            f"Over 3 years it returned {_p(a['r3y'])} a year after fees"
            + (f", {_p(abs(ex3))} a year {'more' if ex3 >= 0 else 'less'} than its yardstick, {B.e(yname)}" if ex3 is not None else "") + ".")
    hero = _hero(B, "PMS strategy", s["name"], lede, chips=f"<div class='pm-chips'>{chips}</div>", art="lines")
    kpis = _kpis([("Assets", _cr(s["aum"]), f"end of {_mo(lastm)}"), ("3 years, a year", _p(a["r3y"]), "after fees"),
                  ("vs its yardstick, 3 years", f"<span{_cls(ex3)}>{_p(ex3, 1, True)}</span>", B.e(ysh) + ", a year"),
                  ("Worst fall", _p(m.get("max_dd")), f"yardstick {_p(m.get('bench_dd'))}")])
    # ---------- rating panel
    rating = ""
    pc = s.get("pct", {})
    if tier:
        top = sorted(((v, k) for k, v in pc.items()), reverse=True)
        strong = [LONG[k] for v, k in top[:2] if v >= 0.6]
        weak = [LONG[k] for v, k in top[::-1][:2] if v <= 0.4]
        why = []
        if strong:
            why.append("Stronger than most peers on " + " and ".join(strong) + ".")
        if weak:
            why.append("Weaker on " + " and ".join(weak) + ".")
        if s.get("flag"):
            why.append(B.e(s["flag"]) + ".")
        pil = defaultdict(list)
        for k, v in pc.items():
            pil[PILLARS[k][0]].append(v)
        pbars = "".join(f"<div><span>{p}</span><span class='pm-bar'><i style='width:{sum(v) / len(v) * 100:.0f}%'></i></span><b>{sum(v) / len(v) * 100:.0f}</b></div>"
                        for p, v in pil.items())
        rating = (f"<div class='pm-rate' style='--tc:{TIER_VAR[tier]}'>{_ring(s['score'], tier)}<div>{B.tier_badge(tier, True)}"
                  f"<h3>{s['rank']} of {s['of']} rated {_peer_label(s)} strategies</h3><p>{' '.join(why)}</p>"
                  f"<p style='margin-top:8px;font-size:13px'>Rated at the quarterly review of data to {_mo(D['review'])}; next review on data to {_mo(D['next_review'])}. "
                  f"<a href='/pms/how-pms-returns-are-measured/#rating'>How the rating works</a></p></div>"
                  f"<div class='pm-pil'><p style='font-size:13px'>Standing among its peers by pillar (100 = top of the group)</p>{pbars}</div></div>")
    elif s.get("pending"):
        rating = (f"<div class='pm-rate'><div style='grid-column:1/-1'><h3>Rated at the next quarterly review</h3><p>This strategy became eligible after the last review "
                  f"(data to {_mo(D['review'])}). It will be rated on data to {_mo(D['next_review'])}.</p></div></div>")
    # ---------- trailing returns vs yardstick
    per = [("1 month", "r1m"), ("3 months", "r3m"), ("6 months", "r6m"), ("1 year", "r1y"), ("2 years", "r2y"),
           ("3 years", "r3y"), ("4 years", "r4y"), ("5 years", "r5y"), ("Since launch", "rsi")]
    rows = []
    for lab_, k in per:
        if a.get(k) is None:
            continue
        d = None if yr.get(k) is None else a[k] - yr[k]
        rows.append([lab_, _p(a[k]), _p(yr.get(k)), f"<span{_cls(d)}>{_p(d, 1, True)}</span>"])
    ret_tbl = _table(["Period", "Strategy", B.e(ysh), "Difference"], rows)
    # ---------- growth of Rs 50 lakh
    gs, gb, x1, x2 = [], [], 50.0, 50.0
    for x, y in zip(r, b):
        x1 *= 1 + x / 100
        x2 *= 1 + y / 100
        gs.append(x1)
        gb.append(x2)
    growth = _line_chart([(s["name"], "var(--teal)", gs), (yname, "var(--brass)", gb)], months, fmt=lambda v: f"₹{v:,.0f}L", area=True,
                         label=f"Growth of ₹50 lakh in {s['name']} and {yname}")
    gap = gs[-1] - gb[-1]
    # ---------- rolling 12 months
    r12s, r12b, lab12 = [], [], []
    for i in range(12, len(r) + 1):
        r12s.append((_chain(r[i - 12:i]) - 1) * 100)
        r12b.append((_chain(b[i - 12:i]) - 1) * 100)
        lab12.append(months[i - 1])
    roll = _line_chart([("Strategy", "var(--teal)", r12s), (yname, "var(--brass)", r12b)], lab12, fmt=lambda v: f"{v:,.0f}%", zero=0,
                       label="Rolling 12-month return") if r12s else ""
    # ---------- calendar years
    cal = s.get("cal", {})
    crow = []
    for y, c in sorted(cal.items()):
        lab_ = y + (f" <small class='muted' style='display:inline'>({MON[int(c['from'][5:]) - 1]}–{MON[int(c['to'][5:]) - 1]})</small>" if c["n"] < 12 else "")
        crow.append([lab_, _p(c["r"]), _p(c["b"]), f"<span{_cls(c['r'] - c['b'])}>{_p(c['r'] - c['b'], 1, True)}</span>"])
    cal_tbl = _table(["Year", "Strategy", B.e(ysh), "Difference"], crow) if crow else ""
    # ---------- monthly grid
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
                col = f"color-mix(in srgb,var(--{'good' if d >= 0 else 'bad'}) {min(55, 8 + abs(d) * 7):.0f}%,var(--surface))"
                cells.append(f"<td style='background:{col}' title='{MON[k]} {y}: strategy {x:.2f}%, yardstick {yy:.2f}%'>{x:.1f}</td>")
            else:
                cells.append("<td></td>")
        hrow.append(f"<tr><th>{y}</th>{''.join(cells)}</tr>")
    heat = ("<div class='tablewrap' style='margin-top:14px'><table class='pm-heat'><thead><tr><th></th>" + "".join(f"<th>{x}</th>" for x in MON)
            + "</tr></thead><tbody>" + "".join(hrow) + "</tbody></table></div>")
    # ---------- consistency and risk
    P = lambda v, d=0: _p(None if v is None else v * 100, d)
    cons = [("Months ahead of its yardstick", P(m.get("hit_m"))), ("12-month spells ahead", P(m.get("hit_12m"))),
            ("Alpha, a year (market exposure removed)", _p(m.get("alpha"), 1, True)), ("Information ratio", _n(m.get("ir"))),
            ("Lead in its weaker half of the record", _p(m.get("half_min"), 1, True)),
            ("Best 12 months against the yardstick", _p(m.get("best_12m_ex"), 1, True)), ("Worst 12 months against the yardstick", _p(m.get("worst_12m_ex"), 1, True)),
            ("Best 12 months", _p(max(r12s) if r12s else None)), ("Worst 12 months", _p(min(r12s) if r12s else None))]
    risk = [("Worst fall, month-end to month-end", _p(m.get("max_dd"))), ("Yardstick's worst fall, same months", _p(m.get("bench_dd"))),
            ("Months from peak to bottom", str(m.get("dd_months")) if m.get("dd_months") is not None else "–"),
            ("Months to recover", str(m.get("recovery_months")) if m.get("recovery_months") is not None else ("not yet" if (m.get("max_dd") or 0) < 0 else "–")),
            ("Share of the yardstick's falls taken", P(m.get("down_capture"))), ("Share of the yardstick's rises taken", P(m.get("up_capture"))),
            ("Volatility, a year", _p(m.get("vol"))), ("Beta to Nifty 500", _n(m.get("beta"))), ("Tracking error, a year", _p(m.get("te"))),
            ("Sharpe ratio (6.5% risk-free)", _n(m.get("sharpe"))), ("Sortino ratio", _n(m.get("sortino"))),
            ("Months with a loss", P(m.get("neg_months"))), ("Worst month", _p(m.get("worst_month"))), ("Best month", _p(m.get("best_month")))]
    risk = [x for x in risk if x[1] != "–"]
    cons = [x for x in cons if x[1] != "–"]
    kv = lambda L: "<div class='kv' style='margin-top:12px'>" + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in L) + "</div>"
    # ---------- money flows and assets
    fl = s.get("flows", {})
    fm = [mo for mo in months if mo in fl]
    flows = ""
    if len(fm) >= 6:
        f12 = m.get("flow12_pct")
        tot12 = sum(fl[mo] for mo in fm[-12:])
        flows = (f"<div class='pm-sec' id='flows'><h2>Money coming in and going out</h2><p class='muted'>Each month's change in assets that the month's return does not explain: "
                 f"new money in (green) or withdrawals (red). An estimate from APMI's month-end assets. Last 12 months: {'+' if tot12 >= 0 else '−'}₹{abs(tot12):,.0f} cr"
                 f"{f', {f12:+.0f}% of the assets a year ago' if f12 is not None else ''}.</p>{_bars(fm, [fl[mo] for mo in fm], label='Monthly money in and out')}</div>")
    aum_hist = s.get("aum_hist", {})
    am = sorted(k for k in aum_hist if k >= months[0])
    aum_chart = _line_chart([("Assets (₹ crore)", "var(--teal)", [aum_hist[k] for k in am])], am, fmt=lambda v: f"{v:,.0f}", area=True,
                            label="Assets over time") if len(am) >= 6 else ""
    # ---------- peers
    pr = sorted([p for p in peers if p.get("rank")], key=lambda p: p["rank"])
    if s.get("rank"):
        i = s["rank"] - 1
        near = pr[max(0, i - 4): i + 5]
    else:
        near = pr[:9]
    prow = [[(f"<b>{B.e(p['name'])}</b>" if p is s else f"<a href='{url_s(p)}'>{B.e(p['name'])}</a>") + f"<small>{B.e(p['manager'])}</small>",
             B.tier_badge(p.get("tier")), str(p.get("rank", "–")), _p(p["apmi"].get("r3y")), f"<span{_cls(p['m'].get('alpha'))}>{_p(p['m'].get('alpha'), 1, True)}</span>",
             _p(p["m"].get("max_dd")), _cr(p["aum"])] for p in near]
    peer_tbl = _table(["Strategy", "Rating", "Rank", "3 years a year", "Alpha", "Worst fall", "Assets"], prow)
    bars = "".join(f"<div><span>{PILLARS[k][1]}</span><b style='display:flex;gap:10px;align-items:center'><span class='pm-bar'><i style='width:{v * 100:.0f}%'></i></span>{v * 100:.0f}</b></div>"
                   for k, v in pc.items())
    scat = _scatter([(p["m"]["vol"], p["m"]["alpha"], p.get("tier"), B.e(p["name"]), url_s(p), p is s) for p in pr
                     if p["m"].get("vol") is not None and p["m"].get("alpha") is not None],
                    "Volatility, a year →", "↑ Alpha over its yardstick, a year", label=f"{s['name']} among its peers") if len(pr) >= 5 else ""
    pct_html = (f"<p class='muted' style='font-size:14.5px;margin-top:10px'>Where it stands among {s.get('of', len(pr))} rated {_peer_label(s)} strategies on each "
                f"measure (100 = top of the group).</p><div class='kv' style='margin-top:6px'>{bars}</div>") if bars else ""
    others = [x for x in mgr_all if x is not s]
    oth = ""
    if others:
        oth = ("<div class='pm-sec' id='more'><h2>More from " + B.e(s["manager"]) + "</h2>"
               + _table(["Strategy", "Rating", "1 year", "3 years a year", "Assets"],
                        [[(f"<a href='{url_s(x)}'>{B.e(x['name'])}</a>" if x.get("rated") else B.e(x["name"]))
                          + (f"<small>Not rated: {B.e(x['why_unrated'].split(':')[0].lower())}</small>" if not x.get("rated") and x.get("why_unrated") else ""),
                          B.tier_badge(x.get("tier")) if x.get("tier") else "<span class='muted'>–</span>",
                          _p(x["apmi"].get("r1y")), _p(x["apmi"].get("r3y")), _cr(x["aum"])] for x in sorted(others, key=lambda x: -x["aum"])])
               + (f"<p style='margin-top:10px'><a href='{url_m(s['mslug'])}'>{B.e(s['manager'])}: all strategies and assets →</a></p>" if url_m(s["mslug"]) not in ("/pms/", path) else "") + "</div>")
    nav = ("<nav class='pm-nav' aria-label='On this page'>" + "".join(f"<a href='#{i}'>{t}</a>" for i, t in
           [("returns", "Returns"), ("growth", "Growth"), ("years", "Year by year"), ("months", "Every month"), ("rolling", "Rolling 12 months"),
            ("risk", "Consistency and risk"), ("flows", "Money flows"), ("peers", "Peers")] if (i != "flows" or flows) and (i != "years" or cal_tbl) and (i != "rolling" or roll)) + "</nav>")
    ymix = f" The yardstick is the passive mix that matched its ups and downs most closely: {B.e(yname)}." if s["yard"].get("mix") is not None else ""
    body = (kpis + rating + nav
            + f"<div class='pm-sec' id='returns'><h2>Returns</h2><p class='muted'>As reported to APMI for {_mo(lastm)}: after fees, before tax; periods over a year are a year. "
              f"Compared with {B.e(yname)} over the same months.{ymix}</p>{ret_tbl}</div>"
            + f"<div class='pm-sec' id='growth'><h2>What ₹50 lakh became</h2><p class='muted'>Invested at the end of {_mo(_prev(first))}, month-end values to {_mo(lastm)}, after fees: "
              f"₹{gs[-1]:,.1f} lakh, against ₹{gb[-1]:,.1f} lakh in its yardstick ({'+' if gap >= 0 else '−'}₹{abs(gap):,.1f} lakh).</p>{growth}</div>"
            + (f"<div class='pm-sec' id='years'><h2>Year by year</h2>{cal_tbl}</div>" if cal_tbl else "")
            + f"<div class='pm-sec' id='months'><h2>Every month</h2><p class='muted'>Monthly return (%). Green: ahead of its yardstick that month; red: behind. Deeper colour, bigger gap.</p>{heat}</div>"
            + (f"<div class='pm-sec' id='rolling'><h2>Rolling 12 months</h2><p class='muted'>The return over the 12 months to each month-end, against its yardstick.</p>{roll}</div>" if roll else "")
            + f"<div class='pm-two pm-sec' id='risk'><div><h2>Consistency</h2>{kv(cons)}</div><div><h2>Risk</h2>{kv(risk)}</div></div>"
            + flows
            + (f"<div class='pm-sec'><h2>Assets</h2><p class='muted'>Client money in the strategy at each month-end (₹ crore).</p>{aum_chart}</div>" if aum_chart else "")
            + f"<div class='pm-sec' id='peers'><h2>Against its peers</h2>{pct_html}"
            + (f"<p class='muted' style='font-size:14.5px;margin-top:18px'>Every rated {_peer_label(s)} strategy: alpha over its own yardstick against volatility. "
               f"Up and to the left is better. Tap a dot to open it.</p>{scat}" if scat else "")
            + f"{peer_tbl}<p style='margin-top:10px'><a href='{gurl}'>All rated {GROUP_TXT[g]} strategies →</a></p></div>"
            + oth
            + "<div class='pm-sec'><h2>What this page cannot show</h2><p class='muted'>Holdings, fees and the fee structure (fixed or profit-sharing) are in the "
              "portfolio manager's disclosure document and monthly factsheet, not in APMI's reports. Individual clients' returns differ from the strategy's with the "
              "timing of their money and their fee plan.</p></div>")
    faq = [(f"What return has {s['name']} given?", f"{_p(a['r1y'])} over 1 year and {_p(a['r3y'])} a year over 3 years to {_mo(lastm)}, after fees and before tax, as reported to APMI."
            + (f" Its yardstick, {yname}, returned {_p(yr.get('r3y'))} a year over the same 3 years." if yr.get("r3y") is not None else "")),
           (f"How big is {s['name']}?", f"{_cr(s['aum'])} of client money at the end of {_mo(lastm)}."),
           ("What was its worst fall?", f"{_p(m.get('max_dd'))} from a month-end peak to a month-end low between {_mo(first)} and {_mo(lastm)}; its yardstick's worst fall over the same months was {_p(m.get('bench_dd'))}.")]
    if tier:
        faq.append((f"How is {s['name']} rated?", f"{tier} ({TIER_WORD[tier]}): {s['rank']} of {s['of']} rated {_peer_label(s)} strategies at the quarterly review of data to {_mo(D['review'])}. "
                    "Ratings describe the track record against its own yardstick and peers; they are not a recommendation or a forecast."))
    from build_pages import faq_html, faq_ld
    body += "<div class='pm-sec'>" + faq_html(B, faq) + "</div>"
    title = (f"{s['name']} PMS ({s['manager']}): returns, risk and rating | Aeterna Wealth" if s.get("dup_name")
             else f"{s['name']} PMS: returns, risk and rating | Aeterna Wealth")
    desc = (f"{s['name']} ({s['manager']}): {_p(a['r3y'])} a year over 3 years after fees against {yname}, worst fall {_p(m.get('max_dd'))}, assets {_cr(s['aum'])}"
            + (f"; rated {tier} ({s['rank']} of {s['of']})" if tier else "") + f". Data to {_mo(lastm)}.")
    crumbs = [("PMS", "/pms/"), (f"{g} ratings", gurl)] + ([(s["manager"], url_m(s["mslug"]))] if url_m(s["mslug"]) not in ("/pms/", path) else []) + [(s["name"], path)]
    _wrap(B, path, title, desc, crumbs, hero, body, (faq_ld(faq),))


# ------------------------------------------------------------------ manager page
def manager_page(B, D, mg, L):
    path = f"/pms/{mg['slug']}/"
    rated = [s for s in L if s.get("rated")]
    cards = []
    for s in sorted(L, key=lambda s: -s["aum"]):
        t = s.get("tier")
        spark = ""
        if len(s["r"]) >= 12:
            gg, pts = 1.0, []
            for x in s["r"]:
                gg *= 1 + x / 100
                pts.append(gg)
            lo, hi = min(pts), max(pts)
            P = " ".join(f"{i / (len(pts) - 1) * 240:.1f},{40 - (v - lo) / ((hi - lo) or 1) * 36:.1f}" for i, v in enumerate(pts))
            spark = f"<svg viewBox='0 0 240 44' style='width:100%;height:44px' aria-hidden='true'><polyline fill='none' stroke='var(--teal)' stroke-width='2' points='{P}'/></svg>"
        meta = f"{B.e(s['type'])} · {'discretionary' if s['service'] == 'D' else 'non-discretionary'}" + (f" · {B.e(s.get('style_group'))}" if s.get("style_group") else "")
        head = (f"<div class='row' style='justify-content:space-between;gap:10px;align-items:flex-start'><h3>{B.e(s['name'])}</h3>"
                + (B.tier_badge(t) if t else "") + "</div>")
        stats = (f"<div class='pm-ms'><div><span>Assets</span><b>{_cr(s['aum'])}</b></div><div><span>1 year</span><b>{_p(s['apmi'].get('r1y'))}</b></div>"
                 f"<div><span>3 years, a year</span><b>{_p(s['apmi'].get('r3y'))}</b></div><div><span>vs its yardstick, 3Y</span><b{_cls(s['m'].get('ex3y'))}>{_p(s['m'].get('ex3y'), 1, True)}</b></div></div>")
        foot = (f"<span class='muted'>{t} {TIER_WORD[t]}: {s['rank']} of {s['of']} · open →</span>" if t else
                f"<span class='muted'>Not rated: {B.e((s.get('why_unrated') or 'rated at the next review').split(':')[0].lower())}</span>")
        tag = "a" if s.get("rated") else "div"
        href = f" href='{url_s(s)}'" if s.get("rated") else ""
        cards.append(f"<{tag} class='pm-card'{href}>{head}<span class='muted'>{meta}</span>{spark}{stats}{foot}</{tag}>")
    tot = sum(s["aum"] for s in L)
    hist = defaultdict(float)
    for s in L:
        for mo, v in s.get("aum_hist", {}).items():
            if mo >= D["first"]:
                hist[mo] += v
    hm = sorted(hist)
    chart = _line_chart([("Assets in these strategies (₹ crore)", "var(--teal)", [hist[k] for k in hm])], hm, fmt=lambda v: f"{v:,.0f}", area=True,
                        label=f"{mg['name']} assets over time") if len(hm) >= 6 else ""
    lede = (f"{B.e(mg['name'])} manages {_cr(mg['aum_all'])} across {mg['n_all']} PMS strategies reported to APMI for {_mo(D['as_of'])}. "
            f"{len(L)} of them hold ₹100 crore or more and are shown here; {len(rated)} have a long enough discretionary record to rate.")
    hero = _hero(B, "Portfolio manager", mg["name"], lede, _stamp(D), art="lines")
    best = min((s for s in rated if s.get("rank")), key=lambda s: s["rank"] / s["of"], default=None)
    kp = _kpis([("Assets, all strategies", _cr(mg["aum_all"]), f"{mg['n_all']} strategies"), ("Shown here (₹100 cr+)", str(len(L)), _cr(tot)),
                ("Rated", str(len(rated)), "discretionary, 3-year record"),
                ("Highest rated", (best.get("tier") or "–") if best else "–", B.e(best["name"]) if best else "none rated")])
    body = (kp + f"<div class='pm-sec'><h2>Strategies</h2><p class='muted'>Largest first. Rated strategies open to their full record.</p><div class='pm-cards'>{''.join(cards)}</div></div>"
            + (f"<div class='pm-sec'><h2>Assets over time</h2><p class='muted'>Month-end client money in the strategies above.</p>{chart}</div>" if chart else ""))
    title = f"{mg['name']} PMS: every strategy's returns and rating | Aeterna Wealth"
    desc = f"{mg['name']}: {len(L)} PMS strategies over ₹100 crore, {_cr(tot)} in them; returns after fees, risk and ratings from APMI data to {_mo(D['as_of'])}."
    _wrap(B, path, title, desc, [("PMS", "/pms/"), (mg["name"], path)], hero, body)


# ------------------------------------------------------------------ group pages
def _rank_table(B, L):
    head = ["<th class='l'>Strategy</th>", "<th data-k>Rating</th>", "<th data-k>Rank</th>", "<th>Yardstick</th>", "<th data-k>3 years<br>a year</th>",
            "<th data-k>vs yardstick<br>3 years</th>", "<th data-k>Alpha<br>a year</th>", "<th data-k>Info<br>ratio</th>", "<th data-k>12-month<br>spells ahead</th>",
            "<th data-k>Worst<br>fall</th>", "<th data-k>Assets</th>"]
    TV = {"A+": 4, "A": 3, "B": 2, "C": 1}
    rows = []
    for s in sorted(L, key=lambda s: ((s.get("peer_group") or ""), s.get("rank") or 9999)):
        m = s["m"]
        v = lambda x: "" if x is None else f"{x:.4f}"
        cells = [f"<td class='l'><a href='{url_s(s)}'>{B.e(s['name'])}</a><small>{B.e(s['manager'])}</small></td>",
                 f"<td class='num' data-v='{TV.get(s.get('tier'), 0)}'>{B.tier_badge(s.get('tier'))}</td>",
                 f"<td class='num' data-v='{-(s.get('rank') or 9999) / max(1, s.get('of') or 1):.4f}'>{s.get('rank', '–')}<small>of {s.get('of', '–')}</small></td>",
                 f"<td class='num' style='white-space:nowrap'>{B.e(_ysh(s))}</td>",
                 f"<td class='num' data-v='{v(s['apmi'].get('r3y'))}'>{_p(s['apmi'].get('r3y'))}</td>",
                 f"<td class='num' data-v='{v(m.get('ex3y'))}'><span{_cls(m.get('ex3y'))}>{_p(m.get('ex3y'), 1, True)}</span></td>",
                 f"<td class='num' data-v='{v(m.get('alpha'))}'><span{_cls(m.get('alpha'))}>{_p(m.get('alpha'), 1, True)}</span></td>",
                 f"<td class='num' data-v='{v(m.get('ir'))}'>{_n(m.get('ir'))}</td>",
                 f"<td class='num' data-v='{v(m.get('hit_12m'))}'>{_p(None if m.get('hit_12m') is None else m['hit_12m'] * 100, 0)}</td>",
                 f"<td class='num' data-v='{v(m.get('max_dd'))}'>{_p(m.get('max_dd'))}</td>",
                 f"<td class='num' data-v='{s['aum']:.2f}'>{_cr(s['aum'])}</td>"]
        srch = B.e((s["name"] + " " + s["manager"]).lower())
        rows.append(f"<tr data-s='{srch}' data-g='{B.e(s.get('peer_group') or '')}' data-t='{s.get('tier') or ''}'>{''.join(cells)}</tr>")
    return f"<div class='tablewrap' style='margin-top:14px'><table class='pm-t'><thead><tr>{''.join(head)}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"


def group_page(B, D, g, L):
    path = f"/pms/ratings/{GROUP_SLUG[g]}/"
    cnt = {t: sum(s.get("tier") == t for s in L) for t in ("A+", "A", "B", "C")}
    eq = g == "Equity"
    sub = sorted({s.get("peer_group") for s in L if s.get("peer_group")})
    if eq:
        lede = (f"{len(L)} discretionary equity PMS strategies with ₹100 crore or more and 3 years of reported returns, each measured against the index it "
                f"tracks most closely and ranked within its style: large and multi cap ({sum(s.get('peer_group') == 'Large and multi cap' for s in L)}) or mid and small cap "
                f"({sum(s.get('peer_group') == 'Mid and small cap' for s in L)}).")
    elif g == "Debt":
        lede = (f"{len(L)} discretionary debt PMS strategies with ₹100 crore or more and 3 years of reported returns, measured against the median high-quality "
                "bond mutual fund (corporate bond, banking and PSU, short duration): what an investor would otherwise hold.")
    else:
        lede = (f"{len(L)} discretionary hybrid and multi-asset PMS strategies with ₹100 crore or more and 3 years of reported returns, each measured against "
                "the passive mix of Nifty 500 TRI and bond funds that matched its ups and downs most closely.")
    hero = _hero(B, "PMS ratings", f"{g} PMS strategies, rated", lede, _stamp(D), art="dots")
    med = lambda v: sorted(v)[len(v) // 2] if v else None
    exs = [s["m"].get("ex3y") for s in L if s["m"].get("ex3y") is not None]
    beat = sum(x > 0 for x in exs)
    kp = _kpis([("Rated strategies", str(len(L)), " · ".join(f"{t} {cnt[t]}" for t in cnt)),
                ("Ahead of their yardstick, 3 years", f"{beat} of {len(exs)}", f"{beat / max(1, len(exs)) * 100:.0f}%, after fees"),
                ("Typical 3-year return", _p(med([s['apmi']['r3y'] for s in L])), "a year, median"),
                ("Typical worst fall", _p(med([s['m'].get('max_dd') for s in L if s['m'].get('max_dd') is not None])), "median")])
    tiers = f"<div style='margin-top:22px'>{_tierbar(L)}</div>"
    scat = _scatter([(s["m"]["vol"], s["m"]["alpha"], s.get("tier"), B.e(s["name"]), url_s(s), False) for s in L
                     if s["m"].get("vol") is not None and s["m"].get("alpha") is not None],
                    "Volatility, a year →", "↑ Alpha over its yardstick, a year", label=f"{g} PMS strategies: alpha against volatility")
    seg_g = ("<div class='pm-seg' data-f='g' role='group' aria-label='Style'><button type='button' data-v='' aria-pressed='true'>All styles</button>"
             + "".join(f"<button type='button' data-v='{B.e(x)}' aria-pressed='false'>{B.e(x)}</button>" for x in sub) + "</div>") if len(sub) > 1 else ""
    seg_t = ("<div class='pm-seg' data-f='t' role='group' aria-label='Rating'><button type='button' data-v='' aria-pressed='true'>All</button>"
             + "".join(f"<button type='button' data-v='{t}' aria-pressed='false'>{t}</button>" for t in ("A+", "A", "B", "C")) + "</div>")
    tools = (f"<div class='pm-tools'><input id='pmQ' type='search' placeholder='Search strategy or manager' aria-label='Search strategy or manager'>{seg_g}{seg_t}"
             f"<span class='muted' style='font-size:13.5px'><b id='pmN'>{len(L)}</b> shown · tap a column to sort</span></div>")
    body = (kp + tiers
            + f"<div class='pm-sec'><h2>Return over the yardstick against risk</h2><p class='muted'>Each dot is a strategy: alpha (its return over its own yardstick "
              f"with market exposure removed) against volatility. Colour is the rating. Up and to the left is better. Tap a dot to open it.</p>{scat}</div>"
            + f"<div class='pm-sec' id='table'><h2>Every rated strategy</h2><p class='muted'>Ranked within {'its style group' if eq else 'the group'}; the rank is out of the "
              f"number under it. Alpha and the 12-month spells are measured against each strategy's own yardstick.</p>{tools}{_rank_table(B, L)}</div>")
    others = "".join(f"<a class='pm-chip' href='/pms/ratings/{GROUP_SLUG[x]}/'>{x} ratings →</a>" for x in GROUP_SLUG if x != g)
    body += f"<div class='pm-chips' style='margin-top:18px'>{others}<a class='pm-chip' href='/pms/how-pms-returns-are-measured/#rating'>How we rate →</a><a class='pm-chip' href='/pms/'>PMS research home →</a></div>"
    title = f"{g} PMS ratings: {len(L)} strategies ranked against their own yardstick ({_mo(D['as_of'])}) | Aeterna Wealth"
    desc = f"{len(L)} {GROUP_TXT[g]} PMS strategies ranked on return over their own yardstick, consistency and risk; APMI data to {_mo(D['as_of'])}."
    _wrap(B, path, title, desc, [("PMS", "/pms/"), (f"{g} ratings", path)], hero, body, js=SORT_JS)


# ------------------------------------------------------------------ hub
def hub_page(B, D, S, managers):
    path = "/pms/"
    rated = [s for s in S if s.get("rated") and s.get("tier")]
    I = D.get("industry", {})
    eqr = [s for s in rated if s["group"] == "Equity"]
    exs = [s["m"].get("ex3y") for s in eqr if s["m"].get("ex3y") is not None]
    beat = sum(x > 0 for x in exs)
    lede = (f"Every PMS strategy in India reports its returns to APMI each month. We read all {D['n_all']:,} of them, show the {len(S)} with ₹100 crore or more, "
            f"and rate the {len(rated)} discretionary ones with 3 years of record, each against a yardstick that fits it: the right style index for equity, "
            "bond funds for debt, a matched mix for hybrid.")
    hero = _hero(B, "PMS research", "PMS returns, risk and ratings", lede, _stamp(D), art="dots", chips=
                 "<div class='pm-chips'>" + "".join(f"<a class='pm-chip' href='/pms/ratings/{GROUP_SLUG[g]}/'>{g} ratings →</a>" for g in GROUP_SLUG)
                 + "<a class='pm-chip' href='#managers'>All portfolio managers →</a></div>")
    kp = _kpis([("Money in PMS", _crs(D["aum_all"]), f"{D['n_all']:,} strategies"), ("Shown here", str(len(S)), "₹100 crore or more"),
                ("Rated", str(len(rated)), "discretionary, 3-year record"),
                ("Equity strategies ahead of their index", f"{beat} of {len(exs)}", "over 3 years, after fees")])
    ah = I.get("aum_hist", {})
    am = sorted(ah)
    aum_chart = _line_chart([("All PMS strategies", "var(--teal)", [ah[k] for k in am])], am, fmt=lambda v: f"₹{v / 1e5:,.2f}L cr", area=True, h=230,
                            label="Money in PMS over time", small=True) if len(am) >= 6 else ""
    sb = I.get("size_bands", [])
    small = sum(x[1] for x in sb[:2]) / (sum(x[1] for x in sb) or 1) * 100 if sb else 0
    big = sum(x[2] for x in sb[2:]) / (sum(x[2] for x in sb) or 1) * 100 if sb else 0
    SZ = ["var(--t-u)", "var(--t-c)", "var(--t-b)", "var(--t-a)", "var(--t-ap)"]
    bands = C.split_bar([("Strategies", [(x[0], x[1]) for x in sb]), ("Money", [(x[0], x[2]) for x in sb])], SZ, label="Strategies and money by size", bare=True) if sb else ""
    at = I.get("aum_type", {})
    mix = C.split_bar([("Money", sorted(((k, v) for k, v in at.items()), key=lambda x: -x[1]))], ["var(--teal)", "var(--brass)", "var(--t-a)", "var(--t-b)"],
                      label="Money by asset class", bare=True) if at else ""
    market = (f"<div class='pm-sec' id='market'><h2>The PMS market in one view</h2><p class='muted'>Client money in every strategy APMI reports: "
              f"{_crs(ah[am[0]]) if am else '–'} in {_mo(am[0]) if am else ''}, {_crs(ah[am[-1]]) if am else '–'} in {_mo(am[-1]) if am else ''}. Hover or tap the chart for any month.</p>"
              f"<div class='pm-two' style='grid-template-columns:1.4fr 1fr;align-items:stretch'><div>{aum_chart}</div>"
              f"<div><div class='ch sm' style='height:calc(100% - 14px);box-sizing:border-box'><p class='pm-sub' style='margin:2px 0 0'><b>Most strategies are small; most money is not.</b> "
              f"{small:.0f}% of discretionary equity strategies manage under ₹100 crore, but {big:.0f}% of the money is in the ones above it, which is where we draw our line.</p>"
              f"{bands}"
              f"<p class='pm-sub' style='margin:16px 0 0'><b>By asset class</b> (all strategies)</p>{mix}</div></div></div></div>")
    scat = _scatter([(s["m"]["vol"], s["m"]["alpha"], s.get("tier"), B.e(s["name"]), url_s(s), False) for s in eqr
                     if s["m"].get("vol") is not None and s["m"].get("alpha") is not None],
                    "Volatility, a year →", "↑ Alpha over its own index, a year", label="Rated equity PMS: alpha against volatility")
    lead = [s for s in eqr if s.get("tier") in ("A+", "A")]
    behind = sorted(1 - s["m"]["hit_m"] for s in lead if s["m"].get("hit_m") is not None)
    bshare = behind[len(behind) // 2] * 100 if behind else 40
    rec = (f"<div class='pm-sec' id='record'><h2>What the record says</h2><p class='muted'>{beat} of {len(exs)} rated equity strategies beat their own index over 3 years after fees. "
           "Each dot is one of them: what it earned over its index once market exposure is taken out (alpha), against how much it swung. "
           f"Even the A and A+ strategies trailed their index in about {bshare:.0f}% of months: a PMS is judged over years, not quarters.</p>"
           f"{scat}<p class='pm-note' style='margin-top:10px'>Only strategies that grew past ₹100 crore and are still reporting; ones that shrank or closed are not here, "
           "so the industry as a whole did less well.</p></div>")
    pg_cards = []
    for key, label, url, desc in (("Large and multi cap", "Large and multi cap equity", "/pms/ratings/equity/#large-and-multi-cap", "Against Nifty 50, Nifty 500 or Multicap 50:25:25"),
                                  ("Mid and small cap", "Mid and small cap equity", "/pms/ratings/equity/#mid-and-small-cap", "Against Nifty Midcap 150 or Smallcap 250"),
                                  ("Hybrid and multi-asset", "Hybrid and multi-asset", "/pms/ratings/hybrid-and-multi-asset/", "Against a matched equity and bond mix"),
                                  ("Debt", "Debt", "/pms/ratings/debt/", "Against the median high-quality bond fund")):
        L = sorted([s for s in rated if (s.get("peer_group") or s["group"]) == key], key=lambda s: s["rank"])
        if not L:
            continue
        top = "".join(f"<li><span>{s['rank']}</span><a href='{url_s(s)}'>{B.e(s['name'])}<small>{B.e(s['manager'])}</small></a>{B.tier_badge(s.get('tier'))}</li>" for s in L[:5])
        pg_cards.append(f"<div class='pm-card'><span class='pm-eyebrow'>{len(L)} rated</span><h3>{label}</h3><span class='muted'>{desc}</span>{_tierbar(L)}"
                        f"<ul class='pm-mini'>{top}</ul><a href='{url}' style='font-weight:600;font-size:14px;margin-top:auto'>See all {len(L)} →</a></div>")
    groups = (f"<div class='pm-sec' id='groups'><h2>Top of each peer group</h2><p class='muted'>Strategies are only compared with others of the same kind, "
              f"each against its own yardstick. Rated at the quarterly review of data to {_mo(D['review'])}.</p><div class='pm-cards'>{''.join(pg_cards)}</div></div>")
    how = ("<div class='pm-sec' id='how'><h2>How we rate, in three steps</h2><div class='pm-steps'>"
           "<div>{I1}<h3>A fair yardstick</h3><p>Equity against the style index it tracks most closely; debt against bond funds; hybrid against a matched mix. A small-cap manager has to beat small caps.</p></div>"
           "<div>{I2}<h3>Skill, consistency, risk</h3><p>Alpha and information ratio, how often it was ahead, and how it fell: the measures that lined up best with the next year in our test. Not last year's return.</p></div>"
           "<div>{I3}<h3>Reviewed quarterly</h3><p>Numbers update monthly; ratings every quarter, with a buffer so a strategy does not flip on one month. Large withdrawals count at once.</p></div>"
           "</div><p style='margin-top:12px'><a href='/pms/how-pms-returns-are-measured/'>The full method, the evidence and its limits →</a></p></div>").replace("{I1}", ILL.icon("scale")).replace("{I2}", ILL.icon("dots")).replace("{I3}", ILL.icon("calendar"))
    shown_m = [mg for mg in managers if MLINK.get(mg["slug"])]
    by_l = defaultdict(list)
    for mg in shown_m:
        c = mg["name"][:1].upper()
        by_l[c if c.isalpha() else "#"].append(mg)
    dirx = "".join(f"<h4>{c}</h4>" + "".join(f"<div data-s='{B.e(mg['name'].lower())}'><a href='{url_m(mg['slug'])}'>{B.e(mg['name'])}</a></div>" for mg in by_l[c]) for c in sorted(by_l))
    bigm = sorted(shown_m, key=lambda mg: -mg.get("aum_all", 0))[:12]
    nrated = defaultdict(int)
    for s_ in rated:
        nrated[s_["mslug"]] += 1
    mcards = "".join(f"<a class='pm-card' href='{url_m(mg['slug'])}' style='gap:4px'><b style='font-weight:600'>{B.e(mg['name'])}</b>"
                     f"<span class='muted'>{_crs(mg['aum_all'])} · {mg['n_all']} strategies · {nrated[mg['slug']]} rated</span></a>" for mg in bigm)
    mgr = (f"<div class='pm-sec' id='managers'><h2>Portfolio managers</h2><p class='muted'>{len(shown_m)} managers have at least one rated strategy. "
           "The largest by money managed, then every one A to Z. Managers with one rated strategy link straight to it.</p>"
           f"<div class='pm-cards' style='grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px'>{mcards}</div>"
           f"<details class='faq' style='margin-top:16px'><summary>All {len(shown_m)} portfolio managers, A to Z</summary>"
           "<div class='pm-tools'><input id='pmM' type='search' placeholder='Find a portfolio manager' aria-label='Find a portfolio manager'></div>"
           f"<div class='pm-dir' id='pmDir'>{dirx}</div></details></div>")
    mjs = ("<script>(function(){var q=document.getElementById('pmM'),d=document.getElementById('pmDir');if(!q||!d)return;q.addEventListener('input',function(){var s=q.value.toLowerCase();"
           "[].forEach.call(d.querySelectorAll('div[data-s]'),function(x){x.hidden=!!s&&x.getAttribute('data-s').indexOf(s)<0});"
           "[].forEach.call(d.querySelectorAll('h4'),function(h){var n=h.nextElementSibling,v=false;while(n&&n.tagName!=='H4'){if(!n.hidden)v=true;n=n.nextElementSibling}h.hidden=!v})})})();</script>")
    nav = ("<nav class='pm-nav' aria-label='On this page'>" + "".join(f"<a href='#{i}'>{t}</a>" for i, t in
           [("market", "The market"), ("record", "The record"), ("groups", "Peer groups"), ("how", "How we rate"), ("managers", "Managers"), ("explained", "PMS explained")]) + "</nav>")
    body = kp + nav + market + rec + groups + how + mgr
    X = getattr(B, "INVEST_EXTRA", {}).get("pms")
    ld = ()
    if X:
        from build_pages import faq_ld
        body += (X["css"] + "<div class='pm-sec' id='explained'><h2>PMS explained</h2><p class='muted'>What a PMS is, who it suits, what it costs and how it is taxed.</p>"
                 "<div class='inv-facts' style='margin-top:16px'>" + X["facts"] + "</div>"
                 + f"<div style='margin-top:20px'>{X['secs']}<div class='inv-sec'><h2>How we work with you</h2><div class='body'><ol class='inv-steps'>{X['steps']}</ol></div></div>"
                 + "<div class='inv-sec'><h2>Common questions</h2><div class='body'>"
                 + "".join(f"<details class='faq'><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>" for q, a in X["faq"]) + "</div></div></div></div>")
        ld = (faq_ld(X["faq"]),)
    title = f"PMS returns and ratings: {len(rated)} strategies against their own yardstick ({_mo(D['as_of'])}) | Aeterna Wealth"
    desc = (f"PMS performance for {len(S)} strategies over ₹100 crore: returns after fees, risk, consistency and ratings against the right yardstick for each "
            f"(style index, bond funds or a matched mix), from APMI data to {_mo(D['as_of'])}.")
    _wrap(B, path, title, desc, [("PMS", "/pms/")], hero, body, ld, js=mjs)


# ------------------------------------------------------------------ method
def method_page(B, D):
    path = "/pms/how-pms-returns-are-measured/"
    S = D["strategies"]
    rated = [s for s in S if s.get("rated") and s.get("tier")]
    yc = defaultdict(int)
    for s in rated:
        if s["group"] == "Equity":
            yc[s["yard"]["name"]] += 1
    ytab = _hbars(sorted(yc.items(), key=lambda x: -x[1]), lambda v: f"{v:.0f} strategies", label="Equity strategies by fitted yardstick")
    wtab = lambda W: "<div class='pm-pil' style='margin-top:12px'>" + "".join(
        f"<div><span>{PILLARS[k][1]}</span><span class='pm-bar'><i style='width:{abs(w) * 4}%'></i></span><b>{abs(w)}</b></div>" for k, w in W) + "</div>"
    W_EQ = [("alpha", 20), ("ir", 15), ("hit_m", 15), ("hit_12m", 10), ("half_min", 10), ("down_capture", 10), ("vol", 10), ("rel_dd", 10)]
    W_DB = [("ex_ann", 25), ("sortino", 20), ("ir", 15), ("hit_12m", 15), ("max_dd", 15), ("vol", 10)]
    W_HY = [("alpha", 20), ("ir", 15), ("hit_12m", 15), ("sortino", 15), ("rel_dd", 15), ("down_capture", 10), ("vol", 10)]
    hero = _hero(B, "Method", "How PMS returns are measured, and how we rate", "What the numbers on our PMS pages mean, the yardstick each strategy is held to, "
                 "how the score is built, how often ratings change, and what the evidence does and does not show.", _stamp(D), art="rings", chips=
                 "<div class='pm-chips'><a class='pm-chip' href='#yardstick'>Yardsticks</a><a class='pm-chip' href='#rating'>The score</a>"
                 "<a class='pm-chip' href='#review'>Review cycle</a><a class='pm-chip' href='#evidence'>Evidence</a></div>")
    body = f"""<div class='prose' style='max-width:860px'>
<h2>Where the numbers come from</h2><p>SEBI requires every portfolio manager to report each strategy ("investment approach") to APMI, the Association of Portfolio Managers in India, every month: client money at the month end and returns over 1, 3 and 6 months, 1 to 5 years and since launch. APMI publishes them. We read every month's report from April 2023, when the reports became complete, to {_mo(D['as_of'])}.</p>
<h2>What the returns mean</h2><ul><li><b>Time-weighted (TWRR):</b> the return of the strategy itself, not affected by when clients added or took out money. Your own return differs with your timing.</li>
<li><b>After all fees and expenses</b>, including any profit share, and <b>before your tax</b>. In a PMS you own the shares, so you pay capital gains tax on every sale the manager makes.</li>
<li><b>Periods over a year are annualised.</b></li><li><b>Discretionary</b> strategies: the manager decides and trades for every client in the same model portfolio. In <b>non-discretionary</b> ones each client approves each trade, so the reported return depends on the clients' choices; we list them but do not rate them.</li></ul>
<h2 id='yardstick'>One yardstick per asset class</h2><p>A strategy is only as good as what it is compared with. A small-cap manager who beat Nifty 500 during a small-cap rally showed no skill; a debt strategy compared with a share index tells you nothing. So each asset class has its own yardstick, read from the strategy's own returns (APMI gives no style labels):</p>
<ul><li><b>Equity:</b> the style index the strategy tracked most closely over its record (the lowest tracking error) among Nifty 50, Nifty 500, Nifty 500 Multicap 50:25:25, Nifty Midcap 150 and Nifty Smallcap 250 TRI. Strategies are then ranked within their style: large and multi cap, or mid and small cap.</li>
<li><b>Debt:</b> the median high-quality bond mutual fund (corporate bond, banking and PSU, short duration) month by month: what the investor would otherwise hold.</li>
<li><b>Hybrid and multi-asset:</b> the passive mix of Nifty 500 TRI and that bond yardstick that matched the strategy's ups and downs most closely, in 5% steps (for example 60% equity, 40% bonds). A strategy with more equity does not win just because shares rose.</li></ul>
<p>Which index the {sum(yc.values())} rated equity strategies fitted:</p></div>
{ytab}
<div class='prose' style='max-width:860px'>
<h2 id='rating'>The score</h2><p>Each measure is turned into a percentile within the peer group (100 = top) and blended with the weights below. Rated: discretionary strategies with ₹100 crore or more (kept until they fall below ₹75 crore), a 3-year return and at least 24 months of monthly record.</p></div>
<div class='pm-steps'>
<div>{ILL.icon('growth')}<h3>Equity</h3><p>Skill 70, risk 30</p>{wtab(W_EQ)}</div><div>{ILL.icon('shield')}<h3>Debt</h3><p>Return, downside and steadiness</p>{wtab(W_DB)}</div><div>{ILL.icon('scale')}<h3>Hybrid and multi-asset</h3><p>Return over its mix, with protection</p>{wtab(W_HY)}</div></div>
<div class='prose' style='max-width:860px'>
<h2>Tiers</h2><ul><li><b>A+ Leading:</b> top 10% of the peer group and a score of 70 or more.</li><li><b>A Strong:</b> top 30% and 55 or more.</li><li><b>B In line:</b> the middle.</li><li><b>C Lagging:</b> bottom 30%.</li></ul>
<p>A or A+ also needs a lead over the yardstick both over 3 years and over the whole record (positive alpha); otherwise B. A strategy whose clients withdrew more than 30% of its money in the last 12 months is held at B, with the reason shown.</p>
<h2 id='review'>How often ratings change</h2><p>Returns, risk figures and money flows update every month, when APMI publishes (we load each month on the 20th). <b>Ratings are reviewed quarterly</b>, on data to March, June, September and December. At each review a strategy keeps its tier unless it has moved clearly past the boundary: 5 percentile points and 5 score points. In our test, re-rating every month would have changed the average strategy's tier about twice a year; quarterly with this buffer, about once every 16 months. Material events do not wait: the withdrawal rule and the ₹75 crore floor apply every month. The last review used data to {_mo(D['review'])}; the next uses data to {_mo(D['next_review'])}.</p>
<h2 id='evidence'>What the evidence says</h2><p>We tested every measure on every discretionary equity strategy with ₹100 crore or more at each month-end from March 2025 to March 2026 (about 300 strategies each time, including ones that later shrank or closed), against the next 12 months' return over its index.</p>
<ul><li>The measures we weight most (alpha, information ratio, share of months and of 12-month spells ahead) lined up with the next year at every one of the 13 test dates.</li>
<li>Last year's return, what most PMS rankings use, lined up least, and against Nifty 500 not at all.</li><li>Past volatility and worst falls lined up strongly with the next year's worst fall: risk persists, which is why the score keeps a risk pillar.</li>
<li>Strategies in the top 30% by our score went on to beat their index over the next 12 months 64% of the time, by a median of 2 points a year; the bottom 30% trailed slightly.</li></ul>
<p><b>Honest limit:</b> 13 overlapping test dates are about one and a half independent years in one market. This shows the measures are sensible; it does not show they forecast. Our ratings describe track records.</p>
<h2>What it cannot tell you</h2><ul><li>APMI has 43 months of complete data: one long rise and one fall in Indian shares. Strategies that closed drop out of the reports.</li><li>No holdings, fees or style labels are in APMI's data. Credit strategies earn part of their lead over the high-quality bond yardstick by taking credit risk, which the risk measures only partly capture.</li><li>Your return differs from the strategy's with your timing and fee plan. Read the disclosure document, and judge a PMS over years.</li></ul></div>"""
    _wrap(B, path, "How PMS returns are measured and how we rate PMS strategies | Aeterna Wealth",
          "What APMI's PMS returns mean (time-weighted, after fees, before tax), the yardstick for each asset class (style index, bond funds, matched mix), the score, quarterly reviews and the evidence.",
          [("PMS", "/pms/"), ("How we measure", path)], hero, body)


# ------------------------------------------------------------------ AIF
def aif_page(B):
    path = "/aif/"
    X = getattr(B, "INVEST_EXTRA", {}).get("aif")
    cats = ("<div class='pm-steps'>"
            "<div>{I4}<h3>Category I</h3><p>Start-ups, early-stage and social ventures, SME and infrastructure funds. Usually closed-ended, 7–10 years, money called in stages. Income passes through to investors for tax.</p></div>"
            "<div>{I5}<h3>Category II</h3><p>Private equity, private credit, real estate and funds of funds: everything that is not I or III, with no borrowing beyond day-to-day needs. Closed-ended, often 5–8 years; income passes through.</p></div>"
            "<div>{I6}<h3>Category III</h3><p>Listed-market strategies that can trade actively and use leverage or derivatives: long-only, long-short. Can be open-ended. Taxed in the fund, not in your hands.</p></div></div>").replace("{I4}", ILL.icon("growth")).replace("{I5}", ILL.icon("layers")).replace("{I6}", ILL.icon("bars"))
    cmp_ = _table(["", "Mutual fund", "PMS", "AIF"],
                  [["Minimum", "₹100 or less", "₹50 lakh", "₹1 crore (most)"], ["You own", "Units of a pooled fund", "The shares, in your own demat", "Units of a pooled fund"],
                   ["Returns published", "Every day (NAV)", "Every month (APMI)", "No; category averages twice a year"],
                   ["Exit", "Any day", "Any day (exit load in early years)", "Often locked in for years"],
                   ["Tax on the manager's trades", "Nothing until you sell", "Yours, on every sale", "Cat I/II: yours; Cat III: in the fund"]])
    mine = """<div class='inv-sec'><h2>Why we do not rank AIFs</h2><div class='body'><p>No one publishes returns for individual AIF schemes. SEBI's benchmarking framework (CRISIL, NSE and others) gives each AIF its own report privately and publishes only category-level averages twice a year, for March and September. Private equity and credit funds are also valued only occasionally, and their returns depend on when each investment is sold. A ranking from public data would be guesswork, so we do not make one.</p></div></div>
<div class='inv-sec'><h2>What to ask before investing</h2><div class='body'><ul><li>The scheme's returns since its first close, as an IRR, against its category benchmark from the benchmarking agency's report.</li><li>The fees: management fee, set-up costs, the hurdle rate and the manager's share of profits.</li><li>The lock-in and when the fund expects to return money; whether you can exit early.</li><li>How your returns are taxed: Category I and II pass income through to investors; Category III is taxed in the fund.</li></ul><p>For listed-equity strategies with monthly reported returns, see our <a href='/pms/'>PMS returns and ratings</a>.</p></div></div>"""
    hero = _hero(B, "Alternative investments", "Alternative investment funds (AIFs)",
                 "What they are, how SEBI classifies them, how they compare with mutual funds and PMS, what they cost, and what you can and cannot find out before investing.",
                 art="rings", chips="<div class='pm-chips'><a class='pm-chip' href='#categories'>The three categories</a><a class='pm-chip' href='#compare'>AIF, PMS or mutual fund</a>"
                       "<a class='pm-chip' href='#ask'>What to ask</a><a class='pm-chip' href='/pms/'>PMS ratings →</a></div>")
    body = (f"<div class='pm-sec' id='categories'><h2>The three categories</h2><p class='muted'>SEBI's AIF Regulations, 2012 sort every fund into one of three categories, "
            f"which decides what it may invest in, whether it may borrow and how it is taxed.</p>{cats}</div>"
            f"<div class='pm-sec' id='compare'><h2>AIF, PMS or mutual fund</h2><p class='muted'>The same idea, a professional managing your money, under three sets of rules.</p>{cmp_}</div>")
    ld = ()
    if X:
        from build_pages import faq_ld
        import re as _re
        secs = _re.sub(r"<div class='inv-sec'><h2>The three categories</h2>.*?</div></div>", "", X["secs"], count=1, flags=_re.S)   # shown above as cards
        body += (X["css"] + "<div class='pm-sec'><h2>AIFs in brief</h2><div class='inv-facts' style='margin-top:16px'>" + X["facts"] + "</div></div><div class='pm-sec' id='ask'>" + secs + mine
                 + f"<div class='inv-sec'><h2>How we work with you</h2><div class='body'><ol class='inv-steps'>{X['steps']}</ol></div></div>"
                 + "<div class='inv-sec'><h2>Common questions</h2><div class='body'>"
                 + "".join(f"<details class='faq'><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>" for q, a in X["faq"]) + "</div></div></div>")
        ld = (faq_ld(X["faq"]),)
    else:
        body += "<div class='pm-sec' id='ask'>" + mine + "</div>"
    _wrap(B, path, "AIFs in India: Category I, II and III, minimum ₹1 crore, fees and tax | Aeterna Wealth",
          "Alternative investment funds explained: SEBI's Category I, II and III, how they compare with PMS and mutual funds, the ₹1 crore minimum, lock-ins, fees, tax and what to ask before investing.",
          [("AIFs", path)], hero, body, ld)


def build(B, urls):
    p = B.S / "data" / "pms.json"
    if not p.exists():
        return
    D = json.loads(p.read_text(encoding="utf-8"))
    D.setdefault("review", D["as_of"])
    D.setdefault("next_review", D["as_of"])
    S = D["strategies"]
    from collections import Counter
    nc = Counter(s["name"].lower() for s in S if s.get("rated"))
    for s in S:
        s["dup_name"] = nc[s["name"].lower()] > 1
    by_m = defaultdict(list)
    for s in S:
        by_m[s["mslug"]].append(s)
    MLINK.clear()
    for mg in D["managers"]:
        L = by_m[mg["slug"]]
        rated = [s for s in L if s.get("rated")]
        # one page per thing: a manager page only when it covers 2+ strategies; otherwise its one rated strategy's page is the page
        mg["has_page"] = len(L) >= 2 and bool(rated)
        if mg["has_page"]:
            MLINK[mg["slug"]] = f"/pms/{mg['slug']}/"
        elif len(rated) == 1:
            MLINK[mg["slug"]] = url_s(rated[0])
    for g_ in GROUP_SLUG:
        L = [s for s in S if s["group"] == g_ and s.get("rated")]
        if L:
            group_page(B, D, g_, L)
            urls.append((f"/pms/ratings/{GROUP_SLUG[g_]}/", "monthly", "0.7"))
    for s in S:
        if s.get("rated"):
            strategy_page(B, D, s, [x for x in S if (x.get("peer_group") or x["group"]) == (s.get("peer_group") or s["group"]) and x.get("rated")], by_m[s["mslug"]])
            urls.append((url_s(s), "monthly", "0.6"))
    for mg in D["managers"]:
        if mg["has_page"]:
            manager_page(B, D, mg, by_m[mg["slug"]])
            urls.append((f"/pms/{mg['slug']}/", "monthly", "0.5"))
    hub_page(B, D, S, D["managers"])
    method_page(B, D)
    aif_page(B)
    urls += [("/pms/", "monthly", "0.8"), ("/pms/how-pms-returns-are-measured/", "monthly", "0.5"), ("/aif/", "monthly", "0.5")]
