/** Date & reporting-period helpers. All dates are ISO 'YYYY-MM-DD' strings in local business time (no TZ maths). */

export interface DateRange { from: string; to: string }

export const pad2 = (n: number) => String(n).padStart(2, '0');

export function toIso(y: number, m: number, d: number) {
  return `${y}-${pad2(m)}-${pad2(d)}`;
}

export function parseIso(s: string): { y: number; m: number; d: number } {
  const [y, m, d] = s.split('-').map(Number);
  return { y, m, d };
}

export function isValidIso(s: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const { y, m, d } = parseIso(s);
  return m >= 1 && m <= 12 && d >= 1 && d <= daysInMonth(y, m);
}

export function daysInMonth(y: number, m: number) {
  return new Date(Date.UTC(y, m, 0)).getUTCDate();
}

export function addDays(iso: string, n: number): string {
  const { y, m, d } = parseIso(iso);
  const t = new Date(Date.UTC(y, m - 1, d + n));
  return toIso(t.getUTCFullYear(), t.getUTCMonth() + 1, t.getUTCDate());
}

export function addMonths(iso: string, n: number): string {
  const { y, m, d } = parseIso(iso);
  const idx = y * 12 + (m - 1) + n;
  const ny = Math.floor(idx / 12);
  const nm = (idx % 12) + 1;
  return toIso(ny, nm, Math.min(d, daysInMonth(ny, nm)));
}

export function daysBetween(a: string, b: string): number {
  const pa = parseIso(a);
  const pb = parseIso(b);
  return Math.round((Date.UTC(pb.y, pb.m - 1, pb.d) - Date.UTC(pa.y, pa.m - 1, pa.d)) / 86400000);
}

/** Inclusive number of days in a range. */
export function rangeDays(r: DateRange) {
  return daysBetween(r.from, r.to) + 1;
}

export function monthStart(iso: string) {
  const { y, m } = parseIso(iso);
  return toIso(y, m, 1);
}

export function monthEnd(iso: string) {
  const { y, m } = parseIso(iso);
  return toIso(y, m, daysInMonth(y, m));
}

/** Financial year containing `iso`, for a FY starting in `startMonth` (India: 4 = April). */
export function fyOf(iso: string, startMonth = 4): DateRange & { label: string; startYear: number } {
  const { y, m } = parseIso(iso);
  const startYear = m >= startMonth ? y : y - 1;
  const from = toIso(startYear, startMonth, 1);
  const to = addDays(addMonths(from, 12), -1);
  const label = startMonth === 1 ? `${startYear}` : `FY ${startYear}-${String((startYear + 1) % 100).padStart(2, '0')}`;
  return { from, to, label, startYear };
}

/** Months (first-day ISO) intersecting the range. */
export function monthsIn(r: DateRange): string[] {
  const out: string[] = [];
  let cur = monthStart(r.from);
  while (cur <= r.to) {
    out.push(cur);
    cur = addMonths(cur, 1);
  }
  return out;
}

export function monthLabel(iso: string) {
  const { y, m } = parseIso(iso);
  return `${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1]} ${String(y).slice(2)}`;
}

/** Quarter of the FY (1..4) for a date. */
export function fyQuarter(iso: string, startMonth = 4) {
  const { m } = parseIso(iso);
  return Math.floor(((m - startMonth + 12) % 12) / 3) + 1;
}

/** The immediately preceding range of equal length (month→month, quarter→quarter, else same day count). */
export function previousPeriod(r: DateRange): DateRange {
  const isWholeMonths = r.from === monthStart(r.from) && r.to === monthEnd(r.to);
  if (isWholeMonths) {
    const months = monthsIn(r).length;
    const from = addMonths(r.from, -months);
    return { from, to: monthEnd(addMonths(r.from, -1)) };
  }
  const len = rangeDays(r);
  return { from: addDays(r.from, -len), to: addDays(r.from, -1) };
}

/** Same range one year earlier (handles month-end alignment, e.g. Feb 29). */
export function previousYear(r: DateRange): DateRange {
  const isWholeMonths = r.from === monthStart(r.from) && r.to === monthEnd(r.to);
  return {
    from: addMonths(r.from, -12),
    to: isWholeMonths ? monthEnd(addMonths(r.to, -12)) : addMonths(r.to, -12),
  };
}

export type ComparisonMode = 'previous_period' | 'previous_year' | 'none';

export function comparisonRange(r: DateRange, mode: ComparisonMode): DateRange | null {
  if (mode === 'none') return null;
  return mode === 'previous_year' ? previousYear(r) : previousPeriod(r);
}
