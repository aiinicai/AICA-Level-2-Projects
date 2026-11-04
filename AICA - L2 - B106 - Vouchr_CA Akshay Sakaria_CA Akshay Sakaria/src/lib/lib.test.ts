import { describe, expect, it } from 'vitest';
import { checkGstin, checkPan, gstinCheckChar } from './validators';
import { daysBetween, fyLabel, isBackdatedEntry } from './dates';
import { cleanAmount, computeAmounts, splitFromTotal } from './money';
import { suggestHead, suggestItc, suggestRcm, suggestTds } from './rules';
import { buildTallyXml, voucherLines, DEFAULT_LEDGERS } from './tallyXml';
import { parseEInvoiceQr } from './einvoiceQr';
import { normInv, parse2B, reconcile } from './reco';
import { buildAlerts, outstanding } from './alerts';
import { toCsv } from './csv';
import { BLOCKED_RULES, EXPENSE_HEADS, RCM_RULES, TDS_RATES } from '../data/masters';
import type { Expense, Payment } from '../data/types';
import { ageBucket, billStatus, dueDate, paidAmount, unallocated } from './alerts';
import { allocateLines } from './payalloc';
import { parseChallanText, parseDate, parseInvoiceText } from './extract';
import { detectMode, matchBankRows, parseBankStatement, parseCsv } from './bank';
import { stateName } from './states';

const payment = (o: Partial<Payment>): Payment => ({
  id: 'p', clientId: 'c', vendorId: 'v', vendorName: 'V', mode: 'cash', paidOn: '2026-10-06', amount: 0, allocations: [], isBackdated: false, createdBy: 'u', createdAt: '', ...o
});

const head = (id: string) => EXPENSE_HEADS.find((h) => h.id === id)!;
const exp = (o: Partial<Expense>): Expense => ({
  id: 'x', clientId: 'c', fyLabel: '2026-27', vendorName: 'V', invoiceNo: 'I1', invoiceDate: '2026-10-05', entrySource: 'manual',
  grossAmount: 1000, discount: 0, taxableValue: 1000, cgst: 90, sgst: 90, igst: 0, totalAmount: 1180, headId: 'h-print',
  tdsAmount: 0, rcmApplicable: false, rcmTax: 0, itcEligible: true, status: 'approved', isBackdated: false, createdBy: 'u', createdAt: '', ...o
});

describe('validators', () => {
  it('accepts a GSTIN with a correct check digit and rejects a typo', () => {
    const base = '27AAPFU0939F1Z';
    const good = base + gstinCheckChar(base);
    expect(checkGstin(good).ok).toBe(true);
    expect(checkGstin(good).pan).toBe('AAPFU0939F');
    expect(checkGstin(base + (good[14] === 'A' ? 'B' : 'A')).ok).toBe(false);
  });
  it('rejects bad GSTIN shapes and state codes', () => {
    expect(checkGstin('27AAPFU0939F1Z').reason).toMatch(/15/);
    expect(checkGstin('00AAPFU0939F1ZV').ok).toBe(false);
    expect(checkGstin('27aapfu0939f1z' + gstinCheckChar('27AAPFU0939F1Z')).ok).toBe(true); // lower-case input is normalised
    expect(checkGstin('27AAPFU0939F1A5').ok).toBe(false); // 14th char must be Z
  });
  it('reads PAN entity type from 4th character', () => {
    expect(checkPan('ABCPE1234F')).toMatchObject({ ok: true, entityType: 'Individual' });
    expect(checkPan('ABCCE1234F').entityType).toBe('Company');
    expect(checkPan('ABCXE1234F').ok).toBe(false);
    expect(checkPan('ABCPE12345').ok).toBe(false);
  });
});

