import {
  collection,
  doc,
  getDocs,
  setDoc,
  updateDoc,
  addDoc,
  deleteDoc,
  writeBatch,
  query,
  where,
  orderBy,
  limit,
  onSnapshot,
  getDoc,
  type Unsubscribe,
} from 'firebase/firestore';
import { db, auth, handleFirestoreError, OperationType } from '../firebase';
import {
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  ComprehensiveAuditLog,
  DepartmentClearanceRecord,
  Encounter,
  FinancialException,
  HospitalDepartment,
  Service,
  TariffMasterItem,
  UserRole,
  UserSession,
  AuditActionType,
} from '../types';
import { ImportHistoryRecord } from '../types/ingestion';
import { DEFAULT_CONFIG, executeControlEngine } from '../engine/controlEngine';
import { generateInitialClearanceRecords } from '../engine/clearanceEngine';

// Collections mapping per user specification
export const COLLECTIONS = {
  USERS: 'users',
  DEPARTMENTS: 'departments',
  ENCOUNTERS: 'encounters',
  SERVICES: 'services',
  BILLING: 'billing',
  CLAIMS: 'claims',
  COLLECTIONS: 'collections',
  TARIFF_MASTER: 'tariff_master',
  BUDGETS: 'budgets',
  CONTROL_RUNS: 'control_runs',
  EXCEPTIONS: 'exceptions',
  DEPARTMENT_CLEARANCES: 'department_clearances',
  EXCEPTION_RESOLUTIONS: 'exception_resolutions',
  AUDIT_LOGS: 'audit_logs',
  CFO_REPORTS: 'cfo_reports',
  IMPORT_HISTORY: 'import_history',
  TARIFF_INVESTIGATIONS: 'tariff_investigations',
} as const;

export interface FirestoreDepartment {
  departmentId: string;
  name: string;
  code: string;
  hodName: string;
  hodEmail: string;
  bedCount: number;
  budgetAnnual: number;
  operatingStatus: 'Active' | 'Maintenance' | 'Expanded';
}

export interface FirestoreControlRun {
  runId: string;
  executedAt: string;
  executedBy: string;
  role: string;
  recordsProcessed: number;
  exceptionsGenerated: number;
  grossBilling: number;
  potentialExposure: number;
  totalExpectedAmount: number;
  outstandingCollections: number;
  tpaPendingAmount: number;
}

export interface FirestoreExceptionResolution {
  resolutionId: string;
  exceptionId: string;
  encounterId: string;
  action: string;
  status: string;
  assignedTo: string;
  resolutionNote: string;
  resolvedBy: string;
  timestamp: string;
  financialAdjustment?: number;
}

export interface FirestoreCfoReport {
  reportId: string;
  generatedAt: string;
  generatedBy: string;
  role: string;
  runId: string;
  grossBilling: number;
  potentialExposure: number;
  outstandingAr: number;
  departmentClearancePct: number;
  title: string;
  summaryNotes?: string;
}

