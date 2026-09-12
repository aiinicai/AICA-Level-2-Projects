// Complete permission-matrix test for firestore.rules.
//
// Runs against the local Firestore emulator, so it needs no credentials and never touches the
// live project. Every role is simulated and every collection is asserted, which means the
// whole rule set is checked in one run instead of discovering gaps one login at a time.
//
//   npm test        (from the tests/ folder)

import { readFileSync } from 'node:fs';
import { initializeTestEnvironment, assertSucceeds, assertFails } from '@firebase/rules-unit-testing';
import { doc, getDoc, setDoc, deleteDoc, collection, getDocs } from 'firebase/firestore';

const ADMIN_EMAIL = 'mahesh@primeaccounting.in';

let pass = 0, fail = 0;
const results = [];

async function check(name, expectAllowed, op) {
  try {
    await (expectAllowed ? assertSucceeds(op()) : assertFails(op()));
    pass++; results.push(['PASS', name, expectAllowed ? 'allowed' : 'denied']);
  } catch (e) {
    fail++; results.push(['FAIL', name, expectAllowed ? 'expected allow, got DENY' : 'expected deny, got ALLOW']);
  }
}

const testEnv = await initializeTestEnvironment({
  projectId: 'officeflow-rules-test',
  firestore: { rules: readFileSync('../firestore.rules', 'utf8'), host: '127.0.0.1', port: 8080 }
});
await testEnv.clearFirestore();

// ── identities ───────────────────────────────────────────────────────────
const UID = { admin:'uid-admin', partner:'uid-partner', manager:'uid-manager', member:'uid-member', other:'uid-other' };
const ctx = {
  anon:    testEnv.unauthenticatedContext(),
  admin:   testEnv.authenticatedContext(UID.admin,   { email: ADMIN_EMAIL }),
  partner: testEnv.authenticatedContext(UID.partner, { email: 'shivakumar@primeaccounting.in' }),
  manager: testEnv.authenticatedContext(UID.manager, { email: 'rakshitha@primeaccounting.in' }),
  member:  testEnv.authenticatedContext(UID.member,  { email: 'pavan@primeaccounting.in' }),
  other:   testEnv.authenticatedContext(UID.other,   { email: 'zenith@primeaccounting.in' }),
  nobody:  testEnv.authenticatedContext('uid-nobody',{ email: 'stranger@example.com' })   // signed in, not on the roster
};
const db = Object.fromEntries(Object.entries(ctx).map(([k, c]) => [k, c.firestore()]));

// ── seed the roster and some work, bypassing rules ───────────────────────
const member = (id, name, role, email) => ({ id, name, role: 'Associate', userRole: role, email,
  department: 'Accounts', phone: '', avatarColorHex: '#1E40AF',
  isPrimaryAdmin: role === 'ADMIN', createdDateMillis: Date.now() });

const task = (id, assignedTo, assignedBy) => ({ id, title: 'T-' + id, description: '',
  assignedMemberId: assignedTo, assignedMemberName: 'x', assignedMemberRole: '',
  assignedBy: 'x', assignedByMemberId: assignedBy, projectId: '', projectName: 'General Office',
  priority: 'MEDIUM', status: 'TODO', progressPercentage: 0, dueDateMillis: Date.now(),
  category: 'CLIENT_PROJECT', monthlyRepetitiveCategory: 'NONE', tags: '', checklistItems: '',
  completedChecklistCount: 0, totalChecklistCount: 0, lastProgressRemark: '',
  createdMillis: Date.now(), updatedMillis: Date.now() });

