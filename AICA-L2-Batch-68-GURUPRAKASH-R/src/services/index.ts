/**
 * Service registry. Components import from here only, never from a concrete
 * implementation, so the mock layer can be swapped for REST services later.
 *
 * Stage 2 note: clients and engagements now use entity-specific service
 * interfaces (no generic CRUD contract, and no permanent delete). The generic
 * EntityService remains for the modules still awaiting their own stage.
 */
import { API_CONFIG } from "@/config/api";
import { activityService } from "./activity.service";
import { clarificationService } from "./clarification.service";
import { clientService } from "./client.service";
import { closureUpdateService } from "./closure-update.service";
import { dashboardService } from "./dashboard.service";
import { engagementService } from "./engagement.service";
import { evidenceService } from "./evidence.service";
import { managementActionService } from "./management-action.service";
import { managementResponseService } from "./management-response.service";
import { observationService } from "./observation.service";
import { procedureService } from "./procedure.service";
import { reportService } from "./report.service";
import { requirementService } from "./requirement.service";
import { scopeService } from "./scope.service";
import type { ServiceMode } from "./service.types";

export const serviceMode: ServiceMode = API_CONFIG.useRemoteApi ? "rest" : "mock";

export const services = {
  dashboard: dashboardService,
  clients: clientService,
  engagements: engagementService,
  activity: activityService,
  scopes: scopeService,
  procedures: procedureService,
  requirements: requirementService,
  evidence: evidenceService,
  clarifications: clarificationService,
  observations: observationService,
  managementResponses: managementResponseService,
  managementActions: managementActionService,
  closureUpdates: closureUpdateService,
  reports: reportService,
} as const;

export type Services = typeof services;
export * from "./service.types";
export type { ClientListItem, ClientListQuery } from "./client.service";
export type { EngagementListItem, EngagementListQuery } from "./engagement.service";
export type { ScopeListItem, ScopeListQuery } from "./scope.service";
export type { ProcedureListItem, ProcedureListQuery } from "./procedure.service";
export type { RequirementListItem, RequirementListQuery } from "./requirement.service";
export type { EvidenceListItem, EvidenceListQuery } from "./evidence.service";
export type { ClarificationListItem, ClarificationListQuery } from "./clarification.service";
export type { ObservationListItem, ObservationListQuery } from "./observation.service";
export type { ResponseListItem, ResponseListQuery } from "./management-response.service";
export type { ActionListItem, ActionListQuery } from "./management-action.service";
export type { ClosureListItem, ClosureListQuery } from "./closure-update.service";
export type { ReportListItem, ReportListQuery } from "./report.service";
