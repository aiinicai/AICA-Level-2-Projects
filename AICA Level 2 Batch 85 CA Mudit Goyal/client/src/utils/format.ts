// Display formatters, carried over from the main MGSG app so the two look and
// read the same. Per CLAUDE.md:
//   - the UI shows rupees rounded to the nearest rupee, no decimals
//   - PDFs and print show 2 decimals
//   - dates everywhere read dd-MMM-yy (e.g. 19-May-26)

const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** Rounded to the nearest rupee, with Indian thousands grouping. */
export function formatRupeesUI(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const n = Number(value);
  if (!isFinite(n)) return '';
  return Math.round(n).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

/** Money with 2 decimals — PDF and print contexts only. */
export function formatRupeesPrint(value: number | string | null | undefined): string {
  if (value === null || value === undefined || value === '') return '';
  const n = Number(value);
  if (!isFinite(n)) return '';
  return n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** dd-MMM-yy, e.g. 19-May-26. */
export function formatDateDdMmmYy(d: Date | string | null | undefined): string {
  if (!d) return '';
  const dt = d instanceof Date ? d : new Date(d);
  if (isNaN(dt.getTime())) return '';
  return `${String(dt.getDate()).padStart(2, '0')}-${MONTHS_SHORT[dt.getMonth()]}-${String(dt.getFullYear()).slice(-2)}`;
}

/** dd-MMM-yyyy, for documents where a two-digit year is ambiguous. */
export function formatDateDdMmmYyyy(d: Date | string | null | undefined): string {
  if (!d) return '';
  const dt = d instanceof Date ? d : new Date(d);
  if (isNaN(dt.getTime())) return '';
  return `${String(dt.getDate()).padStart(2, '0')}-${MONTHS_SHORT[dt.getMonth()]}-${dt.getFullYear()}`;
}

/** Clock time as HH:MM, for punches. */
export function formatTime(d: Date | string | null | undefined): string {
  if (!d) return '—';
  const dt = d instanceof Date ? d : new Date(d);
  if (isNaN(dt.getTime())) return '—';
  return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
}

/** Minutes as "7h 45m" — how long someone actually worked. */
export function formatDuration(minutes: number | null | undefined): string {
  const m = Number(minutes ?? 0);
  if (!isFinite(m) || m <= 0) return '—';
  return `${Math.floor(m / 60)}h ${String(m % 60).padStart(2, '0')}m`;
}

/** Today as YYYY-MM-DD, the shape every date input and API filter expects. */
export function todayInputValue(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
