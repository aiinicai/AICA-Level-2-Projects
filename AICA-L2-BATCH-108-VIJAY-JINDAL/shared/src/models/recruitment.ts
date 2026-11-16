import type { EpochMs, AuditStamp } from './common.js';
import type { CollectionRole } from './candidate.js';
export type { CollectionRole };

export type VacancyStatus = 'draft' | 'published' | 'closed' | 'archived';
export type CertificationPolicy = 'mandatory' | 'preferred' | 'not_required';

/** vacancies/{vacancyId} - public read only when status == 'published'. */
export interface Vacancy extends AuditStamp {
  vacancyId: string;              // e.g. VAC-2026-000123
  title: string;
  role: CollectionRole;
  openings: number;
  stateCode: string; district?: string; city: string;
  employerDisplayName?: string;   // only when the employer approved display
  employerDisplayApproved: boolean;
  requirements: string[];
  certificationPolicy: CertificationPolicy;
  minExperienceMonths: number;
  salaryMinInr?: number; salaryMaxInr?: number;
  joiningNeed: 'immediate' | 'within_15_days' | 'within_30_days' | 'flexible';
  closingDate: string;            // YYYY-MM-DD (IST end of day)
  description: string;
  status: VacancyStatus;
  products?: string[];
}

export type RecruitmentStage =
  | 'new' | 'screening' | 'contacted' | 'shortlisted' | 'interview_scheduled' | 'selected'
  | 'offered' | 'joined' | 'follow_up_due' | 'unreachable' | 'not_interested' | 'rejected' | 'vacancy_closed';

export const RECRUITMENT_STAGES: readonly RecruitmentStage[] = [
  'new', 'screening', 'contacted', 'shortlisted', 'interview_scheduled', 'selected', 'offered', 'joined',
  'follow_up_due', 'unreachable', 'not_interested', 'rejected', 'vacancy_closed',
];

/** Candidate-visible status mapping (internal stages are simplified for candidates). */
export type CandidateVisibleStatus = 'received' | 'under_review' | 'interview' | 'selected' | 'not_progressed' | 'closed';

/**
 * applications/{vacancyId}_{uid}
 * Deterministic ID guarantees one application per candidate per vacancy.
 * Created only by the submitApplication Cloud Function.
 */
export interface Application {
  applicationId: string;
  vacancyId: string;
  uid: string;
  candidateId: string;
  submittedAt: EpochMs;
  certificationEligibility: 'meets' | 'not_established' | 'not_required';
  candidateStatus: CandidateVisibleStatus;
}

/** applications_internal/{applicationId} - staff only. Notes are never visible to candidates. */
export interface ApplicationInternal {
  stage: RecruitmentStage;
  assignedRecruiterUid?: string;
  followUpDate?: string;
  interviewAt?: EpochMs;
  reasonCode?: string;
  updatedAt: EpochMs;
}

/** applications_internal/{applicationId}/events/{eventId} - append-only history. */
export interface RecruitmentEvent {
  at: EpochMs;
  byUid: string;
  type: 'stage_change' | 'note' | 'assignment' | 'interview' | 'follow_up';
  fromStage?: RecruitmentStage; toStage?: RecruitmentStage;
  note?: string;
}
