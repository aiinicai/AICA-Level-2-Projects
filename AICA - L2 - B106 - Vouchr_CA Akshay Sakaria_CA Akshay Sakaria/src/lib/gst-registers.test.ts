// RCM time of supply and the 180-day ITC register. Invented names and numbers.
import { describe, expect, it } from 'vitest';
import { itcRegister, rcmLiability } from './gstRegisters';
import type { Expense, Payment, RcmRule } from '../data/types';

const rules = [{ code: 'GTA', supply: 'services' }, { code: 'CASHEW', supply: 'goods' }] as RcmRule[];
const rcmBill = (over: Partial<Expense> = {}) => ({ id: 'r1', clientId: 'c1', vendorName: 'Sample Roadlines', invoiceNo: 'LR-1', invoiceDate: '2026-08-01', status: 'approved',
  taxableValue: 40000, cgst: 0, sgst: 0, igst: 0, totalAmount: 40000, tdsAmount: 0, rcmApplicable: true, rcmCode: 'GTA', rcmTax: 2000, itcEligible: true, ...over }) as Expense;
const pay = (paidOn: string, expenseId: string, amount: number) => ({ id: paidOn + expenseId, paidOn, amount, allocations: [{ expenseId, amount }] }) as unknown as Payment;

describe('RCM: when the GST is due', () => {
  it('services, paid before 60 days → due on the payment date', () => {
    const r = rcmLiability([rcmBill()], [pay('2026-08-20', 'r1', 40000)], rules, '2026-11-03');
    expect(r.map((x) => [x.date, x.amount, x.basis])).toEqual([['2026-08-20', 2000, 'payment']]);
  });
  it('services, unpaid → the day after 60 days from the invoice (01 Aug → 01 Oct)', () => {
    expect(rcmLiability([rcmBill()], [], rules, '2026-11-03').map((x) => [x.date, x.basis])).toEqual([['2026-10-01', 'after_60_days']]);
  });
  it('half paid in time → half on the payment date, the rest on day 61', () => {
    const r = rcmLiability([rcmBill()], [pay('2026-08-10', 'r1', 20000)], rules, '2026-11-03');
    expect(r.map((x) => [x.date, x.amount])).toEqual([['2026-08-10', 1000], ['2026-10-01', 1000]]);
  });
  it('payment after day 61 does not move the date', () =>
    expect(rcmLiability([rcmBill()], [pay('2026-10-20', 'r1', 40000)], rules, '2026-11-03').map((x) => x.date)).toEqual(['2026-10-01']));
  it('goods → day after 30 days, marked "receipt date not recorded"', () => {
    const r = rcmLiability([rcmBill({ rcmCode: 'CASHEW' })], [], rules, '2026-11-03');
    expect(r.map((x) => [x.date, x.basis, x.receiptUnknown])).toEqual([['2026-09-01', 'after_30_days', true]]);
  });
  it('future date is shown as upcoming', () => expect(rcmLiability([rcmBill({ invoiceDate: '2026-10-20' })], [], rules, '2026-11-03')[0].upcoming).toBe(true));
});

describe('ITC 180-day register', () => {
  const b = { id: 'e1', clientId: 'c1', vendorName: 'Sample Traders', invoiceNo: 'ST/1', invoiceDate: '2026-04-01', status: 'approved', taxableValue: 10000, cgst: 900, sgst: 900, igst: 0,
    totalAmount: 11800, tdsAmount: 0, rcmApplicable: false, rcmTax: 0, itcEligible: true } as Expense;
  it('unpaid at day 180 → reverse all of it in the month the 180 days end', () => {
    const [r] = itcRegister([b], [], [], '2026-11-03');
    expect([r.day180, r.reverseAmount, r.reverseMonth, r.status]).toEqual(['2026-09-28', 1800, '2026-09', 'reverse']);
  });
  it('half paid by day 180 → reverse half', () => expect(itcRegister([b], [pay('2026-06-01', 'e1', 5900)], [], '2026-11-03')[0].reverseAmount).toBe(900));
  it('paid in time → no reversal', () => expect(itcRegister([b], [pay('2026-06-01', 'e1', 11800)], [], '2026-11-03')[0].status).toBe('paid_in_time'));
  it('reversed, later paid → re-claim', () => {
    const rec = [{ id: 'x', clientId: 'c1', expenseId: 'e1', amount: 1800, reversedIn: '2026-09', by: 'ca', at: '' }];
    expect(itcRegister([b], [], rec, '2026-11-03')[0].status).toBe('reversed');
    const r = itcRegister([b], [pay('2026-10-15', 'e1', 11800)], rec, '2026-11-03')[0];
    expect([r.status, r.reclaimable]).toEqual(['reclaim', 1800]);
    expect(itcRegister([b], [pay('2026-10-15', 'e1', 11800)], [{ ...rec[0], reclaimedAmount: 1800, reclaimedIn: '2026-10' }], '2026-11-03')[0].status).toBe('reclaimed');
  });
  it('reverse-charge bills are outside this rule', () => expect(itcRegister([{ ...b, rcmApplicable: true }], [], [], '2026-11-03')).toEqual([]));
  it('TDS deducted counts as paid', () =>
    expect(itcRegister([{ ...b, tdsAmount: 200 }], [pay('2026-06-01', 'e1', 11600)], [], '2026-11-03')[0].status).toBe('paid_in_time'));
});
