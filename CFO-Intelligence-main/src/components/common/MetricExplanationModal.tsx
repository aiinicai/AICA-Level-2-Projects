import React, { useState } from 'react';
import { X, HelpCircle, Sparkles, BookOpen, Target, ArrowRight, CheckCircle2, Shield } from 'lucide-react';
import { KpiMetric, ClientProfile } from '../../types';

interface MetricExplanationModalProps {
  metric: KpiMetric | null;
  client: ClientProfile;
  onClose: () => void;
}

export const MetricExplanationModal: React.FC<MetricExplanationModalProps> = ({
  metric,
  client,
  onClose,
}) => {
  const [aiExpanded, setAiExpanded] = useState(false);
  const [loadingAi, setLoadingAi] = useState(false);
  const [aiInsight, setAiInsight] = useState<{
    plainEnglishMeaning?: string;
    peerComparison?: string;
    step1Action?: string;
    step2Action?: string;
  } | null>(null);

  if (!metric) return null;

  const handleAskAi = async () => {
    setLoadingAi(true);
    setAiExpanded(true);
    try {
      const res = await fetch('/api/ai/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          metricName: metric.name,
          metricValue: metric.formattedValue,
          industry: client.industryName,
          context: {
            category: metric.category,
            benchmark: metric.benchmarkFormatted,
            trend: metric.trend,
            changePercent: metric.changePercentage,
          },
        }),
      });
      const data = await res.json();
      setAiInsight(data);
    } catch (e) {
      console.error(e);
      setAiInsight({
        plainEnglishMeaning: `Your ${metric.name} of ${metric.formattedValue} reflects how effectively operations in ${client.industryName} generate operating leverage.`,
        peerComparison: `Peers in the ${client.industryName} sector maintain an average target of ${metric.benchmarkFormatted || 'typical median'}.`,
        step1Action: `Review monthly line item variances in the P&L and operational schedules.`,
        step2Action: `Work with your Virtual CFO team to optimize driver assumptions in the next rolling forecast.`,
      });
    } finally {
      setLoadingAi(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-xl w-full overflow-hidden">
        {/* Modal Header */}
        <div className="bg-slate-900 px-6 py-4 text-white flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-600/30 rounded-lg text-indigo-400 border border-indigo-500/30">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
                Financial Metric Intelligence
              </div>
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                {metric.name}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          {/* Top Metric Strip */}
          <div className="flex items-center justify-between p-4 bg-slate-50 border border-slate-200 rounded-xl">
            <div>
              <span className="text-xs text-slate-500 font-medium">Current Client Metric</span>
              <div className="text-2xl font-bold text-slate-900">{metric.formattedValue}</div>
            </div>
            <div className="text-right">
              <span className="text-xs text-slate-500 font-medium">Industry Benchmark</span>
              <div className="text-sm font-semibold text-slate-700">
                {metric.benchmarkFormatted || 'Proprietary Target'}
              </div>
              <span className="inline-block mt-0.5 text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                {client.industryName}
              </span>
            </div>
          </div>

          {/* Section 1: What is it? */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold text-indigo-600 uppercase tracking-wider flex items-center gap-1.5">
              <BookOpen className="w-4 h-4" /> 1. What is it?
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed bg-indigo-50/50 p-3 rounded-lg border border-indigo-100">
              {metric.explanation?.whatIsIt || 'A fundamental performance indicator evaluating company efficiency.'}
            </p>
          </div>

          {/* Section 2: Why it matters */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold text-amber-700 uppercase tracking-wider flex items-center gap-1.5">
              <Target className="w-4 h-4" /> 2. Why does it matter?
            </h4>
            <p className="text-sm text-slate-700 leading-relaxed bg-amber-50/50 p-3 rounded-lg border border-amber-100">
              {metric.explanation?.whyItMatters || 'Helps management identify financial health and avoid liquidity compression.'}
            </p>
          </div>

          {/* Section 3: What does my number mean? */}
          <div className="space-y-1.5">
            <h4 className="text-xs font-bold text-emerald-700 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> 3. What does my number mean?
            </h4>
            <p className="text-sm text-slate-800 font-medium leading-relaxed bg-emerald-50/60 p-3 rounded-lg border border-emerald-200">
              {metric.explanation?.whatMyNumberMeans || `Your current metric stands at ${metric.formattedValue}.`}
            </p>
          </div>

          {/* Section 4: Deterministic Formula */}
          {metric.explanation?.formula && (
            <div className="p-3 bg-slate-100 rounded-lg border border-slate-200 text-xs">
              <span className="font-semibold text-slate-600">Deterministic Formula: </span>
              <code className="text-indigo-700 font-mono bg-white px-2 py-0.5 rounded border border-slate-300">
                {metric.explanation.formula}
              </code>
            </div>
          )}

          {/* AI Root-Cause Explainer Button */}
          {!aiExpanded ? (
            <button
              onClick={handleAskAi}
              disabled={loadingAi}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-linear-to-r from-indigo-600 to-violet-600 text-white text-sm font-semibold rounded-xl hover:from-indigo-700 hover:to-violet-700 transition-all shadow-md"
            >
              <Sparkles className="w-4 h-4" />
              Ask AI Virtual CFO: "Deep Root-Cause Explanation"
            </button>
          ) : (
            <div className="border border-violet-200 bg-violet-50/60 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between text-violet-900 font-bold text-sm">
                <span className="flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-violet-600" /> AI CFO Root-Cause Analysis
                </span>
                <span className="text-[11px] text-violet-600 font-normal flex items-center gap-1">
                  <Shield className="w-3 h-3" /> Redacted Dataset
                </span>
              </div>
              {loadingAi ? (
                <div className="py-4 text-center text-xs text-violet-700 animate-pulse">
                  Analyzing underlying drivers with deterministic model...
                </div>
              ) : aiInsight ? (
                <div className="space-y-2.5 text-xs text-slate-800">
                  <div className="p-2.5 bg-white rounded-lg border border-violet-100">
                    <span className="font-bold text-violet-800">Executive Takeaway: </span>
                    {aiInsight.plainEnglishMeaning}
                  </div>
                  {aiInsight.peerComparison && (
                    <div className="p-2.5 bg-white rounded-lg border border-violet-100">
                      <span className="font-bold text-violet-800">Industry Peer Context: </span>
                      {aiInsight.peerComparison}
                    </div>
                  )}
                  {(aiInsight.step1Action || aiInsight.step2Action) && (
                    <div className="p-2.5 bg-white rounded-lg border border-violet-100 space-y-1">
                      <span className="font-bold text-violet-800">Actionable Steps:</span>
                      {aiInsight.step1Action && <p className="pl-2 border-l-2 border-violet-400">1. {aiInsight.step1Action}</p>}
                      {aiInsight.step2Action && <p className="pl-2 border-l-2 border-violet-400">2. {aiInsight.step2Action}</p>}
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="bg-slate-50 px-6 py-3 border-t border-slate-200 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-white text-xs font-semibold rounded-lg hover:bg-slate-800 transition-colors"
          >
            Close Explanation
          </button>
        </div>
      </div>
    </div>
  );
};
