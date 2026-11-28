# Thesis: rating PMS strategies, method v2 (27 Nov 2026)

v1 (draft of 26 Nov) measured every equity strategy against Nifty 500 TRI and ranked debt and hybrid strategies only
against each other. The owner asked for a separate method per asset class, risk-adjusted and as forward-looking as
the data allows, with a set review cycle. v2 does that. Evidence: `audit/pms/walkforward.py`,
`audit/pms/compare_models.py`; v1 to v2 rating changes: `audit/pms/v1_v2_movers.csv` (83 of 321).

## What is rated (unchanged)
- Source: APMI's monthly reports (every PMS strategy, as SEBI requires): assets and time-weighted returns after all
  fees, before tax. Complete from April 2023.
- Shown: strategies with Rs 100 crore or more (kept until below Rs 75 crore).
- Rated: discretionary, 3-year return reported, 24+ months of monthly record. Not rated (listed with the reason):
  non-discretionary, too young, liquid strategies, and "equity" strategies that do not behave like stock portfolios.

## One yardstick per asset class
| Asset class | Yardstick | Peer group |
|---|---|---|
| Equity | The style index the strategy tracks most closely over its record (lowest tracking error): Nifty 50, Nifty 500, Nifty 500 Multicap 50:25:25, Nifty Midcap 150 or Nifty Smallcap 250 TRI | Large and multi cap (Nifty 50 / 500 / Multicap fits) or Mid and small cap (Midcap 150 / Smallcap 250 fits) |
| Debt | The median high-quality bond mutual fund (corporate bond, banking & PSU, short duration; all plans), month by month | Debt |
| Hybrid and multi-asset | The strategy's own mix of Nifty 500 TRI and the bond yardstick, equity share fitted in 5% steps by least tracking error | Hybrid and multi-asset |

Why: a small-cap manager beating Nifty 500 in a small-cap rally is not skill; against Nifty Smallcap 250 it has to
beat its own market. A debt strategy is compared with what an investor would otherwise hold (a good bond fund). A
hybrid strategy is judged against the passive mix with the same equity exposure, so a high-equity strategy does not
win just because shares rose. The style is read from the returns (no labels exist in APMI data).

## Scores (percentile within the peer group; weights)
- Equity (skill 70, risk 30): alpha over the style index (beta-adjusted) 20; information ratio 15; share of months
  ahead 15; share of rolling 12-month spells ahead 10; lead in both halves of the record 10; down capture (lower is
  better) 10; volatility (lower) 10; worst fall compared with the index's worst fall 10.
- Debt: return over the bond yardstick 25; Sortino 20; information ratio 15; 12-month spells ahead 15; worst fall 15;
  volatility (lower) 10.
- Hybrid and multi-asset: alpha over its mix 20; information ratio 15; 12-month spells ahead 15; Sortino 15; worst fall
  compared with the mix 15; down capture 10; volatility (lower) 10.

## Tiers and guards
A+ top 10% of the peer group and score 70+; A top 30% and 55+; C bottom 30%; B the rest. A or A+ also needs a lead
over the yardstick over 3 years and a positive alpha over the whole record (otherwise B). Money-flow guard (applied
every month): clients withdrew more than 30% of the assets in 12 months: held at B, reason shown.

## Review cycle
- Data and every metric on the pages: monthly (the 20th, when APMI has the previous month).
- Ratings: quarterly, on data to March, June, September and December (published around 20 April, July, October,
  January). First review: data to October 2026; next: December 2026.
- Buffer: at a review a strategy keeps its tier unless its percentile moves 5 points past the boundary (and its score
  5 points past the score line). Tested on the walk-forward panel (24-month records): monthly reviews moved 199% of
  strategies a year (each about twice); quarterly 119%; quarterly with the 5-point buffer 73%.
- Between reviews: a strategy newly eligible waits for the next review; the money-flow guard and the Rs 75 crore
  floor apply at once (material changes are not held for the quarter).

## Evidence: did these measures line up with the next 12 months?
Panel: every discretionary equity strategy with Rs 100 crore+ and 24 months of record at each month-end from March
2025 to March 2026 (13 formations, about 300 strategies each, including ones that later shrank); forward = the next
12 months' excess return over its style index.
- Return-quality measures were positive in every formation: months ahead (rank correlation 0.16), up capture 0.13,
  alpha 0.12, information ratio 0.12, 12-month spells ahead 0.10. The trailing 1-year return, what PMS sites rank on,
  was the weakest (0.06, and negative against Nifty 500).
- Risk measures predicted risk: past volatility and tracking error lined up with the next year's worst fall (-0.29),
  past worst fall +0.22.
- Composite: v2 0.12 (excess) and 0.09 (worst fall) against v1 0.10 and 0.06. Top 30% by v2 beat their style index
  over the next 12 months 64% of the time (median +2.0 points a year); bottom 30% median -0.3.
- Honest limit: 13 overlapping formations are about one and a half independent years in one market. This shows
  the measures are sensible, not that they forecast. Ratings stay described as track-record assessments.

## Known limits (on the method page)
- 43 months of data: one long rise and one fall. Survivorship: closed strategies drop out of APMI's reports.
- No holdings, fees or cap-size labels in APMI data. The bond yardstick is high-quality; credit strategies earn part
  of their lead from credit risk, which the worst-fall and volatility measures only partly capture.
- Returns are the strategy's; a client's own return differs with timing and fee plan.

## Asked of the owner
Approve v2, or change: the Rs 100 crore line, the weights, the quarterly cycle and buffer.
