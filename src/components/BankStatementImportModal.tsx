import React, { useState, useRef } from 'react';
import {
  X,
  Upload,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Building,
  CreditCard,
  Wallet,
  Sparkles,
  ArrowRight,
  Filter,
  RefreshCw,
  Sliders,
  TrendingDown,
  TrendingUp,
  Info,
  Check,
  ChevronDown
} from 'lucide-react';
import {
  Account,
  ExpenseCategory,
  ExtractedStatementTransaction,
  StatementExtractionResult,
  Transaction,
  TransactionType
} from '../types/finance';
import { StatementService } from '../services/statementService';

interface BankStatementImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  accounts: Account[];
  transactions: Transaction[];
  onTransactionsImported: (updatedAccounts: Account[], newTransactions: Transaction[]) => void;
}

const CATEGORY_OPTIONS: ExpenseCategory[] = [
  'Food & Groceries',
  'Food',
  'Groceries',
  'Fuel',
  'Clothing',
  'Utilities',
  'Telecom',
  'Transport',
  'Shopping',
  'Healthcare',
  'Entertainment',
  'Travel',
  'Education',
  'Rent & Housing',
  'Salary',
  'Other'
];

export const BankStatementImportModal: React.FC<BankStatementImportModalProps> = ({
  isOpen,
  onClose,
  accounts,
  transactions,
  onTransactionsImported
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedAccountTargetId, setSelectedAccountTargetId] = useState<string>(
    accounts[0]?.id || ''
  );
  const [bankHint, setBankHint] = useState<string>('Emirates NBD');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [processingStep, setProcessingStep] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Extraction & Preview state
  const [extractedData, setExtractedData] = useState<StatementExtractionResult | null>(null);
  const [editableTransactions, setEditableTransactions] = useState<
    ExtractedStatementTransaction[]
  >([]);
  const [filterType, setFilterType] = useState<'all' | 'new' | 'duplicates' | 'flagged'>('all');
  const [learnedCount, setLearnedCount] = useState<number>(0);
  const [postedSuccess, setPostedSuccess] = useState<number | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setErrorMessage(null);
    }
  };

  const processExtractedResult = (rawResult: StatementExtractionResult) => {
    // Apply multi-attribute duplicate shield
    const shieldedTxs = StatementService.applyDuplicateShield(
      rawResult.transactions,
      transactions
    );

    // Auto-select target account if bank name matches
    if (rawResult.bankName) {
      const detected = rawResult.bankName.toLowerCase();
      const match = accounts.find(
        a =>
          a.name.toLowerCase().includes(detected) ||
          (a.bankName && a.bankName.toLowerCase().includes(detected))
      );
      if (match) {
        setSelectedAccountTargetId(match.id);
      }
    }

    setExtractedData(rawResult);
    setEditableTransactions(shieldedTxs);
  };

  const handleStartExtraction = async () => {
    if (!selectedFile) {
      setErrorMessage('Please select a PDF, Excel (.xlsx, .xls), or CSV bank statement file.');
      return;
    }

    setIsProcessing(true);
    setErrorMessage(null);
    setProcessingStep('Uploading statement to secure AI Document reader...');

    try {
      setProcessingStep('Extracting transaction tables, dates & amounts via Gemini AI...');
      const result = await StatementService.parseStatement(
        selectedFile,
        bankHint,
        accounts
      );

      setProcessingStep('Executing Python Rules Engine & mathematical reconciliation...');
      processExtractedResult(result);
      setProcessingStep('');
    } catch (err: any) {
      console.error('Extraction error:', err);
      setErrorMessage(err.message || 'Failed to extract bank statement. Please try another file or test with sample.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleLoadSample = (sampleIndex: number) => {
    const samples = StatementService.getSampleStatements();
    const chosen = samples[sampleIndex];
    if (!chosen) return;

    setIsProcessing(true);
    setErrorMessage(null);
    setProcessingStep(`Loading ${chosen.name}...`);

    setTimeout(() => {
      processExtractedResult(chosen.data);
      setIsProcessing(false);
      setProcessingStep('');
    }, 600);
  };

  // Toggle single transaction selection
  const handleToggleSelect = (id: string) => {
    setEditableTransactions(prev =>
      prev.map(tx => (tx.id === id ? { ...tx, selected: !tx.selected } : tx))
    );
  };

  // Change category and trigger AI learning
  const handleCategoryChange = (id: string, newCategory: ExpenseCategory) => {
    setEditableTransactions(prev =>
      prev.map(tx => (tx.id === id ? { ...tx, selectedCategory: newCategory } : tx))
    );
    setLearnedCount(prev => prev + 1);
  };

  // Change merchant name
  const handleMerchantChange = (id: string, newMerchant: string) => {
    setEditableTransactions(prev =>
      prev.map(tx => (tx.id === id ? { ...tx, merchant: newMerchant } : tx))
    );
  };

  // Change date
  const handleDateChange = (id: string, newDate: string) => {
    setEditableTransactions(prev =>
      prev.map(tx => (tx.id === id ? { ...tx, date: newDate } : tx))
    );
  };

  // Quick selection helpers
  const handleSelectAll = (select: boolean) => {
    setEditableTransactions(prev => prev.map(tx => ({ ...tx, selected: select })));
  };

  const handleExcludeDuplicates = () => {
    setEditableTransactions(prev =>
      prev.map(tx => (tx.isDuplicate ? { ...tx, selected: false } : tx))
    );
  };

  // Final posting action
  const handlePostTransactions = () => {
    const approved = editableTransactions.filter(tx => tx.selected);
    if (approved.length === 0) {
      alert('Please select at least one transaction to post.');
      return;
    }

    if (!selectedAccountTargetId) {
      alert('Please select an account to post these transactions into.');
      return;
    }

    const { updatedAccounts, newTransactions, postedCount } =
      StatementService.postTransactionsToLedger(
        approved,
        selectedAccountTargetId,
        accounts,
        transactions
      );

    setPostedSuccess(postedCount);
    onTransactionsImported(updatedAccounts, newTransactions);
  };

  // Filtering displayed rows
  const filteredList = editableTransactions.filter(tx => {
    if (filterType === 'new') return !tx.isDuplicate;
    if (filterType === 'duplicates') return tx.isDuplicate;
    if (filterType === 'flagged') return tx.isSuspicious;
    return true;
  });

  const selectedCount = editableTransactions.filter(tx => tx.selected).length;
  const duplicateCount = editableTransactions.filter(tx => tx.isDuplicate).length;
  const flaggedCount = editableTransactions.filter(tx => tx.isSuspicious).length;
  const selectedTotalDebit = editableTransactions
    .filter(tx => tx.selected && tx.type === 'expense')
    .reduce((s, tx) => s + tx.amount, 0);

  const targetAccountObj = accounts.find(a => a.id === selectedAccountTargetId);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-3 sm:p-4 overflow-y-auto animate-fade-in">
      <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden my-4 sm:my-6 flex flex-col max-h-[92vh]">
        {/* Modal Top Header */}
        <div className="p-4 sm:p-5 bg-slate-950 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-2xl bg-teal-500/20 text-teal-400 border border-teal-500/30 flex items-center justify-center shrink-0">
              <FileSpreadsheet className="w-5 h-5 sm:w-6 sm:h-6" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-base sm:text-lg font-bold text-white tracking-tight">
                  AI Bank Statement Import &amp; Reconciliation
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-500/15 text-teal-300 border border-teal-500/30">
                  UAE Banks • Auto-Post
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Upload PDF, Excel (.xlsx), or CSV from Emirates NBD, ADCB, FAB, Mashreq &amp; RAKBANK
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
          {/* Success Screen after posting */}
          {postedSuccess !== null ? (
            <div className="text-center py-10 px-4 space-y-4">
              <div className="w-16 h-16 rounded-full bg-teal-500/20 text-teal-400 border border-teal-500/30 mx-auto flex items-center justify-center">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <h4 className="text-xl font-black text-white">
                {postedSuccess} Transactions Successfully Posted!
              </h4>
              <p className="text-xs sm:text-sm text-slate-400 max-w-md mx-auto">
                Transactions have been accurately posted to{' '}
                <strong className="text-teal-400 font-semibold">{targetAccountObj?.name}</strong>.
                Account balances, charts, categories, and cash flow forecasts have updated
                automatically.
              </p>
              {learnedCount > 0 && (
                <div className="inline-flex items-center gap-1.5 text-xs text-teal-300 bg-teal-950/60 border border-teal-500/30 px-3 py-1.5 rounded-xl">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI learned {learnedCount} merchant category corrections for future auto-classification</span>
                </div>
              )}
              <div className="pt-3">
                <button
                  onClick={onClose}
                  className="px-6 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 font-bold text-xs sm:text-sm rounded-xl transition cursor-pointer shadow-lg"
                >
                  View Updated Ledger &amp; Dashboard
                </button>
              </div>
            </div>
          ) : !extractedData ? (
            /* Upload & File Selection Screen */
            <div className="space-y-6">
              {/* Target Account Selector */}
              <div className="bg-slate-950/70 border border-slate-800 rounded-2xl p-4">
                <label className="block text-xs font-bold text-slate-300 mb-2">
                  Select Target Account to Reconcile &amp; Post:
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {accounts.map(acc => (
                    <button
                      key={acc.id}
                      type="button"
                      onClick={() => setSelectedAccountTargetId(acc.id)}
                      className={`flex items-center gap-3 p-3 rounded-xl border text-left transition cursor-pointer ${
                        selectedAccountTargetId === acc.id
                          ? 'bg-teal-500/10 border-teal-500 text-white'
                          : 'bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700'
                      }`}
                    >
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${acc.color}25`, color: acc.color }}
                      >
                        {acc.type === 'credit_card' ? (
                          <CreditCard className="w-4 h-4" />
                        ) : acc.type === 'cash' ? (
                          <Wallet className="w-4 h-4" />
                        ) : (
                          <Building className="w-4 h-4" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold truncate">{acc.name}</div>
                        <div className="text-[10px] text-slate-400">
                          {acc.accountNumberMasked} • Bal: AED{' '}
                          {acc.balance.toLocaleString('en-AE', { minimumFractionDigits: 0 })}
                        </div>
                      </div>
                      {selectedAccountTargetId === acc.id && (
                        <Check className="w-4 h-4 text-teal-400 shrink-0" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              {/* Drag & Drop Upload Container */}
              <div
                onDragOver={e => e.preventDefault()}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-3xl p-6 sm:p-8 text-center transition cursor-pointer ${
                  selectedFile
                    ? 'border-teal-500/70 bg-teal-950/20'
                    : 'border-slate-700 hover:border-teal-400/50 bg-slate-950/40 hover:bg-slate-950/60'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.xlsx,.xls,.csv"
                  className="hidden"
                  onChange={handleFileChange}
                />

                <div className="w-14 h-14 rounded-2xl bg-teal-500/10 text-teal-400 border border-teal-500/20 mx-auto flex items-center justify-center mb-3">
                  <Upload className="w-6 h-6 animate-pulse" />
                </div>

                {selectedFile ? (
                  <div>
                    <h4 className="text-sm sm:text-base font-bold text-white flex items-center justify-center gap-2">
                      <FileText className="w-4 h-4 text-teal-400" />
                      <span>{selectedFile.name}</span>
                    </h4>
                    <p className="text-xs text-teal-300 mt-1">
                      {(selectedFile.size / 1024).toFixed(1)} KB • Ready for AI extraction
                    </p>
                    <span className="inline-block mt-3 text-[11px] text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1 rounded-lg">
                      Click to choose a different file
                    </span>
                  </div>
                ) : (
                  <div>
                    <h4 className="text-sm sm:text-base font-bold text-white">
                      Drag &amp; drop your Bank Statement here
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      Supports PDF (digital or scanned), Excel (.xlsx, .xls) and CSV
                    </p>
                    <div className="flex items-center justify-center gap-2 mt-4 text-[10px] font-semibold text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        Emirates NBD
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        ADCB
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        FAB
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        Mashreq
                      </span>
                      <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700">
                        RAKBANK
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Error Alert */}
              {errorMessage && (
                <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2.5">
                  <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{errorMessage}</span>
                </div>
              )}

              {/* Primary Extract Action Button */}
              <div>
                <button
                  type="button"
                  disabled={!selectedFile || isProcessing}
                  onClick={handleStartExtraction}
                  className={`w-full py-3.5 px-4 rounded-2xl font-bold text-xs sm:text-sm flex items-center justify-center gap-2 transition cursor-pointer shadow-lg ${
                    selectedFile && !isProcessing
                      ? 'bg-teal-500 hover:bg-teal-400 text-slate-950 shadow-teal-500/20'
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                  }`}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-teal-400" />
                      <span>{processingStep || 'Processing statement...'}</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Extract, Categorize &amp; Reconcile Statement</span>
                    </>
                  )}
                </button>
              </div>

              {/* 1-Click Test Samples Divider */}
              <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-slate-800" />
                </div>
                <div className="relative flex justify-center text-xs uppercase">
                  <span className="bg-slate-900 px-3 text-slate-500 font-semibold tracking-wider text-[10px]">
                    Instant Testing with Realistic UAE Statements
                  </span>
                </div>
              </div>

              {/* Sample Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => handleLoadSample(0)}
                  disabled={isProcessing}
                  className="p-3.5 rounded-2xl bg-slate-950/80 hover:bg-slate-950 border border-slate-800 hover:border-teal-500/50 text-left transition cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white group-hover:text-teal-400 transition">
                      Emirates NBD Checking Statement
                    </span>
                    <span className="text-[9px] font-bold text-teal-400 bg-teal-500/10 px-1.5 py-0.5 rounded">
                      Checking
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2">
                    Features WPS Salary credit (AED 10,000), DEWA, Carrefour, ENOC, Du Telecom &amp; Card Autopay.
                  </p>
                  <div className="mt-2.5 flex items-center gap-1 text-[10px] font-semibold text-teal-400">
                    <span>Load &amp; Reconcile Sample</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => handleLoadSample(1)}
                  disabled={isProcessing}
                  className="p-3.5 rounded-2xl bg-slate-950/80 hover:bg-slate-950 border border-slate-800 hover:border-teal-500/50 text-left transition cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-white group-hover:text-teal-400 transition">
                      ADCB TouchPoints Credit Card
                    </span>
                    <span className="text-[9px] font-bold text-indigo-400 bg-indigo-500/10 px-1.5 py-0.5 rounded">
                      Credit Card
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 line-clamp-2">
                    Features Card Payment (AED 3,200), ADNOC petrol, Shake Shack dining, Amazon &amp; Lulu.
                  </p>
                  <div className="mt-2.5 flex items-center gap-1 text-[10px] font-semibold text-indigo-400">
                    <span>Load &amp; Reconcile Sample</span>
                    <ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </button>
              </div>
            </div>
          ) : (
            /* Extracted Preview, Reconciliation & Approval Screen */
            <div className="space-y-5">
              {/* Top Bank & Reconciliation Summary Card */}
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 sm:p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-9 h-9 rounded-xl bg-teal-500/20 text-teal-400 flex items-center justify-center font-black text-xs">
                      {extractedData.bankName.slice(0, 2).toUpperCase()}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white">{extractedData.bankName}</h4>
                      <p className="text-[11px] text-slate-400">
                        {extractedData.accountNumberMasked || 'Account Statement'}
                        {extractedData.statementPeriod?.start && (
                          <span>
                            {' '}
                            • {extractedData.statementPeriod.start} to{' '}
                            {extractedData.statementPeriod.end}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>

                  {/* Target Account Selector in Header */}
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400 whitespace-nowrap">Posting to:</span>
                    <select
                      value={selectedAccountTargetId}
                      onChange={e => setSelectedAccountTargetId(e.target.value)}
                      className="bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-white font-medium focus:border-teal-400 outline-none cursor-pointer"
                    >
                      {accounts.map(acc => (
                        <option key={acc.id} value={acc.id}>
                          {acc.name} ({acc.accountNumberMasked})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* 4 Financial Key Figures */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2.5">
                    <span className="text-[10px] text-slate-400 block font-medium">Opening Balance</span>
                    <span className="text-xs sm:text-sm font-bold text-white tabular-nums">
                      AED {extractedData.openingBalance?.toLocaleString('en-AE', { minimumFractionDigits: 2 }) || '0.00'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2.5">
                    <span className="text-[10px] text-rose-400 block font-medium">Total Debits (Spent)</span>
                    <span className="text-xs sm:text-sm font-bold text-rose-300 tabular-nums">
                      AED {extractedData.totalDebits?.toLocaleString('en-AE', { minimumFractionDigits: 2 }) || '0.00'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2.5">
                    <span className="text-[10px] text-teal-400 block font-medium">Total Credits (In)</span>
                    <span className="text-xs sm:text-sm font-bold text-teal-300 tabular-nums">
                      AED {extractedData.totalCredits?.toLocaleString('en-AE', { minimumFractionDigits: 2 }) || '0.00'}
                    </span>
                  </div>
                  <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-2.5">
                    <span className="text-[10px] text-slate-400 block font-medium">Closing Balance</span>
                    <span className="text-xs sm:text-sm font-bold text-white tabular-nums">
                      AED {extractedData.closingBalance?.toLocaleString('en-AE', { minimumFractionDigits: 2 }) || '0.00'}
                    </span>
                  </div>
                </div>

                {/* Mathematical Reconciliation Box */}
                {extractedData.reconciliation && (
                  <div
                    className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
                      extractedData.reconciliation.isBalanced
                        ? 'bg-teal-500/10 border-teal-500/30 text-teal-200'
                        : 'bg-amber-500/10 border-amber-500/30 text-amber-200'
                    }`}
                  >
                    {extractedData.reconciliation.isBalanced ? (
                      <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <span className="font-bold block">
                        {extractedData.reconciliation.isBalanced
                          ? 'Mathematical Reconciliation Verified ✓'
                          : 'Reconciliation Warning'}
                      </span>
                      <p className="text-[11px] opacity-90 mt-0.5">
                        {extractedData.reconciliation.notes}
                      </p>
                    </div>
                  </div>
                )}

                {/* Anti-Duplicate Shield Banner */}
                {duplicateCount > 0 && (
                  <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-200 text-xs flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-blue-400 shrink-0" />
                      <span>
                        <strong>Anti-Duplicate Shield:</strong> {duplicateCount} transaction(s)
                        match entries already in your ledger and were automatically unselected to
                        prevent double counting.
                      </span>
                    </div>
                    <button
                      onClick={handleExcludeDuplicates}
                      className="px-2.5 py-1 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded-lg text-[10px] font-bold whitespace-nowrap transition cursor-pointer"
                    >
                      Deselect All Duplicates
                    </button>
                  </div>
                )}
              </div>

              {/* Table Controls & Filters */}
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                {/* Filter Tabs */}
                <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
                  <button
                    onClick={() => setFilterType('all')}
                    className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                      filterType === 'all'
                        ? 'bg-teal-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    All ({editableTransactions.length})
                  </button>
                  <button
                    onClick={() => setFilterType('new')}
                    className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                      filterType === 'new'
                        ? 'bg-teal-500 text-slate-950 font-bold'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    New ({editableTransactions.length - duplicateCount})
                  </button>
                  {duplicateCount > 0 && (
                    <button
                      onClick={() => setFilterType('duplicates')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                        filterType === 'duplicates'
                          ? 'bg-teal-500 text-slate-950 font-bold'
                          : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Duplicates ({duplicateCount})
                    </button>
                  )}
                  {flaggedCount > 0 && (
                    <button
                      onClick={() => setFilterType('flagged')}
                      className={`px-2.5 py-1 rounded-lg font-medium transition cursor-pointer ${
                        filterType === 'flagged'
                          ? 'bg-amber-500 text-slate-950 font-bold'
                          : 'text-amber-400 hover:text-white'
                      }`}
                    >
                      Flagged ({flaggedCount})
                    </button>
                  )}
                </div>

                {/* Bulk Select Toggles */}
                <div className="flex items-center gap-2 text-[11px] text-slate-400">
                  <button
                    onClick={() => handleSelectAll(true)}
                    className="hover:text-teal-400 transition cursor-pointer"
                  >
                    Select All
                  </button>
                  <span>•</span>
                  <button
                    onClick={() => handleSelectAll(false)}
                    className="hover:text-rose-400 transition cursor-pointer"
                  >
                    Deselect All
                  </button>
                  <span>•</span>
                  <button
                    onClick={() => {
                      setExtractedData(null);
                      setSelectedFile(null);
                    }}
                    className="hover:text-white transition cursor-pointer"
                  >
                    Upload Another
                  </button>
                </div>
              </div>

              {/* Transactions Editable Table / Cards */}
              <div className="bg-slate-950/80 border border-slate-800 rounded-2xl overflow-hidden">
                <div className="divide-y divide-slate-800/80">
                  {filteredList.map(tx => {
                    const isExpense = tx.type === 'expense';
                    const isIncome = tx.type === 'income';
                    const isCardPayment = tx.type === 'card_payment';

                    return (
                      <div
                        key={tx.id}
                        className={`p-3 sm:p-4 transition flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                          tx.selected
                            ? 'bg-slate-900/60'
                            : 'bg-slate-950/40 opacity-70 hover:opacity-100'
                        } ${tx.isDuplicate ? 'border-l-4 border-l-blue-500' : ''} ${
                          tx.isSuspicious ? 'border-l-4 border-l-amber-500' : ''
                        }`}
                      >
                        {/* Left: Checkbox + Date + Merchant + Narrative */}
                        <div className="flex items-start gap-3 min-w-0 flex-1">
                          <input
                            type="checkbox"
                            checked={tx.selected}
                            onChange={() => handleToggleSelect(tx.id)}
                            className="w-4 h-4 mt-1 rounded bg-slate-800 border-slate-700 text-teal-500 focus:ring-teal-400 cursor-pointer accent-teal-500"
                          />
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              {/* Editable Date */}
                              <input
                                type="date"
                                value={tx.date}
                                onChange={e => handleDateChange(tx.id, e.target.value)}
                                className="bg-slate-900 border border-slate-700/80 rounded-lg px-2 py-0.5 text-[11px] text-slate-300 font-mono outline-none focus:border-teal-400 cursor-pointer"
                              />

                              {/* Editable Merchant */}
                              <input
                                type="text"
                                value={tx.merchant}
                                onChange={e => handleMerchantChange(tx.id, e.target.value)}
                                className="bg-slate-900 border border-slate-700/80 rounded-lg px-2 py-0.5 text-xs text-white font-bold outline-none focus:border-teal-400 min-w-[140px] flex-1"
                                placeholder="Merchant name"
                              />

                              {/* Badges */}
                              {tx.isDuplicate && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/40">
                                  Duplicate Shield
                                </span>
                              )}
                              {tx.isSuspicious && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40">
                                  {tx.suspiciousReason || 'Flagged'}
                                </span>
                              )}
                              {isCardPayment && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
                                  Card Settlement
                                </span>
                              )}
                              {isIncome && (
                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                                  Income / Salary
                                </span>
                              )}
                            </div>

                            {/* Raw Narrative & Duplicate Reason */}
                            <p className="text-[10px] text-slate-400 mt-1 truncate font-mono">
                              {tx.description}
                            </p>
                            {tx.isDuplicate && tx.duplicateReason && (
                              <p className="text-[10px] text-blue-300 mt-0.5">
                                ℹ️ {tx.duplicateReason}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Right: Category Selector + Amount */}
                        <div className="flex items-center justify-between sm:justify-end gap-3 shrink-0">
                          {/* Category Dropdown */}
                          <div className="flex items-center gap-1.5">
                            <select
                              value={tx.selectedCategory}
                              onChange={e =>
                                handleCategoryChange(tx.id, e.target.value as ExpenseCategory)
                              }
                              className="bg-slate-900 border border-slate-700 rounded-xl px-2.5 py-1.5 text-xs text-slate-200 font-medium focus:border-teal-400 outline-none cursor-pointer"
                            >
                              {CATEGORY_OPTIONS.map(cat => (
                                <option key={cat} value={cat}>
                                  {cat}
                                </option>
                              ))}
                            </select>
                          </div>

                          {/* Amount */}
                          <div className="text-right min-w-[90px]">
                            <span
                              className={`text-sm sm:text-base font-black tabular-nums tracking-tight ${
                                isIncome
                                  ? 'text-teal-400'
                                  : isCardPayment
                                  ? 'text-indigo-400'
                                  : 'text-rose-400'
                              }`}
                            >
                              {isIncome ? '+' : '-'} AED{' '}
                              {tx.amount.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Bottom Footer with Primary Action */}
        {extractedData && postedSuccess === null && (
          <div className="p-4 bg-slate-950 border-t border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
            <div className="text-xs text-slate-400">
              <span className="font-bold text-white">{selectedCount}</span> of{' '}
              {editableTransactions.length} transactions selected • Spending Sum:{' '}
              <strong className="text-rose-400">
                AED {selectedTotalDebit.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
              </strong>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2.5 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={selectedCount === 0}
                onClick={handlePostTransactions}
                className={`px-5 py-2.5 rounded-xl font-bold text-xs sm:text-sm flex items-center gap-2 transition cursor-pointer shadow-lg ${
                  selectedCount > 0
                    ? 'bg-teal-500 hover:bg-teal-400 text-slate-950 shadow-teal-500/20'
                    : 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                }`}
              >
                <Check className="w-4 h-4" />
                <span>
                  Approve &amp; Post ({selectedCount}) to {targetAccountObj?.name || 'Account'}
                </span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
