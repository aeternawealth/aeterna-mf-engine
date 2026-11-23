"""AMFI's NAVAll sometimes leaves a line's plan and option blank, or mislabels them. Nov 2026: Motilal Oswal Midcap,
HSBC Small Cap, Tata Nifty 50 Index and 17 more schemes were missing from the site; Kotak Active Momentum's Regular
growth and IDCW labels were swapped. The scheme master's line names fill the gaps without disturbing labelled schemes."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine import ingest  # noqa: E402

HEAD = "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
CAT_MID = "Open Ended Schemes(Equity Scheme - Mid Cap Fund)\n"
CAT_LARGE = "Open Ended Schemes(Equity Scheme - Large Cap Fund)\n"
NAVALL = (HEAD + CAT_MID + "Motilal Oswal Mutual Fund\n"
          "127044;INF1;INF2;Motilal Oswal Midcap Fund;;;48.5;20-Nov-2026\n"
          "127042;INF3;-;Motilal Oswal Midcap Fund;;;120.5;20-Nov-2026\n"
          "127040;INF4;INF5;Motilal Oswal Midcap Fund;;;47.0;20-Nov-2026\n"
          "127039;INF6;-;Motilal Oswal Midcap Fund;;;104.1;20-Nov-2026\n"
          + CAT_LARGE + "Edelweiss Mutual Fund\n"
          "200001;INF7;-;Edelweiss Large Cap Fund;Regular Plan;Growth;80.0;20-Nov-2026\n"
          "200002;INF8;-;Edelweiss Large Cap Fund;Direct Plan;Growth;95.0;20-Nov-2026\n"
          "111935;INF9;-;Edelweiss Large Cap Fund;;;79.0;20-Nov-2026\n"
          "Kotak Mahindra Mutual Fund\n"
          "153753;INFa;-;Kotak Active Momentum Fund;Direct Plan;Growth Option;10.5;20-Nov-2026\n"
          "153755;INFb;-;Kotak Active Momentum Fund;Regular Plan;Payout of IDCW option- Direct;10.4;20-Nov-2026\n"
          "153756;INFc;-;Kotak Active Momentum Fund;Regular Plan;Growth;10.4;20-Nov-2026\n"
          "Old Mutual Fund\n"
          "300001;INFd;-;Closed Large Cap Fund;;;12.0;24-Apr-2020\n")
MASTER = ("AMC,Code,Scheme Name,Scheme Type,Scheme Category,Scheme NAV Name,Min,Launch,Closure,ISIN\n"
          "M,127044,Motilal Oswal Midcap Fund,Open Ended,Mid Cap,Motilal Oswal Midcap Fund-Direct - IDCW Payout/Reinvestment,500,,,x\n"
          "M,127042,Motilal Oswal Midcap Fund,Open Ended,Mid Cap,Motilal Oswal Midcap Fund-Direct Plan-Growth Option,500,,,x\n"
          "M,127040,Motilal Oswal Midcap Fund,Open Ended,Mid Cap,Motilal Oswal Midcap Fund-Regular - IDCW Payout/Reinvestment,500,,,x\n"
          "M,127039,Motilal Oswal Midcap Fund,Open Ended,Mid Cap,Motilal Oswal Midcap Fund-Regular Plan-Growth Option,500,,,x\n"
          "E,111935,Edelweiss Large Cap Fund,Open Ended,Large Cap,Edelweiss Large Cap Fund -Plan B - Growth option,500,,,x\n"
          "K,153755,Kotak Active Momentum Fund,Open Ended,Thematic,Kotak Active Momentum Fund - Regular Plan - Growth,500,,,x\n"
          "K,153756,Kotak Active Momentum Fund,Open Ended,Thematic,Kotak Active Momentum Fund - Regular Plan - IDCW - Payout & Reinvestment,500,,,x\n"
          "O,300001,Closed Large Cap Fund,Open Ended,Large Cap,Closed Large Cap Fund - Regular Plan - Growth,500,,,x\n")


def _universe():
    return ingest.build_universe(ingest.fill_plan_option(ingest.parse_navall(NAVALL), MASTER))


def test_unlabelled_scheme_is_added_with_both_plans():
    u = _universe()
    m = u[u["name"] == "Motilal Oswal Midcap Fund"].set_index("plan_type")["code"].to_dict()
    assert m == {"Direct": 127042, "Regular": 127039}


def test_legacy_line_does_not_replace_current_plan():
    u = _universe()
    e = u[u["name"] == "Edelweiss Large Cap Fund"].set_index("plan_type")["code"].to_dict()
    assert e == {"Regular": 200001, "Direct": 200002}       # not 111935 (Plan B)


def test_mislabelled_growth_line_is_corrected():
    u = _universe()
    k = u[u["name"] == "Kotak Active Momentum Fund"].set_index("plan_type")["code"].to_dict()
    assert k.get("Regular") == 153755


def test_closed_scheme_stays_out():
    assert "Closed Large Cap Fund" not in set(_universe()["name"])


def test_no_master_changes_nothing():
    d = ingest.parse_navall(NAVALL)
    assert ingest.fill_plan_option(d, "").equals(d)
