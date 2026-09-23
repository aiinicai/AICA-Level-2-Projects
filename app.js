'use strict';

/* ==================================================================== */
/* Tiny API client                                                      */
/* ==================================================================== */

const Api = {
  async _req(method, url, body) {
    const opts = { method, headers: {} };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    let res;
    try {
      res = await fetch(url, opts);
    } catch (netErr) {
      throw new Error('Could not reach the server. Is "node server.js" still running?');
    }
    let payload = null;
    const text = await res.text();
    if (text) {
      try { payload = JSON.parse(text); } catch (e) { /* non-JSON response */ }
    }
    if (!res.ok) {
      const msg = (payload && payload.message) || `Request failed (${res.status})`;
      throw new Error(msg);
    }
    return payload;
  },
  get(url) { return this._req('GET', url); },
  post(url, body) { return this._req('POST', url, body); },
  put(url, body) { return this._req('PUT', url, body); },
  del(url) { return this._req('DELETE', url); },
};

/* ==================================================================== */
/* Formatting helpers                                                   */
/* ==================================================================== */

const fmtINR = new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0,
});
const fmtPct = (n) => (n === null || n === undefined) ? '—' : (n * 100).toFixed(1) + '%';
const fmtDate = (s) => {
  if (!s) return '—';
  const d = new Date(s + (s.length === 10 ? 'T00:00:00' : ''));
  if (Number.isNaN(d.getTime())) return s;
  return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
};

function money(n) { return fmtINR.format(Math.round(n || 0)); }

function profitClass(n) { return n >= 0 ? 'is-profit' : 'is-loss'; }

/* ==================================================================== */
/* Global state                                                         */
/* ==================================================================== */

const State = {
  managers: [],       // [{id, name, isPartner}]
  dashboard: null,    // last /api/dashboard payload
  assignmentsFlat: [], // for select boxes
};

/* ==================================================================== */
/* Toast                                                                */
/* ==================================================================== */

let toastTimer = null;
function toast(message, isError) {
  const el = document.getElementById('toast');
  el.textContent = message;
  el.classList.toggle('is-error', !!isError);
  el.classList.add('is-visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('is-visible'), 3200);
}

function reportError(err) {
  console.error(err);
  toast(err.message || 'Something went wrong', true);
}

/* ==================================================================== */
/* Navigation                                                           */
/* ==================================================================== */

function initNav() {
  document.getElementById('app-nav').addEventListener('click', (e) => {
    const btn = e.target.closest('.app-nav__btn');
    if (!btn) return;
    showView(btn.dataset.view);
  });
}

function showView(name) {
  document.querySelectorAll('.app-nav__btn').forEach(b => b.classList.toggle('is-active', b.dataset.view === name));
  document.querySelectorAll('.view').forEach(v => v.classList.remove('is-active'));
  const el = document.getElementById('view-' + name);
  if (el) el.classList.add('is-active');
  if (name === 'assignments') renderAssignmentsTable();
  if (name === 'staff') renderStaffTable();
  if (name === 'revenue') renderRevenueTable();
  if (name === 'managers') renderManagers();
}

/* ==================================================================== */
/* Modal helpers                                                        */
/* ==================================================================== */

function openModal(id) { document.getElementById(id).classList.add('is-open'); }
function closeModal(id) {
  document.getElementById(id).classList.remove('is-open');
  const errEl = document.querySelector(`#${id} .form-error`);
  if (errEl) { errEl.textContent = ''; errEl.classList.remove('is-visible'); }
}

function initModalChrome() {
  document.querySelectorAll('[data-close-modal]').forEach(btn => {
    btn.addEventListener('click', () => closeModal(btn.dataset.closeModal));
  });
  document.querySelectorAll('.modal-backdrop').forEach(bd => {
    bd.addEventListener('click', (e) => { if (e.target === bd) closeModal(bd.id); });
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-backdrop.is-open').forEach(bd => closeModal(bd.id));
    }
  });
}