describe('dates', () => {
  it('maps dates to Indian FY', () => {
    expect(fyLabel('2026-04-01')).toBe('2026-27');
    expect(fyLabel('2027-03-31')).toBe('2026-27');
    expect(fyLabel('2026-03-31')).toBe('2025-26');
  });
  it('flags past-dated entries outside window', () => {
    expect(isBackdatedEntry('2026-09-15', '2026-10-31', 0)).toBe(true);
    expect(isBackdatedEntry('2026-10-01', '2026-10-31', 0)).toBe(false);
    expect(isBackdatedEntry('2026-09-28', '2026-10-02', 7)).toBe(false);
    expect(isBackdatedEntry('2026-12-31', '2027-01-01', 0)).toBe(true); // across year end
  });
  it('counts days across month ends', () => {
    expect(daysBetween('2026-01-31', '2026-03-01')).toBe(29);
  });
});

describe('amounts', () => {
  it('applies discount before GST and splits intra-state', () => {
    expect(computeAmounts(1000, 100, 18, false)).toEqual({ taxableValue: 900, cgst: 81, sgst: 81, igst: 0, totalAmount: 1062 });
    expect(computeAmounts(1000, 0, 18, true).igst).toBe(180);
  });
  it('splits from bill total without losing paise', () => {
    const s = splitFromTotal(999.99, 18, false);
    expect(Math.round((s.taxableValue + s.cgst + s.sgst) * 100)).toBe(99999);
    expect(splitFromTotal(500, 0, false)).toEqual({ taxableValue: 500, cgst: 0, sgst: 0, igst: 0, totalAmount: 500 });
  });
  it('cleans typed amounts', () => {
    expect(cleanAmount('1,23,456.789')).toBe('123456.78');
    expect(cleanAmount('1.2.3')).toBe('1.23');
    expect(cleanAmount('00042')).toBe('42');
    expect(cleanAmount('.5')).toBe('0.5');
    expect(cleanAmount('abc')).toBe('');
  });
});

describe('rules', () => {
  it('prefers longest HSN/SAC prefix', () => {
    expect(suggestHead('', '998212', EXPENSE_HEADS).headId).toBe('h-legal');
    expect(suggestHead('', '998311', EXPENSE_HEADS).headId).toBe('h-prof');
  });
  it('uses keywords when no HSN, vendor history first, misc last', () => {
    expect(suggestHead('Airtel broadband bill', undefined, EXPENSE_HEADS).headId).toBe('h-phone');
    expect(suggestHead('Airtel', undefined, EXPENSE_HEADS, 'h-misc').headId).toBe('h-misc');
    expect(suggestHead('zzz', undefined, EXPENSE_HEADS)).toMatchObject({ headId: 'h-misc', confidence: 0.2 });
  });
  it('contractor TDS: 1% for individual, threshold respected, higher rate without PAN', () => {
    const c = head('h-contract');
    expect(suggestTds(c, { pan: 'ABCPE1234F', panStatus: 'Operative' }, 40000, 0, TDS_RATES)).toMatchObject({ code: 'CONTRACT_IND', amount: 400 });
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Operative' }, 10000, 0, TDS_RATES).amount).toBe(0);
    expect(suggestTds(c, undefined, 40000, 0, TDS_RATES).ratePct).toBe(20);
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Inoperative' }, 40000, 0, TDS_RATES).ratePct).toBe(20);
  });
  it('catches up TDS on earlier bills when the yearly limit is first crossed', () => {
    const c = head('h-contract');
    // 95,000 booked earlier without TDS; this 10,000 bill crosses 1,00,000 → TDS on 1,05,000 @2%
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Operative' }, 10000, 95000, TDS_RATES, 95000).amount).toBe(2100);
    // already crossed earlier → only this bill
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Operative' }, 10000, 120000, TDS_RATES, 0).amount).toBe(200);
  });
  it('no TDS for heads without a TDS code', () => {
    expect(suggestTds(head('h-print'), undefined, 900000, 0, TDS_RATES).amount).toBe(0);
  });
  it('RCM on security only for non-body-corporate, with rate', () => {
    const s = head('h-security');
    expect(suggestRcm(s, { gstRegistered: false, pan: 'ABCPE1234F' }, RCM_RULES)).toMatchObject({ applicable: true, ratePct: 18 });
    expect(suggestRcm(s, { gstRegistered: true, pan: 'ABCCE1234F' }, RCM_RULES).applicable).toBe(false);
    expect(suggestRcm(head('h-freight'), { gstRegistered: false }, RCM_RULES).ratePct).toBe(5);
    expect(suggestRcm(head('h-print'), { gstRegistered: false }, RCM_RULES).applicable).toBe(false);
  });
  it('blocks ITC on food and for unregistered vendors', () => {
    expect(suggestItc(head('h-staff'), '', true, BLOCKED_RULES)).toMatchObject({ eligible: false, blockedCode: 'FOOD' });
    expect(suggestItc(head('h-print'), '', false, BLOCKED_RULES).eligible).toBe(false);
    expect(suggestItc(head('h-misc'), 'diwali gift hampers', true, BLOCKED_RULES).blockedCode).toBe('GIFTS');
  });
});

