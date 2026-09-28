/* ABC Private Limited - Travel & Expense Management (PWA front-end) */
'use strict';

/* ================================================================== */
/* Utilities                                                          */
/* ================================================================== */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (s) => (s === null || s === undefined ? '' : String(s)).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const inr = (n) => (n === null || n === undefined || n === '' ? '—' : '₹' + Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 }));
const fmtDate = (d) => { if (!d) return '—'; const x = new Date(d.length === 10 ? d + 'T00:00:00' : d); return x.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }); };
const fmtDT = (d) => (d ? new Date(d).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');
const today = () => { const d = new Date(); d.setMinutes(d.getMinutes() - d.getTimezoneOffset()); return d.toISOString().slice(0, 10); };
const daysBetween = (a, b) => Math.round((new Date(b + 'T00:00:00Z') - new Date(a + 'T00:00:00Z')) / 86400000);
const opt = (vals, sel) => vals.map((v) => { const [val, lab] = Array.isArray(v) ? v : [v, v]; return `<option value="${esc(val)}" ${String(sel) === String(val) ? 'selected' : ''}>${esc(lab)}</option>`; }).join('');

const state = { token: null, user: null, meta: null, unread: 0, entitlement: null, deferredPrompt: null };
try { state.token = localStorage.getItem('abc_token'); } catch { /* storage unavailable */ }

function toast(msg, type = '') {
  const t = document.createElement('div');
  t.className = 'toast ' + type; t.textContent = msg;
  $('#toasts').appendChild(t);
  setTimeout(() => t.remove(), type === 'error' ? 6000 : 3500);
}

async function api(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  let res;
  try { res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined }); } catch (e) { throw new Error('Cannot reach the server. Check your connection.'); }
  let data = {};
  try { data = await res.json(); } catch { /* not json */ }
  if (res.status === 401 && !path.startsWith('/api/auth/')) { logoutLocal(); throw new Error(data.error || 'Session expired. Please log in again.'); }
  if (!res.ok) throw new Error(data.error || 'Request failed (' + res.status + ')');
  return data;
}
function fileUrl(path) { return path + (path.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(state.token || ''); }

function logoutLocal() {
  state.token = null; state.user = null;
  const tw = document.getElementById('toasts'); if (tw) tw.innerHTML = '';
  try { localStorage.removeItem('abc_token'); } catch { /* ignore */ }
  location.hash = '#/login';
}

function readFileB64(file) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(',')[1]);
    r.onerror = reject;
    r.readAsDataURL(file);
  });
}
async function uploadFiles(reqId, files, kind, itemId) {
  let n = 0;
  for (const f of files) {
    if (f.size > 5 * 1024 * 1024) { toast(`${f.name}: larger than 5 MB`, 'error'); continue; }
    const data = await readFileB64(f);
    const r = await api(`/api/requests/${reqId}/attachments`, { method: 'POST', body: { name: f.name, mime: f.type || 'application/octet-stream', data, kind, item_id: itemId } });
    if (r.duplicate_of) toast(`Warning: ${f.name} was already uploaded earlier (${r.duplicate_of}). Flagged as possible duplicate.`, 'error');
    n++;
  }
  return n;
}

function modal(title, html, { wide } = {}) {
  const bg = document.createElement('div');
  bg.className = 'modal-bg';
  bg.innerHTML = `<div class="modal" role="dialog" aria-modal="true" style="${wide ? 'max-width:960px' : ''}"><h2>${esc(title)}<button class="btn sm" data-close aria-label="Close">✕</button></h2><div class="modal-body">${html}</div></div>`;
  document.body.appendChild(bg);
  const close = () => bg.remove();
  bg.addEventListener('click', (e) => { if (e.target === bg || e.target.closest('[data-close]')) close(); });
  return { el: bg, close };
}

const STAGE_CHIP = {
  DRAFT: 'grey', PENDING_BH: '', PENDING_MD: '', SENT_BACK: 'warn', PENDING_BOOKING: '', BOOKED: 'good',
  CLAIM_PENDING_BH: '', CLAIM_PENDING_HR: '', CLAIM_SENT_BACK: 'warn', CLAIM_PENDING_ACCOUNTS: '', PAID: 'good', REJECTED: 'critical', CANCELLED: 'grey',
};
const stageChip = (stage, label) => `<span class="chip ${STAGE_CHIP[stage] || ''}">${esc(label || (state.meta && state.meta.stages[stage] ? state.meta.stages[stage].label : stage))}</span>`;
const SEV_LABEL = { critical: '⛔ Critical', serious: '⚠ Serious', warning: '△ Warning' };
const EXC_LABEL = {
  LATE_BOOKING: 'Late booking', HOTEL_ABOVE_GRADE: 'Hotel above grade', HOTEL_RATE: 'Hotel rate over limit', FLIGHT_ABOVE_GRADE: 'Flight class above grade',
  LONG_TRIP: 'Long trip', OVER_BUDGET: 'Over budget', MISSING_BILLS: 'Missing bills', FOOD_OVER_DA: 'Food over DA', DUPLICATE_BILL: 'Duplicate bill',
  DATE_OUTSIDE_TRIP: 'Date outside trip', LATE_CLAIM: 'Late claim', CLAIM_OVERDUE: 'Claim overdue',
};
const WF = () => state.meta.workflow_roles;
const isAdmin = () => state.user && state.user.is_admin;
const isWorkflowRole = () => state.user && Object.values(WF()).includes(state.user.role);

/* ================================================================== */
/* Icons                                                              */
/* ================================================================== */
const I = {
  home: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1z"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>',
  plane: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 16l20-7-3-2-7 2-5-5H5l3 6-4 1-2-2H1l1 4z"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 11l3 3 8-8"/><path d="M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9"/></svg>',
  chart: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M7 15v3M12 10v8M17 6v12"/></svg>',
  list: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="8" r="4"/><path d="M1 21v-1a6 6 0 0 1 12 0v1M16 3.1a4 4 0 0 1 0 7.8M23 21v-1a6 6 0 0 0-4-5.7"/></svg>',
  cog: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>',
  bell: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0"/></svg>',
  book: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20V3H6.5A2.5 2.5 0 0 0 4 5.5z"/><path d="M4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5"/></svg>',
  bulb: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18h6M10 22h4M12 2a7 7 0 0 0-4 12.7V17h8v-2.3A7 7 0 0 0 12 2z"/></svg>',
  user: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a8 8 0 0 1 16 0v1"/></svg>',
  download: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M12 3v12M7 10l5 5 5-5M5 21h14"/></svg>',
  menu: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><path d="M3 6h18M3 12h18M3 18h18"/></svg>',
  logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
  wallet: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="6" width="20" height="14" rx="2"/><path d="M2 10h20M16 15h2"/></svg>',
};

/* ================================================================== */
/* PWA install                                                        */
/* ================================================================== */
const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  state.deferredPrompt = e;
  $$('.btn-install').forEach((b) => b.classList.remove('hidden'));
});
window.addEventListener('appinstalled', () => {
  state.deferredPrompt = null;
  $$('.btn-install').forEach((b) => b.classList.add('hidden'));
  toast('ABC Travel app installed successfully!', 'success');
});
async function installApp() {
  if (state.deferredPrompt) {
    state.deferredPrompt.prompt();
    const { outcome } = await state.deferredPrompt.userChoice;
    if (outcome === 'accepted') toast('Installing ABC Travel…', 'success');
    state.deferredPrompt = null;
    return;
  }
  const ua = navigator.userAgent;
  const ios = /iphone|ipad|ipod/i.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  const secure = window.isSecureContext;
  modal('Install ABC Travel App', `
    ${!secure ? '<div class="alert warn">Installation needs a secure connection (HTTPS) or <b>localhost</b>. Ask IT to publish the app over HTTPS for mobile installation.</div>' : ''}
    ${ios ? `<p><b>iPhone / iPad (Safari):</b></p><ol><li>Tap the <b>Share</b> button (square with arrow) in Safari.</li><li>Scroll and tap <b>Add to Home Screen</b>.</li><li>Tap <b>Add</b>. The ABC Travel icon appears on your home screen.</li></ol>` : `
    <p><b>Desktop (Chrome / Edge):</b> click the <b>Install</b> icon (⊕ / computer with arrow) at the right end of the address bar, or open the browser menu <b>⋮ → Cast, save and share → Install page as app…</b> (Edge: <b>… → Apps → Install this site as an app</b>).</p>
    <p><b>Android (Chrome):</b> tap <b>⋮</b> menu → <b>Add to Home screen</b> / <b>Install app</b>.</p>`}
    <p class="muted small">If the app is already installed, open it from your Start menu, dock or home screen.</p>`);
}
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch((e) => console.warn('SW registration failed', e)); });
}
window.addEventListener('online', () => { const b = $('#offline'); if (b) b.classList.add('hidden'); });
window.addEventListener('offline', () => { const b = $('#offline'); if (b) b.classList.remove('hidden'); });

/* ================================================================== */
/* Auth screens                                                       */
/* ================================================================== */
async function renderAuth(mode = 'login') {
  let status = { has_users: true, company: 'ABC Private Limited' };
  try { status = await api('/api/auth/status'); } catch (e) { /* offline */ }
  if (!status.has_users) mode = 'signup';
  $('#app').innerHTML = `
  <div class="auth-wrap">
    <div class="auth-card">
      <div class="brand"><img src="/icons/icon-192.png" alt=""><div><h1 style="margin:0">${esc(status.company)}</h1><div class="muted">Travel &amp; Expense Management</div></div></div>
      <div class="tabs" role="tablist">
        <button data-tab="login" class="${mode === 'login' ? 'active' : ''}">Login</button>
        <button data-tab="signup" class="${mode === 'signup' ? 'active' : ''}">Sign Up</button>
      </div>
      ${!status.has_users ? '<div class="alert info">No users yet. <b>The first person to sign up becomes the Administrator.</b></div>' : ''}
      <form id="loginForm" class="${mode === 'login' ? '' : 'hidden'}" autocomplete="on">
        <div class="field"><label for="le">Email id</label><input id="le" type="email" name="email" required autocomplete="username" placeholder="name@abc.com"></div>
        <div class="field"><label for="lp">Password</label><input id="lp" type="password" name="password" required autocomplete="current-password"></div>
        <button class="btn primary" style="width:100%">Login</button>
      </form>
      <form id="signupForm" class="${mode === 'signup' ? '' : 'hidden'}" autocomplete="on">
        <div class="field"><label for="sn">Full name</label><input id="sn" name="name" ${!status.has_users ? 'required' : ''} placeholder="${status.has_users ? 'Optional - as registered by Admin' : 'Your name'}"></div>
        <div class="field"><label for="se">Email id</label><input id="se" type="email" name="email" required autocomplete="username" placeholder="${status.has_users ? 'Email id added by your Admin' : 'admin@abc.com'}"></div>
        <div class="field"><label for="sp">Password</label><input id="sp" type="password" name="password" required minlength="8" autocomplete="new-password"><span class="hint">Min 8 characters with letters and numbers.</span></div>
        <div class="field"><label for="sp2">Confirm password</label><input id="sp2" type="password" name="password2" required autocomplete="new-password"></div>
        <button class="btn primary" style="width:100%">Sign Up</button>
        ${status.has_users ? '<p class="muted small">Only employees whose email id has been added by the Admin can sign up.</p>' : ''}
      </form>
      <div id="authMsg"></div>
      <div class="auth-foot"><span>© ${new Date().getFullYear()} ${esc(status.company)}</span>
        <button class="btn sm btn-install-auth" type="button">${I.download} Install App</button></div>
    </div>
  </div>`;
  $$('.tabs button').forEach((b) => b.onclick = () => renderAuth(b.dataset.tab));
  $('.btn-install-auth').onclick = installApp;
  const msg = (t, cls) => { $('#authMsg').innerHTML = `<div class="alert ${cls}">${esc(t)}</div>`; };
  $('#loginForm').onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    try {
      const r = await api('/api/auth/login', { method: 'POST', body: { email: f.get('email'), password: f.get('password') } });
      state.token = r.token;
      try { localStorage.setItem('abc_token', r.token); } catch { /* ignore */ }
      await boot(true);
    } catch (err) { msg(err.message, 'error'); }
  };
  $('#signupForm').onsubmit = async (e) => {
    e.preventDefault();
    const f = new FormData(e.target);
    if (f.get('password') !== f.get('password2')) return msg('Passwords do not match.', 'error');
    try {
      const r = await api('/api/auth/signup', { method: 'POST', body: { name: f.get('name'), email: f.get('email'), password: f.get('password') } });
      await renderAuth('login');
      $('#le').value = f.get('email');
      msg(r.message, 'good');
    } catch (err) { msg(err.message, 'error'); }
  };
}

