/**
 * database.cjs — Pure JS SQLite Database Layer for Audit Observation Tracker
 * Uses sql.js (sql-asm.js) for 100% bundled EXE compatibility without native binaries or WASM file dependencies.
 * Database file: ./data/audit_tracker.db
 */

const initSqlJs = require('./sqlite-engine.cjs');
const path = require('path');
const fs = require('fs');

const DATA_DIR = path.join(process.cwd(), 'data');
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

const DB_PATH = path.join(DATA_DIR, 'audit_tracker.db');
let dbInstance = null;

function saveDb() {
  if (!dbInstance) return;
  try {
    const data = dbInstance.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(DB_PATH, buffer);
  } catch (err) {
    console.error('Error saving SQLite database file:', err);
  }
}

// Helper methods on db wrapper
const db = {
  all(sql, params = []) {
    const stmt = dbInstance.prepare(sql);
    if (params && params.length > 0) stmt.bind(params);
    const results = [];
    while (stmt.step()) {
      results.push(stmt.getAsObject());
    }
    stmt.free();
    return results;
  },

  get(sql, params = []) {
    const rows = this.all(sql, params);
    return rows.length > 0 ? rows[0] : null;
  },

  run(sql, params = []) {
    const stmt = dbInstance.prepare(sql);
    if (params && params.length > 0) stmt.bind(params);
    stmt.step();
    stmt.free();
    saveDb();
    return { changes: dbInstance.getRowsModified() };
  },

  exec(sql) {
    dbInstance.exec(sql);
    saveDb();
  }
};

// ─── Seed Data ──────────────────────────────────────────────────────────────

const DEFAULT_AUDIT_TYPES = [
  { id: 'at-1', name: 'Stock Audit', code: 'SA', isDefault: true, description: 'Inventory verification & valuation audit for bank CC/OD limits' },
  { id: 'at-2', name: 'Tax Audit', code: 'TA', isDefault: true, description: 'Income Tax Act Sec 44AB compliance audit & Form 3CD reporting' },
  { id: 'at-3', name: 'CAG Audit', code: 'CAG', isDefault: true, description: 'Comptroller and Auditor General of India public sector audit' },
  { id: 'at-4', name: 'Concurrent Audit', code: 'CA', isDefault: true, description: 'Real-time transaction & loan monitoring audit for bank branches' },
  { id: 'at-5', name: 'Statutory Audit', code: 'STAT', isDefault: true, description: 'Companies Act financial statements & internal control audit' },
  { id: 'at-6', name: 'Internal Audit', code: 'IA', isDefault: true, description: 'Management process reviews & operational risk evaluation' },
  { id: 'at-7', name: 'GST Audit / ITC Review', code: 'GST', isDefault: true, description: 'GSTR-2B vs 3B input tax credit reconciliation & reverse charge check' },
  { id: 'at-8', name: 'Other', code: 'OTH', isDefault: true, description: 'Custom or specialized audit engagements' },
];

const DEFAULT_FIRM_PROFILE = {
  firmName: 'R. K. Garg & Associates',
  frn: '014285N',
  address: 'Suite 402, Mercantile House, 15 K.G. Marg, Connaught Place',
  city: 'New Delhi - 110001',
  phone: '+91 11 4356 8900',
  email: 'audit@rkgargca.in',
  partnerName: 'CA Ritesh Garg, FCA',
  membershipNo: '098765',
  website: 'www.rkgargca.com',
};

