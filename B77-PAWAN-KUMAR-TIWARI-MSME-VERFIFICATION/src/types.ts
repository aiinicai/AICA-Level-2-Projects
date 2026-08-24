export type MSMEStatus = 'MSME' | 'Non-MSME' | 'Exempt';
export type MSMECategory = 'Micro' | 'Small' | 'Medium' | 'Not Applicable';
export type VerificationStatus = 'Verified' | 'Not Verified' | 'Pending' | 'Mismatch' | 'Not Found';
export type MajorActivity = 'Manufacturing' | 'Services' | 'Trading';

export type UserRole = 'Admin' | 'Finance Manager' | 'Accounts User' | 'Management' | 'Auditor';

export interface Vendor {
  id: string;
  vendorCode: string;
  vendorName: string;
  pan: string;
  gstin: string;
  udyamNumber: string;
  isMSME: boolean;
  msmeStatus: MSMEStatus;
  msmeCategory: MSMECategory;
  majorActivity: MajorActivity;
  udyamRegistrationDate?: string;
  verificationDate?: string;
  verificationStatus: VerificationStatus;
  verifiedBy?: string;
  certificateUrl?: string;
  certificateFileName?: string;
  hasWrittenAgreement: boolean;
  agreedCreditDays: number;
  contactPerson?: string;
  email?: string;
  phone?: string;
  bankAccountNumber?: string;
  bankIfsc?: string;
  remarks: string;
  verificationHistory: VendorVerificationLog[];
  createdDate: string;
  updatedDate: string;
}

export interface VendorVerificationLog {
  id: string;
  timestamp: string;
  verifiedBy: string;
  previousStatus: VerificationStatus;
  newStatus: VerificationStatus;
  previousCategory?: MSMECategory;
  newCategory?: MSMECategory;
  udyamChecked: string;
  portalResponse?: string;
  remarks: string;
}

export interface PartPayment {
  id: string;
  invoiceId: string;
  paymentReference: string;
  paymentDate: string;
  amount: number;
  paymentMode: 'NEFT' | 'RTGS' | 'Cheque' | 'UPI' | 'Direct Debit';
  bankReferenceNo?: string;
  remarks?: string;
  recordedBy: string;
  recordedAt: string;
}

export interface Invoice {
  id: string;
  invoiceNumber: string;
  vendorId: string;
  vendorName: string;
  vendorCode: string;
  msmeCategory: MSMECategory;
  isMSME: boolean;
  invoiceDate: string;
  invoiceAmount: number;
  gstAmount: number;
  totalInvoiceAmount: number;
  poNumber: string;
  poDate: string;
  materialDescription: string;
  mrnDate: string; // Material Receipt Note Date
  acceptanceDate: string; // Actual acceptance date
  deemedAcceptanceDate: string; // MRN + 15 days if not explicitly accepted
  hasWrittenAgreement: boolean;
  agreedPaymentTerms: string; // e.g. "30 Days from MRN", "45 Days from Acceptance"
  creditDays: number;
  statutoryLimitDays: number; // e.g. 45 or 15 days under MSMED Act Section 15
  finalDueDate: string;
  payments: PartPayment[];
  amountPaid: number;
  outstandingAmount: number;
  status: 'Paid' | 'Partially Paid' | 'Unpaid';
  disputeFlag: boolean;
  disputeReason?: string;
  isDueDateManuallyOverridden?: boolean;
  overrideReason?: string;
  overrideApprovedBy?: string;
  attachmentUrl?: string; // Base64 or object preview URL
  attachmentFileName?: string;
  attachmentType?: 'pdf' | 'jpeg' | 'png';
  attachmentSize?: number;
  extractedViaAI?: boolean;
  financialYear: string;
  createdAt: string;
  updatedAt: string;
}

export interface ExtractedInvoiceData {
  fileId: string;
  fileName: string;
  fileType: 'pdf' | 'jpeg' | 'png';
  fileSize: number;
  fileDataUrl: string;
  invoiceNumber: string;
  vendorName: string;
  vendorGstin?: string;
  vendorPan?: string;
  invoiceDate: string;
  basicAmount: number;
  gstRate?: number;
  gstAmount: number;
  totalAmount: number;
  poNumber?: string;
  poDate?: string;
  materialDescription?: string;
  mrnDate?: string;
  acceptanceDate?: string;
  agreedCreditDays?: number;
  hasWrittenAgreement?: boolean;
  agreedPaymentTerms?: string;
  udyamNumber?: string;
  isMsmeClaimed?: boolean;
  matchedVendorId?: string;
  matchedVendorName?: string;
  matchedVendorCode?: string;
  msmeCategory?: MSMECategory;
  confidenceScore?: number;
  extractionEngine?: string;
  extractionNotes?: string[];
  status: 'PENDING' | 'EXTRACTED' | 'VERIFIED' | 'FAILED';
  errorMessage?: string;
}

