"""Investor guides (/learn/<slug>/): evergreen answers to the questions Indian investors search for most, each built on
figures recomputed from our own data on every build. Tax rules: Finance (No. 2) Act 2024, as in force for 2025-26.
Called from build_site.main() with its helpers as B."""
import statistics as st

from invest_pages import CSS, _data


def _figs(funds, ins):
    f = {}
    items = {i["id"]: i for i in (ins or {}).get("items", [])}
    f["items"] = items
    sb = (items.get("scoreboard") or {}).get("rows") or []
    f["sb"] = sb
    f["beat3"], f["n3"] = sum(r["beat3"] for r in sb), sum(r["n3"] for r in sb)
    f["beat5"], f["n5"] = sum(r["beat5"] for r in sb), sum(r["n5"] for r in sb)
    lc = next((r for r in sb if r["category"] == "Large Cap"), None)
    f["lc"] = lc
    n50 = [x for x in funds if x.get("peer_group") == "Index: NIFTY 50" and x["plan_type"] == "Direct" and x.get("ter") is not None]
    f["n50_count"] = len({x.get("pair_key") for x in funds if x.get("peer_group") == "Index: NIFTY 50"})
    f["n50_min_ter"] = min((x["ter"] for x in n50), default=None)
    f["n50_med_ter"] = st.median([x["ter"] for x in n50]) if n50 else None
    reg = [x for x in funds if x["plan_type"] == "Regular" and x.get("ter") is not None]
    f["reg_ter"] = {c: st.median([x["ter"] for x in reg if x["category"] == c]) for c in ("Large Cap", "Flexi Cap", "Mid Cap", "Small Cap")
                    if any(x["category"] == c for x in reg)}
    return f


def _fv_sip(monthly, years, r):
    mr = (1 + r) ** (1 / 12) - 1
    return sum(monthly * (1 + mr) ** k for k in range(1, years * 12 + 1))


def _L(x):
    return f"₹{x / 1e7:.2f} crore" if x >= 1e7 else f"₹{x / 1e5:.1f} lakh"


