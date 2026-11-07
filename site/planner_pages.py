"""Allocation planner: /plan/ - an interactive, browser-only asset allocation and rebalancing tool.

Design (see the method section on the page itself):
  * Foundations before investing: high-interest debt, emergency fund, term and health cover.
  * Risk tolerance (scenario questions) and risk capacity (cash flow, EMIs, reserves, dependants, horizon)
    are scored separately; equity is capped by the LOWER of the two, and the gap is explained.
  * Goal-based buckets: each goal's mix follows its years to go (glide path), so a 2-year down payment and
    25-year retirement are never given the same allocation. The overall recommendation is the sum.
  * Rebalancing redirects new money first and suggests switching only for large drift (tax and exit loads).
  * Asset classes and fund categories only, never named schemes: indicative and educational, as fits a
    mutual fund distributor. Nothing leaves the browser unless the user chooses to send a summary.
"""

PATH = "/plan/"

CSS = r"""
<style>
:root{--c-eq:#0b4a3c;--c-debt:#7a9a91;--c-gold:#b08a3e;--c-cash:#a7b1ae;--c-re:#6b5a86;--c-alt:#c2795a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--c-eq:#6cc0ae;--c-debt:#5d7a73;--c-gold:#d3a861;--c-cash:#6c7774;--c-re:#9d8cc0;--c-alt:#d99a7f}}
:root[data-theme="dark"]{--c-eq:#6cc0ae;--c-debt:#5d7a73;--c-gold:#d3a861;--c-cash:#6c7774;--c-re:#9d8cc0;--c-alt:#d99a7f}
.pl-wrap{max-width:900px}
.pl-prog{display:flex;gap:6px;margin:20px 0 6px}.pl-prog i{flex:1;height:5px;border-radius:3px;background:var(--rule)}.pl-prog i.on{background:var(--teal)}
.pl-step h2{font-size:26px}.pl-step .sub{color:var(--ink-2);margin-top:6px;max-width:70ch}
.pl-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 20px;margin-top:18px}
@media (max-width:640px){.pl-grid{grid-template-columns:1fr}}
.pl-grid .full{grid-column:1/-1}
.pl-f{display:grid;gap:6px}.pl-f>span{font-size:13.5px;color:var(--ink-2)}
.pl-f input,.pl-f select{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:10px 12px;width:100%;min-width:0;font:inherit;color:inherit}
.pl-f small{color:var(--ink-3);font-size:12.5px;min-height:1em}
.pl-q{margin-top:18px;border:1px solid var(--rule);border-radius:var(--r);padding:16px;background:var(--surface)}
.pl-q legend{font-weight:600;padding:0 4px}.pl-q p{margin:4px 0 10px;color:var(--ink-2);font-size:14px}
.pl-opt{display:flex;gap:10px;align-items:flex-start;padding:9px 10px;border-radius:var(--r);cursor:pointer;font-size:14.5px}
.pl-opt:hover{background:var(--band)}.pl-opt input{margin-top:3px;accent-color:var(--teal)}
.pl-nav{display:flex;justify-content:space-between;gap:12px;margin-top:24px;flex-wrap:wrap}
.pl-goal{display:grid;grid-template-columns:1.4fr 1fr .7fr auto;gap:10px;align-items:end;padding:12px 0;border-bottom:1px dashed var(--rule)}
@media (max-width:640px){.pl-goal{grid-template-columns:1fr 1fr}.pl-goal .gname{grid-column:1/-1}}
.pl-x{border:1px solid var(--rule);background:var(--surface);border-radius:var(--r);padding:9px 12px;cursor:pointer;color:var(--ink-2)}
.pl-err{color:#a4332a;font-size:14px;margin-top:10px}
.pl-bar{display:flex;height:30px;border-radius:var(--r);overflow:hidden;border:1px solid var(--rule)}
.pl-bar span{display:block;height:100%}
.pl-leg{display:flex;flex-wrap:wrap;gap:6px 16px;font-size:13px;margin-top:8px;color:var(--ink-2)}.pl-leg b{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.pl-meter{position:relative;height:10px;border-radius:5px;background:linear-gradient(90deg,var(--c-debt),var(--c-eq));margin:10px 0 4px}
.pl-meter i{position:absolute;top:-5px;width:4px;height:20px;border-radius:2px;background:var(--ink);transform:translateX(-2px)}
.pl-meter-l{display:flex;justify-content:space-between;font-size:12px;color:var(--ink-3)}
.pl-flag{border-left:3px solid var(--brass);padding:10px 14px;background:var(--surface);border-radius:0 var(--r) var(--r) 0;margin-top:10px;font-size:14.5px}
.pl-flag.ok{border-left-color:var(--teal)}
.pl-k{font:600 26px var(--f-display)}
.pl-tl{display:grid;gap:14px;margin-top:12px}.pl-tl>div{border-left:2px solid var(--teal-soft);padding:2px 0 2px 16px}
.pl-tl b{display:block;font:600 16px var(--f-display)}.pl-tl ul{margin:6px 0 0;padding-left:18px;font-size:14.5px}
.pl-dash h2{font-size:24px;margin-top:34px}
.pl-dash .tablewrap td,.pl-dash .tablewrap th{white-space:normal}
@media print{header,footer,.pl-nav,.pl-noprint{display:none!important}.card{break-inside:avoid}}
</style>
"""

HTML = r"""
<section class="band" style="padding-top:28px"><div class="wrap pl-wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/calculators/">Calculators</a> › Allocation planner</nav>
<div class="eyebrow" style="margin-top:16px">Allocation planner</div>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:8px">How should your money be split?</h1>
<p class="lede" style="margin-top:12px">Answer a few questions about your finances, your goals and how you handle market falls. You get an indicative mix of equity, debt and gold for each goal, how it compares with what you hold today, and a month-by-month plan.</p>
<p class="muted" style="font-size:13.5px;margin-top:8px">About 6 minutes. Everything stays in your browser; nothing is sent to us unless you choose to share your summary.</p>
<div class="pl-prog" id="plProg" aria-hidden="true"></div>
<p class="muted mono" style="font-size:12.5px" id="plStepLbl"></p>
<div id="plBody" class="card pl-step" style="margin-top:8px"></div>
<noscript><p class="note">The planner needs JavaScript.</p></noscript>
<details class="faq pl-noprint" style="margin-top:34px"><summary>How the planner works</summary>
<div style="padding:4px 0 8px;max-width:80ch;font-size:14.5px">
<p><b>Foundations first.</b> Expensive debt (personal loans, credit cards) is cleared before investing, an emergency fund of 6 months' expenses and EMIs is built (9 if your income is variable, more with dependants on one income, 12 in retirement), and term and health cover are checked.</p>
<p><b>Two separate risk scores.</b> Your answers to the scenario questions give your risk <i>tolerance</i>. Your finances give your risk <i>capacity</i>: years until you need the money, how much of your income goes on EMIs, your emergency reserve, how steady your income is, and who depends on you. The equity share is set by the lower of the two.</p>
<p><b>One mix per goal.</b> Money needed within 3 years stays out of equity; 3 to 5 years, up to 30% equity; 5 to 7 years, up to 50%; 7 to 10 years, up to 65%; beyond 10 years, up to your profile's limit (30% to 85%). Goals 5 years or more away hold 5 to 8% in gold. As a goal comes within 3 years, its money moves to debt.</p>
<p><b>Your existing investments</b> are assigned to goals nearest-first (EPF, PPF and NPS only to retirement); the monthly amount each goal still needs uses the assumed returns, which you can change. Your own home is left out of the investible portfolio, but its EMI is counted in your cash flow.</p>
<p><b>Rebalancing</b> steers new SIPs into whatever is underweight first, because selling costs tax and exit loads; switching is suggested only when an asset class is more than 10 percentage points off target.</p>
</div></details>
<p class="muted" style="font-size:12.5px;margin-top:18px;max-width:90ch">Indicative and educational only: not investment advice, a recommendation of any scheme, or a guarantee of returns. Assumed returns are illustrations; mutual fund returns can be negative. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889), not a SEBI-registered investment adviser. Insurance and loan points are general checks; please review them with a qualified professional.</p>
</div></section>
"""

