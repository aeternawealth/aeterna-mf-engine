"""Advance tax calculator: /income-tax/advance-tax-calculator/ (tax year 2026-27).

The year's tax comes from the full engine (site/tax_engine.js, txBoth); the instalments and interest from txAdvance in
the same file, tested in tests/test_tax_engine.py. No section numbers are shown: the new Act's numbers go up only from the
tax department's official mapping.
"""
import json

FY, CHECKED = "2026-27", "25 Nov 2026"
DUE = [("2026-06-15", "15 June 2026", 15), ("2026-09-15", "15 September 2026", 45), ("2026-12-15", "15 December 2026", 75), ("2027-03-15", "15 March 2027", 100)]

FAQ = [
    ("Who has to pay advance tax?",
     "Anyone whose tax for the year, after TDS and TCS, comes to ₹10,000 or more: salaried people with rent, interest, capital gains "
     "or freelance income that TDS does not cover, professionals, business owners, investors and NRIs with Indian income. "
     "Residents aged 60 or more with no business or professional income are exempt."),
    ("What are the due dates for tax year 2026-27?",
     "15 June 2026 (15% of the year's tax), 15 September 2026 (45%), 15 December 2026 (75%) and 15 March 2027 (100%). The percentages are "
     "cumulative: by each date, that share of the year's tax should have been paid in total."),
    ("What if I pay late or too little?",
     "Interest of 1% a month on the shortfall. For each of the first three instalments it runs for 3 months, and for the March "
     "instalment 1 month. There is no interest for June if you paid at least 12% of the year's tax, or for September if you paid at least "
     "36%. If less than 90% is paid by 31 March, a further 1% a month runs from April on the unpaid tax until you pay it."),
    ("I have a presumptive business or profession. When do I pay?",
     "If you declare income on a presumptive basis (a share of turnover or receipts), the whole advance tax is due in one instalment "
     "by 15 March 2027. Paying earlier is allowed."),
    ("What if I sell shares or mutual funds during the year?",
     "Capital gains often cannot be estimated in advance. If the gain arises after an instalment date, no interest is charged for the "
     "earlier instalments as long as the tax on it is paid in the instalments that remain, or by 31 March if the gain comes after 15 March."),
    ("My employer deducts TDS. Do I still need to pay?",
     "Only if TDS falls short of your total tax by ₹10,000 or more, which usually happens when you have rent, interest, capital gains or "
     "other income besides salary. Enter that income and your expected TDS above to see."),
    ("How do I pay advance tax?",
     "Online on the income tax e-filing portal, through e-Pay Tax, choosing 'Advance tax' as the type of payment and tax year 2026-27, "
     "by net banking, UPI, card or at a bank. Keep the challan receipt; you enter it in your return."),
]

FIELDS_X = [  # advance-tax inputs, shown above the income form
    ("axRegime", "Regime you will file under", [("lower", "Whichever is lower"), ("new", "New regime"), ("old", "Old regime")]),
    ("axSal", "Does your employer deduct tax from your salary?", [("1", "Yes: count it as paid"), ("0", "No")]),
    ("axTDS", "Other TDS and TCS for the year (bank interest, rent, property sale and so on)", 0),
    ("axPres", "Business or profession on a presumptive basis?", [("0", "No"), ("1", "Yes (pay it all by 15 March)")]),
    ("axP0", "Advance tax paid up to 15 June 2026", 0),
    ("axP1", "Paid 16 June to 15 September", 0),
    ("axP2", "Paid 16 September to 15 December", 0),
    ("axP3", "Paid 16 December to 15 March", 0),
    ("axMon", "If anything is left after March, when will you pay it?", [("4", "With the return, by 31 July 2027"), ("1", "In April 2027"), ("2", "In May 2027"), ("3", "In June 2027")]),
]

