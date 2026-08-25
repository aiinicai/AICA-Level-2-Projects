import React, { useState } from 'react';
import { 
  ClipboardList, 
  AlertCircle, 
  CheckCircle2, 
  Clock, 
  UserCheck, 
  BookMarked,
  Copy,
  Check
} from 'lucide-react';
import { AuditRecommendation } from '../types';

interface Part3RecommendationsListProps {
  recommendations: AuditRecommendation[];
}

export const Part3RecommendationsList: React.FC<Part3RecommendationsListProps> = ({ recommendations }) => {
  const [copied, setCopied] = useState(false);
  const [completedItems, setCompletedItems] = useState<Record<string, boolean>>({});

  const toggleComplete = (id: string) => {
    setCompletedItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const getPriorityBadge = (priority: string) => {
    const p = priority.toLowerCase();
    if (p.includes('immediate')) {
      return (
        <span className="bg-red-600 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
          IMMEDIATE RECTIFICATION
        </span>
      );
    }
    if (p.includes('pre-signing') || p.includes('presigning')) {
      return (
        <span className="bg-orange-500 text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
          PRE-SIGNING SIGN-OFF
        </span>
      );
    }
    return (
      <span className="bg-[#141414] text-white px-2 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider inline-block">
        MANAGEMENT LETTER ITEM
      </span>
    );
  };

  const handleCopyActionPlan = () => {
    const text = recommendations
      .map(
        (r, idx) =>
          `${idx + 1}. [${r.priority}] ${r.category}: ${r.recommendation} (Assigned to: ${r.actionFor}${
            r.statutoryReference ? ` | Ref: ${r.statutoryReference}` : ''
          })`
      )
      .join('\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="part-3-audit-recommendations" className="bg-white border-2 border-[#141414] shadow-dense mb-6 overflow-hidden">
      {/* Section Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between p-4 bg-[#F9F9F7] border-b border-[#141414] gap-3">
        <div>
          <h2 className="text-[11px] font-serif italic uppercase text-[#141414]/70 mb-0.5 tracking-wider">
            Audit Action Plan • Part 3
          </h2>
          <h3 className="text-base sm:text-lg font-bold uppercase tracking-tight text-[#141414]">
            Part 3: Actionable Audit Recommendations
          </h3>
          <p className="text-[10px] font-mono text-[#141414]/70 mt-0.5 uppercase">
            STATUTORY COMPLIANCE ACTION STEPS FOR CA ENGAGEMENT TEAM & MANAGEMENT PRE-SIGNING
          </p>
        </div>

        {/* Copy Action Plan */}
        <button
          id="copy-part-3-btn"
          onClick={handleCopyActionPlan}
          className="self-start md:self-center inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-mono font-bold uppercase bg-white hover:bg-neutral-100 text-[#141414] border border-[#141414] transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-700" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'COPIED PLAN' : 'COPY ACTION PLAN'}</span>
        </button>
      </div>

      {/* Recommendations Cards List */}
      <div className="p-4 space-y-2.5 bg-[#E4E3E0]">
        {recommendations.length === 0 ? (
          <div className="p-6 text-center text-[#141414]/60 font-mono text-xs bg-white border border-[#141414]">
            NO PENDING STATUTORY AUDIT RECOMMENDATIONS. ALL DISCLOSURE CHECKS SATISFIED.
          </div>
        ) : (
          recommendations.map((rec, index) => {
            const isDone = !!completedItems[rec.id || `rec-${index}`];
            return (
              <div
                key={rec.id || index}
                className={`p-3.5 border border-[#141414] transition flex flex-col sm:flex-row items-start justify-between gap-3 ${
                  isDone
                    ? 'bg-[#D1D0CC] opacity-60'
                    : 'bg-white hover:bg-[#F9F9F7]'
                }`}
              >
                <div className="flex items-start space-x-3 flex-1">
                  <button
                    onClick={() => toggleComplete(rec.id || `rec-${index}`)}
                    className="mt-0.5 shrink-0 text-[#141414] cursor-pointer"
                    title={isDone ? 'Mark as Pending' : 'Mark as Verified/Cleared'}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-4 h-4 text-green-700" />
                    ) : (
                      <div className="w-4 h-4 border-2 border-[#141414] hover:bg-neutral-200" />
                    )}
                  </button>

                  <div className="space-y-1 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[11px] font-mono font-bold uppercase text-[#141414]">
                        STEP {String(index + 1).padStart(2, '0')}: {rec.category}
                      </span>
                      {getPriorityBadge(rec.priority)}
                      {rec.statutoryReference && (
                        <span className="px-1.5 py-0.2 bg-[#D1D0CC] text-[#141414] font-mono text-[9px] font-bold border border-[#141414]/30 uppercase">
                          {rec.statutoryReference}
                        </span>
                      )}
                    </div>

                    <p className={`text-xs text-[#141414] leading-snug font-serif italic ${isDone ? 'line-through opacity-60' : ''}`}>
                      {rec.recommendation}
                    </p>

                    <div className="flex items-center space-x-2 text-[10px] font-mono text-[#141414]/70 pt-0.5 uppercase">
                      <UserCheck className="w-3 h-3 text-[#141414]" />
                      <span>ACTION FOR: <strong className="text-[#141414]">{rec.actionFor}</strong></span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
};

