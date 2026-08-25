// SSA Kartavya - Clients Master Module

let activeSubTab = 'manage'; // manage, add, upload, update, archived
let clientTableView = true; // Table view vs Tile/Grid view
let selectedClientIdsForBulk = []; // tracking checkbox selections
let selectedColumns = ['code', 'name', 'entityType', 'pan', 'status', 'pic', 'mic']; // default visible columns
let activeClientProfileId = null; // tracking profile drawer state
let onboardingWizardStep = 1; // 1-4 onboarding steps

// Initializer
window.initClientsModule = function() {
  renderClientsSubTabs();
  navigateSubTab(activeSubTab);
};

// SUB TABS NAVIGATION
function renderClientsSubTabs() {
  const container = document.getElementById('clients-sub-tabs-bar');
  if (!container) return;

  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
  
  let buttons = `<button class="sub-tab-btn ${activeSubTab === 'manage' ? 'active' : ''}" onclick="navigateSubTab('manage')">Manage Clients</button>`;
  
  if (user.role === 'super_admin') {
    buttons += `
      <button class="sub-tab-btn ${activeSubTab === 'add' ? 'active' : ''}" onclick="navigateSubTab('add')">Add New Client</button>
      <button class="sub-tab-btn ${activeSubTab === 'upload' ? 'active' : ''}" onclick="navigateSubTab('upload')">Bulk Upload</button>
      <button class="sub-tab-btn ${activeSubTab === 'update' ? 'active' : ''}" onclick="navigateSubTab('update')">Bulk Update</button>
      <button class="sub-tab-btn ${activeSubTab === 'archived' ? 'active' : ''}" onclick="navigateSubTab('archived')">Archived Clients</button>
    `;
  } else if (user.role === 'manager') {
    buttons += `
      <button class="sub-tab-btn ${activeSubTab === 'archived' ? 'active' : ''}" onclick="navigateSubTab('archived')">Archived Clients</button>
    `;
  }
  
  container.innerHTML = `<div class="sub-tabs">${buttons}</div>`;
}

window.navigateSubTab = function(tabName) {
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };

  let targetTab = tabName;
  if (user.role === 'staff' && tabName !== 'manage') {
    targetTab = 'manage';
  } else if (user.role === 'manager' && ['add', 'upload', 'update'].includes(tabName)) {
    targetTab = 'manage';
  }

  activeSubTab = targetTab;
  renderClientsSubTabs();
  
  // Hide all sub-panels
  document.querySelectorAll('.client-sub-panel').forEach(el => el.style.display = 'none');
  
  // Show active sub-panel
  const activePanel = document.getElementById(`client-panel-${targetTab}`);
  if (activePanel) activePanel.style.display = 'block';

  // Specific panel loaders
  if (targetTab === 'manage') {
    renderClientDirectory();
    populateDirectoryFilters();
  } else if (targetTab === 'add') {
    initOnboardingWizard();
  } else if (targetTab === 'upload') {
    initBulkUpload();
  } else if (targetTab === 'update') {
    renderBulkUpdateDirectory();
  } else if (targetTab === 'archived') {
    renderArchivedClients();
  }
};

// DIRECTORY VIEW FILTERS & RE-RENDERS
let searchVal = '';
let filterPartner = '';
let filterManager = '';
let filterEntity = '';
let filterStatus = 'All';

function populateDirectoryFilters() {
  const partnerSelect = document.getElementById('filter-pic');
  const managerSelect = document.getElementById('filter-mic');
  
  if (!partnerSelect || !managerSelect) return;

  // Partners (super_admin)
  const partners = window.State.team.filter(t => t.role === 'super_admin' && t.status === 'Active');
  partnerSelect.innerHTML = `<option value="">All Partners</option>` + partners.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

  // Managers
  const managers = window.State.team.filter(t => t.role === 'manager' && t.status === 'Active');
  managerSelect.innerHTML = `<option value="">All Managers</option>` + managers.map(m => `<option value="${m.id}">${m.name}</option>`).join('');

  // Re-apply current state values
  document.getElementById('client-search').value = searchVal;
  partnerSelect.value = filterPartner;
  managerSelect.value = filterManager;
  document.getElementById('filter-entity').value = filterEntity;
  document.getElementById('filter-status').value = filterStatus;
}

window.setClientDirectoryFilters = function(search = '', partner = '', manager = '', status = 'All') {
  searchVal = search;
  filterPartner = partner;
  filterManager = manager;
  filterStatus = status;
  
  // If view is loaded, update inputs
  const sInput = document.getElementById('client-search');
  if (sInput) sInput.value = search;
  const pInput = document.getElementById('filter-pic');
  if (pInput) pInput.value = partner;
  const mInput = document.getElementById('filter-mic');
  if (mInput) mInput.value = manager;
  const statInput = document.getElementById('filter-status');
  if (statInput) statInput.value = status;
  
  renderClientDirectory();
};

window.onFilterChange = function() {
  searchVal = document.getElementById('client-search').value;
  filterPartner = document.getElementById('filter-pic').value;
  filterManager = document.getElementById('filter-mic').value;
  filterEntity = document.getElementById('filter-entity').value;
  filterStatus = document.getElementById('filter-status').value;
  
  renderClientDirectory();
};

window.toggleClientViewMode = function(isTable) {
  clientTableView = isTable;
  renderClientDirectory();
};

window.toggleColumnPicker = function() {
  const panel = document.getElementById('column-picker-dropdown');
  panel.classList.toggle('active');
};

window.onColumnToggle = function(checkbox) {
  const col = checkbox.value;
  if (checkbox.checked) {
    if (!selectedColumns.includes(col)) selectedColumns.push(col);
  } else {
    selectedColumns = selectedColumns.filter(c => c !== col);
  }
  renderClientDirectory();
};

// MAIN CLIENT DIRECTORY RENDERER
window.renderClientDirectory = function() {
  const container = document.getElementById('client-directory-content');
  if (!container) return;

  const allActiveClients = window.State.clients.filter(c => !c.isArchived);
  const activeCount = allActiveClients.filter(c => c.status === 'Active').length;
  const prospectCount = allActiveClients.filter(c => c.status === 'Prospect').length;
  const onHoldCount = allActiveClients.filter(c => c.status === 'On Hold').length;
  const mappedServices = (window.State.engagements || []).filter(e => allActiveClients.some(c => c.id === e.clientId)).length;

  // Filter clients list
  let clients = window.State.clients.filter(c => !c.isArchived);

  // Apply search
  if (searchVal.trim() !== '') {
    const q = searchVal.toLowerCase();
    clients = clients.filter(c => 
      c.name.toLowerCase().includes(q) || 
      c.code.toLowerCase().includes(q) || 
      (c.tradeName && c.tradeName.toLowerCase().includes(q)) || 
      c.pan.toLowerCase().includes(q)
    );
  }

  // Apply selectors
  if (filterPartner) clients = clients.filter(c => c.picUserId === filterPartner);
  if (filterManager) clients = clients.filter(c => c.micUserId === filterManager);
  if (filterEntity) clients = clients.filter(c => c.entityType === filterEntity);
  if (filterStatus !== 'All') clients = clients.filter(c => c.status === filterStatus);

  container.innerHTML = `
    <section class="client-directory-hero">
      <div class="client-directory-copy"><span class="client-directory-eyebrow">Client relationship workspace</span><h3>See every client, ownership detail, and active service scope in one place.</h3><p>Open a profile to manage engagements, people, contacts, and client-specific resource budgets.</p></div>
      <div class="client-directory-metrics">
        <div><span>Client base</span><strong>${allActiveClients.length}</strong></div>
        <div><span>Active</span><strong>${activeCount}</strong></div>
        <div><span>Prospects</span><strong>${prospectCount}</strong></div>
        <div><span>Service mappings</span><strong>${mappedServices}</strong></div>
      </div>
    </section>
    <div class="client-directory-results-head"><div><span class="client-directory-eyebrow">Directory</span><h3>${clients.length} client${clients.length === 1 ? '' : 's'} in view</h3></div><span class="client-filter-note">${onHoldCount ? `${onHoldCount} on hold firm-wide` : 'All client records are current'}</span></div>
    <div id="client-directory-results"></div>`;
  const resultsContainer = document.getElementById('client-directory-results');
  if (!clients.length) {
    resultsContainer.innerHTML = `<div class="client-directory-empty"><span>⌕</span><h4>No clients match these filters</h4><p>Try clearing a filter or search for another client identifier.</p></div>`;
    return;
  }

  if (clientTableView) {
    renderDirectoryTable(resultsContainer, clients);
  } else {
    renderDirectoryTiles(resultsContainer, clients);
  }
};

