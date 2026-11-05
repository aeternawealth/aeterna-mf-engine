"""Agent 10 - AMC portfolio downloader (runs on your PC, zero AI tokens).

1. Reads advisorkhoj.com's per-AMC "Monthly Portfolio Disclosures" index (plain HTTP) to get the
   official link for "Monthly Portfolio Disclosure - <Month YYYY>" - usually a direct Excel/ZIP.
2. Downloads it to data/holdings/<YYYY-MM>/<AMC>/. Only if the link is a web page (or the file is
   blocked) does it start a headless Chromium (Playwright) and look for the file on that page.
3. Writes data/holdings/<YYYY-MM>/_download_log.csv  -> AMCs marked FAILED need a manual download
   (or add an override URL in data/manual/amc_sources.csv: amc,url).

Usage:  python -m engine.amc_downloader --month 2026-10 [--only HDFC,SBI] [--show]
"""
from __future__ import annotations

import argparse
import csv
import re
import zipfile
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config as C

INDEX = "https://www.advisorkhoj.com/form-download-centre/Mutual/{slug}/Monthly-Portfolio-Disclosures"
FILE_RE = re.compile(r"\.(xlsx|xls|xlsm|zip)(\?|$)", re.I)

# Top AMCs by equity AUM first. slug = advisorkhoj URL slug. Extend freely.
AMCS = [
    "SBI-Mutual-Fund", "ICICI-Prudential-Mutual-Fund", "HDFC-Mutual-Fund", "Nippon-India-Mutual-Fund",
    "Kotak-Mahindra-Mutual-Fund", "Axis-Mutual-Fund", "Aditya-Birla-Sun-Life-Mutual-Fund", "UTI-Mutual-Fund",
    "Mirae-Asset-Mutual-Fund", "DSP-Mutual-Fund", "Tata-Mutual-Fund", "Bandhan-Mutual-Fund",
    "Motilal-Oswal-Mutual-Fund", "Edelweiss-Mutual-Fund", "Canara-Robeco-Mutual-Fund",
    "Franklin-Templeton-Mutual-Fund", "PPFAS-Mutual-Fund", "Quant-Mutual-Fund", "HSBC-Mutual-Fund",
    "Invesco-Mutual-Fund", "Sundaram-Mutual-Fund", "Mahindra-Manulife-Mutual-Fund", "WhiteOak-Capital-Mutual-Fund",
    "Baroda-BNP-Paribas-Mutual-Fund", "LIC-Mutual-Fund", "Union-Mutual-Fund", "Bajaj-Finserv-Mutual-Fund",
    "360-ONE-Mutual-Fund", "Groww-Mutual-Fund", "Zerodha-Mutual-Fund", "ITI-Mutual-Fund", "JM-Financial-Mutual-Fund",
    "Navi-Mutual-Fund", "Helios-Mutual-Fund", "Trust-Mutual-Fund", "Samco-Mutual-Fund", "NJ-Mutual-Fund",
    "Bank-of-India-Mutual-Fund", "PGIM-India-Mutual-Fund", "Quantum-Mutual-Fund", "Shriram-Mutual-Fund",
    "Old-Bridge-Mutual-Fund", "Unifi-Mutual-Fund", "Abakkus-Mutual-Fund", "Angel-One-Mutual-Fund",
    "Jio-BlackRock-Mutual-Fund", "Capitalmind-Mutual-Fund", "Choice-Mutual-Fund", "The-Wealth-Company-Mutual-Fund",
]


def month_tokens(month: str) -> list[str]:
    d = pd.Period(month).to_timestamp(how="end")
    m, y = d.month, d.year
    full, abbr = d.strftime("%B"), d.strftime("%b")
    last = d.day
    toks = [f"{full} {y}", f"{full}-{y}", f"{full}_{y}", f"{full}{y}", f"{abbr} {y}", f"{abbr}-{y}", f"{abbr}_{y}",
            f"{abbr}{y}", f"{abbr}-{str(y)[2:]}", f"{abbr}'{str(y)[2:]}", f"{abbr} {str(y)[2:]}", f"{abbr}{str(y)[2:]}",
            f"{full}-{str(y)[2:]}", f"{full} {str(y)[2:]}",
            f"{last:02d}.{m:02d}.{y}", f"{last:02d}-{m:02d}-{y}", f"{last:02d}{m:02d}{y}", f"{y}{m:02d}{last:02d}",
            f"{y}-{m:02d}", f"{m:02d}-{y}", f"{m:02d}{y}", f"{y}{m:02d}", f"{last}{abbr}{y}", f"{last} {abbr} {y}"]
    return [t.lower() for t in toks]


def _matches_month(text: str, toks) -> bool:
    t = text.lower().replace("%20", " ")
    return any(k in t for k in toks)