function showFormError(prefix, message) {
  const el = document.getElementById(`${prefix}-error`);
  el.textContent = message;
  el.classList.add('is-visible');
}

/* ==================================================================== */
/* Bootstrap: load managers + dashboard, populate selects                */
/* ==================================================================== */

async function bootstrap() {
  try {
    const [managers, dashboard] = await Promise.all([
      Api.get('/api/managers'),
      Api.get('/api/dashboard'),
    ]);
    State.managers = managers;
    State.dashboard = dashboard;
    populateManagerSelects();
    populateAssignmentSelects();
    renderDashboard();
    renderManagers();
  } catch (err) {
    reportError(err);
  }
}

async function refreshDashboard() {
  const dashboard = await Api.get('/api/dashboard');
  State.dashboard = dashboard;
  populateAssignmentSelects();
  renderDashboard();
  renderManagers();
}

function managerName(id) {
  const m = State.managers.find(x => x.id === id);
  return m ? m.name : '—';
}

function populateManagerSelects() {
  const options = State.managers
    .map(m => `<option value="${m.id}">${escapeHtml(m.name)}</option>`)
    .join('');
  const targets = ['a-manager', 's-manager', 'flt-a-manager', 'flt-s-manager'];
  targets.forEach(id => {
    const el = document.getElementById(id);
    const firstOpt = el.querySelector('option');
    const keepFirst = firstOpt && firstOpt.value === ''; // preserve "Choose…" / "All managers" placeholders
    el.innerHTML = (keepFirst ? firstOpt.outerHTML : '') + options;
  });
}

