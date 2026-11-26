export const BOOTSTRAPPED_ADMIN_EMAIL = 'anup.mundhra15@gmail.com';

// Verbatim validation bounds synchronized with firebase-blueprint.json
export const VALIDATION_LIMITS = {
  idPattern: /^[a-zA-Z0-9_-]+$/,
  emailPattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  datePattern: /^\d{4}-\d{2}-\d{2}$/,
  codePattern: /^[A-Z0-9_-]+$/,
  maxIdLength: 128,
  maxEmployeeCodeLength: 40,
  maxNameLength: 120,
  maxEmailLength: 160,
  maxDesignationLength: 120,
  maxDepartmentLength: 100,
  maxCategoryNameLength: 80,
  maxCategoryCodeLength: 16,
  maxReasonLength: 500,
  maxCommentLength: 500,
  maxHolidayNameLength: 100,
  maxJoiningDateLength: 20,
  maxSpreadsheetIdLength: 200,
  maxSpreadsheetTitleLength: 160,
  maxSheetNameLength: 120,
} as const;

export type EmployeeStatus = 'active' | 'resigned';
export type RosterSource = 'google_sheet' | 'excel' | 'manual';
export type HalfDayOption = 'none' | 'first_half' | 'second_half';
export type LeaveStatus = 'pending' | 'approved' | 'rejected' | 'cancelled';

export interface Employee {
  id: string;
  employeeCode?: string;
  name: string;
  email: string;
  designation: string;
  department: string;
  managerEmail: string;
  managerName: string;
  isManager: boolean;
  isAdmin: boolean;
  status: EmployeeStatus;
  joiningDate: string;
  source: RosterSource;
  updatedAt?: unknown;
}

export interface LeaveCategory {
  id: string;
  name: string;
  code: string;
  defaultOpening: number;
  monthlyAccrual: number;
  allowNegative: boolean;
  requiresReason: boolean;
  active: boolean;
  updatedAt?: unknown;
}

export interface LeaveBalance {
  id: string;
  employeeId: string;
  employeeEmail: string;
  employeeName: string;
  managerEmail: string;
  year: number;
  categoryId: string;
  categoryName: string;
  opening: number;
  accrued: number;
  availed: number;
  closing: number;
  updatedAt?: unknown;
}

export interface LeaveRequest {
  id: string;
  employeeId: string;
  employeeEmail: string;
  employeeName: string;
  employeeDesignation: string;
  managerEmail: string;
  categoryId: string;
  categoryName: string;
  startDate: string;
  endDate: string;
  halfDay: HalfDayOption;
  workingDays: number;
  reason: string;
  status: LeaveStatus;
  managerComment: string;
  reviewedBy: string;
  reviewedAt?: unknown;
  createdAt?: unknown;
  updatedAt?: unknown;
}

export interface Holiday {
  id: string;
  date: string;
  name: string;
  updatedAt?: unknown;
}

export interface RosterSyncConfig {
  spreadsheetId: string;
  spreadsheetTitle: string;
  sheetName: string;
  lastSyncedBy: string;
  activeCount: number;
  resignedCount: number;
  updatedAt?: unknown;
}

export interface ParsedRosterRow {
  rowIndex: number;
  employeeCode: string;
  name: string;
  email: string;
  designation: string;
  department: string;
  managerEmail: string;
  status: EmployeeStatus;
  joiningDate: string;
  isAdmin: boolean;
}

export interface RosterDiffItem {
  employeeId: string;
  incoming: ParsedRosterRow;
  existing?: Employee;
  changeType: 'new_joinee' | 'updated' | 'resignee' | 'unchanged';
  changes: string[];
}

export interface RosterDiffSummary {
  newJoinees: RosterDiffItem[];
  updated: RosterDiffItem[];
  resignees: RosterDiffItem[];
  unchangedCount: number;
  warnings: string[];
  resolvedRecords: Omit<Employee, 'id' | 'updatedAt'>[];
}

export interface ToastMessage {
  id: string;
  type: 'success' | 'error' | 'info';
  title: string;
  detail?: string;
}
