export type AccountType = 'bank' | 'credit_card' | 'cash' | 'investment';

export interface Account {
  id: string;
  name: string;
  type: AccountType;
  bankName?: string;
  brokerName?: string; // e.g. "Sarwa", "Wio Invest", "Interactive Brokers", "Baraka", "eToro"
  accountNumberMasked: string; // e.g. "•••• 4289"
  balance: number; // For bank/cash: current balance in AED. For credit_card: outstanding balance (amount owed). For investment: current portfolio valuation.
  initialBalance?: number; // Starting/opening balance before transactions
  creditLimit?: number; // For credit cards
  dueDate?: string; // e.g. "28th of every month"
  color: string;
  // Investment Specific Fields
  totalInvested?: number; // Total cash principal deposited / parked into investments
  currentValuation?: number; // Current market valuation in AED
  unrealizedGainLoss?: number; // Unrealized gain or loss in AED (+/-)
  gainLossPercentage?: number; // % unrealized return (+/-)
  assetClass?: 'Stocks & ETFs' | 'Crypto' | 'Gold & Bullion' | 'Real Estate' | 'Mutual Funds' | 'Sukuk & Fixed Income' | 'General Portfolio';
}

export const UAE_INVESTMENT_PLATFORMS = [
  'Sarwa (Invest & Trade)',
  'Wio Invest',
  'Interactive Brokers (IBKR)',
  'Baraka (SCA Regulated)',
  'eToro UAE',
  'National Bonds Corporation',
  'Binance / Crypto Portfolio',
  'Physical Gold / Bullion',
  'Stake (Real Estate Crowdfunding)',
  'SmartCrowd (Real Estate)',
  'Emirates NBD Securities',
  'ADCB Securities',
  'FAB Securities',
  'Other Broker / Investment'
] as const;

export const UAE_BANKS_LIST = [
  'Emirates NBD',
  'Abu Dhabi Commercial Bank (ADCB)',
  'Dubai Islamic Bank (DIB)',
  'First Abu Dhabi Bank (FAB)',
  'Mashreq (Salary & Savings / Neo)',
  'Citi (Citibank UAE)',
  'Abu Dhabi Islamic Bank (ADIB)',
  'Commercial Bank of Dubai (CBD)',
  'RAKBANK',
  'HSBC UAE',
  'Standard Chartered UAE',
  'Wio Bank',
  'Liv. by ENBD',
  'Sharjah Islamic Bank (SIB)',
  'Al Hilal Bank',
  'Ajman Bank',
  'Al Maryah Community Bank (Mbank)',
  'National Bank of Fujairah (NBF)',
  'National Bank of Umm Al Qaiwain (NBQ)',
  'Commercial Bank International (CBI)',
  'United Arab Bank (UAB)',
  'Bank of Sharjah',
  'Habib Bank AG Zurich',
  'Ruya Islamic Bank',
  'Zand Digital Bank',
  'Other Bank'
] as const;

export type StandardExpenseCategory =
  | 'Rent & Housing'
  | 'Food'
  | 'Groceries'
  | 'Food & Groceries'
  | 'Clothing'
  | 'Petrol'
  | 'Fuel'
  | 'Utilities'
  | 'Telecom'
  | 'Shopping'
  | 'Transport'
  | 'Healthcare'
  | 'Entertainment'
  | 'Travel'
  | 'Education'
  | 'Salary'
  | 'Other';

export type ExpenseCategory = StandardExpenseCategory | string;

export interface CategoryBudget {
  category: ExpenseCategory;
  monthlyLimit: number; // in AED
  icon: string;
  color: string;
  isCustom?: boolean;
}

export type TransactionType = 'expense' | 'income' | 'transfer' | 'card_payment' | 'investment_deposit' | 'investment_withdrawal';

export interface ReceiptItem {
  id: string;
  name: string;
  amount: number; // in AED
  category: ExpenseCategory;
  quantity?: number;
}

export interface CategorySplit {
  category: ExpenseCategory;
  amount: number; // in AED
}

export interface Transaction {
  id: string;
  amount: number; // in AED (net total transaction)
  originalAmount?: number; // original foreign amount if applicable
  originalCurrency?: string; // e.g. "USD", "EUR", "AED"
  exchangeRate?: number; // exchange rate used to convert to AED (e.g. 3.6725 for USD)
  currency: string; // "AED"
  merchant: string;
  category: ExpenseCategory;
  date: string; // ISO date string
  time?: string;
  accountId: string;
  toAccountId?: string; // For transfers / card payments
  type: TransactionType;
  source: 'auto_notification' | 'manual' | 'sms_import' | 'statement_import';
  bankName?: string;
  rawNotificationText?: string;
  isRedFlag: boolean;
  redFlagReason?: string; // e.g., "Foreign Currency (USD)", "High Amount (>1500 AED)"
  isVerifiedByUser: boolean;
  notes?: string;
  receiptImage?: string; // base64 encoded photo receipt or invoice
  hasReceipt?: boolean;
  items?: ReceiptItem[]; // itemized breakdown extracted from receipt OCR
  categorySplits?: CategorySplit[]; // allocated category split amounts
}

export interface ExtractedStatementTransaction {
  id: string;
  date: string;
  description: string;
  merchant: string;
  amount: number;
  debit: number;
  credit: number;
  balance?: number;
  type: TransactionType;
  suggestedCategory: ExpenseCategory;
  selectedCategory: ExpenseCategory;
  matchedAccountId?: string;
  currency: string;
  isDuplicate?: boolean;
  duplicateReason?: string;
  isSuspicious?: boolean;
  suspiciousReason?: string;
  selected: boolean;
}

export interface StatementExtractionResult {
  bankName: string;
  accountNumberMasked?: string;
  accountType?: AccountType;
  statementPeriod?: { start?: string; end?: string };
  openingBalance?: number;
  closingBalance?: number;
  totalDebits?: number;
  totalCredits?: number;
  currency?: string;
  reconciliation?: {
    isBalanced: boolean;
    calculatedClosing?: number;
    variance?: number;
    notes?: string;
    flaggedItemsCount?: number;
  };
  transactions: ExtractedStatementTransaction[];
}

export interface Subscription {
  id: string;
  name: string;
  amount: number; // in AED
  category: ExpenseCategory;
  billingCycle: 'monthly' | 'yearly';
  billingDay: number; // 1-31
  accountId: string;
  active: boolean;
  logoText: string;
  color: string;
}

export interface MerchantRuleCorrection {
  merchantKeyword: string;
  category: ExpenseCategory;
  updatedAt: string;
}

export interface MerchantLedgerMemory {
  merchantKeyword: string;
  accountId: string;
  accountName?: string;
  category?: ExpenseCategory;
  updatedAt: string;
}

