// GST registers. The CA confirms every rule before relying on them (marked unverified in the masters).
//
// 1) RCM — when the reverse-charge GST is due (its "time of supply", CGST Act):
//    • services, s.13(3): the EARLIER of the payment date and the date immediately after 60 days from the invoice;
//    • goods, s.12(3): the EARLIEST of receipt of goods, payment, and the date immediately after 30 days from the invoice.
//      Goods receipt is not recorded in Vouchr, so goods entries are marked "receipt date not recorded".
//    Paid in part: each payment fixes the time for its share; the rest falls on the 61st (or 31st) day.
//    Reported in GSTR-3B table 3.1(d) for the month of that date.
// 2) ITC 180-day register — CGST Act s.16(2) second proviso: ITC on a bill not paid within 180 days of the invoice date is
//    reversed (in the return for the period the 180 days end), and re-claimed when it is paid. Proportionate to the part
//    unpaid. Reverse-charge bills are outside this rule. TDS deducted counts as paid. Interest, if any, is the CA's call.
import type { Expense, ItcReversal, Payment, RcmRule } from '../data/types';
import { round2 } from './money';

const addDays = (iso: string, n: number) => { const d = new Date(iso + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
const live = (e: Expense) => e.status !== 'rejected' && e.status !== 'draft';
const settledBase = (e: Expense) => round2(e.totalAmount + (e.noteAdjust ?? 0) - e.tdsAmount); // what is paid in cash

export interface RcmEntry { expenseId: string; vendorName: string; invoiceNo?: string; date: string; month: string; amount: number;
  basis: 'payment' | 'after_60_days' | 'after_30_days'; supply: 'goods' | 'services'; upcoming: boolean; receiptUnknown?: boolean }

export function rcmLiability(expenses: Expense[], payments: Payment[], rules: RcmRule[], today: string): RcmEntry[] {
  const out: RcmEntry[] = [];
  for (const e of expenses.filter((x) => live(x) && x.rcmApplicable && x.rcmTax > 0)) {
    const supply = rules.find((r) => r.code === e.rcmCode)?.supply ?? 'services';
    const cutoff = addDays(e.invoiceDate, supply === 'goods' ? 31 : 61);
    const base = settledBase(e) || e.totalAmount;
    const allocs = payments.flatMap((p) => p.allocations.filter((a) => a.expenseId === e.id).map((a) => ({ date: p.paidOn, amount: a.amount }))).sort((a, b) => a.date.localeCompare(b.date));
    let left = e.rcmTax;
    const push = (date: string, amount: number, basis: RcmEntry['basis']) => {
      if (amount <= 0) return;
      out.push({ expenseId: e.id, vendorName: e.vendorName, invoiceNo: e.invoiceNo, date, month: date.slice(0, 7), amount, basis, supply, upcoming: date > today, receiptUnknown: supply === 'goods' || undefined });
    };
    for (const a of allocs) {
      if (a.date >= cutoff || left <= 0) break;
      const share = round2(Math.min(left, (e.rcmTax * a.amount) / base));
      push(a.date, share, 'payment');
      left = round2(left - share);
    }
    const lateBasis: RcmEntry['basis'] = supply === 'goods' ? 'after_30_days' : 'after_60_days';
    push(cutoff, round2(left), lateBasis);
  }
  return out.sort((a, b) => a.date.localeCompare(b.date));
}

export type ItcStatus = 'not_due' | 'paid_in_time' | 'reverse' | 'reversed' | 'reclaim' | 'reclaimed';
export interface ItcRow { expenseId: string; vendorName: string; invoiceNo?: string; invoiceDate: string; day180: string; itc: number;
  unpaidAt180: number; reverseAmount: number; reverseMonth: string; status: ItcStatus; record?: ItcReversal; reclaimable: number }

export function itcRegister(expenses: Expense[], payments: Payment[], records: ItcReversal[], today: string): ItcRow[] {
  const rows: ItcRow[] = [];
  for (const e of expenses.filter((x) => live(x) && x.itcEligible && !x.rcmApplicable && x.cgst + x.sgst + x.igst > 0)) {
    const itc = round2(e.cgst + e.sgst + e.igst);
    const day180 = addDays(e.invoiceDate, 180);
    const base = settledBase(e);
    const paidBy = (d: string) => round2(payments.reduce((s, p) => s + (p.paidOn <= d ? p.allocations.filter((a) => a.expenseId === e.id).reduce((x, a) => x + a.amount, 0) : 0), 0));
    const unpaidAt180 = round2(Math.max(0, base - paidBy(day180)));
    const reverseAmount = base > 0 ? round2((itc * unpaidAt180) / base) : 0;
    const record = records.find((r) => r.expenseId === e.id);
    const unpaidNow = round2(Math.max(0, base - paidBy(today)));
    const reclaimable = record ? round2(Math.max(0, record.amount - (base > 0 ? (itc * unpaidNow) / base : 0) - (record.reclaimedAmount ?? 0))) : 0;
    const status: ItcStatus = day180 >= today ? 'not_due'
      : reverseAmount <= 0 ? 'paid_in_time'
      : !record ? 'reverse'
      : record.reclaimedAmount && record.reclaimedAmount >= record.amount - 0.01 ? 'reclaimed'
      : reclaimable > 0 ? 'reclaim' : 'reversed';
    if (status === 'not_due' && unpaidNow <= 0) continue; // paid before day 180 comes — nothing to watch
    rows.push({ expenseId: e.id, vendorName: e.vendorName, invoiceNo: e.invoiceNo, invoiceDate: e.invoiceDate, day180, itc, unpaidAt180, reverseAmount,
      reverseMonth: day180.slice(0, 7), status, record, reclaimable });
  }
  return rows.sort((a, b) => a.day180.localeCompare(b.day180));
}
