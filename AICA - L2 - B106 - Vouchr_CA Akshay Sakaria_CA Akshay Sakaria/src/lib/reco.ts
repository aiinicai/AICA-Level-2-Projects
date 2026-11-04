// GSTR-2B (or 2A) ↔ books reconciliation.
// Parser follows the layout used by open-source tools: data.docdata.b2b[].inv[] (or top-level docdata),
// supplier `ctin`/`trdnm`, invoice `inum`, `dt` (DD-MM-YYYY), `val`, tax either on the invoice
// (txval/igst/cgst/sgst/cess) or in items[] / itms[].itm_det (iamt/camt/samt/csamt).
// NOT an official GSTN spec — validate against a real portal download before go-live.

import type { Expense, RecoLine, RecoStatus } from '../data/types';
import { round2 } from './money';

const num = (v: unknown) => (typeof v === 'number' ? v : Number(v ?? 0)) || 0;

function ddmmyyyy(d?: string): string | undefined {
  if (!d) return undefined;
  const m = /^(\d{2})[-/](\d{2})[-/](\d{4})$/.exec(d);
  return m ? `${m[3]}-${m[2]}-${m[1]}` : d;
}

interface RawInv {
  inum?: string; dt?: string; val?: number;
  txval?: number; igst?: number; cgst?: number; sgst?: number; cess?: number;
  iamt?: number; camt?: number; samt?: number; csamt?: number; itcavl?: string;
  items?: Record<string, number>[];
  itms?: { itm_det?: Record<string, number> }[];
}

function taxOf(inv: RawInv) {
  const items: Record<string, number>[] = inv.items ?? inv.itms?.map((i) => i.itm_det ?? {}) ?? [];
  const src = items.length ? items : [inv as Record<string, number>];
  const sum = (a: string, b?: string) => round2(src.reduce((s, it) => s + num(it[a] ?? (b ? it[b] : 0)), 0));
  return { taxableValue: sum('txval'), igst: sum('igst', 'iamt'), cgst: sum('cgst', 'camt'), sgst: sum('sgst', 'samt'), cess: sum('cess', 'csamt') };
}

export interface Parsed2B {
  period?: string;
  gstin?: string;
  lines: RecoLine[];
}

export function parse2B(json: unknown): Parsed2B {
  const root = json as { data?: Record<string, unknown> } & Record<string, unknown>;
  const data = (root.data ?? root) as { rtnprd?: string; gstin?: string; docdata?: { b2b?: unknown[]; cdnr?: unknown[] }; b2b?: unknown[]; cdnr?: unknown[] };
  const b2b = (data.docdata?.b2b ?? data.b2b ?? []) as { ctin?: string; trdnm?: string; inv?: RawInv[] }[];
  const cdnr = (data.docdata?.cdnr ?? data.cdnr ?? []) as { ctin?: string; trdnm?: string; nt?: (RawInv & { ntnum?: string; typ?: string })[] }[];
  if (!Array.isArray(b2b)) throw new Error('No B2B invoices found in this file');
  const lines: RecoLine[] = [];
  // CDNR: credit (typ C) / debit (typ D) notes from suppliers. Layout as for b2b with ntnum / typ — not an official spec either.
  for (const sup of Array.isArray(cdnr) ? cdnr : []) {
    for (const nt of sup.nt ?? []) {
      const typ = String(nt.typ ?? '').toUpperCase();
      if (!sup.ctin || !nt.ntnum || (typ !== 'C' && typ !== 'D')) continue;
      lines.push({ docType: typ === 'C' ? 'credit' : 'debit', supplierGstin: sup.ctin.toUpperCase(), supplierName: sup.trdnm, invoiceNo: String(nt.ntnum),
        invoiceDate: ddmmyyyy(nt.dt), invoiceValue: nt.val !== undefined ? num(nt.val) : undefined, itcAvailable: nt.itcavl === undefined ? undefined : nt.itcavl === 'Y', ...taxOf(nt) });
    }
  }
  for (const sup of b2b) {
    for (const inv of sup.inv ?? []) {
      if (!sup.ctin || !inv.inum) continue;
      lines.push({
        docType: 'invoice', supplierGstin: sup.ctin.toUpperCase(), supplierName: sup.trdnm, invoiceNo: String(inv.inum),
        invoiceDate: ddmmyyyy(inv.dt), invoiceValue: inv.val !== undefined ? num(inv.val) : undefined,
        itcAvailable: inv.itcavl === undefined ? undefined : inv.itcavl === 'Y', ...taxOf(inv)
      });
    }
  }
  return { period: data.rtnprd, gstin: data.gstin, lines };
}

