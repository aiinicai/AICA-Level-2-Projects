/**
 * Stage 3 — planning and fieldwork entities.
 *
 * Scope → Procedure → Requirement → Evidence, plus Clarifications which may be
 * attached at any level. Kept in one module because the five entities share the
 * same lifecycle vocabulary and are always used together.
 */
import type {
  BaseEntity,
  ClarificationId,
  EngagementId,
  EvidenceId,
  ObservationId,
  ProcedureId,
  RequirementId,
  ScopeId,
  StatusTone,
} from "./common";

/* ------------------------------------------------------------------ */
/* Scope                                                               */
/* ------------------------------------------------------------------ */

export const SCOPE_STATUSES = ["Draft", "Active", "Completed", "Not Applicable"] as const;
export type ScopeStatus = (typeof SCOPE_STATUSES)[number];

export const SCOPE_STATUS_TONES: Record<ScopeStatus, StatusTone> = {
  Draft: "neutral",
  Active: "info",
  Completed: "success",
  "Not Applicable": "neutral",
};

export interface ScopeRecord extends BaseEntity<ScopeId> {
  reference: ScopeId;
  engagementId: EngagementId;
  process: string;
  subProcess: string;
  objective: string;
  inclusion: string;
  exclusion: string;
  keyRisk: string;
  expectedControl: string;
  applicablePolicy: string;
  assignedAuditor: string;
  status: ScopeStatus;
  remarks: string;
}

export type ScopeFormValues = Omit<
  ScopeRecord,
  keyof BaseEntity<ScopeId> | "reference" | "status"
>;

/* ------------------------------------------------------------------ */
/* Procedure                                                           */
/* ------------------------------------------------------------------ */

export const PROCEDURE_STATUSES = [
  "Not Started",
  "In Progress",
  "Evidence Awaited",
  "Completed",
  "Exception Noted",
  "Not Applicable",
] as const;
export type ProcedureStatus = (typeof PROCEDURE_STATUSES)[number];

export const PROCEDURE_STATUS_TONES: Record<ProcedureStatus, StatusTone> = {
  "Not Started": "neutral",
  "In Progress": "info",
  "Evidence Awaited": "warning",
  Completed: "success",
  "Exception Noted": "critical",
  "Not Applicable": "neutral",
};

/** Statuses in which the test conclusion becomes editable. */
export const CONCLUSION_STATUSES: ProcedureStatus[] = [
  "Completed",
  "Exception Noted",
  "Not Applicable",
];

export const PROCEDURE_FINAL_STATUSES: ProcedureStatus[] = [
  "Completed",
  "Exception Noted",
  "Not Applicable",
];

/** Permitted forward / lateral transitions (Not Applicable and reopen handled separately). */
export const PROCEDURE_TRANSITIONS: Record<ProcedureStatus, ProcedureStatus[]> = {
  "Not Started": ["In Progress"],
  "In Progress": ["Evidence Awaited", "Completed", "Exception Noted"],
  "Evidence Awaited": ["In Progress", "Completed", "Exception Noted"],
  Completed: [],
  "Exception Noted": [],
  "Not Applicable": [],
};

export const SAMPLE_METHODS = [
  "Random",
  "Judgemental",
  "Systematic",
  "Stratified",
  "Full Population",
  "High Value Items",
] as const;

export interface ProcedureRecord extends BaseEntity<ProcedureId> {
  reference: ProcedureId;
  scopeId: ScopeId;
  riskAddressed: string;
  controlObjective: string;
  description: string;
  population: string;
  sampleSize: string;
  sampleMethod: string;
  assignedAuditor: string;
  targetDate: string;
  status: ProcedureStatus;
  conclusion: string;
  remarks: string;
}

export type ProcedureFormValues = Omit<
  ProcedureRecord,
  keyof BaseEntity<ProcedureId> | "reference" | "status"
>;

/* ------------------------------------------------------------------ */
/* Requirement                                                         */
/* ------------------------------------------------------------------ */