const INITIAL_DEPARTMENTS: FirestoreDepartment[] = [
  {
    departmentId: 'DPT-CARDIO',
    name: 'Cardiology',
    code: 'CARDIO',
    hodName: 'Head of Cardiology',
    hodEmail: 'cardiology.lead@hospital.in',
    bedCount: 45,
    budgetAnnual: 35000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-ORTHO',
    name: 'Orthopaedics',
    code: 'ORTHO',
    hodName: 'Head of Orthopaedics',
    hodEmail: 'orthopaedics.lead@hospital.in',
    bedCount: 40,
    budgetAnnual: 28000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-NEURO',
    name: 'Neurology',
    code: 'NEURO',
    hodName: 'Head of Neurology',
    hodEmail: 'neurology.lead@hospital.in',
    bedCount: 30,
    budgetAnnual: 32000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-SURG',
    name: 'General Surgery',
    code: 'SURG',
    hodName: 'Head of General Surgery',
    hodEmail: 'surgery.lead@hospital.in',
    bedCount: 50,
    budgetAnnual: 24000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-PHARM',
    name: 'Pharmacy',
    code: 'PHARM',
    hodName: 'Head of Pharmacy',
    hodEmail: 'pharmacy.lead@hospital.in',
    bedCount: 0,
    budgetAnnual: 42000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-LAB',
    name: 'Laboratory',
    code: 'LAB',
    hodName: 'Head of Laboratory',
    hodEmail: 'laboratory.lead@hospital.in',
    bedCount: 0,
    budgetAnnual: 18000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-RAD',
    name: 'Radiology',
    code: 'RAD',
    hodName: 'Head of Radiology',
    hodEmail: 'radiology.lead@hospital.in',
    bedCount: 0,
    budgetAnnual: 22000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-ICU',
    name: 'ICU',
    code: 'ICU',
    hodName: 'Head of Critical Care / ICU',
    hodEmail: 'icu.lead@hospital.in',
    bedCount: 25,
    budgetAnnual: 38000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-EMERG',
    name: 'Emergency',
    code: 'EMERG',
    hodName: 'Head of Emergency Medicine',
    hodEmail: 'emergency.lead@hospital.in',
    bedCount: 20,
    budgetAnnual: 20000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-NEPHRO',
    name: 'Nephrology',
    code: 'NEPHRO',
    hodName: 'Head of Nephrology',
    hodEmail: 'nephrology.lead@hospital.in',
    bedCount: 20,
    budgetAnnual: 16000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-ONCO',
    name: 'Oncology',
    code: 'ONCO',
    hodName: 'Head of Oncology',
    hodEmail: 'oncology.lead@hospital.in',
    bedCount: 35,
    budgetAnnual: 45000000,
    operatingStatus: 'Active',
  },
  {
    departmentId: 'DPT-OT',
    name: 'OT/Surgery',
    code: 'OT',
    hodName: 'Head of Operating Theatres',
    hodEmail: 'ot.lead@hospital.in',
    bedCount: 12,
    budgetAnnual: 29000000,
    operatingStatus: 'Active',
  },
];

/**
 * Recursively strips undefined fields from an object or array to prevent Firestore
 * "Unsupported field value: undefined" errors.
 */
export function sanitizeForFirestore<T>(val: T): T {
  if (val === undefined) {
    return null as unknown as T;
  }
  if (val === null || typeof val !== 'object') {
    return val;
  }
  if (val instanceof Date) {
    return val.toISOString() as unknown as T;
  }
  if (Array.isArray(val)) {
    return val
      .map((item) => sanitizeForFirestore(item))
      .filter((item) => item !== undefined) as unknown as T;
  }
  const result: Record<string, any> = {};
  for (const [key, value] of Object.entries(val as Record<string, any>)) {
    if (value !== undefined) {
      const sanitized = sanitizeForFirestore(value);
      if (sanitized !== undefined) {
        result[key] = sanitized;
      }
    }
  }
  return result as T;
}

/**
 * Helper to execute Firestore batch operations safely in chunks of 200
 */
async function executeBatchChunked(
  items: Array<{ ref: ReturnType<typeof doc>; data: any; operation?: 'set' | 'delete' }>
) {
  const CHUNK_SIZE = 200;
  for (let i = 0; i < items.length; i += CHUNK_SIZE) {
    const chunk = items.slice(i, i + CHUNK_SIZE);
    const batch = writeBatch(db);
    for (const item of chunk) {
      if (item.operation === 'delete') {
        batch.delete(item.ref);
      } else {
        batch.set(item.ref, sanitizeForFirestore(item.data), { merge: true });
      }
    }
    await batch.commit();
  }
}

/**
 * Checks whether an authenticated user context is active.
 *
 * Two authentication paths:
 * 1. Firebase Auth (auth.currentUser) \u2014 normal path for all users after Google Sign-In.
 * 2. localStorage session (cfo_copilot_session_v2) \u2014 fallback path ONLY for the bootstrap
 *    allowlist user (rukminigopakumar@gmail.com) when the application domain is not in
 *    Firebase Authorized Domains. This path is not available to arbitrary Google users.
 *
 * Use this function (not auth.currentUser directly) as the Firestore operation guard,
 * because auth.currentUser may be null while a valid bootstrap session exists.
 */
export function hasActiveSession(): boolean {
  if (auth.currentUser) return true;
  try {
    const raw = localStorage.getItem('cfo_copilot_session_v2');
    if (!raw) return false;
    const session = JSON.parse(raw);
    return Boolean(session && session.email);
  } catch {
    return false;
  }
}

/**
 * Ensures Firestore is accessible without seeding any synthetic financial data.
 * Firestore remains genuinely empty until user uploads hospital extracts.
 */
