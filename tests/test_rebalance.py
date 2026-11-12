"""Tests for the rebalance tool: tax lots, exemption, grandfathering, exit loads, lock-ins, glide path, profiles,
overlap, and three synthetic clients. Run: python -m pytest tests/test_rebalance.py -q"""
from datetime import date, timedelta

import pytest

from rebalance import config as C, data as D, plan as P, tax as T
from rebalance.cas import Holding, Portfolio

TODAY = date(2026, 11, 12)


# ------------------------------------------------------------------ tax lots
def test_fifo_consumes_oldest_first():
    lots = T.lots_fifo([
        {"date": date(2024, 1, 1), "units": 10, "amount": 1000},
        {"date": date(2024, 6, 1), "units": 10, "amount": 1200},
        {"date": date(2025, 1, 1), "units": -15, "amount": -1800},
    ])
    assert len(lots) == 1 and lots[0].date == date(2024, 6, 1)
    assert lots[0].units == pytest.approx(5) and lots[0].cost == pytest.approx(120)


def test_short_and_long_term_split():
    lots = [T.Lot(TODAY - timedelta(days=500), 10, 100), T.Lot(TODAY - timedelta(days=100), 10, 100)]
    sc = T.sell(lots, 20, TODAY, 150, cls="equity", category="Flexi Cap")
    assert sc.lt_gain == pytest.approx(500) and sc.st_gain == pytest.approx(500)
    assert sc.load == pytest.approx(10 * 150 * 0.01)        # only the young lot pays the 1% exit load


def test_grandfathering():
    lot = [T.Lot(date(2017, 6, 1), 10, 50)]
    # cost becomes the 31 Jan 2018 NAV (80) when the sale price is above it
    assert T.sell(lot, 10, TODAY, 100, grandfather_nav=80).lt_gain == pytest.approx(200)
    # ... and the sale price when that is lower: no gain, no loss
    assert T.sell(lot, 10, TODAY, 70, grandfather_nav=80).lt_gain == pytest.approx(0)
    # units bought after 31 Jan 2018 are not grandfathered
    assert T.sell([T.Lot(date(2018, 3, 1), 10, 50)], 10, TODAY, 100, grandfather_nav=80).lt_gain == pytest.approx(500)


def test_ltcg_exemption_and_cess():
    sc = T.SaleCost(lt_gain=200_000)
    t = T.tax_due(sc, "equity", 0.3, exempt_left=125_000)
    assert t["exempt_used"] == pytest.approx(125_000)
    assert t["tax"] == pytest.approx(75_000 * 0.125 * 1.04)
    # the next sale in the same financial year has no exemption left
    assert T.tax_due(T.SaleCost(lt_gain=50_000), "equity", 0.3, exempt_left=0)["tax"] == pytest.approx(50_000 * 0.125 * 1.04)


def test_short_term_loss_offsets_long_term_gain():
    t = T.tax_due(T.SaleCost(st_gain=-30_000, lt_gain=200_000), "equity", 0.3, exempt_left=125_000)
    assert t["tax"] == pytest.approx((170_000 - 125_000) * 0.125 * 1.04)


def test_financial_year_boundary():
    assert T.fy_start(date(2027, 3, 31)) == date(2026, 4, 1)
    assert T.fy_start(date(2027, 4, 1)) == date(2027, 4, 1)


def test_exit_load_windows():
    young = [T.Lot(TODAY - timedelta(days=20), 10, 10)]
    assert T.sell(young, 10, TODAY, 10, category="Arbitrage").load == pytest.approx(100 * 0.0025)
    assert T.sell([T.Lot(TODAY - timedelta(days=40), 10, 10)], 10, TODAY, 10, category="Arbitrage").load == 0
    assert T.sell([T.Lot(TODAY - timedelta(days=400), 10, 10)], 10, TODAY, 10, category="Mid Cap").load == 0


def test_elss_lock_in():
    sc = T.sell([T.Lot(TODAY - timedelta(days=700), 10, 10)], 10, TODAY, 12, category="ELSS")
    assert sc.locked_units == pytest.approx(10)
    assert T.sell([T.Lot(TODAY - timedelta(days=1200), 10, 10)], 10, TODAY, 12, category="ELSS").locked_units == 0


