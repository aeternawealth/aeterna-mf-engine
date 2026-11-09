"""Design preview v2 (/preview/v2/), unlisted and noindex. Built with the frontend-design guidance: one memorable element
(a real SIP chart that redraws per category), quiet everything else, no template chrome."""
import json
from pathlib import Path

import statistics

HERE = Path(__file__).parent
PATH = "/preview/v2/"
START = "2013-01"
SIP = 10000
CATS = [("flexi-cap", "Flexi cap", "NIFTY 500", "Nifty 500"), ("large-cap", "Large cap", "NIFTY 100", "Nifty 100"),
        ("mid-cap", "Mid cap", "NIFTY MIDCAP 150", "Nifty Midcap 150"), ("small-cap", "Small cap", "NIFTY SMALLCAP 250", "Nifty Smallcap 250")]


def _sip(rets):
    """Value path of SIP rupees invested at the start of every month, growing by the month's return."""
    v, out = 0.0, []
    for r in rets:
        v = (v + SIP) * (1 + r)
        out.append(round(v))
    return out


def series():
    B = json.loads((HERE / "data/series/bench.json").read_text())
    M = B["months"]; i0 = M.index(START)
    out = {}
    for slug, name, idx, idx_name in CATS:
        d = json.loads((HERE / f"data/series/{slug}.json").read_text())
        S = list(d["nav"].values())
        T = B["tri"][idx]
        med, tr = [], []
        for m in range(i0 + 1, len(M)):
            rs = [s[m] / s[m - 1] - 1 for s in S if s[m] and s[m - 1]]
            rs = [r for r in rs if -0.5 < r < 1]
            if not rs or not T[m] or not T[m - 1]:
                break
            med.append(statistics.median(rs)); tr.append(T[m] / T[m - 1] - 1)
        n = len(med)
        out[slug] = dict(name=name, idx=idx_name, months=M[i0 + 1:i0 + 1 + n], fund=_sip(med), index=_sip(tr),
                         put=[SIP * (k + 1) for k in range(n)])
    return out


