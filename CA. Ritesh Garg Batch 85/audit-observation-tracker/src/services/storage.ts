import { AuditType, Engagement, Observation, FirmProfile, ObservationStatus, AuditChecklistItem } from '../types/audit';
import { getFYShortCode } from '../utils/formatters';

const STORAGE_KEYS = {
  AUDIT_TYPES: 'ca_audit_types_v1',
  ENGAGEMENTS: 'ca_engagements_v1',
  OBSERVATIONS: 'ca_observations_v1',
  FIRM_PROFILE: 'ca_firm_profile_v1',
  CHECKLIST_ITEMS: 'ca_audit_checklist_items_v1',
};

export const DEFAULT_AUDIT_TYPES: AuditType[] = [
  { id: 'at-1', name: 'Stock Audit', code: 'SA', isDefault: true, description: 'Inventory verification & valuation audit for bank CC/OD limits' },
  { id: 'at-2', name: 'Tax Audit', code: 'TA', isDefault: true, description: 'Income Tax Act Sec 44AB compliance audit & Form 3CD reporting' },
  { id: 'at-3', name: 'CAG Audit', code: 'CAG', isDefault: true, description: 'Comptroller and Auditor General of India public sector audit' },
  { id: 'at-4', name: 'Concurrent Audit', code: 'CA', isDefault: true, description: 'Real-time transaction & loan monitoring audit for bank branches' },
  { id: 'at-5', name: 'Statutory Audit', code: 'STAT', isDefault: true, description: 'Companies Act financial statements & internal control audit' },
  { id: 'at-6', name: 'Internal Audit', code: 'IA', isDefault: true, description: 'Management process reviews & operational risk evaluation' },
  { id: 'at-7', name: 'GST Audit / ITC Review', code: 'GST', isDefault: true, description: 'GSTR-2B vs 3B input tax credit reconciliation & reverse charge check' },
  { id: 'at-8', name: 'Other', code: 'OTH', isDefault: true, description: 'Custom or specialized audit engagements' },
];

