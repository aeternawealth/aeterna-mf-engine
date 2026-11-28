"""Interactive SVG charts shared by every static page (PMS, mutual fund category and fund pages, insights).

Charts are drawn server-side as plain SVG (they read without script); CHART_JS adds the interaction: a crosshair with
every series' value on line charts, a tooltip on scatter dots and bars, keyboard focus on dots. Include `assets()`
once per page that has a chart (it is idempotent per build call). Standard library only.
"""
import json
import math

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
TIER_VAR = {"A+": "var(--t-ap)", "A": "var(--t-a)", "B": "var(--t-b)", "C": "var(--t-c)"}
TIER_WORD = {"A+": "Leading", "A": "Strong", "B": "In line", "C": "Lagging"}


def _mo(m):
    return f"{MON[int(m[5:7]) - 1]} {m[:4]}" if isinstance(m, str) and len(m) >= 7 and m[4] == "-" else str(m)


def _esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;").replace('"', "&quot;")


def ticks(lo, hi, n=5):
    raw = (hi - lo) / n
    mag = 10 ** math.floor(math.log10(raw)) if raw > 0 else 1
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    v = math.ceil(lo / step) * step
    out = []
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out


CSS = """<style>
.ch{position:relative;margin-top:14px;border:1px solid var(--rule);border-radius:var(--r);background:var(--surface);padding:12px 12px 8px}
.ch svg{width:100%;height:auto;display:block;overflow:visible;touch-action:pan-y}
.ch-leg{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;color:var(--ink-2);margin:6px 4px 0}
.ch-leg i{display:inline-block;width:14px;height:3px;vertical-align:middle;margin-right:6px;border-radius:2px}.ch-leg i.dot{width:9px;height:9px;border-radius:50%}
.ch-tip{position:absolute;pointer-events:none;z-index:4;min-width:150px;max-width:260px;background:var(--ink);color:var(--paper);border-radius:8px;padding:8px 10px;font-size:12.5px;line-height:1.45;box-shadow:0 10px 24px -10px rgba(var(--shadow),.5);visibility:hidden}
.ch-tip.on{visibility:visible}.ch-tip b{display:block;font-weight:600;margin-bottom:2px}.ch-tip i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}
.ch-tip span{display:flex;justify-content:space-between;gap:12px}.ch-tip em{font-style:normal;font-family:var(--f-mono);white-space:nowrap}
.ch circle.d{cursor:pointer;transition:r .12s}.ch circle.d:hover,.ch circle.d:focus{stroke:var(--ink);stroke-width:2;outline:none}
.ch .xh{stroke:var(--ink-3);stroke-dasharray:3 3;visibility:hidden}.ch.on .xh{visibility:visible}
.ch.sm{padding:8px}.ch.sm svg{max-height:260px}
@media (max-width:700px){.ch{overflow-x:auto;-webkit-overflow-scrolling:touch}.ch svg.w{min-width:600px}}
</style>"""

