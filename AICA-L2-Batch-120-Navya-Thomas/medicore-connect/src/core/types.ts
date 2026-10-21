/**
 * MediCore Connect - Data Model & Type Definitions
 * Meridian Healthcare Group (5 Hospitals, 5 Clinics, 5 Pharmacies)
 */

export type TransactionStatus =
  | 'Draft'
  | 'Pending Approval'
  | 'Pending Higher Approval'
  | 'Approved'
  | 'Approved - Accounting Error'
  | 'Posted'
  | 'Rejected'
  | 'Cancelled'
  | 'Reversed';

export type UserRole =
  | 'Finance Controller'
  | 'CFO'
  | 'AP Maker'
  | 'AR Maker'
  | 'Procurement Maker / Buyer'
  | 'Store Controller'
  | 'Treasury Maker'
  | 'Fixed Asset Accountant'
  | 'Intercompany Accountant';

export type ERPModule =
  | 'Procurement'
  | 'Supply Chain Execution'
  | 'Payables'
  | 'Receivables'
  | 'Fixed Assets'
  | 'Cash Management'
  | 'Intercompany Accounting'
  | 'General Accounting'
  | 'Period Close'
  | 'Access and Roles'
  | 'Reports'
  | 'Tools';

export interface ModuleAccessConfig {
  module: ERPModule;
  makerUserId: string;
  makerName: string;
  approverUserId: string;
  approverName: string;
  approvalLimitAED: number | null; // null = Unlimited
  description?: string;
}

export interface User {
  userId: string;
  name: string;
  role: UserRole;
  password?: string;
  approvalLimitAED: number | null; // null = Unlimited
  department?: string;
}

export type BusinessUnitType = 'Hospital' | 'Clinic' | 'Pharmacy';

export interface BusinessUnit {
  code: string; // e.g. H01, C01, P01
  name: string;
  type: BusinessUnitType;
  emirate: string; // Abu Dhabi, Dubai, Sharjah, Ras Al Khaimah, etc.
  vatTrn: string;
  status: 'Active' | 'Inactive';
}

export type AccountType = 'Asset' | 'Liability' | 'Equity' | 'Revenue' | 'Expense' | 'Contra';

export interface Account {
  code: string; // e.g. "1000", "2000"
  name: string;
  type: AccountType;
  normalBalance: 'Debit' | 'Credit';
  ifrsLine: string;
  isNonCurrent?: boolean;
  isControlAccount?: boolean; // blocked for manual journals
  manualJournalAllowed?: boolean;
  subledgerSource?: 'Payables' | 'Receivables' | 'Inventory' | 'Fixed Assets' | 'Cash' | 'Intercompany' | 'None';
  isActive: boolean;
  pendingApproval?: boolean;
  pendingChanges?: Partial<Account>;
  createdBy?: string;
  approvedBy?: string;
}

export type PeriodStatus = 'Closed' | 'Open' | 'Future';

export interface FiscalPeriod {
  name: string; // e.g. "Jan-26", "Oct-26"
  year: number; // 2026
  month: number; // 1-12
  startDate: string; // YYYY-MM-DD
  endDate: string; // YYYY-MM-DD
  status: PeriodStatus;
}

export type TaxCode = 'STANDARD_5' | 'ZERO_0' | 'EXEMPT' | 'OUT_OF_SCOPE';

export interface TaxCodeConfig {
  code: TaxCode;
  name: string;
  rate: number; // 0.05, 0, etc.
  description: string;
}

export type DocumentPrefix =
  | 'REQ'
  | 'PO'
  | 'RCV'
  | 'PINV'
  | 'PCM'
  | 'PAY'
  | 'RINV'
  | 'RCM'
  | 'RCT'
  | 'PCV'
  | 'MCV'
  | 'CTR'
  | 'BST'
  | 'FAB'
  | 'ICI'
  | 'ICC'
  | 'ICJ'
  | 'JV'
  | 'STO'
  | 'ADJ'
  | 'CNS';

