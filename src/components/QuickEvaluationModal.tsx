import React from 'react';
import { User, ServiceDeliverableCatalog, TaskEvaluation, CompletionStatus } from '../types';
import { MOCK_USERS, MOCK_DELIVERABLES_CATALOG } from '../data/mockData';
import { X, CheckCircle2, PlusCircle, Clock, Award } from 'lucide-react';

interface QuickEvaluationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveEvaluation: (evaluation: TaskEvaluation) => void;
  defaultEmployeeId?: string;
  evaluatorUser: User;
}

export const QuickEvaluationModal: React.FC<QuickEvaluationModalProps> = ({
  isOpen,
  onClose,
  onSaveEvaluation,
  defaultEmployeeId,
  evaluatorUser,
}) => {
  const [employeeId, setEmployeeId] = React.useState<string>(defaultEmployeeId || 'emp-zayed');
  const [deliverableId, setDeliverableId] = React.useState<string>(MOCK_DELIVERABLES_CATALOG[0].id);
  const [completionStatus, setCompletionStatus] = React.useState<CompletionStatus>('Quality_Exceeded');
  const [slaHoursTurnaround, setSlaHoursTurnaround] = React.useState<number>(24);
  const [feedbackNotes, setFeedbackNotes] = React.useState<string>('Thorough working papers and clear audit disclosures.');

  React.useEffect(() => {
    if (defaultEmployeeId) {
      setEmployeeId(defaultEmployeeId);
    }
  }, [defaultEmployeeId]);

  if (!isOpen) return null;

  const selectedDeliverable = MOCK_DELIVERABLES_CATALOG.find((d) => d.id === deliverableId) || MOCK_DELIVERABLES_CATALOG[0];
  const selectedEmployee = MOCK_USERS.find((u) => u.id === employeeId) || MOCK_USERS[3];

  const calculatePoints = () => {
    let multiplier = 1.0;
    if (completionStatus === 'Quality_Exceeded') multiplier = selectedDeliverable.qualityWeightage;
    else if (completionStatus === 'On-Time') multiplier = 1.0;
    else if (completionStatus === 'Delayed') multiplier = 0.85;
    else if (completionStatus === 'Needs_Revision') multiplier = 0.75;
    const pts = selectedDeliverable.basePointValue * multiplier;
    return Math.min(100, Math.round(pts * 10) / 10);
  };

  const currentPoints = calculatePoints();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newEval: TaskEvaluation = {
      id: `eval-${Date.now()}`,
      employeeId,
      employeeName: selectedEmployee.fullName,
      deliverableId: selectedDeliverable.id,
      deliverableName: selectedDeliverable.deliverableName,
      departmentId: selectedEmployee.departmentId,
      evaluatorId: evaluatorUser.id,
      evaluatorName: evaluatorUser.fullName,
      completionStatus,
      pointsAwarded: currentPoints,
      taskDeadline: '2026-10-10 18:00',
      actualCompletionTimestamp: '2026-10-10 15:45',
      slaHoursTurnaround,
      feedbackNotes,
      evaluatedDate: new Date().toISOString().split('T')[0],
    };
    onSaveEvaluation(newEval);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-700 text-white flex items-center justify-center">
              <PlusCircle className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                Log Service Deliverable Points
              </h3>
              <p className="text-xs text-slate-500">
                Award points based on standardized Paras Advisory deliverable catalog
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4 text-xs">
          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Assign to Auditor / Team Member:</label>
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
            >
              {MOCK_USERS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.fullName} ({u.employeeIdCode}) — {u.currentDesignation}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Standardized Deliverable Item:</label>
            <select
              value={deliverableId}
              onChange={(e) => setDeliverableId(e.target.value)}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
            >
              {MOCK_DELIVERABLES_CATALOG.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.deliverableName} (Base: {d.basePointValue} pts, SLA: {d.slaHoursExpected}h)
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-500">{selectedDeliverable.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="font-bold text-slate-800">Completion Quality & SLA:</label>
              <select
                value={completionStatus}
                onChange={(e) => setCompletionStatus(e.target.value as CompletionStatus)}
                className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600 cursor-pointer"
              >
                <option value="Quality_Exceeded">Quality Exceeded ({selectedDeliverable.qualityWeightage}x)</option>
                <option value="On-Time">On-Time (1.0x)</option>
                <option value="Delayed">Delayed SLA (0.85x)</option>
                <option value="Needs_Revision">Needs Revision (0.75x)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="font-bold text-slate-800">Actual Turnaround (Hours):</label>
              <input
                type="number"
                min={1}
                max={120}
                value={slaHoursTurnaround}
                onChange={(e) => setSlaHoursTurnaround(Number(e.target.value))}
                className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-mono font-bold text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Constructive Feedback & Notes:</label>
            <textarea
              rows={3}
              value={feedbackNotes}
              onChange={(e) => setFeedbackNotes(e.target.value)}
              placeholder="Provide growth-oriented comments, technical observations, and feedback..."
              className="w-full p-2.5 rounded-lg border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-blue-600"
            />
          </div>

          <div className="p-3.5 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-between">
            <div>
              <span className="text-[11px] font-bold text-teal-900 uppercase">Calculated Deliverable Points:</span>
              <p className="text-[11px] text-teal-700">Base {selectedDeliverable.basePointValue} × Quality Multiplier</p>
            </div>
            <div className="text-right">
              <span className="text-2xl font-black text-teal-900 tabular-nums">{currentPoints}</span>
              <span className="text-xs text-teal-700 block">/ 100 max</span>
            </div>
          </div>

          <div className="pt-2 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-5 py-2 rounded-lg bg-blue-700 hover:bg-blue-800 text-white font-bold transition-colors cursor-pointer"
            >
              Confirm & Award Points
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
