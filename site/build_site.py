"""Builds the public website into site/dist/ (standard library only, so Cloudflare Pages can run it).

    python3 site/build_site.py

- index.html: the interactive app (site/app.html) with full <head> SEO: title, description, canonical,
  share preview, structured data (organisation, website search), analytics hooks
- /mutual-funds/                      every category, with links
- /mutual-funds/<category>/            category page: what SEBI requires, all funds (Regular and Direct), FAQ
- /mutual-funds/<category>/<fund>/     one page per fund plan (1,687): rating, returns vs index, risk, holdings
- sitemap.xml, robots.txt, llms.txt, llms-full.txt, data/funds.csv, 404.html, assets/site.css, og.png
- data/*.json copied for the app

Until launch (site/LAUNCHED absent) every page carries noindex and robots.txt disallows everything, so the
*.pages.dev preview stays out of search results. Analytics IDs live in site/site_config.json.
"""
import csv
import html
import json
import sys
import re
import shutil
from datetime import date
from pathlib import Path

S = Path(__file__).resolve().parent
DIST = S / "dist"
SITE = "https://aeternawealth.com"
CFG = json.loads((S / "site_config.json").read_text()) if (S / "site_config.json").exists() else {}
LAUNCHED = (S / "LAUNCHED").exists()
SOCIAL = CFG.get("social", [])
def aum_label(f):
    """'AUM on 30 Oct 2026' (AMFI month end) or 'Average AUM, Jul–Sep 2026' (quarterly fallback)."""
    a = str(f.get("aum_asof") or "")
    if not a or a == "nan":
        return "AUM"
    return f"Average AUM, {a.replace(' average', '')}" if "average" in a else f"AUM on {a}"


INDEXNOW_KEY = "8f3c2a9e5b7d41c6a0e4f9b2d6c8a1e3"   # public by design: IndexNow verifies ownership by fetching /<key>.txt
ORG = {
    "name": "Aeterna Wealth Private Limited", "brand": "Aeterna Wealth", "arn": "ARN-317889",
    "phone": "+91-85959-93600", "email": "contact@aeternawealth.com",
    "street": "B-5/7, 2nd Floor, Safdarjung Enclave, Africa Avenue Marg", "city": "New Delhi", "pin": "110029",
}
CAT_INFO = {   # what SEBI's categorisation (Oct 2017 circular, multi cap revised 2020) requires
    "Large Cap": "invest at least 80% in large-cap stocks (the 100 largest listed companies by market value)",
    "Mid Cap": "invest at least 65% in mid-cap stocks (companies ranked 101 to 250 by market value)",
    "Small Cap": "invest at least 65% in small-cap stocks (companies ranked 251 and below)",
    "Large & Mid Cap": "invest at least 35% each in large-cap and mid-cap stocks",
    "Multi Cap": "invest at least 25% each in large-cap, mid-cap and small-cap stocks",
    "Flexi Cap": "invest at least 65% in equities, across large, mid and small caps in any mix",
    "Focused": "hold at most 30 stocks, with at least 65% in equities",
    "ELSS": "invest at least 80% in equities, with a three-year lock-in and a tax deduction under the old tax regime",
    "Value / Contra": "follow a value or contrarian strategy, with at least 65% in equities",
    "Dividend Yield": "invest at least 65% in dividend-yielding stocks",
    "Sectoral/Thematic": "invest at least 80% in one sector or theme, such as banking, technology or infrastructure",
    "Index Fund": "track an index such as the Nifty 50 as closely and cheaply as possible",
    "Arbitrage": "invest at least 65% in equities hedged with derivatives, earning the price gap between the cash and futures markets",
    "Aggressive Hybrid": "invest 65% to 80% in equities and the rest in debt",
    "Balanced Advantage": "move between equity and debt as they see fit (dynamic asset allocation), often hedging part of their equity",
    "Equity Savings": "invest at least 65% in equities, much of it hedged with arbitrage, at least 10% in debt",
    "Multi Asset Allocation": "invest at least 10% in each of three asset classes, usually equity, debt and gold",
    "Balanced Hybrid": "invest 40% to 60% in equities and the rest in debt, without arbitrage",
    "Conservative Hybrid": "invest 10% to 25% in equities and 75% to 90% in debt",
    "Overnight": "lend only overnight, in securities maturing the next business day",
    "Liquid": "hold debt and money market securities maturing within about three months",
    "Money Market": "hold money market instruments (treasury bills, certificates of deposit, commercial paper) maturing within a year",
    "Ultra Short Term": "keep the portfolio's duration short, roughly three to six months",
    "Ultra Short to Short Term": "keep the portfolio's duration between ultra short and short, roughly six months to a year (formerly low duration funds)",
    "Short Term": "keep the portfolio's duration at roughly one to three years",
    "Medium Term": "keep the portfolio's duration at roughly three to four years",
    "Medium to Long Term": "keep the portfolio's duration at roughly four to seven years",
    "Long Term": "keep the portfolio's duration above about seven years",
    "Dynamic Term": "change the portfolio's duration freely as their view on interest rates changes",
    "Corporate Bond": "invest at least 80% in the highest-rated corporate bonds (AA+ and above)",
    "Credit Risk": "invest at least 65% in bonds rated below the highest grades, for extra yield",
    "Banking & PSU": "invest at least 80% in bonds of banks, public sector undertakings and public financial institutions",
    "Gilt": "invest at least 80% in government securities, which carry no credit risk",
    "Gilt 10-Year Constant Maturity": "invest at least 80% in government securities, keeping the portfolio's duration near ten years",
    "Floating Rate": "invest mostly in bonds whose interest rate resets with market rates",
    "Debt Sectoral": "lend mainly to one sector, such as financial services (a category new in 2026)",
}
CAT_PITCH = {   # what the category is for, in plain words
    "Large Cap": "The steadiest part of an equity portfolio: India's 100 largest companies. Beating the index here is hard, so cost and a fund's record against the Nifty 100 matter most, and for many investors a low-cost index fund does the job.",
    "Mid Cap": "Companies ranked 101 to 250: more room to grow than large caps, and deeper falls along the way. Suits money you will not need for seven years or more. Funds differ widely here, so the choice of fund matters more than in large caps.",
    "Small Cap": "India's smaller listed companies: the highest long-run return potential and the sharpest falls; drops of 30 to 50% have happened. Best built up slowly, for ten-year money, in a fund that can still buy and sell its stocks easily.",
    "Large & Mid Cap": "At least 35% each in large and mid caps: a middle path between the stability of large companies and the growth of mid-sized ones.",
    "Multi Cap": "At least 25% each in large, mid and small caps, so the fund cannot drift into one size of company. A ready-made spread across the market.",
    "Flexi Cap": "The manager can move freely between large, mid and small companies. One good flexi cap fund can be the core of an equity portfolio; the risk is a manager whose style drifts with fashion.",
    "Focused": "At most 30 stocks: high conviction, so results depend heavily on the manager's picks, for better and worse.",
    "ELSS": "Tax-saving equity funds. The three-year lock-in also helps: it is hard to panic-sell in a fall.",
    "Value / Contra": "Funds that buy out-of-favour companies. They can lag for years and then catch up quickly, so they reward patience.",
    "Dividend Yield": "Mostly companies that pay high dividends, which has often made them steadier in falls.",
    "Sectoral/Thematic": "One sector or theme, such as banking, pharma or technology. These show the widest spread of results of any category: a theme can lag for years. Most investors keep them to a small slice.",
    "Index Fund": "Funds that follow an index at low cost. Between funds on the same index, the choice comes down to cost and how closely each one tracks it.",
    "Aggressive Hybrid": "Mostly equity with a debt cushion: a gentler ride than a pure equity fund for five-year-plus money, rebalanced for you. Taxed as equity.",
    "Balanced Advantage": "The fund decides how much equity to hold, buying more when markets are cheap and less when they are expensive. The test is whether it really falls less than the market, which is what we measure.",
    "Equity Savings": "A little equity, a lot of arbitrage and some debt: modest returns with small swings, taxed as equity. Often a better fit than an FD for three-year money in the higher tax slabs.",
    "Multi Asset Allocation": "Equity, debt and gold in one fund, rebalanced for you. Gold tends to rise when equities fall, which steadies the ride. Most of these funds are young, so many are not rated yet.",
    "Balanced Hybrid": "Equity and debt in roughly equal parts, without arbitrage. Only a few funds exist in this category.",
    "Conservative Hybrid": "Mostly debt with a small equity kicker, for investors who want a little more than a debt fund and can accept small falls. Taxed like a debt fund, at your slab rate.",
    "Overnight": "The safest place to park money for a few days: almost no interest-rate or credit risk, and returns close to the RBI's overnight rate. Funds differ mainly in cost.",
    "Liquid": "Where most people keep their emergency fund and short-term cash: returns close to short-term rates, withdrawals usually the next working day. Funds differ in cost and in how careful they are with credit.",
    "Money Market": "A step up from liquid funds for money needed in three months to a year, with slightly higher returns and still very small swings.",
    "Ultra Short Term": "For money needed in three to twelve months. A little more return than a liquid fund; a fund that reaches for yield with weaker bonds can stumble, which is what our credit check looks for.",
    "Ultra Short to Short Term": "For money needed in six months to about a year and a half: still steady, with slightly more interest-rate risk than ultra short funds.",
    "Short Term": "For money needed in one to three years. Rate rises cause small dips; most of the return comes from the interest earned.",
    "Medium Term": "Three-to-four-year duration: more swing when interest rates move. Suits money needed in three years or more.",
    "Medium to Long Term": "Four-to-seven-year duration: noticeable gains when rates fall and dips when they rise.",
    "Long Term": "Long bonds: the most sensitive to interest rates. A bet on rates falling as much as a place to hold money.",
    "Dynamic Term": "The manager decides the duration. Results depend on calling interest rates right, so the spread between funds is wide.",
    "Corporate Bond": "High-quality company bonds: a little more than gilts, with low credit risk. A common core holding for money needed in two years or more.",
    "Credit Risk": "Bonds of lower-rated companies for extra yield. Defaults have hit these funds before; we flag any fund whose NAV has had a sharp one-day fall well below its category, with the date. Most investors keep them small, if at all.",
    "Banking & PSU": "Bonds of banks and government-owned companies: high quality and steady, similar to corporate bond funds.",
    "Gilt": "Government bonds: no credit risk, but prices move with interest rates, sometimes sharply.",
    "Gilt 10-Year Constant Maturity": "Government bonds held near a ten-year duration: a pure interest-rate fund with no credit risk.",
    "Floating Rate": "Bonds whose interest resets with market rates, which softens the impact of rate rises.",
    "Debt Sectoral": "Debt from one sector, such as financial services. A new category, so most funds are too young to rate.",
    "Arbitrage": "A low-risk place to park money for a few months or more. Each stock bought is matched by a futures sale, so returns track short-term interest rates rather than the stock market. Before tax they usually earn a little less than liquid funds; they are taxed as equity, so after tax they often come out ahead for investors in the higher slabs.",
}
ASSET_CLASSES = [   # the three master categories, in site order
    ("Equity", "Funds that own shares: the long-term growth part of a portfolio."),
    ("Hybrid", "Funds that mix equity, debt and gold, or hedge their equity: from aggressive hybrid to arbitrage. Each is measured against a composite of the Nifty 50 and bond or liquid funds in its own proportions."),
    ("Debt", "Funds that lend: from overnight and liquid funds to corporate bond, gilt and credit risk funds. There is no free debt index, so each fund is measured against the median fund of its own category, with a check for any sharp one-day fall well below its category."),
]
HYBRID_CATS = {"Arbitrage", "Aggressive Hybrid", "Balanced Advantage", "Equity Savings", "Multi Asset Allocation", "Balanced Hybrid", "Conservative Hybrid"}
DEBT_CATS = set(['Overnight', 'Liquid', 'Money Market', 'Ultra Short Term', 'Ultra Short to Short Term', 'Short Term', 'Medium Term', 'Medium to Long Term', 'Long Term', 'Dynamic Term', 'Corporate Bond', 'Credit Risk', 'Banking & PSU', 'Gilt', 'Gilt 10-Year Constant Maturity', 'Floating Rate', 'Debt Sectoral'])
def asset_class(c):
    return "Hybrid" if c in HYBRID_CATS else "Debt" if c in DEBT_CATS else "Equity"
# tax assumptions for the after-tax comparison with liquid funds (same as engine/config.py)
TAX_SLAB_TOP, TAX_EQUITY_LTCG = 0.312, 0.13
TAX_TEXT = {"equity": "Taxed as an equity fund: gains on units held over a year at 12.5% beyond ₹1.25 lakh a year; within a year, 20%.",
            "other": "Taxed as a non-equity, non-debt fund: gains on units held over two years at 12.5%; within two years, at your slab rate.",
            "debt": "Taxed at your income-tax slab rate on all gains, however long you hold (more than 65% of the fund is in debt)."}

