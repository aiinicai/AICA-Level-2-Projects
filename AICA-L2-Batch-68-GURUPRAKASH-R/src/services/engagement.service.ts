import type { Actor } from "@/types/activity";
import { formatId, type EngagementId, type LifecycleStage } from "@/types/common";
import {
  CANCELLABLE_STATUSES,
  CORRECTABLE_STATUSES,
  HOLDABLE_STATUSES,
  nextStatus,
  resolveStage,
  STATUS_TO_STAGE,
  type EngagementFormValues,
  type EngagementRecord,
  type EngagementStatus,
} from "@/types/engagement";
import { appendActivity } from "./activity.service";
import { delay } from "./mock.utils";
import { clientNameFor, sequences, store } from "./store";

export type EngagementListItem = EngagementRecord & { clientName: string };

export interface EngagementListQuery {
  search?: string;
  clientId?: string;
  auditType?: string;
  auditArea?: string;
  status?: string;
  stage?: string;
  manager?: string;
  plannedFrom?: string;
  plannedTo?: string;
  sortBy?: "reference" | "clientName" | "plannedStartDate" | "plannedCompletionDate" | "status" | "updatedAt";
  sortDir?: "asc" | "desc";
  page?: number;
  pageSize?: number;
}

export interface EngagementListResult {
  items: EngagementListItem[];
  total: number;
  page: number;
  pageSize: number;
}

export interface EngagementService {
  list(query?: EngagementListQuery): Promise<EngagementListResult>;
  getById(id: string): Promise<EngagementListItem | null>;
  getByClientId(clientId: string): Promise<EngagementListItem[]>;
  create(values: EngagementFormValues, actor: Actor): Promise<EngagementRecord>;
  update(id: string, values: EngagementFormValues, actor: Actor): Promise<EngagementRecord>;
  advanceStatus(id: string, actor: Actor, remarks?: string): Promise<EngagementRecord>;
  placeOnHold(id: string, reason: string, actor: Actor): Promise<EngagementRecord>;
  resume(id: string, reason: string, actor: Actor): Promise<EngagementRecord>;
  cancel(id: string, reason: string, actor: Actor): Promise<EngagementRecord>;
  close(id: string, closureRemarks: string, actor: Actor): Promise<EngagementRecord>;
  reopen(id: string, reason: string, actor: Actor): Promise<EngagementRecord>;
  correctStatus(
    id: string,
    target: EngagementStatus,
    reason: string,
    actor: Actor,
  ): Promise<EngagementRecord>;
}

const decorate = (engagement: EngagementRecord): EngagementListItem => ({
  ...engagement,
  clientName: clientNameFor(engagement.clientId) ?? "Unknown client",
});

function find(id: string): EngagementRecord {
  const engagement = store.engagements.find((row) => row.id === id);
  if (!engagement) throw new Error(`Engagement ${id} was not found.`);
  return engagement;
}

function touch(engagement: EngagementRecord, actor: Actor) {
  engagement.updatedAt = new Date().toISOString();
  engagement.updatedBy = actor.user;
}

function log(
  engagement: EngagementRecord,
  actor: Actor,
  action: string,
  remarks: string,
  previousStatus: string | null = null,
  newStatus: string | null = null,
) {
  appendActivity({
    user: actor.user,
    role: actor.role,
    clientId: engagement.clientId,
    clientName: clientNameFor(engagement.clientId),
    engagementId: engagement.id,
    engagementRef: engagement.reference,
    module: "Engagements",
    recordReference: engagement.reference,
    action,
    previousStatus,
    newStatus,
    remarks,
  });
}

/** Applies a status change and keeps the stored lifecycle stage consistent. */
function applyStatus(engagement: EngagementRecord, status: EngagementStatus) {
  const mapped = STATUS_TO_STAGE[status];
  engagement.status = status;
  if (mapped) engagement.lifecycleStage = mapped;
}

