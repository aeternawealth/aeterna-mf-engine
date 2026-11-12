"""From a portfolio and a client profile to a plan: target shape, a verdict on every holding, exits (with tax, exit
load and timing), where new money goes (SIP, lump sum, STP), and a thesis for every change of shape.
Rules: docs/rebalance_principles.md; numbers: config.py."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import config as C
from . import data as D
from . import tax as T
from .cas import Holding, Portfolio

CATEGORY_NOTE = {
    "Large Cap": "the 100 largest companies (at least 80%)",
    "Index Fund": "an index, at index cost",
    "Flexi Cap": "any mix of large, mid and small companies, at the manager's choice",
    "Multi Cap": "at least 25% each in large, mid and small companies",
    "Focused": "at most 30 stocks, any size",
    "Value / Contra": "out-of-favour or cheaply valued companies",
    "ELSS": "any size, with a 3-year lock-in and a tax deduction under the old regime",
    "Large & Mid Cap": "at least 35% each in large and mid companies",
    "Mid Cap": "companies ranked 101-250 (at least 65%)",
    "Small Cap": "companies ranked beyond 250 (at least 65%)",
    "Sectoral/Thematic": "one sector or theme",
    "Arbitrage": "hedged cash-futures trades: near-liquid returns, taxed as equity",
}
REVERSE_IF = {
    "small": "the goal comes within 7 years, or a 35-45% fall in small caps would force a sale",
    "midlm": "the goal comes within 5 years, or mid-cap valuations reach the top decile of their history while the goal is near",
    "flexi": "the client's horizon or risk profile changes",
    "large": "the client moves to a more aggressive profile with a long horizon",
    "parked": "the goal is more than 3 years away and the client is comfortable with equity swings",
    "debt": "the goal moves further out, or rates make arbitrage better after tax",
}


@dataclass
class Client:
    name: str = ""
    goal: str = "growth"                 # growth | retirement | education | house | other
    target_today: float | None = None    # rupees in today's money
    target_year: int | None = None
    sip: float = 0.0
    lumpsum: float = 0.0
    risk_attitude: str = "aggressive"
    risk_capacity: str = "very_aggressive"
    slab: float = 0.30
    ltcg_used: float = 0.0               # long-term equity gains already booked this financial year
    plan: str = "Regular"                # plan type for new money: Aeterna clients Regular, the founders Direct
    keep: list = field(default_factory=list)      # holdings the client wants kept (name parts or AMFI codes)
    emergency_reserve: float = 0.0       # rupees to leave in parked money (0 when the emergency fund is held elsewhere)
    stp_months: int | None = None
    inflation: float | None = None

    @property
    def profile(self) -> str:
        i = min(C.PROFILES.index(self.risk_attitude), C.PROFILES.index(self.risk_capacity))
        return C.PROFILES[i]


@dataclass
class Verdict:
    h: Holding
    action: str                          # "add" | "hold" | "stop" | "exit" | "deploy"
    reasons: list = field(default_factory=list)   # (code, text)
    when: str = ""
    sell_value: float = 0.0
    sell_now: float = 0.0                # part sold now (the rest later); equals sell_value when all is sold now
    cost_low: float = 0.0                # tax + exit load if undated units are long-term
    cost_high: float = 0.0               # ... if they are short-term (equal when lots are exact)
    tax_detail: dict = field(default_factory=dict)


@dataclass
class Plan:
    client: Client
    portfolio: Portfolio
    profile: str
    years: int | None
    target: dict                         # bucket -> share of the portfolio
    current: dict                        # bucket -> share now
    after: dict                          # bucket -> share after deploying 12 months of new money
    verdicts: list
    sip: list                            # (fund row, amount, bucket, why)
    deploy: list                         # (fund row, amount, bucket) from lump sum, exits and parked money
    stp_months: int
    theses: list
    warnings: list
    overlap: list                        # (fund a, fund b, share)
    amc_share: dict
    lookthrough_before: dict
    lookthrough_after: dict
    cat_before: dict
    cat_after: dict
    as_of: date


def glide(years: int | None, profile: str) -> float:
    cap = C.MAX_EQUITY[profile]
    if years is None:
        return cap
    pts = C.GLIDE
    if years <= pts[0][0]:
        return min(cap, pts[0][1])
    for (y0, e0), (y1, e1) in zip(pts, pts[1:]):
        if years <= y1:
            return min(cap, e0 + (e1 - e0) * (years - y0) / (y1 - y0))
    return cap


def _kept(client: Client, h: Holding) -> bool:
    for k in client.keep:
        if str(k).isdigit() and h.code == int(k):
            return True
        if str(k).lower() in h.name.lower():
            return True
    return False


def _fund_str(f) -> str:
    return f"{f['name']} ({f['plan_type']})"


def _tier(f) -> str:
    return "" if f is None else str(f.get("tier") or "")


def _num(x):
    try:
        x = float(x)
        return None if x != x else x
    except (TypeError, ValueError):
        return None


def _sale(h: Holding, value: float, on: date, client: Client, exempt_left: float):
    f = h.fund
    cls = T.tax_class(f)
    units = min(h.units, value / h.nav) if h.nav else 0
    gf = D.nav_on(h.code, C.TAX["equity"]["grandfather_date"]) if h.code else None
    sc = T.sell(h.lots, units, on, h.nav, cls=cls, category=h.category or "", code=h.code, grandfather_nav=gf)
    hi = T.tax_due(sc, cls, client.slab, exempt_left, unknown_as="ST")
    lo = T.tax_due(sc, cls, client.slab, exempt_left, unknown_as="LT")
    return sc, lo, hi


def build(port: Portfolio, client: Client, on: date | None = None) -> Plan:
    on = on or port.as_of
    profile = client.profile
    years = (client.target_year - on.year) if client.target_year else None
    warnings = list(port.warnings)
    total = port.value

    # ------------------------------------------------------------ target shape
    eq = glide(years, profile)
    target = {b: eq * w for b, w in C.EQUITY_MIX[profile].items()}
    non_eq_bucket = "parked" if (years is not None and years <= 3) or client.slab >= 0.20 else "debt"
    target[non_eq_bucket] = target.get(non_eq_bucket, 0) + (1 - eq)
    if client.goal != "growth" and years is not None and years < 0:
        warnings.append("The goal year has passed; the plan treats the money as needed now.")

    def shares(values: dict) -> dict:
        t = sum(values.values()) or 1
        return {k: v / t for k, v in values.items() if v > 0}

    cur_val: dict = {}
    for h in port.holdings:
        cur_val[h.bucket] = cur_val.get(h.bucket, 0) + h.value
    current = shares(cur_val)

    # ------------------------------------------------------------ verdict on each holding
    verdicts = []
    held_eq = [h for h in port.holdings if h.bucket in C.EQUITY_BUCKETS + ["thematic"]]
    for h in port.holdings:
        f, t = h.fund, _tier(h.fund)
        v = Verdict(h, "hold")
        if _kept(client, h):
            v.reasons.append(("keep", "kept at the client's request"))
        elif f is None:
            v.reasons.append(("data", "not in our fund data, so not rated; held"))
        elif h.bucket == "parked":
            v.action = "deploy"
            v.reasons.append(("R1", "parked money: earns about what a liquid fund pays"))
        elif t in C.EXIT_TIERS:
            v.action = "exit"
            rk = f"{int(f['peer_rank'])} of {int(f['peer_count'])}" if _num(f.get("peer_rank")) else ""
            why = f"rated C in {f['peer_group']}" + (f" (rank {rk})" if rk else "")
            fl = str(f.get("flags") or "")
            if "mandate" in fl:
                why += f"; its portfolio breaks the {f['category']} rule ({f.get('mandate_breaches')})"
            v.reasons.append(("R4", why))
        elif t == "Unrated" and h.value < C.SMALL_HOLDING * total:
            v.action = "exit"
            v.reasons.append(("R3", f"under {C.SMALL_HOLDING:.0%} of the portfolio and too new to rate: adds a fund without adding diversification"))
        elif t == "Unrated":
            v.reasons.append(("hold", f"too new to rate ({_num(f.get('age_years')) or 0:.1f} years); reviewed when it has a 3-year record"))
            v.action = "stop"
        elif t == "B":
            v.action = "stop"
            v.reasons.append(("hold", "rated B: held, but new money goes to A/A+ funds"))
        elif t in C.NEW_MONEY_TIERS:
            v.action = "add"
            v.reasons.append(("hold", f"rated {t} (rank {int(f['peer_rank'])} of {int(f['peer_count'])} in {f['peer_group']})"))
        if f is not None and f["plan_type"] == "Regular" and client.plan == "Direct" and v.action != "exit":
            o = D.other_plan(f)
            if o is not None and _num(f.get("ter")) and _num(o.get("ter")):
                v.reasons.append(("R5", f"Regular plan costs {f['ter'] - o['ter']:.2f}% a year more than Direct "
                                        f"(about ₹{h.value * (f['ter'] - o['ter']) / 100:,.0f} a year here)"))
                v.action = "exit" if v.action != "add" else v.action
        verdicts.append(v)

    # redundancy within a bucket: keep the best-rated funds, stop the rest
    for b in C.EQUITY_BUCKETS:
        live = [v for v in verdicts if v.h.bucket == b and v.action in ("add", "hold", "stop") and not _kept(client, v.h)]
        live.sort(key=lambda v: -(_num(v.h.fund.get("score")) or 0) if v.h.fund is not None else 0)
        for v in live[C.MAX_FUNDS_PER_BUCKET:]:
            if v.action != "add":
                v.reasons.append(("R3", f"one of {len(live)} funds in the {C.BUCKET_LABEL[b].lower()} sleeve: merge into fewer funds"))
                v.action = "exit"

    # ------------------------------------------------------------ exits: cost and timing (exemption used in order)
    exempt_left = max(0.0, C.TAX["equity"]["ltcg_exempt"] - client.ltcg_used)
    exits = sorted([v for v in verdicts if v.action == "exit"], key=lambda v: v.h.value)
    for v in exits:
        h = v.h
        sc, lo, hi = _sale(h, h.value, on, client, exempt_left)
        if sc.locked_units > 1e-6:
            v.when = "after the ELSS lock-in ends"
            v.reasons.append(("lock", f"{sc.locked_units:.1f} units are still in the 3-year ELSS lock-in"))
        v.sell_value = h.value
        v.cost_low = lo["tax"] + sc.load - sc.load_undated
        v.cost_high = hi["tax"] + sc.load
        v.tax_detail = {"gain": sc.gain, "load": sc.load, "tax_low": lo["tax"], "tax_high": hi["tax"],
                        "exempt_used": lo["exempt_used"], "exact": h.exact_lots}
        cheap = v.cost_high <= C.SELL_COST_OK * h.value
        later = T.cheaper_on(h.lots, on, h.nav, cls=T.tax_class(h.fund), category=h.category or "", code=h.code)
        broken = any(c == "R4" for c, _ in v.reasons)
        if v.when:
            pass
        elif cheap:
            v.when = "now"
        elif not h.exact_lots:
            v.when = "now for units held over a year; the rest as each turns 12 months old (check purchase dates)"
        elif later:
            mu = T.mature_units(h.lots, on, cls=T.tax_class(h.fund), category=h.category or "", code=h.code)
            if mu > 1e-6 and mu < h.units - 1e-6:
                # FIFO sells the oldest units first: sell those now, the rest once every lot is past its cost steps
                part, plo, phi = _sale(h, mu * h.nav, on, client, exempt_left)
                v.sell_now = mu * h.nav
                v.when = (f"now for ₹{mu * h.nav:,.0f} (units over a year old; cost ₹{phi['tax'] + part.load:,.0f}); "
                          f"the remaining ₹{h.value - mu * h.nav:,.0f} on or after {later:%d %b %Y}, when its tax and exit load fall "
                          f"(selling it all today would cost ₹{v.cost_high:,.0f})")
                exempt_left = max(0.0, exempt_left - plo["exempt_used"])
            else:
                v.when = f"on or after {later:%d %b %Y}, when its tax and exit load fall (selling today would cost ₹{v.cost_high:,.0f})"
        elif broken:
            v.when = "now (all units are already long-term)"
        else:
            v.when = "now"
        if v.when.startswith("now") and not v.sell_now:
            v.sell_now = v.sell_value
            exempt_left = max(0.0, exempt_left - lo["exempt_used"])

    # ------------------------------------------------------------ new money and where it goes
    exit_now = sum(v.sell_now for v in verdicts if v.action == "exit")
    parked_val = sum(v.h.value for v in verdicts if v.action == "deploy")
    kept = {}
    for v in verdicts:
        if v.action in ("add", "hold", "stop"):
            kept[v.h.bucket] = kept.get(v.h.bucket, 0) + v.h.value
        elif v.action == "exit":
            kept[v.h.bucket] = kept.get(v.h.bucket, 0) + v.h.value - v.sell_now
    horizon_sip = client.sip * C.DEPLOY_HORIZON_MONTHS
    total_after = total + client.lumpsum + horizon_sip
    parked_target = target.get("parked", 0) * total_after + client.emergency_reserve
    parked_keep = min(parked_val, parked_target)
    deployable = parked_val - parked_keep + exit_now + client.lumpsum
    kept["parked"] = kept.get("parked", 0) + parked_keep
    need = {b: max(0.0, target.get(b, 0) * total_after - kept.get(b, 0)) for b in list(C.EQUITY_BUCKETS) + ["debt", "parked"]}
    need = {b: x for b, x in need.items() if x > 1}
    if not need:
        need = {b: target[b] for b in target if target[b] > 0}
    tn = sum(need.values())

    # fund choice per bucket
    fdf = D.funds()
    chosen: dict = {}

    def ok_overlap(row, picked):
        for p in picked:
            o = D.overlap(row["pair_key"], p["pair_key"])
            if o is not None and o > C.OVERLAP_HIGH:
                return False
        return True

    # 1) funds already held and rated A/A+, best score first, one per fund house (a house style shows up across its
    #    funds), a second fund in a sleeve only when its overlap with the first is known to be low;
    # 2) sleeves still empty take the best-rated eligible fund not yet held.
    picked_all, used_amc = [], set()
    held_good = [v.h.fund for v in verdicts if v.action == "add" and v.h.bucket in need]
    held_good.sort(key=lambda f: -(_num(f.get("score")) or 0))
    for f in held_good:
        b = f["bucket"]
        picks = chosen.setdefault(b, [])
        if len(picks) >= C.MAX_FUNDS_PER_BUCKET or f["amc"] in used_amc:
            continue
        if picks and D.overlap(f["pair_key"], picks[0]["pair_key"]) is None:
            continue
        if ok_overlap(f, picked_all):
            picks.append(f)
            picked_all.append(f)
            used_amc.add(f["amc"])
    for b in sorted(need, key=lambda b: -need[b]):
        if chosen.get(b):
            continue
        cats = C.BUCKET_CATEGORIES.get(b) or C.NONEQUITY_CATEGORIES["short" if b == "parked" else "long"]
        pool = fdf[fdf.category.isin(cats) & (fdf.plan_type == client.plan) & fdf.tier.isin(C.NEW_MONEY_TIERS)
                   & (fdf.gate == "ok")].copy()
        pool = pool[(pd.to_numeric(pool.aum_cr, errors="coerce") >= 500) & (pd.to_numeric(pool.age_years, errors="coerce") >= 3)]
        for _, f in pool.sort_values("score", ascending=False).iterrows():
            if f["amc"] not in used_amc and ok_overlap(f, picked_all):
                chosen[b] = [f]
                picked_all.append(f)
                used_amc.add(f["amc"])
                break
        else:
            chosen.pop(b, None)
            warnings.append(f"No A/A+ fund found for the {C.BUCKET_LABEL[b].lower()} sleeve; its share of new money is spread over the others.")
    chosen = {b: p for b, p in chosen.items() if p}
    picked_codes = {int(f["code"]) for f in picked_all}
    for v in verdicts:
        if v.action == "add" and v.h.code not in picked_codes:
            v.action = "hold"
            v.reasons.append(("hold", "held; this month's new money goes to the funds below (one per fund house, best-rated first)"))

    tn = sum(need[b] for b in chosen) or 1
    sip, deploy = [], []
    for b, picks in chosen.items():
        share = need[b] / tn
        n = len(picks)
        for f in picks:
            amt = client.sip * share / n
            sip.append([f, amt, b])
            deploy.append([f, deployable * share / n, b])
    # round SIPs; fold amounts below the minimum into the largest SIP
    sip = [s for s in sip if s[1] > 0]
    sip.sort(key=lambda s: -s[1])
    for s in sip[1:]:
        if s[1] < C.MIN_SIP_PER_FUND:
            sip[0][1] += s[1]
            s[1] = 0
    sip = [s for s in sip if s[1] > 0]
    if sip:
        r = [round(s[1] / C.SIP_ROUND) * C.SIP_ROUND for s in sip]
        r[0] += client.sip - sum(r)
        for s, x in zip(sip, r):
            s[1] = x
    deploy = [d for d in deploy if d[1] > 1]

    # ------------------------------------------------------------ after-state (12 months of new money, no market moves)
    after_val = dict(kept)
    for f, a, b in sip:
        after_val[b] = after_val.get(b, 0) + a * C.DEPLOY_HORIZON_MONTHS
    for f, a, b in deploy:
        after_val[b] = after_val.get(b, 0) + a
    after_val["parked"] = after_val.get("parked", 0)
    after = shares(after_val)

    # categories before/after and look-through
    def fund_values_after():
        vals = {}
        for v in verdicts:
            if v.action in ("add", "hold", "stop"):
                vals[v.h.code] = vals.get(v.h.code, 0) + v.h.value
            elif v.action == "exit" and v.h.value - v.sell_now > 1:
                vals[v.h.code] = vals.get(v.h.code, 0) + v.h.value - v.sell_now
            elif v.action == "deploy":
                vals[v.h.code] = vals.get(v.h.code, 0) + v.h.value * (parked_keep / parked_val if parked_val else 0)
        for f, a, b in sip:
            vals[int(f["code"])] = vals.get(int(f["code"]), 0) + a * C.DEPLOY_HORIZON_MONTHS
        for f, a, b in deploy:
            vals[int(f["code"])] = vals.get(int(f["code"]), 0) + a
        return vals

    before_vals = {}
    for h in port.holdings:
        if h.code:
            before_vals[h.code] = before_vals.get(h.code, 0) + h.value
    after_vals = fund_values_after()

    def by_cat(vals):
        out = {}
        for c, x in vals.items():
            cat = fdf.loc[c, "category"] if c in fdf.index else "Other"
            out[cat] = out.get(cat, 0) + x
        return shares(out)

    def look(vals):
        tot, mix = 0.0, {"large": 0.0, "mid": 0.0, "small": 0.0, "other": 0.0}
        for c, x in vals.items():
            if c not in fdf.index or fdf.loc[c, "bucket"] not in C.EQUITY_BUCKETS + ["thematic"]:
                continue
            r = fdf.loc[c]
            l, m, s = (_num(r.get("large_pct")), _num(r.get("mid_pct")), _num(r.get("small_pct")))
            if l is None:
                l, m, s = {"Small Cap": (5, 20, 70), "Mid Cap": (15, 70, 12), "Large Cap": (88, 10, 1)}.get(r["category"], (55, 25, 18))
            tot += x
            mix["large"] += x * l / 100
            mix["mid"] += x * m / 100
            mix["small"] += x * s / 100
            mix["other"] += x * max(0, 100 - l - m - s) / 100
        return {k: v / tot for k, v in mix.items()} if tot else {}

    cat_before, cat_after = by_cat(before_vals), by_cat(after_vals)

    # overlap and fund-house concentration of the equity funds held after the plan
    eq_codes = [c for c in after_vals if c in fdf.index and fdf.loc[c, "bucket"] in C.EQUITY_BUCKETS and after_vals[c] > 0.01 * total]
    ov = []
    for i, a in enumerate(eq_codes):
        for b in eq_codes[i + 1:]:
            o = D.overlap(fdf.loc[a, "pair_key"], fdf.loc[b, "pair_key"])
            if o is not None:
                ov.append((fdf.loc[a], fdf.loc[b], o))
    ov.sort(key=lambda x: -x[2])
    amc = {}
    eqtot = sum(after_vals[c] for c in eq_codes) or 1
    for c in eq_codes:
        amc[fdf.loc[c, "amc"]] = amc.get(fdf.loc[c, "amc"], 0) + after_vals[c] / eqtot
    for a, s in amc.items():
        if s > C.MAX_AMC_SHARE:
            warnings.append(f"{a} would hold {s:.0%} of the equity: one fund house's style, above the {C.MAX_AMC_SHARE:.0%} guide.")
    for a, b, o in ov:
        if o > C.OVERLAP_HIGH * 0.9:
            warnings.append(f"{a['name']} and {b['name']} share {o:.0%} of their portfolios: close to one bet.")

    # ------------------------------------------------------------ theses for changes of shape
    theses = []
    exit_cost = {}
    for v in verdicts:
        if v.action == "exit":
            exit_cost[v.h.bucket] = exit_cost.get(v.h.bucket, (0, 0))
            lo, hi = exit_cost[v.h.bucket]
            exit_cost[v.h.bucket] = (lo + v.cost_low, hi + v.cost_high)
    for b in list(C.EQUITY_BUCKETS) + ["parked", "debt", "thematic"]:
        c0, c1, tg = current.get(b, 0), after.get(b, 0), target.get(b, 0)
        band = max(C.BAND_ABS, C.BAND_REL * tg)
        if abs(c1 - c0) < band and not (c0 == 0 and c1 > 0.02) and not (c1 < 0.005 < c0):
            continue
        lo, hi = exit_cost.get(b, (0, 0))
        cost = "nothing: it is done with new money" if hi < 1 else (
            f"about ₹{lo:,.0f}" if abs(hi - lo) < 1 else f"₹{lo:,.0f} to ₹{hi:,.0f} in tax and exit loads, depending on purchase dates")
        horizon = "no fixed date" if years is None else f"{years} years to the goal"
        theses.append({
            "bucket": b,
            "title": f"{C.BUCKET_LABEL[b]}: {c0:.0%} now → {c1:.0%} in 12 months (target {tg:.0%})",
            "what": _what(b, cat_before, cat_after),
            "why": f"A {profile.replace('_', ' ')} profile with {horizon} puts {tg:.0%} here. " + (
                "The sleeve is under-weight, so new money goes here first." if c1 > c0 else
                ("This horizon doesn't need cash-like money: it earns about what a liquid fund pays while the equity sleeves are short of target, "
                 "so it moves into them step by step." if b in ("parked", "debt") else
                 "The sleeve is above its share for this profile; new money goes elsewhere, and exits here are for the funds' own reasons.")),
            "cost": cost,
            "reverse": REVERSE_IF.get(b, "the client's goal or risk profile changes"),
            "evidence": "Fund choices use our track-record ratings, which describe the past and are not a forecast; "
                        "the case for the change rests on the client's goal and risk, not on recent returns.",
        })
    # category switches inside a sleeve (e.g. flexi cap -> multi cap)
    for cat in sorted(set(cat_before) | set(cat_after)):
        a0, a1 = cat_before.get(cat, 0), cat_after.get(cat, 0)
        if (a0 < 0.02 <= a1) or (a1 < 0.01 < a0 and a0 >= 0.03):
            b = C.BUCKET_OF_CATEGORY.get(cat)
            same = [k for k in set(cat_before) | set(cat_after) if C.BUCKET_OF_CATEGORY.get(k) == b]
            if any(t["bucket"] == b for t in theses) and same == [cat]:
                continue                  # the sleeve's own thesis already covers it
            notes = CATEGORY_NOTE.get(cat, "")
            theses.append({
                "bucket": "category", "title": f"{cat}: {a0:.0%} → {a1:.0%}",
                "what": f"{cat} funds invest in {notes}." if notes else "",
                "why": ("added because the sleeve needs new money and the best-rated eligible fund is in this category"
                        if a1 > a0 else "the funds held here are being exited (see their reasons) and new money goes elsewhere in the sleeve"),
                "cost": "see the exits table", "reverse": "the category's funds return to an A rating or the client's needs change",
                "evidence": "A category change follows from fund verdicts and the target shape, not from the category's recent returns.",
            })

    return Plan(client=client, portfolio=port, profile=profile, years=years, target=target, current=current, after=after,
                verdicts=verdicts, sip=sip, deploy=deploy, stp_months=client.stp_months or C.STP_MONTHS[profile],
                theses=theses, warnings=warnings, overlap=ov, amc_share=amc,
                lookthrough_before=look(before_vals), lookthrough_after=look(after_vals),
                cat_before=cat_before, cat_after=cat_after, as_of=on)


def _what(b, cb, ca) -> str:
    cats = {k for k in set(cb) | set(ca) if C.BUCKET_OF_CATEGORY.get(k) == b}
    parts = [f"{k} {cb.get(k, 0):.0%} → {ca.get(k, 0):.0%}" for k in sorted(cats) if abs(cb.get(k, 0) - ca.get(k, 0)) >= 0.005]
    return "; ".join(parts)
