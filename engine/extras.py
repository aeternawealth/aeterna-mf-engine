"""Agent 1b - AMFI extras via `amfipy`: TER (by ISIN), month-end AUM (quarterly average as fallback), market-cap list.
Writes data/manual/ter.csv, aum.csv and amfi_mcap.xlsx. Each step fails soft.
"""
from __future__ import annotations

import re
from datetime import date

import pandas as pd

from . import config as C


def _fy(d: date) -> str:
    y = d.year if d.month >= 4 else d.year - 1
    return f"{y}-{y + 1}"


def _nm(s: str) -> str:
    s = re.sub(r"(?i)\b(direct|regular)\s*(plan)?\b|\bgrowth( option| plan)?\b", "", str(s))
    return re.sub(r"[^a-z0-9&]+", "", s.lower())


def fetch_ter(universe: pd.DataFrame, log=print):
    """AMFI TER Excel (all schemes, all TER revisions) -> latest Regular & Direct total TER per scheme."""
    import difflib, io, httpx
    frames = []
    for per in (pd.Period(date.today(), "M") - 1, pd.Period(date.today(), "M")):   # last full month + current
        r = httpx.get("https://www.amfiindia.com/api/populate-te-rdata-revised",
                      params={"MF_ID": "All", "Month": per.strftime("%m-%Y"), "strCat": "-1", "strType": "-1", "excel": "true"},
                      headers={**C.HTTP_HEADERS, "Referer": "https://www.amfiindia.com/ter-of-mf-schemes"},
                      timeout=180, follow_redirects=True)
        if r.status_code == 200 and len(r.content) > 1000:
            frames.append(pd.read_excel(io.BytesIO(r.content)))
    x = pd.concat(frames, ignore_index=True)
    x.columns = [str(c).strip() for c in x.columns]
    reg = next(c for c in x.columns if c.startswith("Regular") and "Total TER" in c)
    dirc = next(c for c in x.columns if c.startswith("Direct") and "Total TER" in c)
    # SEBI's 2026 format splits Total TER into the fund's fee (Base Expense Ratio) + brokerage + transaction cost
    # + statutory levies. For arbitrage funds the levies (mostly STT on their trades) dwarf the fee.
    reg_b = next((c for c in x.columns if c.startswith("Regular") and "Base Expense" in c), None)
    dir_b = next((c for c in x.columns if c.startswith("Direct") and "Base Expense" in c), None)
    x["TER Date"] = pd.to_datetime(x["TER Date"], errors="coerce")
    x = x.dropna(subset=[reg, dirc], how="all").sort_values("TER Date").groupby("Scheme Name").tail(1)
    x["k"] = x["Scheme Name"].map(_nm)
    x["ter_date"] = x["TER Date"].dt.strftime("%Y-%m-%d")
    ter = x.set_index("k")[[reg, dirc, "ter_date"] + [c for c in (reg_b, dir_b) if c]]
    ter = ter[~ter.index.duplicated(keep="last")]
    u = universe.copy()
    u["k"] = u["name"].map(_nm)
    keys = list(ter.index)
    miss = [k for k in u["k"].unique() if k not in ter.index]
    alias = {k: (difflib.get_close_matches(k, keys, 1, 0.92) or [None])[0] for k in miss}
    u["k2"] = u["k"].map(lambda k: k if k in ter.index else alias.get(k))
    def pick(row):
        if not isinstance(row.k2, str):
            return None
        return ter.at[row.k2, reg if row.plan_type == "Regular" else dirc]
    u["ter"] = pd.to_numeric(u.apply(pick, axis=1), errors="coerce")
    u.loc[u["ter"] > 5, "ter"] = None   # data-entry errors
    if reg_b and dir_b:
        u["ter_base"] = pd.to_numeric(u.apply(lambda r: ter.at[r.k2, reg_b if r.plan_type == "Regular" else dir_b]
                                              if isinstance(r.k2, str) else None, axis=1), errors="coerce")
        u.loc[u["ter_base"] > u["ter"], "ter_base"] = None
    u["ter_date"] = u["k2"].map(lambda k: ter.at[k, "ter_date"] if isinstance(k, str) else None)
    out = u.dropna(subset=["ter"])[["code", "ter", "ter_date"] + (["ter_base"] if "ter_base" in u else [])]
    C.MANUAL.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.MANUAL / "ter.csv", index=False)
    log(f"  TER: {len(out)}/{len(u)} plans matched")
    return out