export const DEFAULT_FIRM_PROFILE: FirmProfile = {
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

export const DEFAULT_CHECKLIST_ITEMS: AuditChecklistItem[] = [
  // Stock Audit Checklists
  {
    id: 'chk-sa-01',
    auditTypeId: 'at-1',
    category: 'Physical Inventory Verification',
    itemNumber: '1.1',
    checkPoint: 'Perform physical sample test-check of top 80% valuation items against ERP stock ledger as on cut-off date.',
    procedureGuidance: 'Physically count raw materials, WIP, finished goods in presence of unit head. Check calibration of weighing scales.',
    statutoryReference: 'CARO 2020 Cl. 3(ii)(a) / SA 501',
    riskLevel: 'High',
    isMandatory: true,
  },
  {
    id: 'chk-sa-02',
    auditTypeId: 'at-1',
    category: 'Drawing Power (DP) & Ageing',
    itemNumber: '1.2',
    checkPoint: 'Verify computation of Drawing Power (DP) excluding unpaid stocks (creditors) and non-moving/obsolete items (>90 days).',
    procedureGuidance: 'Check monthly stock statement submitted to consortium bank against ERP sub-ledgers. Recompute DP with stipulated margin.',
    statutoryReference: 'RBI Master Circular on DP & Working Capital',
    riskLevel: 'Critical',
    isMandatory: true,
  },
  {
    id: 'chk-sa-03',
    auditTypeId: 'at-1',
    category: 'Insurance & Bank Hypothecation',
    itemNumber: '1.3',
    checkPoint: 'Verify adequate insurance cover against fire, earthquake, STFI, with Bank Hypothecation clause endorsement.',
    procedureGuidance: 'Check policy validity, reinstatement value clause, and premium payment receipt before audit date.',
    statutoryReference: 'Bank Sanction Terms / Hypothecation Agreement',
    riskLevel: 'High',
    isMandatory: true,
  },
  {
    id: 'chk-sa-04',
    auditTypeId: 'at-1',
    category: 'Book Debts & Sundry Debtors',
    itemNumber: '1.4',
    checkPoint: 'Verify debtor aging schedule and ensure debts overdue >90 days or disputed receivables are excluded from DP.',
    procedureGuidance: 'Obtain party-wise aging ledger, verify realization after cutoff date, test sales cut-off invoices.',
    statutoryReference: 'RBI Working Capital Guidelines',
    riskLevel: 'High',
    isMandatory: true,
  },
  // Tax Audit Checklists
  {
    id: 'chk-ta-01',
    auditTypeId: 'at-2',
    category: 'Clause 22 / MSME Compliance',
    itemNumber: '2.1',
    checkPoint: 'Verify compliance with Section 43B(h) for payments to registered Micro & Small Enterprises within agreed terms (max 45 days).',
    procedureGuidance: 'Obtain Udyam registration certificates, check supplier agreements, compute disallowance and interest under MSMED Act.',
    statutoryReference: 'Sec 43B(h) Income Tax Act 1961 / MSMED Act 2006',
    riskLevel: 'Critical',
    isMandatory: true,
  },
  {
    id: 'chk-ta-02',
    auditTypeId: 'at-2',
    category: 'Clause 21 / TDS Defaults',
    itemNumber: '2.2',
    checkPoint: 'Verify TDS deduction under Sections 194C, 194J, 194Q, 194H and deposit before statutory due dates.',
    procedureGuidance: 'Reconcile Form 26AS/AIS with purchase and expense registers. Note short deduction and delayed deposits.',
    statutoryReference: 'Sec 40(a)(ia) / Form 3CD Cl. 21(b)',
    riskLevel: 'High',
    isMandatory: true,
  },
  {
    id: 'chk-ta-03',
    auditTypeId: 'at-2',
    category: 'Clause 31 / Cash Transactions',
    itemNumber: '2.3',
    checkPoint: 'Verify receipt/repayment of loans, deposits, and specify advances in excess of ₹ 20,000 otherwise than by account payee cheque.',
    procedureGuidance: 'Review cash book ledgers, ledger accounts of directors, relatives, and related parties under Sec 40A(2)(b).',
    statutoryReference: 'Sec 269SS / Sec 269T / Form 3CD Cl. 31',
    riskLevel: 'Critical',
    isMandatory: true,
  },
  // CAG Audit Checklists
  {
    id: 'chk-cag-01',
    auditTypeId: 'at-3',
    category: 'Public Procurement & GeM Rules',
    itemNumber: '3.1',
    checkPoint: 'Verify mandatory procurement of goods and services via Government e-Marketplace (GeM) and tender threshold adherence.',
    procedureGuidance: 'Check Non-Availability Certificates (NAC) where procurement bypassed GeM. Review purchase order files.',
    statutoryReference: 'GFR 2017 Rule 149 / CVC Guidelines',
    riskLevel: 'Critical',
    isMandatory: true,
  },
  {
    id: 'chk-cag-02',
    auditTypeId: 'at-3',
    category: 'Financial Delegation & Propriety',
    itemNumber: '3.2',
    checkPoint: 'Examine sanction approvals against Delegation of Financial Powers (DoFP) and check for split sanctions.',
    procedureGuidance: 'Check if purchase orders were deliberately fragmented to avoid higher authority approval thresholds.',
    statutoryReference: 'DoFP Rules / CAG MSO (Audit)',
    riskLevel: 'High',
    isMandatory: true,
  },
  // Concurrent Audit Checklists
  {
    id: 'chk-ca-01',
    auditTypeId: 'at-4',
    category: 'Credit Sanction & Disbursement',
    itemNumber: '4.1',
    checkPoint: 'Check pre-disbursement sanction term compliance, legal search report, title deeds verification, and CIBIL report.',
    procedureGuidance: 'Verify ROC charge filing in Form CHG-1 within 30 days and valid mortgage entry in branch register.',
    statutoryReference: 'RBI Master Directions on Credit Management',
    riskLevel: 'Critical',
    isMandatory: true,
  },
  {
    id: 'chk-ca-02',
    auditTypeId: 'at-4',
    category: 'IRAC Norms & NPA Classification',
    itemNumber: '4.2',
    checkPoint: 'Verify SMA-0, SMA-1, SMA-2 alerts and check timely identification of Non-Performing Assets (NPAs).',
    procedureGuidance: 'Inspect continuous out-of-order accounts, overdue interest servicing, and stock audit overdue renewal.',
    statutoryReference: 'RBI Master Circular on IRAC Norms',
    riskLevel: 'Critical',
    isMandatory: true,
  },
];

const SEED_ENGAGEMENTS: Engagement[] = [
  {
    id: 'ENG-2025-001',
    clientName: 'Apex Precision Engineering Pvt Ltd',
    clientPanGstin: '07AAACA1234F1Z8 / AAACA1234F',
    clientCode: 'APEX',
    auditTypeId: 'at-1', // Stock Audit
    financialYear: '2024-25',
    teamMembers: ['CA Ritesh Garg (Partner)', 'Ankit Sharma (Senior)', 'Rohit Verma (Article)'],
    engagementPartner: 'CA Ritesh Garg',
    startDate: '2025-01-10',
    endDate: '2025-01-28',
    branchLocation: 'Plant 1, Industrial Area, Manesar',
    overallStatus: 'In Progress',
    notes: 'Stock audit assigned by State Bank of India (Consortium Lead) for Working Capital Limit of ₹ 45 Cr.',
    createdAt: '2025-01-05T10:00:00.000Z',
    updatedAt: '2025-01-20T14:30:00.000Z',
  },
  {
    id: 'ENG-2025-002',
    clientName: 'Bharat Global Logistics Ltd',
    clientPanGstin: '27AABCB5678K1ZQ / AABCB5678K',
    clientCode: 'BGLL',
    auditTypeId: 'at-2', // Tax Audit
    financialYear: '2024-25',
    teamMembers: ['CA Ritesh Garg (Partner)', 'Priya Mehta (Manager)', 'Vikas Jain (Article)'],
    engagementPartner: 'CA Ritesh Garg',
    startDate: '2025-02-01',
    endDate: '2025-03-15',
    branchLocation: 'Corporate HQ, Nariman Point, Mumbai',
    overallStatus: 'In Progress',
    notes: 'Sec 44AB Tax Audit for FY 2024-25. Key focus on 43B(h) MSME compliance and TDS deduction reconciliation.',
    createdAt: '2025-01-15T11:00:00.000Z',
    updatedAt: '2025-02-10T16:00:00.000Z',
  },
  {
    id: 'ENG-2025-003',
    clientName: 'Northern Coalfields Energy Corp (PSU)',
    clientPanGstin: '09AAACN9988P1Z3',
    clientCode: 'NCEC',
    auditTypeId: 'at-3', // CAG Audit
    financialYear: '2024-25',
    teamMembers: ['CA Ritesh Garg (Partner)', 'Suresh Narang (Senior Auditor)', 'Divya Iyer (Auditor)'],
    engagementPartner: 'CA Ritesh Garg',
    startDate: '2025-01-05',
    endDate: '2025-02-25',
    branchLocation: 'Singrauli Regional Office & Heavy Mining Unit',
    overallStatus: 'Fieldwork Complete',
    notes: 'CAG Supplementary Audit under Section 143(6) of Companies Act 2013.',
    createdAt: '2024-12-20T09:00:00.000Z',
    updatedAt: '2025-02-20T12:00:00.000Z',
  },
  {
    id: 'ENG-2025-004',
    clientName: 'Punjab National Bank - Mid Corporate Branch',
    clientPanGstin: '07AAACP0123M1Z2',
    clientCode: 'PNB',
    auditTypeId: 'at-4', // Concurrent Audit
    financialYear: '2024-25',
    teamMembers: ['Amit Kulkarni (Team Lead)', 'Kavita Singh (Article Assistant)'],
    engagementPartner: 'CA Ritesh Garg',
    startDate: '2025-01-01',
    endDate: '2025-03-31',
    branchLocation: 'Parliament Street Branch, New Delhi',
    overallStatus: 'In Progress',
    notes: 'Monthly concurrent audit covering high value credit sanctions, Forex transactions, and NPA early warning triggers.',
    createdAt: '2024-12-30T10:00:00.000Z',
    updatedAt: '2025-02-18T18:00:00.000Z',
  },
];

const SEED_OBSERVATIONS: Observation[] = [
  {
    id: 'OBS-001',
    referenceNo: 'SA-2425-APEX-001',
    engagementId: 'ENG-2025-001',
    dateOfObservation: '2025-01-14',
    areaProcess: 'Inventory Valuation & Non-Moving Stock',
    description: 'Physical verification revealed slow-moving and obsolete raw material inventory lying without movement for over 180 days valued at ₹ 38.5 Lakhs. No obsolescence provision has been made in the drawing power statement submitted to the bank.',
    severity: 'Critical',
    financialImpact: 3850000,
    rootCause: 'Lack of automated ERP aging report integration with bank stock statement preparation module.',
    recommendation: 'Exclude non-moving stock over 90/180 days as per sanction terms from eligible inventory for Drawing Power calculation. Establish quarterly scrap review committee.',
    discussionStakeholder: 'Mr. Rajesh Taneja (CFO) & Mr. S. K. Roy (Works Manager)',
    dateOfDiscussion: '2025-01-16',
    managementResponse: 'Agreed. Obsolete inventory of ₹ 38.50 Lakhs will be segregated and excluded in the DP statement for January 2025. Provision will be recognized in Q4 accounts.',
    status: 'Rectified',
    rectificationStatus: 'Rectified',
    targetRectificationDate: '2025-01-25',
    actualRectificationDate: '2025-01-24',
    personResponsible: 'Ankit Sharma (Senior)',
    attachments: 'Stock_Aging_Sheet_Annexure1.xlsx, Revised_DP_Letter_SBI.pdf',
    remarks: 'Verified bank DP statement for Jan 2025. Amount excluded from eligible limit.',
    createdAt: '2025-01-14T14:00:00.000Z',
    updatedAt: '2025-01-24T17:00:00.000Z',
  },
  {
    id: 'OBS-002',
    referenceNo: 'SA-2425-APEX-002',
    engagementId: 'ENG-2025-001',
    dateOfObservation: '2025-01-18',
    areaProcess: 'Insurance Coverage & Under-Insurance',
    description: 'The overall inventory stock holding at Plant 1 was ₹ 52.40 Crores as on 31-12-2024 against total Floater Fire & Burglary Insurance cover of only ₹ 40.00 Crores, resulting in under-insurance of ₹ 12.40 Crores and bank mortgage clause not endorsed on the renewal endorsement.',
    severity: 'High',
    financialImpact: 124000000,
    rootCause: 'Buffer capacity stock buildup during peak production season not updated with insurance broker.',
    recommendation: 'Immediately obtain supplementary insurance cover of ₹ 15 Cr with agreed bank hypothecation clause.',
    discussionStakeholder: 'Mr. Arvind Saxena (General Manager - Finance)',
    dateOfDiscussion: '2025-01-19',
    managementResponse: 'Endorsement request submitted to New India Assurance for additional cover of ₹ 15 Crores. Premium paid on 20-01-2025.',
    status: 'Rectified',
    rectificationStatus: 'Rectified',
    targetRectificationDate: '2025-01-22',
    actualRectificationDate: '2025-01-21',
    personResponsible: 'Rohit Verma (Article)',
    attachments: 'Policy_Endorsement_NIA_1244.pdf',
    remarks: 'Verified copy of revised endorsement certificate with bank lien marked.',
    createdAt: '2025-01-18T16:00:00.000Z',
    updatedAt: '2025-01-21T11:00:00.000Z',
  },
  {
    id: 'OBS-003',
    referenceNo: 'TA-2425-BGLL-001',
    engagementId: 'ENG-2025-002',
    dateOfObservation: '2025-02-04',
    areaProcess: 'Sec 43B(h) MSME Vendor Payment Compliance',
    description: 'During review of sundry creditors aging as of 31st March, payments totaling ₹ 64,80,000 to micro and small enterprise suppliers were overdue beyond 45 days (or written agreement period). Disallowance under Section 43B(h) of Income Tax Act 1961 is attracted.',
    severity: 'Critical',
    financialImpact: 6480000,
    rootCause: 'Vendor master in SAP lacked MSME Udyam registration classification and automated payment due date alerts.',
    recommendation: 'Classify all registered MSME suppliers in ERP. Ensure overdue amounts are cleared before financial year end to claim tax deduction or report under Clause 22 of Form 3CD.',
    discussionStakeholder: 'Ms. Sunita Rao (VP - Accounts & Taxation)',
    dateOfDiscussion: '2025-02-06',
    managementResponse: 'Treasury department has released ₹ 45 Lakhs on 10-Feb-2025. Balance ₹ 19.80 Lakhs is scheduled for clearance before 15-March-2025.',
    status: 'In Progress' as any, // Under Discussion / In Progress
    rectificationStatus: 'In Progress',
    targetRectificationDate: '2025-03-15',
    personResponsible: 'Priya Mehta (Manager)',
    attachments: 'MSME_Overdue_Aging_Clause22.xlsx',
    remarks: 'Partial rectification verified. Balance tracking in progress.',
    createdAt: '2025-02-04T12:00:00.000Z',
    updatedAt: '2025-02-12T15:00:00.000Z',
  },
  {
    id: 'OBS-004',
    referenceNo: 'TA-2425-BGLL-002',
    engagementId: 'ENG-2025-002',
    dateOfObservation: '2025-02-08',
    areaProcess: 'TDS Deduction under Sec 194C / 194Q',
    description: 'Short deduction of TDS amounting to ₹ 3,45,000 noted on freight contractor payments due to non-availability of PAN/Declaration under Sec 194C(6) for 14 fleet operators.',
    severity: 'Medium',
    financialImpact: 345000,
    rootCause: 'Decentralized hiring of spot transport vehicles at branch warehouses without HO verification.',
    recommendation: 'Collect valid PAN & Annexure 194C declarations from all operators or deduct TDS @ 20% under Section 206AA. Deposit pending TDS with interest under Sec 201(1A).',
    discussionStakeholder: 'Mr. Ketan Shah (Head - Logistics Accounts)',
    dateOfDiscussion: '2025-02-09',
    managementResponse: 'Declarations obtained from 10 transporters; TDS of ₹ 1,12,000 deposited with interest for the remaining 4.',
    status: 'Under Discussion',
    rectificationStatus: 'In Progress',
    targetRectificationDate: '2025-02-28',
    personResponsible: 'Vikas Jain (Article)',
    attachments: 'TDS_Reconciliation_Working.xlsx',
    remarks: 'Awaiting deposit challans for remaining transporters.',
    createdAt: '2025-02-08T15:30:00.000Z',
    updatedAt: '2025-02-10T14:00:00.000Z',
  },
  {
    id: 'OBS-005',
    referenceNo: 'CAG-2425-NCEC-001',
    engagementId: 'ENG-2025-003',
    dateOfObservation: '2025-01-12',
    areaProcess: 'Capital Work in Progress (CWIP) & Asset Capitalization',
    description: 'Coal handling conveyor plant erected and put to trial commercial use in October 2023 continued to be shown under Capital Work-in-Progress (₹ 18.20 Crores). Resulted in non-provision of depreciation of ₹ 1.45 Crores and distortion of operating profit.',
    severity: 'Critical',
    financialImpact: 14500000,
    rootCause: 'Pending formal issuance of Final Taking Over Certificate (TOC) by technical committee despite commercial operations.',
    recommendation: 'Capitalize the asset effective from date of commercial trial run as per Ind AS 16. Charge prospective depreciation and rectify prior period adjustment.',
    discussionStakeholder: 'Mr. B. K. Mishra (Director - Finance) & Chief Engineer (Projects)',
    dateOfDiscussion: '2025-01-20',
    managementResponse: 'Draft CAG observation noted. Technical TOC expedited and asset capitalization entry passed in Q3 accounts with depreciation effect.',
    status: 'Management Response Awaited',
    rectificationStatus: 'In Progress',
    targetRectificationDate: '2025-02-28',
    personResponsible: 'Suresh Narang (Senior Auditor)',
    attachments: 'CWIP_Review_Plant4_IndAS16.pdf',
    remarks: 'Awaiting audit committee ratification in February board meeting.',
    createdAt: '2025-01-12T11:00:00.000Z',
    updatedAt: '2025-01-25T16:30:00.000Z',
  },
  {
    id: 'OBS-006',
    referenceNo: 'CAG-2425-NCEC-002',
    engagementId: 'ENG-2025-003',
    dateOfObservation: '2025-01-22',
    areaProcess: 'CSR Expenditure Provision & Unspent Funds Deposit',
    description: 'Unspent CSR obligation of ₹ 2.30 Crores for ongoing projects for FY 2023-24 was not transferred to a designated Unspent CSR Account in a scheduled bank within 30 days of financial year end, violating Section 135(6) of Companies Act 2013.',
    severity: 'High',
    financialImpact: 23000000,
    rootCause: 'Delay in opening specialized escrow bank account with PSU bank.',
    recommendation: 'Transfer funds immediately to comply with statutory mandate and report in Directors Report and Notes to Accounts.',
    discussionStakeholder: 'Mr. R. C. Verma (Company Secretary) & GM (CSR)',
    dateOfDiscussion: '2025-01-24',
    managementResponse: 'Specialized CSR account opened with Union Bank of India on 28-01-2025 and entire unspent sum of ₹ 2.30 Cr transferred.',
    status: 'Closed',
    rectificationStatus: 'Rectified',
    targetRectificationDate: '2025-01-30',
    actualRectificationDate: '2025-01-28',
    personResponsible: 'Divya Iyer (Auditor)',
    attachments: 'UBI_CSR_Account_Deposit_Receipt.pdf',
    remarks: 'Bank certificate verified. Compliance achieved.',
    createdAt: '2025-01-22T14:00:00.000Z',
    updatedAt: '2025-01-29T10:00:00.000Z',
  },
  {
    id: 'OBS-007',
    referenceNo: 'CA-2425-PNB-001',
    engagementId: 'ENG-2025-004',
    dateOfObservation: '2025-01-15',
    areaProcess: 'Credit Monitoring & Expired Sanction Limits',
    description: 'Three Cash Credit borrower accounts with total aggregate limits of ₹ 8.50 Crores were operating beyond the sanctioned validity date without regular annual review or ad-hoc limit regularization for over 90 days.',
    severity: 'High',
    financialImpact: 85000000,
    rootCause: 'Non-submission of audited balance sheets by borrowers within stipulated 6-month period.',
    recommendation: 'Issue notice for immediate financial submission or levy penal interest / tag as Special Mention Account (SMA-1/2) as per RBI prudential guidelines.',
    discussionStakeholder: 'Mr. Sanjeev Kumar (Chief Manager - Credit)',
    dateOfDiscussion: '2025-01-16',
    managementResponse: 'Renewal proposals for 2 accounts processed and sanctioned on 25-01-2025. Third account (₹ 1.5 Cr) served with recall notice.',
    status: 'Under Discussion',
    rectificationStatus: 'In Progress',
    targetRectificationDate: '2025-02-15',
    personResponsible: 'Amit Kulkarni (Team Lead)',
    attachments: 'Expired_Limits_Summary_Jan25.xlsx',
    remarks: 'Follow up required on recovery of recall account.',
    createdAt: '2025-01-15T16:00:00.000Z',
    updatedAt: '2025-01-26T12:00:00.000Z',
  },
  {
    id: 'OBS-008',
    referenceNo: 'CA-2425-PNB-002',
    engagementId: 'ENG-2025-004',
    dateOfObservation: '2025-01-25',
    areaProcess: 'KYC & Re-KYC Documentation in High Risk Accounts',
    description: 'Periodic Re-KYC review overdue in 18 High-Risk Current Accounts with monthly cumulative transactions exceeding ₹ 50 Lakhs. PAN/Aadhaar re-validation pending.',
    severity: 'Medium',
    financialImpact: 0,
    rootCause: 'Staff shortage at branch front-desk during demonetization/election currency duty.',
    recommendation: 'Issue registered notices to non-compliant account holders with 30-day timeline before debit freeze.',
    discussionStakeholder: 'Ms. Meena Bhatt (Operations In-charge)',
    dateOfDiscussion: '2025-01-27',
    managementResponse: 'SMS alerts and registered letters sent to all 18 customers. 11 accounts updated as of 05-Feb.',
    status: 'Open',
    rectificationStatus: 'In Progress',
    targetRectificationDate: '2025-02-20',
    personResponsible: 'Kavita Singh (Article Assistant)',
    attachments: 'High_Risk_KYC_List.pdf',
    remarks: 'Branch to provide updated status report by 20th Feb.',
    createdAt: '2025-01-25T13:30:00.000Z',
    updatedAt: '2025-02-05T17:00:00.000Z',
  }
];

class StorageService {
  constructor() {
    this.purgeDummyDataIfPresent();
  }

  private purgeDummyDataIfPresent(): void {
    try {
      const dummyEngIds = new Set(['ENG-2025-001', 'ENG-2025-002', 'ENG-2025-003', 'ENG-2025-004']);
      const dummyClientNames = new Set([
        'Apex Precision Engineering Pvt Ltd',
        'Bharat Global Logistics Ltd',
        'Northern Coalfields Energy Corp (PSU)',
        'Punjab National Bank - Mid Corporate Branch',
      ]);

      const storedEngs = this.get<Engagement[]>(STORAGE_KEYS.ENGAGEMENTS, []);
      if (Array.isArray(storedEngs) && storedEngs.length > 0) {
        const cleanedEngs = storedEngs.filter(e => !dummyEngIds.has(e.id) && !dummyClientNames.has(e.clientName));
        if (cleanedEngs.length !== storedEngs.length) {
          this.set(STORAGE_KEYS.ENGAGEMENTS, cleanedEngs);
        }
      }

      const dummyObsIds = new Set(['OBS-001', 'OBS-002', 'OBS-003', 'OBS-004', 'OBS-005', 'OBS-006', 'OBS-007', 'OBS-008']);
      const storedObs = this.get<Observation[]>(STORAGE_KEYS.OBSERVATIONS, []);
      if (Array.isArray(storedObs) && storedObs.length > 0) {
        const cleanedObs = storedObs.filter(o => !dummyObsIds.has(o.id) && !dummyEngIds.has(o.engagementId));
        if (cleanedObs.length !== storedObs.length) {
          this.set(STORAGE_KEYS.OBSERVATIONS, cleanedObs);
        }
      }
    } catch (e) {
      console.error('Error purging dummy data:', e);
    }
  }

  private get<T>(key: string, fallback: T): T {
    try {
      const data = localStorage.getItem(key);
      if (!data) return fallback;
      const parsed = JSON.parse(data);
      if (parsed === null || parsed === undefined) return fallback;
      return parsed;
    } catch (e) {
      console.error(`Error reading ${key} from localStorage:`, e);
      return fallback;
    }
  }

  private set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      console.error(`Error writing ${key} to localStorage:`, e);
    }
  }

  // Audit Types
  getAuditTypes(): AuditType[] {
    const types = this.get<AuditType[]>(STORAGE_KEYS.AUDIT_TYPES, []);
    if (!types || types.length === 0) {
      this.set(STORAGE_KEYS.AUDIT_TYPES, DEFAULT_AUDIT_TYPES);
      return DEFAULT_AUDIT_TYPES;
    }
    return types;
  }

  saveAuditType(type: Partial<AuditType> & { name: string; code: string }): AuditType {
    const types = this.getAuditTypes();
    if (type.id) {
      const index = types.findIndex(t => t.id === type.id);
      if (index >= 0) {
        types[index] = { ...types[index], ...type };
        this.set(STORAGE_KEYS.AUDIT_TYPES, types);
        return types[index];
      }
    }
    const newType: AuditType = {
      id: `at-${Date.now()}`,
      name: type.name.trim(),
      code: type.code.trim().toUpperCase(),
      description: type.description?.trim(),
      isDefault: false,
    };
    types.push(newType);
    this.set(STORAGE_KEYS.AUDIT_TYPES, types);
    return newType;
  }

  deleteAuditType(id: string): boolean {
    const types = this.getAuditTypes();
    const filtered = types.filter(t => t.id !== id);
    this.set(STORAGE_KEYS.AUDIT_TYPES, filtered);
    return true;
  }

  // Engagements
  getEngagements(): Engagement[] {
    return this.get<Engagement[]>(STORAGE_KEYS.ENGAGEMENTS, []);
  }

  getEngagementById(id: string): Engagement | undefined {
    return this.getEngagements().find(e => e.id === id);
  }

  saveEngagement(eng: Partial<Engagement> & { clientName: string; auditTypeId: string; financialYear: string; engagementPartner?: string }): Engagement {
    const engagements = this.getEngagements();
    const now = new Date().toISOString();

    if (eng.id) {
      const index = engagements.findIndex(e => e.id === eng.id);
      if (index >= 0) {
        const updated: Engagement = {
          ...engagements[index],
          ...eng,
          updatedAt: now,
        };
        engagements[index] = updated;
        this.set(STORAGE_KEYS.ENGAGEMENTS, engagements);
        return updated;
      }
    }

    // Auto generate new ID
    const year = new Date().getFullYear();
    const count = engagements.length + 1;
    const newId = `ENG-${year}-${String(count).padStart(3, '0')}`;

    const newEng: Engagement = {
      id: newId,
      clientName: eng.clientName.trim(),
      clientPanGstin: eng.clientPanGstin?.trim(),
      clientCode: eng.clientCode?.trim().toUpperCase() || 'CLI',
      auditTypeId: eng.auditTypeId,
      financialYear: eng.financialYear.trim(),
      teamMembers: eng.teamMembers || [],
      engagementPartner: eng.engagementPartner?.trim() || 'Engagement Partner',
      startDate: eng.startDate || new Date().toISOString().split('T')[0],
      endDate: eng.endDate || new Date().toISOString().split('T')[0],
      branchLocation: eng.branchLocation?.trim(),
      overallStatus: eng.overallStatus || 'In Progress',
      notes: eng.notes?.trim(),
      createdAt: now,
      updatedAt: now,
    };

    engagements.unshift(newEng);
    this.set(STORAGE_KEYS.ENGAGEMENTS, engagements);
    return newEng;
  }

  deleteEngagement(id: string): boolean {
    const engagements = this.getEngagements();
    const filtered = engagements.filter(e => e.id !== id);
    this.set(STORAGE_KEYS.ENGAGEMENTS, filtered);

    // Also remove linked observations
    const observations = this.getObservations();
    const remainingObs = observations.filter(o => o.engagementId !== id);
    this.set(STORAGE_KEYS.OBSERVATIONS, remainingObs);
    return true;
  }

  // Observations
  getObservations(): Observation[] {
    return this.get<Observation[]>(STORAGE_KEYS.OBSERVATIONS, []);
  }

  getObservationById(id: string): Observation | undefined {
    return this.getObservations().find(o => o.id === id);
  }

  getObservationsByEngagementId(engagementId: string): Observation[] {
    return this.getObservations().filter(o => o.engagementId === engagementId);
  }

  /**
   * Generates the next collision-proof Reference No. for a given engagement
   * Format: <AuditTypeCode>-<FYShort>-<ClientCode>-<Sequence> (e.g. SA-2425-APEX-003)
   */
  generateObservationRefNo(engagementId: string): string {
    const engagement = this.getEngagementById(engagementId);
    if (!engagement) return `OBS-${Date.now()}`;

    const auditTypes = this.getAuditTypes();
    const auditType = auditTypes.find(at => at.id === engagement.auditTypeId);
    const typeCode = auditType?.code || 'AUD';
    const fyCode = getFYShortCode(engagement.financialYear);
    const clientCode = engagement.clientCode || 'CLI';

    const existingObs = this.getObservationsByEngagementId(engagementId);
    const prefix = `${typeCode}-${fyCode}-${clientCode}-`;

    let maxSeq = 0;
    for (const ob of existingObs) {
      if (ob.referenceNo.startsWith(prefix)) {
        const seqStr = ob.referenceNo.replace(prefix, '');
        const seqNum = parseInt(seqStr, 10);
        if (!isNaN(seqNum) && seqNum > maxSeq) {
          maxSeq = seqNum;
        }
      }
    }

    const nextSeq = String(maxSeq + 1).padStart(3, '0');
    return `${prefix}${nextSeq}`;
  }

  saveObservation(obs: Partial<Observation> & { engagementId: string; description: string; severity: any; status: any }): Observation {
    const observations = this.getObservations();
    const now = new Date().toISOString();

    if (obs.id) {
      const index = observations.findIndex(o => o.id === obs.id);
      if (index >= 0) {
        const updated: Observation = {
          ...observations[index],
          ...obs,
          updatedAt: now,
        };
        observations[index] = updated;
        this.set(STORAGE_KEYS.OBSERVATIONS, observations);
        return updated;
      }
    }

    const newId = `OBS-${Date.now()}`;
    const refNo = obs.referenceNo || this.generateObservationRefNo(obs.engagementId);

    const newObs: Observation = {
      id: newId,
      referenceNo: refNo,
      engagementId: obs.engagementId,
      dateOfObservation: obs.dateOfObservation || new Date().toISOString().split('T')[0],
      areaProcess: obs.areaProcess?.trim() || 'General Audit Observation',
      description: obs.description.trim(),
      severity: obs.severity || 'Medium',
      financialImpact: obs.financialImpact !== undefined ? Number(obs.financialImpact) : undefined,
      rootCause: obs.rootCause?.trim(),
      recommendation: obs.recommendation?.trim() || '',
      discussionStakeholder: obs.discussionStakeholder?.trim(),
      dateOfDiscussion: obs.dateOfDiscussion,
      managementResponse: obs.managementResponse?.trim(),
      status: obs.status || 'Open',
      rectificationStatus: obs.rectificationStatus || 'Not Started',
      targetRectificationDate: obs.targetRectificationDate,
      actualRectificationDate: obs.actualRectificationDate,
      personResponsible: obs.personResponsible?.trim() || 'Audit Team',
      attachments: obs.attachments?.trim(),
      remarks: obs.remarks?.trim(),
      createdAt: now,
      updatedAt: now,
    };

    observations.unshift(newObs);
    this.set(STORAGE_KEYS.OBSERVATIONS, observations);
    return newObs;
  }

  updateObservationStatus(id: string, status: ObservationStatus): Observation | undefined {
    const observations = this.getObservations();
    const index = observations.findIndex(o => o.id === id);
    if (index >= 0) {
      observations[index].status = status;
      observations[index].updatedAt = new Date().toISOString();
      this.set(STORAGE_KEYS.OBSERVATIONS, observations);
      return observations[index];
    }
    return undefined;
  }

  deleteObservation(id: string): boolean {
    const observations = this.getObservations();
    const filtered = observations.filter(o => o.id !== id);
    this.set(STORAGE_KEYS.OBSERVATIONS, filtered);
    return true;
  }

  // Bulk Engagements
  bulkAddEngagements(newEngagements: Engagement[]): number {
    const existing = this.getEngagements();
    const existingIds = new Set(existing.map(e => e.id));
    
    const toAdd: Engagement[] = [];
    newEngagements.forEach(eng => {
      let candidateId = eng.id;
      let counter = 1;
      while (existingIds.has(candidateId)) {
        candidateId = `${eng.id}-${counter++}`;
      }
      existingIds.add(candidateId);
      toAdd.push({
        ...eng,
        id: candidateId,
        createdAt: eng.createdAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });

    const combined = [...existing, ...toAdd];
    this.set(STORAGE_KEYS.ENGAGEMENTS, combined);
    return toAdd.length;
  }

  // Checklists Management
  getChecklistItems(): AuditChecklistItem[] {
    const items = this.get<AuditChecklistItem[]>(STORAGE_KEYS.CHECKLIST_ITEMS, []);
    if (!items || items.length === 0) {
      this.set(STORAGE_KEYS.CHECKLIST_ITEMS, DEFAULT_CHECKLIST_ITEMS);
      return DEFAULT_CHECKLIST_ITEMS;
    }
    return items;
  }

  saveChecklistItem(itemData: Partial<AuditChecklistItem> & { checkPoint: string; auditTypeId: string }): AuditChecklistItem {
    const items = this.getChecklistItems();
    if (itemData.id) {
      const index = items.findIndex(i => i.id === itemData.id);
      if (index >= 0) {
        items[index] = {
          ...items[index],
          ...itemData,
          updatedAt: new Date().toISOString(),
        };
        this.set(STORAGE_KEYS.CHECKLIST_ITEMS, items);
        return items[index];
      }
    }

    const newItem: AuditChecklistItem = {
      id: `chk-${Date.now()}-${Math.floor(Math.random() * 1000)}`,
      auditTypeId: itemData.auditTypeId,
      category: itemData.category || 'General Verification',
      itemNumber: itemData.itemNumber || `CL-${items.length + 1}`,
      checkPoint: itemData.checkPoint,
      procedureGuidance: itemData.procedureGuidance,
      statutoryReference: itemData.statutoryReference,
      riskLevel: itemData.riskLevel || 'High',
      isMandatory: itemData.isMandatory !== undefined ? itemData.isMandatory : true,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    items.push(newItem);
    this.set(STORAGE_KEYS.CHECKLIST_ITEMS, items);
    return newItem;
  }

  deleteChecklistItem(id: string): boolean {
    const items = this.getChecklistItems();
    const filtered = items.filter(i => i.id !== id);
    this.set(STORAGE_KEYS.CHECKLIST_ITEMS, filtered);
    return true;
  }

  bulkSaveChecklistItems(newItems: AuditChecklistItem[], replace = false): number {
    if (replace) {
      this.set(STORAGE_KEYS.CHECKLIST_ITEMS, newItems);
      return newItems.length;
    }

    const existing = this.getChecklistItems();
    const combined = [...existing, ...newItems];
    this.set(STORAGE_KEYS.CHECKLIST_ITEMS, combined);
    return newItems.length;
  }

  // Firm Profile
  getFirmProfile(): FirmProfile {
    const profile = this.get<Partial<FirmProfile>>(STORAGE_KEYS.FIRM_PROFILE, DEFAULT_FIRM_PROFILE);
    if (!profile || typeof profile !== 'object') {
      return DEFAULT_FIRM_PROFILE;
    }
    return {
      ...DEFAULT_FIRM_PROFILE,
      ...profile,
      partnerName: profile.partnerName || DEFAULT_FIRM_PROFILE.partnerName,
      firmName: profile.firmName || DEFAULT_FIRM_PROFILE.firmName,
    };
  }

  saveFirmProfile(profile: FirmProfile): FirmProfile {
    this.set(STORAGE_KEYS.FIRM_PROFILE, profile);
    return profile;
  }

  // Reset / Backup / Restore
  clearAllClientData(): void {
    this.set(STORAGE_KEYS.ENGAGEMENTS, []);
    this.set(STORAGE_KEYS.OBSERVATIONS, []);
  }

  resetToSampleData(): void {
    this.set(STORAGE_KEYS.AUDIT_TYPES, DEFAULT_AUDIT_TYPES);
    this.set(STORAGE_KEYS.ENGAGEMENTS, SEED_ENGAGEMENTS);
    this.set(STORAGE_KEYS.OBSERVATIONS, SEED_OBSERVATIONS);
    this.set(STORAGE_KEYS.FIRM_PROFILE, DEFAULT_FIRM_PROFILE);
    this.set(STORAGE_KEYS.CHECKLIST_ITEMS, DEFAULT_CHECKLIST_ITEMS);
  }

  exportAllDataJson(): string {
    const data = {
      version: '1.1',
      exportedAt: new Date().toISOString(),
      firmProfile: this.getFirmProfile(),
      auditTypes: this.getAuditTypes(),
      checklistItems: this.getChecklistItems(),
      engagements: this.getEngagements(),
      observations: this.getObservations(),
    };
    return JSON.stringify(data, null, 2);
  }

  importDataJson(jsonStr: string): boolean {
    try {
      const data = JSON.parse(jsonStr);
      if (data.firmProfile) this.set(STORAGE_KEYS.FIRM_PROFILE, data.firmProfile);
      if (Array.isArray(data.auditTypes)) this.set(STORAGE_KEYS.AUDIT_TYPES, data.auditTypes);
      if (Array.isArray(data.checklistItems)) this.set(STORAGE_KEYS.CHECKLIST_ITEMS, data.checklistItems);
      if (Array.isArray(data.engagements)) this.set(STORAGE_KEYS.ENGAGEMENTS, data.engagements);
      if (Array.isArray(data.observations)) this.set(STORAGE_KEYS.OBSERVATIONS, data.observations);
      return true;
    } catch (e) {
      console.error('Failed to import JSON data:', e);
      return false;
    }
  }
}

export const storageService = new StorageService();
