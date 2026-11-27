import React, { useState } from 'react';
import {
  Search,
  Filter,
  ShieldAlert,
  CheckCircle,
  AlertOctagon,
  Edit2,
  Trash2,
  CreditCard,
  Building,
  Wallet,
  ArrowUpRight,
  ArrowDownLeft,
  RefreshCw,
  X,
  FileText,
  Sliders,
  Globe,
  ShieldCheck
} from 'lucide-react';
import { Account, ExpenseCategory, Transaction, TransactionType } from '../types/finance';
import { AlterForeignModal } from './AlterForeignModal';
import { cleanMerchantName, categorizeMerchant } from '../services/categorizer';
import { StorageService } from '../services/storage';
import { ReceiptScannerModal } from './ReceiptScannerModal';

interface TransactionListProps {
  transactions: Transaction[];
  accounts: Account[];
  onUpdateTransaction: (updated: Transaction) => void;
  onDeleteTransaction: (id: string) => void;
  onLearnCategory: (merchant: string, newCategory: ExpenseCategory) => void;
  initialCategory?: string;
  onClearCategory?: () => void;
}

/**
 * Strict Category Matching Rules Engine
 * Enforces exact category identity without cross-category bleed.
 * E.g., clicking 'Food' returns ONLY Food; 'Groceries' returns ONLY Groceries.
 */
export function matchesStrictCategory(
  transactionCategory: string | undefined | null,
  filterCategory: string | undefined | null
): boolean {
  if (!filterCategory || filterCategory.trim().toLowerCase() === 'all') return true;
  if (!transactionCategory) return false;

  const target = filterCategory.trim().toLowerCase();
  const actual = transactionCategory.trim().toLowerCase();

  // Strict exact match - zero cross-category bleeding
  return actual === target;
}

export function transactionMatchesCategory(
  tx: Transaction,
  filterCategory: string | undefined | null
): boolean {
  if (!filterCategory || filterCategory.trim().toLowerCase() === 'all') return true;

  // 1. Exact match on main category
  if (matchesStrictCategory(tx.category, filterCategory)) return true;

  // 2. Exact match on any itemized category split
  if (tx.categorySplits && tx.categorySplits.length > 0) {
    return tx.categorySplits.some(split => matchesStrictCategory(split.category, filterCategory));
  }

  return false;
}

export function getCategoryAttributedAmount(
  tx: Transaction,
  filterCategory: string | undefined | null
): number {
  if (!filterCategory || filterCategory.trim().toLowerCase() === 'all') {
    return tx.amount;
  }

  if (tx.categorySplits && tx.categorySplits.length > 0) {
    const matchingSplits = tx.categorySplits.filter(s => matchesStrictCategory(s.category, filterCategory));
    if (matchingSplits.length > 0) {
      return matchingSplits.reduce((sum, s) => sum + s.amount, 0);
    }
  }

  if (matchesStrictCategory(tx.category, filterCategory)) {
    return tx.amount;
  }

  return 0;
}

const DEFAULT_CATEGORIES: ExpenseCategory[] = [
  'Rent & Housing',
  'Food',
  'Groceries',
  'Petrol',
  'Utilities',
  'Telecom',
  'Shopping',
  'Transport',
  'Healthcare',
  'Entertainment',
  'Travel',
  'Education',
  'Salary',
  'Other'
];

