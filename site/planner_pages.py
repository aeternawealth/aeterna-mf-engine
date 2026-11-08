"""Allocation planner: /plan/ - interactive, browser-only allocation, rebalancing and goal simulator.

The maths lives in site/planner/model.js (tested by tests/planner.test.mjs on thousands of investors and on real
market history); real monthly returns since 2007 are in site/planner/market.json (tools/planner_market.py).
This file builds the page: the questions, the dashboard and the charts.
"""
from pathlib import Path

PATH = "/plan/"
HERE = Path(__file__).resolve().parent

CSS = r"""
<style>
:root{--c-eq:#0b4a3c;--c-debt:#7a9a91;--c-gold:#b08a3e;--c-cash:#b7c0bd;--c-re:#6b5a86;--c-alt:#c2795a;--c-ef:#4f7cac;--c-arb:#9fb7d6;--c-band:rgba(11,74,60,.16);--c-bad:#a4332a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--c-eq:#6cc0ae;--c-debt:#5d7a73;--c-gold:#d3a861;--c-cash:#56615e;--c-re:#9d8cc0;--c-alt:#d99a7f;--c-band:rgba(108,192,174,.2);--c-bad:#e0857b}}
:root[data-theme="dark"]{--c-eq:#6cc0ae;--c-debt:#5d7a73;--c-gold:#d3a861;--c-cash:#56615e;--c-re:#9d8cc0;--c-alt:#d99a7f;--c-band:rgba(108,192,174,.2);--c-bad:#e0857b}
.pl-wrap{max-width:980px}
.pl-prog{display:flex;gap:6px;margin:20px 0 6px}.pl-prog i{flex:1;height:5px;border-radius:3px;background:var(--rule)}.pl-prog i.on{background:var(--teal)}
.pl-step h2{font-size:26px}.pl-step .sub{color:var(--ink-2);margin-top:6px;max-width:70ch}
.pl-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 20px;margin-top:18px}
@media (max-width:640px){.pl-grid{grid-template-columns:1fr}}
.pl-grid .full{grid-column:1/-1}
.pl-f{display:grid;gap:6px}.pl-f>span{font-size:13.5px;color:var(--ink-2)}
.pl-f input,.pl-f select{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:10px 12px;width:100%;min-width:0;font:inherit;color:inherit}
.pl-f input[type=range]{padding:0;border:0;accent-color:var(--teal)}
.pl-f small{color:var(--ink-3);font-size:12.5px;min-height:1em}
.pl-q{margin-top:18px;border:1px solid var(--rule);border-radius:var(--r);padding:16px;background:var(--surface)}
.pl-q legend{font-weight:600;padding:0 4px}.pl-q p{margin:4px 0 10px;color:var(--ink-2);font-size:14px}
.pl-opt{display:flex;gap:10px;align-items:flex-start;padding:9px 10px;border-radius:var(--r);cursor:pointer;font-size:14.5px}
.pl-opt:hover{background:var(--band)}.pl-opt input{margin-top:3px;accent-color:var(--teal)}
.pl-nav{display:flex;justify-content:space-between;gap:12px;margin-top:24px;flex-wrap:wrap}
.pl-goal{display:grid;grid-template-columns:1.4fr 1fr .7fr auto;gap:10px;align-items:end;padding:12px 0;border-bottom:1px dashed var(--rule)}
@media (max-width:640px){.pl-goal{grid-template-columns:1fr 1fr}.pl-goal .gname{grid-column:1/-1}}
.pl-x{border:1px solid var(--rule);background:var(--surface);border-radius:var(--r);padding:9px 12px;cursor:pointer;color:var(--ink-2)}
.pl-err{color:var(--c-bad);font-size:14px;margin-top:10px}
.pl-dash h2{font-size:25px;margin-top:38px}
.pl-dash .tablewrap td,.pl-dash .tablewrap th{white-space:normal}
.pl-k{font:600 26px var(--f-display)}
.pl-meter{position:relative;height:10px;border-radius:5px;background:linear-gradient(90deg,var(--c-debt),var(--c-eq));margin:8px 0 4px}
.pl-meter i{position:absolute;top:-5px;width:4px;height:20px;border-radius:2px;background:var(--ink);transform:translateX(-2px)}
.pl-meter-l{display:flex;justify-content:space-between;font-size:12px;color:var(--ink-3)}
.pl-flag{border-left:3px solid var(--brass);padding:10px 14px;background:var(--surface);border-radius:0 var(--r) var(--r) 0;margin-top:10px;font-size:14.5px}
.pl-flag.ok{border-left-color:var(--teal)}
.pl-donuts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px;margin-top:14px}
@media (max-width:640px){.pl-donuts{grid-template-columns:1fr}}
.pl-donut{display:flex;gap:16px;align-items:center}.pl-donut svg{flex:none}
.pl-donut ul{list-style:none;padding:0;margin:0;font-size:13.5px;display:grid;gap:4px}.pl-donut li b{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:7px}
.pl-goals{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin-top:14px}
.pl-gc{display:grid;gap:8px}.pl-gc h3{font-size:18px}
.pl-mix{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--rule)}.pl-mix span{height:100%}
.pl-prob{display:flex;align-items:center;gap:10px}.pl-prob svg{flex:none}
.pl-bar{display:flex;height:28px;border-radius:var(--r);overflow:hidden;border:1px solid var(--rule)}.pl-bar span{display:block;height:100%}
.pl-ctrl{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px 18px}
@media (max-width:820px){.pl-ctrl{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:480px){.pl-ctrl{grid-template-columns:1fr}}
.pl-sticky{position:sticky;top:64px;z-index:5;background:var(--paper);padding:10px 0;border-bottom:1px solid var(--rule)}
.pl-tl{display:grid;gap:14px;margin-top:12px}.pl-tl>div{border-left:2px solid var(--teal-soft);padding:2px 0 2px 16px}
.pl-tl b{display:block;font:600 16px var(--f-display)}.pl-tl ul{margin:6px 0 0;padding-left:18px;font-size:14.5px}
.pl-busy{opacity:.55;transition:opacity .15s}
.pl-verdict{border-left:4px solid var(--teal)}.pl-verdict.bad{border-left-color:var(--c-bad)}
.pl-act{margin:14px 0 0;padding:0;list-style:none;counter-reset:a;display:grid;gap:10px}
.pl-act li{counter-increment:a;position:relative;background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:14px 16px 14px 54px}
.pl-act li::before{content:counter(a);position:absolute;left:16px;top:14px;width:26px;height:26px;border-radius:50%;background:var(--teal);color:var(--paper);font:600 14px/26px var(--f-mono);text-align:center}
.pl-act b{font:600 16px var(--f-display)}.pl-act p{margin:6px 0 0;font-size:14.5px}
.pl-fan text{font:11px var(--f-mono);fill:var(--ink-3)}.pl-fan{overflow:hidden;display:block}
.pl-fanwrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
@media (max-width:640px){.pl-fan{min-width:640px}.pl-fanwrap::after{content:'Swipe the chart to see all of it';display:block;font-size:12px;color:var(--ink-3);margin-top:4px}}
@media print{header,footer,.pl-nav,.pl-noprint{display:none!important}.card{break-inside:avoid}.pl-sticky{position:static}}
</style>
"""

HTML = r"""
<section class="band" style="padding-top:28px"><div class="wrap pl-wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/calculators/">Calculators</a> › Allocation planner</nav>
<div class="eyebrow" style="margin-top:16px">Allocation planner</div>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:8px">How should your money be split?</h1>
<p class="lede" style="margin-top:12px">A plan built around your goals, your finances and how you handle market falls: the mix of equity, debt and gold for each goal, what to change in what you hold today, how much to invest each month, and the chance of reaching each goal, tested on real Indian market history since 2007.</p>
<p class="muted" style="font-size:13.5px;margin-top:8px">About 6 minutes. Everything stays in your browser; nothing is sent to us unless you choose to share your summary.</p>
<div class="pl-prog" id="plProg" aria-hidden="true"></div>
<p class="muted mono" style="font-size:12.5px" id="plStepLbl"></p>
<div id="plBody" class="card pl-step" style="margin-top:8px"></div>
<noscript><p class="note">The planner needs JavaScript.</p></noscript>
__FAQ__
<details class="faq pl-noprint" style="margin-top:14px"><summary>How the planner works</summary>
<div style="padding:4px 0 8px;max-width:82ch;font-size:14.5px">
<p><b>Foundations first.</b> Expensive debt is cleared before investing; an emergency fund of 6 months' expenses and EMIs is built (9 if your income varies, 2 more with dependants on one income, 12 in retirement); term and health cover are checked.</p>
<p><b>Two risk scores.</b> Your answers give your risk <i>tolerance</i>; your finances give your risk <i>capacity</i>: years until you stop working, EMIs as a share of income, your surplus, how steady your income is, who depends on you, and age. The lower of the two sets your profile, and with it the most equity your long-term money holds: 25% for the most cautious, up to 85% for the boldest.</p>
<p><b>One mix per goal, from real data.</b> We replayed thousands of sequences of real Indian market months since 2007 (equity, debt and gold together, in 12-month blocks so crashes and recoveries stay intact) and measured, for every horizon and equity share, the chance of ending below the money put in. Each goal holds the most equity whose chance of loss stays within your profile's limit, and never more than 15% at 3 years, 35% at 5 years or 55% at 7 years. Money needed within 3 years holds no equity. Every year, each goal's money is moved towards safety as its date approaches.</p>
<p><b>Monthly amounts that hold up in bad markets.</b> Each goal's SIP is the amount that reached its target in 3 out of 4 simulated markets (you can choose 1 in 2 or 9 in 10), not a single assumed return, which would only work half the time. Retirement is sized from the expenses you expect in retirement, for the years to your life expectancy, still growing with inflation. Future EPF and NPS contributions count towards it.</p>
<p><b>Rebalancing</b> steers new money into whatever is underweight first, because selling costs tax and exit loads; switching is suggested only when an asset class is more than 10 percentage points off target. EPF, PPF and NPS cannot be moved and are left as they are.</p>
<p><b>Tested.</b> The model is checked on 3,000 simulated investors of every age, income and risk appetite (allocations must add up, never invest more than the surplus, never more equity for shorter goals or tighter finances), and on every start month since 2007: plans built for a 3-in-4 chance reached their targets in 78 to 98% of real start months.</p>
</div></details>
<p class="muted" style="font-size:12.5px;margin-top:18px;max-width:90ch">Indicative and educational only: not investment advice, a recommendation of any scheme, or a guarantee of returns. Simulations replay past market months; the future can be worse. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889), not a SEBI-registered investment adviser. Insurance and loan points are general checks; please review them with a qualified professional.</p>
</div></section>
"""

