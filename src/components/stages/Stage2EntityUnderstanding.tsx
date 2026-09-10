import React from 'react';
import { EngagementData } from '../../types';
import { Building, Sparkles, ShieldAlert, BookOpen } from 'lucide-react';

interface Stage2Props {
  engagement: EngagementData;
  onChange: (updated: EngagementData) => void;
  onOpenKnowledgeBase?: () => void;
}

export const Stage2EntityUnderstanding: React.FC<Stage2Props> = ({
  engagement,
  onChange,
  onOpenKnowledgeBase,
}) => {
  const updateUnderstanding = (key: keyof EngagementData['entityUnderstanding'], value: string) => {
    onChange({
      ...engagement,
      entityUnderstanding: {
        ...engagement.entityUnderstanding,
        [key]: value,
      },
    });
  };

  const sections: Array<{
    key: keyof EngagementData['entityUnderstanding'];
    title: string;
    guidance: string;
    placeholder: string;
    rows: number;
  }> = [
    {
      key: 'natureOfBusiness',
      title: '1. Nature of the Entity (Operations & Revenue Streams)',
      guidance: 'Core products/services, manufacturing/trading facilities, domestic vs export revenue split, key distribution channels, and seasonal patterns.',
      placeholder: 'Describe the operating facilities, capacity, primary product lines, market presence, and key customers...',
      rows: 4,
    },
    {
      key: 'ownershipAndGovernance',
      title: '2. Ownership, Capital Structure & Governance',
      guidance: 'Shareholding pattern, promoter holding, board composition, independent directors, and frequency of Audit Committee meetings.',
      placeholder: 'Document shareholding breakdown, board structure, key executive leadership, and oversight committees...',
      rows: 3,
    },
    {
      key: 'objectivesAndStrategies',
      title: '3. Objectives, Strategies & Related Business Risks',
      guidance: 'Strategic business plans, capital expenditure plans, R&D/technology modernization, and risks that strategies may fail.',
      placeholder: 'Outline management strategic roadmap, upcoming capex projects, new product ventures, and operational hurdles...',
      rows: 3,
    },
    {
      key: 'industryFactors',
      title: '4. Industry Factors & Competitive Environment',
      guidance: 'Market demand, raw material supply dynamics, cyclicality, pricing pressure, key competitors, and substitute products.',
      placeholder: 'Detail market dynamics, raw material price volatility, major industry competitors, and capacity utilization benchmarks...',
      rows: 3,
    },
    {
      key: 'regulatoryFactors',
      title: '5. Regulatory & Statutory Framework',
      guidance: 'Applicable accounting framework (AS / Ind AS), Schedule III, Companies Act 2013, GST, direct tax, environmental norms, and industry-specific regulations.',
      placeholder: 'List statutory enactments, licensing requirements, environmental compliance (e.g. SPCB/CPCB), and export-import regulations...',
      rows: 3,
    },
    {
      key: 'otherExternalFactors',
      title: '6. Other External Economic Factors',
      guidance: 'General economic conditions, interest rate trends, inflation, foreign exchange volatility, and global supply chain disruptions.',
      placeholder: 'Assess impact of FX fluctuations on receivables/payables, interest rate impacts on borrowings, and macro-economic factors...',
      rows: 3,
    },
    {
      key: 'performanceMeasures',
      title: '7. Measurement & Review of Financial Performance',
      guidance: 'Key performance indicators (KPIs) monitored by management and lenders (e.g., EBITDA margin, inventory days, debtor days, capacity utilization).',
      placeholder: 'Specify internal management metrics, bank covenants, variance analysis triggers, and target ratios...',
      rows: 3,
    },
    {
      key: 'entityLevelRisks',
      title: '8. Entity-Level Risks Arising from the Above (Summary Synthesis)',
      guidance: 'Synthesize the principal risks of material misstatement identified at the financial statement level that pervade the financial statements.',
      placeholder: 'Summarize the overarching entity-level risks that inform the overall audit strategy...',
      rows: 4,
    },
  ];

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Stage Header */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono-num text-xs font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
              Stage 02 • SA 315 (Revised)
            </span>
            <span className="text-xs text-stone-500">Para 11: Entity & Environment</span>
          </div>
          <h2 className="font-serif font-bold text-xl text-stone-900 dark:text-stone-100">
            Understanding the Entity and Its Environment
          </h2>
          <p className="text-xs text-stone-600 dark:text-stone-400 mt-1">
            Establish a thorough frame of reference for identifying and assessing risks of material misstatement across operations, governance, and economics.
          </p>
        </div>

        {onOpenKnowledgeBase && (
          <button
            onClick={onOpenKnowledgeBase}
            className="px-3 py-1.5 rounded-md bg-stone-100 dark:bg-stone-800 hover:bg-stone-200 text-stone-700 dark:text-stone-300 text-xs font-medium flex items-center gap-1.5 shrink-0 self-start transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>SA 315 Para 11 Ref</span>
          </button>
        )}
      </div>

      {/* 8 Structured Sections */}
      <div className="space-y-4">
        {sections.map((sec, idx) => (
          <div
            key={sec.key}
            className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs space-y-2"
          >
            <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-1">
              <h3 className="font-serif font-bold text-sm text-stone-900 dark:text-stone-100">
                {sec.title}
              </h3>
              <span className="text-[11px] text-stone-400">
                {sec.guidance}
              </span>
            </div>

            <textarea
              rows={sec.rows}
              value={engagement.entityUnderstanding[sec.key]}
              onChange={(e) => updateUnderstanding(sec.key, e.target.value)}
              placeholder={sec.placeholder}
              className="w-full px-3 py-2 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 placeholder-stone-400 text-xs leading-relaxed focus:border-amber-700"
            />
          </div>
        ))}
      </div>
    </div>
  );
};