await testEnv.withSecurityRulesDisabled(async (c) => {
  const s = c.firestore();
  await setDoc(doc(s,'teamMembers',UID.admin),   member(UID.admin,'Mahesh','ADMIN',ADMIN_EMAIL));
  await setDoc(doc(s,'teamMembers',UID.partner), member(UID.partner,'Shivakumar','PARTNER','shivakumar@primeaccounting.in'));
  await setDoc(doc(s,'teamMembers',UID.manager), member(UID.manager,'Rakshitha','MANAGER','rakshitha@primeaccounting.in'));
  await setDoc(doc(s,'teamMembers',UID.member),  member(UID.member,'Pavan','TEAM_MEMBER','pavan@primeaccounting.in'));
  await setDoc(doc(s,'teamMembers',UID.other),   member(UID.other,'Zenith','TEAM_MEMBER','zenith@primeaccounting.in'));
  await setDoc(doc(s,'tasks','task-mine'),    task('task-mine',  UID.member,  UID.manager));
  await setDoc(doc(s,'tasks','task-theirs'),  task('task-theirs',UID.other,   UID.admin));
  await setDoc(doc(s,'tasks','task-by-mgr'),  task('task-by-mgr',UID.other,   UID.manager));
  await setDoc(doc(s,'projects','p1'), { id:'p1', name:'P', code:'', clientName:'', description:'',
    leadMemberName:'', startDateMillis:0, targetDateMillis:0, status:'ACTIVE', progressPercentage:0,
    category:'', colorHex:'#1E40AF', lastUpdateRemark:'' });
  await setDoc(doc(s,'taxNotifications','n1'), { id:'n1', title:'N', department:'GST' });
  await setDoc(doc(s,'portalIntegrations','po1'), { id:'po1', name:'GST', portalUrl:'https://x' });
});

// ── unauthenticated ──────────────────────────────────────────────────────
await check('anon: read roster',            false, () => getDoc(doc(db.anon,'teamMembers',UID.admin)));
await check('anon: read tasks',             false, () => getDocs(collection(db.anon,'tasks')));
await check('anon: write a task',           false, () => setDoc(doc(db.anon,'tasks','x'), task('x',UID.member,UID.admin)));

// ── signed in but not on the roster ──────────────────────────────────────
await check('stranger: read roster',        true,  () => getDocs(collection(db.nobody,'teamMembers')));
await check('stranger: read projects',      true,  () => getDocs(collection(db.nobody,'projects')));
await check('stranger: create a task',      false, () => setDoc(doc(db.nobody,'tasks','x'), task('x','uid-nobody','uid-nobody')));
await check('stranger: make self ADMIN',    false, () => setDoc(doc(db.nobody,'teamMembers','uid-nobody'),
                                                       member('uid-nobody','Hacker','ADMIN','stranger@example.com')));

// ── primary admin bootstrap (the first-sign-in path) ─────────────────────
const fresh = testEnv.authenticatedContext('uid-fresh-admin', { email: ADMIN_EMAIL }).firestore();
await check('bootstrap: primary admin creates own profile', true, () =>
  setDoc(doc(fresh,'teamMembers','uid-fresh-admin'), member('uid-fresh-admin','Mahesh','ADMIN',ADMIN_EMAIL)));
const imposter = testEnv.authenticatedContext('uid-imposter', { email: 'nasty@example.com' }).firestore();
await check('bootstrap: someone else cannot use that path', false, () =>
  setDoc(doc(imposter,'teamMembers','uid-imposter'), member('uid-imposter','X','ADMIN',ADMIN_EMAIL)));

// ── team member ──────────────────────────────────────────────────────────
await check('member: read own task',        true,  () => getDoc(doc(db.member,'tasks','task-mine')));
await check('member: read someone else task',false, () => getDoc(doc(db.member,'tasks','task-theirs')));
await check('member: list ALL tasks',       false, () => getDocs(collection(db.member,'tasks')));
await check('member: update own task',      true,  () => setDoc(doc(db.member,'tasks','task-mine'),
                                                       { ...task('task-mine',UID.member,UID.manager), progressPercentage:50 }));
await check('member: update other task',    false, () => setDoc(doc(db.member,'tasks','task-theirs'),
                                                       { ...task('task-theirs',UID.other,UID.admin), progressPercentage:50 }));
await check('member: create a task',        false, () => setDoc(doc(db.member,'tasks','new1'), task('new1',UID.member,UID.member)));
await check('member: delete a task',        false, () => deleteDoc(doc(db.member,'tasks','task-mine')));
await check('member: onboard someone',      false, () => setDoc(doc(db.member,'teamMembers','uid-new'),
                                                       member('uid-new','New','TEAM_MEMBER','new@primeaccounting.in')));
