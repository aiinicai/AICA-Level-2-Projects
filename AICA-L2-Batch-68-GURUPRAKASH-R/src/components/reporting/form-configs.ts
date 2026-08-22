import type { PromptField, PromptOption, PromptValues } from "@/components/common/prompt-dialog";
import type { ObservationFormValues, RatingScale } from "@/types/observation";
import { calculateRisk, RATING_SCALE, REPORTING_DECISIONS } from "@/types/observation";
import type { ActionFormValues } from "@/services/management-action.service";
import type { RecordResponseInput } from "@/services/management-response.service";
import type { ClosureUpdateInput, VerificationInput } from "@/services/closure-update.service";
import type { ReportFormValues } from "@/services/report.service";
import {
  ACTION_PRIORITIES,
  ACTION_TYPES,
  MANAGEMENT_ACCEPTANCES,
  type ActionPriority,
  type ActionType,
  type ManagementAcceptance,
} from "@/types/reporting";
import type { EngagementId, ObservationId } from "@/types/common";

/**
 * Declarative field schemas for the Stage 4 registers, mirroring the Stage 3
 * fieldwork configuration so every module shares one dialog implementation.
 */

const options = (values: readonly string[]): PromptOption[] =>
  values.map((value) => ({ value, label: value }));

export const RATING_OPTIONS = options(RATING_SCALE);

export interface ObservationFieldContext {
  engagements: PromptOption[];
  scopes: { id: string; reference: string; process: string; engagementId: string }[];
  procedures: { id: string; reference: string; description: string; engagementId: string }[];
  requirements: { id: string; reference: string; description: string; engagementId: string }[];
  clarifications: { id: string; reference: string; subject: string; engagementId: string }[];
}

const forEngagement = <T extends { engagementId: string }>(rows: T[], engagementId: string) =>
  rows.filter((row) => row.engagementId === engagementId);

export function observationFields(
  context: ObservationFieldContext,
  lockEngagement: boolean,
): PromptField[] {
  return [
    {
      name: "engagementId",
      label: "Engagement",
      type: "select",
      required: true,
      readOnly: lockEngagement,
      options: context.engagements,
      clears: ["scopeId", "procedureId", "requirementId", "clarificationId"],
    },
    { name: "process", label: "Process / area", required: true },
    { name: "title", label: "Observation title", required: true, full: true, minLength: 5 },
    {
      name: "scopeId",
      label: "Scope item",
      type: "select",
      options: (values) =>
        forEngagement(context.scopes, values.engagementId ?? "").map((row) => ({
          value: row.id,
          label: `${row.reference} · ${row.process}`,
        })),
    },
    {
      name: "procedureId",
      label: "Procedure",
      type: "select",
      options: (values) =>
        forEngagement(context.procedures, values.engagementId ?? "").map((row) => ({
          value: row.id,
          label: `${row.reference} · ${row.description}`,
        })),
    },
    {
      name: "requirementId",
      label: "Data requirement",
      type: "select",
      options: (values) =>
        forEngagement(context.requirements, values.engagementId ?? "").map((row) => ({
          value: row.id,
          label: `${row.reference} · ${row.description}`,
        })),
    },
    {
      name: "clarificationId",
      label: "Source clarification",
      type: "select",
      options: (values) =>
        forEngagement(context.clarifications, values.engagementId ?? "").map((row) => ({
          value: row.id,
          label: `${row.reference} · ${row.subject}`,
        })),
    },
    { name: "condition", label: "Condition (what was found)", type: "textarea", rows: 4, required: true, full: true },
    { name: "criteria", label: "Criteria (policy, control or standard)", type: "textarea", rows: 3, full: true },
    { name: "rootCause", label: "Root cause", type: "textarea", rows: 3, full: true },
    { name: "riskImplication", label: "Risk / implication", type: "textarea", rows: 3, required: true, full: true },
    { name: "financialImpact", label: "Financial impact (if quantified)" },
    { name: "supportingEvidence", label: "Supporting evidence reference" },
    { name: "recommendation", label: "Recommendation", type: "textarea", rows: 3, required: true, full: true },
    { name: "impactRating", label: "Impact", type: "select", required: true, options: RATING_OPTIONS },
    { name: "likelihoodRating", label: "Likelihood", type: "select", required: true, options: RATING_OPTIONS },
    {
      name: "finalRiskRating",
      label: "Final risk rating",
      type: "select",
      options: options(["High", "Medium", "Low"]),
      hint: "Leave blank to accept the calculated rating.",
    },
    {
      name: "riskOverrideReason",
      label: "Risk override reason",
      type: "textarea",
      rows: 2,
      required: true,
      full: true,
      visible: (values) => {
        const impact = values.impactRating as RatingScale | "";
        const likelihood = values.likelihoodRating as RatingScale | "";
        if (!impact || !likelihood || !values.finalRiskRating) return false;
        return calculateRisk(impact, likelihood) !== values.finalRiskRating;
      },
    },
    {
      name: "reportingDecision",
      label: "Reporting decision",
      type: "select",
      options: options(REPORTING_DECISIONS),
    },
    { name: "preparedBy", label: "Prepared by", required: true },
    { name: "reviewedBy", label: "Reviewed by" },
  ];
}