def _candidate_links(page, toks):
    links = page.eval_on_selector_all(
        "a", "els => els.map(e => ({href: e.href || '', text: (e.innerText || e.title || '').trim()}))")
    good = []
    for l in links:
        blob = f"{l['href']} {l['text']}"
        is_file = bool(FILE_RE.search(l["href"]))
        if _matches_month(blob, toks) and (is_file or re.search(r"portfolio|download|excel|xls", blob, re.I)):
            score = (3 if is_file else 0) + (2 if re.search(r"portfolio", blob, re.I) else 0) \
                - (5 if re.search(r"fortnight|debt|factsheet|half.?year|pdf|overlap|dividend|etf", blob, re.I) else 0) \
                + (2 if re.search(r"monthly", blob, re.I) else 0) + (2 if re.search(r"all|consolidated|complete", blob, re.I) else 0)
            good.append((score, l))
    return [l for s, l in sorted(good, key=lambda x: -x[0]) if s > 0]


def _save(download, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / download.suggested_filename
    download.save_as(p)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if re.search(r"\.(xlsx|xls|xlsm)$", n, re.I) and not re.search(r"debt|fortnight", n, re.I):
                    z.extract(n, folder)
    return p


def _get(url, **kw):
    import requests
    return requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"}, timeout=90, **kw)


def list_amcs() -> list[str]:
    """All AMCs from advisorkhoj's 'Select Company' dropdown -> URL slugs."""
    h = _get(INDEX.format(slug="HDFC-Mutual-Fund")).text
    # any attributes: the page's own AMC (HDFC here) is the `selected` option and was being skipped
    names = re.findall(r'<option\b[^>]*\bvalue="([^"]+)"[^>]*>', h)
    slugs = [n.strip().replace(" ", "-") for n in names if n.strip().lower().endswith("mutual fund")]
    if len(slugs) < 20:   # dropdown changed or failed to load: use the built-in list
        return AMCS
    if "HDFC-Mutual-Fund" not in slugs:
        slugs.insert(0, "HDFC-Mutual-Fund")
    return list(dict.fromkeys(slugs))


def find_link(slug: str, month: str):
    """Return (href, label) of the 'Monthly Portfolio Disclosure - <Month YYYY>' entry for this AMC."""
    h = _get(INDEX.format(slug=slug)).text
    label = pd.Period(month).strftime("%B %Y").lower()
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        t = re.sub(r"<[^>]+>|\s+", " ", text).strip().lower()
        if t.startswith("monthly portfolio") and label in t and "advisorkhoj" not in href:
            return href.replace("&amp;", "&"), t
    return None, None


def _direct(url: str, folder: Path) -> Path | None:
    r = _get(url, allow_redirects=True)
    if r.status_code != 200 or len(r.content) < 2000 or r.content[:15].lstrip().lower().startswith((b"<!doctype", b"<html")):
        return None
    name = re.sub(r"[?#].*$", "", url.rstrip("/").split("/")[-1]) or "portfolio.xlsx"
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / re.sub(r"%20|[^A-Za-z0-9._-]", "_", name)
    p.write_bytes(r.content)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            for n in z.namelist():
                if re.search(r"\.(xlsx|xls|xlsm)$", n, re.I) and not re.search(r"debt|fortnight", n, re.I):
                    z.extract(n, folder)
    return p


_SKIP = re.compile(r"fortnight|half.?year|debt|liquid|overnight|money.?market|gilt|bond|factsheet|riskometer|risk-o-meter|"
                   r"dividend|overlap|exposure.*derivative|annual|\bter\b|\bkim\b|\bsid\b", re.I)


def _download_all(html: str, base: str, month: str, folder: Path) -> list[Path]:
    from urllib.parse import urljoin, unquote
    toks = month_tokens(month)
    links = set(re.findall(r'(?:href|data-href|data-url)\s*=\s*["\']([^"\']+?\.(?:xlsx?|xlsm|zip)(?:\?[^"\']*)?)["\']', html, re.I))
    pick = []
    for l in links:
        name = unquote(l.split("?")[0].rsplit("/", 1)[-1]).lower().replace("–", "-")
        if _matches_month(unquote(l), toks) and not _SKIP.search(name.replace("portfolio", "")):
            pick.append(urljoin(base, l))
    got = []
    for u in sorted(pick)[:200]:
        try:
            p = _direct(u, folder)
            if p:
                got.append(p)
        except Exception:
            continue
    return got


def download_amc(ctx, slug: str, month: str, out: Path, override: str | None = None):
    from .amc_adapters import AMC_ADAPTERS
    if slug in AMC_ADAPTERS:                      # dedicated adapter for script/API-driven AMC sites
        try:
            urls = AMC_ADAPTERS[slug](month)
        except Exception as e:
            return "FAILED", f"adapter error: {type(e).__name__}: {str(e)[:120]}", None
        if not urls:
            return "NOT_YET", "adapter found no files for this month", None
        got = [p for p in (_direct(u, out / slug) for u in urls) if p]
        return ("OK", f"{len(got)}/{len(urls)} files via adapter", got[0]) if got else ("FAILED", "adapter files did not download", None)
    return _download_generic(ctx, slug, month, out, override)


def _download_generic(ctx, slug: str, month: str, out: Path, override: str | None = None):
    try:
        url, label = (override, "override") if override else find_link(slug, month)
    except Exception as e:
        return "FAILED", f"advisorkhoj: {type(e).__name__}", None
    if not url:
        return "NOT_YET", f"no '{pd.Period(month).strftime('%B %Y')}' entry on advisorkhoj yet", None
    if FILE_RE.search(url):
        try:
            p = _direct(url, out / slug)
            if p:
                return "OK", url, p
        except Exception:
            pass
    # Page (not a file): many AMCs list one file PER SCHEME on the page (Canara, Helios...). Collect every
    # month-matching monthly-portfolio file from the static HTML first; render with a browser only if none.
    if not url.lower().startswith("http"):
        return "FAILED", f"no usable link on advisorkhoj ({url})", None
    try:
        got = _download_all(_get(url).text, url, month, out / slug)
        if got:
            return "OK", f"{len(got)} files from {url}", got[0]
    except Exception:
        pass
    if ctx is None:
        return "FAILED", f"needs browser: {url}", None
    page = ctx.new_page()
    try:
        if FILE_RE.search(url):
            with page.expect_download(timeout=90000) as d:
                page.evaluate("u => { const a=document.createElement('a'); a.href=u; document.body.appendChild(a); a.click(); }", url)
            return "OK", url, _save(d.value, out / slug)
        page.goto(url, timeout=90000, wait_until="domcontentloaded")
        page.wait_for_timeout(4000)
        got = _download_all(page.content(), url, month, out / slug)
        if got:
            return "OK", f"{len(got)} files (rendered) from {url}", got[0]
        cands = _candidate_links(page, month_tokens(month))
        for l in cands[:3]:
            if FILE_RE.search(l["href"]):
                p = _direct(l["href"], out / slug)
                if p:
                    return "OK", l["href"], p
            try:
                with page.expect_download(timeout=60000) as d:
                    page.evaluate("u => { const a=[...document.querySelectorAll('a')].find(x=>x.href===u); a ? a.click() : window.open(u); }", l["href"])
                return "OK", l["href"], _save(d.value, out / slug)
            except Exception:
                continue
        return "FAILED", f"no {month} file found on {url}", None
    except Exception as e:
        return "FAILED", f"{type(e).__name__}: {str(e)[:150]}", None
    finally:
        page.close()


def run(month: str, only=None, show=False, log=print):
    out = C.DATA / "holdings" / month
    out.mkdir(parents=True, exist_ok=True)
    overrides = {}
    ov = C.MANUAL / "amc_sources.csv"
    if ov.exists():
        overrides = dict(pd.read_csv(ov)[["amc", "url"]].values)
    try:
        amcs = list_amcs()
    except Exception:
        amcs = AMCS
    amcs = [a for a in amcs if not only or any(o.lower() in a.lower() for o in only)]
    rows, pw, b, ctx = [], None, None, None
    try:
        for slug in amcs:
            if (out / slug).exists() and any((out / slug).glob("*.xls*")):
                rows.append((slug, "SKIPPED", "already downloaded", ""))
                continue
            st, info, path = download_amc(ctx, slug, month, out, overrides.get(slug))
            if st == "FAILED" and ctx is None and info.startswith("needs browser"):
                from playwright.sync_api import sync_playwright
                pw = sync_playwright().start()
                b = pw.chromium.launch(headless=not show)
                ctx = b.new_context(accept_downloads=True, user_agent=C.HTTP_HEADERS["User-Agent"])
                st, info, path = download_amc(ctx, slug, month, out, overrides.get(slug))
            rows.append((slug, st, info, str(path or "")))
            log(f"  {st:7s} {slug}  {info if st != 'OK' else ''}")
    finally:
        if b:
            b.close()
        if pw:
            pw.stop()
    with open(out / "_download_log.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["amc", "status", "info", "file", f"run {datetime.now():%Y-%m-%d %H:%M}"])
        w.writerows(rows)
    ok = sum(r[1] in ("OK", "SKIPPED") for r in rows)
    pending = sum(r[1] == "NOT_YET" for r in rows)
    log(f"  holdings download: {ok}/{len(rows)} AMCs OK, {pending} not published yet -> {out}")
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=(pd.Period(datetime.now(), "M") - 1).strftime("%Y-%m"))
    ap.add_argument("--only", default=None)
    ap.add_argument("--show", action="store_true", help="show the browser window")
    a = ap.parse_args()
    run(a.month, a.only.split(",") if a.only else None, a.show)
