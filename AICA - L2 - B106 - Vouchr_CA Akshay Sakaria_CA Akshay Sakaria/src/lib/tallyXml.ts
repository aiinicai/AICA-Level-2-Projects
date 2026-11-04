// Builds a Tally import XML: Journal vouchers for approved expenses + Payment vouchers for payments.
// Tally sign convention (cross-checked with open-source Tally SDKs): debit = ISDEEMEDPOSITIVE Yes with a
// negative AMOUNT; credit = No with a positive AMOUNT. Ledger names must already exist in the client's Tally
// company. Test-import into a copy of each client's company before first live use.

import { tdsCreditFor } from './tdsAdvance';
import type { Expense, ExpenseHead, Payment, VendorNote } from '../data/types';
import { noteLines, REASON_LABEL } from './vendorNotes';
import { round2 } from './money';

export interface TallyLedgers {
  inputCgst: string;
  inputSgst: string;
  inputIgst: string;
  tdsPayable: string;
  rcmInput: string;
  rcmOutput: string;
  roundOff: string;
  cash: string;
  bank: string;
}

export const DEFAULT_LEDGERS: TallyLedgers = {
  inputCgst: 'Input CGST',
  inputSgst: 'Input SGST',
  inputIgst: 'Input IGST',
  tdsPayable: 'TDS Payable',
  rcmInput: 'Input GST (RCM)',
  rcmOutput: 'GST Payable (RCM)',
  roundOff: 'Round Off',
  cash: 'Cash',
  bank: 'Bank'
};

/** Bills may round the total to the rupee; up to this difference is booked to Round Off. */
export const ROUND_OFF_LIMIT = 1;

const esc = (s: string) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

interface Line {
  ledger: string;
  amount: number; // + debit, - credit
  costCentre?: string; // Tally cost centre (project / branch), on the expense line only
}

export function voucherLines(e: Expense, head: ExpenseHead, ledgers: TallyLedgers, partyLedger: string = e.vendorName, costCentre?: string, tdsCredit = 0): Line[] {
  const tds = round2(Math.max(0, e.tdsAmount - tdsCredit)); // TDS already deducted on an applied advance is not deducted again
  const gst = round2(e.cgst + e.sgst + e.igst);
  const itc = e.itcEligible === true;
  const other = round2(e.nonTaxableAmount ?? 0); // e.g. fare collected on behalf of the airline — no GST on this bill
  const lines: Line[] = [{ ledger: head.tallyLedger, amount: round2(e.taxableValue + other + (itc ? 0 : gst)), costCentre }];
  if (itc) {
    if (e.cgst) lines.push({ ledger: ledgers.inputCgst, amount: e.cgst });
    if (e.sgst) lines.push({ ledger: ledgers.inputSgst, amount: e.sgst });
    if (e.igst) lines.push({ ledger: ledgers.inputIgst, amount: e.igst });
  }
  const diff = round2(e.totalAmount - e.taxableValue - other - gst);
  if (diff !== 0) {
    if (Math.abs(diff) > ROUND_OFF_LIMIT) throw new Error(`${e.vendorName} ${e.invoiceNo ?? ''}: taxable + non-GST charges + GST differs from total by ₹${diff}`);
    lines.push({ ledger: ledgers.roundOff, amount: diff });
  }
  if (e.rcmApplicable && e.rcmTax > 0) {
    // self-assessed GST: liability always; ITC only when the credit is eligible
    lines.push({ ledger: itc ? ledgers.rcmInput : head.tallyLedger, amount: e.rcmTax });
    lines.push({ ledger: ledgers.rcmOutput, amount: -e.rcmTax });
  }
  if (tds) lines.push({ ledger: ledgers.tdsPayable, amount: -tds });
  lines.push({ ledger: partyLedger, amount: -round2(e.totalAmount - tds) });
  return lines;
}

function lineXml(l: Line): string {
  const debit = l.amount > 0;
  const amt = (-l.amount).toFixed(2);
  // Cost centre allocation (Tally "Primary Cost Category") — the ledger must have cost centres enabled in Tally
  const cc = l.costCentre
    ? `<CATEGORYALLOCATIONS.LIST><CATEGORY>Primary Cost Category</CATEGORY><ISDEEMEDPOSITIVE>${debit ? 'Yes' : 'No'}</ISDEEMEDPOSITIVE><COSTCENTREALLOCATIONS.LIST><NAME>${esc(l.costCentre)}</NAME><AMOUNT>${amt}</AMOUNT></COSTCENTREALLOCATIONS.LIST></CATEGORYALLOCATIONS.LIST>`
    : '';
  return `<ALLLEDGERENTRIES.LIST><LEDGERNAME>${esc(l.ledger)}</LEDGERNAME><ISDEEMEDPOSITIVE>${debit ? 'Yes' : 'No'}</ISDEEMEDPOSITIVE><AMOUNT>${amt}</AMOUNT>${cc}</ALLLEDGERENTRIES.LIST>`;
}

function merge(lines: Line[]): Line[] {
  const m = new Map<string, Line>();
  for (const l of lines) {
    const cur = m.get(l.ledger);
    m.set(l.ledger, { ledger: l.ledger, amount: round2((cur?.amount ?? 0) + l.amount), costCentre: cur?.costCentre ?? l.costCentre });
  }
  return [...m.values()].filter((l) => l.amount !== 0);
}

