import type { Field } from "@/lib/types";

export type Cell = string | number | null;
export type SheetRows = Record<string, Cell>[];

export interface ParsedWorkbook {
  sheetNames: string[];
  sheets: Record<string, { columns: string[]; rows: SheetRows }>;
}

/** Reads an .xlsx/.xls/.csv file in the browser. The file never leaves the device until import. */
export async function parseWorkbook(file: File): Promise<ParsedWorkbook> {
  const XLSX = await import("xlsx");
  const isText = /\.csv$/i.test(file.name);
  // Text files keep their cells as written so 01/04/2026 stays day-first, not US month-first.
  const wb = isText
    ? XLSX.read(await file.text(), { type: "string", raw: true, cellDates: false })
    : XLSX.read(await file.arrayBuffer(), { cellDates: true });
  const sheets: ParsedWorkbook["sheets"] = {};
  for (const name of wb.SheetNames) {
    const ws = wb.Sheets[name];
    if (!ws) continue;
    const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, { defval: null, raw: !isText });

    const columns: string[] = [];
    const normalised: SheetRows = rows.map((r) => {
      const out: Record<string, Cell> = {};
      for (const [k, v] of Object.entries(r)) {
        const key = k.trim();
        if (!columns.includes(key)) columns.push(key);
        out[key] = toCell(v);
      }
      return out;
    });
    sheets[name] = { columns, rows: normalised };
  }
  return { sheetNames: Object.keys(sheets), sheets };
}

function toCell(value: unknown): Cell {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  if (typeof value === "number" || typeof value === "string") return value;
  return String(value);
}

const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "");

/** Best-effort guess of which sheet column feeds each dataset field. */
export function autoMap(columns: string[], fields: Field[]): Record<string, string> {
  const map: Record<string, string> = {};
  const taken = new Set<string>();

  // Pass 1: exact name/label matches win the column outright.
  for (const field of fields) {
    const targets = [slug(field.name), slug(field.label)];
    const hit = columns.find((c) => !taken.has(c) && targets.includes(slug(c)));
    if (hit) {
      map[field.name] = hit;
      taken.add(hit);
    }
  }

  // Pass 2: remaining fields take a close partial match on a still-free column.
  for (const field of fields) {
    if (map[field.name]) continue;
    const targets = [slug(field.name), slug(field.label)];
    const hit = columns.find(
      (c) =>
        !taken.has(c) &&
        targets.some((t) => {
          const col = slug(c);
          return col.startsWith(t) || t.startsWith(col) || col.endsWith(t) || t.endsWith(col);
        }),
    );
    if (hit) {
      map[field.name] = hit;
      taken.add(hit);
    }
  }
  return map;
}


export interface ValidationIssue {
  level: "error" | "warning";
  message: string;
}

export interface MappingResult {
  rows: SheetRows;
  issues: ValidationIssue[];
  skipped: number;
}

/** Converts mapped sheet rows into dataset rows, reporting anything that could not be read. */
export function applyMapping(
  rows: SheetRows,
  fields: Field[],
  mapping: Record<string, string>,
  dateField?: string,
): MappingResult {
  const issues: ValidationIssue[] = [];
  const mapped = fields.filter((f) => mapping[f.name]);

  if (mapped.length === 0) issues.push({ level: "error", message: "Match at least one column before importing." });
  if (dateField && !mapping[dateField])
    issues.push({ level: "warning", message: "No date column matched — time-based charts will be empty." });
  if (!mapped.some((f) => f.role === "measure"))
    issues.push({ level: "warning", message: "No amount or quantity column matched — totals will show zero." });

  const badNumbers = new Map<string, number>();
  const badDates = new Map<string, number>();
  const out: SheetRows = [];
  let skipped = 0;

  for (const row of rows) {
    const record: Record<string, Cell> = {};
    let hasValue = false;
    for (const field of mapped) {
      const raw = row[mapping[field.name]!] ?? null;
      if (raw === null) {
        record[field.name] = field.role === "measure" ? 0 : null;
        continue;
      }
      hasValue = true;
      if (field.type === "number" || field.type === "currency" || field.type === "percent") {
        const n = typeof raw === "number" ? raw : Number(String(raw).replace(/[^0-9.-]/g, ""));
        if (Number.isNaN(n)) {
          badNumbers.set(field.label, (badNumbers.get(field.label) ?? 0) + 1);
          record[field.name] = 0;
        } else record[field.name] = n;
      } else if (field.type === "date") {
        const iso = toIsoDate(raw);
        if (!iso) badDates.set(field.label, (badDates.get(field.label) ?? 0) + 1);
        record[field.name] = iso;
      } else {
        record[field.name] = String(raw);
      }
    }
    if (!hasValue) {
      skipped += 1;
      continue;
    }
    out.push(record);
  }

  for (const [label, count] of badNumbers)
    issues.push({ level: "warning", message: `${count} row(s) in “${label}” were not numbers and were read as 0.` });
  for (const [label, count] of badDates)
    issues.push({ level: "warning", message: `${count} row(s) in “${label}” had a date that could not be read.` });
  if (skipped) issues.push({ level: "warning", message: `${skipped} empty row(s) will be ignored.` });
  if (out.length === 0) issues.push({ level: "error", message: "No usable rows found in this sheet." });

  return { rows: out, issues, skipped };
}

function toIsoDate(raw: Cell): string | null {
  if (raw === null) return null;
  if (typeof raw === "number") {
    // Excel serial date (days since 30 Dec 1899)
    const ms = Math.round((raw - 25569) * 86400000);
    const d = new Date(ms);
    return Number.isNaN(d.getTime()) ? null : d.toISOString().slice(0, 10);
  }
  const s = raw.trim();
  const dmy = s.match(/^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$/);
  if (dmy) {
    const [, d, m, y] = dmy;
    const year = y!.length === 2 ? `20${y}` : y!;
    return `${year}-${m!.padStart(2, "0")}-${d!.padStart(2, "0")}`;
  }
  const parsed = new Date(s);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toISOString().slice(0, 10);
}
