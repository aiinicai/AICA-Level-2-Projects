import type { UserRole } from "./common";

export const ACTIVITY_MODULES = [
  "Clients",
  "Engagements",
  "Scope",
  "Procedures",
  "Requirements",
  "Evidence",
  "Clarifications",
  "Observations",
  "Management Responses",
  "Management Actions",
  "Closure Tracking",
  "Final Reporting",
] as const;
export type ActivityModule = (typeof ACTIVITY_MODULES)[number];

/** Append-only audit trail entry. Never edited or deleted in the UI. */
export interface ActivityRecord {
  id: string;
  timestamp: string;
  user: string;
  role: UserRole;
  clientId: string | null;
  clientName: string | null;
  engagementId: string | null;
  engagementRef: string | null;
  module: ActivityModule;
  recordReference: string;
  action: string;
  previousStatus: string | null;
  newStatus: string | null;
  remarks: string;
}

export type ActivityInput = Omit<ActivityRecord, "id" | "timestamp">;

/** Identity of whoever performs an action — supplied by the role selector. */
export interface Actor {
  user: string;
  role: UserRole;
}
