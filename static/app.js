let currentProfile = {};
let mappingRegisterData = [];
let schedule3MasterMap = {};
let schedule3MasterList = [];

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    loadCompanyProfile();
    loadReconciliation();
    loadImportedLedgersTable();
    loadSchedule3Master();
});

function initTheme() {
    const savedTheme = localStorage.getItem('app_theme') || 'royal';
    changeAppTheme(savedTheme, false);
    const sel = document.getElementById('themeSelector');
    if (sel) sel.value = savedTheme;
}

function changeAppTheme(themeName, persist = true) {
    document.body.classList.remove('theme-emerald', 'theme-burgundy', 'theme-midnight', 'theme-terracotta');
    if (themeName !== 'royal') {
        document.body.classList.add(`theme-${themeName}`);
    }
    if (persist) {
        localStorage.setItem('app_theme', themeName);
        showToast(`Theme switched to ${themeName.charAt(0).toUpperCase() + themeName.slice(1)}`, 'info');
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.nav-tab').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(sec => sec.classList.remove('active'));
    document.querySelectorAll('.workflow-stepper .step').forEach(st => st.classList.remove('active'));
    document.querySelectorAll('.sub-nav-pill').forEach(pill => pill.classList.remove('active'));

    const activeBtn = document.querySelector(`.nav-tab[onclick="switchTab('${tabId}')"]`);
    if (activeBtn) activeBtn.classList.add('active');

    const targetSec = document.getElementById(`tab-${tabId}`);
    if (targetSec) targetSec.classList.add('active');

    // Update Sub-nav pills
    document.querySelectorAll(`.sub-nav-pill[onclick="switchTab('${tabId}')"]`).forEach(pill => pill.classList.add('active'));

    // Update Stepper active state
    let stepId = 'step-setup';
    if (tabId === 'import') stepId = 'step-import';
    else if (tabId === 'mapping') stepId = 'step-mapping';
    else if (tabId === 'exceptions') stepId = 'step-exceptions';
    else if (['bs', 'pl', 'cashflow', 'ratios', 'corp_policies', 'notes'].includes(tabId)) stepId = 'step-bs';
    const stepEl = document.getElementById(stepId);
    if (stepEl) stepEl.classList.add('active');

    if (tabId === 'import') loadImportedLedgersTable();
    if (tabId === 'mapping') loadMappingRegister();
    if (tabId === 'exceptions') loadReconciliation();
    if (tabId === 'bs' || tabId === 'pl' || tabId === 'cashflow' || tabId === 'ratios') loadStatements();
    if (tabId === 'corp_policies') loadCorporatePolicies();
    if (tabId === 'notes') loadNotes();
}

async function loadCompanyProfile() {
    try {
        const res = await fetch('/api/company');
        const data = await res.json();
        currentProfile = data;

        document.getElementById('company_name').value = data.company_name || '';
        document.getElementById('financial_statement_type').value = data.financial_statement_type || 'Standalone';
        document.getElementById('financial_year').value = data.financial_year || '2023-24';
        document.getElementById('comparative_year').value = data.comparative_year || '2022-23';
        document.getElementById('currency').value = data.currency || 'INR';
        document.getElementById('rounding_unit').value = data.rounding_unit || 'Lakhs';
        document.getElementById('decimal_places').value = data.decimal_places || 2;
        document.getElementById('entity_type').value = data.entity_type || 'Non-SMC';
        document.getElementById('cin').value = data.cin || '';
        document.getElementById('registered_address').value = data.registered_address || '';

        updateRoundingBadge();
    } catch (err) {
        console.error("Failed to load company settings:", err);
    }
}

async function saveCompanySettings(e) {
    e.preventDefault();
    const btn = e.submitter || document.querySelector('#companyForm button[type=submit]');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ Saving...'; }

    const payload = {
        company_name: document.getElementById('company_name').value,
        financial_statement_type: document.getElementById('financial_statement_type').value,
        financial_year: document.getElementById('financial_year').value,
        comparative_year: document.getElementById('comparative_year').value,
        currency: document.getElementById('currency').value,
        rounding_unit: document.getElementById('rounding_unit').value,
        decimal_places: parseInt(document.getElementById('decimal_places').value),
        entity_type: document.getElementById('entity_type').value,
        cin: document.getElementById('cin').value,
        registered_address: document.getElementById('registered_address').value
    };

    try {
        const res = await fetch('/api/company', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await res.json();
        showToast('✅ Profile saved! Now import your Trial Balance.', 'success');
    } catch (err) {
        showToast('⚠️ Could not save to server — please ensure the app is running. Proceeding anyway.', 'warning');
        console.warn('Save error:', err);
    } finally {
        if (btn) { btn.disabled = false; btn.innerHTML = '💾 Save Profile & Proceed to TB Import ➔'; }
        await loadCompanyProfile();
        switchTab('import');
    }
}

function showToast(msg, type = 'success') {
    let toast = document.getElementById('appToast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'appToast';
        toast.style.cssText = 'position:fixed;bottom:28px;right:28px;z-index:99999;padding:14px 22px;border-radius:10px;font-size:14px;font-weight:600;max-width:380px;box-shadow:0 8px 24px rgba(0,0,0,0.18);transition:opacity 0.4s;';
        document.body.appendChild(toast);
    }
    toast.style.background = type === 'success' ? '#10b981' : type === 'warning' ? '#f59e0b' : '#ef4444';
    toast.style.color = 'white';
    toast.style.opacity = '1';
    toast.textContent = msg;
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => { toast.style.opacity = '0'; }, 3500);
}

function updateRoundingBadge() {
    const badge = document.getElementById('currentRoundingBadge');
    if (badge) badge.innerText = `Unit: ${currentProfile.rounding_unit || 'Lakhs'}`;
}

async function loadImportedLedgersTable() {
    try {
        const res = await fetch('/api/import/ledgers');
        const rows = await res.json();
        const tbody = document.getElementById('importedTbBody');
        if (!tbody) return;

        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center text-muted">No Trial Balance imported yet. Upload a file or click "Load Demo Sample Data".</td></tr>`;
            ['totTxDr','totTxCr','totClDr','totClCr','totPY'].forEach(id => {
                const el = document.getElementById(id); if (el) el.textContent = '—';
            });
            return;
        }

        const fmt = v => Math.abs(v || 0).toLocaleString('en-IN', {minimumFractionDigits: 2});

        let txDr = 0, txCr = 0, clDr = 0, clCr = 0, pyDr = 0, pyCr = 0;

        tbody.innerHTML = rows.map(r => {
            const opBal = r.opening_dr > 0
                ? `${fmt(r.opening_dr)} Dr`
                : r.opening_cr > 0
                    ? `<span style="color:#991b1b">${fmt(r.opening_cr)} Cr</span>`
                    : '0.00';
            txDr += (r.debit || 0);
            txCr += (r.credit || 0);
            clDr += (r.closing_dr || 0);
            clCr += (r.closing_cr || 0);
            if ((r.prior_closing_net || 0) >= 0) pyDr += (r.prior_closing_net || 0);
            else pyCr += Math.abs(r.prior_closing_net || 0);
            const pyBal = (r.prior_closing_net || 0) < 0
                ? `<span style="color:#991b1b">${fmt(r.prior_closing_net)} Cr</span>`
                : `${fmt(r.prior_closing_net)} Dr`;
            return `
            <tr>
                <td><strong>${r.ledger_name}</strong></td>
                <td><span class="badge badge-secondary">${r.tally_group}</span></td>
                <td class="text-right">${opBal}</td>
                <td class="text-right">${fmt(r.debit)}</td>
                <td class="text-right">${fmt(r.credit)}</td>
                <td class="text-right" style="color:#166534;font-weight:600;">${r.closing_dr > 0 ? fmt(r.closing_dr) : '—'}</td>
                <td class="text-right" style="color:#991b1b;font-weight:600;">${r.closing_cr > 0 ? fmt(r.closing_cr) : '—'}</td>
                <td class="text-right">${pyBal}</td>
            </tr>`;
        }).join('');

        // Update tfoot totals
        const setTot = (id, val, style) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = val.toLocaleString('en-IN', {minimumFractionDigits: 2});
                if (style) el.style.cssText = style;
            }
        };
        setTot('totTxDr', txDr);
        setTot('totTxCr', txCr);
        setTot('totClDr', clDr);
        setTot('totClCr', clCr);

        // Tally check: Closing Dr ≈ Closing Cr?
        const diff = Math.abs(clDr - clCr);
        const totClDrEl = document.getElementById('totClDr');
        const totClCrEl = document.getElementById('totClCr');
        if (diff < 1) {
            if (totClDrEl) totClDrEl.style.background = '#d1fae5';
            if (totClCrEl) totClCrEl.style.background = '#d1fae5';
        } else {
            if (totClDrEl) totClDrEl.style.background = '#fee2e2';
            if (totClCrEl) totClCrEl.style.background = '#fee2e2';
        }

        // PY total
        const totPYEl = document.getElementById('totPY');
        if (totPYEl) totPYEl.textContent = `Dr ${pyDr.toLocaleString('en-IN',{minimumFractionDigits:2})} / Cr ${pyCr.toLocaleString('en-IN',{minimumFractionDigits:2})}`;

    } catch (err) {
        console.error("Failed to load imported ledgers:", err);
    }
}


