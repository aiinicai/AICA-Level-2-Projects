/**
 * Firestore security-rules tests. Run with:  npm run test:rules   (needs Java + Firebase emulator; runs in CI)
 * Covers: forged profile/certificate access, server-only collections, staff MFA, disabled staff,
 * unauthorized exports, append-only consents, server-owned fields, closed-collection enumeration.
 */
import { before, after, beforeEach, test } from 'node:test';
import { readFileSync } from 'node:fs';
import { initializeTestEnvironment, assertFails, assertSucceeds, type RulesTestEnvironment } from '@firebase/rules-unit-testing';
import { doc, getDoc, setDoc, updateDoc, getDocs, collection, serverTimestamp, deleteDoc } from 'firebase/firestore';

let env: RulesTestEnvironment;
const PHONE = { phone_number: '+919876543210' };
const staffToken = (role: string, grants: string[] = [], mfa = true, active = true) => ({
  role, grants, staff_active: active, firebase: { sign_in_provider: 'password', ...(mfa ? { sign_in_second_factor: 'totp' } : {}) },
});

before(async () => {
  env = await initializeTestEnvironment({
    projectId: 'demo-vrs-rules',
    firestore: { rules: readFileSync('firestore.rules', 'utf8'), host: '127.0.0.1', port: 8080 },
  });
});
after(async () => { await env.cleanup(); });
beforeEach(async () => {
  await env.clearFirestore();
  await env.withSecurityRulesDisabled(async (ctx) => {
    const db = ctx.firestore();
    const core = { uid: 'alice', candidateId: 'VRS-C-AAAAAAAA', referralCode: 'RAAAAAA', fullName: 'Alice Kaur', accountStatus: 'active',
      mobileE164: '+919876543210', location: { stateCode: 'PB', city: 'Ludhiana', pin: '141001' } };
    await setDoc(doc(db, 'candidates/alice'), core);
    await setDoc(doc(db, 'candidates/bob'), { ...core, uid: 'bob', candidateId: 'VRS-C-BBBBBBBB', fullName: 'Bob Singh' });
    await setDoc(doc(db, 'candidates/bob/restricted/identity'), { dateOfBirth: '1990-01-01' });
    await setDoc(doc(db, 'certificates/VRS-TC-2026-AAAA-BBBB'), { uid: 'bob', certificateId: 'VRS-TC-2026-AAAA-BBBB' });
    await setDoc(doc(db, 'certificate_verification/VRS-TC-2026-AAAA-BBBB'), { valid: true });
    await setDoc(doc(db, 'question_bank/q1'), { correctChoiceIndexes: [0] });
    await setDoc(doc(db, 'vacancies/VAC-1'), { status: 'closed' });
    await setDoc(doc(db, 'vacancies/VAC-2'), { status: 'published' });
    await setDoc(doc(db, 'applications/app_bob'), { uid: 'bob', vacancyId: 'VAC-2' });
    await setDoc(doc(db, 'data_requests/dr_alice'), { uid: 'alice', type: 'correction' });
    await setDoc(doc(db, 'data_requests/dr_bob'), { uid: 'bob', type: 'closure' });
  });
});

const alice = () => env.authenticatedContext('alice', PHONE).firestore();

test('candidate reads own profile but not another candidate (forged ID)', async () => {
  await assertSucceeds(getDoc(doc(alice(), 'candidates/alice')));
  await assertFails(getDoc(doc(alice(), 'candidates/bob')));
  await assertFails(getDoc(doc(alice(), 'candidates/bob/restricted/identity')));
});

test('anonymous users cannot read any profile', async () => {
  await assertFails(getDoc(doc(env.unauthenticatedContext().firestore(), 'candidates/alice')));
});

test("forged certificate URL: cannot read another user's private certificate", async () => {
  await assertFails(getDoc(doc(alice(), 'certificates/VRS-TC-2026-AAAA-BBBB')));
});

test('public verification allows single get but not listing/enumeration', async () => {
  const anon = env.unauthenticatedContext().firestore();
  await assertSucceeds(getDoc(doc(anon, 'certificate_verification/VRS-TC-2026-AAAA-BBBB')));
  await assertFails(getDocs(collection(anon, 'certificate_verification')));
});

