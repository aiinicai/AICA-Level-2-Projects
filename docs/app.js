/* CFO Workforce Dashboard – reads data/index.json and data/dashboard_data_<Mon-YYYY>.json written by consolidate.py */
(function () {
  'use strict';
  const S = { all: {}, periods: [], period: '', country: '', pop: 'Total', sources: {}, view: 'overview', hl: '' };
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const COLORS = () => ['--s1', '--s2', '--s3', '--s4', '--s5', '--s6'].map(css);
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const pkey = (p) => { const [m, y] = p.split('-'); return +y * 12 + MONTHS.indexOf(m); };
  const R = (v, d) => Math.round(v * 10 ** d) / 10 ** d;
  const sign = (v) => (v > 0 ? '+' : v < 0 ? '−' : '');
  const F = {
    int: d3.format(','), pct: (v) => (Math.abs(v) < 0.0005 ? '0.0%' : sign(v) + Math.abs(v * 100).toFixed(1) + '%'), pctu: (v) => (v * 100).toFixed(1) + '%',
    signed: (v) => sign(v) + d3.format(',')(Math.abs(v)), scr2: (v) => sign(v) + Math.abs(v).toFixed(2), lakh: (v) => v.toFixed(2)
  };
  const cr = (v) => (S.country ? v.toFixed(2) : v.toFixed(1));
  const autoFmt = (dom, pre = '') => { const s = Math.abs(dom[1] - dom[0]); const f = d3.format(s < 2 ? ',.2f' : s < 20 ? ',.1f' : ',.0f'); return (v) => pre + f(v); };

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
      actual_hc: ahc, budget_hc: bhc, hc_var: ahc - bhc, hc_var_pct: bhc ? (ahc - bhc) / bhc : 0,
      internal_hc: ihc, external_hc: xhc, external_share: ahc ? xhc / ahc : 0,
      actual_cost_cr: ac / 1e7, budget_cost_cr: bc / 1e7, cost_var_cr: (ac - bc) / 1e7, cost_var_pct: bc ? (ac - bc) / bc : 0,
      cph_lakh: ahc ? ac / ahc / 1e5 : 0, cph_budget_lakh: bhc ? bc / bhc / 1e5 : 0, cph_var_pct: ahc && bhc ? (ac / ahc) / (bc / bhc) - 1 : 0,
      volume_cr: s('Volume effect (INR)') / 1e7, rate_cr: s('Rate / mix effect (INR)') / 1e7,
      internal_exit_pct: iOpen ? iExit / iOpen : 0
    };
  }
  function linesFor(d, country) {   // table rows: per country (group view) or per population (country view)
    const v = d.variance;
    if (!country) {
      const cs = [...new Set(v.map((r) => r.Country))];
      return { rows: cs.map((c) => ({ label: c, key: c, ...totals(d, c) })), total: { label: 'Group', ...totals(d, '') } };
    }
    const one = (pop) => {
      const r = v.find((x) => x.Country === country && x.Population === pop); if (!r) return null;
      const ahc = r['Actual headcount'], bhc = r['Budget headcount'], ac = r['Actual monthly cost (INR)'], bc = r['Budget monthly cost (INR)'];
      return { label: pop, actual_hc: ahc, budget_hc: bhc, hc_var_pct: (ahc - bhc) / bhc, actual_cost_cr: ac / 1e7, budget_cost_cr: bc / 1e7,
        cost_var_pct: (ac - bc) / bc, volume_cr: r['Volume effect (INR)'] / 1e7, rate_cr: r['Rate / mix effect (INR)'] / 1e7, cph_var_pct: (ac / ahc) / (bc / bhc) - 1 };
    };
    return { rows: ['Internal', 'External'].map(one).filter(Boolean), total: { label: country + ' total', ...totals(d, country) } };
  }
  function walk(d, country, pop) {
    const rows = d.walk.filter((r) => (!country || r.Country === country) && (pop === 'Total' || r.Population === pop));
    const g = (k) => d3.sum(rows, (r) => +r[k] || 0);
    return { opening: g('Opening'), hires: g('Hires'), leavers: g('Leavers'), terminations: g('Terminations'), project_hires: g('Project hires'), closing: g('Closing') };
  }
  const prevPeriod = () => { const i = S.periods.indexOf(S.period); return i > 0 ? S.periods[i - 1] : null; };

  // ---------- rendering ----------
  function setText(el, txt, cls) { el.textContent = txt; el.classList.remove('good', 'bad', 'warn'); if (cls) el.classList.add(cls); }
  const toneHc = (v) => (v > 0.02 ? 'bad' : v > 0 ? 'warn' : 'good');
  const toneCost = (v) => (v > 0 ? 'bad' : 'good');

  function render() {
    const d = S.all[S.period]; if (!d) return;
    const t = totals(d, S.country);
    const pp = prevPeriod(), tp = pp ? totals(S.all[pp], S.country) : null;
    const scope = S.country || 'Group';
    $('#scope-name').textContent = scope;
    $('#period-name').textContent = S.period;
    const proj = S.view === 'projects';
    $('#view-overview').hidden = proj; $('#view-projects').hidden = !proj; $('#pop-wrap').hidden = proj;
    $$('.tabs button').forEach((b) => b.setAttribute('aria-selected', String(b.dataset.view === S.view)));
    document.querySelector('h1').childNodes[1].textContent = proj ? ' projects – ' : ' workforce – ';
    $('#scope-sub').textContent = (S.country ? S.country : 'India · UK · US · France · China') + ' · internal employees and external consultants · monthly cost in ₹ crore at month FX rates';
    $$('[data-scope]').forEach((el) => (el.textContent = '— ' + scope + ', ' + S.period));
    $$('[data-scope-only]').forEach((el) => (el.textContent = '— ' + scope));
    if (proj) { renderProjects(d); finish(d); return; }

    const K = {
      actual_hc: [F.int(t.actual_hc)], budget_hc: [F.int(t.budget_hc)], hc_var_pct: [F.pct(t.hc_var_pct), toneHc(t.hc_var_pct)],
      mom_hc: tp ? [F.signed(t.actual_hc - tp.actual_hc)] : ['n/a'],
      actual_cost_cr: [cr(t.actual_cost_cr)], budget_cost_cr: [cr(t.budget_cost_cr)], cost_var_pct: [F.pct(t.cost_var_pct), toneCost(t.cost_var_pct)],
      mom_cost: tp ? [F.pct(t.actual_cost_cr / tp.actual_cost_cr - 1)] : ['n/a'],
      cph_lakh: [F.lakh(t.cph_lakh)], cph_budget_lakh: [F.lakh(t.cph_budget_lakh)], cph_var_pct: [F.pct(t.cph_var_pct), toneCost(t.cph_var_pct)],
      internal_hc: [F.int(t.internal_hc)], external_hc: [F.int(t.external_hc)], external_share: [F.pctu(t.external_share)], internal_exit_pct: [F.pctu(t.internal_exit_pct)]
    };
    $$('[data-k]').forEach((el) => { const v = K[el.dataset.k]; setText(el, v[0], v[1]); });

    const tail = t.hc_var > 0 && t.cost_var_pct <= 0 ? 'the extra heads are being absorbed by a lower cost per head'
      : t.hc_var > 0 && t.cost_var_pct > 0 ? 'both headcount and cost are running above budget'
      : t.hc_var <= 0 && t.cost_var_pct > 0 ? 'cost per head is above budget' : 'both are within budget';
    $('#takeaway').textContent = `${scope} headcount is ${F.int(t.actual_hc)}, ${F.pct(t.hc_var_pct)} against budget, while monthly cost of ₹${cr(t.actual_cost_cr)} Cr is ${F.pct(t.cost_var_pct)} against budget: ${tail}.`
      + (tp ? ` Since ${pp}, headcount moved ${F.signed(t.actual_hc - tp.actual_hc)} and cost ${F.pct(t.actual_cost_cr / tp.actual_cost_cr - 1)}.` : '');

    $('#c-what').textContent = `Headcount closed at ${F.int(t.actual_hc)} against a budget of ${F.int(t.budget_hc)} (${F.signed(t.hc_var)} heads, ${F.pct(t.hc_var_pct)}). Monthly cost was ₹${cr(t.actual_cost_cr)} Cr against ₹${cr(t.budget_cost_cr)} Cr, a variance of ₹${F.scr2(t.cost_var_cr)} Cr (${F.pct(t.cost_var_pct)}).`;
    let why = `Volume effect ₹${F.scr2(t.volume_cr)} Cr from the headcount difference; rate / mix effect ₹${F.scr2(t.rate_cr)} Cr from cost per head of ₹${F.lakh(t.cph_lakh)} L against ₹${F.lakh(t.cph_budget_lakh)} L budgeted (${F.pct(t.cph_var_pct)}).`;
    if (!S.country) {
      const rows = linesFor(d, '').rows;
      const topHc = rows.reduce((a, r) => (r.hc_var_pct > a.hc_var_pct ? r : a));
      const topRate = rows.reduce((a, r) => (r.rate_cr < a.rate_cr ? r : a));
      why += ` The largest headcount overrun is ${topHc.label} (${F.pct(topHc.hc_var_pct)}); the largest rate / mix effect is in ${topRate.label} (₹${F.scr2(topRate.rate_cr)} Cr).`;
    } else {
      const w = walk(d, S.country, 'Internal');
      why += ` Internal ${F.int(t.internal_hc)} and external ${F.int(t.external_hc)} heads (external share ${F.pctu(t.external_share)}); internal joiners ${w.hires + w.project_hires} against ${w.leavers + w.terminations} exits (${F.pctu(t.internal_exit_pct)} of opening).`;
    }
    $('#c-why').textContent = why;
    $('#impact').textContent = t.volume_cr > 0 && t.rate_cr < 0
      ? `${scope} ${t.cost_var_pct <= 0 ? 'is within budget' : 'is only slightly over budget'} because the lower cost per head offsets the extra heads. If cost per head returns to budget (promotions, increments, experienced backfills), the same headcount would cost ₹${t.volume_cr.toFixed(2)} Cr a month more than budget.`
      : t.volume_cr > 0 ? `${scope} is over budget on both headcount and cost per head; the full ₹${F.scr2(t.cost_var_cr)} Cr a month flows to the P&L unless hiring is slowed.`
      : `${scope} is at or below budgeted headcount; the cost variance of ₹${F.scr2(t.cost_var_cr)} Cr comes from cost per head.`;

    $('#share-panel').hidden = !!S.country;
    if (!S.country) drawShare(d);
    drawWalk(d); drawBridge(t); drawTable(d); drawGrade(d); drawLoc(d); drawTrend();
    finish(d);
  }

  function finish(d) {
    const src = S.sources[S.period] || '';
    $('#foot').textContent = `Data: ${src} · period ${d.kpi.period} · generated ${d.kpi.generated} · validation errors ${d.kpi.validation_errors} · months loaded: ${S.periods.join(', ')}`;
    const h = '#p=' + S.period + (S.country ? '&c=' + encodeURIComponent(S.country) : '') + (S.view === 'projects' ? '&v=projects' : '');
    if (location.hash !== h) history.replaceState(null, '', h);
  }

  function tooltip(el) { return d3.select(el).append('div').attr('class', 'tip').style('display', 'none'); }
  function showTip(tip, el, ev, text, W) { const [px, py] = d3.pointer(ev, el); tip.style('display', null).style('left', Math.min(px + 12, W - 190) + 'px').style('top', py - 36 + 'px').text(text); }

  function waterfall(el, steps, fmt, label) {
    el.replaceChildren();
    const W = Math.max(280, el.clientWidth), rowH = 34, ml = 100, mr = 76, mt = 6, mb = 26, H = mt + mb + steps.length * rowH;
    let run = 0;
    const bars = steps.map((s) => { if (s.kind === 'total') { run = s.value; return { ...s, x0: 0, x1: s.value }; } const x0 = run; run += s.value; return { ...s, x0, x1: run }; });
    const moves = bars.filter((b) => b.kind !== 'total').map((b) => Math.abs(b.value));
    const ends = bars.flatMap((b) => (b.kind === 'total' ? [b.value] : [b.x0, b.x1]));
    const span = Math.max(d3.max(moves) || 1, d3.max(ends) - d3.min(ends) || 1);
    const x = d3.scaleLinear().domain([d3.min(ends) - span * 1.2, d3.max(ends) + span * 0.4]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(bars.map((b) => b.label)).range([mt, H - mb]).padding(0.28);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', label);
    svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 90))).tickFormat(fmt.axis === 'inr' ? autoFmt(x.domain(), '₹') : fmt.axis).tickSizeInner(-(H - mb - mt)).tickSizeOuter(0)).call((g) => g.select('.domain').remove());
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(8)).call((g) => g.select('.domain').remove());
    const tip = tooltip(el);
    const col = (b) => (b.kind === 'total' ? css('--s1') : b.good ? css('--ok') : css('--bad'));
    const g = svg.append('g').selectAll('g').data(bars).join('g');
    g.append('rect').attr('y', (b) => y(b.label)).attr('height', y.bandwidth())
      .attr('x', (b) => x(b.kind === 'total' ? x.domain()[0] : Math.min(b.x0, b.x1)))
      .attr('width', (b) => Math.max(2, b.kind === 'total' ? x(b.value) - x(x.domain()[0]) : Math.abs(x(b.x1) - x(b.x0))))
      .attr('rx', 2).attr('fill', col)
      .on('pointermove', (ev, b) => showTip(tip, el, ev, b.kind === 'total' ? `${b.label}: ${fmt.val(b.value)}` : `${b.label}: ${fmt.signed(b.value)} → ${fmt.val(b.x1)}`, W))
      .on('pointerleave', () => tip.style('display', 'none'));
    g.append('text').attr('class', 'val').attr('dy', '0.35em').attr('y', (b) => y(b.label) + y.bandwidth() / 2)
      .attr('x', (b) => x(b.kind === 'total' ? b.value : Math.max(b.x0, b.x1)) + 6).text((b) => (b.kind === 'total' ? fmt.val(b.value) : fmt.signed(b.value)));
    g.filter((b, i) => i < bars.length - 1).append('line')
      .attr('x1', (b) => x(b.kind === 'total' ? b.value : b.x1)).attr('x2', (b) => x(b.kind === 'total' ? b.value : b.x1))
      .attr('y1', (b) => y(b.label) + y.bandwidth()).attr('y2', (b) => y(b.label) + y.step()).attr('stroke', css('--ref')).attr('stroke-dasharray', '2,2');
  }

  function drawWalk(d) {
    const w = walk(d, S.country, S.pop);
    waterfall($('#walk-chart'), [
      { label: 'Opening', value: w.opening, kind: 'total' }, { label: 'Hires', value: w.hires, good: true },
      { label: 'Leavers', value: -w.leavers }, { label: 'Terminations', value: -w.terminations },
      { label: 'Project hires', value: w.project_hires, good: true }, { label: 'Closing', value: w.closing, kind: 'total' }
    ], { val: F.int, signed: F.signed, axis: d3.format(',') }, `Workforce walk ${S.country || 'group'} ${S.pop} ${S.period}: opening ${w.opening}, closing ${w.closing}`);
  }

  function drawBridge(t) {
    const dp = S.country ? 2 : 1;
    waterfall($('#bridge-chart'), [
      { label: 'Budget cost', value: R(t.budget_cost_cr, dp), kind: 'total' }, { label: 'Volume', value: t.volume_cr, good: t.volume_cr <= 0 },
      { label: 'Rate / mix', value: t.rate_cr, good: t.rate_cr <= 0 }, { label: 'Actual cost', value: R(t.actual_cost_cr, dp), kind: 'total' }
    ], { val: (v) => '₹' + v.toFixed(dp) + ' Cr', signed: (v) => sign(v) + Math.abs(v).toFixed(2) + ' Cr', axis: 'inr' },
    `Cost bridge ${S.country || 'group'} ${S.period} from ${R(t.budget_cost_cr, dp)} to ${R(t.actual_cost_cr, dp)} crore`);
  }

  function drawTable(d) {
    const tb = $('#var-table tbody'); tb.replaceChildren();
    const { rows, total } = linesFor(d, S.country);
    $('#th-first').textContent = S.country ? 'Population' : 'Country';
    $('#table-title').firstChild.textContent = S.country ? 'Variance by population ' : 'Variance by country ';
    $('#table-sub').textContent = S.country ? `${S.country} only · internal employees and external consultants · cost in ₹ crore per month · variance = actual − budget`
      : 'Cost in ₹ crore per month · variance = actual − budget · tap a row to focus on that country';
    const cls = (v) => (v > 0 ? 'bad' : 'good');
    [...rows, total].forEach((r, i) => {
      const tr = tb.insertRow(); if (r === total) tr.className = 'total';
      [[r.label], [F.int(r.actual_hc)], [F.int(r.budget_hc)], [F.pct(r.hc_var_pct), toneHc(r.hc_var_pct)],
        [r.actual_cost_cr.toFixed(2)], [r.budget_cost_cr.toFixed(2)], [F.pct(r.cost_var_pct), cls(r.cost_var_pct)],
        [F.scr2(r.volume_cr), cls(r.volume_cr)], [F.scr2(r.rate_cr), cls(r.rate_cr)], [F.pct(r.cph_var_pct), cls(r.cph_var_pct)]]
        .forEach(([txt, c]) => { const td = tr.insertCell(); td.textContent = txt; if (c) td.className = c; });
      if (!S.country && r !== total) tr.addEventListener('click', () => setCountry(r.key));
      else tr.style.cursor = 'default';
    });
  }

  function drawGrade(d) {
    const el = $('#grade-chart'); el.replaceChildren();
    const grades = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6'], C = COLORS();
    const tip = tooltip(el), W = Math.max(280, el.clientWidth);
    if (S.country) {
      const r = d.grade_mix.find((x) => x.Country === S.country); if (!r) { el.textContent = 'No internal employees for ' + S.country; return; }
      const tot = d3.sum(grades, (k) => +r[k] || 0);
      const data = grades.map((k, i) => ({ grade: k, n: +r[k] || 0, share: (+r[k] || 0) / tot, c: C[i] }));
      $('#grade-sub').textContent = `${S.country}: internal month-end headcount by grade (${F.int(tot)} employees)`;
      const ml = 40, mr = 90, rowH = 30, H = data.length * rowH + 24;
      const x = d3.scaleLinear().domain([0, d3.max(data, (z) => z.n)]).range([ml, W - mr]).nice(4);
      const y = d3.scaleBand().domain(grades).range([0, H - 24]).padding(0.25);
      const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', `Grade mix ${S.country}`);
      svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 70))).tickFormat(d3.format(',')).tickSizeOuter(0));
      svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
      data.forEach((z) => {
        svg.append('rect').attr('x', x(0)).attr('width', Math.max(1, x(z.n) - x(0))).attr('y', y(z.grade)).attr('height', y.bandwidth()).attr('rx', 2).attr('fill', z.c)
          .on('pointermove', (ev) => showTip(tip, el, ev, `${z.grade}: ${F.int(z.n)} (${F.pctu(z.share)})`, W)).on('pointerleave', () => tip.style('display', 'none'));
        svg.append('text').attr('class', 'val').attr('x', x(z.n) + 6).attr('y', y(z.grade) + y.bandwidth() / 2).attr('dy', '0.35em').text(`${F.int(z.n)} · ${F.pctu(z.share)}`);
      });
      return;
    }
    $('#grade-sub').textContent = 'Share of month-end headcount by grade (G1 associate → G6 director)';
    const data = d.grade_mix.map((r) => { const tot = d3.sum(grades, (k) => +r[k] || 0); return { country: r.Country, parts: grades.map((k) => ({ grade: k, n: +r[k] || 0, share: (+r[k] || 0) / tot })) }; })
      .sort((a, b) => (a.country === 'Group') - (b.country === 'Group'));
    const ml = 64, mr = 8, rowH = 30, H = data.length * rowH + 24;
    const x = d3.scaleLinear().domain([0, 1]).range([ml, W - mr]);
    const y = d3.scaleBand().domain(data.map((r) => r.country)).range([0, H - 24]).padding(0.25);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Internal grade mix by country');
    svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(4).tickFormat(d3.format('.0%')).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
    data.forEach((r) => {
      let acc = 0;
      r.parts.forEach((p, i) => {
        const x0 = acc; acc += p.share;
        svg.append('rect').attr('x', x(x0)).attr('width', Math.max(0, x(acc) - x(x0) - 1)).attr('y', y(r.country)).attr('height', y.bandwidth()).attr('fill', C[i])
          .on('pointermove', (ev) => showTip(tip, el, ev, `${r.country} ${p.grade}: ${F.int(p.n)} (${F.pctu(p.share)})`, W)).on('pointerleave', () => tip.style('display', 'none'));
        if (x(acc) - x(x0) > 30) svg.append('text').attr('x', (x(x0) + x(acc)) / 2).attr('y', y(r.country) + y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'middle').style('fill', '#fff').text(Math.round(p.share * 100) + '%');
      });
    });
    const lg = d3.select(el).append('div').attr('class', 'legend');
    grades.forEach((gr, i) => { const s = lg.append('span'); s.append('i').style('background', C[i]); s.append('span').text(gr); });
  }

  function drawLoc(d) {
    const el = $('#loc-chart'); el.replaceChildren();
    const C = COLORS(), tip = tooltip(el), W = Math.max(280, el.clientWidth);
    let rows = [...d.location_mix].sort((a, b) => b.Total - a.Total);
    if (S.country) {
      const r = rows.find((z) => z.Country === S.country); if (!r) { el.textContent = 'No data for ' + S.country; return; }
      $('#loc-sub').textContent = `${S.country}: ${F.int(r.Total)} heads, ${F.pctu(r['Share of group'])} of group headcount`;
      const parts = [{ k: 'Internal', n: r.Internal, c: C[0] }, { k: 'External', n: r.External, c: C[1] }];
      const ml = 70, mr = 110, rowH = 40, H = parts.length * rowH + 24;
      const x = d3.scaleLinear().domain([0, r.Total]).range([ml, W - mr]).nice(4);
      const y = d3.scaleBand().domain(parts.map((p) => p.k)).range([0, H - 24]).padding(0.25);
      const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', `Internal and external headcount ${S.country}`);
      svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 70))).tickFormat(d3.format(',')).tickSizeOuter(0));
      svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
      parts.forEach((p) => {
        svg.append('rect').attr('x', x(0)).attr('width', Math.max(1, x(p.n) - x(0))).attr('y', y(p.k)).attr('height', y.bandwidth()).attr('rx', 2).attr('fill', p.c)
          .on('pointermove', (ev) => showTip(tip, el, ev, `${S.country} ${p.k.toLowerCase()}: ${F.int(p.n)}`, W)).on('pointerleave', () => tip.style('display', 'none'));
        svg.append('text').attr('class', 'val').attr('x', x(p.n) + 6).attr('y', y(p.k) + y.bandwidth() / 2).attr('dy', '0.35em').text(`${F.int(p.n)} · ${F.pctu(p.n / r.Total)} of ${S.country}`);
      });
      return;
    }
    $('#loc-sub').textContent = 'Month-end headcount, internal and external; label shows total, share of group and external %';
    const ml = 64, mr = 130, rowH = 34, H = rows.length * rowH + 24;
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.Total)]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(rows.map((r) => r.Country)).range([0, H - 24]).padding(0.25);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Headcount by country, internal and external');
    svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 80))).tickFormat(d3.format(',')).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
    rows.forEach((r) => {
      svg.append('rect').attr('x', x(0)).attr('width', x(r.Internal) - x(0)).attr('y', y(r.Country)).attr('height', y.bandwidth()).attr('fill', C[0]).style('cursor', 'pointer')
        .on('pointermove', (ev) => showTip(tip, el, ev, `${r.Country} internal: ${F.int(r.Internal)}`, W)).on('pointerleave', () => tip.style('display', 'none')).on('click', () => setCountry(r.Country));
      svg.append('rect').attr('x', x(r.Internal)).attr('width', x(r.Total) - x(r.Internal)).attr('y', y(r.Country)).attr('height', y.bandwidth()).attr('fill', C[1]).style('cursor', 'pointer')
        .on('pointermove', (ev) => showTip(tip, el, ev, `${r.Country} external: ${F.int(r.External)} (${F.pctu(r['External %'])})`, W)).on('pointerleave', () => tip.style('display', 'none')).on('click', () => setCountry(r.Country));
      svg.append('text').attr('class', 'val').attr('x', x(r.Total) + 6).attr('y', y(r.Country) + y.bandwidth() / 2).attr('dy', '0.35em')
        .text(`${F.int(r.Total)} · ${F.pctu(r['Share of group'])} · ext ${F.pctu(r['External %'])}`);
    });
    const lg = d3.select(el).append('div').attr('class', 'legend');
    [['Internal', 0], ['External', 1]].forEach(([t, i]) => { const s = lg.append('span'); s.append('i').style('background', C[i]); s.append('span').text(t); });
  }

  function drawShare(d) {
    const el = $('#share-chart'); el.replaceChildren();
    const g = totals(d, ''), C = COLORS();
    const rows = [...new Set(d.variance.map((r) => r.Country))].map((c) => { const t = totals(d, c); return { c, hc: t.actual_hc / g.actual_hc, cost: t.actual_cost_cr / g.actual_cost_cr, nh: t.actual_hc, nc: t.actual_cost_cr, cph: t.cph_lakh }; })
      .sort((a, b) => b.hc - a.hc);
    const W = Math.max(280, el.clientWidth), ml = 64, mr = 150, grp = 46, H = rows.length * grp + 26;
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => Math.max(r.hc, r.cost))]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(rows.map((r) => r.c)).range([0, H - 26]).paddingInner(0.28);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Each country share of group headcount and of group cost');
    svg.append('g').attr('transform', `translate(0,${H - 26})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 80))).tickFormat(d3.format('.0%')).tickSizeInner(-(H - 26)).tickSizeOuter(0)).call((s) => s.select('.domain').remove());
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(8)).call((s) => s.select('.domain').remove());
    const tip = tooltip(el), bh = y.bandwidth() / 2;
    $('#share-avg').textContent = `Right: cost per head per month (▼ below / ▲ above the group average of ₹${F.lakh(g.cph_lakh)} L)`;
    rows.forEach((r) => {
      const gEl = svg.append('g').style('cursor', 'pointer').on('click', () => setCountry(r.c))
        .on('pointermove', (ev) => showTip(tip, el, ev, `${r.c}: ${F.pctu(r.hc)} of heads (${F.int(r.nh)}), ${F.pctu(r.cost)} of cost (₹${r.nc.toFixed(1)} Cr) · ₹${F.lakh(r.cph)} L a head`, W))
        .on('pointerleave', () => tip.style('display', 'none'));
      gEl.append('rect').attr('x', x(0)).attr('y', y(r.c)).attr('width', x(r.hc) - x(0)).attr('height', bh - 1).attr('rx', 2).attr('fill', C[0]);
      gEl.append('rect').attr('x', x(0)).attr('y', y(r.c) + bh).attr('width', x(r.cost) - x(0)).attr('height', bh - 1).attr('rx', 2).attr('fill', C[1]);
      gEl.append('text').attr('class', 'val').attr('x', x(r.hc) + 6).attr('y', y(r.c) + bh / 2).attr('dy', '0.35em').text(F.pctu(r.hc));
      gEl.append('text').attr('class', 'val').attr('x', x(r.cost) + 6).attr('y', y(r.c) + bh * 1.5).attr('dy', '0.35em').text(F.pctu(r.cost));
      const gap = r.cost - r.hc;
      svg.append('text').attr('x', W - 6).attr('y', y(r.c) + y.bandwidth() / 2).attr('dy', '0.35em').attr('text-anchor', 'end')
        .style('fill', css('--fg')).style('font-weight', 600)
        .text(`₹${F.lakh(r.cph)} L / head ${gap < 0 ? '▼' : '▲'}`);
    });
  }

  // ---------- projects page ----------
  function projRows(d, country) {
    const rs = (d.projects || []).filter((r) => !country || r.Country === country);
    const by = d3.group(rs, (r) => r['Project name']);
    return [...by].map(([name, rows]) => {
      const s = (pop, k) => d3.sum(rows.filter((r) => !pop || r.Population === pop), (r) => +r[k] || 0);
      const heads = s('', 'Headcount'), cost = s('', 'Monthly cost (INR)') / 1e7;
      return { name, short: name.replace(/^Project\s+/, '').split(' - ')[0], countries: [...new Set(rows.map((r) => r.Country).filter(Boolean))],
        int: s('Internal', 'Headcount'), ext: s('External', 'Headcount'), heads, cost, joined: s('', 'Joined in month'), cph: heads ? cost * 100 / heads : 0 };
    }).filter((r) => r.heads > 0).sort((a, b) => b.cost - a.cost);
  }
  function projSum(d, country) {
    const rows = projRows(d, country);
    return { rows, heads: d3.sum(rows, (r) => r.heads), int: d3.sum(rows, (r) => r.int), ext: d3.sum(rows, (r) => r.ext), cost: d3.sum(rows, (r) => r.cost), joined: d3.sum(rows, (r) => r.joined) };
  }

  function renderProjects(d) {
    const scope = S.country || 'Group', t = totals(d, S.country), P = projSum(d, S.country);
    const pp = prevPeriod(), Pp = pp ? projSum(S.all[pp], S.country) : null;
    const hasCountry = (d.projects || []).some((r) => r.Country);
    const K = {
      heads: F.int(P.heads), int: F.int(P.int), ext: F.int(P.ext), mom_heads: Pp ? F.signed(P.heads - Pp.heads) : 'n/a',
      cost: P.cost.toFixed(2), cost_share: F.pctu(t.actual_cost_cr ? P.cost / t.actual_cost_cr : 0), mom_cost: Pp && Pp.cost ? F.pct(P.cost / Pp.cost - 1) : 'n/a',
      cph: F.lakh(P.heads ? P.cost * 100 / P.heads : 0), cph_all: F.lakh(t.cph_lakh), nproj: F.int(P.rows.length), joined: F.int(P.joined),
      head_share: F.pctu(t.actual_hc ? P.heads / t.actual_hc : 0)
    };
    $$('[data-p]').forEach((el) => (el.textContent = K[el.dataset.p]));
    const top = P.rows[0];
    $('#takeaway').textContent = !P.rows.length ? `${scope} has no project resources at the end of ${S.period}.`
      : `${scope} has ${P.rows.length} active project${P.rows.length > 1 ? 's' : ''} using ${F.int(P.heads)} heads (${K.head_share} of the workforce) at ₹${P.cost.toFixed(2)} Cr a month (${K.cost_share} of workforce cost); ${F.int(P.joined)} joined in ${S.period}. `
        + `${top.name} is the largest at ₹${top.cost.toFixed(2)} Cr with ${F.int(top.heads)} heads, ${F.pctu(top.ext / top.heads)} of them external.`
        + (Pp ? ` Since ${pp}, project heads moved ${F.signed(P.heads - Pp.heads)} and cost ${Pp.cost ? F.pct(P.cost / Pp.cost - 1) : 'n/a'}.` : '')
        + (S.country && !hasCountry ? ' (This month file has no country split for projects; figures are group-wide.)' : '');
    drawProjChart(P); drawProjTrend(); drawProjTable(P); 
    $('#proj-matrix-panel').hidden = !!S.country; if (!S.country) drawProjMatrix(d);
  }

  function drawProjChart(P) {
    const el = $('#proj-chart'); el.replaceChildren();
    if (!P.rows.length) { el.textContent = 'No project resources.'; return; }
    const C = COLORS(), W = Math.max(280, el.clientWidth), ml = 96, mr = 150, rowH = 38, H = P.rows.length * rowH + 24, tip = tooltip(el);
    const x = d3.scaleLinear().domain([0, d3.max(P.rows, (r) => r.heads)]).range([ml, W - mr]).nice(4);
    const y = d3.scaleBand().domain(P.rows.map((r) => r.short)).range([0, H - 24]).padding(0.25);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Project headcount, internal and external, with monthly cost');
    svg.append('g').attr('transform', `translate(0,${H - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((W - ml - mr) / 70))).tickFormat(d3.format(',')).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0).tickPadding(6)).call((g) => g.select('.domain').remove());
    P.rows.forEach((r) => {
      const op = S.hl && S.hl !== r.name ? 0.3 : 1;
      const g = svg.append('g').style('cursor', 'pointer').attr('opacity', op).on('click', () => { S.hl = S.hl === r.name ? '' : r.name; render(); })
        .on('pointermove', (ev) => showTip(tip, el, ev, `${r.name}: ${F.int(r.int)} internal + ${F.int(r.ext)} external · ₹${r.cost.toFixed(2)} Cr · ${r.countries.join(', ')}`, W))
        .on('pointerleave', () => tip.style('display', 'none'));
      g.append('rect').attr('x', x(0)).attr('width', x(r.int) - x(0)).attr('y', y(r.short)).attr('height', y.bandwidth()).attr('fill', C[0]);
      g.append('rect').attr('x', x(r.int)).attr('width', x(r.heads) - x(r.int)).attr('y', y(r.short)).attr('height', y.bandwidth()).attr('fill', C[1]);
      g.append('text').attr('class', 'val').attr('x', x(r.heads) + 6).attr('y', y(r.short) + y.bandwidth() / 2).attr('dy', '0.35em').text(`${F.int(r.heads)} · ₹${r.cost.toFixed(2)} Cr · ₹${F.lakh(r.cph)} L`);
    });
    const lg = d3.select(el).append('div').attr('class', 'legend');
    [['Internal', 0], ['External', 1]].forEach(([t, i]) => { const s = lg.append('span'); s.append('i').style('background', C[i]); s.append('span').text(t); });
  }

  function drawProjTrend() {
    const el = $('#proj-trend'); el.replaceChildren();
    const per = S.periods.map((p) => ({ p, rows: projRows(S.all[p], S.country) }));
    const names = [...new Set(per.flatMap((z) => z.rows.map((r) => r.name)))];
    if (!names.length) { el.textContent = 'No project resources.'; return; }
    const C = [...COLORS(), css('--ok'), css('--ref')];
    const series = names.map((n, i) => ({ n, short: n.replace(/^Project\s+/, '').split(' - ')[0], c: C[i % C.length],
      v: per.map((z) => ({ p: z.p, cost: (z.rows.find((r) => r.name === n) || { cost: 0 }).cost })) }));
    const W = Math.max(280, el.clientWidth), H = 260, ml = 46, mr = 70, mt = 14, mb = 26, tip = tooltip(el);
    const x = d3.scalePoint().domain(S.periods).range([ml, W - mr]).padding(0.3);
    const y = d3.scaleLinear().domain([0, d3.max(series, (s) => d3.max(s.v, (z) => z.cost)) * 1.1 || 1]).range([H - mb, mt]).nice(4);
    const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', 'Monthly cost by project');
    if (S.all[S.period]) svg.append('rect').attr('class', 'trend-sel').attr('x', x(S.period) - x.step() / 2).attr('width', x.step()).attr('y', mt - 8).attr('height', H - mb - mt + 8);
    svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).tickFormat((p) => p.replace('-20', " '")).tickSizeOuter(0));
    svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(autoFmt(y.domain())).tickSizeInner(-(W - ml - mr)).tickSizeOuter(0)).call((g) => g.select('.domain').remove());
    series.forEach((s) => {
      const op = S.hl && S.hl !== s.n ? 0.2 : 1;
      svg.append('path').datum(s.v).attr('class', 'mline').attr('stroke', s.c).attr('opacity', op).attr('d', d3.line().x((z) => x(z.p)).y((z) => y(z.cost)));
      s.v.forEach((z) => svg.append('circle').attr('cx', x(z.p)).attr('cy', y(z.cost)).attr('r', z.p === S.period ? 4.5 : 3).attr('fill', s.c).attr('opacity', op)
        .on('pointermove', (ev) => showTip(tip, el, ev, `${s.short} ${z.p}: ₹${z.cost.toFixed(2)} Cr`, W)).on('pointerleave', () => tip.style('display', 'none')));
      const last = s.v[s.v.length - 1];
      svg.append('text').attr('x', x(last.p) + 8).attr('y', y(last.cost)).attr('dy', '0.35em').style('fill', s.c).style('font-weight', 600).attr('opacity', op).text(s.short);
    });
  }

  function drawProjTable(P) {
    const tb = $('#proj-table tbody'); tb.replaceChildren();
    if (!P.rows.length) { const td = tb.insertRow().insertCell(); td.colSpan = 10; td.textContent = 'No project resources at month-end.'; return; }
    [...P.rows, { name: 'Total', countries: [...new Set(P.rows.flatMap((r) => r.countries))], int: P.int, ext: P.ext, heads: P.heads, joined: P.joined, cost: P.cost, cph: P.heads ? P.cost * 100 / P.heads : 0, total: true }]
      .forEach((r) => {
        const tr = tb.insertRow(); if (r.total) tr.className = 'total'; if (S.hl === r.name) tr.classList.add('hl');
        [r.name, r.countries.length > 3 ? r.countries.length + ' countries' : r.countries.join(', '), F.int(r.int), F.int(r.ext), F.int(r.heads), F.int(r.joined),
          r.cost.toFixed(2), F.lakh(r.cph), F.pctu(r.heads ? r.ext / r.heads : 0), F.pctu(P.cost ? r.cost / P.cost : 0)]
          .forEach((v) => { tr.insertCell().textContent = v; });
        if (!r.total) { tr.style.cursor = 'pointer'; tr.addEventListener('click', () => { S.hl = S.hl === r.name ? '' : r.name; render(); }); }
      });
  }

  function drawProjMatrix(d) {
    const rows = projRows(d, ''), countries = [...new Set(d.variance.map((r) => r.Country))];
    const th = $('#proj-matrix thead'), tb = $('#proj-matrix tbody'); th.replaceChildren(); tb.replaceChildren();
    const hr = th.insertRow(); const h0 = document.createElement('th'); h0.textContent = 'Project'; hr.append(h0);
    countries.forEach((c) => { const h = document.createElement('th'); h.textContent = c; h.className = 'cc'; h.addEventListener('click', () => setCountry(c)); hr.append(h); });
    const ht = document.createElement('th'); ht.textContent = 'Total'; hr.append(ht);
    const cell = (n, c) => d3.sum((d.projects || []).filter((r) => r['Project name'] === n && r.Country === c), (r) => +r.Headcount || 0);
    const mx = d3.max(rows.flatMap((r) => countries.map((c) => cell(r.name, c)))) || 1;
    const shade = d3.scaleLinear().domain([0, mx]).range([0.06, 0.85]);
    rows.forEach((r) => {
      const tr = tb.insertRow(); tr.insertCell().textContent = r.short;
      countries.forEach((c) => {
        const v = cell(r.name, c), td = tr.insertCell(); td.className = 'cell'; td.textContent = v ? F.int(v) : '–';
        if (v) { const col = d3.color(css('--s3')); col.opacity = shade(v); td.style.background = col.formatRgb(); if (shade(v) > 0.5) td.style.color = '#fff'; }
      });
      const tt = tr.insertCell(); tt.textContent = F.int(r.heads); tt.style.fontWeight = 600;
    });
  }

  function drawTrend() {
    const pts = S.periods.map((p) => ({ p, ...totals(S.all[p], S.country) }));
    const one = (el, fa, fb, fmt, label) => {
      el.replaceChildren();
      const W = Math.max(260, el.clientWidth), H = 200, ml = 54, mr = 16, mt = 18, mb = 26;
      const x = d3.scalePoint().domain(pts.map((z) => z.p)).range([ml, W - mr]).padding(0.4);
      const vals = pts.flatMap((z) => [fa(z), fb(z)]);
      const pad = (d3.max(vals) - d3.min(vals)) * 0.25 || 1;
      const y = d3.scaleLinear().domain([d3.min(vals) - pad, d3.max(vals) + pad]).range([H - mb, mt]).nice(4);
      const svg = d3.select(el).append('svg').attr('width', W).attr('height', H).attr('role', 'img').attr('aria-label', label);
      const sel = pts.find((z) => z.p === S.period);
      if (sel) svg.append('rect').attr('class', 'trend-sel').attr('x', x(sel.p) - x.step() / 2).attr('width', x.step()).attr('y', mt - 12).attr('height', H - mb - mt + 12);
      svg.append('g').attr('transform', `translate(0,${H - mb})`).call(d3.axisBottom(x).tickFormat((p) => p.replace('-20', " '")).tickSizeOuter(0));
      svg.append('g').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(4).tickFormat(fmt.axis === 'auto' ? autoFmt(y.domain()) : fmt.axis).tickSizeInner(-(W - ml - mr)).tickSizeOuter(0)).call((g) => g.select('.domain').remove());
      const line = (f) => d3.line().x((z) => x(z.p)).y((z) => y(f(z)));
      svg.append('path').datum(pts).attr('d', line(fb)).attr('fill', 'none').attr('stroke', css('--s2')).attr('stroke-width', 2).attr('stroke-dasharray', '5,4');
      svg.append('path').datum(pts).attr('d', line(fa)).attr('fill', 'none').attr('stroke', css('--s1')).attr('stroke-width', 2.5);
      const tip = tooltip(el);
      pts.forEach((z) => {
        svg.append('circle').attr('cx', x(z.p)).attr('cy', y(fb(z))).attr('r', 3).attr('fill', css('--s2'));
        svg.append('circle').attr('cx', x(z.p)).attr('cy', y(fa(z))).attr('r', z.p === S.period ? 5.5 : 4).attr('fill', css('--s1')).style('cursor', 'pointer')
          .on('pointermove', (ev) => showTip(tip, el, ev, `${z.p}: actual ${fmt.val(fa(z))}, budget ${fmt.val(fb(z))} (${F.pct(fa(z) / fb(z) - 1)})`, W))
          .on('pointerleave', () => tip.style('display', 'none')).on('click', () => setPeriod(z.p));
        const above = fa(z) >= fb(z);
        svg.append('text').attr('class', 'val').attr('x', x(z.p)).attr('y', y(fa(z)) + (above ? -10 : 18)).attr('text-anchor', 'middle').text(fmt.val(fa(z)));
      });
    };
    one($('#trend-hc'), (z) => z.actual_hc, (z) => z.budget_hc, { val: F.int, axis: d3.format(',') }, `Headcount trend ${S.country || 'group'}`);
    one($('#trend-cost'), (z) => z.actual_cost_cr, (z) => z.budget_cost_cr, { val: (v) => cr(v), axis: 'auto' }, `Cost trend ${S.country || 'group'}`);
  }

  // ---------- filters ----------
  function fillPeriodControls() {
    const years = [...new Set(S.periods.map((p) => p.split('-')[1]))];
    const ysel = $('#year'), msel = $('#month');
    const [m, y] = S.period.split('-');
    ysel.replaceChildren(...years.map((v) => new Option(v, v))); ysel.value = y;
    msel.replaceChildren(...S.periods.filter((p) => p.endsWith(y)).map((p) => new Option(p.split('-')[0], p.split('-')[0]))); msel.value = m;
    const countries = [...new Set(S.all[S.period].variance.map((r) => r.Country))];
    if (!countries.includes(S.country)) S.country = '';
    const d = S.all[S.period], wrap = $('#country-buttons');
    wrap.replaceChildren(...['', ...countries].map((c) => {
      const btn = document.createElement('button'); btn.type = 'button'; btn.dataset.c = c;
      btn.append(c || 'Group');
      const n = document.createElement('span'); n.className = 'n'; n.textContent = F.int(totals(d, c).actual_hc); btn.append(n);
      btn.addEventListener('click', () => setCountry(c));
      return btn;
    }));
    markCountry();
  }
  function setPeriod(p) { if (!S.all[p]) return; S.period = p; fillPeriodControls(); render(); }
  function markCountry() { $$('#country-buttons button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.c === S.country))); }
  function setCountry(c) { S.country = c; markCountry(); render(); window.scrollTo({ top: 0, behavior: 'smooth' }); }

  $('#year').addEventListener('change', (e) => { const y = e.target.value; const ps = S.periods.filter((p) => p.endsWith(y)); setPeriod(ps[ps.length - 1]); });
  $('#month').addEventListener('change', (e) => setPeriod(e.target.value + '-' + $('#year').value));
  $('#pop').addEventListener('change', (e) => { S.pop = e.target.value; render(); });
  $$('.tabs button').forEach((b) => b.addEventListener('click', () => { S.view = b.dataset.view; render(); }));
  $('#reset').addEventListener('click', () => { S.country = ''; S.pop = 'Total'; $('#pop').value = 'Total'; setPeriod(S.periods[S.periods.length - 1]); });

  // ---------- data loading ----------
  function check(d) {
    const need = ['kpi', 'walk', 'variance', 'grade_mix', 'location_mix'];
    const miss = need.filter((k) => !d || !d[k]);
    if (miss.length) throw new Error('not a consolidate.py dashboard file (missing ' + miss.join(', ') + ')');
    return d;
  }
  function add(d, source) {
    check(d); const p = d.kpi.period; S.all[p] = d; S.sources[p] = source;
    S.periods = Object.keys(S.all).sort((a, b) => pkey(a) - pkey(b));
    return p;
  }
  function start() {
    const fromHash = new URLSearchParams(location.hash.slice(1));
    const want = fromHash.get('p'); S.country = fromHash.get('c') || ''; S.view = fromHash.get('v') === 'projects' ? 'projects' : 'overview';
    S.period = S.all[want] ? want : S.periods[S.periods.length - 1];
    $('#status').textContent = ''; fillPeriodControls(); render();
  }
  const getJSON = (u) => fetch(u, { cache: 'no-cache' }).then((r) => { if (!r.ok) throw new Error(u + ': HTTP ' + r.status); return r.json(); });
  getJSON('data/index.json')
    .then((ix) => Promise.allSettled(ix.periods.map((p) => getJSON(`data/dashboard_data_${p}.json`).then((d) => add(d, `data/dashboard_data_${p}.json`)))))
    .catch(() => getJSON('data/dashboard_data.json').then((d) => add(d, 'data/dashboard_data.json')))
    .then((res) => {
      if (!S.periods.length) throw new Error('no months could be loaded');
      start();
      const failed = (Array.isArray(res) ? res : []).filter((r) => r.status === 'rejected').map((r) => r.reason.message);
      if (failed.length) { $('#status').textContent = 'Some months could not be loaded: ' + failed.join('; '); $('#status').className = 'sub err'; }
    })
    .catch((err) => {
      $('#takeaway').textContent = 'No data loaded yet.';
      $('#status').textContent = location.protocol === 'file:'
        ? 'This page was opened straight from your computer, and browsers do not let a page read the data folder that way. Click "Load month files" and select all the dashboard_data_*.json files at once, or open the published GitHub Pages link instead.'
        : 'Could not load data (' + err.message + '). Check that docs/data/ contains index.json and every dashboard_data_<Mon-YYYY>.json it lists, or click "Load month files".';
      $('#status').className = 'sub err';
    });

  $('#file').addEventListener('change', (e) => {
    const files = Array.from(e.target.files || []); if (!files.length) return;
    const bad = [];
    Promise.all(files.map((f) => f.text().then((t) => {
      const d = JSON.parse(t);
      if (Array.isArray(d.periods) && !d.kpi) return null;          // index.json – not needed when loading by hand
      return add(d, f.name + ' (this device)');
    }).catch((err) => { bad.push(f.name + ': ' + err.message); return null; })))
      .then((ps) => {
        const loaded = ps.filter(Boolean).sort((x, y) => pkey(x) - pkey(y));
        const st = $('#status');
        st.textContent = (loaded.length ? `Loaded ${loaded.length} month(s): ${loaded.join(', ')}.` : '') + (bad.length ? ' Skipped: ' + bad.join('; ') : '');
        st.className = bad.length ? 'sub err' : 'sub';
        if (!loaded.length) return;
        if (!S.period) { S.period = loaded[loaded.length - 1]; fillPeriodControls(); render(); } else setPeriod(loaded[loaded.length - 1]);
      });
    e.target.value = '';
  });
  window.addEventListener('hashchange', () => {
    const q = new URLSearchParams(location.hash.slice(1)); const p = q.get('p'), c = q.get('c') || '', v = q.get('v') === 'projects' ? 'projects' : 'overview';
    if ((p && p !== S.period && S.all[p]) || c !== S.country || v !== S.view) { S.country = c; S.view = v; setPeriod(S.all[p] ? p : S.period); markCountry(); }
  });
  let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(render, 150); });
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', render);

  // ---------- install as app (PWA) ----------
  let deferred;
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; $('#install').hidden = false; });
  $('#install').addEventListener('click', () => { if (!deferred) return; deferred.prompt(); deferred.userChoice.finally(() => { deferred = null; $('#install').hidden = true; }); });
  if ('serviceWorker' in navigator) window.addEventListener('load', () => navigator.serviceWorker.register('sw.js').catch(() => {}));
})();
