"""Mutual fund page visuals in the same language as the PMS pages: category KPI strip and tier bar, the peer dot chart
(3-year return over the index against volatility, every plan in the peer group), the rating dial, and section navs.
Uses site/charts.py (interactive SVG). Standard library only."""
import math

import charts as C

CSS = """<style>
.mv-hero{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:32px;align-items:start}@media (max-width:900px){.mv-hero{grid-template-columns:1fr}}
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


def dots_data(funds, asset_class):
    """Compact data for the all-funds dot chart (/data/dots.json): Regular plans with a 3-year volatility, index funds left out."""
    fam = {"Equity": "E", "Hybrid": "H", "Debt": "D"}
    r = lambda v: None if v is None else round(v * 100, 2)
    out = []
    for f in funds:
        if f["plan_type"] != "Regular" or f.get("vol_3y") is None or f["category"] == "Index Fund" or not f.get("_url"):
            continue
        out.append([f["_name"], f["_url"], f["category"], fam.get(asset_class(f["category"]), "E"), f.get("tier") if f.get("tier") in C.TIER_VAR else "",
                    r(f.get("excess_1Y")), r(f.get("excess_3Y")), r(f["vol_3y"]), r(f.get("ret_1Y")), r(f.get("ret_3Y"))])
    return out


EXPLORER = """<div class='mv-sec' id='all-dots'><h2>Every fund on one chart</h2>
<p class='muted'>Each dot is a Regular plan: its return over its own yardstick (the category index for equity, a composite for hybrid, the category's median fund for debt),
after expenses, against how much it swung over 3 years. Colour is the rating. Up and to the left is better. Hover or tap a dot for its numbers; click to open it.</p>
<div class='pm-tools' style='display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:14px'>
<div class='xs-seg' data-k='f' role='group' aria-label='Asset class'><button type='button' data-v='E' aria-pressed='true'>Equity</button><button type='button' data-v='H' aria-pressed='false'>Hybrid</button><button type='button' data-v='D' aria-pressed='false'>Debt</button><button type='button' data-v='' aria-pressed='false'>All</button></div>
<div class='xs-seg' data-k='p' role='group' aria-label='Period'><button type='button' data-v='3' aria-pressed='true'>3 years</button><button type='button' data-v='1' aria-pressed='false'>1 year</button></div>
<select id='xsCat' aria-label='Category' class='xs-sel'><option value=''>All categories</option></select>
<span class='muted' style='font-size:13.5px'><b id='xsN'>–</b> funds</span></div>
<div class='ch' id='xsCh' data-dots='1' style='min-height:200px'><p class='muted' style='padding:20px'>Loading the chart…</p></div>
<p class='muted' style='font-size:12.5px;margin-top:8px'>Volatility is over 3 years in both views, so only plans with a 3-year record are shown. Index funds are not shown: they aim to match their index, not beat it. Hollow dots are beyond the scale and drawn at its edge; their own numbers are in the tooltip.</p></div>
<style>.xs-seg{display:inline-flex;flex-wrap:wrap;border:1px solid var(--rule);border-radius:var(--r);overflow:hidden;background:var(--surface)}
.xs-seg button{border:0;background:none;padding:9px 14px;font:600 13.5px var(--f-body);color:var(--ink-2);cursor:pointer;border-right:1px solid var(--rule)}.xs-seg button:last-child{border-right:0}
.xs-seg button[aria-pressed=true]{background:var(--teal);color:var(--on-teal)}.xs-sel{border:1px solid var(--rule);border-radius:var(--r);padding:9px 12px;font:inherit;font-size:14px;background:var(--surface);color:var(--ink);max-width:100%}
#xsCh svg.w{min-width:0}</style>
<script>(function(){var D=null,st={f:'E',p:'3',c:''},ch=document.getElementById('xsCh'),sel=document.getElementById('xsCat'),TV={'A+':'var(--t-ap)','A':'var(--t-a)','B':'var(--t-b)','C':'var(--t-c)'},TW={'A+':'Leading','A':'Strong','B':'In line','C':'Lagging'};
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;').replace(/"/g,'&quot;')}
function ticks(lo,hi,n){var raw=(hi-lo)/n,mag=Math.pow(10,Math.floor(Math.log10(raw||1))),st=[1,2,2.5,5,10].map(function(m){return m*mag}).find(function(s){return s>=raw})||raw,v=Math.ceil(lo/st)*st,o=[];while(v<=hi+1e-9){o.push(Math.round(v*1e6)/1e6);v+=st}return o}
function cats(){var s={};D.forEach(function(d){if(!st.f||d[3]===st.f)s[d[2]]=(s[d[2]]||0)+1});var k=Object.keys(s).sort();sel.innerHTML='<option value="">All categories</option>'+k.map(function(c){return '<option value="'+esc(c)+'">'+esc(c)+' ('+s[c]+')</option>'}).join('');if(k.indexOf(st.c)<0)st.c='';sel.value=st.c}
function draw(){var yi=st.p==='1'?5:6,P=D.filter(function(d){return (!st.f||d[3]===st.f)&&(!st.c||d[2]===st.c)&&d[yi]!=null&&d[7]!=null});document.getElementById('xsN').textContent=P.length;
 if(P.length<2){ch.innerHTML='<p class="muted" style="padding:20px">Not enough funds with a record for this view.</p>';return}
 var nar=ch.clientWidth<600,W=nar?440:960,H=nar?480:480,L=48,R=14,T=34,B=44,q=function(a,p){a=a.slice().sort(function(x,y){return x-y});return a[Math.min(a.length-1,Math.max(0,Math.round(p*(a.length-1))))]},
 xs=P.map(function(d){return d[7]}),ys=P.map(function(d){return d[yi]}),cut=P.length>40?.01:0,
 lo=Math.min(0,q(ys,cut)),hi=Math.max(0,q(ys,1-cut)),x0=q(xs,0),x1=q(xs,1-cut);
 var px=(x1-x0)*.05||1,py=(hi-lo)*.06||1;x0-=px;x1+=px;lo-=py;hi+=py;
 var X=function(v){return L+(W-L-R)*(Math.max(x0,Math.min(x1,v))-x0)/(x1-x0)},Y=function(v){return T+(H-T-B)*(1-(Math.max(lo,Math.min(hi,v))-lo)/(hi-lo))},g='';
 ticks(lo,hi,5).forEach(function(v){g+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(v).toFixed(1)+'" y2="'+Y(v).toFixed(1)+'" stroke="var(--rule)"/><text x="'+(L-8)+'" y="'+(Y(v)+4).toFixed(1)+'" text-anchor="end" font-size="12" fill="var(--ink-3)">'+(v>0?'+':v<0?'−':'')+Math.abs(v)+'%</text>'});
 ticks(x0,x1,5).forEach(function(u){g+='<text x="'+X(u).toFixed(1)+'" y="'+(H-24)+'" text-anchor="middle" font-size="12" fill="var(--ink-3)">'+u+'%</text>'});
 g+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+Y(0).toFixed(1)+'" y2="'+Y(0).toFixed(1)+'" stroke="var(--ink-3)" stroke-dasharray="3 3"/>';
 g+='<text x="'+((L+W-R)/2)+'" y="'+(H-4)+'" text-anchor="middle" font-size="12.5" fill="var(--ink-2)">Volatility over 3 years, a year →</text><text x="'+(L+4)+'" y="'+(T+4)+'" font-size="12.5" fill="var(--ink-2)">↑ '+(st.p==='1'?'1-year':'3-year')+' return over its yardstick'+(st.p==='3'?', a year':'')+'</text>';
 var r=(P.length>300?3.6:P.length>120?4.4:5.4)*(nar?1.25:1);
 P.forEach(function(d){var y=d[yi],tt='<b>'+esc(d[0])+'</b><span>'+esc(d[2])+'</span>'+(d[4]?'<span>Rating<em>'+d[4]+' '+TW[d[4]]+'</em></span>':'')+'<span>'+(st.p==='1'?'1-year':'3-year')+' return over yardstick<em>'+(y>0?'+':'')+y.toFixed(1)+'%</em></span><span>'+(st.p==='1'?'1-year return':'3-year return, a year')+'<em>'+(d[st.p==='1'?8:9]!=null?d[st.p==='1'?8:9].toFixed(1)+'%':'–')+'</em></span><span>Volatility, 3 years<em>'+d[7].toFixed(1)+'%</em></span>';
  var out=y>hi||y<lo||d[7]>x1,cl=TV[d[4]]||'var(--t-u)';if(out)tt+='<span>Off the scale: drawn at the edge</span>';
  g+='<circle class="d" tabindex="0" cx="'+X(d[7]).toFixed(1)+'" cy="'+Y(y).toFixed(1)+'" r="'+r+'" fill="'+(out?'var(--surface)':cl)+'" fill-opacity="'+(out?1:.8)+'" stroke="'+(out?cl:'var(--surface)')+'" stroke-width="'+(out?2:1)+'" data-u="'+esc(d[1])+'" data-t="'+esc(tt)+'"/>'});
 ch.innerHTML='<svg class="w" viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Mutual funds: return over yardstick against volatility">'+g+'</svg><div class="ch-leg">'+['A+','A','B','C'].map(function(t){return '<span><i class="dot" style="background:'+TV[t]+'"></i>'+t+' '+TW[t]+'</span>'}).join('')+'</div>';
 bind()}
function bind(){var t=ch.querySelector('.ch-tip');if(!t){t=document.createElement('div');t.className='ch-tip';ch.appendChild(t)}
 function place(cx,cy){var r=ch.getBoundingClientRect(),w=t.offsetWidth,h=t.offsetHeight,x=cx-r.left+14,y=cy-r.top-h-10;if(x+w>r.width-4)x=cx-r.left-w-14;if(x<4)x=4;if(y<4)y=cy-r.top+16;t.style.left=x+'px';t.style.top=y+'px'}
 ch.querySelectorAll('circle.d').forEach(function(c){var sh=function(e){t.innerHTML=c.getAttribute('data-t');t.classList.add('on');var b=c.getBoundingClientRect();place(e&&e.clientX||b.left,e&&e.clientY||b.top)};
  c.addEventListener('pointerenter',sh);c.addEventListener('pointermove',sh);c.addEventListener('focus',function(){sh()});c.addEventListener('pointerleave',function(){t.classList.remove('on')});c.addEventListener('blur',function(){t.classList.remove('on')});
  c.addEventListener('click',function(e){if(e.pointerType==='touch'&&!c.__t){c.__t=1;e.preventDefault();sh(e);return}location.href=c.getAttribute('data-u')});
  c.addEventListener('keydown',function(e){if(e.key==='Enter')location.href=c.getAttribute('data-u')})})}
document.querySelectorAll('#all-dots .xs-seg').forEach(function(s){s.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;[].forEach.call(s.children,function(x){x.setAttribute('aria-pressed',x===b)});st[s.getAttribute('data-k')]=b.getAttribute('data-v');if(D){if(s.getAttribute('data-k')==='f')cats();draw()}})});
sel.addEventListener('change',function(){st.c=sel.value;draw()});
fetch('/data/dots.json').then(function(r){return r.json()}).then(function(d){D=d;cats();draw()}).catch(function(){ch.innerHTML='<p class="muted" style="padding:20px">The chart could not load.</p>'});})();</script>"""
