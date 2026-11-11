/**
 * Checks for the reconciliation engine, the importer and the two AI Studio bugs fixed here.
 * Run with:  npm test
 */
import fs from 'node:fs';
import * as XLSX from 'xlsx';
import { toIndianDate } from '../src/lib/dates';
import { checkGstin } from '../src/lib/gstin';
import { autoMap, detectHeaderRow, importWorkbook, sheetRows, toTable } from '../src/lib/importer';
import { invCore, invKey, runAll, timeBarred } from '../src/lib/engine';
import type { Datasets, Row } from '../src/types';

let failed = 0;
let passed = 0;
function eq(name: string, got: unknown, want: unknown) {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (ok) passed++;
  else {
    failed++;
    console.log(`FAIL ${name}\n     got:  ${JSON.stringify(got)}\n     want: ${JSON.stringify(want)}`);
  }
}

/* ---------------- Dates: always day-first ---------------- */
eq('dd/mm/yyyy', toIndianDate('04/10/2026'), '04/10/2026');
eq('d-m-yy', toIndianDate('4-10-26'), '04/10/2026');
eq('dd.mm.yyyy', toIndianDate('04.10.2026'), '04/10/2026');
eq('ISO', toIndianDate('2026-10-04'), '04/10/2026');
eq('dd-Mon-yyyy', toIndianDate('04-Oct-2026'), '04/10/2026');
eq('Excel serial', toIndianDate(46299), '04/10/2026');
eq('impossible date', toIndianDate('31/02/2026'), '');
eq('13th month is not swapped', toIndianDate('12/13/2026'), '');
eq('amount is not a date', toIndianDate(118000), '');

/* ---------------- CSV import keeps 04/10 as 4 October ---------------- */
const csv = [
  'GSTIN of supplier,Trade/Legal name,Invoice number,Invoice date,Taxable Value,Integrated Tax,Central Tax,State/UT Tax,Invoice Value',
  '27AAPFU0939F1ZV,Sunrise Traders,ST/2025-26/0091,04/10/2025,100000,0,9000,9000,118000',
  '27AAPFU0939F1ZV,Sunrise Traders,ST/2025-26/0092,13/10/2025,1000,0,90,90,1180',
].join('\n');
const wbCsv = XLSX.read(csv, { type: 'string', raw: true, dense: true });
const raw = sheetRows(wbCsv, wbCsv.SheetNames[0]);
const t = toTable(raw, detectHeaderRow(raw));
const map = autoMap(t).map;
eq('auto-mapped date column', map.date, 'Invoice date');
eq('auto-mapped IGST column', map.igst, 'Integrated Tax');
const imp = importWorkbook(wbCsv, 'g2b', map, { allSheets: false, sheet: wbCsv.SheetNames[0] });
eq('CSV dates stay day-first', imp.main.map((r) => r.date), ['04/10/2025', '13/10/2025']);
/* ---------------- Tally export: supplier invoice no., not voucher no. ---------------- */
const tally = [
  'Date,Particulars,GSTIN/UIN,Voucher No.,Supplier Invoice No.,Taxable Value,Integrated Tax Amount,Central Tax Amount,State Tax Amount',
  '04-10-2026,Tata Consultancy Services Ltd,27AAACT2727Q1ZW,P-001,INV/2026/101,"1,50,000",0,"13,500","13,500"',
  ',Grand Total,,,,,,,',
].join('\n');
const wbT = XLSX.read(tally, { type: 'string', raw: true, dense: true });
const rawT = sheetRows(wbT, wbT.SheetNames[0]);
const mapT = autoMap(toTable(rawT, detectHeaderRow(rawT))).map;
eq('Tally mapping', [mapT.inv, mapT.name, mapT.gstin, mapT.date], ['Supplier Invoice No.', 'Particulars', 'GSTIN/UIN', 'Date']);
const impT = importWorkbook(wbT, 'bks', mapT, { allSheets: false, sheet: wbT.SheetNames[0] });
eq('Tally row (lakh commas, dd-mm-yyyy, total row skipped)', impT.main.map((r) => [r.inv, r.date, r.taxable, r.cgst]), [['INV/2026/101', '04/10/2026', 150000, 13500]]);