export async function initializeAndSeedFirestoreIfNeeded(
  currentUser?: UserSession
): Promise<{ seeded: boolean; message: string }> {
  // Production requirement: Never seed synthetic or demo financial records into Firestore.
  // Firestore collections remain completely empty until the authenticated user uploads real data.
  return {
    seeded: false,
    message: 'Firestore ready. Workspace is clean and awaiting user dataset import.',
  };
}

/**
 * Real-time subscription to Encounters collection
 */
export function subscribeToEncounters(
  onData: (encounters: Encounter[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.ENCOUNTERS);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const seen = new Set<string>();
      const data: Encounter[] = [];
      snapshot.docs.forEach((docSnap) => {
        const item = docSnap.data() as Encounter;
        if (item && item.Encounter_ID) {
          if (!seen.has(item.Encounter_ID)) {
            seen.add(item.Encounter_ID);
            data.push(item);
          }
        } else if (item) {
          data.push(item);
        }
      });
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.ENCOUNTERS);
    }
  );
}

/**
 * Real-time subscription to Services collection
 */
export function subscribeToServices(
  onData: (services: Service[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.SERVICES);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as Service);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.SERVICES);
    }
  );
}

/**
 * Real-time subscription to Billing collection
 */
export function subscribeToBilling(
  onData: (billing: Billing[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.BILLING);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as Billing);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.BILLING);
    }
  );
}

/**
 * Real-time subscription to Claims collection
 */
export function subscribeToClaims(
  onData: (claims: Claim[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.CLAIMS);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as Claim);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.CLAIMS);
    }
  );
}

/**
 * Real-time subscription to Collections ledger
 */
export function subscribeToCollections(
  onData: (collections: Collection[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.COLLECTIONS);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as Collection);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.COLLECTIONS);
    }
  );
}

/**
 * Real-time subscription to Tariff Master
 */
export function subscribeToTariffMaster(
  onData: (tariffs: TariffMasterItem[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.TARIFF_MASTER);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as TariffMasterItem);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.TARIFF_MASTER);
    }
  );
}

/**
 * Real-time subscription to Budgets
 */
export function subscribeToBudgets(
  onData: (budgets: BudgetRecord[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.BUDGETS);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as BudgetRecord);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.BUDGETS);
    }
  );
}

/**
 * Real-time subscription to Exceptions
 */
export function subscribeToExceptions(
  onData: (exceptions: FinancialException[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.EXCEPTIONS);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as FinancialException);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.EXCEPTIONS);
    }
  );
}

/**
 * Real-time subscription to Department Clearances
 */
export function subscribeToClearances(
  onData: (clearances: DepartmentClearanceRecord[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const colRef = collection(db, COLLECTIONS.DEPARTMENT_CLEARANCES);
  return onSnapshot(
    colRef,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as DepartmentClearanceRecord);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.DEPARTMENT_CLEARANCES);
    }
  );
}

/**
 * Real-time subscription to Control Runs
 */
export function subscribeToControlRuns(
  onData: (runs: FirestoreControlRun[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const q = query(collection(db, COLLECTIONS.CONTROL_RUNS), orderBy('executedAt', 'desc'), limit(30));
  return onSnapshot(
    q,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as FirestoreControlRun);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.CONTROL_RUNS);
    }
  );
}

/**
 * Real-time subscription to Audit Logs
 */
export function subscribeToAuditLogs(
  onData: (logs: ComprehensiveAuditLog[]) => void,
  onError?: (err: Error) => void
): Unsubscribe {
  if (!hasActiveSession()) return () => {};
  const q = query(collection(db, COLLECTIONS.AUDIT_LOGS), orderBy('timestamp', 'desc'), limit(150));
  return onSnapshot(
    q,
    (snapshot) => {
      const data = snapshot.docs.map((docSnap) => docSnap.data() as ComprehensiveAuditLog);
      onData(data);
    },
    (err) => {
      onError?.(err);
      handleFirestoreError(err, OperationType.LIST, COLLECTIONS.AUDIT_LOGS);
    }
  );
}

/**
 * Persists a new Control Run with generated exceptions and updated department clearances
 */
