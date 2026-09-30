// Formatting & small helpers. Amounts arrive from the API as exact decimal strings;
// formatting is string-based so no precision is lost in the browser.
import { store } from './store.js';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function groupIndian(intStr) {
  if (intStr.length <= 3) return intStr;
  const last3 = intStr.slice(-3);
  let rest = intStr.slice(0, -3);
  const parts = [];
  while (rest.length > 2) { parts.unshift(rest.slice(-2)); rest = rest.slice(0, -2); }
  if (rest) parts.unshift(rest);
  return parts.join(',') + ',' + last3;
}
function groupIntl(intStr) { return intStr.replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

// round a decimal string to n places (half-up) without floating point
export function roundStr(v, places = 2) {
  if (v === null || v === undefined || v === '') return null;
  let s = String(v).trim();
  if (/e/i.test(s)) s = Number(s).toFixed(places + 4);
  let neg = s.startsWith('-');
  if (neg) s = s.slice(1);
  let [i, f = ''] = s.split('.');
  i = i.replace(/^0+(?=\d)/, '') || '0';
  f = f.padEnd(places + 1, '0');
  let keep = f.slice(0, places), next = f.charCodeAt(places) - 48;
  let digits = (i + keep).split('').map(Number);
  if (next >= 5) {
    let k = digits.length - 1;
    while (k >= 0) { if (digits[k] === 9) { digits[k] = 0; k--; } else { digits[k]++; break; } }
    if (k < 0) digits.unshift(1);
  }
  const all = digits.join('');
  const ip = all.slice(0, all.length - places) || '0';
  const fp = places ? all.slice(all.length - places) : '';
  if (/^0+$/.test(ip + fp)) neg = false;
  return (neg ? '-' : '') + ip + (places ? '.' + fp : '');
}

export function money(v, opts = {}) {
  if (v === null || v === undefined || v === '') return opts.blank ?? '—';
  const units = opts.units || store.units || 'ABSOLUTE';
  let s = String(v);
  let places = opts.places ?? 2;
  if (units === 'LAKHS' && !opts.absolute) { s = String(Number(s) / 1e5); places = opts.places ?? 2; }
  if (units === 'CRORES' && !opts.absolute) { s = String(Number(s) / 1e7); places = opts.places ?? 2; }
  const r = roundStr(s, places);
  if (r === null) return '—';
  const neg = r.startsWith('-');
  const [i, f] = (neg ? r.slice(1) : r).split('.');
  const g = (opts.intl || store.numberFormat === 'INTERNATIONAL') ? groupIntl(i) : groupIndian(i);
  const out = g + (f !== undefined ? '.' + f : '');
  if (opts.zeroDash && /^0\.?0*$/.test(i + (f || ''))) return '–';
  return neg ? `(${out})` : out;
}
export function isNeg(v) { return v !== null && v !== undefined && String(v).trim().startsWith('-') && Number(v) !== 0; }
export function num(v, d = 2) { return v === null || v === undefined || v === '' ? '—' : roundStr(v, d); }
export function pct(v, d = 2) { return v === null || v === undefined || v === '' ? '—' : roundStr(v, d) + '%'; }
export function unitLabel() { return { ABSOLUTE: '₹', LAKHS: '₹ lakh', CRORES: '₹ crore' }[store.units || 'ABSOLUTE']; }

export function date(v) {
  if (!v) return '—';
  const s = String(v).slice(0, 10);
  const [y, m, d] = s.split('-');
  if (!d) return s;
  return `${d}-${MONTHS[Number(m) - 1]}-${y}`;
}
export function dateTime(v) {
  if (!v) return '—';
  const s = String(v);
  return date(s) + ' ' + s.slice(11, 16);
}
export function today() { const d = new Date(); return iso(d); }
export function iso(d) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }
export function monthEnd(s) { const [y, m] = s.split('-').map(Number); return iso(new Date(y, m, 0)); }
export function addMonths(s, n) {
  const [y, m, d] = s.split('-').map(Number);
  const t = new Date(y, m - 1 + n, 1);
  const dim = new Date(t.getFullYear(), t.getMonth() + 1, 0).getDate();
  return iso(new Date(t.getFullYear(), t.getMonth(), Math.min(d, dim)));
}
export function addDays(s, n) { const [y, m, d] = s.split('-').map(Number); return iso(new Date(y, m - 1, d + n)); }
export function fyOf(s, startMonth = 4) {
  const [y, m] = s.split('-').map(Number);
  const sy = m >= startMonth ? y : y - 1;
  const start = `${sy}-${String(startMonth).padStart(2, '0')}-01`;
  return [start, addDays(addMonths(start, 12), -1)];
}
export function fyLabel(s, startMonth = 4) { const [a, b] = fyOf(s, startMonth); return `FY ${a.slice(0, 4)}-${b.slice(2, 4)}`; }
export function debounce(fn, ms = 250) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
export function clone(o) { return JSON.parse(JSON.stringify(o ?? null)); }
export function titleCase(s) { return String(s || '').toLowerCase().replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
export function statusClass(s) {
  return { 'Draft': 'draft', 'Prepared': 'prepared', 'Under Review': 'review', 'Approved': 'approved', 'Posted': 'posted',
    'Modified': 'modified', 'Terminated': 'terminated', 'Archived': 'draft', 'Superseded': 'draft', 'Completed': 'approved',
    'Running': 'review', 'Failed': 'bad', 'Rejected': 'bad', 'Validated': 'prepared', 'Errors': 'bad', 'Imported': 'approved',
    'Locked': 'bad', 'Open': 'ok', 'Submitted': 'prepared' }[s] || 'draft';
}
export function sum(rows, key) { return rows.reduce((a, r) => a + Number(r[key] || 0), 0); }

// exact decimal addition of API decimal strings (6 dp internal precision, BigInt based)
function toMicro(v) {
  let s = String(v).trim();
  if (/e/i.test(s)) s = Number(s).toFixed(6);
  const neg = s.startsWith('-');
  if (neg || s.startsWith('+')) s = s.slice(1);
  const [i, f = ''] = s.split('.');
  const b = BigInt((i || '0') + (f + '000000').slice(0, 6));
  return neg ? -b : b;
}
function fromMicro(b) {
  const neg = b < 0n;
  if (neg) b = -b;
  const s = b.toString().padStart(7, '0');
  return (neg ? '-' : '') + s.slice(0, -6) + '.' + s.slice(-6);
}
export function decAdd(...vals) {
  let t = 0n;
  for (const v of vals) { if (v !== null && v !== undefined && v !== '') t += toMicro(v); }
  return fromMicro(t);
}
export function decSub(a, b) { return fromMicro(toMicro(a || 0) - toMicro(b || 0)); }
export function decSum(rows, key) { return decAdd(...rows.map(r => r[key])); }
export function decNeg(a) { return fromMicro(-toMicro(a || 0)); }
