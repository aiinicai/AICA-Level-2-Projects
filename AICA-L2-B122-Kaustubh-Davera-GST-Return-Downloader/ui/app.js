'use strict';
/* GST Downloader UI. Talks to Python through window.pywebview.api (see api.py). */

const $ = (id) => document.getElementById(id);
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const S = {
  init: null, clients: [], selected: new Set(), filter: 'all', search: '',
  mode: 'A', fy: null, months: new Set(), single: null, client: null,
  tab: 'clients', job: null, jobKey: '', promptId: null, polling: false,
  emailItems: [], emailSel: null, editing: null, showPwd: false,
};

/* ------------------------------------------------------------ helpers */
function api(name, ...args) {
  try {
    return window.pywebview.api[name](...args).then((r) => r, (e) => ({ ok: false, error: String(e) }));
  } catch (e) {
    return Promise.resolve({ ok: false, error: String(e) });
  }
}
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
let toastTimer = null;
function toast(msg, err) {
  const t = $('toast');
  t.textContent = msg;
  t.className = 'toast' + (err ? ' err' : '');
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, err ? 7000 : 3500);
}
function fail(r) { toast(r && r.error ? r.error : 'Something went wrong', true); }
function fyLabel(y) { return `${y}-${String((y + 1) % 100).padStart(2, '0')}`; }
function key(y, m) { return `${y}-${m}`; }
function unkey(k) { return k.split('-').map(Number); }
function periodSort(a, b) { const [ay, am] = unkey(a), [by, bm] = unkey(b); return ay - by || am - bm; }
function isAvail(y, m) { const [ty, tm] = S.init.today; return y < ty || (y === ty && m < tm); }
function fyMonths(fy) {
  const out = [];
  for (let m = 4; m <= 12; m++) out.push([fy, m]);
  for (let m = 1; m <= 3; m++) out.push([fy + 1, m]);
  return out;
}

function confirmBox(title, text, yes = 'Yes') {
  return new Promise((resolve) => {
    $('cfTitle').textContent = title;
    $('cfText').textContent = text;
    $('cfYes').textContent = yes;
    showModal('confirmModal');
    const done = (v) => { $('cfYes').onclick = $('cfNo').onclick = null; hideModal('confirmModal'); resolve(v); };
    $('cfYes').onclick = () => done(true);
    $('cfNo').onclick = () => done(false);
  });
}
function showModal(id) {
  ['captchaModal', 'manualModal', 'confirmModal'].forEach((m) => { $(m).hidden = m !== id; });
  $('overlay').hidden = false;
}
function hideModal(id) {
  $(id).hidden = true;
  if (['captchaModal', 'manualModal', 'confirmModal'].every((m) => $(m).hidden)) $('overlay').hidden = true;
}

/* ------------------------------------------------------------ tabs */
function show(tab) {
  S.tab = tab;
  document.querySelectorAll('.nav').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab').forEach((s) => { s.hidden = s.id !== 'tab-' + tab; });
  if (tab === 'clients') renderClients();
  if (tab === 'download') renderDownload();
  if (tab === 'status') poll();
  if (tab === 'email') loadEmail();
  if (tab === 'settings') loadSettings();
}

/* ------------------------------------------------------------ clients */
function status(c) {
  if (c.blocked) return { cls: 'b-bad', icon: '✕', text: 'Blocked' };
  if (c.errors.length) return { cls: 'b-bad', icon: '!', text: c.errors[0] };
  if (c.warnings.length) return { cls: 'b-warn', icon: '!', text: c.warnings[0] };
  return { cls: 'b-ok', icon: '✓', text: 'Ready' };
}
const isReady = (c) => !c.blocked && !c.errors.length;
const FILTERS = [
  ['all', 'All', () => true],
  ['ready', 'Ready', isReady],
  ['issues', 'Issues', (c) => c.errors.length || c.warnings.length],
  ['blocked', 'Blocked', (c) => c.blocked],
  ['old', 'Old password', (c) => c.pwd_old],
];

