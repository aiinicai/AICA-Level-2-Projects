// AR module samples: our customer ledger for Al Noor Trading LLC vs Al Noor's statement of account.
// Al Noor's SOA is their AP view of us, so signs are inverse (our Debit = their Credit).
import { Rng, UniqueAmounts } from './lib/rng.mjs';
import { d, addDays, businessDays, fmtDate, fmtAmt, toAed, sum, pad } from './lib/util.mjs';
import { writeLedger, bizFwd, bizBack, runBalance } from './lib/ledger.mjs';
import { OUR_COMPANY } from './lib/names.mjs';

const OPENING = 4821540; // 48,215.40 owed by Al Noor at 01-Aug-2026 (Dr in ours, Cr in theirs)
const CUST = 'Al Noor Trading LLC';

export async function generateAr(outDir) {
  const rng = new Rng(2026080202);
  const amts = new UniqueAmounts(rng);
  const P = { disputedOurs: amts.reserve(687550), disputedTheirs: amts.reserve(678550), poa: amts.reserve(1000000), cn: amts.reserve(241575), dn: amts.reserve(123640) };
  const days = [...businessDays(2026, 8), ...businessDays(2026, 9)];
  const ours = []; // {date, vno, type, ref, narr, dr, cr, tag}
  const theirs = []; // {date, doc, ref, narr, dr, cr, tag}

  // ---- Invoices INV-00118 .. INV-00157 ----
  const N_INV = 46;
  const invPool = days.filter((x) => x <= d(2026, 9, 24));
  const invDays = Array.from({ length: N_INV - 1 }, () => rng.pick(invPool)).sort((a, b) => a - b);
  invDays.push(d(2026, 9, 29)); // last invoice: delivered 29-Sep, not yet booked by the customer
  const DISPUTED = 31, DATELAG = 9, UNBOOKED = N_INV - 1;
  const VARIANT = { 5: (n) => String(n), 11: (n) => pad(n, 5), 16: (n) => `INV ${n}`, 21: (n) => `inv-${pad(n, 5)}`, 26: (n) => `INV/${pad(n, 5)}`, 34: (n) => String(n) };
  const products = ['Packaging film rolls', 'Corrugated cartons (assorted)', 'Stretch wrap 23 micron', 'PP strapping bands', 'Pallet labels & tags', 'Food-grade containers', 'Shrink sleeves', 'Bubble wrap rolls', 'Kraft paper reams'];
  const invoices = [];
  invDays.forEach((dt, i) => {
    const n = 118 + i;
    const no = `INV-${pad(n, 5)}`;
    const amount = i === DISPUTED ? P.disputedOurs : amts.take(1800, 26000);
    const inv = { i, n, no, date: dt, amount, lpo: `LPO-AN-${4400 + i * 3 + rng.int(0, 2)}`, product: rng.pick(products) };
    invoices.push(inv);
    ours.push({ date: dt, vno: `SI-${dt.getUTCMonth() === 7 ? '2608' : '2609'}-${pad(200 + i, 4)}`, type: 'Sales Invoice', ref: no, narr: `${inv.product} - ${inv.lpo}`, dr: amount, cr: 0, tag: 'invoice' });
    if (i === UNBOOKED) return;
    const lag = i === DATELAG ? 10 : rng.int(0, 4);
    const tDate = bizFwd(addDays(dt, lag));
    theirs.push({
      date: tDate, doc: `PI-26-${pad(451 + i, 4)}`, ref: VARIANT[i] ? VARIANT[i](n) : no,
      narr: `Purchase - ${inv.product}`, dr: 0, cr: i === DISPUTED ? P.disputedTheirs : amount,
      tag: i === DISPUTED ? 'disputed' : i === DATELAG ? 'date-lag' : VARIANT[i] ? 'ref-variant' : 'invoice',
    });
    inv.theirDate = tDate;
  });

  // ---- Credit note CN-0007 (return of goods against an August invoice) ----
  const cnDate = d(2026, 8, 19);
  ours.push({ date: cnDate, vno: 'CN-2608-0007', type: 'Credit Note', ref: 'CN-0007', narr: `Goods returned - damaged cartons against ${invoices[3].no}`, dr: 0, cr: P.cn, tag: 'credit-note' });
  theirs.push({ date: bizFwd(addDays(cnDate, 2)), doc: 'DN-AN-0388', ref: 'CN-0007', narr: 'Supplier credit note received - goods returned', dr: P.cn, cr: 0, tag: 'credit-note' });

  // ---- Receipts: customer pays groups of 1-3 invoices 20-40 days after invoicing ----
  const open = invoices.filter((x) => x.i !== DISPUTED && x.i !== UNBOOKED && x.i !== 3);
  const receipts = [];
  // Receipts/credits have the opposite sign to invoices, so they only need to be unique among themselves.
  const pays = new Set([P.poa, P.cn, P.dn]);
  let k = 0, rv = 1;
  while (k < open.length) {
    const size = Math.min(rng.int(1, 3), open.length - k);
    const grp = open.slice(k, k + size);
    const last = grp[grp.length - 1];
    const ourDate = bizFwd(addDays(last.date, rng.int(7, 24)));
    if (ourDate > d(2026, 9, 25)) break;
    const amount = sum(grp, (g) => g.amount);
    if (pays.has(amount)) { k += 1; continue; }
    pays.add(amount);
    k += size;
    const byCheque = receipts.length % 6 === 2;
    const ref = byCheque ? `${rng.int(1, 9)}${rng.digits(5)}` : `TT26${pad(ourDate.getUTCMonth() + 1, 2)}${rng.digits(4)}`;
    const theirDate = bizBack(addDays(ourDate, -rng.int(0, 3)));
    receipts.push({ ourDate, theirDate, amount, ref, grp });
  }
  for (const r of receipts) {
    const invs = r.grp.map((g) => g.no).join(', ');
    ours.push({ date: r.ourDate, vno: `RV-${r.ourDate.getUTCMonth() === 7 ? '2608' : '2609'}-${pad(rv++, 4)}`, type: 'Receipt', ref: r.ref, narr: `Received ${/^\d/.test(r.ref) ? 'cheque' : 'TT'} - settles ${invs}`, dr: 0, cr: r.amount, tag: 'receipt' });
    theirs.push({ date: r.theirDate, doc: `PV-26-${pad(380 + rv, 4)}`, ref: /^\d/.test(r.ref) ? `CHQ-${r.ref}` : r.ref, narr: `Payment to ${OUR_COMPANY} - ${r.grp.map((g) => g.n).join('/')}`, dr: r.amount, cr: 0, tag: 'receipt' });
  }

  // ---- Payment on account (both sides) ----
  const poaRef = 'TT26091408';
  ours.push({ date: d(2026, 9, 14), vno: `RV-2609-${pad(rv++, 4)}`, type: 'Receipt', ref: poaRef, narr: 'Payment on account - not allocated to invoices', dr: 0, cr: P.poa, tag: 'payment-on-account' });
  theirs.push({ date: d(2026, 9, 11), doc: `PV-26-${pad(380 + rv, 4)}`, ref: poaRef, narr: 'Advance payment on account', dr: P.poa, cr: 0, tag: 'payment-on-account' });

  // ---- Payment in transit: PDC received and booked by us 29-Sep; Al Noor books it on clearing in October ----
  const pit = { date: d(2026, 9, 29), ref: '000781', amount: amts.take(9000, 16000) };
  ours.push({ date: pit.date, vno: `RV-2609-${pad(rv++, 4)}`, type: 'Receipt', ref: pit.ref, narr: 'PDC cheque 000781 dated 30-Sep-2026 received (Emirates Islamic)', dr: 0, cr: pit.amount, tag: 'payment-in-transit' });

  // ---- Customer's debit note not in our books (short supply claim) ----
  theirs.push({ date: d(2026, 9, 23), doc: 'DN-AN-0412', ref: 'DN-AN-0412', narr: `Debit note - short supply on ${invoices[28].no.replace('INV-00', '')} (12 cartons)`, dr: P.dn, cr: 0, tag: 'their-debit-note' });

  // ---- Sort & balance ----
  const order = (a, b) => a.date - b.date || (a.cr ? 1 : 0) - (b.cr ? 1 : 0);
  ours.sort(order);
  theirs.sort((a, b) => a.date - b.date || (a.dr ? 1 : 0) - (b.dr ? 1 : 0));
  const oursClose = runBalance(ours, OPENING, (r) => r.dr - r.cr);
  const theirsClose = runBalance(theirs, OPENING, (r) => r.cr - r.dr);

  const amtCols = [
    { header: 'Debit', key: 'dr', width: 14, type: 'amount' },
    { header: 'Credit', key: 'cr', width: 14, type: 'amount' },
  ];
  const map = (r) => ({ ...r, dr: r.dr ? toAed(r.dr) : null, cr: r.cr ? toAed(r.cr) : null, balance: toAed(r.balance) });
  await writeLedger(`${outDir}/ar/Our_AR_Ledger_AlNoor_Trading.xlsx`, {
    sheet: 'Customer Ledger',
    titles: [OUR_COMPANY, `Customer Ledger - C-1045 ${CUST}`, 'Period: 01-Aug-2026 to 30-Sep-2026    Currency: AED'],
    columns: [
      { header: 'Date', key: 'date', width: 13, type: 'date' },
      { header: 'Voucher No', key: 'vno', width: 15 },
      { header: 'Type', key: 'type', width: 14 },
      { header: 'Invoice / Ref No', key: 'ref', width: 17 },
      { header: 'Narration', key: 'narr', width: 58 },
      ...amtCols,
      { header: 'Balance', key: 'balance', width: 15, type: 'amount' },
    ],
    rows: [
      { date: d(2026, 8, 1), narr: 'Opening balance', balance: toAed(OPENING), _style: 'balance' },
      ...ours.map(map),
      { date: d(2026, 9, 30), narr: 'Closing balance', balance: toAed(oursClose), _style: 'balance' },
    ],
  });
  await writeLedger(`${outDir}/ar/AlNoor_Trading_SOA.xlsx`, {
    sheet: 'SOA',
    titles: ['AL NOOR TRADING LLC', 'P.O. Box 41822, Al Qusais Industrial Area 3, Dubai, UAE', 'SUPPLIER STATEMENT OF ACCOUNT', `Supplier: ${OUR_COMPANY} (Vendor code V-2207)`, 'Period: 01/08/2026 to 30/09/2026  (balance shown = amount payable by Al Noor)', ''],
    columns: [
      { header: 'Posting Date', key: 'date', width: 13, type: 'date' },
      { header: 'Our Doc No', key: 'doc', width: 14 },
      { header: 'Supplier Inv / Ref', key: 'ref', width: 18 },
      { header: 'Particulars', key: 'narr', width: 52 },
      ...amtCols,
      { header: 'Balance (Cr)', key: 'balance', width: 15, type: 'amount' },
    ],
    rows: [
      { date: d(2026, 8, 1), narr: 'Opening Balance', balance: toAed(OPENING), _style: 'balance' },
      ...theirs.map(map),
      { date: d(2026, 9, 30), narr: 'Closing Balance', balance: toAed(theirsClose), _style: 'balance' },
    ],
  });

  const unbooked = invoices[UNBOOKED];
  const disputed = invoices[DISPUTED];
  const disputeDiff = P.disputedOurs - P.disputedTheirs;
  const result = oursClose - unbooked.amount + pit.amount - P.dn - disputeDiff;
  const statement = [
    ['Balance as per our books (Dr, 30-Sep-2026)', oursClose],
    [`Less: invoice in our books not booked by customer - ${unbooked.no} ${fmtDate(unbooked.date)}`, -unbooked.amount],
    [`Add: payment in transit in our books, not theirs - PDC ${pit.ref} ${fmtDate(pit.date)}`, pit.amount],
    ['Less: item in their books, not ours - customer debit note DN-AN-0412 (short supply)', -P.dn],
    [`Less: amount difference on ${disputed.no} (ours ${fmtAmt(P.disputedOurs)} vs theirs ${fmtAmt(P.disputedTheirs)})`, -disputeDiff],
    ["Balance as per customer's statement (Cr, 30-Sep-2026)", result],
    ["Balance per customer's statement (file)", theirsClose],
    ['Unexplained difference', theirsClose - result],
  ];
  if (theirsClose - result !== 0) throw new Error('AR statement does not tie');

  const variants = Object.keys(VARIANT).map((i) => `${invoices[i].no} vs "${VARIANT[i](invoices[i].n)}"`);
  const datelag = invoices[DATELAG];
  const scenarios = [
    { s: 'Matching invoices', d: `${N_INV - 3} invoices between ${invoices[0].no} and ${invoices[N_INV - 2].no} booked by Al Noor 0-4 days later (date tolerance +/-7)`, e: 'Matched' },
    { s: 'Invoice numbers written differently', d: variants.join('; '), e: 'Matched with Reference rule = Normalised (prefix INV, dashes, spaces, leading zeros ignored); Doubtful with Exact' },
    { s: 'Invoice booked late by customer', d: `${datelag.no} ${fmtAmt(datelag.amount)}: ours ${fmtDate(datelag.date)}, theirs ${fmtDate(datelag.theirDate)}`, e: 'Doubtful - "Reference and amount agree; date differs by more than 7 days"' },
    { s: 'Customer receipts', d: `${receipts.length} payments (TT and cheque); cheque refs written "CHQ-123456" in the SOA vs "123456" in ours`, e: 'Matched (Normalised strips the CHQ prefix)' },
    { s: 'Credit note', d: `CN-0007 ${fmtAmt(P.cn)} (ours Credit 19-Aug; theirs Debit 21-Aug as DN-AN-0388)`, e: 'Matched - detected as a credit note' },
    { s: 'Payment on account', d: `TT26091408 ${fmtAmt(P.poa)} - not allocated to any invoice (ours 14-Sep, theirs 11-Sep)`, e: 'Matched - labelled payment on account' },
    { s: 'Payment in transit (ours only)', d: `PDC ${pit.ref} ${fmtAmt(pit.amount)} booked by us 29-Sep; Al Noor books on clearing`, e: 'Unmatched - ours' },
    { s: 'Invoice not booked by customer', d: `${unbooked.no} ${fmtDate(unbooked.date)} ${fmtAmt(unbooked.amount)}`, e: 'Unmatched - ours' },
    { s: 'Disputed invoice (transposition)', d: `${disputed.no}: ours ${fmtAmt(P.disputedOurs)} vs theirs ${fmtAmt(P.disputedTheirs)}`, e: 'Doubtful - "Reference and date agree; amount differs by 90.00 (possible transposition)"' },
    { s: "Customer's debit note (theirs only)", d: `DN-AN-0412 23-Sep ${fmtAmt(P.dn)} - short-supply claim we have not accepted`, e: 'Unmatched - theirs' },
  ];
  const matched = N_INV - 3 + receipts.length + 2;
  return {
    key: 'ar',
    files: ['ar/Our_AR_Ledger_AlNoor_Trading.xlsx', 'ar/AlNoor_Trading_SOA.xlsx'],
    rowsA: ours.length, rowsB: theirs.length, opening: OPENING, closeA: oursClose, closeB: theirsClose,
    tiers: { matched, doubtful: 2, likely: 0, unmatchedA: 2, unmatchedB: 1 },
    planted: { disputedNo: disputed.no, disputeDiff, unbookedNo: unbooked.no, pitRef: pit.ref, variants: Object.keys(VARIANT).map((i) => [invoices[i].no, VARIANT[i](invoices[i].n)]) },
    statement, scenarios,
  };
}