function populateAssignmentSelects() {
  const list = (State.dashboard && State.dashboard.assignments) || [];
  State.assignmentsFlat = list;
  const sorted = [...list].sort((a, b) => a.name.localeCompare(b.name));
  const opts = sorted.map(a => `<option value="${a.id}">${escapeHtml(a.name)} (${managerName(a.managerId)})</option>`).join('');

  const sAssignment = document.getElementById('s-assignment');
  sAssignment.innerHTML = opts;

  const rAssignment = document.getElementById('r-assignment');
  rAssignment.innerHTML = opts;

  const fltA = document.getElementById('flt-r-assignment');
  fltA.innerHTML = fltA.querySelector('option').outerHTML +
    sorted.map(a => `<option value="${a.id}">${escapeHtml(a.name)}</option>`).join('');
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ==================================================================== */
/* Dashboard rendering                                                  */
/* ==================================================================== */

function renderDashboard() {
  const d = State.dashboard;
  if (!d) return;

  document.getElementById('overhead-rate-label').textContent = (d.overheadRate * 100).toFixed(0) + '%';
  document.getElementById('overhead-rate-label-2').textContent = (d.overheadRate * 100).toFixed(0) + '%';

  const firmProfitEl = document.getElementById('dash-firm-profit');
  firmProfitEl.textContent = money(d.firm.profit);
  firmProfitEl.classList.toggle('is-profit', d.firm.profit >= 0);
  firmProfitEl.classList.toggle('is-loss', d.firm.profit < 0);

  document.getElementById('dash-period').textContent =
    `Source period: ${State.periodLabel || ''}`.trim();

  document.getElementById('dash-billing').textContent = money(d.firm.billing);
  document.getElementById('dash-cost').textContent = money(d.firm.totalCost);
  document.getElementById('dash-margin').textContent = fmtPct(d.firm.margin);
  document.getElementById('dash-count').textContent = d.firm.assignmentCount;

  // Manager comparison bar chart
  const chartData = d.managers.map(m => ({ label: m.name, billing: m.billing, cost: m.totalCost, profit: m.profit }));
  const chartHost = document.getElementById('chart-managers');
  chartHost.innerHTML = '';
  chartHost.appendChild(Charts.barChart(chartData, { width: 520 }));

  // Cost mix donut
  const mix = [
    { label: 'Direct staff', value: d.firm.directCost, color: '#0f6b5c' },
    { label: 'Pooled (many)', value: d.firm.manyAssignmentsCost, color: '#a9822f' },
    { label: 'Partner pool', value: d.firm.partnerCost, color: '#8a6d1d' },
    { label: 'Overhead', value: d.firm.overhead, color: '#c9d6cf' },
  ];
  const donutHost = document.getElementById('chart-cost-mix');
  donutHost.innerHTML = '';
  donutHost.appendChild(Charts.donutChart(mix, { size: 200 }));
  const legend = document.getElementById('chart-cost-mix-legend');
  legend.innerHTML = mix.map(seg => `
    <span class="legend__item">
      <span class="legend__swatch" style="background:${seg.color}"></span>
      ${escapeHtml(seg.label)} — ${money(seg.value)}
    </span>`).join('');

  // Buckets
  renderBucket('profitable', d.buckets.profitable);
  renderBucket('nonProfitable', d.buckets.nonProfitable);
  renderBucket('inProgress', d.buckets.inProgress);

  document.getElementById('assignment-detail').style.display = 'none';
}

function renderBucket(key, items) {
  document.getElementById(`count-${key}`).textContent = items.length;
  const host = document.getElementById(`list-${key}`);
  if (!items.length) {
    host.innerHTML = '<div class="empty-note">Nothing here yet.</div>';
    return;
  }
  const sorted = [...items].sort((a, b) => b.profit - a.profit);
  host.innerHTML = sorted.map(a => `
    <div class="a-card" data-id="${a.id}" data-context="dashboard">
      <div class="a-card__top">
        <span class="a-card__name">${escapeHtml(a.name)}</span>
        <span class="a-card__profit ${profitClass(a.profit)}">${money(a.profit)}</span>
      </div>
      <div class="a-card__meta">
        <span>${escapeHtml(managerName(a.managerId))}</span>
        <span>Billing ${money(a.billing)}</span>
      </div>
    </div>`).join('');
  host.querySelectorAll('.a-card').forEach(card => {
    card.addEventListener('click', () => showAssignmentDetail(card.dataset.id, 'assignment-detail'));
  });
}

async function showAssignmentDetail(id, hostId) {
  try {
    const a = await Api.get(`/api/assignments/${id}`);
    const host = document.getElementById(hostId);
    host.style.display = 'block';
    host.innerHTML = detailHtml(a);
    wireDetailActions(host, a);
    host.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (err) {
    reportError(err);
  }
}

function bucketLabel(bucket) {
  return { profitable: 'Profitable', nonProfitable: 'Non-profitable', inProgress: 'In progress' }[bucket] || bucket;
}

function detailHtml(a) {
  const staffRows = a.staff.map(s => `
    <tr>
      <td>${escapeHtml(s.name)}</td>
      <td>${escapeHtml(s.designation)}</td>
      <td class="num">${money(s.cost)}</td>
    </tr>`).join('') || '<tr><td colspan="3" class="text-muted">No dedicated staff recorded.</td></tr>';

  const revRows = a.revenue.map(r => `
    <tr>
      <td>${fmtDate(r.date)}</td>
      <td>${r.type === 'credit' ? '<span class="badge badge--loss">Credit note</span>' : '<span class="badge badge--neutral">Billing</span>'}</td>
      <td>${escapeHtml(r.milestone || r.mid || '')}</td>
      <td class="num">${money(r.amount)}</td>
    </tr>`).join('') || '<tr><td colspan="4" class="text-muted">No revenue entries recorded.</td></tr>';

  return `
    <div class="drawer__head">
      <div>
        <h3 class="mt-0">${escapeHtml(a.name)}</h3>
        <p class="section-sub">${escapeHtml(managerName(a.managerId))} · <span class="badge badge--${a.bucket === 'profitable' ? 'profit' : a.bucket === 'nonProfitable' ? 'loss' : 'progress'}">${bucketLabel(a.bucket)}</span></p>
      </div>
      <button class="btn btn--sm" data-detail-close>Close</button>
    </div>
    <div class="kpi-row">
      <div class="kpi"><div class="kpi__label">Billing</div><div class="kpi__value">${money(a.billing)}</div></div>
      <div class="kpi"><div class="kpi__label">Direct staff cost</div><div class="kpi__value">${money(a.directCost)}</div></div>
      <div class="kpi"><div class="kpi__label">Pooled (many) cost</div><div class="kpi__value">${money(a.manyAssignmentsCost)}</div></div>
      <div class="kpi"><div class="kpi__label">Partner cost share</div><div class="kpi__value">${money(a.partnerCost)}</div></div>
      <div class="kpi"><div class="kpi__label">Overhead</div><div class="kpi__value">${money(a.overhead)}</div></div>
      <div class="kpi"><div class="kpi__label">Total cost</div><div class="kpi__value">${money(a.totalCost)}</div></div>
      <div class="kpi"><div class="kpi__label">Profit</div><div class="kpi__value ${profitClass(a.profit)}">${money(a.profit)}</div></div>
      <div class="kpi"><div class="kpi__label">Margin</div><div class="kpi__value">${fmtPct(a.margin)}</div></div>
    </div>
    <h3>Dedicated staff</h3>
    <div class="table-wrap">
      <table><thead><tr><th>Name</th><th>Designation</th><th class="num">Cost</th></tr></thead>
      <tbody>${staffRows}</tbody></table>
    </div>
    <h3 style="margin-top:22px;">Revenue entries</h3>
    <div class="table-wrap">
      <table><thead><tr><th>Date</th><th>Type</th><th>Milestone / MID</th><th class="num">Amount</th></tr></thead>
      <tbody>${revRows}</tbody></table>
    </div>
  `;
}

function wireDetailActions(host, a) {
  const closeBtn = host.querySelector('[data-detail-close]');
  if (closeBtn) closeBtn.addEventListener('click', () => { host.style.display = 'none'; host.innerHTML = ''; });
}

/* ==================================================================== */
/* Managers view                                                        */
/* ==================================================================== */

function renderManagers() {
  const d = State.dashboard;
  if (!d) return;
  const grid = document.getElementById('mgr-grid');
  grid.innerHTML = d.managers.map(m => `
    <div class="mgr-card">
      <div class="mgr-card__name">${escapeHtml(m.name)}</div>
      <div class="mgr-card__row"><span class="k">Assignments</span><span class="v">${m.assignmentCount}</span></div>
      <div class="mgr-card__row"><span class="k">Billing</span><span class="v">${money(m.billing)}</span></div>
      <div class="mgr-card__row"><span class="k">Direct cost</span><span class="v">${money(m.directCost)}</span></div>
      <div class="mgr-card__row"><span class="k">Pooled (many) cost</span><span class="v">${money(m.manyAssignmentsCost)}</span></div>
      <div class="mgr-card__row"><span class="k">Partner share</span><span class="v">${money(m.partnerCostShare)}</span></div>
      <div class="mgr-card__row"><span class="k">Overhead</span><span class="v">${money(m.overhead)}</span></div>
      <div class="mgr-card__row"><span class="k">Total cost</span><span class="v">${money(m.totalCost)}</span></div>
      <div class="mgr-card__row"><span class="k">Profit</span><span class="v ${profitClass(m.profit)}">${money(m.profit)}</span></div>
      <div class="mgr-card__row"><span class="k">Margin</span><span class="v">${fmtPct(m.margin)}</span></div>
    </div>`).join('');

  const partnerHost = document.getElementById('partner-card');
  const p = d.partner;
  partnerHost.innerHTML = `
    <div class="mgr-card">
      <div class="mgr-card__name">${escapeHtml(p.name)}</div>
      <div class="mgr-card__row"><span class="k">Staff reporting to Partner</span><span class="v">${p.staffCount}</span></div>
      <div class="mgr-card__row"><span class="k">Total Partner-pool cost</span><span class="v">${money(p.poolCost)}</span></div>
      ${d.managers.map(m => `<div class="mgr-card__row"><span class="k">→ allocated to ${escapeHtml(m.name)}</span><span class="v">${money(p.allocatedByManager[m.id] || 0)}</span></div>`).join('')}
    </div>`;
}

/* ==================================================================== */
/* Assignments table                                                    */
/* ==================================================================== */

async function renderAssignmentsTable() {
  try {
    const managerId = document.getElementById('flt-a-manager').value;
    const status = document.getElementById('flt-a-status').value;
    const qs = new URLSearchParams();
    if (managerId) qs.set('managerId', managerId);
    if (status) qs.set('status', status);
    const list = await Api.get('/api/assignments' + (qs.toString() ? '?' + qs.toString() : ''));
    const sorted = [...list].sort((a, b) => a.name.localeCompare(b.name));
    const tbody = document.getElementById('tbl-assignments');
    tbody.innerHTML = sorted.map(a => `
      <tr data-id="${a.id}">
        <td>${escapeHtml(a.name)}</td>
        <td>${escapeHtml(managerName(a.managerId))}</td>
        <td>${a.status === 'in-progress' ? '<span class="badge badge--progress">In progress</span>' : '<span class="badge badge--neutral">Completed</span>'}</td>
        <td class="num">${money(a.billing)}</td>
        <td class="num">${money(a.totalCost)}</td>
        <td class="num ${profitClass(a.profit)}">${money(a.profit)}</td>
        <td class="num">${fmtPct(a.margin)}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn--ghost btn--sm" data-action="view">View</button>
            <button class="btn btn--ghost btn--sm" data-action="edit">Edit</button>
            <button class="btn btn--ghost btn--sm btn--danger" data-action="delete">Delete</button>
          </div>
        </td>
      </tr>`).join('') || `<tr><td colspan="8" class="text-muted" style="padding:20px;">No assignments match these filters.</td></tr>`;

    tbody.querySelectorAll('tr[data-id]').forEach(row => {
      const id = row.dataset.id;
      row.querySelector('[data-action="view"]').addEventListener('click', () => showAssignmentDetail(id, 'assignments-detail'));
      row.querySelector('[data-action="edit"]').addEventListener('click', () => openAssignmentModal(id));
      row.querySelector('[data-action="delete"]').addEventListener('click', () => deleteAssignment(id));
    });
  } catch (err) {
    reportError(err);
  }
}

async function deleteAssignment(id) {
  const a = State.assignmentsFlat.find(x => x.id === id);
  const name = a ? a.name : id;
  if (!confirm(`Delete "${name}"? Its staff cost entries become unassigned and its revenue entries are removed. This cannot be undone.`)) return;
  try {
    await Api.del(`/api/assignments/${id}`);
    toast(`Deleted "${name}".`);
    await refreshDashboard();
    renderAssignmentsTable();
  } catch (err) {
    reportError(err);
  }
}

/* --- Assignment add/edit modal --- */

function openAssignmentModal(id) {
  const isEdit = !!id;
  document.getElementById('modal-assignment-title').textContent = isEdit ? 'Edit assignment' : 'Add assignment';
  document.getElementById('a-id').value = id || '';
  if (isEdit) {
    const a = State.assignmentsFlat.find(x => x.id === id);
    document.getElementById('a-name').value = a ? a.name : '';
    document.getElementById('a-manager').value = a ? a.managerId : '';
    document.getElementById('a-status').value = a ? a.status : 'in-progress';
    document.getElementById('a-notes').value = (a && a.notes) || '';
  } else {
    document.getElementById('form-assignment').reset();
  }
  openModal('modal-assignment');
}

function initAssignmentForm() {
  document.getElementById('btn-add-assignment').addEventListener('click', () => openAssignmentModal(null));
  document.getElementById('form-assignment').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('a-id').value;
    const payload = {
      name: document.getElementById('a-name').value.trim(),
      managerId: document.getElementById('a-manager').value,
      status: document.getElementById('a-status').value,
      notes: document.getElementById('a-notes').value,
    };
    if (!payload.name) { showFormError('modal-assignment', 'Assignment name is required.'); return; }
    if (!payload.managerId) { showFormError('modal-assignment', 'Choose a manager.'); return; }
    try {
      if (id) {
        await Api.put(`/api/assignments/${id}`, payload);
        toast('Assignment updated.');
      } else {
        await Api.post('/api/assignments', payload);
        toast('Assignment added.');
      }
      closeModal('modal-assignment');
      await refreshDashboard();
      if (document.getElementById('view-assignments').classList.contains('is-active')) renderAssignmentsTable();
    } catch (err) {
      showFormError('modal-assignment', err.message);
    }
  });
}

