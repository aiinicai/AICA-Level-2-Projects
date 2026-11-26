import {
  TIMESHEET_LIMITS,
  type DayInfo,
  type PayrollRow,
  type Project,
  type ProjectReport,
  type ProjectStaffRef,
  type ProjectSummaryRow,
  type TimesheetDetailRow,
  type TimesheetEntry,
  type TimesheetLine,
} from '../types/timesheet';
import type { Employee, Holiday, LeaveRequest } from '../types/leave';
import { parseIsoDateLocal, roundDays } from './dateUtils';

export function toIso(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function addDaysIso(iso: string, days: number): string {
  const dt = parseIsoDateLocal(iso);
  if (!dt) return iso;
  dt.setDate(dt.getDate() + days);
  return toIso(dt);
}

export function eachDate(startIso: string, endIso: string): string[] {
  const out: string[] = [];
  const start = parseIsoDateLocal(startIso);
  const end = parseIsoDateLocal(endIso);
  if (!start || !end || end < start) return out;
  const cursor = new Date(start.getTime());
  while (cursor <= end) {
    out.push(toIso(cursor));
    cursor.setDate(cursor.getDate() + 1);
  }
  return out;
}

export function isWeekend(iso: string): boolean {
  const dt = parseIsoDateLocal(iso);
  if (!dt) return false;
  const dow = dt.getDay();
  return dow === 0 || dow === 6;
}

export function monthRange(year: number, monthIndex: number): { start: string; end: string } {
  const start = new Date(year, monthIndex, 1);
  const end = new Date(year, monthIndex + 1, 0);
  return { start: toIso(start), end: toIso(end) };
}

export function monthLabel(year: number, monthIndex: number): string {
  return new Date(year, monthIndex, 1).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
  });
}

/** First date (inclusive) of the open entry window, e.g. today - 14 days. */
export function openWindowStart(today: string): string {
  return addDaysIso(today, -TIMESHEET_LIMITS.openWindowDays);
}

export function isWithinOpenWindow(date: string, today: string): boolean {
  return date >= openWindowStart(today) && date <= today;
}

export interface LeaveDayInfo {
  label: string;
  half: boolean;
}

/** Expands APPROVED leave requests into a date -> leave info map (weekdays only). */
export function buildApprovedLeaveMap(requests: LeaveRequest[]): Map<string, LeaveDayInfo> {
  const map = new Map<string, LeaveDayInfo>();
  for (const req of requests) {
    if (req.status !== 'approved') continue;
    const half = req.halfDay !== 'none' && req.startDate === req.endDate;
    for (const d of eachDate(req.startDate, req.endDate)) {
      if (isWeekend(d)) continue;
      map.set(d, { label: req.categoryName, half });
    }
  }
  return map;
}

export function buildHolidayMap(holidays: Holiday[]): Map<string, string> {
  const map = new Map<string, string>();
  for (const h of holidays) map.set(h.date, h.name);
  return map;
}

export function getDayInfo(
  date: string,
  today: string,
  holidayMap: Map<string, string>,
  leaveMap: Map<string, LeaveDayInfo>
): DayInfo {
  const inOpenWindow = isWithinOpenWindow(date, today);
  const future = date > today;
  if (isWeekend(date)) {
    return { date, kind: 'weekend', label: 'Weekly off', halfDayLeave: false, inOpenWindow, future };
  }
  const holiday = holidayMap.get(date);
  if (holiday) {
    return { date, kind: 'holiday', label: holiday, halfDayLeave: false, inOpenWindow, future };
  }
  const leave = leaveMap.get(date);
  if (leave) {
    return {
      date,
      kind: 'leave',
      label: leave.label,
      halfDayLeave: leave.half,
      inOpenWindow,
      future,
    };
  }
  return { date, kind: 'working', label: '', halfDayLeave: false, inOpenWindow, future };
}

export function sumHours(lines: TimesheetLine[]): number {
  return roundDays(lines.reduce((acc, l) => acc + (Number.isFinite(l.hours) ? l.hours : 0), 0));
}

export interface LineValidation {
  total: number;
  complete: boolean; // exactly the daily hours
  error: string | null;
}

