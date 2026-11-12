"""Read a client's holdings.

- read_cas(): CAMS / KFintech consolidated account statement (PDF, password-protected) via `casparser`. Gives every
  transaction, so tax lots are exact.
- read_export(): a broker's holdings sheet (e.g. Groww's "Mutual_Funds_*.xlsx"). Has no purchase dates, so each
  holding becomes one lot with an unknown date and the tax shown is a range.

Privacy: the PAN is masked as soon as it is read, nothing is written to disk here, and the password is never stored."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

from . import data as D
from .tax import Lot, lots_fifo


@dataclass
class Holding:
    name: str
    plan: str
    units: float
    nav: float
    value: float
    invested: float
    lots: list = field(default_factory=list)
    folio: str = ""
    code: int | None = None
    isin: str = ""
    fund: object = None          # the funds.json row (pandas Series) or None
    exact_lots: bool = False
    source: str = ""

    @property
    def category(self):
        return None if self.fund is None else self.fund["category"]

    @property
    def bucket(self):
        return "other" if self.fund is None else self.fund["bucket"]


@dataclass
class Portfolio:
    investor: str
    pan_masked: str
    as_of: date
    holdings: list
    source: str
    warnings: list = field(default_factory=list)

    @property
    def value(self):
        return sum(h.value for h in self.holdings)


def mask_pan(pan: str | None) -> str:
    p = str(pan or "").strip().upper()
    return p[:5] + "****" + p[-1] if re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", p) else ("" if not p else "****")


def _finish(hs: list[Holding], warnings: list) -> list[Holding]:
    for h in hs:
        f = D.match(h.name, h.plan, code=h.code)
        h.fund = f
        if f is None:
            warnings.append(f"Not matched to our fund data: {h.name}. It is kept in the totals but not rated.")
        else:
            h.code = int(f["code"])
            h.plan = f["plan_type"]
    return hs


def read_cas(path, password: str) -> Portfolio:
    import casparser
    d = casparser.read_cas_pdf(str(path), password, output="dict")
    info = d.get("investor_info") or {}
    end = d.get("statement_period", {}).get("to")
    try:
        as_of = pd.to_datetime(end, dayfirst=True).date()
    except Exception:
        as_of = date.today()
    hs, warns, pan = [], [], ""
    for fo in d.get("folios", []):
        pan = pan or fo.get("PAN") or ""
        for s in fo.get("schemes", []):
            close = float(s.get("close") or 0)
            if close <= 1e-6:
                continue
            v = s.get("valuation") or {}
            txs = [{"date": pd.to_datetime(t["date"]).date(), "units": t.get("units"), "nav": t.get("nav"),
                    "amount": t.get("amount"), "type": t.get("type")} for t in s.get("transactions", []) if t.get("units")]
            lots = lots_fifo(txs)
            held = sum(l.units for l in lots)
            open_bal = float(s.get("open") or 0)
            exact = abs(held - close) < max(0.01, 0.001 * close)
            if not exact:
                # the statement starts after the first purchase: the opening balance has no dates
                gap = close - held
                if gap > 0:
                    lots.insert(0, Lot(None, gap, float(v.get("cost") or 0) / close if close else 0))
                warns.append(f"{s['scheme']}: {gap:.3f} units carried in from before the statement period (opening balance "
                             f"{open_bal:.3f}); their purchase dates are unknown. A CAS from inception fixes this.")
            name = s["scheme"]
            plan = "Direct" if re.search(r"\bdirect\b", name, re.I) else "Regular"
            hs.append(Holding(name=name, plan=plan, units=close, nav=float(v.get("nav") or 0), value=float(v.get("value") or 0),
                              invested=float(v.get("cost") or sum(l.units * l.cost for l in lots)), lots=lots,
                              folio=str(fo.get("folio", "")), code=s.get("amfi"), isin=s.get("isin") or "",
                              exact_lots=exact, source="CAS"))
    return Portfolio(investor=info.get("name", ""), pan_masked=mask_pan(pan), as_of=as_of, holdings=_finish(hs, warns),
                     source="CAS", warnings=warns)


def read_export(path) -> Portfolio:
    """Groww-style holdings sheet: a header row with 'Scheme Name' ... 'Units', 'Invested Value', 'Current Value'."""
    raw = pd.read_excel(path, header=None)
    hdr = next(i for i in range(len(raw)) if "Scheme Name" in [str(x).strip() for x in raw.iloc[i]])
    df = raw.iloc[hdr + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[hdr]]
    df = df[df["Scheme Name"].notna() & pd.to_numeric(df["Units"], errors="coerce").notna()]
    name = ""
    pan = ""
    for i in range(hdr):
        row = [str(x).strip() for x in raw.iloc[i]]
        if row[0] == "Name":
            name = row[1]
        if row[0] == "PAN":
            pan = row[1]
    m = re.search(r"(\d{2})-(\d{2})-(\d{4})\.xls", str(path))
    as_of = date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else date.today()
    hs = []
    for _, r in df.iterrows():
        units, inv, val = float(r["Units"]), float(r["Invested Value"]), float(r["Current Value"])
        nm = str(r["Scheme Name"])
        plan = "Direct" if re.search(r"\bdirect\b", nm, re.I) else "Regular"
        hs.append(Holding(name=nm, plan=plan, units=units, nav=val / units if units else 0, value=val, invested=inv,
                          lots=[Lot(None, units, inv / units if units else 0)], folio=str(r.get("Folio No.", "")),
                          source=str(r.get("Source", ""))))
    warns = ["This statement has no purchase dates, so tax and exit loads are shown as a range (all short-term vs all "
             "long-term). A CAS from camsonline.com gives exact figures."]
    return Portfolio(investor=name, pan_masked=mask_pan(pan), as_of=as_of, holdings=_finish(hs, warns), source="holdings export",
                     warnings=warns)


def read(path, password: str | None = None) -> Portfolio:
    p = str(path).lower()
    if p.endswith(".pdf"):
        if not password:
            raise ValueError("a CAS PDF needs its password")
        return read_cas(path, password)
    return read_export(path)
