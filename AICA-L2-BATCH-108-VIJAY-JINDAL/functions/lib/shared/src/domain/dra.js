const norm = (s) => (s ?? '').replace(/\s+/g, '').toUpperCase();
/**
 * Applies a candidate's DRA update. Rule: changing the certificate number OR the certificate file
 * resets the staff document review to 'pending' (or 'not_submitted' if no file) and clears issuer verification.
 * Candidates can never set review/verification fields themselves - those are copied from `current`.
 */
export function applyCandidateDraUpdate(current, update, now) {
    const certificateChanged = !current ||
        norm(current.certificateNumber) !== norm(update.certificateNumber) ||
        (current.certificateFileHash ?? '') !== (update.certificateFileHash ?? '') ||
        (current.certificateFilePath ?? '') !== (update.certificateFilePath ?? '');
    const hasFile = Boolean(update.certificateFilePath);
    const resetReview = { status: hasFile ? 'pending' : 'not_submitted' };
    // Not-certified candidates should not carry stale certificate details.
    const certFields = update.status === 'not_certified'
        ? { certificateNumber: undefined, issuer: undefined, nameOnCertificate: undefined, issueOrPassingDate: undefined, certificateFilePath: undefined, certificateFileHash: undefined }
        : {};
    return {
        ...update,
        ...certFields,
        documentReview: certificateChanged || !current ? { ...resetReview } : current.documentReview,
        issuerVerification: certificateChanged || !current ? { status: 'not_checked' } : current.issuerVerification,
        updatedAt: now,
    };
}
/** Conditional requirements: certified candidates must give number + issuer; uploads may come later. */
export function draValidationErrors(q) {
    const e = [];
    if (q.status === 'certified') {
        if (!q.certificateNumber || !/^[A-Za-z0-9/\-]{4,40}$/.test(q.certificateNumber.trim()))
            e.push('certificate_number_required');
        if (!q.issuer?.trim())
            e.push('issuer_required');
    }
    return e;
}
//# sourceMappingURL=dra.js.map