/* ==================================================================== */
/* Staff table                                                          */
/* ==================================================================== */

async function renderStaffTable() {
  try {
    const managerId = document.getElementById('flt-s-manager').value;
    const scope = document.getElementById('flt-s-scope').value;
    const qs = new URLSearchParams();
    if (managerId) qs.set('managerId', managerId);
    if (scope) qs.set('scope', scope);
    const list = await Api.get('/api/staff' + (qs.toString() ? '?' + qs.toString() : ''));
    const scopeLabel = { dedicated: 'Dedicated', many: 'Many assignments', partner: 'Partner pool' };
    const assignmentName = (aid) => {
      const a = State.assignmentsFlat.find(x => x.id === aid);
      return a ? a.name : '—';
    };
    const tbody = document.getElementById('tbl-staff');
    tbody.innerHTML = list.map(s => `
      <tr data-id="${s.id}">
        <td>${escapeHtml(s.name)}</td>
        <td>${escapeHtml(s.designation || '—')}</td>
        <td>${escapeHtml(managerName(s.managerId))}</td>
        <td><span class="badge badge--neutral">${scopeLabel[s.scope] || s.scope}</span></td>
        <td>${s.scope === 'dedicated' ? escapeHtml(assignmentName(s.assignmentId)) : '—'}</td>
        <td class="num">${money(s.cost)}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn--ghost btn--sm" data-action="edit">Edit</button>
            <button class="btn btn--ghost btn--sm btn--danger" data-action="delete">Delete</button>
          </div>
        </td>
      </tr>`).join('') || `<tr><td colspan="7" class="text-muted" style="padding:20px;">No staff cost entries match these filters.</td></tr>`;

    tbody.querySelectorAll('tr[data-id]').forEach(row => {
      const id = row.dataset.id;
      row.querySelector('[data-action="edit"]').addEventListener('click', () => openStaffModal(id, list));
      row.querySelector('[data-action="delete"]').addEventListener('click', () => deleteStaff(id));
    });
  } catch (err) {
    reportError(err);
  }
}

