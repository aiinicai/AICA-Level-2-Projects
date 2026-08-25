import type { Actor } from "@/types/activity";
import { formatId, type ObservationId, type ReportId } from "@/types/common";
import type { ObservationRecord } from "@/types/observation";
import type { ReportRecord, ReportStatus } from "@/types/reporting";
import { delay } from "./mock.utils";
import { sequences, store } from "./store";
import { observationService } from "./observation.service";
import {
  activeFilter,
  actionsForObservation,
  engagementContext,
  findReport,
  logReporting,
  matches,
  meta,
  responseForObservation,
  today,
  touch,
} from "./reporting.support";

export interface ReportListQuery {
  search?: string;
  clientId?: string;
  engagementId?: string;
  status?: string;
}

export interface ReportListItem extends ReportRecord {
  engagementRef: string;
  clientId: string;
  clientName: string;
  observationCount: number;
}

export interface ReportObservationLine {
  observation: ObservationRecord;
  responseSummary: string;
  responseAccepted: boolean;
  actionSummary: string[];
}

function decorate(row: ReportRecord): ReportListItem {
  const context = engagementContext(row.engagementId);
  return {
    ...row,
    engagementRef: context.engagementRef,
    clientId: context.clientId,
    clientName: context.clientName,
    observationCount: row.observationIds.length,
  };
}

function log(row: ReportRecord, action: string, remarks: string, previous: ReportStatus | null, actor: Actor) {
  logReporting({
    module: "Final Reporting",
    engagementId: row.engagementId,
    reference: row.reference,
    action,
    remarks,
    previousStatus: previous,
    newStatus: row.status,
    actor,
  });
}

export interface ReportFormValues {
  engagementId: ReportRecord["engagementId"];
  title: string;
  reportPeriod: string;
  addressee: string;
  issueDate: string;
  executiveSummary: string;
  overallConclusion: string;
  preparedBy: string;
}

