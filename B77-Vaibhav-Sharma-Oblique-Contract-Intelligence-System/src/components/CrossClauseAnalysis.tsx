import React, { useState } from 'react';
import { 
  GitMerge, 
  Sparkles, 
  AlertTriangle, 
  AlertCircle, 
  CheckCircle2, 
  HelpCircle, 
  RefreshCw, 
  FileText, 
  ArrowRight,
  ShieldCheck,
  Zap,
  CornerDownRight
} from 'lucide-react';
import { ContractDocument, CrossClauseInsight } from '../types/contract';

interface CrossClauseAnalysisProps {
  contract: ContractDocument;
  onRefreshCrossClause: () => Promise<void>;
  onJumpToClause?: (page: number, clauseNumber: string) => void;
}

export const CrossClauseAnalysis: React.FC<CrossClauseAnalysisProps> = ({
  contract,
  onRefreshCrossClause,
  onJumpToClause
}) => {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  const [refreshSuccess, setRefreshSuccess] = useState(false);
  const [selectedInsightId, setSelectedInsightId] = useState<string>(
    contract.crossClauseInsights[0]?.id || ''
  );

  const activeInsight = contract.crossClauseInsights.find(i => i.id === selectedInsightId) || contract.crossClauseInsights[0];

  const handleRunFreshPass = async () => {
    setIsRefreshing(true);
    setRefreshError(null);
    setRefreshSuccess(false);
    try {
      await onRefreshCrossClause();
      setRefreshSuccess(true);
      setTimeout(() => setRefreshSuccess(false), 4000);
    } catch (err: any) {
      setRefreshError(err.message || 'Second-pass reasoning encountered an error. Please try again.');
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-xl p-6 shadow-sm border border-indigo-900/60">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 uppercase tracking-wider">
                Second-Pass Reasoning Engine
              </span>
              <span className="text-xs text-indigo-300 font-medium">
                {contract.crossClauseInsights.length} Compound Risk Interactions Discovered
              </span>
            </div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              "Show Me What I Might Have Missed"
            </h1>
            <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
              Standard contract reviews evaluate clauses in isolation. This engine analyzes how separate clauses (e.g. credit terms + retention + tax indemnities + supplier classification) interact to produce hidden compliance, cash-flow, or statutory tax risks.
            </p>
          </div>

          <button
            onClick={handleRunFreshPass}
            disabled={isRefreshing}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-sm transition disabled:opacity-50 shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>{isRefreshing ? 'Analyzing Cross-Clauses...' : 'Re-Run 2nd Pass'}</span>
          </button>
        </div>
      </div>

      {refreshError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{refreshError}</span>
          </div>
          <button
            onClick={handleRunFreshPass}
            className="px-3 py-1 rounded bg-rose-600 text-white font-semibold hover:bg-rose-700 transition"
          >
            Retry
          </button>
        </div>
      )}

      {refreshSuccess && (
        <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>Cross-clause reasoning updated successfully with latest statutory models.</span>
        </div>
      )}

      {contract.crossClauseInsights.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200 p-8 text-center space-y-3">
          <GitMerge className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-bold text-slate-800">No Compound Cross-Clause Interactions Found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            The isolated clauses do not present conflicting or compounding statutory risks. You can re-run the second-pass reasoning pass at any time.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Left 1 Col: List of Compound Interactions */}
          <div className="space-y-3">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 px-1">
              Detected Compound Interactions
            </h3>

            <div className="space-y-2.5">
              {contract.crossClauseInsights.map((insight, idx) => (
                <div
                  key={insight.id}
                  onClick={() => setSelectedInsightId(insight.id)}
                  className={`p-4 rounded-xl border transition cursor-pointer text-xs ${
                    activeInsight?.id === insight.id
                      ? 'bg-purple-50/80 border-purple-300 shadow-xs ring-1 ring-purple-400/40'
                      : 'bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      insight.combinedAttention === 'RED' ? 'bg-rose-600 text-white' :
                      insight.combinedAttention === 'AMBER' ? 'bg-amber-500 text-white' :
                      'bg-blue-600 text-white'
                    }`}>
                      {insight.combinedAttention} RISK
                    </span>

                    <span className="text-[10px] text-slate-500 font-mono">
                      {insight.involvedClauses.length} Clauses Involved
                    </span>
                  </div>

                  <h4 className="font-bold text-slate-900 text-xs mb-1.5 leading-snug">
                    {insight.title}
                  </h4>

                  <p className="text-slate-500 text-[11px] line-clamp-2 leading-relaxed">
                    {insight.whyItMatters}
                  </p>

                  <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-purple-700 font-medium">
                    <span>
                      {insight.involvedClauses.map(c => `Cl ${c.clauseNumber}`).join(' + ')}
                    </span>
                    <ArrowRight className="w-3 h-3 text-purple-500" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right 2 Cols: Deep Compound Analysis Inspector */}
          {activeInsight && (
            <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6 text-xs text-slate-800">
              {/* Top Banner */}
              <div className="border-b border-slate-100 pb-4 space-y-2">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    activeInsight.combinedAttention === 'RED' ? 'bg-rose-600 text-white' :
                    activeInsight.combinedAttention === 'AMBER' ? 'bg-amber-500 text-white' :
                    'bg-blue-600 text-white'
                  }`}>
                    {activeInsight.combinedAttention} COMPOUND RISK
                  </span>
                  <span className="text-xs text-purple-700 font-semibold uppercase tracking-wider">
                    Cross-Clause Synergistic Insight
                  </span>
                </div>
                <h2 className="text-base font-bold text-slate-900 tracking-tight">
                  {activeInsight.title}
                </h2>
              </div>

              {/* Interacting Clauses Chain */}
              <div className="space-y-2">
                <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                  <GitMerge className="w-3.5 h-3.5 text-purple-600" />
                  <span>Interacting Clauses in this Synergistic Loop</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {activeInsight.involvedClauses.map((clause, idx) => (
                    <div 
                      key={idx}
                      className="bg-slate-50 p-3.5 rounded-lg border border-slate-200 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-indigo-700 text-[11px]">
                          Clause {clause.clauseNumber} (Page {clause.pageNumber})
                        </span>
                      </div>
                      <p className="text-slate-600 text-[11px] leading-relaxed">
                        {clause.summary}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              {/* WHY THIS MATTERS (WHY IT WAS MISSED IN ISOLATION) */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-purple-950 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                  <span>Why Reading These Clauses Together Reveals Non-Obvious Risk</span>
                </h4>
                <p className="text-slate-800 bg-purple-50/60 p-3.5 rounded-lg border border-purple-200 leading-relaxed font-medium">
                  {activeInsight.whyItMatters}
                </p>
              </div>

              {/* COMBINED IMPACT */}
              <div className="space-y-1.5">
                <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                  Compounding Accounting, Tax & Working Capital Implication
                </h4>
                <p className="text-slate-700 bg-slate-50 p-3.5 rounded-lg border border-slate-200 leading-relaxed whitespace-pre-line">
                  {activeInsight.combinedImpact}
                </p>
              </div>

              {/* WHAT TO VERIFY */}
              {activeInsight.whatToVerify.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                    Joint Verification Steps
                  </h4>
                  <ul className="space-y-1.5">
                    {activeInsight.whatToVerify.map((item, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-slate-700 bg-slate-50 p-2 rounded border border-slate-100">
                        <CornerDownRight className="w-3.5 h-3.5 text-purple-600 shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* MANAGEMENT QUESTIONS */}
              {activeInsight.managementQuestions.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
                    Questions to Pose to Management / Legal Counsel
                  </h4>
                  <ul className="space-y-1.5">
                    {activeInsight.managementQuestions.map((q, idx) => (
                      <li key={idx} className="flex items-start space-x-2 text-slate-700 bg-amber-50/50 p-2 rounded border border-amber-100">
                        <HelpCircle className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                        <span className="font-medium">{q}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* ACTIONABLE RECOMMENDATION */}
              <div className="p-4 rounded-xl bg-emerald-50/60 border border-emerald-200 space-y-1">
                <h4 className="font-bold text-emerald-900 uppercase tracking-wider text-[11px] flex items-center space-x-1.5">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  <span>Recommended CA Action & Remediation Strategy</span>
                </h4>
                <p className="text-emerald-950 font-medium leading-relaxed">
                  {activeInsight.recommendedAction}
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
