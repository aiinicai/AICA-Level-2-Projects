// Converts different file contents into simple tables (header row + data rows).
// Pure functions – used inside the parse Web Worker and covered by tests.

import { parseXml, findAll, childText, xmlToTable, XNode } from "./xml";
import { readBooks, type Books } from "../c44/books";

export type Cell = string | number | null;
export type Matrix = Cell[][];
export interface SheetTable { name: string; rows: Matrix; preMapped?: boolean }
export interface ParsedFile {
  software: string; sheets: SheetTable[]; gstinDirectory?: Record<string, string>;
  /** Clause 31: loan ledgers and their postings read from a Tally XML (Day Book or Group Vouchers). */
  loans?: import("../c31/tally").LoanExtract;
  /** Clause 44 ledger method: groups, ledger masters and vouchers of a Tally XML that carries its masters. */
  books?: Books;
  /** Files read from inside a ZIP. */
  files?: string[];
}

/** Decode bytes, handling UTF-16 (common for Tally exports) and UTF-8 BOM. */
export function decodeText(buf: ArrayBuffer): string {
  const b = new Uint8Array(buf);
  if (b[0] === 0xff && b[1] === 0xfe) return new TextDecoder("utf-16le").decode(b.subarray(2));
  if (b[0] === 0xfe && b[1] === 0xff) return new TextDecoder("utf-16be").decode(b.subarray(2));
  // UTF-16 without BOM: many zero bytes in odd positions
  if (b.length > 8 && b[1] === 0 && b[3] === 0 && b[0] !== 0) return new TextDecoder("utf-16le").decode(b);
  const t = new TextDecoder("utf-8").decode(b);
  return t.charCodeAt(0) === 0xfeff ? t.slice(1) : t;
}

/** CSV / TXT with auto-detected delimiter (comma, tab, pipe, semicolon), quote aware. */
export function parseDelimited(text: string): Matrix {
  const sample = text.split(/\r?\n/).slice(0, 20).join("\n");
  const cands = [",", "\t", "|", ";"];
  let delim = ",", best = -1;
  for (const c of cands) {
    const cnt = sample.split(c).length;
    if (cnt > best) { best = cnt; delim = c; }
  }
  const rows: Matrix = [];
  let row: Cell[] = [];
  let cur = "";
  let q = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (q) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cur += '"'; i++; } else q = false;
      } else cur += ch;
    } else if (ch === '"' && cur === "") q = true;
    else if (ch === delim) { row.push(cur); cur = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && text[i + 1] === "\n") i++;
      row.push(cur); rows.push(row); row = []; cur = "";
    } else cur += ch;
  }
  if (cur !== "" || row.length) { row.push(cur); rows.push(row); }
  return rows.filter((r) => r.some((c) => String(c ?? "").trim() !== ""));
}

const TALLY_HEADER = ["Date", "Voucher Type", "Voucher No", "Party Name", "GSTIN", "Expense Head", "Amount", "Narration"];

/**
 * Tally XML (Day Book / Ledger Vouchers / vouchers export).
 * Each voucher's non-party ledger lines become rows: Party = PARTYLEDGERNAME, Head = ledger, Amount = |amount|.
 * Ledger masters (if present) supply GSTINs.
 */
export function tallyXmlToTable(root: XNode): ParsedFile {
  const gstinDirectory: Record<string, string> = {};
  for (const led of findAll(root, "LEDGER")) {
    const name = (led.attrs["NAME"] || childText(led, "NAME")).trim();
    let g = childText(led, "PARTYGSTIN") || childText(led, "GSTIN");
    if (!g) {
      for (const reg of findAll(led, "LEDGSTREGDETAILS.LIST")) {
        g = childText(reg, "GSTIN");
        if (g) break;
      }
    }
    if (name && g) gstinDirectory[name.toLowerCase()] = g.toUpperCase();
  }
  const rows: Matrix = [TALLY_HEADER];
  for (const v of findAll(root, "VOUCHER")) {
    const date = childText(v, "DATE");
    const vtype = v.attrs["VCHTYPE"] || childText(v, "VOUCHERTYPENAME");
    const vno = childText(v, "VOUCHERNUMBER");
    const party = childText(v, "PARTYLEDGERNAME") || childText(v, "PARTYNAME");
    const partyGstin = childText(v, "PARTYGSTIN") || gstinDirectory[party.toLowerCase()] || "";
    const narration = childText(v, "NARRATION");
    const lines = [
      ...v.children.filter((c) => c.name === "ALLLEDGERENTRIES.LIST" || c.name === "LEDGERENTRIES.LIST"),
      ...v.children.filter((c) => c.name === "ALLINVENTORYENTRIES.LIST" || c.name === "INVENTORYENTRIES.LIST")
        .flatMap((inv) => inv.children.filter((c) => c.name === "ACCOUNTINGALLOCATIONS.LIST")),
    ];
    for (const l of lines) {
      const ledger = childText(l, "LEDGERNAME");
      if (!ledger || ledger.toLowerCase() === party.toLowerCase()) continue;
      const amt = parseFloat(childText(l, "AMOUNT").replace(/,/g, ""));
      if (!isFinite(amt) || amt === 0) continue;
      // In Tally XML, debits are negative. Expenses are debits.
      const isDebit = childText(l, "ISDEEMEDPOSITIVE").toLowerCase() === "yes" || amt < 0;
      rows.push([date, vtype, vno, party || ledger, partyGstin, ledger, isDebit ? Math.abs(amt) : -Math.abs(amt), narration]);
    }
  }
  const books = readBooks(root);
  const withMasters = books.ledgers.some((l) => l.parent);
  return { software: "Tally (XML)", sheets: [{ name: "Tally vouchers", rows, preMapped: true }], gstinDirectory, books: withMasters ? books : undefined };
}

