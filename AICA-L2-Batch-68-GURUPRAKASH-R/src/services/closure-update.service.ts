import type { Actor } from "@/types/activity";
import { formatId, type ClosureUpdateId } from "@/types/common";
import type {
  ClosureEvidenceMeta,
  ClosureUpdateRecord,
  ImplementationStatus,
} from "@/types/reporting";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  activeFilter,
  closureUpdatesForAction,
  engagementContext,
  findAction,
  logReporting,
  matches,
  meta,
  refreshRollUp,
  syncActionImplementation,
  today,
  touch,
} from "./reporting.support";

/**
 * Closure tracking. Updates are append-only: an update is never edited once the
 * auditor has verified it, and nothing is ever deleted.
 */

export interface ClosureListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  actionId?: string;
  implementationStatus?: string;
  verification?: "verified" | "pending" | "all";
}

export interface ClosureListItem extends ClosureUpdateRecord {
  actionRef: string;
  actionTitle: string;
  actionOwner: string;
  observationRef: string;
  engagementId: string;
  engagementRef: string;
  clientId: string;
  clientName: string;
  verified: boolean;
}

function decorate(row: ClosureUpdateRecord): ClosureListItem {
  const action = store.managementActions.find((item) => item.id === row.actionId);
  const observation = store.observations.find((item) => item.id === action?.observationId);
  const context = engagementContext(observation?.engagementId ?? "");
  return {
    ...row,
    actionRef: action?.reference ?? "—",
    actionTitle: action?.title ?? "—",
    actionOwner: action?.actionOwner ?? "—",
    observationRef: observation?.reference ?? "—",
    engagementId: context.engagementId,
    engagementRef: context.engagementRef,
    clientId: context.clientId,
    clientName: context.clientName,
    verified: Boolean(row.auditorVerification),
  };
}

function log(row: ClosureUpdateRecord, action: string, remarks: string, previous: string | null, actor: Actor) {
  const parent = store.managementActions.find((item) => item.id === row.actionId);
  const observation = store.observations.find((item) => item.id === parent?.observationId);
  logReporting({
    module: "Closure Tracking",
    engagementId: observation?.engagementId ?? "",
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: row.implementationStatus,
    actor,
  });
}

export interface ClosureUpdateInput {
  updateDate: string;
  updatedByPerson: string;
  managementUpdate: string;
  implementationStatus: Extract<
    ImplementationStatus,
    "Update Received" | "Partly Implemented" | "Implemented"
  >;
  closureEvidence?: ClosureEvidenceMeta | null;
}

export interface VerificationInput {
  auditorVerification: string;
  closureConclusion: string;
  implementationStatus: Extract<
    ImplementationStatus,
    "Partly Implemented" | "Implemented" | "Risk Accepted" | "Closed"
  >;
  reopenReason?: string;
  riskAcceptanceNote?: string;
}

