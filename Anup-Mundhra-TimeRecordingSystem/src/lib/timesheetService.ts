import {
  collection,
  deleteDoc,
  doc,
  getDocs,
  serverTimestamp,
  setDoc,
  updateDoc,
  writeBatch,
} from './fsAdapter';
import * as XLSX from 'xlsx';
import type { Employee } from '../types/leave';
import {
  TIMESHEET_LIMITS,
  type PayrollRow,
  type Project,
  type ProjectType,
  type TimesheetEntry,
  type TimesheetLine,
} from '../types/timesheet';
import { sanitizeEmailId } from './dateUtils';
import { db, handleFirestoreError, OperationType } from './firebase';
import { fetchGoogleSheetRows, type RawSheetTable } from './sheetsAndExcel';
import { sumHours } from './timesheetUtils';
import type { ProjectReport } from '../types/timesheet';

export const PROJECTS_TAB_NAME = 'Projects';

// ---------------------------------------------------------------------------
// Projects master (Google Sheet tab "Projects")
// ---------------------------------------------------------------------------

type ParsedProject = Omit<Project, 'updatedAt'>;

function normHeader(h: string): string {
  return h.toLowerCase().replace(/[^a-z0-9]/g, '');
}

function findHeader(headers: string[], exact: string[], partial: string[] = []): string {
  const normalized = headers.map((h) => ({ raw: h, norm: normHeader(h) }));
  for (const c of exact) {
    const hit = normalized.find((h) => h.norm === c);
    if (hit) return hit.raw;
  }
  for (const c of partial) {
    const hit = normalized.find((h) => h.norm.includes(c));
    if (hit) return hit.raw;
  }
  return '';
}

export function parseProjectsTable(table: RawSheetTable): {
  projects: ParsedProject[];
  warnings: string[];
} {
  const h = table.headers;
  const colCode = findHeader(h, ['projectcode', 'code'], ['projectcode']);
  const colName = findHeader(h, ['projectname', 'name'], ['projectname']);
  const colClient = findHeader(h, ['clientname', 'client'], ['client']);
  const colType = findHeader(h, ['type', 'projecttype'], ['type']);
  const colActive = findHeader(h, ['active', 'status'], ['active']);
  const colPartner = findHeader(h, ['projectpartner', 'partner'], []);
  const colManager = findHeader(h, ['projectmanager', 'manager'], []);
  const colPartnerEmail = findHeader(h, [], ['partneremail']);
  const colManagerEmail = findHeader(h, [], ['manageremail']);

  const warnings: string[] = [];
  if (!colCode || !colName) {
    throw new Error('The "Projects" tab needs "Project Code" and "Project Name" columns.');
  }

  const projects: ParsedProject[] = [];
  const seen = new Set<string>();
  table.rows.forEach((row, idx) => {
    const code = (row[colCode] || '').trim().toUpperCase();
    const name = (row[colName] || '').trim();
    if (!code && !name) return;
    const rowLabel = `Row ${idx + 2}`;
    if (!code || !name) {
      warnings.push(`${rowLabel}: missing project code or name, skipped.`);
      return;
    }
    if (code.length > TIMESHEET_LIMITS.maxProjectCodeLength) {
      warnings.push(`${rowLabel}: project code "${code}" is too long, skipped.`);
      return;
    }
    const id = sanitizeEmailId(code);
    if (seen.has(id)) {
      warnings.push(`${rowLabel}: duplicate project code "${code}", skipped.`);
      return;
    }
    seen.add(id);

    const typeRaw = (colType ? row[colType] : '').toLowerCase();
    const type: ProjectType = typeRaw.includes('non') ? 'non_chargeable' : 'chargeable';
    const activeRaw = (colActive ? row[colActive] : 'yes').trim().toLowerCase();
    const active = !(activeRaw === 'no' || activeRaw === 'false' || activeRaw === 'inactive' || activeRaw === '0');

    projects.push({
      id,
      code,
      name: name.slice(0, TIMESHEET_LIMITS.maxProjectNameLength),
      client: ((colClient ? row[colClient] : '') || '').trim().slice(0, 120),
      type,
      active,
      partnerName: ((colPartner ? row[colPartner] : '') || '').trim().slice(0, 120),
      partnerEmail: ((colPartnerEmail ? row[colPartnerEmail] : '') || '').trim().toLowerCase(),
      managerName: ((colManager ? row[colManager] : '') || '').trim().slice(0, 120),
      managerEmail: ((colManagerEmail ? row[colManagerEmail] : '') || '').trim().toLowerCase(),
    });
  });

  if (projects.length === 0) warnings.push('No project rows were found in the "Projects" tab.');
  return { projects, warnings };
}

