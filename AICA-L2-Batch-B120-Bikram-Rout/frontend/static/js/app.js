// BRS Tool Frontend Controller
let currentView = 'dashboard';
let activeUser = {
  name: "System Administrator",
  role: "Administrator",
  username: "admin"
};

let currentAccountId = "ACC-01";
let currentPeriodId = "PER-01";

let selectedLedgerIds = new Set();
let selectedBankIds = new Set();
let activeChartInstances = {};

// On Initial Load
document.addEventListener('DOMContentLoaded', async () => {
  lucide.createIcons();
  await loadAccountList();
  await loadPeriodList();
  navigateTo('dashboard');
});

function showToast(title, message, isError = false) {
  const toast = document.getElementById('toast');
  const toastTitle = document.getElementById('toastTitle');
  const toastMsg = document.getElementById('toastMsg');
  const toastIcon = document.getElementById('toastIcon');

  toastTitle.textContent = title;
  toastMsg.textContent = message;
  toastIcon.innerHTML = isError ? 
    '<i data-lucide="alert-triangle" class="w-5 h-5 text-amber-400"></i>' : 
    '<i data-lucide="check-circle" class="w-5 h-5 text-emerald-400"></i>';
  lucide.createIcons();

  toast.classList.remove('translate-y-24', 'opacity-0');
  toast.classList.add('translate-y-0', 'opacity-100');

  setTimeout(() => {
    toast.classList.remove('translate-y-0', 'opacity-100');
    toast.classList.add('translate-y-24', 'opacity-0');
  }, 3500);
}

function switchUserRole(role) {
  activeUser.role = role;
  const roleNames = {
    "Administrator": "System Administrator",
    "Preparer": "John Reynolds (Preparer)",
    "Reviewer": "Elena Vasquez (Reviewer)",
    "Approver": "Robert Vance (Approver)",
    "Auditor": "Sarah Jenkins (Auditor)"
  };
  activeUser.name = roleNames[role] || role;
  document.getElementById('activeUserName').textContent = activeUser.name;
  document.getElementById('activeUserRole').textContent = role;
  document.getElementById('userAvatar').textContent = role.slice(0, 2).toUpperCase();
  showToast("Role Switched", `Active context is now: ${role}`);
  // Refresh current view
  navigateTo(currentView);
}

async function resetDemoData() {
  if (!confirm("Reset all database transactions to clean demonstration state (including Section 15 acceptance test)?")) return;
  try {
    const res = await fetch('/api/system/reset-demo', { method: 'POST' });
    const data = await res.json();
    showToast("Demo Data Reset", data.message);
    await loadAccountList();
    await loadPeriodList();
    navigateTo(currentView);
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function loadAccountList() {
  try {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    const select = document.getElementById('globalAccountSelect');
    select.innerHTML = '';
    data.accounts.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.id;
      const mask = `•••• ${a.account_number.slice(-4)}`;
      let tag = "";
      if (a.id === "ACC-01") tag = " [Acceptance Test]";
      if (a.id === "ACC-02") tag = " [Auto-Match Demo]";
      if (a.id === "ACC-03") tag = " [Reconciled]";
      opt.textContent = `${a.bank_name} - ${mask} (${a.currency})${tag}`;
      select.appendChild(opt);
    });
    if (data.accounts.some(a => a.id === currentAccountId)) {
      select.value = currentAccountId;
    } else if (data.accounts.length > 0) {
      currentAccountId = data.accounts[0].id;
      select.value = currentAccountId;
    }
  } catch (e) {
    console.error("Failed to load accounts", e);
  }
}

