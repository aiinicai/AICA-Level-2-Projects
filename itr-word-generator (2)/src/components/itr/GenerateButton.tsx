/**
 * GenerateButton & Export Controller - ITR Computation Studio
 * Multi-format export (Word .docx, PDF .pdf, or Both),
 * verification confirmation, and professional CA output formatting.
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
  Files,
  FileType,
} from 'lucide-react';
import { CompleteITRData } from '../../itr-types';
import { downloadITRDocx } from '../../utils/itrDocxGenerator';
import { downloadITRPdf } from '../../utils/itrPdfGenerator';
import { formatIndianCurrency, numberToIndianRupeesWords } from '../../utils/numberParsing';

export type ExportFormat = 'docx' | 'pdf' | 'both';

interface GenerateButtonProps {
  data: CompleteITRData;
  disabled?: boolean;
  onDataChange?: (updated: CompleteITRData) => void;
}

export const GenerateButton: React.FC<GenerateButtonProps> = ({ data, disabled = false, onDataChange }) => {
  const [exportFormat, setExportFormat] = useState<ExportFormat>('both');
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);
  const [userConfirmed, setUserConfirmed] = useState(true);
  const [copied, setCopied] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cleanName = (data.personalInfo.name || 'Assessee').replace(/[^A-Za-z0-9]/g, '_').slice(0, 25);
  const pan = data.personalInfo.pan || 'PAN';
  const ay = (data.personalInfo.assessmentYear || '2026-27').replace(/[^0-9-]/g, '');
  const docxFileName = `ITR_Computation_${cleanName}_${pan}_AY${ay}.docx`;
  const pdfFileName = `ITR_Computation_${cleanName}_${pan}_AY${ay}.pdf`;

  // Detect any missing critical fields
  const unresolvedFields: string[] = [];
  if (!data.personalInfo.pan || data.personalInfo.pan === 'PAN') unresolvedFields.push('Permanent Account Number (PAN)');
  if (!data.personalInfo.name || data.personalInfo.name === 'Assessee') unresolvedFields.push('Assessee Name');
  if (!data.personalInfo.assessmentYear) unresolvedFields.push('Assessment Year');
  if (data.incomeHeads.grossTotalIncome === 0) unresolvedFields.push('Gross Total Income (GTI)');
  if (data.taxComputation.totalTaxableIncome === 0) unresolvedFields.push('Total Taxable Income');

  const handleGenerate = async (targetFormat: ExportFormat = exportFormat) => {
    try {
      setIsGenerating(true);
      setDownloadSuccess(null);
      setErrorMessage(null);

      if (targetFormat === 'docx') {
        await downloadITRDocx(data, docxFileName);
        setDownloadSuccess('Word Document (.docx) downloaded successfully!');
      } else if (targetFormat === 'pdf') {
        await downloadITRPdf(data, pdfFileName);
        setDownloadSuccess('PDF Document (.pdf) downloaded successfully!');
      } else {
        // Both: Download DOCX and PDF in sequence
        await downloadITRDocx(data, docxFileName);
        // Brief 400ms pause to ensure smooth browser file downloads
        await new Promise((resolve) => setTimeout(resolve, 400));
        await downloadITRPdf(data, pdfFileName);
        setDownloadSuccess('Both Word (.docx) and PDF (.pdf) downloaded successfully!');
      }

      setTimeout(() => setDownloadSuccess(null), 5000);
    } catch (err: any) {
      console.error('Error generating documents:', err);
      setErrorMessage(err?.message || 'Failed to generate computation document. Please try again.');
    } finally {
      setIsGenerating(false);
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

  const updateStyleConfig = (key: string, val: any) => {
    if (!onDataChange) return;
    onDataChange({
      ...data,
      styleConfig: {
        ...data.styleConfig,
        [key]: val,
      },
    });
  };

  const updateCAConfig = (key: string, val: any) => {
    if (!onDataChange) return;
    onDataChange({
      ...data,
      caDetails: {
        ...data.caDetails,
        [key]: val,
      },
    });
  };

  const isBankIncluded = data.styleConfig?.includeBankDetails ?? true;
  const isCAIncluded = data.caDetails?.includeCASection ?? false;

  return (
    <div id="computation-export-panel" className="bg-white rounded-lg border border-slate-200 p-4 sm:p-5 shadow-sm space-y-4">
      {/* Top preferences and export format selector */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-3">
        {/* Output Format Selector */}
        <div className="space-y-1">
          <label className="text-xs font-semibold text-slate-700 block">Export Format:</label>
          <div className="inline-flex p-0.5 bg-slate-100 rounded-lg border border-slate-200 text-xs">
            <button
              type="button"
              id="export-format-both-btn"
              onClick={() => setExportFormat('both')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                exportFormat === 'both'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <Files className="w-3.5 h-3.5" />
              <span>Both (DOCX + PDF)</span>
            </button>
            <button
              type="button"
              id="export-format-pdf-btn"
              onClick={() => setExportFormat('pdf')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                exportFormat === 'pdf'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <FileType className="w-3.5 h-3.5" />
              <span>PDF (.pdf)</span>
            </button>
            <button
              type="button"
              id="export-format-docx-btn"
              onClick={() => setExportFormat('docx')}
              className={`px-3 py-1.5 rounded-md font-medium transition-all flex items-center gap-1.5 cursor-pointer ${
                exportFormat === 'docx'
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/60'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Word (.docx)</span>
            </button>
          </div>
        </div>

        {/* Quick Actions & Toggles */}
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isBankIncluded}
              onChange={(e) => updateStyleConfig('includeBankDetails', e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-slate-600 font-medium">Include Bank Details</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={isCAIncluded}
              onChange={(e) => updateCAConfig('includeCASection', e.target.checked)}
              className="rounded border-slate-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="text-xs text-slate-600 font-medium">Include Audit Trail & CA UDIN</span>
          </label>

          <button
            type="button"
            onClick={handleCopySummary}
            className="text-xs text-slate-600 hover:text-slate-900 border border-slate-300 px-2.5 py-1.5 rounded bg-white hover:bg-slate-50 flex items-center gap-1 cursor-pointer transition-colors shadow-2xs"
          >
            {copied ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied Summary' : 'Copy Summary'}</span>
          </button>
        </div>
      </div>

      {/* Target Filename Preview & Accurate Privacy Notice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between bg-slate-50 border border-slate-200 rounded-md px-3 py-2 text-xs gap-2">
        <div className="flex items-center gap-2 text-slate-600">
          <FileText className="w-4 h-4 text-blue-600 shrink-0" />
          <span className="truncate">
            Export target: <strong className="font-mono text-slate-800">{exportFormat === 'both' ? `${docxFileName} & ${pdfFileName}` : exportFormat === 'pdf' ? pdfFileName : docxFileName}</strong>
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px] text-slate-600 font-medium shrink-0">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
          <span>Local parsing available • AI extraction optional</span>
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

      {/* Main Action Buttons Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 pt-1">
        {/* Primary Selected Export Button */}
        <button
          type="button"
          id="generate-computation-main-btn"
          disabled={disabled || isGenerating || !userConfirmed}
          onClick={() => handleGenerate(exportFormat)}
          className="sm:col-span-8 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 sm:py-4 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed uppercase tracking-wider text-xs sm:text-sm"
        >
          {isGenerating ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              <span>GENERATING COMPUTATION DOCUMENT...</span>
            </>
          ) : downloadSuccess ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-emerald-300" />
              <span>{downloadSuccess}</span>
            </>
          ) : (
            <>
              <Download className="h-5 w-5" />
              <span>
                {exportFormat === 'both'
                  ? 'GENERATE COMPUTATION (WORD & PDF)'
                  : exportFormat === 'pdf'
                  ? 'GENERATE COMPUTATION (PDF)'
                  : 'GENERATE COMPUTATION (WORD)'}
              </span>
            </>
          )}
        </button>

        {/* Direct Quick PDF Button */}
        <button
          type="button"
          id="quick-download-pdf-btn"
          disabled={disabled || isGenerating || !userConfirmed}
          onClick={() => handleGenerate('pdf')}
          className="sm:col-span-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 sm:py-3.5 rounded-xl border border-slate-700 flex flex-col items-center justify-center text-xs transition-colors cursor-pointer disabled:opacity-50"
          title="Download single PDF computation"
        >
          <span className="font-bold flex items-center gap-1">
            <FileType className="w-3.5 h-3.5 text-red-400" /> PDF (.pdf)
          </span>
          <span className="text-[10px] text-slate-300">Direct Download</span>
        </button>

        {/* Direct Quick Word Button */}
        <button
          type="button"
          id="quick-download-docx-btn"
          disabled={disabled || isGenerating || !userConfirmed}
          onClick={() => handleGenerate('docx')}
          className="sm:col-span-2 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 sm:py-3.5 rounded-xl border border-slate-700 flex flex-col items-center justify-center text-xs transition-colors cursor-pointer disabled:opacity-50"
          title="Download single Word (.docx) computation"
        >
          <span className="font-bold flex items-center gap-1">
            <FileText className="w-3.5 h-3.5 text-blue-400" /> Word (.docx)
          </span>
          <span className="text-[10px] text-slate-300">Direct Download</span>
        </button>
      </div>

      {/* Error display if any */}
      {errorMessage && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center justify-between">
          <span>{errorMessage}</span>
          <button
            type="button"
            onClick={() => handleGenerate(exportFormat)}
            className="underline font-bold hover:text-red-900 cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
};