/* ================================================================== */
/* Shell                                                              */
/* ================================================================== */
function navItems() {
  const u = state.user; const wf = WF();
  const items = [
    ['sec', 'My Travel'],
    ['#/dashboard', I.home, 'Dashboard'],
    ['#/new', I.plus, 'New Travel Request'],
    ['#/requests', I.plane, 'My Trips & Claims'],
  ];
  if (isWorkflowRole() || isAdmin()) {
    const label = u.role === wf.TA ? 'Booking Desk' : u.role === wf.AC ? 'Accounts Desk' : 'Pending Approvals';
    items.push(['sec', 'Work Queue'], ['#/approvals', I.check, label, 'approvals']);
  }
  if (isAdmin()) {
    items.push(['sec', 'Administration'], ['#/analytics', I.chart, 'Analytics Dashboard'], ['#/all', I.list, 'All Requests'],
      ['#/employees', I.users, 'Employees'], ['#/settings', I.cog, 'Policy & Settings'], ['#/logs', I.lock, 'Sign-in / Sign-up Log']);
  }
  items.push(['sec', 'More'], ['#/policy', I.book, 'Travel Policy'], ['#/features', I.bulb, 'Feature Board'], ['#/profile', I.user, 'My Profile']);
  return items;
}
function renderShell() {
  const u = state.user;
  $('#app').innerHTML = `
  <div id="offline" class="offline-bar ${navigator.onLine ? 'hidden' : ''}">You are offline - changes cannot be saved until you reconnect.</div>
  <header class="topbar">
    <button class="icon menu-toggle" id="menuBtn" aria-label="Menu">${I.menu}</button>
    <a class="logo" href="#/dashboard"><img src="/icons/icon-192.png" alt=""><div><span class="full">${esc(state.meta.settings.company_name)}</span><small>Travel &amp; Expense</small></div></a>
    <div class="spacer"></div>
    <button class="btn-install ${isStandalone() ? 'hidden' : ''}" id="installBtn" title="Install app">${I.download}<span class="lbl">Install App</span></button>
    <button class="icon" id="bellBtn" aria-label="Notifications" title="Notifications">${I.bell}<span class="badge-dot ${state.unread ? '' : 'hidden'}" id="bellCount">${state.unread}</span></button>
    <div class="user-chip"><b>${esc(u.name)}</b><span>${esc(u.is_admin ? (u.role === 'Admin' ? 'Administrator' : u.role + ' · Admin') : u.role)}</span></div>
    <button class="icon" id="logoutBtn" aria-label="Logout" title="Logout">${I.logout}</button>
  </header>
  <div class="layout">
    <nav class="sidebar" id="sidebar">${navItems().map((n) => n[0] === 'sec' ? `<div class="sec">${esc(n[1])}</div>` : `<a href="${n[0]}" data-route="${n[0]}">${n[1]}<span>${esc(n[2])}</span>${n[3] ? '<span class="count hidden" id="navCount"></span>' : ''}</a>`).join('')}</nav>
    <main class="main" id="main"></main>
  </div>`;
  $('#installBtn').onclick = installApp;
  $('#bellBtn').onclick = () => { location.hash = '#/notifications'; };
  $('#logoutBtn').onclick = async () => { try { await api('/api/auth/logout', { method: 'POST' }); } catch { /* ignore */ } logoutLocal(); };
  $('#menuBtn').onclick = () => $('#sidebar').classList.toggle('open');
  $('#sidebar').addEventListener('click', (e) => { if (e.target.closest('a')) $('#sidebar').classList.remove('open'); });
  refreshCounts();
}
async function refreshCounts() {
  try {
    const me = await api('/api/me');
    state.unread = me.unread;
    const b = $('#bellCount'); if (b) { b.textContent = me.unread; b.classList.toggle('hidden', !me.unread); }
    if ($('#navCount')) {
      const d = await api('/api/dashboard');
      $('#navCount').textContent = d.approvals_waiting; $('#navCount').classList.toggle('hidden', !d.approvals_waiting);
    }
  } catch { /* ignore */ }
}

/* ================================================================== */
/* Router                                                             */
/* ================================================================== */
const ROUTES = {
  dashboard: pageDashboard, new: pageNewRequest, edit: pageNewRequest, requests: pageMyRequests, request: pageRequest,
  approvals: pageApprovals, analytics: pageAnalytics, all: pageAllRequests, employees: pageEmployees, settings: pageSettings,
  logs: pageLogs, notifications: pageNotifications, features: pageFeatures, profile: pageProfile, policy: pagePolicy,
};
async function router() {
  const hash = location.hash || '#/dashboard';
  const [, name, arg] = hash.split('/');
  if (!state.user) { if (name === 'signup') return renderAuth('signup'); return renderAuth('login'); }
  if (!$('#main')) renderShell();
  const fn = ROUTES[name] || pageDashboard;
  $$('#sidebar a').forEach((a) => a.classList.toggle('active', a.dataset.route === '#/' + (name === 'edit' ? 'requests' : name)));
  const main = $('#main');
  main.innerHTML = '<div class="empty">Loading…</div>';
  window.scrollTo(0, 0);
  try { await fn(main, arg); } catch (e) { main.innerHTML = `<div class="alert error">${esc(e.message)}</div>`; }
}
window.addEventListener('hashchange', router);

async function boot(fromLogin) {
  if (!state.token) { state.user = null; return router(); }
  try {
    const me = await api('/api/me');
    state.user = me.user; state.unread = me.unread; state.entitlement = me.entitlement;
    state.meta = await api('/api/meta');
    $('#app').innerHTML = '';
    if (fromLogin || /login|signup/.test(location.hash) || !location.hash) location.hash = '#/dashboard';
    renderShell();
    router();
  } catch (e) {
    state.user = null;
    renderAuth('login');
  }
}

/* ================================================================== */
/* Dashboard                                                          */
/* ================================================================== */
async function pageDashboard(main) {
  const d = await api('/api/dashboard');
  const u = state.user; const e = state.entitlement || {};
  const minDays = state.meta.settings.min_advance_days;
  main.innerHTML = `
    <div class="page-head"><div><h1>Welcome, ${esc(u.name.split(' ')[0])}</h1><p>${esc(u.role)}${u.department ? ' · ' + esc(u.department) : ''} · ${esc(u.email)}</p></div>
      <a class="btn primary" href="#/new">${I.plus} New Travel Request</a></div>
    <div class="kpis">
      <div class="kpi"><div class="label">My trips</div><div class="value">${d.total_trips}</div><div class="sub">submitted to date</div></div>
      <div class="kpi"><div class="label">My requests in approval</div><div class="value">${d.pending_mine}</div><div class="sub">awaiting others</div></div>
      ${isWorkflowRole() || isAdmin() ? `<div class="kpi ${d.approvals_waiting ? 'alert' : ''}"><div class="label">Waiting for my action</div><div class="value">${d.approvals_waiting}</div><div class="sub"><a href="#/approvals">Open work queue →</a></div></div>` : ''}
      <div class="kpi"><div class="label">Claims in process</div><div class="value">${inr(d.in_process)}</div><div class="sub">with approvers / accounts</div></div>
      <div class="kpi"><div class="label">Reimbursed</div><div class="value">${inr(d.reimbursed)}</div><div class="sub">net paid to me</div></div>
      <div class="kpi"><div class="label">My avg. planning lead</div><div class="value">${d.avg_lead_days === null ? '—' : d.avg_lead_days + ' d'}</div><div class="sub">policy: ${minDays}+ days ahead</div></div>
    </div>
    ${d.to_claim.length ? `<div class="alert warn"><b>Action needed:</b> submit your expense statement with bills for ${d.to_claim.map((t) => `<a href="#/request/${t.id}">${esc(t.ref_no)} (${esc(t.from_city)} → ${esc(t.to_city)})</a>`).join(', ')}.</div>` : ''}
    <div class="grid g2">
      <div class="card"><h3>Upcoming trips</h3>
        ${d.upcoming.length ? `<ul class="list-plain">${d.upcoming.map((t) => `<li><div><a href="#/request/${t.id}"><b>${esc(t.from_city)} → ${esc(t.to_city)}</b></a><div class="small muted">${esc(t.ref_no)} · ${fmtDate(t.depart_date)} – ${fmtDate(t.return_date)}${t.pnr ? ' · ' + esc(t.airline) + ' PNR ' + esc(t.pnr) : ''}</div></div>${stageChip(t.stage)}</li>`).join('')}</ul>` : '<div class="empty">No upcoming trips. <a href="#/new">Plan one well in advance</a> for cheaper fares.</div>'}
      </div>
      <div class="card"><h3>My travel entitlement <span class="chip">${esc(u.role)}</span></h3>
        <dl class="kv">
          <dt>Flight class</dt><dd>${esc(e.flight_class)}</dd>
          <dt>Hotel category</dt><dd>${esc(e.hotel_category)} (up to ${inr(e.hotel_max_per_night)}/night)</dd>
          <dt>Food / DA per day</dt><dd>${inr(e.da_per_day)}</dd>
          <dt>Local conveyance / day</dt><dd>${inr(e.local_per_day)}</dd>
          <dt>Advance planning</dt><dd>Raise request at least <b>${minDays} days</b> before travel</dd>
        </dl>
        <p class="small muted" style="margin-top:10px">As per ${esc(state.meta.settings.company_name)} Matrix of Authority. <a href="#/policy">View full policy</a></p>
      </div>
    </div>
    <div class="card"><h3>How the travel workflow works</h3>${workflowDiagram()}</div>`;
}

function workflowDiagram() {
  const steps = [
    ['1', 'Employee', 'Pre-travel request: route, days, estimate (flight, hotel, food, misc), purpose'],
    ['2', 'Business Head', 'Approves / sends back / rejects; can revise budget'],
    ['3', 'Managing Director', 'Final pre-travel approval'],
    ['4', 'Travel Assistant', 'Books flight & hotel as per Matrix of Authority (3/4/5 Star)'],
    ['5', 'Employee', 'Travels; submits expense statement with bills attached'],
    ['6', 'Business Head', 'Verifies claim, can edit approved amount per line'],
    ['7', 'HR Head', 'Final approval of expense statement'],
    ['8', 'Accountant', 'Accounting voucher, advance adjustment, payment'],
  ];
  return `<div class="stepper">${steps.map((s) => `<div class="step done"><div class="dot">${s[0]}</div><b>${esc(s[1])}</b><div class="small" style="padding:0 4px">${esc(s[2])}</div></div>`).join('')}</div>`;
}

/* ================================================================== */
/* New / Edit request                                                 */
/* ================================================================== */
const CITIES = ['Mumbai', 'Delhi', 'Bengaluru', 'Chennai', 'Hyderabad', 'Kolkata', 'Pune', 'Ahmedabad', 'Jaipur', 'Kochi', 'Goa', 'Lucknow', 'Chandigarh', 'Indore', 'Nagpur', 'Coimbatore', 'Bhubaneswar', 'Guwahati',
  'Dubai', 'Singapore', 'London', 'New York', 'Frankfurt', 'Tokyo', 'Hong Kong', 'Sydney', 'Paris', 'Doha'];

