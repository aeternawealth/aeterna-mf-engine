"""Aeterna Tax: /income-tax/ hub, the full calculator and the slab page (FY 2026-27).

The rules live once, in site/tax_engine.js (loaded by the calculator, run by tests/test_tax_engine.py with node).
The slab tables below are printed from the same numbers; the test checks they agree with the engine.
Section numbers are the 1961-Act ones people search for; the Income-tax Act, 2025 keeps the limits under new numbers.
"""
import json
import shutil
from pathlib import Path

FY, AY, CHECKED = "2026-27", "2027-28", "25 Nov 2026"
NEW = [(0, 4e5, 0), (4e5, 8e5, 5), (8e5, 12e5, 10), (12e5, 16e5, 15), (16e5, 20e5, 20), (20e5, 24e5, 25), (24e5, None, 30)]
OLD = {"Below 60": [(0, 2.5e5, 0), (2.5e5, 5e5, 5), (5e5, 10e5, 20), (10e5, None, 30)],
       "60 to 79 (senior citizen)": [(0, 3e5, 0), (3e5, 5e5, 5), (5e5, 10e5, 20), (10e5, None, 30)],
       "80 and above (super senior citizen)": [(0, 5e5, 0), (5e5, 10e5, 20), (10e5, None, 30)]}
WA = "https://wa.me/918595993600?text="

FIELDS = [  # id, label, group, default, hint
    ("age", "Your age on 31 March 2027", "You", "<60", [("<60", "Below 60"), ("60-79", "60 to 79"), ("80+", "80 or above")]),
    ("resident", "Residential status", "You", "1", [("1", "Resident in India"), ("0", "Non-resident (NRI)")]),
    ("salary", "Gross salary or pension, before any deduction", "Salary", 1500000, "Include allowances, bonus and taxable perquisites"),
    ("basic", "Basic pay + DA (for HRA and employer NPS)", "Salary", 600000, ""),
    ("hraRecd", "HRA received", "Salary", 0, ""),
    ("rent", "Rent you pay in a year", "Salary", 0, ""),
    ("metro", "You live in", "Salary", "0", [("0", "Other city"), ("1", "Delhi, Mumbai, Kolkata or Chennai")]),
    ("profTax", "Professional tax paid", "Salary", 2500, "Old regime only, up to ₹2,500"),
    ("employerNPS", "Employer's contribution to your NPS", "Salary", 0, "Allowed in both regimes: 14% of basic + DA in the new, 10% in the old"),
    ("selfInterest", "Home-loan interest, home you live in", "House property", 0, "Old regime only, up to ₹2 lakh"),
    ("letRent", "Rent received from a let-out property", "House property", 0, ""),
    ("municipal", "Municipal tax paid on it", "House property", 0, ""),
    ("letInterest", "Home-loan interest on the let-out property", "House property", 0, ""),
    ("business", "Business or professional income (net profit)", "Other income", 0, "For presumptive 44ADA, enter 50% of receipts"),
    ("interestSav", "Savings account interest", "Other income", 10000, ""),
    ("interestFD", "FD, RD and bond interest", "Other income", 0, ""),
    ("dividends", "Dividends", "Other income", 0, ""),
    ("otherIncome", "Other income (gifts above ₹50,000, family pension and the like)", "Other income", 0, ""),
    ("stcg111A", "Short-term gains: equity funds and listed shares (held 12 months or less)", "Capital gains", 0, "Taxed at 20%"),
    ("ltcg112A", "Long-term gains: equity funds and listed shares (held over 12 months)", "Capital gains", 0, "12.5% above ₹1.25 lakh"),
    ("ltcgOther", "Long-term gains: property, gold, unlisted shares, bonds", "Capital gains", 0, "12.5%, without indexation"),
    ("stcgSlab", "Short-term gains taxed at your slab: debt funds, property, gold", "Capital gains", 0, ""),
    ("vda", "Crypto and other virtual digital assets (gain)", "Capital gains", 0, "Flat 30%, no losses set off"),
    ("lottery", "Lottery, game-show and online-game winnings", "Capital gains", 0, "Flat 30%"),
    ("c80", "80C: EPF, PPF, ELSS, life insurance, home-loan principal, school fees", "Deductions (old regime)", 150000, "Up to ₹1.5 lakh"),
    ("nps1b", "Your own NPS contribution, 80CCD(1B)", "Deductions (old regime)", 0, "Up to ₹50,000, over and above 80C"),
    ("d80self", "Health insurance for self, spouse, children, 80D", "Deductions (old regime)", 25000, "Up to ₹25,000 (₹50,000 if you are a senior)"),
    ("d80parents", "Health insurance for parents, 80D", "Deductions (old regime)", 0, ""),
    ("parentsSenior", "Parents' age", "Deductions (old regime)", "1", [("1", "60 or above (limit ₹50,000)"), ("0", "Below 60 (limit ₹25,000)")]),
    ("e80", "Education-loan interest, 80E", "Deductions (old regime)", 0, "No upper limit"),
    ("g80", "Donations, 80G (eligible amount after the 50% or 100% rule)", "Deductions (old regime)", 0, ""),
    ("u80", "Disability, 80U or 80DD", "Deductions (old regime)", 0, "₹75,000, or ₹1.25 lakh for severe disability"),
    ("otherDed", "Other deductions", "Deductions (old regime)", 0, ""),
]


