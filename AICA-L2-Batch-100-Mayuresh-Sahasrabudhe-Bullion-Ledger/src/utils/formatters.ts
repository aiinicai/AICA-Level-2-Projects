/**
 * Formatting utilities for Indian financial context (INR, lakhs/crores, DD-MMM-YYYY dates).
 */

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

/**
 * Format a number into Indian Rupee notation (e.g. ₹1,40,054.00)
 */
export function formatINR(value: number | null | undefined, options: { decimals?: number; showSymbol?: boolean } = {}): string {
  if (value === null || value === undefined || isNaN(value)) {
    return '₹0.00';
  }
  
  const decimals = options.decimals ?? 2;
  const showSymbol = options.showSymbol ?? true;
  const prefix = showSymbol ? '₹' : '';
  const isNegative = value < 0;
  const absVal = Math.abs(value);

  const fixed = absVal.toFixed(decimals);
  const [intPart, decPart] = fixed.split('.');

  // Indian number grouping: last 3 digits, then groups of 2
  let result = '';
  if (intPart.length > 3) {
    const lastThree = intPart.slice(-3);
    const remaining = intPart.slice(0, -3);
    const groups: string[] = [];
    for (let i = remaining.length; i > 0; i -= 2) {
      groups.unshift(remaining.substring(Math.max(0, i - 2), i));
    }
    result = groups.join(',') + ',' + lastThree;
  } else {
    result = intPart;
  }

  if (decimals > 0 && decPart !== undefined) {
    result += '.' + decPart;
  }

  return (isNegative ? '-' : '') + prefix + result;
}

/**
 * Format weight in grams with custom decimal places (e.g. 10.000 g)
 */
export function formatGrams(grams: number | null | undefined, decimals = 3): string {
  if (grams === null || grams === undefined || isNaN(grams)) {
    return `0.${'0'.repeat(decimals)} g`;
  }
  const formatted = formatINR(grams, { decimals, showSymbol: false });
  return `${formatted} g`;
}

/**
 * Format ISO date string (YYYY-MM-DD) to DD-MMM-YYYY (e.g. 30-Oct-2026)
 */
export function formatDisplayDate(isoDate: string | null | undefined): string {
  if (!isoDate || typeof isoDate !== 'string') return '—';
  
  const parts = isoDate.split('-');
  if (parts.length !== 3) return isoDate;
  
  const year = parts[0];
  const monthIdx = parseInt(parts[1], 10) - 1;
  const day = parts[2].padStart(2, '0');
  
  if (monthIdx < 0 || monthIdx > 11) return isoDate;
  return `${day}-${MONTH_NAMES[monthIdx]}-${year}`;
}

/**
 * Format percentage (e.g. +14.28% or -2.10%)
 */
export function formatPercent(pct: number | null | undefined, showSign = true, decimals = 2): string {
  if (pct === null || pct === undefined || isNaN(pct)) {
    return 'N/A';
  }
  const sign = showSign && pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(decimals)}%`;
}

/**
 * Get current business date in Asia/Kolkata as YYYY-MM-DD
 */
export function getKolkataToday(): string {
  try {
    const now = new Date();
    // Use Intl for Asia/Kolkata
    const formatter = new Intl.DateTimeFormat('en-CA', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
    return formatter.format(now); // en-CA returns YYYY-MM-DD
  } catch {
    return new Date().toISOString().split('T')[0];
  }
}

/**
 * Calculate calendar day difference between two YYYY-MM-DD date strings (d2 - d1)
 */
export function daysBetween(date1: string, date2: string): number {
  const [y1, m1, d1] = date1.split('-').map(Number);
  const [y2, m2, d2] = date2.split('-').map(Number);
  
  const utc1 = Date.UTC(y1, m1 - 1, d1);
  const utc2 = Date.UTC(y2, m2 - 1, d2);
  
  const msPerDay = 1000 * 60 * 60 * 24;
  return Math.round((utc2 - utc1) / msPerDay);
}

/**
 * Add days to YYYY-MM-DD date string
 */
export function addDays(isoDate: string, days: number): string {
  const [y, m, d] = isoDate.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().split('T')[0];
}

/**
 * Check if a date string is valid YYYY-MM-DD
 */
export function isValidISODate(dateStr: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateStr)) return false;
  const [y, m, d] = dateStr.split('-').map(Number);
  if (m < 1 || m > 12 || d < 1 || d > 31) return false;
  const testDate = new Date(Date.UTC(y, m - 1, d));
  return testDate.getUTCFullYear() === y && (testDate.getUTCMonth() + 1) === m && testDate.getUTCDate() === d;
}

// Convenient aliases
export const getTodayKolkata = getKolkataToday;
export const formatDateDisplay = formatDisplayDate;