async function pageNewRequest(main, editId) {
  const s = state.meta.settings; const e = state.entitlement;
  let r = {
    trip_type: 'Domestic', from_city: state.user.base_city || '', to_city: '', depart_date: '', return_date: '', purpose: '', client_name: '', cost_center: '',
    est_flight: '', est_hotel: '', est_food: '', est_local: '', est_misc: '', advance_requested: '', preferred_airline: '', preferred_time: '',
    flight_class_requested: e.flight_class, hotel_category_requested: e.hotel_category, late_justification: '',
  };
  if (editId) {
    r = await api('/api/requests/' + editId);
    if (!r.can_edit) { main.innerHTML = '<div class="alert error">This request can no longer be edited.</div>'; return; }
  }
  const minDate = today();
  main.innerHTML = `
  <div class="page-head"><div><h1>${editId ? 'Edit Travel Request ' + esc(r.ref_no) : 'New Pre-Travel Approval Request'}</h1>
    <p>Goes to Business Head → Managing Director → Travel Assistant for booking.</p></div></div>
  ${r.stage === 'SENT_BACK' ? `<div class="alert warn"><b>Sent back for correction:</b> ${esc((r.history.filter((h) => h.action === 'SEND_BACK').pop() || {}).comment)}</div>` : ''}
  <form id="reqForm">
    <div class="card"><h3>Trip details</h3>
      <div class="form-grid">
        <div class="field"><label>Trip type</label><select name="trip_type">${opt(s.features.international_travel ? ['Domestic', 'International'] : ['Domestic'], r.trip_type)}</select></div>
        <div class="field"><label>From city *</label><input name="from_city" list="cities" required value="${esc(r.from_city)}"></div>
        <div class="field"><label>To city *</label><input name="to_city" list="cities" required value="${esc(r.to_city)}"></div>
        <div class="field"><label>Departure date *</label><input type="date" name="depart_date" required min="${minDate}" value="${esc(r.depart_date)}"></div>
        <div class="field"><label>Return date *</label><input type="date" name="return_date" required min="${minDate}" value="${esc(r.return_date)}"></div>
        <div class="field"><label>Duration</label><input id="daysOut" readonly value="—"></div>
        <div class="field full"><label>Purpose of travel *</label><textarea name="purpose" required placeholder="e.g. Client meeting with XYZ Ltd for annual contract renewal; product demo">${esc(r.purpose)}</textarea></div>
        <div class="field"><label>Client / Customer</label><input name="client_name" value="${esc(r.client_name)}"></div>
        <div class="field"><label>Cost center / Project</label><input name="cost_center" value="${esc(r.cost_center)}" placeholder="e.g. SALES-WEST"></div>
      </div>
      <datalist id="cities">${CITIES.map((c) => `<option value="${c}">`).join('')}</datalist>
      <div id="leadBox" class="lead-meter" style="margin-top:12px"></div>
      <div class="field full hidden" id="lateBox" style="margin-top:10px"><label>Justification for late planning *</label><textarea name="late_justification" placeholder="Why could this trip not be planned ${s.min_advance_days} days in advance?">${esc(r.late_justification)}</textarea></div>
    </div>
    <div class="card"><h3>Travel preferences <span class="small muted">Your entitlement: ${esc(e.flight_class)} · ${esc(e.hotel_category)} up to ${inr(e.hotel_max_per_night)}/night</span></h3>
      <div class="form-grid">
        <div class="field"><label>Preferred airline</label><select name="preferred_airline"><option value="">No preference</option>${opt(s.airlines, r.preferred_airline)}</select></div>
        <div class="field"><label>Preferred time</label><select name="preferred_time">${opt(['', 'Early morning (before 8am)', 'Morning (8am-12pm)', 'Afternoon (12-5pm)', 'Evening (after 5pm)'], r.preferred_time)}</select></div>
        <div class="field"><label>Flight class</label><select name="flight_class_requested">${opt(state.meta.flight_classes, r.flight_class_requested)}</select></div>
        <div class="field"><label>Hotel category</label><select name="hotel_category_requested">${opt(state.meta.hotel_categories, r.hotel_category_requested)}</select></div>
      </div>
      <div id="gradeWarn"></div>
    </div>
    <div class="card"><h3>Approximate cost estimate (₹) <button type="button" class="btn sm" id="autoFill">Auto-fill from policy</button></h3>
      <div class="form-grid">
        <div class="field"><label>Flight cost</label><input type="number" min="0" step="1" name="est_flight" value="${esc(r.est_flight)}"></div>
        <div class="field"><label>Hotel stay</label><input type="number" min="0" step="1" name="est_hotel" value="${esc(r.est_hotel)}"></div>
        <div class="field"><label>Food</label><input type="number" min="0" step="1" name="est_food" value="${esc(r.est_food)}"></div>
        <div class="field"><label>Local conveyance</label><input type="number" min="0" step="1" name="est_local" value="${esc(r.est_local)}"></div>
        <div class="field"><label>Miscellaneous</label><input type="number" min="0" step="1" name="est_misc" value="${esc(r.est_misc)}"></div>
        ${s.features.travel_advance ? `<div class="field"><label>Travel advance required</label><input type="number" min="0" step="1" name="advance_requested" value="${esc(r.advance_requested)}"><span class="hint">Adjusted against final claim</span></div>` : ''}
      </div>
      <p style="margin:12px 0 0">Approximate total: <span class="pill-total" id="estTotal">₹0</span></p>
    </div>
    <div class="actions">
      <button class="btn" type="submit" data-submit="0">Save as draft</button>
      <button class="btn primary" type="submit" data-submit="1">Submit for approval</button>
      <a class="btn" href="${editId ? '#/request/' + editId : '#/requests'}">Cancel</a>
    </div>
  </form>`;
  const form = $('#reqForm');
  const val = (n) => form.elements[n] ? form.elements[n].value : '';
  const HR = { '2 Star': 2, '3 Star': 3, '4 Star': 4, '5 Star': 5 }; const FR = { Economy: 1, 'Premium Economy': 2, Business: 3, First: 4 };
  function update() {
    const dd = val('depart_date'), rd = val('return_date');
    let days = 0;
    if (dd && rd && rd >= dd) { days = daysBetween(dd, rd) + 1; $('#daysOut').value = `${days} day(s), ${days - 1} night(s)`; } else $('#daysOut').value = '—';
    if (dd) {
      const lead = daysBetween(today(), dd);
      const ok = lead >= s.min_advance_days;
      $('#leadBox').className = 'lead-meter alert ' + (ok ? 'good' : lead < 3 ? 'error' : 'warn');
      $('#leadBox').innerHTML = ok ? `✔ Planned <b>${lead} days</b> in advance - meets the ${s.min_advance_days}-day advance booking policy. Early booking gets cheaper fares.` :
        `⚠ Only <b>${lead} day(s)</b> before travel. Policy requires ${s.min_advance_days} days so that flight tickets are cheaper. This will be flagged as an exception.`;
      $('#lateBox').classList.toggle('hidden', ok || !s.features.late_booking_justification);
    } else { $('#leadBox').className = 'lead-meter alert info'; $('#leadBox').innerHTML = `Tip: plan at least <b>${s.min_advance_days} days</b> ahead - airfares are usually much cheaper when booked early.`; }
    const tot = ['est_flight', 'est_hotel', 'est_food', 'est_local', 'est_misc'].reduce((a, k) => a + (Number(val(k)) || 0), 0);
    $('#estTotal').textContent = inr(tot);
    const warn = [];
    if (HR[val('hotel_category_requested')] > HR[e.hotel_category]) warn.push(`${val('hotel_category_requested')} hotel is above your entitlement (${e.hotel_category}).`);
    if (FR[val('flight_class_requested')] > FR[e.flight_class]) warn.push(`${val('flight_class_requested')} class is above your entitlement (${e.flight_class}).`);
    $('#gradeWarn').innerHTML = warn.length ? `<div class="alert warn">${warn.map(esc).join('<br>')} It will be flagged for approvers.</div>` : '';
    return days;
  }
  form.addEventListener('input', update); form.addEventListener('change', update); update();
  $('#autoFill').onclick = () => {
    const days = update();
    if (!days) return toast('Select travel dates first.', 'error');
    const intl = val('trip_type') === 'International';
    if (!Number(val('est_flight'))) form.elements.est_flight.value = intl ? 45000 : 9000;
    form.elements.est_hotel.value = Math.max(0, days - 1) * e.hotel_max_per_night;
    form.elements.est_food.value = days * e.da_per_day;
    form.elements.est_local.value = days * e.local_per_day;
    if (!Number(val('est_misc'))) form.elements.est_misc.value = 1000;
    update();
    toast('Estimates filled from your entitlement. Adjust as needed.');
  };
  let submitFlag = false;
  $$('button[type=submit]', form).forEach((b) => b.addEventListener('click', () => { submitFlag = b.dataset.submit === '1'; }));
  form.onsubmit = async (ev) => {
    ev.preventDefault();
    const body = Object.fromEntries(new FormData(form).entries());
    body.submit = submitFlag;
    try {
      if (editId) { await api('/api/requests/' + editId, { method: 'PUT', body }); toast(submitFlag ? 'Request submitted for approval.' : 'Changes saved.', 'success'); location.hash = '#/request/' + editId; }
      else { const res = await api('/api/requests', { method: 'POST', body }); toast(`${res.ref_no} ${submitFlag ? 'submitted for approval' : 'saved as draft'}.`, 'success'); location.hash = '#/request/' + res.id; }
    } catch (err) { toast(err.message, 'error'); }
  };
}

/* ================================================================== */
/* Lists                                                              */
/* ================================================================== */
function requestTable(rows, { showEmp = false, empty = 'No requests yet.' } = {}) {
  if (!rows.length) return `<div class="empty">${empty}</div>`;
  return `<div class="table-wrap"><table><thead><tr><th>Ref no.</th>${showEmp ? '<th>Employee</th>' : ''}<th>Route</th><th>Travel dates</th><th class="num">Estimate</th><th class="num">Claim</th><th>Status</th><th>Flags</th></tr></thead><tbody>
  ${rows.map((r) => `<tr class="clickable" data-href="#/request/${r.id}"><td><a href="#/request/${r.id}">${esc(r.ref_no)}</a><div class="small muted">${esc(r.trip_type)}</div></td>
    ${showEmp ? `<td>${esc(r.employee_name)}<div class="small muted">${esc(r.employee_role)}</div></td>` : ''}
    <td>${esc(r.from_city)} → ${esc(r.to_city)}<div class="small muted">${esc((r.purpose || '').slice(0, 50))}</div></td>
    <td class="nowrap">${fmtDate(r.depart_date)}<div class="small muted">${r.days} day(s) · lead ${r.lead_days ?? '—'}d</div></td>
    <td class="num">${inr(r.approved_amount || r.est_total)}</td><td class="num">${r.claim_total ? inr(r.claim_approved || r.claim_total) : '—'}</td>
    <td>${stageChip(r.stage, r.stage_label)}</td>
    <td>${(r.exceptions || []).map((x) => `<span class="chip warn" title="${esc(x)}">${esc(EXC_LABEL[x] || x)}</span>`).join(' ')}</td></tr>`).join('')}
  </tbody></table></div>`;
}
function bindRowClicks(root) { $$('tr.clickable', root).forEach((tr) => tr.addEventListener('click', (e) => { if (!e.target.closest('a,button,input')) location.hash = tr.dataset.href; })); }

async function pageMyRequests(main) {
  const rows = await api('/api/requests?scope=mine');
  main.innerHTML = `<div class="page-head"><div><h1>My Trips &amp; Claims</h1><p>View, edit pending requests, submit expense statements with bills.</p></div><a class="btn primary" href="#/new">${I.plus} New Request</a></div>
    <div class="filters"><div class="field"><label>Status</label><select id="fStage"><option value="">All</option><option value="open">In approval / active</option><option value="edit">Editable (draft / sent back)</option><option value="claim">Expense statement due</option><option value="closed">Closed</option></select></div>
    <div class="field"><label>Search</label><input id="fQ" placeholder="City, ref no., purpose"></div></div>
    <div class="card" id="list"></div>`;
  const draw = () => {
    const st = $('#fStage').value, q = $('#fQ').value.toLowerCase();
    const f = rows.filter((r) => (!st || (st === 'open' && /PENDING|BOOKED/.test(r.stage)) || (st === 'edit' && ['DRAFT', 'SENT_BACK', 'CLAIM_SENT_BACK'].includes(r.stage)) ||
      (st === 'claim' && ['BOOKED', 'CLAIM_SENT_BACK'].includes(r.stage)) || (st === 'closed' && ['PAID', 'REJECTED', 'CANCELLED'].includes(r.stage))) &&
      (!q || `${r.ref_no} ${r.from_city} ${r.to_city} ${r.purpose}`.toLowerCase().includes(q)));
    $('#list').innerHTML = requestTable(f, { empty: 'No requests found. <a href="#/new">Create your first travel request</a>.' });
    bindRowClicks($('#list'));
  };
  $('#fStage').onchange = draw; $('#fQ').oninput = draw; draw();
}

