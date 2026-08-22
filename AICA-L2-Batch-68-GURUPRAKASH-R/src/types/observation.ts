/**
 * Stage 4 — Audit Observations.
 *
 * The observation carries three independent status axes, deliberately kept
 * apart: the drafting/reporting workflow status, the reporting decision, and
 * the derived implementation roll-up.
 */
import type {
  BaseEntity,
  ClarificationId,
  EngagementId,
  EvidenceId,
  ObservationId,
  ProcedureId,
  RequirementId,
  RiskRating,
  ScopeId,
  StatusTone,
} from "./common";

/* ------------------------------------------------------------------ */
/* Workflow status                                                     */
/* ------------------------------------------------------------------ */

export const OBSERVATION_STATUSES = [
  "Draft",
  "Under Auditor Review",
  "Issued for Management Response",
  "Awaiting Finalisation",
  "Finalised",
  "Included in Report",
  "Reported",
  "Dropped",
] as const;
export type ObservationStatus = (typeof OBSERVATION_STATUSES)[number];

export const OBSERVATION_STATUS_TONES: Record<ObservationStatus, StatusTone> = {
  Draft: "neutral",
  "Under Auditor Review": "info",
  "Issued for Management Response": "warning",
  "Awaiting Finalisation": "warning",
  Finalised: "success",
  "Included in Report": "success",
  Reported: "success",
  Dropped: "neutral",
};

/** States in which the observation wording may still be edited. */
export const OBSERVATION_EDITABLE_STATUSES: ObservationStatus[] = [
  "Draft",
  "Under Auditor Review",
  "Issued for Management Response",
  "Awaiting Finalisation",
];

export const OBSERVATION_PRE_FINAL_STATUSES: ObservationStatus[] = [
  "Draft",
  "Under Auditor Review",
  "Issued for Management Response",
  "Awaiting Finalisation",
];

/* ------------------------------------------------------------------ */
/* Reporting decision                                                  */
/* ------------------------------------------------------------------ */

export const REPORTING_DECISIONS = [
  "Include in Final Report",
  "Merge with Another Observation",
  "Advisory Point",
  "Verbal Discussion",
  "Working Papers Only",
  "Drop after Explanation",
] as const;
export type ReportingDecision = (typeof REPORTING_DECISIONS)[number];

/** Decisions that make an observation eligible for the final report. */
export const REPORTABLE_DECISIONS: ReportingDecision[] = [
  "Include in Final Report",
  "Advisory Point",
];

/* ------------------------------------------------------------------ */
/* Risk matrix                                                         */
/* ------------------------------------------------------------------ */

export const RATING_SCALE = ["Low", "Medium", "High"] as const;
export type RatingScale = (typeof RATING_SCALE)[number];

const RISK_MATRIX: Record<RatingScale, Record<RatingScale, RiskRating>> = {
  Low: { Low: "Low", Medium: "Low", High: "Medium" },
  Medium: { Low: "Low", Medium: "Medium", High: "High" },
  High: { Low: "Medium", Medium: "High", High: "High" },
};

/** Impact × Likelihood → suggested risk rating. Auditor judgement may override. */
export function calculateRisk(impact: RatingScale, likelihood: RatingScale): RiskRating {
  return RISK_MATRIX[impact][likelihood];
}

export const RISK_ORDER: Record<RiskRating, number> = { High: 0, Medium: 1, Low: 2 };

/* ------------------------------------------------------------------ */
/* Implementation roll-up (derived — never entered)                    */
/* ------------------------------------------------------------------ */

export const IMPLEMENTATION_ROLLUPS = [
  "No Action Created",
  "Awaiting Management Response",
  "Open",
  "Partly Implemented",
  "Implemented",
  "Risk Accepted",
  "Closed",
] as const;
export type ImplementationRollUp = (typeof IMPLEMENTATION_ROLLUPS)[number];

export const ROLLUP_TONES: Record<ImplementationRollUp, StatusTone> = {
  "No Action Created": "neutral",
  "Awaiting Management Response": "warning",
  Open: "info",
  "Partly Implemented": "warning",
  Implemented: "success",
  "Risk Accepted": "warning",
  Closed: "success",
};

/* ------------------------------------------------------------------ */
/* Entity                                                              */
/* ------------------------------------------------------------------ */

export interface ObservationRecord extends BaseEntity<ObservationId> {
  reference: ObservationId;
  engagementId: EngagementId;
  process: string;
  title: string;
  scopeId: ScopeId | null;
  procedureId: ProcedureId | null;
  requirementId: RequirementId | null;
  evidenceId: EvidenceId | null;
  clarificationId: ClarificationId | null;
  condition: string;
  criteria: string;
  rootCause: string;
  riskImplication: string;
  financialImpact: string;
  recommendation: string;
  supportingEvidence: string;
  impactRating: RatingScale | "";
  likelihoodRating: RatingScale | "";
  calculatedRiskRating: RiskRating | "";
  finalRiskRating: RiskRating | "";
  riskOverrideReason: string;
  status: ObservationStatus;
  reportingDecision: ReportingDecision | "";
  implementationRollUp: ImplementationRollUp;
  preparedBy: string;
  reviewedBy: string;
  reviewRemarks: string;
  finalisationRemarks: string;
  dropReason: string;
}

export type ObservationFormValues = Omit<
  ObservationRecord,
  | keyof BaseEntity<ObservationId>
  | "reference"
  | "status"
  | "calculatedRiskRating"
  | "implementationRollUp"
  | "reviewRemarks"
  | "finalisationRemarks"
  | "dropReason"
>;

/** Fields that must be present before an observation may be submitted for review. */
export function missingForReview(row: ObservationRecord): string[] {
  const gaps: string[] = [];
  if (!row.engagementId) gaps.push("Engagement");
  if (!row.process.trim()) gaps.push("Process");
  if (!row.title.trim()) gaps.push("Observation title");
  if (!row.condition.trim()) gaps.push("Condition");
  if (!row.riskImplication.trim()) gaps.push("Risk or implication");
  if (!row.recommendation.trim()) gaps.push("Recommendation");
  if (!row.impactRating) gaps.push("Impact rating");
  if (!row.likelihoodRating) gaps.push("Likelihood rating");
  if (!row.preparedBy.trim()) gaps.push("Prepared by");
  return gaps;
}

/** Additional fields required before finalisation. */
export function missingForFinalisation(row: ObservationRecord): string[] {
  const gaps = missingForReview(row);
  if (!row.criteria.trim()) gaps.push("Criteria");
  if (!row.rootCause.trim()) gaps.push("Root cause (or 'Root cause not established')");
  if (!row.finalRiskRating) gaps.push("Final risk rating");
  if (!row.reportingDecision) gaps.push("Reporting decision");
  if (!row.reviewedBy.trim()) gaps.push("Reviewed by");
  if (!row.reviewRemarks.trim()) gaps.push("Review remarks");
  return gaps;
}
