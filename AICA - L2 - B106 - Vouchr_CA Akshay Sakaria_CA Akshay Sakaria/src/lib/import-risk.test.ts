import { describe, expect, it } from 'vitest';
import type { Client, Expense, TdsRate, Vendor } from '../data/types';
import { gstRatesOn } from '../data/masters';
import { parseMode } from '../data/store';
import { datasetOf, mapGrid, parseCsv } from './importer';
import { benfordMad, riskCheck } from './anomaly';
import { gstinCheckChar } from './validators';

describe('GST 2.0 slabs', () => {
  it('old slabs before 22-09-2025, 5/18/40 from that day', () => {
    expect(gstRatesOn('2025-09-21')).toEqual([0, 5, 12, 18, 28]);
    expect(gstRatesOn('2025-09-22')).toEqual([0, 5, 18, 40]);
  });
});

describe('Excel import — reading', () => {
  it('parses quoted CSV with commas, quotes and CRLF', () => {
    expect(parseCsv('﻿a,b\r\n"x, y","say ""hi"""\r\n')).toEqual([['a', 'b'], ['x, y', 'say "hi"']]);
  });

  it('maps headings by alias, cleans dates and amounts', () => {
    const grid = [
      ['Party Name', 'Invoice Date', 'Taxable Amount', 'CGST', 'SGST', 'Invoice No', 'Something else'],
      ['Acme', '05-10-2026', '1,000.00', 90, 90, 101, 'x'],
      ['Beta', new Date(Date.UTC(2026, 9, 6)), 500, null, null, 'B-1', ''],
      ['Gamma', 46301, '₹ 250', '', '', '', ''],
      [null, '', '', '', '', '', '']
    ];
    const p = mapGrid(datasetOf('bills'), grid);
    expect(p.missing).toEqual([]);
    expect(p.unknown).toEqual(['Something else']);
    expect(p.rows).toHaveLength(3);
    expect(p.rows[0]).toMatchObject({ _row: 2, vendor: 'Acme', invoiceDate: '2026-10-05', taxable: 1000, cgst: 90, invoiceNo: '101' });
    expect(p.rows[1].invoiceDate).toBe('2026-10-06');
    expect(p.rows[2]).toMatchObject({ invoiceDate: '2026-10-06', taxable: 250 }); // Excel serial 46301 = 06-10-2026
  });

  it('reports missing required columns and unreadable cells', () => {
    expect(mapGrid(datasetOf('payments'), [['Vendor name', 'Amount']]).missing).toEqual(['Paid on', 'Mode']);
    const p = mapGrid(datasetOf('payments'), [['Vendor name', 'Amount', 'Paid on', 'Mode'], ['A', 'abc', '01-10-2026', 'Cash'], ['B', 10, '31-02-x', 'UPI']]);
    expect(p.rows).toHaveLength(0);
    expect(p.cellErrors.map((c) => c.row)).toEqual([2, 3]);
  });

  it('reads payment modes the way people write them', () => {
    expect(['NEFT', 'GPay', 'Chq', 'Petty cash', 'Credit card', 'RTGS', 'xyz'].map(parseMode)).toEqual(['bank', 'upi', 'cheque', 'cash', 'card', 'bank', undefined]);
  });
});

const client = { id: 'c', stateCode: '27' } as Client;
const gst = (s: string) => s + gstinCheckChar(s);
const vReg: Vendor = { id: 'v1', clientId: 'c', name: 'Reg', gstin: gst('27AAKFS4821M1Z'), gstRegistered: true, stateCode: '27' };
const vUnreg: Vendor = { id: 'v2', clientId: 'c', name: 'Unreg', gstRegistered: false };
const rates = [{ code: 'C', ratePct: 1, thresholdSingle: 30000, effectiveFrom: '2026-04-01', verified: true, description: '', sourceNote: '' }] as TdsRate[];
let n = 0;
const bill = (o: Partial<Expense>): Expense => ({
  id: `e${++n}`, clientId: 'c', fyLabel: '2026-27', vendorId: 'v1', vendorName: 'Reg', invoiceDate: '2026-10-01', entrySource: 'manual',
  grossAmount: 0, discount: 0, taxableValue: 1000, cgst: 0, sgst: 0, igst: 0, totalAmount: 1000, tdsAmount: 0, rcmApplicable: false, rcmTax: 0,
  status: 'submitted', isBackdated: false, createdBy: 'u', createdAt: '2026-10-01T00:00:00Z', ...o
});
const codes = (es: Expense[]) => riskCheck(es, [vReg, vUnreg], client, rates).map((f) => f.code);

describe('Bill risk check', () => {
  it('flags GST charged without GSTIN as high', () => {
    const f = riskCheck([bill({ vendorId: 'v2', cgst: 90, sgst: 90, totalAmount: 1180 })], [vReg, vUnreg], client, rates);
    expect(f[0]).toMatchObject({ code: 'gst_without_gstin', severity: 'high' });
  });
  it('flags 12% / 28% on bills after GST 2.0 but not before', () => {
    expect(codes([bill({ invoiceDate: '2026-10-01', cgst: 60, sgst: 60, totalAmount: 1120 })])).toContain('old_gst_slab');
    expect(codes([bill({ invoiceDate: '2025-08-01', cgst: 60, sgst: 60, totalAmount: 1120 })])).not.toContain('old_gst_slab');
  });
  it('flags the same bill number written differently', () => {
    expect(codes([bill({ invoiceNo: 'INV-001' }), bill({ invoiceNo: 'INV/001', invoiceDate: '2026-10-03' })])).toContain('bill_no_variant');
  });
  it('flags several bills just under the single-bill TDS limit in a week', () => {
    const es = [bill({ taxableValue: 18000, tdsCode: 'C', invoiceDate: '2026-10-01' }), bill({ taxableValue: 17000, invoiceDate: '2026-10-05' })];
    expect(codes(es)).toContain('tds_split');
    expect(codes([es[0], { ...es[1], invoiceDate: '2026-10-20' }])).not.toContain('tds_split');
  });
  it('ignores drafts and returned bills, and stays quiet on a clean bill', () => {
    expect(codes([bill({ vendorId: 'v2', cgst: 9, sgst: 9, status: 'draft' })])).toEqual([]);
    expect(codes([bill({ cgst: 90, sgst: 90, totalAmount: 1180, invoiceNo: 'A1' })])).toEqual([]);
  });
});

describe('Benford test', () => {
  it('needs 100 amounts; natural data conforms, uniform first digits do not', () => {
    expect(benfordMad([100, 200])).toBeUndefined();
    const natural: number[] = [];
    for (let d = 1; d <= 9; d++) for (let i = 0; i < Math.round(Math.log10(1 + 1 / d) * 1000); i++) natural.push(d * 1000 + i);
    expect(benfordMad(natural)!.mad).toBeLessThan(0.006);
    const uniform = Array.from({ length: 900 }, (_, i) => (Math.floor(i / 100) + 1) * 1000);
    expect(benfordMad(uniform)!.mad).toBeGreaterThan(0.015);
  });
});