function voucher(type: 'Journal' | 'Payment' | 'Debit Note', date: string, ref: string, narration: string, lines: Line[]): string {
  const sum = round2(lines.reduce((s, l) => s + l.amount, 0));
  if (sum !== 0) throw new Error(`Voucher ${ref} does not balance (${sum})`);
  return `<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE="${type}" ACTION="Create"><DATE>${date.replace(/-/g, '')}</DATE><VOUCHERTYPENAME>${type}</VOUCHERTYPENAME><REFERENCE>${esc(ref)}</REFERENCE><NARRATION>${esc(narration)}</NARRATION>${lines.map(lineXml).join('')}</VOUCHER></TALLYMESSAGE>`;
}

export interface TallyOptions {
  payments?: Payment[];
  /** every payment of the client — needed to know TDS already deducted on advances applied to a bill */
  allPayments?: Payment[];
  allExpenses?: Expense[];
  /** Tally party ledger for a vendor (vendor master override, else the vendor name). */
  partyLedger?: (vendorId: string | undefined, name: string) => string;
  /** Tally cost centre name for a bill (project / branch). */
  costCentreOf?: (e: Expense) => string | undefined;
  /** Tally ledger the money left from (Cash, or the chosen bank account). */
  paymentLedger?: (p: Payment) => string;
  /** credit / debit notes from vendors. Credit note → Debit Note voucher (enable that voucher type in Tally); debit note → Journal. */
  notes?: VendorNote[];
  ledgers?: TallyLedgers;
}

export function buildTallyXml(company: string, expenses: Expense[], heads: ExpenseHead[], opts: TallyOptions = {}): string {
  const ledgers = opts.ledgers ?? DEFAULT_LEDGERS;
  const party = opts.partyLedger ?? ((_: string | undefined, n: string) => n);
  const payLedger = opts.paymentLedger ?? ((p: Payment) => (p.mode === 'cash' ? ledgers.cash : ledgers.bank));
  const all = opts.allExpenses ?? expenses;
  const vouchers = expenses.map((e) => {
    const head = heads.find((h) => h.id === e.headId);
    if (!head) throw new Error(`Expense ${e.invoiceNo ?? e.id} has no expense head`);
    const auto = `Bill ${e.invoiceNo ?? ''}${e.hsnSac ? ' HSN/SAC ' + e.hsnSac : ''}${e.rcmApplicable ? ' RCM' : ''}`.trim();
    const narration = e.narration ? `${e.narration} (${auto})` : `Vouchr ${auto}`;
    return voucher('Journal', e.invoiceDate, e.invoiceNo ?? e.id, narration, merge(voucherLines(e, head, ledgers, party(e.vendorId, e.vendorName), opts.costCentreOf?.(e), tdsCreditFor(e.id, opts.allPayments ?? opts.payments ?? []))));
  });
  for (const p of opts.payments ?? []) {
    const bills = p.allocations.map((a) => {
      const e = all.find((x) => x.id === a.expenseId);
      if (!e) throw new Error(`Payment ${p.ref ?? p.id} refers to an unknown bill`);
      return `${e.invoiceNo ?? e.id} ₹${a.amount}`;
    });
    const advance = round2(p.amount - p.allocations.reduce((s, a) => s + a.amount, 0));
    const narration = `Vouchr ${p.mode.toUpperCase()} ${p.ref ?? ''} — ${bills.join(', ') || 'advance'}${bills.length && advance > 0 ? `, advance ₹${advance}` : ''}`;
    const tds = p.tdsOnAdvance?.amount ?? 0; // TDS on the advance: vendor credited cash + TDS, TDS payable credited
    vouchers.push(voucher('Payment', p.paidOn, p.ref ?? p.id, tds ? `${narration} · TDS ₹${tds} (${p.tdsOnAdvance!.code})` : narration, [
      { ledger: party(p.vendorId, p.vendorName), amount: round2(p.amount + tds) },
      { ledger: payLedger(p), amount: -p.amount },
      ...(tds ? [{ ledger: ledgers.tdsPayable, amount: -tds }] : [])
    ]));
  }
  for (const n of opts.notes ?? []) {
    const bill = n.expenseId ? all.find((x) => x.id === n.expenseId) : undefined;
    const head = heads.find((h) => h.id === (bill?.headId ?? n.headId));
    if (!head) throw new Error(`Note ${n.noteNo} has no expense head`);
    const narration = `Vouchr ${n.kind === 'credit' ? 'credit' : 'debit'} note ${n.noteNo} — ${REASON_LABEL[n.reason]}${bill ? ` against bill ${bill.invoiceNo ?? ''}` : ''}${n.remark ? ` · ${n.remark}` : ''}`;
    vouchers.push(voucher(n.kind === 'credit' ? 'Debit Note' : 'Journal', n.noteDate, n.noteNo, narration, merge(noteLines(n, head, ledgers, party(n.vendorId, n.vendorName)))));
  }
  return `<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES><SVCURRENTCOMPANY>${esc(company)}</SVCURRENTCOMPANY></STATICVARIABLES></REQUESTDESC><REQUESTDATA>${vouchers.join('')}</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>`;
}
