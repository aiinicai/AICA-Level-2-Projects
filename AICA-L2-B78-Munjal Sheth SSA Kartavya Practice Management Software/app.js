// SSA Kartavya - Central State & Core Loader

window.SERVICES_MAP = {
  'tax_annual': 'Income Tax Annual returns',
  'tax_audit': 'Income Tax Audit',
  'stat_audit': 'Statutory Audit',
  'gst_r1': 'GSTR 1 filing',
  'gst_3b': 'GSTR 3B filing',
  'certificates': 'Certificates'
};

// Centralized persistent state object
window.State = {
  clients: [],
  gstRegistrations: [],
  contacts: [],
  engagements: [],
  team: [],
  notifications: [],
  timesheets: [],
  jobs: [],
  jobBoardView: 'card'
};

// Date inputs represent a local calendar day.  Using toISOString() here would
// convert that day to UTC and can show the previous date in India before 05:30.
window.toLocalISODate = function(date = new Date()) {
  const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return offsetDate.toISOString().slice(0, 10);
};

// State persistence helpers
const STORAGE_KEY = 'SSA_KARTAVYA_STATE';

window.saveState = function() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(window.State));
  if (window.updateNotificationBadge) window.updateNotificationBadge();
};

window.updateNotificationBadge = function() {
  const badgeEl = document.querySelector('.notification-badge');
  if (!badgeEl) return;
  
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  const activeUserId = user ? user.id : '';

  const list = window.State.notifications || [];
  const myNotifs = list.filter(n => !n.managerId || n.managerId === activeUserId);

  const count = myNotifs.length;
  if (count > 0) {
    badgeEl.style.display = 'block';
  } else {
    badgeEl.style.display = 'none';
  }
};

window.rebuildServicesMap = function() {
  window.SERVICES_MAP = {};
  if (window.State && window.State.services) {
    window.State.services.forEach(s => {
      window.SERVICES_MAP[s.id] = s.name;
    });
  }
};

window.loadState = function() {
  const data = localStorage.getItem(STORAGE_KEY);
  if (data) {
    try {
      window.State = JSON.parse(data);
      if (!window.State || typeof window.State !== 'object') {
        seedMockData();
        return;
      }
      if (!window.State.clients || !Array.isArray(window.State.clients) || window.State.clients.length === 0) {
        seedMockData();
        return;
      }
      if (!window.State.gstRegistrations) window.State.gstRegistrations = [];
      if (!window.State.contacts) window.State.contacts = [];
      if (!window.State.engagements) window.State.engagements = [];
      if (!window.State.team || !Array.isArray(window.State.team) || window.State.team.length === 0) {
        seedMockData();
        return;
      }
      if (!window.State.notifications) window.State.notifications = [];
      if (!window.State.timesheets) window.State.timesheets = [];
      if (!window.State.jobs) window.State.jobs = [];
      if (!window.State.services || !Array.isArray(window.State.services) || window.State.services.length === 0) {
        window.State.services = [
          { id: 'tax_annual', name: 'Income Tax Annual returns', defaultFreq: 'Annual', baselineFee: 15000 },
          { id: 'tax_audit', name: 'Income Tax Audit', defaultFreq: 'Annual', baselineFee: 50000 },
          { id: 'stat_audit', name: 'Statutory Audit', defaultFreq: 'Annual', baselineFee: 100000 },
          { id: 'gst_r1', name: 'GSTR 1 filing', defaultFreq: 'Monthly', baselineFee: 3000 },
          { id: 'gst_3b', name: 'GSTR 3B filing', defaultFreq: 'Monthly', baselineFee: 3000 },
          { id: 'certificates', name: 'Certificates', defaultFreq: 'One-time', baselineFee: 5000 }
        ];
      }
      if (!window.State.activeUserId) window.State.activeUserId = 'u_solani';
      if (!window.State.jobBoardView) window.State.jobBoardView = 'card';
      window.rebuildServicesMap();
      if (window.updateNotificationBadge) window.updateNotificationBadge();
    } catch(e) {
      console.error("Failed to parse localState. Loading mock data instead.", e);
      seedMockData();
    }
  } else {
    seedMockData();
  }
};

// Sequential ID Generator
window.generateCode = function(prefix, arr, codeProperty = 'code') {
  const regex = new RegExp(`^${prefix}-(\\d+)$`);
  let maxSeq = 0;
  arr.forEach(item => {
    const val = item[codeProperty];
    if (val) {
      const match = val.match(regex);
      if (match) {
        const seq = parseInt(match[1], 10);
        if (seq > maxSeq) maxSeq = seq;
      }
    }
  });
  const nextSeq = maxSeq + 1;
  return `${prefix}-${String(nextSeq).padStart(5, '0')}`;
};

// Levenshtein distance similarity calculation
window.levenshteinSimilarity = function(s1, s2) {
  s1 = (s1 || '').trim().toLowerCase();
  s2 = (s2 || '').trim().toLowerCase();
  
  if (s1 === s2) return 1.0;
  if (s1.length === 0 || s2.length === 0) return 0.0;
  
  const m = s1.length;
  const n = s2.length;
  const d = [];
  
  for (let i = 0; i <= m; i++) {
    d[i] = [i];
  }
  for (let j = 0; j <= n; j++) {
    d[0][j] = j;
  }
  
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = s1[i-1] === s2[j-1] ? 0 : 1;
      d[i][j] = Math.min(
        d[i-1][j] + 1, // deletion
        d[i][j-1] + 1, // insertion
        d[i-1][j-1] + cost // substitution
      );
    }
  }
  
  const maxLength = Math.max(s1.length, s2.length);
  return 1.0 - (d[m][n] / maxLength);
};

// GSTIN State Code prefixes (all 38 Indian state prefixes)
window.GSTIN_STATES = {
  '01': 'Jammu & Kashmir', '02': 'Himachal Pradesh', '03': 'Punjab', '04': 'Chandigarh', 
  '05': 'Uttarakhand', '06': 'Haryana', '07': 'Delhi', '08': 'Rajasthan', '09': 'Uttar Pradesh', 
  '10': 'Bihar', '11': 'Sikkim', '12': 'Arunachal Pradesh', '13': 'Nagaland', '14': 'Manipur', 
  '15': 'Mizoram', '16': 'Tripura', '17': 'Meghalaya', '18': 'Assam', '19': 'West Bengal', 
  '20': 'Jharkhand', '21': 'Odisha', '22': 'Chhattisgarh', '23': 'Madhya Pradesh', '24': 'Gujarat', 
  '26': 'Dadra and Nagar Haveli and Daman and Diu', '27': 'Maharashtra', '29': 'Karnataka', '30': 'Goa', 
  '31': 'Lakshadweep', '32': 'Kerala', '33': 'Tamil Nadu', '34': 'Puducherry', '35': 'Andaman & Nicobar', 
  '36': 'Telangana', '37': 'Andhra Pradesh', '38': 'Ladakh'
};

window.resolveGSTINState = function(gstin) {
  if (!gstin || gstin.length < 2) return 'Unknown';
  const prefix = gstin.substring(0, 2);
  return window.GSTIN_STATES[prefix] || 'Unknown';
};

// MOCK DATA SEED
function seedMockData() {
  // Service Catalogue
  window.State.services = [
    { id: 'tax_annual', name: 'Income Tax Annual returns', defaultFreq: 'Annual', baselineFee: 15000 },
    { id: 'tax_audit', name: 'Income Tax Audit', defaultFreq: 'Annual', baselineFee: 50000 },
    { id: 'stat_audit', name: 'Statutory Audit', defaultFreq: 'Annual', baselineFee: 100000 },
    { id: 'gst_r1', name: 'GSTR 1 filing', defaultFreq: 'Monthly', baselineFee: 3000 },
    { id: 'gst_3b', name: 'GSTR 3B filing', defaultFreq: 'Monthly', baselineFee: 3000 },
    { id: 'certificates', name: 'Certificates', defaultFreq: 'One-time', baselineFee: 5000 }
  ];

  // Team
  window.State.team = [
    { id: 'u_solani', code: 'SSA-EMP-00001', name: 'Sheth Solani', role: 'super_admin', roleLabel: 'Partner', designation: 'Founding Partner', department: 'Audit', managerId: '', status: 'Active', costPerHour: 1500, stdHours: 160, passwordHash: btoa('password123') },
    { id: 'u_munjal', code: 'SSA-EMP-00002', name: 'Munjal Solani', role: 'super_admin', roleLabel: 'Partner', designation: 'Tax Partner', department: 'Taxation', managerId: '', status: 'Active', costPerHour: 1200, stdHours: 160, passwordHash: btoa('password123') },
    { id: 'u_desai', code: 'SSA-EMP-00003', name: 'Riddhi Desai', role: 'manager', roleLabel: 'Manager', designation: 'Senior Manager', department: 'Audit', managerId: 'u_solani', status: 'Active', costPerHour: 800, stdHours: 160, passwordHash: btoa('password123') },
    { id: 'u_mehta', code: 'SSA-EMP-00004', name: 'Amit Mehta', role: 'manager', roleLabel: 'Manager', designation: 'Tax Manager', department: 'Taxation', managerId: 'u_munjal', status: 'Active', costPerHour: 750, stdHours: 160, passwordHash: btoa('password123') },
    { id: 'u_patel', code: 'SSA-EMP-00005', name: 'Vikram Patel', role: 'staff', roleLabel: 'Staff Associate', designation: 'Article Assistant', department: 'Audit', managerId: 'u_desai', status: 'Active', costPerHour: 250, stdHours: 180, passwordHash: btoa('password123') },
    { id: 'u_shah', code: 'SSA-EMP-00006', name: 'Nisha Shah', role: 'staff', roleLabel: 'Staff Associate', designation: 'Consultant', department: 'Taxation', managerId: 'u_mehta', status: 'Active', costPerHour: 300, stdHours: 160, passwordHash: btoa('password123') },
    { id: 'u_joshi', code: 'SSA-EMP-00007', name: 'Karan Joshi', role: 'staff', roleLabel: 'Staff Associate', designation: 'Article Assistant', department: 'Corporate Advisory', managerId: 'u_desai', status: 'Active', costPerHour: 200, stdHours: 180, passwordHash: btoa('password123') }
  ];

  // Clients
  window.State.clients = [
    {
      id: 'c_1', code: 'SSA-CL-00001', name: 'Acme Corporation Private Limited', tradeName: 'Acme Corp', groupName: 'Acme Group',
      entityType: 'Private Limited', pan: 'AABCA1234F', status: 'Active', picUserId: 'u_solani', micUserId: 'u_desai',
      onboardingDate: '2022-04-15', fyEnd: 'March 31', referenceName: 'Direct Client', additionalInfo: 'Tech Manufacturing sector',
      tan: 'MUMA12345B', cin: 'U72200MH2022PTC123456', incorporationDate: '2022-04-01', msmeRegistrationStatus: 'Registered',
      industry: 'Technology', businessActivity: 'Software development & hardware assembly', listedExchange: 'Unlisted',
      previousAuditor: 'KV & Associates', registeredOfficeAddress: '101, Acme Tower, Andheri East, Mumbai - 400069',
      communicationAddress: '101, Acme Tower, Andheri East, Mumbai - 400069', billingAddress: '101, Acme Tower, Andheri East, Mumbai - 400069',
      isArchived: false
    },
    {
      id: 'c_2', code: 'SSA-CL-00002', name: 'Bhaskar Global LLP', tradeName: 'Bhaskar Global', groupName: 'Bhaskar Group',
      entityType: 'LLP', pan: 'ABBCH5678G', status: 'Active', picUserId: 'u_munjal', micUserId: 'u_mehta',
      onboardingDate: '2023-01-10', fyEnd: 'March 31', referenceName: 'Ref-Munjal', additionalInfo: 'Import export business',
      tan: 'DELB98765C', cin: '', llpin: 'AAA-9999', incorporationDate: '2022-12-15', msmeRegistrationStatus: 'Registered',
      industry: 'Logistics', businessActivity: 'Global freight forwarding', listedExchange: 'Unlisted',
      previousAuditor: 'None', registeredOfficeAddress: 'Plot 42, Okhla Phase 3, New Delhi - 110020',
      communicationAddress: 'Plot 42, Okhla Phase 3, New Delhi - 110020', billingAddress: 'Plot 42, Okhla Phase 3, New Delhi - 110020',
      isArchived: false
    },
    {
      id: 'c_3', code: 'SSA-CL-00003', name: 'Zion Retail Associates', tradeName: 'Zion Retail', groupName: 'Zion Retail',
      entityType: 'Partnership Firm', pan: 'AACCF9012K', status: 'Prospect', picUserId: 'u_solani', micUserId: 'u_mehta',
      onboardingDate: '2026-08-01', fyEnd: 'March 31', referenceName: 'Web Enquiry', additionalInfo: 'Apparel stores chain',
      tan: 'AHDA54321D', incorporationDate: '2026-07-20', msmeRegistrationStatus: 'Not Registered',
      industry: 'Retail', businessActivity: 'Clothing stores', listedExchange: 'Unlisted',
      previousAuditor: 'RS & Co', registeredOfficeAddress: 'Shop 5, Zion Plaza, CG Road, Ahmedabad - 380009',
      communicationAddress: 'Shop 5, Zion Plaza, CG Road, Ahmedabad - 380009', billingAddress: 'Shop 5, Zion Plaza, CG Road, Ahmedabad - 380009',
      isArchived: false
    },
    {
      id: 'c_4', code: 'SSA-CL-00004', name: 'Devendra Kumar (HUF)', tradeName: 'DK HUF Investments', groupName: 'DK Group',
      entityType: 'HUF', pan: 'AADCD3456L', status: 'Active', picUserId: 'u_munjal', micUserId: 'u_desai',
      onboardingDate: '2024-05-20', fyEnd: 'March 31', referenceName: 'Mr. Devendra K.', additionalInfo: 'Investment management only',
      incorporationDate: '2015-06-10', msmeRegistrationStatus: 'Not Applicable',
      industry: 'Financial Services', businessActivity: 'Equities & Mutual Fund investments', listedExchange: 'Unlisted',
      registeredOfficeAddress: 'A-501, Shanti Sadan, Link Road, Mumbai - 400053',
      communicationAddress: 'A-501, Shanti Sadan, Link Road, Mumbai - 400053', billingAddress: 'A-501, Shanti Sadan, Link Road, Mumbai - 400053',
      isArchived: false
    },
    {
      id: 'c_5', code: 'SSA-CL-00005', name: 'Apex Logistics Limited', tradeName: 'Apex Express', groupName: 'Apex Group',
      entityType: 'Public Limited', pan: 'AACEP7890M', status: 'On Hold', picUserId: 'u_solani', micUserId: 'u_desai',
      onboardingDate: '2021-11-01', fyEnd: 'March 31', referenceName: 'Bank Referral', additionalInfo: 'Listed entity on BSE',
      tan: 'MUMA99887C', cin: 'L60200MH2021PLC987654', incorporationDate: '2021-10-10', msmeRegistrationStatus: 'Not Registered',
      industry: 'Logistics', businessActivity: 'Express courier & cargo delivery', listedExchange: 'BSE',
      previousAuditor: 'KPMG India', registeredOfficeAddress: 'Apex House, Vashi, Navi Mumbai - 400703',
      communicationAddress: 'Apex House, Vashi, Navi Mumbai - 400703', billingAddress: 'Apex House, Vashi, Navi Mumbai - 400703',
      isArchived: false
    }
  ];

  // GST Registrations (Max 30 per client)
  window.State.gstRegistrations = [
    { id: 'g_1', clientId: 'c_1', gstin: '27AABCA1234F1Z0', state: 'Maharashtra', status: 'Active' },
    { id: 'g_2', clientId: 'c_1', gstin: '24AABCA1234F2Z5', state: 'Gujarat', status: 'Active' },
    { id: 'g_3', clientId: 'c_2', gstin: '07ABBCH5678G1Z1', state: 'Delhi', status: 'Active' },
    { id: 'g_4', clientId: 'c_5', gstin: '27AACEP7890M1Z2', state: 'Maharashtra', status: 'Active' },
    { id: 'g_5', clientId: 'c_5', gstin: '29AACEP7890M3Z6', state: 'Karnataka', status: 'Suspended' }
  ];

  // Contacts
  window.State.contacts = [
    { id: 'con_1', clientId: 'c_1', name: 'Ramesh Sawant', designation: 'CFO', email: 'ramesh@acmecorp.com', mobile: '9820098200', isPrimary: true },
    { id: 'con_2', clientId: 'c_1', name: 'Shreya Kapoor', designation: 'Accounts Manager', email: 'shreya@acmecorp.com', mobile: '9819998199', isPrimary: false },
    { id: 'con_3', clientId: 'c_2', name: 'R. K. Bhaskar', designation: 'Managing Partner', email: 'rk@bhaskarglobal.com', mobile: '9930099300', isPrimary: true },
    { id: 'con_4', clientId: 'c_3', name: 'Praveen Shah', designation: 'Partner', email: 'praveen@zionretail.com', mobile: '9004490044', isPrimary: true },
    { id: 'con_5', clientId: 'c_4', name: 'Devendra Kumar', designation: 'Karta', email: 'devendra@dkhuf.com', mobile: '9821098210', isPrimary: true },
    { id: 'con_6', clientId: 'c_5', name: 'Nikhil Sen', designation: 'Compliance Officer', email: 'cs@apexlogistics.com', mobile: '9822098220', isPrimary: true }
  ];

  // Services & Engagements
  window.State.engagements = [
    { id: 'e_1', clientId: 'c_1', serviceId: 'stat_audit', picUserId: 'u_solani', micUserId: 'u_desai', teamUserIds: ['u_patel', 'u_joshi'], agreedFee: 150000, frequency: 'Annual' },
    { id: 'e_2', clientId: 'c_1', serviceId: 'gst_3b', picUserId: 'u_solani', micUserId: 'u_mehta', teamUserIds: ['u_shah'], agreedFee: 20000, frequency: 'Monthly' },
    { id: 'e_3', clientId: 'c_2', serviceId: 'tax_annual', picUserId: 'u_munjal', micUserId: 'u_mehta', teamUserIds: ['u_shah'], agreedFee: 80000, frequency: 'Annual' },
    { id: 'e_4', clientId: 'c_4', serviceId: 'stat_audit', picUserId: 'u_munjal', micUserId: 'u_desai', teamUserIds: ['u_patel'], agreedFee: 50000, frequency: 'Annual' },
    { id: 'e_5', clientId: 'c_5', serviceId: 'stat_audit', picUserId: 'u_solani', micUserId: 'u_desai', teamUserIds: ['u_patel', 'u_joshi'], agreedFee: 300000, frequency: 'Annual' }
  ];

  // Critical Alerts / Notifications
  window.State.notifications = [
    { id: 'n_1', type: 'Filing Delay', title: 'GST Filing Overdue', desc: 'Bhaskar Global LLP GST Return (GSTR-3B) is overdue for July 2026.', managerId: 'u_mehta', isCritical: true, clientName: 'Bhaskar Global LLP' },
    { id: 'n_2', type: 'Timesheet Delay', title: 'Timesheet Submission Pending', desc: 'Karan Joshi timesheet for week ending 08-Aug-2026 is pending approval.', managerId: 'u_desai', isCritical: true, clientName: 'SSA Internal' },
    { id: 'n_3', type: 'Filing Delay', title: 'Income Tax Return Pending', desc: 'Acme Corporation Tax Audit filing is scheduled. Prev Auditor report is missing.', managerId: 'u_desai', isCritical: false, clientName: 'Acme Corporation Private Limited' }
  ];

  // Daily Timesheets Mock Data
  window.State.timesheets = [
    { id: 'ts_1', employeeId: 'u_patel', date: '2026-08-19', clientId: 'c_1', serviceId: 'stat_audit', hours: 8, description: 'Vouching purchase book invoices', status: 'Approved' },
    { id: 'ts_2', employeeId: 'u_patel', date: '2026-08-20', clientId: 'c_1', serviceId: 'stat_audit', hours: 7, description: 'Investigating outstanding debtors balance details', status: 'Approved' },
    { id: 'ts_3', employeeId: 'u_shah', date: '2026-08-20', clientId: 'c_2', serviceId: 'gst_3b', hours: 6, description: 'Reviewing Input Tax Credit ledgers matching', status: 'Approved' },
    { id: 'ts_4', employeeId: 'u_joshi', date: '2026-08-20', clientId: 'c_5', serviceId: 'stat_audit', hours: 8, description: 'Physical verification of inventory list', status: 'Approved' },
    { id: 'ts_pending_1', employeeId: 'u_patel', date: '2026-08-21', clientId: 'c_1', serviceId: 'stat_audit', hours: 8, description: 'Pending approval test: internal ledger audit', status: 'Pending' },
    { id: 'ts_pending_2', employeeId: 'u_joshi', date: '2026-08-21', clientId: 'c_5', serviceId: 'stat_audit', hours: 6, description: 'Pending approval test: client queries preparation', status: 'Pending' }
  ];

  // Seed Jobs/Tasks Mock Data
  window.State.jobs = [
    { id: 'job_1', title: 'Statutory Audit FY 2025-26', clientId: 'c_1', serviceId: 'stat_audit', assignedUserId: 'u_desai', picUserId: 'u_solani', micUserId: 'u_desai', priority: 'High', dueDate: '2026-09-30', status: 'In Progress', completionDate: '' },
    { id: 'job_2', title: 'GSTR-3B July Filing', clientId: 'c_2', serviceId: 'gst_3b', assignedUserId: 'u_shah', picUserId: 'u_munjal', micUserId: 'u_mehta', priority: 'Very Urgent', dueDate: '2026-08-20', status: 'To Do', completionDate: '' },
    { id: 'job_3', title: 'Income Tax Annual Return FY 2025-26', clientId: 'c_1', serviceId: 'tax_annual', assignedUserId: 'u_patel', picUserId: 'u_solani', micUserId: 'u_desai', priority: 'Moderate', dueDate: '2026-07-31', status: 'Completed', completionDate: '2026-08-15' },
    { id: 'job_4', title: 'Net Worth Certificate for Visa', clientId: 'c_3', serviceId: 'certificates', assignedUserId: 'u_mehta', picUserId: 'u_solani', micUserId: 'u_mehta', priority: 'Urgent', dueDate: '2026-08-28', status: 'Under Review', completionDate: '' }
  ];

  window.State.activeUserId = 'u_solani';
  window.rebuildServicesMap();
  window.saveState();
}

// ACCESS MANAGEMENT SYSTEM (RBAC)
window.getCurrentActiveUser = function() {
  const activeUserId = window.State.activeUserId;
  if (!activeUserId) return null;
  return (window.State.team || []).find(t => t.id === activeUserId) || null;
};

window.checkAuthenticationStatus = function() {
  const overlay = document.getElementById('login-overlay');
  if (!overlay) return;

  const user = window.getCurrentActiveUser();
  if (user) {
    overlay.style.display = 'none';
    
    // Sync UI states
    window.updateProfileSwitcherSelector();
    window.applyRoleAccessControls();
  } else {
    overlay.style.display = 'flex';
    
    // Populate user select dropdown
    const selectEl = document.getElementById('login-user-select');
    if (selectEl) {
      const activeTeam = (window.State.team || []).filter(t => t.status === 'Active');
      selectEl.innerHTML = activeTeam.map(t => `<option value="${t.id}">${t.name} (${t.role === 'super_admin' ? 'Partner' : t.role === 'manager' ? 'Manager' : 'Staff'})</option>`).join('');
      // Show user photo card for the initially selected user
      if (activeTeam.length > 0) setTimeout(() => window.onLoginUserChange && window.onLoginUserChange(activeTeam[0].id), 0);
    }
    
    // Focus password
    const pwdEl = document.getElementById('login-password');
    if (pwdEl) {
      pwdEl.value = '';
      pwdEl.focus();
    }
    
    const errorEl = document.getElementById('login-error-msg');
    if (errorEl) errorEl.style.display = 'none';
  }
};

