import React from 'react';
import {
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  FileCheck,
  Scale,
  ShieldAlert,
  ArrowRight,
  ListTodo,
  Layers,
  Compass,
} from 'lucide-react';
import {
  EngagementData,
  StageProgress,
  ComputedMateriality,
  RiskLevel,
} from '../../types';
import { formatCompactINR, formatINR, getOutstandingItems } from '../../utils/calculations';

interface StageOverviewProps {
  engagement: EngagementData;
  stagesProgress: StageProgress[];
  materiality: ComputedMateriality;
  overallPercent: number;
  onSelectStage: (stage: number) => void;
}

export const StageOverview: React.FC<StageOverviewProps> = ({
  engagement,
  stagesProgress,
  materiality,
  overallPercent,
  onSelectStage,
}) => {
  const pendingItems = getOutstandingItems(engagement);

  // Compute Risk heat counts
  const riskCounts: Record<RiskLevel, number> = {
    Low: 0,
    Moderate: 0,
    Significant: 0,
  };

  engagement.controlRiskRegister.forEach((cr) => {
    if (cr.finalRating in riskCounts) {
      riskCounts[cr.finalRating]++;
    }
  });

  const walkthroughsDone = engagement.walkthroughs.filter((w) => w.performed).length;
  const walkthroughsTotal = Math.max(1, engagement.walkthroughs.length);

  const fsRatedCount = engagement.fsLineItemRisks.filter((r) => r.inherentRisk !== '').length;
  const fsTotalCount = engagement.fsLineItemRisks.length;

  const strategiesDefined = engagement.auditStrategy.filter(
    (s) => (s.testOfControls || s.testOfDetails || s.analyticalProcedures) && s.proceduresNotes.trim().length > 5
  ).length;
  const strategiesTotal = Math.max(1, engagement.auditStrategy.length);

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-900 dark:bg-amber-950/70 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                Statutory Audit Planning
              </span>
              <span className="text-xs text-stone-500 font-mono-num">
                {engagement.financialYear}
              </span>
            </div>
            <h1 className="font-serif font-bold text-2xl text-stone-900 dark:text-stone-100">
              {engagement.clientName}
            </h1>
            <p className="text-xs text-stone-600 dark:text-stone-400 mt-1 max-w-2xl">
              Engagement Lead: <span className="font-semibold text-stone-800 dark:text-stone-200">{engagement.engagementPartner}</span> • Senior: <span className="font-semibold text-stone-800 dark:text-stone-200">{engagement.auditSenior}</span> • Preceding: {engagement.precedingAuditor}
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[10px] uppercase font-bold text-stone-400 tracking-wider block">
                Overall Progress
              </span>
              <span className="text-3xl font-serif font-bold text-amber-900 dark:text-amber-400 font-mono-num">
                {overallPercent}%
              </span>
            </div>
            <button
              onClick={() => {
                const nextIncomplete = stagesProgress.find((s) => s.percent < 100);
                if (nextIncomplete) onSelectStage(nextIncomplete.stageNumber);
                else onSelectStage(1);
              }}
              className="px-4 py-2 bg-amber-800 dark:bg-amber-600 hover:bg-amber-900 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-xs transition-colors"
            >
              <span>Continue Planning</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* 4 Stat Tiles */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Tile 1: Completion */}
        <div className="bg-white dark:bg-[#15191f] p-4 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex items-center gap-3.5">
          <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
            <TrendingUp className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-semibold uppercase text-stone-400 tracking-wider">
              Planning Completion
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono-num text-stone-900 dark:text-stone-100">
                {overallPercent}%
              </span>
              <span className="text-xs text-stone-500">of 13 stages</span>
            </div>
          </div>
        </div>

        {/* Tile 2: Walkthroughs */}
        <div className="bg-white dark:bg-[#15191f] p-4 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex items-center gap-3.5">
          <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300">
            <FileCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-semibold uppercase text-stone-400 tracking-wider">
              Walkthroughs Performed
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono-num text-stone-900 dark:text-stone-100">
                {walkthroughsDone} / {walkthroughsTotal}
              </span>
              <span className="text-xs text-stone-500">processes</span>
            </div>
          </div>
        </div>

        {/* Tile 3: FS Line Items */}
        <div className="bg-white dark:bg-[#15191f] p-4 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex items-center gap-3.5">
          <div className="p-3 rounded-lg bg-blue-50 dark:bg-blue-950/60 text-blue-800 dark:text-blue-300">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-semibold uppercase text-stone-400 tracking-wider">
              FS Line Items Rated
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono-num text-stone-900 dark:text-stone-100">
                {fsRatedCount} / {fsTotalCount}
              </span>
              <span className="text-xs text-stone-500">Sched III</span>
            </div>
          </div>
        </div>

        {/* Tile 4: Audit Responses */}
        <div className="bg-white dark:bg-[#15191f] p-4 rounded-xl border border-[#dedbd2] dark:border-[#272f38] shadow-xs flex items-center gap-3.5">
          <div className="p-3 rounded-lg bg-purple-50 dark:bg-purple-950/60 text-purple-800 dark:text-purple-300">
            <Compass className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-semibold uppercase text-stone-400 tracking-wider">
              Audit Responses Set
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono-num text-stone-900 dark:text-stone-100">
                {strategiesDefined} / {strategiesTotal}
              </span>
              <span className="text-xs text-stone-500">risks (SA 330)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Row: Risk Heat Strip & Materiality Snapshot */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Risk Heat Strip */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                Assessed Control Risk Heat Map (SA 315)
              </h3>
            </div>
            <button
              onClick={() => onSelectStage(9)}
              className="text-xs text-amber-700 dark:text-amber-400 font-semibold hover:underline flex items-center gap-1"
            >
              <span>View Register</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            {/* Low */}
            <div className="p-3 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800">
              <span className="text-[10px] uppercase font-bold text-emerald-800 dark:text-emerald-300 block tracking-wider">
                Low Risk
              </span>
              <span className="text-2xl font-bold font-mono-num text-emerald-900 dark:text-emerald-200">
                {riskCounts.Low}
              </span>
              <span className="text-[10px] text-emerald-700 dark:text-emerald-400 block mt-0.5">
                Matrix score 0-1
              </span>
            </div>

            {/* Moderate */}
            <div className="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800">
              <span className="text-[10px] uppercase font-bold text-amber-800 dark:text-amber-300 block tracking-wider">
                Moderate Risk
              </span>
              <span className="text-2xl font-bold font-mono-num text-amber-900 dark:text-amber-200">
                {riskCounts.Moderate}
              </span>
              <span className="text-[10px] text-amber-700 dark:text-amber-400 block mt-0.5">
                Matrix score 2
              </span>
            </div>

            {/* Significant */}
            <div className="p-3 rounded-lg bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800">
              <span className="text-[10px] uppercase font-bold text-rose-800 dark:text-rose-300 block tracking-wider">
                Significant Risk
              </span>
              <span className="text-2xl font-bold font-mono-num text-rose-900 dark:text-rose-200">
                {riskCounts.Significant}
              </span>
              <span className="text-[10px] text-rose-700 dark:text-rose-400 block mt-0.5">
                Score 3-4 (SA 330 TOD)
              </span>
            </div>
          </div>

          <div className="mt-4 text-xs text-stone-500 flex items-center justify-between">
            <span>Combination Formula: Probability (0-2) + Magnitude (0-2)</span>
            <span className="font-semibold text-stone-700 dark:text-stone-300">
              Total {engagement.controlRiskRegister.length} active risks
            </span>
          </div>
        </div>

        {/* Materiality Snapshot */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-amber-700 dark:text-amber-400" />
              <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
                Materiality Snapshot (SA 320 / SA 450)
              </h3>
            </div>
            <button
              onClick={() => onSelectStage(10)}
              className="text-xs text-amber-700 dark:text-amber-400 font-semibold hover:underline flex items-center gap-1"
            >
              <span>Adjust Inputs</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between p-2.5 rounded-md bg-stone-50 dark:bg-[#1a2027] border border-stone-200 dark:border-stone-800">
              <div>
                <span className="text-xs font-semibold text-stone-900 dark:text-stone-100 block">
                  Benchmark Basis: {engagement.materiality.benchmarkBasis}
                </span>
                <span className="text-[11px] text-stone-500 font-mono-num">
                  Amount: {formatINR(engagement.materiality.benchmarkAmount)}
                </span>
              </div>
              <span className="text-xs font-mono-num font-bold text-stone-700 dark:text-stone-300">
                {engagement.materiality.omPercent}% applied
              </span>
            </div>

            <div className="grid grid-cols-3 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-amber-50/70 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800">
                <span className="text-[10px] text-stone-500 block uppercase">Overall Mat.</span>
                <span className="font-mono-num font-bold text-stone-900 dark:text-stone-100 block">
                  {formatCompactINR(materiality.overallMateriality)}
                </span>
              </div>
              <div className="p-2 rounded bg-amber-100/70 dark:bg-amber-900/40 border border-amber-300 dark:border-amber-700">
                <span className="text-[10px] text-stone-500 block uppercase">Perf. Mat. (PM)</span>
                <span className="font-mono-num font-bold text-amber-900 dark:text-amber-200 block">
                  {formatCompactINR(materiality.performanceMateriality)}
                </span>
              </div>
              <div className="p-2 rounded bg-stone-100 dark:bg-stone-800 border border-stone-200 dark:border-stone-700">
                <span className="text-[10px] text-stone-500 block uppercase">Clearly Trivial</span>
                <span className="font-mono-num font-bold text-stone-700 dark:text-stone-300 block">
                  {formatCompactINR(materiality.clearlyTrivialThreshold)}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Row: Outstanding Action Items & Stage Progress List */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Outstanding Items (1 col) */}
        <div className="bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs flex flex-col">
          <div className="flex items-center gap-2 mb-3">
            <ListTodo className="w-4 h-4 text-rose-700 dark:text-rose-400" />
            <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100">
              Outstanding Planning Items
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2">
            {pendingItems.length === 0 ? (
              <div className="p-4 text-center text-xs text-stone-500">
                <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
                <p className="font-semibold text-emerald-800 dark:text-emerald-300">
                  All standard audit planning items completed!
                </p>
                <p className="text-[11px] mt-1">Ready for engagement partner review and approval.</p>
              </div>
            ) : (
              pendingItems.map((item, idx) => (
                <div
                  key={idx}
                  onClick={() => onSelectStage(item.stageNumber)}
                  className="p-3 rounded-lg border border-stone-200 dark:border-stone-800 hover:border-amber-700 dark:hover:border-amber-500 cursor-pointer transition-colors bg-stone-50/50 dark:bg-[#1a2027]"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-400">
                      Stage {item.stageNumber}: {item.stageName}
                    </span>
                    <span
                      className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${
                        item.urgency === 'High'
                          ? 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
                          : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300'
                      }`}
                    >
                      {item.urgency}
                    </span>
                  </div>
                  <p className="text-xs text-stone-700 dark:text-stone-300 font-medium">
                    {item.itemText}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 13 Stages Progress List (2 cols) */}
        <div className="lg:col-span-2 bg-white dark:bg-[#15191f] rounded-xl border border-[#dedbd2] dark:border-[#272f38] p-5 shadow-xs">
          <h3 className="font-serif font-bold text-base text-stone-900 dark:text-stone-100 mb-3">
            Planning Stages Progress Breakdown
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {stagesProgress.map((sp) => (
              <div
                key={sp.stageNumber}
                onClick={() => onSelectStage(sp.stageNumber)}
                className="p-3 rounded-lg border border-stone-200 dark:border-stone-800 hover:bg-stone-50 dark:hover:bg-stone-800/50 cursor-pointer transition-colors flex items-center justify-between"
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-2">
                  <span className="font-mono-num text-xs font-bold w-6 h-6 rounded bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 flex items-center justify-center shrink-0">
                    {sp.stageNumber}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-stone-800 dark:text-stone-200 truncate">
                      {sp.shortTitle}
                    </p>
                    <p className="text-[10px] text-stone-400 truncate">
                      {sp.saRef}
                    </p>
                  </div>
                </div>

                <div className="text-right shrink-0">
                  <div className="flex items-center gap-2">
                    <div className="w-12 h-1.5 rounded-full bg-stone-200 dark:bg-stone-700 overflow-hidden">
                      <div
                        className={`h-full ${sp.percent === 100 ? 'bg-emerald-600' : 'bg-amber-600'}`}
                        style={{ width: `${sp.percent}%` }}
                      />
                    </div>
                    <span className="font-mono-num text-xs font-bold text-stone-700 dark:text-stone-300 w-8 text-right">
                      {sp.percent}%
                    </span>
                  </div>
                  <span className="text-[10px] text-stone-400 font-mono-num">
                    {sp.doneCount}/{sp.totalCount} items
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