RET_RANK = {}   # (code, period) -> (rank by return over the index, funds ranked)
RH = {}   # rating history per scheme code, from outputs/latest/rating_history.json (written by the monthly run)
RH_JS = r"""function rhDraw(el){const H=JSON.parse(el.dataset.h),T=['A+','A','B','C','Unrated'],Y={'A+':26,'A':62,'B':98,'C':134,'Unrated':168},CL={'A+':'var(--t-ap)','A':'var(--t-a)','B':'var(--t-b)','C':'var(--t-c)','Unrated':'var(--t-u)'};
 const W=el.clientWidth<560?420:760,L=W<500?66:70,R=14,n=H.length,x=i=>L+(n>1?i/(n-1):.5)*(W-L-R),mo=m=>{const[a,b]=m.split('-');return new Date(+a,+b-1,1).toLocaleDateString('en-IN',{month:'short',year:'2-digit'})};
 let d='';H.forEach((h,i)=>{d+=(i?`H${x(i).toFixed(1)}V${Y[h[1]]}`:`M${x(0).toFixed(1)} ${Y[h[1]]}`)});
 const ticks=[0,Math.round((n-1)/2),n-1].filter((v,i,a)=>a.indexOf(v)===i);
 el.innerHTML=`<svg viewBox="0 0 ${W} 196" role="img" aria-label="Rating each month, ${mo(H[0][0])} to ${mo(H[n-1][0])}">${T.map(t=>`<line x1="${L}" x2="${W-R}" y1="${Y[t]}" y2="${Y[t]}" stroke="var(--rule)"/><text x="${L-8}" y="${Y[t]+4}" text-anchor="end" font-size="12.5" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${t}</text>`).join('')}
 ${H.map((h,i)=>h[6]==='after a fall'?`<rect x="${(x(i)-(W-L-R)/Math.max(1,n-1)/2).toFixed(1)}" y="12" width="${((W-L-R)/Math.max(1,n-1)).toFixed(1)}" height="166" fill="var(--brass)" opacity=".18"/>`:'').join('')}
 <path class="rh-line" pathLength="1" d="${d}" fill="none" stroke="var(--teal)" stroke-width="2" stroke-linejoin="round"/>
 ${H.map((h,i)=>`<circle class="rh-dot${h[5]?' ch':''}" cx="${x(i).toFixed(1)}" cy="${Y[h[1]]}" r="${h[5]?6:4}" fill="${CL[h[1]]}" stroke="var(--surface)" stroke-width="1.5" style="--d:${300+i*25}ms"/>`).join('')}
 ${ticks.map(i=>`<text x="${x(i)}" y="190" text-anchor="${i===0?'start':i===n-1?'end':'middle'}" font-size="12" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${mo(H[i][0])}</text>`).join('')}
 <line id="rhG" y1="14" y2="176" stroke="var(--ink-3)" stroke-dasharray="3 3" visibility="hidden"/><rect id="rhHit" x="${L-10}" y="0" width="${W-L-R+20}" height="196" fill="transparent"/></svg><div class="rh-tip" id="rhTip" aria-live="polite"></div>`;
 const tip=document.getElementById('rhTip'),g=document.getElementById('rhG'),hit=document.getElementById('rhHit');
 if(H.some(h=>h[6]==='after a fall'))el.insertAdjacentHTML('beforeend','<p class="muted" style="font-size:12.5px;margin-top:6px;display:flex;gap:8px;align-items:center"><span style="display:inline-block;width:14px;height:12px;background:var(--brass);opacity:.35;border-radius:2px"></span>Shaded months: after-a-fall mode. The category\'s index was below its 200-day average, so half the score came from the after-a-fall criteria.</p>');
 const show=i=>{const h=H[i];tip.innerHTML=`<b>${mo(h[0])}</b> <span class="tier-dot" style="background:${CL[h[1]]}"></span>${h[1]==='Unrated'?'Not rated':'Rated '+h[1]+' ('+({'A+':'Leading','A':'Strong','B':'In line','C':'Lagging','Watch':'Under review'}[h[1]]||'')+')'}${h[2]?` · ${h[2]} of ${h[3]} in its group`:''}${h[6]==='after a fall'?' · after-a-fall mode':''}${h[5]?`<span class="rh-why">${h[5]}</span>`:''}`;g.setAttribute('x1',x(i));g.setAttribute('x2',x(i));g.setAttribute('visibility','visible')};
 const at=e=>{const r=hit.getBoundingClientRect();return Math.max(0,Math.min(n-1,Math.round(((e.clientX-r.left)/r.width*(W-L-R+20)-10)/(W-L-R)*(n-1))))};
 hit.addEventListener('pointermove',e=>show(at(e)));hit.addEventListener('pointerdown',e=>show(at(e)));
 let last=-1;H.forEach((h,i)=>{if(h[5])last=i});show(last>=0?last:n-1);g.setAttribute('visibility','hidden')}
document.querySelectorAll('.rh-chart').forEach(rhDraw);"""
EQUITY_ACTIVE = {"Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value / Contra", "Dividend Yield", "Sectoral/Thematic"}
REVIEW_FLAGS = {"mandate_breach": "its portfolio is outside SEBI's limits for the category"}


PC_HTML = r"""<section class="band"><div class="wrap" style="max-width:860px">
<p class="eyebrow">Portfolio check</p><h1>How do your funds rate?</h1>
<p class="lede" style="margin-top:12px">Add the mutual funds you hold. You'll see each one's rating against its category, what our review rule says about it, and where your funds overlap. Nothing you enter leaves your browser.</p>
<div class="card" style="margin-top:22px;position:relative">
 <label for="pcq" style="font-weight:600">Add a fund</label>
 <input id="pcq" type="search" autocomplete="off" placeholder="Type a fund name, e.g. Parag Parikh Flexi" style="width:100%;margin-top:8px;padding:12px 14px;font:inherit;border:1px solid var(--rule);border-radius:8px;background:var(--bg);color:var(--ink)">
 <div id="pcs" role="listbox" style="display:grid;gap:2px;margin-top:6px"></div>
</div>
<div id="pcsum" style="margin-top:22px"></div>
<div id="pclist" style="display:grid;gap:10px;margin-top:12px"></div>
<div id="pcnotes" style="margin-top:16px"></div>
<div class="card" style="margin-top:22px"><b>Want us to go through it with you?</b><p class="muted" style="margin-top:6px">A portfolio review covers costs, overlap, tax on any switch and whether each fund still fits your plan.</p>
<p style="margin-top:12px"><a class="btn primary" href="/#contact">Book a portfolio review</a> <a class="btn" href="/#method">How ratings work</a></p></div>
<p class="muted" style="font-size:12.5px;margin-top:18px">Ratings describe each fund's past record against its category, not a forecast, and are not a recommendation to buy or sell. Aeterna Wealth is an AMFI-registered mutual fund distributor (ARN-317889). Mutual fund investments are subject to market risks; read all scheme-related documents carefully.</p>
</div></section>
<script>
(function(){
var W={"A+":"Leading","A":"Strong","B":"In line","C":"Lagging","Watch":"Under review","Unrated":"Not yet rated"},
 CL={"A+":"t-ap","A":"t-a","B":"t-b","C":"t-c"},D=[],sel=[],K="aw_pc";
function esc(x){return String(x).replace(/[&<>"]/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})}
function save(){try{localStorage.setItem(K,JSON.stringify(sel))}catch(e){}}
function rv(t,mb){if(t==="A+")return["In the A+ group","New money in this category goes to A+ funds."];
 if(t==="A")return["Keep","Rated A: if you hold it, it stays."];
 if(t==="B"||t==="C")return["Review due after 12 months below A",mb?"Its portfolio has been outside SEBI's limits for its category.":"We look at it once it has been below A for 12 months, when the exit load has ended in almost every equity fund, and weigh the tax first."];
 if(t==="Watch")return["Under review","Something changed at the fund (for example a manager or a merger)."];
 return["Not rated yet","Less than 3 years of history."]}
function draw(){
 var F=sel.map(function(c){return D.find(function(d){return d[0]===c})}).filter(Boolean),cnt={};
 F.forEach(function(d){cnt[d[5]]=(cnt[d[5]]||0)+1});
 document.getElementById("pcsum").innerHTML=F.length?'<h2 style="font-size:24px">Your '+F.length+' fund'+(F.length>1?'s':'')+'</h2><p style="margin-top:6px;font-size:16px">'+["A+","A","B","C","Watch","Unrated"].filter(function(t){return cnt[t]}).map(function(t){return'<b>'+cnt[t]+'</b> '+W[t]}).join(' · ')+'</p>':'<p class="muted">Add funds above to see how they rate.</p>';
 document.getElementById("pclist").innerHTML=F.map(function(d){var r=rv(d[5],d[9]);
  return'<div class="card" style="display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:start"><span class="tier '+(CL[d[5]]||"t-u")+'">'+esc(d[5]==="Unrated"?"–":d[5])+'</span><div style="min-width:0"><a href="'+esc(d[8])+'" style="font-weight:600">'+esc(d[1])+'</a><div class="muted" style="font-size:13px">'+esc(d[2])+' · '+esc(d[3])+(d[6]?' · '+d[6]+' of '+d[7]+' in its group':'')+'</div><div style="font-size:14px;margin-top:4px"><b>'+esc(W[d[5]]||"")+'.</b> '+esc(r[0])+'. '+esc(r[1])+'</div></div><button type="button" data-rm="'+d[0]+'" aria-label="Remove '+esc(d[1])+'" style="background:none;border:0;color:var(--ink-2);font:13px var(--f-body);text-decoration:underline;cursor:pointer;padding:4px">Remove</button></div>'}).join("");
 var n=[],byA={},byC={};F.forEach(function(d){(byA[d[4]]=byA[d[4]]||[]).push(d);if(d[3]!=="Index Fund")(byC[d[3]]=byC[d[3]]||[]).push(d)});
 Object.keys(byA).forEach(function(a){if(byA[a].length>=3)n.push(byA[a].length+" funds from "+esc(a.replace(/ Mutual Fund$/,""))+": one investment team often holds many of the same stocks across its funds, so these may overlap more than their number suggests.")});
 Object.keys(byC).forEach(function(c){if(byC[c].length>=2)n.push(byC[c].length+" funds in "+esc(c)+": funds in one category follow the same index and SEBI rules, so they tend to move together.")});
 if(F.some(function(d){return d[2]==="Regular"}))n.push("Regular plans include distributor commission; Direct plans of the same funds cost less. Each fund page shows both.");
 document.getElementById("pcnotes").innerHTML=n.length?'<div class="card"><b>Worth knowing</b><ul style="margin:8px 0 0;padding-left:20px;display:grid;gap:6px">'+n.map(function(x){return"<li>"+x+"</li>"}).join("")+'</ul></div>':"";
 [].forEach.call(document.querySelectorAll("[data-rm]"),function(b){b.onclick=function(){sel=sel.filter(function(c){return c!==+b.dataset.rm});save();draw()}})}
var q=document.getElementById("pcq"),box=document.getElementById("pcs");
q.addEventListener("input",function(){var t=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);if(!t.length||!D.length){box.innerHTML="";return}
 var ph=t.filter(function(w){return["regular","direct"].indexOf(w)<0}).join(" ");
 var m=D.filter(function(d){var s=(d[1]+" "+d[2]).toLowerCase();return t.every(function(w){return s.indexOf(w)>=0})})
  .map(function(d){var n=d[1].toLowerCase().replace(/&/g,"and");return[(n.indexOf(ph.replace(/&/g,"and"))>=0?0:1),n.length,d]})
  .sort(function(a,b){return a[0]-b[0]||a[1]-b[1]}).map(function(x){return x[2]}).slice(0,8);
 box.innerHTML=m.map(function(d){return'<button type="button" class="btn" style="justify-content:space-between;text-align:left;width:100%" data-add="'+d[0]+'"><span>'+esc(d[1])+' <span class="muted" style="font-size:12.5px">'+esc(d[2])+'</span></span><span class="tier '+(CL[d[5]]||"t-u")+'">'+esc(d[5]==="Unrated"?"–":d[5])+'</span></button>'}).join("")||'<p class="muted" style="font-size:13.5px">No fund matches.</p>';
 [].forEach.call(box.querySelectorAll("[data-add]"),function(b){b.onclick=function(){var c=+b.dataset.add;if(sel.indexOf(c)<0)sel.push(c);save();q.value="";box.innerHTML="";draw();q.focus()}})});
try{sel=JSON.parse(localStorage.getItem(K)||"[]")||[]}catch(e){sel=[]}
fetch("/data/check.json").then(function(r){return r.json()}).then(function(x){D=x;draw()}).catch(function(){document.getElementById("pcsum").innerHTML='<p class="muted">The fund list did not load. Refresh the page to try again.</p>'});
draw()})();
</script>"""


