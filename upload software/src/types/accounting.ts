export type EntityType = 
  | 'Proprietorship'
  | 'Partnership Firm'
  | 'Limited Liability Partnership (LLP)'
  | 'Hindu Undivided Family (HUF)'
  | 'Trust / Society'
  | 'Association of Persons (AOP / BOI)';

export interface EntityDetails {
  id: string;
  name: string;
  entityType: EntityType;
  pan: string;
  gstin: string;
  address: string;
  financialYear: string; // e.g. "2024-2025"
  balanceSheetDate: string; // e.g. "31st March 2025"
  previousYearDate?: string; // e.g. "31st March 2024"
  currencySymbol: string; // e.g. "₹"
  currencyFormat: 'INR' | 'INTERNATIONAL';
  auditorName?: string;
  membershipNumber?: string;
  firmRegistrationNo?: string;
  udin?: string;
  placeOfSigning?: string;
  dateOfSigning?: string;
  proprietorOrPartnerNames?: string[];
}

export type HeadNature = 'Liability' | 'Asset';
export type MainHeadType = 'Capital & Liabilities' | 'Assets';

export type ICAIMajorCategory = 
  | 'OWNERS_FUNDS'
  | 'NON_CURRENT_LIABILITIES'
  | 'CURRENT_LIABILITIES'
  | 'NON_CURRENT_ASSETS'
  | 'CURRENT_ASSETS';

export interface BalanceSheetHeadConfig {
  id: string;
  code: string; // e.g. "L01", "L02", "A01"
  mainHead: MainHeadType;
  subHead: string; // e.g. "Capital Account", "Secured Loans"
  scheduleNo: number | string; // e.g. 1, 2, "3A"
  scheduleTitle: string; // e.g. "Schedule 1 - Capital Account"
  nature: HeadNature;
  icaiMajorCategory?: ICAIMajorCategory;
  displayOrder: number;
  active: boolean;
  isSpecialSchedule?: 'CAPITAL' | 'FIXED_ASSETS' | 'INVESTMENTS' | 'TRADE_RECEIVABLES' | 'TRADE_PAYABLES' | 'CASH_BANK' | 'INVENTORIES' | 'STANDARD';
  description?: string;
}

export type ClassificationTarget = 
  | 'BALANCE_SHEET'
  | 'PROFIT_AND_LOSS'
  | 'TRADING'
  | 'UNCLASSIFIED';

export type TargetStatementType = ClassificationTarget;


export type PLCategory = 
  | 'DIRECT_INCOME'
  | 'INDIRECT_INCOME'
  | 'DIRECT_EXPENSE'
  | 'INDIRECT_EXPENSE'
  | 'NONE';

export type ClassificationStatus = 'CONFIRMED' | 'AUTO_SUGGESTED' | 'REVIEW_NEEDED';
export type ConfidenceLevel = 'HIGH' | 'MEDIUM' | 'LOW';

export interface LedgerItem {
  id: string;
  ledgerCode?: string;
  ledgerName: string;
  originalGroup: string;
  debit: number;
  credit: number;
  netBalance: number; // positive = Debit balance, negative = Credit balance
  natureDrCr: 'Dr' | 'Cr';
  previousYearAmount?: number;
  previousYearDebit?: number;
  previousYearCredit?: number;
  
  // Classification
  targetType: ClassificationTarget;
  headCode?: string; // Links to BalanceSheetHeadConfig.code
  mainHead?: string;
  subHead?: string;
  scheduleNo?: number | string;
  plCategory?: PLCategory;
  
  status: ClassificationStatus;
  confidence: ConfidenceLevel;
  confidenceReason?: string;
  userNotes?: string;
  isUserModified?: boolean;
  hasSavedRule?: boolean;
  savedRuleNature?: string;
}

