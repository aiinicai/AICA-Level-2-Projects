// Payables maths (bill status, due dates, ageing) and alerts. Server-side, the same logic runs daily
// (alerts Edge Function) and sends push + email; in the app it powers the bell, dues and dashboard.

import { tdsCreditFor, tdsEntries } from './tdsAdvance';
import type { Expense, Notification, Payment, TdsChallan } from '../data/types';
import { daysBetween, monthKey, monthName, toIso } from './dates';
import { fmtInr, round2 } from './money';

/** Amount of this bill settled by all payments (a payment may settle several bills). */
export const paidAmount = (expenseId: string, payments: Payment[]) =>
  round2(payments.reduce((s, p) => s + p.allocations.filter((a) => a.expenseId === expenseId).reduce((x, a) => x + a.amount, 0), 0));

export const netPayable = (e: Expense) => round2(e.totalAmount - e.tdsAmount);

/** Balance = total − cash paid − TDS deducted on applied advances − TDS still to deduct on the bill. */
export const outstanding = (e: Expense, payments: Payment[]) => {
  const credit = tdsCreditFor(e.id, payments);
  // + debit notes − credit notes from the vendor on this bill; below zero = the vendor owes us (refund or adjust)
  return round2(e.totalAmount + (e.noteAdjust ?? 0) - paidAmount(e.id, payments) - credit - Math.max(0, e.tdsAmount - credit));
};

/** Part of a payment not yet applied to any bill — a vendor advance. */
export const unallocated = (p: Payment) => round2(p.amount - p.allocations.reduce((s, a) => s + a.amount, 0));

export function dueDate(e: Expense, creditDays: number): string {
  const d = new Date(e.invoiceDate + 'T00:00:00');
  d.setDate(d.getDate() + creditDays);
  return toIso(d);
}

export type BillStatus = 'paid' | 'partial' | 'overdue' | 'open';

export function billStatus(e: Expense, payments: Payment[], today: string, creditDays: number): BillStatus {
  const due = outstanding(e, payments);
  if (due <= 0) return 'paid';
  if (dueDate(e, creditDays) < today) return 'overdue';
  return paidAmount(e.id, payments) > 0 ? 'partial' : 'open';
}

export const AGE_BUCKETS = ['Not due', '1–30', '31–60', '61–90', '90+'] as const;

/** Payables ageing by days past the due date (QuickBooks / Zoho style buckets). */
export function ageBucket(e: Expense, today: string, creditDays: number): (typeof AGE_BUCKETS)[number] {
  const late = daysBetween(dueDate(e, creditDays), today);
  if (late <= 0) return 'Not due';
  if (late <= 30) return '1–30';
  if (late <= 60) return '31–60';
  if (late <= 90) return '61–90';
  return '90+';
}

/** TDS deducted in a month is due on the 7th of next month (30 April for March) — confirm against the 2026 Rules. */
export function tdsDueDate(month: string): string {
  const [y, m] = month.split('-').map(Number);
  return m === 3 ? `${y}-04-30` : toIso(new Date(y, m, 7));
}

export interface AlertOptions {
  challans?: TdsChallan[];
  tallyMode?: 'none' | 'xml_file' | 'bridge';
  creditDaysOf?: (e: Expense) => number;
}

