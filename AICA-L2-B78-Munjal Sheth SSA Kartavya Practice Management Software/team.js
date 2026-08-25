let teamOnboardingStep = 1;

window.initTeamModule = function() {
  renderTeamStats();
  renderTeamRoster();
  renderOrgTree();
  populateCalculatorEmployeeSelect();
  calculateProfitability();

  // Bulk and individual roster imports are partner-only.
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
  document.querySelectorAll('#view-team [data-partner-action]').forEach(button => {
    button.style.display = user.role === 'super_admin' ? 'inline-flex' : 'none';
  });
};

// TEAM STATS
function renderTeamStats() {
  const team = window.State.team;
  
  const activeCount = team.filter(t => t.status === 'Active').length;
  const partnersCount = team.filter(t => t.role === 'super_admin' && t.status === 'Active').length;
  const managersCount = team.filter(t => t.role === 'manager' && t.status === 'Active').length;
  const staffCount = team.filter(t => t.role === 'staff' && t.status === 'Active').length;
  
  // Let's assume employees with IDs ending in 6 or 7 are "new joiners" in mock data
  const newJoinersCount = 2; 

  document.getElementById('t-stat-active').textContent = activeCount;
  document.getElementById('t-stat-partners').textContent = partnersCount;
  document.getElementById('t-stat-managers').textContent = managersCount;
  document.getElementById('t-stat-staff').textContent = staffCount;
  document.getElementById('t-stat-joiners').textContent = newJoinersCount;
}

