import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  Calendar,
  DollarSign,
  Tag,
  User,
  Building,
  FileText,
  Clock,
  Paperclip,
  Image as ImageIcon,
  Trash2,
  Sparkles,
  Loader2,
  CheckCircle2,
  FileUp,
  Edit3,
  Eye,
  Check,
  ArrowRight,
  ShieldCheck,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { AppRow, DueCategory, Frequency, InvType, Kind, RecType } from '../types';
import {
  CATS,
  DEF_ALERTS,
  DEF_INV_ALERTS,
  FREQ,
  INV,
  KIND_NAME,
  REC,
  todayIST,
  inr,
  longD,
} from '../utils/calculations';
import { getAttachment, AttachmentRecord } from '../utils/attachmentStorage';
import { scanDocumentFile } from '../utils/documentScanner';
import { findDuplicate } from '../utils/duplicateDetector';
import {
  DOCUMENT_VALIDITY_RULES,
  hasPrescribedExpiry,
  suggestExpiryDate,
  validateDocumentDates,
} from '../utils/documentValidity';

interface Props {
  isOpen: boolean;
  kind: Kind;
  rows?: AppRow[];
  initialRow?: AppRow | null;
  presetData?: Record<string, any> | null;
  presetFile?: File | null;
  onClose: () => void;
  onSave: (
    kind: Kind,
    data: Record<string, any>,
    id?: string,
    attachmentFile?: File | null,
    deleteAttachment?: boolean
  ) => void;
  onViewAttachment?: (rowId: string, itemName: string) => void;
}

