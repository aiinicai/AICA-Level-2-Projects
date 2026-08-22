import type { PromptField, PromptOption, PromptValues } from "@/components/common/prompt-dialog";
import type { ClarificationId, EngagementId, EvidenceId, ProcedureId, RequirementId, ScopeId } from "@/types/common";
import {
  AUDIT_RESULTS,
  DEPARTMENTS,
  DOCUMENT_CATEGORIES,
  DOCUMENT_FORMATS,
  EVIDENCE_REVIEW_STATUSES,
  FILE_TYPES,
  REQUIREMENT_PRIORITIES,
  SAMPLE_METHODS,
  type ClarificationFormValues,
  type EvidenceFormValues,
  type ProcedureFormValues,
  type RequirementFormValues,
  type RequirementPriority,
  type ScopeFormValues,
} from "@/types/fieldwork";

/**
 * Declarative field definitions for every Stage 3 form, consumed by the shared
 * PromptDialog. Keeping them here keeps the page components thin.
 */

export const AUDITORS = ["Auditor 1", "Auditor 2", "Auditor 3", "Auditor 4", "A. Auditor"] as const;

export const PROCESSES = [
  "Job Work",
  "Procurement",
  "Inventory",
  "Production",
  "Sales and Receivables",
  "Finance and Accounts",
  "Fixed Assets",
  "Human Resources",
  "Information Technology",
] as const;

const list = (values: readonly string[]): PromptOption[] =>
  values.map((value) => ({ value, label: value }));

export const auditorOptions = list(AUDITORS);

/* ------------------------------- Scope ------------------------------ */

export function scopeFields(engagements: PromptOption[], lockEngagement = false): PromptField[] {
  return [
    {
      name: "engagementId",
      label: "Engagement",
      type: "select",
      required: true,
      options: engagements,
      readOnly: lockEngagement,
    },
    { name: "process", label: "Process", type: "select", required: true, options: list(PROCESSES) },
    { name: "subProcess", label: "Sub-process", placeholder: "Optional" },
    { name: "assignedAuditor", label: "Assigned auditor", type: "select", required: true, options: auditorOptions },
    { name: "objective", label: "Audit objective", type: "textarea", required: true, rows: 3 },
    { name: "keyRisk", label: "Key risk", type: "textarea", required: true, rows: 2 },
    { name: "expectedControl", label: "Expected control", type: "textarea", required: true, rows: 2 },
    { name: "inclusion", label: "Scope inclusion", type: "textarea", rows: 2 },
    { name: "exclusion", label: "Scope exclusion", type: "textarea", rows: 2 },
    { name: "applicablePolicy", label: "Applicable policy or regulation", full: true },
    { name: "remarks", label: "Remarks", type: "textarea", rows: 2 },
  ];
}

export function toScopeValues(values: PromptValues): ScopeFormValues {
  return {
    engagementId: values.engagementId as EngagementId,
    process: values.process,
    subProcess: values.subProcess ?? "",
    objective: values.objective,
    inclusion: values.inclusion ?? "",
    exclusion: values.exclusion ?? "",
    keyRisk: values.keyRisk,
    expectedControl: values.expectedControl,
    applicablePolicy: values.applicablePolicy ?? "",
    assignedAuditor: values.assignedAuditor,
    remarks: values.remarks ?? "",
  };
}

/* ----------------------------- Procedure ---------------------------- */

export function procedureFields(scopes: PromptOption[], lockScope = false): PromptField[] {
  return [
    { name: "scopeId", label: "Scope", type: "select", required: true, options: scopes, readOnly: lockScope },
    { name: "assignedAuditor", label: "Assigned auditor", type: "select", required: true, options: auditorOptions },
    { name: "riskAddressed", label: "Risk addressed", type: "textarea", required: true, rows: 2 },
    { name: "controlObjective", label: "Control objective", type: "textarea", required: true, rows: 2 },
    { name: "description", label: "Procedure description", type: "textarea", required: true, rows: 3 },
    { name: "population", label: "Population" },
    { name: "sampleSize", label: "Sample size" },
    { name: "sampleMethod", label: "Sample selection method", type: "select", options: list(SAMPLE_METHODS) },
    {
      name: "targetDate",
      label: "Target date",
      type: "date",
      required: true,
      hint: "Cannot be earlier than the engagement planned start date.",
    },
    { name: "remarks", label: "Remarks", type: "textarea", rows: 2 },
  ];
}