const GSTR2B_HEADER = ["Supplier GSTIN", "Supplier Name", "Invoice No", "Invoice Date", "Taxable Value", "Invoice Value", "Section"];

/** GSTR-2B / 2A JSON from the GST portal → invoice table. Anything else → flat table of the largest array. */
export function jsonToTable(data: unknown): ParsedFile {
  const d = data as Record<string, any>;
  const docdata = d?.data?.docdata ?? d?.docdata;
  if (docdata && (docdata.b2b || docdata.cdnr)) {
    const rows: Matrix = [GSTR2B_HEADER];
    for (const sec of ["b2b", "b2ba"]) {
      for (const s of docdata[sec] ?? []) {
        for (const inv of s.inv ?? []) rows.push([s.ctin, s.trdnm, inv.inum, inv.dt, num(inv.txval), num(inv.val), sec.toUpperCase()]);
      }
    }
    for (const s of docdata.cdnr ?? []) {
      for (const nt of s.nt ?? []) {
        const sign = String(nt.typ).toUpperCase() === "C" ? -1 : 1;
        rows.push([s.ctin, s.trdnm, nt.ntnum, nt.dt, sign * num(nt.txval), sign * num(nt.val), "CDNR"]);
      }
    }
    return { software: "GSTR-2B (GST portal)", sheets: [{ name: "GSTR-2B", rows, preMapped: true }] };
  }
  // generic: find the largest array of objects
  let best: any[] = [];
  const visit = (x: any, depth: number) => {
    if (depth > 6 || !x || typeof x !== "object") return;
    if (Array.isArray(x)) {
      if (x.length > best.length && x.some((e) => e && typeof e === "object" && !Array.isArray(e))) best = x;
      x.slice(0, 50).forEach((e) => visit(e, depth + 1));
    } else Object.values(x).forEach((v) => visit(v, depth + 1));
  };
  visit(data, 0);
  const cols: string[] = [];
  const recs = best.filter((e) => e && typeof e === "object").map((e) => {
    const flat: Record<string, Cell> = {};
    for (const [k, v] of Object.entries(e)) if (v === null || typeof v !== "object") flat[k] = v as Cell;
    Object.keys(flat).forEach((k) => { if (!cols.includes(k)) cols.push(k); });
    return flat;
  });
  return { software: "JSON", sheets: [{ name: "Data", rows: [cols, ...recs.map((r) => cols.map((c) => (r[c] ?? null) as Cell))] }] };
}

function num(v: unknown): number {
  const n = Number(v);
  return isFinite(n) ? n : 0;
}

/** Entry point for text-based files. Excel files are handled with SheetJS in the worker. */
export function parseTextFile(fileName: string, buf: ArrayBuffer): ParsedFile {
  const text = decodeText(buf);
  const lower = fileName.toLowerCase();
  const trimmed = text.trimStart();
  if (lower.endsWith(".json") || trimmed.startsWith("{") || trimmed.startsWith("[")) {
    try { return jsonToTable(JSON.parse(text)); } catch { /* fall through */ }
  }
  if (lower.endsWith(".xml") || trimmed.startsWith("<")) {
    const root = parseXml(text);
    if (findAll(root, "VOUCHER").length || findAll(root, "TALLYMESSAGE").length) return tallyXmlToTable(root);
    return { software: "XML", sheets: [{ name: "XML data", rows: xmlToTable(root) }] };
  }
  return { software: lower.endsWith(".csv") ? "CSV" : "Text", sheets: [{ name: "Data", rows: parseDelimited(text) }] };
}

/** Guess the software that produced a sheet from typical header words / title rows. */
export function detectSoftware(rows: Matrix): string {
  const top = rows.slice(0, 12).map((r) => r.join(" ").toLowerCase()).join(" ");
  if (/tally|ledger vouchers|day book|vch type|vch no/.test(top)) return "Tally";
  if (/busy/.test(top)) return "Busy";
  if (/marg/.test(top)) return "Marg";
  if (/zoho/.test(top)) return "Zoho Books";
  if (/quickbooks|qbo/.test(top)) return "QuickBooks";
  if (/gstr-?2b|gstr-?2a|supplier.*gstin|gstin of supplier/.test(top)) return "GSTR-2B (Excel)";
  if (/posting date|g\/l account|document number|vendor/.test(top)) return "SAP / ERP";
  return "Excel";
}
