import React, { useState } from 'react';
import { 
  X, 
  Calculator, 
  Plus, 
  Trash2, 
  CheckCircle2, 
  AlertTriangle, 
  Sparkles, 
  FileText 
} from 'lucide-react';
import { InconsistencyItem } from '../types';
import { performOfflineReconciliation } from '../engine/offlineReconciler';

interface NoteReconcilerModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialItem?: InconsistencyItem | null;
}

export const NoteReconcilerModal: React.FC<NoteReconcilerModalProps> = ({
  isOpen,
  onClose,
  initialItem,
}) => {
  const [lineName, setLineName] = useState(initialItem?.lineItem || 'Trade Receivables (Gross)');
  const [primaryFigure, setPrimaryFigure] = useState(
    initialItem?.primaryFigure.replace(/[^0-9.-]/g, '') || '18450.00'
  );
  const [noteTitle, setNoteTitle] = useState(initialItem?.noteRef || 'Note 11: Trade Receivables Breakup');
  
  const [rows, setRows] = useState<Array<{ name: string; amount: string; isDeduction: boolean }>>([
    { name: 'Undisputed - Considered Good', amount: '17200.00', isDeduction: false },
    { name: 'Significant Credit Risk', amount: '1650.00', isDeduction: false },
    { name: 'Allowance for ECL (Impairment)', amount: '600.00', isDeduction: true },
    { name: 'Disputed - Considered Good', amount: '200.00', isDeduction: false },
  ]);

  const [aiMemo, setAiMemo] = useState<string | null>(null);
  const [isGeneratingMemo, setIsGeneratingMemo] = useState(false);

  if (!isOpen) return null;

  const primaryNum = parseFloat(primaryFigure) || 0;

  const noteSum = rows.reduce((acc, r) => {
    const val = parseFloat(r.amount) || 0;
    return r.isDeduction ? acc - val : acc + val;
  }, 0);

  const variance = primaryNum - noteSum;
  const isTallied = Math.abs(variance) < 0.001;

  const addRow = () => {
    setRows([...rows, { name: '', amount: '0.00', isDeduction: false }]);
  };

  const removeRow = (idx: number) => {
    setRows(rows.filter((_, i) => i !== idx));
  };

  const updateRow = (idx: number, field: string, value: any) => {
    const newRows = [...rows];
    newRows[idx] = { ...newRows[idx], [field]: value };
    setRows(newRows);
  };

  const handleGenerateAiMemo = async () => {
    setIsGeneratingMemo(true);
    try {
      // Execute 100% offline reconciliation engine
      const offlineResult = performOfflineReconciliation(
        lineName,
        primaryFigure,
        noteTitle,
        rows
      );
      setAiMemo(offlineResult.memo);
    } catch (err) {
      console.error('Offline reconciler error:', err);
    } finally {
      setIsGeneratingMemo(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white border-2 border-[#141414] shadow-dense max-w-2xl w-full overflow-hidden animate-scaleIn my-8">
        {/* Header */}
        <div className="bg-[#141414] text-white p-4 flex items-center justify-between border-b border-[#141414]">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 bg-[#00FF00] flex items-center justify-center text-[#141414] font-bold">
              <Calculator className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs sm:text-sm uppercase tracking-tight text-white font-mono">
                Note Reconciler & Footing Validator
              </h3>
              <p className="text-[10px] text-neutral-400 font-serif italic">
                Calculate sub-schedule casting sums and test adjustments in real-time
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-white p-1 hover:bg-neutral-800 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <div className="p-5 space-y-4 max-h-[75vh] overflow-y-auto bg-white">
          {/* Primary Statement Figure Inputs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-[#F9F9F7] p-3.5 border border-[#141414]">
            <div>
              <label className="text-[10px] font-mono font-bold uppercase text-[#141414] block mb-1">
                Primary Line Item Name:
              </label>
              <input
                type="text"
                value={lineName}
                onChange={(e) => setLineName(e.target.value)}
                className="w-full text-xs p-1.5 border border-[#141414] bg-white font-sans text-[#141414] focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] font-mono font-bold uppercase text-[#141414] block mb-1">
                Reported Amount on Primary Statement:
              </label>
              <input
                type="number"
                step="any"
                value={primaryFigure}
                onChange={(e) => setPrimaryFigure(e.target.value)}
                className="w-full text-xs p-1.5 font-mono font-bold border border-[#141414] bg-white text-[#141414] focus:outline-none"
              />
            </div>
          </div>

          {/* Note Sub-Schedules List */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-[10px] font-mono font-bold uppercase text-[#141414]">
                Note Sub-Schedules / Itemized Breakup:
              </label>
              <button
                onClick={addRow}
                className="inline-flex items-center space-x-1 text-[10px] font-mono font-bold uppercase text-[#141414] bg-[#E4E3E0] hover:bg-[#D1D0CC] px-2 py-1 border border-[#141414]"
              >
                <Plus className="w-3 h-3" />
                <span>Add Row</span>
              </button>
            </div>

            <div className="space-y-1.5">
              {rows.map((row, idx) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <input
                    type="text"
                    placeholder="Sub-item description..."
                    value={row.name}
                    onChange={(e) => updateRow(idx, 'name', e.target.value)}
                    className="flex-1 text-xs p-1.5 border border-[#141414] bg-[#F9F9F7] text-[#141414]"
                  />
                  <input
                    type="number"
                    step="any"
                    placeholder="0.00"
                    value={row.amount}
                    onChange={(e) => updateRow(idx, 'amount', e.target.value)}
                    className="w-28 text-xs p-1.5 font-mono border border-[#141414] bg-white text-right text-[#141414]"
                  />
                  <button
                    type="button"
                    onClick={() => updateRow(idx, 'isDeduction', !row.isDeduction)}
                    className={`px-2 py-1 text-[9px] font-mono font-bold uppercase transition border border-[#141414] ${
                      row.isDeduction
                        ? 'bg-red-600 text-white'
                        : 'bg-green-700 text-white'
                    }`}
                  >
                    {row.isDeduction ? '(-) LESS' : '(+) ADD'}
                  </button>
                  <button
                    onClick={() => removeRow(idx)}
                    className="p-1.5 text-neutral-400 hover:text-red-600"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Mathematical Footing Comparison Bar */}
          <div className="bg-[#141414] text-white p-3.5 border border-[#141414] space-y-1.5 font-mono">
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">SUM OF DETAILED NOTE ITEMS:</span>
              <span className="font-bold text-white">
                {noteSum.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-neutral-400">PRIMARY STATEMENT FIGURE:</span>
              <span className="font-bold text-white">
                {primaryNum.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>
            <div className="pt-2 border-t border-neutral-700 flex items-center justify-between">
              <span className="text-xs font-bold text-neutral-300">VARIANCE / CASTING DIFFERENCE:</span>
              <span
                className={`font-extrabold text-sm ${
                  isTallied ? 'text-[#00FF00]' : 'text-red-400'
                }`}
              >
                {variance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>
            </div>

            <div className="pt-1">
              {isTallied ? (
                <div className="flex items-center space-x-1.5 text-[#00FF00] text-[10px]">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>FOOTING RECONCILED: Zero variance between statement and notes.</span>
                </div>
              ) : (
                <div className="flex items-center space-x-1.5 text-red-400 text-[10px]">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>FOOTING VARIANCE DETECTED: Adjust sub-schedule lines or verify journal entry.</span>
                </div>
              )}
            </div>
          </div>

          {/* AI CA Reconciliation Memo */}
          <div>
            <button
              onClick={handleGenerateAiMemo}
              disabled={isGeneratingMemo}
              className="w-full py-2 px-3 text-xs font-mono font-bold uppercase bg-[#141414] hover:bg-neutral-800 text-white flex items-center justify-center space-x-2 transition border border-[#141414]"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#00FF00]" />
              <span>{isGeneratingMemo ? 'Drafting Audit Memo...' : 'Draft CA Reconciliation Working Memo'}</span>
            </button>

            {aiMemo && (
              <div className="mt-3 p-3 bg-[#F9F9F7] border border-[#141414] text-xs text-[#141414] whitespace-pre-wrap font-serif italic leading-relaxed">
                <div className="font-mono font-bold not-italic text-[10px] uppercase text-[#141414] mb-1 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-[#141414]" />
                  <span>Auditor Note Reconciliation Working Paper:</span>
                </div>
                {aiMemo}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-[#E4E3E0] border-t border-[#141414] flex justify-end">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-xs font-mono font-bold uppercase text-[#141414] bg-white hover:bg-neutral-100 border border-[#141414] transition"
          >
            Close Reconciler
          </button>
        </div>
      </div>
    </div>
  );
};