describe('tally xml', () => {
  const e = exp({ vendorName: 'Sharma & Co', invoiceNo: 'INV/1', grossAmount: 50000, taxableValue: 50000, cgst: 4500, sgst: 4500, totalAmount: 59000, headId: 'h-prof', tdsAmount: 5000 });
  const sum = (l: { amount: number }[]) => Math.round(l.reduce((s, x) => s + x.amount, 0) * 100);
  it('balances and escapes', () => {
    expect(sum(voucherLines(e, head('h-prof'), DEFAULT_LEDGERS))).toBe(0);
    const xml = buildTallyXml('Demo & Co', [e], EXPENSE_HEADS);
    expect(xml).toContain('<SVCURRENTCOMPANY>Demo &amp; Co</SVCURRENTCOMPANY>');
    expect(xml).toContain('<LEDGERNAME>Sharma &amp; Co</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>54000.00</AMOUNT>');
  });
  it('books round-off up to ₹1 and refuses larger gaps', () => {
    const r = exp({ taxableValue: 847.46, cgst: 76.27, sgst: 76.27, totalAmount: 1000 });
    const lines = voucherLines(r, head('h-print'), DEFAULT_LEDGERS);
    expect(lines.find((l) => l.ledger === 'Round Off')).toBeUndefined(); // exact → no round-off line
    const r2 = exp({ taxableValue: 847, cgst: 76, sgst: 76, totalAmount: 1000 });
    expect(voucherLines(r2, head('h-print'), DEFAULT_LEDGERS).find((l) => l.ledger === 'Round Off')?.amount).toBe(1);
    expect(() => voucherLines(exp({ totalAmount: 1200 }), head('h-print'), DEFAULT_LEDGERS)).toThrow(/differs/);
  });
  it('adds RCM liability and ITC lines, still balanced', () => {
    const g = exp({ vendorName: 'Swift', headId: 'h-freight', taxableValue: 18500, cgst: 0, sgst: 0, totalAmount: 18500, rcmApplicable: true, rcmTax: 925, itcEligible: true });
    const lines = voucherLines(g, head('h-freight'), DEFAULT_LEDGERS);
    expect(lines).toContainEqual({ ledger: 'GST Payable (RCM)', amount: -925 });
    expect(lines).toContainEqual({ ledger: 'Input GST (RCM)', amount: 925 });
    expect(sum(lines)).toBe(0);
  });
  it('ineligible ITC goes into the expense ledger', () => {
    const f = exp({ headId: 'h-staff', itcEligible: false });
    expect(voucherLines(f, head('h-staff'), DEFAULT_LEDGERS)[0]).toEqual({ ledger: 'Staff Welfare', amount: 1180 });
  });
  it('emits payment vouchers with the right party and bank ledgers', () => {
    const p = payment({ mode: 'upi', accountId: 'b1', amount: 1500, allocations: [{ expenseId: 'x', amount: 1180 }] });
    const xml = buildTallyXml('C', [], EXPENSE_HEADS, {
      payments: [p], allExpenses: [exp({})],
      partyLedger: () => 'Vendor Ledger (Tally)', paymentLedger: (q) => (q.accountId === 'b1' ? 'HDFC Bank' : 'Cash')
    });
    expect(xml).toContain('VCHTYPE="Payment"');
    expect(xml).toContain('<LEDGERNAME>HDFC Bank</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>1500.00</AMOUNT>');
    expect(xml).toContain('<LEDGERNAME>Vendor Ledger (Tally)</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-1500.00</AMOUNT>');
    expect(xml).toContain('advance ₹320'); // 1500 paid, 1180 applied
  });
  it('refuses a payment that points at an unknown bill', () => {
    expect(() => buildTallyXml('C', [], EXPENSE_HEADS, { payments: [payment({ allocations: [{ expenseId: 'nope', amount: 1 }] })], allExpenses: [] })).toThrow(/unknown bill/);
  });
  it('rejects an expense without a head', () => {
    expect(() => buildTallyXml('C', [exp({ headId: undefined })], EXPENSE_HEADS)).toThrow(/no expense head/);
  });
});

