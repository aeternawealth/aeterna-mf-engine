"""Monthly PMS refresh (run on the 20th; retried daily to the 28th until APMI has the month).

    python tools/pms_update.py [YYYY-MM]      # default: last calendar month

1. If data/pms/apmi_monthly.csv already holds the month, stop ("up to date").
2. Fetch the month from APMI (engine/pms_fetch.py); fewer than 1,000 strategies = not published yet, stop.
3. Add it to the history, refresh the style-index TRI month-ends (data/pms/bench_monthly.csv; the bond column is rebuilt by pms_build).
4. Rebuild site/data/pms.json (tools/pms_build.py) and write outputs/latest/pms_changes.md: rating changes,
   strategies added and dropped. Writes "updated=1" to $GITHUB_OUTPUT when something changed.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.pms import load_raw  # noqa: E402
from engine.pms_fetch import fetch  # noqa: E402

HIST = ROOT / "data/pms/apmi_monthly.csv"
BENCH = ROOT / "data/pms/bench_monthly.csv"
SITE = ROOT / "site/data/pms.json"


def _out(k, v):
    p = os.environ.get("GITHUB_OUTPUT")
    if p:
        with open(p, "a") as f:
            f.write(f"{k}={v}\n")


def last_month():
    t = date.today()
    y, m = (t.year - 1, 12) if t.month == 1 else (t.year, t.month - 1)
    return f"{y}-{m:02d}"


def refresh_bench(month):
    """Month-end TRI levels from NSE Indices (same source as the fund engine)."""
    import requests
    from engine import ingest as I
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})
    try:
        s.get("https://www.niftyindices.com/reports/historical-data", timeout=60)
        cols = {}
        for n in ("NIFTY 50", "NIFTY 500", "NIFTY500 MULTICAP 50:25:25", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250"):
            ser = I.fetch_tri(s, n)
            if ser is None or ser.empty:
                raise RuntimeError(f"no data for {n}")
            me = ser.groupby(ser.index.to_period("M")).last()
            me.index = me.index.strftime("%Y-%m")
            cols[n] = me
        b = pd.DataFrame(cols)
        b = b[(b.index >= "2015-01") & (b.index <= month)]
        b.index.name = "month"
        b.to_csv(BENCH)
        print("bench: to", b.index.max())
    except Exception as e:   # keep the old file; that month's index comparison is missing until next run
        print("bench refresh failed:", type(e).__name__, str(e)[:200])


def changes(old, new):
    o = {s["id"]: s for s in old.get("strategies", [])}
    n = {s["id"]: s for s in new["strategies"]}
    lines = [f"# PMS refresh: data to {new['as_of']}", ""]
    moved = [(n[i], o[i].get("tier"), n[i].get("tier")) for i in n if i in o and o[i].get("tier") != n[i].get("tier") and (o[i].get("tier") or n[i].get("tier"))]
    lines.append(f"Rating changes: {len(moved)}")
    for s, a, b in sorted(moved, key=lambda x: x[0]["name"]):
        lines.append(f"- {s['name']} ({s['manager']}): {a or 'not rated'} -> {b or 'not rated'}" + (f"; {s['flag']}" if s.get("flag") else ""))
    add = [n[i] for i in n if i not in o]
    gone = [o[i] for i in o if i not in n]
    lines += ["", f"New on the site (Rs 100 crore or more): {len(add)}"] + [f"- {s['name']} ({s['manager']}), Rs {s['aum']:,.0f} cr" for s in add]
    lines += ["", f"Dropped (below Rs 75 crore): {len(gone)}"] + [f"- {s['name']} ({s['manager']})" for s in gone]
    return "\n".join(lines) + "\n"


def main():
    month = sys.argv[1] if len(sys.argv) > 1 else last_month()
    hist = pd.read_csv(HIST)
    if (hist.month == month).sum() >= 1000:
        print(month, "up to date")
        _out("updated", "0")
        return
    tmp = Path("/tmp/pms_update")
    fetch(tmp, [month])
    new = load_raw(tmp / "raw")
    new = new[new.month == month]
    if len(new) < 1000:
        print(month, f"not published yet ({len(new)} strategies)")
        _out("updated", "0")
        return
    hist = pd.concat([hist[hist.month != month], new[hist.columns.intersection(new.columns)]], ignore_index=True)
    hist.sort_values(["iaid", "month"]).to_csv(HIST, index=False)
    print(month, len(new), "strategies added")
    refresh_bench(month)
    old = json.loads(SITE.read_text()) if SITE.exists() else {}
    from tools.pms_build import build
    build()
    rep = changes(old, json.loads(SITE.read_text()))
    (ROOT / "outputs/latest").mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs/latest/pms_changes.md").write_text(rep, encoding="utf-8")
    print(rep)
    _out("updated", "1")


if __name__ == "__main__":
    main()
