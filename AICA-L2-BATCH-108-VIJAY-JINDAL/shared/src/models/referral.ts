import type { EpochMs } from './common.js';

/** referral_codes/{code} -> owner mapping. Readable publicly only as {active} (no uid exposed via rules). */
export interface ReferralCodeDoc { code: string; ownerUid: string; active: boolean; createdAt: EpochMs }

/** referral_stats/{ownerUid} - aggregate counts only, readable by that owner. */
export interface ReferralStats { verifiedJoins: number; rejected: number; lastJoinAt?: EpochMs }

/** referral_attributions/{newUid} - staff only. */
export interface ReferralAttribution {
  newUid: string; referrerUid: string; code: string;
  status: 'attributed' | 'rejected';
  reason?: ReferralRejectReason;
  at: EpochMs;
  campaign?: string;
}

export type ReferralRejectReason =
  | 'tracking_disabled' | 'unknown_code' | 'inactive_code' | 'self_referral'
  | 'already_attributed' | 'duplicate_phone' | 'not_verified' | 'referrer_disabled' | 'velocity_limit';