const DEFAULT_CHECKLIST_ITEMS = [
  { id: 'chk-sa-01', auditTypeId: 'at-1', category: 'Physical Inventory Verification', itemNumber: '1.1', checkPoint: 'Perform physical sample test-check of top 80% valuation items against ERP stock ledger as on cut-off date.', procedureGuidance: 'Physically count raw materials, WIP, finished goods in presence of unit head. Check calibration of weighing scales.', statutoryReference: 'CARO 2020 Cl. 3(ii)(a) / SA 501', riskLevel: 'High', isMandatory: true },
  { id: 'chk-sa-02', auditTypeId: 'at-1', category: 'Drawing Power (DP) & Ageing', itemNumber: '1.2', checkPoint: 'Verify computation of Drawing Power (DP) excluding unpaid stocks (creditors) and non-moving/obsolete items (>90 days).', procedureGuidance: 'Check monthly stock statement submitted to consortium bank against ERP sub-ledgers. Recompute DP with stipulated margin.', statutoryReference: 'RBI Master Circular on DP & Working Capital', riskLevel: 'Critical', isMandatory: true },
  { id: 'chk-sa-03', auditTypeId: 'at-1', category: 'Insurance & Bank Hypothecation', itemNumber: '1.3', checkPoint: 'Verify adequate insurance cover against fire, earthquake, STFI, with Bank Hypothecation clause endorsement.', procedureGuidance: 'Check policy validity, reinstatement value clause, and premium payment receipt before audit date.', statutoryReference: 'Bank Sanction Terms / Hypothecation Agreement', riskLevel: 'High', isMandatory: true },
  { id: 'chk-sa-04', auditTypeId: 'at-1', category: 'Book Debts & Sundry Debtors', itemNumber: '1.4', checkPoint: 'Verify debtor aging schedule and ensure debts overdue >90 days or disputed receivables are excluded from DP.', procedureGuidance: 'Obtain party-wise aging ledger, verify realization after cutoff date, test sales cut-off invoices.', statutoryReference: 'RBI Working Capital Guidelines', riskLevel: 'High', isMandatory: true },
  { id: 'chk-ta-01', auditTypeId: 'at-2', category: 'Clause 22 / MSME Compliance', itemNumber: '2.1', checkPoint: 'Verify compliance with Section 43B(h) for payments to registered Micro & Small Enterprises within agreed terms (max 45 days).', procedureGuidance: 'Obtain Udyam registration certificates, check supplier agreements, compute disallowance and interest under MSMED Act.', statutoryReference: 'Sec 43B(h) Income Tax Act 1961 / MSMED Act 2006', riskLevel: 'Critical', isMandatory: true },
  { id: 'chk-ta-02', auditTypeId: 'at-2', category: 'Clause 21 / TDS Defaults', itemNumber: '2.2', checkPoint: 'Verify TDS deduction under Sections 194C, 194J, 194Q, 194H and deposit before statutory due dates.', procedureGuidance: 'Reconcile Form 26AS/AIS with purchase and expense registers. Note short deduction and delayed deposits.', statutoryReference: 'Sec 40(a)(ia) / Form 3CD Cl. 21(b)', riskLevel: 'High', isMandatory: true },
  { id: 'chk-ta-03', auditTypeId: 'at-2', category: 'Clause 31 / Cash Transactions', itemNumber: '2.3', checkPoint: 'Verify receipt/repayment of loans, deposits, and specify advances in excess of ₹ 20,000 otherwise than by account payee cheque.', procedureGuidance: 'Review cash book ledgers, ledger accounts of directors, relatives, and related parties under Sec 40A(2)(b).', statutoryReference: 'Sec 269SS / Sec 269T / Form 3CD Cl. 31', riskLevel: 'Critical', isMandatory: true },
  { id: 'chk-cag-01', auditTypeId: 'at-3', category: 'Public Procurement & GeM Rules', itemNumber: '3.1', checkPoint: 'Verify mandatory procurement of goods and services via Government e-Marketplace (GeM) and tender threshold adherence.', procedureGuidance: 'Check Non-Availability Certificates (NAC) where procurement bypassed GeM. Review purchase order files.', statutoryReference: 'GFR 2017 Rule 149 / CVC Guidelines', riskLevel: 'Critical', isMandatory: true },
  { id: 'chk-cag-02', auditTypeId: 'at-3', category: 'Financial Delegation & Propriety', itemNumber: '3.2', checkPoint: 'Examine sanction approvals against Delegation of Financial Powers (DoFP) and check for split sanctions.', procedureGuidance: 'Check if purchase orders were deliberately fragmented to avoid higher authority approval thresholds.', statutoryReference: 'DoFP Rules / CAG MSO (Audit)', riskLevel: 'High', isMandatory: true },
  { id: 'chk-ca-01', auditTypeId: 'at-4', category: 'Credit Sanction & Disbursement', itemNumber: '4.1', checkPoint: 'Check pre-disbursement sanction term compliance, legal search report, title deeds verification, and CIBIL report.', procedureGuidance: 'Verify ROC charge filing in Form CHG-1 within 30 days and valid mortgage entry in branch register.', statutoryReference: 'RBI Master Directions on Credit Management', riskLevel: 'Critical', isMandatory: true },
  { id: 'chk-ca-02', auditTypeId: 'at-4', category: 'IRAC Norms & NPA Classification', itemNumber: '4.2', checkPoint: 'Verify SMA-0, SMA-1, SMA-2 alerts and check timely identification of Non-Performing Assets (NPAs).', procedureGuidance: 'Inspect continuous out-of-order accounts, overdue interest servicing, and stock audit overdue renewal.', statutoryReference: 'RBI Master Circular on IRAC Norms', riskLevel: 'Critical', isMandatory: true },
];

