'use strict';

let CURRENT_USER = null;
let USERS = [];
let TASKS = [];
let statusChart, priorityChart, memberChart;

const PALETTE = {
  Pending: '#d97706',
  'In Progress': '#2563eb',
  Completed: '#16a34a',
  Low: '#94a3b8',
  Medium: '#2563eb',
  High: '#ea580c',
  Urgent: '#dc2626',
};

function toast(msg, isError) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show' + (isError ? ' error' : '');
  setTimeout(() => { el.className = 'toast'; }, 2600);
}

async function api(path, opts) {
  const res = await fetch(path, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts));
  let data = {};
  try { data = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

async function init() {
  const sessionData = await api('/api/session');
  if (!sessionData.user) { window.location.href = '/login.html'; return; }
  CURRENT_USER = sessionData.user;

  document.getElementById('whoLabel').textContent = CURRENT_USER.name;
  document.getElementById('roleBadge').textContent = CURRENT_USER.role === 'admin' ? 'Admin / Partner' : 'Team Member';
  if (CURRENT_USER.role === 'admin') {
    document.getElementById('teamTabBtn').style.display = 'inline-block';
  } else {
    // Team members land on a Tasks view scoped to their own work by
    // default (they can still untick this to see the full firm list).
    document.getElementById('filterMine').checked = true;
  }

  document.getElementById('logoutBtn').addEventListener('click', async () => {
    await api('/api/logout', { method: 'POST' });
    window.location.href = '/login.html';
  });

  setupTabs();
  setupTaskModal();
  setupUserModal();
  setupFilters();

  await loadUsers();
  await loadTasks();
  await loadDashboard();
}

function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      document.querySelectorAll('.tab-panel').forEach((p) => (p.style.display = 'none'));
      document.getElementById('tab-' + btn.dataset.tab).style.display = 'block';
      if (btn.dataset.tab === 'dashboard') loadDashboard();
      if (btn.dataset.tab === 'team') loadUsersTable();
    });
  });
}

// ---------------- Users ----------------
async function loadUsers() {
  const data = await api('/api/users');
  USERS = data.users;
  const checklist = document.getElementById('assigneeChecklist');
  const filterSel = document.getElementById('filterAssignee');
  checklist.innerHTML = '';
  filterSel.innerHTML = '<option value="">All team members</option>';
  USERS.filter((u) => u.active).forEach((u) => {
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" value="${u.id}"> ${escapeHtml(u.name)}${u.role === 'admin' ? ' (Admin)' : ''}`;
    checklist.appendChild(label);

    const opt2 = document.createElement('option');
    opt2.value = u.id; opt2.textContent = u.name;
    filterSel.appendChild(opt2);
  });
  if (CURRENT_USER.role === 'admin') loadUsersTable();
}