export interface SequenceRecord {
  prefix: DocumentPrefix;
  year: number;
  currentValue: number;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  entityType: string;
  entityId: string;
  action: 'CREATE' | 'UPDATE' | 'SUBMIT' | 'APPROVE' | 'REJECT' | 'POST' | 'REVERSE' | 'CANCEL';
  userId: string;
  userName: string;
  comments?: string;
  details?: Record<string, any>;
}

export interface Notification {
  id: string;
  title: string;
  message: string;
  type: 'approval' | 'rejection' | 'alert' | 'system';
  targetUserId?: string; // or all approvers
  targetRole?: UserRole;
  linkUrl?: string;
  read: boolean;
  timestamp: string;
}

// Master Entities
export interface Supplier {
  id: string;
  code: string;
  name: string;
  trn: string;
  paymentTerms: string; // e.g. "Net 30", "Immediate"
  bankName: string;
  bankIban: string;
  category: 'Pharmaceuticals' | 'Medical Equipment' | 'Consumables' | 'Facility Services' | 'Utilities' | 'IT & Telecom' | 'Professional Services';
  sites: string[];
  poNotRequired?: boolean; // utilities, rent, etc.
  status: 'Active' | 'Inactive';
}

export interface Customer {
  id: string;
  code: string;
  name: string;
  type: 'Insurance' | 'Corporate' | 'Patient' | 'Government';
  trn?: string;
  paymentTerms: string;
  creditLimitAED: number;
  currentBalanceAED: number;
  status: 'Active' | 'Inactive';
}

export type ItemClass =
  | 'Pharmaceutical'
  | 'Consumable'
  | 'Implants & Surgical'
  | 'General'
  | 'Service'
  | 'Capital Asset';

export interface Item {
  code: string;
  description: string;
  itemClass: ItemClass;
  uom: string; // Box, Each, Vial, Pack, Session
  unitPrice: number;
  weightedAvgCost: number;
  reorderLevel: number;
  expiryTracked: boolean;
  status: 'Active' | 'Inactive';
}

// Supply Chain & Procurement
export interface RequisitionLine {
  lineNumber: number;
  itemCode?: string;
  description: string;
  itemClass?: ItemClass;
  uom?: string;
  quantity: number;
  estimatedUnitPrice?: number;
  estimatedCost?: number;
  estimatedAmount?: number;
  suggestedSupplierId?: string;
  suggestedSupplierName?: string;
  chargeAccount?: string;
  department: string;
  isCapital: boolean;
  assetCategory?: string;
  needByDate?: string;
  convertedQuantity?: number;
}

export interface Requisition {
  id: string;
  number: string; // REQ-2026-000001
  businessUnit: string;
  date?: string; // ISO date
  requisitionDate?: string;
  needByDate?: string;
  requesterId?: string;
  requesterName?: string;
  department: string;
  requisitionType?: 'Goods' | 'Services' | 'Capital Asset';
  deliveryLocation?: string;
  priority?: 'Normal' | 'Urgent';
  justification?: string;
  description: string;
  status: TransactionStatus | 'Partially Converted' | 'Converted to PO';
  lines: RequisitionLine[];
  subtotal?: number;
  taxAmount?: number;
  totalAmount: number;
  attachments?: string[];
  createdBy: string;
  createdAt: string;
  submittedAt?: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  relatedPoNumbers?: string[];
}

export interface POLine {
  lineNumber: number;
  itemCode?: string;
  description: string;
  itemClass?: ItemClass;
  uom?: string;
  quantity: number;
  receivedQuantity: number;
  invoicedQuantity: number;
  unitPrice: number;
  lineAmount: number;
  taxCode: TaxCode;
  account: string;
  department: string;
  isCapital: boolean;
  assetCategory?: string;
  needByDate?: string;
  sourceRequisitionNumber?: string;
  sourceRequisitionLineNumber?: number;
}