def _inp(B, f):
    i, label, _g, d, h = f
    if isinstance(h, list):
        return (f"<label class='field'><span>{B.e(label)}</span><select id='{i}'>"
                + "".join(f"<option value='{k}'{' selected' if k == d else ''}>{B.e(t)}</option>" for k, t in h) + "</select></label>")
    return (f"<label class='field'><span>{B.e(label)}</span><input type='number' inputmode='numeric' id='{i}' min='0' step='1000' value='{d}'>"
            + (f"<small class='muted' style='font-size:12.5px'>{B.e(h)}</small>" if h else "") + "</label>")


def _form(B):
    groups, out = [], []
    for f in FIELDS:
        if f[2] not in groups:
            groups.append(f[2])
    for k, g in enumerate(groups):
        out.append(f"<details class='card tx-g'{' open' if k < 2 else ''}><summary><b>{B.e(g)}</b></summary><div class='stack' style='gap:14px;margin-top:12px'>"
                   + "".join(_inp(B, f) for f in FIELDS if f[2] == g) + "</div></details>")
    return "".join(out)


def _slab_rows(S):
    def L(x):
        return "₹" + (f"{x / 1e5:g} lakh" if x else "0")
    return "".join(f"<tr><td class='l'>{L(lo)} to {L(hi)}</td><td class='num'>{r}%</td></tr>" if hi else
                   f"<tr><td class='l'>Above {L(lo)}</td><td class='num'>{r}%</td></tr>" for lo, hi, r in S)


def slab_tables():
    t = ("<h3 style='font-size:20px;margin-top:22px'>New regime (the default), every age</h3><div class='tablewrap'><table><thead><tr><th class='l'>Taxable income</th><th>Rate</th></tr></thead><tbody>"
         + _slab_rows(NEW) + "</tbody></table></div>")
    for k, S in OLD.items():
        t += (f"<h3 style='font-size:20px;margin-top:22px'>Old regime, age {k}</h3><div class='tablewrap'><table><thead><tr><th class='l'>Taxable income</th><th>Rate</th></tr></thead><tbody>"
              + _slab_rows(S) + "</tbody></table></div>")
    return t


COMMON = [
    ("Rebate", "New regime: no tax if taxable income is up to ₹12 lakh (rebate up to ₹60,000), with relief just above it. Old regime: no tax up to ₹5 lakh (rebate up to ₹12,500). Residents only. In the new regime the rebate does not cover tax on capital gains at special rates."),
    ("Standard deduction", "₹75,000 in the new regime, ₹50,000 in the old, for salaried people and pensioners."),
    ("Surcharge", "10% of the tax above ₹50 lakh of income, 15% above ₹1 crore, 25% above ₹2 crore, and 37% above ₹5 crore in the old regime only (the new regime stops at 25%). On capital gains and dividends it never exceeds 15%. Marginal relief applies at each step."),
    ("Cess", "4% health and education cess on the tax and surcharge."),
    ("Capital gains", "Equity funds and listed shares: 20% short term, 12.5% long term above ₹1.25 lakh a year. Other long-term gains: 12.5% without indexation. Debt funds bought from April 2023: your slab rate."),
]

