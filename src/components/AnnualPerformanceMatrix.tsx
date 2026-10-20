import React from 'react';
import { 
  User, 
  AnnualPerformancePlan, 
  AnnualGoalItem, 
  AppraisalRecord,
  AttendanceRecord 
} from '../types';
import { 
  Target, 
  CheckCircle2, 
  Clock, 
  Award, 
  Calendar, 
  PlusCircle, 
  Edit3, 
  Send, 
  ShieldCheck, 
  Check, 
  AlertCircle,
  TrendingUp,
  FileText,
  Download,
  Printer
} from 'lucide-react';
import { exportToWord, exportToPdf, generatePerformanceMatrixHtml } from '../utils/reportExporter';
import { KPIProgressChart } from './KPIProgressChart';

interface AnnualPerformanceMatrixProps {
  currentUser: User;
  employeeUser: User;
  plan: AnnualPerformancePlan;
  attendanceRecords: AttendanceRecord[];
  appraisalRecord?: AppraisalRecord;
  onSavePlan: (updatedPlan: AnnualPerformancePlan) => void;
  onApprovePlan: (planId: string, notes: string) => void;
  onFinalAssess: (planId: string, assessedScore: number) => void;
}

export const AnnualPerformanceMatrix: React.FC<AnnualPerformanceMatrixProps> = ({
  currentUser,
  employeeUser,
  plan,
  attendanceRecords,
  appraisalRecord,
  onSavePlan,
  onApprovePlan,
  onFinalAssess,
}) => {
  const isManagerOrAdmin = currentUser.role === 'department_manager' || currentUser.role === 'super_admin' || currentUser.role === 'hr_manager';
  const isEmployeeOwner = currentUser.id === employeeUser.id;

  // Local editable state for goals
  const [goals, setGoals] = React.useState<AnnualGoalItem[]>(plan.goals);
  const [managerNotes, setManagerNotes] = React.useState<string>(plan.managerApprovalNotes || '');
  const [showAddGoalModal, setShowAddGoalModal] = React.useState<boolean>(false);
  const [notification, setNotification] = React.useState<string | null>(null);

  // New goal state
  const [newTitle, setNewTitle] = React.useState<string>('Sovereign Client Audit File Closure');
  const [newCategory, setNewCategory] = React.useState<string>('Core Service Delivery');
  const [newWeight, setNewWeight] = React.useState<number>(25);
  const [newDeliverableTarget, setNewDeliverableTarget] = React.useState<number>(10);
  const [newSlaTarget, setNewSlaTarget] = React.useState<number>(36);
  const [newQualityTarget, setNewQualityTarget] = React.useState<number>(95);

  const totalWeightage = goals.reduce((acc, curr) => acc + curr.weightagePct, 0);

  // Punctuality index from prefilled HR records
  const onTimeCount = attendanceRecords.filter((a) => a.status === 'On-Time').length;
  const attendanceRate = attendanceRecords.length > 0
    ? Math.round((onTimeCount / attendanceRecords.length) * 100)
    : 95;

  const handleUpdateGoalField = (goalId: string, field: keyof AnnualGoalItem, value: any) => {
    setGoals((prev) =>
      prev.map((g) => (g.id === goalId ? { ...g, [field]: value } : g))
    );
  };

  const handleAddGoal = (e: React.FormEvent) => {
    e.preventDefault();
    const newGoalItem: AnnualGoalItem = {
      id: `g-${Date.now()}`,
      title: newTitle,
      category: newCategory,
      weightagePct: newWeight,
      targetDeliverableCount: newDeliverableTarget,
      actualAchievedCount: 0,
      targetSlaHours: newSlaTarget,
      actualAvgSlaHours: newSlaTarget,
      targetQualityScore: newQualityTarget,
      actualQualityScore: 0,
      achievementNarrative: '',
      managerAssessmentScore: 85,
    };
    const updated = [...goals, newGoalItem];
    setGoals(updated);
    setShowAddGoalModal(false);
    onSavePlan({ ...plan, goals: updated, lastUpdated: new Date().toISOString().split('T')[0] });
    setNotification('Goal added to annual matrix draft.');
    setTimeout(() => setNotification(null), 3000);
  };

  const handleSubmitPlanToManager = () => {
    const updated: AnnualPerformancePlan = {
      ...plan,
      goals,
      planStatus: 'Submitted_To_Manager',
      lastUpdated: new Date().toISOString().split('T')[0],
    };
    onSavePlan(updated);
    setNotification('Annual performance plan submitted to practice manager for formal approval.');
    setTimeout(() => setNotification(null), 3500);
  };

  const handleManagerApprove = () => {
    onApprovePlan(plan.id, managerNotes || 'Approved. Practice manager verified technical targets.');
    setNotification('Annual performance matrix approved! Employee may now fill in achievements.');
    setTimeout(() => setNotification(null), 3500);
  };

  const handleSubmitAchievements = () => {
    const updated: AnnualPerformancePlan = {
      ...plan,
      goals,
      planStatus: 'Achievement_Submitted',
      lastUpdated: new Date().toISOString().split('T')[0],
    };
    onSavePlan(updated);
    setNotification('Achievement matrix submitted for manager assessment.');
    setTimeout(() => setNotification(null), 3500);
  };

  const handleCalculateAndFinalizeAssessment = () => {
    let weightedSum = 0;
    goals.forEach((g) => {
      weightedSum += (g.weightagePct / 100) * (g.managerAssessmentScore || 85);
    });
    const finalScore = Math.round(weightedSum * 10) / 10;
    onFinalAssess(plan.id, finalScore);
    setNotification(`Annual assessment finalized! Final assessed score: ${finalScore} points.`);
    setTimeout(() => setNotification(null), 3500);
  };

  const handleExportWord = () => {
    const html = generatePerformanceMatrixHtml(plan, employeeUser, 'Tariq Al Hammadi');
    exportToWord({
      title: `Annual Performance Matrix: ${employeeUser.fullName}`,
      subtitle: `Year ${plan.year} Objective Deliverables & Evaluation Matrix • Paras Accounting & Auditing Advisory`,
      filename: `Annual_Matrix_${employeeUser.fullName.replace(/\s+/g, '_')}_${plan.year}`,
      officialRefCode: `PAA-MAT-${plan.year}-${employeeUser.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  const handleExportPdf = () => {
    const html = generatePerformanceMatrixHtml(plan, employeeUser, 'Tariq Al Hammadi');
    exportToPdf({
      title: `Annual Performance Matrix: ${employeeUser.fullName}`,
      subtitle: `Year ${plan.year} Objective Deliverables & Evaluation Matrix • Paras Accounting & Auditing Advisory`,
      filename: `Annual_Matrix_${employeeUser.fullName.replace(/\s+/g, '_')}_${plan.year}`,
      officialRefCode: `PAA-MAT-${plan.year}-${employeeUser.employeeIdCode.replace('EMP-', '')}`,
      contentHtml: html,
    });
  };

  return (
    <div className="space-y-6">
      {/* Header & Status Indicator */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold text-teal-800 uppercase tracking-wider">
            <Target className="w-4 h-4 text-teal-600" />
            <span>Annual Performance Matrix & Achievement Cycle</span>
            <span className="text-slate-300">•</span>
            <span className="text-slate-500 font-mono">Year {plan.year}</span>
          </div>
          <h2 className="text-xl font-bold text-slate-900 mt-1">
            Annual Objective Plan: {employeeUser.fullName}
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {employeeUser.currentDesignation} • Practice: {employeeUser.departmentName}
          </p>
        </div>

        {/* Workflow Status Badge & Action */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <div className="flex items-center gap-2">
            <button
              onClick={handleExportWord}
              className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Download Annual Matrix as Word document"
            >
              <Download className="w-3.5 h-3.5 text-blue-700" />
              Word (.doc)
            </button>
            <button
              onClick={handleExportPdf}
              className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs transition-colors flex items-center gap-1.5 cursor-pointer"
              title="Print or Save Annual Matrix as PDF"
            >
              <Printer className="w-3.5 h-3.5 text-teal-700" />
              PDF
            </button>
          </div>

          <div className="px-3.5 py-1.5 rounded-lg border text-xs font-bold">
            {plan.planStatus === 'Draft' && (
              <span className="text-slate-700 bg-slate-100 border-slate-200 px-2 py-0.5 rounded">
                Plan Setup in Progress (Draft)
              </span>
            )}
            {plan.planStatus === 'Submitted_To_Manager' && (
              <span className="text-blue-800 bg-blue-50 border-blue-200 px-2 py-0.5 rounded">
                Awaiting Manager Plan Approval
              </span>
            )}
            {plan.planStatus === 'Manager_Approved' && (
              <span className="text-teal-800 bg-teal-50 border-teal-200 px-2 py-0.5 rounded">
                Plan Approved • Achievement Tracking Active
              </span>
            )}
            {plan.planStatus === 'Achievement_Submitted' && (
              <span className="text-amber-800 bg-amber-50 border-amber-200 px-2 py-0.5 rounded">
                Achievements Submitted • Ready for Final Assessment
              </span>
            )}
            {plan.planStatus === 'Final_Assessed' && (
              <span className="text-purple-800 bg-purple-50 border-purple-200 px-2 py-0.5 rounded">
                Final Assessed: {plan.assessedScore} Pts
              </span>
            )}
          </div>

          {notification && (
            <div className="text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-200 px-3 py-1 rounded-md animate-in fade-in">
              {notification}
            </div>
          )}
        </div>
      </div>

      {/* Prefilled HR Controls Banner (Length of Service + Attendance) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-1">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Award className="w-3.5 h-3.5 text-teal-600" />
            <span>Prefilled HR Service Record</span>
          </div>
          <div className="text-2xl font-black text-slate-900 tabular-nums">
            {employeeUser.tenureYears} Years
          </div>
          <div className="text-xs text-teal-700 font-medium">
            Active Loyalty Multiplier: {(employeeUser.tenureYears >= 8 ? 1.15 : employeeUser.tenureYears >= 5 ? 1.10 : employeeUser.tenureYears >= 2 ? 1.05 : 1.00).toFixed(2)}x boost
          </div>
          <p className="text-[11px] text-slate-400">Prefilled directly from Paras Advisory HR records.</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-1">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-blue-600" />
            <span>HR Attendance Control Matrix</span>
          </div>
          <div className="text-2xl font-black text-slate-900 tabular-nums">
            {attendanceRate}% Punctual
          </div>
          <div className="text-xs text-blue-700 font-medium">
            Standard 08:30 AM arrival with 15-min grace window
          </div>
          <p className="text-[11px] text-slate-400">Prefilled via biometric office attendance controls.</p>
        </div>

        <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs space-y-1">
          <div className="text-xs font-bold text-slate-500 uppercase tracking-wider flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-indigo-600" />
            <span>Matrix Weightage Balance</span>
          </div>
          <div className="text-2xl font-black text-slate-900 tabular-nums">
            {totalWeightage}% / 100%
          </div>
          <div className={`text-xs font-semibold ${totalWeightage === 100 ? 'text-teal-700' : 'text-amber-700'}`}>
            {totalWeightage === 100 ? 'Balanced 100% Allocation' : `Variance: ${100 - totalWeightage}% required`}
          </div>
          <p className="text-[11px] text-slate-400">Distributed across core delivery & assurance.</p>
        </div>
      </div>

      {/* Interactive Annual KPI Progress & Trajectory Chart */}
      <KPIProgressChart 
        plan={plan} 
        employeeUser={employeeUser} 
        appraisalRecord={appraisalRecord} 
      />

      {/* Goal Matrix Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Annual Performance & Achievement Matrix Table
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Employee sets targets • Manager approves • Employee logs achievements • App assesses score
            </p>
          </div>
          {plan.planStatus === 'Draft' && (
            <button
              onClick={() => setShowAddGoalModal(true)}
              className="px-3 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              Add Annual Goal
            </button>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold">
                <th className="py-3 px-4">Goal & Category</th>
                <th className="py-3 px-3 text-center">Weight</th>
                <th className="py-3 px-3 text-center">Target Qty</th>
                <th className="py-3 px-3 text-center">Actual Achieved</th>
                <th className="py-3 px-3 text-center">Target SLA</th>
                <th className="py-3 px-3 text-center">Target Quality</th>
                <th className="py-3 px-4">Achievement Narrative</th>
                <th className="py-3 px-3 text-right">Assessed Pts</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {goals.map((g) => {
                const isApproved = plan.planStatus !== 'Draft' && plan.planStatus !== 'Submitted_To_Manager';
                return (
                  <tr key={g.id} className="hover:bg-slate-50/50">
                    <td className="py-3.5 px-4">
                      <div className="font-bold text-slate-900">{g.title}</div>
                      <div className="text-[11px] text-slate-400">{g.category}</div>
                    </td>
                    <td className="py-3.5 px-3 text-center font-bold text-slate-800 tabular-nums">
                      {g.weightagePct}%
                    </td>
                    <td className="py-3.5 px-3 text-center font-semibold text-slate-700 tabular-nums">
                      {g.targetDeliverableCount}
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      {isApproved && (isEmployeeOwner || isManagerOrAdmin) ? (
                        <input
                          type="number"
                          min={0}
                          max={50}
                          value={g.actualAchievedCount}
                          onChange={(e) => handleUpdateGoalField(g.id, 'actualAchievedCount', Number(e.target.value))}
                          className="w-16 py-1 px-2 border border-slate-200 rounded text-center font-bold text-teal-800 bg-white"
                        />
                      ) : (
                        <span className="font-bold text-teal-800 tabular-nums">{g.actualAchievedCount}</span>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-center tabular-nums text-slate-600">
                      {g.targetSlaHours}h
                    </td>
                    <td className="py-3.5 px-3 text-center tabular-nums font-semibold text-slate-700">
                      {g.targetQualityScore} pts
                    </td>
                    <td className="py-3.5 px-4">
                      {isApproved && (isEmployeeOwner || isManagerOrAdmin) ? (
                        <textarea
                          rows={2}
                          value={g.achievementNarrative}
                          onChange={(e) => handleUpdateGoalField(g.id, 'achievementNarrative', e.target.value)}
                          placeholder="Employee notes on completed deliverables..."
                          className="w-full p-1.5 border border-slate-200 rounded text-[11px] text-slate-800 bg-white"
                        />
                      ) : (
                        <span className="text-[11px] text-slate-600 italic">
                          {g.achievementNarrative || 'Pending completion.'}
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-right">
                      {isManagerOrAdmin && plan.planStatus === 'Achievement_Submitted' ? (
                        <input
                          type="number"
                          min={0}
                          max={100}
                          value={g.managerAssessmentScore}
                          onChange={(e) => handleUpdateGoalField(g.id, 'managerAssessmentScore', Number(e.target.value))}
                          className="w-16 py-1 px-2 border border-blue-300 rounded text-right font-black text-blue-900 bg-blue-50/50"
                        />
                      ) : (
                        <span className="font-black text-slate-900 tabular-nums">
                          {g.managerAssessmentScore} pts
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Manager Review Notes & Actions Bar */}
        <div className="p-5 bg-slate-50 border-t border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="text-xs text-slate-600 flex-1">
            {plan.managerApprovalNotes && (
              <div>
                <strong>Manager Note:</strong> "{plan.managerApprovalNotes}"
                {plan.managerApprovedBy && <span className="text-slate-400 ml-1.5">• {plan.managerApprovedBy}</span>}
              </div>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            {plan.planStatus === 'Draft' && isEmployeeOwner && (
              <button
                onClick={handleSubmitPlanToManager}
                className="px-4 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                Submit Plan to Manager for Approval
              </button>
            )}
            {plan.planStatus === 'Submitted_To_Manager' && isManagerOrAdmin && (
              <button
                onClick={handleManagerApprove}
                className="px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
              >
                <Check className="w-3.5 h-3.5" />
                Approve Employee Annual Plan
              </button>
            )}
            {plan.planStatus === 'Manager_Approved' && isEmployeeOwner && (
              <button
                onClick={handleSubmitAchievements}
                className="px-4 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
              >
                <Send className="w-3.5 h-3.5" />
                Submit Achievements for Assessment
              </button>
            )}
            {plan.planStatus === 'Achievement_Submitted' && isManagerOrAdmin && (
              <button
                onClick={handleCalculateAndFinalizeAssessment}
                className="px-4 py-2 rounded-lg bg-purple-700 hover:bg-purple-800 text-white font-bold text-xs flex items-center gap-1.5 transition-colors shadow-xs cursor-pointer"
              >
                <Award className="w-3.5 h-3.5" />
                Finalize Annual Assessment & Score
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Modal: Add Goal Item */}
      {showAddGoalModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg p-6 space-y-4 text-xs animate-in fade-in">
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Add Annual Performance Goal
            </h3>
            <div className="space-y-3">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Goal Title:</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Category:</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs bg-white"
                  >
                    <option value="Core Service Delivery">Core Service Delivery</option>
                    <option value="Quality & Assurance">Quality & Assurance</option>
                    <option value="People & Leadership">People & Leadership</option>
                    <option value="Professional Excellence">Professional Excellence</option>
                  </select>
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Weightage (%):</label>
                  <input
                    type="number"
                    min={5}
                    max={100}
                    value={newWeight}
                    onChange={(e) => setNewWeight(Number(e.target.value))}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Target Count:</label>
                  <input
                    type="number"
                    min={1}
                    value={newDeliverableTarget}
                    onChange={(e) => setNewDeliverableTarget(Number(e.target.value))}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Target SLA (h):</label>
                  <input
                    type="number"
                    min={1}
                    value={newSlaTarget}
                    onChange={(e) => setNewSlaTarget(Number(e.target.value))}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
                <div>
                  <label className="font-semibold text-slate-700 block mb-1">Quality Target:</label>
                  <input
                    type="number"
                    min={50}
                    max={100}
                    value={newQualityTarget}
                    onChange={(e) => setNewQualityTarget(Number(e.target.value))}
                    className="w-full p-2 border border-slate-200 rounded-lg text-xs"
                  />
                </div>
              </div>
            </div>
            <div className="pt-2 flex justify-end gap-2 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowAddGoalModal(false)}
                className="px-3 py-1.5 rounded-lg border border-slate-200 text-slate-600 cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleAddGoal}
                className="px-4 py-1.5 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold cursor-pointer"
              >
                Save Goal
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
