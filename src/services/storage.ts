import {
  Account,
  CategoryBudget,
  ExpenseCategory,
  MerchantLedgerMemory,
  MerchantRuleCorrection,
  Subscription,
  Transaction
} from '../types/finance';

const STORAGE_KEYS = {
  TRANSACTIONS: 'dirhamtrack_transactions_clean_v5',
  ACCOUNTS: 'dirhamtrack_accounts_clean_v5',
  BUDGETS: 'dirhamtrack_budgets_clean_v5',
  SUBSCRIPTIONS: 'dirhamtrack_subscriptions_clean_v5',
  CORRECTIONS: 'dirhamtrack_corrections_clean_v5',
  LEDGER_MEMORY: 'dirhamtrack_ledger_memory_v1',
  CUSTOM_CATEGORIES: 'dirhamtrack_custom_categories_v1',
  PIN_CODE: 'dirhamtrack_pin_v5',
  IS_PIN_ENABLED: 'dirhamtrack_pin_enabled_v5',
  PIN_AUTO_LOCK: 'dirhamtrack_pin_autolock_v1',
  PIN_PHONE: 'dirhamtrack_pin_phone_v1',
  PIN_EMAIL: 'dirhamtrack_pin_email_v1',
  IS_LOCKED: 'dirhamtrack_is_locked_v1',
  THEME_MODE: 'dirhamtrack_theme_v5'
};

// Default accounts: Starts with Cash Wallet only - NO pre-added bank accounts
export const DEFAULT_ACCOUNTS: Account[] = [
  {
    id: 'acc-cash',
    name: 'Cash Wallet',
    type: 'cash',
    accountNumberMasked: 'Cash',
    balance: 0.00,
    initialBalance: 0.00,
    color: '#10b981'
  }
];

export const DEFAULT_BUDGETS: CategoryBudget[] = [
  { category: 'Rent & Housing', monthlyLimit: 5500, icon: 'Home', color: '#6366f1' },
  { category: 'Food & Groceries', monthlyLimit: 3000, icon: 'ShoppingBag', color: '#10b981' },
  { category: 'Food', monthlyLimit: 1500, icon: 'Utensils', color: '#f97316' },
  { category: 'Groceries', monthlyLimit: 1500, icon: 'ShoppingBag', color: '#10b981' },
  { category: 'Clothing', monthlyLimit: 1200, icon: 'Shirt', color: '#ec4899' },
  { category: 'Fuel', monthlyLimit: 800, icon: 'Fuel', color: '#06b6d4' },
  { category: 'Petrol', monthlyLimit: 800, icon: 'Fuel', color: '#06b6d4' },
  { category: 'Utilities', monthlyLimit: 950, icon: 'Zap', color: '#eab308' },
  { category: 'Telecom', monthlyLimit: 500, icon: 'Phone', color: '#8b5cf6' },
  { category: 'Shopping', monthlyLimit: 1500, icon: 'Tag', color: '#ec4899' },
  { category: 'Transport', monthlyLimit: 500, icon: 'Car', color: '#3b82f6' },
  { category: 'Entertainment', monthlyLimit: 600, icon: 'Film', color: '#14b8a6' },
  { category: 'Healthcare', monthlyLimit: 500, icon: 'HeartPulse', color: '#ef4444' },
  { category: 'Education', monthlyLimit: 1000, icon: 'GraduationCap', color: '#0ea5e9' }
];

export const DEFAULT_SUBSCRIPTIONS: Subscription[] = [];

// Completely empty transactions list - 0 sample transactions
export const DEFAULT_TRANSACTIONS: Transaction[] = [];

