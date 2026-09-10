import React, { useState, useRef } from 'react';
import * as XLSX from 'xlsx';
import {
  X,
  Upload,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  FileDown,
  Sparkles,
  ArrowRight,
  Database,
  RefreshCw,
} from 'lucide-react';
import { TrialBalanceItem, TrialBalanceData, ComputedMateriality } from '../types';
import {
  detectHeaders,
  parseRawTableToTB,
  generateTrialBalanceTemplate,
  ColumnMapping,
} from '../utils/tbParser';
import { computeTBSummary, ZENITH_SAMPLE_TRIAL_BALANCE } from '../data/sampleTrialBalance';
import { formatINR, formatCompactINR } from '../utils/calculations';

interface TBImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  materiality: ComputedMateriality;
  onApplyTB: (tbData: TrialBalanceData, syncMateriality?: boolean) => void;
}

export const TBImportModal: React.FC<TBImportModalProps> = ({
  isOpen,
  onClose,
  materiality,
  onApplyTB,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [fileName, setFileName] = useState<string>('');
  const [rawSheetData, setRawSheetData] = useState<any[][] | null>(null);
  const [headers, setHeaders] = useState<string[]>([]);
  const [headerRowIndex, setHeaderRowIndex] = useState<number>(0);
  const [mapping, setMapping] = useState<ColumnMapping>({
    accountCode: '',
    accountName: '',
    scheduleIIIGroup: '',
    category: '',
    debit: '',
    credit: '',
    net: '',
    priorYear: '',
  });

  const [parsedItems, setParsedItems] = useState<TrialBalanceItem[]>([]);
  const [syncMateriality, setSyncMateriality] = useState<boolean>(true);
  const [dragOver, setDragOver] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const processWorkbookData = (data: any[][], name: string) => {
    try {
      const detection = detectHeaders(data);
      setRawSheetData(data);
      setHeaders(detection.headers);
      setHeaderRowIndex(detection.headerRowIndex);
      setMapping(detection.suggestedMapping);
      setFileName(name);
      setErrorMsg('');

      // Try initial parse
      const items = parseRawTableToTB(
        data,
        detection.suggestedMapping,
        detection.headerRowIndex,
        materiality.overallMateriality,
        materiality.performanceMateriality,
        materiality.clearlyTrivialThreshold
      );
      setParsedItems(items);
    } catch (err: any) {
      setErrorMsg(`Failed to parse sheet: ${err.message || 'Unknown format'}`);
    }
  };

  const handleFileSelect = (selectedFile: File) => {
    setFile(selectedFile);
    setErrorMsg('');
    const reader = new FileReader();

    reader.onload = (e) => {
      try {
        const buffer = e.target?.result;
        const wb = XLSX.read(buffer, { type: 'binary' });
        const firstSheetName = wb.SheetNames[0];
        const ws = wb.Sheets[firstSheetName];
        const data: any[][] = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' });

        if (!data || data.length === 0) {
          setErrorMsg('The selected spreadsheet appears to be empty.');
          return;
        }

        processWorkbookData(data, selectedFile.name);
      } catch (err: any) {
        setErrorMsg(`Error reading spreadsheet: ${err.message || 'Invalid file format'}`);
      }
    };

    reader.readAsBinaryString(selectedFile);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleMappingChange = (key: keyof ColumnMapping, val: string) => {
    const updated = { ...mapping, [key]: val };
    setMapping(updated);
    if (rawSheetData) {
      const items = parseRawTableToTB(
        rawSheetData,
        updated,
        headerRowIndex,
        materiality.overallMateriality,
        materiality.performanceMateriality,
        materiality.clearlyTrivialThreshold
      );
      setParsedItems(items);
    }
  };

  const handleLoadSample = () => {
    onApplyTB(ZENITH_SAMPLE_TRIAL_BALANCE, syncMateriality);
    onClose();
  };

  const handleDownloadTemplate = () => {
    const templateBytes = generateTrialBalanceTemplate();
    const blob = new Blob([templateBytes], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Trial_Balance_Import_Template_ICAI.xlsx';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleConfirmImport = () => {
    if (parsedItems.length === 0) {
      setErrorMsg('No valid account rows found to import.');
      return;
    }

    const summary = computeTBSummary(parsedItems);
    const tbData: TrialBalanceData = {
      importedAt: new Date().toISOString(),
      fileName: fileName || 'Imported_Trial_Balance.xlsx',
      items: parsedItems,
      summary,
    };

    onApplyTB(tbData, syncMateriality);
    onClose();
  };

  const summary = parsedItems.length > 0 ? computeTBSummary(parsedItems) : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-3 overflow-y-auto">
      <div className="bg-white dark:bg-[#15191f] text-[#1c222b] dark:text-[#f3f4f6] w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden border border-[#dedbd2] dark:border-[#272f38] flex flex-col max-h-[92vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#dedbd2] dark:border-[#272f38] bg-[#f8f7f4] dark:bg-[#1a2027]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-800 dark:bg-amber-600 text-white flex items-center justify-center shadow-xs">
              <FileSpreadsheet className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                Import Client Trial Balance (TB)
              </h2>
              <p className="text-xs text-stone-500 dark:text-stone-400">
                Supports Excel (.xlsx, .xls) and CSV files • Automatic Schedule III mapping
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadTemplate}
              className="px-2.5 py-1.5 rounded text-xs font-medium text-amber-900 dark:text-amber-300 bg-amber-100 dark:bg-amber-950/60 hover:bg-amber-200 dark:hover:bg-amber-900/60 border border-amber-300 dark:border-amber-800 flex items-center gap-1.5 transition-colors"
              title="Download standardized Excel template with sample Schedule III groupings"
            >
              <FileDown className="w-3.5 h-3.5" />
              <span>Download Template</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 hover:bg-stone-200 dark:hover:bg-stone-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs sm:text-sm">
          {errorMsg && (
            <div className="p-3.5 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-300 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <p className="text-xs leading-relaxed">{errorMsg}</p>
            </div>
          )}

          {/* Upload Drop Zone & Sample Loader */}
          {!rawSheetData && (
            <div className="space-y-4">
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  dragOver
                    ? 'border-amber-600 bg-amber-50/70 dark:bg-amber-950/20 scale-[0.99]'
                    : 'border-stone-300 dark:border-stone-700 hover:border-amber-600 dark:hover:border-amber-500 bg-stone-50/50 dark:bg-[#1a2027]/40'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx, .xls, .csv"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      handleFileSelect(e.target.files[0]);
                    }
                  }}
                  className="hidden"
                />
                <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-400 mx-auto flex items-center justify-center mb-3">
                  <Upload className="w-6 h-6" />
                </div>
                <h3 className="font-semibold text-sm text-stone-900 dark:text-stone-100 mb-1">
                  Drag & drop your client Trial Balance here
                </h3>
                <p className="text-xs text-stone-500 dark:text-stone-400 max-w-md mx-auto">
                  Or click to browse from your computer. Works with standard reports exported from
                  Tally, SAP, Zoho Books, Busy, QuickBooks, or custom client workbooks.
                </p>
              </div>

              {/* Sample TB Card */}
              <div className="p-4 rounded-xl bg-gradient-to-r from-amber-50 to-stone-50 dark:from-amber-950/20 dark:to-stone-900/40 border border-amber-200 dark:border-amber-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-lg bg-amber-200/60 dark:bg-amber-900/60 flex items-center justify-center text-amber-900 dark:text-amber-300">
                    <Database className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-xs sm:text-sm text-stone-900 dark:text-stone-100">
                      Looking for sample data?
                    </h4>
                    <p className="text-xs text-stone-600 dark:text-stone-400">
                      Load the pre-configured Zenith Fabrics Private Limited Trial Balance (₹ 185 Cr Turnover, 35 accounts).
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleLoadSample}
                  className="px-3.5 py-1.5 rounded-md bg-stone-900 hover:bg-stone-800 dark:bg-stone-100 dark:hover:bg-white text-white dark:text-stone-900 text-xs font-semibold shrink-0 transition-colors shadow-xs flex items-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-amber-400 dark:text-amber-600" />
                  <span>Load Zenith Fabrics TB</span>
                </button>
              </div>
            </div>
          )}

          {/* Active Sheet Mapping & Summary Preview */}
          {rawSheetData && (
            <div className="space-y-5">
              {/* File Info Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 p-3 bg-stone-100 dark:bg-[#1a2027] rounded-lg border border-stone-200 dark:border-stone-800 text-xs">
                <div className="flex items-center gap-2">
                  <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                  <span className="font-semibold text-stone-800 dark:text-stone-200">{fileName}</span>
                  <span className="text-stone-400">•</span>
                  <span className="text-stone-500">{parsedItems.length} accounts detected</span>
                </div>
                <button
                  onClick={() => {
                    setRawSheetData(null);
                    setParsedItems([]);
                  }}
                  className="text-stone-600 dark:text-stone-400 hover:text-rose-600 flex items-center gap-1 text-xs"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Choose different file</span>
                </button>
              </div>

              {/* Column Mapping Selectors */}
              <div className="p-4 rounded-lg bg-white dark:bg-[#1c222b] border border-[#dedbd2] dark:border-[#2e3742] space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-xs text-stone-900 dark:text-stone-100 uppercase tracking-wider">
                    Confirm Column Mappings
                  </h4>
                  <span className="text-[11px] text-stone-400">
                    Auto-detected based on header keywords
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Account Code
                    </label>
                    <select
                      value={mapping.accountCode}
                      onChange={(e) => handleMappingChange('accountCode', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(None)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Account / Ledger Name *
                    </label>
                    <select
                      value={mapping.accountName}
                      onChange={(e) => handleMappingChange('accountName', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs font-semibold text-amber-800 dark:text-amber-400"
                    >
                      <option value="">Select column...</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Debit Amount (Dr)
                    </label>
                    <select
                      value={mapping.debit}
                      onChange={(e) => handleMappingChange('debit', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(None / Net)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Credit Amount (Cr)
                    </label>
                    <select
                      value={mapping.credit}
                      onChange={(e) => handleMappingChange('credit', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(None / Net)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Schedule III Group
                    </label>
                    <select
                      value={mapping.scheduleIIIGroup}
                      onChange={(e) => handleMappingChange('scheduleIIIGroup', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(Auto Categorize)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Category (Asset/Liab/Rev)
                    </label>
                    <select
                      value={mapping.category}
                      onChange={(e) => handleMappingChange('category', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(Auto Categorize)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Prior Year Balance
                    </label>
                    <select
                      value={mapping.priorYear}
                      onChange={(e) => handleMappingChange('priorYear', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(None)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-medium text-stone-500 mb-1">
                      Net Closing Balance
                    </label>
                    <select
                      value={mapping.net}
                      onChange={(e) => handleMappingChange('net', e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-stone-900 dark:text-stone-100 text-xs"
                    >
                      <option value="">(Computed from Dr - Cr)</option>
                      {headers.map((h, i) => (
                        <option key={i} value={h}>
                          {h}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Validation & Aggregates Preview */}
              {summary && (
                <div className="p-4 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800 space-y-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {summary.isBalanced ? (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300 dark:bg-emerald-950/60 dark:text-emerald-300 dark:border-emerald-800">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>Trial Balance Balanced (Dr = Cr)</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-300 dark:bg-amber-950/60 dark:text-amber-300 dark:border-amber-800">
                          <AlertTriangle className="w-3.5 h-3.5" />
                          <span>
                            Out of Balance: Diff ₹ {formatINR(summary.difference)}
                          </span>
                        </div>
                      )}
                    </div>

                    <label className="flex items-center gap-2 text-xs font-medium cursor-pointer text-stone-700 dark:text-stone-300">
                      <input
                        type="checkbox"
                        checked={syncMateriality}
                        onChange={(e) => setSyncMateriality(e.target.checked)}
                        className="rounded text-amber-800 focus:ring-amber-500 w-4 h-4"
                      />
                      <span>Automatically update Stage 10 Materiality with TB figures</span>
                    </label>
                  </div>

                  {/* Financial Aggregates Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 pt-1">
                    <div className="p-2.5 bg-white dark:bg-[#14181d] rounded border border-stone-200 dark:border-stone-800">
                      <span className="text-[10px] uppercase font-bold text-stone-500 block">
                        Turnover / Revenue
                      </span>
                      <span className="font-mono-num font-bold text-sm text-stone-900 dark:text-stone-100">
                        {formatCompactINR(summary.totalRevenue)}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white dark:bg-[#14181d] rounded border border-stone-200 dark:border-stone-800">
                      <span className="text-[10px] uppercase font-bold text-stone-500 block">
                        Profit Before Tax (PBT)
                      </span>
                      <span className="font-mono-num font-bold text-sm text-amber-800 dark:text-amber-400">
                        {formatCompactINR(summary.profitBeforeTax)}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white dark:bg-[#14181d] rounded border border-stone-200 dark:border-stone-800">
                      <span className="text-[10px] uppercase font-bold text-stone-500 block">
                        Total Assets
                      </span>
                      <span className="font-mono-num font-bold text-sm text-stone-900 dark:text-stone-100">
                        {formatCompactINR(summary.totalAssets)}
                      </span>
                    </div>
                    <div className="p-2.5 bg-white dark:bg-[#14181d] rounded border border-stone-200 dark:border-stone-800">
                      <span className="text-[10px] uppercase font-bold text-stone-500 block">
                        Net Worth / Equity
                      </span>
                      <span className="font-mono-num font-bold text-sm text-stone-900 dark:text-stone-100">
                        {formatCompactINR(summary.totalEquity)}
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Sample Rows Table Preview */}
              <div className="border border-stone-200 dark:border-stone-800 rounded-lg overflow-hidden">
                <div className="px-3 py-2 bg-stone-100 dark:bg-[#1a2027] border-b border-stone-200 dark:border-stone-800 font-semibold text-xs text-stone-700 dark:text-stone-300">
                  Sample Preview (First 6 Accounts)
                </div>
                <div className="overflow-x-auto max-h-56">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead className="bg-stone-50 dark:bg-[#1c222b] text-[11px] text-stone-500 border-b border-stone-200 dark:border-stone-800 sticky top-0">
                      <tr>
                        <th className="p-2">Code</th>
                        <th className="p-2">Account Name</th>
                        <th className="p-2">Schedule III Group</th>
                        <th className="p-2">Category</th>
                        <th className="p-2 text-right">Debit (₹)</th>
                        <th className="p-2 text-right">Credit (₹)</th>
                        <th className="p-2">Materiality</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-200 dark:divide-stone-800">
                      {parsedItems.slice(0, 6).map((item, idx) => (
                        <tr key={idx} className="hover:bg-stone-50 dark:hover:bg-stone-800/40">
                          <td className="p-2 font-mono">{item.accountCode}</td>
                          <td className="p-2 font-medium text-stone-900 dark:text-stone-100">
                            {item.accountName}
                          </td>
                          <td className="p-2 text-stone-600 dark:text-stone-400">
                            {item.scheduleIIIGroup}
                          </td>
                          <td className="p-2">
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-stone-200 dark:bg-stone-800 text-stone-700 dark:text-stone-300">
                              {item.category}
                            </span>
                          </td>
                          <td className="p-2 text-right font-mono-num">
                            {item.currentYearDebit ? formatINR(item.currentYearDebit) : '-'}
                          </td>
                          <td className="p-2 text-right font-mono-num">
                            {item.currentYearCredit ? formatINR(item.currentYearCredit) : '-'}
                          </td>
                          <td className="p-2">
                            <span
                              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                                item.materialityFlag === 'Material (>OM)'
                                  ? 'bg-rose-100 text-rose-800 dark:bg-rose-950/60 dark:text-rose-300'
                                  : item.materialityFlag === 'Significant (>PM)'
                                  ? 'bg-amber-100 text-amber-800 dark:bg-amber-950/60 dark:text-amber-300'
                                  : 'bg-stone-100 text-stone-600 dark:bg-stone-800 dark:text-stone-400'
                              }`}
                            >
                              {item.materialityFlag}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-[#dedbd2] dark:border-[#272f38] bg-[#f8f7f4] dark:bg-[#1a2027]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md border border-stone-300 dark:border-stone-700 text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 text-xs font-medium transition-colors"
          >
            Cancel
          </button>

          <div className="flex items-center gap-3">
            {rawSheetData && (
              <button
                onClick={handleConfirmImport}
                className="px-5 py-2 rounded-md bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 transition-colors"
              >
                <span>Confirm & Import ({parsedItems.length} accounts)</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