async function deleteStaff(id) {
  if (!confirm('Delete this staff cost entry? This cannot be undone.')) return;
  try {
    await Api.del(`/api/staff/${id}`);
    toast('Staff cost entry deleted.');
    await refreshDashboard();
    renderStaffTable();
  } catch (err) {
    reportError(err);
  }
}

function toggleStaffAssignmentField() {
  const scope = document.getElementById('s-scope').value;
  document.getElementById('s-assignment-field').style.display = scope === 'dedicated' ? 'flex' : 'none';
}

function openStaffModal(id, cachedList) {
  const isEdit = !!id;
  document.getElementById('modal-staff-title').textContent = isEdit ? 'Edit staff cost entry' : 'Add staff cost entry';
  document.getElementById('s-id').value = id || '';
  if (isEdit) {
    const s = (cachedList || []).find(x => x.id === id);
    document.getElementById('s-name').value = s ? s.name : '';
    document.getElementById('s-designation').value = s ? s.designation : '';
    document.getElementById('s-manager').value = s ? s.managerId : '';
    document.getElementById('s-scope').value = s ? s.scope : 'dedicated';
    document.getElementById('s-assignment').value = s ? (s.assignmentId || '') : '';
    document.getElementById('s-cost').value = s ? s.cost : '';
    document.getElementById('s-period').value = (s && s.period) || '';
    document.getElementById('s-notes').value = (s && s.notes) || '';
  } else {
    document.getElementById('form-staff').reset();
    document.getElementById('s-scope').value = 'dedicated';
  }
  toggleStaffAssignmentField();
  openModal('modal-staff');
}

