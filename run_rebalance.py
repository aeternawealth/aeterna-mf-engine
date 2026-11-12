"""Portfolio review and rebalance plan for one client.

    python run_rebalance.py clients/harshit.yaml                 # asks for the CAS password if the statement is a PDF
    CAS_PASSWORD=... python run_rebalance.py clients/harshit.yaml
    python run_rebalance.py --example > clients/new_client.yaml  # a blank client file to fill in

Writes clients/<name>/review_<date>.html (for the client) and workings_<date>.csv (lot-level tax, internal).
Client files and statements live in clients/, which git ignores. Rules: docs/rebalance_principles.md."""
from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
from pathlib import Path

import yaml

from rebalance import cas, plan as P, project as J, report as R

EXAMPLE = """# Client file for run_rebalance.py. Amounts in rupees. Delete what you don't know; defaults are shown.
name: Client Name
statement: clients/client_cas.pdf     # CAMS/KFintech CAS PDF (detailed, from inception) or a broker's holdings .xlsx
goal: growth                          # growth | retirement | education | house | other
target_today: null                    # goal amount in today's money, e.g. 20000000 (leave null for plain growth)
target_year: null                     # e.g. 2045
sip: 25000                            # monthly SIP the client can commit to
lumpsum: 0                            # money available now, outside the statement
risk_attitude: aggressive             # conservative | moderate | aggressive | very_aggressive (how they'd act in a 35% fall)
risk_capacity: aggressive             # the same scale, from income stability, dependants, loans, other assets
slab: 0.30                            # income-tax slab rate
ltcg_used: 0                          # long-term equity gains already booked this financial year
plan: Regular                         # plan type for new money: Regular (via Aeterna) or Direct
keep: []                              # funds to keep whatever the plan says: name parts or AMFI codes
emergency_reserve: 0                  # rupees to leave in liquid/arbitrage (0 if the emergency fund is held elsewhere)
stp_months: null                      # months to move parked money into equity (default by profile)
inflation: null                       # e.g. 0.06; education defaults to 0.10
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("client", nargs="?")
    ap.add_argument("--example", action="store_true", help="print a blank client file")
    ap.add_argument("--no-projection", action="store_true")
    a = ap.parse_args()
    if a.example:
        print(EXAMPLE)
        return
    if not a.client:
        ap.error("give a client file (see --example)")
    cfg = yaml.safe_load(Path(a.client).read_text()) or {}
    stmt = cfg.pop("statement")
    pw = None
    if str(stmt).lower().endswith(".pdf"):
        pw = os.environ.get("CAS_PASSWORD") or getpass.getpass("CAS password: ")
    port = cas.read(stmt, pw)
    fields = set(P.Client.__dataclass_fields__)
    client = P.Client(**{k: v for k, v in cfg.items() if k in fields and v is not None})
    plan = P.build(port, client)
    proj = None if a.no_projection else J.project(plan)
    slug = re.sub(r"[^a-z0-9]+", "-", (client.name or port.investor or "client").lower()).strip("-")
    out = Path("clients") / slug
    out.mkdir(parents=True, exist_ok=True)
    html_p = out / f"review_{plan.as_of:%Y-%m-%d}.html"
    html_p.write_text(R.render(plan, proj), encoding="utf-8")
    R.workings_csv(plan, out / f"workings_{plan.as_of:%Y-%m-%d}.csv")
    print(f"{client.name or port.investor}: {len(port.holdings)} funds, {R.rs(port.value)}; profile {plan.profile}")
    for f, amt, b in plan.sip:
        print(f"  SIP  {R.rs(amt):>12}  {f['name']} ({f['plan_type']}, {f['tier']})")
    for v in plan.verdicts:
        if v.action == "exit":
            print(f"  EXIT {R.rs(v.sell_value):>12}  {v.h.name}: {v.when}")
    for w in plan.warnings:
        print("  note:", w)
    print(f"report: {html_p}")


if __name__ == "__main__":
    sys.exit(main())