window.handleLoginSubmit = function(event) {
  event.preventDefault();
  
  const userId = document.getElementById('login-user-select').value;
  const enteredPwd = document.getElementById('login-password').value;
  const errorEl = document.getElementById('login-error-msg');
  
  const user = (window.State.team || []).find(t => t.id === userId);
  if (!user) return;
  
  const storedHash = user.passwordHash || btoa('password123');
  const enteredHash = btoa(enteredPwd);
  
  if (enteredHash === storedHash) {
    window.State.activeUserId = userId;
    window.saveState();
    
    // Authenticate and redirect to dashboard
    window.checkAuthenticationStatus();
    window.navigateModule('dashboard');
  } else {
    if (errorEl) errorEl.style.display = 'block';
  }
};

window.handleLogout = function() {
  if (!confirm("Are you sure you want to log out of the compliance portal?")) return;
  window.State.activeUserId = null;
  window.saveState();
  window.checkAuthenticationStatus();
};

// ─── OTP State (in-memory + sessionStorage, never persisted to State) ────────
let _otpTargetUserId = null;

window.showLoginStep = function(step) {
  [1, 2, 3].forEach(n => {
    const el = document.getElementById(`login-step-${n}`);
    if (el) el.style.display = n === step ? 'block' : 'none';
  });
};

window.showForgotPassword = function() {
  const selectEl = document.getElementById('otp-user-select');
  if (selectEl) {
    const activeTeam = (window.State.team || []).filter(t => t.status === 'Active');
    selectEl.innerHTML = activeTeam.map(t => `<option value="${t.id}">${t.name} (${t.roleLabel || t.role})</option>`).join('');
    selectEl.onchange = () => _updateOtpMobilePreview(selectEl.value);
    _updateOtpMobilePreview(selectEl.value);
  }
  window.showLoginStep(2);
};

function _updateOtpMobilePreview(userId) {
  const user = (window.State.team || []).find(t => t.id === userId);
  const previewEl = document.getElementById('otp-mobile-preview');
  const warnEl    = document.getElementById('otp-no-mobile-warn');
  const maskedEl  = document.getElementById('otp-mobile-masked');
  if (!user || !previewEl || !warnEl) return;
  if (user.mobile && user.mobile.length >= 6) {
    const masked = '****' + user.mobile.slice(-4);
    if (maskedEl) maskedEl.textContent = masked;
    previewEl.style.display = 'block';
    warnEl.style.display    = 'none';
  } else {
    previewEl.style.display = 'none';
    warnEl.style.display    = 'block';
  }
}

window.sendOtp = function() {
  const selectEl = document.getElementById('otp-user-select');
  if (!selectEl) return;
  const userId = selectEl.value;
  const user = (window.State.team || []).find(t => t.id === userId);
  if (!user) { alert('Please select a valid user.'); return; }
  if (!user.mobile || user.mobile.length < 6) {
    alert('No mobile number registered for this account. Please contact a Partner.');
    return;
  }

  // Generate 6-digit OTP
  const otp = String(Math.floor(100000 + Math.random() * 900000));
  const expiry = Date.now() + 5 * 60 * 1000; // 5 minutes

  // Store in sessionStorage (not State/localStorage)
  sessionStorage.setItem('_ssa_otp', JSON.stringify({ otp, userId, expiry }));
  _otpTargetUserId = userId;

  // Show OTP demo value
  const demoValEl = document.getElementById('otp-demo-value');
  if (demoValEl) demoValEl.textContent = otp;

  window.showLoginStep(3);
  const otpInput = document.getElementById('otp-input');
  if (otpInput) { otpInput.value = ''; otpInput.focus(); }
  const errEl = document.getElementById('otp-error-msg');
  if (errEl) errEl.style.display = 'none';
};

window.verifyOtpAndReset = function() {
  const errEl   = document.getElementById('otp-error-msg');
  const otpVal  = (document.getElementById('otp-input')?.value || '').trim();
  const newPwd  = document.getElementById('otp-new-pwd')?.value || '';
  const newPwd2 = document.getElementById('otp-new-pwd2')?.value || '';

  function showErr(msg) {
    if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
  }

  // Validate fields
  if (!otpVal) { showErr('Please enter the OTP.'); return; }
  if (!newPwd) { showErr('Please enter a new password.'); return; }
  if (newPwd.length < 8) { showErr('Password must be at least 8 characters.'); return; }
  if (newPwd !== newPwd2) { showErr('Passwords do not match.'); return; }

  // Check sessionStorage OTP
  let stored = null;
  try { stored = JSON.parse(sessionStorage.getItem('_ssa_otp') || 'null'); } catch(e) {}
  if (!stored) { showErr('OTP session expired or invalid. Please request a new OTP.'); return; }
  if (Date.now() > stored.expiry) {
    sessionStorage.removeItem('_ssa_otp');
    showErr('OTP has expired. Please go back and request a new one.');
    return;
  }
  if (stored.otp !== otpVal) { showErr('Incorrect OTP. Please try again.'); return; }

  // OTP valid — update password
  const user = (window.State.team || []).find(t => t.id === stored.userId);
  if (!user) { showErr('User not found. Please try again.'); return; }
  user.passwordHash = btoa(newPwd);
  window.saveState();

  // Clear OTP
  sessionStorage.removeItem('_ssa_otp');
  _otpTargetUserId = null;

  // Return to login with success message
  window.showLoginStep(1);
  const loginSelect = document.getElementById('login-user-select');
  if (loginSelect) loginSelect.value = stored.userId;
  const errLoginEl = document.getElementById('login-error-msg');
  if (errLoginEl) {
    errLoginEl.style.color = '#2ecc71';
    errLoginEl.textContent = '✅ Password reset successfully! Please log in with your new password.';
    errLoginEl.style.display = 'block';
    setTimeout(() => {
      errLoginEl.style.color = '#e74c3c';
      errLoginEl.textContent = 'Incorrect password. Please try again.';
      errLoginEl.style.display = 'none';
    }, 5000);
  }
  onLoginUserChange(stored.userId);
};

