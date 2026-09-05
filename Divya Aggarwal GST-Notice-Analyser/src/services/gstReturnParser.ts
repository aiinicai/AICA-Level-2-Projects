import * as XLSX from 'xlsx';
import { GstDocType, ParsedFigure, TaxHead } from '../types';

// ── Document-type detection ──────────────────────────────────────────────────
const DOC_MARKERS: { type: GstDocType; re: RegExp }[] = [
  { type: 'GSTR-9C', re: /gstr[\s-]?9c|reconciliation statement/i },
  { type: 'GSTR-9', re: /gstr[\s-]?9\b|annual return/i },
  { type: 'GSTR-3B', re: /gstr[\s-]?3b/i },
  { type: 'GSTR-2B', re: /gstr[\s-]?2b|auto[\s-]?drafted itc/i },
  { type: 'GSTR-2A', re: /gstr[\s-]?2a/i },
  { type: 'GSTR-1', re: /gstr[\s-]?1\b/i },
  { type: 'CASH_LEDGER', re: /electronic cash ledger|cash ledger/i },
  { type: 'CREDIT_LEDGER', re: /electronic credit ledger|credit ledger/i },
  { type: 'COMPARISON', re: /comparison of (liability|tax)|liability (declared|paid).*itc|tax liabilities and itc/i },
  { type: 'BOOKS', re: /trial balance|books of account|profit (and|&) loss|p&l/i },
];

// ── Figure rules: friendly label ← row-text patterns ─────────────────────────
interface Rule { label: string; re: RegExp; docTypes?: GstDocType[] }

