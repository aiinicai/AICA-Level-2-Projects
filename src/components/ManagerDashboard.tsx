import React from 'react';
import { 
  User, 
  AppraisalRecord, 
  TaskEvaluation, 
  CoachingNote, 
  PerformanceTier,
  ActionPlanStatus,
  ServiceDeliverableCatalog,
  CompletionStatus
} from '../types';
import { 
  calculatePerformanceScore, 
  getTierMetadata, 
  getLoyaltyTierInfo 
} from '../utils/scoringEngine';
import { 
  MOCK_DELIVERABLES_CATALOG 
} from '../data/mockData';
import { 
  Users, 
  TrendingUp, 
  PlusCircle, 
  MessageSquare, 
  ShieldAlert, 
  Sparkles, 
  Clock, 
  Award, 
  ChevronRight,
  Filter,
  Search,
  CheckCircle2,
  FileText,
  Sliders,
  Scale,
  Save,
  Check,
  Calendar,
  AlertCircle,
  Briefcase,
  ExternalLink,
  ChevronDown,
  Download,
  Printer
} from 'lucide-react';
import { exportToWord, exportToPdf, generateAppraisalReportHtml } from '../utils/reportExporter';

interface ManagerDashboardProps {
  managerUser: User;
  allManagers: User[];
  teamUsers: User[];
  teamAppraisals: AppraisalRecord[];
  recentEvaluations: TaskEvaluation[];
  coachingNotes: CoachingNote[];
  onOpenQuickEval: (employeeId?: string) => void;
  onOpenAddCoaching: (employeeId?: string) => void;
  onSaveEvaluation: (evaluation: TaskEvaluation) => void;
  onUpdateAppraisal: (appraisal: AppraisalRecord) => void;
  onOpenComplianceDoc: (employeeId: string) => void;
  onViewAsEmployee?: (employee: User) => void;
}

