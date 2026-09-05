import React, { useState, useRef, useEffect } from 'react';
import { Client, NoticeCase, ReconciliationItem, NoticeIssue, DocumentItem, ParsedFigure } from '../types';
import {
  calculateReconciliation,
  recomputeItem,
  applyFiguresToSchedules,
  buildRequiredSchedules,
  exportReconciliationsToExcel,
} from '../services/reconciliationEngine';
import { parseGstReturnFile } from '../services/gstReturnParser';
import {
  Calculator, Download, Upload, CheckCircle2, AlertTriangle, Plus, Trash2, Wand2, FileSpreadsheet,
} from 'lucide-react';

interface ReconciliationViewProps {
  activeClient: Client | null;
  activeCase: NoticeCase | null;
  issues: NoticeIssue[];
  documentItems: DocumentItem[];
  reconciliations: ReconciliationItem[];
  portalFigures: ParsedFigure[];
  onSaveReconciliations: (recons: ReconciliationItem[]) => Promise<void>;
  onSavePortalFigures: (figures: ParsedFigure[]) => Promise<void>;
}

const inr = (n: number) => '₹' + (n || 0).toLocaleString('en-IN');

export const ReconciliationView: React.FC<ReconciliationViewProps> = ({
  activeClient,
  activeCase,
  issues,
  documentItems,
  reconciliations,
  portalFigures,
  onSaveReconciliations,
  onSavePortalFigures,
}) => {
  const [showRecalcModal, setShowRecalcModal] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const [parseNote, setParseNote] = useState<string | null>(null);
  const [rows, setRows] = useState<ReconciliationItem[]>(reconciliations);

  const [customReconType, setCustomReconType] = useState('GSTR-2B vs GSTR-3B — ITC (Table 4A5)');
  const [customPeriod, setCustomPeriod] = useState(activeCase?.period || '');
  const [customNoticeVal, setCustomNoticeVal] = useState(activeCase?.principalTax ? String(activeCase.principalTax) : '');
  const [customPortalVal, setCustomPortalVal] = useState('');
  const [customBooksVal, setCustomBooksVal] = useState('');

  const gstFileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { setRows(reconciliations); }, [reconciliations]);

  if (!activeCase || !activeClient) {
    return (
      <div className="flex items-center justify-center h-full p-8 text-gray-500 text-xs">
        No active notice selected. Please select a notice to view reconciliations.
      </div>
    );
  }

  const caseId = activeCase.id;

  // ── Portal return uploads ────────────────────────────────────────────────
  const handleGstUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setIsParsing(true);
    setParseNote(null);
    try {
      const collected: ParsedFigure[] = [];
      for (const f of files) {
        try {
          collected.push(...(await parseGstReturnFile(f)));
        } catch (err: any) {
          setParseNote(`Could not read ${f.name}: ${err.message}. Upload the portal's Excel/CSV export, or add the figure manually below.`);
        }
      }
      if (collected.length === 0 && !parseNote) {
        setParseNote(
          `No GST figures were recognised in ${files.map((f) => f.name).join(', ')}. ` +
          `The portal PDF can't be read directly — download the Excel/CSV export, or add figures manually below.`,
        );
      }
      const next = [...portalFigures, ...collected];
      await onSavePortalFigures(next);
      if (collected.length) setParseNote(`Detected ${collected.length} figure(s) from ${files.length} file(s). Review them, then Auto-fill schedules.`);
    } finally {
      setIsParsing(false);
      if (gstFileRef.current) gstFileRef.current.value = '';
    }
  };

  const updateFigure = (id: string, patch: Partial<ParsedFigure>) =>
    onSavePortalFigures(portalFigures.map((f) => (f.id === id ? { ...f, ...patch } : f)));

  const deleteFigure = (id: string) =>
    onSavePortalFigures(portalFigures.filter((f) => f.id !== id));

  const addBlankFigure = () =>
    onSavePortalFigures([
      ...portalFigures,
      { id: `fig_${Date.now()}`, sourceFile: 'manual entry', docType: 'OTHER', label: '', value: 0 },
    ]);

  const autofillSchedules = async () => {
    const updated = applyFiguresToSchedules(rows, portalFigures).map((r) => ({ ...r, caseId }));
    setRows(updated);
    await onSaveReconciliations(updated);
    setParseNote('Schedules auto-filled from the detected figures where a match was found. Adjust any cell below.');
  };

  // ── Schedule cell editing ───────────────────────────────────────────────
  const round2 = (n: number) => Math.round((n || 0) * 100) / 100;
  const editCell = (id: string, field: 'noticeValue' | 'portalValue' | 'booksValue', raw: string) => {
    const n = round2(Number(raw.replace(/[^0-9.\-]/g, '')) || 0);
    setRows((prev) => prev.map((r) => (r.id === id ? recomputeItem({ ...r, [field]: n }) : r)));
  };
  const commitRows = () => onSaveReconciliations(rows.map((r) => ({ ...r, caseId })));

  const deleteRow = async (id: string) => {
    const next = rows.filter((r) => r.id !== id);
    setRows(next);
    await onSaveReconciliations(next.map((r) => ({ ...r, caseId })));
  };

  // ── Excel exports ───────────────────────────────────────────────────────
  const handleExportExcel = () => {
    const actionPoints = documentItems.map((d) => ({
      document: d.docName,
      category: d.category,
      status: d.status,
      forIssue: d.remarks || '',
    }));
    exportReconciliationsToExcel(
      activeClient.legalName,
      activeClient.gstin,
      activeCase.noticeNumber,
      activeCase.period || activeCase.replyDeadline,
      rows,
      portalFigures,
      actionPoints,
    );
  };

  const addStandardSchedules = async () => {
    const std = buildRequiredSchedules(issues, activeCase).map((r) => ({ ...r, caseId }));
    const existing = new Set(rows.map((r) => r.reconType));
    const toAdd = std.filter((r) => !existing.has(r.reconType));
    if (toAdd.length === 0) { setParseNote('All standard schedules for this notice are already present.'); return; }
    const next = [...rows, ...toAdd];
    setRows(next);
    await onSaveReconciliations(next);
    setParseNote(`Added ${toAdd.length} standard schedule(s) for this notice.`);
  };

  const handleAddCustom = async (e: React.FormEvent) => {
    e.preventDefault();
    const item = calculateReconciliation(customReconType, customPeriod, Number(customNoticeVal) || 0, Number(customPortalVal) || 0, Number(customBooksVal) || 0);
    item.caseId = caseId;
    const next = [item, ...rows];
    setRows(next);
    await onSaveReconciliations(next);
    setShowRecalcModal(false);
  };

  const filedFor = (n?: number) => {
    if (!n) return 'General';
    const iss = issues.find((i) => i.issueNumber === n);
    return iss ? `Issue ${n}: ${iss.title}` : `Issue ${n}`;
  };
  const uploadedFiles = [...new Set(portalFigures.map((f) => f.sourceFile))];

  return (
    <div className="p-6 space-y-5 overflow-y-auto h-full bg-[#F8FAFC]">
      {/* Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-2xs flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-emerald-50 text-emerald-700 rounded-xl border border-emerald-200">
            <Calculator className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900">Reconciliation workpaper</h1>
            <p className="text-xs text-slate-500">
              Upload the GST returns and ledgers the notice relies on, reconcile against the demand, export the workpaper.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <input ref={gstFileRef} type="file" multiple accept=".xlsx,.xls,.csv" onChange={handleGstUpload} className="hidden" />
          <button
            onClick={() => gstFileRef.current?.click()}
            disabled={isParsing}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-[#4338CA] hover:bg-[#3730A3] text-white rounded-xl text-xs font-semibold shadow-xs cursor-pointer disabled:opacity-50"
          >
            <Upload className="w-4 h-4" />
            <span>{isParsing ? 'Reading…' : 'Upload GST returns'}</span>
          </button>
          <button
            onClick={() => setShowRecalcModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 rounded-xl text-xs font-semibold shadow-2xs cursor-pointer"
          >
            <Plus className="w-4 h-4" /> <span>Add schedule</span>
          </button>
          <button
            onClick={handleExportExcel}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-xs cursor-pointer"
          >
            <Download className="w-4 h-4" /> <span>Export workpaper</span>
          </button>
        </div>
      </div>

      {/* Portal figures */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
            <FileSpreadsheet className="w-3.5 h-3.5 text-[#4338CA]" /> Portal figures
            <span className="text-slate-400 font-medium normal-case">({portalFigures.length} detected)</span>
          </span>
          <div className="flex items-center gap-2">
            <button onClick={addBlankFigure} className="text-[11px] font-semibold text-[#4338CA] hover:underline cursor-pointer">+ Add figure</button>
            <button
              onClick={autofillSchedules}
              disabled={portalFigures.length === 0}
              className="flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-[#4338CA] hover:bg-indigo-100 disabled:opacity-40 cursor-pointer"
            >
              <Wand2 className="w-3 h-3" /> Auto-fill schedules
            </button>
          </div>
        </div>

        <div className="p-4 space-y-3">
          <div
            onClick={() => gstFileRef.current?.click()}
            className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-4 text-center hover:border-[#4338CA]"
          >
            <Upload className="mb-1 h-5 w-5 text-[#4338CA]" />
            <div className="text-xs font-semibold text-slate-700">Drop GSTR-3B / 1 / 2B / 9 / 9C, cash &amp; credit ledgers, comparison statement</div>
            <div className="text-[11px] text-slate-500">Portal Excel or CSV exports · one or many files</div>
          </div>

          {uploadedFiles.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {uploadedFiles.map((f) => (
                <span key={f} className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-medium text-slate-600">
                  {f} · {portalFigures.filter((x) => x.sourceFile === f).length}
                </span>
              ))}
            </div>
          )}

          {parseNote && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] text-amber-800">{parseNote}</div>
          )}

          {portalFigures.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-200">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-[10px] font-bold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Source</th>
                    <th className="px-3 py-2">Document</th>
                    <th className="px-3 py-2">Figure</th>
                    <th className="px-3 py-2">Head</th>
                    <th className="px-3 py-2 text-right">Amount (₹)</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {portalFigures.map((f) => (
                    <tr key={f.id}>
                      <td className="px-3 py-1.5 text-slate-400">{f.sourceFile}</td>
                      <td className="px-3 py-1.5">
                        <select
                          value={f.docType}
                          onChange={(e) => updateFigure(f.id, { docType: e.target.value as ParsedFigure['docType'] })}
                          className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[11px]"
                        >
                          {['GSTR-3B','GSTR-1','GSTR-2B','GSTR-2A','GSTR-9','GSTR-9C','CASH_LEDGER','CREDIT_LEDGER','COMPARISON','BOOKS','OTHER'].map((d) => (
                            <option key={d} value={d}>{d}</option>
                          ))}
                        </select>
                      </td>
                      <td className="px-3 py-1.5">
                        <input
                          value={f.label}
                          onChange={(e) => updateFigure(f.id, { label: e.target.value })}
                          placeholder="e.g. GSTR-2B ITC available"
                          className="w-full min-w-[200px] rounded border border-slate-200 px-1.5 py-0.5 text-[11px]"
                        />
                      </td>
                      <td className="px-3 py-1.5">
                        <select
                          value={f.head || ''}
                          onChange={(e) => updateFigure(f.id, { head: (e.target.value || undefined) as ParsedFigure['head'] })}
                          className="rounded border border-slate-200 bg-white px-1 py-0.5 text-[11px]"
                        >
                          <option value="">—</option>
                          {['IGST','CGST','SGST','CESS','TOTAL','VALUE'].map((h) => <option key={h} value={h}>{h}</option>)}
                        </select>
                      </td>
                      <td className="px-3 py-1.5 text-right">
                        <input
                          value={String(f.value)}
                          onChange={(e) => updateFigure(f.id, { value: Number(e.target.value.replace(/[^0-9.\-]/g, '')) || 0 })}
                          className="w-28 rounded border border-slate-200 px-1.5 py-0.5 text-right font-mono text-[11px]"
                        />
                      </td>
                      <td className="px-3 py-1.5 text-right">
                        <button onClick={() => deleteFigure(f.id)} className="text-slate-300 hover:text-red-600 cursor-pointer">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Schedules */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-2xs">
        <div className="px-5 py-3 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
            Reconciliation schedules ({rows.length})
          </span>
          <div className="flex items-center gap-3">
            <button onClick={addStandardSchedules} className="text-[11px] font-semibold text-[#4338CA] hover:underline cursor-pointer">
              + Standard schedules for this notice
            </button>
            <span className="text-[11px] text-slate-500 font-mono">{activeClient.legalName} · {activeClient.gstin}</span>
          </div>
        </div>

        {rows.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No schedules yet. They are created automatically when a notice is analysed — or click <strong>Add schedule</strong>.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 border-b border-slate-200 uppercase text-[10px] font-bold tracking-wider">
                <tr>
                  <th className="px-4 py-3">Schedule</th>
                  <th className="px-4 py-3 text-right">Notice / demand</th>
                  <th className="px-4 py-3 text-right">Portal / return</th>
                  <th className="px-4 py-3 text-right">Books</th>
                  <th className="px-4 py-3 text-right">Variance</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-4 py-3">Analysis</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {rows.map((r) => {
                  const mismatch = r.status === 'MISMATCH';
                  const missing = r.status === 'MISSING_DATA';
                  return (
                    <tr key={r.id} className="align-top hover:bg-slate-50/70">
                      <td className="px-4 py-3">
                        <div className="font-bold text-slate-900">{r.reconType}</div>
                        <div className="text-[10px] text-slate-400">{r.period} · {filedFor(r.issueNumber)}</div>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input value={String(round2(r.noticeValue))} onChange={(e) => editCell(r.id, 'noticeValue', e.target.value)} onBlur={commitRows}
                          className="w-28 rounded border border-slate-200 px-1.5 py-1 text-right font-mono" />
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input value={String(round2(r.portalValue))} onChange={(e) => editCell(r.id, 'portalValue', e.target.value)} onBlur={commitRows}
                          className="w-28 rounded border border-slate-200 px-1.5 py-1 text-right font-mono text-blue-700" />
                        {r.portalHint && <div className="mt-0.5 text-[9px] text-slate-400 max-w-[150px] ml-auto">{r.portalHint}</div>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <input value={String(round2(r.booksValue))} onChange={(e) => editCell(r.id, 'booksValue', e.target.value)} onBlur={commitRows}
                          className="w-28 rounded border border-slate-200 px-1.5 py-1 text-right font-mono text-slate-700" />
                        {r.booksHint && <div className="mt-0.5 text-[9px] text-slate-400 max-w-[150px] ml-auto">{r.booksHint}</div>}
                      </td>
                      <td className={`px-4 py-3 text-right font-mono font-black ${mismatch ? 'text-red-600' : missing ? 'text-slate-400' : 'text-emerald-600'}`}>
                        {inr(r.variance)}
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold ${
                          mismatch ? 'bg-red-50 text-red-700 border border-red-200'
                            : missing ? 'bg-slate-100 text-slate-500 border border-slate-200'
                            : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}`}>
                          {mismatch ? <AlertTriangle className="w-3 h-3" /> : missing ? null : <CheckCircle2 className="w-3 h-3" />}
                          {r.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[11px] text-slate-600 leading-relaxed max-w-xs">{r.varianceReason}</td>
                      <td className="px-4 py-3 text-right">
                        <button onClick={() => deleteRow(r.id)} className="text-slate-300 hover:text-red-600 cursor-pointer">
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showRecalcModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <h2 className="text-sm font-bold text-slate-900">Add reconciliation schedule</h2>
              <button onClick={() => setShowRecalcModal(false)} className="text-slate-400 hover:text-slate-600 cursor-pointer text-lg leading-none">×</button>
            </div>
            <form onSubmit={handleAddCustom} className="p-6 space-y-3.5 text-xs">
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Schedule</label>
                <input value={customReconType} onChange={(e) => setCustomReconType(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-[#4338CA]" />
              </div>
              <div>
                <label className="block font-semibold text-slate-600 mb-1">Period</label>
                <input value={customPeriod} onChange={(e) => setCustomPeriod(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-[#4338CA]" />
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[['Notice / demand', customNoticeVal, setCustomNoticeVal], ['Portal / return', customPortalVal, setCustomPortalVal], ['Books', customBooksVal, setCustomBooksVal]].map(([lbl, val, setter]: any) => (
                  <div key={lbl}>
                    <label className="block font-semibold text-slate-600 mb-1">{lbl} (₹)</label>
                    <input type="number" value={val} onChange={(e) => setter(e.target.value)}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:border-[#4338CA]" />
                  </div>
                ))}
              </div>
              <div className="p-3 bg-slate-50 rounded-xl text-center">
                <span className="text-[11px] text-slate-500 font-semibold uppercase">Variance</span>
                <div className="text-base font-black text-red-600 mt-0.5">
                  {inr(Math.abs((Number(customNoticeVal) || 0) - (Number(customPortalVal) || 0)))}
                </div>
              </div>
              <div className="pt-3 border-t border-slate-200 flex justify-end gap-2">
                <button type="button" onClick={() => setShowRecalcModal(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-semibold cursor-pointer">Cancel</button>
                <button type="submit" className="px-5 py-2 bg-[#4338CA] text-white font-semibold rounded-lg hover:bg-[#3730A3] cursor-pointer shadow-xs">Add schedule</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
