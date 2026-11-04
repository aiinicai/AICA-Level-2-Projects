// TDS on advances (Income-tax Act 2025 s.393: deduct at credit or payment, whichever is earlier).
// Model: the cash actually paid is recorded on the payment; TDS deducted on the advance part sits on the payment
// (tdsOnAdvance). When the advance is applied to a bill, the TDS attributable to the applied cash moves with it as
// `tdsCredit` on the allocation, and the bill deducts only what is still due — so TDS is never deducted twice.
import type { Expense, Payment, TdsRate, Vendor } from '../data/types';
import { round2 } from './money';

/** Cash paid N with TDS at r%: the vendor is credited N ÷ (1 − r%), TDS = N × r ÷ (100 − r). ₹99,000 at 1% → TDS ₹1,000. */
export const grossUpTds = (net: number, ratePct: number) => (ratePct > 0 && ratePct < 100 ? round2((net * ratePct) / (100 - ratePct)) : 0);

/** TDS already deducted on advances that were applied to this bill. */
export const tdsCreditFor = (expenseId: string, payments: Payment[]) =>
  round2(payments.reduce((s, p) => s + p.allocations.filter((a) => a.expenseId === expenseId).reduce((x, a) => x + (a.tdsCredit ?? 0), 0), 0));

/** TDS still to deduct on the bill itself (bill TDS less what was deducted on applied advances). */
export const billTdsDue = (e: Expense, payments: Payment[]) => round2(Math.max(0, e.tdsAmount - tdsCreditFor(e.id, payments)));

/** TDS deducted on an advance and not yet carried to any bill. */
export const unusedAdvanceTds = (p: Payment) => round2((p.tdsOnAdvance?.amount ?? 0) - p.allocations.reduce((s, a) => s + (a.tdsCredit ?? 0), 0));

/** Balance of a bill after `cash` (+ its TDS credit) from advance `p` is applied. */
export function previewApply(e: Expense, payments: Payment[], p: Payment, cash: number) {
  const credit = p.tdsOnAdvance ? Math.min(grossUpTds(cash, p.tdsOnAdvance.ratePct), unusedAdvanceTds(p)) : 0;
  const paid = round2(payments.reduce((s, x) => s + x.allocations.filter((a) => a.expenseId === e.id).reduce((t, a) => t + a.amount, 0), 0) + cash);
  const creditAll = round2(tdsCreditFor(e.id, payments) + credit);
  return { credit: round2(credit), after: round2(e.totalAmount - paid - creditAll - Math.max(0, e.tdsAmount - creditAll)) };
}

/** Largest cash amount of advance `p` that can be applied to bill `e` without overpaying it. */
export function maxApplicable(e: Expense, payments: Payment[], p: Payment, left: number): number {
  if (previewApply(e, payments, p, left).after >= -0.005) return round2(left);
  let lo = 0, hi = left;
  for (let i = 0; i < 40; i++) { const mid = (lo + hi) / 2; if (previewApply(e, payments, p, mid).after >= -0.005) lo = mid; else hi = mid; }
  return Math.floor(lo * 100) / 100;
}

export interface AdvanceTdsSuggestion { code?: string; ratePct: number; applies: boolean; reason: string; vars?: Record<string, string | number>; noPan?: boolean }

/** Should TDS be deducted on this advance? Uses the vendor's TDS section from its earlier bills, the higher rate for a
 *  missing / inoperative PAN, and the single-payment and yearly limits (bills + advances paid this year). The CA decides. */
