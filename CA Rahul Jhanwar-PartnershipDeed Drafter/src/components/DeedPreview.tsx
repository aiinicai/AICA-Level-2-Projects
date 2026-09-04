import React, { useState } from 'react';
import { 
  Download, 
  Printer, 
  Copy, 
  Check, 
  ZoomIn, 
  ZoomOut, 
  Maximize2, 
  Minimize2,
  FileText,
  FileDown,
  Loader2,
  ShieldAlert,
  Scissors,
  BookOpen,
  ShieldCheck,
  CreditCard
} from 'lucide-react';
import { DeedFormData } from '../types';
import { constructDeedBody } from '../utils/deedEngine';
import { PageBreakModal } from './PageBreakModal';

interface DeedPreviewProps {
  formData: DeedFormData;
  onDownloadWord: () => void;
  onDownloadPDF: () => void;
  onPrint?: () => void;
  onUpdateFormData?: (updates: Partial<DeedFormData>) => void;
  isExportingPdf?: boolean;
}

export const DeedPreview: React.FC<DeedPreviewProps> = ({
  formData,
  onDownloadWord,
  onDownloadPDF,
  onPrint,
  onUpdateFormData,
  isExportingPdf = false,
}) => {
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [isPageBreakModalOpen, setIsPageBreakModalOpen] = useState<boolean>(false);

  const deedHtml = constructDeedBody(formData);
  const activeBreaksCount = (formData.pageBreakBeforeClauses?.length || 0) + (formData.signaturePageBreak === 'newPage' ? 1 : 0);

  // Profit Share Validation (Adaptive to deed type)
  let totalProfitShare = 0;
  if (formData.deedType === 'supplementary') {
    const supp = formData.supplementaryConfig;
    const retiringIds = supp?.retiringPartnerIds || [];
    const continuing = (formData.partners || []).filter(p => !retiringIds.includes(p.id));
    const incoming = supp?.incomingPartners || [];
    const allActive = [...continuing, ...incoming];
    totalProfitShare = allActive.reduce((sum, p) => {
      const val = supp?.revisedProfitShares?.[p.id];
      const num = parseFloat(val !== undefined && val !== '' ? val : (p.profitShare || '0')) || 0;
      return sum + num;
    }, 0);
  } else {
    totalProfitShare = formData.partners.reduce(
      (sum, p) => sum + (parseFloat(p.profitShare) || 0), 
      0
    );
  }
  const isProfitValid = Math.abs(totalProfitShare - 100) < 0.01;

  const handleCopyText = () => {
    // Extract plain text representation
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = deedHtml;
    const plainText = tempDiv.innerText || tempDiv.textContent || '';
    navigator.clipboard.writeText(plainText);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2500);
  };

  return (
    <div className={`flex flex-col bg-[#E2E8F0] border border-slate-300 overflow-hidden shadow-xs ${
      isFullscreen ? 'fixed inset-0 z-50 rounded-none bg-slate-900/90 p-4' : 'h-full rounded-xl'
    }`}>
      
      {/* Preview Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-white text-slate-800 gap-2 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded bg-blue-50 text-blue-700 flex items-center justify-center font-bold text-xs">
            <FileText className="w-3.5 h-3.5" />
          </div>
          <span className="font-bold text-xs text-slate-900 tracking-wide">
            {formData.deedType === 'supplementary' 
              ? 'Supplementary Deed Preview (A4 Legal)' 
              : formData.deedType === 'dissolution' 
              ? 'Dissolution Deed Preview (A4 Legal)' 
              : 'Live Document Preview (A4 Legal)'}
          </span>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-1.5">
          
          {/* Zoom controls */}
          <div className="hidden sm:flex items-center bg-slate-100 rounded-lg p-0.5 border border-slate-200 mr-1">
            <button
              type="button"
              onClick={() => setZoomLevel(Math.max(70, zoomLevel - 10))}
              className="p-1 text-slate-600 hover:text-slate-900 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <span className="px-2 text-[11px] font-mono text-slate-700 min-w-10 text-center font-semibold">
              {zoomLevel}%
            </span>
            <button
              type="button"
              onClick={() => setZoomLevel(Math.min(150, zoomLevel + 10))}
              className="p-1 text-slate-600 hover:text-slate-900 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Cover Page Toggle */}
          {onUpdateFormData && (
            <button
              type="button"
              onClick={() => onUpdateFormData({ includeCoverPage: formData.includeCoverPage === false ? true : false })}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold transition ${
                formData.includeCoverPage !== false
                  ? 'border-indigo-200 bg-indigo-50 hover:bg-indigo-100 text-indigo-700'
                  : 'border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-600'
              }`}
              title="Toggle Cover / Front Title Page"
            >
              <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
              <span>Cover Page:</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                formData.includeCoverPage !== false ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600'
              }`}>
                {formData.includeCoverPage !== false ? 'ON' : 'OFF'}
              </span>
            </button>
          )}

          {/* ID Proofs Attached Page Toggle */}
          {onUpdateFormData && (
            <button
              type="button"
              onClick={() => onUpdateFormData({ includeKycAnnexure: !Boolean(formData.includeKycAnnexure) })}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-xs font-semibold transition ${
                Boolean(formData.includeKycAnnexure)
                  ? 'border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-800'
                  : 'border-slate-300 bg-slate-50 hover:bg-slate-100 text-slate-600'
              }`}
              title="Toggle attached single-page PAN & Aadhaar proof copies (Notary sheets removed)"
            >
              <CreditCard className="w-3.5 h-3.5 text-emerald-600" />
              <span className="hidden xl:inline">ID Proof Copies:</span>
              <span className="xl:hidden">ID Proofs:</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                Boolean(formData.includeKycAnnexure) ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
              }`}>
                {Boolean(formData.includeKycAnnexure) ? 'ON' : 'OFF'}
              </span>
            </button>
          )}

          {/* Page Breaks & Spacing Options Button */}
          {onUpdateFormData && (
            <button
              type="button"
              onClick={() => setIsPageBreakModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-blue-200 bg-blue-50/80 hover:bg-blue-100 text-blue-700 text-xs font-semibold transition"
              title="Configure manual page breaks, density and signature flow"
            >
              <Scissors className="w-3.5 h-3.5 text-blue-600" />
              <span>Page Breaks</span>
              {activeBreaksCount > 0 ? (
                <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.2 rounded-full font-bold">
                  {activeBreaksCount}
                </span>
              ) : (
                <span className="text-[10px] text-blue-600 font-medium">Auto</span>
              )}
            </button>
          )}

          {/* Copy Plain Text */}
          <button
            type="button"
            onClick={handleCopyText}
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
            title="Copy Text"
          >
            {isCopied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5 text-slate-500" />}
            <span className="hidden md:inline">{isCopied ? 'Copied' : 'Copy Text'}</span>
          </button>

          {/* Download Word */}
          <button
            type="button"
            onClick={onDownloadWord}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-xs font-bold text-white transition shadow-xs"
            title="Download formatted Microsoft Word .doc file"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Word (.doc)</span>
          </button>

          {/* Download PDF */}
          <button
            type="button"
            onClick={onDownloadPDF}
            disabled={isExportingPdf}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-emerald-700 hover:bg-emerald-800 text-xs font-bold text-white transition shadow-xs disabled:opacity-60"
            title="Generate and download PDF file"
          >
            {isExportingPdf ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Creating PDF...</span>
              </>
            ) : (
              <>
                <FileDown className="w-3.5 h-3.5" />
                <span>Save PDF</span>
              </>
            )}
          </button>

          {/* Print A4 */}
          <button
            type="button"
            onClick={onPrint || onDownloadPDF}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-900 text-xs font-bold text-white transition shadow-xs"
            title="Print to printer or save via browser print dialog"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print A4</span>
          </button>

          {/* Fullscreen toggle */}
          <button
            type="button"
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 text-slate-600 hover:text-slate-900 transition ml-1"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>

        </div>
      </div>

      {/* Validation banner if profit share != 100% */}
      {!isProfitValid && (
        <div className="bg-amber-50 text-amber-900 border-b border-amber-200 px-4 py-1.5 text-xs font-semibold flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span>
            Notice: Partner profit shares currently sum to {totalProfitShare.toFixed(2)}% (Should equal exactly 100.00%).
          </span>
        </div>
      )}

      {/* Paper Container Viewport */}
      <div className="flex-1 p-4 sm:p-6 overflow-y-auto flex justify-center bg-[#E2E8F0]">
        
        {/* Rendered Deed Paper */}
        <div 
          style={{ 
            transform: `scale(${zoomLevel / 100})`, 
            transformOrigin: 'top center',
            transition: 'transform 0.15s ease-out'
          }}
          className="w-full max-w-[850px] bg-white text-black p-8 sm:p-14 shadow-lg rounded-sm border border-slate-300 font-serif text-[14px] leading-[1.75] text-justify select-text h-fit"
        >
          {/* Injecting styles for deed table and execution tables to match user template */}
          <style>{`
            .deed-title {
              text-align: center;
              font-size: 19px;
              font-weight: bold;
              letter-spacing: 1.5px;
              text-decoration: underline;
              margin-bottom: 24px;
              font-family: 'Times New Roman', Times, serif;
            }
            p, .deed-p {
              margin-top: 0;
              margin-bottom: 18px;
              line-height: 1.75;
            }
            .deed-table {
              width: 100%;
              border-collapse: collapse;
              margin: 16px 0;
              table-layout: fixed;
            }
            .deed-table th, .deed-table td {
              border: 1px solid #000;
              padding: 8px 10px;
              text-align: left;
              word-wrap: break-word;
            }
            .exec-table {
              width: 100%;
              border-collapse: collapse;
              margin-top: 14px;
              margin-bottom: 22px;
              table-layout: fixed;
            }
            .exec-table th, .exec-table td {
              border: 1px solid #000;
              padding: 8px;
              word-wrap: break-word;
              font-size: 13px;
            }
            .photo-box, .thumb-box {
              width: 75px;
              height: 85px;
              border: 1px dashed #475569;
              margin: auto;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 8.5px;
              text-align: center;
              color: #334155;
              background-color: #f8fafc;
            }
            .sign-space {
              min-height: 80px;
              display: flex;
              flex-direction: column;
              justify-content: flex-end;
              align-items: center;
              font-size: 12px;
              font-weight: bold;
            }
            .page-break-before {
              page-break-before: always;
              margin-top: 36px;
              padding-top: 16px;
              border-top: 2px dashed #94a3b8;
              position: relative;
            }
            .page-break-before::before {
              content: "✂️ [MANUAL PAGE BREAK] - Next section starts on fresh page";
              display: block;
              font-family: system-ui, -apple-system, sans-serif;
              font-size: 11px;
              font-weight: 700;
              color: #334155;
              text-align: center;
              margin-bottom: 14px;
              background: #f1f5f9;
              padding: 3px 10px;
              border: 1px solid #cbd5e1;
              border-radius: 6px;
              width: fit-content;
              margin-left: auto;
              margin-right: auto;
            }
            .page-break-after {
              page-break-after: always;
              margin-bottom: 36px;
              padding-bottom: 20px;
              border-bottom: 2px dashed #6366f1;
              position: relative;
            }
            .page-break-after::after {
              content: "📑 [COVER PAGE / FRONT TITLE] — Main Deed Clauses Begin On Page 2";
              display: block;
              font-family: system-ui, -apple-system, sans-serif;
              font-size: 11px;
              font-weight: 700;
              color: #4338ca;
              text-align: center;
              margin-top: 20px;
              background: #eef2ff;
              padding: 4px 14px;
              border: 1px solid #c7d2fe;
              border-radius: 6px;
              width: fit-content;
              margin-left: auto;
              margin-right: auto;
            }
          `}</style>
          
          <div dangerouslySetInnerHTML={{ __html: deedHtml }} />
        </div>

      </div>

      {/* Page Break Configuration Modal */}
      {onUpdateFormData && (
        <PageBreakModal
          isOpen={isPageBreakModalOpen}
          onClose={() => setIsPageBreakModalOpen(false)}
          formData={formData}
          onUpdateFormData={onUpdateFormData}
        />
      )}

    </div>
  );
};

