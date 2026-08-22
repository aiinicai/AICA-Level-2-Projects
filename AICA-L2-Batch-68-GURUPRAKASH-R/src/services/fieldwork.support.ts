import { appendActivity } from "./activity.service";
import { clientNameFor, store } from "./store";
import type { Actor, ActivityModule } from "@/types/activity";
import type { EngagementId, ProcedureId, RequirementId, ScopeId } from "@/types/common";
import type {
  ClarificationRecord,
  EvidenceRecord,
  ProcedureRecord,
  RequirementRecord,
  ScopeRecord,
} from "@/types/fieldwork";

/**
 * Shared lookups and activity logging for the Stage 3 fieldwork services.
 * Kept separate so each entity service stays focused on its own rules.
 */

export function nowIso() {
  return new Date().toISOString();
}

export function touch<T extends { updatedAt: string; updatedBy: string }>(row: T, actor: Actor): T {
  row.updatedAt = nowIso();
  row.updatedBy = actor.user;
  return row;
}

/* ----------------------------- Lookups ----------------------------- */

export function findScope(id: string): ScopeRecord {
  const row = store.scopes.find((item) => item.id === id);
  if (!row) throw new Error(`Scope ${id} was not found.`);
  return row;
}

export function findProcedure(id: string): ProcedureRecord {
  const row = store.procedures.find((item) => item.id === id);
  if (!row) throw new Error(`Procedure ${id} was not found.`);
  return row;
}

export function findRequirement(id: string): RequirementRecord {
  const row = store.requirements.find((item) => item.id === id);
  if (!row) throw new Error(`Requirement ${id} was not found.`);
  return row;
}

export function findEvidence(id: string): EvidenceRecord {
  const row = store.evidence.find((item) => item.id === id);
  if (!row) throw new Error(`Evidence ${id} was not found.`);
  return row;
}

export function findClarification(id: string): ClarificationRecord {
  const row = store.clarifications.find((item) => item.id === id);
  if (!row) throw new Error(`Clarification ${id} was not found.`);
  return row;
}

export function engagementOf(engagementId: string) {
  return store.engagements.find((item) => item.id === engagementId) ?? null;
}

/** Engagement id reachable from a scope. */
export function engagementOfScope(scopeId: ScopeId): EngagementId {
  return findScope(scopeId).engagementId;
}

/** Engagement id reachable from a procedure (through its scope). */
export function engagementOfProcedure(procedureId: ProcedureId): EngagementId {
  return engagementOfScope(findProcedure(procedureId).scopeId);
}

export function scopeOfProcedure(procedureId: ProcedureId): ScopeRecord {
  return findScope(findProcedure(procedureId).scopeId);
}

export function evidenceForRequirement(requirementId: RequirementId): EvidenceRecord[] {
  return store.evidence.filter((row) => row.requirementId === requirementId);
}

export function requirementsForProcedure(procedureId: ProcedureId): RequirementRecord[] {
  return store.requirements.filter((row) => row.procedureId === procedureId);
}

export function proceduresForScope(scopeId: ScopeId): ProcedureRecord[] {
  return store.procedures.filter((row) => row.scopeId === scopeId);
}

/** Every procedure id belonging to an engagement, via its scopes. */
export function procedureIdsForEngagement(engagementId: string): string[] {
  const scopeIds = store.scopes
    .filter((row) => row.engagementId === engagementId)
    .map((row) => row.id);
  return store.procedures.filter((row) => scopeIds.includes(row.scopeId)).map((row) => row.id);
}

/* --------------------------- Activity log --------------------------- */

export interface FieldworkLogInput {
  module: ActivityModule;
  engagementId: string;
  reference: string;
  action: string;
  remarks: string;
  previousStatus?: string | null;
  newStatus?: string | null;
  actor: Actor;
}

/** Appends one immutable activity entry, resolving client and engagement context. */
export function logFieldwork(input: FieldworkLogInput) {
  const engagement = engagementOf(input.engagementId);
  appendActivity({
    user: input.actor.user,
    role: input.actor.role,
    clientId: engagement?.clientId ?? null,
    clientName: clientNameFor(engagement?.clientId ?? null),
    engagementId: engagement?.id ?? null,
    engagementRef: engagement?.reference ?? null,
    module: input.module,
    recordReference: input.reference,
    action: input.action,
    previousStatus: input.previousStatus ?? null,
    newStatus: input.newStatus ?? null,
    remarks: input.remarks,
  });
}

/** Case-insensitive contains across the supplied fields. */
export function matches(term: string | undefined, ...fields: (string | null | undefined)[]) {
  const needle = term?.trim().toLowerCase();
  if (!needle) return true;
  return fields.some((field) => (field ?? "").toLowerCase().includes(needle));
}

export function byUpdatedDesc(a: { updatedAt: string }, b: { updatedAt: string }) {
  return b.updatedAt.localeCompare(a.updatedAt);
}
