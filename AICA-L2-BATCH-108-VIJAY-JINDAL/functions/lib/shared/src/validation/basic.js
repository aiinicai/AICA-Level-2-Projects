/** Normalises Indian mobile input (+91, 91, 0 prefixes, spaces, dashes) to E.164 (+91XXXXXXXXXX) or null. */
export function normalizeIndianMobile(input) {
    const digits = (input ?? '').replace(/[\s\-()]/g, '');
    const m = /^(?:\+91|91|0)?([6-9]\d{9})$/.exec(digits);
    return m ? `+91${m[1]}` : null;
}
/** Masks a phone for logs/UI: +91XXXXXX3210 -> "+91******3210". Never log full numbers. */
export function maskPhone(e164) {
    return e164.length >= 4 ? `${e164.slice(0, 3)}******${e164.slice(-4)}` : '****';
}
export const isValidPin = (pin) => /^[1-9]\d{5}$/.test(pin ?? '');
/** Names: letters in Latin, Devanagari, Gurmukhi; spaces, dot, apostrophe, hyphen; 2-80 chars. */
const NAME_RE = /^[\p{Script=Latin}\p{Script=Devanagari}\p{Script=Gurmukhi}][\p{Script=Latin}\p{Script=Devanagari}\p{Script=Gurmukhi}\p{M} .'-]{1,79}$/u;
export const isValidPersonName = (name) => NAME_RE.test((name ?? '').trim());
export const cleanText = (s, max = 200) => (s ?? '').replace(/[\u0000-\u001F\u007F<>]/g, '').replace(/\s+/g, ' ').trim().slice(0, max);
/** PAN format AAAAA9999A. Only validated when PAN collection is justified. */
export const isValidPan = (pan) => /^[A-Z]{5}\d{4}[A-Z]$/.test(pan ?? '');
export const maskPan = (pan) => (isValidPan(pan) ? `XXXXX${pan.slice(5, 9)}X` : '');
export const isValidEmail = (e) => /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,}$/.test(e ?? '');
/** Age in whole years at a given date (YYYY-MM-DD). */
export function ageOn(dobIso, onIso) {
    const d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(dobIso);
    const o = /^(\d{4})-(\d{2})-(\d{2})$/.exec(onIso);
    if (!d || !o)
        return null;
    let age = +o[1] - +d[1];
    if (+o[2] < +d[2] || (+o[2] === +d[2] && +o[3] < +d[3]))
        age--;
    return age;
}
//# sourceMappingURL=basic.js.map