async function loadPeriodList() {
  try {
    const res = await fetch(`/api/periods?account_id=${currentAccountId}`);
    const data = await res.json();
    const select = document.getElementById('globalPeriodSelect');
    select.innerHTML = '';
    if (data.periods && data.periods.length > 0) {
      data.periods.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.period_name} (${p.status})`;
        select.appendChild(opt);
      });
      currentPeriodId = data.periods[0].id;
      select.value = currentPeriodId;
    }
  } catch (e) {
    console.error("Failed to load periods", e);
  }
}

async function onGlobalAccountChange() {
  currentAccountId = document.getElementById('globalAccountSelect').value;
  await loadPeriodList();
  navigateTo(currentView);
}

function onGlobalPeriodChange() {
  currentPeriodId = document.getElementById('globalPeriodSelect').value;
  navigateTo(currentView);
}

function formatMoney(amount, currency = 'USD') {
  if (amount === null || amount === undefined) return '$0.00';
  const num = typeof amount === 'number' ? amount : parseFloat(amount);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(num);
}

function navigateTo(viewId) {
  currentView = viewId;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.remove('bg-slate-800', 'text-white', 'border-l-4', 'border-brand-teal');
    el.classList.add('text-slate-300');
  });

  const activeBtn = document.getElementById(`nav-${viewId}`);
  if (activeBtn) {
    activeBtn.classList.add('bg-slate-800', 'text-white', 'border-l-4', 'border-brand-teal');
    activeBtn.classList.remove('text-slate-300');
  }

  // Cleanup charts
  for (const key in activeChartInstances) {
    if (activeChartInstances[key]) {
      activeChartInstances[key].destroy();
    }
  }
  activeChartInstances = {};

  const titles = {
    dashboard: "Reconciliation Executive Dashboard",
    workspace: "Side-by-Side Reconciliation Workspace",
    brs: "Bank Reconciliation Statement (BRS)",
    outstanding: "Outstanding Items & Aging Schedule",
    upload: "Document Upload & Processing Centre",
    validation: "Data Integrity & Mathematical Validation",
    approvals: "Period Governance & Segregation of Duties",
    companies: "Company Master Data",
    accounts: "Bank Account Master Registry",
    reports: "Audit & Management Reports",
    audit: "Immutable Audit Log",
    settings: "Reconciliation Matching Rules & Tolerances"
  };

  document.getElementById('pageTitle').textContent = titles[viewId] || "BRS Tool";
  const container = document.getElementById('contentContainer');

  switch (viewId) {
    case 'dashboard': renderDashboard(container); break;
    case 'workspace': renderWorkspace(container); break;
    case 'brs': renderBRS(container); break;
    case 'outstanding': renderOutstanding(container); break;
    case 'upload': renderUpload(container); break;
    case 'validation': renderValidation(container); break;
    case 'approvals': renderApprovals(container); break;
    case 'companies': renderCompanies(container); break;
    case 'accounts': renderAccounts(container); break;
    case 'reports': renderReports(container); break;
    case 'audit': renderAudit(container); break;
    case 'settings': renderSettings(container); break;
    default: renderDashboard(container);
  }

  setTimeout(() => lucide.createIcons(), 50);
}

// ----------------- MODULE 1: DASHBOARD -----------------
async function renderDashboard(container) {
  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading live executive reconciliation analytics...</div>`;
  try {
    const res = await fetch('/api/dashboard/summary');
    if (!res.ok) throw new Error('Server returned HTTP ' + res.status);
    const raw = await res.json();

    // Accept both the old and the new API key names and never leave a field undefined.
    const ag = raw.aging_buckets || {};
    const agOld = raw.aging || {};
    const num = (...v) => { for (const x of v) if (x !== undefined && x !== null) return Number(x) || 0; return 0; };
    const data = {
      ...raw,
      total_accounts: num(raw.total_accounts, raw.total_active_accounts),
      reconciled_accounts: num(raw.reconciled_accounts, raw.reconciled_approved_periods),
      unreconciled_accounts: num(raw.unreconciled_accounts),
      match_rate_percentage: num(raw.match_rate_percentage, raw.match_rate),
      matched_tx_count: num(raw.matched_tx_count, raw.matched_count),
      unmatched_tx_count: num(raw.unmatched_tx_count, raw.unmatched_count),
      gross_unmatched_exposure: num(raw.gross_unmatched_exposure, raw.unmatched_gross_exposure),
      total_residual_variance: num(raw.total_residual_variance),
      pending_periods: num(raw.pending_periods, num(raw.in_progress_periods) + num(raw.draft_periods)),
      currency_balances: raw.currency_balances || [],
      top_variances: (raw.top_variances || []).map(v => ({
        ...v,
        account_id: v.account_id || v.id,
        company_name: v.company_name || '-',
        account_number: String(v.account_number || ''),
      })),
      aging_buckets: {
        '0-30': num(ag['0-30'], agOld['0-30 Days']),
        '31-60': num(ag['31-60'], agOld['31-60 Days']),
        '61-90': num(ag['61-90'], agOld['61-90 Days']),
        '90+': num(ag['90+'], agOld['90+ Days']),
      },
    };

    container.innerHTML = `
      <!-- Acceptance Test Highlight Banner -->
      <div class="mb-6 bg-gradient-to-r from-slate-900 to-brand-navy rounded-xl p-5 text-white shadow-md flex items-center justify-between border border-slate-700">
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="bg-amber-500/20 text-amber-300 text-xs font-bold px-2.5 py-0.5 rounded border border-amber-500/30">Numeric Acceptance Test Loaded</span>
            <span class="text-xs text-slate-300">Prompt Specification Section 15</span>
          </div>
          <p class="text-sm text-slate-200">
            Account <b>JPMorgan Chase •••• 9482</b>: Ledger Balance $100k, Bank Balance $108.5k, Outstanding Payment -$10k, Deposit in Transit +$2k, Bank Charge -$500.
            <span class="text-amber-400 font-semibold">Exact Residual: $1,000.00 (Unreconciled)</span>
          </p>
        </div>
        <button onclick="currentAccountId='ACC-01'; document.getElementById('globalAccountSelect').value='ACC-01'; navigateTo('brs');" class="px-4 py-2 bg-brand-teal hover:bg-teal-600 text-white text-xs font-semibold rounded-lg shadow transition flex items-center space-x-1.5 flex-shrink-0">
          <span>View Acceptance BRS</span>
          <i data-lucide="arrow-right" class="w-4 h-4"></i>
        </button>
      </div>

      <!-- KPI Metric Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-6">
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Bank Accounts</span>
            <div class="w-8 h-8 rounded-lg bg-teal-50 text-brand-teal flex items-center justify-center">
              <i data-lucide="landmark" class="w-4 h-4"></i>
            </div>
          </div>
          <div class="text-2xl font-bold text-slate-800">${data.total_accounts}</div>
          <div class="text-xs text-emerald-600 font-medium mt-1 flex items-center space-x-1">
            <i data-lucide="check-circle" class="w-3.5 h-3.5"></i>
            <span>${data.reconciled_accounts} Balanced / ${data.unreconciled_accounts} With Variances</span>
          </div>
        </div>

        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Transaction Match Rate</span>
            <div class="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <i data-lucide="percent" class="w-4 h-4"></i>
            </div>
          </div>
          <div class="text-2xl font-bold text-slate-800">${data.match_rate_percentage}%</div>
          <div class="text-xs text-slate-500 font-medium mt-1">
            ${data.matched_tx_count} Matched / ${data.matched_tx_count + data.unmatched_tx_count} Total Items
          </div>
        </div>

        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Gross Unmatched Exposure</span>
            <div class="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <i data-lucide="alert-circle" class="w-4 h-4"></i>
            </div>
          </div>
          <div class="text-2xl font-bold text-slate-800">${formatMoney(data.gross_unmatched_exposure)}</div>
          <div class="text-xs text-amber-600 font-medium mt-1">
            ${data.unmatched_tx_count} Items Pending Matching
          </div>
        </div>

        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Residual Variance</span>
            <div class="w-8 h-8 rounded-lg bg-rose-50 text-rose-600 flex items-center justify-center">
              <i data-lucide="scale" class="w-4 h-4"></i>
            </div>
          </div>
          <div class="text-2xl font-bold ${data.total_residual_variance > 0 ? 'text-rose-600' : 'text-emerald-600'}">
            ${formatMoney(data.total_residual_variance)}
          </div>
          <div class="text-xs text-slate-500 font-medium mt-1">
            ${data.pending_periods} Periods in Workflow
          </div>
        </div>
      </div>

      <!-- Charts Row -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm lg:col-span-2">
          <h3 class="font-bold text-sm text-slate-800 mb-4 flex items-center space-x-2">
            <i data-lucide="bar-chart-3" class="w-4 h-4 text-brand-teal"></i>
            <span>Balances by Currency: Bank vs Oracle GL</span>
          </h3>
          <div class="h-64">
            <canvas id="currencyChart"></canvas>
          </div>
        </div>

        <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
          <h3 class="font-bold text-sm text-slate-800 mb-4 flex items-center space-x-2">
            <i data-lucide="pie-chart" class="w-4 h-4 text-amber-500"></i>
            <span>Outstanding Aging Buckets</span>
          </h3>
          <div class="h-64 flex items-center justify-center">
            <canvas id="agingChart"></canvas>
          </div>
        </div>
      </div>

      <!-- Top Accounts with Residual Variances Table -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-bold text-sm text-slate-800 flex items-center space-x-2">
            <i data-lucide="alert-triangle" class="w-4 h-4 text-amber-500"></i>
            <span>Account-Wise Reconciliation & Residual Differences</span>
          </h3>
          <span class="text-xs text-slate-400">Drill down directly into workspace</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-5 py-3">Account / Bank</th>
                <th class="px-5 py-3">Company</th>
                <th class="px-5 py-3">Period</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3 text-right">Residual Variance</th>
                <th class="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.top_variances.map(v => `
                <tr class="hover:bg-slate-50/80 transition">
                  <td class="px-5 py-3.5 font-medium text-slate-800">
                    <div>${v.bank_name}</div>
                    <div class="text-[11px] text-slate-400 font-mono">•••• ${v.account_number.slice(-4)} (${v.currency})</div>
                  </td>
                  <td class="px-5 py-3.5 text-slate-600">${v.company_name}</td>
                  <td class="px-5 py-3.5 font-mono text-slate-600">${v.period_name}</td>
                  <td class="px-5 py-3.5">
                    <span class="px-2 py-0.5 rounded-full text-[10px] font-bold ${
                      v.status === 'Approved' ? 'bg-emerald-100 text-emerald-800' :
                      v.status === 'In Progress' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-800'
                    }">${v.status}</span>
                  </td>
                  <td class="px-5 py-3.5 text-right font-mono font-bold ${Math.abs(v.residual_diff) > 0 ? 'text-amber-600' : 'text-emerald-600'}">
                    ${formatMoney(v.residual_diff, v.currency)}
                  </td>
                  <td class="px-5 py-3.5 text-right">
                    <button onclick="currentAccountId='${v.account_id}'; currentPeriodId='${v.period_id}'; document.getElementById('globalAccountSelect').value='${v.account_id}'; navigateTo('workspace');" class="text-brand-teal hover:text-teal-700 font-semibold text-xs">
                      Reconcile &rarr;
                    </button>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Render Currency Chart
    const ctxC = document.getElementById('currencyChart').getContext('2d');
    activeChartInstances.currency = new Chart(ctxC, {
      type: 'bar',
      data: {
        labels: data.currency_balances.map(c => c.currency),
        datasets: [
          {
            label: 'Bank Statement Balance',
            data: data.currency_balances.map(c => c.total_bank),
            backgroundColor: '#0D9488',
            borderRadius: 6
          },
          {
            label: 'Oracle GL Balance',
            data: data.currency_balances.map(c => c.total_ledger),
            backgroundColor: '#0F172A',
            borderRadius: 6
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top' } }
      }
    });

    // Render Aging Chart
    const ctxA = document.getElementById('agingChart').getContext('2d');
    activeChartInstances.aging = new Chart(ctxA, {
      type: 'doughnut',
      data: {
        labels: ['0-30 Days', '31-60 Days', '61-90 Days', '90+ Days'],
        datasets: [{
          data: [
            data.aging_buckets['0-30'],
            data.aging_buckets['31-60'],
            data.aging_buckets['61-90'],
            data.aging_buckets['90+']
          ],
          backgroundColor: ['#10B981', '#3B82F6', '#F59E0B', '#EF4444'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom' } }
      }
    });

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load dashboard: ${err.message}</div>`;
  }
}

// ----------------- MODULE 2: RECONCILIATION WORKSPACE -----------------
async function renderWorkspace(container) {
  selectedLedgerIds.clear();
  selectedBankIds.clear();

  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading side-by-side reconciliation workspace...</div>`;
  try {
    const res = await fetch(`/api/reconciliation/${currentAccountId}/${currentPeriodId}`);
    const data = await res.json();
    const brs = data.brs;

    container.innerHTML = `
      <!-- Workspace Toolbar & BRS Mini Bar -->
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-5 flex flex-wrap items-center justify-between gap-4">
        <div class="flex items-center space-x-4">
          <div class="text-xs">
            <span class="text-slate-400 uppercase font-medium">Bank Statement:</span>
            <span class="font-bold text-slate-800 ml-1 font-mono">${formatMoney(brs.bank_closing_balance, brs.currency)}</span>
          </div>
          <div class="text-xs">
            <span class="text-slate-400 uppercase font-medium">Oracle GL:</span>
            <span class="font-bold text-slate-800 ml-1 font-mono">${formatMoney(brs.ledger_closing_balance, brs.currency)}</span>
          </div>
          <div class="text-xs">
            <span class="text-slate-400 uppercase font-medium">Residual Diff:</span>
            <span class="font-bold font-mono ml-1 ${Math.abs(brs.residual_difference) > 0 ? 'text-amber-600' : 'text-emerald-600'}">
              ${formatMoney(brs.residual_difference, brs.currency)}
            </span>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold ${brs.is_reconciled ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'}">
            ${brs.is_reconciled ? 'RECONCILED' : 'UNRECONCILED'}
          </span>
        </div>

        <div class="flex items-center space-x-2">
          <input type="text" id="workspaceSearch" placeholder="Search ref, desc..." oninput="filterWorkspaceItems()" class="text-xs px-3 py-1.5 border border-slate-300 rounded-lg w-44 focus:outline-none focus:border-brand-teal">
          
          <select id="workspaceStatusFilter" onchange="filterWorkspaceItems()" class="text-xs px-3 py-1.5 border border-slate-300 rounded-lg bg-white focus:outline-none">
            <option value="All">All Statuses</option>
            <option value="Unmatched" selected>Unmatched Only</option>
            <option value="Matched">Matched Only</option>
          </select>

          <button onclick="triggerAutoMatch()" class="flex items-center space-x-1 px-3 py-1.5 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow-sm transition">
            <i data-lucide="zap" class="w-3.5 h-3.5"></i>
            <span>Run Auto-Reconcile</span>
          </button>
        </div>
      </div>

      <!-- Suggested Matches Review Banner (if any) -->
      ${data.match_groups.filter(mg => mg.status === 'Suggested').map(smg => `
        <div class="mb-5 bg-amber-50 border border-amber-300 rounded-xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-sm">
          <div class="flex items-center space-x-3">
            <div class="w-8 h-8 rounded-lg bg-amber-100 text-amber-800 flex items-center justify-center flex-shrink-0">
              <i data-lucide="help-circle" class="w-5 h-5"></i>
            </div>
            <div>
              <div class="flex items-center space-x-2">
                <span class="bg-amber-200 text-amber-900 text-[10px] font-bold px-2 py-0.5 rounded">SUGGESTED MATCH REVIEW</span>
                <span class="font-mono text-xs text-slate-600 font-bold">${smg.id}</span>
              </div>
              <p class="text-xs text-slate-700 mt-0.5">${smg.rule_name} &bull; ${smg.notes || 'Fuzzy token similarity'} &bull; ${smg.item_count} items</p>
            </div>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="confirmSuggested('${smg.id}')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1">
              <i data-lucide="check" class="w-3.5 h-3.5"></i>
              <span>Confirm Match</span>
            </button>
            <button onclick="rejectSuggested('${smg.id}')" class="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1">
              <i data-lucide="x" class="w-3.5 h-3.5"></i>
              <span>Reject Suggestion</span>
            </button>
          </div>
        </div>
      `).join('')}

      <!-- Side-by-Side Dual Pane Container -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-5 mb-24">
        
        <!-- LEFT: Oracle General Ledger Transactions -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[520px]">
          <div class="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between rounded-t-xl">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
              <h3 class="font-bold text-xs uppercase tracking-wider text-slate-700">Oracle General Ledger</h3>
            </div>
            <span class="text-xs text-slate-500 font-medium" id="ledgerCount">${data.ledger_transactions.length} Records</span>
          </div>

          <div class="flex-1 overflow-y-auto custom-scroll p-2 divide-y divide-slate-100" id="ledgerList">
            ${data.ledger_transactions.map(t => renderTxRow(t, 'ledger')).join('')}
          </div>
        </div>

        <!-- RIGHT: Bank Statement Transactions -->
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col h-[520px]">
          <div class="px-4 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between rounded-t-xl">
            <div class="flex items-center space-x-2">
              <span class="w-2.5 h-2.5 rounded-full bg-brand-teal"></span>
              <h3 class="font-bold text-xs uppercase tracking-wider text-slate-700">Bank Statement Lines</h3>
            </div>
            <span class="text-xs text-slate-500 font-medium" id="bankCount">${data.bank_transactions.length} Records</span>
          </div>

          <div class="flex-1 overflow-y-auto custom-scroll p-2 divide-y divide-slate-100" id="bankList">
            ${data.bank_transactions.map(t => renderTxRow(t, 'bank')).join('')}
          </div>
        </div>

      </div>

      <!-- Active Match Groups Table Panel -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
          <h3 class="font-bold text-sm text-slate-800 flex items-center space-x-2">
            <i data-lucide="link" class="w-4 h-4 text-brand-teal"></i>
            <span>Active Reconciliation Match Groups (${data.match_groups.length})</span>
          </h3>
          <span class="text-xs text-slate-400">Atomic match allocations & unmatch audit</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-4 py-2.5">Group ID</th>
                <th class="px-4 py-2.5">Rule / Type</th>
                <th class="px-4 py-2.5">Items</th>
                <th class="px-4 py-2.5">Matched At</th>
                <th class="px-4 py-2.5">Matched By</th>
                <th class="px-4 py-2.5">Notes</th>
                <th class="px-4 py-2.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.match_groups.map(mg => `
                <tr class="hover:bg-slate-50">
                  <td class="px-4 py-3 font-mono font-bold ${mg.status === 'Suggested' ? 'text-amber-600' : 'text-brand-teal'}">${mg.id}</td>
                  <td class="px-4 py-3 font-medium text-slate-800">
                    ${mg.rule_name} 
                    <span class="text-[10px] text-slate-400">(${mg.match_type})</span>
                    ${mg.status === 'Suggested' ? '<span class="ml-1 text-[10px] font-bold bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded">Suggested</span>' : ''}
                  </td>
                  <td class="px-4 py-3 font-medium">${mg.item_count} items</td>
                  <td class="px-4 py-3 text-slate-500">${mg.matched_at.slice(0, 16).replace('T', ' ')}</td>
                  <td class="px-4 py-3 text-slate-600">${mg.matched_by}</td>
                  <td class="px-4 py-3 text-slate-500">${mg.notes || '-'}</td>
                  <td class="px-4 py-3 text-right">
                    <button onclick="triggerUnmatch('${mg.id}')" class="text-rose-600 hover:text-rose-800 font-semibold text-xs flex items-center space-x-1 ml-auto">
                      <i data-lucide="unlink" class="w-3 h-3"></i>
                      <span>Unmatch</span>
                    </button>
                  </td>
                </tr>
              `).join('')}
              ${data.match_groups.length === 0 ? `<tr><td colspan="7" class="px-4 py-4 text-center text-slate-400">No match groups created yet. Run auto-match or select items for manual matching.</td></tr>` : ''}
            </tbody>
          </table>
        </div>
      </div>

      <!-- Floating Selection Dock -->
      <div id="selectionDock" class="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-brand-navy text-white px-6 py-3.5 rounded-2xl shadow-2xl flex items-center space-x-8 border border-slate-700 z-40 transition duration-200">
        <div class="flex items-center space-x-6 text-xs">
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Selected Ledger</span>
            <span id="dockLedgerSum" class="font-mono font-bold text-sm text-indigo-300">$0.00 (0 items)</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Selected Bank</span>
            <span id="dockBankSum" class="font-mono font-bold text-sm text-teal-300">$0.00 (0 items)</span>
          </div>
          <div class="border-l border-slate-700 pl-6">
            <span class="text-slate-400 block text-[10px] uppercase font-semibold">Variance Delta</span>
            <span id="dockDeltaSum" class="font-mono font-bold text-sm text-emerald-400">$0.00</span>
          </div>
        </div>

        <div class="flex items-center space-x-3">
          <button onclick="clearSelection()" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition">
            Clear
          </button>
          <button id="btnPartialMatch" onclick="executePartialMatch()" class="hidden px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
            <i data-lucide="pie-chart" class="w-3.5 h-3.5"></i>
            <span>Partial Allocate</span>
          </button>
          <button id="btnManualMatch" onclick="executeManualMatch()" class="px-4 py-1.5 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
            <i data-lucide="check" class="w-3.5 h-3.5"></i>
            <span>Confirm Match</span>
          </button>
        </div>
      </div>
    `;

    filterWorkspaceItems();
    updateSelectionDock();

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load workspace: ${err.message}</div>`;
  }
}

function renderTxRow(t, type) {
  const isMatched = t.recon_status === 'Matched';
  const signedAmt = t.signed_amount;
  const isPositive = signedAmt > 0;
  
  return `
    <div class="p-3 hover:bg-slate-50 flex items-start justify-between space-x-3 text-xs tx-item" data-id="${t.id}" data-type="${type}" data-status="${t.recon_status}" data-search="${(t.description + ' ' + (t.reference || '')).toLowerCase()}" data-amount="${signedAmt}">
      <div class="flex items-start space-x-3">
        ${!isMatched ? `
          <input type="checkbox" onchange="toggleSelectTx('${t.id}', '${type}', this.checked)" class="mt-1 rounded text-brand-teal focus:ring-0 cursor-pointer">
        ` : `
          <span class="mt-1 text-emerald-500"><i data-lucide="check" class="w-3.5 h-3.5"></i></span>
        `}
        <div>
          <div class="font-medium text-slate-800">${t.description}</div>
          <div class="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
            <span class="font-mono">${t.tx_date}</span>
            ${t.reference ? `<span class="bg-slate-100 text-slate-600 px-1.5 rounded font-mono">${t.reference}</span>` : ''}
            ${t.cheque_number ? `<span class="bg-amber-50 text-amber-700 px-1.5 rounded font-mono">${t.cheque_number}</span>` : ''}
          </div>
        </div>
      </div>

      <div class="text-right flex-shrink-0">
        <div class="font-mono font-bold ${isPositive ? 'text-emerald-600' : 'text-slate-800'}">
          ${formatMoney(signedAmt, t.currency)}
        </div>
        <div class="mt-0.5">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-semibold ${
            isMatched ? 'bg-emerald-100 text-emerald-800' :
            t.recon_status === 'Suggested Match' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-600'
          }">${t.recon_status}</span>
        </div>
      </div>
    </div>
  `;
}

function filterWorkspaceItems() {
  const search = (document.getElementById('workspaceSearch')?.value || '').toLowerCase();
  const filter = document.getElementById('workspaceStatusFilter')?.value || 'All';

  document.querySelectorAll('.tx-item').forEach(el => {
    const s = el.getAttribute('data-search');
    const st = el.getAttribute('data-status');
    const matchSearch = !search || s.includes(search);
    const matchStatus = filter === 'All' || st === filter;
    el.style.display = (matchSearch && matchStatus) ? 'flex' : 'none';
  });
}

function toggleSelectTx(id, type, checked) {
  if (type === 'ledger') {
    if (checked) selectedLedgerIds.add(id);
    else selectedLedgerIds.delete(id);
  } else {
    if (checked) selectedBankIds.add(id);
    else selectedBankIds.delete(id);
  }
  updateSelectionDock();
}

function clearSelection() {
  selectedLedgerIds.clear();
  selectedBankIds.clear();
  document.querySelectorAll('.tx-item input[type="checkbox"]').forEach(cb => cb.checked = false);
  updateSelectionDock();
}

function updateSelectionDock() {
  let lSum = 0;
  let bSum = 0;

  selectedLedgerIds.forEach(id => {
    const el = document.querySelector(`.tx-item[data-id="${id}"]`);
    if (el) lSum += parseFloat(el.getAttribute('data-amount') || 0);
  });

  selectedBankIds.forEach(id => {
    const el = document.querySelector(`.tx-item[data-id="${id}"]`);
    if (el) bSum += parseFloat(el.getAttribute('data-amount') || 0);
  });

  const delta = (lSum - bSum);
  const dock = document.getElementById('selectionDock');
  if (!dock) return;

  document.getElementById('dockLedgerSum').textContent = `${formatMoney(lSum)} (${selectedLedgerIds.size})`;
  document.getElementById('dockBankSum').textContent = `${formatMoney(bSum)} (${selectedBankIds.size})`;
  
  const deltaEl = document.getElementById('dockDeltaSum');
  deltaEl.textContent = formatMoney(delta);
  if (Math.abs(delta) < 0.001) {
    deltaEl.className = "font-mono font-bold text-sm text-emerald-400";
  } else {
    deltaEl.className = "font-mono font-bold text-sm text-amber-400";
  }

  // Button disabled if not equal or no selection
  const btn = document.getElementById('btnManualMatch');
  if (selectedLedgerIds.size > 0 && selectedBankIds.size > 0 && Math.abs(delta) < 0.001) {
    btn.disabled = false;
    btn.classList.remove('opacity-50', 'cursor-not-allowed');
  } else {
    btn.disabled = true;
    btn.classList.add('opacity-50', 'cursor-not-allowed');
  }

  // Partial match button enabled only when exactly 1 ledger and 1 bank item are selected
  const btnPartial = document.getElementById('btnPartialMatch');
  if (btnPartial) {
    if (selectedLedgerIds.size === 1 && selectedBankIds.size === 1) {
      btnPartial.classList.remove('hidden');
      btnPartial.disabled = false;
    } else {
      btnPartial.classList.add('hidden');
      btnPartial.disabled = true;
    }
  }
}

async function executePartialMatch() {
  if (selectedLedgerIds.size !== 1 || selectedBankIds.size !== 1) {
    alert("Please select exactly 1 Ledger item and 1 Bank item for partial allocation.");
    return;
  }
  const ledgerId = Array.from(selectedLedgerIds)[0];
  const bankId = Array.from(selectedBankIds)[0];
  const lEl = document.querySelector(`.tx-item[data-id="${ledgerId}"]`);
  const bEl = document.querySelector(`.tx-item[data-id="${bankId}"]`);
  const lAmt = Math.abs(parseFloat(lEl.getAttribute('data-amount') || 0));
  const bAmt = Math.abs(parseFloat(bEl.getAttribute('data-amount') || 0));
  const maxAlloc = Math.min(lAmt, bAmt);

  const allocInput = prompt(`Enter amount to allocate (Max: ${maxAlloc.toFixed(2)}):`, maxAlloc.toFixed(2));
  if (!allocInput) return;
  const allocAmount = parseFloat(allocInput);
  if (isNaN(allocAmount) || allocAmount <= 0) {
    showToast("Invalid Amount", "Please enter a valid positive number", true);
    return;
  }

  try {
    const res = await fetch('/api/reconciliation/partial-match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: currentAccountId,
        period_id: currentPeriodId,
        ledger_id: ledgerId,
        bank_id: bankId,
        allocated_amount: allocAmount,
        user: activeUser.name,
        notes: "Partial allocation via workspace"
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Partial Match Confirmed", `Allocated $${allocAmount.toFixed(2)}. Remaining: Ledger $${data.ledger_remaining.toFixed(2)}, Bank $${data.bank_remaining.toFixed(2)}`);
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Allocation Failed", data.detail || "Partial match failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function confirmSuggested(mgId) {
  try {
    const res = await fetch('/api/reconciliation/confirm-suggested', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ match_group_id: mgId, user: activeUser.name })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Suggestion Confirmed", "Match marked as Matched and confirmed");
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Failed to confirm suggestion", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function rejectSuggested(mgId) {
  const reason = prompt("Enter reason for rejecting this suggested match:", "Unrelated counterparty") || "Rejected by user";
  try {
    const res = await fetch('/api/reconciliation/reject-suggested', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ match_group_id: mgId, user: activeUser.name, reason: reason })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Suggestion Rejected", "Transactions reset to Unmatched status");
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Failed to reject suggestion", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function triggerAutoMatch() {
  try {
    showToast("Reconciliation Started", "Running multi-stage deterministic rules...");
    const res = await fetch(`/api/reconciliation/auto-match?account_id=${currentAccountId}&period_id=${currentPeriodId}&user=${encodeURIComponent(activeUser.name)}`, {
      method: 'POST'
    });
    const data = await res.json();
    if (data.success) {
      showToast("Auto-Reconcile Finished", `Matched ${data.matches_created} groups ($${data.matched_amount.toLocaleString()})`);
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.error || "Matching failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function executeManualMatch() {
  try {
    const res = await fetch('/api/reconciliation/manual-match', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: currentAccountId,
        period_id: currentPeriodId,
        ledger_ids: Array.from(selectedLedgerIds),
        bank_ids: Array.from(selectedBankIds),
        user: activeUser.name,
        notes: "Manual match confirmed in workspace"
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Manual Match Confirmed", `Group ID: ${data.match_group_id}`);
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Match Rejected", data.detail || "Sums do not match", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function triggerUnmatch(mgId) {
  const reason = prompt("Enter mandatory audit reason for unmatching this group:", "Incorrect entry pair");
  if (!reason) return;

  try {
    const res = await fetch('/api/reconciliation/unmatch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        match_group_id: mgId,
        user: activeUser.name,
        reason: reason
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Unmatched", `Reverted ${data.reverted_count} transactions to Unmatched status`);
      renderWorkspace(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Unmatch failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

// ----------------- MODULE 3: BANK RECONCILIATION STATEMENT -----------------
async function renderBRS(container) {
  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading Bank Reconciliation Statement...</div>`;
  try {
    const res = await fetch(`/api/brs/${currentAccountId}/${currentPeriodId}`);
    const brs = await res.json();

    container.innerHTML = `
      <div class="max-w-4xl mx-auto bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-12">
        
        <!-- Header Banner -->
        <div class="bg-brand-navy text-white p-6 flex items-center justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <span class="bg-teal-500/20 text-teal-300 text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider">Official Finance Statement</span>
              <span class="text-xs text-slate-400 font-mono">${brs.period_name}</span>
            </div>
            <h2 class="text-xl font-bold mt-1">${brs.bank_name} Bank Reconciliation Statement</h2>
            <p class="text-xs text-slate-300 mt-0.5">Account: •••• ${brs.account_number.slice(-4)} (${brs.currency}) &nbsp;|&nbsp; Period Status: <span class="font-bold text-amber-300">${brs.period_status}</span></p>
          </div>

          <div class="text-right">
            <span class="inline-block px-3 py-1 rounded-full text-xs font-bold ${brs.is_reconciled ? 'bg-emerald-500 text-white' : 'bg-amber-500 text-slate-900'}">
              ${brs.is_reconciled ? 'BALANCED & RECONCILED' : 'UNRESOLVED RESIDUAL'}
            </span>
            <div class="text-[11px] text-slate-400 mt-1 font-mono">Precision: Exact Decimal</div>
          </div>
        </div>

        <!-- Statement Calculation Grid -->
        <div class="p-6">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b-2 border-slate-800 text-slate-500 uppercase font-semibold">
                <th class="py-3">Statement Line Item</th>
                <th class="py-3 text-right">Amount (${brs.currency})</th>
                <th class="py-3 pl-6">Cash Sign & Logic</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              
              <!-- Section A: Bank Perspective -->
              <tr class="bg-slate-50/60 font-semibold text-slate-800">
                <td class="py-3.5 pl-2 font-bold text-slate-900">A. Bank Statement Closing Balance</td>
                <td class="py-3.5 text-right font-mono font-bold text-slate-900">${formatMoney(brs.bank_closing_balance, brs.currency)}</td>
                <td class="py-3.5 pl-6 text-slate-500 text-[11px]">Confirmed closing balance per bank statement file</td>
              </tr>
              <tr>
                <td class="py-2.5 pl-6 text-slate-600">Add / (Less): Outstanding Cheques & Payments</td>
                <td class="py-2.5 text-right font-mono font-medium text-rose-600">${formatMoney(brs.ledger_payments_in_transit, brs.currency)}</td>
                <td class="py-2.5 pl-6 text-slate-400 text-[11px]">Signed ledger disbursements not yet cleared at bank</td>
              </tr>
              <tr>
                <td class="py-2.5 pl-6 text-slate-600">Add / (Less): Deposits in Transit</td>
                <td class="py-2.5 text-right font-mono font-medium text-emerald-600">${formatMoney(brs.ledger_deposits_in_transit, brs.currency)}</td>
                <td class="py-2.5 pl-6 text-slate-400 text-[11px]">Signed ledger receipts not yet cleared at bank</td>
              </tr>
              <tr class="bg-teal-50/50 font-bold border-y border-teal-100">
                <td class="py-3 pl-2 text-brand-teal">ADJUSTED BANK BALANCE</td>
                <td class="py-3 text-right font-mono text-brand-teal text-sm">${formatMoney(brs.adjusted_bank_balance, brs.currency)}</td>
                <td class="py-3 pl-6 text-teal-700 text-[11px]">Bank Closing + All Ledger Unmatched Movements</td>
              </tr>

              <!-- Section B: Ledger Perspective -->
              <tr class="bg-slate-50/60 font-semibold text-slate-800">
                <td class="py-3.5 pl-2 font-bold text-slate-900 pt-6">B. Oracle General Ledger Closing Balance</td>
                <td class="py-3.5 text-right font-mono font-bold text-slate-900 pt-6">${formatMoney(brs.ledger_closing_balance, brs.currency)}</td>
                <td class="py-3.5 pl-6 text-slate-500 text-[11px] pt-6">Confirmed closing balance per Oracle Cash GL</td>
              </tr>
              <tr>
                <td class="py-2.5 pl-6 text-slate-600">Add / (Less): Unrecorded Bank Charges & Fees</td>
                <td class="py-2.5 text-right font-mono font-medium text-rose-600">${formatMoney(brs.bank_charges, brs.currency)}</td>
                <td class="py-2.5 pl-6 text-slate-400 text-[11px]">Direct bank debits/fees not yet recorded in Oracle</td>
              </tr>
              <tr>
                <td class="py-2.5 pl-6 text-slate-600">Add / (Less): Unrecorded Bank Interest & Credits</td>
                <td class="py-2.5 text-right font-mono font-medium text-emerald-600">${formatMoney(brs.bank_interest_credits, brs.currency)}</td>
                <td class="py-2.5 pl-6 text-slate-400 text-[11px]">Direct bank receipts/interest not yet recorded in Oracle</td>
              </tr>
              <tr class="bg-indigo-50/50 font-bold border-y border-indigo-100">
                <td class="py-3 pl-2 text-indigo-900">ADJUSTED LEDGER BALANCE</td>
                <td class="py-3 text-right font-mono text-indigo-900 text-sm">${formatMoney(brs.adjusted_ledger_balance, brs.currency)}</td>
                <td class="py-3 pl-6 text-indigo-700 text-[11px]">Ledger Closing + All Bank Unmatched Movements</td>
              </tr>

              <!-- Section C: Residual Variance -->
              <tr class="font-bold border-t-2 border-slate-800 ${Math.abs(brs.residual_difference) > 0 ? 'bg-amber-50' : 'bg-emerald-50'}">
                <td class="py-4 pl-2 text-slate-900 text-sm">RESIDUAL UNRECONCILED VARIANCE</td>
                <td class="py-4 text-right font-mono text-base ${Math.abs(brs.residual_difference) > 0 ? 'text-amber-700' : 'text-emerald-700'}">
                  ${formatMoney(brs.residual_difference, brs.currency)}
                </td>
                <td class="py-4 pl-6 text-[11px] ${Math.abs(brs.residual_difference) > 0 ? 'text-amber-800' : 'text-emerald-800'}">
                  ${brs.is_reconciled ? 'Exact Zero Residual: Reconciliation is 100% Complete!' : 'Variance Detected: Cannot force to zero. Mandatory review required.'}
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Numeric Acceptance Formula Card -->
          <div class="mt-6 bg-slate-50 rounded-xl p-4 border border-slate-200 text-xs text-slate-600">
            <h4 class="font-bold text-slate-800 mb-1 flex items-center space-x-1.5">
              <i data-lucide="calculator" class="w-4 h-4 text-brand-teal"></i>
              <span>Reconciliation Formula Breakdown</span>
            </h4>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2 font-mono text-[11px]">
              <div class="bg-white p-2.5 rounded border border-slate-200">
                <span class="text-slate-400 block">Adjusted Bank:</span>
                ${brs.bank_closing_balance.toLocaleString()} + (${brs.ledger_unmatched_sum.toLocaleString()}) = <b>${brs.adjusted_bank_balance.toLocaleString()}</b>
              </div>
              <div class="bg-white p-2.5 rounded border border-slate-200">
                <span class="text-slate-400 block">Adjusted Ledger:</span>
                ${brs.ledger_closing_balance.toLocaleString()} + (${brs.bank_unmatched_sum.toLocaleString()}) = <b>${brs.adjusted_ledger_balance.toLocaleString()}</b>
              </div>
            </div>
          </div>

          <!-- Actions Toolbar -->
          <div class="mt-6 flex items-center justify-between border-t border-slate-200 pt-5">
            <div class="flex items-center space-x-2">
              <button onclick="downloadReport('excel')" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
                <i data-lucide="file-spreadsheet" class="w-4 h-4"></i>
                <span>Download Multi-Sheet Excel</span>
              </button>
              <button onclick="downloadReport('pdf')" class="px-4 py-2 bg-brand-navy hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
                <i data-lucide="file-text" class="w-4 h-4"></i>
                <span>Download PDF Statement</span>
              </button>
            </div>

            <div class="flex items-center space-x-2">
              <button onclick="submitWorkflowAction('${brs.period_id}', 'Approved')" class="px-4 py-2 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-1.5">
                <i data-lucide="check-circle-2" class="w-4 h-4"></i>
                <span>Approve & Sign-off</span>
              </button>
            </div>
          </div>
        </div>

      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load BRS: ${err.message}</div>`;
  }
}

// ----------------- MODULE 4: OUTSTANDING ITEMS -----------------
async function renderOutstanding(container) {
  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading outstanding items schedule...</div>`;
  try {
    const res = await fetch(`/api/reconciliation/${currentAccountId}/${currentPeriodId}`);
    const data = await res.json();
    const unmatched = [
      ...data.ledger_transactions.filter(t => t.recon_status !== 'Matched'),
      ...data.bank_transactions.filter(t => t.recon_status !== 'Matched')
    ];

    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Outstanding Items Schedule & Categorization</h3>
            <p class="text-xs text-slate-400">Unreconciled timing items carried forward without duplication</p>
          </div>
          <span class="text-xs font-semibold px-2.5 py-1 bg-amber-50 text-amber-700 border border-amber-200 rounded-full">
            ${unmatched.length} Outstanding Items
          </span>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-5 py-3">Source</th>
                <th class="px-5 py-3">Date</th>
                <th class="px-5 py-3">Description</th>
                <th class="px-5 py-3">Reference / Cheque</th>
                <th class="px-5 py-3 text-right">Signed Amount</th>
                <th class="px-5 py-3">Classification Category</th>
                <th class="px-5 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${unmatched.map(t => `
                <tr class="hover:bg-slate-50">
                  <td class="px-5 py-3.5">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${t.source === 'Oracle Ledger' ? 'bg-indigo-100 text-indigo-800' : 'bg-teal-100 text-teal-800'}">
                      ${t.source}
                    </span>
                  </td>
                  <td class="px-5 py-3.5 font-mono text-slate-600">${t.tx_date}</td>
                  <td class="px-5 py-3.5 font-medium text-slate-800">${t.description}</td>
                  <td class="px-5 py-3.5 font-mono text-slate-500">${t.reference || t.cheque_number || '-'}</td>
                  <td class="px-5 py-3.5 text-right font-mono font-bold ${t.signed_amount > 0 ? 'text-emerald-600' : 'text-slate-800'}">
                    ${formatMoney(t.signed_amount, t.currency)}
                  </td>
                  <td class="px-5 py-3.5">
                    <select onchange="updateItemCategory('${t.id}', this.value)" class="text-xs bg-white border border-slate-300 rounded px-2 py-1 focus:outline-none">
                      <option value="Timing Difference" ${t.category === 'Timing Difference' ? 'selected' : ''}>Timing Difference</option>
                      <option value="Outstanding Cheque" ${t.category === 'Outstanding Cheque' ? 'selected' : ''}>Outstanding Cheque</option>
                      <option value="Deposit in Transit" ${t.category === 'Deposit in Transit' ? 'selected' : ''}>Deposit in Transit</option>
                      <option value="Bank Charge" ${t.category === 'Bank Charge' ? 'selected' : ''}>Bank Charge</option>
                      <option value="Interest" ${t.category === 'Interest' ? 'selected' : ''}>Interest</option>
                      <option value="Error" ${t.category === 'Error' ? 'selected' : ''}>Error / Disputed</option>
                    </select>
                  </td>
                  <td class="px-5 py-3.5 text-right">
                    <button onclick="navigateTo('workspace')" class="text-brand-teal hover:text-teal-700 font-semibold text-xs">
                      View in Workspace &rarr;
                    </button>
                  </td>
                </tr>
              `).join('')}
              ${unmatched.length === 0 ? `<tr><td colspan="7" class="px-5 py-8 text-center text-slate-400">All items are fully matched! No outstanding timing differences.</td></tr>` : ''}
            </tbody>
          </table>
        </div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load outstanding items: ${err.message}</div>`;
  }
}

async function updateItemCategory(txId, category) {
  try {
    const res = await fetch('/api/reconciliation/categorize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        transaction_id: txId,
        category: category,
        user: activeUser.name
      })
    });
    const data = await res.json();
    if (data.success) {
      showToast("Category Updated", `Assigned to ${category}`);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

// ----------------- MODULE 5: UPLOAD CENTRE -----------------
function renderUpload(container) {
  container.innerHTML = `
    <div class="max-w-4xl mx-auto space-y-6">
      
      <!-- Upload Card -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 class="font-bold text-base text-slate-800 mb-1 flex items-center space-x-2">
          <i data-lucide="upload-cloud" class="w-5 h-5 text-brand-teal"></i>
          <span>Document & File Upload Centre</span>
        </h3>
        <p class="text-xs text-slate-500 mb-6">
          Upload Oracle Accounting GL Exports or Bank Statements. Supports Excel (.xlsx, .xls), CSV, TSV, MT940, OFX/QFX, CAMT.053 XML (.xml), and PDF.
        </p>

        <form id="uploadForm" onsubmit="handleFormUpload(event)" class="space-y-4">
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Target Account</label>
              <select id="uploadAccount" class="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:outline-none focus:border-brand-teal">
                <option value="ACC-01">JPMorgan Chase - •••• 9482 (USD)</option>
                <option value="ACC-02">HSBC Commercial - •••• 3941 (USD)</option>
                <option value="ACC-03">First Abu Dhabi Bank - •••• 4851 (AED)</option>
                <option value="ACC-04">BNP Paribas - •••• 3841 (EUR)</option>
                <option value="ACC-05">Barclays Corporate - •••• 4821 (GBP)</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Period</label>
              <select id="uploadPeriod" class="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:outline-none focus:border-brand-teal">
                <option value="PER-01">2026-09</option>
                <option value="PER-02">2026-10</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Document Source Type</label>
              <select id="uploadSource" class="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:outline-none focus:border-brand-teal">
                <option value="Oracle Ledger">Oracle General Ledger Export</option>
                <option value="Bank Statement">Bank Statement</option>
              </select>
            </div>
          </div>

          <!-- Optional Password & Overwrite Controls -->
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <div>
              <label class="block text-xs font-semibold text-slate-700 mb-1">Document Password (If encrypted PDF)</label>
              <input type="password" id="uploadPassword" placeholder="Enter PDF password (optional)" class="w-full text-xs border border-slate-300 rounded-lg p-2 bg-white focus:outline-none focus:border-brand-teal">
              <p class="text-[10px] text-slate-400 mt-0.5">Processed in-memory only. Never stored or logged.</p>
            </div>
            <div class="flex items-center pt-3">
              <label class="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                <input type="checkbox" id="uploadAllowReplace" class="rounded text-brand-teal focus:ring-0">
                <span class="font-medium">Overwrite batch if duplicate file detected</span>
              </label>
            </div>
          </div>

          <!-- Drag and drop box -->
          <div class="border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:border-brand-teal transition cursor-pointer bg-slate-50" onclick="document.getElementById('fileInput').click()">
            <input type="file" id="fileInput" class="hidden" accept=".xlsx,.xls,.csv,.tsv,.txt,.pdf,.ofx,.qfx,.xml" onchange="onFileSelected(this)">
            <i data-lucide="file-up" class="w-10 h-10 text-slate-400 mx-auto mb-2"></i>
            <p class="text-sm font-semibold text-slate-700" id="selectedFileName">Click to browse or drag and drop financial statement</p>
            <p class="text-xs text-slate-400 mt-1">XLSX, XLS, CSV, TSV, MT940, OFX, CAMT.053 XML, or PDF (Max 25MB)</p>
          </div>

          <div class="flex items-center justify-between pt-2">
            <span class="text-[11px] text-slate-400">SHA-256 deduplication and debit/credit cash conventions verified on upload</span>
            <button type="submit" id="btnUploadSubmit" class="px-5 py-2.5 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow transition flex items-center space-x-2">
              <i data-lucide="upload" class="w-4 h-4"></i>
              <span>Process & Ingest File</span>
            </button>
          </div>
        </form>
      </div>

      <!-- Sample Template Generators -->
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h4 class="font-bold text-sm text-slate-800 mb-2 flex items-center space-x-2">
          <i data-lucide="download" class="w-4 h-4 text-emerald-600"></i>
          <span>Download Sample Bank / Ledger Files for Testing</span>
        </h4>
        <p class="text-xs text-slate-500 mb-4">
          Click below to generate and download ready-made test statement files formatted for instant ingestion:
        </p>

        <div class="grid grid-cols-1 md:grid-cols-4 gap-3">
          <button onclick="downloadSampleFile('oracle_csv')" class="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition">
            <div class="font-bold text-xs text-indigo-700">Sample Oracle Ledger (.csv)</div>
            <div class="text-[10px] text-slate-500 mt-0.5">Date, Desc, Ref, Cheque, Debit, Credit</div>
          </button>

          <button onclick="downloadSampleFile('bank_csv')" class="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition">
            <div class="font-bold text-xs text-teal-700">Sample Bank Statement (.csv)</div>
            <div class="text-[10px] text-slate-500 mt-0.5">Date, Narrative, Ref, Amount</div>
          </button>

          <button onclick="downloadSampleFile('mt940_txt')" class="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition">
            <div class="font-bold text-xs text-slate-800">Sample SWIFT MT940 (.txt)</div>
            <div class="text-[10px] text-slate-500 mt-0.5">:60F:, :61: statement line, :62F:</div>
          </button>

          <button onclick="downloadSampleFile('camt053_xml')" class="p-3 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-left transition">
            <div class="font-bold text-xs text-emerald-700">Sample CAMT.053 XML (.xml)</div>
            <div class="text-[10px] text-slate-500 mt-0.5">ISO 20022 BkToCstmrStmt XML</div>
          </button>
        </div>
      </div>

    </div>
  `;
}

function onFileSelected(input) {
  if (input.files && input.files[0]) {
    document.getElementById('selectedFileName').textContent = `Selected: ${input.files[0].name} (${(input.files[0].size / 1024).toFixed(1)} KB)`;
  }
}

async function handleFormUpload(e) {
  e.preventDefault();
  const fileInput = document.getElementById('fileInput');
  if (!fileInput.files || !fileInput.files[0]) {
    alert("Please select a file to upload first!");
    return;
  }

  const formData = new FormData();
  formData.append('file', fileInput.files[0]);
  formData.append('account_id', document.getElementById('uploadAccount').value);
  formData.append('period_id', document.getElementById('uploadPeriod').value);
  formData.append('source_type', document.getElementById('uploadSource').value);
  formData.append('user', activeUser.name);

  const pwd = document.getElementById('uploadPassword')?.value;
  if (pwd) formData.append('password', pwd);

  const allowReplace = document.getElementById('uploadAllowReplace')?.checked;
  if (allowReplace) formData.append('allow_replace', 'true');

  const btn = document.getElementById('btnUploadSubmit');
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="w-4 h-4 animate-spin"></i><span>Ingesting...</span>`;
  lucide.createIcons();

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Upload Successful", `Ingested ${data.records_imported} transactions! Batch: ${data.batch_id}`);
      navigateTo('workspace');
    } else {
      showToast("Upload Failed", data.detail || "Invalid format", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="upload" class="w-4 h-4"></i><span>Process & Ingest File</span>`;
    lucide.createIcons();
  }
}

function downloadSampleFile(type) {
  let content = "";
  let filename = "";

  if (type === 'oracle_csv') {
    filename = "Sample_Oracle_Ledger.csv";
    content = `Date,Description,Reference,Cheque_Number,Debit,Credit,Journal_ID\n2026-09-05,Customer Wire Settlement,REF-ZEN-901,CHK-1001,15000.00,0.00,JE-90112\n2026-09-12,Vendor Payment Software Corp,REF-SW-22,CHK-8811,0.00,4200.00,JE-90115\n2026-09-20,Office Equipment Purchase,REF-EQ-44,CHK-8812,0.00,1850.00,JE-90120\n2026-09-28,Vendor Cheque Disbursement,REF-OUT-10K,CHK-8831,0.00,10000.00,JE-90450\n2026-09-30,Branch Cash Collection,DEP-2026-99,,2000.00,0.00,JE-90455\n`;
  } else if (type === 'bank_csv') {
    filename = "Sample_Bank_Statement.csv";
    content = `Date,Description,Reference,Debit,Credit\n2026-09-06,INWARD WIRE REF-ZEN-901,REF-ZEN-901,0.00,15000.00\n2026-09-13,OUTWARD WIRE SOFTWARE CORP,REF-SW-22,4200.00,0.00\n2026-09-21,DIRECT DEBIT EQUIPMENT,REF-EQ-44,1850.00,0.00\n2026-09-30,MONTHLY SERVICE CHARGE,FEE-SEP-26,500.00,0.00\n`;
  } else if (type === 'mt940_txt') {
    filename = "Sample_Statement_MT940.txt";
    content = `:20:STMT20260930\n:25:4892019482\n:28C:001/01\n:60F:C260901USD100000,00\n:61:2609060906CR15000,00NTRFNONREF//REF-ZEN-901\n:86:INWARD WIRE ZENITH CORP\n:61:2609300930DR500,00NCHGFEE-SEP-26//FEE-SEP-26\n:86:MONTHLY SERVICE CHARGE\n:62F:C260930USD108500,00\n`;
  } else if (type === 'camt053_xml') {
    filename = "Sample_Statement_CAMT053.xml";
    content = `<?xml version="1.0" encoding="UTF-8"?>\n<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.02">\n  <BkToCstmrStmt>\n    <Stmt>\n      <Bal><Tp><CdOrPrtry><Cd>OPBD</Cd></CdOrPrtry></Tp><Amt Ccy="USD">100000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd></Bal>\n      <Bal><Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp><Amt Ccy="USD">108500.00</Amt><CdtDbtInd>CRDT</CdtDbtInd></Bal>\n      <Ntry><Amt Ccy="USD">15000.00</Amt><CdtDbtInd>CRDT</CdtDbtInd><BookgDt><Dt>2026-09-06</Dt></BookgDt><NtryDtls><TxDtls><Refs><EndToEndId>REF-ZEN-901</EndToEndId></Refs><RmtInf><Ustrd>INWARD WIRE ZENITH CORP</Ustrd></RmtInf></TxDtls></NtryDtls></Ntry>\n      <Ntry><Amt Ccy="USD">500.00</Amt><CdtDbtInd>DBIT</CdtDbtInd><BookgDt><Dt>2026-09-30</Dt></BookgDt><NtryDtls><TxDtls><Refs><EndToEndId>FEE-SEP-26</EndToEndId></Refs><RmtInf><Ustrd>MONTHLY SERVICE CHARGE</Ustrd></RmtInf></TxDtls></NtryDtls></Ntry>\n    </Stmt>\n  </BkToCstmrStmt>\n</Document>\n`;
  }

  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

// ----------------- MODULE 6: DATA VALIDATION -----------------
async function renderValidation(container) {
  container.innerHTML = `<div class="p-8 text-center text-slate-400">Running mathematical and data integrity validations...</div>`;
  try {
    const res = await fetch(`/api/validation/${currentAccountId}/${currentPeriodId}`);
    const data = await res.json();

    container.innerHTML = `
      <div class="max-w-4xl mx-auto bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Financial Integrity & Validation Suite</h3>
            <p class="text-xs text-slate-500">Automated pre-reconciliation checks across ${data.total_records} ingested transactions</p>
          </div>
          <button onclick="renderValidation(document.getElementById('contentContainer'))" class="px-3 py-1.5 bg-white border border-slate-300 rounded text-xs font-semibold text-slate-700 hover:bg-slate-100 flex items-center space-x-1">
            <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i>
            <span>Re-verify</span>
          </button>
        </div>

        <div class="p-6 space-y-4">
          ${data.checks.map(c => `
            <div class="p-4 rounded-xl border ${
              c.status === 'PASS' ? 'border-emerald-200 bg-emerald-50/30' :
              c.status === 'WARNING' ? 'border-amber-200 bg-amber-50/30' : 'border-rose-200 bg-rose-50/30'
            } flex items-start justify-between">
              <div class="space-y-1">
                <div class="flex items-center space-x-2">
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                    c.status === 'PASS' ? 'bg-emerald-100 text-emerald-800' :
                    c.status === 'WARNING' ? 'bg-amber-100 text-amber-800' : 'bg-rose-100 text-rose-800'
                  }">${c.status}</span>
                  <h4 class="font-bold text-xs text-slate-800">${c.name}</h4>
                </div>
                <p class="text-xs text-slate-600">${c.description}</p>
                <p class="text-[11px] text-slate-400 font-mono">${c.details}</p>
              </div>

              <div class="text-right">
                <span class="text-xs font-bold ${c.status === 'PASS' ? 'text-emerald-700' : 'text-amber-700'}">
                  ${c.status === 'PASS' ? 'VERIFIED' : 'ATTENTION'}
                </span>
              </div>
            </div>
          `).join('')}
        </div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load validations: ${err.message}</div>`;
  }
}

// ----------------- MODULE 7: APPROVALS & WORKFLOW -----------------
async function renderApprovals(container) {
  container.innerHTML = `<div class="p-8 text-center text-slate-400">Loading period sign-off governance queue...</div>`;
  try {
    const res = await fetch('/api/approvals');
    const data = await res.json();

    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Period Approval & Segregation of Duties Governance</h3>
            <p class="text-xs text-slate-400">Enforces: Preparer != Approver, Residual must equal 0.00 to approve</p>
          </div>
          <div class="flex items-center space-x-3">
            <span class="text-xs font-mono font-semibold bg-slate-100 text-slate-700 px-3 py-1 rounded">
              Role: ${activeUser.role}
            </span>
            <button onclick="showRolloverModal()" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow flex items-center space-x-1 transition">
              <i data-lucide="fast-forward" class="w-3.5 h-3.5"></i>
              <span>Rollover Uncleared Items</span>
            </button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-5 py-3">Account</th>
                <th class="px-5 py-3">Company</th>
                <th class="px-5 py-3">Period</th>
                <th class="px-5 py-3">Status</th>
                <th class="px-5 py-3 text-right">Residual Variance</th>
                <th class="px-5 py-3">Preparer / Approver</th>
                <th class="px-5 py-3 text-right">Workflow Transition</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.queue.map(p => `
                <tr class="hover:bg-slate-50">
                  <td class="px-5 py-3.5 font-medium text-slate-800">
                    ${p.bank_name} <span class="font-mono text-slate-400 text-[11px]">•••• ${p.account_number.slice(-4)} (${p.currency})</span>
                  </td>
                  <td class="px-5 py-3.5 text-slate-600">${p.company_name}</td>
                  <td class="px-5 py-3.5 font-mono text-slate-600">${p.period_name}</td>
                  <td class="px-5 py-3.5">
                    <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      p.status === 'Approved' ? 'bg-emerald-100 text-emerald-800' :
                      p.status === 'Locked' ? 'bg-slate-800 text-white' :
                      p.status === 'In Progress' ? 'bg-amber-100 text-amber-800' : 'bg-slate-100 text-slate-700'
                    }">${p.status}</span>
                  </td>
                  <td class="px-5 py-3.5 text-right font-mono font-bold ${Math.abs(p.residual_diff) > 0 ? 'text-amber-600' : 'text-emerald-600'}">
                    ${formatMoney(p.residual_diff, p.currency)}
                  </td>
                  <td class="px-5 py-3.5 text-slate-500 text-[11px]">
                    <div>Prep: <b>${p.preparer || 'Staff'}</b></div>
                    <div>Appr: <b>${p.approver || 'Controller'}</b></div>
                  </td>
                  <td class="px-5 py-3.5 text-right space-x-1">
                    ${p.status === 'Draft' ? `
                      <button onclick="submitWorkflowAction('${p.id}', 'In Progress')" class="px-2.5 py-1 bg-slate-700 hover:bg-slate-800 text-white rounded text-[11px] font-semibold">Start In Progress</button>
                    ` : ''}
                    ${p.status === 'In Progress' ? `
                      <button onclick="submitWorkflowAction('${p.id}', 'Submitted')" class="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-[11px] font-semibold">Submit</button>
                    ` : ''}
                    ${p.status === 'Submitted' ? `
                      <button onclick="submitWorkflowAction('${p.id}', 'Reviewed')" class="px-2.5 py-1 bg-teal-600 hover:bg-teal-700 text-white rounded text-[11px] font-semibold">Review</button>
                    ` : ''}
                    ${p.status === 'Reviewed' ? `
                      <button onclick="submitWorkflowAction('${p.id}', 'Approved')" class="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded text-[11px] font-semibold">Approve</button>
                    ` : ''}
                    ${p.status === 'Approved' ? `
                      <button onclick="submitWorkflowAction('${p.id}', 'Locked')" class="px-2.5 py-1 bg-brand-navy hover:bg-slate-900 text-white rounded text-[11px] font-semibold">Lock</button>
                    ` : ''}
                    ${p.status === 'Locked' ? `
                      <button onclick="showUnlockModal('${p.id}')" class="px-2.5 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded text-[11px] font-semibold">Unlock</button>
                    ` : ''}
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;

  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Failed to load approvals: ${err.message}</div>`;
  }
}

async function showRolloverModal() {
  const nextPeriod = prompt("Enter next period name (e.g. 2026-10):", "2026-10");
  if (!nextPeriod) return;

  try {
    const res = await fetch('/api/periods/rollover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        account_id: currentAccountId,
        current_period_id: currentPeriodId,
        next_period_name: nextPeriod,
        start_date: `${nextPeriod}-01`,
        end_date: `${nextPeriod}-30`,
        user: activeUser.name
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Period Rolled Over", `Created ${nextPeriod} and carried forward ${data.carried_count} uncleared items!`);
      await loadPeriodList();
      renderApprovals(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Rollover failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function showUnlockModal(periodId) {
  const reason = prompt("Enter mandatory documented business reason for unlocking this locked period:", "Audit re-investigation requested");
  if (!reason) return;

  try {
    const res = await fetch('/api/periods/unlock', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        period_id: periodId,
        user: activeUser.name,
        role: activeUser.role,
        reason: reason
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Period Reopened", "Locked period reopened for modifications");
      renderApprovals(document.getElementById('contentContainer'));
    } else {
      showToast("Permission Denied", data.detail || "Unlock failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

async function submitWorkflowAction(periodId, targetStatus) {
  let notes = "";
  if (targetStatus === 'In Progress' && confirm("Are you requesting to start or review this period?")) {
    notes = prompt("Enter note for status change:", "Reconciliation review update") || "Status update";
  }

  try {
    const res = await fetch('/api/approvals/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        period_id: periodId,
        target_status: targetStatus,
        user: activeUser.name,
        role: activeUser.role,
        notes: notes
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Workflow Updated", `Period status transitioned to ${targetStatus}`);
      navigateTo(currentView);
    } else {
      showToast("Action Forbidden", data.detail || "Workflow check failed", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

// ----------------- MODULE 8: COMPANIES -----------------
async function renderCompanies(container) {
  try {
    const res = await fetch('/api/companies');
    const data = await res.json();
    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Company Master Registry</h3>
            <p class="text-xs text-slate-400">${data.companies.length} Active Legal Entities</p>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="showBulkImportModal('companies')" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow flex items-center space-x-1 transition">
              <i data-lucide="file-up" class="w-3.5 h-3.5"></i>
              <span>Bulk Import</span>
            </button>
            <button onclick="showAddCompanyModal()" class="px-3 py-1.5 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow flex items-center space-x-1 transition">
              <i data-lucide="plus" class="w-3.5 h-3.5"></i>
              <span>New Company</span>
            </button>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-5 py-3">Company Code</th>
                <th class="px-5 py-3">Company Name</th>
                <th class="px-5 py-3">Reporting Currency</th>
                <th class="px-5 py-3">Created Date</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.companies.map(c => `
                <tr class="hover:bg-slate-50">
                  <td class="px-5 py-3.5 font-mono font-bold text-brand-teal">${c.code}</td>
                  <td class="px-5 py-3.5 font-medium text-slate-800">${c.name}</td>
                  <td class="px-5 py-3.5 font-bold text-slate-600">${c.reporting_currency}</td>
                  <td class="px-5 py-3.5 text-slate-400 font-mono">${c.created_at.slice(0, 10)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Error: ${err.message}</div>`;
  }
}

async function showAddCompanyModal() {
  const code = prompt("Enter unique Company Code (e.g. ACME-US):");
  if (!code) return;
  const name = prompt("Enter Company Legal Name:");
  if (!name) return;
  const ccy = prompt("Enter Reporting Currency (USD, EUR, AED, GBP):", "USD") || "USD";

  try {
    const res = await fetch('/api/companies/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code, name: name, reporting_currency: ccy, user: activeUser.name })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Company Created", `Added ${name} (${code})`);
      renderCompanies(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Failed to create company", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

// ----------------- MODULE 9: BANKS & ACCOUNTS -----------------
async function renderAccounts(container) {
  try {
    const res = await fetch('/api/accounts');
    const data = await res.json();
    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Bank Accounts Master Registry</h3>
            <p class="text-xs text-slate-400">Configured with Oracle Cash GL account mappings, allocation rules, and masking</p>
          </div>
          <div class="flex items-center space-x-2">
            <button onclick="showBulkImportModal('accounts')" class="px-3 py-1.5 bg-slate-700 hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow flex items-center space-x-1 transition">
              <i data-lucide="file-up" class="w-3.5 h-3.5"></i>
              <span>Bulk Import</span>
            </button>
            <button onclick="showAddAccountModal()" class="px-3 py-1.5 bg-brand-teal hover:bg-teal-600 text-white rounded-lg text-xs font-semibold shadow flex items-center space-x-1 transition">
              <i data-lucide="plus" class="w-3.5 h-3.5"></i>
              <span>New Account</span>
            </button>
          </div>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-5 py-3">Bank Name</th>
                <th class="px-5 py-3">Account Number (Masked)</th>
                <th class="px-5 py-3">Currency</th>
                <th class="px-5 py-3">Oracle Cash GL / Sub</th>
                <th class="px-5 py-3">Company</th>
                <th class="px-5 py-3">Opening Bal</th>
                <th class="px-5 py-3">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.accounts.map(a => `
                <tr class="hover:bg-slate-50">
                  <td class="px-5 py-3.5 font-bold text-slate-800">${a.bank_name}</td>
                  <td class="px-5 py-3.5 font-mono text-slate-700">•••• ${a.account_number.slice(-4)}</td>
                  <td class="px-5 py-3.5 font-bold text-teal-700">${a.currency}</td>
                  <td class="px-5 py-3.5 font-mono text-indigo-700">
                    ${a.gl_account}
                    ${a.gl_sub_account ? `<span class="text-[10px] text-slate-500 block">Sub: ${a.gl_sub_account}</span>` : ''}
                  </td>
                  <td class="px-5 py-3.5 text-slate-600">${a.company_name}</td>
                  <td class="px-5 py-3.5 font-mono">${formatMoney(a.opening_balance, a.currency)}</td>
                  <td class="px-5 py-3.5">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">${a.status}</span>
                  </td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Error: ${err.message}</div>`;
  }
}

async function showAddAccountModal() {
  const bankName = prompt("Enter Bank Name (e.g. Citibank NA):");
  if (!bankName) return;
  const accNum = prompt("Enter Account Number (leading zeros preserved):");
  if (!accNum) return;
  const glAcc = prompt("Enter Oracle Cash GL Account (e.g. 1010-009-CASH):", "1010-001-CASH");
  if (!glAcc) return;
  const glSub = prompt("Enter GL Sub-Account / Allocation Identifier (optional):", "") || "";
  const ccy = prompt("Enter Currency (USD, EUR, AED, GBP):", "USD") || "USD";

  try {
    const res = await fetch('/api/accounts/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company_id: "CMP-01",
        bank_name: bankName,
        account_number: accNum,
        gl_account: glAcc,
        gl_sub_account: glSub,
        currency: ccy,
        user: activeUser.name
      })
    });
    const data = await res.json();
    if (res.ok) {
      showToast("Account Created", `Added ${bankName} account`);
      await loadAccountList();
      renderAccounts(document.getElementById('contentContainer'));
    } else {
      showToast("Error", data.detail || "Failed to create account", true);
    }
  } catch (err) {
    showToast("Error", err.message, true);
  }
}

function showBulkImportModal(type) {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.csv,.xlsx,.xls';
  input.onchange = async () => {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('master_type', type);
    formData.append('user', activeUser.name);

    showToast("Importing Master Data", `Processing ${file.name}...`);
    try {
      const res = await fetch('/api/master-data/import', { method: 'POST', body: formData });
      const data = await res.json();
      if (res.ok) {
        showToast("Import Complete", `Imported ${data.imported_count} ${type}!`);
        if (type === 'companies') renderCompanies(document.getElementById('contentContainer'));
        else {
          await loadAccountList();
          renderAccounts(document.getElementById('contentContainer'));
        }
      } else {
        showToast("Import Failed", data.detail || "Error parsing file", true);
      }
    } catch (err) {
      showToast("Error", err.message, true);
    }
  };
  input.click();
}

// ----------------- MODULE 10: REPORTS & EXPORTS -----------------
function renderReports(container) {
  container.innerHTML = `
    <div class="max-w-4xl mx-auto space-y-6">
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h3 class="font-bold text-base text-slate-800 mb-1 flex items-center space-x-2">
          <i data-lucide="file-spreadsheet" class="w-5 h-5 text-emerald-600"></i>
          <span>Official Reports & Export Generator</span>
        </h3>
        <p class="text-xs text-slate-500 mb-6">
          Download formatted Bank Reconciliation Statements and multi-sheet audit workbooks for internal/external certification.
        </p>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div class="p-5 border border-slate-200 rounded-xl bg-slate-50 flex flex-col justify-between">
            <div>
              <div class="flex items-center space-x-2 mb-2">
                <div class="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center">
                  <i data-lucide="file-spreadsheet" class="w-4 h-4"></i>
                </div>
                <h4 class="font-bold text-sm text-slate-800">Comprehensive Excel Workbook (.xlsx)</h4>
              </div>
              <p class="text-xs text-slate-600 mb-4 leading-relaxed">
                Contains separate worksheets:
                <br/>1. <b>Summary & BRS</b> &nbsp;|&nbsp; 2. <b>Matched Items</b>
                <br/>3. <b>Ledger Outstanding</b> &nbsp;|&nbsp; 4. <b>Bank Outstanding</b>
                <br/>5. <b>Aging Analysis</b> &nbsp;|&nbsp; 6. <b>Audit Trail</b>
                <br/><span class="text-[11px] text-slate-400">Protected against spreadsheet formula injection.</span>
              </p>
            </div>
            <button onclick="downloadReport('excel')" class="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold shadow transition">
              Download Full Excel Workbook
            </button>
          </div>

          <div class="p-5 border border-slate-200 rounded-xl bg-slate-50 flex flex-col justify-between">
            <div>
              <div class="flex items-center space-x-2 mb-2">
                <div class="w-8 h-8 rounded-lg bg-slate-800 text-white flex items-center justify-center">
                  <i data-lucide="file-text" class="w-4 h-4"></i>
                </div>
                <h4 class="font-bold text-sm text-slate-800">Formal PDF BRS Certificate</h4>
              </div>
              <p class="text-xs text-slate-600 mb-4 leading-relaxed">
                Official single/multi-page Bank Reconciliation Statement report with adjusted bank balances, adjusted ledger balances, sign conventions, and certification lines for Preparer, Reviewer, and Approver.
              </p>
            </div>
            <button onclick="downloadReport('pdf')" class="w-full py-2 bg-brand-navy hover:bg-slate-800 text-white rounded-lg text-xs font-semibold shadow transition">
              Download PDF BRS Statement
            </button>
          </div>
        </div>
      </div>
    </div>
  `;
}

function downloadReport(format) {
  const url = format === 'excel' ? 
    `/api/reports/excel/${currentAccountId}/${currentPeriodId}` : 
    `/api/reports/pdf/${currentAccountId}/${currentPeriodId}`;
  window.location.href = url;
}

// ----------------- MODULE 11: AUDIT TRAIL -----------------
async function renderAudit(container) {
  try {
    const res = await fetch('/api/audit-logs');
    const data = await res.json();
    container.innerHTML = `
      <div class="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden mb-8">
        <div class="px-6 py-4 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h3 class="font-bold text-sm text-slate-800">Immutable Audit Trail</h3>
            <p class="text-xs text-slate-400">Real-time tamper-evident recording of uploads, matching, unmatching, and approvals</p>
          </div>
          <span class="text-xs text-slate-400">${data.logs.length} Logged Events</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200">
              <tr>
                <th class="px-4 py-3">Timestamp</th>
                <th class="px-4 py-3">User</th>
                <th class="px-4 py-3">Action</th>
                <th class="px-4 py-3">Entity Type</th>
                <th class="px-4 py-3">Entity ID</th>
                <th class="px-4 py-3">Reason / Details</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              ${data.logs.map(l => `
                <tr class="hover:bg-slate-50">
                  <td class="px-4 py-3 font-mono text-slate-500">${l.timestamp.slice(0, 19).replace('T', ' ')}</td>
                  <td class="px-4 py-3 font-medium text-slate-800">${l.user}</td>
                  <td class="px-4 py-3">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold ${
                      l.action.includes('MATCH') ? 'bg-teal-100 text-teal-800' :
                      l.action.includes('UNMATCH') ? 'bg-rose-100 text-rose-800' :
                      l.action.includes('WORKFLOW') ? 'bg-indigo-100 text-indigo-800' : 'bg-slate-100 text-slate-700'
                    }">${l.action}</span>
                  </td>
                  <td class="px-4 py-3 text-slate-600">${l.entity_type}</td>
                  <td class="px-4 py-3 font-mono text-slate-500">${l.entity_id}</td>
                  <td class="px-4 py-3 text-slate-600">${l.reason || '-'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Error: ${err.message}</div>`;
  }
}

// ----------------- MODULE 12: SETTINGS & RULES -----------------
async function renderSettings(container) {
  try {
    const res = await fetch('/api/rules');
    const data = await res.json();
    container.innerHTML = `
      <div class="max-w-4xl mx-auto space-y-6">
        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h3 class="font-bold text-base text-slate-800 mb-1 flex items-center space-x-2">
            <i data-lucide="sliders" class="w-5 h-5 text-brand-teal"></i>
            <span>Reconciliation Matching Engine Rules</span>
          </h3>
          <p class="text-xs text-slate-500 mb-6">
            Prioritized deterministic matching rules executed sequentially during automatic reconciliation.
          </p>

          <div class="space-y-3">
            ${data.rules.map(r => `
              <div class="p-4 border border-slate-200 rounded-xl bg-slate-50/50 flex items-center justify-between">
                <div class="space-y-0.5">
                  <div class="flex items-center space-x-2">
                    <span class="w-5 h-5 rounded-full bg-brand-navy text-white text-[10px] font-bold flex items-center justify-center">${r.priority}</span>
                    <h4 class="font-bold text-xs text-slate-800">${r.name}</h4>
                  </div>
                  <p class="text-xs text-slate-500 pl-7">${r.description}</p>
                  <p class="text-[11px] text-teal-700 pl-7 font-mono">Date Tolerance: ${r.date_tolerance_days} days &nbsp;|&nbsp; Amount Tolerance: $${r.amount_tolerance.toFixed(2)}</p>
                </div>
                <div>
                  <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Active</span>
                </div>
              </div>
            `).join('')}
          </div>
        </div>

        <div class="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <h4 class="font-bold text-sm text-slate-800 mb-2">LAN Sharing & Host Information</h4>
          <p class="text-xs text-slate-500 mb-3">
            This instance of BRS Tool is bound to <span class="font-mono bg-slate-100 px-1 py-0.5 rounded">0.0.0.0:8000</span>.
            Share this URL with any computer connected on the same Wi-Fi / Local Area Network:
          </p>
          <div class="p-3 bg-slate-900 text-emerald-400 font-mono text-sm rounded-lg flex items-center justify-between select-all">
            <span>http://172.20.31.32:8000</span>
            <button onclick="navigator.clipboard.writeText('http://172.20.31.32:8000'); showToast('Copied', 'LAN address copied to clipboard');" class="text-xs bg-slate-800 hover:bg-slate-700 text-white px-2.5 py-1 rounded">Copy</button>
          </div>
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="p-8 text-center text-rose-500">Error: ${err.message}</div>`;
  }
}