function applyInit(r) {
  if (!r || r.ok === false) { fail(r); return; }
  S.init = r;
  S.clients = r.clients.slice().sort((a, b) => a.display_name.localeCompare(b.display_name));
  const have = new Set(S.clients.map((c) => c.gstin));
  [...S.selected].forEach((g) => { if (!have.has(g)) S.selected.delete(g); });
  $('firmName').textContent = r.firm_name;
  $('excelPath').textContent = r.excel_path;
  $('clientCount').textContent = `${S.clients.length} clients`;
  $('loadedAt').textContent = r.loaded_at;
  $('loadError').hidden = !r.load_error;
  $('loadError').textContent = r.load_error || '';
  if (!$('dlFolder').value) $('dlFolder').value = r.download_folder;
  if (S.fy === null) S.fy = r.current_fy;
  renderClients();
  if (S.tab === 'download') renderDownload();
}

function shownClients() {
  const f = FILTERS.find((x) => x[0] === S.filter)[2];
  const q = S.search.trim().toLowerCase();
  return S.clients.filter((c) => f(c) && (!q || [c.display_name, c.name, c.gstin, c.login_id].some((v) => (v || '').toLowerCase().includes(q))));
}

function renderClients() {
  if (!S.init) return;
  $('chips').innerHTML = FILTERS.map(([k, label, fn]) =>
    `<button class="chip ${S.filter === k ? 'on' : ''}" data-filter="${k}">${label} ${S.clients.filter(fn).length}</button>`).join('');

  const list = shownClients();
  $('clientRows').innerHTML = list.map((c) => {
    const st = status(c);
    const sel = S.selected.has(c.gstin);
    const age = c.pwd_updated ? esc(c.pwd_updated) + (c.pwd_old ? ' <span class="badge b-warn">old</span>' : '') : '<span class="muted">—</span>';
    return `<tr class="${sel ? 'sel' : ''}">
      <td><input type="checkbox" data-g="${esc(c.gstin)}" ${sel ? 'checked' : ''} aria-label="Select ${esc(c.display_name)}"></td>
      <td class="name" title="${esc(c.name)}">${esc(c.display_name)}</td>
      <td class="mono small">${esc(c.gstin)}</td>
      <td title="${esc(c.email)}">${esc(c.email) || '<span class="muted">—</span>'}</td>
      <td>${esc(c.login_id)}</td>
      <td>${esc(c.filing)}</td>
      <td>${age}</td>
      <td><span class="badge ${st.cls}" title="${esc(st.text)}">${st.icon} ${esc(st.text)}</span></td>
      <td><button class="btn mini" data-edit="${esc(c.gstin)}">Edit</button></td></tr>`;
  }).join('');
  $('clientEmpty').hidden = list.length > 0;
  $('selectAll').checked = list.length > 0 && list.every((c) => S.selected.has(c.gstin));
  $('selCount').textContent = `${S.selected.size} selected`;
  $('shownCount').textContent = `Showing ${list.length} of ${S.clients.length}`;

  const issues = [];
  S.clients.forEach((c) => {
    if (c.blocked) issues.push([c, `Blocked: ${c.blocked_reason || 'last login failed'}`]);
    c.errors.forEach((e) => issues.push([c, e]));
    c.warnings.forEach((w) => issues.push([c, w]));
  });
  $('issues').hidden = issues.length === 0;
  if (issues.length) {
    $('issuesTitle').textContent = `${issues.length} issue${issues.length > 1 ? 's' : ''} found. Fix these before downloading.`;
    const top = issues.slice(0, 8).map(([c, m]) => `<button data-edit="${esc(c.gstin)}"><b>${esc(c.display_name)}</b> · ${esc(m)}</button>`);
    if (issues.length > 8) top.push(`<button data-filter="issues"><b>+ ${issues.length - 8} more</b> · show all</button>`);
    $('issuesList').innerHTML = top.join('');
  }
}

