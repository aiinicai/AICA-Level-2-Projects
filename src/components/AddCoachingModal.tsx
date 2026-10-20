import React from 'react';
import { User, CoachingNote } from '../types';
import { MOCK_USERS } from '../data/mockData';
import { X, MessageSquare, CheckCircle2, Calendar } from 'lucide-react';

interface AddCoachingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveCoaching: (note: CoachingNote) => void;
  defaultEmployeeId?: string;
  authorUser: User;
}

export const AddCoachingModal: React.FC<AddCoachingModalProps> = ({
  isOpen,
  onClose,
  onSaveCoaching,
  defaultEmployeeId,
  authorUser,
}) => {
  const [employeeId, setEmployeeId] = React.useState<string>(defaultEmployeeId || 'emp-zayed');
  const [objective, setObjective] = React.useState<string>('Sovereign Client Audit Workpaper Acceleration');
  const [guidance, setGuidance] = React.useState<string>(
    'Reviewed IFRS disclosure documentation. Encouraged auditor to leverage standardized Excel macros to shorten audit turnaround by 3 hours. Scheduled senior peer pairing.'
  );
  const [followUpDate, setFollowUpDate] = React.useState<string>('2026-11-10');

  React.useEffect(() => {
    if (defaultEmployeeId) {
      setEmployeeId(defaultEmployeeId);
    }
  }, [defaultEmployeeId]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newNote: CoachingNote = {
      id: `coach-${Date.now()}`,
      employeeId,
      authorId: authorUser.id,
      authorName: authorUser.fullName,
      date: new Date().toISOString().split('T')[0],
      objective,
      constructiveGuidance: guidance,
      followUpDate,
      status: 'In Progress',
      skillArea: objective,
      noteText: guidance,
    };
    onSaveCoaching(newNote);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/60 backdrop-blur-xs p-4 overflow-y-auto">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-teal-700 text-white flex items-center justify-center">
              <MessageSquare className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900 leading-tight">
                Log Constructive Coaching Session
              </h3>
              <p className="text-xs text-slate-500">
                Document 1-on-1 developmental support and mentoring objectives
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
            <label className="font-bold text-slate-800">Auditor / Team Member:</label>
            <select
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-teal-600 cursor-pointer"
            >
              {MOCK_USERS.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.fullName} ({u.employeeIdCode}) — {u.currentDesignation}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Mentorship Objective / Target Skill:</label>
            <input
              type="text"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              placeholder="e.g. Sampling Methodology Optimization"
              className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-teal-600"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Constructive Guidance & Agreed Action:</label>
            <textarea
              rows={4}
              value={guidance}
              onChange={(e) => setGuidance(e.target.value)}
              placeholder="Record encouraging observations, supportive recommendations, and next milestones..."
              className="w-full p-2.5 rounded-lg border border-slate-200 text-xs text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-teal-600"
            />
          </div>

          <div className="space-y-1.5">
            <label className="font-bold text-slate-800">Follow-up Milestone Checkpoint:</label>
            <input
              type="date"
              value={followUpDate}
              onChange={(e) => setFollowUpDate(e.target.value)}
              className="w-full py-2 px-3 rounded-lg border border-slate-200 text-xs font-medium text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-teal-600"
            />
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
              className="px-5 py-2 rounded-lg bg-teal-700 hover:bg-teal-800 text-white font-bold transition-colors cursor-pointer"
            >
              Save Coaching Entry
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