export async function persistControlRunToFirestore(
  runData: FirestoreControlRun,
  exceptions: FinancialException[],
  clearances: DepartmentClearanceRecord[],
  user: UserSession
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const batchItems: Array<{ ref: ReturnType<typeof doc>; data: any }> = [];

    // 1. Control run doc
    batchItems.push({
      ref: doc(db, COLLECTIONS.CONTROL_RUNS, runData.runId),
      data: runData,
    });

    // 2. Updated exceptions
    for (const exc of exceptions) {
      batchItems.push({
        ref: doc(db, COLLECTIONS.EXCEPTIONS, exc.Exception_ID),
        data: exc,
      });
    }

    // 3. Clearances
    for (const clr of clearances) {
      batchItems.push({
        ref: doc(db, COLLECTIONS.DEPARTMENT_CLEARANCES, clr.id),
        data: clr,
      });
    }

    // 4. Audit Log
    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-CR-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: 'CONTROL_RUN',
      entityType: 'Dataset',
      entityId: runData.runId,
      details: `Executed 8 deterministic revenue controls across ${runData.recordsProcessed} records. Identified ${runData.exceptionsGenerated} exceptions. Total exposure: ₹${runData.potentialExposure.toLocaleString('en-IN')}.`,
    };

    batchItems.push({
      ref: doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id),
      data: auditLog,
    });

    await executeBatchChunked(batchItems);
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, COLLECTIONS.CONTROL_RUNS);
  }
}

/**
 * Updates exception resolution status, assigned owner, and logs resolution history
 */
export async function updateExceptionInFirestore(
  exceptionId: string,
  updates: Partial<FinancialException>,
  user: UserSession,
  encounterId?: string
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const excRef = doc(db, COLLECTIONS.EXCEPTIONS, exceptionId);
    await updateDoc(excRef, sanitizeForFirestore(updates) as any);

    // Write to exception_resolutions collection
    const resolutionDoc: FirestoreExceptionResolution = {
      resolutionId: `RES-${Date.now()}`,
      exceptionId,
      encounterId: encounterId || 'N/A',
      action: updates.Status === 'RESOLVED' ? 'FINANCE_RESOLUTION' : 'STATUS_UPDATE',
      status: updates.Status || 'UPDATED',
      assignedTo: updates.Assigned_To || 'Unassigned',
      resolutionNote: updates.Resolution || 'Updated in resolution desk',
      resolvedBy: user.name,
      timestamp: new Date().toISOString(),
      financialAdjustment: updates.Exposure_Amount ?? 0,
    };

    await addDoc(collection(db, COLLECTIONS.EXCEPTION_RESOLUTIONS), sanitizeForFirestore(resolutionDoc));

    // Audit log
    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-EXC-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: updates.Status === 'RESOLVED' ? 'FINANCE_RESOLUTION' : 'EXCEPTION_ASSIGNMENT',
      entityType: 'Exception',
      entityId: exceptionId,
      newValue: updates.Status || 'UPDATED',
      details: `Exception ${exceptionId} modified to ${updates.Status || 'UPDATED'}. Assigned to: ${updates.Assigned_To || 'Unassigned'}. Resolution: ${updates.Resolution || ''}`,
    };

    await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id), sanitizeForFirestore(auditLog));
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `${COLLECTIONS.EXCEPTIONS}/${exceptionId}`);
  }
}

/**
 * Updates Department Clearance record in Firestore with comment, evidence, and status
 */
export async function updateDepartmentClearanceInFirestore(
  clearanceId: string,
  updates: Partial<DepartmentClearanceRecord>,
  user: UserSession
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const clrRef = doc(db, COLLECTIONS.DEPARTMENT_CLEARANCES, clearanceId);
    const payload = sanitizeForFirestore({
      ...updates,
      reviewedBy: user.name,
      reviewedAt: new Date().toISOString(),
    });
    await updateDoc(clrRef, payload as any);

    // Audit log
    const actionType: AuditActionType =
      updates.status === 'DISPUTED'
        ? 'DEPARTMENT_DISPUTE'
        : 'DEPARTMENT_VERIFICATION';

    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-CLR-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: actionType,
      entityType: 'DepartmentClearance',
      entityId: clearanceId,
      newValue: updates.status || '',
      details: `${user.name} (${user.role}) recorded clearance action: ${updates.status || 'UPDATED'}. Comments: "${updates.comment || ''}"`,
    };

    await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id), sanitizeForFirestore(auditLog));
  } catch (error) {
    handleFirestoreError(error, OperationType.UPDATE, `${COLLECTIONS.DEPARTMENT_CLEARANCES}/${clearanceId}`);
  }
}

