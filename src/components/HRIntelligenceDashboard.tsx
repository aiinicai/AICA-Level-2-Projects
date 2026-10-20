import React from 'react';
import { 
  User, 
  Department, 
  AppraisalRecord, 
  SkillItem, 
  TrainingCourse, 
  TrainingRecommendation,
  StatutoryNotice 
} from '../types';
import { 
  Building2, 
  TrendingUp, 
  ShieldAlert, 
  PieChart, 
  Award, 
  DollarSign, 
  AlertTriangle, 
  CheckCircle2, 
  ArrowUpRight,
  BookOpen,
  Sliders,
  FileCheck,
  Scale,
  Download,
  Printer
} from 'lucide-react';
import { exportToWord, exportToPdf, generatePracticeAnalyticsReportHtml } from '../utils/reportExporter';

interface HRIntelligenceDashboardProps {
  companyInfo: {
    name: string;
    totalEmployees: number;
    annualTDBudgetAED: number;
    allocatedTDBudgetAED: number;
    activeCycleName: string;
    statutoryLaw: string;
  };
  departments: Department[];
  allUsers: User[];
  allAppraisals: AppraisalRecord[];
  skills: SkillItem[];
  courses: TrainingCourse[];
  trainingRecommendations: TrainingRecommendation[];
  statutoryNotices: StatutoryNotice[];
  onOpenComplianceDoc: (employeeId?: string) => void;
  onOpenSimulator: () => void;
}

