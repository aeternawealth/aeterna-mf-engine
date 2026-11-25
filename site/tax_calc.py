"""Income tax, old vs new regime, with the ELSS (80C) saving. FY 2026-27 (AY 2027-28), resident individual under 60.

Rules checked 25 Nov 2026. Budget 2026 left the slabs unchanged; the Income-tax Act, 2025 replaced the 1961 Act from
1 April 2026 with the same rates and limits (the 80C investment deduction is section 123 of the new Act).
The same rules are written twice, in Python (worked example, tests) and in JavaScript (the live calculator);
tests/test_tax_calc.py checks that both give the same answers.
"""
TAX_CHECKED = "25 Nov 2026"
FY = "2026-27"

NEW = [(400000, 0), (800000, .05), (1200000, .10), (1600000, .15), (2000000, .20), (2400000, .25), (None, .30)]
OLD = [(250000, 0), (500000, .05), (1000000, .20), (None, .30)]
SUR = [(5e7, .37), (2e7, .25), (1e7, .15), (5e6, .10)]          # income above -> surcharge rate; new regime capped at 25%


def _slab(x, S):
    t, lo = 0.0, 0
    for hi, r in S:
        top = x if hi is None else min(x, hi)
        if top > lo:
            t += (top - lo) * r
        if hi is None or x <= hi:
            break
        lo = hi
    return t


def tax(income, regime, salaried=True, c80=0, d80=0, home=0, hra=0, nps=0, other=0):
    """Tax with cess on slab income. Returns (taxable income, tax)."""
    if regime == "new":
        ti = max(0, income - (75000 if salaried else 0))
        S, cap, reb = NEW, .25, 1200000
    else:
        ded = min(c80, 150000) + max(0, d80) + min(home, 200000) + max(0, hra) + min(nps, 50000) + max(0, other)
        ti = max(0, income - (50000 if salaried else 0) - ded)
        S, cap, reb = OLD, .37, 500000
    t = _slab(ti, S)
    if ti <= reb:
        t = 0
    elif regime == "new":
        t = min(t, ti - reb)                                      # marginal relief just above ₹12 lakh
    for th, r in SUR:
        if ti > th:
            r = min(r, cap)
            nxt = [x for x in SUR if x[0] < th]
            base = _slab(th, S) * (1 + (nxt[0][1] if nxt else 0))   # tax + surcharge at the threshold
            t = min(t * (1 + r), base + (ti - th))                  # marginal relief on surcharge
            break
    return ti, round(t * 1.04)


JS = r"""
const TX={NEW:[[4e5,0],[8e5,.05],[12e5,.10],[16e5,.15],[20e5,.20],[24e5,.25],[null,.30]],OLD:[[2.5e5,0],[5e5,.05],[10e5,.20],[null,.30]],SUR:[[5e7,.37],[2e7,.25],[1e7,.15],[5e6,.10]]};
function txSlab(x,S){let t=0,lo=0;for(const [hi,r] of S){const top=hi==null?x:Math.min(x,hi);if(top>lo)t+=(top-lo)*r;if(hi==null||x<=hi)break;lo=hi}return t}
function txTax(o,regime){let ti,S,cap,reb;
 if(regime==='new'){ti=Math.max(0,o.g-(o.sal?75000:0));S=TX.NEW;cap=.25;reb=12e5}
 else{const ded=Math.min(o.c,150000)+Math.max(0,o.d)+Math.min(o.h,200000)+Math.max(0,o.hra)+Math.min(o.n,50000)+Math.max(0,o.o);ti=Math.max(0,o.g-(o.sal?50000:0)-ded);S=TX.OLD;cap=.37;reb=5e5}
 let t=txSlab(ti,S);if(ti<=reb)t=0;else if(regime==='new')t=Math.min(t,ti-reb);
 for(let k=0;k<TX.SUR.length;k++){const [th,r0]=TX.SUR[k];if(ti>th){const r=Math.min(r0,cap),nx=TX.SUR[k+1],base=txSlab(th,S)*(1+(nx?nx[1]:0));t=Math.min(t*(1+r),base+(ti-th));break}}
 return {ti,tax:Math.round(t*1.04)}}
"""