def test_new_debt_is_slab_whatever_the_holding():
    sc = T.sell([T.Lot(date(2023, 6, 1), 10, 10)], 10, TODAY, 13, cls="debt", category="Short Term")
    assert sc.st_gain == pytest.approx(30) and sc.lt_gain == 0
    assert T.tax_due(sc, "debt", 0.3, 125_000)["tax"] == pytest.approx(30 * 0.3 * 1.04)


def test_unknown_dates_bracket_the_cost():
    sc = T.sell([T.Lot(None, 10, 100)], 10, TODAY, 150, category="Mid Cap")
    assert sc.unknown_gain == pytest.approx(500) and sc.load_undated == pytest.approx(15)
    hi = T.tax_due(sc, "equity", 0.3, 125_000, unknown_as="ST")["tax"]
    lo = T.tax_due(sc, "equity", 0.3, 125_000, unknown_as="LT")["tax"]
    assert hi == pytest.approx(500 * 0.2 * 1.04) and lo == 0


def test_cheaper_on_is_the_long_term_date():
    d = TODAY - timedelta(days=300)
    assert T.cheaper_on([T.Lot(d, 10, 100)], TODAY, 150) == d + timedelta(days=366)
    assert T.cheaper_on([T.Lot(d, 10, 200)], TODAY, 150) is None      # a lot at a loss has no reason to wait


# ------------------------------------------------------------------ profile and glide
def test_capacity_caps_attitude():
    assert P.Client(risk_attitude="very_aggressive", risk_capacity="moderate").profile == "moderate"
    assert P.Client(risk_attitude="conservative", risk_capacity="very_aggressive").profile == "conservative"


def test_glide_path():
    assert P.glide(None, "aggressive") == C.MAX_EQUITY["aggressive"]
    assert P.glide(3, "very_aggressive") == pytest.approx(0.30)
    assert P.glide(4, "very_aggressive") == pytest.approx(0.40)
    assert P.glide(20, "moderate") == C.MAX_EQUITY["moderate"]
    assert P.glide(2, "moderate") < P.glide(6, "moderate")


def test_overlap_is_a_share():
    w = D.weights()
    if len(w) < 2:
        pytest.skip("no portfolio data")
    a, b = list(w)[:2]
    o = D.overlap(a, b)
    assert 0 <= o <= 1 and o == pytest.approx(D.overlap(b, a))
    assert D.overlap(a, a) == pytest.approx(min(1.0, w[a].sum()), rel=1e-6)


# ------------------------------------------------------------------ synthetic clients
def _holding(row, value, days_old=800):
    nav = float(row["nav_latest"])
    units = value / nav
    return Holding(name=row["name"], plan=row["plan_type"], units=units, nav=nav, value=value, invested=value * 0.8,
                   lots=[T.Lot(TODAY - timedelta(days=days_old), units, nav * 0.8)], code=int(row["code"]), fund=row,
                   exact_lots=True, source="test")


def _pick(category, tier, plan="Regular", n=0):
    f = D.funds()
    rows = f[(f.category == category) & (f.tier == tier) & (f.plan_type == plan) & f.nav_latest.notna()].sort_values("score", ascending=False)
    if len(rows) <= n:
        pytest.skip(f"no {tier} {category} fund in the data")
    return rows.iloc[n]


def _port(hs):
    return Portfolio("Test", "", TODAY, hs, "test")


def test_conservative_retiree_three_years_out():
    hs = [_holding(_pick("Small Cap", "A+"), 2_000_000), _holding(_pick("Flexi Cap", "A+"), 2_000_000)]
    c = P.Client(goal="retirement", target_today=5_000_000, target_year=2029, sip=20_000, risk_attitude="moderate",
                 risk_capacity="conservative", slab=0.3)
    p = P.build(_port(hs), c)
    assert p.profile == "conservative"
    assert p.target.get("small", 0) == 0
    assert sum(v for k, v in p.target.items() if k in C.EQUITY_BUCKETS) == pytest.approx(0.30)
    assert all(b not in ("small",) for f, a, b in p.sip)                    # no new money into small caps
    assert any(t["bucket"] in ("parked", "debt") for t in p.theses)          # the shift to safety is explained


