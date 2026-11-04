// Credit / debit notes received FROM vendors (CGST Act s.34).
//  • credit note (return, rate reduced, discount after the bill): we owe less, and the GST on it reduces our ITC;
//  • debit note (rate increased, extra charge): we owe more, and its GST adds to ITC (if the bill's ITC is eligible).
// A note is linked to the bill it corrects (its balance changes) or kept at vendor level until linked.
// Matched with GSTR-2B section CDNR. TDS on the original bill is not changed automatically — marked for the CA.
import type { Expense, ExpenseHead, RecoLine, VendorNote } from '../data/types';
import { round2 } from './money';
import { normInv, type RecoRow } from './reco';

export const NOTE_REASONS = ['return', 'rate', 'discount', 'deficiency', 'other'] as const;
export const REASON_LABEL: Record<VendorNote['reason'], string> = {
  return: 'Goods returned', rate: 'Rate / price corrected', discount: 'Discount after the bill', deficiency: 'Deficient service', other: 'Other'
};

export const noteGst = (n: Pick<VendorNote, 'cgst' | 'sgst' | 'igst'>) => round2(n.cgst + n.sgst + n.igst);
/** + increases what we owe (debit note), − reduces it (credit note). */
export const signed = (n: Pick<VendorNote, 'kind' | 'totalAmount'>) => (n.kind === 'debit' ? n.totalAmount : -n.totalAmount);

const live = (notes: VendorNote[]) => notes.filter((n) => n.status !== 'void');

/** Change to a bill's value from the notes linked to it (stored on the bill as noteAdjust). */
export const noteAdjustFor = (expenseId: string, notes: VendorNote[]) =>
  round2(live(notes).filter((n) => n.expenseId === expenseId).reduce((s, n) => s + signed(n), 0));

/** ITC change from notes: credit notes on ITC-eligible purchases reduce it, debit notes add to it. */
export const noteItcDelta = (notes: VendorNote[]) =>
  round2(live(notes).filter((n) => n.itcEligible).reduce((s, n) => s + (n.kind === 'debit' ? 1 : -1) * noteGst(n), 0));

/** Notes not linked to any bill yet — vendor-level credit (−) or charge (+). */
export const vendorLevelBalance = (vendorId: string, notes: VendorNote[]) =>
  round2(live(notes).filter((n) => n.vendorId === vendorId && !n.expenseId).reduce((s, n) => s + signed(n), 0));

export interface NoteCheck { errors: string[]; flags: string[]; vars?: Record<string, number> }

/** Rules before a note is saved. `bill` = the linked bill, `others` = other live notes already on it. */
export function checkNote(n: Omit<VendorNote, 'id' | 'createdAt' | 'createdBy' | 'status'>, bill: Expense | undefined, others: VendorNote[], allNotes: VendorNote[]): NoteCheck {
  const errors: string[] = [], flags: string[] = [];
  let vars: Record<string, number> | undefined;
  if (!n.noteNo.trim()) errors.push('Enter the note number printed on the vendor’s note');
  if (!(n.totalAmount > 0)) errors.push('Enter the note amount');
  if (Math.abs(round2(n.taxableValue + noteGst(n) - n.totalAmount)) > 1) errors.push('Taxable + GST differs from the note total by more than ₹1');
  if (n.cgst !== n.sgst) errors.push('CGST and SGST must be equal');
  if (n.igst > 0 && n.cgst + n.sgst > 0) errors.push('A note has either IGST or CGST + SGST, not both');
  const dup = live(allNotes).find((x) => x.vendorId === n.vendorId && x.fyLabel === n.fyLabel && normInv(x.noteNo) === normInv(n.noteNo) && x.kind === n.kind);
  if (dup) errors.push('This note number is already recorded for this vendor in this financial year');
  if (bill) {
    if (bill.vendorId !== n.vendorId) errors.push('The bill belongs to another vendor');
    if (n.noteDate < bill.invoiceDate) errors.push('A note cannot be dated before the bill it corrects');
    if (n.kind === 'credit') {
      const room = round2(bill.totalAmount + others.filter((x) => x.status !== 'void').reduce((s, x) => s + signed(x), 0));
      if (n.totalAmount > room + 0.01) { errors.push('Credit notes cannot exceed the bill value (₹{room} left)'); vars = { room }; }
    }
    if (bill.tdsAmount > 0) flags.push('tds_on_original'); // TDS was worked out on the original amount — the CA decides any change
    if ((bill.igst > 0) !== (n.igst > 0) && noteGst(n) > 0) errors.push('The note’s tax type (IGST vs CGST + SGST) must match the bill');
  }
  return { errors, flags, vars };
}

