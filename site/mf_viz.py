"""Mutual fund page visuals in the same language as the PMS pages: category KPI strip and tier bar, the peer dot chart
(3-year return over the index against volatility, every plan in the peer group), the rating dial, and section navs.
Uses site/charts.py (interactive SVG). Standard library only."""
import math

import charts as C

CSS = """<style>
.mv-hero{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:32px;align-items:center}@media (max-width:900px){.mv-hero{grid-template-columns:1fr}}
.mv-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;margin-top:22px}
.mv-kpis div{background:var(--surface);padding:15px 17px}.mv-kpis>div>span{display:block;color:var(--ink-2);font-size:13px}.mv-kpis b{display:block;font:500 23px/1.25 var(--f-mono);margin-top:4px}
.mv-kpis small{display:block;color:var(--ink-3);font-size:12.5px;margin-top:2px}
.mv-tbar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--rule);margin-top:16px}.mv-tbar i{display:block;height:100%}
.mv-tleg{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12.5px;color:var(--ink-2);margin-top:6px}.mv-tleg span:before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px;background:var(--c)}
.mv-nav{position:sticky;top:64px;z-index:5;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;padding:10px 0;margin-top:22px;background:var(--paper);border-bottom:1px solid var(--rule)}
.mv-nav::-webkit-scrollbar{display:none}.mv-nav a{flex:none;font-size:13.5px;font-weight:600;color:var(--ink-2);text-decoration:none;padding:6px 12px;border-radius:999px}.mv-nav a:hover{background:var(--band);color:var(--teal)}
.mv-sec{margin-top:40px;scroll-margin-top:90px}.mv-sec>h2{font-size:clamp(23px,2.5vw,28px)}.mv-sec>p.muted{margin-top:6px;font-size:15px}
.mv-ring{width:96px;height:96px;position:relative;flex:none}.mv-ring svg{width:96px;height:96px;transform:rotate(-90deg)}
.mv-ring b{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;font:500 26px/1 var(--f-mono)}.mv-ring b small{font:400 10px var(--f-body);color:var(--ink-3);margin-top:4px}
@media (max-width:700px){.mv-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.mv-kpis b{font-size:19px}.mv-nav{top:56px}}
</style>"""


def _med(v):
    v = sorted(x for x in v if x is not None)
    return v[len(v) // 2] if v else None


def _p(v, d=1, plus=False):
    if v is None:
        return "–"
    s = f"{v:,.{d}f}%"
    return ("+" + s) if plus and v > 0 else s.replace("-", "−")


def kpis(items):
    return "<div class='mv-kpis'>" + "".join(f"<div><span>{k}</span><b>{v}</b>{f'<small>{s}</small>' if s else ''}</div>" for k, v, s in items) + "</div>"


def tierbar(L):
    cnt = {t: sum(f.get("tier") == t for f in L) for t in ("A+", "A", "B", "C")}
    n = sum(cnt.values())
    if not n:
        return ""
    bar = "".join(f"<i style='width:{cnt[t] / n * 100:.2f}%;background:{C.TIER_VAR[t]}' title='{t}: {cnt[t]}'></i>" for t in cnt if cnt[t])
    leg = "".join(f"<span style='--c:{C.TIER_VAR[t]}'>{t} {C.TIER_WORD[t]} {cnt[t]}</span>" for t in cnt)
    return f"<div class='mv-tbar'>{bar}</div><div class='mv-tleg'>{leg}</div>"


def ring(score, tier):
    if score is None:
        return ""
    c = 2 * math.pi * 40
    f = max(0, min(100, score)) / 100
    return (f"<div class='mv-ring'><svg viewBox='0 0 96 96' aria-hidden='true'><circle cx='48' cy='48' r='40' fill='none' stroke='var(--rule)' stroke-width='8'/>"
            f"<circle cx='48' cy='48' r='40' fill='none' stroke='{C.TIER_VAR.get(tier, 'var(--teal)')}' stroke-width='8' stroke-linecap='round' stroke-dasharray='{c * f:.1f} {c:.1f}'/></svg>"
            f"<b>{score:.0f}<small>score of 100</small></b></div>")


def nav(items):
    return "<nav class='mv-nav' aria-label='On this page'>" + "".join(f"<a href='#{i}'>{t}</a>" for i, t in items) + "</nav>"


def peer_dots(P, e, me=None, h=420, label="peers"):
    """P: plans in one peer group and plan type. x = 3-year volatility, y = 3-year return over the index (a year)."""
    pts = []
    for f in P:
        x, y = f.get("vol_3y"), f.get("excess_3Y")
        if x is None or y is None or not f.get("_url"):
            continue
        extra = f"<span>3-year return<em>{(f.get('ret_3Y') or 0) * 100:.1f}%</em></span>" if f.get("ret_3Y") is not None else ""
        pts.append((x * 100, y * 100, f.get("tier") if f.get("tier") in C.TIER_VAR else None, f["_name"], f["_url"], f is me, extra))
    if len(pts) < 5:
        return ""
    return C.scatter(pts, "Volatility over 3 years, a year →", "↑ 3-year return over its index, a year", h=h, label=label,
                     me_label="This fund")


def category_block(c, L, e, as_of_txt, bench_txt):
    """KPIs, tier bar and the dot chart for a category page (Regular plans: one dot per scheme)."""
    reg = [f for f in L if f["plan_type"] == "Regular"]
    if not reg:
        return "", ""
    e3 = [f["excess_3Y"] for f in reg if f.get("excess_3Y") is not None]
    beat = sum(x > 0 for x in e3)
    r3 = _med([f.get("ret_3Y") for f in reg])
    dd = _med([f.get("max_drawdown_3y") for f in reg])
    k = kpis([("Plans rated", str(sum(1 for f in L if f.get("tier") in C.TIER_VAR)), f"{len(reg)} Regular, {len(L) - len(reg)} Direct"),
              ("Ahead of the index, 3 years", f"{beat} of {len(e3)}" if e3 else "–", "Regular plans, after expenses"),
              ("Typical 3-year return", _p(None if r3 is None else r3 * 100), "a year, median Regular plan"),
              ("Typical worst fall, 3 years", _p(None if dd is None else dd * 100), "median Regular plan")]) + tierbar(reg)
    groups = {}
    for f in reg:
        groups.setdefault(f.get("peer_group") or c, []).append(f)
    charts = ""
    for g, P in sorted(groups.items(), key=lambda x: -len(x[1])):
        ch = peer_dots(P, e, label=f"{g}: 3-year return over the index against volatility")
        if ch:
            charts += (f"<p class='muted' style='font-size:14px;margin-top:14px'><b>{e(g)}</b> · {len(P)} Regular plans</p>" if len(groups) > 1 else "") + ch
    if not charts:
        return k, ""
    sec = (f"<div class='mv-sec' id='dots'><h2>Every fund at a glance</h2><p class='muted'>Each dot is a Regular plan: its 3-year return over {bench_txt} (after expenses) "
           f"against how much it swung. Colour is the rating. Up and to the left is better. Hover or tap a dot for its numbers; click to open it.</p>{charts}</div>")
    return k, sec