export function suggestAdvanceTds(vendor: Vendor | undefined, expenses: Expense[], payments: Payment[], rates: TdsRate[], advanceNet: number, paidOn: string, fy: string, code?: string): AdvanceTdsSuggestion {
  const bills = expenses.filter((e) => e.vendorId === vendor?.id && e.status !== 'rejected' && e.status !== 'draft');
  const useCode = code ?? [...bills].sort((a, b) => b.invoiceDate.localeCompare(a.invoiceDate)).find((e) => e.tdsCode)?.tdsCode;
  if (!vendor || !useCode) return { ratePct: 0, applies: false, reason: 'No TDS section known for this vendor yet — choose one if TDS applies to this advance.' };
  const r = rates.find((x) => x.code === useCode && x.effectiveFrom <= paidOn && (!x.effectiveTo || x.effectiveTo >= paidOn)) ?? rates.find((x) => x.code === useCode);
  if (!r) return { code: useCode, ratePct: 0, applies: false, reason: 'This TDS section is not in the tax masters.' };
  const noPan = !vendor.pan || vendor.panStatus === 'Inoperative';
  const ratePct = noPan && r.noPanRatePct ? r.noPanRatePct : r.ratePct;
  const gross = round2(advanceNet + grossUpTds(advanceNet, ratePct));
  const fyBills = round2(bills.filter((e) => e.fyLabel === fy).reduce((s, e) => s + e.taxableValue, 0));
  const fyAdvances = round2(payments.filter((p) => p.vendorId === vendor.id && p.tdsOnAdvance && p.paidOn >= `${fy.slice(0, 4)}-04-01`)
    .reduce((s, p) => s + (p.tdsOnAdvance!.base ?? (p.tdsOnAdvance!.amount * 100) / p.tdsOnAdvance!.ratePct), 0));
  const yearTotal = round2(fyBills + fyAdvances + gross);
  const overSingle = r.thresholdSingle !== undefined && gross > r.thresholdSingle;
  const overYear = r.thresholdAggregate !== undefined && yearTotal > r.thresholdAggregate;
  const noLimit = r.thresholdSingle === undefined && r.thresholdAggregate === undefined;
  const applies = overSingle || overYear || noLimit;
  const reason = applies
    ? overSingle ? 'This advance (₹{gross}) is above the single-payment limit of ₹{single}.' : overYear ? 'With this advance, payments to this vendor this year (₹{year}) cross the yearly limit of ₹{limit}.' : 'This section has no limit.'
    : 'Below the limits (₹{gross} now, ₹{year} this year) — TDS not needed yet.';
  return { code: useCode, ratePct, applies, reason, noPan,
    vars: { gross: inr(gross), single: inr(r.thresholdSingle ?? 0), year: inr(yearTotal), limit: inr(r.thresholdAggregate ?? 0) } };
}

const inr = (n: number) => n.toLocaleString('en-IN', { maximumFractionDigits: 2 });

export interface TdsEntry { check?: boolean /* marked for CA review */; kind: 'bill' | 'advance'; date: string; month: string; vendorId?: string; vendorName: string; code?: string; ratePct?: number; base: number; tds: number; ref: string }

/** Every TDS liability in one list, in the month it arose (s.393: credit or payment, whichever is earlier):
 *  - an advance paid on/before the bill date → that TDS belongs to the advance month, the bill shows only the rest;
 *  - an advance paid after the bill date → the bill's TDS stays in the bill month (it was already due), and the advance
 *    month shows only the TDS not used for such older bills.
 *  Feeds the TDS register, challan due alerts and the Form 140 working. */
export function tdsEntries(expenses: Expense[], payments: Payment[]): TdsEntry[] {
  const out: TdsEntry[] = [];
  const billDate = new Map(expenses.map((e) => [e.id, e.invoiceDate]));
  const isEarly = (p: Payment, expenseId: string) => p.paidOn <= (billDate.get(expenseId) ?? '');
  for (const e of expenses) {
    if (e.status === 'rejected' || e.status === 'draft') continue;
    const early = payments.reduce((s, p) => s + p.allocations.filter((a) => a.expenseId === e.id && isEarly(p, e.id)).reduce((x, a) => x + (a.tdsCredit ?? 0), 0), 0);
    const due = round2(Math.max(0, e.tdsAmount - early));
    if (due > 0) out.push({ kind: 'bill', date: e.invoiceDate, month: e.invoiceDate.slice(0, 7), vendorId: e.vendorId, vendorName: e.vendorName, code: e.tdsCode, ratePct: e.tdsRatePct,
      base: due === e.tdsAmount ? e.taxableValue : round2((due * 100) / (e.tdsRatePct || 1)), tds: due, ref: e.invoiceNo ?? e.id });
  }
  for (const p of payments) {
    const t = p.tdsOnAdvance;
    if (!t || t.amount <= 0) continue;
    const lateAllocs = p.allocations.filter((a) => !isEarly(p, a.expenseId));
    const late = lateAllocs.reduce((s, a) => s + (a.tdsCredit ?? 0), 0);
    const tds = round2(t.amount - late);
    if (tds <= 0) continue;
    // base = amount credited to the vendor for this TDS: recorded base less what went to older bills (cash + their TDS)
    const base = t.base ? round2(t.base - lateAllocs.reduce((s, a) => s + a.amount + (a.tdsCredit ?? 0), 0)) : round2((tds * 100) / t.ratePct);
    out.push({ check: p.flags?.includes('adv_tds_section_differs'), kind: 'advance', date: p.paidOn, month: p.paidOn.slice(0, 7), vendorId: p.vendorId, vendorName: p.vendorName, code: t.code, ratePct: t.ratePct, base, tds, ref: p.ref ?? p.id });
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}
