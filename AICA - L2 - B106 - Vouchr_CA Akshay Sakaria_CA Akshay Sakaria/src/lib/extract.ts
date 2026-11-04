// Free, on-device field extraction from document text (PDF text layer or OCR output).
// Approach follows invoice2data (PyPI): keyword-anchored regex rules — but generic, not per-vendor templates,
// so every field is a *suggestion* the user confirms. Nothing here guesses silently: unknown = undefined.

import { checkGstin } from './validators';
import { round2 } from './money';

const MONTHS: Record<string, string> = { jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06', jul: '07', aug: '08', sep: '09', sept: '09', oct: '10', nov: '11', dec: '12' };

/** Collapse the spacing PDF/OCR text comes with ("Date   of   Deposit", "27- Jul-2024"). */
export const squash = (t: string) => t.replace(/ /g, ' ').replace(/[ \t]+/g, ' ').replace(/ ?- ?/g, '-');

/** Parses 27-Jul-2024, 27 July 2024, 27/07/2024, 27.07.24, 2024-07-27 → yyyy-mm-dd. */
export function parseDate(raw: string): string | undefined {
  const s = raw.trim().replace(/\s+/g, ' ');
  let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = /^(\d{1,2})[-/. ](\d{1,2})[-/. ](\d{2}|\d{4})$/.exec(s);
  if (m) {
    const y = m[3].length === 2 ? `20${m[3]}` : m[3];
    const mo = Number(m[2]), d = Number(m[1]);
    if (mo < 1 || mo > 12 || d < 1 || d > 31) return undefined;
    return `${y}-${String(mo).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
  }
  m = /^(\d{1,2})[-/. ]?([A-Za-z]{3,9})[-/., ]+(\d{2}|\d{4})$/.exec(s);
  if (m) {
    const mo = MONTHS[m[2].toLowerCase().slice(0, m[2].toLowerCase().startsWith('sept') ? 4 : 3)];
    if (!mo) return undefined;
    const y = m[3].length === 2 ? `20${m[3]}` : m[3];
    return `${y}-${mo}-${m[1].padStart(2, '0')}`;
  }
  return undefined;
}

const DATE_RE = /(\d{4}-\d{2}-\d{2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[-/. ]?[A-Za-z]{3,9}[-/., ]+\d{2,4})/;
const AMOUNT_RE = /(?:₹|rs\.?|inr)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.\d{1,2})?|[0-9]+(?:\.\d{1,2})?)/i;
const toNum = (s: string) => Number(s.replace(/,/g, ''));

/** Value that follows a label on the same line, e.g. "BSR code : 6360014". */
function after(text: string, label: RegExp, value: RegExp): string | undefined {
  for (const line of text.split(/\r?\n/)) {
    const i = line.search(label);
    if (i < 0) continue;
    const rest = line.slice(i).replace(label, '').replace(/^\s*[:.\-#]*\s*/, '');
    const m = value.exec(rest);
    if (m) return m[1] ?? m[0];
  }
  return undefined;
}

/** Label on one line, value on the next (common in PDF text layers: "Amount (in Rs.) :" / "₹ 1"). */
function afterOrNext(text: string, label: RegExp, value: RegExp): string | undefined {
  const same = after(text, label, value);
  if (same) return same;
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length - 1; i++) {
    if (label.test(lines[i])) {
      const m = value.exec(lines[i + 1]);
      if (m) return m[1] ?? m[0];
    }
  }
  return undefined;
}

// ---------------------------------------------------------------- invoices

export interface InvoiceFields {
  vendorName?: string;
  vendorGstin?: string;
  invoiceNo?: string;
  invoiceDate?: string;
  totalAmount?: number;
  gstRatePct?: number;
  hsnSac?: string;
  discount?: number;
  irn?: string;
  gstinRepaired?: boolean;
  taxAmount?: number; // CGST + SGST + IGST printed on the bill
  taxKind?: 'intra' | 'inter'; // what the bill actually charged: CGST+SGST (intra-state) or IGST (inter-state)
  nonTaxable?: number; // printed charges outside this bill's GST (fare collected for an airline / IRCTC, reimbursements)
  ecoPaysTax?: boolean; // section 9(5): the e-commerce operator pays the GST
  ecoGstin?: string; // GSTIN fixed from a photo misread (e.g. Z read as 2) — check digit passed, person should still check
  found: number; // how many fields were found (for the "check carefully" hint)
}

const NOT_A_NAME = /^(tax\s*invoice|e-?\s*invoice|invoice|bill\s*of\s*supply|original|duplicate|triplicate|cash\s*memo|receipt|estimate|gstin|irn|ack|page\s*\d|paid|take\s*away|delivery)/i;
const COMPANY = /\b(private\s+limited|pvt\.?\s*ltd\.?|limited|ltd\.?|llp|& co\.?|enterprises|traders|services|industries|works|stores?|agencies|associates|hardware|solutions)\b/i;
// labels that sit in the same row as "Invoice No." in tabular PDFs — never a bill number
const LABEL_WORD = /^(hsn|sac|hsn\/sac|date|dated|dt|gstin|pan|cin|place|e-?way|delivery|booking|order|reference|ref)\b/i;
// strongest first: the amount actually payable
const STRONG_TOTAL = /(grand\s*total|total\s*amount\s*payable|amount\s*payable|net\s*payable|total\s*payable|total\s*inv(?:oice)?\.?\s*(?:amt|amount|value)|invoice\s*(?:total|value)|total\s*amount|bill\s*amount|total\s*amt)/i;

/** Amount on a total line: the one right after "₹" if printed, else the rightmost amount (last column = row total). */
function amountOnLine(line: string, from = 0): number | undefined {
  const part = line.slice(from);
  const rupee = /₹\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.\d{1,2})?|[0-9]+(?:\.\d{1,2})?)/.exec(part);
  if (rupee) return toNum(rupee[1]);
  const all = [...part.matchAll(/(?<![\w/.-])([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.\d{1,2})?|[0-9]+\.\d{1,2})(?![\w/])/g)].map((m) => toNum(m[1]));
  return all.length ? all[all.length - 1] : undefined;
}

/** Value under a label in a table ("Invoice No.  HSN/SAC" / "M06AI26…  998551"), by column position.
 *  Looks up to 3 rows down, because PDFs interleave rows of neighbouring columns. `rows` keep their original spacing. */
function underLabel(rows: string[], label: RegExp, valid: (v: string) => boolean): string | undefined {
  for (let i = 0; i < rows.length - 1; i++) {
    const cells = rows[i].split(/\s{2,}/);
    const idx = cells.findIndex((c) => label.test(c));
    if (idx < 0) continue;
    for (const below of rows.slice(i + 1, i + 4)) {
      const v = below.split(/\s{2,}/)[idx]?.trim().split(/\s+/)[0];
      if (v && valid(v)) return v;
    }
  }
  return undefined;
}
const looksLikeBillNo = (v: string) => /\d/.test(v) && v.length >= 3 && !LABEL_WORD.test(v) && !new RegExp(`^${DATE_RE.source}$`).test(v) && !/^\d{10,}$/.test(v) && !/^\d{2}[A-Z]{5}\d{4}[A-Z]/i.test(v); // not an e-way bill no. or a GSTIN

// GSTIN layout: 2 digits · 5 letters · 4 digits · letter · 1-9/A-Z · "Z" · check character
const GSTIN_KIND = 'DDLLLLLDDDDLAZA';
const TO_DIGIT: Record<string, string> = { O: '0', D: '0', Q: '0', I: '1', L: '1', Z: '2', S: '5', B: '8', G: '6', T: '7' };
const TO_LETTER: Record<string, string> = { '0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B', '6': 'G', '7': 'T' };

/** Repairs only look-alike photo misreads, position by position, and accepts the result only if the official check
 *  character then matches. Anything else (a wrong letter that isn't a look-alike) is left unread — never guessed. */
export function repairGstin(raw: string): string | undefined {
  const c = raw.toUpperCase().replace(/[^0-9A-Z]/g, '');
  if (c.length !== 15) return undefined;
  const fixed = [...c].map((ch, i) => {
    const k = GSTIN_KIND[i];
    if (k === 'D') return /\d/.test(ch) ? ch : TO_DIGIT[ch] ?? ch;
    if (k === 'L') return /[A-Z]/.test(ch) ? ch : TO_LETTER[ch] ?? ch;
    if (k === 'Z') return ch === '2' ? 'Z' : ch;
    return ch;
  }).join('');
  return checkGstin(fixed).ok ? fixed : undefined;
}

export function parseInvoiceText(raw: string, ownGstin?: string): InvoiceFields {
  const text = squash(raw);
  const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
  const flat = lines.join(' ');
  const rows = raw.replace(/\u00a0/g, ' ').split(/\r?\n/).map((l) => l.trim()).filter(Boolean); // original spacing, for table columns
  const r: InvoiceFields = { found: 0 };

  // Supplier GSTIN = first valid GSTIN that is not the client's own
  const gstins = [...text.toUpperCase().matchAll(/\b\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b/g)].map((m) => m[0]);
  r.vendorGstin = gstins.find((g) => g !== ownGstin?.toUpperCase() && checkGstin(g).ok);
  if (!r.vendorGstin) {
    // photos: try look-alike repair on GSTIN-shaped tokens near a "GSTIN" label
    for (const m of text.toUpperCase().matchAll(/GSTIN[^A-Z0-9]{0,6}([0-9A-Z]{15})/g)) {
      const g = repairGstin(m[1]);
      if (g && g !== ownGstin?.toUpperCase()) { r.vendorGstin = g; r.gstinRepaired = true; break; }
    }
  }

  // Bill number: same line ("Invoice No: X"), or the cell under the label in a two-row table. Must contain a digit.
  const NO_LABEL = /\b(?:tax\s*)?(?:invoice|inv|[b8]ill)\s*(?:no\.?|number|#)|\bbill\s*(?=:)/i;
  const same = after(text, NO_LABEL, /([A-Za-z0-9][A-Za-z0-9/\-_.]{0,29})/)?.replace(/[.]$/, '');
  r.invoiceNo = same && looksLikeBillNo(same) ? same : underLabel(rows, NO_LABEL, looksLikeBillNo);

  // date after its label; otherwise the first date-like text that is a REAL date ("01/25-26" inside a bill no. is not)
  const labelled = after(text, /\b(?:invoice|bill|inv)?\s*(?:date|dated|dt\.?)\b/i, DATE_RE);
  r.invoiceDate = (labelled ? parseDate(labelled) : undefined)
    ?? [...text.matchAll(new RegExp(DATE_RE.source, 'g'))].map((m) => parseDate(m[1])).find(Boolean);

  // Total: first "grand total / amount payable / total invoice amount" line; otherwise a "Total" row that is not a tax-summary row
  for (const line of lines) {
    const m = STRONG_TOTAL.exec(line);
    if (!m || /(in\s*words|taxable)/i.test(line.slice(m.index, m.index + m[0].length + 2))) continue;
    const n = amountOnLine(line, m.index + m[0].length);
    if (n && n > 0 && n < 1e10) { r.totalAmount = round2(n); break; }
  }
  if (r.totalAmount === undefined) {
    const weak: number[] = [];
    lines.forEach((line, i) => {
      if (!/^total\b/i.test(line) || /(in\s*words|items?|qty|quantity)/i.test(line)) return;
      if (i > 0 && /taxable/i.test(lines[i - 1])) return; // HSN-wise tax summary table
      const n = amountOnLine(line);
      if (n && n > 0 && n < 1e10) weak.push(n);
    });
    if (weak.length) r.totalAmount = round2(weak[0]);
  }

  // GST rate: "CGST @ 9%" → 18; "IGST 18%" → 18
  const half = /\b[CS]GST\s*@?\s*\(?\s*(\d{1,2}(?:\.\d+)?)\s*%/i.exec(text);
  const full = /\bIGST\s*@?\s*\(?\s*(\d{1,2}(?:\.\d+)?)\s*%/i.exec(text);
  const rate = full ? Number(full[1]) : half ? Number(half[1]) * 2 : undefined;
  if (rate !== undefined && [0, 3, 5, 12, 18, 28, 40].includes(rate)) r.gstRatePct = rate;

  r.hsnSac = after(text, /\b(?:HSN|SAC)(?:\s*\/\s*SAC)?(?:\s*code)?\b/i, /\b(\d{4}|\d{6}|\d{8})\b/) ?? underLabel(rows, /\b(?:HSN|SAC)\b/i, (v) => /^\d{4,8}$/.test(v));
  const disc = after(text, /\bdiscount\s*(?:fixed|amount)?\b/i, /\(?\s*(?:₹|rs\.?)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.\d{1,2})?|[0-9]+\.\d{1,2})\s*\)?/i);
  if (disc && toNum(disc) > 0 && (!r.totalAmount || toNum(disc) < r.totalAmount)) r.discount = toNum(disc);

  // e-invoice IRN: 64 hex characters after "IRN" (may wrap onto two lines in the PDF)
  const irn = /\bIRN\b\s*[:.]?\s*([0-9a-f\-\s]{64,90})/i.exec(flat)?.[1].replace(/[\s-]/g, '').slice(0, 64);
  if (irn && /^[0-9a-f]{64}$/i.test(irn)) r.irn = irn.toLowerCase();

  // Vendor name: explicit "Sold by / Invoice issued by" wins; else a company-like line before the supplier GSTIN
  const named = /\b(?:invoice\s*issued\s*by|sold\s*by|seller|supplier)\s*:?\s*([A-Za-z][A-Za-z0-9&.,()' -]{2,80}?)(?=\s+on\s+behalf|\s*,?\s*(?:ship-?\s*from|address|gstin|pan)\b|\s{2,}|$)/i.exec(flat);
  const gIdx = r.vendorGstin ? lines.findIndex((l) => l.toUpperCase().includes(r.vendorGstin!)) : -1;
  const pool = (gIdx > 0 ? lines.slice(0, gIdx) : lines.slice(0, 6)).flatMap((l) => l.split(/\s{2,}/)).map((l) => l.trim().replace(/[,:]$/, ''));
  const ok = (l: string) => l.length > 2 && l.length < 70 && /[A-Za-z]{3}/.test(l) && !NOT_A_NAME.test(l) && !/\d{6,}/.test(l) && !/[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4}/.test(l);
  if (r.vendorGstin || r.invoiceNo || r.totalAmount) {
    r.vendorName = named?.[1].trim().replace(/[,.]$/, '') ?? pool.find((l) => ok(l) && COMPANY.test(l)) ?? pool.find(ok);
  }

  // GST amounts as printed: first "CGST/SGST/UTGST/IGST … % … amount" line of each kind
  const taxOf = (kind: RegExp) => {
    // a "Total IGST …" line wins over the first item line (ride bills list tax per item, then the total)
    const ordered = [...lines.filter((l) => /^total\b/i.test(l)), ...lines.filter((l) => !/^total\b/i.test(l))];
    for (const line of ordered) {
      const m = kind.exec(line);
      if (!m) continue;
      const pct = line.indexOf('%', m.index);
      if (pct < 0) continue;
      const n = amountOnLine(line, pct + 1);
      if (n !== undefined && n > 0) return n;
    }
    return 0;
  };
  const cg = taxOf(/\bCGST\b/i), sg = taxOf(/\b(?:SGST|UTGST)\b/i), ig = taxOf(/\bIGST\b/i);
  if (cg + sg + ig > 0) r.taxAmount = round2(cg + sg + ig);
  if (ig > 0 && !cg && !sg) r.taxKind = 'inter';
  else if ((cg > 0 || sg > 0) && !ig) r.taxKind = 'intra';

  // Non-GST part (travel portals, booking platforms): printed lines for fares / charges of ANOTHER supplier, which carry no
  // GST of their own on this bill. Accepted only if the arithmetic agrees: total − non-GST − GST = GST ÷ rate (±₹1).
  if (r.totalAmount && r.taxAmount && r.gstRatePct) {
    const PASS = /(fare|collected\s+on\s+behalf|on\s+behalf\s+of|reimburs|pure\s+agent|inclusive\s+of\s+(?:applicable\s+)?taxes|including\s+gst)/i;
    let pass = 0;
    const used = new Set<number>();
    const bare = /^(?:₹|rs\.?)?\s*[0-9][0-9,]*(?:\.\d{1,2})?$/i; // a line holding only an amount
    lines.forEach((line, i) => {
      if (!PASS.test(line) || /\b[CSI]GST\b|UTGST/i.test(line.replace(/including\s+gst/i, ''))) return;
      const own = amountOnLine(line);
      if (own !== undefined) { pass += own; return; }
      // PDF column layouts often print the amount on the line just above or below its label
      for (const j of [i - 1, i + 1]) if (lines[j] && !used.has(j) && bare.test(lines[j])) { pass += amountOnLine(lines[j]) ?? 0; used.add(j); return; }
    });
    const taxable = r.totalAmount - pass - r.taxAmount;
    if (pass > 1 && Math.abs(taxable - (r.taxAmount * 100) / r.gstRatePct) <= 1) r.nonTaxable = round2(pass);
  }

  // Section 9(5): "Tax to be paid under section 9(5) by ECO", "Details of ECO under GST", "e-commerce operator"
  if (/section\s*9\s*\(\s*5\s*\)|\b9\s*\(\s*5\s*\)|e-?\s*commerce\s+operator|\bby\s+eco\b|details\s+of\s+eco/i.test(flat)) {
    r.ecoPaysTax = true;
    const g = /\bECO\b[\s\S]{0,300}?(\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z])/.exec(flat.toUpperCase())?.[1];
    if (g && checkGstin(g).ok) r.ecoGstin = g;
  }

  r.found = [r.vendorGstin, r.invoiceNo, r.invoiceDate, r.totalAmount, r.vendorName].filter(Boolean).length;
  return r;
}

// ---------------------------------------------------------------- TDS challan receipts
// Labels taken from a real e-Pay Tax "Challan Receipt" (incometax.gov.in): "BSR code :", "Challan No :",
// "Date of Deposit : 27-Jul-2024", "Tender Date : 27/07/2024", "CIN :", "Amount (in Rs.) :" then "₹ 1",
// "ITNS No. : 280", "Minor Head : ... (300)", "Total (A+B+C+D+E+F) ₹ 1".

export interface ChallanFields {
  bsrCode?: string;
  challanNo?: string;
  depositDate?: string;
  amount?: number;
  cin?: string;
  itns?: string;
  tan?: string;
  minorHead?: string;
  found: number;
}

export function parseChallanText(raw: string): ChallanFields {
  const text = squash(raw);
  const r: ChallanFields = { found: 0 };
  r.bsrCode = after(text, /BSR\s*code/i, /\b(\d{7})\b/);
  r.challanNo = after(text, /Challan\s*(?:No\.?|Number|Serial\s*No\.?)/i, /\b(\d{5})\b/);
  const dep = after(text, /Date\s*of\s*Deposit/i, DATE_RE) ?? after(text, /Tender\s*Date/i, DATE_RE);
  r.depositDate = dep ? parseDate(dep) : undefined;
  const total = after(text, /Total\s*\(A\+B/i, AMOUNT_RE) ?? afterOrNext(text, /Amount\s*\(in\s*Rs\.?\)/i, AMOUNT_RE);
  if (total) r.amount = toNum(total);
  r.cin = after(text, /\bCIN\b/i, /\b([0-9A-Z]{15,22})\b/);
  r.itns = after(text, /ITNS\s*No\.?/i, /\b(\d{3})\b/);
  r.tan = /\b([A-Z]{4}\d{5}[A-Z])\b/.exec(text.toUpperCase())?.[1];
  r.minorHead = after(text, /Minor\s*Head/i, /(.{3,60})/)?.trim();
  r.found = [r.bsrCode, r.challanNo, r.depositDate, r.amount].filter((x) => x !== undefined).length;
  return r;
}
