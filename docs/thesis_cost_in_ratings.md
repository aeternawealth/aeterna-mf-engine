# Thesis: should cost be a rating input? (13 Nov 2026)

Prepared for the owner. **No rating has been changed.** This note sets out the evidence for a decision.

## The question

Every return a fund reports is after its costs: the expense ratio comes out of the NAV daily. So a rating built on
returns already "charges" each fund for its costs. Adding the expense ratio as a separate input could count cost twice.

## Where cost is used today

| Family | Cost weight | Notes |
|---|---|---|
| **Equity (all categories, model v8)** | **none** | Rated on momentum against the index, upside capture and size tilt, all from returns after costs. The 10% cost weight was in the old v3 model, retired in November 2026. |
| Hybrid | 10% (fund fee) | |
| Arbitrage | 25% (fund fee) | trading taxes are already in the returns |
| Debt | 20–25% | |
| Index funds | 20% | |

## What removing cost would change (current data)

Scored offline with the engine's own functions (the offline scores reproduce 93% of the live tiers; the rest are
rule overrides applied only in the live run).

| Family | Rated plans | Tier changes | A/A+ before → after |
|---|---|---|---|
| Hybrid | 218 | 16 (7%): 10 up, 6 down | 68 → 71 |
| Debt | 592 | 185 (31%): 94 up, 91 down | 182 → 187 |
| Arbitrage | 52 | 22 (42%): 11 up, 11 down | 15 → 16 |

## Does cost tell us anything about the future?

A rating is useful if it points to the funds that do better next. For every fund with three years of NAVs, each year's
return was measured against its peer group's median (same category, same plan type). Then, within each peer group:
does last year's relative return predict next year's, does the expense ratio predict next year's, and does the expense
ratio add anything once past returns are known? Rank correlations (0 = no link; negative = higher cost, lower next-year
return), for 2024→25 and 2025→26:

| Family | Past year → next year | Cost → next year | Cost's extra signal, given past returns |
|---|---|---|---|
| Debt (591 funds) | 0.28 / 0.41 | −0.22 / −0.28 | −0.20 / −0.19 |
| Arbitrage (52) | 0.76 / 0.47 | −0.14 / −0.22 | −0.19 / −0.15 |
| Hybrid (218) | 0.00 / 0.43 | −0.41 / −0.36 | −0.41 / −0.20 |

Script: `tools/cost_test.py`; data: `data/nav/`, current expense ratios.

## Reading it

- **The double-counting argument is right about the past and wrong about the future, in these three families.**
  Debt, arbitrage and hybrid funds within a category earn very similar returns before costs. The expense ratio is the
  most persistent difference between them, so it predicts next year's relative return even after last year's return
  is known. In both test years, in all three families.
- **Equity is different, and the model already reflects it:** manager skill and style dominate, and the live equity
  ratings use no cost input. A manager who beats the index by 6% after a 1% fee is rated on the 6%.
- **It does not set Regular against Direct.** Plans are rated separately: a Regular plan is compared only with other
  Regular plans. The cost input separates one Regular plan from another, never Regular from Direct.

## Recommendation

Keep cost as it is in debt, arbitrage and hybrid ratings, and keep equity ratings free of cost. Index funds: unchanged
(not part of the business; their rating is cost and tracking by nature).

Caveats: two test years; current expense ratios used for both years (they change slowly, but this flatters cost a
little). A fuller test would use month-end expense ratios from AMFI's history.

**Decision for the owner:** keep as is (recommended), or remove cost from hybrid only (the smallest change, 16 plans;
but hybrid is where cost predicted best).
