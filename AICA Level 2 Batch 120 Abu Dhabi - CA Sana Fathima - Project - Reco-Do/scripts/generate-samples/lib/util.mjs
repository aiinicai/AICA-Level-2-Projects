// Date and money helpers. All dates are UTC midnight so Excel serials are stable on any machine.

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function d(y, m, day) {
  return new Date(Date.UTC(y, m - 1, day));
}
export function addDays(date, n) {
  return new Date(date.getTime() + n * 86400000);
}
export function dayDiff(a, b) {
  return Math.round((b.getTime() - a.getTime()) / 86400000);
}
/** UAE weekend is Saturday + Sunday. */
export function isWeekend(date) {
  const w = date.getUTCDay();
  return w === 0 || w === 6;
}
export function businessDays(y, m) {
  const out = [];
  for (let i = 1; i <= 31; i++) {
    const dt = d(y, m, i);
    if (dt.getUTCMonth() !== m - 1) break;
    if (!isWeekend(dt)) out.push(dt);
  }
  return out;
}
/** Next business day on or after date. */
export function nextBiz(date) {
  let x = date;
  while (isWeekend(x)) x = addDays(x, 1);
  return x;
}
export function fmtDate(date) {
  const dd = String(date.getUTCDate()).padStart(2, '0');
  return `${dd}-${MON[date.getUTCMonth()]}-${date.getUTCFullYear()}`;
}
export function fmtDMY(date) {
  return `${String(date.getUTCDate()).padStart(2, '0')}/${String(date.getUTCMonth() + 1).padStart(2, '0')}/${date.getUTCFullYear()}`;
}
export function ymd(date) {
  return date.toISOString().slice(0, 10);
}
/** Excel serial (1900 system) to UTC date. */
export function serialToDate(serial) {
  return new Date(Math.round((serial - 25569) * 86400000));
}

/** Integer cents -> "1,234.56" (negative shown with leading minus). */
export function fmtAmt(c) {
  const neg = c < 0;
  const abs = Math.abs(c);
  const whole = Math.floor(abs / 100)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${neg ? '-' : ''}${whole}.${String(abs % 100).padStart(2, '0')}`;
}
export const toAed = (c) => (c == null ? null : Math.round(c) / 100);
export const toCents = (v) => (v == null || v === '' ? 0 : Math.round(Number(v) * 100));
export const sum = (arr, f = (x) => x) => arr.reduce((s, x) => s + f(x), 0);

export function pad(n, w) {
  return String(n).padStart(w, '0');
}
