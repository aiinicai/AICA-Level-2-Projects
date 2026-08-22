import React, { useState } from 'react';
import {
  CheckCircle2,
  XCircle,
  PauseCircle,
  Slash,
  Edit3,
  ShieldCheck,
  UserCheck,
  MessageSquare,
  AlertTriangle,
  Info,
  History,
  Eye,
} from 'lucide-react';
import { ClientAdvisory, ApprovalStatus } from '../types';

interface ApprovalCentreViewProps {
  advisories: ClientAdvisory[];
  onUpdateStatus: (advisoryId: string, status: ApprovalStatus, reviewerNotes?: string) => void;
  onUpdateAdvisoryContent: (advisoryId: string, updatedFormal: any) => void;
}

export const ApprovalCentreView: React.FC<ApprovalCentreViewProps> = ({
  advisories,
  onUpdateStatus,
  onUpdateAdvisoryContent,
}) => {
  const [filterStatus, setFilterStatus] = useState<string>('All');
  const [selectedAdvisory, setSelectedAdvisory] = useState<ClientAdvisory | null>(
    advisories.length > 0 ? advisories[0] : null
  );

  const [reviewerNotes, setReviewerNotes] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [showOriginal, setShowOriginal] = useState(false);
  const [editSubject, setEditSubject] = useState('');
  const [editAction, setEditAction] = useState('');

  const filteredAdvisories = advisories.filter((a) => {
    if (filterStatus === 'All') return true;
    return a.approvalStatus === filterStatus;
  });

  const activeAdvisory = selectedAdvisory || (filteredAdvisories.length > 0 ? filteredAdvisories[0] : null);

  const handleStartEdit = () => {
    if (!activeAdvisory) return;
    setEditSubject(activeAdvisory.formalAdvisory.subject);
    setEditAction(activeAdvisory.formalAdvisory.requiredAction);
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    if (!activeAdvisory) return;
    onUpdateAdvisoryContent(activeAdvisory.id, {
      ...activeAdvisory.formalAdvisory,
      subject: editSubject,
      requiredAction: editAction,
    });
    setIsEditing(false);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-teal-600 mb-1">
            <UserCheck className="w-4 h-4" />
            <span>MODULE 8 — HUMAN-IN-THE-LOOP CA APPROVAL CENTRE V2</span>
          </div>
          <h1 className="text-xl font-bold text-slate-900">CA Review & Sign-Off Dashboard</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Mandatory review control. Original AI draft is preserved separately when edited.
          </p>
        </div>
      </div>

      {/* Control Banner */}
      <div className="p-4 bg-teal-50 border border-teal-200/80 rounded-2xl flex items-center space-x-3 text-xs text-teal-950">
        <ShieldCheck className="w-5 h-5 text-teal-700 shrink-0" />
        <div>
          <span className="font-bold">CA Professional Sign-off Protocol:</span> AI-generated professional draft — CA human review required before external client dispatch. Circular and reference numbers must be verified against source facts.
        </div>
      </div>

      {/* Filter Pills */}
      <div className="flex items-center space-x-2 text-xs overflow-x-auto pb-1">
        {['All', 'Pending Review', 'Approved', 'Hold', 'Rejected', 'Not Applicable'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-xl font-bold transition-all cursor-pointer ${
              filterStatus === st
                ? 'bg-slate-900 text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {st}
          </button>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Advisories Queue */}
        <div className="lg:col-span-5 space-y-2">
          {filteredAdvisories.length === 0 ? (
            <div className="p-8 text-center bg-white border border-slate-200 rounded-2xl text-xs text-slate-500">
              No advisories matching status "{filterStatus}".
            </div>
          ) : (
            filteredAdvisories.map((adv) => {
              const isSelected = activeAdvisory?.id === adv.id;
              return (
                <div
                  key={adv.id}
                  onClick={() => {
                    setSelectedAdvisory(adv);
                    setIsEditing(false);
                    setShowOriginal(false);
                    setReviewerNotes(adv.reviewerNotes || '');
                  }}
                  className={`p-4 rounded-2xl border text-xs cursor-pointer transition-all ${
                    isSelected
                      ? 'bg-teal-50/90 border-teal-500 shadow-xs'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-slate-900">{adv.clientName}</span>
                    <span
                      className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                        adv.approvalStatus === 'Approved'
                          ? 'bg-emerald-100 text-emerald-800'
                          : adv.approvalStatus === 'Pending Review'
                          ? 'bg-amber-100 text-amber-800'
                          : adv.approvalStatus === 'Hold'
                          ? 'bg-teal-100 text-teal-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {adv.approvalStatus}
                    </span>
                  </div>

                  <p className="text-[11px] text-slate-600 line-clamp-2 mt-1">
                    {adv.formalAdvisory.subject}
                  </p>
                </div>
              );
            })
          )}
        </div>

        {/* Right Action & Review Details Panel */}
        <div className="lg:col-span-7">
          {activeAdvisory ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-xs space-y-5">
              <div className="flex items-start justify-between border-b border-slate-100 pb-3">
                <div>
                  <span className="text-[10px] uppercase font-bold text-teal-700 block">Reviewing Advisory For</span>
                  <h2 className="text-lg font-bold text-slate-900">{activeAdvisory.clientName}</h2>
                </div>
                <div className="flex items-center space-x-2">
                  {activeAdvisory.originalFormalAdvisory && (
                    <button
                      onClick={() => setShowOriginal(!showOriginal)}
                      className="flex items-center space-x-1 px-3 py-1 bg-slate-100 text-slate-700 text-xs font-bold rounded-lg border border-slate-200 hover:bg-slate-200"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>{showOriginal ? 'Show Edited' : 'View Original Draft'}</span>
                    </button>
                  )}
                  <span
                    className={`text-xs font-bold px-3 py-1 rounded-full ${
                      activeAdvisory.approvalStatus === 'Approved'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {activeAdvisory.approvalStatus}
                  </span>
                </div>
              </div>

              {/* Action Buttons Row */}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <button
                  onClick={() => onUpdateStatus(activeAdvisory.id, 'Approved', reviewerNotes)}
                  className="flex items-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>APPROVE ADVISORY</span>
                </button>

                <button
                  onClick={handleStartEdit}
                  className="flex items-center space-x-1.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs px-4 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                >
                  <Edit3 className="w-4 h-4" />
                  <span>EDIT DRAFT</span>
                </button>

                <button
                  onClick={() => onUpdateStatus(activeAdvisory.id, 'Hold', reviewerNotes)}
                  className="flex items-center space-x-1.5 bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                >
                  <PauseCircle className="w-4 h-4" />
                  <span>HOLD</span>
                </button>

                <button
                  onClick={() => onUpdateStatus(activeAdvisory.id, 'Rejected', reviewerNotes)}
                  className="flex items-center space-x-1.5 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition-all cursor-pointer shadow-xs"
                >
                  <XCircle className="w-4 h-4" />
                  <span>REJECT</span>
                </button>
              </div>

              {/* Edit Mode vs Preview Mode */}
              {isEditing ? (
                <div className="p-4 bg-slate-50 border border-slate-300 rounded-xl space-y-3 text-xs">
                  <h3 className="font-bold text-slate-900">Edit Advisory Content (Original Draft Saved Separately)</h3>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Subject</label>
                    <input
                      type="text"
                      value={editSubject}
                      onChange={(e) => setEditSubject(e.target.value)}
                      className="w-full p-2.5 bg-white border border-slate-300 rounded-xl"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Required Action</label>
                    <textarea
                      rows={4}
                      value={editAction}
                      onChange={(e) => setEditAction(e.target.value)}
                      className="w-full p-2.5 bg-white border border-slate-300 rounded-xl"
                    />
                  </div>
                  <div className="flex justify-end space-x-2 pt-2">
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-3 py-1.5 bg-slate-200 text-slate-700 rounded-lg font-semibold"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-1.5 bg-teal-600 text-white rounded-lg font-bold"
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-3 text-xs">
                  {showOriginal && activeAdvisory.originalFormalAdvisory ? (
                    <div className="space-y-2">
                      <div className="p-2 bg-amber-100 text-amber-900 font-bold text-[10px] uppercase rounded">
                        ORIGINAL UNEDITED AI DRAFT
                      </div>
                      <div className="font-bold text-slate-900">{activeAdvisory.originalFormalAdvisory.subject}</div>
                      <p className="text-slate-700 leading-relaxed">{activeAdvisory.originalFormalAdvisory.development}</p>
                      <div>
                        <span className="font-bold text-slate-800 block">Required Action (Original):</span>
                        <p className="text-slate-700">{activeAdvisory.originalFormalAdvisory.requiredAction}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="font-bold text-slate-900">{activeAdvisory.formalAdvisory.subject}</div>
                      <p className="text-slate-700 leading-relaxed">{activeAdvisory.formalAdvisory.development}</p>
                      <div>
                        <span className="font-bold text-slate-800 block">Required Action:</span>
                        <p className="text-slate-700">{activeAdvisory.formalAdvisory.requiredAction}</p>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Reviewer Notes Field */}
              <div className="space-y-1.5 text-xs">
                <label className="block font-bold text-slate-700">CA Reviewer Notes & Audit Trail Entry</label>
                <textarea
                  rows={2}
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  placeholder="Add notes explaining review decision or turnover verification..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-300 rounded-xl text-xs"
                />
              </div>
            </div>
          ) : (
            <div className="text-center py-20 bg-white border border-slate-200 rounded-2xl">
              <p className="text-slate-500 text-xs">Select an advisory from the left queue to conduct CA review.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
