// Duplicate bills — the check that stops a bill being recorded (and paid) twice.
import { describe, expect, it } from 'vitest';
import { alikeIn, dupIn, normBillNo } from '../data/store';
import type { Expense, Vendor } from '../data/types';

const vendors: Vendor[] = [{ id: 'v1', clientId: 'c', name: 'Sharma Traders', gstin: '27AAKFS4821M1ZQ', gstRegistered: true }];
const bill = (o: Partial<Expense>): Expense => ({ id: 'old', clientId: 'c', fyLabel: '2026-27', vendorId: 'v1', vendorName: 'Sharma Traders', invoiceNo: 'INV-0045',
  invoiceDate: '2026-10-05', totalAmount: 1180, status: 'submitted', createdAt: '2026-10-05T10:00:00Z', ...o } as Expense);
const existing = [bill({})];

describe('duplicate bills', () => {
  it('bill numbers are compared the way people write them', () => {
    expect(normBillNo('INV-0045')).toBe(normBillNo('inv/45'));
    expect(normBillNo('INV 045')).toBe(normBillNo('INV-45'));
    expect(normBillNo('SH/1182')).not.toBe(normBillNo('SH/1190'));
    // found in live testing: separators must not merge number groups before zeros are dropped
    expect(normBillNo('ka-26-0164')).toBe(normBillNo('KA/26/164'));
    expect(normBillNo('KA/26/164')).not.toBe(normBillNo('KA/2/6164')); // different bills must not merge
    expect(normBillNo('INV45')).toBe(normBillNo('INV-0045'));
  });
  it('same vendor typed differently but same GSTIN → caught', () => {
    expect(dupIn(existing, vendors, 'c', { vendorName: 'SHARMA TRADERS PVT LTD', vendorGstin: '27AAKFS4821M1ZQ', invoiceNo: 'INV/45', fy: '2026-27' })?.id).toBe('old');
  });
  it('same vendor record → caught even if the name on this bill is different', () => {
    expect(dupIn(existing, vendors, 'c', { vendorId: 'v1', vendorName: 'Sharma', invoiceNo: 'inv-0045', fy: '2026-27' })?.id).toBe('old');
  });
  it('same bill number in the NEXT financial year is a new bill (serials restart each FY)', () => {
    expect(dupIn(existing, vendors, 'c', { vendorId: 'v1', vendorName: 'Sharma Traders', invoiceNo: 'INV-0045', fy: '2027-28' })).toBeUndefined();
  });
  it('same bill number from a DIFFERENT vendor is not a duplicate', () => {
    expect(dupIn(existing, vendors, 'c', { vendorName: 'Verma Stores', vendorGstin: '27AABCV1234K1ZZ', invoiceNo: 'INV-0045', fy: '2026-27' })).toBeUndefined();
  });
  it('the same photo/file is always a duplicate; a returned (rejected) bill is not', () => {
    expect(dupIn([bill({ imageHash: 'abc' })], vendors, 'c', { vendorName: 'x', imageHash: 'abc' })?.id).toBe('old');
    expect(dupIn([bill({ status: 'rejected' })], vendors, 'c', { vendorId: 'v1', vendorName: 'Sharma Traders', invoiceNo: 'INV-0045', fy: '2026-27' })).toBeUndefined();
  });
  it('look-alike (same vendor, date, amount) also recognises the vendor by GSTIN', () => {
    expect(alikeIn(existing, vendors, 'c', { vendorName: 'SHARMA TRADERS PVT LTD', vendorGstin: '27AAKFS4821M1ZQ' }, '2026-10-05', 1180)?.id).toBe('old');
    expect(alikeIn(existing, vendors, 'c', { vendorName: 'SHARMA TRADERS PVT LTD' }, '2026-10-05', 1180)).toBeUndefined();
  });
});