export interface PurchaseOrder {
  id: string;
  number: string; // PO-2026-000001
  requisitionNumber?: string;
  businessUnit: string;
  supplierId: string;
  supplierName: string;
  supplierSite?: string;
  buyerId?: string;
  buyerName?: string;
  date?: string;
  poDate?: string;
  orderType?: 'Goods' | 'Services' | 'Capital';
  currency: string;
  paymentTerms: string;
  deliveryLocation?: string;
  requiredDate?: string;
  receiptMatching?: 'Yes' | 'Optional' | 'No';
  notes?: string;
  attachments?: string[];
  status: TransactionStatus | 'Partially Received' | 'Received' | 'Partially Invoiced' | 'Invoiced' | 'Closed';
  lines: POLine[];
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  createdBy: string;
  createdAt: string;
  submittedAt?: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  sourceRequisitionNumbers?: string[];
}

export interface ReceiptLine {
  lineNumber: number;
  poNumber: string;
  poLineNumber: number;
  itemCode: string;
  description: string;
  orderedQuantity?: number;
  receivedToDate?: number;
  quantityReceived: number;
  unitPrice: number;
  lineAmount: number;
  account: string; // inventory account or expense
  lotNumber?: string;
  expiryDate?: string;
  subInventory?: string;
}

export interface Receipt {
  id: string;
  number: string; // RCV-2026-000001
  poNumber: string;
  poId?: string;
  businessUnit: string;
  supplierId: string;
  supplierName: string;
  receiptDate: string;
  deliveryNoteNumber?: string;
  notes?: string;
  status: TransactionStatus;
  lines: ReceiptLine[];
  totalAmount: number;
  createdBy: string;
  createdAt: string;
  submittedAt?: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  subledgerEntryId?: string;
  glJournalId?: string;
  glJournalNumber?: string;
}

export interface InventoryBalance {
  businessUnit: string;
  subInventory: 'Main Store' | 'Pharmacy' | 'OT / Ward';
  itemCode: string;
  quantityOnHand: number;
  weightedAvgCost: number;
  batchNumber?: string;
  expiryDate?: string;
}

// Payables
export interface APInvoiceLine {
  lineNumber: number;
  poNumber?: string;
  poLineNumber?: number;
  itemCode?: string;
  description: string;
  quantity: number;
  unitPrice: number;
  lineAmount: number;
  taxCode: TaxCode;
  taxAmount: number;
  distributionAccount: string;
  department: string;
  isCapital?: boolean;
  assetCategory?: string;
}

export interface InvoiceHold {
  type: string;
  reason: string;
  datePlaced: string;
  released: boolean;
}

export interface APInvoice {
  id: string;
  number: string; // PINV-2026-000001
  businessUnit: string;
  invoiceType: 'Standard' | 'Credit Memo' | 'Prepayment';
  supplierId: string;
  supplierName: string;
  supplierSite: string;
  supplierInvoiceNumber: string;
  invoiceDate: string;
  glDate: string;
  dueDate: string;
  currency: string;
  description: string;
  lines: APInvoiceLine[];
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  paidAmount: number;
  status: TransactionStatus;
  holds: InvoiceHold[];
  createdBy: string;
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  postedAt?: string;
  glJournalId?: string;
}

export interface APPaymentApplication {
  invoiceId: string;
  invoiceNumber: string;
  amountApplied: number;
}

export interface APPayment {
  id: string;
  number: string; // PAY-2026-000001
  businessUnit: string;
  supplierId: string;
  supplierName: string;
  paymentDate: string;
  bankAccountCode: string; // 1020
  amount: number;
  paymentMethod: 'Bank Transfer' | 'Cheque' | 'Direct Debit';
  referenceNumber: string;
  applications: APPaymentApplication[];
  status: TransactionStatus;
  createdBy: string;
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  glJournalId?: string;
}

// Receivables
export interface ARTransactionLine {
  lineNumber: number;
  serviceCategory: string; // e.g. Inpatient, Outpatient, Lab, Surgery, Pharmacy
  description: string;
  revenueAccount: string; // 4000-4060
  amount: number;
  taxCode: TaxCode;
  taxAmount: number;
  insuranceDiscountAmount: number;
  patientCoPayAmount: number;
}

