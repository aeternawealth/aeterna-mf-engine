"""Aeterna MF Engine - configuration: categories, benchmarks, protocols, weights.

Every number the engine produces is computed deterministically in Python from
public data. The weights below are the "house view" and are meant to be
reviewed against the walk-forward backtest (backtest.py) each quarter.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
NAV_DIR = DATA / "nav"
MANUAL = DATA / "manual"          # optional ter.csv / aum.csv / flags.csv dropped by hand or by an agent
OUT = ROOT / "outputs"

NAVALL_URL = "https://portal.amfiindia.com/spages/NAVAll.txt"
MFAPI_URL = "https://api.mfapi.in/mf/{code}"
TRI_URL = "https://www.niftyindices.com/BackPage/getTotalReturnIndexString"
TRI_LIST_URL = "https://www.niftyindices.com/BackPage/gethistoricaltypeindexdata"
TRI_GROUPS = ["Broad Market Indices", "Sectoral Indices", "Strategy Indices", "Thematic Indices"]
HISTORY_START = "01-Jan-2013"

HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AeternaMFEngine/1.0",
    "Accept": "application/json, text/plain, */*",
}

# ---------------------------------------------------------------------------
# Category normalisation. AMFI uses two naming generations ("Equity Scheme -
# Large Cap Fund" and "Equity Schemes - Large Cap Fund"); we key on keywords.
# Order matters: first match wins.
# ---------------------------------------------------------------------------
CATEGORY_RULES = [
    ("large & mid", "Large & Mid Cap"),
    ("large cap", "Large Cap"),
    ("mid cap", "Mid Cap"),
    ("small cap", "Small Cap"),
    ("multi cap", "Multi Cap"),
    ("flexi cap", "Flexi Cap"),
    ("focused", "Focused"),
    ("elss", "ELSS"),
    ("value", "Value"),
    ("contra", "Contra"),
    ("dividend yield", "Dividend Yield"),
    ("sectoral", "Sectoral/Thematic"),
    ("thematic", "Sectoral/Thematic"),
]
INDEX_CATEGORY_KEYS = ["index funds - equity", "other scheme - index funds"]
# Hybrid categories handled so far (AMFI raw-category keyword -> our category). Debt and the other hybrid
# categories follow; each needs its own yardstick and protocol before it is added.
HYBRID_RULES = [("arbitrage", "Arbitrage")]
# Three master categories for the site: every category maps to one
ASSET_CLASS = {"Arbitrage": "Hybrid"}   # everything else (equity categories, equity index funds) -> "Equity"
LIQUID_CATEGORY_KEY = "liquid fund"     # AMFI raw category of the liquid funds used as the arbitrage yardstick

# Benchmark (Total Return Index) per category - SEBI tier-1 style benchmarks.
CATEGORY_BENCHMARK = {
    "Large Cap": "NIFTY 100",
    "Large & Mid Cap": "NIFTY LARGEMIDCAP 250",
    "Mid Cap": "NIFTY MIDCAP 150",
    "Small Cap": "NIFTY SMALLCAP 250",
    "Multi Cap": "NIFTY500 MULTICAP 50:25:25",
    "Flexi Cap": "NIFTY 500",
    "Focused": "NIFTY 500",
    "ELSS": "NIFTY 500",
    "Value": "NIFTY 500",
    "Contra": "NIFTY 500",
    "Dividend Yield": "NIFTY 500",
    "Sectoral/Thematic": "NIFTY 500",
    "Arbitrage": "NIFTY 50 ARBITRAGE",   # SEBI tier-1 benchmark; falls back to the median arbitrage fund if absent
}

# Thematic sub-buckets so a pharma fund is compared with pharma funds.
THEME_RULES = [
    (["bank", "financial", "finserv", "bfsi"], "Banking & Financials", "NIFTY FINANCIAL SERVICES"),
    (["pharma", "health"], "Pharma & Healthcare", "NIFTY HEALTHCARE INDEX"),
    (["technology", "digital", " it ", "tech"], "Technology", "NIFTY IT"),
    (["infra", "infrastructure"], "Infrastructure", "NIFTY INFRASTRUCTURE"),
    (["consumption", "consumer", "fmcg"], "Consumption", "NIFTY INDIA CONSUMPTION"),
    (["psu", "public sector"], "PSU", "NIFTY PSE"),
    (["mnc"], "MNC", "NIFTY MNC"),
    (["manufactur"], "Manufacturing", "NIFTY INDIA MANUFACTURING"),
    (["business cycle"], "Business Cycle", "NIFTY 500"),
    (["quant"], "Quant / Factor", "NIFTY 500"),
    (["momentum"], "Momentum", "NIFTY 500"),
    (["esg"], "ESG", "NIFTY 500"),
    (["international", "global", "us ", "nasdaq", "overseas"], "International", None),
    (["energy", "power"], "Energy", "NIFTY ENERGY"),
    (["defence"], "Defence", "NIFTY INDIA DEFENCE"),
]
THEME_MIN_PEERS = 4   # below this, thematic funds are ranked in the broad "Other Themes" bucket
THEME_MIN_RATED = 6   # a theme needs >= 6 rated (3Y+) funds per plan to be its own peer group
MERGE_PEER_GROUPS = {"Contra": "Value / Contra", "Value": "Value / Contra"}  # SEBI: an AMC may run a value OR a contra fund - same job

# ---------------------------------------------------------------------------
# Gates & tiers
# ---------------------------------------------------------------------------
MIN_HISTORY_YEARS_ACTIVE = 3.0
MIN_HISTORY_YEARS_INDEX = 1.0
STALE_NAV_DAYS = 10             # NAV older than this vs latest market date -> excluded
# Absolute guard: A+ must have beaten its benchmark on BOTH the recent 3Y CAGR and the median rolling 3Y window;
# A must have beaten it on at least one. Otherwise the tier is capped at B (relative rank alone is not enough).
ABSOLUTE_GUARD = True
TIER_CUTS = [                   # (label, min percentile rank of blended score within peer group, min score)
    ("A+", 0.90, 70),
    ("A", 0.70, 55),
    ("B", 0.30, 0),
    ("C", 0.0, 0),
]

# ---------------------------------------------------------------------------
# Protocols: metric -> (pillar, weight, higher_is_better)
# Weights inside a protocol need not sum to 100; they are renormalised over
# the metrics actually available for that fund (e.g. if TER is missing).
# ---------------------------------------------------------------------------
# v3 (audit Nov-2026). Changes vs v1:
#  * de-duplicated: 3Y excess, 3Y IR and 3Y Sortino are 0.95-0.98 rank-correlated within a peer group -> IR only;
#    upside capture (0.71 corr. with beta) dropped; fund age and AUM dropped (no performance content; AUM is
#    0.81 correlated with low TER = double-counted cost).
#  * beta-neutral risk: raw downside capture and max drawdown mostly reward LOW BETA (a cheap, passive exposure)
#    and were the most anti-predictive inputs in the 2019-25 backtest; replaced by the capture ratio
#    (upside/downside) and Jensen's alpha. Downside capture / drawdown remain on display and in the
#    deep-drawdown flag.
#  * rolling metrics on a common sample of window end-dates for every fund (metrics.ROLL_LOOKBACK).
ACTIVE_EQUITY_PROTOCOL = {
    "roll3y_excess_median": ("Long-run excess", 15, True),
    "roll3y_hit_rate":      ("Long-run excess", 10, True),
    "info_ratio_3y":        ("Risk-adjusted", 15, True),
    "capture_ratio_3y":     ("Risk-adjusted", 12, True),
    "alpha_3y":             ("Risk-adjusted", 8, True),
    "roll3y_excess_p10":    ("Consistency", 10, True),
    "roll1y_hit_rate":      ("Consistency", 10, True),
    "ter":                  ("Cost", 10, False),
    "active_share":         ("Portfolio", 4, True),
    "mandate_ok":           ("Portfolio", 3, True),
    "cash_other_pct":       ("Portfolio", 2, False),
    "turnover_1m":          ("Portfolio", 1, False),
}

SMALL_MID_PROTOCOL = dict(ACTIVE_EQUITY_PROTOCOL)
SMALL_MID_PROTOCOL.update({
    "aum_capacity_penalty": ("Portfolio", 2, False),   # capacity: very large small/mid funds struggle to deploy
    "beyond500_pct": ("Portfolio", 2, False),          # liquidity risk
})

THEMATIC_PROTOCOL = dict(ACTIVE_EQUITY_PROTOCOL)

INDEX_PROTOCOL = {
    "tracking_diff_1y":     ("Tracking", 35, True),   # fund minus index return (negative); closer to 0 better
    "tracking_err_1y":      ("Tracking", 30, False),   # index fund AUM dropped: liquidity matters for ETFs, not index funds
    "tracking_diff_3y":     ("Tracking", 15, True),
    "ter":                  ("Cost", 20, False),
}

# Arbitrage funds (hybrid): cash-futures arbitrage, so returns sit close to short-term rates. They are compared
# with each other on return over the arbitrage index (which has no costs, so most funds trail it), consistency,
# cost and size; the absolute guard for A/A+ is beating the median liquid fund (protocols.assign_tiers).
ARBITRAGE_PROTOCOL = {
    "roll1y_excess_median": ("Return", 25, True),    # median rolling 1-year return over the arbitrage index
    "excess_cagr_3y":       ("Return", 15, True),
    "roll1y_hit_rate":      ("Consistency", 10, True),
    "vol_3y":               ("Consistency", 10, False),   # monthly-return volatility, annualised
    "neg_months_3y":        ("Consistency", 5, False),    # share of months with a negative return
    "ter_base":             ("Cost", 25, False),   # the fund's fee; trading taxes are already in the returns above
    "aum_size":             ("Size", 10, True),           # AUM capped at ARB_AUM_CAP: below it, too few trades to spread costs
}
ARB_AUM_CAP = 5000   # Rs crore; above this, size earns no more credit
# Investors pick arbitrage over liquid funds for tax: liquid-fund gains are taxed at the slab rate, arbitrage gains
# as equity. The liquid comparison that decides A/A+ is after tax for a top-slab investor holding over a year:
# 30% + 4% cess on liquid gains; 12.5% LTCG + 4% cess on arbitrage gains (surcharge and the Rs 1.25 lakh
# exemption ignored, both of which only widen the gap). Before-tax figures are shown as well.
TAX_SLAB_TOP = 0.312
TAX_EQUITY_LTCG = 0.13


def protocol_for(category: str):
    if category == "Arbitrage":
        return "Arbitrage protocol", ARBITRAGE_PROTOCOL
    if category == "Index Fund":
        return "Index protocol", INDEX_PROTOCOL
    if category in ("Small Cap", "Mid Cap"):
        return "Small/Mid protocol", SMALL_MID_PROTOCOL
    if category == "Sectoral/Thematic":
        return "Thematic protocol", THEMATIC_PROTOCOL
    return "Active equity protocol", ACTIVE_EQUITY_PROTOCOL

# Red flags -> override tier to "Avoid" / "Watch"
RED_FLAGS = {
    "chronic_underperformer": "3Y rolling hit rate < 25% and median rolling excess < -2%",
    "turnaround_unproven": "Chronic rolling underperformance but positive 3Y excess recently -> capped at B",
    "risk_without_reward": "Downside capture > 110% and 3Y info ratio < 0",
    "deep_drawdown": "5Y max drawdown worse than category 10th percentile by >5pp",
    "mandate_breach": "Portfolio violates SEBI category mandate in two consecutive months (e.g. small cap fund <65% in small caps) -> capped at B",
    "mandate_watch": "Portfolio violates SEBI category mandate in the latest month only (informational, no cap)",
    "closet_indexer": "Active share below threshold (50%; 30% for large caps) AND no 3Y excess return - paying active fees for index returns",
    "trails_liquid_after_tax": "Arbitrage fund: 3Y return after tax below the median liquid fund's after tax, top slab (cannot be rated A or A+)",
}
CLOSET_INDEX_ACTIVE_SHARE = 50          # default threshold
CLOSET_INDEX_BY_CATEGORY = {"Large Cap": 30}   # large caps structurally hug the index (80% in top 100)


# ---------------------------------------------------------------------------
# Period-wise (horizon) rankings: every fund old enough for the window is ranked.
# 3Y+ is the recommended view; 6M/1Y mostly reflect recent momentum / luck.
# ---------------------------------------------------------------------------
HORIZON_LIST = ["6M", "1Y", "3Y", "5Y"]
# Funds carrying these long-term red flags get tier "Avoid" and are NOT given period ranks either,
# so a short-term bounce can't push a chronic underperformer to the top of a 6M/1Y table.
HARD_FLAGS = ("chronic_underperformer", "risk_without_reward")
RECOMMENDED_HORIZON = "3Y"


def horizon_protocol(h: str, category: str) -> dict:
    """Period views (v2). Short windows: risk statistics on <= 26 weekly points are noisy, so excess return
    dominates; Sortino dropped everywhere (0.98 rank-correlated with excess return within a peer group)."""
    if category == "Index Fund":
        return {f"excess_{h}": ("Tracking", 45, True), f"te_{h}": ("Tracking", 35, False), "ter": ("Cost", 20, False)}
    if category == "Arbitrage":
        return {f"excess_{h}": ("Return", 60, True), f"hit_{h}": ("Consistency", 15, True), "ter_base": ("Cost", 25, False)}
    w = {"6M": (50, 0, 10, 10, 20), "1Y": (40, 10, 10, 10, 20), "3Y": (25, 15, 15, 10, 25), "5Y": (25, 15, 15, 10, 25)}[h]
    p = {f"excess_{h}": ("Return", w[0], True), f"ir_{h}": ("Return", w[1], True),
         f"dcap_{h}": ("Risk", w[2], False), f"mdd_{h}": ("Risk", w[3], True),
         f"hit_{h}": ("Consistency", w[4], True), "ter": ("Cost", 10, False)}
    return {k: v for k, v in p.items() if v[1] > 0}
