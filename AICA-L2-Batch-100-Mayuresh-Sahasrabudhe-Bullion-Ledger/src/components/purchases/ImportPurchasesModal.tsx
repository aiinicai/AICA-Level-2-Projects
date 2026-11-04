import React, { useState, useRef } from 'react';
import { Purchase } from '../../types';
import {
  parsePurchasesFile,
  generatePurchaseTemplateXLSX,
  PurchaseValidationResult,
} from '../../utils/purchaseExcel';
import { formatINR, formatGrams } from '../../utils/formatters';
import {
  X,
  Upload,
  Download,
  AlertCircle,
  CheckCircle,
  AlertTriangle,
  FileSpreadsheet,
} from 'lucide-react';

interface ImportPurchasesModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (purchases: Purchase[], batchId: string) => void;
  existingPurchases: Purchase[];
}

export const ImportPurchasesModal: React.FC<ImportPurchasesModalProps> = ({
  isOpen,
  onClose,
  onImport,
  existingPurchases,
}) => {
  const [fileName, setFileName] = useState<string | null>(null);
  const [result, setResult] = useState<PurchaseValidationResult | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDownloadTemplate = () => {
    const buffer = generatePurchaseTemplateXLSX();
    const blob = new Blob([buffer as any], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Bullion_Ledger_Purchase_Template.xlsx';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setFileName(file.name);
    setIsProcessing(true);

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const buffer = event.target?.result;
        if (buffer) {
          const res = parsePurchasesFile(buffer as ArrayBuffer, file.name, existingPurchases);
          setResult(res);
        }
      } catch (err: any) {
        alert(`Error parsing spreadsheet: ${err.message}`);
      } finally {
        setIsProcessing(false);
      }
    };

    reader.readAsArrayBuffer(file);
  };

  const handleConfirmImport = () => {
    if (!result || result.validPurchases.length === 0) return;
    onImport(result.validPurchases, result.batchId);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-stone-900/60 backdrop-blur-2xs flex items-center justify-center p-3 sm:p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full border border-stone-200 overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-stone-200 bg-[#FAF7F2] shrink-0">
          <div>
            <h2 className="text-base font-bold text-stone-900 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-[#B88B2A]" />
              Import Purchases from XLSX / CSV
            </h2>
            <p className="text-xs text-stone-500">
              Bulk import bullion invoices with automatic verification and duplicate alerts
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-stone-400 hover:text-stone-700 p-1 rounded-md"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-5 overflow-y-auto space-y-4">
          {/* Action Row */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-stone-50 p-4 rounded-xl border border-stone-200">
            <div>
              <span className="text-xs font-bold text-stone-800 block">
                Need the standardized spreadsheet format?
              </span>
              <p className="text-[11px] text-stone-500">
                Download the verified template with validation guidance and example rows.
              </p>
            </div>
            <button
              type="button"
              onClick={handleDownloadTemplate}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-stone-800 bg-white hover:bg-stone-100 border border-stone-300 rounded-lg shadow-2xs transition-colors shrink-0"
            >
              <Download className="w-3.5 h-3.5 text-[#B88B2A]" />
              <span>Download XLSX Template</span>
            </button>
          </div>

          {/* Upload Dropzone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-stone-300 hover:border-[#B88B2A] rounded-xl p-6 text-center cursor-pointer transition-colors bg-[#FAF7F2]/50 hover:bg-[#FAF7F2]"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <Upload className="w-8 h-8 text-[#B88B2A] mx-auto mb-2" />
            <p className="text-xs font-semibold text-stone-800">
              {fileName ? fileName : 'Click to select or drop an Excel (.xlsx) or CSV file'}
            </p>
            <p className="text-[11px] text-stone-500 mt-1">
              Supports .xlsx, .xls, and UTF-8 CSV with quoted headers
            </p>
          </div>

          {isProcessing && (
            <div className="text-center py-4 text-xs text-stone-500">
              Analyzing file and validating fields...
            </div>
          )}

          {/* Validation Summary */}
          {result && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-center">
                  <span className="text-xs font-semibold text-emerald-800 block">
                    Valid Records
                  </span>
                  <span className="text-lg font-bold text-emerald-700">
                    {result.validPurchases.length}
                  </span>
                </div>
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-center">
                  <span className="text-xs font-semibold text-amber-800 block">
                    Duplicate Warnings
                  </span>
                  <span className="text-lg font-bold text-amber-700">
                    {result.warnings.length}
                  </span>
                </div>
                <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-center">
                  <span className="text-xs font-semibold text-rose-800 block">
                    Invalid Errors
                  </span>
                  <span className="text-lg font-bold text-rose-700">
                    {result.errors.length}
                  </span>
                </div>
              </div>

              {/* Errors list if any */}
              {result.errors.length > 0 && (
                <div className="bg-rose-50 border border-rose-200 rounded-lg p-3 text-xs text-rose-900 space-y-1">
                  <span className="font-bold flex items-center gap-1 text-rose-800">
                    <AlertCircle className="w-4 h-4 text-rose-600" />
                    Validation Errors ({result.errors.length}):
                  </span>
                  <ul className="list-disc pl-5 space-y-0.5 text-[11px] max-h-24 overflow-y-auto">
                    {result.errors.map((err, i) => (
                      <li key={i}>
                        Row {err.row}: <span className="font-semibold">{err.field}</span> - {err.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Warnings list if any */}
              {result.warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-900 space-y-1">
                  <span className="font-bold flex items-center gap-1 text-amber-800">
                    <AlertTriangle className="w-4 h-4 text-amber-600" />
                    Duplicate Warnings ({result.warnings.length}):
                  </span>
                  <ul className="list-disc pl-5 space-y-0.5 text-[11px] max-h-20 overflow-y-auto">
                    {result.warnings.map((w, i) => (
                      <li key={i}>
                        Row {w.row}: {w.message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Preview Table of Valid Purchases */}
              {result.validPurchases.length > 0 && (
                <div>
                  <span className="text-xs font-bold text-stone-800 block mb-2">
                    Preview of Ready-to-Import Lots ({result.validPurchases.length}):
                  </span>
                  <div className="border border-stone-200 rounded-lg overflow-x-auto max-h-56">
                    <table className="w-full text-[11px] text-left">
                      <thead className="bg-[#FAF7F2] text-stone-700 border-b border-stone-200 font-semibold sticky top-0">
                        <tr>
                          <th className="py-2 px-2.5">Date</th>
                          <th className="py-2 px-2.5">Seller</th>
                          <th className="py-2 px-2.5">Invoice #</th>
                          <th className="py-2 px-2.5">Metal</th>
                          <th className="py-2 px-2.5">Form</th>
                          <th className="py-2 px-2.5">Weight</th>
                          <th className="py-2 px-2.5">Rate</th>
                          <th className="py-2 px-2.5">Invested</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-stone-100">
                        {result.validPurchases.map((p) => (
                          <tr key={p.id} className="hover:bg-stone-50">
                            <td className="py-1.5 px-2.5 whitespace-nowrap">{p.purchaseDate}</td>
                            <td className="py-1.5 px-2.5 font-medium">{p.seller}</td>
                            <td className="py-1.5 px-2.5 font-mono">{p.invoiceNumber}</td>
                            <td className="py-1.5 px-2.5">{p.metal}</td>
                            <td className="py-1.5 px-2.5">{p.form}</td>
                            <td className="py-1.5 px-2.5">{formatGrams(p.weightGrams)}</td>
                            <td className="py-1.5 px-2.5">₹{p.purchaseRate}/g</td>
                            <td className="py-1.5 px-2.5 font-semibold text-stone-900">
                              {formatINR(p.investedAmount)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-stone-200 bg-[#FAF7F2] flex items-center justify-between shrink-0">
          <span className="text-xs text-stone-500">
            {result ? `Batch ID: ${result.batchId}` : 'Upload a file to start validation'}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-1.5 text-xs font-medium text-stone-600 hover:text-stone-900 bg-stone-100 rounded-lg"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmImport}
              disabled={!result || result.validPurchases.length === 0}
              className={`px-4 py-1.5 text-xs font-semibold text-white rounded-lg transition-colors ${
                result && result.validPurchases.length > 0
                  ? 'bg-[#B88B2A] hover:bg-[#8E6B1D] shadow-2xs'
                  : 'bg-stone-300 cursor-not-allowed'
              }`}
            >
              Confirm & Import ({result?.validPurchases.length || 0})
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