export interface ARTransaction {
  id: string;
  number: string; // RINV-2026-000001
  businessUnit: string;
  transactionClass: 'Invoice' | 'Credit Memo';
  customerId: string;
  customerName: string;
  customerType: 'Insurance' | 'Corporate' | 'Patient' | 'Government';
  patientName?: string;
  patientId?: string;
  claimReference?: string;
  visitDate: string;
  transactionDate: string;
  glDate: string;
  dueDate: string;
  description: string;
  lines: ARTransactionLine[];
  subtotal: number;
  discountAmount: number;
  taxAmount: number;
  totalAmount: number; // net receivable
  paidAmount: number;
  status: TransactionStatus;
  createdBy: string;
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  postedAt?: string;
  glJournalId?: string;
}

export interface ARReceiptApplication {
  transactionId: string;
  transactionNumber: string;
  amountApplied: number;
}

export interface ARReceipt {
  id: string;
  number: string; // RCT-2026-000001
  businessUnit: string;
  customerId: string;
  customerName: string;
  receiptDate: string;
  glDate: string;
  receiptMethod: 'Bank Transfer' | 'Credit Card' | 'Cash';
  bankAccountCode: string; // 1030 or 1000
  amount: number;
  unappliedAmount: number;
  referenceNumber: string;
  applications: ARReceiptApplication[];
  status: TransactionStatus;
  createdBy: string;
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  glJournalId?: string;
}

// Fixed Assets
export interface AssetCategory {
  id: string;
  name: string;
  costAccount: string; // 1710-1770
  accumDepAccount: string; // 1810-1870
  depExpenseAccount: string; // 6300
  usefulLifeYears: number;
  depMethod: 'Straight Line';
  residualValuePercentage: number;
}

export interface AssetSourceLine {
  id: string;
  apInvoiceId: string;
  apInvoiceNumber: string;
  lineNumber: number;
  poNumber?: string;
  businessUnit: string;
  description: string;
  cost: number;
  invoiceDate: string;
  inServiceDate: string;
  categoryName?: string;
  units: number;
  department: string;
  status: 'Incomplete' | 'Exception' | 'Ready to Post' | 'Capitalized';
  exceptionReason?: string;
  tagNumber?: string;
  comments?: string;
}

export interface FixedAsset {
  id: string;
  tagNumber: string; // FA-000001
  name: string;
  businessUnit: string;
  department: string;
  category: string;
  costAccount: string;
  accumDepAccount: string;
  cost: number;
  salvageValue: number;
  usefulLifeYears: number;
  inServiceDate: string;
  accumulatedDepreciation: number;
  netBookValue: number;
  status: 'Active' | 'Disposed' | 'Transferred';
  sourceInvoiceNumber?: string;
  lastDepreciationPeriod?: string;
}

export interface DepreciationRunLine {
  assetId: string;
  assetTag: string;
  assetName: string;
  businessUnit: string;
  category: string;
  depreciationAmount: number;
  accumDepAccount: string;
  depExpenseAccount: string;
}

export interface DepreciationRun {
  id: string;
  period: string; // e.g. "Oct-26"
  runDate: string;
  businessUnit: string; // 'All' or specific BU
  totalDepreciation: number;
  lines: DepreciationRunLine[];
  status: TransactionStatus;
  glJournalId?: string;
  createdBy: string;
  approvedBy?: string;
}

// Cash Management
export interface PettyCashFund {
  id: string;
  businessUnit: string;
  custodian: string;
  imprestLimit: number;
  currentBalance: number;
  account: string; // 1010
}