export function toObservationValues(values: PromptValues): ObservationFormValues {
  return {
    engagementId: values.engagementId as EngagementId,
    process: values.process ?? "",
    title: values.title ?? "",
    scopeId: (values.scopeId || null) as ObservationFormValues["scopeId"],
    procedureId: (values.procedureId || null) as ObservationFormValues["procedureId"],
    requirementId: (values.requirementId || null) as ObservationFormValues["requirementId"],
    evidenceId: null,
    clarificationId: (values.clarificationId || null) as ObservationFormValues["clarificationId"],
    condition: values.condition ?? "",
    criteria: values.criteria ?? "",
    rootCause: values.rootCause ?? "",
    riskImplication: values.riskImplication ?? "",
    financialImpact: values.financialImpact ?? "",
    recommendation: values.recommendation ?? "",
    supportingEvidence: values.supportingEvidence ?? "",
    impactRating: (values.impactRating || "") as ObservationFormValues["impactRating"],
    likelihoodRating: (values.likelihoodRating || "") as ObservationFormValues["likelihoodRating"],
    finalRiskRating: (values.finalRiskRating || "") as ObservationFormValues["finalRiskRating"],
    riskOverrideReason: values.riskOverrideReason ?? "",
    reportingDecision: (values.reportingDecision || "") as ObservationFormValues["reportingDecision"],
    preparedBy: values.preparedBy ?? "",
    reviewedBy: values.reviewedBy ?? "",
  };
}

export function observationToPromptValues(row: Record<string, unknown>): PromptValues {
  const result: PromptValues = {};
  for (const [key, value] of Object.entries(row)) {
    if (value === null || value === undefined) result[key] = "";
    else if (typeof value === "string" || typeof value === "number") result[key] = String(value);
  }
  return result;
}

/* ------------------------- Management response ---------------------- */

export const responseFields: PromptField[] = [
  { name: "respondent", label: "Respondent", required: true },
  { name: "respondentDesignation", label: "Designation" },
  { name: "responseDate", label: "Response date", type: "date", required: true },
  {
    name: "managementAcceptance",
    label: "Management position",
    type: "select",
    required: true,
    options: options(MANAGEMENT_ACCEPTANCES),
  },
  {
    name: "managementResponse",
    label: "Management response",
    type: "textarea",
    rows: 5,
    required: true,
    full: true,
    minLength: 10,
  },
  { name: "causeAcknowledged", label: "Cause acknowledged", type: "textarea", rows: 2, full: true },
  { name: "proposedApproach", label: "Proposed remediation approach", type: "textarea", rows: 3, full: true },
  { name: "managementRemarks", label: "Other remarks", type: "textarea", rows: 2, full: true },
];

export function toResponseInput(values: PromptValues): RecordResponseInput {
  return {
    managementResponse: values.managementResponse ?? "",
    respondent: values.respondent ?? "",
    respondentDesignation: values.respondentDesignation ?? "",
    responseDate: values.responseDate ?? "",
    managementAcceptance: (values.managementAcceptance || "Under Discussion") as ManagementAcceptance,
    causeAcknowledged: values.causeAcknowledged ?? "",
    proposedApproach: values.proposedApproach ?? "",
    managementRemarks: values.managementRemarks ?? "",
  };
}

/* -------------------------- Management action ----------------------- */

export function actionFields(observations: PromptOption[], lockObservation: boolean): PromptField[] {
  return [
    {
      name: "observationId",
      label: "Observation",
      type: "select",
      required: true,
      readOnly: lockObservation,
      options: observations,
    },
    { name: "title", label: "Action title", required: true, minLength: 5 },
    { name: "description", label: "Action description", type: "textarea", rows: 4, required: true, full: true },
    { name: "actionType", label: "Action type", type: "select", required: true, options: options(ACTION_TYPES) },
    { name: "priority", label: "Priority", type: "select", required: true, options: options(ACTION_PRIORITIES) },
    { name: "actionOwner", label: "Action owner", required: true },
    { name: "ownerDesignation", label: "Owner designation" },
    { name: "department", label: "Department", required: true },
    { name: "originalTargetDate", label: "Target date", type: "date", required: true },
  ];
}