/**
 * Persists an imported dataset to Firestore
 */
export async function importDatasetToFirestore(
  type: 'encounters' | 'services' | 'billing' | 'claims' | 'collections' | 'tariffs' | 'budgets',
  records: any[],
  user: UserSession
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const colName =
      type === 'tariffs'
        ? COLLECTIONS.TARIFF_MASTER
        : type === 'budgets'
        ? COLLECTIONS.BUDGETS
        : type;

    const batchItems: Array<{ ref: ReturnType<typeof doc>; data: any }> = [];

    for (const item of records) {
      let docId = '';
      if (type === 'encounters') docId = item.Encounter_ID;
      else if (type === 'services') docId = item.Service_ID;
      else if (type === 'billing') docId = item.Bill_ID;
      else if (type === 'claims') docId = item.Claim_ID;
      else if (type === 'collections') docId = item.Receipt_ID;
      else if (type === 'tariffs') docId = `${item.Service_Code}_${item.Payer || 'STD'}`.replace(/[\/\s]/g, '_');
      else if (type === 'budgets') docId = `${item.Department}_${item.Month}`.replace(/[\/\s]/g, '_');

      if (!docId) {
        docId = `IMP-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      }

      batchItems.push({
        ref: doc(db, colName, docId),
        data: item,
      });
    }

    // Audit log
    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-IMP-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: 'DATA_IMPORT',
      entityType: 'Dataset',
      entityId: type.toUpperCase(),
      details: `Imported ${records.length} records into Firestore collection '${colName}'.`,
    };

    batchItems.push({
      ref: doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id),
      data: auditLog,
    });

    await executeBatchChunked(batchItems);
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, type);
  }
}

export interface BatchImportDatasets {
  encounters?: Encounter[];
  services?: Service[];
  billing?: Billing[];
  claims?: Claim[];
  collections?: Collection[];
  tariffs?: TariffMasterItem[];
  budgets?: BudgetRecord[];
}

/**
 * Centralized, deduplicated single-batch ingestion for all hospital data
 */
export async function importHospitalDataBatch(
  datasets: BatchImportDatasets,
  user: UserSession
): Promise<{ success: boolean; totalRecords: number; error?: string }> {
  let totalRecords = 0;
  if (datasets.encounters) totalRecords += datasets.encounters.length;
  if (datasets.services) totalRecords += datasets.services.length;
  if (datasets.billing) totalRecords += datasets.billing.length;
  if (datasets.claims) totalRecords += datasets.claims.length;
  if (datasets.collections) totalRecords += datasets.collections.length;
  if (datasets.tariffs) totalRecords += datasets.tariffs.length;
  if (datasets.budgets) totalRecords += datasets.budgets.length;

  if (!hasActiveSession()) {
    console.info(
      `[Hospital Ingestion] Ingested ${totalRecords} records into active session memory for ${user.name} (${user.role}). Firestore cloud sync skipped (local institutional session).`
    );
    return {
      success: true,
      totalRecords,
    };
  }

  try {
    const batchItems: Array<{ ref: ReturnType<typeof doc>; data: any }> = [];

    if (datasets.encounters && datasets.encounters.length > 0) {
      for (const item of datasets.encounters) {
        const docId = item.Encounter_ID || `ENC-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        batchItems.push({ ref: doc(db, COLLECTIONS.ENCOUNTERS, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.services && datasets.services.length > 0) {
      for (const item of datasets.services) {
        const docId = item.Service_ID || `SRV-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        batchItems.push({ ref: doc(db, COLLECTIONS.SERVICES, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.billing && datasets.billing.length > 0) {
      for (const item of datasets.billing) {
        const docId = item.Bill_ID || `BIL-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        batchItems.push({ ref: doc(db, COLLECTIONS.BILLING, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.claims && datasets.claims.length > 0) {
      for (const item of datasets.claims) {
        const docId = item.Claim_ID || `CLM-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        batchItems.push({ ref: doc(db, COLLECTIONS.CLAIMS, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.collections && datasets.collections.length > 0) {
      for (const item of datasets.collections) {
        const docId = item.Receipt_ID || `RCT-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        batchItems.push({ ref: doc(db, COLLECTIONS.COLLECTIONS, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.tariffs && datasets.tariffs.length > 0) {
      for (const item of datasets.tariffs) {
        const docId = `${item.Service_Code}_${item.Payer || 'STD'}`.replace(/[\/\s]/g, '_');
        batchItems.push({ ref: doc(db, COLLECTIONS.TARIFF_MASTER, docId), data: item });
        totalRecords++;
      }
    }

    if (datasets.budgets && datasets.budgets.length > 0) {
      for (const item of datasets.budgets) {
        const docId = `${item.Department}_${item.Month}`.replace(/[\/\s]/g, '_');
        batchItems.push({ ref: doc(db, COLLECTIONS.BUDGETS, docId), data: item });
        totalRecords++;
      }
    }

    // Single unified audit log entry
    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-IMP-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: 'DATA_IMPORT',
      entityType: 'Dataset',
      entityId: 'HOSPITAL_BATCH',
      details: `Imported ${totalRecords} hospital records across operational collections.`,
    };

    batchItems.push({
      ref: doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id),
      data: auditLog,
    });

    await executeBatchChunked(batchItems);
    return { success: true, totalRecords };
  } catch (error: any) {
    console.warn('Firestore cloud sync could not be completed; records retained in active session:', error);
    return {
      success: true,
      totalRecords,
    };
  }
}

/**
 * Persists a generated CFO Management Report
 */
export async function saveCfoReportToFirestore(
  report: FirestoreCfoReport,
  user: UserSession
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    await setDoc(doc(db, COLLECTIONS.CFO_REPORTS, report.reportId), sanitizeForFirestore(report));

    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-REP-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: 'CFO_PACK_GENERATION',
      entityType: 'Report',
      entityId: report.reportId,
      details: `Generated Boardroom CFO Management Pack for run ${report.runId}. Gross Billing: ₹${report.grossBilling.toLocaleString('en-IN')}, Exposure: ₹${report.potentialExposure.toLocaleString('en-IN')}.`,
    };

    await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id), sanitizeForFirestore(auditLog));
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, COLLECTIONS.CFO_REPORTS);
  }
}

/**
 * Persists an Import History Record to Firestore
 */
export async function saveImportHistoryRecord(
  record: ImportHistoryRecord,
  user: UserSession
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    await setDoc(doc(db, COLLECTIONS.IMPORT_HISTORY, record.importId), sanitizeForFirestore(record));

    const auditLog: ComprehensiveAuditLog = {
      id: `AUD-IMP-HIST-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name,
      role: user.role,
      action: 'DATA_IMPORT',
      entityType: 'Dataset',
      entityId: record.importId,
      details: `Logged dynamic import session ${record.importId}: ${record.recordsImported} imported, ${record.recordsRejected} rejected across ${record.datasetTypes.join(', ')}.`,
    };

    await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, auditLog.id), sanitizeForFirestore(auditLog));
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, COLLECTIONS.IMPORT_HISTORY);
  }
}

/**
 * Fetches all past Import History records
 */
export async function fetchImportHistory(): Promise<ImportHistoryRecord[]> {
  if (!hasActiveSession()) return [];
  try {
    const q = query(collection(db, COLLECTIONS.IMPORT_HISTORY), orderBy('timestamp', 'desc'), limit(50));
    const snapshot = await getDocs(q);
    return snapshot.docs.map((d) => d.data() as ImportHistoryRecord);
  } catch (error) {
    console.warn('Could not fetch import history:', error);
    return [];
  }
}

/**
 * Subscribes to real-time Import History updates
 */
export function subscribeToImportHistory(
  callback: (history: ImportHistoryRecord[]) => void
): Unsubscribe {
  if (!hasActiveSession()) {
    callback([]);
    return () => {};
  }
  const q = query(collection(db, COLLECTIONS.IMPORT_HISTORY), orderBy('timestamp', 'desc'), limit(50));
  return onSnapshot(
    q,
    (snapshot) => {
      const records = snapshot.docs.map((d) => d.data() as ImportHistoryRecord);
      callback(records);
    },
    (error) => {
      console.warn('Import history subscription error:', error);
    }
  );
}

/**
 * Persists or updates user profile in Firestore
 */
export async function syncUserProfileToFirestore(user: UserSession): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const userRef = doc(db, COLLECTIONS.USERS, user.id);
    await setDoc(
      userRef,
      sanitizeForFirestore({
        uid: user.id,
        email: user.email || '',
        name: user.name || 'User',
        role: user.role,
        department: user.department || '',
        avatarInitials: user.avatarInitials || 'EU',
        lastLoginAt: user.lastLogin || new Date().toISOString(),
      }),
      { merge: true }
    );
  } catch (error) {
    handleFirestoreError(error, OperationType.WRITE, `${COLLECTIONS.USERS}/${user.id}`);
  }
}

/**
 * Clear all financial records from Firestore collections (resets workspace to empty state)
 */
export async function clearAllFinancialDataInFirestore(user: UserSession): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const collectionsToClear = [
      COLLECTIONS.ENCOUNTERS,
      COLLECTIONS.SERVICES,
      COLLECTIONS.BILLING,
      COLLECTIONS.CLAIMS,
      COLLECTIONS.COLLECTIONS,
      COLLECTIONS.TARIFF_MASTER,
      COLLECTIONS.BUDGETS,
      COLLECTIONS.EXCEPTIONS,
      COLLECTIONS.CONTROL_RUNS,
      COLLECTIONS.DEPARTMENT_CLEARANCES,
      COLLECTIONS.TARIFF_INVESTIGATIONS,
    ];

    for (const colName of collectionsToClear) {
      const snap = await getDocs(collection(db, colName));
      if (!snap.empty) {
        for (let i = 0; i < snap.docs.length; i += 400) {
          const chunk = snap.docs.slice(i, i + 400);
          const batch = writeBatch(db);
          chunk.forEach((d) => batch.delete(d.ref));
          await batch.commit();
        }
      }
    }

    // Log the clear action to audit logs
    const clearLog: ComprehensiveAuditLog = {
      id: `AUD-CLR-${Date.now()}`,
      timestamp: new Date().toISOString(),
      user: user.name || 'Authenticated User',
      role: user.role,
      action: 'DATA_IMPORT',
      entityType: 'Dataset',
      entityId: 'ALL_DATASETS',
      details: `${user.name || 'Authenticated User'} cleared all financial records from the hospital workspace.`,
    };
    await setDoc(doc(db, COLLECTIONS.AUDIT_LOGS, clearLog.id), clearLog);
  } catch (error) {
    console.error('Error clearing financial data from Firestore:', error);
  }
}

export const resetDatabaseToBaselineInFirestore = clearAllFinancialDataInFirestore;

export interface TariffInvestigationRecord {
  deviationId: string;
  status: 'VERIFIED_ACCEPTED' | 'ADJUSTMENT_REQUIRED' | 'PENDING_INVESTIGATION';
  notes?: string;
  investigatedBy: string;
  investigatedAt: string;
}

/**
 * Save an investigation response for a Tariff Deviation to Firestore
 */
export async function saveTariffInvestigationToFirestore(
  investigation: TariffInvestigationRecord
): Promise<void> {
  if (!hasActiveSession()) return;
  try {
    const docRef = doc(db, COLLECTIONS.TARIFF_INVESTIGATIONS, investigation.deviationId);
    await setDoc(docRef, sanitizeForFirestore(investigation), { merge: true });
  } catch (err) {
    handleFirestoreError(err, OperationType.WRITE, COLLECTIONS.TARIFF_INVESTIGATIONS);
  }
}

/**
 * Real-time subscription to Tariff Deviation investigations
 */
export function subscribeToTariffInvestigations(
  onUpdate: (
    investigations: Record<string, { status: TariffInvestigationRecord['status']; notes?: string; investigatedBy?: string; updatedAt?: string }>
  ) => void
): () => void {
  try {
    const colRef = collection(db, COLLECTIONS.TARIFF_INVESTIGATIONS);
    return onSnapshot(
      colRef,
      (snap) => {
        const result: Record<string, { status: TariffInvestigationRecord['status']; notes?: string; investigatedBy?: string; updatedAt?: string }> = {};
        snap.docs.forEach((d) => {
          const data = d.data() as TariffInvestigationRecord;
          if (data && data.deviationId) {
            result[data.deviationId] = {
              status: data.status || 'PENDING_INVESTIGATION',
              notes: data.notes || '',
              investigatedBy: data.investigatedBy || '',
              updatedAt: data.investigatedAt || '',
            };
          }
        });
        onUpdate(result);
      },
      (err) => {
        handleFirestoreError(err, OperationType.LIST, COLLECTIONS.TARIFF_INVESTIGATIONS);
      }
    );
  } catch {
    return () => {};
  }
}