function loadUsersTable() {
  const tbody = document.getElementById('userTableBody');
  tbody.innerHTML = '';
  USERS.forEach((u) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(u.name)}</td>
      <td>${escapeHtml(u.username)}</td>
      <td>${u.role === 'admin' ? 'Admin / Partner' : 'Team Member'}</td>
      <td>${u.active ? '<span class="badge badge-Completed">Active</span>' : '<span class="badge badge-Pending">Inactive</span>'}</td>
      <td><button class="btn btn-ghost toggle-active" data-id="${u.id}" data-active="${u.active}">${u.active ? 'Deactivate' : 'Activate'}</button></td>
    `;
    tbody.appendChild(tr);
  });
  tbody.querySelectorAll('.toggle-active').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const id = btn.dataset.id;
      const active = btn.dataset.active === '1' ? false : true;
      try {
        await api('/api/users/' + id, { method: 'PUT', body: JSON.stringify({ active }) });
        toast('Team member updated.');
        await loadUsers();
      } catch (e) { toast(e.message, true); }
    });
  });
}

function setupUserModal() {
  const backdrop = document.getElementById('userModalBackdrop');
  document.getElementById('newUserBtn').addEventListener('click', () => {
    document.getElementById('userForm').reset();
    backdrop.classList.add('show');
  });
  document.getElementById('cancelUserBtn').addEventListener('click', () => backdrop.classList.remove('show'));
  document.getElementById('userForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await api('/api/users', {
        method: 'POST',
        body: JSON.stringify({
          name: document.getElementById('uName').value.trim(),
          username: document.getElementById('uUsername').value.trim(),
          password: document.getElementById('uPassword').value,
          role: document.getElementById('uRole').value,
        }),
      });
      toast('Team member created.');
      backdrop.classList.remove('show');
      await loadUsers();
    } catch (err) { toast(err.message, true); }
  });
}

// ---------------- Tasks ----------------
async function loadTasks() {
  const data = await api('/api/tasks');
  TASKS = data.tasks;
  renderTasks();
}

function currentFilters() {
  return {
    status: document.getElementById('filterStatus').value,
    priority: document.getElementById('filterPriority').value,
    assignee: document.getElementById('filterAssignee').value,
    mine: document.getElementById('filterMine').checked,
    search: document.getElementById('filterSearch').value.trim().toLowerCase(),
  };
}

function setupFilters() {
  ['filterStatus', 'filterPriority', 'filterAssignee', 'filterMine'].forEach((id) => {
    document.getElementById(id).addEventListener('change', renderTasks);
  });
  document.getElementById('filterSearch').addEventListener('input', renderTasks);
}

function isOverdue(t) {
  if (!t.due_date || t.status === 'Completed') return false;
  return t.due_date < new Date().toISOString().slice(0, 10);
}

function taskAssigneeIds(t) {
  return (t.assignees || []).map((a) => a.id);
}

function daysPending(t) {
  const startDate = t.assigned_date || t.created_at.slice(0, 10);
  const start = new Date(startDate + 'T00:00:00');
  const end = t.status === 'Completed' && t.completed_at ? new Date(t.completed_at) : new Date();
  const diffMs = end.setHours(0, 0, 0, 0) - start.setHours(0, 0, 0, 0);
  return Math.max(0, Math.round(diffMs / 86400000));
}

function renderTasks() {
  const f = currentFilters();
  const tbody = document.getElementById('taskTableBody');
  tbody.innerHTML = '';
  let rows = TASKS.filter((t) => {
    if (f.status && t.status !== f.status) return false;
    if (f.priority && t.priority !== f.priority) return false;
    if (f.assignee && !taskAssigneeIds(t).map(String).includes(String(f.assignee))) return false;
    if (f.mine && !taskAssigneeIds(t).includes(CURRENT_USER.id)) return false;
    if (f.search) {
      const hay = (t.client_name + ' ' + t.task_type).toLowerCase();
      if (!hay.includes(f.search)) return false;
    }
    return true;
  });

  document.getElementById('taskEmptyState').style.display = rows.length ? 'none' : 'block';

  rows.forEach((t) => {
    const tr = document.createElement('tr');
    if (isOverdue(t)) tr.classList.add('row-overdue');
    const canEdit = CURRENT_USER.role === 'admin' || t.assigned_by === CURRENT_USER.id || taskAssigneeIds(t).includes(CURRENT_USER.id);
    const pending = daysPending(t);
    const pendingClass = t.status === 'Completed' ? '' : (pending >= 7 ? 'danger' : (pending >= 3 ? 'warn' : ''));
    const pendingLabel = t.status === 'Completed' ? `Took ${pending}d` : `${pending}d`;
    const assigneeChips = (t.assignees || []).map((a) => `<span class="assignee-chip">${escapeHtml(a.name)}</span>`).join(' ');
    tr.innerHTML = `
      <td>${escapeHtml(t.client_name)}</td>
      <td>${escapeHtml(t.task_type)}</td>
      <td>${escapeHtml(t.assigned_date || t.created_at.slice(0, 10))}</td>
      <td>${t.due_date ? escapeHtml(t.due_date) : '<span class="small-muted">—</span>'}${isOverdue(t) ? ' <span class="badge badge-Urgent">Overdue</span>' : ''}</td>
      <td><span class="days-pending ${pendingClass}">${pendingLabel}</span></td>
      <td><span class="badge badge-${t.priority}">${t.priority}</span></td>
      <td></td>
      <td><div class="assignee-chips">${assigneeChips}</div></td>
      <td>${escapeHtml(t.assigned_by_name)}</td>
      <td>${t.notes ? `<span title="${escapeHtml(t.notes)}" class="small-muted">📝</span>` : ''}</td>
      <td></td>
    `;
    // Status cell (inline editable select)
    const statusTd = tr.children[6];
    if (canEdit) {
      const sel = document.createElement('select');
      sel.className = 'status-select';
      ['Pending', 'In Progress', 'Completed'].forEach((s) => {
        const opt = document.createElement('option');
        opt.value = s; opt.textContent = s;
        if (s === t.status) opt.selected = true;
        sel.appendChild(opt);
      });
      sel.addEventListener('change', async () => {
        try {
          await api('/api/tasks/' + t.id, { method: 'PUT', body: JSON.stringify({ status: sel.value }) });
          toast('Task status updated.');
          await loadTasks();
          await loadDashboard();
        } catch (e) { toast(e.message, true); }
      });
      statusTd.appendChild(sel);
    } else {
      statusTd.innerHTML = `<span class="badge badge-${t.status.replace(' ', '')}">${t.status}</span>`;
    }
    // Actions cell
    const actionsTd = tr.children[10];
    if (canEdit) {
      const editBtn = document.createElement('button');
      editBtn.className = 'icon-btn'; editBtn.title = 'Edit'; editBtn.textContent = '✏️';
      editBtn.addEventListener('click', () => openTaskModal(t));
      actionsTd.appendChild(editBtn);
    }
    if (CURRENT_USER.role === 'admin') {
      const delBtn = document.createElement('button');
      delBtn.className = 'icon-btn'; delBtn.title = 'Delete'; delBtn.textContent = '🗑️';
      delBtn.addEventListener('click', async () => {
        if (!confirm('Delete this task?')) return;
        try {
          await api('/api/tasks/' + t.id, { method: 'DELETE' });
          toast('Task deleted.');
          await loadTasks();
          await loadDashboard();
        } catch (e) { toast(e.message, true); }
      });
      actionsTd.appendChild(delBtn);
    }
    tbody.appendChild(tr);
  });
}

function setupTaskModal() {
  const backdrop = document.getElementById('taskModalBackdrop');
  document.getElementById('newTaskBtn').addEventListener('click', () => openTaskModal(null));
  document.getElementById('cancelTaskBtn').addEventListener('click', () => backdrop.classList.remove('show'));

  document.getElementById('taskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('taskId').value;
    const payload = {
      client_name: document.getElementById('clientName').value.trim(),
      task_type: document.getElementById('taskType').value.trim(),
      due_date: document.getElementById('dueDate').value || null,
      assigned_date: document.getElementById('assignedDate').value || null,
      priority: document.getElementById('priority').value,
      status: document.getElementById('status').value,
      notes: document.getElementById('notes').value.trim(),
    };
    const checklist = document.getElementById('assigneeChecklist');
    const canReassign = !checklist.dataset.locked;
    if (canReassign) {
      payload.assigned_to = Array.from(checklist.querySelectorAll('input[type="checkbox"]:checked')).map((cb) => cb.value);
      if (payload.assigned_to.length === 0) { toast('Select at least one team member to assign.', true); return; }
    }
    try {
      if (id) {
        await api('/api/tasks/' + id, { method: 'PUT', body: JSON.stringify(payload) });
        toast('Task updated.');
      } else {
        await api('/api/tasks', { method: 'POST', body: JSON.stringify(payload) });
        toast('Task created and assigned.');
      }
      backdrop.classList.remove('show');
      await loadTasks();
      await loadDashboard();
    } catch (err) { toast(err.message, true); }
  });
}

function openTaskModal(task) {
  document.getElementById('taskModalTitle').textContent = task ? 'Edit Task' : 'New Task';
  document.getElementById('taskId').value = task ? task.id : '';
  document.getElementById('clientName').value = task ? task.client_name : '';
  document.getElementById('taskType').value = task ? task.task_type : '';
  document.getElementById('assignedDate').value = task ? (task.assigned_date || task.created_at.slice(0, 10)) : new Date().toISOString().slice(0, 10);
  document.getElementById('dueDate').value = task && task.due_date ? task.due_date : '';
  document.getElementById('priority').value = task ? task.priority : 'Medium';
  document.getElementById('status').value = task ? task.status : 'Pending';
  document.getElementById('notes').value = task ? (task.notes || '') : '';

  const currentIds = task ? taskAssigneeIds(task) : [CURRENT_USER.id];
  const canReassign = !task || CURRENT_USER.role === 'admin' || task.assigned_by === CURRENT_USER.id;
  const checklist = document.getElementById('assigneeChecklist');
  checklist.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
    cb.checked = currentIds.map(String).includes(cb.value);
    cb.disabled = !canReassign;
  });
  if (canReassign) {
    delete checklist.dataset.locked;
    checklist.title = '';
  } else {
    checklist.dataset.locked = '1';
    checklist.title = 'Only the admin or the person who assigned this task can change who it\'s assigned to.';
  }

  document.getElementById('taskModalBackdrop').classList.add('show');
}

// ---------------- Dashboard ----------------
async function loadDashboard() {
  // Admins see the firm-wide dashboard (unchanged). Team members see a
  // personal dashboard scoped to just the tasks they're assigned to.
  const mineOnly = CURRENT_USER.role !== 'admin';
  const data = await api('/api/dashboard/stats' + (mineOnly ? '?mine=1' : ''));
  const statusMap = {}; data.byStatus.forEach((r) => (statusMap[r.status] = r.count));
  const priorityMap = {}; data.byPriority.forEach((r) => (priorityMap[r.priority] = r.count));

  const completed = statusMap['Completed'] || 0;
  const urgent = priorityMap['Urgent'] || 0;

  document.getElementById('statGrid').innerHTML = `
    <div class="stat-tile"><div class="num">${data.total}</div><div class="label">${mineOnly ? 'My Tasks' : 'Total Tasks'}</div></div>
    <div class="stat-tile overdue"><div class="num">${data.overdue}</div><div class="label">Overdue</div></div>
    <div class="stat-tile completed"><div class="num">${completed}</div><div class="label">Completed</div></div>
    <div class="stat-tile urgent"><div class="num">${urgent}</div><div class="label">Urgent Priority</div></div>
  `;

  document.getElementById('statusChartTitle').textContent = mineOnly ? 'My Tasks by Status' : 'Tasks by Status';
  document.getElementById('priorityChartTitle').textContent = mineOnly ? 'My Tasks by Priority' : 'Tasks by Priority';
  // The cross-team workload chart is only meaningful for the admin's
  // firm-wide view — hide it entirely on the personal dashboard.
  document.getElementById('memberChartCard').style.display = mineOnly ? 'none' : 'block';

  // Chart.js loads from the internet (see app.html) and can occasionally
  // fail if every fallback source is blocked. Don't leave the boxes blank
  // with no explanation — wait for it, and say so clearly if it never shows up.
  try {
    await window.chartReady;
  } catch (e) {
    const msg = '<div style="padding:24px;color:#64748b;font-size:13px;">Charts couldn\'t load — this needs an internet connection on this computer. Everything else in the app still works normally.</div>';
    document.getElementById('statusChart').closest('.chart-box').innerHTML = msg;
    document.getElementById('priorityChart').closest('.chart-box').innerHTML = msg;
    if (!mineOnly) {
      const mc = document.getElementById('memberChart');
      if (mc) mc.closest('.chart-box').innerHTML = msg;
    }
    return;
  }

  const statusLabels = ['Pending', 'In Progress', 'Completed'];
  const statusData = statusLabels.map((s) => statusMap[s] || 0);
  const priorityLabels = ['Low', 'Medium', 'High', 'Urgent'];
  const priorityData = priorityLabels.map((p) => priorityMap[p] || 0);

  if (statusChart) statusChart.destroy();
  statusChart = new Chart(document.getElementById('statusChart'), {
    type: 'doughnut',
    data: { labels: statusLabels, datasets: [{ data: statusData, backgroundColor: statusLabels.map((s) => PALETTE[s]) }] },
    options: { plugins: { legend: { position: 'bottom' } }, maintainAspectRatio: false },
  });

  if (priorityChart) priorityChart.destroy();
  priorityChart = new Chart(document.getElementById('priorityChart'), {
    type: 'bar',
    data: { labels: priorityLabels, datasets: [{ label: 'Tasks', data: priorityData, backgroundColor: priorityLabels.map((p) => PALETTE[p]) }] },
    options: { plugins: { legend: { display: false } }, maintainAspectRatio: false, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
  });

  if (memberChart) { memberChart.destroy(); memberChart = null; }
  if (!mineOnly) {
  memberChart = new Chart(document.getElementById('memberChart'), {
    type: 'bar',
    data: {
      labels: data.byMember.map((m) => m.name),
      datasets: [
        { label: 'Pending', data: data.byMember.map((m) => m.pending), backgroundColor: PALETTE['Pending'] },
        { label: 'In Progress', data: data.byMember.map((m) => m.in_progress), backgroundColor: PALETTE['In Progress'] },
        { label: 'Completed', data: data.byMember.map((m) => m.completed), backgroundColor: PALETTE['Completed'] },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { position: 'bottom' } },
      scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
    },
  });
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

init().catch((err) => {
  console.error(err);
  toast('Failed to load app: ' + err.message, true);
});
