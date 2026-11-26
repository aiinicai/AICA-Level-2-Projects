import * as XLSX from 'xlsx';
import {
  VALIDATION_LIMITS,
  type Employee,
  type EmployeeStatus,
  type ParsedRosterRow,
  type RosterDiffItem,
  type RosterDiffSummary,
} from '../types/leave';
import { normalizeEmail, sanitizeEmailId } from './dateUtils';

export interface ColumnMapping {
  employeeCode: string;
  name: string;
  email: string;
  designation: string;
  department: string;
  managerEmail: string;
  status: string;
  joiningDate: string;
  isAdmin: string;
}

export interface SpreadsheetMetadata {
  spreadsheetId: string;
  title: string;
  sheetNames: string[];
}

export interface RawSheetTable {
  headers: string[];
  rows: Record<string, string>[];
}

export function extractSpreadsheetId(input: string): string {
  const trimmed = input.trim();
  const urlMatch = trimmed.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  if (urlMatch && urlMatch[1]) {
    return urlMatch[1];
  }
  return trimmed;
}

export async function fetchSpreadsheetMetadata(
  spreadsheetId: string,
  accessToken: string
): Promise<SpreadsheetMetadata> {
  const cleanId = extractSpreadsheetId(spreadsheetId);
  if (!cleanId) {
    throw new Error('Please enter a valid Google Sheet URL or Spreadsheet ID.');
  }

  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(cleanId)}?fields=properties.title,sheets.properties.title`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (res.status === 401 || res.status === 403) {
    const peek = await res.clone().json().catch(() => ({}));
    const m = String(peek?.error?.message || '');
    if (res.status === 401 || /insufficient authentication scopes|insufficient permission/i.test(m)) {
      throw new Error('TOKEN_EXPIRED');
    }
  }

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const msg = errBody?.error?.message || `Failed to load Google Sheet (${res.status}).`;
    throw new Error(msg);
  }

  const data = await res.json();
  const title = String(data?.properties?.title || 'Untitled Spreadsheet');
  const sheetNames: string[] = Array.isArray(data?.sheets)
    ? data.sheets
        .map((s: { properties?: { title?: string } }) => s?.properties?.title)
        .filter((t: unknown): t is string => typeof t === 'string' && t.length > 0)
    : [];

  if (sheetNames.length === 0) {
    throw new Error('No worksheet tabs were found in this Google Sheet.');
  }

  return {
    spreadsheetId: cleanId,
    title,
    sheetNames,
  };
}

export async function fetchGoogleSheetRows(
  spreadsheetId: string,
  sheetName: string,
  accessToken: string
): Promise<RawSheetTable> {
  const cleanId = extractSpreadsheetId(spreadsheetId);
  const range = `'${sheetName.replace(/'/g, "''")}'!A1:Z5000`;
  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${encodeURIComponent(cleanId)}/values/${encodeURIComponent(range)}?majorDimension=ROWS`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (res.status === 401 || res.status === 403) {
    const peek = await res.clone().json().catch(() => ({}));
    const m = String(peek?.error?.message || '');
    if (res.status === 401 || /insufficient authentication scopes|insufficient permission/i.test(m)) {
      throw new Error('TOKEN_EXPIRED');
    }
  }

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    const msg = errBody?.error?.message || `Failed to read rows from "${sheetName}".`;
    throw new Error(msg);
  }

  const data = await res.json();
  const values: unknown[][] = Array.isArray(data?.values) ? data.values : [];
  if (values.length < 2) {
    throw new Error(`The selected sheet "${sheetName}" must have a header row and at least one employee row.`);
  }

  const rawHeaders = values[0].map((cell, idx) => {
    const label = String(cell ?? '').trim();
    return label || `Column_${idx + 1}`;
  });

  const rows: Record<string, string>[] = [];
  for (let i = 1; i < values.length; i += 1) {
    const rowArr = values[i] || [];
    const hasAnyValue = rowArr.some((cell) => String(cell ?? '').trim().length > 0);
    if (!hasAnyValue) continue;
    const obj: Record<string, string> = {};
    rawHeaders.forEach((header, colIdx) => {
      obj[header] = String(rowArr[colIdx] ?? '').trim();
    });
    rows.push(obj);
  }

  return { headers: rawHeaders, rows };
}

export async function parseExcelOrCsvFile(file: File): Promise<RawSheetTable> {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: 'array' });
  const firstSheetName = workbook.SheetNames[0];
  if (!firstSheetName) {
    throw new Error('No worksheets found in the uploaded file.');
  }
  const sheet = workbook.Sheets[firstSheetName];
  const matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
  if (matrix.length < 2) {
    throw new Error('The uploaded spreadsheet needs a header row and at least one employee row.');
  }

  const headers = (matrix[0] || []).map((cell, idx) => {
    const label = String(cell ?? '').trim();
    return label || `Column_${idx + 1}`;
  });

  const rows: Record<string, string>[] = [];
  for (let i = 1; i < matrix.length; i += 1) {
    const rowArr = matrix[i] || [];
    const hasAnyValue = rowArr.some((cell) => String(cell ?? '').trim().length > 0);
    if (!hasAnyValue) continue;
    const obj: Record<string, string> = {};
    headers.forEach((header, idx) => {
      obj[header] = String(rowArr[idx] ?? '').trim();
    });
    rows.push(obj);
  }

  return { headers, rows };
}

export async function parseCsvFromUrl(url: string): Promise<RawSheetTable> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Could not load attached spreadsheet (${res.status}).`);
  }
  const csvText = await res.text();
  const workbook = XLSX.read(csvText, { type: 'string' });
  const firstSheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[firstSheetName];
  const matrix = XLSX.utils.sheet_to_json<unknown[]>(sheet, { header: 1, defval: '' });
  if (matrix.length < 2) {
    throw new Error('The attached spreadsheet needs a header row and at least one employee row.');
  }

  const headers = (matrix[0] || []).map((cell, idx) => {
    const label = String(cell ?? '').trim();
    return label || `Column_${idx + 1}`;
  });

  const rows: Record<string, string>[] = [];
  for (let i = 1; i < matrix.length; i += 1) {
    const rowArr = matrix[i] || [];
    const hasAnyValue = rowArr.some((cell) => String(cell ?? '').trim().length > 0);
    if (!hasAnyValue) continue;
    const obj: Record<string, string> = {};
    headers.forEach((header, idx) => {
      obj[header] = String(rowArr[idx] ?? '').trim();
    });
    rows.push(obj);
  }

  return { headers, rows };
}