export const TransactionList: React.FC<TransactionListProps> = ({
  transactions,
  accounts,
  onUpdateTransaction,
  onDeleteTransaction,
  onLearnCategory,
  initialCategory = 'all',
  onClearCategory
}) => {
  const [categoriesList, setCategoriesList] = useState<ExpenseCategory[]>(() =>
    StorageService.getAllExpenseCategories()
  );
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>(initialCategory || 'all');
  const [selectedAccountId, setSelectedAccountId] = useState<string>('all');
  const [filterOnlyRedFlags, setFilterOnlyRedFlags] = useState<boolean>(false);

  React.useEffect(() => {
    if (initialCategory) {
      setSelectedCategory(initialCategory);
    }
  }, [initialCategory]);

  // Security Review Modal State
  const [reviewTx, setReviewTx] = useState<Transaction | null>(null);

  // Alter Foreign Transaction Modal State
  const [alterTx, setAlterTx] = useState<Transaction | null>(null);

  // Edit Category Modal State
  const [editingCategoryTx, setEditingCategoryTx] = useState<Transaction | null>(null);
  const [newCategoryChoice, setNewCategoryChoice] = useState<ExpenseCategory>('Food');
  const [rememberForFuture, setRememberForFuture] = useState(true);

  // Edit Ledger / Account Modal State
  const [editingAccountTx, setEditingAccountTx] = useState<Transaction | null>(null);
  const [newAccountChoice, setNewAccountChoice] = useState<string>('');

  // Edit Merchant Modal State
  const [editingMerchantTx, setEditingMerchantTx] = useState<Transaction | null>(null);
  const [newMerchantName, setNewMerchantName] = useState('');
  const [newMerchantCategory, setNewMerchantCategory] = useState<ExpenseCategory>('Shopping');
  const [newMerchantAccountId, setNewMerchantAccountId] = useState('');
  const [rememberMerchantRule, setRememberMerchantRule] = useState(true);
  const [applyToMatchingUnknown, setApplyToMatchingUnknown] = useState(true);

  // Receipt Photo View State
  const [viewingReceipt, setViewingReceipt] = useState<string | null>(null);
  const [ocrTx, setOcrTx] = useState<Transaction | null>(null);

  // Edit Full Transaction Details Modal State
  const [editingDetailsTx, setEditingDetailsTx] = useState<Transaction | null>(null);
  const [editAmountStr, setEditAmountStr] = useState('');
  const [editMerchant, setEditMerchant] = useState('');
  const [editDateStr, setEditDateStr] = useState('');
  const [editNotesStr, setEditNotesStr] = useState('');
  const [editAccountId, setEditAccountId] = useState('');
  const [editType, setEditType] = useState<TransactionType>('expense');

  const openEditDetails = (tx: Transaction) => {
    setEditingDetailsTx(tx);
    setEditAmountStr(tx.amount.toString());
    setEditMerchant(tx.merchant);
    setEditDateStr(tx.date);
    setEditNotesStr(tx.notes || '');
    setEditAccountId(tx.accountId);
    setEditType(tx.type);
  };

  const handleSaveDetailsChange = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingDetailsTx) return;
    const parsedAmount = parseFloat(editAmountStr);
    if (isNaN(parsedAmount) || parsedAmount < 0) return;

    const targetAcc = accounts.find(a => a.id === editAccountId) || accounts[0];

    const updated: Transaction = {
      ...editingDetailsTx,
      amount: parsedAmount,
      merchant: editMerchant.trim() || editingDetailsTx.merchant,
      date: editDateStr || editingDetailsTx.date,
      notes: editNotesStr.trim() || undefined,
      accountId: editAccountId,
      type: editType,
      bankName: targetAcc?.bankName || targetAcc?.name
    };

    onUpdateTransaction(updated);
    setEditingDetailsTx(null);
  };

  const accountMap = new Map(accounts.map(a => [a.id, a]));

  const filtered = transactions.filter(t => {
    // Red flag filter
    if (filterOnlyRedFlags && !t.isRedFlag) return false;

    // Strict Category filter using rules engine
    if (selectedCategory !== 'all' && !transactionMatchesCategory(t, selectedCategory)) return false;

    // Account filter
    if (selectedAccountId !== 'all' && t.accountId !== selectedAccountId) return false;

    // Search filter
    if (searchTerm.trim()) {
      const q = searchTerm.toLowerCase();
      const matchMerchant = t.merchant.toLowerCase().includes(q);
      const matchBank = (t.bankName || '').toLowerCase().includes(q);
      const matchNotes = (t.notes || '').toLowerCase().includes(q);
      const matchAmount = t.amount.toString().includes(q);
      if (!matchMerchant && !matchBank && !matchNotes && !matchAmount) return false;
    }

    return true;
  });

  const filteredExpenseTotal = filtered
    .filter(t => t.type === 'expense')
    .reduce((s, t) => s + getCategoryAttributedAmount(t, selectedCategory), 0);
  const filteredIncomeTotal = filtered
    .filter(t => t.type === 'income')
    .reduce((s, t) => s + (matchesStrictCategory(t.category, selectedCategory) ? t.amount : 0), 0);

  const handleSaveCategoryChange = () => {
    if (!editingCategoryTx) return;
    const updated: Transaction = {
      ...editingCategoryTx,
      category: newCategoryChoice
    };
    onUpdateTransaction(updated);

    if (rememberForFuture) {
      onLearnCategory(editingCategoryTx.merchant, newCategoryChoice);
    }
    setEditingCategoryTx(null);
  };

  const handleSaveAccountChange = () => {
    if (!editingAccountTx || !newAccountChoice) return;
    const targetAcc = accounts.find(a => a.id === newAccountChoice);
    const updated: Transaction = {
      ...editingAccountTx,
      accountId: newAccountChoice,
      bankName: targetAcc?.bankName || targetAcc?.name
    };
    onUpdateTransaction(updated);
    setEditingAccountTx(null);
  };

  const openEditMerchantModal = (tx: Transaction) => {
    setEditingMerchantTx(tx);
    setNewMerchantName(tx.merchant === 'Unknown Merchant' ? '' : tx.merchant);
    setNewMerchantCategory(tx.category);
    setNewMerchantAccountId(tx.accountId);
    setRememberMerchantRule(true);
    setApplyToMatchingUnknown(true);
  };

  const handleMerchantInputChange = (val: string) => {
    setNewMerchantName(val);
    if (val.trim().length >= 2) {
      const suggested = categorizeMerchant(val);
      if (suggested !== 'Other') {
        setNewMerchantCategory(suggested);
      }
      const rememberedAccId = StorageService.findRememberedLedger(val, transactions);
      if (rememberedAccId) {
        setNewMerchantAccountId(rememberedAccId);
      }
    }
  };

  const handleSaveMerchantChange = () => {
    if (!editingMerchantTx || !newMerchantName.trim()) return;
    const cleanName = cleanMerchantName(newMerchantName.trim());
    const targetAcc = accounts.find(a => a.id === newMerchantAccountId) || accounts[0];

    const updated: Transaction = {
      ...editingMerchantTx,
      merchant: cleanName,
      category: newMerchantCategory,
      accountId: newMerchantAccountId || editingMerchantTx.accountId,
      bankName: targetAcc?.bankName || targetAcc?.name
    };
    onUpdateTransaction(updated);

    if (rememberMerchantRule && cleanName && cleanName !== 'Unknown Merchant') {
      StorageService.rememberMerchantLedger(
        cleanName,
        newMerchantAccountId || editingMerchantTx.accountId,
        targetAcc?.name,
        newMerchantCategory
      );
      onLearnCategory(cleanName, newMerchantCategory);
    }

    if (applyToMatchingUnknown) {
      const otherUnknowns = transactions.filter(
        t => t.id !== editingMerchantTx.id && t.merchant === 'Unknown Merchant' && t.accountId === editingMerchantTx.accountId
      );
      for (const other of otherUnknowns) {
        onUpdateTransaction({
          ...other,
          merchant: cleanName,
          category: newMerchantCategory,
          bankName: targetAcc?.bankName || targetAcc?.name
        });
      }
    }

    setEditingMerchantTx(null);
  };

  const handleConfirmGenuine = (tx: Transaction) => {
    onUpdateTransaction({
      ...tx,
      isVerifiedByUser: true,
      isRedFlag: false,
      redFlagReason: undefined,
      notes: (tx.notes ? tx.notes + ' | ' : '') + 'Confirmed genuine by user'
    });
  };

  const handleMarkSafe = (tx: Transaction) => {
    onUpdateTransaction({
      ...tx,
      isVerifiedByUser: true,
      isRedFlag: false,
      redFlagReason: undefined,
      notes: (tx.notes ? tx.notes + ' | ' : '') + 'Confirmed genuine by user'
    });
    setReviewTx(null);
  };

  const handleFlagDispute = (tx: Transaction) => {
    onUpdateTransaction({
      ...tx,
      isVerifiedByUser: false,
      notes: (tx.notes ? tx.notes + ' | ' : '') + 'Marked for bank dispute review'
    });
    setReviewTx(null);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg">
      {/* Title & Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Recent Transactions
            <span className="text-xs text-slate-400 font-normal">
              ({filtered.length} of {transactions.length})
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Real-time ledger with UAE merchant memory & red flag alerts
          </p>
        </div>

        {/* Filter Badges & Search */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Red Flag Quick Toggle Button */}
          <button
            onClick={() => setFilterOnlyRedFlags(!filterOnlyRedFlags)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${
              filterOnlyRedFlags
                ? 'bg-rose-500 text-white shadow-md shadow-rose-900/40'
                : 'bg-rose-950/40 border border-rose-800/50 text-rose-300 hover:bg-rose-900/40'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Red Flags {transactions.filter(t => t.isRedFlag).length > 0 && `(${transactions.filter(t => t.isRedFlag).length})`}</span>
          </button>

          {/* Account Filter */}
          <select
            value={selectedAccountId}
            onChange={e => setSelectedAccountId(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-teal-500"
          >
            <option value="all">All Accounts</option>
            {accounts.map(a => (
              <option key={a.id} value={a.id}>
                {a.name}
              </option>
            ))}
          </select>

          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={e => setSelectedCategory(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-xs text-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-teal-500"
          >
            <option value="all">All Categories</option>
            {categoriesList.map(c => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Search Input Box */}
      <div className="relative mb-4">
        <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          placeholder="Search by merchant, bank, notes or amount (e.g. Carrefour, ENOC, Steam)..."
          className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-teal-500 transition"
        />
      </div>

      {/* Active Strict Category Filter Banner */}
      {selectedCategory !== 'all' && (
        <div className="mb-4 p-3 rounded-2xl bg-teal-950/60 border border-teal-500/40 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 animate-fade-in shadow-md">
          <div className="flex items-center gap-2.5">
            <span className="w-2.5 h-2.5 rounded-full bg-teal-400 animate-pulse shrink-0" />
            <div>
              <span className="text-slate-300">
                Filtered Category:{' '}
                <strong className="text-white bg-teal-500/20 px-2 py-0.5 rounded-md border border-teal-500/30 font-bold uppercase tracking-wide">
                  {selectedCategory}
                </strong>
              </span>
              <span className="text-teal-300 ml-2 font-medium">
                • {filtered.length} transaction{filtered.length === 1 ? '' : 's'} • Total Spent:{' '}
                <strong className="text-rose-400 font-bold tabular-nums">
                  AED {filteredExpenseTotal.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                </strong>
                {filteredIncomeTotal > 0 && (
                  <span className="text-emerald-400 ml-1.5 font-bold tabular-nums">
                    (In: AED {filteredIncomeTotal.toLocaleString('en-AE', { minimumFractionDigits: 2 })})
                  </span>
                )}
              </span>
            </div>
          </div>
          <button
            onClick={() => {
              setSelectedCategory('all');
              if (onClearCategory) onClearCategory();
            }}
            className="px-3 py-1.5 bg-teal-500/20 hover:bg-teal-500/30 border border-teal-500/40 text-teal-200 rounded-xl text-xs font-bold transition cursor-pointer self-start sm:self-auto shrink-0 flex items-center gap-1"
          >
            <X className="w-3.5 h-3.5" />
            <span>Show All Transactions</span>
          </button>
        </div>
      )}

      {/* Transactions List */}
      <div className="divide-y divide-slate-800/80">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-slate-400">
            <p className="text-sm font-medium">No transactions recorded yet.</p>
            <p className="text-xs text-slate-500 mt-1">
              Paste a bank SMS / notification alert above or tap "+ Add Expense / Income" to record one.
            </p>
          </div>
        ) : (
          filtered.map(tx => {
            const acc = accountMap.get(tx.accountId);
            const isIncome = tx.type === 'income';
            const isTransfer = tx.type === 'transfer' || tx.type === 'card_payment';
            const isForeign = Boolean(
              (tx.originalCurrency && tx.originalCurrency !== 'AED') ||
              (tx.currency && tx.currency !== 'AED') ||
              tx.exchangeRate
            );

            return (
              <div
                key={tx.id}
                className="py-3 px-2 flex items-center justify-between hover:bg-slate-800/40 rounded-xl transition group"
              >
                {/* Left: Icon & Details */}
                <div className="flex items-center gap-3 min-w-0 pr-2">
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      tx.isRedFlag
                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        : isIncome
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : isTransfer
                        ? 'bg-sky-500/20 text-sky-400'
                        : 'bg-slate-800 text-slate-300'
                    }`}
                  >
                    {tx.isRedFlag ? (
                      <AlertOctagon className="w-5 h-5 text-rose-400 animate-pulse" />
                    ) : isIncome ? (
                      <ArrowDownLeft className="w-5 h-5" />
                    ) : isTransfer ? (
                      <RefreshCw className="w-4 h-4" />
                    ) : (
                      <CreditCard className="w-4 h-4" />
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <button
                        onClick={() => openEditMerchantModal(tx)}
                        className="text-xs font-bold text-white truncate max-w-[180px] sm:max-w-[260px] text-left hover:text-teal-300 transition cursor-pointer flex items-center gap-1.5 group/merchant"
                        title="Click to add or edit merchant name"
                      >
                        <span className={tx.merchant === 'Unknown Merchant' ? 'text-amber-300/90 italic underline decoration-dotted' : ''}>
                          {tx.merchant}
                        </span>
                        <span className="p-0.5 rounded bg-slate-850 hover:bg-slate-700 text-slate-400 group-hover/merchant:text-teal-400">
                          <Edit2 className="w-2.5 h-2.5" />
                        </span>
                      </button>

                      {/* Red Flag Alert Chip */}
                      {tx.isRedFlag && (
                        <button
                          onClick={() => setReviewTx(tx)}
                          className="flex items-center gap-1 text-[10px] font-bold text-rose-300 bg-rose-500/20 border border-rose-500/30 px-2 py-0.5 rounded-full hover:bg-rose-500/30 transition cursor-pointer"
                        >
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-400 animate-ping"></span>
                          <span>{tx.isVerifiedByUser ? 'Flag (Verified)' : '🔴 UNCONFIRMED RED FLAG'}</span>
                        </button>
                      )}

                      {/* Foreign Currency Badge */}
                      {isForeign && (
                        <span className="text-[10px] text-amber-300/90 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-md flex items-center gap-1 font-mono">
                          <Globe className="w-2.5 h-2.5 text-amber-400" />
                          <span>{tx.originalCurrency || 'USD'} {tx.originalAmount ? tx.originalAmount.toFixed(2) : ''}</span>
                        </span>
                      )}

                      {/* Alter button for foreign transactions */}
                      {isForeign && (
                        <button
                          onClick={() => setAlterTx(tx)}
                          className="flex items-center gap-1 text-[10px] font-semibold text-teal-300 bg-teal-500/10 hover:bg-teal-500/20 border border-teal-500/30 px-2 py-0.5 rounded-md transition cursor-pointer"
                          title="Alter foreign amount, exchange rate, or AED conversion"
                        >
                          <Sliders className="w-2.5 h-2.5 text-teal-400" />
                          <span>Alter</span>
                        </button>
                      )}

                      {/* Confirm Genuine quick button if unconfirmed foreign red flag */}
                      {isForeign && (tx.isRedFlag || !tx.isVerifiedByUser) && (
                        <button
                          onClick={() => handleConfirmGenuine(tx)}
                          className="flex items-center gap-1 text-[10px] font-bold text-emerald-300 bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 px-2 py-0.5 rounded-md transition cursor-pointer"
                          title="Confirm genuine international transaction and clear red flag"
                        >
                          <ShieldCheck className="w-3 h-3 text-emerald-400" />
                          <span>Confirm Genuine</span>
                        </button>
                      )}

                      {/* Category Click-to-edit badge */}
                      <button
                        onClick={() => {
                          setEditingCategoryTx(tx);
                          setNewCategoryChoice(tx.category);
                        }}
                        className="text-[11px] text-teal-300/90 bg-teal-500/10 hover:bg-teal-500/20 px-2 py-0.5 rounded-md flex items-center gap-1 border border-teal-500/20 transition cursor-pointer"
                        title="Click to edit category and update AI memory"
                      >
                        <span>{tx.category}</span>
                        <Edit2 className="w-2.5 h-2.5 text-teal-400" />
                      </button>

                      {/* Receipt Scanner / View Split Items Button */}
                      <button
                        onClick={() => setOcrTx(tx)}
                        className={`flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-md transition cursor-pointer border ${
                          tx.hasReceipt || (tx.categorySplits && tx.categorySplits.length > 0)
                            ? 'bg-emerald-950/60 text-emerald-300 border-emerald-500/30 hover:bg-emerald-900/60'
                            : 'bg-slate-800/80 text-slate-300 border-slate-700 hover:text-white hover:bg-slate-700'
                        }`}
                        title={tx.hasReceipt ? "View attached receipt & item breakdown" : "Scan receipt / bill to itemize (OCR)"}
                      >
                        <FileText className="w-2.5 h-2.5 text-emerald-400" />
                        <span>{tx.hasReceipt ? `Receipt (${tx.items?.length || 'Items'})` : '+ Receipt'}</span>
                      </button>

                      {/* Receipt Photo Thumbnail Button if attached */}
                      {tx.receiptImage && (
                        <button
                          onClick={() => setViewingReceipt(tx.receiptImage || null)}
                          className="flex items-center gap-1 text-[10px] text-sky-300 bg-sky-950/60 border border-sky-500/30 px-2 py-0.5 rounded-md hover:bg-sky-900/50 transition cursor-pointer"
                          title="View attached receipt image"
                        >
                          <FileText className="w-2.5 h-2.5" />
                          <span>Photo</span>
                        </button>
                      )}
                    </div>

                    {/* Category Splits Display if multiple categories allocated */}
                    {tx.categorySplits && tx.categorySplits.length > 1 && (
                      <div className="flex items-center gap-1.5 flex-wrap mt-1">
                        <span className="text-[9px] font-bold uppercase text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-1.5 py-0.5 rounded">
                          Split Allocated:
                        </span>
                        {tx.categorySplits.map(s => (
                          <span
                            key={s.category}
                            className="text-[10px] font-medium text-slate-200 bg-slate-950 border border-slate-800 px-1.5 py-0.5 rounded flex items-center gap-1"
                          >
                            <span>{s.category}:</span>
                            <span className="text-emerald-400 font-bold tabular-nums">AED {s.amount.toFixed(2)}</span>
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-1 flex-wrap">
                      <span>{tx.date}</span>
                      {tx.time && <span>· {tx.time}</span>}
                      <span>·</span>
                      <button
                        onClick={() => {
                          setEditingAccountTx(tx);
                          setNewAccountChoice(tx.accountId);
                        }}
                        className="text-slate-300 hover:text-teal-300 flex items-center gap-1 transition cursor-pointer px-1 py-0.5 rounded hover:bg-slate-800"
                        title="Click to assign ledger (will remember for next time)"
                      >
                        <span className="underline decoration-dotted underline-offset-2">{acc?.name || tx.bankName || 'Cash'}</span>
                        <Edit2 className="w-2.5 h-2.5 text-slate-500 hover:text-teal-400" />
                      </button>
                      {acc?.accountNumberMasked && (
                        <span>({acc.accountNumberMasked})</span>
                      )}
                      {tx.source === 'auto_notification' && (
                        <span className="text-[10px] text-sky-400 font-medium">· Auto</span>
                      )}
                      {tx.notes && (
                        <span
                          className={`text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 ${
                            tx.notes.includes('Push & SMS') || tx.notes.includes('Duplicate avoided')
                              ? 'bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-semibold'
                              : 'text-slate-400 bg-slate-800/60'
                          }`}
                          title={tx.notes}
                        >
                          {(tx.notes.includes('Push & SMS') || tx.notes.includes('Duplicate avoided')) && (
                            <CheckCircle className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
                          )}
                          <span>
                            {tx.notes.includes('Push & SMS')
                              ? 'Verified (Push + SMS Corroborated)'
                              : tx.notes}
                          </span>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Amount & Actions */}
                <div className="flex items-center gap-2.5 shrink-0 text-right">
                  <div
                    onClick={() => openEditDetails(tx)}
                    className="cursor-pointer hover:opacity-80 transition"
                    title="Click to edit amount & details"
                  >
                    <div
                      className={`text-sm font-bold tabular-nums ${
                        tx.isRedFlag
                          ? 'text-rose-400'
                          : isIncome
                          ? 'text-emerald-400'
                          : 'text-white'
                      }`}
                    >
                      {isIncome ? '+' : isTransfer ? '' : '-'} AED {(selectedCategory !== 'all' ? getCategoryAttributedAmount(tx, selectedCategory) : tx.amount).toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                    </div>

                    {selectedCategory !== 'all' && tx.categorySplits && tx.categorySplits.length > 0 && getCategoryAttributedAmount(tx, selectedCategory) !== tx.amount && (
                      <div className="text-[10px] text-teal-400 font-semibold tabular-nums">
                        (of AED {tx.amount.toFixed(2)} total)
                      </div>
                    )}

                    {tx.originalAmount && tx.originalCurrency && (
                      <div className="text-[10px] text-slate-400 tabular-nums">
                        ({tx.originalCurrency} {tx.originalAmount.toFixed(2)}{tx.exchangeRate ? ` @ ${tx.exchangeRate}` : ''})
                      </div>
                    )}
                  </div>

                  <button
                    onClick={() => openEditDetails(tx)}
                    className="p-1.5 text-slate-500 hover:text-teal-300 transition cursor-pointer opacity-70 group-hover:opacity-100"
                    title="Edit transaction amount & details"
                  >
                    <Edit2 className="w-3.5 h-3.5" />
                  </button>

                  <button
                    onClick={() => onDeleteTransaction(tx.id)}
                    className="p-1.5 text-slate-500 hover:text-rose-400 transition cursor-pointer opacity-70 group-hover:opacity-100"
                    title="Delete transaction and recalculate balance"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Modal: Red Flag Safety Review */}
      {reviewTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-slate-900 border border-rose-500/30 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/20 text-rose-400 flex items-center justify-center">
                  <ShieldAlert className="w-6 h-6" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-white">🔴 International Alert Review</h4>
                  <p className="text-xs text-rose-300">Potential anomaly or foreign transaction</p>
                </div>
              </div>
              <button
                onClick={() => setReviewTx(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-slate-950 rounded-xl p-3.5 border border-slate-800 mb-4 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Merchant:</span>
                <span className="text-white font-bold">{reviewTx.merchant}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Amount AED:</span>
                <span className="text-rose-400 font-bold tabular-nums">AED {reviewTx.amount.toFixed(2)}</span>
              </div>
              {reviewTx.originalAmount && (
                <div className="flex justify-between">
                  <span className="text-slate-400">Foreign Value:</span>
                  <span className="text-slate-200 tabular-nums">
                    {reviewTx.originalCurrency} {reviewTx.originalAmount.toFixed(2)}
                  </span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-slate-400">Bank Source:</span>
                <span className="text-slate-200">{reviewTx.bankName}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Detection Reason:</span>
                <span className="text-rose-300 font-medium text-right max-w-[220px]">
                  {reviewTx.redFlagReason || 'Foreign currency outside UAE.'}
                </span>
              </div>
              {reviewTx.rawNotificationText && (
                <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400 italic">
                  "{reviewTx.rawNotificationText}"
                </div>
              )}
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <button
                onClick={() => {
                  const t = reviewTx;
                  setReviewTx(null);
                  setAlterTx(t);
                }}
                className="py-2.5 px-3 bg-slate-800 hover:bg-slate-750 text-teal-300 font-semibold text-xs rounded-xl border border-slate-700 transition flex items-center justify-center gap-1.5 cursor-pointer"
                title="Alter original currency amount, bank exchange rate markup, or AED conversion"
              >
                <Sliders className="w-3.5 h-3.5 text-teal-400" />
                <span>Alter FX / Rate</span>
              </button>
              <button
                onClick={() => handleMarkSafe(reviewTx)}
                className="flex-1 py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer"
              >
                <CheckCircle className="w-4 h-4" />
                <span>Confirm Genuine</span>
              </button>
              <button
                onClick={() => handleFlagDispute(reviewTx)}
                className="py-2.5 px-3 bg-slate-800 hover:bg-slate-700 text-rose-400 font-semibold text-xs rounded-xl transition cursor-pointer"
              >
                Dispute
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Edit Category & Memorize Rule */}
      {editingCategoryTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-base font-bold text-white">Edit Category</h4>
              <button
                onClick={() => setEditingCategoryTx(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 mb-3">
              Change category for <strong className="text-teal-300">{editingCategoryTx.merchant}</strong>:
            </p>

            <div className="grid grid-cols-2 gap-2 max-h-56 overflow-y-auto mb-4 p-1">
              {categoriesList.map(cat => (
                <button
                  key={cat}
                  onClick={() => setNewCategoryChoice(cat)}
                  className={`py-2 px-3 rounded-lg text-xs font-semibold text-left transition cursor-pointer truncate ${
                    newCategoryChoice === cat
                      ? 'bg-teal-500 text-slate-950 font-bold'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Remember rule toggle */}
            <label className="flex items-center gap-2.5 mb-5 cursor-pointer bg-slate-950 p-2.5 rounded-xl border border-slate-800">
              <input
                type="checkbox"
                checked={rememberForFuture}
                onChange={e => setRememberForFuture(e.target.checked)}
                className="w-4 h-4 text-teal-500 rounded focus:ring-0 focus:outline-none"
              />
              <span className="text-xs text-slate-300">
                Remember this rule for all future transactions from{' '}
                <span className="text-teal-400 font-medium">{editingCategoryTx.merchant}</span>
              </span>
            </label>

            <button
              onClick={handleSaveCategoryChange}
              className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs rounded-xl transition cursor-pointer"
            >
              Save & Apply
            </button>
          </div>
        </div>
      )}

      {/* Modal: Edit Ledger / Account */}
      {editingAccountTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                <span>Assign Ledger Account</span>
              </h4>
              <button
                onClick={() => setEditingAccountTx(null)}
                className="p-1 text-slate-400 hover:text-white cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-300 mb-3 leading-relaxed">
              Assign <strong className="text-teal-300">{editingAccountTx.merchant}</strong> to a ledger account. The app will <strong>automatically remember</strong> this ledger for next time!
            </p>

            <div className="space-y-2 mb-4 max-h-60 overflow-y-auto">
              {accounts.map(acc => (
                <button
                  key={acc.id}
                  onClick={() => setNewAccountChoice(acc.id)}
                  className={`w-full py-2.5 px-3 rounded-xl text-xs font-semibold text-left transition cursor-pointer flex items-center justify-between border ${
                    newAccountChoice === acc.id
                      ? 'bg-teal-500/20 border-teal-500 text-teal-300'
                      : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="font-bold">{acc.name}</div>
                    <div className="text-[10px] text-slate-400">{acc.accountNumberMasked || acc.type}</div>
                  </div>
                  {newAccountChoice === acc.id && (
                    <span className="text-[10px] font-bold text-teal-400 bg-teal-500/10 px-2 py-0.5 rounded border border-teal-500/30">
                      Selected
                    </span>
                  )}
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setEditingAccountTx(null)}
                className="flex-1 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveAccountChange}
                className="flex-1 py-2 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold shadow cursor-pointer"
              >
                Save &amp; Remember
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Receipt Photo Full View */}
      {viewingReceipt && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-4 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-bold text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-teal-400" />
                Attached Receipt Photo
              </h4>
              <button
                onClick={() => setViewingReceipt(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="max-h-[70vh] overflow-auto rounded-xl border border-slate-800 bg-black flex items-center justify-center p-2">
              <img
                src={viewingReceipt}
                alt="Receipt"
                className="max-h-[65vh] w-auto object-contain rounded-lg"
              />
            </div>
            <div className="mt-3 flex justify-end">
              <button
                onClick={() => setViewingReceipt(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-xl"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Edit Merchant Name & Ledger Memory */}
      {editingMerchantTx && (() => {
        const matchingUnknownCount = transactions.filter(
          t => t.id !== editingMerchantTx.id && t.merchant === 'Unknown Merchant' && t.accountId === editingMerchantTx.accountId
        ).length;

        const quickSuggestions = ['Amazon', 'Noon', 'Carrefour', 'Lulu', 'Talabat', 'Deliveroo', 'ENOC', 'ADNOC', 'DEWA', 'Etisalat'];

        return (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in overflow-y-auto">
            <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl my-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
                    <Edit2 className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="text-base font-bold text-white">Edit Merchant Name</h4>
                    <p className="text-[11px] text-slate-400">Update merchant &amp; teach automatic ledger memory</p>
                  </div>
                </div>
                <button
                  onClick={() => setEditingMerchantTx(null)}
                  className="p-1 text-slate-400 hover:text-white cursor-pointer"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Show raw bank notification text if available so user knows the exact context */}
              {editingMerchantTx.rawNotificationText && (
                <div className="p-2.5 mb-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400">
                  <span className="text-slate-500 font-semibold block text-[10px] uppercase tracking-wider mb-1">
                    Captured Bank Alert:
                  </span>
                  <p className="italic text-slate-300 line-clamp-3">
                    "{editingMerchantTx.rawNotificationText}"
                  </p>
                </div>
              )}

              <div className="space-y-3.5 text-xs">
                {/* Merchant Name Input */}
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Merchant Name:
                  </label>
                  <input
                    type="text"
                    value={newMerchantName}
                    onChange={e => handleMerchantInputChange(e.target.value)}
                    placeholder="e.g. Amazon, Carrefour, Lulu, ENOC Petrol..."
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2.5 text-white font-medium focus:outline-none focus:border-teal-500"
                    autoFocus
                  />
                </div>

                {/* Quick suggestion chips */}
                <div>
                  <span className="text-[10px] text-slate-400 uppercase tracking-wider block mb-1.5 font-semibold">
                    Quick Suggestions:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {quickSuggestions.map(sug => (
                      <button
                        key={sug}
                        type="button"
                        onClick={() => handleMerchantInputChange(sug)}
                        className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold border transition cursor-pointer ${
                          newMerchantName.toLowerCase() === sug.toLowerCase()
                            ? 'bg-teal-500 text-slate-950 border-teal-500 font-bold'
                            : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                        }`}
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Ledger Account Selection */}
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Assigned Ledger Account:
                  </label>
                  <select
                    value={newMerchantAccountId}
                    onChange={e => setNewMerchantAccountId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-medium focus:border-teal-500 focus:outline-none"
                  >
                    {accounts.map(acc => (
                      <option key={acc.id} value={acc.id}>
                        {acc.name} ({acc.accountNumberMasked || acc.type})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Category Selection */}
                <div>
                  <label className="block text-slate-300 font-semibold mb-1">
                    Expense Category:
                  </label>
                  <select
                    value={newMerchantCategory}
                    onChange={e => setNewMerchantCategory(e.target.value as ExpenseCategory)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-medium focus:border-teal-500 focus:outline-none"
                  >
                    {categoriesList.map(c => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Remember Rule Toggle */}
                <label className="flex items-start gap-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={rememberMerchantRule}
                    onChange={e => setRememberMerchantRule(e.target.checked)}
                    className="w-4 h-4 text-teal-500 rounded mt-0.5"
                  />
                  <div>
                    <span className="font-semibold text-white block">
                      ⚡ Automatically remember for next time
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Future transactions from this merchant will automatically route to this ledger account and category.
                    </span>
                  </div>
                </label>

                {/* Batch update other unknown transactions if present */}
                {matchingUnknownCount > 0 && (
                  <label className="flex items-start gap-2.5 p-3 rounded-xl bg-teal-950/30 border border-teal-500/30 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={applyToMatchingUnknown}
                      onChange={e => setApplyToMatchingUnknown(e.target.checked)}
                      className="w-4 h-4 text-teal-500 rounded mt-0.5"
                    />
                    <div>
                      <span className="font-bold text-teal-300 block">
                        Apply to {matchingUnknownCount} other Unknown transaction(s)
                      </span>
                      <span className="text-[11px] text-teal-200/70">
                        Also rename the other {matchingUnknownCount} "Unknown Merchant" transaction(s) on this card to "{newMerchantName || 'this merchant'}".
                      </span>
                    </div>
                  </label>
                )}
              </div>

              <div className="flex gap-2.5 mt-5">
                <button
                  type="button"
                  onClick={() => setEditingMerchantTx(null)}
                  className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleSaveMerchantChange}
                  disabled={!newMerchantName.trim()}
                  className="flex-1 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 text-xs font-bold shadow transition cursor-pointer"
                >
                  Save &amp; Update Ledger
                </button>
              </div>
            </div>
          </div>
        );
      })()}

      {/* Modal: Alter Foreign Transaction */}
      {alterTx && (
        <AlterForeignModal
          transaction={alterTx}
          accounts={accounts}
          onClose={() => setAlterTx(null)}
          onSave={updated => {
            onUpdateTransaction(updated);
            setAlterTx(null);
          }}
        />
      )}

      {/* Modal: Edit Transaction Amount & Details */}
      {editingDetailsTx && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in">
          <form
            onSubmit={handleSaveDetailsChange}
            className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl my-6"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center">
                  <Edit2 className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-base font-bold text-white">Edit Transaction &amp; Balance</h4>
                  <p className="text-xs text-slate-400">Balances update automatically upon saving</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setEditingDetailsTx(null)}
                className="p-1 text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3.5 text-xs mb-5">
              <div>
                <label className="block text-slate-400 mb-1">Merchant / Description:</label>
                <input
                  type="text"
                  value={editMerchant}
                  onChange={e => setEditMerchant(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-white font-medium focus:outline-none focus:border-teal-500"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Amount (AED):</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={editAmountStr}
                    onChange={e => setEditAmountStr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3.5 py-2 text-white font-bold font-mono focus:outline-none focus:border-teal-500"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Type:</label>
                  <select
                    value={editType}
                    onChange={e => setEditType(e.target.value as TransactionType)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-teal-500"
                  >
                    <option value="expense">Expense</option>
                    <option value="income">Income / Deposit</option>
                    <option value="card_payment">Credit Card Payment</option>
                    <option value="transfer">Account Transfer</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Account / Ledger:</label>
                <select
                  value={editAccountId}
                  onChange={e => setEditAccountId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-medium focus:outline-none focus:border-teal-500"
                >
                  {accounts.map(acc => (
                    <option key={acc.id} value={acc.id}>
                      {acc.name} ({acc.accountNumberMasked}) - {acc.type === 'credit_card' ? 'Credit Card' : 'Bank/Cash'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Date:</label>
                  <input
                    type="date"
                    value={editDateStr}
                    onChange={e => setEditDateStr(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 mb-1">Notes / Verification:</label>
                  <input
                    type="text"
                    value={editNotesStr}
                    onChange={e => setEditNotesStr(e.target.value)}
                    placeholder="Optional notes"
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-teal-500"
                  />
                </div>
              </div>

              <div className="p-3 bg-teal-950/30 border border-teal-500/20 rounded-xl text-[11px] text-teal-300">
                <span className="font-bold">⚡ Ledger Auto-Rebalance:</span> Changing amount or account will immediately adjust the outstanding card balance or available bank balance without double counting.
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setEditingDetailsTx(null)}
                className="flex-1 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex-1 py-2.5 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold shadow cursor-pointer transition"
              >
                Save &amp; Update Balance
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Receipt Scanner / Itemizer Modal */}
      {ocrTx && (
        <ReceiptScannerModal
          existingTransaction={ocrTx}
          initialMerchant={ocrTx.merchant}
          initialAmount={ocrTx.amount}
          onClose={() => setOcrTx(null)}
          onSaveReceiptData={(result) => {
            onUpdateTransaction({
              ...ocrTx,
              amount: result.amount,
              merchant: result.merchant,
              date: result.date,
              items: result.items,
              categorySplits: result.categorySplits,
              hasReceipt: true,
              receiptImage: result.receiptImage,
              category: result.categorySplits.length > 1 ? result.categorySplits[0].category : ocrTx.category,
              notes: (ocrTx.notes ? ocrTx.notes.split(' | Receipt OCR')[0] : '') + ` | Receipt OCR: ${result.categorySplits.map(s => `${s.category} AED ${s.amount.toFixed(2)}`).join(', ')}`
            });
            setOcrTx(null);
          }}
        />
      )}
    </div>
  );
};
