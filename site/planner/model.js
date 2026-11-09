/* Aeterna allocation planner: the model (pure functions, no DOM). Used by the page and by tests/planner.test.mjs.
 *
 * plan(input, market)            -> profile, foundations, goals with mixes and SIPs, allocation, monthly plan, flags
 * simulate(result, market, opts) -> outcome ranges over time and each goal's chance of success, from real market months
 *
 * Principles
 *  1. Foundations first: expensive debt, then an emergency fund, then insurance checks; only then goal SIPs.
 *  2. Risk tolerance (answers) and risk capacity (finances) are scored separately; the LOWER one sets the profile.
 *  3. Each goal gets its own mix from its years to go. The equity share is the largest one whose chance of ending
 *     below the money put in (19 years of Indian market months, block bootstrap) stays within the profile's limit,
 *     and never above the profile's long-term cap. Money needed within 2 years holds no equity.
 *  4. Never suggest investing more than the monthly surplus. If goals need more, say so and give options.
 *  5. Retirement is sized from expenses in retirement (not today's), over a life expectancy, net of inflation.
 */
(function (root) {
  'use strict';
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const num = v => { const x = parseFloat(String(v ?? '').replace(/,/g, '')); return isFinite(x) ? x : 0; };

  const DEFAULTS = {
    age: 0, retireAge: 60, lifeExp: 90, dependants: 0, earners: 1, incomeType: 'salaried', slab: 30,
    income: 0, expenses: 0, homeEmi: 0, otherEmi: 0, loanOut: 0, hiDebt: 0, hiRate: 0, sipNow: 0, epfMonthly: 0,
    efund: 0, termCover: 0, healthCover: 0, retireExpPct: 70, retireIncome: 0, retireOther: 0,
    goals: [], investing: 'yes',
    eqmf: 0, stocks: 0, topStock: 0, nfunds: 0, fd: 0, debtmf: 0, savings: 0, gold: 0, epf: 0, ppf: 0, nps: 0, npsEq: 50, realestate: 0, alt: 0,
    q: {}, rEq: 11, rDebt: 7, rGold: 8, rCash: 6, infl: 6, stepup: 10, confidence: 85, investShare: 85, epfGrowth: 6, retireMult: 0,
  };
  const QIDS = ['fall', 'range', 'aim', 'exp', 'past', 'see'];

  function normalise(inp) {
    const s = Object.assign({}, DEFAULTS, inp || {});
    for (const k of Object.keys(DEFAULTS)) if (typeof DEFAULTS[k] === 'number') s[k] = num(s[k]);
    s.q = Object.assign({}, inp && inp.q);
    s.goals = (inp && inp.goals || []).map(g => ({ name: g.name || 'Goal', type: g.type || '', cost: num(g.cost), years: num(g.years), infl: num(g.infl) }));
    if (!s.goals.some(g => g.type === 'retire') && s.incomeType !== 'retired') s.goals.unshift({ name: 'Retirement', type: 'retire', cost: 0, years: 0 });
    return s;
  }

  // ---------------------------------------------------------------- risk
  function riskScores(s) {
    const ans = QIDS.map(k => clamp(num(s.q[k]) || 2, 1, 4));
    // experience (exp, past) counts half: it informs but should not dominate how someone says they'd behave
    const w = [1.3, 1.2, 1.2, 0.6, 0.6, 1.1], tw = w.reduce((a, b) => a + b, 0);
    const tol = clamp(ans.reduce((a, v, i) => a + (v - 1) / 3 * w[i], 0) / tw, 0, 1);
    const retired = s.incomeType === 'retired';
    const emi = s.homeEmi + s.otherEmi, out = s.expenses + emi, surplus = s.income - out;
    const emiRatio = s.income ? emi / s.income : 0, efCover = out ? s.efund / out : 0;
    const horizon = retired ? 0 : Math.max(0, s.retireAge - s.age);
    const why = []; let cap = 1;
    const hit = (c, x, t) => { if (c) { cap -= x; why.push(t); } };
    hit(!retired && horizon < 5, .45, 'less than 5 years until you stop working');
    hit(!retired && horizon >= 5 && horizon < 10, .2, 'under 10 years until you stop working');
    hit(retired, .35, 'living off your savings');
    hit(emiRatio > .5, .3, `EMIs taking ${Math.round(emiRatio * 100)}% of income`);
    hit(emiRatio > .35 && emiRatio <= .5, .15, `EMIs taking ${Math.round(emiRatio * 100)}% of income`);
    hit(s.incomeType === 'variable' || s.incomeType === 'business', .1, 'an income that varies');
    hit(s.dependants >= 2 && s.earners < 2, .12, 'dependants on a single income');
    hit(s.income > 0 && surplus <= 0, .3, 'no monthly surplus');
    hit(s.income > 0 && surplus > 0 && surplus < .1 * s.income, .1, 'a small monthly surplus');
    if (!retired && s.age > 45) { const x = Math.min(.25, (s.age - 45) * .015); cap -= x; if (x >= .05) why.push(`being ${s.age}`); }   // gently more careful with age
    hit(efCover < 3, .15, `${efCover.toFixed(1)} months of emergency money`);   // temporary: the plan fixes it first
    cap = clamp(cap, 0, 1);
    if (retired) cap = Math.min(cap, .35);   // living off savings: a fall cannot be waited out by earning more
    const prof = Math.min(tol, cap);
    return { tol, cap, prof, why, emiRatio, efCover, surplus, out, emi, horizon, retired };
  }
  const PROFILES = [[.25, 'Cautious'], [.6, 'Balanced'], [.8, 'Growth'], [1.01, 'High growth']];
  const profileLabel = p => PROFILES.find(([t]) => p < t)[1];
  const equityCap = p => .25 + .60 * p;            // long-term money: 25% (most cautious) to 85% (most aggressive)
  const lossLimit = p => .005 + .075 * p;          // max chance of ending below the money put in, for goal money

  // ---------------------------------------------------------------- goal mix (data-derived glide path)
  function goalMix(y, p, mkt, floor) {
    const E = equityCap(p);
    let eq = 0;
    const ceil = y < 3 ? 0 : Math.min(.85, .15 + .1 * (y - 3));   // 3y 15%, 5y 35%, 7y 55%, 10y+ 85%
    if (y >= 3) {
      const g = mkt && mkt.glide;
      if (g) {
        const yi = clamp(Math.round(y), 1, 30) - 1, lim = lossLimit(p);
        for (let i = 0; i < g.eq.length; i++) if (g.ploss[yi][i] <= lim && g.eq[i] / 100 <= E + 1e-9) eq = g.eq[i] / 100;
      } else eq = y < 3 ? .1 : y < 5 ? .3 : y < 7 ? .5 : y < 10 ? .65 : E;
      eq = Math.min(eq, E, ceil);
    }
    let gold = y >= 5 ? Math.min(.05 + .05 * p, 1 - eq) : 0;
    if (floor > 0 && eq < floor) { eq = floor; gold = Math.max(gold, .05); }
    return { eq, gold, debt: Math.max(0, 1 - eq - gold), y };
  }
  const mixReturn = (m, s) => m.eq * s.rEq / 100 + m.gold * s.rGold / 100 + m.debt * (m.y < 3 ? s.rCash : s.rDebt) / 100;

  // monthly SIP (rising stepup% a year) whose value after y years at return ret reaches fv
  function sipFor(fv, y, ret, step) {
    if (fv <= 0) return 0;
    const months = Math.round(y * 12); if (months <= 0) return Infinity;
    const rm = Math.pow(1 + ret, 1 / 12) - 1; let unit = 0;
    for (let t = 0; t < months; t++) unit += Math.pow(1 + step, Math.floor(t / 12)) * Math.pow(1 + rm, months - t - 1) * (1 + rm);
    return fv / unit;
  }
  const fvSip = (sip, y, ret, step) => sip > 0 ? sip / (sipFor(1, y, ret, step) || Infinity) : 0;

  // monthly spending in retirement, in today's rupees: what the investor entered, else retireExpPct of today's expenses
  const retireSpend = s => s.retireIncome > 0 ? s.retireIncome : s.expenses * s.retireExpPct / 100;
  const retireMonthly = s => Math.max(0, retireSpend(s) - s.retireOther);   // what the corpus itself must pay
  // the retirement target is a multiple of what the investments must pay in a year, set by how many years the money
  // must last (to age 90 unless the investor plans longer). From site/planner/swr.json (Indian markets since 2007, 6%
  // inflation, 35% equity), each lasted its span in 95 of 100 market histories: 22x for 25 years, 25x (the 4% rule)
  // for 30, 28x for 35, 30x for 40, 33x for 50. 40x keeps the corpus's value for the next generation.
  // Chosen by the investor, or set by these spans.
  const retireConf = s => Math.max(50, s.confidence - 10);
  const retireYears = (s, retireAge) => Math.max(90, s.lifeExp || 90) - (retireAge == null ? s.retireAge : retireAge);
  const retireMultiple = (s, retireAge) => { if (s.retireMult > 0) return s.retireMult; const n = retireYears(s, retireAge);
    return n <= 25 ? 22 : n <= 30 ? 25 : n <= 35 ? 28 : n <= 40 ? 30 : 33; };
  // corpus needed at retirement: that multiple of a year's spending from the corpus, inflated to the retirement date
  function corpus(s, retireAge) {
    const infl = s.infl / 100, y = Math.max(0, retireAge - s.age);
    return retireMonthly(s) * 12 * Math.pow(1 + infl, y) * retireMultiple(s, retireAge);
  }

  // costs rise at different speeds: education and medical care far faster than general prices (% a year)
  const GOAL_INFL = [[/educat|school|college|universit|mba|abroad|study|coaching/i, 10], [/medical|health|hospital|treatment|parent|elder|care/i, 10],
                     [/wedding|marriage|shaadi/i, 7], [/holiday|travel|trip|vacation/i, 7], [/home|house|flat|property|down payment/i, 7], [/car|bike|vehicle/i, 4]];
  const goalInfl = (name, s) => { const m = GOAL_INFL.find(([re]) => re.test(name || '')); return m ? m[1] : s.infl; };

  // ---------------------------------------------------------------- the plan
  function plan(input, mkt, opts = {}) {
    const s = normalise(input), r = riskScores(s), infl = s.infl / 100, step = s.stepup / 100;
    const retired = r.retired, deps = s.dependants, single = s.earners < 2;
    // foundations
    const efMonths = retired ? 12 : Math.min(9, 6 + ((s.incomeType === 'variable' || s.incomeType === 'business') ? 3 : 0) + (deps > 0 && single ? 2 : 0));
    const efTarget = efMonths * r.out, efGap0 = Math.max(0, efTarget - s.efund);
    const payDebt = s.hiDebt > 0 && (s.hiRate === 0 || s.hiRate >= 10);
    const termNeed = !retired && (deps > 0 || s.loanOut > 0) ? Math.max(0, 10 * s.income * 12 + s.loanOut - (s.eqmf + s.stocks + s.fd + s.debtmf + s.epf + s.ppf + s.nps) * .5) : 0;
    const termGap = Math.max(0, termNeed - s.termCover);
    const healthNeed = deps > 0 || s.earners > 1 ? 1e6 : 5e5, healthGap = Math.max(0, healthNeed - s.healthCover);
    const p = r.prof, E = equityCap(p);

    // existing money (own home excluded; property and 'other' stay as they are)
    const npsEq = clamp(s.npsEq, 0, 75) / 100;
    const cur = { Equity: s.eqmf + s.stocks + s.nps * npsEq, Debt: s.fd + s.debtmf + s.epf + s.ppf + s.nps * (1 - npsEq), Gold: s.gold, Cash: s.savings, 'Real estate': s.realestate, Other: s.alt, 'Emergency fund': 0 };
    const total = Object.values(cur).reduce((a, b) => a + b, 0);
    // 1. the emergency fund is filled from idle money first: savings, then debt funds, then FDs
    let efNeed = efGap0; const src = { savings: s.savings, debtmf: s.debtmf, fd: s.fd }, efFrom = {};
    for (const k of ['savings', 'debtmf', 'fd']) { const t = Math.min(efNeed, src[k]); if (t > 0) { efFrom[k] = t; src[k] -= t; efNeed -= t; } }
    const efTop = efGap0 - efNeed, efGap = efNeed;
    const movable = s.eqmf + s.stocks + src.fd + src.debtmf + src.savings + s.gold;   // can be assigned to any goal
    const bag = { savings: src.savings, debtmf: src.debtmf, fd: src.fd, eqmf: s.eqmf, stocks: s.stocks, gold: s.gold };
    const PREF = y => y < 3 ? ['savings', 'debtmf', 'fd', 'gold', 'eqmf', 'stocks'] : y < 7 ? ['debtmf', 'fd', 'eqmf', 'savings', 'gold', 'stocks'] : ['eqmf', 'stocks', 'gold', 'debtmf', 'fd', 'savings'];
    const retLocked = s.epf + s.ppf + s.nps;                                           // retirement only

    // goals: essential ones (retirement, education, parents' care, health) are funded first
    const ESS = /retire|educat|school|college|parent|medical|health|care|wedding|marriage|shaadi/i;
    const G = s.goals.map(g => {
      const ret = g.type === 'retire';
      const y = ret ? (retired ? 0 : Math.max(1, s.retireAge - s.age)) : Math.max(0, Math.round(g.years));
      let fv, how = '';
      if (ret) {
        if (g.cost > 0) { fv = g.cost; how = 'your figure'; }
        else { fv = corpus(s, s.retireAge); how = `${retireMultiple(s)}× a year's spending: ₹${Math.round(retireMonthly(s)).toLocaleString('en-IN')} a month from the corpus, in today's money`; }
      }
      const gi = ret ? s.infl : (g.infl > 0 ? g.infl : goalInfl(g.name, s));
      if (!ret) fv = g.cost * Math.pow(1 + gi / 100, y);
      return { name: g.name, ret, y, fv, how, infl: gi, essential: ret || ESS.test(g.name), mix: goalMix(y, p, mkt, ret ? RMIX(E).eq : 0), today: ret ? 0 : g.cost };
    }).filter(g => g.fv > 0).sort((a, b) => a.y - b.y);

    // 2. today's money goes to the nearest goals first (they have the least time); EPF/PPF/NPS only to retirement
    let pool = movable, rp = retLocked;
    for (const g of G) {
      g.r = mixReturn(g.mix, s);
      const pv = g.fv / Math.pow(1 + g.r, g.y);
      g.have = 0;
      g.sources = [];
      if (g.ret) { const a2 = Math.min(rp, pv); g.have += a2; rp -= a2; if (a2 > 0) g.sources.push(['locked', a2]); }
      for (const k of PREF(g.y)) { const t = Math.min(bag[k], Math.max(0, pv - g.have)); if (t > 0) { g.sources.push([k, t]); bag[k] -= t; g.have += t; pool -= t; } }
      g.extra = g.ret ? fvSip(s.epfMonthly, g.y, .08, s.epfGrowth / 100) : 0;   // future EPF/NPS, rising with salary
      g.left = Math.max(0, g.fv - g.have * Math.pow(1 + g.r, g.y) - g.extra);
    }
    // retirement is the goal nothing else can fund later: every rupee not needed for a nearer goal counts towards it
    // first, so the plan never asks for a SIP while existing money sits unassigned
    const RG0 = G.find(g => g.ret);
    if (RG0 && RG0.y > 0) {
      const add = (k, t) => { if (t <= 0) return; const e = RG0.sources.find(x => x[0] === k); if (e) e[1] += t; else RG0.sources.push([k, t]); RG0.have += t; };
      add('locked', rp); rp = 0;
      for (const k of PREF(RG0.y)) { const t = bag[k]; if (t > 0) { add(k, t); bag[k] = 0; pool -= t; } }
      RG0.left = Math.max(0, RG0.fv - RG0.have * Math.pow(1 + RG0.r, RG0.y) - RG0.extra);
    }
    const wealthMix = goalMix(15, p, mkt), leftover = pool + rp, unassigned = Object.assign({}, bag, { locked: rp });

    // 3. monthly money, in two phases: foundations (debt, emergency fund) first, then everything to goals
    const surplus = Math.max(0, r.surplus), buffer = surplus * (1 - clamp(s.investShare, 50, 100) / 100), avail = surplus - buffer;
    const debtPay = payDebt ? Math.min(avail * .6, s.hiDebt) : 0;
    const efPay = efGap > 0 ? Math.min((avail - debtPay) * .6, Math.max(efGap / 12, 0)) : 0;   // aim to finish within a year
    // goals are never on hold for more than 3 years: the foundation phase ends by then even if the fund is not full
    const phaseMonths = Math.min(36, Math.ceil(Math.max(debtPay ? s.hiDebt / debtPay : 0, efPay ? efGap / efPay : 0)));
    const efReached = r.out ? (s.efund + efTop + efPay * phaseMonths) / r.out : 0;
    const avail1 = avail - debtPay - efPay;
    // the retirement target (25x-40x a year's spending) already carries its own safety margin: a 25x corpus lasted 30
    // years in 95 of 100 market histories. So the SIP aims to reach it 10 points less often than other goals; with
    // the default (75%) the money lasted to 90 in about 98 of 100 histories in testing, against 93 when only typical
    // markets reach it, while asking for 85% too would roughly add half again to the SIP for almost no extra safety.
    const conf = s.confidence / 100, retConf = retireConf(s) / 100, useSim = !opts.fast && mkt && mkt.months;
    // what each goal needs after the foundation phase, given what it gets during it (simulated, or the mean-return formula)
    const needAfter = (g, f1, ph) => {
      if (g.y <= 0) return 0;
      if (useSim) return sipForConf(s, p, g, mkt, g.ret ? retConf : conf, Object.assign({}, opts, { f1, ph }));
      const T = g.y * 12, rest = Math.max(1, T - ph), rm = Math.pow(1 + g.r, 1 / 12) - 1;
      const fvF1 = fvSip(f1, ph / 12, g.r, step) * Math.pow(1 + rm, rest);
      return sipFor(Math.max(0, g.left - fvF1), rest / 12, g.r, step) / Math.pow(1 + step, Math.floor(ph / 12));
    };
    const order = G.slice().sort((a2, b2) => (a2.essential === b2.essential ? a2.y - b2.y : a2.essential ? -1 : 1));
    let rem1 = avail1, rem2 = avail;
    for (const g of order) {
      const ph = Math.min(phaseMonths, g.y * 12);
      g.sipStart = needAfter(g, 0, 0);                       // if it could start in full today
      g.f1 = ph > 0 ? Math.min(rem1, g.sipStart) : 0;
      g.sip = ph > 0 ? needAfter(g, g.f1, ph) : g.sipStart;  // needed after the foundation phase
      g.f2 = Math.min(rem2, isFinite(g.sip) ? g.sip : 0);
      if (ph > 0) rem1 -= g.f1;
      rem2 -= g.f2;
      g.ph = ph; g.fund = g.f2; g.funded = g.sip > 0 ? g.f2 / g.sip : 1;
      g.sipMean = sipFor(g.left, g.y, g.r, step);
    }
    const wealth1 = phaseMonths > 0 ? Math.max(0, rem1) : Math.max(0, rem2), wealth2 = Math.max(0, rem2);
    const need = G.reduce((a2, g) => a2 + (isFinite(g.sip) ? g.sip : 0), 0);
    const later = { avail, need, fits: need <= avail + 1 };

    // 4. when goals need more than there is: push the largest unfunded goal out, or retire later
    let option = null;
    const short = G.filter(g => g.funded < .999 && isFinite(g.sip) && g.y > 0);
    if (short.length && avail > 0) {
      const g = short.reduce((a2, b2) => (b2.sip - b2.fund > a2.sip - a2.fund ? b2 : a2)), ratio = g.sip / Math.max(1, g.sipMean);
      const others = need - g.sip;
      for (let k = 1; k <= 20; k++) {
        const y2 = g.y + k, m2 = goalMix(y2, p, mkt, g.ret ? RMIX(E).eq : 0), r2 = mixReturn(m2, s);
        const fv2 = g.ret && !(s.goals.find(x => x.type === 'retire') || {}).cost ? corpus(s, s.retireAge + k) : g.fv * Math.pow(1 + g.infl / 100, k);
        const ex2 = g.ret ? fvSip(s.epfMonthly, y2, .08, s.epfGrowth / 100) : 0;
        const s2 = sipFor(Math.max(0, fv2 - g.have * Math.pow(1 + r2, y2) - ex2), y2, r2, step) * ratio;
        if (others + s2 <= avail) { option = { goal: g.name, years: k, sip: s2, retire: g.ret }; break; }
      }
      if (!option) option = { goal: g.name, none: true, retire: g.ret };
    }

    // 5. target allocation of today's money: each goal's share at its mix now, the rest at the long-term mix
    cur['Arbitrage & liquid'] = 0;
    const tgt = { Equity: 0, Debt: 0, Gold: 0, Cash: 0, 'Arbitrage & liquid': 0, 'Real estate': cur['Real estate'], Other: cur.Other, 'Emergency fund': efTop };
    const put = (amt, m) => { tgt.Equity += amt * m.eq; tgt.Gold += amt * m.gold; if (m.y < 3) tgt['Arbitrage & liquid'] += amt * m.debt; else tgt.Debt += amt * m.debt; };
    G.forEach(g => put(g.have, g.mix)); put(leftover, wealthMix);
    const tgtTotal = Object.values(tgt).reduce((a2, b2) => a2 + b2, 0);

    // 6. fund categories for each rupee, for each phase
    const catsFor = (dp, ep, field, wealth) => {
      const cats = {};
      const addc = (name, url, v) => { if (v < 1) return; const c = cats[name] = cats[name] || { v: 0, url }; c.v += v; };
      if (dp) addc('Repay expensive debt', '', dp);
      if (ep) addc(s.slab >= 20 ? 'Emergency fund: arbitrage funds (a month or two in a liquid fund)' : 'Emergency fund: liquid funds', s.slab >= 20 ? '/mutual-funds/arbitrage/' : '', ep);
      G.forEach(g => vehicles(g[field], g.mix, g.y, p, s).forEach(([n2, u, x]) => addc(n2, u, x)));
      vehicles(wealth, wealthMix, 15, p, s).forEach(([n2, u, x]) => addc(n2, u, x));
      return cats;
    };
    const c1 = phaseMonths > 0 ? catsFor(debtPay, efPay, 'f1', wealth1) : null, c2 = catsFor(0, 0, 'f2', wealth2);
    const names = [...new Set([...(c1 ? Object.keys(c1) : []), ...Object.keys(c2)])];
    const catList = names.map(k => ({ name: k, url: (c2[k] || c1[k]).url, v1: c1 ? (c1[k] ? c1[k].v : 0) : null, v: c2[k] ? c2[k].v : 0 }))
      .sort((a2, b2) => (b2.v + (b2.v1 || 0)) - (a2.v + (a2.v1 || 0)));
    const invest1 = phaseMonths > 0 ? debtPay + efPay + G.reduce((a2, g) => a2 + (g.ph > 0 ? g.f1 : g.f2), 0) + wealth1 : null;
    const invest = G.reduce((a2, g) => a2 + g.f2, 0) + wealth2;

    // 7. retirement in numbers
    const RG = G.find(g => g.ret);
    const retire = RG ? { spendToday: retireSpend(s), other: s.retireOther, monthlyToday: retireMonthly(s), monthlyThen: retireMonthly(s) * Math.pow(1 + infl, RG.y), corpus: RG.fv, years: Math.max(5, s.lifeExp - s.retireAge),
      multiple: retireMultiple(s), have: RG.have, haveThen: RG.have * Math.pow(1 + RG.r, RG.y), extra: RG.extra, sip: RG.sip, fund: RG.f2, f1: RG.f1, ph: RG.ph, y: RG.y, custom: s.retireIncome > 0 } : null;

    return { retire, unassigned, s, r, p, E, label: profileLabel(p), efMonths, efTarget, efGap0, efGap, efTop, efFrom, efReached, payDebt, termNeed, termGap, healthNeed, healthGap,
      cur, total, tgt, tgtTotal, G, wealthMix, leftover, surplus, buffer, avail, debtPay, efPay, phaseMonths, need, wealth: wealth2, wealth1, later, option,
      cats: catList, invest, invest1 };
  }

  // which fund categories carry a sleeve (no index funds; hybrids for mid-term goals)
  function vehicles(v, m, y, p, s) {
    if (v < 1) return [];
    const arb = s.slab >= 20;
    if (y < 1) return [[arb ? 'Arbitrage or liquid funds' : 'Liquid or money market funds', arb ? '/mutual-funds/arbitrage/' : '', v]];
    if (y < 3) return [[arb ? 'Arbitrage funds (taxed as equity)' : 'Money market or short duration funds', arb ? '/mutual-funds/arbitrage/' : '', v]];
    if (y < 5) return [['Equity savings funds (part equity, part arbitrage and debt; taxed as equity)', '', v]];
    if (y < 7) return [['Balanced advantage funds (equity share adjusted to valuations)', '', v * (m.eq + m.debt)], ['Gold funds', '', v * m.gold]];
    const out = [], eqv = v * m.eq;
    const split = p < .2 ? [['Large cap funds', '/mutual-funds/large-cap/', .5], ['Large & mid cap funds', '/mutual-funds/large-and-mid-cap/', .25], ['Flexi cap funds', '/mutual-funds/flexi-cap/', .25]]
      : p < .45 ? [['Large cap funds', '/mutual-funds/large-cap/', .3], ['Flexi or multi cap funds', '/mutual-funds/flexi-cap/', .4], ['Large & mid cap funds', '/mutual-funds/large-and-mid-cap/', .2], ['Mid cap funds', '/mutual-funds/mid-cap/', .1]]
      : p < .7 ? [['Large cap funds', '/mutual-funds/large-cap/', .2], ['Flexi or multi cap funds', '/mutual-funds/flexi-cap/', .4], ['Mid cap funds', '/mutual-funds/mid-cap/', .25], ['Small cap funds', '/mutual-funds/small-cap/', .15]]
      : [['Large cap funds', '/mutual-funds/large-cap/', .15], ['Flexi or multi cap funds', '/mutual-funds/flexi-cap/', .35], ['Mid cap funds', '/mutual-funds/mid-cap/', .25], ['Small cap funds', '/mutual-funds/small-cap/', .25]];
    if (eqv < 6000) out.push(['Flexi or multi cap funds', '/mutual-funds/flexi-cap/', eqv]);   // small SIPs: one fund, not five
    else split.forEach(([n2, u, w]) => out.push([n2, u, eqv * w]));
    out.push([y >= 10 ? 'Corporate bond or banking & PSU debt funds' : 'Short duration or corporate bond funds', '', v * m.debt]);
    out.push(['Gold funds', '', v * m.gold]);
    return out;
  }

  // ---------------------------------------------------------------- simulation on real market months
  function rng(seed) { let x = seed >>> 0 || 1; return () => { x ^= x << 13; x >>>= 0; x ^= x >> 17; x ^= x << 5; x >>>= 0; return x / 4294967296; }; }
  function paths(mkt, months, n, seed, block = 12) {
    const [, eq, de, li, go] = mkt.months, T = eq.length, R = rng(seed), goldOk = go.map((v, i) => v == null ? -1 : i).filter(i => i >= 0);
    const out = [];
    for (let k = 0; k < n; k++) {
      const e = new Float64Array(months), d = new Float64Array(months), l = new Float64Array(months), g = new Float64Array(months);
      for (let t = 0; t < months;) {
        const st = Math.floor(R() * (T - block));
        for (let b = 0; b < block && t < months; b++, t++) {
          const i = st + b; e[t] = eq[i]; d[t] = de[i]; l[t] = li[i];
          g[t] = go[i] != null ? go[i] : go[goldOk[Math.floor(R() * goldOk.length)]];
        }
      }
      out.push({ e, d, l, g });
    }
    return out;
  }
  // value of one goal's money at its date: starts with `have`, adds a SIP rising yearly, de-risks as the date nears
  const MIX = new Map();
  function mixSeries(months, p, mkt, floor) {
    const k = months + '|' + p.toFixed(5) + '|' + (floor || 0); let a = MIX.get(k);
    if (!a) { a = []; for (let t = 0; t < months; t++) { const left = (months - t) / 12; a.push(goalMix(left, p, mkt, floor)); } MIX.set(k, a); if (MIX.size > 400) MIX.delete(MIX.keys().next().value); }
    return a;
  }
  function runBucket(P, have, sip, years, step, p, mkt, extra, xg, f1, ph, floor) {
    const months = Math.round(years * 12), mx = mixSeries(months, p, mkt, floor); let v = have; ph = ph || 0;
    for (let t = 0; t < months; t++) {
      const left = (months - t) / 12, m = mx[t];
      const rd = left < 2 ? P.l[t] : P.d[t];
      v = v * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * rd) + (t < ph ? f1 : sip) * Math.pow(1 + step, Math.floor(t / 12)) + (extra || 0) * Math.pow(1 + (xg ?? step), Math.floor(t / 12));
    }
    return v;
  }
  // retirement, end to end: save until the retirement date (de-risking on the glide path), then pay the monthly
  // spending, rising with inflation, from a retirement mix. Returns the age the money runs out (Infinity = lasts).
  const RMIX = E => { const eq = Math.min(.35, E); return { eq, gold: .05, debt: .95 - eq }; };
  // guard: after a year in which the portfolio lost money, skip that year's inflation increase in spending (the
  // 'inflation rule' of Guyton and Klinger). untilAge: how far to run (default: life expectancy).
  function runRetire(P, s, p, E, mkt, have, f1, ph, sip, y, step, guard, untilAge, out) {
    const acc = Math.round(y * 12), yrs = Math.max(5, (untilAge || s.lifeExp) - s.retireAge), T = Math.min(P.e.length, acc + yrs * 12), mx = mixSeries(acc, p, mkt, RMIX(E).eq), rm = RMIX(E);
    const infl = s.infl / 100, xg = s.epfGrowth / 100; let v = have, W = retireMonthly(s) * Math.pow(1 + infl, acc / 12), V0 = 0, skipped = 0, yr = 1, real85 = null;
    for (let t = 0; t < T; t++) {
      if (t < acc) {
        const left = (acc - t) / 12, m = mx[t], rd = left < 2 ? P.l[t] : P.d[t], up = Math.pow(1 + step, Math.floor(t / 12));
        v = v * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * rd) + (t < ph ? f1 : sip) * up + s.epfMonthly * Math.pow(1 + xg, Math.floor(t / 12));
      } else {
        if (t === acc) { V0 = v; if (out) out.atRetire = v; }
        else if ((t - acc) % 12 === 0) {   // a new year of retirement
          if (guard && yr < 1) skipped++; else W *= 1 + infl;
          yr = 1;
        }
        const g1 = 1 + rm.eq * P.e[t] + rm.gold * P.g[t] + rm.debt * P.d[t]; yr *= g1;
        if (s.age + t / 12 >= 85 && real85 == null) real85 = W / Math.pow(1 + infl, t / 12) / Math.max(1, retireMonthly(s));
        v = v * g1 - W;
        if (v <= 0) { if (out) { out.skipped = skipped; out.real85 = real85; } return s.age + t / 12; }
      }
    }
    if (out) { out.skipped = skipped; out.end = v; out.real85 = real85; }
    return Infinity;
  }

  // SWP from the retirement corpus, path by path: save until the retirement date as planned, then withdraw monthly until
  // age 100. mode 'inflation': amount is in today's money and rises with prices every year; mode 'fixed': amount is
  // the same rupees every month from retirement. Returns yearly percentiles (actual rupees and today's money).
  function swp(res, mkt, opts = {}) {
    const s = res.s, g = res.G.find(x => x.ret); if (!g) return null;
    const n = opts.n || 500, infl = s.infl / 100, step = s.stepup / 100, top = 100, acc = Math.round(g.y * 12), yrs = top - s.retireAge;
    const Ps = paths(mkt, acc + yrs * 12, n, (opts.seed || 31337)), rm = RMIX(res.E), mx = mixSeries(acc, res.p, mkt, RMIX(res.E).eq), xg = s.epfGrowth / 100;
    const mode = opts.mode || 'inflation', amt = opts.amount > 0 ? opts.amount : retireMonthly(s), guard = !!opts.guard;
    const vals = Array.from({ length: yrs + 1 }, () => []), ends = [], wdYear = [];
    for (const P of Ps) {
      let v = g.have, W = 0, yr = 1, ended = Infinity;
      for (let t = 0; t < acc; t++) {
        const left = (acc - t) / 12, m = mx[t], rd = left < 2 ? P.l[t] : P.d[t], up = Math.pow(1 + step, Math.floor(t / 12));
        v = v * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * rd) + (t < g.ph ? g.f1 : g.f2) * up + s.epfMonthly * Math.pow(1 + xg, Math.floor(t / 12));
      }
      vals[0].push(v);
      W = mode === 'fixed' ? amt : amt * Math.pow(1 + infl, acc / 12);
      for (let k = 0; k < yrs * 12; k++) {
        const t = acc + k;
        if (k > 0 && k % 12 === 0) { if (mode !== 'fixed' && !(guard && yr < 1)) W *= 1 + infl; yr = 1; }
        const g1 = 1 + rm.eq * P.e[t] + rm.gold * P.g[t] + rm.debt * P.d[t]; yr *= g1;
        if (v > 0) { v = v * g1 - W; if (v <= 0) { v = 0; if (ended === Infinity) ended = s.retireAge + (k + 1) / 12; } }
        if ((k + 1) % 12 === 0) vals[(k + 1) / 12].push(v);
      }
      ends.push(ended);
    }
    // the withdrawal schedule is the same on every path (it does not depend on returns unless the guardrail is on)
    let W = mode === 'fixed' ? amt : amt * Math.pow(1 + infl, acc / 12);
    for (let y = 0; y < yrs; y++) { wdYear.push({ age: s.retireAge + y, monthly: W, real: W / Math.pow(1 + infl, (acc / 12) + y) }); if (mode !== 'fixed') W *= 1 + infl; }
    ends.sort((a, b) => a - b);
    const q = (a, x) => a[Math.floor(x * (a.length - 1))];
    const years = vals.map((a, y) => { a.sort((x1, x2) => x1 - x2); const d = Math.pow(1 + infl, acc / 12 + y);
      return { age: s.retireAge + y, p10: q(a, .1), p50: q(a, .5), p90: q(a, .9), p10r: q(a, .1) / d, p50r: q(a, .5) / d, p90r: q(a, .9) / d }; });
    const to = x => ends.filter(a => a >= x).length / n;
    return { mode, amount: amt, years, wd: wdYear, ends: { p10: q(ends, .1), p25: q(ends, .25), p50: q(ends, .5) }, to: { 85: to(85), 90: to(90), 95: to(95), 100: to(100) }, n };
  }

  // the plan replayed through what actually happened, month by month, from a given month (e.g. '2008-01'):
  // today's money and the planned SIPs, each goal on its glide path and paid out on its date. Returns the path,
  // the largest fall from a peak (rupees and %), when it bottomed and when it recovered.
  function replay(res, mkt, startYm, years) {
    const [dates, EQ, DE, LI, GO] = mkt.months, i0 = dates.indexOf(startYm);
    if (i0 < 0) return null;
    const T = Math.min(Math.round(years * 12), dates.length - i0), step = res.s.stepup / 100, s0 = res.s, RG = res.G.find(g => g.ret);
    const b = res.G.map(g => ({ g, v: g.have, mx: mixSeries(Math.round(g.y * 12), res.p, mkt, g.ret ? RMIX(res.E).eq : 0), done: false }));
    let w = res.leftover, put = res.total - res.cur['Real estate'] - res.cur.Other, spent = 0, worst = 0, worstAt = -1, rec = null, eqIdx = 1, eqPeak = 1, eqFall = 0, eqBottom = null, ef = res.efTop;
    const path = [];
    for (let t = 0; t < T; t++) {
      const i = i0 + t, e = EQ[i], d = DE[i], l = LI[i], gd = GO[i] != null ? GO[i] : .007, up = Math.pow(1 + step, Math.floor(t / 12));
      for (const x of b) {
        const m12 = Math.round(x.g.y * 12);
        if (x.done || t >= m12) continue;
        const left = (m12 - t) / 12, m = x.mx[t], rd = left < 2 ? l : d, c = (t < x.g.ph ? x.g.f1 : x.g.f2) * up + (x.g.ret ? s0.epfMonthly * Math.pow(1 + s0.epfGrowth / 100, Math.floor(t / 12)) : 0);
        x.v = x.v * (1 + m.eq * e + m.gold * gd + m.debt * rd) + c; put += c;
        if (t === m12 - 1 && !x.g.ret) { spent += x.v; x.v = 0; x.done = true; }
      }
      const wm = res.wealthMix, wc = (RG && t >= Math.round(RG.y * 12)) ? 0 : (t < res.phaseMonths ? res.wealth1 : res.wealth) * up;
      w = w * (1 + wm.eq * e + wm.gold * gd + wm.debt * d) + wc; put += wc;
      const ec = t < res.phaseMonths ? res.efPay : 0; ef = ef * (1 + l) + ec; put += ec;
      const tot = b.reduce((a, x) => a + x.v, 0) + w + spent + ef;   // goals already paid count as 'achieved', not lost
      path.push({ ym: dates[i], v: tot, put });
      const gap = tot - put;   // value against money put in (a paper loss when negative)
      if (gap < worst) { worst = gap; worstAt = t; rec = null; }
      if (worstAt >= 0 && rec == null && t > worstAt && gap >= 0) rec = t;
      eqIdx *= 1 + e; eqPeak = Math.max(eqPeak, eqIdx); if (eqIdx / eqPeak - 1 < eqFall) { eqFall = eqIdx / eqPeak - 1; eqBottom = dates[i]; }
    }
    const last = path[path.length - 1], wp = worstAt >= 0 ? path[worstAt] : null;
    return { start: startYm, path, months: T, worstGap: worst, worstYm: wp && wp.ym, worstPut: wp && wp.put, worstValue: wp && wp.v,
      recoveredYm: rec != null ? path[rec].ym : null, monthsToRecover: rec != null ? rec - worstAt : null, end: last.v, put: last.put, endYm: last.ym, equityFall: eqFall, equityBottom: eqBottom };
  }

  function simulate(res, mkt, opts = {}) {
    const n = opts.n || 600, seed = opts.seed || 20261107, step = res.s.stepup / 100;
    const maxY = Math.max(15, ...res.G.map(g => g.y)), months = Math.round(Math.min(40, maxY) * 12);
    const Ps = paths(mkt, months, n, seed);
    const goals = res.G.map(g => {
      if (g.y <= 0) return { name: g.name, prob: g.left > 0 ? 0 : 1 };
      if (g.ret) {
        const top = Math.max(100, res.s.lifeExp), PR = paths(mkt, Math.round(g.y * 12) + (top - res.s.retireAge) * 12, n, seed + 7);
        const run = guard => { const at = [], sk = [], r85 = []; const ages = PR.map(P => { const o = {}; const a = runRetire(P, res.s, res.p, res.E, mkt, g.have, g.f1, g.ph, g.f2, g.y, step, guard, top, o); at.push(o.atRetire || 0); sk.push(o.skipped || 0); if (o.real85 != null) r85.push(o.real85); return a; }).sort((a, b) => a - b);
          sk.sort((a, b) => a - b); r85.sort((a, b) => a - b);
          const to = x => ages.filter(a => a >= x).length / n; at.sort((a, b) => a - b);
          return { ages, to: { 85: to(85), 90: to(90), 95: to(95), 100: to(100) }, prob: to(res.s.lifeExp), p10age: ages[Math.floor(n * .1)], p25age: ages[Math.floor(n * .25)], p50age: ages[Math.floor(n * .5)], corp50: at[Math.floor(n * .5)], corp10: at[Math.floor(n * .1)], skipped50: sk[Math.floor(n * .5)], real85: r85.length ? r85[Math.floor(r85.length * .5)] : null, real85low: r85.length ? r85[Math.floor(r85.length * .1)] : null }; };
        const plain = run(false), guarded = run(true);
        return Object.assign({ name: g.name, ret: true, guarded }, plain);
      }
      const vals = Ps.map(P => runBucket(P, g.have, g.f2, g.y, step, res.p, mkt, g.ret ? res.s.epfMonthly : 0, res.s.epfGrowth / 100, g.f1, g.ph, g.ret ? RMIX(res.E).eq : 0)).sort((a, b) => a - b);
      return { name: g.name, prob: vals.filter(v => v >= g.fv * .999).length / n, p10: vals[Math.floor(n * .1)], p50: vals[Math.floor(n * .5)], p90: vals[Math.floor(n * .9)], fv: g.fv };
    });
    // total portfolio over time: goals are paid out on their dates; the retirement corpus then pays the monthly
    // spending (rising with inflation) from a retirement mix until life expectancy. Yearly percentiles.
    const s0 = res.s, infl = s0.infl / 100, RG = res.G.find(g => g.ret);
    const horizon = RG ? Math.max(maxY, RG.y + Math.max(5, s0.lifeExp - s0.retireAge)) : maxY;
    const T = Math.round(Math.min(60, horizon) * 12), years = Math.round(T / 12), fan = [], lastAge = [];
    const P2 = paths(mkt, T, n, seed + 1);
    const rmix = { eq: Math.min(.35, res.E), gold: .05 }; rmix.debt = 1 - rmix.eq - rmix.gold;
    const wd = RG ? retireMonthly(s0) : 0;
    const totals = P2.map(P => {
      const row = []; const b = res.G.map(g => ({ g, v: g.have, done: false })); let w = res.leftover, out = null, ef = res.efTop;
      for (let t = 0; t < T; t++) {
        const k = Math.floor(t / 12), up = Math.pow(1 + step, k);
        for (const x of b) {
          const m12 = Math.round(x.g.y * 12);
          if (x.done && !(x.g.ret)) continue;
          if (x.g.ret && t >= m12) {   // drawdown: spend, then grow at the retirement mix
            if (x.v <= 0) continue;
            x.v = x.v * (1 + rmix.eq * P.e[t] + rmix.gold * P.g[t] + rmix.debt * P.d[t]) - wd * Math.pow(1 + infl, t / 12);
            if (x.v <= 0) { w += x.v; x.v = 0; if (out == null) out = t; }   // retirement money gone: spending comes from other savings
            continue;
          }
          const left = (m12 - t) / 12, m = goalMix(left, res.p, mkt, x.g.ret ? RMIX(res.E).eq : 0), rd = left < 2 ? P.l[t] : P.d[t];
          x.v = x.v * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * rd) + (t < x.g.ph ? x.g.f1 : x.g.f2) * up + (x.g.ret ? res.s.epfMonthly * Math.pow(1 + res.s.epfGrowth / 100, k) : 0);
          if (!x.g.ret && t === m12 - 1) { x.v = 0; x.done = true; }   // spent on the goal at the end of its last month
        }
        const m = res.wealthMix;
        w = w * (1 + m.eq * P.e[t] + m.gold * P.g[t] + m.debt * P.d[t]) + (RG && t >= Math.round(RG.y * 12) ? 0 : (t < res.phaseMonths ? res.wealth1 : res.wealth) * up);
        ef = ef * (1 + P.l[t]) + (t < res.phaseMonths ? res.efPay : 0);
        if ((t + 1) % 12 === 0) row.push(b.reduce((a, x) => a + x.v, 0) + w + ef);
      }
      lastAge.push(out == null ? Infinity : s0.age + out / 12);
      return row;
    });
    for (let yv = 0; yv < years; yv++) {
      const col = totals.map(r2 => r2[yv]).sort((a, b) => a - b);
      const d = Math.pow(1 + infl, yv + 1);   // in today's money
      fan.push({ year: yv + 1, age: s0.age + yv + 1, p10: col[Math.floor(n * .1)] / d, p50: col[Math.floor(n * .5)] / d, p90: col[Math.floor(n * .9)] / d });
    }
    lastAge.sort((a, b) => a - b);
    const lasts = RG ? { p10: lastAge[Math.floor(n * .1)], p50: lastAge[Math.floor(n * .5)], toLife: lastAge.filter(a => a >= s0.lifeExp).length / n, lifeExp: s0.lifeExp } : null;
    const payouts = res.G.filter(g => !g.ret && g.y > 0 && g.y <= years).map(g => ({ name: g.name, y: g.y, amt: g.fv, today: g.fv / Math.pow(1 + infl, g.y) }));
    return { goals, fan, n, lasts, payouts };
  }
  // monthly amount for one goal that reaches its target in `conf` of simulated markets (bisection)
  function sipForConf(s, p, g, mkt, conf, opts = {}) {
    if (g.y <= 0) return Infinity;
    const step = s.stepup / 100;
    if (g.ret && opts.lasting) {   // optional: size for the money lasting to lifeExp instead of reaching the target
      const n = opts.nConf || 1500, yrs = Math.max(5, s.lifeExp - s.retireAge), Ps = paths(mkt, Math.round(g.y * 12) + yrs * 12, n, opts.seed || 99), E = equityCap(p);
      const f1 = opts.f1 || 0, ph = opts.ph || 0, tgt = Math.min(.99, conf + .03);
      const ok = sip => Ps.filter(P => runRetire(P, s, p, E, mkt, g.have, f1, ph, sip, g.y, step) >= s.lifeExp).length / n >= tgt;
      if (ok(0)) return 0;
      let lo = 0, hi = Math.max(1000, sipFor(g.left || g.fv, g.y, .08, step) * 2);
      while (!ok(hi) && hi < 1e9) hi *= 2;
      for (let i = 0; i < 20; i++) { const mid = (lo + hi) / 2; if (ok(mid)) hi = mid; else lo = mid; }
      return hi;
    }
    const n = opts.nConf || 1500, Ps = paths(mkt, Math.round(g.y * 12), n, opts.seed || 99);
    // aim 3 points above the target in-sample: a SIP fitted exactly to one set of paths falls ~3 points short on fresh ones
    const f1 = opts.f1 || 0, ph = opts.ph || 0;
    const ok = sip => Ps.filter(P => runBucket(P, g.have, sip, g.y, step, p, mkt, g.ret ? s.epfMonthly : 0, s.epfGrowth / 100, f1, ph, g.ret ? RMIX(equityCap(p)).eq : 0) >= g.fv).length / n >= Math.min(.99, conf + .03);
    if (ok(0)) return 0;
    let lo = 0, hi = Math.max(1000, sipFor(g.left || g.fv, g.y, .08, step) * 4);
    while (!ok(hi) && hi < 1e9) hi *= 2;
    for (let i = 0; i < 22; i++) { const mid = (lo + hi) / 2; if (ok(mid)) hi = mid; else lo = mid; }
    return hi;
  }

  const api = { retireYears, retireConf, retireMultiple, replay, goalInfl, swp, retireSpend, runRetire, RMIX, retireMonthly, corpus, mixSeries, DEFAULTS, QIDS, normalise, riskScores, goalMix, equityCap, lossLimit, profileLabel, sipFor, fvSip, plan, vehicles, simulate, sipForConf, paths };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.PlannerModel = api;
})(typeof window !== 'undefined' ? window : globalThis);