def review_status(f, hist):
    """Where an active equity fund stands under the review rule (Method page, 'How we use the ratings')."""
    if f.get("category") not in EQUITY_ACTIVE:
        return ""
    t, elss = f.get("tier"), f.get("category") == "ELSS"
    wait = "its 3-year lock-in ends" if elss else "you have held it for 12 months"
    flags = [x for x in str(f.get("flags") or "").split(",") if x.strip()]
    hit = [REVIEW_FLAGS[x.strip()] for x in flags if x.strip() in REVIEW_FLAGS]
    below = 0
    for h in reversed(hist or []):
        if h[1] in ("B", "C"): below += 1
        else: break
    since = ""
    if below and hist:
        m = hist[len(hist) - below][0]
        since = f" since {date(int(m[:4]), int(m[5:7]), 1).strftime('%b %Y')} ({below} month{'s' if below > 1 else ''})"
    if hit:
        state, cls, txt = "Review now", "rv-now", f"A red flag brings a review at any time: {'; '.join(hit)}."
    elif t == "A+":
        state, cls, txt = "In the A+ group", "rv-ap", "A score of 75 or more out of 100 against its peer group: the group new money in this category goes to under our review rule."
    elif t == "A":
        state, cls, txt = "Keep", "rv-a", "Rated A: if you hold it, it stays. New money in this category goes to A+ funds."
    elif t in ("B", "C"):
        state, cls, txt = "Review due", "rv-due", (f"Rated {t}{since}. Below A, a fund comes up for review once {wait}"
                                                   + ("" if elss else ", when the exit load has ended in almost every equity fund") + ". We weigh the tax on the gain before replacing it.")
    elif f.get("gate") and "stale" in str(f.get("gate")):
        state, cls, txt = "Review now", "rv-now", "Its NAV has stopped updating: the scheme may have merged or closed."
    else:
        state, cls, txt = "Not rated yet", "rv-new", "Too little history for a rating (3 years), so there is no review signal yet."
    return (f'<div class="card rv {cls}" style="margin-top:16px"><div class="rv-h"><span class="rv-dot"></span><b>Review status: {state}</b></div>'
            f'<p>{txt}</p><p class="muted" style="font-size:12.5px;margin-top:6px">How we use our ratings in client reviews; not a recommendation to buy or sell. Exit loads and tax depend on when you bought, so talk to us before you switch.</p>'
            f'<p style="margin-top:10px"><a href="/#method" class="rv-how">How the review rule works</a></p></div>')


TIER_WORD = {"A+": "A+ (a score of 75 or more)", "A": "A (65 or more)", "B": "B (middle of the peer group)", "C": "C (bottom 30%)"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower().replace("&", " and ")).strip("-")


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def pct(v, d=1):
    return "–" if v is None else f"{v * 100:.{d}f}%"


def spct(v, d=1):
    return "–" if v is None else f"{'+' if v > 0 else ''}{v * 100:.{d}f}%"


def num(v, d=2):
    return "–" if v is None else f"{v:.{d}f}"


def cr(v):
    if v is None:
        return "–"
    n = f"{round(v):,}"
    # Indian grouping: 1,10,925
    s = str(round(v))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        n = head + "," + tail
    return f"₹{n} cr"


def inr2(v):
    """₹ with Indian digit grouping and 2 decimals: 2,045.56 / 1,10,925.00"""
    if v is None:
        return "–"
    whole, frac = f"{v:.2f}".split(".")
    if len(whole) > 3:
        whole = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", whole[:-3]) + "," + whole[-3:]
    return f"₹{whole}.{frac}"


def iname(b):
    """NIFTY MIDCAP 150 -> Nifty Midcap 150 (keeps short acronyms like PSU, IT, MNC)."""
    if not b:
        return b
    return " ".join(w if (len(w) <= 3 and w.isalpha() and w not in ("TOP",)) or any(ch.isdigit() for ch in w) else w.capitalize() for w in str(b).split())


def dmy(v):
    if not v:
        return "–"
    try:
        y, m, d_ = map(int, str(v)[:10].split("-"))
        return date(y, m, d_).strftime("%-d %b %Y")
    except Exception:
        return str(v)


def mon(v):
    try:
        y, m = map(int, str(v).split("-")[:2])
        return date(y, m, 1).strftime("%B %Y")
    except Exception:
        return str(v or "–")


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


ORG_LD = {
    "@context": "https://schema.org", "@type": "FinancialService", "@id": SITE + "/#org",
    "name": ORG["brand"], "legalName": ORG["name"], "url": SITE + "/", "logo": SITE + "/icon-512.png", "image": SITE + "/og.png",
    "telephone": ORG["phone"], "email": ORG["email"],
    "description": "Wealth management for families across India: mutual funds, PMS, AIFs, bonds, unlisted shares and "
                   "tax-aware planning. AMFI-registered mutual fund distributor (ARN-317889). Its website compares every Indian equity and "
                   "index mutual fund, with returns against the right index and track-record ratings.",
    "address": {"@type": "PostalAddress", "streetAddress": ORG["street"], "addressLocality": ORG["city"],
                "postalCode": ORG["pin"], "addressRegion": "Delhi", "addressCountry": "IN"},
    "areaServed": {"@type": "Country", "name": "India"},
    "sameAs": SOCIAL,
    "founder": [dict({"@type": "Person", "name": t["name"], "sameAs": [t["linkedin"]]}, **({"jobTitle": t["role"]} if t.get("role") else {}))
                for t in CFG.get("team", [])],
    "knowsAbout": ["Mutual funds", "Portfolio management services", "Alternative investment funds", "Bonds",
                   "Unlisted shares", "Tax planning"],
}


def analytics_head():
    out = ""
    if CFG.get("cloudflare_beacon_token"):   # cookieless; no consent needed
        out += ("<script defer src='https://static.cloudflareinsights.com/beacon.min.js' "
                f"data-cf-beacon='{{\"token\": \"{e(CFG['cloudflare_beacon_token'])}\"}}'></script>")
    if CFG.get("ga4_id"):   # Google Analytics 4, standard tag (disclosed in the privacy notice; no cookie banner)
        gid = json.dumps(CFG["ga4_id"])
        # only on the real domain: staging and preview visits stay out of the numbers
        out += ("<script>(function(){if(!/(^|\\.)aeternawealth\\.com$/.test(location.hostname))return;"
                f"var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+{gid};document.head.appendChild(s);"
                "window.dataLayer=window.dataLayer||[];window.gtag=function(){dataLayer.push(arguments)};"
                f"gtag('js',new Date());gtag('config',{gid})}})();</script>")
    return out


FAVICON = ('<link rel="icon" href="/favicon.ico" sizes="any"><link rel="icon" href="/favicon.svg" type="image/svg+xml">'
           '<link rel="icon" href="/icon-192.png" type="image/png" sizes="192x192">'
           '<link rel="apple-touch-icon" href="/apple-touch-icon.png">')


def fit_title(t, n=65):
    """Search results show about 60-65 characters: drop the brand suffix first, then trim long fund names."""
    if len(t) <= n:
        return t
    t = re.sub(r"\s*[\(\-]?\s*\(?(formerly|erstwhile)\b[^:)|]*\)?", "", t, flags=re.I)
    if len(t) <= n:
        return t
    t2 = t.replace(" | Aeterna Wealth insights", "").replace(" | Aeterna Wealth", "")
    if len(t2) <= n:
        return t2
    for long, short in ((": NAV, returns, rating, holdings", ": NAV, returns, rating"), (": returns, risk, cost and overlap", ": returns, cost, overlap"),
                        (": ratings, returns and costs", ": ratings and returns"), (" compared: tracking error, expense ratio", " compared")):
        if long in t2:
            t2 = t2.replace(long, short)
            if len(t2) <= n:
                return t2
    return t2


def fit_desc(d, n=158):
    """Descriptions over ~160 characters are cut by search engines: end at a full sentence, else a word."""
    if len(d) <= n:
        return d
    cut = d[:n]
    dot = cut.rfind(". ")
    if dot > 90:
        return cut[:dot + 1]
    return cut[:cut.rfind(" ")].rstrip(",;:") + "…"


THEME_JS = ('<meta name="theme-color" content="#f6f8f7"><script>try{var t=localStorage.getItem("aw-theme");if(t==="light"||t==="dark"){document.documentElement.setAttribute("data-theme",t);'
            'if(t==="dark")document.querySelector(\'meta[name="theme-color"]\').content="#06100d"}}catch(e){}</script>')   # light by default; the switch in the header remembers a choice


def head(title, desc, path, extra_ld=(), og_type="website"):
    title, desc = fit_title(title), fit_desc(desc)
    url = SITE + path
    robots = '<meta name="robots" content="noindex,nofollow">' if not LAUNCHED else '<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
    return (f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            f'<title>{e(title)}</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">{robots}'
            f'<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="Aeterna Wealth">'
            f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
            f'<meta property="og:url" content="{url}"><meta property="og:image" content="{SITE}/og.png"><meta property="og:locale" content="en_IN">'
            f'<meta name="twitter:card" content="summary_large_image"><meta name="twitter:site" content="@AeternaWealth">'
            f'<meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}"><meta name="twitter:image" content="{SITE}/og.png">'
            + THEME_JS + FAVICON + "".join(jsonld(x) for x in extra_ld) + analytics_head())


def crumbs(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate(items)]}


CSS_VER = ""
RANGE_JS = ""   # the range-of-outcomes drawing, taken from the app so both use one copy
HEADER = ""   # filled in main() from the app's own header, so every page has the same menu
HEADER_JS = ("<script>(function(){var dd=[].slice.call(document.querySelectorAll('.dd')),n=document.getElementById('nav'),m=document.getElementById('menuBtn');"
             "function shut(x){x.classList.remove('open');var y=x.querySelector('.ddbtn');if(y)y.setAttribute('aria-expanded','false')}"
             "dd.forEach(function(d){var b=d.querySelector('.ddbtn');if(b)b.onclick=function(e){dd.forEach(function(x){if(x!==d)shut(x)});var o=d.classList.toggle('open');b.setAttribute('aria-expanded',o);e.stopPropagation()}});"
             "document.addEventListener('click',function(e){dd.forEach(function(d){if(!d.contains(e.target))shut(d)})});"
             "if(m)m.onclick=function(){var o=n.classList.toggle('open');m.setAttribute('aria-expanded',o)};"
             "var h=(document.querySelector('a.brand')||{}).href||'/',go=function(){location.href=h.split('#')[0]+'?q='};var s=document.getElementById('srchBtn');if(s)s.onclick=go;"
             "document.addEventListener('keydown',function(e){if(e.key==='/'&&!/input|textarea|select/i.test(document.activeElement.tagName)){e.preventDefault();go()}});"
             "var ac=document.getElementById('addCmp');if(ac)ac.onclick=function(){var c=[];try{c=JSON.parse(localStorage.getItem('aw_cmp')||'[]')}catch(e){}var k=+ac.getAttribute('data-code');if(c.indexOf(k)<0)c.push(k);try{localStorage.setItem('aw_cmp',JSON.stringify(c.slice(-4)))}catch(e){}location.href='/#compare'}})();</script>")


MOTION_JS = ("<script>(function(){if(!('IntersectionObserver' in window)||matchMedia('(prefers-reduced-motion:reduce)').matches)return;"
             "var io=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;var el=e.target;io.unobserve(el);if(el.hasAttribute('data-fig'))fig(el);else el.classList.add('in')})},{rootMargin:'0px 0px -10% 0px'});"
             "function fig(el){var m=el.textContent.match(/^(\\D*)([\\d,]*\\.?\\d+)([\\s\\S]*)$/);if(!m)return;var to=+m[2].replace(/,/g,''),dp=(m[2].split('.')[1]||'').length,t0=performance.now();"
             "(function st(t){var k=Math.min(1,(t-t0)/1100),e=1-Math.pow(1-k,4);el.textContent=m[1]+(to*e).toLocaleString('en-IN',{minimumFractionDigits:dp,maximumFractionDigits:dp})+m[3];if(k<1)requestAnimationFrame(st);else el.textContent=m[0]})(t0)}"
             "[].forEach.call(document.querySelectorAll('main .card,main .tablewrap,main .note,main figure'),function(el){if(el.closest('.sr'))return;if(el.getBoundingClientRect().top>innerHeight*.92){el.classList.add('sr');io.observe(el)}});"
             "[].forEach.call(document.querySelectorAll('main .big-fig'),function(el){if(/^\\D*[\\d,]*\\.?\\d/.test(el.textContent.trim())&&!el.children.length){el.setAttribute('data-fig','');io.observe(el)}});"
             "[].forEach.call(document.querySelectorAll('main a.card'),function(el){el.classList.add('glow')});"
             "if(matchMedia('(hover:hover) and (pointer:fine)').matches)document.addEventListener('pointermove',function(e){var g=e.target.closest&&e.target.closest('.glow');if(!g)return;var r=g.getBoundingClientRect();g.style.setProperty('--mx',(e.clientX-r.left)+'px');g.style.setProperty('--my',(e.clientY-r.top)+'px')},{passive:true})})();</script>")


