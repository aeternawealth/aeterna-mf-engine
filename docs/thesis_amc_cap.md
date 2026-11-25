# Thesis: cap ratings at fund houses whose schemes all move together? (25 Nov 2026)

**Recommendation: do not cap. Keep the fund-house watch as information, and use it when building portfolios.**

## The idea
Every few years one fund house tops the return tables across all its schemes, attracts a wave of money, and then falls
to the bottom (Aditya Birla Sun Life 2016–17, Axis 2018–20, Canara Robeco 2019–22, Quant 2021–23). If one house view
drives every scheme, the schemes rise and fall together, so a rating that looks at each fund alone misses the shared risk.
Proposed rule: a fund rated A or A+ is capped at B when its house's schemes move together (herding 0.40 or more), or when
the house is also top of the tables ("hot house").

## The evidence (audit/amc_cycles.py, audit/bt_amc_cap.py)
- Leadership does not last. The #1 fund house on 3-year returns at each year-end 2009–2025 averaged the 46th percentile
  over the next 3 years; since 2013, last-3-year rank and next-3-year rank are uncorrelated on average (0.00), and
  negative in 2020–21 (−0.4).
- The cap, back-tested on 642 fund-years (2010–2024) in the top 30% of their category (a stand-in for A/A+):

| Trigger | Funds capped | Next 1Y percentile (capped / others) | Next 3Y percentile | Fell to bottom 30% within 3Y |
|---|---|---|---|---|
| House herding ≥ 0.40 | 143 | 53 / 54 | 49 / 53 | 37% / 24% |
| Top quarter of herding that year | 171 | 54 / 54 | 52 / 52 | 33% / 25% |
| Hot house (top 3 on returns) | 216 | 56 / 53 | 53 / 52 | 28% / 27% |
| Hot house and herding ≥ 0.40 | 78 | 55 / 54 | 48 / 53 | 41% / 25% |

## Reading it
- What herding predicts is the **tail**, not the average: a top fund from a house whose schemes move together was about
  1.5 times as likely to end in the bottom 30% three years later (37–41% against 24–25%).
- The average gap is small (4–5 percentile points) and not reliable: by year it worked in 2010, 2014, 2019 and 2022 and
  went the wrong way in 2013, 2015 and 2018 (Axis kept winning for a year after it was flagged). Over the next 1 year,
  capped funds did as well as the rest, so a cap would have pushed investors out of funds still going up.
- Being a hot house alone predicts nothing.
- Small samples: 78 fund-years for the combined trigger, mostly from 2018–2022. Merged and closed schemes are missing,
  which hides some of the worst outcomes, so the true tail risk is probably larger.

## Decision
1. No rating cap: the average effect is too small and unstable, and it would have cost returns in the following year.
2. Show it: the fund-house watch on every fund-house page and the comparison table on /mutual-funds/amc/ (done).
3. Use it where the tail risk matters, in portfolios: the rebalance tool already allows one fund per fund house for new
   money; add a check that no more than one fund comes from a house scoring 0.40 or more, and say why in the client report.
4. Revisit at the June 2027 review with 6 more months of data, and test a softer rule (A+ to A, not to B).