export function toProcedureValues(values: PromptValues, conclusion = ""): ProcedureFormValues {
  return {
    scopeId: values.scopeId as ScopeId,
    riskAddressed: values.riskAddressed,
    controlObjective: values.controlObjective,
    description: values.description,
    population: values.population ?? "",
    sampleSize: values.sampleSize ?? "",
    sampleMethod: values.sampleMethod ?? "",
    assignedAuditor: values.assignedAuditor,
    targetDate: values.targetDate,
    conclusion,
    remarks: values.remarks ?? "",
  };
}

/* ---------------------------- Requirement --------------------------- */

export interface RequirementOptionData {
  engagements: PromptOption[];
  scopes: { id: string; reference: string; process: string; engagementId: string }[];
  procedures: { id: string; reference: string; description: string; scopeId: string }[];
}

/** Engagement → Scope → Procedure cascade; only the procedure id is stored. */
export function requirementFields(data: RequirementOptionData): PromptField[] {
  return [
    {
      name: "engagementId",
      label: "Engagement",
      type: "select",
      required: true,
      options: data.engagements,
      clears: ["scopeId", "procedureId"],
    },
    {
      name: "scopeId",
      label: "Scope",
      type: "select",
      required: true,
      clears: ["procedureId"],
      options: (values) =>
        data.scopes
          .filter((scope) => scope.engagementId === values.engagementId)
          .map((scope) => ({ value: scope.id, label: `${scope.reference} · ${scope.process}` })),
    },
    {
      name: "procedureId",
      label: "Procedure",
      type: "select",
      required: true,
      full: true,
      options: (values) =>
        data.procedures
          .filter((procedure) => procedure.scopeId === values.scopeId)
          .map((procedure) => ({
            value: procedure.id,
            label: `${procedure.reference} · ${procedure.description.slice(0, 70)}`,
          })),
    },
    { name: "department", label: "Department", type: "select", required: true, options: list(DEPARTMENTS) },
    { name: "responsiblePerson", label: "Responsible person", required: true },
    { name: "description", label: "Requirement description", type: "textarea", required: true, rows: 3 },
    { name: "formatRequired", label: "Format required", type: "select", options: list(DOCUMENT_FORMATS) },
    { name: "periodCovered", label: "Period covered" },
    { name: "dueDate", label: "Due date", type: "date", required: true },
    { name: "priority", label: "Priority", type: "select", required: true, options: list(REQUIREMENT_PRIORITIES) },
    { name: "auditorRemarks", label: "Auditor remarks", type: "textarea", rows: 2 },
    { name: "auditeeRemarks", label: "Auditee remarks", type: "textarea", rows: 2 },
  ];
}

export function toRequirementValues(values: PromptValues): RequirementFormValues {
  return {
    engagementId: values.engagementId as EngagementId,
    procedureId: values.procedureId as ProcedureId,
    department: values.department,
    description: values.description,
    formatRequired: values.formatRequired ?? "",
    periodCovered: values.periodCovered ?? "",
    responsiblePerson: values.responsiblePerson,
    dueDate: values.dueDate,
    priority: values.priority as RequirementPriority,
    auditorRemarks: values.auditorRemarks ?? "",
    auditeeRemarks: values.auditeeRemarks ?? "",
  };
}

/* ------------------------------ Evidence ---------------------------- */

export function evidenceFields(requirements: PromptOption[], lockRequirement = false): PromptField[] {
  return [
    {
      name: "requirementId",
      label: "Requirement",
      type: "select",
      required: true,
      full: true,
      options: requirements,
      readOnly: lockRequirement,
    },
    { name: "fileName", label: "File name", required: true, hint: "Metadata only — no file is stored." },
    { name: "documentCategory", label: "Document category", type: "select", required: true, options: list(DOCUMENT_CATEGORIES) },
    { name: "fileType", label: "File type", type: "select", required: true, options: list(FILE_TYPES) },
    { name: "fileSize", label: "File size", placeholder: "e.g. 420 KB" },
    { name: "submittedBy", label: "Submitted by", required: true },
    { name: "submissionDate", label: "Submission date", type: "date", required: true },
    { name: "assignedReviewer", label: "Assigned reviewer", type: "select", required: true, options: auditorOptions },
    { name: "auditeeRemarks", label: "Auditee remarks", type: "textarea", rows: 2 },
  ];
}

export function toEvidenceValues(values: PromptValues): EvidenceFormValues {
  return {
    requirementId: values.requirementId as RequirementId,
    fileName: values.fileName,
    documentCategory: values.documentCategory,
    fileType: values.fileType,
    fileSize: values.fileSize ?? "",
    submittedBy: values.submittedBy,
    submissionDate: values.submissionDate,
    auditeeRemarks: values.auditeeRemarks ?? "",
    assignedReviewer: values.assignedReviewer,
  };
}

