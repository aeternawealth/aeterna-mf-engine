"""The reimagined home page, served unlisted at /preview/ (noindex, not in the sitemap) until it is published.
Built with the taste-skill kit (MIT, preview_home/kit/LICENSE) from preview_home/template.html, filled with the live
ratings in outputs/latest/rankings.json. Plain Python: the site build has no numpy."""
import html
import json
import shutil
from datetime import date
from pathlib import Path

S = Path(__file__).resolve().parent
SRC = S / "preview_home"
CALL = "https://wa.me/918595993600?text=" + "Hi%20Aeterna%2C%20I%27d%20like%20to%20book%20a%20call."
TIER_CLASS = {"A+": "tier--ap", "A": "tier--a", "B": "tier--b", "C": "tier--c"}


SMALL = {"of", "and", "the", "&"}


ACRONYMS = {"HDFC", "ICICI", "SBI", "UTI", "DSP", "HSBC", "PGIM", "JM", "LIC", "ITI", "IDFC", "NJ", "PPFAS", "WOC", "IIFL", "BSE", "NSE", "ELSS", "AMC"}


def _name(n):
    """'BANK OF INDIA FLEXI CAP FUND' and 'ICICI Prudential Flexi Cap fund' read as 'Bank of India Flexi Cap Fund'."""
    n = n.replace(" - Regular Plan", "").replace(" Regular Plan", "").strip()
    out = []
    for i, w in enumerate(n.split()):
        if w.isupper() and w not in ACRONYMS:
            w = w.lower() if i and w.lower() in SMALL else w.capitalize()
        elif w == "fund":
            w = "Fund"
        out.append(w)
    return " ".join(out)


def _pct(x, sign=False):
    return "" if x is None else (f"{x * 100:+.1f}%" if sign else f"{x * 100:.1f}%")


def build_preview(dist: Path):
    d = json.loads((S.parent / "outputs" / "latest" / "rankings.json").read_text())
    F = d["funds"]
    asof = date.fromisoformat(d["as_of"][:10])
    flexi = [f for f in F if f["category"] == "Flexi Cap" and f["plan_type"] == "Regular" and f.get("tier") in TIER_CLASS]
    flexi.sort(key=lambda f: (f.get("peer_rank") or 1e9))
    rows = []
    for f in flexi[:6]:
        name = html.escape(_name(f["name"]))
        rows.append(f'<tr><td class="fund">{name}<small>{html.escape(f["amc"])}</small></td>'
                    f'<td class="num">{_pct(f.get("cagr_3y"))}</td>'
                    f'<td class="num hide-sm pos">{_pct(f.get("excess_cagr_3y"), True)}</td>'
                    f'<td><span class="tier {TIER_CLASS[f["tier"]]}">{f["tier"]}</span></td></tr>')
    cats = {"Value" if f["category"] == "Contra" else f["category"] for f in F}
    reg = lambda c: sum(1 for f in F if f["category"] == c and f["plan_type"] == "Regular")
    allc = lambda c: sum(1 for f in F if f["category"] == c)
    fill = {
        "ASOF": f"{asof.day} {asof:%b %Y}", "N_FUNDS": f"{len(F):,}", "N_CATS": str(len(cats)),
        "N_AMCS": str(len({f['amc'] for f in F})), "N_FLEXI": str(allc("Flexi Cap")), "N_SMALL": str(allc("Small Cap")),
        "N_FLEXI_REG": str(reg("Flexi Cap")), "HERO_ROWS": "".join(rows), "CALL": CALL,
    }
    page = (SRC / "template.html").read_text(encoding="utf-8")
    for k, v in fill.items():
        page = page.replace("{{" + k + "}}", v)
    assert "{{" not in page, "unfilled placeholder in preview_home/template.html"
    out = dist / "preview"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    for sub in ("kit", "img"):
        shutil.copytree(SRC / sub, out / sub)
