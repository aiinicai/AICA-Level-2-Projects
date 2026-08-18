interface ClientItem {
  id: number;
  name: string;
  trade_name: string;
  gstin: string;
  status: string;
  constitution: string;
  address: string;
  registration_date: string;
  created_at: string;
}

interface GSTRecordItem {
  id: number;
  client_id: number;
  return_type: string;
  financial_year: string;
  period: string;
  turnover: number;
  tax_liability: number;
  due_date: string;
  actual_filing_date: string;
  is_edited: boolean;
  created_at: string;
  // GSTR-1 Breakdown
  b2b_supplies: number;
  b2c_large: number;
  b2c_small: number;
  exports: number;
  nil_exempt: number;
  cr_dr_notes: number;
  total_tax_liability: number;
  // GSTR-3B Breakdown
  outward_taxable_3_1_a: number;
  inward_rcm_3_1_d: number;
  zero_rated_3_1_b: number;
  nil_exempt_3_1_c: number;
  itc_available_4_a: number;
  itc_reversed_4_b: number;
  net_itc_4_c: number;
}

interface ComparisonItem {
  period: string;
  gstr1_turnover: number;
  gstr3b_turnover: number;
  turnover_diff: number;
  gstr1_liability: number;
  gstr3b_liability: number;
  liability_diff: number;
  has_gstr1: boolean;
  has_gstr3b: boolean;
  status: string;
}

interface FilingComplianceItem {
  id: number;
  period: string;
  return_type: string;
  due_date: string;
  actual_filing_date: string;
  status: string;
  days_delayed: number;
  is_edited: boolean;
}

interface LedgerItem {
  id: number;
  client_id: number;
  financial_year: string;
  ledger_type: string;
  date: string;
  description: string;
  amount: number;
  created_at: string;
}

