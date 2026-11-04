// Financial-year close: blockers, warnings and what carries forward (invented data).
import { describe, expect, it } from 'vitest';
import { carryForward, fyChecklist, fyMonths } from './fyClose';
import type { Client, Expense, Payment } from '../data/types';

const bill = (over: Partial<Expense>) => ({ id: 'e', clientId: 'c1', fyLabel: '2026-27', vendorName: 'Sample', invoiceNo: 'S/1', invoiceDate: '2026-06-01', status: 'posted',
  taxableValue: 1000, cgst: 0, sgst: 0, igst: 0, totalAmount: 1000, tdsAmount: 0, rcmApplicable: false, rcmTax: 0, itcEligible: false, createdAt: '', ...over }) as Expense;
const client = { tallyMode: 'xml_file' } as Client;

describe('FY close', () => {
  it('months of the year run April to March', () => expect([fyMonths('2026-27')[0], fyMonths('2026-27')[11]]).toEqual(['2026-04', '2027-03']));
  it('bills awaiting review and unposted bills block the close', () => {
    const c = fyChecklist('2026-27', { client, expenses: [bill({ id: 'a', status: 'submitted' }), bill({ id: 'b', status: 'approved' })], payments: [], challans: [], itcReversals: [] }, '2027-05-01');
    expect(c.filter((x) => x.blocker && x.count).map((x) => x.key)).toEqual(['review', 'tally_bills']);
  });
  it('without Tally, posting is not required', () =>
    expect(fyChecklist('2026-27', { client: { tallyMode: 'none' } as Client, expenses: [bill({ status: 'approved' })], payments: [], challans: [], itcReversals: [] }, '2027-05-01').find((x) => x.key === 'tally_bills')!.count).toBe(0));
  it('TDS not covered by challans is a warning, not a blocker', () => {
    const c = fyChecklist('2026-27', { client, expenses: [bill({ tdsAmount: 100, tdsCode: 'X', tdsRatePct: 10 })], payments: [], challans: [], itcReversals: [] }, '2027-05-01').find((x) => x.key === 'tds')!;
    expect([c.blocker, c.count, c.amount]).toEqual([false, 1, 100]);
  });
  it('open bills and unapplied advances carry forward; nothing is lost', () => {
    const pays = [{ id: 'p', vendorName: 'Sample', paidOn: '2027-02-01', amount: 1500, allocations: [{ expenseId: 'e', amount: 400 }] }] as unknown as Payment[];
    const rows = carryForward('2026-27', { expenses: [bill({})], payments: pays, vendorNotes: [] });
    expect(rows.map((r) => [r.kind, r.amount])).toEqual([['open_bill', 600], ['advance', 1100]]);
  });
});
