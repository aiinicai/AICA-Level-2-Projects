import * as XLSX from "xlsx";
import { FIELDS, SOURCES, type FieldKey, type SourceKey } from "./types";

export interface ParsedSheet {
  headers: string[];
  rows: Record<string, unknown>[];
}

export async function parseFile(file: File): Promise<ParsedSheet> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { cellDates: true });
  const sheetName = wb.SheetNames[0];
  if (!sheetName) throw new Error("The file does not contain any worksheet.");
  const ws = wb.Sheets[sheetName];
  if (!ws) throw new Error("The first worksheet could not be read.");
  const rows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, { defval: "" });
  const first = rows[0];
  if (!first) throw new Error("The first worksheet is empty. Please check the file and try again.");
  const headers = Object.keys(first);
  return { headers, rows };
}

const SYNONYMS: Record<FieldKey, string[]> = {
  invoice_no: ["invoice no", "invoice number", "document no", "doc no", "bill no", "voucher no", "invoice"],
  invoice_date: ["invoice date", "document date", "date", "bill date", "voucher date"],
  party_name: ["party name", "party", "customer name", "supplier name", "trade name", "legal name", "name"],
  party_gstin: ["gstin", "party gstin", "gstin/uin", "customer gstin", "supplier gstin", "gst no"],
  taxable_value: ["taxable value", "taxable amount", "assessable value", "net value", "value"],
  gst_rate: ["rate", "gst rate", "tax rate", "rate %"],
  cgst: ["cgst", "cgst amount", "central tax"],
  sgst: ["sgst", "sgst amount", "state tax", "utgst"],
  igst: ["igst", "igst amount", "integrated tax"],
  cess: ["cess", "cess amount"],
  place_of_supply: ["place of supply", "pos", "state"],
  voucher_type: ["voucher type", "type", "vch type"],
  reverse_charge: ["reverse charge", "rcm", "reverse charge applicable"],
  doc_type: ["document type", "note type", "nature of document", "doc type"],
  original_invoice_no: ["original invoice no", "original invoice number", "ref invoice no"],
  supply_type: ["supply type", "nature of supply", "category", "section"],
  hsn: ["hsn", "hsn/sac", "sac", "hsn code"],
};

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, " ").replace(/\s+/g, " ").trim();

export function autoMap(headers: string[]): Partial<Record<FieldKey, string>> {
  const map: Partial<Record<FieldKey, string>> = {};
  for (const f of FIELDS) {
    const cands = [norm(f.label), ...SYNONYMS[f.key].map(norm)];
    const hit =
      headers.find((h) => cands.includes(norm(h))) ??
      headers.find((h) => cands.some((c) => norm(h).includes(c) && c.length > 3));
    if (hit) map[f.key] = hit;
  }
  return map;
}

export function toNumber(v: unknown): number {
  if (typeof v === "number") return isFinite(v) ? v : 0;
  const s = String(v ?? "").replace(/[₹,\s]/g, "").replace(/\((.*)\)/, "-$1");
  const n = parseFloat(s);
  return isFinite(n) ? n : 0;
}

export function toDate(v: unknown): string {
  if (v instanceof Date) return v.toISOString().slice(0, 10);
  const s = String(v ?? "").trim();
  if (!s) return "";
  const dmy = s.match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})$/);
  if (dmy) {
    const d = dmy[1] ?? "";
    const m = dmy[2] ?? "";
    const y = dmy[3] ?? "";
    const yy = y.length === 2 ? `20${y}` : y;
    return `${yy}-${m.padStart(2, "0")}-${d.padStart(2, "0")}`;
  }
  const p = new Date(s);
  return isNaN(p.getTime()) ? "" : p.toISOString().slice(0, 10);
}

export const GSTIN_RE = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;

