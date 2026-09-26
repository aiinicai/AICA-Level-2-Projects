export type UserRole = 'CFO' | 'ACCOUNTANT' | 'AUDITOR' | 'SALES_PROCUREMENT';

export type AccountCategory = 'ASSET' | 'LIABILITY' | 'EQUITY' | 'INCOME' | 'EXPENSE';

export interface Account {
  id?: string;
  code: string;
  name: string;
  scheduleIIIGroup: string;
  subGroup: string;
  category: AccountCategory;
  normalBalance: 'DEBIT' | 'CREDIT';
  balance: number;
}

export interface JournalLine {
  id: string;
  accountId?: string;
  accountCode: string;
  accountName: string;
  debit: number;
  credit: number;
  partyName?: string;
  costCenter?: string;
}

export interface JournalEntry {
  id: string;
  entryNumber?: string;
  date: string;
  referenceDocType?: 'SALES_INVOICE' | 'VENDOR_BILL' | 'PAYROLL_ACCRUAL' | 'PAYROLL_PAYMENT' | 'STOCK_ADJUSTMENT' | 'MANUAL_JOURNAL' | 'REVERSAL';
  sourceDocumentType?: string;
  sourceDocumentId?: string;
  referenceDocId?: string;
  referenceDocNumber?: string;
  referenceDocUrl?: string;
  narration: string;
  lines: JournalLine[];
  isPosted?: boolean;
  isReversed?: boolean;
  reversingEntryId?: string;
  reversedEntryNumber?: string;
  createdBy?: string;
  approvedBy?: string;
  confidenceScore?: number;
  status: 'POSTED' | 'PENDING_REVIEW' | 'REVERSED';
  createdAt?: string;
  totalDebit?: number;
  totalCredit?: number;
  postedBy?: string;
  postedAt?: string;
}

export interface InvoiceItem {
  id: string;
  skuId?: string;
  skuCode?: string;
  description: string;
  hsnSac: string;
  quantity: number;
  unit?: string;
  rate: number;
  amount: number;
  gstRate: number; // e.g. 18
  cgst: number;
  sgst: number;
  igst: number;
  costPrice?: number; // Unit inventory cost for COGS recognition
  isItcEligible?: boolean;
}

export interface SalesInvoice {
  id: string;
  invoiceNumber: string;
  date: string;
  dueDate: string;
  customerId: string;
  customerName: string;
  customerGstin: string;
  branchGstin: string;
  branchName: string;
  items: InvoiceItem[];
  taxableAmount: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
  totalCogs: number;
  status: 'PAID' | 'UNPAID' | 'PARTIALLY_PAID' | 'REVIEW_QUEUE';
  paymentReceived: number;
  irnNumber?: string;
  ewayBillNumber?: string;
  confidenceScore: number;
  confidenceReasons?: string[];
  documentUrl?: string;
  isDisputed: boolean;
  isConsideredDoubtful: boolean;
  journalEntryId?: string;
  notes?: string;
}

export interface VendorBill {
  id: string;
  billNumber: string;
  date: string;
  dueDate: string;
  vendorId: string;
  vendorName: string;
  vendorGstin: string;
  branchGstin: string;
  branchName?: string;
  category: 'RAW_MATERIALS' | 'FREIGHT' | 'RENT' | 'PROFESSIONAL_FEES' | 'UTILITIES' | 'CAPITAL_GOODS' | 'INVENTORY_PURCHASE' | 'EXPENSE';
  items: InvoiceItem[];
  taxableAmount: number;
  cgst: number;
  sgst: number;
  igst: number;
  totalAmount: number;
  tdsApplicable?: boolean;
  tdsSection?: '194C' | '194J' | '194I' | '194Q' | 'NONE';
  tdsRate?: number;
  tdsAmount?: number;
  tdsDeducted?: number;
  netPayable: number;
  itcEligible?: boolean; // Section 17(5) blocked credit flag
  status: 'PAID' | 'UNPAID' | 'REVIEW_QUEUE';
  paymentMade: number;
  poNumber?: string;
  poReference?: string;
  grnNumber?: string;
  grnReference?: string;
  threeWayMatchStatus?: 'MATCHED' | 'DISCREPANCY' | 'NOT_APPLICABLE';
  confidenceScore: number;
  confidenceReasons?: string[];
  documentUrl?: string;
  isMsme: boolean;
  msmeType?: 'MICRO' | 'SMALL' | 'MEDIUM';
  isDisputed: boolean;
  journalEntryId?: string;
}

export type AuditLogEntry = AuditLogItem & {
  performedBy?: string;
  documentReference?: string;
  hash?: string;
};

export type BankTransaction = BankStatementLine & {
  matchedDocumentId?: string;
};

export type PayrollRun = PayrollBatch & {
  headcount?: number;
  journalEntryId?: string;
  netPayable?: number;
};