function initStaffForm() {
  document.getElementById('btn-add-staff').addEventListener('click', () => openStaffModal(null));
  document.getElementById('s-scope').addEventListener('change', toggleStaffAssignmentField);
  document.getElementById('form-staff').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('s-id').value;
    const scope = document.getElementById('s-scope').value;
    const payload = {
      name: document.getElementById('s-name').value.trim(),
      designation: document.getElementById('s-designation').value.trim(),
      managerId: document.getElementById('s-manager').value,
      scope,
      assignmentId: scope === 'dedicated' ? document.getElementById('s-assignment').value : null,
      cost: Number(document.getElementById('s-cost').value),
      period: document.getElementById('s-period').value,
      notes: document.getElementById('s-notes').value,
    };
    if (!payload.name) { showFormError('modal-staff', 'Staff name is required.'); return; }
    if (!payload.managerId) { showFormError('modal-staff', 'Choose a manager.'); return; }
    if (scope === 'dedicated' && !payload.assignmentId) { showFormError('modal-staff', 'Choose an assignment for a dedicated cost.'); return; }
    if (Number.isNaN(payload.cost) || payload.cost < 0) { showFormError('modal-staff', 'Enter a valid, non-negative cost.'); return; }
    try {
      if (id) {
        await Api.put(`/api/staff/${id}`, payload);
        toast('Staff cost entry updated.');
      } else {
        await Api.post('/api/staff', payload);
        toast('Staff cost entry added.');
      }
      closeModal('modal-staff');
      await refreshDashboard();
      if (document.getElementById('view-staff').classList.contains('is-active')) renderStaffTable();
    } catch (err) {
      showFormError('modal-staff', err.message);
    }
  });
}

