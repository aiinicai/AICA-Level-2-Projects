import { defineSecret, defineString } from 'firebase-functions/params';

/** All functions run in Mumbai to keep data in India by default. */
export const REGION = 'asia-south1';

/**
 * Secrets live ONLY in Google Cloud Secret Manager (set with: firebase functions:secrets:set NAME).
 * They are never placed in client code, Firestore, browser storage or logs.
 */
export const PHONE_HASH_KEY = defineSecret('PHONE_HASH_KEY');     // HMAC key for duplicate-phone detection
export const GEMINI_API_KEY = defineSecret('GEMINI_API_KEY');     // Phase 4 (optional AI)
export const SMTP_PASSWORD = defineSecret('SMTP_PASSWORD');       // Phase 7 (contact form email)

/** Non-secret per-environment parameters (.env.staging / .env.production in functions/). */
export const PRIVACY_NOTICE_VERSION = defineString('PRIVACY_NOTICE_VERSION', { default: 'privacy-draft-1' });
export const REFERRAL_VELOCITY_PER_24H = defineString('REFERRAL_VELOCITY_PER_24H', { default: '25' });
