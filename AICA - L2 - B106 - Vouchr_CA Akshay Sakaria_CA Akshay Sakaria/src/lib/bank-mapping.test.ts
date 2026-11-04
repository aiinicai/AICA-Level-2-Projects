// Bank statements in different layouts (invented rows).
import { describe, expect, it } from 'vitest';
import { applyMapping, guessMapping, mappingFromNames, namesFromMapping, parseCsv } from './bank';

describe('bank statement columns', () => {
  it('separate Withdrawal / Deposit columns are recognised', () => {
    const rows = parseCsv('Statement of account\nTxn Date,Narration,Chq/Ref No,Withdrawal Amt,Deposit Amt\n05/10/2026,NEFT-SAMPLE TRADERS,N123,"1,180.00",\n06/10/2026,INTEREST,,,"25.00"\n');
    const m = guessMapping(rows)!;
    expect(applyMapping(rows, m).map((r) => [r.date, r.debit, r.credit, r.ref])).toEqual([['2026-10-05', 1180, 0, 'N123'], ['2026-10-06', 0, 25, undefined]]);
  });
  it('one Amount column + Dr/Cr column', () => {
    const rows = parseCsv('Date,Description,Amount,Dr/Cr\n05-10-2026,UPI/PAPER HOUSE,590,DR\n06-10-2026,REFUND,100,CR\n07-10-2026,??,50,X\n');
    const out = applyMapping(rows, guessMapping(rows)!);
    expect(out.map((r) => [r.debit, r.credit, r.mode])).toEqual([[590, 0, 'upi'], [0, 100, 'bank']]); // unknown marker skipped, not guessed
  });
  it('one Amount column without Dr/Cr → not guessed; the person chooses the sign rule', () => {
    const rows = parseCsv('Date,Details,Amount\n05/10/2026,NEFT OUT,-500\n06/10/2026,IN,200\n');
    expect(guessMapping(rows)).toBeUndefined();
    expect(applyMapping(rows, { headerRow: 0, date: 0, narration: 1, amount: 2, minusIsDebit: true }).map((r) => [r.debit, r.credit])).toEqual([[500, 0], [0, 200]]);
  });
  it('columns remembered by header name work on the next statement of that bank', () => {
    const rows = parseCsv('Date,Details,Amount\n05/10/2026,NEFT OUT,-500\n');
    const saved = namesFromMapping(rows, { headerRow: 0, date: 0, narration: 1, amount: 2, minusIsDebit: true });
    const next = parseCsv('Bank X\n\nDate,Details,Amount\n09/10/2026,CHQ 0042,-750\n');
    expect(applyMapping(next, mappingFromNames(next, saved)!).map((r) => [r.date, r.debit, r.mode])).toEqual([['2026-10-09', 750, 'cheque']]);
  });
});
