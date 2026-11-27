"""Build site/data/pms.json: every PMS strategy we show, with its record, metrics, peer ranks and rating.

    python tools/pms_build.py [--review]

Inputs: data/pms/apmi_monthly.csv (engine/pms_fetch.py + engine/pms.load_raw); data/pms/bench_monthly.csv (month-end
levels: Nifty 50 / 500 / Multicap 50:25:25 / Midcap 150 / Smallcap 250 TRI, and BOND = the median high-quality bond
mutual fund, chained); data/pms/ratings_state.json (the last quarterly review). Method v2: docs/thesis_pms_ratings.md.

Three methods, one per asset class:
  equity  each strategy is measured against the style index it tracks most closely (lowest tracking error among
          Nifty 50, Nifty 500, Nifty 500 Multicap 50:25:25, Nifty Midcap 150, Nifty Smallcap 250) and ranked within
          its style group (large and multi cap / mid and small cap)
  debt    against the median high-quality bond mutual fund (corporate bond, banking & PSU, short duration)
  hybrid  against its own fitted mix of Nifty 500 TRI and the bond yardstick (equity share by least tracking error)
Ratings are reviewed quarterly (data to March, June, September, December) with a 5-point buffer; metrics are monthly.
"""
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.pms import monthly_series, metrics, _chain  # noqa: E402

MIN_AUM, KEEP_AUM, MIN_MONTHS = 100.0, 75.0, 24
RF = 6.5        # % a year, risk-free rate for Sharpe and Sortino (91-day T-bill, approximately)
# strategies APMI files under Equity that are not stock portfolios: kept out of the equity peer group
NOT_EQUITY = re.compile(r"arbitrage|pre[- ]?ipo|unlisted|private equity|\bmope\b|special situations? fund", re.I)
CASH = re.compile(r"liquid|overnight|money market|cash", re.I)


def slug(s):
    s = re.sub(r"\((formerly|earlier)[^)]*\)", "", s, flags=re.I)
    s = re.sub(r"\b(private|pvt\.?|limited|ltd\.?|llp|india|portfolio managers?|asset management|company|co\.?)\b", " ", s, flags=re.I) \
        if False else s
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")[:70]


def mgr_slug(s):
    s = re.sub(r"\((formerly|earlier)[^)]*\)", "", s, flags=re.I)
    s = re.sub(r"\b(private|pvt|limited|ltd|llp|company)\b\.?", " ", s, flags=re.I)
    return slug(s)


def nice(s):
    """APMI names come in every case: title-case the shouty ones, keep acronyms."""
    s = re.sub(r"\s+", " ", s or "").strip()
    if s.isupper() and len(s) > 6:
        s = " ".join(w if (len(w) <= 3 and w.isalpha() and w not in ("THE", "AND", "FOR", "ONE", "TOP")) or not w.isalpha() else w.capitalize()
                     for w in s.split(" "))
    return s


