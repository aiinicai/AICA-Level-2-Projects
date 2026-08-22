/**
 * Stage 4 — Management Responses, Management Actions, Closure Updates and
 * the Final Report. All four sit downstream of an Observation.
 */
import type {
  BaseEntity,
  ClosureUpdateId,
  EngagementId,
  ManagementActionId,
  ManagementResponseId,
  ObservationId,
  ReportId,
  StatusTone,
} from "./common";

/* ------------------------------------------------------------------ */
/* Management Response                                                 */
/* ------------------------------------------------------------------ */

export const MANAGEMENT_ACCEPTANCES = [
  "Accepted",
  "Partially Accepted",
  "Not Accepted",
  "Under Discussion",
] as const;
export type ManagementAcceptance = (typeof MANAGEMENT_ACCEPTANCES)[number];

export const ACCEPTANCE_TONES: Record<ManagementAcceptance, StatusTone> = {
  Accepted: "success",
  "Partially Accepted": "warning",
  "Not Accepted": "critical",
  "Under Discussion": "info",
};

export const RESPONSE_STATUSES = [
  "Awaiting Response",
  "Response Received",
  "Revision Requested",
  "Accepted by Auditor",
] as const;
export type ResponseStatus = (typeof RESPONSE_STATUSES)[number];

export const RESPONSE_STATUS_TONES: Record<ResponseStatus, StatusTone> = {
  "Awaiting Response": "neutral",
  "Response Received": "info",
  "Revision Requested": "warning",
  "Accepted by Auditor": "success",
};

/** Append-only revision history kept inside the response record. */
export interface ResponseVersion {
  version: number;
  managementResponse: string;
  respondent: string;
  responseDate: string;
  managementAcceptance: ManagementAcceptance | "";
  recordedAt: string;
  recordedBy: string;
}

export interface ManagementResponseRecord extends BaseEntity<ManagementResponseId> {
  reference: ManagementResponseId;
  observationId: ObservationId;
  managementAcceptance: ManagementAcceptance | "";
  managementResponse: string;
  causeAcknowledged: string;
  proposedApproach: string;
  managementRemarks: string;
  respondent: string;
  respondentDesignation: string;
  responseDate: string;
  auditorAssessment: string;
  status: ResponseStatus;
  version: number;
  history: ResponseVersion[];
}

/* ------------------------------------------------------------------ */
/* Management Action                                                   */
/* ------------------------------------------------------------------ */

export const ACTION_TYPES = [
  "Corrective",
  "Preventive",
  "Compensating Control",
  "Process Improvement",
] as const;
export type ActionType = (typeof ACTION_TYPES)[number];

export const ACTION_PRIORITIES = ["Low", "Medium", "High", "Critical"] as const;
export type ActionPriority = (typeof ACTION_PRIORITIES)[number];

export const ACTION_PRIORITY_TONES: Record<ActionPriority, StatusTone> = {
  Low: "neutral",
  Medium: "info",
  High: "warning",
  Critical: "critical",
};

export const AGREEMENT_STATUSES = [
  "Draft",
  "Proposed by Management",
  "Revision Requested",
  "Agreed by Auditor",
  "Rejected",
] as const;
export type AgreementStatus = (typeof AGREEMENT_STATUSES)[number];

export const AGREEMENT_TONES: Record<AgreementStatus, StatusTone> = {
  Draft: "neutral",
  "Proposed by Management": "info",
  "Revision Requested": "warning",
  "Agreed by Auditor": "success",
  Rejected: "critical",
};

export const IMPLEMENTATION_STATUSES = [
  "Pending",
  "Update Received",
  "Partly Implemented",
  "Implemented",
  "Risk Accepted",
  "Closed",
] as const;
export type ImplementationStatus = (typeof IMPLEMENTATION_STATUSES)[number];

export const IMPLEMENTATION_TONES: Record<ImplementationStatus, StatusTone> = {
  Pending: "neutral",
  "Update Received": "info",
  "Partly Implemented": "warning",
  Implemented: "success",
  "Risk Accepted": "warning",
  Closed: "success",
};

export type DueStatus = "Not Due" | "Due Soon" | "Overdue" | "—";

export const DUE_TONES: Record<DueStatus, StatusTone> = {
  "Not Due": "neutral",
  "Due Soon": "warning",
  Overdue: "critical",
  "—": "neutral",
};

export const DUE_SOON_DAYS = 7;

/** Derived badge from the effective target date. Never stored. */
export function dueStatusFor(
  originalTargetDate: string,
  revisedTargetDate: string,
  implementationStatus: ImplementationStatus,
  today = new Date(),
): DueStatus {
  if (implementationStatus === "Closed" || implementationStatus === "Risk Accepted") return "Not Due";
  const target = revisedTargetDate || originalTargetDate;
  if (!target) return "—";
  const days = Math.floor(
    (new Date(`${target}T00:00:00Z`).getTime() -
      new Date(today.toISOString().slice(0, 10) + "T00:00:00Z").getTime()) /
      86_400_000,
  );
  if (days < 0) return "Overdue";
  if (days <= DUE_SOON_DAYS) return "Due Soon";
  return "Not Due";
}

export interface ManagementActionRecord extends BaseEntity<ManagementActionId> {
  reference: ManagementActionId;
  observationId: ObservationId;
  title: string;
  description: string;
  actionType: ActionType;
  actionOwner: string;
  ownerDesignation: string;
  department: string;
  originalTargetDate: string;
  revisedTargetDate: string;
  revisedDateReason: string;
  priority: ActionPriority;
  auditorAssessment: string;
  agreementStatus: AgreementStatus;
  implementationStatus: ImplementationStatus;
  escalated: boolean;
  escalationDate: string;
  escalationRemarks: string;
}

/* ------------------------------------------------------------------ */
/* Closure Update (append-only)                                        */
/* ------------------------------------------------------------------ */

export interface ClosureEvidenceMeta {
  fileName: string;
  submissionDate: string;
  submittedBy: string;
  remarks: string;
}

export interface ClosureUpdateRecord extends BaseEntity<ClosureUpdateId> {
  reference: ClosureUpdateId;
  actionId: ManagementActionId;
  updateDate: string;
  updatedByPerson: string;
  managementUpdate: string;
  closureEvidence: ClosureEvidenceMeta | null;
  auditorVerification: string;
  auditorVerificationDate: string;
  implementationStatus: ImplementationStatus;
  closureConclusion: string;
  reopenReason: string;
  riskAcceptanceNote: string;
  escalationNote: string;
}

/* ------------------------------------------------------------------ */
/* Report                                                              */
/* ------------------------------------------------------------------ */

export const REPORT_STATUSES = ["Draft", "Under Review", "Finalised"] as const;
export type ReportStatus = (typeof REPORT_STATUSES)[number];

export const REPORT_STATUS_TONES: Record<ReportStatus, StatusTone> = {
  Draft: "neutral",
  "Under Review": "info",
  Finalised: "success",
};

export interface ReportRecord extends BaseEntity<ReportId> {
  reference: ReportId;
  engagementId: EngagementId;
  title: string;
  reportPeriod: string;
  addressee: string;
  issueDate: string;
  executiveSummary: string;
  overallConclusion: string;
  status: ReportStatus;
  /** Included observations, held in presentation order. */
  observationIds: ObservationId[];
  preparedBy: string;
  reviewedBy: string;
  approvedBy: string;
  /** Audit Manager justification for reporting without an accepted response. */
  unacceptedResponseReason: string;
}