/* ------------------------------------------------------------ edit drawer */
function openEdit(gstin) {
  const c = gstin ? S.clients.find((x) => x.gstin === gstin) : null;
  S.editing = c ? c.gstin : '';
  S.showPwd = false;
  $('dTitle').textContent = c ? 'Edit client' : 'Add client';
  $('dGstin').value = c ? c.gstin : '';
  $('dGstin').disabled = !!c;
  $('dName').value = c ? c.name : '';
  $('dTrade').value = c ? c.trade_name : '';
  $('dLogin').value = c ? c.login_id : '';
  $('dPwd').value = '';
  $('dPwd').type = 'password';
  $('dShow').textContent = 'Show';
  $('dPwd').placeholder = c ? 'Leave blank to keep the current password' : 'Password';
  $('dPwdHint').textContent = c
    ? (c.pwd_updated ? `Last updated ${c.pwd_updated}. ` : '') + 'Symbols are saved exactly as typed.'
    : 'Symbols are saved exactly as typed.';
  $('dEmail').value = c ? c.email : '';
  $('dFiling').value = c && c.filing.toLowerCase().startsWith('q') ? 'Quarterly' : 'Monthly';
  $('dBlocked').hidden = !(c && c.blocked);
  $('dBlockedText').textContent = c && c.blocked
    ? `Blocked: ${c.blocked_reason.replace(/\.\s*$/, '')}. Saving a new password will unblock it.` : '';
  $('dError').hidden = true;
  $('drawer').hidden = $('drawerScrim').hidden = false;
  (c ? $('dPwd') : $('dGstin')).focus();
}
function closeEdit() { $('drawer').hidden = $('drawerScrim').hidden = true; S.editing = null; }

async function saveEdit() {
  const data = {
    gstin: $('dGstin').value.trim().toUpperCase(),
    name: $('dName').value.trim(),
    trade_name: $('dTrade').value.trim(),
    login_id: $('dLogin').value.trim(),
    password: $('dPwd').value,          // not trimmed on purpose
    email: $('dEmail').value.trim(),
    filing: $('dFiling').value,
  };
  if (!data.password) data.password = null;
  $('dSave').disabled = true;
  const r = await api('save_client', S.editing || '', data);
  $('dSave').disabled = false;
  if (!r.ok) { $('dError').textContent = r.error; $('dError').hidden = false; return; }
  applyInit(r);
  closeEdit();
  toast(`Saved ${data.name || data.gstin} to Excel`);
}

/* ------------------------------------------------------------ download */
function dlClients() {
  if (S.mode === 'A') {
    const c = S.clients.find((x) => x.gstin === S.client);
    return c ? [c] : [];
  }
  return S.clients.filter((c) => S.selected.has(c.gstin));
}
function lastAvailIn(fy) {
  const av = fyMonths(fy).filter(([y, m]) => isAvail(y, m));
  return av.length ? key(...av[av.length - 1]) : null;
}

