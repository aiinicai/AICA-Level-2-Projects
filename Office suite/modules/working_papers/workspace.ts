interface ClientItem {
  id: number;
  name: string;
  trade_name?: string;
  gstin?: string;
  status?: string;
}

interface FDRecordItem {
  id: number;
  client_id: number;
  financial_year: string;
  bank_name: string;
  fd_account_number: string;
  principal_amount: number;
  date_of_issue: string;
  date_of_maturity: string;
  interest_rate: number;
  compounding_frequency: string;
  opening_accrued_interest: number;
  tds_deducted: number;
  status: string;
  opening_principal: number;
  created_principal: number;
  matured_principal: number;
  settled_accrued_interest: number;
  is_roll_forward: boolean;
  py_record_id: number | null;
  original_maturity_days: number;
  remaining_maturity_days: number;
  interest_income: number;
  closing_accrued_interest: number;
  closing_principal: number;
  closing_total_balance: number;
  classification_class: string;
  classification_label: string;
}

interface RecoItem {
  bank_name: string;
  deductor_name_26as: string;
  tan: string;
  fd_interest: number;
  as26_interest: number;
  variance: number;
  fd_tds: number;
  as26_tds: number;
  status: string;
  match_score: number;
}

interface SummaryData {
  status: string;
  financial_year: string;
  total_fds: number;
  overall_closing_principal: number;
  overall_accrued_interest: number;
  overall_total_interest_income: number;
  overall_total_balance: number;
  class_1_cash_equivalents: {
    count: number;
    total_opening_principal: number;
    total_created_principal: number;
    total_matured_principal: number;
    total_closing_principal: number;
    total_accrued_interest: number;
    total_interest_income: number;
    total_balance: number;
  };
  class_2_other_current: {
    count: number;
    total_opening_principal: number;
    total_created_principal: number;
    total_matured_principal: number;
    total_closing_principal: number;
    total_accrued_interest: number;
    total_interest_income: number;
    total_balance: number;
  };
  class_3_non_current: {
    count: number;
    total_opening_principal: number;
    total_created_principal: number;
    total_matured_principal: number;
    total_closing_principal: number;
    total_accrued_interest: number;
    total_interest_income: number;
    total_balance: number;
  };
}

