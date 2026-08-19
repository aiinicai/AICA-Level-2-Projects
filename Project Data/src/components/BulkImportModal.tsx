import React, { useState } from 'react';
import { Upload, Download, FileSpreadsheet, CheckCircle, AlertCircle, RefreshCw, X, ArrowRight } from 'lucide-react';
import { InventoryItem, ImportSummary } from '../types';
import { downloadSampleExcelTemplate, parseAndValidateInventoryExcel } from '../services/excelService';

interface BulkImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  inventory: InventoryItem[];
  onImportSuccess: (updatedInventory: InventoryItem[], summary: ImportSummary) => void;
}

export const BulkImportModal: React.FC<BulkImportModalProps> = ({
  isOpen,
  onClose,
  inventory,
  onImportSuccess,
}) => {
  const [selectedMode, setSelectedMode] = useState<'replace' | 'update'>('update');
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        setFile(droppedFile);
        setErrorMessage(null);
      } else {
        setErrorMessage('Please upload a valid Excel file (.xlsx or .xls)');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const handleProcessImport = async () => {
    if (!file) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const { summary, updatedInventory } = await parseAndValidateInventoryExcel(file, inventory, selectedMode);
      setImportSummary(summary);
      if (summary.errors.length === 0) {
        onImportSuccess(updatedInventory, summary);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error processing Excel file');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 max-w-xl w-full shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <FileSpreadsheet className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Import Opening Inventory
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Initialize or update stock in bulk using Excel template
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Download Sample Template Banner */}
        <div className="p-4 rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50 flex items-center justify-between">
          <div>
            <h4 className="text-xs font-bold text-amber-900 dark:text-amber-300">
              Need the template?
            </h4>
            <p className="text-[11px] text-amber-700 dark:text-amber-400">
              Includes all ingredients dynamically extracted from all 90 recipes!
            </p>
          </div>
          <button
            onClick={downloadSampleExcelTemplate}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-600 hover:bg-amber-700 text-white shadow-md transition-all whitespace-nowrap"
          >
            <Download className="w-3.5 h-3.5" />
            Download Template (.xlsx)
          </button>
        </div>

        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
            Select Import Mode
          </label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setSelectedMode('update')}
              className={`p-3.5 rounded-2xl border text-left transition-all ${
                selectedMode === 'update'
                  ? 'bg-orange-500/10 border-orange-500 text-orange-700 dark:text-orange-400 ring-2 ring-orange-500/20'
                  : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
              }`}
            >
              <span className="text-xs font-bold block">1. Update Inventory</span>
              <span className="text-[10px] opacity-80 block mt-0.5">
                Add imported quantities to existing stock (e.g. after fresh grocery shopping)
              </span>
            </button>

            <button
              type="button"
              onClick={() => setSelectedMode('replace')}
              className={`p-3.5 rounded-2xl border text-left transition-all ${
                selectedMode === 'replace'
                  ? 'bg-orange-500/10 border-orange-500 text-orange-700 dark:text-orange-400 ring-2 ring-orange-500/20'
                  : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400'
              }`}
            >
              <span className="text-xs font-bold block">2. Replace Inventory</span>
              <span className="text-[10px] opacity-80 block mt-0.5">
                Overwrite existing inventory quantities completely (Full stock audit)
              </span>
            </button>
          </div>
        </div>

        {/* File Dropzone */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-3xl p-8 text-center transition-all ${
            isDragging
              ? 'border-orange-500 bg-orange-500/10'
              : 'border-slate-300 dark:border-slate-700 hover:border-orange-400'
          }`}
        >
          <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          {file ? (
            <div>
              <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
                Selected: {file.name}
              </p>
              <p className="text-[10px] text-slate-400 mt-1">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Drag & Drop completed Excel file here
              </p>
              <p className="text-[10px] text-slate-400 mt-1">or</p>
              <label className="mt-2 inline-block px-4 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 text-xs font-semibold text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700">
                Browse File
                <input
                  type="file"
                  accept=".xlsx, .xls"
                  onChange={handleFileSelect}
                  className="hidden"
                />
              </label>
            </div>
          )}
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Validation Errors Report */}
        {importSummary && importSummary.errors.length > 0 && (
          <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 space-y-2">
            <h4 className="text-xs font-bold text-rose-800 dark:text-rose-300 flex items-center gap-1.5">
              <AlertCircle className="w-4 h-4" />
              Found {importSummary.errors.length} Validation Errors
            </h4>
            <div className="max-h-32 overflow-y-auto space-y-1.5 text-[11px] pr-1">
              {importSummary.errors.map((err, idx) => (
                <div key={idx} className="p-2 rounded-lg bg-white/60 dark:bg-slate-800/60 text-slate-800 dark:text-slate-200">
                  <span className="font-bold text-rose-600 dark:text-rose-400">
                    Row {err.row} ({err.ingredientName}):
                  </span>{' '}
                  {err.issue}. <span className="italic text-slate-500 dark:text-slate-400">Fix: {err.suggestedFix}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Success Report */}
        {importSummary && importSummary.errors.length === 0 && (
          <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs space-y-1">
            <h4 className="font-bold flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-500" />
              Import Successful!
            </h4>
            <p>Imported Rows: {importSummary.importedRows}</p>
            <p>New Ingredients Created: {importSummary.newIngredientsCount}</p>
            <p>Existing Ingredients Updated: {importSummary.updatedIngredientsCount}</p>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100 dark:border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!file || isLoading}
            onClick={handleProcessImport}
            className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-600 hover:to-teal-700 text-white shadow-lg shadow-emerald-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            Process & Update Inventory
          </button>
        </div>
      </div>
    </div>
  );
};
