"""Fund names shown on the site are tidied (Nov 2026 audit); fund addresses do not change with the tidying."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "site"))
import build_pages as P  # noqa: E402
from engine import ingest  # noqa: E402


def test_nice_names():
    assert P.nice("UTI - Flexi Cap Fund.") == "UTI Flexi Cap Fund"
    assert P.nice("Bandhan Gilt   Fund") == "Bandhan Gilt Fund"
    assert P.nice("ICICI Prudential Liquid Fund -") == "ICICI Prudential Liquid Fund"
    assert P.nice("SBI AGGRESSIVE HYBRID FUND") == "SBI Aggressive Hybrid Fund"
    assert P.nice("ICICI Prudential Money Market Fund - Cash Option") == "ICICI Prudential Money Market Fund"


def test_cash_option_pairs_with_direct():
    head = "Scheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n"
    t = (head + "Open Ended Schemes(Equity Scheme - Large Cap Fund)\nICICI Prudential Mutual Fund\n"
         "1;A;-;ICICI Prudential Large Fund - Cash Option;Regular Plan;Growth;10;20-Nov-2026\n"
         "2;B;-;ICICI Prudential Large Fund;Direct Plan;Growth;11;20-Nov-2026\n")
    u = ingest.build_universe(ingest.parse_navall(t))
    assert u["pair_key"].nunique() == 1
