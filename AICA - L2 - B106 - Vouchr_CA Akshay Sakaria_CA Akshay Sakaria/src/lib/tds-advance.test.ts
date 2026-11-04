// TDS on advances: deduct at payment when it is earlier than the bill (s.393), never deduct twice. Invented names and amounts.
import { describe, expect, it } from 'vitest';
import { billTdsDue, grossUpTds, maxApplicable, previewApply, suggestAdvanceTds, tdsEntries, unusedAdvanceTds } from './tdsAdvance';
import { outstanding } from './alerts';
import { buildTallyXml, voucherLines } from './tallyXml';
import type { Expense, ExpenseHead, Payment, TdsRate, Vendor } from '../data/types';

const RATE: TdsRate = { code: '194C', description: 'Contractor', ratePct: 1, noPanRatePct: 20, thresholdSingle: 30000, thresholdAggregate: 100000, effectiveFrom: '2026-04-01', verified: true, sourceNote: 'test' };
const vendor = { id: 'v1', name: 'Sample Works', pan: 'AAAPS1234Q', panStatus: 'Operative' } as Vendor;
const bill = (over: Partial<Expense> = {}) => ({ id: 'e1', clientId: 'c1', vendorId: 'v1', vendorName: 'Sample Works', invoiceNo: 'SW/1', invoiceDate: '2026-10-20', fyLabel: '2026-27',
  status: 'approved', taxableValue: 100000, cgst: 0, sgst: 0, igst: 0, totalAmount: 100000, tdsCode: '194C', tdsRatePct: 1, tdsAmount: 1000, itcEligible: false, rcmApplicable: false, rcmTax: 0, ...over }) as Expense;
const advance = (over: Partial<Payment> = {}) => ({ id: 'p1', clientId: 'c1', vendorId: 'v1', vendorName: 'Sample Works', mode: 'bank', paidOn: '2026-09-10', amount: 99000,
  allocations: [], tdsOnAdvance: { code: '194C', ratePct: 1, amount: 1000 }, ...over }) as unknown as Payment;

describe('gross-up', () => {
  it('₹99,000 paid at 1% → TDS ₹1,000, vendor credited ₹1,00,000', () => expect(grossUpTds(99000, 1)).toBe(1000));
  it('no rate → no TDS', () => expect(grossUpTds(5000, 0)).toBe(0));
});

describe('applying a TDS-deducted advance to the bill', () => {
  it('the advance settles the bill fully; the bill deducts no TDS again', () => {
    const p = advance();
    expect(previewApply(bill(), [p], p, 99000)).toEqual({ credit: 1000, after: 0 });
    const applied = advance({ allocations: [{ expenseId: 'e1', amount: 99000, tdsCredit: 1000 }] });
    expect(outstanding(bill(), [applied])).toBe(0);
    expect(billTdsDue(bill(), [applied])).toBe(0);
    expect(unusedAdvanceTds(applied)).toBe(0);
  });
  it('bill bigger than the advance: only the remaining TDS is deducted on the bill', () => {
    const e = bill({ taxableValue: 150000, totalAmount: 150000, tdsAmount: 1500 });
    const applied = advance({ allocations: [{ expenseId: 'e1', amount: 99000, tdsCredit: 1000 }] });
    expect(billTdsDue(e, [applied])).toBe(500);
    expect(outstanding(e, [applied])).toBe(49500); // 1,50,000 − 99,000 cash − 1,000 TDS on advance − 500 TDS on bill
  });
  it('bill smaller than the advance: cash applied is cut so the bill is not overpaid', () => {
    const e = bill({ taxableValue: 50000, totalAmount: 50000, tdsAmount: 500 });
    const p = advance();
    const cash = maxApplicable(e, [p], p, 99000);
    expect(cash).toBe(49500);
    expect(previewApply(e, [p], p, cash)).toEqual({ credit: 500, after: 0 });
  });
  it('advance without TDS works as before', () => {
    const p = advance({ tdsOnAdvance: undefined, amount: 40000 });
    expect(previewApply(bill(), [p], p, 40000)).toEqual({ credit: 0, after: 59000 });
  });
});