export async function fetchProjectsFromSheet(
  spreadsheetId: string,
  accessToken: string
): Promise<{ projects: ParsedProject[]; warnings: string[] }> {
  const table = await fetchGoogleSheetRows(spreadsheetId, PROJECTS_TAB_NAME, accessToken);
  return parseProjectsTable(table);
}

/** Upserts projects from the sheet; projects no longer in the sheet are kept but marked inactive. */
export async function commitProjectsSync(
  incoming: ParsedProject[],
  existing: Project[]
): Promise<{ added: number; updated: number; deactivated: number }> {
  try {
    const batch = writeBatch(db);
    const incomingIds = new Set(incoming.map((p) => p.id));
    const existingById = new Map(existing.map((p) => [p.id, p]));
    let added = 0;
    let updated = 0;
    let deactivated = 0;

    for (const p of incoming) {
      if (existingById.has(p.id)) updated += 1;
      else added += 1;
      batch.set(doc(db, 'projects', p.id), {
        code: p.code,
        name: p.name,
        client: p.client,
        type: p.type,
        active: p.active,
        partnerName: p.partnerName,
        partnerEmail: p.partnerEmail,
        managerName: p.managerName,
        managerEmail: p.managerEmail,
        updatedAt: serverTimestamp(),
      });
    }
    for (const p of existing) {
      if (!incomingIds.has(p.id) && p.active) {
        deactivated += 1;
        batch.set(doc(db, 'projects', p.id), {
          code: p.code,
          name: p.name,
          client: p.client,
          type: p.type,
          active: false,
          partnerName: p.partnerName,
          partnerEmail: p.partnerEmail,
          managerName: p.managerName,
          managerEmail: p.managerEmail,
          updatedAt: serverTimestamp(),
        });
      }
    }
    await batch.commit();
    return { added, updated, deactivated };
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'projects');
  }
}

// ---------------------------------------------------------------------------
// Timesheet entries
// ---------------------------------------------------------------------------

export function entryId(employeeId: string, date: string): string {
  return `${employeeId}_${date}`;
}

/** Approver for an employee: reporting manager, or the employee themself when there is none (HR admin approves). */
export function resolveApproverEmail(employee: Employee): string {
  const m = (employee.managerEmail || '').trim().toLowerCase();
  return m && m !== employee.email ? m : employee.email;
}

export function isSelfManaged(entry: Pick<TimesheetEntry, 'employeeEmail' | 'managerEmail'>): boolean {
  return entry.employeeEmail === entry.managerEmail;
}

