"""A carried-forward portfolio must keep its own month (Nov 2026 bug: a re-run relabelled September copies as
October, and the two-month mandate rule counted one portfolio twice)."""
import pandas as pd

from engine import holdings as H


def _row(pk, mid, ok, month=None):
    r = {"pair_key": pk, "n_stocks": 50, "top10_pct": 40.0, "large_pct": 5.0, "mid_pct": mid, "small_pct": 20.0,
         "equity_pct": 85.0, "mandate_ok": ok, "mandate_breaches": "" if ok else f"mid {mid:.0f} (needs >=65)", "unclassified_pct": 0.0}
    if month:
        r["holdings_month"] = month
    return r


def test_rerun_keeps_carried_month_and_rule_counts_once(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "HOLD_DIR", tmp_path)
    sep = pd.DataFrame([_row("amc|a", 59.0, 0, "2026-09"), _row("amc|b", 70.0, 1, "2026-09")])
    H.save_cached(sep, "2026-09")
    # first October run: only fund b is published; a is carried forward from September
    oct1, m = H.with_fallback(pd.DataFrame([_row("amc|b", 71.0, 1)]), "2026-10", log=lambda *a: None)
    H.save_cached(oct1, m)
    assert dict(zip(oct1.pair_key, oct1.holdings_month)) == {"amc|b": "2026-10", "amc|a": "2026-09"}
    # a re-run that downloads nothing new must not relabel the carried portfolio as October
    again, _ = H.with_fallback(pd.DataFrame(), "2026-10", log=lambda *a: None, same_month=H.load_cached("2026-10"))
    assert dict(zip(again.pair_key, again.holdings_month))["amc|a"] == "2026-09"
    out = H.add_prev_mandate(again, "2026-10")
    a = out[out.pair_key == "amc|a"].iloc[0]
    assert pd.isna(a["mandate_ok_prev"])          # one month of data: a watch, not a two-month breach


def test_relabel_copies_heals_old_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(H, "HOLD_DIR", tmp_path)
    H.save_cached(pd.DataFrame([_row("amc|a", 59.0, 0, "2026-09")]), "2026-09")
    wrong = pd.DataFrame([_row("amc|a", 59.0, 0, "2026-10"), _row("amc|c", 66.0, 1, "2026-10")])
    fixed = H.relabel_copies(wrong, "2026-10")
    assert dict(zip(fixed.pair_key, fixed.holdings_month)) == {"amc|a": "2026-09", "amc|c": "2026-10"}
    assert pd.isna(H.add_prev_mandate(fixed, "2026-10").set_index("pair_key").loc["amc|a", "mandate_ok_prev"])
