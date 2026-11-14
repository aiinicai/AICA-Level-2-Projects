import { describe, expect, it } from 'vitest';
import type { Consent } from '../data/types';
import { aiAllowed, clientConsent, dueIn90, NOTICE_VERSION, userConsent } from './consent';
import { CLIENT_TERMS, NOTICE } from '../data/privacyNotice';

const today = '2026-11-02';
const c = (o: Partial<Consent>): Consent => ({ id: Math.random().toString(), scope: 'user', userId: 'u1', clientId: 'c1', noticeVersion: NOTICE_VERSION,
  purposes: { core: true, ai: false }, lang: 'en', method: 'in_app', acceptedBy: 'u1', acceptedAt: '2026-11-01T10:00:00Z', ...o });

describe('DPDP consent rules', () => {
  it('no consent → must agree; current-version consent → ok', () => {
    expect(userConsent([], 'u1', today)).toBeUndefined();
    expect(userConsent([c({})], 'u1', today)).toBeDefined();
  });
  it('a changed notice asks again', () => {
    expect(userConsent([c({ noticeVersion: '2025-old' })], 'u1', today)).toBeUndefined();
  });
  it('withdrawn consent is not valid; the latest decision counts', () => {
    expect(userConsent([c({ withdrawnAt: '2026-11-02T00:00:00Z' })], 'u1', today)).toBeUndefined();
    const older = c({ acceptedAt: '2026-10-01T00:00:00Z', withdrawnAt: '2026-10-05T00:00:00Z' });
    expect(userConsent([older, c({ acceptedAt: '2026-11-01T00:00:00Z' })], 'u1', today)).toBeDefined();
  });
  it('consent lasts until the engagement ends — not beyond', () => {
    expect(userConsent([c({ validUntil: '2027-03-31' })], 'u1', today)).toBeDefined();
    expect(userConsent([c({ validUntil: '2026-10-31' })], 'u1', today)).toBeUndefined();
    expect(clientConsent([c({ scope: 'client', userId: undefined, validUntil: '2026-10-31' })], 'c1', today).state).toBe('expired');
  });
  it('company consent: missing / active / withdrawn are told apart', () => {
    expect(clientConsent([], 'c1', today).state).toBe('missing');
    expect(clientConsent([c({ scope: 'client', userId: undefined })], 'c1', today).state).toBe('active');
    expect(clientConsent([c({ scope: 'client', userId: undefined, withdrawnAt: '2026-11-02T00:00:00Z' })], 'c1', today).state).toBe('withdrawn');
  });
  it('AI only when the user agreed AND the company has not switched it off', () => {
    expect(aiAllowed([c({})], 'u1', 'c1', today).ok).toBe(false);
    expect(aiAllowed([c({ purposes: { core: true, ai: true } })], 'u1', 'c1', today).ok).toBe(true);
    expect(aiAllowed([c({ purposes: { core: true, ai: true } }), c({ scope: 'client', userId: undefined, purposes: { core: true, ai: false } })], 'u1', 'c1', today).ok).toBe(false);
  });
  it('rights requests are due within 90 days', () => {
    expect(dueIn90('2026-11-02T08:00:00Z')).toBe('2027-01-31');
  });
  it('notice has the same sections in English and Hindi, and the minimum contents of Rule 3', () => {
    expect(NOTICE.hi.sections.length).toBe(NOTICE.en.sections.length);
    NOTICE.en.sections.forEach((sec, i) => expect(NOTICE.hi.sections[i].points.length).toBe(sec.points.length));
    const en = JSON.stringify(NOTICE.en);
    for (const must of ['Personal data we process', 'Why we use it', 'withdraw', 'Data Protection Board', 'rights']) expect(en).toContain(must);
    for (const t of [CLIENT_TERMS.en, CLIENT_TERMS.hi]) expect(t).toContain('{client}');
  });
});
