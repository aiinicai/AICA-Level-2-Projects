import type { UnitMode } from '../types/cma';

export const UNIT_DIVISOR: Record<UnitMode, number> = { rs: 1, thousands: 1000, lakhs: 100000 };
export const UNIT_LABEL: Record<UnitMode, string> = { rs: '₹', thousands: "₹ '000", lakhs: '₹ Lakhs' };

/** Convert a raw rupee value to the display unit */
export function toUnit(v: number, unit: UnitMode): number {
  return v / UNIT_DIVISOR[unit];
}

/** Convert a display-unit value back to raw rupees */
export function fromUnit(v: number, unit: UnitMode): number {
  return v * UNIT_DIVISOR[unit];
}

/** Format a raw rupee value for display in the chosen unit, Indian digit grouping */
export function fmt(v: number | null | undefined, unit: UnitMode, decimals?: number): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  const d = decimals ?? (unit === 'rs' ? 0 : 2);
  const x = toUnit(v, unit);
  return x.toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
}

/** Format a ratio value */
export function fmtRatio(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v) || !Number.isFinite(v)) return '-';
  return v.toFixed(2);
}

/** Parse a user-typed display value into raw rupees */
export function parseInput(s: string, unit: UnitMode): number {
  const n = parseFloat(s.replace(/,/g, ''));
  if (Number.isNaN(n)) return 0;
  return fromUnit(n, unit);
}

export function fyLabelFrom(startYear: number, i: number): string {
  const y = startYear + i;
  return `${y}-${(y + 1).toString().slice(-2)}`;
}

export const MONTHS_FY = [
  'April', 'May', 'June', 'July', 'August', 'September',
  'October', 'November', 'December', 'January', 'February', 'March',
];