CSS = """<style>
.v2{--forest:#0B4A3C;--ink2:#17201D;--paper2:#F3F5F1;--sage:#DCE7E1;--brass:#9A7430;background:var(--paper2)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .v2{--forest:#6cc0ae;--ink2:#e6eeeb;--paper2:#0c1412;--sage:#16302b;--brass:#d3a861}}
:root[data-theme=dark] .v2{--forest:#6cc0ae;--ink2:#e6eeeb;--paper2:#0c1412;--sage:#16302b;--brass:#d3a861}
.v2 .wrap{max-width:1180px}
.v2-hero{padding:48px 0 40px}
.v2-hero h1{font-size:clamp(36px,4.6vw,60px);line-height:1.04;letter-spacing:-.012em;max-width:21ch;color:var(--ink2)}
.v2-hero .sub{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:40px;align-items:end;margin-top:26px}
.v2-hero .sub p{font-size:19px;line-height:1.6;color:var(--ink-2);max-width:54ch;margin:0}
.v2-acts{display:flex;gap:12px;flex-wrap:wrap;justify-content:flex-end}
.v2 .btn{border-radius:10px;padding:13px 20px;transition:transform .12s ease,background-color .15s ease}.v2 .btn:active{transform:scale(.98)}
.v2-chart{margin-top:32px;background:var(--surface);border:1px solid var(--rule);border-radius:4px 28px 4px 28px;padding:28px 30px 20px}
.v2-ch-top{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;flex-wrap:wrap}
.v2-ch-top h2{font-size:clamp(22px,2.4vw,30px);max-width:26ch;color:var(--ink2)}
.v2-seg{display:flex;gap:4px;background:var(--paper2);border-radius:10px;padding:4px}
.v2-seg button{border:0;background:none;padding:8px 14px;border-radius:8px;font:500 14.5px var(--f-body);color:var(--ink-2);cursor:pointer}
.v2-seg button[aria-pressed=true]{background:var(--surface);color:var(--ink2);box-shadow:0 1px 2px rgba(20,33,30,.12)}
.v2-figs{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px;margin-top:22px}
.v2-figs div{padding-left:14px;border-left:3px solid var(--k)}.v2-figs b{display:block;font:600 30px/1.1 var(--f-display);color:var(--ink2);font-variant-numeric:tabular-nums}
.v2-figs span{font-size:14px;color:var(--ink-3)}
.v2-svg{width:100%;height:auto;margin-top:16px;display:block;overflow:visible}
.v2-svg .ax{font:12px var(--f-body);fill:var(--ink-3)}
.v2-foot{font-size:13px;color:var(--ink-3);margin-top:8px}
.v2-sec{padding:84px 0}.v2-sec h2{font-size:clamp(30px,3.6vw,46px);line-height:1.08;color:var(--ink2);max-width:20ch}
.v2-sec .intro{font-size:18px;line-height:1.6;color:var(--ink-2);max-width:60ch;margin-top:16px}
.v2-ladder{margin-top:36px;display:grid;gap:0;max-width:880px}
.v2-rung{display:grid;grid-template-columns:96px minmax(0,1fr) auto;gap:24px;align-items:center;padding:22px 0;border-top:1px solid var(--rule)}
.v2-rung:last-child{border-bottom:1px solid var(--rule)}
.v2-rung .t{font:600 34px/1 var(--f-display);color:var(--forest)}.v2-rung b{font:600 19px var(--f-display);color:var(--ink2)}.v2-rung p{margin:4px 0 0;color:var(--ink-2);font-size:15.5px}
.v2-rung .n{font:500 15px var(--f-body);color:var(--ink-3);font-variant-numeric:tabular-nums;text-align:right}
.v2-rung.top{background:linear-gradient(90deg,var(--sage),transparent 70%);margin:0 -20px;padding:22px 20px}
.v2-split{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:56px;align-items:center}
.v2-plan{background:var(--forest);color:#fff;border-radius:28px 4px 28px 4px;padding:38px}
.v2-plan h3{font:600 26px var(--f-display);color:#fff}.v2-plan p{color:rgba(255,255,255,.85);margin-top:10px;line-height:1.6}
.v2-plan .btn{background:#fff;color:var(--forest);border-color:#fff;margin-top:22px}
.v2-list{margin:22px 0 0;padding:0;list-style:none;display:grid;gap:14px}
.v2-list li{padding-left:22px;position:relative;color:var(--ink-2);font-size:16px;line-height:1.55}.v2-list li:before{content:"";position:absolute;left:0;top:.62em;width:8px;height:8px;border-radius:50%;background:var(--brass)}
.v2-close{padding:84px 0 96px}.v2-close h2{font-size:clamp(32px,4vw,52px);max-width:18ch;color:var(--ink2)}.v2-close .intro{margin-top:18px}
.v2-close .row{margin-top:26px;gap:12px}
.v2 .disc{font-size:13px;color:var(--ink-3);max-width:90ch;margin-top:40px}
.v2-note{font-size:13px;color:var(--ink-3);margin-bottom:24px}
@media (max-width:860px){.v2-hero .sub,.v2-split{grid-template-columns:1fr;gap:28px}.v2-acts{justify-content:flex-start}.v2-figs{grid-template-columns:1fr;gap:12px}
 .v2-rung{grid-template-columns:64px minmax(0,1fr);gap:16px}.v2-rung .n{grid-column:2;text-align:left}.v2-chart{padding:20px 16px}}
@media (prefers-reduced-motion:reduce){.v2-svg path{transition:none!important;animation:none!important}}
</style>"""

