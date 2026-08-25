import type { Actor } from "@/types/activity";
import { formatId, type ObservationId } from "@/types/common";
import type { ClarificationRecord } from "@/types/fieldwork";
import {
  calculateRisk,
  missingForFinalisation,
  missingForReview,
  OBSERVATION_EDITABLE_STATUSES,
  OBSERVATION_PRE_FINAL_STATUSES,
  RISK_ORDER,
  type ObservationFormValues,
  type ObservationRecord,
  type ObservationStatus,
  type RatingScale,
} from "@/types/observation";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  actionsForObservation,
  engagementContext,
  findObservation,
  logReporting,
  matches,
  meta,
  nowIso,
  refreshRollUp,
  responseForObservation,
  touch,
  activeFilter,
} from "./reporting.support";

export interface ObservationListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  process?: string;
  riskRating?: string;
  status?: string;
  reportingDecision?: string;
  implementationRollUp?: string;
  sortBy?: "reference" | "risk" | "status" | "updatedAt";
}

export interface ObservationListItem extends ObservationRecord {
  engagementRef: string;
  clientId: string;
  clientName: string;
  responseReference: string | null;
  responseStatus: string | null;
  actionCount: number;
}

function decorate(row: ObservationRecord): ObservationListItem {
  const context = engagementContext(row.engagementId);
  const response = responseForObservation(row.id);
  return {
    ...row,
    engagementRef: context.engagementRef,
    clientId: context.clientId,
    clientName: context.clientName,
    responseReference: response?.reference ?? null,
    responseStatus: response?.status ?? null,
    actionCount: actionsForObservation(row.id).length,
  };
}

const emptyObservation = (
  reference: ObservationId,
  engagementId: ObservationRecord["engagementId"],
): ObservationRecord => ({
  id: reference,
  reference,
  engagementId,
  process: "",
  title: "",
  scopeId: null,
  procedureId: null,
  requirementId: null,
  evidenceId: null,
  clarificationId: null,
  condition: "",
  criteria: "",
  rootCause: "",
  riskImplication: "",
  financialImpact: "",
  recommendation: "",
  supportingEvidence: "",
  impactRating: "",
  likelihoodRating: "",
  calculatedRiskRating: "",
  finalRiskRating: "",
  riskOverrideReason: "",
  status: "Draft",
  reportingDecision: "",
  implementationRollUp: "No Action Created",
  preparedBy: "",
  reviewedBy: "",
  reviewRemarks: "",
  finalisationRemarks: "",
  dropReason: "",
  createdAt: "",
  createdBy: "",
  updatedAt: "",
  updatedBy: "",
  isActive: true,
});

/** Applies the impact × likelihood matrix and the override rule. */
function applyRisk(row: ObservationRecord, values: Partial<ObservationFormValues>) {
  const impact = (values.impactRating ?? row.impactRating) as RatingScale | "";
  const likelihood = (values.likelihoodRating ?? row.likelihoodRating) as RatingScale | "";
  row.impactRating = impact;
  row.likelihoodRating = likelihood;
  row.calculatedRiskRating = impact && likelihood ? calculateRisk(impact, likelihood) : "";
  const requested = values.finalRiskRating ?? row.finalRiskRating;
  row.finalRiskRating = requested || row.calculatedRiskRating;
  if (row.finalRiskRating && row.calculatedRiskRating && row.finalRiskRating !== row.calculatedRiskRating) {
    const reason = (values.riskOverrideReason ?? row.riskOverrideReason ?? "").trim();
    if (!reason) {
      throw new Error(
        `A risk override reason is required when the final rating (${row.finalRiskRating}) differs from the calculated rating (${row.calculatedRiskRating}).`,
      );
    }
    row.riskOverrideReason = reason;
  } else {
    row.riskOverrideReason = "";
  }
}

function guardEditable(row: ObservationRecord) {
  if (!OBSERVATION_EDITABLE_STATUSES.includes(row.status)) {
    throw new Error(
      `${row.reference} is ${row.status}. Finalised wording can only be amended after an Audit Manager reopens the observation.`,
    );
  }
}

function transition(
  row: ObservationRecord,
  next: ObservationStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.status;
  row.status = next;
  row.isActive = next !== "Dropped";
  touch(row, actor);
  logReporting({
    module: "Observations",
    engagementId: row.engagementId,
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: next,
    actor,
  });
  return row;
}