/* ---------------- Official GSTR-2B Excel layout (two heading rows) ---------------- */
const SAMPLE_2B = 'D:/Level 2/Day 5/gstr-2b-recon/sample-uploads/gstr2b-sample.xlsx';
if (fs.existsSync(SAMPLE_2B)) {
  const wb2b = XLSX.read(fs.readFileSync(SAMPLE_2B), { type: 'buffer', raw: true, dense: true });
  const raw2b = sheetRows(wb2b, 'B2B');
  const map2b = autoMap(toTable(raw2b, detectHeaderRow(raw2b))).map;
  eq('GSTR-2B mapping', [map2b.gstin, map2b.name, map2b.inv, map2b.date, map2b.igst, map2b.cgst, map2b.sgst, map2b.rcm], [
    'GSTIN of supplier',
    'Trade/Legal name',
    'Invoice number',
    'Invoice Date',
    'Integrated Tax(₹)',
    'Central Tax(₹)',
    'State/UT Tax(₹)',
    'Supply Attract Reverse Charge',
  ]);
  const imp2b = importWorkbook(wb2b, 'g2b', map2b, { allSheets: true, sheet: 'B2B' });
  eq('GSTR-2B first invoice', [imp2b.main[0]?.inv, imp2b.main[0]?.date, imp2b.main[0]?.cgst], ['INV/2026/101', '04/10/2026', 13500]);
  eq('GSTR-2B CDNR sheet kept apart', imp2b.cdn.map((r) => r.inv), ['CN-1']);
  console.log(`     GSTR-2B sample: ${imp2b.main.length} invoices, ${imp2b.cdn.length} notes, ${imp2b.excluded.length} excluded`);
}

/* ---------------- Excel date cells ---------------- */
// Excel's default short date (number format 14) shows as dd-mm-yyyy on Indian Windows,
// but the spreadsheet library renders it as m/d/yy. The AI Studio import kept that text,
// so 4 October showed as "10/4/26" and its month report read the middle part as the month.
for (const fmt of ['m/d/yy', 'dd/mm/yyyy']) {
  const wbX = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([
    ['GSTIN', 'Name', 'Invoice No', 'Invoice Date', 'Taxable Value', 'IGST', 'CGST', 'SGST'],
    ['27AAPFU0939F1ZV', 'Sunrise Traders', 'A1', 46299, 100, 18, 0, 0],
  ]);
  ws['D2'].t = 'n';
  ws['D2'].z = fmt;
  XLSX.utils.book_append_sheet(wbX, ws, 'B2B');
  const xbuf = XLSX.write(wbX, { type: 'array', bookType: 'xlsx' });
  const impX = importWorkbook(XLSX.read(xbuf, { type: 'array', raw: true, cellDates: false, dense: true }), 'g2b', {}, { allSheets: true, sheet: 'B2B' });
  eq(`Excel date cell (format ${fmt})`, impX.main[0]?.date, '04/10/2026');
  if (fmt === 'm/d/yy') {
    const oldText = XLSX.utils.sheet_to_json<string[]>(XLSX.read(xbuf, { type: 'array', cellDates: true }).Sheets.B2B, { header: 1, raw: false })[1][3];
    console.log(`     AI Studio read this 4 October 2026 cell as "${oldText}" (shown as-is, and put under April in the month report)`);
  }
}

/* ---------------- Split lines are added, rows without GSTIN excluded ---------------- */
const wbS = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(
  wbS,
  XLSX.utils.aoa_to_sheet([
    ['GSTIN', 'Party Name', 'Bill No', 'Bill Date', 'Taxable', 'IGST', 'CGST', 'SGST'],
    ['27AAPFU0939F1ZV', 'Sunrise Traders', '91', '04/10/2025', 60000, 0, 5400, 5400],
    ['27AAPFU0939F1ZV', 'Sunrise Traders', '91', '04/10/2025', 40000, 0, 3600, 3600],
    ['', 'Cash purchase', 'C-1', '05/10/2025', 500, 0, 45, 45],
  ]),
  'Purchase'
);
const impS = importWorkbook(XLSX.read(XLSX.write(wbS, { type: 'array', bookType: 'xlsx' }), { type: 'array', raw: true }), 'bks', {}, { allSheets: false, sheet: 'Purchase' });
eq('split lines summed', impS.main.map((r) => [r.inv, r.taxable, r.cgst]), [['91', 100000, 9000]]);
eq('row without GSTIN excluded', impS.excluded.map((r) => r.reason), ['GSTIN missing']);

