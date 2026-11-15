import type { EpochMs, LocalizedText, AuditStamp } from './common.js';

export interface Course extends AuditStamp {
  courseId: string;
  slug: string;
  title: LocalizedText;
  summary: LocalizedText;
  category: 'ethics' | 'communication' | 'privacy' | 'field_safety' | 'products' | 'operations' | 'compliance' | 'dra_prep';
  status: 'draft' | 'published' | 'archived';
  /** Licensing evidence - content must be original or owner-approved/licensed. */
  contentLicence: { kind: 'original' | 'licensed' | 'owner_approved'; note?: string; approvedBy?: string };
  completionRule: { requireAllLessons: boolean; finalAssessmentId?: string };
  certificateEnabled: boolean;
  version: number;
}

export interface Lesson {
  lessonId: string; moduleId: string; order: number;
  title: LocalizedText;
  kind: 'text' | 'pdf' | 'slides' | 'video' | 'quiz';
  body?: LocalizedText;          // sanitized markdown
  assetPath?: string;            // storage path for pdf/slides/video
  durationMinutes?: number;
}

/** question_bank/{questionId} - STAFF ONLY. Candidates never read answers directly. */
export interface Question {
  questionId: string;
  category: string;
  difficulty: 'easy' | 'medium' | 'hard';
  variants: Partial<Record<'en' | 'hi' | 'pa', { stem: string; choices: string[]; explanation?: string }>>;
  correctChoiceIndexes: number[]; // supports single or multi-correct
  active: boolean;
  source: 'original' | 'licensed';
}

export interface AssessmentConfig {
  assessmentId: string;
  courseId: string;
  questionIds?: string[];          // fixed set OR
  pool?: { category: string; count: number }[]; // random draw
  randomizeQuestions: boolean;
  randomizeChoices: boolean;
  passPercent: number;             // 0..100
  maxAttempts: number;             // 0 = unlimited
  retakeCooldownHours: number;
  timeLimitMinutes?: number;
  marksPerQuestion: number;
  negativeMarks: number;           // >= 0
}

/** attempts/{attemptId} - written only by Cloud Functions. */
export interface Attempt {
  attemptId: string; uid: string; assessmentId: string; courseId: string;
  startedAt: EpochMs; submittedAt?: EpochMs; expiresAt?: EpochMs;
  /** Server-chosen question order and per-question choice permutation. */
  servedQuestions: { questionId: string; choiceOrder: number[] }[];
  responses?: Record<string, number[]>;  // questionId -> displayed choice indexes
  scorePercent?: number; marks?: number; maxMarks?: number;
  passed?: boolean;
  status: 'in_progress' | 'submitted' | 'expired';
}

/**
 * certificates/{certificateId} - private (candidate + staff).
 * PORTAL TRAINING AWARD ONLY. This is NOT an IIBF DRA certificate.
 */
export interface PortalCertificate {
  certificateId: string;           // random, unguessable e.g. VRS-TC-2026-8F3K-Q7MZ
  uid: string; candidateId: string;
  candidateNameAtIssue: string;
  courseId: string; courseTitleAtIssue: string; courseVersion: number;
  scorePercent?: number; grade?: string;
  issuedAt: EpochMs;
  attemptId?: string;
  revoked: boolean; revokedReason?: string;
  publicVerificationConsent: boolean;
}

/** certificate_verification/{certificateId} - public, minimal, only exists when the candidate consented. */
export interface PublicCertificateVerification {
  certificateId: string;
  displayName: string;             // e.g. "Rajesh K." per candidate choice
  courseTitle: string;
  issuedOn: string;                // YYYY-MM-DD
  valid: boolean;
  disclaimer: 'portal_training_not_iibf_dra';
}