def test_aggressive_thirty_year_old():
    hs = [_holding(_pick("Mid Cap", "A+"), 300_000), _holding(_pick("Large & Mid Cap", "A+"), 300_000)]
    c = P.Client(goal="growth", sip=50_000, risk_attitude="aggressive", risk_capacity="aggressive", slab=0.3)
    p = P.build(_port(hs), c)
    assert sum(a for f, a, b in p.sip) == pytest.approx(50_000)
    assert all(a >= C.MIN_SIP_PER_FUND and a % C.SIP_ROUND == 0 for f, a, b in p.sip)
    assert all(f["tier"] in C.NEW_MONEY_TIERS for f, a, b in p.sip)
    assert len({f["amc"] for f, a, b in p.sip}) == len(p.sip)              # one fund house per new-money fund
    assert not any(v.action == "exit" for v in p.verdicts)                   # nothing sound gets sold


def test_messy_sixteen_fund_portfolio():
    spec = [("Small Cap", "A+", 0), ("Small Cap", "C", 0), ("Small Cap", "C", 1), ("Mid Cap", "A+", 0), ("Mid Cap", "C", 0),
            ("Mid Cap", "B", 0), ("Flexi Cap", "C", 0), ("Flexi Cap", "B", 0), ("Flexi Cap", "A", 0), ("Large & Mid Cap", "C", 0),
            ("Large & Mid Cap", "A+", 0), ("Multi Cap", "B", 0), ("Large Cap", "B", 0), ("Large Cap", "C", 0),
            ("Arbitrage", "A", 0), ("Arbitrage", "A", 1)]
    hs = []
    for cat, tier, n in spec:
        hs.append(_holding(_pick(cat, tier, n=n), 1_000_000 if cat == "Arbitrage" else 200_000, days_old=200 if tier == "C" else 900))
    c = P.Client(goal="growth", sip=50_000, risk_attitude="very_aggressive", risk_capacity="very_aggressive", slab=0.3)
    p = P.build(_port(hs), c)
    v = {x.h.code: x for x in p.verdicts}
    for h, (cat, tier, n) in zip(hs, spec):
        if tier == "C":
            assert v[h.code].action == "exit", h.name
        if tier in ("A+", "A") and cat != "Arbitrage":
            assert v[h.code].action in ("add", "hold"), h.name
    # a C fund bought 200 days ago has a short-term gain and a 1% exit load: it waits until that is cheaper
    for x in p.verdicts:
        if x.action == "exit" and x.when.startswith("now") and not any(code == "R4" for code, _ in x.reasons):
            assert x.cost_high <= C.SELL_COST_OK * x.sell_value, x.h.name
        if x.action == "exit" and x.h.lots[0].date and (TODAY - x.h.lots[0].date).days < 365:
            assert not x.when.startswith("now"), (x.h.name, x.when)
    funds_after = {x.h.code for x in p.verdicts if x.action in ("add", "hold", "stop")} | {int(f["code"]) for f, a, b in p.sip}
    assert len(funds_after) <= 10
    assert sum(a for f, a, b in p.deploy) > 1_500_000                          # the parked money is put to work


def test_old_units_sold_now_young_units_later():
    row = _pick("Mid Cap", "C")
    nav = float(row["nav_latest"])
    old = T.Lot(TODAY - timedelta(days=900), 1000 / nav * 100, nav * 0.7)
    young = T.Lot(TODAY - timedelta(days=90), 1000 / nav * 100, nav * 0.9)
    h = Holding(name=row["name"], plan=row["plan_type"], units=old.units + young.units, nav=nav, value=(old.units + young.units) * nav,
                invested=0, lots=[old, young], code=int(row["code"]), fund=row, exact_lots=True)
    p = P.build(_port([h, _holding(_pick("Flexi Cap", "A+"), 2_000_000)]),
                P.Client(sip=20_000, risk_attitude="aggressive", risk_capacity="aggressive"))
    v = next(x for x in p.verdicts if x.h.code == h.code)
    assert v.action == "exit" and v.when.startswith("now for")
    assert v.sell_now == pytest.approx(old.units * nav)
    assert (young.date + timedelta(days=366)).strftime("%d %b %Y") in v.when