JS = """<script>(function(){if(window.__ch)return;window.__ch=1;function init(){
function tip(ch){var t=ch.querySelector('.ch-tip');if(!t){t=document.createElement('div');t.className='ch-tip';ch.appendChild(t)}return t}
function place(ch,t,cx,cy){var r=ch.getBoundingClientRect(),w=t.offsetWidth,h=t.offsetHeight,x=cx-r.left+14,y=cy-r.top-h-10;if(x+w>r.width-4)x=cx-r.left-w-14;if(x<4)x=4;if(y<4)y=cy-r.top+16;t.style.left=x+'px';t.style.top=y+'px'}
document.querySelectorAll('.ch[data-line]').forEach(function(ch){var D=JSON.parse(ch.getAttribute('data-line')),svg=ch.querySelector('svg'),xh=svg.querySelector('.xh'),dots=[].slice.call(svg.querySelectorAll('.xd')),t=tip(ch);
 function at(e){var p=svg.createSVGPoint();p.x=e.clientX;p.y=e.clientY;var q=p.matrixTransform(svg.getScreenCTM().inverse()),i=0,b=1e9;D.x.forEach(function(x,k){var d=Math.abs(x-q.x);if(d<b){b=d;i=k}});return i}
 function show(e){var i=at(e);ch.classList.add('on');xh.setAttribute('x1',D.x[i]);xh.setAttribute('x2',D.x[i]);
  dots.forEach(function(c,k){var y=D.s[k].y[i];if(y==null){c.style.display='none'}else{c.style.display='';c.setAttribute('cx',D.x[i]);c.setAttribute('cy',y)}});
  t.innerHTML='<b>'+D.l[i]+'</b>'+D.s.map(function(s){return s.v[i]==null?'':'<span><span><i style="background:'+s.c+'"></i>'+s.n+'</span><em>'+s.v[i]+'</em></span>'}).join('');t.classList.add('on');place(ch,t,e.clientX,e.clientY)}
 function hide(){ch.classList.remove('on');t.classList.remove('on');dots.forEach(function(c){c.style.display='none'})}
 svg.addEventListener('pointermove',show);svg.addEventListener('pointerdown',show);svg.addEventListener('pointerleave',hide)});
document.querySelectorAll('.ch[data-dots]').forEach(function(ch){var t=tip(ch);
 function show(e,c){t.innerHTML=c.getAttribute('data-t');t.classList.add('on');var r=c.getBoundingClientRect();place(ch,t,e&&e.clientX||r.left+r.width/2,e&&e.clientY||r.top)}
 ch.querySelectorAll('[data-t]').forEach(function(c){c.addEventListener('pointerenter',function(e){show(e,c)});c.addEventListener('pointermove',function(e){show(e,c)});c.addEventListener('focus',function(){show(null,c)});
  c.addEventListener('pointerleave',function(){t.classList.remove('on')});c.addEventListener('blur',function(){t.classList.remove('on')});
  c.addEventListener('click',function(e){var u=c.getAttribute('data-u');if(!u)return;if(e.pointerType==='touch'&&!c.__t){c.__t=1;e.preventDefault();show(e,c);return}location.href=u});
  c.addEventListener('keydown',function(e){if(e.key==='Enter'&&c.getAttribute('data-u'))location.href=c.getAttribute('data-u')})})});
}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();})();</script>"""


def assets():
    return CSS + JS


def line(series, labels, fmt=lambda v: f"{v:,.0f}", zero=None, h=300, area=False, label="chart", W=960, small=False):
    if small:
        W = 620
    """series: [(name, colour, values)], labels: month keys (or any labels). Crosshair shows every series at the hovered month."""
    L, R, T, Bm = 64, 74, 14, 30
    vals = [v for _, _, s in series for v in s if v is not None]
    if not vals:
        return ""
    lo, hi = min(vals + ([zero] if zero is not None else [])), max(vals + ([zero] if zero is not None else []))
    if hi == lo:
        hi += 1
    pad = (hi - lo) * 0.07
    lo, hi = lo - pad, hi + pad
    n = len(labels)
    X = lambda i: L + (W - L - R) * (i / max(1, n - 1))
    Y = lambda v: T + (h - T - Bm) * (1 - (v - lo) / (hi - lo))
    g = []
    for v in ticks(lo, hi, 4):
        g.append(f"<line x1='{L}' x2='{W - R}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='var(--rule)'/>"
                 f"<text x='{L - 8}' y='{Y(v) + 4:.1f}' text-anchor='end' font-size='12' fill='var(--ink-3)'>{_esc(fmt(v))}</text>")
    if zero is not None:
        g.append(f"<line x1='{L}' x2='{W - R}' y1='{Y(zero):.1f}' y2='{Y(zero):.1f}' stroke='var(--ink-3)' stroke-dasharray='3 3'/>")
    step = max(1, math.ceil(n / 6))
    for i in range(0, n, step):
        g.append(f"<text x='{X(i):.1f}' y='{h - 8}' text-anchor='middle' font-size='12' fill='var(--ink-3)'>{_esc(_mo(labels[i]))}</text>")
    ends, data = [], {"x": [round(X(i), 1) for i in range(n)], "l": [_mo(x) for x in labels], "s": []}
    for k, (name, col, s) in enumerate(series):
        pts = [(X(i), Y(v)) for i, v in enumerate(s) if v is not None]
        if not pts:
            continue
        P = " ".join(f"{a:.1f},{b:.1f}" for a, b in pts)
        if area and k == 0:
            base = Y(max(lo, min(hi, zero if zero is not None else lo)))
            g.append(f"<polygon fill='{col}' opacity='.09' points='{pts[0][0]:.1f},{base:.1f} {P} {pts[-1][0]:.1f},{base:.1f}'/>")
        g.append(f"<polyline fill='none' stroke='{col}' stroke-width='{2.4 if k == 0 else 1.8}' stroke-linejoin='round' points='{P}'/>")
        ends.append((pts[-1], col, [v for v in s if v is not None][-1]))
        data["s"].append({"n": _esc(name), "c": col, "v": [None if v is None else _esc(fmt(v)) for v in s], "y": [None if v is None else round(Y(v), 1) for v in s]})
    ends.sort(key=lambda e: e[0][1])
    last_y = -99
    for (px, py), col, lv in ends:
        ty = max(py + 4, last_y + 15)
        last_y = ty
        g.append(f"<circle cx='{px:.1f}' cy='{py:.1f}' r='3.5' fill='{col}'/>"
                 f"<text x='{px + 7:.1f}' y='{ty:.1f}' font-size='12.5' font-weight='600' fill='{col}'>{_esc(fmt(lv))}</text>")
    g.append(f"<line class='xh' x1='0' x2='0' y1='{T}' y2='{h - Bm}'/>")
    g += [f"<circle class='xd' r='4.5' fill='{c}' stroke='var(--surface)' stroke-width='2' style='display:none'/>" for _, c, _ in series]
    leg = "".join(f"<span><i style='background:{c}'></i>{_esc(n_)}</span>" for n_, c, _ in series)
    return (f"<div class='ch{' sm' if small else ''}' data-line='{_esc(json.dumps(data, separators=(',', ':')))}'><svg class='w' viewBox='0 0 {W} {h}' role='img' aria-label='{_esc(label)}'>"
            f"{''.join(g)}</svg><div class='ch-leg'>{leg}</div></div>")