def fetch_aum_qavg(universe: pd.DataFrame, log=print, navall: pd.DataFrame | None = None):
    """AMFI quarterly average AUM per plan (AMFI_Code, in Rs lakh) -> scheme AUM in Rs crore (all plans/options).
    Returns (DataFrame pair_key, aum_cr; period label). Fallback for fetch_aum."""
    import httpx
    h = {**C.HTTP_HEADERS, "Referer": "https://www.amfiindia.com/aum-data/average-aum"}
    url = "https://www.amfiindia.com/api/average-aum-schemewise"
    rows, label = [], ""
    for fy in (1, 2):
        meta = httpx.get(url, params={"strType": "Categorywise", "fyId": fy}, headers=h, timeout=120).json()
        fy_label = meta["data"].get("financial_year", "")
        for p in sorted(meta["data"]["periods"], key=lambda p: p["id"]):
            for attempt in range(3):
                try:
                    r = httpx.get(url, params={"strType": "Categorywise", "fyId": fy, "periodId": p["id"], "MF_ID": "0" if attempt % 2 == 0 else ""},
                                  headers=h, timeout=180)
                    data = r.json().get("data") if r.status_code == 200 else None
                    break
                except Exception:
                    data = None
            for cat in data or []:
                for sch in cat.get("schemes", []):
                    v = sch.get("AverageAumForTheMonth") or {}
                    amt = sum(x for x in v.values() if isinstance(x, (int, float)))
                    rows.append((sch.get("AMFI_Code"), amt))
            if rows:
                label = p["period"]
                break
        if rows:
            break
    if not rows:
        log("  AUM: no data")
        return None
    aum = pd.DataFrame(rows, columns=["code", "aum_lakh"]).dropna()
    aum["code"] = aum["code"].astype(int)
    if navall is not None:   # map every plan/option (incl. IDCW) to its scheme pair_key
        nv = navall.copy()
        base = (nv["name"].str.replace(r"(?i)\b(direct|regular)\s*plan\b", "", regex=True)
                .str.replace(r"(?i)\bgrowth( option| plan)?\b", "", regex=True)
                .str.replace(r"[^A-Za-z0-9&]+", " ", regex=True).str.strip().str.lower())
        nv["pair_key"] = nv["amc"].str.lower().str.strip() + "|" + base
        aum = aum.merge(nv[["code", "pair_key"]], on="code", how="inner")
    else:
        aum = aum.merge(universe[["code", "pair_key"]], on="code", how="inner")
    out = (aum.groupby("pair_key")["aum_lakh"].sum() / 100).rename("aum_cr").reset_index()
    out = out[out.pair_key.isin(universe.pair_key)]
    log(f"  Quarterly average AUM ({label}): {len(out)} schemes")
    return out, label


# AMFI fund-performance tool (run for AMFI by CRISIL): scheme-level daily AUM, the figure fund factsheets,
# Value Research and Groww quote. One call per SEBI sub-category covers every fund house.
_FP = "https://www.amfiindia.com/gateway/pollingsebi/api/amfi/"
_FP_SUBS = ((1, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 44, 45)), (3, (33,)), (5, (38,)))   # equity; hybrid: arbitrage; index funds & ETFs