function renderDownload() {
  if (!S.init) return;
  const cur = S.init.current_fy;
  $('dlFy').innerHTML = [cur, cur - 1, cur - 2].map((y) => `<option value="${y}" ${y === S.fy ? 'selected' : ''}>${fyLabel(y)}</option>`).join('');
  document.querySelectorAll('.mode').forEach((b) => b.classList.toggle('on', b.dataset.mode === S.mode));

  if (!S.client || !S.clients.some((c) => c.gstin === S.client)) {
    const first = S.clients.find((c) => S.selected.has(c.gstin) && isReady(c)) || S.clients.find(isReady) || S.clients[0];
    S.client = first ? first.gstin : null;
  }
  $('dlClient').innerHTML = S.clients.map((c) =>
    `<option value="${esc(c.gstin)}" ${c.gstin === S.client ? 'selected' : ''}>${esc(c.display_name)} (${esc(c.gstin)})${c.blocked ? ' - BLOCKED' : ''}</option>`).join('');
  $('fieldClient').hidden = S.mode !== 'A';
  $('fieldClients').hidden = S.mode !== 'B';
  $('dlClientsInfo').textContent = S.selected.size ? `${S.selected.size} selected on Clients tab` : 'None selected. Pick them on the Clients tab';

  if (S.mode === 'A' && S.months.size === 0) { const k = lastAvailIn(S.fy); if (k) S.months.add(k); }
  if (S.mode === 'B' && !S.single) S.single = lastAvailIn(S.fy);
  $('monthLabel').textContent = S.mode === 'A' ? 'Months (select one or more)' : 'Month (select one)';
  $('months').innerHTML = fyMonths(S.fy).map(([y, m]) => {
    const k = key(y, m);
    const on = S.mode === 'A' ? S.months.has(k) : S.single === k;
    return `<button class="month ${on ? 'on' : ''}" data-k="${k}" ${isAvail(y, m) ? '' : 'disabled'} title="${MON[m - 1]} ${y}">${MON[m - 1]}</button>`;
  }).join('');

  const f2b = $('f2b').checked, ex = $('f2bExcel').checked, js = $('f2bJson').checked;
  $('f2bExcel').disabled = $('f2bJson').disabled = !f2b;
  const perMonth = (f2b ? (+ex + +js) : 0) + (+$('f1').checked) + (+$('f3b').checked);
  const forms = [f2b && (ex || js) ? `2B (${[ex && 'Excel', js && 'JSON'].filter(Boolean).join(' + ')})` : '', $('f1').checked ? 'GSTR-1' : '', $('f3b').checked ? 'GSTR-3B' : ''].filter(Boolean);
  const months = S.mode === 'A' ? [...S.months].sort(periodSort) : (S.single ? [S.single] : []);
  const list = dlClients();
  const ok = list.filter(isReady);
  $('sumClients').textContent = S.mode === 'A' ? (list[0] ? list[0].display_name : '—') : String(list.length);
  $('sumMonths').textContent = months.length ? months.map((k) => { const [y, m] = unkey(k); return `${MON[m - 1]} ${y}`; }).join(', ') : '—';
  $('sumForms').textContent = forms.join(', ') || '—';
  $('sumFiles').textContent = String(ok.length * months.length * perMonth);
  $('sumCaptcha').textContent = String(ok.length);
  const skip = list.length - ok.length;
  $('sumSkip').hidden = skip === 0;
  $('sumSkip').textContent = skip ? `${skip} client(s) will be skipped (blocked or Excel issue)` : '';
  $('folderHint').textContent = 'Files are saved as …\\<Trade name>\\<FY>\\<Trade name> GSTR2B Oct 2026.xlsx';
  $('btnStart').disabled = !(ok.length && months.length && perMonth);
}

async function startDownload() {
  const months = S.mode === 'A' ? [...S.months].sort(periodSort) : [S.single];
  const list = dlClients().filter(isReady);
  const f2b = $('f2b').checked && ($('f2bExcel').checked || $('f2bJson').checked);
  const params = {
    gstins: list.map((c) => c.gstin),
    periods: months.map(unkey),
    forms: {
      GSTR2B: f2b ? { excel: $('f2bExcel').checked, json: $('f2bJson').checked } : false,
      GSTR1: $('f1').checked,
      GSTR3B: $('f3b').checked,
    },
    folder: $('dlFolder').value.trim(),
  };
  $('btnStart').disabled = true;
  const r = await api('start_job', params);
  $('btnStart').disabled = false;
  if (!r.ok) return fail(r);
  S.jobKey = '';
  show('status');
}

/* ------------------------------------------------------------ status */
const ST = {
  done: ['b-ok', '✓ Downloaded'], failed: ['b-bad', '✕ Failed'], blocked: ['b-bad', '✕ Blocked'],
  notavail: ['b-warn', '! Not available'], skipped: ['b-grey', '– Skipped'], manual: ['b-warn', '! Needs you'],
  running: ['b-info', '⟳ Downloading'], waiting: ['b-info', '⏳ Login'], pending: ['b-grey', '○ Pending'],
};

async function poll() {
  if (S.polling) return;
  S.polling = true;
  try {
    const r = await api('get_status');
    if (r.ok) handleJob(r.job);
  } finally { S.polling = false; }
}