await check('member: promote self',         false, () => setDoc(doc(db.member,'teamMembers',UID.member),
                                                       member(UID.member,'Pavan','ADMIN','pavan@primeaccounting.in')));
await check('member: read circulars',       true,  () => getDocs(collection(db.member,'taxNotifications')));
await check('member: publish a circular',   false, () => setDoc(doc(db.member,'taxNotifications','n2'), { id:'n2', title:'X' }));
await check('member: read portals',         true,  () => getDocs(collection(db.member,'portalIntegrations')));
await check('member: add a portal',         false, () => setDoc(doc(db.member,'portalIntegrations','po2'), { id:'po2', name:'X' }));

// ── manager ──────────────────────────────────────────────────────────────
await check('manager: list all tasks',      true,  () => getDocs(collection(db.manager,'tasks')));
await check('manager: create a task',       true,  () => setDoc(doc(db.manager,'tasks','new2'), task('new2',UID.member,UID.manager)));
await check('manager: update any task',     true,  () => setDoc(doc(db.manager,'tasks','task-theirs'),
                                                       { ...task('task-theirs',UID.other,UID.admin), progressPercentage:10 }));
await check('manager: delete a task',       false, () => deleteDoc(doc(db.manager,'tasks','task-theirs')));
await check('manager: onboard someone',     false, () => setDoc(doc(db.manager,'teamMembers','uid-new2'),
                                                       member('uid-new2','New','TEAM_MEMBER','new2@primeaccounting.in')));
await check('manager: create a project',    true,  () => setDoc(doc(db.manager,'projects','p2'), { id:'p2', name:'P2' }));
await check('manager: publish a circular',  true,  () => setDoc(doc(db.manager,'taxNotifications','n3'), { id:'n3', title:'X' }));
await check('manager: add a portal',        false, () => setDoc(doc(db.manager,'portalIntegrations','po3'), { id:'po3', name:'X' }));

// ── partner (must behave exactly like admin) ─────────────────────────────
await check('partner: list all tasks',      true,  () => getDocs(collection(db.partner,'tasks')));
await check('partner: onboard someone',     true,  () => setDoc(doc(db.partner,'teamMembers','uid-new3'),
                                                       member('uid-new3','New','TEAM_MEMBER','new3@primeaccounting.in')));
await check('partner: delete a task',       true,  () => deleteDoc(doc(db.partner,'tasks','task-by-mgr')));
await check('partner: add a portal',        true,  () => setDoc(doc(db.partner,'portalIntegrations','po4'), { id:'po4', name:'X' }));

// ── admin ────────────────────────────────────────────────────────────────
await check('admin: list all tasks',        true,  () => getDocs(collection(db.admin,'tasks')));
await check('admin: onboard someone',       true,  () => setDoc(doc(db.admin,'teamMembers','uid-new4'),
                                                       member('uid-new4','New','TEAM_MEMBER','new4@primeaccounting.in')));
await check('admin: remove a member',       true,  () => deleteDoc(doc(db.admin,'teamMembers','uid-new4')));
await check('admin: add a portal',          true,  () => setDoc(doc(db.admin,'portalIntegrations','po5'), { id:'po5', name:'X' }));

// ── self-service profile edits ───────────────────────────────────────────
await check('member: edit own phone number', true, () => setDoc(doc(db.member,'teamMembers',UID.member),
                                                      { ...member(UID.member,'Pavan','TEAM_MEMBER','pavan@primeaccounting.in'), phone:'+91 90000 00000' }));

// ── anything outside the known collections ───────────────────────────────
await check('admin: write to an unknown collection', false, () => setDoc(doc(db.admin,'secrets','s1'), { a:1 }));

await testEnv.cleanup();

const width = Math.max(...results.map(r => r[1].length));
for (const [state, name, note] of results) {
  console.log(`  ${state}  ${name.padEnd(width)}  ${note}`);
}
console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail > 0 ? 1 : 0);
