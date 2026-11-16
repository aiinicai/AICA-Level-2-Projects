import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';
import { REGION } from './config.js';
import { writeAudit } from './audit.js';
import { applyCandidateDraUpdate, draValidationErrors } from '../../shared/src/domain/dra.js';
import { profileCompleteness } from '../../shared/src/domain/completeness.js';
export const updateDraQualification = onCall({ region: REGION, maxInstances: 20 }, async (req) => {
    const uid = req.auth?.uid;
    if (!uid)
        throw new HttpsError('unauthenticated', 'sign_in_required');
    const data = req.data;
    if (!data?.status)
        throw new HttpsError('invalid-argument', 'status_required');
    const valErrors = draValidationErrors({
        status: data.status,
        certificateNumber: data.certificateNumber,
        issuer: data.issuer,
    });
    if (valErrors.length > 0) {
        throw new HttpsError('invalid-argument', valErrors.join(', '));
    }
    const db = getFirestore();
    const candidateRef = db.doc(`candidates/${uid}`);
    const candidateSnap = await candidateRef.get();
    if (!candidateSnap.exists)
        throw new HttpsError('not-found', 'candidate_not_found');
    if (candidateSnap.get('accountStatus') !== 'active')
        throw new HttpsError('permission-denied', 'account_inactive');
    const draRef = db.doc(`candidates/${uid}/dra/current`);
    const currentSnap = await draRef.get();
    const currentDra = currentSnap.exists ? currentSnap.data() : undefined;
    const now = Date.now();
    const updatedDra = applyCandidateDraUpdate(currentDra, {
        status: data.status,
        certificateNumber: data.certificateNumber ? data.certificateNumber.trim().toUpperCase() : undefined,
        issuer: data.issuer?.trim(),
        nameOnCertificate: data.nameOnCertificate?.trim(),
        issueOrPassingDate: data.issueOrPassingDate,
        trainingInstitute: data.trainingInstitute?.trim(),
        certificateFilePath: data.certificateFilePath,
        certificateFileHash: data.certificateFileHash,
    }, now);
    await draRef.set(updatedDra, { merge: true });
    const subSnap = await db.doc(`candidates/${uid}/occupations/collections`).get();
    const sub = subSnap.exists ? subSnap.data() : undefined;
    const core = candidateSnap.data();
    const report = profileCompleteness({ ...core, draStatus: data.status }, sub, updatedDra);
    await candidateRef.update({
        draStatus: data.status,
        completeness: report.level,
        updatedAt: FieldValue.serverTimestamp(),
    });
    writeAudit({
        actorUid: uid,
        actorRole: 'candidate',
        action: 'document.review',
        targetType: 'candidate',
        targetId: core.candidateId,
        meta: {
            status: data.status,
            hasFile: Boolean(data.certificateFilePath),
            reviewStatus: updatedDra.documentReview.status,
        },
    });
    return { success: true, dra: updatedDra, completeness: report };
});
//# sourceMappingURL=dra.js.map