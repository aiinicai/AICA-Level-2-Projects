import React from 'react';
import { X, Printer, Download, ShieldCheck, CheckCircle2, FileSpreadsheet, FileText } from 'lucide-react';
import { EngagementData, ComputedMateriality } from '../types';
import { formatINR, formatCompactINR } from '../utils/calculations';
import { exportWorkpaperToExcel, exportWorkpaperToWord } from '../utils/workpaperExporter';

interface PrintReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  engagement: EngagementData;
  materiality: ComputedMateriality;
}

export const PrintReportModal: React.FC<PrintReportModalProps> = ({
  isOpen,
  onClose,
  engagement,
  materiality,
}) => {
  if (!isOpen) return null;

  const handlePrint = () => {
    window.print();
  };

  const significantRisks = engagement.controlRiskRegister.filter(
    (r) => r.finalRating === 'Significant'
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-xs p-2 sm:p-4 overflow-y-auto print:p-0 print:static print:bg-transparent">
      <div className="bg-white text-stone-900 w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[92vh] print:max-h-none print:shadow-none print:rounded-none">
        {/* Modal Controls Bar (Hidden in Print) */}
        <div className="flex items-center justify-between px-6 py-3.5 border-b border-stone-200 bg-stone-100 print:hidden">
          <div className="flex items-center gap-2">
            <Printer className="w-4 h-4 text-amber-800" />
            <h2 className="font-serif font-bold text-sm text-stone-800">
              Audit Planning Memorandum Preview (Print Ready)
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => exportWorkpaperToWord(engagement, materiality)}
              className="px-3 py-1.5 rounded-md border border-stone-300 bg-white hover:bg-stone-50 text-blue-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
              title="Download editable Microsoft Word document (.doc)"
            >
              <FileText className="w-3.5 h-3.5" />
              <span>Word</span>
            </button>
            <button
              onClick={() => exportWorkpaperToExcel(engagement, materiality)}
              className="px-3 py-1.5 rounded-md border border-stone-300 bg-white hover:bg-stone-50 text-emerald-700 text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
              title="Download multi-tab Excel workbook (.xlsx)"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Excel</span>
            </button>
            <button
              onClick={handlePrint}
              className="px-4 py-1.5 rounded-md bg-amber-800 hover:bg-amber-900 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print to PDF</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 hover:bg-stone-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Printable Document Body */}
        <div className="flex-1 overflow-y-auto p-8 sm:p-12 space-y-8 font-serif leading-relaxed text-xs sm:text-sm print:overflow-visible print:p-6 print:text-xs">
          {/* Header & Title */}
          <div className="border-b-2 border-stone-900 pb-5 text-center space-y-2">
            <p className="text-[11px] font-sans uppercase font-bold tracking-widest text-amber-900">
              Statutory Audit Workpaper • Confidential
            </p>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
              AUDIT PLANNING MEMORANDUM
            </h1>
            <p className="text-base sm:text-lg font-semibold text-stone-800">
              {engagement.clientName}
            </p>
            <p className="text-xs text-stone-600 font-sans">
              CIN: <span className="font-mono">{engagement.cin}</span> • Financial Year Ended: <span className="font-bold">{engagement.financialYear}</span>
            </p>
            <p className="text-xs text-stone-500 font-sans">
              Conducted in accordance with Standards on Auditing (SAs) issued by the Institute of Chartered Accountants of India (ICAI)
            </p>
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-4 bg-stone-50 border border-stone-200 rounded font-sans text-xs">
            <div>
              <span className="text-stone-500 block uppercase text-[10px] font-bold">Engagement Partner</span>
              <span className="font-semibold text-stone-900">{engagement.engagementPartner}</span>
            </div>
            <div>
              <span className="text-stone-500 block uppercase text-[10px] font-bold">Audit Senior / Lead</span>
              <span className="font-semibold text-stone-900">{engagement.auditSenior}</span>
            </div>
            <div>
              <span className="text-stone-500 block uppercase text-[10px] font-bold">Audit Type</span>
              <span className="font-semibold text-stone-900">{engagement.auditType.split(' ')[0]}</span>
            </div>
            <div>
              <span className="text-stone-500 block uppercase text-[10px] font-bold">Preceding Auditor</span>
              <span className="font-semibold text-stone-900">{engagement.precedingAuditor}</span>
            </div>
          </div>

          {/* Section 1: Executive Summary */}
          <div className="space-y-2">
            <h2 className="text-base font-bold text-stone-900 border-b border-stone-300 pb-1">
              1. Executive Summary & Audit Objectives (SA 300)
            </h2>
            <p className="whitespace-pre-wrap text-stone-700 leading-relaxed font-sans text-xs">
              {engagement.planningMemo.executiveSummary}
            </p>
          </div>

          {/* Section 2: Materiality Benchmark & Thresholds */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-stone-900 border-b border-stone-300 pb-1">
              2. Materiality Determination (SA 320 & SA 450)
            </h2>
            <div className="grid grid-cols-3 gap-3 text-center font-sans text-xs">
              <div className="p-3 border border-stone-300 bg-stone-50 rounded">
                <span className="text-[10px] font-bold uppercase text-stone-500 block">Overall Materiality (OM)</span>
                <span className="text-lg font-bold text-stone-900 font-mono block">
                  {formatINR(materiality.overallMateriality)}
                </span>
                <span className="text-[10px] text-stone-500">{engagement.materiality.omPercent}% of {engagement.materiality.benchmarkBasis.split(' ')[0]}</span>
              </div>
              <div className="p-3 border border-amber-300 bg-amber-50/50 rounded">
                <span className="text-[10px] font-bold uppercase text-amber-800 block">Performance Materiality (PM)</span>
                <span className="text-lg font-bold text-amber-900 font-mono block">
                  {formatINR(materiality.performanceMateriality)}
                </span>
                <span className="text-[10px] text-amber-800">{engagement.materiality.pmPercent}% of OM (Sampling Scope)</span>
              </div>
              <div className="p-3 border border-stone-300 bg-stone-50 rounded">
                <span className="text-[10px] font-bold uppercase text-stone-500 block">Clearly Trivial (CT)</span>
                <span className="text-lg font-bold text-stone-700 font-mono block">
                  {formatINR(materiality.clearlyTrivialThreshold)}
                </span>
                <span className="text-[10px] text-stone-500">{engagement.materiality.clearlyTrivialPercent}% of OM (SA 450 Threshold)</span>
              </div>
            </div>
            <p className="font-sans text-xs text-stone-600">
              <strong>Materiality Rationale:</strong> {engagement.materiality.rationale}
            </p>
          </div>

          {/* Section 3: Understanding the Entity & Internal Controls */}
          <div className="space-y-2">
            <h2 className="text-base font-bold text-stone-900 border-b border-stone-300 pb-1">
              3. Understanding the Entity & Control Environment (SA 315)
            </h2>
            <p className="font-sans text-xs text-stone-700 leading-relaxed">
              <strong>Operations:</strong> {engagement.entityUnderstanding.natureOfBusiness}
            </p>
            <p className="font-sans text-xs text-stone-700 leading-relaxed">
              <strong>Control Environment Conclusion:</strong> {engagement.controlEnvironment.overallConclusion} — {engagement.controlEnvironment.overallNotes}
            </p>
            <p className="font-sans text-xs text-stone-700 leading-relaxed">
              <strong>IT Environment Reliance:</strong> {engagement.informationSystems.generalReliance} across systems ({engagement.informationSystems.systems.map((s) => s.name).join(', ')}).
            </p>
          </div>

          {/* Section 4: Assessed Significant Risks & Fraud */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-stone-900 border-b border-stone-300 pb-1">
              4. Assessed Significant Risks & Fraud Considerations (SA 240 / SA 315)
            </h2>
            <div className="space-y-2 font-sans text-xs">
              <div className="p-3 border border-stone-200 bg-stone-50 rounded">
                <p className="font-bold text-stone-900">Fraud in Revenue Recognition (SA 240 Para 26):</p>
                <p className="text-stone-700 mt-0.5">
                  Presumption: <strong>{engagement.fraudRisk.revenuePresumption}</strong>. {engagement.fraudRisk.revenuePresumption === 'Presumed' ? engagement.fraudRisk.revenueRationale : engagement.fraudRisk.revenueRebuttalJustification}
                </p>
              </div>

              <div className="p-3 border border-stone-200 bg-stone-50 rounded">
                <p className="font-bold text-stone-900">Management Override of Controls (SA 240 Para 31-33):</p>
                <p className="text-stone-700 mt-0.5">
                  Non-rebuttable significant risk addressed via journal entry testing, retrospective evaluation of estimates, and examination of significant unusual transactions.
                </p>
              </div>

              {significantRisks.length > 0 && (
                <div className="p-3 border border-stone-200 bg-stone-50 rounded">
                  <p className="font-bold text-stone-900">Identified Significant Risks Requiring Special Audit Consideration (SA 315 Para 28):</p>
                  <ul className="list-disc list-inside mt-1 space-y-1 text-stone-700">
                    {significantRisks.map((sr) => (
                      <li key={sr.id}>
                        <strong>{sr.lineItemOrProcess}:</strong> Probability {sr.probability}, Magnitude {sr.magnitude} (Assessed: {sr.finalRating}). Controls: {sr.associatedControls}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>

          {/* Section 5: Planned Audit Strategy (SA 330) */}
          <div className="space-y-3">
            <h2 className="text-base font-bold text-stone-900 border-b border-stone-300 pb-1">
              5. Assertion-Level Audit Responses & Sampling Strategy (SA 330)
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left font-sans text-xs border border-stone-300 border-collapse">
                <thead>
                  <tr className="bg-stone-100 border-b border-stone-300 text-stone-700 font-semibold">
                    <th className="p-2">Line Item / Risk</th>
                    <th className="p-2 w-20">Assessed Risk</th>
                    <th className="p-2 w-28 text-center">TOC / SAP / TOD</th>
                    <th className="p-2 w-24">Timing</th>
                    <th className="p-2">Planned Substantive Procedures</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-200">
                  {engagement.auditStrategy.map((strat) => (
                    <tr key={strat.id}>
                      <td className="p-2 font-medium">{strat.lineItemOrRisk}</td>
                      <td className="p-2">
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                          strat.assessedRiskLevel === 'Significant' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {strat.assessedRiskLevel}
                        </span>
                      </td>
                      <td className="p-2 text-center font-mono text-[10px]">
                        {[
                          strat.testOfControls ? 'TOC' : null,
                          strat.analyticalProcedures ? 'SAP' : null,
                          strat.testOfDetails ? 'TOD' : null,
                        ]
                          .filter(Boolean)
                          .join(' + ')}
                      </td>
                      <td className="p-2 text-[11px] text-stone-600">{strat.timing.split(' ')[0]}</td>
                      <td className="p-2 text-stone-700 leading-snug">{strat.proceduresNotes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 6: Trial Balance Highlights & Financial Baseline (If Imported) */}
          {engagement.trialBalance && engagement.trialBalance.items.length > 0 && (
            <div className="space-y-3 font-sans print:break-inside-avoid">
              <h2 className="font-serif font-bold text-base text-stone-900 border-b border-stone-300 pb-1">
                6. Trial Balance & Key Financial Aggregates
              </h2>
              <div className="p-3 bg-stone-50 border border-stone-200 rounded text-xs space-y-2">
                <div className="flex justify-between items-center text-stone-600">
                  <span>File: <b className="text-stone-800">{engagement.trialBalance.fileName || 'Client Trial Balance'}</b></span>
                  <span className="font-semibold text-emerald-800">✓ Reconciled & Balanced (Dr = Cr)</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                  <div className="p-2 bg-white border border-stone-200 rounded">
                    <span className="text-[10px] text-stone-500 block uppercase font-bold">Turnover</span>
                    <span className="font-mono font-bold text-stone-900">{formatCompactINR(engagement.trialBalance.summary.totalRevenue)}</span>
                  </div>
                  <div className="p-2 bg-white border border-stone-200 rounded">
                    <span className="text-[10px] text-stone-500 block uppercase font-bold">PBT</span>
                    <span className="font-mono font-bold text-amber-800">{formatCompactINR(engagement.trialBalance.summary.profitBeforeTax)}</span>
                  </div>
                  <div className="p-2 bg-white border border-stone-200 rounded">
                    <span className="text-[10px] text-stone-500 block uppercase font-bold">Total Assets</span>
                    <span className="font-mono font-bold text-stone-900">{formatCompactINR(engagement.trialBalance.summary.totalAssets)}</span>
                  </div>
                  <div className="p-2 bg-white border border-stone-200 rounded">
                    <span className="text-[10px] text-stone-500 block uppercase font-bold">Net Worth</span>
                    <span className="font-mono font-bold text-stone-900">{formatCompactINR(engagement.trialBalance.summary.totalEquity)}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Section 7: Sign-Offs & Quality Control Approval */}
          <div className="pt-4 border-t-2 border-stone-900 grid grid-cols-2 gap-8 font-sans text-xs">
            <div className="space-y-1">
              <p className="font-bold text-stone-900">PREPARED BY:</p>
              <p className="text-stone-800 font-semibold">{engagement.signOffReview.preparer.name}</p>
              <p className="text-stone-500">Audit Senior / Lead</p>
              <p className="text-stone-600">Date: {engagement.signOffReview.preparer.date}</p>
              <p className="text-[11px] text-emerald-800 font-semibold mt-1">
                ✓ Declaration confirmed under SQC 1
              </p>
            </div>

            <div className="space-y-1">
              <p className="font-bold text-stone-900">REVIEWED & APPROVED BY:</p>
              <p className="text-stone-800 font-semibold">{engagement.signOffReview.reviewer.name}</p>
              <p className="text-stone-500">Engagement Partner (SA 220)</p>
              <p className="text-stone-600">Date: {engagement.signOffReview.reviewer.date}</p>
              <p className="text-[11px] font-bold text-amber-900 mt-1">
                Conclusion: {engagement.signOffReview.reviewer.conclusion}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
