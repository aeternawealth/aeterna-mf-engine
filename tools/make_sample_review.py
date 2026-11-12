"""Builds the public sample report (site/sample_review.html) from a made-up portfolio, so visitors can see what a
portfolio review looks like. No real client data. Re-run after a monthly ratings change:
    python tools/make_sample_review.py"""
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rebalance import data as D, plan as P, project as J, report as R, tax as T  # noqa: E402
from rebalance.cas import Holding, Portfolio  # noqa: E402

TODAY = date.fromisoformat(D.as_of()[:10])
F = D.funds()


def pick(cat, tier, n=0):
    rows = F[(F.category == cat) & (F.tier == tier) & (F.plan_type == "Regular") & F.nav_latest.notna()].sort_values("aum_cr", ascending=False)
    return rows.iloc[min(n, len(rows) - 1)]


def hold(row, value, months_old):
    nav = float(row["nav_latest"])
    lots, left = [], value
    # a SIP-built holding: equal monthly lots, the older ones bought cheaper
    for k in range(months_old, 0, -1):
        amt = value / months_old
        cost = nav / (1.012 ** k)
        lots.append(T.Lot(TODAY - timedelta(days=30 * k), amt / nav, cost))
    units = sum(l.units for l in lots)
    return Holding(name=row["name"] + " - Regular Plan - Growth", plan="Regular", units=units, nav=nav, value=units * nav,
                   invested=sum(l.units * l.cost for l in lots), lots=lots, code=int(row["code"]), fund=row, exact_lots=True, source="sample")


spec = [("Large Cap", "C", 0, 450000, 40), ("Flexi Cap", "B", 0, 600000, 48), ("Flexi Cap", "C", 0, 250000, 30), ("Mid Cap", "A", 0, 300000, 36),
        ("Mid Cap", "C", 0, 150000, 14), ("Small Cap", "B", 0, 200000, 24), ("Small Cap", "C", 0, 120000, 10), ("Large & Mid Cap", "B", 0, 250000, 30),
        ("ELSS", "B", 0, 180000, 44), ("Multi Cap", "C", 0, 100000, 8), ("Sectoral/Thematic", "C", 0, 80000, 6), ("Arbitrage", "A", 0, 700000, 5)]
hs = [hold(pick(c, t, n), v, m) for c, t, n, v, m in spec]
port = Portfolio("Sample investor", "", TODAY, hs, "sample CAS (made-up portfolio)")
client = P.Client(name="Sample investor (made-up portfolio)", goal="retirement", target_today=30_000_000, target_year=TODAY.year + 20, sip=30000,
                  risk_attitude="aggressive", risk_capacity="aggressive", slab=0.30, plan="Regular")
plan = P.build(port, client)
html = R.render(plan, J.project(plan))
banner = ('<div style="background:#0b5a46;color:#fff;padding:12px 16px;text-align:center;font:500 14px/1.5 system-ui">'
          'A sample report, built from a made-up portfolio. '
          '<a href="/invest/portfolio-review/" style="color:#fff;font-weight:600">Get a free review of your own portfolio →</a></div>')
html = html.replace("<body><main>", "<body>" + banner + "<main>", 1)
html = html.replace("<head>", '<head><link rel="canonical" href="https://aeternawealth.com/invest/portfolio-review/sample/">', 1)
(ROOT / "site" / "sample_review.html").write_text(html, encoding="utf-8")
print("site/sample_review.html:", len(hs), "funds,", R.rs(port.value), "| SIPs:", [(f["name"], a) for f, a, b in plan.sip])