async function pageAllRequests(main) {
  const rows = await api('/api/requests?scope=all');
  const stages = state.meta.stages;
  main.innerHTML = `<div class="page-head"><div><h1>All Travel Requests</h1><p>Company-wide register (Admin only).</p></div>
    <a class="btn" href="${fileUrl('/api/export/requests.csv')}">${I.download} Export CSV</a></div>
    <div class="filters"><div class="field"><label>Stage</label><select id="fStage"><option value="">All stages</option>${Object.entries(stages).map(([k, v]) => `<option value="${k}">${esc(v.label)}</option>`).join('')}</select></div>
    <div class="field"><label>Search</label><input id="fQ" placeholder="Employee, city, ref no."></div>
    <div class="field"><label>Only with exceptions</label><select id="fEx"><option value="">No</option><option value="1">Yes</option></select></div></div>
    <div class="card" id="list"></div>`;
  const draw = () => {
    const st = $('#fStage').value, q = $('#fQ').value.toLowerCase(), ex = $('#fEx').value;
    const f = rows.filter((r) => (!st || r.stage === st) && (!ex || r.exceptions.length) && (!q || `${r.ref_no} ${r.employee_name} ${r.from_city} ${r.to_city}`.toLowerCase().includes(q)));
    $('#list').innerHTML = `<p class="small muted">${f.length} request(s)</p>` + requestTable(f, { showEmp: true });
    bindRowClicks($('#list'));
  };
  ['fStage', 'fQ', 'fEx'].forEach((id) => { $('#' + id).oninput = draw; $('#' + id).onchange = draw; }); draw();
}

async function pageApprovals(main) {
  const [rows, done] = await Promise.all([api('/api/requests?scope=approvals'), api('/api/requests?scope=processed')]);
  const u = state.user; const wf = WF();
  const title = u.role === wf.TA ? 'Booking Desk' : u.role === wf.AC ? 'Accounts Desk' : 'Pending Approvals';
  const sub = u.role === wf.TA ? 'MD-approved trips waiting for flight & hotel booking as per Matrix of Authority.' :
    u.role === wf.AC ? 'HR-approved expense statements waiting for accounting and payment. Record travel advances too.' :
      'Requests waiting at your stage. Open a request to review, edit amounts, approve, send back or reject.';
  main.innerHTML = `<div class="page-head"><div><h1>${title}</h1><p>${sub}${isAdmin() && !isWorkflowRole() ? ' As Admin you can act on any stage (logged as Admin override).' : ''}</p></div></div>
    <div class="tabs"><button class="active" data-t="p">Waiting for me (${rows.length})</button><button data-t="d">Processed by me (${done.length})</button></div>
    <div class="card" id="list"></div>`;
  const draw = (t) => {
    $$('.tabs button').forEach((b) => b.classList.toggle('active', b.dataset.t === t));
    $('#list').innerHTML = requestTable(t === 'p' ? rows : done, { showEmp: true, empty: t === 'p' ? '🎉 Nothing pending. You are all caught up.' : 'Nothing processed yet.' });
    bindRowClicks($('#list'));
  };
  $$('.tabs button').forEach((b) => b.onclick = () => draw(b.dataset.t)); draw('p');
  if (u.role === wf.AC || isAdmin()) {
    const adv = await api('/api/requests?scope=advances');
    if (adv.length) main.insertAdjacentHTML('beforeend', `<div class="card"><h3>Travel advances to disburse</h3>${requestTable(adv, { showEmp: true })}</div>`);
    bindRowClicks(main);
  }
}

/* ================================================================== */
/* Request detail (workflow)                                          */
/* ================================================================== */
const FLOW = [
  ['SUBMIT', 'Submitted'], ['PENDING_BH', 'Business Head'], ['PENDING_MD', 'Managing Director'], ['PENDING_BOOKING', 'Booking'],
  ['BOOKED', 'Travel'], ['CLAIM_PENDING_BH', 'Claim: BH'], ['CLAIM_PENDING_HR', 'Claim: HR'], ['CLAIM_PENDING_ACCOUNTS', 'Accounts'], ['PAID', 'Paid'],
];
function stepper(r) {
  const order = FLOW.map((f) => f[0]);
  let cur = r.stage;
  if (cur === 'DRAFT') cur = 'SUBMIT';
  if (cur === 'SENT_BACK') cur = 'SUBMIT';
  if (cur === 'CLAIM_SENT_BACK') cur = 'BOOKED';
  let idx = order.indexOf(cur);
  let bad = false;
  if (['REJECTED', 'CANCELLED'].includes(r.stage)) {
    const last = [...r.history].reverse().find((h) => ['REJECT', 'CANCEL'].includes(h.action));
    idx = last ? Math.max(0, order.indexOf(last.from_stage)) : 0; bad = true;
  }
  const skipped = (k) => (k === 'PENDING_BH' && ['Business Head', 'Managing Director'].includes(r.employee_role)) || (k === 'PENDING_MD' && r.employee_role === 'Managing Director') ||
    (k === 'CLAIM_PENDING_BH' && ['Business Head', 'Managing Director'].includes(r.employee_role));
  return `<div class="stepper">${FLOW.map(([k, lab], i) => {
    const cls = r.stage === 'PAID' ? 'done' : i < idx ? 'done' : i === idx ? (bad ? 'bad' : (r.stage === 'DRAFT' ? '' : 'current')) : '';
    return `<div class="step ${cls}"><div class="dot">${cls === 'done' ? '✓' : cls === 'bad' ? '✕' : i + 1}</div>${esc(lab)}${skipped(k) ? '<div class="small">(skipped)</div>' : ''}</div>`;
  }).join('')}</div>`;
}

function attachmentList(r, itemId, canDelete) {
  const list = r.attachments.filter((a) => (itemId === undefined ? !a.item_id : a.item_id === itemId));
  if (!list.length) return itemId === undefined ? '<span class="muted small">No documents attached.</span>' : '<span class="chip critical">No bill</span>';
  return list.map((a) => `<span class="nowrap"><a href="${fileUrl('/api/attachments/' + a.id)}" target="_blank" rel="noopener">📎 ${esc(a.original_name)}</a>${a.kind !== 'BILL' ? ` <span class="chip grey">${esc(a.kind.replace('_', ' '))}</span>` : ''}${canDelete ? ` <button class="btn sm" data-del-att="${a.id}" title="Remove">✕</button>` : ''}</span>`).join('<br>');
}