export const DEFAULT_CORRECTIONS: MerchantRuleCorrection[] = [
  { merchantKeyword: 'enoc', category: 'Petrol', updatedAt: '2026-10-01' },
  { merchantKeyword: 'adnoc', category: 'Petrol', updatedAt: '2026-10-01' },
  { merchantKeyword: 'eppco', category: 'Petrol', updatedAt: '2026-10-01' },
  { merchantKeyword: 'kfc', category: 'Food', updatedAt: '2026-10-01' },
  { merchantKeyword: 'mcdonald', category: 'Food', updatedAt: '2026-10-01' },
  { merchantKeyword: 'carrefour', category: 'Groceries', updatedAt: '2026-10-01' },
  { merchantKeyword: 'lulu', category: 'Groceries', updatedAt: '2026-10-01' },
  { merchantKeyword: 'nesto', category: 'Groceries', updatedAt: '2026-10-01' },
  { merchantKeyword: 'dewa', category: 'Utilities', updatedAt: '2026-10-01' },
  { merchantKeyword: 'sewa', category: 'Utilities', updatedAt: '2026-10-01' },
  { merchantKeyword: 'etisalat', category: 'Telecom', updatedAt: '2026-10-01' },
  { merchantKeyword: 'du', category: 'Telecom', updatedAt: '2026-10-01' },
  { merchantKeyword: 'amazon', category: 'Shopping', updatedAt: '2026-10-01' },
  { merchantKeyword: 'noon', category: 'Shopping', updatedAt: '2026-10-01' },
  { merchantKeyword: 'rta', category: 'Transport', updatedAt: '2026-10-01' },
  { merchantKeyword: 'salik', category: 'Transport', updatedAt: '2026-10-01' }
];

// Safe LocalStorage helpers for cross-environment stability (Browser, PWA, SSR, Test)
function safeGetItem(key: string): string | null {
  try {
    if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
      return localStorage.getItem(key);
    }
  } catch {}
  return null;
}

function safeSetItem(key: string, value: string): void {
  try {
    if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
      localStorage.setItem(key, value);
    }
  } catch (err) {
    console.warn(`StorageService safeSetItem failed for key "${key}":`, err);
  }
}

export class StorageService {
  static getTransactions(): Transaction[] {
    const data = safeGetItem(STORAGE_KEYS.TRANSACTIONS);
    if (!data) return DEFAULT_TRANSACTIONS;
    try {
      return JSON.parse(data);
    } catch {
      return DEFAULT_TRANSACTIONS;
    }
  }

  static saveTransactions(txs: Transaction[]): void {
    safeSetItem(STORAGE_KEYS.TRANSACTIONS, JSON.stringify(txs));
  }

  static getAccounts(): Account[] {
    const data = safeGetItem(STORAGE_KEYS.ACCOUNTS);
    if (!data) return DEFAULT_ACCOUNTS;
    try {
      return JSON.parse(data);
    } catch {
      return DEFAULT_ACCOUNTS;
    }
  }

  static saveAccounts(accs: Account[]): void {
    safeSetItem(STORAGE_KEYS.ACCOUNTS, JSON.stringify(accs));
  }

  static getBudgets(): CategoryBudget[] {
    const data = safeGetItem(STORAGE_KEYS.BUDGETS);
    if (!data) return DEFAULT_BUDGETS;
    try {
      return JSON.parse(data);
    } catch {
      return DEFAULT_BUDGETS;
    }
  }

  static saveBudgets(budgets: CategoryBudget[]): void {
    safeSetItem(STORAGE_KEYS.BUDGETS, JSON.stringify(budgets));
  }

  static getSubscriptions(): Subscription[] {
    const data = safeGetItem(STORAGE_KEYS.SUBSCRIPTIONS);
    if (!data) return DEFAULT_SUBSCRIPTIONS;
    try {
      return JSON.parse(data);
    } catch {
      return DEFAULT_SUBSCRIPTIONS;
    }
  }

  static saveSubscriptions(subs: Subscription[]): void {
    safeSetItem(STORAGE_KEYS.SUBSCRIPTIONS, JSON.stringify(subs));
  }