describe('e-invoice QR', () => {
  it('decodes signed QR payload', () => {
    const data = { SellerGstin: '29AAACB1234C1ZX', DocNo: 'A/12', DocDt: '05/10/2026', TotInvVal: 11800, MainHsnCode: '998313', Irn: 'abc' };
    const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString('base64url');
    const jwt = `${b64({ alg: 'RS256' })}.${b64({ data: JSON.stringify(data) })}.sig`;
    expect(parseEInvoiceQr(jwt)).toMatchObject({ docNo: 'A/12', docDate: '2026-10-05', totalValue: 11800, mainHsn: '998313' });
    expect(parseEInvoiceQr('hello')).toBeNull();
    expect(parseEInvoiceQr('a.b.c')).toBeNull();
    expect(parseEInvoiceQr('upi://pay?pa=x@y')).toBeNull(); // UPI QR on bills must not be mistaken
  });
});

describe('GSTR-2B reconciliation', () => {
  const file = { data: { gstin: '27AABFS1234K1ZX', rtnprd: '102026', docdata: { b2b: [
    { ctin: '27AAKFK4321L1ZA', trdnm: 'Kulkarni', inv: [
      { inum: 'KA/26/200', dt: '05-10-2026', val: 11800, txval: 10000, igst: 0, cgst: 900, sgst: 900, cess: 0, itcavl: 'Y' },
      { inum: 'KA-26-201', dt: '06-10-2026', val: 5900, items: [{ txval: 5000, cgst: 450, sgst: 450 }] }
    ] },
    { ctin: '27ZZZZZ9999Z1ZZ', trdnm: 'Stranger', inv: [{ inum: '9', dt: '07-10-2026', txval: 100, cgst: 9, sgst: 9 }] }
  ] } } };
  it('parses invoice-level and item-level tax', () => {
    const p = parse2B(file);
    expect(p.period).toBe('102026');
    expect(p.lines).toHaveLength(3);
    expect(p.lines[1]).toMatchObject({ invoiceDate: '2026-10-06', taxableValue: 5000, cgst: 450 });
  });
  it('normalises invoice numbers', () => {
    expect(normInv('ka/26/201')).toBe(normInv('KA-26-201'));
    expect(normInv('00123')).toBe('123');
  });
  it('classifies matched, mismatch, missing in 2B, missing in books', () => {
    const lines = parse2B(file).lines;
    const books = [
      exp({ id: 'a', vendorId: 'k', invoiceNo: 'KA/26/200', invoiceDate: '2026-10-05', taxableValue: 10000, cgst: 900, sgst: 900, totalAmount: 11800 }),
      exp({ id: 'b', vendorId: 'k', invoiceNo: 'ka 26 201', invoiceDate: '2026-10-06', taxableValue: 5000, cgst: 500, sgst: 500, totalAmount: 6000 }),
      exp({ id: 'c', vendorId: 'k', invoiceNo: 'KA/26/999', invoiceDate: '2026-10-09' }),
      exp({ id: 'd', vendorId: undefined, invoiceNo: 'X', cgst: 0, sgst: 0, totalAmount: 1000 }) // no GST → ignored
    ];
    const rows = reconcile(books, (e) => (e.vendorId === 'k' ? '27AAKFK4321L1ZA' : undefined), lines);
    expect(rows.map((r) => r.status).sort()).toEqual(['matched', 'mismatch', 'missing_in_2b', 'missing_in_books']);
    expect(rows.find((r) => r.expenseId === 'b')?.diff).toBe(100);
  });
  it('fails clearly on a wrong file', () => {
    expect(parse2B({ data: { docdata: {} } }).lines).toHaveLength(0);
    expect(() => parse2B({ data: { docdata: { b2b: 'x' } } })).toThrow();
  });
});

