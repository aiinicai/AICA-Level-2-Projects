// Auto-approval: every condition must hold; any doubt keeps the bill for the CA.
import { describe, expect, it } from 'vitest';
import { autoApproveDecision, inSample } from './autoApprove';
import type { Client, Expense } from '../data/types';

const on = { autoApprove: { enabled: true, maxAmount: 5000, samplePct: 0, minHistory: 3 } } as Client;
const b = (over: Partial<Expense> = {}) => ({ id: 'new1', clientId: 'c1', vendorId: 'v1', vendorName: 'Paper House', invoiceDate: '2026-11-01', status: 'submitted',
  taxableValue: 1000, cgst: 90, sgst: 90, igst: 0, totalAmount: 1180, tdsAmount: 0, rcmApplicable: false, rcmTax: 0, headId: 'h-stationery', itcEligible: true,
  fileId: 'local:1', createdAt: '', ...over }) as Expense;
const hist = [1, 2, 3].map((i) => b({ id: `old${i}`, status: 'approved', invoiceDate: `2026-0${i + 5}-01` }));

describe('auto-approval', () => {
  it('off by default → never', () => expect(autoApproveDecision(b(), {} as Client, hist, 0).approve).toBe(false));
  it('all conditions hold → approved, tax treatment copied from the vendor’s approved bills', () =>
    expect(autoApproveDecision(b(), on, hist, 0)).toMatchObject({ approve: true, patch: { headId: 'h-stationery', itcEligible: true } }));
  it.each([
    ['above the limit', b({ totalAmount: 6000, taxableValue: 6000, cgst: 0, sgst: 0 }), 'Above the auto-approval limit'],
    ['no image', b({ fileId: undefined }), 'No bill image'],
    ['TDS', b({ tdsAmount: 10 }), 'TDS applies'],
    ['RCM', b({ rcmApplicable: true }), 'Reverse charge applies'],
    ['past-dated', b({ isBackdated: true }), 'Past-dated entry'],
    ['head differs', b({ headId: 'h-other' }), 'Suggested head differs from the vendor’s approved bills'],
    ['totals do not add up', b({ totalAmount: 1300 }), 'Taxable + GST does not add up to the total']
  ])('%s → stays in the queue', (_label, bill, reason) => expect(autoApproveDecision(bill, on, hist, 0).reasons).toContain(reason));
  it('risk flags → stays', () => expect(autoApproveDecision(b(), on, hist, 1).approve).toBe(false));
  it('vendor with too few approved bills → stays', () => expect(autoApproveDecision(b(), on, hist.slice(0, 2), 0).reasons).toContain('Vendor has fewer approved bills than required'));
  it('vendor’s earlier bills treated differently → stays', () =>
    expect(autoApproveDecision(b(), on, [...hist.slice(0, 2), { ...hist[2], itcEligible: false }], 0).reasons).toContain('Vendor’s earlier bills were not treated the same way'));
  it('sampling is stable and roughly the chosen share', () => {
    expect(inSample('abc', 10)).toBe(inSample('abc', 10));
    const n = Array.from({ length: 2000 }, (_, i) => inSample(`bill-${i}`, 10)).filter(Boolean).length;
    expect(n).toBeGreaterThan(150); expect(n).toBeLessThan(250);
    expect(autoApproveDecision(b(), { autoApprove: { ...on.autoApprove!, samplePct: 100 } } as Client, hist, 0)).toMatchObject({ approve: false, sampled: true });
  });
});
