// Credit / debit notes from vendors. Invented names and numbers.
import { describe, expect, it } from 'vitest';
import { checkNote, noteAdjustFor, noteItcDelta, noteLines, reconcileNotes, vendorLevelBalance } from './vendorNotes';
import { outstanding } from './alerts';
import { parse2B } from './reco';
import { buildTallyXml } from './tallyXml';
import type { Expense, ExpenseHead, VendorNote } from '../data/types';

const bill = { id: 'e1', clientId: 'c1', vendorId: 'v1', vendorName: 'Sample Traders', invoiceNo: 'ST/10', invoiceDate: '2026-10-01', fyLabel: '2026-27', status: 'approved',
  taxableValue: 10000, cgst: 900, sgst: 900, igst: 0, totalAmount: 11800, tdsAmount: 0, itcEligible: true, headId: 'h1', rcmApplicable: false, rcmTax: 0 } as Expense;
const note = (over: Partial<VendorNote> = {}): VendorNote => ({ id: 'n1', clientId: 'c1', fyLabel: '2026-27', vendorId: 'v1', vendorName: 'Sample Traders', kind: 'credit', noteNo: 'CN-1',
  noteDate: '2026-10-10', expenseId: 'e1', reason: 'return', taxableValue: 1000, cgst: 90, sgst: 90, igst: 0, totalAmount: 1180, itcEligible: true, status: 'active', createdBy: 'u', createdAt: '', ...over });

describe('effect on the bill and ITC', () => {
  it('credit note reduces the balance; debit note raises it; cancelled notes do not count', () => {
    const notes = [note(), note({ id: 'n2', kind: 'debit', noteNo: 'DN-1', totalAmount: 590, taxableValue: 500, cgst: 45, sgst: 45 }), note({ id: 'n3', noteNo: 'CN-9', status: 'void' })];
    expect(noteAdjustFor('e1', notes)).toBe(-590);
    expect(outstanding({ ...bill, noteAdjust: -590 }, [])).toBe(11210);
    expect(noteItcDelta(notes)).toBe(-90); // −180 + 90
  });
  it('credit note larger than what is unpaid → negative balance (vendor owes us)', () =>
    expect(outstanding({ ...bill, noteAdjust: -1180 }, [{ id: 'p', allocations: [{ expenseId: 'e1', amount: 11800 }] } as never])).toBe(-1180));
  it('vendor-level notes are kept apart until linked', () =>
    expect(vendorLevelBalance('v1', [note({ expenseId: undefined }), note({ id: 'n2', noteNo: 'CN-2' })])).toBe(-1180));
});

describe('checks before saving', () => {
  const base = { ...note(), id: undefined } as unknown as VendorNote;
  it('a valid credit note passes', () => expect(checkNote(base, bill, [], []).errors).toEqual([]));
  it('cannot exceed the bill value', () => {
    const r = checkNote({ ...base, taxableValue: 12000, cgst: 0, sgst: 0, totalAmount: 12000 }, bill, [], []);
    expect(r.errors).toContain('Credit notes cannot exceed the bill value (₹{room} left)');
    expect(r.vars).toEqual({ room: 11800 });
  });
  it('totals must add up; CGST = SGST; tax type must match the bill', () => {
    expect(checkNote({ ...base, totalAmount: 1300 }, bill, [], []).errors).toContain('Taxable + GST differs from the note total by more than ₹1');
    expect(checkNote({ ...base, cgst: 100, sgst: 80 }, bill, [], []).errors).toContain('CGST and SGST must be equal');
    expect(checkNote({ ...base, cgst: 0, sgst: 0, igst: 180 }, bill, [], []).errors).toContain('The note’s tax type (IGST vs CGST + SGST) must match the bill');
  });
  it('no note dated before its bill; no duplicate number (written differently) in the same FY', () => {
    expect(checkNote({ ...base, noteDate: '2026-09-01' }, bill, [], []).errors).toContain('A note cannot be dated before the bill it corrects');
    expect(checkNote({ ...base, noteNo: 'cn/1' }, bill, [], [note()]).errors).toContain('This note number is already recorded for this vendor in this financial year');
  });
  it('bill with TDS → marked for the CA, not changed', () => expect(checkNote(base, { ...bill, tdsAmount: 200 }, [], []).flags).toEqual(['tds_on_original']));
});

describe('Tally', () => {
  const L = { inputCgst: 'In CGST', inputSgst: 'In SGST', inputIgst: 'In IGST' };
  it('credit note: vendor Dr, expense and input GST Cr; balances', () => {
    const lines = noteLines(note(), { tallyLedger: 'Purchases' }, L, 'Sample Traders');
    expect(lines).toEqual([{ ledger: 'Purchases', amount: -1000 }, { ledger: 'In CGST', amount: -90 }, { ledger: 'In SGST', amount: -90 }, { ledger: 'Sample Traders', amount: 1180 }]);
  });
  it('XML: credit note as a Debit Note voucher, debit note as Journal', () => {
    const xml = buildTallyXml('Demo', [], [{ id: 'h1', tallyLedger: 'Purchases' } as ExpenseHead], { notes: [note(), note({ id: 'n2', kind: 'debit', noteNo: 'DN-1' })], allExpenses: [bill] });
    expect(xml).toContain('VCHTYPE="Debit Note"');
    expect(xml).toContain('VCHTYPE="Journal"');
  });
});

describe('GSTR-2B CDNR', () => {
  const json = { data: { docdata: {
    b2b: [{ ctin: '27AAAAA0000A1Z5', inv: [{ inum: 'ST/10', dt: '01-10-2026', val: 11800, txval: 10000, cgst: 900, sgst: 900, igst: 0 }] }],
    cdnr: [{ ctin: '27AAAAA0000A1Z5', trdnm: 'Sample Traders', nt: [{ ntnum: 'CN-1', typ: 'C', dt: '10-10-2026', val: 1180, txval: 1000, cgst: 90, sgst: 90, igst: 0 }, { ntnum: 'CN-7', typ: 'C', dt: '12-10-2026', txval: 100, cgst: 9, sgst: 9 }] }]
  } } };
  const lines = parse2B(json).lines;
  it('reads credit notes apart from invoices', () => expect(lines.map((l) => [l.docType, l.invoiceNo])).toEqual([['credit', 'CN-1'], ['credit', 'CN-7'], ['invoice', 'ST/10']]));
  it('matches books notes; a portal note not in books is listed', () => {
    const rows = reconcileNotes([note()], () => '27AAAAA0000A1Z5', lines);
    expect(rows.map((r) => [r.status, r.invoiceNo])).toEqual([['matched', 'CN CN-1'], ['missing_in_books', 'CN CN-7']]);
  });
});
