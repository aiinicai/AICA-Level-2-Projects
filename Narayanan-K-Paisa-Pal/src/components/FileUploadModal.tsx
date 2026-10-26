import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  FileText,
  Image as ImageIcon,
  Check,
  X,
  AlertCircle,
  AlertTriangle,
  Loader2,
  ChevronDown,
  Sparkles,
  ShieldCheck,
  Calendar,
  DollarSign,
  ArrowRight,
  CreditCard,
  FileCheck2,
} from 'lucide-react';
import { getSyntheticSpecimenFile } from '../data/dummyDocuments';
import { AppRow, Kind, RecType, InvType } from '../types';
import {
  finalizeRowData,
  guessTableKind,
  mapRows,
  parseDoc,
  parseInvest,
  parseRecord,
  readFileAny,
} from '../utils/documentParser';
import {
  CATS,
  inr,
  INV,
  KIND_PLURAL,
  longD,
  rateTxt,
  REC,
  uid,
} from '../utils/calculations';
import { scanDocumentFile, detectDocumentKind } from '../utils/documentScanner';
import { findDuplicate } from '../utils/duplicateDetector';
import * as XLSX from 'xlsx';
import {
  reconcileExcelWorkbook,
  ReconciledImportRow,
  ReconciliationReport,
} from '../utils/excelReconciliation';
import { ImportPreviewModal } from './ImportPreviewModal';

interface DraftItem {
  kind: Kind;
  data: Record<string, any>;
  text?: string;
  src?: string;
  selected: boolean;
  file?: File;
  duplicateWarning?: string;
}

interface Props {
  isOpen: boolean;
  kind: Kind | 'auto';
  rows: AppRow[];
  onClose: () => void;
  onSaveBatch: (items: { kind: Kind; data: Record<string, any>; file?: File }[]) => void;
  onEditSingle: (kind: Kind, preset: Record<string, any>, file?: File) => void;
  onOpenTrialDocuments?: () => void;
}