window.onLoginUserChange = function(userId) {
  const user = (window.State.team || []).find(t => t.id === userId);
  const photoRow    = document.getElementById('login-user-photo-row');
  const avatarEl    = document.getElementById('login-user-avatar');
  const nameEl      = document.getElementById('login-user-name');
  const roleEl      = document.getElementById('login-user-role');
  if (!user || !photoRow) return;
  photoRow.style.display = 'flex';
  if (nameEl) nameEl.textContent = user.name;
  if (roleEl) roleEl.textContent = user.designation || user.roleLabel || '';
  if (avatarEl) {
    if (user.photo) {
      avatarEl.innerHTML = `<img src="${user.photo}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
    } else {
      const initials = user.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
      avatarEl.textContent = initials;
      avatarEl.style.background = 'linear-gradient(135deg,#2563eb,#1d4ed8)';
    }
  }
};

window.updateProfileSwitcherSelector = function() {
  const selectEl = document.getElementById('user-profile-switcher');
  if (!selectEl) return;

  const team = window.State.team || [];
  const activeUserId = window.State.activeUserId || '';

  selectEl.innerHTML = team
    .filter(t => t.status === 'Active')
    .map(t => `<option value="${t.id}" ${t.id === activeUserId ? 'selected' : ''}>${t.name} (${t.role === 'super_admin' ? 'Partner' : t.role === 'manager' ? 'Manager' : 'Staff'})</option>`)
    .join('');
};

window.onSwitchActiveUser = function(userId) {
  // A profile change must not become an authentication bypass.  The selected
  // user is preselected on the login form, where their password is still
  // required before the session is changed.
  if (userId && userId !== window.State.activeUserId) {
    window.State.activeUserId = null;
    window.saveState();
    window.checkAuthenticationStatus();
    const loginSelect = document.getElementById('login-user-select');
    if (loginSelect) loginSelect.value = userId;
    return;
  }

  window.State.activeUserId = userId;
  window.saveState();

  // If the user was on a tab they no longer have access to, redirect them to dashboard
  const user = window.getCurrentActiveUser();
  if (!user) {
    window.checkAuthenticationStatus();
    return;
  }
  const currentTab = window.currentModule;

  // Sync menu visibility and UI state immediately
  window.applyRoleAccessControls();

  if (user.role === 'staff' && ['team', 'services', 'reports'].includes(currentTab)) {
    window.navigateModule('dashboard');
    alert(`Access Denied: Redirected to Dashboard (active role is Staff).`);
  } else if (user.role === 'manager' && ['services', 'reports'].includes(currentTab)) {
    window.navigateModule('dashboard');
    alert(`Access Denied: Redirected to Dashboard (active role is Manager).`);
  } else {
    // Just refresh the current module to apply local access masks
    window.navigateModule(window.currentModule);
  }
};

window.applyRoleAccessControls = function() {
  const user = window.getCurrentActiveUser();

  // Update switcher selection if out of sync
  const switcher = document.getElementById('user-profile-switcher');
  if (switcher && switcher.value !== user.id) {
    switcher.value = user.id;
  }

  // 1. Show / Hide Sidebar Navigation Links based on role permissions
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(el => {
    const modName = el.getAttribute('data-module');
    if (user.role === 'staff') {
      if (['team', 'services', 'reports'].includes(modName)) {
        el.style.display = 'none';
      } else {
        el.style.display = 'flex';
      }
    } else if (user.role === 'manager') {
      if (['services', 'reports'].includes(modName)) {
        el.style.display = 'none';
      } else {
        el.style.display = 'flex';
      }
    } else {
      el.style.display = 'flex';
    }
  });
};

// ROUTER SYSTEM
window.currentModule = 'dashboard';
window.currentSubTab = '';

window.navigateModule = function(moduleName) {
  const user = window.getCurrentActiveUser();
  if (!user) {
    if (window.checkAuthenticationStatus) window.checkAuthenticationStatus();
    return;
  }

  // Sync sidebar navigation link visibility
  if (window.applyRoleAccessControls) window.applyRoleAccessControls();

  let targetModule = moduleName;

  // Block access depending on system roles
  if (user.role === 'staff' && ['team', 'services', 'reports'].includes(moduleName)) {
    targetModule = 'dashboard';
    alert(`Access Restricted: Staff role cannot access the "${moduleName}" module.`);
  } else if (user.role === 'manager' && ['services', 'reports'].includes(moduleName)) {
    targetModule = 'dashboard';
    alert(`Access Restricted: Manager role cannot access the "${moduleName}" module.`);
  }

  window.currentModule = targetModule;
  document.body.setAttribute('data-active-module', targetModule);
  
  // Update sidebar active link
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.remove('active');
    if (el.getAttribute('data-module') === targetModule) {
      el.classList.add('active');
    }
  });

  // Switch workspace view panels
  document.querySelectorAll('.module-view').forEach(el => {
    el.classList.remove('active');
  });
  const activeView = document.getElementById(`view-${targetModule}`);
  if (activeView) activeView.classList.add('active');

  // Change workspace headers
  updateHeader(targetModule);

  // Trigger module-specific layout renderers
  if (targetModule === 'dashboard') {
    renderDashboard();
  } else if (targetModule === 'clients') {
    if (window.initClientsModule) window.initClientsModule();
  } else if (targetModule === 'team') {
    if (window.initTeamModule) window.initTeamModule();
  } else if (targetModule === 'services') {
    renderServicesCatalogue();
  } else if (targetModule === 'timesheets') {
    renderTimesheetsSkeleton();
  } else if (targetModule === 'jobs') {
    renderJobsModule();
  } else if (targetModule === 'reports') {
    renderReportsSkeleton();
  }
};

function updateHeader(module) {
  const titles = {
    dashboard: { title: 'Practice Flow Dashboard', subtitle: 'Aggregated analytics and tracking indices' },
    clients: { title: 'Clients Master Directory', subtitle: 'Onboard, structure, audit, and reassign clients' },
    team: { title: 'Team Roster & Workload', subtitle: 'Employee matrix, capacities, and organization hierarchies' },
    services: { title: 'Service Master Catalogue', subtitle: 'Corporate, taxation, audit, and advisory scope settings' },
    timesheets: { title: 'Timesheet Capacity Tracker', subtitle: 'Resource hours logged against billing rates' },
    jobs: { title: 'Jobs & Tasks Tracker Board', subtitle: 'Manage, assign, and track compliance filing workflows' },
    reports: { title: 'Executive Operations Reports', subtitle: 'Realized cost metrics and filing statistics' }
  };
  const titleData = titles[module] || { title: 'Firm Management System', subtitle: 'Sheth Solani & Associates' };
  document.getElementById('header-title').textContent = titleData.title;
  document.getElementById('header-subtitle').textContent = titleData.subtitle;
}

function renderServicesCatalogue() {
  const container = document.getElementById('view-services');
  if (!container) return;

  const services = window.State.services || [];
  const frequencyCounts = services.reduce((counts, service) => {
    const frequency = String(service.defaultFreq || 'One-time').toLowerCase();
    counts[frequency] = (counts[frequency] || 0) + 1;
    return counts;
  }, {});

  const serviceVisual = (service) => {
    const text = `${service.id || ''} ${service.name || ''}`.toLowerCase();
    if (text.includes('gst') || text.includes('indirect')) {
      return { label: 'Indirect tax', icon: '↗', colour: '#16a7d8', soft: 'rgba(22, 167, 216, 0.14)' };
    }
    if (text.includes('audit') || text.includes('assurance')) {
      return { label: 'Assurance', icon: '✓', colour: '#8b5cf6', soft: 'rgba(139, 92, 246, 0.14)' };
    }
    if (text.includes('tax') || text.includes('tds') || text.includes('income')) {
      return { label: 'Direct tax', icon: '₹', colour: '#d99017', soft: 'rgba(217, 144, 23, 0.15)' };
    }
    if (text.includes('roc') || text.includes('company') || text.includes('compliance')) {
      return { label: 'Compliance', icon: '◆', colour: '#15a46a', soft: 'rgba(21, 164, 106, 0.14)' };
    }
    return { label: 'Advisory', icon: '✦', colour: '#e05b69', soft: 'rgba(224, 91, 105, 0.14)' };
  };

  const annualisedFee = (service) => {
    const fee = Number(service.baselineFee || 0);
    const frequency = String(service.defaultFreq || '').toLowerCase();
    if (frequency === 'monthly') return fee * 12;
    if (frequency === 'quarterly') return fee * 4;
    return fee;
  };

  container.innerHTML = `
    <div class="services-workspace">
      <section class="services-hero" aria-label="Service catalogue summary">
        <div class="services-hero-copy">
          <span class="services-eyebrow">Firm service library</span>
          <h2>Build every engagement from a clear, consistent service catalogue.</h2>
          <p>Set standard frequency and fee benchmarks once, then use them consistently across client onboarding and planning.</p>
        </div>
        <div class="service-metrics" aria-label="Service catalogue metrics">
          <div class="service-metric">
            <span>Active services</span>
            <strong>${services.length}</strong>
          </div>
          <div class="service-metric">
            <span>Recurring</span>
            <strong>${(frequencyCounts.monthly || 0) + (frequencyCounts.quarterly || 0) + (frequencyCounts.annual || 0)}</strong>
          </div>
          <div class="service-metric">
            <span>One-time</span>
            <strong>${frequencyCounts['one-time'] || 0}</strong>
          </div>
        </div>
      </section>

      <div class="services-layout">
        <section class="services-catalogue-panel">
          <div class="services-catalogue-heading">
            <div>
              <span class="services-eyebrow">Catalogue</span>
              <h3>Available service types</h3>
              <p>Each card provides the standard delivery rhythm and fee reference for your team.</p>
            </div>
            <span class="service-count-pill">${services.length} configured</span>
          </div>

          <div class="service-catalogue-grid">
            ${services.map(service => {
              const serviceConfig = window.getServiceConfiguration ? window.getServiceConfiguration(service) : service;
              const visual = serviceVisual(service);
              const annualValue = annualisedFee(serviceConfig);
              const budgetLines = Array.isArray(serviceConfig.baselineBudget) ? serviceConfig.baselineBudget : [];
              const deliveryBudget = budgetLines.reduce((total, line) => total + Number(line.estimatedCost || 0), 0);
              return `
                <article class="service-catalogue-item" style="--service-colour: ${visual.colour}; --service-soft: ${visual.soft};">
                  <div class="service-card-topline">
                    <span class="service-icon" aria-hidden="true">${visual.icon}</span>
                    <span class="service-category">${visual.label}</span>
                  </div>
                  <div class="service-card-title">
                    <code>${service.id}</code>
                    <h4>${serviceConfig.name}</h4>
                  </div>
                  <div class="service-card-details">
                    <div>
                      <span>Delivery rhythm</span>
                      <strong>${serviceConfig.defaultFreq || 'One-time'}</strong>
                    </div>
                    <div>
                      <span>Baseline fee</span>
                      <strong>₹${Number(serviceConfig.baselineFee || 0).toLocaleString('en-IN')}</strong>
                    </div>
                  </div>
                  <div class="service-card-footer">
                    <span>${String(serviceConfig.defaultFreq || '').toLowerCase() === 'one-time' ? 'One engagement fee' : 'Estimated annual value'}</span>
                    <strong>₹${annualValue.toLocaleString('en-IN')}</strong>
                  </div>
                  <button type="button" class="service-budget-link" onclick="openResourceBudgetEditor('service', '${service.id}')"><span>Resource baseline</span><strong>${budgetLines.length ? `₹${deliveryBudget.toLocaleString('en-IN')} / delivery` : 'Set budget'} →</strong></button>
                  <button type="button" class="service-edit-link" onclick="openServiceEditor('${service.id}')"><span>Edit service &amp; view history</span><strong>${(service.changeHistory || []).length} changes →</strong></button>
                </article>`;
            }).join('') || '<div class="service-catalogue-empty">No service types are configured yet. Add your first service from the panel on the right.</div>'}
          </div>
        </section>

        <aside class="service-add-card">
          <div class="service-add-heading">
            <span class="service-add-mark" aria-hidden="true">+</span>
            <div>
              <span class="services-eyebrow">New entry</span>
              <h3>Add a service type</h3>
            </div>
          </div>
          <p class="service-add-intro">Give your team a reliable baseline before the service is assigned to a client.</p>
          <div class="service-add-form">
            <div class="form-group">
              <label class="form-label">Service Name</label>
              <input type="text" id="new-srv-name" class="form-input" placeholder="e.g. Audit Representation">
            </div>
            <div class="form-group">
              <label class="form-label">Default Frequency</label>
              <select id="new-srv-freq" class="form-select">
                <option value="Annual">Annual</option>
                <option value="Quarterly">Quarterly</option>
                <option value="Monthly">Monthly</option>
                <option value="One-time">One-time</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Baseline Fee (INR)</label>
              <input type="number" id="new-srv-fee" class="form-input" placeholder="e.g. 25000">
            </div>
            <button onclick="addServiceTypeCatalogue()" class="btn btn-primary service-register-button">Register service type <span aria-hidden="true">→</span></button>
          </div>
          <div class="service-add-tip"><span aria-hidden="true">✦</span> Use the normal service fee—not a one-off negotiated client fee—as the baseline.</div>
        </aside>
      </div>
    </div>
  `;
}

window.addServiceTypeCatalogue = function() {
  const name = document.getElementById('new-srv-name').value.trim();
  const freq = document.getElementById('new-srv-freq').value;
  const feeVal = parseFloat(document.getElementById('new-srv-fee').value);

  if (!name) {
    alert("Please enter a service name.");
    return;
  }

  if (isNaN(feeVal) || feeVal < 0) {
    alert("Please enter a valid baseline fee.");
    return;
  }

  // Generate simple unique ID code from name
  let generatedId = 'srv_' + name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  
  // Prevent duplicate ID
  const exists = window.State.services.some(s => s.id === generatedId);
  if (exists) {
    generatedId += '_' + Date.now().toString().substring(8);
  }

  window.State.services.push({
    id: generatedId,
    name: name,
    defaultFreq: freq,
    baselineFee: feeVal,
    baselineBudget: []
  });

  window.rebuildServicesMap();
  window.saveState();
  renderServicesCatalogue();

  alert(`Service "${name}" added successfully. Next, add its baseline resource budget.`);
  window.openResourceBudgetEditor('service', generatedId);
};

// Service versions preserve the configuration used in the past and allow a new
// fee, rhythm or baseline to take effect on a clearly recorded date.
window.cloneServiceBudget = function(lines) {
  return (Array.isArray(lines) ? lines : []).map(line => ({ designation: line.designation, estimatedCost: Number(line.estimatedCost || 0) }));
};

window.getServiceConfiguration = function(service, date = window.toLocalISODate()) {
  if (!service) return { name: '', defaultFreq: 'One-time', baselineFee: 0, baselineBudget: [] };
  const baseline = { name: service.name, defaultFreq: service.defaultFreq, baselineFee: Number(service.baselineFee || 0), baselineBudget: window.cloneServiceBudget(service.baselineBudget) };
  const versions = Array.isArray(service.versions) ? service.versions : [];
  const applicable = versions.filter(version => version.effectiveDate <= date).sort((a, b) => `${b.effectiveDate}${b.changedAt || ''}`.localeCompare(`${a.effectiveDate}${a.changedAt || ''}`))[0];
  return applicable?.configuration ? { ...applicable.configuration, baselineBudget: window.cloneServiceBudget(applicable.configuration.baselineBudget) } : baseline;
};

window.recordServiceVersion = function(service, changes, effectiveDate) {
  const user = window.getCurrentActiveUser?.();
  const today = window.toLocalISODate();
  const effective = effectiveDate || today;
  if (!Array.isArray(service.versions) || !service.versions.length) {
    service.versions = [{ id: `service_initial_${service.id}`, effectiveDate: '1900-01-01', changedAt: '', changedById: 'system', changedByName: 'Initial catalogue', configuration: window.getServiceConfiguration(service, '1900-01-01') }];
  }
  const before = window.getServiceConfiguration(service, effective);
  const configuration = { ...before, ...changes, baselineBudget: window.cloneServiceBudget(changes.baselineBudget ?? before.baselineBudget) };
  const changedAt = new Date().toISOString();
  service.versions.push({ id: `service_version_${Date.now()}`, effectiveDate: effective, changedAt, changedById: user?.id || 'system', changedByName: user?.name || 'System', configuration });
  service.versions.sort((a, b) => `${b.effectiveDate}${b.changedAt || ''}`.localeCompare(`${a.effectiveDate}${a.changedAt || ''}`));
  if (!Array.isArray(service.changeHistory)) service.changeHistory = [];
  service.changeHistory.unshift({ effectiveDate: effective, changedAt, changedByName: user?.name || 'System', before, after: configuration });

  // Freeze the old baseline for existing client-service mappings before the
  // catalogue version changes. New mappings use the new effective version.
  (window.State.engagements || []).filter(engagement => engagement.serviceId === service.id && !Array.isArray(engagement.resourceBudget) && !Array.isArray(engagement.baselineBudgetSnapshot)).forEach(engagement => {
    engagement.baselineBudgetSnapshot = window.cloneServiceBudget(before.baselineBudget);
  });

  const activeConfiguration = window.getServiceConfiguration(service, today);
  service.name = activeConfiguration.name;
  service.defaultFreq = activeConfiguration.defaultFreq;
  service.baselineFee = Number(activeConfiguration.baselineFee || 0);
  service.baselineBudget = window.cloneServiceBudget(activeConfiguration.baselineBudget);
};

window.openServiceEditor = function(serviceId) {
  const user = window.getCurrentActiveUser?.();
  if (!user || user.role !== 'super_admin') { alert('Only Partners can edit service types.'); return; }
  const service = (window.State.services || []).find(item => item.id === serviceId);
  if (!service) return;
  const config = window.getServiceConfiguration(service);
  const history = (service.changeHistory || []).slice(0, 8).map(entry => `<li><strong>${entry.effectiveDate}</strong> · ${entry.changedByName}<br><span>${entry.before.name} / ${entry.before.defaultFreq} / ₹${Number(entry.before.baselineFee || 0).toLocaleString('en-IN')} → ${entry.after.name} / ${entry.after.defaultFreq} / ₹${Number(entry.after.baselineFee || 0).toLocaleString('en-IN')}</span></li>`).join('') || '<li>No amendments recorded yet.</li>';
  let modal = document.getElementById('service-editor-modal');
  if (!modal) { modal = document.createElement('div'); modal.id = 'service-editor-modal'; document.body.appendChild(modal); }
  modal.className = 'resource-budget-modal';
  modal.dataset.id = serviceId;
  modal.innerHTML = `<div class="resource-budget-dialog service-editor-dialog" role="dialog" aria-modal="true" aria-label="Edit service type"><div class="resource-budget-dialog-header"><div><span class="services-eyebrow">Versioned service edit</span><h3>Edit ${config.name}</h3><p>Changes apply from the effective date. Existing client-service budget mappings retain their earlier snapshot.</p></div><button type="button" class="budget-modal-close" onclick="closeServiceEditor()" aria-label="Close">×</button></div><div class="service-edit-grid"><div class="form-group"><label class="form-label">Service name</label><input id="service-edit-name" class="form-input" value="${config.name}"></div><div class="form-group"><label class="form-label">Default frequency</label><select id="service-edit-frequency" class="form-select">${['Annual','Quarterly','Monthly','One-time'].map(value => `<option value="${value}" ${config.defaultFreq === value ? 'selected' : ''}>${value}</option>`).join('')}</select></div><div class="form-group"><label class="form-label">Baseline fee (INR)</label><input id="service-edit-fee" type="number" min="0" class="form-input" value="${Number(config.baselineFee || 0)}"></div><div class="form-group"><label class="form-label">Effective from</label><input id="service-edit-effective" type="date" class="form-input" value="${window.toLocalISODate()}"></div></div><details class="service-history"><summary>Change history (${(service.changeHistory || []).length})</summary><ul>${history}</ul></details><div class="budget-editor-actions"><button type="button" class="btn btn-secondary" onclick="closeServiceEditor()">Cancel</button><button type="button" class="btn btn-primary" onclick="saveServiceEditor()">Save version</button></div></div>`;
};

window.closeServiceEditor = function() { document.getElementById('service-editor-modal')?.remove(); };
window.saveServiceEditor = function() {
  const modal = document.getElementById('service-editor-modal');
  const service = (window.State.services || []).find(item => item.id === modal?.dataset.id);
  if (!service) return;
  const name = document.getElementById('service-edit-name').value.trim();
  const baselineFee = Number(document.getElementById('service-edit-fee').value);
  const effectiveDate = document.getElementById('service-edit-effective').value;
  if (!name || !Number.isFinite(baselineFee) || baselineFee < 0 || !effectiveDate) { alert('Enter a service name, a valid fee, and an effective date.'); return; }
  window.recordServiceVersion(service, { name, defaultFreq: document.getElementById('service-edit-frequency').value, baselineFee }, effectiveDate);
  window.rebuildServicesMap(); window.saveState(); window.closeServiceEditor(); renderServicesCatalogue();
};

// Resource budgets are cost plans for a service delivery. A client engagement can
// inherit its service baseline or carry its own explicit override.
window.getBudgetFrequencyMultiplier = function(frequency) {
  const normalized = String(frequency || 'One-time').toLowerCase();
  if (normalized === 'monthly') return 12;
  if (normalized === 'quarterly') return 4;
  return 1;
};

window.getEngagementBudgetLines = function(engagement) {
  if (!engagement) return [];
  if (Array.isArray(engagement.resourceBudget)) return engagement.resourceBudget;
  if (Array.isArray(engagement.baselineBudgetSnapshot)) return engagement.baselineBudgetSnapshot;
  const service = (window.State.services || []).find(item => item.id === engagement.serviceId);
  return window.cloneServiceBudget(window.getServiceConfiguration(service).baselineBudget);
};

window.getEngagementBudgetCost = function(engagement, annualized = true) {
  const deliveryCost = window.getEngagementBudgetLines(engagement).reduce((sum, line) => sum + Number(line.estimatedCost || 0), 0);
  return annualized ? deliveryCost * window.getBudgetFrequencyMultiplier(engagement?.frequency) : deliveryCost;
};

window.openResourceBudgetEditor = function(target, id) {
  const user = window.getCurrentActiveUser?.();
  if (!user || user.role !== 'super_admin') { alert('Only Partners can edit resource budgets.'); return; }
  const isService = target === 'service';
  const item = isService ? (window.State.services || []).find(service => service.id === id) : (window.State.engagements || []).find(engagement => engagement.id === id);
  if (!item) return;

  const service = isService ? item : (window.State.services || []).find(entry => entry.id === item.serviceId);
  const client = !isService ? (window.State.clients || []).find(entry => entry.id === item.clientId) : null;
  const title = isService ? item.name : `${client?.name || 'Client'} · ${service?.name || item.serviceId}`;
  const sourceLines = isService ? window.getServiceConfiguration(item).baselineBudget : (Array.isArray(item.resourceBudget) ? item.resourceBudget : window.getEngagementBudgetLines(item));
  const designations = [...new Set((window.State.team || []).filter(member => member.status === 'Active').map(member => member.designation).filter(Boolean))];
  const options = designations.map(designation => `<option value="${designation}">${designation}</option>`).join('');
  const renderRow = (line = {}) => `<div class="budget-editor-row"><select class="budget-line-designation form-select"><option value="">Select designation</option>${designations.map(designation => `<option value="${designation}" ${line.designation === designation ? 'selected' : ''}>${designation}</option>`).join('')}</select><div class="budget-cost-input"><span>₹</span><input type="number" min="0" step="1" class="budget-line-cost form-input" value="${Number(line.estimatedCost || 0)}" placeholder="Estimated cost"></div><button type="button" class="budget-row-remove" onclick="this.closest('.budget-editor-row').remove()" aria-label="Remove budget line">×</button></div>`;

  let modal = document.getElementById('resource-budget-modal');
  if (!modal) { modal = document.createElement('div'); modal.id = 'resource-budget-modal'; document.body.appendChild(modal); }
  modal.dataset.target = isService ? 'service' : 'engagement';
  modal.dataset.id = id;
  modal.className = 'resource-budget-modal';
  modal.innerHTML = `<div class="resource-budget-dialog" role="dialog" aria-modal="true" aria-label="Resource budget editor"><div class="resource-budget-dialog-header"><div><span class="services-eyebrow">${isService ? 'Service baseline' : 'Client-service override'}</span><h3>${title}</h3><p>${isService ? 'Set the default delivery cost by designation. This will flow into new client-service mappings.' : 'This mapping overrides the service baseline for this client and service only.'}</p></div><button type="button" class="budget-modal-close" onclick="closeResourceBudgetEditor()" aria-label="Close">×</button></div>${isService ? `<div class="form-group budget-effective-date"><label class="form-label">Budget change effective from</label><input id="budget-edit-effective" type="date" class="form-input" value="${window.toLocalISODate()}"></div>` : ''}<div class="budget-editor-labels"><span>Designation</span><span>Estimated cost per delivery</span><span></span></div><div id="budget-editor-lines" class="budget-editor-lines">${sourceLines.map(renderRow).join('') || renderRow()}</div><button type="button" class="budget-add-line" onclick="addResourceBudgetLine()">+ Add designation</button><div class="budget-editor-total"><span>Estimated cost per delivery</span><strong id="budget-editor-total">₹0</strong></div><div class="budget-editor-actions"><button type="button" class="btn btn-secondary" onclick="closeResourceBudgetEditor()">Cancel</button><button type="button" class="btn btn-primary" onclick="saveResourceBudgetEditor()">Save budget mapping</button></div></div>`;
  window.budgetEditorDesignationOptions = options;
  window.updateResourceBudgetTotal();
};

window.addResourceBudgetLine = function() {
  const lines = document.getElementById('budget-editor-lines');
  if (!lines) return;
  lines.insertAdjacentHTML('beforeend', `<div class="budget-editor-row"><select class="budget-line-designation form-select"><option value="">Select designation</option>${window.budgetEditorDesignationOptions || ''}</select><div class="budget-cost-input"><span>₹</span><input type="number" min="0" step="1" class="budget-line-cost form-input" value="0" placeholder="Estimated cost"></div><button type="button" class="budget-row-remove" onclick="this.closest('.budget-editor-row').remove()" aria-label="Remove budget line">×</button></div>`);
  window.updateResourceBudgetTotal();
};

window.updateResourceBudgetTotal = function() {
  const total = [...document.querySelectorAll('.budget-line-cost')].reduce((sum, input) => sum + Number(input.value || 0), 0);
  const totalEl = document.getElementById('budget-editor-total');
  if (totalEl) totalEl.textContent = `₹${total.toLocaleString('en-IN')}`;
};

document.addEventListener('input', event => { if (event.target.classList?.contains('budget-line-cost')) window.updateResourceBudgetTotal(); });
window.closeResourceBudgetEditor = function() { document.getElementById('resource-budget-modal')?.remove(); };

window.saveResourceBudgetEditor = function() {
  const modal = document.getElementById('resource-budget-modal');
  const user = window.getCurrentActiveUser?.();
  if (!modal || !user || user.role !== 'super_admin') return;
  const lines = [...modal.querySelectorAll('.budget-editor-row')].map(row => ({ designation: row.querySelector('.budget-line-designation')?.value || '', estimatedCost: Number(row.querySelector('.budget-line-cost')?.value || 0) })).filter(line => line.designation && Number.isFinite(line.estimatedCost) && line.estimatedCost >= 0);
  if (lines.some((line, index) => lines.findIndex(other => other.designation === line.designation) !== index)) { alert('Use each designation only once in a budget mapping.'); return; }
  if (!lines.length) { alert('Add at least one designation and estimated cost.'); return; }

  if (modal.dataset.target === 'service') {
    const service = (window.State.services || []).find(item => item.id === modal.dataset.id);
    if (!service) return;
    const effectiveDate = document.getElementById('budget-edit-effective')?.value;
    if (!effectiveDate) { alert('Select the date from which this budget applies.'); return; }
    window.recordServiceVersion(service, { baselineBudget: lines }, effectiveDate);
    window.saveState(); window.closeResourceBudgetEditor(); renderServicesCatalogue();
  } else {
    const engagement = (window.State.engagements || []).find(item => item.id === modal.dataset.id);
    if (!engagement) return;
    engagement.resourceBudget = lines;
    window.saveState(); window.closeResourceBudgetEditor();
    if (typeof window.switchProfileSubTab === 'function') window.switchProfileSubTab('services');
  }
  if (window.renderDashboard) window.renderDashboard();
};

// INTERACTIVE DAILY TIMESHEET LOGGER MODULE
let activeTimesheetEmpId = '';

window.renderTimesheetsSkeleton = function() {
  const container = document.getElementById('view-timesheets');
  if (!container) return;

  const user = window.getCurrentActiveUser();

  // If user is staff, force activeTimesheetEmpId to be their own user ID
  if (user.role === 'staff') {
    activeTimesheetEmpId = user.id;
  } else if (!activeTimesheetEmpId) {
    const activeTeam = window.State.team.filter(t => t.status === 'Active');
    if (activeTeam.length > 0) activeTimesheetEmpId = activeTeam[0].id;
  }

  const selectedEmp = window.State.team.find(t => t.id === activeTimesheetEmpId);

  // Re-render UI structure
  container.innerHTML = `
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h3 class="card-title">Daily Timesheet Capacity Logging</h3>
          <p style="font-size:12px; color: var(--text-muted); margin-top:2px;">Select an employee to log or view daily timesheet activities.</p>
        </div>
        <div style="display: flex; gap: 12px; align-items: center;">
          <span style="font-size: 13px; color: var(--text-muted); font-weight: 600;">Active Employee:</span>
          <select id="ts-emp-select" onchange="onTimesheetEmpChange(this.value)" class="select-filter" style="min-width: 220px;"></select>
        </div>
      </div>
      <div class="card-body">
        <div id="ts-stats-cards" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;"></div>
        
        <div style="display: grid; grid-template-columns: 1.2fr 2fr; gap: 24px;">
          <!-- Daily logging Form -->
          <div class="card" style="border: 1px solid var(--border-color); background: rgba(0,0,0,0.01);">
            <div class="card-header">
              <h4 style="font-size: 14px; font-weight: 700;">Log Daily Time Entry</h4>
            </div>
            <div class="card-body" style="padding: 16px;">
              <form id="ts-log-form" onsubmit="saveTimesheetEntry(event)" style="display: flex; flex-direction: column; gap: 14px;">
                <div class="form-group">
                  <label class="form-label">Date *</label>
                  <input type="date" id="ts-date" class="form-input" required>
                </div>
                <div class="form-group">
                  <label class="form-label">Client Association *</label>
                  <select id="ts-client" onchange="onTimesheetClientChange(this.value)" class="form-select" required>
                    <option value="">— Select Client —</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Service Context *</label>
                  <select id="ts-service" class="form-select" required>
                    <option value="">— Select Service —</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">Hours Spent *</label>
                  <input type="number" id="ts-hours" class="form-input" min="0.5" max="24" step="0.5" placeholder="e.g. 7.5" required>
                </div>
                <div class="form-group">
                  <label class="form-label">Description of Work Done *</label>
                  <textarea id="ts-description" class="form-textarea" rows="3" placeholder="Explain the tasks completed during these hours..." required></textarea>
                </div>
                <button type="submit" class="btn btn-accent" style="width: 100%; justify-content: center; margin-top: 10px;">💾 Log Daily Entry</button>
              </form>
            </div>
          </div>

          <!-- Timesheet Ledger -->
          <div>
            <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; display:flex; justify-content:space-between; align-items:center;">
              <span>Timesheet Ledger for ${selectedEmp ? selectedEmp.name : 'Selected Resource'}</span>
              <span id="ts-total-badge" class="badge badge-staff">Total: 0 hrs</span>
            </h4>
            <div class="table-responsive">
              <table class="custom-table" style="font-size: 13px;">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Client</th>
                    <th>Service Context</th>
                    <th>Hours</th>
                    <th>Work Done</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody id="ts-ledger-body"></tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Pending Timesheet Approvals Card for Partners & Managers -->
    <div id="ts-approvals-card" class="card" style="margin-top: 24px; display: none;">
      <div class="card-header">
        <h3 class="card-title">Pending Timesheet Approvals Queue</h3>
      </div>
      <div class="card-body">
        <div class="table-responsive">
          <table class="custom-table" style="font-size: 13px;">
            <thead>
              <tr>
                <th>Resource Name</th>
                <th>Date</th>
                <th>Client / Service Context</th>
                <th>Hours Logged</th>
                <th>Description of Activity</th>
                <th style="width: 140px; text-align: right;">Actions</th>
              </tr>
            </thead>
            <tbody id="ts-approvals-body"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  // Set default date in form to today
  document.getElementById('ts-date').value = window.toLocalISODate();

  populateTimesheetEmployeeSelect();
  populateTimesheetClientSelect();
  renderTimesheetStats();
  renderTimesheetLedger();
  renderTimesheetApprovalsQueue();
};

window.onTimesheetEmpChange = function(empId) {
  activeTimesheetEmpId = empId;
  renderTimesheetsSkeleton();
};

function populateTimesheetEmployeeSelect() {
  const sel = document.getElementById('ts-emp-select');
  if (!sel) return;
  const activeTeam = window.State.team.filter(t => t.status === 'Active');
  sel.innerHTML = activeTeam.map(t => `<option value="${t.id}" ${t.id === activeTimesheetEmpId ? 'selected' : ''}>${t.name} (${t.designation})</option>`).join('');

  // Lock dropdown if active user is staff
  const user = window.getCurrentActiveUser();
  if (user.role === 'staff') {
    sel.disabled = true;
  } else {
    sel.disabled = false;
  }
}

function populateTimesheetClientSelect() {
  const sel = document.getElementById('ts-client');
  if (!sel) return;
  const activeClients = window.State.clients.filter(c => !c.isArchived && c.status === 'Active');
  sel.innerHTML = `<option value="">— Select Client —</option>` + 
    activeClients.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
}

window.onTimesheetClientChange = function(clientId) {
  const sel = document.getElementById('ts-service');
  if (!sel) return;

  if (!clientId) {
    sel.innerHTML = `<option value="">— Select Service —</option>`;
    return;
  }

  // Find all service engagements mapped to this client
  const clientEngs = window.State.engagements.filter(e => e.clientId === clientId);
  if (clientEngs.length > 0) {
    sel.innerHTML = clientEngs.map(e => {
      const name = window.SERVICES_MAP[e.serviceId] || e.serviceId;
      return `<option value="${e.serviceId}">${name}</option>`;
    }).join('');
  } else {
    // Fallback to all preset services if client doesn't have assigned engagements yet
    const presetServices = window.State.services || [];
    sel.innerHTML = `<option value="">— Generic Service —</option>` +
      presetServices.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  }
};

function renderTimesheetStats() {
  const statsContainer = document.getElementById('ts-stats-cards');
  if (!statsContainer) return;

  const emp = window.State.team.find(t => t.id === activeTimesheetEmpId);
  const myEntries = window.State.timesheets.filter(t => t.employeeId === activeTimesheetEmpId);

  // Compute stats: total hours this month, capacity, billing rate
  const totalHours = myEntries.reduce((sum, entry) => sum + parseFloat(entry.hours || 0), 0);
  const capacity = emp ? (emp.stdHours || 160) : 160;
  const utilization = ((totalHours / capacity) * 100).toFixed(1);
  const costRate = emp ? (emp.costPerHour || emp.costRate || 3000) : 3000;

  statsContainer.innerHTML = `
    <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
      <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Total Hours Logged</div>
      <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: var(--primary);">${totalHours} hrs</div>
      <small style="color: var(--text-muted);">Current logging session</small>
    </div>
    <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
      <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Capacity Utilization</div>
      <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: ${totalHours >= capacity ? '#2ecc71' : '#e67e22'};">${utilization}%</div>
      <small style="color: var(--text-muted);">Standard capacity: ${capacity} hrs</small>
    </div>
    <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
      <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Billable Capacity Rate</div>
      <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: var(--bronze);">₹${costRate.toLocaleString('en-IN')}/hr</div>
      <small style="color: var(--text-muted);">Standard resource cost</small>
    </div>
  `;

  const totalBadge = document.getElementById('ts-total-badge');
  if (totalBadge) totalBadge.textContent = `Total: ${totalHours} hrs`;
}

function renderTimesheetLedger() {
  const tbody = document.getElementById('ts-ledger-body');
  if (!tbody) return;

  const myEntries = window.State.timesheets.filter(t => t.employeeId === activeTimesheetEmpId);

  // Sort by date descending
  myEntries.sort((a, b) => new Date(b.date) - new Date(a.date));

  if (myEntries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted); padding: 20px 0;">No timesheet entries logged for this employee. Use the form to record daily activities.</td></tr>`;
    return;
  }

  tbody.innerHTML = myEntries.map(e => {
    const cl = window.State.clients.find(c => c.id === e.clientId);
    const svcName = window.SERVICES_MAP[e.serviceId] || e.serviceId;
    
    const statusVal = e.status || 'Pending';
    let statusBadge = '';
    if (statusVal === 'Approved') {
      statusBadge = `<span class="badge badge-active" style="background-color:rgba(46,204,113,0.1); color:#2ecc71; border:1px solid rgba(46,204,113,0.2);">Approved</span>`;
    } else if (statusVal === 'Rejected') {
      statusBadge = `<span class="badge badge-inactive" style="background-color:rgba(231,76,60,0.1); color:#e74c3c; border:1px solid rgba(231,76,60,0.2);">Rejected</span>`;
    } else {
      statusBadge = `<span class="badge badge-manager" style="background-color:rgba(241,196,15,0.1); color:#b8924a; border:1px solid rgba(241,196,15,0.2);">Pending</span>`;
    }

    return `
      <tr>
        <td><code>${e.date}</code></td>
        <td><strong>${cl ? cl.name : e.clientId}</strong></td>
        <td>${svcName}</td>
        <td><strong>${e.hours} hrs</strong></td>
        <td style="max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: normal; font-size: 12px; color: var(--text-muted);">${e.description}</td>
        <td>${statusBadge}</td>
        <td>
          ${statusVal !== 'Approved' ? `<button onclick="deleteTimesheetEntry('${e.id}')" class="btn" style="padding: 4px 8px; background: rgba(231,76,60,0.08); color: #e74c3c; border: 1px solid rgba(231,76,60,0.3); font-size: 11px;">Delete</button>` : `<span style="font-size:11px; color:var(--text-muted);">Locked</span>`}
        </td>
      </tr>
    `;
  }).join('');
}

window.saveTimesheetEntry = function(event) {
  event.preventDefault();

  const date = document.getElementById('ts-date').value;
  const clientId = document.getElementById('ts-client').value;
  const serviceId = document.getElementById('ts-service').value;
  const hours = parseFloat(document.getElementById('ts-hours').value);
  const description = document.getElementById('ts-description').value.trim();

  if (!activeTimesheetEmpId) {
    alert("Please select an active employee.");
    return;
  }

  const emp = window.State.team.find(t => t.id === activeTimesheetEmpId);
  if (!emp) {
    alert("Please select a valid active employee.");
    return;
  }

  const activeUser = window.getCurrentActiveUser();
  if (!activeUser || (activeUser.role !== 'super_admin' && activeUser.id !== activeTimesheetEmpId)) {
    alert("Unauthorized: You can only log time against your own profile.");
    return;
  }

  if (isNaN(hours) || hours <= 0 || hours > 24) {
    alert("Please enter a valid amount of hours (0.5 to 24).");
    return;
  }

  // Calculate daily timesheet log limit
  const existingHours = window.State.timesheets
    .filter(t => t.employeeId === activeTimesheetEmpId && t.date === date)
    .reduce((sum, entry) => sum + parseFloat(entry.hours || 0), 0);

  const dailyLimit = emp.role === 'super_admin' ? 24 : 8;
  const roleLabel = emp.role === 'super_admin' ? 'Partner' : 'Staff Employee';

  if (existingHours + hours > dailyLimit) {
    alert(`Daily limit exceeded for ${emp.name} (${roleLabel}). Daily limit is ${dailyLimit} hours. Already logged: ${existingHours} hours on ${date}. Cannot log additional ${hours} hours.`);
    return;
  }

  const newEntry = {
    id: `ts_${Date.now()}`,
    employeeId: activeTimesheetEmpId,
    date,
    clientId,
    serviceId,
    hours,
    description,
    status: 'Pending'
  };

  window.State.timesheets.push(newEntry);
  window.saveState();

  // Reset form inputs except date/client
  document.getElementById('ts-hours').value = '';
  document.getElementById('ts-description').value = '';

  // Re-render components
  renderTimesheetStats();
  renderTimesheetLedger();

  alert("Daily timesheet entry logged successfully.");
};

window.deleteTimesheetEntry = function(entryId) {
  const entry = window.State.timesheets.find(t => t.id === entryId);
  const activeUser = window.getCurrentActiveUser();
  if (!entry || !activeUser) return;
  if (entry.status === 'Approved') {
    alert("Approved timesheet entries are locked and cannot be deleted.");
    return;
  }
  if (activeUser.role !== 'super_admin' && entry.employeeId !== activeUser.id) {
    alert("Unauthorized: You can only delete your own timesheet entries.");
    return;
  }
  if (!confirm("Are you sure you want to delete this timesheet entry?")) return;

  window.State.timesheets = window.State.timesheets.filter(t => t.id !== entryId);
  window.saveState();

  renderTimesheetStats();
  renderTimesheetLedger();
};

window.renderTimesheetApprovalsQueue = function() {
  const card = document.getElementById('ts-approvals-card');
  const tbody = document.getElementById('ts-approvals-body');
  if (!card || !tbody) return;

  const user = window.getCurrentActiveUser();
  if (!user || (user.role !== 'super_admin' && user.role !== 'manager')) {
    card.style.display = 'none';
    return;
  }

  let pendingEntries = [];
  if (user.role === 'super_admin') {
    pendingEntries = window.State.timesheets.filter(t => t.status === 'Pending');
  } else {
    const reportsIds = window.State.team.filter(t => t.managerId === user.id).map(t => t.id);
    pendingEntries = window.State.timesheets.filter(t => t.status === 'Pending' && reportsIds.includes(t.employeeId));
  }

  card.style.display = 'block';

  if (pendingEntries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted); padding:16px 0;">🎉 No pending timesheets in your evaluation queue. All team hours are approved!</td></tr>`;
    return;
  }

  tbody.innerHTML = pendingEntries.map(e => {
    const emp = window.State.team.find(t => t.id === e.employeeId);
    const cl = window.State.clients.find(c => c.id === e.clientId);
    const svcName = window.SERVICES_MAP[e.serviceId] || e.serviceId;
    return `
      <tr>
        <td><strong>${emp ? emp.name : 'Unknown Resource'}</strong><br><small style="color:var(--text-muted);">${emp ? emp.designation : ''}</small></td>
        <td><code>${e.date}</code></td>
        <td><strong>${cl ? cl.name : e.clientId}</strong><br><small style="color:var(--text-muted);">${svcName}</small></td>
        <td><strong>${e.hours} hrs</strong></td>
        <td style="max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:normal; font-size:12px; color:var(--text-muted);">${e.description}</td>
        <td style="white-space:nowrap; text-align:right;">
          <button onclick="approveTimesheetEntry('${e.id}')" class="btn btn-accent" style="padding:4px 10px; font-size:11px; margin-right:4px; font-weight:bold;">✔️ Approve</button>
          <button onclick="rejectTimesheetEntry('${e.id}')" class="btn" style="padding:4px 10px; font-size:11px; background:rgba(231,76,60,0.08); color:#e74c3c; border:1px solid rgba(231,76,60,0.3); font-weight:bold;">❌ Reject</button>
        </td>
      </tr>
    `;
  }).join('');
};

