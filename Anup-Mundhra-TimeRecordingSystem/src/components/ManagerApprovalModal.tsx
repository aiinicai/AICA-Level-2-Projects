import React, { useState } from 'react';
import { Check, MessageSquare, Users, X } from 'lucide-react';
import { datesOverlap, formatDateRangeLabel, roundDays } from '../lib/dateUtils';
import type { LeaveBalance, LeaveRequest } from '../types/leave';

interface ManagerApprovalModalProps {
  open: boolean;
  pendingRequests: LeaveRequest[];
  teamRequests: LeaveRequest[];
  teamBalances: LeaveBalance[];
  onApprove: (req: LeaveRequest, comment: string) => Promise<void>;
  onReject: (req: LeaveRequest, comment: string) => Promise<void>;
  onClose: () => void;
}

export const ManagerApprovalModal: React.FC<ManagerApprovalModalProps> = ({
  open,
  pendingRequests,
  teamRequests,
  teamBalances,
  onApprove,
  onReject,
  onClose,
}) => {
  const [comments, setComments] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  if (!open || pendingRequests.length === 0) return null;

  const getEmployeeClosing = (req: LeaveRequest): number | null => {
    const year = Number(req.startDate.slice(0, 4));
    const bal = teamBalances.find(
      (b) => b.employeeId === req.employeeId && b.year === year && b.categoryId === req.categoryId
    );
    return bal ? bal.closing : null;
  };

  const getTeamOverlaps = (req: LeaveRequest): LeaveRequest[] => {
    return teamRequests.filter(
      (other) =>
        other.id !== req.id &&
        other.status === 'approved' &&
        datesOverlap(req.startDate, req.endDate, other.startDate, other.endDate)
    );
  };

  const handleAction = async (req: LeaveRequest, decision: 'approved' | 'rejected') => {
    setBusyId(req.id);
    try {
      const comment = comments[req.id] || '';
      if (decision === 'approved') {
        await onApprove(req, comment);
      } else {
        await onReject(req, comment);
      }
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="manager-popup-title"
    >
      <div className="bg-white border border-slate-200 rounded-xl max-w-3xl w-full max-h-[88vh] flex flex-col shadow-xl overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-200 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <p className="text-xs font-medium text-amber-700">
              Action Required · {pendingRequests.length} Pending Team {pendingRequests.length === 1 ? 'Request' : 'Requests'}
            </p>
            <h2 id="manager-popup-title" className="text-xl font-semibold text-slate-900">
              Leaves Pending Your Approval
            </h2>
            <p className="text-sm text-slate-600">
              Direct reports awaiting your review. Approving automatically updates their availed and closing leave balances.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-lg cursor-pointer"
            aria-label="Review later"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto divide-y divide-slate-200">
          {pendingRequests.map((req) => {
            const currentClosing = getEmployeeClosing(req);
            const projectedClosing =
              currentClosing !== null ? roundDays(currentClosing - req.workingDays) : null;
            const overlaps = getTeamOverlaps(req);
            const isBusy = busyId === req.id;

            return (
              <div key={req.id} className="p-6 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-base font-semibold text-slate-900">
                        {req.employeeName}
                      </span>
                      <span className="text-slate-300" aria-hidden="true">·</span>
                      <span className="text-sm text-slate-600">
                        {req.employeeDesignation || 'Team Member'}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                      <span>{req.categoryName}</span>
                      <span aria-hidden="true">·</span>
                      <span className="font-mono tabular-nums text-slate-700">
                        {formatDateRangeLabel(req.startDate, req.endDate, req.halfDay)}
                      </span>
                      <span aria-hidden="true">·</span>
                      <span className="font-mono tabular-nums font-medium text-slate-900">
                        {req.workingDays} {req.workingDays === 1 ? 'day' : 'days'}
                      </span>
                    </div>
                  </div>

                  <div className="text-left sm:text-right shrink-0">
                    <p className="text-xs text-slate-500">Current → After Approval</p>
                    <p className="text-sm font-mono tabular-nums font-medium text-slate-900 mt-0.5">
                      {currentClosing !== null ? `${currentClosing}d` : '—'}
                      <span className="text-slate-400 mx-1.5">→</span>
                      <span
                        className={
                          projectedClosing !== null && projectedClosing < 0
                            ? 'text-red-700'
                            : 'text-emerald-700'
                        }
                      >
                        {projectedClosing !== null ? `${projectedClosing}d` : '—'}
                      </span>
                    </p>
                  </div>
                </div>

                <p className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5 leading-relaxed">
                  {req.reason}
                </p>

                {overlaps.length > 0 && (
                  <div className="flex items-center gap-2 text-xs text-amber-700">
                    <Users className="w-3.5 h-3.5 shrink-0" />
                    <span>
                      Team overlap: {overlaps.map((o) => o.employeeName).join(', ')} already approved on overlapping dates.
                    </span>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-1">
                  <div className="relative flex-1">
                    <MessageSquare className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="text"
                      value={comments[req.id] || ''}
                      onChange={(e) =>
                        setComments((prev) => ({ ...prev, [req.id]: e.target.value }))
                      }
                      maxLength={500}
                      placeholder="Optional remark for employee..."
                      disabled={isBusy}
                      className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
                    />
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => handleAction(req, 'rejected')}
                      disabled={isBusy}
                      className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50 transition-colors whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
                    >
                      <X className="w-4 h-4" />
                      Reject
                    </button>
                    <button
                      type="button"
                      onClick={() => handleAction(req, 'approved')}
                      disabled={isBusy}
                      className="inline-flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 transition-colors whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
                    >
                      <Check className="w-4 h-4" />
                      {isBusy ? 'Saving...' : 'Approve'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between gap-4">
          <span className="text-xs text-slate-500">
            You can also review these anytime under Team Approvals.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-100 transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            Review Later
          </button>
        </div>
      </div>
    </div>
  );
};
