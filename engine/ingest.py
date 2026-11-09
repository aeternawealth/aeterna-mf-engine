"""Agent 1 - Data ingestion.

Pulls:
  * AMFI NAVAll.txt     -> scheme universe, SEBI category, plan (Direct/Regular), option
  * mfapi.in            -> full daily NAV history per scheme
  * niftyindices.com    -> Total Return Index history for every Nifty index
Everything is cached under data/ so a run can be repeated offline.
"""
from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

import pandas as pd
import requests

from . import config as C


def _session():
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    s = requests.Session()
    s.headers.update(C.HTTP_HEADERS)
    retry = Retry(total=5, connect=5, read=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504],
                  allowed_methods=None)
    s.mount("https://", HTTPAdapter(max_retries=retry, pool_maxsize=16))
    return s


# ---------------------------------------------------------------- universe
def normalise_category(raw: str) -> str | None:
    low = raw.lower()
    if any(k in low for k in C.INDEX_CATEGORY_KEYS):
        return "Index Fund"
    if "hybrid scheme" in low:
        return next((cat for key, cat in C.HYBRID_RULES if key in low), None)
    if "debt scheme" in low or "income/debt oriented" in low:
        sub = low.split(" - ", 1)[-1]
        return next((cat for key, cat in C.DEBT_RULES if key in sub), None)
    if "equity scheme" not in low:
        return None
    for key, cat in C.CATEGORY_RULES:
        if key in low:
            return cat
    return None


def parse_navall(text: str) -> pd.DataFrame:
    rows, raw_cat, amc = [], None, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        if ";" not in line:
            if re.match(r"^(Open Ended|Close Ended|Interval)", line):
                raw_cat = line
            else:
                amc = line
            continue
        parts = line.split(";")
        if len(parts) >= 8:
            code, isin1, isin2, name, plan, option, nav, dt = parts[:8]
        else:  # legacy 6-column format
            code, isin1, isin2, name, nav, dt = parts[:6]
            plan = "Direct Plan" if "direct" in name.lower() else "Regular Plan"
            option = "Growth" if "growth" in name.lower() else "IDCW"
        rows.append(dict(code=int(code), isin=isin1, name=name.strip(), plan=plan.strip(),
                         option=option.strip(), nav=pd.to_numeric(nav, errors="coerce"),
                         nav_date=pd.to_datetime(dt, format="%d-%b-%Y", errors="coerce"),
                         amc=amc, raw_category=raw_cat))
    df = pd.DataFrame(rows)
    df["category"] = df["raw_category"].fillna("").map(normalise_category)
    return df


def build_universe(navall: pd.DataFrame) -> pd.DataFrame:
    """Open-ended equity, equity index and arbitrage funds, Growth option, Direct & Regular."""
    u = navall[navall["category"].notna()].copy()
    u = u[u["raw_category"].str.startswith("Open Ended")]
    is_growth = u["option"].str.contains("growth", case=False) | (
        u["name"].str.contains("growth", case=False) & ~u["option"].str.contains("idcw|dividend", case=False))
    u = u[is_growth]
    u = u[~u["name"].str.contains(r"\bETF\b|fund of fund|FOF|segregated portfolio|bonus|unclaimed|institutional|retail plan", case=False, regex=True)]
    debt_like = u["name"].str.contains(
        r"crisil|\bibx\b|\bsdl\b|gilt|g-sec|gsec|bond|debt|t-bill|liquid|target maturity|\bpsu\b.*\b20\d\d\b|\b20[2-4]\d\b",
        case=False, regex=True)
    u = u[~((u["category"] == "Index Fund") & debt_like)]
    u["plan_type"] = u["plan"].str.contains("direct", case=False).map({True: "Direct", False: "Regular"})
    u["asset_class"] = u["category"].map(C.ASSET_CLASS).fillna("Equity")
    u["tax"] = u["category"].map(C.TAX_CLASS).fillna("equity")
    # pairing key so Direct and Regular of the same scheme sit side by side
    base = (u["name"].str.replace(r"(?i)\b(direct|regular)\s*plan\b", "", regex=True)
            .str.replace(r"(?i)\bgrowth( option| plan)?\b", "", regex=True)
            .str.replace(r"[^A-Za-z0-9&]+", " ", regex=True).str.strip().str.lower())
    u["pair_key"] = u["amc"].str.lower().str.strip() + "|" + base
    # some schemes list two growth lines per plan (e.g. legacy + current); keep the oldest code
    u = u.sort_values("code").drop_duplicates(["pair_key", "plan_type"], keep="first")
    return u.reset_index(drop=True)


