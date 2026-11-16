/**
 * Random identifiers that are NOT derived from personal data.
 * Crockford base32 alphabet (no I, L, O, U) avoids confusion when read aloud over the phone.
 */
export const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
/** Default uses Web Crypto (available in browsers and Node >= 19). Pass a custom source in tests. */
export const defaultRandomBytes = (n) => {
    const b = new Uint8Array(n);
    globalThis.crypto.getRandomValues(b);
    return b;
};
export function randomCode(length, rnd = defaultRandomBytes) {
    // Rejection sampling: 256 is divisible by 32, so modulo is unbiased here.
    const bytes = rnd(length);
    let out = '';
    for (let i = 0; i < length; i++)
        out += CROCKFORD[bytes[i] % 32];
    return out;
}
/** Permanent candidate ID e.g. VRS-C-7K3M9QX2 (32^8 ~ 1.1e12 space). Uniqueness enforced by a Firestore transaction. */
export const newCandidateId = (rnd) => `VRS-C-${randomCode(8, rnd)}`;
/** Referral code e.g. R7KM3QX - short enough to type, stable for life of the account. */
export const newReferralCode = (rnd) => `R${randomCode(6, rnd)}`;
/** Portal training certificate ID e.g. VRS-TC-2026-8F3K-Q7MZ (unguessable 40-bit+ suffix). */
export const newCertificateId = (year, rnd) => {
    const c = randomCode(8, rnd);
    return `VRS-TC-${year}-${c.slice(0, 4)}-${c.slice(4)}`;
};
export const isCandidateId = (s) => /^VRS-C-[0-9A-HJKMNP-TV-Z]{8}$/.test(s);
export const isCertificateId = (s) => /^VRS-TC-\d{4}-[0-9A-HJKMNP-TV-Z]{4}-[0-9A-HJKMNP-TV-Z]{4}$/.test(s);
/** Deterministic application doc ID enforces "one application per candidate per vacancy". */
export const applicationDocId = (vacancyId, uid) => `${vacancyId}_${uid}`;
//# sourceMappingURL=ids.js.map