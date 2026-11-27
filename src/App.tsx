import React, { useState, useEffect } from 'react';
import {
  Account,
  CategoryBudget,
  ExpenseCategory,
  Subscription,
  Transaction
} from './types/finance';
import { StorageService, DEFAULT_ACCOUNTS } from './services/storage';
import { Header } from './components/Header';
import { Dashboard } from './components/Dashboard';
import { TransactionList } from './components/TransactionList';
import { BudgetManager } from './components/BudgetManager';
import { AccountsManager } from './components/AccountsManager';
import { SubscriptionsTracker } from './components/SubscriptionsTracker';
import { AddTransactionModal } from './components/AddTransactionModal';
import { AddAccountModal } from './components/AddAccountModal';
import { AndroidCodeModal } from './components/AndroidCodeModal';
import { AndroidInstallGuideModal } from './components/AndroidInstallGuideModal';
import { MobileQRCodeModal } from './components/MobileQRCodeModal';
import { MonthlyReportModal } from './components/MonthlyReportModal';
import { PinLockScreen } from './components/PinLockScreen';
import { PinSettingsModal } from './components/PinSettingsModal';
import { AppGuideModal } from './components/AppGuideModal';
import { BottomNavBar } from './components/BottomNavBar';
import { VoiceExpenseModal } from './components/VoiceExpenseModal';
import { FraudDetectionModal } from './components/FraudDetectionModal';
import { PredictiveCashFlowModal } from './components/PredictiveCashFlowModal';
import { FinanceAssistantModal } from './components/FinanceAssistantModal';
import { KeyFeaturesModal } from './components/KeyFeaturesModal';
import { findDuplicateTransaction } from './services/deduplication';
import { extractDateAndTimeToISO } from './services/notificationParser';
import { Mic } from 'lucide-react';

const INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes (300,000 ms)
const SESSION_ACTIVE_KEY = 'dirhamtrack_session_active_v1';
const LAST_ACTIVE_KEY = 'dirhamtrack_last_active_v1';