describe('TDS register and challan months', () => {
  it('advance TDS in the month paid; bill shows only TDS still due', () => {
    const e = bill({ taxableValue: 150000, totalAmount: 150000, tdsAmount: 1500 });
    const applied = advance({ allocations: [{ expenseId: 'e1', amount: 99000, tdsCredit: 1000 }] });
    const rows = tdsEntries([e], [applied]);
    expect(rows.map((r) => [r.kind, r.month, r.tds, r.base])).toEqual([['advance', '2026-09', 1000, 100000], ['bill', '2026-10', 500, 50000]]);
  });
  it('advance paid AFTER the bill: bill TDS stays in the bill month, advance month shows only the rest', () => {
    const e = bill({ invoiceDate: '2026-09-30', taxableValue: 42000, totalAmount: 42000, tdsAmount: 420 });
    const p = advance({ paidOn: '2026-11-03', amount: 50000, tdsOnAdvance: { code: '194C', ratePct: 1, amount: 505.05, base: 50505.05 }, allocations: [{ expenseId: 'e1', amount: 41580, tdsCredit: 420 }] });
    expect(tdsEntries([e], [p]).map((r) => [r.kind, r.month, r.tds, r.base])).toEqual([['bill', '2026-09', 420, 42000], ['advance', '2026-11', 85.05, 8505.05]]);
    expect(outstanding(e, [p])).toBe(0);
  });
  it('unapplied advance shows its exact base (cash + TDS)', () => {
    const p = advance({ amount: 50000, tdsOnAdvance: { code: '194C', ratePct: 1, amount: 505.05, base: 50505.05 } });
    expect(tdsEntries([], [p])[0].base).toBe(50505.05);
  });
  it('fully covered bill does not appear twice', () => {
    const applied = advance({ allocations: [{ expenseId: 'e1', amount: 99000, tdsCredit: 1000 }] });
    expect(tdsEntries([bill()], [applied]).map((r) => r.kind)).toEqual(['advance']);
  });
});

describe('suggestion — the app suggests, the CA decides', () => {
  it('above the single-payment limit → deduct, section taken from earlier bills', () => {
    const s = suggestAdvanceTds(vendor, [bill()], [], [RATE], 40000, '2026-11-01', '2026-27');
    expect(s).toMatchObject({ code: '194C', ratePct: 1, applies: true });
  });
  it('below both limits → not needed yet', () => {
    const s = suggestAdvanceTds(vendor, [bill({ taxableValue: 10000 })], [], [RATE], 5000, '2026-11-01', '2026-27');
    expect(s.applies).toBe(false);
  });
  it('PAN missing → higher rate', () => {
    expect(suggestAdvanceTds({ ...vendor, pan: undefined }, [bill()], [], [RATE], 40000, '2026-11-01', '2026-27').ratePct).toBe(20);
  });
  it('no section known → no guess', () => {
    const s = suggestAdvanceTds(vendor, [], [], [RATE], 40000, '2026-11-01', '2026-27');
    expect(s).toMatchObject({ applies: false, ratePct: 0 });
    expect(s.code).toBeUndefined();
  });
});

describe('Tally', () => {
  const L = { inputCgst: 'In CGST', inputSgst: 'In SGST', inputIgst: 'In IGST', roundOff: 'Round Off', rcmInput: 'RCM In', rcmOutput: 'RCM Out', tdsPayable: 'TDS Payable' };
  it('bill voucher posts only the TDS still due and balances', () => {
    const e = bill({ taxableValue: 150000, totalAmount: 150000, tdsAmount: 1500 });
    const lines = voucherLines(e, { tallyLedger: 'Contract Work' } as ExpenseHead, L as never, 'Sample Works', undefined, 1000);
    expect(lines.find((l) => l.ledger === 'TDS Payable')!.amount).toBe(-500);
    expect(lines.find((l) => l.ledger === 'Sample Works')!.amount).toBe(-149500);
    expect(Math.round(lines.reduce((s, l) => s + l.amount, 0) * 100)).toBe(0);
  });
  it('fully covered bill: no TDS line on the bill voucher', () => {
    const lines = voucherLines(bill(), { tallyLedger: 'Contract Work' } as ExpenseHead, L as never, 'Sample Works', undefined, 1000);
    expect(lines.some((l) => l.ledger === 'TDS Payable')).toBe(false);
  });
  it('advance payment voucher: vendor Dr cash + TDS, bank Cr cash, TDS payable Cr TDS', () => {
    const xml = buildTallyXml('Demo Co', [], [], { payments: [advance()] });
    const amounts = [...xml.matchAll(/<LEDGERNAME>([^<]+)<\/LEDGERNAME>[\s\S]*?<AMOUNT>(-?[\d.]+)<\/AMOUNT>/g)].map((m) => [m[1], Number(m[2])]);
    expect(amounts.length).toBe(3);
    expect(Math.round(amounts.reduce((s, a) => s + (a[1] as number), 0) * 100)).toBe(0); // balances
    expect(amounts.map((a) => Math.abs(a[1] as number)).sort((a, b) => a - b)).toEqual([1000, 99000, 100000]);
  });
});
