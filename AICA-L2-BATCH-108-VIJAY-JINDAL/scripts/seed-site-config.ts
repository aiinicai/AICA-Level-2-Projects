/**
 * Seeds safe DEFAULT site settings. Registration is CLOSED and referral tracking/AI are OFF until the owner approves.
 * Emulator:  npm run seed:emulator
 * Staging:   GOOGLE_CLOUD_PROJECT=vrs-dra-portal-staging npx tsx scripts/seed-site-config.ts   (after `gcloud auth application-default login`)
 */
import { initializeApp } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';

initializeApp();
const db = getFirestore();
const site = {
  operatorName: 'VRS Corporate Solutions',
  contact: { addressLines: [], phone: null, whatsapp: null, supportEmail: null },
  maintenanceMode: { enabled: false, message: { en: 'We are improving the portal. Please try again soon.' } },
  banners: [], announcements: [],
  features: { referralTracking: 'off', aiResume: false, registrationOpen: false },
  updatedAt: FieldValue.serverTimestamp(),
};
await db.doc('cms_public/site').set(site, { merge: true });
await db.doc('settings_private/ai').set({ enabled: false, provider: 'gemini', model: '', approvedModels: [],
  dailyRequestLimit: 0, perCandidateDailyLimit: 0, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
console.log('Seeded cms_public/site and settings_private/ai with safe defaults (registration closed, AI off).');
