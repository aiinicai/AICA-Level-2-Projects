import type { Actor } from "@/types/activity";
import { formatId, type EvidenceId } from "@/types/common";
import type {
  AuditResult,
  EvidenceFormValues,
  EvidenceRecord,
  EvidenceReviewStatus,
} from "@/types/fieldwork";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import {
  byUpdatedDesc,
  evidenceForRequirement,
  findEvidence,
  findRequirement,
  logFieldwork,
  matches,
  nowIso,
  touch,
} from "./fieldwork.support";
import { requirementService } from "./requirement.service";

export interface EvidenceListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  requirementId?: string;
  reviewStatus?: string;
  auditResult?: string;
  reviewer?: string;
  sortBy?: "reference" | "submissionDate" | "reviewStatus" | "updatedAt";
}

export interface EvidenceListItem extends EvidenceRecord {
  requirementRef: string;
  requirementDescription: string;
  procedureRef: string;
  scopeRef: string;
  engagementId: string;
  engagementRef: string;
  clientId: string;
  clientName: string;
}

function decorate(row: EvidenceRecord): EvidenceListItem {
  const requirement = store.requirements.find((item) => item.id === row.requirementId);
  const procedure = store.procedures.find((item) => item.id === requirement?.procedureId);
  const scope = store.scopes.find((item) => item.id === procedure?.scopeId);
  const engagement = store.engagements.find((item) => item.id === requirement?.engagementId);
  const client = store.clients.find((item) => item.id === engagement?.clientId);
  return {
    ...row,
    requirementRef: requirement?.reference ?? "—",
    requirementDescription: requirement?.description ?? "—",
    procedureRef: procedure?.reference ?? "—",
    scopeRef: scope?.reference ?? "—",
    engagementId: engagement?.id ?? "",
    engagementRef: engagement?.reference ?? "—",
    clientId: client?.id ?? "",
    clientName: client?.legalName ?? "—",
  };
}

const ALL = "all";
const active = (value?: string) => value && value !== ALL;