export default function App() {
  // Navigation
  const [activeTab, setActiveTab] = useState<'dashboard' | 'transactions' | 'budgets' | 'accounts' | 'subscriptions'>('dashboard');

  // Application Data State - completely empty/clean
  const [transactions, setTransactions] = useState<Transaction[]>(() => StorageService.getTransactions());
  const [accounts, setAccounts] = useState<Account[]>(() => {
    const rawAccs = StorageService.getAccounts();
    const rawTxs = StorageService.getTransactions();
    return StorageService.recalculateAccountBalances(rawAccs, rawTxs);
  });
  const [budgets, setBudgets] = useState<CategoryBudget[]>(() => StorageService.getBudgets());
  const [subscriptions, setSubscriptions] = useState<Subscription[]>(() => StorageService.getSubscriptions());

  // Security State: If PIN is enabled, app starts locked on fresh launch
  const [pinConfig, setPinConfig] = useState(() => StorageService.getPin());
  const [isLocked, setIsLocked] = useState(() => {
    const config = StorageService.getPin();
    if (!config.enabled) return false;

    // Rule 1: Request PIN when opening the app after completely closing it
    if (typeof window !== 'undefined') {
      const isSessionActive = sessionStorage.getItem(SESSION_ACTIVE_KEY) === 'true';
      if (!isSessionActive) {
        StorageService.setIsLocked(true);
        return true;
      }

      // Rule 2 & 3: Check if time spent in background or away exceeded 5 minutes
      const lastActiveStr = localStorage.getItem(LAST_ACTIVE_KEY) || sessionStorage.getItem(LAST_ACTIVE_KEY);
      if (lastActiveStr) {
        const elapsed = Date.now() - parseInt(lastActiveStr, 10);
        if (elapsed >= INACTIVITY_TIMEOUT_MS) {
          StorageService.setIsLocked(true);
          return true;
        }
      }
    }

    return StorageService.getIsLocked();
  });
  const [pinSettingsModalOpen, setPinSettingsModalOpen] = useState(false);

  // Modals
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [addAccountModalOpen, setAddAccountModalOpen] = useState(false);
  const [reportModalOpen, setReportModalOpen] = useState(false);
  const [androidCodeModalOpen, setAndroidCodeModalOpen] = useState(false);
  const [androidGuideModalOpen, setAndroidGuideModalOpen] = useState(false);
  const [appGuideModalOpen, setAppGuideModalOpen] = useState(false);
  const [qrModalOpen, setQrModalOpen] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [selectedFilterCategory, setSelectedFilterCategory] = useState<string>('all');

  // DirhamTrack Suite Modals
  const [voiceModalOpen, setVoiceModalOpen] = useState(false);
  const [fraudModalOpen, setFraudModalOpen] = useState(false);
  const [forecastModalOpen, setForecastModalOpen] = useState(false);
  const [assistantModalOpen, setAssistantModalOpen] = useState(false);
  const [keyFeaturesModalOpen, setKeyFeaturesModalOpen] = useState(false);

  // Persist state changes
  useEffect(() => {
    StorageService.saveTransactions(transactions);
  }, [transactions]);

  useEffect(() => {
    StorageService.saveAccounts(accounts);
  }, [accounts]);

  useEffect(() => {
    StorageService.saveBudgets(budgets);
  }, [budgets]);

  useEffect(() => {
    StorageService.saveSubscriptions(subscriptions);
  }, [subscriptions]);

  // Smart PIN Lifecycle: 5-minute inactivity, background elapsed check, and user interaction reset
  useEffect(() => {
    if (!pinConfig.enabled) {
      StorageService.setIsLocked(false);
      return;
    }

    let inactivityTimer: NodeJS.Timeout | null = null;

    // Resets the 5-minute foreground inactivity timer upon user interaction
    const recordActiveAndResetTimer = () => {
      const now = Date.now();
      try {
        sessionStorage.setItem(LAST_ACTIVE_KEY, String(now));
        localStorage.setItem(LAST_ACTIVE_KEY, String(now));
      } catch {}

      if (inactivityTimer) {
        clearTimeout(inactivityTimer);
      }

      // If unlocked, trigger lock after 5 minutes of total user inactivity
      if (!isLocked) {
        inactivityTimer = setTimeout(() => {
          setIsLocked(true);
          StorageService.setIsLocked(true);
          try {
            sessionStorage.removeItem(SESSION_ACTIVE_KEY);
          } catch {}
        }, INACTIVITY_TIMEOUT_MS);
      }
    };

    // User interaction events reset the 5-minute idle countdown
    const handleUserInteraction = () => {
      recordActiveAndResetTimer();
    };

    // Record timestamp when user switches away to another app or minimizes
    const handleSwitchAway = () => {
      const now = Date.now();
      try {
        sessionStorage.setItem(LAST_ACTIVE_KEY, String(now));
        localStorage.setItem(LAST_ACTIVE_KEY, String(now));
      } catch {}
    };

    // Evaluate elapsed time when user resumes/returns to app
    const handleResumeApp = () => {
      const now = Date.now();
      let lastActive = 0;
      try {
        const str = localStorage.getItem(LAST_ACTIVE_KEY) || sessionStorage.getItem(LAST_ACTIVE_KEY);
        if (str) lastActive = parseInt(str, 10);
      } catch {}

      if (lastActive > 0) {
        const elapsed = now - lastActive;
        if (elapsed >= INACTIVITY_TIMEOUT_MS) {
          // More than 5 minutes spent in background/away: lock app!
          setIsLocked(true);
          StorageService.setIsLocked(true);
          try {
            sessionStorage.removeItem(SESSION_ACTIVE_KEY);
          } catch {}
          return;
        }
      }

      // User returned within 5 minutes: remain unlocked and restart inactivity timer!
      recordActiveAndResetTimer();
    };

    const handleVisibilityChange = () => {
      if (document.hidden || document.visibilityState === 'hidden') {
        handleSwitchAway();
      } else if (document.visibilityState === 'visible') {
        handleResumeApp();
      }
    };

    const handlePageHide = () => {
      handleSwitchAway();
    };

    const handlePageShow = () => {
      handleResumeApp();
    };

    const handleBlur = () => {
      handleSwitchAway();
    };

    const handleFocus = () => {
      handleResumeApp();
    };

    // User interaction listeners to keep session alive during active use
    const userEvents = ['mousedown', 'mousemove', 'keydown', 'touchstart', 'scroll', 'click'];
    userEvents.forEach(evt => window.addEventListener(evt, handleUserInteraction, { passive: true }));

    // App & PWA lifecycle listeners
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('pagehide', handlePageHide);
    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('focus', handleFocus);
    window.addEventListener('blur', handleBlur);

    // Initial timer setup
    recordActiveAndResetTimer();

    return () => {
      if (inactivityTimer) clearTimeout(inactivityTimer);
      userEvents.forEach(evt => window.removeEventListener(evt, handleUserInteraction));
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pagehide', handlePageHide);
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('blur', handleBlur);
    };
  }, [pinConfig.enabled, isLocked]);

  // Handle Recording New Transaction (from notification listener or manual entry)
  const handleRecordTransaction = (txData: Partial<Transaction>) => {
    // 1. Resolve merchant name: if unknown or missing, check raw text against past transactions & memory
    let resolvedMerchant = txData.merchant;
    let resolvedCategory = txData.category;

    if ((!resolvedMerchant || resolvedMerchant === 'Unknown Merchant') && txData.rawNotificationText) {
      const lowerRaw = txData.rawNotificationText.toLowerCase();
      const pastMerchants = StorageService.getAllPastMerchants(transactions);
      for (const pm of pastMerchants) {
        if (pm.length >= 2 && lowerRaw.includes(pm.toLowerCase())) {
          resolvedMerchant = pm;
          // Inherit category from previous transaction of same merchant
          const previousTx = transactions.find(t => t.merchant.toLowerCase() === pm.toLowerCase() && t.category !== 'Other');
          if (previousTx && (!resolvedCategory || resolvedCategory === 'Other')) {
            resolvedCategory = previousTx.category;
          }
          break;
        }
      }
    }

    const finalMerchant = resolvedMerchant || (txData.type === 'income' ? 'Salary Deposit' : 'Unknown Merchant');

    // Anti-Duplicate Barrier: Verify against existing transactions to prevent double counting from Push Notification and SMS
    const duplicateCandidate = {
      ...txData,
      merchant: finalMerchant,
      category: resolvedCategory
    };
    const duplicateCheck = findDuplicateTransaction(duplicateCandidate as any, transactions);

    if (duplicateCheck.isDuplicate && duplicateCheck.matchedTransaction) {
      const existing = duplicateCheck.matchedTransaction;

      // Corroborate existing transaction by recording dual verification across SMS & Push
      setTransactions(prev => prev.map(t => {
        if (t.id === existing.id) {
          return {
            ...t,
            notes: t.notes?.includes('Push & SMS')
              ? t.notes
              : `${t.notes ? t.notes + ' • ' : ''}Verified via Push & SMS (Duplicate avoided)`
          };
        }
        return t;
      }));

      setToastMessage(`🛡️ Duplicate Eliminated: AED ${(txData.amount || 0).toFixed(2)} at ${existing.merchant} already recorded (verified across Push Notification & SMS).`);
      setTimeout(() => setToastMessage(null), 5000);
      return;
    }

    // 2. Explicit account requested
    let targetAccount = accounts.find(a => {
      if (txData.accountId && a.id === txData.accountId) return true;
      return false;
    });

    // 3. Automatically remember previous transactions once entered in a particular ledger:
    // If not explicitly provided, check if merchant was previously entered under a particular ledger
    if (!targetAccount && finalMerchant && finalMerchant !== 'Unknown Merchant') {
      const rememberedAccId = StorageService.findRememberedLedger(finalMerchant, transactions);
      if (rememberedAccId) {
        targetAccount = accounts.find(a => a.id === rememberedAccId);
      }
    }

    // 4. Match account by bank name or card mask if still not resolved
    if (!targetAccount) {
      targetAccount = accounts.find(a => {
        if (txData.bankName && a.bankName && a.bankName.toLowerCase().includes(txData.bankName.toLowerCase())) return true;
        if (txData.rawNotificationText && a.accountNumberMasked && a.accountNumberMasked.length >= 4) {
          const last4 = a.accountNumberMasked.replace(/[^0-9]/g, '');
          if (last4 && txData.rawNotificationText.includes(last4)) return true;
        }
        return false;
      });
    }

    // 5. If still not matched and it's income (like Mashreq salary), prefer a bank account over cash/credit
    if (!targetAccount) {
      if (txData.type === 'income') {
        targetAccount = accounts.find(a => a.type === 'bank') || accounts[0];
      } else {
        targetAccount = accounts[0];
      }
    }

    const defaultAccountId = targetAccount?.id || 'acc-cash';
    const isForeign = Boolean(
      (txData.originalCurrency && txData.originalCurrency !== 'AED') ||
      (txData.currency && txData.currency !== 'AED') ||
      txData.exchangeRate
    );

    const isRedFlag = isForeign ? true : Boolean(txData.isRedFlag);
    const redFlagReason = isForeign
      ? (txData.redFlagReason || `International transaction (${txData.originalCurrency || 'USD'} ${txData.originalAmount?.toFixed(2) || ''}) - pending genuine confirmation`)
      : txData.redFlagReason;

    // International transactions must be explicitly verified by user
    const isVerifiedByUser = isForeign ? false : (txData.isVerifiedByUser ?? true);

    // Resolve accurate transaction date: If rawNotificationText is available, prioritize date found inside the SMS/notification
    let txDate = txData.date;
    let txTime = txData.time;
    if (txData.rawNotificationText) {
      const extracted = extractDateAndTimeToISO(txData.rawNotificationText);
      if (extracted.date && (!txDate || txDate === new Date().toISOString().split('T')[0])) {
        txDate = extracted.date;
      }
      if (extracted.time && !txTime) {
        txTime = extracted.time;
      }
    }

    const newTx: Transaction = {
      id: `tx-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`,
      amount: txData.amount || 0,
      originalAmount: txData.originalAmount,
      originalCurrency: txData.originalCurrency,
      exchangeRate: txData.exchangeRate || (isForeign && txData.originalAmount && txData.amount ? Number((txData.amount / txData.originalAmount).toFixed(4)) : undefined),
      currency: txData.currency || 'AED',
      merchant: finalMerchant,
      category: resolvedCategory || (txData.type === 'income' ? 'Salary' : 'Other'),
      date: txDate || new Date().toISOString().split('T')[0],
      time: txTime || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      accountId: defaultAccountId,
      toAccountId: txData.toAccountId,
      type: txData.type || 'expense',
      source: txData.source || 'manual',
      bankName: txData.bankName || (targetAccount?.bankName || targetAccount?.name),
      rawNotificationText: txData.rawNotificationText,
      isRedFlag,
      redFlagReason,
      isVerifiedByUser,
      notes: txData.notes,
      receiptImage: txData.receiptImage
    };

    // Update transaction list
    const nextTxs = [newTx, ...transactions];
    setTransactions(nextTxs);
    StorageService.saveTransactions(nextTxs);

    // Apply ledger updates with exact recalculation across all transactions
    const nextAccounts = StorageService.recalculateAccountBalances(accounts, nextTxs);
    setAccounts(nextAccounts);
    StorageService.saveAccounts(nextAccounts);

    // Automatically remember this merchant's ledger so future transactions automatically route to this ledger
    if (newTx.merchant && newTx.merchant !== 'Unknown Merchant' && newTx.accountId) {
      StorageService.rememberMerchantLedger(newTx.merchant, newTx.accountId, targetAccount?.name, newTx.category);
    }
  };

  // Wire Native Android Notification Interceptor Bridge
  useEffect(() => {
    // 1. Expose function for Android WebView evaluateJavascript bridge
    (window as any).onNativeBankNotificationReceived = (payload: any) => {
      if (!payload) return;
      const isIncome = payload.type === 'income';
      const parsedAmount = Number(payload.amount) || 0;
      const merchantName = payload.merchant || (isIncome ? 'Salary Deposit' : 'UAE Merchant');
      const isForeign = Boolean(payload.originalCurrency && payload.originalCurrency !== 'AED');

      handleRecordTransaction({
        amount: parsedAmount,
        originalAmount: payload.originalAmount ? Number(payload.originalAmount) : undefined,
        originalCurrency: payload.originalCurrency,
        exchangeRate: payload.exchangeRate ? Number(payload.exchangeRate) : undefined,
        currency: payload.currency || 'AED',
        merchant: merchantName,
        category: payload.category || (isIncome ? 'Salary' : 'Other'),
        bankName: payload.bankName || 'UAE Bank',
        type: payload.type || 'expense',
        isRedFlag: Boolean(payload.isRedFlag) || isForeign,
        redFlagReason: payload.redFlagReason,
        isVerifiedByUser: isForeign ? false : true,
        rawNotificationText: payload.rawNotificationText,
        source: 'auto_notification',
        date: payload.date || new Date().toISOString().split('T')[0],
        time: payload.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      });

      if (isIncome) {
        setToastMessage(`💰 Auto-Recorded Salary Deposit: AED ${parsedAmount.toFixed(2)} (${merchantName})`);
      } else if (isForeign) {
        setToastMessage(`🔴 International Alert: ${payload.originalCurrency} ${payload.originalAmount || ''} converted to AED ${parsedAmount.toFixed(2)} (Red-flagged pending review)`);
      } else {
        setToastMessage(`⚡ Auto-Caught Bank Alert: ${payload.currency || 'AED'} ${parsedAmount.toFixed(2)} at ${merchantName}`);
      }
      setTimeout(() => setToastMessage(null), 5000);
    };

    // 2. Custom DOM Event listener for automated simulation or internal triggers
    const handleCustomNotification = (e: any) => {
      if (e.detail && (window as any).onNativeBankNotificationReceived) {
        (window as any).onNativeBankNotificationReceived(e.detail);
      }
    };
    window.addEventListener('dirhamtrack:bank_notification', handleCustomNotification);

    return () => {
      delete (window as any).onNativeBankNotificationReceived;
      window.removeEventListener('dirhamtrack:bank_notification', handleCustomNotification);
    };
  }, [accounts]);

  const handleUpdateTransaction = (updated: Transaction) => {
    // Automatically remember this merchant's updated ledger
    if (updated.merchant && updated.accountId) {
      const targetAcc = accounts.find(a => a.id === updated.accountId);
      StorageService.rememberMerchantLedger(updated.merchant, updated.accountId, targetAcc?.name, updated.category);
    }

    const nextTxs = transactions.map(t => (t.id === updated.id ? updated : t));
    setTransactions(nextTxs);
    StorageService.saveTransactions(nextTxs);

    // Automatically recalculate and synchronize account balances
    const nextAccounts = StorageService.recalculateAccountBalances(accounts, nextTxs);
    setAccounts(nextAccounts);
    StorageService.saveAccounts(nextAccounts);
  };

  const handleDeleteTransaction = (id: string) => {
    const targetTx = transactions.find(t => t.id === id);
    if (!targetTx) return;

    const nextTxs = transactions.filter(t => t.id !== id);
    setTransactions(nextTxs);
    StorageService.saveTransactions(nextTxs);

    // Automatically recalculate and synchronize account balances
    const nextAccounts = StorageService.recalculateAccountBalances(accounts, nextTxs);
    setAccounts(nextAccounts);
    StorageService.saveAccounts(nextAccounts);

    const isCreditCard = accounts.find(a => a.id === targetTx.accountId)?.type === 'credit_card';
    setToastMessage(
      `🗑️ Deleted transaction of AED ${targetTx.amount.toFixed(2)}. ${
        isCreditCard ? 'Credit card outstanding balance reduced' : 'Bank balance adjusted'
      } automatically.`
    );
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleLearnCategory = (merchant: string, newCategory: ExpenseCategory) => {
    StorageService.addCorrection(merchant, newCategory);
  };

  const handleDisablePin = () => {
    StorageService.setPin(false, pinConfig.pin, pinConfig.autoLock, pinConfig.email || 'fmdsmb52@gmail.com', pinConfig.phone);
    setPinConfig({ enabled: false, pin: pinConfig.pin, autoLock: pinConfig.autoLock, email: pinConfig.email || 'fmdsmb52@gmail.com', phone: pinConfig.phone });
    setIsLocked(false);
    StorageService.setIsLocked(false);
    try {
      sessionStorage.removeItem(SESSION_ACTIVE_KEY);
    } catch {}
  };

  const handleUnlock = () => {
    setIsLocked(false);
    StorageService.setIsLocked(false);
    try {
      sessionStorage.setItem(SESSION_ACTIVE_KEY, 'true');
      const now = String(Date.now());
      sessionStorage.setItem(LAST_ACTIVE_KEY, now);
      localStorage.setItem(LAST_ACTIVE_KEY, now);
    } catch {}
  };

  const handleLockNow = () => {
    setIsLocked(true);
    StorageService.setIsLocked(true);
    try {
      sessionStorage.removeItem(SESSION_ACTIVE_KEY);
    } catch {}
  };

  const handleResetPin = (newPin: string, newEmail?: string) => {
    const updated = {
      ...pinConfig,
      pin: newPin,
      email: newEmail || pinConfig.email || 'fmdsmb52@gmail.com'
    };
    StorageService.setPin(updated.enabled, updated.pin, updated.autoLock, updated.email, updated.phone);
    setPinConfig(updated);
    handleUnlock();
    setToastMessage('Security PIN successfully reset via Resend Email OTP!');
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleAddAccount = (newAcc: Account) => {
    setAccounts(prev => [...prev, newAcc]);
    setToastMessage(`Added "${newAcc.name}" successfully!`);
    setTimeout(() => setToastMessage(null), 4000);
  };

  const handleClearAllData = () => {
    StorageService.clearAllData();
    setTransactions([]);
    setAccounts(DEFAULT_ACCOUNTS.map(a => ({ ...a, balance: 0.00, initialBalance: 0.00 })));
    setShowClearConfirm(false);
    setToastMessage('All transaction data cleared successfully! Your ledger is clean.');
    setTimeout(() => setToastMessage(null), 5000);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* PIN Lock Screen Overlay if locked */}
      {isLocked && (
        <PinLockScreen
          correctPin={pinConfig.pin}
          recoveryEmail={pinConfig.email || 'fmdsmb52@gmail.com'}
          recoveryPhone={pinConfig.phone}
          onUnlock={handleUnlock}
          onDisablePin={handleDisablePin}
          onResetPin={handleResetPin}
        />
      )}

      {/* Top Bar Navigation */}
      <Header
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenAddModal={() => setAddModalOpen(true)}
        onOpenReportModal={() => setReportModalOpen(true)}
        onOpenAndroidGuide={() => setAndroidGuideModalOpen(true)}
        onOpenAppGuide={() => setAppGuideModalOpen(true)}
        onOpenQrModal={() => setQrModalOpen(true)}
        onClearAllData={() => setShowClearConfirm(true)}
        onLockApp={handleLockNow}
        onOpenPinSettings={() => setPinSettingsModalOpen(true)}
        isPinEnabled={pinConfig.enabled}
        onOpenVoiceModal={() => setVoiceModalOpen(true)}
        onOpenFraudModal={() => setFraudModalOpen(true)}
        onOpenForecastModal={() => setForecastModalOpen(true)}
        onOpenAssistantModal={() => setAssistantModalOpen(true)}
      />

      {/* Notification Toast */}
      {toastMessage && (
        <div className="fixed top-20 right-4 z-50 p-3.5 bg-emerald-950/90 border border-emerald-500/40 rounded-xl text-emerald-200 text-xs shadow-xl animate-fade-in flex items-center gap-2">
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage(null)} className="text-emerald-400 hover:text-white font-bold ml-2">✕</button>
        </div>
      )}

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-3 sm:px-6 pt-3 sm:pt-5 pb-4">
        {activeTab === 'dashboard' && (
          <Dashboard
            transactions={transactions}
            accounts={accounts}
            budgets={budgets}
            onRecordTransaction={handleRecordTransaction}
            onOpenAndroidCode={() => setAndroidCodeModalOpen(true)}
            onOpenAndroidGuide={() => setAndroidGuideModalOpen(true)}
            onOpenAppGuide={() => setAppGuideModalOpen(true)}
            onOpenQrModal={() => setQrModalOpen(true)}
            onOpenAddModal={() => setAddModalOpen(true)}
            onOpenAddAccountModal={() => setAddAccountModalOpen(true)}
            onViewAllTransactions={(cat?: string) => {
              setSelectedFilterCategory(cat || 'all');
              setActiveTab('transactions');
            }}
            onUpdateTransaction={handleUpdateTransaction}
            onOpenVoiceModal={() => setVoiceModalOpen(true)}
            onOpenFraudModal={() => setFraudModalOpen(true)}
            onOpenForecastModal={() => setForecastModalOpen(true)}
            onOpenAssistantModal={() => setAssistantModalOpen(true)}
            onOpenKeyFeaturesModal={() => setKeyFeaturesModalOpen(true)}
          />
        )}

        {activeTab === 'transactions' && (
          <div className="space-y-4 sm:space-y-6">
            <TransactionList
              transactions={transactions}
              accounts={accounts}
              onUpdateTransaction={handleUpdateTransaction}
              onDeleteTransaction={handleDeleteTransaction}
              onLearnCategory={handleLearnCategory}
              initialCategory={selectedFilterCategory}
              onClearCategory={() => setSelectedFilterCategory('all')}
            />
          </div>
        )}

        {activeTab === 'budgets' && (
          <div className="space-y-4 sm:space-y-6">
            <BudgetManager
              budgets={budgets}
              transactions={transactions}
              onUpdateBudgets={setBudgets}
            />
          </div>
        )}

        {activeTab === 'accounts' && (
          <div className="space-y-4 sm:space-y-6">
            <AccountsManager
              accounts={accounts}
              transactions={transactions}
              onRecordTransaction={handleRecordTransaction}
              onUpdateAccounts={setAccounts}
              onUpdateTransactions={setTransactions}
              onOpenAddAccountModal={() => setAddAccountModalOpen(true)}
            />
          </div>
        )}

        {activeTab === 'subscriptions' && (
          <div className="space-y-4 sm:space-y-6">
            <SubscriptionsTracker
              subscriptions={subscriptions}
              onUpdateSubscriptions={setSubscriptions}
            />
          </div>
        )}
      </main>

      {/* Manual Add Transaction Modal */}
      {addModalOpen && (
        <AddTransactionModal
          accounts={accounts}
          onClose={() => setAddModalOpen(false)}
          onAddTransaction={handleRecordTransaction}
          onOpenAddAccountModal={() => {
            setAddModalOpen(false);
            setAddAccountModalOpen(true);
          }}
        />
      )}

      {/* Add Bank or Credit Card Modal */}
      {addAccountModalOpen && (
        <AddAccountModal
          onClose={() => setAddAccountModalOpen(false)}
          onAddAccount={handleAddAccount}
        />
      )}

      {/* Mobile QR Code Scanner Modal */}
      {qrModalOpen && (
        <MobileQRCodeModal onClose={() => setQrModalOpen(false)} />
      )}

      {/* Android & Python Source Code Modal */}
      {androidCodeModalOpen && (
        <AndroidCodeModal onClose={() => setAndroidCodeModalOpen(false)} />
      )}

      {/* Android Setup & Notification Guide Modal */}
      {androidGuideModalOpen && (
        <AndroidInstallGuideModal
          onClose={() => setAndroidGuideModalOpen(false)}
          onOpenCodeViewer={() => {
            setAndroidGuideModalOpen(false);
            setAndroidCodeModalOpen(true);
          }}
        />
      )}

      {/* Monthly Report & PDF Export Modal */}
      {reportModalOpen && (
        <MonthlyReportModal
          transactions={transactions}
          accounts={accounts}
          budgets={budgets}
          onClose={() => setReportModalOpen(false)}
        />
      )}

      {/* App Guide & Feature Overview Modal */}
      {appGuideModalOpen && (
        <AppGuideModal
          onClose={() => setAppGuideModalOpen(false)}
          onOpenAndroidGuide={() => {
            setAppGuideModalOpen(false);
            setAndroidGuideModalOpen(true);
          }}
        />
      )}

      {/* Security PIN Settings Modal */}
      {pinSettingsModalOpen && (
        <PinSettingsModal
          onClose={() => setPinSettingsModalOpen(false)}
          onLockNow={() => {
            handleLockNow();
            setPinSettingsModalOpen(false);
          }}
          onPinUpdated={newCfg => {
            setPinConfig(newCfg);
            if (newCfg.enabled) {
              setToastMessage('PIN Security Active: App is protected.');
            } else {
              setToastMessage('PIN Security turned off.');
            }
            setTimeout(() => setToastMessage(null), 3500);
          }}
        />
      )}

      {/* Clear Data Confirmation Dialog */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <h4 className="text-base font-bold text-white mb-2">Clear All Data?</h4>
            <p className="text-xs text-slate-300 leading-relaxed mb-5">
              This will reset all transactions to zero and reset account balances. Use this to start with a fresh, completely blank ledger.
            </p>
            <div className="flex gap-2.5">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleClearAllData}
                className="flex-1 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow transition"
              >
                Clear Everything
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modern App Footer with Developer Attribution */}
      <footer className="mt-4 border-t border-slate-800/80 bg-slate-950/95 pt-5 pb-28 sm:pb-6 text-xs text-slate-400">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-3.5 text-center sm:text-left">
          {/* Brand & Developer Badge - Centered, balanced, prominent */}
          <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2.5">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center font-bold text-xs">
                د.إ
              </div>
              <span className="font-bold text-white text-xs">DirhamTrack</span>
              <span className="text-slate-600 hidden sm:inline">•</span>
            </div>

            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-teal-500/40 shadow-xs">
              <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />
              <span className="text-slate-400 text-xs">Developed by</span>
              <span className="text-teal-300 font-bold text-xs tracking-wide">Fakhruddin</span>
            </div>
          </div>

          {/* Quick Links */}
          <div className="flex flex-wrap items-center justify-center gap-3.5 text-[11px] text-slate-400">
            <button
              onClick={() => setActiveTab('subscriptions')}
              className="hover:text-teal-300 transition cursor-pointer"
            >
              Recurring Bills
            </button>
            <button
              onClick={() => setReportModalOpen(true)}
              className="hover:text-teal-300 transition cursor-pointer"
            >
              Monthly Statement
            </button>
            <button
              onClick={handleLockNow}
              className="hover:text-teal-300 transition cursor-pointer"
            >
              Lock PIN
            </button>
          </div>
        </div>
      </footer>

      {/* AI Voice Expense Entry Modal */}
      {voiceModalOpen && (
        <VoiceExpenseModal
          accounts={accounts}
          onClose={() => setVoiceModalOpen(false)}
          onAddTransaction={(tx) => {
            handleRecordTransaction(tx);
            setToastMessage(`🎙️ Voice Expense Saved: AED ${(tx.amount || 0).toFixed(2)} at ${tx.merchant || 'Merchant'}`);
            setTimeout(() => setToastMessage(null), 4000);
          }}
        />
      )}

      {/* AI Fraud Detection Modal (Python Scikit-learn Isolation Forest) */}
      {fraudModalOpen && (
        <FraudDetectionModal
          transactions={transactions}
          accounts={accounts}
          onClose={() => setFraudModalOpen(false)}
          onVerifyTransaction={(txId) => {
            const tx = transactions.find(t => t.id === txId);
            if (tx) {
              handleUpdateTransaction({ ...tx, isVerifiedByUser: true, isRedFlag: false });
              setToastMessage(`🛡️ Transaction verified and marked safe.`);
              setTimeout(() => setToastMessage(null), 3000);
            }
          }}
          onReviewTransaction={(tx) => {
            setFraudModalOpen(false);
            setActiveTab('transactions');
          }}
        />
      )}

      {/* Predictive Budget & Cash Flow Modal (Python Statsmodels) */}
      {forecastModalOpen && (
        <PredictiveCashFlowModal
          transactions={transactions}
          budgets={budgets}
          accounts={accounts}
          subscriptions={subscriptions}
          onClose={() => setForecastModalOpen(false)}
        />
      )}

      {/* AI Finance Assistant Modal (Gemini AI) */}
      {assistantModalOpen && (
        <FinanceAssistantModal
          transactions={transactions}
          accounts={accounts}
          budgets={budgets}
          subscriptions={subscriptions}
          onClose={() => setAssistantModalOpen(false)}
        />
      )}

      {/* Key Features & Updates Modal */}
      {keyFeaturesModalOpen && (
        <KeyFeaturesModal
          onClose={() => setKeyFeaturesModalOpen(false)}
          onOpenVoiceModal={() => setVoiceModalOpen(true)}
          onOpenAssistantModal={() => setAssistantModalOpen(true)}
          onOpenForecastModal={() => setForecastModalOpen(true)}
        />
      )}

      {/* Floating Quick Voice Mic Button */}
      <button
        onClick={() => setVoiceModalOpen(true)}
        className="fixed bottom-24 sm:bottom-8 right-4 sm:right-8 z-40 w-12 h-12 sm:w-auto sm:px-4 sm:py-3 rounded-full bg-gradient-to-r from-teal-500 to-emerald-400 text-slate-950 font-bold text-xs shadow-xl shadow-teal-500/40 hover:scale-105 active:scale-95 transition flex items-center justify-center gap-2 cursor-pointer border-2 border-slate-950"
        style={{ bottom: 'max(6.25rem, calc(4.75rem + env(safe-area-inset-bottom, 0px)))' }}
        title="Voice Expense Entry"
        aria-label="Voice Expense Entry"
      >
        <Mic className="w-5 h-5 stroke-[2.5]" />
        <span className="hidden sm:inline">Voice Entry</span>
      </button>

      {/* Mobile Bottom Navigation Bar for Ergonomic Thumb Navigation */}
      <BottomNavBar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenAddModal={() => setAddModalOpen(true)}
      />
    </div>
  );
}