const SEED_ENGAGEMENTS = [
  { id: 'ENG-2025-001', clientName: 'Apex Precision Engineering Pvt Ltd', clientPanGstin: '07AAACA1234F1Z8 / AAACA1234F', clientCode: 'APEX', auditTypeId: 'at-1', financialYear: '2024-25', teamMembers: ['CA Ritesh Garg (Partner)', 'Ankit Sharma (Senior)', 'Rohit Verma (Article)'], engagementPartner: 'CA Ritesh Garg', startDate: '2025-01-10', endDate: '2025-01-28', branchLocation: 'Plant 1, Industrial Area, Manesar', overallStatus: 'In Progress', notes: 'Stock audit assigned by State Bank of India (Consortium Lead) for Working Capital Limit of ₹ 45 Cr.', createdAt: '2025-01-05T10:00:00.000Z', updatedAt: '2025-01-20T14:30:00.000Z' },
  { id: 'ENG-2025-002', clientName: 'Bharat Global Logistics Ltd', clientPanGstin: '27AABCB5678K1ZQ / AABCB5678K', clientCode: 'BGLL', auditTypeId: 'at-2', financialYear: '2024-25', teamMembers: ['CA Ritesh Garg (Partner)', 'Priya Mehta (Manager)', 'Vikas Jain (Article)'], engagementPartner: 'CA Ritesh Garg', startDate: '2025-02-01', endDate: '2025-03-15', branchLocation: 'Corporate HQ, Nariman Point, Mumbai', overallStatus: 'In Progress', notes: 'Sec 44AB Tax Audit for FY 2024-25. Key focus on 43B(h) MSME compliance and TDS deduction reconciliation.', createdAt: '2025-01-15T11:00:00.000Z', updatedAt: '2025-02-10T16:00:00.000Z' },
  { id: 'ENG-2025-003', clientName: 'Northern Coalfields Energy Corp (PSU)', clientPanGstin: '09AAACN9988P1Z3', clientCode: 'NCEC', auditTypeId: 'at-3', financialYear: '2024-25', teamMembers: ['CA Ritesh Garg (Partner)', 'Suresh Narang (Senior Auditor)', 'Divya Iyer (Auditor)'], engagementPartner: 'CA Ritesh Garg', startDate: '2025-01-05', endDate: '2025-02-25', branchLocation: 'Singrauli Regional Office & Heavy Mining Unit', overallStatus: 'Fieldwork Complete', notes: 'CAG Supplementary Audit under Section 143(6) of Companies Act 2013.', createdAt: '2024-12-20T09:00:00.000Z', updatedAt: '2025-02-20T12:00:00.000Z' },
  { id: 'ENG-2025-004', clientName: 'Punjab National Bank - Mid Corporate Branch', clientPanGstin: '07AAACP0123M1Z2', clientCode: 'PNB', auditTypeId: 'at-4', financialYear: '2024-25', teamMembers: ['Amit Kulkarni (Team Lead)', 'Kavita Singh (Article Assistant)'], engagementPartner: 'CA Ritesh Garg', startDate: '2025-01-01', endDate: '2025-03-31', branchLocation: 'Parliament Street Branch, New Delhi', overallStatus: 'In Progress', notes: 'Monthly concurrent audit covering high value credit sanctions, Forex transactions, and NPA early warning triggers.', createdAt: '2024-12-30T10:00:00.000Z', updatedAt: '2025-02-18T18:00:00.000Z' },
];