document.addEventListener('DOMContentLoaded', () => {
  // Theme sync listener from parent frame/window
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'THEME_CHANGE') {
      document.documentElement.setAttribute('data-theme', event.data.theme);
    }
  });

  // Extract client_id from URL query string
  const urlParams = new URLSearchParams(window.location.search);
  const clientIdStr = urlParams.get('client_id');
  if (!clientIdStr) {
    alert('No client_id specified in URL parameters.');
    return;
  }
  const clientId = parseInt(clientIdStr, 10);

  // State
  let currentClient: ClientItem | null = null;
  let selectedFy = '2024-25';

  // DOM Elements
  const selectFy = document.getElementById('select-fy') as HTMLSelectElement;
  const activeClientName = document.getElementById('active-client-name') as HTMLElement;
  const activeClientTradeName = document.getElementById('active-client-trade-name') as HTMLElement;
  const activeClientGstin = document.getElementById('active-client-gstin') as HTMLElement;
  const activeClientStatus = document.getElementById('active-client-status') as HTMLElement;
  const btnRefreshWorkspace = document.getElementById('btn-refresh-workspace') as HTMLButtonElement;

  // Master Data Form Elements
  const formMasterData = document.getElementById('form-master-data') as HTMLFormElement;
  const inputMasterLegalName = document.getElementById('input-master-legal-name') as HTMLInputElement;
  const inputMasterTradeName = document.getElementById('input-master-trade-name') as HTMLInputElement;
  const inputMasterGstin = document.getElementById('input-master-gstin') as HTMLInputElement;
  const selectMasterStatus = document.getElementById('select-master-status') as HTMLSelectElement;
  const inputMasterConstitution = document.getElementById('input-master-constitution') as HTMLInputElement;
  const inputMasterRegDate = document.getElementById('input-master-reg-date') as HTMLInputElement;
  const inputMasterAddress = document.getElementById('input-master-address') as HTMLTextAreaElement;
  const statusMasterSave = document.getElementById('status-master-save') as HTMLElement;
  const badgeMasterStatus = document.getElementById('badge-master-status') as HTMLElement;

  // Option A & B
  const fileReg06 = document.getElementById('file-reg06') as HTMLInputElement;
  const statusReg06 = document.getElementById('status-reg06') as HTMLElement;
  const btnFetchGstinPortal = document.getElementById('btn-fetch-gstin-portal') as HTMLButtonElement;
  const statusGspFetch = document.getElementById('status-gsp-fetch') as HTMLElement;

  // Tabs Navigation
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      tabBtns.forEach((b) => b.classList.remove('active'));
      tabPanes.forEach((p) => p.classList.remove('active'));

      btn.classList.add('active');
      if (targetTab) {
        document.getElementById(targetTab)?.classList.add('active');
      }
    });
  });

  // FY Dropdown Change -> Refresh Data
  if (selectFy) {
    selectedFy = selectFy.value;
    selectFy.addEventListener('change', () => {
      selectedFy = selectFy.value;
      loadWorkspaceData();
    });
  }

  if (btnRefreshWorkspace) {
    btnRefreshWorkspace.addEventListener('click', loadWorkspaceData);
  }

  // --- API LOADERS ---
  async function loadClientProfile() {
    try {
      const res = await fetch(`/api/gst_tool/clients/${clientId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      currentClient = data.client;
      renderClientHeader();
      renderMasterDataForm();
    } catch (err) {
      console.error('Failed to load client profile:', err);
    }
  }

  function renderClientHeader() {
    if (!currentClient) return;
    if (activeClientName) activeClientName.textContent = currentClient.name;
    if (activeClientTradeName) activeClientTradeName.textContent = currentClient.trade_name || currentClient.name;
    if (activeClientGstin) activeClientGstin.textContent = currentClient.gstin;
    if (activeClientStatus) {
      activeClientStatus.textContent = currentClient.status;
      activeClientStatus.className = currentClient.status === 'Active' ? 'badge badge-success' : 'badge badge-danger';
    }
  }

  // OBJECTIVE 3: Render Master Data Form Fields
  function renderMasterDataForm() {
    if (!currentClient) return;
    if (inputMasterLegalName) inputMasterLegalName.value = currentClient.name;
    if (inputMasterTradeName) inputMasterTradeName.value = currentClient.trade_name || currentClient.name;
    if (inputMasterGstin) inputMasterGstin.value = currentClient.gstin;
    if (selectMasterStatus) selectMasterStatus.value = currentClient.status || 'Active';
    if (inputMasterConstitution) inputMasterConstitution.value = currentClient.constitution || '';
    if (inputMasterAddress) inputMasterAddress.value = currentClient.address || '';
    if (inputMasterRegDate) inputMasterRegDate.value = currentClient.registration_date || '';
    if (badgeMasterStatus) {
      badgeMasterStatus.textContent = currentClient.status;
      badgeMasterStatus.className = currentClient.status === 'Active' ? 'badge badge-success' : 'badge badge-danger';
    }
  }

  // OBJECTIVE 3: Master Data Form Submission
  if (formMasterData) {
    formMasterData.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!currentClient) return;

      const name = inputMasterLegalName.value.trim();
      const tradeName = inputMasterTradeName.value.trim();
      const status = selectMasterStatus.value;
      const constitution = inputMasterConstitution.value.trim();
      const address = inputMasterAddress.value.trim();
      const regDate = inputMasterRegDate.value.trim();

      if (statusMasterSave) statusMasterSave.innerHTML = `<span style="color:var(--primary-accent);">Saving changes...</span>`;

      try {
        const res = await fetch(`/api/gst_tool/clients/${clientId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name,
            trade_name: tradeName,
            status,
            constitution,
            address,
            registration_date: regDate
          })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (statusMasterSave) statusMasterSave.innerHTML = `<span style="color:var(--success-text); font-weight:600;">Master Data saved successfully!</span>`;
        await loadClientProfile();
      } catch (err) {
        if (statusMasterSave) statusMasterSave.innerHTML = `<span style="color:var(--danger-text); font-weight:600;">Save error: ${(err as Error).message}</span>`;
      }
    });
  }

  async function loadWorkspaceData() {
    await Promise.all([
      loadClientProfile(),
      loadDashboardTab(),
      loadGSTR1Tab(),
      loadGSTR3BTab(),
      loadLedgersTab(),
      loadSettingsTab()
    ]);
  }

  // 1. Dashboard Tab (Comparison & Filing)
  async function loadDashboardTab() {
    try {
      const [resComp, resFiling] = await Promise.all([
        fetch(`/api/gst_tool/dashboard/comparison?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`),
        fetch(`/api/gst_tool/dashboard/filing?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`)
      ]);

      if (resComp.ok) {
        const dataComp = await resComp.json();
        renderComparisonTable(dataComp.comparison || []);
      }

      if (resFiling.ok) {
        const dataFiling = await resFiling.json();
        const widget = document.getElementById('widget-summary-text');
        if (widget && dataFiling.summary) widget.textContent = dataFiling.summary.message;
        renderFilingTable(dataFiling.filing_compliance || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard tab:', err);
    }
  }

  function renderComparisonTable(items: ComparisonItem[]) {
    const tbody = document.getElementById('tbody-comparison');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No comparison data available for ${selectedFy}.</td></tr>`;
      return;
    }

    items.forEach((item) => {
      const tr = document.createElement('tr');
      const tDiffStyle = item.turnover_diff !== 0 ? 'color: var(--danger-text); font-weight:600;' : 'color: var(--success-text);';
      const lDiffStyle = item.liability_diff !== 0 ? 'color: var(--danger-text); font-weight:600;' : 'color: var(--success-text);';
      let badge = `<span class="badge badge-success">Match</span>`;
      if (item.status === 'Mismatch') badge = `<span class="badge badge-danger">Mismatch</span>`;
      else if (item.status === 'Pending Import') badge = `<span class="badge badge-warning">Pending Import</span>`;

      tr.innerHTML = `
        <td><strong>${item.period}</strong></td>
        <td>₹${item.gstr1_turnover.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${item.gstr3b_turnover.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="${tDiffStyle}">₹${item.turnover_diff.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${item.gstr1_liability.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${item.gstr3b_liability.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="${lDiffStyle}">₹${item.liability_diff.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>${badge}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderFilingTable(items: FilingComplianceItem[]) {
    const tbody = document.getElementById('tbody-filing');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No filing records found for ${selectedFy}.</td></tr>`;
      return;
    }

    items.forEach((item) => {
      const tr = document.createElement('tr');
      let badge = `<span class="badge badge-success">On-Time</span>`;
      if (item.status === 'Delayed') {
        tr.classList.add('delayed-row');
        badge = `<span class="badge badge-danger">Delayed (${item.days_delayed} Days)</span>`;
      } else if (item.status === 'Data Not Available') {
        badge = `<span class="badge badge-warning">Pending</span>`;
      }

      tr.innerHTML = `
        <td><strong>${item.period}</strong></td>
        <td><span class="badge" style="background:var(--bg-subtle); color:var(--text-primary);">${item.return_type}</span></td>
        <td>${item.due_date}</td>
        <td>${item.actual_filing_date}</td>
        <td>${item.days_delayed > 0 ? `+${item.days_delayed} days` : '0'}</td>
        <td>${badge}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // 2. GSTR-1 Tab
  async function loadGSTR1Tab() {
    try {
      const res = await fetch(`/api/gst_tool/records?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}&return_type=GSTR-1`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderGSTR1Table(data.records || []);
    } catch (err) {
      console.error('Failed to load GSTR-1 records:', err);
    }
  }

  // OBJECTIVE 5: Expanded GSTR-1 Data Table
  function renderGSTR1Table(records: GSTRecordItem[]) {
    const tbody = document.getElementById('tbody-gstr1');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="15" style="text-align:center; color:var(--text-muted);">No GSTR-1 records found for ${selectedFy}.</td></tr>`;
      return;
    }

    records.forEach((r) => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', r.id.toString());
      if (r.is_edited) tr.classList.add('edited-row');

      const overrideBadge = r.is_edited
        ? `<span class="badge badge-edited">[Overridden]</span>`
        : `<span class="badge" style="color:var(--text-muted); font-weight:normal;">[Original]</span>`;

      tr.innerHTML = `
        <td>${r.id}</td>
        <td><strong>${r.period}</strong></td>
        <td>${r.financial_year}</td>
        <td class="cell-turnover">₹${r.turnover.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-b2b">₹${(r.b2b_supplies || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-b2clg">₹${(r.b2c_large || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-b2csm">₹${(r.b2c_small || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-exp">₹${(r.exports || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-nil">₹${(r.nil_exempt || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-crdr">₹${(r.cr_dr_notes || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-tot-tax" style="font-weight:700; color:var(--primary-accent);">₹${(r.total_tax_liability || r.tax_liability || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-due">${r.due_date || 'N/A'}</td>
        <td class="cell-filing">${r.actual_filing_date || 'N/A'}</td>
        <td>${overrideBadge}</td>
        <td>
          <button class="btn-primary btn-sm btn-edit-gstr1" data-id="${r.id}">Edit</button>
          <button class="btn-primary btn-sm btn-delete-record" data-id="${r.id}" style="background:var(--danger-bg); color:var(--danger-text);">Delete</button>
        </td>
      `;

      tr.querySelector('.btn-edit-gstr1')?.addEventListener('click', () => startGSTR1Edit(r.id, tbody));
      tr.querySelector('.btn-delete-record')?.addEventListener('click', async () => {
        if (confirm('Delete this GSTR-1 record?')) {
          await deleteRecord(r.id);
        }
      });

      tbody.appendChild(tr);
    });
  }

  function startGSTR1Edit(recordId: number, tbody: HTMLElement) {
    const tr = tbody.querySelector(`tr[data-id="${recordId}"]`) as HTMLTableRowElement;
    if (!tr) return;

    const cellTurnover = tr.querySelector('.cell-turnover') as HTMLElement;
    const cellB2b = tr.querySelector('.cell-b2b') as HTMLElement;
    const cellTotTax = tr.querySelector('.cell-tot-tax') as HTMLElement;
    const cellDue = tr.querySelector('.cell-due') as HTMLElement;
    const cellFiling = tr.querySelector('.cell-filing') as HTMLElement;

    const curTurnover = cellTurnover.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curB2b = cellB2b.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curTotTax = cellTotTax.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curDue = cellDue.textContent?.trim() || '';
    const curFiling = cellFiling.textContent?.trim() || '';

    cellTurnover.innerHTML = `<input type="number" step="0.01" class="input-edit-turnover" value="${curTurnover}" style="width:90px;">`;
    cellB2b.innerHTML = `<input type="number" step="0.01" class="input-edit-b2b" value="${curB2b}" style="width:90px;">`;
    cellTotTax.innerHTML = `<input type="number" step="0.01" class="input-edit-tottax" value="${curTotTax}" style="width:90px;">`;
    cellDue.innerHTML = `<input type="date" class="input-edit-due" value="${curDue}">`;
    cellFiling.innerHTML = `<input type="date" class="input-edit-filing" value="${curFiling}">`;

    const actionCell = tr.children[14];
    actionCell.innerHTML = `
      <button class="btn-primary btn-sm btn-save-record" data-id="${recordId}">Save</button>
      <button class="btn-secondary btn-sm btn-cancel-record">Cancel</button>
    `;

    actionCell.querySelector('.btn-save-record')?.addEventListener('click', () => saveGSTR1Edit(recordId, tr));
    actionCell.querySelector('.btn-cancel-record')?.addEventListener('click', () => loadWorkspaceData());
  }

  async function saveGSTR1Edit(recordId: number, tr: HTMLTableRowElement) {
    const turnoverVal = parseFloat((tr.querySelector('.input-edit-turnover') as HTMLInputElement).value) || 0.0;
    const b2bVal = parseFloat((tr.querySelector('.input-edit-b2b') as HTMLInputElement).value) || 0.0;
    const totTaxVal = parseFloat((tr.querySelector('.input-edit-tottax') as HTMLInputElement).value) || 0.0;
    const dueVal = (tr.querySelector('.input-edit-due') as HTMLInputElement).value;
    const filingVal = (tr.querySelector('.input-edit-filing') as HTMLInputElement).value;

    try {
      const res = await fetch(`/api/gst_tool/records/${recordId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turnover: turnoverVal,
          b2b_supplies: b2bVal,
          tax_liability: totTaxVal,
          total_tax_liability: totTaxVal,
          due_date: dueVal,
          actual_filing_date: filingVal
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceData();
    } catch (err) {
      alert(`Failed to update GSTR-1 record: ${(err as Error).message}`);
    }
  }

  // 3. GSTR-3B Tab
  async function loadGSTR3BTab() {
    try {
      const res = await fetch(`/api/gst_tool/records?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}&return_type=GSTR-3B`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderGSTR3BTable(data.records || []);
    } catch (err) {
      console.error('Failed to load GSTR-3B records:', err);
    }
  }

  // OBJECTIVE 5: Expanded GSTR-3B Data Table
  function renderGSTR3BTable(records: GSTRecordItem[]) {
    const tbody = document.getElementById('tbody-gstr3b');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="14" style="text-align:center; color:var(--text-muted);">No GSTR-3B records found for ${selectedFy}.</td></tr>`;
      return;
    }

    records.forEach((r) => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', r.id.toString());
      if (r.is_edited) tr.classList.add('edited-row');

      const overrideBadge = r.is_edited
        ? `<span class="badge badge-edited">[Overridden]</span>`
        : `<span class="badge" style="color:var(--text-muted); font-weight:normal;">[Original]</span>`;

      tr.innerHTML = `
        <td>${r.id}</td>
        <td><strong>${r.period}</strong></td>
        <td>${r.financial_year}</td>
        <td class="cell-out31a">₹${(r.outward_taxable_3_1_a || r.turnover || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-inrcm">₹${(r.inward_rcm_3_1_d || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-zero31b">₹${(r.zero_rated_3_1_b || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-nil31c">₹${(r.nil_exempt_3_1_c || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-itc4a" style="color:var(--success-text);">₹${(r.itc_available_4_a || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-itc4b" style="color:var(--danger-text);">₹${(r.itc_reversed_4_b || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-netitc" style="font-weight:700; color:var(--emerald-accent);">₹${(r.net_itc_4_c || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="cell-due">${r.due_date || 'N/A'}</td>
        <td class="cell-filing">${r.actual_filing_date || 'N/A'}</td>
        <td>${overrideBadge}</td>
        <td>
          <button class="btn-primary btn-sm btn-edit-gstr3b" data-id="${r.id}">Edit</button>
          <button class="btn-primary btn-sm btn-delete-record" data-id="${r.id}" style="background:var(--danger-bg); color:var(--danger-text);">Delete</button>
        </td>
      `;

      tr.querySelector('.btn-edit-gstr3b')?.addEventListener('click', () => startGSTR3BEdit(r.id, tbody));
      tr.querySelector('.btn-delete-record')?.addEventListener('click', async () => {
        if (confirm('Delete this GSTR-3B record?')) {
          await deleteRecord(r.id);
        }
      });

      tbody.appendChild(tr);
    });
  }

  function startGSTR3BEdit(recordId: number, tbody: HTMLElement) {
    const tr = tbody.querySelector(`tr[data-id="${recordId}"]`) as HTMLTableRowElement;
    if (!tr) return;

    const cellOut31a = tr.querySelector('.cell-out31a') as HTMLElement;
    const cellItc4a = tr.querySelector('.cell-itc4a') as HTMLElement;
    const cellNetItc = tr.querySelector('.cell-netitc') as HTMLElement;
    const cellDue = tr.querySelector('.cell-due') as HTMLElement;
    const cellFiling = tr.querySelector('.cell-filing') as HTMLElement;

    const curOut = cellOut31a.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curItc4a = cellItc4a.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curNetItc = cellNetItc.textContent?.replace(/[₹,]/g, '').trim() || '0';
    const curDue = cellDue.textContent?.trim() || '';
    const curFiling = cellFiling.textContent?.trim() || '';

    cellOut31a.innerHTML = `<input type="number" step="0.01" class="input-edit-out31a" value="${curOut}" style="width:90px;">`;
    cellItc4a.innerHTML = `<input type="number" step="0.01" class="input-edit-itc4a" value="${curItc4a}" style="width:90px;">`;
    cellNetItc.innerHTML = `<input type="number" step="0.01" class="input-edit-netitc" value="${curNetItc}" style="width:90px;">`;
    cellDue.innerHTML = `<input type="date" class="input-edit-due" value="${curDue}">`;
    cellFiling.innerHTML = `<input type="date" class="input-edit-filing" value="${curFiling}">`;

    const actionCell = tr.children[13];
    actionCell.innerHTML = `
      <button class="btn-primary btn-sm btn-save-record" data-id="${recordId}">Save</button>
      <button class="btn-secondary btn-sm btn-cancel-record">Cancel</button>
    `;

    actionCell.querySelector('.btn-save-record')?.addEventListener('click', () => saveGSTR3BEdit(recordId, tr));
    actionCell.querySelector('.btn-cancel-record')?.addEventListener('click', () => loadWorkspaceData());
  }

  async function saveGSTR3BEdit(recordId: number, tr: HTMLTableRowElement) {
    const outVal = parseFloat((tr.querySelector('.input-edit-out31a') as HTMLInputElement).value) || 0.0;
    const itc4aVal = parseFloat((tr.querySelector('.input-edit-itc4a') as HTMLInputElement).value) || 0.0;
    const netItcVal = parseFloat((tr.querySelector('.input-edit-netitc') as HTMLInputElement).value) || 0.0;
    const dueVal = (tr.querySelector('.input-edit-due') as HTMLInputElement).value;
    const filingVal = (tr.querySelector('.input-edit-filing') as HTMLInputElement).value;

    try {
      const res = await fetch(`/api/gst_tool/records/${recordId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turnover: outVal,
          outward_taxable_3_1_a: outVal,
          itc_available_4_a: itc4aVal,
          net_itc_4_c: netItcVal,
          due_date: dueVal,
          actual_filing_date: filingVal
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceData();
    } catch (err) {
      alert(`Failed to update GSTR-3B record: ${(err as Error).message}`);
    }
  }

  async function deleteRecord(recordId: number) {
    try {
      const res = await fetch(`/api/gst_tool/records/${recordId}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceData();
    } catch (err) {
      alert(`Failed to delete record: ${(err as Error).message}`);
    }
  }

  document.getElementById('btn-add-manual-gstr1')?.addEventListener('click', () => addManualRecord('GSTR-1'));
  document.getElementById('btn-add-manual-gstr3b')?.addEventListener('click', () => addManualRecord('GSTR-3B'));

  async function addManualRecord(returnType: string) {
    const period = prompt(`Enter ${returnType} Period (e.g. April 2024):`, 'April 2024');
    if (!period) return;

    try {
      const res = await fetch('/api/gst_tool/records', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: clientId,
          return_type: returnType,
          financial_year: selectedFy,
          period: period,
          turnover: 500000.0,
          tax_liability: 90000.0,
          due_date: returnType === 'GSTR-3B' ? '2024-05-20' : '2024-05-11',
          actual_filing_date: '2024-05-18',
          b2b_supplies: 350000.0,
          b2c_small: 150000.0,
          total_tax_liability: 90000.0,
          outward_taxable_3_1_a: 500000.0,
          itc_available_4_a: 75000.0,
          net_itc_4_c: 75000.0
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceData();
    } catch (err) {
      alert(`Failed to add record: ${(err as Error).message}`);
    }
  }

  // OBJECTIVE 1: Dropzone PDF Upload Handlers with Error Banners
  setupPDFDropzone('dropzone-gstr1', 'file-input-gstr1', 'status-gstr1', 'GSTR-1');
  setupPDFDropzone('dropzone-gstr3b', 'file-input-gstr3b', 'status-gstr3b', 'GSTR-3B');

  function setupPDFDropzone(dropzoneId: string, fileInputId: string, statusId: string, returnType: string) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(fileInputId) as HTMLInputElement;
    const status = document.getElementById(statusId);

    if (!dropzone || !fileInput) return;

    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach((name) => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((name) => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', async (e: DragEvent) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.pdf'));
        if (files.length > 0) await uploadPDFs(files, returnType, status);
      }
    });

    fileInput.addEventListener('change', async () => {
      if (fileInput.files) {
        const files = Array.from(fileInput.files);
        if (files.length > 0) await uploadPDFs(files, returnType, status);
      }
    });
  }

  async function uploadPDFs(files: File[], returnType: string, statusEl: HTMLElement | null) {
    if (statusEl) statusEl.innerHTML = `<div style="color:var(--primary-accent); padding:8px;">Uploading & validating ${files.length} PDF file(s)...</div>`;

    const formData = new FormData();
    formData.append('client_id', clientId.toString());
    formData.append('return_type', returnType);
    files.forEach((f) => formData.append('files', f));

    try {
      const res = await fetch('/api/gst_tool/upload_pdf', {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const errorJson = await res.json().catch(() => null);
        const errorMsg = (errorJson && errorJson.detail) ? errorJson.detail : `HTTP Upload Error ${res.status}`;
        if (statusEl) {
          statusEl.innerHTML = `<div style="color:var(--danger-text); background:var(--danger-bg); border:1px solid var(--danger-text); padding:10px; border-radius:8px; font-weight:600; margin-top:8px;">${errorMsg}</div>`;
        }
        return;
      }

      const data = await res.json();
      if (statusEl) statusEl.innerHTML = `<div style="color:var(--success-text); background:var(--success-bg); border:1px solid var(--success-text); padding:10px; border-radius:8px; font-weight:600; margin-top:8px;">Successfully parsed & saved ${data.count} ${returnType} return(s)!</div>`;
      await loadWorkspaceData();
    } catch (err) {
      if (statusEl) {
        statusEl.innerHTML = `<div style="color:var(--danger-text); background:var(--danger-bg); border:1px solid var(--danger-text); padding:10px; border-radius:8px; font-weight:600; margin-top:8px;">Upload Error: ${(err as Error).message}</div>`;
      }
    }
  }

  // 4. Electronic Ledgers Tab
  async function loadLedgersTab() {
    try {
      const res = await fetch(`/api/gst_tool/ledgers/${clientId}?financial_year=${encodeURIComponent(selectedFy)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const valCash = document.getElementById('val-total-cash');
      const valCredit = document.getElementById('val-total-credit');
      if (valCash) valCash.textContent = `₹${data.total_cash.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
      if (valCredit) valCredit.textContent = `₹${data.total_credit.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

      renderLedgersTable(data.ledgers || []);
    } catch (err) {
      console.error('Failed to load ledgers:', err);
    }
  }

  function renderLedgersTable(ledgers: LedgerItem[]) {
    const tbody = document.getElementById('tbody-ledgers');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (ledgers.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No electronic ledger entries found for ${selectedFy}.</td></tr>`;
      return;
    }

    ledgers.forEach((l) => {
      const tr = document.createElement('tr');
      const typeBadge = l.ledger_type === 'Cash'
        ? `<span class="badge badge-success">Cash</span>`
        : `<span class="badge badge-warning">Credit</span>`;

      tr.innerHTML = `
        <td>${l.id}</td>
        <td>${typeBadge}</td>
        <td>${l.date}</td>
        <td>${l.description}</td>
        <td><strong>₹${l.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</strong></td>
        <td>
          <button class="btn-primary btn-sm btn-delete-ledger" data-id="${l.id}" style="background:var(--danger-bg); color:var(--danger-text);">Delete</button>
        </td>
      `;

      tr.querySelector('.btn-delete-ledger')?.addEventListener('click', async () => {
        if (confirm('Delete this ledger entry?')) {
          await deleteLedger(l.id);
        }
      });

      tbody.appendChild(tr);
    });
  }

  document.getElementById('btn-add-ledger')?.addEventListener('click', async () => {
    const type = prompt('Enter Ledger Type (Cash or Credit):', 'Cash');
    if (!type) return;
    const desc = prompt('Enter Description:', 'Tax payment / ITC credit');
    if (!desc) return;
    const amtStr = prompt('Enter Amount (₹):', '50000');
    if (!amtStr) return;

    try {
      const res = await fetch(`/api/gst_tool/ledgers/${clientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          financial_year: selectedFy,
          ledger_type: type.trim(),
          date: new Date().toISOString().split('T')[0],
          description: desc,
          amount: parseFloat(amtStr) || 0.0
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadLedgersTab();
    } catch (err) {
      alert(`Failed to add ledger entry: ${(err as Error).message}`);
    }
  });

  async function deleteLedger(id: number) {
    try {
      const res = await fetch(`/api/gst_tool/ledgers/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadLedgersTab();
    } catch (err) {
      alert(`Failed to delete ledger entry: ${(err as Error).message}`);
    }
  }

  // 5. Settings Tab & Dual-Method Import
  async function loadSettingsTab() {
    try {
      const res = await fetch(`/api/gst_tool/settings/${clientId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      const dbPath = document.getElementById('settings-db-path');
      const statGstr1 = document.getElementById('stat-gstr1');
      const statGstr3b = document.getElementById('stat-gstr3b');
      const statLedgers = document.getElementById('stat-ledgers');
      const statDbsize = document.getElementById('stat-dbsize');

      if (dbPath && data.database_repository) dbPath.textContent = data.database_repository.absolute_path;
      if (statGstr1 && data.stats) statGstr1.textContent = data.stats.gstr1_records.toString();
      if (statGstr3b && data.stats) statGstr3b.textContent = data.stats.gstr3b_records.toString();
      if (statLedgers && data.stats) statLedgers.textContent = data.stats.ledger_entries.toString();
      if (statDbsize && data.database_repository) statDbsize.textContent = data.database_repository.size_formatted;
    } catch (err) {
      console.error('Failed to load settings tab:', err);
    }
  }

  // OBJECTIVE 1: Form GST REG-06 PDF Upload Handler with Strict GSTIN Validation
  if (fileReg06) {
    fileReg06.addEventListener('change', async () => {
      if (!fileReg06.files || fileReg06.files.length === 0) return;
      const file = fileReg06.files[0];
      if (statusReg06) statusReg06.innerHTML = `<div style="color:var(--primary-accent); padding:4px;">Uploading and validating Form GST REG-06...</div>`;

      const formData = new FormData();
      formData.append('client_id', clientId.toString());
      formData.append('file', file);

      try {
        const res = await fetch('/api/gst_tool/upload_reg06_pdf', {
          method: 'POST',
          body: formData
        });

        if (!res.ok) {
          const errJson = await res.json().catch(() => null);
          const errMsg = (errJson && errJson.detail) ? errJson.detail : `HTTP Error ${res.status}`;
          if (statusReg06) statusReg06.innerHTML = `<div style="color:var(--danger-text); background:var(--danger-bg); border:1px solid var(--danger-text); padding:8px; border-radius:6px; font-weight:600;">${errMsg}</div>`;
          return;
        }

        const data = await res.json();
        if (statusReg06) statusReg06.innerHTML = `<div style="color:var(--success-text); background:var(--success-bg); border:1px solid var(--success-text); padding:8px; border-radius:6px; font-weight:600;">Successfully imported Master Data from REG-06!</div>`;
        await loadClientProfile();
      } catch (err) {
        if (statusReg06) statusReg06.innerHTML = `<div style="color:var(--danger-text); background:var(--danger-bg); border:1px solid var(--danger-text); padding:8px; border-radius:6px; font-weight:600;">REG-06 import error: ${(err as Error).message}</div>`;
      }
    });
  }

  // Option B: Mock GSP Public API Fetch Handler
  if (btnFetchGstinPortal) {
    btnFetchGstinPortal.addEventListener('click', async () => {
      if (!currentClient || !currentClient.gstin) return;
      if (statusGspFetch) statusGspFetch.innerHTML = `<div style="color:var(--primary-accent); padding:4px;">Fetching public GST details for ${currentClient.gstin}...</div>`;

      try {
        const res = await fetch(`/api/gst_tool/fetch_gstin_public/${currentClient.gstin}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        const apiData = result.data;

        if (confirm(`GST Portal API returned details:\nLegal Name: ${apiData.legal_name}\nTrade Name: ${apiData.trade_name}\nAddress: ${apiData.address}\n\nUpdate Client Master Data?`)) {
          const putRes = await fetch(`/api/gst_tool/clients/${clientId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              name: apiData.legal_name,
              trade_name: apiData.trade_name,
              status: apiData.status,
              constitution: apiData.constitution,
              address: apiData.address,
              registration_date: apiData.registration_date
            })
          });
          if (!putRes.ok) throw new Error(`HTTP ${putRes.status}`);
          if (statusGspFetch) statusGspFetch.innerHTML = `<div style="color:var(--success-text); padding:4px;">Master Data updated from GST Portal!</div>`;
          await loadClientProfile();
        } else {
          if (statusGspFetch) statusGspFetch.innerHTML = `<div style="color:var(--warning-text); padding:4px;">Portal fetch cancelled.</div>`;
        }
      } catch (err) {
        if (statusGspFetch) statusGspFetch.innerHTML = `<div style="color:var(--danger-text); padding:4px;">GSP fetch error: ${(err as Error).message}</div>`;
      }
    });
  }

  // Initial Workspace Load
  loadWorkspaceData();
});
