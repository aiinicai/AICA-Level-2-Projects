import type { Unit } from './types';

const inr = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const inr2 = new Intl.NumberFormat('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Indian-style compact currency: ₹ 1.25 Cr, ₹ 4.30 L, ₹ 12,345. Negatives in parentheses (accounting style). */
export function fmtMoney(v: number | null | undefined, opts: { compact?: boolean; symbol?: string; exact?: boolean } = {}) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const sym = opts.symbol ?? '₹';
  const abs = Math.abs(v);
  let body: string;
  if (opts.exact) body = inr2.format(abs);
  else if (opts.compact !== false && abs >= 1e7) body = `${(abs / 1e7).toFixed(2)} Cr`;
  else if (opts.compact !== false && abs >= 1e5) body = `${(abs / 1e5).toFixed(2)} L`;
  else body = inr.format(abs);
  return v < 0 ? `(${sym}${body})` : `${sym}${body}`;
}

export function fmtPct(v: number | null | undefined, dp = 1) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return `${v.toFixed(dp)}%`;
}

export function fmtNum(v: number | null | undefined, dp = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: dp }).format(v);
}

export function fmtValue(v: number | null | undefined, unit: Unit, compact = true) {
  switch (unit) {
    case 'currency':
      return fmtMoney(v, { compact });
    case 'percent':
      return fmtPct(v);
    case 'ratio':
      return v === null || v === undefined ? '—' : `${v.toFixed(2)}x`;
    case 'days':
      return v === null || v === undefined ? '—' : `${Math.round(v)} days`;
    case 'months':
      return v === null || v === undefined ? '—' : `${v.toFixed(1)} months`;
    case 'qty':
      return fmtNum(v, 3);
    default:
      return fmtNum(v, 0);
  }
}

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return '—';
  const [y, m, d] = iso.slice(0, 10).split('-');
  return `${d}-${['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][Number(m) - 1]}-${y}`;
}
