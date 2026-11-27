"""PMS rating method v2 (docs/thesis_pms_ratings.md): yardsticks per asset class, tiers, buffer."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.pms_build import _tier, _stats, _trailing  # noqa: E402

D = json.loads((ROOT / "site/data/pms.json").read_text())
R = [s for s in D["strategies"] if s.get("rated") and s.get("tier")]


def test_each_asset_class_has_its_own_yardstick():
    for s in R:
        y = s["yard"]["name"]
        if s["group"] == "Equity":
            assert y.endswith("TRI") and "bond" not in y and s["peer_group"] in ("Large and multi cap", "Mid and small cap")
        elif s["group"] == "Debt":
            assert y == "median high-quality bond fund"
        else:
            assert "Nifty 500 TRI" in y and "bond" in y and 0 <= s["yard"]["mix"] <= 1


def test_mid_small_peers_use_mid_small_indices():
    for s in R:
        if s.get("peer_group") == "Mid and small cap":
            assert s["yard"]["key"] in ("NIFTY MIDCAP 150", "NIFTY SMALLCAP 250")


def test_tiers_follow_rank_and_guard():
    for s in R:
        if s["tier"] in ("A+", "A") and not s.get("flag"):
            assert s["m"]["ex3y"] > 0 and s["m"]["alpha"] > 0
        if s["tier"] == "A+":
            assert s["score"] >= 70 - 5


def test_buffer_keeps_tier_near_boundary_and_moves_when_clear():
    assert _tier(0.68, 60, "A", True, 0.05) == "A"       # just below the A line: kept
    assert _tier(0.60, 60, "A", True, 0.05) == "B"       # clearly below: moves
    assert _tier(0.72, 60, "B", True, 0.05) == "B"       # just above: needs 5 more points to move up
    assert _tier(0.80, 60, "B", True, 0.05) == "A"
    assert _tier(0.95, 80, None, False, 0.05) == "B"     # no lead over the yardstick: capped at B


def test_stats_against_itself_is_neutral():
    r = [1.0, -2.0, 3.0, 0.5] * 6
    m = _stats(r, r)
    assert abs(m["ex_ann"]) < 1e-9 and abs(m["alpha"]) < 1e-9 and m["hit_m"] == 0


def test_trailing_returns():
    lv = {f"2025-{k:02d}": 100 * 1.01 ** k for k in range(1, 13)}
    lv["2024-12"] = 100.0
    t = _trailing(lv, "2025-12")
    assert abs(t["r1y"] - (1.01 ** 12 - 1) * 100) < 0.01
