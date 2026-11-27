"""PMS strategy performance from APMI (Association of Portfolio Managers in India).

    python -m engine.pms_fetch OUT_DIR 2026-10 [2026-09 ...]     # month-ends to fetch (YYYY-MM)
    python -m engine.pms_fetch OUT_DIR --all                       # Jan 2023 to the latest month APMI offers

APMI publishes every portfolio manager's investment approaches (strategies) each month, as SEBI requires:
AUM, returns after fees (TWRR) over 1M to since inception, and the benchmark's returns. The public report is
www.apmiindia.org/apmi/welcomeiaperformance.htm (no robots.txt; the data is published for investors to compare).
We open it in a headless browser, choose the month, submit the form and read the table: one polite request
at a time, a few seconds apart. Writes OUT_DIR/<YYYY-MM>.csv and OUT_DIR/_fetch_log.csv.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path

URL = "https://www.apmiindia.org/apmi/welcomeiaperformance.htm?action=PMSmenu"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _table(html):
    """Every <table> row as a list of cell texts; returns (header, rows) of the widest table."""
    best = ([], [])
    for t in re.findall(r"<table.*?</table>", html, re.S | re.I):
        rows = [[_clean(c) for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r, re.S | re.I)]
                for r in re.findall(r"<tr.*?</tr>", t, re.S | re.I)]
        rows = [r for r in rows if r]
        if len(rows) > len(best[1]) + 1:
            best = (rows[0], rows[1:])
    return best


def fetch(out: Path, months, debug: Path = None):
    from playwright.sync_api import sync_playwright
    out.mkdir(parents=True, exist_ok=True)
    log = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(user_agent=UA)
        page = ctx.new_page()
        posts = []
        page.on("request", lambda rq: posts.append({"url": rq.url, "post": (rq.post_data or "")[:3000]})
                if rq.method == "POST" else None)
        for ym in months:
            y, m = ym.split("-")
            row = {"month": ym, "rows": 0, "status": "", "note": ""}
            try:
                page.goto(URL, timeout=120000, wait_until="domcontentloaded")
                page.select_option("#fromMonth", str(int(m)))
                page.select_option("#fromYears", y)
                btn = None
                for sel in ("button:has-text('Submit')", "input[type=submit]", "button:has-text('Search')",
                            "button:has-text('Go')", "button[type=submit]", "button:has-text('Show')"):
                    if page.query_selector(sel):
                        btn = sel
                        break
                if not btn:
                    raise RuntimeError("no submit button")
                page.click(btn)
                page.wait_for_load_state("networkidle", timeout=120000)
                page.wait_for_timeout(3000)
                html = page.content()
                head, rows = _table(html)
                if debug and not (debug / "first.html").exists():
                    debug.mkdir(parents=True, exist_ok=True)
                    (debug / "first.html").write_text(html[:4_000_000], encoding="utf-8")
                    (debug / "posts.json").write_text(json.dumps(posts[-5:], indent=1), encoding="utf-8")
                    (debug / "buttons.txt").write_text("\n".join(
                        (e.inner_text() or e.get_attribute("value") or "")[:60] + " | " + (e.get_attribute("onclick") or "")[:200]
                        for e in page.query_selector_all("button, input[type=submit], input[type=button]")), encoding="utf-8")
                if not rows:
                    raise RuntimeError("empty table")
                with open(out / f"{ym}.csv", "w", newline="", encoding="utf-8") as f:
                    w = csv.writer(f)
                    w.writerow(head)
                    w.writerows(rows)
                row.update(rows=len(rows), status="ok", note=" | ".join(head)[:300])
            except Exception as e:
                row.update(status="fail", note=f"{type(e).__name__}: {str(e)[:200]}")
            log.append(row)
            print(row, flush=True)
            time.sleep(4)   # polite: one month at a time
        b.close()
    with open(out / "_fetch_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["month", "rows", "status", "note"])
        w.writeheader()
        w.writerows(log)
    return log


def all_months(last="2026-10"):
    y, m = 2023, 1
    ly, lm = map(int, last.split("-"))
    res = []
    while (y, m) <= (ly, lm):
        res.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return res


if __name__ == "__main__":
    out = Path(sys.argv[1])
    args = sys.argv[2:]
    months = all_months() if args == ["--all"] else args
    fetch(out, months, debug=out / "_debug")
