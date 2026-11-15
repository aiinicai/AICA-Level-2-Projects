/**
 * completeRegistration (Phase 2) - called after the candidate verifies their mobile with Firebase Phone Auth.
 * Creates the candidate core profile, permanent candidate ID, referral code, consent records and referral attribution
 * in ONE transaction. Idempotent: calling twice returns the existing profile.
 * STATUS: written against the shared, unit-tested domain logic; must be exercised in the emulator in Phase 2.
 */
import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore, FieldValue, Timestamp } from 'firebase-admin/firestore';
import { createHmac } from 'node:crypto';
import { REGION, PHONE_HASH_KEY, PRIVACY_NOTICE_VERSION, REFERRAL_VELOCITY_PER_24H } from './config.js';
import { safeLog } from './log.js';
import { writeAudit } from './audit.js';
import { validateRegistration, type RegistrationInput } from '../../shared/src/validation/registration.js';
import { newCandidateId, newReferralCode } from '../../shared/src/ids.js';
import { decideReferral } from '../../shared/src/domain/referral.js';

export const completeRegistration = onCall(
  { region: REGION, secrets: [PHONE_HASH_KEY], enforceAppCheck: process.env.ENFORCE_APP_CHECK === 'true', maxInstances: 20 },
  async (req) => {
    const uid = req.auth?.uid;
    const phone = req.auth?.token.phone_number as string | undefined;
    if (!uid || !phone) throw new HttpsError('unauthenticated', 'verify_mobile_first');

    const input = req.data as RegistrationInput;
    if (input?.noticeVersion !== PRIVACY_NOTICE_VERSION.value()) throw new HttpsError('failed-precondition', 'notice_version_outdated');
    const v = validateRegistration(input);
    if (!v.ok) throw new HttpsError('invalid-argument', 'validation_failed', v.errors);
    const reg = v.value;

    const db = getFirestore();
    const site = (await db.doc('cms_public/site').get()).data() ?? {};
    if (site.maintenanceMode?.enabled) throw new HttpsError('unavailable', 'maintenance');
    if (site.features?.registrationOpen === false) throw new HttpsError('failed-precondition', 'registration_closed');
    const trackingMode = (site.features?.referralTracking ?? 'off') as 'on' | 'paused' | 'off';

    const secretKey = PHONE_HASH_KEY.value() || process.env.PHONE_HASH_KEY || 'vrs-staging-phone-hash-default';
    const phoneHash = createHmac('sha256', secretKey).update(phone).digest('hex');
    const candidateRef = db.doc(`candidates/${uid}`);

    const result = await db.runTransaction(async (tx) => {
      const existing = await tx.get(candidateRef);
      if (existing.exists) return { candidateId: existing.get('candidateId') as string, created: false };

      const phoneIdxRef = db.doc(`phone_index/${phoneHash}`);
      const phoneIdx = await tx.get(phoneIdxRef);
      const phoneHashSeenBefore = phoneIdx.exists && phoneIdx.get('uid') !== uid;

      // Unique IDs (retry on the astronomically unlikely collision)
      let candidateId = '', referralCode = '';
      for (let i = 0; i < 5 && !candidateId; i++) { const c = newCandidateId(); if (!(await tx.get(db.doc(`candidate_ids/${c}`))).exists) candidateId = c; }
      for (let i = 0; i < 5 && !referralCode; i++) { const c = newReferralCode(); if (!(await tx.get(db.doc(`referral_codes/${c}`))).exists) referralCode = c; }
      if (!candidateId || !referralCode) throw new HttpsError('aborted', 'id_generation_failed');

      // Referral decision (server-authoritative)
      let attribution: { referrerUid: string; status: 'attributed' | 'rejected'; reason?: string } | null = null;
      if (reg.referralCode) {
        const codeSnap = await tx.get(db.doc(`referral_codes/${reg.referralCode}`));
        const codeDoc = codeSnap.exists ? (codeSnap.data() as { ownerUid: string; active: boolean }) : undefined;
        let referrerActive = false, referrerPhoneHash: string | undefined, joins24h = 0;
        if (codeDoc) {
          const ref = await tx.get(db.doc(`candidates/${codeDoc.ownerUid}`));
          referrerActive = ref.get('accountStatus') === 'active';
          referrerPhoneHash = (await tx.get(db.doc(`candidates_private_hash/${codeDoc.ownerUid}`))).get('phoneHash');
          const since = Timestamp.fromMillis(Date.now() - 86_400_000);
          joins24h = (await tx.get(db.collection('referral_attributions').where('referrerUid', '==', codeDoc.ownerUid)
            .where('status', '==', 'attributed').where('at', '>=', since).count())).data().count;
        }
        const d = decideReferral({
          trackingMode, code: reg.referralCode, codeDoc, referrerAccountActive: referrerActive, referrerPhoneHash,
          newUid: uid, newPhoneHash: phoneHash, phoneVerified: true, existingAttributionForNewUid: false,
          phoneHashSeenBefore, referrerJoinsLast24h: joins24h, velocityLimitPer24h: Number(REFERRAL_VELOCITY_PER_24H.value()),
        });
        // Record an attribution row only when a real referrer exists (unknown codes have nobody to credit).
        if (codeDoc && d.attribute) {
          attribution = { referrerUid: codeDoc.ownerUid, status: 'attributed' };
          tx.set(db.doc(`referral_stats/${codeDoc.ownerUid}`), { verifiedJoins: FieldValue.increment(1), lastJoinAt: FieldValue.serverTimestamp() }, { merge: true });
        } else if (codeDoc && !d.attribute && d.reason !== null) {
          attribution = { referrerUid: codeDoc.ownerUid, status: 'rejected', reason: d.reason };
          tx.set(db.doc(`referral_stats/${codeDoc.ownerUid}`), { rejected: FieldValue.increment(1) }, { merge: true });
        }
      }

      const now = FieldValue.serverTimestamp();
      tx.create(db.doc(`candidate_ids/${candidateId}`), { uid });
      tx.create(db.doc(`referral_codes/${referralCode}`), { code: referralCode, ownerUid: uid, active: true, createdAt: now });
      tx.set(phoneIdxRef, { uid, at: now });
      tx.create(db.doc(`candidates_private_hash/${uid}`), { phoneHash });
      tx.create(candidateRef, {
        uid, candidateId, referralCode, fullName: reg.fullName, mobileE164: phone, whatsappSameAsMobile: true, emailVerified: false,
        preferredLanguage: reg.preferredLanguage,
        location: { stateCode: reg.stateCode, city: reg.city, pin: reg.pin, pinMismatchFlag: reg.pinMismatch },
        draStatus: reg.draStatus, primaryRole: reg.preferredRole, occupations: ['collections'],
        experienceType: null, relevantExperienceMonths: null, languagesKnown: [], completeness: 'registration_only',
        accountStatus: 'active',
        source: reg.referralCode ? { kind: 'referral', referralCode: reg.referralCode, campaign: reg.campaign ?? null, firstSeenAt: now }
          : { kind: reg.campaign ? 'campaign' : 'direct', campaign: reg.campaign ?? null, firstSeenAt: now },
        ageAttestation18Plus: { accepted: true, at: now, policyVersion: reg.noticeVersion },
        searchTokens: [...new Set([...reg.fullName.toLowerCase().split(' '), reg.city.toLowerCase()])].filter((t) => t.length > 1),
        createdAt: now, updatedAt: now,
      });
      tx.create(db.doc(`candidates/${uid}/dra/current`), {
        status: reg.draStatus, documentReview: { status: 'not_submitted' }, issuerVerification: { status: 'not_checked' }, updatedAt: now,
      });
      const consents: [string, boolean][] = [['privacy_notice', true], ['terms', true], ['recruitment_contact', true],
        ['marketing', reg.consents.marketing], ['whatsapp_updates', reg.consents.whatsappUpdates]];
      for (const [purpose, granted] of consents) {
        tx.create(db.collection(`candidates/${uid}/consents`).doc(), { purpose, granted, noticeVersion: reg.noticeVersion, at: now, channel: 'web' });
      }
      if (attribution) {
        tx.create(db.doc(`referral_attributions/${uid}`), { newUid: uid, code: reg.referralCode, campaign: reg.campaign ?? null, at: now, ...attribution });
        writeAudit({ actorUid: uid, actorRole: 'system', action: attribution.status === 'attributed' ? 'referral.attributed' : 'referral.rejected',
          targetType: 'candidate', targetId: candidateId, ...(attribution.reason ? { meta: { reason: attribution.reason } } : {}) }, tx);
      }
      return { candidateId, created: true };
    });

    safeLog('info', 'registration_complete', { uid, created: result.created });
    return result;
  },
);
