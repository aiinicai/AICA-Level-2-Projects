import type { EpochMs } from './common.js';

/**
 * candidates/{uid}/dra/current
 * OFFICIAL DRA qualification claimed by the candidate. Kept completely separate from portal training awards
 * (see models/training.ts -> PortalCertificate). A portal course certificate must NEVER be stored here.
 */
export interface DraQualification {
  status: 'certified' | 'training_in_progress' | 'result_awaited' | 'not_certified';
  certificateNumber?: string;
  issuer?: string;                     // e.g. "IIBF" - free text from reviewed list
  nameOnCertificate?: string;
  issueOrPassingDate?: string;         // YYYY-MM-DD
  trainingInstitute?: string;
  certificateFilePath?: string;        // private storage path
  certificateFileHash?: string;        // sha256 set by server on upload
  /** Staff document review - our internal check of the uploaded document. */
  documentReview: DocumentReview;
  /** Official issuer verification - only set when checked with the issuer's own system/records. */
  issuerVerification: {
    status: 'not_checked' | 'verified' | 'not_found' | 'mismatch';
    checkedAt?: EpochMs; checkedBy?: string; sourceNote?: string;
  };
  updatedAt: EpochMs;
}

export type DocumentReviewStatus =
  | 'not_submitted' | 'pending' | 'in_review' | 'approved' | 'needs_correction' | 'rejected';

export interface DocumentReview {
  status: DocumentReviewStatus;
  reviewerUid?: string;
  reviewedAt?: EpochMs;
  reasonCode?: string;
}
