import React, { useState, useMemo } from 'react';
import {
  X,
  Printer,
  FileSpreadsheet,
  AlertOctagon,
  Calendar,
  ChevronDown,
  Download,
  Loader2,
  CheckCircle2,
  FileText
} from 'lucide-react';
import { Account, CategoryBudget, Transaction } from '../types/finance';
import {
  exportTransactionsToCSV,
  triggerPrintPDF,
  generateStandaloneStatementHTML,
  downloadStatementHTML,
  StatementData
} from '../services/reports';

interface MonthlyReportModalProps {
  transactions: Transaction[];
  accounts: Account[];
  budgets: CategoryBudget[];
  onClose: () => void;
}

export const MonthlyReportModal: React.FC<MonthlyReportModalProps> = ({
  transactions,
  accounts,
  budgets,
  onClose
}) => {
  const [isPrinting, setIsPrinting] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Extract all distinct months (YYYY-MM) present in transactions, plus current month
  const availableMonths = useMemo(() => {
    const set = new Set<string>();
    const currentMonthKey = new Date().toISOString().slice(0, 7);
    set.add(currentMonthKey);
    for (const t of transactions) {
      if (t.date && t.date.length >= 7) {
        set.add(t.date.slice(0, 7));
      }
    }
    return Array.from(set).sort((a, b) => b.localeCompare(a));
  }, [transactions]);

  // Default to the month of the newest transaction, or current month
  const [selectedMonth, setSelectedMonth] = useState<string>(() => {
    if (transactions.length > 0 && transactions[0].date && transactions[0].date.length >= 7) {
      return transactions[0].date.slice(0, 7);
    }
    return new Date().toISOString().slice(0, 7);
  });

  // Filter transactions strictly for the selected month (or all if 'all' chosen)
  const monthTransactions = useMemo(() => {
    if (selectedMonth === 'all') return transactions;
    return transactions.filter(t => t.date && t.date.startsWith(selectedMonth));
  }, [transactions, selectedMonth]);

  // Aggregate stats strictly for this month
  const expenses = monthTransactions.filter(t => t.type === 'expense');
  const incomes = monthTransactions.filter(t => t.type === 'income');

  const totalExpense = expenses.reduce((s, t) => s + t.amount, 0);
  const totalIncome = incomes.reduce((s, t) => s + t.amount, 0);
  const netSavings = totalIncome - totalExpense;
  const savingsRate = totalIncome > 0 ? (netSavings / totalIncome) * 100 : 0;

  // Category breakdown for selected month
  const categoryTotals: Record<string, number> = {};
  for (const t of expenses) {
    if (t.categorySplits && t.categorySplits.length > 0) {
      for (const split of t.categorySplits) {
        categoryTotals[split.category] = (categoryTotals[split.category] || 0) + split.amount;
      }
    } else {
      categoryTotals[t.category] = (categoryTotals[t.category] || 0) + t.amount;
    }
  }

  const redFlags = monthTransactions.filter(t => t.isRedFlag);

  // Month Title format: e.g. "2026-10" -> "October 2026"
  const formatMonthTitle = (monthKey: string) => {
    if (monthKey === 'all') return 'All Time Summary';
    const [year, month] = monthKey.split('-').map(Number);
    if (!year || !month) return monthKey;
    const date = new Date(year, month - 1, 1);
    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  };

  // Month Period format: e.g. "October 1, 2026 – October 31, 2026"
  const formatMonthPeriod = (monthKey: string) => {
    if (monthKey === 'all') return 'All Historical Transactions';
    const [year, month] = monthKey.split('-').map(Number);
    if (!year || !month) return monthKey;
    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    return `${firstDay.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })} – ${lastDay.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}`;
  };

  const currentMonthTitle = formatMonthTitle(selectedMonth);
  const currentMonthPeriod = formatMonthPeriod(selectedMonth);

  const getStatementData = (): StatementData => ({
    monthTitle: currentMonthTitle,
    monthPeriod: currentMonthPeriod,
    transactions: monthTransactions,
    accounts,
    budgets,
    totalIncome,
    totalExpense,
    netSavings,
    savingsRate,
    categoryTotals,
    redFlags
  });

  const handleExportCSV = () => {
    const prefix = `DirhamTrack_Statement_${currentMonthTitle.replace(/\s+/g, '_')}`;
    exportTransactionsToCSV(monthTransactions, accounts, prefix);
    setStatusMessage('CSV exported successfully!');
    setTimeout(() => setStatusMessage(null), 4000);
  };

  const handleDownloadStatement = () => {
    const html = generateStandaloneStatementHTML(getStatementData());
    downloadStatementHTML(currentMonthTitle, html);
    setStatusMessage('Statement document downloaded! Open it to view or print anytime.');
    setTimeout(() => setStatusMessage(null), 5000);
  };

  const handlePrint = async () => {
    setIsPrinting(true);
    setStatusMessage('Preparing isolated print preview...');
    try {
      const html = generateStandaloneStatementHTML(getStatementData());
      const result = await triggerPrintPDF(html);
      if (result.success) {
        setStatusMessage('Print dialog opened. Select your printer or "Save as PDF".');
      } else {
        // If mobile / browser iframe blocks print, provide instant clean download
        downloadStatementHTML(currentMonthTitle, html);
        setStatusMessage('Browser blocked direct print; clean statement file downloaded!');
      }
    } catch (e) {
      const html = generateStandaloneStatementHTML(getStatementData());
      downloadStatementHTML(currentMonthTitle, html);
      setStatusMessage('Clean statement file saved to downloads.');
    } finally {
      setIsPrinting(false);
      setTimeout(() => setStatusMessage(null), 6000);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end sm:justify-center items-center bg-black/85 backdrop-blur-sm p-0 sm:p-4 overflow-hidden animate-fade-in">
      <div className="w-full max-w-4xl bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[94vh] sm:max-h-[90vh]">
        {/* Header Actions Toolbar (Completely hidden in print) */}
        <div className="no-print p-4 bg-slate-950 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-400 flex items-center justify-center font-bold text-xs">
              د.إ
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-white">
                Monthly Financial Statement
              </h3>
              <p className="text-xs text-slate-400">
                Print or export statement for <span className="text-teal-400 font-semibold">{currentMonthTitle}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* Month Selector Dropdown */}
            <div className="relative">
              <div className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-white">
                <Calendar className="w-3.5 h-3.5 text-teal-400 shrink-0" />
                <select
                  value={selectedMonth}
                  onChange={e => setSelectedMonth(e.target.value)}
                  className="bg-transparent text-white text-xs font-semibold focus:outline-none cursor-pointer pr-1"
                >
                  {availableMonths.map(m => (
                    <option key={m} value={m} className="bg-slate-900 text-white">
                      {formatMonthTitle(m)}
                    </option>
                  ))}
                  <option value="all" className="bg-slate-900 text-white">All Months (Full History)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleExportCSV}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-teal-300 rounded-lg text-xs font-semibold transition cursor-pointer"
              title="Download CSV for selected month"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">CSV</span>
            </button>

            <button
              onClick={handleDownloadStatement}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition cursor-pointer border border-slate-700/60"
              title="Download standalone statement file (works offline & on all mobile devices)"
            >
              <Download className="w-3.5 h-3.5 text-teal-400" />
              <span className="hidden sm:inline">Download File</span>
            </button>

            <button
              onClick={handlePrint}
              disabled={isPrinting}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-teal-500 hover:bg-teal-400 disabled:opacity-50 text-slate-950 rounded-lg text-xs font-bold transition shadow cursor-pointer"
              title="Print only this month's statement (clean white page)"
            >
              {isPrinting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Printer className="w-3.5 h-3.5" />
              )}
              <span>{isPrinting ? 'Opening...' : 'Print / Save PDF'}</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Status notification banner if active */}
        {statusMessage && (
          <div className="no-print bg-teal-950/70 border-b border-teal-500/30 px-4 py-2 text-xs text-teal-300 flex items-center justify-between animate-fadeIn">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-teal-400 shrink-0" />
              <span>{statusMessage}</span>
            </div>
            <button
              onClick={() => setStatusMessage(null)}
              className="text-teal-400 hover:text-white text-xs font-bold ml-2 underline cursor-pointer"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Printable Statement Document Content - ID used for clean isolated print */}
        <div
          id="printable-monthly-statement"
          className="p-4 sm:p-8 bg-slate-900 print:bg-white print:text-slate-900 overflow-y-auto flex-1 min-h-0"
        >
          {/* Document Header */}
          <div className="flex justify-between items-start border-b border-slate-800 print:border-slate-300 pb-5 mb-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="px-2 py-0.5 rounded bg-teal-500 text-slate-950 font-black text-xs print:bg-slate-900 print:text-white">
                  د.إ AED
                </span>
                <h1 className="text-xl sm:text-2xl font-black tracking-tight text-white print:text-slate-950">
                  DirhamTrack
                </h1>
              </div>
              <h2 className="text-sm font-bold text-teal-400 print:text-teal-800">
                Monthly Financial &amp; Expense Statement — {currentMonthTitle}
              </h2>
              <p className="text-xs text-slate-400 print:text-slate-600 mt-1">
                Statement Period: <span className="font-semibold">{currentMonthPeriod}</span>
              </p>
            </div>

            <div className="text-right">
              <span className="text-[10px] text-slate-400 print:text-slate-500 uppercase tracking-widest block font-bold">
                Currency &amp; Region
              </span>
              <span className="text-lg font-black text-teal-400 print:text-teal-900">
                AED (United Arab Emirates)
              </span>
              <p className="text-[11px] text-slate-400 print:text-slate-600 mt-0.5">
                Generated: {new Date().toLocaleDateString('en-AE', { day: 'numeric', month: 'short', year: 'numeric' })}
              </p>
              <span className="inline-block text-[10px] font-semibold text-emerald-400 print:text-emerald-800 mt-1">
                ✓ Verified Personal Ledger
              </span>
            </div>
          </div>

          {/* Executive KPI Summary */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="p-3.5 rounded-xl bg-slate-950 print:bg-slate-50 border border-slate-800 print:border-slate-300">
              <span className="text-[10px] text-slate-400 print:text-slate-600 uppercase tracking-wider block font-semibold">
                Total Income
              </span>
              <span className="text-base sm:text-lg font-black text-emerald-400 print:text-emerald-800 tabular-nums">
                AED {totalIncome.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 print:bg-slate-50 border border-slate-800 print:border-slate-300">
              <span className="text-[10px] text-slate-400 print:text-slate-600 uppercase tracking-wider block font-semibold">
                Total Expenses
              </span>
              <span className="text-base sm:text-lg font-black text-white print:text-slate-950 tabular-nums">
                AED {totalExpense.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 print:bg-slate-50 border border-slate-800 print:border-slate-300">
              <span className="text-[10px] text-slate-400 print:text-slate-600 uppercase tracking-wider block font-semibold">
                Net Monthly Savings
              </span>
              <span className="text-base sm:text-lg font-black text-teal-400 print:text-teal-800 tabular-nums">
                AED {netSavings.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950 print:bg-slate-50 border border-slate-800 print:border-slate-300">
              <span className="text-[10px] text-slate-400 print:text-slate-600 uppercase tracking-wider block font-semibold">
                Savings Rate
              </span>
              <span className="text-base sm:text-lg font-black text-white print:text-slate-950 tabular-nums">
                {savingsRate.toFixed(1)}%
              </span>
            </div>
          </div>

          {/* Category Breakdown Table */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-slate-900">
                Spending by Category — {currentMonthTitle}
              </h3>
              <span className="text-[11px] text-slate-400 print:text-slate-600">
                Total Categories: {budgets.length}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b-2 border-slate-800 print:border-slate-400 text-slate-400 print:text-slate-700 bg-slate-950/60 print:bg-slate-100">
                    <th className="py-2.5 px-3 font-semibold">Category</th>
                    <th className="py-2.5 px-3 text-right font-semibold">Actual Spent (AED)</th>
                    <th className="py-2.5 px-3 text-right font-semibold">Budget Limit (AED)</th>
                    <th className="py-2.5 px-3 text-right font-semibold">% of Total Spend</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 print:divide-slate-200">
                  {budgets.map(b => {
                    const spent = categoryTotals[b.category] || 0;
                    const share = totalExpense > 0 ? (spent / totalExpense) * 100 : 0;
                    return (
                      <tr key={b.category} className="text-slate-200 print:text-slate-900 print:even:bg-slate-50">
                        <td className="py-2 px-3 font-medium">{b.category}</td>
                        <td className="py-2 px-3 text-right font-bold tabular-nums">
                          AED {spent.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 px-3 text-right text-slate-400 print:text-slate-600 tabular-nums">
                          AED {b.monthlyLimit.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-slate-400 print:text-slate-700 font-medium">
                          {share.toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Red Flag Security Audit Section (if any flagged transactions for this month) */}
          {redFlags.length > 0 && (
            <div className="mb-6 p-4 rounded-xl bg-rose-950/20 print:bg-rose-50 border border-rose-500/30 print:border-rose-300">
              <h4 className="text-xs font-bold text-rose-300 print:text-rose-900 flex items-center gap-2 mb-2">
                <AlertOctagon className="w-4 h-4 text-rose-400 print:text-rose-600" />
                Security Audit: {redFlags.length} Flagged / International Transaction(s) in {currentMonthTitle}
              </h4>
              <div className="space-y-1.5 text-xs text-slate-300 print:text-slate-800">
                {redFlags.map(rf => (
                  <div key={rf.id} className="flex justify-between items-center py-1.5 border-b border-rose-900/30 print:border-rose-200 last:border-none">
                    <span>
                      {rf.date} · <strong>{rf.merchant}</strong> ({rf.bankName || 'Bank'})
                      {rf.redFlagReason && <span className="text-[11px] text-slate-400 print:text-slate-600 ml-2">[{rf.redFlagReason}]</span>}
                    </span>
                    <span className="font-bold text-rose-400 print:text-rose-800 tabular-nums">
                      AED {rf.amount.toFixed(2)} {rf.originalAmount ? `(${rf.originalCurrency} ${rf.originalAmount})` : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Transaction Ledger Table for the Selected Month */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 print:text-slate-900">
                Transaction Ledger — {currentMonthTitle}
              </h3>
              <span className="text-[11px] text-slate-400 print:text-slate-600 font-medium">
                {monthTransactions.length} transaction(s) recorded
              </span>
            </div>

            {monthTransactions.length === 0 ? (
              <div className="py-8 text-center text-slate-400 print:text-slate-600 bg-slate-950/40 print:bg-slate-50 rounded-xl border border-slate-800 print:border-slate-300">
                <p className="text-xs font-medium">No transactions recorded for {currentMonthTitle}.</p>
                <p className="text-[11px] text-slate-500 mt-0.5">Select another month or record new transactions.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b-2 border-slate-800 print:border-slate-400 text-slate-400 print:text-slate-700 bg-slate-950/60 print:bg-slate-100">
                      <th className="py-2.5 px-3">Date</th>
                      <th className="py-2.5 px-3">Merchant</th>
                      <th className="py-2.5 px-3">Category</th>
                      <th className="py-2.5 px-3">Bank / Ledger Source</th>
                      <th className="py-2.5 px-3 text-right">Amount (AED)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 print:divide-slate-200 text-slate-300 print:text-slate-900">
                    {monthTransactions.map(t => (
                      <tr key={t.id} className="print:even:bg-slate-50">
                        <td className="py-2 px-3 text-slate-400 print:text-slate-600 font-mono text-[11px] whitespace-nowrap">
                          {t.date}
                        </td>
                        <td className="py-2 px-3 font-semibold text-white print:text-slate-900">
                          {t.merchant}
                        </td>
                        <td className="py-2 px-3">
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 print:bg-slate-100 text-slate-300 print:text-slate-800 font-medium">
                            {t.category}
                          </span>
                        </td>
                        <td className="py-2 px-3 text-slate-400 print:text-slate-700">
                          {t.bankName || 'Manual Ledger'}
                        </td>
                        <td className={`py-2 px-3 text-right font-bold tabular-nums ${
                          t.type === 'income'
                            ? 'text-emerald-400 print:text-emerald-800'
                            : 'text-white print:text-slate-900'
                        }`}>
                          {t.type === 'income' ? '+' : '-'} {t.amount.toLocaleString('en-AE', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Official Document Footer (Visible in print & on screen) */}
          <div className="mt-8 pt-4 border-t border-slate-800 print:border-slate-300 flex flex-col sm:flex-row items-center justify-between gap-2 text-[10px] text-slate-400 print:text-slate-600">
            <div>
              <span>DirhamTrack · Smart UAE Budget &amp; Bank Notification Interceptor</span>
              <span className="mx-2">•</span>
              <span>Confidential Financial Statement</span>
            </div>
            <div className="font-semibold text-slate-300 print:text-slate-800">
              Developed by <span className="text-teal-400 print:text-teal-900 font-bold">Fakhruddin</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