def liquid_universe(navall: pd.DataFrame, keys=None) -> pd.DataFrame:
    """Open-ended funds of the given AMFI categories (default: liquid), Growth option, Direct & Regular: yardsticks."""
    keys = keys or [C.LIQUID_CATEGORY_KEY]
    u = navall[navall["raw_category"].fillna("").str.lower().str.contains("|".join(keys))
               & navall["raw_category"].fillna("").str.startswith("Open Ended")].copy()
    growth = u["option"].str.contains("growth", case=False) & ~u["option"].str.contains("idcw|dividend|bonus", case=False)
    u = u[growth & ~u["name"].str.contains(r"\bETF\b|BeES|segregated|unclaimed|institutional|retail", case=False, regex=True)]
    u = u.assign(plan_type=u["plan"].str.contains("direct", case=False).map({True: "Direct", False: "Regular"}))
    return u.reset_index(drop=True)


def liquid_yardstick(navs: dict, liq: pd.DataFrame, as_of=None) -> dict:
    """Median liquid fund, per plan type: cumulated median daily return of every liquid fund with a live NAV."""
    out = {}
    for plan, g in liq.groupby("plan_type"):
        rets = []
        for c in g["code"]:
            d = navs.get(int(c))
            if d is None or len(d) < 250:
                continue
            s = d.set_index("date")["nav"]
            if as_of is not None and (pd.Timestamp(as_of) - s.index[-1]).days > 10:
                continue   # stale: merged or wound up
            rets.append(s)
        if len(rets) >= 5:
            from .metrics import median_series   # business-day calendar: see median_series
            out[plan] = median_series(rets)
    return out


def fetch_navall(s=None) -> str:
    s = s or _session()
    try:
        r = s.get(C.NAVALL_URL, timeout=90)
        r.raise_for_status()
    except Exception:
        cached = C.RAW / "NAVAll.txt"
        if cached.exists():
            print("  NAVAll download failed - using cached copy")
            return cached.read_text(encoding="utf-8")
        raise
    C.RAW.mkdir(parents=True, exist_ok=True)
    (C.RAW / "NAVAll.txt").write_text(r.text, encoding="utf-8")
    return r.text


# ---------------------------------------------------------------- NAV history
def _fetch_one_nav(s, code: int, retries=3):
    for i in range(retries):
        try:
            r = s.get(C.MFAPI_URL.format(code=code), timeout=60)
            r.raise_for_status()
            j = r.json()
            d = pd.DataFrame(j.get("data", []))
            if d.empty:
                return code, None, j.get("meta", {})
            d["date"] = pd.to_datetime(d["date"], format="%d-%m-%Y")
            d["nav"] = pd.to_numeric(d["nav"], errors="coerce")
            d = d[d["nav"] > 0].sort_values("date").drop_duplicates("date")
            return code, d[["date", "nav"]], j.get("meta", {})
        except Exception:
            time.sleep(1.5 * (i + 1))
    return code, None, {}


def fetch_navs(codes, workers=8, log=print) -> dict:
    C.NAV_DIR.mkdir(parents=True, exist_ok=True)
    s = _session()
    out, failed = {}, []
    with ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(_fetch_one_nav, s, int(c)) for c in codes]
        for n, f in enumerate(as_completed(futs), 1):
            code, d, _meta = f.result()
            if d is None:
                failed.append(code)
                continue
            d.to_csv(C.NAV_DIR / f"{code}.csv", index=False)
            out[code] = d
            if n % 100 == 0:
                log(f"  NAV {n}/{len(futs)}")
    if failed:
        log(f"  NAV fetch failed for {len(failed)} schemes: {failed[:20]}")
    return out


def top_up_from_navall(navs: dict, universe: pd.DataFrame, log=print) -> int:
    """mfapi.in can lag AMFI by a day for some schemes. AMFI's NAVAll (already downloaded for the universe)
    carries each scheme's latest official NAV: append it when it is newer than the last mfapi date."""
    n = 0
    for code, nav, dt in universe[["code", "nav", "nav_date"]].itertuples(index=False):
        d = navs.get(int(code))
        if d is None or d.empty or pd.isna(dt) or not (nav and nav > 0):
            continue
        if pd.Timestamp(dt) > pd.Timestamp(d["date"].max()):
            d = pd.concat([d, pd.DataFrame({"date": [pd.Timestamp(dt)], "nav": [float(nav)]})], ignore_index=True)
            navs[int(code)] = d
            try:
                d.to_csv(C.NAV_DIR / f"{int(code)}.csv", index=False)
            except OSError:
                pass
            n += 1
    if n:
        log(f"  {n} schemes topped up with AMFI's newer NAV (mfapi was a day behind)")
    return n


def load_cached_navs(codes) -> dict:
    out = {}
    for c in codes:
        p = C.NAV_DIR / f"{int(c)}.csv"
        if p.exists():
            out[int(c)] = pd.read_csv(p, parse_dates=["date"])
    return out


# ---------------------------------------------------------------- TRI
def _tri_post(s, url, payload):
    r = s.post(url, data=json.dumps(payload), timeout=90, headers={
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://www.niftyindices.com",
        "Referer": "https://www.niftyindices.com/reports/historical-data",
        "X-Requested-With": "XMLHttpRequest"})
    r.raise_for_status()
    return r.text


