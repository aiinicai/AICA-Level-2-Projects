/**
 * Reads GSTR-2B / purchase register workbooks (xlsx, xls, csv), detects the header row
 * and columns, and turns rows into register entries. Follows the AI Studio rules:
 * - header row = the row (in the first 15) whose cells best match known column names
 * - rows with the same GSTIN + invoice no. are summed (split purchase entries); an
 *   amendment (B2BA) row replaces the original instead
 * - credit/debit notes (CDNR sheets or negative tax) are kept apart from invoices
 * - rows without GSTIN or invoice no. are excluded and listed with the reason
 */
import * as XLSX from 'xlsx';
import type { Kind, Row } from '../types';
import { toIndianDate } from './dates';
import { looksLikeGstin } from './gstin';
import { detectBlocked, detectRcm } from './rules';
import { invKey } from './engine';

export type FieldKey = 'gstin' | 'name' | 'inv' | 'date' | 'taxable' | 'igst' | 'cgst' | 'sgst' | 'total' | 'rcm';

export const FIELDS: { k: FieldKey; lbl: string; req: boolean; hint: string }[] = [
  { k: 'gstin', lbl: 'Supplier GSTIN', req: true, hint: '15-character GSTIN' },
  { k: 'name', lbl: 'Supplier name', req: false, hint: 'Trade / legal name' },
  { k: 'inv', lbl: 'Invoice / note no.', req: true, hint: 'Document number' },
  { k: 'date', lbl: 'Invoice date', req: false, hint: 'Read as dd/mm/yyyy' },
  { k: 'taxable', lbl: 'Taxable value', req: false, hint: 'Value before tax' },
  { k: 'igst', lbl: 'IGST', req: false, hint: 'Integrated tax' },
  { k: 'cgst', lbl: 'CGST', req: false, hint: 'Central tax' },
  { k: 'sgst', lbl: 'SGST / UTGST', req: false, hint: 'State / UT tax' },
  { k: 'total', lbl: 'Invoice value', req: false, hint: 'Taxable + tax' },
  { k: 'rcm', lbl: 'Reverse charge (Y/N)', req: false, hint: 'Reverse charge flag' },
];

const SYNONYMS: Record<FieldKey, string[]> = {
  gstin: ['gstin of supplier', 'gstin/uin of supplier', 'supplier gstin', 'gstin', 'gstin/uin', 'gst no', 'gst no.', 'gst number', 'gstin no', 'gstin no.', 'gst registration no', 'party gstin', 'vendor gstin', 'gstin of party', 'gstin/uin of party', 'gstn', 'party gst no', 'supplier gst', 'registration number'],
  name: ['trade/legal name', 'trade/ legal name', 'legal name of supplier', 'supplier name', 'legal name', 'trade name', 'party name', 'vendor name', 'party', "party's name", "party's a/c name", 'particulars', 'ledger name', 'account name', 'name of supplier', 'supplier legal name', 'name'],
  inv: ['supplier invoice no.', 'supplier invoice no', 'supplier inv no', 'supplier bill no', 'invoice number', 'invoice no', 'invoice no.', 'inv no', 'inv no.', 'bill no', 'bill no.', 'bill number', 'reference no', 'reference no.', 'ref no', 'ref no.', 'document number', 'document no', 'document no.', 'doc no', 'note number', 'note no', 'credit note no', 'debit note no', 'credit/debit note no', 'vch no', 'voucher no', 'voucher no.'],
  date: ['invoice date', 'bill date', 'document date', 'note date', 'credit/debit note date', 'supplier invoice date', 'inv date', 'doc date', 'invoice dt', 'date of invoice', 'voucher date', 'date'],
  taxable: ['taxable value (₹)', 'taxable value (rs)', 'taxable value (rs.)', 'taxable value', 'taxable amount', 'taxable amt', 'assessable value', 'taxable', 'basic value', 'value before tax', 'net value'],
  igst: ['integrated tax (₹)', 'integrated tax(₹)', 'integrated tax', 'integrated tax amount', 'igst (₹)', 'igst amount', 'igst amt', 'igst', 'input igst'],
  cgst: ['central tax (₹)', 'central tax(₹)', 'central tax', 'central tax amount', 'cgst (₹)', 'cgst amount', 'cgst amt', 'cgst', 'input cgst'],
  sgst: ['state/ut tax (₹)', 'state/ut tax(₹)', 'state/ut tax', 'state tax', 'sgst/utgst', 'sgst (₹)', 'sgst amount', 'sgst amt', 'sgst', 'utgst', 'input sgst'],
  total: ['invoice value (₹)', 'invoice value(₹)', 'invoice value', 'note value (₹)', 'note value', 'total invoice value', 'invoice amount', 'bill amount', 'gross total', 'grand total', 'total amount', 'gross amount', 'total value', 'total'],
  rcm: ['supply attract reverse charge', 'reverse charge', 'reverse charge applicable', 'rcm', 'rcm applicable', 'reverse charge (y/n)', 'rev charge'],
};

