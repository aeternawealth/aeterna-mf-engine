// Tests for the website's calculator maths (the CALC block in site/app.html).
//   node tests/calculators.test.mjs
// Each check compares CALC with an answer worked out independently (closed-form formula, textbook value or
// hand calculation), so a change that breaks a formula fails here and in the GitHub "Tests" workflow.
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../site/app.html', import.meta.url), 'utf8');
const a = html.indexOf('/* CALC-START'), b = html.indexOf('/* CALC-END */');
if (a < 0 || b < 0) throw new Error('CALC block not found in site/app.html');
const CALC = new Function(html.slice(a, b) + '; return CALC;')();

let pass = 0, fail = 0;
const near = (name, got, want, tol = 0.01) => {
  const ok = Math.abs(got - want) <= tol;
  ok ? pass++ : fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}: got ${got.toFixed(4)}, expected ${want.toFixed(4)}`);
};
const is = (name, got, want) => { const ok = got === want; ok ? pass++ : fail++; console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}: got ${got}, expected ${want}`); };

// ---- monthly rate convention: 12 months at the monthly rate compound to exactly the yearly rate
near('mrate 12% a year, compounded 12 times', Math.pow(1 + CALC.mrate(12), 12), 1.12, 1e-12);
near('mrate 12% = 0.9489% a month', CALC.mrate(12) * 100, 0.948879, 1e-5);

// ---- SIP: annuity-due closed form  FV = m * ((1+i)^n - 1)/i * (1+i)
{ const m = 10000, i = Math.pow(1.12, 1 / 12) - 1, n = 180;
  near('SIP 10k x 15y @12% vs closed form', CALC.sip(m, 15, 12).bal, m * ((Math.pow(1 + i, n) - 1) / i) * (1 + i));
  near('SIP 10k x 15y @12% invested', CALC.sip(m, 15, 12).inv, 1800000); }
near('SIP at 0% return = money put in', CALC.sip(5000, 10, 0).bal, 600000);
near('SIP step-up 10%, 0% return, 2y', CALC.sip(10000, 2, 0, 10).inv, 120000 + 132000);
{ const r = CALC.sip(10000, 1, 12); near('SIP 1 year: first instalment grows a full year', r.bal,
    [...Array(12)].reduce((s, _, k) => s + 10000 * Math.pow(1.12, (12 - k) / 12), 0)); }

// ---- lump sum
near('Lump 1 lakh x 10y @12%', CALC.lump(100000, 10, 12), 310584.82);
near('Lump 5 lakh x 7y @8%', CALC.lump(500000, 7, 8), 856912.13);

// ---- goal: the SIP it returns must actually reach the goal
{ const g = CALC.goal(2500000, 12, 7, 11, 0);
  near('Goal cost in 12y at 7% inflation', g.fv, 2500000 * Math.pow(1.07, 12));
  near('Goal SIP reaches the goal', CALC.sip(g.sip, 12, 11).bal, g.fv, 0.5);
  near('Goal lump sum reaches the goal', CALC.lump(g.lump, 12, 11), g.fv, 0.01); }
{ const g = CALC.goal(1000000, 10, 6, 10, 200000);
  near('Goal with savings: SIP covers only the gap', CALC.sip(g.sip, 10, 10).bal + 200000 * Math.pow(1.1, 10), g.fv, 0.5); }

// ---- EMI: textbook values (reducing balance, monthly rests, rate/12)
near('EMI 10 lakh @10% x 20y', CALC.emi(1000000, 10, 20).emi, 9650.22);
near('EMI 50 lakh @8.5% x 20y', CALC.emi(5000000, 8.5, 20).emi, 43391.16);
near('EMI 5 lakh @12% x 5y', CALC.emi(500000, 12, 5).emi, 11122.22);
near('EMI at 0% = principal / months', CALC.emi(120000, 0, 1).emi, 10000);
{ const e = CALC.emi(1000000, 10, 20);
  near('EMI schedule ends at zero balance', e.rows[e.rows.length - 1].balance, 0, 0.01);
  near('EMI principal paid sums to the loan', e.rows.reduce((s, r) => s + r.principal, 0), 1000000, 0.01);
  near('EMI total interest', e.interest, 9650.22 * 240 - 1000000, 2); }

// ---- SWP
is('SWP 1.2 lakh, 10k/month, 0% lasts 12 months', CALC.swp(120000, 10000, 0, 0, 5).lastedMonths, 12);
{ const rm = Math.pow(1.08, 1 / 12) - 1; let bal = 1000000; for (let k = 0; k < 24; k++) bal = (bal - 5000) * (1 + rm);
  near('SWP 10 lakh, 5k/month @8%: balance after 2y by hand', CALC.swp(1000000, 5000, 8, 0, 2).bal, bal); }