export interface SavedClassificationRule {
  id: string;
  ledgerName: string;
  normalizedName: string;
  originalGroup?: string;
  targetType: ClassificationTarget;
  headCode?: string;
  subHead?: string;
  scheduleNo?: number | string;
  headNature?: HeadNature; // 'Liability' | 'Asset'
  plCategory?: PLCategory;
  classificationNature: string; // e.g. "Liability - Sch 1 (Capital Account)" or "P&L Indirect Expense"
  savedAt: string;
  updatedAt: string;
  notes?: string;
}

export interface FixedAssetDetail {
  id: string;
  assetName: string;
  openingGrossBlock: number;
  additionsMoreThan180Days: number;
  additionsLessThan180Days: number;
  deductionsGrossBlock: number;
  closingGrossBlock: number;
  openingDepreciation: number;
  currentYearDepreciation: number;
  depreciationOnDeletions: number;
  closingDepreciation: number;
  netBlock: number;
  previousYearNetBlock?: number;
}

export interface PartnerCapitalDetail {
  id: string;
  partnerName: string;
  openingBalance: number;
  additionalCapital: number;
  shareOfProfit: number;
  interestOnCapital: number;
  partnerSalaryOrRemuneration: number;
  drawings: number;
  interestOnDrawings: number;
  closingBalance: number;
}

export interface ManualAdjustment {
  id: string;
  date?: string;
  description: string;
  debitHead: string; // Head code or ledger
  creditHead: string; // Head code or ledger
  amount: number;
  type: 'CLOSING_STOCK' | 'DEPRECIATION' | 'PROVISION' | 'PARTNER_SALARY' | 'OTHER';
  notes?: string;
}

export interface PLStatement {
  directIncomes: { name: string; amount: number; ledgerId: string; previousYearAmount?: number }[];
  totalDirectIncome: number;
  previousYearTotalDirectIncome?: number;
  
  openingStock: number;
  previousYearOpeningStock?: number;
  directExpenses: { name: string; amount: number; ledgerId: string; previousYearAmount?: number }[];
  totalDirectExpenses: number;
  previousYearTotalDirectExpenses?: number;
  closingStock: number;
  previousYearClosingStock?: number;
  
  grossProfit: number;
  previousYearGrossProfit?: number;
  grossProfitPercentage: number;
  previousYearGrossProfitPercentage?: number;
  
  indirectIncomes: { name: string; amount: number; ledgerId: string; previousYearAmount?: number }[];
  totalIndirectIncome: number;
  previousYearTotalIndirectIncome?: number;
  
  indirectExpenses: { name: string; amount: number; ledgerId: string; previousYearAmount?: number }[];
  totalIndirectExpenses: number;
  previousYearTotalIndirectExpenses?: number;
  
  netProfitBeforeTax: number;
  previousYearNetProfitBeforeTax?: number;
  taxProvision: number;
  previousYearTaxProvision?: number;
  netProfitAfterTax: number; // To flow into Capital Account
  previousYearNetProfitAfterTax?: number;
}

export interface ScheduleData {
  headConfig: BalanceSheetHeadConfig;
  ledgers: LedgerItem[];
  totalAmount: number;
  previousYearTotal?: number;
  partnerDetails?: PartnerCapitalDetail[];
  fixedAssetDetails?: FixedAssetDetail[];
  subTotals?: { name: string; amount: number }[];
}

export interface BalanceSheetSummary {
  liabilitiesHeads: {
    headConfig: BalanceSheetHeadConfig;
    amount: number;
    previousYearAmount?: number;
    scheduleNo: number | string;
  }[];
  totalLiabilities: number;
  totalPreviousYearLiabilities?: number;
  
  assetsHeads: {
    headConfig: BalanceSheetHeadConfig;
    amount: number;
    previousYearAmount?: number;
    scheduleNo: number | string;
  }[];
  totalAssets: number;
  totalPreviousYearAssets?: number;
  
  difference: number;
  previousYearDifference?: number;
  isBalanced: boolean;
  isPreviousYearBalanced?: boolean;
}

export interface ReconciliationReport {
  totalTrialBalanceDebit: number;
  totalTrialBalanceCredit: number;
  trialBalanceDifference: number;
  isTrialBalanceBalanced: boolean;
  
