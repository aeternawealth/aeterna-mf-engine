"""About, Method and Contact as real pages (/about/, /method/, /contact/).

Until Nov 2026 these lived only as views inside the home page (#about, #method, #contact), which search engines treat as
the home page itself. Google weighs who runs a money site, how its numbers are made and how to reach it, so each gets its
own URL. Facts only: the founders, registration, office and the published test results (site/model_backtest.json).
"""
import json

FOUNDERS = [
    ("CA Harshit Aggarwal", "Co-founder · Chartered Accountant", "https://www.linkedin.com/in/harshit-aggarwal/", ""),
    ("Adv. Shantnu Singh Sangwan", "Co-founder · Advocate", "https://www.linkedin.com/in/shantnusangwan/", ""),
]
SOCIAL = [("LinkedIn", "https://www.linkedin.com/company/aeterna-wealth"), ("Instagram", "https://www.instagram.com/aeternawealth/"),
          ("X", "https://x.com/AeternaWealth")]

CSS = ("<style>.tp-sec{display:grid;grid-template-columns:260px minmax(0,1fr);gap:40px;padding:28px 0;border-top:1px solid var(--rule)}"
       ".tp-sec h2{font-size:22px;margin:0}.tp-sec .body{display:grid;gap:12px;min-width:0}"
       ".tp-facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:24px}"
       ".tp-facts div{background:var(--surface);border:1px solid var(--rule);border-radius:var(--r);padding:14px 16px}"
       ".tp-facts b{display:block;font:600 21px var(--f-mono);color:var(--ink)}.tp-facts span{font-size:13px;color:var(--ink-3)}"
       ".tp-people{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}"
       ".tp-cards{display:grid;gap:12px}.tp-cards .card b{font-weight:500}"
       "table.tp td,table.tp th{white-space:normal;vertical-align:top}@media (max-width:600px){table.tp td,table.tp th{padding:8px 5px;font-size:13px}}"
       "@media (max-width:820px){.tp-sec{grid-template-columns:1fr;gap:10px}.tp-facts{grid-template-columns:repeat(2,minmax(0,1fr))}.tp-people{grid-template-columns:1fr}}</style>")


def _sec(B, title, body):
    return f"<div class='tp-sec'><h2>{B.e(title)}</h2><div class='body'>{body}</div></div>"


def _social(B):
    return " · ".join(f"<a href='{u}' target='_blank' rel='noopener me'>{n}</a>" for n, u in SOCIAL)


