import { VALIDATION_LIMITS, type HalfDayOption } from '../types/leave';

export function sanitizeEmailId(email: string): string {
  const clean = email.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '_');
  return clean.slice(0, VALIDATION_LIMITS.maxIdLength);
}

export function normalizeEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function getCurrentYear(): number {
  return new Date().getFullYear();
}

export function getTodayIsoDate(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

export function parseIsoDateLocal(iso: string): Date | null {
  if (!VALIDATION_LIMITS.datePattern.test(iso)) return null;
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  if (dt.getFullYear() !== y || dt.getMonth() !== m - 1 || dt.getDate() !== d) {
    return null;
  }
  return dt;
}

export interface WorkingDayBreakdown {
  workingDays: number;
  calendarDays: number;
  weekendDays: number;
  holidayDays: number;
  isValidRange: boolean;
}

export function calculateWorkingDays(
  startDate: string,
  endDate: string,
  halfDay: HalfDayOption,
  holidayDates: Set<string>
): WorkingDayBreakdown {
  const start = parseIsoDateLocal(startDate);
  const end = parseIsoDateLocal(endDate);
  if (!start || !end || end < start) {
    return {
      workingDays: 0,
      calendarDays: 0,
      weekendDays: 0,
      holidayDays: 0,
      isValidRange: false,
    };
  }

  let calendarDays = 0;
  let weekendDays = 0;
  let holidayDays = 0;
  let workingDays = 0;

  const cursor = new Date(start.getTime());
  while (cursor <= end) {
    calendarDays += 1;
    const dayOfWeek = cursor.getDay();
    const y = cursor.getFullYear();
    const m = String(cursor.getMonth() + 1).padStart(2, '0');
    const d = String(cursor.getDate()).padStart(2, '0');
    const iso = `${y}-${m}-${d}`;

    if (dayOfWeek === 0 || dayOfWeek === 6) {
      weekendDays += 1;
    } else if (holidayDates.has(iso)) {
      holidayDays += 1;
    } else {
      workingDays += 1;
    }
    cursor.setDate(cursor.getDate() + 1);
  }

  if (startDate === endDate && halfDay !== 'none' && workingDays === 1) {
    workingDays = 0.5;
  }

  return {
    workingDays,
    calendarDays,
    weekendDays,
    holidayDays,
    isValidRange: true,
  };
}

export function formatShortDate(iso: string): string {
  const dt = parseIsoDateLocal(iso);
  if (!dt) return iso;
  return dt.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateRangeLabel(startDate: string, endDate: string, halfDay: HalfDayOption): string {
  if (startDate === endDate) {
    const suffix =
      halfDay === 'first_half'
        ? ' (First Half)'
        : halfDay === 'second_half'
          ? ' (Second Half)'
          : '';
    return `${formatShortDate(startDate)}${suffix}`;
  }
  return `${formatShortDate(startDate)} – ${formatShortDate(endDate)}`;
}

export function datesOverlap(aStart: string, aEnd: string, bStart: string, bEnd: string): boolean {
  return aStart <= bEnd && bStart <= aEnd;
}

export function roundDays(value: number): number {
  return Math.round(value * 100) / 100;
}