describe('alerts', () => {
  const pay = (amount: number): Payment => payment({ amount, allocations: [{ expenseId: 'x', amount }] });
  it('outstanding = total − TDS − payments', () => {
    expect(outstanding(exp({ tdsAmount: 100 }), [pay(500)])).toBe(580);
  });
  it('raises 30-day and 180-day ITC alerts', () => {
    const a = buildAlerts([exp({ invoiceDate: '2026-08-01' })], [], '2026-10-31');
    expect(a.some((x) => x.kind === 'payment_overdue_30')).toBe(true);
    const b = buildAlerts([exp({ invoiceDate: '2026-03-01' })], [], '2026-10-31');
    expect(b.some((x) => x.kind === 'itc_180')).toBe(true);
    expect(buildAlerts([exp({ invoiceDate: '2026-03-01' })], [pay(1180)], '2026-10-31')).toHaveLength(0);
  });
  it('TDS alert disappears once the challan covers the month', () => {
    const e = [exp({ invoiceDate: '2026-10-05', tdsAmount: 500 })];
    expect(buildAlerts(e, [], '2026-11-03').some((x) => x.kind === 'tds_due')).toBe(true);
    const ch = [{ id: 'c', clientId: 'c', month: '2026-10', amount: 500, bsrCode: '1234567', challanNo: '1', paidOn: '2026-11-02' }];
    expect(buildAlerts(e, [], '2026-11-03', { challans: ch }).some((x) => x.kind === 'tds_due')).toBe(false);
  });
  it('reminds to post to Tally before the 25th', () => {
    const e = [exp({ invoiceDate: '2026-09-10', status: 'approved' })];
    expect(buildAlerts(e, [], '2026-10-20', { tallyMode: 'xml_file' }).find((x) => x.kind === 'tally_posting')?.severity).toBe('warn');
    expect(buildAlerts(e, [], '2026-10-26', { tallyMode: 'xml_file' }).find((x) => x.kind === 'tally_posting')?.severity).toBe('danger');
    expect(buildAlerts(e, [], '2026-10-20', { tallyMode: 'none' }).some((x) => x.kind === 'tally_posting')).toBe(false);
  });
});

describe('csv', () => {
  it('quotes, adds BOM and neutralises formulas', () => {
    const csv = toCsv(['a'], [['=HYPERLINK("x")'], ['-5'], ['say "hi"']]);
    expect(csv.startsWith('﻿')).toBe(true);
    expect(csv).toContain(`"'=HYPERLINK(""x"")"`);
    expect(csv).toContain('"-5"');
    expect(csv).toContain('"say ""hi"""');
  });
});


