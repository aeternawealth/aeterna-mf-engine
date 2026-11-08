// Stress test for the allocation planner model: thousands of investors, hard invariants, calibration and a
// historical backtest on real Indian market months. Run: node tests/planner.test.mjs [--quick]
import { createRequire } from 'module';
import fs from 'fs';
const require = createRequire(import.meta.url);
const M = require('../site/planner/model.js');
const mkt = JSON.parse(fs.readFileSync(new URL('../site/planner/market.json', import.meta.url)));
const QUICK = process.argv.includes('--quick');

let seed = 42; const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; };
const pick = a => a[Math.floor(rnd() * a.length)];
const fails = []; let checks = 0;
const must = (ok, msg, who) => { checks++; if (!ok) fails.push(`${msg} :: ${JSON.stringify(who).slice(0, 260)}`); };
const near = (a, b, tol = 1) => Math.abs(a - b) <= tol;

const RISK = { allCautious: [1, 1, 1, 1, 1, 1], cautious: [2, 1, 2, 2, 3, 2], middle: [3, 2, 3, 2, 3, 3], bold: [3, 3, 4, 3, 3, 3], allBold: [4, 4, 4, 4, 4, 4],
  boldNovice: [4, 4, 4, 1, 1, 4], nervousVeteran: [1, 2, 2, 4, 2, 1] };
const qOf = a => Object.fromEntries(M.QIDS.map((k, i) => [k, a[i]]));

function persona() {
  const age = pick([22, 25, 28, 31, 34, 38, 42, 46, 50, 54, 58, 62, 66, 72]);
  const retired = age >= 62 ? rnd() < .8 : false;
  const income = pick([25e3, 40e3, 60e3, 1e5, 1.5e5, 2.5e5, 4e5, 8e5, 15e5]);
  const exp = income * pick([.35, .5, .65, .8, .95]);
  const homeEmi = rnd() < .45 ? income * pick([.1, .2, .3, .45]) : 0, otherEmi = rnd() < .3 ? income * pick([.05, .1, .2]) : 0;
  const hold = pick(['none', 'small', 'mid', 'large', 'fdHeavy', 'eqHeavy', 'property', 'stockConc']);
  const yearInc = income * 12, H = {};
  const scale = { none: 0, small: .5, mid: 2, large: 8, fdHeavy: 3, eqHeavy: 3, property: 4, stockConc: 3 }[hold];
  if (scale) Object.assign(H, { eqmf: yearInc * scale * .3, stocks: yearInc * scale * .1, fd: yearInc * scale * .2, savings: yearInc * scale * .05, gold: yearInc * scale * .05, epf: yearInc * scale * .2, ppf: yearInc * scale * .05, nps: yearInc * scale * .05 });
  if (hold === 'fdHeavy') Object.assign(H, { fd: yearInc * 2.5, eqmf: yearInc * .2 });
  if (hold === 'eqHeavy') Object.assign(H, { eqmf: yearInc * 2, stocks: yearInc, fd: 0 });
  if (hold === 'property') H.realestate = yearInc * 10;
  if (hold === 'stockConc') Object.assign(H, { stocks: yearInc * 2, topStock: 25 });
  const goals = [];
  if (rnd() < .6) goals.push({ name: 'Child education', cost: yearInc * pick([1, 2, 4]), years: pick([3, 8, 12, 16]) });
  if (rnd() < .4) goals.push({ name: 'Home down payment', cost: yearInc * pick([1, 3]), years: pick([1, 2, 4, 6]) });
  if (rnd() < .3) goals.push({ name: 'Car', cost: yearInc * .6, years: pick([1, 2, 3]) });
  if (rnd() < .2) goals.push({ name: 'Wedding', cost: yearInc * 1.5, years: pick([2, 5, 9]) });
  const rk = pick(Object.keys(RISK));
  return { _risk: rk, _hold: hold, age, retireAge: retired ? age : pick([55, 58, 60, 65]), dependants: pick([0, 0, 1, 2, 3]), earners: pick([1, 1, 2]),
    incomeType: retired ? 'retired' : pick(['salaried', 'salaried', 'variable', 'business']), slab: pick([0, 10, 20, 30]),
    income, expenses: exp, homeEmi, otherEmi, loanOut: (homeEmi + otherEmi) * 120, hiDebt: rnd() < .15 ? income * pick([.5, 2]) : 0, hiRate: pick([14, 24, 36]),
    efund: exp * pick([0, 1, 3, 6, 12]), termCover: yearInc * pick([0, 5, 12]), healthCover: pick([0, 3e5, 5e5, 1e6, 2.5e6]), epfMonthly: retired ? 0 : income * pick([0, .1, .24]) * .5,
    investing: hold === 'none' ? 'no' : 'yes', goals, ...H, q: qOf(RISK[rk]) };
}