/* -------------------------------- Workbook -------------------------------- */

/**
 * Reads the file. CSV/TXT cells stay plain text (raw: true) so the spreadsheet library
 * never re-reads dd/mm dates as US mm/dd dates; Excel date cells arrive as serial numbers.
 */
export async function readWorkbook(file: File): Promise<XLSX.WorkBook> {
  const buf = await file.arrayBuffer();
  return XLSX.read(buf, { type: 'array', raw: true, cellDates: false, dense: true });
}

export type Cell = string | number | boolean | null;

export function sheetRows(wb: XLSX.WorkBook, sheet: string): Cell[][] {
  const ws = wb.Sheets[sheet];
  if (!ws) return [];
  const rows = XLSX.utils.sheet_to_json<Cell[]>(ws, { header: 1, defval: '', raw: true, blankrows: false });
  return rows.filter((r) => r.some((c) => c !== '' && c !== null));
}

/** The sheet with most non-empty rows (GSTR-2B files have a "Read me" sheet first). */
export function biggestSheet(wb: XLSX.WorkBook) {
  let best = wb.SheetNames[0];
  let n = -1;
  for (const s of wb.SheetNames) {
    const c = sheetRows(wb, s).length;
    if (c > n) {
      n = c;
      best = s;
    }
  }
  return best;
}

/* ------------------------------ Header detection ---------------------------- */

