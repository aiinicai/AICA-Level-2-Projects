// Indian financial year runs 1 April – 31 March.

export function fyLabel(isoDate: string): string {
  const d = new Date(isoDate + 'T00:00:00');
  const y = d.getFullYear();
  const start = d.getMonth() >= 3 ? y : y - 1;
  return `${start}-${String((start + 1) % 100).padStart(2, '0')}`;
}

export const todayIso = () => toIso(new Date());

export function toIso(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${m}-${day}`;
}

export function daysBetween(fromIso: string, toIsoDate: string): number {
  const a = new Date(fromIso + 'T00:00:00').getTime();
  const b = new Date(toIsoDate + 'T00:00:00').getTime();
  return Math.round((b - a) / 86_400_000);
}

export function monthKey(isoDate: string): string {
  return isoDate.slice(0, 7);
}

/** Expense entry is "past-dated" if it falls before the current month and outside the client's window. */
export function isBackdatedEntry(invoiceDate: string, today: string, windowDays: number): boolean {
  const monthStart = today.slice(0, 8) + '01';
  return invoiceDate < monthStart && daysBetween(invoiceDate, today) > windowDays;
}

/** Display locale for dates — switched with the app language (set from the Shell). */
let dateLocale = 'en-IN';
export const setDateLocale = (lang: 'en' | 'hi') => { dateLocale = lang === 'hi' ? 'hi-IN' : 'en-IN'; };

export function fmtDate(iso?: string): string {
  if (!iso) return '—';
  const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso);
  return d.toLocaleDateString(dateLocale, { day: '2-digit', month: 'short', year: 'numeric' });
}

export const fmtDateTime = (iso: string) =>
  new Date(iso).toLocaleString(dateLocale, { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });

export function monthName(key: string): string {
  const [y, m] = key.split('-').map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(dateLocale, { month: 'short', year: 'numeric' });
}