RUN = r"""function run(){const o={g:val('g'),sal:$('#st').value==='1',c:val('c'),d:val('d'),h:val('h'),hra:val('hra'),n:val('n'),o:val('o')};
 const N=txTax(o,'new'),O=txTax(o,'old'),room=Math.max(0,150000-Math.min(o.c,150000)),O2=txTax({...o,c:150000},'old'),save=O.tax-O2.tax;
 const best=O2.tax<N.tax?'old':'new',diff=Math.abs(N.tax-O.tax);
 let txt=N.tax===O.tax?`Both regimes give the same tax: ${inr(N.tax)}.`:`The ${N.tax<O.tax?'new':'old'} regime is lower by ${inr(diff)} on your current deductions.`;
 txt+=room>0?(save>0?` Investing another ${inr(room)} in ELSS (filling your ₹1.5 lakh 80C limit) would cut old-regime tax by ${inr(save)}`+(O2.tax<N.tax?`, making the old regime the cheaper one by ${inr(N.tax-O2.tax)}.`:`, but the new regime would still be lower, by ${inr(O2.tax-N.tax)}: ELSS would then give no tax saving, only the fund's returns, with a 3-year lock-in.`):` Your old-regime income is already below the rebate limit, so more 80C investment saves no tax.`)
   :` Your ₹1.5 lakh 80C limit is already full, so more ELSS saves no further tax.`;
 const ys=[5,7.5,10,12,13,15,18,20,24,30,40,50].map(x=>x*1e5);
 out([['New regime tax',inr(N.tax)],['Old regime tax',inr(O.tax)],['ELSS top-up saves (old regime)',inr(save)]],txt,
  ['','New regime','Old regime'],[['Taxable income',inr(N.ti),inr(O.ti)],['Tax with 4% cess',inr(N.tax),inr(O.tax)],['Old regime with 80C full','–',inr(O2.tax)],['Monthly take-home after tax',inr((o.g-N.tax)/12),inr((o.g-O.tax)/12)]],
  {title:'Tax at different incomes, with your deductions',labels:ys.map(x=>'₹'+(x/1e5)+'L'),series:[{n:'New regime',c:'var(--teal)',v:ys.map(g=>txTax({...o,g},'new').tax)},{n:'Old regime',c:'var(--brass)',v:ys.map(g=>txTax({...o,g},'old').tax),dash:1}]})}"""


