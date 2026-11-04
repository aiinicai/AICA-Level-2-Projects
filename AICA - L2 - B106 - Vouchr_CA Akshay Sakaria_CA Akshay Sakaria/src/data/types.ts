export type Role = 'super_admin' | 'client_admin' | 'sub_user';
export type Lang = 'en' | 'hi';

export interface Client {
  id: string;
  name: string;
  /** Auto-approval of low-risk bills — set by the CA firm only (lib/autoApprove.ts). Off when missing. */
  autoApprove?: { enabled: boolean; maxAmount: number; samplePct: number; minHistory: number };
  driveShareWithAdmins?: boolean; // share Vouchr/<Client> read-only with the client's admins (live: drive-share function)
  gstin?: string;
  stateCode?: string;
  logoUrl?: string;
  brandColor: string;
  tallyMode: 'none' | 'xml_file' | 'bridge';
  tallyCompany?: string;
  backdateWindowDays: number;
  bankAccounts: BankAccount[];
  cashLedger: string;
  defaultCreditDays: number; // bill due date = bill date + vendor credit days (or this default)
  cashLimitPerDay: number; // cash paid to one vendor in a day above this is flagged (Act limit to be verified)
  noteAboveAmount: number; // bills above this need a "what was it for" note
  costCentres: CostCentre[]; // optional projects / branches to tag bills with
  engagementEndsOn?: string; // consent stays valid until the engagement with the CA firm ends (or is withdrawn earlier)
}

/** DPDP Act consent record. scope 'user' = the individual's own consent; scope 'client' = the client company's acceptance
 *  of the data-processing terms (contractual). Records are never deleted; withdrawal is stamped on the record. */
export interface Consent {
  id: string;
  scope: 'user' | 'client';
  userId?: string;
  clientId?: string;
  noticeVersion: string;
  purposes: { core: boolean; ai: boolean };
  lang: Lang;
  method: 'in_app' | 'engagement_letter';
  ageConfirmed?: boolean;
  reference?: string; // e.g. "Engagement letter dated 01-04-2026"
  acceptedBy: string;
  acceptedAt: string;
  validUntil?: string;
  withdrawnAt?: string;
  withdrawnBy?: string;
  withdrawReason?: string;
}

/** Data Principal rights request (DPDP Act s.11–14) — to be answered within 90 days (DPDP Rules 2025). */
export interface PrivacyRequest {
  id: string;
  userId: string;
  clientId?: string;
  kind: 'access' | 'correction' | 'erasure' | 'grievance' | 'nominate';
  details: string;
  createdAt: string;
  dueBy: string;
  status: 'open' | 'resolved';
  resolution?: string;
  resolvedAt?: string;
}

/** The CA firm running Vouchr — named in the privacy notice with its contact for privacy questions (s.8(9)). */
export interface FirmInfo { name: string; privacyContactName?: string; privacyEmail?: string; privacyPhone?: string; whatsappNumber?: string /* where staff send bills */;
  irpPublicKeyPem?: string /* e-invoice portal public key, saved by the CA — used to check signed QR codes */ }

/** Where money is paid from: a bank account, a UPI ID (linked to a bank), a company card or a cash box. */
export interface BankAccount {
  id: string;
  kind: 'bank' | 'upi' | 'card' | 'cash';
  name: string; // e.g. "HDFC Current ••4521", "GPay · shreeganesh@okhdfc", "Petty cash — Office"
  upiId?: string;
  linkedBankId?: string; // UPI ID → the bank account it debits
  tallyLedger: string;
  /** statement columns chosen once for this bank (header names), reused for the next upload */
  statementColumns?: { date: string; narration: string; ref?: string; debit?: string; credit?: string; amount?: string; drCr?: string; minusIsDebit?: boolean };
  active?: boolean;
}

export interface CostCentre {
  id: string;
  kind: 'project' | 'branch';
  name: string;
  active: boolean;
}

export type PayMode = 'cash' | 'upi' | 'bank' | 'cheque' | 'card';

export interface User {
  id: string;
  name: string;
  role: Role;
  clientId?: string;
  active?: boolean;
  whatsapp?: string; // E.164 digits, e.g. 919876543210 — set by an admin
  whatsappVerifiedAt?: string; // set only when the person sent the one-time code FROM this number (lib/waVerify.ts)
  whatsappCode?: { hash: string; expires: string; tries: number }; // SHA-256 of the pending code — the code itself is not kept
}

export interface Vendor {
  id: string;
  clientId: string;
  name: string;
  gstin?: string;
  gstRegistered: boolean;
  gstinStatus?: string;
  pan?: string;
  panEntityType?: string;
  panStatus?: 'Operative' | 'Inoperative' | 'Unverified';
  stateCode?: string;
  creditDays?: number;
  tallyLedger?: string; // party ledger name in Tally, when it differs from the vendor name
}

