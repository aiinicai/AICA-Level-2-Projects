// WhatsApp number check by one-time code (same code in the app and the whatsapp-webhook function).
import { describe, expect, it } from 'vitest';
import { checkCode, hashCode, makeCode, MAX_TRIES, parseVerifyText, verifyLink } from './waVerify';

describe('one-time code', () => {
  it('is 6 digits', () => { for (let i = 0; i < 50; i++) expect(makeCode()).toMatch(/^\d{6}$/); });
  it('hash matches Postgres encode(sha256(convert_to(code, UTF8)), hex) for the same input', async () =>
    expect(await hashCode('123456')).toBe('8d969eef6ecad3c29a3a629280e686cf0c3f5d5a86aff3ca12020c923adc6c92'));
  it('reads the message people actually type', () => {
    expect(parseVerifyText('VERIFY 123456')).toBe('123456');
    expect(parseVerifyText('verify123456')).toBe('123456');
    expect(parseVerifyText(' Verify: 123 456 ')).toBe('123456');
    expect(parseVerifyText('hello 123456')).toBeUndefined();
    expect(parseVerifyText('VERIFY 12345')).toBeUndefined();
  });
  it('link opens WhatsApp to the firm number with the message ready', () =>
    expect(verifyLink('+91 98765 43210', '042913')).toBe('https://wa.me/919876543210?text=VERIFY%20042913'));
});

describe('checking a code', () => {
  const later = new Date(Date.now() + 10 * 60_000).toISOString();
  it('right code within time → verified', async () => expect(await checkCode('111222', { hash: await hashCode('111222'), expires: later, tries: 0 })).toBe('verified'));
  it('wrong code → wrong', async () => expect(await checkCode('999999', { hash: await hashCode('111222'), expires: later, tries: 0 })).toBe('wrong'));
  it('expired → expired, even if right', async () => expect(await checkCode('111222', { hash: await hashCode('111222'), expires: new Date(Date.now() - 1000).toISOString(), tries: 0 })).toBe('expired'));
  it('too many tries → blocked, even if right', async () => expect(await checkCode('111222', { hash: await hashCode('111222'), expires: later, tries: MAX_TRIES })).toBe('too_many'));
  it('no code asked for → no_code', async () => expect(await checkCode('111222', {})).toBe('no_code'));
});
