import type { Actor } from "@/types/activity";
import { formatId, type RequirementId } from "@/types/common";
import {
  completionFor,
  type RequirementFormValues,
  type RequirementRecord,
  type ReviewStatus,
  type SubmissionStatus,
} from "@/types/fieldwork";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  byUpdatedDesc,
  evidenceForRequirement,
  findRequirement,
  logFieldwork,
  matches,
  nowIso,
  scopeOfProcedure,
  touch,
} from "./fieldwork.support";

export interface RequirementListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  procedureId?: string;
  department?: string;
  priority?: string;
  submissionStatus?: string;
  reviewStatus?: string;
  responsiblePerson?: string;
  dueFrom?: string;
  dueTo?: string;
  sortBy?: "reference" | "dueDate" | "priority" | "updatedAt";
}

export interface RequirementListItem extends RequirementRecord {
  procedureRef: string;
  scopeId: string;
  scopeRef: string;
  process: string;
  engagementRef: string;
  clientId: string;
  clientName: string;
  evidenceCount: number;
}

const PRIORITY_ORDER = { Critical: 0, High: 1, Medium: 2, Low: 3 } as const;

function decorate(row: RequirementRecord): RequirementListItem {
  const procedure = store.procedures.find((item) => item.id === row.procedureId);
  const scope = procedure ? store.scopes.find((item) => item.id === procedure.scopeId) : undefined;
  const engagement = store.engagements.find((item) => item.id === row.engagementId);
  const client = store.clients.find((item) => item.id === engagement?.clientId);
  return {
    ...row,
    procedureRef: procedure?.reference ?? "—",
    scopeId: scope?.id ?? "",
    scopeRef: scope?.reference ?? "—",
    process: scope?.process ?? "—",
    engagementRef: engagement?.reference ?? "—",
    clientId: client?.id ?? "",
    clientName: client?.legalName ?? "—",
    evidenceCount: evidenceForRequirement(row.id).length,
  };
}

const ALL = "all";
const active = (value?: string) => value && value !== ALL;

function sync(row: RequirementRecord) {
  row.completionPercentage = completionFor(row.submissionStatus, row.reviewStatus);
  return row;
}