def about(B, funds, urls):
    O = B.ORG
    people = "".join(
        f"<div class='card stack' style='gap:6px'><b style='font:500 19px var(--f-display)'>{B.e(n)}</b><span class='muted'>{B.e(r)}</span>"
        + (f"<p style='font-size:15px'>{B.e(d)}</p>" if d else "") + f"<a href='{u}' target='_blank' rel='noopener'>LinkedIn profile</a></div>" for n, r, u, d in FOUNDERS)
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">{CSS}
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/">Home</a> › About</nav>
<h1 style="font-size:clamp(32px,4.4vw,48px);margin-top:14px">A wealth partner that shows its working</h1>
<p class="lede" style="margin-top:14px">{B.e(O['name'])} is an AMFI-registered mutual fund distributor ({O['arn']}) in New Delhi, working with families
across India. We help them invest through mutual funds, portfolio management services (PMS), alternative investment funds (AIFs), bonds and
unlisted shares, with tax planned in from the start.</p>
<div class="tp-facts"><div><b>{len(funds):,}</b><span>fund plans measured every weekday</span></div><div><b>{O['arn']}</b><span>AMFI-registered distributor</span></div>
<div><b>CA + Advocate</b><span>founding team for tax and paperwork</span></div><div><b>New Delhi</b><span>Safdarjung Enclave office</span></div></div>
{_sec(B, "Who we are", f"<p>Aeterna was founded by a Chartered Accountant and a practising advocate. That mix shapes how we work: tax and paperwork are part of investing, not an afterthought.</p><div class='tp-people'>{people}</div>")}
{_sec(B, "What we believe", "<p>Good active funds can earn their place in a portfolio, and the way to find them is to measure every fund against the index it is meant to beat and against the funds it competes with, after all its costs. We build that measurement ourselves, publish it on this site for anyone to use, and use the same numbers with our clients.</p><p>A rating describes a fund's record. It is not a forecast, so we pair it with a simple discipline: new money goes to the strongest funds in each category, and a fund is reviewed, not dropped in a panic, when its record slips.</p>")}
{_sec(B, "How we work", "<ol style='padding-left:20px;display:grid;gap:8px'><li><b>Start with the plan:</b> goals, time frames and how much risk you can sit through, before any fund is named.</li><li><b>Choose with the numbers:</b> each category in your plan is filled from the funds with the strongest records, one fund house per fund so no single house dominates.</li><li><b>Review twice a month:</b> ratings are revised on the 11th and 16th, after fund houses publish their portfolios. We tell you when something you hold needs a look, and why.</li><li><b>Mind the tax:</b> switches are timed around exit loads, the one-year mark and the yearly ₹1.25 lakh tax-free limit on long-term gains.</li></ol><p>We do not sell ULIPs.</p>")}
{_sec(B, "How we are paid", f"<p>As a mutual fund distributor, we earn commission from fund houses on Regular plans. It is included in the plan's expense ratio and shown on your account statement; you pay us no separate fee.</p><p><a href='/disclosures/'>Our disclosures</a> · <a href='/method/'>How our ratings work</a></p>")}
{_sec(B, "Find us", f"<p>{B.e(O['street'])}, {B.e(O['city'])} {O['pin']}<br>Phone and WhatsApp: <a href='tel:{O['phone'].replace('-', '')}'>{B.e(O['phone'])}</a> · Email: <a href='mailto:{O['email']}'>{O['email']}</a></p><p>{_social(B)}</p>")}
<div class="row" style="margin-top:22px"><a class="btn primary" href="/contact/">Talk to us</a><a class="btn" href="/invest/portfolio-review/">Free portfolio review</a><a class="btn" href="/invest/">What we offer</a></div>
</div></section>"""
    ld = {"@context": "https://schema.org", "@type": "AboutPage", "url": B.SITE + "/about/", "name": "About Aeterna Wealth",
          "mainEntity": {"@id": B.SITE + "/#org"},
          "about": [{"@type": "Person", "name": n, "jobTitle": r.split("· ")[-1], "sameAs": [u], "worksFor": {"@id": B.SITE + "/#org"}} for n, r, u, _ in FOUNDERS]}
    B.write("/about/", B.page("About Aeterna Wealth: who we are and how we work",
                              f"Aeterna Wealth is an AMFI-registered mutual fund distributor ({O['arn']}) in New Delhi, founded by a Chartered Accountant and an advocate. How we choose funds, how we are paid, and how to reach us.",
                              "/about/", body, (ld, B.crumbs([("About", "/about/")]))))
    urls.append(("/about/", "monthly", "0.7"))


def method(B, urls):
    S = B.S
    p = S / "model_backtest.json"
    bt = json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    pc = lambda v: "–" if v is None else f"{round(v * 100)}%"
    rows, aplus, allf = "", [], []
    if bt:
        for c, d in bt["categories"].items():
            P = d["post"]
            aplus.append(P["tiers"].get("A+")); allf.append(P.get("all_1y"))
            rows += (f"<tr><td class='l'>{B.e(c)}<small class='muted' style='display:block;font-size:12px'>{B.e(d['model'])} model</small></td>"
                     + "".join(f"<td class='num'>{pc(P['tiers'].get(t))}</td>" for t in ("A+", "A", "B", "C"))
                     + f"<td class='num'>{pc(P.get('all_1y'))}</td></tr>")
    avg = lambda L: sum(x for x in L if x is not None) / max(1, len([x for x in L if x is not None]))
    test = ""
    if rows:
        test = (f"<p>For every month from 2012 to October 2025 we rated each category using only what was known on that date, with the same code that rates funds today, "
                f"including funds that later closed or merged, and then looked at what happened next. Since COVID ({B.e(bt['periods']['post'])}), on average "
                f"<b>{pc(avg(aplus))}</b> of A+ funds beat their index over the following year, against <b>{pc(avg(allf))}</b> of all funds.</p>"
                "<div class='tablewrap'><table class='tp'><thead><tr><th class='l'>Category</th><th>A+</th><th>A</th><th>B</th><th>C</th><th>All</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div><p class='muted' style='font-size:13px'>Share of funds ahead of their index over the next year, by rating, {B.e(bt['periods']['post'])}; "
                f"{B.e(bt.get('plans') or 'Regular and Direct')} plans. The models were chosen after seeing this history, so these figures flatter them a little. "
                "In years when large caps led the market, A+ funds in several categories trailed their index. These are odds from past data, not promises.</p>")
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">{CSS}
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/">Home</a> › Method</nav>
<h1 style="font-size:clamp(30px,4.2vw,46px);margin-top:14px">How we rate mutual funds, and how well it has worked</h1>
<p class="lede" style="margin-top:14px">Every rating on this site is computed from public data with rules we publish here, including where they fall short.
Equity, hybrid and debt funds do different jobs, so each family is measured on what matters for its job.</p>
{_sec(B, "The rules for every fund", "<ul style='padding-left:20px;display:grid;gap:8px'><li><b>Like with like.</b> Each fund is compared only with funds of the same SEBI category and plan type: Regular with Regular, Direct with Direct.</li><li><b>The right yardstick.</b> Equity funds against their category's total-return index (which includes dividends); hybrid funds against a blend of equity and bond yardsticks; debt funds against the median fund of their category.</li><li><b>After costs.</b> Every return is taken from the NAV, which is already net of the fund's expenses.</li><li><b>Enough history.</b> Three years to be rated (one year for index, overnight, liquid and money-market funds). Younger funds show as unrated.</li><li><b>Portfolio checks.</b> A fund whose portfolio breaks its SEBI category rules in two consecutive months moves one rating lower, and its page says why.</li></ul>")}
{_sec(B, "What is measured", "<p><b>Equity funds</b> use a model chosen for each category from about 40 tested: mostly recent return over the index (1 to 12 months), how much of the market's rises a fund captures, and its lean towards the part of the market its category allows. Focused funds add conviction (how far they stray from the index); multi-cap funds average three views including defence in falls. When a category's index is below its 200-day average, half the score switches to the traits of funds that rebound first after a fall.</p><p><b>Hybrid funds</b> are rated on return over their composite yardstick, protection in falls and consistency. <b>Debt funds</b> on return over their category median, consistency and how they behaved on bad days. <b>Arbitrage funds</b> must also beat the median liquid fund after tax to be rated A or A+.</p>")}
{_sec(B, "Ratings", "<div class='tablewrap'><table class='tp'><thead><tr><th class='l'>Rating</th><th class='l'>Equity funds</th><th class='l'>Hybrid, debt and index funds</th></tr></thead><tbody><tr><td class='l'><b>A+</b></td><td class='l'>Score of 75 or more out of 100</td><td class='l'>Top 10%, score 70+, ahead of its yardstick over 3 years and in its median 3-year window</td></tr><tr><td class='l'><b>A</b></td><td class='l'>Score of 65 or more</td><td class='l'>Top 30%, score 55+, ahead on at least one of the two</td></tr><tr><td class='l'><b>B</b></td><td class='l'>The middle of the group</td><td class='l'>The middle of the group</td></tr><tr><td class='l'><b>C</b></td><td class='l'>The bottom 30% (below 65)</td><td class='l'>The bottom 30%, or held back by a red flag</td></tr></tbody></table></div><p>A qualitative flag, such as a fund manager leaving, a merger or SEBI action, turns A and A+ into Watch.</p>")}
{_sec(B, "Did it work?", test or "<p>The category-by-category test is published with each model update.</p>")}
{_sec(B, "When ratings change", "<p>Ratings are revised on the 11th of each month, once fund houses have published the previous month's portfolios (due by the 10th), and again on the 16th for late portfolios. Between those dates the site updates every weekday morning with the latest NAVs, returns and period rankings, while ratings stay as last set.</p>")}
{_sec(B, "Data and limits", "<p>Data comes from AMFI (NAVs, expense ratios, AUM, market-cap lists), NSE Indices (total-return indices) and fund houses' monthly portfolio disclosures. Fund manager changes are not yet tracked automatically; debt funds are rated on their NAVs, not yet on the credit quality of the bonds they hold.</p><p>Ratings describe a fund's past record and are not a forecast or a recommendation to buy or sell. <a href='/disclosures/'>Disclosures</a></p>")}
<div class="row" style="margin-top:22px"><a class="btn primary" href="/mutual-funds/">See the ratings</a><a class="btn" href="/?#method">Interactive version with every category</a><a class="btn" href="/invest/portfolio-review/">Free portfolio review</a></div>
</div></section>"""
    B.write("/method/", B.page("How we rate mutual funds: method and backtest | Aeterna Wealth",
                               "How Aeterna Wealth rates every Indian mutual fund: like-with-like peer groups, the right index, returns after costs, a model per category, and a published test of how A+ funds did next.",
                               "/method/", body, (B.crumbs([("Method", "/method/")]),)))
    urls.append(("/method/", "monthly", "0.7"))


