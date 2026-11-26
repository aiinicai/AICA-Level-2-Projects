export const TIMESHEET_LIMITS = {
  dailyHours: 8,
  hourStep: 0.5,
  openWindowDays: 14,
  maxLinesPerDay: 6,
  maxCommentLength: 500,
  maxReopenReasonLength: 300,
  maxProjectCodeLength: 32,
  maxProjectNameLength: 120,
} as const;

export type ProjectType = 'chargeable' | 'non_chargeable';
export type TimesheetStatus = 'draft' | 'submitted' | 'approved' | 'rejected';

export interface Project {
  id: string; // sanitized project code
  code: string;
  name: string;
  client: string;
  type: ProjectType;
  active: boolean;
  partnerName: string;
  partnerEmail: string;
  managerName: string;
  managerEmail: string;
  updatedAt?: unknown;
}

export interface TimesheetLine {
  projectCode: string;
  projectName: string;
  clientName: string;
  type: ProjectType;
  hours: number;
}

export interface TimesheetEntry {
  id: string; // `${employeeId}_${date}`
  employeeId: string;
  employeeEmail: string;
  employeeName: string;
  managerEmail: string;
  date: string; // YYYY-MM-DD
  lines: TimesheetLine[];
  totalHours: number;
  status: TimesheetStatus;
  managerComment: string;
  reviewedBy: string;
  reopenedBy: string;
  reopenReason: string;
  submittedAt?: unknown;
  reviewedAt?: unknown;
  updatedAt?: unknown;
}

export type DayKind = 'working' | 'weekend' | 'holiday' | 'leave';

export interface DayInfo {
  date: string;
  kind: DayKind;
  label: string; // holiday name or leave category, if any
  halfDayLeave: boolean;
  inOpenWindow: boolean;
  future: boolean;
}

export interface PayrollRow {
  employeeId: string;
  employeeCode: string;
  name: string;
  designation: string;
  managerName: string;
  workingDays: number;
  holidays: number;
  weeklyOffs: number;
  daysPresent: number;
  leaveByCategory: Record<string, number>;
  totalLeave: number;
  pendingApproval: number;
  notSubmitted: number;
  totalHours: number;
  chargeableHours: number;
  nonChargeableHours: number;
  flags: string[];
}

export interface ProjectSummaryRow {
  code: string;
  name: string;
  client: string;
  type: ProjectType;
  partnerName: string;
  managerName: string;
  approvedHours: number;
  pendingHours: number;
  staffCount: number;
  entryDays: number;
}

export interface ProjectStaffRef {
  email: string;
  code: string;
  name: string;
}

export interface TimesheetDetailRow {
  date: string;
  employeeCode: string;
  employeeName: string;
  projectCode: string;
  projectName: string;
  client: string;
  type: ProjectType;
  hours: number;
  status: 'approved' | 'submitted';
}

export interface ProjectReport {
  projectRows: ProjectSummaryRow[];
  staff: ProjectStaffRef[];
  /** projectCode -> staff email -> approved hours */
  matrix: Record<string, Record<string, number>>;
  detail: TimesheetDetailRow[];
}
