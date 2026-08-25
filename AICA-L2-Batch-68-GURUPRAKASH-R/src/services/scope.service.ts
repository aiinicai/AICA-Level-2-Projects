import type { Actor } from "@/types/activity";
import { formatId, type ScopeId } from "@/types/common";
import type { ScopeFormValues, ScopeRecord, ScopeStatus } from "@/types/fieldwork";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  byUpdatedDesc,
  findScope,
  logFieldwork,
  matches,
  nowIso,
  proceduresForScope,
  touch,
} from "./fieldwork.support";

export interface ScopeListQuery {
  search?: string;
  engagementId?: string;
  process?: string;
  auditor?: string;
  status?: string;
  sortBy?: "reference" | "process" | "status" | "updatedAt";
}

export interface ScopeListItem extends ScopeRecord {
  engagementRef: string;
  clientName: string;
  procedureCount: number;
}

function decorate(row: ScopeRecord): ScopeListItem {
  const engagement = store.engagements.find((item) => item.id === row.engagementId);
  const client = store.clients.find((item) => item.id === engagement?.clientId);
  return {
    ...row,
    engagementRef: engagement?.reference ?? "—",
    clientName: client?.legalName ?? "—",
    procedureCount: proceduresForScope(row.id).length,
  };
}

const ALL = "all";
const active = (value?: string) => value && value !== ALL;

export const scopeService = {
  async list(query: ScopeListQuery = {}) {
    let rows = store.scopes.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.process, row.subProcess, row.engagementRef, row.objective) &&
        (!active(query.engagementId) || row.engagementId === query.engagementId) &&
        (!active(query.process) || row.process === query.process) &&
        (!active(query.auditor) || row.assignedAuditor === query.auditor) &&
        (!active(query.status) || row.status === query.status),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return byUpdatedDesc(a, b);
      if (sortBy === "process") return a.process.localeCompare(b.process) || a.reference.localeCompare(b.reference);
      if (sortBy === "status") return a.status.localeCompare(b.status) || a.reference.localeCompare(b.reference);
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.scopes.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.scopes
        .filter((row) => row.engagementId === engagementId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: ScopeFormValues, actor: Actor) {
    const reference = formatId("scope", sequences.nextScope()) as ScopeId;
    const timestamp = nowIso();
    const row: ScopeRecord = {
      ...values,
      id: reference,
      reference,
      status: "Draft",
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.scopes.push(row);
    logFieldwork({
      module: "Scope",
      engagementId: row.engagementId,
      reference,
      action: "Scope created",
      remarks: `${row.process} — ${row.subProcess || row.objective.slice(0, 80)}`,
      newStatus: "Draft",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: ScopeFormValues, actor: Actor) {
    const row = findScope(id);
    if (row.status === "Not Applicable") {
      throw new Error(`${row.reference} is marked Not Applicable and can no longer be edited.`);
    }
    Object.assign(row, values, { id: row.id, reference: row.reference, status: row.status });
    touch(row, actor);
    logFieldwork({
      module: "Scope",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Scope updated",
      remarks: "Scope details amended.",
      previousStatus: row.status,
      newStatus: row.status,
      actor,
    });
    return delay(row);
  },

  /** Draft → Active. */
  async activate(id: string, actor: Actor) {
    const row = findScope(id);
    if (row.status !== "Draft") {
      throw new Error(`Only a Draft scope can be activated. ${row.reference} is ${row.status}.`);
    }
    return delay(setStatus(row, "Active", "Scope activated", "Scope moved into fieldwork.", actor));
  },

  async markCompleted(id: string, remarks: string, actor: Actor) {
    const row = findScope(id);
    if (row.status !== "Draft" && row.status !== "Active") {
      throw new Error(`${row.reference} is ${row.status} and cannot be marked Completed.`);
    }
    const open = proceduresForScope(row.id).filter(
      (procedure) => !["Completed", "Exception Noted", "Not Applicable"].includes(procedure.status),
    );
    if (open.length > 0) {
      throw new Error(
        `${open.length} procedure(s) under ${row.reference} are still open. Complete or mark them Not Applicable first.`,
      );
    }
    return delay(setStatus(row, "Completed", "Scope completed", remarks, actor));
  },

  async markNotApplicable(id: string, reason: string, actor: Actor) {
    const row = findScope(id);
    if (row.status === "Not Applicable") {
      throw new Error(`${row.reference} is already marked Not Applicable.`);
    }
    if (!reason.trim()) throw new Error("A reason is required to mark a scope Not Applicable.");
    return delay(setStatus(row, "Not Applicable", "Scope marked Not Applicable", reason, actor));
  },
};

function setStatus(
  row: ScopeRecord,
  next: ScopeStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.status;
  row.status = next;
  row.isActive = next !== "Not Applicable";
  touch(row, actor);
  logFieldwork({
    module: "Scope",
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

export type ScopeService = typeof scopeService;
