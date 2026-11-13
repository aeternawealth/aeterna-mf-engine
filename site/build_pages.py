"""Extra static pages for search: calculators, fund houses, index and theme groups, fund-vs-fund comparisons,
insight articles and the legal pages. Called from build_site.main(); uses its helpers (passed in as B)."""
import json
import re
from itertools import combinations

ACR = {"SBI", "ICICI", "HDFC", "UTI", "DSP", "LIC", "HSBC", "PGIM", "ITI", "JM", "IDBI", "BNP", "ELSS", "ESG", "PSU", "MNC",
       "IT", "US", "ETF", "FOF", "BSE", "NSE", "TRI", "AMC", "BOI", "IDFC", "PSE", "CPSE", "BFSI", "REIT", "REITS", "II", "III",
       "NFO", "GDP", "TATA", "ONE", "AI"}


NICE_WORD = {"TRUSTMF": "TrustMF", "BANDHAN": "Bandhan", "NAVI": "Navi", "QUANT": "Quant", "SAMCO": "Samco", "GROWW": "Groww"}


def nice(name):
    """'SBI CONTRA FUND' -> 'SBI Contra Fund'; 'BANDHAN Small Cap Fund' -> 'Bandhan Small Cap Fund' (shouting words in
    mixed-case names are fixed too; real acronyms stay)."""
    if not name:
        return name
    if not name.isupper():
        return " ".join(NICE_WORD.get(w, w.capitalize() if (w.isalpha() and w.isupper() and len(w) >= 5 and w not in ACR) else w)
                        for w in name.split(" "))
    out = []
    for w in name.split():
        core = re.sub(r"[^A-Z]", "", w)
        if core in ACR and core not in ("TATA", "ONE"):
            out.append(w)
        elif w.upper() == "NIFTY":
            out.append("Nifty")
        elif w in NICE_WORD:
            out.append(NICE_WORD[w])
        else:
            out.append(w.capitalize() if w.isalpha() else w.title())
    return " ".join(out)


# ------------------------------------------------------------------ calculators
def fld(i, label, v, lo, hi, step):
    return (f'<label class="field"><span>{label}</span><span class="in"><input type="range" id="{i}R" min="{lo}" max="{hi}" step="{step}" '
            f'value="{v}" aria-label="{label}"><input type="number" id="{i}" min="{lo}" max="{hi}" step="{step}" value="{v}" aria-label="{label}"></span></label>')


def sel(i, label, opts, cur):
    return (f'<label class="field"><span>{label}</span><select id="{i}">'
            + "".join(f'<option value="{k}"{" selected" if k == cur else ""}>{t}</option>' for k, t in opts) + "</select></label>")


def mr(r):
    return (1 + r / 100) ** (1 / 12) - 1