// ------------------------------------------------------------- 1. invariants over many investors
const N = QUICK ? 400 : 3000;
const stats = { needOverSurplus: 0, needOverIncome: 0, corpusMult: [], E: {}, label: {} };
for (let i = 0; i < N; i++) {
  const inp = persona(), r = M.plan(inp, mkt, { fast: i % 10 !== 0, nConf: 200 });   // every 10th with confidence SIPs
  const who = { age: inp.age, inc: inp.income, risk: inp._risk, hold: inp._hold, inv: Math.round(r.invest), surplus: Math.round(r.surplus) };
  // money in = money out
  must(r.invest <= r.avail + 1, 'invests more than the surplus minus the buffer', who);
  if (r.invest1 != null) must(r.invest1 <= r.avail + 1, 'foundation phase invests more than available', who);
  if (r.surplus > 0) must(near(r.invest, r.avail, 2), 'part of the available surplus is left unallocated', { ...who, avail: r.avail });
  must(near(r.cats.reduce((a, c) => a + c.v, 0), r.invest, 2), 'category split does not add up to the monthly amount', who);
  if (r.invest1 != null) must(near(r.cats.reduce((a, c) => a + (c.v1 || 0), 0), r.invest1, 2), 'phase-1 category split does not add up', who);
  must(r.efTop <= (inp.savings || 0) + (inp.debtmf || 0) + (inp.fd || 0) + 1, 'emergency top-up uses more idle money than exists', who);
  (stats.phase = stats.phase || []).push(r.phaseMonths);
  must(near(r.tgtTotal, r.total, Math.max(2, r.total * 1e-6)), 'suggested allocation total differs from current total', { ...who, t: r.tgtTotal, c: r.total });
  must(Object.values(r.tgt).every(v => v >= -1 && isFinite(v)), 'negative or invalid target', who);
  must([r.invest, r.efTarget, r.need].every(v => isFinite(v) && v >= 0), 'invalid amount', who);
  // risk
  must(r.E >= .25 - 1e-9 && r.E <= .85 + 1e-9, 'equity cap out of range', who);
  if (inp.incomeType === 'retired') must(r.E <= .46 + 1e-9, 'retiree given too much equity', { ...who, E: r.E });
  must(r.efMonths >= 6 && r.efMonths <= 12, 'emergency months out of range', who);
  for (const g of r.G) {
    const m = g.mix;
    must(near(m.eq + m.debt + m.gold, 1, 1e-9), 'goal mix does not sum to 100%', who);
    if (g.y < 2) must(g.ret ? m.eq <= M.RMIX(r.E).eq + 1e-9 : m.eq === 0, g.ret ? 'retirement money above the retirement mix' : 'equity in money needed within 2 years', { ...who, g: g.name, y: g.y });
    if (g.y < 5) must(m.eq <= .35 + 1e-9, 'too much equity for a goal under 5 years', { ...who, y: g.y, eq: m.eq });
    must(g.f2 <= g.sip + 1e-6 && g.f2 >= 0 && (g.f1 || 0) >= 0, 'goal funded beyond its need', who);
    if (g.ret && g.how.includes('years')) stats.corpusMult.push(g.fv / (inp.expenses * 12 * .7 * Math.pow(1.06, g.y)));
  }
  if (r.need > r.surplus) stats.needOverSurplus++;
  if (r.need > inp.income) stats.needOverIncome++;
  (stats.E[inp._risk] = stats.E[inp._risk] || []).push(r.E);
  stats.label[r.label] = (stats.label[r.label] || 0) + 1;
}