export function toActionValues(values: PromptValues): ActionFormValues {
  return {
    observationId: values.observationId ?? "",
    title: values.title ?? "",
    description: values.description ?? "",
    actionType: (values.actionType || "Corrective") as ActionType,
    actionOwner: values.actionOwner ?? "",
    ownerDesignation: values.ownerDesignation ?? "",
    department: values.department ?? "",
    originalTargetDate: values.originalTargetDate ?? "",
    priority: (values.priority || "Medium") as ActionPriority,
  };
}

/* --------------------------- Closure update ------------------------- */

export const closureUpdateFields: PromptField[] = [
  { name: "updateDate", label: "Update date", type: "date", required: true },
  { name: "updatedByPerson", label: "Reported by", required: true },
  {
    name: "implementationStatus",
    label: "Implementation status",
    type: "select",
    required: true,
    options: options(["Update Received", "Partly Implemented", "Implemented"]),
  },
  {
    name: "managementUpdate",
    label: "Progress update",
    type: "textarea",
    rows: 4,
    required: true,
    full: true,
    minLength: 10,
  },
  { name: "evidenceFileName", label: "Closure evidence (file name)" },
  { name: "evidenceRemarks", label: "Evidence remarks" },
];

export function toClosureUpdateInput(values: PromptValues, submittedBy: string): ClosureUpdateInput {
  return {
    updateDate: values.updateDate ?? "",
    updatedByPerson: values.updatedByPerson ?? "",
    managementUpdate: values.managementUpdate ?? "",
    implementationStatus: (values.implementationStatus ||
      "Update Received") as ClosureUpdateInput["implementationStatus"],
    closureEvidence: values.evidenceFileName
      ? {
          fileName: values.evidenceFileName,
          submissionDate: values.updateDate ?? "",
          submittedBy,
          remarks: values.evidenceRemarks ?? "",
        }
      : null,
  };
}

export const verificationFields: PromptField[] = [
  {
    name: "implementationStatus",
    label: "Verified status",
    type: "select",
    required: true,
    options: options(["Partly Implemented", "Implemented", "Risk Accepted", "Closed"]),
  },
  {
    name: "auditorVerification",
    label: "Verification remarks",
    type: "textarea",
    rows: 4,
    required: true,
    full: true,
    minLength: 10,
  },
  {
    name: "closureConclusion",
    label: "Closure conclusion",
    type: "textarea",
    rows: 3,
    full: true,
    required: true,
    visible: (values) => values.implementationStatus === "Closed",
  },
  {
    name: "riskAcceptanceNote",
    label: "Risk acceptance rationale",
    type: "textarea",
    rows: 3,
    full: true,
    required: true,
    visible: (values) => values.implementationStatus === "Risk Accepted",
  },
  {
    name: "reopenReason",
    label: "Reason the action remains open",
    type: "textarea",
    rows: 3,
    full: true,
    required: true,
    visible: (values) => values.implementationStatus === "Partly Implemented",
  },
];

export function toVerificationInput(values: PromptValues): VerificationInput {
  return {
    auditorVerification: values.auditorVerification ?? "",
    closureConclusion: values.closureConclusion ?? "",
    implementationStatus: (values.implementationStatus ||
      "Partly Implemented") as VerificationInput["implementationStatus"],
    reopenReason: values.reopenReason ?? "",
    riskAcceptanceNote: values.riskAcceptanceNote ?? "",
  };
}

/* ------------------------------- Report ----------------------------- */

export function reportFields(engagements: PromptOption[], lockEngagement: boolean): PromptField[] {
  return [
    {
      name: "engagementId",
      label: "Engagement",
      type: "select",
      required: true,
      readOnly: lockEngagement,
      options: engagements,
    },
    { name: "title", label: "Report title", required: true, minLength: 5 },
    { name: "reportPeriod", label: "Period covered", required: true },
    { name: "addressee", label: "Addressee", required: true },
    { name: "issueDate", label: "Proposed issue date", type: "date" },
    { name: "preparedBy", label: "Prepared by", required: true },
    { name: "executiveSummary", label: "Executive summary", type: "textarea", rows: 5, full: true },
    { name: "overallConclusion", label: "Overall conclusion", type: "textarea", rows: 4, full: true },
  ];
}

export function toReportValues(values: PromptValues): ReportFormValues {
  return {
    engagementId: values.engagementId as EngagementId,
    title: values.title ?? "",
    reportPeriod: values.reportPeriod ?? "",
    addressee: values.addressee ?? "",
    issueDate: values.issueDate ?? "",
    executiveSummary: values.executiveSummary ?? "",
    overallConclusion: values.overallConclusion ?? "",
    preparedBy: values.preparedBy ?? "",
  };
}

export type { ObservationId };