def contact(B, urls):
    O = B.ORG
    tel = O["phone"].replace("-", "")
    cards = "".join(f"<div class='card'><div class='muted' style='font-size:13px'>{k}</div><div style='margin-top:4px'><b>{v}</b></div></div>" for k, v in (
        ("Phone and WhatsApp", f"<a href='tel:{tel}'>{B.e(O['phone'])}</a>"), ("Email", f"<a href='mailto:{O['email']}'>{O['email']}</a>"),
        ("Office", B.e(f"{O['street']}, {O['city']} {O['pin']}"))))
    form = ("<form class='card stack' id='tpform' style='gap:14px'>"
            "<label class='field'><span>Name</span><input id='tn' required autocomplete='name'></label>"
            "<label class='field'><span>What are you planning for?</span><select id='tg'><option>Growing my wealth</option><option>Retirement</option><option>Children's education</option>"
            "<option>Buying a home</option><option>Regular income</option><option>Saving tax</option><option>Reviewing what I already hold</option><option>Something else</option></select></label>"
            "<label class='field'><span>Roughly how much?</span><select id='ta'><option>Not sure yet</option><option>A monthly SIP</option><option>Under ₹10 lakh</option><option>₹10–50 lakh</option>"
            "<option>₹50 lakh–₹1 crore</option><option>₹1–5 crore</option><option>Above ₹5 crore</option></select></label>"
            "<label class='field'><span>Anything else? (optional)</span><textarea id='tm' rows='3'></textarea></label>"
            "<button class='btn primary' type='submit' style='justify-content:center'>Continue on WhatsApp</button>"
            f"<p class='muted' style='font-size:12.5px'>Opens WhatsApp with your message ready to send to {B.e(O['phone'])}. Nothing is stored on this site.</p></form>"
            "<script>document.getElementById('tpform').onsubmit=function(e){e.preventDefault();var g=function(i){return document.getElementById(i).value.trim()};"
            "var t=['Hello Aeterna, I\\'m '+g('tn')+'.','Planning for: '+g('tg')+'.','Amount: '+g('ta')+'.',g('tm')].filter(Boolean).join('\\n');"
            "window.open('https://wa.me/" + B.WA + "?text='+encodeURIComponent(t),'_blank','noopener')}</script>")
    body = f"""<section class="band" style="padding-top:28px"><div class="wrap">{CSS}
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/">Home</a> › Contact</nav>
<h1 style="font-size:clamp(30px,4vw,44px);margin-top:14px">Talk to us</h1>
<p class="lede" style="margin-top:12px">Tell us a little about what you're planning. We reply within one working day, usually on WhatsApp.</p>
<div class="grid g2" style="margin-top:24px;align-items:start">{form}<div class="tp-cards">{cards}
<div class="card"><div class="muted" style="font-size:13px">Already a client?</div><div class="row" style="justify-content:space-between;margin-top:6px"><b>Holdings and statements</b><a class="btn" href="https://onedigital.centricity.co.in/" target="_blank" rel="noopener">Client login</a></div></div>
<div class="card"><div class="muted" style="font-size:13px">Follow us</div><div style="margin-top:6px">{_social(B)}</div></div></div></div>
<p style="margin-top:24px"><a href="/invest/portfolio-review/">Get a free review of the funds you hold</a> · <a href="/about/">About us</a> · <a href="/disclosures/">Disclosures</a></p>
</div></section>"""
    ld = {"@context": "https://schema.org", "@type": "ContactPage", "url": B.SITE + "/contact/", "name": "Contact Aeterna Wealth", "mainEntity": {"@id": B.SITE + "/#org"}}
    B.write("/contact/", B.page("Contact Aeterna Wealth: phone, WhatsApp and office in New Delhi",
                                f"Talk to Aeterna Wealth, AMFI-registered mutual fund distributor ({O['arn']}): phone and WhatsApp {O['phone']}, email, and our office in Safdarjung Enclave, New Delhi.",
                                "/contact/", body, (ld, B.crumbs([("Contact", "/contact/")]))))
    urls.append(("/contact/", "monthly", "0.6"))


def trust_pages(B, funds, urls):
    about(B, funds, urls)
    method(B, urls)
    contact(B, urls)
