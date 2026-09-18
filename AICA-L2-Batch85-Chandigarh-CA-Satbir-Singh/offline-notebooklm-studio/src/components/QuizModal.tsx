import React, { useState } from 'react';
import { SourceItem } from '../types';
import { HelpCircle, X, Check, Loader2, Plus } from 'lucide-react';
import { SourceSelectorDropdown } from './SourceSelectorDropdown';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  sources: SourceItem[];
  selectedSourceIds: Set<string>;
  onGenerate: (options: {
    sources: SourceItem[];
    numQuestions: 'fewer' | 'standard' | 'more';
    difficulty: 'easy' | 'medium' | 'hard';
    topic: string;
  }) => void;
  isGenerating?: boolean;
}

export const QuizModal: React.FC<Props> = ({
  isOpen,
  onClose,
  sources,
  selectedSourceIds: initialSelectedIds,
  onGenerate,
  isGenerating = false,
}) => {
  const [numQuestions, setNumQuestions] = useState<'fewer' | 'standard' | 'more'>('standard');
  const [difficulty, setDifficulty] = useState<'easy' | 'medium' | 'hard'>('medium');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set(initialSelectedIds));
  const [topic, setTopic] = useState('');

  // Sync selected IDs when modal opens
  React.useEffect(() => {
    if (isOpen) {
      setSelectedIds(new Set(initialSelectedIds));
    }
  }, [isOpen, initialSelectedIds]);

  if (!isOpen) return null;

  const quickTopicSuggestions = [
    'AEPS Balance Transfers',
    'Transaction Type Scenarios',
    'Ledger Math Skills',
    'Statutory Grounds & CIT(A)',
    'Quantitative Metrics',
  ];

  const handleChipClick = (suggestion: string) => {
    if (!topic.trim()) {
      setTopic(suggestion);
    } else {
      setTopic((prev) => `${prev}, ${suggestion}`);
    }
  };

  const handleGenerate = () => {
    const chosenSources = sources.filter((s) => selectedIds.has(s.id));
    if (chosenSources.length === 0) return;
    onGenerate({
      sources: chosenSources,
      numQuestions,
      difficulty,
      topic,
    });
  };

  const chosenSourcesCount = selectedIds.size;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden flex flex-col animate-in zoom-in-95 duration-150">
        {/* Header matching Screenshot */}
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
              <HelpCircle className="w-5 h-5" />
            </div>
            <h2 className="text-base font-semibold text-gray-900">Quiz</h2>
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
          {/* Top Controls Row: Number of Questions, Level of Difficulty, Sources */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-5 items-start">
            {/* 1. Number of Questions */}
            <div className="md:col-span-5 space-y-2">
              <label className="block text-xs font-semibold text-gray-700">
                Number of Questions
              </label>
              <div className="inline-flex rounded-full border border-gray-300 p-0.5 bg-white shadow-2xs">
                <button
                  type="button"
                  onClick={() => setNumQuestions('fewer')}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    numQuestions === 'fewer'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Fewer
                </button>
                <button
                  type="button"
                  onClick={() => setNumQuestions('standard')}
                  className={`flex items-center gap-1 px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    numQuestions === 'standard'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {numQuestions === 'standard' && <Check className="w-3.5 h-3.5 text-gray-800" />}
                  <span>Standard (Default)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setNumQuestions('more')}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    numQuestions === 'more'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  More
                </button>
              </div>
            </div>

            {/* 2. Level of Difficulty */}
            <div className="md:col-span-4 space-y-2">
              <label className="block text-xs font-semibold text-gray-700">
                Level of Difficulty
              </label>
              <div className="inline-flex rounded-full border border-gray-300 p-0.5 bg-white shadow-2xs">
                <button
                  type="button"
                  onClick={() => setDifficulty('easy')}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    difficulty === 'easy'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Easy
                </button>
                <button
                  type="button"
                  onClick={() => setDifficulty('medium')}
                  className={`flex items-center gap-1 px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    difficulty === 'medium'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {difficulty === 'medium' && <Check className="w-3.5 h-3.5 text-gray-800" />}
                  <span>Medium (Default)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setDifficulty('hard')}
                  className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition ${
                    difficulty === 'hard'
                      ? 'bg-gray-100 text-gray-900 font-semibold'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Hard
                </button>
              </div>
            </div>

            {/* 3. Sources Selector */}
            <div className="md:col-span-3 space-y-2">
              <label className="block text-xs font-semibold text-gray-700">
                Sources
              </label>
              <SourceSelectorDropdown
                sources={sources}
                selectedSourceIds={selectedIds}
                onChangeSelected={setSelectedIds}
              />
            </div>
          </div>

          {/* "What should the topic be?" Input Box */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-gray-900">
              What should the topic be?
            </label>
            <textarea
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Test knowledge on 5 AEPS balance transfer mechanics to retailer bank accounts."
              rows={4}
              className="w-full p-4 rounded-xl border border-gray-300 bg-white text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition resize-none"
            />

            {/* Quick Topic Chips */}
            <div className="flex flex-wrap gap-2 pt-1">
              {quickTopicSuggestions.map((sugg, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleChipClick(sugg)}
                  className="inline-flex items-center gap-1 px-3 py-1 rounded-full border border-gray-300 bg-white hover:bg-gray-50 text-xs text-gray-700 font-medium transition shadow-2xs"
                >
                  <Plus className="w-3 h-3 text-gray-400" />
                  <span>{sugg}</span>
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
