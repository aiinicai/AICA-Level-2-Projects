import type { UserRole } from "@/types/common";
import {
  ENGAGEMENT_WORKFLOW,
  nextStatus,
  type EngagementStatus,
} from "@/types/engagement";

/**
 * Front-end role gating only. This is presentation-level restriction for the
 * Stage 2 demonstration build — there is no authentication or server-side
 * enforcement behind it.
 */

export const ROLE_DISPLAY_NAME: Record<UserRole, string> = {
  Auditor: "A. Auditor",
  "Audit Manager": "M. Manager",
  "Auditee / Process Owner": "P. Process Owner",
};

export const isAuditee = (role: UserRole) => role === "Auditee / Process Owner";
export const isManager = (role: UserRole) => role === "Audit Manager";

/* ----------------------------- Clients ----------------------------- */

export const canCreateClient = (role: UserRole) => !isAuditee(role);
export const canEditClient = (role: UserRole) => !isAuditee(role);
export const canDeactivateClient = (role: UserRole) => !isAuditee(role);
export const canReactivateClient = (role: UserRole) => isManager(role);
export const canArchiveClient = (role: UserRole) => isManager(role);

/* --------------------------- Engagements --------------------------- */

export const canCreateEngagement = (role: UserRole) => !isAuditee(role);
export const canEditEngagement = (role: UserRole) => !isAuditee(role);
export const canHoldEngagement = (role: UserRole) => isManager(role);
export const canResumeEngagement = (role: UserRole) => isManager(role);
export const canCancelEngagement = (role: UserRole) => isManager(role);
export const canCloseEngagement = (role: UserRole) => isManager(role);
export const canReopenEngagement = (role: UserRole) => isManager(role);
export const canCorrectStatus = (role: UserRole) => isManager(role);

const REPORTING_INDEX = ENGAGEMENT_WORKFLOW.indexOf("Reporting");

/** Auditors may advance only as far as Reporting; beyond that is manager-only. */
export function canAdvanceEngagement(role: UserRole, status: EngagementStatus): boolean {
  if (isAuditee(role)) return false;
  const target = nextStatus(status);
  if (!target) return false;
  if (isManager(role)) return true;
  return ENGAGEMENT_WORKFLOW.indexOf(target) <= REPORTING_INDEX;
}

export function advanceBlockedReason(
  role: UserRole,
  status: EngagementStatus,
): string | null {
  const target = nextStatus(status);
  if (!target) return "No further forward transition is available from this status.";
  if (isAuditee(role)) return "Auditees may only view engagement records.";
  if (!isManager(role) && ENGAGEMENT_WORKFLOW.indexOf(target) > REPORTING_INDEX) {
    return `Moving to ${target} requires the Audit Manager role.`;
  }
  return null;
}

/* ------------------------- Stage 3 fieldwork ------------------------ */

/** Auditors and managers plan work; auditees may only view it. */
export const canManageScope = (role: UserRole) => !isAuditee(role);
export const canMarkScopeNotApplicable = (role: UserRole) => isManager(role);
export const canManageProcedure = (role: UserRole) => !isAuditee(role);
export const canReopenProcedure = (role: UserRole) => isManager(role);
export const canManageRequirement = (role: UserRole) => !isAuditee(role);
export const canReopenRequirement = (role: UserRole) => isManager(role);
/** Auditees supply evidence metadata; auditors and managers review it. */
export const canAddEvidence = (_role: UserRole) => true;
export const canReviewEvidence = (role: UserRole) => !isAuditee(role);
export const canManageClarification = (role: UserRole) => !isAuditee(role);
export const canRespondToClarification = (_role: UserRole) => true;
export const canConvertClarification = (role: UserRole) => !isAuditee(role);

/* --------------------- Stage 4 reporting & closure ------------------ */

/** Observations: auditors draft, managers review, issue and finalise. */
export const canManageObservation = (role: UserRole) => !isAuditee(role);
export const canReviewObservation = (role: UserRole) => isManager(role);
export const canIssueObservation = (role: UserRole) => isManager(role);
export const canFinaliseObservation = (role: UserRole) => isManager(role);
export const canDropObservation = (role: UserRole) => isManager(role);
export const canReopenObservation = (role: UserRole) => isManager(role);

/** Responses: the auditee records them; the audit team assesses them. */
export const canOpenResponse = (role: UserRole) => !isAuditee(role);
export const canRecordResponse = (_role: UserRole) => true;
export const canAssessResponse = (role: UserRole) => !isAuditee(role);
export const canAcceptResponse = (role: UserRole) => !isAuditee(role);

/** Actions: proposed by either side, agreed only by the audit team. */
export const canManageAction = (_role: UserRole) => true;
export const canAgreeAction = (role: UserRole) => !isAuditee(role);
export const canReviseTargetDate = (role: UserRole) => !isAuditee(role);
export const canEscalateAction = (role: UserRole) => isManager(role);

/** Closure: management reports progress, the audit team verifies it. */
export const canRecordClosureUpdate = (_role: UserRole) => true;
export const canVerifyClosure = (role: UserRole) => !isAuditee(role);
export const canReopenAction = (role: UserRole) => isManager(role);

/** Reporting: prepared by auditors, finalised only by the Audit Manager. */
export const canManageReport = (role: UserRole) => !isAuditee(role);
export const canReviewReport = (role: UserRole) => isManager(role);
export const canFinaliseReport = (role: UserRole) => isManager(role);

export const AUDITEE_VIEW_ONLY = "Auditees may view this record but cannot perform this action.";