JS = r"""
(function(){
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const inr=v=>v==null||!isFinite(v)?'–':'₹'+Math.round(v).toLocaleString('en-IN');
const inrS=v=>{if(v==null||!isFinite(v))return'–';const a=Math.abs(v),sg=v<0?'−':'';return sg+(a>=1e7?'₹'+(a/1e7).toFixed(2)+' cr':a>=1e5?'₹'+(a/1e5).toFixed(1)+' lakh':inr(a))};
const pc=(v,d=0)=>v==null||!isFinite(v)?'–':(v*100).toFixed(d)+'%';
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const KEY='aeterna-plan-v1';
const blank={age:'',retireAge:60,dependants:'0',earners:'1',incomeType:'salaried',income:'',expenses:'',homeEmi:'',otherEmi:'',loanOut:'',hiDebt:'',hiRate:'',
  efund:'',termCover:'',healthCover:'',slab:'30',
  goals:[{name:'Retirement',type:'retire',cost:'',years:''}],
  investing:'yes',eqmf:'',stocks:'',topStock:'',nfunds:'',fd:'',debtmf:'',savings:'',gold:'',epf:'',ppf:'',nps:'',npsEq:'50',realestate:'',alt:'',
  q:{},rEq:11,rDebt:7,rGold:7,rCash:6,infl:6,stepup:10};
let S;try{S=Object.assign({},blank,JSON.parse(localStorage.getItem(KEY)||'{}'))}catch(e){S=Object.assign({},blank)}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(S))}catch(e){}};
const n=k=>{const v=parseFloat(String(S[k]??'').replace(/,/g,''));return isFinite(v)?v:0};
let step=0;

/* ---------- questions ---------- */
const QS=[
 {id:'fall',t:'Markets fall and your portfolio is down 20% in three months.',p:'On ₹10 lakh, that is ₹2 lakh gone on paper. What do you do?',o:['Sell everything; I cannot sleep with losses','Sell part of it to limit the damage','Hold and wait for a recovery','Invest more while prices are low']},
 {id:'range',t:'Which range of outcomes would you pick for ₹10 lakh over 5 years?',p:'Wider ranges have a higher average but a worse bad case.',o:['₹12 to 13.5 lakh: steady, small gains','₹11 to 15.5 lakh','₹10 to 18 lakh','₹8 to 22 lakh: the most upside, can end below what I put in']},
 {id:'aim',t:'What matters more to you for long-term money?',p:'',o:['Not losing what I have','Steady income with a little growth','A balance of growth and stability','The highest growth, accepting big swings']},
 {id:'exp',t:'How much investing experience do you have?',p:'',o:['Savings accounts and FDs only','Mutual funds or SIPs for less than 3 years','Mutual funds or shares through at least one big fall (2020, 2022)','10 years or more, including several crashes']},
 {id:'past',t:'In the last big market fall (for example March 2020), what did you do?',p:'',o:['I was not invested in shares then','I sold some or all','I did nothing','I invested more']},
 {id:'see',t:'You open your app and see your equity holdings down sharply.',p:'',o:['I would stop investing for a while','I would worry and check every day','I would be uneasy but carry on','I would barely notice; it is long-term money'],dyn:true}];

/* ---------- steps ---------- */
const F=(k,label,o={})=>`<label class="pl-f ${o.full?'full':''}"><span>${label}</span>${o.sel?`<select data-k="${k}">${o.sel.map(([v,t])=>`<option value="${v}"${String(S[k])===String(v)?' selected':''}>${t}</option>`).join('')}</select>`
  :`<input data-k="${k}" type="number" inputmode="decimal" min="0" ${o.step?`step="${o.step}"`:''} value="${esc(S[k])}" placeholder="${o.ph||''}">`}<small data-h="${k}">${o.money?esc(hint(S[k])):(o.hint||'')}</small></label>`;
const hint=v=>{const x=parseFloat(v);return isFinite(x)&&x>0?inrS(x):''};
const M=(k,label,o={})=>F(k,label,Object.assign({money:1,ph:'₹'},o));
const STEPS=[
 {t:'About you',s:'Who depends on you and how steady your income is shape how much risk your finances can absorb.',
  h:()=>`<div class="pl-grid">${F('age','Your age',{ph:'e.g. 34'})}${S.incomeType==='retired'?'<span></span>':F('retireAge','Age you plan to stop working',{ph:'60'})}
   ${F('dependants','People who depend on your income',{sel:[['0','None'],['1','1'],['2','2'],['3','3 or more']]})}
   ${F('earners','Earning members in the household',{sel:[['1','Only me'],['2','Two or more']]})}
   ${F('incomeType','Your income',{sel:[['salaried','Salaried, steady'],['variable','Salaried with a large variable part, or commission'],['business','Business or self-employed'],['retired','Retired: pension or investments']],full:1})}
   ${F('slab','Your income-tax slab',{sel:[['0','No tax / up to 5%'],['10','10%'],['20','15–20%'],['30','25–30%']],hint:'Used to compare liquid and arbitrage funds after tax.'})}</div>`},
 {t:'Monthly cash flow',s:'Take-home figures, in rupees a month. Your home loan EMI counts here even though your home is not part of your investments.',
  h:()=>`<div class="pl-grid">${M('income','Take-home income (household)')}${M('expenses','Living expenses, excluding EMIs')}
   ${M('homeEmi','Home loan EMI')}${M('otherEmi','Other EMIs (car, education, personal)')}
   ${M('loanOut','Total loans still outstanding',{hint:'All loans together, to size life cover.'})}${M('hiDebt','Of which: credit card or personal loan balance')}
   ${F('hiRate','Interest rate on that expensive debt (% a year)',{ph:'e.g. 14'})}</div>`},
 {t:'Safety net',s:'Money set aside for emergencies, and your insurance. These come before investing.',
  h:()=>`<div class="pl-grid">${M('efund','Emergency fund (cash, sweep FD or liquid fund kept aside)',{full:1})}
   ${M('termCover','Term life cover (sum assured)')}${M('healthCover','Health insurance cover (family)')}</div>`},
 {t:'Your goals',s:'What the money is for. Cost in today\'s rupees; we add inflation. Leave retirement blank to have it sized from your expenses.',
  h:()=>`<div id="plGoals">${S.goals.map((g,i)=>goalRow(g,i)).join('')}</div>
   <div class="row" style="margin-top:14px"><button type="button" class="btn" id="plAddG">Add a goal</button>
   <select id="plPreset" class="pl-x" aria-label="Goal ideas"><option value="">Goal ideas…</option>${['Child\'s higher education','Child\'s wedding','Home down payment','Car','Foreign holiday','Start a business','Parents\' care'].map(x=>`<option>${x}</option>`).join('')}</select></div>`},
 {t:'What you already hold',s:'Today\'s value of each. Leave out the home you live in. Rough figures are fine.',
  h:()=>`<div class="seg" role="group" aria-label="Investing already?" style="margin-top:14px"><button type="button" data-inv="yes" aria-pressed="${S.investing!=='no'}">I already invest</button><button type="button" data-inv="no" aria-pressed="${S.investing==='no'}">Not yet</button></div>
   ${S.investing==='no'?'<p class="muted" style="margin-top:14px">No problem: the plan will give you a starting mix and how much to invest each month. If you have EPF or PPF, add it here anyway; it counts towards retirement.</p><div class="pl-grid">'+M('epf','EPF / VPF')+M('ppf','PPF and Sukanya Samriddhi')+'</div>':`<div class="pl-grid">${M('eqmf','Equity and hybrid mutual funds')}${M('stocks','Shares held directly')}
   ${F('topStock','Your largest single share, as % of all your investments',{ph:'e.g. 8'})}${F('nfunds','Number of equity funds you hold',{ph:'e.g. 6'})}
   ${M('fd','Fixed deposits, bonds, RBI bonds')}${M('debtmf','Debt and liquid mutual funds')}
   ${M('savings','Savings account balance beyond the emergency fund')}${M('gold','Gold: jewellery for investment, coins, SGBs, gold funds')}
   ${M('epf','EPF / VPF')}${M('ppf','PPF and Sukanya Samriddhi')}${M('nps','NPS')}${F('npsEq','Equity share of your NPS (%)',{ph:'50'})}
   ${M('realestate','Property other than your own home (today\'s value)')}${M('alt','Other: PMS, AIF, unlisted shares, crypto')}</div>`}`},
 {t:'How you handle risk',s:'There are no right answers. Answer for how you would really behave, not how you would like to.',
  h:()=>QS.map(q=>`<fieldset class="pl-q"><legend>${esc(q.dyn?seeText():q.t)}</legend>${q.p?`<p>${esc(q.p)}</p>`:''}${q.o.map((o,i)=>`<label class="pl-opt"><input type="radio" name="q_${q.id}" value="${i+1}"${S.q[q.id]==i+1?' checked':''}><span>${esc(o)}</span></label>`).join('')}</fieldset>`).join('')}];
const seeText=()=>{const eq=n('eqmf')+n('stocks');return eq>0?`You open your app and your equity, now ${inrS(eq)}, shows ${inrS(-eq*0.3)} (down 30%).`:QS[5].t};
const goalRow=(g,i)=>`<div class="pl-goal" data-i="${i}"><label class="pl-f gname"><span>Goal</span><input data-g="name" value="${esc(g.name)}" ${g.type==='retire'?'readonly':''}></label>
  <label class="pl-f"><span>${g.type==='retire'?'Corpus needed (optional)':'Cost in today\'s ₹'}</span><input data-g="cost" type="number" min="0" inputmode="decimal" value="${esc(g.cost)}" placeholder="₹"><small>${esc(hint(g.cost))||(g.type==='retire'?'Blank: sized from your expenses':'')}</small></label>
  <label class="pl-f"><span>In years</span><input data-g="years" type="number" min="0" max="60" value="${esc(g.type==='retire'&&!g.years&&n('age')?Math.max(0,n('retireAge')-n('age')):g.years)}" ${g.type==='retire'?'readonly':''}></label>
  ${g.type==='retire'?'<span></span>':`<button type="button" class="pl-x" data-del="${i}" aria-label="Remove ${esc(g.name)}">Remove</button>`}</div>`;

function render(){
  const total=STEPS.length;
  $('#plProg').innerHTML=Array.from({length:total+1},(_,i)=>`<i class="${i<=step?'on':''}"></i>`).join('');
  if(step>=total){$('#plStepLbl').textContent='Your plan';$('#plBody').className='pl-dash';$('#plBody').innerHTML=dashboard();bindDash();return}
  $('#plBody').className='card pl-step';
  $('#plStepLbl').textContent=`Step ${step+1} of ${total}`;
  const st=STEPS[step];
  $('#plBody').innerHTML=`<h2>${st.t}</h2><p class="sub">${st.s}</p>${st.h()}<div class="pl-err" id="plErr" role="alert"></div>
   <div class="pl-nav">${step?'<button type="button" class="btn" id="plBack">Back</button>':'<span></span>'}<button type="button" class="btn primary" id="plNext">${step===total-1?'See my plan':'Next'}</button></div>`;
  $$('#plBody [data-k]').forEach(el=>el.addEventListener('input',()=>{S[el.dataset.k]=el.value;const h=$(`[data-h="${el.dataset.k}"]`);if(h&&el.type==='number'&&el.placeholder==='₹')h.textContent=hint(el.value);save()}));
  $$('#plBody input[type=radio]').forEach(el=>el.addEventListener('change',()=>{S.q[el.name.slice(2)]=+el.value;save()}));
  if(step===3)bindGoals();
  $$('#plBody [data-inv]').forEach(b=>b.onclick=()=>{S.investing=b.dataset.inv;if(S.investing==='no')['eqmf','stocks','topStock','nfunds','fd','debtmf','savings','gold','nps','realestate','alt'].forEach(k=>S[k]='');save();render()});
  const it=$('#plBody [data-k="incomeType"]');if(it)it.addEventListener('change',()=>render());
  $('#plNext').onclick=()=>{const er=check();if(er){$('#plErr').textContent=er;return}step++;render();window.scrollTo({top:$('#plProg').offsetTop-90,behavior:'smooth'})};
  if(step)$('#plBack').onclick=()=>{step--;render()};
}
function bindGoals(){
  $$('#plGoals [data-g]').forEach(el=>el.addEventListener('input',()=>{const i=+el.closest('.pl-goal').dataset.i;S.goals[i][el.dataset.g]=el.value;save()}));
  $$('#plGoals [data-del]').forEach(b=>b.onclick=()=>{S.goals.splice(+b.dataset.del,1);save();render()});
  $('#plAddG').onclick=()=>{S.goals.push({name:'',cost:'',years:''});save();render()};
  $('#plPreset').onchange=e=>{if(e.target.value){S.goals.push({name:e.target.value,cost:'',years:''});save();render()}};
}
function check(){
  if(step===0&&!(n('age')>=18&&n('age')<=90))return 'Please enter your age.';
  if(step===0&&n('retireAge')<n('age')&&S.incomeType!=='retired')return 'The age you plan to stop working should be later than your age (or choose Retired).';
  if(step===1&&!(n('income')>0))return 'Please enter your monthly take-home income.';
  if(step===1&&!(n('expenses')>0))return 'Please enter your monthly living expenses.';
  if(step===3){for(const g of S.goals){if(g.type!=='retire'&&(!g.name||!(+g.cost>0)||!(+g.years>=0)))return 'Each goal needs a name, a cost and the years until you need it (or remove it).'}}
  if(step===5&&QS.some(q=>!S.q[q.id]))return 'Please answer every question.';
  return '';
}

/* ---------- the model ---------- */
const R=()=>({eq:S.rEq/100,debt:S.rDebt/100,gold:S.rGold/100,cash:S.rCash/100,infl:S.infl/100,step:S.stepup/100});
function goalMix(y,E){   // share of equity / debt / gold for money needed in y years, profile cap E
  let eq=y<3?0:y<5?Math.min(E,.30):y<7?Math.min(E,.50):y<10?Math.min(E,.65):E;
  const gold=y<5?0:y<10?.05:.08;
  return {eq,gold,debt:Math.max(0,1-eq-gold)};
}
const mixRet=(m,y,r)=>m.eq*r.eq+m.gold*r.gold+m.debt*(y<3?r.cash:r.debt);
function sipFor(fv,y,ret,step){   // level-then-step-up monthly SIP whose value after y years is fv
  if(fv<=0)return 0; if(y<=0)return fv;
  const rm=Math.pow(1+ret,1/12)-1; let unit=0;
  for(let yr=0;yr<Math.ceil(y);yr++){const g=Math.pow(1+step,yr), months=Math.min(12,Math.round((y-yr)*12));
    for(let m=0;m<months;m++){const left=y*12-(yr*12+m);unit+=g*Math.pow(1+rm,left)}}
  return fv/unit;
}
function model(){
  const r=R(), age=n('age'), retired=S.incomeType==='retired';
  const emi=n('homeEmi')+n('otherEmi'), out=n('expenses')+emi, inc=n('income'), surplus=inc-out;
  const emiRatio=inc?emi/inc:0, deps=+S.dependants, single=S.earners==='1';
  // foundations
  const efMonths=retired?12:6+(S.incomeType==='variable'||S.incomeType==='business'?3:0)+(deps>0&&single?2:0);
  const efTarget=efMonths*out, efHave=n('efund'), efGap=Math.max(0,efTarget-efHave), efCover=out?efHave/out:0;
  const hiDebt=n('hiDebt'), hiRate=n('hiRate'), payDebt=hiDebt>0&&(hiRate===0||hiRate>=11);
  const termNeed=(deps>0||n('loanOut')>0)&&!retired?10*inc*12+n('loanOut'):0, termGap=Math.max(0,termNeed-n('termCover'));
  const healthNeed=deps>0?1e6:5e5, healthGap=Math.max(0,healthNeed-n('healthCover'));
  // risk: tolerance from answers, capacity from finances
  const qs=QS.map(q=>S.q[q.id]||2), tol=clamp((qs.reduce((a,b)=>a+b,0)-6)/18,0,1);
  const horizon=retired?10:Math.max(0,n('retireAge')-age);
  let cap=1, why=[];
  const hit=(c,x,t)=>{if(c){cap-=x;why.push(t)}};
  hit(horizon<5,.45,'less than 5 years until you stop working'); hit(horizon>=5&&horizon<10,.2,'under 10 years until you stop working');
  hit(efCover<3,.25,`an emergency reserve of ${efCover.toFixed(1)} months`); hit(efCover>=3&&efCover<efMonths,.08,'an emergency reserve below target');
  hit(emiRatio>.5,.3,`EMIs taking ${pc(emiRatio)} of income`); hit(emiRatio>.35&&emiRatio<=.5,.15,`EMIs taking ${pc(emiRatio)} of income`);
  hit(S.incomeType==='variable'||S.incomeType==='business',.1,'an income that varies'); hit(retired,.25,'living off your savings');
  hit(deps>=2&&single,.12,`${deps>=3?'three or more':'two'} dependants on one income`); hit(surplus<=0,.3,'no monthly surplus');
  hit(age>=55&&!retired,.1,'being 55 or older'); hit(payDebt,.1,'expensive debt outstanding');
  cap=clamp(cap,0,1);
  const prof=Math.min(tol,cap), E=.30+.55*prof;
  const label=prof<.25?'Cautious':prof<.5?'Balanced':prof<.75?'Growth':'High growth';
  // holdings
  const npsEq=clamp(n('npsEq'),0,75)/100;
  const cur={Equity:n('eqmf')+n('stocks')+n('nps')*npsEq, Debt:n('fd')+n('debtmf')+n('epf')+n('ppf')+n('nps')*(1-npsEq), Gold:n('gold'), Cash:n('savings'), 'Real estate':n('realestate'), Other:n('alt')};
  const liquidPool=n('eqmf')+n('stocks')+n('fd')+n('debtmf')+n('savings')+n('gold')+n('alt'), retPool=n('epf')+n('ppf')+n('nps');
  const totalCur=Object.values(cur).reduce((a,b)=>a+b,0);
  // goals: future cost, existing money assigned nearest-first, SIP needed
  let pool=liquidPool, rp=retPool;
  const G=S.goals.map(g=>{const ret=g.type==='retire';const y=ret?(retired?0:Math.max(0,n('retireAge')-age)):+g.years||0;
      let fv=ret&&!(+g.cost>0)?n('expenses')*12*Math.pow(1+r.infl,y)*28:(+g.cost||0)*Math.pow(1+r.infl,y);
      if(ret&&retired)fv=0;
      return {name:g.name||'Goal',ret,y,fv,mix:goalMix(y,E)}}).sort((a,b)=>a.y-b.y);
  for(const g of G){g.r=mixRet(g.mix,g.y,r);
    const use=(src)=>{const need=g.fv/Math.pow(1+g.r,g.y);return Math.min(src,need-(g.have||0)>0?need-(g.have||0):0)};
    if(g.ret){const a=use(rp);g.have=(g.have||0)+a;rp-=a}
    const b=use(pool);g.have=(g.have||0)+b;pool-=b;
    g.left=Math.max(0,g.fv-g.have*Math.pow(1+g.r,g.y)); g.sip=sipFor(g.left,g.y,g.r,r.step)}
  const wealthMix=goalMix(15,E);
  // target allocation for today's investible money (own home excluded; property and 'other' kept as they are)
  const tgt={Equity:0,Debt:0,Gold:0,Cash:0,'Real estate':cur['Real estate'],Other:cur.Other};
  const add=(amt,m,y)=>{tgt.Equity+=amt*m.eq;tgt.Gold+=amt*m.gold;if(y<1)tgt.Cash+=amt*m.debt;else tgt.Debt+=amt*m.debt};
  G.forEach(g=>add(g.have,g.mix,g.y)); add(pool+rp-n('alt'),wealthMix,15);
  // monthly plan
  let left=Math.max(0,surplus); const plan=[];
  if(payDebt){const x=Math.min(left*.6,hiDebt);plan.push(['Pay down expensive debt',x,'Every rupee repaid earns the loan\'s interest rate, risk-free.']);left-=x}
  if(efGap>0){const x=Math.min(left*.5,efGap/6);plan.push(['Build the emergency fund',x,`Liquid${+S.slab>=20?' or arbitrage':''} fund or sweep FD, until it reaches ${inrS(efTarget)}.`]);left-=x}
  const need=G.reduce((a,g)=>a+g.sip,0);
  const scale=need>left&&need>0?left/need:1;
  G.forEach(g=>{if(g.sip>0)plan.push([g.name,g.sip*scale,`${g.y<3?'No equity: money needed within 3 years':`${pc(g.mix.eq)} equity, ${pc(g.mix.debt)} debt${g.mix.gold?`, ${pc(g.mix.gold)} gold`:''}`}`,g])});
  left-=need*scale;
  if(left>500)plan.push(['Long-term wealth',left,`${pc(wealthMix.eq)} equity, ${pc(wealthMix.debt)} debt, ${pc(wealthMix.gold)} gold`,{mix:wealthMix,y:15}]);
  return {r,age,inc,out,emi,surplus,emiRatio,efMonths,efTarget,efHave,efGap,efCover,hiDebt,hiRate,payDebt,termNeed,termGap,healthNeed,healthGap,tol,cap,why,prof,E,label,cur,tgt,totalCur,G,plan,need,scale,wealthMix};
}

/* ---------- categories for each sleeve ---------- */
function equitySplit(E){ // core / flexi / mid-small by profile
  return E<.5?[['Index funds or large cap',.7,'/mutual-funds/index-fund/'],['Flexi cap',.3,'/mutual-funds/flexi-cap/']]
    :E<.7?[['Index funds or large cap',.5,'/mutual-funds/index-fund/'],['Flexi or multi cap',.35,'/mutual-funds/flexi-cap/'],['Mid and small cap',.15,'/mutual-funds/mid-cap/']]
    :[['Index funds or large cap',.4,'/mutual-funds/index-fund/'],['Flexi or multi cap',.35,'/mutual-funds/flexi-cap/'],['Mid and small cap',.25,'/mutual-funds/small-cap/']];
}
const debtCat=y=>y<1?['Liquid or money market funds'+(+S.slab>=20?' (arbitrage if held over a year: taxed as equity)':''),'/mutual-funds/arbitrage/']
  :y<3?[+S.slab>=20?'Arbitrage funds (taxed as equity)':'Money market or short duration funds','/mutual-funds/arbitrage/']
  :['Short duration, corporate bond or banking & PSU funds; PPF','/mutual-funds/'];

/* ---------- dashboard ---------- */
const COL={Equity:'var(--c-eq)',Debt:'var(--c-debt)',Gold:'var(--c-gold)',Cash:'var(--c-cash)','Real estate':'var(--c-re)',Other:'var(--c-alt)'};
function bar(o){const t=Object.values(o).reduce((a,b)=>a+b,0)||1;
  return `<div class="pl-bar" role="img" aria-label="${Object.entries(o).filter(([,v])=>v>0).map(([k,v])=>k+' '+pc(v/t)).join(', ')}">${Object.entries(o).filter(([,v])=>v>0).map(([k,v])=>`<span style="width:${(v/t*100).toFixed(2)}%;background:${COL[k]}" title="${k} ${pc(v/t)}"></span>`).join('')}</div>`}
const legend=()=>`<div class="pl-leg">${Object.keys(COL).map(k=>`<span><b style="background:${COL[k]}"></b>${k}</span>`).join('')}</div>`;
function dashboard(){
  const m=model(), r=m.r;
  const flags=[];
  if(m.surplus<=0)flags.push(['Your EMIs and expenses use all of your income.','Before investing, the first step is creating a monthly surplus: review expenses, or refinance or prepay the costliest loan.']);
  if(m.payDebt)flags.push([`${inrS(m.hiDebt)} of expensive debt${m.hiRate?' at '+m.hiRate+'%':''}.`,'Clearing it beats any investment return. The plan puts most of your surplus here first.']);
  if(m.efGap>0)flags.push([`Emergency fund: ${m.efCover.toFixed(1)} months covered; ${m.efMonths} recommended.`,`Build up ${inrS(m.efGap)} more in a liquid fund, sweep FD or savings account before taking equity risk.`]);
  if(m.termGap>0)flags.push([`Life cover looks ${n('termCover')?'short':'missing'}: about ${inrS(m.termNeed)} suggested, you have ${inrS(n('termCover'))}.`,'A rule of thumb: 10 times annual income plus outstanding loans, through a plain term plan. Please check with an insurance professional.']);
  if(m.healthGap>0)flags.push([`Health cover of ${inrS(n('healthCover'))} may be low.`,`At least ${inrS(m.healthNeed)} for ${+S.dependants>0?'a family':'one person'} is a common starting point; one hospital stay can use up years of savings.`]);
  if(m.emiRatio>.4)flags.push([`EMIs are ${pc(m.emiRatio)} of your income.`,'Above 40% leaves little room for shocks. Avoid new loans and consider prepaying the costliest one.']);
  const tot=m.totalCur, sh=k=>tot?m.cur[k]/tot:0;
  if(n('topStock')>10)flags.push([`One share is ${n('topStock')}% of your investments.`,'A single company above 10% is a concentration risk; trim over time or stop adding to it.']);
  if(sh('Real estate')>.5)flags.push([`Property is ${pc(sh('Real estate'))} of your investments.`,'It is hard to sell in parts or in a hurry; build liquid investments around it rather than more property.']);
  if(sh('Gold')>.15)flags.push([`Gold is ${pc(sh('Gold'))} of your investments.`,'5 to 10% is usually enough to cushion equity falls; beyond that it mostly adds volatility without income.']);
  if(m.cur.Cash>m.out*12)flags.push([`${inrS(m.cur.Cash)} is sitting in savings beyond your emergency fund.`,'More than a year of expenses idle in a savings account loses to inflation; the plan moves it to your goals.']);
  if(n('nfunds')>7)flags.push([`${n('nfunds')} equity funds.`,'Beyond 5 or 6, funds usually overlap heavily and you pay for active management of an index-like mix. Consolidating makes tracking easier.']);
  if(sh('Debt')>.6&&m.E>.5&&tot>0&&S.investing!=='no')flags.push(['Most of your money is in fixed income.',`For your goals and profile, about ${pc(m.tgt.Equity/Math.max(1,Object.values(m.tgt).reduce((a,b)=>a+b,0)))} in equity is indicated. Move gradually through SIPs, not all at once.`]);
  // rebalancing table
  const tgtTot=Object.values(m.tgt).reduce((a,b)=>a+b,0)||1, rows=Object.keys(COL).map(k=>{const c=m.cur[k],t=m.tgt[k],d=t-c,dp=tot?(t/tgtTot-c/tot):0;
    let act=Math.abs(d)<Math.max(5e4,.02*tot)?'On target':d>0?'Increase: direct new SIPs here first':(Math.abs(dp)>.10&&k!=='Real estate'&&k!=='Other'?'Reduce: stop new money, then switch the excess gradually (mind tax and exit loads)':'Reduce: stop adding new money; let other assets catch up');
    if((k==='Real estate'||k==='Other')&&c>0)act='Kept as is: not part of the rebalancing';
    return c||t?`<tr><td class="l"><b style="display:inline-block;width:10px;height:10px;border-radius:2px;background:${COL[k]};margin-right:6px"></b>${k}</td><td class="num">${inrS(c)}<br><span class="muted" style="font-size:12px">${tot?pc(c/tot):''}</span></td><td class="num">${inrS(t)}<br><span class="muted" style="font-size:12px">${pc(t/tgtTot)}</span></td><td class="num">${d>0?'+':''}${inrS(d)}</td><td class="l" style="font-size:13.5px">${act}</td></tr>`:''}).join('');
  // monthly split by category
  const cat={}; const addc=(nm,url,v)=>{if(v<1)return;cat[nm]=cat[nm]||{v:0,url};cat[nm].v+=v};
  m.plan.forEach(([nm,v,,g])=>{if(!g){addc(nm==='Build the emergency fund'?'Emergency fund: liquid fund or sweep FD':'Pay down expensive debt',nm==='Build the emergency fund'?'/mutual-funds/arbitrage/':'',v);return}
    equitySplit(m.E).forEach(([c,w,u])=>addc(c,u,v*g.mix.eq*w)); const [dc,du]=debtCat(g.y); addc(dc,du,v*g.mix.debt); addc('Gold funds or gold ETFs','',v*g.mix.gold)});
  const catRows=Object.entries(cat).sort((a,b)=>b[1].v-a[1].v).map(([k,o])=>`<tr><td class="l">${o.url?`<a href="${o.url}">${esc(k)}</a>`:esc(k)}</td><td class="num">${inr(o.v)}</td></tr>`).join('');
  const invest=m.plan.reduce((a,p)=>a+p[1],0);
  const gap=Math.abs(m.tol-m.cap)>.25?(m.tol>m.cap?`You are comfortable with more risk than your finances can absorb right now (${m.why.slice(0,3).join(', ')}). The plan follows your finances; as these improve, it can take more equity.`
    :'Your finances could carry more risk than you are comfortable with. The plan follows your comfort, because a plan you abandon in a fall does more harm than a cautious one you keep. Experience of a full market cycle usually raises comfort.'):'Your comfort with risk and your financial capacity are broadly in line.';
  const goalRows=m.G.map(g=>`<tr><td class="l">${esc(g.name)}</td><td class="num">${g.y.toFixed(0)} yrs</td><td class="num">${inrS(g.fv)}</td><td class="num">${inrS(g.have)}</td><td class="num">${pc(g.mix.eq)} / ${pc(g.mix.debt)} / ${pc(g.mix.gold)}</td><td class="num">${inr(g.sip)}</td></tr>`).join('');
  const review=new Date();review.setFullYear(review.getFullYear()+1);
  const firstSteps=m.plan.filter(p=>!p[3]).reduce((a,p)=>a+p[1],0), forGoals=Math.max(0,m.surplus-firstSteps), short=m.need>forGoals+1;
  const months=firstSteps>0?Math.ceil(((m.payDebt?m.hiDebt:0)+m.efGap)/Math.max(1,firstSteps)):0;
  return `<div class="card"><div class="row" style="justify-content:space-between;gap:20px;align-items:flex-start">
   <div><div class="eyebrow">Your profile</div><div class="pl-k" style="margin-top:6px">${m.label}</div><p class="muted" style="margin-top:4px;font-size:14px">Long-term money: up to ${pc(m.E)} in equity</p></div>
   <div style="flex:1;min-width:240px;max-width:420px"><div style="font-size:13.5px">Risk tolerance (your answers)</div><div class="pl-meter"><i style="left:${(m.tol*100).toFixed(0)}%"></i></div>
   <div style="font-size:13.5px;margin-top:10px">Risk capacity (your finances)</div><div class="pl-meter"><i style="left:${(m.cap*100).toFixed(0)}%"></i></div><div class="pl-meter-l"><span>Low</span><span>High</span></div></div></div>
   <p style="margin-top:14px;font-size:14.5px">${esc(gap)}</p></div>

  <h2>Before you invest</h2>${flags.length?flags.map(([a,b])=>`<div class="pl-flag"><b>${esc(a)}</b> ${esc(b)}</div>`).join(''):'<div class="pl-flag ok"><b>Foundations look in place.</b> No expensive debt, an emergency fund on target and insurance that looks adequate.</div>'}

  <h2>Current and suggested allocation</h2>
  ${tot>0?`<p class="muted" style="font-size:13.5px;margin-top:6px">Today: ${inrS(tot)}, excluding your home and emergency fund</p>${bar(m.cur)}`:'<p class="muted" style="margin-top:6px">You have not started investing yet: the suggested starting mix is below.</p>'}
  <p class="muted" style="font-size:13.5px;margin-top:14px">Suggested for the same money</p>${bar(tot>0?m.tgt:{Equity:m.wealthMix.eq,Debt:m.wealthMix.debt,Gold:m.wealthMix.gold})}${legend()}
  ${tot>0?`<div class="tablewrap" style="margin-top:16px"><table><thead><tr><th class="l">Asset class</th><th>Today</th><th>Suggested</th><th>Change</th><th class="l">How</th></tr></thead><tbody>${rows}</tbody></table></div>`:''}

  <h2>Your goals</h2>
  <div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Goal</th><th>When</th><th>Cost then</th><th>Covered by today's money</th><th>Equity / debt / gold</th><th>Monthly needed</th></tr></thead><tbody>${goalRows}</tbody></table></div>
  <p class="muted" style="font-size:12.5px;margin-top:8px">Costs grow at ${S.infl}% inflation. Monthly amounts rise ${S.stepup}% a year with your income. ${m.G.some(g=>g.ret&&!(+S.goals.find(x=>x.type==='retire')?.cost>0))?'Retirement corpus sized at 28 times a year\'s expenses at retirement. ':''}Assumed returns: equity ${S.rEq}%, debt ${S.rDebt}%, gold ${S.rGold}%, short-term debt ${S.rCash}% a year (<a href="#" id="plAss">change</a>).</p>

  <h2>Your monthly plan</h2>
  <div class="grid g2" style="margin-top:12px;align-items:start">
   <div class="card"><div class="muted" style="font-size:13.5px">Monthly surplus</div><div class="pl-k">${inr(Math.max(0,m.surplus))}</div>
    <div class="muted" style="font-size:13.5px;margin-top:10px">Suggested to invest or set aside</div><div class="pl-k">${inr(invest)}</div>
    <p style="font-size:14px;margin-top:10px">${m.surplus<=0?'Create a surplus first: the plan starts once income exceeds expenses and EMIs.'
      :short&&firstSteps>0&&m.need<=m.surplus?`For about ${months} month${months>1?'s':''}, ${inr(firstSteps)} a month goes to ${m.payDebt?'clearing debt':''}${m.payDebt&&m.efGap>0?' and ':''}${m.efGap>0?'the emergency fund':''}, leaving ${inr(forGoals)} for goals that need ${inr(m.need)}. After that, your full surplus covers them.`
      :short?`Your goals need ${inr(m.need)} a month; after the steps above, ${inr(forGoals)} is available (${pc(m.scale)}). Options: push a goal out by a few years, trim its cost, or raise the yearly step-up.`
      :'Your surplus covers what your goals need; the rest goes to long-term wealth.'}</p></div>
   <div class="tablewrap"><table><thead><tr><th class="l">Where it goes, by fund category</th><th>Per month</th></tr></thead><tbody>${catRows||'<tr><td class="l" colspan="2">Nothing to invest yet.</td></tr>'}</tbody></table></div></div>

  <h2>Roadmap</h2><div class="pl-tl">
   <div><b>Next 3 months</b><ul>${[m.payDebt&&'Pay down the expensive debt first.',m.efGap>0&&`Build the emergency fund towards ${inrS(m.efTarget)}.`,(m.termGap>0||m.healthGap>0)&&'Sort out term and health cover.',m.surplus>0&&'Start the goal SIPs above; automate them for the day after salary.',m.cur.Cash>m.out*12&&'Move idle savings into the goals they belong to.'].filter(Boolean).map(x=>`<li>${x}</li>`).join('')}</ul></div>
   <div><b>3 to 12 months</b><ul><li>Steer new money into whatever is underweight before selling anything.</li>${n('nfunds')>7?'<li>Consolidate overlapping equity funds.</li>':''}<li>Check that SIPs are in the right category for each goal's timeline.</li></ul></div>
   <div><b>1 to 3 years</b><ul><li>Raise SIPs by ${S.stepup}% with each raise.</li><li>Rebalance when any asset class is 5 points or more off target; use the yearly ₹1.25 lakh tax-free equity gain to do it tax-efficiently.</li></ul></div>
   <div><b>Beyond</b><ul><li>As each goal comes within 3 years, move its money out of equity in stages.</li><li>Revisit the plan after marriage, a child, a new job or loan, or an inheritance.</li></ul></div></div>
  <div class="pl-flag ok" style="margin-top:18px"><b>Review by ${review.toLocaleDateString('en-IN',{month:'long',year:'numeric'})},</b> or sooner if your income, family or goals change.</div>

  <h2>What-if simulator</h2>
  <p class="muted" style="margin-top:6px;font-size:14px;max-width:75ch">Move the sliders to see the range of outcomes, not just one number. Each run simulates 1,000 possible market paths using the assumed returns and typical swings (equity about 17% a year, gold 14%, debt 3%).</p>
  <div class="card pl-noprint" id="plSim" style="margin-top:12px"><div class="pl-grid">
   <label class="pl-f"><span>Invest per month: <b id="sAmtL"></b></span><input type="range" id="sAmt" min="1000" max="${Math.max(50000,Math.round(Math.max(invest,m.surplus)*2/1000)*1000)}" step="500" value="${Math.max(1000,Math.round(invest/500)*500)}"></label>
   <label class="pl-f"><span>Equity share: <b id="sEqL"></b></span><input type="range" id="sEq" min="0" max="90" step="5" value="${Math.round(m.E*20)*5}"></label>
   <label class="pl-f"><span>Years: <b id="sYrL"></b></span><input type="range" id="sYr" min="1" max="35" step="1" value="${Math.min(35,Math.max(1,Math.round(Math.max(...m.G.map(g=>g.y),10))))}"></label>
   <label class="pl-f"><span>Yearly step-up: <b id="sSuL"></b></span><input type="range" id="sSu" min="0" max="20" step="1" value="${S.stepup}"></label>
   <label class="pl-f full"><span>Starting amount already invested</span><input type="number" id="sStart" min="0" value="${Math.round(Math.max(0,m.totalCur-m.cur['Real estate']-m.cur.Other))}"></label>
   <label class="pl-f full"><span>Target to test (optional)</span><select id="sGoal"><option value="">None</option>${m.G.filter(g=>g.fv>0).map(g=>`<option value="${Math.round(g.fv)}" data-y="${Math.max(1,Math.round(g.y))}">${esc(g.name)}: ${inrS(g.fv)} in ${g.y.toFixed(0)} yrs</option>`).join('')}</select></label></div>
   <div class="out" style="margin-top:16px" id="sOut"></div><p id="sTxt" style="font-size:14px;margin-top:10px"></p></div>

  <div class="inv-cta pl-noprint"><div><h2>Want us to look at it with you?</h2><p>We can review this plan against your actual funds and pick the schemes for each category. The first conversation is free.</p></div>
   <div class="row"><a class="btn" id="plWa" target="_blank" rel="noopener">Send my summary on WhatsApp</a><a class="btn ghost" href="/#contact">Talk to us</a></div></div>
  <div class="pl-nav pl-noprint"><button type="button" class="btn" id="plEdit">Edit my answers</button><div class="row"><button type="button" class="btn" id="plPrint">Save as PDF</button><button type="button" class="btn" id="plReset">Start over</button></div></div>
  <div id="plAssBox" hidden class="card pl-noprint" style="margin-top:16px"><b>Assumptions</b><div class="pl-grid">${[['rEq','Equity return % a year'],['rDebt','Debt return % a year'],['rGold','Gold return % a year'],['rCash','Short-term debt return % a year'],['infl','Inflation %'],['stepup','Yearly SIP step-up %']].map(([k,l])=>`<label class="pl-f"><span>${l}</span><input data-a="${k}" type="number" step="0.5" value="${S[k]}"></label>`).join('')}</div><p style="margin-top:12px"><button type="button" class="btn primary" id="plAssGo">Recalculate</button></p></div>`;
}
function bindDash(){
  const m=model();
  const txt=`Hi Aeterna, I used your allocation planner. Profile: ${m.label} (long-term equity up to ${pc(m.E)}). Monthly surplus ${inr(Math.max(0,m.surplus))}; goals: ${m.G.map(g=>g.name+' in '+g.y.toFixed(0)+' yrs').join(', ')}. Current investments ${inrS(m.totalCur)}. I'd like to review it with you.`;
  $('#plWa').href='https://wa.me/918595993600?text='+encodeURIComponent(txt);
  $('#plEdit').onclick=()=>{step=0;render()};
  $('#plPrint').onclick=()=>window.print();
  $('#plReset').onclick=()=>{if(confirm('Clear all your answers from this device?')){S=JSON.parse(JSON.stringify(blank));save();step=0;render()}};
  $('#plAss').onclick=e=>{e.preventDefault();const b=$('#plAssBox');b.hidden=false;b.scrollIntoView({behavior:'smooth'})};
  $('#plAssGo').onclick=()=>{$$('[data-a]').forEach(i=>{const v=parseFloat(i.value);if(isFinite(v))S[i.dataset.a]=v});save();render()};
  sim();['sAmt','sEq','sYr','sSu','sStart'].forEach(id=>$('#'+id).addEventListener('input',sim));
  $('#sGoal').addEventListener('change',e=>{const o=e.target.selectedOptions[0];if(o&&o.dataset.y){$('#sYr').value=o.dataset.y}sim()});
  if(typeof gtag==='function')try{gtag('event','planner_complete',{profile:m.label})}catch(e){}
}
function sim(){
  const amt=+$('#sAmt').value, eq=+$('#sEq').value/100, yrs=+$('#sYr').value, su=+$('#sSu').value/100, start=+$('#sStart').value||0, tgt=+$('#sGoal').value||0;
  $('#sAmtL').textContent=inr(amt);$('#sEqL').textContent=pc(eq);$('#sYrL').textContent=yrs+(yrs>1?' years':' year');$('#sSuL').textContent=pc(su);
  const gold=yrs>=5?Math.min(.08,1-eq):0, debt=Math.max(0,1-eq-gold), r=R();
  const mu=eq*r.eq+gold*r.gold+debt*r.debt, vol=Math.sqrt(Math.max(0,(eq*.17)**2+(gold*.14)**2+(debt*.03)**2-2*eq*gold*.17*.14*.1));
  // monthly lognormal steps, seeded so the same inputs always give the same answer
  let seed=12345;const rnd=()=>{seed=(seed*1103515245+12345)%2147483648;return seed/2147483648};
  const gauss=()=>{let u=0;while(!u)u=rnd();const v=rnd();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v)};
  const mm=Math.log(1+mu)/12-vol*vol/24, sm=vol/Math.sqrt(12), N=1000, res=[];let paid=start;
  for(let p=0;p<N;p++){let v=start;for(let t=0;t<yrs*12;t++){v=v*Math.exp(mm+sm*gauss())+amt*Math.pow(1+su,Math.floor(t/12))}res.push(v)}
  for(let t=0;t<yrs*12;t++)paid+=amt*Math.pow(1+su,Math.floor(t/12));
  res.sort((a,b)=>a-b);const q=x=>res[Math.floor(x*(N-1))];
  const hit=tgt?res.filter(v=>v>=tgt).length/N:null;
  const dfl=Math.pow(1+r.infl,yrs);
  $('#sOut').innerHTML=[['Weak markets (1 in 10)',q(.1)],['Typical',q(.5)],['Strong markets (1 in 10)',q(.9)]].map(([a,b])=>`<div class="card" style="padding:14px"><div class="muted" style="font-size:12.5px">${a}</div><div class="pl-k" style="font-size:22px">${inrS(b)}</div><div class="muted" style="font-size:12.5px">${inrS(b/dfl)} in today's money</div></div>`).join('');
  $('#sTxt').innerHTML=`You would put in ${inrS(paid)} in all. "Today's money" removes ${S.infl}% inflation a year. ${hit!=null?`<b>Chance of reaching ${inrS(tgt)}: ${pc(hit)}.</b> `:''}${eq>.6&&yrs<5?'With under 5 years to go, a high equity share makes the weak case much worse; consider less equity for money needed soon. ':''}${hit!=null&&hit<.6?'To raise the odds: invest a little more, add a year or two, or raise the step-up. ':''}Illustration only: real returns will differ and can be negative.`;
}
render();
})();
"""


