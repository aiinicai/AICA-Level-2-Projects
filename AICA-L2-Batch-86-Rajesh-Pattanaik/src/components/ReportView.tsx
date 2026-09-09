import React, { useState } from 'react';
import { VerificationReport, ClaimStatus } from '../types';
import { generateVerificationPdf } from '../utils/pdfExport';
import {
  ShieldCheck,
  AlertTriangle,
  Copy,
  Printer,
  Check,
  ArrowUp,
  Download,
  FileDown,
  Scale,
  BookOpen,
  FileCheck2,
  AlertOctagon,
  Sparkles,
  ClipboardList,
  Gavel,
  ShieldAlert,
  HelpCircle,
  Layers,
  FileSpreadsheet,
  CheckCircle2
} from 'lucide-react';

interface ReportViewProps {
  report: VerificationReport;
  onReset?: () => void;
}

export const ReportView: React.FC<ReportViewProps> = ({ report }) => {
  const [copied, setCopied] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const [pdfDownloaded, setPdfDownloaded] = useState(false);

  const handleCopySummary = () => {
    const text = `CA VerifyAI — Professional Verification & Missed-Issue Report
Case Date: ${new Date(report.verificationTimestamp).toLocaleString()}
Overall Status: ${report.overallStatus}
Source-Supported Reliability Score: ${report.verificationScore}/100
Source Reliability: ${report.sourceReliability}

Executive Verdict:
${report.executiveVerdict}

${report.scoreExplanation ? `Score Explanation: ${report.scoreExplanation}\n` : ''}${
      report.limitedVerificationNotice ? `Notice: ${report.limitedVerificationNotice}\n` : ''
    }
Key Highlights:
- Supported Claims: ${report.supportedClaims?.length || 0}
- Claims Requiring Verification: ${report.questionableClaims?.length || 0}
- Potential Errors / Contradictions: ${report.potentialErrors?.length || 0}
- Missed Issues / Omissions: ${report.missedIssues?.length || 0}

Disclaimer: ${report.professionalRelianceWarning}
Attribution: Developed by CA Rajesh Kumar Pattanaik, Bhubaneswar, Odisha (AICA Level 2 Capstone)`;

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleDownloadPdf = () => {
    setIsGeneratingPdf(true);
    try {
      generateVerificationPdf(report);
      setPdfDownloaded(true);
      setTimeout(() => setPdfDownloaded(false), 3000);
    } catch (err) {
      console.error('Failed to generate PDF:', err);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const scrollToTop = () => {
    const el = document.getElementById('verification-report-section');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const renderClaimStatusBadge = (status: ClaimStatus | string) => {
    switch (status) {
      case 'SUPPORTED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 shadow-2xs">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-700 shrink-0" />
            SUBSTANTIATED & VERIFIED
          </span>
        );
      case 'REQUIRES VERIFICATION':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-amber-100 text-amber-950 border border-amber-300 shadow-2xs">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-700 shrink-0" />
            DUE DILIGENCE REQUIRED
          </span>
        );
      case 'POTENTIAL ERROR':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-rose-100 text-rose-950 border border-rose-300 shadow-2xs">
            <AlertOctagon className="w-3.5 h-3.5 text-rose-700 shrink-0" />
            CRITICAL STATUTORY MISSTATEMENT
          </span>
        );
      case 'NOT ESTABLISHED BY SUPPLIED SOURCES':
      case 'NOT ESTABLISHED':
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-bold bg-slate-100 text-slate-900 border border-slate-300 shadow-2xs">
            <HelpCircle className="w-3.5 h-3.5 text-slate-600 shrink-0" />
            UNCONFIRMED BY SOURCES
          </span>
        );
    }
  };

  return (
    <section
      id="verification-report-section"
      className="bg-white rounded-xl shadow-xs border border-slate-200 flex flex-col overflow-hidden print:border-none print:shadow-none transition-all"
    >
      {/* NO-SOURCE LIMITED VERIFICATION BANNER */}
      {report.isLimitedVerification && (
        <div className="bg-amber-500 text-slate-950 px-4 py-3 border-b border-amber-600 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-slate-950 shrink-0 mt-0.5" />
          <div className="text-xs leading-relaxed">
            <strong className="font-bold text-sm block">Statutory Notice: Limited Verification (No Primary Source Material Supplied)</strong>
            <span>
              {report.limitedVerificationNotice ||
                'No authoritative statutory reference material was supplied. The analysis below is an AI-assisted risk and completeness review and requires independent verification against current official gazettes, Acts, and judicial rulings.'}
            </span>
          </div>
        </div>
      )}

      {/* ========================================================
          FORMAL CHARTERED ACCOUNTANT FIRM LETTERHEAD & TOP BAR
      ======================================================== */}
      <div className="p-4 sm:p-5 border-b border-slate-200 bg-slate-900 text-white flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-amber-500 text-slate-950">
              MEMO #{new Date(report.verificationTimestamp).getFullYear()}-
              {(new Date(report.verificationTimestamp).getTime() % 1000)
                .toString()
                .padStart(3, '0')}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
              Source: {report.sourceReliability}
            </span>
            <span className="text-[11px] text-slate-400">
              {new Date(report.verificationTimestamp).toLocaleDateString('en-GB', {
                day: '2-digit',
                month: 'short',
                year: 'numeric'
              })} | {new Date(report.verificationTimestamp).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit'
              })} IST
            </span>
          </div>

          <div className="text-[11px] font-bold tracking-wider uppercase text-amber-400">
            CA Rajesh Kumar Pattanaik & Associates · Chartered Accountants
          </div>
          <h2 className="text-lg sm:text-xl font-bold text-white tracking-tight mt-0.5">
            Statutory Verification & Cross-Domain Regulatory Audit Memorandum
          </h2>
          <p className="text-xs text-slate-300 mt-0.5">
            ICAI Due Diligence Standards · Authoritative Act-level corroboration, latent omission audit & penalty schedule.
          </p>
        </div>

        {/* PRIMARY ACTION BUTTONS */}
        <div className="flex items-center gap-2 flex-wrap w-full md:w-auto justify-start md:justify-end no-print">
          {/* READY-MADE DOWNLOADABLE PDF BUTTON */}
          <button
            type="button"
            onClick={handleDownloadPdf}
            disabled={isGeneratingPdf}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold text-xs shadow-sm transition-all cursor-pointer disabled:opacity-75 disabled:cursor-not-allowed"
            title="Download publication-quality official CA Audit Memorandum PDF"
          >
            {pdfDownloaded ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>PDF Downloaded!</span>
              </>
            ) : isGeneratingPdf ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Generating CA Memorandum...</span>
              </>
            ) : (
              <>
                <FileDown className="w-4 h-4 text-white shrink-0" />
                <div className="text-left">
                  <span className="block leading-none font-bold">Download Official PDF</span>
                  <span className="text-[9px] font-normal text-emerald-100 leading-none">
                    CA Firm Audit Memorandum
                  </span>
                </div>
              </>
            )}
          </button>

          {/* PRINT BUTTON */}
          <button
            type="button"
            onClick={handlePrint}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors cursor-pointer"
            title="Print or save via browser"
          >
            <Printer className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Print / Save</span>
          </button>

          {/* COPY SUMMARY BUTTON */}
          <button
            type="button"
            onClick={handleCopySummary}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-colors cursor-pointer"
            title="Copy Executive Summary to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Copy Memo</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ========================================================
          SCORE & STATISTICAL INDICATORS BAR
      ======================================================== */}
      <div className="p-4 bg-slate-50 border-b border-slate-200 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
        {/* Metric indicators */}
        <div className="grid grid-cols-3 gap-3 text-center sm:text-left flex-1">
          <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">
              Source Support
            </span>
            <div
              className={`text-sm font-bold mt-0.5 ${
                report.scoreBreakdown?.sourceSupport === 'High'
                  ? 'text-emerald-700'
                  : report.scoreBreakdown?.sourceSupport === 'Moderate'
                  ? 'text-amber-600'
                  : 'text-rose-600'
              }`}
            >
              {report.scoreBreakdown?.sourceSupport || 'Moderate'}
            </div>
          </div>

          <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">
              Completeness
            </span>
            <div
              className={`text-sm font-bold mt-0.5 ${
                report.scoreBreakdown?.completeness === 'Comprehensive'
                  ? 'text-emerald-700'
                  : report.scoreBreakdown?.completeness === 'Partial'
                  ? 'text-amber-600'
                  : 'text-rose-600'
              }`}
            >
              {report.scoreBreakdown?.completeness || 'Partial'}
            </div>
          </div>

          <div className="bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs">
            <span className="text-[9px] font-bold uppercase tracking-wider text-slate-400 block">
              Professional Risk
            </span>
            <div
              className={`text-sm font-bold mt-0.5 ${
                report.scoreBreakdown?.professionalRisk === 'Low'
                  ? 'text-emerald-700'
                  : report.scoreBreakdown?.professionalRisk === 'Moderate'
                  ? 'text-amber-600'
                  : 'text-rose-600'
              }`}
            >
              {report.scoreBreakdown?.professionalRisk || 'Elevated'}
            </div>
          </div>
        </div>

        {/* Reliability Score Dial */}
        <div className="flex items-center justify-end gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs shrink-0">
          <div className="text-right">
            <div className="text-[9px] font-bold uppercase tracking-tight text-slate-400">
              Reliability Score
            </div>
            <div className="text-xs font-bold text-slate-900">
              {report.overallStatus}
            </div>
          </div>
          <div
            className={`w-12 h-12 rounded-full border-4 flex items-center justify-center font-black text-sm shrink-0 shadow-xs ${
              report.verificationScore >= 85
                ? 'border-emerald-500 text-emerald-800 bg-emerald-50'
                : report.verificationScore >= 65
                ? 'border-amber-400 text-amber-900 bg-amber-50'
                : report.verificationScore >= 45
                ? 'border-amber-500 text-amber-900 bg-amber-50'
                : 'border-rose-500 text-rose-900 bg-rose-50'
            }`}
          >
            {report.verificationScore}
          </div>
        </div>
      </div>

      {/* ========================================================
          QUICK JUMP NAVIGATION STRIP (NO-PRINT)
      ======================================================== */}
      <div className="bg-slate-100/90 border-b border-slate-200 px-4 py-2 overflow-x-auto no-print">
        <div className="flex items-center gap-1.5 text-[11px] font-semibold text-slate-600 whitespace-nowrap min-w-max">
          <span className="text-[10px] font-bold uppercase text-slate-400 mr-1">Section Jump:</span>
          <button
            type="button"
            onClick={() => scrollToSection('section-verdict')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            1. Verdict
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-facts')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            2. Facts ({report.keyFacts?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-domains')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            3. Domains ({report.applicableDomains?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-supported')}
            className="px-2.5 py-1 rounded bg-white hover:bg-emerald-50 text-emerald-800 border border-emerald-200 transition-colors cursor-pointer font-bold"
          >
            4. Supported ({report.supportedClaims?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-verify')}
            className="px-2.5 py-1 rounded bg-white hover:bg-amber-50 text-amber-900 border border-amber-200 transition-colors cursor-pointer font-bold"
          >
            5. Verify ({report.questionableClaims?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-errors')}
            className="px-2.5 py-1 rounded bg-white hover:bg-rose-50 text-rose-900 border border-rose-200 transition-colors cursor-pointer font-bold"
          >
            6. Errors ({report.potentialErrors?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-missed-issues')}
            className="px-3 py-1 rounded bg-indigo-700 hover:bg-indigo-600 text-white font-bold transition-colors cursor-pointer shadow-2xs"
          >
            7. Missed Issues ({report.missedIssues?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-evidence')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            8. Evidence ({report.sourceEvidenceList?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-penalties')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            9. Penalties ({report.consequencesAndPenalties?.length || 0})
          </button>
          <button
            type="button"
            onClick={() => scrollToSection('section-actions')}
            className="px-2.5 py-1 rounded bg-white hover:bg-slate-200 text-slate-800 border border-slate-200 transition-colors cursor-pointer"
          >
            10. Actions ({report.recommendedProfessionalActions?.length || 0})
          </button>
        </div>
      </div>

      {/* ========================================================
          MAIN REPORT BODY IN 11 NUMBERED SECTIONS
      ======================================================== */}
      <div className="p-4 sm:p-6 space-y-6 text-slate-900">

        {/* 1. 🎯 EXECUTIVE VERDICT */}
        <div id="section-verdict" className="scroll-mt-4 print-break-inside-avoid">
          <div className="flex items-center justify-between bg-amber-500 text-slate-950 px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
            <div className="flex items-center gap-2">
              <span className="w-5 h-5 rounded-full bg-slate-950 text-amber-400 flex items-center justify-center text-[10px]">
                1
              </span>
              <span>Executive Verdict & Reliability Rating</span>
            </div>
            <span className="text-[10px] bg-slate-950 text-white px-2 py-0.5 rounded">
              Score: {report.verificationScore}/100
            </span>
          </div>

          <div className="bg-amber-50/90 border-x border-b border-amber-300 p-4 sm:p-5 rounded-b-lg shadow-2xs">
            <p className="text-sm sm:text-base text-amber-950 leading-relaxed font-bold">
              {report.executiveVerdict}
            </p>
            {report.scoreExplanation && (
              <div className="mt-3 pt-3 border-t border-amber-200/80 text-xs text-amber-900 flex items-start gap-2">
                <span className="font-bold shrink-0">Rationale:</span>
                <span className="italic leading-normal">{report.scoreExplanation}</span>
              </div>
            )}
          </div>
        </div>

        {/* 2. 📌 KEY FACTS IDENTIFIED */}
        {report.keyFacts && report.keyFacts.length > 0 && (
          <div id="section-facts" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-slate-800 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-slate-700 text-white flex items-center justify-center text-[10px]">
                  2
                </span>
                <span>Key Facts Identified & Statutory Triggers</span>
              </div>
              <span className="text-[10px] bg-slate-700 text-slate-200 px-2 py-0.5 rounded">
                {report.keyFacts.length} Facts Found
              </span>
            </div>

            <div className="bg-slate-50 border-x border-b border-slate-200 p-4 rounded-b-lg">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {report.keyFacts.map((kf, idx) => (
                  <div
                    key={kf.id || idx}
                    className="bg-white border border-slate-200 rounded-lg p-3 text-xs flex items-start gap-2.5 shadow-2xs hover:border-slate-300 transition-colors"
                  >
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 font-bold text-[10px] shrink-0 border border-slate-200 uppercase tracking-tight">
                      {kf.category}
                    </span>
                    <span className="text-slate-800 font-medium leading-normal">{kf.fact}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 3. ⚖️ APPLICABLE PROFESSIONAL DOMAINS */}
        {report.applicableDomains && report.applicableDomains.length > 0 && (
          <div id="section-domains" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-slate-900 text-white px-4 py-2.5 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white flex items-center justify-center text-[10px]">
                  3
                </span>
                <span>Applicable Professional Domains & AI Omission Status</span>
              </div>
              <span className="text-[10px] text-slate-300 hidden sm:inline">
                Evaluates statutory cross-domain obligations triggered by client facts
              </span>
            </div>

            <div className="bg-white border-x border-b border-slate-200 p-4 rounded-b-lg space-y-4">
              {report.applicableDomains.map((dom, idx) => {
                const isMissed = dom.aiAddressedStatus === 'Missed / Omitted';
                const isPartial = dom.aiAddressedStatus === 'Partially Addressed';

                return (
                  <div
                    key={idx}
                    className={`rounded-lg border p-3.5 sm:p-4 shadow-2xs transition-all ${
                      isMissed
                        ? 'border-rose-300 bg-rose-50/40'
                        : isPartial
                        ? 'border-amber-300 bg-amber-50/40'
                        : 'border-slate-200 bg-white'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-2.5 py-0.5 rounded bg-slate-900 text-white text-xs font-bold">
                          {dom.domain}
                        </span>
                        <span className="text-xs text-slate-600 font-mono bg-slate-100 px-2 py-0.5 rounded border border-slate-200 font-medium">
                          {dom.relevantProvision}
                        </span>
                      </div>

                      <div>
                        {isMissed ? (
                          <span className="px-2.5 py-1 rounded text-xs font-bold bg-rose-600 text-white shadow-2xs inline-flex items-center gap-1.5 animate-pulse">
                            <span className="w-1.5 h-1.5 rounded-full bg-white"></span>
                            AI Addressed: Missed / Omitted
                          </span>
                        ) : isPartial ? (
                          <span className="px-2.5 py-1 rounded text-xs font-bold bg-amber-100 text-amber-900 border border-amber-300 inline-flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
                            AI Addressed: Partial
                          </span>
                        ) : (
                          <span className="px-2.5 py-1 rounded text-xs font-bold bg-emerald-100 text-emerald-900 border border-emerald-300 inline-flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
                            AI Addressed: Yes
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
                      <div className="bg-white/80 p-3 rounded border border-slate-200/80">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Why It Applies
                        </span>
                        <p className="text-slate-800 leading-relaxed">{dom.whyItApplies}</p>
                      </div>

                      <div className="bg-white/80 p-3 rounded border border-slate-200/80">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Professional Impact
                        </span>
                        <p className="text-slate-800 leading-relaxed">{dom.impact}</p>
                      </div>

                      <div className="bg-white/80 p-3 rounded border border-slate-200/80">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Due Diligence Required
                        </span>
                        <p className="text-slate-900 font-medium leading-relaxed">
                          {dom.verificationRequired}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 4. 🟢 SUPPORTED CLAIMS */}
        {report.supportedClaims && report.supportedClaims.length > 0 && (
          <div id="section-supported" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-emerald-800 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-emerald-700 text-white flex items-center justify-center text-[10px]">
                  4
                </span>
                <span>Supported Claims & Statutory Corroboration</span>
              </div>
              <span className="text-[10px] bg-emerald-700 text-emerald-100 px-2 py-0.5 rounded">
                {report.supportedClaims.length} Verified
              </span>
            </div>

            <div className="bg-emerald-50/50 border-x border-b border-emerald-200 p-4 rounded-b-lg space-y-3">
              {report.supportedClaims.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="bg-white rounded-lg border border-emerald-200 p-3.5 text-xs space-y-2 shadow-2xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-bold text-slate-900 text-xs sm:text-sm">
                      “{item.claim}”
                    </div>
                    {renderClaimStatusBadge(item.status)}
                  </div>

                  {item.sourceEvidence && (
                    <div className="bg-emerald-50/80 p-2.5 rounded border border-emerald-200 text-xs text-emerald-950 font-mono">
                      <strong className="font-sans font-bold text-emerald-900 block mb-0.5">
                        Statutory Evidence Cited:
                      </strong>
                      “{item.sourceEvidence}”
                    </div>
                  )}

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
                    <div>
                      <span className="font-bold text-slate-500 block">Analysis:</span>
                      <span className="text-slate-700 leading-normal">{item.analysis}</span>
                    </div>
                    <div>
                      <span className="font-bold text-slate-500 block">Professional Implication:</span>
                      <span className="text-slate-900 font-medium leading-normal">
                        {item.professionalImplication}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 5. 🟠 CLAIMS REQUIRING VERIFICATION */}
        {report.questionableClaims && report.questionableClaims.length > 0 && (
          <div id="section-verify" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-amber-700 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-amber-800 text-white flex items-center justify-center text-[10px]">
                  5
                </span>
                <span>Claims Requiring Professional Due Diligence</span>
              </div>
              <span className="text-[10px] bg-amber-800 text-amber-100 px-2 py-0.5 rounded">
                {report.questionableClaims.length} Items
              </span>
            </div>

            <div className="bg-amber-50/50 border-x border-b border-amber-200 p-4 rounded-b-lg space-y-3">
              {report.questionableClaims.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="bg-white rounded-lg border border-amber-200 p-3.5 text-xs space-y-2 shadow-2xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-bold text-slate-900 text-xs sm:text-sm">
                      “{item.claim}”
                    </div>
                    {renderClaimStatusBadge(item.status)}
                  </div>

                  <div className="bg-amber-50 p-2.5 rounded border border-amber-200 text-xs text-amber-950">
                    <strong className="font-bold text-amber-900 block mb-0.5">
                      Due Diligence Notice:
                    </strong>
                    {item.missingEvidenceNotice || item.sourceEvidence || 'Not corroborated by authoritative texts.'}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
                    <div>
                      <span className="font-bold text-slate-500 block">Verification Reason:</span>
                      <span className="text-slate-700 leading-normal">{item.analysis}</span>
                    </div>
                    <div>
                      <span className="font-bold text-slate-500 block">Professional Risk:</span>
                      <span className="text-slate-900 font-medium leading-normal">
                        {item.professionalImplication}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 6. 🔴 POTENTIAL ERRORS / STATUTORY MISSTATEMENTS */}
        {report.potentialErrors && report.potentialErrors.length > 0 && (
          <div id="section-errors" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-rose-700 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-rose-800 text-white flex items-center justify-center text-[10px]">
                  6
                </span>
                <span>Potential Errors & Statutory Misstatements</span>
              </div>
              <span className="text-[10px] bg-rose-800 text-white px-2 py-0.5 rounded font-bold">
                {report.potentialErrors.length} Critical Issues
              </span>
            </div>

            <div className="bg-rose-50/50 border-x border-b border-rose-200 p-4 rounded-b-lg space-y-3">
              {report.potentialErrors.map((item, idx) => (
                <div
                  key={item.id || idx}
                  className="bg-white rounded-lg border-2 border-rose-300 p-4 text-xs space-y-2.5 shadow-xs"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="font-bold text-rose-950 text-xs sm:text-sm">
                      “{item.statementInAIAnswer}”
                    </div>
                    <span className="px-2.5 py-1 rounded text-[10px] font-bold bg-rose-600 text-white uppercase tracking-wider shrink-0 shadow-2xs">
                      {item.errorType.replace(/_/g, ' ')}
                    </span>
                  </div>

                  <div className="bg-rose-50 p-3 rounded-lg border border-rose-200 text-xs text-rose-950">
                    <strong className="font-bold text-rose-900 block mb-1">
                      Contradicting Statutory Evidence:
                    </strong>
                    <span className="font-mono leading-relaxed block">
                      “{item.contradictingSourceEvidence}”
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1">
                    <div>
                      <span className="font-bold text-slate-500 block">Technical Analysis:</span>
                      <span className="text-slate-800 leading-normal">{item.analysis}</span>
                    </div>
                    <div>
                      <span className="font-bold text-slate-500 block">Professional Exposure:</span>
                      <span className="text-rose-900 font-bold leading-normal">
                        {item.professionalImplication}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 7. 🔎 MISSED ISSUES & RELATED PROVISIONS (CENTRAL CA DIFFERENTIATOR) */}
        {report.missedIssues && report.missedIssues.length > 0 && (
          <div id="section-missed-issues" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-indigo-900 text-white px-4 py-3 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-indigo-700 text-white flex items-center justify-center text-[10px]">
                  7
                </span>
                <span>Missed Issues & Related Provisions</span>
                <span className="text-[9px] bg-amber-400 text-slate-950 px-2 py-0.5 rounded font-black hidden sm:inline">
                  ★ Core CA Verification Engine
                </span>
              </div>
              <span className="text-[10px] bg-indigo-700 text-indigo-100 px-2 py-0.5 rounded">
                {report.missedIssues.length} Omissions Detected
              </span>
            </div>

            <div className="bg-indigo-50/30 border-x-2 border-b-2 border-indigo-300 p-4 sm:p-5 rounded-b-lg space-y-4">
              <p className="text-xs text-indigo-950/80 font-medium italic">
                “Even if the AI’s primary answer is correct, what professional consequences, reporting requirements and statutory penalties did the AI omit?”
              </p>

              <div className="space-y-4">
                {report.missedIssues.map((miss, idx) => (
                  <div
                    key={miss.id || idx}
                    className="bg-white rounded-xl border border-indigo-200 p-4 text-xs space-y-3 shadow-xs"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-2.5">
                      <div className="flex items-center gap-2">
                        <span className="px-2.5 py-0.5 rounded bg-indigo-100 text-indigo-900 font-bold text-[10px] border border-indigo-200">
                          {miss.domain}
                        </span>
                        <h4 className="font-bold text-slate-900 text-sm">
                          {miss.issueTitle}
                        </h4>
                      </div>
                      <div className="flex items-center gap-1.5 text-xs text-slate-600 font-mono">
                        <span>Provision:</span>
                        <strong className="text-indigo-950 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                          {miss.applicableProvision}
                        </strong>
                      </div>
                    </div>

                    <p className="text-slate-800 leading-relaxed text-xs sm:text-[13px]">
                      {miss.description}
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1 text-xs">
                      <div className="bg-slate-50 p-3 rounded-lg border border-slate-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
                          Why AI Missed It
                        </span>
                        <p className="text-slate-700 leading-relaxed">{miss.whyMissedByAI}</p>
                      </div>

                      <div className="bg-rose-50 p-3 rounded-lg border border-rose-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-rose-800 block mb-1">
                          Consequences & Penalties
                        </span>
                        <p className="text-rose-950 font-bold leading-relaxed">
                          {miss.consequenceOrPenalty}
                        </p>
                      </div>

                      <div className="bg-emerald-50 p-3 rounded-lg border border-emerald-200">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-800 block mb-1">
                          Action Required
                        </span>
                        <p className="text-emerald-950 font-medium leading-relaxed">
                          {miss.actionRequired}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 8. 📚 SOURCE EVIDENCE MATRIX */}
        {report.sourceEvidenceList && report.sourceEvidenceList.length > 0 && (
          <div id="section-evidence" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-slate-800 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-slate-700 text-white flex items-center justify-center text-[10px]">
                  8
                </span>
                <span>Source Evidence Matrix & Claim Audit</span>
              </div>
              <span className="text-[10px] text-slate-300">Claim-by-claim verification</span>
            </div>

            <div className="bg-slate-50 border-x border-b border-slate-200 p-4 rounded-b-lg space-y-3">
              {report.sourceEvidenceList.map((ev, idx) => (
                <div
                  key={ev.id || idx}
                  className="bg-white p-3.5 rounded-lg border border-slate-200 space-y-2 text-xs shadow-2xs"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                    <div className="text-xs font-bold text-slate-800">
                      Claim #{idx + 1}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200">
                        {ev.sourceHierarchy}
                      </span>
                      {renderClaimStatusBadge(ev.status)}
                    </div>
                  </div>

                  <div className="bg-slate-50 p-2.5 rounded border border-slate-200 italic text-slate-900 font-medium">
                    “{ev.aiClaim}”
                  </div>

                  <div className="bg-emerald-50/60 p-2.5 rounded border border-emerald-200 font-mono text-xs text-emerald-950">
                    <strong className="font-sans font-bold text-emerald-900 block mb-0.5">
                      Authoritative Source Excerpt:
                    </strong>
                    {ev.sourceEvidence === 'Not established by the supplied sources.' ? (
                      <span className="text-amber-800 font-sans italic">
                        Not established by the supplied sources.
                      </span>
                    ) : (
                      `“${ev.sourceEvidence}”`
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pt-1 text-slate-700">
                    <div>
                      <strong className="text-slate-900 block">Analysis:</strong>
                      <span className="leading-normal">{ev.analysis}</span>
                    </div>
                    <div>
                      <strong className="text-slate-900 block">Implication:</strong>
                      <span className="leading-normal">{ev.professionalImplication}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 9. ⚠️ CONSEQUENCES / PENALTIES / REPORTING IMPACT */}
        {report.consequencesAndPenalties && report.consequencesAndPenalties.length > 0 && (
          <div id="section-penalties" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-rose-800 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-rose-900 text-white flex items-center justify-center text-[10px]">
                  9
                </span>
                <span>Consequences, Penalties & Reporting Impact</span>
              </div>
              <span className="text-[10px] bg-rose-900 text-white px-2 py-0.5 rounded font-bold">
                {report.consequencesAndPenalties.length} Exposures
              </span>
            </div>

            <div className="bg-rose-50/40 border-x border-b border-rose-200 p-4 rounded-b-lg space-y-3">
              {report.consequencesAndPenalties.map((cp, idx) => (
                <div
                  key={cp.id || idx}
                  className="bg-white rounded-lg border border-rose-200 p-3.5 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-900 text-white">
                        {cp.area}
                      </span>
                      <strong className="text-slate-900 text-xs">{cp.provision}</strong>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          cp.riskLevel === 'Critical'
                            ? 'bg-rose-600 text-white'
                            : 'bg-amber-500 text-white'
                        }`}
                      >
                        {cp.riskLevel} Risk
                      </span>
                    </div>
                    <p className="text-slate-700 leading-normal">{cp.description}</p>
                  </div>
                  <div className="bg-rose-50 p-2.5 rounded border border-rose-200 text-rose-950 text-xs font-bold sm:max-w-xs shrink-0 text-right">
                    {cp.statutoryPenaltyOrImpact}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 10. 🎯 RECOMMENDED PROFESSIONAL ACTIONS */}
        {report.recommendedProfessionalActions && report.recommendedProfessionalActions.length > 0 && (
          <div id="section-actions" className="scroll-mt-4 print-break-inside-avoid">
            <div className="flex items-center justify-between bg-slate-900 text-white px-4 py-2 rounded-t-lg font-bold text-xs uppercase tracking-wider">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-slate-800 text-white flex items-center justify-center text-[10px]">
                  10
                </span>
                <span>Recommended Professional Actions (Action Checklist)</span>
              </div>
              <span className="text-[10px] text-slate-300">Immediate next steps</span>
            </div>

            <div className="bg-slate-50 border-x border-b border-slate-200 p-4 rounded-b-lg">
              <ul className="space-y-2.5 text-xs text-slate-800">
                {report.recommendedProfessionalActions.map((act, idx) => (
                  <li
                    key={idx}
                    className="flex items-start gap-3 bg-white p-3 rounded-lg border border-slate-200 shadow-2xs"
                  >
                    <span className="w-6 h-6 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                      {idx + 1}
                    </span>
                    <span className="leading-relaxed font-medium text-slate-900">{act}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {/* 11. 🛡️ PROFESSIONAL RELIANCE WARNING & CA ATTESTATION */}
        <div className="bg-slate-900 text-white p-6 rounded-xl shadow-sm print-break-inside-avoid border border-slate-800">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-emerald-400">
              <ShieldCheck className="w-4 h-4" />
              <span>11. Professional Reliance Warning & Statutory Disclaimer</span>
            </div>
            <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              ICAI Ethical Conventions
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed mb-6 max-w-4xl">
            {report.professionalRelianceWarning ||
              'CA VerifyAI is an AI-assisted professional verification and risk-identification tool. It does not replace professional judgment, authoritative legal research, or independent verification against current official gazette publications and primary judicial precedents.'}
          </p>

          <div className="border-t border-slate-800 pt-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="text-xs font-bold text-white uppercase tracking-wider">
                CA Rajesh Kumar Pattanaik & Associates
              </div>
              <div className="text-[11px] text-slate-400">
                Chartered Accountants & Registered Tax Auditors · Bhubaneswar, Odisha
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                AICA Level 2 Research Capstone Fellow · Regulatory & Statutory Quality Assurance
              </div>
            </div>

            <div className="bg-slate-800/80 border border-slate-700 px-3 py-2 rounded text-left sm:text-right w-full sm:w-auto">
              <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                Attested Under Due Diligence Norms
              </div>
              <div className="text-[9px] text-slate-400 font-mono mt-0.5">
                Ref: CAVA-{new Date(report.verificationTimestamp).getFullYear()}-{(new Date(report.verificationTimestamp).getTime() % 1000).toString().padStart(3, '0')}
              </div>
            </div>
          </div>
        </div>

        {/* BOTTOM ACTION BAR FOR USER CONVENIENCE (NO-PRINT) */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200 no-print">
          <button
            type="button"
            onClick={scrollToTop}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 text-xs font-semibold transition-colors cursor-pointer"
          >
            <ArrowUp className="w-3.5 h-3.5" />
            <span>Back to Top</span>
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDownloadPdf}
              disabled={isGeneratingPdf}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-white font-bold text-xs shadow-xs transition-all cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Download Ready-Made PDF Report</span>
            </button>
          </div>
        </div>

      </div>
    </section>
  );
};