/* ---------------- Invoice numbers ---------------- */
eq('invKey FY and zeros', invKey('st/2025-26/0091'), 'ST/25-26/91');
eq('core: FY tag removed', invCore('TAX-2024-25/0091'), '91');
eq('core: prefix removed', invCore('INV/91'), '91');
eq('core: plain', invCore('0091'), '91');
eq('core: keeps non-FY numbers', invCore('BC-1182'), '1182');

/* ---------------- Each invoice counted once ---------------- */
const R = (p: Partial<Row>): Row => ({ gstin: '27AAPFU0939F1ZV', name: 'Sunrise Traders', inv: '', date: '04/10/2025', taxable: 0, igst: 0, cgst: 0, sgst: 0, total: 0, source: 'g2b', rowNum: 2, sheet: 'B2B', ...p });
const empty = { g2b: [], g2b_cdn: [], g2b_excl: [], bks: [], bks_cdn: [], bks_excl: [], cdn_g2b: [], cdn_bks: [], rcm: [] };
const ds: Datasets = {
  ...empty,
  g2b: [
    R({ inv: 'ST/2025-26/0091', taxable: 100000, cgst: 9000, sgst: 9000 }), // smart pass 1 with "91"
    R({ inv: 'X-1', taxable: 5000, igst: 900 }), // exact
    R({ inv: 'Y-1', taxable: 5000, igst: 900 }), // within tolerance (books 950)
    R({ inv: 'Z-1', taxable: 9999, igst: 1800 }), // only in 2B
    R({ gstin: '29AAGCB1286Q1Z0', inv: 'ACME-402', taxable: 2000, igst: 360, date: '10/10/2025' }), // pass 2 amount + date
  ],
  bks: [
    R({ source: 'bks', inv: '91', taxable: 100000, cgst: 9000, sgst: 9000 }),
    R({ source: 'bks', inv: 'X-1', taxable: 5000, igst: 900 }),
    R({ source: 'bks', inv: 'Y-1', taxable: 5000, igst: 950 }),
    R({ source: 'bks', inv: 'W-9', taxable: 3000, igst: 540 }), // only in books
    R({ source: 'bks', gstin: '29AAGCB1286Q1Z0', inv: 'AC/BILL', taxable: 2000, igst: 360, date: '10/10/2025' }),
  ],
};
const rc = runAll(ds, 100, []);
eq('final counts', rc.counts, { exact: 1, tol: 1, mismatch: 0, smart: 2, missBooks: 1, miss2b: 1, total: 6 });
eq('smart passes used', rc.smart.filter((s) => !s.s.startsWith('sm')).map((s) => s.s).sort(), ['ad', 'cm']);
eq('lines = 2B + books - pairs', rc.lines.length, ds.g2b.length + ds.bks.length - 4);
const sumSmart = rc.lines.filter((l) => l.status === 'smart').length;
const sumMissing = rc.lines.filter((l) => l.status === 'missBooks' || l.status === 'miss2b').length;
eq('smart-matched invoices are not also missing', sumSmart + sumMissing, 4);
eq('Table 4(A)(5) = matched only', Math.round(rc.t4.eligible.igst + rc.t4.eligible.cgst + rc.t4.eligible.sgst), 1800);

/* ---------------- Section 16(4) uses dd/mm ---------------- */
// 04/10/2024 is in FY 2024-25: last date 30/11/2025. On 30/10/2026 it is past; 10/04/2025 (FY 2025-26) is not.
const tb = timeBarred([R({ inv: 'A', date: '04/10/2024' }), R({ inv: 'B', date: '10/04/2025' })], new Date(2026, 9, 30));
eq('16(4) time-barred', tb.map((r) => [r.inv, r.fy, r.deadline]), [['A', '2024-25', '30/11/2025']]);

/* ---------------- GSTIN check digit ---------------- */
eq('valid GSTIN', checkGstin('27AAPFU0939F1ZV').valid, true);
eq('wrong check digit', checkGstin('27AAPFU0939F1ZX').valid, false);
eq('bad state code', checkGstin('45AAPFU0939F1ZV').valid, false);

console.log(`\n${passed} passed, ${failed} failed`);
if (failed) process.exit(1);
