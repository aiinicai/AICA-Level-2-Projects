import * as XLSX from "xlsx";

export type RawRow = Record<string, unknown>;

export type Category =
  | "Matched"
  | "Amount Mismatch"
  | "Missing in 2B"
  | "Missing in Books"
  | "ITC Ineligible"
  | "Duplicate in Books"
  | "Duplicate in 2B";

export interface ParsedInvoice {
  gstin: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  invoiceValue: number;
  taxableValue: number;
  igst: number;
  cgst: number;
  sgst: number;
  itcAvailability?: string;
}

export interface ReconRow {
  key: string;
  gstin: string;
  supplier: string;
  invoiceNumber: string;
  invoiceDate: string;
  valueBooks: number | null;
  value2B: number | null;
  taxBooks: number | null;
  tax2B: number | null;
  difference: number;
  category: Category;
  remarks: string;
}

export const TOLERANCE = 1;

const pick = (row: RawRow, candidates: string[]): unknown => {
  const keys = Object.keys(row);
  for (const c of candidates) {
    const hit = keys.find(
      (k) => k.toLowerCase().replace(/[^a-z0-9]/g, "") === c.toLowerCase().replace(/[^a-z0-9]/g, ""),
    );
    if (hit !== undefined) return row[hit];
  }
  // loose contains match
  for (const c of candidates) {
    const needle = c.toLowerCase().replace(/[^a-z0-9]/g, "");
    const hit = keys.find((k) => k.toLowerCase().replace(/[^a-z0-9]/g, "").includes(needle));
    if (hit !== undefined) return row[hit];
  }
  return undefined;
};

const num = (v: unknown): number => {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = Number(v.replace(/[^0-9.\-]/g, ""));
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
};

const str = (v: unknown): string => (v === undefined || v === null ? "" : String(v).trim());

export const normalizeInvoiceNo = (v: string): string =>
  v
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, "")
    .replace(/^0+/, "");

export const normalizeGstin = (v: string): string => v.toUpperCase().replace(/[^A-Z0-9]/g, "");

const excelDate = (v: unknown): string => {
  if (typeof v === "number") {
    const d = XLSX.SSF.parse_date_code(v);
    if (d) return `${String(d.d).padStart(2, "0")}/${String(d.m).padStart(2, "0")}/${d.y}`;
  }
  return str(v);
};

export function rowsToInvoices(rows: RawRow[]): ParsedInvoice[] {
  return rows
    .map((r) => ({
      gstin: str(pick(r, ["GSTIN", "Supplier GSTIN", "GSTIN of supplier"])),
      supplier: str(pick(r, ["Supplier Name", "Trade Name", "Supplier"])),
      invoiceNumber: str(pick(r, ["Invoice Number", "Invoice No", "Document Number"])),
      invoiceDate: excelDate(pick(r, ["Invoice Date", "Document Date"])),
      invoiceValue: num(pick(r, ["Invoice Value", "Total Invoice Value"])),
      taxableValue: num(pick(r, ["Taxable Value"])),
      igst: num(pick(r, ["IGST"])),
      cgst: num(pick(r, ["CGST"])),
      sgst: num(pick(r, ["SGST"])),
      itcAvailability: str(pick(r, ["ITC Availability", "ITC Available", "ITC"])),
    }))
    .filter((i) => i.gstin || i.invoiceNumber);
}

export async function parseFile(file: File): Promise<{ rows: RawRow[]; headers: string[] }> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: "array" });
  const sheetName = wb.SheetNames[0];
  const ws = sheetName ? wb.Sheets[sheetName] : undefined;
  if (!ws) return { rows: [], headers: [] };
  const rows = XLSX.utils.sheet_to_json<RawRow>(ws, { defval: "" });
  const first = rows[0];
  const headers = first ? Object.keys(first) : [];
  return { rows, headers };
}

const totalTax = (i: ParsedInvoice) => i.igst + i.cgst + i.sgst;

const isIneligible = (i: ParsedInvoice) => {
  const v = (i.itcAvailability ?? "").trim().toLowerCase();
  if (!v) return false;
  if (v === "yes" || v === "y" || v === "available" || v === "eligible") return false;
  return true;
};

