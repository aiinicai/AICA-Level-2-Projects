import React, { useState } from 'react';
import { 
  BankStatementData, 
  BankTransaction, 
  CashAuditAlert, 
  DuplicateGroup 
} from '../types';
import { RiskBadge } from './RiskBadge';
import { 
  Landmark, 
  TrendingUp, 
  TrendingDown, 
  AlertOctagon, 
  Copy, 
  Search, 
  Filter, 
  Flame, 
  ArrowUpRight, 
  ArrowDownLeft,
  Calendar,
  CreditCard,
  FileSpreadsheet,
  AlertTriangle
} from 'lucide-react';

interface BankStatementModuleProps {
  data: BankStatementData;
  onExportExcel: () => void;
}

export const BankStatementModule: React.FC<BankStatementModuleProps> = ({
  data,
  onExportExcel,
}) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedFilter, setSelectedFilter] = useState<'ALL' | 'CASH_50K' | 'DUPLICATES' | 'CREDITS' | 'DEBITS'>('ALL');

  const hasCashRisk = data.highCashTransactionsCount > 0;
  const hasDuplicates = data.duplicateTransactionsCount > 0;

  // Filter transactions
  const filteredTransactions = (data.transactions || []).filter(tx => {
    const matchesSearch = 
      !searchQuery ||
      tx.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      tx.date.includes(searchQuery) ||
      (tx.referenceNo && tx.referenceNo.toLowerCase().includes(searchQuery.toLowerCase())) ||
      (tx.category && tx.category.toLowerCase().includes(searchQuery.toLowerCase()));

    if (!matchesSearch) return false;

    if (selectedFilter === 'CASH_50K') return tx.isCashAbove50k;
    if (selectedFilter === 'DUPLICATES') return tx.isDuplicate;
    if (selectedFilter === 'CREDITS') return (tx.credit || 0) > 0;
    if (selectedFilter === 'DEBITS') return (tx.debit || 0) > 0;

    return true;
  });

  return (
    <div className="space-y-4">
      
      {/* 3-Card Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">High Cash Transactions (&gt;₹50k)</p>
          <div className="flex items-center justify-between">
            <span className="text-xl font-bold font-mono text-slate-800">
              {data.highCashTransactionsCount || 0}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tight ${
              hasCashRisk ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {hasCashRisk ? 'SFT Review' : 'Clean'}
            </span>
          </div>
        </div>

        <div className={`bg-white p-4 rounded-xl border shadow-xs ${
          hasDuplicates ? 'border-slate-200 border-l-4 border-l-amber-500' : 'border-slate-200 border-l-4 border-l-emerald-500'
        }`}>
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Duplicate Debits</p>
          <div className="flex items-center justify-between">
            <span className={`text-xl font-bold font-mono ${hasDuplicates ? 'text-amber-700' : 'text-emerald-700'}`}>
              {data.duplicateTransactionsCount || 0}
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-tight ${
              hasDuplicates ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
            }`}>
              {hasDuplicates ? 'Possible Error' : 'Zero Duplicate'}
            </span>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider mb-1">Net Cash Movement</p>
          <div className="flex items-center justify-between">
            <span className={`text-lg font-bold font-mono ${data.netCashFlow >= 0 ? 'text-emerald-700' : 'text-red-600'}`}>
              {data.netCashFlow >= 0 ? `+₹${data.netCashFlow?.toLocaleString('en-IN')}` : `-₹${Math.abs(data.netCashFlow)?.toLocaleString('en-IN')}`}
            </span>
            <span className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold uppercase tracking-tight">
              {data.totalTransactionsCount || 0} Txns
            </span>
          </div>
        </div>
      </div>

      {/* Main Ledger Dashboard Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col overflow-hidden">
        
        {/* Table Header / Toolbar */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-3 bg-slate-50/60">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-4 bg-indigo-600 rounded-full"></span>
            <h2 className="font-bold text-slate-700 text-sm">
              Bank Statement &amp; Forensic Ledger ({filteredTransactions.length})
            </h2>
            <span className="text-[11px] text-slate-500 font-mono bg-white px-2 py-0.5 rounded border border-slate-200">
              A/C: {data.accountNumber}
            </span>
          </div>

          {/* Search & Filter Pill Buttons & Export */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Search Input */}
            <div className="relative min-w-[160px]">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search narration..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1 bg-white border border-slate-200 rounded text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>

            {/* Filter Buttons */}
            <div className="flex items-center gap-1 bg-slate-100 p-0.5 rounded text-[11px] font-semibold border border-slate-200">
              <button
                onClick={() => setSelectedFilter('ALL')}
                className={`px-2 py-1 rounded transition-colors ${selectedFilter === 'ALL' ? 'bg-white text-indigo-700 font-bold shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                All
              </button>
              <button
                onClick={() => setSelectedFilter('CASH_50K')}
                className={`px-2 py-1 rounded transition-colors ${selectedFilter === 'CASH_50K' ? 'bg-white text-red-600 font-bold shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Cash &gt;₹50k
              </button>
              <button
                onClick={() => setSelectedFilter('DUPLICATES')}
                className={`px-2 py-1 rounded transition-colors ${selectedFilter === 'DUPLICATES' ? 'bg-white text-amber-700 font-bold shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Duplicates
              </button>
              <button
                onClick={() => setSelectedFilter('CREDITS')}
                className={`px-2 py-1 rounded transition-colors ${selectedFilter === 'CREDITS' ? 'bg-white text-emerald-700 font-bold shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Inflows
              </button>
              <button
                onClick={() => setSelectedFilter('DEBITS')}
                className={`px-2 py-1 rounded transition-colors ${selectedFilter === 'DEBITS' ? 'bg-white text-red-600 font-bold shadow-2xs' : 'text-slate-600 hover:text-slate-900'}`}
              >
                Outflows
              </button>
            </div>

            <button 
              onClick={onExportExcel}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded text-xs font-bold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="overflow-x-auto max-h-[420px]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-100/60 sticky top-0">
              <tr className="border-b border-slate-200 text-[11px] text-slate-500 font-bold uppercase tracking-wider">
                <th className="p-2.5 pl-5">Date</th>
                <th className="p-2.5">Narration / Description</th>
                <th className="p-2.5">Ref No</th>
                <th className="p-2.5">Mode</th>
                <th className="p-2.5 text-right">Debit (₹)</th>
                <th className="p-2.5 text-right">Credit (₹)</th>
                <th className="p-2.5 text-right">Balance (₹)</th>
                <th className="p-2.5 pr-5 text-center">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-slate-700">
              {filteredTransactions && filteredTransactions.length > 0 ? (
                filteredTransactions.map((tx, idx) => (
                  <tr 
                    key={tx.id || idx}
                    className={`transition-colors ${
                      tx.isCashAbove50k 
                        ? 'bg-red-50/40 hover:bg-red-50/70' 
                        : tx.isDuplicate
                        ? 'bg-amber-50/40 hover:bg-amber-50/70'
                        : 'hover:bg-slate-50/70'
                    }`}
                  >
                    <td className="p-2.5 pl-5 font-mono text-slate-600 whitespace-nowrap">{tx.date}</td>
                    <td className="p-2.5 font-semibold text-slate-800 max-w-[260px]">
                      <div className="truncate" title={tx.description}>
                        {tx.description}
                      </div>
                      {tx.category && (
                        <span className="text-[10px] text-slate-400 font-normal block">
                          {tx.category}
                        </span>
                      )}
                    </td>
                    <td className="p-2.5 font-mono text-slate-500 text-[11px] whitespace-nowrap">
                      {tx.referenceNo || '—'}
                    </td>
                    <td className="p-2.5">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        tx.mode === 'CASH'
                          ? 'bg-red-100 text-red-700'
                          : tx.mode === 'UPI'
                          ? 'bg-purple-100 text-purple-700'
                          : tx.mode === 'NEFT' || tx.mode === 'RTGS'
                          ? 'bg-indigo-100 text-indigo-700'
                          : 'bg-slate-100 text-slate-600'
                      }`}>
                        {tx.mode}
                      </span>
                    </td>
                    <td className="p-2.5 text-right font-mono font-semibold text-red-600 whitespace-nowrap">
                      {tx.debit ? `₹${tx.debit.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="p-2.5 text-right font-mono font-semibold text-emerald-700 whitespace-nowrap">
                      {tx.credit ? `₹${tx.credit.toLocaleString('en-IN')}` : '—'}
                    </td>
                    <td className="p-2.5 text-right font-mono font-bold text-slate-900 whitespace-nowrap">
                      ₹{tx.balance?.toLocaleString('en-IN')}
                    </td>
                    <td className="p-2.5 pr-5 text-center whitespace-nowrap">
                      {tx.isCashAbove50k ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-[10px] font-bold">
                          <Flame className="w-3 h-3" />
                          <span>CASH &gt;₹50k</span>
                        </span>
                      ) : tx.isDuplicate ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-[10px] font-bold">
                          <Copy className="w-3 h-3" />
                          <span>DUPLICATE</span>
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 rounded-full text-[10px] font-bold">
                          VERIFIED
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-slate-400">
                    No transactions matching filter criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Sleek Summary Bottom Bar */}
        <div className="p-3 bg-slate-900 flex items-center justify-between text-white text-xs">
          <div className="flex items-center gap-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">SUMMARY</span>
            <span className="text-[11px] text-slate-300">
              Total Inflows: ₹{data.totalInflows?.toLocaleString('en-IN')} • Total Outflows: ₹{data.totalOutflows?.toLocaleString('en-IN')}
            </span>
          </div>
          <button 
            onClick={onExportExcel}
            className="bg-indigo-600 text-white px-3 py-1 rounded text-[10px] font-bold uppercase hover:bg-indigo-500 transition-colors shadow-2xs"
          >
            Save Audit Workpaper
          </button>
        </div>
      </div>

      {/* Cash Transactions > ₹50,000 Alert Section */}
      {data.cashAuditAlerts && data.cashAuditAlerts.length > 0 && (
        <div className="p-4 rounded-xl bg-white border border-red-200 border-l-4 border-l-red-500 shadow-2xs space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-red-800 uppercase tracking-wider flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 text-red-600" />
              <span>Section 269ST &amp; SFT High-Value Cash Alerts (&gt;₹50,000)</span>
            </h4>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700">
              {data.cashAuditAlerts.length} High-Risk Entries
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {data.cashAuditAlerts.map((alert, i) => (
              <div key={i} className="p-3 rounded-lg bg-red-50/30 border border-red-200 text-xs space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-mono text-slate-500 text-[10px]">{alert.date}</span>
                  <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-red-100 text-red-700">
                    {alert.section}
                  </span>
                </div>
                <div className="flex items-baseline justify-between">
                  <span className="text-xs text-slate-700 font-semibold">{alert.type === 'DEPOSIT' ? 'Cash Deposit' : 'Cash Withdrawal'}:</span>
                  <span className="text-sm font-extrabold font-mono text-red-600">
                    ₹{alert.amount?.toLocaleString('en-IN')}
                  </span>
                </div>
                <p className="text-[11px] text-slate-800 font-semibold">{alert.ruleViolation}</p>
                <p className="text-[10px] text-slate-500 leading-tight pt-1 border-t border-red-100">
                  {alert.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Duplicate Entries Warning Card */}
      {data.duplicateGroups && data.duplicateGroups.length > 0 && (
        <div className="p-4 rounded-xl bg-white border border-amber-200 border-l-4 border-l-amber-500 shadow-2xs space-y-2.5 text-xs">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-amber-800 uppercase tracking-wider flex items-center gap-2">
              <Copy className="w-4 h-4 text-amber-600" />
              <span>Duplicate Transaction Instances ({data.duplicateGroups.length})</span>
            </h4>
            <span className="text-[10px] text-amber-700 font-bold">Possible Double Debit / Ledger Error</span>
          </div>

          <div className="space-y-2">
            {data.duplicateGroups.map((dup, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-amber-50/40 border border-amber-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-slate-700 font-semibold">{dup.date}</span>
                    <span className="text-amber-800 font-bold font-mono">₹{dup.amount?.toLocaleString('en-IN')}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] bg-amber-100 text-amber-800 font-bold">
                      {dup.count} Repeated Entries
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 mt-0.5 truncate max-w-lg">
                    {dup.descriptions.join(' ➔ ')}
                  </p>
                </div>
                <span className="text-[10px] text-slate-500 shrink-0 font-medium">
                  Reconcile with Vendor Invoice
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Forensic Bank Audit Synthesis */}
      <div className="p-3.5 rounded-xl bg-white border border-slate-200 text-xs text-slate-600 shadow-2xs">
        <span className="font-bold text-slate-800 block mb-1">Forensic Bank Audit Summary:</span>
        <p className="leading-relaxed">{data.auditSummary}</p>
      </div>

    </div>
  );
};