def bars(labels, vals, fmt=lambda v: f"₹{v:,.0f} cr", h=230, label="bar chart", W=960):
    L, R, T, Bm = 64, 12, 12, 30
    v2 = [v for v in vals if v is not None]
    if not v2:
        return ""
    lo, hi = min(0, min(v2)), max(0, max(v2))
    if hi == lo:
        hi += 1
    n = len(labels)
    bw = (W - L - R) / n
    Y = lambda v: T + (h - T - Bm) * (1 - (v - lo) / (hi - lo))
    g = [f"<line x1='{L}' x2='{W - R}' y1='{Y(0):.1f}' y2='{Y(0):.1f}' stroke='var(--ink-3)'/>"]
    for k in (lo, hi):
        if k:
            g.append(f"<text x='{L - 8}' y='{Y(k) + 4:.1f}' text-anchor='end' font-size='12' fill='var(--ink-3)'>{_esc(fmt(k))}</text>")
    for i, v in enumerate(vals):
        if v is None:
            continue
        y0, y1 = sorted((Y(0), Y(v)))
        g.append(f"<rect x='{L + i * bw + 1:.1f}' y='{y0:.1f}' width='{max(1, bw - 2):.1f}' height='{max(0.5, y1 - y0):.1f}' rx='1.5' tabindex='0' "
                 f"fill='{'var(--good)' if v >= 0 else 'var(--bad)'}' data-t='<b>{_esc(_mo(labels[i]))}</b>{_esc(fmt(v))}'/>")
    step = max(1, math.ceil(n / 6))
    for i in range(0, n, step):
        g.append(f"<text x='{L + i * bw + bw / 2:.1f}' y='{h - 8}' text-anchor='middle' font-size='12' fill='var(--ink-3)'>{_esc(_mo(labels[i]))}</text>")
    return f"<div class='ch' data-dots='1'><svg class='w' viewBox='0 0 {W} {h}' role='img' aria-label='{_esc(label)}'>{''.join(g)}</svg></div>"