FAQ = [
    ("Which tax regime is better for me in FY 2026-27?", "The new regime is lower for most people because of its wider slabs and the ₹12 lakh rebate. The old regime wins only with large deductions: at a ₹15 lakh salary, more than about ₹5.5 lakh beyond the standard deduction; at ₹25 lakh and above, about ₹8 lakh. The calculator compares both for your own numbers."),
    ("Is income up to ₹12 lakh tax-free?", "In the new regime, yes, for residents with taxable income up to ₹12 lakh, through the rebate. For salaried people that means a salary up to ₹12.75 lakh after the ₹75,000 standard deduction. Capital gains taxed at special rates are not covered by the rebate."),
    ("What deductions are allowed in the new regime?", "The standard deduction (₹75,000), your employer's NPS contribution (up to 14% of basic and DA), and deductions within house property for a let-out home. 80C, 80D, HRA and home-loan interest on a self-occupied home are not allowed."),
    ("Do senior citizens get a higher exemption?", "Only in the old regime: ₹3 lakh at 60 to 79 and ₹5 lakh at 80 and above, for residents. The new regime has one set of slabs for every age. Seniors also get a ₹50,000 deduction for deposit interest under 80TTB and a ₹50,000 health insurance limit under 80D in the old regime."),
    ("How are NRIs taxed?", "On income earned or received in India, at the same slabs. NRIs do not get the rebate, the higher exemption for seniors, 80TTB, or the use of the unused basic exemption against capital gains."),
    ("What changed with the Income-tax Act, 2025?", "It replaced the 1961 Act from 1 April 2026. It keeps the rates and limits, renumbers the sections, and replaces the old 'previous year' and 'assessment year' with a single tax year: tax year 2026-27 is 1 April 2026 to 31 March 2027, what used to be FY 2026-27 / AY 2027-28. Returns for it are due by 31 July 2027 for most individuals."),
    ("What is not included in this calculator?", "Agricultural income, HUFs, firms and companies, alternative minimum tax, foreign tax credits, clubbing of income, set-off of brought-forward losses and some rare deductions. If any apply to you, have a CA check the result."),
    ("When is the last date to save tax for FY 2026-27?", "31 March 2027 for investments and payments that count (80C, 80D, NPS). The return is due by 31 July 2027 for most individuals, and advance tax instalments fall on 15 June, 15 September, 15 December and 15 March."),
]