function handleJob(job) {
  S.job = job;
  $('runDot').hidden = !(job && job.running);
  $('statusEmpty').hidden = !!job;
  $('statusBody').hidden = !job;
  if (!job) return;

  const c = job.counts;
  const n = (k) => c[k] || 0;
  const total = job.rows.length;
  const pend = n('pending') + n('running') + n('waiting');
  $('cDone').textContent = n('done');
  $('cBlocked').textContent = n('blocked');
  $('cAttn').textContent = n('failed') + n('manual') + n('notavail') + n('skipped');
  $('cPending').textContent = pend;
  $('progressBar').style.width = total ? `${Math.round(100 * (total - pend) / total)}%` : '0';
  $('jobTitle').textContent = (job.running ? 'Downloading · ' : 'Finished · ') + job.title;
  $('jobSub').textContent = `${total - pend} of ${total} items done` + (job.paused ? ' · Paused' : '') + (job.stopping ? ' · Stopping…' : '');
  $('btnPause').textContent = job.paused ? 'Resume' : 'Pause';
  $('btnPause').disabled = $('btnStop').disabled = !job.running;
  $('btnRetry').disabled = job.running;

  const k = JSON.stringify(job.rows.map((r) => [r.id, r.status, r.note]));
  if (k !== S.jobKey) {
    S.jobKey = k;
    $('statusRows').innerHTML = job.rows.map((r) => {
      const [cls, label] = ST[r.status] || ['b-grey', r.status];
      let act = '';
      if (r.status === 'done' && r.files.length) act = `<button class="btn mini" data-open="${esc(r.files[0])}">Open</button>`;
      if (r.status === 'manual') act = `<button class="btn mini" data-showprompt="1">Show</button>`;
      return `<tr><td class="name">${esc(r.client)}</td><td>${esc(r.period)}</td><td>${esc(r.form_label)}</td>
        <td><span class="badge ${cls}">${label}</span></td><td class="note">${esc(r.note)}</td><td>${act}</td></tr>`;
    }).join('');
  }

  const p = job.prompt;
  if (p && p.id !== S.promptId) openPrompt(p);
  if (!p && S.promptId !== null) {
    S.promptId = null;
    hideModal('captchaModal');
    hideModal('manualModal');
  }
}

function openPrompt(p) {
  S.promptId = p.id;
  if (p.type === 'captcha') {
    $('cpIndex').textContent = `CLIENT ${p.index} OF ${p.total}`;
    $('cpAttempt').textContent = `Captcha attempt ${p.attempt} of ${p.max}`;
    $('cpClient').textContent = p.client;
    $('cpGstin').textContent = p.gstin;
    $('cpError').hidden = !p.error;
    $('cpError').textContent = p.error || '';
    $('cpImg').hidden = !p.image;
    $('cpNoImg').hidden = !!p.image;
    if (p.image) $('cpImg').src = p.image;
    $('cpNext').textContent = p.next ? `Next: ${p.next} · ${p.total - p.index} remaining` : 'Last client in this run';
    $('cpInput').value = '';
    setCaptchaBusy(false);
    showModal('captchaModal');
    setTimeout(() => $('cpInput').focus(), 50);
  } else if (p.type === 'manual') {
    $('mnClient').textContent = p.client;
    $('mnWhat').textContent = `${p.form} · ${p.period}`;
    $('mnReason').textContent = `Could not do it automatically: ${p.reason}`;
    $('mnNeed').textContent = p.need > 1 ? `Waiting for ${p.need} files (Excel and JSON).` : 'Waiting for 1 file.';
    showModal('manualModal');
  }
}
function setCaptchaBusy(b) {
  ['cpLogin', 'cpSkip', 'cpRefresh', 'cpInput'].forEach((id) => { $(id).disabled = b; });
  $('cpLogin').textContent = b ? 'Checking…' : 'Login (Enter ↵)';
}
async function answer(ans) {
  const id = S.promptId;
  if (id === null) return;
  const r = await api('respond_prompt', id, ans);
  if (!r.ok) toast('That prompt has already closed', true);
  poll();
}
async function captchaLogin() {
  const text = $('cpInput').value.trim();
  if (!text) { $('cpInput').focus(); return; }
  setCaptchaBusy(true);
  await answer({ action: 'submit', text });
}

/* ------------------------------------------------------------ email */
const EST = { ready: ['b-info', 'Ready'], sent: ['b-ok', 'Sent ✓'], skipped: ['b-grey', 'Skipped'], noemail: ['b-warn', 'No email'] };

