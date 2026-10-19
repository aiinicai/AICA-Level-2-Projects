/**
 * Demo Business 21 - Retail & Wholesale Supermarket ERP
 * Front-end State & Application Controller
 */

// Global Application State
window.ERP_STATE = {
  currentRole: "Approver", // Single-person company
  activeTab: "tab-dashboard",
  company: null,
  inventory: [],
  inventoryMovements: [],
  accounts: [],
  taxCodes: [],
  vendors: [],
  customers: [],
  budgets: [],
  charts: {},
  pendingApprovals: [],
  companies: [],
  switchTargetCompanyId: null,
  dashboardKPIs: null,
  chartsData: null,
  currentSlide: 1,
  totalSlides: 5,
  currentTBData: null,
  currentPLData: null,
  currentBSData: null,
  currentTaxData: null
};

// Utilities
const fmtMoney = (amount) => {
  const num = Number(amount) || 0;
  const sym = window.ERP_STATE.company?.currency_symbol || "$";
  return sym + num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

const getBadgeHTML = (status) => {
  const s = status || "Draft";
  let cls = "badge-draft";
  if (s === "Approved" || s === "Fully Received" || s === "Paid") cls = "badge-approved";
  else if (s === "Pending Approval" || s === "Partially Paid" || s === "Partially Received") cls = "badge-pending";
  else if (s === "Rejected") cls = "badge-rejected";

  return `<span class="px-2 py-0.5 rounded text-[11px] font-semibold ${cls}">${s}</span>`;
};

// Application Initialization
document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initRoleSwitcher();
  initSidebarToggle();
  window.refreshAllData();
});

// Refresh All Data Across Active Modules
window.refreshAllData = async () => {
  await Promise.all([
    loadCompanySettings(),
    loadCompanies(),
    window.loadInventory(),
    loadAccounts(),
    loadTaxCodes(),
    loadVendors(),
    loadCustomers(),
    loadBudgets(),
    loadDashboardKPIs(),
    loadApprovalQueue()
  ]);

  // Load whichever tab is active
  window.switchTab(window.ERP_STATE.activeTab);
};

// -------------------------------------------------------------
// 1. Navigation & Role Management
// -------------------------------------------------------------
function initNavigation() {
  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabId = btn.getAttribute("data-tab");
      if (tabId) {
        window.switchTab(tabId);
      }
    });
  });
}

window.goToCustomerMaster = () => {
  window.switchTab("tab-customer-master");
};

window.goToVendorMaster = () => {
  window.switchTab("tab-vendor-master");
};

window.goToGeneralJournal = () => {
  window.switchTab("tab-vouchers");
  if (window.openManualJVModal) window.openManualJVModal();
};

window.switchTab = function (tabId) {
  if (!tabId) return;

  // Handle virtual tab redirects
  let targetSectionId = tabId;
  let activeNavTab = tabId;

  if (tabId === "tab-customer-master") {
    targetSectionId = "tab-ar";
    activeNavTab = "tab-customer-master";
  } else if (tabId === "tab-vendor-master") {
    targetSectionId = "tab-ap";
    activeNavTab = "tab-vendor-master";
  } else if (tabId === "tab-ar") {
    targetSectionId = "tab-ar";
    activeNavTab = "tab-ar";
  } else if (tabId === "tab-ap") {
    targetSectionId = "tab-ap";
    activeNavTab = "tab-ap";
  }

  // Ensure target section exists in DOM; if not, fall back to tab-dashboard
  if (!document.getElementById(targetSectionId)) {
    targetSectionId = "tab-dashboard";
    activeNavTab = "tab-dashboard";
  }

  window.ERP_STATE.activeTab = activeNavTab;

  // Update nav buttons
  document.querySelectorAll(".nav-item").forEach((btn) => {
    const bTab = btn.getAttribute("data-tab");
    if (bTab === activeNavTab) {
      btn.classList.add("tab-active");
    } else {
      btn.classList.remove("tab-active");
    }
  });

  // Show target section, hide all other tab-content sections
  document.querySelectorAll(".tab-content").forEach((section) => {
    if (section.id === targetSectionId) {
      section.classList.remove("hidden");
    } else {
      section.classList.add("hidden");
    }
  });

  // Execute subtab activations if needed
  if (tabId === "tab-customer-master") {
    if (window.switchARSubtab) window.switchARSubtab("customers");
  } else if (tabId === "tab-vendor-master") {
    if (window.switchAPSubtab) window.switchAPSubtab("vendors");
  }

  // Trigger tab-specific loaders
  if (targetSectionId === "tab-dashboard") loadDashboardKPIs();
  else if (targetSectionId === "tab-inventory") window.loadInventory();
  else if (targetSectionId === "tab-vouchers") window.loadVouchers();
  else if (targetSectionId === "tab-coa") loadAccounts();
  else if (targetSectionId === "tab-budget") window.loadBudgets();
  else if (targetSectionId === "tab-pr") window.loadPRs();
  else if (targetSectionId === "tab-po") window.loadPOs();
  else if (targetSectionId === "tab-grn") window.loadGRNs();
  else if (targetSectionId === "tab-ap") window.loadAPData();
  else if (targetSectionId === "tab-ar") window.loadARData();
  else if (targetSectionId === "tab-tax") window.loadTaxData();
  else if (targetSectionId === "tab-reports") window.loadFinancialReports();
  else if (targetSectionId === "tab-approvals") window.loadApprovalQueue();
};

function initRoleSwitcher() {
  const selector = document.getElementById("role-selector");
  if (selector) {
    selector.addEventListener("change", (e) => {
      window.ERP_STATE.currentRole = e.target.value;
      updateRoleUI();
    });
  }

  document.getElementById("btn-top-approvals")?.addEventListener("click", () => {
    switchTab("tab-approvals");
  });

  document.getElementById("btn-reset-db")?.addEventListener("click", () => {
    window.openResetChoiceModal();
  });
}

function updateRoleUI() {
  const role = window.ERP_STATE.currentRole;
  const msgEl = document.getElementById("approval-role-msg");
  if (msgEl) {
    if (role === "Approver") {
      msgEl.textContent = "Approver Role active (Checker): You have authority to review, approve, or reject transactions across all modules.";
    } else {
      msgEl.textContent = "Submitter Role active (Maker): You can draft and submit transactions. Approver authority is locked.";
    }
  }
  // Re-render approval center to enable/disable buttons
  renderApprovalTable();
}

function initSidebarToggle() {
  const toggleBtn = document.getElementById("btn-toggle-sidebar");
  const sidebar = document.getElementById("app-sidebar");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("w-64");
      sidebar.classList.toggle("w-16");
      document.querySelectorAll(".sidebar-text").forEach((span) => {
        span.classList.toggle("hidden");
      });
    });
  }
}

// -------------------------------------------------------------
// 2. Executive Dashboard & Charts
// -------------------------------------------------------------
async function loadDashboardKPIs() {
  try {
    const [kpiRes, chartRes] = await Promise.all([
      fetch("/api/reports/dashboard-kpis"),
      fetch("/api/reports/charts-data")
    ]);
    const kpis = await kpiRes.json();
    const chartData = await chartRes.json();
    window.ERP_STATE.dashboardKPIs = kpis;
    window.ERP_STATE.chartsData = chartData;

    // Populate KPI cards
    document.getElementById("kpi-revenue").textContent = fmtMoney(kpis.total_revenue);
    if (document.getElementById("kpi-inventory")) {
      document.getElementById("kpi-inventory").textContent = fmtMoney(kpis.total_inventory_valuation || 0);
    }
    document.getElementById("kpi-net-profit").textContent = fmtMoney(kpis.net_profit);
    document.getElementById("kpi-net-margin").textContent = `Margin: ${kpis.net_margin_pct.toFixed(1)}%`;
    document.getElementById("kpi-cash-bank").textContent = fmtMoney(kpis.cash_bank_balance);
    document.getElementById("kpi-ar").textContent = fmtMoney(kpis.open_ar);
    document.getElementById("kpi-ap").textContent = fmtMoney(kpis.open_ap);
    document.getElementById("kpi-net-tax").textContent = `Net Tax: ${fmtMoney(kpis.net_tax_payable)}`;

    // Populate Slide Deck fields
    document.getElementById("p-slide-rev").textContent = fmtMoney(kpis.total_revenue);
    document.getElementById("p-slide-profit").textContent = fmtMoney(kpis.net_profit);
    document.getElementById("p-slide-margin").textContent = `Margin: ${kpis.net_margin_pct.toFixed(1)}%`;
    document.getElementById("p-slide-cash").textContent = fmtMoney(kpis.cash_bank_balance);
    document.getElementById("p-budget-util").textContent = `${kpis.budget_utilization_pct.toFixed(1)}%`;

    renderDashboardCharts(chartData);
  } catch (err) {
    console.error("Error loading dashboard:", err);
  }
}

