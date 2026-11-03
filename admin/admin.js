const { esc, $, api, num, vbars, hrow, donut, line, toast, modal, confirmBox, download, play } = D;
const root = $('#app');
let ME, LOCS, view = 'dash', timer, selCount = null;
const STATUS = { counting: ['Counting', ''], completion_requested: ['Completion requested', 'warn'], sticker_check: ['Sticker check', 'warn'], submitted: ['Submitted', 'ok'], none: ['No count', ''] };
const badge = s => { const [t, c] = STATUS[s] || [s, '']; return `<span class="badge ${c}">${t}</span>`; };
const NAV = [['dash', 'Visual Dashboard'], ['team', 'Team Member Wise'], ['task', 'Task Wise'], ['analytics', 'Analytics'], ['counts', 'Counts & Completion'], ['table', 'Count Table & Reports'], ['audit', 'Audit Trail'], ['emp', 'Employees']];

D.authPage(root, 'admin', 'COUNT ADMIN', 'Physical stock count control centre', m => { ME = m.user; LOCS = m.locations; shell(); });

function shell() {
  root.innerHTML = `<div class="shell"><aside class="side"><div class="logo">DUNE<small>COUNT ADMIN</small></div>
    ${NAV.map(([k, l]) => `<button class="nav" data-v="${k}">${l}</button>`).join('')}<span class="sp"></span>
    <div class="mute" style="padding:10px;font-size:12px">${esc(ME.name)}<br>${esc(ME.email)}</div><button class="nav" id="so">Sign out</button></aside>
    <main class="main"><div class="top"><h2 id="vt"></h2><span class="sp"></span><span class="mute" style="font-size:12px"><i class="live"></i> Live</span></div><div id="view"></div></main></div>`;
  root.querySelectorAll('.nav[data-v]').forEach(b => b.onclick = () => go(b.dataset.v));
  $('#so').onclick = D.signOut;
  go('dash');
}
function go(v) {
  view = v; clearInterval(timer);
  root.querySelectorAll('.nav[data-v]').forEach(b => b.classList.toggle('on', b.dataset.v === v));
  $('#vt').textContent = NAV.find(n => n[0] === v)[1];
  const fn = VIEWS[v]; fn(true);
  if (['dash', 'team', 'task', 'analytics', 'counts'].includes(v)) timer = setInterval(() => view === v && fn(false), 6000);
}
const V = () => $('#view');
const fmtT = t => (t || '').slice(5, 16);

