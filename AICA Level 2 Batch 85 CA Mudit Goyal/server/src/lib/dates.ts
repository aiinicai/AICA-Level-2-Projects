/**
 * Date helpers.
 *
 * Attendance is stamped in Indian Standard Time regardless of where the server
 * runs: a punch at 00:30 IST belongs to that calendar day in India, not to the
 * previous UTC one. Day columns are `@db.Date`, so the day itself is stored as
 * midnight UTC of the IST calendar date.
 */

const IST_OFFSET_MINUTES = 5 * 60 + 30;

/** Today's date in IST, as `YYYY-MM-DD`. */
export function getISTDateString(at: Date = new Date()): string {
  const shifted = new Date(at.getTime() + IST_OFFSET_MINUTES * 60_000);
  return shifted.toISOString().slice(0, 10);
}

/** Today in IST, as the midnight-UTC Date that `@db.Date` columns store. */
export function getISTTodayUTC(at: Date = new Date()): Date {
  const [y, m, d] = getISTDateString(at).split('-').map(Number);
  return new Date(Date.UTC(y, m - 1, d));
}

/** Parse a `YYYY-MM-DD` string into the midnight-UTC Date a `@db.Date` holds. */
export function parseDateOnly(value: unknown): Date | null {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const d = new Date(`${value}T00:00:00.000Z`);
  return Number.isNaN(d.getTime()) ? null : d;
}

/** `YYYY-MM-DD` for a date-only column. */
export function toDateOnlyString(d: Date | string | null | undefined): string | null {
  if (!d) return null;
  const dt = d instanceof Date ? d : new Date(d);
  return Number.isNaN(dt.getTime()) ? null : dt.toISOString().slice(0, 10);
}

/**
 * The Indian financial year a date falls in, as `26-27`. April starts the year,
 * so 31-Mar-26 is 25-26 and 01-Apr-26 is 26-27.
 */
export function financialYear(d: Date): string {
  const year = d.getUTCFullYear();
  const startYear = d.getUTCMonth() >= 3 ? year : year - 1;
  return `${String(startYear).slice(-2)}-${String(startYear + 1).slice(-2)}`;
}

/** First and last day (midnight UTC) of the given month, 1-indexed. */
export function monthRange(year: number, month: number): { start: Date; end: Date } {
  return {
    start: new Date(Date.UTC(year, month - 1, 1)),
    end: new Date(Date.UTC(year, month, 0)),
  };
}