  static getCorrections(): MerchantRuleCorrection[] {
    const data = safeGetItem(STORAGE_KEYS.CORRECTIONS);
    if (!data) return DEFAULT_CORRECTIONS;
    try {
      return JSON.parse(data);
    } catch {
      return DEFAULT_CORRECTIONS;
    }
  }

  static saveCorrections(rules: MerchantRuleCorrection[]): void {
    safeSetItem(STORAGE_KEYS.CORRECTIONS, JSON.stringify(rules));
  }

  static addCorrection(merchantKeyword: string, category: ExpenseCategory): void {
    const list = this.getCorrections();
    const cleanKey = merchantKeyword.toLowerCase().trim();
    const existingIndex = list.findIndex(r => r.merchantKeyword.toLowerCase() === cleanKey);
    const item: MerchantRuleCorrection = {
      merchantKeyword: cleanKey,
      category,
      updatedAt: new Date().toISOString()
    };
    if (existingIndex >= 0) {
      list[existingIndex] = item;
    } else {
      list.unshift(item);
    }
    this.saveCorrections(list);
  }

  static getMerchantLedgerMemories(): MerchantLedgerMemory[] {
    const data = safeGetItem(STORAGE_KEYS.LEDGER_MEMORY);
    if (!data) return [];
    try {
      return JSON.parse(data);
    } catch {
      return [];
    }
  }

  static saveMerchantLedgerMemories(memories: MerchantLedgerMemory[]): void {
    safeSetItem(STORAGE_KEYS.LEDGER_MEMORY, JSON.stringify(memories));
  }

  /**
   * Learns and remembers which ledger (Account) a merchant was assigned to.
   * Future transactions with this merchant will automatically route to this ledger.
   */
  static rememberMerchantLedger(
    merchant: string,
    accountId: string,
    accountName?: string,
    category?: ExpenseCategory
  ): void {
    if (!merchant || !merchant.trim() || !accountId) return;
    const cleanKey = merchant.toLowerCase().trim();
    const list = this.getMerchantLedgerMemories();
    const existingIndex = list.findIndex(r => r.merchantKeyword.toLowerCase() === cleanKey);
    const item: MerchantLedgerMemory = {
      merchantKeyword: cleanKey,
      accountId,
      accountName,
      category,
      updatedAt: new Date().toISOString()
    };
    if (existingIndex >= 0) {
      list[existingIndex] = item;
    } else {
      list.unshift(item);
    }
    this.saveMerchantLedgerMemories(list);
  }

  /**
   * Finds the remembered ledger (accountId) for a given merchant, checking:
   * 1. Explicit merchant-to-ledger memory rules
   * 2. Historical transactions for the same or similar merchant name
   */
  /**
   * Retrieves all unique past merchants known from memory and transactions.
   */
  static getAllPastMerchants(existingTransactions?: Transaction[]): string[] {
    const list: string[] = [];
    const memories = this.getMerchantLedgerMemories();
    for (const m of memories) {
      if (m.merchantKeyword && m.merchantKeyword.length >= 2 && !list.includes(m.merchantKeyword)) {
        list.push(m.merchantKeyword);
      }
    }
    if (existingTransactions) {
      for (const t of existingTransactions) {
        if (t.merchant && t.merchant !== 'Unknown Merchant' && !list.includes(t.merchant)) {
          list.push(t.merchant);
        }
      }
    }
    return list;
  }

  static findRememberedLedger(
    merchant: string,
    existingTransactions?: Transaction[]
  ): string | undefined {
    if (!merchant || merchant.trim().length < 2 || merchant.toLowerCase() === 'unknown merchant') return undefined;
    const clean = merchant.toLowerCase().trim();

    // 1. Check explicit ledger memory
    const memories = this.getMerchantLedgerMemories();
    const match = memories.find(m => {
      const key = m.merchantKeyword.toLowerCase().trim();
      return clean === key || clean.includes(key) || key.includes(clean);
    });
    if (match && match.accountId) {
      return match.accountId;
    }

    // 2. Check previous transactions history for this merchant
    if (existingTransactions && existingTransactions.length > 0) {
      const pastTx = existingTransactions.find(t => {
        if (!t.merchant || !t.accountId || t.merchant === 'Unknown Merchant') return false;
        const pastName = t.merchant.toLowerCase().trim();
        return pastName === clean || pastName.includes(clean) || clean.includes(pastName);
      });
      if (pastTx && pastTx.accountId) {
        return pastTx.accountId;
      }
    }

    return undefined;
  }