def guides(d, f):
    P = lambda v, n=2: f"{v:.{n}f}%"
    gap = d.get("ter_gap") or 1.0
    sip_gap = _fv_sip(10000, 20, 0.12) - _fv_sip(10000, 20, 0.12 - gap / 100)
    it = f["items"]
    lc = f["lc"]
    ov = d.get("overlap", {})
    g10 = it.get("sip-10y-flexi-cap")
    h3 = it.get("held-3y-large-cap")
    pk = [it[k] for k in ("sip-peak-large-cap", "sip-peak-mid-cap", "sip-peak-small-cap", "sip-peak-flexi-cap") if k in it]
    harvest = 125000 * 0.125 * 1.04
    G = []
    G.append(dict(
        slug="regular-vs-direct-mutual-funds",
        title="Regular vs Direct mutual funds: what the extra cost buys",
        seo="Regular vs Direct mutual funds: cost difference and which to choose",
        desc=f"Regular and Direct plans hold the same portfolio; Regular typically costs {P(gap)} a year more. What that costs over 20 years, what it pays for, and how to choose.",
        answer=f"A Direct plan and a Regular plan of the same fund own exactly the same stocks. The Regular plan costs more, typically {P(gap)} a year across Indian equity funds, because it includes the distributor's commission. On a ₹10,000 monthly SIP for 20 years at an assumed 12%, that difference adds up to about {_L(sip_gap)}. Choose Direct if you will pick, combine and review funds yourself; choose Regular if you want someone to do that work.",
        sections=[
            ("What is the same, and what is not", ["ul", ["Same fund manager, same portfolio, same risk.",
                                                          "Different expense ratio: the Regular plan's includes the distributor's commission, so its NAV grows a little slower.",
                                                          "Different NAV: the two plans start at the same price but drift apart over time because of the cost gap."]]),
            ("What the cost gap adds up to", [f"The gap compounds. At the typical {P(gap)} a year, a ₹10,000 monthly SIP for 20 years at an assumed 12% a year ends about {_L(sip_gap)} lower in the Regular plan. On a ₹1 crore portfolio, the gap is about ₹{gap * 1e5:,.0f} in the first year alone.",
                                              "That is the price of advice and service. Whether it is worth paying depends on what you get for it."]),
            ("What the Regular plan's commission pays for", ["ul", ["Choosing funds, and just as important, not choosing the ones that look good only on recent returns.",
                                                                     "Combining them so they don't overlap, and rebalancing when markets move.",
                                                                     "Tax planning: using the ₹1.25 lakh yearly exemption, the order of redemptions, losses.",
                                                                     "Paperwork: KYC, nominations, transmission after a death, address changes.",
                                                                     "Keeping you invested in falls, which is where most investors lose more than any expense ratio."]]),
            ("How to choose", ["ul", ["You know what to buy, will review it every year and won't panic in a fall: Direct.",
                                      "You want the choice, review and tax planning done for you: Regular, through a distributor you trust and who tells you what they earn.",
                                      "Switching from Regular to Direct counts as a sale, so check the capital-gains tax and exit load before you switch."]]),
        ],
        faq=[("Is a Direct plan always better?", "It is always cheaper. Whether it ends up better depends on whether you choose and manage funds as well as an adviser or distributor would."),
             ("Can I switch from Regular to Direct?", "Yes, but it is a redemption and a fresh purchase, so capital-gains tax and any exit load apply."),
             ("How do I know which plan I hold?", "Your Consolidated Account Statement shows the plan name; Direct plans say 'Direct' in the scheme name.")],
        links=[("/invest/mutual-funds/", "How we choose mutual funds"), ("/calculators/sip/", "SIP calculator")],
    ))
    G.append(dict(
        slug="how-to-choose-a-mutual-fund",
        title="How to choose a mutual fund: a six-step check",
        seo="How to choose a mutual fund in India: a 6-step data check",
        desc="A practical six-step check for choosing an equity mutual fund in India: category, the right index, rolling returns, risk, cost and overlap, with what the data shows.",
        answer="Pick the category first (it decides most of the risk), then compare funds only within it: against the category's total-return index over rolling 3-year periods, on how they held up in falls, on cost, and on how much they overlap with what you already own. Recent 1-year returns are the weakest guide of all.",
        sections=[
            ("1. Start with the category, not the fund", ["The SEBI category (large cap, mid cap, flexi cap and so on) decides most of a fund's risk and return. Choose it from your time frame: large and flexi cap for money you need in 5 years or more; mid and small cap only for 7 to 10 years or more."]),
            ("2. Compare against the right index", [f"A fund should be measured against its own category's total-return index, which includes dividends. Over the last 3 years, only {f['beat3']} of {f['n3']} diversified Regular plans beat theirs." + (f" In large caps, only {lc['beat3']} of {lc['n3']} did." if lc else "")]),
            ("3. Use rolling returns, not one period", ["A single 3-year return depends heavily on the start and end dates. Look at every 3-year window: how often the fund was ahead of its index, and by how much in the bad periods. Our fund pages show this for every fund."]),
            ("4. Check how it behaves in falls", ["Downside capture shows how much of the index's fall a fund took. A fund that falls less recovers faster and is easier to hold on to."]),
            ("5. Compare the cost", [f"Expense ratios are a guaranteed drag. A typical large cap Regular plan costs about {P(f['reg_ter'].get('Large Cap', 2))} a year; a Nifty 50 index fund's Direct plan can cost {P(f['n50_min_ter'])}." if f.get("n50_min_ter") is not None else "Expense ratios are a guaranteed drag; compare them within the category."]),
            ("6. Check overlap with what you own", [f"Among the five largest large cap funds, any two share about {ov['Large Cap']:.0f}% of their portfolios. A second fund that holds the same stocks adds cost, not diversification." if "Large Cap" in ov else "A second fund that holds the same stocks adds cost, not diversification."]),
            ("What not to rely on", ["ul", ["Last year's top performer: in our backtest, top-rated funds did not keep beating their index more often than the average fund.",
                                            "Star ratings alone, NFO launches and fund size on its own.",
                                            "A fund's name: check the portfolio and the SEBI category."]]),
        ],
        faq=[("How many mutual funds should I own?", "Usually 4 to 6 equity funds across categories are enough; more often means more overlap."),
             ("Are past returns useful at all?", "Consistency against the index over many rolling periods is more useful than any single return figure, but none of it predicts the future."),
             ("Should I choose by fund size?", "Size alone says little. Very large small cap funds can find it harder to buy and sell stocks, which can hold returns back.")],
        links=[("/mutual-funds/", "Every fund, by category"), ("/#compare", "Compare funds and overlap"), ("/#method", "How our ratings work")],
    ))
    G.append(dict(
        slug="sip-vs-lump-sum",
        title="SIP or lump sum? What the data says",
        seo="SIP vs lump sum: which is better? What Indian fund data shows",
        desc="SIP or lump sum: the maths, what happened to SIPs started at the last market high, how often 3-year holdings made money, and a simple rule for choosing.",
        answer="If the money is already in hand, a lump sum usually ends higher because more of it is invested for longer; a SIP, or a lump sum spread in over 6 to 12 months through an STP, lowers the risk of investing everything just before a fall. For money that comes in monthly, a SIP is simply the natural fit.",
        sections=[
            ("What happened to SIPs started at the top", [("Even investors who started at the last market high have mostly recovered: " + "; ".join(f"{p['figure']} {p['category'].lower()} funds" for p in pk) + " show SIPs started then worth more than the money put in, though the index itself is still below that high. Instalments made while prices were lower bought more units.") if pk else ""]),
            ("Time in the market matters more than timing", [(f"Across large cap funds with 10 or more years of history, the middle fund made money in {h3['figure']} of all 3-year holding periods since 2006, through the 2008 and 2020 crashes." if h3 else "") + (f" A ₹10,000 monthly SIP over the last 10 years in the middle-ranked flexi cap fund is worth about {g10['figure']} today, on ₹12 lakh put in." if g10 else "")]),
            ("A simple rule", ["ul", ["Monthly income: SIP, and step it up each year with your salary.",
                                      "A bonus, inheritance or property sale: invest part at once and spread the rest over 6 to 12 months with an STP from a liquid fund.",
                                      "Money needed within 3 years: neither; equity is the wrong place for it."]]),
        ],
        faq=[("Is SIP better than lump sum?", "Not always. A lump sum has more time in the market; a SIP spreads the risk of a badly timed start. The right choice depends on whether the money is already in hand."),
             ("What is an STP?", "A systematic transfer plan moves a fixed amount every week or month from a liquid or debt fund into an equity fund, so a lump sum is invested gradually."),
             ("Should I stop my SIP when markets fall?", "Usually not. SIP instalments in a fall buy more units, which is what helps a SIP recover before the market does.")],
        links=[("/calculators/sip/", "SIP calculator"), ("/calculators/lumpsum/", "Lump sum calculator"), ("/#tools-sipreal", "Test a SIP on real NAVs")],
    ))
    G.append(dict(
        slug="mutual-fund-portfolio-overlap",
        title="Mutual fund overlap: why owning six funds can mean owning one",
        seo="Mutual fund overlap: how much is too much, and how to check it",
        desc="Portfolio overlap explained with real data: how much India's largest funds share, why a typical large cap fund looks like a Nifty 50 index fund, and how to check yours.",
        answer=(f"Overlap is the share of two funds' portfolios invested in the same stocks. Among India's five largest large cap funds, any two share about {ov.get('Large Cap', 50):.0f}% of their holdings, and a typical large cap fund is about {d.get('lc_vs_idx', 55):.0f}% the same as a Nifty 50 index fund. Above about 50%, a second fund adds cost more than diversification."),
        sections=[
            ("What the data shows", ["ul", [f"Five largest large cap funds: typical overlap between any two about {ov.get('Large Cap', 0):.0f}%." if "Large Cap" in ov else "",
                                            f"Five largest flexi cap funds: about {ov.get('Flexi Cap', 0):.0f}%." if "Flexi Cap" in ov else "",
                                            f"Five largest mid cap funds: about {ov.get('Mid Cap', 0):.0f}%." if "Mid Cap" in ov else "",
                                            (f"A typical large cap fund vs a Nifty 50 index fund: about {d['lc_vs_idx']:.0f}%, at {d['lc_ter']:.2f}% a year for the Regular plan against {d['idx_ter']:.2f}% for the index fund." if d.get("lc_vs_idx") is not None else "")]]),
            ("Why it matters", ["Overlap hides concentration: five funds can end up with the same ten banks and IT companies at the top. You pay five expense ratios for what is close to one portfolio, and the diversification you think you have is not there in a fall."]),
            ("How to check yours", ["ul", ["Put your funds side by side in our Compare tool: it shows the stocks they share and the overlap.",
                                           "Look at each fund's top 10 holdings in its latest monthly portfolio.",
                                           "Prefer funds from different categories or styles (for example a large cap index fund plus a mid cap and a value fund) over several similar flexi caps."]]),
        ],
        faq=[("How much overlap is too much?", "If two funds share more than about half their portfolios, the second one adds cost more than diversification."),
             ("Is overlap bad in index funds?", "Two index funds on the same index overlap almost completely by design; holding both adds nothing."),
             ("How is overlap calculated?", "For each stock both funds hold, take the smaller of the two weights, and add them up.")],
        links=[("/#compare", "Compare funds and overlap"), ("/invest/portfolio-review/", "Portfolio review")],
    ))
    G.append(dict(
        slug="capital-gains-tax-on-mutual-funds",
        title="Tax on mutual fund gains in 2025-26: LTCG, STCG and how to save",
        seo="Mutual fund capital gains tax 2025-26: LTCG, STCG, how to save",
        desc=f"How equity and debt mutual fund gains are taxed in 2025-26: 12.5% LTCG above ₹1.25 lakh, 20% STCG, debt funds at slab, and legal ways to save, worth up to ₹{harvest:,.0f} a year.",
        answer=f"Equity fund units held more than 12 months: 12.5% tax on gains above ₹1.25 lakh in a financial year. Held 12 months or less: 20%. Debt funds bought from 1 April 2023: your slab rate, however long you hold them. Using the ₹1.25 lakh exemption every year by booking gains and reinvesting can save up to ₹{harvest:,.0f} of tax a year, with cess.",
        sections=[
            ("The rates", ["ul", ["Equity funds (65%+ in Indian equity), held more than 12 months: 12.5% on gains above ₹1.25 lakh a year.",
                                  "Equity funds held 12 months or less: 20%.",
                                  "Debt funds bought from 1 April 2023: slab rate, no indexation.",
                                  "Hybrid funds: taxed as equity or debt depending on their equity share.",
                                  "A 4% health and education cess applies on top; surcharge for high incomes."]]),
            ("Five legal ways to pay less", ["ul", [f"Harvest the ₹1.25 lakh exemption every year: sell units with that much long-term gain and reinvest. That saves up to ₹{harvest:,.0f} a year, more for a family where each member has their own exemption.",
                                                   "Set off losses: short-term losses against any capital gains, long-term losses only against long-term gains. Carry unused losses forward for 8 years by filing on time.",
                                                   "Mind the 12-month line: waiting a few weeks can change a 20% tax into 12.5%, or zero within the exemption.",
                                                   "Redeem in the right order: units go out first in, first out, so know which lots you are selling.",
                                                   "Plan switches: moving from Regular to Direct, or between funds, is a sale and can trigger tax."]]),
            ("Worked example", [f"You sell equity fund units held 18 months with a ₹3 lakh gain. Taxable: ₹3,00,000 − ₹1,25,000 = ₹1,75,000. Tax at 12.5% plus 4% cess: ₹{175000 * 0.125 * 1.04:,.0f}."]),
        ],
        faq=[("Is there a wash-sale rule in India?", "There is no specific wash-sale rule today, so reinvesting straight after a tax-harvesting sale is allowed."),
             ("Is SIP taxed differently?", "Each SIP instalment is a separate purchase with its own 12-month clock."),
             ("Do NRIs pay the same tax?", "The rates are similar, but fund houses deduct TDS on NRIs' redemptions; a tax treaty may reduce the final tax.")],
        links=[("/calculators/capital-gains-tax/", "Capital gains tax calculator"), ("/invest/tax-planning/", "Tax planning with us")],
    ))
    G.append(dict(
        slug="pms-vs-mutual-funds",
        title="PMS vs mutual funds: costs, tax and who each suits",
        seo="PMS vs mutual funds: costs, tax, minimum and who each suits",
        desc="PMS vs mutual funds compared: ₹50 lakh minimum, concentration, fees and their compounding cost, how each is taxed, and a simple way to decide.",
        answer="A PMS holds 15 to 30 stocks in your own demat account with a ₹50 lakh minimum; a mutual fund pools money into a diversified portfolio from ₹100 a month. PMS can suit large portfolios that want a concentrated strategy, but it usually costs more, every trade is taxed in your hands, and results depend heavily on one manager.",
        sections=[
            ("Side by side", ["ul", ["Minimum: PMS ₹50 lakh (SEBI); mutual funds from about ₹100–500 a month.",
                                     "Ownership: PMS shares sit in your demat; a mutual fund gives you units.",
                                     "Concentration: PMS often 15–30 stocks; diversified funds usually 40–80.",
                                     "Tax: PMS trades are taxed in your hands as they happen; a fund's internal trades are not taxed until you sell units.",
                                     "Fees: PMS fixed fees often 1.5–2.5% a year, or a profit share above a hurdle; equity fund expense ratios are capped by SEBI."]]),
            ("The cost question", [f"Fees compound. On ₹50 lakh over 10 years at an assumed 13% before fees, a 2.5% yearly fee leaves about {_L(5e6 * 1.12 ** 10 - 5e6 * 1.105 ** 10)} less than a 1% fee. A PMS has to earn that back to be worth it."]),
            ("How to decide", ["ul", ["Under ₹50 lakh to invest: mutual funds.",
                                      "Large portfolio with a diversified core already: a PMS can add a concentrated strategy alongside.",
                                      "Compare a PMS on its reported returns against a standard benchmark, its worst periods and its fees after tax, not on its best year."]]),
        ],
        faq=[("Is PMS better than mutual funds?", "Not by default. It is more concentrated and usually costs more; it is worth it only if it adds return or diversification after costs and tax."),
             ("What is the minimum for PMS?", "₹50 lakh, in cash or eligible shares."),
             ("Can I exit a PMS any time?", "Yes; SEBI caps exit loads at 3% in the first year, 2% in the second and 1% in the third.")],
        links=[("/invest/pms/", "PMS with us"), ("/invest/mutual-funds/", "Mutual funds with us")],
    ))
    G.append(dict(
        slug="index-funds-vs-active-funds",
        title="Index funds vs active funds in India: who wins?",
        seo="Index funds vs active mutual funds in India: what the data shows",
        desc=f"How many Indian active equity funds beat their index: {f['beat3']} of {f['n3']} over 3 years. Where active funds earn their fee, where index funds win, and what it costs.",
        answer=(f"Over the last 3 years, {f['beat3']} of {f['n3']} diversified active Regular plans beat their category's total-return index, and {f['beat5']} of {f['n5']} over 5 years." + (f" In large caps: {lc['beat3']} of {lc['n3']}." if lc else "") + " Index funds win on cost and certainty; active funds have a better case in mid caps, small caps and flexible mandates, if you pick well."),
        sections=[
            ("By category", ["ul", [f"{r['category']}: {r['beat3']} of {r['n3']} beat the index over 3 years" + (f", {r['beat5']} of {r['n5']} over 5." if r.get('n5') else ".") for r in f["sb"]]]),
            ("The cost gap", [f"A Nifty 50 index fund's Direct plan can cost as little as {P(f['n50_min_ter'])} a year (median {P(f['n50_med_ter'])}); a typical large cap Regular plan costs about {P(f['reg_ter'].get('Large Cap', 2))}. That gap is a head start the active fund has to make up every year." if f.get("n50_min_ter") is not None else ""]),
            ("A sensible mix", ["ul", ["Large caps: a low-cost index fund as the core is hard to beat.",
                                       "Mid and small caps, flexi caps: active funds with a consistent record against their index can add value.",
                                       "Between index funds on the same index, choose on cost and tracking error."]]),
        ],
        faq=[("Do index funds beat active funds in India?", "In large caps, most active funds have not beaten their index over 3 and 5 years. In other categories the record is more mixed."),
             ("Which index fund is best?", "Index funds on the same index hold the same stocks; compare them on expense ratio and tracking error."),
             ("Are index funds safe?", "They carry the full risk of the market they track; they remove the risk of a fund manager underperforming.")],
        links=[("/mutual-funds/index-fund/nifty-50/", "Nifty 50 index funds compared"), ("/insights/scoreboard/", "Active funds vs their index")],
    ))
    sw = _swr()
    if sw:
        a, b = sw["mixes"]["35"], sw["mixes"]["60"]
        r = lambda t, x: next(z for z in t if abs(z["rate"] - x) < .01)
        y0 = sw["from"][:4]
        rows = [[f"{z['multiple']:g}× ({z['rate']:g}%)", f"{z['last30']}%", f"{z['last40']}%", f"{z['last50']}%", f"{z['kept50']}%",
                 f"{r(b, z['rate'])['last50']}%"] for z in a]
        G.append(dict(
            slug="4-percent-rule-india",
            title="The 4% rule in India: how big a corpus lasts for life",
            seo="The 4% rule in India: retirement corpus, safe withdrawal rate and your freedom number",
            desc=f"Does taking 4% a year from a retirement corpus work in India? Tested on Indian market returns since {y0}: how long 25×, 33× and 40× your yearly spending last, and which to aim for.",
            answer=(f"The 4% rule says: take 4% of your corpus in the first year of retirement, raise it with inflation every year, and the money should last about 30 years. "
                    f"That needs a corpus of 25 times your yearly spending. On Indian market returns since {y0}, with inflation at {sw['inflation']:g}%, 25× lasted 30 years in {r(a, 4)['last30']} of 100 cases "
                    f"but 50 years in only {r(a, 4)['last50']}, so it is not 'forever' in India. For money that lasts for life, even if you stop work early, aim for about 33× (3% a year): "
                    f"it lasted 50 years in {r(a, 3)['last50']} of 100. To pass the corpus on with its value intact, aim for about 40× (2.5%)."),
            sections=[
                ("Where the 4% rule comes from", ["It comes from US research in the 1990s (William Bengen, then the 'Trinity study'): a mix of US shares and bonds, from which 4% a year rising with inflation survived every 30-year period in US history.",
                                                  f"India is different. Inflation has been higher (we assume {sw['inflation']:g}% a year), so the withdrawal grows faster, and debt returns are only a little above inflation. Both make a given rate run out sooner."]),
                ("The multiples, in plain words", ["ul", ["Yearly spending means what your investments must pay: your expenses in retirement, less any rent or pension. Not your house, not your income.",
                                                          f"20× (5% a year): lasted 30 years in {r(a, 5)['last30']} of 100 cases. Enough only for a late, short retirement.",
                                                          f"25× (4% a year): lasted 30 years in {r(a, 4)['last30']} of 100, and 40 years in {r(a, 4)['last40']}. Suits retiring at about 60.",
                                                          f"33× (3% a year): lasted 50 years in {r(a, 3)['last50']} of 100. Enough for life at almost any retirement age: a sensible 'freedom number'.",
                                                          f"40× (2.5% a year): after 50 years the corpus was still worth what it started with, in today's money, in {r(a, 2.5)['kept50']} of 100. This is the number for passing wealth on."]]),
                ("Tested on Indian markets", ["table", ["Corpus (year-1 withdrawal)", "Lasts 30 yrs", "40 yrs", "50 yrs", "Value kept, 50 yrs", "50 yrs, 60% equity"], rows,
                                             f"{sw['sequences']:,} sequences of {sw['years']} years built from actual monthly returns of Indian equity, debt and gold funds, {sw['from']} to {sw['to']} (2008 and 2020 included), "
                                             f"in random 12-month blocks. Portfolio: 35% equity, 5% gold, 60% debt, rebalanced monthly; the last column uses 60% equity. The withdrawal rises {sw['inflation']:g}% a year. Fund returns are after fund costs, before tax."]),
                ("What a higher equity share does", [f"More equity makes the corpus grow faster but swing harder. At 60% equity, 4% a year lasted 50 years in {r(b, 4)['last50']} of 100 cases (against {r(a, 4)['last50']} at 35%), "
                                                     f"but early falls hurt more. Most retirees are better served by a modest equity share and a lower withdrawal rate than by a high equity share and a high one."]),
                ("Making any rate safer", ["ul", ["Skip the inflation increase after a year in which the portfolio fell. It costs little and adds years.",
                                                  "Keep two years of spending in liquid and arbitrage funds, so a fall never forces you to sell equity.",
                                                  "Count rent, pension and an annuity first: they shrink what the corpus has to pay.",
                                                  "Keep health cover going after you stop work. Medical costs are the most common reason retirement money runs out early.",
                                                  "Review every year. A rule of thumb is a starting point, not autopilot."]]),
            ],
            faq=[("Is the 4% rule safe in India?", f"For about 30 years, usually: it lasted 30 years in {r(a, 4)['last30']} of 100 cases on Indian market history. For a longer retirement, or to keep the corpus intact, use 3% or less."),
                 ("How much corpus do I need to retire in India?", "Take what your investments must pay each year in retirement, in today's money, after rent and pension. Multiply by 25 for a retirement from about 60, by 33 for one that lasts for life or starts early, and by 40 to pass the corpus on. Then grow it with inflation to your retirement date."),
                 ("Is it 25 times monthly or yearly expenses?", "Yearly. 25 times your monthly spending would be only about two years of spending."),
                 ("Does the 4% rule include tax?", "No. Withdrawals from equity and debt funds are taxed when you redeem; allow for that in the spending figure, or keep the rate a little lower.")],
            links=[("/plan/", "Work out your own freedom number"), ("/calculators/", "Calculators")],
        ))
    return G


