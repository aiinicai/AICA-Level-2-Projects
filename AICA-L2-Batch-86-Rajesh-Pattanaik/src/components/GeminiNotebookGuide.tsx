import React, { useState } from 'react';
import { BookOpenCheck, ChevronDown, ChevronUp, ShieldCheck, ArrowRight, ExternalLink } from 'lucide-react';

export const GeminiNotebookGuide: React.FC = () => {
  const [isExpanded, setIsExpanded] = useState(false);

  const steps = [
    {
      num: 1,
      title: 'Open Gemini Notebook',
      detail: 'Open your Gemini Notebook research workspace.'
    },
    {
      num: 2,
      title: 'Add Sources → Web / Deep Research',
      detail: 'Use Add Sources and select Web / Deep Research mode.'
    },
    {
      num: 3,
      title: 'Search Question / Case Facts',
      detail: 'Search the complete professional question, acts, or case facts.'
    },
    {
      num: 4,
      title: 'Review & Prefer Authoritative Sources',
      detail: 'Prefer primary sources: Acts, Rules, Notifications, Circulars, ICAI guidance.'
    },
    {
      num: 5,
      title: 'Bring Sources into CA VerifyAI',
      detail: 'Download or copy the relevant statutory excerpts and paste or upload them below.'
    }
  ];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-3.5 sm:p-4 text-slate-800 shadow-xs transition-all">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-start sm:items-center gap-2.5">
          <div className="p-2 rounded-lg bg-blue-50 text-blue-800 border border-blue-100 shrink-0 mt-0.5 sm:mt-0">
            <BookOpenCheck className="w-4 h-4 text-blue-700" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-xs sm:text-sm font-bold text-slate-900 flex items-center gap-1.5">
                Research Guidance: Gemini Notebook
              </h3>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200/60">
                Recommended 5-Step Workflow
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5 leading-normal">
              Gemini Notebook is used for research and source collection, while <strong>CA VerifyAI</strong> performs the independent professional verification and missed-issue analysis.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs font-semibold text-blue-700 hover:text-blue-900 flex items-center gap-1 px-2.5 py-1 rounded-md hover:bg-blue-50 transition-colors shrink-0 cursor-pointer self-end sm:self-center"
          aria-expanded={isExpanded}
        >
          {isExpanded ? (
            <>
              Hide 5-Step Guide <ChevronUp className="w-3.5 h-3.5" />
            </>
          ) : (
            <>
              View 5-Step Guide <ChevronDown className="w-3.5 h-3.5" />
            </>
          )}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3.5 pt-3.5 border-t border-slate-100 space-y-3">
          {/* Visual 5-step pipeline */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2.5">
            {steps.map((s, idx) => (
              <div
                key={s.num}
                className="bg-slate-50 border border-slate-200/90 rounded-lg p-2.5 text-xs flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center gap-1.5 font-bold text-slate-900 mb-1">
                    <span className="w-5 h-5 rounded-full bg-slate-900 text-white flex items-center justify-center text-[10px] shrink-0">
                      {s.num}
                    </span>
                    <span className="text-[11px] leading-tight">{s.title}</span>
                  </div>
                  <p className="text-slate-600 text-[10px] pl-6 leading-relaxed">
                    {s.detail}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center justify-between flex-wrap gap-2 px-3 py-2 bg-slate-50 rounded-lg border border-slate-200/80 text-[11px] text-slate-600">
            <div className="flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              <span>
                <strong>Privacy & Sandbox Isolation:</strong> CA VerifyAI does not access your private Gemini Notebook directly. Simply copy/paste or upload your research documents.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