def pct_rank(vals, v):
    xs = [x for x in vals if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if v is None or not xs:
        return None
    below = sum(x < v for x in xs)
    eq = sum(x == v for x in xs)
    return (below + 0.5 * eq) / len(xs)


def extra(r, b):
    """More risk figures from aligned monthly returns r and benchmark b (%)."""
    n = len(r)
    mu = sum(r) / n
    sd = math.sqrt(sum((x - mu) ** 2 for x in r) / (n - 1))
    rf_m = (1 + RF / 100) ** (1 / 12) - 1
    downs = [min(0, x / 100 - rf_m) for x in r]
    dd = math.sqrt(sum(d * d for d in downs) / n)
    ann = (_chain(r) ** (12 / n) - 1)
    mb = sum(b) / n
    cov = sum((x - mu) * (y - mb) for x, y in zip(r, b)) / (n - 1)
    vb = sum((y - mb) ** 2 for y in b) / (n - 1)
    ex = [x - y for x, y in zip(r, b)]
    me = sum(ex) / n
    te = math.sqrt(sum((e - me) ** 2 for e in ex) / (n - 1)) * math.sqrt(12)
    # months to recover from the worst fall (None if not yet recovered)
    g, peak, trough_i, peak_i, worst, rec = 1.0, 1.0, 0, 0, 0.0, None
    path = []
    for x in r:
        g *= 1 + x / 100
        path.append(g)
    pk, pki, best = path[0], 0, (0.0, 0, 0)
    for i, v in enumerate(path):
        if v > pk:
            pk, pki = v, i
        if v / pk - 1 < best[0]:
            best = (v / pk - 1, pki, i)
    if best[0] < 0:
        top = path[best[1]]
        for j in range(best[2] + 1, n):
            if path[j] >= top:
                rec = j - best[2]
                break
    return {"vol": sd * math.sqrt(12), "sharpe": (ann * 100 - RF) / (sd * math.sqrt(12)) if sd else None,
            "sortino": (ann - RF / 100) / (dd * math.sqrt(12)) if dd else None, "beta": cov / vb if vb else None,
            "te": te, "neg_months": sum(x < 0 for x in r) / n, "worst_month": min(r), "best_month": max(r),
            "recovery_months": rec, "dd_months": best[2] - best[1] if best[0] < 0 else 0}


def calendar(months, r, b):
    out = {}
    for y in sorted({m[:4] for m in months}):
        idx = [i for i, m in enumerate(months) if m.startswith(y)]
        out[y] = {"n": len(idx), "r": (_chain([r[i] for i in idx]) - 1) * 100, "b": (_chain([b[i] for i in idx]) - 1) * 100,
                  "from": months[idx[0]], "to": months[idx[-1]]}
    return out


STYLE_IX = {"NIFTY 50": "Nifty 50 TRI", "NIFTY 500": "Nifty 500 TRI", "NIFTY500 MULTICAP 50:25:25": "Nifty 500 Multicap 50:25:25 TRI",
            "NIFTY MIDCAP 150": "Nifty Midcap 150 TRI", "NIFTY SMALLCAP 250": "Nifty Smallcap 250 TRI"}
STYLE_GROUP = {"NIFTY 50": "Large and multi cap", "NIFTY 500": "Large and multi cap", "NIFTY500 MULTICAP 50:25:25": "Large and multi cap",
               "NIFTY MIDCAP 150": "Mid and small cap", "NIFTY SMALLCAP 250": "Mid and small cap"}
BOND_CATS = ("corporate-bond", "banking-psu", "short-term")
BOND_NAME = "median high-quality bond fund"
# weights (percentile within the peer group; negative = lower is better). Evidence: audit/pms/walkforward.py,
# audit/pms/compare_models.py (13 formations Mar 2025 - Mar 2026, next-12-month excess over the style index).
W_EQUITY = {"alpha": 20, "ir": 15, "hit_m": 15, "hit_12m": 10, "half_min": 10, "down_capture": -10, "vol": -10, "rel_dd": 10}
W_DEBT = {"ex_ann": 25, "sortino": 20, "ir": 15, "hit_12m": 15, "max_dd": 15, "vol": -10}
W_HYBRID = {"alpha": 20, "ir": 15, "hit_12m": 15, "sortino": 15, "rel_dd": 15, "down_capture": -10, "vol": -10}
LABEL = {"alpha": "return over its yardstick, adjusted for market exposure (alpha)", "ir": "steadiness of its lead (information ratio)",
         "hit_m": "months ahead of its yardstick", "hit_12m": "12-month spells ahead of its yardstick",
         "half_min": "a lead in both halves of its record", "down_capture": "protection in falling months", "vol": "low volatility",
         "rel_dd": "worst fall compared with its yardstick's", "ex_ann": "return over its yardstick", "sortino": "return per unit of downside risk (Sortino)",
         "max_dd": "worst fall"}
REVIEW_MONTHS = ("03", "06", "09", "12")
BUFFER = 0.05


def bond_returns():
    """Monthly % return of the median high-quality bond mutual fund (all plans), from the site's category NAV series."""
    import numpy as np
    frames = []
    for c in BOND_CATS:
        p = ROOT / f"site/data/series/{c}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        df = pd.DataFrame({k: v for k, v in d["nav"].items()}, index=d["months"]).astype(float)
        frames.append(df.pct_change(fill_method=None) * 100)
    if not frames:
        return None
    r = pd.concat(frames, axis=1)
    r = r[(r.abs() < 8) | r.isna()]           # face-value changes and data errors
    return r.median(axis=1).dropna()


def refresh_bond_column(bl):
    """bench_monthly.csv BOND column (level, 100 at the first month) from bond_returns(); keeps the old one if the series is missing."""
    br = bond_returns()
    if br is None:
        return bl
    lv, g = {}, 100.0
    for m in sorted(br.index):
        g *= 1 + br[m] / 100
        lv[m] = g
    first = min(lv)
    lv = pd.Series(lv)
    bl = bl.copy()
    bl["BOND"] = lv.reindex(bl.index)
    return bl


def _stats(r, b):
    """Measures of r against yardstick b (monthly %, aligned lists)."""
    import numpy as np
    r, b = np.asarray(r, float), np.asarray(b, float)
    n = len(r)
    ex = r - b
    ch = lambda x: float(np.prod(1 + np.asarray(x) / 100))
    out = {"ex_ann": (ch(r) ** (12 / n) - ch(b) ** (12 / n)) * 100}
    sd = ex.std(ddof=1)
    out["ir"] = float(ex.mean() * 12 / (sd * math.sqrt(12))) if sd > 0 else None
    vb = b.var(ddof=1)
    beta = float(np.cov(r, b)[0, 1] / vb) if vb > 0 else None
    out["beta_y"] = beta
    out["alpha"] = float((r.mean() - beta * b.mean()) * 12) if beta is not None else None
    d, u = b < 0, b > 0
    out["down_capture"] = float(r[d].sum() / b[d].sum()) if d.sum() >= 3 else None
    out["up_capture"] = float(r[u].sum() / b[u].sum()) if u.sum() >= 3 else None
    def mdd(x):
        g = np.cumprod(1 + x / 100)
        return float((g / np.maximum.accumulate(g) - 1).min() * 100)
    out["bench_dd"] = mdd(b)
    out["rel_dd"] = mdd(r) - mdd(b)
    roll = [ch(r[i - 12:i]) - ch(b[i - 12:i]) for i in range(12, n + 1)]
    out["hit_12m"] = float(np.mean([x > 0 for x in roll]))
    out["worst_12m_ex"] = float(min(roll) * 100)
    out["best_12m_ex"] = float(max(roll) * 100)
    out["hit_m"] = float((ex > 0).mean())
    h = n // 2
    out["half_min"] = float(min(ex[:h].mean(), ex[h:].mean()) * 12)
    out["te"] = float(sd * math.sqrt(12))
    return out


def _trailing(levels, last):
    """Trailing returns of a month-end level series to `last`, APMI's periods (over a year: a year)."""
    keys = sorted(k for k in levels if levels[k] is not None and not (isinstance(levels[k], float) and math.isnan(levels[k])))
    if last not in keys:
        return {}
    i = keys.index(last)
    out = {}
    for k, nm in (("r1m", 1), ("r3m", 3), ("r6m", 6), ("r1y", 12), ("r2y", 24), ("r3y", 36), ("r4y", 48), ("r5y", 60)):
        if i - nm >= 0 and keys[i - nm] == _shift(last, -nm):
            v = levels[keys[i]] / levels[keys[i - nm]]
            out[k] = round(((v ** (12 / nm) - 1) if nm > 12 else (v - 1)) * 100, 2)
    return out


def _shift(m, k):
    y, mo = int(m[:4]), int(m[5:]) - 1 + k
    return f"{y + mo // 12}-{mo % 12 + 1:02d}"


def _tier(p, score, prev, guard_ok, buf):
    """Tier from percentile p (1 = best) and score; prev = the tier at the last review (kept unless clearly crossed)."""
    raw = "A+" if p >= 0.9 and score >= 70 else "A" if p >= 0.7 and score >= 55 else "C" if p <= 0.3 else "B"
    if prev in ("A+", "A", "B", "C") and buf:
        lo = {"A+": 0.9 - buf, "A": 0.7 - buf, "B": 0.3 - buf, "C": -1}[prev]
        hi = {"A+": 9, "A": 0.9 + buf, "B": 0.7 + buf, "C": 0.3 + buf}[prev]
        sc_ok = score >= {"A+": 70 - 100 * buf, "A": 55 - 100 * buf}.get(prev, 0)
        if lo <= p < hi and sc_ok:
            raw = prev
    if raw in ("A+", "A") and not guard_ok:
        raw = "B"
    return raw


def build(review=None):
    import numpy as np
    df = pd.read_csv(ROOT / "data/pms/apmi_monthly.csv")
    bl = pd.read_csv(ROOT / "data/pms/bench_monthly.csv", index_col=0)
    bl = refresh_bond_column(bl)
    bl.to_csv(ROOT / "data/pms/bench_monthly.csv")
    last = df.month.max()
    bl = bl[bl.index <= last]
    bret = {k: ((bl[k] / bl[k].shift(1) - 1) * 100).dropna().to_dict() for k in bl.columns}
    cur = df[df.month == last].set_index("iaid")
    prev_p = ROOT / "site/data/pms.json"
    shown_before = set()
    if prev_p.exists():
        try:
            shown_before = {s["id"] for s in json.loads(prev_p.read_text())["strategies"]}
        except Exception:
            pass
    state_p = ROOT / "data/pms/ratings_state.json"
    state = json.loads(state_p.read_text()) if state_p.exists() else {}
    if review is None:
        review = (not state) or (last[5:] in REVIEW_MONTHS and state.get("review") != last)
    pool = cur[(cur.aum >= MIN_AUM) | ((cur.aum >= KEEP_AUM) & cur.index.isin(shown_before))]
    S = monthly_series(df[df.iaid.isin(pool.index)])
    A = df[df.iaid.isin(pool.index)].pivot_table(index="iaid", columns="month", values="aum", aggfunc="first")
    strategies = []
    b500 = bret["NIFTY 500"]
    bond = bret.get("BOND", {})
    yard_levels = {}           # yardstick name -> month-end levels (for trailing returns)
    for i, row in pool.iterrows():
        ser = S.loc[i] if i in S.index else pd.Series(dtype=float)
        months = [m for m in ser.index if pd.notna(ser[m]) and m in b500 and m >= "2023-01"]
        r = [float(ser[m]) for m in months]
        name, mgr = nice(row.strategy), nice(row.manager)
        group = row.type if row.type in ("Equity", "Debt") else "Hybrid and multi-asset"
        if row.type == "Equity" and NOT_EQUITY.search(row.strategy):
            group = "Other (arbitrage, unlisted and special situations)"
        if row.type == "Debt" and CASH.search(row.strategy):
            group = "Cash (liquid strategies)"
        s = {"id": int(i), "name": name, "manager": mgr, "mslug": mgr_slug(row.manager), "slug": slug(name),
             "type": row.type, "service": row.service, "group": group, "aum": round(float(row.aum), 2),
             "apmi": {k: (None if pd.isna(row[k]) else float(row[k])) for k in ["r1m", "r3m", "r6m", "r1y", "r2y", "r3y", "r4y", "r5y", "rsi"]},
             "months": months, "r": [round(x, 2) for x in r],
             "aum_hist": {m: round(float(v), 2) for m, v in A.loc[i].items() if pd.notna(v)} if i in A.index else {}}
        long_ok = len(r) >= MIN_MONTHS
        # ---- the yardstick
        yk, yname, ymix = "NIFTY 500", STYLE_IX["NIFTY 500"], None
        if group == "Equity" and long_ok:
            te = {}
            for k in STYLE_IX:
                bb = [bret[k].get(m) for m in months]
                if None in bb:
                    continue
                te[k] = float(np.std(np.array(r) - np.array(bb), ddof=1))
            yk = min(te, key=te.get)
            yname = STYLE_IX[yk]
            s["style_group"] = STYLE_GROUP[yk]
        elif group in ("Debt", "Cash (liquid strategies)") and bond:
            yk, yname = "BOND", BOND_NAME
        elif group == "Hybrid and multi-asset" and bond and long_ok:
            best = None
            for w in [x / 20 for x in range(0, 21)]:
                bb = [w * b500[m] + (1 - w) * bond.get(m, 0) for m in months]
                t = float(np.std(np.array(r) - np.array(bb), ddof=1))
                if best is None or t < best[0]:
                    best = (t, w)
            ymix = best[1]
            yk, yname = "MIX", f"{ymix * 100:.0f}% Nifty 500 TRI + {100 - ymix * 100:.0f}% {BOND_NAME}"
        if yk == "MIX":
            ys = {m: ymix * b500[m] + (1 - ymix) * bond[m] for m in b500 if m in bond}
        else:
            ys = bret[yk]
        s["yard"] = {"key": yk, "name": yname, "mix": ymix}
        b = [ys.get(m) for m in months]
        if None in b:     # yardstick missing a month: fall back to Nifty 500
            ys, b = b500, [b500[m] for m in months]
            s["yard"] = {"key": "NIFTY 500", "name": STYLE_IX["NIFTY 500"], "mix": None}
        s["b"] = [round(x, 3) for x in b]
        lvkey = s["yard"]["name"]
        if lvkey not in yard_levels:
            g_, lv = 100.0, {}
            ks = sorted(ys)
            lv[_shift(ks[0], -1)] = 100.0
            for m in ks:
                g_ *= 1 + ys[m] / 100
                lv[m] = g_
            yard_levels[lvkey] = lv
        s["yr"] = _trailing(yard_levels[lvkey], last)
        m = metrics(ser, b500, MIN_MONTHS)          # vs Nifty 500: kept for reference (beta to the market)
        s["m"] = {k: (None if v is None else round(float(v), 4)) for k, v in m.items() if k in ("months", "max_dd", "ann_ret")}
        if long_ok:
            s["m"].update({k: (None if v is None else round(float(v), 4)) for k, v in extra(r, [b500[x] for x in months]).items()})
            s["m"]["beta"] = s["m"].pop("beta")        # beta to Nifty 500
            s["m"].update({k: (None if v is None else round(float(v), 4)) for k, v in _stats(r, b).items()})
            s["m"]["ann_bench"] = round((_chain(b) ** (12 / len(b)) - 1) * 100, 3)
            s["cal"] = calendar(months, r, b)
            if group == "Equity" and (s["m"].get("beta") is not None and s["m"]["beta"] < 0.5):
                group = s["group"] = "Other (arbitrage, unlisted and special situations)"
                s.pop("style_group", None)
        # 3-year return over the yardstick: APMI's own 3-year figure against the yardstick's 36 months
        if s["apmi"]["r3y"] is not None and s["yr"].get("r3y") is not None:
            s["m"]["ex3y"] = round(s["apmi"]["r3y"] - s["yr"]["r3y"], 2)
            s["m"]["ix3y"] = s["yr"]["r3y"]
        ah = s["aum_hist"]
        fl = {}
        for k, mo in enumerate(months):
            pm = months[k - 1] if k else None
            if pm and pm in ah and mo in ah:
                fl[mo] = round(ah[mo] - ah[pm] * (1 + r[k] / 100), 2)
        s["flows"] = fl
        last12 = [fl[mo] for mo in months[-12:] if mo in fl]
        base = ah.get(months[-13]) if len(months) >= 13 else None
        s["m"]["flow12_pct"] = round(sum(last12) / base * 100, 1) if base and len(last12) >= 10 else None
        s["rated"] = (row.service == "D" and s["apmi"]["r3y"] is not None and long_ok and row.aum >= KEEP_AUM
                      and not group.startswith(("Other", "Cash")))
        s["why_unrated"] = ("Non-discretionary: each client approves trades, so returns depend on the client's choices"
                            if row.service == "N" else "Less than 3 years of reported returns" if s["apmi"]["r3y"] is None or not long_ok
                            else "Not a stock portfolio: filed as equity, but it barely moves with the market (arbitrage, unlisted or special situations)" if group.startswith("Other")
                            else "Cash parking: a liquid strategy where clients keep money between investments" if group.startswith("Cash") else "")
        strategies.append(s)
    # ---- peer groups, scores, tiers
    prev_t = state.get("tiers", {}) if review else {}
    def peer_key(s):
        return s.get("style_group") if s["group"] == "Equity" else s["group"]
    for g in sorted({peer_key(s) for s in strategies if s["rated"]}):
        peers = [s for s in strategies if s["rated"] and peer_key(s) == g]
        W = W_EQUITY if g in STYLE_GROUP.values() else W_DEBT if g == "Debt" else W_HYBRID
        for s in peers:
            sc, wt, ranks = 0.0, 0.0, {}
            for k, w in W.items():
                v = s["m"].get(k)
                p = pct_rank([x["m"].get(k) for x in peers], v)
                if p is None:
                    continue
                if w < 0:
                    p = 1 - p
                ranks[k] = round(p, 3)
                sc += abs(w) * p
                wt += abs(w)
            s["score"] = round(100 * sc / wt, 1) if wt else None
            s["pct"] = ranks
            s["peer_group"] = g
        order = sorted([s for s in peers if s.get("score") is not None], key=lambda s: -s["score"])
        n = len(order)
        for k, s in enumerate(order):
            s["rank"], s["of"] = k + 1, n
            p = 1 - k / max(1, n - 1) if n > 1 else 1.0
            s["pctile"] = round(p, 3)
            # absolute guard: A or A+ needs a lead over the yardstick both over 3 years and over the whole record (alpha)
            guard = (s["m"].get("ex3y") or 0) > 0 and (s["m"].get("alpha") or 0) > 0
            s["tier_new"] = _tier(p, s["score"], prev_t.get(str(s["id"])), guard, BUFFER)
    # ---- quarterly review or carry the last review forward
    if review:
        for s in strategies:
            if s.get("tier_new"):
                s["tier"] = s["tier_new"]
        state = {"review": last, "tiers": {str(s["id"]): s["tier"] for s in strategies if s.get("tier")},
                 "scores": {str(s["id"]): [s["score"], s["rank"], s["of"]] for s in strategies if s.get("tier")}}
        state_p.write_text(json.dumps(state, indent=0), encoding="utf-8")
    else:
        for s in strategies:
            t = state.get("tiers", {}).get(str(s["id"]))
            if s["rated"] and t:
                s["tier"] = t
            elif s["rated"]:
                s["pending"] = True        # newly eligible: rated at the next review
    for s in strategies:
        s.pop("tier_new", None)
        if s.get("tier") in ("A+", "A") and (s["m"].get("flow12_pct") or 0) < -30:     # applies every month
            s["flag"] = "Assets shrinking: clients took out more than 30% of the money in the last 12 months"
            s["tier"] = "B"
    rv = state.get("review", last)
    nxt = next(_shift(rv, k) for k in range(1, 4) if _shift(rv, k)[5:] in REVIEW_MONTHS)
    # slugs unique within a manager
    seen = {}
    for s in strategies:
        k = (s["mslug"], s["slug"])
        if k in seen:
            s["slug"] = f"{s['slug']}-{'nd' if s['service'] == 'N' else s['id']}"
        seen[(s["mslug"], s["slug"])] = 1
    mgrs = {}
    for s in strategies:
        mgrs.setdefault(s["mslug"], {"name": s["manager"], "slug": s["mslug"], "ids": []})["ids"].append(s["id"])
    tot = cur.groupby("manager").aum.agg(["sum", "count"])
    for mg in mgrs.values():
        raw = [n for n in tot.index if mgr_slug(n) == mg["slug"]]
        mg["aum_all"] = round(float(sum(tot.loc[n, "sum"] for n in raw)), 1)
        mg["n_all"] = int(sum(tot.loc[n, "count"] for n in raw))
    # industry view for the hub: every discretionary equity strategy APMI lists, by size band
    eqc = cur[(cur.type == "Equity") & (cur.service == "D")]
    industry = {"aum_type": {t: round(float(cur[cur.type == t].aum.sum()), 0) for t in cur.type.unique()},
                "n_type": {t: int((cur.type == t).sum()) for t in cur.type.unique()},
                "aum_service": {sv: round(float(cur[cur.service == sv].aum.sum()), 0) for sv in ("D", "N")},
                "size_bands": [[lab, int(((eqc.aum >= lo) & (eqc.aum < hi)).sum()), round(float(eqc[(eqc.aum >= lo) & (eqc.aum < hi)].aum.sum()), 0)]
                               for lab, lo, hi in (("Under ₹25 cr", 0, 25), ("₹25–100 cr", 25, 100), ("₹100–500 cr", 100, 500),
                                                   ("₹500–2,000 cr", 500, 2000), ("₹2,000 cr+", 2000, 1e12))]}
    tot_hist = df[df.month >= "2023-04"].groupby("month").aum.sum()
    industry["aum_hist"] = {m: round(float(v), 0) for m, v in tot_hist.items()}
    out = {"as_of": last, "first": min(df[df.month >= "2023-04"].month), "n_all": int(len(cur)),
           "n_all_d": int((cur.service == "D").sum()), "aum_all": round(float(cur.aum.sum()), 0),
           "review": rv, "next_review": nxt, "method": "v2",
           "bench": {k: {m: round(v, 3) for m, v in d.items() if m >= "2023-04"} for k, d in bret.items()},
           "industry": industry, "strategies": strategies, "managers": sorted(mgrs.values(), key=lambda m: m["name"].lower())}
    (ROOT / "site/data").mkdir(exist_ok=True)
    (ROOT / "site/data/pms.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False, allow_nan=False), encoding="utf-8")
    rated = [s for s in strategies if s["rated"]]
    print(f"{len(strategies)} strategies shown, {len(rated)} rated, {len(mgrs)} managers; as of {last}; review {rv} (next {nxt}){' [REVIEW RUN]' if review else ''}")
    for g in sorted({s.get('peer_group') or s['group'] for s in rated}):
        tiers = [s.get("tier") for s in rated if (s.get('peer_group') or s['group']) == g]
        print(" ", g, len(tiers), {t: tiers.count(t) for t in ("A+", "A", "B", "C", None)})


if __name__ == "__main__":
    build(True if "--review" in sys.argv else None)