async function loadEmail() {
  const r = await api('email_list');
  if (!r.ok) return fail(r);
  S.emailItems = r.items;
  $('sender').textContent = r.sender;
  $('emailEmpty').hidden = r.items.length > 0;
  $('emailBody').hidden = r.items.length === 0;
  const cnt = (s) => r.items.filter((i) => i.status === s).length;
  $('emailCounts').innerHTML = r.items.length
    ? `<b class="dark">${cnt('ready')} ready</b> · ${cnt('sent')} sent · ${cnt('skipped')} skipped · ${cnt('noemail')} no email` : '';
  if (!r.items.some((i) => i.gstin === S.emailSel)) {
    const first = r.items.find((i) => i.status === 'ready') || r.items[0];
    S.emailSel = first ? first.gstin : null;
  }
  renderEmailList();
  if (S.emailSel) previewEmail(S.emailSel);
}
function renderEmailList() {
  $('emailList').innerHTML = S.emailItems.map((i) => {
    const [cls, label] = EST[i.status] || ['b-grey', i.status];
    return `<button class="list-item ${i.gstin === S.emailSel ? 'on' : ''}" data-mail="${esc(i.gstin)}">
      <span><b>${esc(i.name)}</b><small>${esc(i.summary)}</small></span><span class="badge ${cls}">${label}</span></button>`;
  }).join('');
  const remaining = S.emailItems.filter((i) => i.status === 'ready').length;
  $('btnSendAll').textContent = `Send all remaining (${remaining})`;
  $('btnSendAll').disabled = remaining === 0;
}
async function previewEmail(gstin) {
  S.emailSel = gstin;
  renderEmailList();
  const p = await api('email_preview', gstin);
  if (!p.ok) return fail(p);
  $('mTo').value = p.to;
  $('mCc').value = p.cc;
  $('mSubject').value = p.subject;
  $('mBody').value = p.body;
  $('mAttach').innerHTML = p.attachment_names.map((n) => `<span class="att">📎 ${esc(n)}</span>`).join('') +
    (p.too_big ? `<span class="badge b-bad">${p.size_mb} MB · too big for Gmail</span>` : `<span class="muted small">${p.size_mb} MB</span>`);
  $('btnSendMail').textContent = p.status === 'sent' ? 'Send again' : 'Send';
}
function nextReady() {
  const n = S.emailItems.find((i) => i.status === 'ready' && i.gstin !== S.emailSel);
  return n ? n.gstin : S.emailSel;
}
async function sendCurrent() {
  const g = S.emailSel;
  if (!g) return;
  if (!$('mTo').value.trim()) return toast('Enter an email address in To', true);
  $('btnSendMail').disabled = true;
  $('btnSendMail').textContent = 'Sending…';
  const r = await api('send_email', g, $('mTo').value, $('mCc').value, $('mSubject').value, $('mBody').value);
  $('btnSendMail').disabled = false;
  if (!r.ok) { $('btnSendMail').textContent = 'Send'; return fail(r); }
  toast(`Sent to ${$('mTo').value}`);
  S.emailSel = nextReady();
  loadEmail();
}
async function sendAll() {
  const items = S.emailItems.filter((i) => i.status === 'ready');
  if (!items.length) return;
  const names = items.slice(0, 12).map((i) => '• ' + i.name).join('\n') + (items.length > 12 ? `\n…and ${items.length - 12} more` : '');
  if (!(await confirmBox(`Send ${items.length} emails?`, `Each client gets the standard message with their files:\n\n${names}`, `Send ${items.length}`))) return;
  let sent = 0, failed = [];
  for (const i of items) {
    toast(`Sending ${sent + failed.length + 1} of ${items.length}: ${i.name}`);
    const p = await api('email_preview', i.gstin);
    if (!p.ok) { failed.push(`${i.name}: ${p.error}`); continue; }
    const r = await api('send_email', i.gstin, p.to, p.cc, p.subject, p.body);
    if (r.ok) sent++; else failed.push(`${i.name}: ${r.error}`);
  }
  if (failed.length) toast(`Sent ${sent}. Failed ${failed.length}:\n${failed.slice(0, 5).join('\n')}`, true);
  else toast(`All ${sent} emails sent`);
  loadEmail();
}