export interface RateMasterEntry {
  id: string;
  effectiveFrom: string;
  effectiveTo: string; // empty or '9999-12-31' for current
  referenceRateType: 'RBI Repo Rate' | 'RBI Bank Rate';
  referenceRate: number; // in percentage, e.g., 6.50
  multiplier: number; // statutory is 3x
  applicableMSMERate: number; // e.g., 19.50%
  rbiNotificationNo: string;
  notificationDate: string;
  compoundingFrequency: 'Monthly' | 'Simple' | 'Quarterly';
  updatedBy: string;
  updatedAt: string;
  remarks?: string;
}

export interface StatutoryRuleConfig {
  id: string;
  ruleName: string;
  maxCreditDaysWithAgreement: number; // 45 days Section 15
  maxCreditDaysWithoutAgreement: number; // 15 days Section 15
  deemedAcceptanceWindowDays: number; // 15 days
  applicableCategories: ('Micro' | 'Small' | 'Medium')[]; // Section 15/16 applies to Micro & Small
  isSection43BHApplicable: boolean; // Disallowance under Income Tax Act for Micro & Small
  interestMultiplier: number; // 3 times RBI rate
  compoundingMethod: 'Monthly Rest' | 'Simple Interest';
  yearDayBasis: 365 | 366;
  gracePeriodDays: number;
  lastUpdated: string;
  updatedBy: string;
}

export interface TrancheCalculation {
  trancheNumber: number;
  periodStart: string;
  periodEnd: string;
  principalBase: number;
  applicableRate: number;
  referenceRate: number;
  delayDays: number;
  interestAmount: number;
  paymentApplied: number;
  closingBalance: number;
  calculationMethod: string;
  rateEffectiveFrom: string;
  rateEffectiveTo: string;
}

export interface InvoiceInterestResult {
  invoiceId: string;
  invoiceNumber: string;
  vendorId: string;
  vendorName: string;
  msmeCategory: MSMECategory;
  invoiceDate: string;
  totalInvoiceAmount: number;
  acceptanceDate: string;
  finalDueDate: string;
  actualSettlementDate?: string; // Latest payment or as-of date
  asOfDate: string;
  isOverdue: boolean;
  totalDelayDays: number;
  totalPaid: number;
  outstandingPrincipal: number;
  applicableAnnualRate: number;
  referenceRate: number;
  totalInterestPayable: number;
  totalAmountPayable: number; // Principal + Interest
  interestPaid: number;
  interestOutstanding: number;
  tranches: TrancheCalculation[];
  section43BHRisk: boolean;
  status: 'Compliant' | 'Approaching Due' | 'Overdue';
}

export interface AgeingBucketSummary {
  bucketName: string;
  bucketKey: 'not_due' | '0_30' | '31_45' | '46_90' | '91_180' | 'above_180';
  minDays: number;
  maxDays: number | null;
  invoiceCount: number;
  totalPrincipal: number;
  totalInterest: number;
  totalPayable: number;
  vendorCount: number;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string;
  user: string;
  userRole: UserRole;
  module: 'Vendor Master' | 'Invoice Register' | 'Payment Register' | 'Interest Rate Master' | 'Statutory Rules' | 'Verification' | 'Manual Override';
  entityId: string;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'VERIFY' | 'OVERRIDE' | 'APPROVE' | 'REJECT' | 'BULK_IMPORT';
  fieldName?: string;
  originalValue?: string;
  revisedValue?: string;
  reason: string;
  requiresApproval: boolean;
  approvalStatus?: 'Approved' | 'Pending' | 'Rejected' | 'Not Required';
  approvedBy?: string;
  approvedAt?: string;
}

export interface ExceptionAlert {
  id: string;
  type: 'CERTIFICATE_MISSING' | 'UDYAM_MISMATCH' | 'PAN_GSTIN_MISMATCH' | 'OVERDUE_INVOICE' | 'STATUTORY_BREACH' | 'HIGH_INTEREST_EXPOSURE' | 'VERIFICATION_PENDING' | 'DUE_SOON' | '43BH_TAX_RISK';
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  title: string;
  description: string;
  entityId: string;
  entityName: string;
  vendorId?: string;
  invoiceId?: string;
  amount?: number;
  date: string;
  actionRequired: string;
  targetModule: 'Vendor Master' | 'MSME Verification' | 'Invoice Register' | 'Payment Register' | 'Interest Calculator';
}
