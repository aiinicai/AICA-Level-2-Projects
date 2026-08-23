/**
 * GenerateButton Component - High Density Design Theme
 * Action panel with currency auto-formatting, audit trail flags,
 * Word doc (.docx) and PDF (.pdf) output options, and primary export buttons.
 */

import React, { useState } from 'react';
import {
  Download,
  Loader2,
  CheckCircle2,
  Copy,
  FileCheck,
  AlertTriangle,
  ShieldCheck,
  FileText,
} from 'lucide-react';
import { CompleteITRData } from '../../itr-types';
import { downloadITRDocx } from '../../utils/itrDocxGenerator';
import { downloadITRPdf } from '../../utils/itrPdfGenerator';
import { formatIndianCurrency, numberToIndianRupeesWords } from '../../utils/numberParsing';

interface GenerateButtonProps {
  data: CompleteITRData;
  disabled?: boolean;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({ data, disabled = false }) => {
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [downloadPdfSuccess, setDownloadPdfSuccess] = useState(false);
  const [autoFormatCurrency, setAutoFormatCurrency] = useState(true);
  const [includeAuditTrail, setIncludeAuditTrail] = useState(true);
  const [userConfirmed, setUserConfirmed] = useState(true);
  const [copied, setCopied] = useState(false);
  const [directDownloadUrl, setDirectDownloadUrl] = useState<string | null>(null);
  const [directFileName, setDirectFileName] = useState<string>('ITR_Computation.docx');
  const [directPdfDownloadUrl, setDirectPdfDownloadUrl] = useState<string | null>(null);
  const [directPdfFileName, setDirectPdfFileName] = useState<string>('ITR_Computation.pdf');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [pdfErrorMessage, setPdfErrorMessage] = useState<string | null>(null);

  const cleanName = (data.personalInfo.name || 'Assessee').replace(/[^A-Za-z0-9]/g, '_').slice(0, 25);
  const pan = data.personalInfo.pan || 'PAN';
  const ay = (data.personalInfo.assessmentYear || '2026-27').replace(/[^0-9-]/g, '');
  const calculatedFileName = `ITR_Computation_${cleanName}_${pan}_AY${ay}.docx`;
  const calculatedPdfFileName = `ITR_Computation_${cleanName}_${pan}_AY${ay}.pdf`;

  // Detect any missing critical fields
  const unresolvedFields: string[] = [];
  if (!data.personalInfo.pan || data.personalInfo.pan === 'PAN') unresolvedFields.push('Permanent Account Number (PAN)');
  if (!data.personalInfo.name || data.personalInfo.name === 'Assessee') unresolvedFields.push('Assessee Name');
  if (!data.personalInfo.assessmentYear) unresolvedFields.push('Assessment Year');
  if (data.incomeHeads.grossTotalIncome === 0) unresolvedFields.push('Gross Total Income (GTI)');
  if (data.taxComputation.totalTaxableIncome === 0) unresolvedFields.push('Total Taxable Income');

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      setDownloadSuccess(false);
      setErrorMessage(null);

      setDirectFileName(calculatedFileName);

      const blob = await downloadITRDocx(data, calculatedFileName);

      if (typeof window !== 'undefined' && window.URL && window.URL.createObjectURL) {
        const url = window.URL.createObjectURL(blob);
        setDirectDownloadUrl(url);
      }

      setDownloadSuccess(true);
      setTimeout(() => setDownloadSuccess(false), 5000);
    } catch (err: any) {
      console.error('Error generating Word document:', err);
      setErrorMessage(err?.message || 'Failed to generate Word document. Please try again.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGeneratePdf = async () => {
    try {
      setIsGeneratingPdf(true);
      setDownloadPdfSuccess(false);
      setPdfErrorMessage(null);

      setDirectPdfFileName(calculatedPdfFileName);

      const blob = await downloadITRPdf(data, calculatedPdfFileName);

      if (typeof window !== 'undefined' && window.URL && window.URL.createObjectURL) {
        const url = window.URL.createObjectURL(blob);
        setDirectPdfDownloadUrl(url);
      }

      setDownloadPdfSuccess(true);
      setTimeout(() => setDownloadPdfSuccess(false), 5000);
    } catch (err: any) {
      console.error('Error generating PDF document:', err);
      setPdfErrorMessage('PDF generation failed. Please try again.');
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const handleCopySummary = () => {
    const p = data.personalInfo;
    const inc = data.incomeHeads;
    const tax = data.taxComputation;
    const paid = data.taxesPaid;

    const summary = `--- INCOME TAX COMPUTATION SUMMARY ---
Assessee Name: ${p.name}
PAN: ${p.pan}
Assessment Year: ${p.assessmentYear} (FY: ${p.financialYear})
Form Type: ${p.formType} | Regime: ${p.taxRegime}

Gross Total Income: ${formatIndianCurrency(inc.grossTotalIncome)}
Total Taxable Income: ${formatIndianCurrency(tax.totalTaxableIncome)} (${numberToIndianRupeesWords(tax.totalTaxableIncome)})
${paid.refundDue > 0 ? `Net Refund Due: ${formatIndianCurrency(paid.refundDue)}` : `Balance Tax Payable: ${formatIndianCurrency(paid.taxPayable)}`}
---------------------------------------`;

    navigator.clipboard.writeText(summary);
    setCopied(true);
    setTimeout(() => setCopied(false), 3000);
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 shadow-sm space-y-4">
      {/* Top preferences bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={autoFormatCurrency}
              onChange={(e) => setAutoFormatCurrency(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-slate-600 font-medium">Auto-format currency (₹)</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeAuditTrail}
              onChange={(e) => setIncludeAuditTrail(e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-slate-600 font-medium">Include Audit Trail & CA UDIN</span>
          </label>
        </div>

        <div className="flex items-center justify-between sm:justify-end gap-3">
          <div className="text-right">
            <span className="text-[10px] uppercase text-slate-400 block">Output Formats</span>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded shadow-2xs">
                Word (.docx)
              </span>
              <span className="text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded shadow-2xs">
                PDF (.pdf)
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCopySummary}
            className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 px-2.5 py-1 rounded bg-white hover:bg-slate-50 flex items-center gap-1"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Target Filename Preview */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-xs">
        <div className="flex flex-wrap items-center gap-3 text-slate-600">
          <div className="flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-blue-600" />
            <span>Word: <strong className="font-mono text-slate-800">{calculatedFileName}</strong></span>
          </div>
          <span className="text-slate-300 hidden sm:inline">•</span>
          <div className="flex items-center gap-1.5">
            <FileText className="w-4 h-4 text-red-600" />
            <span>PDF: <strong className="font-mono text-slate-800">{calculatedPdfFileName}</strong></span>
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-emerald-700 font-medium whitespace-nowrap">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>100% In-Browser Privacy</span>
        </div>
      </div>

      {/* Unresolved fields warning checklist */}
      {unresolvedFields.length > 0 && (
        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs space-y-1">
          <div className="flex items-center gap-1.5 font-bold text-amber-800">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0" />
            <span>Review Recommended: The following details may need confirmation</span>
          </div>
          <ul className="list-disc list-inside pl-1 text-[11px] text-amber-800">
            {unresolvedFields.map((field) => (
              <li key={field}>{field}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Confirmation Checkbox */}
      <label className="flex items-start sm:items-center gap-2 cursor-pointer pt-1">
        <input
          type="checkbox"
          checked={userConfirmed}
          onChange={(e) => setUserConfirmed(e.target.checked)}
          className="mt-0.5 sm:mt-0 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
        />
        <span className="text-xs text-slate-700">
          I have reviewed the tax figures above and confirm they represent the assessee's computation.
        </span>
      </label>

      {/* Two Clearly Separate Export Buttons: Download Word (.docx) and Download PDF (.pdf) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
        {/* Word (.docx) Download Button */}
        <button
          type="button"
          id="generate-word-document-main-btn"
          disabled={disabled || isGenerating || !userConfirmed}
          onClick={handleGenerate}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 sm:py-4 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs sm:text-sm"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>GENERATING WORD (.DOCX)...</span>
            </>
          ) : downloadSuccess ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
              <span>WORD (.DOCX) DOWNLOADED!</span>
            </>
          ) : (
            <>
              <Download className="h-5 w-5" />
              <span>DOWNLOAD WORD (.DOCX)</span>
            </>
          )}
        </button>

        {/* PDF (.pdf) Download Button */}
        <button
          type="button"
          id="generate-pdf-document-main-btn"
          disabled={disabled || isGeneratingPdf || !userConfirmed}
          onClick={handleGeneratePdf}
          className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold py-3.5 sm:py-4 rounded-xl shadow-lg shadow-slate-900/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs sm:text-sm"
        >
          {isGeneratingPdf ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>GENERATING PDF (.PDF)...</span>
            </>
          ) : downloadPdfSuccess ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
              <span>PDF (.PDF) DOWNLOADED!</span>
            </>
          ) : (
            <>
              <Download className="h-5 w-5 text-red-400" />
              <span>DOWNLOAD PDF (.PDF)</span>
            </>
          )}
        </button>
      </div>

      {/* Error display if Word fails */}
      {errorMessage && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center justify-between">
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={handleGenerate}
            className="underline font-bold hover:text-red-900"
          >
            Retry Word
          </button>
        </div>
      )}

      {/* Error display if PDF fails (isolated error handling) */}
      {pdfErrorMessage && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center justify-between">
          <span>{pdfErrorMessage}</span>
          <button
            type="button"
            onClick={handleGeneratePdf}
            className="underline font-bold hover:text-red-900"
          >
            Retry PDF
          </button>
        </div>
      )}

      {/* Fallback direct download link for Word if browser blocked automatic download */}
      {directDownloadUrl && (
        <div className="p-3 bg-blue-50 border border-blue-200 text-blue-900 text-xs rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-blue-600 flex-shrink-0" />
            <span>Word file ready: <strong>{directFileName}</strong></span>
          </div>
          <a
            href={directDownloadUrl}
            download={directFileName}
            className="px-3 py-1.5 bg-blue-700 hover:bg-blue-800 text-white rounded font-semibold text-xs transition-colors"
          >
            Click to Download .docx
          </a>
        </div>
      )}

      {/* Fallback direct download link for PDF if browser blocked automatic download */}
      {directPdfDownloadUrl && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-900 text-xs rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>PDF file ready: <strong>{directPdfFileName}</strong></span>
          </div>
          <a
            href={directPdfDownloadUrl}
            download={directPdfFileName}
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded font-semibold text-xs transition-colors"
          >
            Click to Download .pdf
          </a>
        </div>
      )}
    </div>
  );
};

