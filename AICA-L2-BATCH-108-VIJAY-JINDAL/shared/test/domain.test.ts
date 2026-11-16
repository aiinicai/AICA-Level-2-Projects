import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  newCandidateId, newReferralCode, newCertificateId, isCandidateId, isCertificateId, applicationDocId,
  applyCandidateDraUpdate, draValidationErrors, decideApplication, decideReferral, firstTouchReferral,
  effectiveGrants, canAccess, allowedExportColumns, validateGrantChange, profileCompleteness,
  certificateEligibility, type DraQualification,
} from '../src/index.js';

test('IDs are random, well-formed and not derived from personal data', () => {
  const ids = new Set(Array.from({ length: 5000 }, () => newCandidateId()));
  assert.equal(ids.size, 5000);
  for (const id of [...ids].slice(0, 50)) assert.ok(isCandidateId(id), id);
  assert.match(newReferralCode(), /^R[0-9A-HJKMNP-TV-Z]{6}$/);
  assert.ok(isCertificateId(newCertificateId(2026)));
  assert.ok(!isCertificateId('VRS-TC-2026-AAAA')); // forged/short IDs fail format check
  assert.equal(applicationDocId('VAC-1', 'u1'), 'VAC-1_u1');
});

const approvedDra: DraQualification = {
  status: 'certified', certificateNumber: 'DRA/123456', issuer: 'IIBF', certificateFilePath: 'private/u1/dra/a.pdf',
  certificateFileHash: 'h1', documentReview: { status: 'approved', reviewerUid: 'r1', reviewedAt: 1 },
  issuerVerification: { status: 'verified', checkedAt: 1 }, updatedAt: 1,
};

test('changing DRA certificate number resets review to pending', () => {
  const next = applyCandidateDraUpdate(approvedDra, { ...approvedDra, certificateNumber: 'DRA/999999' }, 2);
  assert.equal(next.documentReview.status, 'pending');
  assert.equal(next.issuerVerification.status, 'not_checked');
});

test('replacing the certificate file resets review to pending', () => {
  const next = applyCandidateDraUpdate(approvedDra, { ...approvedDra, certificateFilePath: 'private/u1/dra/b.pdf', certificateFileHash: 'h2' }, 2);
  assert.equal(next.documentReview.status, 'pending');
});

test('editing unrelated DRA fields keeps the approved review', () => {
  const next = applyCandidateDraUpdate(approvedDra, { ...approvedDra, trainingInstitute: 'Some Institute', certificateNumber: 'dra/123456 ' }, 2);
  assert.equal(next.documentReview.status, 'approved');
});

test('certified without upload is allowed (upload later) but number + issuer required', () => {
  assert.deepEqual(draValidationErrors({ status: 'certified' }), ['certificate_number_required', 'issuer_required']);
  assert.deepEqual(draValidationErrors({ status: 'certified', certificateNumber: 'DRA/1234', issuer: 'IIBF' }), []);
  assert.deepEqual(draValidationErrors({ status: 'not_certified' }), []);
  const first = applyCandidateDraUpdate(undefined, { status: 'certified', certificateNumber: 'DRA/1234', issuer: 'IIBF' }, 1);
  assert.equal(first.documentReview.status, 'not_submitted');
});

const NOW = Date.parse('2026-11-13T06:00:00Z');
const openVacancy = { status: 'published' as const, closingDate: '2026-11-30', certificationPolicy: 'mandatory' as const };

test('repeat application is rejected', () => {
  const d = decideApplication({ vacancy: openVacancy, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: true, nowMs: NOW });
  assert.deepEqual(d, { ok: false, reason: 'already_applied' });
});

