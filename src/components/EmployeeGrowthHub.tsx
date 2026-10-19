import React from 'react';
import { 
  User, 
  AppraisalRecord, 
  TaskEvaluation, 
  AttendanceRecord, 
  TrainingRecommendation, 
  CoachingNote,
  AnnualPerformancePlan
} from '../types';
import { 
  calculatePerformanceScore, 
  getLoyaltyTierInfo, 
  getTierMetadata 
} from '../utils/scoringEngine';
import { 
  TrendingUp, 
  Clock, 
  Award, 
  BookOpen, 
  Calendar, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  ArrowUpRight,
  ShieldCheck,
  ChevronRight,
  Send,
  MessageSquare,
  Download,
  Printer
} from 'lucide-react';
import { exportToWord, exportToPdf, generateAppraisalReportHtml } from '../utils/reportExporter';
import { KPIProgressChart } from './KPIProgressChart';

interface EmployeeGrowthHubProps {
  user: User;
  appraisalRecord?: AppraisalRecord;
  evaluations: TaskEvaluation[];
  attendanceRecords: AttendanceRecord[];
  trainingRecommendations: TrainingRecommendation[];
  coachingNotes: CoachingNote[];
  annualPlan?: AnnualPerformancePlan;
  onEnrollTraining: (recId: string) => void;
  onOpenSimulator: () => void;
  onOpenCompliance: () => void;
  onOpenMatrix?: () => void;
}