/* ==================================================================== */
/* Revenue table                                                        */
/* ==================================================================== */

async function renderRevenueTable() {
  try {
    const assignmentId = document.getElementById('flt-r-assignment').value;
    const type = document.getElementById('flt-r-type').value;
    const qs = new URLSearchParams();
    if (assignmentId) qs.set('assignmentId', assignmentId);
    if (type) qs.set('type', type);
    const list = await Api.get('/api/revenue' + (qs.toString() ? '?' + qs.toString() : ''));
    const sorted = [...list].sort((a, b) => (a.date < b.date ? 1 : -1));
    const assignmentName = (aid) => {
      const a = State.assignmentsFlat.find(x => x.id === aid);
      return a ? a.name : '—';
    };
    const tbody = document.getElementById('tbl-revenue');
    tbody.innerHTML = sorted.map(r => `
      <tr data-id="${r.id}">
        <td>${fmtDate(r.date)}</td>
        <td>${escapeHtml(assignmentName(r.assignmentId))}</td>
        <td>${r.type === 'credit' ? '<span class="badge badge--loss">Credit note</span>' : '<span class="badge badge--neutral">Billing</span>'}</td>
        <td>${escapeHtml(r.voucherType || '')} ${r.mid ? '· ' + escapeHtml(r.mid) : ''}</td>
        <td>${escapeHtml(r.milestone || '')}</td>
        <td class="num">${r.type === 'credit' ? '−' : ''}${money(r.amount)}</td>
        <td>
          <div class="row-actions">
            <button class="btn btn--ghost btn--sm" data-action="edit">Edit</button>
            <button class="btn btn--ghost btn--sm btn--danger" data-action="delete">Delete</button>
          </div>
        </td>
      </tr>`).join('') || `<tr><td colspan="7" class="text-muted" style="padding:20px;">No revenue entries match these filters.</td></tr>`;

    tbody.querySelectorAll('tr[data-id]').forEach(row => {
      const id = row.dataset.id;
      row.querySelector('[data-action="edit"]').addEventListener('click', () => openRevenueModal(id, list));
      row.querySelector('[data-action="delete"]').addEventListener('click', () => deleteRevenue(id));
    });
  } catch (err) {
    reportError(err);
  }
}

