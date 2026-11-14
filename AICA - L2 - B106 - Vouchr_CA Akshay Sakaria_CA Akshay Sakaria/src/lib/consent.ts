// DPDP Act 2023 consent records. Design choices that follow the law (see PRIVACY-DPDP.md):
//   • consent needs a clear affirmative action (s.6(1)) → nothing is pre-ticked; the user ticks and taps "I agree"
//   • consent is the INDIVIDUAL's (Data Principal) → staff consent covers their own data; the client company's acceptance is
//     a separate, contractual record (client admin, or the CA firm recording the signed engagement letter)
//   • valid until the engagement ends, but can be withdrawn at any time, as easily as given (s.6(4)) → withdrawal ends use
//     of the app; records the law requires (e.g. GST books) are still retained (s.6(6), s.8(7))
//   • a changed notice (new NOTICE_VERSION) asks again
import type { Consent } from '../data/types';

export const NOTICE_VERSION = '2026-11-v2'; // v2: WhatsApp bill sending added

const live = (c: Consent, today: string) => !c.withdrawnAt && (!c.validUntil || c.validUntil >= today);
const latest = (xs: Consent[]) => [...xs].sort((a, b) => b.acceptedAt.localeCompare(a.acceptedAt))[0];

/** The user's own consent for the current notice version, if still valid. */
export function userConsent(consents: Consent[], userId: string, today: string): Consent | undefined {
  const c = latest(consents.filter((x) => x.scope === 'user' && x.userId === userId));
  return c && c.noticeVersion === NOTICE_VERSION && live(c, today) ? c : undefined;
}

export type ClientConsentState = { state: 'active'; consent: Consent } | { state: 'missing' } | { state: 'withdrawn' | 'expired'; consent: Consent };
/** The client company's acceptance of the data-processing terms. */
export function clientConsent(consents: Consent[], clientId: string, today: string): ClientConsentState {
  const c = latest(consents.filter((x) => x.scope === 'client' && x.clientId === clientId));
  if (!c) return { state: 'missing' };
  if (c.withdrawnAt) return { state: 'withdrawn', consent: c };
  if (c.validUntil && c.validUntil < today) return { state: 'expired', consent: c };
  return { state: 'active', consent: c };
}

/** AI may run only if the user agreed to AI AND the client company has not switched AI off. */
export function aiAllowed(consents: Consent[], userId: string, clientId: string | undefined, today: string): { ok: boolean; reason?: string } {
  const u = userConsent(consents, userId, today);
  if (!u?.purposes.ai) return { ok: false, reason: 'You have not agreed to AI assistance. You can turn it on in Privacy & consent.' };
  if (clientId) {
    const c = clientConsent(consents, clientId, today);
    if (c.state === 'active' && !c.consent.purposes.ai) return { ok: false, reason: 'Your company has switched AI assistance off.' };
  }
  return { ok: true };
}

/** Rights requests must be answered within 90 days (DPDP Rules 2025). */
export const dueIn90 = (fromIso: string) => {
  const d = new Date(`${fromIso.slice(0, 10)}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 90);
  return d.toISOString().slice(0, 10);
};
