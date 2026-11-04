// Fictional demo data so every screen can be tried before Supabase is connected.
import type { ApiProvider, Client, ComplianceSource, Expense, JobRun, Payment, SystemEvent, User, Vendor } from './types';
import { gstinCheckChar } from '../lib/validators';

const gst = (s: string) => s + gstinCheckChar(s);

export const DEMO_CLIENTS: Client[] = [
  { id: 'c1', name: 'Shree Ganesh Traders', gstin: gst('27AABFS1234K1Z'), stateCode: '27', brandColor: '#0f2a44', tallyMode: 'xml_file', tallyCompany: 'Shree Ganesh Traders 26-27', backdateWindowDays: 0,
    bankAccounts: [
      { id: 'b1', kind: 'bank', name: 'HDFC Current ••4521', tallyLedger: 'HDFC Bank' },
      { id: 'b2', kind: 'bank', name: 'SBI Current ••0817', tallyLedger: 'SBI Bank' },
      { id: 'u1', kind: 'upi', name: 'GPay · shreeganesh@okhdfcbank', upiId: 'shreeganesh@okhdfcbank', linkedBankId: 'b1', tallyLedger: 'HDFC Bank' },
      { id: 'u2', kind: 'upi', name: 'PhonePe · 9820012345@ybl', upiId: '9820012345@ybl', linkedBankId: 'b2', tallyLedger: 'SBI Bank' },
      { id: 'k1', kind: 'card', name: 'HDFC Corporate Card ••8812', tallyLedger: 'HDFC Credit Card' },
      { id: 'c1', kind: 'cash', name: 'Main cash', tallyLedger: 'Cash' },
      { id: 'c2', kind: 'cash', name: 'Petty cash — Office', tallyLedger: 'Petty Cash' }
    ],
    costCentres: [
      { id: 'cc1', kind: 'branch', name: 'Pune HO', active: true },
      { id: 'cc2', kind: 'branch', name: 'Nashik Branch', active: true },
      { id: 'cc3', kind: 'project', name: 'Godown Renovation 2026', active: true }
    ],
    cashLedger: 'Cash', defaultCreditDays: 30, cashLimitPerDay: 10000, noteAboveAmount: 25000 },
  { id: 'c2', name: 'Patel Engineering Works', gstin: gst('24AAGCP5678M1Z'), stateCode: '24', brandColor: '#7c2d12', tallyMode: 'none', backdateWindowDays: 3,
    bankAccounts: [{ id: 'b3', kind: 'bank', name: 'ICICI Current ••7730', tallyLedger: 'ICICI Bank' }, { id: 'c3', kind: 'cash', name: 'Main cash', tallyLedger: 'Cash' }], costCentres: [], cashLedger: 'Cash', defaultCreditDays: 45, cashLimitPerDay: 10000, noteAboveAmount: 50000 }
];

export const DEMO_USERS: User[] = [
  { id: 'u-super', name: 'CA Firm — Reviewer', role: 'super_admin' },
  { id: 'u-admin', name: 'Ravi Kulkarni', role: 'client_admin', clientId: 'c1' },
  { id: 'u-staff', name: 'Meena Joshi', role: 'sub_user', clientId: 'c1' },
  { id: 'u-admin2', name: 'Harsh Patel', role: 'client_admin', clientId: 'c2' }
];

export const DEMO_VENDORS: Vendor[] = [
  { id: 'v1', clientId: 'c1', name: 'Kulkarni Associates', gstin: gst('27AAKFK4321L1Z'), gstRegistered: true, gstinStatus: 'Active', pan: 'AAKFK4321L', panEntityType: 'Firm / LLP', panStatus: 'Operative', stateCode: '27', creditDays: 15 },
  { id: 'v2', clientId: 'c1', name: 'Swift Roadlines', gstRegistered: false, pan: 'BXPPS7788Q', panEntityType: 'Individual', panStatus: 'Operative' },
  { id: 'v3', clientId: 'c1', name: 'Bharti Airtel Ltd', tallyLedger: 'Airtel (Bharti Airtel Ltd)', creditDays: 20, gstin: gst('27AAACB2894G1Z'), gstRegistered: true, gstinStatus: 'Active', pan: 'AAACB2894G', panEntityType: 'Company', panStatus: 'Operative', stateCode: '27' },
  { id: 'v4', clientId: 'c1', name: 'Om Sai Security Services', gstRegistered: false, pan: 'CQRPD1122H', panEntityType: 'Individual', panStatus: 'Unverified' },
  { id: 'v5', clientId: 'c1', name: 'Paper House Stationers', gstin: gst('27ABCPH9090J1Z'), gstRegistered: true, gstinStatus: 'Active', pan: 'ABCPH9090J', panEntityType: 'Individual', panStatus: 'Operative', stateCode: '27' },
  { id: 'v7', clientId: 'c1', name: 'Hotel Annapurna', gstRegistered: false, panStatus: 'Unverified' },
  { id: 'v8', clientId: 'c1', name: 'Ramesh Electricals', gstRegistered: false, panStatus: 'Unverified' },
  { id: 'v6', clientId: 'c2', name: 'Gujarat Steel Fabricators', gstin: gst('24AADCG3344P1Z'), gstRegistered: true, gstinStatus: 'Active', pan: 'AADCG3344P', panEntityType: 'Company', panStatus: 'Operative', stateCode: '24' }
];

