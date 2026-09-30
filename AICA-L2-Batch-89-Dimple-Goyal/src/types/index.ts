/**
 * Indian Receivables & Reconciliation Platform Data Types
 * Comprehensive data schema for multi-tenant SME receivables,
 * payment allocations, TDS 26AS/AIS, and GST reconciliation.
 */

export type UserRole = 
  | 'Business Owner'
  | 'Accountant'
  | 'Finance Manager'
  | 'CA / Consultant'
  | 'Viewer';

export interface User {
  id: string;
  userId: string; // unique login ID (e.g. 'dimple.admin')
  password?: string; // encrypted or stored password (e.g. 'Admin@2026')
  name: string;
  email: string;
  role: UserRole;
  avatarUrl?: string;
  assignedCompanies: string[]; // ['*'] for all or array of company IDs
  phone?: string;
  department?: string;
  lastLogin?: string;
}

export interface Company {
  id: string;
  name: string;
  legalName: string;
  pan: string;
  gstin: string;
  tan?: string;
  msmeRegNo?: string;
  cin?: string;
  businessType: 'Private Limited' | 'Partnership' | 'Sole Proprietorship' | 'LLP' | 'Public Limited';
  industry: string;
  address: string;
  state: string;
  stateCode: string;
  financialYear: string;
  booksStartDate: string;
  currency: 'INR';
  defaultPaymentTerms: number; // in days, e.g. 30
  defaultTdsSection: string;
  defaultTdsRate: number; // e.g. 1% or 2% or 10%
  email?: string;
  phone?: string;
  logoUrl?: string;
  isDefault?: boolean;
}

export interface CustomerAlias {
  alias: string;
  notes?: string;
}

export interface Customer {
  id: string;
  customerId: string; // Display code like CUST-1001
  name: string;
  legalName: string;
  pan: string;
  gstin: string;
  customerType: 'B2B' | 'B2C' | 'Government' | 'SEZ';
  state: string;
  address: string;
  contactPerson: string;
  email: string;
  phone: string;
  paymentTerms: number; // in days
  creditLimit: number;
  tdsApplicable: boolean;
  tdsSection?: string; // 194C (1%/2%), 194J (10%/2%), 194Q (0.1%), 194I (10%)
  tdsRate?: number;
  openingBalance: number;
  status: 'Active' | 'Inactive' | 'Archived';
  notes?: string;
  aliases: string[]; // e.g. ["ABC PVT LTD", "ABC LTD", "ABC CORPORATION"]
  createdAt: string;
}

export type InvoiceStatus = 
  | 'Unpaid'
  | 'Partially Paid'
  | 'Fully Paid'
  | 'Overdue'
  | 'Cancelled'
  | 'Written Off';

export type GSTType = 'B2B' | 'B2C' | 'SEZ' | 'Export';

export interface InvoiceItem {
  id: string;
  description: string;
  hsnSac: string;
  quantity: number;
  rate: number;
  taxableAmount: number;
  gstRate: number; // percentage, e.g. 18
}

export interface Invoice {
  id: string;
  invoiceNumber: string; // e.g. INV-2026-001
  invoiceDate: string; // YYYY-MM-DD
  customerId: string;
  customerName: string;
  customerGstin: string;
  customerPan: string;
  customerState?: string;
  hsnSacCode?: string;
  description?: string;
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  cess: number;
  cgstAmount?: number;
  sgstAmount?: number;
  igstAmount?: number;
  gstAmount?: number;
  gstRate?: number;
  gstType?: string;
  totalInvoiceValue: number;
  paymentTerms: number; // days
  dueDate: string; // YYYY-MM-DD
  tdsApplicable: boolean;
  tdsSection?: string;
  tdsRate?: number;
  tdsDeducted?: number;
  expectedTds: number;
  netReceivable: number; // Total - expectedTds
  amountReceived: number;
  amountAllocated: number;
  balance: number; // Total - amountReceived - tdsDeducted
  status: InvoiceStatus;
  items?: InvoiceItem[];
  notes?: string;
  createdAt: string;
}

export type BankTransactionType = 
  | 'Customer Receipt'
  | 'Bank Charges'
  | 'Inter-account Transfer'
  | 'Vendor Payment'
  | 'Unknown Receipt';