// TEAM ROSTER TABLE
function renderTeamRoster() {
  const container = document.getElementById('team-roster-content');
  if (!container) return;

  const team = window.State.team;

  container.innerHTML = `
    <div class="table-responsive">
      <table class="custom-table">
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Role</th>
            <th>Designation</th>
            <th>Department</th>
            <th>Email</th>
            <th>Capacity</th>
            <th>Cost Rate</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${team.map(t => {
            let roleBadge = 'badge-staff';
            if (t.role === 'super_admin') roleBadge = 'badge-partner';
            if (t.role === 'manager') roleBadge = 'badge-manager';
            const costVal = t.costPerHour !== undefined ? t.costPerHour : (t.costRate || 0);

            const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
            const isPartner = (activeUser.role === 'super_admin');

            let costDisplay = '';
            if (isPartner) {
              costDisplay = `₹<input type="number" value="${costVal}" style="width:80px;padding:4px 6px;border:1px solid var(--border-color);border-radius:var(--radius-sm);font-size:13px;background:var(--bg-card);color:var(--text-main);" onchange="updateEmployeeCostRate('${t.id}', this.value)">`;
            } else {
              costDisplay = `<span style="color:var(--text-muted); font-style:italic; font-size:11px;">[RESTRICTED]</span>`;
            }

            let actionButtons = `<button onclick="openEmpProfileDrawer('${t.id}')" class="btn btn-secondary" style="font-size:11px;padding:4px 10px;margin-right:4px;">View</button>`;
            if (isPartner) {
              actionButtons += `<button onclick="quickToggleEmpStatus('${t.id}')" class="btn" style="font-size:11px;padding:4px 10px;background:${t.status === 'Active' ? 'rgba(231,76,60,0.08)' : 'rgba(46,204,113,0.08)'};color:${t.status === 'Active' ? '#e74c3c' : '#2ecc71'};border:1px solid ${t.status === 'Active' ? 'rgba(231,76,60,0.3)' : 'rgba(46,204,113,0.3)'};">${t.status === 'Active' ? 'Deactivate' : 'Activate'}</button>`;
            }

            return `
              <tr style="cursor:pointer;" onclick="openEmpProfileDrawer('${t.id}')">
                <td><code>${t.code}</code></td>
                <td><strong>${t.name}</strong></td>
                <td><span class="badge ${roleBadge}">${t.roleLabel}</span></td>
                <td>${t.designation}</td>
                <td>${t.department}</td>
                <td style="font-size:12px; color:var(--text-muted);">${t.email || '—'}</td>
                <td>${t.stdHours} hrs</td>
                <td onclick="event.stopPropagation()">
                  <div style="display:flex; align-items:center; gap:4px;">
                    ${costDisplay}
                  </div>
                </td>
                <td><span class="badge ${t.status === 'Active' ? 'badge-active' : 'badge-inactive'}">${t.status}</span></td>
                <td onclick="event.stopPropagation()" style="white-space:nowrap;">
                  ${actionButtons}
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

// RECURSIVE ORGANIZATIONAL CHART
window.renderOrgTree = function() {
  const container = document.getElementById('team-org-tree-content');
  if (!container) return;

  // Root node: Sheth Solani (u_solani) & Munjal Solani (u_munjal) - standard partners
  const roots = window.State.team.filter(t => !t.managerId && t.status === 'Active');

  let html = '<div style="display: flex; flex-direction: column; gap: 20px;">';
  roots.forEach(root => {
    html += `<div class="tree-root-wrapper">
      <div class="tree-node-content" style="border-left: 4px solid var(--bronze);">
        <div class="tree-node-icon">💼</div>
        <div>
          <div style="font-weight: 700; font-size: 14px;">${root.name}</div>
          <div style="font-size: 11px; color: var(--text-muted);">${root.designation} (${root.roleLabel})</div>
        </div>
      </div>
      ${renderTreeChildren(root.id)}
    </div>`;
  });
  html += '</div>';

  container.innerHTML = html;
};

function renderTreeChildren(managerId) {
  const children = window.State.team.filter(t => t.managerId === managerId && t.status === 'Active');
  if (children.length === 0) return '';

  let html = '<div style="display: flex; flex-direction: column;">';
  children.forEach(child => {
    html += `
      <div class="tree-node">
        <div class="tree-node-content" style="border-left: 4px solid var(--module-accent);">
          <div class="tree-node-icon">👤</div>
          <div>
            <div style="font-weight: 600; font-size: 13px;">${child.name}</div>
            <div style="font-size: 10px; color: var(--text-muted);">${child.designation} (${child.roleLabel})</div>
          </div>
        </div>
        ${renderTreeChildren(child.id)}
      </div>
    `;
  });
  html += '</div>';
  return html;
}

// 5-STEP ADD EMPLOYEE WIZARD MODAL
window.openAddEmployeeModal = function() {
  teamOnboardingStep = 1;
  const modal = document.getElementById('add-employee-modal');
  modal.classList.add('active');

  // Reset form inputs
  document.getElementById('emp-code').value    = window.generateCode('SSA-EMP', window.State.team);
  document.getElementById('emp-name').value    = '';
  document.getElementById('emp-desg').value    = '';
  document.getElementById('emp-dept').value    = 'Audit';
  document.getElementById('emp-role').value    = 'staff';
  document.getElementById('emp-hours').value   = 160;
  document.getElementById('emp-rate').value    = 4000;

  const empEmail = document.getElementById('emp-email');
  if (empEmail) empEmail.value = '';
  const empMobile = document.getElementById('emp-mobile');
  if (empMobile) empMobile.value = '';
  const empPwd = document.getElementById('emp-password');
  if (empPwd) empPwd.value = '';
  const empDoj = document.getElementById('emp-doj');
  if (empDoj) empDoj.value = '';

  // Load managers list dropdown
  populateEmployeeManagerSelect();

  renderEmployeeWizardSteps();
  showEmployeeWizardStepPanel();
};

window.closeAddEmployeeModal = function() {
  const modal = document.getElementById('add-employee-modal');
  modal.classList.remove('active');
};

// ─── BULK TEAM IMPORT ──────────────────────────────────────────────────────
let pendingTeamImportRecords = [];

function isTeamImportPartner() {
  return window.getCurrentActiveUser && window.getCurrentActiveUser()?.role === 'super_admin';
}

window.openTeamBulkUploadModal = function() {
  if (!isTeamImportPartner()) { alert('Unauthorized: Only partners can bulk-upload team records.'); return; }
  pendingTeamImportRecords = [];
  document.getElementById('team-csv-import-results').style.display = 'none';
  document.getElementById('team-csv-file-input').value = '';
  const dropzone = document.getElementById('team-csv-dropzone');
  dropzone.ondragover = event => { event.preventDefault(); dropzone.style.borderColor = 'var(--module-accent)'; };
  dropzone.ondragleave = () => { dropzone.style.borderColor = 'var(--border-color)'; };
  dropzone.ondrop = event => { event.preventDefault(); dropzone.style.borderColor = 'var(--border-color)'; window.handleTeamBulkUpload(event.dataTransfer.files[0]); };
  document.getElementById('team-bulk-upload-modal').classList.add('active');
};

window.closeTeamBulkUploadModal = function() {
  document.getElementById('team-bulk-upload-modal').classList.remove('active');
};

window.downloadTeamCSVTemplate = function() {
  const headers = ['Employee Code', 'Full Name', 'Designation', 'Department', 'Role', 'Manager Code', 'Email', 'Mobile', 'Standard Hours', 'Cost Rate', 'Date of Joining'];
  const example = ['SSA-EMP-00008', 'Aarav Mehta', 'Article Associate', 'Audit', 'staff', 'SSA-EMP-00003', 'aarav.mehta@example.com', '9876543210', '160', '350', '2026-08-24'];
  const blob = new Blob([`${headers.join(',')}\r\n${example.join(',')}\r\n`], { type: 'text/csv;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob); link.download = 'SSA_Kartavya_Team_Import_Template.csv';
  document.body.appendChild(link); link.click(); document.body.removeChild(link); URL.revokeObjectURL(link.href);
};

function parseTeamCSVLine(line) {
  const cells = []; let value = ''; let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"' && line[i + 1] === '"' && quoted) { value += '"'; i++; }
    else if (char === '"') quoted = !quoted;
    else if (char === ',' && !quoted) { cells.push(value.trim()); value = ''; }
    else value += char;
  }
  cells.push(value.trim());
  return cells;
}

window.handleTeamBulkUpload = function(file) {
  if (!isTeamImportPartner() || !file) return;
  if (!file.name.toLowerCase().endsWith('.csv')) { alert('Please select a CSV file.'); return; }
  const reader = new FileReader();
  reader.onload = event => {
    const lines = String(event.target.result || '').replace(/^\uFEFF/, '').split(/\r?\n/).filter(line => line.trim());
    if (lines.length < 2) { alert('The CSV needs a header row and at least one employee row.'); return; }
    const headers = parseTeamCSVLine(lines[0]).map(header => header.trim().toLowerCase());
    const required = ['full name', 'designation', 'department', 'role'];
    const missing = required.filter(header => !headers.includes(header));
    if (missing.length) { alert(`Missing required CSV column(s): ${missing.join(', ')}`); return; }
    const indexOf = header => headers.indexOf(header);
    const existingCodes = new Set(window.State.team.map(member => member.code.toUpperCase()));
    const existingEmails = new Set(window.State.team.map(member => (member.email || '').toLowerCase()).filter(Boolean));
    const records = []; const errors = [];
    lines.slice(1).forEach((line, rowIndex) => {
      const row = parseTeamCSVLine(line);
      const get = header => indexOf(header) >= 0 ? (row[indexOf(header)] || '').trim() : '';
      const name = get('full name'); const designation = get('designation'); const department = get('department');
      const role = get('role').toLowerCase(); const email = get('email').toLowerCase();
      let code = get('employee code').toUpperCase();
      if (!code) code = window.generateCode('SSA-EMP', [...window.State.team, ...records]);
      if (!name || !designation || !department || !['staff', 'manager', 'super_admin'].includes(role)) { errors.push(`Row ${rowIndex + 2}: name, designation, department and a valid role are required.`); return; }
      if (existingCodes.has(code) || records.some(record => record.code === code)) { errors.push(`Row ${rowIndex + 2}: duplicate employee code ${code}.`); return; }
      if (email && (existingEmails.has(email) || records.some(record => record.email === email))) { errors.push(`Row ${rowIndex + 2}: duplicate email ${email}.`); return; }
      const hours = Number(get('standard hours') || 160); const rate = Number(get('cost rate') || 3000);
      if (!Number.isFinite(hours) || hours <= 0 || !Number.isFinite(rate) || rate < 0) { errors.push(`Row ${rowIndex + 2}: hours and cost rate must be valid numbers.`); return; }
      records.push({ code, name, designation, department, role, managerCode: get('manager code').toUpperCase(), email, mobile: get('mobile'), stdHours: hours, costRate: rate, dateOfJoining: get('date of joining') || window.toLocalISODate() });
    });
    pendingTeamImportRecords = records;
    const results = document.getElementById('team-csv-import-results');
    results.style.display = 'block';
    results.innerHTML = `<div class="validation-banner ${errors.length ? 'validation-banner-warning' : 'validation-banner-success'}"><strong>${records.length}</strong> valid employee record(s) ready to import.${errors.length ? ` ${errors.length} row(s) need attention.` : ''}</div>${errors.length ? `<div style="max-height:110px; overflow:auto; color:#dc2626; font-size:11px; margin-bottom:12px;">${errors.map(error => `<div>${error}</div>`).join('')}</div>` : ''}${records.length ? `<div class="table-responsive"><table class="custom-table" style="font-size:11px;"><thead><tr><th>Code</th><th>Name</th><th>Role</th><th>Manager Code</th><th>Email</th></tr></thead><tbody>${records.map(record => `<tr><td>${record.code}</td><td><strong>${record.name}</strong></td><td>${record.role}</td><td>${record.managerCode || '—'}</td><td>${record.email || '—'}</td></tr>`).join('')}</tbody></table></div><button onclick="commitTeamBulkUpload()" class="btn btn-primary" style="margin-top:14px;">Import ${records.length} Team Member(s)</button>` : ''}`;
  };
  reader.readAsText(file);
};

window.commitTeamBulkUpload = function() {
  if (!isTeamImportPartner() || !pendingTeamImportRecords.length) return;
  const roleLabels = { super_admin: 'Partner', manager: 'Manager', staff: 'Staff Associate' };
  const teamByCode = new Map(window.State.team.map(member => [member.code.toUpperCase(), member.id]));
  pendingTeamImportRecords.forEach((record, index) => teamByCode.set(record.code, `u_bulk_${Date.now()}_${index}`));
  const imported = pendingTeamImportRecords.map((record, index) => ({
    id: teamByCode.get(record.code), code: record.code, name: record.name, role: record.role, roleLabel: roleLabels[record.role], designation: record.designation, department: record.department,
    managerId: record.managerCode ? (teamByCode.get(record.managerCode) || '') : '', status: 'Active', email: record.email, mobile: record.mobile,
    passwordHash: btoa('password123'), dateOfJoining: record.dateOfJoining, costRate: record.costRate, costPerHour: record.costRate, stdHours: record.stdHours
  }));
  window.State.team.push(...imported);
  window.saveState();
  pendingTeamImportRecords = [];
  window.closeTeamBulkUploadModal();
  window.initTeamModule();
  if (window.renderDashboard) window.renderDashboard();
  alert(`${imported.length} team member(s) imported successfully. Their initial demo password is password123.`);
};

function populateEmployeeManagerSelect() {
  const sel = document.getElementById('emp-manager');
  // Managers & Partners who can be reported to
  const managers = window.State.team.filter(t => (t.role === 'super_admin' || t.role === 'manager') && t.status === 'Active');
  sel.innerHTML = `<option value="">None (Top Level / Partner)</option>` + managers.map(m => `<option value="${m.id}">${m.name} (${m.roleLabel})</option>`).join('');
}

function renderEmployeeWizardSteps() {
  const steps = ['Details', 'Role', 'Reports', 'Capacity', 'Confirm'];
  const container = document.getElementById('emp-wiz-steps-indicators');
  
  container.innerHTML = steps.map((s, idx) => {
    const num = idx + 1;
    let cls = '';
    if (teamOnboardingStep === num) cls = 'active';
    else if (teamOnboardingStep > num) cls = 'completed';
    
    return `
      <div class="wizard-step ${cls}">
        <div class="wizard-step-circle">${num}</div>
        <div class="wizard-step-label">${s}</div>
      </div>
    `;
  }).join('');
}

function showEmployeeWizardStepPanel() {
  document.querySelectorAll('.emp-wiz-panel').forEach(p => p.style.display = 'none');
  document.getElementById(`emp-wiz-panel-${teamOnboardingStep}`).style.display = 'block';

  document.getElementById('btn-emp-prev').style.visibility = teamOnboardingStep === 1 ? 'hidden' : 'visible';
  const nextBtn = document.getElementById('btn-emp-next');
  if (teamOnboardingStep === 5) {
    nextBtn.textContent = 'Save Employee';
    nextBtn.classList.remove('btn-primary');
    nextBtn.classList.add('btn-accent');
    generateEmployeeWizardReview();
  } else {
    nextBtn.textContent = 'Next';
    nextBtn.classList.remove('btn-accent');
    nextBtn.classList.add('btn-primary');
  }
}

window.empWizardNext = function() {
  if (teamOnboardingStep === 5) {
    saveNewOnboardedEmployee();
    return;
  }
  // Validate fields
  if (teamOnboardingStep === 1) {
    const name = document.getElementById('emp-name').value.trim();
    const desg = document.getElementById('emp-desg').value.trim();
    const email = document.getElementById('emp-email')?.value.trim() || '';
    if (!name || !desg) {
      alert("Name and designation are required.");
      return;
    }
    if (email && !email.includes('@')) {
      alert("Please enter a valid email address.");
      return;
    }
  }
  teamOnboardingStep++;
  renderEmployeeWizardSteps();
  showEmployeeWizardStepPanel();
};

window.empWizardPrev = function() {
  if (teamOnboardingStep > 1) {
    teamOnboardingStep--;
    renderEmployeeWizardSteps();
    showEmployeeWizardStepPanel();
  }
};

function generateEmployeeWizardReview() {
  const container = document.getElementById('emp-wiz-confirm-review');
  const name  = document.getElementById('emp-name').value;
  const desg  = document.getElementById('emp-desg').value;
  const role  = document.getElementById('emp-role').value;
  const dept  = document.getElementById('emp-dept').value;
  const hours = document.getElementById('emp-hours').value;
  const rate  = document.getElementById('emp-rate').value;
  const email = document.getElementById('emp-email')?.value || '';
  const mobile= document.getElementById('emp-mobile')?.value || '';
  const doj   = document.getElementById('emp-doj')?.value || '';
  const hasPwd= (document.getElementById('emp-password')?.value || '').length >= 8;

  const roleLabels = { super_admin: 'Partner', manager: 'Manager', staff: 'Staff Associate' };

  container.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 10px; font-size: 13px;">
      <div><strong>Full Name:</strong> ${name}</div>
      <div><strong>Designation:</strong> ${desg}</div>
      <div><strong>Department:</strong> ${dept}</div>
      <div><strong>Email:</strong> ${email || '<span style="color:var(--text-muted)">Not provided</span>'}</div>
      <div><strong>Mobile:</strong> ${mobile || '<span style="color:var(--text-muted)">Not provided</span>'}</div>
      <div><strong>Date of Joining:</strong> ${doj || '<span style="color:var(--text-muted)">Not specified</span>'}</div>
      <div><strong>Assigned System Role:</strong> <span class="badge badge-manager">${roleLabels[role]}</span></div>
      <div><strong>Monthly Capacity:</strong> ${hours} hours</div>
      <div><strong>Hourly Cost Rate:</strong> ₹${parseFloat(rate).toLocaleString('en-IN')}</div>
      <div><strong>Login Password:</strong> ${hasPwd ? '<span style="color:#2ecc71">✅ Set</span>' : '<span style="color:#e67e22">⚠️ Not set — can be added later</span>'}</div>
    </div>
  `;
}

function saveNewOnboardedEmployee() {
  const code = document.getElementById('emp-code').value.trim();
  const name = document.getElementById('emp-name').value.trim();
  const desg = document.getElementById('emp-desg').value.trim();
  const dept = document.getElementById('emp-dept').value;
  const role = document.getElementById('emp-role').value;
  const managerId = document.getElementById('emp-manager').value;
  const stdHours = parseInt(document.getElementById('emp-hours').value, 10);
  const costRate = parseFloat(document.getElementById('emp-rate').value);
  const email = document.getElementById('emp-email')?.value.trim() || '';
  const mobile = document.getElementById('emp-mobile')?.value.trim() || '';
  const password = document.getElementById('emp-password')?.value || '';
  const doj = document.getElementById('emp-doj')?.value || window.toLocalISODate();

  const roleLabels = { super_admin: 'Partner', manager: 'Manager', staff: 'Staff Associate' };
  const newEmpId = `u_${Date.now()}`;

  // Simple email format check if provided
  if (email && !email.includes('@')) {
    alert('Please enter a valid email address.');
    return;
  }

  const newEmp = {
    id: newEmpId,
    code,
    name,
    role,
    roleLabel: roleLabels[role],
    designation: desg,
    department: dept,
    managerId,
    status: 'Active',
    email,
    mobile,
    passwordHash: password ? btoa(password) : '',  // simple base64 encoding (demo only)
    dateOfJoining: doj,
    costRate: isNaN(costRate) ? 3000 : costRate,
    costPerHour: isNaN(costRate) ? 3000 : costRate,
    stdHours: isNaN(stdHours) ? 160 : stdHours
  };

  window.State.team.push(newEmp);
  window.saveState();

  if (window.renderDashboard) window.renderDashboard();
  initTeamModule();

  alert(`Employee ${name} added successfully.`);
  closeAddEmployeeModal();
}

window.updateEmployeeCostRate = function(id, val) {
  const parsed = parseFloat(val);
  if (isNaN(parsed) || parsed < 0) {
    alert("Please enter a valid rate.");
    return;
  }
  const t = window.State.team.find(x => x.id === id);
  if (t) {
    t.costPerHour = parsed;
    t.costRate = parsed;
    window.saveState();
    if (window.renderDashboard) window.renderDashboard();
    renderTeamRoster();
    if (window.calculateProfitability) window.calculateProfitability();
  }
};

window.populateCalculatorEmployeeSelect = function() {
  const sel = document.getElementById('calc-emp-select');
  if (!sel) return;
  const viewer = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  const team = viewer?.role === 'super_admin'
    ? window.State.team.filter(t => t.status === 'Active')
    : window.State.team.filter(t => t.id === viewer?.id && t.status === 'Active');
  sel.innerHTML = team.map(t => `<option value="${t.id}">${t.name} (${t.roleLabel})</option>`).join('');
  sel.disabled = !!viewer && viewer.role !== 'super_admin';
};

window.profitabilityMode = 'individual';

window.switchProfitabilityMode = function(mode) {
  const viewer = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  window.profitabilityMode = mode === 'ledger' && viewer?.role !== 'super_admin' ? 'individual' : mode;
  const selContainer = document.getElementById('calc-emp-select-container');
  if (selContainer) {
    selContainer.style.display = window.profitabilityMode === 'individual' ? 'flex' : 'none';
  }
  window.calculateProfitability();
};

window.getEmployeeProfitabilityMetrics = function(empId) {
  const emp = window.State.team.find(t => t.id === empId);
  if (!emp) return null;

  const costRate = emp.costPerHour !== undefined ? emp.costPerHour : (emp.costRate || 0);
  const stdHours = emp.stdHours || 160;
  const annualCost = costRate * stdHours * 12;

  const myEngs = window.State.engagements.filter(e => 
    e.picUserId === empId || e.micUserId === empId || (e.teamUserIds && e.teamUserIds.includes(empId))
  );

  let totalAllocatedRevenue = 0;

  myEngs.forEach(e => {
    const client = window.State.clients.find(c => c.id === e.clientId);
    if (!client || client.isArchived) return;

    let annualFee = e.agreedFee;
    if (e.frequency === 'Monthly') annualFee = e.agreedFee * 12;
    else if (e.frequency === 'Quarterly') annualFee = e.agreedFee * 4;

    const picObj = window.State.team.find(t => t.id === e.picUserId);
    const micObj = window.State.team.find(t => t.id === e.micUserId);
    
    const picRate = picObj ? (picObj.costPerHour || picObj.costRate || 0) : 0;
    const micRate = micObj ? (micObj.costPerHour || micObj.costRate || 0) : 0;

    let picCostShare = picRate * 20;
    let micCostShare = micRate * 60;
    let associatesCostShare = 0;

    const assocCosts = [];
    if (e.teamUserIds) {
      e.teamUserIds.forEach(sid => {
        const staffObj = window.State.team.find(t => t.id === sid);
        if (staffObj) {
          const sRate = staffObj.costPerHour || staffObj.costRate || 0;
          associatesCostShare += (sRate * 150);
          assocCosts.push({ id: sid, cost: sRate * 150 });
        }
      });
    }

    const totalEngagementTeamCost = picCostShare + micCostShare + associatesCostShare;
    
    let myEngagementCost = 0;
    if (e.picUserId === empId) {
      myEngagementCost = picCostShare;
    } else if (e.micUserId === empId) {
      myEngagementCost = micCostShare;
    } else if (e.teamUserIds && e.teamUserIds.includes(empId)) {
      const match = assocCosts.find(ac => ac.id === empId);
      myEngagementCost = match ? match.cost : (costRate * 150);
    }

    const myShare = totalEngagementTeamCost > 0 ? (myEngagementCost / totalEngagementTeamCost) : 0;
    totalAllocatedRevenue += annualFee * myShare;
  });

  const netMargin = totalAllocatedRevenue - annualCost;
  const marginPercent = totalAllocatedRevenue > 0 ? (netMargin / totalAllocatedRevenue) * 100 : 0;

  return {
    annualCost,
    totalAllocatedRevenue,
    netMargin,
    marginPercent,
    stdHours,
    costRate
  };
};

window.calculateProfitability = function() {
  const sel = document.getElementById('calc-emp-select');
  const resultsDiv = document.getElementById('calc-results-pane');
  if (!sel || !resultsDiv) return;
  const viewer = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!viewer) return;
  const canViewFirm = viewer.role === 'super_admin';
  if (!canViewFirm && window.profitabilityMode === 'ledger') window.profitabilityMode = 'individual';

  const tabHtml = `
    <div style="display: flex; gap: 16px; margin-bottom: 24px; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">
      <button onclick="switchProfitabilityMode('individual')" class="btn" style="background:none; border:none; border-bottom: 2px solid ${window.profitabilityMode === 'individual' ? 'var(--bronze)' : 'transparent'}; border-radius:0; color:${window.profitabilityMode === 'individual' ? 'var(--text-main)' : 'var(--text-muted)'}; font-weight:bold; font-size:13px; padding: 6px 12px; cursor:pointer; outline:none;">
        Individual Calculator
      </button>
      ${canViewFirm ? `<button onclick="switchProfitabilityMode('ledger')" class="btn" style="background:none; border:none; border-bottom: 2px solid ${window.profitabilityMode === 'ledger' ? 'var(--bronze)' : 'transparent'}; border-radius:0; color:${window.profitabilityMode === 'ledger' ? 'var(--text-main)' : 'var(--text-muted)'}; font-weight:bold; font-size:13px; padding: 6px 12px; cursor:pointer; outline:none;">Firm-wide Employee Ledger</button>` : ''}
    </div>
  `;

  if (window.profitabilityMode === 'ledger') {
    const tableRowsHtml = window.State.team.map(emp => {
      const metrics = window.getEmployeeProfitabilityMetrics(emp.id);
      if (!metrics) return '';

      let badgeClass = 'badge-active'; 
      let badgeLabel = 'Profitable';
      if (metrics.marginPercent > 40) {
        badgeClass = 'badge-partner'; 
        badgeLabel = 'Highly Profitable';
      } else if (metrics.marginPercent < 0) {
        badgeClass = 'badge-inactive'; 
        badgeLabel = 'Deficit';
      }

      let roleBadge = 'badge-staff';
      if (emp.role === 'super_admin') roleBadge = 'badge-partner';
      if (emp.role === 'manager') roleBadge = 'badge-manager';

      return `
        <tr>
          <td>
            <strong>${emp.name}</strong><br>
            <small class="text-muted">${emp.code}</small>
          </td>
          <td><span class="badge ${roleBadge}">${emp.roleLabel}</span></td>
          <td>₹${Math.round(metrics.annualCost).toLocaleString('en-IN')}</td>
          <td>₹${Math.round(metrics.totalAllocatedRevenue).toLocaleString('en-IN')}</td>
          <td style="color: ${metrics.netMargin >= 0 ? '#2ecc71' : '#e74c3c'}; font-weight: 700;">
            ${metrics.netMargin >= 0 ? '+' : ''}₹${Math.round(metrics.netMargin).toLocaleString('en-IN')}
          </td>
          <td style="color: ${metrics.netMargin >= 0 ? '#2ecc71' : '#e74c3c'}; font-weight: 700;">
            ${metrics.marginPercent.toFixed(1)}%
          </td>
          <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
        </tr>
      `;
    }).join('');

    resultsDiv.innerHTML = `
      ${tabHtml}
      <div class="table-responsive">
        <table class="custom-table">
          <thead>
            <tr>
              <th>Employee Details</th>
              <th>Role</th>
              <th>Annualized Cost</th>
              <th>Allocated Rev Share</th>
              <th>Net Margin</th>
              <th>Margin %</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${tableRowsHtml || `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">No employees found.</td></tr>`}
          </tbody>
        </table>
      </div>
    `;
    return;
  }

  const empId = canViewFirm ? (sel.value || (window.State.team[0] ? window.State.team[0].id : null)) : viewer.id;
  if (!empId) {
    resultsDiv.innerHTML = `
      ${tabHtml}
      <p style="color:var(--text-muted);">No employees found in state.</p>
    `;
    return;
  }

  const emp = window.State.team.find(t => t.id === empId);
  if (!emp) return;

  const metrics = window.getEmployeeProfitabilityMetrics(empId);
  if (!metrics) return;

  const myEngs = window.State.engagements.filter(e => 
    e.picUserId === empId || e.micUserId === empId || (e.teamUserIds && e.teamUserIds.includes(empId))
  );

  let totalSupportedRevenue = 0;
  const tableRows = myEngs.map(e => {
    const client = window.State.clients.find(c => c.id === e.clientId);
    if (!client || client.isArchived) return '';

    let annualFee = e.agreedFee;
    if (e.frequency === 'Monthly') annualFee = e.agreedFee * 12;
    else if (e.frequency === 'Quarterly') annualFee = e.agreedFee * 4;

    totalSupportedRevenue += annualFee;

    const picObj = window.State.team.find(t => t.id === e.picUserId);
    const micObj = window.State.team.find(t => t.id === e.micUserId);
    
    const picRate = picObj ? (picObj.costPerHour || picObj.costRate || 0) : 0;
    const micRate = micObj ? (micObj.costPerHour || micObj.costRate || 0) : 0;

    let picCostShare = picRate * 20;
    let micCostShare = micRate * 60;
    let associatesCostShare = 0;

    const assocCosts = [];
    if (e.teamUserIds) {
      e.teamUserIds.forEach(sid => {
        const staffObj = window.State.team.find(t => t.id === sid);
        if (staffObj) {
          const sRate = staffObj.costPerHour || staffObj.costRate || 0;
          associatesCostShare += (sRate * 150);
          assocCosts.push({ id: sid, cost: sRate * 150 });
        }
      });
    }

    const totalEngagementTeamCost = picCostShare + micCostShare + associatesCostShare;
    
    let myEngagementCost = 0;
    let roleLabel = 'Associate';
    if (e.picUserId === empId) {
      myEngagementCost = picCostShare;
      roleLabel = 'Partner (PIC)';
    } else if (e.micUserId === empId) {
      myEngagementCost = micCostShare;
      roleLabel = 'Manager (MIC)';
    } else if (e.teamUserIds && e.teamUserIds.includes(empId)) {
      const match = assocCosts.find(ac => ac.id === empId);
      myEngagementCost = match ? match.cost : (metrics.costRate * 150);
      roleLabel = 'Associate';
    }

    const myShare = totalEngagementTeamCost > 0 ? (myEngagementCost / totalEngagementTeamCost) : 0;
    const allocatedRevenue = annualFee * myShare;

    let serviceName = window.SERVICES_MAP[e.serviceId] || e.serviceId;
    if (e.serviceId === 'certificates' && e.description) {
      serviceName += ` (${e.description})`;
    }

    return `
      <tr>
        <td><strong>${client.name}</strong><br><small class="text-muted">${client.code} · ${client.entityType}</small></td>
        <td>${serviceName}</td>
        <td>₹${annualFee.toLocaleString('en-IN')}</td>
        <td>${roleLabel}</td>
        <td>${(myShare * 100).toFixed(1)}%</td>
        <td><strong>₹${Math.round(allocatedRevenue).toLocaleString('en-IN')}</strong></td>
      </tr>
    `;
  }).join('');

  let badgeClass = 'badge-active'; 
  let badgeLabel = 'Profitable';
  if (metrics.marginPercent > 40) {
    badgeClass = 'badge-partner'; 
    badgeLabel = 'Highly Profitable';
  } else if (metrics.marginPercent < 0) {
    badgeClass = 'badge-inactive'; 
    badgeLabel = 'Deficit / Under-allocated';
  }

  resultsDiv.innerHTML = `
    ${tabHtml}
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
      <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 16px; border-radius: var(--radius-md);">
        <div style="font-size: 11px; color: var(--text-muted); font-weight: 600;">ANNUALIZED RESOURCE COST</div>
        <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: var(--text-main);">₹${Math.round(metrics.annualCost).toLocaleString('en-IN')}</div>
        <small style="color: var(--text-muted); font-size:11px;">${metrics.stdHours} hrs/mo @ ₹${metrics.costRate}/hr</small>
      </div>
      <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 16px; border-radius: var(--radius-md);">
        <div style="font-size: 11px; color: var(--text-muted); font-weight: 600;">ALLOCATED REVENUE SHARE</div>
        <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: var(--primary);">₹${Math.round(metrics.totalAllocatedRevenue).toLocaleString('en-IN')}</div>
        <small style="color: var(--text-muted); font-size:11px;">Supported total: ₹${Math.round(totalSupportedRevenue).toLocaleString('en-IN')}</small>
      </div>
      <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 16px; border-radius: var(--radius-md);">
        <div style="font-size: 11px; color: var(--text-muted); font-weight: 600;">INDIVIDUAL PROFIT MARGIN</div>
        <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: ${metrics.netMargin >= 0 ? '#2ecc71' : '#e74c3c'};">
          ${metrics.netMargin >= 0 ? '+' : ''}₹${Math.round(metrics.netMargin).toLocaleString('en-IN')}
        </div>
        <div style="display:flex; align-items:center; gap:8px; margin-top: 4px;">
          <span class="badge ${badgeClass}" style="font-size: 9px; padding: 2px 6px;">${badgeLabel}</span>
          <span style="font-weight:700; font-size:12px; color: ${metrics.netMargin >= 0 ? '#2ecc71' : '#e74c3c'};">${metrics.marginPercent.toFixed(1)}%</span>
        </div>
      </div>
    </div>

    <h4 style="font-size: 14px; font-weight: 600; margin-bottom: 12px;">Assigned Engagements Breakdown</h4>
    <div class="table-responsive">
      <table class="custom-table">
        <thead>
          <tr>
            <th>Client Context</th>
            <th>Service</th>
            <th>Annual Client Fee</th>
            <th>My Role</th>
            <th>Revenue Share %</th>
            <th>Allocated Revenue</th>
          </tr>
        </thead>
        <tbody>
          ${tableRows || `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No active client engagement mappings found.</td></tr>`}
        </tbody>
      </table>
    </div>
  `;
};

// ─── EMPLOYEE PROFILE DRAWER ──────────────────────────────────────────────────

let activeEmpId = null;
let activeEmpSubTab = 'overview';

window.openEmpProfileDrawer = function(empId) {
  activeEmpId = empId;
  activeEmpSubTab = 'overview';
  const emp = window.State.team.find(t => t.id === empId);
  if (!emp) return;

  document.getElementById('emp-drawer-name').textContent = emp.name;
  document.getElementById('emp-drawer-code').textContent = `${emp.code} · ${emp.roleLabel} · ${emp.department}`;

  const toggleBtn = document.getElementById('emp-toggle-status-btn');
  if (toggleBtn) {
    toggleBtn.textContent = emp.status === 'Active' ? '⏸ Deactivate' : '▶ Activate';
    toggleBtn.style.color = emp.status === 'Active' ? '#e67e22' : '#2ecc71';
  }

  // Handle drawer action bar role visibility & self-deactivation locks
  const actionsEl = document.getElementById('emp-drawer-actions');
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (actionsEl) {
    if (activeUser && activeUser.role === 'super_admin') {
      actionsEl.style.display = 'flex';
      
      const isSelf = (empId === activeUser.id);
      const deleteBtn = actionsEl.querySelector("button[onclick='deleteEmployee()']");
      const editBtn = actionsEl.querySelector("button[onclick='openEditEmpModal()']");
      
      if (toggleBtn) {
        toggleBtn.disabled = isSelf;
        toggleBtn.style.opacity = isSelf ? '0.5' : '1';
        toggleBtn.style.cursor = isSelf ? 'not-allowed' : 'pointer';
        toggleBtn.title = isSelf ? 'Safety Lock: You cannot deactivate your own active partner account' : '';
      }
      if (deleteBtn) {
        deleteBtn.disabled = isSelf;
        deleteBtn.style.opacity = isSelf ? '0.5' : '1';
        deleteBtn.style.cursor = isSelf ? 'not-allowed' : 'pointer';
        deleteBtn.title = isSelf ? 'Safety Lock: You cannot delete your own active partner account' : '';
      }
    } else {
      actionsEl.style.display = 'none';
    }
  }

  // Hide Access & Login tab for non-partners
  const accessTabBtn = document.getElementById('emp-drawer-access-tab');
  if (accessTabBtn) {
    if (activeUser && activeUser.role === 'super_admin') {
      accessTabBtn.style.display = 'inline-block';
    } else {
      accessTabBtn.style.display = 'none';
    }
  }

  // Set active sub-tab
  document.querySelectorAll('.emp-sub-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.etab === activeEmpSubTab);
  });

  renderEmpDrawerTab();

  document.getElementById('emp-profile-overlay').classList.add('active');
  document.getElementById('emp-profile-drawer').classList.add('active');
};

window.closeEmpProfileDrawer = function() {
  document.getElementById('emp-profile-overlay').classList.remove('active');
  document.getElementById('emp-profile-drawer').classList.remove('active');
  activeEmpId = null;
};

window.switchEmpSubTab = function(tab) {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (tab === 'access' && (!activeUser || activeUser.role !== 'super_admin')) {
    tab = 'overview';
  }
  activeEmpSubTab = tab;
  document.querySelectorAll('.emp-sub-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.etab === tab);
  });
  renderEmpDrawerTab();
};

function renderEmpDrawerTab() {
  const body = document.getElementById('emp-drawer-body');
  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp || !body) return;

  const roleLabels = { super_admin: 'Partner', manager: 'Manager', staff: 'Staff Associate' };
  const managerName = emp.managerId
    ? (window.State.team.find(t => t.id === emp.managerId)?.name || '—')
    : '— (Top Level)';

  if (activeEmpSubTab === 'overview') {
    body.innerHTML = `
      <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 24px;">
        <div style="width: 64px; height: 64px; border-radius: 50%; background: linear-gradient(135deg, var(--primary), var(--bronze)); display: flex; align-items: center; justify-content: center; font-size: 24px; color: #fff; font-weight: 700; flex-shrink: 0;">
          ${emp.name.charAt(0).toUpperCase()}
        </div>
        <div>
          <div style="font-size: 18px; font-weight: 700;">${emp.name}</div>
          <div style="font-size: 13px; color: var(--text-muted);">${emp.designation} · ${emp.department}</div>
          <span class="badge ${emp.status === 'Active' ? 'badge-active' : 'badge-inactive'}" style="margin-top: 4px; display: inline-block;">${emp.status}</span>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
        ${field('Employee Code', `<code>${emp.code}</code>`)}
        ${field('System Role', `<span class="badge ${emp.role === 'super_admin' ? 'badge-partner' : emp.role === 'manager' ? 'badge-manager' : 'badge-staff'}">${emp.roleLabel}</span>`)}
        ${field('Email', emp.email || '—')}
        ${field('Mobile', emp.mobile || '—')}
        ${field('Date of Joining', emp.dateOfJoining || '—')}
        ${field('Reports To', managerName)}
      </div>
    `;
  } else if (activeEmpSubTab === 'access') {
    body.innerHTML = `
      <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 16px;">Login & Access Details</h4>
      <div style="display: grid; grid-template-columns: 1fr; gap: 12px; font-size: 13px; margin-bottom: 24px;">
        ${field('Email / Username', emp.email || '<span style="color: var(--text-muted);">Not set</span>')}
        ${field('Password', emp.passwordHash ? '<span style="color: #2ecc71;">✅ Password Set</span>' : '<span style="color: #e74c3c;">❌ No password set</span>')}
        ${field('System Role', `<span class="badge ${emp.role === 'super_admin' ? 'badge-partner' : emp.role === 'manager' ? 'badge-manager' : 'badge-staff'}">${emp.roleLabel}</span>`)}
        ${field('Access Level', emp.role === 'super_admin' ? 'Full Access (Partner)' : emp.role === 'manager' ? 'Manager — Approve Timesheets' : 'Standard Staff Access')}
        ${field('Account Status', emp.status === 'Active' ? '<span style="color:#2ecc71">✅ Active</span>' : '<span style="color:#e74c3c">❌ Inactive / Deactivated</span>')}
      </div>
      <div style="background: rgba(0,0,0,0.02); padding: 14px; border-radius: 10px; border: 1px solid var(--border-color);">
        <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Quick Password Reset</div>
        <div style="display: flex; gap: 8px; align-items: center;">
          <input type="password" id="quick-pwd-input" class="form-input" placeholder="New password" style="flex:1;">
          <button onclick="quickResetPassword()" class="btn btn-secondary" style="white-space: nowrap;">Reset Password</button>
        </div>
      </div>
    `;
  } else if (activeEmpSubTab === 'capacity') {
    const totalAssignments = window.State.engagements.filter(e => e.picUserId === emp.id || e.micUserId === emp.id || (e.teamUserIds || []).includes(emp.id)).length;

    const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : { role: 'super_admin' };
    const isPartner = (activeUser.role === 'super_admin');

    const rateVal = isPartner ? `₹${(emp.costPerHour || emp.costRate || 0).toLocaleString('en-IN')}` : '[RESTRICTED]';
    const annualizedVal = isPartner ? `₹${((emp.costPerHour || emp.costRate || 0) * (emp.stdHours || 160) * 12).toLocaleString('en-IN')}` : '[RESTRICTED]';

    let rateEditHtml = '';
    if (isPartner) {
      rateEditHtml = `
      <div style="background: rgba(0,0,0,0.02); padding: 14px; border-radius: 10px; border: 1px solid var(--border-color);">
        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 10px;">INLINE RATE & CAPACITY EDIT</div>
        <div style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <label>Hourly Cost Rate (₹):</label>
          <input type="number" id="drawer-rate-input" value="${emp.costPerHour || emp.costRate || 0}" class="form-input" style="width: 120px;">
          <button onclick="updateEmployeeCostRate('${emp.id}', document.getElementById('drawer-rate-input').value)" class="btn btn-secondary">Update</button>
        </div>
        <div style="display: flex; align-items: center; gap: 8px; font-size: 13px; margin-top: 10px;">
          <label>Monthly Hours:</label>
          <input type="number" id="drawer-hours-input" value="${emp.stdHours || 160}" class="form-input" style="width: 120px;">
          <button onclick="updateEmpHours('${emp.id}', document.getElementById('drawer-hours-input').value)" class="btn btn-secondary">Update</button>
        </div>
      </div>
      `;
    } else {
      rateEditHtml = `
      <div style="background: rgba(0,0,0,0.02); padding: 14px; border-radius: 10px; border: 1px solid var(--border-color);">
        <div style="font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 10px;">INLINE CAPACITY EDIT</div>
        <div style="display: flex; align-items: center; gap: 8px; font-size: 13px;">
          <label>Monthly Hours:</label>
          <input type="number" id="drawer-hours-input" value="${emp.stdHours || 160}" class="form-input" style="width: 120px;">
          <button onclick="updateEmpHours('${emp.id}', document.getElementById('drawer-hours-input').value)" class="btn btn-secondary">Update</button>
        </div>
      </div>
      `;
    }

    body.innerHTML = `
      <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 16px;">Work Capacity</h4>
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px; margin-bottom: 20px;">
        ${field('Monthly Std. Hours', `${emp.stdHours || 160} hrs`)}
        ${field('Hourly Cost Rate', rateVal)}
        ${field('Annualized Cost', annualizedVal)}
        ${field('Active Engagements', `${totalAssignments} client services`)}
      </div>
      ${rateEditHtml}
    `;
  } else if (activeEmpSubTab === 'clients') {
    const assignments = window.State.engagements.filter(e =>
      e.picUserId === emp.id || e.micUserId === emp.id || (e.teamUserIds || []).includes(emp.id)
    );
    const rows = assignments.map(e => {
      const cl = window.State.clients.find(c => c.id === e.clientId);
      const svcName = window.SERVICES_MAP?.[e.serviceId] || e.serviceId;
      const myRole = e.picUserId === emp.id ? 'PIC' : e.micUserId === emp.id ? 'MIC' : 'Team';
      return `<tr>
        <td><strong>${cl?.name || '—'}</strong><br><code style="font-size:10px;">${cl?.code || ''}</code></td>
        <td style="font-size:12px;">${svcName}</td>
        <td><span class="badge ${myRole === 'PIC' ? 'badge-partner' : myRole === 'MIC' ? 'badge-manager' : 'badge-staff'}">${myRole}</span></td>
        <td>₹${(e.agreedFee || 0).toLocaleString('en-IN')}</td>
      </tr>`;
    }).join('');
    body.innerHTML = `
      <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 16px;">Client Assignments (${assignments.length})</h4>
      <div class="table-responsive">
        <table class="custom-table" style="font-size:12px;">
          <thead><tr><th>Client</th><th>Service</th><th>My Role</th><th>Agreed Fee</th></tr></thead>
          <tbody>${rows || '<tr><td colspan="4" style="text-align:center;color:var(--text-muted);">No assignments found</td></tr>'}</tbody>
        </table>
      </div>
    `;
  }
}

function field(label, value) {
  return `
    <div style="background: rgba(0,0,0,0.02); padding: 12px; border-radius: 8px; border: 1px solid var(--border-color);">
      <div style="font-size: 10px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">${label}</div>
      <div style="font-size: 13px; font-weight: 600;">${value}</div>
    </div>`;
}

// ─── EDIT EMPLOYEE ────────────────────────────────────────────────────────────

window.openEditEmpModal = function() {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can edit employee details.");
    return;
  }

  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp) return;

  document.getElementById('edit-emp-name').value   = emp.name || '';
  document.getElementById('edit-emp-desg').value   = emp.designation || '';
  document.getElementById('edit-emp-dept').value   = emp.department || 'Audit';
  document.getElementById('edit-emp-role').value   = emp.role || 'staff';
  document.getElementById('edit-emp-email').value  = emp.email || '';
  document.getElementById('edit-emp-mobile').value = emp.mobile || '';
  document.getElementById('edit-emp-doj').value    = emp.dateOfJoining || '';
  document.getElementById('edit-emp-hours').value  = emp.stdHours || 160;
  document.getElementById('edit-emp-rate').value   = emp.costPerHour || emp.costRate || 3000;
  document.getElementById('edit-emp-password').value  = '';
  document.getElementById('edit-emp-password2').value = '';

  // Hide password reset section when editing a Partner's profile (only a partner can change another partner's pwd)
  const pwdSection = document.getElementById('edit-emp-password-section');
  if (pwdSection) {
    // Show password section only when editing non-partner employees
    const isTargetPartner = (emp.role === 'super_admin');
    // A partner CAN change another partner's password — but let's show it regardless (only partners reach here)
    pwdSection.style.display = 'block';
  }

  // Populate managers dropdown (exclude self)
  const sel = document.getElementById('edit-emp-manager');
  const managers = window.State.team.filter(t => (t.role === 'super_admin' || t.role === 'manager') && t.id !== activeEmpId);
  sel.innerHTML = `<option value="">— None (Top Level / Partner) —</option>` +
    managers.map(m => `<option value="${m.id}" ${m.id === emp.managerId ? 'selected' : ''}>${m.name} (${m.roleLabel})</option>`).join('');

  document.getElementById('edit-emp-modal').classList.add('active');
};

window.closeEditEmpModal = function() {
  document.getElementById('edit-emp-modal').classList.remove('active');
};

window.saveEditEmployee = function() {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can edit employee details.");
    return;
  }
  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp) return;
  if (emp.role === 'super_admin' && activeUser.role !== 'super_admin') {
    alert("Unauthorized: Managers cannot edit Partner details.");
    return;
  }

  const name  = document.getElementById('edit-emp-name').value.trim();
  const email = document.getElementById('edit-emp-email').value.trim();
  if (!name) { alert('Name is required.'); return; }

  const pwd1 = document.getElementById('edit-emp-password').value;
  const pwd2 = document.getElementById('edit-emp-password2').value;
  if (pwd1 && pwd1 !== pwd2) { alert('Passwords do not match.'); return; }
  if (pwd1 && pwd1.length < 8) { alert('Password must be at least 8 characters.'); return; }

  const roleLabels = { super_admin: 'Partner', manager: 'Manager', staff: 'Staff Associate' };
  const role = document.getElementById('edit-emp-role').value;

  emp.name          = name;
  emp.designation   = document.getElementById('edit-emp-desg').value.trim();
  emp.department    = document.getElementById('edit-emp-dept').value;
  emp.role          = role;
  emp.roleLabel     = roleLabels[role];
  emp.email         = email;
  emp.mobile        = document.getElementById('edit-emp-mobile').value.trim();
  emp.dateOfJoining = document.getElementById('edit-emp-doj').value;
  emp.managerId     = document.getElementById('edit-emp-manager').value;
  emp.stdHours      = parseInt(document.getElementById('edit-emp-hours').value, 10) || 160;
  emp.costRate      = parseFloat(document.getElementById('edit-emp-rate').value) || 3000;
  emp.costPerHour   = emp.costRate;
  // Only Partners can update passwords — explicit guard even if UI is bypassed
  if (pwd1 && activeUser && activeUser.role === 'super_admin') {
    emp.passwordHash = btoa(pwd1);
  }

  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  initTeamModule();
  closeEditEmpModal();

  // Refresh drawer
  openEmpProfileDrawer(activeEmpId);
  alert(`${name}'s details updated successfully.`);
};

// ─── STATUS TOGGLE & DELETE ───────────────────────────────────────────────────

window.toggleEmpStatus = function() {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can toggle employee status.");
    return;
  }
  if (activeEmpId === activeUser.id) {
    alert("Safety Lock: You cannot deactivate or activate your own partner account.");
    return;
  }
  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp) return;
  const newStatus = emp.status === 'Active' ? 'Inactive' : 'Active';
  if (!confirm(`Are you sure you want to ${newStatus === 'Inactive' ? 'deactivate' : 'activate'} ${emp.name}?`)) return;
  emp.status = newStatus;
  window.saveState();
  initTeamModule();
  openEmpProfileDrawer(activeEmpId);
};

