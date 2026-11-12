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


def groww(month: str) -> list[str]:
    """growwmf.in compliance-docs tree API: Statutory Disclosure/Portfolio/<FY>/'Monthly Portfolio- Sep 30 2026.xlsx'."""
    full, abbr, y = _month(month)
    r = requests.get("https://mapi.growwmf.in/v1/api/mf-data/v1/files", headers=UA, timeout=60)
    out = []

    def walk(node, path):
        for f in node.get("files", []):
            n = (f.get("name") or "").lower()
            if "portfolio" in path.lower() and n.startswith("monthly portfolio") and str(y) in n \
                    and (full in n or re.search(rf"\b{abbr}\b", n)) and f.get("publicUrl"):
                out.append(f["publicUrl"])
        for sub in node.get("folders", []):
            walk(sub, path + "/" + (sub.get("name") or ""))
    if r.ok:
        walk(r.json().get("data", {}), "")
    return out


def canara(month: str) -> list[str]:
    """canararobeco.com scheme-monthly-portfolio listing: one file per scheme, ~10 per page (&pagination=N)."""
    from urllib.parse import urljoin
    full, abbr, y = _month(month)
    base = "https://www.canararobeco.com/documents/statutory-disclosures/scheme-dashboard/scheme-monthly-portfolio/"
    out, seen_pages = [], set()
    for page in range(1, 16):
        r = requests.get(base, params={"filteryear": y, "filtermonth": f"{pd.Period(month).month:02d}", "pagination": page},
                         headers=UA, timeout=60)
        if not r.ok:
            break
        links = [urljoin(base, l) for l in re.findall(r'href="([^"]+\.xlsx?)"', r.text, re.I)]
        new = [l for l in links if l not in out]
        key = tuple(sorted(links))
        if not new or key in seen_pages:   # past the last page
            break
        seen_pages.add(key)
        out += [l for l in new if full in l.lower() and str(y) in l and not _SKIP.search(l.rsplit("/", 1)[-1].replace("-", " "))]
    return list(dict.fromkeys(out))


# HSBC: every scheme's monthly portfolio sits at a fixed address,
# .../portfolios/document-<DDMMYYYY>/hsbc-<scheme>-<DD>-<mon>-<YYYY>.xlsx (probe of 12 Nov 2026). The scheme list comes
# from the information library when it loads (it often times out from cloud servers), otherwise from this list.
HSBC_SCHEMES = ['aggressive-hybrid-active-fof', 'aggressive-hybrid-fund', 'arbitrage-fund', 'asia-pacific-ex-japan-div-yieldfund', 'balanced-advantage-fund', 'banking-and-psu-debt-fund', 'brazil-fund', 'business-cycles-fund', 'conservative-hybrid-fund', 'consumption-fund', 'corporate-bond-fund', 'credit-risk-fund', 'crisil-ibx-gilt-june-2027-index-fund', 'crl-ibx-50-50-sdl-apr-2028-index-fund', 'dynamic-term-fund', 'elss-tax-saver-fund', 'equity-savings-fund', 'financial-services-fund', 'flexi-cap-fund', 'focused-fund', 'gilt-fund', 'global-emerging-markets-fund', 'gold-etf', 'gold-etf-fof', 'income-plus-arbitrage-active-fof', 'india-export-opportunities-fund', 'infrastructure-fund', 'large-cap-fund', 'large-mid-cap-fund', 'liquid-fund', 'medium-term-fund', 'medium-to-long-term-fund', 'midcap-fund', 'money-market-fund', 'multi-asset-active-fof', 'multi-asset-allocation-fund', 'multi-cap-fund', 'nifty-50-index-fund', 'nifty-next-50-index-fund', 'overnight-fund', 'short-term-fund', 'small-cap-fund', 'ultra-short-term-fund', 'ultra-short-to-short-term-fund', 'value-fund']


def _month_end_days(month: str) -> list:
    """the calendar month-end and, when that falls on a weekend, the last business day before it"""
    end = pd.Period(month).end_time.normalize()
    days = [end]
    if end.weekday() >= 5:
        days.append(end - pd.offsets.BDay(1))
    return days