async function deleteRevenue(id) {
  if (!confirm('Delete this revenue entry? This cannot be undone.')) return;
  try {
    await Api.del(`/api/revenue/${id}`);
    toast('Revenue entry deleted.');
    await refreshDashboard();
    renderRevenueTable();
  } catch (err) {
    reportError(err);
  }
}

function openRevenueModal(id, cachedList) {
  const isEdit = !!id;
  document.getElementById('modal-revenue-title').textContent = isEdit ? 'Edit revenue entry' : 'Add revenue entry';
  document.getElementById('r-id').value = id || '';
  if (isEdit) {
    const r = (cachedList || []).find(x => x.id === id);
    document.getElementById('r-assignment').value = r ? r.assignmentId : '';
    document.getElementById('r-date').value = r ? r.date : '';
    document.getElementById('r-type').value = r ? r.type : 'billing';
    document.getElementById('r-voucherType').value = (r && r.voucherType) || '';
    document.getElementById('r-mid').value = (r && r.mid) || '';
    document.getElementById('r-milestone').value = (r && r.milestone) || '';
    document.getElementById('r-amount').value = r ? r.amount : '';
    document.getElementById('r-notes').value = (r && r.notes) || '';
  } else {
    document.getElementById('form-revenue').reset();
    document.getElementById('r-date').value = new Date().toISOString().slice(0, 10);
  }
  openModal('modal-revenue');
}

function initRevenueForm() {
  document.getElementById('btn-add-revenue').addEventListener('click', () => openRevenueModal(null));
  document.getElementById('form-revenue').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('r-id').value;
    const payload = {
      assignmentId: document.getElementById('r-assignment').value,
      date: document.getElementById('r-date').value,
      type: document.getElementById('r-type').value,
      voucherType: document.getElementById('r-voucherType').value,
      mid: document.getElementById('r-mid').value,
      milestone: document.getElementById('r-milestone').value,
      amount: Number(document.getElementById('r-amount').value),
      notes: document.getElementById('r-notes').value,
    };
    if (!payload.assignmentId) { showFormError('modal-revenue', 'Choose an assignment.'); return; }
    if (Number.isNaN(payload.amount)) { showFormError('modal-revenue', 'Enter a valid amount.'); return; }
    try {
      if (id) {
        await Api.put(`/api/revenue/${id}`, payload);
        toast('Revenue entry updated.');
      } else {
        await Api.post('/api/revenue', payload);
        toast('Revenue entry added.');
      }
      closeModal('modal-revenue');
      await refreshDashboard();
      if (document.getElementById('view-revenue').classList.contains('is-active')) renderRevenueTable();
    } catch (err) {
      showFormError('modal-revenue', err.message);
    }
  });
}

/* ==================================================================== */
/* Filter wiring                                                        */
/* ==================================================================== */

function initFilters() {
  document.getElementById('flt-a-manager').addEventListener('change', renderAssignmentsTable);
  document.getElementById('flt-a-status').addEventListener('change', renderAssignmentsTable);
  document.getElementById('flt-s-manager').addEventListener('change', renderStaffTable);
  document.getElementById('flt-s-scope').addEventListener('change', renderStaffTable);
  document.getElementById('flt-r-assignment').addEventListener('change', renderRevenueTable);
  document.getElementById('flt-r-type').addEventListener('change', renderRevenueTable);
}

/* ==================================================================== */
/* Init                                                                 */
/* ==================================================================== */

async function init() {
  try {
    const meta = await Api.get('/api/meta');
    State.periodLabel = meta.sourcePeriod || '';
  } catch (e) { /* non-fatal */ }

  initNav();
  initModalChrome();
  initAssignmentForm();
  initStaffForm();
  initRevenueForm();
  initFilters();
  await bootstrap();
}

document.addEventListener('DOMContentLoaded', init);
