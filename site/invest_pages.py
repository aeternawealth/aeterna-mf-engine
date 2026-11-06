"""Static pages for each service in the Invest menu (/invest/<slug>/) and the /invest/ hub.
Each page: what it is, who it suits, costs, tax, risks, how we help, common questions, and figures from our own data
where we have it. Rules and tax rates are as of the Finance (No. 2) Act 2024 and SEBI rules in force in 2026.
Called from build_site.main() with its helpers as B."""
import itertools
import re
import json
import statistics as st

PAGES = ["mutual-funds", "pms", "aif", "bonds", "unlisted-shares", "tax-planning", "portfolio-review"]
NAMES = {"mutual-funds": "Mutual funds", "pms": "PMS", "aif": "AIFs", "bonds": "Bonds", "unlisted-shares": "Unlisted shares",
         "tax-planning": "Tax planning", "portfolio-review": "Portfolio review"}

CSS = """<style>
.inv-page{max-width:none}
.inv-page .note{max-width:none}
.inv-hero{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(0,1fr);gap:40px;align-items:start}
.inv-facts{align-self:center;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);border-radius:var(--r);overflow:hidden}
.inv-facts>div{background:var(--surface);padding:16px 18px}.inv-facts b{display:block;font:600 22px/1.2 var(--f-mono);color:var(--ink);font-variant-numeric:tabular-nums}
.inv-facts span{display:block;color:var(--ink-3);font-size:13px;margin-top:4px}
.inv-sec{display:grid;grid-template-columns:300px minmax(0,1fr);gap:48px;padding:30px 0;border-top:1px solid var(--rule);align-items:start}
.inv-sec h2{font-size:22px;line-height:1.25;margin:0}.inv-sec .body{display:grid;gap:12px;min-width:0}.inv-sec .body p{margin:0}.inv-sec .faq:first-child{margin-top:0}
.inv-sec ul{margin:0;padding-left:20px;display:grid;gap:6px}
.inv-steps{list-style:none;padding:0;margin:0;display:grid;gap:14px;counter-reset:st}
.inv-steps li{display:grid;grid-template-columns:30px 1fr;column-gap:12px;counter-increment:st}
.inv-steps li::before{content:counter(st);grid-row:span 2;width:28px;height:28px;border-radius:50%;background:var(--teal-soft);color:var(--teal);font:600 14px/28px var(--f-mono);text-align:center}
.inv-steps b{font:600 16px/1.3 var(--f-display);color:var(--ink)}.inv-steps span{color:var(--ink-2)}
.inv-cta{display:flex;justify-content:space-between;align-items:center;gap:18px;flex-wrap:wrap;padding:24px;border-radius:var(--r);background:var(--teal);color:#fff;margin-top:34px}
.inv-cta h2{color:#fff;font-size:24px}.inv-cta p{margin:6px 0 0;color:rgba(255,255,255,.85)}.inv-cta .btn{background:#fff;color:var(--teal);border-color:#fff}
.inv-more{display:flex;flex-wrap:wrap;gap:8px;margin-top:22px}
@media (max-width:520px){.inv-facts b{font-size:18px}.inv-facts>div{padding:14px}}
@media (max-width:860px){.inv-hero{grid-template-columns:1fr;gap:22px}.inv-sec{grid-template-columns:1fr;gap:10px;padding:24px 0}}
</style>"""


def _overlap(h, a, b):
    A = {t[0]: t[2] for t in h.get(a, [])}
    Bm = {t[0]: t[2] for t in h.get(b, [])}
    return sum(min(A[k], Bm[k]) for k in set(A) & set(Bm))


