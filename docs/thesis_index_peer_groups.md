# Thesis: two data fixes that change some ratings (25 Nov 2026)

**Recommendation: apply both before the 11 December monthly run.** Neither changes how any fund is scored. Both fix which
funds are compared with which, and which plan line represents a fund. Held on `staging` until the owner approves.

## 1. Index funds: peer groups split by the fund house's name

**What is wrong.** An index fund is compared with the other funds tracking the same index. When its name does not match
an index on the Nifty list (all BSE indices, and a few Nifty names), the engine built the label from the fund name after
removing the fund house's name. That removal missed short forms and punctuation, so funds tracking the same index landed
in groups of their own:

| Today's peer group | Should be | Plans | Rated today |
|---|---|---|---|
| `- BSE SENSEX` (Nippon India Index Fund - BSE Sensex Plan) | BSE SENSEX | 2 | B, "1 of 1" |
| `KOTAK BSE SENSEX` | BSE SENSEX | 2 | B, "1 of 1" |
| `MF BSE SENSEX` (LIC MF) | BSE SENSEX | 2 | B, "1 of 1" |
| `INDIA BSE SENSEX` (Invesco India) | BSE SENSEX | 2 | Unrated (young) |
| `NIFTY` (SBI Nifty Index Fund, tracks the Nifty 50) | NIFTY 50 | 2 | B, "1 of 1"; measured against a peer average, not the Nifty 50 TRI |
| `KOTAK BSE HOUSING` | BSE HOUSING (with UTI) | 2 | B, "1 of 1" |
| `KOTAK BSE PSU` | BSE PSU | 2 | B, "1 of 1" |
| `INDIA NIFTY CHEMICAL` (Invesco India) | NIFTY CHEMICAL | 2 | Unrated |

A fund alone in its group gets B by default and "1 of 1": the rating says nothing. Today 119 index plans have no peers;
after the fix 105 (the rest genuinely track an index no other fund tracks).

**The fix** (`engine/rank.py`, `index_label`): read the index from the fund's name starting at the first index-family
word (NIFTY, BSE, SENSEX, S&P, NASDAQ, MSCI...), so no fund-house name can stay in front; treat spacing as the same index
("NIFTY50 EQUAL WEIGHT" = "NIFTY 50 EQUAL WEIGHT"); and where the label names an index on the Nifty list, use that index's
TRI as the benchmark (SBI Nifty Index Fund moves from a peer-average proxy to the Nifty 50 TRI).

**What moves.** 16 plans (8 funds) change group. Ranks can move in the groups they join: BSE Sensex (13 plans become 21),
Nifty 50 (51 become 53), BSE Housing (2 become 4), BSE PSU, Nifty Chemical: 82 plans in all. No active fund is affected.
The index protocol itself (tracking difference, tracking error, cost, age, size) is unchanged.

## 2. Which growth line represents a plan

**What is wrong.** AMFI lists some schemes with two growth lines per plan: a legacy class (Retail, Institutional) beside
the plan sold today, or a line it stopped pricing. The engine kept the lowest code, which picked the legacy line:

| Fund (Regular plan) | Line the site rates today | Rated today | After the fix |
|---|---|---|---|
| Nippon India Liquid Fund | Retail Plan (legacy class) | C, 35 of 35 | the current Regular plan (code 100851) |
| Nippon India Gilt Fund | Institutional Plan | B, 9 of 21 | the current Regular plan (109720) |
| Nippon India Ultra Short to Short Term Fund | Retail Plan | B, 12 of 20 | the current Regular plan (111753) |
| Sundaram Banking & PSU Debt Fund | a Retail line last priced in June 2024, so the plan was dropped | missing from the site | the live Regular plan (100784) |

**The fix** (`engine/ingest.py`, `build_universe`): prefer a line AMFI still prices, then one that is not a legacy
Retail/Institutional class, then the oldest code. A plan's only line is always kept, whatever it is called (Franklin
labels its Direct plans "Retail Plan Growth" and "Super Institutional Growth"; they stay).

**What moves.** 4 plans: the corrected funds get their own rating (interim from the next daily run, full on 11 Dec), and
the other Regular plans in Liquid, Gilt, Ultra Short to Short Term and Banking & PSU can move a place as the correct
plan takes its rank.

## Tests
`tests/test_universe.py`: a stale lower code does not displace the live plan (Sundaram); a current class beats a legacy
class (Nippon Liquid); a plan's only line is kept (Franklin); Kotak, LIC, Nippon, Invesco and UTI Sensex funds share one
group, SBI Nifty joins Nifty 50, and "Nifty50 Equal Weight" = "Nifty 50 Equal Weight".

## After approval
Merge to `main` before 11 December; the monthly run re-rates and `outputs/latest/revision_report.md` lists every change
fund by fund, with this note as the reason.
