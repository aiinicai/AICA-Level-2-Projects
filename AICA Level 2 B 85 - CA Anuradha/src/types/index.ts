export type Role = 'department_submitter' | 'finance_controller' | 'management' | 'admin';

export type Department = 'HR' | 'Admin' | 'IT' | 'Finance';

export type Priority = 'Critical' | 'Important' | 'Optional';

export type SubmissionStatus = 'Not Started' | 'Draft' | 'Submitted' | 'Locked' | 'Approved' | 'Rejected' | 'Changes Requested';

export type MonthStatus = 'Open' | 'Ready for Approval' | 'Approved' | 'Closed';

export interface User {
  id: string;
  name: string;
  email: string;
  role: Role;
  department?: Department;
  title: string;
  avatar?: string;
}

export interface LineItem {
  id: string;
  submissionId: string;
  department: Department;
  category: string;
  description: string;
  amountInr: number;
  priority: Priority;
  notes: string;
  approvedAmountInr?: number;
  status?: 'pending' | 'approved' | 'adjusted' | 'rejected';
  adjustmentNote?: string;
}

export interface DepartmentSubmission {
  id: string;
  monthId: string;
  department: Department;
  status: SubmissionStatus;
  submittedBy?: string;
  submittedAt?: string; // ISO string
  lastUpdatedBy?: string;
  lastUpdatedAt?: string;
  recalledAt?: string;
  recalledBy?: string;
  comments?: string;
  lineItems: LineItem[];
}

export interface ApprovalRecord {
  id: string;
  monthId: string;
  approverId: string;
  approverName: string;
  approverRole: string;
  decision: 'Approved' | 'Approved with Adjustments' | 'Rejected' | 'Changes Requested';
  comments: string;
  decidedAt: string; // ISO string
  totalRequestedInr: number;
  totalApprovedInr: number;
  totalRequestedAud: number;
  totalApprovedAud: number;
  exchangeRate: number;
  departmentDecisions?: {
    department: Department;
    requestedInr: number;
    approvedInr: number;
    notes?: string;
  }[];
}

export interface MonthCycle {
  id: string; // e.g. '2026-10'
  label: string; // e.g. 'October 2026'
  status: MonthStatus;
  exchangeRate: number; // 1 INR to AUD (e.g. 0.0182)
  rateSource: string; // e.g. 'RBI reference rate as of 24/09/2026'
  rateLockedAt?: string;
  rateLockedBy?: string;
  submissionDeadline: string; // e.g. '2026-09-25'
  consolidationNotes?: string;
  controllerMarkedReadyAt?: string;
  controllerMarkedReadyBy?: string;
  approvalRecord?: ApprovalRecord;
  createdAt: string;
}

export interface AuditLogEntry {
  id: string;
  timestamp: string; // ISO string
  userId: string;
  userName: string;
  userRole: string;
  action: string;
  details: string;
  monthId: string;
  department?: Department;
}

export interface DepartmentCategory {
  id: string;
  department: Department;
  name: string;
  description: string;
  isDefault?: boolean;
}
