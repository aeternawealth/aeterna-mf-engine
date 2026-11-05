"""Agent 1b - AMFI extras via `amfipy`: TER (by ISIN), quarterly average AUM, market-cap list.
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
    x["TER Date"] = pd.to_datetime(x["TER Date"], errors="coerce")
    x = x.dropna(subset=[reg, dirc], how="all").sort_values("TER Date").groupby("Scheme Name").tail(1)
    x["k"] = x["Scheme Name"].map(_nm)
    x["ter_date"] = x["TER Date"].dt.strftime("%Y-%m-%d")
    ter = x.set_index("k")[[reg, dirc, "ter_date"]]
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
    u["ter_date"] = u["k2"].map(lambda k: ter.at[k, "ter_date"] if isinstance(k, str) else None)
    out = u.dropna(subset=["ter"])[["code", "ter", "ter_date"]]
    C.MANUAL.mkdir(parents=True, exist_ok=True)
    out.to_csv(C.MANUAL / "ter.csv", index=False)
    log(f"  TER: {len(out)}/{len(u)} plans matched")
    return out


def fetch_aum(universe: pd.DataFrame, log=print, navall: pd.DataFrame | None = None):
    """AMFI quarterly average AUM per plan (AMFI_Code, in Rs lakh) -> scheme AUM in Rs crore (all plans/options)."""
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
    out.to_csv(C.MANUAL / "aum.csv", index=False)
    (C.MANUAL / "aum.period.txt").write_text(f"{label} (quarterly average, AMFI)")
    log(f"  AUM ({label}): {len(out)} schemes")
    return out


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
