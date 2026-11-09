"""Builds the public website's data files from the engine's latest outputs.
site/data/funds.json (one record per plan), holdings.json (top holdings per scheme), meta.json."""
import json, math, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
src = json.loads((ROOT / "outputs" / "latest" / "rankings.json").read_text())
KEEP = ["code","name","amc","asset_class","tax","bench_label","category","peer_group","plan_type","benchmark","tier","score","peer_rank","peer_count","flags","gate",
 "age_years","nav_latest","nav_date","nav_prev_date","nav_chg_1d","ter","ter_base","ter_date","aum_cr","aum_asof","pair_key",
 "roll3y_excess_median","roll3y_hit_rate","roll1y_hit_rate","info_ratio_3y","capture_ratio_3y","alpha_3y","sharpe_3y","sortino_3y",
 "roll1y_excess_median","neg_months_3y","worst_day_3y","worst_rel_day_5y","worst_rel_day_date","liq_cagr_1y","liq_cagr_3y","excess_vs_liquid_1y","excess_vs_liquid_3y","excess_vs_liquid_post_tax_1y","excess_vs_liquid_post_tax_3y",
 "downside_capture_3y","upside_capture_3y","max_drawdown_5y","max_drawdown_3y","vol_3y","beta_3y","tracking_diff_1y","tracking_err_1y",
 "hist3y_n","hist3y_median","hist3y_p10","hist3y_p90","hist3y_worst","hist3y_best","hist3y_pos","hist3y_gt7","hist3y_from",
 "flow_1q","flow_4q","flow_quarter","aum_1y_ago_cr","n_stocks","top10_pct","large_pct","mid_pct","small_pct","active_share",
 "cash_other_pct","top_sector","top_sector_pct","mandate_breaches","holdings_month"]
for h in ["6M","1Y","3Y","5Y"]:
    KEEP += [f"ret_{h}", f"excess_{h}", f"rank_{h}", f"peers_{h}", f"score_{h}"]
def clean(v):
    if isinstance(v, float):
        if math.isnan(v) or math.isinf(v): return None
        return round(v, 5)
    return v
funds = []
import datetime as _dt
_dates = [str(f.get("nav_date"))[:10] for f in src["funds"] if f.get("nav_date")]
_latest = max(_dates) if _dates else None
dropped = []
for f in src["funds"]:
    # a scheme with no NAV for 90+ days has been merged or wound up: keep it out of the public site
    d = str(f.get("nav_date") or "")[:10]
    if _latest and d and (_dt.date.fromisoformat(_latest) - _dt.date.fromisoformat(d)).days > 90:
        dropped.append(f.get("name")); continue
    r = {k: clean(f.get(k)) for k in KEEP if f.get(k) not in (None, "")}
    if r.get("category") in ("Value", "Contra"): r["category"] = "Value / Contra"
    funds.append(r)
out = ROOT / "site" / "data"; out.mkdir(parents=True, exist_ok=True)
(out / "funds.json").write_text(json.dumps(funds, separators=(",", ":")))
if dropped:
    print(f"dropped {len(dropped)} closed or merged plans (no NAV for 90+ days): {sorted(set(dropped))}")
import re
# AMC files mark footnotes on security names (e.g. 'HDFC Bank Ltd.£', 'Infosys Ltd.*'): drop trailing marks
hold = {pk: [[r[0], re.sub(r"[\s£$#*@^~†‡§¥€]+$", "", str(r[1])), *r[2:]] for r in rows] for pk, rows in (src.get("holdings", {}) or {}).items()}
# some AMC files carry the ISIN but no security name: borrow the name another fund uses for that ISIN
_bad = lambda n: str(n).strip().lower() in ("nan", "none", "", "-")
_names = {}
for rows in hold.values():
    for r in rows:
        if r and not _bad(r[1]) and r[0]:
            _names.setdefault(r[0], r[1])
_fixed = _left = 0
for pk, rows in hold.items():
    for r in rows:
        if _bad(r[1]):
            if _names.get(r[0]):
                r[1] = _names[r[0]]; _fixed += 1
            else:
                r[1] = "Unnamed holding (" + str(r[0]) + ")" if r[0] else "Unnamed holding"; _left += 1
if _fixed or _left:
    print(f"holdings: {_fixed} security names filled from other funds by ISIN, {_left} left unnamed")
src["holdings"] = hold
(out / "holdings.json").write_text(json.dumps(hold, separators=(",", ":")))
meta = dict(src.get("meta", {})); meta["as_of"] = src["as_of"]; meta["n_funds"] = len(funds)
# Holdings coverage, for the methodology page and the 'holdings not available' note on fund pages
H = src.get("holdings", {}) or {}
schemes = {}
for f in funds:
    schemes.setdefault(f.get("pair_key"), f)
by_amc = {}
for pk, f in schemes.items():
    a = by_amc.setdefault(f.get("amc", ""), [0, 0])
    a[0] += 1
    a[1] += bool(H.get(pk))
meta["holdings_coverage"] = {"schemes": len(schemes), "with_holdings": sum(v[1] for v in by_amc.values())}
meta["holdings_missing_amcs"] = sorted(([a, v[0]] for a, v in by_amc.items() if v[1] == 0), key=lambda x: -x[1])
(out / "meta.json").write_text(json.dumps(meta))
print("funds", len(funds), "holdings", len(src.get("holdings", {})), {p.name: p.stat().st_size // 1024 for p in out.glob("*.json")})