describe('split & multi-bill payments', () => {
  it('spreads several payment lines across bills oldest-first; extra stays as advance', () => {
    // bill A 1000, bill B 500; paid 700 cash + 900 UPI → A: 700+300, B: 500, advance 100
    const r = allocateLines([700, 900], [{ expenseId: 'A', amount: 1000 }, { expenseId: 'B', amount: 500 }]);
    expect(r[0]).toEqual([{ expenseId: 'A', amount: 700 }]);
    expect(r[1]).toEqual([{ expenseId: 'A', amount: 300 }, { expenseId: 'B', amount: 500 }]);
    expect(900 - r[1].reduce((x, a) => x + a.amount, 0)).toBe(100);
  });
  it('one bill paid in two parts on two days in two modes', () => {
    const e = exp({ id: 'x', totalAmount: 18500, taxableValue: 18500, cgst: 0, sgst: 0 });
    const ps = [payment({ mode: 'cash', paidOn: '2026-08-25', amount: 8000, allocations: [{ expenseId: 'x', amount: 8000 }] }),
      payment({ id: 'p2', mode: 'upi', paidOn: '2026-09-10', amount: 10500, allocations: [{ expenseId: 'x', amount: 10500 }] })];
    expect(paidAmount('x', ps)).toBe(18500);
    expect(outstanding(e, ps)).toBe(0);
    expect(billStatus(e, ps.slice(0, 1), '2026-09-01', 30)).toBe('partial');
  });
  it('a single payment can settle two bills', () => {
    const p = payment({ amount: 1000, allocations: [{ expenseId: 'a', amount: 600 }, { expenseId: 'b', amount: 400 }] });
    expect(paidAmount('a', [p])).toBe(600);
    expect(paidAmount('b', [p])).toBe(400);
    expect(unallocated(p)).toBe(0);
  });
  it('bill status and ageing follow vendor credit days', () => {
    const e = exp({ invoiceDate: '2026-08-01' });
    expect(dueDate(e, 15)).toBe('2026-08-16');
    expect(billStatus(e, [], '2026-08-10', 15)).toBe('open');
    expect(billStatus(e, [], '2026-08-20', 15)).toBe('overdue');
    expect(ageBucket(e, '2026-08-10', 15)).toBe('Not due');
    expect(ageBucket(e, '2026-10-01', 15)).toBe('31–60');
    expect(ageBucket(e, '2027-01-01', 15)).toBe('90+');
  });
});

describe('document reading (on-device)', () => {
  // Text as pdf.js extracts it from a real e-Pay Tax challan receipt (personal details replaced).
  const challan = `INCOME   TAX   DEPARTMENT
Challan   Receipt
ITNS   No. :   281
TAN   :
MUMA12345B
Name   :   SHREE   GANESH   TRADERS
Major   Head   :   Income   Tax   (Other   than   Companies)   (0021)
Minor   Head   :   TDS/TCS Payable by Taxpayer   (200)
Amount   (in   Rs.)   :
₹   8,920
CIN   :   26100700025990UTIB
Mode   of   Payment   :   Net   Banking
Date   of   Deposit   :   07- Oct-2026
BSR   code   :   6360014
Challan   No   :   00707
Tender   Date   :   07/10/2026
Total   (A+B+C+D+E+F)   ₹   8,920`;
  it('reads BSR, challan no, deposit date, amount, CIN from a challan receipt', () => {
    expect(parseChallanText(challan)).toMatchObject({ bsrCode: '6360014', challanNo: '00707', depositDate: '2026-10-07', amount: 8920, cin: '26100700025990UTIB', itns: '281', tan: 'MUMA12345B', found: 4 });
  });
  it('parses Indian date styles', () => {
    expect(parseDate('27-Jul-2024')).toBe('2024-07-27');
    expect(parseDate('27/07/2024')).toBe('2024-07-27');
    expect(parseDate('5.9.24')).toBe('2024-09-05');
    expect(parseDate('03 Sept 2026')).toBe('2026-09-03');
    expect(parseDate('31/13/2026')).toBeUndefined();
  });
  const gstinOf = (base: string) => base + gstinCheckChar(base);
  it('reads an e-mailed tax invoice (PDF text layer)', () => {
    const seller = gstinOf('27ABCPH9090J1Z');
    const buyer = gstinOf('27AABFS1234K1Z');
    const text = `TAX INVOICE
Paper House Stationers
Shop 4, MG Road, Pune
GSTIN: ${seller}
Bill To: Shree Ganesh Traders  GSTIN: ${buyer}
Invoice No: PH-2302          Invoice Date: 05/10/2026
HSN/SAC: 4820   A4 paper 10 reams
Taxable value 1,000.00
CGST @ 9% 90.00   SGST @ 9% 90.00
Grand Total ₹ 1,180.00
Amount in words: One thousand one hundred eighty only`;
    expect(parseInvoiceText(text, buyer)).toMatchObject({ vendorGstin: seller, vendorName: 'Paper House Stationers', invoiceNo: 'PH-2302', invoiceDate: '2026-10-05', totalAmount: 1180, gstRatePct: 18, hsnSac: '4820', found: 5 });
  });
  it('does not invent fields it cannot see', () => {
    const r = parseInvoiceText('Thank you for shopping\nVisit again');
    expect([r.vendorGstin, r.invoiceNo, r.totalAmount, r.vendorName]).toEqual([undefined, undefined, undefined, undefined]);
    expect(r.found).toBe(0);
  });
  it('maps GSTIN to state', () => {
    expect(stateName('27AABFS1234K1ZA')).toBe('Maharashtra');
    expect(stateName('24')).toBe('Gujarat');
  });
});

