/** Server-side rule: a portal course certificate may be issued only when every requirement is met. */
export function certificateEligibility(args: {
  courseCertificateEnabled: boolean;
  requireAllLessons: boolean;
  totalLessons: number;
  completedLessonIds: readonly string[];
  allLessonIds: readonly string[];
  finalAssessmentRequired: boolean;
  passedFinalAssessment: boolean;
  alreadyIssued: boolean;
  accountActive: boolean;
}): { eligible: true } | { eligible: false; reason: string } {
  if (!args.accountActive) return { eligible: false, reason: 'account_inactive' };
  if (!args.courseCertificateEnabled) return { eligible: false, reason: 'certificate_not_enabled' };
  if (args.alreadyIssued) return { eligible: false, reason: 'already_issued' };
  if (args.requireAllLessons) {
    const done = new Set(args.completedLessonIds);
    if (!args.allLessonIds.every((id) => done.has(id))) return { eligible: false, reason: 'lessons_incomplete' };
  }
  if (args.finalAssessmentRequired && !args.passedFinalAssessment) return { eligible: false, reason: 'assessment_not_passed' };
  return { eligible: true };
}

export const PORTAL_CERTIFICATE_DISCLAIMER_EN =
  'This is a free training course completion certificate issued by the portal operator. It is NOT an IIBF DRA certificate ' +
  'and does not replace the mandatory accredited DRA training or the official IIBF examination.';