/** Validates a day's lines. A draft may be partial; submission needs `complete`. */
export function validateLines(lines: TimesheetLine[]): LineValidation {
  const total = sumHours(lines);
  const { dailyHours, hourStep, maxLinesPerDay } = TIMESHEET_LIMITS;

  if (lines.length > maxLinesPerDay) {
    return { total, complete: false, error: `At most ${maxLinesPerDay} project lines per day.` };
  }
  const seen = new Set<string>();
  for (const line of lines) {
    if (!line.projectCode) {
      return { total, complete: false, error: 'Choose a project for every line.' };
    }
    if (seen.has(line.projectCode)) {
      return { total, complete: false, error: 'Each project can appear only once per day.' };
    }
    seen.add(line.projectCode);
    if (!Number.isFinite(line.hours) || line.hours <= 0) {
      return { total, complete: false, error: 'Hours must be greater than zero.' };
    }
    if (Math.abs(line.hours / hourStep - Math.round(line.hours / hourStep)) > 1e-9) {
      return { total, complete: false, error: `Hours must be in steps of ${hourStep}.` };
    }
  }
  if (total > dailyHours) {
    return {
      total,
      complete: false,
      error: `A day cannot exceed ${dailyHours} hours (currently ${total}).`,
    };
  }
  return { total, complete: total === dailyHours, error: null };
}

export function canEmployeeEdit(
  entry: TimesheetEntry | undefined,
  day: DayInfo
): { editable: boolean; reason: string } {
  if (day.kind !== 'working') {
    return { editable: false, reason: day.label || 'Not a working day' };
  }
  if (day.future) return { editable: false, reason: 'Future dates cannot be filled' };
  const reopened = Boolean(entry && entry.reopenedBy);
  if (!day.inOpenWindow && !reopened) {
    return { editable: false, reason: 'Frozen. Ask an HR admin to reopen this day.' };
  }
  if (!entry) return { editable: true, reason: '' };
  if (entry.status === 'draft' || entry.status === 'rejected') {
    return { editable: true, reason: '' };
  }
  if (entry.status === 'submitted') return { editable: false, reason: 'Awaiting approval' };
  return { editable: false, reason: 'Approved' };
}

// ---------------------------------------------------------------------------
// Payroll report
// ---------------------------------------------------------------------------

export function computePayrollRows(params: {
  /** Either a month (year + monthIndex) or an explicit start/end range */
  year?: number;
  monthIndex?: number;
  start?: string;
  end?: string;
  today: string;
  employees: Employee[];
  entries: TimesheetEntry[];
  leaveRequests: LeaveRequest[];
  holidays: Holiday[];
}): PayrollRow[] {
  const { today, employees, entries, leaveRequests, holidays } = params;
  const { start, end } =
    params.start && params.end
      ? { start: params.start, end: params.end }
      : monthRange(params.year ?? new Date().getFullYear(), params.monthIndex ?? 0);
  const dates = eachDate(start, end);
  const holidayMap = buildHolidayMap(holidays);

  const entriesByEmp = new Map<string, Map<string, TimesheetEntry>>();
  for (const e of entries) {
    if (e.date < start || e.date > end) continue;
    if (!entriesByEmp.has(e.employeeEmail)) entriesByEmp.set(e.employeeEmail, new Map());
    entriesByEmp.get(e.employeeEmail)!.set(e.date, e);
  }

  const leaveByEmp = new Map<string, LeaveRequest[]>();
  for (const r of leaveRequests) {
    if (r.status !== 'approved') continue;
    if (!leaveByEmp.has(r.employeeEmail)) leaveByEmp.set(r.employeeEmail, []);
    leaveByEmp.get(r.employeeEmail)!.push(r);
  }

  const rows: PayrollRow[] = [];
  for (const emp of employees) {
    if (emp.status !== 'active') continue;

    const leaveMap = buildApprovedLeaveMap(leaveByEmp.get(emp.email) || []);
    const empEntries = entriesByEmp.get(emp.email) || new Map<string, TimesheetEntry>();

    const row: PayrollRow = {
      employeeId: emp.id,
      employeeCode: emp.employeeCode || '',
      name: emp.name,
      designation: emp.designation,
      managerName: emp.managerName || emp.managerEmail,
      workingDays: 0,
      holidays: 0,
      weeklyOffs: 0,
      daysPresent: 0,
      leaveByCategory: {},
      totalLeave: 0,
      pendingApproval: 0,
      notSubmitted: 0,
      totalHours: 0,
      chargeableHours: 0,
      nonChargeableHours: 0,
      flags: [],
    };

    for (const d of dates) {
      // Ignore dates before the employee joined (when a joining date is known)
      if (emp.joiningDate && d < emp.joiningDate) continue;

      if (isWeekend(d)) {
        row.weeklyOffs += 1;
        continue;
      }
      if (holidayMap.has(d)) {
        row.holidays += 1;
        continue;
      }
      row.workingDays += 1;

      const leave = leaveMap.get(d);
      const entry = empEntries.get(d);

      if (leave) {
        const days = leave.half ? 0.5 : 1;
        row.leaveByCategory[leave.label] = roundDays((row.leaveByCategory[leave.label] || 0) + days);
        row.totalLeave = roundDays(row.totalLeave + days);
        if (entry && entry.status === 'approved') {
          row.flags.push(`${d}: approved timesheet on a leave day`);
        }
        if (!(leave.half && entry && entry.status === 'approved')) continue;
      }

      if (entry && entry.status === 'approved') {
        row.daysPresent += 1;
        for (const line of entry.lines) {
          row.totalHours = roundDays(row.totalHours + line.hours);
          if (line.type === 'chargeable') {
            row.chargeableHours = roundDays(row.chargeableHours + line.hours);
          } else {
            row.nonChargeableHours = roundDays(row.nonChargeableHours + line.hours);
          }
        }
      } else if (entry && entry.status === 'submitted') {
        row.pendingApproval += 1;
      } else if (d <= today) {
        row.notSubmitted += 1;
      }
    }

    if (row.pendingApproval > 0) row.flags.push(`${row.pendingApproval} day(s) pending approval`);
    if (row.notSubmitted > 0) row.flags.push(`${row.notSubmitted} day(s) not submitted`);
    rows.push(row);
  }

  rows.sort((a, b) => a.employeeCode.localeCompare(b.employeeCode) || a.name.localeCompare(b.name));
  return rows;
}