export interface ExpenseHead {
  id: string;
  name: string;
  tallyLedger: string;
  keywords: string[];
  sacHsnPrefixes: string[];
  defaultTdsCode?: string;
  blocked175?: string;
  rcmCode?: string;
}

export interface TdsRate {
  code: string;
  description: string;
  actReference?: string;
  ratePct: number;
  thresholdSingle?: number;
  thresholdAggregate?: number;
  appliesToEntity?: string[];
  noPanRatePct?: number;
  effectiveFrom: string;
  effectiveTo?: string;
  verified: boolean;
  sourceNote: string;
}

export interface RcmRule {
  code: string;
  description: string;
  supplierCondition: 'unregistered' | 'non_body_corporate' | 'any';
  notificationRef: string;
  defaultRatePct: number; // GST rate payable under RCM — must be verified
  supply?: 'goods' | 'services'; // decides the time-of-supply rule (s.12(3) goods / s.13(3) services); default services
  verified: boolean;
}

export interface BlockedRule {
  code: string;
  description: string;
  keywords: string[];
}

export type ExpenseStatus = 'draft' | 'submitted' | 'approved' | 'rejected' | 'posted';

export interface Expense {
  id: string;
  clientId: string;
  fyLabel: string;
  vendorId?: string;
  vendorName: string;
  invoiceNo?: string;
  invoiceDate: string; // yyyy-mm-dd
  entrySource: 'photo' | 'qr' | 'manual' | 'pdf' | 'whatsapp';
  /** Part of the bill total outside this supplier's GST, recorded exactly as printed: e.g. air / rail fare a travel portal
   *  collects on behalf of the airline or IRCTC, reimbursements. Posted to the expense ledger without GST. */
  nonTaxableAmount?: number;
  /** Section 9(5) CGST Act: GST on this supply is paid by the e-commerce operator (Zomato, Swiggy, Uber, Ola…), not the supplier. */
  ecoPaysTax?: boolean;
  ecoGstin?: string;
  irn?: string;
  irnSignature?: 'valid' | 'invalid' | 'unchecked'; // signed e-invoice QR checked against the IRP public key
  noteAdjust?: number; // + debit notes − credit notes linked to this bill (kept in step by the store)
  imageHash?: string;
  imageDataUrl?: string; // small thumbnail for lists/previews only — the original is in Drive (fileId)
  attachmentName?: string; // PDF / e-mailed bill
  noImageReason?: string; // required when no photo/file is attached
  fileId?: string; // Google Drive file id ("local:…" in demo) of the original bill
  filePath?: string; // Vouchr/<Client>/FY …/Bills/<name>
  narration?: string; // accounting narration (goes to the Tally voucher)
  costCentreId?: string; // optional project / branch
  description?: string;
  hsnSac?: string;
  grossAmount: number;
  discount: number;
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
  headId?: string;
  headConfidence?: number;
  tdsCode?: string;
  tdsRatePct?: number;
  tdsAmount: number;
  rcmApplicable: boolean;
  rcmCode?: string;
  rcmRatePct?: number;
  rcmTax: number; // GST payable by us under reverse charge
  itcEligible?: boolean;
  blockedCode?: string;
  status: ExpenseStatus;
  reviewNote?: string;
  reviewedAt?: string;
  isBackdated: boolean;
  createdBy: string;
  createdAt: string;
  postedAt?: string;
  resubmittedAt?: string;
  autoApproved?: boolean; // approved by the client's auto-approval rule, not by a person
  sampleCheck?: boolean; // passed the rule but picked for a CA sample check
  assignedTo?: string; // CA reviewer the bill is assigned to
  notDuplicateOf?: string; // user confirmed this is a different bill from a look-alike
}

export interface Allocation {
  expenseId: string;
  amount: number;
  tdsCredit?: number; // TDS already deducted on the advance this cash came from (counts against the bill's TDS)
}

/** One payment to a vendor. It may settle several bills (allocations); any unallocated balance is an advance. */
export interface Payment {
  id: string;
  clientId: string;
  vendorId: string;
  vendorName: string;
  mode: PayMode;
  accountId?: string; // bank account for non-cash modes
  ref?: string; // UTR / UPI ref / cheque no.
  paidOn: string;
  amount: number;
  allocations: Allocation[];
  isBackdated: boolean;
  flags?: string[]; // e.g. cash_limit, paid_before_bill_date
  source?: 'manual' | 'bank_import' | 'excel_import';
  postedAt?: string; // exported to Tally as a Payment voucher
  /** TDS deducted on the advance part of this payment (s.393: at payment, if earlier than the bill). */
  tdsOnAdvance?: { code: string; ratePct: number; amount: number; base?: number }; // base = amount credited to the vendor (cash + TDS)
  createdBy: string;
  createdAt: string;
}