def _aum_key(s: str) -> str:
    s = re.sub(r"\([^)]*\)?", " ", str(s).lower())          # "(Formerly ...)", "(MOFSP500)", unclosed "(Formerly ..."
    s = re.sub(r"\b(erstwhile|formerly)\b.*", " ", s)
    s = s.replace("&", " and ").replace("zerodha case", "zerodha")
    s = re.sub(r"\b(direct|regular|plan|growth|option)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s).replace("fund", "").replace("scheme", "")


def fetch_aum_monthend(universe: pd.DataFrame, log=print, today: date | None = None):
    """Month-end AUM (Rs crore, all plans) for the last month end AMFI has data for. Returns (pair_key, aum_cr), date."""
    import difflib
    import httpx
    # this gateway rejects (406) a User-Agent carrying our engine tag, so send a plain browser one
    h = {**C.HTTP_HEADERS, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://www.amfiindia.com/otherdata/fund-performance"}
    d = pd.Timestamp(today or date.today()).replace(day=1) - pd.Timedelta(days=1)   # last day of the previous month
    for _ in range(6):   # walk back over a month-end weekend / holiday
        rows = []
        for cat, subs in _FP_SUBS:
            for sc in subs:
                body = {"maturityType": 1, "category": cat, "subCategory": sc, "mfid": 0, "reportDate": d.strftime("%d-%b-%Y")}
                for attempt in range(3):
                    try:
                        data = httpx.post(_FP + "fundperformance", json=body, headers=h, timeout=120).json().get("data") or []
                        break
                    except Exception:
                        data = []
                rows += [(x.get("schemeName"), x.get("dailyAUM"), x.get("navDate")) for x in data]
        rows = [r for r in rows if r[2] == d.strftime("%d-%b-%Y")]
        if len(rows) > 500:
            break
        d -= pd.Timedelta(days=1)
    else:
        log("  Month-end AUM: no data")
        return None, None
    a = pd.DataFrame(rows, columns=["name", "aum_cr", "date"])
    a["aum_cr"] = pd.to_numeric(a["aum_cr"], errors="coerce")
    a["k"] = a["name"].map(_aum_key)
    a = a.dropna(subset=["aum_cr"]).drop_duplicates("k", keep=False).set_index("k")
    sch = universe.drop_duplicates("pair_key")[["pair_key", "name"]].copy()
    sch["k"] = sch["name"].map(_aum_key)
    keys = list(a.index)

    def find(k):
        if k in a.index:
            return k
        digits = re.findall(r"\d+", k)   # "nifty 50" vs "nifty 500" are different funds: numbers must agree exactly
        c = [x for x in difflib.get_close_matches(k, keys, n=3, cutoff=0.94) if re.findall(r"\d+", x) == digits][:2]   # spelling slips ("Heathcare")
        return c[0] if len(c) == 1 or (len(c) == 2 and difflib.SequenceMatcher(None, k, c[1]).ratio() < 0.94) else None
    sch["hit"] = sch["k"].map(find)
    sch = sch.dropna(subset=["hit"])
    sch = sch[~sch["hit"].duplicated(keep=False)]   # one AMFI scheme must not feed two of ours
    sch["aum_cr"] = sch["hit"].map(a["aum_cr"])
    log(f"  Month-end AUM ({d:%d %b %Y}): {len(sch)}/{universe.pair_key.nunique()} schemes")
    return sch[["pair_key", "aum_cr"]], d


def fetch_aum(universe: pd.DataFrame, log=print, navall: pd.DataFrame | None = None, quarterly: bool = True):
    """data/manual/aum.csv: month-end AUM from AMFI where available, else AMFI's quarterly average, labelled per fund
    (aum_asof). quarterly=False (daily run) keeps the last quarterly figures already on file for the fallback."""
    me, d = fetch_aum_monthend(universe, log)
    if me is None or len(me) < 0.8 * universe.pair_key.nunique():
        log("  Month-end AUM: too few matches, keeping the previous aum.csv")
        return None
    me = me.assign(aum_asof=f"{d.day} {d:%b %Y}")
    qa, qlabel = (fetch_aum_qavg(universe, log, navall) if quarterly else (None, None))
    if qa is None:   # reuse the quarterly fallback from the last file
        prev = (pd.read_csv(C.MANUAL / "aum.csv") if (C.MANUAL / "aum.csv").exists() else pd.DataFrame())
        if "aum_asof" in prev.columns:
            qa = prev[prev["aum_asof"].astype(str).str.contains("average")][["pair_key", "aum_cr", "aum_asof"]]
        elif len(prev) and (C.MANUAL / "aum.period.txt").exists():
            qa = prev[["pair_key", "aum_cr"]].assign(aum_asof=_qavg_label((C.MANUAL / "aum.period.txt").read_text()))
    elif qlabel:
        qa = qa.assign(aum_asof=_qavg_label(qlabel))
    out = me
    if qa is not None and len(qa):
        out = pd.concat([me, qa[~qa.pair_key.isin(me.pair_key)]], ignore_index=True)
    # sanity: a month-end figure wildly off the quarterly average is more likely a mismatch than a real move
    if qa is not None and len(qa):
        chk = me.merge(qa[["pair_key", "aum_cr"]], on="pair_key", suffixes=("", "_q"))
        odd = chk[(chk.aum_cr_q > 50) & ((chk.aum_cr / chk.aum_cr_q > 4) | (chk.aum_cr / chk.aum_cr_q < 0.25))]
        for r in odd.itertuples():
            log(f"  AUM check: {r.pair_key} month-end {r.aum_cr:,.0f} vs quarterly avg {r.aum_cr_q:,.0f} cr")
    out.to_csv(C.MANUAL / "aum.csv", index=False)
    (C.MANUAL / "aum.period.txt").write_text(f"{d.day} {d:%b %Y} (month-end, AMFI)")
    log(f"  AUM: {len(me)} month-end, {len(out) - len(me)} quarterly-average fallback")
    return out


def _qavg_label(period: str) -> str:
    """'July - September 2026 (quarterly average, AMFI)' -> 'Jul–Sep 2026 average'."""
    p = re.sub(r"\s*\(.*\)\s*$", "", str(period))
    return re.sub(r"(\w{3})\w* - (\w{3})\w* (\d{4})", r"\1–\2 \3", p) + " average"


def fetch_mcap_list(log=print):
    from amfipy.research import ResearchClient
    r = ResearchClient()
    flat = [x for x in r.categorisation_of_stocks_flat() if x.get("excelUrl")]
    if not flat:
        return None
    latest = flat[-1]
    dest = C.MANUAL / "amfi_mcap.xlsx"
    tag = C.MANUAL / "amfi_mcap.period.txt"
    label = f"{latest['year']} {latest['period']}"
    if dest.exists() and tag.exists() and tag.read_text() == label:
        return dest
    dest.write_bytes(r.download_categorisation_file(latest["excelUrl"]))
    tag.write_text(label)
    log(f"  Market-cap list: {label}")
    return dest


def run_all(universe, log=print, navall=None):
    for fn in (lambda: fetch_ter(universe, log), lambda: fetch_aum(universe, log, navall), lambda: fetch_mcap_list(log)):
        try:
            fn()
        except Exception as e:
            log(f"  extras step failed: {type(e).__name__}: {str(e)[:160]}")