UI = r"""
(function(){
const PM=window.PlannerModel, MKT=window.PLANNER_MARKET;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inr=v=>v==null||!isFinite(v)?'–':'₹'+Math.round(v).toLocaleString('en-IN');
const inrS=v=>{if(v==null||!isFinite(v))return'–';const a=Math.abs(v),sg=v<0?'−':'';return sg+(a>=1e7?'₹'+(a/1e7).toFixed(2)+' cr':a>=1e5?'₹'+(a/1e5).toFixed(a<1e6?2:1).replace(/\.?0+$/,'')+' lakh':inr(a))};
const pc=(v,d=0)=>v==null||!isFinite(v)?'–':(v*100).toFixed(d)+'%';
const KEY='aeterna-plan-v2';
const blank={age:'',retireAge:60,lifeExp:90,retireOther:'',retireExpPct:70,dependants:'0',earners:'1',incomeType:'salaried',slab:'30',income:'',expenses:'',homeEmi:'',otherEmi:'',loanOut:'',hiDebt:'',hiRate:'',epfMonthly:'',
  efund:'',termCover:'',healthCover:'',goals:[{name:'Retirement',type:'retire',cost:'',years:''}],
  investing:'yes',eqmf:'',stocks:'',topStock:'',nfunds:'',fd:'',debtmf:'',savings:'',gold:'',epf:'',ppf:'',nps:'',npsEq:'50',realestate:'',alt:'',
  retireIncome:'',q:{},rEq:11,rDebt:7,rGold:8,rCash:6,infl:6,stepup:10,confidence:75,investShare:85};
let S;try{S=Object.assign(JSON.parse(JSON.stringify(blank)),JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){S=JSON.parse(JSON.stringify(blank))}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const n=k=>{const v=parseFloat(String(S[k]??'').replace(/,/g,''));return isFinite(v)?v:0};
let step=0;

const QS=[
 {id:'fall',t:'Markets fall and your portfolio is down 20% in three months.',p:'On ₹10 lakh, that is ₹2 lakh gone on paper. What do you do?',o:['Sell everything; I cannot sleep with losses','Sell part of it to limit the damage','Hold and wait for a recovery','Invest more while prices are low']},
 {id:'range',t:'Which range of outcomes would you pick for ₹10 lakh over 5 years?',p:'Wider ranges have a higher average but a worse bad case.',o:['₹12 to 13.5 lakh: steady, small gains','₹11 to 15.5 lakh','₹10 to 18 lakh','₹8 to 22 lakh: the most upside, can end below what I put in']},
 {id:'aim',t:'What matters more to you for long-term money?',p:'',o:['Not losing what I have','Steady income with a little growth','A balance of growth and stability','The highest growth, accepting big swings']},
 {id:'exp',t:'How much investing experience do you have?',p:'',o:['Savings accounts and FDs only','Mutual funds or SIPs for less than 3 years','Mutual funds or shares through at least one big fall (2020, 2022)','10 years or more, including several crashes']},
 {id:'past',t:'In the last big market fall (for example March 2020), what did you do?',p:'',o:['I was not invested in shares then','I sold some or all','I did nothing','I invested more']},
 {id:'see',t:'You open your app and see your equity holdings down sharply.',p:'',o:['I would stop investing for a while','I would worry and check every day','I would be uneasy but carry on','I would barely notice; it is long-term money'],dyn:true}];

const hint=v=>{const x=parseFloat(v);return isFinite(x)&&x>0?inrS(x):''};
const F=(k,label,o={})=>`<label class="pl-f ${o.full?'full':''}"><span>${label}</span>${o.sel?`<select data-k="${k}">${o.sel.map(([v,t])=>`<option value="${v}"${String(S[k])===String(v)?' selected':''}>${t}</option>`).join('')}</select>`
  :`<input data-k="${k}" type="number" inputmode="decimal" min="0" value="${esc(S[k])}" placeholder="${o.ph||''}"${o.money?' data-money="1"':''}>`}<small data-h="${k}">${o.money?esc(hint(S[k])):(o.hint||'')}</small></label>`;
const M=(k,label,o={})=>F(k,label,Object.assign({money:1,ph:'₹'},o));
const retired=()=>S.incomeType==='retired';
const STEPS=[
 {t:'About you',s:'Who depends on you and how steady your income is shape how much risk your finances can absorb.',
  h:()=>`<div class="pl-grid">${F('incomeType','Your income',{sel:[['salaried','Salaried, steady'],['variable','Salaried with a large variable part, or commission'],['business','Business or self-employed'],['retired','Retired: pension or investments']],full:1})}
   ${F('age','Your age',{ph:'e.g. 34'})}${retired()?'<span></span>':F('retireAge','Age you plan to stop working',{ph:'60'})}
   ${F('dependants','People who depend on your income',{sel:[['0','None'],['1','1'],['2','2'],['3','3 or more']]})}
   ${F('earners','Earning members in the household',{sel:[['1','Only me'],['2','Two or more']]})}
   ${F('slab','Your income-tax slab',{sel:[['0','No tax / up to 5%'],['10','10%'],['20','15–20%'],['30','25–30%']],hint:'Decides between arbitrage and liquid funds for short-term money.',full:1})}</div>`},
 {t:'Monthly cash flow',s:'Take-home figures, a month. Your home loan EMI counts here even though your home is not part of your investments.',
  h:()=>`<div class="pl-grid">${M('income',retired()?'Monthly income (pension, rent, interest)':'Take-home income (household)')}${M('expenses','Living expenses, excluding EMIs')}
   ${M('homeEmi','Home loan EMI')}${M('otherEmi','Other EMIs (car, education, personal)')}
   ${M('loanOut','Total loans still outstanding',{hint:'All loans together, to size life cover.'})}${M('hiDebt','Of which: credit card or personal loan balance')}
   ${F('hiRate','Interest on that expensive debt (% a year)',{ph:'e.g. 14'})}${retired()?'':M('epfMonthly','EPF and NPS going in each month (you + employer)',{hint:'Counts towards retirement.'})}</div>`},
 {t:'Safety net',s:'Money set aside for emergencies, and your insurance. These come before investing.',
  h:()=>`<div class="pl-grid">${M('efund','Emergency fund (money kept aside, not counted below)',{full:1})}
   ${M('termCover','Term life cover (sum assured)')}${M('healthCover','Health insurance cover (family)')}</div>`},
 {t:'Your goals',s:'What the money is for. Cost in today\'s rupees; inflation is added. Retirement is sized for you, or enter your own figure.',
  h:()=>`<div id="plGoals">${S.goals.map((g,i)=>goalRow(g,i)).join('')}</div>
   <div class="row" style="margin-top:14px"><button type="button" class="btn" id="plAddG">Add a goal</button>
   <select id="plPreset" class="pl-x" aria-label="Goal ideas"><option value="">Goal ideas…</option>${["Child's higher education","Child's wedding","Home down payment","Car","Foreign holiday","Start a business","Parents' care"].map(x=>`<option>${x}</option>`).join('')}</select></div>
   ${retired()?'':`<div class="pl-grid" style="margin-top:20px">${M('retireIncome','Monthly spending you will need in retirement, in today’s money',{hint:n('expenses')?'Leave blank to use 70% of today’s expenses: '+inrS(n('expenses')*.7)+' a month':''})}${M('retireOther','Rent, pension or other income that continues in retirement, a month',{hint:'In today’s money. Reduces what your investments must pay.'})}${F('lifeExp','Plan for the money to last until age',{sel:[['85','85'],['90','90 (suggested)'],['95','95'],['100','100']],full:1})}</div>`}`},
 {t:'What you already hold',s:'Today\'s value of each. Leave out the home you live in. Rough figures are fine.',
  h:()=>`<div class="seg" role="group" aria-label="Investing already?" style="margin-top:14px"><button type="button" data-inv="yes" aria-pressed="${S.investing!=='no'}">I already invest</button><button type="button" data-inv="no" aria-pressed="${S.investing==='no'}">Not yet</button></div>
   ${S.investing==='no'?'<p class="muted" style="margin-top:14px">The plan will give you a starting mix and how much to invest each month. If you have EPF or PPF, add it; it counts towards retirement.</p><div class="pl-grid">'+M('epf','EPF / VPF')+M('ppf','PPF and Sukanya Samriddhi')+'</div>'
   :`<div class="pl-grid">${M('eqmf','Equity and hybrid mutual funds')}${M('stocks','Shares held directly')}
   ${F('topStock','Your largest single share, as % of all your investments',{ph:'e.g. 8'})}${F('nfunds','Number of equity funds you hold',{ph:'e.g. 6'})}
   ${M('fd','Fixed deposits, bonds, RBI bonds')}${M('debtmf','Debt and liquid mutual funds')}
   ${M('savings','Savings account balance beyond the emergency fund')}${M('gold','Gold: coins, SGBs, gold funds (not jewellery you wear)')}
   ${M('epf','EPF / VPF')}${M('ppf','PPF and Sukanya Samriddhi')}${M('nps','NPS')}${F('npsEq','Equity share of your NPS (%)',{ph:'50'})}
   ${M('realestate','Property other than your own home')}${M('alt','Other: PMS, AIF, unlisted shares, crypto')}</div>`}`},
 {t:'How you handle risk',s:'There are no right answers. Answer for how you would really behave, not how you would like to.',
  h:()=>QS.map(q=>`<fieldset class="pl-q"><legend>${esc(q.dyn?seeText():q.t)}</legend>${q.p?`<p>${esc(q.p)}</p>`:''}${q.o.map((o,i)=>`<label class="pl-opt"><input type="radio" name="q_${q.id}" value="${i+1}"${S.q[q.id]==i+1?' checked':''}><span>${esc(o)}</span></label>`).join('')}</fieldset>`).join('')}];
const seeText=()=>{const eq=n('eqmf')+n('stocks');return eq>0?`Your equity, now ${inrS(eq)}, shows ${inrS(-eq*0.3)} (down 30%) when you open your app.`:QS[5].t};
const goalRow=(g,i)=>`<div class="pl-goal" data-i="${i}"><label class="pl-f gname"><span>Goal</span><input data-g="name" value="${esc(g.name)}" ${g.type==='retire'?'readonly':''}></label>
  <label class="pl-f"><span>${g.type==='retire'?'Corpus (optional)':'Cost in today\'s ₹'}</span><input data-g="cost" type="number" min="0" inputmode="decimal" value="${esc(g.cost)}" placeholder="${g.type==='retire'?'Sized for you':'₹'}"><small>${esc(hint(g.cost))}</small></label>
  <label class="pl-f"><span>In years</span><input data-g="years" type="number" min="0" max="60" value="${esc(g.type==='retire'?(n('age')?Math.max(0,n('retireAge')-n('age')):''):g.years)}" ${g.type==='retire'?'readonly':''}></label>
  ${g.type==='retire'?'<span></span>':`<button type="button" class="pl-x" data-del="${i}" aria-label="Remove ${esc(g.name)}">Remove</button>`}</div>`;

function render(){
  const total=STEPS.length;
  S.goals=S.goals.filter(g=>g.type!=='retire'||!retired());if(!retired()&&!S.goals.some(g=>g.type==='retire'))S.goals.unshift({name:'Retirement',type:'retire',cost:'',years:''});
  $('#plProg').innerHTML=Array.from({length:total+1},(_,i)=>`<i class="${i<=step?'on':''}"></i>`).join('');
  if(step>=total){$('#plStepLbl').textContent='Your plan';$('#plBody').className='pl-dash';dashboard();return}
  $('#plBody').className='card pl-step';$('#plStepLbl').textContent=`Step ${step+1} of ${total}`;
  const st=STEPS[step];
  $('#plBody').innerHTML=`<h2>${st.t}</h2><p class="sub">${st.s}</p>${st.h()}<div class="pl-err" id="plErr" role="alert"></div>
   <div class="pl-nav">${step?'<button type="button" class="btn" id="plBack">Back</button>':'<span></span>'}<button type="button" class="btn primary" id="plNext">${step===total-1?'See my plan':'Next'}</button></div>`;
  $$('#plBody [data-k]').forEach(el=>el.addEventListener('input',()=>{S[el.dataset.k]=el.value;const h=$(`[data-h="${el.dataset.k}"]`);if(h&&el.dataset.money)h.textContent=hint(el.value);save()}));
  $$('#plBody input[type=radio]').forEach(el=>el.addEventListener('change',()=>{S.q[el.name.slice(2)]=+el.value;save()}));
  $$('#plBody [data-inv]').forEach(b=>b.onclick=()=>{S.investing=b.dataset.inv;if(S.investing==='no')['eqmf','stocks','topStock','nfunds','fd','debtmf','savings','gold','nps','realestate','alt'].forEach(k=>S[k]='');save();render()});
  const it=$('#plBody [data-k="incomeType"]');if(it)it.addEventListener('change',()=>render());
  if(step===3)bindGoals();
  $('#plNext').onclick=()=>{const er=check();if(er){$('#plErr').textContent=er;return}step++;render();window.scrollTo({top:$('#plProg').getBoundingClientRect().top+scrollY-90,behavior:'smooth'})};
  if(step)$('#plBack').onclick=()=>{step--;render()};
}
function bindGoals(){
  $$('#plGoals [data-g]').forEach(el=>el.addEventListener('input',()=>{const i=+el.closest('.pl-goal').dataset.i;S.goals[i][el.dataset.g]=el.value;const sm=el.parentElement.querySelector('small');if(sm&&el.dataset.g==='cost')sm.textContent=hint(el.value);save()}));
  $$('#plGoals [data-del]').forEach(b=>b.onclick=()=>{S.goals.splice(+b.dataset.del,1);save();render()});
  $('#plAddG').onclick=()=>{S.goals.push({name:'',cost:'',years:''});save();render()};
  $('#plPreset').onchange=e=>{if(e.target.value){S.goals.push({name:e.target.value,cost:'',years:''});save();render()}};
}
function check(){
  if(step===0&&!(n('age')>=18&&n('age')<=90))return 'Please enter your age (18 to 90).';
  if(step===0&&!retired()&&n('retireAge')<=n('age'))return 'The age you plan to stop working should be later than your age, or choose Retired.';
  if(step===1&&!(n('income')>0))return 'Please enter your monthly income.';
  if(step===1&&!(n('expenses')>0))return 'Please enter your monthly living expenses.';
  if(step===3){for(const g of S.goals){if(g.type!=='retire'&&(!g.name||!(+g.cost>0)||!(+g.years>=0)||+g.years>60))return 'Each goal needs a name, a cost and the years until you need it (or remove it).'}}
  if(step===5&&QS.some(q=>!S.q[q.id]))return 'Please answer every question.';
  return '';
}

/* ---------- charts ---------- */
const COL={Equity:'var(--c-eq)',Debt:'var(--c-debt)',Gold:'var(--c-gold)','Arbitrage & liquid':'var(--c-arb)',Cash:'var(--c-cash)','Emergency fund':'var(--c-ef)','Real estate':'var(--c-re)',Other:'var(--c-alt)'};
function donut(o,title,sub){
  const t=Object.values(o).reduce((a,b)=>a+b,0)||1, R=52, C=2*Math.PI*R; let off=0;
  const arcs=Object.entries(o).filter(([,v])=>v>0).map(([k,v])=>{const len=v/t*C;const a=`<circle r="${R}" cx="64" cy="64" fill="none" stroke="${COL[k]}" stroke-width="20" stroke-dasharray="${len} ${C-len}" stroke-dashoffset="${-off}" transform="rotate(-90 64 64)"><title>${k} ${pc(v/t)}</title></circle>`;off+=len;return a}).join('');
  const li=Object.entries(o).filter(([,v])=>v>0).map(([k,v])=>`<li><b style="background:${COL[k]}"></b>${k} <span class="mono">${pc(v/t)}</span> <span class="muted">${inrS(v)}</span></li>`).join('');
  return `<div class="card pl-donut"><svg width="128" height="128" viewBox="0 0 128 128" role="img" aria-label="${esc(title)}">${arcs}<text x="64" y="60" text-anchor="middle" style="font:600 13px var(--f-display);fill:var(--ink)">${esc(title)}</text><text x="64" y="77" text-anchor="middle" style="font:12px var(--f-mono);fill:var(--ink-3)">${esc(sub)}</text></svg><ul>${li}</ul></div>`;
}
const mixBar=m=>`<div class="pl-mix" role="img" aria-label="${pc(m.eq)} equity, ${pc(m.debt)} debt, ${pc(m.gold)} gold"><span style="width:${m.eq*100}%;background:var(--c-eq)"></span><span style="width:${m.debt*100}%;background:var(--c-debt)"></span><span style="width:${m.gold*100}%;background:var(--c-gold)"></span></div>`;
function gauge(p){const R=22,C=2*Math.PI*R,col=p>=.7?'var(--teal)':p>=.45?'var(--brass)':'var(--c-bad)';
  return `<svg width="56" height="56" viewBox="0 0 56 56" aria-hidden="true"><circle r="${R}" cx="28" cy="28" fill="none" stroke="var(--rule)" stroke-width="6"/><circle r="${R}" cx="28" cy="28" fill="none" stroke="${col}" stroke-width="6" stroke-linecap="round" stroke-dasharray="${C*p} ${C}" transform="rotate(-90 28 28)"/><text x="28" y="32" text-anchor="middle" style="font:600 12px var(--f-mono);fill:var(--ink)">${Math.round(p*100)}%</text></svg>`}
function axis(maxRaw){
  const e=Math.pow(10,Math.floor(Math.log10(Math.max(1,maxRaw/4)))), f=maxRaw/4/e, st=(f<=1?1:f<=2?2:f<=2.5?2.5:f<=5?5:10)*e;
  const top=Math.ceil(maxRaw/st)*st, t=[];for(let v=0;v<=top+1e-6;v+=st)t.push(v);return {top,t};
}
const shortR=v=>v>=1e7?((v/1e7)>=100?Math.round(v/1e7):+(v/1e7).toFixed(v/1e7>=10?0:1))+' cr':v>=1e5?Math.round(v/1e5)+' L':v>0?Math.round(v/1e3)+'k':'0';
function chartLabel(xx,txt,yy,col,W,L,Rp){
  const w=txt.length*6.7, right=xx+4+w<=W-Rp, ok=xx-4-w>=L;
  const anchor=right?'start':'end', x0=right?xx+4:Math.max(L+w,xx-4);
  return `<text x="${x0}" y="${yy}" text-anchor="${anchor}" style="fill:${col}">${esc(txt)}</text>`;
}
function fan(sim,res){
  const nl=(sim.payouts||[]).length+(res.retire?1:0);
  const F=sim.fan, W=760, H=300+nl*12, L=70, Rp=16, T=14+nl*13, B=34; if(!F.length)return '';
  const p90=Math.max(...F.map(f=>f.p90)), p50=Math.max(...F.map(f=>f.p50)), start0=res.total-res.cur['Real estate']-res.cur.Other;
  const capped=p90>2.2*p50, ax=axis((capped?2.2*p50:p90)*1.02||1), maxV=ax.top;
  const years=F.length, x=i=>L+(W-L-Rp)*i/years, y=v=>T+(H-T-B)*(1-Math.min(v,maxV)/maxV);
  const start=res.total-res.cur['Real estate']-res.cur.Other, age0=res.s.age;
  const pts=k=>[`${x(0)},${y(start)}`].concat(F.map((f,i)=>`${x(i+1)},${y(f[k])}`));
  const band=pts('p90').concat(pts('p10').reverse()).join(' ');
  const ticks=ax.t.map(v=>`<line x1="${L}" x2="${W-Rp}" y1="${y(v)}" y2="${y(v)}" stroke="var(--rule)"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end">₹${shortR(v)}</text>`).join('');
  const step=years>30?5:years>12?2:1;
  const xt=F.map((f,i)=>(i+1)%step===0?`<text x="${x(i+1)}" y="${H-14}" text-anchor="middle">${f.age}</text>`:'').join('')+`<text x="${(L+W)/2}" y="${H-1}" text-anchor="middle">Your age</text>`;
  const lab=(xx,txt,row,col)=>`<line x1="${xx}" x2="${xx}" y1="${10+row*13+3}" y2="${T}" stroke="${col}" stroke-width=".8"/>${chartLabel(xx,txt,10+row*13,col,W,L,Rp)}`;
  const gm=(sim.payouts||[]).map((pp,i)=>`<line x1="${x(pp.y)}" x2="${x(pp.y)}" y1="${T}" y2="${H-B}" stroke="var(--brass)" stroke-dasharray="3 3"/>${lab(x(pp.y),`${pp.name.slice(0,24)}: −${inrS(pp.today)} (today's money)`,i,'var(--brass)')}`).join('');
  const R=res.retire, rx=R?x(R.y):null;
  const rm=R&&R.y<=years?`<rect x="${rx}" y="${T}" width="${W-Rp-rx}" height="${H-T-B}" fill="var(--band)" opacity=".6"/><line x1="${rx}" x2="${rx}" y1="${T}" y2="${H-B}" stroke="var(--teal)" stroke-dasharray="4 3"/>${lab(rx,`Retire at ${res.s.retireAge}: spend ${inrS(R.monthlyToday)} a month (today's money)`,(sim.payouts||[]).length,'var(--teal)')}`:'';
  return `<div class="pl-fanwrap"><svg class="pl-fan" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Range of outcomes for your investments, to age ${age0+years}">${rm}${ticks}<polygon points="${band}" fill="var(--c-band)"/>
   <polyline points="${pts('p50').join(' ')}" fill="none" stroke="var(--c-eq)" stroke-width="2.5"/>${gm}${xt}</svg></div>
   <div class="row" style="gap:18px;font-size:12.5px;color:var(--ink-2)"><span><b style="display:inline-block;width:14px;height:10px;background:var(--c-band);margin-right:6px"></b>8 in 10 outcomes fall in this band</span><span><b style="display:inline-block;width:14px;height:3px;background:var(--c-eq);vertical-align:middle;margin-right:6px"></b>Typical outcome</span><span style="color:var(--brass)">┆ Money spent on a goal</span>${R?'<span>Shaded: retirement, living off the corpus</span>':''}<span class="muted">All amounts in today's money${capped?'; the top of the band (best 1 in 10 markets) is cut off to keep the scale readable':''}</span></div>`;
}

/* ---------- what to do now ---------- */
const SRCN={savings:'savings account',debtmf:'debt funds',fd:'FDs',eqmf:'equity funds',stocks:'shares',gold:'gold',locked:'EPF, PPF and NPS'};
function actions(m,sim,m90){
  const s=m.s, A=[], prob=Object.fromEntries(sim.goals.map(g=>[g.name,g])), arb=s.slab>=20;
  const srcTxt=src=>src.map(([k,v])=>`${inrS(v)} from ${SRCN[k]}`).join(', ');
  if(m.r.surplus<=0)A.push(['Create a monthly surplus first','Your EMIs and expenses use all of your income. Trim expenses, or refinance or prepay the costliest loan; nothing below works without it.']);
  if(m.payDebt)A.push([`Pay off ${inrS(s.hiDebt)} of expensive debt`,`Put ${inr(m.debtPay)} a month towards it until it is gone (about ${Math.ceil(s.hiDebt/Math.max(1,m.debtPay))} months). At ${s.hiRate||'double-digit'}% interest, this beats any fund.`]);
  if(m.efGap0>0)A.push([`Set up your emergency fund: ${inrS(m.efTarget)}`,(m.efTop>0?`This week, move ${srcTxt(Object.entries(m.efFrom))} into ${arb?'an arbitrage fund, keeping a month or two of expenses in a liquid fund for instant access':'a liquid fund'}. `:'')+(m.efGap>0?`Add ${inr(m.efPay)} a month for the remaining ${inrS(m.efGap)}.`:'')]);
  for(const g of m.G){
    if(g.ret||g.y<=0)continue;
    const where=g.y<3?(arb?'arbitrage funds (or liquid funds for money needed within months)':'liquid or money market funds'):g.y<5?'equity savings funds':g.y<7?'balanced advantage funds':'the equity, debt and gold mix shown on the goal';
    const fromEq=g.sources.filter(([k])=>k==='eqmf'||k==='stocks').reduce((a,[,v])=>a+v,0);
    const pr=prob[g.name]||{};
    let t=`${g.name}, in ${g.y} year${g.y>1?'s':''}: ${inrS(g.fv)} then (${inrS(g.today||0)} today).`;
    let d=g.have>0?`Set aside ${inrS(g.have)} now: ${srcTxt(g.sources)}. Keep it in ${where}. `:'';
    if(fromEq>0&&g.y<7)d+=`Switch the ${inrS(fromEq)} from equity ${g.y<3?'now: a fall now could not be recovered before the date':'over the next 3 to 6 months'}; long-term gains above ₹1.25 lakh a year are taxed at 12.5%. `;
    if(g.sip>0)d+=g.funded>=.999?`Then invest ${inr(g.f2)} a month into the same.`:`It needs ${inr(g.sip)} a month; the plan can give it ${inr(g.f2)}.`;
    else if(g.have>0)d+='Nothing more is needed each month.';
    if(pr.prob!=null)d+=` Chance of having the full amount: ${pc(pr.prob)}.`;
    A.push([t,d]);
  }
  const R=m.retire;
  if(R){const g=m.G.find(x=>x.ret), pr=prob[g.name]||{};
    let d=(R.other>0?`${inrS(R.spendToday)} a month, less ${inrS(R.other)} of rent or pension, leaves ${inrS(R.monthlyToday)} a month for your investments to pay (today's money); `:`${inrS(R.monthlyToday)} a month in today's money `)+`that is ${inrS(R.monthlyThen)} a month when you retire, rising with inflation after that. To pay it until ${s.lifeExp}, you need about ${inrS(R.corpus)} at ${s.retireAge}. `;
    d+=`Earmarked today: ${inrS(R.have)} (${srcTxt(g.sources)}), worth about ${inrS(R.haveThen)} by then${R.extra>0?`, plus ${inrS(R.extra)} from future EPF and NPS`:''}. `;
    d+=R.sip>0?(g.funded>=.999?`<b>Invest ${inr(R.fund)} a month</b>${s.stepup?`, rising ${s.stepup}% a year`:''} towards it.`:`It needs ${inr(R.sip)} a month; the plan can give it ${inr(R.fund)} (${pc(g.funded)}).`):`Your earmarked money already covers it: nothing more is needed each month.`;
    d+=` <b>Chance the money lasts until ${s.lifeExp}: ${pc(pr.prob)}</b>${pr.p10age!=null?`; in weak markets (1 in 10) it lasts until about ${isFinite(pr.p10age)?Math.floor(pr.p10age):s.lifeExp+'+'}`:''}.`;
    A.push([`Retirement at ${s.retireAge}: ${inrS(R.spendToday)} a month in today's money, until ${s.lifeExp}`,d+' The retirement income plan below shows how the money is drawn and what protects it if you live longer.']);}
  if(m.termGap>0)A.push([`Buy ${inrS(m.termGap)} more term life cover`,`Suggested total about ${inrS(m.termNeed)}; you have ${inrS(s.termCover)}. A plain term plan; please check with an insurance professional.`]);
  if(m.healthGap>0)A.push([`Raise health cover to ${inrS(m.healthNeed)} or more`,`You have ${inrS(s.healthCover)}. A super top-up is a cheap way to add cover.`]);
  if(s.nfunds>7)A.push([`Cut ${s.nfunds} equity funds down to 5 or 6`,'They overlap heavily. Keep one or two per category in the plan; switch the rest as part of the moves above, oldest units first to keep tax low.']);
  if(s.topStock>10)A.push([`Trim the share that is ${s.topStock}% of your investments`,'Bring it under 10% over a few months; stop adding to it.']);
  const short=m.G.filter(g=>g.sip>0&&g.funded<.999);
  if(short.length){const o=m.option;
    A.push([`Close the gap of ${inr(m.need-m.later.avail)} a month`,`Your goals need ${inr(m.need)} a month and ${inr(m.later.avail)} is available. `+(o&&!o.none?(o.retire?`Stop working ${o.years} year${o.years>1?'s':''} later, `:`Push "${esc(o.goal)}" out by ${o.years} year${o.years>1?'s':''}, `)+`or raise the yearly step-up, or use the ${100-s.investShare}% buffer.`:`Trim a goal, push one out, or raise the yearly step-up.`)]);}
  if(m.wealth>500&&m.G.length)A.push([`Optional: invest some of the remaining ${inr(m.wealth)} a month`,`Your goals are covered without it, so you may spend it. Whatever you do invest goes into ${pc(m.wealthMix.eq)} equity, ${pc(m.wealthMix.debt)} debt and ${pc(m.wealthMix.gold)} gold, and is a reserve if markets are weak in retirement.`]);
  if(m90&&!short.length&&s.confidence<90){const extra=m90.need-m.need; if(extra>500)A.push([`For more margin: ${inr(extra)} a month more`,`That would give every goal a 9-in-10 chance (planning for bad markets too). `+(extra<=m.wealth?`It fits within the ${inr(m.wealth)} left over each month.`:m.wealth>500?`The ${inr(m.wealth)} left over each month covers ${pc(m.wealth/extra)} of it.`:'')]);}
  return A;
}

/* ---------- dashboard ---------- */
let lastRes=null;
function compute(){const res=PM.plan(S,MKT,{nConf:900});const sim=PM.simulate(res,MKT,{n:500});lastRes=res;
  let m90=null;try{if(+S.confidence<90)m90=PM.plan(Object.assign({},S,{confidence:90}),MKT,{nConf:600})}catch(e){}
  let alt=[];try{if(res.retire){const b=res.retire.spendToday;alt=[1,1.25,1.5].map(k=>{const r2=k===1?res:PM.plan(Object.assign({},S,{retireIncome:Math.round(b*k/5000)*5000}),MKT,{nConf:600});
    const g=r2.G.find(x=>x.ret);return {inc:r2.retire.spendToday,net:r2.retire.monthlyToday,sip:g.sip,need:r2.need,ok:r2.need<=r2.avail+1,corpus:r2.retire.corpus}})}}catch(e){}
  let ages=[];try{if(res.retire)ages=[85,90,95,100].map(a=>{const r2=a===+S.lifeExp?res:PM.plan(Object.assign({},S,{lifeExp:a}),MKT,{nConf:500});const g=r2.G.find(x=>x.ret);return {age:a,sip:g.sip,need:r2.need,corpus:r2.retire.corpus}})}catch(e){}
  return {res,sim,m90,alt,ages}}
function dashboard(){
  $('#plBody').innerHTML=`<div class="card"><p>Running your plan through 19 years of real market months…</p></div>`;
  setTimeout(()=>{const {res,sim,m90,alt,ages}=compute();SW.amount=null;$('#plBody').innerHTML=dashHtml(res,sim,m90,alt,ages);bindDash(res);bindSwp(res)},20);
}
function flagsOf(m){
  const s=m.s, f=[], tot=m.total, sh=k=>tot?m.cur[k]/tot:0;
  if(m.r.surplus<=0)f.push(['Your EMIs and expenses use all of your income.','The first step is creating a monthly surplus: trim expenses, or refinance or prepay the costliest loan.']);
  if(m.payDebt)f.push([`${inrS(s.hiDebt)} of expensive debt${s.hiRate?' at '+s.hiRate+'%':''}.`,`Clearing it is a guaranteed ${s.hiRate||'double-digit'}% return, more than any fund. 60% of your surplus goes here until it is gone.`]);
  const efWhere=s.slab>=20?'an arbitrage fund (taxed as equity, so better than an FD in your slab), with a month or two in a liquid fund for instant access':'a liquid fund';
  const fromTxt=Object.entries(m.efFrom).map(([k,v])=>`${inrS(v)} from your ${({savings:'savings account',debtmf:'debt funds',fd:'FDs'})[k]}`).join(', ');
  if(m.efGap0>0)f.push([`Emergency fund: ${m.r.efCover.toFixed(1)} months covered; ${m.efMonths} recommended (${inrS(m.efTarget)}).`,
    (m.efTop>0?`Move ${fromTxt} into it now. `:'')+(m.efGap>0?`Build the remaining ${inrS(m.efGap)} from your monthly surplus${m.phaseMonths>=36&&m.efReached<m.efMonths?` (about ${m.efReached.toFixed(1)} months' cover in 3 years; goals start then regardless)`:''}. `:'')+`Keep it in ${efWhere}.`]);
  if(m.termGap>0)f.push([`Life cover looks ${s.termCover?'short':'missing'}: about ${inrS(m.termNeed)} suggested, you have ${inrS(s.termCover)}.`,'Rule of thumb: 10 times annual income plus loans, less half your investments, through a plain term plan. Please check with an insurance professional.']);
  if(m.healthGap>0)f.push([`Health cover of ${inrS(s.healthCover)} may be low.`,`${inrS(m.healthNeed)} or more for ${+s.dependants>0||+s.earners>1?'a family':'one person'} is a common starting point; one hospital stay can use up years of savings.`]);
  if(m.r.emiRatio>.4)f.push([`EMIs are ${pc(m.r.emiRatio)} of your income.`,'Above 40% leaves little room for shocks. Avoid new loans; prepay the costliest one when you can.']);
  if(s.topStock>10)f.push([`One share is ${s.topStock}% of your investments.`,'A single company above 10% is a concentration risk; stop adding to it and trim it over time.']);
  if(sh('Real estate')>.5)f.push([`Property is ${pc(sh('Real estate'))} of your investments.`,'It cannot be sold in parts or in a hurry, so the plan never counts on selling it; build liquid investments around it rather than more property.']);
  if(sh('Gold')>.15)f.push([`Gold is ${pc(sh('Gold'))} of your investments.`,'5 to 10% is usually enough to cushion equity falls; beyond that it adds swings without income.']);
  if(m.cur.Cash>m.r.out*12)f.push([`${inrS(m.cur.Cash)} is idle in savings beyond your emergency fund.`,'More than a year of expenses in a savings account loses to inflation; the plan moves it to your goals.']);
  if(s.nfunds>7)f.push([`${s.nfunds} equity funds.`,'Beyond 5 or 6, funds overlap heavily; consolidating makes the portfolio easier to track and rebalance.']);
  return f;
}
function verdict(m,alt){
  const s=m.s, sur=Math.max(0,m.r.surplus), found=m.debtPay+m.efPay, goalNeed=m.need, req=goalNeed+(m.phaseMonths>0?0:0);
  const per=m.G.filter(g=>g.sip>0).map(g=>`${inr(g.sip)} for ${esc(g.name.toLowerCase().startsWith('retire')?'retirement':g.name)}`).join(', ');
  let h='', cls='ok';
  if(sur<=0){h=`<b>There is no monthly surplus to invest.</b> Your expenses and EMIs use all your income; the steps below start with creating one.`;cls='bad'}
  else if(goalNeed<=0){h=`<b>Your existing investments already cover your goals.</b> You don't need to invest anything more for them. Your surplus of ${inr(sur)} a month is yours to spend or to build extra wealth; investing some of it adds margin for weak markets.`}
  else if(goalNeed<=sur){const spare=sur-goalNeed-found;
    h=`<b>Invest ${inr(goalNeed)} a month</b>${found>0?` (plus ${inr(found)} a month for the first ${m.phaseMonths} months, to ${m.debtPay?'clear debt':''}${m.debtPay&&m.efPay?' and ':''}${m.efPay?'build the emergency fund':''})`:''}: ${per}. That is enough for every goal in ${s.confidence==90?'9':s.confidence==50?'1':'3'} out of ${s.confidence==50?'2':s.confidence==90?'10':'4'} markets.`
     +(spare>0?` <b>You may spend up to ${inr(spare)} a month more on your lifestyle today</b>, since your surplus is ${inr(sur)}; investing part of it buys extra margin${m.r.surplus*.15<spare?`. We suggest keeping at least ${inr(Math.min(spare,sur*.15))} of it as a buffer for irregular costs`:''}.`:'')}
  else {const gap=goalNeed-sur;cls='bad';
    h=`<b>Your goals need ${inr(goalNeed)} a month; your surplus is ${inr(sur)}. You are short by ${inr(gap)} a month.</b> ${per}. Essential goals are funded first; the steps below show what to change.`}
  let tbl='';
  if(alt&&alt.length>1)tbl=`<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Retirement spending, today's money (to ${s.lifeExp})</th><th>Corpus at ${s.retireAge}</th><th>Retirement SIP</th><th>All goals together</th><th class="l">With your surplus of ${inr(sur)}</th></tr></thead><tbody>${alt.map(a=>`<tr><td class="l">${inr(a.inc)} a month${a.net<a.inc?` <span class="muted" style="font-size:12px">(${inr(a.net)} from investments)</span>`:''}</td><td class="num">${inrS(a.corpus)}</td><td class="num">${inr(a.sip)}</td><td class="num">${inr(a.need)}</td><td class="l">${a.need<=sur?`Reachable; ${inr(sur-a.need)} a month to spare`:`Short by ${inr(a.need-sur)} a month`}</td></tr>`).join('')}</tbody></table></div>`;
  return `<div class="card pl-verdict ${cls}" style="margin-top:18px"><div class="eyebrow">The answer</div><p style="font-size:16px;margin-top:8px;line-height:1.55">${h}</p>${tbl}</div>`;
}
function retireHtml(m,sim,ages){
  const R=m.retire,s=m.s;if(!R)return '';
  const g=sim.goals.find(x=>x.ret)||{},gg=g.guarded||{},infl=s.infl/100,dfl=Math.pow(1+infl,R.y);
  const A=a=>a==null?'–':isFinite(a)?Math.floor(a):'100+';
  const yearly=R.monthlyThen*12, corp=g.corp50||R.corpus, wr=yearly/corp;
  const b1=yearly*2, b2=yearly*5*Math.pow(1+infl,3.5), b3=Math.max(0,corp-b1-b2);
  const sur=Math.max(0,m.r.surplus);
  const ageRows=(ages||[]).map(a=>`<tr${a.age==s.lifeExp?' style="font-weight:600"':''}><td class="l">Until ${a.age}${a.age==s.lifeExp?' (your plan)':''}</td><td class="num">${inrS(a.corpus)}</td><td class="num">${inr(a.sip)}</td><td class="num">${inr(a.need)}</td><td class="l">${a.need<=sur?`Reachable; ${inr(sur-a.need)} a month to spare`:`Short by ${inr(a.need-sur)} a month`}</td></tr>`).join('');
  const lastRow=(lab,o)=>`<tr><td class="l">${lab}</td>${[85,90,95,100].map(a=>`<td class="num">${o.to?pc(o.to[a]):'–'}</td>`).join('')}<td class="num">${A(o.p10age)}</td></tr>`;
  const annuity=Math.round(1e7*.07/12/1000)*1000;
  return `<h2>Your retirement income plan</h2>
  <div class="grid g2" style="margin-top:12px;align-items:start">
   <div class="card"><div class="kv" style="grid-template-columns:1fr">
    <div><span>Spending you want, today's money</span><b>${inr(R.spendToday)}</b></div>
    ${R.other>0?`<div><span>Less rent / pension that continues</span><b>−${inr(R.other)}</b></div>`:''}
    <div><span><b style="color:var(--ink)">Your investments must pay</b> (today's money)</span><b>${inr(R.monthlyToday)}</b></div>
    <div><span>The same at ${s.retireAge}, after inflation</span><b>${inr(R.monthlyThen)} a month</b></div>
    <div><span>Corpus at ${s.retireAge}, typical markets</span><b>${inrS(g.corp50)}</b></div>
    <div><span>Corpus at ${s.retireAge}, weak markets (1 in 10)</span><b>${inrS(g.corp10)}</b></div>
    <div><span>First-year withdrawal, as a share of the corpus</span><b>${pc(wr,1)}</b></div></div></div>
   <div class="card"><b>Why the money can run out</b><p style="font-size:14.5px;margin-top:8px">You start by taking ${pc(wr,1)} of the corpus in the first year, and that amount rises ${s.infl}% a year with prices: ${inrS(yearly)} in year 1, ${inrS(yearly*Math.pow(1+infl,10))} in year 10, ${inrS(yearly*Math.pow(1+infl,20))} in year 20. A retirement mix (${pc(PM.RMIX(m.E).eq)} equity, the rest mainly debt) has earned about 9% a year since 2007, only about 3% more than inflation. So the corpus shrinks in real terms every year, and a bad market early in retirement, when the corpus is largest, does the most damage. That is why the plan is tested to ${s.lifeExp}, not to an average life expectancy.</p></div></div>

  <h3 style="margin-top:22px">Will it last?</h3>
  <div class="tablewrap" style="margin-top:10px"><table><thead><tr><th class="l">Chance your money lasts until</th><th>85</th><th>90</th><th>95</th><th>100</th><th>Weak markets (1 in 10): lasts until</th></tr></thead><tbody>
   ${lastRow('Spending rises with inflation every year',g)}${lastRow('With the guardrail below',gg)}</tbody></table></div>
  <p class="muted" style="font-size:12.5px;margin-top:6px">From 800 sequences of real market months since 2007, saving until ${s.retireAge} and spending after it.</p>

  <h3 style="margin-top:22px">How long should you plan for?</h3>
  <p style="font-size:14.5px;margin-top:6px;max-width:80ch">Planning to an older age costs more each month now, and is the surest protection against outliving your money.</p>
  <div class="tablewrap" style="margin-top:10px"><table><thead><tr><th class="l">Plan for the money to last</th><th>Corpus needed at ${s.retireAge}</th><th>Retirement SIP</th><th>All goals together</th><th class="l">With your surplus of ${inr(sur)}</th></tr></thead><tbody>${ageRows}</tbody></table></div>

  <h3 style="margin-top:22px">Your SWP: how the money is withdrawn, and how long it lasts</h3>
  <div class="card pl-noprint" id="swpBox" style="margin-top:10px">
   <div class="pl-ctrl" style="grid-template-columns:repeat(4,minmax(0,1fr))">
    <label class="pl-f"><span>Monthly withdrawal</span><div class="seg" role="group" aria-label="Withdrawal type"><button type="button" data-sw="inflation" aria-pressed="true">Rises with prices</button><button type="button" data-sw="fixed" aria-pressed="false">Fixed rupees</button></div></label>
    <label class="pl-f"><span id="swAmtL">Amount, in today's money</span><input type="number" id="swAmt" min="0" step="5000" value="${Math.round(R.monthlyToday)}"><small id="swAmtH"></small></label>
    <label class="pl-f"><span>Show amounts in</span><select id="swView"><option value="real">Today's money</option><option value="nom">Actual rupees</option></select></label>
    <label class="pl-f"><span>Guardrail</span><select id="swGuard"><option value="0">Off</option><option value="1">Skip the increase after a losing year</option></select></label></div>
   <div id="swOut" style="margin-top:14px"></div></div>

  <h3 style="margin-top:22px">At ${s.retireAge}: turning the corpus into a monthly income</h3>
  <div class="grid g3" style="margin-top:10px">
   <div class="card"><div class="eyebrow">Bucket 1 · next 2 years</div><div class="pl-k" style="font-size:22px;margin-top:6px">${inrS(b1)}</div><p style="font-size:14px;margin-top:6px">Liquid and arbitrage funds. A monthly SWP of ${inr(R.monthlyThen)} is paid from here, so a market fall never forces you to sell.</p></div>
   <div class="card"><div class="eyebrow">Bucket 2 · years 3 to 7</div><div class="pl-k" style="font-size:22px;margin-top:6px">${inrS(b2)}</div><p style="font-size:14px;margin-top:6px">Conservative hybrid, short-duration and corporate bond funds. Refills bucket 1 each year.</p></div>
   <div class="card"><div class="eyebrow">Bucket 3 · year 8 onwards</div><div class="pl-k" style="font-size:22px;margin-top:6px">${inrS(b3)}</div><p style="font-size:14px;margin-top:6px">Large cap, flexi cap and balanced advantage funds, plus gold: the growth that keeps pace with prices for the next 20 years and more.</p></div></div>
  <p style="font-size:14.5px;margin-top:12px;max-width:80ch"><b>Each year:</b> top bucket 1 back up to 2 years of spending, from bucket 3 if equity had a good year, from bucket 2 if it fell. Re-split the rest once a year. Amounts are for typical markets; rework them with us at ${s.retireAge - 1}.</p>

  <h3 style="margin-top:22px">Safeguards for a long life</h3>
  <ol class="pl-act" style="margin-top:10px">
   <li><b>The guardrail: after a year in which your portfolio lost money, skip that year's increase.</b><p>${gg.skipped50!=null?`In the simulations this happened about ${gg.skipped50} time${gg.skipped50===1?'':'s'} in a typical retirement and left spending at 85 about ${pc(1-(gg.real85||1))} lower in today's money, while raising the chance of the money lasting to ${s.lifeExp} from ${pc(g.prob)} to ${pc(gg.prob)}.`:''}</p></li>
   <li><b>Plan to ${Math.max(95,+s.lifeExp+5)}, not ${s.lifeExp}, if you can.</b><p>See the table above for the extra monthly amount. Money left at the end is a legacy; money running out at 88 is a crisis.</p></li>
   <li><b>A lifetime annuity for the essentials.</b><p>At ${s.retireAge}, part of the corpus can buy an annuity from an insurer that pays a fixed amount for life, however long you live: roughly ₹${annuity.toLocaleString('en-IN')} a month for every ₹1 crore at about 7% a year today. It does not rise with prices, so it suits the essentials${R.other>0?' alongside your rent':''}, not the whole lifestyle. Rates vary by insurer and age; check current quotes before deciding.</p></li>
   ${R.other>0?`<li><b>Keep the property and its rent.</b><p>The plan counts its ${inr(R.other)} a month (today's money) as income and never assumes you sell it. Raise the rent in line with the market to keep its value rising with prices.</p></li>`:''}
   <li><b>Keep health cover going after you stop working.</b><p>Medical costs are the most common reason retirement money runs out early. Keep a family floater plus a super top-up into your 80s.</p></li></ol>`;
}
let SW={mode:'inflation',amount:null,view:'real',guard:false};
function swpRender(m){
  const box=$('#swOut');if(!box||!m.retire)return;
  const s=m.s, infl=s.infl/100, yrsTo=m.retire.y;
  if(SW.amount==null)SW.amount=Math.round(m.retire.monthlyToday);
  const w=PM.swp(m,MKT,{mode:SW.mode,amount:SW.amount,guard:SW.guard,n:500});if(!w)return;
  const real=SW.view==='real', k=real?'r':'', Y=w.years, W=760,H=300,L=70,Rp=16,T=26,B=34;
  const q90=Math.max(...Y.map(y=>y['p90'+k])), q50=Math.max(...Y.map(y=>y['p50'+k])), capped=q90>2.2*q50, ax=axis((capped?2.2*q50:q90)*1.02||1), maxV=ax.top;
  const x=i=>L+(W-L-Rp)*i/(Y.length-1), y=v=>T+(H-T-B)*(1-Math.min(v,maxV)/maxV);
  const pts=q=>Y.map((r,i)=>`${x(i)},${y(r[q+k])}`);
  const band=pts('p90').concat(pts('p10').reverse()).join(' ');
  const ticks=ax.t.map(v=>`<line x1="${L}" x2="${W-Rp}" y1="${y(v)}" y2="${y(v)}" stroke="var(--rule)"/><text x="${L-8}" y="${y(v)+4}" text-anchor="end">₹${shortR(v)}</text>`).join('');
  const xt=Y.map((r,i)=>r.age%5===0?`<text x="${x(i)}" y="${H-14}" text-anchor="middle">${r.age}</text>`:'').join('')+`<text x="${(L+W)/2}" y="${H-1}" text-anchor="middle">Your age</text>`;
  let er=0;const endMark=(a,lab,col)=>isFinite(a)&&a<100?`<line x1="${x(a-s.retireAge)}" x2="${x(a-s.retireAge)}" y1="${T}" y2="${H-B}" stroke="${col}" stroke-dasharray="4 3"/>${chartLabel(x(a-s.retireAge),lab+' '+Math.floor(a),12+(er++)*13,col,W,L,Rp)}`:'';
  const life=`<line x1="${x(s.lifeExp-s.retireAge)}" x2="${x(s.lifeExp-s.retireAge)}" y1="${T}" y2="${H-B}" stroke="var(--teal)" stroke-width=".8"/>${chartLabel(x(s.lifeExp-s.retireAge),'plan age '+s.lifeExp,H-B-6,'var(--teal)',W,L,Rp)}`;
  const chart=`<div class="pl-fanwrap"><svg class="pl-fan" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Corpus during retirement">${ticks}<polygon points="${band}" fill="var(--c-band)"/><polyline points="${pts('p50').join(' ')}" fill="none" stroke="var(--c-eq)" stroke-width="2.5"/>${life}${endMark(w.ends.p10,'Runs out in weak markets at','var(--c-bad)')}${endMark(w.ends.p50,'Runs out in typical markets at','var(--brass)')}${xt}</svg></div>
   <div class="row" style="gap:18px;font-size:12.5px;color:var(--ink-2)"><span><b style="display:inline-block;width:14px;height:10px;background:var(--c-band);margin-right:6px"></b>Corpus: 8 in 10 outcomes</span><span><b style="display:inline-block;width:14px;height:3px;background:var(--c-eq);vertical-align:middle;margin-right:6px"></b>Typical</span><span class="muted">${real?"In today's money":'In actual rupees'}${capped?'; top of the band cut off to keep the scale readable':''}</span></div>`;
  const A=a=>isFinite(a)?Math.floor(a):'100+';
  const first=w.wd[0], at85=w.wd.find(r=>r.age===85)||w.wd[w.wd.length-1];
  const sum=SW.mode==='fixed'
    ?`<b>${inr(first.monthly)} every month, never increased.</b> At ${s.retireAge} that buys what ${inr(first.real)} buys today; by 85 it buys only what ${inr(at85.real)} buys today. The money ${w.to[100]>.9?'very likely never runs out':w.ends.p10<100?`runs out at about ${A(w.ends.p10)} in weak markets`:'lasts past 100'}, but your lifestyle shrinks with every year of inflation.`
    :`<b>${inr(SW.amount)} a month in today's money: ${inr(first.monthly)} a month at ${s.retireAge}, ${inr(at85.monthly)} at 85</b>, rising ${s.infl}% a year so your lifestyle stays the same. The money lasts until about <b>${A(w.ends.p10)} in weak markets</b> (1 in 10), ${A(w.ends.p25)} in 1 market in 4, and ${A(w.ends.p50)} in typical markets.`;
  const lasts=`<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Chance the money lasts until</th><th>85</th><th>90</th><th>95</th><th>100</th></tr></thead><tbody><tr><td class="l">This SWP</td>${[85,90,95,100].map(a=>`<td class="num">${pc(w.to[a])}</td>`).join('')}</tr></tbody></table></div>`;
  const rows=w.wd.filter(r=>(r.age-s.retireAge)%5===0||r.age===85||r.age===90).filter((r,i,a)=>a.findIndex(z=>z.age===r.age)===i).map(r=>{const yy=Y[r.age-s.retireAge]||{};return `<tr><td class="l">${r.age}</td><td class="num">${inr(r.monthly)}</td><td class="num">${inr(r.real)}</td><td class="num">${inrS(real?yy.p50r:yy.p50)}</td><td class="num">${(real?yy.p10r:yy.p10)>0?inrS(real?yy.p10r:yy.p10):'<span style="color:var(--c-bad)">run out</span>'}</td></tr>`}).join('');
  const tbl=`<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Age</th><th>SWP a month, actual ₹</th><th>Worth in today's money</th><th>Corpus left, typical</th><th>Corpus left, weak markets</th></tr></thead><tbody>${rows}</tbody></table></div>
   <p class="muted" style="font-size:12.5px;margin-top:6px">Corpus columns in ${real?"today's money":'actual rupees'}. The corpus starts from what your plan builds by ${s.retireAge} (typical ${inrS(real?Y[0].p50r:Y[0].p50)}), invested ${pc(PM.RMIX(m.E).eq)} in equity and the rest mainly in debt, through 500 sequences of real market months since 2007. The SWP is paid monthly from bucket 1.</p>`;
  box.innerHTML=`<p style="font-size:14.5px">${sum}</p>${chart}${lasts}${tbl}`;
  $('#swAmtL').textContent=SW.mode==='fixed'?'Amount, actual rupees every month':"Amount, in today's money";
  $('#swAmtH').textContent=SW.mode==='fixed'?`At ${s.retireAge}, worth ${inr(first.real)} today`:`${inr(first.monthly)} a month at ${s.retireAge}`;
}
function bindSwp(m){
  if(!$('#swpBox'))return;
  $$('#swpBox [data-sw]').forEach(b=>b.onclick=()=>{const was=SW.mode;SW.mode=b.dataset.sw;$$('#swpBox [data-sw]').forEach(x=>x.setAttribute('aria-pressed',x===b));
    if(was!==SW.mode){const f=Math.pow(1+m.s.infl/100,m.retire.y);SW.amount=SW.mode==='fixed'?Math.round(m.retire.monthlyToday/5000)*5000:Math.round(m.retire.monthlyToday);$('#swAmt').value=SW.amount}swpRender(m)});
  let t=null;$('#swAmt').oninput=e=>{clearTimeout(t);t=setTimeout(()=>{SW.amount=Math.max(0,+e.target.value||0);swpRender(m)},250)};
  $('#swView').onchange=e=>{SW.view=e.target.value;swpRender(m)};
  $('#swGuard').onchange=e=>{SW.guard=e.target.value==='1';swpRender(m)};
  swpRender(m);
}
function dashHtml(m,sim,m90,alt,ages){
  const s=m.s, flags=flagsOf(m), tot=m.total, tt=m.tgtTotal||1, hasCur=tot>0&&s.investing!=='no';
  const gap=Math.abs(m.r.tol-m.r.cap)>.2?(m.r.tol>m.r.cap?`You are comfortable with more risk than your finances can absorb right now (${m.r.why.slice(0,3).join('; ')}). The plan follows your finances; as these improve, it can take more equity.`
    :'Your finances could carry more risk than you are comfortable with. The plan follows your comfort: a plan you abandon in a fall does more harm than a careful one you keep.'):'Your comfort with risk and your financial capacity are broadly in line.';
  const prob=Object.fromEntries(sim.goals.map(g=>[g.name,g]));
  const goals=m.G.map(g=>{const pr=prob[g.name]||{prob:0};const fundedFull=g.funded>=.999;
    const reach=!fundedFull&&g.y>0&&pr.p50!=null?(g.ret?`With this plan, typical markets get you about ${inrS(pr.p50)}: enough for about ${inr(pr.p50/g.fv*m.retire.monthlyToday)} a month in retirement, in today's money.`:`With this plan, typical markets get you about ${inrS(pr.p50)} of the ${inrS(g.fv)}.`):'';
    return `<div class="card pl-gc"><div class="row" style="justify-content:space-between;align-items:flex-start;gap:8px"><div><h3>${esc(g.name)}</h3><div class="muted" style="font-size:13px">${g.essential?'Essential · ':'Nice to have · '}${g.y?`in ${g.y} year${g.y>1?'s':''}`:'now'} · ${inrS(g.fv)} then${g.ret&&g.how&&g.how!=='your figure'?' ('+esc(g.how)+')':''}</div></div>${g.y>0?`<div class="pl-prob">${gauge(pr.prob)}</div>`:''}</div>
      ${mixBar(g.mix)}<div class="muted" style="font-size:12.5px">${pc(g.mix.eq)} equity · ${pc(g.mix.debt)} debt${g.mix.gold?' · '+pc(g.mix.gold)+' gold':''}${g.y>3?'; moves to safety as the date nears':''}</div>
      <div class="kv" style="grid-template-columns:1fr"><div><span>Set aside from today's money</span><b>${inrS(g.have)}</b></div>${g.sources&&g.sources.length?`<div style="border:0;padding-top:0"><span class="muted" style="font-size:12.5px">${g.sources.map(([k,v])=>inrS(v)+' '+SRCN[k]).join(' · ')}</span></div>`:''}${g.extra>0?`<div><span>Future EPF / NPS</span><b>${inrS(g.extra)}</b></div>`:''}${g.ph>0&&g.f1>0?`<div><span>Months 1–${g.ph}, while foundations are built</span><b>${inr(g.f1)}</b></div>`:''}<div><span>Needs a month${g.ph>0?` from month ${g.ph+1}`:''} (${s.confidence===50?'typical markets':s.confidence===90?'9 in 10 markets':'3 in 4 markets'})</span><b>${g.sip>0?inr(g.sip):'Nothing more'}</b></div>${g.sip>0?`<div><span>In your plan</span><b>${inr(g.f2)}${fundedFull?'':` <span style="color:var(--c-bad)">(${pc(g.funded)})</span>`}</b></div>`:''}</div>
      <p style="font-size:13px;margin:0">${g.y===0?(g.left>0?'Due now and not fully covered.':'Covered.'):`${g.ret?`<b>${pc(pr.prob)}</b> chance your money lasts until ${s.lifeExp}${pr.p10age!=null?`; in weak markets until about ${isFinite(pr.p10age)?Math.floor(pr.p10age):s.lifeExp+'+'}`:''}.`:`<b>${pc(pr.prob)}</b> chance of reaching it with this plan${pr.p10!=null&&fundedFull?`; in weak markets about ${inrS(pr.p10)}`:''}.`}`} ${g.ret?'':reach}</p></div>`}).join('');
  const rows=Object.keys(COL).map(k=>{const c=m.cur[k],t=m.tgt[k],d=t-c;if(!c&&!t)return '';
    const dp=tot?t/tt-c/tot:0;let act=Math.abs(d)<Math.max(5e4,.02*tot)?'On target':d>0?'Increase: through the moves and SIPs in the plan above':'Reduce: the plan above says which holdings move, and where';
    if(k==='Real estate'||k==='Other')act=k==='Real estate'&&+S.retireOther>0?'Kept: its rent counts towards retirement income':'Kept as is';if(k==='Emergency fund')act='From idle savings, step 1 above';if(k==='Arbitrage & liquid')act='Money for goals within 3 years';
    return `<tr><td class="l"><b style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${COL[k]};margin-right:6px"></b>${k}</td><td class="num">${inrS(c)} <span class="muted" style="font-size:12px">${pc(c/tot)}</span></td><td class="num">${inrS(t)} <span class="muted" style="font-size:12px">${pc(t/tt)}</span></td><td class="num">${d>=0?'+':''}${inrS(d)}</td><td class="l" style="font-size:13.5px">${act}</td></tr>`}).join('');
  const locked=s.epf+s.ppf+s.nps;
  const two=m.invest1!=null;
  const catRows=m.cats.map(c=>`<tr><td class="l">${c.url?`<a href="${c.url}">${esc(c.name)}</a>`:esc(c.name)}</td>${two?`<td class="num">${c.v1?inr(c.v1):'–'}</td>`:''}<td class="num">${c.v?inr(c.v):'–'}</td></tr>`).join('');
  const later=m.phaseMonths>0?`For the first ${m.phaseMonths} month${m.phaseMonths>1?'s':''}, ${inr(m.debtPay+m.efPay)} a month goes to ${[m.debtPay?'clearing debt':'',m.efPay?'the emergency fund':''].filter(Boolean).join(' and ')}; your goals get the rest. From month ${m.phaseMonths+1}, everything goes to your goals.`:'';
  const opt=m.option;
  const shortTxt=m.need>m.later.avail+1?`Your goals need ${inr(m.need)} a month; ${inr(m.later.avail)} is available after the buffer. Essential goals are funded first.${opt&&!opt.none?` <b>One way to close the gap:</b> ${opt.retire?`stop working ${opt.years} year${opt.years>1?'s':''} later`:`push "${esc(opt.goal)}" out by ${opt.years} year${opt.years>1?'s':''}`}, which brings its monthly need to ${inr(opt.sip)}.`:opt&&opt.none?` "${esc(opt.goal)}" stays out of reach even 20 years later at this surplus: it needs a smaller target or a bigger surplus.`:''}`:'';
  const review=new Date();review.setFullYear(review.getFullYear()+1);
  const startMix=hasCur?null:m.wealthMix;
  return `<div class="pl-sticky pl-noprint"><div class="pl-ctrl">
    <label class="pl-f"><span>Plan for</span><select id="cConf"><option value="50"${s.confidence==50?' selected':''}>Typical markets (1 in 2)</option><option value="75"${s.confidence==75?' selected':''}>Most markets (3 in 4)</option><option value="90"${s.confidence==90?' selected':''}>Bad markets too (9 in 10)</option></select></label>
    <label class="pl-f"><span>SIPs rise each year: <b id="cSuL">${s.stepup}%</b></span><input type="range" id="cSu" min="0" max="20" step="1" value="${s.stepup}"></label>
    <label class="pl-f"><span>Invest of surplus: <b id="cIsL">${s.investShare}%</b></span><input type="range" id="cIs" min="50" max="100" step="5" value="${s.investShare}"></label>
    ${retired()?'<span></span>':`<label class="pl-f"><span>Stop working at: <b id="cRaL">${s.retireAge}</b></span><input type="range" id="cRa" min="${Math.min(75,Math.max(n('age')+1,40))}" max="75" step="1" value="${s.retireAge}"></label>`}</div></div>
  <div id="plOut">
  ${verdict(m,alt)}
  <h2 style="margin-top:22px">What to do now</h2>
  <p class="muted" style="font-size:13.5px;margin-top:6px">In order. Each step uses the numbers below; change the controls above and the steps update.</p>
  <ol class="pl-act">${actions(m,sim,m90).map(([t,d])=>`<li><b>${t}</b><p>${d}</p></li>`).join('')}</ol>
  <div class="card" style="margin-top:22px"><div class="row" style="justify-content:space-between;gap:20px;align-items:flex-start">
   <div><div class="eyebrow">Your profile</div><div class="pl-k" style="margin-top:6px">${m.label}</div><p class="muted" style="margin-top:4px;font-size:14px">Long-term money: up to ${pc(m.E)} in equity</p></div>
   <div style="flex:1;min-width:240px;max-width:430px"><div style="font-size:13.5px">Risk tolerance: how you feel about falls</div><div class="pl-meter"><i style="left:${(m.r.tol*100).toFixed(0)}%"></i></div>
   <div style="font-size:13.5px;margin-top:10px">Risk capacity: what your finances can absorb</div><div class="pl-meter"><i style="left:${(m.r.cap*100).toFixed(0)}%"></i></div><div class="pl-meter-l"><span>Low</span><span>High</span></div></div></div>
   <p style="margin-top:14px;font-size:14.5px">${esc(gap)}</p></div>

  <h2>Checks</h2>${flags.length?flags.map(([a,b])=>`<div class="pl-flag"><b>${esc(a)}</b> ${esc(b)}</div>`).join(''):'<div class="pl-flag ok"><b>Foundations in place.</b> No expensive debt, an emergency fund on target and insurance that looks adequate.</div>'}

  <h2>${hasCur?'Your money today, and the suggested mix':'Your starting mix'}</h2>
  ${hasCur?`<p class="muted" style="font-size:13.5px;margin-top:6px">${inrS(tot)} invested, excluding your home and emergency fund${locked?`; ${inrS(locked)} of it in EPF, PPF and NPS, which stay where they are`:''}.</p>
  <div class="pl-donuts">${donut(m.cur,'Today',inrS(tot))}${donut(m.tgt,'Suggested',inrS(tt))}</div>
  <div class="tablewrap" style="margin-top:14px"><table><thead><tr><th class="l">Asset class</th><th>Today</th><th>Suggested</th><th>Change</th><th class="l">How</th></tr></thead><tbody>${rows}</tbody></table></div>`
  :`<div class="pl-donuts">${donut({Equity:startMix.eq,Debt:startMix.debt,Gold:startMix.gold},'Long-term','mix')}<div class="card"><p style="font-size:14.5px">Long-term money (10 years or more) in your profile: ${pc(startMix.eq)} equity, ${pc(startMix.debt)} debt and ${pc(startMix.gold)} gold. Money for nearer goals is shown with each goal below.</p></div></div>`}

  <h2>Your goals</h2>
  <p class="muted" style="font-size:13.5px;margin-top:6px">Costs grow at ${s.infl}% inflation. The chance of success comes from replaying real market months since 2007 with your plan.</p>
  <div class="pl-goals">${goals||'<div class="card">No goals yet: everything goes to long-term wealth.</div>'}</div>

  ${retireHtml(m,sim,ages)}

  <h2>Your monthly plan</h2>
  <div class="grid g2" style="margin-top:12px;align-items:start">
   <div class="card"><div class="kv" style="grid-template-columns:1fr"><div><span>Monthly surplus (income − expenses − EMIs)</span><b>${inr(Math.max(0,m.r.surplus))}</b></div><div><span>Kept as a buffer for irregular costs (${100-s.investShare}%)</span><b>${inr(m.buffer)}</b></div><div><span><b style="color:var(--ink)">Invested or set aside</b></span><b>${inr(m.invest)}</b></div></div>
    ${later?`<p style="font-size:14px;margin-top:10px">${later}</p>`:''}${shortTxt?`<p style="font-size:14px;margin-top:10px">${shortTxt}</p>`:`<p style="font-size:14px;margin-top:10px">${m.r.surplus<=0?'Create a surplus first: the plan starts once income exceeds expenses and EMIs.':'Your goals are covered; the rest builds long-term wealth.'}</p>`}</div>
   <div class="tablewrap"><table><thead><tr><th class="l">Where it goes, by fund category</th>${two?`<th>Months 1–${m.phaseMonths}</th><th>From month ${m.phaseMonths+1}</th>`:'<th>A month</th>'}</tr></thead><tbody>${catRows||'<tr><td class="l" colspan="3">Nothing to invest yet.</td></tr>'}<tr><td class="l"><b>Total</b></td>${two?`<td class="num"><b>${inr(m.invest1)}</b></td>`:''}<td class="num"><b>${inr(m.invest)}</b></td></tr></tbody></table></div></div>

  <h2>How your money could grow</h2>
  <p class="muted" style="font-size:13.5px;margin-top:6px;max-width:80ch">All your investments together, with this plan, across 500 sequences of real market months since 2007 (including 2008 and 2020). In today's money, so ₹1 lakh on the chart buys what ₹1 lakh buys now. The line drops when a goal is paid for; after retirement it includes any extra you invest beyond your goals. The SWP simulator above shows the retirement corpus on its own, withdrawal by withdrawal, to age 100.</p>
  <div class="card" style="margin-top:12px">${fan(sim,m)}</div>

  <h2>Roadmap</h2><div class="pl-tl">
   <div><b>Next 3 months</b><ul>${[m.payDebt&&'Pay down the expensive debt first.',m.efGap>0&&`Build the emergency fund towards ${inrS(m.efTarget)}.`,(m.termGap>0||m.healthGap>0)&&'Sort out term and health cover.',m.r.surplus>0&&'Start the SIPs above; schedule them for the day after salary.',m.cur.Cash>m.r.out*12&&'Move idle savings into the goals they belong to.'].filter(Boolean).map(x=>`<li>${x}</li>`).join('')}</ul></div>
   <div><b>3 to 12 months</b><ul><li>Steer new money into what is underweight before selling anything.</li>${s.nfunds>7?'<li>Consolidate overlapping equity funds.</li>':''}<li>Check each SIP is in the category its goal's timeline needs.</li></ul></div>
   <div><b>1 to 3 years</b><ul><li>Raise SIPs by ${s.stepup}% with each raise.</li><li>Rebalance once a year, or when an asset class is 5 points off; use the ₹1.25 lakh yearly tax-free equity gain to do it.</li></ul></div>
   <div><b>Later</b><ul><li>As each goal comes within 3 years, move its money out of equity in stages.</li>${m.retire?`<li>At ${s.retireAge-1}: set up the three retirement buckets and the monthly SWP; consider an annuity for the essentials.</li>`:''}<li>Revisit the plan after marriage, a child, a new job or loan, or an inheritance.</li></ul></div></div>
  <div class="pl-flag ok" style="margin-top:18px"><b>Review by ${review.toLocaleDateString('en-IN',{month:'long',year:'numeric'})},</b> or sooner if your income, family or goals change.</div>

  <div class="inv-cta pl-noprint"><div><h2>Want us to look at it with you?</h2><p>We can review this plan against your actual funds and choose the schemes for each category. The first conversation is free.</p></div>
   <div class="row"><a class="btn" id="plWa" target="_blank" rel="noopener">Send my summary on WhatsApp</a><a class="btn ghost" href="/#contact">Talk to us</a></div></div>
  <div class="pl-nav pl-noprint"><button type="button" class="btn" id="plEdit">Edit my answers</button><div class="row"><button type="button" class="btn" id="plAssB">Assumptions</button><button type="button" class="btn" id="plPrint">Save as PDF</button><button type="button" class="btn" id="plReset">Start over</button></div></div>
  <div id="plAssBox" hidden class="card pl-noprint" style="margin-top:16px"><b>Assumptions</b><p class="muted" style="font-size:13px">Used to size retirement and to split goals; the chances of success come from real market months, not from these.</p><div class="pl-grid">${[['rEq','Equity return % a year'],['rDebt','Debt return % a year'],['rGold','Gold return % a year'],['rCash','Short-term debt return % a year'],['infl','Inflation %']].map(([k,l])=>`<label class="pl-f"><span>${l}</span><input data-a="${k}" type="number" step="0.5" value="${s[k]}"></label>`).join('')}</div><p style="margin-top:12px"><button type="button" class="btn primary" id="plAssGo">Recalculate</button></p></div>
  </div>`;
}
let tmr=null;
function live(){clearTimeout(tmr);const o=$('#plOut');if(o)o.classList.add('pl-busy');tmr=setTimeout(()=>{save();dashboard()},280)}
function bindDash(m){
  const txt=`Hi Aeterna, I used your allocation planner. Profile: ${m.label} (long-term equity up to ${pc(m.E)}). Monthly surplus ${inr(Math.max(0,m.r.surplus))}; goals: ${m.G.map(g=>g.name+' in '+g.y+' yrs').join(', ')}. Investments ${inrS(m.total)}. I'd like to review it with you.`;
  $('#plWa').href='https://wa.me/918595993600?text='+encodeURIComponent(txt);
  $('#plEdit').onclick=()=>{step=0;render()};
  $('#plPrint').onclick=()=>window.print();
  $('#plReset').onclick=()=>{if(confirm('Clear all your answers from this device?')){S=JSON.parse(JSON.stringify(blank));save();step=0;render()}};
  $('#plAssB').onclick=()=>{const b=$('#plAssBox');b.hidden=!b.hidden;if(!b.hidden)b.scrollIntoView({behavior:'smooth'})};
  $('#plAssGo').onclick=()=>{$$('[data-a]').forEach(i=>{const v=parseFloat(i.value);if(isFinite(v))S[i.dataset.a]=v});live()};
  $('#cConf').onchange=e=>{S.confidence=+e.target.value;live()};
  const sl=(id,k,lab,suf)=>{const el=$(id);if(!el)return;el.oninput=()=>{$(lab).textContent=el.value+suf;S[k]=+el.value;live()}};
  sl('#cSu','stepup','#cSuL','%');sl('#cIs','investShare','#cIsL','%');sl('#cRa','retireAge','#cRaL','');
  if(typeof gtag==='function')try{gtag('event','planner_complete',{profile:m.label})}catch(e){}
}
render();
})();
"""


