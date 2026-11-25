"""Period rankings (1M, 3M, 6M, 1Y, 3Y, 5Y): equity and hybrid funds carry no cost input (returns are already after costs)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import config as C  # noqa: E402

HORIZONS = ("1M", "3M", "YTD", "6M", "1Y", "3Y", "5Y")


def test_equity_and_hybrid_period_views_have_no_cost():
    for cat in ("Flexi Cap", "Small Cap", "Large Cap", "ELSS", "Sectoral/Thematic", "Aggressive Hybrid", "Balanced Advantage"):
        for h in HORIZONS:
            p = C.horizon_protocol(h, cat)
            assert "ter" not in p and "ter_base" not in p, (cat, h)
            assert all(v[0] != "Cost" for v in p.values()), (cat, h)
            assert sum(v[1] for v in p.values()) == 100, (cat, h)


def test_return_over_benchmark_leads():
    for h in HORIZONS:
        p = C.horizon_protocol(h, "Flexi Cap")
        assert max(p, key=lambda k: p[k][1]) == f"excess_{h}"


def test_other_families_unchanged():
    for h in HORIZONS:
        assert "ter" in C.horizon_protocol(h, "Index Fund")
        assert "ter_base" in C.horizon_protocol(h, "Arbitrage")
