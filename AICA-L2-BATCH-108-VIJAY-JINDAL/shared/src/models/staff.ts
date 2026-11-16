import type { EpochMs } from './common.js';

export type StaffRole = 'owner_admin' | 'recruiter' | 'document_reviewer' | 'viewer';

/** Field groups that can be granted individually. */
export type FieldGroup =
  | 'profile.basic'          // name, candidateId, location city/district, roles, DRA status summary, experience
  | 'contact.phone'          // full phone numbers
  | 'contact.email'
  | 'identity.restricted'    // father name, DOB, addresses, masked PAN
  | 'compensation'           // salary
  | 'documents.view'         // signed download of certificates/CVs
  | 'notes.recruitment'      // internal notes & stages
  | 'referrals.report'
  | 'training.manage'
  | 'cms.manage'
  | 'vacancies.manage'
  | 'export.csv';            // must be separately approved by owner admin

/** Stored in staff/{uid}; mirrored to custom claims {role, grants} by the setStaffRole function. */
export interface StaffMember {
  uid: string;
  displayName: string;
  email: string;
  role: StaffRole;
  extraGrants: FieldGroup[];
  revokedGrants: FieldGroup[];
  scope?: { stateCodes?: string[] };   // optional geographic scoping
  disabled: boolean;
  mfaEnrolled: boolean;
  createdAt: EpochMs; createdBy: string;
}

export interface AuditLogEntry {
  at: EpochMs;
  actorUid: string;
  actorRole: StaffRole | 'candidate' | 'system';
  action:
    | 'profile.view_restricted' | 'document.download' | 'document.review' | 'dra.update' | 'export.run'
    | 'staff.create' | 'staff.role_change' | 'staff.disable'
    | 'referral.attributed' | 'referral.rejected'
    | 'course.edit' | 'certificate.issue' | 'certificate.revoke'
    | 'settings.change' | 'contact.message_status' | 'consent.change' | 'account.closure' | 'account.deletion';
  targetType?: string;
  targetId?: string;          // internal IDs only - never phone, PAN or document content
  meta?: Record<string, string | number | boolean>;
}