// ------------------------------------------------------------- 2. monotonicity: more risk appetite never means less equity
const base = { age: 35, retireAge: 60, income: 1.5e5, expenses: 6e4, efund: 6e5, investing: 'yes', eqmf: 1e6, fd: 5e5, healthCover: 1e6, termCover: 2e7 };
let prevE = -1;
for (const rk of ['allCautious', 'cautious', 'middle', 'bold', 'allBold']) { const e = M.plan({ ...base, q: qOf(RISK[rk]) }, mkt, { fast: 1 }).E; must(e >= prevE - 1e-9, `equity fell when risk answers rose (${rk})`, { e, prevE }); prevE = e; }
for (let p = 0; p <= 1.0001; p += .1) { let prev = -1; for (let y = 0; y <= 30; y++) { const m = M.goalMix(y, p, mkt); must(m.eq >= prev - 1e-9, 'equity fell as the goal moved further away', { p, y }); prev = m.eq; } }
for (let y = 0; y <= 30; y++) { let prev = -1; for (let p = 0; p <= 1.0001; p += .1) { const m = M.goalMix(y, p, mkt); must(m.eq >= prev - 1e-9, 'equity fell as the profile got bolder', { p, y }); prev = m.eq; } }
// worse finances never mean more equity
{ const rich = M.plan({ ...base, q: qOf(RISK.allBold) }, mkt, { fast: 1 }).E;
  const tight = M.plan({ ...base, q: qOf(RISK.allBold), homeEmi: 8e4, efund: 0 }, mkt, { fast: 1 }).E;
  must(tight <= rich, 'tighter finances gave more equity', { rich, tight }); }

// ------------------------------------------------------------- 3. the glide path, by profile
const glideRows = [];
for (const [lab, p] of [['Cautious', .1], ['Balanced', .33], ['Growth', .6], ['High growth', .9]]) glideRows.push([lab, ...[1, 2, 3, 4, 5, 7, 10, 15, 20].map(y => Math.round(M.goalMix(y, p, mkt).eq * 100))]);

// ------------------------------------------------------------- 4. calibration: does a "75%" SIP reach the goal 75% of the time on fresh paths?
const calib = [];
for (const [y, lab] of [[3, 'Car in 3y'], [5, 'Down payment in 5y'], [8, 'Education in 8y'], [12, 'Education in 12y'], [20, 'Wealth in 20y']]) for (const p of [.1, .5, .9]) {
  const g = { name: lab, ret: false, y, fv: 2.5e6, have: 0, mix: M.goalMix(y, p, mkt) };
  const s = M.normalise({ stepup: 10, confidence: 75 }); g.sipMean = M.sipFor(g.fv, y, .08, .1);
  const sip = M.sipForConf(s, p, g, mkt, .75, { nConf: 500, seed: 1 });
  const fresh = M.paths(mkt, y * 12, 2000, 777);
  let hit = 0; for (const P of fresh) { let v = 0; for (let t = 0; t < y * 12; t++) { const left = (y * 12 - t) / 12, m = M.goalMix(left, p, mkt); v = v * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * (left < 2 ? P.l[t] : P.d[t])) + sip * Math.pow(1.1, Math.floor(t / 12)); } if (v >= g.fv) hit++; }
  calib.push([lab, p, Math.round(sip), hit / 2000]);
  must(Math.abs(hit / 2000 - .75) < .06, 'calibration off: a 75% SIP did not hit about 75% on fresh simulated markets', { lab, p, got: hit / 2000 });
}