describe('bank statement import', () => {
  const csv = `HDFC BANK Statement of account
Date,Narration,Chq./Ref.No.,Value Dt,Withdrawal Amt.,Deposit Amt.,Closing Balance
"10/09/26","UPI-SWIFT ROADLINES-swift@okhdfc-UPI 7781200",0000778,10/09/26,"10,500.00",,"1,20,000.00"
12/10/26,NEFT DR-KULKARNI ASSOCIATES-KA/26/164,N2810,12/10/26,26500.00,,93500.00
15/10/26,CHQ PAID-000123-RANDOM PERSON,000123,15/10/26,1850.00,,91650.00
16/10/26,INTEREST CREDIT,,16/10/26,,120.00,91770.00
Opening balance,,,,,,`;
  it('finds the header row, parses Indian amounts and dates, skips footers', () => {
    const rows = parseBankStatement(csv);
    expect(rows).toHaveLength(4);
    expect(rows[0]).toMatchObject({ date: '2026-09-10', debit: 10500, mode: 'upi', ref: '0000778' });
    expect(rows[3]).toMatchObject({ debit: 0, credit: 120 });
  });
  it('detects payment mode from narration', () => {
    expect(detectMode('NEFT DR-ABC')).toBe('bank');
    expect(detectMode('CHQ PAID 0001')).toBe('cheque');
    expect(detectMode('POS 4123 AMAZON')).toBe('card');
  });
  it('handles quotes and commas inside cells', () => {
    expect(parseCsv('a,"b, c","d ""q"""\n1,2,3')).toEqual([['a', 'b, c', 'd "q"'], ['1', '2', '3']]);
  });
  it('suggests vendor + bill matches; amount-only matches are lower confidence', () => {
    const vendors = [{ id: 'v1', clientId: 'c', name: 'Kulkarni Associates', gstRegistered: true }, { id: 'v2', clientId: 'c', name: 'Swift Roadlines', gstRegistered: false }];
    const b1 = exp({ id: 'k1', vendorId: 'v1', invoiceNo: 'KA/26/164', totalAmount: 29500, tdsAmount: 2500 });
    const b2 = exp({ id: 's1', vendorId: 'v2', invoiceNo: '466', invoiceDate: '2026-10-27', totalAmount: 21500 });
    const b3 = exp({ id: 'r1', vendorId: 'v3', invoiceNo: 'RE-55', totalAmount: 1850 });
    const m = matchBankRows(parseBankStatement(csv), vendors, [{ expense: b1, due: 27000 }, { expense: b2, due: 21500 }, { expense: b3, due: 1850 }]);
    expect(m[0]).toMatchObject({ vendor: { id: 'v2' }, confidence: 'medium' });               // vendor named, partial payment of a bigger bill
    expect(m[0].bills).toEqual([{ expense: b2, amount: 10500 }]);
    expect(m[1]).toMatchObject({ vendor: { id: 'v1' }, confidence: 'medium' });               // bill no. in narration, 26,500 of 27,000
    expect(m[2]).toMatchObject({ confidence: 'medium', reason: 'Amount matches one unpaid bill' }); // amount only
    expect(m).toHaveLength(3);                                                               // credits ignored
  });
});

