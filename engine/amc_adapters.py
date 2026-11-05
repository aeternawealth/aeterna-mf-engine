"""Per-AMC portfolio adapters: for AMCs whose websites load files through scripts/APIs.
Each adapter returns the list of file URLs for the requested month (YYYY-MM); the generic
downloader then fetches, unzips and parses them. Add a new AMC = add one function + one AMC_ADAPTERS entry.
"""
from __future__ import annotations

import re

import pandas as pd
import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
_SKIP = re.compile(r"debt|liquid|overnight|money market|gilt|bond|arbitrage|hybrid|savings|fortnight|half.?year|etf|fof|fund of fund|"
                   r"multi asset|balanced|conservative|duration|credit|corporate|banking and psu|floater|income", re.I)


def _month(month: str):
    p = pd.Period(month)
    return p.strftime("%B").lower(), p.strftime("%b").lower(), p.year


def invesco(month: str) -> list[str]:
    full, abbr, y = _month(month)
    out = []
    for cls in ("equity", "index"):
        r = requests.get("https://www.invescomutualfund.com/api/CompleteMonthlyHoldings",
                         params={"year": y, "classification": cls}, headers=UA, timeout=60)
        for f in r.json() if r.ok else []:
            u = f.get(f"{abbr.capitalize()}Url") or f.get(f"{full.capitalize()}Url")
            if u and not _SKIP.search(f.get("Name", "")):
                out.append(u)
    return out


def mirae(month: str) -> list[str]:
    full, abbr, y = _month(month)
    r = requests.post("https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData",
                      json={"request": {"modulename": "portfolio_tab1", "pgno": 1, "pgsize": 400}},
                      headers={**UA, "X-Requested-With": "XMLHttpRequest"}, timeout=60)
    out = []
    for d in r.json().get("Data", []):
        t = d.get("Title", "").lower()
        if (full in t or f"{abbr} " in t) and str(y) in t and not _SKIP.search(t):
            out.append("https://www.miraeassetmf.co.in" + d["URL"] if d["URL"].startswith("/") else d["URL"])
    return out


def whiteoak(month: str) -> list[str]:
    full, abbr, y = _month(month)
    out = []
    for page in range(1, 6):
        r = requests.get("https://cms.whiteoakamc.com/api/scheme-portfolios",
                         params={"pagination[page]": page, "pagination[pageSize]": 100, "sort[0]": "published_date:desc", "populate": "*"},
                         headers={**UA, "Origin": "https://mf.whiteoakamc.com", "Referer": "https://mf.whiteoakamc.com/"}, timeout=60)
        data = r.json().get("data", []) if r.ok else []
        for d in data:
            a = d.get("attributes", {})
            name = (a.get("doc_name") or "").lower()
            if a.get("period") != "Monthly" or str(y) not in name or (full not in name and abbr not in name) or _SKIP.search(a.get("scheme_name", "")):
                continue
            f = (((a.get("doc_file") or {}).get("data") or {}).get("attributes") or {}).get("url")
            if f:
                out.append(f if f.startswith("http") else "https://cms.whiteoakamc.com" + f)
        if not data:
            break
    return out


def dsp(month: str) -> list[str]:
    full, abbr, y = _month(month)
    h = requests.get("https://www.dspim.com/mandatory-disclosures/portfolio-disclosures", headers=UA, timeout=60).text
    out = []
    for href, text in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', h, re.S):
        t = re.sub(r"<[^>]+>|\s+", " ", text).strip().lower()
        if t.startswith("portfolio details as on") and full in t and str(y) in t:
            out.append(href)
    return out[:1]


def motilal(month: str) -> list[str]:
    """AEM search API behind motilaloswalmf.com/download/month-end-portfolio. The monthly file is titled
    'Scheme Portfolio Details <Month> <YYYY>' (filed under the publishing month, so match on the title)."""
    from urllib.parse import quote
    full, abbr, y = _month(month)
    r = requests.get("https://www.motilaloswalmf.com/content/aem-cloud-dept-backend-motilal-oswal/api/search-documents.json",
                     params={"year": "", "category": "month end portfolio", "month": "", "type": "mf"}, headers=UA, timeout=60)
    out = []
    for d in r.json().get("results", []) if r.ok else []:
        t = (d.get("title") or "").lower()
        if "fortnight" in t or str(y) not in t or not (full in t or re.search(rf"\b{abbr}\b", t)):
            continue
        if "scheme portfolio" in t or "month end portfolio" in t or "monthly portfolio" in t:
            out.append("https://www.motilaloswalmf.com" + quote(d["path"]))
    return out


def pgim(month: str) -> list[str]:
    """pgimindia.com disclosure API: section 'Monthly Portfolio' (SECTION_747960037), one entry per month."""
    from urllib.parse import quote
    full, abbr, y = _month(month)
    r = requests.post("https://www.pgimindia.com/api/v1/brochure/published/disclosure",
                      json={"headerId": 2, "sectionId": "SECTION_747960037", "source": "W", "branchCode": None},
                      headers={**UA, "Referer": "https://www.pgimindia.com/mutual-funds/disclosures/Portfolios/Monthly-Portfolio"}, timeout=60)
    out = []
    for tab in r.json().get("data", []) if r.ok else []:
        for c in tab.get("content", []):
            if str(c.get("year")) == str(y) and str(c.get("month", "")).lower() in (full, abbr) and c.get("pdfPath"):
                u = c["pdfPath"]
                out.append(u.split("/image/")[0] + "/image/" + quote(u.split("/image/")[1]) if "/image/" in u else u)
    return out


AMC_ADAPTERS = {
    "Motilal-Oswal-Mutual-Fund": motilal,
    "PGIM-India-Mutual-Fund": pgim,
    "Invesco-Mutual-Fund": invesco,
    "Mirae-Asset-Mutual-Fund": mirae,
    "WhiteOak-Capital-Mutual-Fund": whiteoak,
    "DSP-Mutual-Fund": dsp,
}
