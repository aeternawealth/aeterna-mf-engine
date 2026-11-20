"""Debt NAV face-value changes (e.g. UTI Liquid, Rs 4,700 to Rs 470 units in June 2026) must not show as returns:
not in the period returns and ranks (engine), not in the charts (site series). Nov 2026."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "site"))

from engine.metrics import debt_clean, horizon_metrics  # noqa: E402
import build_series as BS  # noqa: E402


def _liquid(split_day="2026-06-15"):
    idx = pd.bdate_range("2021-01-01", "2026-11-19")
    nav = pd.Series(1000 * (1 + 0.065 / 252) ** np.arange(len(idx)), index=idx)
    nav[nav.index >= split_day] /= 10            # units re-denominated: one tenth the NAV, ten times the units
    bench = pd.Series(1000 * (1 + 0.065 / 252) ** np.arange(len(idx)), index=idx)
    return nav, bench


def test_period_returns_ignore_face_value_change():
    nav, bench = _liquid()
    as_of = nav.index[-1]
    raw = horizon_metrics(nav, bench, as_of)
    clean = horizon_metrics(debt_clean(nav), bench, as_of)
    assert raw["ret_1Y"] < -0.8                  # the bug: about -89%
    assert abs(clean["ret_1Y"] - 0.065) < 0.01   # the fix: about 6.5%
    assert abs(clean["ret_3Y"] - 0.065) < 0.01


def test_chart_series_restated_in_todays_units():
    nav, _ = _liquid()
    c = BS.face_value_clean(nav)
    assert c.iloc[-1] == nav.iloc[-1]            # ends at the real current NAV
    assert c.pct_change().min() > -0.01          # no crash in the history
    assert abs(c.iloc[-1] / c[c.index <= "2025-11-19"].iloc[-1] - 1.065) < 0.01


def test_clean_series_untouched():
    _, bench = _liquid()
    pd.testing.assert_series_equal(BS.face_value_clean(bench), bench)
