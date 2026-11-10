/**
 * Indian date handling. Every date is stored as dd/mm/yyyy.
 *
 * The AI Studio version let the spreadsheet library guess dates in CSV files, and it
 * guesses the US way (04/10/2026 became 10 April). Here CSV cells are read as plain
 * text and slash/dash/dot dates are always read day-first. Only yyyy-mm-dd (ISO) is
 * read year-first.
 */
import * as XLSX from 'xlsx';

const MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
export const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const pad = (n: number) => String(n).padStart(2, '0');

function valid(y: number, m: number, d: number) {
  if (!(y >= 1900 && y <= 2200 && m >= 1 && m <= 12 && d >= 1 && d <= 31)) return false;
  const dt = new Date(y, m - 1, d);
  return dt.getFullYear() === y && dt.getMonth() === m - 1 && dt.getDate() === d;
}

const fmt = (y: number, m: number, d: number) => (valid(y, m, d) ? `${pad(d)}/${pad(m)}/${y}` : '');

const fullYear = (y: number) => (y < 100 ? 2000 + y : y);

/** Converts any cell value from a register into dd/mm/yyyy ('' if it is not a date). */
export function toIndianDate(value: unknown): string {
  if (value === null || value === undefined || value === '') return '';
  if (value instanceof Date) {
    return isNaN(value.getTime()) ? '' : fmt(value.getFullYear(), value.getMonth() + 1, value.getDate());
  }
  if (typeof value === 'number') return fromSerial(value);

  const s = String(value).trim();
  if (!s) return '';

  // Excel serial number stored as text
  if (/^\d{5}(\.\d+)?$/.test(s)) return fromSerial(parseFloat(s));

  // yyyy-mm-dd or yyyy/mm/dd (optionally followed by a time)
  let m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})(?:[ T].*)?$/);
  if (m) return fmt(+m[1], +m[2], +m[3]);

  // dd/mm/yyyy, dd-mm-yy, dd.mm.yyyy (always day first)
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})(?:\s.*)?$/);
  if (m) return fmt(fullYear(+m[3]), +m[2], +m[1]);

  // dd-Mon-yyyy, dd Mon yyyy, dd-Month-yy
  m = s.match(/^(\d{1,2})[-/. ]([A-Za-z]{3,9})[-/., ]+(\d{2}|\d{4})$/);
  if (m) {
    const mi = MONTHS.indexOf(m[2].slice(0, 3).toLowerCase());
    if (mi >= 0) return fmt(fullYear(+m[3]), mi + 1, +m[1]);
  }

  // Mon dd, yyyy
  m = s.match(/^([A-Za-z]{3,9})[ -](\d{1,2}),?[ -](\d{4})$/);
  if (m) {
    const mi = MONTHS.indexOf(m[1].slice(0, 3).toLowerCase());
    if (mi >= 0) return fmt(+m[3], mi + 1, +m[2]);
  }
  return '';
}

function fromSerial(n: number): string {
  // Plausible invoice dates only (1955 to 2119); anything else is an amount, not a date.
  if (!(n > 20000 && n < 80000)) return '';
  const p = XLSX.SSF.parse_date_code(n);
  return p ? fmt(p.y, p.m, p.d) : '';
}

/** Parses a stored dd/mm/yyyy date. */
export function parseIndianDate(s: string): Date | null {
  const m = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(s || '');
  if (!m) return null;
  return new Date(+m[3], +m[2] - 1, +m[1]);
}

/** "Oct-2026" style label plus a sortable key. */
export function monthOf(s: string): { key: string; label: string } | null {
  const m = /^\d{2}\/(\d{2})\/(\d{4})$/.exec(s || '');
  if (!m) return null;
  return { key: `${m[2]}-${m[1]}`, label: `${MONTH_LABELS[+m[1] - 1]}-${m[2]}` };
}

/** Indian financial year that an invoice date falls in, e.g. 2025 for 15/06/2025 and 15/02/2026. */
export function financialYearStart(d: Date) {
  return d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
}

export const todayIndian = () => {
  const d = new Date();
  return fmt(d.getFullYear(), d.getMonth() + 1, d.getDate());
};