export function reconcile(books: ParsedInvoice[], gstr2b: ParsedInvoice[]): ReconRow[] {
  const keyOf = (i: ParsedInvoice) => `${normalizeGstin(i.gstin)}|${normalizeInvoiceNo(i.invoiceNumber)}`;
  const map2b = new Map<string, ParsedInvoice>();
  gstr2b.forEach((i) => {
    const k = keyOf(i);
    if (!map2b.has(k)) map2b.set(k, i);
  });
  const countIn = (list: ParsedInvoice[]) => {
    const c = new Map<string, number>();
    list.forEach((i) => c.set(keyOf(i), (c.get(keyOf(i)) ?? 0) + 1));
    return c;
  };
  const booksCounts = countIn(books);
  const b2Counts = countIn(gstr2b);
  const seenBooks = new Set<string>();
  const seen2b = new Set<string>();
  const used = new Set<string>();
  const out: ReconRow[] = [];

  for (const b of books) {
    const key = keyOf(b);
    if (seenBooks.has(key)) {
      out.push({
        key,
        gstin: b.gstin,
        supplier: b.supplier,
        invoiceNumber: b.invoiceNumber,
        invoiceDate: b.invoiceDate,
        valueBooks: b.invoiceValue,
        value2B: null,
        taxBooks: totalTax(b),
        tax2B: null,
        difference: 0,
        category: "Duplicate in Books",
        remarks: `Duplicate invoice entry detected in Purchase Register (same GSTIN + Invoice Number appears ${booksCounts.get(key) ?? 2} times). Only one instance matched against GSTR-2B — review for double booking of ITC.`,
      });
      continue;
    }
    seenBooks.add(key);
    const m = map2b.get(key);
    if (!m) {
      out.push({
        key,
        gstin: b.gstin,
        supplier: b.supplier,
        invoiceNumber: b.invoiceNumber,
        invoiceDate: b.invoiceDate,
        valueBooks: b.invoiceValue,
        value2B: null,
        taxBooks: totalTax(b),
        tax2B: null,
        difference: b.invoiceValue,
        category: "Missing in 2B",
        remarks: "Not reported by supplier in GSTR-2B — ITC at risk. Follow up with supplier.",
      });
      continue;
    }
    used.add(key);
    const valDiff = b.invoiceValue - m.invoiceValue;
    const taxDiff = totalTax(b) - totalTax(m);
    const mismatch = Math.abs(valDiff) > TOLERANCE || Math.abs(taxDiff) > TOLERANCE;
    const ineligible = isIneligible(m);
    const category: Category = ineligible ? "ITC Ineligible" : mismatch ? "Amount Mismatch" : "Matched";
    out.push({
      key,
      gstin: b.gstin || m.gstin,
      supplier: b.supplier || m.supplier,
      invoiceNumber: b.invoiceNumber,
      invoiceDate: b.invoiceDate || m.invoiceDate,
      valueBooks: b.invoiceValue,
      value2B: m.invoiceValue,
      taxBooks: totalTax(b),
      tax2B: totalTax(m),
      difference: valDiff,
      category,
      remarks: ineligible
        ? `ITC marked ineligible in 2B${m.itcAvailability ? ` (${m.itcAvailability})` : ""}`
        : mismatch
          ? `Value diff ₹${valDiff.toFixed(2)}, tax diff ₹${taxDiff.toFixed(2)}`
          : "Matched within ₹1 tolerance",
    });
  }

  for (const m of gstr2b) {
    const key = keyOf(m);
    if (seen2b.has(key)) {
      out.push({
        key,
        gstin: m.gstin,
        supplier: m.supplier,
        invoiceNumber: m.invoiceNumber,
        invoiceDate: m.invoiceDate,
        valueBooks: null,
        value2B: m.invoiceValue,
        taxBooks: null,
        tax2B: totalTax(m),
        difference: 0,
        category: "Duplicate in 2B",
        remarks: `Duplicate invoice entry detected in GSTR-2B (same GSTIN + Invoice Number appears ${b2Counts.get(key) ?? 2} times). Only one instance was compared — could be an amended invoice; review before claiming ITC.`,
      });
      continue;
    }
    seen2b.add(key);
    if (used.has(key)) continue;
    const ineligible = isIneligible(m);
    out.push({
      key,
      gstin: m.gstin,
      supplier: m.supplier,
      invoiceNumber: m.invoiceNumber,
      invoiceDate: m.invoiceDate,
      valueBooks: null,
      value2B: m.invoiceValue,
      taxBooks: null,
      tax2B: totalTax(m),
      difference: -m.invoiceValue,
      category: ineligible ? "ITC Ineligible" : "Missing in Books",
      remarks: ineligible
        ? `In 2B but ITC ineligible${m.itcAvailability ? ` (${m.itcAvailability})` : ""}; also not in books`
        : "In GSTR-2B only — possible unrecorded purchase. Verify with accounts.",
    });
  }

  return out;
}

export interface Summary {
  total: number;
  counts: Record<Category, number>;
  matchedPct: number;
  itcAtRisk: number;
  duplicates: number;
}

const DUPLICATE_CATEGORIES: Category[] = ["Duplicate in Books", "Duplicate in 2B"];
const isDuplicate = (c: Category) => DUPLICATE_CATEGORIES.includes(c);

export function summarize(rows: ReconRow[]): Summary {
  const counts: Record<Category, number> = {
    Matched: 0,
    "Amount Mismatch": 0,
    "Missing in 2B": 0,
    "Missing in Books": 0,
    "ITC Ineligible": 0,
    "Duplicate in Books": 0,
    "Duplicate in 2B": 0,
  };
  let itcAtRisk = 0;
  for (const r of rows) {
    counts[r.category] += 1;
    if (r.category === "Missing in 2B") itcAtRisk += r.taxBooks ?? 0;
    if (r.category === "Amount Mismatch") itcAtRisk += Math.abs((r.taxBooks ?? 0) - (r.tax2B ?? 0));
    if (r.category === "ITC Ineligible") itcAtRisk += r.tax2B ?? 0;
    if (isDuplicate(r.category)) itcAtRisk += (r.taxBooks ?? 0) || (r.tax2B ?? 0);
  }
  const duplicates = counts["Duplicate in Books"] + counts["Duplicate in 2B"];
  const compared = rows.length - duplicates;
  return {
    total: compared,
    counts,
    matchedPct: compared ? (counts.Matched / compared) * 100 : 0,
    itcAtRisk,
    duplicates,
  };
}

export function exportToExcel(rows: ReconRow[]) {
  const data = rows.map((r) => ({
    GSTIN: r.gstin,
    "Supplier Name": r.supplier,
    "Invoice Number": r.invoiceNumber,
    "Invoice Date": r.invoiceDate,
    "Invoice Value (Books)": r.valueBooks ?? "",
    "Invoice Value (2B)": r.value2B ?? "",
    "Tax (Books)": r.taxBooks ?? "",
    "Tax (2B)": r.tax2B ?? "",
    Difference: Number(r.difference.toFixed(2)),
    Category: r.category,
    Remarks: r.remarks,
  }));
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, "Reconciliation");
  XLSX.writeFile(wb, `GST-Reconciliation-${new Date().toISOString().slice(0, 10)}.xlsx`);
}

export const formatINR = (n: number) =>
  `₹${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
