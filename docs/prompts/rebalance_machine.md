# Prompt: the Aeterna rebalance and new-money machine

Paste everything below the line into a new Claude Code session on the `aeterna-mf-engine` repository (best: it can
read the engine's ratings, holdings and overlap data directly). It also works in an ordinary Claude chat if you upload a
client's CAS PDF (or its parsed JSON) and `funds.json` from aeternawealth.com/data/funds.json.

---

You are building an internal tool for Aeterna Wealth, an AMFI-registered mutual fund distributor (ARN-317889) in
India. Aeterna is **not** a SEBI-registered investment adviser or research analyst. Its recommendations are incidental to
distribution and must be suitable for the client. The founders are a Chartered Accountant and an advocate.

The tool takes a client's Consolidated Account Statement (CAS) and produces a rebalance and new-money plan for a
goal: retirement, a child's education, a house, or plain wealth growth. It covers SIPs, lump sums and STPs, and it
says what to sell, switch, keep and start, with reasons. It is used by Aeterna staff with the client in the room. It
is not a public robo-adviser.

## Work in this order. Show each step's output to me before going on.

### 1. Think from first principles first (write this down as `docs/rebalance_principles.md`)

Before any code, write a short note answering:

- **What is a rebalance for?** Name the reasons that justify one. At least:
  1. allocation drift outside a band,
  2. the goal's glide path (less equity as the goal approaches),
  3. redundancy (too many funds, high overlap),
  4. a broken fund (mandate breach, manager exit, merger, sustained bottom-quartile record, style drift),
  5. cost (a high expense ratio for the category),
  6. tax (harvesting the yearly LTCG exemption, using up losses).
- **What does it cost?** Capital gains tax, exit loads, days out of the market, and the behavioural cost of churn.
  The rule: act only when the expected benefit clearly beats the cost. Steer new money first (cash-flow
  rebalancing) and sell only with a written reason.
- **What does past performance tell us?** Our own walk-forward backtest (see `audit/` and `AGENTS.md`) found
  that a high rating at date T had little or no power to predict the next 3 years' excess return. So fund
  selection is about avoiding broken funds and sending new money to sound ones. It is not about chasing last year's
  winner. Use hysteresis: new money goes only to A/A+ funds, but an existing holding is sold only when it is C, or
  has a hard flag, and a thesis supports the sale. A fund that slips from A to B is held.
- **When is a category change justified** (e.g. multi cap to flexi cap, mid cap to large & mid cap)? Only when the
  client's need changes, or the category no longer fits the goal. A fund ranking change alone is not enough.

### 2. Read the CAS

- Use the `casparser` Python package (CAMS and KFintech consolidated CAS PDFs; password-protected, so ask for the
  password at run time and never store it). Fall back to parsing the detailed CAS by hand only if needed.
- Extract every folio, scheme, ISIN, AMFI code, plan (Direct/Regular), option (Growth/IDCW), the full transaction
  history (purchases, SIP instalments, redemptions, switches, dividends, stamp duty, STT), units, current value and
  nominee status.
- Build **tax lots** (FIFO, as Indian tax law requires) for each scheme: purchase date, units, cost.
- Privacy: the CAS contains PAN, email, phone and address. Keep it local, mask PAN in every output
  (`ABCDE****F`), never send it to an external service, and delete the parsed file when the session ends.
  Never commit client data to the repository; put it in a git-ignored `clients/` folder.

### 3. Profile the client and the goal (ask, don't assume)

Ask a short questionnaire and save the answers in the client file:

- Goal type, target amount in today's rupees, target year, and whether money is needed partly earlier.
- Current monthly SIP capacity, expected lump sums, and the emergency fund held outside this portfolio.
- Risk capacity (income stability, dependants, other assets, loans) and risk attitude: one question on how they
  would act in a 35% fall. Combine them into a profile: conservative, moderate, aggressive or very aggressive.
  Capacity caps attitude.
- Tax slab, and realised capital gains already booked this financial year.
- Any funds the client wants to keep for personal reasons.

### 4. Set the target (the "policy")

- Equity / hybrid / debt split from the risk profile **and** years to goal. Use a glide path: for example, start
  cutting equity 5 years before the goal and move the money to short-duration debt or arbitrage funds by the goal
  year. Put the glide path in a table in config so it can be tuned.
- Within equity, a category mix (large, flexi or multi, mid, small, sectoral at most 10%, international at most
  15%) that fits the profile. A very aggressive profile can hold up to about 35% in small caps; a moderate one about
  10%.
- Fund count: 4–7 equity funds for most portfolios. More than 2 funds in one category needs a reason.
- **Bands:** rebalance a sleeve only when it is more than 5 percentage points (or 25% relative) away from target,
  checked once a year and after any 20% market move.

### 5. Score the current portfolio

For each holding, from the engine's data (`site/data/funds.json`; holdings and overlap from
`data/holdings/<month>/_weights.csv`; ratings logic in `engine/protocols.py`):

