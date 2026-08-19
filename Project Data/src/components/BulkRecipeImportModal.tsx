import React, { useState } from 'react';
import { Upload, Download, BookOpen, CheckCircle, AlertCircle, RefreshCw, X, ArrowRight, Sparkles } from 'lucide-react';
import { Recipe, InventoryItem, ImportSummary } from '../types';
import { downloadRecipeExcelTemplate, parseAndValidateRecipeExcel, RecipeImportResult } from '../services/excelService';

interface BulkRecipeImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  recipes: Recipe[];
  inventory: InventoryItem[];
  onImportSuccess: (result: RecipeImportResult) => void;
}

export const BulkRecipeImportModal: React.FC<BulkRecipeImportModalProps> = ({
  isOpen,
  onClose,
  recipes,
  inventory,
  onImportSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [importResult, setImportResult] = useState<RecipeImportResult | null>(null);
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
      const result = await parseAndValidateRecipeExcel(file, recipes, inventory);
      setImportResult(result);
      if (result.summary.errors.length === 0) {
        onImportSuccess(result);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error processing Recipe Excel file');
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
            <div className="p-2.5 rounded-2xl bg-orange-500/10 text-orange-600 dark:text-orange-400">
              <BookOpen className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                Import Recipe Master
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Bulk add or update recipes with goals & auto-syncing ingredients
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
        <div className="p-4 rounded-2xl bg-orange-50 dark:bg-orange-950/30 border border-orange-200 dark:border-orange-800/50 flex items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-bold text-orange-900 dark:text-orange-300">
              Download Recipe Excel Template
            </h4>
            <p className="text-[11px] text-orange-700 dark:text-orange-400 mt-0.5">
              Includes columns for Dietary Goals, Ingredients (Name:Qty:Unit), and Instructions.
            </p>
          </div>
          <button
            onClick={downloadRecipeExcelTemplate}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-orange-600 hover:bg-orange-700 text-white shadow-md transition-all whitespace-nowrap"
          >
            <Download className="w-3.5 h-3.5" />
            Download (.xlsx)
          </button>
        </div>

        {/* Notice for Auto Ingredient Sync */}
        <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/50 flex items-start gap-2.5 text-xs text-emerald-800 dark:text-emerald-300">
          <Sparkles className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Auto-Master Ingredient Sync:</span>
            <p className="text-[11px] opacity-90 mt-0.5">
              If an imported recipe contains an ingredient not present in the Inventory Master, it will automatically be created in the inventory list so it can be reordered in the Grocery List when stock is low!
            </p>
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
                Drag & Drop recipe Excel file here
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

        {/* Success Report */}
        {importResult && importResult.summary.errors.length === 0 && (
          <div className="p-3.5 rounded-2xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 text-xs space-y-1">
            <h4 className="font-bold flex items-center gap-1.5">
              <CheckCircle className="w-4 h-4 text-emerald-500" />
              Recipe Import Successful!
            </h4>
            <p>Imported Recipes: {importResult.summary.importedRows}</p>
            <p>New Recipes Created: {importResult.summary.newIngredientsCount}</p>
            {importResult.autoAddedInventoryItems.length > 0 && (
              <p className="font-bold text-orange-600 dark:text-orange-400 mt-1">
                ✨ {importResult.autoAddedInventoryItems.length} New Ingredient(s) auto-added to Inventory Master for reordering!
              </p>
            )}
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
            className="px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 text-white shadow-lg shadow-orange-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            Process & Import Recipes
          </button>
        </div>
      </div>
    </div>
  );
};
