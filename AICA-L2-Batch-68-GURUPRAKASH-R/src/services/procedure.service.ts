import type { Actor } from "@/types/activity";
import { formatId, type ProcedureId } from "@/types/common";
import {
  PROCEDURE_TRANSITIONS,
  type ProcedureFormValues,
  type ProcedureRecord,
  type ProcedureStatus,
} from "@/types/fieldwork";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  byUpdatedDesc,
  engagementOf,
  engagementOfProcedure,
  findProcedure,
  findScope,
  logFieldwork,
  matches,
  nowIso,
  procedureIdsForEngagement,
  requirementsForProcedure,
  touch,
} from "./fieldwork.support";

export interface ProcedureListQuery {
  search?: string;
  engagementId?: string;
  scopeId?: string;
  auditor?: string;
  status?: string;
  sortBy?: "reference" | "targetDate" | "status" | "updatedAt";
}

export interface ProcedureListItem extends ProcedureRecord {
  scopeRef: string;
  process: string;
  engagementId: string;
  engagementRef: string;
  clientName: string;
  requirementCount: number;
}

function decorate(row: ProcedureRecord): ProcedureListItem {
  const scope = store.scopes.find((item) => item.id === row.scopeId);
  const engagement = store.engagements.find((item) => item.id === scope?.engagementId);
  const client = store.clients.find((item) => item.id === engagement?.clientId);
  return {
    ...row,
    scopeRef: scope?.reference ?? "—",
    process: scope?.process ?? "—",
    engagementId: scope?.engagementId ?? "",
    engagementRef: engagement?.reference ?? "—",
    clientName: client?.legalName ?? "—",
    requirementCount: requirementsForProcedure(row.id).length,
  };
}

const ALL = "all";
const active = (value?: string) => value && value !== ALL;

export const procedureService = {
  async list(query: ProcedureListQuery = {}) {
    let rows = store.procedures.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.description, row.scopeRef, row.riskAddressed, row.process) &&
        (!active(query.engagementId) || row.engagementId === query.engagementId) &&
        (!active(query.scopeId) || row.scopeId === query.scopeId) &&
        (!active(query.auditor) || row.assignedAuditor === query.auditor) &&
        (!active(query.status) || row.status === query.status),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return byUpdatedDesc(a, b);
      if (sortBy === "targetDate") return a.targetDate.localeCompare(b.targetDate);
      if (sortBy === "status") return a.status.localeCompare(b.status) || a.reference.localeCompare(b.reference);
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.procedures.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByScopeId(scopeId: string) {
    return delay(
      store.procedures
        .filter((row) => row.scopeId === scopeId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async getByEngagementId(engagementId: string) {
    const ids = procedureIdsForEngagement(engagementId);
    return delay(
      store.procedures
        .filter((row) => ids.includes(row.id))
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: ProcedureFormValues, actor: Actor) {
    validateTargetDate(values);
    const reference = formatId("procedure", sequences.nextProcedure()) as ProcedureId;
    const timestamp = nowIso();
    const row: ProcedureRecord = {
      ...values,
      conclusion: "",
      id: reference,
      reference,
      status: "Not Started",
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.procedures.push(row);
    logFieldwork({
      module: "Procedures",
      engagementId: engagementOfProcedure(reference),
      reference,
      action: "Procedure created",
      remarks: row.description.slice(0, 120),
      newStatus: "Not Started",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: ProcedureFormValues, actor: Actor) {
    const row = findProcedure(id);
    if (row.status === "Not Applicable") {
      throw new Error(`${row.reference} is Not Applicable and can no longer be edited.`);
    }
    validateTargetDate({ ...values, scopeId: row.scopeId });
    const conclusionEditable = ["Completed", "Exception Noted", "Not Applicable"].includes(row.status);
    Object.assign(row, values, {
      id: row.id,
      reference: row.reference,
      status: row.status,
      conclusion: conclusionEditable ? values.conclusion : row.conclusion,
    });
    touch(row, actor);
    logFieldwork({
      module: "Procedures",
      engagementId: engagementOfProcedure(row.id),
      reference: row.reference,
      action: "Procedure updated",
      remarks: "Procedure details amended.",
      previousStatus: row.status,
      newStatus: row.status,
      actor,
    });
    return delay(row);
  },

  /** Controlled forward / lateral transition along the permitted map. */
  async changeStatus(id: string, next: ProcedureStatus, remarks: string, actor: Actor) {
    const row = findProcedure(id);
    if (!PROCEDURE_TRANSITIONS[row.status].includes(next)) {
      throw new Error(`${row.reference} cannot move from ${row.status} to ${next}.`);
    }
    return delay(apply(row, next, `Procedure marked ${next}`, remarks, actor));
  },

  async markNotApplicable(id: string, reason: string, actor: Actor) {
    const row = findProcedure(id);
    if (["Completed", "Exception Noted", "Not Applicable"].includes(row.status)) {
      throw new Error(
        `${row.reference} is ${row.status}; only a non-final procedure may be marked Not Applicable.`,
      );
    }
    if (!reason.trim()) throw new Error("A reason is required to mark a procedure Not Applicable.");
    return delay(apply(row, "Not Applicable", "Procedure marked Not Applicable", reason, actor));
  },

  /** Manager-only reopen of a finalised procedure. */
  async reopen(id: string, reason: string, actor: Actor) {
    const row = findProcedure(id);
    if (row.status !== "Completed" && row.status !== "Exception Noted") {
      throw new Error(`Only a Completed or Exception Noted procedure can be reopened. ${row.reference} is ${row.status}.`);
    }
    if (actor.role !== "Audit Manager") {
      throw new Error("Only the Audit Manager may reopen a finalised procedure.");
    }
    if (!reason.trim()) throw new Error("A reason is required to reopen a procedure.");
    return delay(apply(row, "In Progress", "Procedure reopened", reason, actor));
  },

  /** Test conclusion is editable only in a final status. */
  async recordConclusion(id: string, conclusion: string, actor: Actor) {
    const row = findProcedure(id);
    if (!["Completed", "Exception Noted", "Not Applicable"].includes(row.status)) {
      throw new Error("A test conclusion can only be recorded once the procedure reaches a final status.");
    }
    row.conclusion = conclusion;
    touch(row, actor);
    logFieldwork({
      module: "Procedures",
      engagementId: engagementOfProcedure(row.id),
      reference: row.reference,
      action: "Test conclusion recorded",
      remarks: conclusion.slice(0, 200),
      previousStatus: row.status,
      newStatus: row.status,
      actor,
    });
    return delay(row);
  },
};

function apply(
  row: ProcedureRecord,
  next: ProcedureStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.status;
  row.status = next;
  row.isActive = next !== "Not Applicable";
  touch(row, actor);
  logFieldwork({
    module: "Procedures",
    engagementId: engagementOfProcedure(row.id),
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: next,
    actor,
  });
  return row;
}

function validateTargetDate(values: { scopeId: string; targetDate: string }) {
  const scope = findScope(values.scopeId);
  const engagement = engagementOf(scope.engagementId);
  if (engagement && values.targetDate && values.targetDate < engagement.plannedStartDate) {
    throw new Error(
      `Target date cannot be earlier than the engagement planned start date (${engagement.plannedStartDate}).`,
    );
  }
}

export type ProcedureService = typeof procedureService;