JS = r"""<script>(()=>{
const D=window.V2D, el=document.getElementById('v2svg'), W=1100, H=360, P={l:8,r:70,t:16,b:30};
const L=n=>n>=1e7?'₹'+(n/1e7).toFixed(2)+' cr':'₹'+(n/1e5).toFixed(1)+' lakh';
function draw(k,anim){const d=D[k], n=d.months.length, mx=Math.max(...d.fund,...d.index)*1.05;
 const x=i=>P.l+(W-P.l-P.r)*i/(n-1), y=v=>H-P.b-(H-P.t-P.b)*v/mx;
 const line=a=>a.map((v,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(v).toFixed(1)).join('');
 let g='';for(let yr=2014;yr<=2026;yr+=2){const i=d.months.indexOf(yr+'-01');if(i>=0)g+=`<line x1="${x(i)}" x2="${x(i)}" y1="${P.t}" y2="${H-P.b}" stroke="var(--rule)"/><text class="ax" x="${x(i)}" y="${H-8}" text-anchor="middle">${yr}</text>`}
 const last=n-1;
 el.innerHTML=g+`<path d="${line(d.put)}" fill="none" stroke="var(--brass)" stroke-width="2" stroke-dasharray="5 6"/>
  <path class="ln" d="${line(d.index)}" fill="none" stroke="var(--ink-3)" stroke-width="2.2"/>
  <path class="ln" d="${line(d.fund)}" fill="none" stroke="var(--forest)" stroke-width="3.4" stroke-linecap="round"/>
  <circle cx="${x(last)}" cy="${y(d.fund[last])}" r="5" fill="var(--forest)"/>
  <text class="ax" x="${x(last)+10}" y="${y(d.fund[last])+4}" style="fill:var(--ink2);font-weight:600">${L(d.fund[last])}</text>`;
 if(anim&&!matchMedia('(prefers-reduced-motion: reduce)').matches)el.querySelectorAll('.ln').forEach((p,j)=>{const len=p.getTotalLength();p.style.strokeDasharray=len;p.style.strokeDashoffset=len;p.getBoundingClientRect();p.style.transition=`stroke-dashoffset ${1.6+j*.2}s cubic-bezier(.3,.6,.2,1)`;p.style.strokeDashoffset=0});
 const yrs=Math.round(n/12);
 document.getElementById('v2h').textContent=`₹10,000 a month in the typical ${d.name.toLowerCase()} fund, from January 2013`;
 document.getElementById('v2f').textContent=L(d.fund[last]);document.getElementById('v2i').textContent=L(d.index[last]);document.getElementById('v2p').textContent=L(d.put[last]);
 document.getElementById('v2il').textContent=`in the ${d.idx} total-return index`;
 document.getElementById('v2foot').textContent=`Typical fund: the median monthly return of every ${d.name.toLowerCase()} fund with a NAV that month, Regular and Direct plans, ${d.months[0]} to ${d.months[last]}. Index: NSE total-return index, dividends included. Before tax. Past returns do not predict future returns.`}
document.querySelectorAll('.v2-seg button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.v2-seg button').forEach(x=>x.setAttribute('aria-pressed',x===b));draw(b.dataset.k,true)});
draw('flexi-cap',true)})()</script>"""