JS = r"""
const $=s=>document.querySelector(s),inr=v=>'₹'+Math.round(Math.max(0,v||0)).toLocaleString('en-IN');
const IDS=__IDS__,DUE=__DUE__;
function val(i){const el=$('#'+i);return !el?0:el.tagName==='SELECT'?el.value:+el.value||0}
function read(){const p={};for(const i of IDS)p[i]=val(i);p.resident=p.resident!=='0';p.metro=p.metro==='1';p.parentsSenior=p.parentsSenior==='1';return p}
function run(){const p=read(),{N,O}=txBoth(p),reg=val('axRegime'),R=reg==='old'?O:reg==='new'?N:(O.payable<N.payable?O:N);
 const S={};for(const i of ['age','resident','salary','basic','hraRecd','rent','metro','profTax','employerNPS','selfInterest','c80','nps1b','d80self','d80parents','parentsSenior','e80','g80','u80','otherDed'])S[i]=p[i];
 const salTDS=val('axSal')==='1'&&+p.salary>0?txCompute(S,R===N?'new':'old').payable:0;
 const tax=R.payable,T=Math.max(0,tax-salTDS-val('axTDS')),pres=val('axPres')==='1',exempt=p.resident&&p.age!=='<60'&&!(+p.business>0);
 const paid=[0,1,2,3].map(i=>Math.max(0,+val('axP'+i)||0)),months=+val('axMon');
 const A=txAdvance(T,paid,{presumptive:pres,exempt,months});
 const today=new Date().toISOString().slice(0,10);let k=DUE.findIndex(d=>today<=d[0]);if(pres&&k>=0)k=3;
 // interest already run up: past windows as entered, the rest paid on time
 let fill=paid.slice();if(k>=0)for(let i=k;i<4;i++){const need=A.due[i]-fill.slice(0,i+1).reduce((a,b)=>a+b,0);if(need>0)fill[i]+=need}
 const B=txAdvance(T,fill,{presumptive:pres,exempt,months}),Z=txAdvance(T,paid.map((v,i)=>k<0||i<k?v:(i===k?v:0)),{presumptive:pres,exempt,months});
 const regName=R===N?'new':'old';
 let head;
 if(!A.liable)head=`<div><span>Tax for the year (${regName} regime)</span><b>${inr(tax)}</b></div><div><span>After TDS and TCS</span><b>${inr(T)}</b></div><div><span>Advance tax</span><b>None due</b></div>`;
 else{const nx=k<0?null:Math.max(0,A.due[k]-A.cum[k]);
  head=`<div><span>Tax for the year (${regName} regime)</span><b>${inr(tax)}</b></div><div><span>Advance tax for the year, after TDS${salTDS?' (salary TDS '+inr(salTDS)+')':''}</span><b>${inr(T)}</b></div>`+
   (k<0?`<div><span>All instalments are past</span><b>${inr(Math.max(0,T-A.cum[3]))} left</b></div>`:`<div><span>Pay by ${DUE[k][1]}</span><b>${inr(nx)}</b></div>`)}
 $('#axOut').innerHTML=head;
 let note='';
 if(exempt&&T>=10000)note='You are a resident aged 60 or more with no business income, so you need not pay advance tax. Pay the tax before you file your return.';
 else if(!A.liable)note=T>0?`Your tax after TDS is under ₹10,000, so no advance tax is due. Pay ${inr(T)} before you file your return.`:'TDS covers your tax: nothing more to pay.';
 $('#axNote').innerHTML=note;
 $('#axTbl').hidden=$('#axInt').hidden=!A.liable;$('#axNote').hidden=!note;
 if(!A.liable)return
 const rows=DUE.map((d,i)=>{const pc=pres?(i<3?0:100):d[2],left=Math.max(0,A.due[i]-A.cum[i]);
  return `<tr${i===k?' class="ax-now"':''}><td class="l">${d[1].replace(/(\d+) (\w{3})\w* (20\d\d)/,'$1 $2 $3')}<small class="muted" style="display:block;font-size:12px">${pc}% of the tax${i===k?' <span class="ax-tag">next</span>':''}</small></td><td class="num">${inr(A.due[i])}</td><td class="num">${inr(A.cum[i])}</td><td class="num">${inr(left)}</td></tr>`}).join('');
 $('#axTbl').innerHTML=`<table><thead><tr><th class="l">Due date</th><th>Due</th><th>Paid</th><th>Short</th></tr></thead><tbody>${rows}</tbody></table>`;
 const I=[];
 if(B.interest>0)I.push(`Interest already owed for missed instalments, even if you pay the rest on time: <b>${inr(B.interest)}</b>. It is paid with the balance tax.`);
 else I.push('No interest so far: you are on time.');
 if(k>=0&&Z.interest>B.interest)I.push(`If you pay nothing more until you file in July, interest would come to about <b>${inr(Z.interest)}</b>.`);
 if(A.interest>0&&k<0)I.push(`Interest on what you have entered: <b>${inr(A.interest)}</b>.`);
 $('#axInt').innerHTML=I.map(t=>`<p style="margin-top:6px">${t}</p>`).join('');
 const msg=encodeURIComponent(`Hi, I used the Aeterna advance tax calculator (FY __FY__): advance tax for the year ${inr(T)}. I would like a CA to check it.`);$('#axCA').href='__WA__'+msg}
document.querySelectorAll('#axForm input,#axForm select').forEach(el=>el.addEventListener('input',run));run();
"""