export const ItemModal: React.FC<Props> = ({
  isOpen,
  kind,
  rows = [],
  initialRow,
  presetData,
  presetFile,
  onClose,
  onSave,
  onViewAttachment,
}) => {
  // Option 1: 'scan' (Auto-Scan & Automatic Input), Option 2: 'manual' (Type Details Manually)
  const [currentKind, setCurrentKind] = useState<Kind>(initialRow?.kind || kind);
  const [dupWarningDismissed, setDupWarningDismissed] = useState<boolean>(false);
  const [inputMode, setInputMode] = useState<'scan' | 'manual'>('scan');
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [error, setError] = useState<string>('');
  const [stagedFile, setStagedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [existingAttachment, setExistingAttachment] = useState<AttachmentRecord | null>(null);
  const [shouldDeleteAttachment, setShouldDeleteAttachment] = useState(false);
  const [isAutoScanning, setIsAutoScanning] = useState<boolean>(false);
  const [scanStatus, setScanStatus] = useState<string>('');
  const [scanBanner, setScanBanner] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scanAndPopulate = async (file: File) => {
    setIsAutoScanning(true);
    setScanStatus('Reading & scanning document with AI scanner...');
    setScanBanner(null);
    setError('');
    setDupWarningDismissed(false);

    try {
      const result = await scanDocumentFile(file, currentKind, (status) => setScanStatus(status));
      if (result && result.data && Object.keys(result.data).length > 0) {
        if (result.detectedKind && result.detectedKind !== currentKind) {
          setCurrentKind(result.detectedKind);
          const kindNames: Record<Kind, string> = {
            rec: 'Official Record / ID',
            inv: 'Bank Investment',
            due: 'Due Date / Bill',
            util: 'Utility Bill',
          };
          setScanBanner(
            `Document recognized as ${kindNames[result.detectedKind]}! Switched category to ${
              result.detectedKind === 'rec'
                ? 'Records & IDs'
                : result.detectedKind === 'inv'
                ? 'Investments'
                : result.detectedKind === 'util'
                ? 'Utilities'
                : 'Due Dates'
            } automatically.`
          );
        } else {
          setScanBanner(
            `All columns autofilled automatically from "${file.name}"! No manual typing required.`
          );
        }
        setFormData((prev) => {
          const next = { ...prev };
          for (const [k, v] of Object.entries(result.data)) {
            if (v !== undefined && v !== null && v !== '') {
              next[k] = v;
            }
          }
          if (Array.isArray(next.alerts)) {
            next.alerts = next.alerts.join(', ');
          }
          return next;
        });
      } else {
        setScanBanner(`Attached "${file.name}". You can review and save.`);
      }
    } catch (err: any) {
      console.error('Scan error:', err);
      setScanBanner(`Attached "${file.name}".`);
    } finally {
      setIsAutoScanning(false);
      setScanStatus('');
    }
  };

  const handleFilePicked = async (file: File | null) => {
    if (!file) return;
    setStagedFile(file);
    setShouldDeleteAttachment(false);
    if (file.type.startsWith('image/')) {
      const url = URL.createObjectURL(file);
      setFilePreview(url);
    } else {
      setFilePreview(null);
    }
    // Automatically scan the attached document and populate every column!
    await scanAndPopulate(file);
  };

  const loadSampleAttachment = async (url: string, filename: string) => {
    try {
      setIsAutoScanning(true);
      setScanStatus(`Loading ${filename}...`);
      const resp = await fetch(url);
      const blob = await resp.blob();
      const file = new File([blob], filename, { type: blob.type || 'application/pdf' });
      setStagedFile(file);
      await scanAndPopulate(file);
    } catch (err: any) {
      console.error('Failed to load sample attachment', err);
      setIsAutoScanning(false);
    }
  };

  useEffect(() => {
    setCurrentKind(initialRow?.kind || kind);
    setDupWarningDismissed(false);
    setStagedFile(null);
    setFilePreview(null);
    setShouldDeleteAttachment(false);
    setScanBanner(null);
    setIsAutoScanning(false);

    if (presetFile && !initialRow) {
      setInputMode('scan');
      setStagedFile(presetFile);
      if (presetFile.type.startsWith('image/')) {
        setFilePreview(URL.createObjectURL(presetFile));
      }
      if (presetData && Object.keys(presetData).length > 0) {
        const d = { ...presetData };
        if (Array.isArray(d.alerts)) d.alerts = d.alerts.join(', ');
        setFormData(d);
        setScanBanner(
          `All columns autofilled from "${presetFile.name}". Review and click Save.`
        );
      } else {
        scanAndPopulate(presetFile);
      }
      return;
    }

    if (initialRow) {
      // User is editing an existing row, so open manual edit mode by default
      setInputMode('manual');
      const d = { ...initialRow.data };
      if (Array.isArray(d.alerts)) {
        d.alerts = d.alerts.join(', ');
      }
      setFormData(d);

      getAttachment(initialRow.id, d.attachmentUrl, d.attachmentName).then((att) => {
        setExistingAttachment(att);
      });
    } else if (presetData) {
      setInputMode('scan');
      const d = { ...presetData };
      if (Array.isArray(d.alerts)) {
        d.alerts = d.alerts.join(', ');
      }
      setFormData(d);
      setExistingAttachment(null);
      setScanBanner('Columns pre-filled from scanned document. Review and click Save.');
    } else {
      // Adding new item: default to Auto-Scan mode so user can scan effortlessly
      setInputMode('scan');
      setExistingAttachment(null);
      // Default blank values
      const targetKind = kind;
      if (targetKind === 'due') {
        setFormData({
          category: 'utility',
          freq: 'monthly',
          due: todayIST(),
          alerts: DEF_ALERTS['utility']?.join(', ') || '5, 2, 0',
          interval: 35,
        });
      } else if (targetKind === 'inv') {
        setFormData({
          type: 'fd',
          alerts: '30, 15, 7, 1',
        });
      } else {
        setFormData({
          type: 'id',
          alerts: '60, 30, 7',
        });
      }
    }
    setError('');
  }, [isOpen, initialRow, presetData, presetFile, kind]);

  if (!isOpen) return null;

  const handleChange = (field: string, val: any) => {
    setFormData((prev) => {
      const next = { ...prev, [field]: val };
      if (field === 'category' && currentKind === 'due' && DEF_ALERTS[val]) {
        next.alerts = DEF_ALERTS[val].join(', ');
      }
      return next;
    });
  };

  const handleClearAttachment = () => {
    setStagedFile(null);
    setFilePreview(null);
    setScanBanner(null);
    if (existingAttachment) {
      setShouldDeleteAttachment(true);
    }
  };

  const handleSubmit = (e?: React.FormEvent) => {
    if (e && typeof e.preventDefault === 'function') {
      e.preventDefault();
    }
    setError('');

    const out: Record<string, any> = { ...formData };

    // Format numbers and ensure customer-friendly defaults so Save NEVER fails or blocks:
    if (currentKind === 'inv') {
      // Auto-generate name if empty so user is NEVER prompted:
      if (!out.name || !out.name.trim()) {
        if (out.institution && out.institution.trim()) {
          out.name = `${out.institution.trim()} Fixed Deposit`;
        } else if (stagedFile?.name) {
          out.name = stagedFile.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
        } else if (existingAttachment?.name) {
          out.name = existingAttachment.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
        } else {
          out.name = 'Bank Fixed Deposit';
        }
      }
      out.type = out.type || 'fd';
      out.invested = out.invested === '' || out.invested == null ? 0 : +out.invested;
      out.current = out.current === '' || out.current == null ? out.invested : +out.current;
      out.rate = out.rate === '' || out.rate == null ? 0 : +out.rate;
    } else if (currentKind === 'util') {
      if (!out.name || !out.name.trim()) {
        if (out.provider && out.provider.trim()) {
          out.name = `${out.provider.trim()} Bill`;
        } else if (stagedFile?.name) {
          out.name = stagedFile.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
        } else {
          out.name = 'Utility Bill';
        }
      }
      out.utilityType = out.utilityType || 'electricity';
      out.provider = out.provider || out.name;
      out.dueDate = out.dueDate || out.due || todayIST();
      out.due = out.dueDate;
      const bAmt =
        out.billAmount !== '' && out.billAmount != null
          ? +out.billAmount
          : out.amount !== '' && out.amount != null
          ? +out.amount
          : 0;
      out.billAmount = bAmt;
      out.balanceOutstanding =
        out.balanceOutstanding != null && out.balanceOutstanding !== ''
          ? +out.balanceOutstanding
          : bAmt;
      out.status = out.status || 'pending';
      out.freq = out.freq || 'monthly';
      out.accountNumber = out.accountNumber || out.ref || '';
    } else if (currentKind === 'due') {
      if (!out.name || !out.name.trim()) {
        if (out.provider && out.provider.trim()) {
          out.name = `${out.provider.trim()} Due Payment`;
        } else if (stagedFile?.name) {
          out.name = stagedFile.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
        } else {
          out.name = 'Bill Payment';
        }
      }
      if (!out.due || !/^\d{4}-\d{2}-\d{2}$/.test(out.due)) {
        out.due = todayIST();
      }
      out.category = out.category || 'utility';
      out.amount = out.amount === '' || out.amount == null ? 0 : +out.amount;
      out.interval = +out.interval || 35;
      out.status = out.status || 'pending';
      out.anchor = +out.due.slice(8, 10);
    } else if (currentKind === 'rec') {
      if (!out.title || !out.title.trim()) {
        if (stagedFile?.name) {
          out.title = stagedFile.name.replace(/\.[^/.]+$/, '').replace(/[_-]+/g, ' ').trim();
        } else {
          out.title = 'Document Record';
        }
      }
      out.type = out.type || 'id';

      // Date validation: Expiry cannot precede issue date
      if (out.issued && out.expires) {
        const valResult = validateDocumentDates(out.issued, out.expires);
        if (!valResult.isValid && valResult.error) {
          setError(valResult.error);
          return;
        }
      }

      // Check statutory expiry requirement
      const docRequiresExpiry = hasPrescribedExpiry(out.type, out.title);
      if (docRequiresExpiry) {
        if (!out.expires || !out.expires.trim() || /permanent|no expiry|lifetime/i.test(out.expires)) {
          setError(
            `⚠️ Expiry Date Required: Under Indian statutory rules (${
              out.type === 'passport' ? 'Passports Act 1967' : 'Motor Vehicles / Insurance Acts'
            }), this document requires a recorded expiry date and can NEVER be labeled "Permanent". Please enter the valid expiry date.`
          );
          return;
        }
      } else {
        // Lifelong statutory documents (PAN, Aadhaar) do not require expiry dates
        if (out.type === 'pan' || out.type === 'aadhaar') {
          delete out.expires;
        }
      }
    }

    // Process alerts
    if (typeof out.alerts === 'string') {
      out.alerts = out.alerts
        .split(/[,\s|]+/)
        .map(Number)
        .filter((n) => Number.isFinite(n) && n >= 0);
    }
    if (!out.alerts || !out.alerts.length) {
      if (currentKind === 'util') {
        out.alerts = [7, 3, 0];
      } else if (currentKind === 'due') {
        out.alerts = DEF_ALERTS[out.category] || [7, 1];
      } else if (currentKind === 'inv') {
        out.alerts = [30, 15, 7, 1];
      } else {
        out.alerts = [60, 30, 7];
      }
    }

    // Check for duplicates if adding a new entry
    const dupCheck = findDuplicate(rows, currentKind, out, initialRow?.id);
    if (!initialRow && dupCheck.isDuplicate && !dupWarningDismissed) {
      setError(`⚠️ Potential Duplicate Warning: ${dupCheck.reason}. Click "Save Anyway" if you still wish to add this entry.`);
      setDupWarningDismissed(true);
      return;
    }

    onSave(currentKind, out, initialRow?.id, stagedFile, shouldDeleteAttachment);
  };

  const hasAttachment = Boolean(
    stagedFile || (existingAttachment && !shouldDeleteAttachment)
  );
  const activeFileName = stagedFile?.name || (existingAttachment && !shouldDeleteAttachment ? existingAttachment.name : null);
  const activeFileSize = stagedFile?.size || (existingAttachment && !shouldDeleteAttachment ? existingAttachment.size : null);

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-3 sm:p-4 overflow-y-auto"
    >
      <div className="bg-white dark:bg-[#131C2E] border border-[#DCE2EA] dark:border-[#25324A] rounded-2xl max-w-xl w-full max-h-[92vh] flex flex-col shadow-2xl relative text-[#0F1B2D] dark:text-[#E8EDF5] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 sm:px-6 py-4 border-b border-[#DCE2EA] dark:border-[#25324A]">
          <div>
            <h2 className="font-bold text-lg text-[#0F1B2D] dark:text-[#E8EDF5] flex items-center gap-2">
              <span>{initialRow ? 'Edit' : 'Add'} {KIND_NAME[currentKind]}</span>
            </h2>
            <p className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-0.5">
              Choose automatic scan input or type details manually
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Category Switcher Pill Bar (allowing switching between categories) */}
        {!initialRow && (
          <div className="flex items-center gap-1.5 px-4 sm:px-6 py-2 bg-slate-50 dark:bg-slate-900/60 border-b border-[#DCE2EA] dark:border-[#25324A] text-xs flex-wrap">
            <span className="text-[#6F7E92] dark:text-[#8594AA] font-semibold text-[11px] mr-1">Category:</span>
            {(['util', 'due', 'inv', 'rec'] as Kind[]).map((k) => (
              <button
                key={k}
                type="button"
                onClick={() => {
                  setCurrentKind(k);
                  setScanBanner(null);
                  setError('');
                  setDupWarningDismissed(false);
                }}
                className={`px-3 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
                  currentKind === k
                    ? 'bg-[#0E7C86] text-white shadow-xs font-semibold'
                    : 'bg-white dark:bg-[#131C2E] text-[#46566C] dark:text-[#A9B6C9] border border-[#DCE2EA] dark:border-[#25324A] hover:border-[#0E7C86]'
                }`}
              >
                {k === 'util'
                  ? '⚡ Utilities & Bills'
                  : k === 'due'
                  ? 'Due Dates & EMIs'
                  : k === 'inv'
                  ? 'Bank Investments'
                  : 'Official Records & IDs'}
              </button>
            ))}
          </div>
        )}

        {/* Dual Option Switcher Tabs */}
        <div className="flex border-b border-[#DCE2EA] dark:border-[#25324A] bg-[#F7F9FC] dark:bg-[#0B1220] px-3 sm:px-6 pt-2 gap-2">
          <button
            type="button"
            onClick={() => setInputMode('scan')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-2.5 text-xs font-semibold rounded-t-xl transition cursor-pointer ${
              inputMode === 'scan'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <Sparkles className="w-4 h-4 text-[#0E7C86]" />
            <span>Option 1: ⚡ Auto-Scan (Automatic Input)</span>
            {hasAttachment && (
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Voucher attached & scanned" />
            )}
          </button>
          <button
            type="button"
            onClick={() => setInputMode('manual')}
            className={`flex items-center gap-2 px-3 sm:px-4 py-2.5 text-xs font-semibold rounded-t-xl transition cursor-pointer ${
              inputMode === 'manual'
                ? 'bg-white dark:bg-[#131C2E] text-[#0E7C86] dark:text-teal-300 border-t-2 border-t-[#0E7C86] border-x border-[#DCE2EA] dark:border-[#25324A] shadow-xs'
                : 'text-[#6F7E92] hover:text-[#0F1B2D] dark:hover:text-[#E8EDF5]'
            }`}
          >
            <Edit3 className="w-4 h-4 text-[#0E7C86]" />
            <span>Option 2: ✍️ Type Details Manually</span>
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 overflow-y-auto space-y-4 flex-1">
          {/* Active Auto-Scanning Indicator */}
          {isAutoScanning && (
            <div className="p-3.5 rounded-xl bg-teal-50 dark:bg-teal-950/60 border border-teal-300 dark:border-teal-700 flex items-center gap-3 text-teal-900 dark:text-teal-100 text-xs shadow-xs animate-pulse">
              <Loader2 className="w-5 h-5 animate-spin text-[#0E7C86] flex-shrink-0" />
              <div>
                <div className="font-semibold text-xs sm:text-sm">Auto-Scanning Document...</div>
                <div className="text-[11px] text-teal-700 dark:text-teal-300">
                  {scanStatus || 'Extracting financial details & filling columns automatically...'}
                </div>
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 text-xs rounded-lg bg-rose-50 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300 border border-rose-200 dark:border-rose-900">
              {error}
            </div>
          )}

          {/* Duplicate Warning Banner */}
          {!initialRow && findDuplicate(rows, currentKind, formData).isDuplicate && (
            <div className="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/70 border border-amber-300 dark:border-amber-700 text-amber-900 dark:text-amber-200 text-xs flex items-start gap-2.5 shadow-xs">
              <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <span className="font-bold block">⚠️ Potential Duplicate Warning</span>
                <span className="text-[11px] leading-relaxed">
                  {findDuplicate(rows, currentKind, formData).reason}
                </span>
              </div>
            </div>
          )}

          {/* ========================================================= */}
          {/* OPTION 1: AUTO-SCAN & AUTOMATIC INPUT                      */}
          {/* ========================================================= */}
          {inputMode === 'scan' && (
            <div className="space-y-4">
              {/* If an attachment is already present (or just scanned), show the Automatic Input Confirmation Card */}
              {hasAttachment ? (
                <div className="rounded-2xl border-2 border-emerald-500/30 bg-emerald-50/40 dark:bg-emerald-950/20 p-4 sm:p-5 shadow-sm space-y-4">
                  {/* Status Banner */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-emerald-100 dark:bg-emerald-900/60 flex items-center justify-center text-emerald-600 dark:text-emerald-400 flex-shrink-0 mt-0.5">
                        <CheckCircle2 className="w-5 h-5" />
                      </div>
                      <div>
                        <span className="font-bold text-sm sm:text-base text-emerald-900 dark:text-emerald-200 block">
                          Document Scanned & Details Input Automatically
                        </span>
                        <span className="text-xs text-emerald-700 dark:text-emerald-300">
                          File: <span className="font-semibold">{activeFileName}</span>
                          {activeFileSize ? ` (${(activeFileSize / 1024).toFixed(0)} KB)` : ''}
                        </span>
                      </div>
                    </div>

                    <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-900/80 text-emerald-800 dark:text-emerald-200 text-[11px] font-bold">
                      ⚡ 100% Autofilled
                    </span>
                  </div>

                  {/* Summary Breakdown Grid of Extracted Columns */}
                  <div className="bg-white dark:bg-[#0B1220] rounded-xl border border-emerald-200 dark:border-emerald-800/60 p-3.5 space-y-2.5 text-xs">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                          {kind === 'inv' ? 'Investment Name' : kind === 'due' ? 'Payment Name' : 'Document Title'}
                        </span>
                        <span className="font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                          {formData.name || formData.title || (formData.institution ? `${formData.institution} Fixed Deposit` : 'Fixed Deposit')}
                        </span>
                      </div>

                      <div>
                        <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                          {kind === 'inv' ? 'Bank / Institution' : kind === 'due' ? 'Biller / Provider' : 'Document Type'}
                        </span>
                        <span className="font-semibold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                          {formData.institution || formData.provider || formData.type || 'Bank FD'}
                        </span>
                      </div>
                    </div>

                    {currentKind === 'rec' ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                        <div>
                          <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Document Number</span>
                          <span className="font-mono font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                            {formData.number || '—'}
                          </span>
                        </div>

                        <div>
                          <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Document Holder</span>
                          <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5]">
                            {formData.holder || '—'}
                          </span>
                        </div>

                        <div>
                          <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Expiry Date</span>
                          <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5]">
                            {formData.expires ? longD(formData.expires) : 'No expiry'}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                              {currentKind === 'inv' ? 'Account / Certificate No.' : 'Account / Ref No.'}
                            </span>
                            <span className="font-mono font-semibold text-[#0F1B2D] dark:text-[#E8EDF5]">
                              {formData.ref || formData.number || '—'}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">Depositor / Holder</span>
                            <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5]">
                              {formData.holder || '—'}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                              {currentKind === 'inv' ? 'Interest Rate' : 'Frequency'}
                            </span>
                            <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400">
                              {currentKind === 'inv' ? (formData.rate ? `${formData.rate}% p.a.` : '—') : (formData.freq || 'Monthly')}
                            </span>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-2 border-t border-slate-100 dark:border-slate-800/80">
                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                              {currentKind === 'inv' ? 'Amount Invested' : 'Amount Due'}
                            </span>
                            <span className="font-mono font-bold text-sm text-[#0F1B2D] dark:text-[#E8EDF5]">
                              {formData.invested ? inr(formData.invested) : (formData.amount ? inr(formData.amount) : '—')}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                              {currentKind === 'inv' ? 'Current / Maturity Value' : 'Status'}
                            </span>
                            <span className="font-mono font-bold text-sm text-emerald-700 dark:text-emerald-300">
                              {currentKind === 'inv' ? (formData.current ? inr(formData.current) : (formData.invested ? inr(formData.invested) : '—')) : (formData.status || 'Pending')}
                            </span>
                          </div>

                          <div>
                            <span className="text-[#6F7E92] dark:text-[#8594AA] text-[11px] block">
                              {currentKind === 'inv' ? 'Maturity Date' : 'Due Date'}
                            </span>
                            <span className="font-medium text-[#0F1B2D] dark:text-[#E8EDF5]">
                              {formData.maturity ? longD(formData.maturity) : (formData.due ? longD(formData.due) : '—')}
                            </span>
                          </div>
                        </div>
                      </>
                    )}

                    {formData.notes && (
                      <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 text-[11px] text-[#46566C] dark:text-[#A9B6C9]">
                        <span className="font-semibold">Notes / Details:</span> {formData.notes}
                      </div>
                    )}
                  </div>

                  {/* 3 User-Requested Direct Actions: Save, Edit, Delete/Replace */}
                  <div className="p-3 bg-white dark:bg-[#0B1220] rounded-xl border border-emerald-200 dark:border-emerald-800/60 space-y-2">
                    <div className="text-[11px] font-semibold text-[#46566C] dark:text-[#A9B6C9] text-center">
                      Ready to store this {KIND_NAME[currentKind]} in your records:
                    </div>

                    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2">
                      {/* Action 1: Save This Item immediately */}
                      <button
                        type="button"
                        onClick={() => handleSubmit()}
                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#0E7C86] hover:bg-[#128e9a] text-white text-sm font-bold shadow-md transition cursor-pointer"
                      >
                        <Check className="w-4 h-4" />
                        <span>✓ Save This {KIND_NAME[currentKind]}</span>
                      </button>

                      {/* Action 2: Edit Details (switches to manual mode with pre-filled fields) */}
                      <button
                        type="button"
                        onClick={() => setInputMode('manual')}
                        className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl border border-[#DCE2EA] dark:border-[#25324A] bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-xs font-semibold text-[#0F1B2D] dark:text-[#E8EDF5] transition cursor-pointer"
                        title="Edit any field before saving"
                      >
                        <Edit3 className="w-3.5 h-3.5 text-[#0E7C86]" />
                        <span>✏️ Edit Details</span>
                      </button>

                      {/* Action 3: Delete / Replace Voucher */}
                      <button
                        type="button"
                        onClick={handleClearAttachment}
                        className="flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl border border-rose-200 dark:border-rose-900 bg-rose-50/70 hover:bg-rose-100 dark:bg-rose-950/50 text-rose-700 dark:text-rose-300 text-xs font-semibold transition cursor-pointer"
                        title="Remove this attachment to scan a different one"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>🗑️ Delete / Replace</span>
                      </button>
                    </div>

                    {/* View voucher link */}
                    <div className="flex items-center justify-center pt-1 text-[11px] text-[#0E7C86]">
                      {existingAttachment && onViewAttachment && initialRow ? (
                        <button
                          type="button"
                          onClick={() => onViewAttachment(initialRow.id, formData.name || 'Document')}
                          className="flex items-center gap-1 font-semibold hover:underline"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          <span>View Attached Voucher Document</span>
                        </button>
                      ) : stagedFile ? (
                        <button
                          type="button"
                          onClick={() => scanAndPopulate(stagedFile)}
                          className="flex items-center gap-1 font-semibold hover:underline"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                          <span>Re-scan this document</span>
                        </button>
                      ) : null}
                    </div>
                  </div>
                </div>
              ) : (
                /* Scanner Dropzone & Quick Presets (when no voucher attached yet) */
                <div className="space-y-4">
                  {/* Dropzone */}
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setIsDragOver(true);
                    }}
                    onDragLeave={() => setIsDragOver(false)}
                    onDrop={(e) => {
                      e.preventDefault();
                      setIsDragOver(false);
                      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                        handleFilePicked(e.dataTransfer.files[0]);
                      }
                    }}
                    onClick={() => fileInputRef.current?.click()}
                    className={`transition-all rounded-2xl border-2 border-dashed p-6 text-center cursor-pointer ${
                      isDragOver
                        ? 'border-[#0E7C86] bg-teal-100/50 dark:bg-teal-950/40'
                        : 'border-teal-300 dark:border-teal-700 bg-teal-50/40 dark:bg-teal-950/20 hover:border-[#0E7C86] hover:bg-teal-50/80'
                    }`}
                  >
                    <div className="w-12 h-12 rounded-full bg-teal-100 dark:bg-teal-900/60 flex items-center justify-center text-[#0E7C86] mx-auto mb-3">
                      <FileUp className="w-6 h-6" />
                    </div>
                    <div className="text-sm font-bold text-[#0F1B2D] dark:text-[#E8EDF5]">
                      Scan FD Receipt or Certificate (PDF / Image)
                    </div>
                    <div className="text-xs text-[#6F7E92] dark:text-[#8594AA] mt-1 max-w-sm mx-auto">
                      Drop voucher here or click to browse. The scanner extracts Bank, Account Number, Amount, Interest Rate, and Dates automatically with zero typing!
                    </div>
                    <div className="mt-3 inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#0E7C86] text-white text-xs font-semibold shadow-xs">
                      <Paperclip className="w-3.5 h-3.5" />
                      <span>Select Receipt / Voucher</span>
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*,.pdf"
                      className="hidden"
                      onChange={(e) => handleFilePicked(e.target.files?.[0] || null)}
                    />
                  </div>

                  {/* Quick 1-click test buttons for Irin Joseph's bank FDs */}
                  {kind === 'inv' && (
                    <div className="p-3.5 rounded-2xl bg-white dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] shadow-2xs">
                      <div className="text-xs font-bold text-[#0F1B2D] dark:text-[#E8EDF5] mb-2 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-[#0E7C86]" />
                        <span>Quick 1-Tap Auto-Scan Test Receipts:</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            loadSampleAttachment(
                              '/assets/aistudio/Irin_FD_SBI_74546726.pdf',
                              'Irin_FD_SBI_74546726.pdf'
                            )
                          }
                          className="flex items-center gap-2 p-2.5 rounded-xl bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/80 dark:hover:bg-teal-900 text-teal-900 dark:text-teal-200 text-xs font-semibold border border-teal-200 dark:border-teal-800 transition shadow-2xs text-left cursor-pointer"
                        >
                          <FileText className="w-4 h-4 text-[#0E7C86] flex-shrink-0" />
                          <div className="truncate">
                            <span className="block truncate font-bold">SBI Senior Citizen FD</span>
                            <span className="text-[10px] text-teal-700 dark:text-teal-300 font-mono">
                              ₹4,00,000 · 7.10% p.a.
                            </span>
                          </div>
                        </button>

                        <button
                          type="button"
                          onClick={() =>
                            loadSampleAttachment(
                              '/assets/aistudio/Irin_FD_Gramin_Bank_5d23749c.pdf',
                              'Irin_FD_Gramin_Bank_5d23749c.pdf'
                            )
                          }
                          className="flex items-center gap-2 p-2.5 rounded-xl bg-teal-50 hover:bg-teal-100 dark:bg-teal-950/80 dark:hover:bg-teal-900 text-teal-900 dark:text-teal-200 text-xs font-semibold border border-teal-200 dark:border-teal-800 transition shadow-2xs text-left cursor-pointer"
                        >
                          <FileText className="w-4 h-4 text-[#0E7C86] flex-shrink-0" />
                          <div className="truncate">
                            <span className="block truncate font-bold">Kerala Gramin Bank FD</span>
                            <span className="text-[10px] text-teal-700 dark:text-teal-300 font-mono">
                              ₹56,323 · 7.00% p.a.
                            </span>
                          </div>
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Switch to manual typing prompt */}
                  <div className="text-center p-3 rounded-xl bg-slate-50 dark:bg-[#0B1220]/60 border border-slate-200 dark:border-slate-800 text-xs text-[#6F7E92] dark:text-[#8594AA]">
                    <span>Prefer to enter details manually? </span>
                    <button
                      type="button"
                      onClick={() => setInputMode('manual')}
                      className="text-[#0E7C86] font-semibold hover:underline cursor-pointer"
                    >
                      Click Option 2: Type Details Manually →
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ========================================================= */}
          {/* OPTION 2: TYPE DETAILS MANUALLY                           */}
          {/* ========================================================= */}
          {inputMode === 'manual' && (
            <div className="space-y-4">
              {/* Helper tip at top of manual form */}
              <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-50 dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] text-xs">
                <span className="text-[#6F7E92] dark:text-[#8594AA]">
                  {hasAttachment
                    ? `Editing autofilled fields from "${activeFileName}"`
                    : 'Typing details manually.'}
                </span>
                <button
                  type="button"
                  onClick={() => setInputMode('scan')}
                  className="text-xs font-semibold text-[#0E7C86] hover:underline flex items-center gap-1 cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>Switch to ⚡ Auto-Scan</span>
                </button>
              </div>

              {/* UTILITY FIELDS */}
              {currentKind === 'util' && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Bill / Utility Description
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. BESCOM Electricity Bill, BWSSB Water, Tata Power"
                      value={formData.name || ''}
                      onChange={(e) => handleChange('name', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Utility Type
                      </label>
                      <select
                        value={formData.utilityType || 'electricity'}
                        onChange={(e) => handleChange('utilityType', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        <option value="electricity">Electricity Bill</option>
                        <option value="water">Water Bill</option>
                        <option value="broadband">Broadband / WiFi</option>
                        <option value="mobile">Mobile / Landline</option>
                        <option value="gas">Piped Gas (PNG) / LPG</option>
                        <option value="dth">DTH / Cable TV</option>
                        <option value="maintenance">Society Maintenance</option>
                        <option value="other">Other Utility</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Service Provider / Board
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. BESCOM, BWSSB, Adani Electricity, Airtel"
                        value={formData.provider || ''}
                        onChange={(e) => handleChange('provider', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Consumer / Account / Meter No.
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 0482019482 (leading zeros preserved)"
                        value={formData.accountNumber || formData.ref || ''}
                        onChange={(e) => {
                          handleChange('accountNumber', e.target.value);
                          handleChange('ref', e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm font-mono focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Family Member / Property
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Arun Menon - Flat 4B"
                        value={formData.holder || ''}
                        onChange={(e) => handleChange('holder', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Bill Amount (₹)
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 2680"
                        value={formData.billAmount ?? formData.amount ?? ''}
                        onChange={(e) => {
                          handleChange('billAmount', e.target.value);
                          handleChange('amount', e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm font-bold focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Payment Due Date (IST)
                      </label>
                      <input
                        type="date"
                        value={formData.dueDate || formData.due || ''}
                        onChange={(e) => {
                          handleChange('dueDate', e.target.value);
                          handleChange('due', e.target.value);
                        }}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Billing Period
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Oct 2026 or 01-09-2026 to 30-09-2026"
                        value={formData.billingPeriod || ''}
                        onChange={(e) => handleChange('billingPeriod', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Billing Cycle Frequency
                      </label>
                      <select
                        value={formData.freq || 'monthly'}
                        onChange={(e) => handleChange('freq', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        <option value="monthly">Monthly</option>
                        <option value="bimonthly">Every 2 Months (Bi-monthly)</option>
                        <option value="quarterly">Quarterly</option>
                        <option value="annual">Yearly</option>
                        <option value="once">One-Time</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Notes / Meter Reading / Remarks
                    </label>
                    <input
                      type="text"
                      placeholder="Optional notes or online payment portal link"
                      value={formData.notes || ''}
                      onChange={(e) => handleChange('notes', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>
                </>
              )}

              {/* DUE DATE FIELDS */}
              {currentKind === 'due' && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Home Loan EMI, LPG Cylinder, Car Insurance"
                      value={formData.name || ''}
                      onChange={(e) => handleChange('name', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Category
                      </label>
                      <select
                        value={formData.category || 'utility'}
                        onChange={(e) => handleChange('category', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        {Object.entries(CATS).map(([k, label]) => (
                          <option key={k} value={k}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Amount (₹)
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 42500"
                        value={formData.amount ?? ''}
                        onChange={(e) => handleChange('amount', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Next due date
                      </label>
                      <input
                        type="date"
                        value={formData.due || ''}
                        onChange={(e) => handleChange('due', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Repeats
                      </label>
                      <select
                        value={formData.freq || 'monthly'}
                        onChange={(e) => handleChange('freq', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        {Object.entries(FREQ).map(([k, label]) => (
                          <option key={k} value={k}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {formData.freq === 'days' && (
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        If "Every N days": number of days
                      </label>
                      <input
                        type="number"
                        placeholder="35"
                        value={formData.interval ?? 35}
                        onChange={(e) => handleChange('interval', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Provider / Bank / Biller
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. HDFC Bank, Tata AIG, BESCOM"
                        value={formData.provider || ''}
                        onChange={(e) => handleChange('provider', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        For whom (Family member / holder)
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Ravi, Meena, Self"
                        value={formData.holder || ''}
                        onChange={(e) => handleChange('holder', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Policy / Account / Consumer no.
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. POL-8812903"
                      value={formData.ref || ''}
                      onChange={(e) => handleChange('ref', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Alert this many days before (e.g. 30, 7, 1)
                    </label>
                    <input
                      type="text"
                      placeholder="30, 7, 1"
                      value={formData.alerts || ''}
                      onChange={(e) => handleChange('alerts', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Notes / remarks
                    </label>
                    <input
                      type="text"
                      placeholder="Optional details or website link"
                      value={formData.notes || ''}
                      onChange={(e) => handleChange('notes', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>
                </>
              )}

              {/* INVESTMENT FIELDS */}
              {currentKind === 'inv' && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Investment Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. SBI Senior Citizen Fixed Deposit, HDFC Top 100"
                      value={formData.name || ''}
                      onChange={(e) => handleChange('name', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Type
                      </label>
                      <select
                        value={formData.type || 'fd'}
                        onChange={(e) => handleChange('type', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        {Object.entries(INV).map(([k, label]) => (
                          <option key={k} value={k}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Holder / Depositor
                      </label>
                      <input
                        type="text"
                        placeholder="Whose holding is it? e.g. Irin Joseph"
                        value={formData.holder || ''}
                        onChange={(e) => handleChange('holder', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Bank / Institution / AMC
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. State Bank of India, Kerala Gramin Bank"
                        value={formData.institution || ''}
                        onChange={(e) => handleChange('institution', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Account / Certificate / Folio No.
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 43203056352, 40328202400250"
                        value={formData.ref || ''}
                        onChange={(e) => handleChange('ref', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Amount Invested (₹)
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 400000"
                        value={formData.invested ?? ''}
                        onChange={(e) => handleChange('invested', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Maturity / Current Value (₹)
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 433303"
                        value={formData.current ?? ''}
                        onChange={(e) => handleChange('current', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Interest Rate (% p.a.)
                      </label>
                      <input
                        type="number"
                        step="any"
                        placeholder="e.g. 7.10"
                        value={formData.rate ?? ''}
                        onChange={(e) => handleChange('rate', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Start / Deposit Date
                      </label>
                      <input
                        type="date"
                        value={formData.start || ''}
                        onChange={(e) => handleChange('start', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Maturity Date
                      </label>
                      <input
                        type="date"
                        value={formData.maturity || ''}
                        onChange={(e) => handleChange('maturity', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Next Interest / Coupon Date
                      </label>
                      <input
                        type="date"
                        value={formData.nextint || ''}
                        onChange={(e) => handleChange('nextint', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Alert this many days before (e.g. 30, 15, 7, 1)
                    </label>
                    <input
                      type="text"
                      placeholder="30, 15, 7, 1"
                      value={formData.alerts || ''}
                      onChange={(e) => handleChange('alerts', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Notes / Remarks / Nominee
                    </label>
                    <input
                      type="text"
                      placeholder="Remarks, nominee name, branch contact"
                      value={formData.notes || ''}
                      onChange={(e) => handleChange('notes', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>
                </>
              )}

              {/* RECORD FIELDS */}
              {currentKind === 'rec' && (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Title
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Passport, Driving Licence, Health Insurance, RC"
                      value={formData.title || ''}
                      onChange={(e) => handleChange('title', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Document Classification
                      </label>
                      <select
                        value={formData.type || 'id'}
                        onChange={(e) => handleChange('type', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      >
                        {Object.entries(REC).map(([k, label]) => (
                          <option key={k} value={k}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                        Holder Name (Household Member)
                      </label>
                      <input
                        type="text"
                        placeholder="Whose document is it? e.g. Vikram Sharma"
                        value={formData.holder || ''}
                        onChange={(e) => handleChange('holder', e.target.value)}
                        className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      {formData.type === 'passport'
                        ? 'Passport Booklet Number'
                        : formData.type === 'licence'
                        ? 'Driving Licence Number'
                        : formData.type === 'insurance' || formData.type === 'policy'
                        ? 'Policy / Certificate Number'
                        : formData.type === 'pan'
                        ? 'PAN Number (10 alphanumeric)'
                        : formData.type === 'aadhaar'
                        ? 'Masked Aadhaar Number'
                        : 'Document / Account / Policy Number'}
                    </label>
                    <input
                      type="text"
                      placeholder={
                        formData.type === 'passport'
                          ? 'e.g. V9481024'
                          : formData.type === 'licence'
                          ? 'e.g. TN-01-2016-0004918'
                          : formData.type === 'pan'
                          ? 'e.g. BPWPS4820K'
                          : formData.type === 'aadhaar'
                          ? 'e.g. XXXX-XXXX-4819'
                          : 'e.g. DL-0420110012345'
                      }
                      value={formData.number || ''}
                      onChange={(e) => handleChange('number', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm font-mono focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  {/* Document-Specific Statutory Validity Banners & Fields */}
                  {formData.type === 'passport' && (
                    <div className="p-3 rounded-xl bg-blue-50/70 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-900 text-xs space-y-1.5">
                      <div className="font-bold text-blue-900 dark:text-blue-200 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-blue-600" />
                        <span>Passports Act, 1967 Statutory Validity Rules</span>
                      </div>
                      <p className="text-blue-800 dark:text-blue-300">
                        Adult passports are valid for 10 years (5 years for minors). Expiry date is mandatory and can <strong>never</strong> be classified as "Permanent".
                      </p>
                      {formData.issued && !formData.expires && (
                        <button
                          type="button"
                          onClick={() => {
                            const sug = suggestExpiryDate('passport', formData.issued);
                            if (sug?.suggestedExpiry) {
                              handleChange('expires', sug.suggestedExpiry);
                            }
                          }}
                          className="mt-1 px-2.5 py-1 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-bold text-[11px] flex items-center gap-1 transition cursor-pointer"
                        >
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Suggest 10-Yr Expiry Date ({suggestExpiryDate('passport', formData.issued)?.suggestedExpiry})</span>
                        </button>
                      )}
                    </div>
                  )}

                  {formData.type === 'licence' && (
                    <div className="p-3 rounded-xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200 dark:border-teal-900 text-xs">
                      <div className="font-bold text-teal-900 dark:text-teal-200 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-teal-600" />
                        <span>Motor Vehicles Act, 1988 Validity</span>
                      </div>
                      <p className="text-teal-800 dark:text-teal-300 mt-0.5">
                        Driving licences have statutory validity periods (typically 20 years or until age 50 for non-transport; 3/5 years for transport vehicles).
                      </p>
                    </div>
                  )}

                  {(formData.type === 'pan' || formData.type === 'aadhaar') && (
                    <div className="p-3 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 text-xs">
                      <div className="font-bold text-emerald-900 dark:text-emerald-200 flex items-center gap-1.5">
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                        <span>Statutory Lifelong Document — No Expiry Date Required</span>
                      </div>
                      <p className="text-emerald-800 dark:text-emerald-300 mt-0.5">
                        {formData.type === 'pan'
                          ? 'Section 139A Income-tax Act, 1961: PAN is a permanent identifier with no expiry date.'
                          : 'Aadhaar Act, 2016: 12-digit lifelong biometric identity with no statutory expiration date.'}
                      </p>
                    </div>
                  )}

                  {/* Separate fields for Insurance: Coverage Commencement, Policy Expiry/Renewal, Premium Payment Due Date, Sum Insured */}
                  {(formData.type === 'insurance' || formData.type === 'policy') ? (
                    <div className="space-y-3 p-3.5 rounded-xl bg-purple-50/50 dark:bg-purple-950/30 border border-purple-200 dark:border-purple-900">
                      <div className="text-xs font-bold text-purple-900 dark:text-purple-200 flex items-center gap-1.5">
                        <ShieldCheck className="w-4 h-4 text-purple-600" />
                        <span>Insurance Act, 1938 & IRDAI — Distinct Renewal & Premium Tracking</span>
                      </div>
                      <p className="text-[11px] text-purple-800 dark:text-purple-300">
                        Policy coverage renewal date and premium payment due date are recorded as separate events so you never lose coverage:
                      </p>

                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div>
                          <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                            Insurance Company / Provider
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. Star Health, HDFC Life, ICICI Lombard"
                            value={formData.institution || formData.provider || ''}
                            onChange={(e) => {
                              handleChange('institution', e.target.value);
                              handleChange('provider', e.target.value);
                            }}
                            className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                            Sum Insured / IDV (₹)
                          </label>
                          <input
                            type="number"
                            placeholder="e.g. 1500000"
                            value={formData.sumInsured ?? ''}
                            onChange={(e) => handleChange('sumInsured', e.target.value)}
                            className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                          />
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                            Coverage Commencement
                          </label>
                          <input
                            type="date"
                            value={formData.issued || formData.start || ''}
                            onChange={(e) => {
                              handleChange('issued', e.target.value);
                              handleChange('start', e.target.value);
                            }}
                            className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                            Policy Expiry / Renewal Date
                          </label>
                          <input
                            type="date"
                            value={formData.expires || ''}
                            onChange={(e) => handleChange('expires', e.target.value)}
                            className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                          />
                        </div>

                        <div>
                          <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                            Next Premium Due Date
                          </label>
                          <input
                            type="date"
                            value={formData.due || ''}
                            onChange={(e) => handleChange('due', e.target.value)}
                            className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                          />
                        </div>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                          Annual Premium Amount (₹)
                        </label>
                        <input
                          type="number"
                          placeholder="e.g. 18450"
                          value={formData.premium ?? formData.amount ?? ''}
                          onChange={(e) => {
                            handleChange('premium', e.target.value);
                            handleChange('amount', e.target.value);
                          }}
                          className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                        />
                      </div>
                    </div>
                  ) : formData.type !== 'pan' && formData.type !== 'aadhaar' ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                          Date of Issue
                        </label>
                        <input
                          type="date"
                          value={formData.issued || ''}
                          onChange={(e) => handleChange('issued', e.target.value)}
                          className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                          Expiry Date {hasPrescribedExpiry(formData.type) && <span className="text-rose-600 font-bold">* (Mandatory)</span>}
                        </label>
                        <input
                          type="date"
                          value={formData.expires || ''}
                          onChange={(e) => handleChange('expires', e.target.value)}
                          className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                        />
                      </div>
                    </div>
                  ) : null}

                  {/* Live Date Validation Warning */}
                  {formData.issued && formData.expires && (() => {
                    const check = validateDocumentDates(formData.issued, formData.expires);
                    if (!check.isValid) {
                      return (
                        <div className="p-2.5 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs flex items-center gap-1.5">
                          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                          <span>{check.error || check.warning}</span>
                        </div>
                      );
                    }
                    return null;
                  })()}

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Advance Alert Notifications (Days before expiry, e.g. 60, 30, 7)
                    </label>
                    <input
                      type="text"
                      placeholder="60, 30, 7"
                      value={formData.alerts || ''}
                      onChange={(e) => handleChange('alerts', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#46566C] dark:text-[#A9B6C9] mb-1">
                      Notes &amp; Safe Storage Location
                    </label>
                    <input
                      type="text"
                      placeholder="Bank locker, physical folder, contact person"
                      value={formData.notes || ''}
                      onChange={(e) => handleChange('notes', e.target.value)}
                      className="w-full bg-[#FFFFFF] dark:bg-[#0B1220] border border-[#DCE2EA] dark:border-[#25324A] rounded-xl px-3 py-2 text-sm focus:outline-2 focus:outline-[#0E7C86]"
                    />
                  </div>
                </>
              )}
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-4 border-t border-[#DCE2EA] dark:border-[#25324A] flex items-center justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-sm font-medium border border-[#DCE2EA] dark:border-[#25324A] hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className={`px-5 py-2 rounded-xl text-sm font-semibold text-white transition shadow-sm cursor-pointer ${
                dupWarningDismissed ? 'bg-amber-600 hover:bg-amber-700' : 'bg-[#0E7C86] hover:bg-[#128e9a]'
              }`}
            >
              {dupWarningDismissed ? 'Save Anyway' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