- rating tier, peer rank, score, 3Y excess vs its index, red flags (mandate breach, closet indexer, credit event),
  expense ratio, Direct vs Regular, and the fund's age.
- pairwise **overlap** (sum of the smaller weight in each common stock) for all equity funds; flag pairs above 50%.
- fund-house concentration: more than 40% of equity with one AMC gets flagged.
- the client's look-through exposure: market-cap mix, top 10 stocks and top sectors across the whole portfolio.

### 6. Decide actions, cheapest first

1. **Redirect new money.** Choose SIP and lump-sum targets that close the gaps to target, from A/A+ funds in each
   needed category, skipping funds with more than 50% overlap with what is kept. Split the SIP across at most 4–5
   funds, with at least ₹2,000 in each.
2. **Lump sums and parked money** (arbitrage, liquid): deploy through a weekly STP over 3–12 months; the longer
   the period, the more the client fears a fall.
3. **Sell or switch only if a reason from step 1 applies**, and compute for each lot:
   - exit load (scheme-specific, usually 1% within 12 months for equity: keep a per-scheme table),
   - tax: equity STCG 20% under 12 months; LTCG 12.5% above ₹1.25 lakh per financial year (after the exemption
     already used); debt funds bought after 1 April 2023 taxed at slab; grandfathering for units bought before
     1 Feb 2018 (cost = higher of cost and 31 Jan 2018 NAV),
   - then: sell now, sell after date X (when the lot turns long-term or its exit load ends), or sell over N
     financial years to use the ₹1.25 lakh exemption each year.
   Prefer lots that are long-term and have the least gain.
4. **Never** move a client from a Direct plan to a Regular plan without saying so plainly: Aeterna earns commission
   on Regular plans, and the client pays it through the expense ratio. Show the cost difference in rupees per year.

### 7. Write a thesis for every change of shape

When the plan changes the category mix (e.g. multi cap to flexi cap, adding a small-cap sleeve, cutting a sectoral
fund), write a thesis of at most 120 words for each change:

- **What changes:** exposure before and after (market-cap mix, style, number of funds, overlap).
- **Why it suits this client:** goal, horizon, risk profile.
- **What it costs:** tax, exit load and rupees, now and with any phasing.
- **What would make us reverse it.**
- **The evidence and its limits:** "ratings measure the track record, not the future".

### 8. Project the goal

- Monte Carlo (at least 5,000 paths) using the monthly returns of the target categories' median funds, from the
  engine's NAV history, with history bootstrapped in 12-month blocks to keep regimes. Show the 10th, 50th and 90th
  percentile corpus and the chance of reaching the goal, for (a) the current portfolio with the current SIP and
  (b) the proposed plan.
- If the chance is below 70%, show the SIP needed to reach 70% and 85%.
- Inflation: 6% by default; education 10%; editable.

### 9. Produce the output

- A client report (HTML first, PDF later) in Aeterna's site style (`site/app.html` tokens; light mode default):
  snapshot, what we found, target vs current, the action list (each line: action, fund, amount, when, tax and load
  cost, reason), the theses, the goal projection, and what we will monitor and when we next review.
- An internal sheet for staff: lot-level tax workings, overlap matrix, and the data dates used.
- Language: plain English. Say "review" or "move", not "sell everything". No "best fund" or "guaranteed" claims.
  Every report ends with: "Mutual fund investments are subject to market risks. Ratings describe past performance
  and are not a forecast. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889),
  not a SEBI-registered investment adviser."

### 10. Test it

- Unit tests for the tax-lot engine (FIFO, the LTCG exemption across two financial years, grandfathering, exit
  load windows), the bands, and the overlap maths.
- Three synthetic clients (conservative retiree with 3 years to go; aggressive 30-year-old with ₹50,000 SIP; a
  messy 16-fund portfolio with a quarter in arbitrage). Show that the plan for each is sensible, explain any surprise,
  and confirm that no plan sells a lot whose tax cost exceeds its stated benefit.
- Run it on one real CAS (I will provide it) and walk me through the result before calling it done.

## Constraints

- Plain Python (pandas allowed), reproducible, every number traceable to a data source and date.
- Configuration (glide paths, bands, category limits, tax rates) in one YAML or Python config file, with the date
  each tax rule was last checked. Tax rules change with each Budget; flag rules older than 12 months.
- Do not change the rating methodology in `engine/` as part of this work. Read from it.
- Ask me only when an answer changes what you build; otherwise pick a sensible default and say which.