type Seed = Omit<Expense, 'fyLabel' | 'clientId' | 'entrySource' | 'rcmApplicable' | 'rcmTax' | 'isBackdated' | 'createdBy' | 'createdAt' | 'grossAmount'> &
  Partial<Pick<Expense, 'clientId' | 'rcmApplicable' | 'rcmCode' | 'rcmTax' | 'entrySource' | 'createdBy'>>;

const mk = (s: Seed): Expense => ({
  clientId: 'c1', entrySource: 'photo', rcmApplicable: false, rcmTax: 0, isBackdated: false, createdBy: 'u-staff', attachmentName: 'scanned-bill.jpg',
  ...s, grossAmount: s.taxableValue + s.discount, fyLabel: '2026-27', createdAt: s.invoiceDate + 'T11:00:00'
});

export const DEMO_EXPENSES: Expense[] = [
  mk({ id: 'e1', vendorId: 'v1', vendorName: 'Kulkarni Associates', invoiceNo: 'KA/26/118', invoiceDate: '2026-08-04', hsnSac: '998221', discount: 0, taxableValue: 60000, cgst: 5400, sgst: 5400, igst: 0, totalAmount: 70800, headId: 'h-prof', headConfidence: 0.95, tdsCode: 'PROF_FEES', tdsRatePct: 10, tdsAmount: 6000, itcEligible: true, status: 'posted', postedAt: '2026-09-20T10:00:00', description: 'Statutory audit fees Q1' }),
  mk({ id: 'e2', vendorId: 'v3', vendorName: 'Bharti Airtel Ltd', invoiceNo: 'MH2608-55120', invoiceDate: '2026-08-12', hsnSac: '998422', discount: 0, taxableValue: 2499, cgst: 224.91, sgst: 224.91, igst: 0, totalAmount: 2948.82, headId: 'h-phone', headConfidence: 0.85, tdsAmount: 0, itcEligible: true, status: 'posted', postedAt: '2026-09-20T10:00:00', entrySource: 'qr' }),
  mk({ id: 'e3', vendorId: 'v2', vendorName: 'Swift Roadlines', invoiceNo: '412', invoiceDate: '2026-08-21', hsnSac: '996511', discount: 0, taxableValue: 18500, cgst: 0, sgst: 0, igst: 0, totalAmount: 18500, headId: 'h-freight', headConfidence: 0.85, tdsCode: 'CONTRACT_IND', tdsRatePct: 0, tdsAmount: 0, rcmApplicable: true, rcmCode: 'GTA', rcmRatePct: 5, rcmTax: 925, itcEligible: false, status: 'posted', postedAt: '2026-09-20T10:00:00' }),
  mk({ id: 'e4', vendorId: 'v5', vendorName: 'Paper House Stationers', invoiceNo: 'PH-2231', invoiceDate: '2026-09-03', hsnSac: '4820', discount: 250, taxableValue: 4750, cgst: 427.5, sgst: 427.5, igst: 0, totalAmount: 5605, headId: 'h-print', headConfidence: 0.85, tdsAmount: 0, itcEligible: true, status: 'approved' }),
  mk({ id: 'e5', vendorId: 'v4', vendorName: 'Om Sai Security Services', invoiceNo: 'OSS/09', invoiceDate: '2026-09-30', hsnSac: '998525', discount: 0, taxableValue: 42000, cgst: 0, sgst: 0, igst: 0, totalAmount: 42000, headId: 'h-security', headConfidence: 0.85, tdsCode: 'CONTRACT_IND', tdsRatePct: 1, tdsAmount: 420, rcmApplicable: true, rcmCode: 'SECURITY', rcmRatePct: 18, rcmTax: 7560, itcEligible: true, status: 'approved', costCentreId: 'cc2' }),
  mk({ id: 'e6', vendorId: 'v1', vendorName: 'Kulkarni Associates', invoiceNo: 'KA/26/164', invoiceDate: '2026-09-18', hsnSac: '998231', discount: 0, taxableValue: 25000, cgst: 2250, sgst: 2250, igst: 0, totalAmount: 29500, headId: 'h-prof', headConfidence: 0.95, tdsCode: 'PROF_FEES', tdsRatePct: 10, tdsAmount: 2500, itcEligible: true, status: 'approved' }),
  mk({ id: 'e7', vendorId: 'v3', vendorName: 'Bharti Airtel Ltd', invoiceNo: 'MH2610-60231', invoiceDate: '2026-10-12', hsnSac: '998422', discount: 0, taxableValue: 2499, cgst: 224.91, sgst: 224.91, igst: 0, totalAmount: 2948.82, headId: 'h-phone', headConfidence: 0.95, tdsAmount: 0, itcEligible: true, status: 'submitted', entrySource: 'qr' }),
  mk({ id: 'e8', vendorId: 'v7', vendorName: 'Hotel Annapurna', invoiceNo: '7781', invoiceDate: '2026-10-22', hsnSac: '996331', discount: 0, taxableValue: 3200, cgst: 80, sgst: 80, igst: 0, totalAmount: 3360, headId: 'h-staff', headConfidence: 0.6, tdsAmount: 0, itcEligible: false, status: 'submitted', description: 'Team lunch' }),
  mk({ id: 'e9', vendorId: 'v2', vendorName: 'Swift Roadlines', invoiceNo: '466', invoiceDate: '2026-10-27', hsnSac: '996511', discount: 500, taxableValue: 21500, cgst: 0, sgst: 0, igst: 0, totalAmount: 21500, headId: 'h-freight', headConfidence: 0.95, tdsCode: 'CONTRACT_IND', tdsRatePct: 0, tdsAmount: 0, rcmApplicable: true, rcmCode: 'GTA', rcmRatePct: 5, rcmTax: 1075, itcEligible: false, status: 'submitted' }),
  mk({ id: 'e10', vendorId: 'v8', vendorName: 'Ramesh Electricals', invoiceNo: 'RE-55', invoiceDate: '2026-10-29', discount: 0, taxableValue: 1850, cgst: 0, sgst: 0, igst: 0, totalAmount: 1850, headId: 'h-repair', headConfidence: 0.55, tdsAmount: 0, itcEligible: false, status: 'submitted', entrySource: 'manual', description: 'Fan repair', costCentreId: 'cc3', narration: 'Ceiling fan rewinding at godown', attachmentName: undefined, noImageReason: 'Vendor does not give bills (auto, porter, etc.)' }),
  mk({ id: 'e11', clientId: 'c2', vendorId: 'v6', vendorName: 'Gujarat Steel Fabricators', invoiceNo: 'GSF/1020', invoiceDate: '2026-10-08', hsnSac: '998873', discount: 0, taxableValue: 150000, cgst: 13500, sgst: 13500, igst: 0, totalAmount: 177000, headId: 'h-contract', headConfidence: 0.85, tdsCode: 'CONTRACT_OTH', tdsRatePct: 2, tdsAmount: 3000, itcEligible: true, status: 'submitted', createdBy: 'u-admin2' })
];