def entry(fld, sel):
    def be(g):
        n = tax(g, "new")[1]
        return n, next((D for D in range(0, 3000001, 5000) if tax(g, "old", True, 0, 0, 0, 0, 0, D)[1] <= n), None)
    rows = "".join(f"<tr><td class='l'>₹{g / 1e5:.0f} lakh</td><td class='num'>₹{n:,}</td><td class='num'>₹{D:,}</td></tr>"
                   for g in (1000000, 1200000, 1500000, 1800000, 2000000, 2500000, 3000000, 5000000) for n, D in [be(g)])
    return {"id": "income-tax-old-vs-new", "name": "Income tax: old vs new regime", "h1": f"Income tax calculator FY {FY}: old vs new regime, and what ELSS saves",
            "title": f"Income tax calculator FY {FY}: old vs new regime, 80C and ELSS saving | Aeterna Wealth",
            "desc": f"Free income tax calculator for FY {FY} (AY 2027-28): tax under the old and new regimes side by side, which is lower for you, and how much tax an ELSS investment under 80C actually saves.",
            "intro": "Enter your yearly income and the deductions you already claim. The calculator works out your tax under both regimes, shows which is lower, and what filling your ₹1.5 lakh 80C limit with ELSS would change.",
            "inputs": lambda: fld("g", "Yearly income before tax (₹)", 1500000, 100000, 50000000, 10000)
            + sel("st", "Salaried or pensioner?", [("1", "Yes: standard deduction applies"), ("0", "No: business or other income")], "1")
            + fld("c", "80C already used: EPF, PPF, insurance, principal, ELSS (₹)", 50000, 0, 150000, 5000)
            + fld("d", "80D health insurance premium (₹)", 25000, 0, 100000, 1000)
            + fld("h", "Home-loan interest, self-occupied (₹)", 0, 0, 200000, 5000)
            + fld("hra", "HRA exemption (₹)", 0, 0, 2000000, 5000)
            + fld("n", "Own NPS contribution, 80CCD(1B) (₹)", 0, 0, 50000, 5000)
            + fld("o", "Other old-regime deductions (₹)", 0, 0, 2000000, 5000),
            "js": JS + RUN,
            "how": (f"FY {FY} rules, for a resident individual under 60. <b>New regime</b> (the default): nil up to ₹4 lakh, then 5%, 10%, 15%, 20% and 25% for each ₹4 lakh band, "
                    "and 30% above ₹24 lakh; standard deduction ₹75,000 for salaried people and pensioners; a rebate makes tax nil up to ₹12 lakh of taxable income, with relief just above it; "
                    "almost no deductions. <b>Old regime</b>: nil up to ₹2.5 lakh, 5% to ₹5 lakh, 20% to ₹10 lakh, 30% above; standard deduction ₹50,000; nil tax up to ₹5 lakh of taxable income; "
                    "deductions allowed, including up to ₹1.5 lakh under 80C (section 123 of the Income-tax Act, 2025), which is where ELSS counts. "
                    "Surcharge applies above ₹50 lakh (10%), ₹1 crore (15%), ₹2 crore (25%) and, in the old regime only, ₹5 crore (37%), with marginal relief. "
                    "A 4% health and education cess is added. Capital gains taxed at special rates are not included. "
                    f"Rules last checked {TAX_CHECKED}."),
            "example": lambda: ("<p>How much the old regime's deductions (80C, 80D, home-loan interest, HRA, NPS and the rest, beyond the standard deduction) must add up to "
                                "before the old regime gives lower tax, for a salaried person in FY " + FY + ":</p><div class='tablewrap'><table><thead><tr><th class='l'>Salary</th>"
                                "<th>Tax, new regime</th><th>Deductions needed for the old regime to win</th></tr></thead><tbody>" + rows + "</tbody></table></div>"
                                "<p style='margin-top:10px'>80C (₹1.5 lakh), 80D for a family (₹25,000) and NPS (₹50,000) together come to ₹2.25 lakh, short of every break-even above. "
                                "The old regime, and with it the ELSS tax saving, pays mainly for people who also claim home-loan interest (up to ₹2 lakh) and a sizeable HRA exemption.</p>"),
            "faq": [("Does ELSS save tax under the new regime?", "No. The new regime allows no 80C deduction, so an ELSS fund is then an ordinary equity fund with a 3-year lock-in. It saves tax only if you file under the old regime."),
                    ("How much tax can ELSS save?", "Up to ₹1.5 lakh a year counts under 80C, shared with EPF, PPF, life insurance and home-loan principal. In the 30% slab that saves up to ₹46,800 with cess; in the 20% slab up to ₹31,200. If EPF already fills the limit, ELSS saves nothing more."),
                    ("Which regime is better for me?", "It depends on your deductions. At a ₹15 lakh salary the old regime wins only if deductions beyond the standard deduction exceed about ₹5.5 lakh; at ₹25 lakh and above, about ₹8 lakh. 80C, 80D and NPS alone reach ₹2.25 lakh, so the old regime usually needs home-loan interest and HRA as well. The calculator works out your own break-even."),
                    ("Can I switch between regimes every year?", "Salaried people can choose each year when filing the return. People with business income can switch back to the old regime only once."),
                    ("What is the last date to invest in ELSS for this year?", f"31 March 2027 for FY {FY}. Invest a few working days early: the units must be allotted by 31 March, and a SIP through the year avoids putting the whole amount in at one price.")]}
