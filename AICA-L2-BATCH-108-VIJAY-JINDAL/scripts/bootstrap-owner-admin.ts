/**
 * ONE-TIME: makes an existing Firebase Auth user (the owner's company email login) the owner admin.
 * Run on YOUR computer, never in the browser. Requires: `gcloud auth application-default login` with a company Google account
 * that is Owner of the Firebase project. No password/OTP is typed into this script.
 *   GOOGLE_CLOUD_PROJECT=vrs-dra-portal-staging npx tsx scripts/bootstrap-owner-admin.ts owner@yourcompany.com
 * The owner must then enrol MFA (second factor) before any admin screen will work (rules require it).
 */
import { initializeApp } from 'firebase-admin/app';
import { getAuth } from 'firebase-admin/auth';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

const email = process.argv[2];
if (!email) { console.error('Usage: bootstrap-owner-admin.ts <company-email>'); process.exit(1); }
initializeApp();
const user = await getAuth().getUserByEmail(email);
await getAuth().setCustomUserClaims(user.uid, { role: 'owner_admin', grants: [], staff_active: true });
await getFirestore().doc(`staff/${user.uid}`).set({ uid: user.uid, displayName: user.displayName ?? 'Owner', email, role: 'owner_admin',
  extraGrants: [], revokedGrants: [], disabled: false, mfaEnrolled: (user.multiFactor?.enrolledFactors.length ?? 0) > 0,
  createdAt: FieldValue.serverTimestamp(), createdBy: 'bootstrap' }, { merge: true });
await getFirestore().collection('audit_logs').add({ at: FieldValue.serverTimestamp(), actorUid: 'bootstrap', actorRole: 'system',
  action: 'staff.role_change', targetType: 'staff', targetId: user.uid, meta: { role: 'owner_admin' } });
console.log(`Owner admin role set for uid ${user.uid}. Sign out and sign in again to refresh the role.`);