export type AllocationStatus = 
  | 'Unallocated'
  | 'Partially Allocated'
  | 'Fully Allocated';

export interface BankTransaction {
  id: string;
  transactionDate: string; // YYYY-MM-DD
  valueDate: string;
  bankAccount: string; // e.g. "HDFC Current A/c ...4812"
  narration: string;
  referenceNumber: string; // UTR or Cheque No
  debit: number;
  credit: number;
  amount: number;
  runningBalance?: number;
  type: BankTransactionType;
  customerId?: string;
  customerName?: string;
  allocationStatus: AllocationStatus;
  allocatedAmount: number;
  unallocatedAmount: number;
  parsedInvoiceNo?: string;
  extractedInvoiceNumber?: string;
  matchedInvoiceNumbers?: string[];
  parsedCustomerName?: string;
  isCredit: boolean;
  createdAt: string;
}

export type MatchRuleType = 
  | 'Rule 1: Invoice Number Match'
  | 'Rule 2: Exact Customer + Amount'
  | 'Rule 3: Customer + Amount + Date Proximity'
  | 'Rule 4: Split Payment (One-to-Many)'
  | 'Rule 5: Consolidated Payment (Many-to-One)'
  | 'Rule 6: Partial Payment'
  | 'Rule 7: TDS Adjustment Match'
  | 'Rule 8: Short Payment'
  | 'Rule 9: Excess Payment'
  | 'Manual Match';

export type MatchConfidenceLevel = 'High' | 'Medium' | 'Low';

export interface PaymentAllocation {
  id: string;
  bankTransactionId: string;
  invoiceId: string;
  invoiceNumber: string;
  customerId: string;
  customerName: string;
  paymentDate: string;
  allocatedAmount: number;
  tdsDeducted: number;
  discountGiven: number;
  bankCharges: number;
  shortPaymentReason?: 'TDS' | 'Discount' | 'Bank charges' | 'Deduction' | 'Dispute' | 'Other';
  shortPaymentAmount: number;
  excessPaymentAmount: number;
  excessHandling?: 'Advance' | 'Adjustment against future invoice' | 'Refund' | 'Other';
  confidenceScore: number; // 0-100
  confidenceLevel: MatchConfidenceLevel;
  ruleApplied: MatchRuleType;
  status: 'Suggested' | 'Accepted' | 'Rejected' | 'Manual';
  acceptedBy?: string;
  acceptedAt?: string;
  notes?: string;
}

export interface TDS26ASRecord {
  id: string;
  deductorName: string;
  tan: string;
  pan: string;
  section: string; // 194C, 194J, etc.
  transactionDate: string;
  amountPaidCredited: number;
  tdsDeducted: number;
  tdsDeposited: number;
  assessmentYear: string;
  financialYear: string;
  quarter: 'Q1' | 'Q2' | 'Q3' | 'Q4';
  matchedInvoiceId?: string;
  matchedInvoiceNumber?: string;
  customerId?: string;
  status: 'Matched' | 'TDS Mismatch' | 'TDS Not Reflected';
  discrepancyAmount?: number;
  discrepancyReason?: string;
}

export interface GSTRecord {
  id: string;
  gstin: string;
  customerGstin?: string;
  customerName?: string;
  tradeName: string;
  invoiceNumber: string;
  invoiceDate: string;
  taxableValue: number;
  cgst: number;
  sgst: number;
  igst: number;
  total: number;
  totalValue?: number;
  cgstAmount?: number;
  sgstAmount?: number;
  igstAmount?: number;
  gstr1ReportedValue?: number;
  source: 'Sales Register (Books)' | 'GSTR-1 Portal' | 'E-Invoice Portal';
  status: 'Matched' | 'Invoice Missing in GST' | 'GST Data Missing in Books' | 'Amount Mismatch' | 'Tax Mismatch' | 'Duplicate Invoice';
  discrepancyRemarks?: string;
  discrepancyReason?: string;
  differenceAmount?: number;
}