export const requirementService = {
  async list(query: RequirementListQuery = {}) {
    let rows = store.requirements.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.description, row.department, row.responsiblePerson, row.procedureRef) &&
        (!active(query.clientId) || row.clientId === query.clientId) &&
        (!active(query.engagementId) || row.engagementId === query.engagementId) &&
        (!active(query.procedureId) || row.procedureId === query.procedureId) &&
        (!active(query.department) || row.department === query.department) &&
        (!active(query.priority) || row.priority === query.priority) &&
        (!active(query.submissionStatus) || row.submissionStatus === query.submissionStatus) &&
        (!active(query.reviewStatus) || row.reviewStatus === query.reviewStatus) &&
        (!active(query.responsiblePerson) || row.responsiblePerson === query.responsiblePerson) &&
        (!query.dueFrom || row.dueDate >= query.dueFrom) &&
        (!query.dueTo || row.dueDate <= query.dueTo),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return byUpdatedDesc(a, b);
      if (sortBy === "dueDate") return a.dueDate.localeCompare(b.dueDate);
      if (sortBy === "priority") return PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority];
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.requirements.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.requirements
        .filter((row) => row.engagementId === engagementId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async getByProcedureId(procedureId: string) {
    return delay(
      store.requirements.filter((row) => row.procedureId === procedureId).map(decorate),
    );
  },

  async create(values: RequirementFormValues, actor: Actor) {
    const scope = scopeOfProcedure(values.procedureId);
    const reference = formatId("requirement", sequences.nextRequirement()) as RequirementId;
    const timestamp = nowIso();
    const row: RequirementRecord = {
      ...values,
      engagementId: scope.engagementId,
      id: reference,
      reference,
      dateIssued: "",
      submissionStatus: "Draft",
      reviewStatus: "Not Reviewed",
      completionPercentage: 0,
      notApplicableReason: "",
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.requirements.push(row);
    logFieldwork({
      module: "Requirements",
      engagementId: row.engagementId,
      reference,
      action: "Requirement created",
      remarks: row.description.slice(0, 120),
      newStatus: "Draft",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: RequirementFormValues, actor: Actor) {
    const row = findRequirement(id);
    if (row.submissionStatus === "Not Applicable") {
      throw new Error(`${row.reference} is Not Applicable and can no longer be edited.`);
    }
    if (row.dateIssued && values.dueDate && values.dueDate < row.dateIssued) {
      throw new Error(`Due date cannot be earlier than the date issued (${row.dateIssued}).`);
    }
    const scope = scopeOfProcedure(values.procedureId);
    Object.assign(row, values, {
      id: row.id,
      reference: row.reference,
      engagementId: scope.engagementId,
      dateIssued: row.dateIssued,
      submissionStatus: row.submissionStatus,
      reviewStatus: row.reviewStatus,
    });
    sync(row);
    touch(row, actor);
    logFieldwork({
      module: "Requirements",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Requirement updated",
      remarks: "Requirement details amended.",
      previousStatus: row.submissionStatus,
      newStatus: row.submissionStatus,
      actor,
    });
    return delay(row);
  },

  async issue(id: string, actor: Actor) {
    const row = findRequirement(id);
    if (row.submissionStatus !== "Draft") {
      throw new Error(`Only a Draft requirement can be issued. ${row.reference} is ${row.submissionStatus}.`);
    }
    row.dateIssued = nowIso().slice(0, 10);
    if (row.dueDate < row.dateIssued) {
      throw new Error("Due date cannot be earlier than the date issued. Update the due date first.");
    }
    return delay(setSubmission(row, "Issued", "Requirement issued", "Requirement issued to the auditee.", actor));
  },

  async setSubmissionStatus(id: string, next: SubmissionStatus, remarks: string, actor: Actor) {
    const row = findRequirement(id);
    const allowed: Record<SubmissionStatus, SubmissionStatus[]> = {
      Draft: ["Issued"],
      Issued: ["Partially Received", "Received"],
      "Partially Received": ["Received"],
      Received: [],
      "Not Applicable": [],
    };
    if (!allowed[row.submissionStatus].includes(next)) {
      throw new Error(`${row.reference} cannot move from ${row.submissionStatus} to ${next}.`);
    }
    return delay(setSubmission(row, next, `Submission status changed to ${next}`, remarks, actor));
  },

  async setReviewStatus(id: string, next: ReviewStatus, remarks: string, actor: Actor) {
    const row = findRequirement(id);
    const allowed: Record<ReviewStatus, ReviewStatus[]> = {
      "Not Reviewed": ["Under Review"],
      "Under Review": ["Additional Data Required", "Reviewed"],
      "Additional Data Required": ["Under Review"],
      Reviewed: ["Closed"],
      Closed: [],
    };
    if (!allowed[row.reviewStatus].includes(next)) {
      throw new Error(`${row.reference} cannot move review status from ${row.reviewStatus} to ${next}.`);
    }
    if (next === "Under Review" && row.submissionStatus === "Draft") {
      throw new Error("A requirement must be issued before review can begin.");
    }
    if (next === "Reviewed") {
      const linked = evidenceForRequirement(row.id);
      const outstanding = linked.filter((item) => item.reviewStatus !== "Accepted");
      if (linked.length > 0 && outstanding.length > 0) {
        throw new Error(
          `${outstanding.length} linked evidence record(s) are not yet Accepted. Accept all evidence before marking the requirement Reviewed.`,
        );
      }
    }
    return delay(setReview(row, next, `Review status changed to ${next}`, remarks, actor));
  },

  async close(id: string, remarks: string, actor: Actor) {
    const row = findRequirement(id);
    if (row.reviewStatus !== "Reviewed") {
      throw new Error(`Only a Reviewed requirement can be closed. ${row.reference} is ${row.reviewStatus}.`);
    }
    return delay(setReview(row, "Closed", "Requirement closed", remarks, actor));
  },

  /** Manager-only reopen of a closed requirement. */
  async reopen(id: string, reason: string, actor: Actor) {
    const row = findRequirement(id);
    if (row.reviewStatus !== "Closed") {
      throw new Error(`Only a Closed requirement can be reopened. ${row.reference} is ${row.reviewStatus}.`);
    }
    if (actor.role !== "Audit Manager") {
      throw new Error("Only the Audit Manager may reopen a closed requirement.");
    }
    if (!reason.trim()) throw new Error("A reason is required to reopen a requirement.");
    return delay(setReview(row, "Under Review", "Requirement reopened", reason, actor));
  },

  async markNotApplicable(id: string, reason: string, actor: Actor) {
    const row = findRequirement(id);
    if (row.submissionStatus === "Not Applicable") {
      throw new Error(`${row.reference} is already Not Applicable.`);
    }
    if (row.reviewStatus === "Closed") {
      throw new Error(`${row.reference} is closed and cannot be marked Not Applicable.`);
    }
    if (!reason.trim()) throw new Error("A reason is required to mark a requirement Not Applicable.");
    const previous = row.submissionStatus;
    row.submissionStatus = "Not Applicable";
    row.notApplicableReason = reason;
    row.isActive = false;
    sync(row);
    touch(row, actor);
    logFieldwork({
      module: "Requirements",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Requirement marked Not Applicable",
      remarks: reason,
      previousStatus: previous,
      newStatus: "Not Applicable",
      actor,
    });
    return delay(row);
  },

  /** Simulated reminder — logged only, no email or external integration. */
  async sendReminder(id: string, actor: Actor) {
    const row = findRequirement(id);
    if (row.submissionStatus === "Draft") {
      throw new Error("A reminder can only be sent once the requirement has been issued.");
    }
    logFieldwork({
      module: "Requirements",
      engagementId: row.engagementId,
      reference: row.reference,
      action: "Reminder simulated",
      remarks: `Reminder simulated for ${row.responsiblePerson} (due ${row.dueDate}). No email was sent.`,
      previousStatus: row.submissionStatus,
      newStatus: row.submissionStatus,
      actor,
    });
    return delay(row);
  },

  /**
   * Roll-up applied when evidence activity occurs. Used by the evidence
   * service; never lowers a status that is already further along.
   */
  applyEvidenceRollUp(
    requirementId: string,
    change: { submission?: SubmissionStatus; review?: ReviewStatus },
    action: string,
    remarks: string,
    actor: Actor,
  ) {
    const row = findRequirement(requirementId);
    let changed = false;
    if (
      change.submission === "Partially Received" &&
      (row.submissionStatus === "Issued" || row.submissionStatus === "Draft")
    ) {
      row.submissionStatus = "Partially Received";
      changed = true;
    }
    if (change.review && row.reviewStatus !== change.review && row.reviewStatus !== "Closed") {
      if (!(change.review === "Under Review" && row.reviewStatus === "Reviewed")) {
        row.reviewStatus = change.review;
        changed = true;
      }
    }
    if (!changed) return row;
    sync(row);
    touch(row, actor);
    logFieldwork({
      module: "Requirements",
      engagementId: row.engagementId,
      reference: row.reference,
      action,
      remarks,
      previousStatus: row.submissionStatus,
      newStatus: row.reviewStatus,
      actor,
    });
    return row;
  },
};

function setSubmission(
  row: RequirementRecord,
  next: SubmissionStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.submissionStatus;
  row.submissionStatus = next;
  sync(row);
  touch(row, actor);
  logFieldwork({
    module: "Requirements",
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

function setReview(
  row: RequirementRecord,
  next: ReviewStatus,
  action: string,
  remarks: string,
  actor: Actor,
) {
  const previous = row.reviewStatus;
  row.reviewStatus = next;
  sync(row);
  touch(row, actor);
  logFieldwork({
    module: "Requirements",
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

export type RequirementService = typeof requirementService;
