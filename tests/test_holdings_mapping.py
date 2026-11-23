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


AMCS = ["Kotak Mahindra Mutual Fund", "Mahindra Manulife Mutual Fund", "Bank of India Mutual Fund", "Baroda BNP Paribas Mutual Fund",
        "Aditya Birla Sun Life Mutual Fund", "HDFC Mutual Fund", "ICICI Prudential Mutual Fund", "The Wealth Company Mutual Fund",
        "Zerodha CASE Mutual Fund", "quant Mutual Fund", "Quantum Mutual Fund", "360 ONE Mutual Fund", "JM Financial Mutual Fund"]


def test_folder_to_fund_house():
    f = lambda folder: H._amc_for(folder, AMCS)
    assert f("Mahindra-Mutual-Fund") == "Mahindra Manulife Mutual Fund"      # not Kotak Mahindra
    assert f("Kotak-Mahindra-Mutual-Fund") == "Kotak Mahindra Mutual Fund"
    assert f("Bank-of-India-Mutual-Fund") == "Bank of India Mutual Fund"
    assert f("Aditya-Birla-Sun-Life-Mutual-Fund") == "Aditya Birla Sun Life Mutual Fund"
    assert f("Quant-Mutual-Fund") == "quant Mutual Fund"
    assert f("Quantum-Mutual-Fund") == "Quantum Mutual Fund"
    assert f("The-Wealth-Company-Mutual-Fund") == "The Wealth Company Mutual Fund"
    assert f("Zerodha-Mutual-Fund") == "Zerodha CASE Mutual Fund"
    assert f("360-ONE-Mutual-Fund") == "360 ONE Mutual Fund"
    assert f("JM-Financial-Mutual-Fund") == "JM Financial Mutual Fund"


MO = pd.DataFrame([
    {"pair_key": "motilal oswal mutual fund|motilal oswal flexi cap fund", "name": "Motilal Oswal Flexi Cap Fund", "amc": "Motilal Oswal Mutual Fund"},
    {"pair_key": "motilal oswal mutual fund|motilal oswal nifty midcap 150 index fund", "name": "Motilal Oswal Nifty Midcap 150 Index Fund", "amc": "Motilal Oswal Mutual Fund"},
    {"pair_key": "hsbc mutual fund|hsbc multi cap fund", "name": "HSBC Multi Cap Fund", "amc": "HSBC Mutual Fund"},
])


def test_category_words_block_lookalike_schemes():
    # Nov 2026: with the scheme itself missing from the universe, these sheets scored 0.84-0.89 against a sibling
    parsed = [(["Motilal Oswal Midcap Fund"], DF, "Scheme_Portfolio_Details_October_2026.xlsx", "Motilal-Oswal-Mutual-Fund"),
              (["MOTILAL OSWAL LARGE CAP FUND"], DF, "Scheme_Portfolio_Details_October_2026.xlsx", "Motilal-Oswal-Mutual-Fund"),
              (["hsbc small cap fund"], DF, "a.xlsx", "HSBC-Mutual-Fund"),
              (["HSBC Multi Cap Fund"], DF, "b.xlsx", "HSBC-Mutual-Fund")]
    m = H.map_to_schemes(parsed, MO).set_index("title")["pair_key"]
    assert pd.isna(m["Motilal Oswal Midcap Fund"])          # not the Flexi Cap fund, not the Midcap 150 index fund
    assert pd.isna(m["MOTILAL OSWAL LARGE CAP FUND"])
    assert pd.isna(m["hsbc small cap fund"])
    assert m["HSBC Multi Cap Fund"] == "hsbc mutual fund|hsbc multi cap fund"


def test_cat_words():
    assert H._cat_words("Motilal Oswal Midcap Fund") == {"mid cap"}
    assert H._cat_words("Kotak Large & Midcap Fund") == {"large&mid"}
    assert H._cat_words("Mirae Asset Large and Midcap Fund") == {"large&mid"}
    assert H._cat_words("Motilal Oswal Nifty Midcap 150 Index Fund") == {"mid cap", "index"}
    assert H._cat_words("SBI Long Term Equity Fund (Tax Saver)") == {"elss"}
