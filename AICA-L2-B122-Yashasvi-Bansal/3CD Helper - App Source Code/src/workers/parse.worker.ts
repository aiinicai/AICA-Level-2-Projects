// Parses uploaded files off the main thread so large ledgers don't freeze the UI.
import * as XLSX from "xlsx";
import { decodeText, detectSoftware, parseTextFile, type Matrix, type ParsedFile } from "../lib/import/sources";
import { isZip, unzip } from "../lib/import/zip";
import { combineSameLayout } from "../lib/import/combine";
import { mergeBooks, type Books } from "../lib/c44/books";
import { parseXml } from "../lib/import/xml";
import { extractLoans, mergeLoanExtracts, type LoanExtract } from "../lib/c31/tally";

const EXCEL_EXT = /\.(xlsx|xlsm|xlsb|xls|ods|xltx)$/i;

function pad(n: number) { return String(n).padStart(2, "0"); }

function sheetToMatrix(ws: XLSX.WorkSheet): Matrix {
  // Fill merged cells with the top-left value so headers/party names aren't lost.
  const merges = ws["!merges"] ?? [];
  for (const m of merges) {
    const topLeft = ws[XLSX.utils.encode_cell(m.s)];
    if (!topLeft) continue;
    for (let r = m.s.r; r <= m.e.r; r++) {
      for (let c = m.s.c; c <= m.e.c; c++) {
        if (r === m.s.r && c === m.s.c) continue;
        const addr = XLSX.utils.encode_cell({ r, c });
        // only fill header-like merges horizontally / party names vertically
        ws[addr] = { ...topLeft };
      }
    }
  }
  const raw = XLSX.utils.sheet_to_json<unknown[]>(ws, { header: 1, raw: true, defval: null, blankrows: false });
  return raw.map((row) =>
    (row as unknown[]).map((v) => {
      if (v instanceof Date) return `${v.getFullYear()}-${pad(v.getMonth() + 1)}-${pad(v.getDate())}`;
      if (v === null || v === undefined) return null;
      if (typeof v === "number" || typeof v === "string") return v;
      if (typeof v === "boolean") return v ? "TRUE" : "FALSE";
      return String(v);
    }),
  );
}

function parseOne(name: string, buffer: ArrayBuffer, module: string): ParsedFile {
  if (/\.pdf$/i.test(name)) {
    throw new Error("PDF files can't be read reliably. Please export the ledger from your accounting software as Excel, CSV or XML.");
  }
  if (EXCEL_EXT.test(name)) {
    const wb = XLSX.read(buffer, { type: "array", cellDates: true, dense: false });
    const sheets = wb.SheetNames.map((sn) => ({ name: sn, rows: sheetToMatrix(wb.Sheets[sn]) })).filter((s) => s.rows.length > 0);
    if (!sheets.length) throw new Error("The workbook has no data.");
    return { software: detectSoftware(sheets[0].rows), sheets };
  }
  if (module === "c31" && /\.xml$/i.test(name)) {
    const loans = extractLoans(parseXml(decodeText(buffer)));
    if (loans.vouchers > 0 || loans.ledgers.length > 0) return { software: "Tally (XML)", sheets: [], loans };
  }
  const result = parseTextFile(name, buffer);
  if (result.software === "CSV" || result.software === "Text") result.software = detectSoftware(result.sheets[0].rows) === "Excel" ? result.software : detectSoftware(result.sheets[0].rows);
  return result;
}

self.onmessage = async (e: MessageEvent<{ name: string; buffer: ArrayBuffer; module?: string }>) => {
  const { name, buffer } = e.data;
  const module = e.data.module ?? "c44";
  try {
    let result: ParsedFile;
    if (isZip(name, buffer)) {
      const entries = (await unzip(buffer)).filter((f) => /\.(xlsx|xlsm|xlsb|xls|ods|xltx|csv|txt|tsv|json|xml)$/i.test(f.name));
      if (!entries.length) throw new Error("The ZIP has no Excel, CSV, XML or JSON files.");
      const parts = entries.map((f) => ({ f, r: parseOne(f.name, f.data, module) }));
      const loanParts = parts.map((p) => p.r.loans).filter(Boolean) as LoanExtract[];
      const bookParts = parts.map((p) => p.r.books).filter(Boolean) as Books[];
      const sheets = parts.flatMap((p) => p.r.sheets.map((s) => ({ ...s, name: entries.length > 1 ? `${p.f.name} – ${s.name}` : s.name })));
      const fileOf = parts.flatMap((p) => p.r.sheets.map(() => p.f.name));
      result = {
        software: Array.from(new Set(parts.map((p) => p.r.software))).join(", "),
        sheets: combineSameLayout(sheets, fileOf),
        gstinDirectory: Object.assign({}, ...parts.map((p) => p.r.gstinDirectory ?? {})),
        loans: loanParts.length ? mergeLoanExtracts(loanParts) : undefined,
        books: bookParts.length ? mergeBooks(bookParts) : undefined,
        files: entries.map((f) => f.name),
      };
    } else {
      result = parseOne(name, buffer, module);
    }
    if (!result.loans && !result.books?.vouchers.length && (!result.sheets.length || result.sheets.every((s) => s.rows.length < 2))) throw new Error("No rows found in this file.");
    (self as unknown as Worker).postMessage({ ok: true, result });
  } catch (err) {
    (self as unknown as Worker).postMessage({ ok: false, error: err instanceof Error ? err.message : String(err) });
  }
};