const SEED_OBSERVATIONS = [
  { id: 'OBS-001', referenceNo: 'SA-2425-APEX-001', engagementId: 'ENG-2025-001', dateOfObservation: '2025-01-14', areaProcess: 'Inventory Valuation & Non-Moving Stock', description: 'Physical verification revealed slow-moving and obsolete raw material inventory lying without movement for over 180 days valued at ₹ 38.5 Lakhs. No obsolescence provision has been made in the drawing power statement submitted to the bank.', severity: 'Critical', financialImpact: 3850000, rootCause: 'Lack of automated ERP aging report integration with bank stock statement preparation module.', recommendation: 'Exclude non-moving stock over 90/180 days as per sanction terms from eligible inventory for Drawing Power calculation. Establish quarterly scrap review committee.', discussionStakeholder: 'Mr. Rajesh Taneja (CFO) & Mr. S. K. Roy (Works Manager)', dateOfDiscussion: '2025-01-16', managementResponse: 'Agreed. Obsolete inventory of ₹ 38.50 Lakhs will be segregated and excluded in the DP statement for January 2025. Provision will be recognized in Q4 accounts.', status: 'Rectified', rectificationStatus: 'Rectified', targetRectificationDate: '2025-01-25', actualRectificationDate: '2025-01-24', personResponsible: 'Ankit Sharma (Senior)', attachments: 'Stock_Aging_Sheet_Annexure1.xlsx, Revised_DP_Letter_SBI.pdf', remarks: 'Verified bank DP statement for Jan 2025. Amount excluded from eligible limit.', createdAt: '2025-01-14T14:00:00.000Z', updatedAt: '2025-01-24T17:00:00.000Z' },
  { id: 'OBS-002', referenceNo: 'SA-2425-APEX-002', engagementId: 'ENG-2025-001', dateOfObservation: '2025-01-18', areaProcess: 'Insurance Coverage & Under-Insurance', description: 'The overall inventory stock holding at Plant 1 was ₹ 52.40 Crores as on 31-12-2024 against total Floater Fire & Burglary Insurance cover of only ₹ 40.00 Crores, resulting in under-insurance of ₹ 12.40 Crores and bank mortgage clause not endorsed on the renewal endorsement.', severity: 'High', financialImpact: 124000000, rootCause: 'Buffer capacity stock buildup during peak production season not updated with insurance broker.', recommendation: 'Immediately obtain supplementary insurance cover of ₹ 15 Cr with agreed bank hypothecation clause.', discussionStakeholder: 'Mr. Arvind Saxena (General Manager - Finance)', dateOfDiscussion: '2025-01-19', managementResponse: 'Endorsement request submitted to New India Assurance for additional cover of ₹ 15 Crores. Premium paid on 20-01-2025.', status: 'Rectified', rectificationStatus: 'Rectified', targetRectificationDate: '2025-01-22', actualRectificationDate: '2025-01-21', personResponsible: 'Rohit Verma (Article)', attachments: 'Policy_Endorsement_NIA_1244.pdf', remarks: 'Verified copy of revised endorsement certificate with bank lien marked.', createdAt: '2025-01-18T16:00:00.000Z', updatedAt: '2025-01-21T11:00:00.000Z' },
  { id: 'OBS-003', referenceNo: 'TA-2425-BGLL-001', engagementId: 'ENG-2025-002', dateOfObservation: '2025-02-04', areaProcess: 'Sec 43B(h) MSME Vendor Payment Compliance', description: 'During review of sundry creditors aging as of 31st March, payments totaling ₹ 64,80,000 to micro and small enterprise suppliers were overdue beyond 45 days (or written agreement period). Disallowance under Section 43B(h) of Income Tax Act 1961 is attracted.', severity: 'Critical', financialImpact: 6480000, rootCause: 'Vendor master in SAP lacked MSME Udyam registration classification and automated payment due date alerts.', recommendation: 'Classify all registered MSME suppliers in ERP. Ensure overdue amounts are cleared before financial year end to claim tax deduction or report under Clause 22 of Form 3CD.', discussionStakeholder: 'Ms. Sunita Rao (VP - Accounts & Taxation)', dateOfDiscussion: '2025-02-06', managementResponse: 'Treasury department has released ₹ 45 Lakhs on 10-Feb-2025. Balance ₹ 19.80 Lakhs is scheduled for clearance before 15-March-2025.', status: 'Under Discussion', rectificationStatus: 'In Progress', targetRectificationDate: '2025-03-15', personResponsible: 'Priya Mehta (Manager)', attachments: 'MSME_Overdue_Aging_Clause22.xlsx', remarks: 'Partial rectification verified. Balance tracking in progress.', createdAt: '2025-02-04T12:00:00.000Z', updatedAt: '2025-02-12T15:00:00.000Z' },
  { id: 'OBS-004', referenceNo: 'TA-2425-BGLL-002', engagementId: 'ENG-2025-002', dateOfObservation: '2025-02-08', areaProcess: 'TDS Deduction under Sec 194C / 194Q', description: 'Short deduction of TDS amounting to ₹ 3,45,000 noted on freight contractor payments due to non-availability of PAN/Declaration under Sec 194C(6) for 14 fleet operators.', severity: 'Medium', financialImpact: 345000, rootCause: 'Decentralized hiring of spot transport vehicles at branch warehouses without HO verification.', recommendation: 'Collect valid PAN & Annexure 194C declarations from all operators or deduct TDS @ 20% under Section 206AA. Deposit pending TDS with interest under Sec 201(1A).', discussionStakeholder: 'Mr. Ketan Shah (Head - Logistics Accounts)', dateOfDiscussion: '2025-02-09', managementResponse: 'Declarations obtained from 10 transporters; TDS of ₹ 1,12,000 deposited with interest for the remaining 4.', status: 'Under Discussion', rectificationStatus: 'In Progress', targetRectificationDate: '2025-02-28', personResponsible: 'Vikas Jain (Article)', attachments: 'TDS_Reconciliation_Working.xlsx', remarks: 'Awaiting deposit challans for remaining transporters.', createdAt: '2025-02-08T15:30:00.000Z', updatedAt: '2025-02-10T14:00:00.000Z' },
  { id: 'OBS-005', referenceNo: 'CAG-2425-NCEC-001', engagementId: 'ENG-2025-003', dateOfObservation: '2025-01-12', areaProcess: 'Capital Work in Progress (CWIP) & Asset Capitalization', description: 'Coal handling conveyor plant erected and put to trial commercial use in October 2023 continued to be shown under Capital Work-in-Progress (₹ 18.20 Crores). Resulted in non-provision of depreciation of ₹ 1.45 Crores and distortion of operating profit.', severity: 'Critical', financialImpact: 14500000, rootCause: 'Pending formal issuance of Final Taking Over Certificate (TOC) by technical committee despite commercial operations.', recommendation: 'Capitalize the asset effective from date of commercial trial run as per Ind AS 16. Charge prospective depreciation and rectify prior period adjustment.', discussionStakeholder: 'Mr. B. K. Mishra (Director - Finance) & Chief Engineer (Projects)', dateOfDiscussion: '2025-01-20', managementResponse: 'Draft CAG observation noted. Technical TOC expedited and asset capitalization entry passed in Q3 accounts with depreciation effect.', status: 'Management Response Awaited', rectificationStatus: 'In Progress', targetRectificationDate: '2025-02-28', personResponsible: 'Suresh Narang (Senior Auditor)', attachments: 'CWIP_Review_Plant4_IndAS16.pdf', remarks: 'Awaiting audit committee ratification in February board meeting.', createdAt: '2025-01-12T11:00:00.000Z', updatedAt: '2025-01-25T16:30:00.000Z' },
  { id: 'OBS-006', referenceNo: 'CAG-2425-NCEC-002', engagementId: 'ENG-2025-003', dateOfObservation: '2025-01-22', areaProcess: 'CSR Expenditure Provision & Unspent Funds Deposit', description: 'Unspent CSR obligation of ₹ 2.30 Crores for ongoing projects for FY 2023-24 was not transferred to a designated Unspent CSR Account in a scheduled bank within 30 days of financial year end, violating Section 135(6) of Companies Act 2013.', severity: 'High', financialImpact: 23000000, rootCause: 'Delay in opening specialized escrow bank account with PSU bank.', recommendation: 'Transfer funds immediately to comply with statutory mandate and report in Directors Report and Notes to Accounts.', discussionStakeholder: 'Mr. R. C. Verma (Company Secretary) & GM (CSR)', dateOfDiscussion: '2025-01-24', managementResponse: 'Specialized CSR account opened with Union Bank of India on 28-01-2025 and entire unspent sum of ₹ 2.30 Cr transferred.', status: 'Closed', rectificationStatus: 'Rectified', targetRectificationDate: '2025-01-30', actualRectificationDate: '2025-01-28', personResponsible: 'Divya Iyer (Auditor)', attachments: 'UBI_CSR_Account_Deposit_Receipt.pdf', remarks: 'Bank certificate verified. Compliance achieved.', createdAt: '2025-01-22T14:00:00.000Z', updatedAt: '2025-01-29T10:00:00.000Z' },
  { id: 'OBS-007', referenceNo: 'CA-2425-PNB-001', engagementId: 'ENG-2025-004', dateOfObservation: '2025-01-15', areaProcess: 'Credit Monitoring & Expired Sanction Limits', description: 'Three Cash Credit borrower accounts with total aggregate limits of ₹ 8.50 Crores were operating beyond the sanctioned validity date without regular annual review or ad-hoc limit regularization for over 90 days.', severity: 'High', financialImpact: 85000000, rootCause: 'Non-submission of audited balance sheets by borrowers within stipulated 6-month period.', recommendation: 'Issue notice for immediate financial submission or levy penal interest / tag as Special Mention Account (SMA-1/2) as per RBI prudential guidelines.', discussionStakeholder: 'Mr. Sanjeev Kumar (Chief Manager - Credit)', dateOfDiscussion: '2025-01-16', managementResponse: 'Renewal proposals for 2 accounts processed and sanctioned on 25-01-2025. Third account (₹ 1.5 Cr) served with recall notice.', status: 'Under Discussion', rectificationStatus: 'In Progress', targetRectificationDate: '2025-02-15', personResponsible: 'Amit Kulkarni (Team Lead)', attachments: 'Expired_Limits_Summary_Jan25.xlsx', remarks: 'Follow up required on recovery of recall account.', createdAt: '2025-01-15T16:00:00.000Z', updatedAt: '2025-01-26T12:00:00.000Z' },
  { id: 'OBS-008', referenceNo: 'CA-2425-PNB-002', engagementId: 'ENG-2025-004', dateOfObservation: '2025-01-25', areaProcess: 'KYC & Re-KYC Documentation in High Risk Accounts', description: 'Periodic Re-KYC review overdue in 18 High-Risk Current Accounts with monthly cumulative transactions exceeding ₹ 50 Lakhs. PAN/Aadhaar re-validation pending.', severity: 'Medium', financialImpact: 0, rootCause: 'Staff shortage at branch front-desk during demonetization/election currency duty.', recommendation: 'Issue registered notices to non-compliant account holders with 30-day timeline before debit freeze.', discussionStakeholder: 'Ms. Meena Bhatt (Operations In-charge)', dateOfDiscussion: '2025-01-27', managementResponse: 'SMS alerts and registered letters sent to all 18 customers. 11 accounts updated as of 05-Feb.', status: 'Open', rectificationStatus: 'In Progress', targetRectificationDate: '2025-02-20', personResponsible: 'Kavita Singh (Article Assistant)', attachments: 'High_Risk_KYC_List.pdf', remarks: 'Branch to provide updated status report by 20th Feb.', createdAt: '2025-01-25T13:30:00.000Z', updatedAt: '2025-02-05T17:00:00.000Z' },
];