/* ------------------------------------------------------------ settings */
async function loadSettings() {
  const s = await api('get_settings');
  if (!s.ok) return fail(s);
  $('sFirm').value = s.firm_name; $('sPhone').value = s.firm_phone;
  $('sDay').value = s.send_by_day; $('sAge').value = s.pwd_warn_days;
  $('sSender').value = s.sender_email; $('sSenderName').value = s.sender_name; $('sCc').value = s.cc;
  $('sSmtp').value = s.smtp_server; $('sPort').value = s.smtp_port;
  $('sAppPwd').value = '';
  $('sAppPwd').placeholder = s.has_password ? 'Saved (type to change)' : '16-letter app password';
  $('t2bSub').value = s.templates.gstr2b.subject; $('t2bBody').value = s.templates.gstr2b.body;
  $('tRetSub').value = s.templates.returns.subject; $('tRetBody').value = s.templates.returns.body;
}
async function saveSettings() {
  const r = await api('save_settings', {
    firm_name: $('sFirm').value, firm_phone: $('sPhone').value, send_by_day: $('sDay').value,
    pwd_warn_days: $('sAge').value, sender_email: $('sSender').value, sender_name: $('sSenderName').value,
    cc: $('sCc').value, smtp_server: $('sSmtp').value, smtp_port: $('sPort').value, app_password: $('sAppPwd').value,
    templates: {
      gstr2b: { subject: $('t2bSub').value, body: $('t2bBody').value },
      returns: { subject: $('tRetSub').value, body: $('tRetBody').value },
    },
  });
  if (!r.ok) return fail(r);
  toast('Settings saved');
  $('firmName').textContent = $('sFirm').value;
  loadSettings();
}

