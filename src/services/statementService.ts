import {
  Account,
  ExtractedStatementTransaction,
  StatementExtractionResult,
  Transaction,
  ExpenseCategory
} from '../types/finance';
import { findDuplicateTransaction } from './deduplication';
import { StorageService } from './storage';

export class StatementService {
  /**
   * Sends the bank statement file (PDF, XLSX, XLS, CSV) to the server-side
   * Gemini Document AI & Python Rules Engine parser.
   */
  static async parseStatement(
    file: File,
    bankHint?: string,
    accounts?: Account[]
  ): Promise<StatementExtractionResult> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = async () => {
        try {
          const base64Data = reader.result as string;
          const cleanBase64 = base64Data.replace(/^data:[^;]+;base64,/, '');

          const response = await fetch('/api/statement/parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              fileBase64: cleanBase64,
              fileName: file.name,
              fileType: file.name.split('.').pop()?.toLowerCase(),
              bankHint: bankHint || '',
              accounts: accounts || []
            })
          });

          if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Server returned status ${response.status}`);
          }

          const result = await response.json();
          if (!result.success || !result.data) {
            throw new Error(result.error || 'Invalid statement data received');
          }

          resolve(result.data);
        } catch (err) {
          reject(err);
        }
      };

      reader.onerror = () => {
        reject(new Error('Failed to read statement file from disk'));
      };

      reader.readAsDataURL(file);
    });
  }

  /**
   * Cross-checks each extracted transaction against existing ledger entries
   * using the multi-attribute duplicate shield.
   */
  static applyDuplicateShield(
    extractedTransactions: ExtractedStatementTransaction[],
    existingTransactions: Transaction[]
  ): ExtractedStatementTransaction[] {
    return extractedTransactions.map(tx => {
      const dupCheck = findDuplicateTransaction(
        {
          amount: tx.amount,
          merchant: tx.merchant,
          date: tx.date,
          currency: tx.currency,
          type: tx.type,
          rawNotificationText: tx.description
        },
        existingTransactions
      );

      if (dupCheck.isDuplicate) {
        return {
          ...tx,
          isDuplicate: true,
          duplicateReason: `Already in ledger: AED ${tx.amount.toFixed(2)} on ${dupCheck.matchedTransaction?.date || tx.date} (${dupCheck.matchedTransaction?.merchant || tx.merchant})`,
          selected: false // Default to unselected so duplicates aren't double-posted
        };
      }

      return {
        ...tx,
        isDuplicate: false,
        selected: true
      };
    });
  }

  /**
   * Posts approved statement transactions into the live ledger and updates bank/card balances.
   */
  static postTransactionsToLedger(
    approvedItems: ExtractedStatementTransaction[],
    targetAccountId: string,
    existingAccounts: Account[],
    existingTransactions: Transaction[]
  ): { updatedAccounts: Account[]; newTransactions: Transaction[]; postedCount: number } {
    if (approvedItems.length === 0) {
      return { updatedAccounts: existingAccounts, newTransactions: existingTransactions, postedCount: 0 };
    }

    const targetAccount = existingAccounts.find(a => a.id === targetAccountId);
    const newTxList: Transaction[] = [];

    // Track balance delta
    let bankCashDelta = 0;
    let cardDebtDelta = 0;

    for (const item of approvedItems) {
      // Create new transaction
      const txId = `tx-stmt-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
      const isCardPayment = item.type === 'card_payment';
      const isTransfer = item.type === 'transfer';
      const isIncome = item.type === 'income';

      const newTx: Transaction = {
        id: txId,
        amount: item.amount,
        currency: 'AED',
        merchant: item.merchant,
        category: item.selectedCategory || item.suggestedCategory,
        date: item.date,
        time: '12:00 PM',
        accountId: targetAccountId,
        type: item.type,
        source: 'statement_import',
        bankName: targetAccount?.bankName || targetAccount?.name || 'Bank',
        rawNotificationText: item.description,
        isRedFlag: Boolean(item.isSuspicious),
        redFlagReason: item.suspiciousReason,
        isVerifiedByUser: true,
        notes: `Imported via Bank Statement (${item.description})`
      };

      newTxList.push(newTx);

      // Save user category correction to merchant memory so AI learns for future
      if (item.merchant && item.selectedCategory) {
        StorageService.addCorrection(item.merchant, item.selectedCategory);
        if (targetAccountId) {
          StorageService.rememberMerchantLedger(item.merchant, targetAccountId, targetAccount?.name, item.selectedCategory);
        }
      }

      // Calculate account balance adjustment
      if (targetAccount) {
        if (targetAccount.type === 'credit_card') {
          if (isCardPayment) {
            cardDebtDelta -= item.amount; // Payment lowers credit debt
          } else if (item.type === 'expense') {
            cardDebtDelta += item.amount; // Expense increases credit debt
          }
        } else {
          // Bank checking or Cash wallet
          if (isIncome || item.credit > 0) {
            bankCashDelta += item.amount; // Income increases bank balance
          } else if (item.type === 'expense' || item.debit > 0) {
            bankCashDelta -= item.amount; // Expense decreases bank balance
          }
        }
      }
    }

    // Apply account balance updates
    const updatedAccounts = existingAccounts.map(acc => {
      if (acc.id === targetAccountId) {
        if (acc.type === 'credit_card') {
          const newBal = Math.max(0, acc.balance + cardDebtDelta);
          return { ...acc, balance: Math.round(newBal * 100) / 100 };
        } else {
          const newBal = acc.balance + bankCashDelta;
          return { ...acc, balance: Math.round(newBal * 100) / 100 };
        }
      }
      return acc;
    });

    const combinedTransactions = [...newTxList, ...existingTransactions];

    // Persist to local storage
    StorageService.saveTransactions(combinedTransactions);
    StorageService.saveAccounts(updatedAccounts);

    return {
      updatedAccounts,
      newTransactions: combinedTransactions,
      postedCount: newTxList.length
    };
  }

  /**
   * Built-in realistic UAE bank statement samples for 1-click testing.
   */
  static getSampleStatements(): {
    name: string;
    bankName: string;
    accountType: 'bank' | 'credit_card';
    description: string;
    data: StatementExtractionResult;
  }[] {
    const today = new Date();
    const curYear = today.getFullYear();
    const curMonth = (today.getMonth() + 1).toString().padStart(2, '0');

    return [
      {
        name: 'Emirates NBD Checking Account',
        bankName: 'Emirates NBD',
        accountType: 'bank',
        description: 'Standard monthly current account statement with WPS Salary, DEWA, Carrefour, ADNOC, and Credit Card Autopay.',
        data: {
          bankName: 'Emirates NBD',
          accountNumberMasked: '•••• 8912',
          accountType: 'bank',
          statementPeriod: {
            start: `${curYear}-${curMonth}-01`,
            end: `${curYear}-${curMonth}-28`
          },
          openingBalance: 12500.0,
          closingBalance: 16120.0,
          totalDebits: 6380.0,
          totalCredits: 10000.0,
          currency: 'AED',
          reconciliation: {
            isBalanced: true,
            calculatedClosing: 16120.0,
            variance: 0.0,
            notes: 'Verified: Opening (AED 12,500.00) + Credits (AED 10,000.00) - Debits (AED 6,380.00) = Closing (AED 16,120.00).',
            flaggedItemsCount: 1
          },
          transactions: [
            {
              id: 'sample-enbd-1',
              date: `${curYear}-${curMonth}-01`,
              description: 'WPS SALARY TRANSFER MOHRE PAYROLL REF 99281',
              merchant: 'WPS Salary Transfer',
              amount: 10000.0,
              debit: 0,
              credit: 10000.0,
              balance: 22500.0,
              type: 'income',
              suggestedCategory: 'Salary',
              selectedCategory: 'Salary',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-enbd-2',
              date: `${curYear}-${curMonth}-04`,
              description: 'DIRECT DEBIT DEWA ELECTRICITY & WATER DUBAI',
              merchant: 'DEWA',
              amount: 680.0,
              debit: 680.0,
              credit: 0,
              balance: 21820.0,
              type: 'expense',
              suggestedCategory: 'Utilities',
              selectedCategory: 'Utilities',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-enbd-3',
              date: `${curYear}-${curMonth}-08`,
              description: 'POS PURCHASE CARREFOUR MOE MALL OF EMIRATES',
              merchant: 'Carrefour',
              amount: 420.0,
              debit: 420.0,
              credit: 0,
              balance: 21400.0,
              type: 'expense',
              suggestedCategory: 'Groceries',
              selectedCategory: 'Groceries',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-enbd-4',
              date: `${curYear}-${curMonth}-12`,
              description: 'POS ENOC 1042 SZR PETROL STATION DUBAI',
              merchant: 'ENOC Petrol',
              amount: 160.0,
              debit: 160.0,
              credit: 0,
              balance: 21240.0,
              type: 'expense',
              suggestedCategory: 'Fuel',
              selectedCategory: 'Fuel',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-enbd-5',
              date: `${curYear}-${curMonth}-16`,
              description: 'AUTOPAY DU TELECOM MONTHLY POSTPAID 0501234567',
              merchant: 'Du Telecom',
              amount: 320.0,
              debit: 320.0,
              credit: 0,
              balance: 20920.0,
              type: 'expense',
              suggestedCategory: 'Telecom',
              selectedCategory: 'Telecom',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-enbd-6',
              date: `${curYear}-${curMonth}-20`,
              description: 'PAYMENT TO ADCB CREDIT CARD AUTOPAY SETTLEMENT',
              merchant: 'Credit Card Payment (ADCB)',
              amount: 4800.0,
              debit: 4800.0,
              credit: 0,
              balance: 16120.0,
              type: 'card_payment',
              suggestedCategory: 'Other',
              selectedCategory: 'Other',
              currency: 'AED',
              isSuspicious: true,
              suspiciousReason: 'High single transaction amount (> AED 2,500)',
              selected: true
            }
          ]
        }
      },
      {
        name: 'ADCB TouchPoints Credit Card',
        bankName: 'Abu Dhabi Commercial Bank (ADCB)',
        accountType: 'credit_card',
        description: 'Monthly credit card billing statement showing dining, shopping, fuel, and payment settlement.',
        data: {
          bankName: 'Abu Dhabi Commercial Bank (ADCB)',
          accountNumberMasked: '•••• 4289',
          accountType: 'credit_card',
          statementPeriod: {
            start: `${curYear}-${curMonth}-01`,
            end: `${curYear}-${curMonth}-25`
          },
          openingBalance: 3200.0,
          closingBalance: 1950.0,
          totalDebits: 1950.0,
          totalCredits: 3200.0,
          currency: 'AED',
          reconciliation: {
            isBalanced: true,
            calculatedClosing: 1950.0,
            variance: 0.0,
            notes: 'Verified: Previous Balance (AED 3,200.00) - Payments (AED 3,200.00) + New Charges (AED 1,950.00) = Outstanding Balance (AED 1,950.00).',
            flaggedItemsCount: 0
          },
          transactions: [
            {
              id: 'sample-adcb-1',
              date: `${curYear}-${curMonth}-03`,
              description: 'PAYMENT RECEIVED - THANK YOU ONLINE BANKING',
              merchant: 'Credit Card Payment',
              amount: 3200.0,
              debit: 0,
              credit: 3200.0,
              balance: 0.0,
              type: 'card_payment',
              suggestedCategory: 'Other',
              selectedCategory: 'Other',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-2',
              date: `${curYear}-${curMonth}-06`,
              description: 'ADNOC DISTRIB SERVICE STATION ABU DHABI',
              merchant: 'ADNOC Fuel',
              amount: 180.0,
              debit: 180.0,
              credit: 0,
              balance: 180.0,
              type: 'expense',
              suggestedCategory: 'Fuel',
              selectedCategory: 'Fuel',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-3',
              date: `${curYear}-${curMonth}-10`,
              description: 'SHAKE SHACK DUBAI MALL FOOD COURT',
              merchant: 'Shake Shack',
              amount: 145.0,
              debit: 145.0,
              credit: 0,
              balance: 325.0,
              type: 'expense',
              suggestedCategory: 'Food',
              selectedCategory: 'Food',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-4',
              date: `${curYear}-${curMonth}-15`,
              description: 'AMAZON.AE ONLINE RETAIL DUBAI',
              merchant: 'Amazon.ae',
              amount: 625.0,
              debit: 625.0,
              credit: 0,
              balance: 950.0,
              type: 'expense',
              suggestedCategory: 'Shopping',
              selectedCategory: 'Shopping',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-5',
              date: `${curYear}-${curMonth}-18`,
              description: 'ASTER PHARMACY LLC MEDICINE PURCHASE',
              merchant: 'Aster Pharmacy',
              amount: 220.0,
              debit: 220.0,
              credit: 0,
              balance: 1170.0,
              type: 'expense',
              suggestedCategory: 'Healthcare',
              selectedCategory: 'Healthcare',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-6',
              date: `${curYear}-${curMonth}-22`,
              description: 'VOX CINEMAS DUBAI FESTIVAL CITY TICKETS',
              merchant: 'VOX Cinemas',
              amount: 180.0,
              debit: 180.0,
              credit: 0,
              balance: 1350.0,
              type: 'expense',
              suggestedCategory: 'Entertainment',
              selectedCategory: 'Entertainment',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            },
            {
              id: 'sample-adcb-7',
              date: `${curYear}-${curMonth}-24`,
              description: 'LULU HYPERMARKET AL BARSHA DUBAI',
              merchant: 'Lulu Hypermarket',
              amount: 600.0,
              debit: 600.0,
              credit: 0,
              balance: 1950.0,
              type: 'expense',
              suggestedCategory: 'Groceries',
              selectedCategory: 'Groceries',
              currency: 'AED',
              isSuspicious: false,
              selected: true
            }
          ]
        }
      }
    ];
  }
}