async function initDb() {
  const locateFile = (file) => {
    const cwdFile = path.join(process.cwd(), file);
    if (fs.existsSync(cwdFile)) return cwdFile;
    const distFile = path.join(process.cwd(), 'dist-exe', file);
    if (fs.existsSync(distFile)) return distFile;
    const localFile = path.join(__dirname, '..', 'node_modules', 'sql.js', 'dist', file);
    if (fs.existsSync(localFile)) return localFile;
    return file;
  };
  const SQL = await initSqlJs({ locateFile });
  if (fs.existsSync(DB_PATH)) {
    const filebuffer = fs.readFileSync(DB_PATH);
    dbInstance = new SQL.Database(filebuffer);
  } else {
    dbInstance = new SQL.Database();
  }

  // Schema creation
  dbInstance.exec(`
    CREATE TABLE IF NOT EXISTS audit_types (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      code TEXT NOT NULL,
      description TEXT,
      color TEXT,
      is_default INTEGER DEFAULT 0,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS engagements (
      id TEXT PRIMARY KEY,
      client_name TEXT NOT NULL,
      client_pan_gstin TEXT,
      client_code TEXT NOT NULL,
      audit_type_id TEXT NOT NULL,
      financial_year TEXT NOT NULL,
      team_members TEXT DEFAULT '[]',
      engagement_partner TEXT,
      start_date TEXT,
      end_date TEXT,
      branch_location TEXT,
      overall_status TEXT DEFAULT 'Planning',
      notes TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS observations (
      id TEXT PRIMARY KEY,
      reference_no TEXT NOT NULL,
      engagement_id TEXT NOT NULL,
      date_of_observation TEXT,
      area_process TEXT,
      description TEXT NOT NULL,
      severity TEXT NOT NULL DEFAULT 'Medium',
      financial_impact REAL,
      root_cause TEXT,
      recommendation TEXT,
      discussion_stakeholder TEXT,
      date_of_discussion TEXT,
      management_response TEXT,
      status TEXT DEFAULT 'Open',
      rectification_status TEXT DEFAULT 'Not Started',
      target_rectification_date TEXT,
      actual_rectification_date TEXT,
      person_responsible TEXT,
      attachments TEXT,
      remarks TEXT,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS checklist_items (
      id TEXT PRIMARY KEY,
      audit_type_id TEXT NOT NULL,
      category TEXT,
      item_number TEXT,
      check_point TEXT NOT NULL,
      procedure_guidance TEXT,
      statutory_reference TEXT,
      risk_level TEXT DEFAULT 'High',
      is_mandatory INTEGER DEFAULT 1,
      created_at TEXT DEFAULT (datetime('now')),
      updated_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS firm_profile (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      firm_name TEXT NOT NULL,
      frn TEXT,
      address TEXT,
      city TEXT,
      phone TEXT,
      email TEXT,
      partner_name TEXT,
      membership_no TEXT,
      website TEXT,
      updated_at TEXT DEFAULT (datetime('now'))
    );
  `);

  // Seeding
  const countTypes = db.get('SELECT COUNT(*) as cnt FROM audit_types');
  if (!countTypes || countTypes.cnt === 0) {
    for (const t of DEFAULT_AUDIT_TYPES) {
      db.run(
        'INSERT OR IGNORE INTO audit_types (id, name, code, description, is_default) VALUES (?, ?, ?, ?, ?)',
        [t.id, t.name, t.code, t.description || null, t.isDefault ? 1 : 0]
      );
    }
  }

  const countFirm = db.get('SELECT COUNT(*) as cnt FROM firm_profile');
  if (!countFirm || countFirm.cnt === 0) {
    db.run(
      'INSERT INTO firm_profile (id, firm_name, frn, address, city, phone, email, partner_name, membership_no, website) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
      [DEFAULT_FIRM_PROFILE.firmName, DEFAULT_FIRM_PROFILE.frn, DEFAULT_FIRM_PROFILE.address, DEFAULT_FIRM_PROFILE.city, DEFAULT_FIRM_PROFILE.phone, DEFAULT_FIRM_PROFILE.email, DEFAULT_FIRM_PROFILE.partnerName, DEFAULT_FIRM_PROFILE.membershipNo, DEFAULT_FIRM_PROFILE.website]
    );
  }

  const countChk = db.get('SELECT COUNT(*) as cnt FROM checklist_items');
  if (!countChk || countChk.cnt === 0) {
    for (const item of DEFAULT_CHECKLIST_ITEMS) {
      db.run(
        'INSERT OR IGNORE INTO checklist_items (id, audit_type_id, category, item_number, check_point, procedure_guidance, statutory_reference, risk_level, is_mandatory) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [item.id, item.auditTypeId, item.category, item.itemNumber, item.checkPoint, item.procedureGuidance || null, item.statutoryReference || null, item.riskLevel, item.isMandatory ? 1 : 0]
      );
    }
  }

  const countEng = db.get('SELECT COUNT(*) as cnt FROM engagements');
  if (!countEng || countEng.cnt === 0) {
    for (const eng of SEED_ENGAGEMENTS) {
      db.run(
        'INSERT OR IGNORE INTO engagements (id, client_name, client_pan_gstin, client_code, audit_type_id, financial_year, team_members, engagement_partner, start_date, end_date, branch_location, overall_status, notes, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [eng.id, eng.clientName, eng.clientPanGstin, eng.clientCode, eng.auditTypeId, eng.financialYear, JSON.stringify(eng.teamMembers), eng.engagementPartner, eng.startDate, eng.endDate, eng.branchLocation, eng.overallStatus, eng.notes, eng.createdAt, eng.updatedAt]
      );
    }
  }

  const countObs = db.get('SELECT COUNT(*) as cnt FROM observations');
  if (!countObs || countObs.cnt === 0) {
    for (const obs of SEED_OBSERVATIONS) {
      db.run(
        'INSERT OR IGNORE INTO observations (id, reference_no, engagement_id, date_of_observation, area_process, description, severity, financial_impact, root_cause, recommendation, discussion_stakeholder, date_of_discussion, management_response, status, rectification_status, target_rectification_date, actual_rectification_date, person_responsible, attachments, remarks, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        [obs.id, obs.referenceNo, obs.engagementId, obs.dateOfObservation, obs.areaProcess, obs.description, obs.severity, obs.financialImpact || null, obs.rootCause || null, obs.recommendation, obs.discussionStakeholder || null, obs.dateOfDiscussion || null, obs.managementResponse || null, obs.status, obs.rectificationStatus, obs.targetRectificationDate || null, obs.actualRectificationDate || null, obs.personResponsible, obs.attachments || null, obs.remarks || null, obs.createdAt, obs.updatedAt]
      );
    }
  }

  saveDb();
  console.log('✅ SQLite (sql.js WASM) initialized successfully.');
  return db;
}