export const observationService = {
  async list(query: ObservationListQuery = {}) {
    let rows = store.observations.map((row) => {
      refreshRollUp(row.id);
      return decorate(row);
    });
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.title, row.condition, row.process, row.preparedBy) &&
        (!activeFilter(query.clientId) || row.clientId === query.clientId) &&
        (!activeFilter(query.engagementId) || row.engagementId === query.engagementId) &&
        (!activeFilter(query.process) || row.process === query.process) &&
        (!activeFilter(query.riskRating) || row.finalRiskRating === query.riskRating) &&
        (!activeFilter(query.status) || row.status === query.status) &&
        (!activeFilter(query.reportingDecision) || row.reportingDecision === query.reportingDecision) &&
        (!activeFilter(query.implementationRollUp) ||
          row.implementationRollUp === query.implementationRollUp),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return b.updatedAt.localeCompare(a.updatedAt);
      if (sortBy === "status") return a.status.localeCompare(b.status);
      if (sortBy === "risk") {
        const left = a.finalRiskRating ? RISK_ORDER[a.finalRiskRating] : 9;
        const right = b.finalRiskRating ? RISK_ORDER[b.finalRiskRating] : 9;
        return left - right || a.reference.localeCompare(b.reference);
      }
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.observations.find((item) => item.id === id);
    if (row) refreshRollUp(row.id);
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.observations
        .filter((row) => row.engagementId === engagementId)
        .map((row) => {
          refreshRollUp(row.id);
          return decorate(row);
        })
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: ObservationFormValues, actor: Actor) {
    const reference = formatId("observation", sequences.nextObservation()) as ObservationId;
    const row = emptyObservation(reference, values.engagementId);
    Object.assign(row, values, meta(actor));
    applyRisk(row, values);
    store.observations.push(row);
    logReporting({
      module: "Observations",
      engagementId: row.engagementId,
      reference,
      action: "Observation created",
      remarks: row.title,
      newStatus: "Draft",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: Partial<ObservationFormValues>, actor: Actor) {
    const row = findObservation(id);
    guardEditable(row);
    const previousFinal = row.finalRiskRating;
    Object.assign(row, values, { id: row.id, reference: row.reference, status: row.status });
    applyRisk(row, values);
    touch(row, actor);
    logReporting({
      module: "Observations",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Observation updated",
      remarks: "Observation details amended.",
      previousStatus: row.status,
      newStatus: row.status,
      actor,
    });
    if (previousFinal && row.finalRiskRating !== previousFinal) {
      logReporting({
        module: "Observations",
        engagementId: row.engagementId,
        reference: row.reference,
        action: "Risk rating overridden",
        remarks: `Final risk rating changed from ${previousFinal} to ${row.finalRiskRating}. ${row.riskOverrideReason}`.trim(),
        previousStatus: previousFinal,
        newStatus: row.finalRiskRating,
        actor,
      });
    }
    return delay(row);
  },

  async submitForReview(id: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Draft") {
      throw new Error(`Only a Draft observation can be submitted for review. ${row.reference} is ${row.status}.`);
    }
    const gaps = missingForReview(row);
    if (gaps.length) throw new Error(`Complete the following before submission: ${gaps.join(", ")}.`);
    return delay(
      transition(row, "Under Auditor Review", "Submitted for review", "Submitted to the auditor for review.", actor),
    );
  },

  async sendBackToDraft(id: string, reviewRemarks: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Under Auditor Review") {
      throw new Error(`Only an observation Under Auditor Review can be sent back. ${row.reference} is ${row.status}.`);
    }
    if (!reviewRemarks.trim()) throw new Error("Review comments are required when sending an observation back to draft.");
    row.reviewRemarks = reviewRemarks;
    row.reviewedBy = actor.user;
    return delay(transition(row, "Draft", "Sent back to draft", reviewRemarks, actor));
  },

  async issueForResponse(id: string, reviewRemarks: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Under Auditor Review") {
      throw new Error(
        `An observation must be Under Auditor Review before it is issued. ${row.reference} is ${row.status}.`,
      );
    }
    if (!reviewRemarks.trim()) throw new Error("Confirmation remarks are required to issue an observation.");
    row.reviewRemarks = reviewRemarks;
    row.reviewedBy = actor.user;
    return delay(
      transition(
        row,
        "Issued for Management Response",
        "Issued for management response",
        reviewRemarks,
        actor,
      ),
    );
  },

  /**
   * Called by the response and action services. Moves an issued observation to
   * Awaiting Finalisation once the response is accepted and every action is agreed.
   */
  maybeAwaitFinalisation(observationId: string, actor: Actor) {
    const row = store.observations.find((item) => item.id === observationId);
    if (!row || row.status !== "Issued for Management Response") return;
    const response = responseForObservation(observationId);
    if (!response || response.status !== "Accepted by Auditor") return;
    const actions = actionsForObservation(observationId);
    if (actions.some((action) => action.agreementStatus !== "Agreed by Auditor")) return;
    transition(
      row,
      "Awaiting Finalisation",
      "Moved to awaiting finalisation",
      "Management response accepted and all management actions agreed.",
      actor,
    );
  },

  async finalise(id: string, finalisationRemarks: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Awaiting Finalisation") {
      throw new Error(`Only an observation Awaiting Finalisation can be finalised. ${row.reference} is ${row.status}.`);
    }
    if (!finalisationRemarks.trim()) throw new Error("Finalisation remarks are required.");
    row.finalisationRemarks = finalisationRemarks;
    const gaps = missingForFinalisation(row);
    if (gaps.length) throw new Error(`Complete the following before finalisation: ${gaps.join(", ")}.`);
    return delay(transition(row, "Finalised", "Observation finalised", finalisationRemarks, actor));
  },

  async includeInReport(id: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Finalised") {
      throw new Error(`Only a Finalised observation can be included in a report. ${row.reference} is ${row.status}.`);
    }
    return delay(
      transition(row, "Included in Report", "Included in report", "Selected for the final report.", actor),
    );
  },

  /** Called on report finalisation. */
  markReported(id: string, reportReference: string, actor: Actor) {
    const row = store.observations.find((item) => item.id === id);
    if (!row) return;
    if (row.status !== "Included in Report" && row.status !== "Finalised") return;
    transition(row, "Reported", "Reported", `Issued in report ${reportReference}.`, actor);
  },

  async drop(id: string, reason: string, actor: Actor) {
    const row = findObservation(id);
    if (!OBSERVATION_PRE_FINAL_STATUSES.includes(row.status) && row.status !== "Finalised") {
      throw new Error(`${row.reference} is ${row.status} and can no longer be dropped.`);
    }
    if (!reason.trim()) throw new Error("A reason is mandatory when dropping an observation.");
    row.dropReason = reason;
    return delay(transition(row, "Dropped", "Observation dropped", reason, actor));
  },

  async reopen(id: string, reason: string, actor: Actor) {
    const row = findObservation(id);
    if (row.status !== "Finalised" && row.status !== "Included in Report" && row.status !== "Reported") {
      throw new Error(`Only a finalised observation can be reopened. ${row.reference} is ${row.status}.`);
    }
    if (!reason.trim()) throw new Error("A reason is required to reopen a finalised observation.");
    return delay(transition(row, "Awaiting Finalisation", "Observation reopened", reason, actor));
  },

  /**
   * Completes the OBS-#### draft reserved by a clarification conversion.
   * Never creates a duplicate — the reserved reference is reused.
   */
  createStubFromClarification(clarification: ClarificationRecord, actor: Actor): ObservationRecord {
    const existing = store.observations.find((row) => row.clarificationId === clarification.reference);
    if (existing) return existing;
    const reference = formatId("observation", sequences.nextObservation()) as ObservationId;
    const scope = store.scopes.find((row) => row.id === clarification.scopeId);
    const row = emptyObservation(reference, clarification.engagementId);
    Object.assign(row, {
      scopeId: clarification.scopeId,
      procedureId: clarification.procedureId,
      requirementId: clarification.requirementId,
      evidenceId: clarification.evidenceId,
      clarificationId: clarification.reference,
      process: scope?.process ?? "",
      title: clarification.subject,
      condition: [clarification.clarificationRaised, clarification.auditeeResponse]
        .filter(Boolean)
        .join("\n\nAuditee response: "),
      riskImplication: clarification.auditorConclusion,
      preparedBy: actor.user,
      createdAt: nowIso(),
      createdBy: actor.user,
      updatedAt: nowIso(),
      updatedBy: actor.user,
    });
    store.observations.push(row);
    logReporting({
      module: "Observations",
      engagementId: row.engagementId,
      reference,
      action: "Observation draft reserved",
      remarks: `Draft observation created from clarification ${clarification.reference}.`,
      newStatus: "Draft",
      actor,
    });
    return row;
  },
};

export type ObservationService = typeof observationService;
