import React, { useMemo, useState } from 'react';
import { Check, X } from 'lucide-react';
import { formatShortDate } from '../lib/dateUtils';
import type { TimesheetEntry } from '../types/timesheet';

interface TimesheetApprovalsViewProps {
  /** Entries this user may review (assigned to them as approver) */
  reviewableEntries: TimesheetEntry[];
  onReview: (
    entries: TimesheetEntry[],
    decision: 'approved' | 'rejected',
    comment: string
  ) => Promise<void>;
}

export const TimesheetApprovalsView: React.FC<TimesheetApprovalsViewProps> = ({
  reviewableEntries,
  onReview,
}) => {
  const [tab, setTab] = useState<'pending' | 'history'>('pending');
  const [comments, setComments] = useState<Record<string, string>>({});
  const [unchecked, setUnchecked] = useState<Set<string>>(new Set());
  const [busyEmp, setBusyEmp] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const pendingGroups = useMemo(() => {
    const map = new Map<string, TimesheetEntry[]>();
    for (const e of reviewableEntries) {
      if (e.status !== 'submitted') continue;
      if (!map.has(e.employeeEmail)) map.set(e.employeeEmail, []);
      map.get(e.employeeEmail)!.push(e);
    }
    return Array.from(map.entries())
      .map(([email, entries]) => ({
        email,
        name: entries[0].employeeName,
        entries: entries.sort((a, b) => a.date.localeCompare(b.date)),
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [reviewableEntries]);

  const history = useMemo(
    () =>
      reviewableEntries
        .filter((e) => e.status === 'approved' || e.status === 'rejected')
        .sort((a, b) => b.date.localeCompare(a.date))
        .slice(0, 100),
    [reviewableEntries]
  );

  const pendingCount = pendingGroups.reduce((n, g) => n + g.entries.length, 0);

  const act = async (
    email: string,
    entries: TimesheetEntry[],
    decision: 'approved' | 'rejected'
  ) => {
    const chosen = entries.filter((e) => !unchecked.has(e.id));
    if (chosen.length === 0) return;
    const comment = comments[email] || '';
    if (decision === 'rejected' && !comment.trim()) {
      setErrors((p) => ({ ...p, [email]: 'Add a comment so the employee knows what to fix.' }));
      return;
    }
    setErrors((p) => ({ ...p, [email]: '' }));
    setBusyEmp(email);
    try {
      await onReview(chosen, decision, comment);
      setComments((p) => ({ ...p, [email]: '' }));
    } catch (err) {
      setErrors((p) => ({
        ...p,
        [email]: err instanceof Error ? err.message : 'Could not complete the action.',
      }));
    } finally {
      setBusyEmp(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Timesheet Approvals</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Submitted days from employees who report to you (managers' timesheets go to their reporting partner)
          </p>
        </div>
        <div className="inline-flex items-center gap-1 p-1 bg-slate-100 border border-slate-200 rounded-lg">
          {(['pending', 'history'] as const).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md whitespace-nowrap cursor-pointer ${
                tab === t ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {t === 'pending' ? `Pending (${pendingCount} days)` : `History (${history.length})`}
            </button>
          ))}
        </div>
      </div>

      {tab === 'pending' ? (
        pendingGroups.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-10 text-center space-y-2">
            <h2 className="text-base font-semibold text-slate-900">All caught up</h2>
            <p className="text-sm text-slate-500">No submitted timesheets are waiting for you.</p>
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-200">
            {pendingGroups.map((g) => {
              const chosen = g.entries.filter((e) => !unchecked.has(e.id));
              const hours = chosen.reduce((n, e) => n + e.totalHours, 0);
              const busy = busyEmp === g.email;
              return (
                <div key={g.email} className="p-6 space-y-4">
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <div>
                      <span className="text-base font-semibold text-slate-900">{g.name}</span>
                      <span className="ml-2 text-xs text-slate-500">{g.email}</span>
                    </div>
                    <span className="text-xs text-slate-500">
                      <span className="font-mono tabular-nums font-semibold text-slate-800">{chosen.length}</span> of{' '}
                      {g.entries.length} days selected ·{' '}
                      <span className="font-mono tabular-nums font-semibold text-slate-800">{hours}</span> h
                    </span>
                  </div>

                  <ul className="divide-y divide-slate-100 border border-slate-100 rounded-lg">
                    {g.entries.map((e) => (
                      <li key={e.id} className="px-3 py-2 flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={!unchecked.has(e.id)}
                          onChange={(ev) =>
                            setUnchecked((prev) => {
                              const next = new Set(prev);
                              if (ev.target.checked) next.delete(e.id);
                              else next.add(e.id);
                              return next;
                            })
                          }
                        />
                        <span className="w-28 text-sm text-slate-800 shrink-0">{formatShortDate(e.date)}</span>
                        <span className="text-xs text-slate-600 flex-1 min-w-0">
                          {e.lines.map((l, i) => (
                            <span key={i} className="inline-block mr-3">
                              <span className="font-medium text-slate-800">{l.projectCode}</span>{' '}
                              <span className="font-mono tabular-nums">{l.hours}h</span>
                              <span className="text-slate-400">
                                {' '}
                                ({l.type === 'chargeable' ? 'chargeable' : 'non-chargeable'})
                              </span>
                            </span>
                          ))}
                        </span>
                      </li>
                    ))}
                  </ul>

                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="text"
                      value={comments[g.email] || ''}
                      onChange={(e) => setComments((p) => ({ ...p, [g.email]: e.target.value }))}
                      placeholder="Comment (required when rejecting)"
                      maxLength={500}
                      className="flex-1 px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg"
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={busy || chosen.length === 0}
                        onClick={() => act(g.email, g.entries, 'rejected')}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-red-700 bg-white border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 cursor-pointer"
                      >
                        <X className="w-4 h-4" />
                        Reject
                      </button>
                      <button
                        type="button"
                        disabled={busy || chosen.length === 0}
                        onClick={() => act(g.email, g.entries, 'approved')}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-emerald-700 rounded-lg hover:bg-emerald-800 disabled:opacity-50 cursor-pointer"
                      >
                        <Check className="w-4 h-4" />
                        Approve
                      </button>
                    </div>
                  </div>
                  {errors[g.email] && <p className="text-xs text-red-700">{errors[g.email]}</p>}
                </div>
              );
            })}
          </div>
        )
      ) : history.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-10 text-center text-sm text-slate-500">
          No reviewed timesheets yet.
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-200">
                <th className="px-4 py-2.5 font-medium">Date</th>
                <th className="px-4 py-2.5 font-medium">Employee</th>
                <th className="px-4 py-2.5 font-medium">Projects</th>
                <th className="px-4 py-2.5 font-medium text-right">Hours</th>
                <th className="px-4 py-2.5 font-medium">Decision</th>
                <th className="px-4 py-2.5 font-medium">Comment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {history.map((e) => (
                <tr key={e.id}>
                  <td className="px-4 py-2.5 whitespace-nowrap">{formatShortDate(e.date)}</td>
                  <td className="px-4 py-2.5">{e.employeeName}</td>
                  <td className="px-4 py-2.5 text-xs text-slate-600">
                    {e.lines.map((l) => `${l.projectCode} ${l.hours}h`).join(' · ')}
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums">{e.totalHours}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`px-2 py-0.5 text-[11px] font-medium border rounded-md ${
                        e.status === 'approved'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : 'bg-red-50 text-red-800 border-red-200'
                      }`}
                    >
                      {e.status === 'approved' ? 'Approved' : 'Rejected'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-xs text-slate-600">{e.managerComment}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
