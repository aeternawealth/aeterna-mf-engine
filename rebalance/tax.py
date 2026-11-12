"""Tax lots and the cost of selling: FIFO lots, short/long-term gains, the yearly LTCG exemption, grandfathering
(units bought on or before 31 Jan 2018), exit loads and the ELSS lock-in. Rules: config.TAX."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from . import config as C


@dataclass
class Lot:
    date: date | None        # None = unknown purchase date (holdings exports without transactions)
    units: float
    cost: float              # per unit, incl. stamp duty


@dataclass
class Slice:
    """part of a lot sold"""
    lot_date: date | None
    units: float
    basis: float             # per unit, after grandfathering
    proceeds: float
    gain: float
    days: int | None
    term: str                # "ST", "LT" or "?" (date unknown)
    load: float
    locked: bool             # ELSS units still in their 3-year lock-in


@dataclass
class SaleCost:
    slices: list = field(default_factory=list)
    proceeds: float = 0.0
    load: float = 0.0
    load_undated: float = 0.0     # part of `load` on lots with no purchase date (charged only in the short-term case)
    st_gain: float = 0.0
    lt_gain: float = 0.0
    unknown_gain: float = 0.0
    locked_units: float = 0.0

    @property
    def gain(self):
        return self.st_gain + self.lt_gain + self.unknown_gain


def fy_start(d: date) -> date:
    return date(d.year if d.month >= 4 else d.year - 1, 4, 1)


def tax_class(fund) -> str:
    t = None if fund is None else fund.get("tax")
    return t if t in ("equity", "debt", "other") else "equity"


@lru_cache(maxsize=1)
def _load_overrides() -> dict:
    p = Path(__file__).with_name("exit_loads.csv")
    if not p.exists():
        return {}
    with open(p) as fh:
        return {int(r["code"]): {"pct": float(r["pct"]), "days": int(r["days"])} for r in csv.DictReader(fh)}


def exit_load(code, category) -> dict:
    try:
        o = _load_overrides().get(int(code))
    except (TypeError, ValueError):
        o = None
    return o or C.EXIT_LOAD_BY_CATEGORY.get(category, C.EXIT_LOAD_DEFAULT)


def _lt_days(cls: str, lot_date: date | None) -> int:
    if cls == "equity":
        return C.TAX["equity"]["lt_days"]
    return C.TAX[cls]["lt_days"]


def sell(lots: list[Lot], units: float, on: date, nav: float, *, cls: str = "equity", category: str = "",
         code=None, grandfather_nav: float | None = None) -> SaleCost:
    """sell `units` first-in-first-out from `lots` (not modified) at `nav` on date `on`"""
    out = SaleCost()
    load = exit_load(code, category)
    elss = category == "ELSS"
    left = units
    for lot in sorted(lots, key=lambda l: (l.date is None, l.date or date.max)):
        if left <= 1e-9:
            break
        u = min(lot.units, left)
        left -= u
        days = (on - lot.date).days if lot.date else None
        basis = lot.cost
        if (cls == "equity" and lot.date and lot.date <= C.TAX["equity"]["grandfather_date"] and grandfather_nav):
            basis = max(lot.cost, min(grandfather_nav, nav))
        if days is None:
            term = "?"
        else:
            term = "LT" if days > _lt_days(cls, lot.date) else "ST"
        if cls == "debt" and lot.date and lot.date >= C.TAX["debt"]["slab_from"]:
            term = "ST"                     # slab rate whatever the holding period
        ld = u * nav * load["pct"] if (days is None and load["pct"] > 0) or (days is not None and days < load["days"]) else 0.0
        locked = bool(elss and (days is None or days < C.ELSS_LOCK_DAYS))
        s = Slice(lot.date, u, basis, u * nav, u * (nav - basis), days, term, ld, locked)
        out.slices.append(s)
        out.proceeds += s.proceeds
        out.load += ld
        if days is None:
            out.load_undated += ld
        if locked:
            out.locked_units += u
        if term == "ST":
            out.st_gain += s.gain
        elif term == "LT":
            out.lt_gain += s.gain
        else:
            out.unknown_gain += s.gain
    return out


def tax_due(sc: SaleCost, cls: str, slab: float, exempt_left: float, unknown_as: str = "ST") -> dict:
    """tax on one sale (incl. cess). Losses: short-term offsets short- then long-term gains; long-term offsets long-term.
    `unknown_as` decides how lots with no purchase date are treated (report both to bracket the cost)."""
    st, lt = sc.st_gain, sc.lt_gain
    if unknown_as == "ST":
        st += sc.unknown_gain
    else:
        lt += sc.unknown_gain
    if st < 0:
        lt += st
        st = 0.0
    lt_taxable, used = lt, 0.0
    if cls == "equity":
        if lt > 0:
            used = min(lt, exempt_left)
            lt_taxable = lt - used
        rate_st, rate_lt = C.TAX["equity"]["stcg"], C.TAX["equity"]["ltcg"]
    elif cls == "debt":
        rate_st, rate_lt = slab, C.TAX["debt"]["ltcg_old"]
    else:
        rate_st, rate_lt = slab, C.TAX["other"]["ltcg"]
    tax = max(st, 0) * rate_st + max(lt_taxable, 0) * rate_lt
    tax *= 1 + C.TAX["cess"]
    return {"tax": tax, "exempt_used": used, "st_gain": st, "lt_gain": lt}


def cheaper_on(lots: list[Lot], on: date, nav: float, *, cls: str = "equity", category: str = "", code=None) -> date | None:
    """the date by which every lot with a gain is past all its cost steps (long-term status, exit-load window, ELSS
    lock-in): from then on the whole holding is cheap to sell. None if that is already true."""
    load = exit_load(code, category)
    last = None
    for l in lots:
        if not l.date or nav <= l.cost:
            continue
        steps = [l.date + timedelta(days=load["days"]) if load["days"] else None]
        if not (cls == "debt" and l.date >= C.TAX["debt"]["slab_from"]):
            steps.append(l.date + timedelta(days=_lt_days(cls, l.date) + 1))
        if category == "ELSS":
            steps.append(l.date + timedelta(days=C.ELSS_LOCK_DAYS))
        d = max((x for x in steps if x), default=None)
        if d and d > on and (last is None or d > last):
            last = d
    return last


def mature_units(lots: list[Lot], on: date, *, cls: str = "equity", category: str = "", code=None) -> float:
    """units already past their exit-load window, long-term and out of any lock-in (cheap to sell now)"""
    load = exit_load(code, category)
    u = 0.0
    for l in lots:
        if not l.date:
            continue
        d = (on - l.date).days
        lt = cls == "debt" and l.date >= C.TAX["debt"]["slab_from"] or d > _lt_days(cls, l.date)
        if d >= load["days"] and lt and not (category == "ELSS" and d < C.ELSS_LOCK_DAYS):
            u += l.units
    return u


def lots_fifo(transactions: list[dict]) -> list[Lot]:
    """build open lots from transactions [{date, units, nav, amount, type}] (purchases add, redemptions consume FIFO)"""
    lots: list[Lot] = []
    for t in sorted(transactions, key=lambda t: t["date"]):
        u = float(t.get("units") or 0)
        if abs(u) < 1e-9:
            continue
        if u > 0:
            amt = float(t.get("amount") or 0)
            cost = (amt / u) if amt > 0 else float(t.get("nav") or 0)
            lots.append(Lot(t["date"], u, cost))
        else:
            need = -u
            while need > 1e-6 and lots:
                if lots[0].units <= need + 1e-6:
                    need -= lots[0].units
                    lots.pop(0)
                else:
                    lots[0].units -= need
                    need = 0
    return [l for l in lots if l.units > 1e-6]