export interface DebtorReconciliationSummary {
  customerId?: string;
  customerName: string;
  customerGstin: string;
  booksInvoiceCount: number;
  gstr1InvoiceCount: number;
  booksTaxableValue: number;
  gstr1TaxableValue: number;
  booksTaxAmount: number;
  gstr1TaxAmount: number;
  booksTotalValue: number;
  gstr1TotalValue: number;
  taxableVariance: number;
  taxVariance: number;
  totalVariance: number;
  status: 'Fully Matched' | 'Tax / Amount Variance' | 'Missing in GSTR-1' | 'Only in GSTR-1';
  invoices: GSTRecord[];
}

export type ExceptionCategory = 
  | 'Unmatched Receipt'
  | 'Unmatched Invoice'
  | 'Short Payment'
  | 'Excess Payment'
  | 'TDS Missing'
  | 'TDS Mismatch'
  | 'GST Mismatch'
  | 'Duplicate Invoice'
  | 'Duplicate Receipt'
  | 'Unknown Customer'
  | 'Overdue Invoice'
  | 'Invalid Invoice Data';

export interface ExceptionItem {
  id: string;
  category: ExceptionCategory;
  customerId?: string;
  customerName?: string;
  transactionRef?: string;
  invoiceNumber?: string;
  amount: number;
  date: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'Open' | 'In Progress' | 'Resolved' | 'Ignored';
  assignedTo: string;
  remarks: string;
  resolution?: string;
  createdAt?: string;
  resolvedAt?: string;
}

export type DocumentRecord = DocumentItem;

export interface DocumentItem {
  id: string;
  type: 'Invoice' | 'Bank Statement' | 'Form 26AS' | 'GSTR-1' | 'Payment Proof' | 'Other';
  fileName: string;
  fileSize: string;
  fileUrl?: string;
  uploadedBy?: string;
  uploadedAt: string;
  customerId?: string;
  customerName?: string;
  invoiceNumber?: string;
  linkedCustomerId?: string;
  linkedCustomerName?: string;
  linkedInvoiceId?: string;
  linkedInvoiceNumber?: string;
  linkedTransactionId?: string;
  notes?: string;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  userName: string;
  userRole: UserRole;
  action: string;
  entity: string;
  entityId: string;
  oldValue?: string;
  newValue?: string;
  ipAddress?: string;
}

export interface AgeingBucketSummary {
  bucketName: string;
  minDays: number;
  maxDays: number | null; // null for >365
  amount: number;
  invoiceCount: number;
  percentage: number;
}

export interface CustomerAgeingSummary {
  customerId: string;
  customerName: string;
  totalOutstanding: number;
  notDue: number;
  days0to30: number;
  days31to60: number;
  days61to90: number;
  days91to180: number;
  days181to365: number;
  daysAbove365: number;
  days0_30: number;
  days31_60: number;
  days61_90: number;
  days91_180: number;
  days181_365: number;
  days365Plus: number;
  overdueAmount: number;
  averageAgeDays: number;
}

export interface ReconciliationSettings {
  amountTolerance: number; // e.g. 0, 1, 10, 100
  dateToleranceDays: number; // e.g. 7
  autoMatchConfidenceThreshold: number; // e.g. 90
  allowSplitPayments: boolean;
  allowAutoTdsSettlement: boolean;
  ageingBuckets: { label: string; min: number; max: number | null }[];
}

export interface ReconciliationMatch {
  id: string;
  transaction: BankTransaction;
  matchedInvoice: Invoice;
  bankTransaction: BankTransaction;
  invoice: Invoice;
  confidenceScore: number;
  confidenceLevel: MatchConfidenceLevel;
  ruleApplied: MatchRuleType;
  allocatedAmount: number;
  tdsDeducted: number;
  tdsAdjustment: number;
  shortPaymentAmount: number;
  differenceAmount: number;
  differenceReason?: string;
  excessPaymentAmount: number;
  shortPaymentReason?: 'TDS' | 'Discount' | 'Bank charges' | 'Deduction' | 'Dispute' | 'Other';
  excessHandling?: 'Advance' | 'Adjustment against future invoice' | 'Refund' | 'Other';
  explanation: string;
  remarks?: string;
}

export type MatchSuggestion = ReconciliationMatch;