export const DEMO_PAYMENTS: Payment[] = [
  { id: 'p1', clientId: 'c1', vendorId: 'v1', vendorName: 'Kulkarni Associates', mode: 'bank', accountId: 'b1', ref: 'NEFT 88123', paidOn: '2026-08-20', amount: 64800, allocations: [{ expenseId: 'e1', amount: 64800 }], isBackdated: false, postedAt: '2026-09-20T10:00:00', createdBy: 'u-admin', createdAt: '2026-08-20T12:00:00' },
  { id: 'p2', clientId: 'c1', vendorId: 'v3', vendorName: 'Bharti Airtel Ltd', mode: 'upi', accountId: 'u1', ref: 'UPI 6620431', paidOn: '2026-08-15', amount: 2948.82, allocations: [{ expenseId: 'e2', amount: 2948.82 }], isBackdated: false, postedAt: '2026-09-20T10:00:00', createdBy: 'u-staff', createdAt: '2026-08-15T12:00:00' },
  { id: 'p3', clientId: 'c1', vendorId: 'v5', vendorName: 'Paper House Stationers', mode: 'cash', accountId: 'c2', paidOn: '2026-09-03', amount: 5605, allocations: [{ expenseId: 'e4', amount: 5605 }], isBackdated: true, flags: ['backdated_payment'], createdBy: 'u-staff', createdAt: '2026-09-06T12:00:00' },
  // one bill paid in two parts, two modes, two days
  { id: 'p4', clientId: 'c1', vendorId: 'v2', vendorName: 'Swift Roadlines', mode: 'cash', accountId: 'c1', paidOn: '2026-08-25', amount: 8000, allocations: [{ expenseId: 'e3', amount: 8000 }], isBackdated: false, postedAt: '2026-09-20T10:00:00', createdBy: 'u-staff', createdAt: '2026-08-25T12:00:00' },
  { id: 'p5', clientId: 'c1', vendorId: 'v2', vendorName: 'Swift Roadlines', mode: 'upi', accountId: 'u2', ref: 'UPI 7781200', paidOn: '2026-09-10', amount: 10500, allocations: [{ expenseId: 'e3', amount: 10500 }], isBackdated: false, createdBy: 'u-staff', createdAt: '2026-09-10T12:00:00' },
  // advance paid to the security agency, not yet applied to a bill
  { id: 'p6', clientId: 'c1', vendorId: 'v4', vendorName: 'Om Sai Security Services', mode: 'bank', accountId: 'b2', ref: 'NEFT 99120', paidOn: '2026-10-05', amount: 15000, allocations: [], isBackdated: false, createdBy: 'u-admin', createdAt: '2026-10-05T12:00:00' }
];

