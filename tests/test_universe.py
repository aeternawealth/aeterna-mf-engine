"""engine.ingest.build_universe: which growth line represents each plan when AMFI lists more than one (Nov 2026)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import ingest  # noqa: E402

D, OLD = pd.Timestamp("2026-11-20"), pd.Timestamp("2024-06-28")


def _row(code, name, plan, option, date=D, cat="Banking & PSU", amc="X Mutual Fund"):
    return {"code": code, "name": name, "plan": plan, "option": option, "nav_date": date, "category": cat,
            "raw_category": "Open Ended Schemes(Debt Scheme - Banking and PSU Fund)", "amc": amc}


def _pick(rows):
    u = ingest.build_universe(pd.DataFrame(rows))
    return {(r.name, r.plan_type): int(r.code) for r in u.itertuples()}


def test_live_line_beats_a_stale_lower_code():
    # Sundaram Banking & PSU: a 'Retail GROWTH' line last priced in 2024 (lower code) beside the live Regular plan
    got = _pick([_row(100781, "S Banking Fund", "", "Retail GROWTH", OLD), _row(100784, "S Banking Fund", "Regular Plan", "GROWTH"),
                 _row(119625, "S Banking Fund", "Direct Plan", "GROWTH")])
    assert got[("S Banking Fund", "Regular")] == 100784 and got[("S Banking Fund", "Direct")] == 119625


def test_current_class_beats_a_live_legacy_class():
    # Nippon India Liquid: 'Retail Plan - Growth Option' (lower code, still priced) beside the current Regular plan
    got = _pick([_row(100837, "N Liquid Fund", "Regular Plan", "Retail Plan - Growth Option", cat="Liquid"),
                 _row(100851, "N Liquid Fund", "Regular Plan", "Growth Option", cat="Liquid")])
    assert got[("N Liquid Fund", "Regular")] == 100851


def test_only_line_is_kept_whatever_its_name():
    # Franklin's Direct plans are labelled 'Retail Plan Growth' / 'Super Institutional Growth' and are the only lines
    got = _pick([_row(101357, "F Money Market Fund", "Regular Plan", "Growth", cat="Money Market"),
                 _row(118506, "F Money Market Fund", "Direct Plan", "Retail Plan Growth", cat="Money Market")])
    assert got[("F Money Market Fund", "Direct")] == 118506 and got[("F Money Market Fund", "Regular")] == 101357


def test_index_peer_groups_ignore_the_fund_house():
    import pandas as pd
    from engine.rank import assign_peers
    names = [("Kotak BSE Sensex Index Fund", "Kotak Mahindra Mutual Fund"), ("LIC MF BSE Sensex Index Fund", "LIC Mutual Fund"),
             ("Nippon India Index Fund - BSE Sensex Plan", "Nippon India Mutual Fund"), ("Invesco India BSE Sensex Index Fund", "Invesco Mutual Fund"),
             ("UTI BSE Sensex Index Fund", "UTI Mutual Fund"), ("SBI NIFTY INDEX FUND", "SBI Mutual Fund"), ("HDFC Nifty 50 Index Fund", "HDFC Mutual Fund"),
             ("Axis Nifty50 Equal Weight Index Fund", "Axis Mutual Fund"), ("Kotak Nifty 50 Equal Weight Index Fund", "Kotak Mahindra Mutual Fund")]
    u = pd.DataFrame([{"name": n, "amc": a, "category": "Index Fund", "plan_type": "Regular"} for n, a in names])
    tri = pd.DataFrame(columns=["NIFTY 50", "NIFTY50 EQUAL WEIGHT"])
    g = dict(zip(u.name, assign_peers(u, tri).peer_group))
    assert {g[n] for n, _ in names[:5]} == {"Index: BSE SENSEX"}
    assert g["SBI NIFTY INDEX FUND"] == g["HDFC Nifty 50 Index Fund"] == "Index: NIFTY 50"
    assert g["Axis Nifty50 Equal Weight Index Fund"] == g["Kotak Nifty 50 Equal Weight Index Fund"]
