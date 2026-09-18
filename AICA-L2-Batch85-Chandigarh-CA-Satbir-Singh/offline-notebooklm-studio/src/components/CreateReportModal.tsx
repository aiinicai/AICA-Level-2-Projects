import React, { useState } from 'react';
import { SourceItem } from '../types';
import { Sparkles, X, Edit3, Loader2, Wand2, FileText, ArrowLeft } from 'lucide-react';
import { SourceSelectorDropdown } from './SourceSelectorDropdown';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onGenerateReport: (options: {
    sources: SourceItem[];
    formatType: string;
    customTitle?: string;
    customInstructions?: string;
  }) => void;
  isGenerating?: boolean;
}

interface FormatItem {
  id: string;
  title: string;
  description: string;
  hasEdit?: boolean;
  defaultPrompt?: string;
}

export const CreateReportModal: React.FC<Props> = ({
  isOpen,
  onClose,
  sources,
  selectedSourceIds: initialSelectedIds,
  onGenerateReport,
  isGenerating = false,
}) => {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(initialSelectedIds));
  const [activeCustomizing, setActiveCustomizing] = useState<FormatItem | null>(null);
  const [customInstructions, setCustomInstructions] = useState('');
  const [customTitle, setCustomTitle] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set(initialSelectedIds));
      setActiveCustomizing(null);
      setCustomInstructions('');
      setCustomTitle('');
    }
  }, [isOpen, initialSelectedIds]);

  if (!isOpen) return null;

  const baseFormats: FormatItem[] = [
    {
      id: 'custom',
      title: 'Create Your Own',
      description: 'Craft reports your way by specifying structure, style, tone, and more',
      hasEdit: false,
    },
    {
      id: 'briefing_doc',
      title: 'Briefing Doc',
      description: 'Overview of your sources featuring key insights and quotes',
      hasEdit: true,
      defaultPrompt: 'Create a formal executive briefing document with key quotes and core takeaways.',
    },
    {
      id: 'study_guide',
      title: 'Study Guide',
      description: 'Short-answer quiz, suggested essay questions, and glossary of key terms',
      hasEdit: true,
      defaultPrompt: 'Generate a study companion with glossary of terms and conceptual review.',
    },
    {
      id: 'blog_post',
      title: 'Blog Post',
      description: 'Insightful takeaways distilled into a highly readable article',
      hasEdit: true,
      defaultPrompt: 'Distill findings into an engaging, clear blog post for broader audiences.',
    },
  ];

  const suggestedFormats: FormatItem[] = [
    {
      id: 'financial_audit',
      title: 'Financial Audit Report',
      description: 'A comprehensive audit of the AEPS ledger entries to verify transactional integrity and reconciliation.',
      hasEdit: true,
      defaultPrompt: 'Audit financial ledger allocations, balance transfers, and transactional records.',
    },
    {
      id: 'cash_flow',
      title: 'Cash Flow Analysis',
      description: 'A detailed assessment of capital movement between service sales and bank settlement accounts.',
      hasEdit: true,
      defaultPrompt: 'Analyze cash flow mechanics, inflow/outflow cycles, and liquidity trends.',
    },
    {
      id: 'concept_explainer',
      title: 'Concept Explainer',
      description: 'A clear guide explaining how to interpret credit and debit entries in a financial ledger.',
      hasEdit: true,
      defaultPrompt: 'Explain complex statutory concepts and ledger entries simply and intuitively.',
    },
    {
      id: 'operational_overview',
      title: 'Operational Overview',
      description: 'A simplified explanation of the stages a digital transaction goes through based on ledger records.',
      hasEdit: true,
      defaultPrompt: 'Provide an operational stage-by-stage lifecycle of transactions and workflows.',
    },
  ];

  const handleCardClick = (item: FormatItem) => {
    if (item.id === 'custom') {
      setActiveCustomizing(item);
      setCustomTitle('Custom Grounded Report');
      setCustomInstructions('');
    } else {
      // Direct generate or edit
      const chosenSources = sources.filter((s) => selectedIds.has(s.id));
      if (chosenSources.length === 0) return;
      onGenerateReport({
        sources: chosenSources,
        formatType: item.id,
        customTitle: item.title,
        customInstructions: item.defaultPrompt,
      });
    }
  };

  const handleEditClick = (e: React.MouseEvent, item: FormatItem) => {
    e.stopPropagation();
    setActiveCustomizing(item);
    setCustomTitle(item.title);
    setCustomInstructions(item.defaultPrompt || item.description);
  };

  const handleConfirmCustom = () => {
    const chosenSources = sources.filter((s) => selectedIds.has(s.id));
    if (chosenSources.length === 0) return;
    onGenerateReport({
      sources: chosenSources,
      formatType: activeCustomizing?.id || 'custom',
      customTitle: customTitle.trim() || activeCustomizing?.title || 'Custom Report',
      customInstructions: customInstructions.trim(),
    });
  };

  const chosenSourcesCount = selectedIds.size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-4xl bg-[#fbfbfa] rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col animate-in zoom-in-95 duration-150 max-h-[90vh]">
        {/* Header matching Screenshot 2 */}
        <div className="px-6 py-4 border-b border-gray-200/80 bg-white flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-gray-900">Create report</h2>
          </div>

          <div className="flex items-center gap-3">
            {/* Sources dropdown selector in header */}
            <SourceSelectorDropdown
              sources={sources}
              selectedSourceIds={selectedIds}
              onChangeSelected={setSelectedIds}
            />

            <button
              onClick={onClose}
              className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-600 flex items-center justify-center transition"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto">
          {activeCustomizing ? (
            /* Customizing Form */
            <div className="space-y-5 bg-white p-6 rounded-2xl border border-gray-200 shadow-xs">
              <div className="flex items-center justify-between pb-3 border-b border-gray-100">
                <button
                  type="button"
                  onClick={() => setActiveCustomizing(null)}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-600 hover:text-gray-900"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span>Back to templates</span>
                </button>
                <span className="text-xs font-medium text-blue-600">
                  Customizing: {activeCustomizing.title}
                </span>
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-700">
                  Report Title
                </label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder="e.g. Comprehensive Financial Assessment"
                  className="w-full px-3.5 py-2 rounded-xl border border-gray-300 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="block text-xs font-semibold text-gray-700">
                  Custom Instructions & Focus Topics
                </label>
                <textarea
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder="Specify the structure, style, tone, key metrics to highlight, or specific sections..."
                  rows={5}
                  className="w-full p-3.5 rounded-xl border border-gray-300 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 resize-none"
                />
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleConfirmCustom}
                  disabled={chosenSourcesCount === 0 || isGenerating}
                  className="px-6 py-2.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition shadow-sm disabled:opacity-40 flex items-center gap-2"
                >
                  {isGenerating && <Loader2 className="w-4 h-4 animate-spin" />}
                  <span>Generate Report</span>
                </button>
              </div>
            </div>
          ) : (
            <>
              {/* Section 1: Format */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold text-gray-800 tracking-wide">Format</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {baseFormats.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleCardClick(item)}
                      className="relative p-4 rounded-xl bg-[#f5f5f0] hover:bg-[#edece6] border border-[#e8e7e1] transition cursor-pointer flex flex-col justify-between min-h-[120px] group shadow-2xs text-left"
                    >
                      <div className="space-y-1.5 pr-6">
                        <h4 className="text-sm font-bold text-gray-900 leading-tight">
                          {item.title}
                        </h4>
                        <p className="text-xs text-gray-600 leading-snug line-clamp-3">
                          {item.description}
                        </p>
                      </div>

                      {item.hasEdit && (
                        <button
                          type="button"
                          onClick={(e) => handleEditClick(e, item)}
                          className="absolute top-3.5 right-3.5 w-7 h-7 rounded-full bg-white/70 hover:bg-white text-gray-600 hover:text-gray-900 flex items-center justify-center transition shadow-2xs"
                          title="Customize prompt"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Section 2: Suggested Format */}
              <div className="space-y-3">
                <div className="flex items-center space-x-1.5 text-xs font-bold text-gray-800">
                  <Edit3 className="w-3.5 h-3.5 text-gray-600" />
                  <span>Suggested Format</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                  {suggestedFormats.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleCardClick(item)}
                      className="relative p-4 rounded-xl bg-[#f5f5f0] hover:bg-[#edece6] border border-[#e8e7e1] transition cursor-pointer flex flex-col justify-between min-h-[130px] group shadow-2xs text-left"
                    >
                      <div className="space-y-1.5 pr-6">
                        <h4 className="text-sm font-bold text-gray-900 leading-tight">
                          {item.title}
                        </h4>
                        <p className="text-xs text-gray-600 leading-snug line-clamp-3">
                          {item.description}
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={(e) => handleEditClick(e, item)}
                        className="absolute top-3.5 right-3.5 w-7 h-7 rounded-full bg-white/70 hover:bg-white text-gray-600 hover:text-gray-900 flex items-center justify-center transition shadow-2xs"
                        title="Customize prompt"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Bottom Bar Info */}
        <div className="px-6 py-3.5 border-t border-gray-200/70 bg-white flex items-center justify-between text-xs text-gray-500">
          <span>
            Click any format card to generate, or use the pencil icon to customize instructions.
          </span>
          <span className="font-medium text-gray-700">
            {chosenSourcesCount} source{chosenSourcesCount !== 1 ? 's' : ''} selected
          </span>
        </div>
      </div>
    </div>
  );
};