def planner_pages(B, urls):
    desc = ("Free asset allocation planner for India: your risk tolerance and capacity, a mix of equity, debt and gold for each goal, "
            "your current vs suggested portfolio, and a monthly SIP plan. Runs in your browser.")
    faq = [
        ("What is the right asset allocation for me?", "It depends on when you need each part of your money and how much risk your finances and nerves can take. Money needed within 3 years should not be in equity; money for 10 years or more can hold mostly equity if your income, emergency fund and EMIs allow it. The planner works this out goal by goal."),
        ("What is the difference between risk tolerance and risk capacity?", "Tolerance is how comfortable you are with falls; capacity is how much of a fall your finances can absorb without derailing your goals. Someone comfortable with risk but with large EMIs and no emergency fund has low capacity. A sound plan follows the lower of the two."),
        ("Should I count my house in my portfolio?", "Not the home you live in: you will not sell it to fund a goal. Its EMI still matters, because it reduces what you can invest each month. Other property is counted, but as an illiquid holding."),
        ("How often should I rebalance?", "Once a year, or when an asset class drifts 5 percentage points or more from target. Redirecting new SIPs is the cheapest way; switching costs tax and sometimes exit loads."),
    ]
    faq_html = "".join(f"<details class='faq'><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>" for q, a in faq)
    body = (CSS + HTML.replace('<details class="faq pl-noprint" style="margin-top:34px">',
                               f'<h2 class="pl-noprint" style="font-size:24px;margin-top:40px">Common questions</h2><div class="pl-noprint">{faq_html}</div>'
                               '<details class="faq pl-noprint" style="margin-top:14px">', 1)
            + "<script>" + JS + "</script>")
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Allocation planner by Aeterna Wealth", "url": B.SITE + PATH,
              "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "publisher": {"@id": B.SITE + "/#org"}, "description": desc}
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    B.write(PATH, B.page("Asset allocation planner: equity, debt and gold for your goals | Aeterna Wealth", desc, PATH, body,
                         (app_ld, faq_ld, B.crumbs([("Calculators", "/calculators/"), ("Allocation planner", PATH)]))))
    urls.append((PATH, "monthly", "0.9"))
