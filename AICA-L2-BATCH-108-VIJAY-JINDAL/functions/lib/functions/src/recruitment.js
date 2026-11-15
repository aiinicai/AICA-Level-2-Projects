import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore } from 'firebase-admin/firestore';
import { REGION } from './config.js';
import { writeAudit } from './audit.js';
import { decideApplication } from '../../shared/src/domain/applications.js';
export const submitApplication = onCall({ region: REGION, maxInstances: 20 }, async (req) => {
    const uid = req.auth?.uid;
    if (!uid)
        throw new HttpsError('unauthenticated', 'sign_in_required');
    const vacancyId = req.data?.vacancyId;
    if (!vacancyId)
        throw new HttpsError('invalid-argument', 'vacancy_id_required');
    const db = getFirestore();
    const candidateRef = db.doc(`candidates/${uid}`);
    const candidateSnap = await candidateRef.get();
    if (!candidateSnap.exists)
        throw new HttpsError('not-found', 'candidate_profile_required');
    const candidate = candidateSnap.data();
    const vacancyRef = db.doc(`vacancies/${vacancyId}`);
    const vacancySnap = await vacancyRef.get();
    if (!vacancySnap.exists)
        throw new HttpsError('not-found', 'vacancy_not_found');
    const vacancy = vacancySnap.data();
    const draSnap = await db.doc(`candidates/${uid}/dra/current`).get();
    const dra = draSnap.exists ? draSnap.data() : undefined;
    const appDocId = `${vacancyId}_${uid}`;
    const appRef = db.doc(`applications/${appDocId}`);
    const appSnap = await appRef.get();
    const decision = decideApplication({
        vacancy: {
            status: vacancy.status,
            closingDate: vacancy.closingDate,
            certificationPolicy: vacancy.certificationPolicy,
        },
        dra: dra ? { status: dra.status, documentReview: dra.documentReview } : undefined,
        accountStatus: candidate.accountStatus,
        hasBasicProfile: Boolean(candidate.fullName && candidate.location?.city),
        alreadyApplied: appSnap.exists,
        nowMs: Date.now(),
    });
    if (!decision.ok) {
        throw new HttpsError('failed-precondition', decision.reason);
    }
    const now = Date.now();
    const application = {
        applicationId: appDocId,
        vacancyId,
        uid,
        candidateId: candidate.candidateId,
        submittedAt: now,
        certificationEligibility: decision.certificationEligibility,
        candidateStatus: 'received',
    };
    const internal = {
        stage: 'new',
        updatedAt: now,
    };
    const batch = db.batch();
    batch.set(appRef, application);
    batch.set(db.doc(`applications_internal/${appDocId}`), internal);
    batch.set(db.collection(`applications_internal/${appDocId}/events`).doc(), {
        at: now,
        byUid: uid,
        type: 'stage_change',
        toStage: 'new',
        note: 'Application submitted by candidate',
    });
    await batch.commit();
    writeAudit({
        actorUid: uid,
        actorRole: 'candidate',
        action: 'document.review',
        targetType: 'application',
        targetId: appDocId,
        meta: {
            vacancyId,
            candidateId: candidate.candidateId,
            eligibility: decision.certificationEligibility,
        },
    });
    return {
        success: true,
        applicationId: appDocId,
        certificationEligibility: decision.certificationEligibility,
    };
});
const STAGE_TO_CANDIDATE_STATUS = {
    new: 'received',
    screening: 'under_review',
    contacted: 'under_review',
    shortlisted: 'under_review',
    interview_scheduled: 'interview',
    selected: 'selected',
    offered: 'selected',
    joined: 'selected',
    follow_up_due: 'under_review',
    unreachable: 'not_progressed',
    not_interested: 'not_progressed',
    rejected: 'not_progressed',
    vacancy_closed: 'closed',
};
export const updateApplicationStage = onCall({ region: REGION, maxInstances: 20 }, async (req) => {
    const staffUid = req.auth?.uid;
    const role = req.auth?.token.role;
    const grants = req.auth?.token.grants ?? [];
    if (!staffUid || (role !== 'owner_admin' && !grants.includes('notes.recruitment'))) {
        throw new HttpsError('permission-denied', 'staff_permission_required');
    }
    const applicationId = req.data?.applicationId;
    const newStage = req.data?.stage;
    const note = req.data?.note;
    const assignedRecruiterUid = req.data?.assignedRecruiterUid;
    const followUpDate = req.data?.followUpDate;
    const interviewAt = req.data?.interviewAt;
    if (!applicationId || !newStage) {
        throw new HttpsError('invalid-argument', 'application_id_and_stage_required');
    }
    const db = getFirestore();
    const appRef = db.doc(`applications/${applicationId}`);
    const internalRef = db.doc(`applications_internal/${applicationId}`);
    const internalSnap = await internalRef.get();
    if (!internalSnap.exists)
        throw new HttpsError('not-found', 'application_not_found');
    const prevStage = internalSnap.data()?.stage ?? 'new';
    const now = Date.now();
    const candidateStatus = STAGE_TO_CANDIDATE_STATUS[newStage] ?? 'under_review';
    const batch = db.batch();
    batch.update(internalRef, {
        stage: newStage,
        ...(assignedRecruiterUid ? { assignedRecruiterUid } : {}),
        ...(followUpDate ? { followUpDate } : {}),
        ...(interviewAt ? { interviewAt } : {}),
        updatedAt: now,
    });
    batch.update(appRef, {
        candidateStatus,
    });
    batch.set(db.collection(`applications_internal/${applicationId}/events`).doc(), {
        at: now,
        byUid: staffUid,
        type: 'stage_change',
        fromStage: prevStage,
        toStage: newStage,
        note: note || undefined,
    });
    await batch.commit();
    return { success: true, stage: newStage, candidateStatus };
});
//# sourceMappingURL=recruitment.js.map