def advance_page(B, urls, v):
    import tax_pages as TP
    e = B.e

    def xin(f):
        i, label, d = f
        if isinstance(d, list):
            return (f"<label class='field'><span>{e(label)}</span><select id='{i}'>" + "".join(f"<option value='{k}'>{e(t)}</option>" for k, t in d) + "</select></label>")
        return f"<label class='field'><span>{e(label)}</span><input type='number' inputmode='numeric' id='{i}' min='0' step='1000' value='{d}'></label>"

    x = ("<details class='card tx-g' open><summary><b>Advance tax</b></summary><div class='stack' style='gap:14px;margin-top:12px'>"
         + "".join(xin(f) for f in FIELDS_X) + "</div></details>")
    js = (JS.replace("__IDS__", json.dumps([f[0] for f in TP.FIELDS])).replace("__DUE__", json.dumps([[a, b, c] for a, b, c in DUE]))
          .replace("__FY__", FY).replace("__WA__", TP.WA))
    faq_html = "".join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
    path = "/income-tax/advance-tax-calculator/"
    title = f"Advance tax calculator FY {FY}: due dates, instalments and interest | Aeterna Wealth"
    desc = (f"Free advance tax calculator for tax year {FY}: your tax in either regime, the instalments due on 15 June, 15 September, "
            "15 December and 15 March, what to pay next, and the interest on late or missed instalments.")
    dates = "".join(f"<tr><td class='l'>{b}</td><td class='num'>{c}%</td></tr>" for _a, b, c in DUE)
    body = f"""{TP.CSS}<style>.ax-now td{{background:var(--teal-soft)}}#axTbl th,#axTbl td{{padding-left:8px;padding-right:8px}}.ax-tag{{font:500 11px var(--f-mono);text-transform:uppercase;letter-spacing:.06em;color:var(--teal);margin-left:6px}}</style>
<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/income-tax/">Income tax</a> › Advance tax calculator</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Advance tax calculator, tax year {FY}</h1>
<p class="lede" style="margin-top:12px">Your tax for the year, what is due at each instalment, what to pay next, and any interest for paying late. Enter your income below and what you have paid so far; leave the rest at zero.</p>
<div class="tool" id="axForm" style="margin-top:22px"><div class="stack" style="gap:12px">{x}{TP._form(B)}</div>
<div class="stack" id="txSide"><div class="out" id="axOut"></div><p id="axNote" style="font-size:14.5px"></p><div class="tablewrap" id="axTbl" tabindex="0"></div>
<div class="card" id="axInt" style="font-size:14.5px"></div>
<div class="card stack" style="gap:8px;border-color:var(--teal)"><b>Have a CA work out your instalments</b><span class="muted" style="font-size:14px">A chartered accountant estimates your year's income, including capital gains, and tells you what to pay and when.</span><a class="btn primary" id="axCA" href="{TP.WA}" target="_blank" rel="noopener">Ask on WhatsApp</a></div></div></div>
<noscript><p class="note">This calculator needs JavaScript; the rules below show the method.</p></noscript>
<h2 style="font-size:26px;margin-top:40px">Advance tax due dates, tax year {FY}</h2>
<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Pay by</th><th>Share of the year's tax, in total</th></tr></thead><tbody>{dates}</tbody></table></div>
<p style="margin-top:12px">If your business or profession is taxed on a presumptive basis, all of it is due by 15 March 2027. Residents aged 60 or more with no business or professional income do not pay advance tax.</p>
<h2 style="font-size:24px;margin-top:28px">How the calculator works</h2>
<ol style="margin-top:10px"><li>Your tax for the year in the regime you choose, worked out the same way as our <a href="/income-tax/calculator/">income tax calculator</a>: slabs, capital gains at their own rates, rebate, surcharge and cess.</li>
<li>TDS and TCS come off. If your employer deducts tax, the tax on your salary alone is counted as paid through TDS. If what is left is ₹10,000 or more, advance tax applies.</li>
<li>Each instalment is a share of that amount. What you have paid is compared with what was due by each date.</li>
<li>Interest is 1% a month on the shortfall, rounded down to the nearest ₹100: 3 months for each of the June, September and December instalments (none for June if 12% was paid, or September if 36%), 1 month for March. If less than 90% is paid by 31 March, 1% a month runs from April until the tax is paid.</li></ol>
<p class="muted" style="font-size:13px;margin-top:12px">Rules last checked {CHECKED}, under the Income-tax Act, 2025.</p>
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{faq_html}
<p style="margin-top:22px;font-size:14.5px">Related: <a href="/income-tax/calculator/">Income tax calculator</a> · <a href="/income-tax/slabs-fy-2026-27/">Tax slabs FY {FY}</a> · <a href="/income-tax/deductions/">Deductions</a> · <a href="/calculators/capital-gains-tax/">Capital gains tax calculator</a></p>
<p class="muted" style="font-size:12.5px;margin-top:22px">An estimate from the figures you enter, not tax advice.</p>
</div></section><script src="/assets/tax-engine.js?v={v}"></script><script>{js}</script>"""
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"Advance tax calculator FY {FY} by Aeterna Wealth", "url": B.SITE + path,
              "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "publisher": {"@id": B.SITE + "/#org"}, "description": desc}
    B.write(path, B.page(title, desc, path, body, (app_ld, faq_ld, B.crumbs([("Income tax", "/income-tax/"), ("Advance tax calculator", path)]))))
    urls.append((path, "weekly", "0.9"))
    return path
