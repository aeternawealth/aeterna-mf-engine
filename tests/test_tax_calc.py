"""Income tax, old vs new regime (FY 2026-27): known answers, and the JavaScript copy agrees with the Python one."""
import json, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))
import tax_calc as T  # noqa: E402


def test_new_regime_rebate_and_relief():
    assert T.tax(1275000, "new")[1] == 0                     # 12L taxable after 75k standard deduction
    assert T.tax(1500000, "new")[1] == 97500                  # 14.25L taxable: 20k+40k+33.75k = 93,750 + cess
    ti, t = T.tax(1285000, "new")                             # 12.1L taxable: relief caps tax at 10k
    assert ti == 1210000 and t == round(10000 * 1.04)


def test_old_regime():
    assert T.tax(1500000, "old", True, 150000, 25000)[1] == round((12500 + 100000 + 82500) * 1.04)
    assert T.tax(550000, "old", True, 0, 0)[1] == 0          # 5L taxable: rebate


def test_surcharge_marginal_relief():
    ti, t = T.tax(5085000, "new")                             # 50.1L taxable: surcharge capped by income above 50L
    base = T._slab(5000000, T.NEW)
    assert t == round(min(T._slab(ti, T.NEW) * 1.10, base + 10000) * 1.04)


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_matches_python():
    cases = [(g, r, s, c, d, h) for g in (300000, 900000, 1285000, 1500000, 2600000, 5085000, 12000000, 60000000)
             for r in ("new", "old") for s in (True, False) for c, d, h in ((0, 0, 0), (150000, 25000, 200000))]
    js = T.JS + "const C=" + json.dumps(cases) + ";console.log(JSON.stringify(C.map(([g,r,s,c,d,h])=>txTax({g,sal:s,c,d,h,hra:0,n:0,o:0},r).tax)))"
    got = json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True).stdout)
    assert got == [T.tax(g, r, s, c, d, h)[1] for g, r, s, c, d, h in cases]