def scatter(pts, xl, yl, h=440, label="scatter", W=960, me_label="This one"):
    """pts: [(x, y, tier, name, url, highlight, extra_line)]; a dot per item, tooltip on hover/tap, click opens it."""
    if not pts:
        return ""
    L, R, T, Bm = 54, 16, 18, 44
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys + [0]), max(ys + [0])
    px, py = (x1 - x0) * .05 or 1, (y1 - y0) * .06 or 1
    x0, x1, y0, y1 = x0 - px, x1 + px, y0 - py, y1 + py
    X = lambda v: L + (W - L - R) * (v - x0) / (x1 - x0)
    Y = lambda v: T + (h - T - Bm) * (1 - (v - y0) / (y1 - y0))
    g = []
    for v in ticks(y0, y1):
        lab = f"{v:+.0f}%".replace("-", "−") if v else "0%"
        g.append(f"<line x1='{L}' x2='{W - R}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' stroke='var(--rule)'/><text x='{L - 8}' y='{Y(v) + 4:.1f}' text-anchor='end' font-size='12' fill='var(--ink-3)'>{lab}</text>")
    for u in ticks(x0, x1):
        g.append(f"<text x='{X(u):.1f}' y='{h - 24}' text-anchor='middle' font-size='12' fill='var(--ink-3)'>{u:.0f}%</text>")
    g.append(f"<line x1='{L}' x2='{W - R}' y1='{Y(0):.1f}' y2='{Y(0):.1f}' stroke='var(--ink-3)' stroke-dasharray='3 3'/>")
    g.append(f"<text x='{(L + W - R) / 2:.0f}' y='{h - 4}' text-anchor='middle' font-size='12.5' fill='var(--ink-2)'>{_esc(xl)}</text>"
             f"<text x='{L + 4}' y='{T + 4}' font-size='12.5' fill='var(--ink-2)'>{_esc(yl)}</text>")
    hl = []
    for p in sorted(pts, key=lambda p: p[5]):
        x, yv, t, nm, u, me = p[:6]
        extra = p[6] if len(p) > 6 else ""
        tt = (f"<b>{_esc(nm)}</b>" + (f"<span>Rating<em>{t} {TIER_WORD.get(t, '')}</em></span>" if t else "")
              + f"<span>{_esc(yl.strip('↑ ').split(',')[0])}<em>{yv:+.1f}%</em></span><span>{_esc(xl.rstrip(' →').split(',')[0])}<em>{x:.1f}%</em></span>{extra}")
        dot = (f"<circle class='d' tabindex='0' cx='{X(x):.1f}' cy='{Y(yv):.1f}' r='{8 if me else 5.2}' fill='{TIER_VAR.get(t, 'var(--t-u)')}' "
               f"fill-opacity='{1 if me else .8}' stroke='{'var(--ink)' if me else 'var(--surface)'}' stroke-width='{2.4 if me else 1}' "
               f"data-u='{_esc(u or '')}' data-t='{_esc(tt)}'/>")
        (hl if me else g).append(dot)
        if me:
            hl.append(f"<text x='{min(X(x) + 11, W - 100):.1f}' y='{max(Y(yv) - 11, T + 26):.1f}' font-size='13' font-weight='700' fill='var(--ink)'>{_esc(me_label)}</text>")
    leg = "".join(f"<span><i class='dot' style='background:{TIER_VAR[t]}'></i>{t} {TIER_WORD[t]}</span>" for t in ("A+", "A", "B", "C"))
    return (f"<div class='ch' data-dots='1'><svg class='w' viewBox='0 0 {W} {h}' role='img' aria-label='{_esc(label)}'>{''.join(g + hl)}</svg>"
            f"<div class='ch-leg'>{leg}</div></div>")


BARE = " style='border:0;padding:0;margin-top:6px;background:none'"


def split_bar(rows, colours, fmt=lambda v: f"{v:.0f}%", label="share", bare=False):
    """Compact 100% bars: rows = [(row label, [(segment label, value)])], same segments per row; HTML, not SVG."""
    out = []
    for lab, segs in rows:
        tot = sum(v for _, v in segs) or 1
        cells = "".join(f"<i style='width:{v / tot * 100:.2f}%;background:{colours[k % len(colours)]}' tabindex='0' "
                        f"data-t='<b>{_esc(lab)}</b><span>{_esc(s)}<em>{_esc(fmt(v / tot * 100))}</em></span>'>"
                        f"{_esc(fmt(v / tot * 100)) if v / tot > .07 else ''}</i>" for k, (s, v) in enumerate(segs))
        out.append(f"<div class='sb-row'><span>{_esc(lab)}</span><div class='sb'>{cells}</div></div>")
    leg = "".join(f"<span><i class='dot' style='background:{colours[k % len(colours)]};border-radius:2px'></i>{_esc(s)}</span>" for k, (s, _) in enumerate(rows[0][1]))
    return ("<style>.sb-row{display:grid;grid-template-columns:110px minmax(0,1fr);gap:12px;align-items:center;margin-top:10px;font-size:13.5px;color:var(--ink-2)}"
            ".sb{display:flex;height:30px;border-radius:6px;overflow:hidden;background:var(--rule)}.sb i{display:flex;align-items:center;justify-content:center;height:100%;"
            "font:600 12px var(--f-mono);font-style:normal;color:var(--surface);border-right:2px solid var(--surface);min-width:0;overflow:hidden}.sb i:last-child{border-right:0}"
            "@media (max-width:600px){.sb-row{grid-template-columns:1fr;gap:4px}}</style>"
            f"<div class='ch sm' data-dots='1' role='img' aria-label='{_esc(label)}'{BARE if bare else ''}>{''.join(out)}<div class='ch-leg' style='margin-top:12px'>{leg}</div></div>")