export const ManagerDashboard: React.FC<ManagerDashboardProps> = ({
  managerUser,
  allManagers,
  teamUsers,
  teamAppraisals,
  recentEvaluations,
  coachingNotes,
  onOpenQuickEval,
  onOpenAddCoaching,
  onSaveEvaluation,
  onUpdateAppraisal,
  onOpenComplianceDoc,
  onViewAsEmployee,
}) => {
  const [activeSubTab, setActiveSubTab] = React.useState<'roster' | 'evaluation_sheet' | 'deliverables' | 'pip_tracker'>('roster');
  const [selectedEmpId, setSelectedEmpId] = React.useState<string>(teamUsers[0]?.id || 'emp-zayed');
  const [selectedTierFilter, setSelectedTierFilter] = React.useState<string>('all');
  const [searchQuery, setSearchQuery] = React.useState<string>('');

  const selectedEmployee = teamUsers.find((u) => u.id === selectedEmpId) || teamUsers[0];
  const selectedAppraisal = teamAppraisals.find((a) => a.employeeId === selectedEmpId);

  const [editGrossServicePoints, setEditGrossServicePoints] = React.useState<number>(selectedAppraisal?.grossServicePoints ?? 88);
  const [editTaskSLAIndex, setEditTaskSLAIndex] = React.useState<number>(selectedAppraisal?.taskSLAIndex ?? 90);
  const [editPunctualityIndex, setEditPunctualityIndex] = React.useState<number>(selectedAppraisal?.punctualityIndex ?? 92);
  const [editGrowthDelta, setEditGrowthDelta] = React.useState<number>(selectedAppraisal?.growthDeltaPct ?? 4.5);
  const [editActionStatus, setEditActionStatus] = React.useState<ActionPlanStatus>(selectedAppraisal?.actionPlanStatus ?? 'Standard');
  const [editHrApproval, setEditHrApproval] = React.useState<'Approved' | 'Pending Review' | 'Flagged'>(selectedAppraisal?.hrApprovalStatus ?? 'Approved');
  const [evalReviewComments, setEvalReviewComments] = React.useState<string>(
    selectedAppraisal?.coachingNotes?.[0] || 'Demonstrates solid proficiency across IFRS audit workpapers. Turnaround meets statutory practice guidelines.'
  );

  React.useEffect(() => {
    if (selectedEmployee) {
      const app = teamAppraisals.find((a) => a.employeeId === selectedEmployee.id);
      setEditGrossServicePoints(app?.grossServicePoints ?? 85);
      setEditTaskSLAIndex(app?.taskSLAIndex ?? 88);
      setEditPunctualityIndex(app?.punctualityIndex ?? 90);
      setEditGrowthDelta(app?.growthDeltaPct ?? 2.0);
      setEditActionStatus(app?.actionPlanStatus ?? 'Standard');
      setEditHrApproval(app?.hrApprovalStatus ?? 'Approved');
      setEvalReviewComments(
        app?.coachingNotes?.[0] || 'Demonstrates solid proficiency across IFRS audit workpapers.'
      );
    }
  }, [selectedEmpId, teamAppraisals]);

  const [deliverableId, setDeliverableId] = React.useState<string>(MOCK_DELIVERABLES_CATALOG[0].id);
  const [deliverableStatus, setDeliverableStatus] = React.useState<CompletionStatus>('Quality_Exceeded');
  const [deliverableSlaHours, setDeliverableSlaHours] = React.useState<number>(24);
  const [deliverableFeedback, setDeliverableFeedback] = React.useState<string>('Exemplary audit sampling and technical disclosures.');
  const [deliverableSuccessMsg, setDeliverableSuccessMsg] = React.useState<string | null>(null);

  const liveScoreData = calculatePerformanceScore({
    serviceDeliveryPoints: editGrossServicePoints,
    taskSLAPunctuality: editTaskSLAIndex,
    officeAttendancePunctuality: editPunctualityIndex,
    growthDeltaPct: editGrowthDelta,
    tenureYears: selectedEmployee?.tenureYears ?? 3.5,
    consecutiveUnderperformingCycles: selectedAppraisal?.consecutiveUnderperformingCycles ?? 0,
  });

  const selectedLoyalty = getLoyaltyTierInfo(selectedEmployee?.tenureYears ?? 3.5);
  const selectedTierMeta = getTierMetadata(liveScoreData.performanceTier);

  const teamRows = teamUsers.map((member) => {
    const appraisal = teamAppraisals.find((a) => a.employeeId === member.id);
    const scoreData = calculatePerformanceScore({
      serviceDeliveryPoints: appraisal?.grossServicePoints ?? 85,
      taskSLAPunctuality: appraisal?.taskSLAIndex ?? 88,
      officeAttendancePunctuality: appraisal?.punctualityIndex ?? 90,
      growthDeltaPct: appraisal?.growthDeltaPct ?? 2.0,
      tenureYears: member.tenureYears,
      consecutiveUnderperformingCycles: appraisal?.consecutiveUnderperformingCycles ?? 0,
    });
    const loyalty = getLoyaltyTierInfo(member.tenureYears);
    return {
      member,
      appraisal,
      scoreData,
      loyalty,
    };
  });

  const filteredTeam = teamRows.filter((item) => {
    if (selectedTierFilter !== 'all' && item.scoreData.performanceTier !== selectedTierFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = item.member.fullName.toLowerCase().includes(q);
      const matchCode = item.member.employeeIdCode.toLowerCase().includes(q);
      const matchDesignation = item.member.currentDesignation.toLowerCase().includes(q);
      return matchName || matchCode || matchDesignation;
    }
    return true;
  });

  const totalTeam = teamRows.length;
  const highPerformers = teamRows.filter((r) => r.scoreData.performanceTier === 'Exceeds').length;
  const needsSupport = teamRows.filter((r) => r.scoreData.performanceTier === 'Needs_Support').length;
  const underperforming = teamRows.filter((r) => r.scoreData.performanceTier === 'Underperforming').length;

  const handleSaveAppraisalForm = () => {
    if (!selectedEmployee) return;
    const updatedAppraisal: AppraisalRecord = {
      id: selectedAppraisal?.id || `app-${selectedEmployee.id}-q3`,
      cycleId: 'cycle-q3-2026',
      cycleName: 'Q3-2026 Evaluation Cycle',
      employeeId: selectedEmployee.id,
      employeeName: selectedEmployee.fullName,
      departmentId: selectedEmployee.departmentId,
      grossServicePoints: editGrossServicePoints,
      punctualityIndex: editPunctualityIndex,
      taskSLAIndex: editTaskSLAIndex,
      growthDeltaPct: editGrowthDelta,
      tenureYears: selectedEmployee.tenureYears,
      tenureLoyaltyMultiplier: liveScoreData.loyaltyMultiplier,
      baseScore: liveScoreData.baseScore,
      finalWeightedScore: liveScoreData.finalWeightedScore,
      performanceTier: liveScoreData.performanceTier,
      actionPlanStatus: editActionStatus,
      consecutiveUnderperformingCycles: selectedAppraisal?.consecutiveUnderperformingCycles ?? 0,
      coachingNotes: [evalReviewComments, ...(selectedAppraisal?.coachingNotes?.slice(1) || [])],
      hrApprovalStatus: editHrApproval,
      lastEvaluationDate: new Date().toISOString().split('T')[0],
    };
    onUpdateAppraisal(updatedAppraisal);
    setDeliverableSuccessMsg('Appraisal successfully saved & synced!');
    setTimeout(() => setDeliverableSuccessMsg(null), 3500);
  };

  const handleExportAppraisalWord = () => {
    if (!selectedEmployee) return;
    const appraisalToExport: AppraisalRecord = {
      id: selectedAppraisal?.id || `app-${selectedEmployee.id}-q3`,
      cycleId: 'cycle-q3-2026',
      cycleName: 'Q3-2026 Evaluation Cycle',
      employeeId: selectedEmployee.id,
      employeeName: selectedEmployee.fullName,
      departmentId: selectedEmployee.departmentId,
      grossServicePoints: editGrossServicePoints,
      punctualityIndex: editPunctualityIndex,
      taskSLAIndex: editTaskSLAIndex,
      growthDeltaPct: editGrowthDelta,
      tenureYears: selectedEmployee.tenureYears,
      tenureLoyaltyMultiplier: liveScoreData.loyaltyMultiplier,
      baseScore: liveScoreData.baseScore,
      finalWeightedScore: liveScoreData.finalWeightedScore,
      performanceTier: liveScoreData.performanceTier,
      actionPlanStatus: editActionStatus,
      consecutiveUnderperformingCycles: selectedAppraisal?.consecutiveUnderperformingCycles ?? 0,
      coachingNotes: [evalReviewComments, ...(selectedAppraisal?.coachingNotes?.slice(1) || [])],
      hrApprovalStatus: editHrApproval,
      lastEvaluationDate: new Date().toISOString().split('T')[0],
    };
    const html = generateAppraisalReportHtml(appraisalToExport, selectedEmployee, managerUser.fullName);
    exportToWord({
      title: `Appraisal Scorecard: ${selectedEmployee.fullName}`,
      subtitle: `${selectedEmployee.currentDesignation} • ${selectedEmployee.departmentName} • Paras Advisory`,
      filename: `Appraisal_Report_${selectedEmployee.fullName.replace(/\s+/g, '_')}_2026`,
      officialRefCode: `PAA-APP-2026-${selectedEmployee.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  const handleExportAppraisalPdf = () => {
    if (!selectedEmployee) return;
    const appraisalToExport: AppraisalRecord = {
      id: selectedAppraisal?.id || `app-${selectedEmployee.id}-q3`,
      cycleId: 'cycle-q3-2026',
      cycleName: 'Q3-2026 Evaluation Cycle',
      employeeId: selectedEmployee.id,
      employeeName: selectedEmployee.fullName,
      departmentId: selectedEmployee.departmentId,
      grossServicePoints: editGrossServicePoints,
      punctualityIndex: editPunctualityIndex,
      taskSLAIndex: editTaskSLAIndex,
      growthDeltaPct: editGrowthDelta,
      tenureYears: selectedEmployee.tenureYears,
      tenureLoyaltyMultiplier: liveScoreData.loyaltyMultiplier,
      baseScore: liveScoreData.baseScore,
      finalWeightedScore: liveScoreData.finalWeightedScore,
      performanceTier: liveScoreData.performanceTier,
      actionPlanStatus: editActionStatus,
      consecutiveUnderperformingCycles: selectedAppraisal?.consecutiveUnderperformingCycles ?? 0,
      coachingNotes: [evalReviewComments, ...(selectedAppraisal?.coachingNotes?.slice(1) || [])],
      hrApprovalStatus: editHrApproval,
      lastEvaluationDate: new Date().toISOString().split('T')[0],
    };
    const html = generateAppraisalReportHtml(appraisalToExport, selectedEmployee, managerUser.fullName);
    exportToPdf({
      title: `Appraisal Scorecard: ${selectedEmployee.fullName}`,
      subtitle: `${selectedEmployee.currentDesignation} • ${selectedEmployee.departmentName} • Paras Advisory`,
      filename: `Appraisal_Report_${selectedEmployee.fullName.replace(/\s+/g, '_')}_2026`,
      officialRefCode: `PAA-APP-2026-${selectedEmployee.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  const handleAddDeliverableInline = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedEmployee) return;
    const cat = MOCK_DELIVERABLES_CATALOG.find((d) => d.id === deliverableId) || MOCK_DELIVERABLES_CATALOG[0];
    let mult = 1.0;
    if (deliverableStatus === 'Quality_Exceeded') mult = cat.qualityWeightage;
    else if (deliverableStatus === 'Delayed') mult = 0.85;
    else if (deliverableStatus === 'Needs_Revision') mult = 0.75;

    const pts = Math.min(100, Math.round(cat.basePointValue * mult * 10) / 10);
    const newEval: TaskEvaluation = {
      id: `eval-${Date.now()}`,
      employeeId: selectedEmployee.id,
      employeeName: selectedEmployee.fullName,
      deliverableId: cat.id,
      deliverableName: cat.deliverableName,
      departmentId: selectedEmployee.departmentId,
      evaluatorId: managerUser.id,
      evaluatorName: managerUser.fullName,
      completionStatus: deliverableStatus,
      pointsAwarded: pts,
      taskDeadline: '2026-10-11 18:00',
      actualCompletionTimestamp: '2026-10-11 16:30',
      slaHoursTurnaround: deliverableSlaHours,
      feedbackNotes: deliverableFeedback,
      evaluatedDate: new Date().toISOString().split('T')[0],
    };
    onSaveEvaluation(newEval);
    setDeliverableSuccessMsg(`Awarded ${pts} points for "${cat.deliverableName}"!`);
    setTimeout(() => setDeliverableSuccessMsg(null), 3500);
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-300">
      {/* Top Banner */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-xs font-bold text-blue-900 uppercase tracking-wider">
              <Briefcase className="w-3.5 h-3.5 text-blue-700" />
              <span>Manager Evaluations Hub</span>
              <span className="text-slate-300">•</span>
              <span className="text-teal-700">Q3-2026 Practice Review</span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">
              {managerUser.departmentName || 'Statutory Audit & Assurance Practice'}
            </h1>
            <p className="text-xs text-slate-500 mt-1">
              Practice Lead: <strong>{managerUser.fullName}</strong> ({managerUser.currentDesignation})
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => onOpenQuickEval(selectedEmpId)}
              className="px-4 py-2.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-semibold text-xs transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
            >
              <PlusCircle className="w-4 h-4 text-blue-200" />
              Log Deliverable Points
            </button>
            <button
              onClick={() => onOpenAddCoaching(selectedEmpId)}
              className="px-4 py-2.5 rounded-lg border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-2 cursor-pointer"
            >
              <MessageSquare className="w-4 h-4 text-teal-600" />
              Log Constructive Coaching
            </button>
          </div>
        </div>

        {/* 4-Stat Strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100">
          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-100">
            <div className="text-xs text-slate-500 font-medium">Assigned Auditors</div>
            <div className="text-2xl font-bold text-slate-900 mt-1 tabular-nums">{totalTeam}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Active practice members</div>
          </div>
          <div className="p-3.5 rounded-lg bg-teal-50/60 border border-teal-100">
            <div className="text-xs text-teal-800 font-medium">Exceeding Expectations</div>
            <div className="text-2xl font-bold text-teal-900 mt-1 tabular-nums">{highPerformers}</div>
            <div className="text-[11px] text-teal-700 mt-0.5">Eligible for merit rewards</div>
          </div>
          <div className="p-3.5 rounded-lg bg-amber-50/60 border border-amber-100">
            <div className="text-xs text-amber-800 font-medium">Skill Upgrade (Tier 1)</div>
            <div className="text-2xl font-bold text-amber-900 mt-1 tabular-nums">{needsSupport}</div>
            <div className="text-[11px] text-amber-700 mt-0.5">Non-punitive coaching track</div>
          </div>
          <div className="p-3.5 rounded-lg bg-rose-50/60 border border-rose-100">
            <div className="text-xs text-rose-800 font-medium">Active PIP / Mentorship</div>
            <div className="text-2xl font-bold text-rose-900 mt-1 tabular-nums">{underperforming}</div>
            <div className="text-[11px] text-rose-700 mt-0.5">60-Day progressive plan</div>
          </div>
        </div>
      </div>

      {/* Sub-Navigation Bar */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setActiveSubTab('roster')}
            className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeSubTab === 'roster'
                ? 'bg-blue-900 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            Auditor Team Roster ({filteredTeam.length})
          </button>
          <button
            onClick={() => setActiveSubTab('evaluation_sheet')}
            className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeSubTab === 'evaluation_sheet'
                ? 'bg-blue-900 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <Sliders className="w-3.5 h-3.5 text-teal-400" />
            Dedicated Evaluation Sheet
            {selectedEmployee && (
              <span className="text-[10px] bg-teal-800 text-teal-100 px-1.5 py-0.2 rounded font-mono">
                {selectedEmployee.fullName.split(' ')[0]}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveSubTab('deliverables')}
            className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeSubTab === 'deliverables'
                ? 'bg-blue-900 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-500" />
            Deliverables Ledger ({recentEvaluations.length})
          </button>
          <button
            onClick={() => setActiveSubTab('pip_tracker')}
            className={`px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ${
              activeSubTab === 'pip_tracker'
                ? 'bg-blue-900 text-white shadow-xs'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5 text-rose-500" />
            Progressive Support & PIP ({needsSupport + underperforming})
          </button>
        </div>

        {deliverableSuccessMsg && (
          <div className="text-xs font-bold text-teal-700 bg-teal-50 border border-teal-200 px-3 py-1 rounded-md flex items-center gap-1.5 animate-in fade-in">
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-600" />
            {deliverableSuccessMsg}
          </div>
        )}
      </div>

      {/* VIEW 1: DEDICATED AUDITOR EVALUATION SHEET */}
      {activeSubTab === 'evaluation_sheet' && selectedEmployee && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-xl bg-blue-900 text-white font-bold text-lg flex items-center justify-center">
                  {selectedEmployee.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-bold text-slate-900">{selectedEmployee.fullName}</h2>
                    <span className="text-xs font-mono text-slate-400 tabular-nums">({selectedEmployee.employeeIdCode})</span>
                    <span className={`text-[11px] px-2 py-0.5 rounded font-semibold border ${selectedTierMeta.colorClass}`}>
                      {selectedTierMeta.label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {selectedEmployee.currentDesignation} • {selectedEmployee.departmentName}
                  </p>
                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500">
                    <span className="font-semibold text-teal-700">{selectedEmployee.tenureYears} yrs service</span>
                    <span aria-hidden="true">•</span>
                    <span className="font-medium text-slate-700">{selectedLoyalty.boostPct} Loyalty Multiplier</span>
                    <span aria-hidden="true">•</span>
                    <span>Status: <strong className="text-slate-800">{selectedEmployee.status}</strong></span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-right">
                  <span className="text-xs text-slate-400 block">Switch Auditor:</span>
                  <select
                    value={selectedEmpId}
                    onChange={(e) => setSelectedEmpId(e.target.value)}
                    className="mt-0.5 text-xs py-1.5 px-3 rounded-lg border border-slate-200 bg-slate-50 font-semibold text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
                  >
                    {teamUsers.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.fullName} ({u.employeeIdCode})
                      </option>
                    ))}
                  </select>
                </div>
                {onViewAsEmployee && (
                  <button
                    onClick={() => onViewAsEmployee(selectedEmployee)}
                    className="self-end px-3 py-1.5 rounded-lg border border-slate-200 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-50 flex items-center gap-1 cursor-pointer"
                  >
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                    Growth Hub
                  </button>
                )}
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-[11px] text-slate-500 block">Base Evaluation</span>
                <span className="text-xl font-black text-slate-900 tabular-nums">{liveScoreData.baseScore}</span>
                <span className="text-[10px] text-slate-400 block">/ 100 max</span>
              </div>
              <div className="p-3 rounded-lg bg-teal-50/50 border border-teal-100">
                <span className="text-[11px] text-teal-800 block">Loyalty Multiplier</span>
                <span className="text-xl font-black text-teal-900 tabular-nums">{liveScoreData.loyaltyMultiplier.toFixed(2)}x</span>
                <span className="text-[10px] text-teal-700 block">+{selectedLoyalty.boostPct} retention</span>
              </div>
              <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100">
                <span className="text-[11px] text-blue-900 block">Final Weighted Pts</span>
                <span className="text-2xl font-black text-blue-950 tabular-nums">{liveScoreData.finalWeightedScore}</span>
                <span className="text-[10px] text-blue-700 block">Cycle score</span>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 text-white">
                <span className="text-[11px] text-slate-400 block">Cycle Tier</span>
                <span className="text-base font-bold text-teal-400 block mt-1">{selectedTierMeta.label}</span>
                <span className="text-[10px] text-slate-300 block">{editActionStatus.replace('_', ' ')}</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-7 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                    <Sliders className="w-4 h-4 text-blue-700" />
                    Quarterly Appraisal Scorecard & Weights
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Adjust objective scores to recalibrate overall appraisal standing
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleExportAppraisalWord}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    title="Export appraisal report as Word document (.doc)"
                  >
                    <Download className="w-3.5 h-3.5 text-blue-700" />
                    Word (.doc)
                  </button>
                  <button
                    type="button"
                    onClick={handleExportAppraisalPdf}
                    className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                    title="Print or Save appraisal report as PDF"
                  >
                    <Printer className="w-3.5 h-3.5 text-teal-700" />
                    PDF
                  </button>
                  <button
                    type="button"
                    onClick={handleSaveAppraisalForm}
                    className="px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
                  >
                    <Save className="w-3.5 h-3.5" />
                    Save Appraisal
                  </button>
                </div>
              </div>

              {/* Slider 1: Service Deliverables Points (50%) */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-bold text-slate-800">1. Service Deliverable Points (50% Weight):</span>
                  <span className="font-mono font-bold text-blue-900 tabular-nums">
                    {editGrossServicePoints} pts • {liveScoreData.weightedServicePoints} pts
                  </span>
                </div>
                <input
                  type="range"
                  min={20}
                  max={100}
                  step={0.5}
                  value={editGrossServicePoints}
                  onChange={(e) => setEditGrossServicePoints(Number(e.target.value))}
                  className="w-full accent-blue-700 cursor-pointer h-2 bg-slate-100 rounded-lg"
                />
              </div>

              {/* Slider 2: Task Turnaround SLA (25%) */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-bold text-slate-800">2. Task Turnaround SLA Adherence (25% Weight):</span>
                  <span className="font-mono font-bold text-teal-800 tabular-nums">
                    {editTaskSLAIndex}% • {liveScoreData.weightedTaskSLA} pts
                  </span>
                </div>
                <input
                  type="range"
                  min={30}
                  max={100}
                  step={0.5}
                  value={editTaskSLAIndex}
                  onChange={(e) => setEditTaskSLAIndex(Number(e.target.value))}
                  className="w-full accent-teal-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
                />
              </div>

              {/* Slider 3: Office Attendance (15%) */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-bold text-slate-800">3. Office Attendance Punctuality (15% Weight):</span>
                  <span className="font-mono font-bold text-indigo-900 tabular-nums">
                    {editPunctualityIndex}% • {liveScoreData.weightedAttendance} pts
                  </span>
                </div>
                <input
                  type="range"
                  min={40}
                  max={100}
                  step={0.5}
                  value={editPunctualityIndex}
                  onChange={(e) => setEditPunctualityIndex(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
                />
              </div>

              {/* Slider 4: Cycle Growth Delta (10%) */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-bold text-slate-800">4. Growth / Improvement Delta (10% Weight):</span>
                  <span className="font-mono font-bold text-emerald-800 tabular-nums">
                    {editGrowthDelta >= 0 ? '+' : ''}{editGrowthDelta}% • {liveScoreData.weightedGrowth} pts
                  </span>
                </div>
                <input
                  type="range"
                  min={-15}
                  max={25}
                  step={0.5}
                  value={editGrowthDelta}
                  onChange={(e) => setEditGrowthDelta(Number(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer h-2 bg-slate-100 rounded-lg"
                />
              </div>

              {/* Progressive Action Plan & Approval Selector */}
              <div className="pt-3 border-t border-slate-100 grid grid-cols-2 gap-4 text-xs">
                <div className="space-y-1.5">
                  <label className="font-bold text-slate-800">Progressive Action Plan:</label>
                  <select
                    value={editActionStatus}
                    onChange={(e) => setEditActionStatus(e.target.value as ActionPlanStatus)}
                    className="w-full py-1.5 px-3 rounded-lg border border-slate-200 bg-white font-medium text-slate-800 cursor-pointer"
                  >
                    <option value="Standard">Standard (Merit Track)</option>
                    <option value="Coaching">Tier 1: Skill Upgrade Mentoring</option>
                    <option value="PIP_Level_1">Tier 2: Constructive 60-Day PIP</option>
                    <option value="PIP_Level_2">Tier 3: Formal Statutory Review</option>
                    <option value="Escalation_Review">Tier 4: Management Committee Hearing</option>
                  </select>
                </div>
                <div className="space-y-1.5">
                  <label className="font-bold text-slate-800">Appraisal Approval Status:</label>
                  <select
                    value={editHrApproval}
                    onChange={(e) => setEditHrApproval(e.target.value as any)}
                    className="w-full py-1.5 px-3 rounded-lg border border-slate-200 bg-white font-medium text-slate-800 cursor-pointer"
                  >
                    <option value="Approved">Approved (Finalized)</option>
                    <option value="Pending Review">Pending Review</option>
                    <option value="Flagged">Flagged for Committee</option>
                  </select>
                </div>
              </div>

              {/* Manager Feedback Notes */}
              <div className="space-y-1.5 text-xs">
                <label className="font-bold text-slate-800">Manager Appraisal Comments:</label>
                <textarea
                  rows={3}
                  value={evalReviewComments}
                  onChange={(e) => setEvalReviewComments(e.target.value)}
                  placeholder="Record formal appraisal notes, developmental guidance..."
                  className="w-full p-2.5 rounded-lg border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
                />
              </div>

              <div className="pt-2 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => onOpenComplianceDoc(selectedEmployee.id)}
                  className="px-3 py-1.5 text-xs font-semibold text-rose-700 hover:text-rose-900 border border-rose-200 hover:bg-rose-50 rounded-lg flex items-center gap-1.5 cursor-pointer"
                >
                  <Scale className="w-3.5 h-3.5" />
                  Generate UAE Law Notice
                </button>
                <button
                  type="button"
                  onClick={handleSaveAppraisalForm}
                  className="px-5 py-2.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-bold transition-colors flex items-center gap-2 shadow-xs cursor-pointer"
                >
                  <Check className="w-4 h-4" />
                  Save & Finalize ({liveScoreData.finalWeightedScore} pts)
                </button>
              </div>
            </div>

            {/* Right: Direct Deliverable Points Logger */}
            <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-5">
              <div className="border-b border-slate-100 pb-3">
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-teal-600" />
                  Award Deliverable Points
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Log newly completed audit engagement deliverables
                </p>
              </div>
              <form onSubmit={handleAddDeliverableInline} className="space-y-3.5 text-xs">
                <div className="space-y-1">
                  <label className="font-bold text-slate-800">Standardized Deliverable Item:</label>
                  <select
                    value={deliverableId}
                    onChange={(e) => setDeliverableId(e.target.value)}
                    className="w-full py-1.5 px-3 rounded-lg border border-slate-200 bg-white font-medium text-slate-800 cursor-pointer"
                  >
                    {MOCK_DELIVERABLES_CATALOG.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.deliverableName} ({d.basePointValue} pts)
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="font-bold text-slate-800">Completion Quality:</label>
                    <select
                      value={deliverableStatus}
                      onChange={(e) => setDeliverableStatus(e.target.value as CompletionStatus)}
                      className="w-full py-1.5 px-2.5 rounded-lg border border-slate-200 bg-white font-medium text-slate-800 cursor-pointer"
                    >
                      <option value="Quality_Exceeded">Quality Exceeded</option>
                      <option value="On-Time">On-Time</option>
                      <option value="Delayed">Delayed Turnaround</option>
                      <option value="Needs_Revision">Needs Revision</option>
                    </select>
                  </div>
                  <div className="space-y-1">
                    <label className="font-bold text-slate-800">Turnaround (Hours):</label>
                    <input
                      type="number"
                      min={1}
                      max={120}
                      value={deliverableSlaHours}
                      onChange={(e) => setDeliverableSlaHours(Number(e.target.value))}
                      className="w-full py-1.5 px-3 rounded-lg border border-slate-200 bg-white font-mono font-bold text-slate-800"
                    />
                  </div>
                </div>
                <div className="space-y-1">
                  <label className="font-bold text-slate-800">Evaluator Constructive Notes:</label>
                  <textarea
                    rows={2}
                    value={deliverableFeedback}
                    onChange={(e) => setDeliverableFeedback(e.target.value)}
                    placeholder="Feedback notes on audit workpapers..."
                    className="w-full p-2 rounded-lg border border-slate-200 text-xs text-slate-800 bg-white"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5 shadow-xs cursor-pointer"
                >
                  <PlusCircle className="w-3.5 h-3.5" />
                  Award Deliverable Points to {selectedEmployee.fullName.split(' ')[0]}
                </button>
              </form>

              {/* Auditor's Recent Deliverables History */}
              <div className="pt-3 border-t border-slate-100 space-y-2">
                <span className="text-[11px] font-bold text-slate-700 uppercase">Recent Points Awarded:</span>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {recentEvaluations
                    .filter((e) => e.employeeId === selectedEmployee.id)
                    .slice(0, 3)
                    .map((item) => (
                      <div key={item.id} className="p-2.5 rounded-lg border border-slate-100 bg-slate-50 text-[11px] space-y-0.5">
                        <div className="flex justify-between font-bold text-slate-900">
                          <span className="truncate max-w-[200px]">{item.deliverableName}</span>
                          <span className="text-teal-700 tabular-nums">+{item.pointsAwarded.toFixed(1)} pts</span>
                        </div>
                        <p className="text-slate-500 italic truncate">"{item.feedbackNotes}"</p>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* VIEW 2: AUDITOR TEAM ROSTER */}
      {activeSubTab === 'roster' && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-5 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                <Users className="w-4 h-4 text-blue-700" />
                Practice Auditor Team Roster
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Service delivery points (50%) + SLA turnaround (25%) + Attendance (15%) + Growth delta (10%)
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search auditor..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 text-xs rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-blue-600 w-44"
                />
              </div>

              <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-lg">
                <button
                  onClick={() => setSelectedTierFilter('all')}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    selectedTierFilter === 'all'
                      ? 'bg-white text-slate-900 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSelectedTierFilter('Exceeds')}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    selectedTierFilter === 'Exceeds'
                      ? 'bg-white text-teal-800 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Exceeds
                </button>
                <button
                  onClick={() => setSelectedTierFilter('Meets')}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    selectedTierFilter === 'Meets'
                      ? 'bg-white text-blue-800 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Meets
                </button>
                <button
                  onClick={() => setSelectedTierFilter('Needs_Support')}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    selectedTierFilter === 'Needs_Support'
                      ? 'bg-white text-amber-800 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  Needs Support
                </button>
                <button
                  onClick={() => setSelectedTierFilter('Underperforming')}
                  className={`px-2.5 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    selectedTierFilter === 'Underperforming'
                      ? 'bg-white text-rose-800 shadow-xs font-semibold'
                      : 'text-slate-600 hover:text-slate-900'
                  }`}
                >
                  PIP / Review
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-50/70 border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-3 px-4">Auditor</th>
                  <th className="py-3 px-4">Role & Designation</th>
                  <th className="py-3 px-4">Tenure & Loyalty</th>
                  <th className="py-3 px-4 text-right">Base Pts</th>
                  <th className="py-3 px-4 text-right">Growth Delta</th>
                  <th className="py-3 px-4 text-right">Final Weighted</th>
                  <th className="py-3 px-4">Performance Tier</th>
                  <th className="py-3 px-4">Action Status</th>
                  <th className="py-3 px-4 text-right">Evaluation Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredTeam.map(({ member, scoreData, loyalty }) => {
                  const tierMeta = getTierMetadata(scoreData.performanceTier);
                  const isUnderperforming = scoreData.performanceTier === 'Underperforming';
                  const isNeedsSupport = scoreData.performanceTier === 'Needs_Support';

                  return (
                    <tr key={member.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-bold flex items-center justify-center text-xs shrink-0 border border-slate-200">
                            {member.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                          </div>
                          <div>
                            <button
                              onClick={() => {
                                setSelectedEmpId(member.id);
                                setActiveSubTab('evaluation_sheet');
                              }}
                              className="font-bold text-slate-900 hover:text-blue-700 transition-colors text-left cursor-pointer"
                            >
                              {member.fullName}
                            </button>
                            <div className="text-[11px] text-slate-400 font-mono tabular-nums">
                              {member.employeeIdCode}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-slate-600">
                        <div className="font-medium text-slate-900">{member.currentDesignation}</div>
                        <div className="text-[11px] text-slate-400">{member.payGradeLevel}</div>
                      </td>

                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-slate-800 tabular-nums">
                          {member.tenureYears} yrs
                        </div>
                        <div className="text-[11px] text-teal-700 font-medium">
                          {loyalty.boostPct} ({scoreData.loyaltyMultiplier.toFixed(2)}x)
                        </div>
                      </td>

                      <td className="py-3.5 px-4 text-right font-semibold text-slate-700 tabular-nums">
                        {scoreData.baseScore}
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className={`font-semibold tabular-nums inline-flex items-center gap-1 ${
                          scoreData.growthDeltaPct >= 0 ? 'text-emerald-700' : 'text-rose-600'
                        }`}>
                          {scoreData.growthDeltaPct >= 0 ? '+' : ''}{scoreData.growthDeltaPct}%
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-right">
                        <span className="text-sm font-extrabold text-slate-900 tabular-nums">
                          {scoreData.finalWeightedScore}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${tierMeta.colorClass}`}>
                          {tierMeta.label}
                        </span>
                      </td>

                      <td className="py-3.5 px-4">
                        {isUnderperforming ? (
                          <span className="text-[11px] font-semibold text-rose-700 flex items-center gap-1">
                            <ShieldAlert className="w-3.5 h-3.5" /> 60-Day PIP
                          </span>
                        ) : isNeedsSupport ? (
                          <span className="text-[11px] font-semibold text-amber-700 flex items-center gap-1">
                            <Sparkles className="w-3.5 h-3.5" /> Skill Upgrade
                          </span>
                        ) : (
                          <span className="text-[11px] font-medium text-slate-500">
                            Standard Merit
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-right space-x-1 whitespace-nowrap">
                        <button
                          onClick={() => {
                            setSelectedEmpId(member.id);
                            setActiveSubTab('evaluation_sheet');
                          }}
                          className="px-2.5 py-1 text-xs font-bold text-white bg-blue-700 hover:bg-blue-800 rounded transition-colors cursor-pointer"
                          title="Open full evaluation sheet"
                        >
                          Evaluate
                        </button>
                        <button
                          onClick={() => onOpenQuickEval(member.id)}
                          className="px-2 py-1 text-[11px] font-medium text-blue-700 hover:text-blue-900 hover:bg-blue-50 rounded transition-colors cursor-pointer"
                          title="Award deliverable points"
                        >
                          + Pts
                        </button>
                        <button
                          onClick={() => onOpenAddCoaching(member.id)}
                          className="px-2 py-1 text-[11px] font-medium text-teal-700 hover:text-teal-900 hover:bg-teal-50 rounded transition-colors cursor-pointer"
                          title="Add coaching notes"
                        >
                          Coach
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* VIEW 3: DELIVERABLES LEDGER */}
      {activeSubTab === 'deliverables' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Practice Service Deliverables Log
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Objective point evaluations against standardized service catalog
              </p>
            </div>
            <button
              onClick={() => onOpenQuickEval()}
              className="px-3.5 py-1.5 rounded-lg bg-blue-700 hover:bg-blue-800 text-white text-xs font-semibold cursor-pointer"
            >
              + Log New Task
            </button>
          </div>
          <div className="divide-y divide-slate-100">
            {recentEvaluations.map((item) => (
              <div key={item.id} className="py-3 text-xs space-y-1">
                <div className="flex items-start justify-between">
                  <div>
                    <span className="font-bold text-slate-900">{item.employeeName}</span>
                    <span className="text-slate-400 mx-1.5">•</span>
                    <span className="text-slate-700 font-medium">{item.deliverableName}</span>
                  </div>
                  <span className="font-black text-teal-800 tabular-nums">
                    +{item.pointsAwarded.toFixed(1)} pts
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 flex items-center gap-2">
                  <span>Evaluated by {item.evaluatorName}</span>
                  <span aria-hidden="true">•</span>
                  <span>Turnaround: {item.slaHoursTurnaround}h</span>
                  <span aria-hidden="true">•</span>
                  <span className="font-semibold text-slate-700">{item.completionStatus.replace('_', ' ')}</span>
                  <span aria-hidden="true">•</span>
                  <span>{item.evaluatedDate}</span>
                </div>
                <p className="text-slate-600 bg-slate-50 p-2.5 rounded border border-slate-100 text-[11px]">
                  "{item.feedbackNotes}"
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* VIEW 4: PROGRESSIVE SUPPORT & PIP TRACKER */}
      {activeSubTab === 'pip_tracker' && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-6">
          <div className="border-b border-slate-100 pb-3">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose-600" />
              Progressive Escalation & Mentorship Trackers
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Active Tier 1 (Skill Upgrade) and Tier 2 (Constructive 60-Day PIP) interventions
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {teamRows
              .filter((r) => r.scoreData.performanceTier === 'Underperforming' || r.scoreData.performanceTier === 'Needs_Support')
              .map(({ member, scoreData }) => {
                const isUnder = scoreData.performanceTier === 'Underperforming';
                return (
                  <div key={member.id} className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-800 font-bold flex items-center justify-center text-xs">
                          {member.fullName.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                        </div>
                        <div>
                          <div className="font-bold text-slate-900 text-xs">{member.fullName}</div>
                          <div className="text-[11px] text-slate-500">{member.currentDesignation}</div>
                        </div>
                      </div>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        isUnder ? 'bg-rose-50 text-rose-800 border-rose-200' : 'bg-amber-50 text-amber-800 border-amber-200'
                      }`}>
                        {isUnder ? 'Tier 2: 60-Day PIP' : 'Tier 1: Skill Upgrade'}
                      </span>
                    </div>
                    <div className="text-xs space-y-1.5">
                      <div className="flex justify-between text-slate-600">
                        <span>Current Cycle Score:</span>
                        <span className="font-bold text-slate-900 tabular-nums">{scoreData.finalWeightedScore} pts</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Improvement Delta:</span>
                        <span className="font-bold text-rose-600 tabular-nums">{scoreData.growthDeltaPct}%</span>
                      </div>
                      <div className="flex justify-between text-slate-600">
                        <span>Supervisor Assigned:</span>
                        <span className="font-semibold text-slate-800">{managerUser.fullName}</span>
                      </div>
                    </div>
                    <div className="pt-2 border-t border-slate-200 flex items-center justify-between">
                      <button
                        onClick={() => {
                          setSelectedEmpId(member.id);
                          setActiveSubTab('evaluation_sheet');
                        }}
                        className="text-xs font-bold text-blue-700 hover:text-blue-900 cursor-pointer"
                      >
                        Open Evaluation Sheet →
                      </button>
                      <button
                        onClick={() => onOpenComplianceDoc(member.id)}
                        className="text-xs font-semibold text-rose-700 hover:text-rose-900 cursor-pointer"
                      >
                        Print Law Notice
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      )}
    </div>
  );
};
