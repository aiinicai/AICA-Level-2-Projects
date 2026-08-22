import type { Actor } from "@/types/activity";
import { formatId, type ClarificationId } from "@/types/common";
import {
  CLARIFICATION_FINAL_STATUSES,
  type ClarificationFormValues,
  type ClarificationRecord,
  type ClarificationStatus,
} from "@/types/fieldwork";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  byUpdatedDesc,
  findClarification,
  logFieldwork,
  matches,
  nowIso,
  touch,
} from "./fieldwork.support";
import { observationService } from "./observation.service";

export interface ClarificationListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  status?: string;
  respondent?: string;
  dueFrom?: string;
  dueTo?: string;
  sortBy?: "reference" | "dateRaised" | "responseDueDate" | "updatedAt";
}

export interface ClarificationListItem extends ClarificationRecord {
  engagementRef: string;
  clientId: string;
  clientName: string;
  linkedRecord: string;
}

function decorate(row: ClarificationRecord): ClarificationListItem {
  const engagement = store.engagements.find((item) => item.id === row.engagementId);
  const client = store.clients.find((item) => item.id === engagement?.clientId);
  const linked =
    row.evidenceId ?? row.requirementId ?? row.procedureId ?? row.scopeId ?? row.engagementId;
  return {
    ...row,
    engagementRef: engagement?.reference ?? "—",
    clientId: client?.id ?? "",
    clientName: client?.legalName ?? "—",
    linkedRecord: linked,
  };
}

const ALL = "all";
const active = (value?: string) => value && value !== ALL;

export const clarificationService = {
  async list(query: ClarificationListQuery = {}) {
    let rows = store.clarifications.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.subject, row.clarificationRaised, row.respondent, row.linkedRecord) &&
        (!active(query.clientId) || row.clientId === query.clientId) &&
        (!active(query.engagementId) || row.engagementId === query.engagementId) &&
        (!active(query.status) || row.status === query.status) &&
        (!active(query.respondent) || row.respondent === query.respondent) &&
        (!query.dueFrom || row.responseDueDate >= query.dueFrom) &&
        (!query.dueTo || row.responseDueDate <= query.dueTo),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return byUpdatedDesc(a, b);
      if (sortBy === "dateRaised") return b.dateRaised.localeCompare(a.dateRaised);
      if (sortBy === "responseDueDate") return a.responseDueDate.localeCompare(b.responseDueDate);
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.clarifications.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.clarifications
        .filter((row) => row.engagementId === engagementId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: ClarificationFormValues, actor: Actor) {
    const reference = formatId("clarification", sequences.nextClarification()) as ClarificationId;
    const timestamp = nowIso();
    const row: ClarificationRecord = {
      ...values,
      id: reference,
      reference,
      auditeeResponse: "",
      responseDate: "",
      auditorConclusion: "",
      status: "Draft",
      observationId: null,
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.clarifications.push(row);
    logFieldwork({
      module: "Clarifications",
      engagementId: row.engagementId,
      reference,
      action: "Clarification created",
      remarks: row.subject,
      newStatus: "Draft",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: ClarificationFormValues, actor: Actor) {
    const row = guardEditable(id);
    Object.assign(row, values, { id: row.id, reference: row.reference, status: row.status });
    touch(row, actor);
    logFieldwork({
      module: "Clarifications",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Clarification updated",
      remarks: "Clarification details amended.",
      previousStatus: row.status,
      newStatus: row.status,
      actor,
    });
    return delay(row);
  },

  async open(id: string, input: { responseDueDate: string; respondent: string }, actor: Actor) {
    const row = guardEditable(id);
    if (row.status !== "Draft") {
      throw new Error(`Only a Draft clarification can be opened. ${row.reference} is ${row.status}.`);
    }
    if (!input.responseDueDate || !input.respondent.trim()) {
      throw new Error("A response due date and a respondent are required to open a clarification.");
    }
    row.responseDueDate = input.responseDueDate;
    row.respondent = input.respondent;
    return delay(
      apply(row, "Open", "Clarification opened", `Issued to ${input.respondent}, due ${input.responseDueDate}.`, actor),
    );
  },

  async recordResponse(
    id: string,
    input: { auditeeResponse: string; responseDate: string },
    actor: Actor,
  ) {
    const row = guardEditable(id);
    if (row.status !== "Open" && row.status !== "Further Clarification Required") {
      throw new Error(`A response can only be recorded on an open clarification. ${row.reference} is ${row.status}.`);
    }
    if (!input.auditeeResponse.trim() || !input.responseDate) {
      throw new Error("Both the auditee response and the response date are required.");
    }
    row.auditeeResponse = input.auditeeResponse;
    row.responseDate = input.responseDate;
    return delay(apply(row, "Response Received", "Response recorded", input.auditeeResponse.slice(0, 200), actor));
  },

  async seekFurther(id: string, reason: string, actor: Actor) {
    const row = guardEditable(id);
    if (row.status !== "Response Received") {
      throw new Error(`Further clarification can only be sought after a response is received. ${row.reference} is ${row.status}.`);
    }
    if (!reason.trim()) throw new Error("Explain what further clarification is required.");
    return delay(apply(row, "Further Clarification Required", "Further clarification requested", reason, actor));
  },

  async resolve(id: string, auditorConclusion: string, actor: Actor) {
    const row = guardEditable(id);
    if (row.status !== "Response Received") {
      throw new Error(`Only a clarification with a recorded response can be resolved. ${row.reference} is ${row.status}.`);
    }
    if (!auditorConclusion.trim()) throw new Error("An auditor conclusion is required to resolve a clarification.");
    row.auditorConclusion = auditorConclusion;
    return delay(apply(row, "Resolved", "Clarification resolved", auditorConclusion.slice(0, 200), actor));
  },

  /** Reserves an OBS-#### draft stub and freezes the clarification. */
  async convertToObservation(id: string, actor: Actor) {
    const row = guardEditable(id);
    if (row.status !== "Resolved") {
      throw new Error(`Only a Resolved clarification can be converted. ${row.reference} is ${row.status}.`);
    }
    const stub = observationService.createStubFromClarification(row, actor);
    row.observationId = stub.reference;
    apply(
      row,
      "Converted to Observation",
      "Converted to observation",
      `Reserved observation reference ${stub.reference}.`,
      actor,
    );
    return delay({ clarification: row, observation: stub });
  },

  async closeWithoutObservation(id: string, reason: string, actor: Actor) {
    const row = guardEditable(id);
    if (row.status !== "Resolved") {
      throw new Error(`Only a Resolved clarification can be closed. ${row.reference} is ${row.status}.`);
    }
    if (!reason.trim()) throw new Error("A reason is required to close a clarification without an observation.");
    return delay(apply(row, "Closed Without Observation", "Closed without observation", reason, actor));
  },
};

function guardEditable(id: string): ClarificationRecord {
  const row = findClarification(id);
  if (CLARIFICATION_FINAL_STATUSES.includes(row.status)) {
    throw new Error(`${row.reference} is ${row.status} and is now read-only.`);
  }
  return row;
}

function apply(
  row: ClarificationRecord,
  next: ClarificationStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.status;
  row.status = next;
  row.isActive = !CLARIFICATION_FINAL_STATUSES.includes(next);
  row.updatedAt = nowIso();
  row.updatedBy = actor.user;
  logFieldwork({
    module: "Clarifications",
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

export type ClarificationService = typeof clarificationService;
