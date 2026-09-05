import React, { useState, useEffect } from 'react';
import type { Client, TrialBalanceLine, FinancialStatements } from '../types';
import { api } from '../services/api';
import { Columns, Save, Search, RefreshCw, CheckCircle2 } from 'lucide-react';

interface SplitWorkbenchPageProps {
  client: Client;
}

export const SplitWorkbenchPage: React.FC<SplitWorkbenchPageProps> = ({ client }) => {
  const [tbLines, setTbLines] = useState<TrialBalanceLine[]>([]);
  const [fs, setFs] = useState<FinancialStatements | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [search, setSearch] = useState<string>('');
  const [filterStatement, setFilterStatement] = useState<string>('ALL');
  const [activeFsTab, setActiveFsTab] = useState<'BS' | 'PL'>('BS');
  const [classifications, setClassifications] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadWorkbenchData();
  }, [client.id]);

  const loadWorkbenchData = async () => {
    setLoading(true);
    try {
      const [tbRes, fsRes, classRes] = await Promise.all([
        api.getTrialBalance(client.id),
        api.getFinancialStatements(client.id),
        api.getClassifications()
      ]);
      setTbLines(tbRes);
      setFs(fsRes);
      setClassifications(classRes.classifications);
    } catch (err: any) {
      console.error("Failed to load workbench data", err);
    } finally {
      setLoading(false);
    }
  };

  const handleClassificationChange = (lineId: number, newClass: string) => {
    setTbLines(prev => prev.map(line => {
      if (line.id === lineId) {
        return {
          ...line,
          final_classification: newClass,
          user_override: true
        };
      }
      return line;
    }));
  };

  const handleSaveAndRefresh = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updates = tbLines.map(l => ({
        id: l.id,
        final_classification: l.final_classification || '',
        financial_statement: l.financial_statement || '',
        note_number: l.note_number || '',
        current_non_current: l.current_non_current || '',
        user_override: l.user_override
      }));

      await api.saveMapping(client.id, updates);
      const updatedFs = await api.getFinancialStatements(client.id);
      setFs(updatedFs);
      setMessage("Mapping saved & Schedule III financial statements recalculated!");
    } catch (err: any) {
      setMessage(`Error: ${err.message || 'Failed to update mapping'}`);
    } finally {
      setSaving(false);
    }
  };

  const filteredLines = tbLines.filter(l => {
    const matchesSearch = l.ledger_name.toLowerCase().includes(search.toLowerCase()) || 
                          (l.original_group || '').toLowerCase().includes(search.toLowerCase());
    if (filterStatement === 'BS') return matchesSearch && l.financial_statement === 'Balance Sheet';
    if (filterStatement === 'PL') return matchesSearch && l.financial_statement === 'Profit & Loss';
    return matchesSearch;
  });

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-96">
        <div className="flex items-center gap-3 text-orange-600 font-bold text-sm">
          <RefreshCw className="w-5 h-5 animate-spin" /> Loading Split Workbench Workspace...
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Top Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 rounded-lg">
            <Columns className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-lg font-black text-[#1B365D] dark:text-blue-400 flex items-center gap-2">
              Google AI Studio Split Workbench
              <span className="text-[10px] bg-orange-600 text-white font-extrabold px-2 py-0.5 rounded uppercase">
                Real-Time Live Engine
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Side-by-side ledger classification mapping linked directly to live Schedule III Balance Sheet & P&L
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {message && (
            <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 border border-emerald-200 dark:border-emerald-800 px-3 py-1.5 rounded-lg flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" /> {message}
            </span>
          )}

          <button
            onClick={handleSaveAndRefresh}
            disabled={saving}
            className="ca-button-primary flex items-center gap-2"
          >
            {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save & Recalculate FS
          </button>
        </div>
      </div>

      {/* Main Dual-Pane Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT PANE: Ledger Mapping Table (Col 6) */}
        <div className="lg:col-span-6 studio-card p-4 space-y-3 flex flex-col h-[calc(100vh-220px)]">
          <div className="flex items-center justify-between gap-2 pb-2 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider flex items-center gap-2">
              1. Trial Balance Ledgers ({filteredLines.length})
            </h2>

            <div className="flex items-center gap-2">
              <select
                className="studio-input text-xs font-bold py-1 px-2"
                value={filterStatement}
                onChange={(e) => setFilterStatement(e.target.value)}
              >
                <option value="ALL">All Statements</option>
                <option value="BS">Balance Sheet Only</option>
                <option value="PL">Profit & Loss Only</option>
              </select>

              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-slate-400" />
                <input
                  type="text"
                  placeholder="Filter ledgers..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="studio-input text-xs pl-8 py-1 w-36"
                />
              </div>
            </div>
          </div>

          <div className="overflow-y-auto flex-1 border border-slate-200 dark:border-slate-800 rounded-lg">
            <table className="ca-table">
              <thead className="sticky top-0 z-10">
                <tr>
                  <th className="w-2/5">Ledger Name</th>
                  <th className="w-1/5 text-right">CY Amount (₹ L)</th>
                  <th className="w-2/5">Schedule III Classification</th>
                </tr>
              </thead>
              <tbody>
                {filteredLines.map((line) => (
                  <tr key={line.id} className={line.user_override ? 'bg-orange-50/50 dark:bg-orange-950/20' : ''}>
                    <td className="font-semibold text-slate-800 dark:text-slate-200">
                      <div>{line.ledger_name}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{line.original_group}</div>
                    </td>
                    <td className="text-right font-mono font-bold text-slate-700 dark:text-slate-300">
                      {line.cy_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </td>
                    <td>
                      <select
                        className="studio-input text-xs font-bold w-full py-1"
                        value={line.final_classification || ''}
                        onChange={(e) => handleClassificationChange(line.id, e.target.value)}
                      >
                        {classifications.map(c => (
                          <option key={c} value={c}>{c}</option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* RIGHT PANE: Live Schedule III Statement Preview (Col 6) */}
        <div className="lg:col-span-6 studio-card p-4 space-y-3 flex flex-col h-[calc(100vh-220px)]">
          <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-black text-[#1B365D] dark:text-blue-400 uppercase tracking-wider">
                2. Live Schedule III Preview
              </h2>
              {fs?.is_tallied ? (
                <span className="text-[10px] bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-400 font-bold px-2 py-0.5 rounded border border-emerald-300 dark:border-emerald-800">
                  TALLIED
                </span>
              ) : (
                <span className="text-[10px] bg-red-100 text-red-700 font-bold px-2 py-0.5 rounded">
                  DIFF: ₹{fs?.difference.toFixed(2)} L
                </span>
              )}
            </div>

            <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
              <button
                onClick={() => setActiveFsTab('BS')}
                className={`px-3 py-1 text-xs font-bold rounded cursor-pointer ${
                  activeFsTab === 'BS' 
                    ? 'bg-[#1B365D] text-white shadow-xs' 
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                Balance Sheet
              </button>
              <button
                onClick={() => setActiveFsTab('PL')}
                className={`px-3 py-1 text-xs font-bold rounded cursor-pointer ${
                  activeFsTab === 'PL' 
                    ? 'bg-[#1B365D] text-white shadow-xs' 
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900'
                }`}
              >
                Profit & Loss
              </button>
            </div>
          </div>

          <div className="overflow-y-auto flex-1 border border-slate-200 dark:border-slate-800 rounded-lg p-2 bg-white dark:bg-slate-900">
            {activeFsTab === 'BS' ? (
              <table className="fs-report-table">
                <thead>
                  <tr>
                    <th className="w-3/5 text-left">Particulars</th>
                    <th className="w-1/5 text-center">Note</th>
                    <th className="w-1/5 text-right">CY (₹ L)</th>
                  </tr>
                </thead>
                <tbody>
                  {fs?.balance_sheet.map((row, idx) => {
                    let rowClass = "";
                    if (row.is_header) rowClass = "fs-row-header";
                    else if (row.is_subtotal) rowClass = "fs-row-subtotal";
                    else if (row.is_total) rowClass = "fs-row-total";

                    return (
                      <tr key={idx} className={rowClass}>
                        <td className="py-1 px-2">{row.particulars}</td>
                        <td className="py-1 px-2 text-center font-bold">{row.note_number}</td>
                        <td className="py-1 px-2 text-right font-mono font-bold">
                          {row.is_header ? '' : row.cy_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            ) : (
              <table className="fs-report-table">
                <thead>
                  <tr>
                    <th className="w-3/5 text-left">Particulars</th>
                    <th className="w-1/5 text-center">Note</th>
                    <th className="w-1/5 text-right">CY (₹ L)</th>
                  </tr>
                </thead>
                <tbody>
                  {fs?.profit_and_loss.map((row, idx) => {
                    let rowClass = "";
                    if (row.is_header) rowClass = "fs-row-header";
                    else if (row.is_subtotal) rowClass = "fs-row-subtotal";
                    else if (row.is_total) rowClass = "fs-row-total";

                    return (
                      <tr key={idx} className={rowClass}>
                        <td className="py-1 px-2">{row.particulars}</td>
                        <td className="py-1 px-2 text-center font-bold">{row.note_number}</td>
                        <td className="py-1 px-2 text-right font-mono font-bold">
                          {row.is_header ? '' : row.cy_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