/** Invoice numbers are matched ignoring case, spaces, slashes, dashes and leading zeros. */
export const normInv = (s: string) => s.toUpperCase().replace(/[\s/\\\-_.]/g, '').replace(/^0+/, '');

export interface RecoRow {
  status: RecoStatus;
  supplierGstin: string;
  supplierName: string;
  invoiceNo: string;
  invoiceDate?: string;
  booksTax: number;
  portalTax: number;
  diff: number;
  expenseId?: string;
  note?: string;
}

export function reconcile(expenses: Expense[], vendorGstin: (e: Expense) => string | undefined, lines: RecoLine[], tolerance = 1): RecoRow[] {
  const rows: RecoRow[] = [];
  const used = new Set<number>();
  const books = expenses.filter((e) => e.status !== 'rejected' && e.cgst + e.sgst + e.igst > 0);

  for (const e of books) {
    const g = vendorGstin(e);
    const tax = round2(e.cgst + e.sgst + e.igst);
    const idx = g ? lines.findIndex((l, i) => !used.has(i) && (l.docType ?? 'invoice') === 'invoice' && l.supplierGstin === g && normInv(l.invoiceNo) === normInv(e.invoiceNo ?? '')) : -1;
    if (idx < 0) {
      rows.push({ status: 'missing_in_2b', supplierGstin: g ?? '—', supplierName: e.vendorName, invoiceNo: e.invoiceNo ?? '—', invoiceDate: e.invoiceDate,
        booksTax: tax, portalTax: 0, diff: tax, expenseId: e.id, note: g ? 'Supplier has not reported this invoice — follow up before claiming ITC' : 'No vendor GSTIN in books' });
      continue;
    }
    used.add(idx);
    const l = lines[idx];
    const ptax = round2(l.igst + l.cgst + l.sgst);
    const diff = round2(tax - ptax);
    const notes: string[] = [];
    if (Math.abs(diff) > tolerance) notes.push(`Tax differs by ₹${diff}`);
    if (Math.abs(round2(e.taxableValue - l.taxableValue)) > tolerance) notes.push(`Taxable differs (books ₹${e.taxableValue}, 2B ₹${l.taxableValue})`);
    if ((e.igst > 0) !== (l.igst > 0)) notes.push('IGST vs CGST/SGST mismatch');
    if (l.invoiceDate && l.invoiceDate !== e.invoiceDate) notes.push(`Date differs (2B ${l.invoiceDate})`);
    if (l.itcAvailable === false) notes.push('ITC not available as per 2B');
    rows.push({ status: notes.length ? 'mismatch' : 'matched', supplierGstin: l.supplierGstin, supplierName: e.vendorName, invoiceNo: e.invoiceNo ?? l.invoiceNo,
      invoiceDate: e.invoiceDate, booksTax: tax, portalTax: ptax, diff, expenseId: e.id, note: notes.join('; ') || undefined });
  }
  lines.forEach((l, i) => {
    if (used.has(i) || (l.docType ?? 'invoice') !== 'invoice') return; // notes are matched by reconcileNotes
    const ptax = round2(l.igst + l.cgst + l.sgst);
    rows.push({ status: 'missing_in_books', supplierGstin: l.supplierGstin, supplierName: l.supplierName ?? '—', invoiceNo: l.invoiceNo, invoiceDate: l.invoiceDate,
      booksTax: 0, portalTax: ptax, diff: -ptax, note: 'In 2B but not recorded — bill not submitted, or not ours' });
  });
  return rows;
}
