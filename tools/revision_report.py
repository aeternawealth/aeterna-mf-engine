"""Monthly ratings revision report: what changed in this month's ratings and why, fund by fund.

    python tools/revision_report.py

Reads outputs/latest/rankings.csv (this month's ratings), outputs/latest/rating_history.json (the rating at each
month-end, with the reason for each change) and outputs/latest/audit.md if present. Writes
outputs/latest/revision_report.md and outputs/<YYYY-MM>/revision_report.md. Run by the monthly workflow after the
ratings and the audit; the monthly scheduled check emails it to the owner.
"""
from __future__ import annotations

import json
import time
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs" / "latest"
ORDER = {"A+": 4, "A": 3, "B": 2, "C": 1}
EQUITY = ["Large Cap", "Large & Mid Cap", "Mid Cap", "Small Cap", "Flexi Cap", "Multi Cap", "Focused", "ELSS", "Value", "Contra",
          "Dividend Yield", "Sectoral/Thematic"]


def main():
    r = pd.read_csv(OUT / "rankings.csv", low_memory=False)
    hist = json.loads((OUT / "rating_history.json").read_text()) if (OUT / "rating_history.json").exists() else {}
    eq = r[r.category.isin(EQUITY) & (r.plan_type == "Regular")]
    eq = eq.set_index(eq.code.astype(str))
    month = time.strftime("%Y-%m")
    rows = []
    for code, f in eq.iterrows():
        h = hist.get(code) or []
        if len(h) < 2:
            continue
        cur, prev = h[-1], h[-2]
        if cur[1] not in ORDER or prev[1] not in ORDER:
            continue
        step = ORDER[cur[1]] - ORDER[prev[1]]
        rk = (prev[2] - cur[2]) if cur[2] and prev[2] else 0
        if step == 0 and abs(rk) < 3 and not cur[5]:
            continue
        rows.append(dict(category=f.category, name=f["name"], prev=prev[1], cur=cur[1], prev_rank=prev[2], cur_rank=cur[2], n=cur[3],
                         step=step, rank_move=rk, score=cur[4], reason=cur[5] or "", mode=cur[6] if len(cur) > 6 else "",
                         flags=str(f.get("flags") or ""), before_cap=f.get("tier_before_cap")))
    D = pd.DataFrame(rows)
    L = [f"# Ratings revision, {time.strftime('%d %B %Y')}", ""]
    L.append("Equity funds, Regular plans (Direct plans move the same way). Compared with the previous month-end rating. "
             "Ratings describe the past, not a forecast.")
    L.append("")
    if len(D):
        up, dn = (D.step > 0).sum(), (D.step < 0).sum()
        L.append(f"**Summary.** {len(eq)} rated funds; {up} moved up a rating, {dn} moved down, "
                 f"{int(((D.step == 0) & (D.rank_move.abs() >= 3)).sum())} kept their rating but moved 3+ places.")
        modes = eq.groupby("category").market_mode.first() if "market_mode" in eq.columns else pd.Series(dtype=object)
        fall = [c for c, m in modes.items() if m == "after a fall"]
        L.append(f"**Market mode.** {'After-a-fall mode in: ' + ', '.join(fall) if fall else 'Every category in normal mode'}.")
        L.append("")
    for c in [c for c in EQUITY if c in set(eq.category)]:
        g = D[D.category == c] if len(D) else D
        e = eq[eq.category == c]
        ap = e[e.tier == "A+"].sort_values("score", ascending=False)
        L.append(f"## {c}")
        L.append(f"A+ now ({len(ap)}): " + (", ".join(f"{n} ({s:.0f})" for n, s in zip(ap["name"], ap.score)) if len(ap) else "none clears 75 this month"))
        if len(g):
            for title, part in (("Moved up", g[g.step > 0].sort_values("step", ascending=False)),
                                ("Moved down", g[g.step < 0].sort_values("step")),
                                ("Same rating, rank moved 3+ places", g[(g.step == 0) & (g.rank_move.abs() >= 3)].sort_values("rank_move", ascending=False))):
                if not len(part):
                    continue
                L.append(f"**{title}**")
                for x in part.itertuples():
                    cap = f" Score alone gives {x.before_cap}; one step lower for a portfolio outside SEBI limits." if isinstance(x.before_cap, str) and x.before_cap else ""
                    L.append(f"- {x.name}: {x.prev} to {x.cur}, rank {x.prev_rank} to {x.cur_rank} of {x.n}, score {x.score}. {x.reason}{cap}")
        else:
            L.append("No rating changes.")
        L.append("")
    a = OUT / "audit.md"
    if a.exists():
        L.append("## Audit")
        L += [l for l in a.read_text().splitlines() if l.startswith(("# Audit", "FAIL", "CHECK"))] or ["Nothing to fix."]
    text = "\n".join(L) + "\n"
    for p in (OUT / "revision_report.md", ROOT / "outputs" / month / "revision_report.md"):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(text[:3000])


if __name__ == "__main__":
    main()