export interface TdsChallan {
  id: string;
  clientId: string;
  month: string; // yyyy-mm of deduction
  amount: number;
  bsrCode: string;
  challanNo: string;
  paidOn: string;
  cin?: string;
  fileName?: string; // challan receipt PDF / photo the details were read from
  fileId?: string;
  filePath?: string;
}

export type RecoStatus = 'matched' | 'mismatch' | 'missing_in_2b' | 'missing_in_books';

export interface RecoLine {
  docType?: 'invoice' | 'credit' | 'debit'; // GSTR-2B B2B (invoice) or CDNR (credit / debit note)
  supplierGstin: string;
  supplierName?: string;
  invoiceNo: string;
  invoiceDate?: string;
  taxableValue: number;
  igst: number;
  cgst: number;
  sgst: number;
  cess: number;
  invoiceValue?: number;
  itcAvailable?: boolean;
}

/** A financial year closed by the CA firm (lib/fyClose.ts): all 12 months locked, carry-forward totals kept. */
export interface FyClose { clientId: string; fy: string; closedBy: string; at: string; warningsAcknowledged: string[]; carry: { openBills: number; advances: number; advanceTds: number; notes: number } }

/** 180-day ITC reversal recorded by the CA (s.16(2) second proviso) and its re-claim once paid. lib/gstRegisters.ts */
export interface ItcReversal {
  id: string;
  clientId: string;
  expenseId: string;
  amount: number;
  reversedIn: string; // return period yyyy-mm
  reclaimedAmount?: number;
  reclaimedIn?: string;
  by: string;
  at: string;
}

/** Credit / debit note received from a vendor (CGST Act s.34). See lib/vendorNotes.ts. */
export interface VendorNote {
  id: string;
  clientId: string;
  fyLabel: string;
  vendorId: string;
  vendorName: string;
  kind: 'credit' | 'debit';
  noteNo: string;
  noteDate: string;
  expenseId?: string; // the bill it corrects; empty = vendor level until linked
  reason: 'return' | 'rate' | 'discount' | 'deficiency' | 'other';
  headId?: string; // expense head for Tally when not linked (linked notes use the bill's head)
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
  itcEligible: boolean;
  flags?: string[]; // e.g. tds_on_original — marked for the CA
  remark?: string;
  fileId?: string;
  filePath?: string;
  status: 'active' | 'void';
  voidReason?: string;
  postedAt?: string;
  createdBy: string;
  createdAt: string;
}

export interface RecoRun {
  id: string;
  clientId: string;
  period: string; // label shown to user, e.g. 'Oct 2026' or file's rtnprd
  source: 'json_upload' | 'gsp';
  lines: RecoLine[];
  createdAt: string;
}

export interface AuditEntry {
  id: string;
  clientId?: string;
  actor: string;
  table: string;
  rowId?: string;
  action: string;
  flag?: string;
  summary: string;
  at: string;
}

export interface SystemEvent {
  id: string;
  level: 'info' | 'warn' | 'error';
  component: string;
  clientId?: string;
  message: string; // an English template, shown through tr() — {err} holds the technical error text, kept as it was
  vars?: Record<string, string | number>;
  at: string;
}

export interface JobRun {
  id: string;
  job: string;
  startedAt: string;
  ok: boolean;
  rows: number;
  error?: string;
}

export interface ApiProvider {
  code: string;
  label: string;
  provider: string;
  freeQuotaMonthly?: number;
  unitCostInr?: number;
  enabled: boolean;
  usedThisMonth: number;
  cachedHits: number;
}

export interface ComplianceSource {
  id: string;
  name: string;
  url: string;
  area: string;
  lastCheckedAt?: string;
  lastChangedAt?: string;
}

export interface ComplianceFinding {
  id: string;
  area: string;
  kind: 'source_changed' | 'review_due' | 'unverified_master' | 'source_unreachable' | 'ai_suggestion';
  title: string;
  detail: string;
  status: 'open' | 'accepted' | 'dismissed';
  createdAt: string;
}

export interface Notification {
  id: string;
  clientId?: string;
  kind: string;
  title: string;
  body: string;
  dueOn?: string;
  severity: 'info' | 'warn' | 'danger';
  /** Translatable templates ({placeholders} filled from vars); title/body stay as English fallbacks. */
  tTitle?: string;
  tBody?: string;
  vars?: Record<string, string | number>;
}