is('SWP that never runs out reports no end month', CALC.swp(10000000, 20000, 8, 0, 30).lastedMonths, null);
near('SWP yearly rise: total withdrawn, 0% return', CALC.swp(1e9, 1000, 0, 10, 2).withdrawn, 12000 + 13200);

// ---- inflation
near('Inflation 1 lakh x 10y @6% future cost', CALC.infl(100000, 10, 6).future, 179084.77);
near('Inflation 1 lakh in 10y @6% worth today', CALC.infl(100000, 10, 6).today, 55839.48);

// ---- capital-gains tax (Finance (No. 2) Act 2024 defaults; 4% cess; surcharge ignored)
const T = o => CALC.tax({ slab: 30, ...o });
near('Equity 10 months, 3 lakh gain: 20% + cess', T({ asset: 'eq', months: 10, gain: 300000 }).tax, 62400);
near('Equity 18 months, 3 lakh gain: 12.5% above 1.25 lakh', T({ asset: 'eq', months: 18, gain: 300000 }).tax, 175000 * 0.125 * 1.04);
near('Equity exactly 12 months is still short term', T({ asset: 'eq', months: 12, gain: 100000 }).tax, 100000 * 0.20 * 1.04);
near('Equity LT gain under the exemption: no tax', T({ asset: 'eq', months: 24, gain: 100000 }).tax, 0);
near('Debt fund 40 months: slab 30%', T({ asset: 'debt', months: 40, gain: 300000 }).tax, 93600);
near('Listed bond 13 months: 12.5%', T({ asset: 'lbond', months: 13, gain: 300000 }).tax, 39000);
near('Listed bond 6 months: slab', T({ asset: 'lbond', months: 6, gain: 300000, slab: 20 }).tax, 62400);
near('Unlisted shares 30 months: 12.5%', T({ asset: 'unl', months: 30, gain: 300000 }).tax, 39000);
near('Unlisted shares 20 months: slab', T({ asset: 'unl', months: 20, gain: 300000 }).tax, 93600);

// ---- CAGR
near('CAGR 1 lakh -> 2 lakh in 6 years', CALC.cagr(100000, 200000, 6), (Math.pow(2, 1 / 6) - 1) * 100, 1e-9);
near('CAGR inverse of lump sum', CALC.cagr(100000, CALC.lump(100000, 10, 12), 10), 12, 1e-9);
is('CAGR with a zero start is not defined', CALC.cagr(0, 100, 5), null);

// ---- XIRR: one investment held exactly 2 years (730 days) -> CAGR; and a cash-flow set checked by its own NPV
near('XIRR single flow = CAGR', CALC.xirr([{ d: '2023-01-01', a: -100000 }, { d: '2025-01-01', a: 121000 }]),
  (Math.pow(1.21, 365 / 731) - 1) * 100, 1e-6);
{ const fl = [{ d: '2022-01-10', a: -50000 }, { d: '2023-01-10', a: -50000 }, { d: '2024-01-10', a: -50000 }, { d: '2025-01-10', a: -50000 }, { d: '2026-11-13', a: 280000 }];
  const r = CALC.xirr(fl) / 100, t0 = Date.parse('2022-01-10');
  near('XIRR makes NPV zero', fl.reduce((s, x) => s + x.a / Math.pow(1 + r, (Date.parse(x.d) - t0) / 864e5 / 365), 0), 0, 0.01); }
is('XIRR needs money in and out', CALC.xirr([{ d: '2024-01-01', a: -100 }, { d: '2025-01-01', a: -100 }]), null);

// ---- home loan prepay vs invest
{ const base = { P: 5000000, rate: 8.5, years: 20, extra: 10000, r: 12, slab: 30 };
  const x = CALC.prepay(base);
  near('Prepay: EMI equals the EMI calculator', x.emi, CALC.emi(5000000, 8.5, 20).emi, 1e-9);
  is('Prepay: invest scenario closes the loan in the full tenure', x.B.closed, 240);
  is('Prepay: prepaying closes the loan earlier', x.A.closed < 240, true);
  near('Prepay: no extra money -> both scenarios identical', (() => { const y = CALC.prepay({ ...base, extra: 0 }); return y.A.net - y.B.net; })(), 0, 1e-6);
  near('Prepay: both scenarios use the same money', x.A.put + x.A.interest - (x.B.put + x.B.interest), 0, 1);
  { const y = CALC.prepay({ ...base, r: 0 }); is('Prepay at 0% investment return: prepaying wins', y.A.net > y.B.net, true); }
  { const be = CALC.prepayBreakeven(base), y = CALC.prepay({ ...base, r: be });
    near('Prepay break-even return levels the two', y.B.net - y.A.net, 0, 50); } }

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
