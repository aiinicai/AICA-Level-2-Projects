import React, { useEffect, useState, useCallback } from 'react';
import type { Client, FinancialStatements } from '../types';
import { fetchFinancialStatements } from '../services/api';
import { API_BASE } from '../services/api';
import {
  CheckCircle2, XCircle, Download, FileText, ArrowRight, RefreshCw,
  TrendingUp, Printer
} from 'lucide-react';

interface FinancialStatementsProps {
  client: Client;
  onNavigate: (tab: string) => void;
}

const fmt = (v: number, showZero = false) => {
  if (!showZero && v === 0) return '–';
  if (v < 0) return `(${Math.abs(v).toLocaleString('en-IN', { minimumFractionDigits: 2 })})`;
  return v.toLocaleString('en-IN', { minimumFractionDigits: 2 });
};

export const FinancialStatementsPage: React.FC<FinancialStatementsProps> = ({ client, onNavigate }) => {
  const [fs, setFs] = useState<FinancialStatements | null>(null);
  const [activeTab, setActiveTab] = useState<'bs' | 'pl'>('bs');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFinancialStatements(client.id);
      setFs(data);
    } catch (e) {
      console.error(e);
      setError('Failed to load financial statements. Ensure trial balance is mapped.');
    } finally {
      setLoading(false);
    }
  }, [client.id]);

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await fetch(`${API_BASE}/financial-statements/${client.id}/refresh`, { method: 'POST' });
      await loadData();
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { if (client) loadData(); }, [client.id]);

  const rows = activeTab === 'bs' ? fs?.balance_sheet : fs?.profit_and_loss;
  const cyHeader = activeTab === 'bs'
    ? `As at ${client.reporting_period}`
    : `Year ended ${client.reporting_period}`;
  const pyHeader = activeTab === 'bs'
    ? `As at ${client.previous_year_period}`
    : `Year ended ${client.previous_year_period}`;
  const stmtTitle = activeTab === 'bs'
    ? `BALANCE SHEET AS AT ${client.reporting_period.toUpperCase()}`
    : `STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED ${client.reporting_period.toUpperCase()}`;

  return (
    <div className="space-y-5 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-tight flex items-center gap-2">
            <FileText className="w-5 h-5 text-orange-600" />
            Schedule III Division I Financial Statements
          </h1>
          <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mt-0.5">
            {client.name} | {client.reporting_period} | Figures in {client.currency}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="ca-button-outline text-xs flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => window.print()}
            className="ca-button-secondary text-xs flex items-center gap-1.5 cursor-pointer"
          >
            <Printer className="w-3.5 h-3.5" />
            Print View
          </button>
          <button onClick={() => onNavigate('export-reports')} className="ca-button-primary text-xs flex items-center gap-1.5 cursor-pointer">
            <Download className="w-3.5 h-3.5" />
            Export All (PDF / Word / Excel)
          </button>
        </div>
      </div>


      {/* Tally Banner */}
      {fs && (
        <div className={`p-3.5 rounded-lg border flex items-center justify-between text-xs font-bold shadow-sm ${
          fs.is_tallied
            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-900 dark:text-emerald-300'
            : 'bg-rose-50 dark:bg-rose-950/40 border-rose-300 dark:border-rose-800 text-rose-900 dark:text-rose-300'
        }`}>
          <div className="flex items-center gap-2.5">
            {fs.is_tallied
              ? <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
              : <XCircle className="w-5 h-5 text-rose-600 shrink-0" />}
            <span>
              {fs.is_tallied
                ? 'BALANCE SHEET TALLIED — Total Assets equals Total Equity & Liabilities. Statements are arithmetically accurate.'
                : `BALANCE SHEET UNTALLIED — Difference of ₹${Math.abs(fs.difference).toFixed(2)} Lakhs. Please review ledger mappings.`}
            </span>
          </div>
          <button
            onClick={() => onNavigate('ledger-mapping')}
            className="flex items-center gap-1 text-xs font-extrabold underline underline-offset-2 hover:opacity-80 shrink-0"
          >
            Fix Mapping <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-0">
        {[
          { id: 'bs' as const, label: 'I. Balance Sheet' },
          { id: 'pl' as const, label: 'II. Statement of Profit and Loss' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setActiveTab(t.id)}
            className={`px-5 py-2.5 text-xs font-bold rounded-t-md transition-all cursor-pointer border border-b-0 ${
              activeTab === t.id
                ? 'bg-[#1B365D] text-white border-[#1B365D]'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-lg text-xs text-rose-700 font-semibold">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center p-16 gap-3 text-slate-500 text-xs font-semibold">
          <RefreshCw className="w-5 h-5 animate-spin text-orange-500" />
          Generating Schedule III financial statements…
        </div>
      ) : (
        <div className="studio-card overflow-hidden">
          {/* Document Header */}
          <div className="bg-[#1B365D] text-white px-8 py-5 text-center">
            <h2 className="text-base font-black tracking-widest uppercase">{client.name}</h2>
            <div className="text-[11px] font-semibold text-slate-300 mt-0.5">{client.entity_type}</div>
            <h3 className="text-sm font-bold mt-2 uppercase tracking-wide">{stmtTitle}</h3>
            <p className="text-[10px] text-slate-400 mt-1 font-serif italic">
              (Prepared under Schedule III Division I of Companies Act, 2013 · Figures in {client.currency})
            </p>
          </div>

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-[#2d4a73] dark:bg-[#1e3a5f] text-white border-b-2 border-orange-500">
                  <th className="text-left py-3 px-5 font-black uppercase tracking-wide w-1/2">Particulars</th>
                  <th className="text-center py-3 px-4 font-black uppercase tracking-wide w-24 whitespace-nowrap">Note No.</th>
                  <th className="text-right py-3 px-5 font-black uppercase tracking-wide w-1/4 bg-white/10 whitespace-nowrap">{cyHeader}<br /><span className="text-[9px] font-normal opacity-70">(₹ in Lakhs)</span></th>
                  <th className="text-right py-3 px-5 font-black uppercase tracking-wide w-1/4 bg-white/5 whitespace-nowrap">{pyHeader}<br /><span className="text-[9px] font-normal opacity-70">(₹ in Lakhs)</span></th>
                </tr>
              </thead>
              <tbody>
                {rows?.map((row, idx) => {
                  const isHeader = row.is_header;
                  const isSubtotal = row.is_subtotal;
                  const isTotal = row.is_total;
                  const isBlank = row.cy_amount === 0 && row.py_amount === 0 && isHeader;

                  if (isBlank && isHeader) {
                    // Section divider
                    return (
                      <tr key={idx} className="bg-[#1B365D]/8 dark:bg-white/5">
                        <td colSpan={4} className="py-2.5 px-5 text-[11px] font-black text-[#1B365D] dark:text-blue-300 uppercase tracking-widest border-b border-slate-200 dark:border-slate-700">
                          {row.particulars}
                        </td>
                      </tr>
                    );
                  }

                  return (
                    <tr
                      key={idx}
                      className={`border-b border-slate-100 dark:border-slate-800 ${
                        isTotal
                          ? 'bg-[#1B365D]/10 dark:bg-[#1B365D]/40 border-t-2 border-b-2 border-[#1B365D]/30 dark:border-blue-700'
                          : isSubtotal
                          ? 'bg-slate-100/80 dark:bg-slate-800/60 border-t border-slate-300 dark:border-slate-600'
                          : 'hover:bg-slate-50 dark:hover:bg-slate-900/20'
                      }`}
                    >
                      {/* Particulars */}
                      <td className={`py-2.5 px-5 border-r border-slate-200 dark:border-slate-700 ${
                        isTotal
                          ? 'font-black text-[#1B365D] dark:text-blue-300 text-xs uppercase tracking-wide'
                          : isSubtotal
                          ? 'font-bold text-[#1B365D] dark:text-blue-400 text-xs'
                          : 'font-medium text-slate-800 dark:text-slate-200 text-xs'
                      }`}>
                        {isTotal && <span className="inline-block w-2 border-t-2 border-[#1B365D] dark:border-blue-400 mr-1" />}
                        {row.particulars}
                      </td>

                      {/* Note Number */}
                      <td className="py-2.5 px-4 text-center border-r border-slate-200 dark:border-slate-700">
                        {row.note_number && (
                          <button
                            onClick={() => onNavigate('notes-accounts')}
                            className="text-orange-600 dark:text-orange-400 font-black font-mono text-[11px] hover:underline cursor-pointer px-2 py-0.5 rounded hover:bg-orange-50 dark:hover:bg-orange-950/40 transition-colors"
                            title={`Go to Note ${row.note_number}`}
                          >
                            {row.note_number}
                          </button>
                        )}
                      </td>

                      {/* CY Amount */}
                      <td className={`py-2.5 px-5 text-right font-mono border-r border-slate-200 dark:border-slate-700 bg-slate-50/80 dark:bg-slate-900/40 ${
                        isTotal
                          ? 'font-black text-[#1B365D] dark:text-blue-300 text-xs border-t-2 border-b-2 border-[#1B365D]/30 dark:border-blue-700/50'
                          : isSubtotal
                          ? 'font-bold text-[#1B365D] dark:text-blue-400 text-xs'
                          : 'text-slate-800 dark:text-slate-200 text-xs'
                      }`}>
                        {!isHeader ? fmt(row.cy_amount, isTotal || isSubtotal) : ''}
                      </td>

                      {/* PY Amount */}
                      <td className={`py-2.5 px-5 text-right font-mono bg-slate-50/40 dark:bg-slate-900/20 ${
                        isTotal
                          ? 'font-black text-[#1B365D] dark:text-blue-300 text-xs border-t-2 border-b-2 border-[#1B365D]/20 dark:border-blue-700/30'
                          : isSubtotal
                          ? 'font-bold text-slate-600 dark:text-slate-400 text-xs'
                          : 'text-slate-500 dark:text-slate-400 text-xs'
                      }`}>
                        {!isHeader ? fmt(row.py_amount, isTotal || isSubtotal) : ''}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Footer */}
          <div className="px-8 py-5 bg-slate-50 dark:bg-slate-900 border-t border-slate-200 dark:border-slate-800">
            <div className="grid grid-cols-3 gap-8 text-[11px]">
              <div className="space-y-3 border-t-2 border-slate-400 pt-4">
                <div className="font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">For {client.name}</div>
                <div className="text-slate-600 dark:text-slate-400 space-y-1">
                  <div>Director / Partner</div>
                  <div className="font-mono text-[10px] text-slate-400">DIN / DPIN: ____________</div>
                </div>
              </div>
              <div className="space-y-3 border-t-2 border-slate-400 pt-4">
                <div className="font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">Chief Financial Officer</div>
                <div className="text-slate-600 dark:text-slate-400 space-y-1">
                  <div>Membership No.: ____________</div>
                  <div className="font-mono text-[10px] text-slate-400">Place: New Delhi | Date: {new Date().toLocaleDateString('en-IN')}</div>
                </div>
              </div>
              <div className="space-y-3 border-t-2 border-slate-400 pt-4">
                <div className="font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">FS BUILDER LITE</div>
                <div className="text-slate-600 dark:text-slate-400 space-y-1">
                  <div>Prepared by: {client.prepared_by}</div>
                  <div>Reviewed by: {client.reviewed_by}</div>
                  <div className="flex items-center gap-1 mt-1">
                    <TrendingUp className="w-3 h-3 text-orange-500" />
                    <span className="text-[10px] text-slate-400">FS Builder Lite v0.2 — IGAAP</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