export const closureUpdateService = {
  async list(query: ClosureListQuery = {}) {
    const rows = store.closureUpdates
      .map(decorate)
      .filter(
        (row) =>
          matches(query.search, row.reference, row.actionRef, row.actionTitle, row.managementUpdate, row.updatedByPerson) &&
          (!activeFilter(query.clientId) || row.clientId === query.clientId) &&
          (!activeFilter(query.engagementId) || row.engagementId === query.engagementId) &&
          (!activeFilter(query.actionId) || row.actionId === query.actionId) &&
          (!activeFilter(query.implementationStatus) || row.implementationStatus === query.implementationStatus) &&
          (!query.verification ||
            query.verification === "all" ||
            (query.verification === "verified" ? row.verified : !row.verified)),
      )
      .sort((a, b) => b.updateDate.localeCompare(a.updateDate) || b.reference.localeCompare(a.reference));
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getByActionId(actionId: string) {
    return delay(closureUpdatesForAction(actionId).map(decorate));
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.closureUpdates
        .map(decorate)
        .filter((row) => row.engagementId === engagementId)
        .sort((a, b) => b.updateDate.localeCompare(a.updateDate)),
    );
  },

  /** Management-side progress update. Appends a new immutable record. */
  async addUpdate(actionId: string, input: ClosureUpdateInput, actor: Actor) {
    const action = findAction(actionId);
    if (action.agreementStatus !== "Agreed by Auditor") {
      throw new Error(
        `${action.reference} has not yet been agreed by the auditor, so closure updates cannot be recorded.`,
      );
    }
    if (action.implementationStatus === "Closed") {
      throw new Error(`${action.reference} is closed. Reopen the action before recording a further update.`);
    }
    if (!input.managementUpdate.trim() || !input.updatedByPerson.trim() || !input.updateDate) {
      throw new Error("The update narrative, the person reporting it and the update date are all required.");
    }
    const reference = formatId("closureUpdate", sequences.nextClosureUpdate()) as ClosureUpdateId;
    const row: ClosureUpdateRecord = {
      id: reference,
      reference,
      actionId: action.id,
      updateDate: input.updateDate,
      updatedByPerson: input.updatedByPerson,
      managementUpdate: input.managementUpdate,
      closureEvidence: input.closureEvidence ?? null,
      auditorVerification: "",
      auditorVerificationDate: "",
      implementationStatus: input.implementationStatus,
      closureConclusion: "",
      reopenReason: "",
      riskAcceptanceNote: "",
      escalationNote: "",
      ...meta(actor),
    };
    store.closureUpdates.push(row);
    const previous = action.implementationStatus;
    syncActionImplementation(action);
    touch(action, actor);
    log(row, "Closure update recorded", input.managementUpdate, previous, actor);
    refreshRollUp(action.observationId);
    return delay(row);
  },

  /** Auditor verification of the latest update. Verification is written once. */
  async verify(updateId: string, input: VerificationInput, actor: Actor) {
    const row = store.closureUpdates.find((item) => item.id === updateId);
    if (!row) throw new Error(`Closure update ${updateId} was not found.`);
    if (row.auditorVerification) {
      throw new Error(`${row.reference} has already been verified. Record a fresh update instead.`);
    }
    if (!input.auditorVerification.trim()) throw new Error("Verification remarks are required.");
    if (input.implementationStatus === "Closed" && !input.closureConclusion.trim()) {
      throw new Error("A closure conclusion is required to close a management action.");
    }
    if (input.implementationStatus === "Risk Accepted" && !input.riskAcceptanceNote?.trim()) {
      throw new Error("A rationale is required when the residual risk is accepted.");
    }
    if (input.implementationStatus === "Partly Implemented" && !input.reopenReason?.trim()) {
      throw new Error("A reason is required when an update is sent back as only partly implemented.");
    }
    const action = findAction(row.actionId);
    const previous = action.implementationStatus;
    row.auditorVerification = input.auditorVerification;
    row.auditorVerificationDate = today();
    row.closureConclusion = input.closureConclusion;
    row.reopenReason = input.reopenReason ?? "";
    row.riskAcceptanceNote = input.riskAcceptanceNote ?? "";
    row.implementationStatus = input.implementationStatus;
    touch(row, actor);
    syncActionImplementation(action);
    touch(action, actor);
    log(row, "Closure update verified", input.auditorVerification, previous, actor);
    refreshRollUp(action.observationId);
    return delay(row);
  },

  /** Reopening a closed action appends a new record rather than editing history. */
  async reopenAction(actionId: string, reason: string, actor: Actor) {
    const action = findAction(actionId);
    if (action.implementationStatus !== "Closed") {
      throw new Error(`${action.reference} is not closed.`);
    }
    if (!reason.trim()) throw new Error("A reason is required to reopen a closed action.");
    const reference = formatId("closureUpdate", sequences.nextClosureUpdate()) as ClosureUpdateId;
    const row: ClosureUpdateRecord = {
      id: reference,
      reference,
      actionId: action.id,
      updateDate: today(),
      updatedByPerson: actor.user,
      managementUpdate: "Action reopened by the audit team.",
      closureEvidence: null,
      auditorVerification: reason,
      auditorVerificationDate: today(),
      implementationStatus: "Partly Implemented",
      closureConclusion: "",
      reopenReason: reason,
      riskAcceptanceNote: "",
      escalationNote: "",
      ...meta(actor),
    };
    store.closureUpdates.push(row);
    syncActionImplementation(action);
    touch(action, actor);
    log(row, "Action reopened", reason, "Closed", actor);
    refreshRollUp(action.observationId);
    return delay(row);
  },
};

export type ClosureUpdateService = typeof closureUpdateService;
