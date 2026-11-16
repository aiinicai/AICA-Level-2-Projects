import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore } from 'firebase-admin/firestore';
import { randomBytes } from 'node:crypto';
import { REGION } from './config.js';
import { writeAudit } from './audit.js';
import type { DataRightRequest, DataRightType } from '../../shared/src/models/consent.js';
import type { CandidateCore } from '../../shared/src/models/candidate.js';

export const requestDataRights = onCall(
  { region: REGION, maxInstances: 10 },
  async (req) => {
    const uid = req.auth?.uid;
    if (!uid) throw new HttpsError('unauthenticated', 'sign_in_required');

    const type = req.data?.type as DataRightType | undefined;
    const details = String(req.data?.details || '').trim();

    const validTypes: DataRightType[] = ['correction', 'closure', 'deletion', 'consent_withdrawal'];
    if (!type || !validTypes.includes(type)) {
      throw new HttpsError('invalid-argument', 'invalid_request_type');
    }

    if (!details || details.length < 5 || details.length > 2000) {
      throw new HttpsError('invalid-argument', 'details_required');
    }

    const db = getFirestore();
    const candidateRef = db.doc(`candidates/${uid}`);
    const candidateSnap = await candidateRef.get();
    if (!candidateSnap.exists) {
      throw new HttpsError('not-found', 'candidate_profile_not_found');
    }

    const candidate = candidateSnap.data() as CandidateCore;
    const now = Date.now();
    const requestId = `dr_${now}_${randomBytes(4).toString('hex')}`;

    const requestDoc: DataRightRequest = {
      requestId,
      uid,
      candidateId: candidate.candidateId,
      type,
      details,
      status: 'received',
      createdAt: now,
    };

    const batch = db.batch();
    batch.set(db.doc(`data_requests/${requestId}`), requestDoc);

    // If candidate requested immediate account closure, mark candidate status closed
    if (type === 'closure') {
      batch.update(candidateRef, {
        accountStatus: 'closed',
        updatedAt: now,
      });
    }

    await batch.commit();

    // Tamper-evident audit logging
    const auditAction =
      type === 'closure'
        ? 'account.closure'
        : type === 'deletion'
        ? 'account.deletion'
        : type === 'consent_withdrawal'
        ? 'consent.change'
        : 'settings.change';

    writeAudit({
      actorUid: uid,
      actorRole: 'candidate',
      action: auditAction,
      targetType: 'candidate',
      targetId: candidate.candidateId,
      meta: {
        requestId,
        type,
      },
    });

    return {
      success: true,
      requestId,
      status: 'received',
    };
  },
);