def planner_pages(B, urls):
    desc = ("Free allocation planner for India: your risk profile, a mix of equity, debt and gold for each goal, what to change in your portfolio, "
            "a monthly SIP plan, and the chance of reaching each goal, tested on real market data since 2007.")
    faq = [
        ("What is the right asset allocation for me?", "It depends on when you need each part of your money and how much risk your finances and nerves can take. Money needed within 3 years holds no equity; money for 10 years or more can hold mostly equity if your income, emergency fund and EMIs allow it. The planner works this out goal by goal."),
        ("What is the difference between risk tolerance and risk capacity?", "Tolerance is how comfortable you are with falls; capacity is how much of a fall your finances can absorb without derailing your goals. Someone comfortable with risk but with large EMIs and no emergency fund has low capacity. A sound plan follows the lower of the two."),
        ("Where should I keep my emergency fund?", "Somewhere safe and quick to withdraw: a liquid fund, or for most of it an arbitrage fund if you are in the 20% or 30% tax slab, because arbitrage funds are taxed as equity. Keep a month or two in a liquid fund for instant access."),
        ("Should I count my house in my portfolio?", "Not the home you live in: you will not sell it to fund a goal. Its EMI still matters, because it reduces what you can invest each month. Other property is counted, but as an illiquid holding."),
        ("How often should I rebalance?", "Once a year, or when an asset class drifts 5 percentage points or more from target. Redirecting new SIPs is the cheapest way; switching costs tax and sometimes exit loads."),
    ]
    faq_html = "".join(f"<details class='faq'><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>" for q, a in faq)
    model = (HERE / "planner" / "model.js").read_text(encoding="utf-8")
    market = (HERE / "planner" / "market.json").read_text(encoding="utf-8")
    body = (CSS + HTML.replace("__FAQ__", f'<h2 class="pl-noprint" style="font-size:24px;margin-top:40px">Common questions</h2><div class="pl-noprint">{faq_html}</div>')
            + "<script>window.PLANNER_MARKET=" + market + ";</script><script>" + model + "</script><script>" + UI + "</script>")
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Allocation planner by Aeterna Wealth", "url": B.SITE + PATH,
              "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "publisher": {"@id": B.SITE + "/#org"}, "description": desc}
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    B.write(PATH, B.page("Asset allocation planner: equity, debt and gold for your goals | Aeterna Wealth", desc, PATH, body,
                         (app_ld, faq_ld, B.crumbs([("Calculators", "/calculators/"), ("Allocation planner", PATH)]))))
    urls.append((PATH, "monthly", "0.9"))
