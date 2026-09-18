import React, { useState } from 'react';
import { SourceItem } from '../types';
import { Table, X, ChevronDown, Loader2, Plus } from 'lucide-react';
import { SourceSelectorDropdown } from './SourceSelectorDropdown';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onGenerateTable: (options: {
    sources: SourceItem[];
    language: string;
    prompt: string;
  }) => void;
  isGenerating?: boolean;
}

const LANGUAGES = [
  'English',
];

export const DataTableModal: React.FC<Props> = ({
  isOpen,
  onClose,
  sources,
  selectedSourceIds: initialSelectedIds,
  onGenerateTable,
  isGenerating = false,
}) => {
  const [language, setLanguage] = useState('English');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(initialSelectedIds));
  const [prompt, setPrompt] = useState('');

  React.useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set(initialSelectedIds));
      setPrompt('');
    }
  }, [isOpen, initialSelectedIds]);

  if (!isOpen) return null;

  const quickTablePills = [
    'Major findings & key numerical metrics',
    'Financial ledger credit & debit reconciliation',
    'Source comparison by author and topics',
    'Statutory provisions and CIT(A) citations',
  ];

  const handleGenerate = () => {
    const chosenSources = sources.filter((s) => selectedIds.has(s.id));
    if (chosenSources.length === 0) return;
    onGenerateTable({
      sources: chosenSources,
      language,
      prompt,
    });
  };

  const chosenSourcesCount = selectedIds.size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
        {/* Header matching Screenshot 3 */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
              <Table className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-gray-900">Customize Data Table</h2>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-600 flex items-center justify-center transition"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 max-h-[80vh] overflow-y-auto">
          {/* Top Row: Choose language + Sources */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 items-start">
            {/* 1. Choose language */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-gray-700">
                Choose language
              </label>
              <div className="relative">
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="w-full appearance-none px-4 py-2.5 rounded-xl border border-gray-300 bg-white text-sm text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 pr-10 shadow-2xs font-medium cursor-pointer"
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>
                      {lang}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-gray-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* 2. Sources */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-gray-700">
                Sources
              </label>
              <SourceSelectorDropdown
                sources={sources}
                selectedSourceIds={selectedIds}
                onChangeSelected={setSelectedIds}
                className="w-full"
              />
            </div>
          </div>

          {/* "Describe the data table you want to create" */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-900">
              Describe the data table you want to create
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder={`Things to try\n  • Create a table with the major findings in these research papers, using columns: title, author, key result\n  • Extract the most important quotes from my readings, grouping them by topic and author\n  • List vacation destinations in Italy with city, best time to visit, attractions, and cost`}
              rows={6}
              className="w-full p-4 rounded-xl border border-gray-300 bg-white text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition resize-none font-sans leading-relaxed"
            />

            {/* Quick Pills */}
            <div className="flex flex-wrap gap-2 pt-1">
              {quickTablePills.map((pill, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setPrompt(pill)}
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-gray-300 bg-white hover:bg-gray-50 text-xs text-gray-700 font-medium transition shadow-2xs"
                >
                  <Plus className="w-3 h-3 text-gray-400" />
                  <span>{pill}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer with Generate Button */}
        <div className="px-6 py-4 border-t border-gray-100 bg-[#fafafa] flex items-center justify-between">
          <span className="text-xs text-gray-500">
            Grounded on <strong>{chosenSourcesCount}</strong> selected source{chosenSourcesCount !== 1 ? 's' : ''}
          </span>

          <button
            type="button"
            onClick={handleGenerate}
            disabled={chosenSourcesCount === 0 || isGenerating}
            className="px-6 py-2 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium transition shadow-sm disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isGenerating && <Loader2 className="w-4 h-4 animate-spin" />}
            <span>Generate</span>
          </button>
        </div>
      </div>
    </div>
  );
};