window.approveTimesheetEntry = function(entryId) {
  const ts = window.State.timesheets.find(t => t.id === entryId);
  if (!ts) return;

  const approver = window.getCurrentActiveUser();
  const canApprove = approver && (approver.role === 'super_admin' ||
    (approver.role === 'manager' && window.State.team.some(t => t.id === ts.employeeId && t.managerId === approver.id)));
  if (!canApprove) {
    alert("Unauthorized: You cannot approve this timesheet entry.");
    return;
  }
  if (ts.status !== 'Pending') {
    alert("Only pending timesheet entries can be approved.");
    return;
  }

  ts.status = 'Approved';
  window.awardSkillMomentum(ts.employeeId, Math.max(2, Math.round(Number(ts.hours || 0) * 2)), 'an approved timesheet');

  const newNotif = {
    id: `notif_ts_app_${Date.now()}`,
    type: 'Timesheet Approved',
    title: `Timesheet Approved by ${approver ? approver.name : 'Manager'}`,
    desc: `Your hours logged on ${ts.date} (${ts.hours} hrs) have been evaluated and approved.`,
    clientName: 'SSA Internal',
    managerId: ts.employeeId,
    isCritical: false
  };

  if (!window.State.notifications) window.State.notifications = [];
  window.State.notifications.unshift(newNotif);

  window.saveState();
  renderTimesheetStats();
  renderTimesheetLedger();
  renderTimesheetApprovalsQueue();

  alert(`Timesheet entry approved successfully.`);
};

window.rejectTimesheetEntry = function(entryId) {
  const ts = window.State.timesheets.find(t => t.id === entryId);
  if (!ts) return;

  const approver = window.getCurrentActiveUser();
  const canReject = approver && (approver.role === 'super_admin' ||
    (approver.role === 'manager' && window.State.team.some(t => t.id === ts.employeeId && t.managerId === approver.id)));
  if (!canReject) {
    alert("Unauthorized: You cannot reject this timesheet entry.");
    return;
  }
  if (ts.status !== 'Pending') {
    alert("Only pending timesheet entries can be rejected.");
    return;
  }

  const reason = prompt("Enter a brief reason for rejecting this timesheet entry:");
  if (reason === null) return;

  ts.status = 'Rejected';

  const newNotif = {
    id: `notif_ts_rej_${Date.now()}`,
    type: 'Timesheet Rejected',
    title: `Timesheet Rejected by ${approver ? approver.name : 'Manager'}`,
    desc: `Your hours logged on ${ts.date} (${ts.hours} hrs) were rejected. Reason: <strong>${reason || 'Needs clarification.'}</strong>`,
    clientName: 'SSA Internal',
    managerId: ts.employeeId,
    isCritical: true
  };

  if (!window.State.notifications) window.State.notifications = [];
  window.State.notifications.unshift(newNotif);

  window.saveState();
  renderTimesheetStats();
  renderTimesheetLedger();
  renderTimesheetApprovalsQueue();

  alert(`Timesheet entry rejected.`);
};


// INTERACTIVE CLIENT PROFITABILITY & BUDGET VS ACTUAL REPORT DASHBOARD
let activeReportClientId = '';
let activeReportTab = 'ledger'; // ledger, breakdown

window.renderReportsSkeleton = function() {
  const container = document.getElementById('view-reports');
  if (!container) return;

  // Set default client if empty
  if (!activeReportClientId && window.State.clients.length > 0) {
    activeReportClientId = window.State.clients.filter(c => !c.isArchived)[0]?.id || '';
  }

  // Header & Subtabs html
  let html = `
    <div class="card" style="margin-bottom: 24px;">
      <div class="card-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <h3 class="card-title">Practice Profitability & Filing Audits</h3>
          <p style="font-size:12px; color: var(--text-muted); margin-top:2px;">Detailed variance analysis comparing standard resource budgets vs actual logged daily timesheet hours.</p>
        </div>
      </div>
      <div class="card-body">
        <!-- Subtabs -->
        <div class="sub-tabs-container" style="margin-bottom: 20px;">
          <div class="sub-tabs">
            <button onclick="switchReportTab('ledger')" class="sub-tab-btn ${activeReportTab === 'ledger' ? 'active' : ''}">Client Profitability Ledger</button>
            <button onclick="switchReportTab('breakdown')" class="sub-tab-btn ${activeReportTab === 'breakdown' ? 'active' : ''}">Budget vs Actual Breakdown</button>
          </div>
        </div>

        <div id="reports-content-pane"></div>
      </div>
    </div>
  `;
  container.innerHTML = html;
  renderReportsContent();
};

