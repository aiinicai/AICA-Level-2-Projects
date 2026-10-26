import React, { useState } from 'react';
import {
  Check,
  X,
  AlertCircle,
  AlertTriangle,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  FolderArchive,
  Zap,
  ShieldAlert,
} from 'lucide-react';
import { AppRow, Kind } from '../types';
import { inr, longD } from '../utils/calculations';
import {
  ReconciledImportRow,
  ReconciliationReport,
  generateReconciliationCsv,
} from '../utils/excelReconciliation';
import { downloadFile } from '../utils/exportImport';

interface Props {
  isOpen: boolean;
  report: ReconciliationReport | null;
  onClose: () => void;
  onConfirmImport: (selectedRows: ReconciledImportRow[]) => void;
}

export const ImportPreviewModal: React.FC<Props> = ({
  isOpen,
  report,
  onClose,
  onConfirmImport,
}) => {
  const [filterDestination, setFilterDestination] = useState<string>('all');
  const [rows, setRows] = useState<ReconciledImportRow[]>(report?.rows || []);

  // Sync rows when report changes
  React.useEffect(() => {
    if (report?.rows) {
      setRows(report.rows);
    }
  }, [report]);

  if (!isOpen || !report) return null;

  const toggleRow = (id: string) => {
    setRows((prev) =>
      prev.map((r) => (r.id === id ? { ...r, selected: !r.selected } : r))
    );
  };

  const selectAll = (val: boolean) => {
    setRows((prev) =>
      prev.map((r) =>
        r.outcome === 'rejected' ? r : { ...r, selected: val }
      )
    );
  };

  const filteredRows = rows.filter((r) => {
    if (filterDestination === 'all') return true;
    if (filterDestination === 'inv') return r.mappedDestination === 'Investments';
    if (filterDestination === 'id') return r.mappedDestination === 'Records (Identity)';
    if (filterDestination === 'ins') return r.mappedDestination === 'Records (Insurance)';
    if (filterDestination === 'util') return r.mappedDestination === 'Utilities';
    if (filterDestination === 'due') return r.mappedDestination === 'Due Dates';
    return true;
  });

  const selectedCount = rows.filter((r) => r.selected).length;

  const handleDownloadReport = () => {
    const csvContent = generateReconciliationCsv({ ...report, rows });
    downloadFile(
      `paisa-pal-import-reconciliation-${Date.now()}.csv`,
      csvContent,
      'text/csv;charset=utf-8;'
    );
  };

  const handleConfirm = () => {
    const selected = rows.filter((r) => r.selected);
    onConfirmImport(selected);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="import-preview-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/70 backdrop-blur-xs overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#0F1B2D] border border-gray-200 dark:border-gray-800 rounded-3xl w-full max-w-6xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="p-5 sm:p-6 border-b border-gray-100 dark:border-gray-800 flex items-start justify-between gap-4 bg-gradient-to-r from-teal-500/10 via-blue-500/10 to-indigo-500/10 dark:from-teal-950/40 dark:via-blue-950/30 dark:to-indigo-950/40">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-[#0E7C86] text-white flex items-center justify-center shadow-xs">
                <FileSpreadsheet className="w-5 h-5" />
              </div>
              <h2
                id="import-preview-title"
                className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white"
              >
                Import Reconciliation &amp; Destination Mapping Preview
              </h2>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Source File: <strong className="font-mono text-gray-800 dark:text-gray-200">{report.fileName}</strong> · Every single source row is classified and reconciled. <strong>0 rows silently discarded.</strong>
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Reconciliation KPI Bar */}
        <div className="p-4 sm:px-6 bg-gray-50/80 dark:bg-[#0A1424] border-b border-gray-200/80 dark:border-gray-800/80 grid grid-cols-2 sm:grid-cols-6 gap-2.5 text-center">
          <div className="bg-white dark:bg-[#122138] p-2.5 rounded-xl border border-gray-200 dark:border-gray-800">
            <div className="text-[10px] uppercase font-bold text-gray-500 dark:text-gray-400">Source Rows</div>
            <div className="text-lg font-black text-gray-900 dark:text-white mt-0.5">{report.totalSourceRows}</div>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-950/40 p-2.5 rounded-xl border border-emerald-200 dark:border-emerald-800">
            <div className="text-[10px] uppercase font-bold text-emerald-700 dark:text-emerald-400">Newly Imported</div>
            <div className="text-lg font-black text-emerald-700 dark:text-emerald-300 mt-0.5">{report.newlyImportedCount}</div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-950/40 p-2.5 rounded-xl border border-blue-200 dark:border-blue-800">
            <div className="text-[10px] uppercase font-bold text-blue-700 dark:text-blue-400">Updated / Mapped</div>
            <div className="text-lg font-black text-blue-700 dark:text-blue-300 mt-0.5">{report.updatedCount}</div>
          </div>
          <div className="bg-amber-50 dark:bg-amber-950/40 p-2.5 rounded-xl border border-amber-200 dark:border-amber-800">
            <div className="text-[10px] uppercase font-bold text-amber-700 dark:text-amber-400">Skipped (Duplicates)</div>
            <div className="text-lg font-black text-amber-700 dark:text-amber-300 mt-0.5">{report.skippedCount}</div>
          </div>
          <div className="bg-rose-50 dark:bg-rose-950/40 p-2.5 rounded-xl border border-rose-200 dark:border-rose-800">
            <div className="text-[10px] uppercase font-bold text-rose-700 dark:text-rose-400">Rejected (Errors)</div>
            <div className="text-lg font-black text-rose-700 dark:text-rose-300 mt-0.5">{report.rejectedCount}</div>
          </div>
          <div className="bg-gray-100 dark:bg-gray-800/60 p-2.5 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="text-[10px] uppercase font-bold text-gray-600 dark:text-gray-400">Empty Rows</div>
            <div className="text-lg font-black text-gray-700 dark:text-gray-300 mt-0.5">{report.genuinelyEmptyRows}</div>
          </div>
        </div>

        {/* Filter Bar & Controls */}
        <div className="px-5 py-3 border-b border-gray-100 dark:border-gray-800 flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-[#0F1B2D]">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-semibold text-gray-500 mr-1">Destination:</span>
            {[
              { id: 'all', label: `All (${rows.length})` },
              { id: 'inv', label: `Investments (${rows.filter((r) => r.mappedDestination === 'Investments').length})` },
              { id: 'id', label: `Official IDs (${rows.filter((r) => r.mappedDestination === 'Records (Identity)').length})` },
              { id: 'ins', label: `Insurance (${rows.filter((r) => r.mappedDestination === 'Records (Insurance)').length})` },
              { id: 'util', label: `Utilities (${rows.filter((r) => r.mappedDestination === 'Utilities').length})` },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setFilterDestination(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  filterDestination === tab.id
                    ? 'bg-[#0E7C86] text-white shadow-2xs'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => selectAll(true)}
              className="text-xs text-[#0E7C86] dark:text-[#3CB7C2] hover:underline font-semibold"
            >
              Select All Valid
            </button>
            <span className="text-gray-300 dark:text-gray-700">|</span>
            <button
              onClick={() => selectAll(false)}
              className="text-xs text-gray-500 hover:underline font-semibold"
            >
              Clear Selection
            </button>
          </div>
        </div>

        {/* Rows Table */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-2.5">
          {filteredRows.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              No entries found for this destination filter.
            </div>
          ) : (
            <div className="border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden shadow-2xs">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-gray-100 dark:bg-[#142338] text-gray-600 dark:text-gray-300 font-bold border-b border-gray-200 dark:border-gray-800">
                    <th className="py-2.5 px-3 w-10 text-center">Import</th>
                    <th className="py-2.5 px-3 w-24">Sheet / Row</th>
                    <th className="py-2.5 px-3 w-40">Mapped Destination</th>
                    <th className="py-2.5 px-3">Item / Description</th>
                    <th className="py-2.5 px-3">Person / Holder</th>
                    <th className="py-2.5 px-3 font-mono">Account / Doc #</th>
                    <th className="py-2.5 px-3">Amount</th>
                    <th className="py-2.5 px-3">Due / Expiry</th>
                    <th className="py-2.5 px-3">Outcome &amp; Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                  {filteredRows.map((r) => {
                    const isInv = r.mappedDestination === 'Investments';
                    const isId = r.mappedDestination === 'Records (Identity)';
                    const isIns = r.mappedDestination === 'Records (Insurance)';
                    const isUtil = r.mappedDestination === 'Utilities';

                    let badgeClass = 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300';
                    if (isInv) badgeClass = 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800';
                    else if (isId) badgeClass = 'bg-amber-100 text-amber-800 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-800';
                    else if (isIns) badgeClass = 'bg-purple-100 text-purple-800 dark:bg-purple-950/70 dark:text-purple-300 border border-purple-300 dark:border-purple-800';
                    else if (isUtil) badgeClass = 'bg-cyan-100 text-cyan-800 dark:bg-cyan-950/70 dark:text-cyan-300 border border-cyan-300 dark:border-cyan-800';

                    return (
                      <tr
                        key={r.id}
                        className={`hover:bg-gray-50 dark:hover:bg-[#122238] transition ${
                          r.selected
                            ? 'bg-white dark:bg-[#0F1B2D]'
                            : 'opacity-60 bg-gray-50/50 dark:bg-[#0B1524]'
                        }`}
                      >
                        <td className="py-2 px-3 text-center">
                          <input
                            type="checkbox"
                            checked={r.selected}
                            disabled={r.outcome === 'rejected'}
                            onChange={() => toggleRow(r.id)}
                            className="w-4 h-4 rounded text-[#0E7C86] focus:ring-teal-500 cursor-pointer"
                          />
                        </td>
                        <td className="py-2 px-3 text-gray-500 dark:text-gray-400 font-mono text-[11px]">
                          {r.sourceSheet ? `${r.sourceSheet.slice(0, 12)} · ` : ''}R{r.sourceRowNumber}
                        </td>
                        <td className="py-2 px-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${badgeClass}`}>
                            {r.mappedDestination}
                          </span>
                        </td>
                        <td className="py-2 px-3 font-semibold text-gray-900 dark:text-white">
                          <div>{r.titleOrName}</div>
                          {r.proposedCorrections.length > 0 && (
                            <div className="text-[10px] text-teal-600 dark:text-teal-400 font-normal">
                              ✓ {r.proposedCorrections.join(', ')}
                            </div>
                          )}
                        </td>
                        <td className="py-2 px-3 text-gray-700 dark:text-gray-300">
                          {r.holder}
                        </td>
                        <td className="py-2 px-3 font-mono text-gray-900 dark:text-gray-200">
                          {r.identifierNumber || '—'}
                        </td>
                        <td className="py-2 px-3 font-bold text-gray-900 dark:text-white">
                          {r.amountOrValue !== '' ? inr(r.amountOrValue) : '—'}
                          {r.secondaryAmount !== '' && r.secondaryAmount !== r.amountOrValue && (
                            <div className="text-[10px] text-gray-400 font-normal">
                              Val: {inr(r.secondaryAmount)}
                            </div>
                          )}
                        </td>
                        <td className="py-2 px-3 text-gray-700 dark:text-gray-300">
                          {r.dateOrDue ? longD(r.dateOrDue) : <span className="text-gray-400">Permanent / N/A</span>}
                        </td>
                        <td className="py-2 px-3">
                          {r.outcome === 'newly_imported' && (
                            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-bold text-[11px]">
                              <CheckCircle2 className="w-3.5 h-3.5" />
                              Ready to Import
                            </span>
                          )}
                          {r.outcome === 'skipped' && (
                            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold text-[11px]" title={r.duplicateReason}>
                              <AlertTriangle className="w-3.5 h-3.5" />
                              Skipped (Duplicate)
                            </span>
                          )}
                          {r.outcome === 'rejected' && (
                            <span className="inline-flex items-center gap-1 text-rose-600 dark:text-rose-400 font-semibold text-[11px]" title={r.rejectionReason}>
                              <AlertCircle className="w-3.5 h-3.5" />
                              Rejected
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 sm:p-5 border-t border-gray-100 dark:border-gray-800 bg-gray-50/60 dark:bg-[#0A1424] flex flex-col sm:flex-row items-center justify-between gap-3">
          <button
            onClick={handleDownloadReport}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 hover:bg-gray-50 text-gray-700 dark:text-gray-300 shadow-2xs transition"
            title="Download full CSV audit trail of this import"
          >
            <Download className="w-4 h-4 text-[#0E7C86]" />
            <span>Download Reconciliation Report (.CSV)</span>
          </button>

          <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-800 transition"
            >
              Cancel
            </button>
            <button
              onClick={handleConfirm}
              disabled={selectedCount === 0}
              className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold transition shadow-sm ${
                selectedCount > 0
                  ? 'bg-[#0E7C86] hover:bg-[#128e9a] text-white cursor-pointer'
                  : 'bg-gray-300 dark:bg-gray-800 text-gray-500 cursor-not-allowed'
              }`}
            >
              <Check className="w-4 h-4" />
              <span>Confirm &amp; Import {selectedCount} Valid Entries</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
