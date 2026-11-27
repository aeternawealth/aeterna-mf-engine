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


TYPES = ("Equity", "Debt", "Hybrid", "Multi Asset")
SERVICES = ("D", "N")   # discretionary, non-discretionary
POST = "https://www.apmiindia.org/apmi/welcomeiaperformance.htm?action=loadIAReport"


def _month_end(ym):
    import calendar
    y, m = map(int, ym.split("-"))
    return f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"


def fetch(out: Path, months, debug: Path = None, types=TYPES, services=SERVICES, bench=False):
    """For each month, strategy type and service type: the same request APMI's own form sends (action=loadIAReport),
    made from a browser session on the report page; the raw response is saved as is (OUT/raw/) for parsing."""
    from playwright.sync_api import sync_playwright
    raw = out / ("raw_bench" if bench else "raw")
    raw.mkdir(parents=True, exist_ok=True)
    log = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        ctx = b.new_context(user_agent=UA)
        page = ctx.new_page()
        page.goto(URL, timeout=120000, wait_until="domcontentloaded")
        for ym in months:
            y, m = ym.split("-")
            for t in types:
                for sv in services:
                    row = {"month": ym, "type": t, "service": sv, "bytes": 0, "status": "", "note": ""}
                    try:
                        form = {"strategyname": t, "servicetype": sv, "fromMonth": str(int(m)),
                                "fromYears": y, "asOnDate": _month_end(ym)}
                        if bench:   # the report adds BSE 500 TRI (22), MSEI SX 40 TRI (21) and Nifty 50 TRI (17) rows
                            form.update(SelectedBenchmark="22,21,17", pmsProvideName="", pmsInvAprochName="", benchmark="null")
                        r = ctx.request.post(POST, form=form,
                                             headers={"Referer": URL, "X-Requested-With": "XMLHttpRequest"}, timeout=180000)
                        body = r.text()
                        name = f"{ym}_{t.replace(' ', '')}_{sv}.txt"
                        (raw / name).write_text(body, encoding="utf-8")
                        row.update(bytes=len(body), status=str(r.status), note=re.sub(r"\s+", " ", body[:160]))
                    except Exception as e:
                        row.update(status="fail", note=f"{type(e).__name__}: {str(e)[:200]}")
                    log.append(row)
                    print(row, flush=True)
                    time.sleep(3)   # polite: one request at a time
        b.close()
    with open(out / "_fetch_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["month", "type", "service", "bytes", "status", "note"])
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


def probe_bench(out: Path, ym="2026-10"):
    """Find how APMI's page loads benchmark returns: submit the form, tick every benchmark in the table filter,
    record the POST requests and the rows that appear (OUT/bench_probe/)."""
    import json as _j
    from playwright.sync_api import sync_playwright
    d = out / "bench_probe"
    d.mkdir(parents=True, exist_ok=True)
    posts = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        page = b.new_context(user_agent=UA).new_page()

        def on_resp(resp):
            rq = resp.request
            if rq.method == "POST":
                try:
                    body = resp.text()
                except Exception:
                    body = ""
                posts.append({"url": rq.url, "post": (rq.post_data or "")[:3000], "status": resp.status, "body": body[:20000]})
        page.on("response", on_resp)
        page.goto(URL, timeout=120000, wait_until="domcontentloaded")
        y, m = ym.split("-")
        page.select_option("#fromMonth", str(int(m)))
        page.select_option("#fromYears", y)
        page.click("button:has-text('Submit')")
        page.wait_for_load_state("networkidle", timeout=180000)
        page.wait_for_timeout(3000)
        page.evaluate("""() => { const s = document.getElementById('tableFilter-benchmark'); if (!s) return;
            for (const o of s.options) o.selected = true; s.dispatchEvent(new Event('change', {bubbles: true}));
            if (window.getSelectedData) window.getSelectedData(); }""")
        page.wait_for_load_state("networkidle", timeout=120000)
        page.wait_for_timeout(5000)
        h = page.content()
        rows = [r for r in re.findall(r"<tr.*?</tr>", h, re.S) if re.search(r"TRI", r)]
        (d / "bench_rows.html").write_text("\n".join(rows[:50]), encoding="utf-8")
        (d / "posts.json").write_text(_j.dumps(posts, indent=1), encoding="utf-8")
        b.close()
    print("posts", len(posts), "TRI rows", len(rows))


if __name__ == "__main__":
    out = Path(sys.argv[1])
    args = sys.argv[2:]
    if args[:1] == ["--bench"]:
        fetch(out, all_months(), types=("Equity",), services=("D",), bench=True)
        sys.exit(0)
    if args[:1] == ["--probe-bench"]:
        probe_bench(out)
        sys.exit(0)
    months = all_months() if args == ["--all"] else args
    fetch(out, months)