def hsbc(month: str) -> list[str]:
    base = "https://www.assetmanagement.hsbc.co.in/-/media/files/attachments/india/mutual-funds/portfolios/"
    slugs = set(HSBC_SCHEMES)
    try:
        r = requests.get("https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources/information-library", headers=UA, timeout=40)
        slugs |= set(re.findall(r"portfolios/document-\d{8}/hsbc-([a-z0-9-]+?)-\d{2}-[a-z]{3}-\d{4}\.xlsx", r.text, re.I))
    except Exception:
        pass
    out = []
    for d in _month_end_days(month):
        folder = "document-" + d.strftime("%d%m%Y") + "/"
        stamp = (d.strftime("%d") + "-" + d.strftime("%b") + "-" + d.strftime("%Y")).lower()
        out += [base + folder + "hsbc-" + s + "-" + stamp + ".xlsx" for s in sorted(slugs) if not _SKIP.search(s.replace("-", " "))]
    return out


def taurus(month: str) -> list[str]:
    """taurusmutualfund.com/monthly-portfolio: a Drupal view filtered by year and month ids, read from its own dropdowns.
    File names carry the month, e.g. Taurus_Mid_Cap_Fund_Monthly_Portfolio_Report_Performance_September_2026.xlsx;
    links can start with a space."""
    p = pd.Period(month)
    page = "https://taurusmutualfund.com/monthly-portfolio"
    r = requests.get(page, headers=UA, timeout=60)
    if not r.ok:
        return []
    ids = {lab.strip().lower(): v for v, lab in re.findall(r'<option[^>]*value="(\d+)"[^>]*>([^<]+)</option>', r.text)}
    y, mo = ids.get(str(p.year)), ids.get(p.strftime("%B").lower())
    html = r.text
    if y and mo:
        q = requests.get(page, params={"field_monthly_portfolio_target_id": y, "field_month_target_id": mo}, headers=UA, timeout=60)
        html = q.text if q.ok else html
    tag = (p.strftime("%B") + "_" + str(p.year)).lower()
    out = []
    for l in re.findall(r'href="\s*([^"]+?\.(?:xlsx?|zip))\s*"', html, re.I):
        if tag in l.lower():
            out.append(l if l.startswith("http") else "https://taurusmutualfund.com" + ("" if l.startswith("/") else "/") + l)
    return list(dict.fromkeys(out))


def _dbg(amc, label, text):
    """with AETERNA_ADAPTER_DEBUG set (the probe workflow), keep what each step of an adapter received"""
    import os
    d = os.environ.get("AETERNA_ADAPTER_DEBUG")
    if d:
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"adapter_{amc}.txt"), "a", encoding="utf-8") as fh:
            fh.write(f"=== {label}\n{str(text)[:3000]}\n")


def lic(month: str) -> list[str]:
    """licmf.com/downloads/monthly-portfolio: per scheme, category -> scheme list, scheme -> name, (scheme, year) -> months,
    then the files (jQuery posts read from the page on 12 Nov 2026)."""
    p = pd.Period(month)
    base = "https://www.licmf.com"
    s = requests.Session()
    s.headers.update({**UA, "X-Requested-With": "XMLHttpRequest", "Referer": base + "/downloads/monthly-portfolio"})
    try:
        s.get(base + "/downloads/monthly-portfolio", timeout=60)
    except Exception:
        return []
    out = []
    for cat in ("Equity", "Hybrid", "ETFs & Index Funds"):
        r = s.post(base + "/downloads/portfolio-filter-options", data={"fund_category": cat, "filter": "category"}, timeout=60)
        _dbg("lic", f"schemes {cat} {r.status_code}", r.text)
        for code, _name in re.findall(r"""<option[^>]*value=["']([^"']*)["'][^>]*>([^<]+)</option>""", r.text if r.ok else ""):
            if not code.strip():
                continue
            name = s.post(base + "/downloads/portfolio-funds", data={"scheme_code": code}, timeout=60).text.strip()
            months = s.post(base + "/downloads/portfolio-filter-options",
                            data={"year": p.year, "filter": "year", "type": "monthly_portfolio", "scheme_code": code}, timeout=60).text
            _dbg("lic", f"name/months {code}", name + " | " + months)
            mv = None
            for v, label in re.findall(r"""<option[^>]*value=["']([^"']*)["'][^>]*>([^<]+)</option>""", months):
                if label.strip().lower() in (p.strftime("%B").lower(), p.strftime("%b").lower()) or v.strip() in (str(p.month), f"{p.month:02d}"):
                    mv = v
                    break
            if not mv:
                continue
            files = s.post(base + "/downloads/portfolio-files",
                           data={"scheme_code": code, "fund_name": name, "type": "monthly_portfolio", "month": mv, "year": p.year}, timeout=60).text
            _dbg("lic", f"files {code}", files)
            for l in re.findall(r"""href=["']\s*([^"']+?\.(?:xlsx?|zip))\s*["']""", files, re.I):
                out.append(l if l.startswith("http") else base + ("" if l.startswith("/") else "/") + l)
    return list(dict.fromkeys(out))


