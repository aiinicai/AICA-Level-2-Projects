/** Timestamps are stored as Firestore Timestamps; in shared logic we use epoch milliseconds. */
export type EpochMs = number;

export type LanguageCode = 'en' | 'hi' | 'pa';
export const SUPPORTED_LANGUAGES: readonly LanguageCode[] = ['en', 'hi', 'pa'];

/** Text that can carry translations. English is mandatory; others fall back to English. */
export interface LocalizedText { en: string; hi?: string; pa?: string }

export interface AuditStamp { createdAt: EpochMs; updatedAt: EpochMs; createdBy?: string; updatedBy?: string }

/** Reference-data entries entered as "Other" are held for staff review before becoming selectable. */
export type ReviewedEntryStatus = 'approved' | 'pending_review' | 'rejected';
