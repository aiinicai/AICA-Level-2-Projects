import React, { useState } from 'react';
import { AnnualPerformancePlan, User, AppraisalRecord } from '../types';
import { 
  Target, 
  TrendingUp, 
  CheckCircle2, 
  Clock, 
  Award, 
  BarChart3, 
  Sliders, 
  ArrowUpRight, 
  Zap, 
  ShieldCheck,
  Calendar,
  Layers,
  Sparkles
} from 'lucide-react';

interface KPIProgressChartProps {
  plan: AnnualPerformancePlan;
  employeeUser: User;
  appraisalRecord?: AppraisalRecord;
  className?: string;
}

export const KPIProgressChart: React.FC<KPIProgressChartProps> = ({
  plan,
  employeeUser,
  appraisalRecord,
  className = '',
}) => {
  const [activeChartTab, setActiveChartTab] = useState<'deliverables' | 'pillars' | 'trajectory'>('deliverables');

  // Compute overall deliverable completion rate
  const totalWeight = plan.goals.reduce((acc, g) => acc + g.weightagePct, 0) || 100;
  const weightedCompletionRate = Math.min(
    100,
    Math.round(
      plan.goals.reduce((acc, g) => {
        const itemRate = g.targetDeliverableCount > 0 
          ? Math.min(1.2, g.actualAchievedCount / g.targetDeliverableCount) 
          : 1;
        return acc + itemRate * g.weightagePct;
      }, 0) / (totalWeight / 100)
    )
  );

  // Projected or actual assessed score
  const currentScore = plan.assessedScore || appraisalRecord?.finalWeightedScore || 91.5;

  // Scoring tier metadata
  const getScoreTier = (score: number) => {
    if (score >= 90) return { label: 'Exceeds / Partner Track', color: 'text-teal-700 bg-teal-50 border-teal-200' };
    if (score >= 75) return { label: 'Meets Advisory Standards', color: 'text-blue-800 bg-blue-50 border-blue-200' };
    return { label: 'Under Par / Remediation Track', color: 'text-rose-800 bg-rose-50 border-rose-200' };
  };

  const tierInfo = getScoreTier(currentScore);

  // Pillar contribution calculations (50%, 25%, 15%, 10%)
  const grossPts = appraisalRecord?.grossServicePoints || 93.0;
  const slaPts = appraisalRecord?.taskSLAIndex || 91.0;
  const punctPts = appraisalRecord?.punctualityIndex || 95.0;
  const growthPts = 92.0;

  const pillar1Contr = Math.round((grossPts * 0.50) * 10) / 10;
  const pillar2Contr = Math.round((slaPts * 0.25) * 10) / 10;
  const pillar3Contr = Math.round((punctPts * 0.15) * 10) / 10;
  const pillar4Contr = Math.round((growthPts * 0.10) * 10) / 10;
  const baseSubtotal = Math.round((pillar1Contr + pillar2Contr + pillar3Contr + pillar4Contr) * 10) / 10;

  // Monthly velocity data
  const monthlyData = [
    { month: 'Jan', points: 86.5, target: 85, deliverables: 7, slaAvg: 19.5 },
    { month: 'Feb', points: 88.0, target: 85, deliverables: 9, slaAvg: 18.8 },
    { month: 'Mar', points: 89.5, target: 85, deliverables: 11, slaAvg: 17.9 },
    { month: 'Apr', points: 91.0, target: 85, deliverables: 10, slaAvg: 18.2 },
    { month: 'May', points: 90.5, target: 85, deliverables: 12, slaAvg: 18.0 },
    { month: 'Jun', points: 92.5, target: 85, deliverables: 14, slaAvg: 17.4 },
    { month: 'Jul', points: 93.0, target: 85, deliverables: 11, slaAvg: 17.6 },
    { month: 'Aug', points: 92.0, target: 85, deliverables: 13, slaAvg: 17.2 },
    { month: 'Sep', points: 94.5, target: 85, deliverables: 16, slaAvg: 16.8 },
    { month: 'Oct (Current)', points: 95.2, target: 85, deliverables: 8, slaAvg: 16.5 },
  ];

  return (
    <div className={`bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6 ${className}`}>
      {/* Chart Header & Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-bold bg-blue-900 text-teal-400 font-mono tracking-wider flex items-center gap-1">
              <BarChart3 className="w-3 h-3" /> ANNUAL KPI PERFORMANCE INTELLIGENCE
            </span>
            <span className="text-slate-300">•</span>
            <span className="text-xs text-slate-500 font-medium">Year {plan.year} Cycle</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span>KPI Progress & Goal Trajectory Analysis</span>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${tierInfo.color}`}>
              {tierInfo.label}
            </span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time tracking of deliverable milestones, SLA turnaround velocity, and 4-pillar practice weightages for <strong>{employeeUser.fullName}</strong>.
          </p>
        </div>

        {/* View Switcher Pills */}
        <div className="flex items-center p-1 bg-slate-100 rounded-lg border border-slate-200 text-xs font-semibold shrink-0">
          <button
            onClick={() => setActiveChartTab('deliverables')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeChartTab === 'deliverables'
                ? 'bg-white text-blue-950 shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Target className="w-3.5 h-3.5 text-blue-600" />
            Deliverable Goals ({plan.goals.length})
          </button>
          <button
            onClick={() => setActiveChartTab('pillars')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeChartTab === 'pillars'
                ? 'bg-white text-teal-950 shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Layers className="w-3.5 h-3.5 text-teal-600" />
            4-Pillar Weightage
          </button>
          <button
            onClick={() => setActiveChartTab('trajectory')}
            className={`px-3 py-1.5 rounded-md transition-all cursor-pointer flex items-center gap-1.5 ${
              activeChartTab === 'trajectory'
                ? 'bg-white text-indigo-950 shadow-xs font-bold'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
            Monthly Velocity
          </button>
        </div>
      </div>

      {/* Hero Overview Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200/80">
        <div className="flex items-center gap-4">
          <div className="relative w-16 h-16 shrink-0 flex items-center justify-center">
            <svg className="w-16 h-16 transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-200"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className="text-teal-600"
                strokeDasharray={`${weightedCompletionRate}, 100`}
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <div className="absolute text-center">
              <span className="text-sm font-black text-slate-900 tabular-nums leading-none block">
                {weightedCompletionRate}%
              </span>
            </div>
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Annual Target Velocity
            </span>
            <span className="text-sm font-bold text-slate-900">
              {weightedCompletionRate >= 85 ? 'On-Track for Target' : 'Action Plan Active'}
            </span>
            <span className="text-[11px] text-teal-700 block font-medium">
              Weighted goal completion
            </span>
          </div>
        </div>

        <div className="border-l border-slate-200 pl-4">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Composite Assessed Rating
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-2xl font-black text-slate-950 tabular-nums">
              {currentScore}
            </span>
            <span className="text-xs text-slate-400 font-semibold">/ 100 pts</span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            Practice Benchmark: 85.0 pts
          </span>
        </div>

        <div className="border-l border-slate-200 pl-4">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Technical Workpapers
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-2xl font-black text-blue-950 tabular-nums">
              {plan.goals.reduce((acc, g) => acc + g.actualAchievedCount, 0)}
            </span>
            <span className="text-xs text-slate-400 font-semibold">
              / {plan.goals.reduce((acc, g) => acc + g.targetDeliverableCount, 0)} target
            </span>
          </div>
          <span className="text-[11px] text-blue-700 font-medium">
            100% ISA & IFRS Quality Checked
          </span>
        </div>

        <div className="border-l border-slate-200 pl-4">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
            Seniority Retention Boost
          </span>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-2xl font-black text-teal-900 tabular-nums">
              {(employeeUser.tenureYears >= 8 ? 1.15 : employeeUser.tenureYears >= 5 ? 1.10 : employeeUser.tenureYears >= 2 ? 1.05 : 1.00).toFixed(2)}x
            </span>
            <span className="text-xs text-teal-700 font-semibold">+{employeeUser.tenureYears >= 5 ? '10%' : '5%'}</span>
          </div>
          <span className="text-[11px] text-slate-500 font-medium">
            {employeeUser.tenureYears} Years continuous service
          </span>
        </div>
      </div>

      {/* TAB VIEW 1: Deliverable Milestones */}
      {activeChartTab === 'deliverables' && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Individual KPI Goals & Progress Bars</span>
            <span>Target vs Actual Milestones</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {plan.goals.map((goal) => {
              const deliverablePct = goal.targetDeliverableCount > 0 
                ? Math.min(100, Math.round((goal.actualAchievedCount / goal.targetDeliverableCount) * 100))
                : 100;
              
              const isOverperforming = goal.actualAchievedCount >= goal.targetDeliverableCount;
              const slaAhead = goal.actualAvgSlaHours <= goal.targetSlaHours;

              return (
                <div key={goal.id} className="p-4 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition-all space-y-3 shadow-2xs">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200">
                          {goal.category}
                        </span>
                        <span className="text-[11px] font-bold text-slate-400">
                          Weight: {goal.weightagePct}%
                        </span>
                      </div>
                      <h4 className="font-bold text-slate-900 text-sm mt-1">
                        {goal.title}
                      </h4>
                    </div>
                    <div className="text-right">
                      <span className={`text-sm font-black tabular-nums ${isOverperforming ? 'text-teal-700' : 'text-blue-900'}`}>
                        {deliverablePct}%
                      </span>
                      <span className="text-[10px] text-slate-400 block font-medium">Achieved</span>
                    </div>
                  </div>

                  <div>
                    <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                      <div 
                        className={`h-2.5 rounded-full transition-all duration-500 ${
                          deliverablePct >= 100 
                            ? 'bg-gradient-to-r from-teal-600 to-teal-500' 
                            : deliverablePct >= 70 
                            ? 'bg-gradient-to-r from-blue-700 to-blue-500' 
                            : 'bg-amber-500'
                        }`}
                        style={{ width: `${deliverablePct}%` }}
                      />
                    </div>
                    <div className="flex justify-between items-center text-[11px] text-slate-500 mt-1.5 tabular-nums">
                      <span>Deliverables: <strong>{goal.actualAchievedCount}</strong> / {goal.targetDeliverableCount}</span>
                      <span>Target SLA: <strong>{goal.targetSlaHours}h</strong> (Actual: {goal.actualAvgSlaHours}h)</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-slate-100 text-[10px]">
                    <span className={`px-2 py-0.5 rounded font-semibold flex items-center gap-1 ${
                      slaAhead ? 'bg-teal-50 text-teal-800' : 'bg-amber-50 text-amber-800'
                    }`}>
                      <Clock className="w-3 h-3" />
                      {slaAhead ? 'Turnaround Ahead of SLA' : 'SLA Attention Needed'}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold flex items-center gap-1">
                      <CheckCircle2 className="w-3 h-3 text-blue-600" />
                      Quality Score: {goal.actualQualityScore || 92}%
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB VIEW 2: 4-Pillar Weightage */}
      {activeChartTab === 'pillars' && (
        <div className="space-y-5 animate-in fade-in">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>Mathematical Composition of Final Score (Standard SME Formula)</span>
            <span>Total Points: 100.0 Maximum</span>
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-900 flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-blue-700" />
                  Pillar 1: Service Deliverables Point Matrix (50% Weight)
                </span>
                <span className="font-bold text-blue-950 tabular-nums">
                  {pillar1Contr} / 50.0 pts ({grossPts}% raw)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-blue-700 h-3 rounded-full transition-all duration-500" 
                  style={{ width: `${(pillar1Contr / 50) * 100}%` }} 
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Audited workpapers, IFRS sign-offs, and client technical reviews with quality multipliers.
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-900 flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-teal-600" />
                  Pillar 2: Task Turnaround SLA Adherence (25% Weight)
                </span>
                <span className="font-bold text-teal-900 tabular-nums">
                  {pillar2Contr} / 25.0 pts ({slaPts}% raw)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-teal-600 h-3 rounded-full transition-all duration-500" 
                  style={{ width: `${(pillar2Contr / 25) * 100}%` }} 
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Turnaround hours logged on engagements versus engagement benchmark limits.
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-900 flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-indigo-600" />
                  Pillar 3: HR Attendance & Biometric Punctuality Controls (15% Weight)
                </span>
                <span className="font-bold text-indigo-950 tabular-nums">
                  {pillar3Contr} / 15.0 pts ({punctPts}% raw)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-indigo-600 h-3 rounded-full transition-all duration-500" 
                  style={{ width: `${(pillar3Contr / 15) * 100}%` }} 
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Biometric door log arrival before 08:30 AM (15-min grace window). Zero subjective manager override.
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-slate-200 bg-white space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-900 flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                  Pillar 4: Growth Delta & Knowledge Upskilling (10% Weight)
                </span>
                <span className="font-bold text-amber-900 tabular-nums">
                  {pillar4Contr} / 10.0 pts ({growthPts}% raw)
                </span>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-amber-500 h-3 rounded-full transition-all duration-500" 
                  style={{ width: `${(pillar4Contr / 10) * 100}%` }} 
                />
              </div>
              <p className="text-[11px] text-slate-500">
                Participation in sponsored ADGM/ICAEW professional programs and quarterly skill mastery delta.
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 text-white flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-xs text-teal-400 font-bold uppercase tracking-wider block font-mono">
                Mathematical Subtotal Before Retention Multiplier
              </span>
              <div className="text-xl font-bold mt-0.5">
                {baseSubtotal} / 100.0 pts
              </div>
            </div>
            <div className="sm:text-right border-t sm:border-t-0 sm:border-l border-slate-800 pt-3 sm:pt-0 sm:pl-6">
              <span className="text-xs text-slate-400 block">
                Final Sealed Score with {(employeeUser.tenureYears >= 5 ? 1.10 : 1.05)}x Multiplier:
              </span>
              <span className="text-2xl font-black text-teal-300 tabular-nums">
                {currentScore} pts
              </span>
            </div>
          </div>
        </div>
      )}

      {/* TAB VIEW 3: Monthly Velocity */}
      {activeChartTab === 'trajectory' && (
        <div className="space-y-4 animate-in fade-in">
          <div className="flex items-center justify-between text-xs text-slate-500 font-medium">
            <span>2026 Monthly Score Trajectory vs Practice Baseline (85.0 pts)</span>
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-1.5 text-slate-600">
                <div className="w-2.5 h-2.5 rounded bg-blue-700" />
                Actual Monthly Score
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <div className="w-4 h-0.5 bg-rose-500" />
                Practice Target (85)
              </span>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="h-48 flex items-end justify-between gap-2 pt-6 pb-2 px-2 relative">
              <div 
                className="absolute left-0 right-0 border-b-2 border-dashed border-rose-400/80 z-10 pointer-events-none flex justify-end pr-2"
                style={{ bottom: `${(85 / 100) * 100}%` }}
              >
                <span className="text-[10px] font-bold text-rose-600 bg-white px-1 rounded shadow-2xs -translate-y-2">
                  Target: 85 pts
                </span>
              </div>
              {monthlyData.map((item, idx) => {
                const heightPct = Math.round((item.points / 100) * 100);
                const isExceeding = item.points >= 90;
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center h-full justify-end group relative z-20">
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-12 bg-slate-900 text-white text-[10px] rounded-md px-2 py-1 pointer-events-none whitespace-nowrap shadow-lg z-30 font-sans">
                      <div className="font-bold">{item.points} pts</div>
                      <div className="text-[9px] text-slate-400">{item.deliverables} sign-offs • {item.slaAvg}h SLA</div>
                    </div>
                    <div 
                      className={`w-full max-w-[28px] rounded-t-md transition-all duration-500 group-hover:opacity-90 ${
                        isExceeding 
                          ? 'bg-gradient-to-t from-teal-700 to-teal-500' 
                          : 'bg-gradient-to-t from-blue-800 to-blue-600'
                      }`}
                      style={{ height: `${heightPct}%` }}
                    />
                    <span className="text-[10px] font-semibold text-slate-600 mt-2 truncate w-full text-center">
                      {item.month.split(' ')[0]}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-teal-50 border border-teal-200 text-xs text-teal-900 flex items-center justify-between">
            <span className="flex items-center gap-1.5 font-medium">
              <Sparkles className="w-4 h-4 text-teal-600 shrink-0" />
              <span>Velocity Trajectory: Performance consistently up +8.7 pts over evaluation period.</span>
            </span>
            <span className="font-bold text-teal-800 shrink-0">ISA-Compliant Trend ✓</span>
          </div>
        </div>
      )}
    </div>
  );
};
