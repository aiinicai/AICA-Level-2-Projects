import type { FieldGroup, StaffRole } from '../models/staff.js';

export const ALL_FIELD_GROUPS: readonly FieldGroup[] = ['profile.basic', 'contact.phone', 'contact.email', 'identity.restricted',
  'compensation', 'documents.view', 'notes.recruitment', 'referrals.report', 'training.manage', 'cms.manage', 'vacancies.manage', 'export.csv'];

export const ROLE_DEFAULT_GRANTS: Record<StaffRole, readonly FieldGroup[]> = {
  owner_admin: ['profile.basic', 'contact.phone', 'contact.email', 'identity.restricted', 'compensation', 'documents.view',
    'notes.recruitment', 'referrals.report', 'training.manage', 'cms.manage', 'vacancies.manage', 'export.csv'],
  recruiter: ['profile.basic', 'contact.phone', 'contact.email', 'notes.recruitment', 'vacancies.manage'],
  document_reviewer: ['profile.basic', 'documents.view'],
  viewer: ['profile.basic'],
};

/** Grants that only the owner admin may hand out, and that are never part of a non-owner default. */
export const OWNER_APPROVAL_REQUIRED: readonly FieldGroup[] = ['export.csv', 'identity.restricted', 'compensation'];

export function effectiveGrants(role: StaffRole, extra: readonly FieldGroup[] = [], revoked: readonly FieldGroup[] = []): Set<FieldGroup> {
  const s = new Set<FieldGroup>([...ROLE_DEFAULT_GRANTS[role], ...extra]);
  for (const r of revoked) s.delete(r);
  return s;
}

export function canAccess(staff: { role: StaffRole; disabled: boolean; mfaVerified: boolean; grants: Set<FieldGroup> }, group: FieldGroup): boolean {
  if (staff.disabled) return false;
  if (!staff.mfaVerified) return false;  // all staff access requires a second factor in the session
  return staff.grants.has(group);
}

/** Only the owner admin can create/disable staff, change roles, or grant owner-approval fields. */
export function canManageStaff(actorRole: StaffRole): boolean { return actorRole === 'owner_admin'; }

export function validateGrantChange(actorRole: StaffRole, targetRole: StaffRole, added: readonly FieldGroup[]): string | null {
  if (!canManageStaff(actorRole)) return 'only_owner_admin';
  if (targetRole === 'owner_admin') return 'owner_admin_not_assignable_via_ui'; // done by bootstrap script only
  return added.every((g) => ALL_FIELD_GROUPS.includes(g)) ? null : 'invalid_grant';
}

/** Field-level export: returns only columns the actor is allowed to export. Unknown columns are dropped. */
export const EXPORT_COLUMN_GROUPS: Record<string, FieldGroup> = {
  candidateId: 'profile.basic', fullName: 'profile.basic', stateCode: 'profile.basic', district: 'profile.basic',
  city: 'profile.basic', primaryRole: 'profile.basic', draStatus: 'profile.basic', relevantExperienceMonths: 'profile.basic',
  mobile: 'contact.phone', email: 'contact.email', dateOfBirth: 'identity.restricted', expectedSalary: 'compensation',
};

export function allowedExportColumns(grants: Set<FieldGroup>, requested: readonly string[]): string[] | 'forbidden' {
  if (!grants.has('export.csv')) return 'forbidden';
  return requested.filter((c) => { const g = EXPORT_COLUMN_GROUPS[c]; return g !== undefined && grants.has(g); });
}