export const REQUIREMENT_PRIORITIES = ["Low", "Medium", "High", "Critical"] as const;
export type RequirementPriority = (typeof REQUIREMENT_PRIORITIES)[number];

export const PRIORITY_TONES: Record<RequirementPriority, StatusTone> = {
  Low: "neutral",
  Medium: "info",
  High: "warning",
  Critical: "critical",
};

export const SUBMISSION_STATUSES = [
  "Draft",
  "Issued",
  "Partially Received",
  "Received",
  "Not Applicable",
] as const;
export type SubmissionStatus = (typeof SUBMISSION_STATUSES)[number];

export const SUBMISSION_TONES: Record<SubmissionStatus, StatusTone> = {
  Draft: "neutral",
  Issued: "info",
  "Partially Received": "warning",
  Received: "success",
  "Not Applicable": "neutral",
};

export const REVIEW_STATUSES = [
  "Not Reviewed",
  "Under Review",
  "Additional Data Required",
  "Reviewed",
  "Closed",
] as const;
export type ReviewStatus = (typeof REVIEW_STATUSES)[number];

export const REVIEW_TONES: Record<ReviewStatus, StatusTone> = {
  "Not Reviewed": "neutral",
  "Under Review": "info",
  "Additional Data Required": "warning",
  Reviewed: "success",
  Closed: "success",
};

const SUBMISSION_PROGRESS: Record<SubmissionStatus, number> = {
  Draft: 0,
  Issued: 10,
  "Partially Received": 40,
  Received: 60,
  "Not Applicable": 100,
};

const REVIEW_PROGRESS: Record<ReviewStatus, number> = {
  "Not Reviewed": 0,
  "Under Review": 75,
  "Additional Data Required": 65,
  Reviewed: 90,
  Closed: 100,
};

/** Completion is derived, never entered: the highest meaningful stage wins. */
export function completionFor(submission: SubmissionStatus, review: ReviewStatus): number {
  return Math.max(SUBMISSION_PROGRESS[submission], REVIEW_PROGRESS[review]);
}

export const DEPARTMENTS = [
  "Stores",
  "Procurement",
  "Production",
  "Finance and Accounts",
  "Commercial",
  "Quality",
  "Human Resources",
  "Information Technology",
  "Legal and Secretarial",
] as const;

export const DOCUMENT_FORMATS = [
  "Excel",
  "PDF",
  "Scanned copy",
  "ERP extract",
  "Signed hard copy",
  "Any",
] as const;

export interface RequirementRecord extends BaseEntity<RequirementId> {
  reference: RequirementId;
  engagementId: EngagementId;
  procedureId: ProcedureId;
  department: string;
  description: string;
  formatRequired: string;
  periodCovered: string;
  responsiblePerson: string;
  dateIssued: string;
  dueDate: string;
  priority: RequirementPriority;
  submissionStatus: SubmissionStatus;
  reviewStatus: ReviewStatus;
  completionPercentage: number;
  auditorRemarks: string;
  auditeeRemarks: string;
  notApplicableReason: string;
}

export type RequirementFormValues = Omit<
  RequirementRecord,
  | keyof BaseEntity<RequirementId>
  | "reference"
  | "dateIssued"
  | "submissionStatus"
  | "reviewStatus"
  | "completionPercentage"
  | "notApplicableReason"
>;

/* ------------------------------------------------------------------ */
/* Evidence                                                            */
/* ------------------------------------------------------------------ */

export const EVIDENCE_REVIEW_STATUSES = [
  "Revision Pending",
  "Awaiting Review",
  "Incomplete",
  "Incorrect Format",
  "Additional Data Required",
  "Satisfactory",
  "Accepted",
] as const;
export type EvidenceReviewStatus = (typeof EVIDENCE_REVIEW_STATUSES)[number];

export const EVIDENCE_REVIEW_TONES: Record<EvidenceReviewStatus, StatusTone> = {
  "Revision Pending": "warning",
  "Awaiting Review": "neutral",
  Incomplete: "warning",
  "Incorrect Format": "warning",
  "Additional Data Required": "warning",
  Satisfactory: "info",
  Accepted: "success",
};

