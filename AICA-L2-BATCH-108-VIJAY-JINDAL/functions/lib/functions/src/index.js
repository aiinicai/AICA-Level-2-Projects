import { initializeApp } from 'firebase-admin/app';
initializeApp();
export { completeRegistration } from './registration.js';
export { updateDraQualification } from './dra.js';
export { aiImproveResumeSummary } from './ai.js';
export { submitApplication, updateApplicationStage } from './recruitment.js';
export { startAssessmentAttempt, submitAssessmentAttempt } from './training.js';
export { submitContactForm, updateContactMessageStatus } from './contact.js';
export { requestDataRights } from './privacy.js';
/*
 * Planned privileged functions (implemented in later phases; listed so the security model is visible now):
 * Phase 3: updateDraQualification, reviewDraDocument, processUpload (magic-byte check, move from incoming/), getDocumentLink (signed URL + audit),
 *          setStaffRole / disableStaff (owner admin only, custom claims), requestDataRights (correction/closure/deletion), savePan (encrypted)
 * Phase 4: generateResumePdf (deterministic, no AI), aiImproveResume (Gemini via provider abstraction, consent-gated)
 * Phase 5: submitApplication, updateApplicationStage, runExport (field-level, logged), availabilityReminder (scheduled)
 * Phase 6: startAttempt, submitAttempt (server scoring), issueCertificate, setCertificateVisibility
 * Phase 7: submitContactForm (validated, rate-limited, App Check, email via secret SMTP/API), reports
 * Phase 8: scheduled Firestore export + restore-test runbook
 */
//# sourceMappingURL=index.js.map