def _data(funds, hold, ins):
    """Figures from our own data for the mutual fund and portfolio review pages."""
    d = {}
    reg = [f for f in funds if f["plan_type"] == "Regular"]
    d["plans"] = len(funds)
    d["rated"] = sum(1 for f in funds if f.get("tier") in ("A+", "A", "B", "C"))
    main = ["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap", "Flexi Cap", "Focused", "ELSS", "Value / Contra"]
    e3 = [f for f in reg if f["category"] in main and f.get("excess_3Y") is not None]
    d["beat"], d["beat_n"] = sum(f["excess_3Y"] > 0 for f in e3), len(e3)
    pairs = {}
    for f in funds:
        if f.get("ter") is not None and f.get("pair_key"):
            pairs.setdefault(f["pair_key"], {})[f["plan_type"]] = f["ter"]
    gaps = sorted(p["Regular"] - p["Direct"] for p in pairs.values() if "Regular" in p and "Direct" in p)
    d["ter_gap"] = gaps[len(gaps) // 2] if gaps else None
    gap_best = None
    for c in ["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap", "Flexi Cap", "Focused"]:
        r = sorted([f for f in reg if f["category"] == c and f.get("ret_3Y") is not None], key=lambda f: f["ret_3Y"])
        if len(r) >= 8:
            g = 1e6 * ((1 + r[-1]["ret_3Y"]) ** 3 - (1 + r[0]["ret_3Y"]) ** 3)
            if not gap_best or g > gap_best[1]:
                gap_best = (c, g)
    d["gap"] = gap_best
    items = {i["id"]: i for i in (ins or {}).get("items", [])}
    d["sip10"] = items.get("sip-10y-flexi-cap")
    d["held3"] = items.get("held-3y-large-cap")
    # overlap: five largest funds in a category, pairwise; large caps against a Nifty 50 index fund
    ov = {}
    for c in ["Large Cap", "Flexi Cap", "Mid Cap", "ELSS"]:
        D = sorted([f for f in funds if f["category"] == c and f["plan_type"] == "Direct" and f.get("aum_cr") and f.get("pair_key") in hold],
                   key=lambda f: -f["aum_cr"])[:5]
        o = [_overlap(hold, a["pair_key"], b["pair_key"]) for a, b in itertools.combinations(D, 2)]
        if o:
            ov[c] = st.median(o)
    d["overlap"] = ov
    idx = sorted([f for f in funds if f.get("peer_group") == "Index: NIFTY 50" and f["plan_type"] == "Direct" and f.get("pair_key") in hold],
                 key=lambda f: -(f.get("aum_cr") or 0))
    lc = [f for f in reg if f["category"] == "Large Cap" and f.get("pair_key") in hold]
    if idx and lc:
        d["lc_vs_idx"] = st.median(_overlap(hold, f["pair_key"], idx[0]["pair_key"]) for f in lc)
        d["lc_ter"] = st.median(f["ter"] for f in lc if f.get("ter") is not None)
        d["idx_ter"] = idx[0].get("ter")
    return d


def _fee_drag(amount, years, gross, fee):
    return amount * (1 + gross) ** years - amount * (1 + gross - fee) ** years


def _content(B, d):
    L = lambda x: f"₹{x / 1e5:.1f} lakh" if x < 1e7 else f"₹{x / 1e7:.2f} crore"
    P = lambda v, n=1: f"{v * 100:.{n}f}%"
    gap = d.get("gap")
    sip = d.get("sip10")
    ov = d.get("overlap", {})
    pms_drag = _fee_drag(5e6, 10, 0.13, 0.025) - _fee_drag(5e6, 10, 0.13, 0.01)
    return {
        "mutual-funds": dict(
            title="Mutual fund investing with Aeterna: chosen with data, reviewed every year",
            seo="Mutual fund investment services: funds chosen with data | Aeterna Wealth",
            desc="Mutual fund portfolios built and reviewed by Aeterna Wealth, an AMFI-registered distributor (ARN-317889): every equity fund in India measured against its index, overlap and cost checked, tax planned in.",
            lede="Our largest practice. We measure every equity and index fund in India against the right index every weekday, and use that to choose a small set of funds that fit your goals, don't duplicate each other and are reviewed every year.",
            facts=[(f"{d['plans']:,}", "equity and index fund plans we track"),
                   (f"{d['beat']} of {d['beat_n']}", "diversified Regular plans ahead of their index over 3 years"),
                   (L(gap[1]) if gap else "–", f"gap on ₹10 lakh between the strongest and weakest {gap[0].lower() if gap and gap[0] != 'ELSS' else 'ELSS'} fund over 3 years" if gap else ""),
                   (P(d["ter_gap"] / 100, 2) if d.get("ter_gap") is not None else "–", "typical extra yearly cost of a Regular plan over Direct")],
            sections=[
                ("Why the choice of fund matters", [
                    f"Funds in the same SEBI category follow the same rules and face the same market, yet their results spread widely. Over the last three years, ₹10 lakh in the strongest {gap[0].lower() if gap and gap[0] != 'ELSS' else 'ELSS'} fund grew to {L(gap[1])} more than the same amount in the weakest." if gap else "",
                    f"Only {d['beat']} of {d['beat_n']} diversified Regular plans beat their total-return index over three years. Picking well, and moving on from a fund that falls behind, is most of the work.",
                    (f"Patience pays too: a ₹10,000 monthly SIP in the middle-ranked flexi cap fund over the last ten years is worth about {sip['figure']} today, on ₹12 lakh put in." if sip else ""),
                ]),
                ("How we choose funds", ["ul", [
                    "Track record against the category's total-return index, over rolling 3-year windows, not one lucky period.",
                    "Risk: how a fund held up in falls, its downside capture and the range of 3-year outcomes it has delivered.",
                    "Cost: expense ratio, and whether a cheaper index fund does the same job.",
                    "Overlap: two funds that hold the same stocks add cost, not diversification.",
                    "Mandate: whether the portfolio actually follows its SEBI category rules.",
                ]], "Our method and its backtest are published on the Method page, including where the ratings fall short."),
                ("What we offer", ["ul", [
                    "Equity, hybrid, debt and index funds across fund houses.",
                    "SIPs, step-up SIPs, lump sums and systematic transfer plans (STPs) to spread a large amount in.",
                    "Goal plans: children's education, a home, retirement income through SWPs.",
                    "A yearly review, and a check-in whenever a fund you hold slips behind its peers.",
                ]]),
                ("Costs", [
                    "We are a distributor: we earn commission from fund houses on Regular plans, already included in each plan's expense ratio and shown on your Consolidated Account Statement. You pay us no separate fee.",
                    f"The Direct plan of the same fund costs less (typically {P(d['ter_gap'] / 100, 2)} a year) and pays no commission. If you would rather choose and review funds yourself, Direct is the cheaper route; with us you get the choice, the paperwork, the tax planning and the reviews." if d.get("ter_gap") is not None else "",
                ]),
                ("Tax", ["ul", [
                    "Equity funds: gains on units held more than 12 months are taxed at 12.5% above ₹1.25 lakh a year; within 12 months at 20%.",
                    "Debt funds bought from 1 April 2023: taxed at your slab rate, whatever the holding period.",
                    "ELSS funds give a deduction of up to ₹1.5 lakh under Section 80C in the old tax regime, with a 3-year lock-in.",
                    "Switching from a Regular to a Direct plan counts as a sale, so it can trigger capital-gains tax.",
                ]], None, "/calculators/capital-gains-tax/", "Capital gains tax calculator"),
            ],
            steps=[("A first conversation", "Your goals, time frame and what you already hold."),
                   ("A short list of funds", "Chosen with our data, with the reasons for each and what it costs."),
                   ("Account opening and investing", "KYC, SIPs and lump sums handled for you."),
                   ("Reviews", "Every year, or sooner when something changes.")],
            faq=[("Do you charge a fee for mutual funds?", "No separate fee. We earn commission from fund houses on Regular plans; it is part of the plan's expense ratio and appears on your account statement."),
                 ("What is the difference between Regular and Direct plans?", "They hold the same portfolio. The Regular plan includes the distributor's commission, so it costs more; the Direct plan costs less and pays no commission."),
                 ("How many funds should I hold?", "Usually 4 to 6 equity funds are enough. More funds often means more overlap, not more diversification."),
                 ("Can you review funds I bought elsewhere?", "Yes. Bring your Consolidated Account Statement and we will review everything together.")],
            links=[("/mutual-funds/", "Every fund, by category"), ("/#ratings", "Fund ratings"), ("/#compare", "Compare funds"), ("/calculators/sip/", "SIP calculator")],
        ),
        "pms": dict(
            title="Portfolio management services (PMS)",
            seo="PMS in India: how it works, fees, tax and minimum ₹50 lakh | Aeterna Wealth",
            desc="Portfolio management services explained: SEBI's ₹50 lakh minimum, discretionary and non-discretionary PMS, fees, exit loads, tax and how Aeterna Wealth compares strategies for you.",
            lede="A professional manager runs a concentrated portfolio of shares held in your own demat account. PMS can suit large portfolios that want a sharper strategy than a mutual fund, but costs and risk are higher, so the choice of manager matters even more.",
            facts=[("₹50 lakh", "SEBI minimum investment"), ("15–30", "stocks in a typical PMS strategy"),
                   ("Your name", "shares are held in your own demat account"), ("3% / 2% / 1%", "maximum exit load in years 1, 2 and 3")],
            sections=[
                ("What PMS is", [
                    "A portfolio manager registered with SEBI invests on your behalf. Unlike a mutual fund, you own the shares directly, so you see every holding and every trade, and the portfolio can be more concentrated.",
                    "Discretionary PMS: the manager decides what to buy and sell. Non-discretionary: the manager advises and acts with your approval. Most investors choose discretionary.",
                ]),
                ("Who it suits", ["ul", [
                    "Investors who can commit at least ₹50 lakh without needing it for five years or more.",
                    "Those who already have a core of mutual funds and want a concentrated strategy alongside.",
                    "People comfortable with returns that can differ sharply from the index, in both directions.",
                ]]),
                ("Costs", [
                    "Fees vary by manager: a fixed fee (often 1.5–2.5% a year), a profit share above a hurdle, or a mix. Performance fees can only be charged on a high-water-mark basis, so you don't pay twice for the same gains. Brokerage, custody and fund-accounting charges come on top.",
                    f"Costs compound. On ₹50 lakh over 10 years at an assumed 13% a year before fees, a 2.5% yearly fee leaves about {L(pms_drag)} less than a 1% fee would. A PMS has to earn that back to be worth it.",
                    "SEBI lets you invest with a portfolio manager directly, without a distributor. Through us, the manager pays us a distribution fee, and we tell you how much before you invest.",
                ]),
                ("Tax", [
                    "Because the shares are yours, every sale inside the PMS is taxed in your hands: 20% on gains within 12 months, 12.5% above ₹1.25 lakh a year after that, plus dividends at your slab. High-turnover strategies therefore cost more in tax than a mutual fund, where trades inside the fund are not taxed until you sell units.",
                ]),
                ("Risks", ["ul", [
                    "Concentration: 15–30 stocks can fall much more than a diversified fund.",
                    "Manager risk: results depend on one team; a change of manager can change the strategy.",
                    "Not guaranteed: PMS returns can be negative, and past returns may not repeat.",
                ]]),
                ("How we help", [
                    "We compare strategies on their reported returns against a standard benchmark (SEBI requires managers to report time-weighted returns against one), their worst periods, fees after tax and how much they overlap with what you already own. We read the disclosure document with you before you sign.",
                ]),
            ],
            steps=[("Your goals and current portfolio", "So the PMS adds something your mutual funds don't."),
                   ("A short list of strategies", "Compared on record, risk, fees and overlap."),
                   ("Paperwork", "Agreement, demat and bank linking with the portfolio manager."),
                   ("Monitoring", "Quarterly reports read with you, and a yearly review.")],
            faq=[("What is the minimum investment for PMS?", "₹50 lakh, set by SEBI. It can be in cash or in shares you already hold, if the manager accepts them."),
                 ("Is PMS better than mutual funds?", "Not by default. PMS is more concentrated and usually costs more; it is worth it only if the strategy adds return or diversification after those costs."),
                 ("How is PMS taxed?", "Each sale inside the portfolio is taxed in your hands as short- or long-term capital gains, as if you had traded the shares yourself."),
                 ("Can I exit a PMS early?", "Yes. SEBI caps the exit load at 3% in the first year, 2% in the second and 1% in the third; after that, none.")],
            links=[("/invest/aif/", "AIFs"), ("/invest/mutual-funds/", "Mutual funds"), ("/invest/portfolio-review/", "Portfolio review")],
        ),
        "aif": dict(
            title="Alternative investment funds (AIFs)",
            seo="AIFs in India: Category I, II, III, minimum ₹1 crore, tax | Aeterna Wealth",
            desc="Alternative investment funds explained: SEBI's Category I, II and III, the ₹1 crore minimum, drawdowns and lock-ins, fees, tax and how Aeterna Wealth helps you choose and track them.",
            lede="AIFs give access to investments a mutual fund cannot make: private companies, private credit, real estate and long-short strategies. They are for large, patient money; most lock your capital in for years.",
            facts=[("₹1 crore", "SEBI minimum for most investors"), ("3 years+", "minimum life of Category I and II funds"),
                   ("Cat I · II · III", "three SEBI categories"), ("Direct plan", "available since 2023, without a distribution fee")],
            sections=[
                ("The three categories", ["ul", [
                    "Category I: venture capital, SME, social-impact and infrastructure funds.",
                    "Category II: private equity, private credit and real-estate funds. The largest category.",
                    "Category III: hedge-fund-style strategies such as long-short equity, which can be open-ended and use leverage within limits.",
                ]]),
                ("How investing works", [
                    "Most Category I and II funds work on commitments: you commit an amount, say ₹1 crore, and the fund draws it down over two to four years as it finds investments, then returns money as it exits them. Your money can be tied up for 6 to 10 years.",
                ]),
                ("Who it suits", ["ul", [
                    "Investors who can commit at least ₹1 crore (₹25 lakh for the fund's own employees and directors; SEBI-accredited investors can go lower).",
                    "Money you will not need for the fund's whole life.",
                    "Portfolios already well diversified in listed markets.",
                ]]),
                ("Costs", [
                    "Typically a management fee of 1.5–2.5% a year on committed or invested capital and a share of profits (often 10–20%) above a hurdle rate, plus set-up and operating expenses. Since 2023 SEBI requires AIFs to offer a direct plan without a distribution fee; through us, the fund pays a distribution fee, and we tell you how much before you invest.",
                ]),
                ("Tax", ["ul", [
                    "Category I and II are pass-through: income is taxed in your hands as if you earned it directly (capital gains, interest, dividends), except business income, which the fund pays.",
                    "Category III is taxed at the fund level, often at the highest rate, so returns are reported after tax.",
                ]]),
                ("Risks", ["ul", [
                    "Illiquidity: you usually cannot exit early, and secondary sales are rare and at a discount.",
                    "Valuation: holdings are valued periodically, not daily, so reported returns can look smoother than reality.",
                    "Manager and strategy risk, and outcomes that can be negative.",
                ]]),
                ("How we help", [
                    "We compare managers on their earlier funds' realised returns, not just paper gains, and on fees, strategy and fit with your portfolio. We handle the paperwork and track capital calls, distributions and reports over the fund's life.",
                ]),
            ],
            steps=[("Your goals and liquidity needs", "How much can be locked up, and for how long."),
                   ("A short list of funds", "Compared on track record, fees and strategy."),
                   ("Documents", "Private placement memorandum, contribution agreement and KYC."),
                   ("Tracking", "Capital calls, distributions and reports over the fund's life.")],
            faq=[("What is the minimum investment in an AIF?", "₹1 crore for most investors; ₹25 lakh for the fund's employees and directors. SEBI-accredited investors can invest less."),
                 ("Can I withdraw from an AIF early?", "Usually not. Category I and II funds are close-ended with a life of at least three years, often 6 to 10."),
                 ("How are AIFs taxed?", "Category I and II pass income through to investors, taxed in their hands; Category III pays tax at the fund level."),
                 ("Are AIFs regulated?", "Yes, by SEBI under the AIF Regulations, 2012. Regulation does not make them safe; it sets disclosure and conduct rules.")],
            links=[("/invest/pms/", "PMS"), ("/invest/unlisted-shares/", "Unlisted shares"), ("/invest/portfolio-review/", "Portfolio review")],
        ),
        "bonds": dict(
            title="Bonds and fixed income",
            seo="Invest in bonds in India: corporate bonds, G-secs, yield and tax | Aeterna Wealth",
            desc="Listed bonds explained: corporate bonds, government securities, credit ratings, yield to maturity, how bond income is taxed, and how Aeterna Wealth matches bonds to your income and maturity needs.",
            lede="Bonds pay a known rate of interest and return your money on a set date, if the issuer pays. They suit money you need at a known time or as regular income, and they steady a portfolio that is mostly equity.",
            facts=[("₹10,000", "typical unit for many listed bonds"), ("AAA → D", "credit rating scale"),
                   ("Slab rate", "tax on interest"), ("12.5%", "tax on gains from listed bonds held over 12 months")],
            sections=[
                ("What you can buy", ["ul", [
                    "Government securities and treasury bills: the safest credit; you can also buy them directly through RBI Retail Direct.",
                    "State development loans: issued by state governments, usually yielding a little more.",
                    "Corporate bonds and NCDs: issued by companies and NBFCs, rated by SEBI-registered agencies. Higher yields come with higher credit risk.",
                    "Tax-free bonds, bought on the exchange from earlier issues, for investors in high tax brackets.",
                ]]),
                ("Yield, price and duration", [
                    "The yield to maturity is the return you earn if you hold to maturity and the issuer pays everything on time. When interest rates rise, existing bond prices fall, and the longer the bond, the larger the fall. Matching the bond's maturity to when you need the money removes most of that price risk.",
                ]),
                ("Who it suits", ["ul", [
                    "Retirees and families who want regular, predictable income.",
                    "Money set aside for a known date: a fee, a down payment, a loan repayment.",
                    "Equity-heavy portfolios that need a steadier part.",
                ]]),
                ("Tax", ["ul", [
                    "Interest is taxed at your slab rate; TDS applies to interest on listed debentures.",
                    "Listed bonds sold after 12 months: gains taxed at 12.5% without indexation; within 12 months, at your slab rate.",
                    "Unlisted bonds and market-linked debentures: gains taxed at your slab rate, however long you hold them.",
                    "For investors in the 30% slab, a tax-free bond or a debt fund held for the right period can beat a higher-yielding taxable bond after tax.",
                ]], None, "/calculators/capital-gains-tax/", "Capital gains tax calculator"),
                ("Risks", ["ul", [
                    "Credit risk: the issuer may delay or default. A rating is an opinion, not a guarantee, and ratings can be cut.",
                    "Interest-rate risk if you sell before maturity.",
                    "Liquidity: many corporate bonds trade thinly, so selling early can mean a lower price.",
                ]]),
                ("How we help", [
                    "We place bonds through SEBI-registered online bond platforms and brokers, choose issuers and maturities to match your cash-flow needs, spread credit risk across issuers and compare after-tax yields with debt funds and deposits.",
                ]),
            ],
            steps=[("Your income and timing needs", "When you need money, and how much each month or year."),
                   ("A bond ladder or a single bond", "Issuers, ratings and maturities chosen to match."),
                   ("Purchase", "Through a SEBI-registered bond platform into your demat account."),
                   ("Tracking", "Interest receipts, rating changes and reinvestment at maturity.")],
            faq=[("Are bonds safer than equity?", "Usually less volatile, but not risk-free: an issuer can default, and prices fall when interest rates rise if you sell early."),
                 ("How is bond interest taxed?", "At your income-tax slab rate. Listed bonds held over 12 months are taxed at 12.5% on capital gains."),
                 ("What is a good credit rating?", "AAA is the highest. Below AA, yields rise but so does the chance of delays or default."),
                 ("Bonds or debt mutual funds?", "Bonds give a known maturity and yield if held; debt funds give diversification and liquidity. The better choice depends on timing and your tax slab.")],
            links=[("/invest/mutual-funds/", "Mutual funds"), ("/invest/tax-planning/", "Tax planning"), ("/calculators/swp/", "SWP calculator")],
        ),
        "unlisted-shares": dict(
            title="Unlisted and pre-IPO shares",
            seo="Unlisted and pre-IPO shares in India: how to buy, lock-in, tax | Aeterna Wealth",
            desc="Unlisted and pre-IPO shares explained: how they are bought and transferred to your demat, pricing and liquidity, the 6-month post-IPO lock-in, tax rules, and how Aeterna Wealth helps.",
            lede="Shares of companies that have not listed on a stock exchange yet. They can let you invest before an IPO, but prices are set by a small market, information is limited and selling can take time. Best kept to a small part of a large portfolio.",
            facts=[("24 months", "holding for long-term tax treatment"), ("12.5%", "long-term capital-gains tax"),
                   ("6 months", "typical lock-in after an IPO for pre-IPO shares"), ("Demat", "shares are held in your own demat account")],
            sections=[
                ("How it works", [
                    "Unlisted shares are bought from existing shareholders, such as employees, early investors or dealers, at a negotiated price. Once you pay, the shares are transferred into your demat account by an off-market transfer, so you hold them like any other share.",
                    "If the company later lists, pre-IPO shareholders generally cannot sell for six months from the IPO allotment date.",
                ]),
                ("Pricing and information", [
                    "There is no exchange price. Quotes come from dealers and can differ widely, often with a large spread between buying and selling. Annual reports, filings with the Registrar of Companies and the draft IPO prospectus, if there is one, are the main sources. We go through them with you before you buy.",
                ]),
                ("Who it suits", ["ul", [
                    "Experienced investors with a well-diversified core portfolio.",
                    "Money that can stay invested for several years with no guarantee of an exit.",
                    "A small allocation, often a few per cent of the portfolio.",
                ]]),
                ("Tax", ["ul", [
                    "Held more than 24 months: taxed at 12.5% on the gain, without indexation.",
                    "Held 24 months or less: taxed at your slab rate.",
                    "If the company lists, sales on the exchange follow listed-share rules, with the holding period counted from your purchase.",
                ]], None, "/calculators/capital-gains-tax/", "Capital gains tax calculator"),
                ("Risks", ["ul", [
                    "Liquidity: there may be no buyer when you want to sell.",
                    "Valuation: you may pay more than the eventual IPO price; listings can be delayed or cancelled.",
                    "Limited information, and less regulation of the trade itself than on an exchange.",
                ]]),
                ("How we help", [
                    "We give you valuation context against listed peers, explain the transfer and settlement process, check the share transfer is completed into your demat, and tell you what we earn on the transaction before you invest.",
                ]),
            ],
            steps=[("What you are looking for", "Sectors, amount and how long you can stay invested."),
                   ("The company and the price", "Financials, peers and the deal terms."),
                   ("Transfer", "Payment and off-market transfer into your demat."),
                   ("Follow-up", "Company updates, IPO news and tax at sale.")],
            faq=[("Is buying unlisted shares legal in India?", "Yes. Shares of unlisted public companies can be bought and transferred into a demat account, with stamp duty paid on the transfer."),
                 ("Can I sell pre-IPO shares on listing day?", "Usually not. Pre-IPO shareholders are typically locked in for six months from the IPO allotment date."),
                 ("How are unlisted shares taxed?", "Held more than 24 months: 12.5% on the gain. Held less: at your slab rate."),
                 ("How much should I put into unlisted shares?", "A small part of a large, diversified portfolio, only money that can stay invested for years.")],
            links=[("/invest/aif/", "AIFs"), ("/invest/pms/", "PMS"), ("/invest/tax-planning/", "Tax planning")],
        ),
        "tax-planning": dict(
            title="Tax-aware investment planning",
            seo="Tax planning for investments: LTCG harvesting, set-off, NRIs | Aeterna Wealth",
            desc="Capital-gains tax planning for investors in India, led by a chartered accountant: using the ₹1.25 lakh LTCG exemption every year, loss set-off and carry-forward, redemption order, debt fund tax and NRI questions.",
            lede="Tax is part of every investment decision, not a job for March. Led by a chartered accountant, we plan what to sell, when and in what order, so more of your return stays with you.",
            facts=[("₹1.25 lakh", "tax-free long-term equity gains each year"), ("12.5% / 20%", "equity LTCG and STCG tax rates"),
                   ("8 years", "how long capital losses can be carried forward"), (f"₹{125000 * 0.125 * 1.04:,.0f}", "tax saved a year by using the exemption in full")],
            sections=[
                ("Use the ₹1.25 lakh exemption every year", [
                    f"Long-term gains on equity funds and shares are tax-free up to ₹1.25 lakh each financial year. The allowance is lost if unused. Selling units with that much gain and reinvesting the same day resets your purchase price higher and saves up to ₹{125000 * 0.125 * 1.04:,.0f} of future tax a year, with cess. Over ten years that is over ₹1.6 lakh for a single investor, more for a family where each member has their own allowance.",
                ]),
                ("Losses are worth something", ["ul", [
                    "Short-term losses can be set off against short- or long-term gains; long-term losses only against long-term gains.",
                    "Unused losses carry forward for 8 years, but only if your return is filed on time.",
                    "Booking a loss in a fund you no longer want, in the same year as a gain, cuts that year's tax.",
                ]]),
                ("Sell in the right order", [
                    "Mutual fund units are redeemed first in, first out. Knowing which lots are past 12 months, or 24 months for unlisted shares, and timing a sale by a few weeks can turn a 20% tax into 12.5%, or zero within the exemption.",
                ]),
                ("Situations that need care", ["ul", [
                    "Debt funds bought from 1 April 2023 are taxed at your slab rate; for high earners, choosing between debt funds, bonds and deposits changes after-tax returns.",
                    "Switching from Regular to Direct plans is a sale, so plan it around your gains.",
                    "NRIs: fund houses deduct TDS on redemptions, and a double-tax treaty may let you reclaim or reduce it.",
                    "Gifts to a spouse or minor child can bring the income back into your hands under the clubbing rules; gifts to adult children usually do not.",
                    "Business owners and professionals: how investments sit alongside business income and advance tax.",
                ]]),
                ("What it is not", [
                    "We plan investments with tax in mind. Filing your income-tax return, tax audits and disputes are separate services; we can work with your CA or introduce one.",
                ]),
            ],
            steps=[("Your holdings and gains", "From your Consolidated Account Statement and demat holdings."),
                   ("A tax map", "Which lots are short or long term, gains, losses and the exemption left this year."),
                   ("A plan", "What to sell, when and in what order, and what to reinvest in."),
                   ("Every year", "Before 31 March, so the exemption is never wasted.")],
            faq=[("What is tax harvesting in mutual funds?", "Selling equity fund units with up to ₹1.25 lakh of long-term gain and reinvesting, so the gain is tax-free and your cost price resets higher."),
                 ("Is there a wash-sale rule in India?", "There is no specific wash-sale rule today, so reinvesting straight after a sale is allowed. Keep records of each transaction."),
                 ("How long can capital losses be carried forward?", "Eight assessment years, provided the return for the year of the loss is filed by the due date."),
                 ("How are debt mutual funds taxed now?", "Units bought from 1 April 2023 are taxed at your slab rate, whatever the holding period.")],
            links=[("/calculators/capital-gains-tax/", "Capital gains tax calculator"), ("/invest/portfolio-review/", "Portfolio review"), ("/invest/mutual-funds/", "Mutual funds")],
        ),
        "portfolio-review": dict(
            title="Portfolio review",
            seo="Free mutual fund portfolio review: overlap, cost, tax and gaps | Aeterna Wealth",
            desc="A portfolio review from Aeterna Wealth: everything you hold in one view, with fund overlap, costs, tax position, underperformers and gaps, measured with our own fund data.",
            lede="Most portfolios grow by accident: a fund a friend suggested, an NFO, a tax-saver in March. We put everything you hold in one view and show what overlaps, what it costs, how it is taxed and what is missing.",
            facts=[(f"{ov['Large Cap']:.0f}%" if "Large Cap" in ov else "–", "typical portfolio overlap between two of the five largest large cap funds"),
                   (f"{d['lc_vs_idx']:.0f}%" if d.get("lc_vs_idx") is not None else "–", "of a typical large cap fund is the same as a Nifty 50 index fund"),
                   (f"{d['lc_ter']:.2f}% vs {d['idx_ter']:.2f}%" if d.get("lc_ter") is not None and d.get("idx_ter") is not None else "–", "typical large cap Regular plan cost vs a Nifty 50 index fund"),
                   (f"{d['beat']} of {d['beat_n']}", "diversified funds ahead of their index over 3 years")],
            sections=[
                ("What we look at", ["ul", [
                    "Overlap: how much of your funds' portfolios are the same stocks.",
                    "Track record: each fund against its index and its peers, with our ratings.",
                    "Cost: what you pay each year in expense ratios, and where a cheaper option does the same job.",
                    "Tax: unrealised gains and losses, the ₹1.25 lakh exemption and what selling would cost.",
                    "Allocation and gaps: equity, debt and other assets against your goals and time frame.",
                    "Housekeeping: nominations, KYC, joint holdings and folios to consolidate.",
                ]]),
                ("Why overlap matters", [
                    (f"Owning more funds does not always mean more diversification. Among the five largest large cap funds, any two share about {ov['Large Cap']:.0f}% of their portfolios; among the five largest flexi cap funds, about {ov.get('Flexi Cap', 0):.0f}%." if "Large Cap" in ov else ""),
                    (f"A typical large cap fund's portfolio is {d['lc_vs_idx']:.0f}% the same as a Nifty 50 index fund, at a cost of {d['lc_ter']:.2f}% a year for the Regular plan against {d['idx_ter']:.2f}% for the index fund. Paying active fees for an index-like portfolio is one of the most common costs we find." if d.get("lc_vs_idx") is not None else ""),
                ]),
                ("What to bring", ["ul", [
                    "Your Consolidated Account Statement (CAS) from CAMS, KFintech or MF Central, which lists every mutual fund you hold.",
                    "The CAS from NSDL or CDSL if you hold shares or bonds in a demat account.",
                    "Statements for anything else: PMS, AIFs, deposits, insurance policies.",
                ]]),
                ("What you get", [
                    "A clear written summary: what to keep, what to change and why, with the cost and tax of each change. You decide what to act on; we can carry it out for you.",
                ]),
            ],
            steps=[("Send your statements", "CAS and anything else you hold."),
                   ("We analyse", "Overlap, cost, track record, tax and gaps, with our fund data."),
                   ("We talk it through", "A call to go over the findings."),
                   ("You decide", "Keep, change or switch, with the tax cost shown first.")],
            faq=[("Is the portfolio review free?", "Yes, for a first review. If you then invest through us, we earn commission from the fund houses as described in our disclosures."),
                 ("How do I get my Consolidated Account Statement?", "Request it from the CAMS, KFintech or MF Central websites with your PAN and email; it arrives by email within minutes."),
                 ("How much overlap is too much?", "If two funds share more than about half their portfolios, the second one adds cost more than diversification."),
                 ("Will you tell me to sell everything?", "No. Selling has tax and exit-load costs; we only suggest changes where the benefit is clear after those costs.")],
            links=[("/#compare", "Compare funds and overlap"), ("/invest/tax-planning/", "Tax planning"), ("/invest/mutual-funds/", "Mutual funds")],
        ),
    }


def invest_pages(B, funds, hold, ins, urls):
    d = _data(funds, hold, ins)
    C = _content(B, d)
    e = B.e
    for slug in PAGES:
        c = C[slug]
        path = f"/invest/{slug}/"
        facts = "".join(f"<div><b>{e(v)}</b><span>{e(k)}</span></div>" for v, k in c["facts"] if v)
        secs = ""
        for sec in c["sections"]:
            head, body = sec[0], sec[1]
            note = sec[2] if len(sec) > 2 else None
            link = (sec[3], sec[4]) if len(sec) > 4 else None
            if body and body[0] == "ul":
                inner = "<ul>" + "".join(f"<li>{e(x)}</li>" for x in body[1]) + "</ul>"
            else:
                inner = "".join(f"<p>{e(x)}</p>" for x in body if x)
            if note:
                inner += f"<p class='muted'>{e(note)}</p>"
            if link:
                inner += f"<p><a href='{link[0]}'>{e(link[1])} →</a></p>"
            secs += f"<div class='inv-sec'><h2>{e(head)}</h2><div class='body'>{inner}</div></div>"
        steps = "".join(f"<li><b>{e(a)}</b><span>{e(b)}</span></li>" for a, b in c["steps"])
        faq = "".join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in c["faq"])
        more = "".join(f"<a class='btn' href='{u}'>{e(t)}</a>" for u, t in c["links"])
        others = " · ".join(f"<a href='/invest/{s}/'>{e(NAMES[s])}</a>" for s in PAGES if s != slug)
        body = f"""{CSS}<section class="band" style="padding-top:28px"><div class="wrap"><div class="inv-page">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/invest/">Invest</a> › {e(NAMES[slug])}</nav>
<div class="inv-hero" style="margin-top:16px"><div><div class="eyebrow">Invest · {e(NAMES[slug])}</div>
<h1 style="font-size:clamp(32px,4.4vw,48px);margin-top:10px">{e(c['title'])}</h1>
<p class="lede" style="margin-top:14px">{e(c['lede'])}</p>
<div class="row" style="margin-top:20px"><a class="btn primary" href="/#contact">Talk to us</a>{'<a class="btn" href="/mutual-funds/">Browse every fund</a>' if slug == 'mutual-funds' else '<a class="btn" href="/invest/">All solutions</a>'}</div></div>
<div class="inv-facts">{facts}</div></div>
<div style="margin-top:34px">{secs}
<div class='inv-sec'><h2>How we work with you</h2><div class='body'><ol class='inv-steps'>{steps}</ol></div></div>
<div class='inv-sec'><h2>Common questions</h2><div class='body'>{faq}</div></div></div>
<div class="inv-cta"><div><h2>Talk to us about {e(NAMES[slug].lower() if slug not in ('pms', 'aif') else NAMES[slug])}</h2><p>A first conversation is free. We reply within one working day.</p></div><a class="btn" href="/#contact">Talk to us</a></div>
<div class="inv-more">{more}</div>
<p class="note" style="margin-top:26px">Investments are subject to market risks; returns are not guaranteed. Read the offer documents before investing. Tax rules described are those in force for 2025-26 and can change; they are general information, not tax advice for your situation. See our <a href="/disclosures/">disclosures</a>.</p>
<p style="margin-top:16px;font-size:14.5px">Also: {others} · <a href="/invest/">All solutions</a> · <a href="/#contact">Contact</a></p>
</div></div></section>"""
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in c["faq"]]}
        svc_ld = {"@context": "https://schema.org", "@type": "Service", "name": c["title"], "serviceType": NAMES[slug],
                  "provider": {"@id": B.SITE + "/#org"}, "areaServed": {"@type": "Country", "name": "India"}, "url": B.SITE + path,
                  "description": c["desc"]}
        B.write(path, B.page(c["seo"], c["desc"], path, body,
                             (svc_ld, faq_ld, B.crumbs([("Invest", "/invest/"), (NAMES[slug], path)]))))
        urls.append((path, "monthly", "0.8"))
    cards = "".join(f"<a class='card stack sol' href='/invest/{s}/' style='gap:6px;text-decoration:none;color:inherit{';grid-column:1/-1' if s == 'portfolio-review' else ''}'><b style='font:600 19px var(--f-display)'>{e(NAMES[s])}</b>"
                    f"<span class='muted' style='font-size:14px'>{e(C[s]['lede'][:150].rsplit(' ', 1)[0])}…</span></a>" for s in PAGES)
    app = open(__file__.replace("invest_pages.py", "app.html"), encoding="utf-8").read()
    a = app.index('<h2 style="font-size:26px;margin-top:40px">How they compare</h2>')
    b = app.index('capital-gains calculator</a>.</p>', a) + len('capital-gains calculator</a>.</p>')
    table = app[a:b].replace('href="#tools" data-tool="tax"', 'href="/calculators/capital-gains-tax/"')
    qa = re.findall(r"\['([^']+)','([^']+)'\]", app[app.index("['Do you give stock tips"):app.index(".map(q=>`<details class=\"faq\">")])
    faq_html = "".join(f"<details class='faq'><summary>{q}</summary><p>{a_}</p></details>" for q, a_ in qa)
    hub_faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a_}} for q, a_ in qa]}
    body = f"""{CSS}<section class="band" style="padding-top:28px"><div class="wrap"><div class="inv-page">
<div class="eyebrow">What we offer</div><h1 style="font-size:clamp(32px,4.4vw,48px);margin-top:10px">Everything you invest in, with one team</h1>
<p class="lede" style="margin-top:12px;max-width:70ch">Mutual funds are our largest practice and where most families start. As wealth grows, we bring in PMS, AIFs, bonds and unlisted shares where they fit, with tax planned in and the whole portfolio reviewed together.</p>
<div class="grid g3" style="margin-top:26px">{cards}</div>
{table}
<h2 style="font-size:26px;margin-top:40px">Common questions</h2><div style="margin-top:8px">{faq_html}</div>
<div class="inv-cta"><div><h2>Not sure where to start?</h2><p>Most families start with mutual funds. Tell us what you are planning and we'll suggest the right mix.</p></div><a class="btn" href="/#contact">Talk to us</a></div>
</div></div></section>"""
    B.write("/invest/", B.page("Invest: mutual funds, PMS, AIFs, bonds, unlisted shares | Aeterna Wealth",
                               "Mutual funds, PMS, AIFs, bonds, unlisted shares, tax planning and portfolio reviews from Aeterna Wealth, AMFI-registered mutual fund distributor (ARN-317889).",
                               "/invest/", body, (hub_faq_ld, B.crumbs([("Invest", "/invest/")]))))
    urls.append(("/invest/", "monthly", "0.8"))
    return d
