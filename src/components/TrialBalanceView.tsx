import React, { useState } from 'react';
import * as XLSX from 'xlsx';
import {
  FileSpreadsheet,
  Upload,
  Download,
  CheckCircle2,
  AlertTriangle,
  Search,
  Filter,
  ArrowUpDown,
  FileDown,
  Layers,
  Sparkles,
  DollarSign,
  Scale,
  RefreshCw,
  Eye,
} from 'lucide-react';
import { TrialBalanceData, TrialBalanceItem, ComputedMateriality, TBCategory } from '../types';
import { formatINR, formatCompactINR } from '../utils/calculations';
import { generateTrialBalanceTemplate } from '../utils/tbParser';
import { ZENITH_SAMPLE_TRIAL_BALANCE } from '../data/sampleTrialBalance';

interface TrialBalanceViewProps {
  trialBalance?: TrialBalanceData;
  materiality: ComputedMateriality;
  onOpenImportModal: () => void;
  onSyncMaterialityBenchmark: (basis: string, amount: number) => void;
  onClearTB: () => void;
  onLoadSampleTB: () => void;
}

export const TrialBalanceView: React.FC<TrialBalanceViewProps> = ({
  trialBalance,
  materiality,
  onOpenImportModal,
  onSyncMaterialityBenchmark,
  onClearTB,
  onLoadSampleTB,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedMateriality, setSelectedMateriality] = useState<string>('All');
  const [viewMode, setViewMode] = useState<'ledgers' | 'scheduleIII'>('ledgers');
  const [sortField, setSortField] = useState<'code' | 'name' | 'net' | 'variance'>('code');
  const [sortAsc, setSortAsc] = useState(true);

  if (!trialBalance || !trialBalance.items || trialBalance.items.length === 0) {
    return (
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#dedbd2] dark:border-[#272f38]">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold font-serif text-[#1e232a] dark:text-[#f3f4f6]">
              Trial Balance & Financial Aggregates
            </h1>
            <p className="text-xs sm:text-sm text-stone-500 dark:text-stone-400 mt-0.5">
              Import client trial balance to power SA 320 materiality benchmarks, Schedule III groupings, and SA 315 scoping.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                const bytes = generateTrialBalanceTemplate();
                const blob = new Blob([bytes], {
                  type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'Trial_Balance_Template_ICAI.xlsx';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }}
              className="px-3 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#1c222b] text-stone-700 dark:text-stone-300 text-xs font-medium hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors flex items-center gap-1.5 shadow-xs"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>Download Excel Template</span>
            </button>
            <button
              onClick={onOpenImportModal}
              className="px-4 py-1.5 rounded-md bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-colors"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>Import Trial Balance</span>
            </button>
          </div>
        </div>

        {/* Empty State Banner */}
        <div className="p-10 rounded-xl bg-white dark:bg-[#14181d] border border-dashed border-stone-300 dark:border-stone-700 text-center space-y-4 max-w-2xl mx-auto my-8">
          <div className="w-14 h-14 rounded-full bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-400 flex items-center justify-center mx-auto">
            <FileSpreadsheet className="w-7 h-7" />
          </div>
          <div className="space-y-1">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              No Client Trial Balance Imported Yet
            </h3>
            <p className="text-xs text-stone-500 dark:text-stone-400 max-w-md mx-auto leading-relaxed">
              Import an Excel (.xlsx, .xls) or CSV trial balance from your client. The system automatically reconciles debits/credits, maps accounts to Schedule III of Companies Act 2013, and computes baseline figures for SA 320 materiality.
            </p>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
            <button
              onClick={onOpenImportModal}
              className="px-5 py-2 rounded-md bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs flex items-center gap-2 transition-colors"
            >
              <Upload className="w-4 h-4" />
              <span>Import from File</span>
            </button>
            <button
              onClick={onLoadSampleTB}
              className="px-4 py-2 rounded-md bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 text-xs font-semibold border border-stone-300 dark:border-stone-700 transition-colors flex items-center gap-1.5"
            >
              <Sparkles className="w-4 h-4 text-amber-600" />
              <span>Load Zenith Fabrics Sample TB (35 Accounts)</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  const { items, summary } = trialBalance;

  // Filter & Search
  const filteredItems = items.filter((item) => {
    const matchesSearch =
      searchTerm === '' ||
      item.accountName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.accountCode.toLowerCase().includes(searchTerm.toLowerCase()) ||
      item.scheduleIIIGroup.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory =
      selectedCategory === 'All' || item.category === selectedCategory;

    const matchesMateriality =
      selectedMateriality === 'All' || item.materialityFlag === selectedMateriality;

    return matchesSearch && matchesCategory && matchesMateriality;
  });

  // Sort
  const sortedItems = [...filteredItems].sort((a, b) => {
    let comp = 0;
    if (sortField === 'code') comp = a.accountCode.localeCompare(b.accountCode, undefined, { numeric: true });
    else if (sortField === 'name') comp = a.accountName.localeCompare(b.accountName);
    else if (sortField === 'net') comp = Math.abs(a.currentYearNet) - Math.abs(b.currentYearNet);
    else if (sortField === 'variance') comp = (a.variancePercent || 0) - (b.variancePercent || 0);
    return sortAsc ? comp : -comp;
  });

  // Schedule III Grouping Summary
  interface ScheduleIIIGroupData {
    group: string;
    category: TBCategory;
    totalNet: number;
    count: number;
    items: TrialBalanceItem[];
  }

  const scheduleIIIGroups: Record<string, ScheduleIIIGroupData> = {};
  for (const item of items) {
    const g = item.scheduleIIIGroup;
    if (!scheduleIIIGroups[g]) {
      scheduleIIIGroups[g] = { group: g, category: item.category, totalNet: 0, count: 0, items: [] };
    }
    scheduleIIIGroups[g].totalNet += item.currentYearNet;
    scheduleIIIGroups[g].count += 1;
    scheduleIIIGroups[g].items.push(item);
  }

  const handleExportTBOnly = () => {
    const wb = XLSX.utils.book_new();
    const rows: any[][] = [
      ['TRIAL BALANCE SCHEDULE - AUDIT PLANNING WORKPAPER'],
      [`Source File: ${trialBalance.fileName || 'Client TB'} | Reconciled: ${summary.isBalanced ? 'YES (Dr = Cr)' : 'NO'}`],
      [''],
      ['Key Financial Indicators', 'Amount (INR)'],
      ['Turnover / Revenue', summary.totalRevenue],
      ['Profit Before Tax (PBT)', summary.profitBeforeTax],
      ['Total Assets', summary.totalAssets],
      ['Net Worth / Equity', summary.totalEquity],
      ['Total Borrowings', summary.totalBorrowings],
      ['Total Debits', summary.totalDebit],
      ['Total Credits', summary.totalCredit],
      ['Difference', summary.difference],
      [''],
      [
        'Account Code',
        'Account / Ledger Name',
        'Schedule III Group',
        'Category',
        'Debit (INR)',
        'Credit (INR)',
        'Net Closing (INR)',
        'Prior Year (INR)',
        'Variance %',
        'Materiality Flag',
        'Notes',
      ],
    ];

    items.forEach((it) => {
      rows.push([
        it.accountCode,
        it.accountName,
        it.scheduleIIIGroup,
        it.category,
        it.currentYearDebit,
        it.currentYearCredit,
        it.currentYearNet,
        it.priorYearBalance ?? '',
        it.variancePercent !== undefined ? `${it.variancePercent}%` : '',
        it.materialityFlag || 'Normal',
        it.notes || '',
      ]);
    });

    const ws = XLSX.utils.aoa_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, ws, 'Trial_Balance');
    XLSX.writeFile(wb, `Trial_Balance_${trialBalance.fileName || 'Audited'}.xlsx`);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[#dedbd2] dark:border-[#272f38]">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-bold font-serif text-[#1e232a] dark:text-[#f3f4f6]">
              Trial Balance & Financial Aggregates
            </h1>
            <span className="px-2 py-0.5 rounded text-[11px] font-mono-num font-bold bg-amber-100 text-amber-900 border border-amber-300 dark:bg-amber-950/70 dark:text-amber-300 dark:border-amber-800">
              {items.length} Accounts
            </span>
          </div>
          <p className="text-xs sm:text-sm text-stone-500 dark:text-stone-400 mt-0.5">
            Source: <span className="font-semibold text-stone-700 dark:text-stone-300">{trialBalance.fileName || 'Client TB'}</span> • Imported: {trialBalance.importedAt ? new Date(trialBalance.importedAt).toLocaleDateString() : 'Active'}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleExportTBOnly}
            className="px-3 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#1c222b] text-stone-700 dark:text-stone-300 text-xs font-medium hover:bg-stone-100 dark:hover:bg-stone-800 transition-colors flex items-center gap-1.5 shadow-xs"
            title="Export full Trial Balance to Excel spreadsheet"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Export TB (.xlsx)</span>
          </button>
          <button
            onClick={onOpenImportModal}
            className="px-3.5 py-1.5 rounded-md bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Re-import / Replace TB</span>
          </button>
          <button
            onClick={onClearTB}
            className="p-1.5 rounded-md border border-stone-300 dark:border-stone-700 text-stone-500 hover:text-rose-600 dark:text-stone-400 dark:hover:text-rose-400 text-xs transition-colors"
            title="Clear current Trial Balance"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Trial Balance Reconciliation Verification Bar */}
      <div
        className={`p-4 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-xs ${
          summary.isBalanced
            ? 'bg-emerald-50/80 dark:bg-emerald-950/30 border-emerald-300 dark:border-emerald-800/80 text-emerald-950 dark:text-emerald-200'
            : 'bg-amber-50/80 dark:bg-amber-950/30 border-amber-300 dark:border-amber-800/80 text-amber-950 dark:text-amber-200'
        }`}
      >
        <div className="flex items-center gap-3">
          <div
            className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
              summary.isBalanced
                ? 'bg-emerald-200/80 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300'
                : 'bg-amber-200/80 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300'
            }`}
          >
            {summary.isBalanced ? <CheckCircle2 className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold text-sm">
                {summary.isBalanced ? 'Trial Balance Reconciled & Balanced' : 'Trial Balance Out of Balance'}
              </span>
              <span className="text-xs px-2 py-0.2 rounded-full font-mono font-bold bg-white/70 dark:bg-black/40">
                Dr = Cr Proof
              </span>
            </div>
            <p className="text-xs opacity-90 mt-0.5">
              Total Debits: <span className="font-mono-num font-semibold">{formatINR(summary.totalDebit)}</span> • Total Credits: <span className="font-mono-num font-semibold">{formatINR(summary.totalCredit)}</span>
              {!summary.isBalanced && (
                <span className="font-bold text-rose-700 dark:text-rose-400 ml-2">
                  (Difference: ₹ {formatINR(summary.difference)})
                </span>
              )}
            </p>
          </div>
        </div>

        <div className="text-xs opacity-80 shrink-0 font-medium">
          Verified under SA 315 & SA 320 Baseline Framework
        </div>
      </div>

      {/* Five Key Financial Indicators Cards with 1-Click SA 320 Sync */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3.5">
        {/* Turnover */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-[#14181d] border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Turnover / Revenue
            </span>
            <div className="text-lg font-bold font-mono-num text-stone-900 dark:text-stone-100 mt-1">
              {formatCompactINR(summary.totalRevenue)}
            </div>
            <div className="text-[11px] font-mono-num text-stone-500">
              {formatINR(summary.totalRevenue)}
            </div>
          </div>
          <button
            onClick={() => onSyncMaterialityBenchmark('Revenue', summary.totalRevenue)}
            className="mt-3 w-full py-1 px-2 rounded bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/50 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors"
            title="Set Revenue as SA 320 Materiality Benchmark Amount in Stage 10"
          >
            <Scale className="w-3 h-3" />
            <span>Use as Benchmark</span>
          </button>
        </div>

        {/* PBT */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-[#14181d] border border-amber-300/80 dark:border-amber-800/80 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-400">
                Profit Before Tax (PBT)
              </span>
              <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300">
                Common
              </span>
            </div>
            <div className="text-lg font-bold font-mono-num text-amber-800 dark:text-amber-400 mt-1">
              {formatCompactINR(summary.profitBeforeTax)}
            </div>
            <div className="text-[11px] font-mono-num text-stone-500">
              {formatINR(summary.profitBeforeTax)}
            </div>
          </div>
          <button
            onClick={() => onSyncMaterialityBenchmark('Profit before Tax', summary.profitBeforeTax)}
            className="mt-3 w-full py-1 px-2 rounded bg-amber-800 hover:bg-amber-900 text-white text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors shadow-xs"
            title="Set PBT as SA 320 Materiality Benchmark Amount in Stage 10"
          >
            <Scale className="w-3 h-3" />
            <span>Use as Benchmark</span>
          </button>
        </div>

        {/* Total Assets */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-[#14181d] border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Total Assets
            </span>
            <div className="text-lg font-bold font-mono-num text-stone-900 dark:text-stone-100 mt-1">
              {formatCompactINR(summary.totalAssets)}
            </div>
            <div className="text-[11px] font-mono-num text-stone-500">
              {formatINR(summary.totalAssets)}
            </div>
          </div>
          <button
            onClick={() => onSyncMaterialityBenchmark('Total Assets', summary.totalAssets)}
            className="mt-3 w-full py-1 px-2 rounded bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/50 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors"
            title="Set Total Assets as SA 320 Materiality Benchmark Amount in Stage 10"
          >
            <Scale className="w-3 h-3" />
            <span>Use as Benchmark</span>
          </button>
        </div>

        {/* Net Worth */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-[#14181d] border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Net Worth / Equity
            </span>
            <div className="text-lg font-bold font-mono-num text-stone-900 dark:text-stone-100 mt-1">
              {formatCompactINR(summary.totalEquity)}
            </div>
            <div className="text-[11px] font-mono-num text-stone-500">
              {formatINR(summary.totalEquity)}
            </div>
          </div>
          <button
            onClick={() => onSyncMaterialityBenchmark('Net Worth / Total Equity', summary.totalEquity)}
            className="mt-3 w-full py-1 px-2 rounded bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/40 dark:hover:bg-amber-900/50 text-amber-900 dark:text-amber-300 border border-amber-200 dark:border-amber-800/80 text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors"
            title="Set Net Worth as SA 320 Materiality Benchmark Amount in Stage 10"
          >
            <Scale className="w-3 h-3" />
            <span>Use as Benchmark</span>
          </button>
        </div>

        {/* Total Borrowings */}
        <div className="p-3.5 rounded-xl bg-white dark:bg-[#14181d] border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-stone-500 dark:text-stone-400">
              Total Borrowings
            </span>
            <div className="text-lg font-bold font-mono-num text-stone-900 dark:text-stone-100 mt-1">
              {formatCompactINR(summary.totalBorrowings)}
            </div>
            <div className="text-[11px] font-mono-num text-stone-500">
              {formatINR(summary.totalBorrowings)}
            </div>
          </div>
          <button
            onClick={() => onSyncMaterialityBenchmark('Borrowings', summary.totalBorrowings)}
            className="mt-3 w-full py-1 px-2 rounded bg-stone-100 hover:bg-stone-200 dark:bg-stone-800 dark:hover:bg-stone-700 text-stone-700 dark:text-stone-300 text-[11px] font-semibold flex items-center justify-center gap-1 transition-colors"
            title="Set Borrowings as SA 320 Materiality Benchmark Amount in Stage 10"
          >
            <Scale className="w-3 h-3" />
            <span>Use as Benchmark</span>
          </button>
        </div>
      </div>

      {/* Controls & Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-white dark:bg-[#14181d] rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs">
        {/* Search */}
        <div className="relative w-full sm:w-64">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-stone-400" />
          <input
            type="text"
            placeholder="Search accounts or codes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-stone-50 dark:bg-[#1a2027] text-xs text-stone-900 dark:text-stone-100 focus:outline-hidden focus:ring-1 focus:ring-amber-500"
          />
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-stone-300 dark:border-stone-700 p-0.5 bg-stone-100 dark:bg-[#1a2027] text-xs font-medium">
            <button
              onClick={() => setViewMode('ledgers')}
              className={`px-3 py-1 rounded transition-colors ${
                viewMode === 'ledgers'
                  ? 'bg-white dark:bg-[#14181d] text-stone-900 dark:text-stone-100 shadow-xs font-semibold'
                  : 'text-stone-600 dark:text-stone-400 hover:text-stone-900'
              }`}
            >
              All Ledgers ({items.length})
            </button>
            <button
              onClick={() => setViewMode('scheduleIII')}
              className={`px-3 py-1 rounded transition-colors ${
                viewMode === 'scheduleIII'
                  ? 'bg-white dark:bg-[#14181d] text-stone-900 dark:text-stone-100 shadow-xs font-semibold'
                  : 'text-stone-600 dark:text-stone-400 hover:text-stone-900'
              }`}
            >
              Schedule III Heads ({Object.keys(scheduleIIIGroups).length})
            </button>
          </div>
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs">
            <Filter className="w-3.5 h-3.5 text-stone-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-2.5 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#1a2027] text-xs text-stone-900 dark:text-stone-100"
            >
              <option value="All">All Categories</option>
              <option value="Assets">Assets</option>
              <option value="Liabilities">Liabilities</option>
              <option value="Equity">Equity</option>
              <option value="Revenue">Revenue</option>
              <option value="Expenses">Expenses</option>
            </select>
          </div>

          <select
            value={selectedMateriality}
            onChange={(e) => setSelectedMateriality(e.target.value)}
            className="px-2.5 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#1a2027] text-xs text-stone-900 dark:text-stone-100"
          >
            <option value="All">All Materiality Flags</option>
            <option value="Material (>OM)">Material (&gt; OM)</option>
            <option value="Significant (>PM)">Significant (&gt; PM)</option>
            <option value="Clearly Trivial">Clearly Trivial</option>
            <option value="Normal">Normal</option>
          </select>
        </div>
      </div>

      {/* Main Content: Ledgers Table vs Schedule III Heads */}
      {viewMode === 'ledgers' ? (
        <div className="bg-white dark:bg-[#14181d] rounded-xl border border-[#dedbd2] dark:border-[#272f38] overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-[#f8f7f4] dark:bg-[#1a2027] text-stone-600 dark:text-stone-400 border-b border-[#dedbd2] dark:border-[#272f38]">
                <tr>
                  <th
                    onClick={() => {
                      if (sortField === 'code') setSortAsc(!sortAsc);
                      else {
                        setSortField('code');
                        setSortAsc(true);
                      }
                    }}
                    className="p-3 cursor-pointer hover:text-stone-900 dark:hover:text-stone-100"
                  >
                    <div className="flex items-center gap-1">
                      <span>Code</span>
                      <ArrowUpDown className="w-3 h-3 text-stone-400" />
                    </div>
                  </th>
                  <th
                    onClick={() => {
                      if (sortField === 'name') setSortAsc(!sortAsc);
                      else {
                        setSortField('name');
                        setSortAsc(true);
                      }
                    }}
                    className="p-3 cursor-pointer hover:text-stone-900 dark:hover:text-stone-100"
                  >
                    <div className="flex items-center gap-1">
                      <span>Account / Ledger Name</span>
                      <ArrowUpDown className="w-3 h-3 text-stone-400" />
                    </div>
                  </th>
                  <th className="p-3">Schedule III Group</th>
                  <th className="p-3">Category</th>
                  <th className="p-3 text-right">Debit (₹)</th>
                  <th className="p-3 text-right">Credit (₹)</th>
                  <th
                    onClick={() => {
                      if (sortField === 'net') setSortAsc(!sortAsc);
                      else {
                        setSortField('net');
                        setSortAsc(false);
                      }
                    }}
                    className="p-3 text-right cursor-pointer hover:text-stone-900 dark:hover:text-stone-100"
                  >
                    <div className="flex items-center justify-end gap-1">
                      <span>Net Balance (₹)</span>
                      <ArrowUpDown className="w-3 h-3 text-stone-400" />
                    </div>
                  </th>
                  <th className="p-3 text-right">Prior Year (₹)</th>
                  <th
                    onClick={() => {
                      if (sortField === 'variance') setSortAsc(!sortAsc);
                      else {
                        setSortField('variance');
                        setSortAsc(false);
                      }
                    }}
                    className="p-3 text-right cursor-pointer hover:text-stone-900 dark:hover:text-stone-100"
                  >
                    <div className="flex items-center justify-end gap-1">
                      <span>Variance %</span>
                      <ArrowUpDown className="w-3 h-3 text-stone-400" />
                    </div>
                  </th>
                  <th className="p-3">Materiality Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                {sortedItems.length === 0 ? (
                  <tr>
                    <td colSpan={10} className="p-8 text-center text-stone-500">
                      No accounts matched the active search or filters.
                    </td>
                  </tr>
                ) : (
                  sortedItems.map((item) => (
                    <tr
                      key={item.id}
                      className="hover:bg-amber-50/40 dark:hover:bg-amber-950/10 transition-colors"
                    >
                      <td className="p-3 font-mono font-medium text-stone-600 dark:text-stone-400">
                        {item.accountCode}
                      </td>
                      <td className="p-3 font-medium text-stone-900 dark:text-stone-100">
                        <div>{item.accountName}</div>
                        {item.notes && (
                          <div className="text-[11px] text-stone-500 italic mt-0.5">
                            {item.notes}
                          </div>
                        )}
                      </td>
                      <td className="p-3 text-stone-600 dark:text-stone-400 font-medium">
                        {item.scheduleIIIGroup}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                            item.category === 'Revenue'
                              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300'
                              : item.category === 'Expenses'
                              ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                              : item.category === 'Assets'
                              ? 'bg-blue-100 text-blue-800 dark:bg-blue-950/60 dark:text-blue-300'
                              : item.category === 'Liabilities'
                              ? 'bg-purple-100 text-purple-800 dark:bg-purple-950/60 dark:text-purple-300'
                              : 'bg-stone-200 text-stone-800 dark:bg-stone-800 dark:text-stone-300'
                          }`}
                        >
                          {item.category}
                        </span>
                      </td>
                      <td className="p-3 text-right font-mono-num text-stone-700 dark:text-stone-300">
                        {item.currentYearDebit ? formatINR(item.currentYearDebit) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono-num text-stone-700 dark:text-stone-300">
                        {item.currentYearCredit ? formatINR(item.currentYearCredit) : '-'}
                      </td>
                      <td className="p-3 text-right font-mono-num font-bold text-stone-900 dark:text-stone-100">
                        {formatINR(item.currentYearNet)}
                      </td>
                      <td className="p-3 text-right font-mono-num text-stone-500">
                        {item.priorYearBalance !== undefined
                          ? formatINR(item.priorYearBalance)
                          : '-'}
                      </td>
                      <td className="p-3 text-right font-mono-num">
                        {item.variancePercent !== undefined ? (
                          <span
                            className={`font-semibold ${
                              item.variancePercent > 20 || item.variancePercent < -20
                                ? 'text-amber-700 dark:text-amber-400'
                                : 'text-stone-600 dark:text-stone-400'
                            }`}
                          >
                            {item.variancePercent > 0 ? `+${item.variancePercent}%` : `${item.variancePercent}%`}
                          </span>
                        ) : (
                          '-'
                        )}
                      </td>
                      <td className="p-3">
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                            item.materialityFlag === 'Material (>OM)'
                              ? 'bg-rose-100 text-rose-800 border-rose-300 dark:bg-rose-950/60 dark:text-rose-300 dark:border-rose-800'
                              : item.materialityFlag === 'Significant (>PM)'
                              ? 'bg-amber-100 text-amber-800 border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800'
                              : item.materialityFlag === 'Clearly Trivial'
                              ? 'bg-stone-100 text-stone-600 border-stone-200 dark:bg-stone-800 dark:text-stone-400 dark:border-stone-700'
                              : 'bg-stone-50 text-stone-600 border-transparent dark:bg-stone-900 dark:text-stone-400'
                          }`}
                        >
                          {item.materialityFlag || 'Normal'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Schedule III Summary View */
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.values(scheduleIIIGroups).map((g) => (
            <div
              key={g.group}
              className="p-4 rounded-xl bg-white dark:bg-[#14181d] border border-[#dedbd2] dark:border-[#272f38] shadow-xs space-y-3"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100">
                    {g.group}
                  </h3>
                  <span className="text-[11px] text-stone-500">
                    {g.category} • {g.count} sub-accounts
                  </span>
                </div>
                <div className="text-right">
                  <span className="font-mono-num font-bold text-base text-stone-900 dark:text-stone-100 block">
                    {formatINR(g.totalNet)}
                  </span>
                  <span className="text-[10px] text-stone-500 font-mono-num">
                    {formatCompactINR(g.totalNet)}
                  </span>
                </div>
              </div>

              <div className="border-t border-stone-200 dark:border-stone-800 pt-2 space-y-1.5">
                {g.items.map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between text-xs py-1 border-b border-stone-100 dark:border-stone-800/60 last:border-0"
                  >
                    <div className="flex items-center gap-2 truncate pr-2">
                      <span className="font-mono text-[10px] text-stone-400">{sub.accountCode}</span>
                      <span className="truncate text-stone-700 dark:text-stone-300">{sub.accountName}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-mono-num font-medium text-stone-800 dark:text-stone-200">
                        {formatCompactINR(sub.currentYearNet)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