export interface MappedRow {
  invoice_no: string;
  invoice_date: string;
  party_name: string;
  party_gstin: string;
  taxable_value: number;
  gst_rate: number;
  cgst: number;
  sgst: number;
  igst: number;
  cess: number;
  place_of_supply: string;
  voucher_type: string;
  reverse_charge: number;
  doc_type: string;
  original_invoice_no: string;
  supply_type: string;
  hsn: string;
}

export interface ValidationIssue {
  row: number;
  field: string;
  message: string;
  severity: "error" | "warning";
}

export function mapRows(
  rows: Record<string, unknown>[],
  map: Partial<Record<FieldKey, string>>,
): { data: MappedRow[]; issues: ValidationIssue[] } {
  const issues: ValidationIssue[] = [];
  const get = (r: Record<string, unknown>, k: FieldKey) => (map[k] ? r[map[k] as string] : "");
  const data = rows.map((r, i) => {
    const rowNo = i + 2;
    const taxable = toNumber(get(r, "taxable_value"));
    const gstin = String(get(r, "party_gstin") ?? "").trim().toUpperCase();
    const invNo = String(get(r, "invoice_no") ?? "").trim();
    const date = toDate(get(r, "invoice_date"));
    if (!invNo) issues.push({ row: rowNo, field: "Invoice number", message: "Invoice number is blank.", severity: "error" });
    if (!date) issues.push({ row: rowNo, field: "Invoice date", message: "Date is missing or not readable.", severity: "warning" });
    if (gstin && !GSTIN_RE.test(gstin))
      issues.push({ row: rowNo, field: "Party GSTIN", message: `"${gstin}" is not a valid 15-character GSTIN.`, severity: "warning" });
    if (taxable === 0)
      issues.push({ row: rowNo, field: "Taxable value", message: "Taxable value is zero or not a number.", severity: "warning" });

    const rcmRaw = String(get(r, "reverse_charge") ?? "").trim().toLowerCase();
    return {
      invoice_no: invNo,
      invoice_date: date,
      party_name: String(get(r, "party_name") ?? "").trim(),
      party_gstin: gstin,
      taxable_value: taxable,
      gst_rate: toNumber(get(r, "gst_rate")),
      cgst: toNumber(get(r, "cgst")),
      sgst: toNumber(get(r, "sgst")),
      igst: toNumber(get(r, "igst")),
      cess: toNumber(get(r, "cess")),
      place_of_supply: String(get(r, "place_of_supply") ?? "").trim(),
      voucher_type: String(get(r, "voucher_type") ?? "").trim(),
      reverse_charge: ["y", "yes", "true", "1"].includes(rcmRaw) ? 1 : 0,
      doc_type: String(get(r, "doc_type") ?? "").trim() || "Invoice",
      original_invoice_no: String(get(r, "original_invoice_no") ?? "").trim(),
      supply_type: String(get(r, "supply_type") ?? "").trim() || (gstin ? "B2B" : "B2C"),
      hsn: String(get(r, "hsn") ?? "").trim(),
    } satisfies MappedRow;
  });
  return { data, issues };
}

/* ---------- sample templates ---------- */
const SAMPLE: Record<string, string | number> = {
  "Invoice No": "INV-0001",
  "Invoice Date": "01-04-2025",
  "Party Name": "Sample Traders Pvt Ltd",
  GSTIN: "27AAAAA0000A1Z5",
  "Taxable Value": 100000,
  "GST Rate": 18,
  CGST: 9000,
  SGST: 9000,
  IGST: 0,
  Cess: 0,
  "Place of Supply": "Maharashtra",
  "Voucher Type": "Sales",
  "Reverse Charge": "N",
  "Document Type": "Invoice",
  "Original Invoice No": "",
  "Supply Type": "B2B",
  HSN: "9983",
};

export function downloadTemplate(source: SourceKey) {
  const label = SOURCES.find((s) => s.key === source)?.label ?? source;
  const ws = XLSX.utils.json_to_sheet([SAMPLE as unknown as Record<string, unknown>]);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Template");
  XLSX.writeFile(wb, `${label.replace(/[^\w]+/g, "_")}_Template.xlsx`);
}