def footer():
    def label(u):
        return "LinkedIn" if "linkedin" in u else "Instagram" if "instagram" in u else "X" if "x.com" in u else "YouTube" if "youtube" in u else u
    soc = " · ".join('<a href="%s" target="_blank" rel="noopener me">%s</a>' % (e(u), label(u)) for u in SOCIAL)
    return f"""<footer class="site"><div class="wrap"><div class="cols">
 <div class="stack" style="gap:8px"><b style="font:500 18px var(--f-display);color:var(--ink)">{ORG['name']}</b><span>AMFI-registered Mutual Fund Distributor · {ORG['arn']}</span><span>{ORG['street']}, {ORG['city']} {ORG['pin']}</span><span>+91 85959 93600 · {ORG['email']}</span>{f'<span>{soc}</span>' if soc else ''}</div>
 <div class="stack" style="gap:6px"><b style="color:var(--ink)">Fund data</b><a href="/mutual-funds/">All categories</a><a href="/mutual-funds/amc/">Fund houses</a><a href="/mutual-funds/index-fund/">Index funds</a><a href="/insights/">Insights</a><a href="/learn/">Investor guides</a><a href="/#method">Method and backtest</a></div>
 <div class="stack" style="gap:6px"><b style="color:var(--ink)">Calculators</b><a href="/plan/">Money Plan</a><a href="/calculators/sip/">SIP calculator</a><a href="/calculators/goal/">Goal planner</a><a href="/calculators/swp/">SWP calculator</a><a href="/calculators/emi/">EMI calculator</a><a href="/calculators/capital-gains-tax/">Capital gains tax</a></div>
 <div class="stack" style="gap:6px"><b style="color:var(--ink)">Company</b><a href="/invest/">What we offer</a><a href="/#about">About</a><a href="/#contact">Contact</a><a href="/disclosures/">Disclosures</a><a href="/privacy/">Privacy</a><a href="/terms/">Terms</a><a href="/grievances/">Grievances</a></div>
 </div><p class="cat-links" style="margin:18px 0 0;font-size:13.5px;line-height:2;color:var(--ink-3)"><b style="color:var(--ink-2);font-weight:600">Fund categories:</b> <a href="/mutual-funds/large-cap/">Large Cap</a> · <a href="/mutual-funds/mid-cap/">Mid Cap</a> · <a href="/mutual-funds/small-cap/">Small Cap</a> · <a href="/mutual-funds/large-and-mid-cap/">Large &amp; Mid Cap</a> · <a href="/mutual-funds/multi-cap/">Multi Cap</a> · <a href="/mutual-funds/flexi-cap/">Flexi Cap</a> · <a href="/mutual-funds/focused/">Focused</a> · <a href="/mutual-funds/value-contra/">Value / Contra</a> · <a href="/mutual-funds/dividend-yield/">Dividend Yield</a> · <a href="/mutual-funds/elss/">ELSS</a> · <a href="/mutual-funds/sectoral-thematic/">Sectoral/Thematic</a> · <a href="/mutual-funds/index-fund/">Index funds</a> · <a href="/mutual-funds/arbitrage/">Arbitrage</a> · <a href="/mutual-funds/liquid/">Liquid</a> · <a href="/mutual-funds/corporate-bond/">Corporate Bond</a> · <a href="/mutual-funds/gilt/">Gilt</a> · <b style="color:var(--ink-2);font-weight:600;margin-left:6px">Learn:</b> <a href="/learn/">Investor guides</a></p><p class="disc">Mutual fund investments are subject to market risks; read all scheme-related documents carefully. {ORG['name']} is a mutual fund distributor ({ORG['arn']}) and earns commission from asset management companies on Regular plans. Direct plans of the same schemes are available at a lower expense ratio. Ratings describe past track records using public data and are not investment advice, a recommendation or a forecast. Past performance does not guarantee future returns.</p></div></footer>"""


def page(title, desc, path, body, ld=()):
    return (f'<!doctype html>\n<html lang="en-IN" data-theme="light"><head>{head(title, desc, path, ld)}'
            '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Libre+Franklin:wght@400;500;600&family=Source+Serif+4:ital,opsz,wght@0,8..60,400..600;1,8..60,400&display=swap">'
            '<link rel="stylesheet" href="/assets/site.css?v=' + CSS_VER + '"><style>table.cmp th{white-space:normal;text-transform:none;letter-spacing:0;font:600 14px/1.3 var(--f-body)}table.cmp td{white-space:normal}@media (max-width:600px){table.cmp th,table.cmp td{padding:8px 6px;font-size:13px}}.prose h2{font-size:24px;margin:30px 0 8px}.prose ul{padding-left:20px}[hidden]{display:none!important}</style></head><body>'
            f'{HEADER}<main>{body}</main>{footer()}{HEADER_JS}{MOTION_JS}</body></html>\n')


def write(path, text):
    p = DIST / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


TIER_LABEL = {"A+": "Leading", "A": "Strong", "B": "In line", "C": "Lagging", "Watch": "Under review", "Unrated": "Not yet rated"}   # same as TW in app.html


def tier_badge(t, word=False):
    cls = {"A+": "t-ap", "A": "t-a", "B": "t-b", "C": "t-c"}.get(t, "t-u")
    w = TIER_LABEL.get(t, TIER_LABEL["Unrated"])
    b = f'<span class="tier {cls}" title="{e((t + ": " if t in ("A+", "A", "B", "C", "Watch") else "") + w + " in its category")}">{e(t if t and t != "Unrated" else "–")}</span>'
    return f'<span class="row" style="gap:8px;display:inline-flex">{b}<span class="tier-w">{e(w)}</span></span>' if word else b


def cap_note(f):
    flags = [x for x in str(f.get("flags") or "").split(", ") if x]
    mb = []
    for x in str(f.get("mandate_breaches") or "").split("; "):
        m = re.match(r"^(\w+) (\d+) \(needs >=(\d+)\)", x)
        if m:
            what = "equities" if m.group(1) == "equity" else m.group(1) + " caps"
            mb.append(f"{m.group(2)}% in {what}; SEBI requires at least {m.group(3)}%")
    if "mandate_breach" in flags and mb and f.get("tier_before_cap"):
        return (f"Its score puts it in {f['tier_before_cap']}, but it is rated {f.get('tier')}, one step lower, because its portfolio was outside "
                "SEBI's limits for its category in two consecutive monthly portfolios: " + ", ".join(mb) + ".")
    if "mandate_breach" in flags and mb:
        return "Capped at B: " + ", ".join(mb) + " in two consecutive monthly portfolios."
    if "mandate_watch" in flags and mb:
        return "Watch: " + ", ".join(mb) + " in the latest portfolio. No effect on the rating unless this repeats in the next monthly portfolio."
    if "chronic_underperformer" in flags:
        return "Capped at C: persistently behind its index and most peers over rolling 3-year periods."
    return ""