// ------------------------------------------------------------- 4b. retirement end to end: reach the target corpus, then spend
// The retirement SIP is sized to reach 25x / 30x / 33x a year's spending in 85% of markets; on fresh paths it should,
// and the money should then last to 90 in at least 85% of them.
const retCal = [];
for (const [age, ra, inc, have, lab] of [[30, 60, 2e5, 2e6, '30, retire 60'], [45, 60, 3e5, 1.5e7, '45, retire 60'], [52, 58, 4e5, 4e7, '52, retire 58'], [35, 50, 3e5, 5e6, '35, retire 50']]) {
  const inp = { age, retireAge: ra, lifeExp: 90, income: inc, expenses: inc * .5, efund: inc * 4, eqmf: have, healthCover: 1e6, termCover: inc * 150, retireIncome: inc * .4, stepup: 5, q: qOf(RISK.middle) };
  const r = M.plan(inp, mkt, { nConf: 1200 }), g = r.G.find(x => x.ret), s = M.normalise(inp);
  must(Math.abs(g.fv - M.retireMonthly(s) * 12 * Math.pow(1.06, ra - age) * M.retireMultiple(s)) < 1, 'retirement target is not the multiple of yearly spending', { lab });
  const yrs = Math.max(5, s.lifeExp - s.retireAge), fresh = M.paths(mkt, g.y * 12 + yrs * 12, 1500, 4242);
  const step = s.stepup / 100;
  const lasts = fresh.filter(P => M.runRetire(P, s, r.p, r.E, mkt, g.have, g.f1, g.ph, g.sip, g.y, step) >= s.lifeExp).length / 1500;
  retCal.push([lab, Math.round(g.sip), lasts]);
  must(g.sip === 0 || lasts >= .85, 'retirement: a plan that reaches its target corpus should last to 90 in 85% or more of markets', { lab, lasts });
}

// ------------------------------------------------------------- 5. backtest on actual history (every start month)
const [dates, EQ, DE, LI, GO] = mkt.months;
const backtest = [];
for (const [y, p] of [[5, .5], [8, .5], [10, .1], [10, .9]]) {
  const g = { name: 'bt', ret: false, y, fv: 2.5e6, have: 0, mix: M.goalMix(y, p, mkt) }; const s = M.normalise({ stepup: 10 });
  g.sipMean = M.sipFor(g.fv, y, .08, .1); const sip = M.sipForConf(s, p, g, mkt, .75, { nConf: 500, seed: 3 });
  let ok = 0, n = 0, worst = Infinity;
  for (let st = 0; st + y * 12 <= dates.length; st++) {
    let v = 0; for (let t = 0; t < y * 12; t++) { const i = st + t, left = (y * 12 - t) / 12, m = M.goalMix(left, p, mkt), gr = GO[i] ?? 0.008;
      v = v * (1 + m.eq * EQ[i] + m.gold * gr + m.debt * (left < 2 ? LI[i] : DE[i])) + sip * Math.pow(1.1, Math.floor(t / 12)); }
    n++; if (v >= g.fv) ok++; worst = Math.min(worst, v / g.fv);
  }
  backtest.push([`${y}y goal, profile ${p}`, Math.round(sip), n, ok / n, worst]);
}

