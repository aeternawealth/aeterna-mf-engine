"""Net flows (money coming into / leaving a scheme), estimated from AMFI quarterly average AUM:
    flow_q = AUM_q / AUM_{q-1} - avgNAV_q / avgNAV_{q-1}     (growth of AUM not explained by returns)
Shown for information only. In the 2019-25 backtest, past flows did NOT predict future benchmark-relative
returns (heaviest-outflow quintile beat its index over the next 3Y 52% of the time vs 51% for the heaviest-inflow
quintile), so flows are deliberately not part of the score."""
from __future__ import annotations

import glob
import json
import re

import numpy as np
import pandas as pd

from . import config as C

HIST = C.DATA / "aum_hist"
QEND = {"April - June": "06-30", "July - September": "09-30", "October - December": "12-31", "January - March": "03-31"}


def fetch_latest(log=print, quarters=6):
    """Keep data/aum_hist/ topped up with the most recent quarters (one JSON per quarter)."""
    import httpx
    HIST.mkdir(parents=True, exist_ok=True)
    h = {**C.HTTP_HEADERS, "Referer": "https://www.amfiindia.com/aum-data/average-aum"}
    url = "https://www.amfiindia.com/api/average-aum-schemewise"
    got = 0
    for fy in (1, 2):
        meta = httpx.get(url, params={"strType": "Categorywise", "fyId": fy}, headers=h, timeout=120).json()
        for p in meta["data"]["periods"]:
            f = HIST / f"{p['period'].replace(' ', '')}.json"
            if f.exists() or got >= quarters:
                continue
            for attempt in range(4):
                try:
                    r = httpx.get(url, params={"strType": "Categorywise", "fyId": fy, "periodId": p["id"], "MF_ID": "0"}, headers=h, timeout=240)
                    d = r.json().get("data") or []
                    if sum(len(c.get("schemes", [])) for c in d) > 100:
                        break
                except Exception:
                    d = []
            rows = [(s.get("AMFI_Code"), sum(x for x in (s.get("AverageAumForTheMonth") or {}).values() if isinstance(x, (int, float))))
                    for c in d for s in c.get("schemes", [])]
            if rows:
                json.dump({"period": p["period"], "rows": rows}, open(f, "w"))
                got += 1
    log(f"  flows: {len(glob.glob(str(HIST / '*.json')))} quarters of AUM history on disk")


def compute(universe: pd.DataFrame, navall: pd.DataFrame, navs: dict) -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(HIST / "*.json")):
        j = json.load(open(f))
        m = re.match(r"(.*) (\d{4})$", j["period"])
        qe = pd.Timestamp(f"{m.group(2)}-{QEND[m.group(1)]}")
        rows += [(int(c), qe, a) for c, a in j["rows"] if c]
    if not rows:
        return pd.DataFrame()
    A = pd.DataFrame(rows, columns=["code", "qend", "aum"]).drop_duplicates(["code", "qend"])
    base = (navall.name.str.replace(r"(?i)\b(direct|regular)\s*plan\b", "", regex=True)
            .str.replace(r"(?i)\bgrowth( option| plan)?\b", "", regex=True)
            .str.replace(r"[^A-Za-z0-9&]+", " ", regex=True).str.strip().str.lower())
    pk = dict(zip(navall.code, navall.amc.str.lower().str.strip() + "|" + base))
    A["pair_key"] = A.code.map(pk)
    P = A.dropna(subset=["pair_key"]).groupby(["pair_key", "qend"]).aum.sum()
    reg = universe.sort_values("plan_type", ascending=False).drop_duplicates("pair_key").set_index("pair_key").code  # Regular if present
    out = []
    for pkey, q in P.groupby(level=0):
        q = q.droplevel(0).sort_index()
        code = reg.get(pkey)
        if code is None or code not in navs or len(q) < 2:
            continue
        nav = navs[code].set_index("date")["nav"]
        avg = nav.groupby(pd.PeriodIndex(nav.index, freq="Q-DEC")).mean().reindex(pd.PeriodIndex(q.index, freq="Q-DEC")).values
        fl = pd.Series(q.values[1:] / q.values[:-1] - avg[1:] / avg[:-1], index=q.index[1:]).clip(-1, 3)
        last4 = fl.tail(4)
        out.append({"pair_key": pkey, "flow_1q": fl.iloc[-1], "flow_4q": last4.sum() if len(last4) >= 3 else np.nan,
                    "flow_quarter": q.index[-1].strftime("%b %Y"), "aum_1y_ago_cr": q.iloc[-5] / 100 if len(q) >= 5 else np.nan})
    return pd.DataFrame(out)
