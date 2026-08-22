import type { Actor } from "@/types/activity";
import { formatId, type ManagementActionId } from "@/types/common";
import {
  dueStatusFor,
  type ActionPriority,
  type ActionType,
  type AgreementStatus,
  type DueStatus,
  type ManagementActionRecord,
} from "@/types/reporting";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import { observationService } from "./observation.service";
import {
  activeFilter,
  closureUpdatesForAction,
  engagementContext,
  findAction,
  findObservation,
  logReporting,
  matches,
  meta,
  refreshRollUp,
  syncActionImplementation,
  today,
  touch,
} from "./reporting.support";

export interface ActionListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  owner?: string;
  department?: string;
  agreementStatus?: string;
  implementationStatus?: string;
  dueStatus?: string;
  riskRating?: string;
  sortBy?: "reference" | "targetDate" | "status" | "updatedAt";
}

export interface ActionListItem extends ManagementActionRecord {
  effectiveTargetDate: string;
  dueStatus: DueStatus;
  observationRef: string;
  observationTitle: string;
  riskRating: string;
  engagementId: string;
  engagementRef: string;
  clientId: string;
  clientName: string;
  updateCount: number;
}

function decorate(row: ManagementActionRecord): ActionListItem {
  syncActionImplementation(row);
  const observation = store.observations.find((item) => item.id === row.observationId);
  const context = engagementContext(observation?.engagementId ?? "");
  return {
    ...row,
    effectiveTargetDate: row.revisedTargetDate || row.originalTargetDate,
    dueStatus: dueStatusFor(row.originalTargetDate, row.revisedTargetDate, row.implementationStatus),
    observationRef: observation?.reference ?? "—",
    observationTitle: observation?.title ?? "—",
    riskRating: observation?.finalRiskRating || "—",
    engagementId: context.engagementId,
    engagementRef: context.engagementRef,
    clientId: context.clientId,
    clientName: context.clientName,
    updateCount: closureUpdatesForAction(row.id).length,
  };
}

function log(
  row: ManagementActionRecord,
  action: string,
  remarks: string,
  previous: string | null,
  actor: Actor,
) {
  const observation = store.observations.find((item) => item.id === row.observationId);
  logReporting({
    module: "Management Actions",
    engagementId: observation?.engagementId ?? "",
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: row.agreementStatus,
    actor,
  });
}

export interface ActionFormValues {
  observationId: string;
  title: string;
  description: string;
  actionType: ActionType;
  actionOwner: string;
  ownerDesignation?: string;
  department: string;
  originalTargetDate: string;
  priority: ActionPriority;
}

