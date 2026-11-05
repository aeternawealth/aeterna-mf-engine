"""Builds the public website's data files from the engine's latest outputs.
site/data/funds.json (one record per plan), holdings.json (top holdings per scheme), meta.json."""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = json.loads((ROOT / "outputs" / "latest" / "rankings.json").read_text())
KEEP = ["code","name","amc","category","peer_group","plan_type","benchmark","tier","score","peer_rank","peer_count","flags","gate",
 "age_years","nav_latest","nav_date","nav_prev_date","nav_chg_1d","ter","ter_date","aum_cr","pair_key",
 "roll3y_excess_median","roll3y_hit_rate","roll1y_hit_rate","info_ratio_3y","capture_ratio_3y","alpha_3y","sharpe_3y","sortino_3y",
 "downside_capture_3y","upside_capture_3y","max_drawdown_5y","max_drawdown_3y","vol_3y","beta_3y","tracking_diff_1y","tracking_err_1y",
 "hist3y_n","hist3y_median","hist3y_p10","hist3y_p90","hist3y_worst","hist3y_best","hist3y_pos","hist3y_gt7","hist3y_from",
 "flow_1q","flow_4q","flow_quarter","aum_1y_ago_cr","n_stocks","top10_pct","large_pct","mid_pct","small_pct","active_share",
 "cash_other_pct","top_sector","top_sector_pct","mandate_breaches"]
for h in ["6M","1Y","3Y","5Y"]:
    KEEP += [f"ret_{h}", f"excess_{h}", f"rank_{h}", f"peers_{h}", f"score_{h}"]
def clean(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return None
        return round(v, 5)
    return v
funds = []
for f in src["funds"]:
    r = {k: clean(f.get(k)) for k in KEEP if f.get(k) not in (None, "")}
    if r.get("category") in ("Value", "Contra"): r["category"] = "Value / Contra"
    funds.append(r)
out = ROOT / "site" / "data"; out.mkdir(parents=True, exist_ok=True)
(out / "funds.json").write_text(json.dumps(funds, separators=(",", ":")))
(out / "holdings.json").write_text(json.dumps(src.get("holdings", {}), separators=(",", ":")))
meta = dict(src.get("meta", {})); meta["as_of"] = src["as_of"]; meta["n_funds"] = len(funds)
(out / "meta.json").write_text(json.dumps(meta))
print("funds", len(funds), "holdings", len(src.get("holdings", {})), {p.name: p.stat().st_size // 1024 for p in out.glob("*.json")})
