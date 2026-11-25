"""Aeterna Tax: one page per deduction, exemption or rebate (/income-tax/deductions/<slug>/), FY 2026-27.

Each entry: the old (1961 Act) section people search for, the rules, a small calculator and FAQs. `NEWSEC` holds the
Income-tax Act, 2025 section numbers from the official mapping (site/tax_sections.py); a page shows a new number only
when that mapping has it. Limits checked 25 Nov 2026.
"""
import json

CHECKED = "25 Nov 2026"
WA = "https://wa.me/918595993600?text="

# calc kinds: "cap" = amount up to a limit x your slab; "hra"; "rebate"; "gg" (80GG)
D = [
    dict(slug="section-80c", sec="80C", name="Section 80C deduction", short="80C: EPF, PPF, ELSS, insurance and more", limit=150000, calc="cap",
         lead="Up to ₹1.5 lakh a year of specified investments and payments comes off your taxable income, in the old tax regime only. In the 30% slab that saves up to ₹46,800 with cess.",
         who="Individuals and HUFs filing under the old regime.",
         rules=["Limit: ₹1.5 lakh a year in total, shared with 80CCC (pension plans) and your own NPS contribution under 80CCD(1). This combined cap is section 80CCE.",
                "EPF (your own share) and voluntary PF (VPF).",
                "PPF, Sukanya Samriddhi, National Savings Certificates, and 5-year tax-saving bank FDs.",
                "ELSS mutual funds: the shortest lock-in of the 80C options, 3 years for each instalment.",
                "Life insurance premiums for yourself, your spouse or your children. For policies issued from April 2012, only premiums up to 10% of the sum assured count.",
                "Senior Citizens' Savings Scheme deposits.",
                "Principal repaid on a home loan, plus stamp duty and registration in the year you buy.",
                "Tuition fees for up to two children, at a school, college or university in India.",
                "Not allowed in the new regime."],
         faq=[("Can I claim 80C in the new regime?", "No. The new regime allows the standard deduction and your employer's NPS contribution, but not 80C."),
              ("Does EPF count towards 80C?", "Yes, your own contribution. For many salaried people, EPF alone fills a large part of the ₹1.5 lakh, so check your payslip before investing more."),
              ("What is the best 80C investment?", "It depends on how long you can lock money away and how much risk you take. ELSS has the shortest lock-in (3 years) and is invested in shares; PPF is a 15-year government scheme with a set interest rate."),
              ("Is the 80C limit ₹1.5 lakh per person?", "Yes, per taxpayer per year. Spouses each have their own limit, so a couple filing separately can claim up to ₹3 lakh between them.")],
         links=[("/mutual-funds/elss/", "Every ELSS fund compared"), ("/calculators/income-tax-old-vs-new/", "What 80C saves you, old vs new regime"), ("/learn/elss-tax-saving-mutual-funds/", "ELSS explained")]),
    dict(slug="section-80ccd-1b", sec="80CCD(1B)", name="Section 80CCD(1B): extra ₹50,000 for NPS", short="80CCD(1B): your own NPS, over and above 80C", limit=50000, calc="cap",
         lead="Up to ₹50,000 a year that you put into NPS Tier I comes off taxable income, on top of the ₹1.5 lakh under 80C, in the old regime only.",
         who="Any individual, salaried or self-employed, with an NPS Tier I account, filing under the old regime.",
         rules=["Limit: ₹50,000 a year, separate from the ₹1.5 lakh 80C limit.", "Only NPS Tier I contributions count; Tier II does not, except a special Tier II for government employees.",
                "NPS money is mostly locked until 60: at retirement up to 60% can be withdrawn tax-free, and the rest buys an annuity whose income is taxed.",
                "Not allowed in the new regime. Your employer's contribution (80CCD(2)) is a separate deduction allowed in both."],
         faq=[("Can I claim both 80C and 80CCD(1B)?", "Yes. 80CCD(1B) is an extra ₹50,000 over the ₹1.5 lakh 80C limit, so the total can reach ₹2 lakh in the old regime."),
              ("Is 80CCD(1B) available in the new regime?", "No. Only the employer's NPS contribution, under 80CCD(2), is allowed in the new regime.")],
         links=[("/income-tax/deductions/section-80ccd-2/", "Employer NPS, 80CCD(2)"), ("/income-tax/deductions/section-80c/", "80C")]),
    dict(slug="section-80ccd-2", sec="80CCD(2)", name="Section 80CCD(2): employer's NPS contribution", short="80CCD(2): employer NPS, allowed in both regimes", limit=None, calc="emp",
         lead="What your employer pays into your NPS account is deductible up to 14% of your basic pay and DA in the new regime, and 10% in the old (14% for government employees). It is one of the few deductions the new regime allows.",
         who="Salaried employees whose employer contributes to NPS on their behalf.",
         rules=["New regime: up to 14% of basic + DA, for all employees.", "Old regime: up to 10% of basic + DA for private-sector employees, 14% for central and state government employees.",
                "Not counted in the ₹1.5 lakh 80C limit.", "Employer contributions to NPS, EPF and superannuation together above ₹7.5 lakh a year are taxed as a perquisite.",
                "Usually arranged by restructuring your CTC: part of the pay goes to NPS instead of your salary account."],
         faq=[("Does 80CCD(2) work in the new regime?", "Yes, up to 14% of basic + DA. For someone with ₹6 lakh basic in the 30% slab, ₹84,000 into NPS saves about ₹26,000 a year."),
              ("Can I ask my employer for NPS?", "Many employers offer it as a choice in the salary structure; ask HR whether you can route part of your CTC into corporate NPS.")],
         links=[("/income-tax/calculator/", "See the effect in the full calculator")]),
    dict(slug="section-80d", sec="80D", name="Section 80D: health insurance deduction", short="80D: health insurance for you and your parents", limit=None, calc="80d",
         lead="Health insurance premiums are deductible up to ₹25,000 for yourself, your spouse and children (₹50,000 if you are 60 or over) and another ₹25,000 for your parents (₹50,000 if they are 60 or over), in the old regime only.",
         who="Individuals and HUFs filing under the old regime.",
         rules=["Self, spouse and dependent children: ₹25,000; ₹50,000 if you are a senior citizen.", "Parents: a further ₹25,000; ₹50,000 if either parent is a senior citizen.",
                "Maximum ₹1 lakh when you and your parents are all seniors.", "Preventive health check-ups up to ₹5,000 count, within these limits, and may be paid in cash.",
                "Premiums must be paid by any mode other than cash.", "Senior citizens with no health insurance can claim medical expenses within the ₹50,000 limit.",
                "A multi-year policy paid upfront is spread evenly over its years.", "Not allowed in the new regime."],
         faq=[("Can I claim my parents' health insurance under 80D?", "Yes, up to ₹25,000, or ₹50,000 if either parent is 60 or above, even if they are not dependent on you."),
              ("Is GST on the premium included?", "Yes, the deduction is on the premium you pay, including GST."),
              ("Is 80D allowed in the new regime?", "No.")],
         links=[("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="hra-exemption", sec="10(13A)", name="HRA exemption", short="HRA: how much of your house rent allowance is tax-free", limit=None, calc="hra",
         lead="The tax-free part of your HRA is the least of three amounts: the HRA you receive, rent paid minus 10% of basic + DA, and 50% of basic + DA in Delhi, Mumbai, Kolkata or Chennai (40% elsewhere). It applies in the old regime only.",
         who="Salaried employees who receive HRA and pay rent for the home they live in, filing under the old regime.",
         rules=["Exempt HRA = the least of: HRA received; rent paid − 10% of salary; 50% of salary (metro) or 40% (other cities). Salary here means basic + DA (if it counts for retirement benefits) + commission based on turnover.",
                "You must actually pay rent; paying rent to a parent is allowed if they own the home and declare the rent as income.",
                "Give your employer the landlord's PAN if rent is above ₹1 lakh a year.", "No HRA exemption in the new regime.",
                "If you get no HRA, see section 80GG instead."],
         faq=[("Can I claim HRA and a home-loan deduction together?", "Yes, if you live in a rented home and own another (for example in another city, or let out)."),
              ("Is HRA exempt in the new regime?", "No. HRA is fully taxable in the new regime.")],
         links=[("/income-tax/deductions/section-80gg/", "No HRA? Section 80GG"), ("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="section-24b-home-loan-interest", sec="24(b)", name="Section 24(b): home-loan interest deduction", short="24(b): home-loan interest", limit=200000, calc="cap",
         lead="Interest on a home loan for the home you live in is deductible up to ₹2 lakh a year in the old regime. For a let-out home, all the interest is deductible against its rent in both regimes, but the old regime caps the loss set off against other income at ₹2 lakh, and the new regime allows no such set-off.",
         who="Owners repaying a home loan.",
         rules=["Self-occupied home: up to ₹2 lakh a year (old regime only). The construction must be finished within 5 years of the end of the year the loan was taken, or the limit falls to ₹30,000.",
                "Let-out home: interest is deducted from the rent with no cap; a loss beyond ₹2 lakh is carried forward for 8 years (old regime).",
                "Interest paid before the construction was finished is deducted in five equal parts from the year it is completed, within the same limits.",
                "Principal repayments go under 80C, not 24(b).", "New regime: no deduction for a self-occupied home; for a let-out home, interest comes off its rent only."],
         faq=[("Can I claim home-loan interest in the new regime?", "Only for a let-out property, against its rent. Not for the home you live in."),
              ("Can both co-borrowers claim?", "Yes, each co-owner who is also a co-borrower can claim up to ₹2 lakh for a self-occupied home, in proportion to their share.")],
         links=[("/calculators/home-loan-prepayment/", "Prepay the loan or invest?"), ("/calculators/emi/", "EMI calculator")]),
    dict(slug="section-80e", sec="80E", name="Section 80E: education-loan interest", short="80E: education-loan interest, no upper limit", limit=None, calc="cap",
         lead="All the interest paid on a loan for higher education is deductible, with no upper limit, for up to 8 years, in the old regime.",
         who="An individual who took the loan for their own, their spouse's or their children's higher education, or a student they are the legal guardian of.",
         rules=["No limit on the amount; only interest counts, not the principal.", "For the year you start repaying and the next 7 years, or until the interest is paid off, whichever is earlier.",
                "The loan must come from a bank, a financial institution or an approved charitable institution; loans from relatives or employers do not count.",
                "Courses in India or abroad qualify.", "Not allowed in the new regime."],
         faq=[("Is there a limit under 80E?", "No upper limit on the interest, but only for 8 years."), ("Can parents claim 80E?", "Yes, if the loan is in the parent's name for their child's higher education.")],
         links=[("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="section-80g", sec="80G", name="Section 80G: donations to charity", short="80G: donations", limit=None, calc="cap",
         lead="Donations to approved funds and charities are deductible at 100% or 50% of the amount, some with a cap of 10% of adjusted income, in the old regime only.",
         who="Any taxpayer filing under the old regime who donates to an eligible fund or institution.",
         rules=["Four kinds: 100% with no limit (e.g. PM National Relief Fund), 50% with no limit (e.g. PM Drought Relief Fund), 100% within the 10% limit, and 50% within the 10% limit (most registered charities).",
                "The 10% limit is on gross total income less other deductions and income taxed at special rates.",
                "Cash donations above ₹2,000 do not qualify.", "The charity reports your donation to the tax department; your deduction is checked against its Form 10BE certificate.",
                "Not allowed in the new regime."],
         faq=[("Can I claim 80G on a cash donation?", "Only up to ₹2,000 in cash. Larger donations must be by cheque, card or bank transfer.")],
         links=[("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="section-80gg", sec="80GG", name="Section 80GG: rent paid without HRA", short="80GG: rent if you get no HRA", limit=60000, calc="gg",
         lead="If you pay rent but receive no HRA, for example as a self-employed person, you can deduct up to ₹60,000 a year (₹5,000 a month) under 80GG in the old regime.",
         who="Individuals who get no HRA, and who (and whose spouse, minor child or HUF) own no home in the city where they live or work.",
         rules=["Deduction = the least of: ₹5,000 a month; 25% of total income; rent paid − 10% of total income. Total income here is before this deduction.",
                "File Form 10BA, a declaration, with your return.", "Not allowed in the new regime."],
         faq=[("Who can claim 80GG?", "Anyone paying rent who receives no HRA and owns no home in the place they live or work."),
              ("What is the maximum under 80GG?", "₹60,000 a year.")],
         links=[("/income-tax/deductions/hra-exemption/", "HRA exemption")]),
    dict(slug="section-80tta", sec="80TTA", name="Section 80TTA: savings account interest", short="80TTA: ₹10,000 of savings interest", limit=10000, calc="cap",
         lead="Up to ₹10,000 of interest on savings accounts (bank, co-operative bank or post office) is deductible in the old regime, for taxpayers below 60.",
         who="Individuals below 60 and HUFs, residents and non-residents, under the old regime. Senior citizens use 80TTB instead.",
         rules=["Savings-account interest only; FD and RD interest do not count.", "NRIs can claim it on NRO savings accounts.", "Not allowed in the new regime."],
         faq=[("Does 80TTA cover FD interest?", "No, only savings-account interest. For senior citizens, 80TTB covers FDs too.")],
         links=[("/income-tax/deductions/section-80ttb/", "80TTB for senior citizens")]),
    dict(slug="section-80ttb", sec="80TTB", name="Section 80TTB: interest income of senior citizens", short="80TTB: ₹50,000 of deposit interest for seniors", limit=50000, calc="cap",
         lead="Resident senior citizens can deduct up to ₹50,000 a year of interest on savings accounts, fixed and recurring deposits, in the old regime.",
         who="Resident individuals aged 60 or over, filing under the old regime.",
         rules=["Covers interest from banks, co-operative banks and post office deposits, savings and fixed.", "Interest on corporate deposits and bonds does not count.",
                "A senior citizen claiming 80TTB cannot claim 80TTA.", "Not allowed in the new regime, and not available to NRIs."],
         faq=[("Is 80TTB available to NRIs?", "No, only to resident senior citizens.")],
         links=[("/income-tax/deductions/section-80tta/", "80TTA"), ("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="section-80u", sec="80U", name="Section 80U: person with a disability", short="80U: ₹75,000 or ₹1.25 lakh for disability", limit=None, calc="dis",
         lead="A resident with a disability certified by a medical authority can deduct a flat ₹75,000, or ₹1.25 lakh for a severe disability (80% or more), in the old regime.",
         who="Resident individuals with a disability of 40% or more.",
         rules=["Flat deduction, whatever is actually spent.", "Disability of 40% or more: ₹75,000; severe disability (80% or more): ₹1.25 lakh.",
                "A certificate from a specified medical authority is needed (Form 10-IA for some conditions).", "Not allowed in the new regime."],
         faq=[("Do I need to show expenses for 80U?", "No. It is a flat deduction based on the certificate.")],
         links=[("/income-tax/deductions/section-80dd/", "80DD for a dependant with a disability")]),
    dict(slug="section-80dd", sec="80DD", name="Section 80DD: dependant with a disability", short="80DD: care of a dependant with a disability", limit=None, calc="dis",
         lead="A resident who supports a dependant with a disability can deduct a flat ₹75,000, or ₹1.25 lakh for a severe disability, in the old regime.",
         who="Resident individuals and HUFs who look after a dependent spouse, child, parent, brother or sister with a disability.",
         rules=["Flat ₹75,000 (40% or more disability) or ₹1.25 lakh (80% or more), whatever is spent on treatment, training and care, or paid into an approved insurance scheme for the dependant.",
                "Not allowed if the dependant claims 80U themselves.", "A medical certificate is needed.", "Not allowed in the new regime."],
         faq=[("Can both 80U and 80DD be claimed for the same person?", "No. If the person with the disability claims 80U, nobody can claim 80DD for them.")],
         links=[("/income-tax/deductions/section-80u/", "80U")]),
    dict(slug="section-80ddb", sec="80DDB", name="Section 80DDB: treatment of specified diseases", short="80DDB: treatment of serious illnesses", limit=40000, calc="cap",
         lead="What you spend on treating specified serious illnesses (such as cancer, neurological diseases, chronic renal failure) for yourself or a dependant is deductible up to ₹40,000, or ₹1 lakh for a senior citizen, in the old regime.",
         who="Resident individuals and HUFs.",
         rules=["Limit: ₹40,000; ₹1 lakh if the patient is 60 or over.", "Reduced by any amount reimbursed by insurance or the employer.",
                "A prescription from a specialist is needed.", "Not allowed in the new regime."],
         faq=[("Which diseases are covered under 80DDB?", "Those listed in the rules: certain neurological diseases (with 40% disability or more), malignant cancers, full-blown AIDS, chronic renal failure and some blood disorders.")],
         links=[("/income-tax/deductions/section-80d/", "80D health insurance")]),
    dict(slug="standard-deduction", sec="16(ia)", name="Standard deduction for salaried people", short="Standard deduction: ₹75,000 (new) or ₹50,000 (old)", limit=None, calc="std",
         lead="Every salaried employee and pensioner gets a flat ₹75,000 off salary in the new regime and ₹50,000 in the old, with no proof needed.",
         who="Salaried employees and pensioners. Family pension has its own deduction (the lower of one-third of it or ₹25,000 in the new regime, ₹15,000 in the old).",
         rules=["New regime: ₹75,000.", "Old regime: ₹50,000.", "Limited to your salary if it is lower.", "Applied automatically by your employer when deducting tax at source."],
         faq=[("Is the standard deduction available to pensioners?", "Yes, on pension from a former employer, which is taxed as salary.")],
         links=[("/income-tax/calculator/", "Full income tax calculator")]),
    dict(slug="section-87a-rebate", sec="87A", name="Section 87A rebate", short="87A rebate: nil tax up to ₹12 lakh (new) or ₹5 lakh (old)", limit=None, calc="rebate",
         lead="Residents pay no income tax if taxable income is up to ₹12 lakh in the new regime (rebate up to ₹60,000) or up to ₹5 lakh in the old (up to ₹12,500). For salaried people, that is a salary up to ₹12.75 lakh in the new regime.",
         who="Resident individuals. Not available to NRIs, HUFs or companies.",
         rules=["New regime: total income up to ₹12 lakh, rebate up to ₹60,000. Just above ₹12 lakh, marginal relief limits the tax to the income above ₹12 lakh.",
                "In the new regime the rebate does not cover tax on capital gains taxed at special rates (equity gains under 111A and 112A) or on winnings.",
                "Old regime: total income up to ₹5 lakh, rebate up to ₹12,500.", "The threshold is on total income, after deductions, including capital gains."],
         faq=[("Is income up to ₹12 lakh tax-free?", "In the new regime, yes, for residents, except tax on capital gains at special rates."),
              ("Is the rebate available to NRIs?", "No."),
              ("What is marginal relief?", "Someone earning slightly over ₹12 lakh would pay more tax than the extra income without it. Relief caps the tax at the amount by which income exceeds ₹12 lakh.")],
         links=[("/income-tax/slabs-fy-2026-27/", "Tax slabs FY 2026-27"), ("/income-tax/calculator/", "Full income tax calculator")]),
]


def calc_html(d):
    k = d["calc"]
    F = lambda i, l, v: f"<label class='field'><span>{l}</span><input type='number' inputmode='numeric' id='{i}' min='0' step='1000' value='{v}'></label>"
    slab = ("<label class='field'><span>Your top tax slab (old regime)</span><select id='sl'><option value='5'>5%</option><option value='20'>20%</option>"
            "<option value='30' selected>30%</option></select></label>")
    if k == "cap":
        return F("a", f"Amount you invest or pay in the year (₹)", d["limit"] or 100000) + slab
    if k == "80d":
        return (F("a", "Premium for self, spouse, children (₹)", 25000) + "<label class='field'><span>Are you 60 or over?</span><select id='s1'><option value='0'>No</option><option value='1'>Yes</option></select></label>"
                + F("b", "Premium for parents (₹)", 30000) + "<label class='field'><span>Is either parent 60 or over?</span><select id='s2'><option value='1'>Yes</option><option value='0'>No</option></select></label>" + slab)
    if k == "hra":
        return (F("bs", "Basic + DA a year (₹)", 600000) + F("h", "HRA received a year (₹)", 240000) + F("r", "Rent paid a year (₹)", 300000)
                + "<label class='field'><span>City</span><select id='m'><option value='1'>Delhi, Mumbai, Kolkata or Chennai</option><option value='0'>Other city</option></select></label>" + slab)
    if k == "gg":
        return F("ti", "Total income before this deduction (₹)", 800000) + F("r", "Rent paid a year (₹)", 180000) + slab
    if k == "emp":
        return F("bs", "Basic + DA a year (₹)", 600000) + "<label class='field'><span>Your top tax slab</span><select id='sl'><option value='10'>10%</option><option value='15'>15%</option><option value='20'>20%</option><option value='25'>25%</option><option value='30' selected>30%</option></select></label>"
    if k == "dis":
        return "<label class='field'><span>Disability</span><select id='dv'><option value='75000'>40% to 79%</option><option value='125000'>80% or more (severe)</option></select></label>" + slab
    if k == "std":
        return F("a", "Salary or pension a year (₹)", 1000000)
    if k == "rebate":
        return F("ti", "Total taxable income, after deductions (₹)", 1200000)
    return ""


CALC_JS = r"""
const $=s=>document.querySelector(s),v=i=>+($('#'+i)?.value||0),inr=x=>'₹'+Math.round(x).toLocaleString('en-IN'),sl=()=>v('sl')/100;
function show(a,b){$('#dOut').innerHTML=a.map(([k,x])=>`<div><span>${k}</span><b>${x}</b></div>`).join('');$('#dTxt').textContent=b||''}
const K={
cap:L=>{const d=L?Math.min(v('a'),L):v('a');show([['Deduction',inr(d)],['Tax saved, approx.',inr(d*sl()*1.04)]],L&&v('a')>L?`Only ${inr(L)} counts; the rest gives no deduction.`:'At your top slab, with 4% cess, in the old regime.')},
'80d':()=>{const a=Math.min(v('a'),$('#s1').value==='1'?50000:25000),b=Math.min(v('b'),$('#s2').value==='1'?50000:25000);show([['Self and family',inr(a)],['Parents',inr(b)],['Tax saved, approx.',inr((a+b)*sl()*1.04)]],'Old regime, at your top slab, with 4% cess.')},
hra:()=>{const s=v('bs'),x=Math.max(0,Math.min(v('h'),v('r')-.1*s,($('#m').value==='1'?.5:.4)*s));show([['Tax-free HRA',inr(x)],['Taxable HRA',inr(Math.max(0,v('h')-x))],['Tax saved, approx.',inr(x*sl()*1.04)]],'The least of: HRA received, rent minus 10% of basic + DA, and 50% (metro) or 40% of basic + DA.')},
gg:()=>{const t=v('ti'),x=Math.max(0,Math.min(60000,.25*t,v('r')-.1*t));show([['Deduction',inr(x)],['Tax saved, approx.',inr(x*sl()*1.04)]],'The least of ₹60,000, 25% of total income, and rent minus 10% of total income.')},
emp:()=>{const n=.14*v('bs'),o=.10*v('bs');show([['New regime limit (14%)',inr(n)],['Old regime limit (10%, private sector)',inr(o)],['Tax saved, new regime, approx.',inr(n*sl()*1.04)]],'If your employer routes that much of your pay into NPS.')},
dis:()=>{const x=v('dv');show([['Deduction',inr(x)],['Tax saved, approx.',inr(x*sl()*1.04)]],'Flat amount, old regime.')},
std:()=>{const s=v('a');show([['New regime',inr(Math.min(s,75000))],['Old regime',inr(Math.min(s,50000))]],'')},
rebate:()=>{const t=v('ti'),N=txSlabTax(t,TAXRULES.newSlabs),O=txSlabTax(t,TAXRULES.oldSlabs['<60']);
 const rn=t<=12e5?Math.min(N,60000):Math.max(0,N-(t-12e5)),ro=t<=5e5?Math.min(O,12500):0;
 show([['New regime: rebate',inr(rn)],['New regime: tax',inr((N-rn)*1.04)],['Old regime: tax',inr((O-ro)*1.04)]],t<=12e5?'Within ₹12 lakh: no tax in the new regime (resident, no special-rate gains).':(rn?'Marginal relief applies: tax limited to the income above ₹12 lakh.':''))}};
const run=()=>K[__KIND__](__LIMIT__);document.querySelectorAll('#dCalc input,#dCalc select').forEach(e=>e.addEventListener('input',run));run();
"""


def deduction_pages(B, urls, newsec=None, eng_v=""):
    newsec = newsec or {}
    e = B.e
    cards = []
    for d in D:
        path = f"/income-tax/deductions/{d['slug']}/"
        ns = newsec.get(d["sec"])
        nsl = f" It is section {ns} of the Income-tax Act, 2025." if ns else ""
        title = f"{d['name']} FY 2026-27: limit, rules, old vs new regime | Aeterna Wealth"
        desc = (d["lead"][:150].rsplit(" ", 1)[0] + "…") if len(d["lead"]) > 155 else d["lead"]
        faq = d["faq"] + ([("What is the new section number under the Income-tax Act, 2025?", f"Section {ns}. The Income-tax Act, 2025 replaced the 1961 Act from 1 April 2026 and keeps the same limit under the new number; most people and many forms still call it {d['sec']}.")] if ns else [])
        js = CALC_JS.replace("__KIND__", json.dumps(d["calc"])).replace("__LIMIT__", json.dumps(d["limit"]))
        rel = " · ".join(f"<a href='{u}'>{e(t)}</a>" for u, t in d["links"])
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/income-tax/">Income tax</a> › <a href="/income-tax/deductions/">Deductions</a> › {e(d['sec'])}</nav>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:14px">{e(d['name'])}</h1>
<p class="lede" style="margin-top:12px">{e(d['lead'])}{e(nsl)}</p>
<div class="tool" id="dCalc" style="margin-top:22px"><div class="card stack">{calc_html(d)}</div><div class="stack"><div class="out" id="dOut"></div><div class="card"><p id="dTxt" style="font-size:14.5px"></p></div></div></div>
<h2 style="font-size:24px;margin-top:36px">Who can claim it</h2><p style="margin-top:8px">{e(d['who'])}</p>
<h2 style="font-size:24px;margin-top:28px">The rules for FY 2026-27</h2><ul style="margin-top:8px">{''.join(f"<li style='margin-top:8px'>{e(r)}</li>" for r in d['rules'])}</ul>
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{''.join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)}
<div class="card stack" style="gap:8px;margin-top:28px;border-color:var(--teal)"><b>Not sure what you can claim?</b><span class="muted" style="font-size:14px">A chartered accountant can review your deductions and regime before you file.</span><a class="btn primary" style="justify-self:start" href="{WA}{'Hi%2C%20I%20have%20a%20question%20about%20' + d['sec'].replace('(', '%28').replace(')', '%29')}" target="_blank" rel="noopener">Ask on WhatsApp</a></div>
<p style="margin-top:22px;font-size:14.5px">Related: {rel} · <a href="/income-tax/deductions/">All deductions</a> · <a href="/income-tax/calculator/">Full tax calculator</a></p>
<p class="muted" style="font-size:12.5px;margin-top:18px">Rules last checked {CHECKED}. Section numbers are those of the Income-tax Act, 1961, the names most people still use. An estimate, not tax advice.</p>
</div></section>{'<script src="/assets/tax-engine.js?v=' + eng_v + '"></script>' if d['calc'] == 'rebate' else ''}<script>{js}</script>"""
        ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        B.write(path, B.page(title, desc, path, body, (ld, B.crumbs([("Income tax", "/income-tax/"), ("Deductions", "/income-tax/deductions/"), (d["sec"], path)]))))
        urls.append((path, "monthly", "0.7"))
        cards.append((path, d, ns))
    hasn = any(ns for _, _, ns in cards)
    rows = "".join(f"<tr><td class='l'><a href='{p}'>{e(d['sec'])}</a></td>" + (f"<td class='l'>{e(ns or '–')}</td>" if hasn else "") + f"<td class='l'>{e(d['short'].split(': ', 1)[-1])}</td>"
                   f"<td class='l'>{'Both' if d['slug'] in ('section-80ccd-2', 'standard-deduction', 'section-87a-rebate') else 'Old only'}</td></tr>" for p, d, ns in cards)
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/income-tax/">Income tax</a> › Deductions</nav>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:14px">Income tax deductions and exemptions, FY 2026-27</h1>
<p class="lede" style="margin-top:12px">Every common deduction for individuals, with its limit, which regime allows it and a small calculator. The new regime allows only three of them: the standard deduction, your employer's NPS contribution and the rebate.</p>
<div class="tablewrap" style="margin-top:20px"><table><thead><tr><th class="l">Section (1961 Act)</th>{'<th class="l">Income-tax Act, 2025</th>' if hasn else ''}<th class="l">What it covers</th><th class="l">Regime</th></tr></thead><tbody>{rows}</tbody></table></div>
<p style="margin-top:18px"><a class="btn primary" href="/income-tax/calculator/">Work out your tax with all of them</a></p>
</div></section>"""
    B.write("/income-tax/deductions/", B.page("Income tax deductions FY 2026-27: 80C, 80D, HRA, NPS, 24(b), 87A and more | Aeterna Wealth",
                                              "Every income tax deduction and exemption for individuals in FY 2026-27: limits, old vs new regime, with a calculator for each.",
                                              "/income-tax/deductions/", body, (B.crumbs([("Income tax", "/income-tax/"), ("Deductions", "/income-tax/deductions/")]),)))
    urls.append(("/income-tax/deductions/", "monthly", "0.8"))
