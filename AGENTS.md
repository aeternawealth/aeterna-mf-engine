# Aeterna MF Engine: agents & protocols

An internal Aeterna tool that ranks every open-ended equity fund and equity index fund in India within its SEBI category. It refreshes monthly and shows Regular and Direct plans side by side.

## Agents (monthly run)

| # | Agent | What it does | Implemented in |
|---|---|---|---|
| 1 | Data | Pulls the AMFI scheme master (`NAVAll.txt`), daily NAV history for each scheme (mfapi.in), and Total Return Index (TRI) history for every Nifty index (niftyindices.com). | `engine/ingest.py` |
| 2 | Data-check | Excludes stale NAVs (merged or wound-up schemes), ETFs, FoFs, IDCW options and debt index funds. Pairs the Direct and Regular plans of each scheme. | `ingest.build_universe`, gates in `rank.py` |
| 3 | Metrics | Computes rolling returns, alpha vs TRI, capture ratios, drawdowns and tracking metrics in plain Python, so every number can be reproduced. | `engine/metrics.py` |
| 4 | Category protocols | One scoring rulebook per category type (see below). | `config.py`, `protocols.py` |
| 5 | Qualitative | A Claude session reads factsheets and news for fund-manager exits, mergers, mandate changes and SEBI actions, and writes them to `data/manual/flags.csv`. A flagged fund can't be rated A or A+. | Monthly scheduled task |
| 6 | Ranking committee | Converts each metric to a percentile within its peer group, blends the percentiles into pillar scores and a 0–100 score, then applies red-flag overrides and assigns a tier. | `protocols.py` |
| 7 | Publishing | Writes `outputs/<YYYY-MM>/rankings.{csv,xlsx,json}` and the dashboard. | `rank.write_outputs` |
| 9 | Holdings | Parses each AMC's monthly portfolio Excel files (SEBI format) and matches every portfolio to its scheme. Computes concentration, market-cap mix (from the AMFI list), cash, the top sector, active share, month-on-month turnover and style drift, and checks each fund against its SEBI mandate. | `engine/holdings.py` |
| 10 | AMC downloader | Finds each AMC's portfolio page through advisorkhoj's index, downloads that month's Excel/ZIP with a headless browser, and logs any failures. | `engine/amc_downloader.py` |
| 11 | AMFI extras | Pulls expense ratios (matched by ISIN), quarterly average AUM and the half-yearly market-cap list via `amfipy`. | `engine/extras.py` |
| 8 | Validation | Walk-forward backtest: does a high score at date T predict better 3-year forward excess return? | `engine/backtest.py` |

## Peer groups & benchmarks (TRI)

| Category | Benchmark (TRI) |
|---|---|
| Large Cap | Nifty 100 |
| Large & Mid Cap | Nifty LargeMidcap 250 |
| Mid Cap | Nifty Midcap 150 |
| Small Cap | Nifty Smallcap 250 |
| Multi Cap | Nifty500 Multicap 50:25:25 |
| Flexi, Focused, ELSS, Value, Contra, Dividend Yield | Nifty 500 |

- **Sectoral/Thematic funds** are split into theme buckets (Banking, Pharma, Tech, Infra, Consumption, PSU, MNC, and so on), each with its own sector TRI where one exists. A theme with fewer than 4 funds goes into "Other Themes".
- **Index funds** are grouped by the index they track and measured against that index's TRI. For indices not on Nifty (e.g. BSE indices), the benchmark is a proxy built from the median daily return of peer funds.
- **Ranking happens within peer group × plan.** Regular plans are ranked against Regular plans, and Direct against Direct.

## Protocols (weights renormalise if a metric is unavailable)

**Active equity protocol**

| Pillar | Weight | Metrics |
|---|---|---|
| Return quality | 40 | Median rolling 3Y excess vs TRI (14), % of rolling 3Y windows beating TRI (10), 3Y information ratio (10), 5Y excess CAGR (6) |
| Risk | 30 | 3Y downside capture (10, lower is better), 3Y Sortino (8), 5Y max drawdown (7), 10th-percentile rolling 3Y excess (5) |
| Consistency | 15 | % of rolling 1Y windows beating TRI (8), 3Y upside capture (7) |
| Cost | 10 | Expense ratio (TER) |
| Stability | 5 | Fund age (3), AUM (2) |

**Portfolio pillar** (added to every active protocol when holdings data exists): active share (5), mandate compliance (3), cash drag (2), monthly turnover (2). The Small/Mid protocol also penalises the weight in stocks ranked beyond 500 (3), as a liquidity risk.