async function pageRequest(main, id) {
  const r = await api('/api/requests/' + id);
  const s = state.meta.settings; const u = state.user; const wf = WF();
  const st = r.stage;
  const ent = r.entitlement;
  const est = [['Flight', r.est_flight], ['Hotel', r.est_hotel], ['Food', r.est_food], ['Local conveyance', r.est_local], ['Miscellaneous', r.est_misc]];
  const inClaimReview = r.can_act && ['CLAIM_PENDING_BH', 'CLAIM_PENDING_HR'].includes(st);
  const showClaim = r.items.length || r.can_claim;
  main.innerHTML = `
  <div class="page-head"><div><h1>${esc(r.ref_no)} · ${esc(r.from_city)} → ${esc(r.to_city)}</h1>
    <p>${esc(r.employee_name)} (${esc(r.employee_role)}${r.emp_code ? ', ' + esc(r.emp_code) : ''}) · ${esc(r.trip_type)} · ${fmtDate(r.depart_date)} – ${fmtDate(r.return_date)} (${r.days} day${r.days > 1 ? 's' : ''})</p></div>
    <div class="actions" style="margin:0">${stageChip(st, r.stage_label)}
      ${r.can_edit ? `<a class="btn" href="#/edit/${r.id}">✎ Edit request</a>` : ''}
      ${r.can_cancel ? '<button class="btn" id="cancelBtn">Cancel request</button>' : ''}
      <button class="btn" onclick="window.print()">🖨 Print</button></div></div>
  <div class="print-only"><h2>${esc(s.company_name)} - Travel &amp; Expense Statement</h2></div>
  <div class="card no-print">${stepper(r)}</div>
  ${r.exceptions.length ? `<div class="card"><h3>Policy exceptions flagged (${r.exceptions.length})</h3>${r.exceptions.map((x) => `<div class="flag ${x.severity}"><b class="nowrap">${SEV_LABEL[x.severity]}</b><span>${esc(x.message)}</span></div>`).join('')}</div>` : ''}
  <div id="actionPanel"></div>
  <div class="grid g2">
    <div class="card"><h3>Pre-travel request</h3>
      <dl class="kv">
        <dt>Purpose</dt><dd>${esc(r.purpose)}</dd>
        ${r.client_name ? `<dt>Client</dt><dd>${esc(r.client_name)}</dd>` : ''}
        ${r.cost_center ? `<dt>Cost center</dt><dd>${esc(r.cost_center)}</dd>` : ''}
        <dt>Planned</dt><dd>${r.lead_days ?? '—'} day(s) before travel ${r.lead_days !== null && r.lead_days < s.min_advance_days ? '<span class="chip warn">Late</span>' : '<span class="chip good">On time</span>'}</dd>
        ${r.late_justification ? `<dt>Late reason</dt><dd>${esc(r.late_justification)}</dd>` : ''}
        <dt>Preference</dt><dd>${esc(r.preferred_airline || 'Any airline')} · ${esc(r.preferred_time || 'Any time')} · ${esc(r.flight_class_requested)} · ${esc(r.hotel_category_requested)}</dd>
        <dt>Entitlement</dt><dd>${esc(ent.flight_class)} · ${esc(ent.hotel_category)} ≤ ${inr(ent.hotel_max_per_night)}/night · DA ${inr(ent.da_per_day)}/day</dd>
        <dt>Business Head</dt><dd>${esc(r.bh_name || 'Any Business Head')}</dd>
        <dt>Submitted</dt><dd>${fmtDT(r.submitted_at)}</dd>
      </dl>
    </div>
    <div class="card"><h3>Approximate cost estimate</h3>
      <div class="table-wrap"><table><tbody>${est.map(([k, v]) => `<tr><td>${k}</td><td class="num">${inr(v)}</td></tr>`).join('')}
        <tr><td><b>Estimated total</b></td><td class="num"><b>${inr(r.est_total)}</b></td></tr>
        ${r.approved_amount ? `<tr><td><b>Approved budget</b></td><td class="num"><b>${inr(r.approved_amount)}</b></td></tr>` : ''}
        ${r.advance_requested ? `<tr><td>Advance requested / paid</td><td class="num">${inr(r.advance_requested)} / ${inr(r.advance_paid || 0)}</td></tr>` : ''}
      </tbody></table></div>
    </div>
  </div>
  ${r.booked_at ? `<div class="card"><h3>Booking details <span class="small muted">Booked ${fmtDT(r.booked_at)}</span></h3>
    <div class="grid g2"><dl class="kv"><dt>Airline</dt><dd>${esc(r.airline || '—')} ${esc(r.flight_no || '')}${r.return_flight_no ? ' / return ' + esc(r.return_flight_no) : ''}</dd><dt>PNR</dt><dd>${esc(r.pnr || '—')}</dd>
      <dt>Class</dt><dd>${esc(r.flight_class || '—')}</dd><dt>Timing</dt><dd>${esc(r.onward_time || '—')}</dd><dt>Ticket cost</dt><dd>${inr(r.ticket_cost)}</dd></dl>
    <dl class="kv"><dt>Hotel</dt><dd>${esc(r.hotel_name || '—')}</dd><dt>Category</dt><dd>${esc(r.hotel_category || '—')}</dd><dt>Nights × rate</dt><dd>${r.hotel_nights || 0} × ${inr(r.hotel_rate)} = ${inr(r.hotel_cost)}</dd>
      <dt>Booking ref</dt><dd>${esc(r.booking_ref || '—')}</dd>${r.booking_notes ? `<dt>Notes</dt><dd>${esc(r.booking_notes)}</dd>` : ''}</dl></div>
    <div style="margin-top:8px">${attachmentList(r, undefined, false)}</div></div>` : ''}
  ${showClaim ? `<div class="card" id="claimCard"><h3>Expense statement ${r.claim_submitted_at ? `<span class="small muted">Submitted ${fmtDT(r.claim_submitted_at)}</span>` : ''}</h3>
    ${r.can_claim ? `<div class="alert info">Add each expense with its bill (PDF/JPG/PNG, max 5 MB). Bills are mandatory above ${inr(s.bill_required_above)}. Flight & hotel booked by the company need not be claimed again.</div>` : ''}
    <div class="table-wrap"><table><thead><tr><th>Date</th><th>Category</th><th>Description / vendor</th><th>Bill no.</th><th class="num">Amount</th><th class="num">INR</th>${r.claim_submitted_at || inClaimReview ? '<th class="num">Approved</th>' : ''}<th>Bill</th>${r.can_claim ? '<th></th>' : ''}</tr></thead>
    <tbody>${r.items.map((i) => `<tr><td class="nowrap">${fmtDate(i.exp_date)}</td><td>${esc(i.category)}</td><td>${esc(i.description)}<div class="small muted">${esc(i.vendor)}</div></td><td>${esc(i.bill_no)}</td>
      <td class="num">${i.currency !== 'INR' ? esc(i.currency) + ' ' + i.amount + '<div class="small muted">@' + i.fx_rate + '</div>' : inr(i.amount)}</td><td class="num">${inr(i.amount_inr)}</td>
      ${r.claim_submitted_at || inClaimReview ? `<td class="num">${inClaimReview ? `<input type="number" min="0" max="${i.amount_inr}" step="0.01" data-appr="${i.id}" value="${i.approved_inr ?? i.amount_inr}" style="width:110px"><input data-note="${i.id}" placeholder="Note" value="${esc(i.approver_note || '')}" style="width:110px;margin-top:4px">` : inr(i.approved_inr ?? i.amount_inr) + (i.approver_note ? `<div class="small muted">${esc(i.approver_note)}</div>` : '')}</td>` : ''}
      <td>${attachmentList(r, i.id, r.can_claim)}${r.can_claim ? `<div><label class="btn sm" style="margin-top:4px">📎 Attach<input type="file" accept="application/pdf,image/*" multiple hidden data-up-item="${i.id}"></label></div>` : ''}</td>
      ${r.can_claim ? `<td><button class="btn sm" data-del-item="${i.id}">Delete</button></td>` : ''}</tr>`).join('') || '<tr><td colspan="9" class="empty">No expenses added yet.</td></tr>'}</tbody>
    <tfoot><tr><td colspan="5"><b>Total claimed</b></td><td class="num"><b>${inr(r.claim_total || 0)}</b></td>${r.claim_submitted_at || inClaimReview ? `<td class="num"><b id="apprTotal">${inr(r.claim_approved ?? r.claim_total)}</b></td>` : ''}<td colspan="2"></td></tr></tfoot></table></div>
    ${r.claim_notes ? `<p class="small"><b>Employee remarks:</b> ${esc(r.claim_notes)}</p>` : ''}
    ${r.can_claim ? expenseForm(r) : ''}
    ${(r.claim_total || 0) > 0 ? `<p class="small muted">Approved budget ${inr(r.approved_amount || r.est_total)} · Company-paid tickets ${inr(r.ticket_cost || 0)} · Hotel ${inr(r.hotel_cost || 0)} · Advance paid ${inr(r.advance_paid || 0)}</p>` : ''}
  </div>` : ''}
  ${r.paid_at ? `<div class="card"><h3>Accounting &amp; payment</h3><dl class="kv"><dt>Voucher no.</dt><dd>${esc(r.voucher_no)}</dd><dt>GL code / cost center</dt><dd>${esc(r.gl_code || '—')} / ${esc(r.cost_center || '—')}</dd>
    <dt>Claim approved</dt><dd>${inr(r.claim_approved)}</dd><dt>Less: advance</dt><dd>${inr(r.advance_paid || 0)}</dd><dt>Net ${r.net_payable >= 0 ? 'paid to employee' : 'recoverable'}</dt><dd><b>${inr(Math.abs(r.net_payable))}</b></dd>
    <dt>Payment</dt><dd>${esc(r.payment_mode)} ${esc(r.payment_ref || '')} on ${fmtDate(r.payment_date)}</dd>${r.accounting_notes ? `<dt>Notes</dt><dd>${esc(r.accounting_notes)}</dd>` : ''}</dl></div>` : ''}
  <div class="card"><h3>Approval history &amp; audit trail</h3><ul class="timeline">${r.history.map((h) => `<li><b>${esc(h.action.replace(/_/g, ' '))}</b> by ${esc(h.actor_name)} <span class="muted">(${esc(h.actor_role)})</span>
    ${h.to_stage && h.from_stage !== h.to_stage ? ` → ${esc(state.meta.stages[h.to_stage] ? state.meta.stages[h.to_stage].label : h.to_stage)}` : ''}${h.comment ? `<div>“${esc(h.comment)}”</div>` : ''}<div class="when">${fmtDT(h.created_at)}</div></li>`).join('')}</ul></div>`;

  // ---------- action panel -------------
  const panel = $('#actionPanel');
  const act = async (action, extra = {}) => {
    try { await api(`/api/requests/${r.id}/action`, { method: 'POST', body: { action, ...extra } }); toast('Done.', 'success'); refreshCounts(); pageRequest(main, id); }
    catch (e) { toast(e.message, 'error'); }
  };
  if (r.can_act && ['PENDING_BH', 'PENDING_MD'].includes(st)) {
    panel.innerHTML = `<div class="card" style="border-left:4px solid var(--brand-2)"><h3>Your approval - ${esc(r.stage_label)}</h3>
      <div class="form-grid"><div class="field"><label>Approved budget (₹) - edit if required</label><input type="number" id="apAmt" min="1" value="${r.approved_amount || r.est_total}"></div>
      <div class="field full"><label>Comments</label><textarea id="apCmt" placeholder="Remarks (mandatory for send back / reject)"></textarea></div></div>
      <div class="actions"><button class="btn success" id="apOk">✔ Approve</button><button class="btn warn" id="apBack">↩ Send back for correction</button><button class="btn danger" id="apRej">✕ Reject</button></div></div>`;
    $('#apOk').onclick = () => act('APPROVE', { approved_amount: $('#apAmt').value, comment: $('#apCmt').value });
    $('#apBack').onclick = () => act('SEND_BACK', { comment: $('#apCmt').value });
    $('#apRej').onclick = () => act('REJECT', { comment: $('#apCmt').value });
  } else if (r.can_act && st === 'PENDING_BOOKING') {
    const nights = Math.max(0, r.days - 1);
    panel.innerHTML = `<div class="card" style="border-left:4px solid var(--brand-2)"><h3>Book flight &amp; hotel <span class="small muted">Matrix of Authority for ${esc(r.employee_role)}: ${esc(ent.flight_class)} · ${esc(ent.hotel_category)} ≤ ${inr(ent.hotel_max_per_night)}/night</span></h3>
      <div class="alert info">Requested: ${esc(r.preferred_airline || 'any airline')}, ${esc(r.preferred_time || 'any time')}, ${esc(r.flight_class_requested)}, ${esc(r.hotel_category_requested)} hotel. Book the lowest logical fare.</div>
      <form id="bookForm"><div class="form-grid">
        <div class="field"><label>Airline</label><select name="airline"><option value="">— No flight —</option>${opt(s.airlines, r.preferred_airline)}</select></div>
        <div class="field"><label>Flight no. (onward)</label><input name="flight_no" placeholder="6E 2134"></div>
        <div class="field"><label>Flight no. (return)</label><input name="return_flight_no"></div>
        <div class="field"><label>PNR</label><input name="pnr"></div>
        <div class="field"><label>Class</label><select name="flight_class">${opt(state.meta.flight_classes, ent.flight_class)}</select></div>
        <div class="field"><label>Departure time</label><input name="onward_time" placeholder="07:10"></div>
        <div class="field"><label>Ticket cost (₹, return)</label><input type="number" min="0" name="ticket_cost"></div>
        <div class="field"><label>Hotel name</label><input name="hotel_name"></div>
        <div class="field"><label>Hotel category</label><select name="hotel_category">${opt(state.meta.hotel_categories, ent.hotel_category)}</select></div>
        <div class="field"><label>Nights</label><input type="number" min="0" name="hotel_nights" value="${nights}"></div>
        <div class="field"><label>Rate per night (₹)</label><input type="number" min="0" name="hotel_rate"></div>
        <div class="field"><label>Booking reference</label><input name="booking_ref"></div>
        <div class="field full"><label>Booking notes / justification (mandatory if above entitlement)</label><textarea name="comment"></textarea></div>
        <div class="field full"><label>Attach e-ticket / hotel voucher</label><input type="file" name="files" multiple accept="application/pdf,image/*"></div>
      </div><div id="bookWarn"></div>
      <div class="actions"><button class="btn success">✔ Confirm booking</button><button type="button" class="btn warn" id="bkBack">↩ Send back</button></div></form></div>`;
    const bf = $('#bookForm');
    const HR = { '2 Star': 2, '3 Star': 3, '4 Star': 4, '5 Star': 5 }; const FR = { Economy: 1, 'Premium Economy': 2, Business: 3, First: 4 };
    bf.onchange = bf.oninput = () => {
      const w = [];
      if (HR[bf.hotel_category.value] > HR[ent.hotel_category]) w.push('Hotel category above entitlement.');
      if (Number(bf.hotel_rate.value) > ent.hotel_max_per_night) w.push(`Rate above ₹${ent.hotel_max_per_night}/night limit.`);
      if (FR[bf.flight_class.value] > FR[ent.flight_class]) w.push('Flight class above entitlement.');
      $('#bookWarn').innerHTML = w.length ? `<div class="alert warn">${w.join(' ')} Justification required - will be flagged as exception.</div>` : '';
    };
    bf.onsubmit = async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(bf).entries());
      try {
        if (bf.files.files.length) await uploadFiles(r.id, bf.files.files, 'TICKET');
        await api(`/api/requests/${r.id}/action`, { method: 'POST', body: { action: 'BOOK', booking: fd, comment: fd.comment } });
        toast('Booking confirmed. Employee notified.', 'success'); refreshCounts(); pageRequest(main, id);
      } catch (err) { toast(err.message, 'error'); }
    };
    $('#bkBack').onclick = () => act('SEND_BACK', { comment: bf.comment.value });
  } else if (inClaimReview) {
    panel.innerHTML = `<div class="card" style="border-left:4px solid var(--brand-2)"><h3>Review expense statement - ${esc(r.stage_label)}</h3>
      <p class="small">Verify each bill below. You can <b>edit the approved amount per line</b> in the expense table (with a note). Claimed ${inr(r.claim_total)} vs approved budget ${inr(r.approved_amount || r.est_total)}.</p>
      <div class="field"><label>Comments</label><textarea id="clCmt"></textarea></div>
      <div class="actions"><button class="btn success" id="clOk">✔ Approve expense statement</button><button class="btn warn" id="clBack">↩ Send back to employee</button><button class="btn danger" id="clRej">✕ Reject</button></div></div>`;
    const collect = () => $$('[data-appr]').map((inp) => ({ id: inp.dataset.appr, approved_inr: inp.value, note: $(`[data-note="${inp.dataset.appr}"]`).value }));
    $$('[data-appr]').forEach((inp) => inp.oninput = () => { $('#apprTotal').textContent = inr($$('[data-appr]').reduce((a, x) => a + (Number(x.value) || 0), 0)); });
    $('#clOk').onclick = () => act('APPROVE', { items: collect(), comment: $('#clCmt').value });
    $('#clBack').onclick = () => act('SEND_BACK', { comment: $('#clCmt').value });
    $('#clRej').onclick = () => act('REJECT', { comment: $('#clCmt').value });
  } else if (r.can_act && st === 'CLAIM_PENDING_ACCOUNTS') {
    const net = (r.claim_approved || 0) - (r.advance_paid || 0);
    panel.innerHTML = `<div class="card" style="border-left:4px solid var(--brand-2)"><h3>Accounting &amp; payment processing</h3>
      <div class="kpis"><div class="kpi"><div class="label">Claim approved (HR)</div><div class="value">${inr(r.claim_approved)}</div></div>
      <div class="kpi"><div class="label">Less: advance paid</div><div class="value">${inr(r.advance_paid || 0)}</div></div>
      <div class="kpi"><div class="label">${net >= 0 ? 'Net payable to employee' : 'Recover from employee'}</div><div class="value">${inr(Math.abs(net))}</div></div></div>
      <form id="payForm"><div class="form-grid">
        <div class="field"><label>Voucher no. *</label><input name="voucher_no" required placeholder="JV/TR/${new Date().getFullYear()}/001"></div>
        <div class="field"><label>GL code</label><input name="gl_code" value="6105 - Travel & Conveyance"></div>
        <div class="field"><label>Cost center</label><input name="cost_center" value="${esc(r.cost_center || r.department || '')}"></div>
        <div class="field"><label>Payment mode *</label><select name="payment_mode">${opt(['NEFT', 'RTGS', 'IMPS', 'UPI', 'Cheque', 'Cash', 'Salary credit', 'Adjusted / Recovered'])}</select></div>
        <div class="field"><label>UTR / cheque ref.</label><input name="payment_ref"></div>
        <div class="field"><label>Payment date *</label><input type="date" name="payment_date" value="${today()}" required></div>
        <div class="field full"><label>Accounting notes</label><textarea name="accounting_notes"></textarea></div>
        <div class="field full"><label>Attach payment proof (optional)</label><input type="file" name="files" accept="application/pdf,image/*"></div>
      </div><div class="actions"><button class="btn success">✔ Post voucher &amp; mark paid</button><button type="button" class="btn warn" id="payBack">↩ Send back</button></div></form></div>`;
    $('#payForm').onsubmit = async (e) => {
      e.preventDefault();
      const f = e.target; const fd = Object.fromEntries(new FormData(f).entries());
      try {
        if (f.files.files.length) await uploadFiles(r.id, f.files.files, 'PAYMENT_PROOF');
        await api(`/api/requests/${r.id}/action`, { method: 'POST', body: { action: 'PROCESS_PAYMENT', payment: fd } });
        toast('Payment processed. Request closed.', 'success'); refreshCounts(); pageRequest(main, id);
      } catch (err) { toast(err.message, 'error'); }
    };
    $('#payBack').onclick = () => { const c = prompt('Reason for sending back?'); if (c) act('SEND_BACK', { comment: c }); };
  } else if (r.can_claim) {
    panel.innerHTML = `<div class="card" style="border-left:4px solid var(--accent)"><h3>Submit expense statement</h3>
      <p class="small">${st === 'CLAIM_SENT_BACK' ? '<b>Sent back:</b> ' + esc((r.history.filter((h) => h.action === 'SEND_BACK').pop() || {}).comment) + '<br>' : ''}
      After your trip, add all expenses with bills below, then submit. It goes to Business Head → HR Head → Accountant.</p>
      <div class="field"><label>Remarks (mandatory if a bill is missing)</label><textarea id="clNote"></textarea></div>
      <div class="actions"><button class="btn primary" id="clSubmit" ${r.items.length ? '' : 'disabled'}>Submit expense statement (${inr(r.claim_total || 0)})</button></div></div>`;
    $('#clSubmit').onclick = () => act('SUBMIT_CLAIM', { comment: $('#clNote').value });
  } else if (!r.is_owner && Object.values(state.meta.stages[st] || {}).length && state.meta.stages[st].role) {
    panel.innerHTML = `<div class="alert info">Currently waiting for <b>${esc(state.meta.stages[st].role)}</b>${r.bh_name && /BH/.test(st) ? ' (' + esc(r.bh_name) + ')' : ''}.</div>`;
  }
  // advance disbursal for accountant
  if ((u.role === wf.AC || isAdmin()) && ['PENDING_BOOKING', 'BOOKED'].includes(st) && r.advance_requested > 0 && !r.advance_paid) {
    panel.insertAdjacentHTML('beforeend', `<div class="card" style="border-left:4px solid #eda100"><h3>Disburse travel advance</h3><div class="form-grid">
      <div class="field"><label>Amount (₹)</label><input type="number" id="advAmt" value="${r.advance_requested}"></div>
      <div class="field"><label>Payment reference</label><input id="advRef" placeholder="UTR / voucher"></div></div>
      <div class="actions"><button class="btn primary" id="advPay">Record advance paid</button></div></div>`);
    $('#advPay').onclick = () => act('PAY_ADVANCE', { amount: $('#advAmt').value, reference: $('#advRef').value });
  }
  if (r.can_cancel && $('#cancelBtn')) $('#cancelBtn').onclick = () => { if (confirm('Cancel this travel request?')) act('CANCEL'); };

  // ---------- claim editing handlers ----------
  if (r.can_claim) {
    const ef = $('#expForm');
    const cur = ef.currency; const fx = ef.fx_rate;
    cur.onchange = () => { fx.value = s.currencies[cur.value] || ''; $('#fxBox').classList.toggle('hidden', cur.value === 'INR'); };
    ef.onsubmit = async (e) => {
      e.preventDefault();
      const fd = Object.fromEntries(new FormData(ef).entries());
      try {
        const res = await api(`/api/requests/${r.id}/items`, { method: 'POST', body: fd });
        if (ef.bill.files.length) await uploadFiles(r.id, ef.bill.files, 'BILL', res.id);
        toast('Expense added.', 'success'); pageRequest(main, id);
      } catch (err) { toast(err.message, 'error'); }
    };
    $$('[data-up-item]').forEach((inp) => inp.onchange = async () => {
      try { await uploadFiles(r.id, inp.files, 'BILL', Number(inp.dataset.upItem)); toast('Bill attached.', 'success'); pageRequest(main, id); } catch (err) { toast(err.message, 'error'); }
    });
    $$('[data-del-item]').forEach((b) => b.onclick = async () => { if (!confirm('Delete this expense line?')) return; try { await api('/api/items/' + b.dataset.delItem, { method: 'DELETE' }); pageRequest(main, id); } catch (err) { toast(err.message, 'error'); } });
    $$('[data-del-att]').forEach((b) => b.onclick = async () => { try { await api('/api/attachments/' + b.dataset.delAtt, { method: 'DELETE' }); pageRequest(main, id); } catch (err) { toast(err.message, 'error'); } });
  }
}

