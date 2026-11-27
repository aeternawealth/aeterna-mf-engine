"""Build site/data/pms.json: every PMS strategy we show, with its record, metrics, peer ranks and draft rating.

    python tools/pms_build.py

Inputs: data/pms/apmi_monthly.csv (engine/pms_fetch.py + engine/pms.load_raw), data/pms/bench_monthly.csv
(Nifty 500 TRI and Nifty 50 TRI month-end levels). Method: docs/thesis_pms_ratings.md (draft until the owner
approves it; until then pages show the metrics and the draft rating only on staging).
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
WEIGHTS = {   # equity: percentile within the peer group (higher is better after the sign)
    "ex3y": 20, "ir": 20, "hit_12m": 15, "down_capture": -15, "max_dd": 10, "worst_12m_ex": 10, "hit_m": 10}
WEIGHTS_OTHER = {"ann_ret_ex": 30, "hit_12m": 20, "max_dd": 20, "vol": -15, "worst_12m_ex": 15}


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


def build():
    df = pd.read_csv(ROOT / "data/pms/apmi_monthly.csv")
    bl = pd.read_csv(ROOT / "data/pms/bench_monthly.csv", index_col=0)
    bench = {k: ((bl[k] / bl[k].shift(1) - 1) * 100).dropna().to_dict() for k in bl.columns}
    last = df.month.max()
    cur = df[df.month == last].set_index("iaid")
    # who is shown: over Rs 100 cr now, or over Rs 75 cr now and shown last month (so pages do not flicker)
    prev_p = ROOT / "site/data/pms.json"
    shown_before = set()
    if prev_p.exists():
        try:
            shown_before = {s["id"] for s in json.loads(prev_p.read_text())["strategies"]}
        except Exception:
            pass
    pool = cur[(cur.aum >= MIN_AUM) | ((cur.aum >= KEEP_AUM) & cur.index.isin(shown_before))]
    S = monthly_series(df[df.iaid.isin(pool.index)])
    A = df[df.iaid.isin(pool.index)].pivot_table(index="iaid", columns="month", values="aum", aggfunc="first")
    strategies = []
    b500 = bench["NIFTY 500"]
    for i, row in pool.iterrows():
        ser = S.loc[i] if i in S.index else pd.Series(dtype=float)
        months = [m for m in ser.index if pd.notna(ser[m]) and m in b500]
        r = [float(ser[m]) for m in months]
        bb = [b500[m] for m in months]
        name, mgr = nice(row.strategy), nice(row.manager)
        group = row.type if row.type in ("Equity", "Debt") else "Hybrid and multi-asset"
        if row.type == "Equity" and NOT_EQUITY.search(row.strategy):
            group = "Other (arbitrage, unlisted and special situations)"
        s = {"id": int(i), "name": name, "manager": mgr, "mslug": mgr_slug(row.manager), "slug": slug(name),
             "type": row.type, "service": row.service, "group": group, "aum": round(float(row.aum), 2),
             "apmi": {k: (None if pd.isna(row[k]) else float(row[k])) for k in ["r1m", "r3m", "r6m", "r1y", "r2y", "r3y", "r4y", "r5y", "rsi"]},
             "months": months, "r": [round(x, 2) for x in r], "b": [round(x, 3) for x in bb],
             "aum_hist": {m: round(float(v), 2) for m, v in A.loc[i].items() if pd.notna(v)} if i in A.index else {}}
        m = metrics(ser, b500, MIN_MONTHS)
        s["m"] = {k: (None if v is None else round(float(v), 4)) for k, v in m.items()}
        if len(r) >= MIN_MONTHS:
            s["m"].update({k: (None if v is None else round(float(v), 4)) for k, v in extra(r, bb).items()})
            s["cal"] = calendar(months, r, bb)
            # filed under equity but barely moves with the market: not a stock portfolio in practice
            if group == "Equity" and (s["m"].get("beta") is not None and s["m"]["beta"] < 0.5):
                group = s["group"] = "Other (arbitrage, unlisted and special situations)"
        if row.type == "Debt" and CASH.search(row.strategy):
            group = s["group"] = "Cash (liquid strategies)"
        # 3-year excess return over Nifty 500 TRI, from APMI's own 3-year figure and the index over the same 36 months
        if s["apmi"]["r3y"] is not None and len(bl) >= 37:
            lv = bl["NIFTY 500"]
            ix3 = ((lv.loc[last] / lv.iloc[lv.index.get_loc(last) - 36]) ** (1 / 3) - 1) * 100
            s["m"]["ex3y"] = round(s["apmi"]["r3y"] - ix3, 2)
            s["m"]["ix3y"] = round(ix3, 2)
        # money in or out: change in assets not explained by the month's return (Rs cr)
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
        s["rated"] = (row.service == "D" and s["apmi"]["r3y"] is not None and len(r) >= MIN_MONTHS and row.aum >= KEEP_AUM
                      and not group.startswith(("Other", "Cash")))
        s["why_unrated"] = ("Non-discretionary: each client approves trades, so returns depend on the client's choices"
                            if row.service == "N" else "Less than 3 years of reported returns" if s["apmi"]["r3y"] is None or len(r) < MIN_MONTHS
                            else "Not a stock portfolio: filed as equity, but it barely moves with the market (arbitrage, unlisted or special situations)" if group.startswith("Other")
                            else "Cash parking: a liquid strategy where clients keep money between investments" if group.startswith("Cash") else "")
        strategies.append(s)
    # peer ranks and scores (discretionary, rated, within group)
    for g in sorted({s["group"] for s in strategies}):
        peers = [s for s in strategies if s["group"] == g and s["rated"]]
        if g != "Equity":   # debt / hybrid: the benchmark is the peer median month
            pass
        W = WEIGHTS if g == "Equity" else WEIGHTS_OTHER
        if g != "Equity":
            for s in peers:
                s["m"]["ann_ret_ex"] = s["m"].get("ann_ret")
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
        order = sorted([s for s in peers if s.get("score") is not None], key=lambda s: -s["score"])
        n = len(order)
        for k, s in enumerate(order):
            s["rank"], s["of"] = k + 1, n
            top = (k + 1) / n
            ex_ok = (s["m"].get("ex3y") or 0) > 0 if g == "Equity" else True
            if top <= 0.10 and s["score"] >= 70 and ex_ok:
                t = "A+"
            elif top <= 0.30 and s["score"] >= 55:
                t = "A"
            elif top > 0.70:
                t = "C"
            else:
                t = "B"
            if t in ("A+", "A") and g == "Equity" and (s["m"].get("ex3y") or 0) <= 0:
                t = "B"
            if t in ("A+", "A") and (s["m"].get("flow12_pct") or 0) < -30:
                s["flag"] = "Assets shrinking: clients took out more than 30% of the money in the last 12 months"
                t = "B"
            s["tier"] = t
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
    # manager totals from every strategy APMI lists (not only the ones we show)
    tot = cur.groupby("manager").aum.agg(["sum", "count"])
    for m in mgrs.values():
        raw = [n for n in tot.index if mgr_slug(n) == m["slug"]]
        m["aum_all"] = round(float(sum(tot.loc[n, "sum"] for n in raw)), 1)
        m["n_all"] = int(sum(tot.loc[n, "count"] for n in raw))
    out = {"as_of": last, "first": min(df[df.month >= "2023-04"].month), "n_all": int(len(cur)),
           "n_all_d": int((cur.service == "D").sum()), "aum_all": round(float(cur.aum.sum()), 0),
           "bench": {k: {m: round(v, 3) for m, v in d.items() if m >= "2023-04"} for k, d in bench.items()},
           "strategies": strategies, "managers": sorted(mgrs.values(), key=lambda m: m["name"].lower())}
    (ROOT / "site/data").mkdir(exist_ok=True)
    (ROOT / "site/data/pms.json").write_text(json.dumps(out, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    rated = [s for s in strategies if s["rated"]]
    print(f"{len(strategies)} strategies shown, {len(rated)} rated, {len(mgrs)} managers; as of {last}")
    for g in sorted({s['group'] for s in rated}):
        tiers = [s.get("tier") for s in rated if s["group"] == g]
        print(" ", g, len(tiers), {t: tiers.count(t) for t in ("A+", "A", "B", "C")})


if __name__ == "__main__":
    build()