export const DEMO_EVENTS: SystemEvent[] = [
  { id: 's1', level: 'error', component: 'sheets_sync', clientId: 'c2', message: 'Google Sheet not shared with service account — mirror skipped', at: '2026-10-30T02:00:11' },
  { id: 's2', level: 'warn', component: 'gsp_fetch', clientId: 'c1', message: 'GSP consent expired — OTP re-authorisation needed for GSTR-2B fetch', at: '2026-10-29T05:00:03' },
  { id: 's3', level: 'info', component: 'tally_export', clientId: 'c1', message: 'September XML generated: 3 vouchers', at: '2026-09-20T10:00:00' },
  { id: 's4', level: 'warn', component: 'ocr', clientId: 'c1', message: 'Low-confidence read (blurred photo) — sent to manual entry', at: '2026-10-29T16:12:40' },
  { id: 's5', level: 'error', component: 'client_app', clientId: 'c1', message: 'Offline queue retry failed once; succeeded on 2nd attempt', at: '2026-10-28T19:40:02' }
];

export const DEMO_JOBS: JobRun[] = [
  { id: 'j1', job: 'alerts_daily', startedAt: '2026-10-31T03:30:00', ok: true, rows: 6 },
  { id: 'j2', job: 'sheets_mirror', startedAt: '2026-10-31T02:00:00', ok: false, rows: 11, error: '1 of 2 clients failed (c2)' },
  { id: 'j3', job: 'gst_reco_monthly', startedAt: '2026-10-15T05:00:00', ok: true, rows: 42 },
  { id: 'j4', job: 'tally_monthly', startedAt: '2026-10-25T06:00:00', ok: true, rows: 0 },
  { id: 'j5', job: 'compliance_quarterly', startedAt: '2026-10-01T06:00:00', ok: true, rows: 6 }
];

export const DEMO_PROVIDERS: ApiProvider[] = [
  // Every outside connection the app needs. enabled = connected and tested; none is live in the demo.
  { code: 'supabase', label: 'Database, sign-in (email OTP) and server functions', provider: 'Supabase — awaiting go-ahead', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'drive', label: 'Bill filing (Google Drive) and Sheets mirror', provider: 'Google — Shared Drive + service account, or OAuth of the firm account', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'ai', label: 'AI reading, voice, notices (Gemini)', provider: 'Google Gemini — paid tier needed for real bills', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'whatsapp', label: 'WhatsApp bill intake', provider: 'Meta WhatsApp Cloud API', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'gsp', label: 'GSTR-2A/2B fetch (GSP)', provider: 'To be selected on quotes', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'gstin_search', label: 'GSTIN verification', provider: 'To be selected on quotes', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'pan_verify', label: 'PAN verification', provider: 'Protean OPV or KYC vendor', enabled: false, usedThisMonth: 0, cachedHits: 0 },
  { code: 'email', label: 'Email alerts', provider: 'To be selected — free tier first', enabled: false, usedThisMonth: 0, cachedHits: 0 }
];

// Official pages to watch. The watcher only detects that a page CHANGED and raises a finding;
// a CA reads it and updates masters. URLs must be confirmed before go-live.
export const DEMO_SOURCES: ComplianceSource[] = [
  { id: 'cs1', name: 'Income Tax Dept — Notifications', url: 'https://www.incometaxindia.gov.in/', area: 'tds' },
  { id: 'cs2', name: 'CBIC GST — Rate notifications (Central Tax Rate)', url: 'https://cbic-gst.gov.in/', area: 'rcm' },
  { id: 'cs3', name: 'CBIC GST — Central Tax notifications', url: 'https://cbic-gst.gov.in/', area: 'gst' },
  { id: 'cs4', name: 'GST Portal — News & updates', url: 'https://www.gst.gov.in/newsandupdates', area: 'gst' },
  { id: 'cs5', name: 'TIN-NSDL / Protean — TDS statement (FVU) updates', url: 'https://tinpan.proteantech.in/', area: 'forms' }
];
