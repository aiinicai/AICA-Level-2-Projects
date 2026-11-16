import { getFirestore, FieldValue, type Transaction } from 'firebase-admin/firestore';
import type { AuditLogEntry } from '../../shared/src/models/staff.js';

/** Audit entries contain internal IDs only - never phone numbers, PAN or document contents. */
export function writeAudit(entry: Omit<AuditLogEntry, 'at'>, tx?: Transaction): void | Promise<unknown> {
  const ref = getFirestore().collection('audit_logs').doc();
  const data = { ...entry, at: FieldValue.serverTimestamp() };
  return tx ? void tx.create(ref, data) : ref.create(data);
}
