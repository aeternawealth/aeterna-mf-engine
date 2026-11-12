# Rebalancing: first principles

The rules the rebalance tool (`rebalance/`) is built on. Written 12 Nov 2026. Change the rules here first, then the code.

## 1. What a rebalance is for

A portfolio exists to reach a goal with risk the client can live with. A rebalance is justified only by one of six
reasons. Every action in a plan names its reason.

| # | Reason | Example | Typical action |
|---|---|---|---|
| R1 | **Drift**: a sleeve is outside its band | small caps grew from 30% to 42% | steer new money elsewhere; sell only if new money can't close it within a year |
| R2 | **Glide path**: the goal is getting closer | 4 years to a child's college fees | move equity to debt/arbitrage step by step |
| R3 | **Redundancy**: too many funds or too much overlap | 16 funds; two mid-cap funds share 60% of their stocks | stop the weaker one, merge into the stronger |
| R4 | **Broken fund**: the reason we held it no longer holds | mandate breach two months running, manager exit, merger, bottom 30% of peers with no recovery | stop new money now, exit when tax and exit load allow |
| R5 | **Cost**: the fund costs much more than similar funds | expense ratio 0.8 points above the category median | prefer a cheaper fund for new money |
| R6 | **Tax**: free gains are available | ₹1.25 lakh of long-term gains is tax-free each financial year | book gains up to the limit and buy back |

"The fund did badly last year" is not on the list. Neither is "a better fund exists".

## 2. Every sale has a price

- **Tax**: equity gains held under 12 months are taxed at 20%; over 12 months, 12.5% above ₹1.25 lakh a year
  (plus 4% cess). Debt funds bought after 1 April 2023 are taxed at the client's slab rate whatever the holding period.
- **Exit load**: usually 1% on equity units held under a year.
- **Time out of the market** between sale and purchase, and the behavioural cost: clients who churn tend to buy
  after rises and sell after falls.

So the order of preference is:

1. **Redirect new money** (SIP, lump sums, maturing money) towards what is short. This costs nothing.
2. **Deploy parked money** (arbitrage, liquid) through a weekly transfer.
3. **Sell**, only with a named reason, choosing the cheapest lots (long-term, smallest gain) and timing sales so
   that lots first become long-term and exit loads end.

A sale goes ahead only if its benefit clearly beats its cost. When the benefit can't be measured (e.g. "fewer funds"),
the tool sells only if the cost is under 0.5% of the amount sold, or waits until it is.

## 3. What past performance can and can't tell us

Our own walk-forward backtest (`audit/`, 2019–2025) found that a high rating at date T predicted the next three years'
excess return only weakly, and the older model not at all. What the record is good for:

- spotting **broken** funds: mandate breaches, chronic underperformance, closet indexing, a style that drifted;
- picking **sound** funds for new money, among which the differences are mostly noise.

So the tool uses **hysteresis**:

- New money goes only to funds rated A+ or A in their peer group.
- An existing fund rated B is **held**: no new money, no sale.
- A fund rated C, or with a hard flag, is a candidate for exit, and only with a thesis and an acceptable cost.
- Unrated funds (too young) are held and reviewed once they have a 3-year record, unless they are too small to matter.

## 4. Shape before funds

Decide the **shape** (how much in equity, and within equity how much in large, flexi/multi, mid and small caps) from
the client's risk profile and years to the goal. Choose funds after that. A change of shape, such as moving from multi
cap to flexi cap or adding a small-cap sleeve, needs a written thesis covering:

- what changes in exposure,
- why it suits this client,
- what it costs,
- what would make us reverse it.

A ranking change alone never changes the shape.

## 5. Fewer, distinct funds

- 4–7 equity funds is enough for almost anyone. More funds mostly add overlap.
- Two funds that share more than half their stocks count as one bet.
- At most 40% of equity with one fund house: a house style can go out of favour for years.

## 6. The goal decides the risk

- Risk **capacity** (income, dependants, other assets, years to goal) caps risk **attitude**. A client who wants
  to be aggressive but needs the money in three years gets a conservative plan.
- The equity share falls as the goal approaches (the glide path in `rebalance/config.py`).
- The emergency fund (3–6 months of expenses) sits outside the plan, in a liquid fund or the bank.

## 7. What the tool never does

- Move a client from a Direct plan to a Regular plan without saying so plainly. Aeterna earns commission on
  Regular plans, and the client pays it through the expense ratio. The report shows that cost in rupees.
- Promise returns or call a fund the "best". Projections are ranges from history, not forecasts.
- Store a CAS, its password or a PAN in the repository.
