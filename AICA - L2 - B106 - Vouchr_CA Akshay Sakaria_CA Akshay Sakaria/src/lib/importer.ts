// Bulk Excel import: one downloadable template per master, a forgiving reader for .xlsx / .csv, and cell clean-up.
// Business rules are NOT here — the store's importData() checks every row exactly like a manual entry would be checked.
// Libraries: read-excel-file / write-excel-file (MIT, no network, run in the browser). SheetJS from npm (0.18.5)
// is avoided on purpose: that npm build is outdated with published security advisories.

import type { Client } from '../data/types';
import type { ImportKind, ImportRow } from '../data/store';
import { parseDate } from './extract';
import { todayIso } from './dates';
import { gstinCheckChar } from './validators';

export type ColType = 'text' | 'number' | 'date';
export interface ImportColumn {
  key: string;
  header: string; // English heading in the template (matching ignores case, spaces and the * mark)
  required?: boolean;
  type?: ColType;
  en: string; // what to fill — shown on the Instructions sheet in both languages
  hi: string;
  aliases?: string[]; // other headings people commonly use (Tally / Busy / bank exports)
}

export interface ImportDataset {
  kind: ImportKind;
  title: string; // English, translated in the UI via tr()
  blurb: string;
  file: string;
  columns: ImportColumn[];
  examples: (c: Client) => (string | number | Date | undefined)[][];
}

const daysAgo = (n: number) => { const d = new Date(`${todayIso()}T00:00:00`); d.setDate(d.getDate() - n); return d; };
const gst = (first14: string) => first14 + gstinCheckChar(first14);