/** A reserved next version that the auditee has not yet submitted. */
export function isPendingVersion(row: { reviewStatus: EvidenceReviewStatus }): boolean {
  return row.reviewStatus === "Revision Pending";
}


export const AUDIT_RESULTS = [
  "Not Assessed",
  "No Exception",
  "Exception Identified",
  "Further Testing Required",
] as const;
export type AuditResult = (typeof AUDIT_RESULTS)[number];

export const AUDIT_RESULT_TONES: Record<AuditResult, StatusTone> = {
  "Not Assessed": "neutral",
  "No Exception": "success",
  "Exception Identified": "critical",
  "Further Testing Required": "warning",
};

export const DOCUMENT_CATEGORIES = [
  "Register",
  "Reconciliation",
  "Ledger / ERP extract",
  "Policy or SOP",
  "Approval record",
  "Contract or agreement",
  "Correspondence",
  "Report",
  "Other",
] as const;

export const FILE_TYPES = ["XLSX", "PDF", "DOCX", "CSV", "Image", "ZIP"] as const;

export interface EvidenceRecord extends BaseEntity<EvidenceId> {
  reference: EvidenceId;
  requirementId: RequirementId;
  fileName: string;
  documentCategory: string;
  fileType: string;
  fileSize: string;
  version: number;
  /** Reference of the evidence record this version supersedes, if any. */
  supersedes: EvidenceId | null;
  submittedBy: string;
  submissionDate: string;
  auditeeRemarks: string;
  assignedReviewer: string;
  reviewStatus: EvidenceReviewStatus;
  auditResult: AuditResult;
  reviewRemarks: string;
  reviewedDate: string;
}

export type EvidenceFormValues = Omit<
  EvidenceRecord,
  | keyof BaseEntity<EvidenceId>
  | "reference"
  | "version"
  | "supersedes"
  | "reviewStatus"
  | "auditResult"
  | "reviewRemarks"
  | "reviewedDate"
>;

/* ------------------------------------------------------------------ */
/* Clarification                                                       */
/* ------------------------------------------------------------------ */

export const CLARIFICATION_STATUSES = [
  "Draft",
  "Open",
  "Response Received",
  "Further Clarification Required",
  "Resolved",
  "Converted to Observation",
  "Closed Without Observation",
] as const;
export type ClarificationStatus = (typeof CLARIFICATION_STATUSES)[number];

export const CLARIFICATION_TONES: Record<ClarificationStatus, StatusTone> = {
  Draft: "neutral",
  Open: "info",
  "Response Received": "info",
  "Further Clarification Required": "warning",
  Resolved: "success",
  "Converted to Observation": "critical",
  "Closed Without Observation": "success",
};

export const CLARIFICATION_FINAL_STATUSES: ClarificationStatus[] = [
  "Converted to Observation",
  "Closed Without Observation",
];

export interface ClarificationRecord extends BaseEntity<ClarificationId> {
  reference: ClarificationId;
  engagementId: EngagementId;
  scopeId: ScopeId | null;
  procedureId: ProcedureId | null;
  requirementId: RequirementId | null;
  evidenceId: EvidenceId | null;
  subject: string;
  clarificationRaised: string;
  raisedBy: string;
  dateRaised: string;
  responseDueDate: string;
  respondent: string;
  auditeeResponse: string;
  responseDate: string;
  auditorConclusion: string;
  status: ClarificationStatus;
  /** Reserved observation reference once converted — retained permanently. */
  observationId: ObservationId | null;
}

export type ClarificationFormValues = Omit<
  ClarificationRecord,
  | keyof BaseEntity<ClarificationId>
  | "reference"
  | "status"
  | "observationId"
  | "auditeeResponse"
  | "responseDate"
  | "auditorConclusion"
>;

/* ------------------------------------------------------------------ */
/* Observation (full entity lives in ./observation)                    */
/* ------------------------------------------------------------------ */

/** Retained alias: Stage 3 created reserved observation drafts. */
export type { ObservationRecord as ObservationStub } from "./observation";

