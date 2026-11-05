"""Inspect AMC portfolio pages from GitHub's servers to build direct download adapters.

    python tools/probe_amc.py out_dir URL [URL ...]

For each URL: plain HTTP status + every spreadsheet/zip link in the static HTML, then the page rendered in
headless Chromium with every network request recorded (XHR/fetch URLs, methods, POST bodies, and the first
4 KB of JSON responses), plus links found after rendering. Writes one JSON file per URL.
"""
import json
import re
import sys
from pathlib import Path

import requests

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
FILE = re.compile(r"""["'(]([^"'()\s]+?\.(?:xlsx?|xlsm|zip|pdf)(?:\?[^"'()\s]*)?)["')]""", re.I)


def probe(url: str, rep: dict) -> dict:
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=45)
        rep["http"] = {"status": r.status_code, "bytes": len(r.content), "final_url": r.url,
                       "file_links": sorted(set(FILE.findall(r.text)))[:300]}
    except Exception as e:
        rep["http"] = {"error": f"{type(e).__name__}: {str(e)[:200]}"}
    from playwright.sync_api import sync_playwright
    reqs = []
    with sync_playwright() as pw:
        import os
        ch = os.environ.get("PW_CHANNEL") or ("msedge" if sys.platform == "win32" else None)
        b = pw.chromium.launch(channel=ch)
        ctx = b.new_context(user_agent=UA, accept_downloads=True)
        page = ctx.new_page()

        def on_resp(resp):
            rq = resp.request
            if rq.resource_type in ("image", "stylesheet", "font", "media"):
                return
            item = {"url": resp.url[:500], "method": rq.method, "type": rq.resource_type, "status": resp.status,
                    "ctype": resp.headers.get("content-type", "")[:80]}
            if rq.method == "POST":
                item["post"] = (rq.post_data or "")[:1500]
            if "json" in item["ctype"]:
                try:
                    item["body"] = resp.text()[:4000]
                except Exception:
                    pass
            reqs.append(item)
        page.on("response", on_resp)
        try:
            page.goto(url, timeout=90000, wait_until="domcontentloaded")
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception as e:
            rep["render_error"] = f"{type(e).__name__}: {str(e)[:200]}"
        page.wait_for_timeout(5000)
        import traceback
        try:   # open tabs / accordions / buttons that load the portfolio list on click (LIC, Bandhan, ...)
            clicked = []
            for el in page.query_selector_all("a[href^='#'], button, [role=tab], li[data-tab], div[data-toggle], span[onclick]")[:300]:
                try:
                    t = (el.inner_text() or "").strip()
                except Exception:
                    continue
                if re.search(r"monthly portfolio|month end portfolio|portfolio disclosure|^portfolios?$|scheme portfolio", t, re.I) and el.is_visible():
                    try:
                        el.click(timeout=3000)
                        page.wait_for_timeout(3500)
                        clicked.append(t[:80])
                    except Exception:
                        pass
                if len(clicked) >= 6:
                    break
            rep["clicked"] = clicked
        except Exception:
            rep["click_error"] = traceback.format_exc()[-400:]
        try:
            rep["_html"] = page.content()
        except Exception:
            pass
        steps = {
            "rendered_file_links": lambda: sorted(set(FILE.findall(page.content())), key=lambda l: (not re.search(r"\.xls|\.zip", l, re.I), l))[:2500],
            "anchors_mentioning_portfolio": lambda: page.evaluate(
                "() => [...document.querySelectorAll('a,button')].map(e => [(e.innerText||'').trim().slice(0,120), e.getAttribute('href')||'', e.getAttribute('onclick')||''])"
                ".filter(x => /portfolio|monthly|download|sep|2026/i.test(x.join(' '))).slice(0,200)"),
            "selects": lambda: page.evaluate("() => [...document.querySelectorAll('select')].map(s => [s.name||s.id, [...s.options].slice(0,40).map(o => o.value+'|'+o.text)])"),
            "title": lambda: page.title(),
        }
        for k, fn in steps.items():
            try:
                rep[k] = fn()
            except Exception:
                rep[k + "_error"] = traceback.format_exc()[-600:]
        b.close()
    rep["requests"] = [r for r in reqs if r["type"] in ("xhr", "fetch", "document") or r["method"] == "POST"][:300]
    return rep


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    for u in sys.argv[2:]:
        name = re.sub(r"[^A-Za-z0-9]+", "_", u.split("//", 1)[-1])[:80]
        rep = {"url": u}
        try:
            probe(u, rep)   # fills rep step by step: a crash keeps what was gathered
        except Exception:
            import traceback
            rep["error"] = traceback.format_exc()[-1500:]
        html = rep.pop("_html", None)
        if html:
            (out / f"{name}.html").write_text(html[:3_000_000], encoding="utf-8")
        (out / f"{name}.json").write_text(json.dumps(rep, indent=1))
        print(u, "->", rep.get("http", {}).get("status"), len(rep.get("requests", [])), "requests,",
              len(rep.get("rendered_file_links", [])), "file links", flush=True)
