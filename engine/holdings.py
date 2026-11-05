"""Agent 9 - Holdings analysis.

Input : AMC monthly portfolio disclosures (SEBI format Excel, usually one sheet per scheme)
        dropped in data/holdings/<YYYY-MM>/  (any file name, .xlsx/.xls)
        + AMFI half-yearly market-cap list (data/manual/amfi_mcap.xlsx) for Large/Mid/Small tagging.
Output: one row per scheme portfolio (pair_key, shared by Direct & Regular) with
        concentration, market-cap mix, mandate check, active share, cash, turnover, liquidity.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C

HOLD_DIR = C.DATA / "holdings"

# SEBI categorisation mandates (Oct-2017 circular), on % of total assets
MANDATES = {
    "Large Cap": [("large", ">=", 80)],
    "Mid Cap": [("mid", ">=", 65)],
    "Small Cap": [("small", ">=", 65)],
    "Large & Mid Cap": [("large", ">=", 35), ("mid", ">=", 35)],
    "Multi Cap": [("large", ">=", 25), ("mid", ">=", 25), ("small", ">=", 25)],
    "Flexi Cap": [("equity", ">=", 65)],
    "Focused": [("equity", ">=", 65), ("n_stocks", "<=", 30)],
    "ELSS": [("equity", ">=", 80)],
    "Value": [("equity", ">=", 65)],
    "Contra": [("equity", ">=", 65)],
    "Dividend Yield": [("equity", ">=", 65)],
    "Sectoral/Thematic": [("equity", ">=", 80)],
}


# ----------------------------------------------------------- parsing
def _is_equity_isin(isin: str) -> bool:
    if isinstance(isin, str) and len(isin) == 12 and not isin.startswith("IN"):
        return True    # foreign security held by an international fund (stock or overseas fund unit)
    # Indian ISIN: IN + issuer-type(E) + 4 company + 2 security type ('01' = equity shares)
    return isinstance(isin, str) and len(isin) == 12 and isin.startswith("INE") and isin[7:9] == "01"


def _find_header(raw: pd.DataFrame):
    for i in range(min(len(raw), 40)):
        vals = [re.sub(r"\s+", " ", str(v)).strip().lower() for v in raw.iloc[i].tolist()]
        if any("isin" in v for v in vals) and any(re.search(r"nav|net assets|aum", v) for v in vals):
            return i, vals
    return None, None


def _col(vals, *pats):
    for p in pats:
        for j, v in enumerate(vals):
            if re.search(p, v):
                return j
    return None


_JUNK = re.compile(r"portfolio statement|riskomet|product label|suitable for|registered office|toll free|"
                   r"^name of (the )?mutual fund|inception|^nan$|^nat$|back to index|^scheme name\s*:?$", re.I)


def _clean_title(t: str) -> str:
    t = re.sub(r"\s+", " ", str(t)).strip()
    m = re.search(r"(?i)portfolio (statement )?of (.+?)( as on| for the|$).*", t)
    if m:
        t = m.group(2)
    t = re.sub(r"(?i)^(scheme name|name of the scheme)\s*[:\-]\s*", "", t)
    t = re.split(r"(?i)\s*[\(\-–]\s*(an open|open[- ]ended|formerly|erstwhile)", t)[0]
    return t.strip(" -:")


def _title_candidates(top: pd.DataFrame, sheet_name: str) -> list[str]:
    c = []
    for v in top.values.flatten():
        s = str(v).strip()
        if re.search(r"(?i)portfolio (statement )?of ", s):
            s = _clean_title(s)
        if len(s) < 4 or len(s) > 260 or _JUNK.search(s) or " " not in s:
            continue
        s2 = _clean_title(s)
        if s2 and not re.fullmatch(r"(?i)[a-z0-9 &.]*mutual fund( \(live schemes\))?", s2):
            c.append(s2)
    return c + [sheet_name]


def parse_sheet(raw: pd.DataFrame, sheet_name: str):
    h, vals = _find_header(raw)
    if h is None:
        return None
    ci = _col(vals, r"\bisin\b")
    cw = _col(vals, r"% ?(to|of) ?(net ?assets|nav|aum)", r"%.*(nav|aum|net assets)", r"net assets")
    cn = _col(vals, r"name of (the )?instrument", r"instrument", r"name of (the )?(security|issuer|company)", r"^name")
    cs = _col(vals, r"industry", r"sector", r"rating")
    if ci is None or cw is None:
        return None
    title = _title_candidates(raw.iloc[:h], sheet_name)
    body = raw.iloc[h + 1:]
    df = pd.DataFrame({
        "isin": body.iloc[:, ci].astype(str).str.strip().str.upper(),
        "security": body.iloc[:, cn].astype(str).str.strip() if cn is not None else "",
        "industry": body.iloc[:, cs].astype(str).str.strip() if cs is not None else "",
        "weight": pd.to_numeric(body.iloc[:, cw], errors="coerce"),
    }).dropna(subset=["weight"])
    df = df[df["isin"].str.match(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")]   # Indian AND foreign ISINs (international funds)
    if df.empty:
        return None
    if df.weight.sum() <= 1.5:      # some AMCs report fractions
        df["weight"] *= 100
    df["is_equity"] = df["isin"].map(_is_equity_isin)
    return title, df


def _header_rows(raw: pd.DataFrame) -> list[int]:
    rows = []
    for i in range(len(raw)):
        vals = [re.sub(r"\s+", " ", str(v)).strip().lower() for v in raw.iloc[i].tolist()]
        if any(re.fullmatch(r"isin( (no|number|code)\.?)?", v) for v in vals) and any(re.search(r"nav|net assets|aum", v) for v in vals):
            rows.append(i)
    return rows


def parse_sheet_blocks(raw: pd.DataFrame, sheet_name: str):
    """A sheet may stack many schemes vertically (e.g. UTI: one 'EXPOSURE' sheet for all schemes).
    Split at every repeated header row; each block = the rows from ~12 lines above its header to the next block."""
    hs = _header_rows(raw)
    if len(hs) <= 1:
        r = parse_sheet(raw, sheet_name)
        return [r] if r else []
    out = []
    for k, h in enumerate(hs):
        start = max(hs[k - 1] + 1 if k else 0, h - 12)
        end = hs[k + 1] - 12 if k + 1 < len(hs) else len(raw)
        end = max(end, h + 2)
        r = parse_sheet(raw.iloc[start:end].reset_index(drop=True), sheet_name)
        if r:
            out.append(r)
    return out


def parse_file(path: Path) -> list[tuple[str, pd.DataFrame, str]]:
    out = []
    try:
        sheets = pd.read_excel(path, sheet_name=None, header=None)
    except Exception as e:
        print(f"  ! cannot read {path.name}: {e}")
        return out
    for sn, raw in sheets.items():
        for r in parse_sheet_blocks(raw, sn):
            out.append((r[0], r[1], path.name, path.parent.name))
    return out


# ----------------------------------------------------------- mapping sheets -> schemes
def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(direct|regular|plan|growth|option|idcw|the|scheme|an open ended.*)\b", " ", s)
    return re.sub(r"[^a-z0-9&]+", " ", s).strip()


def _amc_for(folder: str, amcs: list[str]):
    k = folder.replace("-", " ").lower()
    for a in amcs:
        if a.lower() == k:
            return a
    m = difflib.get_close_matches(k, [a.lower() for a in amcs], n=1, cutoff=0.6)
    return next((a for a in amcs if m and a.lower() == m[0]), None)


def _strip_brand(s: str, amc: str) -> str:
    words = [w for w in re.findall(r"[a-z0-9]+", (amc or "").lower()) if w not in ("mutual", "fund", "india")]
    for w in words:
        s = re.sub(rf"\b{w}\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


_GUARD = ["arbitrage", "hybrid", "balanced", "savings", "debt", "liquid", "etf", "overnight", "multi asset",
          "fund of fund", "fof", "gold", "silver", "retirement", "children", "bond", "gilt", "income", "money market"]


def map_to_schemes(parsed, universe: pd.DataFrame, cutoff=0.80) -> pd.DataFrame:
    """Match each portfolio to a pair_key, searching only within the AMC the file came from."""
    base = universe.drop_duplicates("pair_key")[["pair_key", "name", "amc"]].copy()
    base["n"] = base["name"].map(_norm)
    amcs = sorted(base.amc.dropna().unique())
    alias_f = C.MANUAL / "scheme_aliases.csv"      # columns: sheet_title, scheme_name  (exact AMFI scheme name)
    aliases = {}
    if alias_f.exists():
        al = pd.read_csv(alias_f)
        nm2pk = dict(zip(base["name"].str.lower().str.strip(), base["pair_key"]))
        aliases = {_norm(t): nm2pk.get(str(n).lower().strip()) for t, n in zip(al.sheet_title, al.scheme_name)}
    rows = []
    for cands, df, fname, folder in parsed:
        hit = next((aliases[_norm(t)] for t in cands if aliases.get(_norm(t))), None)
        if hit:
            rows.append({"title": cands[0], "file": fname, "amc": None, "score": 1.0, "pair_key": hit, "holdings": df})
            continue
        amc = _amc_for(folder, amcs)
        pool = base[base.amc == amc] if amc else base
        best = (0.0, None, None)
        for t in cands:
            tn = _norm(t)
            if not tn:
                continue
            for pk, n in zip(pool.pair_key, pool.n):
                r1 = difflib.SequenceMatcher(None, tn, n).ratio()
                r2 = difflib.SequenceMatcher(None, _strip_brand(tn, amc), _strip_brand(n, amc)).ratio() if amc else 0
                r = max(r1, r2)
                if r > best[0]:
                    best = (r, pk, t)
        ok = best[0] >= cutoff
        if ok:   # reject hybrid/arbitrage/ETF etc. sheets matched to a similarly named equity fund
            tl = (best[2] or "").lower()
            nm = base.loc[base.pair_key == best[1], "name"].iloc[0].lower()
            ok = not any(w in tl and w not in nm for w in _GUARD)
        rows.append({"title": best[2] or (cands[0] if cands else ""), "file": fname, "amc": amc,
                     "score": round(best[0], 2), "pair_key": best[1] if ok else None, "holdings": df})
    out = pd.DataFrame(rows)
    # if two sheets claim one scheme, keep the better match
    return out.sort_values("score", ascending=False)


# ----------------------------------------------------------- market-cap list
def load_mcap_list(path: Path | None = None) -> pd.Series | None:
    """AMFI list -> Series ISIN -> 'large'/'mid'/'small'. Columns detected loosely."""
    path = path or (C.MANUAL / "amfi_mcap.xlsx")
    if not path.exists():
        return None
    raw = pd.read_excel(path, header=None)
    h = next(i for i in range(30) if any("isin" in str(v).lower() for v in raw.iloc[i]))
    df = raw.iloc[h + 1:].copy()
    df.columns = [str(c).strip().lower() for c in raw.iloc[h]]
    icol = next(c for c in df.columns if "isin" in c)
    ccol = next((c for c in df.columns if "categor" in c), None)
    rcol = next((c for c in df.columns if "sr" in c or "rank" in c), None)
    if ccol is not None:
        cat = df[ccol].astype(str).str.lower().str.extract(r"(large|mid|small)")[0]
    else:
        rk = pd.to_numeric(df[rcol], errors="coerce")
        cat = pd.cut(rk, [0, 100, 250, 1e9], labels=["large", "mid", "small"]).astype(str)
    s = pd.Series(cat.values, index=df[icol].astype(str).str.strip().str.upper())
    rank = pd.to_numeric(df[rcol], errors="coerce") if rcol else None
    s.attrs["rank"] = pd.Series(rank.values, index=s.index) if rank is not None else None
    return s.dropna()


# ----------------------------------------------------------- metrics
def _check(val, op, lim):
    return val >= lim if op == ">=" else val <= lim


def portfolio_metrics(df: pd.DataFrame, category: str, mcap: pd.Series | None) -> dict:
    eq = df[df.is_equity]
    w = eq.groupby("isin").weight.sum()
    m = {
        "equity_pct": w.sum(),
        "cash_other_pct": max(0.0, 100 - df.weight.sum()) + df[~df.is_equity].weight.sum(),
        "n_stocks": int((w > 0).sum()),
        "top10_pct": w.nlargest(10).sum(),
        "effective_n": 1 / ((w / w.sum()) ** 2).sum() if w.sum() > 0 else np.nan,
    }
    if eq.industry.astype(str).str.len().gt(1).any():
        sec = eq.groupby("industry").weight.sum()
        m["top_sector"] = sec.idxmax()
        m["top_sector_pct"] = sec.max()
    if mcap is not None and len(w):
        cls = w.index.map(lambda i: mcap.get(i, "unclassified"))
        mix = w.groupby(cls).sum()
        for k in ("large", "mid", "small", "unclassified"):
            m[f"{k}_pct"] = float(mix.get(k, 0.0))
        rank = mcap.attrs.get("rank")
        if rank is not None:
            rk = w.index.map(lambda i: rank.get(i, np.nan))
            m["beyond500_pct"] = float(w[(pd.Series(rk, index=w.index) > 500) | pd.isna(rk)].sum())
    # mandate
    rules = MANDATES.get(category, [])
    breaches = []
    for key, op, lim in rules:
        val = m.get("equity_pct") if key == "equity" else m.get("n_stocks") if key == "n_stocks" else m.get(f"{key}_pct")
        # 3-point tolerance: AMFI's cap list changes twice a year (with a 1-month rebalancing window) and
        # month-end classification lags; only a clear shortfall counts as a breach
        tol = 0 if key == "n_stocks" else 3
        if val is not None and not np.isnan(val) and not _check(val + (tol if op == ">=" else -tol), op, lim):
            breaches.append(f"{key} {val:.0f} (needs {op}{lim})")
    m["mandate_ok"] = 0 if breaches else 1
    m["mandate_breaches"] = "; ".join(breaches)
    return m


def active_share(w_f: pd.Series, w_b: pd.Series) -> float:
    a, b = w_f / w_f.sum(), w_b / w_b.sum()
    idx = a.index.union(b.index)
    return 0.5 * (a.reindex(idx, fill_value=0) - b.reindex(idx, fill_value=0)).abs().sum() * 100


def analyse(month: str, universe_with_peers: pd.DataFrame, prev_month: str | None = None, log=print) -> pd.DataFrame:
    folder = HOLD_DIR / month
    files = sorted([p for p in folder.rglob("*") if p.suffix.lower() in (".xlsx", ".xls", ".xlsm", ".xlsb")
                    and not re.search(r"debt|fortnight|^~", p.name, re.I)])
    if not files:
        log(f"  holdings: no files in {folder}")
        return pd.DataFrame()
    parsed = [x for f in files for x in parse_file(f)]
    parsed = [x for x in parsed if x[1]["is_equity"].any()]   # equity portfolios only
    mapped = map_to_schemes(parsed, universe_with_peers)
    ok = mapped.dropna(subset=["pair_key"]).drop_duplicates("pair_key")
    log(f"  holdings: {len(parsed)} portfolios parsed from {len(files)} files, {len(ok)} mapped to schemes")
    mapped.drop(columns="holdings").to_csv(folder / "_mapping_report.csv", index=False)

    mcap = load_mcap_list()
    meta = universe_with_peers.drop_duplicates("pair_key").set_index("pair_key")
    weights = {pk: h[h.is_equity].groupby("isin").weight.sum() for pk, h in zip(ok.pair_key, ok.holdings)}

    # benchmark proxy portfolios: holdings of index funds tracking each benchmark (median across funds)
    bench_w = {}
    for b, g in meta[meta.category == "Index Fund"].groupby("benchmark"):
        ws = [weights[pk] for pk in g.index if pk in weights]
        if ws:
            bench_w[b] = pd.concat(ws, axis=1).fillna(0).median(axis=1)

    rows = []
    for pk, h in zip(ok.pair_key, ok.holdings):
        cat = meta.at[pk, "category"]
        m = portfolio_metrics(h, cat, mcap)
        m["pair_key"] = pk
        b = meta.at[pk, "benchmark"]
        if cat != "Index Fund":
            if isinstance(b, str) and b in bench_w:
                m["active_share"], m["active_share_basis"] = active_share(weights[pk], bench_w[b]), f"vs {b} index funds"
            else:   # peer-average portfolio fallback
                peers = [weights[p] for p in meta.index[(meta.peer_group == meta.at[pk, "peer_group"])] if p in weights and p != pk]
                if len(peers) >= 3:
                    pav = pd.concat(peers, axis=1).fillna(0).mean(axis=1)
                    m["active_share"], m["active_share_basis"] = active_share(weights[pk], pav), "vs peer average"
        rows.append(m)
    out = pd.DataFrame(rows)

    # month-on-month turnover proxy & style drift
    if prev_month and (HOLD_DIR / prev_month / "_weights.csv").exists():
        prev = pd.read_csv(HOLD_DIR / prev_month / "_weights.csv")
        pw = {pk: g.set_index("isin").weight for pk, g in prev.groupby("pair_key")}
        out["turnover_1m"] = out.pair_key.map(lambda pk: active_share(weights[pk], pw[pk]) if pk in pw else np.nan)
        if (HOLD_DIR / prev_month / "holdings_metrics.csv").exists():
            pm = pd.read_csv(HOLD_DIR / prev_month / "holdings_metrics.csv").set_index("pair_key")
            for k in ("large_pct", "mid_pct", "small_pct"):
                if k in out and k in pm:
                    out[f"drift_{k}"] = out[k] - out.pair_key.map(pm[k])
    long = pd.concat([w.rename("weight").reset_index().assign(pair_key=pk) for pk, w in weights.items()])
    long.to_csv(folder / "_weights.csv", index=False)
    # validation: quarantine portfolios that cannot be the scheme's (wrong sheet mapped / partial parse)
    cat = out.pair_key.map(meta["category"])
    nm = out.pair_key.map(meta["name"]).fillna("").str.lower()
    foreign = nm.str.contains("asian|global|international|us |nasdaq|taiwan|japan|china|world|overseas")
    reason = pd.Series("", index=out.index)
    reason[(out.n_stocks < 5)] = "fewer than 5 equity holdings"
    reason[(out.equity_pct < 50) & ~foreign & (reason == "")] = "equity < 50% of NAV for an equity scheme"
    reason[(out.equity_pct > 102) & (reason == "")] = "weights sum > 102% (double-counted rows)"
    out["validation"] = reason.replace("", "ok")
    out.to_csv(folder / "holdings_metrics.csv", index=False)
    bad = set(out.pair_key[out.validation != "ok"])
    out = out[out.validation == "ok"].copy()
    ok = ok[~ok.pair_key.isin(bad)]
    log(f"  holdings validation: {len(bad)} portfolios quarantined")
    top = {}
    for pk, h in zip(ok.pair_key, ok.holdings):
        e = h[h.is_equity].groupby("isin").agg(security=("security", "first"), weight=("weight", "sum"))
        e = e.sort_values("weight", ascending=False)
        top[pk] = [[i, str(n)[:40], round(float(w), 2)] for i, n, w in zip(e.index, e["security"], e["weight"]) if w > 0.05]
    out.attrs["top"] = top
    import json as _json
    (folder / "_top.json").write_text(_json.dumps(top, separators=(",", ":")))
    out.to_csv(folder / "holdings_valid.csv", index=False)
    return out


def latest_cached_month(before: str | None = None) -> str | None:
    """Most recent month (YYYY-MM) with parsed holdings on disk, optionally strictly before `before`."""
    done = sorted(p.name for p in HOLD_DIR.glob("20??-??") if (p / "holdings_valid.csv").exists())
    if before:
        done = [m for m in done if m < before]
    return done[-1] if done else None


def with_fallback(hold: pd.DataFrame, month: str, log=print, same_month: pd.DataFrame | None = None) -> tuple[pd.DataFrame, str]:
    """Fill funds missing from `month` with their latest earlier parsed portfolio.

    - nothing parsed for `month` (portfolios not published yet, downloads blocked): use the previous month whole
    - some AMCs missing (late publishers, a failed download): carry those funds' previous portfolio forward
    Each row records the month its portfolio is from in `holdings_month`.
    `same_month`: what was already parsed for `month` before this run (a re-run keeps those portfolios).
    Returns (holdings, month the site should show as the holdings month).
    """
    if same_month is not None and len(same_month):
        keep = same_month[~same_month.pair_key.isin(hold.pair_key)] if len(hold) else same_month
        if len(keep):
            top = {**same_month.attrs.get("top", {}), **(hold.attrs.get("top", {}) if len(hold) else {})}
            hold = pd.concat([hold, keep], ignore_index=True) if len(hold) else keep.copy()
            hold.attrs["top"] = top
            log(f"  holdings: kept {len(keep)} portfolios already parsed for {month} that this run did not re-download")
    prev_m = latest_cached_month(before=month)
    if len(hold):
        hold = hold.copy()
        hold["holdings_month"] = month
    if not prev_m:
        return hold, month
    prev = load_cached(prev_m)
    if not len(prev):
        return hold, month
    prev = prev.copy()
    prev["holdings_month"] = prev.get("holdings_month", prev_m)
    if not len(hold):
        log(f"  holdings: nothing parsed for {month}; re-using {len(prev)} portfolios from {prev_m}")
        return prev, prev_m
    carry = prev[~prev.pair_key.isin(hold.pair_key)].copy()
    for c in [c for c in carry.columns if c == "turnover_1m" or c.startswith("drift_")]:
        carry[c] = np.nan   # month-on-month measures are not valid for a carried-forward portfolio
    top = dict(prev.attrs.get("top", {}))
    top = {k: v for k, v in top.items() if k in set(carry.pair_key)}
    out = pd.concat([hold, carry], ignore_index=True)
    out.attrs["top"] = {**top, **hold.attrs.get("top", {})}
    log(f"  holdings: {len(hold)} portfolios from {month}, {len(carry)} carried forward from {prev_m} "
        f"(AMCs not published / not downloaded) -> {len(out)} total")
    return out, month


def save_cached(hold: pd.DataFrame, month: str) -> None:
    import json as _json
    folder = HOLD_DIR / month
    folder.mkdir(parents=True, exist_ok=True)
    hold.to_csv(folder / "holdings_valid.csv", index=False)
    (folder / "_top.json").write_text(_json.dumps(hold.attrs.get("top", {}), separators=(",", ":")))


def load_cached(month: str) -> pd.DataFrame:
    """Parsed results of a previous analyse() run (used by the daily refresh; raw AMC files are not kept in git)."""
    import json as _json
    folder = HOLD_DIR / month
    if not (folder / "holdings_valid.csv").exists():
        return pd.DataFrame()
    out = pd.read_csv(folder / "holdings_valid.csv")
    out.attrs["top"] = _json.loads((folder / "_top.json").read_text()) if (folder / "_top.json").exists() else {}
    return out
