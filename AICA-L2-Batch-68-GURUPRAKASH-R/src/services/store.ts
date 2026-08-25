import { ACTIVITY_SEED } from "@/data/activity.mock";
import { CLIENT_SEED } from "@/data/client.mock";
import { ENGAGEMENT_SEED } from "@/data/engagement.mock";
import {
  CLARIFICATION_SEED,
  EVIDENCE_SEED,
  PROCEDURE_SEED,
  REQUIREMENT_SEED,
  SCOPE_SEED,
} from "@/data/fieldwork.mock";
import {
  ACTION_SEED,
  CLOSURE_SEED,
  OBSERVATION_SEED,
  REPORT_SEED,
  RESPONSE_SEED,
} from "@/data/reporting.mock";
import type { ActivityRecord } from "@/types/activity";
import type { ClientRecord } from "@/types/client";
import type { EngagementRecord } from "@/types/engagement";
import type {
  ClarificationRecord,
  EvidenceRecord,
  ProcedureRecord,
  RequirementRecord,
  ScopeRecord,
} from "@/types/fieldwork";
import type { ObservationRecord } from "@/types/observation";
import type {
  ClosureUpdateRecord,
  ManagementActionRecord,
  ManagementResponseRecord,
  ReportRecord,
} from "@/types/reporting";
import { parseIdSequence } from "@/types/common";

/**
 * Single in-memory store shared by the mock services. Keeping the arrays here
 * avoids circular imports between the entity services, and gives one place to
 * swap for REST calls later.
 */
export const store = {
  clients: CLIENT_SEED.map((client) => ({ ...client })) as ClientRecord[],
  engagements: ENGAGEMENT_SEED.map((engagement) => ({ ...engagement })) as EngagementRecord[],
  activity: ACTIVITY_SEED.map((entry) => ({ ...entry })) as ActivityRecord[],
  scopes: SCOPE_SEED.map((row) => ({ ...row })) as ScopeRecord[],
  procedures: PROCEDURE_SEED.map((row) => ({ ...row })) as ProcedureRecord[],
  requirements: REQUIREMENT_SEED.map((row) => ({ ...row })) as RequirementRecord[],
  evidence: EVIDENCE_SEED.map((row) => ({ ...row })) as EvidenceRecord[],
  clarifications: CLARIFICATION_SEED.map((row) => ({ ...row })) as ClarificationRecord[],
  observations: OBSERVATION_SEED.map((row) => ({ ...row })) as ObservationRecord[],
  managementResponses: RESPONSE_SEED.map((row) => ({ ...row })) as ManagementResponseRecord[],
  managementActions: ACTION_SEED.map((row) => ({ ...row })) as ManagementActionRecord[],
  closureUpdates: CLOSURE_SEED.map((row) => ({ ...row })) as ClosureUpdateRecord[],
  reports: REPORT_SEED.map((row) => ({ ...row })) as ReportRecord[],
};

function nextSequence(ids: string[]): number {
  const highest = ids.reduce((max, id) => Math.max(max, parseIdSequence(id) ?? 0), 0);
  return highest + 1;
}

export const sequences = {
  nextClient: () => nextSequence(store.clients.map((client) => client.id)),
  nextEngagement: () => nextSequence(store.engagements.map((engagement) => engagement.id)),
  nextScope: () => nextSequence(store.scopes.map((row) => row.id)),
  nextProcedure: () => nextSequence(store.procedures.map((row) => row.id)),
  nextRequirement: () => nextSequence(store.requirements.map((row) => row.id)),
  nextEvidence: () => nextSequence(store.evidence.map((row) => row.id)),
  nextClarification: () => nextSequence(store.clarifications.map((row) => row.id)),
  nextObservation: () => nextSequence(store.observations.map((row) => row.id)),
  nextResponse: () => nextSequence(store.managementResponses.map((row) => row.id)),
  nextAction: () => nextSequence(store.managementActions.map((row) => row.id)),
  nextClosureUpdate: () => nextSequence(store.closureUpdates.map((row) => row.id)),
  nextReport: () => nextSequence(store.reports.map((row) => row.id)),
};


export function clientNameFor(clientId: string | null): string | null {
  if (!clientId) return null;
  return store.clients.find((client) => client.id === clientId)?.legalName ?? null;
}
