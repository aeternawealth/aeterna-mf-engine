"""PMS strategies (APMI investment approaches): parse the monthly reports and compute track-record metrics.

Input: data/pms/raw/<YYYY-MM>_<Type>_<D|N>.txt, the APMI report tables saved by engine/pms_fetch.py.
Every return is APMI's: time-weighted, after fees and expenses, before the investor's tax; periods over a
year are annualised. AUM is in Rs crore at the month end.
"""
import html
import re
from pathlib import Path

import pandas as pd

COLS = ["r1m", "r3m", "r6m", "r1y", "r2y", "r3y", "r4y", "r5y", "rsi"]
HEAD = {"1 Month": "r1m", "3 Months": "r3m", "6 Months": "r6m", "1 Year": "r1y", "2 Years": "r2y",
        "3 Years": "r3y", "4 Years": "r4y", "5 Years": "r5y", "Since Inception": "rsi"}
TYPE = {"Equity": "Equity", "Debt": "Debt", "Hybrid": "Hybrid", "MultiAsset": "Multi Asset"}


def _clean(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<!--.*?-->|<[^>]+>", " ", s, flags=re.S))).strip()


def _num(x):
    x = (x or "").replace("₹", "").replace(",", "").strip()
    try:
        return float(x)
    except ValueError:
        return None


def parse_report(text: str) -> list[dict]:
    """One APMI report table -> rows. Header cells inside HTML comments (e.g. 9 Months) are not columns."""
    rows = re.findall(r"<tr.*?</tr>", text, re.S | re.I)
    if not rows:
        return []
    head = [_clean(h) for h in re.findall(r"<th[^>]*>(.*?)</th>", re.sub(r"<!--.*?-->", "", rows[0], flags=re.S), re.S)]
    out = []
    for r in rows[1:]:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", re.sub(r"<!--.*?-->", "", r, flags=re.S), re.S)
        if len(cells) != len(head):
            continue
        v = dict(zip(head, (_clean(c) for c in cells)))
        m = re.search(r"IAID=(\d+)", r)
        d = {"iaid": int(m.group(1)) if m else None, "manager": v.get("PMS Provider Name", ""),
             "strategy": v.get("IA Name", ""), "aum": _num(v.get("AUM (in INR Cr.)") or v.get("AUM(in INR Cr.)"))}
        for h, k in HEAD.items():
            d[k] = _num(v.get(h))
        out.append(d)
    return out


def load_raw(raw_dir: Path) -> pd.DataFrame:
    recs = []
    for p in sorted(Path(raw_dir).glob("*.txt")):
        m = re.match(r"(\d{4}-\d{2})_([A-Za-z]+)_([DN])\.txt$", p.name)
        if not m:
            continue
        for d in parse_report(p.read_text(encoding="utf-8", errors="ignore")):
            d.update(month=m.group(1), type=TYPE.get(m.group(2), m.group(2)), service=m.group(3))
            recs.append(d)
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df = df.dropna(subset=["iaid"]).drop_duplicates(["iaid", "month", "service"])
    return df.sort_values(["iaid", "month"]).reset_index(drop=True)


# ---------------------------------------------------------------- track-record metrics
import math


def monthly_series(df: pd.DataFrame) -> pd.DataFrame:
    """Strategy x month table of 1-month returns (%), one column per month, from each month's report."""
    s = df[df.r1m.notna()].pivot_table(index="iaid", columns="month", values="r1m", aggfunc="first")
    return s.reindex(columns=sorted(s.columns))


def _chain(rets):
    g = 1.0
    for r in rets:
        g *= 1 + r / 100
    return g


def metrics(ser: pd.Series, bench: dict, min_months=24) -> dict:
    """Track record from monthly returns (%) against a benchmark's monthly returns (% by month).
    Only months where both exist count. None where the record is too short."""
    pairs = [(m, ser[m], bench[m]) for m in ser.index if pd.notna(ser[m]) and m in bench]
    n = len(pairs)
    out = {"months": n}
    if n < min_months:
        return out
    r = [p[1] for p in pairs]
    b = [p[2] for p in pairs]
    ex = [x - y for x, y in zip(r, b)]
    out["hit_m"] = sum(e > 0 for e in ex) / n                       # share of months ahead of the benchmark
    roll = [(_chain(r[i - 12:i]) - _chain(b[i - 12:i])) for i in range(12, n + 1)]
    out["hit_12m"] = sum(x > 0 for x in roll) / len(roll)            # share of rolling 12-month windows ahead
    out["worst_12m_ex"] = min(roll) * 100                            # worst 12-month gap to the benchmark (pp)
    mu = sum(ex) / n
    sd = math.sqrt(sum((e - mu) ** 2 for e in ex) / (n - 1)) if n > 1 else 0
    out["ir"] = (mu * 12) / (sd * math.sqrt(12)) if sd else None    # information ratio, annualised
    down = [(x, y) for x, y in zip(r, b) if y < 0]
    up = [(x, y) for x, y in zip(r, b) if y > 0]
    out["down_capture"] = (sum(x for x, _ in down) / sum(y for _, y in down)) if down else None
    out["up_capture"] = (sum(x for x, _ in up) / sum(y for _, y in up)) if up else None
    peak, g, dd = 1.0, 1.0, 0.0
    for x in r:
        g *= 1 + x / 100
        peak = max(peak, g)
        dd = min(dd, g / peak - 1)
    out["max_dd"] = dd * 100                                         # worst fall, month-end to month-end (%)
    out["ann_ret"] = (_chain(r) ** (12 / n) - 1) * 100
    out["ann_bench"] = (_chain(b) ** (12 / n) - 1) * 100
    return out