export const engagementService: EngagementService = {
  async list(query = {}) {
    const term = query.search?.trim().toLowerCase();
    let rows = store.engagements.map(decorate);

    if (term) {
      rows = rows.filter((row) =>
        [row.reference, row.title, row.clientName].join(" ").toLowerCase().includes(term),
      );
    }
    const eq = (value: string | undefined, field: keyof EngagementListItem) => {
      if (!value || value === "all") return;
      rows = rows.filter((row) => String(row[field]) === value);
    };
    eq(query.clientId, "clientId");
    eq(query.auditType, "auditType");
    eq(query.auditArea, "auditArea");
    eq(query.status, "status");
    eq(query.manager, "engagementManager");
    if (query.stage && query.stage !== "all") {
      rows = rows.filter((row) => resolveStage(row.status, row.lifecycleStage) === query.stage);
    }
    if (query.plannedFrom) {
      rows = rows.filter((row) => row.plannedStartDate >= query.plannedFrom!);
    }
    if (query.plannedTo) {
      rows = rows.filter((row) => row.plannedStartDate <= query.plannedTo!);
    }

    const sortBy = query.sortBy ?? "reference";
    const dir = query.sortDir === "desc" ? -1 : 1;
    rows.sort((a, b) => String(a[sortBy]).localeCompare(String(b[sortBy])) * dir);

    const total = rows.length;
    const page = query.page ?? 1;
    const pageSize = query.pageSize ?? 10;
    const start = (page - 1) * pageSize;
    return delay({ items: rows.slice(start, start + pageSize), total, page, pageSize });
  },

  async getById(id) {
    const engagement = store.engagements.find((row) => row.id === id);
    return delay(engagement ? decorate(engagement) : null);
  },

  async getByClientId(clientId) {
    return delay(
      store.engagements
        .filter((engagement) => engagement.clientId === clientId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values, actor) {
    const reference = formatId("engagement", sequences.nextEngagement()) as EngagementId;
    const timestamp = new Date().toISOString();
    const engagement: EngagementRecord = {
      ...values,
      id: reference,
      reference,
      status: "Draft",
      lifecycleStage: "Planning" as LifecycleStage,
      priorStatus: null,
      priorStage: null,
      closureRemarks: "",
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.engagements.push(engagement);
    log(engagement, actor, "Engagement created", values.remarks || "New engagement created.", null, "Draft");
    return delay(engagement);
  },

  async update(id, values, actor) {
    const engagement = find(id);
    Object.assign(engagement, values, { id: engagement.id, reference: engagement.reference });
    touch(engagement, actor);
    log(engagement, actor, "Engagement updated", "Engagement details amended.", engagement.status, engagement.status);
    return delay(engagement);
  },

  async advanceStatus(id, actor, remarks = "") {
    const engagement = find(id);
    if (
      engagement.status === "On Hold" ||
      engagement.status === "Cancelled" ||
      engagement.status === "Closed"
    ) {
      throw new Error(
        `An engagement that is ${engagement.status} cannot be advanced through the normal workflow.`,
      );
    }
    const target = nextStatus(engagement.status);
    if (!target) throw new Error("There is no further forward transition from this status.");
    const previous = engagement.status;
    applyStatus(engagement, target);
    touch(engagement, actor);
    log(engagement, actor, "Status advanced", remarks || `Advanced from ${previous} to ${target}.`, previous, target);
    return delay(engagement);
  },

  async placeOnHold(id, reason, actor) {
    const engagement = find(id);
    if (!HOLDABLE_STATUSES.includes(engagement.status)) {
      throw new Error(
        `An engagement in ${engagement.status} cannot be placed on hold. Only ${HOLDABLE_STATUSES.join(", ")} are permitted.`,
      );
    }
    const previous = engagement.status;
    engagement.priorStatus = previous;
    engagement.priorStage = engagement.lifecycleStage;
    engagement.status = "On Hold";
    touch(engagement, actor);
    log(engagement, actor, "Engagement placed on hold", reason, previous, "On Hold");
    return delay(engagement);
  },

  async resume(id, reason, actor) {
    const engagement = find(id);
    if (engagement.status !== "On Hold") throw new Error("Only an engagement on hold can be resumed.");
    if (!engagement.priorStatus || !engagement.priorStage) {
      throw new Error(
        `${engagement.reference} cannot be resumed: the stored prior status or prior lifecycle stage is missing. Use Correct status to set the intended workflow status.`,
      );
    }
    const restored = engagement.priorStatus;
    engagement.status = restored;
    engagement.lifecycleStage = engagement.priorStage;
    engagement.priorStatus = null;
    engagement.priorStage = null;
    touch(engagement, actor);
    log(engagement, actor, "Engagement resumed", reason || `Resumed to ${restored}.`, "On Hold", restored);
    return delay(engagement);
  },

  async cancel(id, reason, actor) {
    const engagement = find(id);
    if (!CANCELLABLE_STATUSES.includes(engagement.status)) {
      throw new Error(
        engagement.status === "Cancelled"
          ? `${engagement.reference} is already cancelled.`
          : `A ${engagement.status} engagement cannot be cancelled.`,
      );
    }
    const previous = engagement.status;
    engagement.status = "Cancelled";
    engagement.isActive = false;
    touch(engagement, actor);
    log(engagement, actor, "Engagement cancelled", reason, previous, "Cancelled");
    return delay(engagement);
  },

  async close(id, closureRemarks, actor) {
    const engagement = find(id);
    if (engagement.status !== "Action Tracking") {
      throw new Error("An engagement can only be closed from Action Tracking.");
    }
    const remarks = closureRemarks.trim();
    if (!remarks) throw new Error("Closure remarks are mandatory when closing an engagement.");
    const previous = engagement.status;
    applyStatus(engagement, "Closed");
    engagement.closureRemarks = remarks;
    touch(engagement, actor);
    log(engagement, actor, "Engagement closed", remarks, previous, "Closed");
    return delay(engagement);
  },

  async reopen(id, reason, actor) {
    const engagement = find(id);
    if (engagement.status !== "Closed") throw new Error("Only a closed engagement can be reopened.");
    applyStatus(engagement, "Action Tracking");
    touch(engagement, actor);
    log(engagement, actor, "Engagement reopened", reason, "Closed", "Action Tracking");
    return delay(engagement);
  },

  async correctStatus(id, target, reason, actor) {
    const engagement = find(id);
    if (!CORRECTABLE_STATUSES.includes(target)) {
      throw new Error(
        `${target} cannot be set through Correct status. Use the dedicated Hold, Cancel, Close or Reopen action.`,
      );
    }
    if (!reason.trim()) throw new Error("A correction reason is mandatory.");
    if (engagement.status === target) {
      throw new Error(`${engagement.reference} is already recorded as ${target}.`);
    }
    const previous = engagement.status;
    applyStatus(engagement, target);
    engagement.priorStatus = null;
    engagement.priorStage = null;
    engagement.isActive = true;
    touch(engagement, actor);
    log(engagement, actor, "Status corrected", reason, previous, target);
    return delay(engagement);
  },
};