export const managementActionService = {
  async list(query: ActionListQuery = {}) {
    let rows = store.managementActions.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.title, row.description, row.actionOwner, row.observationRef) &&
        (!activeFilter(query.clientId) || row.clientId === query.clientId) &&
        (!activeFilter(query.engagementId) || row.engagementId === query.engagementId) &&
        (!activeFilter(query.owner) || row.actionOwner === query.owner) &&
        (!activeFilter(query.department) || row.department === query.department) &&
        (!activeFilter(query.agreementStatus) || row.agreementStatus === query.agreementStatus) &&
        (!activeFilter(query.implementationStatus) || row.implementationStatus === query.implementationStatus) &&
        (!activeFilter(query.dueStatus) || row.dueStatus === query.dueStatus) &&
        (!activeFilter(query.riskRating) || row.riskRating === query.riskRating),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return b.updatedAt.localeCompare(a.updatedAt);
      if (sortBy === "status") return a.implementationStatus.localeCompare(b.implementationStatus);
      if (sortBy === "targetDate") {
        return (a.effectiveTargetDate || "9999").localeCompare(b.effectiveTargetDate || "9999");
      }
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.managementActions.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByObservationId(observationId: string) {
    return delay(
      store.managementActions
        .filter((row) => row.observationId === observationId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.managementActions
        .map(decorate)
        .filter((row) => row.engagementId === engagementId)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: ActionFormValues, actor: Actor) {
    const observation = findObservation(values.observationId);
    if (!values.title.trim() || !values.actionOwner.trim() || !values.originalTargetDate) {
      throw new Error("The action title, owner and target date are all required.");
    }
    const reference = formatId("managementAction", sequences.nextAction()) as ManagementActionId;
    const row: ManagementActionRecord = {
      id: reference,
      reference,
      observationId: observation.id,
      title: values.title,
      description: values.description,
      actionType: values.actionType,
      actionOwner: values.actionOwner,
      ownerDesignation: values.ownerDesignation ?? "",
      department: values.department,
      originalTargetDate: values.originalTargetDate,
      revisedTargetDate: "",
      revisedDateReason: "",
      priority: values.priority,
      auditorAssessment: "",
      agreementStatus: "Draft",
      implementationStatus: "Pending",
      escalated: false,
      escalationDate: "",
      escalationRemarks: "",
      ...meta(actor),
    };
    store.managementActions.push(row);
    log(row, "Management action created", values.title, null, actor);
    refreshRollUp(observation.id);
    return delay(row);
  },

  async update(id: string, values: Partial<ActionFormValues>, actor: Actor) {
    const row = findAction(id);
    if (row.implementationStatus === "Closed") {
      throw new Error(`${row.reference} is closed and can no longer be amended.`);
    }
    if (row.agreementStatus === "Agreed by Auditor") {
      throw new Error(`${row.reference} has been agreed by the auditor; use Revise Target Date instead.`);
    }
    Object.assign(row, values, { id: row.id, reference: row.reference, observationId: row.observationId });
    touch(row, actor);
    log(row, "Management action updated", "Action details amended.", row.agreementStatus, actor);
    return delay(row);
  },

  async setAgreement(id: string, next: AgreementStatus, remarks: string, actor: Actor) {
    const row = findAction(id);
    if (row.agreementStatus === "Agreed by Auditor") {
      throw new Error(`${row.reference} has already been agreed by the auditor.`);
    }
    if (next !== "Agreed by Auditor" && !remarks.trim()) {
      throw new Error("Auditor remarks are required when an action is not agreed.");
    }
    const previous = row.agreementStatus;
    row.agreementStatus = next;
    row.auditorAssessment = remarks;
    touch(row, actor);
    log(row, `Agreement status set to ${next}`, remarks || "Action agreed by the auditor.", previous, actor);
    if (next === "Agreed by Auditor") observationService.maybeAwaitFinalisation(row.observationId, actor);
    refreshRollUp(row.observationId);
    return delay(row);
  },

  async reviseTargetDate(id: string, revisedTargetDate: string, reason: string, actor: Actor) {
    const row = findAction(id);
    if (row.implementationStatus === "Closed") {
      throw new Error(`${row.reference} is closed; its target date can no longer be revised.`);
    }
    if (!revisedTargetDate) throw new Error("A revised target date is required.");
    if (!reason.trim()) throw new Error("A reason is mandatory when revising a target date.");
    const previous = row.revisedTargetDate || row.originalTargetDate;
    row.revisedTargetDate = revisedTargetDate;
    row.revisedDateReason = reason;
    touch(row, actor);
    log(
      row,
      "Target date revised",
      `Target date moved from ${previous} to ${revisedTargetDate}. ${reason}`,
      row.agreementStatus,
      actor,
    );
    return delay(row);
  },

  async escalate(id: string, remarks: string, actor: Actor) {
    const row = findAction(id);
    if (row.implementationStatus === "Closed") throw new Error(`${row.reference} is already closed.`);
    if (!remarks.trim()) throw new Error("Escalation remarks are required.");
    row.escalated = true;
    row.escalationDate = today();
    row.escalationRemarks = remarks;
    touch(row, actor);
    log(row, "Action escalated", remarks, row.agreementStatus, actor);
    return delay(row);
  },

  async withdrawEscalation(id: string, remarks: string, actor: Actor) {
    const row = findAction(id);
    if (!row.escalated) throw new Error(`${row.reference} is not escalated.`);
    if (!remarks.trim()) throw new Error("Remarks are required to withdraw an escalation.");
    row.escalated = false;
    row.escalationRemarks = remarks;
    touch(row, actor);
    log(row, "Escalation withdrawn", remarks, row.agreementStatus, actor);
    return delay(row);
  },
};

export type ManagementActionService = typeof managementActionService;
