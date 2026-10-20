import React from 'react';
import { calculatePerformanceScore, getLoyaltyTierInfo, getTierMetadata } from '../utils/scoringEngine';
import { 
  Calculator, 
  Sparkles, 
  TrendingUp, 
  Award, 
  ShieldAlert, 
  RotateCcw,
  Info,
  CheckCircle2
} from 'lucide-react';

export const ScoreSimulator: React.FC = () => {
  // Simulator State
  const [servicePoints, setServicePoints] = React.useState<number>(88);
  const [taskSLA, setTaskSLA] = React.useState<number>(90);
  const [attendance, setAttendance] = React.useState<number>(92);
  const [growthDelta, setGrowthDelta] = React.useState<number>(6.5);
  const [tenureYears, setTenureYears] = React.useState<number>(3.5);
  const [consecutiveLow, setConsecutiveLow] = React.useState<number>(0);

  // Compute live score
  const result = calculatePerformanceScore({
    serviceDeliveryPoints: servicePoints,
    taskSLAPunctuality: taskSLA,
    officeAttendancePunctuality: attendance,
    growthDeltaPct: growthDelta,
    tenureYears,
    consecutiveUnderperformingCycles: consecutiveLow,
  });

  const loyaltyTier = getLoyaltyTierInfo(tenureYears);
  const tierMeta = getTierMetadata(result.performanceTier);

  const handleReset = () => {
    setServicePoints(88);
    setTaskSLA(90);
    setAttendance(92);
    setGrowthDelta(6.5);
    setTenureYears(3.5);
    setConsecutiveLow(0);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Simulator Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-teal-800 uppercase tracking-wider">
              <Calculator className="w-3.5 h-3.5 text-teal-600" />
              <span>Interactive Point Evaluation Matrix Sandbox</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              Objective Scoring & Loyalty Multiplier Simulator
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Test "What-If" scenarios on employee deliverables, turnaround SLA, and loyalty boosts
            </p>
          </div>
          <button
            onClick={handleReset}
            className="px-3.5 py-2 rounded-lg border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 self-start sm:self-center cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
            Reset Defaults
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Interactive Controls */}
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Core Evaluation Parameters
            </h2>
            <p className="text-xs text-slate-500">
              Adjust sliders to observe immediate score weighting and escalation triggers
            </p>
          </div>

          {/* Slider 1: Service Delivery Points */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">
                1. Service Delivery Points (50% Weight)
              </span>
              <span className="text-sm font-mono font-bold text-blue-900 tabular-nums">
                {servicePoints} pts
              </span>
            </div>
            <input
              type="range"
              min={20}
              max={100}
              step={1}
              value={servicePoints}
              onChange={(e) => setServicePoints(Number(e.target.value))}
              className="w-full accent-blue-700 cursor-pointer h-2 bg-slate-100 rounded-lg"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>20 (Underperforming)</span>
              <span>Weighted: {result.weightedServicePoints} pts</span>
              <span>100 (Flawless)</span>
            </div>
          </div>

          {/* Slider 2: Task SLA Punctuality */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">
                2. Task Turnaround SLA Adherence (25% Weight)
              </span>
              <span className="text-sm font-mono font-bold text-teal-800 tabular-nums">
                {taskSLA}%
              </span>
            </div>
            <input
              type="range"
              min={20}
              max={100}
              step={1}
              value={taskSLA}
              onChange={(e) => setTaskSLA(Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>20 (Repeated Delays)</span>
              <span>Weighted: {result.weightedTaskSLA} pts</span>
              <span>100 (Zero Breaches)</span>
            </div>
          </div>

          {/* Slider 3: Office Attendance */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">
                3. Office Attendance Punctuality (15% Weight)
              </span>
              <span className="text-sm font-mono font-bold text-indigo-900 tabular-nums">
                {attendance}%
              </span>
            </div>
            <input
              type="range"
              min={30}
              max={100}
              step={1}
              value={attendance}
              onChange={(e) => setAttendance(Number(e.target.value))}
              className="w-full accent-indigo-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>30 (Frequent Lates)</span>
              <span>Weighted: {result.weightedAttendance} pts</span>
              <span>100 (On-Time 08:30 AM)</span>
            </div>
          </div>

          {/* Slider 4: Growth Delta */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800">
                4. Cycle Improvement Delta (10% Weight)
              </span>
              <span className="text-sm font-mono font-bold text-emerald-800 tabular-nums">
                {growthDelta >= 0 ? '+' : ''}{growthDelta}%
              </span>
            </div>
            <input
              type="range"
              min={-20}
              max={25}
              step={0.5}
              value={growthDelta}
              onChange={(e) => setGrowthDelta(Number(e.target.value))}
              className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>-20% (Performance Dip)</span>
              <span>Normalized: {result.growthDeltaScore} pts • {result.weightedGrowth} pts</span>
              <span>+25% (Rapid Growth)</span>
            </div>
          </div>

          {/* Slider 5: Tenure & Loyalty Multiplier */}
          <div className="pt-4 border-t border-slate-100 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <Award className="w-4 h-4 text-teal-600" />
                Employee Tenure (Loyalty Multiplier Boost)
              </span>
              <span className="text-sm font-mono font-bold text-teal-800 tabular-nums">
                {tenureYears} Years ({result.loyaltyMultiplier.toFixed(2)}x)
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={15}
              step={0.5}
              value={tenureYears}
              onChange={(e) => setTenureYears(Number(e.target.value))}
              className="w-full accent-teal-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
            />
            <div className="flex justify-between text-[11px] text-slate-400">
              <span>0-2 yrs (1.00x)</span>
              <span>2-5 yrs (1.05x)</span>
              <span>5-8 yrs (1.10x)</span>
              <span>8+ yrs (1.15x)</span>
            </div>
          </div>

          {/* Consecutive Underperformance Cycles */}
          <div className="pt-4 border-t border-slate-100 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="font-bold text-slate-800 flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-rose-600" />
                Consecutive Underperformance Cycles (Escalation Trigger)
              </span>
              <span className="text-sm font-mono font-bold text-rose-700 tabular-nums">
                {consecutiveLow} Cycles
              </span>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {[0, 1, 2, 3, 4].map((num) => (
                <button
                  key={num}
                  onClick={() => setConsecutiveLow(num)}
                  className={`py-1.5 text-xs font-semibold rounded-lg border transition-colors cursor-pointer ${
                    consecutiveLow === num
                      ? 'bg-rose-700 text-white border-rose-700'
                      : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                  }`}
                >
                  {num === 0 ? '0 (None)' : `Cycle ${num}`}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Real-time Calculation Breakdown & Outcome */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                Simulated Result
              </span>
              <span className={`text-xs px-2.5 py-1 rounded-md font-semibold border ${tierMeta.colorClass}`}>
                {tierMeta.label}
              </span>
            </div>

            <div className="p-5 rounded-xl bg-slate-900 text-white text-center space-y-2">
              <div className="text-xs text-slate-400 uppercase tracking-widest font-semibold">
                Final Weighted Performance Score
              </div>
              <div className="text-5xl font-extrabold tabular-nums text-teal-400">
                {result.finalWeightedScore}
              </div>
              <div className="text-xs text-slate-300 flex items-center justify-center gap-2 pt-1">
                <span>Base: {result.baseScore}</span>
                <span>•</span>
                <span className="text-teal-300 font-bold">{result.loyaltyMultiplier.toFixed(2)}x Multiplier</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
              <div className="text-[11px] font-bold text-slate-500 uppercase">
                Triggered Action Pathway:
              </div>
              <div className="text-sm font-bold text-slate-900">
                {result.actionPlanStatus === 'Standard' && 'Standard Merit Increment & Annual Recognition Track'}
                {result.actionPlanStatus === 'Coaching' && 'Tier 1: Skill Upgrade Action Plan (Non-Financial Mentorship)'}
                {result.actionPlanStatus === 'PIP_Level_1' && 'Tier 2: Constructive 60-Day Mentorship PIP'}
                {result.actionPlanStatus === 'PIP_Level_2' && 'Tier 3: Formal Statutory Review & Increment Freeze Flag'}
                {result.actionPlanStatus === 'Escalation_Review' && 'Tier 4: Management Hearing under UAE Decree-Law No. 33 of 2021'}
              </div>
              <p className="text-xs text-slate-600 pt-1">
                {result.actionPlanStatus === 'Standard' && 'Performance meets or exceeds firm targets. Eligible for full merit bonuses.'}
                {result.actionPlanStatus === 'Coaching' && 'Non-punitive development pathway. Recommends sponsored ADGM/ICAEW training.'}
                {result.actionPlanStatus === 'PIP_Level_1' && 'Consecutive cycle 2 gap triggers 60 days of structured weekly partner reviews.'}
                {result.actionPlanStatus === 'PIP_Level_2' && 'Formal written statutory notice with potential grade step adjustment.'}
                {result.actionPlanStatus === 'Escalation_Review' && 'Convening Executive Managing Board for statutory reassignment or separation.'}
              </p>
            </div>

            <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-200/60 text-xs space-y-2">
              <div className="font-bold text-blue-950 flex items-center gap-1.5">
                <Info className="w-4 h-4 text-blue-700" />
                Evaluation Arithmetic Formula:
              </div>
              <div className="font-mono text-[11px] text-slate-700 bg-white p-2.5 rounded border border-blue-100 space-y-1 leading-relaxed">
                <div>Base = ({servicePoints} × 0.50) + ({taskSLA} × 0.25)</div>
                <div>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;+ ({attendance} × 0.15) + ({result.growthDeltaScore} × 0.10)</div>
                <div className="text-blue-900 font-bold pt-1 border-t border-slate-100">
                  Base = {result.weightedServicePoints} + {result.weightedTaskSLA} + {result.weightedAttendance} + {result.weightedGrowth} = {result.baseScore}
                </div>
                <div className="text-teal-800 font-bold">
                  Final = {result.baseScore} × {result.loyaltyMultiplier.toFixed(2)} = {result.finalWeightedScore}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