def py_sip(m, yrs, r, step=0):
    rm, bal, inv, amt, rows = mr(r), 0.0, 0.0, m, []
    for mo in range(1, yrs * 12 + 1):
        bal = (bal + amt) * (1 + rm)
        inv += amt
        if mo % 12 == 0:
            rows.append((mo // 12, inv, bal))
            amt *= 1 + step / 100
    return rows


def py_emi(P, rate, yrs):
    i, n = rate / 1200, yrs * 12
    return P * i * (1 + i) ** n / ((1 + i) ** n - 1)


def lakh(x):
    return f"₹{x / 1e7:.2f} crore" if abs(x) >= 1e7 else f"₹{x / 1e5:.2f} lakh" if abs(x) >= 1e5 else f"₹{x:,.0f}"


JS_RT = r"""
const $=s=>document.querySelector(s);
const inr=v=>v==null||!isFinite(v)?'–':'₹'+Math.round(v).toLocaleString('en-IN');
const inrS=v=>{if(v==null||!isFinite(v))return'–';const a=Math.abs(v);return a>=1e7?'₹'+(v/1e7).toFixed(2)+' cr':a>=1e5?'₹'+(v/1e5).toFixed(2)+' lakh':inr(v)};
const val=id=>+($('#'+id)?.value||0);
let cFirst=true;
function chart(c){const el=$('#cChart');if(!el)return;if(!c){el.hidden=true;return}el.hidden=false;
 if(c.split){const tot=c.split.reduce((a,x)=>a+Math.max(0,x[1]),0)||1;el.innerHTML=`<div class="cc-split">${c.split.map(([n,v,col])=>`<i style="width:${(Math.max(0,v)/tot*100).toFixed(2)}%;background:${col}"></i>`).join('')}</div><div class="cc-key">${c.split.map(([n,v,col])=>`<span><i style="background:${col}"></i>${n} <b>${inrS(v)}</b></span>`).join('')}</div>`;return}
 const W=640,H=250,L=6,R=6,T=14,B=26,n=c.labels.length,mx=Math.max(1,...c.series.flatMap(s=>s.v)),x=i=>L+(n>1?i/(n-1):.5)*(W-L-R),y=v=>T+(H-T-B)*(1-Math.max(0,v)/mx);
 const line=s=>s.v.map((v,i)=>(i?'L':'M')+x(i).toFixed(1)+' '+y(v).toFixed(1)).join(' ');
 const ticks=[0,Math.floor((n-1)/2),n-1].filter((v,i,a)=>a.indexOf(v)===i);
 el.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${c.title||'Chart'}">${[.25,.5,.75,1].map(f=>`<line x1="${L}" x2="${W-R}" y1="${y(mx*f)}" y2="${y(mx*f)}" stroke="var(--rule)" stroke-width="1"/>`).join('')}
 <path d="${line(c.series[0])} L${x(n-1)} ${H-B} L${x(0)} ${H-B} Z" fill="var(--teal)" opacity=".13"/>
 ${c.series.map(s=>`<path class="cc-line${cFirst?' draw':''}" pathLength="1" d="${line(s)}" fill="none" stroke="${s.c}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"${s.dash?' stroke-dasharray="5 5"':''}/>`).join('')}
 ${ticks.map(i=>`<text x="${x(i)}" y="${H-7}" text-anchor="${i===0?'start':i===n-1?'end':'middle'}" font-size="12" fill="var(--ink-3)" font-family="IBM Plex Mono,monospace">${c.labels[i]}</text>`).join('')}
 <line id="ccG" y1="${T}" y2="${H-B}" stroke="var(--ink-3)" stroke-width="1" visibility="hidden"/>${c.series.map((s,k)=>`<circle id="ccD${k}" r="4.5" fill="${s.c}" stroke="var(--surface)" stroke-width="1.5" visibility="hidden"/>`).join('')}
 <rect id="ccH" x="0" y="0" width="${W}" height="${H}" fill="transparent"/></svg><div class="cc-key" id="ccK"></div>`;
 const key=i=>{$('#ccK').innerHTML=`<span class="cc-at">${c.labels[i]}</span>`+c.series.map(s=>`<span><i style="background:${s.c}"></i>${s.n} <b>${inrS(s.v[i])}</b></span>`).join('')};key(n-1);
 const h=$('#ccH'),mv=e=>{const r=h.getBoundingClientRect(),i=Math.max(0,Math.min(n-1,Math.round(((e.clientX-r.left)/r.width*W-L)/(W-L-R)*(n-1))));key(i);const g=$('#ccG');g.setAttribute('x1',x(i));g.setAttribute('x2',x(i));g.setAttribute('visibility','visible');
  c.series.forEach((s,k)=>{const d=$('#ccD'+k);d.setAttribute('cx',x(i));d.setAttribute('cy',y(s.v[i]));d.setAttribute('visibility','visible')})};
 h.addEventListener('pointermove',mv);h.addEventListener('pointerdown',mv);h.addEventListener('pointerleave',()=>{key(n-1);$('#ccG').setAttribute('visibility','hidden');c.series.forEach((s,k)=>$('#ccD'+k).setAttribute('visibility','hidden'))});cFirst=false}
function out(pairs,text,head,rows,ch){chart(ch);$('#cOut').innerHTML=pairs.map(([k,v])=>`<div><span>${k}</span><b>${v}</b></div>`).join('');
 $('#cTbl').hidden=!head;$('#cTxt').textContent=text||'';$('#cTbl').innerHTML=head?`<table><thead><tr>${head.map((h,i)=>`<th${i?'':' class="l"'}>${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map((c,i)=>`<td class="${i?'num':'l'}">${c}</td>`).join('')}</tr>`).join('')}</tbody></table>`:''}
document.querySelectorAll('#calc input,#calc select').forEach(el=>{el.addEventListener('input',()=>{const id=el.id.replace(/R$/,''),p=el.id.endsWith('R')?$('#'+id):$('#'+id+'R');if(p&&p!==el)p.value=el.value;run()})});
"""

CALCS = [
    {"id": "sip", "name": "SIP calculator", "h1": "SIP calculator",
     "title": "SIP calculator: monthly SIP returns, with step-up | Aeterna Wealth",
     "desc": "Free SIP calculator for India: see what a monthly SIP grows to, with an optional yearly step-up, using monthly compounding at the equivalent of your yearly return. Includes a year-by-year table.",
     "intro": "Enter a monthly amount, a number of years and a return you want to assume. The calculator shows what the SIP could grow to and how much of that is your own money.",
     "inputs": lambda: fld("a", "Monthly SIP (₹)", 10000, 500, 500000, 500) + fld("y", "Years", 15, 1, 40, 1) + fld("r", "Assumed return a year (%)", 12, 1, 20, 0.5) + fld("s", "Step-up every year (%)", 0, 0, 25, 1),
     "js": "function run(){const r=CALC.sip(val('a'),Math.max(1,Math.round(val('y'))),val('r'),val('s'));out([['Money put in',inrS(r.inv)],['Estimated value',inrS(r.bal)],['Estimated gain',inrS(r.bal-r.inv)]],`A SIP of ${inr(val('a'))} a month for ${Math.round(val('y'))} years at ${val('r')}% a year could grow to about ${inrS(r.bal)}, of which ${inrS(r.inv)} is money you put in.`,['Year','Put in','Value'],r.rows.map(x=>[x.y,inrS(x.inv),inrS(x.val)]),{title:'SIP value by year',labels:r.rows.map(x=>'Year '+x.y),series:[{n:'Value',c:'var(--teal)',v:r.rows.map(x=>x.val)},{n:'Put in',c:'var(--brass)',v:r.rows.map(x=>x.inv),dash:1}]})}",
     "how": "Each instalment is invested at the start of the month and grows every month at the monthly equivalent of the yearly return: (1 + r)<sup>1/12</sup> − 1, so 12% a year is 0.949% a month, not 1%. For a fixed SIP this gives FV = P × [((1 + i)<sup>n</sup> − 1) / i] × (1 + i), where P is the monthly amount, i the monthly rate and n the number of months. A step-up raises the instalment once a year.",
     "example": lambda: (lambda rows: "<p>₹10,000 a month at an assumed 12% a year:</p><div class='tablewrap'><table><thead><tr><th class='l'>After</th><th>Put in</th><th>Value</th></tr></thead><tbody>"
                         + "".join(f"<tr><td class='l'>{y} years</td><td class='num'>{lakh(i)}</td><td class='num'>{lakh(v)}</td></tr>" for y, i, v in rows if y in (5, 10, 15, 20, 25)) + "</tbody></table></div>")(py_sip(10000, 25, 12)),
     "faq": [("How is SIP return calculated?", "With monthly compounding: each instalment grows every month at the monthly equivalent of the yearly return, (1 + r)^(1/12) − 1. A fixed SIP's value is P × [((1 + i)^n − 1) / i] × (1 + i)."),
             ("What return should I assume for an equity SIP?", "No return is guaranteed. As a reference from real data, a ₹10,000 monthly SIP over the last 10 years in the middle-ranked flexi cap fund grew at about 13% a year; large cap funds about 11%. Past returns may not repeat; a lower assumption is the safer plan."),
             ("What is a step-up SIP?", "A SIP whose instalment rises once a year, for example by 10%, usually in line with income. It shortens the time needed to reach a goal."),
             ("Is a SIP better than a lump sum?", "A lump sum invested at once grows for longer, so it often ends higher in rising markets. A SIP spreads the buying over time, which lowers the risk of investing everything at a market high and suits monthly income.")],
     "app": "sip"},
    {"id": "lumpsum", "name": "Lump sum calculator", "h1": "Lump sum calculator",
     "title": "Lump sum calculator: one-time investment returns | Aeterna Wealth",
     "desc": "Free lump sum calculator for India: what a one-time mutual fund investment could grow to at the yearly return you assume, with a year-by-year table.",
     "intro": "Enter the amount, the number of years and a return to assume.",
     "inputs": lambda: fld("a", "Amount (₹)", 100000, 1000, 100000000, 1000) + fld("y", "Years", 10, 1, 40, 1) + fld("r", "Assumed return a year (%)", 12, 1, 20, 0.5),
     "js": "function run(){const a=val('a'),y=Math.max(1,Math.round(val('y'))),r=val('r'),v=CALC.lump(a,y,r);out([['Invested',inrS(a)],['Estimated value',inrS(v)],['Estimated gain',inrS(v-a)]],`${inr(a)} invested today at ${r}% a year could grow to about ${inrS(v)} in ${y} years.`,['Year','Value'],[...Array(y)].map((_,i)=>[i+1,inrS(CALC.lump(a,i+1,r))]),{title:'Value by year',labels:[...Array(y+1)].map((_,i)=>i?'Year '+i:'Today'),series:[{n:'Value',c:'var(--teal)',v:[...Array(y+1)].map((_,i)=>i?CALC.lump(a,i,r):a)},{n:'Invested',c:'var(--brass)',v:[...Array(y+1)].map(()=>a),dash:1}]})}",
     "how": "Value = amount × (1 + r)<sup>years</sup>, where r is the yearly return (CAGR). That is the same as compounding every month at the monthly equivalent rate.",
     "example": lambda: f"<p>₹1 lakh at 12% a year grows to {lakh(1e5 * 1.12 ** 10)} in 10 years and {lakh(1e5 * 1.12 ** 20)} in 20 years.</p>",
     "faq": [("How is a lump sum return calculated?", "Future value = amount × (1 + yearly return)^years. At 12% a year, money roughly doubles in about 6 years."),
             ("What is CAGR?", "Compound annual growth rate: the steady yearly return that turns the starting amount into the ending amount over the period."),
             ("Lump sum or SIP?", "If the money is already there, a lump sum has longer to grow; a SIP, or a staggered transfer from a liquid fund, reduces the risk of investing everything at a market high.")],
     "app": "lump"},
    {"id": "goal", "name": "Goal planner", "h1": "Goal planner: SIP needed for a goal",
     "title": "Goal SIP calculator: monthly SIP needed for education, home or retirement | Aeterna Wealth",
     "desc": "Free goal calculator for India: the monthly SIP or lump sum you need for a goal such as a child's education, a home or retirement, after inflation and what you have already saved.",
     "intro": "Enter what the goal costs in today's money, when you need it, expected inflation and the return you assume.",
     "inputs": lambda: fld("t", "Goal cost today (₹)", 2500000, 100000, 500000000, 100000) + fld("y", "Years to the goal", 12, 1, 40, 1) + fld("i", "Inflation a year (%)", 7, 0, 15, 0.5) + fld("r", "Assumed return a year (%)", 11, 1, 20, 0.5) + fld("h", "Already saved for it (₹)", 0, 0, 100000000, 10000),
     "js": "function run(){const y=Math.max(1,Math.round(val('y'))),G=CALC.goal(val('t'),y,val('i'),val('r'),val('h'));out([['Goal cost then',inrS(G.fv)],['Monthly SIP needed',inr(G.sip)],['Or a lump sum today',inrS(G.lump)]],`At ${val('i')}% inflation, ${inrS(val('t'))} today will cost about ${inrS(G.fv)} in ${y} years. ${G.need>0?`After what you have saved, a SIP of about ${inr(G.sip)} a month at ${val('r')}% would cover it.`:'What you have already saved should cover it at that return.'}`,['Year','Goal cost by then','Your savings'],(()=>{const sp=G.sip>0?CALC.sip(G.sip,y,val('r'),0).rows:[];window._g=[...Array(y)].map((_,k)=>({y:k+1,cost:val('t')*Math.pow(1+val('i')/100,k+1),sav:CALC.lump(val('h'),k+1,val('r'))+(sp[k]?sp[k].val:0)}));return _g.map(x=>[x.y,inrS(x.cost),inrS(x.sav)])})(),{title:'Goal cost and your savings by year',labels:_g.map(x=>'Year '+x.y),series:[{n:'Your savings',c:'var(--teal)',v:_g.map(x=>x.sav)},{n:'Goal cost',c:'var(--brass)',v:_g.map(x=>x.cost),dash:1}]})}",
     "how": "The goal's cost grows by inflation every year. Money already saved grows at the assumed return. The monthly SIP is the amount that, invested at the start of each month at the monthly equivalent of the yearly return, fills the gap exactly.",
     "example": lambda: "<p>A ₹25 lakh education cost 12 years away at 7% inflation will cost about " + lakh(2.5e6 * 1.07 ** 12) + ". At an assumed 11% a year, that needs a monthly SIP of about ₹" + f"{(2.5e6 * 1.07 ** 12) / (((1 + mr(11)) ** 144 - 1) / mr(11) * (1 + mr(11))):,.0f}" + ".</p>",
     "faq": [("How much SIP do I need for my child's education?", "Grow today's cost by education inflation (often 8–10% a year) to the year it is needed, subtract what your savings will grow to, and divide the gap by the SIP growth factor. The calculator does this for you."),
             ("What inflation should I use?", "India's consumer inflation has averaged roughly 5–7% a year over the last two decades; education and healthcare have often risen faster."),
             ("Can I use this for retirement?", "Yes, for the corpus you need on the day you retire. To see how long a corpus lasts once you start withdrawing, use the SWP calculator.")],
     "app": "goal"},
    {"id": "swp", "name": "SWP calculator", "h1": "SWP calculator: how long will my money last?",
     "title": "SWP calculator: monthly withdrawal and retirement income | Aeterna Wealth",
     "desc": "Free SWP calculator for India: how long a corpus lasts with a monthly withdrawal that rises every year with inflation, and what is left at the end.",
     "intro": "Enter your corpus, the monthly amount you want to withdraw, the return you assume and how much the withdrawal should rise each year.",
     "inputs": lambda: fld("c", "Starting corpus (₹)", 10000000, 100000, 500000000, 100000) + fld("w", "Monthly withdrawal (₹)", 60000, 1000, 5000000, 1000) + fld("r", "Assumed return a year (%)", 8, 0, 15, 0.5) + fld("i", "Raise the withdrawal every year by (%)", 6, 0, 12, 0.5) + fld("y", "Years to show", 30, 5, 50, 1),
     "js": "function run(){const y=Math.max(1,Math.round(val('y'))),r=CALC.swp(val('c'),val('w'),val('r'),val('i'),y),l=r.lastedMonths;out([['Money lasts',l==null?`${y}+ years`:`${Math.floor(l/12)} yrs ${l%12} mo`],['Total withdrawn',inrS(r.withdrawn)],['Left at the end',inrS(r.bal)]],l==null?`The corpus supports the withdrawal for all ${y} years, with ${inrS(r.bal)} left.`:`At these numbers the money runs out after ${Math.floor(l/12)} years and ${l%12} months.`,['Year','Withdrawn so far','Corpus left'],r.rows.map(x=>[x.y,inrS(x.inv),inrS(x.val)]),{title:'Corpus left by year',labels:r.rows.map(x=>'Year '+x.y),series:[{n:'Corpus left',c:'var(--teal)',v:r.rows.map(x=>x.val)},{n:'Withdrawn so far',c:'var(--brass)',v:r.rows.map(x=>x.inv),dash:1}]})}",
     "how": "Each withdrawal comes out at the start of the month; what remains grows every month at the monthly equivalent of the yearly return. The withdrawal rises once a year by the rate you choose, to keep up with inflation.",
     "example": lambda: "<p>A ₹1 crore corpus, ₹60,000 a month rising 6% a year, at an assumed 8% a year: see the result above (the calculator opens with these numbers).</p>",
     "faq": [("What is a safe withdrawal rate in India?", "There is no single safe rate. With Indian inflation of 5–7%, withdrawing more than about 4–5% of the corpus in the first year, rising with inflation, risks running out within 25–30 years unless returns are high."),
             ("How is SWP taxed?", "Each withdrawal is treated as a sale of units; only the gain portion is taxed, as short- or long-term capital gain depending on how long those units were held."),
             ("SWP or dividend (IDCW) option?", "An SWP gives you a fixed, planned amount and is taxed only on gains; IDCW payouts are irregular and fully taxed at your slab rate.")],
     "app": "swp"},
    {"id": "emi", "name": "EMI calculator", "h1": "Loan EMI calculator",
     "title": "EMI calculator: home, car and personal loan EMI and interest | Aeterna Wealth",
     "desc": "Free EMI calculator for India: monthly EMI, total interest and a year-by-year payoff table for home, car and personal loans, using the reducing-balance method banks use.",
     "intro": "Enter the loan amount, the interest rate and the tenure.",
     "inputs": lambda: fld("p", "Loan amount (₹)", 5000000, 100000, 200000000, 100000) + fld("r", "Interest rate a year (%)", 8.5, 1, 24, 0.05) + fld("y", "Tenure (years)", 20, 1, 30, 1),
     "js": "function run(){const r=CALC.emi(val('p'),val('r'),val('y'));out([['Monthly EMI',inr(r.emi)],['Total interest',inrS(r.interest)],['Total paid',inrS(r.total)]],`On ${inrS(val('p'))} at ${val('r')}% for ${val('y')} years, the EMI is ${inr(r.emi)} and total interest ${inrS(r.interest)}.`,['Year','Interest','Principal','Balance'],r.rows.map(x=>[x.y,inr(x.interest),inr(x.principal),inr(x.balance)]),{title:'Loan balance by year',labels:r.rows.map(x=>'Year '+x.y),series:[{n:'Loan left',c:'var(--teal)',v:r.rows.map(x=>x.balance)},{n:'Interest that year',c:'var(--brass)',v:r.rows.map(x=>x.interest),dash:1}]})}",
     "how": "EMI = P × i × (1 + i)<sup>n</sup> / ((1 + i)<sup>n</sup> − 1), where P is the loan, i the yearly rate ÷ 12 and n the number of months. Interest is charged every month on the balance still outstanding (reducing balance).",
     "example": lambda: f"<p>A ₹50 lakh home loan at 8.5% for 20 years has an EMI of ₹{py_emi(5e6, 8.5, 20):,.0f}; total interest is {lakh(py_emi(5e6, 8.5, 20) * 240 - 5e6)}.</p>",
     "faq": [("How is EMI calculated?", "EMI = P × i × (1 + i)^n / ((1 + i)^n − 1), with i = yearly rate ÷ 12 and n = months. A ₹10 lakh loan at 10% for 20 years has an EMI of ₹9,650."),
             ("Should I prepay my home loan or invest?", "Compare the loan rate after tax benefits with the return you can reasonably expect after tax. Prepaying gives a certain saving equal to the loan rate; investing may earn more but is not guaranteed."),
             ("Does a longer tenure reduce total interest?", "No. A longer tenure lowers the EMI but raises total interest, because the balance is paid down more slowly.")],
     "app": "emi"},
    {"id": "inflation", "name": "Inflation calculator", "h1": "Inflation calculator",
     "title": "Inflation calculator India: future cost and today's value of money | Aeterna Wealth",
     "desc": "Free inflation calculator for India: what something will cost in future at the inflation rate you choose, and what a future sum is worth in today's money.",
     "intro": "Enter an amount, a number of years and an inflation rate.",
     "inputs": lambda: fld("a", "Amount (₹)", 100000, 1000, 100000000, 1000) + fld("y", "Years", 10, 1, 50, 1) + fld("i", "Inflation a year (%)", 6, 0, 15, 0.5),
     "js": "function run(){const y=Math.max(1,Math.round(val('y'))),r=CALC.infl(val('a'),y,val('i'));out([['What it will cost then',inrS(r.future)],['That sum in today\\'s money',inrS(r.today)]],`Something that costs ${inrS(val('a'))} today would cost about ${inrS(r.future)} in ${y} years at ${val('i')}% inflation.`,['Year','Cost by then'],[...Array(y)].map((_,k)=>[k+1,inrS(val('a')*Math.pow(1+val('i')/100,k+1))]),{title:'Cost by year',labels:[...Array(y+1)].map((_,k)=>k?'Year '+k:'Today'),series:[{n:'Cost',c:'var(--teal)',v:[...Array(y+1)].map((_,k)=>val('a')*Math.pow(1+val('i')/100,k))},{n:'Cost today',c:'var(--brass)',v:[...Array(y+1)].map(()=>val('a')),dash:1}]})}",
     "how": "Future cost = amount × (1 + inflation)<sup>years</sup>. Today's value of a future sum = amount ÷ (1 + inflation)<sup>years</sup>.",
     "example": lambda: f"<p>At 6% inflation, ₹1 lakh of spending today costs {lakh(1e5 * 1.06 ** 10)} in 10 years and {lakh(1e5 * 1.06 ** 20)} in 20 years.</p>",
     "faq": [("What is India's average inflation?", "Consumer price inflation in India has averaged roughly 5–7% a year over the last two decades, with education and healthcare often higher."),
             ("Why does inflation matter for investing?", "Money that earns less than inflation loses buying power. A fixed deposit at 7% with 6% inflation, before tax, grows your buying power by only about 1% a year.")],
     "app": "infl"},
    {"id": "capital-gains-tax", "name": "Capital gains tax calculator", "h1": "Capital gains tax calculator: mutual funds, bonds, unlisted shares",
     "title": "Capital gains tax calculator: LTCG and STCG on mutual funds (2025-26 rules) | Aeterna Wealth",
     "desc": "Free capital gains tax calculator for India: LTCG and STCG on equity and debt mutual funds, listed bonds and unlisted shares under the rules from 23 July 2024 (12.5% LTCG, 20% STCG, ₹1.25 lakh exemption).",
     "intro": "Choose what you are selling, how long you have held it and the gain.",
     "inputs": lambda: sel("as", "What are you selling?", [("eq", "Equity mutual funds (65%+ equity)"), ("debt", "Debt mutual funds (bought from 1 Apr 2023)"), ("lbond", "Listed bonds and debentures"), ("unl", "Unlisted shares")], "eq")
     + fld("m", "Months held", 18, 1, 120, 1) + fld("g", "Gain (₹)", 300000, 0, 50000000, 10000) + sel("sl", "Your income-tax slab", [("0", "0%"), ("5", "5%"), ("10", "10%"), ("15", "15%"), ("20", "20%"), ("30", "30%")], "30"),
     "js": "function run(){const T=CALC.tax({asset:$('#as').value,months:val('m'),gain:val('g'),slab:+$('#sl').value});out([['Type',T.lt?'Long term':'Short term'],['Taxable gain',inrS(T.taxable)],['Tax (with 4% cess)',inr(T.tax)]],`Taxed at ${T.rate}%${T.lt&&$('#as').value==='eq'?' on gains above ₹1.25 lakh a year':''}, plus 4% cess. Surcharge is not included.`,null,null,{split:[['You keep',val('g')-T.tax,'var(--teal)'],['Tax',T.tax,'var(--brass)']]})}",
     "how": "Equity mutual funds: long term if held more than 12 months, taxed at 12.5% on gains above ₹1.25 lakh a year; short term at 20%. Debt funds bought from 1 April 2023: your slab rate, however long you hold. Listed bonds: long term after 12 months at 12.5%. Unlisted shares: long term after 24 months at 12.5%. Short-term gains on bonds and unlisted shares are taxed at your slab. A 4% cess applies; surcharge is ignored.",
     "example": lambda: f"<p>An equity fund held 18 months with a ₹3 lakh gain: (₹3,00,000 − ₹1,25,000) × 12.5% × 1.04 = ₹{175000 * 0.125 * 1.04:,.0f}.</p>",
     "faq": [("What is the LTCG tax on equity mutual funds?", "12.5% on long-term gains (units held more than 12 months) above ₹1.25 lakh in a financial year, plus cess, for sales from 23 July 2024."),
             ("What is the STCG tax on equity mutual funds?", "20% plus cess on gains from units held 12 months or less, for sales from 23 July 2024."),
             ("How are debt mutual funds taxed?", "Units bought from 1 April 2023 are taxed at your income-tax slab rate whatever the holding period; there is no indexation."),
             ("How are unlisted shares taxed?", "Long term after 24 months, at 12.5% without indexation; short-term gains at your slab rate.")],
     "app": "tax"},
    {"id": "home-loan-prepayment", "name": "Home loan: prepay or invest?", "h1": "Home loan calculator: prepay or invest?",
     "title": "Home loan prepayment vs SIP calculator: prepay or invest? | Aeterna Wealth",
     "desc": "Free home loan prepayment calculator for India: put extra money into prepaying your home loan or invest it in a SIP? Interest saved, years cut, wealth at the end after tax, and the break-even return.",
     "intro": "You have some extra money each month, or a lump sum. Should it go into prepaying the home loan, or into investments while you keep paying the EMI? Enter your loan and the return you assume; the calculator compares where you end up by the loan's original end date.",
     "inputs": lambda: fld("p", "Loan outstanding (₹)", 5000000, 100000, 200000000, 100000) + fld("r", "Loan interest rate (%)", 8.5, 5, 15, 0.05)
     + fld("y", "Years left on the loan", 20, 1, 30, 1) + fld("x", "Extra money each month (₹)", 10000, 0, 1000000, 1000) + fld("l", "Lump sum available now (₹)", 0, 0, 50000000, 50000)
     + fld("i", "Assumed investment return (%)", 12, 0, 20, 0.5)
     + sel("d", "Claim home-loan interest deduction?", [("0", "No (new tax regime)"), ("1", "Yes, old regime: up to ₹2 lakh a year")], "0")
     + sel("sl", "Your income-tax slab", [("5", "5%"), ("10", "10%"), ("15", "15%"), ("20", "20%"), ("30", "30%")], "30"),
     "js": "function run(){const o={P:val('p'),rate:val('r'),years:Math.max(1,Math.round(val('y'))),extra:val('x'),lump:val('l'),r:val('i'),ded:$('#d').value==='1',slab:+$('#sl').value};"
           "const x=CALC.prepay(o),A=x.A,B=x.B,n=o.years*12,be=CALC.prepayBreakeven(o),d=B.net-A.net,cut=A.closed==null?0:n-A.closed;"
           "const ym=m=>`${Math.floor(m/12)} yrs ${m%12} mo`;"
           "if(!o.extra&&!o.lump){out([['EMI',inr(x.emi)]],'Enter an extra monthly amount or a lump sum to compare the two choices.',null,null,null);return}"
           "out([['EMI',inr(x.emi)],['Prepaying closes the loan',cut>0?ym(cut)+' earlier':'on time'],['Interest saved by prepaying',inrS(B.interest-A.interest)],[d>=0?'Investing ends ahead by':'Prepaying ends ahead by',inrS(Math.abs(d))],['Break-even return',be==null?'over 30%':be.toFixed(1)+'% a year']],"
           "`Prepaying with ${inr(o.extra)} a month${o.lump?` and ${inrS(o.lump)} now`:''} closes the loan ${cut>0?ym(cut)+' early':'on time'} and saves ${inrS(B.interest-A.interest)} of interest. Investing the same money at ${o.r}% a year instead would leave you ${inrS(Math.abs(d))} ${d>=0?'better':'worse'} off by the original end date, after tax. Investing comes out ahead only if your investments earn more than about ${be==null?'30':be.toFixed(1)}% a year; prepaying's saving is certain, investment returns are not.`,"
           "['Year','Loan left (prepay)','Invested (prepay)','Loan left (invest)','Invested (invest)'],A.rows.map((a,k)=>[a.y,inrS(a.bal),inrS(a.pot),inrS(B.rows[k].bal),inrS(B.rows[k].pot)]),"
           "{title:'Home paid off plus investments',labels:['0',...A.rows.map(a=>a.y+'y')],series:[{n:'Invest the extra',c:'var(--teal)',v:[0,...B.rows.map(b=>b.eq)]},{n:'Prepay the loan',c:'var(--brass)',dash:true,v:[0,...A.rows.map(a=>a.eq)]}]})}",
     "how": "Both choices use exactly the same money each month: the EMI plus the extra amount. <b>Prepay</b>: the extra goes into the loan; the EMI stays the same, so the loan closes early, and from then on the EMI and the extra are invested. <b>Invest</b>: you keep paying the EMI and invest the extra from day one. Interest is charged monthly on the reducing balance; investments grow monthly at the equivalent of the yearly return you assume. At the loan's original end date, both investment pots pay long-term capital-gains tax (12.5% above ₹1.25 lakh, as one sale). With the old-regime deduction, each year's interest (up to ₹2 lakh) cuts your tax at your slab, and that saving is invested too. The break-even return is the investment return at which both choices end level.",
     "example": lambda: "<p>A ₹50 lakh loan at 8.5% with 20 years left (EMI ₹43,391) and ₹10,000 a month extra: prepaying closes the loan about 7 years early and saves about ₹21.8 lakh of interest. Investing the ₹10,000 instead at an assumed 12% a year ends about ₹15.4 lakh ahead after tax by the original end date. The break-even return is about 9.5% a year, or about 8.1% if you claim the old-regime interest deduction. (The calculator opens with these numbers.)</p>",
     "faq": [("Should I prepay my home loan or invest in mutual funds?", "Compare what the loan costs you after any tax benefit with what your investments can reasonably earn after tax. Prepaying gives a certain return equal to the loan rate; equity funds have historically earned more over long periods but with ups and downs. The calculator shows the break-even return: if you expect to earn clearly more than that, and can sit through market falls, investing has tended to come out ahead."),
             ("Does prepaying reduce my EMI or my tenure?", "Usually banks keep the EMI the same and shorten the tenure, which saves the most interest. You can ask the bank to reduce the EMI instead; the interest saved is then smaller."),
             ("Are there charges for prepaying a home loan?", "RBI does not allow banks and housing finance companies to charge individuals a prepayment or foreclosure penalty on floating-rate home loans. Fixed-rate loans may carry a charge; check your loan agreement."),
             ("How does the tax deduction change the answer?", "Under the old tax regime, interest on a self-occupied home loan is deductible up to ₹2 lakh a year (section 24(b)), and principal counts towards section 80C. The deduction lowers the loan's real cost, which favours investing. Under the new regime there is no deduction for a self-occupied home."),
             ("Is it better to do both?", "Often, yes: many families keep an emergency fund, invest for long-term goals and use bonuses to prepay part of the loan. Prepaying also lowers risk, since a smaller loan is easier to carry through a job loss.")],
     "app": "prepay"},
    {"id": "cagr", "name": "CAGR calculator", "h1": "CAGR calculator",
     "title": "CAGR calculator: compound annual growth rate of an investment | Aeterna Wealth",
     "desc": "Free CAGR calculator: the steady yearly growth rate between a starting and an ending value, with absolute return and a year-by-year path. Use it for mutual funds, shares, property or any investment.",
     "intro": "Enter what you started with, what it is worth now and how many years it took.",
     "inputs": lambda: fld("s", "Starting value (₹)", 100000, 1000, 1000000000, 1000) + fld("e", "Ending value (₹)", 250000, 1000, 1000000000, 1000) + fld("y", "Years", 7, 0.5, 50, 0.5),
     "js": "function run(){const s=val('s'),e=val('e'),y=val('y'),c=CALC.cagr(s,e,y);if(c==null){out([['CAGR','–']],'Enter a starting value, an ending value and the years.',null,null,null);return}"
           "const k=Math.max(1,Math.ceil(y));out([['CAGR',c.toFixed(2)+'% a year'],['Absolute return',((e/s-1)*100).toFixed(1)+'%'],['Gain',inrS(e-s)]],"
           "`${inrS(s)} growing to ${inrS(e)} in ${y} years is a compound annual growth rate of ${c.toFixed(2)}% a year: the steady yearly rate that gets you from one to the other.`,"
           "['Year','Value at this CAGR'],[...Array(k)].map((_,i)=>[i+1,inrS(s*Math.pow(1+c/100,Math.min(i+1,y)))]),"
           "{title:'Growth at this CAGR',labels:['0',...[...Array(k)].map((_,i)=>(i+1)+'y')],series:[{n:'Value',c:'var(--teal)',v:[s,...[...Array(k)].map((_,i)=>s*Math.pow(1+c/100,Math.min(i+1,y)))]}]})}",
     "how": "CAGR = (ending value ÷ starting value)<sup>1 / years</sup> − 1. It is the single yearly rate that, compounded, turns the starting value into the ending value, ignoring the ups and downs in between. It is right for one investment made at one time; for SIPs and investments made on different dates, use the XIRR calculator.",
     "example": lambda: f"<p>₹1 lakh growing to ₹2.5 lakh in 7 years: (2.5)<sup>1/7</sup> − 1 = {((2.5 ** (1 / 7)) - 1) * 100:.2f}% a year. The absolute return is 150%, but CAGR is what lets you compare it with a fund or an index over the same 7 years.</p>",
     "faq": [("What is CAGR?", "Compound annual growth rate: the steady yearly return that turns a starting value into an ending value over a period. A fund's 3-year or 5-year return is usually quoted as a CAGR."),
             ("What is the difference between CAGR and absolute return?", "Absolute return is the total gain as a percentage, ignoring time. CAGR spreads it over the years, so investments held for different lengths of time can be compared."),
             ("CAGR or XIRR?", "CAGR for a single investment made once. XIRR when money went in or came out on different dates, such as a SIP; it gives each rupee credit only for the time it was invested."),
             ("How should I judge a fund's CAGR?", "Against its own index and its peers over the same period: our fund pages show each fund's CAGR next to its index's total-return CAGR.")],
     "app": "cagr"},
    {"id": "xirr", "name": "XIRR calculator", "h1": "XIRR calculator: your real return on SIPs and investments",
     "title": "XIRR calculator: return on SIPs and multiple investments | Aeterna Wealth",
     "desc": "Free XIRR calculator for India: the true yearly return on investments made on different dates, such as SIPs, top-ups and withdrawals, from the dates and amounts.",
     "intro": "Enter each investment (and any withdrawal) with its date, then what the holding is worth today. Blank rows are ignored.",
     "inputs": lambda: xirr_inputs(),
     "js": "function run(){if(!$('#vd').value)$('#vd').value=new Date().toISOString().slice(0,10);const fl=[];let inv=0,got=0;const rows=[];"
           "for(let k=0;k<8;k++){const d=$('#d'+k).value,a=val('i'+k),w=val('w'+k);if(!d)continue;if(a>0){fl.push({d,a:-a});inv+=a;rows.push([d,inr(a),''])}if(w>0){fl.push({d,a:w});got+=w;rows.push([d,'',inr(w)])}}"
           "const cv=val('cv');if(cv>0){fl.push({d:$('#vd').value,a:cv});got+=cv;rows.push([$('#vd').value+' (value)','',inr(cv)])}"
           "const x=CALC.xirr(fl);if(x==null){out([['XIRR','–']],'Enter at least one investment with a date, and a current value or a withdrawal.',null,null,null);return}"
           "out([['XIRR',x.toFixed(2)+'% a year'],['Total invested',inrS(inv)],['Value and withdrawals',inrS(got)],['Gain',inrS(got-inv)]],"
           "`Your money earned ${x.toFixed(2)}% a year, allowing for when each rupee went in and came out. Compare it with what the same cash flows would have earned in the fund's index.`,"
           "['Date','Invested','Received'],rows,{split:[['Invested',inv,'var(--ink-3)'],[got>=inv?'Gain':'Loss',Math.abs(got-inv),'var(--teal)']]})}",
     "how": "XIRR is the yearly rate r at which the investments and withdrawals, each discounted by (1 + r)<sup>days / 365</sup> from its own date, add up to zero. In other words, the return that a bank account would need to pay to turn exactly your cash flows into exactly your result. It is solved numerically; the calculator does it for you.",
     "example": lambda: "<p>₹50,000 invested each January from 2022 to 2025 (₹2 lakh in all), worth ₹2.8 lakh in November 2026: the XIRR is about 10.4% a year. The absolute gain is 40%, but most of the money was invested for far less than five years, which XIRR takes into account. (The calculator opens with these numbers.)</p>",
     "faq": [("What is XIRR in mutual funds?", "Extended internal rate of return: the yearly return on money that went in (and out) on different dates, like SIP instalments. Fund houses and your CAS show it for your own holdings."),
             ("Why is my SIP's XIRR different from the fund's return?", "The fund's 3-year or 5-year return is a CAGR from one date. Your XIRR depends on when each of your instalments went in and what the market did after each one."),
             ("Can XIRR be negative?", "Yes, when the current value plus withdrawals is less than what you put in."),
             ("How do I calculate XIRR in Excel or Google Sheets?", "List each investment as a negative amount and the current value as a positive amount, each with its date, then use =XIRR(amounts, dates). This calculator does the same.")],
     "app": "xirr"},
]


def xirr_inputs():
    """dated cash-flow rows for the XIRR calculator (blank rows are ignored); fits a phone without sideways scrolling"""
    d0 = ["2022-01-10", "2023-01-10", "2024-01-10", "2025-01-10"]
    st = "width:100%;min-width:0;box-sizing:border-box;padding:7px 6px;font-size:14px"
    td = "padding:4px 3px"
    rows = "".join(f"<tr><td style='{td}'><input type='date' id='d{k}' value='{d0[k] if k < 4 else ''}' aria-label='Date {k + 1}' style='{st}'></td>"
                   f"<td style='{td}'><input type='number' id='i{k}' min='0' step='500' inputmode='decimal' value='{50000 if k < 4 else ''}' aria-label='Invested {k + 1}' style='{st}'></td>"
                   f"<td style='{td}'><input type='number' id='w{k}' min='0' step='500' inputmode='decimal' value='' aria-label='Taken out {k + 1}' style='{st}'></td></tr>" for k in range(8))
    th = "padding:6px 3px;white-space:normal"
    return ("<table style='width:100%;table-layout:fixed;border-collapse:collapse'><colgroup><col style='width:42%'><col style='width:29%'><col style='width:29%'></colgroup>"
            f"<thead><tr><th class='l' style='{th}'>Date</th><th style='{th}'>Invested (₹)</th><th style='{th}'>Taken out (₹)</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
            "<label class='field'><span>Value today (₹)</span><span class='in'><input type='number' id='cv' min='0' step='1000' inputmode='decimal' value='280000' aria-label='Value today'></span></label>"
            "<label class='field'><span>Valued on</span><span class='in'><input type='date' id='vd' value='2026-11-13' aria-label='Valued on'></span></label>")


def calculator_pages(B, urls, calc_js):
    cards = ["<a class='card stack sol' href='/plan/' style='gap:6px;text-decoration:none;color:inherit;border-color:var(--teal)'><b style='font:500 18px var(--f-display)'>Money Plan</b><span class='muted' style='font-size:14px'>How much to invest, and where, for each goal; what to change in what you hold; how long retirement money lasts.</span></a>"]
    for c in CALCS:
        path = f"/calculators/{c['id']}/"
        others = " · ".join(f"<a href='/calculators/{o['id']}/'>{o['name']}</a>" for o in CALCS if o is not c)
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/calculators/">Calculators</a> › {c['name']}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">{c['h1']}</h1>
<p class="lede" style="margin-top:12px">{c['intro']}</p>
<div class="tool" id="calc" style="margin-top:22px"><div class="card stack">{c['inputs']()}</div>
<div class="stack"><div class="out" id="cOut"></div><div class="card"><p id="cTxt" style="font-size:14.5px"></p></div><div class="card cc" id="cChart"></div><div class="tablewrap" id="cTbl" tabindex="0"></div></div></div>
<noscript><p class="note">This calculator needs JavaScript; the worked example below shows the method.</p></noscript>
<h2 style="font-size:26px;margin-top:40px">How it is calculated</h2><p style="margin-top:10px">{c['how']}</p>
<h2 style="font-size:24px;margin-top:28px">Worked example</h2><div style="margin-top:10px">{c['example']()}</div>
{'<p style="margin-top:18px"><a class="btn primary" href="/#tools-sipreal">Test a SIP on real fund NAVs</a> <a class="btn" href="/calculators/xirr/">Work out your XIRR</a></p>' if c['id'] in ('sip', 'lumpsum') else ''}
{'<p style="margin-top:18px"><a class="btn primary" href="/calculators/home-loan-prepayment/">Prepay the loan or invest? Compare</a></p>' if c['id'] == 'emi' else ''}
{'<p style="margin-top:18px"><a class="btn" href="/learn/cagr-vs-xirr/">CAGR vs XIRR explained</a></p>' if c['id'] in ('cagr', 'xirr') else ''}
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{''.join(f'<details class="faq"><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>' for q, a in c['faq'])}
<p class="muted" style="font-size:12.5px;margin-top:22px">Illustrations only, not investment or tax advice. Mutual fund returns are not guaranteed and can be negative; the assumed return is yours to choose. Talk to us before acting on a tax estimate.</p>
<p style="margin-top:22px;font-size:14.5px">More calculators: {others}</p>
</div></section>
<script>{calc_js}{JS_RT}{c['js']};run();</script>"""
        app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{c['name']} by Aeterna Wealth", "url": B.SITE + path,
                  "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
                  "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "publisher": {"@id": B.SITE + "/#org"}, "description": c["desc"]}
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]}
        B.write(path, B.page(c["title"], c["desc"], path, body, (app_ld, faq_ld, B.crumbs([("Calculators", "/calculators/"), (c["name"], path)]))))
        urls.append((path, "monthly", "0.8"))
        cards.append(f"<a class='card stack sol' href='{path}' style='gap:6px;text-decoration:none;color:inherit'><b style='font:500 18px var(--f-display)'>{c['name']}</b><span class='muted' style='font-size:14px'>{B.e(c['desc'].split(': ', 1)[-1][:120])}</span></a>")
    cards.append("<a class='card stack sol' href='/#tools-sipreal' style='gap:6px;text-decoration:none;color:inherit'><b style='font:500 18px var(--f-display)'>SIP backtest on real NAVs</b><span class='muted' style='font-size:14px'>What a SIP in actual funds of a category would be worth today, from any start month.</span></a>")
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap"><h1 style="font-size:clamp(30px,4vw,44px)">Financial calculators</h1>
<p class="lede" style="margin-top:12px">Free calculators for the questions families ask most: SIPs, goals, retirement income, home loans, returns (CAGR and XIRR), inflation and capital-gains tax. Each one shows how it is calculated.</p>
<div class="grid g3" style="margin-top:26px">{''.join(cards)}</div></div></section>"""
    B.write("/calculators/", B.page("Financial calculators: SIP, home loan prepayment, CAGR, XIRR, SWP, EMI, tax | Aeterna Wealth",
                                    "Free financial calculators for India: SIP with step-up, lump sum, goal planner, home loan prepay-or-invest, CAGR, XIRR, SWP retirement income, loan EMI, inflation and capital-gains tax, each with its method explained.",
                                    "/calculators/", body, (B.crumbs([("Calculators", "/calculators/")]),)))
    urls.append(("/calculators/", "monthly", "0.8"))


# ------------------------------------------------------------------ fund tables shared by group pages
TORD = {"A+": 0, "A": 1, "B": 2, "C": 3}


def fund_table(B, L, index=False, sub="amc"):
    L = sorted(L, key=lambda f: (TORD.get(f.get("tier"), 9), -(f.get("score") or -1), f["name"]))
    if index:
        head = "<th class='l'>Fund</th><th>Rating</th><th>Expense ratio</th><th>Tracking difference, 1Y</th><th>Tracking error, 1Y</th><th>1Y return</th><th>AUM</th>"
        rows = "".join(f"<tr><td class='fund l'><a href='{f['_url']}'>{B.e(f['_name'])}</a><small>{B.e(f.get('amc', ''))}</small></td><td>{B.tier_badge(f.get('tier'))}</td>"
                       f"<td class='num'>{B.num(f.get('ter'), 2)}%</td><td class='num'>{B.num(f.get('tracking_diff_1y'))}%</td><td class='num'>{B.num(f.get('tracking_err_1y'))}%</td>"
                       f"<td class='num'>{B.pct(f.get('ret_1Y'))}</td><td class='num'>{B.cr(f.get('aum_cr'))}</td></tr>" for f in L)
    else:
        head = "<th class='l'>Fund</th><th>Rating</th><th>1Y return</th><th>3Y return</th><th>3Y vs index</th><th>Expense ratio</th><th>AUM</th>"
        rows = "".join(f"<tr><td class='fund l'><a href='{f['_url']}'>{B.e(f['_name'])}</a><small>{B.e(f.get(sub) or '')} · {B.num(f.get('age_years'), 1)} yrs</small></td>"
                       f"<td>{B.tier_badge(f.get('tier'))}</td><td class='num'>{B.pct(f.get('ret_1Y'))}</td><td class='num'>{B.pct(f.get('ret_3Y'))}</td>"
                       f"<td class='num {'pos' if (f.get('excess_3Y') or 0) > 0 else 'neg' if f.get('excess_3Y') is not None else ''}'>{B.spct(f.get('excess_3Y'))}</td>"
                       f"<td class='num'>{B.num(f.get('ter'), 2)}%</td><td class='num'>{B.cr(f.get('aum_cr'))}</td></tr>" for f in L)
    return f"<div class='tablewrap' style='margin-top:12px'><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>"


def two_plans(B, L, index=False):
    out = ""
    for plan in ("Direct", "Regular"):
        P = [f for f in L if f["plan_type"] == plan]
        if P:
            out += f"<h2 style='font-size:24px;margin-top:30px'>{plan} plans ({len(P)})</h2>" + fund_table(B, P, index)
    return out


def faq_html(B, faq):
    return "<h2 style='font-size:24px;margin-top:36px'>Common questions</h2>" + "".join(
        f"<details class='faq'><summary>{B.e(q)}</summary><p>{B.e(a)}</p></details>" for q, a in faq)


def faq_ld(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}


# ------------------------------------------------------------------ index groups and themes
def group_pages(B, funds, urls, as_of):
    idx, thm = {}, {}
    for f in funds:
        pg = str(f.get("peer_group") or "")
        if pg.startswith("Index: "):
            k = pg[7:].strip(" -")
            idx.setdefault(k, []).append(f)
        elif pg.startswith("Thematic: ") and "Other" not in pg:
            thm.setdefault(pg[10:].strip(), []).append(f)
    made_idx, made_thm = [], []
    for k, L in sorted(idx.items(), key=lambda x: -len(x[1])):
        if len(L) < 4:
            continue
        nm = B.iname(k)
        path = f"/mutual-funds/index-fund/{B.slug(nm)}/"
        d = [f for f in L if f["plan_type"] == "Direct" and f.get("tracking_err_1y") is not None]
        lo_te = min(d, key=lambda f: f["tracking_err_1y"]) if d else None
        lo_ter = min((f for f in L if f["plan_type"] == "Direct" and f.get("ter") is not None), key=lambda f: f["ter"], default=None)
        faq = [(f"How many {nm} index funds are there?", f"{len({f.get('pair_key') for f in L})} schemes track the {nm} index, with {len(L)} plans (Regular and Direct), as of {B.dmy(as_of)}.")]
        if lo_te:
            faq.append((f"Which {nm} index fund has the lowest tracking error?", f"Among Direct plans, {lo_te['_name']} had the lowest 1-year tracking error, {B.num(lo_te['tracking_err_1y'])}%, as of {B.dmy(as_of)}. Tracking error measures how closely the fund follows the index day to day."))
        if lo_ter:
            faq.append((f"Which {nm} index fund has the lowest expense ratio?", f"Among Direct plans, {lo_ter['_name']} at {B.num(lo_ter['ter'], 2)}% a year, as of {B.dmy(as_of)}."))
        faq.append(("How do you choose between index funds on the same index?", "They hold the same stocks, so look at cost (expense ratio), how closely they track (tracking difference and tracking error) and size (AUM, for smooth trading). Our rating weighs those in that order."))
        desc = f"All {len(L)} {nm} index fund plans in India compared: expense ratio, 1-year tracking difference and tracking error, returns and AUM. Updated daily."[:300]
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/index-fund/">Index funds</a> › {B.e(nm)}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">{B.e(nm)} index funds compared</h1>
<p class="lede" style="margin-top:12px">{len(L)} plans that track the {B.e(nm)} index, compared on cost and how closely they follow it. Data as of {B.dmy(as_of)}.</p>
{two_plans(B, L, index=True)}{faq_html(B, faq)}
<p class="note" style="margin-top:28px">Ratings describe past tracking and cost, not a recommendation. Read the scheme documents before investing.</p></div></section>"""
        B.write(path, B.page(f"{nm} index funds: expense ratio and tracking error compared | Aeterna Wealth", desc, path, body,
                             (faq_ld(faq), B.crumbs([("Mutual funds", "/mutual-funds/"), ("Index funds", "/mutual-funds/index-fund/"), (nm, path)]))))
        urls.append((path, "daily", "0.7"))
        made_idx.append((nm, path, len(L)))
    for k, L in sorted(thm.items(), key=lambda x: -len(x[1])):
        if len(L) < 6:
            continue
        path = f"/mutual-funds/sectoral-thematic/{B.slug(k)}/"
        reg = [f for f in L if f["plan_type"] == "Regular" and f.get("excess_3Y") is not None]
        beat = sum(f["excess_3Y"] > 0 for f in reg)
        faq = [(f"How many {k.lower()} funds are there in India?", f"{len({f.get('pair_key') for f in L})} schemes ({len(L)} plans) as of {B.dmy(as_of)}.")]
        if reg:
            faq.append((f"Have {k.lower()} funds beaten their index?", f"{beat} of {len(reg)} Regular plans with 3 years of history beat their benchmark's total-return index over the last 3 years."))
        faq.append(("Are sectoral and thematic funds risky?", "More than diversified funds: they put most of the money into one sector or theme, so returns swing more and can lag for years. Most investors keep them to a small part of the portfolio."))
        desc = f"All {len(L)} {k.lower()} sectoral and thematic mutual fund plans in India: track-record ratings, returns vs index, expense ratios and AUM. Updated daily."[:300]
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/sectoral-thematic/">Sectoral/Thematic</a> › {B.e(k)}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">{B.e(k)} funds in India</h1>
<p class="lede" style="margin-top:12px">{len(L)} sectoral and thematic plans in the {B.e(k.lower())} theme, rated against each other and their sector index. Data as of {B.dmy(as_of)}.</p>
{two_plans(B, L)}{faq_html(B, faq)}
<p class="note" style="margin-top:28px">Ratings describe past track records and are not a recommendation. Read the scheme documents before investing.</p></div></section>"""
        B.write(path, B.page(f"{k} mutual funds: ratings, returns and costs | Aeterna Wealth", desc, path, body,
                             (faq_ld(faq), B.crumbs([("Mutual funds", "/mutual-funds/"), ("Sectoral/Thematic", "/mutual-funds/sectoral-thematic/"), (k, path)]))))
        urls.append((path, "daily", "0.7"))
        made_thm.append((k, path, len(L)))
    return made_idx, made_thm


# ------------------------------------------------------------------ fund houses
def amc_pages(B, funds, urls, as_of):
    by = {}
    for f in funds:
        by.setdefault(f.get("amc") or "Other", []).append(f)
    cards = []
    for a, L in sorted(by.items()):
        path = f"/mutual-funds/amc/{B.slug(a)}/"
        cats = {}
        for f in L:
            cats.setdefault(f["category"], []).append(f)
        rated = [f for f in L if f.get("tier") in TORD]
        top = sum(f["tier"] in ("A+", "A") for f in rated)
        secs = "".join(f"<h2 style='font-size:22px;margin-top:28px'>{B.e(c)} ({len(X)} plans)</h2>" + fund_table(B, X, index=(c == "Index Fund"), sub="peer_group")
                       for c, X in sorted(cats.items(), key=lambda x: -len(x[1])))
        schemes = len({f.get("pair_key") for f in L})
        faq = [(f"How many equity funds does {a} have?", f"{schemes} equity and index schemes ({len(L)} plans, Regular and Direct) across {len(cats)} categories, as of {B.dmy(as_of)}.")]
        if rated:
            faq.append((f"How do {a} funds rate?", f"{top} of {len(rated)} rated plans are in the A+ or A tier, meaning the top 30% of their category on track record. Ratings compare each plan only with peers in the same category and plan type."))
        desc = f"All {schemes} {a} equity and index fund schemes: track-record ratings, returns vs index, expense ratios and AUM by category. Updated daily."[:300]
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/amc/">Fund houses</a> › {B.e(a)}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">{B.e(a)}: equity and index funds</h1>
<p class="lede" style="margin-top:12px">{schemes} schemes in {len(cats)} categories{f'; {top} of {len(rated)} rated plans are in the top two tiers of their category' if rated else ''}. Data as of {B.dmy(as_of)}.</p>
{secs}{faq_html(B, faq)}
<p class="note" style="margin-top:28px">Ratings describe past track records and are not a recommendation. Read the scheme documents before investing.</p></div></section>"""
        B.write(path, B.page(f"{a} schemes: equity fund ratings, returns and costs | Aeterna Wealth", desc, path, body,
                             (faq_ld(faq), B.crumbs([("Mutual funds", "/mutual-funds/"), ("Fund houses", "/mutual-funds/amc/"), (a, path)]))))
        urls.append((path, "daily", "0.6"))
        cards.append(f"<a href='{path}'>{B.e(a)}</a> <span class='muted'>({schemes})</span>")
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › Fund houses</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Mutual fund houses (AMCs) in India</h1>
<p class="lede" style="margin-top:12px">{len(by)} fund houses with open-ended equity or index funds. Pick one to see every scheme it runs, rated within its category.</p>
<ul style="columns:3 220px;margin-top:22px;line-height:2">{''.join(f'<li>{c}</li>' for c in cards)}</ul></div></section>"""
    B.write("/mutual-funds/amc/", B.page("Mutual fund houses (AMCs) in India: all equity schemes rated | Aeterna Wealth",
                                         f"All {len(by)} Indian mutual fund houses with equity and index funds, each with its schemes rated on track record, returns, cost and holdings.",
                                         "/mutual-funds/amc/", body, (B.crumbs([("Mutual funds", "/mutual-funds/"), ("Fund houses", "/mutual-funds/amc/")]),)))
    urls.append(("/mutual-funds/amc/", "weekly", "0.7"))


# ------------------------------------------------------------------ fund vs fund
CMP_CATS = ["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap", "Flexi Cap", "Focused", "ELSS", "Value / Contra",
            "Dividend Yield", "Aggressive Hybrid", "Balanced Advantage", "Multi Asset Allocation", "Arbitrage"]
CMP_TOP = 8          # the largest schemes per category compared pairwise (28 pages a category)
CMP_INDEX = {}       # index funds are not compared pairwise (Nov 2026); old pages redirect to /mutual-funds/index-fund/
CMP_INDEX_REMOVED = {"Index: NIFTY 50": 8, "Index: NIFTY NEXT 50": 6}


def overlap(h1, h2):
    a = {t[0]: t[2] for t in h1 or []}
    b = {t[0]: t[2] for t in h2 or []}
    common = set(a) & set(b)
    return len(common), sum(min(a[k], b[k]) for k in common)


def _rk(B, X):
    if X.get("score") is None or X.get("peer_rank") is None:
        return "–"
    return f"{X['score']:.0f} · #{int(X['peer_rank'])} of {int(X['peer_count'])}"


def _top10(B, f):
    v = f.get("top10_pct")
    return "–" if v is None else B.pct(v, 0) if v <= 1 else f"{v:.0f}%"


def _mix(f):
    v = [f.get(k) for k in ("large_pct", "mid_pct", "small_pct")]
    return "–" if any(x is None for x in v) else " / ".join(f"{x:.0f}" for x in v) + "%"


def _related(B, a, b, rel, path, c):
    out = []
    for f in (a, b):
        L = [(n, p) for n, p in rel.get(f["pair_key"], []) if p != path][:7]
        if L:
            out.append(f"<div><b>{B.e(f['_name'])} vs</b><ul style='margin:6px 0 0;padding-left:20px'>" + "".join(f"<li><a href='{p}'>{B.e(n)}</a></li>" for n, p in L) + "</ul></div>")
    lc = c if c == "ELSS" else c.lower()
    tp = getattr(B, "MADE_TOP", {}).get(c)
    top = f"<p style='margin-top:14px'>" + (f"<a href='{tp}'>Top-rated {B.e(lc)} funds this month</a> · " if tp else "") + f"<a href='/mutual-funds/{B.slug(c)}/'>All {B.e(lc)} funds</a></p>"
    return ("<h2 style='font-size:24px;margin-top:34px'>More comparisons</h2><div class='grid g2' style='margin-top:12px'>" + "".join(out) + "</div>" + top) if out else top


def removed_index_compare_paths(B, funds):
    """the index-fund comparison pages published until Nov 2026, so they can redirect"""
    out = []
    D = sorted([f for f in funds if f["category"] == "Index Fund" and f["plan_type"] == "Direct" and f.get("aum_cr")], key=lambda f: -f["aum_cr"])
    for g, n in CMP_INDEX_REMOVED.items():
        for a, b in combinations([f for f in D if str(f.get("peer_group")) == g][:n], 2):
            a, b = sorted((a, b), key=lambda f: f["_name"])
            out.append(f"/compare/{B.slug(a['_name'])}-vs-{B.slug(b['_name'])}/")
    return out


def compare_pages(B, funds, hold, urls, as_of):
    """Pages for the most-asked pairs: the CMP_TOP largest schemes in each main category (by Direct-plan AUM), and the
    largest Nifty 50 / Nifty Next 50 index funds. Each page: both plans' ratings and returns, consistency, falls,
    company-size mix, cost in rupees, overlap, and links to the other comparisons of both funds."""
    made = {}
    by_pair = {}
    for f in funds:
        by_pair.setdefault(f.get("pair_key"), {})[f["plan_type"]] = f
    groups = []
    for c in CMP_CATS:
        D = sorted([f for f in funds if f["category"] == c and f["plan_type"] == "Direct" and f.get("aum_cr")], key=lambda f: -f["aum_cr"])
        if c == "Index Fund":
            groups += [(c, [f for f in D if str(f.get("peer_group")) == g][:n]) for g, n in CMP_INDEX.items()]
        else:
            groups.append((c, D[:CMP_TOP]))
    pairs = []
    for c, D in groups:
        pairs += [(c, a, b) for a, b in combinations(D, 2)]
    # every page links to the other comparisons of both its funds
    rel = {}
    for c, a, b in pairs:
        a2, b2 = sorted((a, b), key=lambda f: f["_name"])
        pth = f"/compare/{B.slug(a2['_name'])}-vs-{B.slug(b2['_name'])}/"
        for x, y in ((a2, b2), (b2, a2)):
            rel.setdefault(x["pair_key"], []).append((y["_name"], pth))
    for c, a, b in pairs:
        if True:
            a, b = sorted((a, b), key=lambda f: f["_name"])
            path = f"/compare/{B.slug(a['_name'])}-vs-{B.slug(b['_name'])}/"
            if path in made.values():
                continue
            A, Bp = by_pair.get(a.get("pair_key"), {}), by_pair.get(b.get("pair_key"), {})
            n_common, ov = overlap(hold.get(a.get("pair_key")), hold.get(b.get("pair_key")))
            rows = [("Category", a["category"], b["category"]), ("Fund house", a.get("amc"), b.get("amc")),
                    ("Benchmark", a.get("bench_label") or (B.iname(a.get("benchmark")) + " TRI" if a.get("benchmark") else "–"),
                     b.get("bench_label") or (B.iname(b.get("benchmark")) + " TRI" if b.get("benchmark") else "–")),
                    ("Age", f"{B.num(a.get('age_years'), 1)} years", f"{B.num(b.get('age_years'), 1)} years"),
                    (B.aum_label(a) if a.get("aum_asof") == b.get("aum_asof") else "AUM", B.cr(a.get("aum_cr")), B.cr(b.get("aum_cr")))]
            for plan, X, Y in (("Direct", a, b), ("Regular", A.get("Regular"), Bp.get("Regular"))):
                if not X or not Y:
                    continue
                rows += [(f"<b>{plan} plan</b>", "", ""), ("Rating", B.tier_badge(X.get("tier")), B.tier_badge(Y.get("tier"))),
                         ("Expense ratio", f"{B.num(X.get('ter'), 2)}%", f"{B.num(Y.get('ter'), 2)}%"),
                         ("1Y return", B.pct(X.get("ret_1Y")), B.pct(Y.get("ret_1Y"))), ("3Y return (a year)", B.pct(X.get("ret_3Y")), B.pct(Y.get("ret_3Y"))),
                         ("5Y return (a year)", B.pct(X.get("ret_5Y")), B.pct(Y.get("ret_5Y"))),
                         ("3Y vs index", B.spct(X.get("excess_3Y")), B.spct(Y.get("excess_3Y"))),
                         ("Rating score, rank", _rk(B, X), _rk(B, Y))]
            rows += [("<b>Consistency, risk and portfolio</b>", "", ""),
                     ("Ahead of index, rolling 3Y periods", B.pct(a.get("roll3y_hit_rate"), 0), B.pct(b.get("roll3y_hit_rate"), 0)),
                     ("Deepest fall, 3Y", B.pct(a.get("max_drawdown_3y")), B.pct(b.get("max_drawdown_3y"))),
                     ("Volatility, 3Y", B.pct(a.get("vol_3y")), B.pct(b.get("vol_3y"))),
                     ("Max fall, 5Y", B.pct(a.get("max_drawdown_5y")), B.pct(b.get("max_drawdown_5y"))),
                     ("Down capture, 3Y", B.num(a.get("downside_capture_3y"), 0), B.num(b.get("downside_capture_3y"), 0)),
                     ("Stocks held", B.num(a.get("n_stocks"), 0), B.num(b.get("n_stocks"), 0)),
                     ("Top 10 holdings", _top10(B, a), _top10(B, b)),
                     ("Large / mid / small caps", _mix(a), _mix(b)),
                     ("Largest sector", B.e(a.get("top_sector") or "–"), B.e(b.get("top_sector") or "–"))]
            tbl = "".join(f"<tr><td class='l'>{k}</td><td class='num'>{x if x is not None else '–'}</td><td class='num'>{y if y is not None else '–'}</td></tr>" for k, x, y in rows)
            r3a, r3b = a.get("ret_3Y"), b.get("ret_3Y")
            summ = []
            if r3a is not None and r3b is not None:
                hi, lo = (a, b) if r3a >= r3b else (b, a)
                summ.append(f"Over the last 3 years, {hi['_name']} returned {B.pct(hi['ret_3Y'])} a year against {B.pct(lo['ret_3Y'])} for {lo['_name']} (Direct plans).")
            ha, hb = a.get("roll3y_hit_rate"), b.get("roll3y_hit_rate")
            if ha is not None and hb is not None and abs(ha - hb) >= 0.05:
                hi, lo = (a, b) if ha > hb else (b, a)
                summ.append(f"{hi['_name']} was the more consistent: ahead of its index in {B.pct(hi['roll3y_hit_rate'], 0)} of rolling 3-year periods, against {B.pct(lo['roll3y_hit_rate'], 0)}.")
            da, db = a.get("downside_capture_3y"), b.get("downside_capture_3y")
            if da is not None and db is not None and abs(da - db) >= 5:
                lo_, hi_ = (a, b) if da < db else (b, a)
                summ.append(f"In falling months, {lo_['_name']} fell less: {B.num(lo_['downside_capture_3y'], 0)}% of the index's fall, against {B.num(hi_['downside_capture_3y'], 0)}%.")
            sa, sb_ = a.get("small_pct"), b.get("small_pct")
            if sa is not None and sb_ is not None and abs(sa - sb_) >= 10 and c not in ("Small Cap", "Arbitrage"):
                big, sml = (a, b) if sa > sb_ else (b, a)
                summ.append(f"{big['_name']} leans more to smaller companies ({big['small_pct']:.0f}% in small caps against {sml['small_pct']:.0f}%), so expect bigger swings both ways.")
            if hold.get(a.get("pair_key")) and hold.get(b.get("pair_key")):
                summ.append(f"They hold {n_common} stocks in common; the portfolio overlap is {ov:.0f}%.")
            ta, tb = a.get("tier"), b.get("tier")
            rate_ans = (f"On our track-record ratings (Direct plans), {a['_name']} is rated {ta} and {b['_name']} is rated {tb}, each against its own category. "
                        "Ratings describe the record so far and are not a forecast; which suits you depends on your goal and the funds you already hold.") if ta and tb else ""
            faq = [(f"{a['_name']} or {b['_name']}: which is better?", rate_ans or "Neither is better for everyone; see the table and how each fits your portfolio."),
                   (f"{a['_name']} or {b['_name']}: which has done better?", " ".join(summ[:1]) or "See the table for returns over each period."),
                   (f"How much do {a['_name']} and {b['_name']} overlap?", summ[-1] if hold.get(a.get("pair_key")) and hold.get(b.get("pair_key")) else "Holdings for one of these schemes are not available yet."),
                   ("Should I hold both?", "Two funds with a high overlap add little diversification. Check how they fit your goal and the rest of your portfolio; we can help.")]
            desc = (f"{a['_name']} vs {b['_name']}: returns, rating, expense ratio, risk and portfolio overlap compared, Direct and Regular plans. " + " ".join(summ))[:300]
            body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/{B.slug(c)}/">{B.e(c)}</a> › Compare</nav>
<h1 style="font-size:clamp(28px,4vw,40px);margin-top:14px">{B.e(a['_name'])} vs {B.e(b['_name'])}</h1>
<p class="lede" style="margin-top:12px">{B.e(' '.join(summ))} Data as of {B.dmy(as_of)}.</p>
<div class="tablewrap" style="margin-top:20px"><table class="cmp"><thead><tr><th class="l"></th><th><a href="{a['_url']}">{B.e(a['_name'])}</a></th><th><a href="{b['_url']}">{B.e(b['_name'])}</a></th></tr></thead><tbody>{tbl}</tbody></table></div>
<div class="row" style="margin-top:16px"><a class="btn primary" href="/#compare">Compare any funds interactively</a><a class="btn" href="{B.wa_link(f"Hello Aeterna, I'm comparing {a['_name']} and {b['_name']} and would like help choosing.")}" target="_blank" rel="noopener">Ask us which fits you</a></div>
{faq_html(B, faq)}
{_related(B, a, b, rel, path, c)}
<p class="note" style="margin-top:28px">Past performance does not guarantee future returns. This comparison is not a recommendation to buy or sell either fund.</p></div></section>"""
            B.write(path, B.page(f"{a['_name']} vs {b['_name']}: returns, risk, cost and overlap | Aeterna Wealth", desc, path, body,
                                 (faq_ld(faq), B.crumbs([("Mutual funds", "/mutual-funds/"), (c, f"/mutual-funds/{B.slug(c)}/"), ("Compare", path)]))))
            urls.append((path, "weekly", "0.6"))
            made[(a["pair_key"], b["pair_key"])] = path
    return made


# ------------------------------------------------------------------ insights
def insight_pages(B, ins, urls, as_of):
    items = ins.get("items") or []
    if not items:
        return
    cards = []
    for i in items:
        path = f"/insights/{i['id']}/"
        extra = ""
        if i.get("kind") == "scoreboard":
            extra = ("<div class='tablewrap' style='margin-top:18px'><table><thead><tr><th class='l'>Category</th><th>Beat the index, 3Y</th><th>Beat the index, 5Y</th></tr></thead><tbody>"
                     + "".join(f"<tr><td class='l'>{B.e(r['category'])}</td><td class='num'>{r['beat3']} of {r['n3']}</td><td class='num'>{(str(r['beat5']) + ' of ' + str(r['n5'])) if r['n5'] else '–'}</td></tr>" for r in i["rows"])
                     + "</tbody></table></div>")
        t = i.get("try") or {}
        link = "/#ratings" if t.get("tool") == "ratings" else "/#tools-" + t.get("tool", "sip")
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap" style="max-width:820px">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/insights/">Insights</a> › {B.e(i['title'])}</nav>
<div class="big-fig" style="margin-top:18px">{B.e(i['figure'])}</div>
<h1 style="font-size:clamp(28px,4vw,40px);margin-top:8px">{B.e(i['title'])}</h1>
<p class="muted" style="margin-top:8px">Aeterna Wealth · worked out from AMFI NAVs and NSE total-return indices · data as of {B.dmy(ins.get('as_of') or as_of)}</p>
<p class="lede" style="margin-top:16px">{B.e(i['text'])}</p>{extra}
<p style="margin-top:20px"><a class="btn primary" href="{link}">Check it yourself</a></p>
<p class="note" style="margin-top:28px">Recomputed every weekday from public data. Describes what has happened, not what will; not a recommendation to buy or sell any fund.</p>
</div></section>"""
        art = {"@context": "https://schema.org", "@type": "Article", "headline": i["title"][:110], "description": i["text"][:300],
               "datePublished": ins.get("as_of") or as_of, "dateModified": ins.get("as_of") or as_of, "inLanguage": "en-IN",
               "author": {"@id": B.SITE + "/#org"}, "publisher": {"@id": B.SITE + "/#org"}, "image": B.SITE + "/og.png",
               "mainEntityOfPage": B.SITE + path}
        B.write(path, B.page(f"{i['title']} | Aeterna Wealth insights", i["text"][:300], path, body,
                             (art, B.crumbs([("Insights", "/insights/"), (i["title"], path)]))))
        urls.append((path, "daily", "0.6"))
        cards.append(f"<a class='card stack' href='{path}' style='gap:8px;text-decoration:none;color:inherit'><div class='big-fig'>{B.e(i['figure'])}</div><b style='font:500 18px/1.3 var(--f-display)'>{B.e(i['title'])}</b><span class='muted' style='font-size:14px'>{B.e(i['text'][:160])}…</span></a>")
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap"><h1 style="font-size:clamp(30px,4vw,44px)">Indian mutual funds in numbers</h1>
<p class="lede" style="margin-top:12px">Facts worked out from our own data every weekday: what SIPs have earned, how many funds beat their index, and what costs add up to. Last updated {B.dmy(ins.get('as_of') or as_of)}.</p>
<div class="grid g3" style="margin-top:26px">{''.join(cards)}</div></div></section>"""
    B.write("/insights/", B.page("Mutual fund insights: SIP returns, funds vs index, costs | Aeterna Wealth",
                                 "Data-backed facts on Indian mutual funds, recomputed every weekday: 10-year SIP returns by category, SIPs started at market highs, how many active funds beat their index, and Regular vs Direct costs.",
                                 "/insights/", body, (B.crumbs([("Insights", "/insights/")]),)))
    urls.append(("/insights/", "daily", "0.8"))


# ------------------------------------------------------------------ legal
def legal_pages(B, urls):
    O = B.ORG
    upd = "5 November 2026"
    pages = {
        "disclosures": ("Disclosures", f"""
<h2>Registration</h2><p>{O['name']} is registered with the Association of Mutual Funds in India (AMFI) as a mutual fund distributor, {O['arn']}. We are not registered with SEBI as an investment adviser or a research analyst, and we do not advise on individual listed shares.</p>
<h2>Mutual funds and commission</h2><p>We receive commission from asset management companies for investments in Regular plans. Commission rates differ across schemes and fund houses and are shown in your Consolidated Account Statement. Direct plans of the same schemes carry a lower expense ratio and pay no distributor commission; you can invest in them directly with the fund house.</p>
<h2>Portfolio management services (PMS) and alternative investment funds (AIFs)</h2><p>We distribute PMS and AIF products offered by SEBI-registered portfolio managers and AIF managers, and receive a fee or commission from them; we can tell you the amount for any product before you invest. The minimum investment is ₹50 lakh for PMS and ₹1 crore for most AIFs. These products are not guaranteed, can lose value, may be illiquid for years and carry higher fees than mutual funds. Read the disclosure document or private placement memorandum before investing.</p>
<h2>Bonds and unlisted shares</h2><p>Bonds are offered through SEBI-registered online bond platform providers or stockbrokers. Bonds carry credit, interest-rate and liquidity risk; a rating is an opinion, not a guarantee. Unlisted shares are not traded on a stock exchange, can be hard to sell, have limited public information and can lose value. We may earn a margin or fee on these transactions; ask us for it before you invest.</p>
<h2>About the ratings and data</h2><p>Ratings and statistics on this site are computed from public data (AMFI, NSE Indices and fund-house disclosures) using the method described on the Method page. They describe past track records and are not investment advice, a recommendation to buy, sell or hold any scheme, or a forecast of future returns. Our own backtest found that the ratings did not predict the following three years' returns. Data may contain errors or delays; check scheme documents before investing.</p>
<h2>Risk</h2><p>Mutual fund investments are subject to market risks; read all scheme-related documents carefully. Past performance may or may not be sustained in future.</p>"""),
        "privacy": ("Privacy policy", f"""
<p>Last updated {upd}. This policy explains what personal data {O['name']} ("we") collects through this website and how we use it, in line with the Digital Personal Data Protection Act, 2023.</p>
<h2>What we collect</h2><ul><li><b>What you send us:</b> your name, phone number, email and message when you contact us by WhatsApp, phone, email or a form.</li><li><b>Usage data:</b> pages visited, device and browser type, approximate location (city) and how you reached the site, through Cloudflare Web Analytics (no cookies) and Google Analytics (which sets cookies named <code>_ga</code> and <code>_ga_*</code> holding a random identifier).</li></ul>
<p>The calculators and fund data run in your browser; the numbers you enter are not sent to us. A few preferences, such as the funds you add to Compare, are kept in your own browser's storage.</p>
<h2>How we use it</h2><p>To reply to you and provide the services you ask for, to meet our legal and regulatory duties (including KYC when you invest), and, in aggregate, to understand which pages are useful. We do not sell personal data and do not show ads.</p>
<h2>Who we share it with</h2><p>Fund houses, registrars (CAMS, KFintech), product manufacturers and platforms when you invest through us, as required to process your transactions; service providers that host this site and analytics (Cloudflare, Google), under their terms; and regulators or authorities when the law requires.</p>
<h2>How long we keep it</h2><p>Enquiries for up to 3 years unless you become a client; client records for as long as regulations require (generally at least 8 years).</p>
<h2>Your rights</h2><p>You can ask to see, correct or delete your personal data, or withdraw consent, by writing to {O['email']}. You can block or delete cookies in your browser settings at any time. If you are not satisfied with our response, you may complain to the Data Protection Board of India.</p>
<h2>Contact</h2><p>{O['name']}, {O['street']}, {O['city']} {O['pin']} · {O['email']} · +91 85959 93600</p>"""),
        "terms": ("Terms of use", f"""
<p>Last updated {upd}. By using this website you agree to these terms.</p>
<h2>Information, not advice</h2><p>The fund data, ratings, insights and calculators on this site are general information. They are not investment, tax or legal advice, or a recommendation to buy, sell or hold any product. Calculators use the assumptions you enter; actual returns will differ.</p>
<h2>Accuracy</h2><p>The data comes from public sources (AMFI, NSE Indices, fund houses) and is processed automatically. We work to keep it correct and current but do not guarantee that it is complete, accurate or timely. Check the scheme documents and the fund house before investing.</p>
<h2>Use of the data</h2><p>You may view, download and cite the fund data, including the CSV and JSON files, with a link to aeternawealth.com. Do not present it as your own or imply that we endorse your product.</p>
<h2>Links</h2><p>Links to other sites, such as fund houses or the client login provider, are for convenience; we are not responsible for their content.</p>
<h2>Liability</h2><p>To the extent the law allows, we are not liable for any loss arising from use of this site or reliance on its content.</p>
<h2>Law</h2><p>These terms are governed by the laws of India; courts in New Delhi have jurisdiction.</p>"""),
        "grievances": ("Grievance redressal", f"""
<p>If you have a complaint about our service, we want to put it right quickly.</p>
<h2>Step 1: write to us</h2><p>Email {O['email']} or call +91 85959 93600 (Mon–Sat, 10 am–7 pm), with your name, folio or PAN and what went wrong. We acknowledge within 2 working days and aim to resolve within 21 days.</p>
<h2>Step 2: the fund house</h2><p>For a complaint about a scheme or a transaction, you can also write to the asset management company's investor service team; their details are in the scheme documents and on their website.</p>
<h2>Step 3: SEBI SCORES and Online Dispute Resolution</h2><p>If you are not satisfied, you can lodge a complaint on SEBI's SCORES portal, <a href="https://scores.sebi.gov.in" target="_blank" rel="noopener">scores.sebi.gov.in</a>. After that, you can start online conciliation or arbitration through the Securities Market ODR portal, <a href="https://smartodr.in" target="_blank" rel="noopener">smartodr.in</a>.</p>
<h2>Distributor details</h2><p>{O['name']} · AMFI-registered mutual fund distributor · {O['arn']} · {O['street']}, {O['city']} {O['pin']}</p>"""),
    }
    for slug_, (h1, html) in pages.items():
        path = f"/{slug_}/"
        body = f"<section class='band' style='padding-top:28px'><div class='wrap prose' style='max-width:820px'><h1 style='font-size:clamp(30px,4vw,44px)'>{h1}</h1>{html}</div></section>"
        B.write(path, B.page(f"{h1} | Aeterna Wealth", f"{h1} of {O['name']}, AMFI-registered mutual fund distributor ({O['arn']}).", path, body,
                             (B.crumbs([(h1, path)]),)))
        urls.append((path, "yearly", "0.3"))


def calc_js(app_html):
    a, b = app_html.index("/* CALC-START"), app_html.index("/* CALC-END */")
    return app_html[a:b]