  static getCustomCategories(): string[] {
    try {
      const data = localStorage.getItem(STORAGE_KEYS.CUSTOM_CATEGORIES);
      return data ? JSON.parse(data) : [];
    } catch {
      return [];
    }
  }

  static saveCustomCategories(categories: string[]): void {
    localStorage.setItem(STORAGE_KEYS.CUSTOM_CATEGORIES, JSON.stringify(categories));
  }

  static addCustomCategory(categoryName: string): string[] {
    const clean = categoryName.trim();
    if (!clean) return this.getCustomCategories();
    const existing = this.getCustomCategories();
    if (!existing.some(c => c.toLowerCase() === clean.toLowerCase())) {
      const updated = [...existing, clean];
      this.saveCustomCategories(updated);
      return updated;
    }
    return existing;
  }

  static deleteCustomCategory(categoryName: string): string[] {
    const existing = this.getCustomCategories();
    const updated = existing.filter(c => c.toLowerCase() !== categoryName.toLowerCase().trim());
    this.saveCustomCategories(updated);
    return updated;
  }

  static getAllExpenseCategories(): ExpenseCategory[] {
    const base: ExpenseCategory[] = [
      'Food & Groceries',
      'Food',
      'Groceries',
      'Clothing',
      'Shopping',
      'Fuel',
      'Petrol',
      'Healthcare',
      'Transport',
      'Rent & Housing',
      'Utilities',
      'Telecom',
      'Entertainment',
      'Travel',
      'Education',
      'Salary',
      'Other'
    ];
    const custom = this.getCustomCategories();
    for (const c of custom) {
      if (!base.includes(c)) {
        base.splice(base.length - 2, 0, c); // insert before Salary and Other
      }
    }
    return base;
  }

  static getPin(): { enabled: boolean; pin: string; autoLock: boolean; email: string; phone: string } {
    try {
      const enabled = localStorage.getItem(STORAGE_KEYS.IS_PIN_ENABLED) === 'true';
      const pin = localStorage.getItem(STORAGE_KEYS.PIN_CODE) || '1234';
      const autoLock = localStorage.getItem(STORAGE_KEYS.PIN_AUTO_LOCK) !== 'false'; // default true
      const email = localStorage.getItem(STORAGE_KEYS.PIN_EMAIL) || 'fmdsmb52@gmail.com';
      const phone = localStorage.getItem(STORAGE_KEYS.PIN_PHONE) || '';
      return { enabled, pin, autoLock, email, phone };
    } catch {
      return { enabled: false, pin: '1234', autoLock: true, email: 'fmdsmb52@gmail.com', phone: '' };
    }
  }

  static setPin(enabled: boolean, pin: string, autoLock = true, email = 'fmdsmb52@gmail.com', phone = ''): void {
    localStorage.setItem(STORAGE_KEYS.IS_PIN_ENABLED, String(enabled));
    localStorage.setItem(STORAGE_KEYS.PIN_CODE, pin);
    localStorage.setItem(STORAGE_KEYS.PIN_AUTO_LOCK, String(autoLock));
    if (email) {
      localStorage.setItem(STORAGE_KEYS.PIN_EMAIL, email.trim());
    }
    if (phone) {
      localStorage.setItem(STORAGE_KEYS.PIN_PHONE, phone.trim());
    }
    if (enabled) {
      localStorage.setItem(STORAGE_KEYS.IS_LOCKED, 'true');
    }
  }

