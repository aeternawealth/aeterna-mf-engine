"""Portfolio files that title their sheet with a code (HSBC: 'HEMIDF') are matched by the file name instead."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import holdings as H  # noqa: E402

UNI = pd.DataFrame([
    {"pair_key": "hsbc mutual fund|hsbc small cap fund", "name": "HSBC Small Cap Fund", "amc": "HSBC Mutual Fund"},
    {"pair_key": "hsbc mutual fund|hsbc midcap fund", "name": "HSBC Midcap Fund", "amc": "HSBC Mutual Fund"},
    {"pair_key": "hsbc mutual fund|hsbc large cap fund", "name": "HSBC Large Cap Fund", "amc": "HSBC Mutual Fund"},
    {"pair_key": "hsbc mutual fund|hsbc aggressive hybrid fund", "name": "HSBC Aggressive Hybrid Fund", "amc": "HSBC Mutual Fund"},
])
DF = pd.DataFrame({"isin": ["INE040A01034"], "weight": [5.0]})


def test_title_from_file():
    assert H._title_from_file("hsbc-small-cap-fund-31-oct-2026.xlsx") == "hsbc small cap fund"
    assert H._title_from_file("MP-Unifi-Flexi-Cap-Fund-31102026.xlsx") == "Unifi Flexi Cap Fund"
    assert H._title_from_file("Monthly_Portfolio_October_2026.xlsx") == ""


def test_code_titled_sheets_match_by_file_name():
    parsed = [(["HEMIDF"], DF, "hsbc-small-cap-fund-31-oct-2026.xlsx", "HSBC-Mutual-Fund"),
              (["HEMCPF"], DF, "hsbc-midcap-fund-31-oct-2026.xlsx", "HSBC-Mutual-Fund"),
              (["HEEQTF"], DF, "hsbc-large-cap-fund-31-oct-2026.xlsx", "HSBC-Mutual-Fund")]
    m = H.map_to_schemes(parsed, UNI).set_index("file")["pair_key"]
    assert m["hsbc-small-cap-fund-31-oct-2026.xlsx"] == "hsbc mutual fund|hsbc small cap fund"
    assert m["hsbc-midcap-fund-31-oct-2026.xlsx"] == "hsbc mutual fund|hsbc midcap fund"
    assert m["hsbc-large-cap-fund-31-oct-2026.xlsx"] == "hsbc mutual fund|hsbc large cap fund"


def test_combined_file_name_is_not_used():
    # two portfolios in one file: the file name says nothing about either sheet, so codes stay unmatched
    parsed = [(["HEMIDF"], DF, "hsbc-small-cap-fund-31-oct-2026.xlsx", "HSBC-Mutual-Fund"),
              (["HEMCPF"], DF, "hsbc-small-cap-fund-31-oct-2026.xlsx", "HSBC-Mutual-Fund")]
    assert H.map_to_schemes(parsed, UNI)["pair_key"].isna().all()
