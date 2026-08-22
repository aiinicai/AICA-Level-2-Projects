import type { Actor } from "@/types/activity";
import { formatId, type ManagementResponseId } from "@/types/common";
import type {
  ManagementAcceptance,
  ManagementResponseRecord,
  ResponseStatus,
} from "@/types/reporting";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import { observationService } from "./observation.service";
import {
  activeFilter,
  engagementContext,
  findObservation,
  findResponse,
  logReporting,
  matches,
  meta,
  nowIso,
  refreshRollUp,
  responseForObservation,
  touch,
} from "./reporting.support";

export interface ResponseListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  status?: string;
  acceptance?: string;
  sortBy?: "reference" | "responseDate" | "status" | "updatedAt";
}

export interface ResponseListItem extends ManagementResponseRecord {
  observationRef: string;
  observationTitle: string;
  riskRating: string;
  engagementId: string;
  engagementRef: string;
  clientId: string;
  clientName: string;
}

function decorate(row: ManagementResponseRecord): ResponseListItem {
  const observation = store.observations.find((item) => item.id === row.observationId);
  const context = engagementContext(observation?.engagementId ?? "");
  return {
    ...row,
    observationRef: observation?.reference ?? "—",
    observationTitle: observation?.title ?? "—",
    riskRating: observation?.finalRiskRating || "—",
    engagementId: context.engagementId,
    engagementRef: context.engagementRef,
    clientId: context.clientId,
    clientName: context.clientName,
  };
}

function log(row: ManagementResponseRecord, action: string, remarks: string, previous: ResponseStatus | null, actor: Actor) {
  const observation = store.observations.find((item) => item.id === row.observationId);
  logReporting({
    module: "Management Responses",
    engagementId: observation?.engagementId ?? "",
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: row.status,
    actor,
  });
}

export interface RecordResponseInput {
  managementResponse: string;
  respondent: string;
  respondentDesignation?: string;
  responseDate: string;
  managementAcceptance: ManagementAcceptance;
  causeAcknowledged?: string;
  proposedApproach?: string;
  managementRemarks?: string;
}

export const managementResponseService = {
  async list(query: ResponseListQuery = {}) {
    let rows = store.managementResponses.map(decorate);

    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.observationRef, row.observationTitle, row.respondent, row.managementResponse) &&
        (!activeFilter(query.clientId) || row.clientId === query.clientId) &&
        (!activeFilter(query.engagementId) || row.engagementId === query.engagementId) &&
        (!activeFilter(query.status) || row.status === query.status) &&
        (!activeFilter(query.acceptance) || row.managementAcceptance === query.acceptance),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return b.updatedAt.localeCompare(a.updatedAt);
      if (sortBy === "status") return a.status.localeCompare(b.status);
      if (sortBy === "responseDate") return b.responseDate.localeCompare(a.responseDate);
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.managementResponses.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByObservationId(observationId: string) {
    const row = responseForObservation(observationId);
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.managementResponses
        .map(decorate)
        .filter((row) => row.engagementId === engagementId)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  /** Opens the single response slot for an observation. */
  async create(observationId: string, actor: Actor) {
    const observation = findObservation(observationId);
    if (responseForObservation(observationId)) {
      throw new Error(`${observation.reference} already has a management response record.`);
    }
    const reference = formatId("managementResponse", sequences.nextResponse()) as ManagementResponseId;
    const row: ManagementResponseRecord = {
      id: reference,
      reference,
      observationId: observation.id,
      managementAcceptance: "",
      managementResponse: "",
      causeAcknowledged: "",
      proposedApproach: "",
      managementRemarks: "",
      respondent: "",
      respondentDesignation: "",
      responseDate: "",
      auditorAssessment: "",
      status: "Awaiting Response",
      version: 0,
      history: [],
      ...meta(actor),
    };
    store.managementResponses.push(row);
    log(row, "Management response created", `Response slot opened for ${observation.reference}.`, null, actor);
    refreshRollUp(observation.id);
    return delay(row);
  },

  /** Records or revises the response. Prior wording is preserved in history. */
  async recordResponse(id: string, input: RecordResponseInput, actor: Actor) {
    const row = findResponse(id);
    if (row.status === "Accepted by Auditor") {
      throw new Error(`${row.reference} has been accepted by the auditor and can no longer be revised.`);
    }
    if (!input.managementResponse.trim() || !input.respondent.trim() || !input.responseDate) {
      throw new Error("The management response, respondent and response date are all required.");
    }
    const previous = row.status;
    const revising = row.version > 0;
    if (revising) {
      row.history.push({
        version: row.version,
        managementResponse: row.managementResponse,
        respondent: row.respondent,
        responseDate: row.responseDate,
        managementAcceptance: row.managementAcceptance,
        recordedAt: row.updatedAt,
        recordedBy: row.updatedBy,
      });
    }
    row.version += 1;
    row.managementResponse = input.managementResponse;
    row.respondent = input.respondent;
    row.respondentDesignation = input.respondentDesignation ?? row.respondentDesignation;
    row.responseDate = input.responseDate;
    row.managementAcceptance = input.managementAcceptance;
    row.causeAcknowledged = input.causeAcknowledged ?? row.causeAcknowledged;
    row.proposedApproach = input.proposedApproach ?? row.proposedApproach;
    row.managementRemarks = input.managementRemarks ?? row.managementRemarks;
    row.status = "Response Received";
    touch(row, actor);
    log(
      row,
      revising ? "Response revised" : "Response submitted",
      `Version ${row.version} recorded by ${input.respondent} (${input.managementAcceptance}).`,
      previous,
      actor,
    );
    refreshRollUp(row.observationId);
    return delay(row);
  },

  async requestRevision(id: string, remarks: string, actor: Actor) {
    const row = findResponse(id);
    if (row.status !== "Response Received") {
      throw new Error(`A revision can only be requested on a received response. ${row.reference} is ${row.status}.`);
    }
    if (!remarks.trim()) throw new Error("Auditor remarks are required when requesting a revision.");
    const previous = row.status;
    row.auditorAssessment = remarks;
    row.status = "Revision Requested";
    touch(row, actor);
    log(row, "Revision requested", remarks, previous, actor);
    return delay(row);
  },

  async accept(id: string, auditorAssessment: string, actor: Actor) {
    const row = findResponse(id);
    if (row.status !== "Response Received") {
      throw new Error(`Only a received response can be accepted. ${row.reference} is ${row.status}.`);
    }
    if (!auditorAssessment.trim()) throw new Error("An auditor assessment is required to accept a response.");
    const previous = row.status;
    row.auditorAssessment = auditorAssessment;
    row.status = "Accepted by Auditor";
    row.updatedAt = nowIso();
    row.updatedBy = actor.user;
    log(row, "Accepted by auditor", auditorAssessment, previous, actor);
    observationService.maybeAwaitFinalisation(row.observationId, actor);
    refreshRollUp(row.observationId);
    return delay(row);
  },
};

export type ManagementResponseService = typeof managementResponseService;