// ---------------------------------------------------------------------------
// Project-wise / staff-wise hours report
// ---------------------------------------------------------------------------

/**
 * Hours per project and per staff for a date range. Approved days count as hours;
 * submitted days are shown separately as pending. Drafts and rejected days are ignored.
 */
export function computeProjectReport(params: {
  from: string;
  to: string;
  entries: TimesheetEntry[];
  projects: Project[];
  employees: Employee[];
}): ProjectReport {
  const { from, to, entries, projects, employees } = params;
  const empByEmail = new Map(employees.map((e) => [e.email, e]));
  const projectByCode = new Map(projects.map((p) => [p.code, p]));

  const rowMap = new Map<string, ProjectSummaryRow>();
  const staffSets = new Map<string, Set<string>>();
  const matrix: Record<string, Record<string, number>> = {};
  const staffSeen = new Map<string, ProjectStaffRef>();
  const detail: TimesheetDetailRow[] = [];

  const ensureRow = (code: string, name: string, client: string, type: 'chargeable' | 'non_chargeable') => {
    let row = rowMap.get(code);
    if (!row) {
      const master = projectByCode.get(code);
      row = {
        code,
        name: master?.name || name,
        client: master?.client || client,
        type: master?.type || type,
        partnerName: master?.partnerName || '',
        managerName: master?.managerName || '',
        approvedHours: 0,
        pendingHours: 0,
        staffCount: 0,
        entryDays: 0,
      };
      rowMap.set(code, row);
    }
    return row;
  };

  for (const e of entries) {
    if (e.date < from || e.date > to) continue;
    if (e.status !== 'approved' && e.status !== 'submitted') continue;
    const emp = empByEmail.get(e.employeeEmail);
    const staffRef: ProjectStaffRef = {
      email: e.employeeEmail,
      code: emp?.employeeCode || '',
      name: emp?.name || e.employeeName,
    };
    for (const line of e.lines) {
      const row = ensureRow(line.projectCode, line.projectName, line.clientName, line.type);
      row.entryDays += 1;
      if (e.status === 'approved') {
        row.approvedHours = roundDays(row.approvedHours + line.hours);
        matrix[line.projectCode] = matrix[line.projectCode] || {};
        matrix[line.projectCode][e.employeeEmail] = roundDays(
          (matrix[line.projectCode][e.employeeEmail] || 0) + line.hours
        );
        if (!staffSets.has(line.projectCode)) staffSets.set(line.projectCode, new Set());
        staffSets.get(line.projectCode)!.add(e.employeeEmail);
        staffSeen.set(e.employeeEmail, staffRef);
      } else {
        row.pendingHours = roundDays(row.pendingHours + line.hours);
      }
      detail.push({
        date: e.date,
        employeeCode: staffRef.code,
        employeeName: staffRef.name,
        projectCode: line.projectCode,
        projectName: row.name,
        client: row.client,
        type: row.type,
        hours: line.hours,
        status: e.status,
      });
    }
  }

  for (const [code, set] of staffSets) {
    const row = rowMap.get(code);
    if (row) row.staffCount = set.size;
  }

  const projectRows = Array.from(rowMap.values()).sort(
    (a, b) => (a.type === b.type ? 0 : a.type === 'chargeable' ? -1 : 1) || a.code.localeCompare(b.code)
  );
  const staff = Array.from(staffSeen.values()).sort(
    (a, b) => a.code.localeCompare(b.code) || a.name.localeCompare(b.name)
  );
  detail.sort(
    (a, b) =>
      a.date.localeCompare(b.date) ||
      a.employeeName.localeCompare(b.employeeName) ||
      a.projectCode.localeCompare(b.projectCode)
  );
  return { projectRows, staff, matrix, detail };
}
