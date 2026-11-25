/* CFO Workforce Dashboard – reads data/dashboard_data.json written by consolidate.py */
(function () {
  'use strict';
  const S = { data: null, country: '', pop: 'Total', source: '' };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const COLORS = () => ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6'].map(css);
  const R = (v, d) => Math.round(v * 10 ** d) / 10 ** d;
  const sign = (v) => (v > 0 ? '+' : v < 0 ? '−' : '');
  const F = {
    int: d3.format(','), pct: (v) => sign(v) + Math.abs(v * 100).toFixed(1) + '%', pctu: (v) => (v * 100).toFixed(1) + '%',
    signed: (v) => sign(v) + d3.format(',')(Math.abs(v)), cr: (v) => v.toFixed(1), scr: (v) => sign(v) + Math.abs(v).toFixed(1),
    scr2: (v) => sign(v) + Math.abs(v).toFixed(2), lakh: (v) => v.toFixed(2)
  };

  // ---------- calculations (same definitions as consolidate.py) ----------
  function totals(d, country) {
    const v = d.variance.filter((r) => !country || r.Country === country);
    const s = (k, pop) => v.filter((r) => !pop || r.Population === pop).reduce((a, r) => a + (+r[k] || 0), 0);
    const ahc = s('Actual headcount'), bhc = s('Budget headcount');
    const ac = s('Actual monthly cost (INR)'), bc = s('Budget monthly cost (INR)');
    const ihc = s('Actual headcount', 'Internal'), xhc = s('Actual headcount', 'External');
    const wi = d.walk.filter((r) => r.Population === 'Internal' && (!country || r.Country === country));
    const iOpen = d3.sum(wi, (r) => r.Opening), iExit = d3.sum(wi, (r) => r.Leavers + r.Terminations);
    return {
      period: d.kpi.period, actual_hc: ahc, budget_hc: bhc, hc_var: ahc - bhc, hc_var_pct: (ahc - bhc) / bhc,
      internal_hc: ihc, external_hc: xhc, external_share: xhc / ahc,
      actual_cost_cr: R(ac / 1e7, country ? 2 : 1), budget_cost_cr: R(bc / 1e7, country ? 2 : 1),
      cost_var_cr: R((ac - bc) / 1e7, 2), cost_var_pct: (ac - bc) / bc,
      cph_lakh: ac / ahc / 1e5, cph_budget_lakh: bc / bhc / 1e5, cph_var_pct: (ac / ahc) / (bc / bhc) - 1,
      volume_cr: R(s('Volume effect (INR)') / 1e7, 2), rate_cr: R(s('Rate / mix effect (INR)') / 1e7, 2),
      internal_exit_pct: iOpen ? iExit / iOpen : 0
    };
  }
  function walk(d, country, pop) {
    const rows = d.walk.filter((r) => (!country || r.Country === country) && (pop === 'Total' || r.Population === pop));
    const g = (k) => d3.sum(rows, (r) => +r[k] || 0);
    return { opening: g('Opening'), hires: g('Hires'), leavers: g('Leavers'), terminations: g('Terminations'), project_hires: g('Project hires'), closing: g('Closing') };
  }
  function byCountry(d) {
    return [...new Set(d.variance.map((r) => r.Country))].map((c) => ({ country: c, ...totals(d, c) }));
  }

  // ---------- rendering ----------
  function setText(el, txt, cls) { el.textContent = txt; el.classList.remove('good', 'bad', 'warn'); if (cls) el.classList.add(cls); }
  const toneHc = (v) => (v > 0.02 ? 'bad' : v > 0 ? 'warn' : 'good');
  const toneCost = (v) => (v > 0 ? 'bad' : 'good');
  const FMT = {
    period: [(v) => v], actual_hc: [F.int], budget_hc: [F.int], hc_var: [F.signed, (v) => (v > 0 ? 'bad' : 'good')], hc_var_pct: [F.pct, toneHc],
    internal_hc: [F.int], external_hc: [F.int], external_share: [F.pctu], internal_exit_pct: [F.pctu],
    actual_cost_cr: [(v) => (S.country ? v.toFixed(2) : v.toFixed(1))], budget_cost_cr: [(v) => (S.country ? v.toFixed(2) : v.toFixed(1))],
    cost_var_cr: [F.scr2, toneCost], cost_var_pct: [F.pct, toneCost], cph_lakh: [F.lakh], cph_budget_lakh: [F.lakh], cph_var_pct: [F.pct, toneCost],
    volume_cr: [F.scr2, toneCost], rate_cr: [F.scr2, toneCost]
  };

  function render() {
    const d = S.data; if (!d) return;
    const g = totals(d, ''), t = totals(d, S.country);
    $$('[data-k]').forEach((el) => { const k = el.dataset.k, f = FMT[k]; setText(el, f[0](g[k]), f[1] && f[1](g[k])); });
    $$('[data-c]').forEach((el) => { const k = el.dataset.c, f = FMT[k]; setText(el, f[0](t[k]), f[1] && f[1](t[k])); });
    $$('[data-scope]').forEach((el) => (el.textContent = '— ' + (S.country || 'group')));
    $('#lede-tail').textContent = g.hc_var > 0 && g.cost_var_pct <= 0 ? ': extra heads are being absorbed by a lower cost per head'
      : g.hc_var > 0 && g.cost_var_pct > 0 ? ': both headcount and cost are running above budget'
      : g.hc_var <= 0 && g.cost_var_pct > 0 ? ': cost per head is above budget' : ': both are within budget';

    const rows = byCountry(d);
    const why = $('#why-country');
    if (!S.country) {
      const topHc = rows.reduce((a, r) => (r.hc_var_pct > a.hc_var_pct ? r : a));
      const topRate = rows.reduce((a, r) => (r.rate_cr < a.rate_cr ? r : a));
      why.textContent = ` The largest headcount overrun is ${topHc.country} (${F.pct(topHc.hc_var_pct)}); the largest rate / mix effect is in ${topRate.country} (₹${F.scr2(topRate.rate_cr)} Cr).`;
    } else {
      why.textContent = ` Internal ${F.int(t.internal_hc)} and external ${F.int(t.external_hc)} heads (external share ${F.pctu(t.external_share)}); internal exits were ${F.pctu(t.internal_exit_pct)} of opening headcount this month.`;
    }
    const scope = S.country || 'The group';
    $('#impact').textContent = t.volume_cr > 0 && t.rate_cr < 0
      ? `${scope} ${t.cost_var_pct <= 0 ? 'is within budget' : 'is only slightly over budget'} because the lower cost per head offsets the extra heads. If cost per head returns to budget (promotions, increments, experienced backfills), the same headcount would cost ₹${t.volume_cr.toFixed(2)} Cr a month more than budget.`
      : t.volume_cr > 0 ? `${scope} is over budget on both headcount and cost per head; the full ₹${F.scr2(t.cost_var_cr)} Cr a month variance flows to the P&L unless hiring is slowed.`
      : `${scope} is at or below budgeted headcount; the cost variance of ₹${F.scr2(t.cost_var_cr)} Cr comes from cost per head.`;

    drawWalk(); drawBridge(t); drawTable(rows); drawGrade(); drawLoc();
    $('#foot').textContent = `Data: ${S.source} · period ${d.kpi.period} · generated ${d.kpi.generated} · validation errors ${d.kpi.validation_errors}`;
  }

  function waterfall(el, steps, fmt, label) {
    el.replaceChildren();
    const W = Math.max(280, el.clientWidth), rowH = 34, ml = 100, mr = 70, mt = 6, mb = 26, H = mt + mb + steps.length * rowH;
    let run = 0;
    const bars = steps.map((s) => { if (s.kind === 'total') { run = s.value; return { ...s, x0: 0, x1: s.value }; } const x0 = run; run += s.value; return { ...s, x0, x1: run }; });
    const moves = bars.filter((b) => b.kind !== 'total').map((b) => Math.abs(b.value));
    const ends = bars.flatMap((b) => (b.kind === 'total' ? [b.value] : [b.x0, b.x1]));
    const span = Math.max(d3.max(moves) || 1, d3.max(ends) - d3.min(ends) || 1);
    const x = d3.scaleLinear().domain([d3.min(ends) - span * 1.2, d3.max(ends) + span * 0.4]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(bars.map((b) => b.label)).range([mt, H - mb]).padding(0.28);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', label);
    svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 90))).tickFormat(fmt.axis).tickSizeInner(-(H - mb - mt)).tickSizeOuter(0)).call((g) => g.select('.domain').remove());
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(8)).call((g) => g.select('.domain').remove());
    const tip = d3.select(el).append('div').attr('class', 'tip').style('display', 'none');
    const col = (b) => (b.kind === 'total' ? css('--s1') : b.good ? css('--ok') : css('--bad'));
    const g = svg.append('g').selectAll('g').data(bars).join('g');
    g.append('rect').attr('y', (b) => y(b.label)).attr('height', y.bandwidth())
      .attr('x', (b) => x(b.kind === 'total' ? x.domain()[0] : Math.min(b.x0, b.x1)))
      .attr('width', (b) => Math.max(2, b.kind === 'total' ? x(b.value) - x(x.domain()[0]) : Math.abs(x(b.x1) - x(b.x0))))
      .attr('rx', 2).attr('fill', col)
      .on('pointermove', (ev, b) => { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 12, W - 170) + 'px').style('top', py - 36 + 'px').text(b.kind === 'total' ? `${b.label}: ${fmt.val(b.value)}` : `${b.label}: ${fmt.signed(b.value)} → ${fmt.val(b.x1)}`); })
      .on('pointerleave', () => tip.style('display', 'none'));
    g.append('text').attr('class', 'val').attr('dy', '0.35em').attr('y', (b) => y(b.label) + y.bandwidth() / 2)
      .attr('x', (b) => x(b.kind === 'total' ? b.value : Math.max(b.x0, b.x1)) + 6).text((b) => (b.kind === 'total' ? fmt.val(b.value) : fmt.signed(b.value)));
    g.filter((b, i) => i < bars.length - 1).append('line')
      .attr('x1', (b) => x(b.kind === 'total' ? b.value : b.x1)).attr('x2', (b) => x(b.kind === 'total' ? b.value : b.x1))
      .attr('y1', (b) => y(b.label) + y.bandwidth()).attr('y2', (b) => y(b.label) + y.step()).attr('stroke', css('--ref')).attr('stroke-dasharray', '2,2');
  }

  function drawWalk() {
    const w = walk(S.data, S.country, S.pop);
    waterfall($('#walk-chart'), [
      { label: 'Opening', value: w.opening, kind: 'total' }, { label: 'Hires', value: w.hires, good: true },
      { label: 'Leavers', value: -w.leavers }, { label: 'Terminations', value: -w.terminations },
      { label: 'Project hires', value: w.project_hires, good: true }, { label: 'Closing', value: w.closing, kind: 'total' }
    ], { val: F.int, signed: F.signed, axis: d3.format(',') }, `Workforce walk ${S.country || 'group'} ${S.pop}: opening ${w.opening}, closing ${w.closing}`);
  }

  function drawBridge(t) {
    const dp = S.country ? 2 : 1;
    const bc = t.budget_cost_cr, ac = t.actual_cost_cr;
    waterfall($('#bridge-chart'), [
      { label: 'Budget cost', value: bc, kind: 'total' }, { label: 'Volume', value: t.volume_cr, good: t.volume_cr <= 0 },
      { label: 'Rate / mix', value: t.rate_cr, good: t.rate_cr <= 0 }, { label: 'Actual cost', value: ac, kind: 'total' }
    ], { val: (v) => '₹' + v.toFixed(dp) + ' Cr', signed: (v) => sign(v) + Math.abs(v).toFixed(2) + ' Cr', axis: (v) => '₹' + d3.format(',.0f')(v) }, `Cost bridge ${S.country || 'group'} from ${bc} to ${ac} crore`);
  }

  function drawTable(rows) {
    const tb = $('#country-table tbody'); tb.replaceChildren();
    const cls = (v) => (v > 0 ? 'bad' : 'good');
    rows.forEach((r) => {
      const tr = tb.insertRow(); if (r.country === S.country) tr.classList.add('sel');
      [[r.country], [F.int(r.actual_hc)], [F.int(r.budget_hc)], [F.pct(r.hc_var_pct), toneHc(r.hc_var_pct)],
        [r.actual_cost_cr.toFixed(2)], [r.budget_cost_cr.toFixed(2)], [F.pct(r.cost_var_pct), cls(r.cost_var_pct)],
        [F.scr2(r.volume_cr), cls(r.volume_cr)], [F.scr2(r.rate_cr), cls(r.rate_cr)], [F.pct(r.cph_var_pct), cls(r.cph_var_pct)]]
        .forEach(([txt, c]) => { const td = tr.insertCell(); td.textContent = txt; if (c) td.className = c; });
      tr.addEventListener('click', () => setCountry(S.country === r.country ? '' : r.country));
    });
  }

  function drawGrade() {
    const el = $('#grade-chart'); el.replaceChildren();
    const grades = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6'], C = COLORS();
    const data = S.data.grade_mix.map((r) => { const tot = d3.sum(grades, (k) => +r[k] || 0); return { country: r.Country, tot, parts: grades.map((k) => ({ grade: k, n: +r[k] || 0, share: (+r[k] || 0) / tot })) }; })
      .sort((a, b) => (a.country === 'Group') - (b.country === 'Group'));
    const W = Math.max(280, el.clientWidth), ml = 64, mr = 8, rowH = 30, H = data.length * rowH + 24;
    const x = d3.scaleLinear().domain([0, 1]).range([ml, W - mr]);
    const y = d3.scaleBand().domain(data.map((r) => r.country)).range([0, H - 24]).padding(0.25);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Internal grade mix by country');
    svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(4).tickFormat(d3.format('.0%')).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
    const tip = d3.select(el).append('div').attr('class', 'tip').style('display', 'none');
    data.forEach((r) => {
      let acc = 0; const dim = S.country && r.country !== S.country && r.country !== 'Group' ? 0.3 : 1;
      r.parts.forEach((p, i) => {
        const x0 = acc; acc += p.share;
        svg.append('rect').attr('x', x(x0)).attr('width', Math.max(0, x(acc) - x(x0) - 1)).attr('y', y(r.country)).attr('height', y.bandwidth()).attr('fill', C[i]).attr('opacity', dim)
          .on('pointermove', (ev) => { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 12, W - 170) + 'px').style('top', py - 36 + 'px').text(`${r.country} ${p.grade}: ${F.int(p.n)} (${F.pctu(p.share)})`); })
          .on('pointerleave', () => tip.style('display', 'none'));
        if (x(acc) - x(x0) > 30) svg.append('text').attr('x', (x(x0) + x(acc)) / 2).attr('y', y(r.country) + y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'middle').attr('fill', '#fff').attr('opacity', dim).style('fill', '#fff').text(Math.round(p.share * 100) + '%');
      });
    });
    const lg = d3.select(el).append('div').attr('class', 'legend');
    grades.forEach((gr, i) => { const s = lg.append('span'); s.append('i').style('background', C[i]); s.append('span').text(gr); });
  }

  function drawLoc() {
    const el = $('#loc-chart'); el.replaceChildren();
    const C = COLORS();
    const rows = [...S.data.location_mix].sort((a, b) => b.Total - a.Total);
    const W = Math.max(280, el.clientWidth), ml = 64, mr = 120, rowH = 34, H = rows.length * rowH + 24;
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.Total)]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(rows.map((r) => r.Country)).range([0, H - 24]).padding(0.25);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Headcount by country, internal and external');
    svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 80))).tickFormat(d3.format(',')).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
    const tip = d3.select(el).append('div').attr('class', 'tip').style('display', 'none');
    const show = (ev, t) => { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 12, W - 190) + 'px').style('top', py - 36 + 'px').text(t); };
    rows.forEach((r) => {
      const dim = S.country && r.Country !== S.country ? 0.3 : 1;
      svg.append('rect').attr('x', x(0)).attr('width', x(r.Internal) - x(0)).attr('y', y(r.Country)).attr('height', y.bandwidth()).attr('fill', C[0]).attr('opacity', dim)
        .on('pointermove', (ev) => show(ev, `${r.Country} internal: ${F.int(r.Internal)}`)).on('pointerleave', () => tip.style('display', 'none'));
      svg.append('rect').attr('x', x(r.Internal)).attr('width', x(r.Total) - x(r.Internal)).attr('y', y(r.Country)).attr('height', y.bandwidth()).attr('fill', C[1]).attr('opacity', dim)
        .on('pointermove', (ev) => show(ev, `${r.Country} external: ${F.int(r.External)} (${F.pctu(r['External %'])})`)).on('pointerleave', () => tip.style('display', 'none'));
      svg.append('text').attr('class', 'val').attr('x', x(r.Total) + 6).attr('y', y(r.Country) + y.bandwidth() / 2).attr('dy', '0.35em').attr('opacity', dim)
        .text(`${F.int(r.Total)} · ${F.pctu(r['Share of group'])} · ext ${F.pctu(r['External %'])}`);
    });
    const lg = d3.select(el).append('div').attr('class', 'legend');
    [['Internal', 0], ['External', 1]].forEach(([t, i]) => { const s = lg.append('span'); s.append('i').style('background', C[i]); s.append('span').text(t); });
  }

  // ---------- data loading ----------
  function validate(d) {
    const need = ['kpi', 'walk', 'variance', 'grade_mix', 'location_mix'];
    const miss = need.filter((k) => !d || !d[k]);
    if (miss.length) throw new Error('Not a consolidate.py dashboard file (missing ' + miss.join(', ') + ')');
    return d;
  }
  function load(d, source) {
    S.data = validate(d); S.source = source;
    const sel = $('#country'); const keep = S.country;
    sel.replaceChildren(new Option('All countries', ''), ...[...new Set(d.variance.map((r) => r.Country))].map((c) => new Option(c, c)));
    S.country = [...sel.options].some((o) => o.value === keep) ? keep : ''; sel.value = S.country;
    $('#status').textContent = '';
    render();
  }
  function setCountry(c) { S.country = c; $('#country').value = c; render(); }

  $('#country').addEventListener('change', (e) => setCountry(e.target.value));
  $('#pop').addEventListener('change', (e) => { S.pop = e.target.value; render(); });
  $('#file').addEventListener('change', (e) => {
    const f = e.target.files[0]; if (!f) return;
    f.text().then((t) => load(JSON.parse(t), f.name)).catch((err) => { $('#status').textContent = 'Could not read that file: ' + err.message; $('#status').className = 'sub err'; });
  });
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 150); });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);

  fetch('data/dashboard_data.json', { cache: 'no-cache' })
    .then((r) => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then((d) => load(d, 'data/dashboard_data.json'))
    .catch((err) => { $('#status').textContent = 'Could not load data/dashboard_data.json (' + err.message + '). Use "Load month file" to open a dashboard_data JSON from consolidate.py.'; $('#status').className = 'sub err'; });

  // ---------- install as app (PWA) ----------
  let deferred;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; $('#install').hidden = false; });
  $('#install').addEventListener('click', () => { if (!deferred) return; deferred.prompt(); deferred.userChoice.finally(() => { deferred = null; $('#install').hidden = true; }); });
  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
})();
