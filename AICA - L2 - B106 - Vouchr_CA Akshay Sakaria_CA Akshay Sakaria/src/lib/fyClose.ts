// Financial-year close (AUDIT-v0.4 B11). The checklist is computed from the books; blockers must be cleared before the CA
// firm can close; warnings are shown and must be acknowledged. Closing locks the 12 months. Nothing is moved or deleted:
// open bills, advances and notes simply carry on into the next year and are listed in the carry-forward sheet.
import type { Client, Expense, ItcReversal, Payment, TdsChallan, VendorNote } from '../data/types';
import { outstanding, unallocated } from './alerts';
import { itcRegister } from './gstRegisters';
import { round2 } from './money';
import { tdsEntries, unusedAdvanceTds } from './tdsAdvance';
import { vendorLevelBalance } from './vendorNotes';

export const fyMonths = (fy: string) => {
  const y = Number(fy.slice(0, 4));
  return Array.from({ length: 12 }, (_, i) => { const m = ((i + 3) % 12) + 1; return `${i < 9 ? y : y + 1}-${String(m).padStart(2, '0')}`; });
};
export const fyEnd = (fy: string) => `${Number(fy.slice(0, 4)) + 1}-03-31`;

export interface CloseCheck { key: string; label: string; count: number; amount?: number; blocker: boolean; vars?: Record<string, string | number> }

export function fyChecklist(fy: string, d: { client?: Client; expenses: Expense[]; payments: Payment[]; challans: TdsChallan[]; itcReversals: ItcReversal[] }, today: string): CloseCheck[] {
  const months = new Set(fyMonths(fy));
  const inFy = d.expenses.filter((e) => e.fyLabel === fy);
  const tally = d.client?.tallyMode && d.client.tallyMode !== 'none';
  const awaiting = inFy.filter((e) => e.status === 'submitted').length;
  const drafts = inFy.filter((e) => e.status === 'draft').length;
  const notPosted = tally ? inFy.filter((e) => e.status === 'approved').length : 0;
  const paysNotPosted = tally ? d.payments.filter((p) => months.has(p.paidOn.slice(0, 7)) && !p.postedAt).length : 0;
  const tdsByMonth = new Map<string, number>();
  for (const t of tdsEntries(d.expenses, d.payments)) if (months.has(t.month)) tdsByMonth.set(t.month, round2((tdsByMonth.get(t.month) ?? 0) + t.tds));
  const shortMonths = [...tdsByMonth].filter(([m, amt]) => d.challans.filter((c) => c.month === m).reduce((s, c) => s + c.amount, 0) < amt - 0.5);
  const tdsShort = round2(shortMonths.reduce((s, [m, amt]) => s + amt - d.challans.filter((c) => c.month === m).reduce((x, c) => x + c.amount, 0), 0));
  const itcDue = itcRegister(inFy, d.payments, d.itcReversals, today).filter((r) => r.status === 'reverse');
  return [
    { key: 'review', label: '{n} bill(s) still awaiting CA review', count: awaiting, blocker: true },
    { key: 'drafts', label: '{n} draft(s) not completed — complete or delete them', count: drafts, blocker: true },
    { key: 'tally_bills', label: '{n} approved bill(s) not posted to Tally', count: notPosted, blocker: true },
    { key: 'tally_pays', label: '{n} payment(s) of this year not posted to Tally', count: paysNotPosted, blocker: true },
    { key: 'tds', label: 'TDS of {n} month(s) not fully covered by challans ({amt})', count: shortMonths.length, amount: tdsShort, blocker: false },
    { key: 'itc', label: '{n} ITC reversal(s) due (180 days) not recorded', count: itcDue.length, amount: round2(itcDue.reduce((s, r) => s + r.reverseAmount, 0)), blocker: false }
  ];
}

export interface CarryRow { kind: 'open_bill' | 'advance' | 'advance_tds' | 'vendor_note'; vendor: string; ref: string; date: string; amount: number }

/** What carries into the next year (as on the FY end date's books — balances are as of today). */
export function carryForward(fy: string, d: { expenses: Expense[]; payments: Payment[]; vendorNotes: VendorNote[] }): CarryRow[] {
  const end = fyEnd(fy);
  const out: CarryRow[] = [];
  for (const e of d.expenses.filter((x) => x.invoiceDate <= end && x.status !== 'rejected' && x.status !== 'draft')) {
    const bal = outstanding(e, d.payments);
    if (Math.abs(bal) > 0.005) out.push({ kind: 'open_bill', vendor: e.vendorName, ref: e.invoiceNo ?? e.id, date: e.invoiceDate, amount: bal });
  }
  for (const p of d.payments.filter((x) => x.paidOn <= end)) {
    const left = unallocated(p);
    if (left > 0.005) out.push({ kind: 'advance', vendor: p.vendorName, ref: p.ref ?? p.id, date: p.paidOn, amount: left });
    const t = unusedAdvanceTds(p);
    if (t > 0.005) out.push({ kind: 'advance_tds', vendor: p.vendorName, ref: p.ref ?? p.id, date: p.paidOn, amount: t });
  }
  const seen = new Set<string>();
  for (const n of d.vendorNotes.filter((x) => x.status === 'active' && !x.expenseId && x.noteDate <= end)) {
    if (seen.has(n.vendorId)) continue;
    seen.add(n.vendorId);
    out.push({ kind: 'vendor_note', vendor: n.vendorName, ref: 'notes not linked to a bill', date: n.noteDate, amount: vendorLevelBalance(n.vendorId, d.vendorNotes) });
  }
  return out.sort((a, b) => a.vendor.localeCompare(b.vendor) || a.date.localeCompare(b.date));
}