  static getIsLocked(): boolean {
    try {
      const pinConfig = this.getPin();
      if (!pinConfig.enabled) return false;
      const val = localStorage.getItem(STORAGE_KEYS.IS_LOCKED);
      // If PIN is enabled, app should lock by default unless explicitly unlocked
      return val !== 'false';
    } catch {
      return false;
    }
  }

  static setIsLocked(locked: boolean): void {
    try {
      localStorage.setItem(STORAGE_KEYS.IS_LOCKED, String(locked));
    } catch {}
  }

  static clearAllData(): void {
    // Clear all previous versions as well
    localStorage.clear();
  }

  /**
   * Computes the signed impact of a single transaction on a given account.
   * Returns a positive or negative float.
   * Handles:
   * - expense: decreases bank/cash balance, INCREASES credit card outstanding balance
   * - income: increases bank/cash balance, DECREASES credit card outstanding balance (refunds/cashback)
   * - card_payment: decreases bank balance, DECREASES credit card debt (anti-double-counting)
   * - transfer: decreases fromAccount balance, increases toAccount balance
   */
  static calculateTransactionImpact(
    tx: Transaction,
    accountId: string,
    accountType: string
  ): number {
    const isFrom = tx.accountId === accountId;
    const isTo = tx.toAccountId === accountId;

    if (!isFrom && !isTo) return 0;

    const amount = Number(tx.amount) || 0;

    if (tx.type === 'expense') {
      if (isFrom) {
        // For credit cards: expense increases outstanding debt (+amount)
        // For bank/cash: expense decreases available balance (-amount)
        return accountType === 'credit_card' ? amount : -amount;
      }
    } else if (tx.type === 'income') {
      if (isFrom) {
        // For credit cards: income/refund decreases outstanding debt (-amount)
        // For bank/cash: income increases available balance (+amount)
        return accountType === 'credit_card' ? -amount : amount;
      }
    } else if (tx.type === 'card_payment') {
      if (isFrom) {
        // Paying bank account: balance decreases (-amount)
        return -amount;
      }
      if (isTo) {
        // Target credit card: outstanding debt decreases (-amount)
        return -amount;
      }
    } else if (tx.type === 'transfer' || tx.type === 'investment_deposit' || tx.type === 'investment_withdrawal') {
      if (isFrom) {
        return accountType === 'credit_card' ? amount : -amount;
      }
      if (isTo) {
        return accountType === 'credit_card' ? -amount : amount;
      }
    }

    return 0;
  }

  /**
   * Recalculates all account balances strictly and accurately based on their
   * starting opening balance (initialBalance) and all actual recorded transactions.
   * Guaranteed to eliminate discrepancies from duplicated entries, deleted transactions,
   * or edited accounts/amounts.
   */
  static recalculateAccountBalances(
    accounts: Account[],
    transactions: Transaction[]
  ): Account[] {
    return accounts.map(acc => {
      // Determine initial starting opening balance for this account
      let startingBalance = acc.initialBalance;
      if (startingBalance === undefined) {
        if (acc.type === 'credit_card') {
          // Credit cards in standard practice start with 0 debt unless explicitly specified
          startingBalance = 0;
        } else {
          // If transactions exist and account has a balance, preserve opening balance
          let historicalImpact = 0;
          for (const tx of transactions) {
            historicalImpact += this.calculateTransactionImpact(tx, acc.id, acc.type);
          }
          startingBalance = Math.round((acc.balance - historicalImpact) * 100) / 100;
        }
      }

      // Compute exact cumulative impact of all current transactions
      let netImpact = 0;
      for (const tx of transactions) {
        netImpact += this.calculateTransactionImpact(tx, acc.id, acc.type);
      }

      const rawCalculated = Math.round((startingBalance + netImpact) * 100) / 100;

      // Handle Investment accounts (valuation, invested capital, gain/loss)
      if (acc.type === 'investment') {
        const totalInvested = Math.max(0, rawCalculated);
        let valuation = acc.currentValuation;
        if (valuation === undefined) {
          valuation = totalInvested;
        } else if (acc.totalInvested !== undefined) {
          // If total invested changed due to new deposits or withdrawals, adjust valuation by the cash flow delta
          const deltaTransfers = totalInvested - acc.totalInvested;
          if (deltaTransfers !== 0) {
            valuation = Math.max(0, Math.round((valuation + deltaTransfers) * 100) / 100);
          }
        }
        const gainLoss = Math.round((valuation - totalInvested) * 100) / 100;
        const gainLossPct = totalInvested > 0 ? Math.round(((valuation - totalInvested) / totalInvested) * 1000) / 10 : 0;

        return {
          ...acc,
          initialBalance: startingBalance,
          totalInvested,
          currentValuation: valuation,
          balance: valuation,
          unrealizedGainLoss: gainLoss,
          gainLossPercentage: gainLossPct
        };
      }

      // For credit cards, outstanding debt cannot be negative
      const finalBalance = acc.type === 'credit_card' ? Math.max(0, rawCalculated) : rawCalculated;

      return {
        ...acc,
        initialBalance: startingBalance,
        balance: finalBalance
      };
    });
  }

