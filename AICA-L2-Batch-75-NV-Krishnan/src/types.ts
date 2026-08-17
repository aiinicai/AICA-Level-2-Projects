import { Timestamp } from "firebase/firestore";

export type Role = "full_admin" | "team_member" | "client";

export type FolderStatus = "WIP" | "BEING_REVIEWED" | "APPROVED";

export type ConsentStatus = "PENDING" | "SENT" | "SEND_FAILED" | "GIVEN" | "WITHDRAWN" | "DECLINED";

export type EntityType = "company" | "non_company";

export type RetentionBasis = "from_date" | "contract_tenure";

export interface ServiceRetentionPolicy {
  basis: RetentionBasis;
  years: number | null;
  statute: string | null;
  entityDependent?: boolean;
  conditionalRules?: {
    companyMandatory: number;
    nonCompanyOrNonMandatory: number;
  };
  note?: string;
}

export interface ServiceConsentTemplate {
  body: string;
  version: number;
}

export interface Service {
  id: string;
  name: string;
  consentTemplate: ServiceConsentTemplate;
  retentionPolicy: ServiceRetentionPolicy;
}

export interface UserProfile {
  uid: string;
  email: string;
  role: Role;
  linkedClientId?: string;
  isActive: boolean;
  displayName?: string;
  createdAt?: Timestamp | Date | any;
}

export interface Client {
  id: string;
  name: string;
  email: string;
  phone: string;
  entityType: EntityType;
  isActive: boolean;
  createdAt?: Timestamp | Date | any;
}

export interface EmailDeliveryInfo {
  status: "SENT" | "FAILED" | "PENDING";
  method?: string;
  messageId?: string;
  previewUrl?: string;
  error?: string;
  timestamp?: string;
}

export interface Engagement {
  id: string;
  clientId: string;
  serviceId: string;
  assignedTeamMemberIds: string[];
  status: FolderStatus;
  statusNotes?: string;
  consentStatus: ConsentStatus;
  emailDelivery?: EmailDeliveryInfo;
  contractStartDate: string;
  contractEndDate: string;
  erasureDueDate: string;
  createdAt?: Timestamp | Date | any;
  updatedAt?: Timestamp | Date | any;
}

export interface EngagementDocument {
  id: string;
  name: string;
  fileName?: string;
  storagePath?: string;
  url: string;
  uploadedBy?: string;
  uploadedByUid: string;
  uploadedByName: string;
  uploadedByRole: Role;
  uploadedAt: Timestamp | Date | any;
  fileType: string;
  fileSize: number;
}

export interface ClientComment {
  id: string;
  authorId: string;
  authorName: string;
  authorRole: Role;
  text: string;
  timestamp: Timestamp | Date | any;
}

export interface ReviewNote {
  id: string;
  authorId: string;
  authorName: string;
  authorRole: Role;
  text: string;
  entryType?: string; // e.g. "review_comment"
  timestamp: Timestamp | Date | any;
}

export interface PendingItem {
  id: string;
  authorId: string;
  authorName: string;
  authorRole: Role;
  text: string;
  status: "open" | "resolved";
  timestamp: Timestamp | Date | any;
  resolvedAt?: Timestamp | Date | any;
  resolvedBy?: string;
  resolvedByName?: string;
}

export interface ConsentLogEntry {
  id?: string;
  engagementId: string;
  clientId: string;
  serviceId: string;
  serviceName?: string;
  action: "SENT" | "SEND_FAILED" | "GIVEN" | "WITHDRAWN" | "DECLINED";
  timestamp: Timestamp | Date | any;
  actorUid: string;
  actorEmail: string;
  clientEmail?: string;
  notes?: string;
}
