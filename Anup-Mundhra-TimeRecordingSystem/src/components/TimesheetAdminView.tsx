import React, { useMemo, useState } from 'react';
import { RefreshCw, Unlock } from 'lucide-react';
import { formatShortDate } from '../lib/dateUtils';
import { monthLabel } from '../lib/timesheetUtils';
import type { Employee } from '../types/leave';
import type { Project, TimesheetEntry } from '../types/timesheet';

interface TimesheetAdminViewProps {
  projects: Project[];
  employees: Employee[];
  entries: TimesheetEntry[];
  syncing: boolean;
  lastSyncMessage: string | null;
  onSyncProjects: () => void;
  onReopen: (entry: TimesheetEntry, reason: string) => Promise<void>;
}

export const TimesheetAdminView: React.FC<TimesheetAdminViewProps> = ({
  projects,
  employees,
  entries,
  syncing,
  lastSyncMessage,
  onSyncProjects,
  onReopen,
}) => {
  const [empEmail, setEmpEmail] = useState('');
  const [reason, setReason] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeEmployees = useMemo(
    () => employees.filter((e) => e.status === 'active').sort((a, b) => a.name.localeCompare(b.name)),
    [employees]
  );

  const empEntries = useMemo(
    () =>
      entries
        .filter((e) => e.employeeEmail === empEmail && e.status !== 'draft')
        .sort((a, b) => b.date.localeCompare(a.date))
        .slice(0, 60),
    [entries, empEmail]
  );

  const handleReopen = async (entry: TimesheetEntry) => {
    setError(null);
    if (!reason.trim()) {
      setError('Enter a reason before reopening a day.');
      return;
    }
    setBusyId(entry.id);
    try {
      await onReopen(entry, reason);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reopen this day.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Projects and Reopen</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Projects come from the "Projects" tab of the linked Google Sheet. HR admins can reopen frozen or approved days.
        </p>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl">
        <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-slate-200">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Project master ({projects.length})</h2>
            {lastSyncMessage && <p className="text-xs text-slate-500 mt-0.5">{lastSyncMessage}</p>}
          </div>
          <button
            type="button"
            onClick={onSyncProjects}
            disabled={syncing}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            Sync Projects from Sheet
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-200 whitespace-nowrap">
                <th className="px-4 py-2.5 font-medium">Code</th>
                <th className="px-4 py-2.5 font-medium">Project</th>
                <th className="px-4 py-2.5 font-medium">Client</th>
                <th className="px-4 py-2.5 font-medium">Type</th>
                <th className="px-4 py-2.5 font-medium">Partner</th>
                <th className="px-4 py-2.5 font-medium">Manager</th>
                <th className="px-4 py-2.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {projects.map((p) => (
                <tr key={p.id} className={p.active ? '' : 'text-slate-400'}>
                  <td className="px-4 py-2.5 font-mono">{p.code}</td>
                  <td className="px-4 py-2.5">{p.name}</td>
                  <td className="px-4 py-2.5">{p.client}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`px-2 py-0.5 text-[11px] font-medium border rounded-md ${
                        p.type === 'chargeable'
                          ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                          : 'bg-slate-50 text-slate-700 border-slate-200'
                      }`}
                    >
                      {p.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable'}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">{p.partnerName || '-'}</td>
                  <td className="px-4 py-2.5">{p.managerName || '-'}</td>
                  <td className="px-4 py-2.5">{p.active ? 'Active' : 'Inactive'}</td>
                </tr>
              ))}
              {projects.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                    No projects yet. Add a "Projects" tab to the linked sheet and sync.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
        <h2 className="text-sm font-semibold text-slate-900">Reopen a day for an employee</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <select
            value={empEmail}
            onChange={(e) => setEmpEmail(e.target.value)}
            className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg"
          >
            <option value="">Select employee...</option>
            {activeEmployees.map((e) => (
              <option key={e.id} value={e.email}>
                {e.name} ({e.email})
              </option>
            ))}
          </select>
          <input
            type="text"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            maxLength={300}
            placeholder="Reason for reopening (required)"
            className="px-3 py-2 text-sm bg-white border border-slate-200 rounded-lg"
          />
        </div>
        {error && <p className="text-xs text-red-700">{error}</p>}
        {empEmail && empEntries.length === 0 && (
          <p className="text-sm text-slate-500">No submitted, approved or rejected days for this employee.</p>
        )}
        {empEntries.length > 0 && (
          <ul className="divide-y divide-slate-100 border border-slate-100 rounded-lg">
            {empEntries.map((e) => (
              <li key={e.id} className="px-3 py-2 flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm">
                  <span className="font-medium text-slate-900">{formatShortDate(e.date)}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    {monthLabel(Number(e.date.slice(0, 4)), Number(e.date.slice(5, 7)) - 1)} ·{' '}
                    {e.lines.map((l) => `${l.projectCode} ${l.hours}h`).join(' · ')} · {e.status}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => handleReopen(e)}
                  disabled={busyId === e.id}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-800 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 cursor-pointer"
                >
                  <Unlock className="w-3.5 h-3.5" />
                  Reopen
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};