  /**
   * Applies transaction financial impact to ledger accounts.
   */
  static applyTransactionLedger(
    tx: Transaction,
    accounts: Account[]
  ): Account[] {
    const updated = [...accounts];
    const fromAccIndex = updated.findIndex(a => a.id === tx.accountId);
    const toAccIndex = tx.toAccountId ? updated.findIndex(a => a.id === tx.toAccountId) : -1;

    if (fromAccIndex >= 0) {
      const fromAcc = updated[fromAccIndex];
      const delta = this.calculateTransactionImpact(tx, fromAcc.id, fromAcc.type);
      const newBal = Math.round((fromAcc.balance + delta) * 100) / 100;
      updated[fromAccIndex] = {
        ...fromAcc,
        balance: fromAcc.type === 'credit_card' ? Math.max(0, newBal) : newBal
      };
    }

    if (toAccIndex >= 0) {
      const toAcc = updated[toAccIndex];
      const delta = this.calculateTransactionImpact(tx, toAcc.id, toAcc.type);
      const newBal = Math.round((toAcc.balance + delta) * 100) / 100;
      updated[toAccIndex] = {
        ...toAcc,
        balance: toAcc.type === 'credit_card' ? Math.max(0, newBal) : newBal
      };
    }

    return updated;
  }

  /**
   * Reverts transaction financial impact from ledger accounts.
   * Called when a transaction is deleted or replaced.
   */
  static revertTransactionLedger(
    tx: Transaction,
    accounts: Account[]
  ): Account[] {
    const updated = [...accounts];
    const fromAccIndex = updated.findIndex(a => a.id === tx.accountId);
    const toAccIndex = tx.toAccountId ? updated.findIndex(a => a.id === tx.toAccountId) : -1;

    if (fromAccIndex >= 0) {
      const fromAcc = updated[fromAccIndex];
      // Revert is the exact opposite of impact (-delta)
      const delta = this.calculateTransactionImpact(tx, fromAcc.id, fromAcc.type);
      const newBal = Math.round((fromAcc.balance - delta) * 100) / 100;
      updated[fromAccIndex] = {
        ...fromAcc,
        balance: fromAcc.type === 'credit_card' ? Math.max(0, newBal) : newBal
      };
    }

    if (toAccIndex >= 0) {
      const toAcc = updated[toAccIndex];
      const delta = this.calculateTransactionImpact(tx, toAcc.id, toAcc.type);
      const newBal = Math.round((toAcc.balance - delta) * 100) / 100;
      updated[toAccIndex] = {
        ...toAcc,
        balance: toAcc.type === 'credit_card' ? Math.max(0, newBal) : newBal
      };
    }

    return updated;
  }
}