// ─── Row Mappers ─────────────────────────────────────────────────────────────

function mapAuditType(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    code: row.code,
    description: row.description,
    color: row.color,
    isDefault: !!row.is_default,
  };
}

function mapEngagement(row) {
  if (!row) return null;
  return {
    id: row.id,
    clientName: row.client_name,
    clientPanGstin: row.client_pan_gstin,
    clientCode: row.client_code,
    auditTypeId: row.audit_type_id,
    financialYear: row.financial_year,
    teamMembers: JSON.parse(row.team_members || '[]'),
    engagementPartner: row.engagement_partner,
    startDate: row.start_date,
    endDate: row.end_date,
    branchLocation: row.branch_location,
    overallStatus: row.overall_status,
    notes: row.notes,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapObservation(row) {
  if (!row) return null;
  return {
    id: row.id,
    referenceNo: row.reference_no,
    engagementId: row.engagement_id,
    dateOfObservation: row.date_of_observation,
    areaProcess: row.area_process,
    description: row.description,
    severity: row.severity,
    financialImpact: row.financial_impact,
    rootCause: row.root_cause,
    recommendation: row.recommendation,
    discussionStakeholder: row.discussion_stakeholder,
    dateOfDiscussion: row.date_of_discussion,
    managementResponse: row.management_response,
    status: row.status,
    rectificationStatus: row.rectification_status,
    targetRectificationDate: row.target_rectification_date,
    actualRectificationDate: row.actual_rectification_date,
    personResponsible: row.person_responsible,
    attachments: row.attachments,
    remarks: row.remarks,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapChecklistItem(row) {
  if (!row) return null;
  return {
    id: row.id,
    auditTypeId: row.audit_type_id,
    category: row.category,
    itemNumber: row.item_number,
    checkPoint: row.check_point,
    procedureGuidance: row.procedure_guidance,
    statutoryReference: row.statutory_reference,
    riskLevel: row.risk_level,
    isMandatory: !!row.is_mandatory,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapFirmProfile(row) {
  if (!row) return DEFAULT_FIRM_PROFILE;
  return {
    firmName: row.firm_name,
    frn: row.frn,
    address: row.address,
    city: row.city,
    phone: row.phone,
    email: row.email,
    partnerName: row.partner_name,
    membershipNo: row.membership_no,
    website: row.website,
  };
}

module.exports = {
  initDb,
  db,
  mapAuditType,
  mapEngagement,
  mapObservation,
  mapChecklistItem,
  mapFirmProfile,
  DEFAULT_AUDIT_TYPES,
  DEFAULT_FIRM_PROFILE,
  DEFAULT_CHECKLIST_ITEMS,
  SEED_ENGAGEMENTS,
  SEED_OBSERVATIONS,
};
