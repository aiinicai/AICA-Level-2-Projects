// Indian number / date formatting and parsing helpers.

const inr2 = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const inr0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });

export function formatINR(n: number | string | null | undefined, opts: { symbol?: boolean; decimals?: boolean } = {}): string {
  const v = Number(n ?? 0);
  if (!isFinite(v)) return "-";
  const s = (opts.decimals === false ? inr0 : inr2).format(v);
  return opts.symbol === false ? s : `₹${s}`;
}

/** Short form for cards: ₹1.25 Cr, ₹4.50 L */
export function formatINRShort(n: number | string | null | undefined): string {
  const v = Number(n ?? 0);
  const a = Math.abs(v);
  if (a >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
  return formatINR(v, { decimals: false });
}

export function formatDate(d: string | Date | null | undefined): string {
  if (!d) return "";
  const dt = typeof d === "string" ? new Date(d.length === 10 ? d + "T00:00:00" : d) : d;
  if (isNaN(dt.getTime())) return "";
  const dd = String(dt.getDate()).padStart(2, "0");
  const mm = String(dt.getMonth() + 1).padStart(2, "0");
  return `${dd}-${mm}-${dt.getFullYear()}`;
}

export function formatDateTime(d: string | null | undefined): string {
  if (!d) return "";
  const dt = new Date(d);
  if (isNaN(dt.getTime())) return "";
  return `${formatDate(dt)} ${String(dt.getHours()).padStart(2, "0")}:${String(dt.getMinutes()).padStart(2, "0")}`;
}

/**
 * Parse amounts as exported by Indian accounting software:
 * "1,23,456.50", "₹ 5,000", "(2,000)", "2,000 Dr", "1500 Cr", "-300", 1234.5
 * Returns null when no number is present.
 */
export function parseAmount(v: unknown): { value: number; side: "dr" | "cr" | null } | null {
  if (v === null || v === undefined) return null;
  if (typeof v === "number") return isFinite(v) ? { value: v, side: null } : null;
  let s = String(v).trim();
  if (!s) return null;
  let side: "dr" | "cr" | null = null;
  const sideMatch = s.match(/\b(dr|cr)\.?\s*$/i);
  if (sideMatch) {
    side = sideMatch[1].toLowerCase() as "dr" | "cr";
    s = s.slice(0, sideMatch.index).trim();
  }
  let negative = false;
  if (/^\(.*\)$/.test(s)) { negative = true; s = s.slice(1, -1); }
  s = s.replace(/₹|rs\.?|inr/gi, "").replace(/[,\s]/g, "");
  if (s.endsWith("-")) { negative = true; s = s.slice(0, -1); }
  if (!/^[-+]?\d*\.?\d+$/.test(s)) return null;
  let n = parseFloat(s);
  if (negative) n = -n;
  return { value: n, side };
}

/** Parse many date styles to ISO yyyy-mm-dd. Excel serials, dd-mm-yyyy, dd/mm/yy, 1-Apr-2024, yyyymmdd (Tally), ISO. */
export function parseDate(v: unknown): string | null {
  if (v === null || v === undefined || v === "") return null;
  const iso = (y: number, m: number, d: number) => {
    if (y < 100) y += y >= 70 ? 1900 : 2000;
    const dt = new Date(Date.UTC(y, m - 1, d));
    if (dt.getUTCFullYear() !== y || dt.getUTCMonth() !== m - 1 || dt.getUTCDate() !== d) return null;
    return `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  };
  if (v instanceof Date) return isNaN(v.getTime()) ? null : iso(v.getFullYear(), v.getMonth() + 1, v.getDate());
  if (typeof v === "number") {
    if (v > 20000 && v < 80000) {
      const ms = Math.round((v - 25569) * 86400 * 1000);
      const dt = new Date(ms);
      return iso(dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate());
    }
    if (v >= 19000101 && v <= 21001231) return parseDate(String(v));
    return null;
  }
  const s = String(v).trim();
  let m = s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (m) return iso(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/);
  if (m) return iso(+m[1], +m[2], +m[3]);
  m = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})/);
  if (m) return iso(+m[3], +m[2], +m[1]);
  const months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"];
  m = s.match(/^(\d{1,2})[-\s/.]([A-Za-z]{3,9})[-\s/.,]+(\d{2,4})/);
  if (m) {
    const mi = months.indexOf(m[2].slice(0, 3).toLowerCase());
    if (mi >= 0) return iso(+m[3], mi + 1, +m[1]);
  }
  if (/^\d+(\.\d+)?$/.test(s)) return parseDate(Number(s));
  return null;
}

/** "2025-26" style assessment years around today. */
export function assessmentYearOptions(): string[] {
  const now = new Date();
  const fyStart = now.getMonth() >= 3 ? now.getFullYear() : now.getFullYear() - 1;
  const currentAY = fyStart + 1;
  const list: string[] = [];
  for (let y = currentAY + 1; y >= currentAY - 6; y--) list.push(`${y}-${String((y + 1) % 100).padStart(2, "0")}`);
  return list;
}

export function previousYearOf(ay: string): string {
  const y = parseInt(ay.slice(0, 4), 10);
  return `${y - 1}-${String(y % 100).padStart(2, "0")}`;
}