export const reportService = {
  async list(query: ReportListQuery = {}) {
    const rows = store.reports
      .map(decorate)
      .filter(
        (row) =>
          matches(query.search, row.reference, row.title, row.addressee, row.engagementRef, row.clientName) &&
          (!activeFilter(query.clientId) || row.clientId === query.clientId) &&
          (!activeFilter(query.engagementId) || row.engagementId === query.engagementId) &&
          (!activeFilter(query.status) || row.status === query.status),
      )
      .sort((a, b) => a.reference.localeCompare(b.reference));
    return delay({ items: rows, total: rows.length, page: 1, pageSize: rows.length });
  },

  async getById(id: string) {
    const row = store.reports.find((item) => item.id === id) ?? null;
    return delay(row ? decorate(row) : null);
  },

  async getByEngagementId(engagementId: string) {
    return delay(
      store.reports
        .filter((row) => row.engagementId === engagementId)
        .map(decorate)
        .sort((a, b) => a.reference.localeCompare(b.reference)),
    );
  },

  /** Observations eligible for inclusion: finalised and not dropped. */
  async eligibleObservations(engagementId: string) {
    return delay(
      store.observations.filter(
        (row) =>
          row.engagementId === engagementId &&
          (row.status === "Finalised" || row.status === "Included in Report" || row.status === "Reported"),
      ),
    );
  },

  /** Assembled preview content for the report document. */
  async preview(id: string): Promise<ReportObservationLine[]> {
    const report = findReport(id);
    const lines = report.observationIds
      .map((observationId) => store.observations.find((row) => row.id === observationId))
      .filter((row): row is ObservationRecord => Boolean(row))
      .map((observation) => {
        const response = responseForObservation(observation.id);
        return {
          observation,
          responseSummary: response?.managementResponse || "No management response recorded.",
          responseAccepted: response?.status === "Accepted by Auditor",
          actionSummary: actionsForObservation(observation.id).map(
            (action) =>
              `${action.reference} — ${action.title} (${action.actionOwner}, target ${action.revisedTargetDate || action.originalTargetDate})`,
          ),
        };
      });
    return delay(lines);
  },

  async create(values: ReportFormValues, actor: Actor) {
    const reference = formatId("report", sequences.nextReport()) as ReportId;
    const row: ReportRecord = {
      id: reference,
      reference,
      engagementId: values.engagementId,
      title: values.title,
      reportPeriod: values.reportPeriod,
      addressee: values.addressee,
      issueDate: values.issueDate,
      executiveSummary: values.executiveSummary,
      overallConclusion: values.overallConclusion,
      status: "Draft",
      observationIds: [],
      preparedBy: values.preparedBy || actor.user,
      reviewedBy: "",
      approvedBy: "",
      unacceptedResponseReason: "",
      ...meta(actor),
    };
    store.reports.push(row);
    log(row, "Report created", values.title, null, actor);
    return delay(row);
  },

  async update(id: string, values: Partial<ReportFormValues>, actor: Actor) {
    const row = findReport(id);
    if (row.status === "Finalised") {
      throw new Error(`${row.reference} has been finalised and can no longer be edited.`);
    }
    Object.assign(row, values, { id: row.id, reference: row.reference, status: row.status });
    touch(row, actor);
    log(row, "Report updated", "Report details amended.", row.status, actor);
    return delay(row);
  },

  async setObservations(id: string, observationIds: string[], actor: Actor) {
    const row = findReport(id);
    if (row.status === "Finalised") {
      throw new Error(`${row.reference} has been finalised; its contents can no longer be changed.`);
    }
    const eligible = new Set(
      store.observations
        .filter(
          (item) =>
            item.engagementId === row.engagementId &&
            (item.status === "Finalised" || item.status === "Included in Report" || item.status === "Reported"),
        )
        .map((item) => item.id),
    );
    const rejected = observationIds.filter((observationId) => !eligible.has(observationId as ObservationId));
    if (rejected.length) {
      throw new Error(`Only finalised observations can be included. Not eligible: ${rejected.join(", ")}.`);
    }
    row.observationIds = observationIds as ObservationId[];
    touch(row, actor);
    log(
      row,
      "Report contents updated",
      `${observationIds.length} observation(s) selected for inclusion.`,
      row.status,
      actor,
    );
    return delay(row);
  },

  async submitForReview(id: string, actor: Actor) {
    const row = findReport(id);
    if (row.status !== "Draft") throw new Error(`Only a Draft report can be submitted for review. ${row.reference} is ${row.status}.`);
    if (!row.observationIds.length) throw new Error("Include at least one finalised observation before submitting the report.");
    if (!row.executiveSummary.trim() || !row.overallConclusion.trim()) {
      throw new Error("The executive summary and overall conclusion are required before review.");
    }
    const previous = row.status;
    row.status = "Under Review";
    touch(row, actor);
    log(row, "Report submitted for review", "Draft report submitted to the Audit Manager.", previous, actor);
    return delay(row);
  },

  async sendBackToDraft(id: string, remarks: string, actor: Actor) {
    const row = findReport(id);
    if (row.status !== "Under Review") throw new Error(`${row.reference} is ${row.status} and cannot be sent back.`);
    if (!remarks.trim()) throw new Error("Review comments are required when returning a report to draft.");
    const previous = row.status;
    row.status = "Draft";
    row.reviewedBy = actor.user;
    touch(row, actor);
    log(row, "Report returned to draft", remarks, previous, actor);
    return delay(row);
  },

  /**
   * Finalisation locks the report and marks every included observation as
   * Reported. Observations without an accepted response require an explicit
   * Audit Manager justification.
   */
  async finalise(id: string, remarks: string, actor: Actor, unacceptedResponseReason = "") {
    const row = findReport(id);
    if (row.status !== "Under Review") {
      throw new Error(`Only a report Under Review can be finalised. ${row.reference} is ${row.status}.`);
    }
    if (!remarks.trim()) throw new Error("Approval remarks are required to finalise a report.");
    const withoutAcceptedResponse = row.observationIds.filter((observationId) => {
      const response = responseForObservation(observationId);
      return !response || response.status !== "Accepted by Auditor";
    });
    if (withoutAcceptedResponse.length && !unacceptedResponseReason.trim()) {
      throw new Error(
        `These observations have no accepted management response: ${withoutAcceptedResponse.join(", ")}. A justification is required to report them.`,
      );
    }
    const previous = row.status;
    row.status = "Finalised";
    row.approvedBy = actor.user;
    row.issueDate = row.issueDate || today();
    row.unacceptedResponseReason = unacceptedResponseReason;
    touch(row, actor);
    log(row, "Report finalised", remarks, previous, actor);
    row.observationIds.forEach((observationId) =>
      observationService.markReported(observationId, row.reference, actor),
    );
    return delay(row);
  },
};

export type ReportService = typeof reportService;
