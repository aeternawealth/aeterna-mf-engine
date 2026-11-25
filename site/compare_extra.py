"""Extra sections for the fund-vs-fund comparison pages (Nov 2026).

Google crawled 145 comparison pages and indexed none: each was one table of numbers in the same template. These
sections give each pair facts no other pair has, all worked out from our own data:
- calendar-year returns of both funds and their index (month-end NAVs, /data/series)
- the market's falls since 2018 (Nifty 500 TRI, 10% or more from a month-end peak): each fund's fall and the
  12 months after the low
- what each fund holds that the other does not, and their biggest common holdings (latest monthly portfolios)
- how the two portfolios differ (size mix, concentration, cash, distance from the index)
- a written reading of the record, fund by fund, with no "better" claim

Regular plans are shown first (the plans Aeterna distributes); cost appears only as plain data.
"""
import json
from functools import lru_cache

FALL_MIN = 0.10          # a market fall: the Nifty 500 TRI 10% or more below its month-end peak
FALL_FROM = "2018-01"
MARKET = "NIFTY 500"


def _pct(v, d=1):
    return "–" if v is None else f"{v * 100:.{d}f}%"


def _spct(v, d=1):
    return "–" if v is None else f"{'+' if v >= 0 else '−'}{abs(v) * 100:.{d}f}%"


@lru_cache(maxsize=None)
def _load(path):
    try:
        return json.loads(open(path, encoding="utf-8").read())
    except Exception:
        return None


def nav_series(B, code):
    """month list and month-end NAVs of one plan, or (None, None). B.SERIES_FILE maps int code -> series file stem."""
    SF = getattr(B, "SERIES_FILE", {}) or {}
    try:
        stem = SF.get(int(code))
    except (TypeError, ValueError):
        stem = None
    if not stem:
        return None, None
    d = _load(str(B.S / "data" / "series" / f"{stem}.json"))
    v = (d or {}).get("nav", {}).get(str(code))
    return (d.get("months"), v) if v else (None, None)


def bench_series(B):
    d = _load(str(B.S / "data" / "series" / "bench.json"))
    return (d.get("months"), d.get("tri", {})) if d else (None, {})


def _at(months, vals, m):
    try:
        x = vals[months.index(m)]
        return x if x else None
    except (ValueError, IndexError, TypeError, AttributeError):
        return None


def _ret(months, vals, m0, m1):
    a, b = _at(months, vals, m0), _at(months, vals, m1)
    return b / a - 1 if a and b else None


def calendar_years(months, vals, last_n=6):
    """{label: return} for the last full calendar years and the current year to date"""
    if not months or not vals:
        return {}
    last = months[-1]
    y1 = int(last[:4])
    out = {}
    for y in range(y1 - last_n, y1):
        out[str(y)] = _ret(months, vals, f"{y - 1}-12", f"{y}-12")
    if last[5:] != "12":
        out[f"{y1} so far"] = _ret(months, vals, f"{y1 - 1}-12", last)
    return out


def market_falls(B):
    """[(peak month, low month, fall)] for the Nifty 500 since FALL_FROM"""
    m, tri = bench_series(B)
    v = tri.get(MARKET) if tri else None
    if not m or not v or FALL_FROM not in m:
        return []
    ep, pk = [], m.index(FALL_FROM)
    for i in range(pk, len(m)):
        if v[i] is None:
            continue
        if v[pk] is None or v[i] >= v[pk]:
            pk = i
            continue
        dd = v[i] / v[pk] - 1
        if dd <= -FALL_MIN:
            if not ep or ep[-1][0] != m[pk]:
                ep.append([m[pk], m[i], dd])
            elif dd < ep[-1][2]:
                ep[-1][1], ep[-1][2] = m[i], dd
    return [tuple(e) for e in ep]


def _mon(m):
    import calendar
    return f"{calendar.month_abbr[int(m[5:])]} {m[:4]}"


def _plus12(months, m):
    try:
        i = months.index(m) + 12
        return months[i] if i < len(months) else None
    except ValueError:
        return None


def _clean(n):
    try:
        from stock_pages import clean_name
        return clean_name(n)
    except Exception:
        return n