const RULES: Rule[] = [
  // GSTR-3B
  { label: 'GSTR-3B 3.1(a) — Outward taxable value', re: /3\.1\s*\(?a\)?|outward taxable supplies \(other than zero/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 3.1(d) — Inward supplies liable to RCM', re: /3\.1\s*\(?d\)?|inward supplies.*reverse charge/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 4(A)(5) — All other ITC availed', re: /4\s*\(?a\)?\s*\(?5\)?|all other itc/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 4(B) — ITC reversed', re: /4\s*\(?b\)?|itc reversed/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 4(C) — Net ITC available', re: /4\s*\(?c\)?|net itc available/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 5.1 — Interest', re: /\b5\.1\b|interest.*(late fee|payable)/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 6.1 — Tax paid in cash', re: /paid (in|through) cash|tax paid.*cash/i, docTypes: ['GSTR-3B', 'OTHER'] },
  { label: 'GSTR-3B 6.1 — Tax paid through ITC', re: /paid (through|by) itc|tax paid.*itc/i, docTypes: ['GSTR-3B', 'OTHER'] },

  // GSTR-1
  { label: 'GSTR-1 — Total outward taxable value', re: /total.*outward|total taxable value|total invoice value|total liability/i, docTypes: ['GSTR-1'] },

  // GSTR-2B
  { label: 'GSTR-2B — ITC available (Table 3 / Part A)', re: /itc available|table 3|part a.*itc|itc.*may be availed/i, docTypes: ['GSTR-2B', 'GSTR-2A'] },
  { label: 'GSTR-2B — ITC not available (Table 4)', re: /itc not available|table 4.*itc|ineligible itc/i, docTypes: ['GSTR-2B'] },

  // GSTR-9
  { label: 'GSTR-9 Table 4 — Outward taxable value', re: /table 4\b|4n\b|outward supplies on which tax is payable/i, docTypes: ['GSTR-9'] },
  { label: 'GSTR-9 Table 6 — ITC availed', re: /table 6\b|6o\b|total itc availed/i, docTypes: ['GSTR-9'] },
  { label: 'GSTR-9 Table 7 — ITC reversed', re: /table 7\b|7j\b|total itc reversed/i, docTypes: ['GSTR-9'] },
  { label: 'GSTR-9 Table 9 — Tax paid', re: /table 9\b|tax payable|tax paid.*annual/i, docTypes: ['GSTR-9'] },
  { label: 'GSTR-9 Table 8D — ITC difference', re: /8d\b|difference.*itc.*2a/i, docTypes: ['GSTR-9'] },

  // GSTR-9C
  { label: 'GSTR-9C — Turnover as per books', re: /turnover as per (audited|books).*(financial|annual)/i, docTypes: ['GSTR-9C'] },
  { label: 'GSTR-9C — Unreconciled turnover', re: /un[\s-]?reconciled turnover/i, docTypes: ['GSTR-9C'] },
  { label: 'GSTR-9C — Unreconciled ITC', re: /un[\s-]?reconciled.*itc/i, docTypes: ['GSTR-9C'] },
  { label: 'GSTR-9C — Additional tax payable', re: /additional.*tax.*(payable|liability)/i, docTypes: ['GSTR-9C'] },

  // Ledgers
  { label: 'Electronic Cash Ledger — closing balance', re: /closing balance|balance available|cash.*balance/i, docTypes: ['CASH_LEDGER'] },
  { label: 'Electronic Credit Ledger — closing balance', re: /closing balance|balance available|credit.*balance/i, docTypes: ['CREDIT_LEDGER'] },

  // Comparison statement
  { label: 'Comparison — Tax liability declared (GSTR-1)', re: /liability.*(declared|gstr[\s-]?1)/i, docTypes: ['COMPARISON'] },
  { label: 'Comparison — Tax paid (GSTR-3B)', re: /tax paid.*(3b|cash|declared)/i, docTypes: ['COMPARISON'] },
  { label: 'Comparison — ITC as per GSTR-2A/2B', re: /itc.*(2a|2b).*(accrued|available)|itc as per (auto|2)/i, docTypes: ['COMPARISON'] },
  { label: 'Comparison — ITC claimed (GSTR-3B)', re: /itc (claimed|availed).*3b|itc.*table 4/i, docTypes: ['COMPARISON'] },
  { label: 'Comparison — Difference', re: /difference|excess|short/i, docTypes: ['COMPARISON'] },

  // Books
  { label: 'Books — Turnover / Sales', re: /(gross|net) (sales|turnover|revenue)|sales account/i, docTypes: ['BOOKS'] },
  { label: 'Books — Purchases', re: /purchase(s)? account|total purchases/i, docTypes: ['BOOKS'] },
  { label: 'Books — Input tax / ITC ledger', re: /input (cgst|sgst|igst|tax)|itc receivable/i, docTypes: ['BOOKS'] },
];

const HEAD_RE: { head: TaxHead; re: RegExp }[] = [
  { head: 'IGST', re: /\bigst\b/i },
  { head: 'CGST', re: /\bcgst\b/i },
  { head: 'SGST', re: /\b(s|ut)gst\b/i },
  { head: 'CESS', re: /\bcess\b/i },
];

const toNum = (v: any): number => {
  if (typeof v === 'number') return isFinite(v) ? v : 0;
  const n = parseFloat(String(v ?? '').replace(/[^0-9.\-]/g, ''));
  return isNaN(n) ? 0 : n;
};

function guessDocType(allText: string, fileName: string): GstDocType {
  const hay = `${fileName}\n${allText}`;
  for (const m of DOC_MARKERS) if (m.re.test(hay)) return m.type;
  return 'OTHER';
}

/**
 * Parse an uploaded GST portal export (.xlsx/.xls/.csv). Scans every sheet for
 * rows whose text matches a known GST label and pulls the numeric value(s) in
 * that row, tagged by tax head where detectable. Heuristic — the CA verifies.
 */
export async function parseGstReturnFile(file: File): Promise<ParsedFigure[]> {
  const buf = await file.arrayBuffer();
  const wb = XLSX.read(buf, { type: 'array' });

  const allRows: any[][] = [];
  for (const name of wb.SheetNames) {
    const rows = XLSX.utils.sheet_to_json<any[]>(wb.Sheets[name], { header: 1, blankrows: false });
    allRows.push(...rows.filter(Array.isArray));
  }

  const allText = allRows.map((r) => r.map((c) => String(c ?? '')).join(' ')).join('\n');
  const docType = guessDocType(allText, file.name);

  // Build a column → tax-head map from any header row that names the heads.
  const colHead = new Map<number, TaxHead>();
  allRows.forEach((row) => {
    const hits = row
      .map((c, i) => ({ i, h: HEAD_RE.find((x) => x.re.test(String(c || '')))?.head }))
      .filter((x) => x.h) as { i: number; h: TaxHead }[];
    if (hits.length >= 2) hits.forEach(({ i, h }) => { if (!colHead.has(i)) colHead.set(i, h); });
    // "Total" / "amount" column
    row.forEach((c, i) => {
      if (!colHead.has(i) && /\b(total|amount|value)\b/i.test(String(c || ''))) colHead.set(i, /value/i.test(String(c)) ? 'VALUE' : 'TOTAL');
    });
  });

  const out: ParsedFigure[] = [];
  const seen = new Set<string>();

  allRows.forEach((row) => {
    const cells = row.map((c) => (c == null ? '' : c));
    const rowText = cells.map((c) => String(c)).join(' ').toLowerCase();
    if (!rowText.trim()) return;

    const rule = RULES.find(
      (r) => r.re.test(rowText) && (!r.docTypes || r.docTypes.includes(docType) || docType === 'OTHER'),
    );
    if (!rule) return;

    const nums = cells
      .map((c, i) => ({ i, n: toNum(c), raw: String(c) }))
      .filter((x) => x.n !== 0 && /[0-9]/.test(x.raw) && !/[a-z]{3,}/i.test(x.raw.replace(/[a-z]*gst/i, '')));
    if (nums.length === 0) return;

    const rowHeads = HEAD_RE.filter((h) => h.re.test(rowText)).map((h) => h.head);

    nums.forEach(({ i, n }, idx) => {
      let head: TaxHead | undefined = colHead.get(i);
      if (!head && rowHeads.length === 1) head = rowHeads[0];
      else if (!head && rowHeads.length > 1 && rowHeads[idx]) head = rowHeads[idx];
      if (!head && nums.length === 1) head = /value|turnover|outward|purchase|sales/i.test(rule.label) ? 'VALUE' : 'TOTAL';

      const key = `${rule.label}|${head || ''}`;
      if (seen.has(key)) return;
      seen.add(key);

      out.push({
        id: `fig_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
        sourceFile: file.name,
        docType,
        label: rule.label,
        value: n,
        head,
      });
    });
  });

  return out;
}

/**
 * Collapse a set of figures matching a label into one amount:
 * prefer an explicit TOTAL/VALUE, else sum the IGST+CGST+SGST(+CESS) heads,
 * else sum whatever is there.
 */
export function sumFigures(figures: ParsedFigure[]): number {
  if (figures.length === 0) return 0;
  const total = figures.find((f) => f.head === 'TOTAL' || f.head === 'VALUE');
  if (total) return total.value;
  const heads = figures.filter((f) => f.head && f.head !== 'CESS');
  if (heads.length) return heads.reduce((s, f) => s + f.value, 0) + (figures.find((f) => f.head === 'CESS')?.value || 0);
  return figures.reduce((s, f) => s + f.value, 0);
}