export const evidenceService = {
  async list(query: EvidenceListQuery = {}) {
    let rows = store.evidence.map(decorate);
    rows = rows.filter(
      (row) =>
        matches(query.search, row.reference, row.fileName, row.requirementRef, row.submittedBy, row.documentCategory) &&
        (!active(query.clientId) || row.clientId === query.clientId) &&
        (!active(query.engagementId) || row.engagementId === query.engagementId) &&
        (!active(query.requirementId) || row.requirementId === query.requirementId) &&
        (!active(query.reviewStatus) || row.reviewStatus === query.reviewStatus) &&
        (!active(query.auditResult) || row.auditResult === query.auditResult) &&
        (!active(query.reviewer) || row.assignedReviewer === query.reviewer),
    );
    const sortBy = query.sortBy ?? "reference";
    rows.sort((a, b) => {
      if (sortBy === "updatedAt") return byUpdatedDesc(a, b);
      if (sortBy === "submissionDate") return b.submissionDate.localeCompare(a.submissionDate);
      if (sortBy === "reviewStatus") return a.reviewStatus.localeCompare(b.reviewStatus);
      return a.reference.localeCompare(b.reference);
    });
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.evidence.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByRequirementId(requirementId: string) {
    return delay(
      store.evidence
        .filter((row) => row.requirementId === requirementId)
        .map(decorate)
        .sort((a, b) => a.version - b.version),
    );
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.evidence
        .map(decorate)
        .filter((row) => row.engagementId === engagementId)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  async create(values: EvidenceFormValues, actor: Actor) {
    const requirement = findRequirement(values.requirementId);
    const reference = formatId("evidence", sequences.nextEvidence()) as EvidenceId;
    const timestamp = nowIso();
    const row: EvidenceRecord = {
      ...values,
      id: reference,
      reference,
      version: 1,
      supersedes: null,
      reviewStatus: "Awaiting Review",
      auditResult: "Not Assessed",
      reviewRemarks: "",
      reviewedDate: "",
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.evidence.push(row);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference,
      action: "Evidence added",
      remarks: `${row.fileName} submitted against ${requirement.reference}.`,
      newStatus: "Awaiting Review",
      actor,
    });
    // Roll-up: any submitted evidence moves the requirement to Partially Received.
    requirementService.applyEvidenceRollUp(
      requirement.id,
      { submission: "Partially Received" },
      "Submission status changed to Partially Received",
      `Evidence ${reference} received.`,
      actor,
    );
    return delay(row);
  },

  /**
   * Creates the next version of an existing evidence record. The earlier
   * version is retained unchanged — version history is never overwritten.
   */
  async addRevision(id: string, values: Partial<EvidenceFormValues>, actor: Actor) {
    const previous = findEvidence(id);
    const requirement = findRequirement(previous.requirementId);
    const siblings = evidenceForRequirement(previous.requirementId);
    const nextVersion = Math.max(...siblings.map((item) => item.version)) + 1;
    const reference = formatId("evidence", sequences.nextEvidence()) as EvidenceId;
    const timestamp = nowIso();
    const row: EvidenceRecord = {
      ...previous,
      ...values,
      id: reference,
      reference,
      version: nextVersion,
      supersedes: previous.reference,
      reviewStatus: "Awaiting Review",
      auditResult: "Not Assessed",
      reviewRemarks: "",
      reviewedDate: "",
      submissionDate: values.submissionDate || timestamp.slice(0, 10),
      createdAt: timestamp,
      createdBy: actor.user,
      updatedAt: timestamp,
      updatedBy: actor.user,
      isActive: true,
    };
    store.evidence.push(row);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference,
      action: "Evidence revised",
      remarks: `Version ${nextVersion} created, superseding ${previous.reference}.`,
      newStatus: "Awaiting Review",
      actor,
    });
    return delay(row);
  },

  async update(id: string, values: Partial<EvidenceFormValues>, actor: Actor) {
    const row = findEvidence(id);
    const requirement = findRequirement(row.requirementId);
    Object.assign(row, values, { id: row.id, reference: row.reference, version: row.version });
    touch(row, actor);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference: row.reference,
      action: "Evidence updated",
      remarks: "Evidence metadata amended.",
      previousStatus: row.reviewStatus,
      newStatus: row.reviewStatus,
      actor,
    });
    return delay(row);
  },

  async startReview(id: string, actor: Actor) {
    const row = findEvidence(id);
    if (row.reviewStatus !== "Awaiting Review") {
      throw new Error(`${row.reference} is already under review (${row.reviewStatus}).`);
    }
    const requirement = findRequirement(row.requirementId);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference: row.reference,
      action: "Review started",
      remarks: `Review commenced by ${actor.user}.`,
      previousStatus: row.reviewStatus,
      newStatus: row.reviewStatus,
      actor,
    });
    requirementService.applyEvidenceRollUp(
      requirement.id,
      { review: "Under Review" },
      "Review status changed to Under Review",
      `Review started on evidence ${row.reference}.`,
      actor,
    );
    return delay(row);
  },

  /** Records the reviewer's conclusion. Review status and audit result stay separate. */
  async recordReview(
    id: string,
    input: { reviewStatus: EvidenceReviewStatus; auditResult: AuditResult; reviewRemarks: string },
    actor: Actor,
  ) {
    const row = findEvidence(id);
    if (row.reviewStatus === "Accepted") {
      throw new Error(`${row.reference} has been accepted and can no longer be re-reviewed.`);
    }
    if (input.reviewStatus === "Accepted") {
      throw new Error("Use the Accept action to accept evidence.");
    }
    const requirement = findRequirement(row.requirementId);
    const previous = row.reviewStatus;
    row.reviewStatus = input.reviewStatus;
    row.auditResult = input.auditResult;
    row.reviewRemarks = input.reviewRemarks;
    row.reviewedDate = nowIso().slice(0, 10);
    touch(row, actor);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference: row.reference,
      action: "Review completed",
      remarks: `${input.reviewRemarks} (Audit result: ${input.auditResult})`,
      previousStatus: previous,
      newStatus: input.reviewStatus,
      actor,
    });
    requirementService.applyEvidenceRollUp(
      requirement.id,
      { review: "Under Review" },
      "Review status changed to Under Review",
      `Evidence ${row.reference} reviewed.`,
      actor,
    );
    return delay(row);
  },

  /**
   * Requests a revision: places a next-version placeholder and moves the parent
   * requirement to Additional Data Required.
   */
  async requestRevision(id: string, reason: string, actor: Actor) {
    const row = findEvidence(id);
    if (row.reviewStatus === "Accepted") {
      throw new Error(`${row.reference} has been accepted; a revision cannot be requested.`);
    }
    if (!reason.trim()) throw new Error("A reason is required when requesting a revision.");
    const requirement = findRequirement(row.requirementId);
    const previous = row.reviewStatus;
    row.reviewStatus = "Additional Data Required";
    row.reviewRemarks = reason;
    row.reviewedDate = nowIso().slice(0, 10);
    touch(row, actor);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference: row.reference,
      action: "Revision requested",
      remarks: reason,
      previousStatus: previous,
      newStatus: "Additional Data Required",
      actor,
    });
    // Next-version placeholder awaiting the auditee's resubmission.
    const placeholder = await this.addRevision(
      row.id,
      {
        fileName: `${row.fileName.replace(/\.[^.]+$/, "")}-revision-pending`,
        auditeeRemarks: `Revision requested: ${reason}`,
        submissionDate: "",
      },
      actor,
    );
    requirementService.applyEvidenceRollUp(
      requirement.id,
      { review: "Additional Data Required" },
      "Review status changed to Additional Data Required",
      `Revision requested on evidence ${row.reference}.`,
      actor,
    );
    return delay({ evidence: row, placeholder });
  },

  /** Acceptance requires a Satisfactory review; an exception may still be recorded. */
  async accept(id: string, remarks: string, actor: Actor) {
    const row = findEvidence(id);
    if (row.reviewStatus !== "Satisfactory") {
      throw new Error(
        `Evidence must be marked Satisfactory before acceptance. ${row.reference} is ${row.reviewStatus}.`,
      );
    }
    const requirement = findRequirement(row.requirementId);
    const previous = row.reviewStatus;
    row.reviewStatus = "Accepted";
    row.reviewRemarks = remarks || row.reviewRemarks;
    row.reviewedDate = nowIso().slice(0, 10);
    touch(row, actor);
    logFieldwork({
      module: "Evidence",
      engagementId: requirement.engagementId,
      reference: row.reference,
      action: "Evidence accepted",
      remarks: `${remarks} (Audit result retained: ${row.auditResult})`,
      previousStatus: previous,
      newStatus: "Accepted",
      actor,
    });
    return delay(row);
  },
};

export type EvidenceService = typeof evidenceService;