export const FileUploadModal: React.FC<Props> = ({
  isOpen,
  kind: initialKind,
  rows,
  onClose,
  onSaveBatch,
  onEditSingle,
  onOpenTrialDocuments,
}) => {
  // Category tabs: 'auto' (Auto-detect), 'rec' (Records & IDs), 'inv' (Investments), 'due' (Due Dates)
  const [activeCategory, setActiveCategory] = useState<Kind | 'auto'>('auto');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [pastedText, setPastedText] = useState<string>('');
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [drafts, setDrafts] = useState<DraftItem[]>([]);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const [reconciliationReport, setReconciliationReport] = useState<ReconciliationReport | null>(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setActiveCategory(initialKind || 'auto');
      setSelectedFiles([]);
      setPastedText('');
      setStatusMessage('');
      setDrafts([]);
      setReconciliationReport(null);
      setPreviewModalOpen(false);
    }
  }, [isOpen, initialKind]);

  if (!isOpen) return null;

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const list = Array.from(files);
    setSelectedFiles((prev) => [...prev, ...list]);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleTestSyntheticDoc = async (
    category: 'passport' | 'bank_fd' | 'insurance' | 'utility_bill'
  ) => {
    try {
      setIsLoading(true);
      const { file, doc } = getSyntheticSpecimenFile(category);
      setSelectedFiles([file]);
      setStatusMessage(`Scanning synthetic specimen ${doc.fileName}...`);
      const scanRes = await scanDocumentFile(
        file,
        activeCategory === 'auto' ? 'auto' : activeCategory,
        (status) => setStatusMessage(status)
      );
      if (scanRes && scanRes.data && Object.keys(scanRes.data).length > 0) {
        let detectedItemKind: Kind = scanRes.detectedKind || 'due';
        if (
          scanRes.data?.type === 'passport' ||
          scanRes.data?.type === 'id' ||
          scanRes.data?.type === 'licence' ||
          scanRes.data?.type === 'vehicle' ||
          scanRes.detectedKind === 'rec'
        ) {
          detectedItemKind = 'rec';
        } else if (activeCategory !== 'auto') {
          detectedItemKind = activeCategory;
        }
        const dup = findDuplicate(rows, detectedItemKind, scanRes.data);
        setDrafts([
          {
            kind: detectedItemKind,
            data: scanRes.data,
            text: scanRes.rawText || JSON.stringify(scanRes.data, null, 2),
            src: doc.fileName,
            selected: !dup.isDuplicate,
            file,
            duplicateWarning: dup.isDuplicate ? dup.reason : undefined,
          },
        ]);
        setStatusMessage('');
      } else {
        setStatusMessage('Scan completed.');
      }
    } catch (err: any) {
      console.error('Error testing synthetic document:', err);
      setStatusMessage(err.message || 'Error scanning synthetic file');
    } finally {
      setIsLoading(false);
    }
  };

  const handleProcess = async () => {
    if (!selectedFiles.length && !pastedText.trim()) {
      setStatusMessage('Please select a file (PDF, Excel, image) or paste text.');
      return;
    }

    setIsLoading(true);
    setStatusMessage('Reading files & analyzing document contents...');
    const extractedDrafts: DraftItem[] = [];
    const fromText: { t: string; src: string; file?: File }[] = [];

    try {
      for (const file of selectedFiles) {
        const isExcel = /\.(xlsx|xls|xlsm|xlsb|csv)$/i.test(file.name);

        // 1. Direct multi-sheet spreadsheet reconciliation for Excel (.xlsx, .xls) and CSV
        if (isExcel) {
          setStatusMessage(`Analyzing spreadsheet ${file.name} across all worksheets...`);
          try {
            const buffer = await file.arrayBuffer();
            const wb = XLSX.read(buffer, { type: 'array', cellDates: true, raw: false });
            const report = reconcileExcelWorkbook(wb, file.name, rows);
            if (report && report.totalSourceRows > 0) {
              setReconciliationReport(report);
              setPreviewModalOpen(true);
              setIsLoading(false);
              return;
            }
          } catch (excelErr: any) {
            console.warn('Excel parse error, trying text fallback', excelErr);
          }
        }

        // 2. Intelligent Document Scanner for PDF, Images, Word documents
        setStatusMessage(`Scanning ${file.name} with intelligent scanner...`);
        try {
          const scanRes = await scanDocumentFile(
            file,
            activeCategory === 'auto' ? 'auto' : activeCategory,
            (status) => setStatusMessage(status)
          );
          if (scanRes && scanRes.data && Object.keys(scanRes.data).length > 0) {
            let detectedItemKind: Kind = scanRes.detectedKind || 'due';
            const isPassportOrRecord =
              scanRes.data?.type === 'passport' ||
              scanRes.data?.type === 'id' ||
              scanRes.data?.type === 'licence' ||
              scanRes.data?.type === 'vehicle' ||
              scanRes.detectedKind === 'rec' ||
              detectDocumentKind(file.name, scanRes.rawText || '', 'due') === 'rec';

            if (isPassportOrRecord) {
              detectedItemKind = 'rec';
            } else if (activeCategory !== 'auto') {
              detectedItemKind = activeCategory;
            } else if (!scanRes.detectedKind) {
              detectedItemKind = detectDocumentKind(file.name, scanRes.rawText || '', 'inv');
            }

            const dup = findDuplicate(rows, detectedItemKind, scanRes.data);

            extractedDrafts.push({
              kind: detectedItemKind,
              data: scanRes.data,
              text: scanRes.rawText || JSON.stringify(scanRes.data, null, 2),
              src: file.name,
              selected: !dup.isDuplicate, // uncheck duplicate by default to protect user
              file,
              duplicateWarning: dup.isDuplicate ? dup.reason : undefined,
            });
            continue;
          }
        } catch (scanErr) {
          console.warn('Scan document error, attempting local table fallback', scanErr);
        }

        // 3. Fall back to local client text parsing
        setStatusMessage(`Reading ${file.name} text locally...`);
        const result = await readFileAny(file, (msg) => setStatusMessage(msg));
        if (result.table && result.table.length) {
          const effectiveKind =
            activeCategory !== 'auto'
              ? activeCategory
              : guessTableKind(Object.keys(result.table[0]), 'due');

          const mapped = mapRows(effectiveKind, result.table);
          mapped.forEach((m) => {
            const dup = findDuplicate(rows, m.kind, m.data);
            extractedDrafts.push({
              ...m,
              src: file.name,
              selected: !dup.isDuplicate,
              file,
              duplicateWarning: dup.isDuplicate ? dup.reason : undefined,
            });
          });
        } else if (result.text) {
          fromText.push({ t: result.text, src: file.name, file });
        }
      }

      if (pastedText.trim()) {
        fromText.push({ t: pastedText.trim(), src: 'Pasted text' });
      }

      for (const item of fromText) {
        const detectedKindFromText = detectDocumentKind(item.src, item.t, 'rec');
        const itemKind =
          detectedKindFromText === 'rec'
            ? 'rec'
            : activeCategory !== 'auto'
            ? activeCategory
            : detectedKindFromText;

        let parsed: Record<string, any> = {};
        if (itemKind === 'rec') parsed = parseRecord(item.t);
        else if (itemKind === 'inv') parsed = parseInvest(item.t);
        else parsed = parseDoc(item.t);

        const isValid =
          itemKind === 'rec'
            ? Boolean(parsed.title || parsed.number || parsed.expires || parsed.holder || parsed.type)
            : itemKind === 'inv'
            ? Boolean(parsed.name || parsed.invested || parsed.current || parsed.maturity || parsed.rate)
            : Boolean(parsed.name || parsed.due || parsed.amount || parsed.category);

        if (isValid) {
          const dup = findDuplicate(rows, itemKind, parsed);
          extractedDrafts.push({
            kind: itemKind,
            data: parsed,
            text: item.t,
            src: item.src,
            selected: !dup.isDuplicate,
            file: item.file,
            duplicateWarning: dup.isDuplicate ? dup.reason : undefined,
          });
        }
      }

      if (!extractedDrafts.length) {
        setStatusMessage(
          'No usable entries found. Please ensure the scan is clear or check the spreadsheet columns.'
        );
      } else {
        setStatusMessage('');
        setDrafts(extractedDrafts);
      }
    } catch (err: any) {
      console.error(err);
      setStatusMessage(err.message || 'Error parsing files.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveDrafts = () => {
    const selected = drafts.filter((d) => d.selected);
    if (!selected.length) {
      alert('Please select at least one item to save.');
      return;
    }

    // Check for duplicates among selected items
    const duplicates = selected.filter((d) => d.duplicateWarning || findDuplicate(rows, d.kind, d.data).isDuplicate);
    if (duplicates.length > 0) {
      const confirmSave = window.confirm(
        `⚠️ Duplicate Warning: ${duplicates.length} selected item(s) appear to already exist in your records or investments:\n\n${duplicates
          .map(
            (d) =>
              `• ${d.data.title || d.data.name || 'Item'} (${d.data.number || d.data.ref || 'No Ref'})`
          )
          .join('\n')}\n\nDo you still want to proceed and save as duplicate entries?`
      );
      if (!confirmSave) return;
    }

    const finalized = selected.map((d) => ({
      kind: d.kind,
      data: finalizeRowData(d.kind, d.data),
      file: d.file,
    }));
    onSaveBatch(finalized);
    onClose();
  };

  const renderFieldSummary = (itemKind: Kind, d: Record<string, any>) => {
    const fields: [string, string][] = [];
    if (d.holder) fields.push(['Holder', d.holder]);
    if (d.title || d.name) fields.push(['Title / Name', d.title || d.name]);
    if (d.type) {
      const typeLabel =
        itemKind === 'rec'
          ? (REC as Record<string, string>)[d.type] || d.type
          : itemKind === 'inv'
          ? (INV as Record<string, string>)[d.type] || d.type
          : d.type;
      fields.push(['Type', typeLabel]);
    }
    if (d.number || d.ref) fields.push(['Number / Ref', d.number || d.ref]);
    if (d.expires) fields.push(['Expiry Date', longD(d.expires)]);
    if (d.issued) fields.push(['Issue Date', longD(d.issued)]);
    if (d.category) fields.push(['Category', CATS[d.category as keyof typeof CATS] || d.category]);
    if (d.provider || d.institution) fields.push(['Bank/Company', d.provider || d.institution]);
    if (d.amount) fields.push(['Amount', inr(d.amount)]);
    if (d.invested) fields.push(['Invested', inr(d.invested)]);
    if (d.current) fields.push(['Current Value', inr(d.current)]);
    if (d.rate) fields.push(['Interest Rate', rateTxt(d.rate)]);
    if (d.due) fields.push(['Due Date', longD(d.due)]);
    if (d.start) fields.push(['Start Date', longD(d.start)]);
    if (d.maturity) fields.push(['Maturity Date', longD(d.maturity)]);

    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-3 gap-y-1 mt-2 text-xs">
        {fields.map(([label, val]) => (
          <div key={label} className="truncate">
            <span className="text-[#6F7E92] dark:text-[#8594AA]">{label}: </span>
            <span className="font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">{val}</span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-xl w-full max-h-[92vh] flex flex-col shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-[#DCE2EA] dark:border-[#25324A]">
          <div>
            <h2 className="font-bold text-lg text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#0E7C86]" />
              <span>Add from file (Auto-Detect)</span>
            </h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
              Excel (.xlsx, .xls), Passports, PAN cards, IDs, FD receipts, and bills
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 cursor-pointer"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Tabs: Auto-Detect vs Specific Section */}
        <div className="flex border-b border-[#DCE2EA] dark:border-[#25324A] bg-[#F7F9FC] dark:bg-[#0B1220] px-3 sm:px-6 pt-2 gap-1 overflow-x-auto text-xs font-semibold">
          <button
            type="button"
            onClick={() => setActiveCategory('auto')}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-xl transition cursor-pointer whitespace-nowrap ${
              activeCategory === 'auto'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5 text-[#0E7C86]" />
            <span>✨ Auto-Detect</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveCategory('rec')}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-xl transition cursor-pointer whitespace-nowrap ${
              activeCategory === 'rec'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
            <span>📋 Records & IDs</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveCategory('inv')}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-xl transition cursor-pointer whitespace-nowrap ${
              activeCategory === 'inv'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <DollarSign className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
            <span>💰 Investments</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveCategory('due')}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-t-xl transition cursor-pointer whitespace-nowrap ${
              activeCategory === 'due'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <Calendar className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            <span>📅 Due Dates & Bills</span>
          </button>
        </div>

        {/* Trial Documents Shortcut Banner */}
        {onOpenTrialDocuments && (
          <div className="mx-5 sm:mx-6 mt-3 p-2.5 rounded-xl bg-gradient-to-r from-teal-50 to-blue-50 dark:from-teal-950/40 dark:to-blue-950/40 border border-teal-200 dark:border-teal-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#0E7C86] flex-shrink-0" />
              <span className="text-teal-950 dark:text-teal-200">
                Want to test OCR accuracy? Try our <strong>41 Synthetic Specimen Documents across 10 Persons</strong> (Passports, DL, PAN, Aadhaar, FDs, Bills)
              </span>
            </div>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenTrialDocuments();
                }}
                className="px-3 py-1.5 rounded-lg bg-[#0E7C86] hover:bg-[#128e9a] text-white font-bold text-xs whitespace-nowrap shadow-xs transition cursor-pointer"
              >
                Browse 10 Persons Hub →
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="p-5 sm:p-6 overflow-y-auto flex-1 space-y-4">
          {drafts.length === 0 ? (
            <>
              {/* Drag & Drop Area */}
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center gap-2 ${
                  isDragOver
                    ? 'border-[#0E7C86] bg-[#0E7C86]/5 dark:bg-[#0E7C86]/10'
                    : 'border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86] bg-[#EEF1F5]/40 dark:bg-[#0B1220]/40'
                }`}
              >
                <div className="w-12 h-12 rounded-full bg-teal-100 dark:bg-teal-900/60 flex items-center justify-center text-[#0E7C86] mb-1">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div className="text-sm font-bold text-[#0F1B2D] dark:text-[#E8EDF5]">
                  Drop file here or click to browse
                </div>
                <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] max-w-sm">
                  Supports <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">Excel (.xlsx, .xls)</strong>, <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">PDF</strong>, and <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">Photos</strong>. Auto-detector categorizes Passports, PAN cards, FD receipts, and bills automatically.
                </div>
                <div className="mt-2 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-xs font-semibold border border-emerald-200 dark:border-emerald-800">
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  <span>Excel (.xlsx / .xls) Multi-Row Import Enabled</span>
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".xlsx,.xls,.xlsm,.xlsb,.csv,.pdf,image/*,.docx,.txt"
                  className="hidden"
                  onChange={(e) => handleFiles(e.target.files)}
                />
              </div>

              {selectedFiles.length > 0 && (
                <div className="space-y-1 text-xs bg-slate-50 dark:bg-slate-900/60 p-3 rounded-xl border border-slate-200 dark:border-slate-800">
                  <div className="font-semibold text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center justify-between">
                    <span>Selected files ({selectedFiles.length}):</span>
                    <button
                      type="button"
                      onClick={() => setSelectedFiles([])}
                      className="text-[11px] text-rose-600 hover:underline cursor-pointer"
                    >
                      Clear
                    </button>
                  </div>
                  <ul className="list-disc list-inside text-[#46566C] dark:text-[#A9B6C9] max-h-24 overflow-y-auto">
                    {selectedFiles.map((f, i) => (
                      <li key={i} className="truncate">
                        {f.name} ({(f.size / 1024).toFixed(1)} KB)
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Quick Test Synthetic Specimen Buttons */}
              <div className="space-y-2 p-3.5 rounded-2xl bg-gradient-to-br from-amber-50/70 to-teal-50/70 dark:from-amber-950/20 dark:to-teal-950/30 border border-teal-200 dark:border-teal-800">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 font-bold text-xs text-[#0F1B2D] dark:text-[#E8EDF5]">
                    <Sparkles className="w-3.5 h-3.5 text-amber-500" />
                    <span>🎯 Test Synthetic Specimen Documents (1-Click Test Scan)</span>
                  </div>
                  <span className="text-[10px] text-teal-700 dark:text-teal-300 font-semibold bg-teal-100/70 dark:bg-teal-900/50 px-2 py-0.5 rounded-full">
                    DPDP Safe · Synthetic
                  </span>
                </div>
                <p className="text-[11px] text-[#46566C] dark:text-[#A9B6C9]">
                  1-click test synthetic vector specimens to verify OCR categorization, statutory expiry rules, and instant field mapping:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                  <button
                    type="button"
                    onClick={() => handleTestSyntheticDoc('passport')}
                    className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-[#25324A] hover:border-[#0E7C86] hover:shadow-xs transition text-left cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-base">📘</span>
                      <div className="truncate">
                        <div className="text-xs font-bold text-[#0F1B2D] dark:text-[#E8EDF5] group-hover:text-[#0E7C86] transition truncate">
                          Synthetic Passport - Vikram Sharma
                        </div>
                        <div className="text-[10px] text-[#6F7E92] dark:text-[#8594AA] truncate">
                          Passports Act 1967 · Expiry 2034 · Issue/Expiry
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-blue-600 bg-blue-50 dark:bg-blue-950 px-1.5 py-0.5 rounded-md flex-shrink-0">
                      Records
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTestSyntheticDoc('bank_fd')}
                    className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-[#25324A] hover:border-[#0E7C86] hover:shadow-xs transition text-left cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-base">🏦</span>
                      <div className="truncate">
                        <div className="text-xs font-bold text-[#0F1B2D] dark:text-[#E8EDF5] group-hover:text-[#0E7C86] transition truncate">
                          Synthetic Bank FD - SBI Term Deposit
                        </div>
                        <div className="text-[10px] text-[#6F7E92] dark:text-[#8594AA] truncate">
                          ₹4,50,000 · 7.1% p.a. · Matured Alert
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-950 px-1.5 py-0.5 rounded-md flex-shrink-0">
                      Investments
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTestSyntheticDoc('insurance')}
                    className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-[#25324A] hover:border-[#0E7C86] hover:shadow-xs transition text-left cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-base">🛡️</span>
                      <div className="truncate">
                        <div className="text-xs font-bold text-[#0F1B2D] dark:text-[#E8EDF5] group-hover:text-[#0E7C86] transition truncate">
                          Synthetic Health Policy - Star Health
                        </div>
                        <div className="text-[10px] text-[#6F7E92] dark:text-[#8594AA] truncate">
                          ₹15L Cover · Dr. Meenakshi · Premium Due
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-teal-600 bg-teal-50 dark:bg-teal-950 px-1.5 py-0.5 rounded-md flex-shrink-0">
                      Insurance
                    </span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleTestSyntheticDoc('utility_bill')}
                    className="flex items-center justify-between p-2 rounded-xl bg-white dark:bg-[#131C2E] border border-teal-200 dark:border-[#25324A] hover:border-[#0E7C86] hover:shadow-xs transition text-left cursor-pointer group"
                  >
                    <div className="flex items-center gap-2 overflow-hidden">
                      <span className="text-base">⚡</span>
                      <div className="truncate">
                        <div className="text-xs font-bold text-[#0F1B2D] dark:text-[#E8EDF5] group-hover:text-[#0E7C86] transition truncate">
                          Synthetic Power Bill - BESCOM Bengaluru
                        </div>
                        <div className="text-[10px] text-[#6F7E92] dark:text-[#8594AA] truncate">
                          ₹2,680 · Chetan Gowda · Due Date & Overdue
                        </div>
                      </div>
                    </div>
                    <span className="text-[10px] font-bold text-amber-600 bg-amber-50 dark:bg-amber-950 px-1.5 py-0.5 rounded-md flex-shrink-0">
                      Utilities
                    </span>
                  </button>
                </div>
              </div>

              {/* Paste Text Option */}
              <div>
                <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                  Or paste text from SMS, email or document details:
                </label>
                <textarea
                  rows={2}
                  value={pastedText}
                  onChange={(e) => setPastedText(e.target.value)}
                  placeholder="e.g. PAN Card No: ABCDE1234F, Holder: Irin Joseph..."
                  className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl p-3 text-xs focus:outline-2 focus:outline-[#0E7C86]"
                />
              </div>

              {statusMessage && (
                <div className="flex items-center gap-2 p-3 text-xs rounded-xl bg-teal-50 dark:bg-teal-950/50 text-teal-900 dark:text-teal-200 border border-teal-200 dark:border-teal-900">
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin flex-shrink-0 text-[#0E7C86]" />
                  ) : (
                    <AlertCircle className="w-4 h-4 flex-shrink-0 text-[#0E7C86]" />
                  )}
                  <span>{statusMessage}</span>
                </div>
              )}
            </>
          ) : (
            /* DRAFTS PREVIEW STAGE */
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-[#0F1B2D] dark:text-[#E8EDF5]">
                    Extracted {drafts.length} item{drafts.length === 1 ? '' : 's'}. Review & Save:
                  </h3>
                  <p className="text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                    Duplicate items are flagged and unchecked to prevent accidental duplicates.
                  </p>
                </div>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900 text-emerald-800 dark:text-emerald-200">
                  {drafts.filter((d) => d.selected).length} selected
                </span>
              </div>

              <div className="space-y-2.5 max-h-[50vh] overflow-y-auto pr-1">
                {drafts.map((draft, idx) => (
                  <div
                    key={idx}
                    className={`p-3.5 rounded-xl border transition ${
                      draft.duplicateWarning
                        ? 'border-amber-300 dark:border-amber-700 bg-amber-50/20 dark:bg-amber-950/20'
                        : draft.selected
                        ? 'border-[#0E7C86] bg-emerald-50/20 dark:bg-emerald-950/10'
                        : 'border-[#DCE2EA] dark:border-[#25324A] opacity-60'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <input
                        type="checkbox"
                        checked={draft.selected}
                        onChange={(e) => {
                          const val = e.target.checked;
                          setDrafts((prev) =>
                            prev.map((it, i) => (i === idx ? { ...it, selected: val } : it))
                          );
                        }}
                        className="mt-1 h-4 w-4 rounded border-gray-300 text-[#0E7C86] focus:ring-[#0E7C86] cursor-pointer"
                      />
                      <div className="flex-1 min-w-0">
                        {/* Top bar with destination tag & kind switcher */}
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-[#6F7E92] dark:text-[#8594AA] truncate">
                              File: <strong className="text-[#0F1B2D] dark:text-[#E8EDF5]">{draft.src || 'file'}</strong>
                            </span>

                            {/* Destination Section Badge & Selector */}
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-bold bg-teal-100 dark:bg-teal-900/80 text-teal-800 dark:text-teal-200">
                              <span>Saving to:</span>
                              <select
                                value={draft.kind}
                                onChange={(e) => {
                                  const newKind = e.target.value as Kind;
                                  setDrafts((prev) =>
                                    prev.map((it, i) => (i === idx ? { ...it, kind: newKind } : it))
                                  );
                                }}
                                className="bg-transparent border-none font-bold text-teal-950 dark:text-teal-100 cursor-pointer focus:outline-none"
                              >
                                <option value="rec">📋 Records & IDs</option>
                                <option value="inv">💰 Investments</option>
                                <option value="due">📅 Due Dates & Bills</option>
                              </select>
                            </span>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              onEditSingle(draft.kind, draft.data, draft.file);
                              onClose();
                            }}
                            className="text-xs font-semibold text-[#0E7C86] hover:underline cursor-pointer"
                          >
                            ✏️ Edit details
                          </button>
                        </div>

                        {renderFieldSummary(draft.kind, draft.data)}

                        {/* Duplicate Warning Banner */}
                        {draft.duplicateWarning && (
                          <div className="mt-2 p-2 rounded-lg bg-amber-50 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-700/80 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2">
                            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
                            <div className="flex-1">
                              <span className="font-bold block">⚠️ Potential Duplicate</span>
                              <span className="text-[11px] leading-relaxed">{draft.duplicateWarning}</span>
                            </div>
                          </div>
                        )}

                        {draft.text && !draft.duplicateWarning && (
                          <details className="mt-2 text-[11px] text-[#6F7E92] dark:text-[#8594AA]">
                            <summary className="cursor-pointer hover:underline">
                              View raw extracted text
                            </summary>
                            <pre className="mt-1 p-2 bg-slate-100 dark:bg-slate-900 rounded-lg whitespace-pre-wrap font-mono text-[10px] max-h-24 overflow-y-auto">
                              {draft.text.slice(0, 1500)}
                            </pre>
                          </details>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 sm:px-6 py-4 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-between">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-sm font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
          >
            Cancel
          </button>

          {drafts.length === 0 ? (
            <button
              type="button"
              disabled={isLoading || (!selectedFiles.length && !pastedText.trim())}
              onClick={handleProcess}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-[#0E7C86] hover:bg-[#128e9a] disabled:opacity-50 text-white transition shadow-sm cursor-pointer"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              <span>{isLoading ? 'Processing...' : 'Read & Extract Document'}</span>
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setDrafts([])}
                className="px-3 py-2 rounded-xl text-xs font-medium text-[#46566C] dark:text-[#A9B6C9] hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              >
                Scan another file
              </button>
              <button
                type="button"
                onClick={handleSaveDrafts}
                className="flex items-center gap-1.5 px-5 py-2.5 rounded-xl text-sm font-bold bg-[#0E7C86] hover:bg-[#128e9a] text-white transition shadow-sm cursor-pointer"
              >
                <Check className="w-4 h-4" />
                <span>Save to {drafts.some((d) => d.kind === 'rec') ? 'Records' : 'Portfolio'}</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {previewModalOpen && reconciliationReport && (
        <ImportPreviewModal
          isOpen={previewModalOpen}
          report={reconciliationReport}
          onClose={() => {
            setPreviewModalOpen(false);
            setReconciliationReport(null);
          }}
          onConfirmImport={(selectedRows) => {
            const items = selectedRows.map((r) => ({
              kind: r.detectedKind,
              data: r.appRowData,
            }));
            onSaveBatch(items);
            setPreviewModalOpen(false);
            setReconciliationReport(null);
            onClose();
          }}
        />
      )}
    </div>
  );
};