export const DATASETS: ImportDataset[] = [
  {
    kind: 'vendors', title: 'Vendors', file: 'Vouchr-vendors-template.xlsx',
    blurb: 'Your supplier list with GSTIN, PAN and credit days.',
    columns: [
      { key: 'name', header: 'Vendor name', required: true, en: 'Name as on the bill', hi: 'बिल पर लिखा नाम', aliases: ['party name', 'supplier name', 'name', 'ledger name'] },
      { key: 'gstin', header: 'GSTIN', en: '15 characters; leave blank if not registered', hi: '15 अक्षर; रजिस्टर्ड नहीं तो खाली छोड़ें', aliases: ['gst no', 'gst number', 'gstin uin'] },
      { key: 'pan', header: 'PAN', en: '10 characters; filled from GSTIN if blank', hi: '10 अक्षर; खाली हो तो GSTIN से लिया जाएगा', aliases: ['pan no', 'it pan'] },
      { key: 'creditDays', header: 'Credit days', type: 'number', en: 'Days allowed to pay (0–365); blank = client default', hi: 'भुगतान के लिए दिन (0–365); खाली = क्लाइंट डिफ़ॉल्ट', aliases: ['credit period', 'payment terms'] },
      { key: 'tallyLedger', header: 'Tally ledger name', en: 'Only if the Tally ledger name differs from the vendor name', hi: 'केवल तब, जब Tally लेजर का नाम अलग हो' }
    ],
    examples: () => [
      ['Sharma Office Supplies (sample)', gst('27AAKFS4821M1Z'), '', 30, ''],
      ['Ravi Electricals (sample)', '', 'ABHPR4821K', 15, '']
    ]
  },
  {
    kind: 'bills', title: 'Old / opening bills', file: 'Vouchr-bills-template.xlsx',
    blurb: 'Bills from before you started Vouchr, or a purchase register from Tally / Busy. They go to the CA review queue.',
    columns: [
      { key: 'vendor', header: 'Vendor name', required: true, en: 'New names are added to the vendor list', hi: 'नया नाम विक्रेता सूची में जुड़ जाएगा', aliases: ['party name', 'supplier name', 'particulars', 'party'] },
      { key: 'gstin', header: 'Vendor GSTIN', en: 'Leave blank if not registered', hi: 'रजिस्टर्ड नहीं तो खाली छोड़ें', aliases: ['gstin', 'gstin uin', 'gst no'] },
      { key: 'invoiceNo', header: 'Bill no.', en: "Vendor's invoice number", hi: 'विक्रेता का बिल नंबर', aliases: ['invoice no', 'invoice number', 'supplier invoice no', 'bill number', 'voucher no'] },
      { key: 'invoiceDate', header: 'Bill date', required: true, type: 'date', en: 'dd-mm-yyyy', hi: 'दिन-महीना-साल (dd-mm-yyyy)', aliases: ['invoice date', 'date', 'supplier invoice date'] },
      { key: 'taxable', header: 'Taxable value', required: true, type: 'number', en: 'Amount before GST, after discount', hi: 'GST से पहले की राशि, छूट के बाद', aliases: ['taxable amount', 'assessable value', 'value'] },
      { key: 'cgst', header: 'CGST', type: 'number', en: 'Amount in ₹ (same state)', hi: 'राशि ₹ में (राज्य के अंदर)', aliases: ['central tax', 'cgst amount'] },
      { key: 'sgst', header: 'SGST', type: 'number', en: 'Amount in ₹ (same state)', hi: 'राशि ₹ में (राज्य के अंदर)', aliases: ['state tax', 'sgst amount', 'sgst utgst', 'utgst'] },
      { key: 'igst', header: 'IGST', type: 'number', en: 'Amount in ₹ (other state)', hi: 'राशि ₹ में (दूसरा राज्य)', aliases: ['integrated tax', 'igst amount'] },
      { key: 'total', header: 'Bill total', type: 'number', en: 'Optional check — must equal taxable + GST (±₹1)', hi: 'वैकल्पिक जाँच — टैक्सेबल + GST के बराबर (±₹1)', aliases: ['invoice value', 'total', 'gross total', 'amount'] },
      { key: 'discount', header: 'Discount', type: 'number', en: 'Only if shown on the bill', hi: 'केवल अगर बिल पर दिखी हो' },
      { key: 'hsn', header: 'HSN / SAC', en: '4–8 digits', hi: '4–8 अंक', aliases: ['hsn', 'sac', 'hsn sac', 'hsn code'] },
      { key: 'description', header: 'What was it for', en: 'Required above the client limit for notes', hi: 'क्लाइंट की नोट-सीमा से ऊपर ज़रूरी', aliases: ['description', 'item', 'details', 'narration short'] },
      { key: 'centre', header: 'Project / branch', en: 'Must match a project / branch already set up', hi: 'पहले से बने प्रोजेक्ट / शाखा से मेल खाए', aliases: ['cost centre', 'cost center', 'branch', 'project'] },
      { key: 'narration', header: 'Narration', en: 'Goes into the Tally voucher', hi: 'Tally वाउचर में जाएगा' },
      { key: 'nonTaxable', header: 'Non-GST charges', type: 'number', en: 'Part of the total outside this bill’s GST, as printed (e.g. air/rail fare collected on behalf of the airline/IRCTC)', hi: 'कुल में से वह हिस्सा जिस पर इस बिल में GST नहीं, जैसा छपा है (जैसे एयरलाइन/IRCTC की ओर से लिया गया किराया)', aliases: ['non taxable', 'reimbursement', 'fare charges', 'pass through'] },
      { key: 'eco', header: 'GST paid by app (9(5))', en: 'Y if Zomato / Swiggy / Uber / Ola etc. paid the GST under section 9(5)', hi: 'Y, यदि Zomato / Swiggy / Uber / Ola आदि ने धारा 9(5) में GST भरा', aliases: ['eco', '9(5)', 'section 9(5)'] },
      { key: 'ecoGstin', header: 'App / operator GSTIN', en: 'GSTIN of the e-commerce operator, if printed', hi: 'ई-कॉमर्स ऑपरेटर का GSTIN, यदि छपा हो', aliases: ['eco gstin', 'operator gstin'] }
    ],
    examples: (c) => [
      ['Sharma Office Supplies (sample)', gst('27AAKFS4821M1Z'), 'SOS/245', daysAgo(12), 10000, 900, 900, 0, 11800, 0, '4802', 'A4 paper, 20 reams', c.costCentres.find((x) => x.active)?.name ?? '', '', 0, '', ''],
      ['Ravi Electricals (sample)', '', 'RE-88', daysAgo(5), 2500, 0, 0, 0, 2500, 0, '9987', 'Ceiling fan repair', '', 'Office fan repair', 0, '', ''],
      // travel portal: GST only on its fee; the fare is collected for the airline (non-GST on this bill)
      ['Sample Travel Portal (sample)', gst('06AAKCS4821M1Z'), 'TP/0001', daysAgo(20), 135.59, 12.2, 12.2, 0, 2875, 0, '998551', 'Air ticket PNQ-AMD', '', '', 2715, '', ''],
      // food app order: GST paid by the app under section 9(5)
      ['Sample Food App (sample)', gst('29AAKCF4821M1Z'), 'FA-1001', daysAgo(8), 729.8, 18.25, 18.25, 0, 766, 0, '996331', 'Team lunch', '', '', 0, 'Y', gst('29AAKCF4821M1Z')]
    ]
  },
  {
    kind: 'payments', title: 'Payments made', file: 'Vouchr-payments-template.xlsx',
    blurb: 'Payments already made to vendors. Applied to the bill number given, or to the oldest unpaid bills; any extra is kept as an advance.',
    columns: [
      { key: 'vendor', header: 'Vendor name', required: true, en: 'Must already be in the vendor list', hi: 'विक्रेता सूची में पहले से होना चाहिए', aliases: ['party name', 'paid to', 'party', 'particulars'] },
      { key: 'amount', header: 'Amount', required: true, type: 'number', en: 'Amount paid in ₹', hi: 'भुगतान की राशि ₹ में', aliases: ['amount paid', 'debit', 'paid amount'] },
      { key: 'paidOn', header: 'Paid on', required: true, type: 'date', en: 'dd-mm-yyyy', hi: 'दिन-महीना-साल (dd-mm-yyyy)', aliases: ['date', 'payment date', 'value date'] },
      { key: 'mode', header: 'Mode', required: true, en: 'Cash, UPI, Bank (NEFT/RTGS/IMPS), Cheque or Card', hi: 'नकद, UPI, बैंक (NEFT/RTGS/IMPS), चेक या कार्ड', aliases: ['payment mode', 'paid by', 'mode of payment'] },
      { key: 'source', header: 'Paid from', en: 'Name of the bank / UPI / card / cash box as set up in Vouchr', hi: 'Vouchr में बने बैंक / UPI / कार्ड / कैश बॉक्स का नाम', aliases: ['bank', 'account', 'paid from account'] },
      { key: 'ref', header: 'Reference', en: 'UTR, cheque no. or UPI transaction ID', hi: 'UTR, चेक नंबर या UPI ट्रांज़ैक्शन ID', aliases: ['utr', 'cheque no', 'ref no', 'transaction id'] },
      { key: 'billNo', header: 'Against bill no.', en: 'Blank = oldest unpaid bills first', hi: 'खाली = सबसे पुराने बकाया बिल पहले', aliases: ['bill no', 'invoice no', 'against invoice'] }
    ],
    examples: (c) => [
      ['Sharma Office Supplies (sample)', 5000, daysAgo(3), 'NEFT', c.bankAccounts.find((a) => a.kind === 'bank' && a.active !== false)?.name ?? '', 'UTR0001234', 'SOS/245'],
      ['Ravi Electricals (sample)', 2500, daysAgo(2), 'Cash', c.bankAccounts.find((a) => a.kind === 'cash' && a.active !== false)?.name ?? '', '', 'RE-88']
    ]
  },
  {
    kind: 'centres', title: 'Projects & branches', file: 'Vouchr-projects-branches-template.xlsx',
    blurb: 'Cost centres used to tag expenses.',
    columns: [
      { key: 'kind', header: 'Type', required: true, en: 'Project or Branch', hi: 'प्रोजेक्ट या शाखा', aliases: ['category'] },
      { key: 'name', header: 'Name', required: true, en: 'e.g. Nashik Branch', hi: 'जैसे नासिक शाखा', aliases: ['cost centre', 'cost center', 'project name', 'branch name'] }
    ],
    examples: () => [['Project', 'Pune office fit-out (sample)'], ['Branch', 'Nagpur branch (sample)']]
  },
  {
    kind: 'sources', title: 'Payment sources', file: 'Vouchr-payment-sources-template.xlsx',
    blurb: 'Bank accounts, UPI IDs, company cards and cash boxes. List bank accounts above the UPI IDs that debit them.',
    columns: [
      { key: 'kind', header: 'Type', required: true, en: 'Bank, UPI, Card or Cash', hi: 'बैंक, UPI, कार्ड या नकद', aliases: ['category'] },
      { key: 'name', header: 'Name', required: true, en: 'As your staff will see it, e.g. HDFC Current ••4521', hi: 'जैसा स्टाफ़ को दिखेगा, जैसे HDFC Current ••4521', aliases: ['account name'] },
      { key: 'upiId', header: 'UPI ID', en: 'Required for UPI, e.g. shop@okhdfc', hi: 'UPI के लिए ज़रूरी, जैसे shop@okhdfc', aliases: ['vpa'] },
      { key: 'linkedBank', header: 'Linked bank account', en: 'For UPI: name of the bank account it debits', hi: 'UPI के लिए: जिस बैंक खाते से पैसा कटता है उसका नाम' },
      { key: 'tallyLedger', header: 'Tally ledger name', en: 'Required unless taken from the linked bank', hi: 'ज़रूरी, जब तक लिंक्ड बैंक से न लिया जाए', aliases: ['ledger', 'tally ledger'] }
    ],
    examples: () => [
      ['Bank', 'ICICI Current ••7788 (sample)', '', '', 'ICICI Bank'],
      ['UPI', 'PhonePe · office (sample)', 'office@ybl', 'ICICI Current ••7788 (sample)', ''],
      ['Cash', 'Petty cash — Site (sample)', '', '', 'Cash']
    ]
  }
];