test('closed vacancy (status or date) rejects applications', () => {
  assert.deepEqual(decideApplication({ vacancy: { ...openVacancy, status: 'closed' }, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: false, reason: 'vacancy_not_open' });
  assert.deepEqual(decideApplication({ vacancy: { ...openVacancy, closingDate: '2026-11-12' }, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: false, reason: 'vacancy_closed_by_date' });
});

test('closing date is evaluated in IST', () => {
  // 2026-11-12 19:00 UTC = 2026-11-13 00:30 IST -> vacancy closing 2026-11-12 is closed
  const t = Date.parse('2026-11-12T19:00:00Z');
  assert.deepEqual(decideApplication({ vacancy: { ...openVacancy, closingDate: '2026-11-12' }, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: t }), { ok: false, reason: 'vacancy_closed_by_date' });
});

test('disabled account cannot apply', () => {
  assert.deepEqual(decideApplication({ vacancy: openVacancy, accountStatus: 'disabled', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: false, reason: 'account_inactive' });
});

test('mandatory certification: fresher marked not_established; approved DRA marked meets', () => {
  assert.deepEqual(decideApplication({ vacancy: openVacancy, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: true, certificationEligibility: 'not_established' });
  assert.deepEqual(decideApplication({ vacancy: openVacancy, dra: { status: 'certified', documentReview: { status: 'pending' } }, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: true, certificationEligibility: 'not_established' });
  assert.deepEqual(decideApplication({ vacancy: openVacancy, dra: approvedDra, accountStatus: 'active', hasBasicProfile: true, alreadyApplied: false, nowMs: NOW }), { ok: true, certificationEligibility: 'meets' });
});

const refBase = {
  trackingMode: 'on' as const, code: 'R7KM3QX', codeDoc: { ownerUid: 'referrer', active: true }, referrerAccountActive: true,
  referrerPhoneHash: 'hA', newUid: 'newbie', newPhoneHash: 'hB', phoneVerified: true, existingAttributionForNewUid: false,
  phoneHashSeenBefore: false, referrerJoinsLast24h: 0, velocityLimitPer24h: 25,
};

test('referral attribution: legitimate join attributed', () => assert.deepEqual(decideReferral(refBase), { attribute: true }));
test('referral attribution: self-referral by uid or phone blocked', () => {
  assert.deepEqual(decideReferral({ ...refBase, newUid: 'referrer' }), { attribute: false, reason: 'self_referral' });
  assert.deepEqual(decideReferral({ ...refBase, newPhoneHash: 'hA' }), { attribute: false, reason: 'self_referral' });
});
test('referral attribution: duplicates, prior attribution, pause, unverified, velocity', () => {
  assert.deepEqual(decideReferral({ ...refBase, phoneHashSeenBefore: true }), { attribute: false, reason: 'duplicate_phone' });
  assert.deepEqual(decideReferral({ ...refBase, existingAttributionForNewUid: true }), { attribute: false, reason: 'already_attributed' });
  assert.deepEqual(decideReferral({ ...refBase, trackingMode: 'paused' }), { attribute: false, reason: 'tracking_disabled' });
  assert.deepEqual(decideReferral({ ...refBase, phoneVerified: false }), { attribute: false, reason: 'not_verified' });
  assert.deepEqual(decideReferral({ ...refBase, codeDoc: undefined }), { attribute: false, reason: 'unknown_code' });
  assert.deepEqual(decideReferral({ ...refBase, referrerJoinsLast24h: 25 }), { attribute: false, reason: 'velocity_limit' });
});
test('first-touch referral is never overwritten', () => {
  assert.equal(firstTouchReferral('RAAAAAA', 'RBBBBBB'), 'RAAAAAA');
  assert.equal(firstTouchReferral(null, 'RBBBBBB'), 'RBBBBBB');
});

test('roles: viewer/recruiter cannot export; owner can; disabled or no-MFA staff get nothing', () => {
  const viewer = { role: 'viewer' as const, disabled: false, mfaVerified: true, grants: effectiveGrants('viewer') };
  const recruiter = { role: 'recruiter' as const, disabled: false, mfaVerified: true, grants: effectiveGrants('recruiter') };
  assert.equal(allowedExportColumns(viewer.grants, ['candidateId']), 'forbidden');
  assert.equal(allowedExportColumns(recruiter.grants, ['candidateId', 'mobile']), 'forbidden');
  assert.ok(!canAccess(recruiter, 'identity.restricted'));
  assert.ok(!canAccess({ ...recruiter, disabled: true }, 'profile.basic'));
  assert.ok(!canAccess({ ...recruiter, mfaVerified: false }, 'profile.basic'));
  const recruiterWithExport = effectiveGrants('recruiter', ['export.csv']);
  assert.deepEqual(allowedExportColumns(recruiterWithExport, ['candidateId', 'mobile', 'dateOfBirth', 'hackerField']), ['candidateId', 'mobile']);
  assert.equal(validateGrantChange('recruiter', 'viewer', ['export.csv']), 'only_owner_admin');
  assert.equal(validateGrantChange('owner_admin', 'owner_admin', []), 'owner_admin_not_assignable_via_ui');
  assert.equal(validateGrantChange('owner_admin', 'viewer', ['profile.basic']), null);
});

test('profile completeness for incomplete fresher and certified candidate', () => {
  const r = profileCompleteness({ fullName: 'A B', draStatus: 'not_certified', location: { stateCode: 'PB', city: 'Moga', pin: '142001' } });
  assert.equal(r.level, 'registration_only');
  assert.ok(r.missing.includes('experienceType'));
  assert.ok(!r.missing.includes('draDetails'));
  const c = profileCompleteness({ fullName: 'A B', draStatus: 'certified', experienceType: 'fresher', location: { stateCode: 'PB', city: 'Moga', pin: '142001' } });
  assert.ok(c.missing.includes('draDetails') && c.missing.includes('draCertificateUpload'));
  assert.equal(c.level, 'partial');
});

test('certificate cannot be issued unless all requirements met', () => {
  const ok = { courseCertificateEnabled: true, requireAllLessons: true, totalLessons: 2, allLessonIds: ['a', 'b'], completedLessonIds: ['a', 'b'],
    finalAssessmentRequired: true, passedFinalAssessment: true, alreadyIssued: false, accountActive: true };
  assert.deepEqual(certificateEligibility(ok), { eligible: true });
  assert.deepEqual(certificateEligibility({ ...ok, completedLessonIds: ['a'] }), { eligible: false, reason: 'lessons_incomplete' });
  assert.deepEqual(certificateEligibility({ ...ok, passedFinalAssessment: false }), { eligible: false, reason: 'assessment_not_passed' });
  assert.deepEqual(certificateEligibility({ ...ok, alreadyIssued: true }), { eligible: false, reason: 'already_issued' });
  assert.deepEqual(certificateEligibility({ ...ok, accountActive: false }), { eligible: false, reason: 'account_inactive' });
});
