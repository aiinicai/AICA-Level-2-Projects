import {
  User,
  TaskEvaluation,
  CoachingNote,
  AppraisalRecord,
  TrainingRecommendation,
  AnnualPerformancePlan,
  ProfessionalCertification,
  AuditLogEntry
} from '../types';
import {
  MOCK_USERS,
  MOCK_APPRAISAL_RECORDS,
  MOCK_TASK_EVALUATIONS,
  MOCK_COACHING_NOTES,
  MOCK_TRAINING_RECOMMENDATIONS,
  MOCK_ANNUAL_PERFORMANCE_PLANS,
  MOCK_CERTIFICATIONS,
  MOCK_AUDIT_LOGS
} from '../data/mockData';

const SESSION_USER_KEY = 'paras_advisory_session_user_v2';
const APPRAISALS_KEY = 'paras_advisory_appraisals_v2';
const EVALUATIONS_KEY = 'paras_advisory_evaluations_v2';
const COACHING_KEY = 'paras_advisory_coaching_v2';
const TRAINING_KEY = 'paras_advisory_training_v2';
const PLANS_KEY = 'paras_advisory_plans_v2';
const CERTS_KEY = 'paras_advisory_certs_v2';
const AUDIT_KEY = 'paras_advisory_audit_v2';

function safeGetItem<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return defaultValue;
    return JSON.parse(raw) as T;
  } catch (err) {
    console.warn(`Storage read notice for ${key}:`, err);
    return defaultValue;
  }
}

function safeSetItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    console.warn(`Storage write notice for ${key}:`, err);
  }
}

export function getInitialSessionUser(): User {
  const stored = safeGetItem<User | null>(SESSION_USER_KEY, null);
  if (stored && stored.id && stored.fullName) {
    return stored;
  }
  // Default to Zayed Al Dhaheri (Senior Audit Specialist)
  return MOCK_USERS[3];
}

export function saveSessionUser(user: User): void {
  safeSetItem(SESSION_USER_KEY, user);
}

export function clearSessionUser(): void {
  try {
    localStorage.removeItem(SESSION_USER_KEY);
  } catch (err) {
    console.warn('Session clear notice:', err);
  }
}

export function getStoredAppraisals(): AppraisalRecord[] {
  return safeGetItem<AppraisalRecord[]>(APPRAISALS_KEY, MOCK_APPRAISAL_RECORDS);
}

export function saveStoredAppraisals(data: AppraisalRecord[]): void {
  safeSetItem(APPRAISALS_KEY, data);
}

export function getStoredEvaluations(): TaskEvaluation[] {
  return safeGetItem<TaskEvaluation[]>(EVALUATIONS_KEY, MOCK_TASK_EVALUATIONS);
}

export function saveStoredEvaluations(data: TaskEvaluation[]): void {
  safeSetItem(EVALUATIONS_KEY, data);
}

export function getStoredCoaching(): CoachingNote[] {
  return safeGetItem<CoachingNote[]>(COACHING_KEY, MOCK_COACHING_NOTES);
}

export function saveStoredCoaching(data: CoachingNote[]): void {
  safeSetItem(COACHING_KEY, data);
}

export function getStoredTraining(): TrainingRecommendation[] {
  return safeGetItem<TrainingRecommendation[]>(TRAINING_KEY, MOCK_TRAINING_RECOMMENDATIONS);
}

export function saveStoredTraining(data: TrainingRecommendation[]): void {
  safeSetItem(TRAINING_KEY, data);
}

export function getStoredPlans(): AnnualPerformancePlan[] {
  return safeGetItem<AnnualPerformancePlan[]>(PLANS_KEY, MOCK_ANNUAL_PERFORMANCE_PLANS);
}

export function saveStoredPlans(data: AnnualPerformancePlan[]): void {
  safeSetItem(PLANS_KEY, data);
}

export function getStoredCerts(): ProfessionalCertification[] {
  return safeGetItem<ProfessionalCertification[]>(CERTS_KEY, MOCK_CERTIFICATIONS);
}

export function saveStoredCerts(data: ProfessionalCertification[]): void {
  safeSetItem(CERTS_KEY, data);
}

export function getStoredAuditLogs(): AuditLogEntry[] {
  return safeGetItem<AuditLogEntry[]>(AUDIT_KEY, MOCK_AUDIT_LOGS);
}

export function saveStoredAuditLogs(data: AuditLogEntry[]): void {
  safeSetItem(AUDIT_KEY, data);
}

export function resetAllSessionData(): void {
  try {
    localStorage.removeItem(SESSION_USER_KEY);
    localStorage.removeItem(APPRAISALS_KEY);
    localStorage.removeItem(EVALUATIONS_KEY);
    localStorage.removeItem(COACHING_KEY);
    localStorage.removeItem(TRAINING_KEY);
    localStorage.removeItem(PLANS_KEY);
    localStorage.removeItem(CERTS_KEY);
    localStorage.removeItem(AUDIT_KEY);
  } catch (e) {
    console.warn(e);
  }
}