export const datasetOf = (k: ImportKind) => DATASETS.find((d) => d.kind === k)!;

const norm = (h: string) => h.toLowerCase().replace(/\*/g, '').replace(/[^a-z0-9]+/g, ' ').trim();

/** Excel template: a Data sheet (headings + two sample rows tailored to this client) and a bilingual Instructions sheet. */
export async function downloadTemplate(ds: ImportDataset, client: Client) {
  const { default: writeXlsxFile } = await import('write-excel-file/browser');
  const head = ds.columns.map((c) => ({
    value: c.required ? `${c.header} *` : c.header, fontWeight: 'bold' as const,
    backgroundColor: c.required ? '#FDECEA' : '#EEF2F7', borderColor: '#D3CDC0', borderStyle: 'thin' as const
  }));
  const rows = ds.examples(client).map((r) => r.map((v, i) =>
    v instanceof Date ? { value: v, type: Date, format: 'dd-mm-yyyy' }
      : ds.columns[i].type === 'number' && typeof v === 'number' ? { value: v, type: Number }
      : { value: v === undefined ? '' : String(v), type: String }));
  const info = [
    [{ value: 'Column', fontWeight: 'bold' as const }, { value: 'Required', fontWeight: 'bold' as const }, { value: 'What to fill', fontWeight: 'bold' as const }, { value: 'क्या भरें', fontWeight: 'bold' as const }],
    ...ds.columns.map((c) => [{ value: c.header }, { value: c.required ? 'Yes / हाँ *' : 'No / नहीं' }, { value: c.en }, { value: c.hi }]),
    [],
    [{ value: 'Delete the sample rows before importing. Keep the headings in row 1. Max 2,000 rows per file.' }],
    [{ value: 'आयात से पहले नमूना पंक्तियाँ हटा दें। पहली पंक्ति के शीर्षक न बदलें। एक फ़ाइल में अधिकतम 2,000 पंक्तियाँ।' }]
  ];
  await writeXlsxFile([
    { sheet: 'Data', data: [head, ...rows], columns: ds.columns.map((c) => ({ width: Math.max(14, c.header.length + 6) })), stickyRowsCount: 1 },
    { sheet: 'Instructions', data: info, columns: [{ width: 22 }, { width: 14 }, { width: 58 }, { width: 58 }] }
  ]).toFile(ds.file);
}