function expenseForm(r) {
  const s = state.meta.settings;
  return `<form id="expForm" style="margin-top:14px"><h3>Add expense</h3><div class="form-grid">
    <div class="field"><label>Date *</label><input type="date" name="exp_date" required value="${r.depart_date}" min="${r.depart_date}"></div>
    <div class="field"><label>Category *</label><select name="category">${opt(s.expense_categories)}</select></div>
    <div class="field"><label>Description</label><input name="description" placeholder="e.g. Dinner with client"></div>
    <div class="field"><label>Vendor</label><input name="vendor"></div>
    <div class="field"><label>Bill / invoice no.</label><input name="bill_no"></div>
    <div class="field"><label>Currency</label><select name="currency">${opt(Object.keys(s.currencies), 'INR')}</select></div>
    <div class="field hidden" id="fxBox"><label>Exchange rate to INR</label><input type="number" step="0.0001" name="fx_rate" value="1"></div>
    <div class="field"><label>Amount *</label><input type="number" name="amount" min="0.01" step="0.01" required></div>
    <div class="field"><label>Bill attachment</label><input type="file" name="bill" multiple accept="application/pdf,image/*" capture="environment"></div>
  </div><div class="actions"><button class="btn primary">+ Add expense</button></div></form>`;
}

/* ================================================================== */
/* Analytics (Admin)                                                  */
/* ================================================================== */
async function pageAnalytics(main) {
  const y = new Date().getFullYear();
  main.innerHTML = `<div class="page-head"><div><h1>Travel Analytics Dashboard</h1><p>Employee-wise, destination-wise, airline-wise spend with exception flags.</p></div>
    <div class="actions" style="margin:0"><a class="btn" href="${fileUrl('/api/export/requests.csv')}">${I.download} Export CSV</a><a class="btn" href="${fileUrl('/api/backup')}">${I.download} Backup database</a></div></div>
    <div class="filters card" style="padding:12px 14px"><div class="field"><label>Travel from</label><input type="date" id="aFrom" value="${y - 1}-04-01"></div>
    <div class="field"><label>Travel to</label><input type="date" id="aTo" value="${y + 1}-03-31"></div>
    <div class="field"><label>Quick range</label><select id="aQuick"><option value="">Custom</option><option value="fy">Current financial year</option><option value="90">Last 90 days</option><option value="all">All time</option></select></div>
    <button class="btn primary" id="aGo">Apply</button></div>
    <div id="aBody"><div class="empty">Loading…</div></div>`;
  const fy = () => { const d = new Date(); const s = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1; return [`${s}-04-01`, `${s + 1}-03-31`]; };
  $('#aQuick').onchange = () => {
    const v = $('#aQuick').value;
    if (v === 'fy') [$('#aFrom').value, $('#aTo').value] = fy();
    if (v === '90') { const d = new Date(); $('#aTo').value = today(); d.setDate(d.getDate() - 90); $('#aFrom').value = d.toISOString().slice(0, 10); }
    if (v === 'all') { $('#aFrom').value = '2000-01-01'; $('#aTo').value = '2099-12-31'; }
    load();
  };
  $('#aGo').onclick = load;
  async function load() {
    const a = await api(`/api/analytics?from=${$('#aFrom').value}&to=${$('#aTo').value}`);
    const k = a.kpis;
    $('#aBody').innerHTML = `
      <div class="kpis">
        <div class="kpi"><div class="label">Total travel spend</div><div class="value">${Charts.compact(k.total_spend)}</div><div class="sub">${k.active_trips} active trips</div></div>
        <div class="kpi"><div class="label">Approved budgets</div><div class="value">${Charts.compact(k.estimated)}</div><div class="sub">pre-travel estimates</div></div>
        <div class="kpi"><div class="label">Reimbursed (net)</div><div class="value">${Charts.compact(k.paid)}</div><div class="sub">closed claims</div></div>
        <div class="kpi"><div class="label">Pending in workflow</div><div class="value">${k.pending_approvals}</div><div class="sub">${k.rejected} rejected</div></div>
        <div class="kpi"><div class="label">Avg. booking lead time</div><div class="value">${k.avg_lead_days} d</div><div class="sub">target ≥ ${a.min_advance_days} days</div></div>
        <div class="kpi ${k.exceptions ? 'alert' : ''}"><div class="label">Exceptions flagged</div><div class="value">${k.exceptions}</div><div class="sub">${k.late_bookings} late bookings</div></div>
      </div>
      <div class="grid g2">
        <div class="card"><h3>Monthly travel spend</h3><div class="chart" id="cMonth"></div></div>
        <div class="card"><h3>Advance planning vs average domestic airfare</h3><div class="chart" id="cLead"></div><p class="small muted">Trips booked earlier pay lower fares - supports the ${a.min_advance_days}-day advance policy.</p></div>
        <div class="card"><h3>Employee-wise spend (top 10)</h3><div class="chart" id="cEmp"></div></div>
        <div class="card"><h3>Destination-wise spend (top 10)</h3><div class="chart" id="cDest"></div></div>
        <div class="card"><h3>Airline-wise ticket spend</h3><div class="chart" id="cAir"></div></div>
        <div class="card"><h3>Expense category split (claims)</h3><div class="chart" id="cCat"></div></div>
        <div class="card"><h3>Department-wise spend</h3><div class="chart" id="cDept"></div></div>
        <div class="card"><h3>Requests by workflow stage</h3><div class="chart" id="cStage"></div></div>
      </div>
      <div class="card"><h3>Exception report (${a.exceptions.length})</h3>
        ${a.exceptions.length ? `<div class="table-wrap"><table><thead><tr><th>Severity</th><th>Type</th><th>Request</th><th>Employee</th><th>Route / date</th><th>Detail</th></tr></thead><tbody>
        ${a.exceptions.map((x) => `<tr class="clickable" data-href="#/request/${x.request_id}"><td><span class="chip ${x.severity === 'warning' ? 'warn' : x.severity}">${SEV_LABEL[x.severity]}</span></td><td>${esc(EXC_LABEL[x.code] || x.code)}</td>
          <td><a href="#/request/${x.request_id}">${esc(x.ref_no)}</a></td><td>${esc(x.employee_name)}</td><td>${esc(x.route)}<div class="small muted">${fmtDate(x.depart_date)}</div></td><td>${esc(x.message)}</td></tr>`).join('')}</tbody></table></div>` : '<div class="empty">No exceptions in this period. 👍</div>'}
      </div>
      <div class="card"><h3>Employee-wise summary</h3><div class="table-wrap"><table><thead><tr><th>Employee</th><th class="num">Trips</th><th class="num">Spend</th><th class="num">Avg / trip</th></tr></thead><tbody>
        ${a.by_employee.map((e) => `<tr><td>${esc(e.key)}</td><td class="num">${e.trips}</td><td class="num">${inr(e.value)}</td><td class="num">${inr(Math.round(e.value / e.trips))}</td></tr>`).join('') || '<tr><td colspan="4" class="empty">No data</td></tr>'}</tbody></table></div></div>`;
    const m = (arr, extra) => arr.map((x) => ({ label: x.key, value: x.value, extra: extra ? extra(x) : `${x.trips} trip(s)` }));
    const monthLab = (k) => { const [yy, mm] = k.split('-'); return new Date(yy, mm - 1, 1).toLocaleDateString('en-IN', { month: 'short', year: '2-digit' }); };
    Charts.column($('#cMonth'), a.by_month.map((x) => ({ label: monthLab(x.key), value: x.value, extra: `${x.trips} trip(s)` })), { title: 'Monthly spend' });
    Charts.column($('#cLead'), a.lead_time.map((x) => ({ label: x.key, value: x.avg_fare, extra: `${x.trips} trip(s) booked` })), { title: 'Average fare by lead time' });
    Charts.hbar($('#cEmp'), m(a.by_employee));
    Charts.hbar($('#cDest'), m(a.by_destination));
    Charts.hbar($('#cAir'), m(a.by_airline, (x) => `${x.trips} ticket(s) · avg ${inr(x.avg_fare)}`));
    Charts.hbar($('#cCat'), a.by_category.map((x) => ({ label: x.key, value: x.value })), { labelW: 140, maxChars: 22 });
    Charts.hbar($('#cDept'), m(a.by_department), { labelW: 150 });
    Charts.hbar($('#cStage'), a.by_stage.map((x) => ({ label: x.label, value: x.value })), { format: (v) => v + ' req.', labelW: 170, maxChars: 26 });
    bindRowClicks($('#aBody'));
  }
  load();
}