export const evidenceReviewFields: PromptField[] = [
  {
    name: "reviewStatus",
    label: "Review status",
    type: "select",
    required: true,
    options: list(EVIDENCE_REVIEW_STATUSES.filter((status) => status !== "Awaiting Review" && status !== "Accepted")),
  },
  { name: "auditResult", label: "Audit result", type: "select", required: true, options: list(AUDIT_RESULTS) },
  { name: "reviewRemarks", label: "Reviewer remarks", type: "textarea", required: true, rows: 3, minLength: 5 },
];

/* --------------------------- Clarification -------------------------- */

export interface ClarificationOptionData {
  engagements: PromptOption[];
  scopes: { id: string; reference: string; process: string; engagementId: string }[];
  procedures: { id: string; reference: string; scopeId: string }[];
  requirements: { id: string; reference: string; engagementId: string }[];
  evidence: { id: string; reference: string; requirementId: string }[];
}

const NONE = "—";

export function clarificationFields(data: ClarificationOptionData, lockEngagement = false): PromptField[] {
  return [
    {
      name: "engagementId",
      label: "Engagement",
      type: "select",
      required: true,
      readOnly: lockEngagement,
      clears: ["scopeId", "procedureId", "requirementId", "evidenceId"],
      options: data.engagements,
    },
    { name: "subject", label: "Clarification subject", required: true },
    {
      name: "scopeId",
      label: "Linked scope (optional)",
      type: "select",
      options: (values) => [
        { value: NONE, label: "Not linked" },
        ...data.scopes
          .filter((scope) => scope.engagementId === values.engagementId)
          .map((scope) => ({ value: scope.id, label: `${scope.reference} · ${scope.process}` })),
      ],
      clears: ["procedureId"],
    },
    {
      name: "procedureId",
      label: "Linked procedure (optional)",
      type: "select",
      options: (values) => [
        { value: NONE, label: "Not linked" },
        ...data.procedures
          .filter((procedure) => procedure.scopeId === values.scopeId)
          .map((procedure) => ({ value: procedure.id, label: procedure.reference })),
      ],
    },
    {
      name: "requirementId",
      label: "Linked requirement (optional)",
      type: "select",
      clears: ["evidenceId"],
      options: (values) => [
        { value: NONE, label: "Not linked" },
        ...data.requirements
          .filter((requirement) => requirement.engagementId === values.engagementId)
          .map((requirement) => ({ value: requirement.id, label: requirement.reference })),
      ],
    },
    {
      name: "evidenceId",
      label: "Linked evidence (optional)",
      type: "select",
      options: (values) => [
        { value: NONE, label: "Not linked" },
        ...data.evidence
          .filter((item) => item.requirementId === values.requirementId)
          .map((item) => ({ value: item.id, label: item.reference })),
      ],
    },
    { name: "clarificationRaised", label: "Clarification raised", type: "textarea", required: true, rows: 4 },
    { name: "raisedBy", label: "Raised by", required: true },
    { name: "dateRaised", label: "Date raised", type: "date", required: true },
    { name: "respondent", label: "Respondent", hint: "Required before the clarification can be opened." },
    { name: "responseDueDate", label: "Response due date", type: "date" },
  ];
}

const orNull = <T extends string>(value: string | undefined): T | null =>
  !value || value === NONE ? null : (value as T);

export function toClarificationValues(values: PromptValues): ClarificationFormValues {
  return {
    engagementId: values.engagementId as EngagementId,
    scopeId: orNull<ScopeId>(values.scopeId),
    procedureId: orNull<ProcedureId>(values.procedureId),
    requirementId: orNull<RequirementId>(values.requirementId),
    evidenceId: orNull<EvidenceId>(values.evidenceId),
    subject: values.subject,
    clarificationRaised: values.clarificationRaised,
    raisedBy: values.raisedBy,
    dateRaised: values.dateRaised,
    responseDueDate: values.responseDueDate ?? "",
    respondent: values.respondent ?? "",
  };
}

export type { ClarificationId };

/** Coerces an entity record into the string map PromptDialog expects. */
export function toPromptValues(record: object): PromptValues {
  const values: PromptValues = {};
  for (const [key, value] of Object.entries(record)) {
    if (value === null || value === undefined || typeof value === "boolean") continue;
    if (typeof value === "object") continue;
    values[key] = String(value);
  }
  return values;
}
