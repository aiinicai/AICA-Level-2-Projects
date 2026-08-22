import type { BaseEntity, ClientId, StatusTone } from "./common";

/* ------------------------------------------------------------------ */
/* Client status (entity specific — not the generic WORKFLOW_STATUSES)  */
/* ------------------------------------------------------------------ */

export const CLIENT_STATUSES = ["Active", "Inactive", "Archived"] as const;
export type ClientStatus = (typeof CLIENT_STATUSES)[number];

export const CLIENT_STATUS_TONES: Record<ClientStatus, StatusTone> = {
  Active: "success",
  Inactive: "warning",
  Archived: "neutral",
};

/* ------------------------------------------------------------------ */
/* Nested collections (Stage 2 keeps these on the client record)        */
/* ------------------------------------------------------------------ */

export const CONTACT_TYPES = [
  "Audit Coordination",
  "Finance",
  "Operations",
  "Compliance",
  "Management",
  "Other",
] as const;
export type ContactType = (typeof CONTACT_TYPES)[number];

export interface ClientContact {
  id: string;
  name: string;
  designation: string;
  department: string;
  email: string;
  mobile: string;
  contactType: ContactType;
  isActive: boolean;
}

export const LOCATION_STATUSES = ["Active", "Inactive"] as const;
export type LocationStatus = (typeof LOCATION_STATUSES)[number];

export interface ClientLocation {
  id: string;
  locationCode: string;
  locationName: string;
  address: string;
  city: string;
  state: string;
  contactPerson: string;
  status: LocationStatus;
}

/* ------------------------------------------------------------------ */
/* Client record                                                        */
/* ------------------------------------------------------------------ */

export interface ClientRecord extends BaseEntity<ClientId> {
  clientCode: ClientId;
  legalName: string;
  tradeName: string;
  industry: string;
  entityType: string;
  registeredOffice: string;
  corporateOffice: string;
  city: string;
  state: string;
  country: string;
  pinCode: string;
  coordinatorName: string;
  coordinatorDesignation: string;
  coordinatorEmail: string;
  coordinatorMobile: string;
  financialYearEnding: string;
  pan: string;
  gstin: string;
  remarks: string;
  status: ClientStatus;
  contacts: ClientContact[];
  locations: ClientLocation[];
}

export type ClientFormValues = Omit<
  ClientRecord,
  keyof BaseEntity<ClientId> | "clientCode" | "contacts" | "locations"
>;