/* ================================================================== */
/* Employees (Admin)                                                  */
/* ================================================================== */
async function pageEmployees(main) {
  const emps = await api('/api/employees');
  const s = state.meta.settings;
  main.innerHTML = `<div class="page-head"><div><h1>Employees</h1><p>Only email ids added here can sign up. Assign role, Business Head and grade (drives Matrix of Authority).</p></div>
    <div class="actions" style="margin:0"><button class="btn" id="impBtn">Import CSV</button><button class="btn primary" id="addBtn">${I.plus} Add employee</button></div></div>
    <div class="filters"><div class="field"><label>Search</label><input id="eQ" placeholder="Name, email, role"></div>
    <div class="field"><label>Role</label><select id="eRole"><option value="">All roles</option>${opt(s.roles)}</select></div></div>
    <div class="card" id="eList"></div>`;
  const draw = () => {
    const q = $('#eQ').value.toLowerCase(), role = $('#eRole').value;
    const f = emps.filter((e) => (!role || e.role === role) && (!q || `${e.name} ${e.email} ${e.role} ${e.emp_code}`.toLowerCase().includes(q)));
    $('#eList').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Code</th><th>Name / email</th><th>Role</th><th>Department</th><th>Business Head</th><th>Status</th><th class="num">Trips</th><th class="num">Spend</th><th>Last login</th><th></th></tr></thead><tbody>
      ${f.map((e) => `<tr><td>${esc(e.emp_code)}</td><td><b>${esc(e.name)}</b>${e.is_admin ? ' <span class="chip">Admin</span>' : ''}<div class="small muted">${esc(e.email)}</div></td><td>${esc(e.role)}</td><td>${esc(e.department || '—')}</td>
        <td>${esc(e.business_head_name || '—')}</td><td>${!e.is_active ? '<span class="chip grey">Inactive</span>' : e.registered ? '<span class="chip good">Signed up</span>' : '<span class="chip warn">Awaiting sign up</span>'}</td>
        <td class="num">${e.trips}</td><td class="num">${inr(e.spend)}</td><td class="small">${fmtDT(e.last_login_at)}</td>
        <td class="nowrap"><button class="btn sm" data-edit="${e.id}">Edit</button> <button class="btn sm" data-pw="${e.id}">Reset password</button></td></tr>`).join('')}</tbody></table></div>`;
    $$('[data-edit]').forEach((b) => b.onclick = () => empModal(emps.find((e) => e.id === Number(b.dataset.edit))));
    $$('[data-pw]').forEach((b) => b.onclick = async () => {
      const e = emps.find((x) => x.id === Number(b.dataset.pw));
      const pw = prompt(`New temporary password for ${e.name} (min 8 chars, letters + numbers):`);
      if (!pw) return;
      try { await api(`/api/employees/${e.id}/reset-password`, { method: 'POST', body: { password: pw } }); toast('Password reset. Share it securely with the employee.', 'success'); } catch (err) { toast(err.message, 'error'); }
    });
  };
  $('#eQ').oninput = draw; $('#eRole').onchange = draw; draw();
  $('#addBtn').onclick = () => empModal(null);
  $('#impBtn').onclick = () => {
    const m = modal('Import employees from CSV', `<p class="small">Columns: <code>emp_code,name,email,role,department,grade,phone,base_city,business_head_email</code>. Role must match the role list.</p>
      <input type="file" id="csvFile" accept=".csv,text/csv"><textarea id="csvText" style="min-height:160px;margin-top:8px" placeholder="emp_code,name,email,role,department,grade,phone,base_city,business_head_email"></textarea>
      <div class="actions"><button class="btn primary" id="csvGo">Import</button></div><div id="csvOut"></div>`);
    $('#csvFile', m.el).onchange = async (e) => { $('#csvText', m.el).value = await e.target.files[0].text(); };
    $('#csvGo', m.el).onclick = async () => {
      try {
        const r = await api('/api/employees/import', { method: 'POST', body: { csv: $('#csvText', m.el).value } });
        $('#csvOut', m.el).innerHTML = `<div class="alert good">Added ${r.added} employee(s).</div>${r.skipped.length ? `<div class="alert warn">Skipped:<br>${r.skipped.map(esc).join('<br>')}</div>` : ''}`;
        setTimeout(() => { if (!r.skipped.length) m.close(); pageEmployees(main); }, 1200);
      } catch (err) { toast(err.message, 'error'); }
    };
  };
  function empModal(e) {
    const bhs = emps.filter((x) => x.role === 'Business Head' && x.is_active && (!e || x.id !== e.id));
    const m = modal(e ? 'Edit employee' : 'Add employee', `<form id="empForm"><div class="form-grid">
      <div class="field"><label>Employee code</label><input name="emp_code" value="${esc(e ? e.emp_code : '')}" placeholder="Auto if blank"></div>
      <div class="field"><label>Full name *</label><input name="name" required value="${esc(e ? e.name : '')}"></div>
      <div class="field"><label>Email id * (used for sign up / login)</label><input type="email" name="email" required value="${esc(e ? e.email : '')}"></div>
      <div class="field"><label>Role *</label><select name="role">${opt(s.roles, e ? e.role : 'Sales Executive')}</select></div>
      <div class="field"><label>Department</label><select name="department"><option value=""></option>${opt(s.departments, e ? e.department : '')}</select></div>
      <div class="field"><label>Grade / band</label><input name="grade" value="${esc(e ? e.grade : '')}" placeholder="e.g. M2"></div>
      <div class="field"><label>Reporting Business Head</label><select name="business_head_id"><option value="">— Any Business Head —</option>${opt(bhs.map((b) => [b.id, b.name]), e ? e.business_head_id : '')}</select></div>
      <div class="field"><label>Mobile</label><input name="phone" value="${esc(e ? e.phone : '')}"></div>
      <div class="field"><label>Base city</label><input name="base_city" list="cities2" value="${esc(e ? e.base_city : '')}"><datalist id="cities2">${CITIES.map((c) => `<option value="${c}">`).join('')}</datalist></div>
      <label class="check"><input type="checkbox" name="is_admin" ${e && e.is_admin ? 'checked' : ''}> Admin access</label>
      <label class="check"><input type="checkbox" name="is_active" ${!e || e.is_active ? 'checked' : ''}> Active</label>
      </div><div class="actions"><button class="btn primary">${e ? 'Save changes' : 'Add employee'}</button></div></form>`);
    $('#empForm', m.el).onsubmit = async (ev) => {
      ev.preventDefault();
      const f = ev.target; const body = Object.fromEntries(new FormData(f).entries());
      body.is_admin = f.is_admin.checked; body.is_active = f.is_active.checked;
      try {
        if (e) await api('/api/employees/' + e.id, { method: 'PUT', body }); else await api('/api/employees', { method: 'POST', body });
        toast(e ? 'Employee updated.' : `Employee added. ${body.email} can now sign up.`, 'success'); m.close();
        state.meta = await api('/api/meta'); pageEmployees(main);
      } catch (err) { toast(err.message, 'error'); }
    };
  }
}

/* ================================================================== */
/* Settings (Admin)                                                   */
/* ================================================================== */
async function pageSettings(main) {
  const { settings: s, matrix } = await api('/api/settings');
  const lines = (a) => a.join('\n');
  main.innerHTML = `<div class="page-head"><div><h1>Policy &amp; Settings</h1><p>Travel policy rules, Matrix of Authority, master lists and optional features.</p></div></div>
  <form id="setForm">
    <div class="card"><h3>Travel policy rules</h3><div class="form-grid">
      <div class="field"><label>Company name</label><input name="company_name" value="${esc(s.company_name)}"></div>
      <div class="field"><label>Minimum advance planning (days)</label><input type="number" min="0" name="min_advance_days" value="${s.min_advance_days}"><span class="hint">Requests closer to travel are flagged "Late booking"</span></div>
      <div class="field"><label>Over-budget tolerance (%)</label><input type="number" min="0" name="over_budget_tolerance_pct" value="${s.over_budget_tolerance_pct}"></div>
      <div class="field"><label>Bill mandatory above (₹)</label><input type="number" min="0" name="bill_required_above" value="${s.bill_required_above}"></div>
      <div class="field"><label>Expense statement deadline (days after return)</label><input type="number" min="0" name="claim_deadline_days" value="${s.claim_deadline_days}"></div>
      <div class="field"><label>Max trip length (days)</label><input type="number" min="1" name="max_trip_days" value="${s.max_trip_days}"></div>
    </div></div>
    <div class="card"><h3>Optional features (switch on / off)</h3><div class="form-grid">
      ${Object.entries({ international_travel: 'International travel & multi-currency', travel_advance: 'Travel advance requests', feature_board: 'Feature suggestion board', late_booking_justification: 'Mandatory justification for late booking' })
    .map(([k, l]) => `<label class="check"><input type="checkbox" name="f_${k}" ${s.features[k] ? 'checked' : ''}> ${l}</label>`).join('')}
    </div></div>
    <div class="grid g2">
      <div class="card"><h3>Roles (drop-down for Admin)</h3><textarea name="roles" style="min-height:190px">${esc(lines(s.roles))}</textarea><span class="hint small muted">One per line. Workflow roles (Business Head, Managing Director, Travel Assistant, HR Head, Accountant) are always kept.</span></div>
      <div class="card"><h3>Departments</h3><textarea name="departments" style="min-height:190px">${esc(lines(s.departments))}</textarea></div>
      <div class="card"><h3>Expense categories</h3><textarea name="expense_categories" style="min-height:190px">${esc(lines(s.expense_categories))}</textarea></div>
      <div class="card"><h3>Airlines</h3><textarea name="airlines" style="min-height:190px">${esc(lines(s.airlines))}</textarea></div>
      <div class="card"><h3>Currencies &amp; exchange rates to INR</h3><textarea name="currencies" style="min-height:150px">${esc(Object.entries(s.currencies).map(([k, v]) => `${k}=${v}`).join('\n'))}</textarea><span class="hint small muted">Format CODE=rate, e.g. USD=84</span></div>
    </div>
    <div class="actions"><button class="btn primary">Save settings</button></div>
  </form>
  <div class="card" style="margin-top:16px"><h3>Matrix of Authority - travel entitlement by role</h3>
    <div class="table-wrap"><table><thead><tr><th>Role</th><th>Flight class</th><th>Hotel category</th><th>Hotel max / night (₹)</th><th>Food DA / day (₹)</th><th>Local conveyance / day (₹)</th></tr></thead><tbody>
    ${matrix.map((m) => `<tr data-role="${esc(m.role)}"><td><b>${esc(m.role)}</b></td><td><select data-k="flight_class">${opt(state.meta.flight_classes, m.flight_class)}</select></td>
      <td><select data-k="hotel_category">${opt(state.meta.hotel_categories, m.hotel_category)}</select></td>
      <td><input type="number" data-k="hotel_max_per_night" value="${m.hotel_max_per_night}"></td><td><input type="number" data-k="da_per_day" value="${m.da_per_day}"></td><td><input type="number" data-k="local_per_day" value="${m.local_per_day}"></td></tr>`).join('')}
    </tbody></table></div><div class="actions"><button class="btn primary" id="saveMatrix">Save Matrix of Authority</button></div></div>`;
  $('#setForm').onsubmit = async (e) => {
    e.preventDefault();
    const f = e.target; const L = (n) => f[n].value.split('\n').map((x) => x.trim()).filter(Boolean);
    const cur = {}; for (const l of L('currencies')) { const [k, v] = l.split('='); if (k && Number(v) > 0) cur[k.trim().toUpperCase()] = Number(v); }
    cur.INR = 1;
    const body = {
      company_name: f.company_name.value, min_advance_days: f.min_advance_days.value, over_budget_tolerance_pct: f.over_budget_tolerance_pct.value,
      bill_required_above: f.bill_required_above.value, claim_deadline_days: f.claim_deadline_days.value, max_trip_days: f.max_trip_days.value,
      roles: L('roles'), departments: L('departments'), expense_categories: L('expense_categories'), airlines: L('airlines'), currencies: cur,
      features: Object.fromEntries(['international_travel', 'travel_advance', 'feature_board', 'late_booking_justification'].map((k) => [k, f['f_' + k].checked])),
    };
    try { await api('/api/settings', { method: 'PUT', body }); state.meta = await api('/api/meta'); toast('Settings saved.', 'success'); renderShell(); router(); } catch (err) { toast(err.message, 'error'); }
  };
  $('#saveMatrix').onclick = async () => {
    const rows = $$('tr[data-role]').map((tr) => { const o = { role: tr.dataset.role }; $$('[data-k]', tr).forEach((i) => { o[i.dataset.k] = i.value; }); return o; });
    try { await api('/api/matrix', { method: 'PUT', body: { rows } }); state.meta = await api('/api/meta'); toast('Matrix of Authority saved.', 'success'); } catch (err) { toast(err.message, 'error'); }
  };
}

/* ================================================================== */
/* Logs, notifications, features, profile, policy                     */
/* ================================================================== */
async function pageLogs(main) {
  const logs = await api('/api/auth-logs');
  const events = [...new Set(logs.map((l) => l.event))];
  main.innerHTML = `<div class="page-head"><div><h1>Sign-in / Sign-up Log</h1><p>Every sign up, login, failed attempt, logout and account change is saved in the database.</p></div></div>
    <div class="filters"><div class="field"><label>Event</label><select id="lE"><option value="">All events</option>${opt(events)}</select></div><div class="field"><label>Email</label><input id="lQ"></div></div>
    <div class="card" id="lList"></div>`;
  const cls = (e) => /FAILED|REJECTED|BLOCKED/.test(e) ? 'critical' : /SUCCESS/.test(e) ? 'good' : '';
  const draw = () => {
    const ev = $('#lE').value, q = $('#lQ').value.toLowerCase();
    const f = logs.filter((l) => (!ev || l.event === ev) && (!q || (l.email || '').includes(q)));
    $('#lList').innerHTML = `<div class="table-wrap"><table><thead><tr><th>Date &amp; time</th><th>Event</th><th>Email</th><th>Detail</th><th>IP</th><th>Device / browser</th></tr></thead><tbody>
      ${f.map((l) => `<tr><td class="nowrap">${fmtDT(l.created_at)}</td><td><span class="chip ${cls(l.event)}">${esc(l.event)}</span></td><td>${esc(l.email)}</td><td>${esc(l.detail || '')}</td><td>${esc(l.ip)}</td><td class="small muted">${esc((l.user_agent || '').slice(0, 70))}</td></tr>`).join('')}</tbody></table></div>`;
  };
  $('#lE').onchange = draw; $('#lQ').oninput = draw; draw();
}

async function pageNotifications(main) {
  const list = await api('/api/notifications');
  main.innerHTML = `<div class="page-head"><div><h1>Notifications</h1></div><button class="btn" id="markAll">Mark all as read</button></div>
    <div class="card">${list.length ? `<ul class="list-plain">${list.map((n) => `<li class="notif ${n.is_read ? '' : 'unread'}"><div>${n.request_id ? `<a href="#/request/${n.request_id}">${esc(n.message)}</a>` : esc(n.message)}<div class="small muted">${fmtDT(n.created_at)}</div></div>${n.is_read ? '' : '<span class="chip">New</span>'}</li>`).join('')}</ul>` : '<div class="empty">No notifications.</div>'}</div>`;
  $('#markAll').onclick = async () => { await api('/api/notifications/read', { method: 'POST' }); refreshCounts(); pageNotifications(main); };
}

async function pageFeatures(main) {
  if (!state.meta.settings.features.feature_board) { main.innerHTML = '<div class="alert info">The feature board is switched off by Admin.</div>'; return; }
  const list = await api('/api/features');
  const statuses = ['Proposed', 'Under Review', 'Planned', 'In Progress', 'Released', 'Declined'];
  main.innerHTML = `<div class="page-head"><div><h1>Feature Board</h1><p>Suggest new features for the travel app and vote. Admin tracks status for the roadmap.</p></div></div>
    <div class="card"><form id="fForm"><div class="form-grid"><div class="field"><label>Feature title</label><input name="title" required placeholder="e.g. Corporate card integration"></div>
      <div class="field full"><label>Description</label><textarea name="description"></textarea></div></div><div class="actions"><button class="btn primary">Submit suggestion</button></div></form></div>
    <div class="card">${list.length ? `<ul class="list-plain">${list.map((f) => `<li><div><b>${esc(f.title)}</b> <span class="chip ${f.status === 'Released' ? 'good' : f.status === 'Declined' ? 'grey' : ''}">${esc(f.status)}</span>
      <div class="small">${esc(f.description || '')}</div><div class="small muted">by ${esc(f.by_name || '—')} · ${fmtDate(f.created_at)}</div></div>
      <div class="nowrap">${isAdmin() ? `<select data-fs="${f.id}" style="width:auto">${opt(statuses, f.status)}</select> ` : ''}<button class="btn sm ${f.voted ? 'primary' : ''}" data-vote="${f.id}">▲ ${f.votes}</button></div></li>`).join('')}</ul>` : '<div class="empty">No suggestions yet.</div>'}</div>`;
  $('#fForm').onsubmit = async (e) => { e.preventDefault(); try { await api('/api/features', { method: 'POST', body: Object.fromEntries(new FormData(e.target).entries()) }); toast('Thanks for the suggestion!', 'success'); pageFeatures(main); } catch (err) { toast(err.message, 'error'); } };
  $$('[data-vote]').forEach((b) => b.onclick = async () => { await api(`/api/features/${b.dataset.vote}/vote`, { method: 'POST' }); pageFeatures(main); });
  $$('[data-fs]').forEach((sel) => sel.onchange = async () => { await api('/api/features/' + sel.dataset.fs, { method: 'PUT', body: { status: sel.value } }); toast('Status updated.', 'success'); });
}

async function pageProfile(main) {
  const u = state.user; const e = state.entitlement;
  main.innerHTML = `<div class="page-head"><div><h1>My Profile</h1></div></div>
    <div class="grid g2"><div class="card"><h3>Details</h3><dl class="kv"><dt>Name</dt><dd>${esc(u.name)}</dd><dt>Email id</dt><dd>${esc(u.email)}</dd><dt>Employee code</dt><dd>${esc(u.emp_code || '—')}</dd>
      <dt>Role</dt><dd>${esc(u.role)}${u.is_admin ? ' (Admin)' : ''}</dd><dt>Department</dt><dd>${esc(u.department || '—')}</dd><dt>Base city</dt><dd>${esc(u.base_city || '—')}</dd>
      <dt>Signed up</dt><dd>${fmtDT(u.registered_at)}</dd><dt>Entitlement</dt><dd>${esc(e.flight_class)} · ${esc(e.hotel_category)} · DA ${inr(e.da_per_day)}</dd></dl>
      <p class="small muted">Contact Admin to change role or details.</p></div>
    <div class="card"><h3>Change password</h3><form id="pwForm"><div class="field"><label>Current password</label><input type="password" name="current" required autocomplete="current-password"></div>
      <div class="field" style="margin-top:8px"><label>New password</label><input type="password" name="password" required minlength="8" autocomplete="new-password"></div>
      <div class="actions"><button class="btn primary">Update password</button></div></form></div></div>`;
  $('#pwForm').onsubmit = async (ev) => { ev.preventDefault(); try { await api('/api/me/password', { method: 'POST', body: Object.fromEntries(new FormData(ev.target).entries()) }); toast('Password updated.', 'success'); ev.target.reset(); } catch (err) { toast(err.message, 'error'); } };
}

async function pagePolicy(main) {
  const s = state.meta.settings; const m = state.meta.matrix;
  main.innerHTML = `<div class="page-head"><div><h1>${esc(s.company_name)} - Travel &amp; Expense Policy</h1><p>Summary of rules enforced by this app.</p></div><button class="btn" onclick="window.print()">🖨 Print</button></div>
    <div class="card"><h3>Approval workflow</h3>${workflowDiagram()}
      <p class="small">Business Heads' own requests go directly to the Managing Director; the MD's own requests go directly to booking. Nobody can approve their own request. Every action is recorded in the audit trail.</p></div>
    <div class="card"><h3>Key rules</h3><ul>
      <li><b>Plan early:</b> raise the pre-travel request at least <b>${s.min_advance_days} days</b> before departure so that flight tickets are cheaper. Late requests need a justification and are flagged.</li>
      <li>No travel or booking without Business Head and Managing Director approval.</li>
      <li>All flights and hotels are booked by the Travel Assistant as per the Matrix of Authority below. Bookings above entitlement need written justification.</li>
      <li>Submit the expense statement within <b>${s.claim_deadline_days} days</b> of return, with bills attached for every expense above <b>${inr(s.bill_required_above)}</b>.</li>
      <li>Claims more than <b>${s.over_budget_tolerance_pct}%</b> above the approved budget are flagged for scrutiny.</li>
      <li>Expense statement is approved by the Business Head and then the HR Head; the Accountant posts the voucher, adjusts any travel advance and releases payment.</li>
      <li>Foreign-currency expenses are converted to INR at the rate entered (default rates set by Finance).</li></ul></div>
    <div class="card"><h3>Matrix of Authority</h3><div class="table-wrap"><table><thead><tr><th>Role</th><th>Flight</th><th>Hotel</th><th class="num">Hotel max / night</th><th class="num">Food DA / day</th><th class="num">Local / day</th></tr></thead><tbody>
      ${m.map((r) => `<tr><td>${esc(r.role)}</td><td>${esc(r.flight_class)}</td><td>${esc(r.hotel_category)}</td><td class="num">${inr(r.hotel_max_per_night)}</td><td class="num">${inr(r.da_per_day)}</td><td class="num">${inr(r.local_per_day)}</td></tr>`).join('')}</tbody></table></div></div>`;
}

/* ================================================================== */
boot();