test('candidate cannot create certificates, attempts or applications directly (score tampering)', async () => {
  await assertFails(setDoc(doc(alice(), 'certificates/VRS-TC-2026-ZZZZ-ZZZZ'), { uid: 'alice' }));
  await assertFails(setDoc(doc(alice(), 'attempts/a1'), { uid: 'alice', scorePercent: 100, passed: true }));
  await assertFails(setDoc(doc(alice(), 'applications/VAC-2_alice'), { uid: 'alice', vacancyId: 'VAC-2' }));
});

test('candidates cannot read the question bank (answer keys)', async () => {
  await assertFails(getDoc(doc(alice(), 'question_bank/q1')));
});

test('closed vacancy hidden from public; published visible', async () => {
  const anon = env.unauthenticatedContext().firestore();
  await assertFails(getDoc(doc(anon, 'vacancies/VAC-1')));
  await assertSucceeds(getDoc(doc(anon, 'vacancies/VAC-2')));
});

test('candidate cannot change server-owned fields (candidateId, accountStatus, phone)', async () => {
  await assertFails(updateDoc(doc(alice(), 'candidates/alice'), { candidateId: 'VRS-C-HACKED00' }));
  await assertFails(updateDoc(doc(alice(), 'candidates/alice'), { accountStatus: 'active', mobileE164: '+919999999999' }));
  await assertSucceeds(updateDoc(doc(alice(), 'candidates/alice'), { fullName: 'Alice K', updatedAt: serverTimestamp() }));
});

test('candidate cannot write DRA review status directly', async () => {
  await assertFails(setDoc(doc(alice(), 'candidates/alice/dra/current'), { documentReview: { status: 'approved' } }));
});

test('consents are append-only', async () => {
  const ref = doc(alice(), 'candidates/alice/consents/c1');
  await assertSucceeds(setDoc(ref, { purpose: 'marketing', granted: false, noticeVersion: 'v1', at: serverTimestamp(), channel: 'web' }));
  await assertFails(updateDoc(ref, { granted: true }));
  await assertFails(deleteDoc(ref));
});

test('staff without MFA, disabled staff, and fake role claims are denied', async () => {
  const noMfa = env.authenticatedContext('r1', staffToken('recruiter', [], false)).firestore();
  const disabled = env.authenticatedContext('r2', staffToken('recruiter', [], true, false)).firestore();
  const fake = env.authenticatedContext('r3', { role: 'superuser', staff_active: true }).firestore();
  for (const db of [noMfa, disabled, fake]) await assertFails(getDoc(doc(db, 'candidates/alice')));
});

test('recruiter with profile.basic can read core profile but not restricted identity', async () => {
  const rec = env.authenticatedContext('r1', staffToken('recruiter', ['profile.basic', 'notes.recruitment'])).firestore();
  await assertSucceeds(getDoc(doc(rec, 'candidates/bob')));
  await assertFails(getDoc(doc(rec, 'candidates/bob/restricted/identity')));
});

test('unauthorized roles cannot read exports, audit logs or private settings', async () => {
  const viewer = env.authenticatedContext('v1', staffToken('viewer', ['profile.basic'])).firestore();
  await assertFails(getDocs(collection(viewer, 'exports')));
  await assertFails(getDocs(collection(viewer, 'audit_logs')));
  await assertFails(getDoc(doc(viewer, 'settings_private/ai')));
  const owner = env.authenticatedContext('o1', staffToken('owner_admin')).firestore();
  await assertSucceeds(getDocs(collection(owner, 'audit_logs')));
});

test('nobody can write audit logs from the client', async () => {
  const owner = env.authenticatedContext('o1', staffToken('owner_admin')).firestore();
  await assertFails(setDoc(doc(owner, 'audit_logs/x'), { action: 'fake' }));
});

test('contact messages cannot be directly written by browser client', async () => {
  await assertFails(setDoc(doc(alice(), 'contact_messages/msg_fake'), { name: 'Alice', message: 'Spam' }));
  const anon = env.unauthenticatedContext().firestore();
  await assertFails(setDoc(doc(anon, 'contact_messages/msg_fake2'), { name: 'Anon', message: 'Spam' }));
});

test('candidate can get own data request but cannot read others or write directly', async () => {
  await assertSucceeds(getDoc(doc(alice(), 'data_requests/dr_alice')));
  await assertFails(getDoc(doc(alice(), 'data_requests/dr_bob')));
  await assertFails(setDoc(doc(alice(), 'data_requests/dr_forged'), { uid: 'alice', status: 'completed' }));
});

test('candidate cannot read another candidate application', async () => {
  await assertFails(getDoc(doc(alice(), 'applications/app_bob')));
});