async function loadSampleData() {
    try {
        const res = await fetch('/api/import/sample', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        await loadImportedLedgersTable();
        await loadReconciliation();
        switchTab('import');
    } catch (err) {
        alert("Error loading sample data: " + err.message);
    }
}

async function uploadTbFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/import/upload', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.status === 'success') {
            alert(data.message);
            await loadImportedLedgersTable();
            await loadReconciliation();
            switchTab('import');
        } else {
            alert("Upload failed: " + data.message);
        }
    } catch (err) {
        alert("Upload error: " + err.message);
    }
}

async function loadMappingRegister() {
    const filter = document.getElementById('mappingFilterStatus').value;
    try {
        const res = await fetch(`/api/mapping/register?status=${filter}`);
        const rows = await res.json();
        mappingRegisterData = rows;

        const tbody = document.getElementById('mappingRegisterBody');
        if (rows.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center text-muted">No mappings found. Import a Trial Balance first.</td></tr>`;
            return;
        }

        tbody.innerHTML = rows.map(r => `
            <tr>
                <td><strong>${r.ledger_name}</strong></td>
                <td><span class="badge badge-secondary">${r.tally_group}</span></td>
                <td class="${r.closing_net < 0 ? 'text-danger' : ''}">${Math.abs(r.closing_net).toLocaleString('en-IN', {minimumFractionDigits: 2})} ${r.closing_net < 0 ? 'Cr' : 'Dr'}</td>
                <td>${r.schedule3_head ? `<strong>${r.schedule3_head}</strong>` : '<span class="text-danger">Unmapped</span>'}</td>
                <td class="text-center">${r.note_no || '-'}</td>
                <td class="text-center"><span class="badge ${r.normal_balance === 'Dr' ? 'badge-primary' : 'badge-secondary'}">${r.normal_balance || '-'}</span></td>
                <td>${r.classification || 'Current'}</td>
                <td>${r.cash_flow_category || 'Operating'}</td>
                <td>
                    <span class="badge ${r.review_status === 'Approved' ? 'badge-success' : 'badge-warning'}">
                        ${r.review_status}
                    </span>
                </td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="openMappingModal('${encodeURIComponent(r.ledger_name)}')">Edit</button>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        console.error("Failed to load mapping register:", err);
    }
}

async function runAutoMapping() {
    try {
        const res = await fetch('/api/mapping/auto', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        loadMappingRegister();
        loadReconciliation();
    } catch (err) {
        alert("Error re-running mapping: " + err.message);
    }
}

async function applyBulkMapping() {
    const group = document.getElementById('bulkTallyGroup').value;
    const code = document.getElementById('bulkScheduleCode').value;
    const note = document.getElementById('bulkNoteNo').value;

    if (!group || !code) {
        alert("Please enter Tally Group and Schedule III Code");
        return;
    }

    try {
        const res = await fetch('/api/mapping/bulk', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ tally_group: group, schedule3_code: code, note_no: note })
        });
        const data = await res.json();
        alert(data.message);
        loadMappingRegister();
        loadReconciliation();
    } catch (err) {
        alert("Error in bulk mapping: " + err.message);
    }
}

async function loadSchedule3Master() {
    try {
        const res = await fetch('/api/schedule3/master');
        schedule3MasterList = await res.json();
        schedule3MasterMap = {};

        const select = document.getElementById('edit_schedule3_code');
        const bulkSelect = document.getElementById('bulkScheduleCode');

        if (select && schedule3MasterList.length > 0) {
            select.innerHTML = '';
            schedule3MasterList.forEach(item => {
                schedule3MasterMap[item.code] = item;
                const opt = document.createElement('option');
                opt.value = item.code;
                const noteText = item.note_no ? ` (Note ${item.note_no})` : '';
                opt.textContent = `${item.line_item_name}${noteText}`;
                select.appendChild(opt);
            });
        }

        if (bulkSelect && schedule3MasterList.length > 0) {
            bulkSelect.innerHTML = '<option value="">-- Select Schedule III Line Item --</option>';
            schedule3MasterList.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item.code;
                const noteText = item.note_no ? ` (Note ${item.note_no})` : '';
                opt.textContent = `${item.line_item_name}${noteText}`;
                bulkSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.error("Failed to load Schedule 3 Master items:", err);
    }
}

function onBulkScheduleCodeChange() {
    const code = document.getElementById('bulkScheduleCode').value;
    const master = schedule3MasterMap[code];
    if (master) {
        document.getElementById('bulkNoteNo').value = master.note_no || '';
    } else {
        document.getElementById('bulkNoteNo').value = '';
    }
}

function onScheduleCodeChange() {
    const code = document.getElementById('edit_schedule3_code').value;
    const master = schedule3MasterMap[code];
    if (master) {
        // Auto fill Note No.
        document.getElementById('edit_note_no').value = master.note_no || '';
        // Auto select Classification if default exists
        if (master.default_classification && master.default_classification !== 'N/A') {
            document.getElementById('edit_classification').value = master.default_classification;
        }
        // Auto select Cash Flow Category if default exists
        if (master.cash_flow_category) {
            document.getElementById('edit_cash_flow').value = master.cash_flow_category;
        }
    }
}

function openMappingModal(encodedLedgerName) {
    const ledgerName = decodeURIComponent(encodedLedgerName);
    const item = mappingRegisterData.find(r => r.ledger_name === ledgerName);
    if (!item) return;

    document.getElementById('edit_ledger_name').value = item.ledger_name;
    document.getElementById('edit_ledger_display').value = item.ledger_name;

    const selectedCode = item.schedule3_code || 'OTHER_CURRENT_LIAB';
    document.getElementById('edit_schedule3_code').value = selectedCode;

    const master = schedule3MasterMap[selectedCode];
    // If note_no is present on ledger mapping, use it; otherwise auto-populate from master
    document.getElementById('edit_note_no').value = item.note_no || (master ? master.note_no : '');
    document.getElementById('edit_classification').value = item.classification || (master ? master.default_classification : 'Current');
    document.getElementById('edit_cash_flow').value = item.cash_flow_category || (master ? master.cash_flow_category : 'Operating');
    document.getElementById('edit_review_status').value = item.review_status || 'Approved';

    document.getElementById('mappingModal').style.display = 'flex';
}

function closeMappingModal() {
    document.getElementById('mappingModal').style.display = 'none';
}

async function saveMappingEdit(e) {
    e.preventDefault();
    const payload = {
        ledger_name: document.getElementById('edit_ledger_name').value,
        schedule3_code: document.getElementById('edit_schedule3_code').value,
        note_no: document.getElementById('edit_note_no').value,
        classification: document.getElementById('edit_classification').value,
        cash_flow_category: document.getElementById('edit_cash_flow').value,
        review_status: document.getElementById('edit_review_status').value,
        review_note: 'Manual user edit'
    };

    try {
        const res = await fetch('/api/mapping/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        closeMappingModal();
        loadMappingRegister();
        loadReconciliation();
    } catch (err) {
        alert("Error updating mapping: " + err.message);
    }
}

async function loadReconciliation() {
    try {
        const res = await fetch('/api/reconciliation');
        const data = await res.json();

        // Update Stats
        document.getElementById('tbBalanceStatus').innerText = data.tb_stats.is_balanced ? "Balanced" : "Out of Balance";
        document.getElementById('tbBalanceStatus').className = data.tb_stats.is_balanced ? "stat-value text-success" : "stat-value text-danger";
        
        document.getElementById('bsDiffValue').innerText = data.financial_totals.bs_diff.toLocaleString('en-IN', {minimumFractionDigits: 2});
        document.getElementById('bsDiffValue').className = data.financial_totals.is_bs_balanced ? "stat-value text-success" : "stat-value text-danger";

        document.getElementById('unmappedCountVal').innerText = data.mapping_stats.unmapped_count;
        document.getElementById('reviewCountVal').innerText = data.mapping_stats.pending_reviews;
        
        // Badges in sidebar
        document.getElementById('reviewCountBadge').innerText = data.mapping_stats.pending_reviews;
        document.getElementById('exceptionBadge').innerText = data.exceptions.length;

        // Render Exceptions
        const exContainer = document.getElementById('exceptionsContainer');
        if (data.exceptions.length === 0) {
            exContainer.innerHTML = `<div class="badge badge-success" style="padding:10px; font-size:13px;">✅ Zero reconciliation exceptions identified. Financial statements tally perfectly!</div>`;
        } else {
            exContainer.innerHTML = data.exceptions.map(ex => `
                <div class="exception-item severity-${ex.severity}">
                    <strong>[${ex.category}]</strong> ${ex.message}
                </div>
            `).join('');
        }

        // Render Checklist - store data globally for modal access
        window._currentChecklistData = data.mandatory_checklist;
        const checkBody = document.getElementById('checklistBody');
        checkBody.innerHTML = data.mandatory_checklist.map((item, idx) => `
            <tr>
                <td><strong>${item.id}</strong></td>
                <td>${item.item}</td>
                <td><span class="badge ${item.status === 'Computed / Ready' || item.status === 'Completed / Complied' ? 'badge-success' : item.status === 'Not Applicable' ? 'badge-secondary' : 'badge-warning'}">${item.status}</span></td>
                <td style="max-width:220px; font-size:12px; color:#475569; word-break:break-word;">${item.details_text ? item.details_text.substring(0, 80) + (item.details_text.length > 80 ? '...' : '') : '<em class="text-muted">No details entered</em>'}</td>
                <td style="text-align:center;">
                    <button class="btn btn-sm btn-outline" style="font-size:12px; padding:4px 10px;" onclick="openChecklistModalByIdx(${idx})">✏️ Edit</button>
                </td>
            </tr>
        `).join('');

    } catch (err) {
        console.error("Failed to load reconciliation:", err);
    }
}

async function loadStatements() {
    try {
        const res = await fetch('/api/statements');
        const data = await res.json();

        const p = data.profile;
        const u = data.unit;

        // Header Labels
        document.getElementById('bsCompanyName').innerText = p.company_name;
        document.getElementById('bsFY').innerText = p.financial_year;
        document.getElementById('bsUnitHeader').innerText = `(All amounts in ${p.currency} ${u}, unless otherwise stated)`;
        document.getElementById('bsColCY').innerText = p.financial_year;
        document.getElementById('bsColPY').innerText = p.comparative_year;

        document.getElementById('plCompanyName').innerText = p.company_name;
        document.getElementById('plFY').innerText = p.financial_year;
        document.getElementById('plUnitHeader').innerText = `(All amounts in ${p.currency} ${u}, unless otherwise stated)`;
        document.getElementById('plColCY').innerText = p.financial_year;
        document.getElementById('plColPY').innerText = p.comparative_year;

        // Render Balance Sheet Table Body
        const bsBody = document.getElementById('bsTableBody');
        let bsRowsHTML = '';

        const appendBsRow = (row) => {
            if (row.is_header) {
                return `<tr class="header-row"><td colspan="4">${row.title}</td></tr>`;
            } else if (row.is_subheader) {
                return `<tr class="subheader-row"><td colspan="4">${row.title}</td></tr>`;
            } else if (row.is_total) {
                return `<tr class="total-row"><td>${row.title}</td><td></td><td class="text-right">${row.cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${row.py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>`;
            } else {
                return `<tr><td>${row.title}</td><td class="text-center">${row.note || ''}</td><td class="text-right">${row.cy !== undefined ? row.cy.toLocaleString('en-IN', {minimumFractionDigits: 2}) : ''}</td><td class="text-right">${row.py !== undefined ? row.py.toLocaleString('en-IN', {minimumFractionDigits: 2}) : ''}</td></tr>`;
            }
        };

        data.bs_equity_liabilities.forEach(r => bsRowsHTML += appendBsRow(r));
        bsRowsHTML += appendBsRow({title: 'TOTAL EQUITY AND LIABILITIES', is_total: true, cy: data.total_eq_liab_cy, py: data.total_eq_liab_py});
        data.bs_assets.forEach(r => bsRowsHTML += appendBsRow(r));
        bsRowsHTML += appendBsRow({title: 'TOTAL ASSETS', is_total: true, cy: data.total_assets_cy, py: data.total_assets_py});
        
        bsBody.innerHTML = bsRowsHTML;

        // Render Profit & Loss Body
        const plBody = document.getElementById('plTableBody');
        let plRowsHTML = `
            <tr><td>I. Revenue from operations</td><td class="text-center">22</td><td class="text-right">${data.pl_revenue_ops_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.pl_revenue_ops_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr><td>II. Other income</td><td class="text-center">23</td><td class="text-right">${data.pl_other_income_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.pl_other_income_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="header-row"><td>III. Total Revenue (I + II)</td><td></td><td class="text-right">${data.total_revenue_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.total_revenue_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="subheader-row"><td colspan="4">IV. Expenses:</td></tr>
        `;

        data.exp_items.forEach(exp => {
            plRowsHTML += `<tr><td>${exp.title}</td><td class="text-center">${exp.note}</td><td class="text-right">${exp.cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${exp.py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>`;
        });

        plRowsHTML += `
            <tr class="header-row"><td>Total Expenses (IV)</td><td></td><td class="text-right">${data.total_expenses_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.total_expenses_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="header-row"><td>V. Profit before tax (III - IV)</td><td></td><td class="text-right">${data.pbt_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.pbt_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="subheader-row"><td colspan="4">VI. Tax Expense:</td></tr>
            <tr><td>   (1) Current tax</td><td class="text-center">15</td><td class="text-right">${data.tax_curr_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.tax_curr_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr><td>   (2) Deferred tax</td><td class="text-center">15</td><td class="text-right">${data.tax_def_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.tax_def_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="total-row"><td>VII. Profit for the period (V - VI)</td><td></td><td class="text-right">${data.pat_cy.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td><td class="text-right">${data.pat_py.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td></tr>
            <tr class="subheader-row"><td colspan="4">VIII. Earnings per equity share (Par value Rs 10/-):</td></tr>
            <tr><td>   (1) Basic (Rs)</td><td></td><td class="text-right">${data.eps_cy.toFixed(2)}</td><td class="text-right">${data.eps_py.toFixed(2)}</td></tr>
            <tr><td>   (2) Diluted (Rs)</td><td></td><td class="text-right">${data.eps_cy.toFixed(2)}</td><td class="text-right">${data.eps_py.toFixed(2)}</td></tr>
        `;
        plBody.innerHTML = plRowsHTML;

        // ── Render Ratios Table Body ──────────────────────────────────────
        // API returns: { ratio, numerator, denominator, cy, py, variance, benchmark }
        const rBody = document.getElementById('ratiosTableBody');
        if (rBody && data.ratios && data.ratios.length > 0) {
            const fmt2 = v => (v !== null && v !== undefined) ? Number(v).toLocaleString('en-IN', {minimumFractionDigits: 2}) : '\u2014';
            rBody.innerHTML = data.ratios.map(r => {
                const name       = r.name      || r.ratio      || '\u2014';
                const variance   = r.variance_pct !== undefined ? r.variance_pct
                                 : r.variance   !== undefined ? parseFloat(r.variance) : null;
                const varClass   = variance !== null && !isNaN(variance) && Math.abs(variance) > 25
                                   ? 'text-danger font-bold' : '';
                const varText    = r.variance !== undefined ? r.variance
                                 : (variance !== null && !isNaN(variance) ? variance.toFixed(2) + '%' : '\u2014');
                return `
                <tr>
                    <td><strong>${name}</strong></td>
                    <td>${r.numerator || '\u2014'}</td>
                    <td>${r.denominator || '\u2014'}</td>
                    <td class="text-right font-bold">${fmt2(r.cy)}</td>
                    <td class="text-right">${fmt2(r.py)}</td>
                    <td class="text-right ${varClass}">${varText}</td>
                    <td><small class="text-muted">${r.benchmark || ''}</small></td>
                </tr>`;
            }).join('');
        }

        // ── Render Cash Flow Statement (AS-3 Indirect Method) ────────────
        // API returns: cash_flow as a flat dict with keys pbt, depreciation, etc.
        document.querySelectorAll('.unitText').forEach(el => el.innerText = u);
        const cfBody = document.getElementById('cfTableBody');
        if (cfBody && data.cash_flow) {
            const cfCN = document.getElementById('cfCompanyName');
            const cfFY = document.getElementById('cfFY');
            const cfUH = document.getElementById('cfUnitHeader');
            const cfCY = document.getElementById('cfColCY');
            const cfPY = document.getElementById('cfColPY');
            if (cfCN) cfCN.innerText = p.company_name;
            if (cfFY) cfFY.innerText = p.financial_year;
            if (cfUH) cfUH.innerText = `(All amounts in ${p.currency} ${u}, unless otherwise stated)`;
            if (cfCY) cfCY.innerText = p.financial_year;
            if (cfPY) cfPY.innerText = p.comparative_year;

            // Handle BOTH formats:
            //   NEW format: cash_flow is an array of row objects (future)
            //   CURRENT format: cash_flow is a flat dict
            if (Array.isArray(data.cash_flow)) {
                // Array-of-rows format
                const appendCfRow = (row) => {
                    const fv = v => (v !== null && v !== undefined) ? Number(v).toLocaleString('en-IN', {minimumFractionDigits: 2}) : '\u2014';
                    if (row.is_header)    return `<tr class="header-row"><td colspan="3">${row.title}</td></tr>`;
                    if (row.is_subheader) return `<tr class="subheader-row"><td colspan="3">${row.title}</td></tr>`;
                    if (row.is_total)     return `<tr class="total-row"><td>${row.title}</td><td class="text-right">${fv(row.cy)}</td><td class="text-right">${fv(row.py)}</td></tr>`;
                    return `<tr><td style="padding-left:24px;">${row.title}</td><td class="text-right">${fv(row.cy)}</td><td class="text-right">${fv(row.py)}</td></tr>`;
                };
                cfBody.innerHTML = data.cash_flow.map(appendCfRow).join('');
            } else {
                // Flat-dict format (current backend)
                const cf = data.cash_flow;
                const fv = v => (v !== undefined && v !== null)
                    ? Number(v).toLocaleString('en-IN', {minimumFractionDigits: 2})
                    : '0.00';
                const br = (label, val, indent=true, isSub=false, isTotal=false) => {
                    const cls = isTotal ? 'total-row' : isSub ? 'subheader-row' : '';
                    const pad = indent && !isSub && !isTotal ? 'style="padding-left:28px;"' : '';
                    return `<tr class="${cls}"><td ${pad}>${label}</td><td class="text-right">${fv(val)}</td><td class="text-right"></td></tr>`;
                };
                const hr = label => `<tr class="header-row"><td colspan="3"><strong>${label}</strong></td></tr>`;
                const totRow = (label, cy, py) => `<tr class="total-row"><td><strong>${label}</strong></td><td class="text-right"><strong>${fv(cy)}</strong></td><td class="text-right"><strong>${fv(py)}</strong></td></tr>`;
                const blankRow = () => `<tr><td colspan="3" style="height:8px;"></td></tr>`;

                let html = '';
                // A. OPERATING
                html += hr('A. CASH FLOW FROM OPERATING ACTIVITIES');
                html += br('Profit before tax',                                         cf.pbt);
                html += br('Add: Depreciation and Amortization',                        cf.depreciation);
                html += br('Add: Finance Costs',                                        cf.finance_costs);
                if (cf.interest_income > 0)
                    html += br('Less: Interest Income',                                 -cf.interest_income);
                html += `<tr class="subheader-row"><td><strong>Operating Cash Flow before Working Capital changes</strong></td><td class="text-right"><strong>${fv(cf.op_cash_before_wc)}</strong></td><td></td></tr>`;
                html += br('(Increase) / Decrease in Inventories',                      cf.inv_change);
                html += br('(Increase) / Decrease in Trade Receivables',                cf.rec_change);
                html += br('(Increase) / Decrease in Other Current Assets & Loans',    (cf.other_ca_change || 0) + (cf.st_loans_change || 0));
                html += br('Increase / (Decrease) in Trade Payables',                  cf.pay_change);
                html += br('Increase / (Decrease) in Other Current Liabilities & Provisions', cf.other_liab_change || 0);
                html += br('Less: Direct Taxes Paid',                                   -(cf.tax_paid || 0));
                html += totRow('Net Cash Flow from Operating Activities (A)',            cf.net_operating, '');
                html += blankRow();

                // B. INVESTING
                html += hr('B. CASH FLOW FROM INVESTING ACTIVITIES');
                html += br('Purchase of Property, Plant & Equipment',                   cf.ppe_purchase);
                if (cf.interest_income > 0)
                    html += br('Interest Received',                                     cf.interest_income);
                html += totRow('Net Cash Flow from Investing Activities (B)',            cf.net_investing, '');
                html += blankRow();

                // C. FINANCING
                html += hr('C. CASH FLOW FROM FINANCING ACTIVITIES');
                if ((cf.share_capital_proceeds || 0) !== 0)
                    html += br('Proceeds from Issue of Share Capital',                  cf.share_capital_proceeds);
                html += br('Proceeds from / (Repayment of) Borrowings',                cf.borrowings_change);
                html += br('Finance Costs Paid',                                        -(cf.finance_costs || 0));
                html += totRow('Net Cash Flow from Financing Activities (C)',            cf.net_financing, '');
                html += blankRow();

                // NET INCREASE
                html += totRow('Net Increase / (Decrease) in Cash & Cash Equivalents (A+B+C)', cf.net_cash_increase, '');
                html += br('Cash & Cash Equivalents at the beginning of the year',     cf.opening_cash);
                html += `<tr class="total-row" style="border-top:2px solid #1e3a8a;"><td><strong>Cash & Cash Equivalents at the end of the year</strong></td><td class="text-right"><strong style="color:#166534;">${fv(cf.closing_cash)}</strong></td><td class="text-right"></td></tr>`;
                html += `<tr><td colspan="3" style="font-size:12px; color:#64748b; padding:6px 12px; font-style:italic;">Note: Closing cash per Balance Sheet = ${fv(cf.actual_closing_cash || cf.closing_cash)}. Variance = ${fv(Math.abs((cf.actual_closing_cash || cf.closing_cash) - cf.closing_cash))}.</td></tr>`;

                cfBody.innerHTML = html;
            }
        }

    } catch (err) {
        console.error("Failed to load financial statements:", err);
    }
}


async function loadNotes() {
    const container = document.getElementById('notesContainer');
    try {
        const res = await fetch('/api/notes');
        const data = await res.json();
        if (!data.notes || data.notes.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No notes data available. Please import Trial Balance and map ledgers first.</p>';
            return;
        }

        const p = data.profile;
        const cy = p.financial_year;
        const py = p.comparative_year;

        document.getElementById('notesCompanyName').innerText = p.company_name + ' — Notes & Financial Schedules (Notes 2 to 29)';
        document.getElementById('notesUnitHeader').innerText =
            `All amounts in ${p.currency} ${p.rounding_unit} unless otherwise stated | FY ${cy} with comparative FY ${py} | Option to add custom auditor remarks under each note.`;

        // Note 1 is exclusively managed under the "Corporate Info & Policies" tab
        const scheduleNotes = data.notes.filter(n => n.note_no !== '1');

        let html = '';
        for (const note of scheduleNotes) {
            const isApproved = note.review_status === 'Approved';
            const reviewBadge = isApproved
                ? '<span class="badge" style="background:#dcfce7; color:#15803d; border:1px solid #86efac; margin-left:10px; font-weight:600; padding:2px 8px; border-radius:4px; font-size:11px;">✅ CA Approved</span>'
                : (note.review_flag || note.review_status === 'Pending')
                    ? '<span class="badge badge-warning" style="margin-left:10px; font-weight:600; padding:2px 8px; border-radius:4px; font-size:11px;">⚠️ CA Review Required</span>'
                    : '';

            html += `
            <div class="note-block" id="note-${note.note_no}">
                <div class="note-header" onclick="toggleNote('note-body-${note.note_no}', this)" style="display:flex; align-items:center; cursor:pointer;">
                    <span class="note-number">Note ${note.note_no}</span>
                    <span class="note-title">${note.title}${reviewBadge}</span>
                    <span class="note-toggle">▼</span>
                </div>
                <div class="note-body" id="note-body-${note.note_no}">`;

            // ── Interactive CA Review / Sign-off Banner ──────────────────────────
            const caReviewMsg = note.sections.find(s => s.ca_review)?.ca_review || (note.review_flag ? 'Statutory Schedule III verification required for classification, terms, and disclosure completeness.' : null);

            if (caReviewMsg || note.review_flag) {
                const alertBg = isApproved ? '#f0fdf4' : '#fffbeb';
                const alertBorder = isApproved ? '#86efac' : '#fde68a';
                const alertText = isApproved ? '#15803d' : '#92400e';

                html += `
                <div class="ca-review-interactive-card" style="background:${alertBg}; border:1px solid ${alertBorder}; border-radius:8px; padding:14px 18px; margin-bottom:16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                        <div style="display:flex; align-items:flex-start; gap:10px; flex:1;">
                            <span style="font-size:18px; line-height:1;">${isApproved ? '✅' : '⚖️'}</span>
                            <div>
                                <strong style="color:${alertText}; font-size:13px;">${isApproved ? 'CA Review Completed & Approved' : 'Statutory CA Review Required:'}</strong>
                                <p style="margin:2px 0 0 0; font-size:12.5px; color:#475569; line-height:1.4;">${escHtml(caReviewMsg || '')}</p>
                                ${isApproved && note.reviewed_by ? `<span style="font-size:11px; color:#16a34a; font-weight:600;">Signed off by ${escHtml(note.reviewed_by)} ${note.reviewed_at ? '(' + note.reviewed_at.split('T')[0] + ')' : ''}</span>` : ''}
                            </div>
                        </div>
                        <div style="display:flex; gap:8px;">
                            ${isApproved 
                                ? `<button type="button" class="btn btn-sm btn-outline" style="font-size:12px; padding:4px 10px; border-radius:6px;" onclick="toggleNoteReviewApproval('${note.note_no}', 'Pending')">↺ Re-open Review</button>`
                                : `<button type="button" class="btn btn-sm btn-primary" style="background:#16a34a; border-color:#16a34a; font-size:12px; padding:6px 14px; font-weight:600; border-radius:6px;" onclick="toggleNoteReviewApproval('${note.note_no}', 'Approved')">✅ Approve Note ${note.note_no}</button>`
                            }
                        </div>
                    </div>
                </div>`;
            }

            for (const sec of note.sections) {
                if (sec.heading) {
                    html += `<h4 class="note-section-heading">${sec.heading}</h4>`;
                }
                if (sec.type === 'text') {
                    html += `<p class="note-text">${sec.content}</p>`;
                } else if (sec.type === 'table') {
                    html += '<div class="table-responsive"><table class="statement-table note-table">';
                    html += '<thead><tr>' + sec.columns.map(c =>
                        `<th class="${sec.columns.indexOf(c) > 0 ? 'text-right' : ''}">${c}</th>`
                    ).join('') + '</tr></thead><tbody>';
                    const rows = sec.rows || [];
                    rows.forEach((row, idx) => {
                        const isTotal = sec.total_row && idx === rows.length - 1;
                        const isSectionHead = row.length > 0 && row.slice(1).every(v => v === '' || v === '—');
                        const cls = isTotal ? 'total-row' : (isSectionHead ? 'subheader-row' : '');
                        html += `<tr class="${cls}">`;
                        row.forEach((cell, ci) => {
                            html += `<td class="${ci > 0 ? 'text-right' : ''}">${cell}</td>`;
                        });
                        html += '</tr>';
                    });
                    html += '</tbody></table></div>';
                }
            }

            // ── Interactive Additional Notes & Footnotes under each note ────
            html += `
                <div class="note-remarks-card" style="margin-top:18px; background:#f8fafc; border:1px solid #cbd5e1; border-radius:8px; padding:14px 18px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; gap:10px; flex-wrap:wrap;">
                        <label style="font-weight:600; font-size:13px; color:#1e3a8a; display:flex; align-items:center; gap:6px;">
                            <span>📝</span> Additional Auditor Remarks & Disclosures for Note ${note.note_no}:
                        </label>
                        <div style="display:flex; gap:8px;">
                            <button type="button" class="btn btn-sm btn-primary" onclick="saveNoteRemarks('${note.note_no}')" style="padding:4px 14px; font-size:12px; border-radius:6px;">💾 Save Remarks</button>
                            ${!isApproved && (note.review_flag || note.review_status === 'Pending')
                                ? `<button type="button" class="btn btn-sm" style="background:#16a34a; color:#fff; border:none; padding:4px 12px; font-size:12px; border-radius:6px; font-weight:600;" onclick="saveRemarksAndApprove('${note.note_no}')">💾 Save & Approve</button>`
                                : ''
                            }
                        </div>
                    </div>
                    <textarea id="noteRemarks_${note.note_no}" class="form-control" rows="3" style="width:100%; padding:10px 12px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; line-height:1.5; resize:vertical; font-family:inherit; color:#1e293b;" placeholder="Enter specific company footnotes, details of security/hypothecation, repayment terms, MSME status, pending litigation details, or auditor remarks related to Note ${note.note_no}...">${escHtml(note.additional_remarks || '')}</textarea>
                </div>
            `;

            html += `</div></div>`;
        }

        container.innerHTML = html;
    } catch (err) {
        container.innerHTML = `<div class="exception-item severity-high">⚠️ Failed to load Notes & Schedules: ${err.message}. Please ensure Trial Balance is imported and all ledgers are mapped.</div>`;
        console.error('loadNotes error:', err);
    }
}

async function toggleNoteReviewApproval(noteNo, newStatus) {
    const txtArea = document.getElementById(`noteRemarks_${noteNo}`);
    const remarks = txtArea ? txtArea.value.trim() : '';

    try {
        const res = await fetch('/api/notes/review/toggle', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: noteNo,
                status: newStatus,
                review_notes: remarks,
                reviewer_name: 'CA Lead Auditor'
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(newStatus === 'Approved' ? `✅ Note ${noteNo} approved successfully!` : `↺ Note ${noteNo} re-opened for review`, 'success');
            await loadNotes();
        } else {
            alert('Error updating review status: ' + data.message);
        }
    } catch (err) {
        alert('Network error while updating review status: ' + err.message);
    }
}

async function saveRemarksAndApprove(noteNo) {
    await saveNoteRemarks(noteNo);
    await toggleNoteReviewApproval(noteNo, 'Approved');
}

async function saveNoteRemarks(noteNo) {
    const txtArea = document.getElementById(`noteRemarks_${noteNo}`);
    const remarks = txtArea ? txtArea.value.trim() : '';

    try {
        const res = await fetch('/api/notes/remarks/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: noteNo,
                additional_remarks: remarks,
                user_name: 'CA Lead Auditor'
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            showToast(`✅ Additional remarks saved for Note ${noteNo}!`, 'success');
        } else {
            alert('Error saving remarks: ' + data.message);
        }
    } catch (err) {
        alert('Network error while saving note remarks: ' + err.message);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
//  DEDICATED CORPORATE INFO & SIGNIFICANT ACCOUNTING POLICIES (NOTE 1) TAB
// ═══════════════════════════════════════════════════════════════════════════

let _directPoliciesList = [];

async function loadCorporatePolicies() {
    const container = document.getElementById('directPoliciesContainer');
    if (!container) return;
    container.innerHTML = '<p class="text-muted text-center" style="padding:30px;">Loading Corporate Information & Accounting Policies...</p>';
    
    try {
        const res = await fetch('/api/notes/custom?note_no=1');
        const data = await res.json();
        if (data.status === 'success') {
            _directPoliciesList = data.sections || [];
            renderDirectPoliciesUI();
        } else {
            container.innerHTML = `<div class="exception-item severity-high">Failed to load Accounting Policies: ${data.message}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div class="exception-item severity-high">Error fetching policies: ${err.message}</div>`;
    }
}

function renderDirectPoliciesUI() {
    const container = document.getElementById('directPoliciesContainer');
    if (!_directPoliciesList || _directPoliciesList.length === 0) {
        container.innerHTML = '<p class="text-muted text-center" style="padding:20px;">No accounting policies found. Click "➕ Add Policy Clause" or "↺ Reset to ICAI Standard".</p>';
        return;
    }

    let html = '';
    _directPoliciesList.forEach((sec, idx) => {
        html += `
        <div class="policy-card-item" style="border:1px solid #cbd5e1; border-radius:10px; padding:18px 22px; background:#ffffff; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; gap:12px;">
                <div style="display:flex; align-items:center; gap:8px; flex:1;">
                    <span style="font-weight:bold; color:#1e40af; font-size:13.5px;">Clause:</span>
                    <input type="text" class="form-control" style="font-weight:700; color:#1e3a8a; font-size:14px; padding:8px 12px; border-radius:6px; border:1px solid #cbd5e1; flex:1;" value="${escHtml(sec.heading || `1.${idx+1} Accounting Policy`)}" id="directPolicyHead_${idx}" onchange="_directPoliciesList[${idx}].heading = this.value">
                </div>
                <button type="button" style="background:#fee2e2; color:#ef4444; border:1px solid #fca5a5; padding:6px 12px; border-radius:6px; font-size:12px; cursor:pointer; font-weight:600;" onclick="removePolicyClause(${idx})">🗑️ Delete Clause</button>
            </div>
            <textarea class="form-control" rows="5" style="width:100%; padding:12px 14px; border-radius:8px; border:1px solid #cbd5e1; font-size:13.5px; line-height:1.6; resize:vertical; font-family:inherit; color:#1e293b;" id="directPolicyContent_${idx}" onchange="_directPoliciesList[${idx}].content = this.value" placeholder="Enter company-specific statutory accounting policy text...">${escHtml(sec.content || '')}</textarea>
        </div>`;
    });

    container.innerHTML = html;
}

function addPolicyClause() {
    const newIdx = (_directPoliciesList.length + 1);
    _directPoliciesList.push({
        heading: `1.${newIdx}  Custom Accounting Policy Clause`,
        type: 'text',
        content: 'Enter company-specific statutory accounting policy clause here...'
    });
    renderDirectPoliciesUI();
    const container = document.getElementById('directPoliciesContainer');
    container.scrollTop = container.scrollHeight;
}

function removePolicyClause(index) {
    if (confirm('Are you sure you want to delete this accounting policy clause?')) {
        _directPoliciesList.splice(index, 1);
        renderDirectPoliciesUI();
    }
}

async function saveDirectPolicies() {
    // Read latest values from DOM
    _directPoliciesList.forEach((sec, idx) => {
        const headEl = document.getElementById(`directPolicyHead_${idx}`);
        const contentEl = document.getElementById(`directPolicyContent_${idx}`);
        if (headEl) sec.heading = headEl.value;
        if (contentEl) sec.content = contentEl.value;
    });

    try {
        const res = await fetch('/api/notes/custom/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: '1',
                sections: _directPoliciesList,
                user_name: 'CA Lead Auditor'
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            showToast('✅ Corporate Information & Accounting Policies saved successfully!', 'success');
        } else {
            alert('Error saving policies: ' + data.message);
        }
    } catch (err) {
        alert('Network error while saving policies: ' + err.message);
    }
}

async function resetPoliciesToDefault() {
    if (!confirm('Are you sure you want to reset all accounting policies to the standard ICAI Schedule III template?')) {
        return;
    }

    try {
        const res = await fetch('/api/notes/custom/reset', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: '1',
                user_name: 'CA Lead Auditor'
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            await loadCorporatePolicies();
            showToast('↺ Accounting policies reset to standard ICAI template', 'info');
        } else {
            alert('Error resetting policies: ' + data.message);
        }
    } catch (err) {
        alert('Network error while resetting policies: ' + err.message);
    }
}


function toggleNote(bodyId, headerEl) {
    const body = document.getElementById(bodyId);
    const toggle = headerEl.querySelector('.note-toggle');
    if (body.style.display === 'none' || body.style.display === '') {
        body.style.display = 'block';
        toggle.textContent = '▲';
    } else {
        body.style.display = 'none';
        toggle.textContent = '▼';
    }
}

function exportData(fmt) {
    const names = {
        'excel': 'Excel Working Papers (.xlsx)',
        'word': 'Word Financials Draft (.docx)',
        'pdf': 'PDF Statutory Report (.pdf)',
        'sample_template': 'Sample Trial Balance Template (.xlsx)'
    };
    showToast(`⏳ Generating ${names[fmt] || fmt.toUpperCase()}...`, 'info');
    
    // Trigger download via hidden link
    const link = document.createElement('a');
    link.href = `/api/export/${fmt}`;
    link.download = '';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function triggerDbBackup() {
    try {
        const res = await fetch('/api/backup', { method: 'POST' });
        const data = await res.json();
        alert(data.message);
    } catch (err) {
        alert("Backup failed: " + err.message);
    }
}

async function runAutomatedTests() {
    const logBox = document.getElementById('testOutputLog');
    logBox.style.display = 'block';
    logBox.innerText = 'Running automated reconciliation and statement test suite...';

    try {
        const res = await fetch('/api/run_tests');
        const data = await res.json();
        logBox.innerText = `[TEST SUITE RESULT: ${data.status.toUpperCase()}]\nTests Run: ${data.tests_run}\nFailures: ${data.failures}\nErrors: ${data.errors}\n\n=== LOG OUTPUT ===\n${data.log}`;
    } catch (err) {
        logBox.innerText = "Error executing tests: " + err.message;
    }
}


// ═══════════════════════════════════════════════════════════════════════════
//  TALLY TB CONVERTER  –  All UI Logic
// ═══════════════════════════════════════════════════════════════════════════

let _tcFile = null;   // Currently selected file

/** Open the converter modal */
function openTallyConverter() {
    document.getElementById('tallyConverterModal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

/** Close via backdrop click */
function closeTallyConverter(evt) {
    if (evt.target === document.getElementById('tallyConverterModal')) {
        closeTallyConverterModal();
    }
}

/** Close the modal */
function closeTallyConverterModal() {
    document.getElementById('tallyConverterModal').style.display = 'none';
    document.body.style.overflow = '';
}

// ESC key support
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        const m = document.getElementById('tallyConverterModal');
        if (m && m.style.display !== 'none') closeTallyConverterModal();
    }
});

// ── File Selection ──────────────────────────────────────────────────────────

function tcFileSelected(evt) {
    const file = evt.target.files[0];
    if (!file) return;
    _tcSetFile(file);
}

function _tcSetFile(file) {
    _tcFile = file;
    // Show file info bar
    document.getElementById('tcFileName').textContent = file.name;
    document.getElementById('tcFileInfo').style.display = 'flex';
    document.getElementById('tcDropZone').style.display = 'none';
    // Enable preview button
    document.getElementById('tcPreviewBtn').disabled = false;
    // Reset other buttons & status
    document.getElementById('tcDownloadBtn').disabled = true;
    document.getElementById('tcImportBtn').disabled = true;
    _tcSetStatus('', '');
    document.getElementById('tcStats').style.display = 'none';
    // Reset preview table
    document.getElementById('tcPreviewBody').innerHTML =
        '<tr><td colspan="7" class="tc-empty-msg">Click <strong>Preview Conversion</strong> to parse this file.</td></tr>';
    document.getElementById('tcPreviewSub').textContent = 'File selected — run preview to see results';
}

function tcClearFile() {
    _tcFile = null;
    document.getElementById('tcFileInfo').style.display = 'none';
    document.getElementById('tcDropZone').style.display = 'block';
    document.getElementById('tcFileInput').value = '';
    document.getElementById('tcPreviewBtn').disabled = true;
    document.getElementById('tcDownloadBtn').disabled = true;
    document.getElementById('tcImportBtn').disabled = true;
    _tcSetStatus('', '');
    document.getElementById('tcStats').style.display = 'none';
    document.getElementById('tcPreviewBody').innerHTML =
        '<tr><td colspan="7" class="tc-empty-msg">Upload a Tally Excel/CSV Trial Balance file and click <strong>Preview Conversion</strong></td></tr>';
    document.getElementById('tcPreviewSub').textContent = 'Upload a file and click "Preview Conversion" to see results';
}

// ── Drag & Drop ─────────────────────────────────────────────────────────────

function tcDragOver(evt) {
    evt.preventDefault();
    document.getElementById('tcDropZone').classList.add('drag-over');
}
function tcDragLeave(evt) {
    document.getElementById('tcDropZone').classList.remove('drag-over');
}
function tcDrop(evt) {
    evt.preventDefault();
    document.getElementById('tcDropZone').classList.remove('drag-over');
    const file = evt.dataTransfer.files[0];
    if (file) _tcSetFile(file);
}

// ── Status Helper ───────────────────────────────────────────────────────────

function _tcSetStatus(msg, type) {
    const el = document.getElementById('tcStatus');
    if (!msg) { el.style.display = 'none'; return; }
    el.className = `tc-status ${type}`;
    el.innerHTML = msg;
    el.style.display = 'block';
}

// ── Preview Conversion ──────────────────────────────────────────────────────

async function tcRunPreview() {
    if (!_tcFile) return;
    const btn = document.getElementById('tcPreviewBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Parsing...';
    _tcSetStatus('⏳ Sending file to server for parsing…', 'loading');

    const fd = new FormData();
    fd.append('file', _tcFile);

    try {
        const res = await fetch('/api/tally-converter/preview', { method: 'POST', body: fd });
        const data = await res.json();

        if (data.status === 'error') {
            _tcSetStatus(`❌ ${data.message}`, 'error');
            btn.disabled = false;
            btn.textContent = '🔍 Preview Conversion';
            return;
        }

        // Render stats
        const stats = data.stats || {};
        document.getElementById('tcStatLedgers').textContent = `📋 ${stats.total_ledgers || 0} Ledgers`;
        document.getElementById('tcStatGroups').textContent  = `🗂 ${stats.groups_detected || 0} Groups`;
        document.getElementById('tcStatStatus').textContent  = '✅ Parsed OK';
        document.getElementById('tcStats').style.display = 'flex';

        // Preview sub-text
        document.getElementById('tcPreviewSub').textContent =
            `${stats.total_ledgers || 0} ledgers detected · ${stats.groups_detected || 0} Tally groups`;

        // Render table
        const preview = data.preview || [];
        const tbody = document.getElementById('tcPreviewBody');
        if (preview.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="tc-empty-msg">No ledgers detected. Check if your file has bold group headers and non-bold ledger rows.</td></tr>';
        } else {
            let prevGroup = null;
            let html = '';
            preview.forEach((row, i) => {
                if (row.tally_group !== prevGroup) {
                    html += `<tr class="tc-group-row">
                        <td colspan="7">🗂 ${escHtml(row.tally_group)}</td>
                    </tr>`;
                    prevGroup = row.tally_group;
                }
                const closingClass = row.closing.includes('Cr') ? 'cr' : 'dr';
                const openingClass = row.opening.includes('Cr') ? 'cr' : 'dr';
                html += `<tr>
                    <td style="color:#94a3b8;font-size:11px">${i + 1}</td>
                    <td title="${escHtml(row.ledger_name)}">${escHtml(row.ledger_name)}</td>
                    <td><span class="tc-grp-pill">${escHtml(row.tally_group)}</span></td>
                    <td class="tc-num ${openingClass}">${escHtml(row.opening)}</td>
                    <td class="tc-num">${escHtml(row.debit)}</td>
                    <td class="tc-num">${escHtml(row.credit)}</td>
                    <td class="tc-num ${closingClass}">${escHtml(row.closing)}</td>
                </tr>`;
            });
            tbody.innerHTML = html;
        }

        // Show warnings if any
        const warnings = (data.errors || []).filter(Boolean);
        if (warnings.length) {
            _tcSetStatus(`⚠️ ${warnings[0]}`, 'error');
        } else {
            _tcSetStatus(`✅ ${data.message}`, 'success');
        }

        // Enable action buttons
        document.getElementById('tcDownloadBtn').disabled = false;
        document.getElementById('tcImportBtn').disabled = false;

    } catch (err) {
        _tcSetStatus(`❌ Network error: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Preview Conversion';
    }
}

// ── Download Converted Excel ────────────────────────────────────────────────

async function tcDownload() {
    if (!_tcFile) return;
    const btn = document.getElementById('tcDownloadBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Generating...';
    _tcSetStatus('⏳ Generating converted Excel file…', 'loading');

    const fd = new FormData();
    fd.append('file', _tcFile);

    try {
        const res = await fetch('/api/tally-converter/download', { method: 'POST', body: fd });
        if (!res.ok) {
            const err = await res.json().catch(() => ({message: 'Unknown error'}));
            _tcSetStatus(`❌ ${err.message}`, 'error');
            return;
        }

        // Trigger browser download
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;

        // Try to get filename from Content-Disposition header
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename="?([^"]+)"?/);
        a.download = match ? match[1] : `Converted_${_tcFile.name.replace(/\.[^.]+$/, '')}.xlsx`;
        a.click();
        URL.revokeObjectURL(url);

        _tcSetStatus('✅ File downloaded successfully! You can now upload it in Step 2 → Import TB.', 'success');
    } catch (err) {
        _tcSetStatus(`❌ Download failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '📥 Download Converted File';
    }
}

// ── Convert & Import Directly ───────────────────────────────────────────────

async function tcImportDirect() {
    if (!_tcFile) return;
    const btn = document.getElementById('tcImportBtn');
    btn.disabled = true;
    btn.textContent = '⏳ Converting & Importing...';
    _tcSetStatus('⏳ Converting and importing into the application…', 'loading');

    const fd = new FormData();
    fd.append('file', _tcFile);

    try {
        const res = await fetch('/api/tally-converter/import', { method: 'POST', body: fd });
        const data = await res.json();

        if (data.status === 'error') {
            _tcSetStatus(`❌ ${data.message}`, 'error');
            return;
        }

        const stats = data.stats || {};
        _tcSetStatus(
            `✅ <strong>Import successful!</strong><br>
            ${stats.total_ledgers || 0} ledgers imported · ${data.mapped || 0} auto-mapped · ${data.reviews || 0} need CA review.<br>
            <em>Close this panel and proceed to Step 3 → Map Ledgers.</em>`,
            'success'
        );

        // Refresh the imported ledgers table in the background
        loadImportedLedgersTable();
        showToast(`✅ Tally TB converted & imported: ${stats.total_ledgers} ledgers, ${data.reviews} need CA review.`, 'success');

    } catch (err) {
        _tcSetStatus(`❌ Import failed: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ Convert & Import Directly';
    }
}

// Utility: escape HTML
function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function escapeHtml(str) {
    return escHtml(str);
}

// ═══════════════════════════════════════════════════════════════════════════
//  MANDATORY CHECKLIST EDIT MODAL LOGIC
// ═══════════════════════════════════════════════════════════════════════════

function openChecklistModalByIdx(idx) {
    const item = (window._currentChecklistData || [])[idx];
    if (!item) return;

    document.getElementById('ckModalRefId').value = item.id;
    document.getElementById('ckModalItemTitle').value = item.item;
    document.getElementById('ckModalTitle').innerText = `Edit Disclosure Details [${item.id}]`;
    document.getElementById('ckModalItemDesc').innerText = item.item;
    document.getElementById('ckModalStatus').value = item.status || 'Requires Input';
    document.getElementById('ckModalDetails').value = item.details_text || '';

    const modal = document.getElementById('checklistEditModal');
    modal.style.display = 'flex';
}

function closeChecklistModal() {
    document.getElementById('checklistEditModal').style.display = 'none';
}

function insertChecklistTemplate() {
    const refId = document.getElementById('ckModalRefId').value;
    const txtArea = document.getElementById('ckModalDetails');

    let template = '';
    if (refId === 'CH01') {
        template = `Shareholders holding > 5% Shares:\n------------------------------------------------------------\nName of Shareholder          | No. of Shares | % of Total Holding\n1. Equity Shares:\n   - Promoter Shareholder A  | 50,000        | 50.00%\n   - Promoter Shareholder B  | 50,000        | 50.00%\n------------------------------------------------------------\n(All shares are fully paid-up equity shares of face value INR 10/- each)`;
    } else if (refId === 'CH02') {
        template = `Promoter Shareholding Pattern:\n------------------------------------------------------------\nPromoter Name                | No. of Shares | % of Total Shares | % Change in CY\n1. Promoter Shareholder A    | 50,000        | 50.00%            | 0.00% (No change)\n2. Promoter Shareholder B    | 50,000        | 50.00%            | 0.00% (No change)\n------------------------------------------------------------`;
    } else if (refId === 'CH06') {
        template = `Corporate Social Responsibility (CSR) Disclosure (Sec 135):\n------------------------------------------------------------\n1. Net Worth: Below INR 500 Cr | Turnover: Below INR 1,000 Cr | Net Profit: Below INR 5 Cr\n2. Applicability: Section 135 is NOT APPLICABLE for the current financial year.\n3. Prescribed CSR Expenditure: Nil\n4. Amount spent during the year: Nil`;
    } else if (refId === 'CH07') {
        template = `Related Party Disclosures under AS-18 (Note 16):\n------------------------------------------------------------\nA. Key Management Personnel (KMP):\n   - Director 1\n   - Director 2\n\nB. Transactions with Related Parties during the year:\n   - Remuneration / Salary to Directors: INR 6,00,000.00\n   - Rent paid to Director: Nil\n\nC. Outstanding Balances at Year-End:\n   - Receivable / (Payable): Nil`;
    } else {
        template = `Auditor verification completed. Schedules and disclosures reconciled with Trial Balance and statutory notes with zero discrepancy.`;
    }

    txtArea.value = template;
}

async function saveChecklistModal() {
    const refId = document.getElementById('ckModalRefId').value;
    const itemTitle = document.getElementById('ckModalItemTitle').value;
    const status = document.getElementById('ckModalStatus').value;
    const detailsText = document.getElementById('ckModalDetails').value;

    try {
        const res = await fetch('/api/disclosures/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                ref_id: refId,
                item_title: itemTitle,
                status: status,
                details_text: detailsText,
                user_name: 'CA Lead Auditor'
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            closeChecklistModal();
            loadReconciliation();
            showToast(`✅ Updated statutory disclosure ${refId}`, 'success');
        } else {
            alert('Error updating disclosure: ' + data.message);
        }
    } catch (err) {
        alert('Network error while saving disclosure: ' + err.message);
    }
}


// ═══════════════════════════════════════════════════════════════════════════
//  NOTE 1 ACCOUNTING POLICIES EDIT MODAL LOGIC
// ═══════════════════════════════════════════════════════════════════════════

let _currentNote1Sections = [];

async function openNote1Modal() {
    const modal = document.getElementById('note1EditModal');
    const container = document.getElementById('note1SectionsContainer');
    container.innerHTML = '<p class="text-muted text-center" style="padding:20px;">Loading Note 1 Accounting Policies...</p>';
    modal.style.display = 'flex';

    try {
        const res = await fetch('/api/notes/custom?note_no=1');
        const data = await res.json();
        if (data.status === 'success') {
            _currentNote1Sections = data.sections || [];
            renderNote1SectionInputs();
        } else {
            container.innerHTML = `<div class="exception-item severity-high">Failed to load Note 1: ${data.message}</div>`;
        }
    } catch (err) {
        container.innerHTML = `<div class="exception-item severity-high">Error fetching Note 1 policies: ${err.message}</div>`;
    }
}

function closeNote1Modal() {
    document.getElementById('note1EditModal').style.display = 'none';
}

function renderNote1SectionInputs() {
    const container = document.getElementById('note1SectionsContainer');
    if (!_currentNote1Sections || _currentNote1Sections.length === 0) {
        container.innerHTML = '<p class="text-muted">No policy sections available.</p>';
        return;
    }

    let html = '';
    _currentNote1Sections.forEach((sec, idx) => {
        html += `
        <div class="policy-card-item" style="border:1px solid #e2e8f0; border-radius:8px; padding:14px 18px; background:#f8fafc;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <input type="text" class="form-control" style="font-weight:700; color:#1e3a8a; font-size:14px; width:75%; padding:6px 10px; border-radius:6px; border:1px solid #cbd5e1;" value="${escHtml(sec.heading || `1.${idx+1} Policy Section`)}" id="note1Head_${idx}" onchange="_currentNote1Sections[${idx}].heading = this.value">
                <button type="button" style="background:#fee2e2; color:#ef4444; border:none; padding:4px 8px; border-radius:6px; font-size:12px; cursor:pointer; font-weight:600;" onclick="removeNote1Section(${idx})">🗑️ Delete</button>
            </div>
            <textarea class="form-control" rows="4" style="width:100%; padding:10px; border-radius:6px; border:1px solid #cbd5e1; font-size:13px; line-height:1.5; resize:vertical;" id="note1Content_${idx}" onchange="_currentNote1Sections[${idx}].content = this.value">${escHtml(sec.content || '')}</textarea>
        </div>`;
    });

    container.innerHTML = html;
}

function addNote1CustomSection() {
    const newIdx = (_currentNote1Sections.length + 1);
    _currentNote1Sections.push({
        heading: `1.${newIdx}  Custom Accounting Policy`,
        type: 'text',
        content: 'Enter company-specific statutory accounting policy clause here...'
    });
    renderNote1SectionInputs();
    const container = document.getElementById('note1SectionsContainer');
    container.scrollTop = container.scrollHeight;
}

function removeNote1Section(index) {
    if (confirm('Are you sure you want to remove this accounting policy section?')) {
        _currentNote1Sections.splice(index, 1);
        renderNote1SectionInputs();
    }
}

async function saveNote1Modal() {
    // Read values from inputs
    _currentNote1Sections.forEach((sec, idx) => {
        const headEl = document.getElementById(`note1Head_${idx}`);
        const contentEl = document.getElementById(`note1Content_${idx}`);
        if (headEl) sec.heading = headEl.value;
        if (contentEl) sec.content = contentEl.value;
    });

    try {
        const res = await fetch('/api/notes/custom/update', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: '1',
                sections: _currentNote1Sections,
                user_name: 'CA Lead Auditor'
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            closeNote1Modal();
            loadNotes();
            showToast('✅ Note 1 Accounting Policies updated successfully!', 'success');
        } else {
            alert('Error updating Note 1: ' + data.message);
        }
    } catch (err) {
        alert('Network error while saving Note 1 policies: ' + err.message);
    }
}

async function resetNote1ToDefault() {
    if (!confirm('Are you sure you want to reset Note 1 to standard ICAI Schedule III template policies? Any custom edits will be reverted.')) {
        return;
    }

    try {
        const res = await fetch('/api/notes/custom/reset', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                note_no: '1',
                user_name: 'CA Lead Auditor'
            })
        });

        const data = await res.json();
        if (data.status === 'success') {
            closeNote1Modal();
            loadNotes();
            showToast('↺ Note 1 reset to standard template', 'info');
        } else {
            alert('Error resetting Note 1: ' + data.message);
        }
    } catch (err) {
        alert('Network error while resetting Note 1: ' + err.message);
    }
}