function renderDirectoryTable(container, clients) {
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  const headersMap = {
    code: 'Client Code', name: 'Legal Name', entityType: 'Entity Type',
    pan: 'PAN ID', status: 'Status', pic: 'Partner In Charge', mic: 'Manager In Charge'
  };

  let headerHTML = '<tr>';
  selectedColumns.forEach(col => {
    headerHTML += `<th>${headersMap[col] || col}</th>`;
  });
  headerHTML += '<th style="text-align: right;">Actions</th></tr>';

  let bodyHTML = '';
  clients.forEach(c => {
    const picObj = window.State.team.find(t => t.id === c.picUserId);
    const micObj = window.State.team.find(t => t.id === c.micUserId);
    
    const engagementCount = (window.State.engagements || []).filter(e => e.clientId === c.id).length;
    let row = '<tr class="client-directory-row">';
    selectedColumns.forEach(col => {
      if (col === 'code') {
        row += `<td><code>${c.code}</code></td>`;
      } else if (col === 'name') {
        row += `<td><button type="button" onclick="openClientProfile('${c.id}')" class="client-directory-name"><span class="client-name-mark">${c.name.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span><span><strong>${c.name}</strong><small>${engagementCount} active service mapping${engagementCount === 1 ? '' : 's'}</small></span></button></td>`;
      } else if (col === 'entityType') {
        row += `<td>${c.entityType}</td>`;
      } else if (col === 'pan') {
        row += `<td><code>${c.pan}</code></td>`;
      } else if (col === 'status') {
        let bClass = 'badge-active';
        if (c.status === 'Prospect') bClass = 'badge-prospect';
        if (c.status === 'On Hold') bClass = 'badge-hold';
        if (c.status === 'Inactive') bClass = 'badge-inactive';
        row += `<td><span class="badge ${bClass}">${c.status}</span></td>`;
      } else if (col === 'pic') {
        row += `<td><span class="client-owner-chip"><i class="client-owner-dot partner"></i>${picObj ? picObj.name : 'Unassigned'}</span></td>`;
      } else if (col === 'mic') {
        row += `<td><span class="client-owner-chip"><i class="client-owner-dot manager"></i>${micObj ? micObj.name : 'Unassigned'}</span></td>`;
      }
    });

    row += `
      <td style="text-align: right;">
        <button onclick="openClientProfile('${c.id}')" class="btn btn-secondary client-table-open">Open</button>
        ${(user?.role === 'super_admin' || user?.role === 'manager') ? `<button onclick="softArchiveClient('${c.id}')" class="client-table-archive" title="Archive client">⌫</button>` : ''}
      </td>
    </tr>`;
    bodyHTML += row;
  });

  container.innerHTML = `
    <div class="table-responsive">
      <table class="custom-table">
        <thead>${headerHTML}</thead>
        <tbody>${bodyHTML}</tbody>
      </table>
    </div>
  `;
}

function renderDirectoryTiles(container, clients) {
  let tilesHTML = '<div class="tile-grid">';
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  clients.forEach(c => {
    const picObj = window.State.team.find(t => t.id === c.picUserId);
    const micObj = window.State.team.find(t => t.id === c.micUserId);
    let bClass = 'badge-active';
    if (c.status === 'Prospect') bClass = 'badge-prospect';
    if (c.status === 'On Hold') bClass = 'badge-hold';
    if (c.status === 'Inactive') bClass = 'badge-inactive';

    tilesHTML += `
      <article class="client-tile client-status-${c.status.toLowerCase().replace(/\s+/g, '-')}">
        <div class="client-tile-header">
          <div class="client-tile-identity">
            <span class="client-tile-monogram">${c.name.split(/\s+/).slice(0, 2).map(part => part[0]).join('').toUpperCase()}</span>
            <div><div onclick="openClientProfile('${c.id}')" class="client-tile-title">${c.name}</div><div class="client-tile-meta">${c.entityType} · <code>${c.code}</code></div></div>
          </div>
          <span class="badge ${bClass}">${c.status}</span>
        </div>
        <div class="client-tile-scope"><span>Service scope</span><strong>${(window.State.engagements || []).filter(e => e.clientId === c.id).length} mapped service${(window.State.engagements || []).filter(e => e.clientId === c.id).length === 1 ? '' : 's'}</strong></div>
        <div class="client-tile-details">
          <div><span>PAN</span><code>${c.pan}</code></div>
          <div><span>Group</span><strong>${c.groupName || 'Independent'}</strong></div>
          <div><span>Partner in charge</span><strong>${picObj ? picObj.name : 'Unassigned'}</strong></div>
          <div><span>Manager in charge</span><strong>${micObj ? micObj.name : 'Unassigned'}</strong></div>
        </div>
        <div class="client-tile-actions">
          <button onclick="openClientProfile('${c.id}')" class="btn btn-primary">Open profile <span>→</span></button>
          ${(user?.role === 'super_admin' || user?.role === 'manager') ? `<button onclick="softArchiveClient('${c.id}')" class="client-archive-button" title="Archive client">⌫</button>` : ''}
        </div>
      </article>
    `;
  });
  tilesHTML += '</div>';
  container.innerHTML = tilesHTML;
}

window.softArchiveClient = function(id) {
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!user || (user.role !== 'super_admin' && user.role !== 'manager')) {
    alert('Unauthorized: Only partners and managers can archive client records.');
    return;
  }
  const c = window.State.clients.find(x => x.id === id);
  if (c) {
    c.isArchived = true;
    window.saveState();
    renderClientDirectory();
    // Render report and metrics refresh
    if (window.renderDashboard) window.renderDashboard();
  }
};