describe('v0.4: Drive filing, payment sources, projects, narration', () => {
  it('files documents client-wise and FY-wise with self-explaining names', async () => {
    const { docFolder, docName } = await import('./storage');
    expect(docFolder('Shree Ganesh Traders', '2026-27', 'Bills')).toBe('Vouchr/Shree-Ganesh-Traders/FY 2026-27/Bills');
    expect(docFolder('A/B & Co.', '2026-27', 'TDS Challans')).toBe('Vouchr/AB-Co/FY 2026-27/TDS Challans');
    expect(docFolder('Shree Ganesh Traders', '', 'Branding')).toBe('Vouchr/Shree-Ganesh-Traders/Branding');
    expect(docName('2026-10-05', 'Paper House Stationers', 'PH/2302', 'IMG_2231.JPG')).toBe('2026-10-05_Paper-House-Stationers_PH2302.jpg');
    expect(docName('2026-10-05', undefined, undefined, 'scan')).toBe('2026-10-05.bin');
  });
  it('payment sources follow the mode; cash needs a choice only with several cash boxes', async () => {
    const { needsSource, sourceKinds } = await import('../data/store');
    const base = { id: 'c', name: 'C', brandColor: '', tallyMode: 'xml_file' as const, backdateWindowDays: 0, cashLedger: 'Cash', defaultCreditDays: 30, cashLimitPerDay: 10000, noteAboveAmount: 0, costCentres: [] };
    const c = { ...base, bankAccounts: [{ id: 'b', kind: 'bank' as const, name: 'HDFC', tallyLedger: 'HDFC' }, { id: 'u', kind: 'upi' as const, name: 'GPay', tallyLedger: 'HDFC', linkedBankId: 'b' }, { id: 'x', kind: 'cash' as const, name: 'Main', tallyLedger: 'Cash' }] };
    expect(sourceKinds('upi')).toEqual(['upi', 'bank']);
    expect(needsSource(c, 'upi')).toBe(true);
    expect(needsSource(c, 'card')).toBe(false); // no card set up → nothing to choose
    expect(needsSource(c, 'cash')).toBe(false); // one cash box → automatic
    expect(needsSource({ ...c, bankAccounts: [...c.bankAccounts, { id: 'y', kind: 'cash' as const, name: 'Petty', tallyLedger: 'Petty Cash' }] }, 'cash')).toBe(true);
  });
  it('Tally journal carries the narration and a cost-centre allocation', () => {
    const e = exp({ narration: 'Paid against PO 114', costCentreId: 'cc2' });
    const xml = buildTallyXml('C', [e], EXPENSE_HEADS, { costCentreOf: () => 'Nashik Branch' });
    expect(xml).toContain('<NARRATION>Paid against PO 114 (Bill I1)</NARRATION>');
    expect(xml).toContain('<COSTCENTREALLOCATIONS.LIST><NAME>Nashik Branch</NAME><AMOUNT>-1000.00</AMOUNT></COSTCENTREALLOCATIONS.LIST>');
    // only the expense ledger line is allocated
    expect(xml.match(/COSTCENTREALLOCATIONS\.LIST><NAME>/g)).toHaveLength(1);
  });
  it('payment voucher uses the UPI ID’s linked bank ledger', () => {
    const p = payment({ mode: 'upi', accountId: 'u1', amount: 500, allocations: [{ expenseId: 'x', amount: 500 }] });
    const xml = buildTallyXml('C', [], EXPENSE_HEADS, { payments: [p], allExpenses: [exp({})], paymentLedger: () => 'HDFC Bank' });
    expect(xml).toContain('<LEDGERNAME>HDFC Bank</LEDGERNAME>');
  });
});

describe('audit fixes', () => {
  it('uses the TDS rate in force on the bill date', () => {
    const c = head('h-prof');
    const rates = [
      ...TDS_RATES.filter((r) => r.code !== 'PROF_FEES'),
      { ...TDS_RATES.find((r) => r.code === 'PROF_FEES')!, effectiveTo: '2026-09-30' },
      { ...TDS_RATES.find((r) => r.code === 'PROF_FEES')!, ratePct: 7.5, effectiveFrom: '2026-10-01' }
    ];
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Operative' }, 60000, 0, rates, 0, '2026-09-15').ratePct).toBe(10);
    expect(suggestTds(c, { pan: 'ABCCE1234F', panStatus: 'Operative' }, 60000, 0, rates, 0, '2026-10-15').ratePct).toBe(7.5);
  });
});
