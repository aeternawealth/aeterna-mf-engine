"""Agent 7 - Publishing: writes a self-contained dashboard.html next to the rankings (opens offline)."""
from __future__ import annotations

from pathlib import Path

HTML = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Aeterna MF Rankings</title>
<style>
:root{--bg:#f6f7f5;--card:#fff;--ink:#16201d;--mut:#62706b;--line:#e3e7e4;--acc:#0f5c4c;--accs:#e3efeb;--warn:#fff6e0;--warnl:#e9c46a;
--ap:#0f6b4f;--a:#3b8f6e;--b:#8a8f3a;--c:#b0702a;--av:#b23b3b;--un:#8d9692}
@media (prefers-color-scheme:dark){:root{--bg:#0f1412;--card:#161d1a;--ink:#e7ece9;--mut:#93a19b;--line:#26302c;--acc:#5cc2a3;--accs:#1d2c27;--warn:#2b2615;--warnl:#7a6526}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:20px 24px 8px}h1{margin:0;font-size:20px}.sub{color:var(--mut);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;padding:12px 24px;position:sticky;top:0;background:var(--bg);z-index:3;border-bottom:1px solid var(--line);align-items:center}
select,input,button{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:8px;padding:7px 10px}
button{cursor:pointer}button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.seg{display:flex}.seg button{border-radius:0;margin-left:-1px}.seg button:first-child{border-radius:8px 0 0 8px;margin:0}.seg button:last-child{border-radius:0 8px 8px 0}
.lbl{font-size:12px;color:var(--mut);margin-right:-2px}
.note{margin:12px 24px 0;padding:10px 14px;border-radius:10px;background:var(--warn);border:1px solid var(--warnl);font-size:13px}
main{padding:12px 24px 90px}.grp{background:var(--card);border:1px solid var(--line);border-radius:12px;margin:0 0 16px;overflow:auto}
.grp h2{font-size:15px;margin:0;padding:12px 14px;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.grp h2 span{color:var(--mut);font-weight:400;font-size:12px}
table{border-collapse:collapse;width:100%;min-width:1000px}th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:var(--mut);font-weight:600;cursor:pointer;background:var(--card)}
td.nm,th.nm{text-align:left;white-space:normal;min-width:240px}tr:hover td{background:var(--accs)}td.nm{cursor:pointer}
tr.dim td{opacity:.55}
.t{display:inline-block;min-width:44px;text-align:center;padding:2px 6px;border-radius:6px;color:#fff;font-weight:600;font-size:12px}
.t-Ap{background:var(--ap)}.t-A{background:var(--a)}.t-B{background:var(--b)}.t-C{background:var(--c)}.t-Avoid{background:var(--av)}.t-Unrated,.t-Watch,.t-NA{background:var(--un)}
.sc{display:flex;align-items:center;gap:6px;justify-content:flex-end}.sc i{display:block;height:6px;border-radius:3px;background:var(--acc)}
.pos{color:var(--ap)}.neg{color:var(--av)}.fl{color:var(--av);font-size:11px}.mut{color:var(--mut)}
dialog{border:1px solid var(--line);border-radius:12px;background:var(--card);color:var(--ink);max-width:1100px;width:95vw;padding:0}
dialog .in{padding:18px;max-height:85vh;overflow:auto}dialog h3{margin:0 0 4px}
.kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:4px 16px;margin-top:12px}
.kv div{display:flex;justify-content:space-between;border-bottom:1px dashed var(--line);padding:3px 0}.kv b{font-weight:500;color:var(--mut)}
.cmpbar{position:fixed;left:50%;transform:translateX(-50%);bottom:16px;background:var(--acc);color:#fff;border-radius:999px;padding:8px 10px 8px 18px;display:none;gap:10px;align-items:center;z-index:5;box-shadow:0 6px 20px rgba(0,0,0,.2)}
.cmpbar button{border:0;background:#fff;color:var(--acc);font-weight:600;border-radius:999px}
.mx{min-width:600px}.mx td,.mx th{white-space:normal}.mx th.row{text-align:left;color:var(--ink);text-transform:none;letter-spacing:0;font-size:13px;font-weight:500;cursor:default}
.mx tr.sec th{background:var(--accs);color:var(--acc);text-align:left;cursor:default}.best{font-weight:700;color:var(--ap)}
footer{color:var(--mut);font-size:12px;padding:0 24px 30px}
@media (max-width:600px){header,.bar,main,footer{padding-left:16px;padding-right:16px}.note{margin:12px 16px 0}}
</style></head><body>
<header><h1>Aeterna MF Rankings</h1><div class="sub">NAV data as of <b id="asof"></b> · portfolios as of <b id="hasof"></b> · ranked within SEBI category × plan · internal use</div></header>
<div class="bar">
 <select id="cat"></select>
 <span class="lbl">Rank by</span><div class="seg" id="hz"></div>
 <div class="seg" id="plan"><button data-v="Regular" class="on">Regular</button><button data-v="Direct">Direct</button><button data-v="Both">Side by side</button></div>
 <select id="tier"><option value="">All tiers</option><option>A+</option><option>A</option><option>B</option><option>C</option><option>Unrated</option></select>
 <input id="q" placeholder="Search fund / AMC" size="20">
</div>
<div class="note" id="note"></div>
<main id="main"></main>
<div class="cmpbar" id="cmpbar"><span id="cmpn"></span><button id="cmpgo">Compare</button><button id="cmpclr">Clear</button></div>
<footer>Scores are percentiles within the peer group (0–100). "Overall" uses the full protocol (rolling returns, risk, cost, portfolio, red flags) and needs 3+ years of history. Period views rank every fund that existed for the whole period on return, risk-adjusted return, downside, drawdown, consistency and cost within that period only. Ratings describe each fund's track record; they are not forecasts. Our 2019–2025 backtest found that neither these ratings nor trailing returns reliably predicted which funds would beat their index next. Past performance is not a guarantee of future returns.</footer>
<dialog id="dlg"><div class="in" id="dd"></div></dialog>
<script>
const D=__DATA__;document.getElementById('asof').textContent=new Date(D.as_of).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'});
(()=>{const m=(D.meta||{}).holdings_month;document.getElementById('hasof').textContent=m?new Date(+m.slice(0,4),+m.slice(5,7)-1,1).toLocaleDateString('en-IN',{month:'short',year:'numeric'})+' month-end':'–'})();
const F=D.funds,H=D.holdings||{},$=s=>document.querySelector(s);
const pct=(v,d=1)=>v==null?'–':(v*100).toFixed(d)+'%',num=(v,d=1)=>v==null?'–':(+v).toFixed(d),sg=v=>v==null?'':(v>0?'pos':'neg');
const TO={'A+':0,'A':1,'B':2,'Watch':3,'C':4,'Avoid':5,'Unrated':6};
const HZ=['Overall',...D.horizons];
let st={cat:null,plan:'Regular',hz:'Overall',tier:'',q:'',sort:null},sel=[];
const catOf=f=>(f.category==='Value'||f.category==='Contra')?'Value / Contra':f.category;
const cats=[...new Set(F.map(catOf))].sort();
$('#cat').innerHTML=cats.map(c=>`<option>${c}</option>`).join('');st.cat=cats.includes('Flexi Cap')?'Flexi Cap':cats[0];$('#cat').value=st.cat;
$('#hz').innerHTML=HZ.map(h=>`<button data-v="${h}" class="${h==='Overall'?'on':''}">${h==='Overall'?'Overall (3Y+)':h}</button>`).join('');
const seg=(id,key)=>document.querySelectorAll(`#${id} button`).forEach(b=>b.onclick=()=>{document.querySelectorAll(`#${id} button`).forEach(x=>x.classList.remove('on'));b.classList.add('on');st[key]=b.dataset.v;st.sort=null;draw()});
seg('hz','hz');seg('plan','plan');
$('#cat').onchange=e=>{st.cat=e.target.value;draw()};$('#tier').onchange=e=>{st.tier=e.target.value;draw()};$('#q').oninput=e=>{st.q=e.target.value.toLowerCase();draw()};
const tier=t=>{t=t==null?'':String(t);return `<span class="t t-${(t||'NA').replace('+','p')}">${t||'–'}</span>`};
const bar=s=>s==null?'<span class="mut">–</span>':`<div class="sc">${num(s)}<i style="width:${s*.6}px"></i></div>`;
const isIdx=()=>st.cat==='Index Fund';
const FL={chronic_underperformer:'⚠ Chronic underperformer',risk_without_reward:'⚠ Risk without reward',turnaround_unproven:'⚠ Recent turnaround, long record weak',deep_drawdown:'⚠ Deep falls vs peers',mandate_breach:'⚠ SEBI mandate breach',closet_indexer:'⚠ Index-like, no extra return',recent_underperformance:'⚠ Weak last 12 months'};
const flg=s=>(s||'').split(', ').filter(Boolean).map(x=>FL[x]||x).join(' · ');
const HARD=f=>/chronic_underperformer|risk_without_reward/.test(f.flags||'');
const benchRet=(list,h)=>{const f=list.find(x=>x['ret_'+h]!=null&&x['excess_'+h]!=null);return f?f['ret_'+h]-f['excess_'+h]:null};
function note(){const h=st.hz;let t='';
 if(h==='6M'||h==='1Y')t=`<b>${h} view ranks recent performance only</b> (excess return over the index, downside protection, worst fall, consistency and cost within the last ${h}). Short periods are dominated by market cycles and luck — base decisions on the <b>3Y / Overall</b> view. Funds with long-term red flags (chronic underperformer, risk without reward) are <b>excluded</b> from period ranks; ⚠ flags are shown next to the name.`;
 else if(h==='Overall')t=`<b>Recommended view.</b> Ranks funds with 3+ years of history on rolling returns, risk, consistency, cost and portfolio quality, with red-flag overrides. Younger funds appear as “Unrated” — switch to 6M/1Y to see where they stand so far.`;
 else t=`<b>${h} view</b> ranks every fund that has existed for the full ${h} on excess return over the index, risk-adjusted return, downside protection, worst fall, consistency and cost within that period. Long-term red-flagged funds are excluded.`;
 $('#note').innerHTML=t}
function cols(){const h=st.hz;
 if(h==='Overall')return isIdx()?[['Tier','tier'],['Score','score'],['Track diff 1Y','tracking_diff_1y'],['Track err 1Y','tracking_err_1y'],['1Y','cagr_1y'],['3Y','cagr_3y'],['TER','ter'],['AUM ₹cr','aum_cr']]
  :[['Tier','tier'],['Score','score'],['1Y','ret_1Y'],['3Y CAGR','cagr_3y'],['5Y CAGR','cagr_5y'],['Roll-3Y excess','roll3y_excess_median'],['Beat index %','roll3y_hit_rate'],['Down capt.','downside_capture_3y'],['Max DD 5Y','max_drawdown_5y'],['Active share','active_share'],['TER','ter'],['AUM ₹cr','aum_cr']];
 return isIdx()?[['Rank','rank_'+h],['Score','score_'+h],['Return','ret_'+h],['Track diff','excess_'+h],['Track err','te_'+h],['TER','ter'],['Overall tier','tier']]
  :[['Rank','rank_'+h],['Score','score_'+h],['Fund return','ret_'+h],['Excess vs index','excess_'+h],['Info ratio','ir_'+h],['Down capt.','dcap_'+h],['Max fall','mdd_'+h],['Beat index %','hit_'+h],['TER','ter'],['Overall tier','tier']]}
function cell(f,k){const v=f[k];
 if(k==='tier')return tier(v);if(k==='score'||k.startsWith('score_'))return bar(v);
 if(k.startsWith('rank_'))return v==null?(HARD(f)?'<span class="fl">excluded</span>':'<span class="mut">n/a</span>'):`<b>${v}</b><span class="mut"> / ${f['peers_'+k.slice(5)]}</span>`;
 if(/^(cagr_|ret_|roll3y_excess|max_drawdown|mdd_)/.test(k))return `<span class="${k.startsWith('roll3y_excess')?sg(v):''}">${pct(v)}</span>`;
 if(k.startsWith('excess_'))return `<span class="${sg(v)}">${isIdx()?num(v*100,2)+'%':pct(v)}</span>`.replace('NaN%','–');
 if(/hit_rate|^hit_/.test(k))return v==null?'–':Math.round(v*100)+'%';
 if(/capture|^dcap_|active_share/.test(k))return num(v,0);if(k==='aum_cr')return v==null?'–':Math.round(v).toLocaleString('en-IN');
 if(k==='ter')return v==null?'–':num(v,2)+'%';if(/^tracking|^te_/.test(k))return v==null?'–':num(v,2)+'%';return num(v,2)}
function nameCell(f){const ck=sel.includes(f.code)?'checked':'';
 return `<label style="display:flex;gap:8px;align-items:flex-start"><input type="checkbox" data-cmp="${f.code}" ${ck} style="margin-top:3px" onclick="event.stopPropagation()"><span>${f.name}<div class="mut" style="font-size:11px">${f.amc||''} · ${(+f.age_years||0).toFixed(1)} yrs${f.flags?` · <span class="fl">${flg(f.flags)}</span>`:''}</div></span></label>`}
function rows(){return F.filter(f=>catOf(f)===st.cat&&(st.plan==='Both'||f.plan_type===st.plan)&&(!st.tier||f.tier===st.tier)&&(!st.q||(f.name+' '+f.amc).toLowerCase().includes(st.q)))}
function sortF(a,b){if(st.sort){const[k,d]=st.sort;const x=a[k],y=b[k];if(x==null)return 1;if(y==null)return -1;return(x>y?1:x<y?-1:0)*d}
 if(st.hz==='Overall')return(TO[a.tier]??9)-(TO[b.tier]??9)||(b.score??-1)-(a.score??-1);
 const k='score_'+st.hz;return(b[k]??-1)-(a[k]??-1)}
function draw(){note();const m=$('#main'),R=rows(),groups={};R.forEach(f=>(groups[f.peer_group]=groups[f.peer_group]||[]).push(f));m.innerHTML='';
 Object.keys(groups).sort().forEach(g=>{if(st.plan==='Both'){m.appendChild(both(g,groups[g]));return}
  const list=groups[g].sort(sortF),C=cols(),k=st.hz==='Overall'?'score':'score_'+st.hz;
  const ranked=list.filter(f=>f[k]!=null).length,bench=list.find(f=>f.benchmark)?.benchmark||'peer proxy';
  const el=document.createElement('section');el.className='grp';
  const br=st.hz==='Overall'?null:benchRet(list,st.hz);
  el.innerHTML=`<h2>${g}<span>${ranked} of ${list.length} ranked${st.hz==='Overall'?'':' for '+st.hz} · benchmark ${bench}${br!=null&&!isIdx()?` returned <b>${pct(br)}</b> over ${st.hz}${st.hz==='6M'?'':' (annualised)'}`:''}</span></h2><table><thead><tr><th class="nm">Fund</th>${C.map(c=>`<th data-k="${c[1]}">${c[0]}</th>`).join('')}</tr></thead><tbody>${list.map(f=>`<tr class="${f[k]==null?'dim':''}"><td class="nm" data-c="${f.code}">${nameCell(f)}</td>${C.map(c=>`<td>${cell(f,c[1])}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
  el.querySelectorAll('th[data-k]').forEach(th=>th.onclick=()=>{const kk=th.dataset.k;st.sort=st.sort&&st.sort[0]===kk?[kk,-st.sort[1]]:[kk,kk.startsWith('rank_')?1:-1];draw()});
  el.querySelectorAll('td[data-c]').forEach(td=>td.onclick=()=>detail(+td.dataset.c));
  el.querySelectorAll('input[data-cmp]').forEach(cb=>cb.onchange=()=>toggle(+cb.dataset.cmp,cb.checked));m.appendChild(el)});
 if(!m.children.length)m.innerHTML='<p class="mut">No funds match.</p>'}
// ---------- Regular vs Direct, side by side
function both(g,list){const by={};list.forEach(f=>{(by[f.pair_key]=by[f.pair_key]||{})[f.plan_type]=f});
 const h=st.hz,ov=h==='Overall',sk=ov?'score':'score_'+h,rk=ov?null:'rank_'+h,ret=ov?'ret_3Y':'ret_'+h,rl=ov?'3Y':h;
 const P=Object.values(by).sort((a,b)=>((b.Regular||b.Direct)[sk]??-1)-((a.Regular||a.Direct)[sk]??-1));
 const el=document.createElement('section');el.className='grp';
 const rc=f=>!f||!f.name?'<span class="mut">–</span>':ov?tier(f.tier):cell(f,rk);
 el.innerHTML=`<h2>${g}<span>Regular vs Direct · ${ov?'Overall rating':h+' rank'} · gap = Direct return minus Regular return (≈ extra cost of the Regular plan)</span></h2><table><thead><tr><th class="nm">Fund</th><th>Regular ${ov?'tier':'rank'}</th><th>Regular score</th><th>Direct ${ov?'tier':'rank'}</th><th>Direct score</th><th>Regular ${rl} return</th><th>Direct ${rl} return</th><th>Gap ${ov||h!=='6M'?'p.a.':''}</th><th>TER Regular</th><th>TER Direct</th></tr></thead><tbody>${P.map(p=>{const r=p.Regular||{},d=p.Direct||{},f=r.name?r:d;
  const gap=(d[ret]!=null&&r[ret]!=null)?d[ret]-r[ret]:null;
  return `<tr class="${f[sk]==null?'dim':''}"><td class="nm" data-c="${f.code}">${nameCell(f)}</td><td>${rc(r)}</td><td>${bar(r[sk])}</td><td>${rc(d)}</td><td>${bar(d[sk])}</td><td>${pct(r[ret])}</td><td>${pct(d[ret])}</td><td>${gap==null?'–':(gap*100).toFixed(2)+'%'}</td><td>${r.ter==null?'–':num(r.ter,2)+'%'}</td><td>${d.ter==null?'–':num(d.ter,2)+'%'}</td></tr>`}).join('')}</tbody></table>`;
 el.querySelectorAll('td[data-c]').forEach(td=>td.onclick=()=>detail(+td.dataset.c));
 el.querySelectorAll('input[data-cmp]').forEach(cb=>cb.onchange=()=>toggle(+cb.dataset.cmp,cb.checked));return el}
function toggle(code,on){sel=sel.filter(c=>c!==code);if(on){if(sel.length>=5){alertless();draw();return}sel.push(code)}cmpUI()}
function alertless(){$('#cmpn').textContent='Max 5 funds'}
function cmpUI(){$('#cmpbar').style.display=sel.length?'flex':'none';$('#cmpn').textContent=`${sel.length} selected`}
$('#cmpclr').onclick=()=>{sel=[];cmpUI();draw()};$('#cmpgo').onclick=()=>compare();
// ---------- comparison matrix
const MX=[['Basics',[['Category','category','t'],['Plan','plan_type','t'],['Latest NAV (₹)','nav_latest','n2'],['NAV date','nav_date','d'],['Age (yrs)','age_years','n1'],['AUM ₹cr','aum_cr','aum',1],['Expense ratio','ter','ter',-1],['Overall tier','tier','tier'],['Overall score','score','n1',1]]],
 ['Returns',[['6M return','ret_6M','p',1],['1Y return','ret_1Y','p',1],['3Y CAGR','ret_3Y','p',1],['5Y CAGR','ret_5Y','p',1]]],
 ['Vs benchmark',[['6M excess','excess_6M','p',1],['1Y excess','excess_1Y','p',1],['3Y excess (CAGR)','excess_3Y','p',1],['5Y excess (CAGR)','excess_5Y','p',1],['Beat index, rolling 3Y windows','roll3y_hit_rate','p0',1]]],
 ['Category rank',[['Rank 6M','rank_6M','rk',-1],['Rank 1Y','rank_1Y','rk',-1],['Rank 3Y','rank_3Y','rk',-1],['Rank 5Y','rank_5Y','rk',-1]]],
 ['Risk',[['Info ratio 3Y','ir_3Y','n2',1],['Info ratio 1Y','ir_1Y','n2',1],['Downside capture 3Y','dcap_3Y','n0',-1],['Downside capture 1Y','dcap_1Y','n0',-1],['Max drawdown 3Y','mdd_3Y','p',1],['Max drawdown 1Y','mdd_1Y','p',1],['Volatility 3Y','vol_3y','p',-1],['Sharpe 3Y','sharpe_3y','n2',1],['Sortino 3Y','sortino_3y','n2',1]]],
 ['Past 3-year outcomes',[['Median 3Y CAGR (all history)','hist3y_median','p',1],['Worst 10% of 3Y periods','hist3y_p10','p',1],['Periods with a gain','hist3y_pos','p0',1]]],
 ['Money flows',[['Net flow, last 4 quarters','flow_4q','p'],['Net flow, latest quarter','flow_1q','p']]],
 ['Portfolio',[['Stocks','n_stocks','n0'],['Top-10 weight','top10_pct','pc'],['Large / Mid / Small %','_mix','t'],['Active share','active_share','n0',1],['Cash & other %','cash_other_pct','pc',-1],['Top sector','_sector','t']]]];
function fmt(f,k,t){const v=k==='_mix'?(f.large_pct==null?null:`${num(f.large_pct,0)} / ${num(f.mid_pct,0)} / ${num(f.small_pct,0)}`):k==='_sector'?(f.top_sector?`${f.top_sector} (${num(f.top_sector_pct,0)}%)`:null):f[k];
 if(v==null||v==='')return '<span class="mut">n/a</span>';
 return {d:String(v).slice(0,10),t:v,n0:num(v,0),n1:num(v,1),n2:num(v,2),p:pct(v),p0:pct(v,0),pc:num(v,1)+'%',ter:num(v,2)+'%',aum:Math.round(v).toLocaleString('en-IN'),tier:tier(v),rk:`${v} / ${f['peers_'+k.slice(5)]}`}[t]}
function overlap(a,b){const A=H[a.pair_key],B=H[b.pair_key];if(!A||!B)return null;const m={};A.forEach(x=>m[x[0]]=x[2]);let s=0;B.forEach(x=>{if(m[x[0]]!=null)s+=Math.min(m[x[0]],x[2])});return s}
function compare(){const fs=sel.map(c=>F.find(f=>f.code===c)).filter(Boolean);if(!fs.length)return;
 let h=`<h3>Fund comparison</h3><div class="sub">Ranks are within each fund's own category & plan. “n/a” = fund not old enough for that period (or no data).</div><div style="overflow:auto;margin-top:12px"><table class="mx"><thead><tr><th class="row"></th>${fs.map(f=>`<th style="text-align:right;white-space:normal;min-width:150px;color:var(--ink);text-transform:none;letter-spacing:0;font-size:13px">${f.name}<div class="mut" style="font-weight:400">${f.plan_type}</div></th>`).join('')}</tr></thead><tbody>`;
 MX.forEach(([sec,rs])=>{h+=`<tr class="sec"><th colspan="${fs.length+1}">${sec}</th></tr>`;
  rs.forEach(([lab,k,t,dir])=>{const vals=fs.map(f=>f[k]);let best=null;
   if(dir&&fs.length>1){const ok=vals.filter(v=>v!=null);if(ok.length>1)best=dir>0?Math.max(...ok):Math.min(...ok)}
   h+=`<tr><th class="row">${lab}</th>${fs.map((f,i)=>`<td class="${best!=null&&vals[i]===best?'best':''}">${fmt(f,k,t)}</td>`).join('')}</tr>`})});
 if(fs.length>1){h+=`<tr class="sec"><th colspan="${fs.length+1}">Portfolio overlap (common holdings, % of portfolio)</th></tr>`;
  fs.forEach(a=>{h+=`<tr><th class="row">${a.name}</th>${fs.map(b=>{if(a===b)return '<td class="mut">—</td>';const o=overlap(a,b);return `<td>${o==null?'<span class="mut">no holdings data</span>':num(o,0)+'%'}</td>`}).join('')}</tr>`});
  const miss=fs.filter(f=>!H[f.pair_key]);if(miss.length)h+=`<tr><td colspan="${fs.length+1}" class="mut" style="text-align:left;white-space:normal">Portfolio not yet available for: ${miss.map(f=>`${f.name} (${f.amc})`).join(', ')}. Overlap can only be computed when both funds' monthly portfolios have been downloaded.</td></tr>`}
 h+=`</tbody></table></div><p class="sub" style="margin-top:10px">Bold green = best among the selected funds on that row. Overlap uses each fund's latest monthly portfolio disclosure.</p><p style="text-align:right;margin:10px 0 0"><button onclick="dlg.close()">Close</button></p>`;
 $('#dd').innerHTML=h;$('#dlg').showModal()}
// ---------- single fund detail
const LBL={score:'Overall score',peer_rank:'Overall rank',peer_count:'Peers',age_years:'Age (yrs)',benchmark:'Benchmark',cagr_1y:'1Y CAGR',cagr_3y:'3Y CAGR',cagr_5y:'5Y CAGR',excess_cagr_3y:'3Y excess vs index',excess_cagr_5y:'5Y excess vs index',roll3y_excess_median:'Median rolling-3Y excess',roll3y_hit_rate:'Rolling-3Y beat rate',roll3y_excess_p10:'Worst-decile rolling-3Y excess',roll1y_hit_rate:'Rolling-1Y beat rate',info_ratio_3y:'Info ratio 3Y',sortino_3y:'Sortino 3Y',sharpe_3y:'Sharpe 3Y',downside_capture_3y:'Downside capture',upside_capture_3y:'Upside capture',max_drawdown_5y:'Max drawdown 5Y',vol_3y:'Volatility 3Y',beta_3y:'Beta 3Y',tracking_diff_1y:'Tracking diff 1Y',tracking_err_1y:'Tracking error 1Y',ter:'TER',aum_cr:'AUM ₹cr',n_stocks:'Stocks',top10_pct:'Top-10 weight %',cash_other_pct:'Cash/other %',large_pct:'Large cap %',mid_pct:'Mid cap %',small_pct:'Small cap %',top_sector:'Top sector',active_share:'Active share',mandate_breaches:'Mandate breaches'};
const PCT=new Set(['cagr_1y','cagr_3y','cagr_5y','excess_cagr_3y','excess_cagr_5y','roll3y_excess_median','roll3y_hit_rate','roll3y_excess_p10','roll1y_hit_rate','max_drawdown_5y','vol_3y']);
const MT=D.meta||{};const dmy=v=>{if(!v)return '–';const d=new Date(String(v).slice(0,10));return isNaN(d)?String(v):d.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})};
const mlab=m=>{if(!m)return null;const [y,mm]=m.split('-');return new Date(+y,+mm-1,1).toLocaleDateString('en-IN',{month:'long',year:'numeric'})};
function asof(f){const hs=H[f.pair_key]?`Month-end ${mlab(MT.holdings_month)||'–'} (AMC disclosure)`:'Not available for this fund yet';
 return `<h4 style="margin:16px 0 0">Data as of</h4><div class="kv">
 <div><b>NAV & returns</b><span>${dmy(f.nav_date)}</span></div>
 <div><b>Benchmark index (TRI)</b><span>${dmy(MT.tri_date)}</span></div>
 <div><b>Expense ratio (TER)</b><span>${f.ter_date?'effective '+dmy(f.ter_date):'–'}</span></div>
 <div><b>AUM</b><span>${MT.aum_period||'–'}</span></div>
 <div><b>Portfolio holdings</b><span>${hs}</span></div>
 <div><b>Market-cap classes</b><span>${MT.mcap_period?'AMFI list '+MT.mcap_period:'–'}</span></div></div>
 <p class="sub" style="margin-top:6px">Returns are for the Growth option, point-to-point on the NAV date shown, CAGR for periods over 1 year. Other sites may differ if they use a different date, plan (Regular/Direct) or option (IDCW), or price index instead of TRI.</p>`}
function hist(f){if(f.hist3y_n==null)return '';
 return `<h4 style="margin:16px 0 0">Range of past outcomes: every 3-year holding period since ${dmy(f.hist3y_from)} (${f.hist3y_n} weekly start dates)</h4><div class="kv">
 <div><b>Typical (median) 3Y CAGR</b><span>${pct(f.hist3y_median)}</span></div><div><b>Bad case (worst 10%)</b><span>${pct(f.hist3y_p10)}</span></div>
 <div><b>Good case (best 10%)</b><span>${pct(f.hist3y_p90)}</span></div><div><b>Worst / best ever</b><span>${pct(f.hist3y_worst)} / ${pct(f.hist3y_best)}</span></div>
 <div><b>Periods with a gain</b><span>${pct(f.hist3y_pos,0)}</span></div><div><b>Periods above 7% a year</b><span>${pct(f.hist3y_gt7,0)}</span></div></div>
 <p class="sub" style="margin-top:6px">History shows the range investors actually experienced; it is not a forecast.</p>`}
function flowbox(f){if(f.flow_4q==null&&f.flow_1q==null)return '';
 return `<h4 style="margin:16px 0 0">Money flows (estimated from AMFI quarterly average AUM)</h4><div class="kv">
 <div><b>Net flow, latest quarter (${f.flow_quarter||''})</b><span class="${sg(f.flow_1q)}">${f.flow_1q==null?'–':(f.flow_1q>0?'+':'')+pct(f.flow_1q)} of AUM</span></div>
 <div><b>Net flow, last 4 quarters</b><span class="${sg(f.flow_4q)}">${f.flow_4q==null?'–':(f.flow_4q>0?'+':'')+pct(f.flow_4q)} of AUM</span></div>
 <div><b>AUM a year earlier</b><span>${f.aum_1y_ago_cr==null?'–':'₹'+Math.round(f.aum_1y_ago_cr).toLocaleString('en-IN')+' cr'}</span></div></div>
 <p class="sub" style="margin-top:6px">Shown for information. In our 2019–25 test, funds with heavy outflows did not go on to underperform, so flows are not part of the rating.</p>`}
function detail(code){const f=F.find(x=>x.code===code);const pil=Object.keys(f).filter(k=>k.startsWith('pillar_')&&f[k]!=null);
 const hz=D.horizons.map(h=>`<div><b>${h}: return / rank</b><span>${pct(f['ret_'+h])} · ${f['rank_'+h]!=null?f['rank_'+h]+' / '+f['peers_'+h]:'n/a'}</span></div>`).join('');
 const top=(H[f.pair_key]||[]).slice(0,10).map(x=>`<div><b>${x[1]}</b><span>${num(x[2],1)}%</span></div>`).join('');
 const navbox=f.nav_latest==null?'':`<div style="display:flex;gap:28px;flex-wrap:wrap;align-items:baseline;margin-top:12px;padding:10px 14px;border:1px solid var(--line);border-radius:10px">
  <div><div class="mut" style="font-size:12px">NAV (${f.plan_type}, Growth) as on ${dmy(f.nav_date)}</div><div style="font-size:22px;font-weight:600">₹${(+f.nav_latest).toLocaleString('en-IN',{minimumFractionDigits:2,maximumFractionDigits:4})}</div></div>
  ${f.nav_chg_1d==null?'':`<div><div class="mut" style="font-size:12px">1-day change (vs ${dmy(f.nav_prev_date)})</div><div style="font-size:16px" class="${sg(f.nav_chg_1d)}">${f.nav_chg_1d>0?'+':''}${(f.nav_chg_1d*100).toFixed(2)}%</div></div>`}
  <div><div class="mut" style="font-size:12px">AMFI scheme code</div><div style="font-size:16px">${f.code}</div></div></div>`;
 $('#dd').innerHTML=`<h3>${f.name}</h3><div class="sub">${f.amc} · ${f.plan_type} · ${f.peer_group} · ${tier(f.tier)} ${f.flags?`<span class="fl">${flg(f.flags)}</span>`:''}</div>${navbox}
 <div class="kv">${hz}</div><div class="kv">${pil.map(k=>`<div><b>${k.slice(7)} pillar</b><span>${num(f[k])}</span></div>`).join('')}</div>
 <div class="kv">${Object.keys(LBL).filter(k=>f[k]!=null&&f[k]!=='').map(k=>`<div><b>${LBL[k]}</b><span>${PCT.has(k)?pct(f[k]):typeof f[k]==='number'?num(f[k],2):f[k]}</span></div>`).join('')}</div>
 ${hist(f)}${flowbox(f)}${top?`<h4 style="margin:16px 0 0">Top holdings</h4><div class="kv">${top}</div>`:''}${asof(f)}
 <p style="text-align:right;margin:14px 0 0"><button onclick="dlg.close()">Close</button></p>`;$('#dlg').showModal()}
draw();
</script></body></html>"""


def build(folder: Path) -> Path:
    data = (folder / "rankings.json").read_text(encoding="utf-8")
    out = folder / "dashboard.html"
    out.write_text(HTML.replace("__DATA__", data), encoding="utf-8")
    return out
