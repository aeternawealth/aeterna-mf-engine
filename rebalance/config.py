"""Every tunable number of the rebalance tool. The reasons behind them: docs/rebalance_principles.md.

Tax rules change with each Budget. Each rule carries the date it was last checked; report.py warns when one is more
than 12 months old.
"""
from datetime import date

# ------------------------------------------------------------------ tax (Finance (No. 2) Act 2024, rates from 23 Jul 2024)
TAX_CHECKED = date(2026, 11, 12)
TAX = {
    "cess": 0.04,                         # health and education cess on the tax
    "equity": {                           # equity-oriented funds (65%+ Indian equity), incl. arbitrage and ELSS
        "lt_days": 365,                   # held MORE than 12 months = long term
        "stcg": 0.20, "ltcg": 0.125,
        "ltcg_exempt": 125_000,           # per financial year, across all equity gains
        "grandfather_date": date(2018, 1, 31),   # cost = max(cost, min(NAV on this date, sale price)) for units bought on or before it
    },
    "debt": {                             # 65%+ debt: bought on/after 1 Apr 2023 -> slab whatever the holding period
        "slab_from": date(2023, 4, 1),
        "lt_days": 730, "ltcg_old": 0.125,       # units bought before 1 Apr 2023, held > 24 months
    },
    "other": {                            # neither (e.g. 35-65% equity hybrids, gold, international FoFs)
        "lt_days": 730, "ltcg": 0.125,    # held > 24 months; otherwise slab
    },
}

# ------------------------------------------------------------------ exit loads (scheme documents vary: per-scheme overrides in
# rebalance/exit_loads.csv with columns code,pct,days). Defaults lean slightly high so costs are not understated.
EXIT_LOAD_DEFAULT = {"pct": 0.01, "days": 365}
EXIT_LOAD_BY_CATEGORY = {
    "Arbitrage": {"pct": 0.0025, "days": 30},
    "Liquid": {"pct": 0.00007, "days": 7},
    "Overnight": {"pct": 0.0, "days": 0},
    "Index Fund": {"pct": 0.0025, "days": 15},
    "Money Market": {"pct": 0.0, "days": 0},
    "Ultra Short Term": {"pct": 0.0, "days": 0},
    "Ultra Short to Short Term": {"pct": 0.0, "days": 0},
    "Short Term": {"pct": 0.0, "days": 0},
    "Corporate Bond": {"pct": 0.0, "days": 0},
    "Banking & PSU": {"pct": 0.0, "days": 0},
    "Gilt": {"pct": 0.0, "days": 0},
    "Equity Savings": {"pct": 0.01, "days": 90},
}
ELSS_LOCK_DAYS = 3 * 365

# ------------------------------------------------------------------ risk profile
PROFILES = ["conservative", "moderate", "aggressive", "very_aggressive"]
MAX_EQUITY = {"conservative": 0.40, "moderate": 0.65, "aggressive": 0.85, "very_aggressive": 1.00}

# equity sleeve mix by profile (fractions of equity). Buckets are defined below.
EQUITY_MIX = {
    "conservative":    {"large": 0.50, "flexi": 0.40, "midlm": 0.10, "small": 0.00},
    "moderate":        {"large": 0.30, "flexi": 0.40, "midlm": 0.20, "small": 0.10},
    "aggressive":      {"large": 0.15, "flexi": 0.35, "midlm": 0.30, "small": 0.20},
    "very_aggressive": {"large": 0.00, "flexi": 0.35, "midlm": 0.30, "small": 0.35},
}

# glide path: the most equity allowed with this many years left to the goal (linear between points).
# A goal with no date (plain wealth growth) uses the profile's maximum.
GLIDE = [(0, 0.05), (1, 0.10), (3, 0.30), (5, 0.50), (7, 0.70), (10, 1.00)]

# ------------------------------------------------------------------ buckets
BUCKET_OF_CATEGORY = {
    "Large Cap": "large", "Index Fund": "large",
    "Flexi Cap": "flexi", "Multi Cap": "flexi", "Focused": "flexi", "Value / Contra": "flexi", "ELSS": "flexi",
    "Dividend Yield": "flexi",
    "Large & Mid Cap": "midlm", "Mid Cap": "midlm",
    "Small Cap": "small",
    "Sectoral/Thematic": "thematic",
    "Arbitrage": "parked", "Liquid": "parked", "Overnight": "parked", "Money Market": "parked",
    "Ultra Short Term": "parked",
}
EQUITY_BUCKETS = ["large", "flexi", "midlm", "small"]
BUCKET_LABEL = {"large": "Large cap and index", "flexi": "Flexi, multi and focused", "midlm": "Mid and large & mid cap",
                "small": "Small cap", "thematic": "Sectoral and thematic", "hybrid": "Hybrid", "debt": "Debt",
                "parked": "Parked (arbitrage, liquid)", "other": "Other"}
# where new money for each equity bucket may go, in order of preference
BUCKET_CATEGORIES = {
    "large": ["Large Cap"], "flexi": ["Flexi Cap", "Multi Cap", "Focused"],
    "midlm": ["Mid Cap", "Large & Mid Cap"], "small": ["Small Cap"],
}
# the non-equity sleeve: short horizons and high slabs favour arbitrage (taxed as equity), longer ones short-duration debt
NONEQUITY_CATEGORIES = {"short": ["Arbitrage", "Money Market"], "long": ["Short Term", "Corporate Bond", "Banking & PSU"]}
THEMATIC_MAX = 0.10            # of equity

# ------------------------------------------------------------------ rebalancing rules
BAND_ABS = 0.05                # a sleeve is "off" when more than 5 points from target ...
BAND_REL = 0.25                # ... or 25% away in relative terms (whichever is wider)
MAX_EQUITY_FUNDS = 7
MAX_FUNDS_PER_BUCKET = 2
MAX_AMC_SHARE = 0.40           # of equity, before a concentration warning
OVERLAP_HIGH = 0.50            # two funds sharing this much count as one bet
MIN_SIP_PER_FUND = 2_000
SIP_ROUND = 500
SMALL_HOLDING = 0.02           # a holding under 2% of the portfolio barely moves the result
SELL_COST_OK = 0.005           # a sale with no measurable benefit goes ahead only if tax + load < 0.5% of the amount
NEW_MONEY_TIERS = ("A+", "A")
EXIT_TIERS = ("C",)
STP_MONTHS = {"conservative": 12, "moderate": 9, "aggressive": 6, "very_aggressive": 6}
DEPLOY_HORIZON_MONTHS = 12     # new money counted when closing gaps: lump sums + this many months of SIP

# ------------------------------------------------------------------ projection
SIMS = 5_000
BLOCK_MONTHS = 12
INFLATION = {"default": 0.06, "education": 0.10}
PROJ_CATEGORIES = {            # history used for each bucket's monthly returns (category median fund)
    "large": ["large-cap"], "flexi": ["flexi-cap"], "midlm": ["mid-cap", "large-mid-cap"], "small": ["small-cap"],
    "thematic": ["flexi-cap"], "hybrid": ["aggressive-hybrid"], "debt": ["short-term"], "parked": ["arbitrage"],
}
SUCCESS_TARGETS = (0.70, 0.85)
