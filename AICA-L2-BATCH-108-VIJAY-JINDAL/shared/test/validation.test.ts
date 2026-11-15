import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  normalizeIndianMobile, maskPhone, isValidPin, isValidPersonName, isValidPan, maskPan, ageOn,
  validateRegistration, STATES_AND_UTS, pinMatchesState, type RegistrationInput,
} from '../src/index.js';

test('covers all 28 states and 8 union territories with unique codes', () => {
  assert.equal(STATES_AND_UTS.filter((s) => s.type === 'state').length, 28);
  assert.equal(STATES_AND_UTS.filter((s) => s.type === 'ut').length, 8);
  assert.equal(new Set(STATES_AND_UTS.map((s) => s.code)).size, 36);
});

test('Indian mobile normalisation', () => {
  assert.equal(normalizeIndianMobile('98765 43210'), '+919876543210');
  assert.equal(normalizeIndianMobile('+91-9876543210'), '+919876543210');
  assert.equal(normalizeIndianMobile('09876543210'), '+919876543210');
  assert.equal(normalizeIndianMobile('5876543210'), null);   // must start 6-9
  assert.equal(normalizeIndianMobile('98765'), null);
  assert.equal(maskPhone('+919876543210'), '+91******3210');
});

test('PIN, names, PAN, age', () => {
  assert.ok(isValidPin('141001'));
  assert.ok(!isValidPin('041001'));
  assert.ok(!isValidPin('14100'));
  assert.ok(isValidPersonName('Gurpreet Singh'));
  assert.ok(isValidPersonName('राजेश कुमार'));
  assert.ok(isValidPersonName('ਗੁਰਪ੍ਰੀਤ ਸਿੰਘ'));
  assert.ok(!isValidPersonName('<script>'));
  assert.ok(!isValidPersonName('A'));
  assert.ok(isValidPan('ABCDE1234F'));
  assert.equal(maskPan('ABCDE1234F'), 'XXXXX1234X');
  assert.equal(ageOn('2008-11-14', '2026-11-13'), 17);
  assert.equal(ageOn('2008-11-13', '2026-11-13'), 18);
});

test('PIN-state mismatch is detected (advisory)', () => {
  assert.ok(pinMatchesState('141001', 'PB'));   // Ludhiana
  assert.ok(pinMatchesState('110001', 'DL'));
  assert.ok(!pinMatchesState('110001', 'PB'));
});

const base: RegistrationInput = {
  fullName: '  Rajesh   Kumar ', stateCode: 'PB', city: 'Ludhiana', pin: '141001',
  draStatus: 'not_certified', preferredRole: 'field_collection', preferredLanguage: 'hi',
  ageAttestation18Plus: true,
  consents: { privacyNotice: true, terms: true, recruitmentContact: true, marketing: false, whatsappUpdates: false },
  noticeVersion: 'privacy-draft-1',
};

test('fresher registration is accepted and cleaned', () => {
  const r = validateRegistration(base);
  assert.ok(r.ok);
  if (r.ok) { assert.equal(r.value.fullName, 'Rajesh Kumar'); assert.equal(r.value.pinMismatch, false); }
});

test('registration rejects missing age attestation and required consents', () => {
  const r = validateRegistration({ ...base, ageAttestation18Plus: false, consents: { ...base.consents, privacyNotice: false } });
  assert.ok(!r.ok);
  if (!r.ok) { assert.equal(r.errors.ageAttestation18Plus, 'age_18_required'); assert.equal(r.errors.privacyNotice, 'privacy_required'); }
});

test('marketing and WhatsApp opt-ins are optional and separate', () => {
  assert.ok(validateRegistration({ ...base, consents: { ...base.consents, marketing: false, whatsappUpdates: false } }).ok);
});

test('registration flags PIN mismatch without blocking', () => {
  const r = validateRegistration({ ...base, pin: '110001' });
  assert.ok(r.ok);
  if (r.ok) assert.equal(r.value.pinMismatch, true);
});

test('malformed referral code is rejected; valid one normalised', () => {
  assert.ok(!validateRegistration({ ...base, referralCode: 'bad!' }).ok);
  const r = validateRegistration({ ...base, referralCode: 'r7km3qx' });
  assert.ok(r.ok);
  if (r.ok) assert.equal(r.value.referralCode, 'R7KM3QX');
});
