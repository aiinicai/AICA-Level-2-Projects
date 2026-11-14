// Travel-portal (non-GST part) and section 9(5) bills — layouts from real test invoices, with INVENTED names and numbers.
import { describe, expect, it } from 'vitest';
import { parseInvoiceText } from './extract';
import { voucherLines } from './tallyXml';
import { riskCheck } from './anomaly';
import { gstinCheckChar } from './validators';
import { TASKS } from '../../supabase/functions/_shared/ai/tasks.ts';
import type { Client, Expense, ExpenseHead, Vendor } from '../data/types';

const g = (s: string) => s + gstinCheckChar(s);
const PORTAL = g('06AAKCS4821M1Z'), APP = g('07AAKCU6223H1Z');

describe('travel portal bills: part of the total has no GST on this bill', () => {
  it('flight: fare printed on its own line is the non-GST part; arithmetic must agree', () => {
    const t = ['SAMPLE TRAVEL (INDIA) PRIVATE LIMITED', `GSTIN ${PORTAL}`, 'Invoice No. TP0001', 'Date 01 Jul 2025',
      '*Fare Charges (including applicable flight taxes collected on behalf of airline) ₹2715.0', 'Service Fees ₹135.59', 'CGST @9% ₹12.2', 'SGST @9% ₹12.2', 'Grand Total ₹2875.0'].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ totalAmount: 2875, taxAmount: 24.4, gstRatePct: 18, nonTaxable: 2715 });
  });
  it('rail: amount printed on the line above its label, plus a second pass-through fee', () => {
    const t = ['SAMPLE TRAVEL (INDIA) PRIVATE LIMITED', `GSTIN ${PORTAL}`, '₹1425.0', '*Rail Fare', '(Inclusive of applicable taxes)',
      '*Convenience fees of rail operator (Including GST)   ₹35.4', 'Effective Service Fees*', '₹33.9', 'CGST @9%   ₹3.05', 'SGST @9%   ₹3.05', 'Grand Total   ₹1500.4'].join('\n');
    expect(parseInvoiceText(t).nonTaxable).toBe(1460.4);
  });
  it('never guesses: no non-GST part when the numbers do not agree', () => {
    const t = ['SAMPLE STORE', `GSTIN ${PORTAL}`, 'Fare charges ₹500.00', 'CGST @9% ₹90.00', 'SGST @9% ₹90.00', 'Grand Total ₹1180.00'].join('\n');
    expect(parseInvoiceText(t).nonTaxable).toBeUndefined();
  });
  it('Tally voucher puts the non-GST part on the expense ledger and still balances', () => {
    const e = { vendorName: 'Sample Travel', invoiceNo: 'TP0001', taxableValue: 135.59, nonTaxableAmount: 2715, cgst: 12.2, sgst: 12.2, igst: 0, totalAmount: 2875, tdsAmount: 0, itcEligible: true, rcmApplicable: false, rcmTax: 0 } as Expense;
    const L = { inputCgst: 'Input CGST', inputSgst: 'Input SGST', inputIgst: 'Input IGST', roundOff: 'Round Off', rcmInput: 'RCM In', rcmOutput: 'RCM Out', tdsPayable: 'TDS' };
    const lines = voucherLines(e, { tallyLedger: 'Travelling Expenses' } as ExpenseHead, L as never);
    expect(lines.find((l) => l.ledger === 'Travelling Expenses')!.amount).toBe(2850.59);
    expect(Math.round(lines.reduce((s, l) => s + l.amount, 0) * 100)).toBe(0); // debits = credits
  });
});

describe('section 9(5) — GST paid by the e-commerce operator', () => {
  it('ride bill: ECO named with its GSTIN; total IGST preferred over the first item line', () => {
    const t = ['Tax Invoice', 'Invoice issued by Sample Rides India Private Limited on behalf of: DRIVER', 'Invoice number: R0001', 'Invoice date: 10 Sept 2025',
      'Ride fare 1 IGST 5% ₹ 29.08 ₹ 581.65', 'Total net amount ₹ 766.65', 'Total IGST 5% ₹ 38.33', 'Total amount payable ₹ 804.98', `Details of ECO under GST: Sample Rides / GST: ${APP}`].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ ecoPaysTax: true, ecoGstin: APP, taxAmount: 38.33, totalAmount: 804.98 });
    expect(parseInvoiceText(t).nonTaxable).toBeUndefined();
  });
  it('food-app receipt: "Tax to be paid under section 9(5) by Eco"', () => {
    const t = ['Sample Sweets', `GSTIN : ${PORTAL}`, 'Date: 18/03/26', 'Bill No.: 255726', 'CGST 2.5% 18.25', 'SGST 2.5% 18.25', 'Grand Total ₹766.00', 'Tax to be paid under section 9(5) by Eco'].join('\n');
    expect(parseInvoiceText(t)).toMatchObject({ ecoPaysTax: true, totalAmount: 766 });
  });
  it('risk check: no "GST without GSTIN" alarm when the app paid the tax; credit on a 9(5) bill is flagged for the CA', () => {
    const v: Vendor = { id: 'v', clientId: 'c', name: 'Driver', gstRegistered: false };
    const e = { id: 'e1', clientId: 'c', vendorId: 'v', vendorName: 'Driver', invoiceDate: '2026-10-01', status: 'submitted', taxableValue: 766.65, cgst: 0, sgst: 0, igst: 38.33, totalAmount: 804.98, tdsAmount: 0, ecoPaysTax: true, itcEligible: true } as Expense;
    const codes = riskCheck([e], [v], { id: 'c', stateCode: '27' } as Client, []).map((f) => f.code);
    expect(codes).not.toContain('gst_without_gstin');
    expect(codes).toContain('eco_itc');
  });
  it('AI: totals check includes the non-GST part (no false "doesn\'t add up")', () => {
    const F = (v: unknown) => ({ value: v, certainty: 'certain', evidence: String(v) });
    const r = TASKS.read_bill.check({ vendor_name: F('Sample Travel'), vendor_gstin: F(PORTAL), invoice_no: F('TP0001'), invoice_date: F('2025-07-01'),
      taxable_value: F(135.59), cgst: F(12.2), sgst: F(12.2), igst: { value: null, certainty: 'not_found', evidence: '' }, total: F(2875), non_taxable_charges: F(2715),
      irn: { value: null, certainty: 'not_found', evidence: '' }, description: F('Air ticket'), eco_pays_tax: { value: null, certainty: 'not_found', evidence: '' }, eco_gstin: { value: null, certainty: 'not_found', evidence: '' } }, {}, '2026-11-02', { text: '', sources: [] });
    expect(r.doubts.filter((d) => /add up/.test(d))).toEqual([]);
  });
});