RUN_JS = r"""
const $=s=>document.querySelector(s),inr=v=>(v<0?'− ':'')+'₹'+Math.round(Math.abs(v||0)).toLocaleString('en-IN');
const IDS=__IDS__;
function read(){const p={};for(const i of IDS){const el=$('#'+i);if(!el)continue;p[i]=el.tagName==='SELECT'?el.value:+el.value||0}
 p.resident=p.resident!=='0';p.metro=p.metro==='1';p.parentsSenior=p.parentsSenior==='1';return p}
function row(k,a,b,cls){return `<tr${cls?` class="${cls}"`:''}><td class="l">${k}</td><td class="num">${a}</td><td class="num">${b}</td></tr>`}
function run(){const p=read(),{N,O,best,saving}=txBoth(p);
 $('#txOut').innerHTML=`<div><span>New regime</span><b>${inr(N.payable)}</b></div><div><span>Old regime</span><b>${inr(O.payable)}</b></div><div><span>${saving?'Lower: '+(best==='new'?'new':'old')+' regime':'Same either way'}</span><b>${saving?'saves '+inr(saving):'–'}</b></div>`;
 const R=[['Gross income',inr(N.gross),inr(O.gross)],['Standard deduction',inr(N.std),inr(O.std)],['HRA exemption','–',inr(O.hra)],['House property income (loss)',inr(N.hp),inr(O.hp)],
  ['Deductions',inr(N.ded),inr(O.ded)],['Taxable income at slab rates',inr(N.normal),inr(O.normal)],['Income at special rates (capital gains, crypto)',inr(N.special),inr(O.special)],
  ['Tax at slab rates',inr(N.tN),inr(O.tN)],['Tax at special rates',inr(N.tSpecial),inr(O.tSpecial)],['Rebate',N.reb?'− '+inr(N.reb):'–',O.reb?'− '+inr(O.reb):'–'],
  ['Surcharge',inr(N.sur),inr(O.sur)],['Cess, 4%',inr(N.cess),inr(O.cess)],['Tax payable',inr(N.payable),inr(O.payable)],
  ['Tax as a share of taxable income',(N.eff*100).toFixed(1)+'%',(O.eff*100).toFixed(1)+'%'],['Tax a month',inr(N.payable/12),inr(O.payable/12)]];
 $('#txTbl').innerHTML=`<table><thead><tr><th class="l">FY __FY__</th><th>New regime</th><th>Old regime</th></tr></thead><tbody>${R.map((r,i)=>row(...r,i===12?'tx-tot':'')).join('')}</tbody></table>`;
 $('#txDed').innerHTML=O.D.length?'<b>Old-regime deductions counted:</b> '+O.D.map(([k,v])=>`${k} ${inr(v)}`).join(' · '):'';
 // what could lower the tax
 const T=[],room=Math.max(0,150000-Math.min(p.c80,150000));
 if(room>0){const O2=txCompute({...p,c80:150000},'old'),s=O.payable-O2.payable;
  if(s>0)T.push(O2.payable<N.payable?`Filling 80C with another ${inr(room)} (for example in an <a href="/mutual-funds/elss/">ELSS fund</a>) would cut old-regime tax by ${inr(s)} and make the old regime the lower one.`:`Another ${inr(room)} in 80C would cut old-regime tax by ${inr(s)}, but the new regime would still be lower, so it would save you nothing.`)}
 if(!p.nps1b){const O3=txCompute({...p,nps1b:50000},'old'),s=O.payable-O3.payable;if(s>0&&O3.payable<N.payable)T.push(`₹50,000 in NPS under 80CCD(1B) would save ${inr(s)} in the old regime.`)}
 if(p.salary>0&&!p.employerNPS&&p.basic>0){const k=Math.round(.14*p.basic),N4=txCompute({...p,employerNPS:k},'new'),s=N.payable-N4.payable;if(s>0)T.push(`If your employer offers NPS, routing ${inr(k)} of your pay into it (14% of basic + DA) would save ${inr(s)} in the new regime too.`)}
 if(p.ltcg112A<125000)T.push(`You can book ${inr(125000-p.ltcg112A)} more of long-term gains on equity funds this year tax-free, by selling and buying back before 31 March. <a href="/learn/capital-gains-tax-on-mutual-funds/">How it works</a>.`);
 $('#txTips').innerHTML=T.length?'<h3 style="font-size:19px">Ways to pay less</h3><ul style="margin-top:8px">'+T.map(t=>`<li style="margin-top:6px">${t}</li>`).join('')+'</ul>':'';
 const msg=encodeURIComponent(`Hi, I used the Aeterna tax calculator (FY __FY__): new regime ${inr(N.payable)}, old regime ${inr(O.payable)}. I would like a CA to check my tax.`);
 $('#txCA').href='__WA__'+msg}
document.querySelectorAll('#txForm input,#txForm select').forEach(el=>el.addEventListener('input',run));run();
"""

CSS = """<style>.tx-g summary{cursor:pointer;list-style:none;font-size:16px}.tx-g summary::-webkit-details-marker{display:none}.tx-g summary::after{content:'＋';float:right;color:var(--ink-3)}
.tx-g[open] summary::after{content:'−'}.tx-tot td{font-weight:600;border-top:2px solid var(--ink-3)}#txSide{position:sticky;top:84px}@media(max-width:900px){#txSide{position:static}}</style>"""