export interface CashVoucher {
  id: string;
  number: string; // PCV-2026-000001 or MCV-2026-000001
  type: 'PettyCash' | 'MainCash';
  businessUnit: string;
  date: string;
  payee: string;
  expenseCategory: string;
  expenseAccount: string; // 6200, 6230, etc.
  department: string;
  description: string;
  amount: number;
  taxCode: TaxCode;
  taxAmount: number;
  receiptAttached: boolean;
  status: TransactionStatus;
  createdBy: string;
  createdAt: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  glJournalId?: string;
}

export interface BankAccount {
  accountCode: string; // 1020, 1030
  name: string;
  bankName: string;
  accountNumber: string;
  iban: string;
  businessUnit: string;
  currency: string;
  currentBalance: number;
}

export interface BankStatementLine {
  id: string;
  statementNumber: string;
  lineDate: string;
  type: 'Credit' | 'Debit';
  amount: number;
  reference: string;
  description: string;
  isReconciled: boolean;
  matchedTransactionType?: 'AP_PAYMENT' | 'AR_RECEIPT' | 'CASH_DEPOSIT' | 'BANK_CHARGE';
  matchedTransactionNumber?: string;
}

export interface BankStatement {
  id: string;
  number: string; // BST-2026-000001
  bankAccountCode: string;
  businessUnit: string;
  statementDate: string;
  openingBalance: number;
  closingBalance: number;
  lines: BankStatementLine[];
  status: 'Reconciled' | 'Partially Reconciled' | 'Unreconciled';
}

// Intercompany Accounting
export interface ICTransactionLine {
  lineNumber: number;
  description: string;
  amount: number;
  providerAccount: string; // 4900, 1200, etc.
  receiverAccount: string; // expense, inventory, asset
}

export interface ICTransaction {
  id: string;
  number: string; // ICI-2026-000001, ICC-2026-000001, ICJ-2026-000001
  type: 'Invoice' | 'Credit Note' | 'Journal';
  providerBU: string;
  receiverBU: string;
  date: string;
  description: string;
  originalTxnNumber?: string;
  lines: ICTransactionLine[];
  totalAmount: number;
  status: TransactionStatus; // Pending Acceptance, Approved, Posted
  createdBy: string;
  createdAt: string;
  receiverAcceptedBy?: string;
  approvedBy?: string;
  approvedAt?: string;
  glJournalId?: string;
}

// General Ledger & Accounting Engine
export interface GLJournalLine {
  lineNumber: number;
  businessUnit: string;
  account: string;
  department?: string;
  debit: number;
  credit: number;
  description: string;
  sourceModule: string;
  sourceDocumentNumber: string;
  sourceDocumentId?: string;
}

export interface GLJournal {
  id: string;
  number: string; // JV-2026-000001
  period: string; // "Oct-26"
  journalDate: string;
  businessUnit: string; // Or "Multi-BU"
  sourceModule:
    | 'Payables'
    | 'Receivables'
    | 'Fixed Assets'
    | 'Cash Management'
    | 'Procurement/Inventory'
    | 'Intercompany'
    | 'Manual'
    | 'Depreciation'
    | 'Opening Balances';
  category: string; // Accrual, Purchase, Payment, Sales, Capitalisation, etc.
  description: string;
  status: TransactionStatus;
  totalDebit: number;
  totalCredit: number;
  lines: GLJournalLine[];
  isReversing?: boolean;
  reversalDate?: string;
  reversedJournalId?: string;
  createdBy: string;
  createdAt: string;
  submittedAt?: string;
  approvedBy?: string;
  approvedAt?: string;
  rejectionReason?: string;
  postedAt?: string;
}

export interface SubledgerLine {
  businessUnit: string;
  account: string;
  department?: string;
  debit: number;
  credit: number;
  description: string;
}

export interface SubledgerEntry {
  sourceModule: GLJournal['sourceModule'];
  sourceDocumentId: string;
  sourceDocumentNumber: string;
  businessUnit: string;
  date: string;
  description: string;
  lines: SubledgerLine[];
}

export interface SystemIntegrityResult {
  checkId: number;
  title: string;
  description: string;
  status: 'PASS' | 'FAIL';
  details: string;
  offendingRecords?: any[];
}
