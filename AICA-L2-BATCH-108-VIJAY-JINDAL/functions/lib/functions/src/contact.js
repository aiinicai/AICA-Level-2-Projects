import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { getFirestore } from 'firebase-admin/firestore';
import { randomBytes } from 'node:crypto';
import { REGION } from './config.js';
import { writeAudit } from './audit.js';
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_REGEX = /^(\+91[\-\s]?)?[6-9]\d{9}$/;
export const submitContactForm = onCall({ region: REGION, maxInstances: 20 }, async (req) => {
    const data = req.data;
    if (!data)
        throw new HttpsError('invalid-argument', 'missing_payload');
    const name = String(data.name || '').trim();
    const email = String(data.email || '').trim().toLowerCase();
    const phone = String(data.phone || '').trim();
    const category = data.category;
    const subject = String(data.subject || '').trim();
    const message = String(data.message || '').trim();
    if (!name || name.length < 2 || name.length > 100) {
        throw new HttpsError('invalid-argument', 'name_invalid');
    }
    if (!email || !EMAIL_REGEX.test(email) || email.length > 120) {
        throw new HttpsError('invalid-argument', 'email_invalid');
    }
    if (!phone || !PHONE_REGEX.test(phone.replace(/\s+/g, ''))) {
        throw new HttpsError('invalid-argument', 'phone_invalid');
    }
    const validCategories = [
        'candidate_inquiry',
        'employer_hiring',
        'institute_listing',
        'verification_query',
        'grievance_feedback',
    ];
    if (!category || !validCategories.includes(category)) {
        throw new HttpsError('invalid-argument', 'category_invalid');
    }
    if (!subject || subject.length < 3 || subject.length > 150) {
        throw new HttpsError('invalid-argument', 'subject_invalid');
    }
    if (!message || message.length < 10 || message.length > 3000) {
        throw new HttpsError('invalid-argument', 'message_invalid');
    }
    const db = getFirestore();
    const now = Date.now();
    const messageId = `msg_${now}_${randomBytes(4).toString('hex')}`;
    const contactDoc = {
        messageId,
        name,
        email,
        phone,
        category,
        subject,
        message,
        status: 'unread',
        createdAt: now,
    };
    await db.doc(`contact_messages/${messageId}`).set(contactDoc);
    return {
        success: true,
        messageId,
    };
});
export const updateContactMessageStatus = onCall({ region: REGION, maxInstances: 10 }, async (req) => {
    const uid = req.auth?.uid;
    const token = req.auth?.token;
    if (!uid)
        throw new HttpsError('unauthenticated', 'sign_in_required');
    const isOwner = token?.role === 'owner_admin';
    const hasCms = Array.isArray(token?.grants) && token.grants.includes('cms.manage');
    if (!isOwner && !hasCms) {
        throw new HttpsError('permission-denied', 'insufficient_privileges');
    }
    const messageId = req.data?.messageId;
    const status = req.data?.status;
    const staffNotes = req.data?.staffNotes;
    if (!messageId)
        throw new HttpsError('invalid-argument', 'message_id_required');
    if (!status || !['unread', 'in_progress', 'resolved'].includes(status)) {
        throw new HttpsError('invalid-argument', 'invalid_status');
    }
    const db = getFirestore();
    const docRef = db.doc(`contact_messages/${messageId}`);
    const snap = await docRef.get();
    if (!snap.exists)
        throw new HttpsError('not-found', 'message_not_found');
    const now = Date.now();
    const updateData = {
        status,
        staffNotes: staffNotes ?? undefined,
    };
    if (status === 'resolved') {
        updateData.resolvedAt = now;
        updateData.resolvedBy = uid;
    }
    await docRef.update(updateData);
    writeAudit({
        actorUid: uid,
        actorRole: isOwner ? 'owner_admin' : 'recruiter',
        action: 'contact.message_status',
        targetType: 'contact_message',
        targetId: messageId,
        meta: {
            newStatus: status,
        },
    });
    return {
        success: true,
        messageId,
        status,
    };
});
//# sourceMappingURL=contact.js.map