def list_indices(s) -> list[tuple[str, str]]:
    out = []
    for g in C.TRI_GROUPS:
        txt = _tri_post(s, C.TRI_LIST_URL, {"cinfo": {"indexgroup": "Historical Index Data", "indextype": g}})
        out += [(g, x["indextype"]) for x in json.loads(txt) if x.get("indextype")]
    return out


def fetch_tri(s, name: str) -> pd.Series | None:
    end = date.today().strftime("%d-%b-%Y")
    ci = {"name": name, "startDate": C.HISTORY_START, "endDate": end, "indexName": name}
    txt = _tri_post(s, C.TRI_URL, {"cinfo": json.dumps(ci).replace('"', "'")})
    arr = json.loads(txt)
    if not arr:
        return None
    d = pd.DataFrame(arr)
    d["date"] = pd.to_datetime(d["Date"], format="%d %b %Y", errors="coerce")
    d["tri"] = pd.to_numeric(d["TotalReturnsIndex"].astype(str).str.replace(",", ""), errors="coerce")
    d = d.dropna(subset=["date", "tri"]).sort_values("date").drop_duplicates("date")
    return d.set_index("date")["tri"]


def _tri_via_browser(log=print) -> dict:
    """Fallback when niftyindices blocks plain HTTP clients: drive a real (headless) browser
    on this PC and call the same endpoints the website's own page uses."""
    from playwright.sync_api import sync_playwright
    js = """async ([groups, start, end]) => {
      const post = (u, b) => fetch(u, {method:'POST', headers:{'Content-Type':'application/json; charset=utf-8'}, body: JSON.stringify(b)}).then(r => r.text());
      let names = [];
      for (const g of groups) { const a = JSON.parse(await post('/BackPage/gethistoricaltypeindexdata', {cinfo:{indexgroup:'Historical Index Data', indextype:g}})); names.push(...a.map(x => [g, x.indextype])); }
      const out = {};
      for (const [g, n] of names) {
        try { const ci = JSON.stringify({name:n, startDate:start, endDate:end, indexName:n}).replace(/"/g, "'");
              const d = JSON.parse(await post('/BackPage/getTotalReturnIndexString', {cinfo: ci}));
              if (d.length) out[n] = d.map(x => [x.Date, x.TotalReturnsIndex]); } catch (e) {}
      }
      return out; }"""
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page()
        pg.goto("https://www.niftyindices.com/reports/historical-data", timeout=90000)
        pg.wait_for_timeout(3000)
        res = pg.evaluate(js, [C.TRI_GROUPS, C.HISTORY_START, date.today().strftime("%d-%b-%Y")])
        b.close()
    series = {}
    for n, rows in res.items():
        d = pd.DataFrame(rows, columns=["Date", "tri"])
        d["date"] = pd.to_datetime(d["Date"], format="%d %b %Y", errors="coerce")
        d["tri"] = pd.to_numeric(d["tri"].astype(str).str.replace(",", ""), errors="coerce")
        d = d.dropna().sort_values("date").drop_duplicates("date")
        if len(d) > 50:
            series[n] = d.set_index("date")["tri"]
    log(f"  TRI via browser: {len(series)} indices")
    return series


def fetch_all_tri(log=print, workers=4) -> pd.DataFrame:
    try:
        return _fetch_all_tri_http(log, workers)
    except Exception as e:
        log(f"  TRI plain HTTP failed ({type(e).__name__}); using headless browser")
        tri = pd.DataFrame(_tri_via_browser(log)).sort_index()
        C.RAW.mkdir(parents=True, exist_ok=True)
        tri.to_csv(C.RAW / "tri.csv")
        return tri


def _fetch_all_tri_http(log=print, workers=4) -> pd.DataFrame:
    s = _session()
    s.get("https://www.niftyindices.com/reports/historical-data", timeout=60)  # cookies
    names = list_indices(s)
    series, groups = {}, {}
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(fetch_tri, s, n): (g, n) for g, n in names}
        for f in as_completed(futs):
            g, n = futs[f]
            try:
                sr = f.result()
            except Exception:
                sr = None
            if sr is not None and len(sr) > 50:
                series[n] = sr
                groups[n] = g
    if len(series) < 20:
        raise RuntimeError("too few TRI series via HTTP")
    tri = pd.DataFrame(series).sort_index()
    C.RAW.mkdir(parents=True, exist_ok=True)
    tri.to_csv(C.RAW / "tri.csv")
    pd.Series(groups).to_csv(C.RAW / "tri_groups.csv", header=["group"])
    log(f"  TRI: {tri.shape[1]} indices, {tri.index.min().date()} -> {tri.index.max().date()}")
    return tri


def load_cached_tri() -> pd.DataFrame:
    return pd.read_csv(C.RAW / "tri.csv", index_col=0, parse_dates=True)


# ---------------------------------------------------------------- manual / optional inputs
def load_manual(name: str) -> pd.DataFrame | None:
    """Optional CSVs in data/manual/: ter.csv (code,ter), aum.csv (code or pair_key,aum_cr), flags.csv (code,flag,note)."""
    p = C.MANUAL / f"{name}.csv"
    return pd.read_csv(p) if p.exists() else None