export async function saveTimesheetDay(params: {
  employee: Employee;
  date: string;
  lines: TimesheetLine[];
  existing?: TimesheetEntry;
}): Promise<void> {
  const { employee, date, lines, existing } = params;
  const id = entryId(employee.id, date);
  try {
    if (lines.length === 0) {
      if (!existing) return;
      if (existing.status !== 'draft') {
        throw new Error('Only a draft day can be cleared. Edit the lines instead, then save and resubmit.');
      }
      await deleteDoc(doc(db, 'timesheetEntries', id));
      return;
    }
    if (existing) {
      await updateDoc(doc(db, 'timesheetEntries', id), {
        lines,
        totalHours: sumHours(lines),
        status: 'draft',
        updatedAt: serverTimestamp(),
      });
      return;
    }
    await setDoc(doc(db, 'timesheetEntries', id), {
      employeeId: employee.id,
      employeeEmail: employee.email,
      employeeName: employee.name,
      managerEmail: resolveApproverEmail(employee),
      date,
      lines,
      totalHours: sumHours(lines),
      status: 'draft',
      managerComment: '',
      reviewedBy: '',
      reopenedBy: '',
      reopenReason: '',
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    if (error instanceof Error && error.message.startsWith('Only a draft')) throw error;
    handleFirestoreError(error, OperationType.WRITE, `timesheetEntries/${id}`);
  }
}

export async function submitTimesheetDays(entries: TimesheetEntry[]): Promise<void> {
  try {
    const batch = writeBatch(db);
    for (const e of entries) {
      batch.update(doc(db, 'timesheetEntries', e.id), {
        status: 'submitted',
        submittedAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      });
    }
    await batch.commit();
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'timesheetEntries');
  }
}

export async function reviewTimesheetDays(params: {
  entries: TimesheetEntry[];
  decision: 'approved' | 'rejected';
  comment: string;
  reviewerEmail: string;
}): Promise<void> {
  const { entries, decision, comment, reviewerEmail } = params;
  const trimmed = comment.trim().slice(0, TIMESHEET_LIMITS.maxCommentLength);
  if (decision === 'rejected' && !trimmed) {
    throw new Error('Please add a comment explaining why the timesheet is rejected.');
  }
  try {
    const batch = writeBatch(db);
    for (const e of entries) {
      batch.update(doc(db, 'timesheetEntries', e.id), {
        status: decision,
        managerComment: trimmed,
        reviewedBy: reviewerEmail,
        reviewedAt: serverTimestamp(),
        updatedAt: serverTimestamp(),
      });
    }
    await batch.commit();
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, 'timesheetEntries');
  }
}

export async function reopenTimesheetDay(params: {
  entry: TimesheetEntry;
  adminEmail: string;
  reason: string;
}): Promise<void> {
  const { entry, adminEmail, reason } = params;
  const trimmed = reason.trim().slice(0, TIMESHEET_LIMITS.maxReopenReasonLength);
  if (!trimmed) throw new Error('Please give a reason for reopening this day.');
  try {
    await updateDoc(doc(db, 'timesheetEntries', entry.id), {
      status: 'draft',
      reopenedBy: adminEmail,
      reopenReason: trimmed,
      updatedAt: serverTimestamp(),
    });
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, `timesheetEntries/${entry.id}`);
  }
}

export async function loadAllTimesheetEntriesForAdmin(): Promise<TimesheetEntry[]> {
  try {
    const snap = await getDocs(collection(db, 'timesheetEntries'));
    return snap.docs.map((d) => ({ id: d.id, ...(d.data() as Omit<TimesheetEntry, 'id'>) }));
  } catch (error) {
    handleFirestoreError(error, OperationType.LIST, 'timesheetEntries');
  }
}

// ---------------------------------------------------------------------------
// Payroll export
// ---------------------------------------------------------------------------

export function exportPayrollToExcel(
  rows: PayrollRow[],
  monthLabelText: string,
  leaveCategoryNames: string[]
): void {
  const data = rows.map((r) => {
    const base: Record<string, string | number> = {
      'Employee Code': r.employeeCode,
      'Employee Name': r.name,
      Designation: r.designation,
      'Reporting Manager': r.managerName,
      'Working Days': r.workingDays,
      Holidays: r.holidays,
      'Weekly Offs': r.weeklyOffs,
      'Days Present (Approved)': r.daysPresent,
    };
    for (const name of leaveCategoryNames) {
      base[`Leave: ${name}`] = r.leaveByCategory[name] || 0;
    }
    base['Total Leave Days'] = r.totalLeave;
    base['Pending Approval (days)'] = r.pendingApproval;
    base['Not Submitted (days)'] = r.notSubmitted;
    base['Total Hours'] = r.totalHours;
    base['Chargeable Hours'] = r.chargeableHours;
    base['Non-chargeable Hours'] = r.nonChargeableHours;
    base.Flags = r.flags.join('; ');
    return base;
  });
  const sheet = XLSX.utils.json_to_sheet(data);
  const book = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(book, sheet, 'Payroll');
  XLSX.writeFile(book, `LeaveLedger_Payroll_Attendance_${monthLabelText.replace(/\s+/g, '_')}.xlsx`);
}