const VIEWS = {
  async dash() {
    const d = await api('/dashboard'), k = d.kpi;
    const rf = d.recent_flags || [];
    V().innerHTML = (rf.length ? `<div class="card" style="border-color:var(--bad);margin-bottom:18px"><h3 class="bad">⚠ Sticker serial exceptions · ${rf.length} latest</h3><div class="tw" style="margin-top:12px;max-height:220px"><table><tr><th>Time</th><th>Location</th><th>Counter</th><th>Type</th><th>Detail</th></tr>${rf.map(f => `<tr><td>${f.ts}</td><td>${f.location}</td><td>${esc(f.user)}</td><td><span class="badge ${f.type === 'MISSING' ? 'bad' : 'warn'}">${f.type === 'MISSING' ? 'Missing sticker' : 'Serial change'}</span></td><td>${esc(f.detail)}</td></tr>`).join('')}</table></div></div>` : '') + `<div class="grid g4">
      ${[['Active counts', k.active, 0, ''], ['Book units (active)', k.book, 0, ''], ['Units counted', k.counted, 0, ''], ['Completion', k.pct, 1, '%'], ['Stickers used', k.stickers, 0, ''], ['Counts submitted', k.submitted, 0, ''], ['Team members active', k.team, 0, ''], ['Sticker exceptions', k.flags, 0, '']].map(([l, v, dc, s], i) => `<div class="card kpi" style="animation-delay:${i * 60}ms"><div class="lbl">${l}</div><div class="val ${l === 'Sticker exceptions' && v ? 'bad' : ''}">${num(v, 'k' + i, dc, s)}</div></div>`).join('')}</div>
      <div class="grid g2" style="margin-top:18px"><div class="card"><h3>Completion status by location</h3><div style="margin-top:14px">${vbars(d.locations.map(l => ({ label: l.location, value: l.pct, suffix: '%' })), 'loc', 100)}</div></div>
      <div class="card"><h3>Units counted vs book</h3><div style="margin-top:8px">${d.locations.map((l, i) => hrow(`${l.location} · ${l.name}`, l.counted, l.book, 'lc' + i, l.book ? `${l.counted} / ${l.book}` : 'no count', l.status === 'submitted' ? 'ok' : '')).join('')}</div></div></div>
      <div class="grid g2" style="margin-top:18px"><div class="card"><h3>Scans over time (cumulative)</h3><div style="margin-top:12px">${line(d.timeline.map(t => ({ x: t.t.slice(11), y: t.cum })), 'tl')}</div></div>
      <div class="card"><h3>Count status</h3><div style="margin-top:14px">${donut(Object.entries(d.status_dist).map(([s, n], i) => ({ label: (STATUS[s] || [s])[0], value: n, color: ['#00AEEF', '#fff', '#ffc857', '#2ee59d', '#7f8fb0'][i % 5] })), d.counts.length, 'counts', 'sd')}</div></div></div>`;
    play(V());
  },

  async team() {
    const d = await api('/dashboard'), m = d.members, tot = m.reduce((a, x) => a + x.n, 0) || 1;
    V().innerHTML = m.length ? `<div class="grid g2"><div class="card"><h3>Units counted per member</h3><div style="margin-top:14px">${vbars(m.slice(0, 8).map(x => ({ label: x.user_name.split(' ')[0], value: x.n })), 'tm')}</div></div>
      <div class="card"><h3>Share of total effort</h3><div style="margin-top:14px">${donut(m.slice(0, 6).map((x, i) => ({ label: x.user_name.split(' ')[0], value: x.n, color: ['#00AEEF', '#fff', '#58d3ff', '#7fd9ff', '#0577a8', '#bde9fb'][i] })), tot, 'units', 'ts')}</div></div></div>
      <div class="card" style="margin-top:18px"><h3>Team scorecard</h3><div class="tw" style="margin-top:12px"><table><tr><th>#</th><th>Member</th><th>Units</th><th>Share</th><th>Units / hour</th><th>Counts worked</th><th>Excess flagged</th><th>First scan</th><th>Last scan</th></tr>
      ${m.map((x, i) => `<tr><td>${i + 1}</td><td><b>${esc(x.user_name)}</b></td><td>${num(x.n, 'tn' + i)}</td><td style="min-width:140px">${hrow('', x.n, tot, 'tsh' + i, '')}</td><td>${num(x.rate_per_hour, 'tr' + i, 1)}</td><td>${x.counts_n}</td><td>${x.excess}</td><td>${fmtT(x.first_ts)}</td><td>${fmtT(x.last_ts)}</td></tr>`).join('')}</table></div></div>`
      : '<div class="card empty">No scans recorded yet. Member performance appears as soon as the count team starts.</div>';
    play(V());
  },

  async task() {
    const d = await api('/dashboard'), steps = ['Counting', 'Completion requested', 'Confirmed', 'Submitted'];
    const idx = { counting: 0, completion_requested: 1, sticker_check: 2, submitted: 3 };
    V().innerHTML = d.counts.length ? `<div class="grid g2">${d.counts.map((c, i) => `<div class="card" style="animation-delay:${i * 70}ms"><div class="row"><div><h2>${c.location} <span class="mute" style="font-size:14px">${esc(c.location_name)}</span></h2><div class="mute" style="font-size:13px">${esc(c.name)}</div></div><span class="sp"></span>${badge(c.status)}</div>
      <div class="steps">${steps.map((s, n) => `<div class="step ${n <= idx[c.status] ? 'done' : ''} ${n === idx[c.status] && c.status !== 'submitted' ? 'now' : ''}">${s}</div>`).join('')}</div>
      ${hrow('Progress', c.matched, c.book, 'tk' + c.id, `${num(c.counted, 'tkc' + c.id)} counted / ${c.book} book`, c.status === 'submitted' ? 'ok' : '')}
      <div class="mute" style="font-size:13px;margin:10px 0 4px">Assigned work done by</div>
      ${c.members.length ? c.members.map((m, n) => hrow(m.user_name, m.n, c.counted, `tkm${c.id}_${n}`, m.n + ' units')).join('') : '<div class="mute" style="font-size:13px">No scans yet</div>'}
      <div class="row mute" style="font-size:12px;margin-top:8px"><span>Started ${fmtT(c.created_at)} by ${esc(c.created_by)}</span><span class="sp"></span>${c.closed_at ? '<span>Closed ' + fmtT(c.closed_at) + '</span>' : ''}</div></div>`).join('')}</div>`
      : '<div class="card empty">No count tasks yet. Start a count under “Counts & Completion”.</div>';
    play(V());
  },

  async analytics() {
    const cs = await api('/counts');
    if (cs.length && !cs.some(c => c.id === selCount)) selCount = cs[0].id;
    if (arguments[0] === false && document.activeElement && document.activeElement.id === 'ac2') return;
    const [a, rf] = await Promise.all([api('/analytics'), cs.length ? api(`/counts/${selCount}/recon-full`) : null]);
    const v = a.variance, tv = v.zero + v.minus + v.plus;
    const eq = (x, y) => x === y ? 'ok' : 'bad';
    const recon = rf ? `<div class="card" style="margin-bottom:18px"><div class="row"><h3>Reconciliation</h3><span class="sp"></span><select id="ac2" style="width:auto;min-width:260px">${cs.map(c => `<option value="${c.id}" ${c.id === selCount ? 'selected' : ''}>${c.location} · ${esc(c.name)} (${(STATUS[c.status] || [c.status])[0]})</option>`).join('')}</select></div>
      <div class="grid g2" style="margin-top:14px">
        <div class="card" style="box-shadow:none"><h3>1 · Sticker to physical units</h3><table style="margin-top:10px">
          <tr><td>Physical units counted</td><td style="text-align:right"><b>${num(rf.sticker.units, 'r1')}</b></td></tr>
          <tr><td>+ Missing stickers (used, no bar code)</td><td style="text-align:right" class="${rf.sticker.missing ? 'bad' : ''}"><b>${num(rf.sticker.missing, 'r2')}</b></td></tr>
          <tr><td>= Stickers used (system)</td><td style="text-align:right"><b>${num(rf.sticker.total_used, 'r3')}</b></td></tr>
          <tr><td>Stickers declared by admin</td><td style="text-align:right"><b>${rf.sticker.declared ?? '-'}</b></td></tr>
          <tr><td>Status</td><td style="text-align:right">${rf.sticker.declared == null ? '<span class="badge warn">Pending submission</span>' : `<span class="badge ${eq(rf.sticker.declared, rf.sticker.total_used)}">${rf.sticker.declared === rf.sticker.total_used ? 'Reconciled' : 'Difference ' + (rf.sticker.declared - rf.sticker.total_used)}</span>`}</td></tr></table>
          ${rf.sticker.missing ? `<p class="bad" style="font-size:13px;margin:10px 0 0">Missing: ${rf.sticker.missing_list.map(m => esc(m.sticker_no)).join(', ')}</p>` : ''}</div>
        <div class="card" style="box-shadow:none"><h3>2 · Book count to physical count</h3><table style="margin-top:10px">
          <tr><td>Book stock units</td><td style="text-align:right"><b>${num(rf.book.book, 'r4')}</b></td></tr>
          <tr><td>Physical units counted</td><td style="text-align:right"><b>${num(rf.book.physical, 'r5')}</b></td></tr>
          <tr><td>Matched (variance 0)</td><td style="text-align:right" class="ok"><b>${num(rf.book.matched, 'r6')}</b></td></tr>
          <tr><td>In book, not physically found (-1)</td><td style="text-align:right" class="${rf.book.not_found ? 'bad' : ''}"><b>${num(rf.book.not_found, 'r7')}</b></td></tr>
          <tr><td>Physical, not in book (+1)</td><td style="text-align:right" class="${rf.book.excess ? 'warn' : ''}"><b>${num(rf.book.excess, 'r8')}</b></td></tr>
          <tr><td>Net variance (physical - book)</td><td style="text-align:right"><b>${rf.book.net_variance > 0 ? '+' : ''}${rf.book.net_variance}</b></td></tr></table>
          ${rf.count.status !== 'submitted' ? '<p class="warn" style="font-size:13px;margin:10px 0 0">Provisional: count still in progress, so "not found" will fall as counting continues.</p>' : ''}</div></div>
      <div class="grid g2" style="margin-top:18px">
        <div class="card" style="box-shadow:none"><h3 class="warn">Physically available, not in book stock · ${rf.excess.length}</h3><div class="tw" style="margin-top:10px;max-height:300px"><table><tr><th>Bar code</th><th>Sticker</th><th>Counted by</th><th>Time</th></tr>${rf.excess.map(x => `<tr><td><b>${esc(x.barcode)}</b></td><td>${esc(x.sticker_no)}</td><td>${esc(x.counted_by)}</td><td>${x.counted_at}</td></tr>`).join('') || '<tr><td colspan=4 class="empty">None</td></tr>'}</table></div></div>
        <div class="card" style="box-shadow:none"><h3 class="bad">In book stock, not physically available · ${rf.not_found.length}</h3><div class="tw" style="margin-top:10px;max-height:300px"><table><tr><th>Bar code</th><th>Description</th></tr>${rf.not_found.map(x => `<tr><td><b>${esc(x.barcode)}</b></td><td>${esc(x.description)}</td></tr>`).join('') || '<tr><td colspan=2 class="empty">None</td></tr>'}</table></div></div></div>
      <div class="row" style="margin-top:14px"><button class="btn sm" id="rx">Excel: count vs book</button><button class="btn sm ghost" id="rc">Results CSV</button></div></div>` : '';
    V().innerHTML = recon + `<div class="grid g4">${[['Excess (not in book) rate', a.excess_rate, 1, '%'], ['Matched units', v.zero, 0, ''], ['Missing (-1)', v.minus, 0, ''], ['Excess (+1)', v.plus, 0, '']].map(([l, x, dc, s], i) => `<div class="card kpi"><div class="lbl">${l}</div><div class="val">${num(x, 'a' + i, dc, s)}</div></div>`).join('')}</div>
      <div class="grid g2" style="margin-top:18px"><div class="card"><h3>Scans per hour</h3><div style="margin-top:12px">${vbars(a.hourly.slice(-10).map(h => ({ label: h.h.slice(11, 13) + 'h', value: h.n })), 'hr')}</div></div>
      <div class="card"><h3>Variance distribution (submitted counts)</h3><div style="margin-top:14px">${tv ? donut([{ label: '0', value: v.zero, color: '#2ee59d' }, { label: '-1', value: v.minus, color: '#ff5d7a' }, { label: '+1', value: v.plus, color: '#ffc857' }], tv, 'units', 'vd') : '<div class="empty">Appears after the first submitted count</div>'}</div></div></div>
      <div class="grid g2" style="margin-top:18px"><div class="card"><h3>Counting speed (median seconds per unit)</h3><div style="margin-top:10px">${a.speed.length ? a.speed.map((s, i) => hrow(s.name, 30 / Math.max(s.median_sec, 1), 1, 'sp' + i, num(s.median_sec, 'spv' + i, 1, ' s'))).join('') : '<div class="empty">Need 2+ scans per member</div>'}</div></div>
      <div class="card"><h3>Accuracy by submitted count</h3><div style="margin-top:10px">${a.accuracy.length ? a.accuracy.map((s, i) => hrow(s.location + ' · ' + s.name, s.accuracy, 100, 'ac' + i, num(s.accuracy, 'acv' + i, 1, '%'), s.accuracy >= 98 ? 'ok' : s.accuracy >= 90 ? 'warn' : 'bad')).join('') : '<div class="empty">No submitted counts yet</div>'}</div></div></div>
      <div class="card" style="margin-top:18px"><h3>Count duration (minutes, start to submit)</h3><div style="margin-top:12px">${a.durations.length ? vbars(a.durations.map(x => ({ label: x.location, value: x.minutes })), 'du') : '<div class="empty">No completed counts yet</div>'}</div></div>`;
    play(V());
    if ($('#ac2')) {
      $('#ac2').onchange = e => { selCount = +e.target.value; VIEWS.analytics(true); };
      $('#rx').onclick = () => download(`/counts/${selCount}/export/xlsx`, 'export');
      $('#rc').onclick = () => download(`/counts/${selCount}/export/results`, 'export');
    }
  },

  async counts() {
    const cs = await api('/counts');
    const html = `<div class="card"><h3>Start a new count</h3><p class="mute" style="font-size:13px">Upload the book quantity Excel (.xlsx / .csv). Row 1 = headers; one row per unit with a <b>Barcode</b> column (and optional <b>Description</b>). Counters will only see these barcodes. <a href="/api/template.xlsx">Download template</a></p>
      <form id="nc" class="grid g3"><div><label>Location</label><select id="nl">${Object.entries(LOCS).map(([k, v]) => `<option value="${k}">${k} · ${v}</option>`).join('')}</select></div>
      <div><label>Count name (optional)</label><input id="nn" placeholder="e.g. October monthly count"></div>
      <div><label>Book quantity file</label><input id="nf" type="file" accept=".xlsx,.xlsm,.csv" required></div>
      <div><button class="btn" style="margin-top:6px">Upload & start count</button></div></form></div>
      <div class="grid g2" style="margin-top:18px">${cs.map(c => `<div class="card"><div class="row"><h2>${c.location}</h2><span class="mute">${esc(c.name)}</span><span class="sp"></span>${badge(c.status)}</div>
        ${hrow('Completion', c.matched, c.book, 'cc' + c.id, `${num(c.counted, 'ccn' + c.id)} / ${c.book} units`, c.status === 'submitted' ? 'ok' : '')}
        <div class="mute" style="font-size:13px">Stickers used: <b class="cy">${c.stickers_used}</b>${c.missing_stickers ? ` (${c.counted} units + <span class="bad">${c.missing_stickers} missing</span>)` : ''}${c.stickers_declared != null ? ' · declared ' + c.stickers_declared : ''}${c.unlisted ? ` · <span class="warn">${c.unlisted} excess</span>` : ''}${c.sticker_flags ? ` · <a href="#" class="bad" data-a="table" data-id="${c.id}">⚠ ${c.sticker_flags} sticker exception(s)</a>` : ''}${c.requested_by ? `<br>Completion requested by ${esc(c.requested_by)} at ${fmtT(c.requested_at)}` : ''}</div>
        <div class="row" style="margin-top:14px">${actions(c)}</div></div>`).join('') || '<div class="card empty">No counts yet</div>'}</div>`;
    if (arguments[0] === false && (document.activeElement || {}).tagName && /INPUT|SELECT/.test(document.activeElement.tagName)) return;
    V().innerHTML = html; play(V());
    $('#nc').onsubmit = async e => {
      e.preventDefault(); const f = new FormData(); f.append('location', $('#nl').value); f.append('name', $('#nn').value); f.append('file', $('#nf').files[0]);
      try { const r = await api('/counts', { method: 'POST', form: f }); toast(`Count started: ${r.units} book units loaded${r.duplicates ? ', ' + r.duplicates + ' duplicate rows ignored' : ''}`, 'ok'); VIEWS.counts(true); } catch (er) { toast(er.message, 'bad'); }
    };
    V().querySelectorAll('[data-a]').forEach(b => b.onclick = () => act(b.dataset.a, +b.dataset.id));
  },

  async table() {
    const cs = await api('/counts'); if (!selCount && cs[0]) selCount = cs[0].id;
    V().innerHTML = `<div class="card"><div class="row"><div style="min-width:260px"><label style="margin-top:0">Count</label><select id="tc">${cs.map(c => `<option value="${c.id}" ${c.id == selCount ? 'selected' : ''}>${c.location} · ${esc(c.name)} (${(STATUS[c.status] || [c.status])[0]})</option>`).join('')}</select></div>
      <div style="flex:1;min-width:200px"><label style="margin-top:0">Search</label><input id="ts" placeholder="barcode / sticker / member"></div></div>
      <div class="row" style="margin-top:14px"><button class="btn sm" data-x="entries">Count table CSV</button><button class="btn sm" data-x="results">Results CSV</button><button class="btn sm" data-x="xlsx">Excel: count vs book</button><button class="btn sm ghost" data-x="audit">Audit CSV</button></div></div>
      <div id="rep"></div>`;
    if (!cs.length) { $('#rep').innerHTML = '<div class="card empty" style="margin-top:18px">No counts yet</div>'; return; }
    $('#tc').onchange = e => { selCount = +e.target.value; draw(); };
    V().querySelectorAll('[data-x]').forEach(b => b.onclick = () => selCount && download(`/counts/${selCount}/export/${b.dataset.x}`, 'export'));
    let rep, ent;
    const draw = async () => {
      let fl, rc;
      [rep, ent, fl, rc] = await Promise.all([api(`/counts/${selCount}/report`), api(`/counts/${selCount}/entries`), api(`/counts/${selCount}/flags`), api(`/counts/${selCount}/recon`)]);
      const s = rep.summary, c = rep.count;
      $('#rep').innerHTML = `<div class="grid g4" style="margin-top:18px">${[['Book units', s.book], ['Counted', s.counted], ['Variance 0', s.zero], ['Variance -1 (missing)', s.minus], ['Variance +1 (excess)', s.plus]].map(([l, v], i) => `<div class="card kpi"><div class="lbl">${l}</div><div class="val">${num(v, 'rp' + i)}</div></div>`).join('')}</div>
        ${c.status !== 'submitted' ? '<p class="warn" style="margin:14px 2px">Provisional: count is not yet submitted. Missing (-1) will fall as counting progresses.</p>' : ''}
        <div class="card" style="margin-top:18px;${fl.length ? 'border-color:var(--bad)' : ''}"><h3 class="${fl.length ? 'bad' : ''}">Sticker exceptions · ${fl.length}</h3>
        ${fl.length ? `<div class="tw" style="margin-top:12px;max-height:260px"><table><tr><th>Time</th><th>Counter</th><th>Type</th><th>Sticker</th><th>Detail</th></tr>${fl.map(f => `<tr><td>${f.ts}</td><td>${esc(f.user)}</td><td><span class="badge ${f.type === 'MISSING' ? 'bad' : 'warn'}">${f.type === 'MISSING' ? 'Missing sticker' : 'New booklet / serial change'}</span></td><td>${esc(f.sticker)}</td><td>${esc(f.detail)}</td></tr>`).join('')}</table></div>` : '<p class="ok" style="margin:10px 0 0">No missing stickers or serial changes.</p>'}</div>
        <div class="card" style="margin-top:18px"><h3>Sticker reconciliation</h3><div class="row" style="margin-top:12px;gap:28px">
          <div class="kpi"><div class="lbl">Units counted</div><div class="val" style="font-size:30px">${rc.units}</div></div>
          <div class="kpi"><div class="lbl">+ Missing stickers</div><div class="val ${rc.missing_count ? 'bad' : ''}" style="font-size:30px">${rc.missing_count}</div></div>
          <div class="kpi"><div class="lbl">= Stickers used</div><div class="val" style="font-size:30px">${rc.total_used}</div></div></div>
          ${rc.missing_count ? `<p class="bad" style="margin:12px 0 0;font-size:13px">Used but no bar code (missing sequence): ${rc.missing.map(m => esc(m.sticker_no)).join(', ')}</p>` : '<p class="ok" style="margin:12px 0 0;font-size:13px">No missing stickers.</p>'}</div>
        <div class="card" style="margin-top:18px"><h3>Count table · ${ent.length} units</h3><div class="tw" style="margin-top:12px"><table id="et"></table></div></div>
        <div class="card" style="margin-top:18px"><h3>Variance report (book vs physical)</h3><div class="tw" style="margin-top:12px"><table id="vt2"></table></div></div>`;
      play($('#rep')); filt();
    };
    const filt = () => {
      const q = $('#ts').value.toLowerCase();
      $('#et').innerHTML = '<tr><th>Time</th><th>Barcode</th><th>Description</th><th>Sticker</th><th>Status</th><th>Counted by</th><th></th></tr>' + ent.filter(e => (e.barcode + e.sticker_no + e.user_name).toLowerCase().includes(q)).map(e => `<tr><td>${e.ts}</td><td><b>${esc(e.barcode)}</b></td><td>${esc(e.description || '')}</td><td>${esc(e.sticker_no)}${e.sticker_flag ? ` <span class="badge ${e.sticker_flag === 'MISSING' ? 'bad' : 'warn'}" title="${esc(e.flag_detail)}">${e.sticker_flag === 'MISSING' ? 'gap' : 'new series'}</span>` : ''}</td><td>${e.in_book ? '<span class="badge ok">In book</span>' : '<span class="badge warn">Excess</span>'}</td><td>${esc(e.user_name)}</td><td>${rep.count.status !== 'submitted' ? `<button class="btn sm danger" data-del="${e.id}">Remove</button>` : ''}</td></tr>`).join('');
      $('#vt2').innerHTML = '<tr><th>Barcode</th><th>Description</th><th>Sticker</th><th>Book</th><th>Counted</th><th>Diff</th></tr>' + rep.rows.filter(r => (r.barcode + r.sticker_no).toLowerCase().includes(q)).map(r => `<tr><td><b>${esc(r.barcode)}</b></td><td>${esc(r.description)}</td><td>${esc(r.sticker_no)}</td><td>${r.book_qty}</td><td>${r.counted_qty}</td><td><span class="badge ${r.difference === 0 ? 'ok' : r.difference < 0 ? 'bad' : 'warn'}">${r.difference > 0 ? '+' : ''}${r.difference}</span></td></tr>`).join('');
      V().querySelectorAll('[data-del]').forEach(b => b.onclick = async () => { if (await confirmBox('Remove this unit?', 'It will be logged in the audit trail.', 'Remove')) { try { await api(`/counts/${selCount}/entries/${b.dataset.del}`, { method: 'DELETE' }); draw(); } catch (e) { toast(e.message, 'bad'); } } });
    };
    $('#ts').oninput = () => rep && filt();
    draw();
  },

  async audit() {
    const cs = await api('/counts');
    V().innerHTML = `<div class="card"><div class="row"><div style="min-width:260px"><label style="margin-top:0">Count</label><select id="ac"><option value="">All activity</option>${cs.map(c => `<option value="${c.id}">${c.location} · ${esc(c.name)}</option>`).join('')}</select></div><span class="sp"></span>
      <button class="btn sm" id="ax">Export audit CSV</button></div><div class="tw" style="margin-top:14px"><table id="at"></table></div></div>`;
    const draw = async () => {
      const id = $('#ac').value, a = await api('/audit' + (id ? '?count_id=' + id : ''));
      $('#at').innerHTML = '<tr><th>Timestamp</th><th>User</th><th>Location</th><th>Action</th><th>Detail</th></tr>' + a.map(r => `<tr><td style="white-space:nowrap">${r.ts}</td><td>${esc(r.user_name || '')}</td><td>${r.location || '-'}</td><td><span class="badge ${/mismatch|removed/.test(r.action) ? 'bad' : /submitted|confirmed/.test(r.action) ? 'ok' : ''}">${r.action}</span></td><td>${esc(r.detail)}</td></tr>`).join('');
    };
    $('#ac').onchange = draw; $('#ax').onclick = () => { const id = $('#ac').value; download(id ? `/counts/${id}/export/audit` : '/export/audit', 'audit.csv'); };
    draw();
  },

  async emp() {
    const list = await api('/employees');
    V().innerHTML = `<div class="grid g2" style="align-items:start"><div class="card"><h3>Add employee</h3><p class="mute" style="font-size:13px">Only email ids added here can sign up. The employee signs up once with this exact email, then signs in.</p>
      <form id="ef"><label>Full name</label><input id="en" required><label>Email id</label><input id="ee" type="email" required><label>Role</label>
      <select id="er"><option value="counter">Count person</option><option value="admin">Count admin</option></select><button class="btn" style="margin-top:18px">Add employee</button></form></div>
      <div class="card"><h3>Employees</h3><div class="tw" style="margin-top:12px"><table><tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th><th>Scans</th><th></th></tr>
      ${list.map(u => `<tr><td>${esc(u.name)}</td><td>${esc(u.email)}</td><td>${u.role === 'admin' ? 'Admin' : 'Counter'}</td><td>${u.registered ? '<span class="badge ok">Registered</span>' : '<span class="badge warn">Awaiting sign-up</span>'}</td><td>${u.scans}</td><td>${u.id === ME.id ? '' : `<button class="btn sm danger" data-rm="${u.id}">Remove</button>`}</td></tr>`).join('')}</table></div></div></div>`;
    $('#ef').onsubmit = async e => { e.preventDefault(); try { await api('/employees', { method: 'POST', body: { name: $('#en').value, email: $('#ee').value, role: $('#er').value } }); toast('Employee added', 'ok'); VIEWS.emp(); } catch (er) { toast(er.message, 'bad'); } };
    V().querySelectorAll('[data-rm]').forEach(b => b.onclick = async () => { if (await confirmBox('Remove employee?', 'They will lose access immediately.', 'Remove')) { await api('/employees/' + b.dataset.rm, { method: 'DELETE' }); VIEWS.emp(); } });
  }
};

