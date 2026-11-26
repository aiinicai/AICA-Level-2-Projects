import React, { useMemo, useState } from 'react';
import { Check, MessageSquare, Users, X } from 'lucide-react';
import { datesOverlap, formatDateRangeLabel, roundDays } from '../lib/dateUtils';
import type { LeaveBalance, LeaveRequest } from '../types/leave';

interface TeamApprovalsViewProps {
  teamRequests: LeaveRequest[];
  teamBalances: LeaveBalance[];
  onApprove: (req: LeaveRequest, comment: string) => Promise<void>;
  onReject: (req: LeaveRequest, comment: string) => Promise<void>;
}

export const TeamApprovalsView: React.FC<TeamApprovalsViewProps> = ({
  teamRequests,
  teamBalances,
  onApprove,
  onReject,
}) => {
  const [filter, setFilter] = useState<'pending' | 'reviewed'>('pending');
  const [comments, setComments] = useState<Record<string, string>>({});
  const [busyId, setBusyId] = useState<string | null>(null);

  const pending = useMemo(
    () => teamRequests.filter((r) => r.status === 'pending'),
    [teamRequests]
  );
  const reviewed = useMemo(
    () => teamRequests.filter((r) => r.status !== 'pending'),
    [teamRequests]
  );

  const getEmployeeClosing = (req: LeaveRequest): number | null => {
    const year = Number(req.startDate.slice(0, 4));
    const bal = teamBalances.find(
      (b) => b.employeeId === req.employeeId && b.year === year && b.categoryId === req.categoryId
    );
    return bal ? bal.closing : null;
  };

  const handleAction = async (req: LeaveRequest, decision: 'approved' | 'rejected') => {
    setBusyId(req.id);
    try {
      const comment = comments[req.id] || '';
      if (decision === 'approved') await onApprove(req, comment);
      else await onReject(req, comment);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Team Leave Approvals</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Direct reports mapped to your email in the employee directory
          </p>
        </div>

        <div className="inline-flex items-center gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
          <button
            type="button"
            onClick={() => setFilter('pending')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              filter === 'pending'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Pending ({pending.length})
          </button>
          <button
            type="button"
            onClick={() => setFilter('reviewed')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
              filter === 'reviewed'
                ? 'bg-white text-slate-900 shadow-xs'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            History ({reviewed.length})
          </button>
        </div>
      </div>

      {filter === 'pending' ? (
        pending.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-10 text-center space-y-2">
            <h2 className="text-base font-semibold text-slate-900">All caught up</h2>
            <p className="text-sm text-slate-500">
              There are no pending leave requests from your team right now.
            </p>
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-200">
            {pending.map((req) => {
              const currentClosing = getEmployeeClosing(req);
              const projected =
                currentClosing !== null ? roundDays(currentClosing - req.workingDays) : null;
              const overlaps = teamRequests.filter(
                (other) =>
                  other.id !== req.id &&
                  other.status === 'approved' &&
                  datesOverlap(req.startDate, req.endDate, other.startDate, other.endDate)
              );
              const isBusy = busyId === req.id;

              return (
                <div key={req.id} className="p-6 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-base font-semibold text-slate-900">
                          {req.employeeName}
                        </span>
                        <span className="text-slate-300" aria-hidden="true">·</span>
                        <span className="text-xs text-slate-600">
                          {req.employeeDesignation || 'Team Member'}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-1">
                        <span>{req.categoryName}</span>
                        <span aria-hidden="true">·</span>
                        <span className="font-mono tabular-nums text-slate-800">
                          {formatDateRangeLabel(req.startDate, req.endDate, req.halfDay)}
                        </span>
                        <span aria-hidden="true">·</span>
                        <span className="font-mono tabular-nums font-semibold text-slate-900">
                          {req.workingDays} {req.workingDays === 1 ? 'day' : 'days'}
                        </span>
                      </div>
                    </div>

                    <div className="text-left sm:text-right">
                      <span className="text-xs text-slate-500">Closing Balance Impact</span>
                      <div className="text-sm font-mono tabular-nums font-medium text-slate-900">
                        {currentClosing !== null ? `${currentClosing}d` : '—'} →{' '}
                        <span
                          className={
                            projected !== null && projected < 0
                              ? 'text-red-700'
                              : 'text-emerald-700'
                          }
                        >
                          {projected !== null ? `${projected}d` : '—'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <p className="text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2.5">
                    {req.reason}
                  </p>

                  {overlaps.length > 0 && (
                    <div className="flex items-center gap-2 text-xs text-amber-700">
                      <Users className="w-3.5 h-3.5 shrink-0" />
                      <span>
                        Team overlap: {overlaps.map((o) => o.employeeName).join(', ')} approved on overlapping dates.
                      </span>
                    </div>
                  )}

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                    <div className="relative flex-1">
                      <MessageSquare className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <input
                        type="text"
                        value={comments[req.id] || ''}
                        onChange={(e) =>
                          setComments((prev) => ({ ...prev, [req.id]: e.target.value }))
                        }
                        maxLength={500}
                        placeholder="Add manager comment (optional)..."
                        disabled={isBusy}
                        className="w-full pl-9 pr-3 py-2 text-sm bg-white border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
                      />
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleAction(req, 'rejected')}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50 whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
                      >
                        <X className="w-4 h-4" />
                        Reject
                      </button>
                      <button
                        type="button"
                        onClick={() => handleAction(req, 'approved')}
                        disabled={isBusy}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 whitespace-nowrap shrink-0 cursor-pointer disabled:opacity-50"
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
        )
      ) : (
        <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          {reviewed.length === 0 ? (
            <div className="p-8 text-center text-sm text-slate-500">
              No reviewed team requests yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 bg-slate-50/70 text-xs font-medium text-slate-600">
                    <th className="py-3 px-6">Employee</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Date Range</th>
                    <th className="py-3 px-4 text-right">Days</th>
                    <th className="py-3 px-4">Remark</th>
                    <th className="py-3 px-6 text-right">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-sm">
                  {reviewed.map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50/70">
                      <td className="py-3 px-6">
                        <div className="font-medium text-slate-900">{req.employeeName}</div>
                        <div className="text-xs text-slate-500">{req.employeeDesignation}</div>
                      </td>
                      <td className="py-3 px-4 text-slate-700">{req.categoryName}</td>
                      <td className="py-3 px-4 font-mono tabular-nums text-xs text-slate-700">
                        {formatDateRangeLabel(req.startDate, req.endDate, req.halfDay)}
                      </td>
                      <td className="py-3 px-4 text-right font-mono tabular-nums text-slate-900">
                        {req.workingDays}
                      </td>
                      <td className="py-3 px-4 text-xs text-slate-600 max-w-xs truncate">
                        {req.managerComment || '—'}
                      </td>
                      <td
                        className={`py-3 px-6 text-right text-xs capitalize font-medium ${
                          req.status === 'approved'
                            ? 'text-emerald-700'
                            : req.status === 'rejected'
                              ? 'text-red-700'
                              : 'text-slate-500'
                        }`}
                      >
                        {req.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
};
