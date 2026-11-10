"""Aeterna MF Engine - configuration: categories, benchmarks, protocols, weights.

Every number the engine produces is computed deterministically in Python from
public data. The weights below are the "house view" and are meant to be
reviewed against the walk-forward backtest (backtest.py) each quarter.
"""
import os
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
HYBRID_RULES = [("arbitrage", "Arbitrage"), ("aggressive hybrid", "Aggressive Hybrid"), ("balanced advantage", "Balanced Advantage"),
                ("dynamic asset allocation", "Balanced Advantage"), ("equity savings", "Equity Savings"), ("multi asset", "Multi Asset Allocation"),
                ("conservative hybrid", "Conservative Hybrid"), ("balanced hybrid", "Balanced Hybrid")]
# composite benchmark for each hybrid category: equity leg (Nifty 50 TRI) and its weight; the rest is the median
# bond fund ('bond') or the median liquid fund ('liquid'), per plan type. SEBI's own tier-1 hybrid benchmarks are
# CRISIL indices we cannot use; these composites follow their equity shares.
HYBRID_COMPOSITE = {
    "Aggressive Hybrid": (.65, "bond"), "Balanced Advantage": (.50, "bond"), "Equity Savings": (.35, "liquid"),
    "Multi Asset Allocation": (.60, "bond"), "Balanced Hybrid": (.50, "bond"), "Conservative Hybrid": (.20, "bond"),
}
HYBRID_EQUITY_INDEX = "NIFTY 50"
BOND_CATEGORY_KEYS = ["corporate bond", "banking and psu"]   # AMFI raw categories averaged into the bond-fund yardstick
# Debt funds. SEBI re-categorised debt schemes in 2026 and AMCs are renaming in stages, so AMFI lists both
# "Debt Scheme - Short Duration Fund" and "Income/Debt Oriented Schemes - Short Term Fund". Both map to the new
# names. Order matters: first match wins (e.g. 'ultra short to short term' before 'ultra short').
DEBT_RULES = [("overnight", "Overnight"), ("liquid", "Liquid"), ("money market", "Money Market"),
              ("ultra short to short term", "Ultra Short to Short Term"), ("low duration", "Ultra Short to Short Term"),
              ("ultra short", "Ultra Short Term"),
              ("medium to long", "Medium to Long Term"), ("medium", "Medium Term"),
              ("short", "Short Term"), ("long", "Long Term"),
              ("dynamic", "Dynamic Term"), ("corporate bond", "Corporate Bond"), ("credit risk", "Credit Risk"),
              ("banking and psu", "Banking & PSU"), ("10-year constant maturity", "Gilt 10-Year Constant Maturity"),
              ("10 year", "Gilt 10-Year Constant Maturity"), ("gilt", "Gilt"), ("floating", "Floating Rate"), ("floater", "Floating Rate"),
              ("sectoral", "Debt Sectoral")]
DEBT_CATEGORIES = ["Overnight", "Liquid", "Money Market", "Ultra Short Term", "Ultra Short to Short Term", "Short Term",
                   "Medium Term", "Medium to Long Term", "Long Term", "Dynamic Term", "Corporate Bond", "Credit Risk",
                   "Banking & PSU", "Gilt", "Gilt 10-Year Constant Maturity", "Floating Rate", "Debt Sectoral"]
# money that must not move: compared on steadiness, cost and size; a one-year record is enough to be rated
DEBT_CASH_LIKE = {"Overnight", "Liquid", "Money Market", "Ultra Short Term", "Ultra Short to Short Term"}
DEBT_MIN_HISTORY_YEARS = {"Overnight": 1.0, "Liquid": 1.0, "Money Market": 1.0}
# a single day's fall this far below the category median that day is not interest rates: it is a default or
# downgrade in the portfolio (credit event)
CREDIT_EVENT_DAY = {"cash": -0.004, "duration": -0.008, "long": -0.012}
DEBT_SOVEREIGN = {"Gilt", "Gilt 10-Year Constant Maturity"}
DEBT_LONG = {"Long Term", "Medium to Long Term", "Dynamic Term", "Gilt", "Gilt 10-Year Constant Maturity"}

# how gains are taxed (equity-oriented: 65%+ in Indian shares; 'debt': more than 65% in debt; 'other': in between)
TAX_CLASS = {"Arbitrage": "equity", "Aggressive Hybrid": "equity", "Balanced Advantage": "equity", "Equity Savings": "equity",
             "Multi Asset Allocation": "other", "Balanced Hybrid": "other", "Conservative Hybrid": "debt"}
TAX_CLASS.update({c: "debt" for c in DEBT_CATEGORIES})   # debt funds: gains taxed at the slab rate, however long held
# Three master categories for the site: every category maps to one
ASSET_CLASS = {c: "Hybrid" for c in ["Arbitrage", "Aggressive Hybrid", "Balanced Advantage", "Equity Savings",
                                     "Multi Asset Allocation", "Balanced Hybrid", "Conservative Hybrid"]}   # everything else (equity categories, equity index funds) -> "Equity"
ASSET_CLASS.update({c: "Debt" for c in DEBT_CATEGORIES})
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

V3_ACTIVE_EQUITY_PROTOCOL = dict(ACTIVE_EQUITY_PROTOCOL)   # kept for reference and the backtest

