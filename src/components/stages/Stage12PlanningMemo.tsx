import React, { useState } from 'react';
import { EngagementData, PlanningMemo } from '../../types';
import { formatINR, formatCompactINR, computeMateriality } from '../../utils/calculations';
import { FileText, Sparkles, RefreshCw, Loader2, Check, Download, Printer } from 'lucide-react';

interface Stage12Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
  onOpenPrintReport?: () => void;
}

export const Stage12PlanningMemo: React.FC<Stage12Props> = ({
  engagement,
  onChange,
  onOpenPrintReport,
}) => {
  const [activeSection, setActiveSection] = useState<keyof PlanningMemo>('executiveSummary');
  const [aiDrafting, setAiDrafting] = useState(false);

  const memo = engagement.planningMemo;
  const materiality = computeMateriality(engagement.materiality);

  const updateMemo = (key: keyof PlanningMemo, value: string) => {
    onChange({
      ...engagement,
      planningMemo: {
        ...engagement.planningMemo,
        [key]: value,
      },
    });
  };

  const handleCompileFromWorkpapers = () => {
    const significantRisks = engagement.controlRiskRegister
      .filter((r) => r.finalRating === 'Significant')
      .map((r) => r.lineItemOrProcess || r.lineItemOrRisk)
      .filter(Boolean)
      .join(', ');

    const itSysList = engagement.informationSystems?.systems?.map((s) => `${s.name || s.systemName} (${s.type || s.criticality})`)
      || engagement.itSystems?.map((s) => `${s.systemName} (${s.criticality})`)
      || [];

    const fraudObj = engagement.fraudRisks || (engagement as any).fraudRisk || {};
    const revPres = fraudObj.revenuePresumption;
    const isRebutted = typeof revPres === 'object' ? Boolean(revPres?.rebutted) : revPres === 'Rebutted';
    const revRat = typeof revPres === 'object' ? revPres?.rationale : (fraudObj.revenueRationale || '');

    const newMemo: PlanningMemo = {
      executiveSummary: `This Audit Planning Memorandum sets out the overall audit strategy, assessed risks of material misstatement, and planned audit procedures for the statutory audit of ${engagement.clientName} for the Financial Year ended ${engagement.financialYear}.\n\nOverall Materiality has been established at ${formatINR(materiality.overallMateriality)} (${formatCompactINR(materiality.overallMateriality)}) based on ${engagement.materiality.omPercent}% of ${engagement.materiality.benchmarkBasis}. Key identified significant risks requiring focused audit response include ${significantRisks || 'revenue recognition and management override of controls'}.`,

      scopeAndObjectives: `The audit is conducted in accordance with Standards on Auditing (SAs) issued by the Institute of Chartered Accountants of India (ICAI) and the provisions of Section 143 of the Companies Act, 2013.\n\nThe principal objective is to obtain reasonable assurance whether the financial statements as a whole are free from material misstatement, whether due to fraud or error, and to issue an independent auditor's report containing our opinion thereon.\n\nPreceding Auditor: ${engagement.precedingAuditor}. Engagement Partner: ${engagement.engagementPartner}.`,

      entityAndRiskAssessment: `Entity Overview:\n${engagement.entityUnderstanding.natureOfBusiness}\n\nInternal Control & IT Environment:\nThe entity operates on ${itSysList.join(', ') || 'integrated ERP systems'}. Control environment was assessed as "${engagement.controlEnvironment.overallConclusion}".\n\nEntity-Level Risks:\n${engagement.entityUnderstanding.entityLevelRisks}`,

      materialityDetermination: `Materiality has been determined in accordance with SA 320 and SA 450:\n\n• Primary Benchmark: ${engagement.materiality.benchmarkBasis} of ${formatINR(engagement.materiality.benchmarkAmount)}\n• Overall Materiality (OM): ${formatINR(materiality.overallMateriality)} (${engagement.materiality.omPercent}%)\n• Performance Materiality (PM): ${formatINR(materiality.performanceMateriality)} (${engagement.materiality.pmPercent}% of OM)\n• Clearly Trivial Threshold (CT): ${formatINR(materiality.clearlyTrivialThreshold)} (${engagement.materiality.clearlyTrivialPercent || engagement.materiality.ctPercent || 5}% of OM)\n\nBasis of Selection:\n${engagement.materiality.rationale}`,

      significantRisksAndFraud: `1. Fraud in Revenue Recognition (SA 240 Para 26):\nStatus: ${!isRebutted ? 'Presumption Applicable (Maintained)' : 'Presumption Rebutted'}.\nRationale: ${revRat || 'Presumed risk of fraud in revenue cut-off and recognition.'}\n\n2. Management Override of Controls (SA 240 Para 31-33):\nNon-rebuttable significant risk. Planned procedures include testing journal entries, retrospective review of estimates, and evaluation of significant unusual transactions.\n\n3. Assessed Significant Risks:\n${significantRisks || 'None identified beyond mandatory fraud presumptions.'}`,

      auditApproachAndStaffing: `Audit Strategy & Fieldwork Timelines:\n• Interim testing of internal controls and walkthroughs: Scheduled for Q3/Q4.\n• Year-end inventory physical verification attendance: Scheduled for 31st March.\n• Year-end substantive procedures and balance confirmations: Scheduled for April/May.\n\nAudit Team Allocation:\n• Engagement Partner: ${engagement.engagementPartner}\n• Audit Senior / Lead: ${engagement.auditSenior}\n• Engagement Quality Control Reviewer: To be appointed under SQC 1.\n\nKey Reports to be Issued:\n• Statutory Independent Auditor's Report under Sec 143\n• Report on Internal Financial Controls over Financial Reporting (IFCoFR)\n• Companies (Auditor's Report) Order (CARO 2020) annexure.`,
    };

    onChange({
      ...engagement,
      planningMemo: newMemo,
    });
  };

  const handleAiDraftSection = async () => {
    setAiDrafting(true);
    try {
      const res = await fetch('/api/gemini/draft-planning-memo', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sectionName: activeSection,
          engagementData: {
            clientName: engagement.clientName,
            financialYear: engagement.financialYear,
            auditType: engagement.auditType,
            materiality,
            controlConclusion: engagement.controlEnvironment.overallConclusion,
            significantRisks: engagement.controlRiskRegister.filter((r) => r.finalRating === 'Significant').map((r) => r.lineItemOrProcess),
            entityUnderstanding: engagement.entityUnderstanding,
            currentText: memo[activeSection],
          },
        }),
      });

      const data = await res.json();
      if (data.draft) {
        updateMemo(activeSection, data.draft);
      }
    } catch (e) {
      console.error('AI draft memo failed', e);
    } finally {
      setAiDrafting(false);
    }
  };

  const sectionsList: Array<{ key: keyof PlanningMemo; title: string }> = [
    { key: 'executiveSummary', title: '1. Executive Summary & Background' },
    { key: 'scopeAndObjectives', title: '2. Scope, Terms & Objectives (SA 210)' },
    { key: 'entityAndRiskAssessment', title: '3. Entity Understanding & Control Evaluation' },
    { key: 'materialityDetermination', title: '4. Materiality & Sampling Thresholds (SA 320)' },
    { key: 'significantRisksAndFraud', title: '5. Significant Risks & Fraud (SA 240 / 315)' },
    { key: 'auditApproachAndStaffing', title: '6. Strategy, Staffing & Deliverables (SA 300)' },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
              Stage 12 • SA 300
            </span>
            <span className="text-xs text-stone-500">Planning an Audit of Financial Statements</span>
          </div>
          <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
            Audit Planning Memorandum (APM)
          </h2>
          <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
            The formal synthesis document detailing the overall audit strategy, key audit matters, materiality levels, and resource deployment for partner review.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
          <button
            type="button"
            onClick={handleCompileFromWorkpapers}
            className="px-3 py-1.5 rounded-lg bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 dark:hover:bg-stone-700 text-stone-800 dark:text-stone-200 text-xs font-medium flex items-center gap-1.5 transition-colors shadow-2xs"
            title="Auto-compile sections using current inputs across Stages 1 through 11"
          >
            <RefreshCw className="w-3.5 h-3.5 text-stone-500" />
            <span>Recompile from Stages</span>
          </button>

          {onOpenPrintReport && (
            <button
              type="button"
              onClick={onOpenPrintReport}
              className="px-3.5 py-1.5 rounded-lg bg-amber-800 hover:bg-amber-900 dark:bg-amber-700 text-white text-xs font-semibold flex items-center gap-1.5 shadow-xs transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Complete Memo</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Workpaper Editor Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Navigation / Sections Selector */}
        <div className="space-y-1 bg-white dark:bg-[#15191f] p-3 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs">
          <p className="text-[11px] font-bold uppercase tracking-wider text-stone-400 px-3 py-1">
            Memorandum Sections
          </p>
          {sectionsList.map((sec) => (
            <button
              key={sec.key}
              onClick={() => setActiveSection(sec.key)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                activeSection === sec.key
                  ? 'bg-amber-800 text-white dark:bg-amber-700 shadow-xs'
                  : 'text-stone-700 dark:text-stone-300 hover:bg-stone-100 dark:hover:bg-stone-800'
              }`}
            >
              {sec.title}
            </button>
          ))}
        </div>

        {/* Section Editor */}
        <div className="md:col-span-2 bg-white dark:bg-[#15191f] p-5 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex flex-col space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              {sectionsList.find((s) => s.key === activeSection)?.title}
            </h3>

            <button
              type="button"
              disabled={aiDrafting}
              onClick={handleAiDraftSection}
              className="px-3 py-1 rounded-md bg-amber-50 hover:bg-amber-100 dark:bg-amber-950/60 dark:hover:bg-amber-900/50 border border-amber-300 dark:border-amber-800 text-amber-900 dark:text-amber-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50 shadow-2xs"
            >
              {aiDrafting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Drafting with Gemini...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Polish Draft</span>
                </>
              )}
            </button>
          </div>

          <textarea
            rows={14}
            value={memo[activeSection]}
            onChange={(e) => updateMemo(activeSection, e.target.value)}
            placeholder="Type or compile memorandum text..."
            className="flex-1 w-full px-3.5 py-3 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 text-xs font-mono leading-relaxed focus:border-amber-700"
          />

          <p className="text-[11px] text-stone-400">
            Tip: Changes made in the editor are saved live to the engagement record and reflected directly in the printable Audit Planning Memorandum.
          </p>
        </div>
      </div>
    </div>
  );
};