export interface StockItem {
  id: string;
  sku: string;
  name: string;
  category: string;
  hsnSac: string;
  gstRate: number;
  uom: string;
  costingMethod: 'FIFO' | 'WEIGHTED_AVG';
  currentStock: number;
  weightedAvgCost: number;
  nrvUnit: number; // Net Realisable Value
  reorderLevel: number;
  lastSaleDate: string;
  daysSinceLastSale: number;
  status: 'ACTIVE' | 'SLOW_MOVING' | 'DEAD_STOCK';
  locationStocks: Record<string, number>;
}

export interface StockTransaction {
  id: string;
  date: string;
  skuId: string;
  skuCode: string;
  skuName: string;
  type: 'IN_PURCHASE' | 'OUT_SALE' | 'TRANSFER' | 'ADJUSTMENT';
  quantity: number;
  unitCost: number;
  totalValue: number;
  referenceDoc: string;
  location: string;
  narration?: string;
}

export interface Customer {
  id: string;
  name: string;
  gstin: string;
  stateCode: string;
  stateName: string;
  creditLimit: number;
  creditPeriodDays: number;
  currentOutstanding: number;
  disputedAmount: number;
  doubtfulAmount: number;
  email: string;
  phone: string;
  city: string;
}

export interface Vendor {
  id: string;
  name: string;
  gstin: string;
  stateCode: string;
  stateName: string;
  paymentTermsDays: number;
  isMsme: boolean;
  msmeType?: 'MICRO' | 'SMALL' | 'MEDIUM';
  tdsSection: '194C' | '194J' | '194I' | '194Q' | 'NONE';
  tdsRate: number;
  currentOutstanding: number;
  disputedAmount: number;
  email: string;
  phone: string;
  city: string;
}

export interface PayrollBatch {
  id: string;
  monthYear: string;
  periodStart: string;
  periodEnd: string;
  departmentCount: number;
  employeeCount: number;
  grossSalary: number;
  pfDeduction: number;
  esiDeduction: number;
  ptDeduction: number;
  tdsDeduction: number;
  netSalaryPayable: number;
  accrualPosted: boolean;
  accrualEntryId?: string;
  accrualDate?: string;
  paymentPosted: boolean;
  paymentEntryId?: string;
  paymentDate?: string;
  bankRefMatched?: string;
}

export interface BankStatementLine {
  id: string;
  date: string;
  description: string;
  type: 'DEBIT' | 'CREDIT';
  amount: number;
  referenceNumber: string;
  matched: boolean;
  matchedDocType?: 'PAYROLL' | 'VENDOR_BILL' | 'CUSTOMER_PAYMENT';
  matchedDocId?: string;
  matchedDocNumber?: string;
}

export interface AuditLogItem {
  id: string;
  timestamp: string;
  userId?: string;
  userName?: string;
  role: UserRole;
  action: 'AUTO_POST' | 'MANUAL_POST' | 'REVERSE' | 'APPROVE' | 'REJECT' | 'UPDATE_SETTINGS' | string;
  entityType?: 'JOURNAL' | 'INVOICE' | 'BILL' | 'PAYROLL' | 'STOCK' | 'POLICY' | string;
  entityId?: string;
  entityNumber?: string;
  documentRef?: string;
  details: string;
  beforeState?: string;
  afterState?: string;
}

export interface SystemSettings {
  companyName: string;
  cin: string;
  pan: string;
  multiGstinList: {
    gstin: string;
    stateCode: string;
    stateName: string;
    branchName: string;
    isPrimary: boolean;
  }[];
  activeGstin: string;
  costingMethod: 'FIFO' | 'WEIGHTED_AVG';
  ocrAutoPostThreshold: number; // e.g. 90
  makerCheckerLimit: number; // INR e.g. 5,00,000
  inventoryProvisionPolicy: {
    slowMovingMonths: number; // default 3 (90 days)
    deadStockMonths: number; // default 6 (180 days)
    provision6To12MonthsPct: number; // e.g. 25% write-down
    provisionAbove12MonthsPct: number; // e.g. 60% write-down
  };
  gspConnected: boolean;
  accountAggregatorConnected: boolean;
  eInvoiceConnected: boolean;
}

export interface ScheduleIIIDebtorAgeingRow {
  category: 'Undisputed - Considered Good' | 'Undisputed - Considered Doubtful' | 'Disputed - Considered Good' | 'Disputed - Considered Doubtful';
  notDue: number;
  lessThan6Months: number;
  sixMonthsToOneYear: number;
  oneToTwoYears: number;
  twoToThreeYears: number;
  moreThanThreeYears: number;
  total: number;
}

export interface ScheduleIIICreditorAgeingRow {
  category: 'MSME - Undisputed' | 'MSME - Disputed' | 'Others - Undisputed' | 'Others - Disputed';
  notDue: number;
  lessThanOneYear: number;
  oneToTwoYears: number;
  twoToThreeYears: number;
  moreThanThreeYears: number;
  total: number;
}
