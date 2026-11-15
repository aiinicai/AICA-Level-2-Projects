import { getFirestore, FieldValue } from 'firebase-admin/firestore';
/** Audit entries contain internal IDs only - never phone numbers, PAN or document contents. */
export function writeAudit(entry, tx) {
    const ref = getFirestore().collection('audit_logs').doc();
    const data = { ...entry, at: FieldValue.serverTimestamp() };
    return tx ? void tx.create(ref, data) : ref.create(data);
}
//# sourceMappingURL=audit.js.map