window.exportClientMaster = function() {
  let csvContent = 'data:text/csv;charset=utf-8,Code,Legal Name,Trade Name,Group,Entity Type,PAN,Status,Onboarding Date,FY End\n';
  window.State.clients.forEach(c => {
    if (!c.isArchived) {
      csvContent += `"${c.code}","${c.name}","${c.tradeName || ''}","${c.groupName || ''}","${c.entityType}","${c.pan}","${c.status}","${c.onboardingDate}","${c.fyEnd}"\n`;
    }
  });
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", "SSA_Clients_Master.csv");
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// ONBOARDING 4-STEP WIZARD
window.initOnboardingWizard = function() {
  onboardingWizardStep = 1;
  renderWizardStepsUI();
  showWizardStepPanel();
  
  // Set default client code in Step 1
  document.getElementById('wiz-code').value = window.generateCode('SSA-CL', window.State.clients);
  
  // Clear other wizard form inputs
  document.getElementById('wiz-name').value = '';
  document.getElementById('wiz-trade').value = '';
  document.getElementById('wiz-group').value = '';
  document.getElementById('wiz-pan').value = '';
  document.getElementById('wiz-gstin-list').innerHTML = '';
  
  // Render dynamic CA services rows
  renderWizardServicesList();

  // Allotments
  const partnerSelect = document.getElementById('wiz-pic');
  const managerSelect = document.getElementById('wiz-mic');
  
  const partners = window.State.team.filter(t => t.role === 'super_admin' && t.status === 'Active');
  partnerSelect.innerHTML = `<option value="">Select Partner</option>` + partners.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

  const managers = window.State.team.filter(t => t.role === 'manager' && t.status === 'Active');
  managerSelect.innerHTML = `<option value="">Select Manager</option>` + managers.map(m => `<option value="${m.id}">${m.name}</option>`).join('');
};

function renderWizardServicesList() {
  const container = document.getElementById('wiz-services-container');
  if (!container) return;

  const services = window.State.services || [];

  container.innerHTML = `
    <div class="table-responsive" style="margin-top: 10px;">
      <table class="custom-table" style="font-size: 13px;">
        <thead>
          <tr>
            <th width="80">Subscribed</th>
            <th>Service Name</th>
            <th width="140">Frequency</th>
            <th width="180">Agreed Fee (per frequency)</th>
            <th>Description (Certificates Only)</th>
          </tr>
        </thead>
        <tbody>
          ${services.map(s => `
            <tr>
              <td style="text-align: center;">
                <input type="checkbox" id="wiz-srv-check-${s.id}" value="${s.id}" onchange="toggleWizardServiceRow('${s.id}')">
              </td>
              <td><strong>${s.name}</strong></td>
              <td>
                <select id="wiz-srv-freq-${s.id}" class="form-select" style="padding: 4px; font-size: 12px; height: auto;" disabled>
                  <option value="Annual" ${s.defaultFreq === 'Annual' ? 'selected' : ''}>Annual</option>
                  <option value="Quarterly" ${s.defaultFreq === 'Quarterly' ? 'selected' : ''}>Quarterly</option>
                  <option value="Monthly" ${s.defaultFreq === 'Monthly' ? 'selected' : ''}>Monthly</option>
                  <option value="One-time" ${s.defaultFreq === 'One-time' ? 'selected' : ''}>One-time</option>
                </select>
              </td>
              <td>
                <div style="display: flex; align-items: center; gap: 4px;">
                  ₹<input type="number" id="wiz-srv-fee-${s.id}" class="form-input" style="padding: 4px 8px; font-size: 12px; width: 100px; height: auto;" placeholder="Fee" disabled>
                </div>
              </td>
              <td>
                ${s.id === 'certificates' ? `
                  <input type="text" id="wiz-srv-desc-${s.id}" class="form-input" style="padding: 4px 8px; font-size: 12px; width: 100%; height: auto;" placeholder="e.g. Net Worth Certificate for Visa" disabled>
                ` : '<span style="color:var(--text-muted); font-size:11px;">N/A</span>'}
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

window.toggleWizardServiceRow = function(srvId) {
  const chk = document.getElementById(`wiz-srv-check-${srvId}`).checked;
  document.getElementById(`wiz-srv-freq-${srvId}`).disabled = !chk;
  document.getElementById(`wiz-srv-fee-${srvId}`).disabled = !chk;
  const descEl = document.getElementById(`wiz-srv-desc-${srvId}`);
  if (descEl) descEl.disabled = !chk;
};

function renderWizardStepsUI() {
  const steps = [
    { n: 1, l: 'Basic Details' },
    { n: 2, l: 'Registrations' },
    { n: 3, l: 'Allotments' },
    { n: 4, l: 'Review' }
  ];

  const container = document.getElementById('wizard-steps-indicators');
  container.innerHTML = steps.map(s => {
    let cls = '';
    if (onboardingWizardStep === s.n) cls = 'active';
    else if (onboardingWizardStep > s.n) cls = 'completed';
    return `
      <div class="wizard-step ${cls}" onclick="goToWizardStep(${s.n})">
        <div class="wizard-step-circle">${s.n}</div>
        <div class="wizard-step-label">${s.l}</div>
      </div>
    `;
  }).join('');
}

function showWizardStepPanel() {
  document.querySelectorAll('.wizard-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`wiz-panel-${onboardingWizardStep}`).classList.add('active');
  
  // Manage visibility of Back / Next buttons
  document.getElementById('btn-wiz-prev').style.visibility = onboardingWizardStep === 1 ? 'hidden' : 'visible';
  const nextBtn = document.getElementById('btn-wiz-next');
  if (onboardingWizardStep === 4) {
    nextBtn.textContent = 'Activate Client';
    nextBtn.classList.remove('btn-primary');
    nextBtn.classList.add('btn-accent');
  } else {
    nextBtn.textContent = 'Continue';
    nextBtn.classList.remove('btn-accent');
    nextBtn.classList.add('btn-primary');
  }

  if (onboardingWizardStep === 4) {
    generateWizardReviewPanel();
  }
}

window.goToWizardStep = function(stepNum) {
  if (stepNum > onboardingWizardStep) {
    // Validate current step before proceeding
    if (!validateWizardStep(onboardingWizardStep)) return;
  }
  onboardingWizardStep = stepNum;
  renderWizardStepsUI();
  showWizardStepPanel();
};

window.wizardNext = function() {
  if (onboardingWizardStep === 4) {
    saveWizardOnboardedClient();
    return;
  }
  if (!validateWizardStep(onboardingWizardStep)) return;
  onboardingWizardStep++;
  renderWizardStepsUI();
  showWizardStepPanel();
};

window.wizardPrev = function() {
  if (onboardingWizardStep > 1) {
    onboardingWizardStep--;
    renderWizardStepsUI();
    showWizardStepPanel();
  }
};

function validateWizardStep(step) {
  if (step === 1) {
    const name = document.getElementById('wiz-name').value.trim();
    const pan = document.getElementById('wiz-pan').value.trim();
    if (!name) {
      alert("Legal name is required.");
      return false;
    }
    if (!pan || pan.length !== 10) {
      alert("PAN must be a valid 10-character code.");
      return false;
    }
  } else if (step === 3) {
    const pic = document.getElementById('wiz-pic').value;
    const mic = document.getElementById('wiz-mic').value;
    if (!pic) {
      alert("Please select a Partner-in-charge.");
      return false;
    }
    if (!mic) {
      alert("Please select a Manager-in-charge.");
      return false;
    }
  }
  return true;
}

// GSTIN Handler on Step 2
window.addNewGSTINInputRow = function() {
  const container = document.getElementById('wiz-gstin-list');
  const count = container.children.length;
  if (count >= 30) {
    alert("Maximum of 30 GSTIN registrations allowed per client.");
    return;
  }
  
  const gstinInputId = `wiz-gstin-${count}`;
  const statusSelectId = `wiz-gstin-status-${count}`;
  const resolveStateId = `wiz-gstin-state-${count}`;

  const row = document.createElement('div');
  row.className = 'form-grid';
  row.style.marginBottom = '12px';
  row.innerHTML = `
    <div class="form-group">
      <label class="form-label">GSTIN (15 characters)</label>
      <input type="text" id="${gstinInputId}" oninput="validateGSTINInputRow(${count})" class="form-input" placeholder="e.g. 27AABCA1234F1Z0" style="text-transform: uppercase;">
    </div>
    <div class="form-group">
      <label class="form-label">Status & Resolved State</label>
      <div style="display: flex; gap: 8px; align-items: center;">
        <select id="${statusSelectId}" class="form-select" style="flex: 1;">
          <option value="Active">Active</option>
          <option value="Suspended">Suspended</option>
        </select>
        <span id="${resolveStateId}" style="font-size: 12px; font-weight: bold; color: var(--bronze); width: 120px;">Unresolved</span>
      </div>
    </div>
  `;
  container.appendChild(row);
};

window.validateGSTINInputRow = function(index) {
  const gInput = document.getElementById(`wiz-gstin-${index}`);
  const sLabel = document.getElementById(`wiz-gstin-state-${index}`);
  const val = gInput.value.trim().toUpperCase();
  const panVal = document.getElementById('wiz-pan').value.trim().toUpperCase();

  if (val.length >= 2) {
    sLabel.textContent = window.resolveGSTINState(val);
  } else {
    sLabel.textContent = 'Unresolved';
  }

  // Format checks (Indian GSTIN regex: 15 chars)
  const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
  if (val.length === 15) {
    const isFormatOk = gstRegex.test(val);
    const panPart = val.substring(2, 12);
    const matchesPAN = panPart === panVal;

    if (!isFormatOk) {
      gInput.style.borderColor = '#e74c3c';
    } else if (!matchesPAN) {
      gInput.style.borderColor = '#e67e22';
      sLabel.textContent += ' (PAN Mismatch!)';
    } else {
      gInput.style.borderColor = '#2ecc71';
    }
  } else {
    gInput.style.borderColor = 'var(--border-color)';
  }
};

// REVIEW SCREEN (STEP 4)
function generateWizardReviewPanel() {
  const reviewContainer = document.getElementById('wiz-review-warnings');
  const name = document.getElementById('wiz-name').value.trim();
  const pan = document.getElementById('wiz-pan').value.trim().toUpperCase();
  const picVal = document.getElementById('wiz-pic').value;
  const micVal = document.getElementById('wiz-mic').value;

  let alertsHtml = '';

  // 1. Check duplicate PAN
  const dupPan = window.State.clients.some(c => c.pan.toUpperCase() === pan && !c.isArchived);
  if (dupPan) {
    alertsHtml += `
      <div class="validation-banner validation-banner-danger">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/></svg>
        <strong>PAN Duplicate Check Failed:</strong> Client with PAN <strong>${pan}</strong> already exists in State registry.
      </div>
    `;
  }

  // 2. Levenshtein check for similar client names
  const matchSimilarityThreshold = 0.8;
  const similarClients = [];
  window.State.clients.forEach(c => {
    if (c.isArchived) return;
    const similarity = window.levenshteinSimilarity(name, c.name);
    if (similarity >= matchSimilarityThreshold) {
      similarClients.push({ name: c.name, score: Math.round(similarity * 100) });
    }
  });

  if (similarClients.length > 0) {
    const listNames = similarClients.map(c => `"${c.name}" (${c.score}% match)`).join(', ');
    alertsHtml += `
      <div class="validation-banner validation-banner-warning">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01"/></svg>
        <strong>Levenshtein Group Similarity Warning:</strong> Highly similar names found in repository: ${listNames}
      </div>
    `;
  }

  // 3. Validation GSTIN format and state codes checks
  const gstinListContainer = document.getElementById('wiz-gstin-list');
  let invalidGstinCount = 0;
  let panMismatchCount = 0;
  
  for (let i = 0; i < gstinListContainer.children.length; i++) {
    const gInput = document.getElementById(`wiz-gstin-${i}`);
    if (gInput) {
      const gVal = gInput.value.trim().toUpperCase();
      const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
      
      if (gVal.length !== 15 || !gstRegex.test(gVal)) {
        invalidGstinCount++;
      } else {
        const panPart = gVal.substring(2, 12);
        if (panPart !== pan) {
          panMismatchCount++;
        }
      }
    }
  }

  if (invalidGstinCount > 0) {
    alertsHtml += `
      <div class="validation-banner validation-banner-danger">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
        <strong>Registration Format Errors:</strong> You have <strong>${invalidGstinCount}</strong> GSTIN entries with invalid structures.
      </div>
    `;
  }

  if (panMismatchCount > 0) {
    alertsHtml += `
      <div class="validation-banner validation-banner-warning">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <strong>PAN-GSTIN Mismatch Alert:</strong> ${panMismatchCount} GSTIN entries do not embed the client's PAN "${pan}" (characters 3-12).
      </div>
    `;
  }

  // 4. Missing Partner or Manager check
  if (!picVal || !micVal) {
    alertsHtml += `
      <div class="validation-banner validation-banner-danger">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
        <strong>Partner/Manager Allotment Missing:</strong> You must designate PIC and MIC assignments before database persistence.
      </div>
    `;
  }

  if (alertsHtml === '') {
    alertsHtml = `
      <div class="validation-banner validation-banner-success">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><path d="M22 4L12 14.01l-3-3"/></svg>
        <strong>Ready for Activation:</strong> All system checklists valid. Legal compliance structure verified.
      </div>
    `;
  }

  reviewContainer.innerHTML = alertsHtml;
}

function saveWizardOnboardedClient() {
  const code = document.getElementById('wiz-code').value.trim();
  const name = document.getElementById('wiz-name').value.trim();
  const trade = document.getElementById('wiz-trade').value.trim();
  const group = document.getElementById('wiz-group').value.trim();
  const entity = document.getElementById('wiz-entity').value;
  const pan = document.getElementById('wiz-pan').value.trim().toUpperCase();
  const pic = document.getElementById('wiz-pic').value;
  const mic = document.getElementById('wiz-mic').value;
  const onboardingDate = window.toLocalISODate();

  // Create Client Object
  const newClientId = `c_${Date.now()}`;
  const clientObj = {
    id: newClientId, code, name, tradeName: trade, groupName: group,
    entityType: entity, pan, status: 'Active', picUserId: pic, micUserId: mic,
    onboardingDate, fyEnd: 'March 31', referenceName: 'Onboarding Wizard',
    tan: '', cin: '', llpin: '', incorporationDate: '', msmeRegistrationStatus: 'Not Registered',
    industry: 'General', businessActivity: 'Commercial Services', listedExchange: 'Unlisted',
    previousAuditor: '', registeredOfficeAddress: '', communicationAddress: '', billingAddress: '',
    isArchived: false
  };

  // Add GST Registrations
  const gstinListContainer = document.getElementById('wiz-gstin-list');
  const gstObjs = [];
  for (let i = 0; i < gstinListContainer.children.length; i++) {
    const gInput = document.getElementById(`wiz-gstin-${i}`);
    const gStatus = document.getElementById(`wiz-gstin-status-${i}`);
    if (gInput && gInput.value.trim()) {
      const gVal = gInput.value.trim().toUpperCase();
      gstObjs.push({
        id: `g_${Date.now()}_${i}`,
        clientId: newClientId,
        gstin: gVal,
        state: window.resolveGSTINState(gVal),
        status: gStatus.value
      });
    }
  }

  // Parse and save multiple modular service selections
  const servicesList = window.State.services.map(s => s.id);
  servicesList.forEach(sid => {
    const chk = document.getElementById(`wiz-srv-check-${sid}`);
    if (chk && chk.checked) {
      const freq = document.getElementById(`wiz-srv-freq-${sid}`).value;
      const fee = parseFloat(document.getElementById(`wiz-srv-fee-${sid}`).value);
      const descEl = document.getElementById(`wiz-srv-desc-${sid}`);
      const description = descEl ? descEl.value.trim() : '';

      if (!isNaN(fee) && fee >= 0) {
        window.State.engagements.push({
          id: `e_${sid}_${Date.now()}`,
          clientId: newClientId,
          serviceId: sid,
          description: description,
          picUserId: pic,
          micUserId: mic,
          teamUserIds: [],
          agreedFee: fee,
          frequency: freq
        });
      }
    }
  });

  // Commit
  window.State.clients.push(clientObj);
  window.State.gstRegistrations.push(...gstObjs);
  
  // Log Audit Log
  console.log(`Audited: Added client ${name} with code ${code}`);
  
  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  
  alert(`Client successfully onboarded under code: ${code}`);
  window.navigateSubTab('manage');
}

// BULK UPLOAD MODULE
function initBulkUpload() {
  const dropzone = document.getElementById('csv-dropzone');
  const fileInput = document.getElementById('csv-file-input');

  dropzone.onclick = () => fileInput.click();

  // drag and drop handlers
  dropzone.ondragover = (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--module-accent)';
  };
  dropzone.ondragleave = () => {
    dropzone.style.borderColor = 'var(--border-color)';
  };
  dropzone.ondrop = (e) => {
    e.preventDefault();
    dropzone.style.borderColor = 'var(--border-color)';
    if (e.dataTransfer.files.length > 0) {
      handleUploadedFile(e.dataTransfer.files[0]);
    }
  };

  fileInput.onchange = () => {
    if (fileInput.files.length > 0) {
      handleUploadedFile(fileInput.files[0]);
    }
  };
}

function handleUploadedFile(file) {
  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    parseBulkCSV(text);
  };
  reader.readAsText(file);
}

// ─── COLUMN DEFINITIONS (mirrors individual onboarding fields) ────────────────
const CSV_COLUMNS = [
  { key: 'name',              label: 'Legal Name *',           required: true,  tip: 'Full legal name as per PAN / Incorporation Certificate' },
  { key: 'tradeName',         label: 'Trade / Brand Name',     required: false, tip: 'Commercial name if different from legal name' },
  { key: 'groupName',         label: 'Group / Promoter Name',  required: false, tip: 'Common business group or promoter family name' },
  { key: 'entityType',        label: 'Entity Type *',          required: true,  tip: 'Private Limited | LLP | Partnership Firm | HUF | Individual | Public Limited | Trust | AOP | BOI | Society' },
  { key: 'pan',               label: 'PAN *',                  required: true,  tip: 'Exactly 10 characters, e.g. AABCA1234F' },
  { key: 'tan',               label: 'TAN',                    required: false, tip: '10-character TAN if applicable, e.g. MUMA12345B' },
  { key: 'cin',               label: 'CIN / LLPIN',            required: false, tip: 'Company/LLP identification number if registered' },
  { key: 'incorporationDate', label: 'Incorporation Date',     required: false, tip: 'YYYY-MM-DD format, e.g. 2022-04-01' },
  { key: 'fyEnd',             label: 'FY End',                 required: false, tip: 'March 31 (default) or June 30 / Sept 30 / Dec 31' },
  { key: 'industry',          label: 'Industry',               required: false, tip: 'e.g. Technology, Real Estate, FMCG, Manufacturing' },
  { key: 'businessActivity',  label: 'Business Activity',      required: false, tip: 'Short description of primary business operations' },
  { key: 'msmeStatus',        label: 'MSME Registration',      required: false, tip: 'Registered | Not Registered | Not Applicable' },
  { key: 'listedExchange',    label: 'Listed Exchange',        required: false, tip: 'BSE | NSE | Unlisted (default: Unlisted)' },
  { key: 'picCode',           label: 'PIC Partner Code *',     required: true,  tip: 'Employee code of the Partner-in-Charge, e.g. SSA-EMP-00001' },
  { key: 'micCode',           label: 'MIC Manager Code *',     required: true,  tip: 'Employee code of the Manager-in-Charge, e.g. SSA-EMP-00003' },
  { key: 'referenceName',     label: 'Reference / Source',     required: false, tip: 'e.g. Bank Referral, Direct Client, Existing Group' },
  { key: 'status',            label: 'Status',                 required: false, tip: 'Active | Prospect | On Hold | Inactive (default: Active)' },
  { key: 'additionalInfo',    label: 'Additional Notes',       required: false, tip: 'Any other relevant remarks for this client' }
];

function parseBulkCSV(text) {
  // Support both comma-delimited and RFC 4180 quoted fields
  function parseCSVRow(row) {
    const result = [];
    let current = '';
    let inQuotes = false;
    for (let i = 0; i < row.length; i++) {
      const ch = row[i];
      if (ch === '"') {
        if (inQuotes && row[i + 1] === '"') { current += '"'; i++; }
        else { inQuotes = !inQuotes; }
      } else if (ch === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += ch;
      }
    }
    result.push(current.trim());
    return result;
  }

  const lines = text.split(/\r?\n/).filter(l => l.trim().length > 0);
  if (lines.length <= 1) {
    alert("Empty or invalid CSV file. Please use the SSA Kartavya template.");
    return;
  }

  const headerRow = parseCSVRow(lines[0]).map(h => h.toLowerCase().replace(/[^a-z\s]/g, '').trim());

  // Map CSV column positions to our schema keys
  const colIndex = {};
  CSV_COLUMNS.forEach(col => {
    const labelNorm = col.label.replace(' *', '').toLowerCase().replace(/[^a-z\s]/g, '').trim();
    const foundIdx = headerRow.findIndex(h => h === labelNorm || h.includes(col.key.toLowerCase()));
    if (foundIdx !== -1) colIndex[col.key] = foundIdx;
  });

  // Build team lookup maps
  const teamByCode = {};
  window.State.team.forEach(t => { teamByCode[t.code] = t.id; });
  const defaultPIC = window.State.team.find(t => t.role === 'super_admin' && t.status === 'Active');
  const defaultMIC = window.State.team.find(t => t.role === 'manager' && t.status === 'Active');

  let validRowsCount = 0;
  let warningRowsCount = 0;
  let invalidRowsCount = 0;
  const errorLogs = [];
  const parsedClients = [];
  const previewRows = [];

  const VALID_ENTITY_TYPES = ['Private Limited', 'LLP', 'Partnership Firm', 'HUF', 'Individual', 'Public Limited', 'Trust', 'AOP', 'BOI', 'Society'];
  const VALID_STATUSES = ['Active', 'Prospect', 'On Hold', 'Inactive'];

  for (let i = 1; i < lines.length; i++) {
    const cells = parseCSVRow(lines[i]);
    const get = (key) => (colIndex[key] !== undefined ? (cells[colIndex[key]] || '').trim() : '');

    const rowErrors = [];
    const rowWarnings = [];

    // ── Required fields ────────────────────────────────
    const name = get('name');
    if (!name) rowErrors.push('Missing Legal Name');

    const pan = get('pan').toUpperCase();
    if (!pan || pan.length !== 10) rowErrors.push(`Invalid PAN "${pan}" – must be exactly 10 characters`);

    const entityType = get('entityType') || 'Private Limited';
    if (!VALID_ENTITY_TYPES.includes(entityType)) {
      rowWarnings.push(`Entity type "${entityType}" not in standard list – defaulting to Private Limited`);
    }

    // PIC / MIC resolution
    const picCodeRaw = get('picCode');
    const micCodeRaw = get('micCode');
    let picUserId = picCodeRaw ? (teamByCode[picCodeRaw] || null) : (defaultPIC ? defaultPIC.id : null);
    let micUserId = micCodeRaw ? (teamByCode[micCodeRaw] || null) : (defaultMIC ? defaultMIC.id : null);
    if (picCodeRaw && !picUserId) rowWarnings.push(`PIC code "${picCodeRaw}" not found – defaulted to first active partner`);
    if (micCodeRaw && !micUserId) rowWarnings.push(`MIC code "${micCodeRaw}" not found – defaulted to first active manager`);
    if (!picUserId) picUserId = defaultPIC ? defaultPIC.id : '';
    if (!micUserId) micUserId = defaultMIC ? defaultMIC.id : '';

    // ── Duplicate PAN check ────────────────────────────
    const isDupState = window.State.clients.some(c => c.pan.toUpperCase() === pan && !c.isArchived);
    const isDupFile  = parsedClients.some(c => c.pan === pan);
    if (isDupState) rowWarnings.push(`PAN "${pan}" already exists in client registry`);
    if (isDupFile)  rowWarnings.push(`PAN "${pan}" appears more than once in this CSV`);

    if (rowErrors.length > 0) {
      invalidRowsCount++;
      rowErrors.forEach(e => errorLogs.push(`Row ${i + 1} [${name || 'Unknown'}]: ❌ ${e}`));
      rowWarnings.forEach(w => errorLogs.push(`Row ${i + 1} [${name || 'Unknown'}]: ⚠️ ${w}`));
      continue;
    }

    if (rowWarnings.length > 0) {
      warningRowsCount++;
      rowWarnings.forEach(w => errorLogs.push(`Row ${i + 1} [${name}]: ⚠️ ${w}`));
    } else {
      validRowsCount++;
    }

    const status = VALID_STATUSES.includes(get('status')) ? get('status') : 'Active';
    const code = window.generateCode('SSA-CL', window.State.clients.concat(parsedClients));

    const clientObj = {
      id: `c_csv_${Date.now()}_${i}`,
      code,
      name,
      tradeName:          get('tradeName'),
      groupName:          get('groupName'),
      entityType:         VALID_ENTITY_TYPES.includes(entityType) ? entityType : 'Private Limited',
      pan,
      tan:                get('tan').toUpperCase(),
      cin:                get('cin'),
      llpin:              '',
      incorporationDate:  get('incorporationDate'),
      fyEnd:              get('fyEnd') || 'March 31',
      industry:           get('industry') || 'General',
      businessActivity:   get('businessActivity') || 'Commercial Services',
      msmeRegistrationStatus: get('msmeStatus') || 'Not Registered',
      listedExchange:     get('listedExchange') || 'Unlisted',
      picUserId,
      micUserId,
      referenceName:      get('referenceName') || 'CSV Import',
      additionalInfo:     get('additionalInfo'),
      status,
      previousAuditor:    '',
      registeredOfficeAddress: '',
      communicationAddress:    '',
      billingAddress:          '',
      onboardingDate: window.toLocalISODate(),
      isArchived: false
    };
    parsedClients.push(clientObj);

    const picName = window.State.team.find(t => t.id === picUserId)?.name || picUserId;
    const micName = window.State.team.find(t => t.id === micUserId)?.name || micUserId;
    previewRows.push({ code, name, entityType: clientObj.entityType, pan, status, picName, micName, hasWarning: rowWarnings.length > 0 });
  }

  // Render assessment panel
  const resultsContainer = document.getElementById('csv-results-summary');
  resultsContainer.style.display = 'block';

  const previewTableRows = previewRows.map(r => `
    <tr style="${r.hasWarning ? 'background: rgba(230,126,34,0.05);' : ''}">
      <td><code>${r.code}</code></td>
      <td><strong>${r.name}</strong></td>
      <td>${r.entityType}</td>
      <td><code>${r.pan}</code></td>
      <td>${r.picName}</td>
      <td>${r.micName}</td>
      <td><span class="badge ${r.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${r.status}</span></td>
    </tr>
  `).join('');

  resultsContainer.innerHTML = `
    <div style="margin-top: 20px;" class="card">
      <div class="card-header">
        <h3 class="card-title">CSV Upload Assessment</h3>
      </div>
      <div class="card-body">
        <div style="display: flex; gap: 24px; margin-bottom: 20px;">
          <div style="background: rgba(46,204,113,0.1); padding: 12px; border-radius: 8px; flex: 1; text-align: center;">
            <div style="font-size: 20px; font-weight: bold; color: #2ecc71;">${validRowsCount}</div>
            <div style="font-size: 12px; color: var(--text-muted);">Valid Rows</div>
          </div>
          <div style="background: rgba(230,126,34,0.1); padding: 12px; border-radius: 8px; flex: 1; text-align: center;">
            <div style="font-size: 20px; font-weight: bold; color: #e67e22;">${warningRowsCount}</div>
            <div style="font-size: 12px; color: var(--text-muted);">With Warnings</div>
          </div>
          <div style="background: rgba(231,76,60,0.1); padding: 12px; border-radius: 8px; flex: 1; text-align: center;">
            <div style="font-size: 20px; font-weight: bold; color: #e74c3c;">${invalidRowsCount}</div>
            <div style="font-size: 12px; color: var(--text-muted);">Invalid / Skipped</div>
          </div>
        </div>

        ${parsedClients.length > 0 ? `
          <h4 style="font-size: 13px; font-weight: bold; margin-bottom: 8px;">Preview of records to be imported (${parsedClients.length}):</h4>
          <div class="table-responsive" style="max-height: 300px; overflow-y: auto; margin-bottom: 16px;">
            <table class="custom-table" style="font-size: 12px;">
              <thead>
                <tr>
                  <th>Code</th><th>Legal Name</th><th>Entity</th><th>PAN</th><th>PIC</th><th>MIC</th><th>Status</th>
                </tr>
              </thead>
              <tbody>${previewTableRows}</tbody>
            </table>
          </div>
        ` : ''}

        ${errorLogs.length > 0 ? `
          <div style="margin-bottom: 16px;">
            <h4 style="font-size: 13px; font-weight: bold; margin-bottom: 8px;">Validation Logs:</h4>
            <div style="background: rgba(0,0,0,0.03); padding: 12px; border-radius: 8px; font-family: monospace; font-size: 11px; max-height: 150px; overflow-y: auto;">
              ${errorLogs.map(log => `<div style="margin-bottom: 3px;">${log}</div>`).join('')}
            </div>
            <a id="error-log-dl" style="font-size: 12px; color: var(--primary); text-decoration: underline; display: block; margin-top: 8px; cursor: pointer;">Download full validation log (.txt)</a>
          </div>
        ` : ''}

        <button onclick="commitCSVUploadClients(${JSON.stringify(parsedClients).replace(/"/g, '&quot;')})" class="btn btn-accent" style="width: 100%;" ${parsedClients.length === 0 ? 'disabled' : ''}>
          Import ${parsedClients.length} Client${parsedClients.length !== 1 ? 's' : ''} into Registry
        </button>
      </div>
    </div>
  `;

  if (errorLogs.length > 0) {
    document.getElementById('error-log-dl').onclick = () => {
      const blob = new Blob([errorLogs.join('\n')], { type: 'text/plain;charset=utf-8' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'SSA_Kartavya_CSV_Validation_Log.txt';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
    };
  }
}

window.commitCSVUploadClients = function(records) {
  if (!records || records.length === 0) return;
  window.State.clients.push(...records);
  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  alert(`${records.length} client${records.length !== 1 ? 's' : ''} successfully imported into SSA Kartavya registry.`);
  window.navigateSubTab('manage');
  document.getElementById('csv-results-summary').style.display = 'none';
};

window.downloadCSVTemplate = function() {
  const headerRow = CSV_COLUMNS.map(c => `"${c.label}"`).join(',');
  const tipRow    = CSV_COLUMNS.map(c => `"${c.tip}"`).join(',');
  const exampleRow = [
    '"Acme Corporation Private Limited"',
    '"Acme Corp"',
    '"Acme Group"',
    '"Private Limited"',
    '"AABCA1234F"',
    '"MUMA12345B"',
    '"U72200MH2022PTC123456"',
    '"2022-04-01"',
    '"March 31"',
    '"Technology"',
    '"Software development & hardware assembly"',
    '"Registered"',
    '"Unlisted"',
    '"SSA-EMP-00001"',
    '"SSA-EMP-00003"',
    '"Direct Client"',
    '"Active"',
    '"Tech Manufacturing sector"'
  ].join(',');

  const csvContent = [headerRow, tipRow, exampleRow].join('\r\n');
  const uri = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csvContent);
  const link = document.createElement('a');
  link.setAttribute('href', uri);
  link.setAttribute('download', 'SSA_Kartavya_Client_Import_Template.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

// BULK UPDATE MULTI-SELECT INTERFACES
window.renderBulkUpdateDirectory = function() {
  const container = document.getElementById('bulk-update-content');
  if (!container) return;

  const clients = window.State.clients.filter(c => !c.isArchived);

  // Render dropdown selectors in bulk reassign menu bar
  const picSel = document.getElementById('bulk-pic');
  const micSel = document.getElementById('bulk-mic');

  const partners = window.State.team.filter(t => t.role === 'super_admin' && t.status === 'Active');
  picSel.innerHTML = `<option value="">Reassign Partner</option>` + partners.map(p => `<option value="${p.id}">${p.name}</option>`).join('');

  const managers = window.State.team.filter(t => t.role === 'manager' && t.status === 'Active');
  micSel.innerHTML = `<option value="">Reassign Manager</option>` + managers.map(m => `<option value="${m.id}">${m.name}</option>`).join('');

  // Clear selections
  selectedClientIdsForBulk = [];
  updateBulkActionBarVisibility();

  container.innerHTML = `
    <div class="table-responsive">
      <table class="custom-table">
        <thead>
          <tr>
            <th width="40"><input type="checkbox" id="bulk-select-all" onclick="toggleSelectAllBulk(this)"></th>
            <th>Code</th>
            <th>Name</th>
            <th>Partner In Charge</th>
            <th>Manager In Charge</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          ${clients.map(c => {
            const pic = window.State.team.find(t => t.id === c.picUserId);
            const mic = window.State.team.find(t => t.id === c.micUserId);
            return `
              <tr>
                <td><input type="checkbox" class="bulk-row-check" value="${c.id}" onclick="toggleSelectClientBulk(this)"></td>
                <td><code>${c.code}</code></td>
                <td><strong>${c.name}</strong></td>
                <td>${pic ? pic.name : 'Unassigned'}</td>
                <td>${mic ? mic.name : 'Unassigned'}</td>
                <td><span class="badge ${c.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${c.status}</span></td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
};

window.toggleSelectClientBulk = function(chk) {
  const id = chk.value;
  if (chk.checked) {
    if (!selectedClientIdsForBulk.includes(id)) selectedClientIdsForBulk.push(id);
  } else {
    selectedClientIdsForBulk = selectedClientIdsForBulk.filter(x => x !== id);
  }
  updateBulkActionBarVisibility();
};

window.toggleSelectAllBulk = function(chk) {
  const checkboxes = document.querySelectorAll('.bulk-row-check');
  selectedClientIdsForBulk = [];
  checkboxes.forEach(c => {
    c.checked = chk.checked;
    if (chk.checked) {
      selectedClientIdsForBulk.push(c.value);
    }
  });
  updateBulkActionBarVisibility();
};

function updateBulkActionBarVisibility() {
  const bar = document.getElementById('bulk-action-menu-bar');
  if (selectedClientIdsForBulk.length > 0) {
    bar.classList.add('active');
    document.getElementById('bulk-selected-count').textContent = `${selectedClientIdsForBulk.length} clients selected`;
  } else {
    bar.classList.remove('active');
  }
}

window.applyBulkUpdates = function() {
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!user || (user.role !== 'super_admin' && user.role !== 'manager')) {
    alert('Unauthorized: Only partners and managers can bulk-update client records.');
    return;
  }
  const pic = document.getElementById('bulk-pic').value;
  const mic = document.getElementById('bulk-mic').value;
  const status = document.getElementById('bulk-status').value;
  const group = document.getElementById('bulk-group').value.trim();

  if (selectedClientIdsForBulk.length === 0) return;

  let updateCount = 0;
  window.State.clients.forEach(c => {
    if (selectedClientIdsForBulk.includes(c.id)) {
      if (pic) c.picUserId = pic;
      if (mic) c.micUserId = mic;
      if (status) c.status = status;
      if (group) c.groupName = group;
      updateCount++;
    }
  });

  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  alert(`Reassigned details for ${updateCount} clients successfully.`);
  window.navigateSubTab('manage');
};

// ARCHIVED CLIENTS VIEW
function renderArchivedClients() {
  const container = document.getElementById('archived-clients-content');
  if (!container) return;

  const archives = window.State.clients.filter(c => c.isArchived);

  if (archives.length === 0) {
    container.innerHTML = `<p style="text-align: center; color: var(--text-muted); padding: 40px;">No soft-archived client profiles found.</p>`;
    return;
  }

  container.innerHTML = `
    <div class="table-responsive">
      <table class="custom-table">
        <thead>
          <tr>
            <th>Client Code</th>
            <th>Legal Name</th>
            <th>PAN ID</th>
            <th>Onboarding Date</th>
            <th style="text-align: right;">Action</th>
          </tr>
        </thead>
        <tbody>
          ${archives.map(c => `
            <tr>
              <td><code>${c.code}</code></td>
              <td><strong>${c.name}</strong></td>
              <td><code>${c.pan}</code></td>
              <td>${c.onboardingDate}</td>
              <td style="text-align: right;">
                <button onclick="restoreSoftArchivedClient('${c.id}')" class="btn btn-primary" style="padding: 4px 8px; font-size: 11px;">Restore Profile</button>
              </td>
            </tr>
          `).join('')}
        </tbody>
      </table>
    </div>
  `;
}

window.restoreSoftArchivedClient = function(id) {
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!user || (user.role !== 'super_admin' && user.role !== 'manager')) {
    alert('Unauthorized: Only partners and managers can restore client records.');
    return;
  }
  const c = window.State.clients.find(x => x.id === id);
  if (c) {
    c.isArchived = false;
    window.saveState();
    if (window.renderDashboard) window.renderDashboard();
    window.navigateSubTab('manage');
  }
};

// CLIENT PROFILE DETAIL TAB DRAWER
window.openClientProfile = function(clientId) {
  activeClientProfileId = clientId;
  const drawer = document.getElementById('client-profile-drawer');
  drawer.classList.add('active');
  
  // Set default profile subtab
  switchProfileSubTab('overview');
};

window.closeClientProfile = function() {
  const drawer = document.getElementById('client-profile-drawer');
  drawer.classList.remove('active');
  activeClientProfileId = null;
};

window.switchProfileSubTab = function(tab) {
  // Update sub-tabs UI inside drawer
  document.querySelectorAll('.profile-sub-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.getAttribute('data-subtab') === tab) {
      btn.classList.add('active');
    }
  });

  const client = window.State.clients.find(c => c.id === activeClientProfileId);
  const container = document.getElementById('profile-drawer-body');
  if (!client) {
    container.innerHTML = `<p>Error loading client details.</p>`;
    return;
  }

  // Render header name
  document.getElementById('profile-client-name').textContent = client.name;
  document.getElementById('profile-client-code').textContent = client.code;

  if (tab === 'overview') {
    const pic = window.State.team.find(t => t.id === client.picUserId);
    const mic = window.State.team.find(t => t.id === client.micUserId);
    container.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div><strong>Group Name:</strong> ${client.groupName || 'Unassigned'}</div>
        <div><strong>Entity Type:</strong> ${client.entityType}</div>
        <div><strong>PAN Identifier:</strong> <code>${client.pan}</code></div>
        <div><strong>Tan Number:</strong> <code>${client.tan || 'N/A'}</code></div>
        <div><strong>CIN / LLPIN:</strong> <code>${client.cin || client.llpin || 'N/A'}</code></div>
        <div><strong>Onboarding Date:</strong> ${client.onboardingDate}</div>
        <div><strong>Financial Year End:</strong> ${client.fyEnd}</div>
        <div><strong>Partner in Charge:</strong> ${pic ? pic.name : 'Unassigned'}</div>
        <div><strong>Manager in Charge:</strong> ${mic ? mic.name : 'Unassigned'}</div>
        <div><strong>Registered Office:</strong><p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">${client.registeredOfficeAddress || 'Not Provided'}</p></div>
        <div><strong>Business Industry:</strong> ${client.industry || 'General'} (${client.businessActivity || 'General Services'})</div>
        <div><strong>Additional Notes:</strong><p style="font-size: 13px; color: var(--text-muted); margin-top: 4px;">${client.additionalInfo || 'No extra insights recorded'}</p></div>
      </div>
    `;
  } else if (tab === 'gst') {
    const gsts = window.State.gstRegistrations.filter(g => g.clientId === client.id);
    const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
    const canWrite = (user.role === 'super_admin');

    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h4 style="font-size: 14px; font-weight: 600;">GSTIN Entries (${gsts.length})</h4>
        ${canWrite ? '<button onclick="addGSTINFromProfileDrawer()" class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;">Add GSTIN</button>' : ''}
      </div>
      <div class="table-responsive">
        <table class="custom-table">
          <thead>
            <tr>
              <th>GSTIN</th>
              <th>State</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${gsts.map(g => `
              <tr>
                <td><code>${g.gstin}</code></td>
                <td>${g.state}</td>
                <td><span class="badge ${g.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${g.status}</span></td>
              </tr>
            `).join('')}
            ${gsts.length === 0 ? `<tr><td colspan="3" style="text-align: center; color: var(--text-muted);">No GSTIN entries found.</td></tr>` : ''}
          </tbody>
        </table>
      </div>
    `;
  } else if (tab === 'contacts') {
    const contacts = window.State.contacts.filter(c => c.clientId === client.id);
    const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
    const canWrite = (user.role === 'super_admin');

    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
        <h4 style="font-size: 14px; font-weight: 600;">Primary Contacts (${contacts.length})</h4>
        ${canWrite ? '<button onclick="addContactFromProfileDrawer()" class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;">Add Contact</button>' : ''}
      </div>
      <div class="table-responsive">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Designation</th>
              <th>Email</th>
              <th>Mobile</th>
            </tr>
          </thead>
          <tbody>
            ${contacts.map(c => `
              <tr>
                <td><strong>${c.name}</strong> ${c.isPrimary ? '<span style="font-size:9px; background:#b8924a; color:#fff; padding:2px 4px; border-radius:4px;">Primary</span>' : ''}</td>
                <td>${c.designation}</td>
                <td>${c.email}</td>
                <td>${c.mobile}</td>
              </tr>
            `).join('')}
            ${contacts.length === 0 ? `<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No contact personnel records logged.</td></tr>` : ''}
          </tbody>
        </table>
      </div>
    `;
  } else if (tab === 'services') {
    const engs = window.State.engagements.filter(e => e.clientId === client.id);
    const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
    const isPartner = (user.role === 'super_admin');
    const isStaff = (user.role === 'staff');

    container.innerHTML = `
      <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Engaged Subscriptions</h4>
      <div class="table-responsive">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Frequency</th>
              <th>Agreed Fee</th>
              ${isPartner ? '<th>Resource Budget</th>' : ''}
              ${isPartner ? '<th style="text-align: right;">Actions</th>' : ''}
            </tr>
          </thead>
          <tbody>
            ${engs.map(e => {
              let serviceName = window.SERVICES_MAP[e.serviceId] || e.serviceId;
              if (e.serviceId === 'certificates' && e.description) {
                serviceName += ` (${e.description})`;
              }

              let freqDisplay = '';
              if (isPartner) {
                freqDisplay = `
                  <select onchange="updateEngagementFrequency('${e.id}', this.value)" class="form-select" style="padding: 4px; font-size: 12px; height: auto; background: var(--bg-card); color: var(--text-main); border-color: var(--border-color);">
                    <option value="Annual" ${e.frequency === 'Annual' ? 'selected' : ''}>Annual</option>
                    <option value="Quarterly" ${e.frequency === 'Quarterly' ? 'selected' : ''}>Quarterly</option>
                    <option value="Monthly" ${e.frequency === 'Monthly' ? 'selected' : ''}>Monthly</option>
                    <option value="One-time" ${e.frequency === 'One-time' ? 'selected' : ''}>One-time</option>
                  </select>
                `;
              } else {
                freqDisplay = `<span style="font-weight: 500; font-size: 13px;">${e.frequency}</span>`;
              }

              let feeDisplay = '';
              if (isStaff) {
                feeDisplay = `<span style="color:var(--text-muted); font-style:italic; font-size:11px;">[RESTRICTED]</span>`;
              } else if (isPartner) {
                feeDisplay = `
                  <div style="display:flex; gap:4px; align-items:center;">
                    ₹<input type="number" id="fee-input-${e.id}" value="${e.agreedFee}" style="width:100px; padding:6px; border:1px solid var(--border-color); border-radius:var(--radius-sm); font-size:13px; color: var(--text-main); background: var(--bg-card);" onchange="updateEngagementFee('${e.id}', this.value)">
                  </div>
                `;
              } else {
                feeDisplay = `<span style="font-weight: 600;">₹${e.agreedFee.toLocaleString('en-IN')}</span>`;
              }

              const budgetLines = window.getEngagementBudgetLines ? window.getEngagementBudgetLines(e) : [];
              const deliveryBudget = budgetLines.reduce((sum, line) => sum + Number(line.estimatedCost || 0), 0);
              const hasBudgetOverride = Array.isArray(e.resourceBudget);
              const budgetDisplay = isPartner ? `
                <button type="button" onclick="openResourceBudgetEditor('engagement', '${e.id}')" class="engagement-budget-button">
                  <span>${budgetLines.length ? `${hasBudgetOverride ? 'Client override' : 'Service baseline'} · ${budgetLines.length} designation${budgetLines.length === 1 ? '' : 's'}` : 'Set mapping'}</span>
                  <strong>${budgetLines.length ? `₹${deliveryBudget.toLocaleString('en-IN')}` : 'Set mapping'} →</strong>
                </button>` : '';

              return `
                <tr>
                  <td><strong>${serviceName}</strong></td>
                  <td>${freqDisplay}</td>
                  <td>${feeDisplay}</td>
                  ${isPartner ? `<td>${budgetDisplay}</td>` : ''}
                  ${isPartner ? `
                  <td style="text-align: right;">
                    <button onclick="removeClientEngagement('${e.id}')" class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px; background: rgba(231,76,60,0.05); color: #e74c3c; border-color: transparent;">Remove</button>
                  </td>
                  ` : ''}
                </tr>
              `;
            }).join('')}
            ${engs.length === 0 ? `<tr><td colspan="${isPartner ? 5 : 3}" style="text-align: center; color: var(--text-muted);">No active subscription allotments mapped.</td></tr>` : ''}
          </tbody>
        </table>
      </div>

      ${isPartner ? `
      <div style="margin-top: 20px; border-top: 1px solid var(--border-color); padding-top: 20px;">
        <h4 style="font-size: 13px; font-weight: 600; margin-bottom: 12px;">Add Service Engagement</h4>
        <div style="display: flex; gap: 8px; flex-wrap: wrap; align-items: flex-end;">
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:11px; font-weight:600; color:var(--text-muted);">Service Scope</span>
            <select id="add-eng-service" onchange="onAddEngagementServiceChange()" class="form-select" style="padding:6px; font-size:12px; height: 32px; background: var(--bg-card); color: var(--text-main); border-color: var(--border-color);">
              ${window.State.services.map(s => `<option value="${s.id}">${s.name}</option>`).join('')}
            </select>
          </div>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:11px; font-weight:600; color:var(--text-muted);">Description (Certificates Only)</span>
            <input type="text" id="add-eng-desc" class="form-input" style="padding:6px; font-size:12px; height: 32px; width: 150px; background: var(--bg-card); color: var(--text-main); border-color: var(--border-color);" placeholder="e.g. Net Worth Cert" disabled>
          </div>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:11px; font-weight:600; color:var(--text-muted);">Frequency</span>
            <select id="add-eng-freq" class="form-select" style="padding:6px; font-size:12px; height: 32px; background: var(--bg-card); color: var(--text-main); border-color: var(--border-color);">
              <option value="Annual">Annual</option>
              <option value="Quarterly">Quarterly</option>
              <option value="Monthly">Monthly</option>
              <option value="One-time">One-time</option>
            </select>
          </div>
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:11px; font-weight:600; color:var(--text-muted);">Agreed Fee (INR)</span>
            <input type="number" id="add-eng-fee" class="form-input" style="padding:6px; font-size:12px; width:100px; height: 32px; background: var(--bg-card); color: var(--text-main); border-color: var(--border-color);" placeholder="e.g. 5000">
          </div>
          <button onclick="addEngagementFromDrawer()" class="btn btn-primary" style="padding:6px 12px; font-size:12px; height: 32px;">Add Service</button>
        </div>
      </div>
      ` : ''}
    `;
  } else if (tab === 'audit') {
    container.innerHTML = `
      <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Profile Modification Trails</h4>
      <div style="display: flex; flex-direction: column; gap: 8px;">
        <div style="border-left: 2px solid var(--border-color); padding-left: 14px; position: relative; font-size: 12px;">
          <div style="position: absolute; left: -5px; top: 2px; width: 8px; height: 8px; border-radius: 50%; background: var(--bronze);"></div>
          <div style="color: var(--text-muted);">14-Aug-2026 13:00</div>
          <div style="font-weight: 600; color: var(--text-main);">Profile Onboarding Initialized</div>
          <div style="color: var(--text-muted);">System seed parameters applied to registry database.</div>
        </div>
      </div>
    `;
  }
};

window.addGSTINFromProfileDrawer = function() {
  const gVal = prompt("Enter 15-character GSTIN Number:");
  if (!gVal) return;
  const gstRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
  if (gVal.length !== 15 || !gstRegex.test(gVal.toUpperCase())) {
    alert("Invalid GSTIN structure format!");
    return;
  }
  const client = window.State.clients.find(c => c.id === activeClientProfileId);
  const gstPan = gVal.substring(2, 12).toUpperCase();
  if (gstPan !== client.pan.toUpperCase()) {
    if (!confirm("Warning: Embedded PAN inside GSTIN does not match client PAN ID. Do you still wish to add?")) {
      return;
    }
  }

  // Count check (limit 30)
  const currentCount = window.State.gstRegistrations.filter(g => g.clientId === activeClientProfileId).length;
  if (currentCount >= 30) {
    alert("Failed: Maximum limit of 30 GST registrations reached.");
    return;
  }

  window.State.gstRegistrations.push({
    id: `g_added_${Date.now()}`,
    clientId: activeClientProfileId,
    gstin: gVal.toUpperCase(),
    state: window.resolveGSTINState(gVal),
    status: 'Active'
  });
  window.saveState();
  switchProfileSubTab('gst');
};

window.addContactFromProfileDrawer = function() {
  const name = prompt("Contact Person Name:");
  if (!name) return;
  const designation = prompt("Designation (e.g. CFO, Director):") || 'Representative';
  const email = prompt("Email address:") || '';
  const mobile = prompt("Mobile phone:") || '';

  const currentCount = window.State.contacts.filter(c => c.clientId === activeClientProfileId).length;
  if (currentCount >= 30) {
    alert("Failed: Maximum limit of 30 contact personnel profiles reached.");
    return;
  }

  window.State.contacts.push({
    id: `con_added_${Date.now()}`,
    clientId: activeClientProfileId,
    name, designation, email, mobile,
    isPrimary: currentCount === 0
  });
  window.saveState();
  switchProfileSubTab('contacts');
};

window.updateEngagementFee = function(id, val) {
  const parsed = parseFloat(val);
  if (isNaN(parsed) || parsed < 0) {
    alert("Please enter a valid positive fee number.");
    return;
  }
  const e = window.State.engagements.find(x => x.id === id);
  if (e) {
    e.agreedFee = parsed;
    window.saveState();
    if (window.renderDashboard) window.renderDashboard();
    switchProfileSubTab('services');
  }
};

window.updateEngagementFrequency = function(id, val) {
  const e = window.State.engagements.find(x => x.id === id);
  if (e) {
    e.frequency = val;
    window.saveState();
    if (window.renderDashboard) window.renderDashboard();
    switchProfileSubTab('services');
  }
};

window.removeClientEngagement = function(id) {
  if (confirm("Are you sure you want to remove this service engagement?")) {
    window.State.engagements = window.State.engagements.filter(e => e.id !== id);
    window.saveState();
    if (window.renderDashboard) window.renderDashboard();
    switchProfileSubTab('services');
  }
};

window.onAddEngagementServiceChange = function() {
  const sVal = document.getElementById('add-eng-service').value;
  const descInput = document.getElementById('add-eng-desc');
  if (descInput) {
    descInput.disabled = sVal !== 'certificates';
    if (sVal !== 'certificates') {
      descInput.value = '';
    }
  }
};

window.addEngagementFromDrawer = function() {
  const serviceId = document.getElementById('add-eng-service').value;
  const description = document.getElementById('add-eng-desc').value.trim();
  const frequency = document.getElementById('add-eng-freq').value;
  const feeVal = parseFloat(document.getElementById('add-eng-fee').value);

  if (isNaN(feeVal) || feeVal < 0) {
    alert("Please enter a valid agreed fee.");
    return;
  }

  if (serviceId === 'certificates' && !description) {
    alert("Please enter a description for the certificate.");
    return;
  }

  const client = window.State.clients.find(c => c.id === activeClientProfileId);
  if (!client) return;

  const existing = window.State.engagements.find(engagement => engagement.clientId === activeClientProfileId && engagement.serviceId === serviceId);
  if (existing) {
    alert('This client already has this service mapped. Edit its resource budget from the existing service row instead.');
    return;
  }

  const service = (window.State.services || []).find(item => item.id === serviceId);
  const serviceConfig = window.getServiceConfiguration ? window.getServiceConfiguration(service) : service;

  const newEng = {
    id: `e_added_${Date.now()}`,
    clientId: activeClientProfileId,
    serviceId,
    description: serviceId === 'certificates' ? description : '',
    picUserId: client.picUserId || 'u_solani',
    micUserId: client.micUserId || 'u_desai',
    teamUserIds: [],
    agreedFee: feeVal,
    frequency,
    baselineBudgetSnapshot: window.cloneServiceBudget ? window.cloneServiceBudget(serviceConfig?.baselineBudget) : []
  };

  window.State.engagements.push(newEng);
  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  switchProfileSubTab('services');
};
