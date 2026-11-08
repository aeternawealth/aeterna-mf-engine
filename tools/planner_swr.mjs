// How long a corpus lasts at each withdrawal rate, on Indian market history: writes site/planner/swr.json,
// which the Money Plan ("your freedom number") and the /learn/4-percent-rule-india/ guide both read.
//
// Method: 4,000 sequences of 50 years, each stitched from random 12-month blocks of actual monthly returns since
// Aug 2007 (the same generator the Money Plan uses). Year 1 withdraws the rate × the starting corpus; the amount
// then rises 6% a year with prices. A sequence "lasts" N years if the corpus is never exhausted before then;
// "kept its value" means after 50 years the corpus is still worth at least what it started with, in today's money.
// Run: node tools/planner_swr.mjs
import fs from 'fs';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const R = new URL('../site/planner/', import.meta.url).pathname;
const M = require(R + 'model.js'), mkt = JSON.parse(fs.readFileSync(R + 'market.json'));

const N = 4000, YEARS = 50, INFL = 0.06, GOLD = 0.05;
const RATES = [0.025, 0.03, 0.035, 0.04, 0.045, 0.05, 0.06];
const MIXES = [35, 60];   // 35%: the Money Plan's retirement mix; 60%: a growth-tilted retirement portfolio

export function table(eqPct, paths = M.paths(mkt, YEARS * 12, N, 4242)) {
  const eq = eqPct / 100, de = 1 - eq - GOLD;
  return RATES.map(w => {
    let l30 = 0, l40 = 0, l50 = 0, keep = 0;
    for (const p of paths) {
      let v = 1, wd = w / 12, dead = 0;
      for (let t = 0; t < YEARS * 12; t++) {
        if (t && t % 12 === 0) wd *= 1 + INFL;
        v = v * (1 + eq * p.e[t] + de * p.d[t] + GOLD * p.g[t]) - wd;
        if (v <= 0) { dead = t + 1; break; }
      }
      if (!dead || dead > 360) l30++;
      if (!dead || dead > 480) l40++;
      if (!dead) { l50++; if (v / Math.pow(1 + INFL, YEARS) >= 1) keep++; }
    }
    const pc = x => Math.round(x / paths.length * 100);
    return { rate: Math.round(w * 1000) / 10, multiple: Math.round(1 / w * 10) / 10, last30: pc(l30), last40: pc(l40), last50: pc(l50), kept50: pc(keep) };
  });
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const P = M.paths(mkt, YEARS * 12, N, 4242), d = mkt.months[0];
  const out = { from: d[0], to: d[d.length - 1], sequences: N, years: YEARS, inflation: INFL * 100, gold: GOLD * 100,
                mixes: Object.fromEntries(MIXES.map(e => [e, table(e, P)])) };
  fs.writeFileSync(R + 'swr.json', JSON.stringify(out));
  for (const e of MIXES) { console.log(`\n${e}% equity`); console.table(out.mixes[e]); }
}
