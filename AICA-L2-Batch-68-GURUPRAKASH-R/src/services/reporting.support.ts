import type { Actor, ActivityModule } from "@/types/activity";
import type { ObservationRecord, ImplementationRollUp } from "@/types/observation";
import type {
  ImplementationStatus,
  ManagementActionRecord,
  ManagementResponseRecord,
  ClosureUpdateRecord,
  ReportRecord,
} from "@/types/reporting";
import { appendActivity } from "./activity.service";
import { clientNameFor, store } from "./store";

/**
 * Shared lookups, roll-up derivations and activity logging for the Stage 4
 * reporting-and-closure services.
 */

export function nowIso() {
  return new Date().toISOString();
}

export function today() {
  return nowIso().slice(0, 10);
}

export function touch<T extends { updatedAt: string; updatedBy: string }>(row: T, actor: Actor): T {
  row.updatedAt = nowIso();
  row.updatedBy = actor.user;
  return row;
}

export function meta(actor: Actor) {
  const timestamp = nowIso();
  return {
    createdAt: timestamp,
    createdBy: actor.user,
    updatedAt: timestamp,
    updatedBy: actor.user,
    isActive: true,
  };
}

/* ----------------------------- Lookups ----------------------------- */

export function findObservation(id: string): ObservationRecord {
  const row = store.observations.find((item) => item.id === id);
  if (!row) throw new Error(`Observation ${id} was not found.`);
  return row;
}

export function findAction(id: string): ManagementActionRecord {
  const row = store.managementActions.find((item) => item.id === id);
  if (!row) throw new Error(`Management action ${id} was not found.`);
  return row;
}

export function findResponse(id: string): ManagementResponseRecord {
  const row = store.managementResponses.find((item) => item.id === id);
  if (!row) throw new Error(`Management response ${id} was not found.`);
  return row;
}

export function findReport(id: string): ReportRecord {
  const row = store.reports.find((item) => item.id === id);
  if (!row) throw new Error(`Report ${id} was not found.`);
  return row;
}

export function responseForObservation(observationId: string): ManagementResponseRecord | null {
  return store.managementResponses.find((row) => row.observationId === observationId) ?? null;
}

export function actionsForObservation(observationId: string): ManagementActionRecord[] {
  return store.managementActions.filter((row) => row.observationId === observationId);
}

export function closureUpdatesForAction(actionId: string): ClosureUpdateRecord[] {
  return store.closureUpdates
    .filter((row) => row.actionId === actionId)
    .sort((a, b) => a.createdAt.localeCompare(b.createdAt));
}

export function latestClosureUpdate(actionId: string): ClosureUpdateRecord | null {
  const history = closureUpdatesForAction(actionId);
  return history.length ? history[history.length - 1] : null;
}

export function engagementContext(engagementId: string) {
  const engagement = store.engagements.find((item) => item.id === engagementId) ?? null;
  const client = store.clients.find((item) => item.id === engagement?.clientId) ?? null;
  return {
    engagementId: engagement?.id ?? "",
    engagementRef: engagement?.reference ?? "—",
    clientId: client?.id ?? "",
    clientName: client?.legalName ?? "—",
  };
}

/* --------------------------- Roll-up rules -------------------------- */

/** The action's implementation status always follows its latest closure update. */
export function syncActionImplementation(action: ManagementActionRecord): ImplementationStatus {
  const latest = latestClosureUpdate(action.id);
  action.implementationStatus = latest?.implementationStatus ?? "Pending";
  return action.implementationStatus;
}

/**
 * Derives an observation's implementation roll-up from its response, actions
 * and closure history. Never selected by a user.
 */
export function deriveRollUp(observationId: string): ImplementationRollUp {
  const actions = actionsForObservation(observationId);
  const response = responseForObservation(observationId);
  if (actions.length === 0) {
    return response && response.status === "Accepted by Auditor"
      ? "No Action Created"
      : response
        ? "Awaiting Management Response"
        : "No Action Created";
  }
  const statuses = actions.map((action) => syncActionImplementation(action));
  const every = (...allowed: ImplementationStatus[]) =>
    statuses.every((status) => allowed.includes(status));
  if (every("Closed")) return "Closed";
  if (every("Closed", "Risk Accepted")) return "Risk Accepted";
  if (every("Closed", "Risk Accepted", "Implemented")) return "Implemented";
  if (statuses.some((status) => status === "Partly Implemented" || status === "Implemented")) {
    return "Partly Implemented";
  }
  return "Open";
}

/** Recomputes and stores the roll-up for one observation. */
export function refreshRollUp(observationId: string): ObservationRecord | null {
  const observation = store.observations.find((row) => row.id === observationId);
  if (!observation) return null;
  observation.implementationRollUp = deriveRollUp(observationId);
  return observation;
}

/* --------------------------- Activity log --------------------------- */

export interface ReportingLogInput {
  module: ActivityModule;
  engagementId: string;
  reference: string;
  action: string;
  remarks: string;
  previousStatus?: string | null;
  newStatus?: string | null;
  actor: Actor;
}

export function logReporting(input: ReportingLogInput) {
  const context = engagementContext(input.engagementId);
  appendActivity({
    user: input.actor.user,
    role: input.actor.role,
    clientId: context.clientId || null,
    clientName: clientNameFor(context.clientId || null),
    engagementId: context.engagementId || null,
    engagementRef: context.engagementId ? context.engagementRef : null,
    module: input.module,
    recordReference: input.reference,
    action: input.action,
    previousStatus: input.previousStatus ?? null,
    newStatus: input.newStatus ?? null,
    remarks: input.remarks,
  });
}

export function matches(term: string | undefined, ...fields: (string | null | undefined)[]) {
  const needle = term?.trim().toLowerCase();
  if (!needle) return true;
  return fields.some((field) => (field ?? "").toLowerCase().includes(needle));
}

export const ALL = "all";
export const activeFilter = (value?: string) => Boolean(value) && value !== ALL;