// ------------------------------------------------------------- 6. typical investors: are the suggested amounts sensible?
const typical = [];
for (const [age, inc, exp, emi, goalsT, label] of [
  [26, 6e4, 3e4, 0, [], 'Single, 26, ₹60k take-home'],
  [32, 1.2e5, 5.5e4, 2.5e4, [['Child education', 2.5e6, 15]], 'Couple, 32, ₹1.2 lakh, home loan'],
  [38, 2e5, 9e4, 4e4, [['Child education', 4e6, 10], ['Car', 1.2e6, 3]], 'Family, 38, ₹2 lakh, two goals'],
  [45, 3e5, 1.4e5, 3e4, [['Child education', 6e6, 4], ['Wedding', 3e6, 9]], 'Family, 45, ₹3 lakh, education soon'],
  [52, 2.5e5, 1.2e5, 0, [], 'Pre-retiree, 52, ₹2.5 lakh'],
  [29, 4e5, 1e5, 0, [['Home down payment', 5e6, 5]], 'Founder, 29, ₹4 lakh, variable']]) {
  const yi = inc * 12;
  const r = M.plan({ age, income: inc, expenses: exp, homeEmi: emi, retireAge: 60, efund: exp * 4, eqmf: yi * (age - 24) * .15, fd: yi * .5, epf: yi * (age - 24) * .1, epfMonthly: inc * .12,
    incomeType: label.includes('Founder') ? 'business' : 'salaried', dependants: label.startsWith('Family') ? 2 : 0, healthCover: 1e6, termCover: yi * 12,
    goals: goalsT.map(([n2, c, y]) => ({ name: n2, cost: c, years: y })), q: qOf(RISK.middle) }, mkt, { nConf: 800 });
  typical.push([label, Math.round(r.surplus), Math.round(r.need), Math.round(r.invest), r.label, r.G.map(g => `${g.name} ${g.y}y ₹${(g.fv / 1e5).toFixed(0)}L sip ${Math.round(g.sip).toLocaleString('en-IN')}`).join(' | ')]);
  must(r.need < inc * 1.5, 'a typical investor is asked for far more than their income', { label, need: r.need, inc });
}

// ------------------------------------------------------------- 6b. goal inflation and the crash replay
{ const s0 = M.normalise({ infl: 6 });
  must(M.goalInfl("Child's higher education", s0) === 10 && M.goalInfl('Parents care', s0) === 10 && M.goalInfl("Daughter's wedding", s0) === 7 && M.goalInfl('New car', s0) === 4 && M.goalInfl('Start a business', s0) === 6, 'goal inflation mapping wrong', {});
  let bad = 0;
  for (let i = 0; i < 300; i++) { const inp = persona(), r = M.plan(inp, mkt, { fast: 1 });
    for (const [ym, y] of [['2008-01', 6], ['2020-01', 3]]) { const x = M.replay(r, mkt, ym, y); if (!x) continue;
      const okPath = x.path.every((q, j) => isFinite(q.v) && q.v >= 0 && (j === 0 || q.put >= x.path[j - 1].put - 1));
      if (!okPath || !(x.equityFall < 0) || (x.worstGap > 1)) bad++; } }
  must(bad === 0, 'replay produced an invalid path', { bad }); }

// ------------------------------------------------------------- 6c. the withdrawal-rate table matches the model's market data
{ const sw = JSON.parse(fs.readFileSync(new URL('../site/planner/swr.json', import.meta.url)));
  const { table } = await import('../tools/planner_swr.mjs');
  const t = table(35, M.paths(mkt, 600, 1500, 777));
  for (const r of [3, 4, 5]) { const a = sw.mixes['35'].find(x => x.rate === r), b = t.find(x => x.rate === r);
    must(Math.abs(a.last30 - b.last30) <= 4 && Math.abs(a.last50 - b.last50) <= 5, 'swr.json out of date: run node tools/planner_swr.mjs', { r, a, b }); }
  const x = sw.mixes['35']; must(x.every((r, i) => !i || (r.last30 <= x[i - 1].last30 && r.last50 <= x[i - 1].last50 && r.kept50 <= x[i - 1].kept50)), 'higher withdrawal lasted longer', {}); }

// ------------------------------------------------------------- 7. the same finances at every age
const ageRows = [];
for (const age of [22, 27, 32, 37, 42, 47, 52, 57, 62, 67, 72]) {
  const ret = age >= 62;
  const row = [age];
  for (const rk of ['allCautious', 'middle', 'allBold']) {
    const r = M.plan({ age, retireAge: ret ? age : 60, incomeType: ret ? 'retired' : 'salaried', income: 1.5e5, expenses: 7e4, efund: 6e5, investing: 'yes', eqmf: 2e6, fd: 1e6, healthCover: 1e6, termCover: 2e7, q: qOf(RISK[rk]) }, mkt, { fast: 1 });
    row.push(`${r.label} ${Math.round(r.E * 100)}%`);
  }
  ageRows.push(row);
}