def holdings_diff(hold_a, hold_b, n=6):
    """(only in A, only in B, common) as [(name, weight a, weight b)], by weight"""
    def norm(rows):
        d = {}
        for r in rows or []:
            if len(r) >= 3 and r[0] and isinstance(r[2], (int, float)) and r[2] > 0:
                d[r[0]] = (_clean(r[1] or r[0]), float(r[2]))
        return d
    A, Bm = norm(hold_a), norm(hold_b)
    only_a = sorted(((A[k][0], A[k][1], None, k) for k in A if k not in Bm), key=lambda x: -x[1])[:n]
    only_b = sorted(((Bm[k][0], None, Bm[k][1], k) for k in Bm if k not in A), key=lambda x: -x[2])[:n]
    common = sorted(((A[k][0], A[k][1], Bm[k][1], k) for k in A if k in Bm), key=lambda x: -(x[1] + x[2]))[:n]
    return only_a, only_b, common


def sections(B, a, b, ra, rb, hold, name_fn, stock_url=None):
    """HTML for the extra sections. a, b: the two funds (Regular plan where it exists: ra, rb); hold: pair_key -> rows."""
    out, facts = [], []
    na, nb = a["_name"], b["_name"]
    e = B.e
    # 1. calendar years
    ma, va = nav_series(B, ra["code"])
    mb, vb = nav_series(B, rb["code"])
    bm, tri = bench_series(B)
    bk = ra.get("benchmark") if ra.get("benchmark") in (tri or {}) else None
    ya, yb = calendar_years(ma, va), calendar_years(mb, vb)
    yi = calendar_years(bm, tri.get(bk)) if bk else {}
    yrs = [y for y in ya if ya.get(y) is not None or yb.get(y) is not None]
    if len(yrs) >= 3:
        win_a = sum(1 for y in yrs if ya.get(y) is not None and yb.get(y) is not None and ya[y] > yb[y])
        both = sum(1 for y in yrs if ya.get(y) is not None and yb.get(y) is not None)
        rows = "".join(f"<tr><td class='l'>{y}</td><td class='num'>{_pct(ya.get(y))}</td><td class='num'>{_pct(yb.get(y))}</td>"
                       + (f"<td class='num muted'>{_pct(yi.get(y))}</td>" if yi else "") + "</tr>" for y in yrs)
        lead = (f"Year by year, {e(na)} was ahead in {win_a} of {both} years and {e(nb)} in {both - win_a}." if both else "")
        out.append(f"<h2 class='cx-h'>Year by year</h2><p>{lead} Calendar-year returns, Regular plans, from month-end NAVs.</p>"
                   f"<div class='tablewrap'><table class='cmp'><thead><tr><th class='l'>Year</th><th>{e(na)}</th><th>{e(nb)}</th>"
                   + (f"<th>{e(B.iname(bk))} TRI</th>" if yi else "") + f"</tr></thead><tbody>{rows}</tbody></table></div>")
        if both:
            facts.append(lead)
    # 2. market falls
    falls = market_falls(B)
    frows, fall_notes = [], []
    for pk, lo, dd in falls:
        fa, fb = _ret(ma, va, pk, lo), _ret(mb, vb, pk, lo)
        if fa is None and fb is None:
            continue
        p12 = _plus12(bm or [], lo)
        aa, ab = (_ret(ma, va, lo, p12), _ret(mb, vb, lo, p12)) if p12 else (None, None)
        frows.append(f"<tr><td class='l'>{_mon(pk)} to {_mon(lo)}<small class='muted' style='display:block'>Nifty 500 {_pct(dd, 0)}</small></td>"
                     f"<td class='num'>{_pct(fa)}</td><td class='num'>{_pct(fb)}</td><td class='num'>{_pct(aa)}</td><td class='num'>{_pct(ab)}</td></tr>")
        if fa is not None and fb is not None and abs(fa - fb) >= 0.02:
            less = na if fa > fb else nb
            fall_notes.append(f"In the fall from {_mon(pk)} to {_mon(lo)}, {e(less)} lost less ({_pct(max(fa, fb))} against {_pct(min(fa, fb))}).")
    if frows:
        out.append("<h2 class='cx-h'>In the market's falls, and the year after</h2>"
                   "<p>Every fall of 10% or more in the Nifty 500 since 2018, measured from the month-end high to the month-end low, "
                   "and what each fund did in the 12 months after the low. Funds that fall less do not always recover faster.</p>"
                   f"<div class='tablewrap'><table class='cmp'><thead><tr><th class='l'>Market fall</th><th>{e(na)}<small class='muted' style='display:block;font-weight:400'>in the fall</small></th>"
                   f"<th>{e(nb)}<small class='muted' style='display:block;font-weight:400'>in the fall</small></th>"
                   f"<th>{e(na)}<small class='muted' style='display:block;font-weight:400'>next 12 months</small></th>"
                   f"<th>{e(nb)}<small class='muted' style='display:block;font-weight:400'>next 12 months</small></th></tr></thead>"
                   f"<tbody>{''.join(frows)}</tbody></table></div>" + (f"<p style='margin-top:10px'>{' '.join(fall_notes[-2:])}</p>" if fall_notes else ""))
        facts += fall_notes[-1:]
    # 3. holdings
    ha, hb = hold.get(a.get("pair_key")), hold.get(b.get("pair_key"))
    if ha and hb:
        oa, ob, cm = holdings_diff(ha, hb)
        link = lambda r: name_fn(r[0], r[3]) if name_fn else e(r[0])

        def li(rows, i):
            return "".join(f"<li>{link(r)} <span class='muted'>{r[i]:.1f}%</span></li>" for r in rows)
        cols = []
        if oa:
            cols.append(f"<div class='card'><b>Only in {e(na)}</b><ul class='cx-ul'>{li(oa, 1)}</ul></div>")
        if ob:
            cols.append(f"<div class='card'><b>Only in {e(nb)}</b><ul class='cx-ul'>{li(ob, 2)}</ul></div>")
        common = "".join(f"<tr><td class='l'>{link(r)}</td><td class='num'>{r[1]:.1f}%</td><td class='num'>{r[2]:.1f}%</td></tr>" for r in cm)
        mon = a.get("holdings_month") or b.get("holdings_month")
        out.append(f"<h2 class='cx-h'>What each fund owns</h2><p>From the latest monthly portfolios{(' (' + B.mon(mon) + ')') if mon else ''}: "
                   "the largest holdings one fund has and the other does not, and the largest stocks both hold, as a share of each fund.</p>"
                   + (f"<div class='grid g2' style='margin-top:12px'>{''.join(cols)}</div>" if cols else "")
                   + (f"<div class='tablewrap' style='margin-top:14px'><table class='cmp'><thead><tr><th class='l'>Held by both</th><th>{e(na)}</th><th>{e(nb)}</th></tr></thead><tbody>{common}</tbody></table></div>" if common else ""))
    # 4. how the portfolios differ
    diffs = []
    for key, label, fmt, gap in (("large_pct", "in large caps", lambda v: f"{v:.0f}%", 10), ("small_pct", "in small caps", lambda v: f"{v:.0f}%", 8),
                                 ("top10_pct", "in its top 10 stocks", lambda v: f"{v:.0f}%", 8), ("cash_other_pct", "in cash and other assets", lambda v: f"{v:.0f}%", 4),
                                 ("active_share", "different from its index (active share)", lambda v: f"{v:.0f}%", 10), ("n_stocks", "stocks", lambda v: f"{v:.0f}", 15)):
        x, y = a.get(key), b.get(key)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and abs(x - y) >= gap:
            hi, lo, vh, vl = (na, nb, x, y) if x > y else (nb, na, y, x)
            diffs.append(f"{e(hi)} has {fmt(vh)} {label}, against {fmt(vl)} for {e(lo)}." if key != "n_stocks"
                         else f"{e(hi)} holds {fmt(vh)} stocks, against {fmt(vl)} for {e(lo)}.")
    if diffs:
        out.append("<h2 class='cx-h'>How the two portfolios differ</h2><ul class='cx-ul' style='padding-left:20px'>" + "".join(f"<li>{d}</li>" for d in diffs) + "</ul>")
    # 5. the record, fund by fund
    def reading(f, r):
        bits = []
        if r.get("tier") and r.get("tier") != "Unrated" and r.get("peer_rank") and (r.get("peer_count") or 0) > 1:
            bits.append(f"rated {r['tier']} (Regular plan), #{int(r['peer_rank'])} of {int(r['peer_count'])} in its category this month")
        if r.get("excess_3Y") is not None:
            bits.append(f"{_spct(r['excess_3Y'])} a year against its index over 3 years")
        if r.get("roll3y_hit_rate") is not None:
            bits.append(f"ahead of its index in {_pct(r['roll3y_hit_rate'], 0)} of rolling 3-year periods")
        if r.get("downside_capture_3y") is not None:
            bits.append(f"took {r['downside_capture_3y']:.0f}% of the index's falls in down months")
        return f"<p><b>{e(f['_name'])}</b>: " + "; ".join(bits) + ".</p>" if bits else ""
    rd = reading(a, ra) + reading(b, rb)
    if rd:
        out.append("<h2 class='cx-h'>The record, fund by fund</h2>" + rd
                   + "<p class='muted' style='font-size:14px'>Ratings describe each fund's record against its own index and category; they are not a forecast. "
                     "Which one fits depends on your goal and what you already hold, which is what our free portfolio review looks at.</p>")
    css = "<style>.cx-h{font-size:24px;margin-top:34px}.cx-ul{margin:8px 0 0;padding-left:18px;display:grid;gap:4px}.cx-ul li{font-size:14.5px}</style>"
    return (css + "".join(out)) if out else "", facts


