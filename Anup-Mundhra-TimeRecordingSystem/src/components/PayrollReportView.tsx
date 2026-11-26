import React, { useMemo, useState } from 'react';
import { ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { exportTimesheetReportToExcel } from '../lib/timesheetService';
import { computePayrollRows, computeProjectReport, monthRange } from '../lib/timesheetUtils';
import { formatShortDate, parseIsoDateLocal } from '../lib/dateUtils';
import type { Employee, Holiday, LeaveCategory, LeaveRequest } from '../types/leave';
import type { Project, TimesheetEntry } from '../types/timesheet';

interface PayrollReportViewProps {
  employees: Employee[];
  entries: TimesheetEntry[];
  leaveRequests: LeaveRequest[];
  holidays: Holiday[];
  categories: LeaveCategory[];
  projects: Project[];
  today: string;
  /** Injected for the preview harness; defaults to the real Excel export */
  onExport?: (from: string, to: string) => void;
}

export const PayrollReportView: React.FC<PayrollReportViewProps> = ({
  employees,
  entries,
  leaveRequests,
  holidays,
  categories,
  projects,
  today,
  onExport,
}) => {
  const t = parseIsoDateLocal(today) || new Date();
  const initial = monthRange(t.getFullYear(), t.getMonth());
  const [from, setFrom] = useState(initial.start);
  const [to, setTo] = useState(initial.end);
  const [tab, setTab] = useState<'staff' | 'project'>('staff');

  const validRange = Boolean(from && to && from <= to);

  const rows = useMemo(
    () =>
      validRange
        ? computePayrollRows({ start: from, end: to, today, employees, entries, leaveRequests, holidays })
        : [],
    [validRange, from, to, today, employees, entries, leaveRequests, holidays]
  );

  const report = useMemo(
    () =>
      validRange
        ? computeProjectReport({ from, to, entries, projects, employees })
        : { projectRows: [], staff: [], matrix: {}, detail: [] },
    [validRange, from, to, entries, projects, employees]
  );

  const leaveNames = useMemo(() => {
    const names = new Set<string>(categories.filter((c) => c.active).map((c) => c.name));
    for (const r of rows) for (const k of Object.keys(r.leaveByCategory)) names.add(k);
    return Array.from(names).sort();
  }, [categories, rows]);

  const label = `${formatShortDate(from)} to ${formatShortDate(to)}`;

  const setMonthOffset = (offset: number) => {
    const d = new Date(t.getFullYear(), t.getMonth() + offset, 1);
    const r = monthRange(d.getFullYear(), d.getMonth());
    setFrom(r.start);
    setTo(r.end);
  };
  const setMonthToDate = () => {
    setFrom(monthRange(t.getFullYear(), t.getMonth()).start);
    setTo(today);
  };
  const shiftMonth = (delta: number) => {
    const base = parseIsoDateLocal(from) || t;
    const d = new Date(base.getFullYear(), base.getMonth() + delta, 1);
    const r = monthRange(d.getFullYear(), d.getMonth());
    setFrom(r.start);
    setTo(r.end);
  };

  const handleExport = () => {
    if (!validRange) return;
    if (onExport) onExport(from, to);
    else
      exportTimesheetReportToExcel({
        periodLabel: label,
        from,
        to,
        rows,
        leaveCategoryNames: leaveNames,
        report,
      });
  };

  const flagged = rows.filter((r) => r.flags.length > 0).length;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Payroll Attendance Report</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Present days count only approved timesheets. Leave comes from approved leave requests.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <input
            type="date"
            value={from}
            max={to}
            onChange={(e) => setFrom(e.target.value)}
            className="px-2.5 py-2 text-xs bg-white border border-slate-300 rounded-lg"
            aria-label="From date"
          />
          <span className="text-xs text-slate-500">to</span>
          <input
            type="date"
            value={to}
            min={from}
            onChange={(e) => setTo(e.target.value)}
            className="px-2.5 py-2 text-xs bg-white border border-slate-300 rounded-lg"
            aria-label="To date"
          />
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            className="p-2 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 cursor-pointer"
            aria-label="Next month"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={!validRange}
            className="ml-1 inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 disabled:opacity-40 cursor-pointer"
          >
            <Download className="w-3.5 h-3.5" />
            Download Excel
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 text-xs">
        <span className="text-slate-500">Quick range:</span>
        <button type="button" onClick={() => setMonthOffset(0)} className="px-2.5 py-1 bg-white border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer">This month</button>
        <button type="button" onClick={setMonthToDate} className="px-2.5 py-1 bg-white border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer">Month to date</button>
        <button type="button" onClick={() => setMonthOffset(-1)} className="px-2.5 py-1 bg-white border border-slate-200 rounded-md hover:bg-slate-50 cursor-pointer">Last month</button>
        <span className="ml-2 text-slate-500">
          Excel has 5 sheets: Staff Summary, Project Summary, Project x Staff, Staff x Project, Daily Detail.
        </span>
      </div>

      <div className="inline-flex p-1 bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold">
        <button
          type="button"
          onClick={() => setTab('staff')}
          className={`px-3 py-1.5 rounded-md cursor-pointer ${tab === 'staff' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'}`}
        >
          Staff-wise
        </button>
        <button
          type="button"
          onClick={() => setTab('project')}
          className={`px-3 py-1.5 rounded-md cursor-pointer ${tab === 'project' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'}`}
        >
          Project-wise
        </button>
      </div>

      {flagged > 0 && (
        <p className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
          {flagged} employee(s) have days that are pending approval or not submitted. Resolve these before
          running payroll.
        </p>
      )}

      {tab === 'project' && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-slate-500 border-b border-slate-200 whitespace-nowrap">
                <th className="px-3 py-2.5 font-medium">Code</th>
                <th className="px-3 py-2.5 font-medium">Project</th>
                <th className="px-3 py-2.5 font-medium">Client</th>
                <th className="px-3 py-2.5 font-medium">Type</th>
                <th className="px-3 py-2.5 font-medium">Partner</th>
                <th className="px-3 py-2.5 font-medium">Manager</th>
                <th className="px-3 py-2.5 font-medium text-right">Staff</th>
                <th className="px-3 py-2.5 font-medium text-right">Approved hours</th>
                <th className="px-3 py-2.5 font-medium text-right">Pending hours</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {report.projectRows.map((p) => (
                <tr key={p.code}>
                  <td className="px-3 py-2.5 font-mono text-slate-500">{p.code}</td>
                  <td className="px-3 py-2.5 font-medium text-slate-900">{p.name}</td>
                  <td className="px-3 py-2.5 text-slate-600">{p.client || '-'}</td>
                  <td className="px-3 py-2.5">
                    <span className={`text-[11px] ${p.type === 'chargeable' ? 'text-emerald-700' : 'text-slate-500'}`}>
                      {p.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable'}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-slate-600">{p.partnerName || '-'}</td>
                  <td className="px-3 py-2.5 text-slate-600">{p.managerName || '-'}</td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">{p.staffCount}</td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums font-semibold text-emerald-800">{p.approvedHours}</td>
                  <td className={`px-3 py-2.5 text-right font-mono tabular-nums ${p.pendingHours ? 'text-sky-700 font-semibold' : ''}`}>{p.pendingHours}</td>
                </tr>
              ))}
              {report.projectRows.length === 0 && (
                <tr>
                  <td colSpan={9} className="px-4 py-8 text-center text-slate-500">
                    No approved or submitted hours in this period.
                  </td>
                </tr>
              )}
              {report.projectRows.length > 0 && (
                <tr className="bg-slate-50 font-semibold">
                  <td className="px-3 py-2.5" colSpan={7}>Total</td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    {Math.round(report.projectRows.reduce((n, p) => n + p.approvedHours, 0) * 100) / 100}
                  </td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums">
                    {Math.round(report.projectRows.reduce((n, p) => n + p.pendingHours, 0) * 100) / 100}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'staff' && (
      <div className="bg-white border border-slate-200 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b border-slate-200 whitespace-nowrap">
              <th className="px-3 py-2.5 font-medium">Code</th>
              <th className="px-3 py-2.5 font-medium">Employee</th>
              <th className="px-3 py-2.5 font-medium text-right">Working days</th>
              <th className="px-3 py-2.5 font-medium text-right">Holidays</th>
              <th className="px-3 py-2.5 font-medium text-right">Weekly offs</th>
              <th className="px-3 py-2.5 font-medium text-right">Present</th>
              {leaveNames.map((n) => (
                <th key={n} className="px-3 py-2.5 font-medium text-right">{n}</th>
              ))}
              <th className="px-3 py-2.5 font-medium text-right">Total leave</th>
              <th className="px-3 py-2.5 font-medium text-right">Pending</th>
              <th className="px-3 py-2.5 font-medium text-right">Not submitted</th>
              <th className="px-3 py-2.5 font-medium text-right">Hours</th>
              <th className="px-3 py-2.5 font-medium text-right">Chargeable</th>
              <th className="px-3 py-2.5 font-medium text-right">Non-chargeable</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-mono tabular-nums">
            {rows.map((r) => (
              <tr key={r.employeeId} className={r.flags.length > 0 ? 'bg-amber-50/40' : ''}>
                <td className="px-3 py-2.5 text-slate-500">{r.employeeCode}</td>
                <td className="px-3 py-2.5 font-sans whitespace-nowrap">
                  <div className="font-medium text-slate-900">{r.name}</div>
                  <div className="text-[11px] text-slate-500">{r.designation}</div>
                </td>
                <td className="px-3 py-2.5 text-right">{r.workingDays}</td>
                <td className="px-3 py-2.5 text-right">{r.holidays}</td>
                <td className="px-3 py-2.5 text-right">{r.weeklyOffs}</td>
                <td className="px-3 py-2.5 text-right font-semibold text-emerald-800">{r.daysPresent}</td>
                {leaveNames.map((n) => (
                  <td key={n} className="px-3 py-2.5 text-right">{r.leaveByCategory[n] || 0}</td>
                ))}
                <td className="px-3 py-2.5 text-right font-semibold">{r.totalLeave}</td>
                <td className={`px-3 py-2.5 text-right ${r.pendingApproval ? 'text-sky-700 font-semibold' : ''}`}>
                  {r.pendingApproval}
                </td>
                <td className={`px-3 py-2.5 text-right ${r.notSubmitted ? 'text-red-700 font-semibold' : ''}`}>
                  {r.notSubmitted}
                </td>
                <td className="px-3 py-2.5 text-right">{r.totalHours}</td>
                <td className="px-3 py-2.5 text-right">{r.chargeableHours}</td>
                <td className="px-3 py-2.5 text-right">{r.nonChargeableHours}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={12 + leaveNames.length} className="px-4 py-8 text-center font-sans text-slate-500">
                  No active employees in the directory.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}
    </div>
  );
};