export function downloadRosterTemplate(): void {
  const sampleRows = [
    {
      Name: 'Aarav Mehta',
      Email: 'aarav.mehta@company.com',
      Designation: 'VP Engineering',
      Department: 'Engineering',
      'Manager Email': '',
      Status: 'Active',
      'Joining Date': '2022-03-15',
      Admin: 'Yes',
    },
    {
      Name: 'Priya Nair',
      Email: 'priya.nair@company.com',
      Designation: 'Engineering Manager',
      Department: 'Engineering',
      'Manager Email': 'aarav.mehta@company.com',
      Status: 'Active',
      'Joining Date': '2023-06-01',
      Admin: 'No',
    },
    {
      Name: 'Rohan Kapoor',
      Email: 'rohan.kapoor@company.com',
      Designation: 'Senior Frontend Engineer',
      Department: 'Engineering',
      'Manager Email': 'priya.nair@company.com',
      Status: 'Active',
      'Joining Date': '2026-01-12',
      Admin: 'No',
    },
    {
      Name: 'Neha Verma',
      Email: 'neha.verma@company.com',
      Designation: 'Product Designer',
      Department: 'Design',
      'Manager Email': 'priya.nair@company.com',
      Status: 'Resigned',
      'Joining Date': '2024-02-01',
      Admin: 'No',
    },
  ];
  const worksheet = XLSX.utils.json_to_sheet(sampleRows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Employees');
  XLSX.writeFile(workbook, 'LeaveLedger_Employee_Roster_Template.xlsx');
}

export function autoDetectColumnMapping(headers: string[]): ColumnMapping {
  const findMatch = (candidates: string[]): string => {
    const normalizedHeaders = headers.map((h) => ({
      raw: h,
      norm: h.toLowerCase().replace(/[^a-z0-9]/g, ''),
    }));

    for (const candidate of candidates) {
      const exact = normalizedHeaders.find((h) => h.norm === candidate);
      if (exact) return exact.raw;
    }
    for (const candidate of candidates) {
      const partial = normalizedHeaders.find((h) => h.norm.includes(candidate));
      if (partial) return partial.raw;
    }
    return '';
  };

  return {
    employeeCode: findMatch(['employeecode', 'empcode', 'code', 'empid', 'employeeid']),
    name: findMatch(['employeename', 'fullname', 'name', 'empname']),
    email: findMatch(['emailid', 'employeeemail', 'email', 'workemail', 'mail']),
    designation: findMatch(['designation', 'jobtitle', 'title', 'position', 'role']),
    department: findMatch(['department', 'dept', 'team', 'division']),
    managerEmail: findMatch(['manageremail', 'reportingmanageremail', 'reportingmanager', 'approveremail', 'manager', 'reportsto']),
    status: findMatch(['status', 'employmentstatus', 'state', 'active']),
    joiningDate: findMatch(['joiningdate', 'doj', 'startdate', 'dateofjoining']),
    isAdmin: findMatch(['admin', 'isadmin', 'hradmin']),
  };
}

function parseStatusValue(raw: string): EmployeeStatus {
  const lower = raw.trim().toLowerCase();
  if (
    lower.includes('resign') ||
    lower.includes('inactive') ||
    lower.includes('exit') ||
    lower.includes('left') ||
    lower.includes('terminat') ||
    lower === 'no' ||
    lower === 'false'
  ) {
    return 'resigned';
  }
  return 'active';
}

function parseBoolValue(raw: string): boolean {
  const lower = raw.trim().toLowerCase();
  return lower === 'yes' || lower === 'true' || lower === '1' || lower === 'admin' || lower === 'hr';
}

export function computeRosterDiff(
  table: RawSheetTable,
  mapping: ColumnMapping,
  existingEmployees: Employee[],
  markMissingAsResigned: boolean
): RosterDiffSummary {
  const warnings: string[] = [];
  const existingById = new Map<string, Employee>();
  for (const emp of existingEmployees) {
    existingById.set(emp.id, emp);
  }

  // Pre-index name -> email across existing directory and incoming sheet so Reporting Manager names resolve to emails
  const emailByName = new Map<string, string>();
  for (const emp of existingEmployees) {
    if (emp.name && emp.email) {
      emailByName.set(emp.name.trim().toLowerCase(), emp.email);
    }
  }
  for (const rawRow of table.rows) {
    const rEmail = normalizeEmail(mapping.email ? rawRow[mapping.email] || '' : '');
    const rName = (mapping.name ? rawRow[mapping.name] || '' : '').trim().toLowerCase();
    if (rName && rEmail && VALIDATION_LIMITS.emailPattern.test(rEmail)) {
      emailByName.set(rName, rEmail);
    }
  }

  const parsedById = new Map<string, ParsedRosterRow>();
  table.rows.forEach((rawRow, idx) => {
    const employeeCode = (mapping.employeeCode ? rawRow[mapping.employeeCode] || '' : '')
      .trim()
      .slice(0, VALIDATION_LIMITS.maxEmployeeCodeLength);
    const rawEmail = mapping.email ? rawRow[mapping.email] || '' : '';
    const email = normalizeEmail(rawEmail);
    const name = (mapping.name ? rawRow[mapping.name] || '' : '').trim();
    const designation = (mapping.designation ? rawRow[mapping.designation] || '' : '').trim() || 'Team Member';
    const department = (mapping.department ? rawRow[mapping.department] || '' : '').trim();
    const rawManager = (mapping.managerEmail ? rawRow[mapping.managerEmail] || '' : '').trim();
    let managerEmail = '';
    if (rawManager) {
      const asEmail = normalizeEmail(rawManager);
      if (VALIDATION_LIMITS.emailPattern.test(asEmail)) {
        managerEmail = asEmail;
      } else {
        const matchedEmail = emailByName.get(rawManager.toLowerCase());
        if (matchedEmail) {
          managerEmail = matchedEmail;
        } else {
          warnings.push(`Row ${idx + 2} (${name || email}): Reporting Manager "${rawManager}" did not match any employee name or email in the sheet.`);
        }
      }
    }
    const statusRaw = mapping.status ? rawRow[mapping.status] || '' : '';
    const status = statusRaw ? parseStatusValue(statusRaw) : 'active';
    const joiningDate = (mapping.joiningDate ? rawRow[mapping.joiningDate] || '' : '').trim().slice(0, VALIDATION_LIMITS.maxJoiningDateLength);
    const isAdmin = mapping.isAdmin ? parseBoolValue(rawRow[mapping.isAdmin] || '') : false;

    if (!email || !VALIDATION_LIMITS.emailPattern.test(email)) {
      warnings.push(`Row ${idx + 2}: Skipped due to invalid or missing email ("${rawEmail}").`);
      return;
    }
    if (!name) {
      warnings.push(`Row ${idx + 2} (${email}): Skipped because Employee Name is blank.`);
      return;
    }

    const empId = sanitizeEmailId(email);
    parsedById.set(empId, {
      rowIndex: idx + 2,
      employeeCode,
      name: name.slice(0, VALIDATION_LIMITS.maxNameLength),
      email: email.slice(0, VALIDATION_LIMITS.maxEmailLength),
      designation: designation.slice(0, VALIDATION_LIMITS.maxDesignationLength),
      department: department.slice(0, VALIDATION_LIMITS.maxDepartmentLength),
      managerEmail: managerEmail.slice(0, VALIDATION_LIMITS.maxEmailLength),
      status,
      joiningDate,
      isAdmin,
    });
  });

  // Determine which emails have >= 1 active direct report
  const managerEmailSet = new Set<string>();
  const nameByEmail = new Map<string, string>();
  for (const existing of existingEmployees) {
    nameByEmail.set(existing.email, existing.name);
  }
  for (const row of parsedById.values()) {
    nameByEmail.set(row.email, row.name);
  }
  for (const row of parsedById.values()) {
    if (row.status === 'active' && row.managerEmail) {
      managerEmailSet.add(row.managerEmail);
    }
  }
  if (!markMissingAsResigned) {
    for (const existing of existingEmployees) {
      const id = existing.id;
      if (!parsedById.has(id) && existing.status === 'active' && existing.managerEmail) {
        managerEmailSet.add(existing.managerEmail);
      }
    }
  }

  const newJoinees: RosterDiffItem[] = [];
  const updated: RosterDiffItem[] = [];
  const resignees: RosterDiffItem[] = [];
  let unchangedCount = 0;
  const resolvedRecords: Omit<Employee, 'id' | 'updatedAt'>[] = [];

  for (const [empId, incoming] of parsedById.entries()) {
    const existing = existingById.get(empId);
    const isManager = managerEmailSet.has(incoming.email);
    const managerName = incoming.managerEmail ? (nameByEmail.get(incoming.managerEmail) || incoming.managerEmail) : '';

    resolvedRecords.push({
      employeeCode: incoming.employeeCode,
      name: incoming.name,
      email: incoming.email,
      designation: incoming.designation,
      department: incoming.department,
      managerEmail: incoming.managerEmail,
      managerName: managerName.slice(0, VALIDATION_LIMITS.maxNameLength),
      isManager,
      isAdmin: incoming.isAdmin || existing?.isAdmin || false,
      status: incoming.status,
      joiningDate: incoming.joiningDate,
      source: 'google_sheet',
    });

    if (!existing) {
      if (incoming.status === 'resigned') {
        resignees.push({
          employeeId: empId,
          incoming,
          changeType: 'resignee',
          changes: ['Imported as Resigned'],
        });
      } else {
        newJoinees.push({
          employeeId: empId,
          incoming,
          changeType: 'new_joinee',
          changes: ['New employee onboarding + default leave balances'],
        });
      }
      continue;
    }

    const changes: string[] = [];
    if ((existing.employeeCode || '') !== incoming.employeeCode) changes.push(`Code: ${existing.employeeCode || '—'} → ${incoming.employeeCode || '—'}`);
    if (existing.name !== incoming.name) changes.push(`Name: ${existing.name} → ${incoming.name}`);
    if (existing.designation !== incoming.designation) changes.push(`Designation: ${existing.designation} → ${incoming.designation}`);
    if (existing.department !== incoming.department) changes.push(`Dept: ${existing.department || '—'} → ${incoming.department || '—'}`);
    if (existing.managerEmail !== incoming.managerEmail) changes.push(`Manager: ${existing.managerEmail || 'None'} → ${incoming.managerEmail || 'None'}`);
    if (existing.isManager !== isManager) changes.push(`Approver authority: ${isManager ? 'Granted' : 'Removed'}`);
    if (existing.status !== incoming.status) changes.push(`Status: ${existing.status} → ${incoming.status}`);

    if (existing.status === 'active' && incoming.status === 'resigned') {
      resignees.push({
        employeeId: empId,
        incoming,
        existing,
        changeType: 'resignee',
        changes,
      });
    } else if (changes.length > 0) {
      updated.push({
        employeeId: empId,
        incoming,
        existing,
        changeType: 'updated',
        changes,
      });
    } else {
      unchangedCount += 1;
    }
  }

  // Handle employees missing from sheet when full-roster sync is enabled
  if (markMissingAsResigned) {
    for (const existing of existingEmployees) {
      if (!parsedById.has(existing.id) && existing.status === 'active') {
        const resignRecord: ParsedRosterRow = {
          rowIndex: -1,
          employeeCode: existing.employeeCode || '',
          name: existing.name,
          email: existing.email,
          designation: existing.designation,
          department: existing.department,
          managerEmail: existing.managerEmail,
          status: 'resigned',
          joiningDate: existing.joiningDate,
          isAdmin: existing.isAdmin,
        };
        resignees.push({
          employeeId: existing.id,
          incoming: resignRecord,
          existing,
          changeType: 'resignee',
          changes: ['Removed from sheet → Marked Resigned'],
        });
        resolvedRecords.push({
          name: existing.name,
          email: existing.email,
          designation: existing.designation,
          department: existing.department,
          managerEmail: existing.managerEmail,
          managerName: existing.managerName,
          isManager: managerEmailSet.has(existing.email),
          isAdmin: existing.isAdmin,
          status: 'resigned',
          joiningDate: existing.joiningDate,
          source: existing.source,
        });
      }
    }
  }

  return {
    newJoinees,
    updated,
    resignees,
    unchangedCount,
    warnings,
    resolvedRecords,
  };
}