# ------------------------------------------------------------------ fund pages and category pages (Nov 2026)
_PEER_YEARS = {}


def peer_years(B, funds, category, plan):
    """{code: {year label: return}} for every plan of this category and plan type with a NAV series (cached)"""
    k = (category, plan)
    if k not in _PEER_YEARS:
        out = {}
        for g in funds:
            if g.get("category") == category and g.get("plan_type") == plan:
                m, v = nav_series(B, g["code"])
                if m:
                    out[g["code"]] = calendar_years(m, v)
        _PEER_YEARS[k] = out
    return _PEER_YEARS[k]


def _median(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


_FALL = {}


def _fall_col(B, funds, category, plan, pk, lo):
    k = (category, plan, pk, lo)
    if k not in _FALL:
        col = []
        for g in funds:
            if g.get("category") == category and g.get("plan_type") == plan:
                gm, gv = nav_series(B, g["code"])
                x = _ret(gm, gv, pk, lo) if gm else None
                if x is not None:
                    col.append(x)
        _FALL[k] = col
    return _FALL[k]


def fund_sections(B, f, funds):
    """'Year by year' and 'In the market's falls' for one fund page: the fund, the category median, its rank that
    year among plans of the same type, and its index."""
    if B.asset_class(f["category"]) not in ("Equity", "Hybrid") or f["category"] == "Arbitrage":
        return ""     # debt and arbitrage years differ by fractions of a percent: noise, not information
    m, v = nav_series(B, f["code"])
    if not m:
        return ""
    e = B.e
    nm = f["_name"].rstrip(" -")
    peers = peer_years(B, funds, f.get("category"), f.get("plan_type"))
    mine = calendar_years(m, v)
    bm, tri = bench_series(B)
    bk = f.get("benchmark") if f.get("benchmark") in (tri or {}) else None
    yi = calendar_years(bm, tri.get(bk)) if bk else {}
    rows, ahead, n_cmp = [], 0, 0
    for y, r in mine.items():
        if r is None:
            continue
        col = [p.get(y) for p in peers.values() if p.get(y) is not None]
        med = _median(col)
        rank = 1 + sum(1 for x in col if x > r) if col else None
        if med is not None:
            n_cmp += 1
            ahead += r > med
        rows.append(f"<tr><td class='l'>{y}</td><td class='num'>{_pct(r)}</td><td class='num'>{_pct(med)}</td>"
                    f"<td class='num'>{(str(rank) + ' of ' + str(len(col))) if rank else '–'}</td>"
                    + (f"<td class='num muted'>{_pct(yi.get(y))}</td>" if yi else "") + "</tr>")
    if len(rows) < 2:
        return ""
    lc = f["category"] if f["category"] == "ELSS" else f["category"].lower()
    out = (f"<h2 style='margin-top:36px;font-size:26px'>Year by year</h2>"
           f"<p style='margin-top:8px'>{e(nm)} beat the median {e(lc)} fund ({e(f.get('plan_type') or '')} plans) in {ahead} of the {n_cmp} calendar years shown. "
           "Returns from month-end NAVs; the rank counts every plan of the same type in the category that year.</p>"
           "<div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Year</th><th>This fund</th><th>Category median</th><th>Rank</th>"
           + (f"<th>{e(B.iname(bk))} TRI</th>" if yi else "") + f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>")
    yp = getattr(B, "MADE_YEARS", {}).get("Value / Contra" if f["category"] in ("Value", "Contra") else f["category"])
    if yp:
        out += f"<p style='margin-top:8px'><a href='{yp}'>Every {e(lc)} fund, year by year</a></p>"
    # market falls: equity and hybrid funds only
    if B.asset_class(f["category"]) in ("Equity", "Hybrid") and f["category"] != "Arbitrage":
        frows = []
        for pk, lo, dd in market_falls(B):
            r = _ret(m, v, pk, lo)
            if r is None:
                continue
            col = _fall_col(B, funds, f.get("category"), f.get("plan_type"), pk, lo)
            rank = 1 + sum(1 for x in col if x > r)
            p12 = _plus12(bm or [], lo)
            after = _ret(m, v, lo, p12) if p12 else None
            frows.append(f"<tr><td class='l'>{_mon(pk)} to {_mon(lo)}<small class='muted' style='display:block'>Nifty 500 {_pct(dd, 0)}</small></td>"
                         f"<td class='num'>{_pct(r)}</td><td class='num'>{rank} of {len(col)}</td><td class='num'>{_pct(after)}</td></tr>")
        if frows:
            out += ("<h2 style='margin-top:36px;font-size:26px'>In the market's falls</h2>"
                    "<p style='margin-top:8px'>Every fall of 10% or more in the Nifty 500 since 2018, from the month-end high to the month-end low: "
                    "how much this fund lost, where that placed it in its category (1 = lost least), and what it made in the 12 months after the low.</p>"
                    "<div class='tablewrap' style='margin-top:12px'><table><thead><tr><th class='l'>Market fall</th><th>This fund</th><th>Rank in the fall</th><th>Next 12 months</th></tr></thead>"
                    f"<tbody>{''.join(frows)}</tbody></table></div>")
    return out


YEAR_CATS = ["Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "Multi Cap", "Flexi Cap", "Focused", "ELSS", "Value / Contra",
             "Dividend Yield", "Aggressive Hybrid", "Balanced Advantage", "Multi Asset Allocation"]


def year_path(B, c):
    return f"/mutual-funds/{B.slug(c)}/year-by-year/"


def category_year_pages(B, funds, urls, as_of):
    """/mutual-funds/<category>/year-by-year/: every Regular plan's calendar-year returns, the five highest each year,
    and each fund in the market's falls since 2018. Facts only: the highest return in a year is not advice."""
    e = B.e
    made = {}
    falls = market_falls(B)
    bm, tri = bench_series(B)
    for c in YEAR_CATS:
        cats = ("Value / Contra", "Value", "Contra") if c == "Value / Contra" else (c,)
        F = [f for f in funds if f.get("category") in cats and f.get("plan_type") == "Regular"]
        rows = []
        for f in F:
            m, v = nav_series(B, f["code"])
            if not m:
                continue
            ys = calendar_years(m, v)
            fl = [(_ret(m, v, pk, lo), _ret(m, v, lo, _plus12(bm or [], lo)) if _plus12(bm or [], lo) else None) for pk, lo, _ in falls]
            if sum(1 for x in ys.values() if x is not None) >= 2:
                rows.append((f, ys, fl))
        if len(rows) < 6:
            continue
        years = list(rows[0][1].keys())
        full = [y for y in years if "so far" not in y]
        bk = next((f.get("benchmark") for f, _, _ in rows if f.get("benchmark") in (tri or {})), None)
        yi = calendar_years(bm, tri.get(bk)) if bk else {}
        last_full = full[-1] if full else years[-1]
        rows.sort(key=lambda r: -(r[1].get(last_full) if r[1].get(last_full) is not None else -9))
        lc = c if c == "ELSS" else c.lower()
        # the five highest each year
        tops = []
        for y in reversed(full[-4:]):
            col = sorted(((r[1].get(y), r[0]) for r in rows if r[1].get(y) is not None), key=lambda x: -x[0])
            if len(col) < 5:
                continue
            med = _median([x for x, _ in col])
            tops.append(f"<div class='card'><b>{y}</b><span class='muted' style='font-size:13px;display:block'>{len(col)} funds · median {_pct(med)}"
                        + (f" · {e(B.iname(bk))} TRI {_pct(yi.get(y))}" if yi.get(y) is not None else "") + "</span><ol class='cx-ul'>"
                        + "".join(f"<li><a href='{f['_url']}'>{e(f['_name'].rstrip(' -'))}</a> <span class='muted'>{_pct(x)}</span></li>" for x, f in col[:5])
                        + "</ol></div>")
        head = "".join(f"<th>{y}</th>" for y in years)
        body_rows = "".join(f"<tr><td class='l'><a href='{f['_url']}'>{e(f['_name'].rstrip(' -'))}</a> {B.tier_badge(f.get('tier'))}</td>"
                            + "".join(f"<td class='num'>{_pct(ys.get(y))}</td>" for y in years) + "</tr>" for f, ys, _ in rows)
        idx_row = (f"<tr><td class='l muted'>{e(B.iname(bk))} TRI (index)</td>" + "".join(f"<td class='num muted'>{_pct(yi.get(y))}</td>" for y in years) + "</tr>") if yi else ""
        # market falls
        frows = ""
        if falls and B.asset_class(c) in ("Equity", "Hybrid"):
            fr = sorted(rows, key=lambda r: -(r[2][-1][0] if r[2][-1][0] is not None else -9))
            fh = "".join(f"<th>{_mon(pk)} to {_mon(lo)}<small class='muted' style='display:block;font-weight:400'>Nifty 500 {_pct(dd, 0)}</small></th>" for pk, lo, dd in falls)
            frows = ("<h2 class='cx-h'>In the market's falls</h2><p>How much each fund lost in every fall of 10% or more in the Nifty 500 since 2018 "
                     "(month-end high to month-end low), and in brackets what it made in the 12 months after the low. Sorted by the most recent fall, smallest loss first.</p>"
                     f"<div class='tablewrap'><table class='cmp yy'><thead><tr><th class='l'>Fund</th>{fh}</tr></thead><tbody>"
                     + "".join(f"<tr><td class='l'><a href='{f['_url']}'>{e(f['_name'].rstrip(' -'))}</a></td>"
                               + "".join(f"<td class='num'>{_pct(a)}<small class='muted' style='display:block'>{('(' + _pct(b) + ')') if b is not None else ''}</small></td>" for a, b in fl)
                               + "</tr>" for f, _, fl in fr)
                     + "</tbody></table></div>")
        path = year_path(B, c)
        ylast = years[-1]
        desc = (f"Calendar-year returns of every {lc} fund (Regular plans), {years[0]} to {ylast}: the five highest each year, the category median, "
                f"the index, and how each fund did in the market's falls since 2018.")
        intro = (f"Every {lc} fund's return in each calendar year, from month-end NAVs (Regular plans, growth option), sorted by {last_full}. "
                 "A fund at the top one year is often in the middle the next, which is why our ratings look at the whole record rather than one year.")
        body = f"""<section class="band" style="padding-top:28px"><div class="wrap">
<style>.cx-h{{font-size:26px;margin-top:36px}}.cx-ul{{margin:8px 0 0;padding-left:20px;display:grid;gap:4px}}.cx-ul li{{font-size:14.5px}}.yy td.l{{min-width:170px}}</style>
<nav aria-label="Breadcrumb" class="muted" style="font-size:13.5px"><a href="/mutual-funds/">Mutual funds</a> › <a href="/mutual-funds/{B.slug(c)}/">{e(c)}</a> › Year by year</nav>
<h1 style="font-size:clamp(28px,4vw,42px);margin-top:14px">{e(c)} fund returns, year by year</h1>
<p class="lede" style="margin-top:12px">{e(intro)} Data to {B.dmy(as_of)}.</p>
<h2 class="cx-h">The five highest returns each year</h2>
<div class="grid g2" style="margin-top:12px">{''.join(tops)}</div>
<h2 class="cx-h">Every fund, every year</h2>
<div class="tablewrap" style="margin-top:12px"><table class="cmp yy"><thead><tr><th class="l">Fund</th>{head}</tr></thead><tbody>{idx_row}{body_rows}</tbody></table></div>
{frows}
<div class="row" style="margin-top:22px"><a class="btn primary" href="/mutual-funds/{B.slug(c)}/">{e(c)} fund ratings</a><a class="btn" href="/invest/portfolio-review/">Free portfolio review</a></div>
<p class="note" style="margin-top:28px">Past returns do not predict future returns. This page lists facts, not recommendations to buy or sell any fund.</p>
</div></section>"""
        B.write(path, B.page(f"{c} fund returns year by year, {years[0]} to {ylast.replace(' so far', '')} | Aeterna Wealth", desc, path, body,
                             (B.crumbs([("Mutual funds", "/mutual-funds/"), (c, f"/mutual-funds/{B.slug(c)}/"), ("Year by year", path)]),)))
        urls.append((path, "monthly", "0.7"))
        made[c] = path
    return made