def main():
    funds = json.loads((S / "data" / "funds.json").read_text())
    meta = json.loads((S / "data" / "meta.json").read_text())
    hold = json.loads((S / "data" / "holdings.json").read_text()) if (S / "data" / "holdings.json").exists() else {}
    ins = json.loads((S / "data" / "insights.json").read_text()) if (S / "data" / "insights.json").exists() else {"items": []}
    as_of = meta.get("as_of")
    if DIST.exists():
        for sub in ("mutual-funds", "assets", "invest", "learn", "calculators", "compare", "insights", "disclosures", "privacy", "terms", "grievances"):
            shutil.rmtree(DIST / sub, ignore_errors=True)
    (DIST / "data").mkdir(parents=True, exist_ok=True)

    # ---- shared stylesheet (the app's own design tokens and components)
    app = (S / "app.html").read_text(encoding="utf-8")
    global HEADER
    hdr = app[app.index("<!-- HEADER-START -->"): app.index("<!-- HEADER-END -->")]
    hdr = re.sub(r'href="#', 'href="/#', hdr)
    HEADER = '<header class="site">' + hdr + '</header>'
    global RANGE_JS
    RANGE_JS = app[app.index('function rangeBlock(f){'): app.index('function portfolioBlock(')]
    css = app[app.index("<style>") + 7: app.index("</style>")]
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    global CSS_VER
    import hashlib
    CSS_VER = hashlib.sha1(css.encode("utf-8")).hexdigest()[:10]   # a new address whenever the styles change, so no browser keeps an old copy
    (DIST / "assets" / "site.css").write_text(css, encoding="utf-8")
    for icon in ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        if (S / icon).exists():
            shutil.copy(S / icon, DIST / icon)
    if (S / "og.png").exists():
        shutil.copy(S / "og.png", DIST / "og.png")

    # ---- urls
    used = set()
    for f in sorted(funds, key=lambda x: (x["name"], x["plan_type"], x["code"])):
        base = f"{slug(f['name'])}-{slug(f['plan_type'])}"
        u = base if base not in used else f"{base}-{f['code']}"
        used.add(u)
        f["_url"] = f"/mutual-funds/{slug(f['category'])}/{u}/"
    (DIST / "data").mkdir(parents=True, exist_ok=True)
    if (S / "model_backtest.json").exists():   # the per-category test shown on the Method page
        shutil.copy(S / "model_backtest.json", DIST / "data" / "model-backtest.json")
    (DIST / "data" / "fund-urls.json").write_text(json.dumps({str(f["code"]): f["_url"] for f in funds}, separators=(",", ":")), encoding="utf-8")
    # portfolio check: a light list of every fund for the /portfolio-check/ page
    chk = [[f["code"], f["name"], f.get("plan_type") or "", f.get("category") or "", f.get("amc") or "", f.get("tier") or "Unrated",
             f.get("peer_rank"), f.get("peer_count"), f["_url"], 1 if "mandate_breach" in str(f.get("flags") or "") else 0] for f in funds]
    (DIST / "data" / "check.json").write_text(json.dumps(chk, separators=(",", ":")), encoding="utf-8")
    # rank by return over the index in each period, within the peer group and plan: what the fund page's returns
    # table shows (the ratings page's period view ranks a blend of return, falls, consistency and cost instead)
    RET_RANK.clear()
    by = {}
    for f in funds:
        for h in ("6M", "1Y", "3Y", "5Y"):
            if f.get("excess_" + h) is not None:
                by.setdefault((f.get("peer_group"), f.get("plan_type"), h), []).append(f)
    for (pg, pl, h), g in by.items():
        g = sorted(g, key=lambda x: -x["excess_" + h])
        for i, x in enumerate(g):
            RET_RANK[(x["code"], h)] = (1 + sum(1 for y in g[:i] if y["excess_" + h] > x["excess_" + h]), len(g))
    rhp = S.parent / "outputs" / "latest" / "rating_history.json"
    if rhp.exists():
        RH.update(json.loads(rhp.read_text(encoding="utf-8")))
    import build_pages as P
    Bm = sys.modules[__name__]
    for f in funds:
        f["_name"] = P.nice(f["name"])
    by_cat = {}
    for f in funds:
        by_cat.setdefault(f["category"], []).append(f)
    CMP_KEYS = ("ret_1Y", "ret_3Y", "ret_5Y", "ter", "vol_3y", "max_drawdown_3y")
    cat_med = {}
    for c, lst in by_cat.items():
        for plan in ("Regular", "Direct"):
            sub = [x for x in lst if x.get("plan_type") == plan]
            m = {}
            for k in CMP_KEYS:
                v = sorted(x[k] for x in sub if isinstance(x.get(k), (int, float)))
                m[k] = (v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2) if len(v) >= 5 else None
                m[k + "_n"] = len(v)
            cat_med[(c, plan)] = m
    order = ["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap", "Flexi Cap", "Focused",
             "Value / Contra", "Dividend Yield", "ELSS", "Sectoral/Thematic", "Index Fund",
             "Aggressive Hybrid", "Balanced Advantage", "Multi Asset Allocation", "Balanced Hybrid", "Equity Savings", "Conservative Hybrid", "Arbitrage"]
    cats = [c for c in order if c in by_cat] + sorted(set(by_cat) - set(order))
    urls = [("/", "daily", "1.0"), ("/mutual-funds/", "daily", "0.9"), ("/portfolio-check/", "weekly", "0.8"), ("/ratings-update/", "monthly", "0.5")]

    # ---- extra page sets (calculators, fund houses, index/theme groups, comparisons, insights, legal)
    cmp_map = P.compare_pages(Bm, funds, hold, urls, as_of)
    made_idx, made_thm = P.group_pages(Bm, funds, urls, as_of)
    P.amc_pages(Bm, funds, urls, as_of)
    P.calculator_pages(Bm, urls, P.calc_js(app))
    P.insight_pages(Bm, ins, urls, as_of)
    P.legal_pages(Bm, urls)
    import invest_pages as IP
    IP.invest_pages(Bm, funds, hold, ins, urls)
    import planner_pages as PL
    PL.planner_pages(Bm, urls)
    import learn_pages as LP
    LP.learn_pages(Bm, funds, hold, ins, urls, as_of)
    cmp_by = {}
    for (ka, kb), pth in cmp_map.items():
        cmp_by.setdefault(ka, []).append((kb, pth))
        cmp_by.setdefault(kb, []).append((ka, pth))
    name_by_pair = {f.get("pair_key"): f["_name"] for f in funds}

    # ---- fund pages
    tord = {"A+": 0, "A": 1, "B": 2, "C": 3}
    for f in funds:
        twin = next((x for x in funds if x.get("pair_key") == f.get("pair_key") and x["code"] != f["code"]), None)
        top = (hold.get(f.get("pair_key")) or [])[:10]
        bench = iname(f.get("benchmark")) or "peer median"
        BL = f.get("bench_label")
        bp = BL if BL and BL.startswith("the median") else f"its composite benchmark ({BL})" if BL else f"the {bench} TRI"
        rated = f.get("tier") not in (None, "", "Unrated")
        r3, e3 = f.get("ret_3Y"), f.get("excess_3Y")
        arb = f["category"] == "Arbitrage"
        desc_bits = [f"{f['_name']} ({f['plan_type']}, Growth), {f['category'].lower()} fund from {f.get('amc', '')}."]
        if arb and r3 is not None and f.get("liq_cagr_3y") is not None:
            desc_bits.append(f"3-year return {pct(r3)} a year vs {pct(f['liq_cagr_3y'])} for the median liquid fund (before tax).")
        elif r3 is not None and e3 is not None:
            desc_bits.append(f"3-year return {pct(r3)} a year vs {pct(r3 - e3)} for {bp}.")
        if rated:
            desc_bits.append(f"Track-record rating {f['tier']} ({int(f.get('peer_rank') or 0)} of {int(f.get('peer_count') or 0)}).")
        desc_bits.append(f"NAV {inr2(f.get('nav_latest'))} on {dmy(f.get('nav_date'))}; expense ratio {num(f.get('ter'), 2)}%.")
        desc = " ".join(desc_bits)[:300]
        title = f"{f['_name']} ({f['plan_type']}): NAV, returns, rating, holdings | Aeterna Wealth"
        rows = ""
        for h, lab in (("6M", "6 months"), ("1Y", "1 year"), ("3Y", "3 years (a year)"), ("5Y", "5 years (a year)")):
            r, x = f.get("ret_" + h), f.get("excess_" + h)
            rr = RET_RANK.get((f["code"], h))
            rank_s = "%d / %d" % rr if rr else "–"
            idx_s = pct(r - x) if r is not None and x is not None else "–"
            cls = "pos" if (x or 0) > 0 else ("neg" if x is not None else "")
            rows += (f"<tr><td class='l'>{lab}</td><td class='num'>{pct(r)}</td><td class='num'>{idx_s}</td>"
                     f"<td class='num {cls}'>{spct(x)}</td><td class='num'>{rank_s}</td></tr>")
        risk = [("Volatility, 3Y", pct(f.get("vol_3y"))), ("Max fall, 5Y", pct(f.get("max_drawdown_5y"))),
                ("Up capture, 3Y", num(f.get("upside_capture_3y"), 0)), ("Down capture, 3Y", num(f.get("downside_capture_3y"), 0)),
                ("Information ratio, 3Y", num(f.get("info_ratio_3y"))), ("Jensen's alpha, 3Y", spct(f.get("alpha_3y"))),
                ("Beta, 3Y", num(f.get("beta_3y"))), ("Sharpe, 3Y", num(f.get("sharpe_3y"))),
                ("Tracking difference, 1Y", (num(f.get("tracking_diff_1y")) + "%") if f.get("tracking_diff_1y") is not None else "–"),
                ("Tracking error, 1Y", (num(f.get("tracking_err_1y")) + "%") if f.get("tracking_err_1y") is not None else "–")]
        if arb:
            risk = [("Volatility, 3Y (monthly returns)", pct(f.get("vol_3y"), 2)), ("Months with a loss, 3Y", pct(f.get("neg_months_3y"), 0)),
                    ("Max fall, 3Y", pct(f.get("max_drawdown_3y"), 2)), ("Rolling 1-year return vs index, median", spct(f.get("roll1y_excess_median"), 2)),
                    ("Rolling 1-year periods ahead of the index", pct(f.get("roll1y_hit_rate"), 0))]
        risk = "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in risk if v not in ("–", "–%"))
        hold_html = ("<div class='kv' style='grid-template-columns:1fr'>" + "".join(f"<div><span>{e(t[1])}</span><b>{num(t[2], 1)}%</b></div>" for t in top) + "</div>"
                     f"<p class='muted' style='font-size:12.5px;margin-top:8px'>Top 10 holdings, {mon(f.get('holdings_month') or meta.get('holdings_month'))} portfolio.</p>") if top else \
            "<p class='muted'>Holdings for this scheme are not available yet; its rating uses the track record only.</p>"
        if arb:
            hold_html = ("<p class='muted'>An arbitrage fund buys shares and sells the same shares in the futures market, so its stock list "
                         "says nothing about its risk; we leave it out. What matters is the return it earns over short-term rates, its costs and its size.</p>")
        liq_html = ""
        if arb:
            lrows = ""
            for y, lab in ((1, "1 year"), (3, "3 years (a year)")):
                fr, lr = f.get(f"ret_{y}Y"), f.get(f"liq_cagr_{y}y")
                if fr is None or lr is None:
                    continue
                fa, la = fr * (1 - TAX_EQUITY_LTCG), lr * (1 - TAX_SLAB_TOP)
                lrows += (f"<tr><td class='l'>{lab}</td><td class='num'>{pct(fr, 2)}</td><td class='num'>{pct(lr, 2)}</td><td class='num {'pos' if fr > lr else 'neg'}'>{spct(fr - lr, 2)}</td>"
                          f"<td class='num'>{pct(fa, 2)}</td><td class='num'>{pct(la, 2)}</td><td class='num {'pos' if fa > la else 'neg'}'>{spct(fa - la, 2)}</td></tr>")
            if lrows:
                liq_html = ("<h2 style='margin-top:36px;font-size:26px'>Against liquid funds</h2>"
                            "<div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Period</th><th>Fund</th><th>Median liquid fund</th><th>Difference</th>"
                            "<th>Fund, after tax</th><th>Liquid, after tax</th><th>Difference, after tax</th></tr></thead><tbody>" + lrows + "</tbody></table></div>"
                            "<p class='muted' style='font-size:12.5px;margin-top:8px'>Median of every liquid fund's " + e(f['plan_type']) + " plan (Growth). After tax assumes the 30% slab and a holding of over a year: "
                            "liquid-fund gains taxed at 31.2% (slab plus cess), arbitrage gains at 13% (long-term capital gains plus cess). Surcharge and the ₹1.25 lakh yearly exemption on equity gains are ignored; "
                            "both favour arbitrage further. In a lower slab, or for less than a year (20% plus cess on arbitrage gains), the gap is smaller and can reverse.</p>")
        cn = cap_note(f)
        peers = sorted([x for x in by_cat[f["category"]] if x["plan_type"] == f["plan_type"] and x.get("peer_group") == f.get("peer_group") and x["code"] != f["code"]],
                       key=lambda x: abs((x.get("peer_rank") or 999) - (f.get("peer_rank") or 999)) if rated else -(x.get("aum_cr") or 0))[:6]
        faq = [(f"What is the NAV of {f['_name']} ({f['plan_type']} plan)?", f"{inr2(f.get('nav_latest'))} on {dmy(f.get('nav_date'))} (Growth option)."),
               (f"What is the expense ratio of {f['_name']} ({f['plan_type']})?", f"{num(f.get('ter'), 2)}% a year" + (f"; the {twin['plan_type']} plan's is {num(twin.get('ter'), 2)}%." if twin and twin.get('ter') is not None else "."))]
        if r3 is not None and e3 is not None:
            faq.append((f"What return has {f['_name']} given over 3 years?", f"{pct(r3)} a year ({f['plan_type']} plan) over the 3 years to {dmy(f.get('nav_date'))}, against {pct(r3 - e3)} for {bp}."))
        if f.get("tax") and asset_class(f["category"]) == "Hybrid":
            faq.append((f"How is {f['_name']} taxed?", TAX_TEXT.get(f["tax"], "")))
        if arb:
            faq.append((f"Is {f['_name']} better than a liquid fund?", "Before tax, arbitrage funds usually earn a little less than liquid funds. They are taxed as equity, so for an investor in the 30% slab who holds for over a year, they have usually come out ahead after tax; see the table above. For lower slabs or short holdings the gap narrows."))
            faq.append(("How are arbitrage funds taxed?", "As equity funds: gains on units held over a year are taxed at 12.5% beyond ₹1.25 lakh a year (plus cess); held for a year or less, at 20%. Liquid fund gains are added to your income and taxed at your slab rate."))
        if top and not arb:
            faq.append((f"What does {f['_name']} invest in?", f"Its largest holdings are {', '.join(t[1] for t in top[:3])}" + (f", with {num(f.get('n_stocks'), 0)} stocks in all" if f.get('n_stocks') else "") + f" ({mon(f.get('holdings_month') or meta.get('holdings_month'))} portfolio)."))
        if rated:
            faq.append((f"How is {f['_name']} rated?", f"{f['tier']}: {int(f.get('peer_rank') or 0)} of {int(f.get('peer_count') or 0)} {f['plan_type']} plans in {f.get('peer_group')}, on its track record. This describes the past and is not a recommendation."))
        cmp_links = "".join(f"<li><a href='{pth}'>{e(f['_name'])} vs {e(name_by_pair.get(k, ''))}</a></li>" for k, pth in cmp_by.get(f.get("pair_key"), []))
        more = (("<div class='grid g2' style='margin-top:36px;align-items:start'><div><h2 style='font-size:24px'>Similar funds</h2><ul style='margin-top:10px;line-height:1.9'>"
                 + "".join(f"<li><a href='{x['_url']}'>{e(x['_name'])}</a> <span class='muted'>{e(x.get('tier') or '')}</span></li>" for x in peers) + "</ul></div>"
                 + (f"<div><h2 style='font-size:24px'>Compared</h2><ul style='margin-top:10px;line-height:1.9'>{cmp_links}</ul></div>" if cmp_links else "") + "</div>")
                + "<h2 style='font-size:24px;margin-top:36px'>Common questions</h2>"
                + "".join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq))
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        twin_btn = ('<a class="btn" href="%s">See %s plan</a>' % (twin["_url"], e(twin["plan_type"]))) if twin else ""
        rate_head = (": %d of %d in %s" % (int(f.get("peer_rank") or 0), int(f.get("peer_count") or 0), e(f.get("peer_group")))) if rated else ""
        rate_text = ("%s, score %s out of 100. Describes the past, not a forecast." % (TIER_WORD.get(f["tier"], f["tier"]), num(f.get("score"), 1))) if rated \
            else "Not rated yet: a rating needs at least 3 years of history (1 year for index funds)."
        cap_html = ('<p class="flag" style="font-size:13.5px;margin-top:4px">%s</p>' % e(cn)) if cn else ""
        sc = f.get("score")
        if rated and f.get("market_mode") and sc is not None and f.get("tier") in ("A", "B", "C"):   # v8 equity: distance to the next tier
            nxt, cut = ("A+", 75) if f["tier"] == "A" else ("A", 65)
            gap = cut - float(sc)
            if gap > 0:
                cap_html += ('<p class="muted" style="font-size:13px;margin-top:4px">Score %s: %s point%s below %s (%s needs %d).</p>'
                             % (num(sc, 1), num(gap, 1), "" if round(gap, 1) == 1 else "s", nxt, nxt, cut))
        if rated and f.get("market_mode"):   # v7 equity: which criteria the month was rated on, and the 3-year note
            cap_html += ('<p class="muted" style="font-size:13px;margin-top:6px"><span class="mode %s">%s</span> %s</p>'
                         % (("mode-n", "Normal mode", "Rated on the normal criteria for its category.") if f["market_mode"] == "normal" else
                            ("mode-f", "After-a-fall mode", "Its category's index was below its 200-day average on the rating day, so half the score comes from the after-a-fall criteria.")))
            if f.get("behind_index_3y"):
                cap_html += '<p class="muted" style="font-size:13px;margin-top:4px">Behind its index over 3 years, after costs. Shown for information; it does not cap the rating.</p>'
            if (f.get("tier") in ("B", "C") and (f.get("roll3y_hit_rate") or 0) >= .8 and (f.get("excess_5Y") if f.get("excess_5Y") is not None else -1) > .01
                    and (f.get("info_ratio_3y") if f.get("info_ratio_3y") is not None else -1) > .3):
                # the rating leans on the last 1-12 months; a long, steady record against the index is shown beside it
                cap_html += ('<p style="font-size:13.5px;margin-top:6px"><span class="mode mode-n">Strong long record</span> Ahead of its index in %s of rolling '
                             '3-year periods, and %s a year over 5 years. The rating leans on recent months; this record is shown for balance.</p>'
                             % (pct(f["roll3y_hit_rate"], 0), spct(f["excess_5Y"])))
            if f.get("one_month_lead"):
                cap_html += ('<p class="muted" style="font-size:13px;margin-top:4px">Most of its lead over the index in the last 6 months came from one month (%s, %s). '
                             'One large gain can fade; the rating does not adjust for it.</p>' % (e(f["one_month_lead"]), spct(f.get("one_month_gain"))))
        cap_html += (' <a href="/#method" style="font-size:13px">How ratings work</a> · <a href="/ratings-update/" style="font-size:13px">What changed in November 2026</a>'
                     if rated and f.get("market_mode") else "")
        d1 = f.get("nav_chg_1d")
        day_html = (f'<div><div class="muted" style="font-size:13px">1-day change</div><div class="mono {"pos" if d1 > 0 else "neg" if d1 < 0 else ""}" style="font-size:20px">{spct(d1, 2)}</div></div>') if d1 is not None else ""
        flow_html = ""
        if f.get("flow_4q") is not None:
            fr = [(f"Net flow, quarter to {e(f.get('flow_quarter') or '')}", spct(f.get("flow_1q")) + " of AUM"), ("Net flow, last 4 quarters", spct(f.get("flow_4q")) + " of AUM")]
            flow_html = ('<h3 style="margin-top:28px">Money flows</h3><div class="kv" style="margin-top:8px">' + "".join(f"<div><span>{k}</span><b>{v}</b></div>" for k, v in fr)
                         + '</div><p class="muted" style="font-size:12.5px;margin-top:8px">Estimated from AMFI quarterly average AUM after removing the change in NAV.</p>')
        rh_html = ""
        hh = RH.get(str(f["code"])) or []
        if len(hh) >= 3:
            mo = lambda m: date(int(m[:4]), int(m[5:7]), 1).strftime("%b %Y")
            chg = [h for h in hh if h[5]][::-1][:6]
            def chg_head(p, h):
                rk = f"rank {p[2]} → {h[2]} of {h[3]}" if h[2] and p[2] else ""
                return (f"{e(h[1])}, {rk}" if p[1] == h[1] else f"{e(p[1])} → {e(h[1])}" + (f" ({rk})" if rk else ""))
            items = "".join(f"<li><b>{mo(h[0])}: {chg_head(p, h)}</b>. {e(h[5])}</li>" for h in chg for p in [hh[hh.index(h) - 1]])
            rh_html = (f'<h2 style="margin-top:36px;font-size:26px">Rating history</h2><p class="muted" style="margin-top:8px">The rating at each month-end over the last {len(hh)} months. '
                       'Hover or tap the chart for a month; larger dots mark a change and shaded months were rated in after-a-fall mode. Months before November 2026 are rebuilt with today\'s rules, using only data available at each month-end.</p>'
                       f'<div class="card rh-card" style="margin-top:14px"><div class="rh-chart" data-h="{e(json.dumps(hh, separators=(",", ":")))}"></div></div>'
                       + (f'<h3 style="margin-top:18px;font-size:18px">Recent changes</h3><ul class="rh-list">{items}</ul>' if chg else '<p class="muted" style="margin-top:12px">No change of rating in this period.</p>')
                       + f'<script>{RH_JS}</script>')
        range_html = ""
        if f.get("hist3y_n") and not arb and asset_class(f["category"]) != "Debt":
            rd = {k: f.get(k) for k in ("hist3y_worst", "hist3y_p10", "hist3y_median", "hist3y_p90", "hist3y_best", "hist3y_n", "hist3y_pos", "hist3y_gt7")}
            rd["hist3y_from"] = dmy(f.get("hist3y_from"))
            range_html = ('<div id="rangeBox"></div><script>(function(){const pct=(v,d=1)=>v==null?"–":(v*100).toFixed(d)+"%",dmy=x=>x;' + RANGE_JS
                          + 'document.getElementById("rangeBox").innerHTML=rangeBlock(' + json.dumps(rd) + ')})();</script>')
        # how the fund compares with the typical (median) fund of its category and plan
        cm, crow = cat_med.get((f["category"], f.get("plan_type")), {}), ""
        lab = {"ret_1Y": ("Return, 1 year", "ret"), "ret_3Y": ("Return, 3 years (a year)", "ret"), "ret_5Y": ("Return, 5 years (a year)", "ret"),
               "ter": ("Expense ratio", "ter"), "vol_3y": ("Volatility, 3 years", "risk"), "max_drawdown_3y": ("Worst fall, 3 years", "dd")}
        for k, (name, kind) in lab.items():
            v, mv = f.get(k), cm.get(k)
            if not isinstance(v, (int, float)) or mv is None:
                continue
            if kind == "ter":
                word = "cheaper" if v < mv - .005 else "costlier" if v > mv + .005 else "about the same"
                fv, fm = num(v, 2) + "%", num(mv, 2) + "%"
            else:
                d = v - mv
                same = abs(d) < (.001 if kind == "ret" else .002)
                word = ("about the same" if same else ("ahead" if d > 0 else "behind") if kind == "ret" else
                        ("steadier" if d < 0 else "more volatile") if kind == "risk" else ("a smaller fall" if d > 0 else "a deeper fall"))
                fv, fm = pct(v, 2), pct(mv, 2)
            crow += f"<tr><td class='l'>{name}</td><td class='num'>{fv}</td><td class='num'>{fm}</td><td class='l'>{word}</td></tr>"
        lc = f["category"].lower()
        cat_html = ((f"<h2 style='margin-top:36px;font-size:26px'>Against other {e(f['category'])} funds</h2>"
                     + (f"<p style='margin-top:8px'>SEBI requires {e(lc)} funds to {e(CAT_INFO[f['category']])}. "
                        f"Here is how this fund compares with the typical (median) {e(f.get('plan_type') or '')} plan among {cm.get('ret_1Y_n', 0)} in the category.</p>"
                        if f['category'] in CAT_INFO else "")
                     + "<div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Measure</th><th>This fund</th><th>Typical fund</th><th class='l'>This fund is</th></tr></thead><tbody>"
                     + crow + "</tbody></table></div>") if crow else "")
        # what the plan type means, next to the other plan's cost and return
        plan_html = ""
        if twin and isinstance(f.get("ter"), (int, float)) and isinstance(twin.get("ter"), (int, float)):
            g3 = (f.get("ret_3Y") - twin.get("ret_3Y")) if isinstance(f.get("ret_3Y"), (int, float)) and isinstance(twin.get("ret_3Y"), (int, float)) else None
            if f.get("plan_type") == "Direct":
                plan_html = (f"<p style='margin-top:12px'><b>Direct plan.</b> Bought straight from the fund house, with no distributor commission: expense ratio "
                             f"{num(f['ter'], 2)}% a year against {num(twin['ter'], 2)}% for the <a href='{twin['_url']}'>Regular plan</a>"
                             + (f", and {pct(abs(g3), 2)} a year {'more' if g3 > 0 else 'less'} in return over the last 3 years" if g3 is not None else "") + ".</p>")
            else:
                plan_html = (f"<p style='margin-top:12px'><b>Regular plan.</b> Bought through a distributor, whose commission is part of the expense ratio: "
                             f"{num(f['ter'], 2)}% a year against {num(twin['ter'], 2)}% for the <a href='{twin['_url']}'>Direct plan</a>"
                             + (f", a gap of {pct(abs(g3), 2)} a year in return over the last 3 years" if g3 is not None else "")
                             + ". The commission pays for advice, regular reviews and help with paperwork.</p>")
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/{slug(f['category'])}/">{e(f['category'])}</a> › {e(f['_name'])}</nav>
<div class="eyebrow" style="margin-top:18px">{e(f['category'])} · {e(f['plan_type'])} plan · Growth</div>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:8px">{e(f['_name'])} ({e(f['plan_type'])})</h1>
<p class="muted" style="margin-top:8px"><a href="/mutual-funds/amc/{slug(f.get('amc') or 'Other')}/">{e(f.get('amc', ''))}</a> · {'benchmark: the median arbitrage fund' if arb and not f.get('benchmark') else ('benchmark: ' + e(BL)) if BL else 'benchmark ' + e(bench) + ' TRI'} · {num(f.get('age_years'), 1)} years old · AMFI code {f['code']}</p>
{f"<p class='note' style='margin-top:12px'><b>Tax:</b> {e(TAX_TEXT.get(f.get('tax'), ''))}</p>" if f.get('tax') and asset_class(f['category']) in ('Hybrid', 'Debt') else ''}
{plan_html}
<div class="row" style="margin-top:16px"><button class="btn primary" type="button" id="addCmp" data-code="{f['code']}">Add to compare</button>{twin_btn}<a class="btn" href="/#contact">Ask about this fund</a></div>
<div class="grid g2" style="margin-top:24px;align-items:stretch">
 <div class="card navbox"><div><div class="muted" style="font-size:13px">NAV on {dmy(f.get('nav_date'))}</div><div class="big">{inr2(f.get('nav_latest'))}</div></div>{day_html}<div><div class="muted" style="font-size:13px">Expense ratio</div><div class="mono" style="font-size:20px">{num(f.get('ter'), 2)}%</div>{f"<div class='muted' style='font-size:12px'>fund fee {num(f.get('ter_base'), 2)}%, the rest trading taxes and costs</div>" if arb and f.get('ter_base') is not None else ""}</div><div><div class="muted" style="font-size:13px">{aum_label(f)}</div><div class="mono" style="font-size:20px">{cr(f.get('aum_cr'))}</div></div></div>
 <div class="card row" style="gap:18px"><div>{tier_badge(f.get('tier'), True)}</div><div style="flex:1;min-width:200px"><b>Track-record rating{rate_head}</b><p class="muted" style="font-size:14px;margin-top:4px">{rate_text}</p>{cap_html}</div></div>