const clean = (s: unknown) =>
  String(s ?? '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();

/**
 * 100 exact, 80 prefix, 60 contains, 50 all words, 0 none. Synonyms earlier in the list
 * score slightly higher, so "Supplier Invoice No." beats "Voucher No." in a Tally export.
 */
function score(header: unknown, list: string[]): number {
  const h = clean(header);
  if (!h) return 0;
  const first = (test: (s: string) => boolean) => list.findIndex(test);
  let i = first((s) => s === h);
  if (i >= 0) return 100 - i * 0.1;
  i = first((s) => h.startsWith(s) || s.startsWith(h));
  if (i >= 0) return 80 - i * 0.1;
  i = first((s) => h.includes(s) || (s.includes(h) && h.length > 3));
  if (i >= 0) return 60 - i * 0.1;
  const words = h.split(/[\s/\-_().]+/).filter((w) => w.length > 1);
  i = first((s) => {
    const sw = s.split(/[\s/\-_().]+/).filter((w) => w.length > 1);
    return sw.length > 0 && sw.every((w) => words.includes(w));
  });
  return i >= 0 ? 50 - i * 0.1 : 0;
}

export function detectHeaderRow(rows: Cell[][]): number {
  let bestIdx = 0;
  let best = 0;
  for (let i = 0; i < Math.min(15, rows.length); i++) {
    const cells = rows[i].filter((c) => c !== '' && c !== null);
    if (cells.length < 2) continue;
    let total = 0;
    for (const c of cells) {
      for (const k of Object.keys(SYNONYMS) as FieldKey[]) {
        const s = score(c, SYNONYMS[k]);
        if (s > 0) {
          total += s;
          break;
        }
      }
    }
    if (total > best) {
      best = total;
      bestIdx = i;
    }
  }
  return bestIdx;
}

export interface Table {
  headers: string[];
  rows: Record<string, Cell>[];
  headerIdx: number;
}

/**
 * Builds a table from the header row. The official GSTR-2B Excel puts tax headings in
 * two rows ("Tax Amount" above "Integrated Tax(₹)"), so an empty or generic heading is
 * filled from the row below it.
 */
export function toTable(raw: Cell[][], headerIdx: number): Table {
  const head = raw[headerIdx] || [];
  const isHeading = (row: Cell[] | undefined) =>
    !!row && row.filter((c) => typeof c === 'string' && c.trim() && isNaN(Number(c))).length >= 2 && !row.some((c) => looksLikeGstin(c));
  const below = raw[headerIdx + 1] || [];
  const belowIsHeading = isHeading(below);
  // The best-scoring row may be the lower of the two heading rows; then GSTIN / name sit above.
  const above = headerIdx > 0 && isHeading(raw[headerIdx - 1]) ? raw[headerIdx - 1] : [];
  const all = Object.values(SYNONYMS).flat();
  const width = Math.max(head.length, above.length, belowIsHeading ? below.length : 0);
  const seen: Record<string, number> = {};
  const headers: string[] = [];
  for (let i = 0; i < width; i++) {
    let h = String(head[i] ?? '').trim();
    const a = String(above[i] ?? '').trim();
    const b = belowIsHeading ? String(below[i] ?? '').trim() : '';
    if (!h && a) h = a;
    if (b && (!h || /tax amount|amount of tax/i.test(h) || score(b, all) > score(h, all))) h = b;
    if (!h) h = `Column ${i + 1}`;
    seen[h] = (seen[h] || 0) + 1;
    headers.push(seen[h] > 1 ? `${h} (${seen[h]})` : h);
  }
  const start = headerIdx + (belowIsHeading ? 2 : 1);
  const rows: Record<string, Cell>[] = [];
  for (let r = start; r < raw.length; r++) {
    const line = raw[r];
    if (!line.some((c) => c !== '' && c !== null)) continue;
    const o: Record<string, Cell> = {};
    headers.forEach((h, i) => (o[h] = line[i] ?? ''));
    rows.push(o);
  }
  return { headers, rows, headerIdx };
}

export type Mapping = Partial<Record<FieldKey, string>>;

export function autoMap(t: Table): { map: Mapping; conf: Partial<Record<FieldKey, number>> } {
  const map: Mapping = {};
  const conf: Partial<Record<FieldKey, number>> = {};
  const used = new Set<string>();
  for (const f of FIELDS) {
    let best: string | null = null;
    let bs = 0;
    for (const h of t.headers) {
      if (used.has(h)) continue;
      const s = score(h, SYNONYMS[f.k]);
      if (s > bs) {
        bs = s;
        best = h;
      }
    }
    if (best && bs > 0) {
      map[f.k] = best;
      conf[f.k] = bs;
      used.add(best);
    }
  }
  // No clear GSTIN heading: pick the column whose values look like GSTINs.
  if (!map.gstin || (conf.gstin ?? 0) < 60) {
    const sample = t.rows.slice(0, 10);
    for (const h of t.headers) {
      const hits = sample.filter((r) => looksLikeGstin(r[h])).length;
      if (hits >= Math.min(3, sample.length) && hits > 0) {
        map.gstin = h;
        conf.gstin = 95;
        break;
      }
    }
  }
  return { map, conf };
}

/* --------------------------------- Import ---------------------------------- */

export const toNumber = (v: Cell | undefined) => {
  if (typeof v === 'number') return v;
  const s = String(v ?? '').trim();
  if (!s) return 0;
  // "(1,234.50)" and "1,234.50-" are negative amounts in accounting exports
  const neg = /^\(.*\)$/.test(s) || /-$/.test(s);
  const n = parseFloat(s.replace(/[^0-9.-]/g, ''));
  if (!Number.isFinite(n)) return 0;
  return neg && n > 0 ? -n : n;
};

const round2 = (n: number) => Math.round(n * 100) / 100;

const isCdnSheet = (s: string) => /cdnr|credit|debit|cn\/dn|cndn/i.test(s);
const isAmendSheet = (s: string) => /b2ba|cdnra|amend/i.test(s);

export interface ImportOutcome {
  main: Row[];
  cdn: Row[];
  excluded: Row[];
  sheetsUsed: number;
  rcmCount: number;
  blockedRows: { row: Row; catId: string; reason: string }[];
}

/**
 * Builds register rows from the workbook. With allSheets, every sheet is read and mapped
 * on its own (the chosen mapping is reused wherever those headings exist).
 */
export function importWorkbook(
  wb: XLSX.WorkBook,
  kind: Kind,
  mapping: Mapping,
  opts: { allSheets: boolean; sheet: string }
): ImportOutcome {
  const forcedCdn = kind === 'cdn_g2b' || kind === 'cdn_bks';
  const isRcmFile = kind === 'rcm';
  const sheets = opts.allSheets ? wb.SheetNames : [opts.sheet];
  const merged = new Map<string, Row>();
  const cdn: Row[] = [];
  const excluded: Row[] = [];
  let sheetsUsed = 0;

  for (const sheet of sheets) {
    const raw = sheetRows(wb, sheet);
    if (!raw.length) continue;
    const table = toTable(raw, detectHeaderRow(raw));
    if (!table.rows.length) continue;
    const map: Mapping = { ...autoMap(table).map };
    for (const [k, h] of Object.entries(mapping) as [FieldKey, string][]) {
      if (h && table.headers.includes(h)) map[k] = h;
    }
    if (!map.gstin && !map.inv) continue;
    sheetsUsed++;
    const cdnSheet = forcedCdn || isCdnSheet(sheet);
    const amend = isAmendSheet(sheet);
    const get = (r: Record<string, Cell>, k: FieldKey) => (map[k] ? r[map[k]!] : undefined);

    table.rows.forEach((r, i) => {
      const gstin = String(get(r, 'gstin') ?? '').trim().toUpperCase().replace(/\s+/g, '');
      const inv = String(get(r, 'inv') ?? '').trim();
      const name = String(get(r, 'name') ?? '').trim();
      const taxable = round2(toNumber(get(r, 'taxable')));
      const igst = round2(toNumber(get(r, 'igst')));
      const cgst = round2(toNumber(get(r, 'cgst')));
      const sgst = round2(toNumber(get(r, 'sgst')));
      const total = round2(toNumber(get(r, 'total')) || taxable + igst + cgst + sgst);
      if (!gstin && !inv && !taxable && !total && !name) return;
      // Totals rows at the bottom of Tally / Busy exports
      if (!gstin && !inv && /^(grand )?total/i.test(name)) return;

      const row: Row = {
        gstin,
        name,
        inv,
        date: toIndianDate(get(r, 'date')),
        taxable,
        igst,
        cgst,
        sgst,
        total,
        source: kind,
        rowNum: table.headerIdx + i + 2,
        sheet,
        isAmendment: amend || undefined,
      };

      if (cdnSheet || igst + cgst + sgst < -0.01 || isRcmFile) {
        cdn.push(row);
        return;
      }
      if (!gstin || !inv) {
        row.reason = !gstin && !inv ? 'GSTIN and invoice no. missing' : !gstin ? 'GSTIN missing' : 'Invoice no. missing';
        excluded.push(row);
        return;
      }
      const rcm = detectRcm(row, get(r, 'rcm'));
      if (rcm.rcm) {
        row.rcm = true;
        row.rcmReason = rcm.reason;
      }
      const blk = detectBlocked(row);
      if (blk.blocked) {
        row.blocked = true;
        row.blockedReason = blk.reason;
      }
      const key = `${gstin}||${invKey(inv)}`;
      const prev = merged.get(key);
      if (!prev) merged.set(key, row);
      else if (row.isAmendment) merged.set(key, row);
      else if (!prev.isAmendment) {
        prev.taxable = round2(prev.taxable + taxable);
        prev.igst = round2(prev.igst + igst);
        prev.cgst = round2(prev.cgst + cgst);
        prev.sgst = round2(prev.sgst + sgst);
        prev.total = round2(prev.total + total);
      }
    });
  }

  const main = Array.from(merged.values());
  const blockedRows = main
    .map((row) => ({ row, d: detectBlocked(row) }))
    .filter((x) => x.d.blocked)
    .map((x) => ({ row: x.row, catId: (x.d as { catId: string }).catId, reason: (x.d as { reason: string }).reason }));
  return {
    // A separate RCM file is all reverse-charge bills; they are kept in `cdn` above only to
    // skip invoice merging, so hand them back as the main list.
    main: isRcmFile ? cdn.map((r) => ({ ...r, rcm: true })) : main,
    cdn: isRcmFile ? [] : cdn,
    excluded,
    sheetsUsed,
    rcmCount: main.filter((r) => r.rcm).length,
    blockedRows,
  };
}

/* ------------------------------ Sample files ------------------------------- */

export function sampleWorkbook(kind: 'g2b' | 'bks' | 'cdn' | 'rcm'): XLSX.WorkBook {
  const head = ['GSTIN of supplier', 'Trade/Legal name', 'Invoice number', 'Invoice date', 'Taxable Value (₹)', 'Integrated Tax(₹)', 'Central Tax(₹)', 'State/UT Tax(₹)', 'Invoice Value(₹)', 'Reverse Charge'];
  const data: Record<string, (string | number)[][]> = {
    g2b: [
      ['27AAPFU0939F1ZV', 'Sunrise Traders', 'ST/2025-26/0091', '04/10/2025', 100000, 0, 9000, 9000, 118000, 'N'],
      ['29AAGCB1286Q1Z0', 'Bharat Components Pvt Ltd', 'BC-1182', '12/10/2025', 50000, 9000, 0, 0, 59000, 'N'],
      ['27AAACR5055K1Z7', 'Ramesh Roadlines', 'RR/77', '15/10/2025', 20000, 0, 500, 500, 21000, 'Y'],
    ],
    bks: [
      ['27AAPFU0939F1ZV', 'Sunrise Traders', '91', '04/10/2025', 100000, 0, 9000, 9000, 118000, 'N'],
      ['29AAGCB1286Q1Z0', 'Bharat Components Pvt Ltd', 'BC-1182', '12/10/2025', 50000, 9050, 0, 0, 59050, 'N'],
      ['24AAACT2727Q1Z2', 'Western Packaging', 'WP-310', '20/10/2025', 30000, 5400, 0, 0, 35400, 'N'],
    ],
    cdn: [['27AAPFU0939F1ZV', 'Sunrise Traders', 'CN-04', '25/10/2025', -5000, 0, -450, -450, -5900, 'N']],
    rcm: [['27AAACR5055K1Z7', 'Ramesh Roadlines', 'RR/77', '15/10/2025', 20000, 0, 500, 500, 21000, 'Y']],
  };
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet([head, ...data[kind]]), kind === 'cdn' ? 'CDNR' : 'B2B');
  return wb;
}