def sundaram(month: str) -> list[str]:
    """sundarammutual.com/Monthly-Fortnightly-Adhoc-Portfolios: an Ajax.NET method GetCategory('Monthly') returns the list.
    The handler's address (App_Web_<hash>.ashx) changes when the site is redeployed, so it is read from the page."""
    p = pd.Period(month)
    base = "https://www.sundarammutual.com"
    s = requests.Session()
    s.headers.update(UA)
    page = s.get(base + "/Monthly-Fortnightly-Adhoc-Portfolios", timeout=60).text
    m = re.search(r'(/ajax/Modules_Disclosure_Monthly_Fortnightly_Adhoc_Portfolios,[^"\']+?\.ashx)', page)
    _dbg("sundaram", "handler", m.group(1) if m else "not found; page bytes %d" % len(page))
    if not m:
        return []
    # the handler serves its own proxy script: read the parameter name GetCategory expects, then call it in the
    # Ajax.NET wire format (one "name=value" per line), falling back to the AjaxPro JSON format
    js = s.get(base + m.group(1), timeout=60).text
    _dbg("sundaram", "proxy", js)
    pm = re.search(r'GetCategory\s*[:=]\s*function\s*\(\s*([A-Za-z_]\w*)', js) or re.search(r'"GetCategory"\s*,\s*\{\s*"([^"]+)"', js)
    pname = pm.group(1) if pm else "Category"
    hdr = {"Referer": base + "/Monthly-Fortnightly-Adhoc-Portfolios"}
    r = s.post(base + m.group(1) + "?_method=GetCategory&_session=no", data=f"{pname}=Monthly\r\n",
               headers={**hdr, "Content-Type": "text/plain; charset=utf-8"}, timeout=60)
    if "ajax_error" in r.text or not r.ok:
        r = s.post(base + m.group(1), data='{"%s":"Monthly"}' % pname,
                   headers={**hdr, "Content-Type": "text/plain; charset=utf-8", "X-AjaxPro-Method": "GetCategory"}, timeout=60)
    text = r.text.encode().decode("unicode_escape", errors="ignore") if r.ok else ""
    _dbg("sundaram", f"GetCategory {r.status_code}", r.text)
    toks = (p.strftime("%B").lower(), p.strftime("%b").lower())
    out = []
    for l in re.findall(r'href=\\?["\']([^"\'\\]+?\.(?:xlsx?|zip))', text, re.I):
        low = l.lower()
        if str(p.year) in low and any(t in low for t in toks):
            out.append(l if l.startswith("http") else base + ("" if l.startswith("/") else "/") + l)
    return list(dict.fromkeys(out))


AMC_ADAPTERS = {
    "LIC-Mutual-Fund": lic,
    "Sundaram-Mutual-Fund": sundaram,
    "HSBC-Mutual-Fund": hsbc,
    "Taurus-Mutual-Fund": taurus,
    "Canara-Robeco-Mutual-Fund": canara,
    "Groww-Mutual-Fund": groww,
    "Motilal-Oswal-Mutual-Fund": motilal,
    "PGIM-India-Mutual-Fund": pgim,
    "Invesco-Mutual-Fund": invesco,
    "Mirae-Asset-Mutual-Fund": mirae,
    "WhiteOak-Capital-Mutual-Fund": whiteoak,
    "DSP-Mutual-Fund": dsp,
}