function renderReportsContent() {
  const pane = document.getElementById('reports-content-pane');
  if (!pane) return;

  if (activeReportTab === 'ledger') {
    // Generate Ledger rows
    const clients = window.State.clients.filter(c => !c.isArchived);

    const rows = clients.map(c => {
      // 1. Annualized Revenue
      const clientEngs = window.State.engagements.filter(e => e.clientId === c.id);
      let revenue = 0;
      let budgetedCost = 0;

      clientEngs.forEach(e => {
        let annualFee = e.agreedFee;
        if (e.frequency === 'Monthly') annualFee = e.agreedFee * 12;
        else if (e.frequency === 'Quarterly') annualFee = e.agreedFee * 4;
        revenue += annualFee;

        const mappedBudgetLines = window.getEngagementBudgetLines ? window.getEngagementBudgetLines(e) : [];
        if (mappedBudgetLines.length) {
          budgetedCost += window.getEngagementBudgetCost(e, true);
        } else {
          // Legacy estimate for engagements not yet mapped to a service budget.
          const picObj = window.State.team.find(t => t.id === e.picUserId);
          const micObj = window.State.team.find(t => t.id === e.micUserId);
          budgetedCost += (picObj ? (picObj.costPerHour || picObj.costRate || 0) * 20 : 0);
          budgetedCost += (micObj ? (micObj.costPerHour || micObj.costRate || 0) * 60 : 0);
          (e.teamUserIds || []).forEach(sid => {
            const staffObj = window.State.team.find(t => t.id === sid);
            if (staffObj) budgetedCost += (staffObj.costPerHour || staffObj.costRate || 0) * 150;
          });
        }
      });

      // 2. Actual Cost from Timesheets
      const clientTs = window.State.timesheets.filter(t => t.clientId === c.id);
      let actualCost = 0;
      clientTs.forEach(ts => {
        const empObj = window.State.team.find(t => t.id === ts.employeeId);
        const rate = empObj ? (empObj.costPerHour || empObj.costRate || 0) : 0;
        actualCost += (ts.hours * rate);
      });

      // Ratios
      const budgetMargin = revenue > 0 ? revenue - budgetedCost : 0;
      const budgetMarginPct = revenue > 0 ? (budgetMargin / revenue) * 100 : 0;

      const actualMargin = revenue > 0 ? revenue - actualCost : 0;
      const actualMarginPct = revenue > 0 ? (actualMargin / revenue) * 100 : 0;

      const costVariance = budgetedCost - actualCost; // positive is under budget, negative is over budget

      let statusBadge = '<span class="badge badge-active">Under Budget</span>';
      if (costVariance < 0) {
        statusBadge = '<span class="badge badge-inactive" style="background-color: rgba(231,76,60,0.12); color: #e74c3c;">Over Budget</span>';
      } else if (costVariance === 0) {
        statusBadge = '<span class="badge badge-hold">Within Budget</span>';
      }

      return `
        <tr>
          <td><strong>${c.name}</strong><br><code style="font-size:10px;">${c.code}</code></td>
          <td>₹${revenue.toLocaleString('en-IN')}</td>
          <td>₹${budgetedCost.toLocaleString('en-IN')}<br><small style="color:var(--text-muted); font-size:10px;">Margin: ${budgetMarginPct.toFixed(1)}%</small></td>
          <td>₹${actualCost.toLocaleString('en-IN')}<br><small style="color:var(--text-muted); font-size:10px;">Margin: ${actualMarginPct.toFixed(1)}%</small></td>
          <td style="color: ${costVariance >= 0 ? '#2ecc71' : '#e74c3c'}; font-weight: 700;">
            ${costVariance >= 0 ? '+' : ''}₹${costVariance.toLocaleString('en-IN')}
          </td>
          <td>${statusBadge}</td>
        </tr>
      `;
    }).join('');

    pane.innerHTML = `
      <div class="table-responsive">
        <table class="custom-table" style="font-size:13px;">
          <thead>
            <tr>
              <th>Client Context</th>
              <th>Annualized Revenue</th>
              <th>Budgeted Delivery Cost</th>
              <th>Actual Timesheet Cost</th>
              <th>Cost Variance</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            ${rows || '<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No active clients found.</td></tr>'}
          </tbody>
        </table>
      </div>
    `;
  } else if (activeReportTab === 'breakdown') {
    // Breakdown for a single client
    const clients = window.State.clients.filter(c => !c.isArchived);
    const selectedClient = window.State.clients.find(c => c.id === activeReportClientId);

    // Calculate specific stats for selected client
    let revenue = 0;
    let budgetedCost = 0;
    const budgetedResources = [];
    const clientEngs = window.State.engagements.filter(e => e.clientId === activeReportClientId);

    clientEngs.forEach(e => {
      let annualFee = e.agreedFee;
      if (e.frequency === 'Monthly') annualFee = e.agreedFee * 12;
      else if (e.frequency === 'Quarterly') annualFee = e.agreedFee * 4;
      revenue += annualFee;

      const svcName = window.SERVICES_MAP[e.serviceId] || e.serviceId;

      const mappedBudgetLines = window.getEngagementBudgetLines ? window.getEngagementBudgetLines(e) : [];
      if (mappedBudgetLines.length) {
        const multiplier = window.getBudgetFrequencyMultiplier(e.frequency);
        mappedBudgetLines.forEach(line => {
          const annualCost = Number(line.estimatedCost || 0) * multiplier;
          budgetedCost += annualCost;
          budgetedResources.push({ name: line.designation, role: 'Planned designation', hours: multiplier, rate: Number(line.estimatedCost || 0), totalCost: annualCost, service: svcName, isMappedBudget: true });
        });
      } else {
        const picObj = window.State.team.find(t => t.id === e.picUserId);
        if (picObj) { const rate = picObj.costPerHour || picObj.costRate || 0; budgetedCost += rate * 20; budgetedResources.push({ name: picObj.name, role: 'PIC Partner', hours: 20, rate, totalCost: rate * 20, service: svcName }); }
        const micObj = window.State.team.find(t => t.id === e.micUserId);
        if (micObj) { const rate = micObj.costPerHour || micObj.costRate || 0; budgetedCost += rate * 60; budgetedResources.push({ name: micObj.name, role: 'MIC Manager', hours: 60, rate, totalCost: rate * 60, service: svcName }); }
        (e.teamUserIds || []).forEach(sid => { const staffObj = window.State.team.find(t => t.id === sid); if (staffObj) { const rate = staffObj.costPerHour || staffObj.costRate || 0; budgetedCost += rate * 150; budgetedResources.push({ name: staffObj.name, role: 'Staff Associate', hours: 150, rate, totalCost: rate * 150, service: svcName }); } });
      }
    });

    const clientTs = window.State.timesheets.filter(t => t.clientId === activeReportClientId);
    let actualCost = 0;
    const actualLogs = [];
    clientTs.forEach(ts => {
      const empObj = window.State.team.find(t => t.id === ts.employeeId);
      const rate = empObj ? (empObj.costPerHour || empObj.costRate || 0) : 0;
      const cost = ts.hours * rate;
      actualCost += cost;

      actualLogs.push({
        date: ts.date,
        employeeName: empObj ? empObj.name : 'Unknown',
        role: empObj ? empObj.roleLabel : 'Staff',
        hours: ts.hours,
        rate,
        totalCost: cost,
        description: ts.description,
        service: window.SERVICES_MAP[ts.serviceId] || ts.serviceId
      });
    });

    const variance = budgetedCost - actualCost;

    pane.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px; flex-wrap:wrap; gap:12px;">
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-weight:600; font-size:13px;">Select Client:</span>
          <select id="report-client-select" onchange="onReportClientChange(this.value)" class="select-filter" style="min-width: 250px;">
            ${clients.map(c => `<option value="${c.id}" ${c.id === activeReportClientId ? 'selected' : ''}>${c.name} (${c.code})</option>`).join('')}
          </select>
        </div>
        <div style="font-size:13px; font-weight:700; color: ${variance >= 0 ? '#2ecc71' : '#e74c3c'};">
          Cost Variance: ${variance >= 0 ? 'Under Budget' : 'Over Budget'} by ₹${Math.abs(variance).toLocaleString('en-IN')}
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Annualized Fee (Revenue)</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: var(--primary);">₹${revenue.toLocaleString('en-IN')}</div>
          <small style="color:var(--text-muted);">Sum of assigned contract fees</small>
        </div>
        <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Budgeted Resource Cost</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: var(--bronze);">₹${budgetedCost.toLocaleString('en-IN')}</div>
          <small style="color:var(--text-muted);">Margin: ${revenue > 0 ? (((revenue - budgetedCost)/revenue)*100).toFixed(1) : 0}%</small>
        </div>
        <div style="background: rgba(0,0,0,0.01); border: 1px solid var(--border-color); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Actual Timesheet Cost</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: ${variance >= 0 ? '#2ecc71' : '#e74c3c'};">₹${actualCost.toLocaleString('en-IN')}</div>
          <small style="color:var(--text-muted);">Margin: ${revenue > 0 ? (((revenue - actualCost)/revenue)*100).toFixed(1) : 0}%</small>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
        <!-- Budget Side -->
        <div>
          <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text-muted);">Standard Resource Budget Allocations</h4>
          <div class="table-responsive">
            <table class="custom-table" style="font-size:12px;">
              <thead>
                <tr>
                  <th>Resource</th>
                  <th>Budgeted Role</th>
                  <th>Hours</th>
                  <th>Rate</th>
                  <th>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                ${budgetedResources.map(br => `
                  <tr>
                    <td><strong>${br.name}</strong><br><small style="color:var(--text-muted);">${br.service}</small></td>
                    <td><span class="badge ${br.role.includes('Partner') ? 'badge-partner' : br.role.includes('Manager') ? 'badge-manager' : 'badge-staff'}">${br.role}</span></td>
                    <td>${br.isMappedBudget ? `${br.hours} ${br.hours === 1 ? 'delivery' : 'deliveries'}` : `${br.hours} hrs`}</td>
                    <td>${br.isMappedBudget ? `₹${br.rate.toLocaleString('en-IN')} / delivery` : `₹${br.rate}/hr`}</td>
                    <td><strong>₹${br.totalCost.toLocaleString('en-IN')}</strong></td>
                  </tr>
                `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No budgeted resources registered.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>

        <!-- Actual Side -->
        <div>
          <h4 style="font-size: 14px; font-weight: 700; margin-bottom: 12px; color: var(--text-muted);">Actual Daily Timesheet Cost Logs</h4>
          <div class="table-responsive">
            <table class="custom-table" style="font-size:12px;">
              <thead>
                <tr>
                  <th>Date & Resource</th>
                  <th>Service</th>
                  <th>Hours</th>
                  <th>Cost</th>
                  <th>Work Log</th>
                </tr>
              </thead>
              <tbody>
                ${actualLogs.map(al => `
                  <tr>
                    <td><code>${al.date}</code><br><strong>${al.employeeName}</strong></td>
                    <td>${al.service}</td>
                    <td>${al.hours} hrs</td>
                    <td><strong>₹${al.totalCost.toLocaleString('en-IN')}</strong></td>
                    <td style="white-space:normal; font-size:11px; color:var(--text-muted); max-width:180px;">${al.description}</td>
                  </tr>
                `).join('') || '<tr><td colspan="5" style="text-align:center;color:var(--text-muted);">No daily hours logged yet.</td></tr>'}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }
}

window.switchReportTab = function(tab) {
  activeReportTab = tab;
  renderReportsSkeleton();
};

window.onReportClientChange = function(clientId) {
  activeReportClientId = clientId;
  renderReportsContent();
};

// DASHBOARD RENDERER & LOGIC
let segmentChartInstance = null;

window.renderDashboard = function() {
  const activeClients = window.State.clients.filter(c => !c.isArchived);
  const totalClientsCount = window.State.clients.length;
  const activeClientsCount = activeClients.filter(c => c.status === 'Active').length;
  const teamCount = window.State.team.filter(t => t.status === 'Active').length;

  // Calculate dynamic overdue jobs from jobs board
  const todayStr = window.toLocalISODate();
  const overdueJobs = (window.State.jobs || []).filter(j => j.status !== 'Completed' && j.dueDate < todayStr);

  // Compute dynamic critical alerts count
  const criticalCount = overdueJobs.length + window.State.notifications.filter(n => n.isCritical).length;

  // Calculate pending timesheets: active team members who haven't logged any hours in the last 7 days
  const sevenDaysAgo = new Date();
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const sevenDaysAgoStr = window.toLocalISODate(sevenDaysAgo);
  
  let pendingTimesheetsCount = 0;
  window.State.team.filter(t => t.status === 'Active').forEach(emp => {
    const loggedAny = window.State.timesheets.some(ts => ts.employeeId === emp.id && ts.date >= sevenDaysAgoStr);
    if (!loggedAny) {
      pendingTimesheetsCount++;
    }
  });

  // Render KPI values dynamically
  document.getElementById('kpi-total-clients').textContent = totalClientsCount;
  document.getElementById('kpi-active-clients').textContent = activeClientsCount;
  document.getElementById('kpi-critical-alerts').textContent = criticalCount;
  document.getElementById('kpi-team-count').textContent = teamCount;
  document.getElementById('kpi-timesheet-delays').textContent = pendingTimesheetsCount;

  // ─── Greeting Banner ────────────────────────────────────────────────────────
  const activeUser = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  if (activeUser) {
    const hour = new Date().getHours();
    const greeting = hour < 12 ? 'Good Morning' : hour < 17 ? 'Good Afternoon' : 'Good Evening';
    const firstName = (activeUser.name || 'User').split(' ')[0];
    const initials = (activeUser.name || 'U').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

    const greetingTextEl = document.getElementById('dash-greeting-text');
    const greetingSubEl  = document.getElementById('dash-greeting-sub');
    const greetingAvEl   = document.getElementById('dash-greeting-avatar');
    const greetingStats  = document.getElementById('dash-greeting-stats');

    if (greetingTextEl) greetingTextEl.textContent = `${greeting}, ${firstName} 👋`;
    if (greetingSubEl)  greetingSubEl.textContent = `${today} · ${activeUser.roleLabel || activeUser.role}`;
    if (greetingAvEl) {
      if (activeUser.photo) {
        greetingAvEl.innerHTML = `<img src="${activeUser.photo}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;">`;
      } else {
        greetingAvEl.textContent = initials;
      }
    }

    if (greetingStats) {
      const todayJobs = (window.State.jobs || []).filter(j => j.dueDate === todayStr && j.status !== 'Completed');
      const overdueCount = overdueJobs.length;
      greetingStats.innerHTML = `
        <div class="dash-stat-chip ${todayJobs.length > 0 ? 'dash-stat-chip--amber' : 'dash-stat-chip--green'}">
          <span class="dash-stat-chip-val">${todayJobs.length}</span>
          <span class="dash-stat-chip-label">Due Today</span>
        </div>
        <div class="dash-stat-chip ${overdueCount > 0 ? 'dash-stat-chip--red' : 'dash-stat-chip--green'}">
          <span class="dash-stat-chip-val">${overdueCount}</span>
          <span class="dash-stat-chip-label">Overdue</span>
        </div>
        <div class="dash-stat-chip ${pendingTimesheetsCount > 0 ? 'dash-stat-chip--amber' : 'dash-stat-chip--green'}">
          <span class="dash-stat-chip-val">${pendingTimesheetsCount}</span>
          <span class="dash-stat-chip-label">Pending TS</span>
        </div>
      `;
    }
  }
  // ────────────────────────────────────────────────────────────────────────────

  // 1. Calculate Filing Compliance Health Rate (Completed / Total jobs)
  const totalJobs = window.State.jobs || [];
  const completedJobsCount = totalJobs.filter(j => j.status === 'Completed').length;
  const totalJobsCount = totalJobs.length;
  const complianceRate = totalJobsCount > 0 ? Math.round((completedJobsCount / totalJobsCount) * 100) : 100;

  const healthRateEl = document.getElementById('compliance-health-rate');
  const healthBarEl = document.getElementById('compliance-health-bar');
  const healthSubEl = document.getElementById('compliance-health-subtitle');

  if (healthRateEl && healthBarEl && healthSubEl) {
    healthRateEl.textContent = `${complianceRate}%`;
    healthBarEl.style.width = `${complianceRate}%`;
    
    // Color coding matching urgency
    if (complianceRate >= 80) {
      healthBarEl.style.backgroundColor = '#2ecc71'; // Green
    } else if (complianceRate >= 50) {
      healthBarEl.style.backgroundColor = '#f1c40f'; // Yellow
    } else {
      healthBarEl.style.backgroundColor = '#e74c3c'; // Red
    }
    
    healthSubEl.innerHTML = `Completed: <strong>${completedJobsCount}</strong> · Total Filings: <strong>${totalJobsCount}</strong> (${totalJobsCount - completedJobsCount} pending)`;
  }

  // 2. Render Team Timesheet Leaderboard (Standings in last 7 days)
  const leaderboardBody = document.getElementById('timesheet-leaderboard-body');
  if (leaderboardBody) {
    const activeStaff = window.State.team.filter(t => t.status === 'Active');
    const standings = activeStaff.map(emp => {
      const empLogs = window.State.timesheets.filter(ts => ts.employeeId === emp.id && ts.date >= sevenDaysAgoStr);
      const totalHours = empLogs.reduce((sum, item) => sum + item.hours, 0);
      return { emp, totalHours };
    });

    // Sort by hours descending
    standings.sort((a, b) => b.totalHours - a.totalHours);

    if (standings.length === 0) {
      leaderboardBody.innerHTML = `<div style="text-align:center; color:var(--text-muted); font-size:12px; padding:20px 0;">No active staff registered.</div>`;
    } else {
      const rankMedals = ['🥇', '🥈', '🥉'];
      leaderboardBody.innerHTML = standings.map((st, idx) => {
        const targetHours = 40;
        const percent = Math.min(100, Math.round((st.totalHours / targetHours) * 100));
        const initials = st.emp.name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
        const avatarColors = ['#2563eb','#059669','#7c3aed','#d97706','#dc2626','#0891b2','#be185d'];
        const avatarColor = avatarColors[idx % avatarColors.length];
        const rank = idx < 3 ? rankMedals[idx] : `<span style="font-size:11px;font-weight:700;color:var(--text-muted);">#${idx+1}</span>`;

        let barColor = '#2ecc71';
        if (st.totalHours >= 35) barColor = '#059669';
        else if (st.totalHours >= 15) barColor = '#d97706';
        else if (st.totalHours > 0) barColor = '#e67e22';
        else barColor = 'rgba(220,38,38,0.4)';

        return `
          <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
            <div style="font-size:16px; width:22px; text-align:center; flex-shrink:0;">${rank}</div>
            <div style="width:32px; height:32px; border-radius:50%; background:${avatarColor}; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:700; color:#fff; flex-shrink:0;">${initials}</div>
            <div style="flex:1; min-width:0;">
              <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:4px;">
                <span style="font-size:12px; font-weight:600; color:var(--text-main); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${st.emp.name}</span>
                <span style="font-size:11px; font-weight:700; color:${barColor}; white-space:nowrap; margin-left:8px;">${st.totalHours}<span style="font-weight:400; color:var(--text-muted);"> / 40h</span></span>
              </div>
              <div style="background:var(--border-color); height:6px; border-radius:99px; overflow:hidden;">
                <div style="background:${barColor}; width:${st.totalHours > 0 ? percent : 2}%; height:100%; border-radius:99px; transition: width 0.4s ease;"></div>
              </div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // 3. Render Compliance Bottlenecks & Workload Load Index
  const bottleneckBody = document.getElementById('bottleneck-chart-body');
  if (bottleneckBody) {
    const activeStaff = window.State.team.filter(t => t.status === 'Active');
    const jobs = window.State.jobs || [];
    const todayStr = window.toLocalISODate();

    const bottleneckScores = activeStaff.map(emp => {
      const empJobs = jobs.filter(j => j.assignedUserId === emp.id && j.status !== 'Completed');
      
      let score = 0;
      let overdueCount = 0;
      let reviewCount = 0;
      let progressCount = 0;

      empJobs.forEach(j => {
        if (j.dueDate < todayStr) {
          score += 3; // Overdue
          overdueCount++;
        } else if (j.status === 'Under Review') {
          score += 2; // Under Review
          reviewCount++;
        } else if (j.status === 'In Progress') {
          score += 1; // In Progress
          progressCount++;
        }
      });

      return { emp, score, overdueCount, reviewCount, progressCount };
    });

    // Sort descending by score
    bottleneckScores.sort((a, b) => b.score - a.score);

    // Keep top 5 or non-zero
    const topBottlenecks = bottleneckScores.filter(s => s.score > 0);

    if (topBottlenecks.length === 0) {
      bottleneckBody.innerHTML = `<div style="color:var(--text-muted); font-size:12px; padding:10px 0;">🎉 No bottlenecks detected! All active compliance tasks are on schedule.</div>`;
    } else {
      const maxScore = Math.max(...topBottlenecks.map(s => s.score));

      bottleneckBody.innerHTML = topBottlenecks.map(st => {
        const percent = maxScore > 0 ? Math.round((st.score / maxScore) * 100) : 0;
        
        let barColor = '#3498db'; // blue
        if (st.score >= 6) barColor = '#e74c3c'; // critical -> red
        else if (st.score >= 3) barColor = '#e67e22'; // moderate -> orange
        else barColor = '#f1c40f'; // low -> yellow

        return `
          <div style="margin-bottom:14px; font-family:'Plus Jakarta Sans', sans-serif;">
            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
              <span><strong>${st.emp.name}</strong> <small style="color:var(--text-muted);">(${st.emp.designation})</small></span>
              <span style="font-weight:700; color:${barColor}; font-size:12px;">Delay Index: ${st.score} <small style="color:var(--text-muted); font-weight:normal; font-size:10px;">(${st.overdueCount} Overdue, ${st.reviewCount} In Review, ${st.progressCount} Active)</small></span>
            </div>
            <div style="background:var(--border-color); height:12px; border-radius:6px; overflow:hidden;">
              <div style="background:${barColor}; width:${percent}%; height:100%; border-radius:6px; transition: width 0.3s ease;"></div>
            </div>
          </div>
        `;
      }).join('');
    }
  }

  // Click on metrics to trigger navigation and pre-filters
  setupMetricClickHandlers();

  // Render Alerts List (combines notifications & overdue jobs)
  renderCriticalAlerts();

  // Render Overdue Filings Table (shows actual overdue jobs)
  renderOverdueFilingsTable();

  // Render Segment Profitability Chart using Chart.js
  renderProfitabilityChart();

  // Render personal, work-earned development feedback.
  window.renderSkillMomentum();
  window.renderSkillCapabilityCharts();
};

// ─── SKILL MOMENTUM: GAMIFIED DEVELOPMENT FEEDBACK ──────────────────────────
// The score uses an S-curve: early progress is gradual, consistent practice
// accelerates growth in the middle, and repetitive work tapers near mastery.
window.initializeSkillMomentum = function() {
  (window.State.team || []).forEach(emp => {
    if (typeof emp.growthXP === 'number') return;
    const approvedHours = (window.State.timesheets || []).filter(ts => ts.employeeId === emp.id && ts.status === 'Approved').reduce((total, ts) => total + Number(ts.hours || 0), 0);
    const completedJobs = (window.State.jobs || []).filter(job => job.assignedUserId === emp.id && job.status === 'Completed').length;
    emp.growthXP = Math.round(approvedHours * 2 + completedJobs * 16);
  });
  if (!Array.isArray(window.State.growthFeed)) window.State.growthFeed = [];
};

window.getSkillMomentum = function(employeeId) {
  window.initializeSkillMomentum();
  const emp = (window.State.team || []).find(member => member.id === employeeId);
  if (!emp) return null;
  const xp = Math.max(0, Number(emp.growthXP || 0));
  const score = Math.round(100 / (1 + Math.exp(-0.055 * (xp - 80))));
  const level = Math.min(10, Math.floor(xp / 35) + 1);
  const levelStart = (level - 1) * 35;
  const nextLevelXP = level === 10 ? levelStart : level * 35;
  const levelProgress = level === 10 ? 100 : Math.min(100, Math.round(((xp - levelStart) / 35) * 100));
  let phase = 'Foundation';
  let message = 'Small, consistent wins are building a dependable base.';
  if (score >= 76) {
    phase = 'Mastery';
    message = 'Progress now compounds slowly—quality and varied work matter most.';
  } else if (score >= 26) {
    phase = 'Acceleration';
    message = 'Your consistency is compounding. This is the fastest growth phase.';
  }
  return { emp, xp, score, level, nextLevelXP, levelProgress, phase, message };
};

window.awardSkillMomentum = function(employeeId, points, activity) {
  window.initializeSkillMomentum();
  const emp = (window.State.team || []).find(member => member.id === employeeId);
  if (!emp || !Number.isFinite(points) || points <= 0) return;
  emp.growthXP = Math.max(0, Number(emp.growthXP || 0)) + Math.round(points);
  window.State.growthFeed.unshift({ id: `growth_${Date.now()}_${employeeId}`, employeeId, points: Math.round(points), activity, createdAt: window.toLocalISODate() });
  window.State.growthFeed = window.State.growthFeed.slice(0, 24);
};

window.renderSkillMomentum = function() {
  const card = document.getElementById('skill-momentum-card');
  const user = window.getCurrentActiveUser();
  if (!card || !user) return;
  const momentum = window.getSkillMomentum(user.id);
  if (!momentum) return;
  const recent = (window.State.growthFeed || []).find(item => item.employeeId === user.id);
  const nextLabel = momentum.level === 10 ? 'Peak level reached' : `${momentum.nextLevelXP - momentum.xp} XP to Level ${momentum.level + 1}`;
  const recentHtml = recent ? `<div class="momentum-recent">✦ Latest win: <strong>+${recent.points} XP</strong> for ${recent.activity}</div>` : `<div class="momentum-recent">Complete a job or earn an approved timesheet to build momentum.</div>`;
  card.innerHTML = `
    <div class="momentum-orbit" style="--momentum-score:${momentum.score};"><div class="momentum-orbit-inner"><strong>${momentum.score}</strong><span>/ 100</span></div></div>
    <div class="momentum-main"><div class="momentum-eyebrow">PERSONAL DEVELOPMENT · LEVEL ${momentum.level}</div><div class="momentum-title">${momentum.phase} <span>✦</span></div><p>${momentum.message}</p><div class="momentum-progress-row"><span>${momentum.xp} XP earned</span><strong>${nextLabel}</strong></div><div class="momentum-track"><span style="width:${momentum.levelProgress}%"></span></div>${recentHtml}</div>
    <div class="momentum-curve" aria-hidden="true"><div class="momentum-curve-label">GROWTH CURVE</div><svg viewBox="0 0 180 74" role="img"><path d="M4 64 C 35 63, 44 59, 61 47 S 95 9, 122 9 S 157 10, 176 8" fill="none" stroke="currentColor" stroke-width="4" stroke-linecap="round"/><circle cx="${Math.max(8, Math.min(172, 4 + momentum.score * 1.72))}" cy="${Math.max(8, 64 - momentum.score * 0.56)}" r="5" fill="currentColor"/></svg><div class="momentum-curve-stages"><span>Build</span><span>Accelerate</span><span>Master</span></div></div>
  `;
};

// ─── SKILL CAPABILITY RADARS ────────────────────────────────────────────────
let technicalSkillRadarInstance = null;
let personaSkillRadarInstance = null;

window.getSkillCapabilityProfile = function(employeeId) {
  const approvedTime = (window.State.timesheets || []).filter(entry => entry.employeeId === employeeId && entry.status === 'Approved');
  const completedJobs = (window.State.jobs || []).filter(job => job.assignedUserId === employeeId && job.status === 'Completed');
  const serviceHours = serviceId => approvedTime.filter(entry => entry.serviceId === serviceId).reduce((total, entry) => total + Number(entry.hours || 0), 0);
  const serviceJobs = serviceId => completedJobs.filter(job => job.serviceId === serviceId).length;
  const technicalScore = serviceId => Math.min(10, Math.round((2 + serviceHours(serviceId) * 0.17 + serviceJobs(serviceId) * 1.15) * 10) / 10);

  const meaningfulLogs = approvedTime.filter(entry => (entry.description || '').trim().split(/\s+/).filter(Boolean).length >= 5).length;
  const activeDays = new Set(approvedTime.map(entry => entry.date)).size;
  const onTimeCompletions = completedJobs.filter(job => !job.dueDate || !job.completionDate || job.completionDate <= job.dueDate).length;
  const writtenWork = serviceHours('certificates') + serviceHours('tax_annual') + (serviceJobs('certificates') + serviceJobs('tax_annual')) * 4;
  const personaScore = value => Math.min(10, Math.round(value * 10) / 10);

  return {
    technical: [
      { label: 'Income Tax', score: technicalScore('tax_annual') },
      { label: 'GST Compliance', score: personaScore((technicalScore('gst_r1') + technicalScore('gst_3b')) / 2) },
      { label: 'Tax Audit', score: technicalScore('tax_audit') },
      { label: 'Statutory Audit', score: technicalScore('stat_audit') }
    ],
    persona: [
      { label: 'Time Discipline', score: personaScore(2.5 + activeDays * 0.55 + onTimeCompletions * 0.35) },
      { label: 'Work Communication', score: personaScore(2.5 + meaningfulLogs * 0.6) },
      { label: 'Written Representation', score: personaScore(2 + writtenWork * 0.13) },
      { label: 'Delivery Ownership', score: personaScore(2.5 + completedJobs.length * 0.75 + approvedTime.length * 0.15) }
    ]
  };
};

window.renderSkillCapabilityCharts = function() {
  const technicalCanvas = document.getElementById('technical-skill-radar');
  const personaCanvas = document.getElementById('persona-skill-radar');
  const insight = document.getElementById('skill-development-insight');
  const user = window.getCurrentActiveUser();
  if (!technicalCanvas || !personaCanvas || !insight || !user) return;

  const profile = window.getSkillCapabilityProfile(user.id);
  const allSkills = [...profile.technical, ...profile.persona];
  const focus = [...allSkills].sort((a, b) => a.score - b.score)[0];
  const technicalAverage = profile.technical.reduce((sum, skill) => sum + skill.score, 0) / profile.technical.length;
  const personaAverage = profile.persona.reduce((sum, skill) => sum + skill.score, 0) / profile.persona.length;
  insight.innerHTML = `<div class="capability-insight-label">NEXT GROWTH FOCUS</div><strong>${focus.label}</strong><div class="capability-focus-score">${focus.score.toFixed(1)} <span>/ 10</span></div><p>${focus.score < 5 ? 'Build confidence through supervised, varied assignments in this area.' : 'Keep developing this capability through deliberate practice and feedback.'}</p><div class="capability-averages"><span><i class="legend-tech"></i>Technical <b>${technicalAverage.toFixed(1)}</b></span><span><i class="legend-persona"></i>Persona <b>${personaAverage.toFixed(1)}</b></span></div>`;

  if (typeof Chart === 'undefined') {
    technicalCanvas.parentElement.innerHTML += '<p class="capability-chart-fallback">Charts are unavailable while offline.</p>';
    return;
  }
  if (technicalSkillRadarInstance) technicalSkillRadarInstance.destroy();
  if (personaSkillRadarInstance) personaSkillRadarInstance.destroy();

  const radarOptions = colour => ({
    responsive: true,
    maintainAspectRatio: false,
    scales: { r: { min: 0, max: 10, ticks: { stepSize: 2, display: false }, angleLines: { color: 'rgba(148, 163, 184, 0.24)' }, grid: { color: 'rgba(148, 163, 184, 0.2)' }, pointLabels: { color: document.body.classList.contains('dark-theme') ? '#cbd5e1' : '#53657d', font: { size: 11, family: 'Plus Jakarta Sans' } } } },
    plugins: { legend: { display: false }, tooltip: { callbacks: { label: context => `${context.dataset.label}: ${context.raw} / 10` } } },
    elements: { line: { borderWidth: 2 }, point: { radius: 3, hoverRadius: 5 } },
    animation: { duration: 650 }
  });
  const makeData = (skills, colour) => ({
    labels: skills.map(skill => skill.label),
    datasets: [
      { label: 'Current capability', data: skills.map(skill => skill.score), borderColor: colour, backgroundColor: `${colour}2B`, pointBackgroundColor: colour, pointBorderColor: '#fff' },
      { label: 'Development target', data: skills.map(() => 8), borderColor: `${colour}A6`, borderDash: [5, 5], backgroundColor: 'transparent', pointRadius: 0, pointHoverRadius: 0 }
    ]
  });
  technicalSkillRadarInstance = new Chart(technicalCanvas, { type: 'radar', data: makeData(profile.technical, '#3b82f6'), options: radarOptions('#3b82f6') });
  personaSkillRadarInstance = new Chart(personaCanvas, { type: 'radar', data: makeData(profile.persona, '#d69e43'), options: radarOptions('#d69e43') });
};

function setupMetricClickHandlers() {
  document.getElementById('tile-total-clients').onclick = () => {
    window.navigateModule('clients');
    if (window.setClientDirectoryFilters) {
      window.setClientDirectoryFilters('', '', '', 'All');
    }
  };
  document.getElementById('tile-active-clients').onclick = () => {
    window.navigateModule('clients');
    if (window.setClientDirectoryFilters) {
      window.setClientDirectoryFilters('', '', '', 'Active');
    }
  };
  document.getElementById('tile-critical-alerts').onclick = () => {
    // Open Jobs module to see tasks
    window.navigateModule('jobs');
  };
  document.getElementById('tile-team-count').onclick = () => {
    window.navigateModule('team');
  };
  document.getElementById('tile-timesheet-delays').onclick = () => {
    window.navigateModule('timesheets');
  };
}

function renderCriticalAlerts() {
  const alertContainer = document.getElementById('critical-alerts-list');
  if (!alertContainer) return;

  const todayStr = window.toLocalISODate();
  const overdueJobs = (window.State.jobs || []).filter(j => j.status !== 'Completed' && j.dueDate < todayStr);
  const notifications = window.State.notifications || [];

  const combinedAlerts = [];

  // 1. Add actual overdue jobs to warnings list
  overdueJobs.forEach(j => {
    const cl = window.State.clients.find(c => c.id === j.clientId);
    const owner = window.State.team.find(t => t.id === j.assignedUserId);
    combinedAlerts.push({
      isCritical: true,
      title: `Filing Overdue: ${j.title}`,
      desc: `Task assigned to <strong>${owner ? owner.name : 'Unassigned'}</strong> is past its compliance due date (${j.dueDate}).`,
      clientName: cl ? cl.name : 'Unknown Client'
    });
  });

  // 2. Add standard alerts
  notifications.forEach(n => {
    combinedAlerts.push({
      isCritical: n.isCritical,
      title: n.title,
      desc: n.desc,
      clientName: n.clientName
    });
  });

  if (combinedAlerts.length === 0) {
    alertContainer.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px 0;">No active compliance warnings</div>`;
    return;
  }

  alertContainer.innerHTML = combinedAlerts.map(alert => `
    <div class="alert-item">
      <span class="alert-badge" ${alert.isCritical ? '' : 'style="animation: none; background-color:#3498db;"'}></span>
      <div class="alert-content">
        <div class="alert-title">${alert.title}</div>
        <div class="alert-desc">${alert.desc} <br><strong>Client Scope:</strong> ${alert.clientName}</div>
      </div>
    </div>
  `).join('');
}

function renderOverdueFilingsTable() {
  const container = document.getElementById('overdue-filings-body');
  if (!container) return;

  const todayStr = window.toLocalISODate();
  const overdueJobs = (window.State.jobs || []).filter(j => j.status !== 'Completed' && j.dueDate < todayStr);

  if (overdueJobs.length === 0) {
    container.innerHTML = `<tr><td colspan="4" style="text-align: center; color: var(--text-muted); padding: 20px 0;">No overdue filing events logged. All compliance jobs are on schedule!</td></tr>`;
    return;
  }

  // Render actual overdue tasks dynamically
  container.innerHTML = overdueJobs.map(j => {
    const cl = window.State.clients.find(c => c.id === j.clientId);
    const owner = window.State.team.find(t => t.id === j.assignedUserId);
    return `
      <tr>
        <td><strong>${cl ? cl.name : 'Unknown Client'}</strong><br><small style="color:var(--text-muted);">${cl ? cl.code : ''}</small></td>
        <td>${j.title}<br><small style="color:#e74c3c;">Due: ${j.dueDate}</small></td>
        <td><span class="badge badge-manager">${owner ? owner.name : 'Unassigned'}</span></td>
        <td><span class="badge badge-inactive" style="background-color: rgba(231,76,60,0.12); color: #e74c3c; font-weight: bold;">Overdue</span></td>
      </tr>
    `;
  }).join('');
}

window.profitabilityViewState = { dimension: 'client', period: 'all', clientId: '', layout: 'bar' };

window.onProfitabilityFilterChange = function(field, value) {
  window.profitabilityViewState[field] = value;
  renderProfitabilityChart();
};

function annualizedFee(engagement) {
  const fee = Number(engagement.agreedFee || 0);
  if (engagement.frequency === 'Monthly') return fee * 12;
  if (engagement.frequency === 'Quarterly') return fee * 4;
  return fee;
}

function getProfitabilityPeriod() {
  const today = new Date();
  const key = window.profitabilityViewState.period;
  if (key === 'all') return { start: null, factor: 1, label: 'all recorded activity' };
  if (key === 'month') { today.setDate(today.getDate() - 30); return { start: window.toLocalISODate(today), factor: 1 / 12, label: 'the last 30 days' }; }
  if (key === 'quarter') { today.setDate(today.getDate() - 90); return { start: window.toLocalISODate(today), factor: 1 / 4, label: 'the last 90 days' }; }
  const financialYearStart = new Date();
  financialYearStart.setMonth(financialYearStart.getMonth() < 3 ? -9 : 3, 1);
  return { start: window.toLocalISODate(financialYearStart), factor: 1, label: 'this financial year' };
}

function individualEngagementShare(engagement, employeeId) {
  if (engagement.picUserId === employeeId) return 0.30;
  if (engagement.micUserId === employeeId) return 0.25;
  const team = engagement.teamUserIds || [];
  if (team.includes(employeeId)) return 0.45 / team.length;
  return 0;
}

function renderProfitabilityChart() {
  const ctx = document.getElementById('segmentProfitabilityChart');
  const user = window.getCurrentActiveUser();
  if (!ctx || !user) return;
  if (segmentChartInstance) { segmentChartInstance.destroy(); segmentChartInstance = null; }

  const state = window.profitabilityViewState;
  const period = getProfitabilityPeriod();
  const isPartner = user.role === 'super_admin';
  if (!isPartner && state.dimension === 'person') state.dimension = 'client';
  const dimensionSelect = document.getElementById('profitability-dimension');
  if (dimensionSelect) {
    dimensionSelect.innerHTML = `<option value="client">Client-wise</option><option value="service">Service-wise</option><option value="task">Task-wise</option>${isPartner ? '<option value="person">Person-wise</option>' : ''}`;
    dimensionSelect.value = state.dimension;
  }
  const allActiveClients = (window.State.clients || []).filter(client => !client.isArchived);
  const personalClientIds = new Set(isPartner ? allActiveClients.map(client => client.id) : allActiveClients.filter(client => (window.State.engagements || []).some(engagement => engagement.clientId === client.id && individualEngagementShare(engagement, user.id) > 0) || (window.State.timesheets || []).some(entry => entry.clientId === client.id && entry.employeeId === user.id)).map(client => client.id));
  if (state.clientId && !personalClientIds.has(state.clientId)) state.clientId = '';
  const activeClients = allActiveClients.filter(client => !state.clientId || client.id === state.clientId);
  const selectableClients = allActiveClients.filter(client => personalClientIds.has(client.id));
  const clientSelect = document.getElementById('profitability-client');
  if (clientSelect) {
    clientSelect.innerHTML = `<option value="">All accessible clients</option>${selectableClients.map(client => `<option value="${client.id}" ${client.id === state.clientId ? 'selected' : ''}>${client.name}</option>`).join('')}`;
  }

  const title = document.getElementById('profitability-chart-title');
  const subtitle = document.getElementById('profitability-chart-subtitle');
  if (title) title.textContent = isPartner ? 'Firm Profitability Explorer' : 'My Profitability Explorer';
  if (subtitle) subtitle.textContent = isPartner ? `Firm-wide margin analysis across ${period.label}.` : `Your allocated revenue and delivery cost across ${period.label}.`;

  const accessibleEngagements = (window.State.engagements || []).filter(engagement => {
    const client = activeClients.find(item => item.id === engagement.clientId);
    return client && (isPartner || individualEngagementShare(engagement, user.id) > 0);
  });
  const accessibleTimesheets = (window.State.timesheets || []).filter(entry => {
    const isInPeriod = !period.start || entry.date >= period.start;
    const isClientIncluded = !state.clientId || entry.clientId === state.clientId;
    return isInPeriod && isClientIncluded && (isPartner || entry.employeeId === user.id);
  });

  const buckets = new Map();
  const addBucket = (key, label) => {
    if (!buckets.has(key)) buckets.set(key, { label, revenue: 0, cost: 0 });
    return buckets.get(key);
  };
  const labelForService = serviceId => window.SERVICES_MAP[serviceId] || serviceId || 'Unmapped service';

  if (state.dimension === 'person') {
    (window.State.team || []).filter(employee => employee.status === 'Active').forEach(employee => addBucket(employee.id, employee.name));
    accessibleEngagements.forEach(engagement => {
      (window.State.team || []).filter(employee => employee.status === 'Active').forEach(employee => {
        const share = individualEngagementShare(engagement, employee.id);
        if (share > 0) addBucket(employee.id, employee.name).revenue += annualizedFee(engagement) * period.factor * share;
      });
    });
    accessibleTimesheets.forEach(entry => {
      const employee = (window.State.team || []).find(member => member.id === entry.employeeId);
      if (employee) addBucket(employee.id, employee.name).cost += Number(entry.hours || 0) * Number(employee.costPerHour || employee.costRate || 0);
    });
  } else if (state.dimension === 'task') {
    const allJobs = (window.State.jobs || []).filter(job => {
      const date = job.completionDate || job.dueDate || '';
      const isInPeriod = !period.start || date >= period.start;
      const isClientIncluded = !state.clientId || job.clientId === state.clientId;
      return isInPeriod && isClientIncluded && (isPartner || job.assignedUserId === user.id);
    });
    allJobs.forEach(job => {
      const bucket = addBucket(job.id, job.title);
      const matchingEngagement = accessibleEngagements.find(engagement => engagement.clientId === job.clientId && engagement.serviceId === job.serviceId);
      const matchingJobs = (window.State.jobs || []).filter(item => item.clientId === job.clientId && item.serviceId === job.serviceId).length || 1;
      if (matchingEngagement) bucket.revenue += annualizedFee(matchingEngagement) * period.factor * (isPartner ? 1 : individualEngagementShare(matchingEngagement, user.id)) / matchingJobs;
      const matchingTime = accessibleTimesheets.filter(entry => entry.clientId === job.clientId && entry.serviceId === job.serviceId);
      bucket.cost += matchingTime.reduce((sum, entry) => {
        const employee = (window.State.team || []).find(member => member.id === entry.employeeId);
        return sum + Number(entry.hours || 0) * Number(employee?.costPerHour || employee?.costRate || 0) / matchingJobs;
      }, 0);
    });
  } else {
    accessibleEngagements.forEach(engagement => {
      const client = activeClients.find(item => item.id === engagement.clientId);
      const key = state.dimension === 'service' ? engagement.serviceId : engagement.clientId;
      const label = state.dimension === 'service' ? labelForService(engagement.serviceId) : client.name;
      addBucket(key, label).revenue += annualizedFee(engagement) * period.factor * (isPartner ? 1 : individualEngagementShare(engagement, user.id));
    });
    accessibleTimesheets.forEach(entry => {
      const key = state.dimension === 'service' ? entry.serviceId : entry.clientId;
      const client = activeClients.find(item => item.id === entry.clientId);
      const label = state.dimension === 'service' ? labelForService(entry.serviceId) : (client?.name || 'Unmapped client');
      const employee = (window.State.team || []).find(member => member.id === entry.employeeId);
      addBucket(key, label).cost += Number(entry.hours || 0) * Number(employee?.costPerHour || employee?.costRate || 0);
    });
  }

  const data = [...buckets.values()].sort((a, b) => (b.revenue - b.cost) - (a.revenue - a.cost));
  const revenue = data.reduce((sum, item) => sum + item.revenue, 0);
  const cost = data.reduce((sum, item) => sum + item.cost, 0);
  const margin = revenue - cost;
  const marginPct = revenue ? (margin / revenue) * 100 : 0;
  const summary = document.getElementById('profitability-summary');
  if (summary) summary.innerHTML = `<div><span>Revenue ${isPartner ? '' : 'allocated to me'}</span><strong>₹${Math.round(revenue).toLocaleString('en-IN')}</strong></div><div><span>Delivery cost ${isPartner ? '' : 'of my work'}</span><strong>₹${Math.round(cost).toLocaleString('en-IN')}</strong></div><div class="${margin >= 0 ? 'profit-positive' : 'profit-negative'}"><span>Net margin</span><strong>${margin >= 0 ? '+' : ''}₹${Math.round(margin).toLocaleString('en-IN')}</strong><small>${marginPct.toFixed(1)}%</small></div>`;
  const note = document.getElementById('profitability-chart-note');
  if (note) note.textContent = state.dimension === 'task' ? 'Task view allocates the relevant service fee and matching time across tasks with the same client and service.' : 'Revenue is annualised from service engagements and adjusted for the selected period.';
  const matrix = document.getElementById('profitability-matrix');
  if (matrix) {
    const matrixLabel = state.dimension === 'client' ? 'Client' : state.dimension === 'service' ? 'Service' : state.dimension === 'task' ? 'Task' : 'Person';
    matrix.innerHTML = data.length ? `<div class="profitability-matrix-title">Profitability matrix</div><div class="table-responsive"><table class="custom-table"><thead><tr><th>${matrixLabel}</th><th>Revenue</th><th>Cost</th><th>Net margin</th></tr></thead><tbody>${data.map(item => { const itemMargin = item.revenue - item.cost; return `<tr><td><strong>${item.label}</strong></td><td>₹${Math.round(item.revenue).toLocaleString('en-IN')}</td><td>₹${Math.round(item.cost).toLocaleString('en-IN')}</td><td style="font-weight:700;color:${itemMargin >= 0 ? '#059669' : '#dc2626'};">${itemMargin >= 0 ? '+' : ''}₹${Math.round(itemMargin).toLocaleString('en-IN')}</td></tr>`; }).join('')}</tbody></table></div>` : '';
  }

  if (typeof Chart === 'undefined' || data.length === 0) {
    ctx.style.display = 'none';
    if (note) note.textContent = data.length === 0 ? 'No matching profitability data for these filters.' : 'Charts are currently unavailable.';
    return;
  }
  ctx.style.display = 'block';
  const labels = data.map(item => item.label);
  const chartData = state.layout === 'doughnut'
    ? { labels, datasets: [{ label: 'Net margin', data: data.map(item => Math.max(0, item.revenue - item.cost)), backgroundColor: ['#b8924a', '#3b82f6', '#14b8a6', '#8b5cf6', '#f97316', '#ec4899', '#64748b'], borderWidth: 0 }] }
    : { labels, datasets: [{ label: 'Revenue', data: data.map(item => item.revenue), backgroundColor: '#c99a4a', borderRadius: 7 }, { label: 'Delivery cost', data: data.map(item => item.cost), backgroundColor: '#173a56', borderRadius: 7 }] };
  const compactBars = labels.length > 4;
  segmentChartInstance = new Chart(ctx, { type: state.layout === 'doughnut' ? 'doughnut' : 'bar', data: chartData, options: { responsive: true, maintainAspectRatio: false, datasets: { bar: { barPercentage: compactBars ? 0.52 : 0.72, categoryPercentage: compactBars ? 0.68 : 0.84, maxBarThickness: compactBars ? 22 : 36, borderSkipped: false } }, plugins: { legend: { position: 'bottom', labels: { font: { family: 'Plus Jakarta Sans', size: 11 }, boxWidth: 10, padding: 14 } }, tooltip: { callbacks: { label: context => `${context.dataset.label}: ₹${Number(context.raw || 0).toLocaleString('en-IN')}` } } }, scales: state.layout === 'bar' ? { y: { beginAtZero: true, ticks: { callback: value => `₹${Number(value).toLocaleString('en-IN')}` } }, x: { ticks: { maxRotation: compactBars ? 38 : 0, minRotation: 0, autoSkip: true, maxTicksLimit: 10 } } } : {} } });
}

// DARK MODE
window.toggleDarkMode = function() {
  const body = document.body;
  body.classList.toggle('dark-theme');
  const isDark = body.classList.contains('dark-theme');
  localStorage.setItem('dark-theme-active', isDark ? 'true' : 'false');
  
  // Toggle the icon display or label if necessary
  const icon = document.querySelector('.theme-toggle-btn svg');
  if (icon) {
    if (isDark) {
      icon.innerHTML = '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z"/>';
    } else {
      icon.innerHTML = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';
    }
  }
};

function initTheme() {
  const saved = localStorage.getItem('dark-theme-active');
  if (saved === 'true') {
    document.body.classList.add('dark-theme');
    const icon = document.querySelector('.theme-toggle-btn svg');
    if (icon) {
      icon.innerHTML = '<path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m0-12.728l.707.707m11.314 11.314l.707-.707M12 5a7 7 0 100 14 7 7 0 000-14z"/>';
    }
  }
}

// NOTIFICATIONS DRAWER
window.openNotificationsDrawer = function() {
  const drawer = document.getElementById('notifications-drawer');
  drawer.classList.add('active');
  renderNotificationsLog();
};

window.closeNotificationsDrawer = function() {
  const drawer = document.getElementById('notifications-drawer');
  drawer.classList.remove('active');
};

function renderNotificationsLog() {
  const logContainer = document.getElementById('notifications-log-container');
  
  const user = window.getCurrentActiveUser ? window.getCurrentActiveUser() : null;
  const activeUserId = user ? user.id : '';

  const allAlerts = window.State.notifications || [];
  const alerts = allAlerts.filter(n => !n.managerId || n.managerId === activeUserId);

  if (alerts.length === 0) {
    logContainer.innerHTML = `<p style="color: var(--text-muted); text-align: center; margin-top: 30px;">No alerts logged.</p>`;
    return;
  }

  logContainer.innerHTML = alerts.map(n => `
    <div style="padding: 16px; border-bottom: 1px solid var(--border-color); display: flex; flex-direction: column; gap: 8px;">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <span class="badge ${n.isCritical ? 'badge-inactive' : 'badge-prospect'}" style="background-color: ${n.isCritical ? 'rgba(231, 76, 60, 0.1)' : 'rgba(52, 152, 219, 0.1)'}; color: ${n.isCritical ? '#e74c3c' : '#3498db'};">${n.type}</span>
        <button onclick="dismissNotification('${n.id}')" style="background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 11px;">Dismiss</button>
      </div>
      <h4 style="font-size: 14px; font-weight: 600; color: var(--text-main);">${n.title}</h4>
      <p style="font-size: 12px; color: var(--text-muted);">${n.desc}</p>
      <div style="font-size: 11px; color: var(--text-muted);">Client Scope: <strong>${n.clientName}</strong></div>
    </div>
  `).join('');
}

window.dismissNotification = function(id) {
  window.State.notifications = window.State.notifications.filter(n => n.id !== id);
  window.saveState();
  renderNotificationsLog();
  renderDashboard();
};

// ─── JOBS TRACKER MODULE LOGIC ────────────────────────────────────────────────
// Global filter states for Job Board
let activeJobFilterPic = '';
let activeJobFilterMic = '';
let activeJobScope = 'all';

window.autoGenerateJobsFromEngagements = function() {
  if (!window.State.jobs) window.State.jobs = [];

  const clients = window.State.clients.filter(c => !c.isArchived);
  const engagements = window.State.engagements || [];
  const presetServices = window.State.services || [];

  let generatedCount = 0;

  clients.forEach(c => {
    const clientEngs = engagements.filter(e => e.clientId === c.id);
    clientEngs.forEach(e => {
      const svcName = window.SERVICES_MAP[e.serviceId] || e.serviceId;
      const periods = [];

      // Determine periods based on frequency
      if (e.frequency === 'Monthly') {
        // e.g. July 2026, August 2026
        periods.push({
          label: 'July 2026',
          dueDate: e.serviceId === 'gst_3b' ? '2026-08-20' : e.serviceId === 'gst_r1' ? '2026-08-11' : '2026-08-25'
        });
        periods.push({
          label: 'August 2026',
          dueDate: e.serviceId === 'gst_3b' ? '2026-09-20' : e.serviceId === 'gst_r1' ? '2026-09-11' : '2026-09-25'
        });
      } else if (e.frequency === 'Quarterly') {
        periods.push({
          label: 'Q1 FY 2026-27',
          dueDate: '2026-08-25'
        });
      } else if (e.frequency === 'Annual') {
        periods.push({
          label: 'AY 2026-27',
          dueDate: '2026-09-30'
        });
      } else {
        // One-time / Certificates
        periods.push({
          label: e.description ? `Project (${e.description})` : 'Project Engagement',
          dueDate: '2026-08-31'
        });
      }

      periods.forEach(p => {
        const jobTitle = `${svcName} - ${p.label}`;

        // Verify duplicate check (client + service + period label)
        const jobExists = window.State.jobs.some(j => 
          j.clientId === c.id && 
          j.serviceId === e.serviceId && 
          j.title === jobTitle
        );

        if (!jobExists) {
          // Auto create job assigned to the MIC Manager of the client (handling execution)
          const assignedUserId = c.micUserId || c.picUserId || '';
          
          window.State.jobs.push({
            id: `job_auto_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
            title: jobTitle,
            clientId: c.id,
            serviceId: e.serviceId,
            assignedUserId,
            dueDate: p.dueDate,
            status: 'To Do',
            completionDate: ''
          });
          generatedCount++;
        }
      });
    });
  });

  if (generatedCount > 0) {
    window.saveState();
    console.log(`Auto-generated ${generatedCount} repetitive compliance jobs based on client engagements.`);
  }
};

window.renderJobsModule = function() {
  // Always trigger auto-generation on page display to match client changes
  window.autoGenerateJobsFromEngagements();

  const container = document.getElementById('view-jobs');
  if (!container) return;

  const isFullscreen = document.body.classList.contains('fullscreen-jobs-mode');

  const jobs = window.State.jobs || [];
  const clients = window.State.clients.filter(c => !c.isArchived);
  const team = window.State.team.filter(t => t.status === 'Active');

  // Compute overall status metrics
  const todoCount = jobs.filter(j => j.status === 'To Do').length;
  const progressCount = jobs.filter(j => j.status === 'In Progress').length;
  const reviewCount = jobs.filter(j => j.status === 'Under Review').length;
  const completedCount = jobs.filter(j => j.status === 'Completed').length;

  // Filter lists for PIC & MIC selectors
  const partners = team.filter(t => t.role === 'super_admin');
  const managers = team.filter(t => t.role === 'manager');

  // Fullscreen toggle action button
  const actionButtonHtml = isFullscreen 
    ? `<button onclick="window.close()" class="btn btn-secondary" style="padding:6px 12px; font-size:12px;">❌ Close Fullscreen</button>`
    : `<button onclick="window.open(window.location.pathname + '?view=jobs-fullscreen', '_blank')" class="btn btn-secondary" style="padding:6px 12px; font-size:12px;">🖥️ Open Fullscreen</button>`;

  const user = window.getCurrentActiveUser();
  if (!user) return;
  let htmlContent = '';

  const myAssignedJobs = jobs.filter(job => job.assignedUserId === user.id);
  const returnedToMeCount = myAssignedJobs.filter(job => Boolean(job.feedback)).length;
  const scopeTabsHtml = `
    <div class="job-scope-tabs" role="tablist" aria-label="Task scope">
      ${user.role !== 'staff' ? `
        <button type="button" role="tab" aria-selected="${activeJobScope === 'all'}" class="job-scope-tab ${activeJobScope === 'all' ? 'is-active' : ''}" onclick="setJobScope('all')">All tasks <span>${jobs.length}</span></button>
      ` : ''}
      <button type="button" role="tab" aria-selected="${activeJobScope === 'mine' || user.role === 'staff'}" class="job-scope-tab ${activeJobScope === 'mine' || user.role === 'staff' ? 'is-active' : ''}" onclick="setJobScope('mine')">Assigned to me <span>${myAssignedJobs.length}</span>${returnedToMeCount ? `<em>${returnedToMeCount} returned</em>` : ''}</button>
    </div>`;

  // Compute filtered jobs list for List View
  let filteredJobs = [...jobs];
  if (user.role === 'staff' || activeJobScope === 'mine') {
    filteredJobs = filteredJobs.filter(j => j.assignedUserId === user.id);
  }
  if (activeJobFilterPic) {
    filteredJobs = filteredJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      const picId = j.picUserId || (client ? client.picUserId : null);
      return picId === activeJobFilterPic;
    });
  }
  if (activeJobFilterMic) {
    filteredJobs = filteredJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      const micId = j.micUserId || (client ? client.micUserId : null);
      return micId === activeJobFilterMic;
    });
  }
  const showForm = (user.role !== 'staff');

  if (isFullscreen) {
    // Fullscreen Layout: 100% width columns board
    htmlContent = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
        <h2 style="font-size: 18px; font-weight:700; color:var(--primary); margin:0;">SSA Kartavya - Fullscreen Compliance Job Board</h2>
        <div style="display: flex; gap: 8px; align-items: center;">
          <!-- View Switcher Toggle -->
          <div style="display: inline-flex; align-items: center; background: var(--bg-body); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 2px; margin-right: 8px;">
            <button onclick="setJobBoardView('card')" class="btn" style="padding: 4px 8px; font-size: 11px; border: none; margin: 0; background: ${window.State.jobBoardView === 'card' ? '#1a2e52' : 'transparent'}; color: ${window.State.jobBoardView === 'card' ? '#fff' : 'var(--text-muted)'}; font-weight: 600; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 4px;">🎴 Card</button>
            <button onclick="setJobBoardView('list')" class="btn" style="padding: 4px 8px; font-size: 11px; border: none; margin: 0; background: ${window.State.jobBoardView === 'list' ? '#1a2e52' : 'transparent'}; color: ${window.State.jobBoardView === 'list' ? '#fff' : 'var(--text-muted)'}; font-weight: 600; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 4px;">📝 List</button>
          </div>

          <select id="board-filter-pic" onchange="onJobBoardFilterPicChange(this.value)" class="select-filter" style="padding: 6px 12px; font-size:12px; min-width: 140px;">
            <option value="">Filter by PIC Partner</option>
            ${partners.map(p => `<option value="${p.id}" ${p.id === activeJobFilterPic ? 'selected' : ''}>PIC: ${p.name}</option>`).join('')}
          </select>
          <select id="board-filter-mic" onchange="onJobBoardFilterMicChange(this.value)" class="select-filter" style="padding: 6px 12px; font-size:12px; min-width: 140px;">
            <option value="">Filter by MIC Manager</option>
            ${managers.map(m => `<option value="${m.id}" ${m.id === activeJobFilterMic ? 'selected' : ''}>MIC: ${m.name}</option>`).join('')}
          </select>
          ${(activeJobFilterPic || activeJobFilterMic) ? `<button onclick="clearJobBoardFilters()" class="btn btn-secondary" style="padding:6px 12px; font-size:11px;">Reset</button>` : ''}
          ${actionButtonHtml}
        </div>
      </div>

      ${scopeTabsHtml}

      <!-- Top KPI cards in Fullscreen -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px;">
        <div style="background: rgba(231,76,60,0.06); border: 1px solid rgba(231,76,60,0.2); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">To Do</div>
          <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #e74c3c;">${todoCount}</div>
        </div>
        <div style="background: rgba(241,196,15,0.06); border: 1px solid rgba(241,196,15,0.2); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">In Progress</div>
          <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #f1c40f;">${progressCount}</div>
        </div>
        <div style="background: rgba(52,152,219,0.06); border: 1px solid rgba(52,152,219,0.2); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Under Review</div>
          <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #3498db;">${reviewCount}</div>
        </div>
        <div style="background: rgba(46,204,113,0.06); border: 1px solid rgba(46,204,113,0.2); padding: 10px; border-radius: var(--radius-md);">
          <div style="font-size: 10px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Filing Completed</div>
          <div style="font-size: 18px; font-weight: bold; margin-top: 4px; color: #2ecc71;">${completedCount}</div>
        </div>
      </div>

      <div class="card" style="margin-bottom:0; flex-grow:1; display:flex; flex-direction:column;">
        <div class="card-body" style="padding: 16px; overflow-x: auto; flex-grow:1;">
          ${window.State.jobBoardView === 'list' ? `
            ${window.renderJobListView(filteredJobs, user)}
          ` : `
            <div style="display: flex; gap: 16px; align-items: start; width: 100%; min-width: 1000px;">
              ${renderBoardColumn('To Do', '#e74c3c')}
              ${renderBoardColumn('In Progress', '#f1c40f')}
              ${renderBoardColumn('Under Review', '#3498db')}
              ${renderBoardColumn('Completed', '#2ecc71')}
            </div>
          `}
        </div>
      </div>
    `;
  } else {
    // Standard Dashboard Layout
    htmlContent = `
      <!-- Top KPI cards -->
      <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px;">
        <div style="background: rgba(231,76,60,0.06); border: 1px solid rgba(231,76,60,0.2); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">To Do</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: #e74c3c;">${todoCount}</div>
        </div>
        <div style="background: rgba(241,196,15,0.06); border: 1px solid rgba(241,196,15,0.2); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">In Progress</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: #f1c40f;">${progressCount}</div>
        </div>
        <div style="background: rgba(52,152,219,0.06); border: 1px solid rgba(52,152,219,0.2); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Under Review</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: #3498db;">${reviewCount}</div>
        </div>
        <div style="background: rgba(46,204,113,0.06); border: 1px solid rgba(46,204,113,0.2); padding: 14px; border-radius: var(--radius-md);">
          <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase;">Filing Completed</div>
          <div style="font-size: 20px; font-weight: bold; margin-top: 4px; color: #2ecc71;">${completedCount}</div>
        </div>
      </div>

      <!-- Manager/Partner Pending Alerts Notification Banner -->
      ${user.role !== 'staff' ? '<div id="jobs-pending-summary-bar" style="margin-bottom: 24px; display: grid; grid-template-columns: 1fr 1fr; gap: 16px;"></div>' : ''}

      ${scopeTabsHtml}

      <div style="display: ${showForm ? 'grid' : 'block'}; ${showForm ? 'grid-template-columns: 2fr 1fr;' : ''} gap: 24px; margin-bottom: 24px;">
        <!-- Job Status Board Columns -->
        <div class="card" style="display:flex; flex-direction:column; width: 100%;">
          <div class="card-header" style="flex-wrap: wrap; gap: 12px; display: flex; justify-content: space-between; align-items: center;">
            <h3 class="card-title">${activeJobScope === 'mine' || user.role === 'staff' ? 'Tasks assigned to me' : 'Job Board Columns'}</h3>
            <div style="display: flex; gap: 8px; align-items: center;">
              <!-- View Switcher Toggle -->
              <div style="display: inline-flex; align-items: center; background: var(--bg-body); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 2px; margin-right: 8px;">
                <button onclick="setJobBoardView('card')" class="btn" style="padding: 4px 8px; font-size: 11px; border: none; margin: 0; background: ${window.State.jobBoardView === 'card' ? '#1a2e52' : 'transparent'}; color: ${window.State.jobBoardView === 'card' ? '#fff' : 'var(--text-muted)'}; font-weight: 600; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 4px;">🎴 Card</button>
                <button onclick="setJobBoardView('list')" class="btn" style="padding: 4px 8px; font-size: 11px; border: none; margin: 0; background: ${window.State.jobBoardView === 'list' ? '#1a2e52' : 'transparent'}; color: ${window.State.jobBoardView === 'list' ? '#fff' : 'var(--text-muted)'}; font-weight: 600; cursor: pointer; border-radius: 4px; display: flex; align-items: center; gap: 4px;">📝 List</button>
              </div>

              ${user.role !== 'staff' ? `
              <select id="board-filter-pic" onchange="onJobBoardFilterPicChange(this.value)" class="select-filter" style="padding: 6px 12px; font-size:12px; min-width: 140px;">
                <option value="">Filter by PIC Partner</option>
                ${partners.map(p => `<option value="${p.id}" ${p.id === activeJobFilterPic ? 'selected' : ''}>PIC: ${p.name}</option>`).join('')}
              </select>
              <select id="board-filter-mic" onchange="onJobBoardFilterMicChange(this.value)" class="select-filter" style="padding: 6px 12px; font-size:12px; min-width: 140px;">
                <option value="">Filter by MIC Manager</option>
                ${managers.map(m => `<option value="${m.id}" ${m.id === activeJobFilterMic ? 'selected' : ''}>MIC: ${m.name}</option>`).join('')}
              </select>
              ${(activeJobFilterPic || activeJobFilterMic) ? `<button onclick="clearJobBoardFilters()" class="btn btn-secondary" style="padding:6px 12px; font-size:11px;">Reset</button>` : ''}
              ` : ''}
              ${actionButtonHtml}
            </div>
          </div>
          <div class="card-body" style="padding: 16px; overflow-x: auto;">
            ${window.State.jobBoardView === 'list' ? `
              ${window.renderJobListView(filteredJobs, user)}
            ` : `
              <div style="display: flex; gap: 16px; align-items: start; width: 100%; min-width: 1000px;">
                ${renderBoardColumn('To Do', '#e74c3c')}
                ${renderBoardColumn('In Progress', '#f1c40f')}
                ${renderBoardColumn('Under Review', '#3498db')}
                ${renderBoardColumn('Completed', '#2ecc71')}
              </div>
            `}
          </div>
        </div>

        ${showForm ? `
        <!-- Add Job Form Card -->
        <div class="card" style="align-self: start;">
          <div class="card-header">
            <h3 class="card-title">Create Compliance Job</h3>
          </div>
          <div class="card-body">
            <form id="job-log-form" onsubmit="saveJobEntry(event)" style="display: flex; flex-direction: column; gap: 14px;">
              <div class="form-group">
                <label class="form-label">Job / Task Title *</label>
                <input type="text" id="job-title" class="form-input" placeholder="e.g. Audit Report Filing Q1" required>
              </div>
              <div class="form-group">
                <label class="form-label">Client Association *</label>
                <select id="job-client" onchange="onJobClientChange(this.value)" class="form-select" required>
                  <option value="">— Select Client —</option>
                  ${clients.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Service Type Context *</label>
                <select id="job-service" class="form-select" required>
                  <option value="">— Select Service —</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Partner in Charge (PIC) *</label>
                <select id="job-pic" class="form-select" required>
                  <option value="">— Select PIC Partner —</option>
                  ${team.filter(t => t.role === 'super_admin').map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Manager in Charge (MIC) *</label>
                <select id="job-mic" class="form-select" required>
                  <option value="">— Select MIC Manager —</option>
                  ${team.filter(t => t.role === 'manager' || t.role === 'super_admin').map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Staff in Charge (SIC) *</label>
                <select id="job-assigned" class="form-select" required>
                  <option value="">— Select SIC Owner —</option>
                  ${team.map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('')}
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Task Priority *</label>
                <select id="job-priority" class="form-select" required>
                  <option value="Very Urgent">Very Urgent</option>
                  <option value="Urgent">Urgent</option>
                  <option value="High">High</option>
                  <option value="Moderate" selected>Moderate</option>
                  <option value="Low">Low</option>
                  <option value="Very Low">Very Low</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label">Compliance Due Date *</label>
                <input type="date" id="job-due" class="form-input" required>
              </div>
              <button type="submit" class="btn btn-accent" style="width: 100%; justify-content: center; margin-top: 10px;">🆕 Create Job Task</button>
            </form>
          </div>
        </div>
        ` : ''}
      </div>
    `;
  }

  container.innerHTML = htmlContent;

  if (!isFullscreen) {
    // Set default due date in form to next week
    const nextWeek = new Date();
    nextWeek.setDate(nextWeek.getDate() + 7);
    const dueEl = document.getElementById('job-due');
    if (dueEl) dueEl.value = window.toLocalISODate(nextWeek);

    if (user.role !== 'staff') {
      renderJobsPendingSummaryBar();
    }
  }
};

function renderBoardColumn(status, headerColor) {
  let jobs = (window.State.jobs || []).filter(j => j.status === status);

  // Staff may only see their own work; the Assigned to me tab gives every role
  // the same focused view of tasks where they are the execution owner.
  const user = window.getCurrentActiveUser();
  if (user.role === 'staff' || activeJobScope === 'mine') {
    jobs = jobs.filter(j => j.assignedUserId === user.id);
  }

  // Apply PIC filter if selected
  if (activeJobFilterPic) {
    jobs = jobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      const picId = j.picUserId || (client ? client.picUserId : null);
      return picId === activeJobFilterPic;
    });
  }

  // Apply MIC filter if selected
  if (activeJobFilterMic) {
    jobs = jobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      const micId = j.micUserId || (client ? client.micUserId : null);
      return micId === activeJobFilterMic;
    });
  }

  const cardHtmls = jobs.map(j => {
    const cl = window.State.clients.find(c => c.id === j.clientId);
    const owner = window.State.team.find(t => t.id === j.assignedUserId);
    const svcName = window.SERVICES_MAP[j.serviceId] || j.serviceId;
    const picId = j.picUserId || (cl ? cl.picUserId : null);
    const micId = j.micUserId || (cl ? cl.micUserId : null);
    const picUser = window.State.team.find(t => t.id === picId) || null;
    const micUser = window.State.team.find(t => t.id === micId) || null;
    const sicUser = owner;

    // Resolve priority badge
    const priority = j.priority || 'Moderate';
    let priorityBg = '#f1c40f';
    let priorityColor = '#333';
    if (priority === 'Very Urgent') { priorityBg = '#e74c3c'; priorityColor = '#fff'; }
    else if (priority === 'Urgent') { priorityBg = '#e67e22'; priorityColor = '#fff'; }
    else if (priority === 'High') { priorityBg = '#f39c12'; priorityColor = '#fff'; }
    else if (priority === 'Moderate') { priorityBg = '#f1c40f'; priorityColor = '#333'; }
    else if (priority === 'Low') { priorityBg = '#3498db'; priorityColor = '#fff'; }
    else if (priority === 'Very Low') { priorityBg = '#95a5a6'; priorityColor = '#fff'; }
    const priorityBadge = `<span class="badge" style="background:${priorityBg}; color:${priorityColor}; font-size:9px; padding:2px 6px; font-weight:700; border-radius:4px; text-transform:uppercase;">${priority}</span>`;

    let subText = `Due: <code>${j.dueDate}</code>`;
    if (j.status === 'Completed' && j.completionDate) {
      subText = `<span style="color:#2ecc71;">Filing completed: ${j.completionDate}</span>`;
    }

    // Default card style variables
    let cardBg = 'var(--bg-card)';
    let cardBorder = 'var(--border-color)';
    let urgencyBadge = '';

    if (j.status !== 'Completed') {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const due = new Date(j.dueDate);
      due.setHours(0, 0, 0, 0);
      const diffTime = due - today;
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

      if (diffDays < 0) {
        // Critical / Overdue -> Soft Red
        cardBg = 'rgba(231, 76, 60, 0.08)';
        cardBorder = 'rgba(231, 76, 60, 0.4)';
        urgencyBadge = `<span class="badge" style="background:#e74c3c; color:#fff; font-size:8px; padding:1px 4px; margin-left:6px; font-weight:700;">OVERDUE</span>`;
      } else if (diffDays === 0) {
        // Due Today -> Soft Red
        cardBg = 'rgba(231, 76, 60, 0.08)';
        cardBorder = 'rgba(231, 76, 60, 0.4)';
        urgencyBadge = `<span class="badge" style="background:#e74c3c; color:#fff; font-size:8px; padding:1px 4px; margin-left:6px; font-weight:700;">DUE TODAY</span>`;
      } else if (diffDays >= 1 && diffDays <= 3) {
        // Near -> Soft Orange
        cardBg = 'rgba(230, 126, 34, 0.08)';
        cardBorder = 'rgba(230, 126, 34, 0.4)';
        urgencyBadge = `<span class="badge" style="background:#e67e22; color:#fff; font-size:8px; padding:1px 4px; margin-left:6px; font-weight:700;">NEAR DUE</span>`;
      } else if (diffDays >= 4 && diffDays <= 7) {
        // Medium -> Soft Yellow
        cardBg = 'rgba(241, 196, 15, 0.08)';
        cardBorder = 'rgba(241, 196, 15, 0.4)';
        urgencyBadge = `<span class="badge" style="background:#f1c40f; color:#333; font-size:8px; padding:1px 4px; margin-left:6px; font-weight:700;">MEDIUM</span>`;
      } else {
        // Far -> Soft Green
        cardBg = 'rgba(46, 204, 113, 0.08)';
        cardBorder = 'rgba(46, 204, 113, 0.4)';
        urgencyBadge = `<span class="badge" style="background:#2ecc71; color:#fff; font-size:8px; padding:1px 4px; margin-left:6px; font-weight:700;">ON SCHEDULE</span>`;
      }
    } else {
      // Completed -> Subtle Light Green
      cardBg = 'rgba(46, 204, 113, 0.04)';
      cardBorder = 'rgba(46, 204, 113, 0.2)';
    }

    return `
      <div style="background: ${cardBg}; border: 1px solid ${cardBorder}; border-left: 4px solid ${headerColor}; border-radius: 8px; padding: 14px; margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px; box-shadow: var(--shadow-sm); font-size:12px; position:relative; transition: all 0.2s ease;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
          <div style="font-weight: 700; color: var(--text-main); font-size: 13px; line-height: 1.3;">${j.title}</div>
          ${urgencyBadge}
        </div>
        <div style="display: flex; flex-direction: column; gap: 2px;">
          <div style="color:var(--text-muted); font-size:10px; text-transform: uppercase; font-weight: 600; letter-spacing: 0.3px;">Client</div>
          <strong style="color:var(--text-main); font-size:12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${cl ? cl.name : j.clientId}">🏢 ${cl ? cl.name : j.clientId}</strong>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; gap:4px; margin-top: 2px;">
          <span class="badge badge-staff" style="font-size:9px; padding:2px 6px; font-weight: 600; text-transform: uppercase;">${svcName}</span>
          ${priorityBadge}
        </div>
        
        <!-- Optimized Supervisor Grid -->
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 4px; background: var(--bg-body); padding: 8px; border-radius: 6px; border: 1px solid var(--border-color); text-align: center; margin-top: 4px;">
          <div style="border-right: 1px solid var(--border-color); padding: 2px;">
            <div style="font-size: 8px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px;">PIC</div>
            <div style="font-size: 11px; font-weight: 600; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="Partner in Charge: ${picUser ? picUser.name : 'Unassigned'}">${picUser ? picUser.name.split(' ')[0] : '—'}</div>
          </div>
          <div style="border-right: 1px solid var(--border-color); padding: 2px;">
            <div style="font-size: 8px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px;">MIC</div>
            <div style="font-size: 11px; font-weight: 600; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="Manager in Charge: ${micUser ? micUser.name : 'Unassigned'}">${micUser ? micUser.name.split(' ')[0] : '—'}</div>
          </div>
          <div style="padding: 2px;">
            <div style="font-size: 8px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.3px;">SIC</div>
            <div style="font-size: 11px; font-weight: 600; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="Staff in Charge: ${sicUser ? sicUser.name : 'Unassigned'}">${sicUser ? sicUser.name.split(' ')[0] : '—'}</div>
          </div>
        </div>

        <div style="font-size: 11px; color: var(--text-muted); margin-top: 2px; display: flex; align-items: center; gap: 4px;">
          📅 ${subText}
        </div>
        
        <!-- Feedback warning if task was returned -->
        ${j.feedback ? `
          <div style="background: rgba(231,76,60,0.05); border-left: 3px solid #e74c3c; padding: 8px; border-radius: 4px; margin-top: 4px; font-size: 11px;">
            <strong style="color:#e74c3c; display: block; margin-bottom: 2px;">Returned comments:</strong>
            <div style="color:var(--text-muted); font-style:italic; word-break:break-word; line-height: 1.4;">"${j.feedback}"</div>
          </div>
        ` : ''}

        <!-- Status Switcher dropdown -->
        <div style="margin-top:6px; display:flex; gap:6px; align-items:center; border-top: 1px solid var(--border-color); padding-top: 8px;">
          <select onchange="updateJobStatus('${j.id}', this.value)" style="flex:1; font-size: 11px; padding: 5px; border-radius:4px; border:1px solid var(--border-color); background:var(--bg-card); color:var(--text-main); cursor: pointer; outline: none;">
            <option value="To Do" ${j.status === 'To Do' ? 'selected' : ''}>To Do</option>
            <option value="In Progress" ${j.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
            <option value="Under Review" ${j.status === 'Under Review' ? 'selected' : ''}>Submit for Review</option>
            <option value="Completed" ${j.status === 'Completed' ? 'selected' : ''}>Filing Completed</option>
          </select>
          ${(user.role === 'super_admin' || user.role === 'manager') ? `
            <button onclick="openEditJobModal('${j.id}')" style="background:none; border:none; color:var(--text-muted); cursor:pointer; font-size:12px; padding:2px; display: flex; align-items: center;" title="Edit Task Settings">✏️</button>
          ` : ''}
          ${user.role === 'super_admin' ? `
            <button onclick="deleteJob('${j.id}')" style="background:none; border:none; color:#e74c3c; cursor:pointer; display: flex; align-items: center;" title="Delete task">🗑</button>
          ` : ''}
        </div>

        <!-- Manager Return Button -->
        ${(j.status === 'Under Review' && (user.role === 'super_admin' || user.role === 'manager')) ? `
          <button onclick="returnJobTask('${j.id}')" class="btn btn-secondary" style="margin-top: 4px; width: 100%; font-size: 11px; padding: 6px; border-color: rgba(231,76,60,0.3); color: #e74c3c; font-weight: bold; background: rgba(231,76,60,0.04); display: flex; justify-content: center; align-items: center; gap: 4px;">
            ↩️ Return with Comments
          </button>
        ` : ''}
      </div>
    `;
  }).join('');

  return `
    <div style="flex: 1; min-width: 220px; background: rgba(0,0,0,0.015); border: 1px solid var(--border-color); border-radius: 8px; min-height: 400px; padding: 10px; display:flex; flex-direction:column;">
      <h4 style="font-size: 13px; font-weight: 700; padding-bottom: 8px; border-bottom: 3px solid ${headerColor}; margin-bottom: 12px; color: var(--text-main); display:flex; justify-content:space-between;">
        <span>${status}</span>
        <span style="background:${headerColor}; color:#fff; border-radius:50px; padding: 2px 6px; font-size:10px;">${jobs.length}</span>
      </h4>
      <div style="flex-grow:1; overflow-y:auto; max-height: 480px;">
        ${cardHtmls || `<div style="text-align:center; color:var(--text-muted); font-size:11px; margin-top:20px; padding:10px;">No jobs in this column</div>`}
      </div>
    </div>
  `;
}

window.renderJobListView = function(filteredJobs, user) {
  return `
    <div style="overflow-x: auto; width: 100%;">
      <table class="table" style="width: 100%; border-collapse: collapse; font-size: 12px; text-align: left; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md);">
        <thead>
          <tr style="border-bottom: 2px solid var(--border-color); background: var(--bg-body); color: var(--text-muted); font-weight: 700; text-transform: uppercase; font-size: 10px; letter-spacing: 0.3px;">
            <th style="padding: 12px;">Task Details</th>
            <th style="padding: 12px;">Priority</th>
            <th style="padding: 12px;">Supervisors</th>
            <th style="padding: 12px;">Due Date</th>
            <th style="padding: 12px;">Status</th>
            <th style="padding: 12px; text-align: right;">Actions</th>
          </tr>
        </thead>
        <tbody>
          ${filteredJobs.length === 0 ? `
            <tr>
              <td colspan="6" style="padding: 24px; text-align: center; color: var(--text-muted);">No compliance tasks found matching the criteria.</td>
            </tr>
          ` : filteredJobs.map(j => {
            const cl = window.State.clients.find(c => c.id === j.clientId);
            const owner = window.State.team.find(t => t.id === j.assignedUserId);
            const svcName = window.SERVICES_MAP[j.serviceId] || j.serviceId;
            const picId = j.picUserId || (cl ? cl.picUserId : null);
            const micId = j.micUserId || (cl ? cl.micUserId : null);
            const picUser = window.State.team.find(t => t.id === picId) || null;
            const micUser = window.State.team.find(t => t.id === micId) || null;
            const sicUser = owner;
            
            // Priority
            const priority = j.priority || 'Moderate';
            let priorityBg = '#f1c40f';
            let priorityColor = '#333';
            if (priority === 'Very Urgent') { priorityBg = '#e74c3c'; priorityColor = '#fff'; }
            else if (priority === 'Urgent') { priorityBg = '#e67e22'; priorityColor = '#fff'; }
            else if (priority === 'High') { priorityBg = '#f39c12'; priorityColor = '#fff'; }
            else if (priority === 'Moderate') { priorityBg = '#f1c40f'; priorityColor = '#333'; }
            else if (priority === 'Low') { priorityBg = '#3498db'; priorityColor = '#fff'; }
            else if (priority === 'Very Low') { priorityBg = '#95a5a6'; priorityColor = '#fff'; }
            const priorityBadge = `<span class="badge" style="background:${priorityBg}; color:${priorityColor}; font-size:9px; padding:2px 6px; font-weight:700; border-radius:4px; text-transform:uppercase;">${priority}</span>`;

            // Urgency color
            let isOverdue = false;
            let isToday = false;
            let dueColor = 'var(--text-main)';
            if (j.status !== 'Completed') {
              const today = new Date();
              today.setHours(0,0,0,0);
              const due = new Date(j.dueDate);
              due.setHours(0,0,0,0);
              const diff = due - today;
              const diffDays = Math.ceil(diff / (1000 * 60 * 60 * 24));
              if (diffDays < 0) { isOverdue = true; dueColor = '#e74c3c'; }
              else if (diffDays === 0) { isToday = true; dueColor = '#e74c3c'; }
            }

            const dateText = j.status === 'Completed' && j.completionDate 
              ? `<span style="color:#2ecc71;">Filing completed: ${j.completionDate}</span>`
              : `<span style="color:${dueColor}; font-weight: ${isOverdue || isToday ? 'bold' : 'normal'};">${j.dueDate} ${isOverdue ? '⚠️ OVERDUE' : ''} ${isToday ? 'DUE TODAY' : ''}</span>`;

            return `
              <tr style="border-bottom: 1px solid var(--border-color); vertical-align: middle;">
                <td style="padding: 12px;">
                  <div style="font-weight: 700; color: var(--text-main); font-size: 13px; margin-bottom: 2px;">${j.title}</div>
                  <div style="font-size: 11px; color: var(--text-muted);">
                    🏢 ${cl ? cl.name : j.clientId} &nbsp;•&nbsp; 
                    <span class="badge badge-staff" style="font-size: 8px; padding: 1px 4px; font-weight: 600; text-transform: uppercase;">${svcName}</span>
                  </div>
                </td>
                <td style="padding: 12px;">${priorityBadge}</td>
                <td style="padding: 12px;">
                  <div style="display: flex; gap: 8px; font-size: 11px;">
                    <span title="Partner in Charge: ${picUser ? picUser.name : 'Unassigned'}">👑 <strong>${picUser ? picUser.name.split(' ')[0] : '—'}</strong></span>
                    <span title="Manager in Charge: ${micUser ? micUser.name : 'Unassigned'}">👔 <strong>${micUser ? micUser.name.split(' ')[0] : '—'}</strong></span>
                    <span title="Staff in Charge: ${sicUser ? sicUser.name : 'Unassigned'}">👤 <strong>${sicUser ? sicUser.name.split(' ')[0] : '—'}</strong></span>
                  </div>
                </td>
                <td style="padding: 12px;">${dateText}</td>
                <td style="padding: 12px;">
                  <div style="display: flex; flex-direction: column; gap: 4px;">
                    <select onchange="updateJobStatus('${j.id}', this.value)" style="font-size: 11px; padding: 4px; border-radius:4px; border:1px solid var(--border-color); background:var(--bg-card); color:var(--text-main); outline: none; cursor: pointer;">
                      <option value="To Do" ${j.status === 'To Do' ? 'selected' : ''}>To Do</option>
                      <option value="In Progress" ${j.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                      <option value="Under Review" ${j.status === 'Under Review' ? 'selected' : ''}>Submit for Review</option>
                      <option value="Completed" ${j.status === 'Completed' ? 'selected' : ''}>Filing Completed</option>
                    </select>
                    <!-- Manager Return Button inside List View row -->
                    ${(j.status === 'Under Review' && (user.role === 'super_admin' || user.role === 'manager')) ? `
                      <button onclick="returnJobTask('${j.id}')" class="btn btn-secondary" style="font-size: 9px; padding: 2px 4px; border-color: rgba(231,76,60,0.3); color: #e74c3c; font-weight: bold; background: rgba(231,76,60,0.04); width: 100%; text-align: center;">
                        ↩️ Return Comments
                      </button>
                    ` : ''}
                  </div>
                  ${j.feedback ? `
                    <div style="font-size: 10px; color: #e74c3c; margin-top: 4px; font-style: italic; max-width: 200px; word-break: break-all;">Returned: "${j.feedback}"</div>
                  ` : ''}
                </td>
                <td style="padding: 12px; text-align: right;">
                  <div style="display: inline-flex; gap: 8px;">
                    ${(user.role === 'super_admin' || user.role === 'manager') ? `
                      <button onclick="openEditJobModal('${j.id}')" class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;">✏️ Edit</button>
                    ` : ''}
                    ${user.role === 'super_admin' ? `
                      <button onclick="deleteJob('${j.id}')" class="btn" style="padding: 4px 8px; font-size: 11px; background: rgba(231,76,60,0.1); color: #e74c3c; border: 1px solid rgba(231,76,60,0.3);">🗑 Delete</button>
                    ` : ''}
                  </div>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    </div>
  `;
}

function renderJobsPendingSummaryBar() {
  const bar = document.getElementById('jobs-pending-summary-bar');
  if (!bar) return;

  const jobs = window.State.jobs || [];
  const pendingJobs = jobs.filter(j => j.status !== 'Completed');

  const partnersSummary = window.State.team.filter(t => t.role === 'super_admin' && t.status === 'Active').map(p => {
    const count = pendingJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      return client && client.picUserId === p.id;
    }).length;

    const todayStr = window.toLocalISODate();
    const overdueCount = pendingJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      return client && client.picUserId === p.id && j.dueDate < todayStr;
    }).length;

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; padding:4px 0; border-bottom:1px solid var(--border-color);">
        <span><strong>${p.name}</strong></span>
        <span style="font-weight:600;">
          <span style="color:var(--text-main);">${count} pending</span>
          ${overdueCount > 0 ? `· <span style="color:#e74c3c; font-weight:700;">${overdueCount} overdue</span>` : ''}
        </span>
      </div>
    `;
  }).join('');

  const managersSummary = window.State.team.filter(t => t.role === 'manager' && t.status === 'Active').map(m => {
    const count = pendingJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      return client && client.micUserId === m.id;
    }).length;

    const todayStr = window.toLocalISODate();
    const overdueCount = pendingJobs.filter(j => {
      const client = window.State.clients.find(c => c.id === j.clientId);
      return client && client.micUserId === m.id && j.dueDate < todayStr;
    }).length;

    return `
      <div style="display:flex; justify-content:space-between; align-items:center; font-size:12px; padding:4px 0; border-bottom:1px solid var(--border-color);">
        <span><strong>${m.name}</strong></span>
        <span style="font-weight:600;">
          <span style="color:var(--text-main);">${count} pending</span>
          ${overdueCount > 0 ? `· <span style="color:#e74c3c; font-weight:700;">${overdueCount} overdue</span>` : ''}
        </span>
      </div>
    `;
  }).join('');

  bar.innerHTML = `
    <div class="card" style="padding:14px; border:1px solid var(--border-color);">
      <h4 style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">PIC Workloads (Partners)</h4>
      <div>${partnersSummary || '<div style="font-size:12px; color:var(--text-muted);">No active partners registered.</div>'}</div>
    </div>
    <div class="card" style="padding:14px; border:1px solid var(--border-color);">
      <h4 style="font-size:12px; font-weight:700; color:var(--text-muted); margin-bottom:8px; text-transform:uppercase; letter-spacing:0.5px;">MIC Workloads (Managers)</h4>
      <div>${managersSummary || '<div style="font-size:12px; color:var(--text-muted);">No active managers registered.</div>'}</div>
    </div>
  `;
}

window.setJobBoardView = function(view) {
  window.State.jobBoardView = view || 'card';
  window.saveState();
  renderJobsModule();
};

window.setJobScope = function(scope) {
  activeJobScope = scope === 'mine' ? 'mine' : 'all';
  renderJobsModule();
};

window.onJobBoardFilterPicChange = function(picId) {
  activeJobFilterPic = picId;
  renderJobsModule();
};

window.onJobBoardFilterMicChange = function(micId) {
  activeJobFilterMic = micId;
  renderJobsModule();
};

window.clearJobBoardFilters = function() {
  activeJobFilterPic = '';
  activeJobFilterMic = '';
  renderJobsModule();
};
window.onJobClientChange = function(clientId) {
  const sel = document.getElementById('job-service');
  if (!sel) return;

  if (!clientId) {
    sel.innerHTML = `<option value="">— Select Service —</option>`;
    return;
  }

  // Auto-fill PIC and MIC from client defaults
  const cl = window.State.clients.find(c => c.id === clientId);
  if (cl) {
    const picSelect = document.getElementById('job-pic');
    const micSelect = document.getElementById('job-mic');
    if (picSelect && cl.picUserId) picSelect.value = cl.picUserId;
    if (micSelect && cl.micUserId) micSelect.value = cl.micUserId;
  }

  // Populate dynamic service dropdown
  const clientEngs = window.State.engagements.filter(e => e.clientId === clientId);
  if (clientEngs.length > 0) {
    sel.innerHTML = clientEngs.map(e => {
      const name = window.SERVICES_MAP[e.serviceId] || e.serviceId;
      return `<option value="${e.serviceId}">${name}</option>`;
    }).join('');
  } else {
    const presetServices = window.State.services || [];
    sel.innerHTML = `<option value="">— Generic Service —</option>` +
      presetServices.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  }
};

window.saveJobEntry = function(event) {
  event.preventDefault();

  const creator = window.getCurrentActiveUser();
  if (!creator || (creator.role !== 'super_admin' && creator.role !== 'manager')) {
    alert("Unauthorized: Only partners and managers can create compliance jobs.");
    return;
  }

  const title = document.getElementById('job-title').value.trim();
  const clientId = document.getElementById('job-client').value;
  const serviceId = document.getElementById('job-service').value;
  const assignedUserId = document.getElementById('job-assigned').value;
  const picUserId = document.getElementById('job-pic').value;
  const micUserId = document.getElementById('job-mic').value;
  const priority = document.getElementById('job-priority').value;
  const dueDate = document.getElementById('job-due').value;

  const newJob = {
    id: `job_${Date.now()}`,
    title,
    clientId,
    serviceId,
    assignedUserId,
    picUserId,
    micUserId,
    priority,
    dueDate,
    status: 'To Do',
    completionDate: ''
  };

  if (!window.State.jobs) window.State.jobs = [];
  window.State.jobs.push(newJob);

  // Add Notification for Assignment
  const cl = window.State.clients.find(c => c.id === clientId);
  const owner = window.State.team.find(t => t.id === assignedUserId);
  const newNotif = {
    id: `notif_assign_${Date.now()}`,
    type: 'Task Assigned',
    title: `New Task Assigned: ${title}`,
    desc: `Filing task was assigned to <strong>${owner ? owner.name : 'Unassigned'}</strong>. Due date is set to ${dueDate}.`,
    clientName: cl ? cl.name : 'Unknown Client',
    isCritical: false
  };
  if (!window.State.notifications) window.State.notifications = [];
  window.State.notifications.unshift(newNotif);

  window.saveState();

  // Reset form inputs except date
  document.getElementById('job-title').value = '';
  document.getElementById('job-client').value = '';
  document.getElementById('job-service').innerHTML = `<option value="">— Select Service —</option>`;
  document.getElementById('job-assigned').value = '';
  document.getElementById('job-pic').value = '';
  document.getElementById('job-mic').value = '';
  document.getElementById('job-priority').value = 'Moderate';

  renderJobsModule();
  alert("New compliance job created successfully.");
};

window.updateJobStatus = function(jobId, newStatus) {
  const job = window.State.jobs.find(j => j.id === jobId);
  if (!job) return;

  const user = window.getCurrentActiveUser();
  const validStatuses = ['To Do', 'In Progress', 'Under Review', 'Completed'];
  if (!user || !validStatuses.includes(newStatus)) {
    alert("Unauthorized: Invalid job update.");
    return;
  }
  if (user.role === 'staff' && job.assignedUserId !== user.id) {
    alert("Unauthorized: You can only update tasks assigned to you.");
    return;
  }

  const prevStatus = job.status;

  // Intercept "Under Review" to prompt the user to select their reviewer (Manager/Partner)
  if (newStatus === 'Under Review' && prevStatus !== 'Under Review') {
    window.pendingReviewJobId = jobId;
    const modal = document.getElementById('submit-review-modal');
    const selectEl = document.getElementById('review-reviewer-select');
    
    if (modal && selectEl) {
      // Find all active Partners & Managers to populate the dropdown
      const reviewers = window.State.team.filter(t => t.status === 'Active' && (t.role === 'super_admin' || t.role === 'manager'));
      
      // Default PIC/MIC if available from client configuration
      const cl = window.State.clients.find(c => c.id === job.clientId);
      const defaultReviewerId = cl ? (cl.micUserId || cl.picUserId || '') : '';

      selectEl.innerHTML = reviewers.map(t => `
        <option value="${t.id}" ${t.id === defaultReviewerId ? 'selected' : ''}>${t.name} (${t.role === 'super_admin' ? 'Partner' : 'Manager'} - ${t.designation})</option>
      `).join('');

      modal.style.display = 'flex';
      return; // Stop execution, wait for confirmation!
    }
  }

  job.status = newStatus;
  
  if (newStatus === 'Completed') {
    job.completionDate = window.toLocalISODate();
  } else {
    job.completionDate = '';
  }

  const cl = window.State.clients.find(c => c.id === job.clientId);
  const owner = window.State.team.find(t => t.id === job.assignedUserId);

  if (newStatus === 'Completed' && prevStatus !== 'Completed') {
    window.awardSkillMomentum(job.assignedUserId, 16, 'a completed compliance job');
    const notif = {
      id: `notif_completed_${Date.now()}`,
      type: 'Filing Successful',
      title: `Filing Completed: ${job.title}`,
      desc: `The compliance task has been successfully filed on portal by <strong>${owner ? owner.name : 'Unassigned'}</strong>.`,
      clientName: cl ? cl.name : 'Unknown Client',
      isCritical: false
    };
    if (!window.State.notifications) window.State.notifications = [];
    window.State.notifications.unshift(notif);
  }

  window.saveState();
  renderJobsModule();
  
  if (window.renderDashboard) window.renderDashboard();
};

window.closeSubmitReviewModal = function() {
  const modal = document.getElementById('submit-review-modal');
  if (modal) modal.style.display = 'none';
  window.pendingReviewJobId = null;
  renderJobsModule();
};

window.confirmSubmitReview = function() {
  const jobId = window.pendingReviewJobId;
  const reviewerId = document.getElementById('review-reviewer-select').value;
  if (!jobId || !reviewerId) return;

  const job = window.State.jobs.find(j => j.id === jobId);
  if (!job) return;

  const user = window.getCurrentActiveUser();
  if (!user || (user.role === 'staff' && job.assignedUserId !== user.id)) {
    alert("Unauthorized: You can only submit your own assigned tasks for review.");
    return;
  }

  job.status = 'Under Review';
  job.completionDate = '';
  job.reviewerUserId = reviewerId;
  job.feedback = '';

  const cl = window.State.clients.find(c => c.id === job.clientId);
  const owner = window.State.team.find(t => t.id === job.assignedUserId);
  const reviewer = window.State.team.find(t => t.id === reviewerId);

  // Push targeted notification directly to the selected reviewer
  const notif = {
    id: `notif_review_targeted_${Date.now()}`,
    type: 'Filing Review Request',
    title: `Filing Review Requested: ${job.title}`,
    desc: `Task submitted to you for evaluation by <strong>${owner ? owner.name : 'Unassigned'}</strong>. Verification required.`,
    clientName: cl ? cl.name : 'Unknown Client',
    managerId: reviewerId,
    isCritical: true
  };

  if (!window.State.notifications) window.State.notifications = [];
  window.State.notifications.unshift(notif);

  window.saveState();
  
  document.getElementById('submit-review-modal').style.display = 'none';
  window.pendingReviewJobId = null;

  renderJobsModule();
  if (window.renderDashboard) window.renderDashboard();

  alert(`Task submitted for review to ${reviewer ? reviewer.name : 'selected reviewer'}.`);
};

window.returnJobTask = function(jobId) {
  const job = window.State.jobs.find(j => j.id === jobId);
  if (!job) return;

  const reviewer = window.getCurrentActiveUser();
  if (!reviewer || (reviewer.role !== 'super_admin' && reviewer.role !== 'manager')) {
    alert("Unauthorized: Only partners and managers can return a task.");
    return;
  }
  if (job.status !== 'Under Review') {
    alert("Only tasks under review can be returned.");
    return;
  }
  if (reviewer.role === 'manager' && job.reviewerUserId && job.reviewerUserId !== reviewer.id) {
    alert("Unauthorized: This task is assigned to a different reviewer.");
    return;
  }

  const comments = prompt("Enter comments/reasons for returning this task to the associate:");
  if (comments === null) return; // User cancelled

  if (!comments.trim()) {
    alert("Please enter a brief feedback comment to help the associate modify the task.");
    return;
  }

  job.status = 'In Progress';
  job.feedback = comments.trim();
  job.reviewerUserId = null;

  // Notify the assigned owner
  const notif = {
    id: `notif_returned_${Date.now()}`,
    type: 'Task Returned',
    title: `Task Returned: ${job.title}`,
    desc: `Your submitted filing was returned by <strong>${reviewer ? reviewer.name : 'Manager'}</strong>. Feedback: <strong>"${comments.trim()}"</strong>`,
    clientName: 'SSA Internal',
    managerId: job.assignedUserId,
    isCritical: true
  };

  if (!window.State.notifications) window.State.notifications = [];
  window.State.notifications.unshift(notif);

  window.saveState();
  renderJobsModule();
  
  if (window.renderDashboard) window.renderDashboard();
  alert(`Task returned to associate with comments.`);
};

window.deleteJob = function(jobId) {
  const user = window.getCurrentActiveUser();
  if (!user || user.role !== 'super_admin') {
    alert("Unauthorized: Only partners can delete compliance jobs.");
    return;
  }
  if (!confirm("Are you sure you want to delete this job?")) return;

  window.State.jobs = window.State.jobs.filter(j => j.id !== jobId);
  window.saveState();
  renderJobsModule();

  if (window.renderDashboard) window.renderDashboard();
};

window.openEditJobModal = function(jobId) {
  const job = window.State.jobs.find(j => j.id === jobId);
  if (!job) return;

  const cl = window.State.clients.find(c => c.id === job.clientId);
  const svcName = window.SERVICES_MAP[job.serviceId] || job.serviceId;
  const user = window.getCurrentActiveUser();
  if (!user) return;

  // Set fields
  document.getElementById('edit-job-id').value = jobId;
  document.getElementById('edit-job-client-name').value = cl ? cl.name : job.clientId;
  document.getElementById('edit-job-service-name').value = svcName;
  document.getElementById('edit-job-title').value = job.title || '';
  document.getElementById('edit-job-priority').value = job.priority || 'Moderate';
  document.getElementById('edit-job-due').value = job.dueDate || '';

  // Populate PIC (Partners only)
  const picSelect = document.getElementById('edit-job-pic');
  const partners = window.State.team.filter(t => t.role === 'super_admin');
  picSelect.innerHTML = partners.map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('');
  const currentPicId = job.picUserId || (cl ? cl.picUserId : '');
  picSelect.value = currentPicId;

  // Populate MIC (Managers/Partners)
  const micSelect = document.getElementById('edit-job-mic');
  const managers = window.State.team.filter(t => t.role === 'manager' || t.role === 'super_admin');
  micSelect.innerHTML = managers.map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('');
  const currentMicId = job.micUserId || (cl ? cl.micUserId : '');
  micSelect.value = currentMicId;

  // Populate SIC (All team members)
  const sicSelect = document.getElementById('edit-job-sic');
  sicSelect.innerHTML = window.State.team.map(t => `<option value="${t.id}">${t.name} (${t.designation})</option>`).join('');
  sicSelect.value = job.assignedUserId || '';

  // Enforce role-based disabled states
  if (user.role === 'super_admin') {
    picSelect.disabled = false;
    micSelect.disabled = false;
    sicSelect.disabled = false;
    document.getElementById('edit-job-priority').disabled = false;
    document.getElementById('edit-job-due').disabled = false;
    document.getElementById('edit-job-title').disabled = false;
  } else if (user.role === 'manager') {
    picSelect.disabled = true;
    micSelect.disabled = true;
    sicSelect.disabled = false;
    document.getElementById('edit-job-priority').disabled = false;
    document.getElementById('edit-job-due').disabled = false;
    document.getElementById('edit-job-title').disabled = false;
  } else {
    picSelect.disabled = true;
    micSelect.disabled = true;
    sicSelect.disabled = true;
    document.getElementById('edit-job-priority').disabled = true;
    document.getElementById('edit-job-due').disabled = true;
    document.getElementById('edit-job-title').disabled = true;
  }

  const modal = document.getElementById('edit-task-modal');
  if (modal) modal.style.display = 'flex';
};

window.closeEditJobModal = function() {
  const modal = document.getElementById('edit-task-modal');
  if (modal) modal.style.display = 'none';
};

window.saveEditedJob = function() {
  const jobId = document.getElementById('edit-job-id').value;
  const job = window.State.jobs.find(j => j.id === jobId);
  if (!job) return;

  const user = window.getCurrentActiveUser();
  if (!user) return;

  // Fields
  const title = document.getElementById('edit-job-title').value.trim();
  const picUserId = document.getElementById('edit-job-pic').value;
  const micUserId = document.getElementById('edit-job-mic').value;
  const assignedUserId = document.getElementById('edit-job-sic').value;
  const priority = document.getElementById('edit-job-priority').value;
  const dueDate = document.getElementById('edit-job-due').value;

  if (!title) {
    alert("Please enter a job/task title.");
    return;
  }
  if (!dueDate) {
    alert("Please select a compliance due date.");
    return;
  }

  const previousAssignedId = job.assignedUserId;

  if (user.role === 'super_admin') {
    job.title = title;
    job.picUserId = picUserId;
    job.micUserId = micUserId;
    job.assignedUserId = assignedUserId;
    job.priority = priority;
    job.dueDate = dueDate;
  } else if (user.role === 'manager') {
    job.title = title;
    job.assignedUserId = assignedUserId;
    job.priority = priority;
    job.dueDate = dueDate;
  } else {
    alert("Unauthorized: You do not have permission to edit this compliance task.");
    return;
  }

  // If Staff in Charge (SIC) assignment changed, dispatch a notification
  if (assignedUserId !== previousAssignedId) {
    const cl = window.State.clients.find(c => c.id === job.clientId);
    const newOwner = window.State.team.find(t => t.id === assignedUserId);
    const notif = {
      id: `notif_assign_updated_${Date.now()}`,
      type: 'Task Assigned',
      title: `Task Re-assigned: ${job.title}`,
      desc: `You have been newly assigned as Staff in Charge (SIC) by <strong>${user.name}</strong>. Due date is ${job.dueDate}.`,
      clientName: cl ? cl.name : 'Unknown Client',
      managerId: assignedUserId,
      isCritical: false
    };
    if (!window.State.notifications) window.State.notifications = [];
    window.State.notifications.unshift(notif);
  }

  window.saveState();
  window.closeEditJobModal();
  renderJobsModule();
  if (window.renderDashboard) window.renderDashboard();
  alert("Compliance task updated successfully.");
};

// ─── MORNING BRIEFING EMAIL SIMULATION LOGIC ──────────────────────────────────
window.simulateMorningBriefingEmailDispatches = function() {
  const activeTeam = (window.State.team || []).filter(t => t.status === 'Active');
  if (activeTeam.length === 0) {
    alert("No active roster profiles found to dispatch email briefings.");
    return;
  }

  let count = 0;
  const todayStr = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

  activeTeam.forEach(emp => {
    const myJobs = (window.State.jobs || []).filter(j => j.assignedUserId === emp.id && j.status !== 'Completed');
    const email = emp.email || `${emp.name.toLowerCase().replace(/\s+/g, '')}@firm.com`;
    
    const newNotif = {
      id: `notif_email_${Date.now()}_${emp.id}`,
      type: 'System Daemon',
      title: `✉️ Daily Briefing Email Dispatched`,
      desc: `Morning briefing successfully dispatched to <strong>${email}</strong> for ${todayStr}. Contains <strong>${myJobs.length}</strong> active compliance tasks.`,
      clientName: 'SSA Internal',
      managerId: emp.id,
      isCritical: false
    };

    if (!window.State.notifications) window.State.notifications = [];
    window.State.notifications.unshift(newNotif);
    count++;
  });

  window.saveState();
  
  if (window.renderDashboard) window.renderDashboard();
  alert(`Morning Briefing Email Simulation complete. Dispatched compliance briefing logs for ${count} active team members.`);
};

window.openMorningEmailPreviewModal = function() {
  const modal = document.getElementById('email-preview-modal');
  if (!modal) return;

  const user = window.getCurrentActiveUser();
  if (!user) {
    alert("Please log in to preview your morning email briefing.");
    return;
  }

  const email = user.email || `${user.name.toLowerCase().replace(/\s+/g, '')}@firm.com`;
  document.getElementById('email-preview-recipient').textContent = `To: ${user.name} <${email}>`;
  document.getElementById('email-body-username').textContent = user.name;
  
  const todayStr = new Date().toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
  document.getElementById('email-body-date').textContent = todayStr;

  const allJobs = window.State.jobs || [];
  const myPendingJobs = allJobs.filter(j => j.assignedUserId === user.id && j.status !== 'Completed');
  const myCompletedJobs = allJobs.filter(j => j.assignedUserId === user.id && j.status === 'Completed');

  document.getElementById('email-body-pending-count').textContent = myPendingJobs.length;
  document.getElementById('email-body-completed-count').textContent = myCompletedJobs.length;

  const listContainer = document.getElementById('email-body-tasks-list');
  if (myPendingJobs.length === 0) {
    listContainer.innerHTML = `<tr><td colspan="3" style="padding:16px; text-align:center; color:#64748b; font-style:italic;">No pending tasks assigned! You are completely up-to-date.</td></tr>`;
  } else {
    myPendingJobs.sort((a, b) => new Date(a.dueDate) - new Date(b.dueDate));

    listContainer.innerHTML = myPendingJobs.map(j => {
      const cl = window.State.clients.find(c => c.id === j.clientId);
      const today = window.toLocalISODate();
      const isOverdue = j.dueDate < today;
      
      let urgencyBadge = '';
      if (isOverdue) {
        urgencyBadge = `<span style="background:#fecaca; color:#dc2626; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">Overdue</span>`;
      } else if (j.status === 'Under Review') {
        urgencyBadge = `<span style="background:#dbeafe; color:#2563eb; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">In Review</span>`;
      } else {
        urgencyBadge = `<span style="background:#fef3c7; color:#d97706; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">Active</span>`;
      }

      return `
        <tr style="border-bottom: 1px solid #cbd5e1;">
          <td style="padding: 10px; border: 1px solid #cbd5e1;">
            <strong>${cl ? cl.name : 'Unknown Client'}</strong><br>
            <span style="color:#64748b;">${j.title}</span>
          </td>
          <td style="padding: 10px; border: 1px solid #cbd5e1; font-family: monospace;">${j.dueDate}</td>
          <td style="padding: 10px; border: 1px solid #cbd5e1;">${urgencyBadge}</td>
        </tr>
      `;
    }).join('');
  }

  modal.style.display = 'flex';
};

window.closeMorningEmailPreviewModal = function() {
  const modal = document.getElementById('email-preview-modal');
  if (modal) modal.style.display = 'none';
};

// End of Jobs Tracker Module Logic


// INITIALIZATION LOGIC
window.addEventListener('DOMContentLoaded', () => {
  // Check if we are loading fullscreen view mode
  const isFullscreenView = window.location.search.includes('view=jobs-fullscreen');
  if (isFullscreenView) {
    document.body.classList.add('fullscreen-jobs-mode');
  }

  window.loadState();
  initTheme();

  // Validate active login status and display overlay if logged out
  if (window.checkAuthenticationStatus) window.checkAuthenticationStatus();

  // Handle active session selectors
  const sessionSel = document.getElementById('sessionSelector');
  if (sessionSel) {
    sessionSel.addEventListener('change', () => {
      // Refresh page context for specific assessment years
      renderDashboard();
    });
  }

  // Set default view on hash check or home click
  let module = 'dashboard';
  if (isFullscreenView) {
    module = 'jobs';
  } else if (window.location.hash) {
    module = window.location.hash.replace('#', '');
  }
  window.navigateModule(module);

  // Global nav routing support
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const mod = btn.getAttribute('data-module');
      window.location.hash = mod;
      window.navigateModule(mod);
    });
  });
});

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.replace('#', '');
  if (hash) {
    window.navigateModule(hash);
  }
});