export const EmployeeGrowthHub: React.FC<EmployeeGrowthHubProps> = ({
  user,
  appraisalRecord,
  evaluations,
  attendanceRecords,
  trainingRecommendations,
  coachingNotes,
  annualPlan,
  onEnrollTraining,
  onOpenSimulator,
  onOpenCompliance,
  onOpenMatrix,
}) => {
  // Compute score breakdown using scoring engine
  const scoreData = calculatePerformanceScore({
    serviceDeliveryPoints: appraisalRecord?.grossServicePoints ?? 88,
    taskSLAPunctuality: appraisalRecord?.taskSLAIndex ?? 90,
    officeAttendancePunctuality: appraisalRecord?.punctualityIndex ?? 92,
    growthDeltaPct: appraisalRecord?.growthDeltaPct ?? 8.5,
    tenureYears: user.tenureYears,
    consecutiveUnderperformingCycles: appraisalRecord?.consecutiveUnderperformingCycles ?? 0,
  });

  const loyaltyTier = getLoyaltyTierInfo(user.tenureYears);
  const tierMeta = getTierMetadata(scoreData.performanceTier);

  const [activeAttendanceFilter, setActiveAttendanceFilter] = React.useState<'all' | 'ontime' | 'late'>('all');

  const filteredAttendance = attendanceRecords.filter((record) => {
    if (activeAttendanceFilter === 'ontime') return record.status === 'On-Time';
    if (activeAttendanceFilter === 'late') return record.status !== 'On-Time';
    return true;
  });

  const [aiSynthesis, setAiSynthesis] = React.useState<any | null>(null);
  const [isGeneratingAi, setIsGeneratingAi] = React.useState<boolean>(false);

  const handleGenerateAiSynthesis = async () => {
    setIsGeneratingAi(true);
    try {
      const { generateExecutivePerformanceSynthesis } = await import('../services/geminiService');
      const result = await generateExecutivePerformanceSynthesis(
        user,
        appraisalRecord || {
          id: 'temp',
          cycleId: 'cycle-q3-2026',
          cycleName: '2026 Annual Cycle',
          employeeId: user.id,
          employeeName: user.fullName,
          departmentId: user.departmentId,
          grossServicePoints: scoreData.serviceDeliveryPoints,
          punctualityIndex: scoreData.officeAttendancePunctuality,
          taskSLAIndex: scoreData.taskSLAPunctuality,
          growthDeltaPct: scoreData.growthDeltaPct,
          tenureYears: user.tenureYears,
          tenureLoyaltyMultiplier: scoreData.loyaltyMultiplier,
          baseScore: scoreData.baseScore,
          finalWeightedScore: scoreData.finalWeightedScore,
          performanceTier: scoreData.performanceTier,
          actionPlanStatus: scoreData.actionPlanStatus,
          consecutiveUnderperformingCycles: 0,
          coachingNotes: [],
          hrApprovalStatus: 'Approved',
          lastEvaluationDate: new Date().toISOString().split('T')[0],
        },
        annualPlan
      );
      setAiSynthesis(result);
    } catch (e) {
      console.warn('AI synthesis notice:', e);
    } finally {
      setIsGeneratingAi(false);
    }
  };

  const handleExportScorecardWord = () => {
    if (!appraisalRecord) return;
    const html = generateAppraisalReportHtml(appraisalRecord, user, user.managerName || 'Tariq Al Hammadi');
    exportToWord({
      title: `Appraisal Scorecard: ${user.fullName}`,
      subtitle: `${user.currentDesignation} • ${user.departmentName} • Paras Advisory`,
      filename: `Appraisal_Scorecard_${user.fullName.replace(/\s+/g, '_')}_2026`,
      officialRefCode: `PAA-APP-2026-${user.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  const handleExportScorecardPdf = () => {
    if (!appraisalRecord) return;
    const html = generateAppraisalReportHtml(appraisalRecord, user, user.managerName || 'Tariq Al Hammadi');
    exportToPdf({
      title: `Appraisal Scorecard: ${user.fullName}`,
      subtitle: `${user.currentDesignation} • ${user.departmentName} • Paras Advisory`,
      filename: `Appraisal_Scorecard_${user.fullName.replace(/\s+/g, '_')}_2026`,
      officialRefCode: `PAA-APP-2026-${user.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Welcome & Employee Snapshot */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-900 to-teal-700 text-white font-bold text-xl flex items-center justify-center shadow-xs">
              {user.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">{user.fullName}</h1>
                <span className="text-xs font-mono text-slate-400 tabular-nums">({user.employeeIdCode})</span>
              </div>
              <p className="text-sm font-medium text-slate-600 mt-0.5">{user.currentDesignation}</p>
              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-slate-500">
                <span className="text-blue-900 font-semibold">{user.departmentName}</span>
                <span aria-hidden="true">•</span>
                <span>Reporting to {user.managerName || 'Division Lead'}</span>
                <span aria-hidden="true">•</span>
                <span>{user.officeLocation}</span>
                <span aria-hidden="true">•</span>
                <span className="font-medium text-teal-700 tabular-nums">{user.tenureYears} Years Service</span>
              </div>
            </div>
          </div>

          {/* Loyalty Badge & Actions */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            <div className="px-4 py-3 rounded-lg bg-teal-50 border border-teal-200/80">
              <div className="flex items-center gap-2">
                <Award className="w-4 h-4 text-teal-700" />
                <span className="text-xs font-bold text-teal-900 uppercase tracking-wider">
                  {loyaltyTier.tierName}
                </span>
              </div>
              <div className="text-sm font-semibold text-teal-800 mt-1 flex items-center gap-1.5">
                <span className="tabular-nums">{loyaltyTier.boostPct}</span> Loyalty Multiplier
                <span className="text-xs text-teal-600 font-normal">applied to final score</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {appraisalRecord && (
                <>
                  <button
                    onClick={handleExportScorecardWord}
                    className="px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    title="Download official appraisal scorecard in Word format"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-700" />
                    Word (.doc)
                  </button>
                  <button
                    onClick={handleExportScorecardPdf}
                    className="px-3 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    title="Print or Save appraisal scorecard as PDF"
                  >
                    <Printer className="w-3.5 h-3.5 text-teal-700" />
                    PDF
                  </button>
                </>
              )}
              <button
                onClick={handleGenerateAiSynthesis}
                disabled={isGeneratingAi}
                className="px-3.5 py-2.5 rounded-lg bg-gradient-to-r from-blue-900 to-indigo-900 hover:from-blue-800 hover:to-indigo-800 text-white font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                title="Synthesize performance insights via Gemini 2.5 Flash"
              >
                <Sparkles className="w-3.5 h-3.5 text-teal-400" />
                {isGeneratingAi ? 'Synthesizing...' : 'AI Executive Insights'}
              </button>
              <button
                onClick={onOpenSimulator}
                className="px-3.5 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-50 transition-colors flex items-center gap-1.5 cursor-pointer"
              >
                Simulate
                <ArrowUpRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* AI Executive Talent Synthesis Panel (Powered by Gemini) */}
      {aiSynthesis && (
        <div className="bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 text-white rounded-2xl p-6 border border-slate-800 shadow-xl space-y-4 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-teal-500/20 border border-teal-400/30 flex items-center justify-center text-teal-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <span>Gemini Executive Talent & Governance Synthesis</span>
                  <span className="text-[10px] font-mono font-normal bg-teal-900/60 text-teal-300 px-2 py-0.5 rounded border border-teal-700/50">
                    gemini-2.5-flash
                  </span>
                </h3>
                <p className="text-[11px] text-slate-400">
                  Domain synthesis grounded in ISA 230 audit standards and UAE Federal Decree-Law No. 33 of 2021
                </p>
              </div>
            </div>
            <button
              onClick={() => setAiSynthesis(null)}
              className="text-slate-400 hover:text-white text-xs cursor-pointer px-2 py-1"
            >
              ✕ Close
            </button>
          </div>

          <p className="text-xs text-slate-200 leading-relaxed bg-slate-950/40 p-3.5 rounded-xl border border-slate-800">
            "{aiSynthesis.executiveSummary}"
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div className="space-y-2 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
              <span className="font-bold text-teal-300 text-[11px] uppercase tracking-wider block">
                Observed Core Strengths
              </span>
              <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                {aiSynthesis.strengths?.map((s: string, idx: number) => (
                  <li key={idx}>{s}</li>
                ))}
              </ul>
            </div>

            <div className="space-y-2 bg-slate-900/60 p-3.5 rounded-xl border border-slate-800">
              <span className="font-bold text-amber-300 text-[11px] uppercase tracking-wider block">
                Development & Mentoring Priorities
              </span>
              <ul className="space-y-1.5 list-disc list-inside text-slate-300 text-[11px]">
                {aiSynthesis.remediationAreas?.map((r: string, idx: number) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-[11px] pt-1">
            <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
              <span className="text-slate-400 block font-semibold">Statutory Standing:</span>
              <span className="text-teal-400 font-medium">{aiSynthesis.statutoryComplianceStatus}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
              <span className="text-slate-400 block font-semibold">Recommended Path:</span>
              <span className="text-slate-200">{aiSynthesis.recommendedLearningModule}</span>
            </div>
            <div className="p-2.5 rounded-lg bg-slate-800/40 border border-slate-800">
              <span className="text-slate-400 block font-semibold">Retention Decision:</span>
              <span className="text-emerald-400 font-medium">{aiSynthesis.retentionRecommendation}</span>
            </div>
          </div>
        </div>
      )}

      {/* Grid: Performance Scorecard + Loyalty Stepper */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Performance Scorecard
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">Active Cycle: Q3-2026 Evaluation</p>
              </div>
              <span className={`text-xs px-2.5 py-1 rounded-md font-semibold border ${tierMeta.colorClass}`}>
                {tierMeta.label}
              </span>
            </div>

            {/* Circular Progress Ring & Scores */}
            <div className="my-6 flex flex-col sm:flex-row items-center justify-center gap-6">
              <div className="relative w-36 h-36 flex items-center justify-center">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    stroke="#E2E8F0"
                    strokeWidth="8"
                    fill="transparent"
                  />
                  <circle
                    cx="50"
                    cy="50"
                    r="42"
                    stroke="#0D9488"
                    strokeWidth="8"
                    strokeDasharray={264}
                    strokeDashoffset={264 - (264 * Math.min(100, scoreData.finalWeightedScore)) / 100}
                    strokeLinecap="round"
                    fill="transparent"
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className="text-3xl font-extrabold text-slate-900 tabular-nums">
                    {scoreData.finalWeightedScore}
                  </span>
                  <span className="text-[11px] font-semibold text-teal-700 tracking-wider">
                    FINAL PTS
                  </span>
                </div>
              </div>

              <div className="space-y-2 text-center sm:text-left">
                <div>
                  <div className="text-xs text-slate-500">Unweighted Base Score</div>
                  <div className="text-lg font-bold text-slate-800 tabular-nums">
                    {scoreData.baseScore} <span className="text-xs font-normal text-slate-400">/ 100</span>
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Tenure Multiplier</div>
                  <div className="text-sm font-semibold text-teal-700 tabular-nums flex items-center gap-1 justify-center sm:justify-start">
                    <Sparkles className="w-3.5 h-3.5" />
                    {scoreData.loyaltyMultiplier.toFixed(2)}x ({user.tenureYears} yrs)
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-500">Cycle Improvement Delta</div>
                  <div className="text-sm font-semibold text-emerald-600 tabular-nums flex items-center gap-1 justify-center sm:justify-start">
                    <TrendingUp className="w-3.5 h-3.5" />
                    +{scoreData.growthDeltaPct}% vs Q2
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Point Matrix Breakdown */}
          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200/60 space-y-2.5 text-xs">
            <div className="flex justify-between items-center text-slate-600">
              <span>Service Delivery Deliverables (50%)</span>
              <span className="font-semibold text-slate-900 tabular-nums">
                {scoreData.serviceDeliveryPoints} pts • {scoreData.weightedServicePoints}
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-blue-700 h-1.5 rounded-full" 
                style={{ width: `${Math.min(100, scoreData.serviceDeliveryPoints)}%` }} 
              />
            </div>

            <div className="flex justify-between items-center text-slate-600 pt-1">
              <span>Task SLA Turnaround Punctuality (25%)</span>
              <span className="font-semibold text-slate-900 tabular-nums">
                {scoreData.taskSLAPunctuality} pts • {scoreData.weightedTaskSLA}
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-teal-600 h-1.5 rounded-full" 
                style={{ width: `${Math.min(100, scoreData.taskSLAPunctuality)}%` }} 
              />
            </div>

            <div className="flex justify-between items-center text-slate-600 pt-1">
              <span>Office Attendance Punctuality (15%)</span>
              <span className="font-semibold text-slate-900 tabular-nums">
                {scoreData.officeAttendancePunctuality} pts • {scoreData.weightedAttendance}
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-indigo-600 h-1.5 rounded-full" 
                style={{ width: `${Math.min(100, scoreData.officeAttendancePunctuality)}%` }} 
              />
            </div>

            <div className="flex justify-between items-center text-slate-600 pt-1">
              <span>Growth / Improvement Delta (10%)</span>
              <span className="font-semibold text-slate-900 tabular-nums">
                {scoreData.growthDeltaScore} pts • {scoreData.weightedGrowth}
              </span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-1.5 overflow-hidden">
              <div 
                className="bg-emerald-600 h-1.5 rounded-full" 
                style={{ width: `${Math.min(100, scoreData.growthDeltaScore)}%` }} 
              />
            </div>
          </div>
        </div>

        {/* Loyalty Milestones */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <Award className="w-4 h-4 text-teal-600" />
                  Tenure Excellence & Retention Milestones
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Automated multiplier boost recognizing long-serving institutional experience
                </p>
              </div>
              <span className="text-xs font-mono text-teal-800 bg-teal-50 border border-teal-200 px-2.5 py-1 rounded-md font-semibold tabular-nums">
                {user.tenureYears} Years Active
              </span>
            </div>

            <div className="mt-6 space-y-4">
              <div className={`p-4 rounded-lg border transition-all ${user.tenureYears < 2 ? 'border-blue-400 bg-blue-50/40 ring-1 ring-blue-300' : 'border-slate-200 bg-slate-50/60'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${user.tenureYears >= 2 ? 'bg-teal-600 text-white' : 'bg-blue-600 text-white'}`}>
                      {user.tenureYears >= 2 ? '✓' : '1'}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900">0 – 2 Years — Foundation Tier</div>
                      <div className="text-[11px] text-slate-500">Base Evaluation Multiplier (1.00x)</div>
                    </div>
                  </div>
                  <span className="text-xs font-semibold text-slate-600 tabular-nums">1.00x Multiplier</span>
                </div>
              </div>

              <div className={`p-4 rounded-lg border transition-all ${user.tenureYears >= 2 && user.tenureYears < 5 ? 'border-teal-500 bg-teal-50/60 ring-1 ring-teal-400' : user.tenureYears >= 5 ? 'border-slate-200 bg-slate-50/60' : 'border-dashed border-slate-200 opacity-60'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${user.tenureYears >= 5 ? 'bg-teal-600 text-white' : user.tenureYears >= 2 ? 'bg-teal-700 text-white' : 'bg-slate-300 text-slate-600'}`}>
                      {user.tenureYears >= 5 ? '✓' : '2'}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                        2 – 5 Years — Growth Contributor Tier
                        {user.tenureYears >= 2 && user.tenureYears < 5 && (
                          <span className="text-[10px] bg-teal-600 text-white font-bold px-1.5 py-0.5 rounded">
                            CURRENT
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500">+5% Score Loyalty Multiplier</div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-teal-800 tabular-nums">+5% Multiplier (1.05x)</span>
                </div>
              </div>

              <div className={`p-4 rounded-lg border transition-all ${user.tenureYears >= 5 && user.tenureYears < 8 ? 'border-teal-500 bg-teal-50/60 ring-1 ring-teal-400' : user.tenureYears >= 8 ? 'border-slate-200 bg-slate-50/60' : 'border-dashed border-slate-200 opacity-60'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${user.tenureYears >= 8 ? 'bg-teal-600 text-white' : user.tenureYears >= 5 ? 'bg-teal-700 text-white' : 'bg-slate-300 text-slate-600'}`}>
                      {user.tenureYears >= 8 ? '✓' : '3'}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                        5 – 8 Years — Distinction Retention Tier
                        {user.tenureYears >= 5 && user.tenureYears < 8 && (
                          <span className="text-[10px] bg-teal-600 text-white font-bold px-1.5 py-0.5 rounded">
                            CURRENT
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500">+10% Multiplier + Annual Loyalty Bonus Eligibility</div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-teal-800 tabular-nums">+10% Multiplier (1.10x)</span>
                </div>
              </div>

              <div className={`p-4 rounded-lg border transition-all ${user.tenureYears >= 8 ? 'border-teal-500 bg-teal-50/60 ring-1 ring-teal-400' : 'border-dashed border-slate-200 opacity-60'}`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${user.tenureYears >= 8 ? 'bg-teal-700 text-white' : 'bg-slate-300 text-slate-600'}`}>
                      {user.tenureYears >= 8 ? '✓' : '4'}
                    </div>
                    <div>
                      <div className="text-xs font-bold text-slate-900 flex items-center gap-2">
                        8+ Years — Senior Merit Circle
                        {user.tenureYears >= 8 && (
                          <span className="text-[10px] bg-teal-600 text-white font-bold px-1.5 py-0.5 rounded">
                            CURRENT
                          </span>
                        )}
                      </div>
                      <div className="text-[11px] text-slate-500">+15% Multiplier + Priority Merit Recognition</div>
                    </div>
                  </div>
                  <span className="text-xs font-bold text-teal-800 tabular-nums">+15% Multiplier (1.15x)</span>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-slate-100">
            <div className="text-xs font-bold text-slate-800 mb-2">Active Perks for {loyaltyTier.tierName}:</div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {loyaltyTier.perks.map((perk, i) => (
                <div key={i} className="flex items-center gap-2 text-xs text-slate-600">
                  <CheckCircle2 className="w-3.5 h-3.5 text-teal-600 shrink-0" />
                  <span>{perk}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {annualPlan && (
        <KPIProgressChart 
          plan={annualPlan} 
          employeeUser={user} 
          appraisalRecord={appraisalRecord} 
        />
      )}

      {/* Office Punctuality Calendar Strip */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Calendar className="w-4 h-4 text-blue-700" />
              Office Attendance & SLA Turnaround Tracking
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Standard work shift: 08:30 AM • Grace period: 15 mins • Abu Dhabi Office Check-ins
            </p>
          </div>
          <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg shrink-0">
            <button
              onClick={() => setActiveAttendanceFilter('all')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeAttendanceFilter === 'all'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              All Days ({attendanceRecords.length})
            </button>
            <button
              onClick={() => setActiveAttendanceFilter('ontime')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeAttendanceFilter === 'ontime'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              On-Time
            </button>
            <button
              onClick={() => setActiveAttendanceFilter('late')}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                activeAttendanceFilter === 'late'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Grace Period
            </button>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-12 gap-2.5 mt-5">
          {filteredAttendance.map((rec) => {
            const isOnTime = rec.status === 'On-Time';
            return (
              <div
                key={rec.id}
                className={`p-2.5 rounded-lg border text-center transition-all ${
                  isOnTime
                    ? 'border-teal-200 bg-teal-50/40 text-teal-900'
                    : 'border-amber-200 bg-amber-50/40 text-amber-900'
                }`}
              >
                <div className="text-[11px] font-semibold text-slate-500">{rec.date.slice(5)}</div>
                <div className="text-sm font-bold my-1 font-mono tabular-nums">{rec.checkInTime}</div>
                <div className="text-[10px] font-medium leading-tight">
                  {isOnTime ? 'On-Time' : 'Grace Period'}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2-Column: Logged Deliverables & Recommended L&D Courses */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-teal-600" />
                  Service Deliverable Point Log
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Objective points awarded by department lead against standardized catalog
                </p>
              </div>
              <span className="text-xs text-slate-500 font-mono tabular-nums">
                {evaluations.length} Evaluated Tasks
              </span>
            </div>
            <div className="mt-4 divide-y divide-slate-100">
              {evaluations.map((item) => (
                <div key={item.id} className="py-3.5 space-y-1.5">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{item.deliverableName}</h4>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500">
                        <span>Evaluated by {item.evaluatorName}</span>
                        <span aria-hidden="true">•</span>
                        <span>{item.evaluatedDate}</span>
                        <span aria-hidden="true">•</span>
                        <span className="tabular-nums">SLA Turnaround: {item.slaHoursTurnaround}h</span>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-sm font-black text-slate-900 tabular-nums">
                        {item.pointsAwarded.toFixed(1)}
                      </span>
                      <span className="text-[11px] text-slate-500 block leading-tight">points</span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-600 bg-slate-50/80 p-2.5 rounded-md border border-slate-100">
                    "{item.feedbackNotes}"
                  </p>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Points count towards 50% Service Matrix weightage</span>
            <span className="font-semibold text-blue-900 tabular-nums">Avg: 90.2 Pts</span>
          </div>
        </div>

        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-blue-700" />
                  Recommended Learning & Development
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Tailored training modules mapped to boost competency areas
                </p>
              </div>
            </div>
            <div className="mt-4 space-y-3.5">
              {trainingRecommendations.map((rec) => {
                const isEnrolled = rec.status === 'Enrolled';
                return (
                  <div 
                    key={rec.id} 
                    className="p-3.5 rounded-lg border border-slate-200 hover:border-slate-300 transition-colors bg-white space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h4 className="text-xs font-bold text-slate-900 leading-snug">{rec.courseTitle}</h4>
                        <div className="text-[11px] text-teal-700 font-semibold mt-0.5">
                          Company Sponsored • AED {rec.costAED.toLocaleString()}
                        </div>
                      </div>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                        isEnrolled 
                          ? 'bg-teal-100 text-teal-800' 
                          : 'bg-blue-100 text-blue-800'
                      }`}>
                        {rec.status}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-600">{rec.reason}</p>
                    <div className="pt-2 flex items-center justify-between text-xs border-t border-slate-100">
                      <span className="text-[11px] text-slate-400">
                        {rec.recommendedByHR ? 'HR Approved Program' : 'Self-Development'}
                      </span>
                      {!isEnrolled ? (
                        <button
                          onClick={() => onEnrollTraining(rec.id)}
                          className="px-2.5 py-1 text-xs font-semibold text-white bg-teal-700 hover:bg-teal-800 rounded transition-colors cursor-pointer"
                        >
                          Enroll Now
                        </button>
                      ) : (
                        <span className="text-xs font-medium text-teal-700 flex items-center gap-1">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Enrolled
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="mt-5 p-3.5 rounded-lg bg-blue-50/60 border border-blue-200/60">
            <div className="flex items-start gap-2.5">
              <MessageSquare className="w-4 h-4 text-blue-700 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-bold text-blue-950">Manager Coaching Session Active</span>
                <p className="text-slate-600 mt-0.5">
                  Next growth check-in scheduled for November 15, 2026. Focus: Senior Architecture Fellowship.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
