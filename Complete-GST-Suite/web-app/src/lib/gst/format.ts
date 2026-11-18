export function inr(n: number): string {
  const r = Math.round(n);
  return (r < 0 ? "−" : "") + "₹" + Math.abs(r).toLocaleString("en-IN");
}

const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** DD-MMM-YYYY, e.g. 07-Nov-2026 */
export function fmtDate(iso: string): string {
  if (!iso) return "—";
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const d = m ? new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])) : new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${String(d.getDate()).padStart(2, "0")}-${MON[d.getMonth()]}-${d.getFullYear()}`;
}

/** DD-MMM-YYYY HH:MM */
export function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return `${fmtDate(isoDay(d))} ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** FY 2025-26 months as YYYY-MM keys */
export const MONTHS: string[] = Array.from({ length: 12 }, (_, i) => {
  const m = ((i + 3) % 12) + 1;
  const y = i < 9 ? 2025 : 2026;
  return `${y}-${String(m).padStart(2, "0")}`;
});

const MN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function monthLabel(key: string): string {
  const [y = "", m = "1"] = key.split("-");
  return `${MN[Number(m) - 1]}-${y.slice(2)}`;
}

export function daysBetween(fromIso: string, toIso: string): number {
  const a = new Date(fromIso.slice(0, 10) + "T00:00:00");
  const b = new Date(toIso.slice(0, 10) + "T00:00:00");
  return Math.round((b.getTime() - a.getTime()) / 86400000);
}

export function isoDay(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}
