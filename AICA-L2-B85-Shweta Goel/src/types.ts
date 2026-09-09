export type AuditModule = 'invoice' | 'gst' | 'bank' | 'tds';

export type RiskLevel = 'compliant' | 'warning' | 'critical';

export interface UploadedDocument {
  id: string;
  name: string;
  type?: 'image' | 'pdf' | string;
  mimeType: string;
  dataUrl: string;
  rawBase64?: string;
  base64Data?: string;
  size: number;
  uploadedAt: string;
  isSample?: boolean;
  sampleType?: string;
}

/* =========================================================
   1. INVOICE REVIEW MODULE TYPES
   ========================================================= */
export interface InvoiceLineItem {
  id?: string;
  description: string;
  hsnSac?: string;
  quantity?: number;
  unit?: string;
  unitPrice?: number;
  taxableValue: number;
  gstRatePercent: number;
  cgst?: number;
  sgst?: number;
  igst?: number;
  total: number;
}

export interface InvoiceAuditIssue {
  type: 'math_error' | 'missing_field' | 'tax_mismatch' | 'compliance_warning' | 'info';
  severity: 'high' | 'medium' | 'low';
  title: string;
  message: string;
  field?: string;
}

export interface AccountingJournalEntry {
  debitLedger: string;
  debitAmount: number;
  gstInputLedger?: string;
  gstInputAmount?: number;
  creditLedger: string;
  creditAmount: number;
  tdsPayableLedger?: string;
  tdsPayableAmount?: number;
}

export interface SuggestedAccountHead {
  ledgerName: string;
  accountCategory: string;
  natureOfExpense: 'Revenue Expenditure' | 'Capital Expenditure' | 'Deferred Revenue';
  costCenter?: string;
  accountingRationale: string;
  recommendedJournalEntry?: AccountingJournalEntry;
}

export interface InvoiceReviewData {
  vendorName: string;
  vendorGSTIN: string;
  receiverName: string;
  receiverGSTIN: string;
  invoiceNumber: string;
  invoiceDate: string;
  dueDate?: string;
  placeOfSupply: string;
  taxableAmount: number;
  cgstAmount: number;
  sgstAmount: number;
  igstAmount: number;
  cessAmount?: number;
  totalCalculatedTax: number;
  totalInvoiceAmount: number;
  computedTotal: number;
  mathDiscrepancy: number;
  isMathValid: boolean;
  lineItems: InvoiceLineItem[];
  riskStatus: RiskLevel;
  auditIssues: InvoiceAuditIssue[];
  confidenceScore: number;
  summary: string;
  suggestedAccountHead?: SuggestedAccountHead;
}

/* =========================================================
   2. GST COMPLIANCE MODULE TYPES
   ========================================================= */
export interface GSTComplianceFlag {
  rule: string;
  status: 'PASS' | 'FAIL' | 'WARNING';
  message: string;
  impact: string;
  remedy: string;
}

export interface GSTBlockedCreditClause {
  clause: string;
  title: string;
  category: string;
  isTriggered: boolean;
  status: 'BLOCKED' | 'CLEAR' | 'POTENTIAL_RISK';
  statutoryText: string;
  reason: string;
}

export interface GSTSection16Condition {
  conditionNumber: string;
  title: string;
  requirement: string;
  isSatisfied: boolean;
  status: 'SATISFIED' | 'NOT_SATISFIED' | 'PENDING_VERIFICATION';
  statutoryRef: string;
  notes: string;
}

export interface GSTLineItemITCClassification {
  description: string;
  hsnSac?: string;
  taxableValue: number;
  taxRatePercent: number;
  totalTax: number;
  nature: 'Input Goods' | 'Input Services' | 'Capital Goods' | 'Motor Vehicle' | 'Food & Catering' | 'Works Contract' | 'Personal / Non-Business' | 'Other Ineligible';
  itcEligibility: 'ELIGIBLE' | 'BLOCKED_17_5' | 'BLOCKED_POS' | 'REVERSIBLE';
  sectionRef: string;
  eligibleTaxAmount: number;
  blockedTaxAmount: number;
  reason: string;
  alertLevel?: string; // e.g. "🔴 Critical Red (Blocked Credit)" or "🟢 Compliant Green"
}

export interface GSTITCEligibilityData {
  overallEligibility: 'ELIGIBLE' | 'BLOCKED_17_5' | 'BLOCKED_POS_ERROR' | 'PARTIALLY_ELIGIBLE' | 'REVERSAL_REQUIRED';
  totalGstPaid: number;
  eligibleITCAmount: number;
  blockedITCAmount: number;
  gstr3bReportingTable: string; // e.g. "Table 4(A)(5) - All Other ITC" or "Table 4(B)(1) - Ineligible as per Section 17(5)"
  gstr2bReconciliationNote: string;
  timeLimitSection16_4: {
    maxAvailmentDate: string;
    isWithinTimeLimit: boolean;
    statutoryDeadlineNote: string;
  };
  rule37_180DaysReversal: {
    invoiceDate: string;
    paymentDueDate180Days: string;
    interestRatePercent: number;
    riskStatus: 'SAFE' | 'WARNING_OVERDUE' | 'REVERSED';
  };
  blockedCreditClauses: GSTBlockedCreditClause[];
  section16GoldenConditions: GSTSection16Condition[];
  itemClassifications?: GSTLineItemITCClassification[];
  caWorkpaperFinding: string;
  actionRequired: string;
}