/** Tally lines (+ debit / − credit). Credit note: vendor Dr; expense and input GST Cr. Debit note: the reverse. */
export function noteLines(n: VendorNote, head: Pick<ExpenseHead, 'tallyLedger'>, ledgers: { inputCgst: string; inputSgst: string; inputIgst: string }, partyLedger: string) {
  const s = n.kind === 'credit' ? -1 : 1; // credit note reverses the purchase
  const lines = [{ ledger: head.tallyLedger, amount: s * round2(n.taxableValue + (n.itcEligible ? 0 : noteGst(n))) }];
  if (n.itcEligible) {
    if (n.cgst) lines.push({ ledger: ledgers.inputCgst, amount: s * n.cgst });
    if (n.sgst) lines.push({ ledger: ledgers.inputSgst, amount: s * n.sgst });
    if (n.igst) lines.push({ ledger: ledgers.inputIgst, amount: s * n.igst });
  }
  const diff = round2(n.totalAmount - n.taxableValue - noteGst(n));
  if (diff) lines.push({ ledger: head.tallyLedger, amount: s * diff });
  lines.push({ ledger: partyLedger, amount: -s * n.totalAmount });
  return lines;
}

/** Books' notes ↔ GSTR-2B CDNR lines (same matching as invoices: GSTIN + note number, then tax compared). */
export function reconcileNotes(notes: VendorNote[], gstinOf: (vendorId: string) => string | undefined, lines: RecoLine[], tolerance = 1): RecoRow[] {
  const portal = lines.filter((l) => l.docType === 'credit' || l.docType === 'debit');
  const used = new Set<number>();
  const rows: RecoRow[] = [];
  for (const n of live(notes).filter((x) => noteGst(x) > 0)) {
    const g = gstinOf(n.vendorId);
    const tax = noteGst(n);
    const idx = g ? portal.findIndex((l, i) => !used.has(i) && l.supplierGstin === g && l.docType === n.kind && normInv(l.invoiceNo) === normInv(n.noteNo)) : -1;
    const label = `${n.kind === 'credit' ? 'CN' : 'DN'} ${n.noteNo}`;
    if (idx < 0) {
      rows.push({ status: 'missing_in_2b', supplierGstin: g ?? '—', supplierName: n.vendorName, invoiceNo: label, invoiceDate: n.noteDate, booksTax: tax, portalTax: 0, diff: tax,
        note: n.kind === 'credit' ? 'Credit note not in 2B yet — the ITC reduction still applies from your books' : 'Debit note not in 2B — do not claim its ITC until the supplier reports it' });
      continue;
    }
    used.add(idx);
    const l = portal[idx];
    const ptax = round2(l.igst + l.cgst + l.sgst);
    const diff = round2(tax - ptax);
    const notes2: string[] = [];
    if (Math.abs(diff) > tolerance) notes2.push(`Tax differs by ₹${diff}`);
    if (l.invoiceDate && l.invoiceDate !== n.noteDate) notes2.push(`Date differs (2B ${l.invoiceDate})`);
    rows.push({ status: notes2.length ? 'mismatch' : 'matched', supplierGstin: l.supplierGstin, supplierName: n.vendorName, invoiceNo: label, invoiceDate: n.noteDate,
      booksTax: tax, portalTax: ptax, diff, note: notes2.join('; ') || undefined });
  }
  portal.forEach((l, i) => {
    if (used.has(i)) return;
    const ptax = round2(l.igst + l.cgst + l.sgst);
    rows.push({ status: 'missing_in_books', supplierGstin: l.supplierGstin, supplierName: l.supplierName ?? '—', invoiceNo: `${l.docType === 'credit' ? 'CN' : 'DN'} ${l.invoiceNo}`,
      invoiceDate: l.invoiceDate, booksTax: 0, portalTax: ptax, diff: -ptax,
      note: l.docType === 'credit' ? 'Credit note in 2B but not recorded — record it: it reduces your ITC' : 'Debit note in 2B but not recorded' });
  });
  return rows;
}
