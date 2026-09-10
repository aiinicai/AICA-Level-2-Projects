import React, { useState } from 'react';
import {
  X,
  BookOpen,
  Sparkles,
  Search,
  ChevronRight,
  ShieldCheck,
  Send,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { ICAI_STANDARDS, ICAIStandardDoc } from '../data/icaiStandards';

interface KnowledgeBaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultStandard?: string;
}

export const KnowledgeBaseModal: React.FC<KnowledgeBaseModalProps> = ({
  isOpen,
  onClose,
  defaultStandard,
}) => {
  const [selectedStandard, setSelectedStandard] = useState<ICAIStandardDoc>(
    () => ICAI_STANDARDS.find((s) => s.code.includes(defaultStandard || '')) || ICAI_STANDARDS[0]
  );
  const [searchFilter, setSearchFilter] = useState('');
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiAnswer, setAiAnswer] = useState<string | null>(null);
  const [isAiLoading, setIsAiLoading] = useState(false);

  if (!isOpen) return null;

  const filteredStandards = ICAI_STANDARDS.filter(
    (s) =>
      s.code.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.title.toLowerCase().includes(searchFilter.toLowerCase()) ||
      s.summary.toLowerCase().includes(searchFilter.toLowerCase())
  );

  const handleAskGemini = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiQuestion.trim()) return;

    setIsAiLoading(true);
    setAiAnswer(null);

    try {
      const res = await fetch('/api/gemini/ask-icai-kb', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: aiQuestion,
          standardReference: selectedStandard.code,
        }),
      });

      const data = await res.json();
      setAiAnswer(data.answer || data.error || 'No response returned.');
    } catch (err: any) {
      setAiAnswer('Unable to communicate with AI Assistant. Please check your network or server status.');
    } finally {
      setIsAiLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4 sm:p-6 overflow-y-auto animate-in fade-in">
      <div className="bg-[#fcfbf9] dark:bg-[#15191f] w-full max-w-5xl rounded-xl border border-[#dedbd2] dark:border-[#2e3742] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#dedbd2] dark:border-[#272f38] bg-[#f7f5ef] dark:bg-[#11151a]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-md bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                ICAI Knowledge Base & Technical Library
              </h2>
              <p className="text-xs text-stone-500 dark:text-stone-400">
                Authoritative Standards on Auditing (SAs) issued by the Institute of Chartered Accountants of India
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 hover:bg-stone-200 dark:hover:bg-stone-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          {/* Left Column: Standards Selector */}
          <div className="w-full md:w-80 border-r border-[#dedbd2] dark:border-[#272f38] flex flex-col bg-[#f5f3eb] dark:bg-[#13171d]">
            <div className="p-3 border-b border-[#dedbd2] dark:border-[#272f38]">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
                <input
                  type="text"
                  placeholder="Filter standards (e.g., SA 315, fraud)..."
                  value={searchFilter}
                  onChange={(e) => setSearchFilter(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md bg-white dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-hidden focus:border-amber-700"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {filteredStandards.map((std) => {
                const isSelected = selectedStandard.code === std.code;
                return (
                  <button
                    key={std.code}
                    onClick={() => {
                      setSelectedStandard(std);
                      setAiAnswer(null);
                    }}
                    className={`w-full text-left p-2.5 rounded-lg transition-all ${
                      isSelected
                        ? 'bg-amber-800 text-white dark:bg-amber-700 shadow-xs'
                        : 'hover:bg-stone-200 dark:hover:bg-stone-800 text-stone-800 dark:text-stone-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono-num font-bold text-xs">{std.code}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                        isSelected ? 'bg-amber-900/60 text-amber-200' : 'bg-stone-200 dark:bg-stone-800 text-stone-500'
                      }`}>
                        {std.category.split('&')[0]}
                      </span>
                    </div>
                    <p className={`text-xs mt-1 font-medium line-clamp-1 ${isSelected ? 'text-amber-100' : 'text-stone-700 dark:text-stone-300'}`}>
                      {std.title}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Standard Details + Gemini Q&A */}
          <div className="flex-1 flex flex-col overflow-y-auto p-6 bg-white dark:bg-[#161a21]">
            <div className="border-b border-stone-200 dark:border-stone-800 pb-4 mb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono-num text-sm font-bold text-amber-800 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/60 px-2 py-0.5 rounded border border-amber-200 dark:border-amber-800">
                  {selectedStandard.code}
                </span>
                <span className="text-xs text-stone-500 dark:text-stone-400">
                  {selectedStandard.category}
                </span>
              </div>
              <h3 className="font-serif font-bold text-lg text-stone-900 dark:text-stone-100">
                {selectedStandard.title}
              </h3>
              <p className="text-xs text-stone-600 dark:text-stone-300 mt-2 leading-relaxed">
                {selectedStandard.summary}
              </p>
            </div>

            {/* Key Paragraphs */}
            <div className="mb-6 space-y-3">
              <h4 className="text-xs uppercase font-bold tracking-wider text-stone-500 dark:text-stone-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-amber-700 dark:text-amber-400" />
                <span>Mandatory Paragraphs & Clauses</span>
              </h4>
              <div className="space-y-2.5">
                {selectedStandard.keyParagraphs.map((kp, idx) => (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-[#fbf9f4] dark:bg-[#1a2027] border border-[#e8e4db] dark:border-[#2e3742]"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono-num text-xs font-bold text-amber-900 dark:text-amber-300">
                        {kp.ref}
                      </span>
                      <span className="text-xs font-semibold text-stone-700 dark:text-stone-300">
                        {kp.title}
                      </span>
                    </div>
                    <p className="text-xs text-stone-600 dark:text-stone-300 leading-relaxed">
                      {kp.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            {/* Practical Guidance */}
            <div className="mb-6 p-4 rounded-lg bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800">
              <h4 className="text-xs uppercase font-bold tracking-wider text-emerald-900 dark:text-emerald-300 mb-2">
                Practical Auditor Implementation Notes
              </h4>
              <ul className="space-y-1 text-xs text-emerald-950 dark:text-emerald-200 list-disc list-inside">
                {selectedStandard.practicalAuditorGuidance.map((g, idx) => (
                  <li key={idx}>{g}</li>
                ))}
              </ul>
            </div>

            {/* Ask Gemini Section */}
            <div className="mt-auto border-t border-stone-200 dark:border-stone-800 pt-5">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <h4 className="text-xs font-bold uppercase tracking-wider text-stone-800 dark:text-stone-200">
                  Ask Gemini Technical Assistant on {selectedStandard.code}
                </h4>
              </div>
              <p className="text-xs text-stone-500 mb-3">
                Query the AI model grounded strictly in Indian Standards on Auditing for application dilemmas, paragraph references, and compliance checklists.
              </p>

              <form onSubmit={handleAskGemini} className="flex gap-2">
                <input
                  type="text"
                  placeholder={`E.g., What are the exact requirements to rebut the revenue fraud presumption in ${selectedStandard.code}?`}
                  value={aiQuestion}
                  onChange={(e) => setAiQuestion(e.target.value)}
                  className="flex-1 px-3 py-2 text-xs rounded-md bg-white dark:bg-[#1a2027] border border-stone-300 dark:border-stone-700 text-stone-900 dark:text-stone-100 placeholder-stone-400 focus:outline-hidden focus:border-amber-700"
                />
                <button
                  type="submit"
                  disabled={isAiLoading || !aiQuestion.trim()}
                  className="px-4 py-2 bg-amber-800 dark:bg-amber-600 text-white rounded-md text-xs font-medium hover:bg-amber-900 transition-colors disabled:opacity-50 flex items-center gap-1.5 shadow-xs shrink-0"
                >
                  {isAiLoading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Consulting...</span>
                    </>
                  ) : (
                    <>
                      <Send className="w-3.5 h-3.5" />
                      <span>Ask AI</span>
                    </>
                  )}
                </button>
              </form>

              {aiAnswer && (
                <div className="mt-3 p-3.5 rounded-lg bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-700 text-xs text-stone-800 dark:text-stone-200 leading-relaxed whitespace-pre-wrap animate-in fade-in">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold text-amber-700 dark:text-amber-400 mb-1.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>Gemini Technical Opinion (ICAI Grounded)</span>
                  </div>
                  {aiAnswer}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