def tax_pages(B, urls):
    S = Path(__file__).resolve().parent
    eng = (S / "tax_engine.js").read_text(encoding="utf-8")
    import hashlib
    v = hashlib.sha1(eng.encode()).hexdigest()[:10]
    (B.DIST / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(S / "tax_engine.js", B.DIST / "assets" / "tax-engine.js")
    e = B.e
    faq_html = "".join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in FAQ)
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ]}
    rules = "".join(f"<li style='margin-top:8px'><b>{e(k)}.</b> {e(t)}</li>" for k, t in COMMON)
    js = RUN_JS.replace("__IDS__", json.dumps([f[0] for f in FIELDS])).replace("__FY__", FY).replace("__WA__", WA)

    # ---------------------------------------------------------------- the calculator
    path = "/income-tax/calculator/"
    title = f"Income tax calculator tax year {FY} (FY {FY}): old vs new regime | Aeterna Wealth"
    desc = (f"Free income tax calculator for tax year {FY} under the Income-tax Act, 2025: salary, HRA, house property, business, "
            "capital gains, crypto, every deduction, rebate, surcharge and cess, for residents, NRIs and senior citizens, old and new regime side by side.")
    body = f"""{CSS}<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/income-tax/">Income tax</a> › Calculator</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Income tax calculator, tax year {FY}: old vs new regime</h1>
<p class="lede" style="margin-top:12px">Your tax for tax year {FY} (1 April 2026 to 31 March 2027) under the Income-tax Act, 2025, in both regimes, for any individual: salaried or self-employed, resident or NRI, any age. Fill in what applies; leave the rest at zero.</p>
<div class="tool" id="txForm" style="margin-top:22px"><div class="stack" style="gap:12px">{_form(B)}</div>
<div class="stack" id="txSide"><div class="out" id="txOut"></div><div class="tablewrap" id="txTbl" tabindex="0"></div>
<p class="muted" id="txDed" style="font-size:13px"></p><div class="card" id="txTips"></div>
<div class="card stack" style="gap:8px;border-color:var(--teal)"><b>Have a CA check this before you file</b><span class="muted" style="font-size:14px">A chartered accountant reviews your regime choice, deductions and capital gains, and can file your return.</span><a class="btn primary" id="txCA" href="{WA}" target="_blank" rel="noopener">Ask on WhatsApp</a></div></div></div>
<noscript><p class="note">This calculator needs JavaScript; the rules below show the method.</p></noscript>
<h2 style="font-size:26px;margin-top:40px">How your tax is worked out</h2>
<ol style="margin-top:10px"><li>Income under each head: salary (after the standard deduction, and HRA and professional tax in the old regime), house property, business, capital gains and other sources.</li>
<li>Deductions come off income taxed at slab rates (most of them in the old regime only). They never reduce capital gains taxed at special rates.</li>
<li>Slab income is taxed at the regime's slab rates; capital gains, crypto and winnings at their own flat rates. Residents whose slab income is below the exemption limit use the unused part against equity capital gains.</li>
<li>The rebate, then surcharge with marginal relief, then the 4% cess.</li></ol>
<h2 style="font-size:24px;margin-top:28px">FY {FY} slab rates</h2>{slab_tables()}
<h2 style="font-size:24px;margin-top:28px">Rebate, surcharge, cess and capital gains</h2><ul style="margin-top:6px">{rules}</ul>
<p class="muted" style="font-size:13px;margin-top:12px">Rules last checked {CHECKED}, under the Income-tax Act, 2025. Deductions are shown by their familiar names (80C, 80D and so on); the new section numbers will be added from the tax department's official mapping.</p>
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{faq_html}
<p style="margin-top:22px;font-size:14.5px">Related: <a href="/income-tax/deductions/">Every deduction explained</a> · <a href="/income-tax/slabs-fy-2026-27/">Tax slabs FY {FY}</a> · <a href="/calculators/income-tax-old-vs-new/">What ELSS saves you</a> · <a href="/calculators/capital-gains-tax/">Capital gains tax calculator</a> · <a href="/learn/elss-tax-saving-mutual-funds/">ELSS explained</a></p>
<p class="muted" style="font-size:12.5px;margin-top:22px">An estimate from the figures you enter, not tax advice. Have a CA check your return before you file.</p>
</div></section><script src="/assets/tax-engine.js?v={v}"></script><script>{js}</script>"""
    app_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"Income tax calculator FY {FY} by Aeterna Wealth", "url": B.SITE + path,
              "applicationCategory": "FinanceApplication", "operatingSystem": "Any", "isAccessibleForFree": True,
              "offers": {"@type": "Offer", "price": "0", "priceCurrency": "INR"}, "publisher": {"@id": B.SITE + "/#org"}, "description": desc}
    B.write(path, B.page(title, desc, path, body, (app_ld, faq_ld, B.crumbs([("Income tax", "/income-tax/"), ("Calculator", path)]))))
    urls.append((path, "weekly", "0.9"))

    import tax_deductions as TD
    TD.deduction_pages(B, urls, {}, v)

    # ---------------------------------------------------------------- slabs
    sp = "/income-tax/slabs-fy-2026-27/"
    sfaq = FAQ[1:2] + FAQ[3:6]
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/income-tax/">Income tax</a> › Slabs FY {FY}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Income tax slabs, tax year {FY}: new and old regime</h1>
<p class="lede" style="margin-top:12px">Budget 2026 left the slabs unchanged. In the new regime, the default, income up to ₹12 lakh is tax-free for residents through the rebate (₹12.75 lakh of salary after the standard deduction). The old regime keeps its slabs and its deductions.</p>
<p style="margin-top:16px"><a class="btn primary" href="{path}">Work out your tax in both regimes</a></p>
{slab_tables()}
<h2 style="font-size:24px;margin-top:28px">Rebate, surcharge, cess and capital gains</h2><ul style="margin-top:6px">{rules}</ul>
<p class="muted" style="font-size:13px;margin-top:12px">Rules last checked {CHECKED}.</p>
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{''.join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in sfaq)}
</div></section>"""
    sld = {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in sfaq]}
    B.write(sp, B.page(f"Income tax slabs FY {FY} (tax year {FY}): new and old regime, senior citizens | Aeterna Wealth",
                       f"Income tax slab rates for tax year {FY} under the Income-tax Act, 2025: new regime, old regime for below 60, senior and super senior citizens, the ₹12 lakh rebate, surcharge, cess and capital gains rates.",
                       sp, body, (sld, B.crumbs([("Income tax", "/income-tax/"), (f"Slabs FY {FY}", sp)]))))
    urls.append((sp, "monthly", "0.8"))

    # ---------------------------------------------------------------- hub
    cards = [(path, "Income tax calculator", "Both regimes, every individual: salary, HRA, house property, capital gains, crypto, all deductions."),
             (sp, f"Tax slabs FY {FY}", "New and old regime rates for every age, rebate, surcharge and cess."),
             ("/income-tax/deductions/", "Deductions and exemptions", "80C, 80D, HRA, NPS, home-loan interest, 87A and more: limits, regime, a calculator each."),
             ("/calculators/income-tax-old-vs-new/", "Old vs new regime, quick check", "Your income and deductions in, the lower regime and what ELSS saves you out."),
             ("/calculators/capital-gains-tax/", "Capital gains tax calculator", "Equity and debt funds, bonds and unlisted shares."),
             ("/learn/capital-gains-tax-on-mutual-funds/", "Tax on mutual fund gains", "Short and long term, equity and debt, SIPs and switches."),
             ("/learn/elss-tax-saving-mutual-funds/", "ELSS and 80C", "The tax saving, the 3-year lock-in, and when it is worth it.")]
    dates = [("15 December 2026", "Third advance tax instalment (75% of the year's tax paid by now)"), ("15 March 2027", "Last advance tax instalment (100%)"),
             ("31 March 2027", f"Last day for FY {FY} tax-saving investments and payments"), ("31 July 2027", f"Return due for FY {FY}, for individuals without a tax audit"),
             ("31 December 2027", "Last day for a belated or revised return for FY " + FY)]
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<h1 style="font-size:clamp(30px,4vw,44px)">Income tax for individuals, tax year {FY}</h1>
<p class="lede" style="margin-top:12px">Calculators and plain guides for the first year under the Income-tax Act, 2025: which regime to choose, what you can deduct, how capital gains are taxed, and when to pay and file.</p>
<div class="grid g3" style="margin-top:26px">{''.join(f"<a class='card stack sol' href='{u}' style='gap:6px;text-decoration:none;color:inherit'><b style='font:500 18px var(--f-display)'>{e(n)}</b><span class='muted' style='font-size:14px'>{e(d)}</span></a>" for u, n, d in cards)}</div>
<h2 style="font-size:26px;margin-top:40px">Key dates</h2><div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Date</th><th class="l">What</th></tr></thead><tbody>{''.join(f"<tr><td class='l'>{d}</td><td class='l'>{e(w)}</td></tr>" for d, w in dates)}</tbody></table></div>
<p class="muted" style="font-size:13px;margin-top:8px">Under current rules, checked {CHECKED}. The tax department can extend a due date; we update this page when it does.</p>
<div class="card stack" style="gap:8px;margin-top:30px;border-color:var(--teal)"><b>Tax planning and return filing, with a CA</b><span class="muted" style="font-size:14px">A chartered accountant reviews your regime, deductions and capital gains, and can file your return.</span><a class="btn primary" href="{WA}{'Hi%2C%20I%20would%20like%20help%20with%20my%20income%20tax.'}" target="_blank" rel="noopener" style="justify-self:start">Ask on WhatsApp</a></div>
</div></section>"""
    B.write("/income-tax/", B.page(f"Income tax FY {FY}: calculator, slabs, deductions and due dates | Aeterna Wealth",
                                   f"Income tax for individuals in tax year {FY}, under the Income-tax Act, 2025: a full old vs new regime calculator, slab rates, deductions, capital gains and the key dates for paying and filing.",
                                   "/income-tax/", body, (B.crumbs([("Income tax", "/income-tax/")]),)))
    urls.append(("/income-tax/", "weekly", "0.9"))
