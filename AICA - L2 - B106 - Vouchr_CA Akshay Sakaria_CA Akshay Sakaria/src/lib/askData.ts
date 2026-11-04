// G — "Ask your data": the fixed, read-only queries. AI only picks one of these and its filters (shown to the user, editable);
// every number on screen is calculated HERE from the records — never by AI.
import type { CostCentre, Expense, ExpenseHead, PayMode, Payment } from '../data/types';
import { outstanding } from './alerts';
import { round2 } from './money';

export const ASK_QUERIES = ['spend_total', 'top_vendors', 'dues', 'tds_total', 'itc_total', 'payments_total', 'bill_count'] as const;
export type AskQuery = (typeof ASK_QUERIES)[number];
export const ASK_LABEL: Record<AskQuery, string> = {
  spend_total: 'Spend (taxable value)', top_vendors: 'Top vendors by bill value', dues: 'Unpaid dues by vendor', tds_total: 'TDS deducted',
  itc_total: 'ITC available', payments_total: 'Payments made', bill_count: 'Number of bills'
};
export interface AskFilters { from?: string; to?: string; headId?: string; centreId?: string; vendor?: string; mode?: PayMode }
export interface AskAnswer { value: number; unit: 'inr' | 'count'; rows: { label: string; value: number }[]; basedOn: number }

export function runAsk(q: AskQuery, f: AskFilters, data: { expenses: Expense[]; payments: Payment[]; heads: ExpenseHead[]; centres: CostCentre[] }): AskAnswer {
  const inRange = (d: string) => (!f.from || d >= f.from) && (!f.to || d <= f.to);
  const bills = data.expenses.filter((e) => e.status !== 'draft' && e.status !== 'rejected' && inRange(e.invoiceDate)
    && (!f.headId || e.headId === f.headId) && (!f.centreId || e.costCentreId === f.centreId) && (!f.vendor || e.vendorName === f.vendor));
  const sum = (xs: number[]) => round2(xs.reduce((a, b) => a + b, 0));
  const group = (pairs: [string, number][]) => [...pairs.reduce((m, [k, v]) => m.set(k, (m.get(k) ?? 0) + v), new Map<string, number>())]
    .map(([label, value]) => ({ label, value: round2(value) })).sort((a, b) => b.value - a.value);
  switch (q) {
    case 'spend_total': return { value: sum(bills.map((e) => e.taxableValue)), unit: 'inr', rows: group(bills.map((e) => [data.heads.find((h) => h.id === e.headId)?.name ?? 'Unclassified', e.taxableValue])).slice(0, 8), basedOn: bills.length };
    case 'top_vendors': { const rows = group(bills.map((e) => [e.vendorName, e.totalAmount])).slice(0, 10); return { value: sum(rows.map((r) => r.value)), unit: 'inr', rows, basedOn: bills.length }; }
    case 'dues': { const rows = group(bills.map((e) => [e.vendorName, outstanding(e, data.payments)])).filter((r) => r.value > 0); return { value: sum(rows.map((r) => r.value)), unit: 'inr', rows, basedOn: bills.length }; }
    case 'tds_total': return { value: sum(bills.map((e) => e.tdsAmount)), unit: 'inr', rows: group(bills.filter((e) => e.tdsAmount).map((e) => [e.tdsCode ?? '—', e.tdsAmount])), basedOn: bills.length };
    case 'itc_total': return { value: sum(bills.filter((e) => e.itcEligible).map((e) => e.cgst + e.sgst + e.igst)), unit: 'inr', rows: [], basedOn: bills.length };
    case 'bill_count': return { value: bills.length, unit: 'count', rows: [], basedOn: bills.length };
    case 'payments_total': {
      const ps = data.payments.filter((p) => inRange(p.paidOn) && (!f.mode || p.mode === f.mode) && (!f.vendor || p.vendorName === f.vendor));
      return { value: sum(ps.map((p) => p.amount)), unit: 'inr', rows: group(ps.map((p) => [p.mode.toUpperCase(), p.amount])), basedOn: ps.length };
    }
  }
}