type Cell = string | number | boolean | Date | null | undefined;

/** Minimal RFC-4180 CSV reader (quoted fields, doubled quotes, CRLF), for people who save the template as CSV. */
export function parseCsv(text: string): string[][] {
  const out: string[][] = [];
  let row: string[] = [], cur = '', q = false;
  const t = text.replace(/^﻿/, '');
  for (let i = 0; i < t.length; i++) {
    const ch = t[i];
    if (q) {
      if (ch === '"' && t[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch;
    } else if (ch === '"') q = true;
    else if (ch === ',') { row.push(cur); cur = ''; }
    else if (ch === '\n' || ch === '\r') { if (ch === '\r' && t[i + 1] === '\n') i++; row.push(cur); out.push(row); row = []; cur = ''; }
    else cur += ch;
  }
  if (cur || row.length) { row.push(cur); out.push(row); }
  return out;
}

export async function readGrid(file: File): Promise<Cell[][]> {
  if (/\.csv$/i.test(file.name) || file.type === 'text/csv') return parseCsv(await file.text());
  const { readSheet } = await import('read-excel-file/browser');
  return (await readSheet(file)) as Cell[][];
}

function toDate(v: Cell): string | undefined {
  if (v instanceof Date) return `${v.getUTCFullYear()}-${String(v.getUTCMonth() + 1).padStart(2, '0')}-${String(v.getUTCDate()).padStart(2, '0')}`;
  if (typeof v === 'number' && v > 20000 && v < 80000) return toDate(new Date(Date.UTC(1899, 11, 30) + Math.round(v) * 86400000)); // Excel serial date
  return typeof v === 'string' ? parseDate(v) : undefined;
}

function toNumber(v: Cell): number | undefined {
  if (typeof v === 'number') return v;
  if (typeof v !== 'string') return undefined;
  const t = v.replace(/[₹,\s]|rs\.?|inr/gi, '');
  if (/^\(.*\)$/.test(t)) return -Number(t.slice(1, -1)); // accounting negatives (1,000)
  return t && /^-?\d*\.?\d+$/.test(t) ? Number(t) : undefined;
}

export interface ParsedFile {
  rows: ImportRow[];
  /** Rows whose cells could not be read (bad date / number) — shown as failed without reaching the store. */
  cellErrors: { row: number; message: string; vars: Record<string, string | number> }[];
  missing: string[]; // required headings not found
  unknown: string[]; // headings that were ignored
}

/** Maps headings → template keys (by heading or alias) and cleans every cell by its column type. */
export function mapGrid(ds: ImportDataset, grid: Cell[][]): ParsedFile {
  const empty = (c: Cell) => c === null || c === undefined || (typeof c === 'string' && !c.trim());
  const headIdx = grid.findIndex((r) => r.some((c) => !empty(c)));
  if (headIdx < 0) return { rows: [], cellErrors: [], missing: ds.columns.filter((c) => c.required).map((c) => c.header), unknown: [] };
  const heads = grid[headIdx].map((c) => norm(String(c ?? '')));
  const colOf = new Map<string, number>();
  const unknown: string[] = [];
  heads.forEach((h, i) => {
    if (!h) return;
    const col = ds.columns.find((c) => norm(c.header) === h || c.aliases?.some((a) => norm(a) === h));
    if (col && !colOf.has(col.key)) colOf.set(col.key, i); else unknown.push(String(grid[headIdx][i]));
  });
  const missing = ds.columns.filter((c) => c.required && !colOf.has(c.key)).map((c) => c.header);
  const rows: ImportRow[] = [];
  const cellErrors: ParsedFile['cellErrors'] = [];
  grid.slice(headIdx + 1, headIdx + 1 + 2000).forEach((r, i) => {
    const rowNo = headIdx + i + 2;
    if (r.every(empty)) return;
    const out: ImportRow = { _row: rowNo };
    for (const c of ds.columns) {
      const idx = colOf.get(c.key);
      const raw = idx === undefined ? undefined : r[idx];
      if (empty(raw)) continue;
      if (c.type === 'date') {
        const d = toDate(raw);
        if (!d) { cellErrors.push({ row: rowNo, message: '{col}: "{value}" is not a date (use dd-mm-yyyy)', vars: { col: c.header, value: String(raw) } }); return; }
        out[c.key] = d;
      } else if (c.type === 'number') {
        const n = toNumber(raw);
        if (n === undefined) { cellErrors.push({ row: rowNo, message: '{col}: "{value}" is not a number', vars: { col: c.header, value: String(raw) } }); return; }
        out[c.key] = n;
      } else out[c.key] = raw instanceof Date ? toDate(raw) : String(raw).trim();
    }
    rows.push(out);
  });
  return { rows, cellErrors, missing, unknown };
}
