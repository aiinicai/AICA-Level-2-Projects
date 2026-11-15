import type { ReferralRejectReason } from '../models/referral.js';

/** reason === null means "no referral code was supplied" (nothing to record). */
export type ReferralDecision = { attribute: true } | { attribute: false; reason: ReferralRejectReason | null };

/**
 * Decides whether a NEW verified registration may be attributed to a referral code.
 * Runs only server-side, inside the registration transaction.
 * phoneHash = HMAC-SHA256(server secret, E.164 phone) so duplicates can be detected without storing raw numbers twice.
 */
export function decideReferral(args: {
  trackingMode: 'on' | 'paused' | 'off';
  code?: string;
  codeDoc?: { ownerUid: string; active: boolean };
  referrerAccountActive: boolean;
  referrerPhoneHash?: string;
  newUid: string;
  newPhoneHash: string;
  phoneVerified: boolean;
  existingAttributionForNewUid: boolean;
  phoneHashSeenBefore: boolean;      // phone previously registered (incl. closed accounts)
  referrerJoinsLast24h: number;
  velocityLimitPer24h: number;
}): ReferralDecision {
  if (!args.code) return { attribute: false, reason: null };                 // no referral at all
  if (args.trackingMode !== 'on') return { attribute: false, reason: 'tracking_disabled' };
  if (!args.phoneVerified) return { attribute: false, reason: 'not_verified' };
  if (args.existingAttributionForNewUid) return { attribute: false, reason: 'already_attributed' };
  if (!args.codeDoc) return { attribute: false, reason: 'unknown_code' };
  if (!args.codeDoc.active) return { attribute: false, reason: 'inactive_code' };
  if (args.codeDoc.ownerUid === args.newUid || args.referrerPhoneHash === args.newPhoneHash) return { attribute: false, reason: 'self_referral' };
  if (!args.referrerAccountActive) return { attribute: false, reason: 'referrer_disabled' };
  if (args.phoneHashSeenBefore) return { attribute: false, reason: 'duplicate_phone' };
  if (args.referrerJoinsLast24h >= args.velocityLimitPer24h) return { attribute: false, reason: 'velocity_limit' };
  return { attribute: true };
}

/**
 * Client-side first-touch storage rule: keep the first referral code seen, never overwrite it with a later link.
 * (Server is still authoritative - see decideReferral.)
 */
export function firstTouchReferral(existing: string | null, incoming: string | null): string | null {
  return existing ?? incoming;
}