  totalAssets: number;
  totalLiabilities: number;
  balanceSheetDifference: number;
  isBalanceSheetBalanced: boolean;
  
  unclassifiedLedgersCount: number;
  unclassifiedTotalAmount: number;
  
  plNetProfit: number;
  capitalProfitTransferred: number;
  plTransferDifference: number;
  
  negativeBalances: { ledgerName: string; amount: number; expected: string; actual: string }[];
  
  status: 'BALANCED' | 'DIFFERENCE_EXISTS' | 'UNCLASSIFIED_ITEMS' | 'CRITICAL_ERROR';
}

export interface DepreciationAssetItem {
  id: string;
  assetName: string;
  category?: string;
  grossBlock: number;
  depreciationRate: number; // e.g. 10, 15, 40 (%)
  accumulatedDepreciation: number; // Opening accumulated depreciation
  depreciationForTheYear: number; // Depreciation of current year
  closingValue: number; // Closing carrying amount / Net block
  previousYearClosing: number; // Closing of previous year
  notes?: string;
}

export type NoteCategory = 
  | 'POLICIES'
  | 'CAPITAL'
  | 'LOANS'
  | 'MSME'
  | 'RECEIVABLES_PAYABLES'
  | 'CONTINGENT'
  | 'RELATED_PARTY'
  | 'STATUTORY'
  | 'CUSTOM';

export interface NoteToAccountItem {
  id: string;
  noteNumber: number | string;
  title: string;
  category: NoteCategory;
  content: string;
  isActive: boolean;
  isStandard: boolean;
  lastModified?: string;
}

export type ActiveTab = 
  | 'overview'
  | 'control'
  | 'trial-balance'
  | 'classification'
  | 'depreciation'
  | 'profit-and-loss'
  | 'balance-sheet'
  | 'schedules'
  | 'notes'
  | 'reconciliation'
  | 'adjustments';

// =========================================================================
// USER AUTHENTICATION & ACCESS CONTROL TYPES
// =========================================================================
export type UserRole = 'ADMIN' | 'AUDITOR' | 'ACCOUNTANT' | 'VIEWER';
export type UserStatus = 'APPROVED' | 'PENDING' | 'SUSPENDED';

export interface AppUser {
  id: string; // unique user ID / username
  name: string; // full name
  email: string;
  role: UserRole;
  status: UserStatus;
  createdAt: string;
  approvedAt?: string;
  approvedBy?: string;
  lastLoginAt?: string;
}

export interface UserRegistrationInput {
  id: string; // User ID
  name: string;
  email: string;
  password: string;
  role?: UserRole;
}

// =========================================================================
// ENTITY DATA VAULT (SAVE & FETCH FOR REVIEW)
// =========================================================================
export interface SavedEntitySummary {
  id: string; // unique snapshot ID
  entityId: string;
  entityName: string;
  entityType: EntityType;
  financialYear: string;
  balanceSheetDate: string;
  savedAt: string;
  savedBy: string; // User ID
  versionTag?: string; // e.g. "Final Audit Signed", "Draft 1"
  totalAssets: number;
  totalLiabilities: number;
  netProfit: number;
  isBalanced: boolean;
  difference: number;
  ledgersCount: number;
}

export interface SavedEntityWorkspace {
  id: string; // unique snapshot ID
  entityId: string;
  entityName: string;
  entityType: EntityType;
  financialYear: string;
  balanceSheetDate: string;
  savedAt: string;
  savedBy: string; // User ID
  versionTag?: string;
  notes?: string;
  summary: {
    totalAssets: number;
    totalLiabilities: number;
    netProfit: number;
    isBalanced: boolean;
    difference: number;
    ledgersCount: number;
    adjustmentsCount: number;
    assetsCount: number;
  };
  data: {
    entity: EntityDetails;
    ledgers: LedgerItem[];
    headConfigs: BalanceSheetHeadConfig[];
    adjustments: ManualAdjustment[];
    depreciationAssets: DepreciationAssetItem[];
    notesToAccounts: NoteToAccountItem[];
  };
}