def preview_v2(B, urls):
    S = series()
    funds = json.loads((HERE / "data/funds.json").read_text(encoding="utf-8"))
    funds = funds["funds"] if isinstance(funds, dict) else funds
    cnt = {t: sum(1 for f in funds if f.get("tier") == t) for t in ("A+", "A", "B", "C")}
    rated = sum(cnt.values())
    rungs = [("A+", "The strongest record in its category", "Top 10% of its peer group, a score of 70 or more, and ahead of its benchmark."),
             ("A", "Clearly above most of its peers", "Top 30% with a score of 55 or more, and ahead of its benchmark on at least one test."),
             ("B", "In the middle of the pack", "Neither a reason to buy nor to sell on its own."),
             ("C", "Behind its peers, or held back by a red flag", "Worth a review if you hold it.")]
    ladder = "".join(f'<div class="v2-rung{" top" if t == "A+" else ""}"><div class="t">{t}</div><div><b>{h}</b><p>{p}</p></div><div class="n">{cnt[t]:,} plans today</div></div>' for t, h, p in rungs)
    segs = "".join(f'<button type="button" data-k="{k}" aria-pressed="{str(k == "flexi-cap").lower()}">{v["name"]}</button>' for k, v in S.items())
    body = CSS + f"""<div class="v2">
<section class="v2-hero"><div class="wrap">
 <p class="v2-note">Design preview two, not linked from the site. <a href="/preview/">Preview one</a> · <a href="/">Current home page</a></p>
 <h1>Your savings, put to work with the facts in front of you</h1>
 <div class="sub"><p>We measure all {len(funds):,} mutual fund plans in India against the right benchmark every month, and turn your goals into a monthly plan you can follow. AMFI-registered distributor, ARN-317889, New Delhi.</p>
  <div class="v2-acts"><a class="btn primary" href="/plan/">Build my Money Plan</a><a class="btn" href="/#contact">Talk to us</a></div></div>
 <div class="v2-chart">
  <div class="v2-ch-top"><h2 id="v2h"></h2><div class="v2-seg" role="group" aria-label="Fund category">{segs}</div></div>
  <div class="v2-figs"><div style="--k:var(--forest)"><b id="v2f"></b><span>in the typical fund today</span></div><div style="--k:var(--ink-3)"><b id="v2i"></b><span id="v2il"></span></div><div style="--k:var(--brass)"><b id="v2p"></b><span>put in, ₹10,000 every month</span></div></div>
  <svg class="v2-svg" id="v2svg" viewBox="0 0 1100 360" role="img" aria-label="Growth of a ₹10,000 monthly SIP: typical fund, its index, and money put in"></svg>
  <p class="v2-foot" id="v2foot"></p>
 </div></div></section>

<section class="v2-sec"><div class="wrap">
 <h2>Four ratings, earned against each fund's own peers</h2>
 <p class="intro">A small cap fund is compared only with small cap funds, a Direct plan only with Direct plans. Each fund is measured against the index it is meant to beat, and the ratings are recalculated every month. {rated:,} plans have enough history to be rated today.</p>
 <div class="v2-ladder">{ladder}</div>
 <p style="margin-top:22px"><a href="/#ratings">See the ratings for every category</a> &nbsp; <a href="/#method">How the ratings are built</a></p>
</div></section>

<section class="v2-sec" style="padding-top:0"><div class="wrap v2-split">
 <div><h2>How much should you invest, and where?</h2>
  <ul class="v2-list"><li>Each goal priced in today's money, from a wedding next year to retirement</li><li>What your existing investments already cover, before any new SIP</li><li>A secure retirement target: 22 to 33 times a year's spending, depending on when you stop working</li><li>Your plan replayed through the 2008 and 2020 crashes</li></ul></div>
 <div class="v2-plan"><h3>The Money Plan</h3><p>Two minutes for a quick plan, six for a detailed one. It runs in your browser; nothing is sent to us unless you choose to.</p><a class="btn" href="/plan/">Build my Money Plan</a></div>
</div></section>

<section class="v2-close"><div class="wrap">
 <h2>Start with a conversation, not a form</h2>
 <p class="intro">A first call is free. We reply within one working day, and we tell you what we earn on every fund we suggest.</p>
 <div class="row"><a class="btn primary" href="/#contact">Talk to us</a><a class="btn" href="/invest/">What we offer</a></div>
 <p class="disc">Mutual fund investments are subject to market risks; read all scheme-related documents carefully. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889) and earns commission on Regular plans. Ratings describe past track records and are not forecasts.</p>
</div></section></div>"""
    body += "<script>window.V2D=" + json.dumps(S, separators=(",", ":")) + ";</script>" + JS
    html = B.page("Aeterna Wealth: design preview two", "Design preview of the Aeterna Wealth home page.", PATH, body)
    html = html.replace('<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">', '<meta name="robots" content="noindex,nofollow">')
    B.write(PATH, html)
