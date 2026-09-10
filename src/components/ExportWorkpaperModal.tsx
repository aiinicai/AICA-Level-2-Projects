import React, { useState } from 'react';
import {
  X,
  FileSpreadsheet,
  FileText,
  FileDown,
  Printer,
  CheckCircle2,
  Download,
  Check,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { EngagementData, ComputedMateriality } from '../types';
import {
  exportWorkpaperToExcel,
  exportWorkpaperToWord,
  exportWorkpaperToPdf,
} from '../utils/workpaperExporter';

interface ExportWorkpaperModalProps {
  isOpen: boolean;
  onClose: () => void;
  engagement: EngagementData;
  materiality: ComputedMateriality;
  onOpenPrintReport: () => void;
}

export const ExportWorkpaperModal: React.FC<ExportWorkpaperModalProps> = ({
  isOpen,
  onClose,
  engagement,
  materiality,
  onOpenPrintReport,
}) => {
  const [downloadingFormat, setDownloadingFormat] = useState<string | null>(null);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExport = async (format: 'excel' | 'word' | 'pdf') => {
    setDownloadingFormat(format);
    setDownloadSuccess(null);

    try {
      if (format === 'excel') {
        exportWorkpaperToExcel(engagement, materiality);
      } else if (format === 'word') {
        exportWorkpaperToWord(engagement, materiality);
      } else if (format === 'pdf') {
        await exportWorkpaperToPdf(engagement, materiality);
      }
      setDownloadSuccess(format);
      setTimeout(() => setDownloadSuccess(null), 4000);
    } catch (err) {
      console.error(`Export failed for ${format}:`, err);
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white dark:bg-[#15191f] text-[#1c222b] dark:text-[#f3f4f6] w-full max-w-2xl rounded-xl shadow-2xl overflow-hidden border border-[#dedbd2] dark:border-[#272f38] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#dedbd2] dark:border-[#272f38] bg-[#f8f7f4] dark:bg-[#1a2027]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-stone-900 dark:bg-stone-100 text-white dark:text-stone-900 flex items-center justify-center shadow-xs">
              <Download className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                Export Complete Statutory Audit Workpaper
              </h2>
              <p className="text-xs text-stone-500 dark:text-stone-400">
                Generate compliant audit documentation files per ICAI Standards on Auditing
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 dark:hover:text-stone-200 hover:bg-stone-200 dark:hover:bg-stone-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 text-xs sm:text-sm">
          {downloadSuccess && (
            <div className="p-3.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 flex items-center gap-2.5 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span className="font-medium text-xs">
                Successfully generated and downloaded your {downloadSuccess.toUpperCase()} workpaper!
              </span>
            </div>
          )}

          <div className="p-3 bg-stone-50 dark:bg-[#1a2027] rounded-lg border border-stone-200 dark:border-stone-800 flex items-center justify-between">
            <div>
              <span className="font-semibold text-stone-800 dark:text-stone-200 block">
                {engagement.clientName}
              </span>
              <span className="text-xs text-stone-500">
                Financial Year: {engagement.financialYear} • Lead: {engagement.engagementPartner}
              </span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-100 text-amber-900 dark:bg-amber-950/60 dark:text-amber-300 text-[11px] font-semibold">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>ICAI SAs Compliant</span>
            </div>
          </div>

          <p className="text-xs text-stone-600 dark:text-stone-400 leading-relaxed">
            Select your preferred file format below. All exports include the complete engagement index, SA 320 materiality calculations, Trial Balance schedules, SA 315 & SA 240 risk registers, SA 330 audit strategy matrix, and SQC 1 sign-offs.
          </p>

          {/* 3 Format Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            {/* Word Card */}
            <div className="p-4 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-[#1c222b] hover:border-blue-500 transition-all flex flex-col justify-between shadow-xs">
              <div>
                <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 flex items-center justify-center mb-3">
                  <FileText className="w-5 h-5" />
                </div>
                <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100">
                  Microsoft Word
                </h3>
                <span className="text-[11px] font-mono text-blue-600 dark:text-blue-400 block mb-2">
                  .doc / .docx
                </span>
                <p className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed">
                  Formatted Audit Planning Memorandum with styled headings, schedules, and sign-off blocks. Editable in Word & Google Docs.
                </p>
              </div>

              <button
                onClick={() => handleExport('word')}
                disabled={downloadingFormat !== null}
                className="mt-4 w-full py-2 px-3 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
              >
                {downloadingFormat === 'word' ? (
                  <span>Generating...</span>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Word</span>
                  </>
                )}
              </button>
            </div>

            {/* Excel Card */}
            <div className="p-4 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-[#1c222b] hover:border-emerald-500 transition-all flex flex-col justify-between shadow-xs">
              <div>
                <div className="w-10 h-10 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center mb-3">
                  <FileSpreadsheet className="w-5 h-5" />
                </div>
                <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100">
                  Microsoft Excel
                </h3>
                <span className="text-[11px] font-mono text-emerald-600 dark:text-emerald-400 block mb-2">
                  .xlsx (Multi-Sheet)
                </span>
                <p className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed">
                  Comprehensive 10-tab audit workpaper workbook: Engagement, Materiality, TB, FS Risks, Fraud Register, Strategy & Notes.
                </p>
              </div>

              <button
                onClick={() => handleExport('excel')}
                disabled={downloadingFormat !== null}
                className="mt-4 w-full py-2 px-3 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
              >
                {downloadingFormat === 'excel' ? (
                  <span>Generating...</span>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Excel</span>
                  </>
                )}
              </button>
            </div>

            {/* PDF Card */}
            <div className="p-4 rounded-xl border border-stone-200 dark:border-stone-700 bg-white dark:bg-[#1c222b] hover:border-rose-500 transition-all flex flex-col justify-between shadow-xs">
              <div>
                <div className="w-10 h-10 rounded-lg bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 flex items-center justify-center mb-3">
                  <FileDown className="w-5 h-5" />
                </div>
                <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100">
                  PDF Document
                </h3>
                <span className="text-[11px] font-mono text-rose-600 dark:text-rose-400 block mb-2">
                  .pdf (Executive)
                </span>
                <p className="text-xs text-stone-500 dark:text-stone-400 leading-relaxed">
                  Clean, structured PDF document containing core materiality determination, key aggregates, and significant risks.
                </p>
              </div>

              <button
                onClick={() => handleExport('pdf')}
                disabled={downloadingFormat !== null}
                className="mt-4 w-full py-2 px-3 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-xs transition-colors disabled:opacity-50"
              >
                {downloadingFormat === 'pdf' ? (
                  <span>Generating...</span>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Download PDF</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Browser High-Res Print Option */}
          <div className="p-3.5 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Printer className="w-4 h-4 text-stone-500" />
              <div>
                <span className="font-medium text-xs text-stone-800 dark:text-stone-200 block">
                  Need a full-bleed multi-page printout?
                </span>
                <span className="text-[11px] text-stone-500">
                  Open the interactive print view with custom margins and page breaks.
                </span>
              </div>
            </div>
            <button
              onClick={() => {
                onClose();
                onOpenPrintReport();
              }}
              className="px-3 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-[#15191f] text-xs font-semibold text-stone-800 dark:text-stone-200 hover:bg-stone-100 transition-colors shadow-xs"
            >
              Open Print View
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#dedbd2] dark:border-[#272f38] bg-[#f8f7f4] dark:bg-[#1a2027] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-md border border-stone-300 dark:border-stone-700 text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800 text-xs font-medium transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