export interface GSTComplianceData {
  vendorName: string;
  vendorGSTIN: string;
  vendorState: string;
  vendorStateCode: string;
  isVendorGSTINValid: boolean;
  receiverName: string;
  receiverGSTIN: string;
  receiverState: string;
  receiverStateCode: string;
  isReceiverGSTINValid: boolean;
  invoiceNumber: string;
  invoiceDate: string;
  placeOfSupply: string;
  placeOfSupplyStateCode: string;
  transactionType: 'INTRA_STATE' | 'INTER_STATE' | 'SEZ_EXPORT' | 'UNSPECIFIED';
  expectedTaxType: 'CGST_SGST' | 'IGST' | 'ZERO_RATED';
  appliedTaxType: 'CGST_SGST' | 'IGST' | 'BOTH' | 'NONE';
  isPoSCompliant: boolean;
  taxableValue: number;
  cgstCharged: number;
  sgstCharged: number;
  igstCharged: number;
  appliedTaxRates: number[];
  areTaxRatesStandard: boolean;
  gstr2bMatchStatus: 'MATCHED' | 'MISMATCH_TAX' | 'MISMATCH_INVOICE_NO' | 'NOT_IN_2B' | 'ELIGIBLE_ITC';
  riskStatus: RiskLevel;
  complianceFlags: GSTComplianceFlag[];
  auditNotes: string;
  itcEligibility?: GSTITCEligibilityData;
}

/* =========================================================
   3. BANK STATEMENT ANALYSIS TYPES
   ========================================================= */
export interface BankTransaction {
  id: string;
  date: string;
  description: string;
  referenceNo?: string;
  debit?: number;
  credit?: number;
  balance: number;
  mode: 'CASH' | 'UPI' | 'NEFT' | 'RTGS' | 'IMPS' | 'CHEQUE' | 'CHARGES' | 'INTEREST' | 'OTHER';
  isCashAbove50k: boolean;
  isDuplicate: boolean;
  category?: string;
  notes?: string;
}

export interface CashAuditAlert {
  date: string;
  amount: number;
  type: 'DEPOSIT' | 'WITHDRAWAL';
  ruleViolation: string;
  section: 'Sec 269ST' | 'Sec 269SS' | 'Sec 269T' | 'SFT Reporting';
  description: string;
}

export interface DuplicateGroup {
  date: string;
  amount: number;
  type: 'DEBIT' | 'CREDIT';
  descriptions: string[];
  count: number;
}

export interface BankStatementData {
  bankName: string;
  accountNumber: string;
  accountHolder: string;
  ifscCode?: string;
  period: { from: string; to: string };
  openingBalance: number;
  closingBalance: number;
  totalInflows: number;
  totalOutflows: number;
  netCashFlow: number;
  totalTransactionsCount: number;
  highCashTransactionsCount: number;
  duplicateTransactionsCount: number;
  transactions: BankTransaction[];
  cashAuditAlerts: CashAuditAlert[];
  duplicateGroups: DuplicateGroup[];
  riskStatus: RiskLevel;
  auditSummary: string;
}

/* =========================================================
   4. TDS ANALYSER MODULE TYPES
   ========================================================= */
export interface SectionWiseTDS {
  section: string;
  description: string;
  natureOfPayment: string;
  taxableAmount: number;
  applicableRate: number;
  deductedRate: number;
  expectedTDS: number;
  actualTDS: number;
  variance: number;
  status: 'CORRECT' | 'SHORT_DEDUCTION' | 'OVER_DEDUCTION' | 'MISSED_TDS';
  remarks: string;
}

export interface TDSAnalysisData {
  deductorName: string;
  deductorTAN?: string;
  deducteeName: string;
  deducteePAN?: string;
  invoiceOrRefNumber: string;
  date: string;
  grossServiceAmount: number;
  natureOfService: string;
  declaredTDSSection: string;
  recommendedTDSSection: string;
  sectionTitle: string;
  standardRate: number;
  appliedRate: number;
  isRateCorrect: boolean;
  actualTDSDeducted: number;
  expectedTDSDeducted: number;
  tdsVariance: number; // positive = short deduction
  thresholdLimit: number;
  isThresholdExceeded: boolean;
  isTDSMissed: boolean;
  isShortDeduction: boolean;
  lowerDeductionCertStatus: 'NO_CERTIFICATE' | 'VALID_SEC_197' | 'EXPIRED';
  sectionWiseBreakdown: SectionWiseTDS[];
  riskStatus: RiskLevel;
  caAuditRecommendations: string[];
  form26ASDeclarationStatus: 'MATCHED' | 'UNMATCHED' | 'NOT_REPORTED' | 'NOT_APPLICABLE';
}

/* =========================================================
   CA FIRM & CLIENT CONFIG
   ========================================================= */
export interface CAFirmProfile {
  firmName: string;
  partnerName: string;
  membershipNo?: string;
  frnNumber?: string;
  clientName: string;
  clientPAN?: string;
  clientGSTIN?: string;
  financialYear: string;
  assessmentYear?: string;
}