def _swr():
    import json, pathlib
    p = pathlib.Path(__file__).parent / "planner" / "swr.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def learn_pages(B, funds, hold, ins, urls, as_of):
    d = _data(funds, hold, ins)
    f = _figs(funds, ins)
    e = B.e
    gs = guides(d, f)
    for g in gs:
        path = f"/learn/{g['slug']}/"
        secs = ""
        for head, body in g["sections"]:
            if body and body[0] == "table":
                inner = ("<div class='tablewrap'><table><thead><tr>" + "".join(f"<th class='{'l' if i == 0 else ''}'>{e(h)}</th>" for i, h in enumerate(body[1]))
                         + "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td class='{'l' if i == 0 else 'num'}'>{e(c)}</td>" for i, c in enumerate(row)) + "</tr>" for row in body[2])
                         + f"</tbody></table></div><p class='note' style='margin-top:8px'>{e(body[3])}</p>")
            elif body and body[0] == "ul":
                inner = "<ul>" + "".join(f"<li>{e(x)}</li>" for x in body[1] if x) + "</ul>"
            else:
                inner = "".join(f"<p>{e(x)}</p>" for x in body if x)
            if inner.strip("<ul></ul>"):
                secs += f"<div class='inv-sec'><h2>{e(head)}</h2><div class='body'>{inner}</div></div>"
        faq = "".join(f"<details class='faq'><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in g["faq"])
        others = "".join(f"<li><a href='/learn/{o['slug']}/'>{e(o['title'])}</a></li>" for o in gs if o is not g)
        more = "".join(f"<a class='btn' href='{u}'>{e(t)}</a>" for u, t in g["links"])
        body = f"""{CSS}<section class="band" style="padding-top:28px"><div class="wrap"><div class="inv-page">
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/learn/">Learn</a> › {e(g['title'])}</nav>
<div class="eyebrow" style="margin-top:16px">Investor guide</div>
<h1 style="font-size:clamp(30px,4.2vw,46px);margin-top:10px;max-width:24ch">{e(g['title'])}</h1>
<p class="muted" style="margin-top:10px;font-size:13.5px">Aeterna Wealth · figures from our fund data, updated {B.dmy(as_of)}</p>
<div class="card" style="margin-top:22px;border-left:4px solid var(--teal)"><div class="eyebrow">The short answer</div><p style="margin-top:8px;font-size:16.5px;line-height:1.6">{e(g['answer'])}</p></div>
<div style="margin-top:26px">{secs}<div class='inv-sec'><h2>Common questions</h2><div class='body'>{faq}</div></div></div>
<div class="inv-cta"><div><h2>Want this worked out for your money?</h2><p>A first conversation is free. We reply within one working day.</p></div><a class="btn" href="/#contact">Talk to us</a></div>
<div class="inv-more">{more}</div>
<div class='inv-sec' style="margin-top:26px"><h2>More guides</h2><div class='body'><ul>{others}</ul></div></div>
<p class="note" style="margin-top:20px">General information, not investment or tax advice for your situation. Mutual fund investments are subject to market risks; read all scheme-related documents carefully. Past performance does not guarantee future returns.</p>
</div></div></section>"""
        art = {"@context": "https://schema.org", "@type": "Article", "headline": g["title"][:110], "description": g["desc"],
               "datePublished": "2026-11-06", "dateModified": as_of, "inLanguage": "en-IN", "author": {"@id": B.SITE + "/#org"},
               "publisher": {"@id": B.SITE + "/#org"}, "image": B.SITE + "/og.png", "mainEntityOfPage": B.SITE + path}
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in
                                 [(g["title"], g["answer"])] + g["faq"]]}
        B.write(path, B.page(g["seo"] + " | Aeterna Wealth", g["desc"], path, body,
                             (art, faq_ld, B.crumbs([("Learn", "/learn/"), (g["title"], path)]))))
        urls.append((path, "weekly", "0.8"))
    cards = "".join(f"<a class='card stack sol' href='/learn/{g['slug']}/' style='gap:6px;text-decoration:none;color:inherit'><b style='font:600 19px/1.3 var(--f-display)'>{e(g['title'])}</b>"
                    f"<span class='muted' style='font-size:14px'>{e(g['desc'][:140].rsplit(' ', 1)[0])}…</span></a>" for g in gs)
    body = f"""{CSS}<section class="band" style="padding-top:28px"><div class="wrap"><div class="inv-page">
<div class="eyebrow">Learn</div><h1 style="font-size:clamp(32px,4.4vw,48px);margin-top:10px">Investor guides</h1>
<p class="lede" style="margin-top:12px;max-width:70ch">Straight answers to the questions Indian investors ask most, with figures worked out from our own fund data and updated every weekday.</p>
<div class="grid g3" style="margin-top:26px">{cards}</div>
<p style="margin-top:22px"><a class="btn" href="/insights/">This month's insights</a> <a class="btn" href="/calculators/">Calculators</a></p>
</div></div></section>"""
    B.write("/learn/", B.page("Investor guides: mutual funds, SIPs, tax, PMS | Aeterna Wealth",
                              "Straight answers to the questions Indian investors ask most: Regular vs Direct, choosing a fund, SIP vs lump sum, overlap, capital-gains tax, PMS and index funds.",
                              "/learn/", body, (B.crumbs([("Learn", "/learn/")]),)))
    urls.append(("/learn/", "weekly", "0.8"))