**Small/Mid protocol:** downside protection gets more weight (downside capture 12, drawdown 9). Large AUM is a mild penalty rather than a plus, because of capacity constraints in small and mid caps.

**Index protocol:** 1Y tracking difference (35), 1Y tracking error (30), 3Y tracking difference (10), TER (15), age (5), AUM (5).

## Gates, tiers, red flags

**Gates.** A fund is shown as *Unrated* if either applies:

- It has less than 3 years of history (less than 1 year for index funds).
- Its NAV is more than 10 days older than the latest market date.

**Tiers** are based on the fund's rank within its peer group:

| Tier | Requirement |
|---|---|
| A+ | Top 10% of the peer group and score ≥ 70 |
| A | Top 30% and score ≥ 55 |
| B | Middle of the peer group |
| C | Bottom 30% |

**Red flags:**

| Flag | Trigger | Effect |
|---|---|---|
| Chronic underperformer | Rolling 3Y hit rate below 25% and median excess below −2% | Avoid |
| Risk without reward | Downside capture above 110% and information ratio below 0 | Avoid |
| Deep drawdown | Max drawdown more than 5 percentage points worse than the peer group's 10th percentile | Capped at B |
| Mandate breach | Portfolio breaks the SEBI category rule (e.g. a small-cap fund with less than 65% in small caps, or a focused fund with more than 30 stocks) in **two consecutive monthly portfolios** (Nov 2026) | Capped at B |
| Mandate watch | The same, in the latest month only | Shown on the site; no cap |
| Closet indexer | Active share below 50% (30% for large caps) and no 3-year excess return over the benchmark | Capped at B |
| Turnaround unproven | Chronic rolling underperformance, but a positive 3-year excess return recently | Capped at B |
| Manual / qualitative flag | Raised by the qualitative agent | Rating becomes Watch (if it was A or A+) |

## Holdings inputs

- `data/holdings/<YYYY-MM>/`: the AMC monthly portfolio Excel files, saved exactly as downloaded (any file names). After each run, check `_mapping_report.csv` to see which portfolios didn't match a scheme.
- `data/manual/amfi_mcap.xlsx`: AMFI's half-yearly list of stocks by average market cap (published in January and July).
- **Active-share benchmark:** taken from the holdings of the index funds that track the category benchmark, so those index funds' portfolio files are needed too. Without them, active share is measured against the average portfolio of peer funds.

## Optional inputs (`data/manual/`)

- `ter.csv` with columns `code, ter`
- `aum.csv` with columns `code, aum_cr`
- `flags.csv` with columns `code, flag, note`

## Run

```
pip install -r requirements.txt
python run_monthly.py              # fresh data -> outputs/YYYY-MM/
python run_monthly.py --backtest   # + validation
python run_monthly.py --offline    # reuse cached data
```

## Roadmap

- **v2 (built):** Holdings agent. Next: days-to-liquidate using exchange volumes, and fund-to-fund overlap.
- **v3:** Debt funds: credit quality, YTM vs duration, and AMC credit-event history.
- **v4:** Tune the weights based on the backtest, reviewed quarterly.

## v3 changes (November 2026 audit). These supersede the protocol tables above.

**Active equity weights:**

| Pillar | Metric | Weight |
|---|---|---|
| Long-run excess | Median rolling 3Y excess vs TRI | 15 |
| | Rolling 3Y hit rate | 10 |
| Risk-adjusted | Information ratio, 3Y | 15 |
| | Capture ratio (up ÷ down), 3Y | 12 |
| | Jensen's alpha, 3Y | 8 |
| Consistency | Worst-decile rolling 3Y excess | 10 |
| | Rolling 1Y hit rate | 10 |
| Cost | TER | 10 |
| Portfolio (when holdings exist) | Active share 4, mandate 3, cash 2, turnover 1 | 10 |

**Removed:** Sortino, upside and downside capture, max drawdown, 5Y excess, age, AUM. They duplicated other inputs or rewarded low beta.

**Rolling windows:** every fund is measured on the same window end-dates (last 3 years). A fund with less than 90% coverage gets no rolling metric.

**Tier rules:**
- Absolute guard: A+ needs positive 3Y excess and positive median rolling excess; A needs one of the two; otherwise the fund is capped at B.
- "Avoid" removed (it was anti-predictive in the backtest). Hard flags now cap a fund at C.
- Chronic underperformer now also requires the fund to be in the bottom 40% of its peers.

**Peer groups:**
- Value and Contra are merged into one peer group.
- Themes with fewer than 6 rated funds are pooled into "Other Themes".
- AMC names are stripped before theme matching.