function actions(c) {
  const b = (a, t, cls = '') => `<button class="btn sm ${cls}" data-a="${a}" data-id="${c.id}">${t}</button>`;
  if (c.status === 'counting') return b('confirm', 'Confirm completion') + b('table', 'View table', 'ghost');
  if (c.status === 'completion_requested') return b('confirm', 'Confirm completion') + b('reopen', 'Send back to counters', 'ghost') + b('table', 'View table', 'ghost');
  if (c.status === 'sticker_check') return b('stickers', 'Confirm sticker count & submit') + b('reopen', 'Reopen', 'ghost');
  return b('xlsx', 'Excel: count vs book') + b('results', 'Results CSV', 'ghost') + b('table', 'View report', 'ghost');
}
async function act(a, id) {
  try {
    if (a === 'table') { selCount = id; return go('table'); }
    if (a === 'xlsx' || a === 'results') return download(`/counts/${id}/export/${a}`, 'export');
    if (a === 'confirm') { if (!await confirmBox('Confirm count completion?', 'Counters will no longer be able to add units to this count.', 'Confirm')) return; await api(`/counts/${id}/confirm-completion`, { method: 'POST' }); toast('Completion confirmed. Now confirm the sticker count.', 'ok'); }
    if (a === 'reopen') { await api(`/counts/${id}/reopen`, { method: 'POST' }); toast('Count reopened'); }
    if (a === 'stickers') return stickerDialog(id);
    VIEWS.counts(true);
  } catch (e) { toast(e.message, 'bad'); }
}
async function stickerDialog(id) {
  const rc = await api(`/counts/${id}/recon`);
  const m = modal(`<h2>Sticker reconciliation</h2><div class="row" style="gap:22px;margin:6px 0 4px">
    <div class="kpi"><div class="lbl">Units counted</div><div class="val" style="font-size:28px">${rc.units}</div></div>
    <div class="kpi"><div class="lbl">+ Missing stickers</div><div class="val ${rc.missing_count ? 'bad' : ''}" style="font-size:28px">${rc.missing_count}</div></div>
    <div class="kpi"><div class="lbl">= Expected</div><div class="val" style="font-size:28px">${rc.total_used}</div></div></div>
    ${rc.missing_count ? `<p class="bad" style="font-size:13px">Used but no bar code: ${rc.missing.map(x => esc(x.sticker_no)).join(', ')}</p>` : ''}
    <p class="mute">Enter the total number of stickers used at this location (check the booklets physically). It must equal units counted plus missing stickers, otherwise submission is blocked.</p>
    <label>Stickers used</label><input id="sn" type="number" min="0" autofocus><div id="se" class="bad" style="min-height:22px;margin-top:10px;font-size:13px"></div>
    <div class="row" style="margin-top:12px"><span class="sp"></span><button class="btn ghost" id="sc">Cancel</button><button class="btn" id="ss">Confirm & generate report</button></div>`);
  $('#sc', m).onclick = () => m.close();
  $('#ss', m).onclick = async () => {
    try { await api(`/counts/${id}/submit`, { method: 'POST', body: { stickers: $('#sn', m).value } }); m.close(); toast('Count submitted. Variance report generated.', 'ok'); selCount = id; go('table'); }
    catch (e) { $('#se', m).textContent = e.message; }
  };
}
