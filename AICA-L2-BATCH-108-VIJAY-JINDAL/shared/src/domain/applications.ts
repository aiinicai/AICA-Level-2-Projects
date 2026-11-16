import type { Vacancy } from '../models/recruitment.js';
import type { DraQualification } from '../models/dra.js';

export type ApplyDecision =
  | { ok: true; certificationEligibility: 'meets' | 'not_established' | 'not_required' }
  | { ok: false; reason: 'vacancy_not_open' | 'vacancy_closed_by_date' | 'already_applied' | 'account_inactive' | 'profile_incomplete' };

/** Returns today's date in India (IST, UTC+5:30) as YYYY-MM-DD. */
export function istDate(nowMs: number): string {
  return new Date(nowMs + 330 * 60_000).toISOString().slice(0, 10);
}

/**
 * Server-side apply rules. Mandatory-certification vacancies still ACCEPT the application
 * (pending owner decision D5) but mark it 'not_established' so recruiters see it clearly.
 */
export function decideApplication(args: {
  vacancy: Pick<Vacancy, 'status' | 'closingDate' | 'certificationPolicy'>;
  dra?: Pick<DraQualification, 'status' | 'documentReview'>;
  accountStatus: string;
  hasBasicProfile: boolean;
  alreadyApplied: boolean;
  nowMs: number;
}): ApplyDecision {
  if (args.accountStatus !== 'active') return { ok: false, reason: 'account_inactive' };
  if (args.vacancy.status !== 'published') return { ok: false, reason: 'vacancy_not_open' };
  if (istDate(args.nowMs) > args.vacancy.closingDate) return { ok: false, reason: 'vacancy_closed_by_date' };
  if (args.alreadyApplied) return { ok: false, reason: 'already_applied' };
  if (!args.hasBasicProfile) return { ok: false, reason: 'profile_incomplete' };
  if (args.vacancy.certificationPolicy === 'not_required') return { ok: true, certificationEligibility: 'not_required' };
  const meets = args.dra?.status === 'certified' && args.dra.documentReview.status === 'approved';
  return { ok: true, certificationEligibility: meets ? 'meets' : 'not_established' };
}