export const HRIntelligenceDashboard: React.FC<HRIntelligenceDashboardProps> = ({
  companyInfo,
  departments,
  allUsers,
  allAppraisals,
  skills,
  courses,
  trainingRecommendations,
  statutoryNotices,
  onOpenComplianceDoc,
  onOpenSimulator,
}) => {
  const [tdBudgetTotal, setTdBudgetTotal] = React.useState<number>(companyInfo.annualTDBudgetAED);
  const [selectedDeptFilter, setSelectedDeptFilter] = React.useState<string>('all');

  const avgPerformanceScore = Math.round(
    allAppraisals.reduce((acc, curr) => acc + curr.finalWeightedScore, 0) / (allAppraisals.length || 1) * 10
  ) / 10;

  const avgTaskSLAIndex = Math.round(
    allAppraisals.reduce((acc, curr) => acc + curr.taskSLAIndex, 0) / (allAppraisals.length || 1) * 10
  ) / 10;

  const avgPunctualityIndex = Math.round(
    allAppraisals.reduce((acc, curr) => acc + curr.punctualityIndex, 0) / (allAppraisals.length || 1) * 10
  ) / 10;

  const enrolledTrainingCost = trainingRecommendations
    .filter((r) => r.status === 'Enrolled' || r.status === 'Completed')
    .reduce((acc, curr) => acc + curr.costAED, 0);

  const tier1Count = allAppraisals.filter((a) => a.performanceTier === 'Needs_Support').length;
  const tier2Count = allAppraisals.filter((a) => a.actionPlanStatus === 'PIP_Level_1').length;
  const tier3Count = allAppraisals.filter((a) => a.actionPlanStatus === 'PIP_Level_2').length;
  const tier4Count = allAppraisals.filter((a) => a.actionPlanStatus === 'Escalation_Review').length;

  const filteredSkills = skills.filter((s) => {
    if (selectedDeptFilter === 'all') return true;
    return s.departmentId === selectedDeptFilter;
  });

  const handleExportFirmWord = () => {
    const html = generatePracticeAnalyticsReportHtml(companyInfo, departments, allAppraisals, allUsers);
    exportToWord({
      title: 'Firm-Wide HR Intelligence & Performance Analytics Report',
      subtitle: `${companyInfo.name} • Operational & T&D Budget Review • ${companyInfo.totalEmployees} Personnel`,
      filename: 'Paras_Advisory_Firmwide_Performance_Report_2026',
      officialRefCode: 'PAA-EXEC-INTEL-2026',
      contentHtml: html,
    });
  };

  const handleExportFirmPdf = () => {
    const html = generatePracticeAnalyticsReportHtml(companyInfo, departments, allAppraisals, allUsers);
    exportToPdf({
      title: 'Firm-Wide HR Intelligence & Performance Analytics Report',
      subtitle: `${companyInfo.name} • Operational & T&D Budget Review • ${companyInfo.totalEmployees} Personnel`,
      filename: 'Paras_Advisory_Firmwide_Performance_Report_2026',
      officialRefCode: 'PAA-EXEC-INTEL-2026',
      contentHtml: html,
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
              <span>Executive HR Intelligence & Analytics</span>
              <span className="text-slate-300">•</span>
              <span className="text-teal-700">MOHRE UAE Regulatory Framework</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              {companyInfo.name} — Org Performance Matrix
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Active Appraisal Cycle: {companyInfo.activeCycleName} • Scope: {companyInfo.totalEmployees} Employees (Abu Dhabi Headquarters)
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={handleExportFirmWord}
              className="px-3.5 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              title="Download firm analytics report as Word document"
            >
              <Download className="w-4 h-4 text-blue-700" />
              Word (.doc)
            </button>
            <button
              onClick={handleExportFirmPdf}
              className="px-3.5 py-2.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
              title="Print or Save firm analytics report as PDF"
            >
              <Printer className="w-4 h-4 text-teal-700" />
              PDF
            </button>
            <button
              onClick={() => onOpenComplianceDoc()}
              className="px-4 py-2.5 rounded-lg bg-rose-700 hover:bg-rose-800 text-white font-semibold text-xs transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
            >
              <Scale className="w-4 h-4 text-rose-200" />
              Statutory Notice Generator
            </button>
            <button
              onClick={onOpenSimulator}
              className="px-4 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              <Sliders className="w-4 h-4 text-teal-600" />
              Scoring Sandbox
            </button>
          </div>
        </div>

        {/* 4 Core Organizational Gauges */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100">
          <div className="p-4 rounded-lg bg-blue-50/50 border border-blue-100">
            <div className="text-xs text-blue-900 font-medium">Org Weighted Score Average</div>
            <div className="text-2xl font-extrabold text-blue-950 mt-1 tabular-nums">
              {avgPerformanceScore} <span className="text-xs font-normal text-slate-500">/ 100</span>
            </div>
            <div className="text-[11px] text-teal-700 mt-1 flex items-center gap-1 font-semibold">
              <TrendingUp className="w-3 h-3" /> +4.2% YoY Firm Improvement
            </div>
          </div>

          <div className="p-4 rounded-lg bg-teal-50/50 border border-teal-100">
            <div className="text-xs text-teal-900 font-medium">Audit SLA Completion Index</div>
            <div className="text-2xl font-extrabold text-teal-950 mt-1 tabular-nums">
              {avgTaskSLAIndex}%
            </div>
            <div className="text-[11px] text-teal-700 mt-1 font-medium">
              Target threshold: 85.0%
            </div>
          </div>

          <div className="p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="text-xs text-slate-600 font-medium">Office Attendance Punctuality</div>
            <div className="text-2xl font-extrabold text-slate-900 mt-1 tabular-nums">
              {avgPunctualityIndex}%
            </div>
            <div className="text-[11px] text-slate-500 mt-1 font-medium">
              Standard 08:30 AM arrival check-in
            </div>
          </div>

          <div className="p-4 rounded-lg bg-indigo-50/50 border border-indigo-100">
            <div className="text-xs text-indigo-900 font-medium">Long-Tenure Retention Health</div>
            <div className="text-2xl font-extrabold text-indigo-950 mt-1 tabular-nums">
              91.4%
            </div>
            <div className="text-[11px] text-indigo-700 mt-1 font-semibold">
              Attrition drop: -4.8% since Loyalty Multiplier
            </div>
          </div>
        </div>
      </div>

      {/* 4-Tier UAE Labor Law Pathway */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <Scale className="w-4 h-4 text-rose-700" />
              Progressive Escalation Framework & Statutory Safeguards
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Transparent, non-punitive step-by-step pathway aligned with UAE Federal Decree-Law No. 33 of 2021
            </p>
          </div>
          <span className="text-xs font-semibold text-rose-800 bg-rose-50 border border-rose-200 px-3 py-1 rounded-md">
            MOHRE Due-Process Active
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <div className="p-4 rounded-lg border border-amber-200 bg-amber-50/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-900">TIER 1 • MINOR DIP</span>
              <span className="text-xs font-bold text-amber-800 bg-amber-100 px-2 py-0.5 rounded tabular-nums">
                {tier1Count} Active
              </span>
            </div>
            <h4 className="text-xs font-bold text-slate-900">Skill Upgrade Action Plan</h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Auto-recommends specific training courses & senior peer pairing. <strong>No financial or disciplinary impact.</strong>
            </p>
            <div className="pt-2 text-[10px] text-amber-800 font-semibold border-t border-amber-200/60">
              Duration: 45 Days • Mentoring Track
            </div>
          </div>

          <div className="p-4 rounded-lg border border-orange-200 bg-orange-50/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-orange-900">TIER 2 • CYCLE 2</span>
              <span className="text-xs font-bold text-orange-800 bg-orange-100 px-2 py-0.5 rounded tabular-nums">
                {tier2Count} Active
              </span>
            </div>
            <h4 className="text-xs font-bold text-slate-900">Constructive 60-Day PIP</h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              1-on-1 mentorship agreement with practice partner. Clear weekly deliverables and milestone reviews.
            </p>
            <div className="pt-2 text-[10px] text-orange-800 font-semibold border-t border-orange-200/60">
              Duration: 60 Days • Partner Checkpoints
            </div>
          </div>

          <div className="p-4 rounded-lg border border-rose-200 bg-rose-50/30 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-rose-900">TIER 3 • CYCLE 3</span>
              <span className="text-xs font-bold text-rose-800 bg-rose-100 px-2 py-0.5 rounded tabular-nums">
                {tier3Count} Active
              </span>
            </div>
            <h4 className="text-xs font-bold text-slate-900">Formal Statutory Review</h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Formal statutory warning following three consecutive review cycles. Triggers increment freeze and re-skilling.
            </p>
            <div className="pt-2 text-[10px] text-rose-800 font-semibold border-t border-rose-200/60">
              Duration: 30 Days • HR Committee
            </div>
          </div>

          <div className="p-4 rounded-lg border border-red-300 bg-red-50/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-red-950">TIER 4 • CRITICAL</span>
              <span className="text-xs font-bold text-red-900 bg-red-100 px-2 py-0.5 rounded tabular-nums">
                {tier4Count} Active
              </span>
            </div>
            <h4 className="text-xs font-bold text-slate-900">Final Committee Hearing</h4>
            <p className="text-[11px] text-slate-600 leading-relaxed">
              Structural role re-assignment, step demotion, or HR-governed termination procedures with full statutory notice.
            </p>
            <div className="pt-2 text-[10px] text-red-800 font-semibold border-t border-red-200/60">
              MOHRE UAE Statutory Documentation
            </div>
          </div>
        </div>
      </div>

      {/* 2-Column: Skill-Gap Heatmap & T&D Budget Allocation Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <PieChart className="w-4 h-4 text-blue-700" />
                  Practice Skill-Gap Heatmap & Benchmark
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Firm proficiency baseline vs. current audit delivery ratings
                </p>
              </div>
              <select
                value={selectedDeptFilter}
                onChange={(e) => setSelectedDeptFilter(e.target.value)}
                className="text-xs py-1.5 px-3 rounded-lg border border-slate-200 bg-white font-medium text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
              >
                <option value="all">All Practice Areas</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div className="mt-5 space-y-4">
              {filteredSkills.map((skill) => {
                const gap = Math.round((skill.benchmarkScore - skill.companyAverage) * 10) / 10;
                const pct = Math.min(100, Math.round((skill.companyAverage / skill.benchmarkScore) * 100));
                const isCriticalGap = gap >= 0.7;
                return (
                  <div key={skill.id} className="space-y-1.5">
                    <div className="flex items-center justify-between text-xs">
                      <div>
                        <span className="font-bold text-slate-900">{skill.skillName}</span>
                        <span className="text-[11px] text-slate-400 ml-2">({skill.category})</span>
                      </div>
                      <div className="text-right">
                        <span className="font-semibold text-slate-800 tabular-nums">
                          {skill.companyAverage.toFixed(1)} / {skill.benchmarkScore.toFixed(1)}
                        </span>
                        <span className={`ml-2 font-bold tabular-nums text-[11px] ${
                          isCriticalGap ? 'text-rose-600' : 'text-teal-700'
                        }`}>
                          (Gap: -{gap.toFixed(1)})
                        </span>
                      </div>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden flex">
                      <div
                        className={`h-2 rounded-full transition-all duration-500 ${
                          isCriticalGap ? 'bg-amber-500' : 'bg-teal-600'
                        }`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="mt-6 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Benchmark target set at 4.5+ across sovereign engagements</span>
            <span className="font-semibold text-blue-900">
              ADGM / ADAA Quality Standard
            </span>
          </div>
        </div>

        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-teal-600" />
                  T&D Budget Allocation Engine
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Automated training budget planner in UAE Dirhams (AED)
                </p>
              </div>
            </div>

            <div className="mt-4 p-4 rounded-xl bg-slate-900 text-white space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                    Approved Annual L&D Fund
                  </div>
                  <div className="text-2xl font-black text-white tabular-nums mt-0.5">
                    AED {tdBudgetTotal.toLocaleString()}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                    Allocated
                  </div>
                  <div className="text-sm font-bold text-teal-400 tabular-nums mt-0.5">
                    AED {enrolledTrainingCost.toLocaleString()}
                  </div>
                </div>
              </div>

              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-teal-400 h-2 rounded-full"
                  style={{ width: `${Math.min(100, (enrolledTrainingCost / tdBudgetTotal) * 100)}%` }}
                />
              </div>

              <div className="space-y-1.5 pt-1">
                <div className="flex justify-between text-xs text-slate-300">
                  <span>Interactive Budget Sandbox:</span>
                  <span className="font-mono tabular-nums text-teal-300">
                    AED {tdBudgetTotal.toLocaleString()}
                  </span>
                </div>
                <input
                  type="range"
                  min={200000}
                  max={1000000}
                  step={25000}
                  value={tdBudgetTotal}
                  onChange={(e) => setTdBudgetTotal(Number(e.target.value))}
                  className="w-full accent-teal-400 cursor-pointer h-1.5 bg-slate-700 rounded-lg"
                />
                <div className="flex justify-between text-[10px] text-slate-500">
                  <span>AED 200,000</span>
                  <span>AED 1,000,000</span>
                </div>
              </div>
            </div>

            <div className="mt-5 space-y-2.5 text-xs">
              <div className="font-bold text-slate-800">Departmental Allocation (AED):</div>
              {departments.map((dept) => {
                const ratio = Math.round((dept.allocatedTDBudgetAED / dept.annualTDBudgetAED) * 100);
                return (
                  <div key={dept.id} className="p-2.5 rounded-lg border border-slate-100 bg-slate-50/60 flex items-center justify-between">
                    <div>
                      <span className="font-semibold text-slate-900">{dept.name}</span>
                      <span className="text-[11px] text-slate-400 block">{dept.employeeCount} staff</span>
                    </div>
                    <div className="text-right">
                      <span className="font-bold text-slate-800 tabular-nums">
                        AED {dept.allocatedTDBudgetAED.toLocaleString()}
                      </span>
                      <span className="text-[11px] text-slate-500 block tabular-nums">
                        {ratio}% utilized
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
          <div className="mt-5 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Surplus fund: AED {(tdBudgetTotal - enrolledTrainingCost).toLocaleString()}</span>
            <span className="font-semibold text-teal-700">100% Non-Punitive Skill Funding</span>
          </div>
        </div>
      </div>
    </div>
  );
};