</div>
{review_status(f, RH.get(str(f["code"])))}
{rh_html}
<h2 style="margin-top:36px;font-size:26px">Returns against the index</h2>
<div class="tablewrap" style="margin-top:12px"><table><thead><tr><th class="l">Period</th><th>Fund</th><th>Index (TRI)</th><th>Difference</th><th>Rank by return</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="muted" style="font-size:12.5px;margin-top:8px">Growth option, point to point to {dmy(f.get('nav_date'))}; periods over a year are annualised (CAGR). Index returns use the total-return index, which includes dividends. Rank by return: among {e(f['plan_type'])} plans in {e(f.get('peer_group') or f['category'])} with a record for the whole period, by return over the index.</p>
{cat_html}
{liq_html}
{range_html}
<div class="grid g2" style="margin-top:36px;align-items:start"><div><h2 style="font-size:26px">Risk</h2><div class="kv" style="margin-top:12px">{risk}</div></div>
<div><h2 style="font-size:26px">Portfolio</h2><div style="margin-top:12px">{hold_html}</div>{flow_html}</div></div>
{more}
<p class="note" style="margin-top:32px">Data as of {dmy(as_of)}: NAVs from AMFI, index data from NSE Indices, portfolios from {e(f.get('amc', 'the fund house'))}'s monthly disclosure. Updated every weekday. Read the scheme documents before investing.</p>
</div></section>"""
        fund_ld = {"@context": "https://schema.org", "@type": "InvestmentFund", "name": f"{f['_name']} - {f['plan_type']} Plan - Growth",
                   "url": SITE + f["_url"], "category": f["category"],
                   "provider": {"@type": "Organization", "name": f.get("amc", "")},
                   "feesAndCommissionsSpecification": f"Total expense ratio {num(f.get('ter'), 2)}% a year",
                   "identifier": {"@type": "PropertyValue", "propertyID": "AMFI scheme code", "value": str(f["code"])},
                   "description": desc}
        write(f["_url"], page(title, desc, f["_url"], body,
                              (fund_ld, faq_ld, crumbs([("Mutual funds", "/mutual-funds/"), (f["category"], f"/mutual-funds/{slug(f['category'])}/"), (f["_name"], f["_url"])]))))
        urls.append((f["_url"], "daily", "0.7" if f.get("tier") in ("A+", "A", "B", "C") and asset_class(f["category"]) in ("Equity", "Hybrid") else "0.5"))

    # ---- category pages
    cat_cards = []
    for c in cats:
        L = by_cat[c]
        lc = c if c == "ELSS" else c.lower()
        reg = [f for f in L if f["plan_type"] == "Regular"]
        e3 = [f for f in reg if f.get("excess_3Y") is not None]
        beat = sum(1 for f in e3 if f["excess_3Y"] > 0)
        bench = iname(next((f.get("benchmark") for f in L if f.get("benchmark")), None))
        CBL = next((f.get("bench_label") for f in L if f.get("bench_label")), None)
        BPH = ("the median fund in their category" if CBL.startswith("the median") else f"their composite benchmark ({CBL})") if CBL else None
        path = f"/mutual-funds/{slug(c)}/"
        r3 = sorted([f for f in reg if f.get("ret_3Y") is not None], key=lambda f: f["ret_3Y"])
        gap_html = ""
        if len(r3) >= 8 and c not in ("Index Fund", "Sectoral/Thematic", "Arbitrage"):
            lo, hi = r3[0], r3[-1]
            gap = 1e6 * ((1 + hi["ret_3Y"]) ** 3 - (1 + lo["ret_3Y"]) ** 3)
            gap_html = (f"<div class='card' style='margin-top:18px'><div class='big-fig'>₹{gap / 1e5:.1f} lakh</div>"
                        f"<p style='margin-top:6px'>The difference, on ₹10 lakh invested three years ago, between the strongest {e(lc if c != 'ELSS' else c)} fund "
                        f"({pct(hi['ret_3Y'])} a year) and the weakest ({pct(lo['ret_3Y'])} a year). Same category, same SEBI rules, same market. "
                        + (f"<b>{beat} of {len(e3)}</b> funds beat {(e(BPH) if BPH else ('the ' + e(bench) + ' total-return index')) if (bench or BPH) else 'their index'} over the same period." if e3 else "")
                        + "</p><p class='muted' style='font-size:12.5px;margin-top:6px'>Regular plans, to the latest NAV. Past returns, not a forecast.</p></div>")
        grp = made_idx if c == "Index Fund" else made_thm if c == "Sectoral/Thematic" else []
        sub = ("<h2 style='font-size:24px;margin-top:30px'>" + ("By index tracked" if c == "Index Fund" else "By theme") + "</h2><div class='row' style='margin-top:12px;gap:8px;flex-wrap:wrap'>"
               + "".join(f"<a class='btn' href='{pth}'>{e(nm)} <span class='muted'>({n})</span></a>" for nm, pth, n in grp) + "</div>") if grp else ""
        tabs = ""
        arbc = c == "Arbitrage"
        if arbc:
            lq = [f for f in reg if f.get("excess_vs_liquid_post_tax_3y") is not None]
            beat_l = sum(1 for f in lq if f["excess_vs_liquid_post_tax_3y"] > 0)
            if lq:
                gap_html = (f"<div class='card' style='margin-top:18px'><div class='big-fig'>{beat_l} of {len(lq)}</div>"
                            f"<p style='margin-top:6px'>arbitrage funds (Regular plans with 3 years of history) beat the median liquid fund over 3 years <b>after tax</b> for an investor in the 30% slab. "
                            f"Before tax, {sum(1 for f in lq if (f.get('excess_vs_liquid_3y') or 0) > 0)} did.</p>"
                            "<p class='muted' style='font-size:12.5px;margin-top:6px'>Liquid-fund gains taxed at 31.2%, arbitrage gains at 13% (held over a year). Past returns, not a forecast.</p></div>")
        for plan in ("Regular", "Direct") if arbc else ():
            P = sorted([f for f in L if f["plan_type"] == plan], key=lambda f: (tord.get(f.get("tier"), 9), -(f.get("score") or -1), f["name"]))
            trs = "".join(f"<tr><td class='fund l'><a href='{f['_url']}'>{e(f['_name'])}</a><small>{e(f.get('amc', ''))} · {num(f.get('age_years'), 1)} yrs</small></td>"
                          f"<td>{tier_badge(f.get('tier'))}</td><td class='num'>{pct(f.get('ret_1Y'), 2)}</td><td class='num'>{pct(f.get('ret_3Y'), 2)}</td>"
                          f"<td class='num {'pos' if (f.get('excess_vs_liquid_post_tax_3y') or 0) > 0 else 'neg' if f.get('excess_vs_liquid_post_tax_3y') is not None else ''}'>{spct(f.get('excess_vs_liquid_post_tax_3y'), 2)}</td>"
                          f"<td class='num'>{num(f.get('ter_base'), 2)}%</td><td class='num'>{num(f.get('ter'), 2)}%</td><td class='num'>{cr(f.get('aum_cr'))}</td></tr>" for f in P)
            tabs += (f"<h2 style='font-size:24px;margin-top:32px'>{plan} plans ({len(P)})</h2><div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Fund</th><th>Rating</th><th>1Y return</th><th>3Y return</th><th>3Y vs liquid, after tax</th><th>Fund fee</th><th>Expense ratio</th><th>AUM</th></tr></thead><tbody>{trs}</tbody></table></div>")
        if arbc:
            tabs += ("<p class='muted' style='font-size:12.5px;margin-top:10px'><b>3Y vs liquid, after tax</b>: the fund's 3-year return minus the median liquid fund's, both after tax for the 30% slab. "
                     "<b>Fund fee</b>: the base expense ratio the fund house charges. <b>Expense ratio</b>: AMFI's total, which adds brokerage and statutory levies; for arbitrage funds these are mostly "
                     "securities transaction tax on their trades, already reflected in the returns.</p>")
        for plan in ("Regular", "Direct") if not arbc else ():
            P = sorted([f for f in L if f["plan_type"] == plan], key=lambda f: (tord.get(f.get("tier"), 9), -(f.get("score") or -1), f["name"]))
            trs = "".join(f"<tr><td class='fund l'><a href='{f['_url']}'>{e(f['_name'])}</a><small>{e(f.get('amc', ''))} · {num(f.get('age_years'), 1)} yrs</small></td>"
                          f"<td>{tier_badge(f.get('tier'))}</td><td class='num'>{pct(f.get('ret_3Y'))}</td><td class='num {'pos' if (f.get('excess_3Y') or 0) > 0 else 'neg' if f.get('excess_3Y') is not None else ''}'>{spct(f.get('excess_3Y'))}</td>"
                          f"<td class='num'>{num(f.get('ter'), 2)}%</td><td class='num'>{cr(f.get('aum_cr'))}</td></tr>" for f in P)
            tabs += (f"<h2 style='font-size:24px;margin-top:32px'>{plan} plans ({len(P)})</h2><div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Fund</th><th>Rating</th><th>3Y return</th><th>3Y vs index</th><th>Expense ratio</th><th>AUM</th></tr></thead><tbody>{trs}</tbody></table></div>")
        faq = [(f"What does a {lc} fund invest in?", f"SEBI requires {lc} funds to {CAT_INFO.get(c, 'follow their stated mandate')}."),
               ("Arbitrage fund or liquid fund?", "Before tax, liquid funds have usually earned a little more. Arbitrage funds are taxed as equity (12.5% on gains held over a year, beyond ₹1.25 lakh), liquid funds at your slab rate, so for investors in the higher slabs who hold for over a year, arbitrage funds have usually come out ahead after tax. Liquid funds suit money you may need within days; arbitrage funds suit a few months or more."),
               ("How are arbitrage funds rated?", "Against each other, Regular with Regular and Direct with Direct: return over the Nifty 50 Arbitrage index (rolling 1-year and 3-year), consistency (how often they stay ahead, volatility, months with a loss), the fund fee, and size, since a very small fund has fewer trades to spread its costs over. To be rated A or A+, a fund must also have beaten the median liquid fund after tax for a top-slab investor.")] if c == "Arbitrage" else [(f"What does a {lc} fund invest in?", f"SEBI requires {lc} funds to {CAT_INFO.get(c, 'follow their stated mandate')}."),
               (f"How many {lc} funds beat their index over 3 years?",
                f"{beat} of {len(e3)} {lc} funds (Regular plans with 3 years of history) beat {(BPH if BPH else ('the ' + bench + ' total-return index')) if (bench or BPH) else 'their index'} over the 3 years to {dmy(as_of)}." if e3 else "Not enough funds have 3 years of history yet."),
               ("How are these funds rated?", "Each fund is compared only with funds in its category and plan type, on its long-run return over the index, risk-adjusted return, consistency, cost and portfolio. The ratings describe the track record so far; our own backtest found they do not predict future returns.")]
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        desc = (f"All {len(L)} arbitrage mutual fund plans in India compared: track-record ratings, returns vs liquid funds before and after tax, fund fees and AUM. Updated daily.")[:300] if arbc else \
            (f"All {len(L)} {lc} mutual fund plans in India compared: track-record ratings, 3-year returns vs "
                f"{BPH if BPH else bench + ' TRI' if bench else 'their index'}, expense ratios and AUM. {beat} of {len(e3)} Regular plans beat the index over 3 years. Updated daily.")[:300]
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › {e(c)}</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">{e(c)} funds in India</h1>
<p class="lede" style="margin-top:12px">{len(L)} plans ({len(reg)} Regular, {len(L) - len(reg)} Direct), rated on their track record against {(e(BPH) if BPH else ('the ' + e(bench) + ' total-return index')) if (bench or BPH) else ('the median arbitrage fund' if arbc else 'their index')}{', liquid funds' if arbc else ''} and their peers. Data as of {dmy(as_of)}.</p>
<p style="margin-top:14px">{e(CAT_PITCH.get(c, ''))} SEBI requires {e(c if c == 'ELSS' else lc)} funds to {e(CAT_INFO.get(c, 'follow their stated mandate'))}.</p>
{gap_html}
<div class="row" style="margin-top:16px"><a class="btn primary" href="/?cat={e(c)}#ratings">Sort and filter interactively</a><a class="btn" href="/#compare">Compare funds</a></div>
{sub}{tabs}
<h2 style="font-size:24px;margin-top:36px">Common questions</h2>{''.join(f'<details class="faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)}
<p class="note" style="margin-top:28px">Ratings describe past track records and are not a recommendation to buy or sell. Read the scheme documents before investing.</p>
</div></section>"""
        write(path, page(f"{c} mutual funds: top-rated by track record, {mon(as_of[:7]) if as_of else ''}".replace("Index Fund mutual funds", "Index funds").replace("Sectoral/Thematic mutual funds", "Sectoral and thematic funds") + " | Aeterna Wealth", desc, path, body,
                         (faq_ld, crumbs([("Mutual funds", "/mutual-funds/"), (c, path)]))))
        urls.append((path, "daily", "0.8"))
        sub_line = (f"{len(L)} plans · {beat_l} of {len(lq)} beat liquid funds after tax over 3Y" if arbc and lq else
                    f"{len(L)} plans · {beat} of {len(e3)} beat the index over 3Y" if e3 and not arbc else f"{len(L)} plans")
        cat_cards.append((asset_class(c), f"<a class='card stack sol' href='{path}' style='gap:6px;text-decoration:none;color:inherit'><b style='font:500 18px var(--f-display)'>{e(c)}</b><span class='muted' style='font-size:14px'>{sub_line}</span></a>"))

    hub_sections = ""
    for ac, blurb in ASSET_CLASSES:
        cards = [h for a, h in cat_cards if a == ac]
        n_ac = sum(1 for f in funds if asset_class(f["category"]) == ac)
        cnt = f" <span class='muted' style='font-size:16px;font-weight:400'>{n_ac:,} plans</span>" if n_ac else ""
        hub_sections += (f"<h2 id='{ac.lower()}' style='font-size:28px;margin-top:34px'>{ac} funds{cnt}</h2>"
                         f"<p class='muted' style='margin-top:6px'>{e(blurb)}</p>"
                         + (f"<div class='grid g3' style='margin-top:16px'>{''.join(cards)}</div>" if cards else ""))
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<h1 style="font-size:clamp(30px,4vw,44px)">Mutual funds in India, compared</h1>
<p class="lede" style="margin-top:12px">{len(funds):,} plans in {len(cats)} categories, each measured against the right yardstick and against its peers: returns, risk, cost, holdings and a track-record rating. Built from AMFI, NSE Indices and fund-house data, refreshed every weekday; data as of {dmy(as_of)}.</p>
{hub_sections}
<div class="card row" style="margin-top:26px;justify-content:space-between;gap:14px;flex-wrap:wrap"><div><b style="font:500 18px var(--f-display)">Rather have us choose for you?</b><p class="muted" style="margin:4px 0 0;font-size:14px">We use this data to pick a small set of funds for your goals and review them every year.</p></div><a class="btn primary" href="/invest/mutual-funds/">Mutual fund investing with Aeterna</a></div>
<p style="margin-top:24px">Also: <a href="/mutual-funds/amc/">funds by fund house</a> · <a href="/mutual-funds/index-fund/">index funds by index</a> · <a href="/insights/">insights</a> · <a href="/calculators/">calculators</a></p>
<p class="muted" style="margin-top:10px">Prefer a spreadsheet? Download <a href="/data/funds.csv">all funds as CSV</a>. See <a href="/#method">how the ratings work</a>.</p>
</div></section>"""
    write("/mutual-funds/", page("Every mutual fund in India compared: ratings, returns and costs | Aeterna Wealth",
                                 f"Compare {len(funds):,} Indian mutual fund plans, equity, index and arbitrage funds: track-record ratings, returns vs the right yardstick, risk, expense ratios and holdings. Updated every weekday.",
                                 "/mutual-funds/", body, (crumbs([("Mutual funds", "/mutual-funds/")]),)))

    # ---- the app (home page) with full head
    home_desc = ("Wealth management for families across India: mutual funds, PMS, AIFs, bonds, unlisted shares and tax-aware "
                 "planning. Open fund data and track-record ratings for every Indian equity fund. AMFI-registered MFD, ARN-317889.")
    site_ld = {"@context": "https://schema.org", "@type": "WebSite", "@id": SITE + "/#website", "name": "Aeterna Wealth", "url": SITE + "/",
               "publisher": {"@id": SITE + "/#org"},
               "potentialAction": {"@type": "SearchAction", "target": {"@type": "EntryPoint", "urlTemplate": SITE + "/?q={search_term_string}"},
                                   "query-input": "required name=search_term_string"}}
    app_body = app.replace('<title>Aeterna Wealth</title>', '', 1)
    app_body = re.sub(r'<meta name="description"[^>]*>', '', app_body, count=1)
    index = ('<!doctype html>\n<html lang="en-IN" data-theme="light"><head>'
             + head("Aeterna Wealth: mutual funds, PMS, AIFs, bonds, unlisted shares", home_desc, "/", (ORG_LD, site_ld))
             + '<style>:root{padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}[hidden]{display:none!important}img{max-width:100%}</style>'
             + '</head><body>\n' + app_body
             + '\n</body></html>\n')
    (DIST / "index.html").write_text(index, encoding="utf-8")

    # ---- data for the app + open data
    for fp in (S / "data").rglob("*.json"):
        dst = DIST / "data" / fp.relative_to(S / "data")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(fp, dst)
    cols = ["code", "name", "amc", "category", "plan_type", "benchmark", "tier", "score", "peer_rank", "peer_count", "nav_latest", "nav_date",
            "ter", "aum_cr", "ret_6M", "ret_1Y", "ret_3Y", "ret_5Y", "excess_1Y", "excess_3Y", "excess_5Y", "max_drawdown_5y",
            "upside_capture_3y", "downside_capture_3y", "info_ratio_3y", "alpha_3y"]
    with open(DIST / "data" / "funds.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols + ["url"])
        for f in funds:
            w.writerow([f.get(c, "") for c in cols] + [SITE + f["_url"]])

    # ---- sitemap, robots, llms
    today = str(date.today())
    (DIST / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{as_of or today}</lastmod><changefreq>{cf}</changefreq><priority>{pr}</priority></url>\n" for u, cf, pr in urls)
                                      + "</urlset>\n", encoding="utf-8")
    (DIST / "robots.txt").write_text(
        "User-agent: *\nDisallow: /\n" if not LAUNCHED else
        "User-agent: *\nAllow: /\n\n# Search engines and AI assistants are welcome to read and cite the fund data\n"
        + "".join(f"User-agent: {b}\nAllow: /\n" for b in ["Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-Web",
                                                             "PerplexityBot", "Google-Extended", "Applebot", "Applebot-Extended", "CCBot", "DuckDuckBot"])
        + f"\nSitemap: {SITE}/sitemap.xml\n")
    about = (f"> {ORG['name']} (Aeterna Wealth) is a wealth management firm in New Delhi, India, working with families across India on "
             "mutual funds, portfolio management services (PMS), alternative investment funds (AIFs), bonds, unlisted shares and tax-aware "
             f"planning. It is an AMFI-registered mutual fund distributor ({ORG['arn']}); it is not a SEBI-registered investment adviser "
             "and does not advise on individual listed shares. Its website compares every Indian equity and index mutual fund using public data from AMFI, NSE Indices and fund houses: track-record ratings, returns against "
             "total-return indices, risk, costs and holdings for every Indian equity and index mutual fund, updated every weekday. "
             "Ratings describe past track records and are not forecasts or investment advice.")
    links = "\n".join(f"- [{c} funds]({SITE}/mutual-funds/{slug(c)}/)" for c in cats)
    llms = (f"# Aeterna Wealth\n\n{about}\n\nContact: {ORG['phone']} · {ORG['email']} · {ORG['street']}, {ORG['city']} {ORG['pin']}\n"
            + ("Profiles: " + ", ".join(SOCIAL) + "\n" if SOCIAL else "")
            + f"\n## Fund data\n- [All categories]({SITE}/mutual-funds/)\n{links}\n\n## Downloadable data\n- [All funds, latest metrics (CSV)]({SITE}/data/funds.csv)\n"
            f"- [All funds (JSON)]({SITE}/data/funds.json)\n- [Data dates and sources (JSON)]({SITE}/data/meta.json)\n- [This month's insights (JSON)]({SITE}/data/insights.json)\n\n"
            f"## Tools and guides\n- [Calculators: SIP, lump sum, goal, SWP, EMI, inflation, capital-gains tax]({SITE}/calculators/)\n- [Fund houses]({SITE}/mutual-funds/amc/)\n- [Insights]({SITE}/insights/)\n\n"
            f"## More\n- [Full text for language models]({SITE}/llms-full.txt)\n- [Method and backtest]({SITE}/#method)\n- [Disclosures]({SITE}/disclosures/)\n- [Privacy]({SITE}/privacy/)\n")
    (DIST / "llms.txt").write_text(llms, encoding="utf-8")
    full = [f"# Aeterna Wealth: full reference\n\n{about}\n",
            "## How the ratings work\nFunds are compared only within their SEBI category and plan type (Regular with Regular, Direct with Direct), "
            "against the total-return version of the category benchmark. Pillars: long-run excess return over the index (25%), risk-adjusted "
            "return: information ratio, capture ratio and Jensen's alpha (35%), consistency (20%), cost (10%) and portfolio: active share, SEBI "
            "mandate fit, cash and turnover (10%). Tiers: A+ = top 10% of a peer group with a score of at least 70; A = top 30% with at least 55; "
            "then B and C. An equity fund off its SEBI mandate in two consecutive monthly portfolios is rated one step lower; persistent underperformers at C. "
            "A 2019-2025 backtest found the ratings did not predict the next three years' returns, so they are presented as track-record "
            "assessments, not forecasts.\n",
            f"## Data sources and schedule\nNAVs: AMFI (daily). Index data: NSE Indices total-return indices (daily). Expense ratios, AUM and "
            f"market-cap classes: AMFI. Holdings: each fund house's monthly portfolio disclosure (refreshed on the 11th and 16th). Latest data: {dmy(as_of)}.\n",
            "## Categories\n"]
    for c in cats:
        L = by_cat[c]
        reg = [f for f in L if f["plan_type"] == "Regular" and f.get("excess_3Y") is not None]
        beat = sum(1 for f in reg if f["excess_3Y"] > 0)
        top = sorted([f for f in L if f["plan_type"] == "Regular" and f.get("score") is not None], key=lambda f: -f["score"])[:5]
        full.append(f"### {c}\nSEBI rule: {CAT_INFO.get(c, '')}. {len(L)} plans. Over 3 years, {beat} of {len(reg)} Regular plans beat the index. "
                    f"Highest track-record scores (Regular plans; not a recommendation): "
                    + "; ".join(f"{f['_name']} ({f['tier']}, 3Y {pct(f.get('ret_3Y'))} vs index {spct(f.get('excess_3Y'))})" for f in top)
                    + f". Page: {SITE}/mutual-funds/{slug(c)}/\n")
    if ins.get("items"):
        full.append("## This month in numbers\n" + "\n".join(f"- {i['title']}: {i['text']}" for i in ins["items"]) + "\n")
    full.append(f"## Disclosures\nMutual fund investments are subject to market risks; read all scheme-related documents carefully. {ORG['name']} "
                f"earns commission from asset management companies on Regular plans; Direct plans cost less and pay no commission.\n")
    (DIST / "llms-full.txt").write_text("\n".join(full), encoding="utf-8")

    # ---- portfolio check: the visitor's funds, their ratings and what the review rule says
    write("/portfolio-check/", page("Check your mutual fund portfolio | Aeterna Wealth",
        "Add the funds you hold and see each one's rating in its category, what our review rule says, and where your funds overlap.", "/portfolio-check/",
        PC_HTML))

    # ---- client note on the November 2026 ratings change
    write("/ratings-update/", page("Our fund ratings changed in November 2026 | Aeterna Wealth",
        "Why some well-known equity funds now have a lower rating, and what it means if you hold one.", "/ratings-update/",
        "<section class='band'><div class='wrap prose' style='max-width:760px'>"
        "<p class='eyebrow'>Note for clients · November 2026</p><h1>Our fund ratings changed this month</h1>"
        "<p class='lede' style='margin-top:12px'>If a fund you hold now shows a lower rating, there is nothing you need to do today. Here is what changed and why.</p>"
        "<h2>What changed</h2><p>We tested about 40 ways of rating equity funds on eleven years of real data, with the same code that rates funds on this site, "
        "and kept the one whose top-rated funds most often went on to beat their index. Ratings are now set by score: A+ at 75 out of 100 or more, A at 65 or more, "
        "so a category can have several A+ funds, or none in a given month.</p>"
        "<h2>Why some well-known funds moved down</h2><p>The ratings favour funds that have been ahead of their index in recent months and that keep up when the market rises. "
        "Several large, long-established funds have trailed their index lately, so they rank lower for now. A lower rating describes the recent record against the index. "
        "It is not a view on the fund house, and ratings change month to month.</p>"
        "<h2>If you hold a fund now rated B or C</h2><ul>"
        "<li>No action is needed today. Under our review rule a fund comes up for review only after it has been rated below A for 12 months, by when the exit load has ended in almost every equity fund.</li>"
        "<li>For ELSS funds, a review applies only after the 3-year lock-in.</li>"
        "<li>Before any switch we weigh the tax on your gain and your own plan. We go through this with you in your review.</li></ul>"
        "<h2>New investments</h2><p>Under the same rule, new money in a category goes to the funds rated A+ in that category at the time.</p>"
        "<h2>What the ratings cannot do</h2><p>Ratings describe the past and are not a forecast. In years when large companies lead the market, "
        "funds rated on recent strength have done no better than the rest. We publish these limits, and the full test results, on the "
        "<a href='/#method'>Method page</a>.</p>"
        "<p style='margin-top:20px'><a class='btn' href='/#contact'>Talk to us about your funds</a></p>"
        "<p class='muted' style='font-size:12.5px;margin-top:24px'>Aeterna Wealth is an AMFI-registered mutual fund distributor (ARN-317889), not an investment adviser. "
        "We earn commission from fund houses on Regular plans. Mutual fund investments are subject to market risks; read all scheme-related documents carefully.</p>"
        "</div></section>"))

    # ---- 404 and domain
    write("/404.html", page("Page not found | Aeterna Wealth", "This page does not exist.", "/404.html",
                            "<section class='band'><div class='wrap'><h1>Page not found</h1><p class='lede' style='margin-top:12px'>The page you asked for isn't here. "
                            "Try the <a href='/mutual-funds/'>fund categories</a>, the <a href='/#tools'>calculators</a> or the <a href='/'>home page</a>.</p></div></section>"))
    (DIST / "CNAME").write_text("aeternawealth.com\n")
    (DIST / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY, encoding="utf-8")
    # 301s from the old WordPress site's genuine pages, so any ranking they earned carries over
    # (its ~1,760 injected spam pages are deliberately left to 404 so search engines drop them)
    old = {"/about-us/": "/#about", "/services/": "/invest/", "/offerings/": "/invest/", "/blogs/": "/insights/", "/resources/": "/calculators/",
           "/contact-us/": "/#contact", "/thankyou-page/": "/", "/sip/": "/calculators/sip/", "/lumpsum/": "/calculators/lumpsum/",
           "/terms-conditions/": "/terms/", "/privacy-policy-2/": "/privacy/", "/pms/": "/invest/pms/", "/aif/": "/invest/aif/",
           "/debt-products/": "/invest/bonds/", "/loan-against-mf/": "/invest/mutual-funds/", "/succession-planning/": "/invest/",
           "/taxation-services/": "/invest/tax-planning/", "/the-magic-of-compounding-let-your-money-work-for-you/": "/calculators/sip/",
           "/mitigating-short-term-market-volatility/": "/insights/", "/tax-efficient-strategies-for-long-term-growth/": "/invest/tax-planning/",
           "/category/blog/": "/insights/", "/wp-sitemap.xml": "/sitemap.xml", "/sitemap_index.xml": "/sitemap.xml"}
    (DIST / "_redirects").write_text("".join(f"{a} {b} 301\n{a.rstrip('/')} {b} 301\n" if a.endswith("/") else f"{a} {b} 301\n" for a, b in old.items()), encoding="utf-8")
    csp = ("default-src 'self'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com https://www.googletagmanager.com; "
           "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; "
           "img-src 'self' data: https://*.google-analytics.com https://www.googletagmanager.com https://stats.g.doubleclick.net https://www.google.com https://www.google.co.in; "
           "connect-src 'self' https://cloudflareinsights.com https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://stats.g.doubleclick.net https://www.google.com; "
           "frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests")
    (DIST / "_headers").write_text(
        "/*\n"
        f"  Content-Security-Policy: {csp}\n"
        "  X-Frame-Options: DENY\n"
        "  X-Content-Type-Options: nosniff\n"
        "  Referrer-Policy: strict-origin-when-cross-origin\n"
        "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()\n"
        "  Strict-Transport-Security: max-age=31536000; includeSubDomains\n"
        "  Cross-Origin-Opener-Policy: same-origin\n"
        "/assets/*\n  Cache-Control: public, max-age=3600\n"
        "/data/*\n  Cache-Control: public, max-age=300\n"
        "/og.png\n  Cache-Control: public, max-age=86400\n", encoding="utf-8")
    print(f"built {DIST}: {len(funds)} fund pages, {len(cats)} categories, {len(urls)} URLs in sitemap, launched={LAUNCHED}")


if __name__ == "__main__":
    main()
