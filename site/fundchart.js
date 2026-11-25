/* Growth of ₹10,000 on fund pages: the fund's NAV against its index (total return).
   Short ranges (1M to 1Y) use daily NAVs, 3Y weekly, 5Y and longer month-end values, all from files the site
   publishes: /data/nav/<code>.json (to the last month end), /data/nav/recent-<category>.json (the days since),
   /data/series/* (month-end history). Drag across the chart to zoom in; hover or touch for values; the CSV button
   downloads what is on screen. Loads only when the chart scrolls near the screen. */
(() => {
  const C = {};
  const get = u => C[u] || (C[u] = fetch(u).then(r => r.ok ? r.json() : null).catch(() => null));
  const DAYMS = 864e5;
  const iso = t => new Date(t).toISOString().slice(0, 10);
  const DAY = t => new Date(t).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });
  const MONL = t => new Date(t).toLocaleDateString('en-IN', { month: 'short', year: 'numeric', timeZone: 'UTC' });
  const AX = (t, span) => new Date(t).toLocaleDateString('en-IN', span < 200 * DAYMS ? { day: 'numeric', month: 'short', timeZone: 'UTC' } : { month: 'short', year: 'numeric', timeZone: 'UTC' });
  const inr = v => '₹' + Math.round(v).toLocaleString('en-IN');
  const trim = x => x.replace(/\.0$/, '');
  const short = v => v >= 1e7 ? '₹' + trim((v / 1e7).toFixed(1)) + 'Cr' : v >= 1e5 ? '₹' + trim((v / 1e5).toFixed(1)) + 'L' : '₹' + trim((v / 1e3).toFixed(1)) + 'k';
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  // [label, months back, source]: d = daily/weekly points, m = month-end series
  const PERIODS = [['1M', 1, 'd'], ['3M', 3, 'd'], ['6M', 6, 'd'], ['YTD', 0, 'd'], ['1Y', 12, 'd'], ['3Y', 36, 'd'], ['5Y', 60, 'm'], ['10Y', 120, 'm'], ['Max', 1e9, 'm']];

  const unpack = p => { if (!p) return []; let t = Date.parse(p.s + 'T00:00:00Z'); return p.d.map((g, i) => { t += g * DAYMS; return [t, p.v[i]]; }); };
  const lookup = A => { const M = new Map(A); return t => { if (M.has(t)) return M.get(t); let lo = 0, hi = A.length - 1, r = null; while (lo <= hi) { const k = (lo + hi) >> 1; if (A[k][0] <= t) { r = A[k][1]; lo = k + 1; } else hi = k - 1; } return r; }; };

  function monthly(s, b, l, code, bn) {
    const nav = s.nav[code] || [], tri = b && bn ? (b.tri[bn] || []) : [];
    const bi = b ? Object.fromEntries(b.months.map((m, i) => [m, i])) : {};
    const P = [];
    s.months.forEach((m, i) => {
      const v = nav[i]; if (v == null) return;
      const [y, mo] = m.split('-').map(Number), j = bi[m];
      P.push({ t: Date.UTC(y, mo, 0), label: MONL(Date.UTC(y, mo - 1, 1)), nav: v, tri: j != null && tri[j] != null ? tri[j] : null });
    });
    const ln = l && l.nav && l.nav[code], lt = l && l.tri && bn && l.tri[bn];
    if (ln) { const t = Date.parse(ln[0] + 'T00:00:00Z'); if (!P.length || t > P[P.length - 1].t) P.push({ t, label: DAY(t), nav: ln[1], tri: lt ? lt[1] : null, latest: true }); }
    return P;
  }

  function fine(h, r, bh, br, l, code, bn) {
    const A = unpack(h).concat(unpack(r && r.nav && r.nav[code]));
    const ln = l && l.nav && l.nav[code];
    if (ln) { const t = Date.parse(ln[0] + 'T00:00:00Z'); if (!A.length || t > A[A.length - 1][0]) A.push([t, ln[1]]); }
    const T = bn ? unpack(bh && bh.tri && bh.tri[bn]).concat(unpack(br && br.tri && br.tri[bn])) : [];
    const lt = l && l.tri && bn && l.tri[bn];
    if (lt) { const t = Date.parse(lt[0] + 'T00:00:00Z'); if (!T.length || t > T[T.length - 1][0]) T.push([t, lt[1]]); }
    const tri = T.length ? lookup(T) : () => null;
    return A.map(([t, v]) => ({ t, label: DAY(t), nav: v, tri: tri(t) }));
  }

  function pick(st) {
    const p = PERIODS.find(x => x[0] === st.period), src = p[2] === 'd' && st.F.length ? st.F : st.P;
    const end = src[src.length - 1].t;
    let from;
    if (p[0] === 'YTD') from = Date.UTC(new Date(end).getUTCFullYear() - 1, 11, 31);
    else if (p[1] >= 1e9) from = -Infinity;
    else { const d = new Date(end); from = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() - p[1], d.getUTCDate()); }
    let i0 = src.findIndex(q => q.t > from); i0 = Math.max(0, i0 - 1);   // start from the last point on or before the start date
    let S = src.slice(i0);
    if (p[0] === '3Y') S = S.filter((q, i) => i === 0 || i === S.length - 1 || new Date(q.t).getUTCDay() === 5 || q.t < S[S.length - 1].t - 400 * DAYMS);   // weekly
    if (st.zoom) { const z = S.filter(q => q.t >= st.zoom[0] && q.t <= st.zoom[1]); if (z.length >= 3) S = z; }
    return S;
  }

  function render(el, st) {
    const { name, bname } = st;
    const S = pick(st);
    const hasIdx = !!bname && S.every(p => p.tri != null);
    const f0 = S[0].nav, t0 = hasIdx ? S[0].tri : 1;
    const V = S.map(p => ({ ...p, f: 10000 * p.nav / f0, tv: hasIdx ? 10000 * p.tri / t0 : null }));
    const W = Math.max(300, el.querySelector('.fc-plot').clientWidth), H = 250, L = 52, R = 12, T = 12, B = 28;
    const all = V.flatMap(p => hasIdx ? [p.f, p.tv] : [p.f]);
    let lo = Math.min(...all, 10000), hi = Math.max(...all, 10000); const pad = (hi - lo) * .06 || 100; lo -= pad; hi += pad;
    const ta = V[0].t, tb = V[V.length - 1].t, span = Math.max(tb - ta, DAYMS);
    const x = t => L + (t - ta) / span * (W - L - R);
    const y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
    const path = k => V.map((p, i) => (i ? 'L' : 'M') + x(p.t).toFixed(1) + ' ' + y(p[k]).toFixed(1)).join('');
    const raw = (hi - lo) / 4, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map(k => k * mag).find(v => v >= raw);
    const grid = []; for (let g = Math.ceil(lo / step) * step; g <= hi; g += step) grid.push(g);
    const nt = W < 480 ? 3 : 5, ticks = Array.from({ length: nt }, (_, k) => ta + k * span / (nt - 1));
    const end = V[V.length - 1];
    el.querySelector('.fc-plot').innerHTML =
      `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="Growth of ₹10,000 in ${esc(name)} from ${V[0].label} to ${end.label}: ${inr(end.f)}${hasIdx ? `, against ${inr(end.tv)} in the ${esc(bname)}` : ''}.">
        ${grid.map(g => `<line x1="${L}" x2="${W - R}" y1="${y(g).toFixed(1)}" y2="${y(g).toFixed(1)}" stroke="var(--rule)"/><text x="${L - 8}" y="${(y(g) + 4).toFixed(1)}" text-anchor="end" font-size="11.5" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${short(g)}</text>`).join('')}
        <line x1="${L}" x2="${W - R}" y1="${y(10000).toFixed(1)}" y2="${y(10000).toFixed(1)}" stroke="var(--ink-3)" stroke-dasharray="2 3" opacity=".6"/>
        ${ticks.map((t, k) => `<text x="${x(t).toFixed(1)}" y="${H - 8}" text-anchor="${k === 0 ? 'start' : k === nt - 1 ? 'end' : 'middle'}" font-size="11.5" font-family="IBM Plex Mono,monospace" fill="var(--ink-3)">${AX(t, span)}</text>`).join('')}
        ${hasIdx ? `<path d="${path('tv')}" fill="none" stroke="var(--ink-3)" stroke-width="1.6" stroke-dasharray="5 4" stroke-linejoin="round"/>` : ''}
        <path d="${path('f')}" fill="none" stroke="var(--teal)" stroke-width="2.2" stroke-linejoin="round"/>
        <rect class="fc-sel" y="${T}" height="${H - T - B}" fill="var(--teal)" opacity=".12" visibility="hidden"/>
        <g class="fc-hover" visibility="hidden"><line class="fc-x" y1="${T}" y2="${H - B}" stroke="var(--ink-3)" stroke-width="1"/>
          <circle class="fc-df" r="4.5" fill="var(--teal)" stroke="var(--surface)" stroke-width="2"/>${hasIdx ? '<circle class="fc-dt" r="4" fill="var(--ink-3)" stroke="var(--surface)" stroke-width="2"/>' : ''}</g>
        <rect x="${L}" y="${T}" width="${W - L - R}" height="${H - T - B}" fill="transparent" class="fc-hit" style="cursor:crosshair"/>
      </svg>`;
    const diff = hasIdx ? end.f - end.tv : null;
    el.querySelector('.fc-sum').innerHTML = `₹10,000 invested ${/^\d/.test(V[0].label) ? 'on' : 'in'} <b>${V[0].label}</b> would be worth <b>${inr(end.f)}</b> on ${end.label}` +
      (hasIdx ? `, against <b>${inr(end.tv)}</b> in the ${esc(bname)} (${diff >= 0 ? 'ahead by' : 'behind by'} ${inr(Math.abs(diff))}).` : '.') +
      ` <span class="fc-gran">${st.zoom ? 'Zoomed in. ' : ''}${PERIODS.find(p => p[0] === st.period)[2] === 'd' && st.F.length ? (st.period === '3Y' ? 'Weekly' : 'Daily') + ' NAVs.' : 'Month-end NAVs.'}</span>`;
    el.querySelectorAll('.fc-tabs button[data-p]').forEach(bt => bt.setAttribute('aria-pressed', !st.zoom && bt.dataset.p === st.period));
    el.querySelector('.fc-reset').hidden = !st.zoom;
    const svg = el.querySelector('svg'), hov = svg.querySelector('.fc-hover'), tip = el.querySelector('.fc-tip'), sel = svg.querySelector('.fc-sel');
    const tAt = ev => { const r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width; return ta + Math.max(0, Math.min(1, (px - L) / (W - L - R))) * span; };
    const near = t => { let lo2 = 0, hi2 = V.length - 1; while (hi2 - lo2 > 1) { const k = (lo2 + hi2) >> 1; if (V[k].t <= t) lo2 = k; else hi2 = k; } return t - V[lo2].t < V[hi2].t - t ? lo2 : hi2; };
    let drag = null;
    const show = ev => {
      const t = tAt(ev);
      if (drag != null && Math.abs(x(t) - x(drag)) > 8) {
        const a = Math.min(x(t), x(drag)), b = Math.max(x(t), x(drag));
        sel.setAttribute('x', a); sel.setAttribute('width', b - a); sel.setAttribute('visibility', 'visible');
      }
      const p = V[near(t)], cx = x(p.t), r = svg.getBoundingClientRect();
      hov.setAttribute('visibility', 'visible');
      hov.querySelector('.fc-x').setAttribute('x1', cx); hov.querySelector('.fc-x').setAttribute('x2', cx);
      hov.querySelector('.fc-df').setAttribute('cx', cx); hov.querySelector('.fc-df').setAttribute('cy', y(p.f));
      if (hasIdx) { hov.querySelector('.fc-dt').setAttribute('cx', cx); hov.querySelector('.fc-dt').setAttribute('cy', y(p.tv)); }
      const chg = (p.f / 10000 - 1) * 100;
      tip.innerHTML = `<b>${p.label}</b><span><i style="background:var(--teal)"></i>Fund ${inr(p.f)} <em>NAV ₹${p.nav.toLocaleString('en-IN', { maximumFractionDigits: 4 })} · ${chg >= 0 ? '+' : ''}${chg.toFixed(1)}%</em></span>` +
        (hasIdx ? `<span><i style="background:var(--ink-3)"></i>Index ${inr(p.tv)} <em>${p.tv >= 10000 ? '+' : ''}${(p.tv / 100 - 100).toFixed(1)}%</em></span>` : '');
      tip.hidden = false;
      const left = cx / W * r.width, tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(r.width - tw, left - tw / 2)) + 'px';
    };
    const hide = () => { hov.setAttribute('visibility', 'hidden'); tip.hidden = true; };
    const hit = svg.querySelector('.fc-hit');
    hit.addEventListener('pointerdown', ev => { drag = tAt(ev); show(ev); });
    hit.addEventListener('pointermove', show);
    hit.addEventListener('pointerleave', () => { hide(); drag = null; sel.setAttribute('visibility', 'hidden'); });
    hit.addEventListener('pointerup', ev => {
      if (drag == null) return;
      const t = tAt(ev), a = Math.min(t, drag), b = Math.max(t, drag); drag = null;
      if (Math.abs(x(b) - x(a)) > 8 && V.filter(q => q.t >= a && q.t <= b).length >= 3) { st.zoom = [a, b]; render(el, st); }
      else sel.setAttribute('visibility', 'hidden');
    });
    st.shown = V;
  }

  function csv(el, st) {
    const rows = [['date', 'nav', 'index_tri', 'value_of_10000']].concat(st.shown.map(p => [iso(p.t), p.nav, p.tri ?? '', Math.round(p.f)]));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([rows.map(r => r.join(',')).join('\n') + '\n'], { type: 'text/csv' }));
    a.download = (el.dataset.name || 'fund').replace(/[^\w]+/g, '-').toLowerCase() + '-nav.csv';
    document.body.appendChild(a); a.click(); a.remove();
  }

  function init(el) {
    const code = el.dataset.code, bn = el.dataset.bench || '', cat = el.dataset.file;
    Promise.all([get('/data/series/' + cat + '.json'), bn ? get('/data/series/bench.json') : null, get('/data/series/last.json'),
      get('/data/nav/' + code + '.json'), get('/data/nav/recent-' + cat + '.json'), bn ? get('/data/nav/bench.json') : null, bn ? get('/data/nav/recent-bench.json') : null])
      .then(([s, b, l, h, r, bh, br]) => {
        if (!s || !s.nav || !s.nav[code]) { el.hidden = true; return; }
        const P = monthly(s, b, l, code, bn), F = h ? fine(h, r, bh, br, l, code, bn) : [];
        if (P.length < 4) { el.hidden = true; return; }
        const span = arr => arr.length ? arr[arr.length - 1].t - arr[0].t : 0;
        const avail = PERIODS.filter(([p, m, src]) => {
          const arr = src === 'd' && F.length ? F : P;
          if (src === 'd' && !F.length && m < 12) return false;
          return m >= 1e9 || p === 'YTD' || span(arr) >= (m * 30.4 - 10) * DAYMS;
        });
        const st = { P, F, name: el.dataset.name, bname: bn ? el.dataset.bname : '', zoom: null, period: avail.some(p => p[0] === '1Y') ? '1Y' : avail[avail.length - 1][0] };
        el.querySelector('.fc-tabs').innerHTML = avail.map(([p]) => `<button type="button" data-p="${p}" aria-pressed="false">${p}</button>`).join('') +
          '<button type="button" class="fc-reset" hidden>Reset zoom</button><button type="button" class="fc-csv" title="Download the NAVs shown">CSV</button>';
        el.querySelectorAll('.fc-tabs button[data-p]').forEach(bt => bt.onclick = () => { st.period = bt.dataset.p; st.zoom = null; render(el, st); });
        el.querySelector('.fc-reset').onclick = () => { st.zoom = null; render(el, st); };
        el.querySelector('.fc-csv').onclick = () => csv(el, st);
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
