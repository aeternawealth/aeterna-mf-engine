/* Growth of ₹10,000 on fund pages: the fund's month-end NAV against its index (total return), from the same
   /data/series files the site already publishes. Loads only when the chart scrolls near the screen; one copy of
   this file and of each data file is cached across every fund page. */
(() => {
  const C = {};
  const get = u => C[u] || (C[u] = fetch(u).then(r => r.ok ? r.json() : null).catch(() => null));
  const MON = m => { const [a, b] = m.split('-'); return new Date(+a, +b - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: 'numeric' }); };
  const DAY = d => new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  const inr = v => '₹' + Math.round(v).toLocaleString('en-IN');
  const trim = x => x.replace(/\.0$/, '');
  const short = v => v >= 1e7 ? '₹' + trim((v / 1e7).toFixed(1)) + 'Cr' : v >= 1e5 ? '₹' + trim((v / 1e5).toFixed(1)) + 'L' : '₹' + trim((v / 1e3).toFixed(1)) + 'k';
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const PERIODS = [['1Y', 12], ['3Y', 36], ['5Y', 60], ['10Y', 120], ['Max', 1e9]];

  function points(s, b, l, code, bn) {
    const nav = s.nav[code] || [], tri = b && bn ? (b.tri[bn] || []) : [];
    const bi = b ? Object.fromEntries(b.months.map((m, i) => [m, i])) : {};
    const P = [];
    s.months.forEach((m, i) => {
      const v = nav[i];
      if (v == null) return;
      const j = bi[m];
      P.push({ m, label: MON(m), nav: v, tri: j != null && tri[j] != null ? tri[j] : null });
    });
    const ln = l && l.nav && l.nav[code], lt = l && l.tri && bn && l.tri[bn];
    if (ln && P.length && ln[0].slice(0, 7) > P[P.length - 1].m) {
      P.push({ m: ln[0].slice(0, 7), label: DAY(ln[0]), nav: ln[1], tri: lt ? lt[1] : null, latest: true });
    }
    return P;
  }

  function render(el, st) {
    const { P, name, bname } = st;
    const n = P.length;
    const months = st.period === 'Max' ? n - 1 : Math.min(n - 1, PERIODS.find(p => p[0] === st.period)[1]);
    const S = P.slice(n - 1 - months);
    const hasIdx = S.every(p => p.tri != null) && !!bname;
    const f0 = S[0].nav, t0 = hasIdx ? S[0].tri : 1;
    const V = S.map(p => ({ ...p, f: 10000 * p.nav / f0, t: hasIdx ? 10000 * p.tri / t0 : null }));
    const W = Math.max(300, el.querySelector('.fc-plot').clientWidth), H = 250, L = 52, R = 12, T = 12, B = 28;
    const all = V.flatMap(p => hasIdx ? [p.f, p.t] : [p.f]);
    let lo = Math.min(...all), hi = Math.max(...all);
    const pad = (hi - lo) * 0.08 || 500; lo -= pad; hi += pad;
    const x = i => L + (V.length > 1 ? i / (V.length - 1) : 0.5) * (W - L - R);
    const y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    const path = k => V.map((p, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(p[k]).toFixed(1)).join('');
    const raw = (hi - lo) / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(v => v >= raw);
    const grid = []; for (let g = Math.ceil(lo / step) * step; g <= hi; g += step) grid.push(g);
    const nt = W < 480 ? 3 : 5, ticks = [...new Set(Array.from({ length: nt }, (_, k) => Math.round(k * (V.length - 1) / (nt - 1))))];
    const end = V[V.length - 1];
    el.querySelector('.fc-plot').innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="Growth of ₹10,000 in ${esc(name)} from ${S[0].label} to ${end.label}: ${inr(end.f)}${hasIdx ? `, against ${inr(end.t)} in the ${esc(bname)}` : ''}.">
        ${grid.map(g => `<line x1="${L}" x2="${W - R}" y1="${y(g).toFixed(1)}" y2="${y(g).toFixed(1)}" stroke="var(--rule)"/><text x="${L - 8}" y="${(y(g) + 4).toFixed(1)}" text-anchor="end" font-size="11.5" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${short(g)}</text>`).join('')}
        <line x1="${L}" x2="${W - R}" y1="${y(10000).toFixed(1)}" y2="${y(10000).toFixed(1)}" stroke="var(--ink-3)" stroke-dasharray="2 3" opacity=".6"/>
        ${ticks.map(i => `<text x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="${i === 0 ? 'start' : i === V.length - 1 ? 'end' : 'middle'}" font-size="11.5" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${V[i].label.replace(/^\d+ /, '')}</text>`).join('')}
        ${hasIdx ? `<path d="${path('t')}" fill="none" stroke="var(--ink-3)" stroke-width="1.6" stroke-dasharray="5 4" stroke-linejoin="round"/>` : ''}
        <path d="${path('f')}" fill="none" stroke="var(--teal)" stroke-width="2.4" stroke-linejoin="round"/>
        <g class="fc-hover" visibility="hidden"><line class="fc-x" y1="${T}" y2="${H - B}" stroke="var(--ink-3)" stroke-width="1"/>
          <circle class="fc-df" r="4.5" fill="var(--teal)" stroke="var(--surface)" stroke-width="2"/>${hasIdx ? '<circle class="fc-dt" r="4" fill="var(--ink-3)" stroke="var(--surface)" stroke-width="2"/>' : ''}</g>
        <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" class="fc-hit"/>
      </svg>`;
    const diff = hasIdx ? end.f - end.t : null;
    el.querySelector('.fc-sum').innerHTML = `₹10,000 invested in <b>${S[0].label}</b> would be worth <b>${inr(end.f)}</b> on ${end.label}` +
      (hasIdx ? `, against <b>${inr(end.t)}</b> in the ${esc(bname)} (${diff >= 0 ? 'ahead by' : 'behind by'} ${inr(Math.abs(diff))}).` : '.');
    el.querySelectorAll('.fc-tabs button').forEach(bt => bt.setAttribute('aria-pressed', bt.dataset.p === st.period));
    const svg = el.querySelector('svg'), hov = svg.querySelector('.fc-hover'), tip = el.querySelector('.fc-tip');
    const show = ev => {
      const r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width;
      const i = Math.max(0, Math.min(V.length - 1, Math.round((px - L) / (W - L - R) * (V.length - 1))));
      const p = V[i], cx = x(i);
      hov.setAttribute('visibility', 'visible');
      hov.querySelector('.fc-x').setAttribute('x1', cx); hov.querySelector('.fc-x').setAttribute('x2', cx);
      hov.querySelector('.fc-df').setAttribute('cx', cx); hov.querySelector('.fc-df').setAttribute('cy', y(p.f));
      if (hasIdx) { hov.querySelector('.fc-dt').setAttribute('cx', cx); hov.querySelector('.fc-dt').setAttribute('cy', y(p.t)); }
      tip.innerHTML = `<b>${p.label}</b><span><i style="background:var(--teal)"></i>Fund ${inr(p.f)} <em>NAV ₹${p.nav.toLocaleString('en-IN', { maximumFractionDigits: 4 })}</em></span>` +
        (hasIdx ? `<span><i style="background:var(--ink-3)"></i>Index ${inr(p.t)}</span>` : '');
      tip.hidden = false;
      const left = cx / W * r.width, tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(r.width - tw, left - tw / 2)) + 'px';
    };
    const hide = () => { hov.setAttribute('visibility', 'hidden'); tip.hidden = true; };
    const hit = svg.querySelector('.fc-hit');
    hit.addEventListener('pointermove', show); hit.addEventListener('pointerdown', show); hit.addEventListener('pointerleave', hide);
  }

  function init(el) {
    const code = el.dataset.code, bn = el.dataset.bench || '';
    Promise.all([get('/data/series/' + el.dataset.file + '.json'), bn ? get('/data/series/bench.json') : null, get('/data/series/last.json')])
      .then(([s, b, l]) => {
        if (!s || !s.nav || !s.nav[code]) { el.hidden = true; return; }
        const P = points(s, b, l, code, bn);
        if (P.length < 4) { el.hidden = true; return; }
        const avail = PERIODS.filter(([, m]) => m === 1e9 || P.length - 1 >= m);
        const st = { P, name: el.dataset.name, bname: bn ? el.dataset.bname : '', period: avail.some(p => p[0] === '5Y') ? '5Y' : avail[avail.length - 1][0] };
        el.querySelector('.fc-tabs').innerHTML = avail.map(([p]) => `<button type="button" data-p="${p}" aria-pressed="false">${p}</button>`).join('');
        el.querySelectorAll('.fc-tabs button').forEach(bt => bt.onclick = () => { st.period = bt.dataset.p; render(el, st); });
        el.querySelector('.fc-key').innerHTML = `<span><i style="background:var(--teal)"></i>${esc(st.name)}</span>` + (st.bname ? `<span><i class="dash"></i>${esc(st.bname)}</span>` : '');
        render(el, st);
        let t; addEventListener('resize', () => { clearTimeout(t); t = setTimeout(() => render(el, st), 150); });
      });
  }

  const els = document.querySelectorAll('.fchart');
  if (!els.length) return;
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.unobserve(e.target); init(e.target); } }), { rootMargin: '400px' });
    els.forEach(el => io.observe(el));
  } else els.forEach(init);
})();
