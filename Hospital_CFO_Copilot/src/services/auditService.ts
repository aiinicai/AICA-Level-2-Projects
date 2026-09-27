import { doc, setDoc } from 'firebase/firestore';
import { db } from '../firebase';
import { AuditActionType, ComprehensiveAuditLog, UserRole } from '../types';
import { COLLECTIONS, sanitizeForFirestore, hasActiveSession } from './firestoreDataService';

const AUDIT_STORAGE_KEY = 'cfo_copilot_audit_logs_v2';

export const INITIAL_AUDIT_LOGS: ComprehensiveAuditLog[] = [];

export function getStoredAuditLogs(): ComprehensiveAuditLog[] {
  try {
    const raw = localStorage.getItem(AUDIT_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveAuditLogs(logs: ComprehensiveAuditLog[]): void {
  try {
    localStorage.setItem(AUDIT_STORAGE_KEY, JSON.stringify(logs.slice(0, 500))); // Keep last 500
  } catch (err) {
    console.error('Failed to save audit logs:', err);
  }
}

export function createAuditLog(
  user: string,
  role: UserRole,
  action: AuditActionType,
  entityType: ComprehensiveAuditLog['entityType'],
  entityId: string,
  details: string,
  previousValue?: string,
  newValue?: string
): ComprehensiveAuditLog {
  const now = new Date();
  const timestamp = now.toISOString().replace('T', ' ').slice(0, 19);
  const id = `AUD-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(
    now.getDate()
  ).padStart(2, '0')}-${String(Math.floor(Math.random() * 9000) + 1000)}`;

  return {
    id,
    timestamp,
    user,
    role,
    action,
    entityType,
    entityId,
    details,
    previousValue,
    newValue,
  };
}

/**
 * Logs a governance-relevant audit event.
 *
 * Persists the event to the immutable Firestore `audit_logs` collection
 * using the standard setDoc pattern, while maintaining a local cache in
 * browser storage for fast in-session UI responsiveness.
 */
export async function logEvent(entry: {
  user: string;
  role: UserRole;
  action: AuditActionType;
  entityType: ComprehensiveAuditLog['entityType'];
  entityId: string;
  details: string;
  previousValue?: string;
  newValue?: string;
}): Promise<ComprehensiveAuditLog> {
  const current = getStoredAuditLogs();
  const log = createAuditLog(
    entry.user,
    entry.role,
    entry.action,
    entry.entityType,
    entry.entityId,
    entry.details,
    entry.previousValue,
    entry.newValue
  );

  // 1. Maintain local cache for UI responsiveness
  saveAuditLogs([log, ...current]);

  // 2. Persist to authoritative Firestore audit_logs collection
  try {
    if (hasActiveSession()) {
      await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, log.id), sanitizeForFirestore(log));
    }
  } catch (err) {
    console.warn('[AuditService] Failed to persist audit record to Firestore:', err);
  }

  return log;
}

export const auditService = {
  getStoredAuditLogs,
  saveAuditLogs,
  createAuditLog,
  logEvent,
};
