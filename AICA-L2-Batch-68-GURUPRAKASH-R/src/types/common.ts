/**
 * Common enums, ID types and metadata contracts shared by every AuditFlow module.
 * Full entity models are introduced in later stages.
 */

/* ------------------------------------------------------------------ */
/* Entity ID conventions                                               */
/* ------------------------------------------------------------------ */

export const ID_PREFIX = {
  client: "CLT",
  engagement: "ENG",
  scope: "SCP",
  procedure: "PRC",
  requirement: "REQ",
  evidence: "EVD",
  clarification: "CLR",
  observation: "OBS",
  managementResponse: "MGR",
  managementAction: "ACT",
  closureUpdate: "CLU",
  report: "RPT",
} as const;

export type EntityKind = keyof typeof ID_PREFIX;
export type IdPrefix = (typeof ID_PREFIX)[EntityKind];

/** Template-literal ID types, e.g. "CLT-0001". */
export type PrefixedId<P extends IdPrefix> = `${P}-${string}`;

export type ClientId = PrefixedId<"CLT">;
export type EngagementId = PrefixedId<"ENG">;
export type ScopeId = PrefixedId<"SCP">;
export type ProcedureId = PrefixedId<"PRC">;
export type RequirementId = PrefixedId<"REQ">;
export type EvidenceId = PrefixedId<"EVD">;
export type ClarificationId = PrefixedId<"CLR">;
export type ObservationId = PrefixedId<"OBS">;
export type ManagementResponseId = PrefixedId<"MGR">;
export type ManagementActionId = PrefixedId<"ACT">;
export type ClosureUpdateId = PrefixedId<"CLU">;
export type ReportId = PrefixedId<"RPT">;

export type EntityId =
  | ClientId
  | EngagementId
  | ScopeId
  | ProcedureId
  | RequirementId
  | EvidenceId
  | ClarificationId
  | ObservationId
  | ManagementResponseId
  | ManagementActionId
  | ClosureUpdateId
  | ReportId;

/** Formats a sequence number into the canonical 4-digit ID, e.g. formatId("client", 7) -> "CLT-0007". */
export function formatId<K extends EntityKind>(
  kind: K,
  sequence: number,
): `${(typeof ID_PREFIX)[K]}-${string}` {
  return `${ID_PREFIX[kind]}-${String(sequence).padStart(4, "0")}` as `${(typeof ID_PREFIX)[K]}-${string}`;
}

export function parseIdSequence(id: string): number | null {
  const match = /^[A-Z]{3}-(\d{4,})$/.exec(id);
  return match ? Number(match[1]) : null;
}

/* ------------------------------------------------------------------ */
/* Common metadata                                                     */
/* ------------------------------------------------------------------ */

export interface AuditMetadata {
  createdAt: string;
  createdBy: string;
  updatedAt: string;
  updatedBy: string;
  isActive: boolean;
}

export interface BaseEntity<TId extends string = string> extends AuditMetadata {
  id: TId;
}

/* ------------------------------------------------------------------ */
/* Shared enums                                                        */
/* ------------------------------------------------------------------ */

export const USER_ROLES = ["Auditor", "Audit Manager", "Auditee / Process Owner"] as const;
export type UserRole = (typeof USER_ROLES)[number];

export const LIFECYCLE_STAGES = [
  "Planning",
  "Fieldwork",
  "Clarifications",
  "Reporting",
  "Action Tracking",
  "Closure",
] as const;
export type LifecycleStage = (typeof LIFECYCLE_STAGES)[number];

export const RISK_RATINGS = ["High", "Medium", "Low"] as const;
export type RiskRating = (typeof RISK_RATINGS)[number];

export const WORKFLOW_STATUSES = [
  "Draft",
  "Pending",
  "In Progress",
  "Submitted",
  "Under Review",
  "Clarification Raised",
  "Accepted",
  "Rejected",
  "Overdue",
  "Closed",
] as const;
export type WorkflowStatus = (typeof WORKFLOW_STATUSES)[number];

export type StatusTone = "neutral" | "info" | "success" | "warning" | "critical";

/* ------------------------------------------------------------------ */
/* Generic list/query contracts used by the service layer              */
/* ------------------------------------------------------------------ */

export interface ListQuery {
  search?: string;
  page?: number;
  pageSize?: number;
  sortBy?: string;
  sortDir?: "asc" | "desc";
  filters?: Record<string, string | string[] | undefined>;
}

export interface ListResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ServiceError {
  code: string;
  message: string;
}