# v4 (Nov 2026, audit/research_monthly.py): the inputs that predicted the next 1 month to 3 years over the benchmark in
# both 2012-18 and 2019-26 (walk-forward, monthly, closed funds included). Long-run quality measures (information
# ratio, alpha, Sharpe, Sortino, capture ratio, hit rates) predicted in 2012-18 and then flipped, so they are shown on
# fund pages but carry no weight. A+ in 2019-26: 56% beat the benchmark next year (all funds 48%; v3 45%).
LEAN_EQUITY_PROTOCOL = {
    "mom_1m":            ("Momentum", 12.5, True),     # fund minus benchmark TRI return, last month
    "mom_3m":            ("Momentum", 12.5, True),
    "mom_6m":            ("Momentum", 12.5, True),
    "mom_12m":           ("Momentum", 12.5, True),
    "style_small":       ("Size tilt", 15, True),      # weekly slope on Nifty Smallcap 250 over the benchmark, 3Y
    "style_mid":         ("Size tilt", 15, True),      # weekly slope on Nifty Midcap 150 over the benchmark, 3Y
    "upside_capture_3y": ("Upside capture", 20, True),
}
# Which equity model rates the funds. "v3" is the live model; "v4" is the candidate, run on the staging branch only
# (the data workflows set AETERNA_EQUITY_MODEL from the branch) until it is approved for the live site.
EQUITY_MODEL = os.environ.get("AETERNA_EQUITY_MODEL", "v3")
ACTIVE_EQUITY_PROTOCOL = LEAN_EQUITY_PROTOCOL if EQUITY_MODEL == "v4" else V3_ACTIVE_EQUITY_PROTOCOL

SMALL_MID_PROTOCOL = dict(ACTIVE_EQUITY_PROTOCOL)
if EQUITY_MODEL != "v4":   # v4: the capacity and liquidity inputs were not in the walk-forward test, so they carry no weight there
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


# Hybrid funds (other than arbitrage) exist to soften falls: they are compared with peers on return over their
# composite, consistency, how much of the market's falls they took, their worst fall, and the fund fee.
HYBRID_PROTOCOL = {
    "roll3y_excess_median": ("Return", 15, True),
    "roll3y_hit_rate":      ("Return", 10, True),
    "info_ratio_3y":        ("Return", 10, True),
    "downside_capture_3y":  ("Protection", 15, False),
    "max_drawdown_3y":      ("Protection", 10, True),     # negative: closer to 0 is better
    "capture_ratio_3y":     ("Protection", 10, True),
    "roll1y_hit_rate":      ("Consistency", 10, True),
    "ter_base":             ("Cost", 10, False),          # fee; hedging trades' taxes are already in the returns
}


# Debt funds have no free total-return index (SEBI's tier-1 debt benchmarks are CRISIL's), so each fund is
# measured against the median fund of its own category and plan type, day by day. What separates debt funds is
# steadiness, credit discipline and cost: a debt fund's job is to be boring.
DEBT_CASH_PROTOCOL = {
    "roll1y_excess_median": ("Return", 20, True),      # median rolling 1-year return over the category median
    "excess_cagr_3y":       ("Return", 10, True),
    "roll1y_hit_rate":      ("Consistency", 15, True),
    "vol_3y":               ("Consistency", 10, False),
    "worst_day_3y":         ("Credit", 10, True),        # worst single day: negative; closer to 0 is better
    "ter":                  ("Cost", 25, False),
    "aum_size":             ("Size", 10, True),          # capped: liquidity for redemptions, not size for its own sake
}
DEBT_DURATION_PROTOCOL = {
    "roll1y_excess_median": ("Return", 15, True),
    "excess_cagr_3y":       ("Return", 15, True),
    "roll1y_hit_rate":      ("Consistency", 15, True),
    "vol_3y":               ("Consistency", 10, False),
    "max_drawdown_3y":      ("Credit", 10, True),
    "worst_day_3y":         ("Credit", 15, True),
    "ter":                  ("Cost", 20, False),
}
DEBT_CREDIT_PROTOCOL = dict(DEBT_DURATION_PROTOCOL, max_drawdown_3y=("Credit", 15, True), worst_day_3y=("Credit", 20, True),
                            excess_cagr_3y=("Return", 10, True))


def protocol_for(category: str):
    if category in DEBT_CASH_LIKE:
        return "Debt protocol: cash-like", DEBT_CASH_PROTOCOL
    if category == "Credit Risk":
        return "Debt protocol: credit risk", DEBT_CREDIT_PROTOCOL
    if category in DEBT_CATEGORIES:
        return "Debt protocol: duration", DEBT_DURATION_PROTOCOL
    if category in HYBRID_COMPOSITE:
        return "Hybrid protocol", HYBRID_PROTOCOL
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
    "credit_event": "Debt fund: a single day in the last 5 years on which it fell far more than its category median, too much to be interest rates (holdings marked down, e.g. after a downgrade; not by itself evidence of a default) -> capped at B",
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
    if category in DEBT_CATEGORIES:
        return {f"excess_{h}": ("Return", 55, True), f"hit_{h}": ("Consistency", 20, True), "ter": ("Cost", 25, False)}
    w = {"6M": (50, 0, 10, 10, 20), "1Y": (40, 10, 10, 10, 20), "3Y": (25, 15, 15, 10, 25), "5Y": (25, 15, 15, 10, 25)}[h]
    p = {f"excess_{h}": ("Return", w[0], True), f"ir_{h}": ("Return", w[1], True),
         f"dcap_{h}": ("Risk", w[2], False), f"mdd_{h}": ("Risk", w[3], True),
         f"hit_{h}": ("Consistency", w[4], True), "ter": ("Cost", 10, False)}
    return {k: v for k, v in p.items() if v[1] > 0}