export function buildAlerts(expenses: Expense[], payments: Payment[], today: string, opts: AlertOptions = {}): Notification[] {
  const out: Notification[] = [];
  const live = expenses.filter((e) => e.status !== 'rejected' && e.status !== 'draft');
  const terms = opts.creditDaysOf ?? (() => 30);

  for (const e of live) {
    const due = outstanding(e, payments);
    if (due <= 0) continue;
    const age = daysBetween(e.invoiceDate, today);
    const late = daysBetween(dueDate(e, terms(e)), today);
    if (age > 180 && e.itcEligible) {
      out.push({ id: `itc-${e.id}`, clientId: e.clientId, kind: 'itc_180', severity: 'danger',
        title: `ITC reversal: ${e.vendorName} unpaid ${age} days`,
        body: `Bill ${e.invoiceNo ?? ''} — ${fmtInr(due)} unpaid beyond 180 days. ITC must be reversed until paid.`,
        tTitle: 'ITC reversal: {vendor} unpaid {days} days', tBody: 'Bill {no} — {amount} unpaid beyond 180 days. ITC must be reversed until paid.',
        vars: { vendor: e.vendorName, days: age, no: e.invoiceNo ?? '', amount: fmtInr(due) } });
    } else if (late > 0) {
      out.push({ id: `due-${e.id}`, clientId: e.clientId, kind: 'payment_overdue_30', severity: late > 30 ? 'danger' : 'warn',
        title: `${e.vendorName}: ${fmtInr(due)} overdue by ${late} days`,
        body: `Bill ${e.invoiceNo ?? ''} dated ${e.invoiceDate} · ${age} days old`,
        tTitle: '{vendor}: {amount} overdue by {late} days', tBody: 'Bill {no} dated {date} · {days} days old',
        vars: { vendor: e.vendorName, amount: fmtInr(due), late, no: e.invoiceNo ?? '', date: e.invoiceDate, days: age } });
    }
  }

  // TDS per month: bills (what is still due on them) + advances (in the month paid)
  const tdsByMonth = new Map<string, number>();
  for (const t of tdsEntries(live, payments)) tdsByMonth.set(t.month, round2((tdsByMonth.get(t.month) ?? 0) + t.tds));
  for (const [k, amt] of tdsByMonth) {
    const paid = round2((opts.challans ?? []).filter((c) => c.month === k).reduce((s, c) => s + c.amount, 0));
    if (paid >= amt) continue;
    const due = tdsDueDate(k);
    const left = daysBetween(today, due);
    if (left >= -60 && left <= 10) {
      out.push({ id: `tds-${k}`, kind: 'tds_due', severity: left < 0 ? 'danger' : 'warn', dueOn: due,
        title: `TDS ${fmtInr(round2(amt - paid))} for ${monthName(k)} ${left < 0 ? 'overdue' : `due in ${left} days`}`,
        body: paid > 0 ? `Challans recorded ${fmtInr(paid)} of ${fmtInr(amt)} — balance unpaid.` : 'Pay the challan, then snap or upload the challan receipt in TDS.',
        tTitle: left < 0 ? 'TDS {amount} for {month} overdue' : 'TDS {amount} for {month} due in {left} days',
        tBody: paid > 0 ? 'Challans recorded {paid} of {total} — balance unpaid.' : 'Pay the challan, then snap or upload the challan receipt in TDS.',
        vars: { amount: fmtInr(round2(amt - paid)), month: monthName(k), left, paid: fmtInr(paid), total: fmtInr(amt) } });
    }
  }

  const day = Number(today.slice(8, 10));
  if (day >= 14 && day <= 20) {
    out.push({ id: `reco-${today.slice(0, 7)}`, kind: 'gst_reco', severity: 'info',
      title: 'GSTR-2B ready — monthly reconciliation due', body: 'Review mismatches before filing GSTR-3B.',
      tTitle: 'GSTR-2B ready — monthly reconciliation due', tBody: 'Review mismatches before filing GSTR-3B.' });
  }

  if (opts.tallyMode && opts.tallyMode !== 'none' && day >= 18) {
    const d = new Date(today + 'T00:00:00'); d.setDate(1); d.setMonth(d.getMonth() - 1);
    const prev = toIso(d).slice(0, 7);
    const pending = live.filter((e) => monthKey(e.invoiceDate) <= prev && e.status !== 'posted');
    if (pending.length) {
      const lateTally = day > 25;
      out.push({ id: `tally-${prev}`, kind: 'tally_posting', severity: lateTally ? 'danger' : 'warn',
        title: `${pending.length} bill(s) up to ${monthName(prev)} not yet posted to Tally${lateTally ? ' — 25th deadline passed' : ''}`,
        body: `${pending.filter((e) => e.status === 'submitted').length} still awaiting CA review; post the rest by the 25th.`,
        tTitle: lateTally ? '{n} bill(s) up to {month} not yet posted to Tally — 25th deadline passed' : '{n} bill(s) up to {month} not yet posted to Tally',
        tBody: '{r} still awaiting CA review; post the rest by the 25th.',
        vars: { n: pending.length, month: monthName(prev), r: pending.filter((e) => e.status === 'submitted').length } });
    }
  }
  return out;
}
