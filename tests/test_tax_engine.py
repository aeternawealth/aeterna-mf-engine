"""Full income tax engine (site/tax_engine.js), FY 2026-27. Each expected figure is worked by hand in the comment."""
import json, shutil, subprocess, sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))
pytestmark = pytest.mark.skipif(not shutil.which("node"), reason="node not installed")

CASES = [  # (inputs, regime, expected tax payable)
    ({"salary": 1500000}, "new", 97500),                   # 14.25L: 20k+40k+33.75k = 93,750 x 1.04
    ({"salary": 1275000}, "new", 0),                       # 12L taxable: rebate
    ({"salary": 1285000}, "new", 10400),                   # 12.1L: marginal relief caps tax at 10k
    ({"salary": 1500000, "c80": 150000, "d80self": 25000}, "old", 202800),   # 12.75L: 12.5k+100k+82.5k
    ({"salary": 600000, "age": "60-79"}, "old", 20800),    # 5.5L, senior: (5L-3L) 5% + 0.5L 20% = 20k
    ({"salary": 1000000, "age": "80+"}, "old", 93600),     # 9.5L, super senior: 4.5L x 20% = 90k
    ({"interestFD": 1000000, "resident": False}, "new", 41600),   # NRI, no rebate: 20k + 20k
    ({"ltcg112A": 500000}, "new", 0),                      # 3.75L taxable gain inside the unused 4L exemption
    ({"salary": 2075000, "ltcg112A": 1000000}, "new", 321750),    # 20L slab 2L + 8.75L x 12.5%
    ({"salary": 1075000, "stcg111A": 300000}, "new", 104000),     # 10L slab 40k (total 13L, no rebate) + 60k
    ({"salary": 5085000}, "new", 1133600),                 # 50.1L: surcharge relief, 10.8L + 10k
    ({"salary": 5575000}, "new", 1407120),                 # 55L: 12.3L + 10% surcharge
    ({"salary": 575000, "vda": 200000}, "new", 62400),     # rebate does not cover crypto: 60k
]


def _run(js):
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True, cwd=ROOT).stdout)


def test_cases():
    js = "const T=require('./site/tax_engine.js');const C=" + json.dumps(CASES) + ";console.log(JSON.stringify(C.map(([p,r])=>T.txCompute(p,r).payable)))"
    assert _run(js) == [c[2] for c in CASES]


def test_hra():
    js = "const T=require('./site/tax_engine.js');console.log(JSON.stringify([T.txHRA({basic:600000,hraRecd:240000,rent:300000,metro:true}),T.txHRA({basic:600000,hraRecd:300000,rent:200000})]))"
    assert _run(js) == [240000, 140000]      # least of 2.4L, 2.4L, 3L; least of 3L, 1.4L, 2.4L


def test_slab_page_matches_engine():
    import tax_pages as TP
    eng = _run("const T=require('./site/tax_engine.js');console.log(JSON.stringify(T.TAXRULES))")
    assert [[hi, round(r * 100)] for hi, r in eng["newSlabs"]] == [[hi, r] for lo, hi, r in TP.NEW]
    assert [[hi, round(r * 100)] for hi, r in eng["oldSlabs"]["60-79"]] == [[hi, r] for lo, hi, r in TP.OLD["60 to 79 (senior citizen)"]]