/* ------------------------------------------------------------ events */
function wire() {
  document.querySelectorAll('.nav').forEach((b) => b.addEventListener('click', () => show(b.dataset.tab)));
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-go],[data-filter],[data-edit],[data-open],[data-showprompt],[data-mail],[data-k],[data-mode]');
    if (!t) return;
    if (t.dataset.go) show(t.dataset.go);
    else if (t.dataset.filter) { S.filter = t.dataset.filter; renderClients(); }
    else if (t.dataset.edit !== undefined) openEdit(t.dataset.edit);
    else if (t.dataset.open) api('open_path', t.dataset.open);
    else if (t.dataset.showprompt && S.job && S.job.prompt) openPrompt(S.job.prompt);
    else if (t.dataset.mail) previewEmail(t.dataset.mail);
    else if (t.dataset.k) {
      const k = t.dataset.k;
      if (S.mode === 'A') { S.months.has(k) ? S.months.delete(k) : S.months.add(k); } else S.single = k;
      renderDownload();
    } else if (t.dataset.mode) { S.mode = t.dataset.mode; renderDownload(); }
  });

  // clients
  $('search').addEventListener('input', (e) => { S.search = e.target.value; renderClients(); });
  $('clientRows').addEventListener('change', (e) => {
    const g = e.target.dataset.g;
    if (!g) return;
    e.target.checked ? S.selected.add(g) : S.selected.delete(g);
    renderClients();
  });
  $('selectAll').addEventListener('change', (e) => {
    shownClients().forEach((c) => (e.target.checked ? S.selected.add(c.gstin) : S.selected.delete(c.gstin)));
    renderClients();
  });
  $('btnSelectReady').addEventListener('click', () => { S.clients.filter(isReady).forEach((c) => S.selected.add(c.gstin)); renderClients(); });
  $('btnReload').addEventListener('click', async () => { applyInit(await api('reload_clients')); toast('Client list reloaded'); });
  $('btnChangeExcel').addEventListener('click', async () => { const r = await api('choose_excel'); if (!r.cancelled) applyInit(r); });
  $('btnOpenExcel').addEventListener('click', async () => { const r = await api('open_excel'); if (!r.ok) fail(r); });
  $('btnAddClient').addEventListener('click', () => openEdit(''));
  $('btnToDownload').addEventListener('click', () => {
    if (S.selected.size === 1) { S.mode = 'A'; S.client = [...S.selected][0]; }
    else if (S.selected.size > 1) S.mode = 'B';
    show('download');
  });

  // drawer
  $('dClose').addEventListener('click', closeEdit);
  $('dCancel').addEventListener('click', closeEdit);
  $('drawerScrim').addEventListener('click', closeEdit);
  $('dSave').addEventListener('click', saveEdit);
  $('dShow').addEventListener('click', () => {
    S.showPwd = !S.showPwd;
    $('dPwd').type = S.showPwd ? 'text' : 'password';
    $('dShow').textContent = S.showPwd ? 'Hide' : 'Show';
  });
  $('dUnblock').addEventListener('click', async () => {
    if (!S.editing) return;
    if (!(await confirmBox('Unblock without a new password?', 'Only do this if you are sure the password in Excel is correct (for example, the client confirmed it). A wrong attempt counts towards the portal lock.', 'Unblock'))) return;
    const r = await api('unblock', S.editing);
    applyInit(r);
    $('dBlocked').hidden = true;
    toast('Client unblocked');
  });

  // download
  $('dlFy').addEventListener('change', (e) => { S.fy = Number(e.target.value); S.months.clear(); S.single = null; renderDownload(); });
  $('dlClient').addEventListener('change', (e) => { S.client = e.target.value; renderDownload(); });
  $('dlChangeClients').addEventListener('click', () => show('clients'));
  ['f2b', 'f2bExcel', 'f2bJson', 'f1', 'f3b'].forEach((id) => $(id).addEventListener('change', renderDownload));
  $('btnBrowse').addEventListener('click', async () => { const r = await api('choose_folder'); if (r.ok) $('dlFolder').value = r.path; });
  $('dlFolder').addEventListener('change', async (e) => { const r = await api('set_download_folder', e.target.value); if (!r.ok) fail(r); });
  $('btnStart').addEventListener('click', startDownload);

  // status
  $('btnPause').addEventListener('click', () => api('pause', !(S.job && S.job.paused)).then(poll));
  $('btnStop').addEventListener('click', async () => {
    if (await confirmBox('Stop the run?', 'The current step finishes, then the rest is skipped.', 'Stop')) api('stop_job').then(poll);
  });
  $('btnRetry').addEventListener('click', async () => { const r = await api('retry_failed'); if (!r.ok) fail(r); else { S.jobKey = ''; poll(); } });
  $('btnOpenFolder').addEventListener('click', () => api('open_download_folder'));
  $('btnReport').addEventListener('click', async () => { const r = await api('export_report'); r.ok ? toast('Report saved:\n' + r.path) : fail(r); });

  // captcha / manual
  $('cpInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') captchaLogin(); });
  $('cpLogin').addEventListener('click', captchaLogin);
  $('cpRefresh').addEventListener('click', () => { setCaptchaBusy(true); answer({ action: 'refresh' }); });
  $('cpSkip').addEventListener('click', () => { setCaptchaBusy(true); answer({ action: 'skip' }); });
  $('cpStopAll').addEventListener('click', async () => {
    const id = S.promptId;
    if (!(await confirmBox('Stop the whole run?', 'This client and all remaining clients will be skipped.', 'Stop'))) { if (S.promptId === id && S.job && S.job.prompt) openPrompt(S.job.prompt); return; }
    S.promptId = id;
    await answer({ action: 'stop' });
    api('stop_job');
  });
  $('mnDone').addEventListener('click', () => answer({ action: 'done' }));
  $('mnRetry').addEventListener('click', () => answer({ action: 'retry' }));
  $('mnSkip').addEventListener('click', () => answer({ action: 'skip' }));

  // email
  $('btnSendMail').addEventListener('click', sendCurrent);
  $('btnSkipMail').addEventListener('click', async () => { if (!S.emailSel) return; await api('skip_email', S.emailSel); S.emailSel = nextReady(); loadEmail(); });
  $('btnSendAll').addEventListener('click', sendAll);

  // settings
  $('btnSaveSettings').addEventListener('click', saveSettings);
  $('btnTestMail').addEventListener('click', async () => {
    toast('Sending test email…');
    const r = await api('test_email');
    if (r.ok) { toast(`Test email sent to ${r.to} (port ${r.port})`); loadSettings(); } else fail(r);
  });
}

/* ------------------------------------------------------------ start */
let started = false;
async function start() {
  if (started) return;
  started = true;
  wire();
  applyInit(await api('get_init'));
  setInterval(() => { if (S.tab === 'status' || (S.job && S.job.running)) poll(); }, 800);
  poll();
}
window.addEventListener('pywebviewready', start);
if (window.pywebview && window.pywebview.api) start();