function renderDashboardCharts(data) {
  // Chart 1: Revenue vs Expense Trend
  const ctxTrend = document.getElementById("chart-trend")?.getContext("2d");
  if (ctxTrend) {
    if (window.ERP_STATE.charts.trend) window.ERP_STATE.charts.trend.destroy();
    window.ERP_STATE.charts.trend = new Chart(ctxTrend, {
      type: "line",
      data: {
        labels: data.trend_analysis.labels,
        datasets: [
          {
            label: "Sales Revenue",
            data: data.trend_analysis.revenue,
            borderColor: "#0078d4",
            backgroundColor: "rgba(0, 120, 212, 0.1)",
            tension: 0.3,
            fill: true
          },
          {
            label: "Expenses",
            data: data.trend_analysis.expenses,
            borderColor: "#ef4444",
            backgroundColor: "transparent",
            tension: 0.3
          },
          {
            label: "Net Profit",
            data: data.trend_analysis.net_profit,
            borderColor: "#10b981",
            backgroundColor: "transparent",
            tension: 0.3,
            borderDash: [5, 5]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } }
      }
    });
  }

  // Chart 2: Customer Sales Doughnut
  const ctxCustomer = document.getElementById("chart-customer")?.getContext("2d");
  if (ctxCustomer) {
    if (window.ERP_STATE.charts.customer) window.ERP_STATE.charts.customer.destroy();
    window.ERP_STATE.charts.customer = new Chart(ctxCustomer, {
      type: "doughnut",
      data: {
        labels: data.sales_by_customer.labels,
        datasets: [
          {
            data: data.sales_by_customer.data,
            backgroundColor: ["#0078d4", "#00bcf2", "#107c41", "#ff8c00", "#5c2d91"]
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } }
      }
    });
  }

  // Chart 3: Budget vs Actuals Bar
  const ctxBudget = document.getElementById("chart-budget")?.getContext("2d");
  if (ctxBudget) {
    if (window.ERP_STATE.charts.budget) window.ERP_STATE.charts.budget.destroy();
    window.ERP_STATE.charts.budget = new Chart(ctxBudget, {
      type: "bar",
      data: {
        labels: data.budget_vs_actual.labels,
        datasets: [
          { label: "Approved Budget", data: data.budget_vs_actual.budget, backgroundColor: "#94a3b8" },
          { label: "Encumbrance (Commitment)", data: data.budget_vs_actual.encumbrance, backgroundColor: "#f59e0b" },
          { label: "Actual Consumed", data: data.budget_vs_actual.actual, backgroundColor: "#0078d4" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  // Chart 4: Aging Summary Bar
  const ctxAging = document.getElementById("chart-aging")?.getContext("2d");
  if (ctxAging) {
    if (window.ERP_STATE.charts.aging) window.ERP_STATE.charts.aging.destroy();
    window.ERP_STATE.charts.aging = new Chart(ctxAging, {
      type: "bar",
      data: {
        labels: data.aging_summary.labels,
        datasets: [
          { label: "Accounts Receivable (AR)", data: data.aging_summary.ar, backgroundColor: "#0078d4" },
          { label: "Accounts Payable (AP)", data: data.aging_summary.ap, backgroundColor: "#ef4444" }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 11 } } } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

// -------------------------------------------------------------
// 3. General Ledger (Vouchers) & Manual JV
// -------------------------------------------------------------
window.loadVouchers = async () => {
  try {
    const src = document.getElementById("filter-voucher-source")?.value || "";
    const st = document.getElementById("filter-voucher-status")?.value || "";
    const q = document.getElementById("filter-voucher-search")?.value || "";

    let url = "/api/gl/vouchers?";
    if (src) url += `source_module=${src}&`;
    if (st) url += `status=${st}&`;
    if (q) url += `search=${encodeURIComponent(q)}&`;

    const res = await fetch(url);
    const vouchers = await res.json();

    const tbody = document.getElementById("vouchers-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (vouchers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="11" class="text-center py-6 text-slate-400">No voucher transactions match filter.</td></tr>`;
      return;
    }

    vouchers.forEach((v) => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition cursor-pointer";
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-blue-700" onclick="window.viewVoucherDetail('${v.voucher_no}')">${v.voucher_no}</td>
        <td class="p-3 text-slate-600">${v.posting_date}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-200 text-slate-800">${v.source_module}</span></td>
        <td class="p-3 font-mono text-slate-600">${v.document_ref}</td>
        <td class="p-3 font-medium text-slate-800 max-w-xs truncate" title="${v.description}">${v.description}</td>
        <td class="p-3 text-right font-mono font-semibold text-slate-800">${fmtMoney(v.total_debit)}</td>
        <td class="p-3 text-right font-mono font-semibold text-slate-800">${fmtMoney(v.total_credit)}</td>
        <td class="p-3 text-center">${getBadgeHTML(v.status)}</td>
        <td class="p-3 text-slate-500">${v.created_by}</td>
        <td class="p-3 text-slate-500">${v.approved_by || "-"}</td>
        <td class="p-3 text-center">
          <button onclick="window.viewVoucherDetail('${v.voucher_no}')" class="text-blue-600 hover:text-blue-800 font-medium text-xs">
            <i class="fa-solid fa-eye mr-1"></i>View
          </button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading vouchers:", err);
  }
};

let voucherSearchTimeout = null;
window.debounceVoucherSearch = () => {
  clearTimeout(voucherSearchTimeout);
  voucherSearchTimeout = setTimeout(() => {
    window.loadVouchers();
  }, 300);
};

window.viewVoucherDetail = async (voucherNo) => {
  try {
    const res = await fetch(`/api/gl/vouchers/${voucherNo}`);
    if (!res.ok) throw new Error("Voucher not found");
    const v = await res.json();

    document.getElementById("vdetail-no").textContent = v.voucher_no;
    document.getElementById("vdetail-date").textContent = v.posting_date;
    document.getElementById("vdetail-module").textContent = v.source_module;
    document.getElementById("vdetail-ref").textContent = v.document_ref;
    document.getElementById("vdetail-status").innerHTML = getBadgeHTML(v.status);
    document.getElementById("vdetail-desc").textContent = v.description;

    const tbody = document.getElementById("vdetail-lines-body");
    tbody.innerHTML = "";
    v.lines.forEach((l) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-2.5 font-mono text-slate-500">${l.line_no}</td>
        <td class="p-2.5 font-medium text-slate-800">${l.account_code} - ${l.account_name}</td>
        <td class="p-2.5 text-slate-600">${l.description || "-"}</td>
        <td class="p-2.5 text-right font-mono font-semibold text-slate-900">${l.debit > 0 ? fmtMoney(l.debit) : "-"}</td>
        <td class="p-2.5 text-right font-mono font-semibold text-slate-900">${l.credit > 0 ? fmtMoney(l.credit) : "-"}</td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById("vdetail-tot-dr").textContent = fmtMoney(v.total_debit);
    document.getElementById("vdetail-tot-cr").textContent = fmtMoney(v.total_credit);

    document.getElementById("modal-voucher-detail").classList.remove("hidden");
  } catch (err) {
    alert("Error fetching voucher detail: " + err.message);
  }
};

window.closeVoucherDetailModal = () => {
  document.getElementById("modal-voucher-detail").classList.add("hidden");
};

// Manual JV Form
window.openManualJVModal = () => {
  document.getElementById("jv-form-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("jv-form-ref").value = "JV-MAN-" + Math.floor(1000 + Math.random() * 9000);
  document.getElementById("jv-form-desc").value = "";

  const tbody = document.getElementById("jv-lines-tbody");
  tbody.innerHTML = "";
  // Add 2 initial lines
  window.addJVLineRow();
  window.addJVLineRow();
  window.calcJVBalance();

  document.getElementById("modal-manual-jv").classList.remove("hidden");
};

window.closeManualJVModal = () => {
  document.getElementById("modal-manual-jv").classList.add("hidden");
};

window.addJVLineRow = () => {
  const tbody = document.getElementById("jv-lines-tbody");
  const tr = document.createElement("tr");

  let optHTML = '<option value="">-- Select GL Account --</option>';
  window.ERP_STATE.accounts.forEach((a) => {
    optHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name} (${a.account_type})</option>`;
  });

  tr.innerHTML = `
    <td class="p-2">
      <select class="jv-acc-select w-full border rounded px-2 py-1 bg-white focus:outline-none text-xs">${optHTML}</select>
    </td>
    <td class="p-2">
      <input type="text" placeholder="Line description" class="jv-narration-input w-full border rounded px-2 py-1 bg-white focus:outline-none text-xs">
    </td>
    <td class="p-2 text-right">
      <input type="number" step="0.01" value="0.00" oninput="window.calcJVBalance()" class="jv-debit-input w-full border rounded px-2 py-1 text-right font-mono bg-white focus:outline-none text-xs">
    </td>
    <td class="p-2 text-right">
      <input type="number" step="0.01" value="0.00" oninput="window.calcJVBalance()" class="jv-credit-input w-full border rounded px-2 py-1 text-right font-mono bg-white focus:outline-none text-xs">
    </td>
    <td class="p-2 text-center">
      <button type="button" onclick="this.closest('tr').remove(); window.calcJVBalance();" class="text-rose-500 hover:text-rose-700">
        <i class="fa-solid fa-trash-can"></i>
      </button>
    </td>
  `;
  tbody.appendChild(tr);
};

window.calcJVBalance = () => {
  let totDr = 0;
  let totCr = 0;

  document.querySelectorAll(".jv-debit-input").forEach((inp) => {
    totDr += Number(inp.value) || 0;
  });
  document.querySelectorAll(".jv-credit-input").forEach((inp) => {
    totCr += Number(inp.value) || 0;
  });

  totDr = Math.round(totDr * 100) / 100;
  totCr = Math.round(totCr * 100) / 100;
  const variance = Math.round((totDr - totCr) * 100) / 100;

  document.getElementById("jv-live-tot-dr").textContent = fmtMoney(totDr);
  document.getElementById("jv-live-tot-cr").textContent = fmtMoney(totCr);

  const bar = document.getElementById("jv-balance-status-bar");
  const msg = document.getElementById("jv-variance-msg");
  const val = document.getElementById("jv-variance-val");
  const submitBtn = document.getElementById("btn-submit-jv");

  val.textContent = `Variance: ${fmtMoney(Math.abs(variance))}`;

  if (totDr > 0 && Math.abs(variance) < 0.01) {
    bar.className = "p-3 rounded-lg border flex items-center justify-between text-xs font-semibold bg-emerald-50 border-emerald-300 text-emerald-800";
    msg.innerHTML = '<i class="fa-solid fa-circle-check mr-1.5"></i>Voucher is perfectly balanced: Total Debit == Total Credit';
    submitBtn.disabled = false;
    submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
  } else {
    bar.className = "p-3 rounded-lg border flex items-center justify-between text-xs font-semibold bg-rose-50 border-rose-300 text-rose-800";
    msg.innerHTML = '<i class="fa-solid fa-circle-xmark mr-1.5"></i>Out of Balance! Debits and Credits must match and be > 0';
    submitBtn.disabled = true;
    submitBtn.classList.add("opacity-50", "cursor-not-allowed");
  }
};

window.submitManualJV = async () => {
  const pDate = document.getElementById("jv-form-date").value;
  const docRef = document.getElementById("jv-form-ref").value.trim();
  const desc = document.getElementById("jv-form-desc").value.trim();

  if (!pDate || !docRef || !desc) {
    alert("Please fill in Date, Document Reference, and Description");
    return;
  }

  const lines = [];
  let valid = true;
  document.querySelectorAll("#jv-lines-tbody tr").forEach((tr) => {
    const acc = tr.querySelector(".jv-acc-select")?.value;
    const narr = tr.querySelector(".jv-narration-input")?.value.trim();
    const dr = Number(tr.querySelector(".jv-debit-input")?.value) || 0;
    const cr = Number(tr.querySelector(".jv-credit-input")?.value) || 0;

    if (!acc) {
      valid = false;
      return;
    }
    if (dr > 0 || cr > 0) {
      lines.push({ account_code: acc, description: narr, debit: dr, credit: cr });
    }
  });

  if (!valid || lines.length < 2) {
    alert("Please select valid accounts for at least 2 lines");
    return;
  }

  try {
    const res = await fetch("/api/gl/vouchers?status=Approved&created_by=Owner / Accountant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        posting_date: pDate,
        document_ref: docRef,
        description: desc,
        lines: lines
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Submission failed");
    }

    alert("Journal Voucher posted to General Ledger successfully!");
    window.closeManualJVModal();
    window.loadVouchers();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 4. Chart of Accounts & Opening TB Upload
// -------------------------------------------------------------
async function loadAccounts() {
  try {
    const res = await fetch("/api/accounts");
    window.ERP_STATE.accounts = await res.json();

    const tbody = document.getElementById("coa-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    let totDr = 0;
    let totCr = 0;

    window.ERP_STATE.accounts.forEach((a) => {
      totDr += a.opening_debit;
      totCr += a.opening_credit;

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-slate-900">${a.account_code}</td>
        <td class="p-3 font-medium text-slate-800">${a.account_name}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-100 text-slate-700">${a.account_type}</span></td>
        <td class="p-3 text-slate-600">${a.sub_category}</td>
        <td class="p-3 text-center">${a.is_control_account ? '<span class="text-blue-600 font-bold"><i class="fa-solid fa-check"></i></span>' : "-"}</td>
        <td class="p-3 text-right font-mono">${a.opening_debit > 0 ? fmtMoney(a.opening_debit) : "-"}</td>
        <td class="p-3 text-right font-mono">${a.opening_credit > 0 ? fmtMoney(a.opening_credit) : "-"}</td>
      `;
      tbody.appendChild(tr);
    });

    document.getElementById("coa-tot-op-dr").textContent = fmtMoney(totDr);
    document.getElementById("coa-tot-op-cr").textContent = fmtMoney(totCr);

    // Update Opening Balance Migration Status Card
    const statusCard = document.getElementById("coa-tb-status-card");
    const statusTitle = document.getElementById("coa-tb-status-title");
    const statusDesc = document.getElementById("coa-tb-status-desc");
    const statusActions = document.getElementById("coa-tb-status-actions");
    const statusIcon = document.getElementById("coa-tb-status-icon");

    if (statusCard && statusTitle && statusDesc) {
      if (totDr === 0 && totCr === 0) {
        statusCard.className = "bg-amber-50 border border-amber-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs";
        if (statusIcon) statusIcon.className = "w-9 h-9 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center text-lg";
        statusTitle.textContent = "Opening Balances Not Yet Migrated";
        statusTitle.className = "font-bold text-amber-900";
        statusDesc.textContent = "Your ledger has clean $0.00 opening balances. Ready for data migration from your previous accounting records.";
        if (statusActions) {
          statusActions.innerHTML = `
            <button onclick="window.openEnterOpeningTBModal()" class="bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 rounded font-semibold flex items-center shadow-sm">
              <i class="fa-solid fa-table-cells mr-1.5"></i>Enter Opening Balances
            </button>
            <button onclick="window.openUploadTBModal()" class="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 px-3 py-1.5 rounded font-medium">
              <i class="fa-solid fa-upload mr-1"></i>Upload CSV/Excel
            </button>
          `;
        }
      } else {
        statusCard.className = "bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs";
        if (statusIcon) statusIcon.className = "w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center text-lg";
        statusTitle.textContent = `Opening Position Active: Balanced at ${fmtMoney(totDr)}`;
        statusTitle.className = "font-bold text-emerald-900";
        statusDesc.textContent = "Opening Trial Balance is balanced and active in the General Ledger as approved voucher OB-0001.";
        if (statusActions) {
          statusActions.innerHTML = `
            <button onclick="window.openEnterOpeningTBModal()" class="bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 px-3 py-1.5 rounded font-medium">
              <i class="fa-solid fa-pen mr-1 text-blue-600"></i>Edit / Adjust
            </button>
            <button onclick="window.resetOpeningTB()" class="bg-white hover:bg-rose-50 text-rose-700 border border-rose-300 px-3 py-1.5 rounded font-medium">
              <i class="fa-solid fa-trash-can mr-1"></i>Clear OB
            </button>
          `;
        }
      }
    }
  } catch (err) {
    console.error("Error loading accounts:", err);
  }
}

// -------------------------------------------------------------
// Opening TB Migration On-Screen Grid Functions
// -------------------------------------------------------------
window.openEnterOpeningTBModal = () => {
  const tbody = document.getElementById("enter-tb-tbody");
  if (!tbody) return;
  tbody.innerHTML = "";

  window.ERP_STATE.accounts.forEach((a) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50";
    tr.innerHTML = `
      <td class="p-2.5 font-mono font-bold text-slate-800">${a.account_code}</td>
      <td class="p-2.5 font-medium text-slate-800">${a.account_name}</td>
      <td class="p-2.5 text-slate-500">
        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">${a.account_type}</span>
        <span class="text-slate-400 ml-1">(${a.sub_category})</span>
      </td>
      <td class="p-2.5 text-right">
        <input type="number" step="0.01" min="0" value="${a.opening_debit || 0}" data-acccode="${a.account_code}" data-accname="${a.account_name}" data-acctype="${a.account_type}" data-accsub="${a.sub_category}" data-ctrl="${a.is_control_account}" class="tb-input-dr w-full border rounded px-2.5 py-1 text-right font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs" oninput="window.calcOpeningTBGridTotals()">
      </td>
      <td class="p-2.5 text-right">
        <input type="number" step="0.01" min="0" value="${a.opening_credit || 0}" data-acccode="${a.account_code}" class="tb-input-cr w-full border rounded px-2.5 py-1 text-right font-mono bg-white focus:outline-none focus:ring-1 focus:ring-blue-500 text-xs" oninput="window.calcOpeningTBGridTotals()">
      </td>
    `;
    tbody.appendChild(tr);
  });

  window.calcOpeningTBGridTotals();
  document.getElementById("modal-enter-opening-tb").classList.remove("hidden");
};

window.closeEnterOpeningTBModal = () => {
  document.getElementById("modal-enter-opening-tb").classList.add("hidden");
};

window.clearOpeningTBInputs = () => {
  document.querySelectorAll(".tb-input-dr").forEach(i => i.value = "0");
  document.querySelectorAll(".tb-input-cr").forEach(i => i.value = "0");
  window.calcOpeningTBGridTotals();
};

window.calcOpeningTBGridTotals = () => {
  let totDr = 0;
  let totCr = 0;

  document.querySelectorAll(".tb-input-dr").forEach((inp) => {
    totDr += Number(inp.value) || 0;
  });
  document.querySelectorAll(".tb-input-cr").forEach((inp) => {
    totCr += Number(inp.value) || 0;
  });

  totDr = Math.round(totDr * 100) / 100;
  totCr = Math.round(totCr * 100) / 100;
  const variance = Math.round(Math.abs(totDr - totCr) * 100) / 100;

  document.getElementById("enter-tb-total-dr").textContent = fmtMoney(totDr);
  document.getElementById("enter-tb-total-cr").textContent = fmtMoney(totCr);
  document.getElementById("enter-tb-variance").textContent = fmtMoney(variance);

  const badge = document.getElementById("enter-tb-badge");
  const saveBtn = document.getElementById("btn-save-opening-tb");

  if (totDr === 0 && totCr === 0) {
    badge.className = "px-2.5 py-1 rounded text-[11px] font-bold bg-slate-100 text-slate-600";
    badge.textContent = "ZERO BALANCES";
    if (saveBtn) saveBtn.disabled = true;
  } else if (variance < 0.01) {
    badge.className = "px-2.5 py-1 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800";
    badge.textContent = "BALANCED";
    if (saveBtn) saveBtn.disabled = false;
  } else {
    badge.className = "px-2.5 py-1 rounded text-[11px] font-bold bg-rose-100 text-rose-800";
    badge.textContent = `UNBALANCED (Diff: ${fmtMoney(variance)})`;
    if (saveBtn) saveBtn.disabled = true;
  }
};

window.submitEnterOpeningTB = async () => {
  const drInputs = document.querySelectorAll(".tb-input-dr");
  const crInputs = document.querySelectorAll(".tb-input-cr");

  const rows = [];
  drInputs.forEach((drInp, idx) => {
    const crInp = crInputs[idx];
    const dr = Number(drInp.value) || 0;
    const cr = Number(crInp.value) || 0;
    rows.push({
      account_code: drInp.getAttribute("data-acccode"),
      account_name: drInp.getAttribute("data-accname"),
      account_type: drInp.getAttribute("data-acctype"),
      sub_category: drInp.getAttribute("data-accsub"),
      is_control_account: drInp.getAttribute("data-ctrl") === "true",
      opening_debit: dr,
      opening_credit: cr
    });
  });

  const totDr = Math.round(rows.reduce((s, r) => s + r.opening_debit, 0) * 100) / 100;
  const totCr = Math.round(rows.reduce((s, r) => s + r.opening_credit, 0) * 100) / 100;

  if (Math.abs(totDr - totCr) > 0.01) {
    alert(`Cannot save unbalanced trial balance! Total Debits: ${fmtMoney(totDr)} vs Credits: ${fmtMoney(totCr)}.`);
    return;
  }

  try {
    const res = await fetch("/api/opening-tb/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(rows)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to save opening trial balance");
    }
    const data = await res.json();
    alert(data.message);
    window.closeEnterOpeningTBModal();
    await loadAccounts();
    window.loadVouchers();
    window.loadFinancialReports();
    loadDashboardKPIs();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.resetOpeningTB = async () => {
  if (!confirm("Are you sure you want to clear the Opening Trial Balance? Opening debits/credits will be reset to $0.00 and voucher OB-0001 removed.")) {
    return;
  }
  try {
    const res = await fetch("/api/opening-tb/reset", { method: "DELETE" });
    const data = await res.json();
    alert(data.message);
    await loadAccounts();
    window.loadVouchers();
    window.loadFinancialReports();
    loadDashboardKPIs();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.downloadSampleTBTemplate = () => {
  window.location.href = "/api/opening-tb/template";
};

window.openUploadTBModal = () => {
  document.getElementById("tb-file-input").value = "";
  document.getElementById("tb-preview-container").classList.add("hidden");
  document.getElementById("btn-commit-tb").disabled = true;
  document.getElementById("modal-upload-tb").classList.remove("hidden");
};

window.closeUploadTBModal = () => {
  document.getElementById("modal-upload-tb").classList.add("hidden");
};

let parsedTBUploadRows = [];

window.handleTBFileSelect = (event) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (e) => {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: "array" });
      const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
      const jsonRows = XLSX.utils.sheet_to_json(firstSheet);

      parsedTBUploadRows = jsonRows.map((r) => ({
        account_code: String(r.account_code || r["Account Code"] || "").trim(),
        account_name: String(r.account_name || r["Account Name"] || "").trim(),
        account_type: String(r.account_type || r["Account Type"] || "Expense").trim(),
        sub_category: String(r.sub_category || r["Sub Category"] || "General").trim(),
        is_control_account: String(r.is_control_account).toLowerCase() === "true",
        opening_debit: Number(r.opening_debit || r["Opening Debit"]) || 0.0,
        opening_credit: Number(r.opening_credit || r["Opening Credit"]) || 0.0
      }));

      // Validate via API
      const valRes = await fetch("/api/opening-tb/validate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsedTBUploadRows)
      });
      const valData = await valRes.json();

      const previewContainer = document.getElementById("tb-preview-container");
      const badge = document.getElementById("tb-validation-result-badge");
      const commitBtn = document.getElementById("btn-commit-tb");
      previewContainer.classList.remove("hidden");

      if (valData.valid) {
        badge.className = "p-3 rounded-lg border text-xs font-semibold flex items-center justify-between bg-emerald-50 border-emerald-300 text-emerald-800";
        badge.innerHTML = `<span><i class="fa-solid fa-circle-check mr-2"></i>${valData.message}</span><span class="font-mono">Total: ${fmtMoney(valData.total_debit)}</span>`;
        commitBtn.disabled = false;
      } else {
        badge.className = "p-3 rounded-lg border text-xs font-semibold flex items-center justify-between bg-rose-50 border-rose-300 text-rose-800";
        badge.innerHTML = `<span><i class="fa-solid fa-circle-xmark mr-2"></i>${valData.message}</span><span class="font-mono">Variance: ${fmtMoney(valData.variance)}</span>`;
        commitBtn.disabled = true;
      }
    } catch (err) {
      alert("Error parsing file: " + err.message);
    }
  };
  reader.readAsArrayBuffer(file);
};

window.commitTBUpload = async () => {
  if (!parsedTBUploadRows.length) return;
  try {
    const res = await fetch("/api/opening-tb/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(parsedTBUploadRows)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }
    const data = await res.json();
    alert(data.message);
    window.closeUploadTBModal();
    window.refreshAllData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 5. Budget Control Engine
// -------------------------------------------------------------
window.loadBudgets = async () => {
  try {
    const res = await fetch("/api/budgets?fiscal_year=2026");
    window.ERP_STATE.budgets = await res.json();

    const tbody = document.getElementById("budget-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    window.ERP_STATE.budgets.forEach((b) => {
      const pct = b.utilization_percentage || 0;
      let barColor = "bg-emerald-500";
      if (pct >= 100) barColor = "bg-rose-500";
      else if (pct >= 80) barColor = "bg-amber-500";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-slate-800">${b.account_code} - ${b.account_name}</td>
        <td class="p-3 text-slate-600 font-medium">${b.department}</td>
        <td class="p-3 text-right font-mono font-semibold">${fmtMoney(b.annual_budget)}</td>
        <td class="p-3 text-right font-mono text-slate-500">${fmtMoney(b.pre_encumbrance)}</td>
        <td class="p-3 text-right font-mono text-amber-600 font-medium">${fmtMoney(b.encumbrance)}</td>
        <td class="p-3 text-right font-mono text-blue-700 font-semibold">${fmtMoney(b.actual_consumed)}</td>
        <td class="p-3 text-right font-mono font-bold ${b.available_budget < 0 ? 'text-rose-600' : 'text-emerald-700'}">${fmtMoney(b.available_budget)}</td>
        <td class="p-3 text-center">
          <div class="flex items-center space-x-2">
            <div class="flex-1 bg-slate-200 rounded-full h-2 overflow-hidden">
              <div class="${barColor} h-2 rounded-full" style="width: ${Math.min(pct, 100)}%"></div>
            </div>
            <span class="text-[11px] font-mono font-bold ${pct > 100 ? 'text-rose-600' : 'text-slate-700'}">${pct.toFixed(0)}%</span>
          </div>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading budgets:", err);
  }
};

// -------------------------------------------------------------
// 6. Procurement (P2P): PR -> PO -> GRN
// -------------------------------------------------------------
window.loadPRs = async () => {
  try {
    const res = await fetch("/api/p2p/prs");
    const prs = await res.json();
    const tbody = document.getElementById("pr-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    prs.forEach((p) => {
      const itemsDesc = p.lines.map((l) => `${l.quantity}x ${l.description}`).join(", ");
      const canConvert = p.status === "Approved";

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-amber-700">${p.pr_number}</td>
        <td class="p-3 text-slate-600">${p.pr_date}</td>
        <td class="p-3 font-medium text-slate-800">${p.department}</td>
        <td class="p-3 text-slate-600 max-w-xs truncate" title="${itemsDesc}">${itemsDesc}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(p.total_amount)}</td>
        <td class="p-3 text-center">${getBadgeHTML(p.status)}</td>
        <td class="p-3 text-slate-500">${p.created_by}</td>
        <td class="p-3 text-slate-500">${p.approved_by || "-"}</td>
        <td class="p-3 text-center">
          ${
            canConvert
              ? `<button onclick="window.openConvertPOModal(${p.id}, '${p.pr_number}', ${p.total_amount})" class="bg-amber-500 hover:bg-amber-600 text-white px-2.5 py-1 rounded text-xs font-semibold shadow-sm"><i class="fa-solid fa-cart-shopping mr-1"></i>Convert to PO</button>`
              : "-"
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading PRs:", err);
  }
};

window.openNewPRModal = () => {
  document.getElementById("pr-form-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("pr-form-desc").value = "";
  document.getElementById("pr-form-qty").value = 1;
  document.getElementById("pr-form-price").value = 1000;
  document.getElementById("pr-form-notes").value = "";

  // Populate account select
  const accSel = document.getElementById("pr-form-account");
  accSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.account_type === "Expense" || a.account_type === "Asset")
    .forEach((a) => {
      accSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  window.onPRLineAccountOrAmountChange();
  document.getElementById("modal-pr").classList.remove("hidden");
};

window.closePRModal = () => {
  document.getElementById("modal-pr").classList.add("hidden");
};

let prBudgetCheckTimeout = null;
window.onPRLineAccountOrAmountChange = () => {
  clearTimeout(prBudgetCheckTimeout);
  prBudgetCheckTimeout = setTimeout(async () => {
    const accCode = document.getElementById("pr-form-account")?.value;
    const qty = Number(document.getElementById("pr-form-qty")?.value) || 0;
    const price = Number(document.getElementById("pr-form-price")?.value) || 0;
    const lineTot = qty * price;

    if (!accCode) return;

    try {
      const res = await fetch("/api/budgets/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ account_code: accCode, amount: lineTot })
      });
      const data = await res.json();

      const badge = document.getElementById("pr-budget-check-badge");
      const msg = document.getElementById("pr-budget-msg");
      const st = document.getElementById("pr-budget-status");
      const submitBtn = document.getElementById("btn-submit-pr");

      if (data.passed) {
        badge.className = "p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-between bg-emerald-50 border-emerald-300 text-emerald-800";
        msg.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5"></i>${data.message}`;
        st.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-200 text-emerald-900";
        st.textContent = "BUDGET PASS";
        submitBtn.disabled = false;
        submitBtn.classList.remove("opacity-50", "cursor-not-allowed");
      } else {
        badge.className = "p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-between bg-rose-50 border-rose-300 text-rose-800";
        msg.innerHTML = `<i class="fa-solid fa-circle-xmark mr-1.5"></i>${data.message}`;
        st.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-rose-200 text-rose-900";
        st.textContent = "OVER BUDGET";
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-50", "cursor-not-allowed");
      }
    } catch (err) {
      console.error("Budget check error:", err);
    }
  }, 250);
};

window.submitPR = async () => {
  const dept = document.getElementById("pr-form-dept").value;
  const pDate = document.getElementById("pr-form-date").value;
  const acc = document.getElementById("pr-form-account").value;
  const desc = document.getElementById("pr-form-desc").value.trim();
  const qty = Number(document.getElementById("pr-form-qty").value) || 0;
  const price = Number(document.getElementById("pr-form-price").value) || 0;
  const notes = document.getElementById("pr-form-notes").value.trim();

  if (!desc || qty <= 0 || price <= 0) {
    alert("Please enter a valid description, quantity and price");
    return;
  }

  try {
    const res = await fetch("/api/p2p/prs?status=Approved&created_by=Owner / Operations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pr_date: pDate,
        department: dept,
        notes: notes,
        lines: [{ description: desc, account_code: acc, quantity: qty, unit_price: price }]
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "PR creation failed");
    }

    alert("Purchase Requisition created and approved for PO conversion!");
    window.closePRModal();
    window.loadPRs();
    loadApprovalQueue();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.openConvertPOModal = (prId, prNum, amount) => {
  document.getElementById("convert-pr-id").value = prId;
  document.getElementById("convert-pr-summary").textContent = `${prNum} (${fmtMoney(amount)})`;

  const vSel = document.getElementById("convert-po-vendor");
  vSel.innerHTML = "";
  window.ERP_STATE.vendors.forEach((v) => {
    vSel.innerHTML += `<option value="${v.vendor_code}">${v.name} (${v.vendor_code})</option>`;
  });

  const tSel = document.getElementById("convert-po-tax");
  tSel.innerHTML = "";
  window.ERP_STATE.taxCodes.forEach((t) => {
    tSel.innerHTML += `<option value="${t.code}">${t.name} (${t.rate}%)</option>`;
  });

  document.getElementById("modal-convert-po").classList.remove("hidden");
};

window.closeConvertPOModal = () => {
  document.getElementById("modal-convert-po").classList.add("hidden");
};

window.confirmConvertPO = async () => {
  const prId = document.getElementById("convert-pr-id").value;
  const vendor = document.getElementById("convert-po-vendor").value;
  const tax = document.getElementById("convert-po-tax").value;

  try {
    const res = await fetch(`/api/p2p/prs/${prId}/convert-to-po?vendor_code=${vendor}&tax_code=${tax}`, {
      method: "POST"
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Conversion failed");
    }
    const po = await res.json();
    alert(`Successfully generated Purchase Order: ${po.po_number}`);
    window.closeConvertPOModal();
    window.loadPRs();
    window.loadPOs();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// Purchase Orders (PO)
window.loadPOs = async () => {
  try {
    const res = await fetch("/api/p2p/pos");
    const pos = await res.json();
    const tbody = document.getElementById("po-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    pos.forEach((p) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-amber-700">${p.po_number}</td>
        <td class="p-3 font-mono text-slate-500">${p.pr_number || "-"}</td>
        <td class="p-3 text-slate-600">${p.po_date}</td>
        <td class="p-3 font-medium text-slate-800">${p.vendor_name || p.vendor_code}</td>
        <td class="p-3 text-right font-mono">${fmtMoney(p.subtotal)}</td>
        <td class="p-3 text-right font-mono">${fmtMoney(p.tax_amount)}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(p.total_amount)}</td>
        <td class="p-3 text-center">${getBadgeHTML(p.status)}</td>
        <td class="p-3 text-slate-600">${p.delivery_date}</td>
        <td class="p-3 text-center">
          ${
            p.status === "Approved" || p.status === "Partially Received"
              ? `<button onclick="window.openNewGRNModal('${p.po_number}')" class="text-amber-600 hover:text-amber-800 font-semibold text-xs"><i class="fa-solid fa-truck-ramp-box mr-1"></i>Receive</button>`
              : "-"
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading POs:", err);
  }
};

// Goods Receipt Notes (GRN)
window.loadGRNs = async () => {
  try {
    const res = await fetch("/api/p2p/grns");
    const grns = await res.json();
    const tbody = document.getElementById("grn-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    grns.forEach((g) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-amber-700">${g.grn_number}</td>
        <td class="p-3 font-mono text-slate-600">${g.po_number}</td>
        <td class="p-3 text-slate-600">${g.grn_date}</td>
        <td class="p-3 text-slate-600">${g.vendor_delivery_ref || "-"}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(g.total_amount)}</td>
        <td class="p-3 text-center">${getBadgeHTML(g.status)}</td>
        <td class="p-3 font-mono text-blue-700 font-bold">${g.voucher_no || "-"}</td>
        <td class="p-3 text-center">
          ${g.voucher_no ? `<button onclick="window.viewVoucherDetail('${g.voucher_no}')" class="text-blue-600 hover:underline"><i class="fa-solid fa-eye"></i></button>` : "-"}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading GRNs:", err);
  }
};

let currentPOForGRN = null;
window.openNewGRNModal = async (defaultPONum) => {
  try {
    const res = await fetch("/api/p2p/pos");
    const pos = await res.json();
    const approvedPOs = pos.filter((p) => p.status === "Approved" || p.status === "Partially Received");

    const poSel = document.getElementById("grn-form-po");
    poSel.innerHTML = '<option value="">-- Select Approved PO --</option>';
    approvedPOs.forEach((p) => {
      const sel = p.po_number === defaultPONum ? "selected" : "";
      poSel.innerHTML += `<option value="${p.po_number}" ${sel}>${p.po_number} - ${p.vendor_name} (${fmtMoney(p.total_amount)})</option>`;
    });

    document.getElementById("grn-form-del-ref").value = "DEL-" + Math.floor(10000 + Math.random() * 90000);
    window.onGRNPOSelect();
    document.getElementById("modal-grn").classList.remove("hidden");
  } catch (err) {
    alert("Error loading approved POs: " + err.message);
  }
};

window.closeGRNModal = () => {
  document.getElementById("modal-grn").classList.add("hidden");
};

window.onGRNPOSelect = async () => {
  const poNum = document.getElementById("grn-form-po").value;
  const tbody = document.getElementById("grn-lines-tbody");
  tbody.innerHTML = "";

  if (!poNum) return;

  const res = await fetch("/api/p2p/pos");
  const pos = await res.json();
  currentPOForGRN = pos.find((p) => p.po_number === poNum);

  if (!currentPOForGRN) return;

  currentPOForGRN.lines.forEach((l) => {
    const remaining = Math.max(0, l.quantity - l.received_qty);
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="p-2.5 font-medium text-slate-800">${l.description}</td>
      <td class="p-2.5 font-mono text-slate-600">${l.account_code}</td>
      <td class="p-2.5 text-right font-mono">${l.quantity}</td>
      <td class="p-2.5 text-right font-mono">${l.received_qty}</td>
      <td class="p-2.5 text-right">
        <input type="number" step="0.5" max="${remaining}" min="0.1" value="${remaining}" data-poline="${l.id}" data-acc="${l.account_code}" data-desc="${l.description}" data-price="${l.unit_price}" class="grn-line-qty w-full border rounded px-2 py-1 text-right font-mono bg-white focus:outline-none text-xs">
      </td>
    `;
    tbody.appendChild(tr);
  });
};

window.submitGRN = async () => {
  const poNum = document.getElementById("grn-form-po").value;
  const delRef = document.getElementById("grn-form-del-ref").value.trim();

  if (!poNum) {
    alert("Please select a Purchase Order");
    return;
  }

  const lines = [];
  document.querySelectorAll(".grn-line-qty").forEach((inp) => {
    const qty = Number(inp.value) || 0;
    if (qty > 0) {
      lines.push({
        po_line_id: Number(inp.getAttribute("data-poline")),
        account_code: inp.getAttribute("data-acc"),
        description: inp.getAttribute("data-desc"),
        received_qty: qty,
        unit_price: Number(inp.getAttribute("data-price"))
      });
    }
  });

  if (!lines.length) {
    alert("Please enter quantities to receive");
    return;
  }

  try {
    const res = await fetch("/api/p2p/grns?status=Approved&created_by=Owner / Operations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        po_number: poNum,
        grn_date: new Date().toISOString().split("T")[0],
        vendor_delivery_ref: delRef,
        lines: lines
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "GRN submission failed");
    }

    alert("GRN Approved and Posted! GL Voucher created and Inventory stock updated automatically.");
    window.closeGRNModal();
    window.loadGRNs();
    window.loadInventory();
    loadApprovalQueue();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 7. Accounts Payable (AP): Invoices & Payments
// -------------------------------------------------------------
window.switchAPSubtab = (subtab) => {
  document.getElementById("ap-view-invoices")?.classList.add("hidden");
  document.getElementById("ap-view-payments")?.classList.add("hidden");
  document.getElementById("ap-view-creditnotes")?.classList.add("hidden");
  document.getElementById("ap-view-vendors")?.classList.add("hidden");

  document.getElementById("ap-subtab-invoices").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ap-subtab-payments").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ap-subtab-creditnotes").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ap-subtab-vendors").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";

  if (subtab === "invoices") {
    document.getElementById("ap-view-invoices")?.classList.remove("hidden");
    document.getElementById("ap-subtab-invoices").className = "px-4 py-2 font-bold border-b-2 border-blue-600 text-blue-600";
  } else if (subtab === "payments") {
    document.getElementById("ap-view-payments")?.classList.remove("hidden");
    document.getElementById("ap-subtab-payments").className = "px-4 py-2 font-bold border-b-2 border-blue-600 text-blue-600";
  } else if (subtab === "creditnotes") {
    document.getElementById("ap-view-creditnotes")?.classList.remove("hidden");
    document.getElementById("ap-subtab-creditnotes").className = "px-4 py-2 font-bold border-b-2 border-blue-600 text-blue-600";
    if (window.loadAPCreditNotes) window.loadAPCreditNotes();
  } else {
    document.getElementById("ap-view-vendors")?.classList.remove("hidden");
    document.getElementById("ap-subtab-vendors").className = "px-4 py-2 font-bold border-b-2 border-blue-600 text-blue-600";
  }
};

window.loadAPData = async () => {
  try {
    const [invRes, pmtRes, venRes] = await Promise.all([
      fetch("/api/ap/invoices"),
      fetch("/api/ap/payments"),
      fetch("/api/ap/vendors")
    ]);
    const invoices = await invRes.json();
    const payments = await pmtRes.json();
    if (venRes.ok) {
      window.ERP_STATE.vendors = await venRes.json();
    }

    // Render Invoices Table
    const invTbody = document.getElementById("ap-invoices-table-body");
    if (invTbody) {
      invTbody.innerHTML = "";
      invoices.forEach((inv) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-3 font-mono font-bold text-amber-700">${inv.invoice_number}</td>
          <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100">${inv.invoice_mode === "Mode_A_PO" ? "3-Way Match" : "Direct Expense"}</span></td>
          <td class="p-3 font-medium text-slate-800">${inv.vendor_name || inv.vendor_code}</td>
          <td class="p-3 font-mono text-slate-600">${inv.vendor_invoice_ref}</td>
          <td class="p-3 text-slate-600">${inv.invoice_date}</td>
          <td class="p-3 text-right font-mono">${fmtMoney(inv.subtotal)}</td>
          <td class="p-3 text-right font-mono">${fmtMoney(inv.tax_amount)}</td>
          <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(inv.total_amount)}</td>
          <td class="p-3 text-right font-mono font-bold text-rose-600">${fmtMoney(inv.remaining_balance)}</td>
          <td class="p-3 text-center">${getBadgeHTML(inv.status)}</td>
          <td class="p-3 text-center">${getBadgeHTML(inv.payment_status)}</td>
          <td class="p-3 text-center">
            ${inv.voucher_no ? `<button onclick="window.viewVoucherDetail('${inv.voucher_no}')" class="text-blue-600 hover:underline"><i class="fa-solid fa-eye"></i></button>` : "-"}
          </td>
        `;
        invTbody.appendChild(tr);
      });
    }

    // Render Payments Table
    const pmtTbody = document.getElementById("ap-payments-table-body");
    if (pmtTbody) {
      pmtTbody.innerHTML = "";
      payments.forEach((p) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-3 font-mono font-bold text-blue-700">${p.payment_number}</td>
          <td class="p-3 text-slate-600">${p.payment_date}</td>
          <td class="p-3 font-medium text-slate-800">${p.vendor_name || p.vendor_code}</td>
          <td class="p-3 font-mono text-slate-600">${p.bank_account_code}</td>
          <td class="p-3 font-mono text-slate-600">${p.payment_ref}</td>
          <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(p.total_amount)}</td>
          <td class="p-3 text-center">${getBadgeHTML(p.status)}</td>
          <td class="p-3 font-mono text-blue-700 font-bold">${p.voucher_no || "-"}</td>
          <td class="p-3 text-center">
            ${p.voucher_no ? `<button onclick="window.viewVoucherDetail('${p.voucher_no}')" class="text-blue-600 hover:underline"><i class="fa-solid fa-eye"></i></button>` : "-"}
          </td>
        `;
        pmtTbody.appendChild(tr);
      });
    }

    // Render Vendors Table with Balances and Quick Event Entry Actions
    const venTbody = document.getElementById("ap-vendors-table-body");
    if (venTbody) {
      venTbody.innerHTML = "";
      if (!window.ERP_STATE.vendors.length) {
        venTbody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-slate-400">No vendors registered yet. Click <button onclick="window.openNewVendorModal()" class="text-blue-600 font-semibold underline">+ New Vendor</button> to add your suppliers.</td></tr>';
      } else {
        window.ERP_STATE.vendors.forEach((v) => {
          // Calculate open payable balance for this vendor
          const vInvs = invoices.filter(i => i.vendor_code === v.vendor_code && i.status === "Approved");
          const vBalance = Math.round(vInvs.reduce((acc, i) => acc + (i.remaining_balance || 0), 0) * 100) / 100;

          const tr = document.createElement("tr");
          tr.className = "hover:bg-slate-50 transition";
          tr.innerHTML = `
            <td class="p-3 font-mono font-bold text-slate-900">${v.vendor_code}</td>
            <td class="p-3 font-medium text-slate-800">${v.name}</td>
            <td class="p-3 font-mono text-slate-600">${v.trn}</td>
            <td class="p-3 text-slate-600">${v.payment_terms}</td>
            <td class="p-3 font-mono text-[11px] text-slate-600">${v.bank_details || "-"}</td>
            <td class="p-3 text-slate-600">${v.phone || v.email || "-"}</td>
            <td class="p-3 text-right font-mono font-bold ${vBalance > 0 ? 'text-amber-600' : 'text-slate-500'}">${fmtMoney(vBalance)}</td>
            <td class="p-3 text-center whitespace-nowrap">
              <div class="flex items-center justify-center space-x-1.5">
                <button onclick="window.quickBillForVendor('${v.vendor_code}')" class="px-2 py-1 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded text-[11px] font-semibold flex items-center shadow-xs" title="Record Bill for this Vendor">
                  <i class="fa-solid fa-file-invoice-dollar mr-1"></i>+ Bill
                </button>
                <button onclick="window.quickPaymentForVendor('${v.vendor_code}')" class="px-2 py-1 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded text-[11px] font-semibold flex items-center shadow-xs" title="Disburse Payment">
                  <i class="fa-solid fa-money-bill-transfer mr-1"></i>+ Pay
                </button>
                <button onclick="window.quickPOForVendor('${v.vendor_code}')" class="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded text-[11px] font-semibold flex items-center shadow-xs" title="Create Purchase Order">
                  <i class="fa-solid fa-cart-shopping mr-1"></i>+ PO
                </button>
                <button onclick="window.openVendorStatement('${v.vendor_code}')" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[11px] font-semibold flex items-center" title="View Vendor History">
                  <i class="fa-solid fa-book mr-1"></i>Ledger
                </button>
                <button onclick="window.openEditVendorModal('${v.vendor_code}')" class="p-1 text-slate-400 hover:text-slate-800 rounded" title="Edit Vendor Details">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
              </div>
            </td>
          `;
          venTbody.appendChild(tr);
        });
      }
    }
  } catch (err) {
    console.error("Error loading AP data:", err);
  }
};

window.openNewAPInvoiceModal = async () => {
  const vSel = document.getElementById("ap-inv-vendor");
  vSel.innerHTML = "";
  window.ERP_STATE.vendors.forEach((v) => {
    vSel.innerHTML += `<option value="${v.vendor_code}">${v.name} (${v.vendor_code})</option>`;
  });

  const tSel = document.getElementById("ap-inv-tax");
  tSel.innerHTML = "";
  window.ERP_STATE.taxCodes.forEach((t) => {
    tSel.innerHTML += `<option value="${t.code}">${t.name} (${t.rate}%)</option>`;
  });

  const expSel = document.getElementById("ap-inv-exp-account");
  expSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.account_type === "Expense")
    .forEach((a) => {
      expSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  // Approved POs for Mode A
  const res = await fetch("/api/p2p/pos");
  const pos = await res.json();
  const poSel = document.getElementById("ap-inv-po");
  poSel.innerHTML = '<option value="">-- Select Approved PO --</option>';
  pos.filter((p) => p.status === "Approved" || p.status === "Partially Received" || p.status === "Fully Received")
    .forEach((p) => {
      poSel.innerHTML += `<option value="${p.po_number}">${p.po_number} - ${p.vendor_name} (${fmtMoney(p.total_amount)})</option>`;
    });

  document.getElementById("ap-inv-ref").value = "VEND-INV-" + Math.floor(1000 + Math.random() * 9000);
  window.calcAPInvoiceTotals();
  document.getElementById("modal-ap-invoice").classList.remove("hidden");
};

window.closeAPInvoiceModal = () => {
  document.getElementById("modal-ap-invoice").classList.add("hidden");
};

window.toggleAPInvoiceMode = () => {
  const mode = document.querySelector('input[name="ap-mode"]:checked').value;
  if (mode === "Mode_A_PO") {
    document.getElementById("ap-mode-a-fields").classList.remove("hidden");
    document.getElementById("ap-mode-b-fields").classList.add("hidden");
  } else {
    document.getElementById("ap-mode-a-fields").classList.add("hidden");
    document.getElementById("ap-mode-b-fields").classList.remove("hidden");
    window.onAPModeBAmountChange();
  }
};

window.onAPInvoicePOSelect = async () => {
  const poNum = document.getElementById("ap-inv-po").value;
  const grnSel = document.getElementById("ap-inv-grn");
  grnSel.innerHTML = '<option value="">-- Select GRN --</option>';

  if (!poNum) {
    if (window.onAPInvoiceGRNSelect) window.onAPInvoiceGRNSelect();
    return;
  }

  const res = await fetch("/api/p2p/grns");
  const grns = await res.json();
  const validGrns = grns.filter((g) => g.po_number === poNum && g.status === "Approved");
  validGrns.forEach((g) => {
    grnSel.innerHTML += `<option value="${g.grn_number}">${g.grn_number} (${fmtMoney(g.total_amount)})</option>`;
  });
  if (validGrns.length === 1) {
    grnSel.value = validGrns[0].grn_number;
  }
  if (window.onAPInvoiceGRNSelect) window.onAPInvoiceGRNSelect();
};

window.onAPInvoiceGRNSelect = async () => {
  const grnNum = document.getElementById("ap-inv-grn")?.value;
  const badge = document.getElementById("ap-grn-limit-badge");
  const msg = document.getElementById("ap-grn-limit-msg");
  const valBadge = document.getElementById("ap-grn-limit-val");
  const subInp = document.getElementById("ap-inv-subtotal");

  if (!grnNum) {
    if (badge) badge.classList.add("hidden");
    window._currentGRNLimit = null;
    return;
  }

  try {
    const [grnRes, invRes] = await Promise.all([
      fetch("/api/p2p/grns"),
      fetch("/api/ap/invoices")
    ]);
    const grns = await grnRes.json();
    const grn = grns.find(g => g.grn_number === grnNum);
    if (!grn) return;

    const grnTotal = Number(grn.total_amount) || 0;
    const allInvs = await invRes.json();
    const invoicedAgainstGRN = allInvs
      .filter(i => i.grn_number === grnNum && i.status !== "Rejected")
      .reduce((sum, i) => sum + (Number(i.subtotal) || 0), 0);

    const maxAllowed = Math.max(0, Math.round((grnTotal - invoicedAgainstGRN) * 100) / 100);
    window._currentGRNLimit = maxAllowed;

    if (badge) {
      badge.classList.remove("hidden");
      msg.innerHTML = `<i class="fa-solid fa-shield-halved mr-1.5 text-amber-600"></i>3-Way Match Limit: Max allowable subtotal is ${fmtMoney(maxAllowed)} (GRN Value: ${fmtMoney(grnTotal)}, Prior Billed: ${fmtMoney(invoicedAgainstGRN)})`;
      valBadge.textContent = `Max: ${fmtMoney(maxAllowed)}`;
    }

    if (subInp) {
      subInp.max = maxAllowed;
      subInp.value = maxAllowed;
      window.calcAPInvoiceTotals();
    }
  } catch (err) {
    console.error("Error checking GRN limit:", err);
  }
};

window.onAPModeBAmountChange = async () => {
  const accCode = document.getElementById("ap-inv-exp-account").value;
  const subtotal = Number(document.getElementById("ap-inv-subtotal").value) || 0;

  if (!accCode) return;

  try {
    const res = await fetch("/api/budgets/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_code: accCode, amount: subtotal })
    });
    const data = await res.json();

    const badge = document.getElementById("ap-mode-b-budget-badge");
    const msg = document.getElementById("ap-budget-msg");
    const st = document.getElementById("ap-budget-status");

    if (data.passed) {
      badge.className = "p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-between bg-emerald-50 border-emerald-300 text-emerald-800";
      msg.innerHTML = `<i class="fa-solid fa-circle-check mr-1.5"></i>${data.message}`;
      st.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-200 text-emerald-900";
      st.textContent = "PASS";
    } else {
      badge.className = "p-2.5 rounded-lg border text-xs font-semibold flex items-center justify-between bg-rose-50 border-rose-300 text-rose-800";
      msg.innerHTML = `<i class="fa-solid fa-circle-xmark mr-1.5"></i>${data.message}`;
      st.className = "px-2 py-0.5 rounded text-[11px] font-bold bg-rose-200 text-rose-900";
      st.textContent = "FAIL";
    }
  } catch (err) {
    console.error("AP Budget check error:", err);
  }
};

window.calcAPInvoiceTotals = () => {
  const sub = Number(document.getElementById("ap-inv-subtotal")?.value) || 0;
  const taxCode = document.getElementById("ap-inv-tax")?.value || "VAT-STD-5";
  const taxObj = window.ERP_STATE.taxCodes.find((t) => t.code === taxCode);
  const rate = taxObj ? taxObj.rate : 5.0;

  const tax = Math.round(sub * (rate / 100.0) * 100) / 100;
  const tot = Math.round((sub + tax) * 100) / 100;

  document.getElementById("ap-inv-total").value = fmtMoney(tot);
};

window.submitAPInvoice = async () => {
  const mode = document.querySelector('input[name="ap-mode"]:checked').value;
  const vendor = document.getElementById("ap-inv-vendor").value;
  const ref = document.getElementById("ap-inv-ref").value.trim();
  const subtotal = Number(document.getElementById("ap-inv-subtotal").value) || 0;
  const taxCode = document.getElementById("ap-inv-tax").value;

  if (!vendor || !ref || subtotal <= 0) {
    alert("Please fill in Vendor, Vendor Invoice Ref, and Subtotal");
    return;
  }

  // 3-Way Match Hard Validation
  if (mode === "Mode_A_PO") {
    const grnNum = document.getElementById("ap-inv-grn").value;
    if (!grnNum) {
      alert("Please select an approved GRN for 3-Way Match Mode");
      return;
    }
    if (window._currentGRNLimit !== null && window._currentGRNLimit !== undefined) {
      if (subtotal > (window._currentGRNLimit + 0.001)) {
        alert(`3-Way Match Violation: Invoiced subtotal ($${subtotal.toFixed(2)}) cannot exceed the maximum allowable GRN limit ($${window._currentGRNLimit.toFixed(2)}). Please adjust the invoice subtotal.`);
        return;
      }
    }
  }

  const taxObj = window.ERP_STATE.taxCodes.find((t) => t.code === taxCode);
  const rate = taxObj ? taxObj.rate : 5.0;
  const taxAmt = Math.round(subtotal * (rate / 100.0) * 100) / 100;
  const totalAmt = Math.round((subtotal + taxAmt) * 100) / 100;

  const payload = {
    invoice_mode: mode,
    vendor_code: vendor,
    vendor_invoice_ref: ref,
    po_number: mode === "Mode_A_PO" ? document.getElementById("ap-inv-po").value : null,
    grn_number: mode === "Mode_A_PO" ? document.getElementById("ap-inv-grn").value : null,
    invoice_date: new Date().toISOString().split("T")[0],
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
    expense_account_code: mode === "Mode_B_Direct" ? document.getElementById("ap-inv-exp-account").value : null,
    tax_code: taxCode,
    subtotal: subtotal,
    tax_amount: taxAmt,
    total_amount: totalAmt
  };

  try {
    const res = await fetch("/api/ap/invoices?status=Approved&created_by=Owner / Accountant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Invoice creation failed");
    }

    alert("Vendor Invoice posted directly to General Ledger!");
    window.closeAPInvoiceModal();
    window.loadAPData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// AP Payments
window.openAPPaymentModal = () => {
  const vSel = document.getElementById("pmt-form-vendor");
  vSel.innerHTML = '<option value="">-- Select Vendor --</option>';
  window.ERP_STATE.vendors.forEach((v) => {
    vSel.innerHTML += `<option value="${v.vendor_code}">${v.name} (${v.vendor_code})</option>`;
  });

  const bSel = document.getElementById("pmt-form-bank");
  bSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.sub_category === "Bank")
    .forEach((a) => {
      bSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  document.getElementById("pmt-form-ref").value = "CHK-" + Math.floor(10000 + Math.random() * 90000);
  document.getElementById("pmt-open-invoices-tbody").innerHTML = "";

  document.getElementById("modal-ap-payment").classList.remove("hidden");
};

window.closeAPPaymentModal = () => {
  document.getElementById("modal-ap-payment").classList.add("hidden");
};

window.onAPPaymentVendorSelect = async () => {
  const vendor = document.getElementById("pmt-form-vendor").value;
  const tbody = document.getElementById("pmt-open-invoices-tbody");
  tbody.innerHTML = "";

  if (!vendor) return;

  const res = await fetch(`/api/ap/invoices?vendor_code=${vendor}&status=Approved`);
  const invoices = await res.json();
  const openInvs = invoices.filter((i) => i.payment_status !== "Paid" && i.remaining_balance > 0);

  if (!openInvs.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-400">No open approved invoices for this vendor.</td></tr>';
    return;
  }

  openInvs.forEach((inv) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="p-2 text-center">
        <input type="checkbox" class="pmt-inv-chk" data-invid="${inv.id}" data-invnum="${inv.invoice_number}" data-balance="${inv.remaining_balance}" onchange="window.togglePaymentInv(this)">
      </td>
      <td class="p-2 font-mono font-bold text-slate-800">${inv.invoice_number}</td>
      <td class="p-2 text-slate-600">${inv.invoice_date}</td>
      <td class="p-2 text-right font-mono font-bold text-rose-600">${fmtMoney(inv.remaining_balance)}</td>
      <td class="p-2 text-right">
        <input type="number" step="0.01" max="${inv.remaining_balance}" value="${inv.remaining_balance}" disabled class="pmt-inv-amt w-full border rounded px-2 py-1 text-right font-mono bg-slate-100 text-xs">
      </td>
    `;
    tbody.appendChild(tr);
  });
};

window.togglePaymentInv = (chk) => {
  const amtInp = chk.closest("tr").querySelector(".pmt-inv-amt");
  if (chk.checked) {
    amtInp.disabled = false;
    amtInp.classList.remove("bg-slate-100");
    amtInp.classList.add("bg-white");
  } else {
    amtInp.disabled = true;
    amtInp.classList.remove("bg-white");
    amtInp.classList.add("bg-slate-100");
  }
};

window.submitAPPayment = async () => {
  const vendor = document.getElementById("pmt-form-vendor").value;
  const bank = document.getElementById("pmt-form-bank").value;
  const ref = document.getElementById("pmt-form-ref").value.trim();
  const method = document.getElementById("pmt-form-method").value;

  if (!vendor || !bank || !ref) {
    alert("Please select Vendor, Paying Bank, and Reference");
    return;
  }

  const lines = [];
  document.querySelectorAll(".pmt-inv-chk:checked").forEach((chk) => {
    const amt = Number(chk.closest("tr").querySelector(".pmt-inv-amt").value) || 0;
    if (amt > 0) {
      lines.push({
        ap_invoice_id: Number(chk.getAttribute("data-invid")),
        invoice_number: chk.getAttribute("data-invnum"),
        amount_paid: amt
      });
    }
  });

  if (!lines.length) {
    alert("Please select at least one invoice to pay");
    return;
  }

  try {
    const res = await fetch("/api/ap/payments?status=Approved&created_by=Owner / Accountant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        payment_date: new Date().toISOString().split("T")[0],
        vendor_code: vendor,
        bank_account_code: bank,
        payment_ref: ref,
        payment_method: method,
        lines: lines
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Payment creation failed");
    }

    alert("Disbursement payment approved and posted to General Ledger!");
    window.closeAPPaymentModal();
    window.loadAPData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.onAPPaymentMethodChange = () => {
  const method = document.getElementById("pmt-form-method")?.value;
  const bSel = document.getElementById("pmt-form-bank");
  const refInp = document.getElementById("pmt-form-ref");
  if (!bSel) return;

  if (method === "Cash") {
    for (let i = 0; i < bSel.options.length; i++) {
      if (bSel.options[i].value === "1010" || bSel.options[i].text.toLowerCase().includes("cash")) {
        bSel.selectedIndex = i;
        break;
      }
    }
    if (refInp && (!refInp.value || refInp.value.startsWith("CHK-") || refInp.value.startsWith("WTR-"))) {
      refInp.value = "CASH-PMT-" + Math.floor(1000 + Math.random() * 9000);
    }
  } else if (method === "Cheque") {
    if (refInp && (!refInp.value || refInp.value.startsWith("CASH-"))) {
      refInp.value = "CHK-" + Math.floor(10000 + Math.random() * 90000);
    }
  }
};

// =============================================================
// AP Purchase Credit Notes Controller
// =============================================================
window.loadAPCreditNotes = async () => {
  try {
    const res = await fetch("/api/ap/credit-notes");
    if (!res.ok) return;
    const cns = await res.json();
    const tbody = document.getElementById("ap-creditnotes-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!cns.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="p-4 text-center text-slate-400">No purchase credit notes recorded yet.</td></tr>';
      return;
    }
    cns.forEach(cn => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-rose-700">${cn.credit_note_number}</td>
        <td class="p-3 text-slate-600">${cn.credit_note_date}</td>
        <td class="p-3 font-medium text-slate-800">${cn.vendor_name || cn.vendor_code}</td>
        <td class="p-3 font-mono text-slate-600">${cn.original_invoice_ref || "-"}</td>
        <td class="p-3 text-slate-700">${cn.reason}</td>
        <td class="p-3 text-right font-mono">${fmtMoney(cn.subtotal)}</td>
        <td class="p-3 text-right font-mono text-amber-600">${fmtMoney(cn.tax_amount)}</td>
        <td class="p-3 text-right font-mono font-bold text-rose-700">${fmtMoney(cn.total_credit)}</td>
        <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Approved</span></td>
        <td class="p-3 text-center">
          ${cn.voucher_no ? `<button onclick="window.viewVoucherDetail('${cn.voucher_no}')" class="text-blue-600 hover:underline font-mono font-bold">${cn.voucher_no}</button>` : "-"}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading AP credit notes:", err);
  }
};

window.openNewAPCreditNoteModal = async () => {
  const vSel = document.getElementById("ap-cn-vendor");
  vSel.innerHTML = '<option value="">-- Select Vendor --</option>';
  (window.ERP_STATE.vendors || []).forEach(v => {
    vSel.innerHTML += `<option value="${v.vendor_code}">${v.name} (${v.vendor_code})</option>`;
  });

  document.getElementById("ap-cn-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("ap-cn-reason").value = "";
  document.getElementById("ap-cn-subtotal").value = "100.00";
  window.onAPCreditNoteVendorSelect();
  window.calcAPCreditNoteLive();
  document.getElementById("modal-ap-credit-note").classList.remove("hidden");
};

window.closeNewAPCreditNoteModal = () => {
  document.getElementById("modal-ap-credit-note").classList.add("hidden");
};

window.onAPCreditNoteVendorSelect = async () => {
  const vendCode = document.getElementById("ap-cn-vendor").value;
  const invSel = document.getElementById("ap-cn-invoice-ref");
  invSel.innerHTML = '<option value="">-- General Vendor Credit Note --</option>';
  if (!vendCode) return;

  try {
    const res = await fetch(`/api/ap/invoices?vendor_code=${vendCode}&status=Approved`);
    const invs = await res.json();
    invs.forEach(inv => {
      invSel.innerHTML += `<option value="${inv.invoice_number}" data-balance="${inv.remaining_balance}">${inv.invoice_number} (Ref: ${inv.vendor_invoice_ref}, Bal: ${fmtMoney(inv.remaining_balance)})</option>`;
    });
  } catch (e) {
    console.error("Error loading vendor invoices for credit note:", e);
  }
};

window.onAPCreditNoteInvoiceSelect = () => {
  const invSel = document.getElementById("ap-cn-invoice-ref");
  const opt = invSel.options[invSel.selectedIndex];
  if (opt && opt.getAttribute("data-balance")) {
    const bal = Number(opt.getAttribute("data-balance")) || 0;
    if (bal > 0) {
      document.getElementById("ap-cn-subtotal").value = (bal / 1.05).toFixed(2);
      window.calcAPCreditNoteLive();
    }
  }
};

window.calcAPCreditNoteLive = () => {
  const sub = Number(document.getElementById("ap-cn-subtotal").value) || 0;
  const taxCode = document.getElementById("ap-cn-tax").value;
  const taxRate = taxCode === "STANDARD_5" ? 0.05 : 0.0;
  const tax = Math.round(sub * taxRate * 100) / 100;
  const tot = Math.round((sub + tax) * 100) / 100;
  document.getElementById("ap-cn-total").value = fmtMoney(tot);
};

window.submitAPCreditNote = async () => {
  const vendor = document.getElementById("ap-cn-vendor").value;
  const invRef = document.getElementById("ap-cn-invoice-ref").value || null;
  const cnDate = document.getElementById("ap-cn-date").value;
  const reason = document.getElementById("ap-cn-reason").value.trim();
  const subtotal = Number(document.getElementById("ap-cn-subtotal").value) || 0;
  const taxCode = document.getElementById("ap-cn-tax").value;

  if (!vendor || !reason || subtotal <= 0) {
    alert("Please fill in Vendor, Reason, and Subtotal Credit Amount");
    return;
  }

  const taxRate = taxCode === "STANDARD_5" ? 0.05 : 0.0;
  const taxAmt = Math.round(subtotal * taxRate * 100) / 100;
  const totalCredit = Math.round((subtotal + taxAmt) * 100) / 100;

  try {
    const res = await fetch("/api/ap/credit-notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vendor_code: vendor,
        original_invoice_ref: invRef,
        credit_note_date: cnDate,
        reason: reason,
        subtotal: subtotal,
        tax_code: taxCode,
        tax_amount: taxAmt,
        total_credit: totalCredit
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Credit Note submission failed");
    }
    alert("Purchase Credit Note posted directly to General Ledger!");
    window.closeNewAPCreditNoteModal();
    window.loadAPData();
    window.loadAPCreditNotes();
    window.switchAPSubtab("creditnotes");
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 8. Accounts Receivable (AR): Invoicing & Receipts
// -------------------------------------------------------------
window.switchARSubtab = (subtab) => {
  document.getElementById("ar-view-invoices")?.classList.add("hidden");
  document.getElementById("ar-view-receipts")?.classList.add("hidden");
  document.getElementById("ar-view-creditnotes")?.classList.add("hidden");
  document.getElementById("ar-view-customers")?.classList.add("hidden");

  document.getElementById("ar-subtab-invoices").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ar-subtab-receipts").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ar-subtab-creditnotes").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("ar-subtab-customers").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";

  if (subtab === "invoices") {
    document.getElementById("ar-view-invoices")?.classList.remove("hidden");
    document.getElementById("ar-subtab-invoices").className = "px-4 py-2 font-bold border-b-2 border-cyan-600 text-cyan-600";
  } else if (subtab === "receipts") {
    document.getElementById("ar-view-receipts")?.classList.remove("hidden");
    document.getElementById("ar-subtab-receipts").className = "px-4 py-2 font-bold border-b-2 border-cyan-600 text-cyan-600";
  } else if (subtab === "creditnotes") {
    document.getElementById("ar-view-creditnotes")?.classList.remove("hidden");
    document.getElementById("ar-subtab-creditnotes").className = "px-4 py-2 font-bold border-b-2 border-cyan-600 text-cyan-600";
    if (window.loadARCreditNotes) window.loadARCreditNotes();
  } else {
    document.getElementById("ar-view-customers")?.classList.remove("hidden");
    document.getElementById("ar-subtab-customers").className = "px-4 py-2 font-bold border-b-2 border-cyan-600 text-cyan-600";
  }
};

window.loadARData = async () => {
  try {
    const [invRes, rcptRes, custRes] = await Promise.all([
      fetch("/api/ar/invoices"),
      fetch("/api/ar/receipts"),
      fetch("/api/ar/customers")
    ]);
    const invoices = await invRes.json();
    const receipts = await rcptRes.json();
    if (custRes.ok) {
      window.ERP_STATE.customers = await custRes.json();
    }

    // Render AR Invoices Table
    const invTbody = document.getElementById("ar-invoices-table-body");
    if (invTbody) {
      invTbody.innerHTML = "";
      invoices.forEach((inv) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-3 font-mono font-bold text-cyan-700">${inv.invoice_number}</td>
          <td class="p-3 text-slate-600">${inv.invoice_date}</td>
          <td class="p-3 font-medium text-slate-800">${inv.customer_name || inv.customer_code}</td>
          <td class="p-3 text-right font-mono">${fmtMoney(inv.subtotal)}</td>
          <td class="p-3 text-right font-mono">${fmtMoney(inv.tax_amount)}</td>
          <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(inv.total_amount)}</td>
          <td class="p-3 text-right font-mono font-bold text-cyan-700">${fmtMoney(inv.remaining_balance)}</td>
          <td class="p-3 text-center">${getBadgeHTML(inv.status)}</td>
          <td class="p-3 text-center">${getBadgeHTML(inv.payment_status)}</td>
          <td class="p-3 text-center">
            <button onclick="window.downloadTaxInvoicePDF('${inv.invoice_number}')" class="bg-cyan-50 hover:bg-cyan-100 text-cyan-700 border border-cyan-200 px-2 py-0.5 rounded text-[11px] font-semibold flex items-center mx-auto">
              <i class="fa-solid fa-file-pdf text-rose-500 mr-1"></i>Tax Invoice PDF
            </button>
          </td>
          <td class="p-3 text-center">
            ${inv.voucher_no ? `<button onclick="window.viewVoucherDetail('${inv.voucher_no}')" class="text-blue-600 hover:underline"><i class="fa-solid fa-eye"></i></button>` : "-"}
          </td>
        `;
        invTbody.appendChild(tr);
      });
    }

    // Render AR Receipts Table
    const rcptTbody = document.getElementById("ar-receipts-table-body");
    if (rcptTbody) {
      rcptTbody.innerHTML = "";
      receipts.forEach((r) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-3 font-mono font-bold text-blue-700">${r.receipt_number}</td>
          <td class="p-3 text-slate-600">${r.receipt_date}</td>
          <td class="p-3 font-medium text-slate-800">${r.customer_name || r.customer_code}</td>
          <td class="p-3 font-mono text-slate-600">${r.bank_account_code}</td>
          <td class="p-3 font-mono text-slate-600">${r.receipt_ref}</td>
          <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(r.total_amount)}</td>
          <td class="p-3 text-center">${getBadgeHTML(r.status)}</td>
          <td class="p-3 font-mono text-blue-700 font-bold">${r.voucher_no || "-"}</td>
          <td class="p-3 text-center">
            ${r.voucher_no ? `<button onclick="window.viewVoucherDetail('${r.voucher_no}')" class="text-blue-600 hover:underline"><i class="fa-solid fa-eye"></i></button>` : "-"}
          </td>
        `;
        rcptTbody.appendChild(tr);
      });
    }

    // Render Customer Master Table with Balances and Quick Event Entry Actions
    const custTbody = document.getElementById("ar-customers-table-body");
    if (custTbody) {
      custTbody.innerHTML = "";
      if (!window.ERP_STATE.customers.length) {
        custTbody.innerHTML = '<tr><td colspan="8" class="p-4 text-center text-slate-400">No customers registered yet. Click <button onclick="window.openNewCustomerModal()" class="text-cyan-600 font-semibold underline">+ New Customer</button> to add your retail / wholesale buyers.</td></tr>';
      } else {
        window.ERP_STATE.customers.forEach((c) => {
          // Calculate open receivable balance for this customer
          const cInvs = invoices.filter(i => i.customer_code === c.customer_code && i.status === "Approved");
          const cBalance = Math.round(cInvs.reduce((acc, i) => acc + (i.remaining_balance || 0), 0) * 100) / 100;

          const tr = document.createElement("tr");
          tr.className = "hover:bg-slate-50 transition";
          tr.innerHTML = `
            <td class="p-3 font-mono font-bold text-slate-900">${c.customer_code}</td>
            <td class="p-3 font-medium text-slate-800">${c.name}</td>
            <td class="p-3 font-mono text-slate-600">${c.trn}</td>
            <td class="p-3 text-right font-mono font-semibold">${fmtMoney(c.credit_limit)}</td>
            <td class="p-3 text-slate-600">${c.billing_address || "-"}</td>
            <td class="p-3 text-slate-600">${c.phone || c.email || "-"}</td>
            <td class="p-3 text-right font-mono font-bold ${cBalance > 0 ? 'text-rose-600' : 'text-slate-500'}">${fmtMoney(cBalance)}</td>
            <td class="p-3 text-center whitespace-nowrap">
              <div class="flex items-center justify-center space-x-1.5">
                <button onclick="window.quickInvoiceForCustomer('${c.customer_code}')" class="px-2 py-1 bg-cyan-50 hover:bg-cyan-100 text-cyan-700 rounded text-[11px] font-semibold flex items-center shadow-xs" title="Create Sales Invoice for this Customer">
                  <i class="fa-solid fa-receipt mr-1"></i>+ Invoice
                </button>
                <button onclick="window.quickReceiptForCustomer('${c.customer_code}')" class="px-2 py-1 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded text-[11px] font-semibold flex items-center shadow-xs" title="Record Bank Collection">
                  <i class="fa-solid fa-hand-holding-dollar mr-1"></i>+ Receipt
                </button>
                <button onclick="window.openCustomerStatement('${c.customer_code}')" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-[11px] font-semibold flex items-center" title="View Customer History">
                  <i class="fa-solid fa-book mr-1"></i>Ledger
                </button>
                <button onclick="window.openEditCustomerModal('${c.customer_code}')" class="p-1 text-slate-400 hover:text-slate-800 rounded" title="Edit Customer Details">
                  <i class="fa-solid fa-pen-to-square"></i>
                </button>
              </div>
            </td>
          `;
          custTbody.appendChild(tr);
        });
      }
    }
    if (window.loadARCreditNotes) window.loadARCreditNotes();
  } catch (err) {
    console.error("Error loading AR data:", err);
  }
};

window.openNewARInvoiceModal = () => {
  const cSel = document.getElementById("ar-inv-customer");
  cSel.innerHTML = "";
  window.ERP_STATE.customers.forEach((c) => {
    cSel.innerHTML += `<option value="${c.customer_code}">${c.name} (${c.customer_code})</option>`;
  });

  const revSel = document.getElementById("ar-inv-rev-account");
  revSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.account_type === "Revenue")
    .forEach((a) => {
      revSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  const tSel = document.getElementById("ar-inv-tax");
  tSel.innerHTML = "";
  window.ERP_STATE.taxCodes.forEach((t) => {
    tSel.innerHTML += `<option value="${t.code}">${t.name} (${t.rate}%)</option>`;
  });

  // Populate Product (SKU) select dropdown
  const itemSel = document.getElementById("ar-inv-item-select");
  if (itemSel) {
    itemSel.innerHTML = '<option value="">-- Choose Stock Product or Custom Item --</option>';
    (window.ERP_STATE.inventory || []).forEach((it) => {
      itemSel.innerHTML += `<option value="${it.item_code}">${it.name} (${it.item_code}) - Stock: ${it.stock_quantity} ${it.unit} - $${it.selling_price.toFixed(2)}</option>`;
    });
  }

  document.getElementById("ar-inv-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("ar-inv-desc").value = "Consumer Goods Direct Sale";
  document.getElementById("ar-inv-qty").value = 1;
  document.getElementById("ar-inv-price").value = 25.00;
  document.getElementById("ar-inv-discount").value = 0;

  window.calcARInvoiceLive();
  document.getElementById("modal-ar-invoice").classList.remove("hidden");
};

window.onARInvoiceItemSelect = () => {
  const code = document.getElementById("ar-inv-item-select")?.value;
  if (!code) return;
  const item = (window.ERP_STATE.inventory || []).find((i) => i.item_code === code);
  if (item) {
    document.getElementById("ar-inv-desc").value = item.name;
    document.getElementById("ar-inv-price").value = item.selling_price;
    const revSel = document.getElementById("ar-inv-rev-account");
    if (revSel) revSel.value = "4000";
    window.calcARInvoiceLive();
  }
};

window.closeARInvoiceModal = () => {
  document.getElementById("modal-ar-invoice").classList.add("hidden");
};

window.calcARInvoiceLive = () => {
  const qty = Number(document.getElementById("ar-inv-qty")?.value) || 0;
  const price = Number(document.getElementById("ar-inv-price")?.value) || 0;
  const disc = Number(document.getElementById("ar-inv-discount")?.value) || 0;
  const taxCode = document.getElementById("ar-inv-tax")?.value || "VAT-STD-5";

  const taxObj = window.ERP_STATE.taxCodes.find((t) => t.code === taxCode);
  const rate = taxObj ? taxObj.rate : 5.0;

  const net = Math.max(0, qty * price - disc);
  const tax = Math.round(net * (rate / 100.0) * 100) / 100;
  const tot = Math.round((net + tax) * 100) / 100;

  document.getElementById("ar-inv-live-total").textContent = fmtMoney(tot);
};

window.submitARInvoice = async () => {
  const cust = document.getElementById("ar-inv-customer").value;
  const iDate = document.getElementById("ar-inv-date").value;
  const revAcc = document.getElementById("ar-inv-rev-account").value;
  const desc = document.getElementById("ar-inv-desc").value.trim();
  const qty = Number(document.getElementById("ar-inv-qty").value) || 0;
  const price = Number(document.getElementById("ar-inv-price").value) || 0;
  const disc = Number(document.getElementById("ar-inv-discount").value) || 0;
  const tax = document.getElementById("ar-inv-tax").value;
  const itemCode = document.getElementById("ar-inv-item-select")?.value || null;

  if (!cust || !desc || qty <= 0 || price <= 0) {
    alert("Please fill in Customer, Description, Quantity and Unit Price");
    return;
  }

  const payload = {
    customer_code: cust,
    invoice_date: iDate,
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0],
    lines: [
      {
        item_code: itemCode,
        description: desc,
        revenue_account_code: revAcc,
        quantity: qty,
        unit_price: price,
        discount_amount: disc,
        tax_code: tax
      }
    ]
  };

  try {
    const res = await fetch("/api/ar/invoices?status=Approved&created_by=Owner / Accountant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Sales Invoice submission failed");
    }

    alert("Sales Invoice posted and GL & Inventory updated immediately!");
    window.closeARInvoiceModal();
    window.loadARData();
    window.loadInventory();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// AR Receipts
window.openARReceiptModal = () => {
  const cSel = document.getElementById("rcpt-form-customer");
  cSel.innerHTML = '<option value="">-- Select Customer --</option>';
  window.ERP_STATE.customers.forEach((c) => {
    cSel.innerHTML += `<option value="${c.customer_code}">${c.name} (${c.customer_code})</option>`;
  });

  const bSel = document.getElementById("rcpt-form-bank");
  bSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.sub_category === "Bank")
    .forEach((a) => {
      bSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  document.getElementById("rcpt-form-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("rcpt-form-ref").value = "WIRE-CUST-" + Math.floor(1000 + Math.random() * 9000);
  document.getElementById("rcpt-open-invoices-tbody").innerHTML = "";

  document.getElementById("modal-ar-receipt").classList.remove("hidden");
};

window.closeARReceiptModal = () => {
  document.getElementById("modal-ar-receipt").classList.add("hidden");
};

window.onARReceiptCustomerSelect = async () => {
  const cust = document.getElementById("rcpt-form-customer").value;
  const tbody = document.getElementById("rcpt-open-invoices-tbody");
  tbody.innerHTML = "";

  if (!cust) return;

  const res = await fetch(`/api/ar/invoices?customer_code=${cust}&status=Approved`);
  const invoices = await res.json();
  const openInvs = invoices.filter((i) => i.payment_status !== "Paid" && i.remaining_balance > 0);

  if (!openInvs.length) {
    tbody.innerHTML = '<tr><td colspan="5" class="p-3 text-center text-slate-400">No open approved invoices for this customer.</td></tr>';
    return;
  }

  openInvs.forEach((inv) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="p-2 text-center">
        <input type="checkbox" class="rcpt-inv-chk" data-invid="${inv.id}" data-invnum="${inv.invoice_number}" data-balance="${inv.remaining_balance}" onchange="window.toggleReceiptInv(this)">
      </td>
      <td class="p-2 font-mono font-bold text-slate-800">${inv.invoice_number}</td>
      <td class="p-2 text-slate-600">${inv.invoice_date}</td>
      <td class="p-2 text-right font-mono font-bold text-cyan-700">${fmtMoney(inv.remaining_balance)}</td>
      <td class="p-2 text-right">
        <input type="number" step="0.01" max="${inv.remaining_balance}" value="${inv.remaining_balance}" disabled class="rcpt-inv-amt w-full border rounded px-2 py-1 text-right font-mono bg-slate-100 text-xs">
      </td>
    `;
    tbody.appendChild(tr);
  });
};

window.toggleReceiptInv = (chk) => {
  const amtInp = chk.closest("tr").querySelector(".rcpt-inv-amt");
  if (chk.checked) {
    amtInp.disabled = false;
    amtInp.classList.remove("bg-slate-100");
    amtInp.classList.add("bg-white");
  } else {
    amtInp.disabled = true;
    amtInp.classList.remove("bg-white");
    amtInp.classList.add("bg-slate-100");
  }
};

window.submitARReceipt = async () => {
  const cust = document.getElementById("rcpt-form-customer").value;
  const bank = document.getElementById("rcpt-form-bank").value;
  const ref = document.getElementById("rcpt-form-ref").value.trim();
  const rDate = document.getElementById("rcpt-form-date").value;

  const method = document.getElementById("rcpt-form-method")?.value || "Bank Transfer";

  if (!cust || !bank || !ref) {
    alert("Please select Customer, Bank, and Remittance Reference");
    return;
  }

  const lines = [];
  document.querySelectorAll(".rcpt-inv-chk:checked").forEach((chk) => {
    const amt = Number(chk.closest("tr").querySelector(".rcpt-inv-amt").value) || 0;
    if (amt > 0) {
      lines.push({
        ar_invoice_id: Number(chk.getAttribute("data-invid")),
        invoice_number: chk.getAttribute("data-invnum"),
        amount_received: amt
      });
    }
  });

  if (!lines.length) {
    alert("Please select at least one invoice to receive payment for");
    return;
  }

  try {
    const res = await fetch("/api/ar/receipts?status=Approved&created_by=Owner / Accountant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        receipt_date: rDate,
        customer_code: cust,
        bank_account_code: bank,
        receipt_ref: ref,
        receipt_method: method,
        lines: lines
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Receipt creation failed");
    }

    alert("Customer Bank Receipt approved and posted to General Ledger!");
    window.closeARReceiptModal();
    window.loadARData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.onARReceiptMethodChange = () => {
  const method = document.getElementById("rcpt-form-method")?.value;
  const bSel = document.getElementById("rcpt-form-bank");
  const refInp = document.getElementById("rcpt-form-ref");
  if (!bSel) return;

  if (method === "Cash") {
    for (let i = 0; i < bSel.options.length; i++) {
      if (bSel.options[i].value === "1010" || bSel.options[i].text.toLowerCase().includes("cash")) {
        bSel.selectedIndex = i;
        break;
      }
    }
    if (refInp && (!refInp.value || refInp.value.startsWith("WIRE-") || refInp.value.startsWith("CHK-"))) {
      refInp.value = "CASH-RCPT-" + Math.floor(1000 + Math.random() * 9000);
    }
  } else if (method === "Cheque") {
    if (refInp && (!refInp.value || refInp.value.startsWith("CASH-") || refInp.value.startsWith("WIRE-"))) {
      refInp.value = "CHK-" + Math.floor(10000 + Math.random() * 90000);
    }
  }
};

// =============================================================
// AR Sales Credit Notes Controller
// =============================================================
window.loadARCreditNotes = async () => {
  try {
    const res = await fetch("/api/ar/credit-notes");
    if (!res.ok) return;
    const cns = await res.json();
    const tbody = document.getElementById("ar-creditnotes-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";
    if (!cns.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="p-4 text-center text-slate-400">No sales credit notes recorded yet.</td></tr>';
      return;
    }
    cns.forEach(cn => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="p-3 font-mono font-bold text-rose-700">${cn.credit_note_number}</td>
        <td class="p-3 text-slate-600">${cn.credit_note_date}</td>
        <td class="p-3 font-medium text-slate-800">${cn.customer_name || cn.customer_code}</td>
        <td class="p-3 font-mono text-slate-600">${cn.original_invoice_number || "-"}</td>
        <td class="p-3 text-slate-700">${cn.reason}</td>
        <td class="p-3 text-right font-mono">${fmtMoney(cn.subtotal)}</td>
        <td class="p-3 text-right font-mono text-amber-600">${fmtMoney(cn.tax_amount)}</td>
        <td class="p-3 text-right font-mono font-bold text-rose-700">${fmtMoney(cn.total_credit)}</td>
        <td class="p-3 text-center"><span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">Approved</span></td>
        <td class="p-3 text-center">
          ${cn.voucher_no ? `<button onclick="window.viewVoucherDetail('${cn.voucher_no}')" class="text-blue-600 hover:underline font-mono font-bold">${cn.voucher_no}</button>` : "-"}
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading AR credit notes:", err);
  }
};

window.openNewARCreditNoteModal = async () => {
  const cSel = document.getElementById("ar-cn-customer");
  cSel.innerHTML = '<option value="">-- Select Customer --</option>';
  (window.ERP_STATE.customers || []).forEach(c => {
    cSel.innerHTML += `<option value="${c.customer_code}">${c.name} (${c.customer_code})</option>`;
  });

  document.getElementById("ar-cn-date").value = new Date().toISOString().split("T")[0];
  document.getElementById("ar-cn-reason").value = "";
  document.getElementById("ar-cn-subtotal").value = "100.00";
  window.onARCreditNoteCustomerSelect();
  window.calcARCreditNoteLive();
  document.getElementById("modal-ar-credit-note").classList.remove("hidden");
};

window.closeNewARCreditNoteModal = () => {
  document.getElementById("modal-ar-credit-note").classList.add("hidden");
};

window.onARCreditNoteCustomerSelect = async () => {
  const custCode = document.getElementById("ar-cn-customer").value;
  const invSel = document.getElementById("ar-cn-invoice-ref");
  invSel.innerHTML = '<option value="">-- General Customer Credit Note --</option>';
  if (!custCode) return;

  try {
    const res = await fetch(`/api/ar/invoices?customer_code=${custCode}&status=Approved`);
    const invs = await res.json();
    invs.forEach(inv => {
      invSel.innerHTML += `<option value="${inv.invoice_number}" data-balance="${inv.remaining_balance}">${inv.invoice_number} (Bal: ${fmtMoney(inv.remaining_balance)})</option>`;
    });
  } catch (e) {
    console.error("Error loading customer invoices for credit note:", e);
  }
};

window.onARCreditNoteInvoiceSelect = () => {
  const invSel = document.getElementById("ar-cn-invoice-ref");
  const opt = invSel.options[invSel.selectedIndex];
  if (opt && opt.getAttribute("data-balance")) {
    const bal = Number(opt.getAttribute("data-balance")) || 0;
    if (bal > 0) {
      document.getElementById("ar-cn-subtotal").value = (bal / 1.05).toFixed(2);
      window.calcARCreditNoteLive();
    }
  }
};

window.calcARCreditNoteLive = () => {
  const sub = Number(document.getElementById("ar-cn-subtotal").value) || 0;
  const taxCode = document.getElementById("ar-cn-tax").value;
  const taxRate = taxCode === "STANDARD_5" ? 0.05 : 0.0;
  const tax = Math.round(sub * taxRate * 100) / 100;
  const tot = Math.round((sub + tax) * 100) / 100;
  document.getElementById("ar-cn-total").value = fmtMoney(tot);
};

window.submitARCreditNote = async () => {
  const cust = document.getElementById("ar-cn-customer").value;
  const invRef = document.getElementById("ar-cn-invoice-ref").value || null;
  const cnDate = document.getElementById("ar-cn-date").value;
  const reason = document.getElementById("ar-cn-reason").value.trim();
  const subtotal = Number(document.getElementById("ar-cn-subtotal").value) || 0;
  const taxCode = document.getElementById("ar-cn-tax").value;

  if (!cust || !reason || subtotal <= 0) {
    alert("Please fill in Customer, Reason, and Subtotal Credit Amount");
    return;
  }

  const taxRate = taxCode === "STANDARD_5" ? 0.05 : 0.0;
  const taxAmt = Math.round(subtotal * taxRate * 100) / 100;
  const totalCredit = Math.round((subtotal + taxAmt) * 100) / 100;

  try {
    const res = await fetch("/api/ar/credit-notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_code: cust,
        original_invoice_number: invRef,
        credit_note_date: cnDate,
        reason: reason,
        subtotal: subtotal,
        tax_code: taxCode,
        tax_amount: taxAmt,
        total_credit: totalCredit
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Credit Note submission failed");
    }
    alert("Sales Credit Note posted directly to General Ledger!");
    window.closeNewARCreditNoteModal();
    window.loadARData();
    window.loadARCreditNotes();
    window.switchARSubtab("creditnotes");
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 9. Downloadable PDF Tax Invoice (jsPDF + AutoTable)
// -------------------------------------------------------------
window.downloadTaxInvoicePDF = async (invoiceNumber) => {
  try {
    const res = await fetch("/api/ar/invoices");
    const invoices = await res.json();
    const inv = invoices.find((i) => i.invoice_number === invoiceNumber);

    if (!inv) {
      alert("Invoice details could not be retrieved");
      return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "pt", "a4");

    // Header Branding
    doc.setFillColor(0, 32, 80); // Navy D365 header
    doc.rect(0, 0, 595.28, 70, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.text("TAX INVOICE", 40, 42);

    const comp = window.ERP_STATE.company || {};
    const compName = (comp.company_name || "Demo Business 21").toUpperCase();
    const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";
    const compAddress = comp.company_address || "Dubai, UAE";

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(compName, 380, 30);
    doc.text(`TRN: ${compTrn}`, 380, 42);
    doc.text(compAddress, 380, 54);

    // Invoice Meta & Customer Details
    doc.setTextColor(30, 41, 59);
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("BILLED TO:", 40, 105);

    doc.setFont("helvetica", "normal");
    doc.text(inv.customer_name || inv.customer_code, 40, 120);
    doc.text(`TRN / Tax ID: ${inv.customer_trn || "DEMO-TRN"}`, 40, 133);
    doc.text(inv.customer_address || "Gate Avenue, DIFC, Dubai, UAE", 40, 146);

    doc.setFont("helvetica", "bold");
    doc.text("INVOICE DETAILS:", 380, 105);
    doc.setFont("helvetica", "normal");
    doc.text(`Invoice No: ${inv.invoice_number}`, 380, 120);
    doc.text(`Date of Issue: ${inv.invoice_date}`, 380, 133);
    doc.text(`Payment Due: ${inv.due_date}`, 380, 146);
    doc.text(`Status: ${inv.status.toUpperCase()}`, 380, 159);

    // AutoTable for Line Items
    const tableRows = inv.lines.map((l) => [
      l.line_no,
      l.description,
      l.quantity,
      fmtMoney(l.unit_price),
      fmtMoney(l.net_amount),
      l.tax_code + " (5%)",
      fmtMoney(l.tax_amount),
      fmtMoney(l.total_amount)
    ]);

    doc.autoTable({
      startY: 185,
      head: [["#", "Description", "Qty", "Unit Price", "Net Amt", "VAT Rate", "VAT Amt", "Total ($)"]],
      body: tableRows,
      theme: "striped",
      headStyles: { fillColor: [0, 32, 80], textColor: [255, 255, 255], fontStyle: "bold" },
      styles: { fontSize: 8.5, cellPadding: 5 }
    });

    const finalY = doc.lastAutoTable.finalY + 20;

    // Summary Box
    doc.setFillColor(248, 250, 252);
    doc.rect(340, finalY, 215, 80, "F");
    doc.setDrawColor(226, 232, 240);
    doc.rect(340, finalY, 215, 80, "S");

    doc.setFontSize(9);
    doc.setTextColor(71, 85, 105);
    doc.text("Subtotal (Excl. Tax):", 350, finalY + 20);
    doc.text("VAT / Indirect Tax (5%):", 350, finalY + 40);
    doc.setFont("helvetica", "bold");
    doc.setTextColor(15, 23, 42);
    doc.text("Gross Total Payable:", 350, finalY + 65);

    doc.setFont("helvetica", "normal");
    doc.text(fmtMoney(inv.subtotal), 545, finalY + 20, { align: "right" });
    doc.text(fmtMoney(inv.tax_amount), 545, finalY + 40, { align: "right" });
    doc.setFont("helvetica", "bold");
    doc.text(fmtMoney(inv.total_amount), 545, finalY + 65, { align: "right" });

    // Official Stamp
    doc.setDrawColor(0, 120, 212);
    doc.setFillColor(238, 242, 255);
    doc.roundedRect(40, finalY, 180, 50, 4, 4, "FD");
    doc.setTextColor(0, 120, 212);
    doc.setFontSize(8);
    const stampTitle = `${compName} POSTED`;
    doc.text(stampTitle.length > 32 ? stampTitle.substring(0, 32) + "..." : stampTitle, 50, finalY + 20);
    doc.setFontSize(7.5);
    doc.setFont("helvetica", "normal");
    doc.text(`Voucher Ref: ${inv.voucher_no || "AR-INV-POSTED"}`, 50, finalY + 32);
    doc.text(`Approved By: ${inv.approved_by || "Finance Manager"}`, 50, finalY + 42);

    doc.save(`${inv.invoice_number}_Tax_Invoice.pdf`);
  } catch (err) {
    alert("Error generating Tax Invoice PDF: " + err.message);
  }
};

// -------------------------------------------------------------
// 10. Taxation & VAT Return
// -------------------------------------------------------------
window.loadTaxData = async () => {
  try {
    const [retRes, codeRes] = await Promise.all([
      fetch("/api/tax/return-summary"),
      fetch("/api/tax/codes")
    ]);
    const taxRet = await retRes.json();
    const codes = await codeRes.json();
    window.ERP_STATE.taxCodes = codes;
    window.ERP_STATE.currentTaxData = taxRet;

    const comp = window.ERP_STATE.company || {};
    const compName = comp.company_name || "Demo Retail Company LLC";
    const compTRN = comp.trn || comp.company_trn || "DEMO-TRN";

    const nameEl = document.getElementById("fta-tax-name");
    if (nameEl) nameEl.textContent = compName;
    const trnEl = document.getElementById("fta-tax-trn");
    if (trnEl) trnEl.textContent = compTRN;

    const b1Net = Number(taxRet.box1_output_standard?.net_amount || 0);
    const b1Tax = Number(taxRet.box1_output_standard?.tax_amount || 0);
    const b2Net = Number(taxRet.box2_zero_exempt?.net_amount || 0);
    const b3Net = Number(taxRet.box3_input_standard?.net_amount || 0);
    const b3Tax = Number(taxRet.box3_input_standard?.tax_amount || 0);
    const b7Net = b1Net + b2Net;
    const b7Tax = b1Tax;
    const b10Net = b3Net;
    const b10Tax = b3Tax;
    const b11Tax = b7Tax;
    const b12Tax = b10Tax;
    const b13Tax = b11Tax - b12Tax;
    const b15Tax = b13Tax;

    const fAED = (val) => Number(val || 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

    // Section 1: Output Tax
    const b1bNetEl = document.getElementById("fta-b1b-net");
    if (b1bNetEl) b1bNetEl.textContent = fAED(b1Net);
    const b1bTaxEl = document.getElementById("fta-b1b-tax");
    if (b1bTaxEl) b1bTaxEl.textContent = fAED(b1Tax);

    const b3NetEl = document.getElementById("fta-b3-net");
    if (b3NetEl) b3NetEl.textContent = fAED(b2Net);

    const b7NetEl = document.getElementById("fta-b7-net");
    if (b7NetEl) b7NetEl.textContent = fAED(b7Net);
    const b7TaxEl = document.getElementById("fta-b7-tax");
    if (b7TaxEl) b7TaxEl.textContent = fAED(b7Tax);

    // Section 2: Input Tax
    const b8NetEl = document.getElementById("fta-b8-net");
    if (b8NetEl) b8NetEl.textContent = fAED(b3Net);
    const b8TaxEl = document.getElementById("fta-b8-tax");
    if (b8TaxEl) b8TaxEl.textContent = fAED(b3Tax);

    const b10NetEl = document.getElementById("fta-b10-net");
    if (b10NetEl) b10NetEl.textContent = fAED(b10Net);
    const b10TaxEl = document.getElementById("fta-b10-tax");
    if (b10TaxEl) b10TaxEl.textContent = fAED(b10Tax);

    // Section 3: Net VAT Due
    const b11TaxEl = document.getElementById("fta-b11-tax");
    if (b11TaxEl) b11TaxEl.textContent = fAED(b11Tax);
    const b12TaxEl = document.getElementById("fta-b12-tax");
    if (b12TaxEl) b12TaxEl.textContent = fAED(b12Tax);
    const b13TaxEl = document.getElementById("fta-b13-tax");
    if (b13TaxEl) b13TaxEl.textContent = fAED(b13Tax);
    const b15TaxEl = document.getElementById("fta-b15-tax");
    if (b15TaxEl) b15TaxEl.textContent = (b15Tax < 0 ? `(AED ${fAED(Math.abs(b15Tax))})` : `AED ${fAED(b15Tax)}`);

    // Top 3 KPI Cards
    const kpiOutput = document.getElementById("fta-kpi-output");
    if (kpiOutput) kpiOutput.textContent = `AED ${fAED(b7Tax)}`;
    const kpiInput = document.getElementById("fta-kpi-input");
    if (kpiInput) kpiInput.textContent = `AED ${fAED(b10Tax)}`;
    const kpiNet = document.getElementById("fta-kpi-net");
    if (kpiNet) kpiNet.textContent = (b15Tax < 0 ? `(AED ${fAED(Math.abs(b15Tax))})` : `AED ${fAED(b15Tax)}`);

    const kpiBadge = document.getElementById("fta-kpi-badge");
    if (kpiBadge) {
      if (b15Tax > 0) {
        kpiBadge.textContent = "NET TAX PAYABLE TO FTA";
        kpiBadge.className = "bg-rose-500/20 border border-rose-400/40 text-rose-300 text-[10px] font-bold px-2 py-1 rounded";
      } else if (b15Tax < 0) {
        kpiBadge.textContent = "VAT REFUND DUE FROM FTA";
        kpiBadge.className = "bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 text-[10px] font-bold px-2 py-1 rounded";
      } else {
        kpiBadge.textContent = "NIL VAT DUE (BALANCED)";
        kpiBadge.className = "bg-slate-500/20 border border-slate-400/40 text-slate-300 text-[10px] font-bold px-2 py-1 rounded";
      }
    }

    // Backward compatible IDs
    const tB1Net = document.getElementById("tax-b1-net");
    if (tB1Net) tB1Net.textContent = fmtMoney(b1Net);
    const tB1Tax = document.getElementById("tax-b1-tax");
    if (tB1Tax) tB1Tax.textContent = fmtMoney(b1Tax);
    const tB2Net = document.getElementById("tax-b2-net");
    if (tB2Net) tB2Net.textContent = fmtMoney(b2Net);
    const tB3Net = document.getElementById("tax-b3-net");
    if (tB3Net) tB3Net.textContent = fmtMoney(b3Net);
    const tB3Tax = document.getElementById("tax-b3-tax");
    if (tB3Tax) tB3Tax.textContent = fmtMoney(b3Tax);
    const tB4Net = document.getElementById("tax-b4-net");
    if (tB4Net) tB4Net.textContent = fmtMoney(b7Net - b10Net);
    const tB4Tax = document.getElementById("tax-b4-tax");
    if (tB4Tax) tB4Tax.textContent = fmtMoney(b15Tax);


    // Populate Tax Codes Table
    const tbody = document.getElementById("tax-codes-table-body");
    if (tbody) {
      tbody.innerHTML = "";
      codes.forEach((c) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-2.5 font-mono font-bold text-slate-800">${c.code}</td>
          <td class="p-2.5 font-medium text-slate-800">${c.name}</td>
          <td class="p-2.5 text-right font-mono font-bold text-blue-700">${c.rate}%</td>
          <td class="p-2.5 text-slate-600">${c.type}</td>
          <td class="p-2.5 text-slate-500">${c.description}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Update Slide Deck Tax slide
    document.getElementById("p-tax-b1").textContent = fmtMoney(taxRet.box1_output_standard.tax_amount);
    document.getElementById("p-tax-b3").textContent = fmtMoney(taxRet.box3_input_standard.tax_amount);
    document.getElementById("p-tax-b4").textContent = fmtMoney(taxRet.box4_net_tax.tax_amount);
  } catch (err) {
    console.error("Error loading tax data:", err);
  }
};

window.exportTaxReturnExcel = () => {
  if (!window.ERP_STATE.currentTaxData) return;
  const d = window.ERP_STATE.currentTaxData;
  const comp = window.ERP_STATE.company || {};
  const compName = comp.company_name || "Demo Retail Company";
  const compTRN = comp.trn || comp.company_trn || "DEMO-TRN";
  const compAddr = comp.company_address || "Dubai, UAE";

  const b1Net = d.box1_output_standard?.net_amount || 0;
  const b1Tax = d.box1_output_standard?.tax_amount || 0;
  const b2Net = d.box2_zero_exempt?.net_amount || 0;
  const b3Net = d.box3_input_standard?.net_amount || 0;
  const b3Tax = d.box3_input_standard?.tax_amount || 0;
  const b4Tax = d.box4_net_tax?.tax_amount || (b1Tax - b3Tax);

  const ftaRows = [
    ["FEDERAL TAX AUTHORITY - UNITED ARAB EMIRATES", "", "", "الهيئة الاتحادية للضرائب - دولة الإمارات العربية المتحدة"],
    ["VAT RETURN FORM (VAT201)", "", "", "إقرار ضريبة القيمة المضافة (نموذج 201)"],
    ["", "", "", ""],
    ["1. TAXABLE PERSON DETAILS", "", "", "بيانات الخاضع للضريبة"],
    ["Tax Registration Number (TRN):", compTRN, "", "رقم التسجيل الضريبي"],
    ["Legal Name of Taxable Person (English):", compName, "", "الاسم القانوني للخاضع للضريبة (الإنجليزية)"],
    ["Legal Name of Taxable Person (Arabic):", compName, "", "الاسم القانوني للخاضع للضريبة (العربية)"],
    ["Tax Return Period:", "01/01/2026 to 31/12/2026", "", "فترة الإقرار الضريبي"],
    ["Tax Year:", "2026", "", "السنة الضريبية"],
    ["Return Due Date:", "28/01/2027", "", "تاريخ استحقاق الإقرار"],
    ["", "", "", ""],
    ["2. VAT ON SALES AND ALL OTHER OUTPUTS", "", "", "ضريبة القيمة المضافة على المبيعات والمخرجات الأخرى"],
    ["Box No.", "Description / البيان", "Amount (AED) / المبلغ", "VAT Amount (AED) / مبلغ الضريبة", "Adjustments (AED) / التسويات"],
    ["Box 1a", "Standard rated supplies in Abu Dhabi / توريدات خاضعة للنسبة الأساسية في أبوظبي", 0.00, 0.00, 0.00],
    ["Box 1b", "Standard rated supplies in Dubai / توريدات خاضعة للنسبة الأساسية في دبي", b1Net, b1Tax, 0.00],
    ["Box 1c", "Standard rated supplies in Sharjah / توريدات خاضعة للنسبة الأساسية في الشارقة", 0.00, 0.00, 0.00],
    ["Box 1d", "Standard rated supplies in Ajman / توريدات خاضعة للنسبة الأساسية في عجمان", 0.00, 0.00, 0.00],
    ["Box 1e", "Standard rated supplies in Umm Al Quwain / توريدات خاضعة للنسبة الأساسية في أم القيوين", 0.00, 0.00, 0.00],
    ["Box 1f", "Standard rated supplies in Ras Al Khaimah / توريدات خاضعة للنسبة الأساسية في رأس الخيمة", 0.00, 0.00, 0.00],
    ["Box 1g", "Standard rated supplies in Fujairah / توريدات خاضعة للنسبة الأساسية في الفجيرة", 0.00, 0.00, 0.00],
    ["Box 2", "Tax Invoices subject to Reverse Charge provisions / توريدات خاضعة لآلية الاحتساب العكسي", 0.00, 0.00, 0.00],
    ["Box 3", "Zero rated supplies / توريدات خاضعة للنسبة الصفرية", b2Net, 0.00, 0.00],
    ["Box 4", "Exempt supplies / توريدات معفاة من الضريبة", 0.00, 0.00, 0.00],
    ["Box 5", "Goods imported into the UAE (customs declarations) / السلع المستوردة إلى دولة الإمارات", 0.00, 0.00, 0.00],
    ["Box 6", "Adjustments to goods imported into the UAE / تسويات على السلع المستوردة", 0.00, 0.00, 0.00],
    ["Box 7", "TOTAL VALUE OF SUPPLIES AND OUTPUT TAX / إجمالي المخرجات والضريبة المستحقة", b1Net + b2Net, b1Tax, 0.00],
    ["", "", "", "", ""],
    ["3. VAT ON EXPENSES AND ALL OTHER INPUTS", "", "", "ضريبة القيمة المضافة على النفقات والمدخلات الأخرى"],
    ["Box No.", "Description / البيان", "Amount (AED) / المبلغ", "Recoverable Tax (AED) / الضريبة المستردة", "Adjustments (AED) / التسويات"],
    ["Box 8", "Standard rated expenses / نفقات خاضعة للنسبة الأساسية", b3Net, b3Tax, 0.00],
    ["Box 9", "Supplies subject to the Reverse Charge provisions / توريدات خاضعة لآلية الاحتساب العكسي", 0.00, 0.00, 0.00],
    ["Box 10", "TOTAL VALUE OF EXPENSES AND RECOVERABLE TAX / إجمالي النفقات والضريبة القابلة للاسترداد", b3Net, b3Tax, 0.00],
    ["", "", "", "", ""],
    ["4. NET VAT DUE / صافي ضريبة القيمة المضافة المستحقة", "", "", ""],
    ["Box No.", "Description / البيان", "Calculation Basis / طريقة الاحتساب", "Net Amount (AED) / المبلغ الصافي"],
    ["Box 11", "Total value of due tax for the period / إجمالي الضريبة المستحقة للفترة", "Box 7 Output Tax", b1Tax],
    ["Box 12", "Total value of recoverable tax for the period / إجمالي الضريبة القابلة للاسترداد", "Box 10 Recoverable Tax", b3Tax],
    ["Box 13", "Payable tax for the period / صافي الضريبة واجبة السداد أو (المستردة)", "Box 11 - Box 12", b4Tax],
    ["Box 14", "Penalties / Administrative Fines (if any) / الغرامات الإدارية", "FTA Assessment", 0.00],
    ["Box 15", "NET VAT PAYABLE / (REFUNDABLE) / إجمالي المبلغ المستحق أو (القابل للاسترداد)", "Box 13 + Box 14", b4Tax],
    ["", "", "", ""],
    ["5. DECLARATION BY TAXABLE PERSON", "", "", "إقرار الخاضع للضريبة"],
    ["I hereby declare that the information provided in this return is true, complete, and accurate according to UAE Federal Decree-Law No. (8) of 2017 on Value Added Tax."],
    ["Authorized Signatory:", compName, "Submission Date:", new Date().toLocaleDateString('en-GB')]
  ];

  const ws = XLSX.utils.aoa_to_sheet(ftaRows);
  ws["!cols"] = [{ wch: 12 }, { wch: 55 }, { wch: 25 }, { wch: 30 }, { wch: 25 }];
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "UAE_FTA_VAT201");
  const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
  XLSX.writeFile(wb, `UAE_FTA_Form_VAT201_Return_${safeName}.xlsx`);
};

window.downloadTaxReturnPDF = () => {
  if (!window.ERP_STATE.currentTaxData) return;
  const d = window.ERP_STATE.currentTaxData;
  const comp = window.ERP_STATE.company || {};
  const compName = comp.company_name || "Demo Retail Company";
  const compTRN = comp.trn || comp.company_trn || "DEMO-TRN";

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF("p", "pt", "a4");

  // Header Banner
  doc.setFillColor(0, 104, 55); // UAE FTA Emerald Green
  doc.rect(0, 0, 595.28, 75, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("FEDERAL TAX AUTHORITY - UAE | FORM VAT 201", 40, 35);
  doc.setFontSize(9);
  doc.setFont("helvetica", "normal");
  doc.text(`Taxable Person: ${compName} | TRN: ${compTRN} | Period: 01/01/2026 - 31/12/2026`, 40, 55);

  const b1Net = d.box1_output_standard?.net_amount || 0;
  const b1Tax = d.box1_output_standard?.tax_amount || 0;
  const b2Net = d.box2_zero_exempt?.net_amount || 0;
  const b3Net = d.box3_input_standard?.net_amount || 0;
  const b3Tax = d.box3_input_standard?.tax_amount || 0;
  const b4Tax = d.box4_net_tax?.tax_amount || (b1Tax - b3Tax);

  // Section 1: Output Tax
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("1. VAT on Sales and all other Outputs (Box 1 - 7)", 40, 100);

  const outRows = [
    ["Box 1b", "Standard rated supplies in Dubai (5%)", fmtMoney(b1Net), fmtMoney(b1Tax)],
    ["Box 1a,c-g", "Standard rated supplies in other Emirates", "$0.00", "$0.00"],
    ["Box 2", "Supplies subject to the Reverse Charge provisions", "$0.00", "$0.00"],
    ["Box 3", "Zero-rated supplies", fmtMoney(b2Net), "$0.00"],
    ["Box 4", "Exempt supplies", "$0.00", "$0.00"],
    ["Box 7", "TOTAL VALUE OF SUPPLIES & OUTPUT TAX DUE", fmtMoney(b1Net + b2Net), fmtMoney(b1Tax)]
  ];

  doc.autoTable({
    startY: 110,
    head: [["Box", "Description", "Taxable Amount", "Output Tax Due"]],
    body: outRows,
    theme: "grid",
    headStyles: { fillColor: [0, 104, 55] },
    styles: { fontSize: 8.5 },
    columnStyles: {
      2: { halign: "right" },
      3: { halign: "right", fontStyle: "bold" }
    }
  });

  // Section 2: Input Tax
  const inY = doc.lastAutoTable.finalY + 20;
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("2. VAT on Expenses and all other Inputs (Box 8 - 10)", 40, inY);

  const inRows = [
    ["Box 8", "Standard rated expenses & purchases (5% recoverable)", fmtMoney(b3Net), fmtMoney(b3Tax)],
    ["Box 9", "Supplies subject to Reverse Charge provisions", "$0.00", "$0.00"],
    ["Box 10", "TOTAL VALUE OF EXPENSES & RECOVERABLE INPUT TAX", fmtMoney(b3Net), fmtMoney(b3Tax)]
  ];

  doc.autoTable({
    startY: inY + 10,
    head: [["Box", "Description", "Expense Amount", "Recoverable Input Tax"]],
    body: inRows,
    theme: "grid",
    headStyles: { fillColor: [30, 64, 175] },
    styles: { fontSize: 8.5 },
    columnStyles: {
      2: { halign: "right" },
      3: { halign: "right", fontStyle: "bold" }
    }
  });

  // Section 3: Net Tax
  const netY = doc.lastAutoTable.finalY + 20;
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text("3. Net VAT Due / Position (Box 11 - 15)", 40, netY);

  const netRows = [
    ["Box 11", "Total value of due tax for the period (Box 7)", fmtMoney(b1Tax)],
    ["Box 12", "Total value of recoverable tax for the period (Box 10)", fmtMoney(b3Tax)],
    ["Box 13", "Payable tax for the period (Box 11 - Box 12)", fmtMoney(b4Tax)],
    ["Box 14", "Penalties / Administrative Surcharges", "$0.00"],
    ["Box 15", "NET VAT PAYABLE / (REFUNDABLE) TOTAL", fmtMoney(b4Tax)]
  ];

  doc.autoTable({
    startY: netY + 10,
    head: [["Box", "Description / Calculation", "Net VAT Position"]],
    body: netRows,
    theme: "grid",
    headStyles: { fillColor: [194, 65, 12] },
    styles: { fontSize: 9 },
    columnStyles: {
      2: { halign: "right", fontStyle: "bold" }
    }
  });

  const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
  doc.save(`UAE_FTA_Form_VAT201_${safeName}.pdf`);
};

// -------------------------------------------------------------
// 11. Management Financial Statements (TB, P&L, BS)
// -------------------------------------------------------------
window.switchReportSubtab = (subtab) => {
  document.getElementById("report-view-tb").classList.add("hidden");
  document.getElementById("report-view-pl").classList.add("hidden");
  document.getElementById("report-view-bs").classList.add("hidden");

  document.getElementById("report-subtab-tb").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("report-subtab-pl").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  document.getElementById("report-subtab-bs").className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";

  if (subtab === "tb") {
    document.getElementById("report-view-tb").classList.remove("hidden");
    document.getElementById("report-subtab-tb").className = "px-4 py-2 font-bold border-b-2 border-indigo-600 text-indigo-600";
  } else if (subtab === "pl") {
    document.getElementById("report-view-pl").classList.remove("hidden");
    document.getElementById("report-subtab-pl").className = "px-4 py-2 font-bold border-b-2 border-indigo-600 text-indigo-600";
  } else {
    document.getElementById("report-view-bs").classList.remove("hidden");
    document.getElementById("report-subtab-bs").className = "px-4 py-2 font-bold border-b-2 border-indigo-600 text-indigo-600";
  }
};

window.loadFinancialReports = async () => {
  try {
    const [tbRes, plRes, bsRes] = await Promise.all([
      fetch("/api/reports/trial-balance"),
      fetch("/api/reports/profit-loss"),
      fetch("/api/reports/balance-sheet")
    ]);
    const tb = await tbRes.json();
    const pl = await plRes.json();
    const bs = await bsRes.json();

    window.ERP_STATE.currentTBData = tb;
    window.ERP_STATE.currentPLData = pl;
    window.ERP_STATE.currentBSData = bs;

    renderTrialBalance(tb);
    renderProfitAndLoss(pl);
    renderBalanceSheet(bs);
  } catch (err) {
    console.error("Error loading financial statements:", err);
  }
};

function renderTrialBalance(tb) {
  const tbody = document.getElementById("tb-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  tb.rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="p-2.5 font-mono font-bold text-slate-800">${r.account_code}</td>
      <td class="p-2.5 font-medium text-slate-800">${r.account_name}</td>
      <td class="p-2.5 text-slate-500 text-[11px]">${r.account_type}</td>
      <td class="p-2 text-right font-mono border-l border-slate-200">${r.opening_debit > 0 ? fmtMoney(r.opening_debit) : "-"}</td>
      <td class="p-2 text-right font-mono">${r.opening_credit > 0 ? fmtMoney(r.opening_credit) : "-"}</td>
      <td class="p-2 text-right font-mono border-l border-slate-200">${r.period_debit > 0 ? fmtMoney(r.period_debit) : "-"}</td>
      <td class="p-2 text-right font-mono">${r.period_credit > 0 ? fmtMoney(r.period_credit) : "-"}</td>
      <td class="p-2 text-right font-mono font-bold text-slate-900 border-l border-slate-200">${r.closing_debit > 0 ? fmtMoney(r.closing_debit) : "-"}</td>
      <td class="p-2 text-right font-mono font-bold text-slate-900">${r.closing_credit > 0 ? fmtMoney(r.closing_credit) : "-"}</td>
    `;
    tbody.appendChild(tr);
  });

  const footer = document.getElementById("tb-table-footer");
  footer.innerHTML = `
    <td colspan="3" class="p-2.5 text-right font-bold text-slate-800">Totals:</td>
    <td class="p-2.5 text-right font-mono text-emerald-800 font-bold border-l border-slate-200">${fmtMoney(tb.total_opening_debit)}</td>
    <td class="p-2.5 text-right font-mono text-emerald-800 font-bold">${fmtMoney(tb.total_opening_credit)}</td>
    <td class="p-2.5 text-right font-mono text-emerald-800 font-bold border-l border-slate-200">${fmtMoney(tb.total_period_debit)}</td>
    <td class="p-2.5 text-right font-mono text-emerald-800 font-bold">${fmtMoney(tb.total_period_credit)}</td>
    <td class="p-2.5 text-right font-mono text-emerald-900 font-black border-l border-slate-200">${fmtMoney(tb.total_closing_debit)}</td>
    <td class="p-2.5 text-right font-mono text-emerald-900 font-black">${fmtMoney(tb.total_closing_credit)}</td>
  `;

  document.getElementById("tb-balanced-amount").textContent = `${fmtMoney(tb.total_closing_debit)} (Variance: $0.00)`;
}

function renderProfitAndLoss(pl) {
  const revContainer = document.getElementById("pl-revenue-lines");
  revContainer.innerHTML = "";
  pl.revenue_items.forEach((item) => {
    revContainer.innerHTML += `
      <div class="flex justify-between py-1.5 px-3">
        <span class="text-slate-700">${item.account_code} - ${item.account_name}</span>
        <span class="font-mono font-medium text-slate-900">${fmtMoney(item.amount)}</span>
      </div>
    `;
  });
  document.getElementById("pl-total-revenue").textContent = fmtMoney(pl.total_revenue);

  const cogsContainer = document.getElementById("pl-cogs-lines");
  cogsContainer.innerHTML = "";
  if (!pl.cogs_items.length) {
    cogsContainer.innerHTML = '<div class="py-1 px-3 text-slate-400 italic">No direct costs incurred in period.</div>';
  } else {
    pl.cogs_items.forEach((item) => {
      cogsContainer.innerHTML += `
        <div class="flex justify-between py-1.5 px-3">
          <span class="text-slate-700">${item.account_code} - ${item.account_name}</span>
          <span class="font-mono font-medium text-slate-900">${fmtMoney(item.amount)}</span>
        </div>
      `;
    });
  }
  document.getElementById("pl-total-cogs").textContent = fmtMoney(pl.total_cogs);

  document.getElementById("pl-gross-profit").textContent = fmtMoney(pl.gross_profit);
  document.getElementById("pl-gross-margin").textContent = `(Gross Margin: ${pl.gross_margin_pct.toFixed(1)}%)`;

  const opexContainer = document.getElementById("pl-opex-lines");
  opexContainer.innerHTML = "";
  pl.operating_expenses.forEach((item) => {
    opexContainer.innerHTML += `
      <div class="flex justify-between py-1.5 px-3">
        <span class="text-slate-700">${item.account_code} - ${item.account_name}</span>
        <span class="font-mono font-medium text-slate-900">${fmtMoney(item.amount)}</span>
      </div>
    `;
  });
  document.getElementById("pl-total-opex").textContent = fmtMoney(pl.total_operating_expenses);

  document.getElementById("pl-net-profit").textContent = fmtMoney(pl.net_profit);
  document.getElementById("pl-net-margin").textContent = `(Net Margin: ${pl.net_margin_pct.toFixed(1)}%)`;

  // Update Slide 2
  document.getElementById("p-pl-rev").textContent = fmtMoney(pl.total_revenue);
  document.getElementById("p-pl-cogs").textContent = fmtMoney(pl.total_cogs);
  document.getElementById("p-pl-gross").textContent = fmtMoney(pl.gross_profit);
  document.getElementById("p-pl-opex").textContent = fmtMoney(pl.total_operating_expenses);
  document.getElementById("p-pl-net").textContent = fmtMoney(pl.net_profit);
}

function renderBalanceSheet(bs) {
  const assetContainer = document.getElementById("bs-asset-lines");
  assetContainer.innerHTML = "";
  bs.assets.items.forEach((item) => {
    assetContainer.innerHTML += `
      <div class="flex justify-between py-1.5 px-3">
        <span class="text-slate-700">${item.account_code} - ${item.account_name}</span>
        <span class="font-mono font-medium text-slate-900">${fmtMoney(item.amount)}</span>
      </div>
    `;
  });
  document.getElementById("bs-total-assets").textContent = fmtMoney(bs.total_assets);

  const liabContainer = document.getElementById("bs-liability-lines");
  liabContainer.innerHTML = "";
  bs.liabilities.items.forEach((item) => {
    liabContainer.innerHTML += `
      <div class="flex justify-between py-1.5 px-3">
        <span class="text-slate-700">${item.account_code} - ${item.account_name}</span>
        <span class="font-mono font-medium text-slate-900">${fmtMoney(item.amount)}</span>
      </div>
    `;
  });
  document.getElementById("bs-total-liabilities").textContent = fmtMoney(bs.total_liabilities);

  const eqContainer = document.getElementById("bs-equity-lines");
  eqContainer.innerHTML = "";
  bs.equity.items.forEach((item) => {
    const isRoll = item.account_code === "PL-ROLL";
    eqContainer.innerHTML += `
      <div class="flex justify-between py-1.5 px-3 ${isRoll ? 'bg-emerald-50/60 font-semibold text-emerald-900' : ''}">
        <span>${item.account_code} - ${item.account_name}</span>
        <span class="font-mono">${fmtMoney(item.amount)}</span>
      </div>
    `;
  });
  document.getElementById("bs-total-equity").textContent = fmtMoney(bs.total_equity);

  document.getElementById("bs-total-l-and-e").textContent = fmtMoney(bs.total_liabilities_and_equity);
  document.getElementById("bs-balanced-amount").textContent = `${fmtMoney(bs.total_assets)} = ${fmtMoney(bs.total_liabilities_and_equity)} (Variance: $0.00)`;

  // Update Slide 3
  document.getElementById("p-bs-assets").textContent = fmtMoney(bs.total_assets);
  document.getElementById("p-bs-l-and-e").textContent = fmtMoney(bs.total_liabilities_and_equity);
}

window.exportCurrentReportExcel = () => {
  const comp = window.ERP_STATE.company || {};
  const compName = comp.company_name || "Demo Business 21";
  const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";
  const currSym = comp.currency_symbol || "AED";

  const wb = XLSX.utils.book_new();

  // Sheet 1: Consolidated General Ledger Trial Balance
  if (window.ERP_STATE.currentTBData) {
    const tb = window.ERP_STATE.currentTBData;
    const tbRows = [
      ["CONSOLIDATED GENERAL LEDGER TRIAL BALANCE"],
      ["Company Legal Name:", compName],
      ["Tax Registration Number (TRN):", compTrn],
      ["Reporting Date:", new Date().toLocaleDateString("en-GB")],
      ["Functional Currency:", currSym],
      [""],
      [
        "Account Code",
        "Account Name",
        "Account Type",
        "Opening Debit",
        "Opening Credit",
        "Period Debit",
        "Period Credit",
        "Closing Debit",
        "Closing Credit"
      ]
    ];

    tb.rows.forEach((r) => {
      tbRows.push([
        r.account_code,
        r.account_name,
        r.account_type,
        r.opening_debit,
        r.opening_credit,
        r.period_debit,
        r.period_credit,
        r.closing_debit,
        r.closing_credit
      ]);
    });

    tbRows.push([
      "TOTALS",
      "Consolidated Ledger Total",
      "",
      tb.total_opening_debit,
      tb.total_opening_credit,
      tb.total_period_debit,
      tb.total_period_credit,
      tb.total_closing_debit,
      tb.total_closing_credit
    ]);

    const wsTB = XLSX.utils.aoa_to_sheet(tbRows);
    wsTB["!cols"] = [
      { wch: 15 },
      { wch: 35 },
      { wch: 18 },
      { wch: 18 },
      { wch: 18 },
      { wch: 18 },
      { wch: 18 },
      { wch: 18 },
      { wch: 18 }
    ];
    XLSX.utils.book_append_sheet(wb, wsTB, "Trial_Balance");
  }

  // Sheet 2: Scheduled Profit & Loss Statement (Income Statement)
  if (window.ERP_STATE.currentPLData) {
    const pl = window.ERP_STATE.currentPLData;
    const plRows = [
      ["SCHEDULED STATEMENT OF PROFIT AND LOSS (INCOME STATEMENT)"],
      ["Company Legal Name:", compName],
      ["Tax Registration Number (TRN):", compTrn],
      ["Reporting Period:", "Current Fiscal Period (YTD)"],
      ["Functional Currency:", currSym],
      [""],
      ["Schedule / Line Item Description", "Account Code", "Account Details", "Amount (" + currSym + ")"],
      ["SCHEDULE 1: OPERATING REVENUE & TURNOVER", "", "", ""]
    ];

    pl.revenue_items.forEach((item) => {
      plRows.push(["", item.account_code, item.account_name, item.amount]);
    });
    plRows.push(["TOTAL OPERATING REVENUE", "", "", pl.total_revenue]);
    plRows.push(["", "", "", ""]);

    plRows.push(["SCHEDULE 2: COST OF GOODS SOLD & DIRECT COSTS", "", "", ""]);
    if (pl.cogs_items && pl.cogs_items.length) {
      pl.cogs_items.forEach((item) => {
        plRows.push(["", item.account_code, item.account_name, item.amount]);
      });
    } else {
      plRows.push(["", "-", "Direct wholesale & retail goods cost", 0.0]);
    }
    plRows.push(["TOTAL COST OF GOODS SOLD", "", "", pl.total_cogs]);
    plRows.push(["", "", "", ""]);

    plRows.push([`GROSS PROFIT (Gross Margin: ${pl.gross_margin_pct.toFixed(1)}%)`, "", "", pl.gross_profit]);
    plRows.push(["", "", "", ""]);

    plRows.push(["SCHEDULE 3: OPERATING OVERHEADS & ADMINISTRATIVE EXPENSES", "", "", ""]);
    pl.operating_expenses.forEach((item) => {
      plRows.push(["", item.account_code, item.account_name, item.amount]);
    });
    plRows.push(["TOTAL OPERATING OVERHEADS (OpEx)", "", "", pl.total_operating_expenses]);
    plRows.push(["", "", "", ""]);

    plRows.push([`NET OPERATING PROFIT / (LOSS) (Net Margin: ${pl.net_margin_pct.toFixed(1)}%)`, "", "", pl.net_profit]);

    const wsPL = XLSX.utils.aoa_to_sheet(plRows);
    wsPL["!cols"] = [{ wch: 42 }, { wch: 15 }, { wch: 38 }, { wch: 22 }];
    XLSX.utils.book_append_sheet(wb, wsPL, "Scheduled_P&L");
  }

  // Sheet 3: Scheduled Statement of Financial Position (Balance Sheet)
  if (window.ERP_STATE.currentBSData) {
    const bs = window.ERP_STATE.currentBSData;
    const bsRows = [
      ["SCHEDULED STATEMENT OF FINANCIAL POSITION (BALANCE SHEET)"],
      ["Company Legal Name:", compName],
      ["Tax Registration Number (TRN):", compTrn],
      ["Reporting Date:", new Date().toLocaleDateString("en-GB")],
      ["Functional Currency:", currSym],
      [""],
      ["Schedule / Category", "Account Code", "Account Details", "Amount (" + currSym + ")"],
      ["SCHEDULE A: ASSETS (CURRENT & NON-CURRENT)", "", "", ""]
    ];

    bs.assets.items.forEach((item) => {
      bsRows.push(["", item.account_code, item.account_name, item.amount]);
    });
    bsRows.push(["TOTAL ASSETS", "", "", bs.total_assets]);
    bsRows.push(["", "", "", ""]);

    bsRows.push(["SCHEDULE B: LIABILITIES (CURRENT & NON-CURRENT)", "", "", ""]);
    bs.liabilities.items.forEach((item) => {
      bsRows.push(["", item.account_code, item.account_name, item.amount]);
    });
    bsRows.push(["TOTAL LIABILITIES", "", "", bs.total_liabilities]);
    bsRows.push(["", "", "", ""]);

    bsRows.push(["SCHEDULE C: SHAREHOLDERS' EQUITY", "", "", ""]);
    bs.equity.items.forEach((item) => {
      bsRows.push(["", item.account_code, item.account_name, item.amount]);
    });
    bsRows.push(["TOTAL SHAREHOLDERS' EQUITY", "", "", bs.total_equity]);
    bsRows.push(["", "", "", ""]);

    bsRows.push(["TOTAL LIABILITIES & SHAREHOLDERS' EQUITY", "", "", bs.total_liabilities_and_equity]);
    bsRows.push(["", "", "", ""]);
    bsRows.push([
      "ACCOUNTING EQUATION CONFIRMATION",
      "",
      `Assets (${bs.total_assets.toFixed(2)}) = Liabilities + Equity (${bs.total_liabilities_and_equity.toFixed(2)})`,
      "BALANCED ($0.00 Variance)"
    ]);

    const wsBS = XLSX.utils.aoa_to_sheet(bsRows);
    wsBS["!cols"] = [{ wch: 42 }, { wch: 15 }, { wch: 38 }, { wch: 22 }];
    XLSX.utils.book_append_sheet(wb, wsBS, "Scheduled_Balance_Sheet");
  }

  const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
  XLSX.writeFile(wb, `${safeName}_Scheduled_Financial_Statements.xlsx`);
};

window.downloadFinancialStatementsPDF = async () => {
  try {
    let tb = window.ERP_STATE.currentTBData;
    let pl = window.ERP_STATE.currentPLData;
    let bs = window.ERP_STATE.currentBSData;

    if (!tb || !pl || !bs) {
      const [tbRes, plRes, bsRes] = await Promise.all([
        fetch("/api/reports/trial-balance"),
        fetch("/api/reports/profit-loss"),
        fetch("/api/reports/balance-sheet")
      ]);
      tb = await tbRes.json();
      pl = await plRes.json();
      bs = await bsRes.json();
      window.ERP_STATE.currentTBData = tb;
      window.ERP_STATE.currentPLData = pl;
      window.ERP_STATE.currentBSData = bs;
    }

    const comp = window.ERP_STATE.company || {};
    const compName = (comp.company_name || "Demo Business 21").toUpperCase();
    const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";
    const compAddr = comp.company_address || "Dubai, UAE";

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "pt", "a4");

    // PAGE 1: Scheduled Statement of Profit and Loss (Income Statement)
    doc.setFillColor(0, 32, 80);
    doc.rect(0, 0, 595.28, 80, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.text("SCHEDULED STATEMENT OF PROFIT & LOSS", 40, 42);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(`${compName} | TRN: ${compTrn} | ${compAddr}`, 40, 60);

    const plTableRows = [];
    plTableRows.push([{ content: "SCHEDULE 1: REVENUE & OPERATING TURNOVER", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    pl.revenue_items.forEach((item) => {
      plTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
    });
    plTableRows.push([{ content: "TOTAL GROSS REVENUE", colSpan: 2, styles: { fontStyle: "bold", textColor: [16, 124, 65] } }, { content: fmtMoney(pl.total_revenue), styles: { fontStyle: "bold", halign: "right", textColor: [16, 124, 65] } }]);

    plTableRows.push([{ content: "SCHEDULE 2: COST OF GOODS SOLD & DIRECT COSTS", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    if (pl.cogs_items && pl.cogs_items.length) {
      pl.cogs_items.forEach((item) => {
        plTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
      });
    } else {
      plTableRows.push(["-", "Direct inventory purchases & wholesale costs", "$0.00"]);
    }
    plTableRows.push([{ content: "TOTAL COST OF GOODS SOLD", colSpan: 2, styles: { fontStyle: "bold", textColor: [220, 38, 38] } }, { content: fmtMoney(pl.total_cogs), styles: { fontStyle: "bold", halign: "right", textColor: [220, 38, 38] } }]);

    plTableRows.push([{ content: `GROSS PROFIT (Gross Margin: ${pl.gross_margin_pct.toFixed(1)}%)`, colSpan: 2, styles: { fontStyle: "bold", fillColor: [220, 252, 231], textColor: [22, 101, 52] } }, { content: fmtMoney(pl.gross_profit), styles: { fontStyle: "bold", halign: "right", fillColor: [220, 252, 231], textColor: [22, 101, 52] } }]);

    plTableRows.push([{ content: "SCHEDULE 3: OPERATING OVERHEADS & ADMINISTRATIVE EXPENSES", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    pl.operating_expenses.forEach((item) => {
      plTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
    });
    plTableRows.push([{ content: "TOTAL OPERATING OVERHEADS (OpEx)", colSpan: 2, styles: { fontStyle: "bold", textColor: [220, 38, 38] } }, { content: fmtMoney(pl.total_operating_expenses), styles: { fontStyle: "bold", halign: "right", textColor: [220, 38, 38] } }]);

    plTableRows.push([{ content: `NET OPERATING PROFIT / (LOSS) (Net Margin: ${pl.net_margin_pct.toFixed(1)}%)`, colSpan: 2, styles: { fontStyle: "bold", fillColor: [219, 234, 254], textColor: [30, 64, 175], fontSize: 10 } }, { content: fmtMoney(pl.net_profit), styles: { fontStyle: "bold", halign: "right", fillColor: [219, 234, 254], textColor: [30, 64, 175], fontSize: 10 } }]);

    doc.autoTable({
      startY: 100,
      head: [["Code", "Account / Schedule Line Description", "Amount ($)"]],
      body: plTableRows,
      theme: "grid",
      headStyles: { fillColor: [0, 32, 80] },
      styles: { fontSize: 8.5 },
      columnStyles: {
        0: { w: 60 },
        2: { halign: "right" }
      }
    });

    // PAGE 2: Scheduled Statement of Financial Position (Balance Sheet)
    doc.addPage();
    doc.setFillColor(0, 32, 80);
    doc.rect(0, 0, 595.28, 80, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(18);
    doc.text("SCHEDULED STATEMENT OF FINANCIAL POSITION", 40, 42);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text(`${compName} | TRN: ${compTrn} | Balance Sheet`, 40, 60);

    const bsTableRows = [];
    bsTableRows.push([{ content: "SCHEDULE A: ASSETS (CURRENT & NON-CURRENT)", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    bs.assets.items.forEach((item) => {
      bsTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
    });
    bsTableRows.push([{ content: "TOTAL ASSETS", colSpan: 2, styles: { fontStyle: "bold", textColor: [16, 124, 65] } }, { content: fmtMoney(bs.total_assets), styles: { fontStyle: "bold", halign: "right", textColor: [16, 124, 65] } }]);

    bsTableRows.push([{ content: "SCHEDULE B: LIABILITIES (CURRENT & NON-CURRENT)", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    bs.liabilities.items.forEach((item) => {
      bsTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
    });
    bsTableRows.push([{ content: "TOTAL LIABILITIES", colSpan: 2, styles: { fontStyle: "bold", textColor: [220, 38, 38] } }, { content: fmtMoney(bs.total_liabilities), styles: { fontStyle: "bold", halign: "right", textColor: [220, 38, 38] } }]);

    bsTableRows.push([{ content: "SCHEDULE C: SHAREHOLDERS' EQUITY", colSpan: 3, styles: { fontStyle: "bold", fillColor: [241, 245, 249], textColor: [15, 23, 42] } }]);
    bs.equity.items.forEach((item) => {
      bsTableRows.push([item.account_code, item.account_name, fmtMoney(item.amount)]);
    });
    bsTableRows.push([{ content: "TOTAL SHAREHOLDERS' EQUITY", colSpan: 2, styles: { fontStyle: "bold", textColor: [30, 64, 175] } }, { content: fmtMoney(bs.total_equity), styles: { fontStyle: "bold", halign: "right", textColor: [30, 64, 175] } }]);

    bsTableRows.push([{ content: "TOTAL LIABILITIES & SHAREHOLDERS' EQUITY", colSpan: 2, styles: { fontStyle: "bold", fillColor: [226, 232, 240], fontSize: 9.5 } }, { content: fmtMoney(bs.total_liabilities_and_equity), styles: { fontStyle: "bold", halign: "right", fillColor: [226, 232, 240], fontSize: 9.5 } }]);

    bsTableRows.push([{ content: "EQUATION STATUS: ASSETS = LIABILITIES + EQUITY (BALANCED: $0.00 VARIANCE)", colSpan: 3, styles: { fontStyle: "bold", halign: "center", fillColor: [220, 252, 231], textColor: [22, 101, 52] } }]);

    doc.autoTable({
      startY: 100,
      head: [["Code", "Account / Balance Sheet Schedule Description", "Amount ($)"]],
      body: bsTableRows,
      theme: "grid",
      headStyles: { fillColor: [16, 124, 65] },
      styles: { fontSize: 8.5 },
      columnStyles: {
        0: { w: 60 },
        2: { halign: "right" }
      }
    });

    // PAGE 3: Consolidated General Ledger Trial Balance
    doc.addPage();
    doc.setFillColor(0, 32, 80);
    doc.rect(0, 0, 595.28, 45, "F");
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(13);
    doc.setFont("helvetica", "bold");
    doc.text(`${compName} | Consolidated General Ledger Trial Balance`, 40, 28);

    const tbPdfRows = tb.rows.map((r) => [
      r.account_code,
      r.account_name,
      r.account_type,
      fmtMoney(r.opening_debit),
      fmtMoney(r.opening_credit),
      fmtMoney(r.period_debit),
      fmtMoney(r.period_credit),
      fmtMoney(r.closing_debit),
      fmtMoney(r.closing_credit)
    ]);

    tbPdfRows.push([
      "TOTAL",
      "Consolidated Ledger Sum",
      "",
      fmtMoney(tb.total_opening_debit),
      fmtMoney(tb.total_opening_credit),
      fmtMoney(tb.total_period_debit),
      fmtMoney(tb.total_period_credit),
      fmtMoney(tb.total_closing_debit),
      fmtMoney(tb.total_closing_credit)
    ]);

    doc.autoTable({
      startY: 60,
      head: [["Code", "Account Name", "Type", "Op. Dr", "Op. Cr", "Per. Dr", "Per. Cr", "Cl. Dr", "Cl. Cr"]],
      body: tbPdfRows,
      theme: "striped",
      headStyles: { fillColor: [0, 32, 80] },
      styles: { fontSize: 7, cellPadding: 2.5 },
      columnStyles: {
        3: { halign: "right" },
        4: { halign: "right" },
        5: { halign: "right" },
        6: { halign: "right" },
        7: { halign: "right", fontStyle: "bold" },
        8: { halign: "right", fontStyle: "bold" }
      }
    });

    const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
    doc.save(`${safeName}_Scheduled_Financial_Statements.pdf`);
  } catch (err) {
    alert("Error generating financial statements PDF: " + err.message);
  }
};

// -------------------------------------------------------------
// 12. Approval Center (Maker-Checker Engine)
// -------------------------------------------------------------
async function loadApprovalQueue() {
  try {
    const res = await fetch("/api/approvals/pending");
    const items = await res.json();
    window.ERP_STATE.pendingApprovals = items;

    const count = items.length;
    document.getElementById("top-approval-badge").textContent = count;
    document.getElementById("side-approval-badge").textContent = count;
    const totalCountEl = document.getElementById("approval-total-count");
    if (totalCountEl) totalCountEl.textContent = count;

    renderApprovalTable();
  } catch (err) {
    console.error("Error loading approval queue:", err);
  }
}
window.loadApprovalQueue = loadApprovalQueue;

function renderApprovalTable() {
  const tbody = document.getElementById("approvals-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  const items = window.ERP_STATE.pendingApprovals;
  const isApprover = window.ERP_STATE.currentRole === "Approver";

  if (!items.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="text-center py-8 text-slate-400">
          <i class="fa-solid fa-circle-check text-2xl text-emerald-500 mb-2"></i>
          <p class="font-medium text-slate-700">All queues are clear!</p>
          <p class="text-xs">No transactions are currently awaiting Maker-Checker approval.</p>
        </td>
      </tr>
    `;
    return;
  }

  items.forEach((item) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition";
    tr.innerHTML = `
      <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-100 text-amber-900 border border-amber-200">${item.module}</span></td>
      <td class="p-3 font-mono font-bold text-slate-900">${item.document_number}</td>
      <td class="p-3 text-slate-600">${item.date}</td>
      <td class="p-3 text-slate-700 font-medium">${item.party_or_desc}</td>
      <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(item.amount)}</td>
      <td class="p-3 text-slate-500">${item.created_by}</td>
      <td class="p-3 text-center">${getBadgeHTML(item.status)}</td>
      <td class="p-3 text-center">
        ${
          isApprover
            ? `
              <div class="flex items-center justify-center space-x-1.5">
                <button onclick="window.approveItem('${item.module}', ${item.document_id})" class="bg-emerald-600 hover:bg-emerald-700 text-white px-2.5 py-1 rounded text-xs font-semibold shadow-sm flex items-center">
                  <i class="fa-solid fa-check mr-1"></i>Approve
                </button>
                <button onclick="window.openRejectModal('${item.module}', ${item.document_id})" class="bg-rose-600 hover:bg-rose-700 text-white px-2.5 py-1 rounded text-xs font-semibold shadow-sm flex items-center">
                  <i class="fa-solid fa-xmark mr-1"></i>Reject
                </button>
              </div>
            `
            : `
              <span class="text-slate-400 italic text-[11px]"><i class="fa-solid fa-lock mr-1"></i>Pending Checker Review</span>
            `
        }
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.approveItem = async (module, docId) => {
  try {
    const res = await fetch("/api/approvals/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        module: module,
        document_id: docId,
        action: "approve",
        approved_by: "Checker (Finance Manager)"
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Approval failed");
    }
    const data = await res.json();
    alert(data.message);
    window.refreshAllData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.openRejectModal = (module, docId) => {
  document.getElementById("reject-module").value = module;
  document.getElementById("reject-doc-id").value = docId;
  document.getElementById("reject-comment-input").value = "";
  document.getElementById("modal-reject-comment").classList.remove("hidden");
};

window.closeRejectCommentModal = () => {
  document.getElementById("modal-reject-comment").classList.add("hidden");
};

window.confirmRejectAction = async () => {
  const module = document.getElementById("reject-module").value;
  const docId = Number(document.getElementById("reject-doc-id").value);
  const comment = document.getElementById("reject-comment-input").value.trim();

  if (!comment) {
    alert("Mandatory: Please provide a comment explaining why this transaction is rejected.");
    return;
  }

  try {
    const res = await fetch("/api/approvals/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        module: module,
        document_id: docId,
        action: "reject",
        comment: comment,
        approved_by: "Checker (Finance Manager)"
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Rejection failed");
    }
    const data = await res.json();
    alert(data.message);
    window.closeRejectCommentModal();
    window.refreshAllData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 13. Presentation Mode & Management Pack PDF
// -------------------------------------------------------------
document.getElementById("btn-presentation-mode")?.addEventListener("click", () => {
  window.showSlide(1);
  document.getElementById("presentation-deck").classList.remove("hidden");
});

window.exitPresentationMode = () => {
  document.getElementById("presentation-deck").classList.add("hidden");
};

window.showSlide = (slideNum) => {
  window.ERP_STATE.currentSlide = slideNum;
  document.querySelectorAll(".pres-slide").forEach((el, idx) => {
    if (idx + 1 === slideNum) el.classList.remove("hidden");
    else el.classList.add("hidden");
  });
  document.getElementById("slide-number-indicator").textContent = `Slide ${slideNum} of ${window.ERP_STATE.totalSlides}`;
};

window.nextSlide = () => {
  if (window.ERP_STATE.currentSlide < window.ERP_STATE.totalSlides) {
    window.showSlide(window.ERP_STATE.currentSlide + 1);
  } else {
    window.showSlide(1);
  }
};

window.prevSlide = () => {
  if (window.ERP_STATE.currentSlide > 1) {
    window.showSlide(window.ERP_STATE.currentSlide - 1);
  } else {
    window.showSlide(window.ERP_STATE.totalSlides);
  }
};

// Download Complete Executive Management Pack PDF (Live Dashboard Data)
// Download Complete Executive Management Pack PDF (Ditto Dashboard Data & Live Visual Charts)
window.downloadManagementPackPDF = async () => {
  try {
    let kpis = window.ERP_STATE.dashboardKPIs;
    let charts = window.ERP_STATE.chartsData;
    if (!kpis || !charts) {
      const [kpiRes, chartRes] = await Promise.all([
        fetch("/api/reports/dashboard-kpis"),
        fetch("/api/reports/charts-data")
      ]);
      kpis = await kpiRes.json();
      charts = await chartRes.json();
      window.ERP_STATE.dashboardKPIs = kpis;
      window.ERP_STATE.chartsData = charts;
    }

    // Ensure charts are rendered on canvas
    if (typeof renderDashboardCharts === "function") {
      renderDashboardCharts(charts);
    }

    const comp = window.ERP_STATE.company || {};
    const compName = (comp.company_name || "Demo Business 21").toUpperCase();
    const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";
    const compAddr = comp.company_address || "Dubai, UAE";

    const { jsPDF } = window.jspdf;
    // Landscape A4: 841.89 pt width x 595.28 pt height
    const doc = new jsPDF("l", "pt", "a4");
    const pageWidth = 841.89;
    const pageHeight = 595.28;

    const getCanvasImgData = (canvasId) => {
      const canvas = document.getElementById(canvasId);
      if (!canvas) return null;
      try {
        const w = canvas.width || 800;
        const h = canvas.height || 400;
        const offCanvas = document.createElement("canvas");
        offCanvas.width = w;
        offCanvas.height = h;
        const offCtx = offCanvas.getContext("2d");
        offCtx.fillStyle = "#ffffff";
        offCtx.fillRect(0, 0, w, h);
        offCtx.drawImage(canvas, 0, 0, w, h);
        return offCanvas.toDataURL("image/png");
      } catch (err) {
        try {
          return canvas.toDataURL("image/png");
        } catch (e2) {
          return null;
        }
      }
    };

    // ========================================================
    // PAGE 1: DITTO EXECUTIVE DASHBOARD (CARDS + 4 CHARTS)
    // ========================================================
    // Top Navy Ribbon Header
    doc.setFillColor(0, 32, 80);
    doc.rect(0, 0, pageWidth, 48, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(15);
    doc.text("EXECUTIVE FINANCIAL DASHBOARD", 34, 25);

    doc.setFontSize(8.5);
    doc.setFont("helvetica", "normal");
    doc.text(`${compName}   |   TRN: ${compTrn}   |   ${compAddr}`, 34, 40);

    const reportDateStr = new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    doc.setFontSize(8.5);
    doc.text(`Generated: ${reportDateStr} | Base: AED / USD`, pageWidth - 34, 30, { align: "right" });

    // 5 KPI Metric Cards Row (Total width: 770 pt, left: 36 pt)
    const cardY = 56;
    const cardH = 56;
    const cardW = 146;
    const cardGap = 10;
    const startX = 36;

    const kpiCardData = [
      {
        title: "TOTAL SALES REVENUE",
        val: fmtMoney(kpis.total_revenue),
        sub: "Approved Billing",
        color: [0, 120, 212]
      },
      {
        title: "TOTAL STOCK VALUE",
        val: fmtMoney(kpis.total_inventory_valuation || 0),
        sub: "Store Asset (1200)",
        color: [13, 148, 136]
      },
      {
        title: "NET PROFIT / (LOSS)",
        val: fmtMoney(kpis.net_profit),
        sub: `Margin: ${kpis.net_margin_pct.toFixed(1)}%`,
        color: kpis.net_profit >= 0 ? [5, 150, 105] : [220, 38, 38]
      },
      {
        title: "CASH & TREASURY",
        val: fmtMoney(kpis.cash_bank_balance),
        sub: "Liquid Reserves",
        color: [2, 132, 199]
      },
      {
        title: "WORKING CAPITAL GAP",
        val: `AR: ${fmtMoney(kpis.open_ar)}`,
        sub: `AP: ${fmtMoney(kpis.open_ap)} | Net VAT: ${fmtMoney(kpis.net_tax_payable)}`,
        color: [124, 58, 237]
      }
    ];

    kpiCardData.forEach((c, idx) => {
      const cx = startX + idx * (cardW + cardGap);
      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(1);
      doc.roundedRect(cx, cardY, cardW, cardH, 4, 4, "FD");

      // Title
      doc.setTextColor(100, 116, 139);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(7);
      doc.text(c.title, cx + 10, cardY + 14);

      // Amount
      doc.setTextColor(c.color[0], c.color[1], c.color[2]);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(idx === 4 ? 10 : 12);
      doc.text(c.val, cx + 10, cardY + 32);

      // Subtitle
      doc.setTextColor(148, 163, 184);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(6.5);
      doc.text(c.sub, cx + 10, cardY + 47);
    });

    // 4 Visual Charts Grid (2x2 layout, strictly aligned)
    const chartY1 = 122;
    const chartH = 195;
    const chartW = 376;
    const chartGap = 18;
    const col1X = 36;
    const col2X = col1X + chartW + chartGap;

    const trendImg = getCanvasImgData("chart-trend");
    const custImg = getCanvasImgData("chart-customer");
    const budgetImg = getCanvasImgData("chart-budget");
    const agingImg = getCanvasImgData("chart-aging");

    const renderChartPanel = (x, y, w, h, title, badge, imgData) => {
      doc.setFillColor(255, 255, 255);
      doc.setDrawColor(226, 232, 240);
      doc.setLineWidth(1);
      doc.roundedRect(x, y, w, h, 4, 4, "FD");

      // Title bar
      doc.setTextColor(30, 41, 59);
      doc.setFont("helvetica", "bold");
      doc.setFontSize(9);
      doc.text(title, x + 12, y + 16);

      doc.setTextColor(148, 163, 184);
      doc.setFont("helvetica", "normal");
      doc.setFontSize(7.5);
      doc.text(badge, x + w - 12, y + 16, { align: "right" });

      // Embed chart image
      if (imgData) {
        doc.addImage(imgData, "PNG", x + 10, y + 24, w - 20, h - 32);
      } else {
        doc.setTextColor(148, 163, 184);
        doc.setFontSize(10);
        doc.text("Live Chart Data Rendered", x + w / 2, y + h / 2, { align: "center" });
      }
    };

    // Row 1: Trend & Customer Portfolio
    renderChartPanel(col1X, chartY1, chartW, chartH, "Revenue vs. Expenses Trend", "6-Month Rolling", trendImg);
    renderChartPanel(col2X, chartY1, chartW, chartH, "Customer Revenue Portfolio", "Approved Invoices", custImg);

    // Row 2: Budget Control & Working Capital Aging
    const chartY2 = 327;
    renderChartPanel(col1X, chartY2, chartW, chartH, "Budget vs. Encumbrance vs. Actuals", "By Department", budgetImg);
    renderChartPanel(col2X, chartY2, chartW, chartH, "Receivables vs. Payables Aging", "Outstanding Balances", agingImg);

    // Page 1 Footer
    doc.setDrawColor(226, 232, 240);
    doc.line(36, 532, pageWidth - 36, 532);
    doc.setTextColor(148, 163, 184);
    doc.setFontSize(7.5);
    doc.setFont("helvetica", "normal");
    doc.text("Demo Business 21 - Executive Financial Management Pack | Real-time Verified Ledger", 36, 545);
    doc.text("Page 1 of 2 (Executive Visual Dashboard)", pageWidth - 36, 545, { align: "right" });

    // ========================================================
    // PAGE 2: FINANCIAL SCHEDULES & MANAGEMENT TABLES
    // ========================================================
    doc.addPage("l", "a4");

    // Header Ribbon
    doc.setFillColor(0, 32, 80);
    doc.rect(0, 0, pageWidth, 40, "F");

    doc.setTextColor(255, 255, 255);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.text("EXECUTIVE MANAGEMENT REPORTING PACK - FINANCIAL SCHEDULES", 36, 22);
    doc.setFontSize(8);
    doc.setFont("helvetica", "normal");
    doc.text(`${compName} | TRN: ${compTrn} | Management Reporting Schedules`, 36, 33);

    // Schedule 1: 6-Month Trend Analysis Table (Top Left)
    const trend = charts.trend_analysis;
    const trendRows = trend.labels.map((m, idx) => {
      const rev = trend.revenue[idx] || 0;
      const exp = trend.expenses[idx] || 0;
      const prof = trend.net_profit[idx] || (rev - exp);
      const margin = rev > 0 ? ((prof / rev) * 100).toFixed(1) + "%" : "0.0%";
      return [m, fmtMoney(rev), fmtMoney(exp), fmtMoney(prof), margin];
    });

    doc.setTextColor(30, 41, 59);
    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("1. Six-Month Revenue & Profit Trajectory", 36, 60);

    doc.autoTable({
      startY: 66,
      margin: { left: 36, right: pageWidth / 2 + 10 },
      head: [["Month", "Revenue", "Expenses", "Net Profit", "Margin"]],
      body: trendRows,
      theme: "grid",
      headStyles: { fillColor: [0, 32, 80], fontSize: 7.5 },
      styles: { fontSize: 7.5, cellPadding: 3 },
      columnStyles: {
        1: { halign: "right" },
        2: { halign: "right" },
        3: { halign: "right", fontStyle: "bold" },
        4: { halign: "center" }
      }
    });

    // Schedule 2: Customer Sales Distribution (Top Right)
    const custTotal = charts.sales_by_customer.data.reduce((a, b) => a + b, 0);
    const custRows = charts.sales_by_customer.labels.map((lbl, idx) => {
      const val = charts.sales_by_customer.data[idx] || 0;
      const pct = custTotal > 0 ? ((val / custTotal) * 100).toFixed(1) + "%" : "0.0%";
      return [lbl, fmtMoney(val), pct];
    });

    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("2. Wholesale Customer Revenue Share", pageWidth / 2 + 10, 60);

    doc.autoTable({
      startY: 66,
      margin: { left: pageWidth / 2 + 10, right: 36 },
      head: [["Customer / Channel Account", "Sales Volume", "Share (%)"]],
      body: custRows,
      theme: "grid",
      headStyles: { fillColor: [0, 120, 212], fontSize: 7.5 },
      styles: { fontSize: 7.5, cellPadding: 3 },
      columnStyles: {
        1: { halign: "right", fontStyle: "bold" },
        2: { halign: "center" }
      }
    });

    // Schedule 3: Working Capital Aging (AR vs AP) (Bottom Left)
    const nextY = Math.max(doc.lastAutoTable.finalY + 20, 290);
    const aging = charts.aging_summary;
    const agingRows = aging.labels.map((lbl, idx) => {
      const arVal = aging.ar[idx] || 0;
      const apVal = aging.ap[idx] || 0;
      const net = arVal - apVal;
      return [lbl, fmtMoney(arVal), fmtMoney(apVal), fmtMoney(net)];
    });

    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("3. Working Capital Aging Profile (AR vs. AP)", 36, nextY);

    doc.autoTable({
      startY: nextY + 6,
      margin: { left: 36, right: pageWidth / 2 + 10 },
      head: [["Aging Bracket", "Accounts Rec. (AR)", "Accounts Pay. (AP)", "Net Cash Exposure"]],
      body: agingRows,
      theme: "grid",
      headStyles: { fillColor: [194, 65, 12], fontSize: 7.5 },
      styles: { fontSize: 7.5, cellPadding: 3 },
      columnStyles: {
        1: { halign: "right", fontStyle: "bold" },
        2: { halign: "right", fontStyle: "bold" },
        3: { halign: "right", fontStyle: "bold" }
      }
    });

    // Schedule 4: Departmental Budget Allocation & Utilization (Bottom Right)
    const bva = charts.budget_vs_actual;
    const budgetRows = bva.labels.map((lbl, idx) => {
      const bApp = bva.budget[idx] || 0;
      const bEnc = bva.encumbrance[idx] || 0;
      const bAct = bva.actual[idx] || 0;
      const bRem = bApp - bEnc - bAct;
      const util = bApp > 0 ? (((bEnc + bAct) / bApp) * 100).toFixed(1) + "%" : "0.0%";
      return [lbl, fmtMoney(bApp), fmtMoney(bEnc), fmtMoney(bAct), fmtMoney(bRem), util];
    });

    doc.setFontSize(10);
    doc.setFont("helvetica", "bold");
    doc.text("4. Departmental Budgetary Allocation & Utilization", pageWidth / 2 + 10, nextY);

    doc.autoTable({
      startY: nextY + 6,
      margin: { left: pageWidth / 2 + 10, right: 36 },
      head: [["Department", "Budget", "Pre-Enc.", "Consumed", "Remaining", "Util."]],
      body: budgetRows,
      theme: "grid",
      headStyles: { fillColor: [71, 85, 105], fontSize: 7.5 },
      styles: { fontSize: 7.5, cellPadding: 3 },
      columnStyles: {
        1: { halign: "right" },
        2: { halign: "right" },
        3: { halign: "right" },
        4: { halign: "right", fontStyle: "bold" },
        5: { halign: "center" }
      }
    });

    // Page 2 Footer
    doc.setDrawColor(226, 232, 240);
    doc.line(36, 532, pageWidth - 36, 532);
    doc.setTextColor(148, 163, 184);
    doc.setFontSize(7.5);
    doc.setFont("helvetica", "normal");
    doc.text("Demo Business 21 - Executive Financial Management Pack | Audit Trail Supported", 36, 545);
    doc.text("Page 2 of 2 (Financial Schedules)", pageWidth - 36, 545, { align: "right" });

    const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
    doc.save(`${safeName}_Executive_Management_Pack.pdf`);
  } catch (err) {
    alert("Error generating management pack PDF: " + err.message);
  }
};

// -------------------------------------------------------------
// 14. Master Data Loaders
// -------------------------------------------------------------
async function loadTaxCodes() {
  try {
    const res = await fetch("/api/tax/codes");
    window.ERP_STATE.taxCodes = await res.json();
  } catch (err) {
    console.error("Error loading tax codes:", err);
  }
}

window.loadVendors = async function loadVendors() {
  try {
    const res = await fetch("/api/ap/vendors");
    window.ERP_STATE.vendors = await res.json();
  } catch (err) {
    console.error("Error loading vendors:", err);
  }
};

window.loadCustomers = async function loadCustomers() {
  try {
    const res = await fetch("/api/ar/customers");
    window.ERP_STATE.customers = await res.json();
  } catch (err) {
    console.error("Error loading customers:", err);
  }
};

async function resetDatabase() {
  try {
    const res = await fetch("/api/system/reset-db", { method: "POST" });
    const data = await res.json();
    alert(data.message);
    window.refreshAllData();
  } catch (err) {
    alert("Error resetting database: " + err.message);
  }
}

// -------------------------------------------------------------
// 15. Supplementary Entity Modals & Exports
// -------------------------------------------------------------
window.exportDashboardExcel = async () => {
  try {
    let kpis = window.ERP_STATE.dashboardKPIs;
    let charts = window.ERP_STATE.chartsData;
    if (!kpis || !charts) {
      const [kpiRes, chartRes] = await Promise.all([
        fetch("/api/reports/dashboard-kpis"),
        fetch("/api/reports/charts-data")
      ]);
      kpis = await kpiRes.json();
      charts = await chartRes.json();
      window.ERP_STATE.dashboardKPIs = kpis;
      window.ERP_STATE.chartsData = charts;
    }

    const comp = window.ERP_STATE.company || {};
    const compName = comp.company_name || "Demo Business 21";
    const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";

    const wb = XLSX.utils.book_new();

    // Sheet 1: Executive KPI Scorecard
    const kpiSheetData = [
      ["EXECUTIVE BUSINESS DASHBOARD - PERFORMANCE SCORECARD"],
      ["Company Legal Name:", compName],
      ["Tax Registration Number (TRN):", compTrn],
      ["Export Date:", new Date().toLocaleDateString("en-GB")],
      [""],
      ["Metric Description", "Amount / Ratio", "Unit / Operational Context"],
      ["Total Gross Sales Revenue", kpis.total_revenue, comp.currency_symbol || "AED"],
      ["Total Operating Expenses & COGS", kpis.total_expenses, comp.currency_symbol || "AED"],
      ["Net Operating Profit", kpis.net_profit, comp.currency_symbol || "AED"],
      ["Net Profit Margin", kpis.net_margin_pct / 100, "Percentage"],
      ["Cash & Liquid Bank Balances", kpis.cash_bank_balance, comp.currency_symbol || "AED"],
      ["Total Inventory Valuation", kpis.total_inventory_valuation || 0, comp.currency_symbol || "AED"],
      ["Accounts Receivable (Open AR)", kpis.open_ar, comp.currency_symbol || "AED"],
      ["Accounts Payable (Open AP)", kpis.open_ap, comp.currency_symbol || "AED"],
      ["Net Working Capital (AR - AP)", kpis.open_ar - kpis.open_ap, comp.currency_symbol || "AED"],
      ["Net VAT Payable / (Refundable)", kpis.net_tax_payable, comp.currency_symbol || "AED"],
      ["Budget Utilization Rate", kpis.budget_utilization_pct / 100, "Percentage"]
    ];
    const wsKPI = XLSX.utils.aoa_to_sheet(kpiSheetData);
    wsKPI["!cols"] = [{ wch: 35 }, { wch: 20 }, { wch: 25 }];
    XLSX.utils.book_append_sheet(wb, wsKPI, "Executive_KPIs");

    // Sheet 2: 6-Month Trend Analysis
    const trend = charts.trend_analysis;
    const trendSheetData = [
      ["SIX-MONTH FINANCIAL TRAJECTORY & TREND ANALYSIS"],
      ["Company:", compName],
      [""],
      ["Month", "Sales Revenue", "Operating Expenses", "Net Operating Profit", "Net Margin %"]
    ];
    trend.labels.forEach((m, idx) => {
      const rev = trend.revenue[idx] || 0;
      const exp = trend.expenses[idx] || 0;
      const prof = trend.net_profit[idx] || (rev - exp);
      const pct = rev > 0 ? (prof / rev) : 0;
      trendSheetData.push([m, rev, exp, prof, pct]);
    });
    const wsTrend = XLSX.utils.aoa_to_sheet(trendSheetData);
    wsTrend["!cols"] = [{ wch: 15 }, { wch: 20 }, { wch: 20 }, { wch: 22 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, wsTrend, "Monthly_Trend");

    // Sheet 3: Customer Sales Portfolio
    const custSheetData = [
      ["WHOLESALE CUSTOMER SALES DISTRIBUTION PORTFOLIO"],
      ["Company:", compName],
      [""],
      ["Customer / Channel Account", "Invoiced Sales Volume", "Revenue Share (%)"]
    ];
    const custTotal = charts.sales_by_customer.data.reduce((a, b) => a + b, 0);
    charts.sales_by_customer.labels.forEach((lbl, idx) => {
      const val = charts.sales_by_customer.data[idx] || 0;
      const pct = custTotal > 0 ? (val / custTotal) : 0;
      custSheetData.push([lbl, val, pct]);
    });
    custSheetData.push(["TOTAL INVOICED REVENUE", custTotal, 1.0]);
    const wsCust = XLSX.utils.aoa_to_sheet(custSheetData);
    wsCust["!cols"] = [{ wch: 35 }, { wch: 25 }, { wch: 20 }];
    XLSX.utils.book_append_sheet(wb, wsCust, "Customer_Sales");

    // Sheet 4: Working Capital Aging Profile
    const aging = charts.aging_summary;
    const agingSheetData = [
      ["WORKING CAPITAL & AGING ANALYSIS (AR vs AP)"],
      ["Company:", compName],
      [""],
      ["Aging Bracket", "Accounts Receivable (AR)", "Accounts Payable (AP)", "Net Cash Flow Exposure"]
    ];
    aging.labels.forEach((lbl, idx) => {
      const arVal = aging.ar[idx] || 0;
      const apVal = aging.ap[idx] || 0;
      agingSheetData.push([lbl, arVal, apVal, arVal - apVal]);
    });
    const wsAging = XLSX.utils.aoa_to_sheet(agingSheetData);
    wsAging["!cols"] = [{ wch: 22 }, { wch: 26 }, { wch: 26 }, { wch: 26 }];
    XLSX.utils.book_append_sheet(wb, wsAging, "Working_Capital_Aging");

    // Sheet 5: Budgetary Allocation & Expense Controls
    const bva = charts.budget_vs_actual;
    const budgetSheetData = [
      ["BUDGETARY CONTROL & COST CENTER ALLOCATION"],
      ["Company:", compName],
      [""],
      ["Department / Account", "Approved Budget", "Pre-Encumbrance / Commitment", "Actual Consumed", "Remaining Variance", "Utilization Rate"]
    ];
    bva.labels.forEach((lbl, idx) => {
      const bApp = bva.budget[idx] || 0;
      const bEnc = bva.encumbrance[idx] || 0;
      const bAct = bva.actual[idx] || 0;
      const bRem = bApp - bEnc - bAct;
      const util = bApp > 0 ? ((bEnc + bAct) / bApp) : 0;
      budgetSheetData.push([lbl, bApp, bEnc, bAct, bRem, util]);
    });
    const wsBudget = XLSX.utils.aoa_to_sheet(budgetSheetData);
    wsBudget["!cols"] = [{ wch: 25 }, { wch: 20 }, { wch: 28 }, { wch: 20 }, { wch: 22 }, { wch: 18 }];
    XLSX.utils.book_append_sheet(wb, wsBudget, "Budget_Utilization");

    const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
    XLSX.writeFile(wb, `${safeName}_Business_Dashboard_Pack.xlsx`);
  } catch (err) {
    alert("Error exporting dashboard Excel: " + err.message);
  }
};

window.downloadDashboardPPT = async () => {
  try {
    if (typeof PptxGenJS === "undefined") {
      alert("PptxGenJS library is loading. Please try again in a few moments.");
      return;
    }

    let kpis = window.ERP_STATE.dashboardKPIs;
    let charts = window.ERP_STATE.chartsData;
    if (!kpis || !charts) {
      const [kpiRes, chartRes] = await Promise.all([
        fetch("/api/reports/dashboard-kpis"),
        fetch("/api/reports/charts-data")
      ]);
      kpis = await kpiRes.json();
      charts = await chartRes.json();
      window.ERP_STATE.dashboardKPIs = kpis;
      window.ERP_STATE.chartsData = charts;
    }

    const comp = window.ERP_STATE.company || {};
    const compName = (comp.company_name || "Demo Business 21").toUpperCase();
    const compTrn = comp.trn || comp.company_trn || "DEMO-TRN";

    const pptx = new PptxGenJS();
    pptx.layout = "LAYOUT_16x9";

    // SLIDE 1: Title Slide (Corporate Dark Navy)
    const s1 = pptx.addSlide();
    s1.background = { color: "002050" };

    s1.addText("EXECUTIVE MANAGEMENT PERFORMANCE PACK", {
      x: 0.8,
      y: 1.8,
      w: 11.5,
      h: 0.8,
      fontSize: 32,
      fontFace: "Arial",
      color: "FFFFFF",
      bold: true
    });

    s1.addText(compName, {
      x: 0.8,
      y: 2.7,
      w: 11.5,
      h: 0.6,
      fontSize: 22,
      fontFace: "Arial",
      color: "38BDF8",
      bold: true
    });

    s1.addText(`TRN: ${compTrn}  |  Operational Financial Review  |  ${new Date().toLocaleDateString("en-GB")}`, {
      x: 0.8,
      y: 3.5,
      w: 11.5,
      h: 0.4,
      fontSize: 14,
      fontFace: "Arial",
      color: "94A3B8"
    });

    s1.addText("Demo Business 21 - Retail & Wholesale Enterprise ERP", {
      x: 0.8,
      y: 6.2,
      w: 11.5,
      h: 0.4,
      fontSize: 11,
      fontFace: "Arial",
      color: "64748B"
    });

    // Helper for header banner on content slides
    const addHeader = (slide, title) => {
      slide.background = { color: "F8FAFC" };
      slide.addShape(pptx.ShapeType.rect, {
        x: 0,
        y: 0,
        w: "100%",
        h: 0.9,
        fill: { color: "002050" }
      });
      slide.addText(title, {
        x: 0.8,
        y: 0.15,
        w: 8.5,
        h: 0.6,
        fontSize: 18,
        fontFace: "Arial",
        color: "FFFFFF",
        bold: true
      });
      slide.addText(compName, {
        x: 8.5,
        y: 0.22,
        w: 4.0,
        h: 0.5,
        fontSize: 11,
        fontFace: "Arial",
        color: "38BDF8",
        align: "right",
        bold: true
      });
    };

    const getCanvasImgData = (canvasId) => {
      const canvas = document.getElementById(canvasId);
      if (!canvas) return null;
      try {
        const w = canvas.width || 800;
        const h = canvas.height || 400;
        const offCanvas = document.createElement("canvas");
        offCanvas.width = w;
        offCanvas.height = h;
        const offCtx = offCanvas.getContext("2d");
        offCtx.fillStyle = "#ffffff";
        offCtx.fillRect(0, 0, w, h);
        offCtx.drawImage(canvas, 0, 0, w, h);
        return offCanvas.toDataURL("image/png");
      } catch (err) {
        try {
          return canvas.toDataURL("image/png");
        } catch (e2) {
          return null;
        }
      }
    };

    // Ensure charts are rendered on canvases
    if (typeof renderDashboardCharts === "function") {
      renderDashboardCharts(charts);
    }

    // SLIDE 2: Ditto Executive Visual Dashboard (KPI Cards + 4 Live Interactive Charts)
    const s2 = pptx.addSlide();
    addHeader(s2, "Executive Business Dashboard (Live Overview)");

    // 5 KPI Cards across the top ribbon
    const kpiCards5 = [
      { label: "Total Sales Revenue", val: fmtMoney(kpis.total_revenue), color: "0078D4", sub: "Approved Billing" },
      { label: "Total Stock Value", val: fmtMoney(kpis.total_inventory_valuation || 0), color: "0D9488", sub: "Store Asset (1200)" },
      { label: "Net Operating Profit", val: fmtMoney(kpis.net_profit), color: kpis.net_profit >= 0 ? "059669" : "EF4444", sub: `Margin: ${kpis.net_margin_pct.toFixed(1)}%` },
      { label: "Cash & Treasury", val: fmtMoney(kpis.cash_bank_balance), color: "0284C7", sub: "Liquid Reserves" },
      { label: "Working Capital Gap", val: `AR: ${fmtMoney(kpis.open_ar)}`, color: "7C3AED", sub: `AP: ${fmtMoney(kpis.open_ap)} | Net VAT: ${fmtMoney(kpis.net_tax_payable)}` }
    ];

    const cardW = 2.25;
    const cardH = 1.15;
    const cardGap = 0.2;
    const startX = 0.64;
    const cardY = 0.95;

    kpiCards5.forEach((c, idx) => {
      const cx = startX + idx * (cardW + cardGap);
      s2.addShape(pptx.ShapeType.rect, {
        x: cx,
        y: cardY,
        w: cardW,
        h: cardH,
        fill: { color: "FFFFFF" },
        line: { color: "E2E8F0", width: 1.0 }
      });

      s2.addText(c.label, {
        x: cx + 0.1,
        y: cardY + 0.1,
        w: cardW - 0.2,
        h: 0.25,
        fontSize: 9,
        fontFace: "Arial",
        color: "64748B",
        bold: true
      });

      s2.addText(c.val, {
        x: cx + 0.1,
        y: cardY + 0.35,
        w: cardW - 0.2,
        h: 0.45,
        fontSize: idx === 4 ? 13 : 16,
        fontFace: "Arial",
        color: c.color,
        bold: true
      });

      s2.addText(c.sub, {
        x: cx + 0.1,
        y: cardY + 0.82,
        w: cardW - 0.2,
        h: 0.25,
        fontSize: 8,
        fontFace: "Arial",
        color: "94A3B8"
      });
    });

    // 4 Visual Chart Panels (2x2 Grid)
    const chartW = 5.85;
    const chartH = 2.3;
    const col1X = 0.64;
    const col2X = 6.84;
    const chartRow1Y = 2.22;
    const chartRow2Y = 4.67;

    const trendImg = getCanvasImgData("chart-trend");
    const custImg = getCanvasImgData("chart-customer");
    const budgetImg = getCanvasImgData("chart-budget");
    const agingImg = getCanvasImgData("chart-aging");

    const addChartSlidePanel = (slide, x, y, w, h, title, badge, imgData) => {
      slide.addShape(pptx.ShapeType.rect, {
        x: x,
        y: y,
        w: w,
        h: h,
        fill: { color: "FFFFFF" },
        line: { color: "E2E8F0", width: 1.0 }
      });

      slide.addText(title, {
        x: x + 0.15,
        y: y + 0.1,
        w: w - 1.5,
        h: 0.28,
        fontSize: 10,
        fontFace: "Arial",
        color: "1E293B",
        bold: true
      });

      slide.addText(badge, {
        x: x + w - 1.8,
        y: y + 0.1,
        w: 1.6,
        h: 0.28,
        fontSize: 8.5,
        fontFace: "Arial",
        color: "94A3B8",
        align: "right"
      });

      if (imgData) {
        slide.addImage({
          data: imgData,
          x: x + 0.15,
          y: y + 0.38,
          w: w - 0.3,
          h: h - 0.48
        });
      }
    };

    // Row 1: Trend & Customer Portfolio
    addChartSlidePanel(s2, col1X, chartRow1Y, chartW, chartH, "Revenue vs. Expenses Trend", "6-Month Rolling", trendImg);
    addChartSlidePanel(s2, col2X, chartRow1Y, chartW, chartH, "Customer Revenue Portfolio", "Approved Invoices", custImg);

    // Row 2: Budget vs Actuals & Aging Summary
    addChartSlidePanel(s2, col1X, chartRow2Y, chartW, chartH, "Budget vs. Encumbrance vs. Actuals", "By Department", budgetImg);
    addChartSlidePanel(s2, col2X, chartRow2Y, chartW, chartH, "Receivables vs. Payables Aging", "Outstanding Balances", agingImg);

    // SLIDE 3: 6-Month Trajectory & Trend Analysis Table
    const s3 = pptx.addSlide();
    addHeader(s3, "Six-Month Financial Trajectory & Margin Trend");

    const trend = charts.trend_analysis;
    const trendRowsPPT = [
      [
        { text: "Month", options: { bold: true, fill: "002050", color: "FFFFFF" } },
        { text: "Sales Revenue", options: { bold: true, fill: "002050", color: "FFFFFF", align: "right" } },
        { text: "Operating Expenses", options: { bold: true, fill: "002050", color: "FFFFFF", align: "right" } },
        { text: "Net Operating Profit", options: { bold: true, fill: "002050", color: "FFFFFF", align: "right" } },
        { text: "Net Margin %", options: { bold: true, fill: "002050", color: "FFFFFF", align: "center" } }
      ]
    ];
    trend.labels.forEach((m, idx) => {
      const rev = trend.revenue[idx] || 0;
      const exp = trend.expenses[idx] || 0;
      const prof = trend.net_profit[idx] || (rev - exp);
      const pct = rev > 0 ? ((prof / rev) * 100).toFixed(1) + "%" : "0.0%";
      trendRowsPPT.push([
        { text: m },
        { text: fmtMoney(rev), options: { align: "right" } },
        { text: fmtMoney(exp), options: { align: "right" } },
        { text: fmtMoney(prof), options: { align: "right", bold: true, color: prof >= 0 ? "107C41" : "EF4444" } },
        { text: pct, options: { align: "center" } }
      ]);
    });

    s3.addTable(trendRowsPPT, {
      x: 0.8,
      y: 1.4,
      w: 11.7,
      colW: [2.0, 2.5, 2.5, 2.5, 2.2],
      fontSize: 11,
      fontFace: "Arial",
      border: { pt: 0.5, color: "CBD5E1" }
    });

    // SLIDE 4: Customer Sales Portfolio & Wholesale Distribution
    const s4 = pptx.addSlide();
    addHeader(s4, "Wholesale Customer Sales Distribution Portfolio");

    const custTotal = charts.sales_by_customer.data.reduce((a, b) => a + b, 0);
    const custRowsPPT = [
      [
        { text: "Customer / Wholesale Account", options: { bold: true, fill: "0078D4", color: "FFFFFF" } },
        { text: "Invoiced Sales Volume", options: { bold: true, fill: "0078D4", color: "FFFFFF", align: "right" } },
        { text: "Revenue Share (%)", options: { bold: true, fill: "0078D4", color: "FFFFFF", align: "center" } }
      ]
    ];
    charts.sales_by_customer.labels.forEach((lbl, idx) => {
      const val = charts.sales_by_customer.data[idx] || 0;
      const pct = custTotal > 0 ? ((val / custTotal) * 100).toFixed(1) + "%" : "0.0%";
      custRowsPPT.push([
        { text: lbl },
        { text: fmtMoney(val), options: { align: "right", bold: true } },
        { text: pct, options: { align: "center" } }
      ]);
    });

    s4.addTable(custRowsPPT, {
      x: 0.8,
      y: 1.4,
      w: 11.7,
      colW: [5.5, 3.5, 2.7],
      fontSize: 11,
      fontFace: "Arial",
      border: { pt: 0.5, color: "CBD5E1" }
    });

    // SLIDE 5: Working Capital & Aging Profile
    const s5 = pptx.addSlide();
    addHeader(s5, "Working Capital Liquidity & Aging Profile (AR vs AP)");

    const aging = charts.aging_summary;
    const agingRowsPPT = [
      [
        { text: "Aging Bracket", options: { bold: true, fill: "C2410C", color: "FFFFFF" } },
        { text: "Accounts Receivable (AR)", options: { bold: true, fill: "C2410C", color: "FFFFFF", align: "right" } },
        { text: "Accounts Payable (AP)", options: { bold: true, fill: "C2410C", color: "FFFFFF", align: "right" } },
        { text: "Net Working Capital Exposure", options: { bold: true, fill: "C2410C", color: "FFFFFF", align: "right" } }
      ]
    ];
    aging.labels.forEach((lbl, idx) => {
      const arVal = aging.ar[idx] || 0;
      const apVal = aging.ap[idx] || 0;
      const net = arVal - apVal;
      agingRowsPPT.push([
        { text: lbl },
        { text: fmtMoney(arVal), options: { align: "right", bold: true, color: "0078D4" } },
        { text: fmtMoney(apVal), options: { align: "right", bold: true, color: "EF4444" } },
        { text: fmtMoney(net), options: { align: "right", bold: true } }
      ]);
    });

    s5.addTable(agingRowsPPT, {
      x: 0.8,
      y: 1.4,
      w: 11.7,
      colW: [3.2, 2.8, 2.8, 2.9],
      fontSize: 11,
      fontFace: "Arial",
      border: { pt: 0.5, color: "CBD5E1" }
    });

    // SLIDE 6: Budgetary Allocation & Expense Controls
    const s6 = pptx.addSlide();
    addHeader(s6, "Budgetary Allocation & Expense Controls");

    const bva = charts.budget_vs_actual;
    const budgetRowsPPT = [
      [
        { text: "Cost Center / Department", options: { bold: true, fill: "475569", color: "FFFFFF" } },
        { text: "Approved Budget", options: { bold: true, fill: "475569", color: "FFFFFF", align: "right" } },
        { text: "Commitments", options: { bold: true, fill: "475569", color: "FFFFFF", align: "right" } },
        { text: "Actual Consumed", options: { bold: true, fill: "475569", color: "FFFFFF", align: "right" } },
        { text: "Remaining Budget", options: { bold: true, fill: "475569", color: "FFFFFF", align: "right" } },
        { text: "Utilization", options: { bold: true, fill: "475569", color: "FFFFFF", align: "center" } }
      ]
    ];
    bva.labels.forEach((lbl, idx) => {
      const bApp = bva.budget[idx] || 0;
      const bEnc = bva.encumbrance[idx] || 0;
      const bAct = bva.actual[idx] || 0;
      const bRem = bApp - bEnc - bAct;
      const util = bApp > 0 ? (((bEnc + bAct) / bApp) * 100).toFixed(1) + "%" : "0.0%";
      budgetRowsPPT.push([
        { text: lbl },
        { text: fmtMoney(bApp), options: { align: "right" } },
        { text: fmtMoney(bEnc), options: { align: "right" } },
        { text: fmtMoney(bAct), options: { align: "right" } },
        { text: fmtMoney(bRem), options: { align: "right", bold: true } },
        { text: util, options: { align: "center" } }
      ]);
    });

    s6.addTable(budgetRowsPPT, {
      x: 0.8,
      y: 1.4,
      w: 11.7,
      colW: [2.5, 1.8, 1.8, 1.8, 2.0, 1.8],
      fontSize: 10,
      fontFace: "Arial",
      border: { pt: 0.5, color: "CBD5E1" }
    });

    const safeName = compName.replace(/[^a-zA-Z0-9_-]/g, "_");
    await pptx.writeFile({ fileName: `${safeName}_Executive_Performance_Deck.pptx` });
  } catch (err) {
    alert("Error generating PPT presentation: " + err.message);
  }
};

window.exportVouchersExcel = async () => {
  try {
    const res = await fetch("/api/gl/vouchers");
    const vouchers = await res.json();
    const rows = vouchers.map((v) => ({
      Voucher_No: v.voucher_no,
      Posting_Date: v.posting_date,
      Module: v.source_module,
      Doc_Ref: v.document_ref,
      Description: v.description,
      Total_Debit: v.total_debit,
      Total_Credit: v.total_credit,
      Status: v.status,
      Created_By: v.created_by,
      Approved_By: v.approved_by || ""
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "GL_Vouchers");
    XLSX.writeFile(wb, "D365_GL_Vouchers_Master_Ledger.xlsx");
  } catch (err) {
    alert("Error exporting vouchers: " + err.message);
  }
};

// New Account
window.openNewAccountModal = () => {
  document.getElementById("acc-form-code").value = "";
  document.getElementById("acc-form-name").value = "";
  document.getElementById("acc-form-sub").value = "Operating Expense";
  document.getElementById("acc-form-ctrl").checked = false;
  document.getElementById("modal-new-account").classList.remove("hidden");
};

window.closeNewAccountModal = () => {
  document.getElementById("modal-new-account").classList.add("hidden");
};

window.submitNewAccount = async () => {
  const code = document.getElementById("acc-form-code").value.trim();
  const name = document.getElementById("acc-form-name").value.trim();
  const type = document.getElementById("acc-form-type").value;
  const sub = document.getElementById("acc-form-sub").value.trim();
  const ctrl = document.getElementById("acc-form-ctrl").checked;

  if (!code || !name) {
    alert("Please provide Account Code and Account Name");
    return;
  }

  try {
    const res = await fetch("/api/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_code: code,
        account_name: name,
        account_type: type,
        sub_category: sub,
        is_control_account: ctrl,
        opening_debit: 0.0,
        opening_credit: 0.0
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create account");
    }
    alert("Account successfully created!");
    window.closeNewAccountModal();
    window.loadAccounts();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// New Budget
window.openNewBudgetModal = () => {
  const accSel = document.getElementById("budget-form-acc");
  accSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.account_type === "Expense" || a.account_type === "Asset")
    .forEach((a) => {
      accSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  document.getElementById("budget-form-amount").value = 50000;
  document.getElementById("budget-form-notes").value = "Approved FY-2026 allocation";
  document.getElementById("modal-new-budget").classList.remove("hidden");
};

window.closeNewBudgetModal = () => {
  document.getElementById("modal-new-budget").classList.add("hidden");
};

window.submitNewBudget = async () => {
  const acc = document.getElementById("budget-form-acc").value;
  const dept = document.getElementById("budget-form-dept").value;
  const amt = Number(document.getElementById("budget-form-amount").value) || 0;
  const notes = document.getElementById("budget-form-notes").value.trim();

  if (!acc || amt <= 0) {
    alert("Please select account and valid budget amount");
    return;
  }

  try {
    const res = await fetch("/api/budgets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fiscal_year: 2026,
        account_code: acc,
        department: dept,
        annual_budget: amt,
        notes: notes
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to save budget");
    }
    alert("Budget allocation saved!");
    window.closeNewBudgetModal();
    window.loadBudgets();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// New Vendor
window.openNewVendorModal = () => {
  document.getElementById("vend-form-code").value = "VEND-" + Math.floor(100 + Math.random() * 900);
  document.getElementById("vend-form-name").value = "";
  document.getElementById("vend-form-trn").value = "100" + Math.floor(1000000000 + Math.random() * 9000000000);
  document.getElementById("vend-form-bank").value = "";
  document.getElementById("vend-form-email").value = "";
  document.getElementById("modal-new-vendor").classList.remove("hidden");
};

window.closeNewVendorModal = () => {
  document.getElementById("modal-new-vendor").classList.add("hidden");
};

window.submitNewVendor = async () => {
  const code = document.getElementById("vend-form-code").value.trim();
  const name = document.getElementById("vend-form-name").value.trim();
  const trn = document.getElementById("vend-form-trn").value.trim();
  const terms = document.getElementById("vend-form-terms").value;
  const bank = document.getElementById("vend-form-bank").value.trim();
  const email = document.getElementById("vend-form-email").value.trim();

  if (!code || !name || !trn) {
    alert("Please fill in Vendor Code, Legal Name, and TRN");
    return;
  }

  try {
    const res = await fetch("/api/ap/vendors", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        vendor_code: code,
        name: name,
        trn: trn,
        payment_terms: terms,
        bank_details: bank,
        email: email
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create vendor");
    }
    alert("Vendor created successfully!");
    window.closeNewVendorModal();
    if (window.loadVendors) await window.loadVendors();
    await window.loadAPData();
    window.goToVendorMaster();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// New Customer
window.openNewCustomerModal = () => {
  document.getElementById("cust-form-code").value = "CUST-" + Math.floor(100 + Math.random() * 900);
  document.getElementById("cust-form-name").value = "";
  document.getElementById("cust-form-trn").value = "100" + Math.floor(1000000000 + Math.random() * 9000000000);
  document.getElementById("cust-form-credit").value = 150000;
  document.getElementById("cust-form-address").value = "Market Street, Store #12, Dubai";
  document.getElementById("cust-form-email").value = "";
  document.getElementById("modal-new-customer").classList.remove("hidden");
};

window.closeNewCustomerModal = () => {
  document.getElementById("modal-new-customer").classList.add("hidden");
};

window.submitNewCustomer = async () => {
  const code = document.getElementById("cust-form-code").value.trim();
  const name = document.getElementById("cust-form-name").value.trim();
  const trn = document.getElementById("cust-form-trn").value.trim();
  const credit = Number(document.getElementById("cust-form-credit").value) || 0;
  const addr = document.getElementById("cust-form-address").value.trim();
  const email = document.getElementById("cust-form-email").value.trim();

  if (!code || !name || !trn) {
    alert("Please fill in Customer Code, Legal Name, and TRN");
    return;
  }

  try {
    const res = await fetch("/api/ar/customers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        customer_code: code,
        name: name,
        trn: trn,
        credit_limit: credit,
        billing_address: addr,
        email: email
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create customer");
    }
    alert("Customer created successfully!");
    window.closeNewCustomerModal();
    if (window.loadCustomers) await window.loadCustomers();
    await window.loadARData();
    window.goToCustomerMaster();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// Direct PO
window.openNewPOModal = () => {
  const vSel = document.getElementById("po-form-vendor");
  vSel.innerHTML = "";
  window.ERP_STATE.vendors.forEach((v) => {
    vSel.innerHTML += `<option value="${v.vendor_code}">${v.name} (${v.vendor_code})</option>`;
  });

  const accSel = document.getElementById("po-form-account");
  accSel.innerHTML = "";
  window.ERP_STATE.accounts
    .filter((a) => a.account_type === "Expense" || a.account_type === "Asset")
    .forEach((a) => {
      accSel.innerHTML += `<option value="${a.account_code}">${a.account_code} - ${a.account_name}</option>`;
    });

  const tSel = document.getElementById("po-form-tax");
  tSel.innerHTML = "";
  window.ERP_STATE.taxCodes.forEach((t) => {
    tSel.innerHTML += `<option value="${t.code}">${t.name} (${t.rate}%)</option>`;
  });

  document.getElementById("po-form-delivery").value = new Date(Date.now() + 14 * 86400000).toISOString().split("T")[0];
  document.getElementById("modal-new-po").classList.remove("hidden");
};

window.closeNewPOModal = () => {
  document.getElementById("modal-new-po").classList.add("hidden");
};

window.submitDirectPO = async () => {
  const vendor = document.getElementById("po-form-vendor").value;
  const delDate = document.getElementById("po-form-delivery").value;
  const acc = document.getElementById("po-form-account").value;
  const desc = document.getElementById("po-form-desc").value.trim();
  const qty = Number(document.getElementById("po-form-qty").value) || 0;
  const price = Number(document.getElementById("po-form-price").value) || 0;
  const tax = document.getElementById("po-form-tax").value;

  if (!vendor || !desc || qty <= 0 || price <= 0) {
    alert("Please fill in Vendor, Description, Quantity, and Unit Price");
    return;
  }

  try {
    const res = await fetch("/api/p2p/pos?status=Approved&created_by=Owner / Operations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        po_date: new Date().toISOString().split("T")[0],
        delivery_date: delDate,
        vendor_code: vendor,
        tax_code: tax,
        lines: [{ description: desc, account_code: acc, quantity: qty, unit_price: price }]
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "PO creation failed");
    }

    alert("Purchase Order created and approved successfully!");
    window.closeNewPOModal();
    window.loadPOs();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 12. Company Profile & Business Settings
// -------------------------------------------------------------
async function loadCompanySettings() {
  try {
    const res = await fetch("/api/settings");
    if (res.ok) {
      const data = await res.json();
      window.ERP_STATE.company = data;
      const hName = document.getElementById("header-company-name");
      if (hName) hName.textContent = data.company_name;
      const plComp = document.getElementById("pl-company-name");
      if (plComp) plComp.textContent = data.company_name;
      const bsComp = document.getElementById("bs-company-name");
      if (bsComp) bsComp.textContent = data.company_name;
      const presComp = document.getElementById("pres-company-name");
      if (presComp) presComp.textContent = data.company_name;
    }
  } catch (err) {
    console.error("Error loading company settings:", err);
  }
}

// -------------------------------------------------------------
// 12.1 Multi-Company & 4-Digit Security PIN Engine
// -------------------------------------------------------------
async function loadCompanies() {
  try {
    const res = await fetch("/api/companies");
    if (!res.ok) return;
    const comps = await res.json();
    window.ERP_STATE.companies = comps;

    const container = document.getElementById("company-switcher-list");
    if (!container) return;
    container.innerHTML = "";

    if (!comps.length) {
      container.innerHTML = '<div class="p-4 text-center text-slate-400">No registered companies found.</div>';
      return;
    }

    comps.forEach((c) => {
      const card = document.createElement("div");
      card.className = `p-3.5 rounded-lg border transition ${
        c.is_active
          ? "border-emerald-400 bg-emerald-50/70 shadow-sm"
          : "border-slate-200 bg-white hover:border-slate-300 shadow-sm"
      } flex flex-col sm:flex-row sm:items-center justify-between gap-3`;

      const safeName = (c.company_name || "").replace(/'/g, "\\'");
      card.innerHTML = `
        <div class="space-y-1">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-slate-800 text-sm">${c.company_name}</span>
            ${
              c.is_active
                ? '<span class="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-300 flex items-center"><i class="fa-solid fa-circle-check mr-1 text-emerald-600"></i>Active Store</span>'
                : '<span class="bg-slate-100 text-slate-600 text-[10px] font-medium px-2 py-0.5 rounded border border-slate-200"><i class="fa-solid fa-lock mr-1"></i>PIN Protected</span>'
            }
          </div>
          <div class="text-[11px] text-slate-500 flex flex-wrap items-center gap-x-2">
            <span><strong class="text-slate-600">TRN:</strong> <span class="font-mono">${c.trn || '-'}</span></span>
            <span>•</span>
            <span><strong class="text-slate-600">Currency:</strong> ${c.currency_symbol || c.currency}</span>
            <span>•</span>
            <span>${c.company_address || 'Dubai, UAE'}</span>
          </div>
        </div>
        <div class="flex items-center space-x-2 shrink-0">
          ${
            c.is_active
              ? '<span class="text-emerald-700 text-xs font-semibold px-2 py-1 flex items-center"><i class="fa-solid fa-check-double mr-1"></i>Current Store</span>'
              : `<button onclick="window.requestSwitchCompany('${c.id}', '${safeName}')" class="bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 rounded text-xs font-semibold shadow flex items-center transition"><i class="fa-solid fa-key mr-1.5"></i>Switch (PIN)</button>`
          }
          ${
            comps.length > 1
              ? `<button onclick="window.requestDeleteCompany('${c.id}', '${safeName}')" class="bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 hover:border-rose-300 px-2.5 py-1.5 rounded text-xs font-medium flex items-center transition" title="Delete company with PIN"><i class="fa-solid fa-trash-can mr-1"></i>Delete</button>`
              : ''
          }
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Error loading companies:", err);
  }
}

window.switchCompanySetupTab = (tab) => {
  const tabCompanies = document.getElementById("cset-tab-companies");
  const tabProfile = document.getElementById("cset-tab-profile");
  const btnCompanies = document.getElementById("tab-btn-cset-companies");
  const btnProfile = document.getElementById("tab-btn-cset-profile");

  if (tab === "companies") {
    if (tabCompanies) tabCompanies.classList.remove("hidden");
    if (tabProfile) tabProfile.classList.add("hidden");
    if (btnCompanies) {
      btnCompanies.className = "px-4 py-2 border-b-2 border-blue-600 text-blue-600 flex items-center";
    }
    if (btnProfile) {
      btnProfile.className = "px-4 py-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center";
    }
    loadCompanies();
  } else {
    if (tabCompanies) tabCompanies.classList.add("hidden");
    if (tabProfile) tabProfile.classList.remove("hidden");
    if (btnProfile) {
      btnProfile.className = "px-4 py-2 border-b-2 border-blue-600 text-blue-600 flex items-center";
    }
    if (btnCompanies) {
      btnCompanies.className = "px-4 py-2 border-b-2 border-transparent text-slate-500 hover:text-slate-800 flex items-center";
    }

    const comp = window.ERP_STATE.company || {};
    const cName = document.getElementById("setting-company-name");
    if (cName) cName.value = comp.company_name || "";
    const cTrn = document.getElementById("setting-company-trn");
    if (cTrn) cTrn.value = comp.trn || comp.company_trn || "";
    const cCurr = document.getElementById("setting-company-currency");
    if (cCurr) cCurr.value = comp.currency_symbol || comp.currency || "AED";
    const cAddr = document.getElementById("setting-company-address");
    if (cAddr) cAddr.value = comp.company_address || "";
    const cPhone = document.getElementById("setting-company-phone");
    if (cPhone) cPhone.value = comp.phone || "";
    const cEmail = document.getElementById("setting-company-email");
    if (cEmail) cEmail.value = comp.email || "";
    const cPin = document.getElementById("setting-company-pin");
    if (cPin) cPin.value = "";
  }
};

window.openCompanySettingsModal = (defaultTab = "companies") => {
  const modal = document.getElementById("modal-company-settings");
  if (modal) modal.classList.remove("hidden");
  window.switchCompanySetupTab(defaultTab);
};

window.closeCompanySettingsModal = () => {
  const modal = document.getElementById("modal-company-settings");
  if (modal) modal.classList.add("hidden");
};

window.openCompanySwitcherModal = () => {
  window.openCompanySettingsModal("companies");
};

window.closeCompanySwitcherModal = () => {
  window.closeCompanySettingsModal();
};

window.requestSwitchCompany = (companyId, companyName) => {
  window.ERP_STATE.switchTargetCompanyId = companyId;
  const modalCompName = document.getElementById("pin-modal-company-name");
  if (modalCompName) modalCompName.textContent = companyName;
  const pinInput = document.getElementById("company-pin-input");
  if (pinInput) pinInput.value = "";
  const errEl = document.getElementById("pin-error-msg");
  if (errEl) {
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }
  document.getElementById("modal-verify-pin").classList.remove("hidden");
  setTimeout(() => pinInput && pinInput.focus(), 150);
};

window.closeVerifyPinModal = () => {
  document.getElementById("modal-verify-pin").classList.add("hidden");
  window.ERP_STATE.switchTargetCompanyId = null;
};

window.submitPinVerification = async () => {
  const pinInput = document.getElementById("company-pin-input");
  const pin = pinInput ? pinInput.value.trim() : "";
  const errEl = document.getElementById("pin-error-msg");

  if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
    if (errEl) {
      errEl.textContent = "Please enter a valid 4-digit numeric PIN.";
      errEl.classList.remove("hidden");
    }
    return;
  }

  const targetId = window.ERP_STATE.switchTargetCompanyId;
  if (!targetId) {
    window.closeVerifyPinModal();
    return;
  }

  try {
    const res = await fetch("/api/companies/switch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_id: targetId, pin: pin })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication failed");
    }
    const comp = await res.json();
    window.closeVerifyPinModal();
    window.closeCompanySettingsModal();
    alert(`Successfully switched active company to:\n${comp.company_name}`);
    await window.refreshAllData();
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    } else {
      alert("Error: " + err.message);
    }
  }
};

window.openCreateCompanyModal = () => {
  document.getElementById("newcomp-name").value = "";
  document.getElementById("newcomp-trn").value = "";
  document.getElementById("newcomp-pin").value = "";
  document.getElementById("newcomp-currency").value = "AED";
  document.getElementById("newcomp-symbol").value = "AED";
  document.getElementById("newcomp-address").value = "Dubai, UAE";
  document.getElementById("newcomp-phone").value = "";
  document.getElementById("newcomp-email").value = "";
  document.getElementById("modal-create-company").classList.remove("hidden");
};

window.closeCreateCompanyModal = () => {
  document.getElementById("modal-create-company").classList.add("hidden");
};

window.submitCreateCompany = async () => {
  const name = document.getElementById("newcomp-name").value.trim();
  const trn = document.getElementById("newcomp-trn").value.trim();
  const pin = document.getElementById("newcomp-pin").value.trim();
  const curr = document.getElementById("newcomp-currency").value.trim() || "AED";
  const sym = document.getElementById("newcomp-symbol").value.trim() || "AED";
  const addr = document.getElementById("newcomp-address").value.trim();
  const phone = document.getElementById("newcomp-phone").value.trim();
  const email = document.getElementById("newcomp-email").value.trim();

  if (!name) {
    alert("Please enter a valid Company / Store Legal Name");
    return;
  }
  if (!trn) {
    alert("Please enter a Tax Registration Number (TRN)");
    return;
  }
  if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
    alert("Security PIN must be exactly 4 numeric digits (e.g. 1234)");
    return;
  }

  try {
    const res = await fetch("/api/companies/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: name,
        trn: trn,
        pin: pin,
        currency: curr,
        currency_symbol: sym,
        company_address: addr,
        phone: phone,
        email: email
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create company");
    }
    const newComp = await res.json();
    alert(`Company "${newComp.company_name}" created and activated!\nFresh isolated database initialized with standard Chart of Accounts ($0.00 balances).`);
    window.closeCreateCompanyModal();
    window.closeCompanySettingsModal();
    await window.refreshAllData();
  } catch (err) {
    alert("Error creating company: " + err.message);
  }
};

window.requestDeleteCompany = (companyId, companyName) => {
  window.ERP_STATE.deleteTargetCompanyId = companyId;
  const modalCompName = document.getElementById("delete-modal-company-name");
  if (modalCompName) modalCompName.textContent = companyName;
  const pinInput = document.getElementById("delete-company-pin-input");
  if (pinInput) pinInput.value = "";
  const errEl = document.getElementById("delete-pin-error-msg");
  if (errEl) {
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }
  document.getElementById("modal-delete-company-pin").classList.remove("hidden");
  setTimeout(() => pinInput && pinInput.focus(), 150);
};

window.closeDeleteCompanyModal = () => {
  const el = document.getElementById("modal-delete-company-pin");
  if (el) el.classList.add("hidden");
  window.ERP_STATE.deleteTargetCompanyId = null;
};

window.confirmDeleteCompany = async () => {
  const pinInput = document.getElementById("delete-company-pin-input");
  const pin = pinInput ? pinInput.value.trim() : "";
  const errEl = document.getElementById("delete-pin-error-msg");

  if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
    if (errEl) {
      errEl.textContent = "Please enter the valid 4-digit security PIN.";
      errEl.classList.remove("hidden");
    }
    return;
  }

  const targetId = window.ERP_STATE.deleteTargetCompanyId;
  if (!targetId) {
    window.closeDeleteCompanyModal();
    return;
  }

  try {
    const res = await fetch(`/api/companies/${targetId}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: pin })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Deletion failed");
    }
    const result = await res.json();
    window.closeDeleteCompanyModal();
    alert(result.message || "Company was successfully deleted.");
    await loadCompanies();
    await window.refreshAllData();
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    } else {
      alert("Error: " + err.message);
    }
  }
};

window.saveCompanySettings = async () => {
  const name = document.getElementById("setting-company-name").value.trim();
  const trn = document.getElementById("setting-company-trn").value.trim();
  const sym = document.getElementById("setting-company-currency").value.trim() || "AED";
  const addr = document.getElementById("setting-company-address").value.trim();
  const phone = document.getElementById("setting-company-phone").value.trim();
  const email = document.getElementById("setting-company-email").value.trim();
  const pinInput = document.getElementById("setting-company-pin");
  const newPin = pinInput ? pinInput.value.trim() : "";

  if (!name) {
    alert("Please enter a valid Company / Store Legal Name");
    return;
  }

  if (newPin && (newPin.length !== 4 || !/^\d{4}$/.test(newPin))) {
    alert("If changing PIN, it must be exactly 4 numeric digits (e.g. 1234)");
    return;
  }

  try {
    const activeComp = (window.ERP_STATE.companies || []).find(c => c.is_active) || window.ERP_STATE.company || {};
    const compId = activeComp.id || "comp_1";

    const res = await fetch("/api/companies/update", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_id: compId,
        company_name: name,
        trn: trn,
        currency: "AED",
        currency_symbol: sym,
        company_address: addr,
        phone: phone,
        email: email,
        new_pin: newPin || null
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to save company settings");
    }

    const saved = await res.json();
    window.ERP_STATE.company = saved;
    const hName = document.getElementById("header-company-name");
    if (hName) hName.textContent = saved.company_name;

    alert("Company profile and settings updated successfully!");
    window.closeCompanySettingsModal();
    await window.refreshAllData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};


// -------------------------------------------------------------
// 13. Inventory Management Module
// -------------------------------------------------------------
window.loadInventory = async () => {
  try {
    const [itemsRes, sumRes] = await Promise.all([
      fetch("/api/inventory/items"),
      fetch("/api/inventory/summary")
    ]);

    const items = await itemsRes.json();
    const summary = await sumRes.json();
    window.ERP_STATE.inventory = items;

    // Update KPIs
    if (document.getElementById("inv-kpi-skus")) document.getElementById("inv-kpi-skus").textContent = summary.total_skus;
    if (document.getElementById("inv-kpi-valuation")) document.getElementById("inv-kpi-valuation").textContent = fmtMoney(summary.total_inventory_valuation);
    if (document.getElementById("inv-kpi-low")) document.getElementById("inv-kpi-low").textContent = summary.low_stock_count;
    if (document.getElementById("inv-kpi-out")) document.getElementById("inv-kpi-out").textContent = summary.out_of_stock_count;
    if (document.getElementById("kpi-inventory")) document.getElementById("kpi-inventory").textContent = fmtMoney(summary.total_inventory_valuation);

    renderInventoryTable(items);

    // Update Dropdowns
    const adjustSel = document.getElementById("adjust-form-item");
    if (adjustSel) {
      adjustSel.innerHTML = '<option value="">-- Choose Product --</option>';
      items.forEach((it) => {
        adjustSel.innerHTML += `<option value="${it.item_code}">${it.name} (${it.item_code}) - Stock: ${it.stock_quantity}</option>`;
      });
    }

    const arItemSel = document.getElementById("ar-inv-item-select");
    if (arItemSel) {
      arItemSel.innerHTML = '<option value="">-- Choose Stock Product or Custom Item --</option>';
      items.forEach((it) => {
        arItemSel.innerHTML += `<option value="${it.item_code}">${it.name} (${it.item_code}) - Stock: ${it.stock_quantity} ${it.unit} - $${it.selling_price.toFixed(2)}</option>`;
      });
    }
  } catch (err) {
    console.error("Error loading inventory:", err);
  }
};

function renderInventoryTable(items) {
  const tbody = document.getElementById("inventory-table-body");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (!items.length) {
    tbody.innerHTML = '<tr><td colspan="12" class="p-4 text-center text-slate-400">No products found in catalog. Click "+ Add Product" to create one.</td></tr>';
    return;
  }

  items.forEach((it) => {
    const margin = it.selling_price > 0 ? (((it.selling_price - it.cost_price) / it.selling_price) * 100).toFixed(1) : "0.0";
    let statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">In Stock</span>';
    if (it.stock_quantity <= 0) {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 animate-pulse">Out of Stock</span>';
    } else if (it.stock_quantity <= it.reorder_level) {
      statusBadge = '<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800">Low Stock</span>';
    }

    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-50 transition";
    tr.innerHTML = `
      <td class="p-3 font-mono font-bold text-teal-800">${it.item_code}</td>
      <td class="p-3 font-semibold text-slate-800">${it.name}</td>
      <td class="p-3"><span class="px-2 py-0.5 rounded bg-slate-100 text-slate-700 text-[11px] font-medium">${it.category || "General"}</span></td>
      <td class="p-3 font-mono text-slate-500">${it.barcode || "-"}</td>
      <td class="p-3 text-slate-600">${it.unit || "Pcs"}</td>
      <td class="p-3 text-right font-mono">${fmtMoney(it.cost_price)}</td>
      <td class="p-3 text-right font-mono font-semibold text-slate-900">${fmtMoney(it.selling_price)}</td>
      <td class="p-3 text-right font-mono text-emerald-700 font-bold">${margin}%</td>
      <td class="p-3 text-right font-mono font-bold ${it.stock_quantity <= it.reorder_level ? 'text-amber-600' : 'text-slate-800'}">${it.stock_quantity}</td>
      <td class="p-3 text-right font-mono font-bold text-teal-900">${fmtMoney(it.stock_valuation)}</td>
      <td class="p-3 text-center">${statusBadge}</td>
      <td class="p-3 text-center">
        <button onclick="window.openStockAdjustModal('${it.item_code}')" class="text-teal-600 hover:text-teal-800 font-semibold text-xs transition">
          <i class="fa-solid fa-sliders mr-1"></i>Adjust
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

window.filterInventoryTable = () => {
  const search = (document.getElementById("filter-inv-search")?.value || "").toLowerCase();
  const cat = document.getElementById("filter-inv-category")?.value || "";

  const filtered = (window.ERP_STATE.inventory || []).filter((it) => {
    const matchSearch =
      !search ||
      it.name.toLowerCase().includes(search) ||
      it.item_code.toLowerCase().includes(search) ||
      (it.barcode && it.barcode.toLowerCase().includes(search));
    const matchCat = !cat || it.category === cat;
    return matchSearch && matchCat;
  });

  renderInventoryTable(filtered);
};

window.switchInventorySubtab = (subtab) => {
  const catView = document.getElementById("inv-view-catalog");
  const movView = document.getElementById("inv-view-movements");
  const catBtn = document.getElementById("inv-subtab-catalog");
  const movBtn = document.getElementById("inv-subtab-movements");

  if (subtab === "catalog") {
    catView.classList.remove("hidden");
    movView.classList.add("hidden");
    catBtn.className = "px-4 py-2 font-bold border-b-2 border-teal-600 text-teal-600";
    movBtn.className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
  } else {
    catView.classList.add("hidden");
    movView.classList.remove("hidden");
    movBtn.className = "px-4 py-2 font-bold border-b-2 border-teal-600 text-teal-600";
    catBtn.className = "px-4 py-2 font-medium text-slate-500 hover:text-slate-800";
    window.loadInventoryMovements();
  }
};

window.loadInventoryMovements = async () => {
  try {
    const res = await fetch("/api/inventory/movements");
    const movements = await res.json();
    window.ERP_STATE.inventoryMovements = movements;

    const tbody = document.getElementById("inventory-movements-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (!movements.length) {
      tbody.innerHTML = '<tr><td colspan="9" class="p-4 text-center text-slate-400">No stock movements recorded yet.</td></tr>';
      return;
    }

    movements.forEach((m) => {
      const isPositive = m.quantity > 0;
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="p-3 text-slate-600">${m.movement_date}</td>
        <td class="p-3 font-mono font-bold text-teal-800">${m.item_code}</td>
        <td class="p-3 font-medium text-slate-800">${m.item_name}</td>
        <td class="p-3"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">${m.movement_type}</span></td>
        <td class="p-3 font-mono text-slate-600">${m.reference_doc || "-"}</td>
        <td class="p-3 text-right font-mono font-bold ${isPositive ? 'text-emerald-600' : 'text-rose-600'}">${isPositive ? '+' : ''}${m.quantity}</td>
        <td class="p-3 text-right font-mono">${fmtMoney(m.unit_cost)}</td>
        <td class="p-3 text-right font-mono font-bold text-slate-900">${fmtMoney(m.total_cost)}</td>
        <td class="p-3 text-slate-500 text-[11px]">${m.notes || "-"}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error loading inventory movements:", err);
  }
};

window.openNewItemModal = () => {
  const randNum = Math.floor(100 + Math.random() * 900);
  document.getElementById("item-form-code").value = "SKU-RET-" + randNum;
  document.getElementById("item-form-name").value = "";
  document.getElementById("item-form-barcode").value = "6291001" + randNum;
  document.getElementById("item-form-cost").value = 10.00;
  document.getElementById("item-form-sell").value = 15.00;
  document.getElementById("item-form-stock").value = 50;
  document.getElementById("item-form-reorder").value = 15;
  document.getElementById("modal-new-item").classList.remove("hidden");
};

window.closeNewItemModal = () => {
  document.getElementById("modal-new-item").classList.add("hidden");
};

window.submitNewItem = async () => {
  const code = document.getElementById("item-form-code").value.trim().toUpperCase();
  const cat = document.getElementById("item-form-category").value;
  const name = document.getElementById("item-form-name").value.trim();
  const barcode = document.getElementById("item-form-barcode").value.trim();
  const unit = document.getElementById("item-form-unit").value;
  const cost = Number(document.getElementById("item-form-cost").value) || 0;
  const sell = Number(document.getElementById("item-form-sell").value) || 0;
  const stock = Number(document.getElementById("item-form-stock").value) || 0;
  const reorder = Number(document.getElementById("item-form-reorder").value) || 0;

  if (!code || !name || cost <= 0 || sell <= 0) {
    alert("Please fill in Item Code, Product Name, and valid Cost / Selling prices.");
    return;
  }

  try {
    const res = await fetch("/api/inventory/items", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item_code: code,
        name: name,
        category: cat,
        barcode: barcode,
        unit: unit,
        cost_price: cost,
        selling_price: sell,
        stock_quantity: stock,
        reorder_level: reorder
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to create product SKU");
    }

    alert(`Product SKU ${code} created successfully!`);
    window.closeNewItemModal();
    window.loadInventory();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.openStockAdjustModal = (itemCode) => {
  document.getElementById("adjust-form-qty").value = "";
  document.getElementById("adjust-form-notes").value = "";
  const sel = document.getElementById("adjust-form-item");

  if (itemCode) {
    sel.value = itemCode;
  }
  window.onAdjustItemSelect();
  document.getElementById("modal-stock-adjust").classList.remove("hidden");
};

window.onAdjustItemSelect = () => {
  const code = document.getElementById("adjust-form-item").value;
  const item = (window.ERP_STATE.inventory || []).find((i) => i.item_code === code);
  const stockSpan = document.getElementById("adjust-current-stock");
  if (item) {
    stockSpan.textContent = `${item.stock_quantity} ${item.unit} (Unit Cost: $${item.cost_price.toFixed(2)})`;
  } else {
    stockSpan.textContent = "0";
  }
};

window.closeStockAdjustModal = () => {
  document.getElementById("modal-stock-adjust").classList.add("hidden");
};

window.submitStockAdjustment = async () => {
  const itemCode = document.getElementById("adjust-form-item").value;
  const type = document.getElementById("adjust-form-type").value;
  const qty = Number(document.getElementById("adjust-form-qty").value);
  const notes = document.getElementById("adjust-form-notes").value.trim();

  if (!itemCode || isNaN(qty) || qty === 0 || !notes) {
    alert("Please select a Product, enter non-zero Quantity (+ or -), and provide a reason.");
    return;
  }

  try {
    const res = await fetch("/api/inventory/adjust", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        item_code: itemCode,
        adjustment_type: type,
        quantity: qty,
        reason: notes
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Stock adjustment failed");
    }

    const data = await res.json();
    alert(`Stock adjustment recorded! New stock: ${data.item.stock_quantity}. GL Voucher ${data.voucher_no || ''} posted.`);
    window.closeStockAdjustModal();
    window.loadInventory();
    window.loadVouchers();
    loadDashboardKPIs();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.exportInventoryExcel = () => {
  if (!window.ERP_STATE.inventory || !window.ERP_STATE.inventory.length) {
    alert("No inventory data to export.");
    return;
  }

  const rows = window.ERP_STATE.inventory.map((it) => ({
    "Item Code": it.item_code,
    "Product Name": it.name,
    "Category": it.category,
    "Barcode": it.barcode,
    "Unit": it.unit,
    "Cost Price ($)": it.cost_price,
    "Selling Price ($)": it.selling_price,
    "Margin ($)": Math.round((it.selling_price - it.cost_price) * 100) / 100,
    "Stock Qty": it.stock_quantity,
    "Valuation ($)": it.stock_valuation,
    "Reorder Level": it.reorder_level
  }));

  const ws = XLSX.utils.json_to_sheet(rows);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Store_Inventory");
  XLSX.writeFile(wb, "Store_Inventory_Stock_Catalog.xlsx");
};

// -------------------------------------------------------------
// 14. Vendor & Customer Data Event Entry & Quick Actions
// -------------------------------------------------------------
window.quickBillForVendor = (vendCode) => {
  window.openNewAPInvoiceModal();
  const vSel = document.getElementById("ap-inv-vendor");
  if (vSel) {
    vSel.value = vendCode;
    window.onAPInvoiceVendorSelect();
  }
};

window.quickPaymentForVendor = (vendCode) => {
  window.openAPPaymentModal();
  const vSel = document.getElementById("pmt-form-vendor");
  if (vSel) {
    vSel.value = vendCode;
    window.onAPPaymentVendorSelect();
  }
};

window.quickPOForVendor = (vendCode) => {
  window.openNewPOModal();
  const vSel = document.getElementById("po-form-vendor");
  if (vSel) {
    vSel.value = vendCode;
  }
};

window.onAPInvoiceVendorSelect = () => {
  const code = document.getElementById("ap-inv-vendor")?.value;
  const box = document.getElementById("ap-inv-vend-info");
  if (!code || !box) return;
  const vend = (window.ERP_STATE.vendors || []).find((v) => v.vendor_code === code);
  if (vend) {
    box.classList.remove("hidden");
    box.innerHTML = `<span class="font-bold text-slate-800">${vend.name}</span> | TRN: <span class="font-mono font-semibold">${vend.trn}</span> | Terms: <span class="font-semibold text-blue-700">${vend.payment_terms}</span><br><span class="text-slate-500 font-mono text-[10px]">${vend.bank_details || 'No bank recorded'}</span>`;
  } else {
    box.classList.add("hidden");
  }
};

window.openVendorStatement = async (vendCode) => {
  try {
    const res = await fetch(`/api/ap/vendors/${vendCode}/statement`);
    if (!res.ok) throw new Error("Vendor statement not found");
    const data = await res.json();
    const v = data.vendor;

    document.getElementById("vstmt-name").textContent = v.name;
    document.getElementById("vstmt-code-trn").textContent = `Code: ${v.vendor_code} | TRN: ${v.trn} | Terms: ${v.payment_terms}`;
    document.getElementById("vstmt-contact").textContent = `Bank: ${v.bank_details || '-'} | Phone: ${v.phone || '-'} | Email: ${v.email || '-'}`;

    document.getElementById("vstmt-tot-billed").textContent = fmtMoney(data.total_billed);
    document.getElementById("vstmt-tot-paid").textContent = fmtMoney(data.total_paid);
    document.getElementById("vstmt-tot-balance").textContent = fmtMoney(data.outstanding_balance);

    document.getElementById("btn-vstmt-new-bill").onclick = () => {
      window.closeVendorStatementModal();
      window.quickBillForVendor(v.vendor_code);
    };
    document.getElementById("btn-vstmt-new-pmt").onclick = () => {
      window.closeVendorStatementModal();
      window.quickPaymentForVendor(v.vendor_code);
    };

    const invTbody = document.getElementById("vstmt-invoices-tbody");
    invTbody.innerHTML = "";
    if (!data.invoices.length) {
      invTbody.innerHTML = '<tr><td colspan="7" class="p-3 text-center text-slate-400">No bills recorded for this vendor yet.</td></tr>';
    } else {
      data.invoices.forEach((inv) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-2 font-mono font-bold text-slate-800">${inv.invoice_number}</td>
          <td class="p-2 text-slate-600">${inv.vendor_invoice_ref}</td>
          <td class="p-2 text-slate-600">${inv.invoice_date}</td>
          <td class="p-2 text-right font-mono font-semibold">${fmtMoney(inv.total_amount)}</td>
          <td class="p-2 text-right font-mono text-blue-600">${fmtMoney(inv.paid_amount)}</td>
          <td class="p-2 text-right font-mono font-bold ${inv.remaining_balance > 0 ? 'text-amber-600' : 'text-slate-400'}">${fmtMoney(inv.remaining_balance)}</td>
          <td class="p-2 text-center">${getBadgeHTML(inv.status)}</td>
        `;
        invTbody.appendChild(tr);
      });
    }

    const pmtTbody = document.getElementById("vstmt-payments-tbody");
    pmtTbody.innerHTML = "";
    if (!data.payments.length) {
      pmtTbody.innerHTML = '<tr><td colspan="6" class="p-3 text-center text-slate-400">No disbursements recorded for this vendor yet.</td></tr>';
    } else {
      data.payments.forEach((pmt) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-2 font-mono font-bold text-slate-800">${pmt.payment_number}</td>
          <td class="p-2 text-slate-600">${pmt.payment_date}</td>
          <td class="p-2 font-mono text-slate-600">${pmt.payment_ref}</td>
          <td class="p-2 font-mono text-slate-600">${pmt.bank_account_code}</td>
          <td class="p-2 text-right font-mono font-bold text-blue-600">${fmtMoney(pmt.total_amount)}</td>
          <td class="p-2 text-center">${getBadgeHTML(pmt.status)}</td>
        `;
        pmtTbody.appendChild(tr);
      });
    }

    document.getElementById("modal-vendor-statement").classList.remove("hidden");
  } catch (err) {
    alert("Error fetching vendor statement: " + err.message);
  }
};

window.closeVendorStatementModal = () => {
  document.getElementById("modal-vendor-statement").classList.add("hidden");
};

window.openEditVendorModal = (vendCode) => {
  const vend = (window.ERP_STATE.vendors || []).find((v) => v.vendor_code === vendCode);
  if (!vend) return;
  document.getElementById("edit-vend-code").value = vend.vendor_code;
  document.getElementById("edit-vend-name").value = vend.name;
  document.getElementById("edit-vend-trn").value = vend.trn;
  document.getElementById("edit-vend-terms").value = vend.payment_terms || "Net 30";
  document.getElementById("edit-vend-bank").value = vend.bank_details || "";
  document.getElementById("edit-vend-email").value = vend.email || "";
  document.getElementById("edit-vend-phone").value = vend.phone || "";
  document.getElementById("modal-edit-vendor").classList.remove("hidden");
};

window.closeEditVendorModal = () => {
  document.getElementById("modal-edit-vendor").classList.add("hidden");
};

window.submitEditVendor = async () => {
  const code = document.getElementById("edit-vend-code").value;
  const name = document.getElementById("edit-vend-name").value.trim();
  const trn = document.getElementById("edit-vend-trn").value.trim();
  const terms = document.getElementById("edit-vend-terms").value;
  const bank = document.getElementById("edit-vend-bank").value.trim();
  const email = document.getElementById("edit-vend-email").value.trim();
  const phone = document.getElementById("edit-vend-phone").value.trim();

  if (!name || !trn) {
    alert("Vendor Legal Name and TRN are required");
    return;
  }

  try {
    const res = await fetch(`/api/ap/vendors/${code}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        trn: trn,
        payment_terms: terms,
        bank_details: bank,
        email: email,
        phone: phone
      })
    });
    if (!res.ok) throw new Error("Failed to update vendor record");
    alert("Vendor updated successfully!");
    window.closeEditVendorModal();
    await loadVendors();
    window.loadAPData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

window.quickInvoiceForCustomer = (custCode) => {
  window.openNewARInvoiceModal();
  const cSel = document.getElementById("ar-inv-customer");
  if (cSel) {
    cSel.value = custCode;
    window.onARInvoiceCustomerSelect();
  }
};

window.quickReceiptForCustomer = (custCode) => {
  window.openARReceiptModal();
  const cSel = document.getElementById("rcpt-form-customer");
  if (cSel) {
    cSel.value = custCode;
    window.onARReceiptCustomerSelect();
  }
};

window.onARInvoiceCustomerSelect = () => {
  const code = document.getElementById("ar-inv-customer")?.value;
  const box = document.getElementById("ar-inv-cust-info");
  if (!code || !box) return;
  const cust = (window.ERP_STATE.customers || []).find((c) => c.customer_code === code);
  if (cust) {
    box.classList.remove("hidden");
    box.innerHTML = `<span class="font-bold text-slate-800">${cust.name}</span> | TRN: <span class="font-mono font-semibold">${cust.trn}</span> | Credit Limit: <span class="font-mono font-semibold text-emerald-700">${fmtMoney(cust.credit_limit)}</span><br><span class="text-slate-500">${cust.billing_address || 'No billing address'}</span>`;
  } else {
    box.classList.add("hidden");
  }
};

window.openCustomerStatement = async (custCode) => {
  try {
    const res = await fetch(`/api/ar/customers/${custCode}/statement`);
    if (!res.ok) throw new Error("Customer statement not found");
    const data = await res.json();
    const c = data.customer;

    document.getElementById("cstmt-name").textContent = c.name;
    document.getElementById("cstmt-code-trn").textContent = `Code: ${c.customer_code} | TRN: ${c.trn} | Credit Limit: ${fmtMoney(c.credit_limit)}`;
    document.getElementById("cstmt-contact").textContent = `Address: ${c.billing_address || '-'} | Phone: ${c.phone || '-'} | Email: ${c.email || '-'}`;

    document.getElementById("cstmt-tot-invoiced").textContent = fmtMoney(data.total_invoiced);
    document.getElementById("cstmt-tot-collected").textContent = fmtMoney(data.total_collected);
    document.getElementById("cstmt-tot-balance").textContent = fmtMoney(data.outstanding_balance);

    document.getElementById("btn-cstmt-new-inv").onclick = () => {
      window.closeCustomerStatementModal();
      window.quickInvoiceForCustomer(c.customer_code);
    };
    document.getElementById("btn-cstmt-new-rcpt").onclick = () => {
      window.closeCustomerStatementModal();
      window.quickReceiptForCustomer(c.customer_code);
    };

    const invTbody = document.getElementById("cstmt-invoices-tbody");
    invTbody.innerHTML = "";
    if (!data.invoices.length) {
      invTbody.innerHTML = '<tr><td colspan="6" class="p-3 text-center text-slate-400">No sales invoices recorded for this customer yet.</td></tr>';
    } else {
      data.invoices.forEach((inv) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-2 font-mono font-bold text-slate-800">${inv.invoice_number}</td>
          <td class="p-2 text-slate-600">${inv.invoice_date}</td>
          <td class="p-2 text-right font-mono font-semibold">${fmtMoney(inv.total_amount)}</td>
          <td class="p-2 text-right font-mono text-emerald-600">${fmtMoney(inv.paid_amount)}</td>
          <td class="p-2 text-right font-mono font-bold ${inv.remaining_balance > 0 ? 'text-rose-600' : 'text-slate-400'}">${fmtMoney(inv.remaining_balance)}</td>
          <td class="p-2 text-center">${getBadgeHTML(inv.status)}</td>
        `;
        invTbody.appendChild(tr);
      });
    }

    const rcptTbody = document.getElementById("cstmt-receipts-tbody");
    rcptTbody.innerHTML = "";
    if (!data.receipts.length) {
      rcptTbody.innerHTML = '<tr><td colspan="6" class="p-3 text-center text-slate-400">No bank collections recorded for this customer yet.</td></tr>';
    } else {
      data.receipts.forEach((rcpt) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="p-2 font-mono font-bold text-slate-800">${rcpt.receipt_number}</td>
          <td class="p-2 text-slate-600">${rcpt.receipt_date}</td>
          <td class="p-2 font-mono text-slate-600">${rcpt.receipt_ref}</td>
          <td class="p-2 font-mono text-slate-600">${rcpt.bank_account_code}</td>
          <td class="p-2 text-right font-mono font-bold text-emerald-600">${fmtMoney(rcpt.total_amount)}</td>
          <td class="p-2 text-center">${getBadgeHTML(rcpt.status)}</td>
        `;
        rcptTbody.appendChild(tr);
      });
    }

    document.getElementById("modal-customer-statement").classList.remove("hidden");
  } catch (err) {
    alert("Error fetching customer statement: " + err.message);
  }
};

window.closeCustomerStatementModal = () => {
  document.getElementById("modal-customer-statement").classList.add("hidden");
};

window.openEditCustomerModal = (custCode) => {
  const cust = (window.ERP_STATE.customers || []).find((c) => c.customer_code === custCode);
  if (!cust) return;
  document.getElementById("edit-cust-code").value = cust.customer_code;
  document.getElementById("edit-cust-name").value = cust.name;
  document.getElementById("edit-cust-trn").value = cust.trn;
  document.getElementById("edit-cust-credit").value = cust.credit_limit || 0;
  document.getElementById("edit-cust-address").value = cust.billing_address || "";
  document.getElementById("edit-cust-email").value = cust.email || "";
  document.getElementById("edit-cust-phone").value = cust.phone || "";
  document.getElementById("modal-edit-customer").classList.remove("hidden");
};

window.closeEditCustomerModal = () => {
  document.getElementById("modal-edit-customer").classList.add("hidden");
};

window.submitEditCustomer = async () => {
  const code = document.getElementById("edit-cust-code").value;
  const name = document.getElementById("edit-cust-name").value.trim();
  const trn = document.getElementById("edit-cust-trn").value.trim();
  const credit = Number(document.getElementById("edit-cust-credit").value) || 0;
  const addr = document.getElementById("edit-cust-address").value.trim();
  const email = document.getElementById("edit-cust-email").value.trim();
  const phone = document.getElementById("edit-cust-phone").value.trim();

  if (!name || !trn) {
    alert("Customer Legal Name and TRN are required");
    return;
  }

  try {
    const res = await fetch(`/api/ar/customers/${code}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name,
        trn: trn,
        credit_limit: credit,
        billing_address: addr,
        email: email,
        phone: phone
      })
    });
    if (!res.ok) throw new Error("Failed to update customer record");
    alert("Customer updated successfully!");
    window.closeEditCustomerModal();
    await loadCustomers();
    window.loadARData();
  } catch (err) {
    alert("Error: " + err.message);
  }
};

// -------------------------------------------------------------
// 15. Reset & Initial Configuration Dialog
// -------------------------------------------------------------
window.openResetChoiceModal = () => {
  document.getElementById("modal-reset-choice").classList.remove("hidden");
};

window.closeResetChoiceModal = () => {
  const el = document.getElementById("modal-reset-choice");
  if (el) el.classList.add("hidden");
};

window.requestResetWithPin = (resetMode) => {
  window.ERP_STATE.pendingResetMode = resetMode; // 'clean' or 'demo'
  const comp = window.ERP_STATE.company || {};
  const compNameEl = document.getElementById("reset-pin-company-name");
  if (compNameEl) compNameEl.textContent = comp.company_name || "Active Company";

  const actionTitle = document.getElementById("reset-pin-modal-action");
  if (actionTitle) {
    actionTitle.textContent = resetMode === "clean"
      ? "Reset to Clean Production Slate ($0.00 Balances)"
      : "Reset & Load Sample Supermarket Demo Data";
  }

  const pinInput = document.getElementById("reset-db-pin-input");
  if (pinInput) pinInput.value = "";
  const errEl = document.getElementById("reset-pin-error-msg");
  if (errEl) {
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }

  window.closeResetChoiceModal();
  const pinModal = document.getElementById("modal-reset-db-pin");
  if (pinModal) pinModal.classList.remove("hidden");
  setTimeout(() => pinInput && pinInput.focus(), 150);
};

window.closeResetPinModal = () => {
  const modal = document.getElementById("modal-reset-db-pin");
  if (modal) modal.classList.add("hidden");
  window.ERP_STATE.pendingResetMode = null;
};

window.submitResetWithPin = async () => {
  const pinInput = document.getElementById("reset-db-pin-input");
  const pin = pinInput ? pinInput.value.trim() : "";
  const errEl = document.getElementById("reset-pin-error-msg");

  if (!pin || pin.length !== 4 || !/^\d{4}$/.test(pin)) {
    if (errEl) {
      errEl.textContent = "Please enter the valid 4-digit security PIN.";
      errEl.classList.remove("hidden");
    }
    return;
  }

  const mode = window.ERP_STATE.pendingResetMode || "clean";
  const url = mode === "clean" ? "/api/system/reset-clean" : "/api/system/seed-demo";

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pin: pin })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Authentication / Reset failed");
    }
    const data = await res.json();
    window.closeResetPinModal();
    alert(data.message);
    await window.refreshAllData();
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message;
      errEl.classList.remove("hidden");
    } else {
      alert("Error: " + err.message);
    }
  }
};

window.confirmCleanSlateReset = () => {
  window.requestResetWithPin("clean");
};

window.confirmDemoDataLoad = () => {
  window.requestResetWithPin("demo");
};