/** Multi-sheet workbook: staff summary, project summary, project x staff, staff x project, daily detail. */
export function exportTimesheetReportToExcel(params: {
  periodLabel: string;
  from: string;
  to: string;
  rows: PayrollRow[];
  leaveCategoryNames: string[];
  report: ProjectReport;
}): void {
  const { periodLabel, from, to, rows, leaveCategoryNames, report } = params;
  const book = XLSX.utils.book_new();
  const widths = (cols: number, first = 14) => Array.from({ length: cols }, (_, i) => ({ wch: i === 0 ? first : 16 }));
  const r1 = (n: number) => Math.round(n * 100) / 100;

  // 1. Staff summary (attendance, leave and hours)
  const staffHeader = [
    'Employee Code', 'Employee Name', 'Designation', 'Reporting Manager',
    'Working Days', 'Holidays', 'Weekly Offs', 'Days Present (Approved)',
    ...leaveCategoryNames.map((n) => `Leave: ${n}`),
    'Total Leave Days', 'Pending Approval (days)', 'Not Submitted (days)',
    'Total Hours', 'Chargeable Hours', 'Non-chargeable Hours', 'Chargeable %', 'Flags',
  ];
  const staffAoa: (string | number)[][] = [staffHeader];
  const tot = { wd: 0, hol: 0, off: 0, pres: 0, leave: 0, pend: 0, ns: 0, h: 0, c: 0, nc: 0 };
  const leaveTot: Record<string, number> = {};
  for (const r of rows) {
    staffAoa.push([
      r.employeeCode, r.name, r.designation, r.managerName,
      r.workingDays, r.holidays, r.weeklyOffs, r.daysPresent,
      ...leaveCategoryNames.map((n) => r.leaveByCategory[n] || 0),
      r.totalLeave, r.pendingApproval, r.notSubmitted,
      r.totalHours, r.chargeableHours, r.nonChargeableHours,
      r.totalHours > 0 ? r1((r.chargeableHours / r.totalHours) * 100) : 0,
      r.flags.join('; '),
    ]);
    tot.wd += r.workingDays; tot.hol += r.holidays; tot.off += r.weeklyOffs; tot.pres += r.daysPresent;
    tot.leave += r.totalLeave; tot.pend += r.pendingApproval; tot.ns += r.notSubmitted;
    tot.h += r.totalHours; tot.c += r.chargeableHours; tot.nc += r.nonChargeableHours;
    for (const n of leaveCategoryNames) leaveTot[n] = (leaveTot[n] || 0) + (r.leaveByCategory[n] || 0);
  }
  staffAoa.push([
    'TOTAL', '', '', '', r1(tot.wd), r1(tot.hol), r1(tot.off), r1(tot.pres),
    ...leaveCategoryNames.map((n) => r1(leaveTot[n] || 0)),
    r1(tot.leave), r1(tot.pend), r1(tot.ns), r1(tot.h), r1(tot.c), r1(tot.nc),
    tot.h > 0 ? r1((tot.c / tot.h) * 100) : 0, '',
  ]);

  // 2. Project summary
  const projAoa: (string | number)[][] = [[
    'Project Code', 'Project Name', 'Client', 'Type', 'Partner', 'Manager',
    'Approved Hours', 'Pending Approval Hours', 'Staff Count', 'Entry Lines',
  ]];
  let projApproved = 0;
  let projPending = 0;
  for (const p of report.projectRows) {
    projAoa.push([
      p.code, p.name, p.client, p.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable',
      p.partnerName, p.managerName, p.approvedHours, p.pendingHours, p.staffCount, p.entryDays,
    ]);
    projApproved += p.approvedHours;
    projPending += p.pendingHours;
  }
  projAoa.push(['TOTAL', '', '', '', '', '', r1(projApproved), r1(projPending), '', '']);

  // 3. Project x Staff (approved hours)
  const pxsAoa: (string | number)[][] = [
    ['Project Code', 'Project Name', 'Type', ...report.staff.map((s) => s.name), 'Total'],
  ];
  const colTotals = report.staff.map(() => 0);
  for (const p of report.projectRows) {
    const cells = report.staff.map((s) => report.matrix[p.code]?.[s.email] || 0);
    cells.forEach((v, i) => { colTotals[i] += v; });
    pxsAoa.push([p.code, p.name, p.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable', ...cells, r1(cells.reduce((a, b) => a + b, 0))]);
  }
  pxsAoa.push(['TOTAL', '', '', ...colTotals.map(r1), r1(colTotals.reduce((a, b) => a + b, 0))]);

  // 4. Staff x Project (approved hours)
  const sxpAoa: (string | number)[][] = [
    ['Employee Code', 'Employee Name', ...report.projectRows.map((p) => p.code), 'Total', 'Chargeable', 'Non-chargeable'],
  ];
  for (const s of report.staff) {
    let total = 0; let charge = 0; let nonCharge = 0;
    const cells = report.projectRows.map((p) => {
      const v = report.matrix[p.code]?.[s.email] || 0;
      total += v;
      if (p.type === 'chargeable') charge += v; else nonCharge += v;
      return v;
    });
    sxpAoa.push([s.code, s.name, ...cells, r1(total), r1(charge), r1(nonCharge)]);
  }

  // 5. Daily detail
  const detailAoa: (string | number)[][] = [[
    'Date', 'Employee Code', 'Employee Name', 'Project Code', 'Project Name', 'Client', 'Type', 'Hours', 'Status',
  ]];
  for (const d of report.detail) {
    detailAoa.push([
      d.date, d.employeeCode, d.employeeName, d.projectCode, d.projectName, d.client,
      d.type === 'chargeable' ? 'Chargeable' : 'Non-chargeable', d.hours,
      d.status === 'approved' ? 'Approved' : 'Pending approval',
    ]);
  }

  // 0. Notes
  const notesAoa: (string | number)[][] = [
    ['TimeRecordingSystem report'],
    ['Period', `${from} to ${to}`],
    ['Label', periodLabel],
    ['Generated on', new Date().toISOString().slice(0, 10)],
    [],
    ['Basis'],
    ['Present days and hours count APPROVED timesheets only.'],
    ['Submitted-but-not-approved days appear as "Pending" and are excluded from approved hours.'],
    ['Draft and rejected days are ignored. Leave comes from approved leave requests.'],
  ];

  const add = (name: string, aoa: (string | number)[][], cols: number, first = 14) => {
    const sheet = XLSX.utils.aoa_to_sheet(aoa);
    sheet['!cols'] = widths(cols, first);
    XLSX.utils.book_append_sheet(book, sheet, name);
  };
  add('Notes', notesAoa, 2, 40);
  add('Staff Summary', staffAoa, staffHeader.length);
  add('Project Summary', projAoa, 10);
  add('Project x Staff', pxsAoa, pxsAoa[0].length);
  add('Staff x Project', sxpAoa, sxpAoa[0].length);
  add('Daily Detail', detailAoa, 9, 12);

  XLSX.writeFile(book, `TimeRecordingSystem_Report_${from}_to_${to}.xlsx`);
}
