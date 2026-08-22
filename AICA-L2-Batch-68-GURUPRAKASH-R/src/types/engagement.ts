import type { BaseEntity, ClientId, EngagementId, LifecycleStage, StatusTone } from "./common";

/* ------------------------------------------------------------------ */
/* Engagement status (entity specific — "Overdue" is never stored)      */
/* ------------------------------------------------------------------ */

export const ENGAGEMENT_STATUSES = [
  "Draft",
  "Planned",
  "In Progress",
  "Fieldwork Completed",
  "Reporting",
  "Action Tracking",
  "Closed",
  "On Hold",
  "Cancelled",
] as const;
export type EngagementStatus = (typeof ENGAGEMENT_STATUSES)[number];

/** Ordered forward workflow. On Hold / Cancelled sit outside this path. */
export const ENGAGEMENT_WORKFLOW: EngagementStatus[] = [
  "Draft",
  "Planned",
  "In Progress",
  "Fieldwork Completed",
  "Reporting",
  "Action Tracking",
  "Closed",
];

export const ENGAGEMENT_STATUS_TONES: Record<EngagementStatus, StatusTone> = {
  Draft: "neutral",
  Planned: "info",
  "In Progress": "info",
  "Fieldwork Completed": "info",
  Reporting: "warning",
  "Action Tracking": "warning",
  Closed: "success",
  "On Hold": "warning",
  Cancelled: "critical",
};

/** Status → lifecycle stage. On Hold / Cancelled retain the stored stage. */
export const STATUS_TO_STAGE: Record<EngagementStatus, LifecycleStage | null> = {
  Draft: "Planning",
  Planned: "Planning",
  "In Progress": "Fieldwork",
  "Fieldwork Completed": "Clarifications",
  Reporting: "Reporting",
  "Action Tracking": "Action Tracking",
  Closed: "Closure",
  "On Hold": null,
  Cancelled: null,
};

/** Statuses that count as an "active" (live) engagement for a client. */
export const ACTIVE_ENGAGEMENT_STATUSES: EngagementStatus[] = [
  "Planned",
  "In Progress",
  "Fieldwork Completed",
  "Reporting",
  "Action Tracking",
];

/** Statuses a manager may set through the "Correct status" action. */
export const CORRECTABLE_STATUSES: EngagementStatus[] = [
  "Draft",
  "Planned",
  "In Progress",
  "Fieldwork Completed",
  "Reporting",
  "Action Tracking",
];

/** Statuses from which an engagement may be placed on hold. */
export const HOLDABLE_STATUSES: EngagementStatus[] = [
  "Planned",
  "In Progress",
  "Fieldwork Completed",
  "Reporting",
  "Action Tracking",
];

/** Statuses from which an engagement may be cancelled. */
export const CANCELLABLE_STATUSES: EngagementStatus[] = [
  "Draft",
  ...HOLDABLE_STATUSES,
  "On Hold",
];

export function nextStatus(status: EngagementStatus): EngagementStatus | null {
  const index = ENGAGEMENT_WORKFLOW.indexOf(status);
  if (index < 0 || index === ENGAGEMENT_WORKFLOW.length - 1) return null;
  return ENGAGEMENT_WORKFLOW[index + 1];
}

export function resolveStage(
  status: EngagementStatus,
  storedStage: LifecycleStage,
): LifecycleStage {
  return STATUS_TO_STAGE[status] ?? storedStage;
}

/* ------------------------------------------------------------------ */
/* Master values                                                        */
/* ------------------------------------------------------------------ */

export const AUDIT_TYPES = [
  "Internal Audit",
  "Process Audit",
  "Compliance Audit",
  "Operational Audit",
  "Financial Controls Review",
  "Special Review",
  "Follow-up Audit",
] as const;
export type AuditType = (typeof AUDIT_TYPES)[number];

export const AUDIT_AREAS = [
  "Procurement",
  "Inventory",
  "Inventory and Job Work",
  "Job Work",
  "Production",
  "Sales and Receivables",
  "Finance and Accounts",
  "Fixed Assets",
  "GST",
  "TDS and Direct Tax",
  "HR and Payroll",
  "Information Technology",
  "Legal and Compliance",
  "Other",
] as const;
export type AuditArea = (typeof AUDIT_AREAS)[number];

/* ------------------------------------------------------------------ */
/* Engagement record                                                    */
/* ------------------------------------------------------------------ */

export interface EngagementRecord extends BaseEntity<EngagementId> {
  reference: EngagementId;
  clientId: ClientId;
  title: string;
  auditType: string;
  auditArea: string;
  auditPeriodFrom: string;
  auditPeriodTo: string;
  location: string;
  objective: string;
  engagementManager: string;
  auditTeam: string[];
  processOwner: string;
  auditCoordinator: string;
  plannedStartDate: string;
  plannedCompletionDate: string;
  reportingDueDate: string;
  status: EngagementStatus;
  lifecycleStage: LifecycleStage;
  priorStatus: EngagementStatus | null;
  priorStage: LifecycleStage | null;
  remarks: string;
  closureRemarks: string;
}

export type EngagementFormValues = Omit<
  EngagementRecord,
  | keyof BaseEntity<EngagementId>
  | "reference"
  | "status"
  | "lifecycleStage"
  | "priorStatus"
  | "priorStage"
  | "closureRemarks"
>;