// ------------------------------------------------------------- report
const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
console.log(`\nPlanner stress test: ${N} investors, ${checks} checks, ${fails.length} failures`);
const uniq = [...new Set(fails.map(f => f.split(' :: ')[0]))];
for (const u of uniq) { const ex = fails.filter(f => f.startsWith(u)); console.log(`  FAIL x${ex.length}: ${ex[0]}`); }
console.log('\nLong-term equity cap by risk answers (mean, min-max):');
for (const [k, v] of Object.entries(stats.E)) console.log(`  ${k.padEnd(15)} ${(avg(v) * 100).toFixed(0)}%  (${(Math.min(...v) * 100).toFixed(0)}-${(Math.max(...v) * 100).toFixed(0)}%)`);
console.log('Profiles:', JSON.stringify(stats.label));
{ const ph = stats.phase.slice().sort((a, b) => a - b), q = x => ph[Math.floor(x * (ph.length - 1))];
  console.log(`Foundation phase (debt + emergency fund): none for ${(ph.filter(x => !x).length / ph.length * 100).toFixed(0)}%; median ${q(.5)}, 90th pct ${q(.9)}, max ${q(1)} months`); }
console.log(`Goals need more than the surplus: ${(stats.needOverSurplus / N * 100).toFixed(0)}% of investors; more than total income: ${(stats.needOverIncome / N * 100).toFixed(0)}%`);
if (stats.corpusMult.length) console.log(`Retirement corpus = ${Math.min(...stats.corpusMult).toFixed(1)}-${Math.max(...stats.corpusMult).toFixed(1)} x the first year's retirement spending`);
console.log('\nEquity % by years to goal:      1y  2y  3y  4y  5y  7y 10y 15y 20y');
for (const r of glideRows) console.log(`  ${r[0].padEnd(28)}` + r.slice(1).map(v => String(v).padStart(4)).join(''));
console.log('\nCalibration (75% SIP on 2,000 fresh simulated markets):');
for (const [l, p, sip, h] of calib) console.log(`  ${l.padEnd(20)} profile ${p}: SIP ${sip.toLocaleString('en-IN')} -> hit ${(h * 100).toFixed(1)}%`);
console.log('\nRetirement: reach 25x-33x yearly spending, then spend to 90 (1,500 fresh paths):');
for (const [l, sip, h] of retCal) console.log(`  ${l.padEnd(16)} SIP ${sip.toLocaleString('en-IN')} -> money lasts to 90 in ${(h * 100).toFixed(1)}%`);
console.log('\nBacktest on actual months since 2007 (every start month, ₹25 lakh target, SIP rising 10% a year):');
for (const [l, sip, n, r2, w] of backtest) console.log(`  ${l.padEnd(24)} SIP ${sip.toLocaleString('en-IN')}: reached in ${(r2 * 100).toFixed(0)}% of ${n} real start months; worst ended at ${(w * 100).toFixed(0)}% of target`);
console.log('\nSame finances (₹1.5 lakh take-home, ₹30 lakh invested) at every age: cautious / middle / bold answers');
for (const r of ageRows) console.log(`  ${String(r[0]).padStart(3)}: ${r.slice(1).map(x => x.padEnd(18)).join('')}`);
console.log('\nTypical investors (middle risk answers):');
for (const [l, sur, need, inv, lab, gs] of typical) console.log(`  ${l.padEnd(40)} surplus ${sur.toLocaleString('en-IN')}, goals need ${need.toLocaleString('en-IN')}, plan invests ${inv.toLocaleString('en-IN')} [${lab}]\n      ${gs}`);
process.exit(fails.length ? 1 : 0);
