import React, { useState } from 'react';
import { 
  ShieldCheck, AlertCircle, CheckCircle, XCircle, 
  Send, MessageSquare, Clock, UserCheck
} from 'lucide-react';
import { Proposal, ProposalStatus, UserRole } from '../types';
import { formatProposalStatus } from '../utils/formatters';
import { ApiClient } from '../api/client';

interface ReviewerTabProps {
  proposal: Proposal;
  currentRole: UserRole;
  onRefresh: () => void;
}

export const ReviewerTab: React.FC<ReviewerTabProps> = ({
  proposal,
  currentRole,
  onRefresh,
}) => {
  const [selectedStatus, setSelectedStatus] = useState<ProposalStatus>(proposal.status);
  const [reviewNotes, setReviewNotes] = useState<string>(proposal.review_notes || '');
  const [isUpdating, setIsUpdating] = useState(false);

  const handleUpdateStatus = async () => {
    setIsUpdating(true);
    try {
      await ApiClient.request(`/proposals/${proposal.id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: selectedStatus,
          review_notes: reviewNotes,
        }),
      });
      alert(`Proposal status successfully updated to ${selectedStatus.replace(/_/g, ' ').toUpperCase()}`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Error updating status');
    } finally {
      setIsUpdating(false);
    }
  };

  const statusMeta = formatProposalStatus(proposal.status);

  return (
    <div className="space-y-6">
      {/* Reviewer Action Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <span className="text-[11px] font-semibold tracking-wider text-brand-800 uppercase">
              Credit Facilitator Governance
            </span>
            <h4 className="font-bold text-slate-900 text-base mt-0.5">
              Reviewer Approval & Stage Progression
            </h4>
            <p className="text-xs text-slate-500">
              Four-eyes principle: Reviewers inspect checklist completeness, extracted figures, and DSCR/FOIR coverage.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Current Stage:</span>
            <span className={`px-3 py-1 rounded-full border text-xs font-semibold ${statusMeta.color}`}>
              {statusMeta.label}
            </span>
          </div>
        </div>

        <div className="space-y-4 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Transition Proposal Stage
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value as ProposalStatus)}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-slate-800 font-medium focus:ring-1 focus:ring-brand-500"
            >
              <option value="lead">Lead Sourced</option>
              <option value="onboarding">Client Onboarding</option>
              <option value="proposal_draft">Proposal Draft</option>
              <option value="document_collection">Document Collection</option>
              <option value="extraction_verification">Extraction & Verification</option>
              <option value="financial_analysis">Financial Underwriting Completed</option>
              <option value="lender_comparison">Lender Policy Matching</option>
              <option value="reviewer_approval">Reviewer Approval Queue</option>
              <option value="report_generation">Report Pack Ready for Generation</option>
              <option value="submission_tracking">Submitted to Commercial Bank (Tracking)</option>
              <option value="sanctioned">Bank Credit Sanction Received</option>
              <option value="closed_won">Closed - Won (Sanctioned & Disbursed)</option>
              <option value="closed_lost">Closed - Not Won (Declined / Borrower Withdrawn)</option>
              <option value="rejected">Declined / Not Pursued</option>
            </select>
          </div>

          {/* Quick Action Badges */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <span className="text-[11px] text-slate-500 font-medium">Quick Close:</span>
            <button
              type="button"
              onClick={() => setSelectedStatus('closed_won')}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                selectedStatus === 'closed_won'
                  ? 'bg-emerald-600 text-white border-emerald-700 shadow-sm'
                  : 'bg-emerald-50 text-emerald-800 border-emerald-300 hover:bg-emerald-100'
              }`}
            >
              ✓ Won (Sanctioned)
            </button>
            <button
              type="button"
              onClick={() => setSelectedStatus('closed_lost')}
              className={`px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                selectedStatus === 'closed_lost'
                  ? 'bg-rose-600 text-white border-rose-700 shadow-sm'
                  : 'bg-rose-50 text-rose-800 border-rose-300 hover:bg-rose-100'
              }`}
            >
              ✕ Not Won
            </button>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">
              Credit Committee & Reviewer Observations / Covenants
            </label>
            <textarea
              rows={4}
              value={reviewNotes}
              onChange={(e) => setReviewNotes(e.target.value)}
              placeholder="Record any covenants, margin requirements, personal guarantee conditions, or additional clarifications required before bank submission..."
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-3 text-slate-800 leading-relaxed focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div className="pt-2 flex items-center justify-end">
            <button
              onClick={handleUpdateStatus}
              disabled={isUpdating}
              className="flex items-center gap-2 px-5 py-2.5 bg-brand-800 hover:bg-brand-900 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <UserCheck className="w-4 h-4" />
              <span>{isUpdating ? 'Committing...' : 'Commit Status & Review Decision'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