document.addEventListener('DOMContentLoaded', () => {
  // Theme sync listener
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
  const activeClientStatus = document.getElementById('active-client-status') as HTMLElement;
  
  const btnRefreshData = document.getElementById('btn-refresh-data') as HTMLButtonElement;
  const btnTriggerRollforward = document.getElementById('btn-trigger-rollforward') as HTMLButtonElement;
  const btnDownloadTemplate = document.getElementById('btn-download-template') as HTMLButtonElement;
  const btnExportExcel = document.getElementById('btn-export-excel') as HTMLButtonElement;

  // Summary Widgets Elements
  const valClass1Total = document.getElementById('val-class1-total') as HTMLElement;
  const valClass1Count = document.getElementById('val-class1-count') as HTMLElement;

  const valClass2Total = document.getElementById('val-class2-total') as HTMLElement;
  const valClass2Count = document.getElementById('val-class2-count') as HTMLElement;

  const valClass3Total = document.getElementById('val-class3-total') as HTMLElement;
  const valClass3Count = document.getElementById('val-class3-count') as HTMLElement;

  const valOverallTotal = document.getElementById('val-overall-total') as HTMLElement;
  const valOverallCount = document.getElementById('val-overall-count') as HTMLElement;
  const valOverallInterest = document.getElementById('val-overall-interest') as HTMLElement;
  const valOverallAccrued = document.getElementById('val-overall-accrued') as HTMLElement;
  const valReportingDate = document.getElementById('val-reporting-date') as HTMLElement;

  // Uploaders & Status
  const dropzoneExcel = document.getElementById('dropzone-excel') as HTMLElement;
  const fileExcel = document.getElementById('file-excel') as HTMLInputElement;
  const statusExcel = document.getElementById('status-excel') as HTMLElement;

  const dropzonePdf = document.getElementById('dropzone-pdf') as HTMLElement;
  const filePdf = document.getElementById('file-pdf') as HTMLInputElement;
  const statusPdf = document.getElementById('status-pdf') as HTMLElement;

  const dropzone26as = document.getElementById('dropzone-26as') as HTMLElement;
  const file26as = document.getElementById('file-26as') as HTMLInputElement;
  const status26as = document.getElementById('status-26as') as HTMLElement;

  // Reconciliation Table Elements
  const btnDelete26asData = document.getElementById('btn-delete-26as-data') as HTMLButtonElement;
  const recoSummaryText = document.getElementById('reco-summary-text') as HTMLElement;
  const tbodyReco = document.getElementById('tbody-reco') as HTMLElement;

  // Table & Section Elements
  const btnDeleteAllFds = document.getElementById('btn-delete-all-fds') as HTMLButtonElement;
  const modalFd = document.getElementById('modal-fd') as HTMLElement;
  const formFd = document.getElementById('form-fd') as HTMLFormElement;
  const modalFdTitle = document.getElementById('modal-fd-title') as HTMLElement;
  const inputFdId = document.getElementById('input-fd-id') as HTMLInputElement;
  const inputBankName = document.getElementById('input-bank-name') as HTMLInputElement;
  const inputFdAcc = document.getElementById('input-fd-acc') as HTMLInputElement;
  const inputPrincipal = document.getElementById('input-principal') as HTMLInputElement;
  const inputRate = document.getElementById('input-rate') as HTMLInputElement;
  const selectFreq = document.getElementById('select-freq') as HTMLSelectElement;
  const inputDateIssue = document.getElementById('input-date-issue') as HTMLInputElement;
  const inputDateMaturity = document.getElementById('input-date-maturity') as HTMLInputElement;
  const inputOpeningAccrued = document.getElementById('input-opening-accrued') as HTMLInputElement;
  const inputTds = document.getElementById('input-tds') as HTMLInputElement;
  const selectFdStatus = document.getElementById('select-fd-status') as HTMLSelectElement;
  const btnOpenAddFdModal = document.getElementById('btn-open-add-fd-modal') as HTMLButtonElement;
  const btnCloseFdModal = document.getElementById('btn-close-fd-modal') as HTMLButtonElement;

  // FY Dropdown Listener
  if (selectFy) {
    selectedFy = selectFy.value;
    selectFy.addEventListener('change', () => {
      selectedFy = selectFy.value;
      updateReportingDateLabel();
      loadWorkspaceData();
    });
  }

  function updateReportingDateLabel() {
    try {
      const parts = selectedFy.split('-');
      const yr = parts[1].length === 2 ? `20${parts[1]}` : parts[1];
      if (valReportingDate) valReportingDate.textContent = `As of Mar 31, ${yr}`;
    } catch (e) {
      if (valReportingDate) valReportingDate.textContent = `Reporting Date`;
    }
  }

  // --- API LOADERS ---
  async function loadClientProfile() {
    try {
      const res = await fetch(`/api/working_papers/entities/${clientId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      currentClient = data.entity || data.client;
      renderClientHeader();
    } catch (err) {
      console.error('Failed to load client profile:', err);
      currentClient = { id: clientId, name: "Acme Enterprises Private Limited", status: "Active" };
      renderClientHeader();
    }
  }

  function renderClientHeader() {
    if (!currentClient) return;
    if (activeClientName) activeClientName.textContent = currentClient.name;
    if (activeClientStatus) {
      activeClientStatus.textContent = currentClient.status || 'Active';
      activeClientStatus.className = (currentClient.status || 'Active') === 'Active' ? 'badge badge-success' : 'badge badge-danger';
    }
  }

  async function loadWorkspaceData() {
    await Promise.all([
      loadClientProfile(),
      loadSummaryWidgets(),
      loadFDRecordsTable(),
      load26ASReconciliation()
    ]);
  }

  // Refresh Button Handler
  if (btnRefreshData) {
    btnRefreshData.addEventListener('click', async () => {
      btnRefreshData.classList.add('refreshing');
      await loadWorkspaceData();
      btnRefreshData.classList.remove('refreshing');
    });
  }

  // Delete All Button Handler
  if (btnDeleteAllFds) {
    btnDeleteAllFds.addEventListener('click', async () => {
      if (confirm(`Are you sure you want to delete ALL FD entries for ${selectedFy}? This will also delete any downstream rolled-forward entries in future financial years.`)) {
        try {
          const res = await fetch(`/api/working_papers/records_all?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`, {
            method: 'DELETE'
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          alert(`Deleted all ${data.deleted_count} FD record(s) for ${selectedFy}.`);
          await loadWorkspaceData();
        } catch (err) {
          alert(`Failed to delete records: ${(err as Error).message}`);
        }
      }
    });
  }

  // Delete 26AS Data Button Handler
  if (btnDelete26asData) {
    btnDelete26asData.addEventListener('click', async () => {
      if (confirm(`Are you sure you want to delete all imported Form 26AS entries for ${selectedFy}?`)) {
        try {
          const res = await fetch(`/api/working_papers/as26_all?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`, {
            method: 'DELETE'
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const data = await res.json();
          alert(`Deleted ${data.deleted_count} Form 26AS entry(ies) for ${selectedFy}.`);
          if (status26as) status26as.innerHTML = '';
          await loadWorkspaceData();
        } catch (err) {
          alert(`Failed to delete 26AS data: ${(err as Error).message}`);
        }
      }
    });
  }

  // 1. Summary Widgets Loader
  async function loadSummaryWidgets() {
    try {
      const res = await fetch(`/api/working_papers/summary?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: SummaryData = await res.json();
      renderSummaryWidgets(data);
    } catch (err) {
      console.error('Failed to load summary widgets:', err);
    }
  }

  function renderSummaryWidgets(data: SummaryData) {
    const c1 = data.class_1_cash_equivalents;
    const c2 = data.class_2_other_current;
    const c3 = data.class_3_non_current;

    // Show Principal Balances for Class 1, Class 2, Class 3 (without accrued interest)
    if (valClass1Total) valClass1Total.textContent = `₹${(c1.total_closing_principal || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    if (valClass1Count) valClass1Count.textContent = `${c1.count} FD Record(s)`;

    if (valClass2Total) valClass2Total.textContent = `₹${(c2.total_closing_principal || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    if (valClass2Count) valClass2Count.textContent = `${c2.count} FD Record(s)`;

    if (valClass3Total) valClass3Total.textContent = `₹${(c3.total_closing_principal || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    if (valClass3Count) valClass3Count.textContent = `${c3.count} FD Record(s)`;

    // Grand Total FD Principal Investments
    if (valOverallTotal) valOverallTotal.textContent = `₹${(data.overall_closing_principal || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    if (valOverallCount) valOverallCount.textContent = `${data.total_fds} Total FDs`;

    // Separate Tile 5: Total Interest Income (FY)
    if (valOverallInterest) valOverallInterest.textContent = `₹${(data.overall_total_interest_income || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    // Separate Tile 6: Total Accrued Interest
    if (valOverallAccrued) valOverallAccrued.textContent = `₹${(data.overall_accrued_interest || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
  }

  // 2. FD Records Table Loader
  async function loadFDRecordsTable() {
    try {
      const res = await fetch(`/api/working_papers/records?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderFDTable(data.records || []);
    } catch (err) {
      console.error('Failed to load FD records:', err);
    }
  }

  function renderFDTable(records: FDRecordItem[]) {
    const tbody = document.getElementById('tbody-fds');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (records.length === 0) {
      tbody.innerHTML = `<tr><td colspan="21" style="text-align:center; color:var(--text-muted);">No FD records found for ${selectedFy}.</td></tr>`;
      return;
    }

    records.forEach((r) => {
      const tr = document.createElement('tr');
      tr.setAttribute('data-id', r.id.toString());
      if (r.is_roll_forward) {
        tr.className = 'row-rollforward';
      }

      let badgeClass = 'badge-class2';
      if (r.classification_class === 'Class 1') badgeClass = 'badge-class1';
      else if (r.classification_class === 'Class 3') badgeClass = 'badge-class3';

      let classificationBadge = `<span class="badge ${badgeClass}">${r.classification_class}: ${r.classification_label}</span>`;
      if (r.is_roll_forward) {
        classificationBadge += ` <span class="badge badge-rollforward" style="margin-left:4px;">Roll-Forward (PY)</span>`;
      }

      tr.innerHTML = `
        <td>${r.id}</td>
        <td><strong>${r.bank_name}</strong></td>
        <td><span class="gstin-badge">${r.fd_account_number}</span></td>
        <td>₹${r.opening_principal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="color:var(--primary-accent);">+₹${r.created_principal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="color:var(--warning-text);">-₹${r.matured_principal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="font-weight:700;">₹${r.closing_principal.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>${r.date_of_issue}</td>
        <td>${r.date_of_maturity}</td>
        <td>${r.interest_rate}%</td>
        <td>${r.compounding_frequency}</td>
        <td>${r.original_maturity_days} days</td>
        <td>${r.remaining_maturity_days} days</td>
        <td>₹${r.opening_accrued_interest.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="color:var(--success-text);">₹${r.interest_income.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${r.tds_deducted.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${r.settled_accrued_interest.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${r.closing_accrued_interest.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="font-weight:700; color:var(--primary-accent);">₹${r.closing_total_balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>${classificationBadge}</td>
        <td>
          <button class="btn-primary btn-sm btn-edit-fd" data-id="${r.id}">Edit</button>
          <button class="btn-primary btn-sm btn-delete-fd" data-id="${r.id}" style="background:var(--danger-bg); color:var(--danger-text);">Delete</button>
        </td>
      `;

      tr.querySelector('.btn-edit-fd')?.addEventListener('click', () => openEditFdModal(r));
      tr.querySelector('.btn-delete-fd')?.addEventListener('click', async () => {
        if (confirm(`Delete FD record "${r.bank_name} (${r.fd_account_number})"?`)) {
          await deleteFDRecord(r.id);
        }
      });

      tbody.appendChild(tr);
    });
  }

  // 3. Form 26AS Reconciliation Loader
  async function load26ASReconciliation() {
    try {
      const res = await fetch(`/api/working_papers/reconciliation_26as?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      render26ASReconciliationTable(data);
    } catch (err) {
      console.error('Failed to load 26AS reconciliation:', err);
    }
  }

  function render26ASReconciliationTable(data: any) {
    if (!tbodyReco) return;
    tbodyReco.innerHTML = '';

    const items: RecoItem[] = data.items || [];

    if (recoSummaryText) {
      recoSummaryText.textContent = `FD Interest: ₹${(data.total_fd_interest || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })} | 26AS 194A: ₹${(data.total_26as_interest || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })} | Variance: ₹${(data.total_variance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }

    if (items.length === 0) {
      tbodyReco.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-muted);">No 26AS entries loaded yet. Import Form 26AS PDF above to view bank reconciliation.</td></tr>`;
      return;
    }

    items.forEach((item) => {
      const tr = document.createElement('tr');

      let statusBadge = `<span class="badge badge-success">Matched</span>`;
      if (item.status === '26AS Interest Higher') {
        statusBadge = `<span class="badge badge-warning">26AS Interest Higher</span>`;
      } else if (item.status === 'FD Interest Higher') {
        statusBadge = `<span class="badge badge-warning">FD Interest Higher</span>`;
      } else if (item.status.includes('Unmatched')) {
        statusBadge = `<span class="badge badge-danger">${item.status}</span>`;
      }

      tr.innerHTML = `
        <td><strong>${item.bank_name}</strong></td>
        <td>${item.deductor_name_26as}</td>
        <td><span class="gstin-badge">${item.tan}</span></td>
        <td>₹${item.fd_interest.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="color:var(--purple-accent); font-weight:600;">₹${item.as26_interest.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td style="font-weight:700; color:${item.variance === 0 ? 'var(--success-text)' : 'var(--danger-text)'}">₹${item.variance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>₹${item.fd_tds.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>${statusBadge}</td>
      `;

      tbodyReco.appendChild(tr);
    });
  }

  // --- ACTIONS & EXPORTS ---

  // Download Template
  if (btnDownloadTemplate) {
    btnDownloadTemplate.addEventListener('click', () => {
      window.location.href = '/api/working_papers/template';
    });
  }

  // Export Working Paper (.xlsx)
  if (btnExportExcel) {
    btnExportExcel.addEventListener('click', () => {
      window.location.href = `/api/working_papers/export_working_paper?client_id=${clientId}&financial_year=${encodeURIComponent(selectedFy)}`;
    });
  }

  // Upload Excel Handler
  if (dropzoneExcel && fileExcel) {
    dropzoneExcel.addEventListener('click', () => fileExcel.click());

    ['dragenter', 'dragover'].forEach((name) => {
      dropzoneExcel.addEventListener(name, (e) => {
        e.preventDefault();
        dropzoneExcel.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((name) => {
      dropzoneExcel.addEventListener(name, (e) => {
        e.preventDefault();
        dropzoneExcel.classList.remove('dragover');
      });
    });

    dropzoneExcel.addEventListener('drop', async (e: DragEvent) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.xlsx') || f.name.endsWith('.xls'));
        if (files.length > 0) await uploadExcelFile(files[0]);
      }
    });

    fileExcel.addEventListener('change', async () => {
      if (fileExcel.files && fileExcel.files.length > 0) {
        await uploadExcelFile(fileExcel.files[0]);
      }
    });
  }

  async function uploadExcelFile(file: File) {
    if (statusExcel) statusExcel.innerHTML = `<div style="color:var(--primary-accent); padding:4px;">Uploading and computing Excel schedule...</div>`;

    const formData = new FormData();
    formData.append('client_id', clientId.toString());
    formData.append('financial_year', selectedFy);
    formData.append('file', file);

    try {
      const res = await fetch('/api/working_papers/upload_excel', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      if (statusExcel) statusExcel.innerHTML = `<div style="color:var(--success-text); padding:4px;">Successfully imported & computed ${data.processed_count} FD record(s)!</div>`;
      await loadWorkspaceData();
    } catch (err) {
      if (statusExcel) statusExcel.innerHTML = `<div style="color:var(--danger-text); padding:4px;">Import error: ${(err as Error).message}</div>`;
    }
  }

  // Upload PDF Handler
  if (dropzonePdf && filePdf) {
    dropzonePdf.addEventListener('click', () => filePdf.click());

    ['dragenter', 'dragover'].forEach((name) => {
      dropzonePdf.addEventListener(name, (e) => {
        e.preventDefault();
        dropzonePdf.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((name) => {
      dropzonePdf.addEventListener(name, (e) => {
        e.preventDefault();
        dropzonePdf.classList.remove('dragover');
      });
    });

    dropzonePdf.addEventListener('drop', async (e: DragEvent) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.pdf'));
        if (files.length > 0) await uploadPdfFile(files[0]);
      }
    });

    filePdf.addEventListener('change', async () => {
      if (filePdf.files && filePdf.files.length > 0) {
        await uploadPdfFile(filePdf.files[0]);
      }
    });
  }

  async function uploadPdfFile(file: File) {
    if (statusPdf) statusPdf.innerHTML = `<div style="color:var(--primary-accent); padding:4px;">Parsing FD Receipt PDF...</div>`;

    const formData = new FormData();
    formData.append('client_id', clientId.toString());
    formData.append('financial_year', selectedFy);
    formData.append('file', file);

    try {
      const res = await fetch('/api/working_papers/upload_pdf', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      if (statusPdf) statusPdf.innerHTML = `<div style="color:var(--success-text); padding:4px;">Successfully parsed & saved FD receipt!</div>`;
      await loadWorkspaceData();
    } catch (err) {
      if (statusPdf) statusPdf.innerHTML = `<div style="color:var(--danger-text); padding:4px;">PDF error: ${(err as Error).message}</div>`;
    }
  }

  // Upload Form 26AS PDF Handler
  if (dropzone26as && file26as) {
    dropzone26as.addEventListener('click', () => file26as.click());

    ['dragenter', 'dragover'].forEach((name) => {
      dropzone26as.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone26as.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach((name) => {
      dropzone26as.addEventListener(name, (e) => {
        e.preventDefault();
        dropzone26as.classList.remove('dragover');
      });
    });

    dropzone26as.addEventListener('drop', async (e: DragEvent) => {
      if (e.dataTransfer && e.dataTransfer.files) {
        const files = Array.from(e.dataTransfer.files).filter((f) => f.name.endsWith('.pdf') || f.name.endsWith('.csv'));
        if (files.length > 0) await upload26asFile(files[0]);
      }
    });

    file26as.addEventListener('change', async () => {
      if (file26as.files && file26as.files.length > 0) {
        await upload26asFile(file26as.files[0]);
      }
    });
  }

  async function upload26asFile(file: File) {
    if (status26as) status26as.innerHTML = `<div style="color:var(--purple-accent); padding:4px;">Parsing Form 26AS File (Sec 194A)...</div>`;

    const formData = new FormData();
    formData.append('client_id', clientId.toString());
    formData.append('financial_year', selectedFy);
    formData.append('file', file);

    try {
      const res = await fetch('/api/working_papers/upload_26as', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      if (status26as) status26as.innerHTML = `<div style="color:var(--success-text); padding:4px;">Parsed & reconciled ${data.parsed_count} Form 26AS Sec 194A entry(ies)!</div>`;
      await loadWorkspaceData();
    } catch (err) {
      if (status26as) status26as.innerHTML = `<div style="color:var(--danger-text); padding:4px;">26AS error: ${(err as Error).message}</div>`;
    }
  }

  // --- MODAL FD FORM FUNCTIONS ---
  function openAddFdModal() {
    if (modalFdTitle) modalFdTitle.textContent = 'Add Manual Fixed Deposit';
    if (inputFdId) inputFdId.value = '';
    if (inputBankName) inputBankName.value = '';
    if (inputFdAcc) inputFdAcc.value = '';
    if (inputPrincipal) inputPrincipal.value = '';
    if (inputRate) inputRate.value = '';
    if (selectFreq) selectFreq.value = 'Quarterly';
    if (inputDateIssue) inputDateIssue.value = '';
    if (inputDateMaturity) inputDateMaturity.value = '';
    if (inputOpeningAccrued) inputOpeningAccrued.value = '0.0';
    if (inputTds) inputTds.value = '0.0';
    if (selectFdStatus) selectFdStatus.value = 'Active';
    modalFd.classList.add('active');
  }

  function openEditFdModal(record: FDRecordItem) {
    if (modalFdTitle) modalFdTitle.textContent = 'Edit Fixed Deposit Record';
    if (inputFdId) inputFdId.value = record.id.toString();
    if (inputBankName) inputBankName.value = record.bank_name;
    if (inputFdAcc) inputFdAcc.value = record.fd_account_number;
    if (inputPrincipal) inputPrincipal.value = record.principal_amount.toString();
    if (inputRate) inputRate.value = record.interest_rate.toString();
    if (selectFreq) selectFreq.value = record.compounding_frequency;
    if (inputDateIssue) inputDateIssue.value = record.date_of_issue;
    if (inputDateMaturity) inputDateMaturity.value = record.date_of_maturity;
    if (inputOpeningAccrued) inputOpeningAccrued.value = record.opening_accrued_interest.toString();
    if (inputTds) inputTds.value = record.tds_deducted.toString();
    if (selectFdStatus) selectFdStatus.value = record.status;
    modalFd.classList.add('active');
  }

  function closeFdModal() {
    modalFd.classList.remove('active');
  }

  if (btnOpenAddFdModal) btnOpenAddFdModal.addEventListener('click', openAddFdModal);
  if (btnCloseFdModal) btnCloseFdModal.addEventListener('click', closeFdModal);

  if (formFd) {
    formFd.addEventListener('submit', async (e) => {
      e.preventDefault();
      const id = inputFdId.value;
      const bankName = inputBankName.value.trim();
      const fdAcc = inputFdAcc.value.trim();
      const principal = parseFloat(inputPrincipal.value) || 0.0;
      const rate = parseFloat(inputRate.value) || 0.0;
      const freq = selectFreq.value;
      const dateIssue = inputDateIssue.value;
      const dateMaturity = inputDateMaturity.value;
      const openingAccrued = parseFloat(inputOpeningAccrued.value) || 0.0;
      const tds = parseFloat(inputTds.value) || 0.0;
      const status = selectFdStatus.value;

      try {
        if (id) {
          const res = await fetch(`/api/working_papers/records/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              bank_name: bankName,
              fd_account_number: fdAcc,
              principal_amount: principal,
              interest_rate: rate,
              compounding_frequency: freq,
              date_of_issue: dateIssue,
              date_of_maturity: dateMaturity,
              opening_accrued_interest: openingAccrued,
              tds_deducted: tds,
              status: status
            })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        } else {
          const res = await fetch('/api/working_papers/records', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              client_id: clientId,
              financial_year: selectedFy,
              bank_name: bankName,
              fd_account_number: fdAcc,
              principal_amount: principal,
              interest_rate: rate,
              compounding_frequency: freq,
              date_of_issue: dateIssue,
              date_of_maturity: dateMaturity,
              opening_accrued_interest: openingAccrued,
              tds_deducted: tds,
              status: status
            })
          });
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
        }

        closeFdModal();
        await loadWorkspaceData();
      } catch (err) {
        alert(`Failed to save FD record: ${(err as Error).message}`);
      }
    });
  }

  async function deleteFDRecord(id: number) {
    try {
      const res = await fetch(`/api/working_papers/records/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await loadWorkspaceData();
    } catch (err) {
      alert(`Failed to delete record: ${(err as Error).message}`);
    }
  }

  // Initial Workspace Load
  updateReportingDateLabel();
  loadWorkspaceData();
});
