import type { EpochMs } from './common.js';

export type ConsentPurpose =
  | 'privacy_notice'          // acknowledgement of the privacy notice version
  | 'terms'
  | 'recruitment_contact'     // calls/messages about jobs
  | 'marketing'               // promotional updates (separate, optional)
  | 'whatsapp_updates'        // separate opt-in
  | 'employer_sharing'        // share profile with external employers
  | 'ai_resume_processing'    // send minimised resume text to AI provider
  | 'certificate_public_verification';

/** candidates/{uid}/consents/{autoId} - append-only ledger; latest record per purpose wins. */
export interface ConsentRecord {
  purpose: ConsentPurpose;
  granted: boolean;
  noticeVersion: string;      // e.g. "privacy-2026-11-draft1"
  at: EpochMs;
  channel: 'web' | 'pwa' | 'staff_assisted';
}

export const REQUIRED_REGISTRATION_CONSENTS: readonly ConsentPurpose[] = ['privacy_notice', 'terms', 'recruitment_contact'];

export type DataRightType = 'correction' | 'closure' | 'deletion' | 'consent_withdrawal';

/** data_requests/{requestId} - DPDP Act 2023 candidate rights request ledger */
export interface DataRightRequest {
  requestId: string;
  uid: string;
  candidateId: string;
  type: DataRightType;
  details: string;
  status: 'received' | 'in_review' | 'completed' | 'rejected';
  createdAt: EpochMs;
  resolvedAt?: EpochMs;
  resolvedBy?: string;
  resolutionNotes?: string;
}