window.quickToggleEmpStatus = function(empId) {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can toggle employee status.");
    return;
  }
  if (empId === activeUser.id) {
    alert("Safety Lock: You cannot deactivate or activate your own partner account.");
    return;
  }
  const emp = window.State.team.find(t => t.id === empId);
  if (!emp) return;
  const newStatus = emp.status === 'Active' ? 'Inactive' : 'Active';
  if (!confirm(`${newStatus === 'Inactive' ? 'Deactivate' : 'Activate'} ${emp.name}?`)) return;
  emp.status = newStatus;
  window.saveState();
  initTeamModule();
};

window.deleteEmployee = function() {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can delete employees.");
    return;
  }
  if (activeEmpId === activeUser.id) {
    alert("Safety Lock: You cannot delete your own partner account.");
    return;
  }
  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp) return;
  const assignedCount = window.State.engagements.filter(e =>
    e.picUserId === emp.id || e.micUserId === emp.id || (e.teamUserIds || []).includes(emp.id)
  ).length;
  if (assignedCount > 0) {
    alert(`Cannot delete ${emp.name} — they are assigned to ${assignedCount} active client engagement(s). Deactivate instead, or reassign first.`);
    return;
  }
  if (!confirm(`Permanently delete ${emp.name}? This cannot be undone.`)) return;
  window.State.team = window.State.team.filter(t => t.id !== activeEmpId);
  window.saveState();
  if (window.renderDashboard) window.renderDashboard();
  initTeamModule();
  closeEmpProfileDrawer();
  alert(`${emp.name} has been removed from the roster.`);
};

window.quickResetPassword = function() {
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (!activeUser || activeUser.role !== 'super_admin') {
    alert("Unauthorized: Only partners can reset passwords.");
    return;
  }
  const emp = window.State.team.find(t => t.id === activeEmpId);
  if (!emp) return;
  if (emp.role === 'super_admin' && activeUser.role !== 'super_admin') {
    alert("Unauthorized: Managers cannot update passwords for Partners.");
    return;
  }
  const newPwd = document.getElementById('quick-pwd-input')?.value;
  if (!newPwd || newPwd.length < 8) { alert('Password must be at least 8 characters.'); return; }
  emp.passwordHash = btoa(newPwd);
  window.saveState();
  document.getElementById('quick-pwd-input').value = '';
  renderEmpDrawerTab();
  alert(`Password for ${emp.name} has been reset.`);
};

window.updateEmpHours = function(empId, val) {
  const parsed = parseInt(val, 10);
  if (isNaN(parsed) || parsed < 1) { alert('Enter valid hours.'); return; }
  const emp = window.State.team.find(t => t.id === empId);
  if (emp) {
    emp.stdHours = parsed;
    window.saveState();
    if (window.calculateProfitability) window.calculateProfitability();
    renderEmpDrawerTab();
  }
};
