import React, { useState, useRef } from 'react';
import {
  Upload,
  FileSpreadsheet,
  Download,
  AlertCircle,
  CheckCircle2,
  X,
  Sparkles,
  Building2,
  FileText,
  CreditCard,
  Search,
  Filter,
  CheckSquare,
  Square,
  AlertTriangle,
  Info,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Eye,
  ShieldCheck,
} from 'lucide-react';
import { useApp } from '../../context/AppContext';
import {
  downloadInvoiceExcelTemplate,
  downloadVendorExcelTemplate,
  downloadPaymentExcelTemplate,
  parseInvoiceExcelFile,
  parseVendorExcelFile,
  parsePaymentExcelFile,
  getDemoInvoiceExcelRows,
  getDemoVendorExcelRows,
  getDemoPaymentExcelRows,
} from '../../utils/excelService';
import { formatINR, formatDate } from '../../utils/formatters';
import { Invoice, Vendor } from '../../types';

export type ExcelImportType = 'invoices' | 'vendors' | 'payments';

interface ExcelUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  type?: ExcelImportType;
}

export const ExcelUploadModal: React.FC<ExcelUploadModalProps> = ({
  isOpen,
  onClose,
  type: initialType = 'invoices',
}) => {
  const {
    vendors,
    invoices,
    statutoryRules,
    bulkAddInvoices,
    bulkAddVendors,
    bulkAddPayments,
  } = useApp();

  const [activeType, setActiveType] = useState<ExcelImportType>(initialType);
  const [file, setFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [parseErrors, setParseErrors] = useState<{ row: number; reason: string }[]>([]);
  const [parsedItems, setParsedItems] = useState<any[]>([]);
  const [selectedRowIndices, setSelectedRowIndices] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [showSpecs, setShowSpecs] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Sync initial type if modal re-opens
  React.useEffect(() => {
    if (isOpen) {
      setActiveType(initialType);
      resetState();
    }
  }, [isOpen, initialType]);

  const resetState = () => {
    setFile(null);
    setIsProcessing(false);
    setParseErrors([]);
    setParsedItems([]);
    setSelectedRowIndices(new Set());
    setSearchTerm('');
    setIsSuccess(false);
    setSuccessMessage('');
  };

  if (!isOpen) return null;

  const handleTabChange = (type: ExcelImportType) => {
    setActiveType(type);
    resetState();
  };

  const handleDownloadTemplate = () => {
    if (activeType === 'invoices') {
      downloadInvoiceExcelTemplate();
    } else if (activeType === 'vendors') {
      downloadVendorExcelTemplate();
    } else {
      downloadPaymentExcelTemplate();
    }
  };

  const handleLoadDemoDataset = () => {
    setIsProcessing(true);
    setParseErrors([]);
    setFile(new File([''], `Demo_${activeType}_Batch.xlsx`));

    setTimeout(() => {
      if (activeType === 'invoices') {
        const demoRows = getDemoInvoiceExcelRows(vendors, invoices, statutoryRules);
        setParsedItems(demoRows);
        setSelectedRowIndices(new Set(demoRows.map((_, i) => i)));
      } else if (activeType === 'vendors') {
        const demoRows = getDemoVendorExcelRows();
        setParsedItems(demoRows);
        setSelectedRowIndices(new Set(demoRows.map((_, i) => i)));
      } else {
        const demoRows = getDemoPaymentExcelRows(invoices);
        setParsedItems(demoRows);
        setSelectedRowIndices(new Set(demoRows.map((_, i) => i)));
      }
      setIsProcessing(false);
    }, 400);
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (!selectedFile) return;

    setFile(selectedFile);
    setIsProcessing(true);
    setParseErrors([]);
    setParsedItems([]);
    setSelectedRowIndices(new Set());
    setIsSuccess(false);

    try {
      if (activeType === 'invoices') {
        const result = await parseInvoiceExcelFile(selectedFile, vendors, invoices, statutoryRules);
        setParsedItems(result.validInvoices);
        setSelectedRowIndices(new Set(result.validInvoices.map((_, i) => i)));
        setParseErrors(result.errors);
      } else if (activeType === 'vendors') {
        const result = await parseVendorExcelFile(selectedFile);
        setParsedItems(result.validVendors);
        setSelectedRowIndices(new Set(result.validVendors.map((_, i) => i)));
        setParseErrors(result.errors);
      } else {
        const result = await parsePaymentExcelFile(selectedFile, invoices);
        setParsedItems(result.validPayments);
        setSelectedRowIndices(new Set(result.validPayments.map((_, i) => i)));
        setParseErrors(result.errors);
      }
    } catch (err: any) {
      setParseErrors([{ row: 0, reason: err.message || 'Failed to read Excel workbook' }]);
    } finally {
      setIsProcessing(false);
    }
  };

  const toggleSelectAll = () => {
    if (selectedRowIndices.size === parsedItems.length) {
      setSelectedRowIndices(new Set());
    } else {
      setSelectedRowIndices(new Set(parsedItems.map((_, i) => i)));
    }
  };

  const toggleRow = (idx: number) => {
    const next = new Set(selectedRowIndices);
    if (next.has(idx)) {
      next.delete(idx);
    } else {
      next.add(idx);
    }
    setSelectedRowIndices(next);
  };

  const handleImport = () => {
    const itemsToImport = parsedItems.filter((_, i) => selectedRowIndices.has(i));
    if (itemsToImport.length === 0) return;

    if (activeType === 'invoices') {
      bulkAddInvoices(itemsToImport);
      setSuccessMessage(`Successfully committed ${itemsToImport.length} MSME invoices with statutory due dates!`);
    } else if (activeType === 'vendors') {
      bulkAddVendors(itemsToImport);
      setSuccessMessage(`Successfully imported ${itemsToImport.length} MSME vendor master records!`);
    } else {
      bulkAddPayments(itemsToImport);
      setSuccessMessage(`Successfully matched & applied ${itemsToImport.length} payment tranche settlements!`);
    }

    setIsSuccess(true);
    setTimeout(() => {
      onClose();
      resetState();
    }, 1500);
  };

  // Filtered parsed items for search
  const filteredParsedItems = parsedItems.filter((item, idx) => {
    if (!searchTerm.trim()) return true;
    const term = searchTerm.toLowerCase();
    if (activeType === 'invoices') {
      return (
        item.invoiceNumber?.toLowerCase().includes(term) ||
        item.vendorName?.toLowerCase().includes(term) ||
        item.poNumber?.toLowerCase().includes(term)
      );
    } else if (activeType === 'vendors') {
      return (
        item.vendorName?.toLowerCase().includes(term) ||
        item.vendorCode?.toLowerCase().includes(term) ||
        item.pan?.toLowerCase().includes(term) ||
        item.udyamNumber?.toLowerCase().includes(term)
      );
    } else {
      return (
        item.invoiceNumber?.toLowerCase().includes(term) ||
        item.vendorName?.toLowerCase().includes(term) ||
        item.paymentReference?.toLowerCase().includes(term) ||
        item.bankReferenceNo?.toLowerCase().includes(term)
      );
    }
  });

  // Calculate batch metrics
  const totalBatchValue = parsedItems.reduce((acc, item) => {
    if (activeType === 'invoices') return acc + (item.totalInvoiceAmount || 0);
    if (activeType === 'payments') return acc + (item.amount || 0);
    return acc;
  }, 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-4xl overflow-hidden animate-in fade-in zoom-in-95 duration-150 max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50/90">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-100 text-emerald-800 rounded-xl shadow-2xs">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-slate-900 text-base">Bulk Excel & CSV Ingestion Engine</h3>
                <span className="px-2 py-0.5 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded text-[10px] font-extrabold">
                  Section 15 & 43B(h) Validated
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Multi-entity spreadsheet data import with automated statutory due date & MSME verification logic
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Entity Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-100/60 px-6 pt-2 gap-2 text-xs font-semibold overflow-x-auto">
          <button
            onClick={() => handleTabChange('invoices')}
            className={`px-4 py-2.5 rounded-t-lg transition-all flex items-center gap-2 cursor-pointer border-t-2 border-x-2 ${
              activeType === 'invoices'
                ? 'bg-white text-blue-700 font-bold border-blue-600 shadow-2xs'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>1. Invoices Register</span>
            {activeType === 'invoices' && parsedItems.length > 0 && (
              <span className="px-1.5 py-0.2 bg-blue-100 text-blue-800 rounded text-[10px] font-extrabold">
                {parsedItems.length}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabChange('vendors')}
            className={`px-4 py-2.5 rounded-t-lg transition-all flex items-center gap-2 cursor-pointer border-t-2 border-x-2 ${
              activeType === 'vendors'
                ? 'bg-white text-blue-700 font-bold border-blue-600 shadow-2xs'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <Building2 className="w-4 h-4" />
            <span>2. MSME Vendor Master</span>
            {activeType === 'vendors' && parsedItems.length > 0 && (
              <span className="px-1.5 py-0.2 bg-blue-100 text-blue-800 rounded text-[10px] font-extrabold">
                {parsedItems.length}
              </span>
            )}
          </button>

          <button
            onClick={() => handleTabChange('payments')}
            className={`px-4 py-2.5 rounded-t-lg transition-all flex items-center gap-2 cursor-pointer border-t-2 border-x-2 ${
              activeType === 'payments'
                ? 'bg-white text-blue-700 font-bold border-blue-600 shadow-2xs'
                : 'border-transparent text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
            }`}
          >
            <CreditCard className="w-4 h-4" />
            <span>3. Bank / Payment Settlements</span>
            {activeType === 'payments' && parsedItems.length > 0 && (
              <span className="px-1.5 py-0.2 bg-blue-100 text-blue-800 rounded text-[10px] font-extrabold">
                {parsedItems.length}
              </span>
            )}
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1 text-xs">
          {/* Step 1 & 2 Action Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Download Template Card */}
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="font-bold text-slate-800 text-xs flex items-center gap-1.5">
                  <Download className="w-3.5 h-3.5 text-emerald-700" />
                  <span>Download Standard {activeType === 'invoices' ? 'Invoice' : activeType === 'vendors' ? 'Vendor' : 'Payment'} Template</span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Pre-configured Excel file with statutory headers and sample entries.
                </p>
              </div>
              <button
                onClick={handleDownloadTemplate}
                className="px-3 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 font-bold rounded-lg shadow-2xs flex items-center gap-1.5 transition-all shrink-0 cursor-pointer text-xs"
              >
                <Download className="w-3.5 h-3.5 text-slate-600" />
                Template
              </button>
            </div>

            {/* Quick Demo Test Load Card */}
            <div className="p-3.5 bg-blue-50/70 border border-blue-200 rounded-xl flex items-center justify-between gap-3">
              <div className="space-y-0.5">
                <div className="font-bold text-blue-900 text-xs flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  <span>1-Click Test Drive (Demo Dataset)</span>
                </div>
                <p className="text-[11px] text-blue-700">
                  Instantly stage sample test data without uploading a local file.
                </p>
              </div>
              <button
                disabled={isProcessing}
                onClick={handleLoadDemoDataset}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg shadow-2xs flex items-center gap-1.5 transition-all shrink-0 cursor-pointer text-xs disabled:opacity-50"
              >
                <Sparkles className="w-3.5 h-3.5" />
                Load Sample
              </button>
            </div>
          </div>

          {/* Upload Dropzone */}
          <div className="space-y-1.5">
            <input
              ref={fileInputRef}
              type="file"
              accept=".xlsx, .xls, .csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 hover:border-emerald-500 rounded-xl p-5 bg-slate-50/50 hover:bg-emerald-50/20 cursor-pointer transition-all text-center"
            >
              <Upload className="w-6 h-6 text-slate-400 mb-1.5" />
              <span className="text-xs font-bold text-slate-700">
                Click to browse or drag & drop {activeType} Excel workbook (.xlsx, .xls, .csv)
              </span>
              <span className="text-[11px] text-slate-400 mt-0.5">
                Automatic column matching, date normalizer, and Section 15 statutory validation applied instantly
              </span>
            </div>
          </div>

          {/* File Selected Indicator */}
          {file && (
            <div className="p-2.5 bg-slate-100 rounded-lg flex items-center justify-between text-xs text-slate-700">
              <div className="flex items-center gap-2 truncate">
                <FileSpreadsheet className="w-4 h-4 text-emerald-600 shrink-0" />
                <span className="font-semibold truncate">{file.name}</span>
                {file.size > 0 && <span className="text-slate-400">({(file.size / 1024).toFixed(1)} KB)</span>}
              </div>
              {isProcessing && (
                <div className="flex items-center gap-1.5 text-blue-600 font-bold animate-pulse">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                  <span>Validating data...</span>
                </div>
              )}
            </div>
          )}

          {/* Errors / Warnings Callout */}
          {parseErrors.length > 0 && (
            <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-amber-900 space-y-1.5">
              <div className="flex items-center gap-2 font-bold text-xs text-amber-800">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                <span>Detected {parseErrors.length} validation notice(s) or skipped row(s):</span>
              </div>
              <ul className="text-[11px] text-amber-700 space-y-1 max-h-24 overflow-y-auto pl-4 list-disc">
                {parseErrors.map((err, idx) => (
                  <li key={idx}>
                    {err.row > 0 ? <strong>Row {err.row}: </strong> : ''}
                    {err.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Staged Data Preview & Selection Grid */}
          {parsedItems.length > 0 && (
            <div className="space-y-3 pt-2">
              {/* Batch Summary KPI Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Staged Records</span>
                  <div className="text-sm font-extrabold text-slate-800">
                    {selectedRowIndices.size} / {parsedItems.length} Selected
                  </div>
                </div>
                {totalBatchValue > 0 && (
                  <div>
                    <span className="text-[10px] font-bold text-slate-400 uppercase">Total Value (₹)</span>
                    <div className="text-sm font-extrabold text-emerald-700 font-mono">
                      {formatINR(totalBatchValue)}
                    </div>
                  </div>
                )}
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Validation Rule</span>
                  <div className="text-xs font-bold text-blue-700 flex items-center gap-1">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>Statutory Capped</span>
                  </div>
                </div>
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Duplicate Protection</span>
                  <div className="text-xs font-bold text-emerald-700 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Cross-Checked</span>
                  </div>
                </div>
              </div>

              {/* Search & Selection Controls */}
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <button
                    onClick={toggleSelectAll}
                    className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded text-xs flex items-center gap-1.5 transition-colors cursor-pointer"
                  >
                    {selectedRowIndices.size === parsedItems.length ? (
                      <>
                        <CheckSquare className="w-3.5 h-3.5 text-blue-600" />
                        <span>Deselect All</span>
                      </>
                    ) : (
                      <>
                        <Square className="w-3.5 h-3.5 text-slate-500" />
                        <span>Select All ({parsedItems.length})</span>
                      </>
                    )}
                  </button>
                  <span className="text-[11px] text-slate-500">
                    Review and verify staged rows before inserting into database
                  </span>
                </div>

                <div className="relative w-48 sm:w-60">
                  <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search staged rows..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-8 pr-2.5 py-1 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-hidden focus:bg-white"
                  />
                </div>
              </div>

              {/* Data Table */}
              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs max-h-56 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-[10px] font-bold text-slate-600 uppercase tracking-wider sticky top-0 z-10">
                    <tr>
                      <th className="px-3 py-2 w-10 text-center">Include</th>
                      {activeType === 'invoices' && (
                        <>
                          <th className="px-3 py-2">Invoice No & Date</th>
                          <th className="px-3 py-2">Vendor / MSME</th>
                          <th className="px-3 py-2">Statutory Due Date</th>
                          <th className="px-3 py-2 text-right">Invoice Amount</th>
                          <th className="px-3 py-2 text-right">Paid</th>
                          <th className="px-3 py-2">Status</th>
                        </>
                      )}
                      {activeType === 'vendors' && (
                        <>
                          <th className="px-3 py-2">Vendor Code & Name</th>
                          <th className="px-3 py-2">PAN & GSTIN</th>
                          <th className="px-3 py-2">Udyam Reg. Number</th>
                          <th className="px-3 py-2">MSME Category</th>
                          <th className="px-3 py-2">Credit Days</th>
                          <th className="px-3 py-2">Agreement</th>
                        </>
                      )}
                      {activeType === 'payments' && (
                        <>
                          <th className="px-3 py-2">Invoice Number</th>
                          <th className="px-3 py-2">Vendor Name</th>
                          <th className="px-3 py-2">Payment Date</th>
                          <th className="px-3 py-2">Mode & UTR Ref</th>
                          <th className="px-3 py-2 text-right">Tranche Amount</th>
                          <th className="px-3 py-2">Payment Ref</th>
                        </>
                      )}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 bg-white">
                    {filteredParsedItems.map((item, idx) => {
                      const isSelected = selectedRowIndices.has(idx);

                      return (
                        <tr
                          key={idx}
                          className={`hover:bg-slate-50/80 transition-colors ${
                            isSelected ? 'bg-blue-50/20' : 'opacity-60 bg-slate-50/30'
                          }`}
                        >
                          <td className="px-3 py-2 text-center">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleRow(idx)}
                              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                            />
                          </td>

                          {activeType === 'invoices' && (
                            <>
                              <td className="px-3 py-2 font-semibold text-slate-800">
                                <div>{item.invoiceNumber}</div>
                                <div className="text-[10px] text-slate-400 font-normal">
                                  {formatDate(item.invoiceDate)}
                                </div>
                              </td>
                              <td className="px-3 py-2">
                                <div className="font-semibold text-slate-800">{item.vendorName}</div>
                                <div className="text-[10px] text-slate-400">
                                  {item.msmeCategory} | Agr: {item.hasWrittenAgreement ? 'Yes' : 'No'}
                                </div>
                              </td>
                              <td className="px-3 py-2">
                                <div className="font-bold text-slate-900 text-[11px]">
                                  {formatDate(item.finalDueDate)}
                                </div>
                                <div className="text-[10px] text-emerald-800 font-semibold">
                                  Cap: {item.statutoryLimitDays}d (Sec 15)
                                </div>
                              </td>
                              <td className="px-3 py-2 text-right font-bold text-slate-900 font-mono">
                                {formatINR(item.totalInvoiceAmount)}
                              </td>
                              <td className="px-3 py-2 text-right font-mono text-emerald-700">
                                {item.amountPaid > 0 ? formatINR(item.amountPaid) : '—'}
                              </td>
                              <td className="px-3 py-2">
                                <span
                                  className={`px-1.5 py-0.2 rounded text-[9px] font-extrabold ${
                                    item.status === 'Paid'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : item.status === 'Partially Paid'
                                      ? 'bg-amber-100 text-amber-800'
                                      : 'bg-blue-100 text-blue-800'
                                  }`}
                                >
                                  {item.status}
                                </span>
                              </td>
                            </>
                          )}

                          {activeType === 'vendors' && (
                            <>
                              <td className="px-3 py-2 font-semibold text-slate-800">
                                <div>{item.vendorName}</div>
                                <div className="text-[10px] text-slate-400 font-mono">{item.vendorCode}</div>
                              </td>
                              <td className="px-3 py-2 font-mono text-[11px] text-slate-700">
                                <div>PAN: {item.pan || '—'}</div>
                                <div className="text-[10px] text-slate-400">GST: {item.gstin || '—'}</div>
                              </td>
                              <td className="px-3 py-2 font-mono font-semibold text-blue-700">
                                {item.udyamNumber || '—'}
                              </td>
                              <td className="px-3 py-2">
                                <span className="px-1.5 py-0.2 bg-blue-100 text-blue-800 rounded font-bold text-[10px]">
                                  {item.msmeCategory}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-semibold text-slate-700">
                                {item.agreedCreditDays} Days
                              </td>
                              <td className="px-3 py-2 text-slate-600">
                                {item.hasWrittenAgreement ? 'Yes (Max 45d)' : 'No (15d Cap)'}
                              </td>
                            </>
                          )}

                          {activeType === 'payments' && (
                            <>
                              <td className="px-3 py-2 font-bold text-slate-800 font-mono">
                                {item.invoiceNumber}
                              </td>
                              <td className="px-3 py-2 font-medium text-slate-800">
                                {item.vendorName}
                              </td>
                              <td className="px-3 py-2 text-slate-700">
                                {formatDate(item.paymentDate)}
                              </td>
                              <td className="px-3 py-2">
                                <div className="font-semibold text-slate-800">{item.paymentMode}</div>
                                <div className="text-[10px] text-slate-400 font-mono">{item.bankReferenceNo || '—'}</div>
                              </td>
                              <td className="px-3 py-2 text-right font-bold text-emerald-700 font-mono text-xs">
                                {formatINR(item.amount)}
                              </td>
                              <td className="px-3 py-2 text-slate-600 font-mono text-[10px]">
                                {item.paymentReference}
                              </td>
                            </>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Success Banner */}
          {isSuccess && (
            <div className="p-3 bg-emerald-600 text-white rounded-xl text-xs font-semibold text-center flex items-center justify-center gap-2 animate-in fade-in">
              <CheckCircle2 className="w-4 h-4" />
              <span>{successMessage || 'Records successfully committed to database!'}</span>
            </div>
          )}
        </div>

        {/* Modal Footer Actions */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-800 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
          >
            Cancel
          </button>

          <div className="flex items-center gap-2">
            {parsedItems.length > 0 && (
              <button
                onClick={resetState}
                className="px-3 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200 rounded-lg transition-colors cursor-pointer"
              >
                Clear Data
              </button>
            )}

            <button
              disabled={selectedRowIndices.size === 0 || isProcessing || isSuccess}
              onClick={handleImport}
              className="px-5 py-2 bg-emerald-700 hover:bg-emerald-800 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow-xs flex items-center gap-2 transition-all cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" />
              <span>
                Commit {selectedRowIndices.size > 0 ? `${selectedRowIndices.size} Records` : 'Data'}
              </span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