**Holdings:**
- Mandate checks allow a 3-point tolerance.
- Stacked-sheet and multi-file parsers added.
- Validation quarantines suspect portfolios.

**Backtest** (`audit/`), 2019–2025: no predictive value (3Y IC −0.08). Present ratings as track-record assessments, not forecasts.

## v4 changes (November 2026): hybrid and debt funds

**Three families, three yardsticks.** Every fund is ranked only within its SEBI category × plan type.

| Family | Benchmark | Protocol (weights) | History needed |
|---|---|---|---|
| Hybrid (aggressive hybrid, balanced advantage, multi asset, balanced hybrid, equity savings, conservative hybrid) | Composite: Nifty 50 TRI + median bond fund (corporate bond, banking & PSU) or, for equity savings, median liquid fund. Equity shares 65 / 50 / 60 / 50 / 35 / 20% | Return 35 (rolling 3Y median excess 15, 3Y hit rate 10, IR 10), Protection 35 (downside capture 15, max drawdown 10, capture ratio 10), Consistency 10 (rolling 1Y hit rate), fee (base expense ratio) 10 | 3 years |
| Arbitrage | Nifty 50 Arbitrage index (or median arbitrage fund) | Rolling 1Y excess 25, 3Y excess 15, 1Y hit rate 10, volatility 10, loss months 5, fee 25, size (capped Rs 5,000 cr) 10. A/A+ must beat the median liquid fund after tax (30% slab) | 3 years |
| Debt (17 SEBI 2026 categories; old names mapped to new) | Median fund of the same category and plan type, on a business-day calendar | Cash-like (overnight, liquid, money market, ultra short, ultra short to short term): return 30, consistency 25, cost 25, worst own day 10, size 10. Duration: return 30, consistency 25, falls 25, cost 20. Credit risk: falls 35 | 3 years (1 for overnight, liquid, money market) |

- **Credit event** (debt): a day in the last 5 years when the fund fell far below its category median (0.4% cash-like, 0.8% duration, 1.2% long), excluding days when the median gilt fund moved 0.4% or more (rate shocks). Capped at B. Gilt funds are not checked.
- **Median series** (`metrics.median_series`): every median-fund yardstick is built on one business-day calendar. Liquid and overnight funds publish NAVs every calendar day; mixing them with business-day funds double-counted weekend interest (the median liquid fund was 1.2% a year too high before Nov 2026).
- Debt NAV face-value changes (one-day moves of -40% or more, or +60% or more) are removed before any metric (`metrics.debt_clean`).
- Hybrid and debt funds: equity portfolio analytics (active share, market-cap mix, mandate checks) are not used.
- Tax shown per fund: equity (65%+ Indian equity), other (non-equity, non-debt), debt (slab rate).

## Audit protocol (November 2026): every change, every run

Do this without being asked.

- **Before every publish to `main`:** build the site and run `python tools/audit.py`. Nothing marked FAIL may go live. Look at every CHECK line, confirm the flag is real, and fix it or explain it in the reply.
- **Before telling the owner a change is done:** check it as a visitor would, in a real browser, at phone width (390px) and desktop width, in dark and light mode. That covers hidden elements, overlapping labels, sideways scrolling, placeholder text ('nan', 'undefined', 'None') and script errors.
- **Rating changes:** for every fund that is #1 in its group or scores 75+ but is not A+, the reason must be a real flag, shown on its page. A portfolio flag must survive data gaps: holdings missing from AMFI's market-cap list count towards the rule.
- **Every run:** the daily and monthly workflows run the audit after building the site (`outputs/latest/audit.md`). The monthly run also writes `outputs/latest/revision_report.md`: what changed in the ratings and why, fund by fund. The monthly scheduled check emails it to the owner.
- **When ratings change:** on the 11th (after fund houses publish portfolios by the 10th) and the 16th (late portfolios). Daily runs update NAVs and returns only.
- **Publishing (owner's standing approval, 11 Nov 2026):** the owner has approved publishing without asking each time. Work on `staging`, run the audit, and publish to `main` when nothing is marked FAIL. Keep the live site's data when merging (take `outputs/`, `site/data/`, `site/dist/`, `data/` from `main`). Then tell the owner what went live. Changes to the rating method still get a test and a written explanation first.
- **Keep staging in step with live:** after every publish to `main`, merge `main` back into `staging` (live data included), so staging always holds everything that is live plus the work in progress. Before starting new work, run `git log origin/staging..origin/main`: it should list nothing but the daily data refreshes. Never commit a code change directly to `main`. If a publish holds back a file that is still in testing on staging, merge `main` back with that file kept from staging (`git checkout staging -- <file>` before committing the merge), or the merge undoes the work in progress.
