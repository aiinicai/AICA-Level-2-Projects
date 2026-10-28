// AP module samples: our supplier ledger for Gulf Supplies LLC vs Gulf Supplies' statement of account.
// Gulf Supplies' SOA is their AR view of us, so signs are inverse (our Credit = their Debit).
import { Rng, UniqueAmounts } from './lib/rng.mjs';
import { d, addDays, businessDays, fmtDate, fmtAmt, toAed, sum, pad } from './lib/util.mjs';
import { writeLedger, bizFwd, runBalance } from './lib/ledger.mjs';
import { OUR_COMPANY } from './lib/names.mjs';

const OPENING = 6390715; // 63,907.15 owed to Gulf Supplies at 01-Aug-2026 (Cr in ours, Dr in theirs)
const SUPP = 'Gulf Supplies LLC';

export async function generateAp(outDir) {
  const rng = new Rng(2026080303);
  const amts = new UniqueAmounts(rng);
  const P = { roundOurs: amts.reserve(731840), roundTheirs: amts.reserve(731890), dn: amts.reserve(184260) };
  const days = [...businessDays(2026, 8), ...businessDays(2026, 9)];
  const ours = []; // {date, vno, type, ref, narr, dr, cr, tag}
  const theirs = []; // {date, doc, narr, lpo, dr, cr, tag}
  const items = ['A4 copier paper (cartons)', 'Industrial gloves', 'Cleaning chemicals', 'Safety shoes', 'Cable ties & fasteners', 'Printer toner cartridges', 'Warehouse racking spares', 'Hand pallet trucks service', 'Stretch film', 'PPE coveralls'];

  // ---- 41 invoices booked on both sides (one with a 0.50 rounding difference) ----
  const N = 44;
  const ROUND = 33, DUP = 18;
  const invPool = days.filter((x) => x <= d(2026, 9, 24));
  const invDays = Array.from({ length: N }, () => rng.pick(invPool)).sort((a, b) => a - b);
  const invoices = invDays.map((dt, i) => {
    const no = `GS-INV-${5520 + i * 2 + rng.int(0, 1)}`;
    const amount = i === ROUND ? P.roundOurs : amts.take(950, 18500);
    return { i, no, date: dt, amount, lpo: `PO-DP-${pad(3100 + i, 5)}`, item: rng.pick(items) };
  });
  let pv = 1, pi = 1;
  const mo = (x) => (x.getUTCMonth() === 7 ? '2608' : '2609');
  for (const inv of invoices) {
    const ourDate = bizFwd(addDays(inv.date, rng.int(0, 4)));
    ours.push({ date: ourDate, vno: `PI-${mo(ourDate)}-${pad(pi++, 4)}`, type: 'Purchase Invoice', ref: inv.no, narr: `${inv.item} - ${inv.lpo}`, dr: 0, cr: inv.amount, tag: inv.i === ROUND ? 'rounding' : 'invoice' });
    const row = { date: inv.date, doc: inv.no, narr: `Tax invoice - ${inv.item}`, lpo: inv.lpo, dr: inv.i === ROUND ? P.roundTheirs : inv.amount, cr: 0, tag: inv.i === ROUND ? 'rounding' : 'invoice' };
    theirs.push(row);
    if (inv.i === DUP) theirs.push({ ...row, tag: 'duplicate' }); // same invoice listed twice in the SOA
  }

  // ---- Debit note (ours) = supplier credit note (theirs) ----
  ours.push({ date: d(2026, 8, 27), vno: 'DN-2608-0031', type: 'Debit Note', ref: 'CN-0118', narr: `Debit note DN-0031 - damaged stock returned on ${invoices[6].no} (supplier CN-0118)`, dr: P.dn, cr: 0, tag: 'debit-note' });
  theirs.push({ date: d(2026, 8, 25), doc: 'CN-0118', narr: 'Credit note against your debit note DN-0031', lpo: invoices[6].lpo, dr: 0, cr: P.dn, tag: 'debit-note' });

  // ---- Payments: we settle groups of 1-3 invoices 25-45 days after invoice ----
  const payable = invoices.filter((x) => x.i !== ROUND && x.i !== 6);
  const payments = [];
  // Payments have the opposite sign to invoices, so they only need to be unique among themselves.
  const pays = new Set([P.dn]);
  let k = 0;
  while (k < payable.length) {
    const size = Math.min(rng.int(1, 3), payable.length - k);
    const grp = payable.slice(k, k + size);
    const date = bizFwd(addDays(grp[grp.length - 1].date, rng.int(8, 26)));
    if (date > d(2026, 9, 25)) break;
    const amount = sum(grp, (g) => g.amount);
    if (pays.has(amount)) { k += 1; continue; }
    pays.add(amount);
    k += size;
    const byCheque = payments.length % 3 === 1;
    const ref = byCheque ? pad(4300 + payments.length * 7, 6) : `FT26${pad(date.getUTCMonth() + 1, 2)}${rng.letters(3)}`;
    payments.push({ date, amount, ref, byCheque, grp, theirDate: bizFwd(addDays(date, rng.int(0, 3))) });
  }
  for (const p of payments) {
    ours.push({ date: p.date, vno: `PV-${mo(p.date)}-${pad(pv++, 4)}`, type: 'Payment', ref: p.ref, narr: `${p.byCheque ? 'Cheque' : 'Bank transfer'} to ${SUPP} - ${p.grp.map((g) => g.no).join(', ')}`, dr: p.amount, cr: 0, tag: 'payment' });
    theirs.push({ date: p.theirDate, doc: p.byCheque ? `CHQ ${p.ref}` : p.ref, narr: `Payment received - thank you (${p.grp.map((g) => g.no.replace('GS-INV-', '')).join('/')})`, lpo: '', dr: 0, cr: p.amount, tag: 'payment' });
  }

  // ---- Payment in transit (ours only): FT sent 30-Sep, supplier receives 01-Oct ----
  const pit = { date: d(2026, 9, 30), ref: 'FT2609GSP', amount: amts.take(6000, 14000) };
  ours.push({ date: pit.date, vno: `PV-2609-${pad(pv++, 4)}`, type: 'Payment', ref: pit.ref, narr: `Bank transfer to ${SUPP} - on account (value 01-Oct)`, dr: pit.amount, cr: 0, tag: 'payment-in-transit' });

  // ---- Supplier invoice missing from our books ----
  const missing = { date: d(2026, 9, 26 + 0), no: 'GS-INV-5611', amount: amts.take(7000, 12000) };
  missing.date = bizFwd(missing.date);
  theirs.push({ date: missing.date, doc: missing.no, narr: 'Tax invoice - Warehouse racking spares (delivered to Jebel Ali store)', lpo: 'PO-DP-03187', dr: missing.amount, cr: 0, tag: 'missing-in-ours' });

  ours.sort((a, b) => a.date - b.date || (a.dr ? 1 : 0) - (b.dr ? 1 : 0));
  theirs.sort((a, b) => a.date - b.date || (a.cr ? 1 : 0) - (b.cr ? 1 : 0));
  const oursClose = runBalance(ours, OPENING, (r) => r.cr - r.dr); // credit balance = owed to supplier
  const theirsClose = runBalance(theirs, OPENING, (r) => r.dr - r.cr); // debit balance = receivable from us

  const map = (r) => ({ ...r, dr: r.dr ? toAed(r.dr) : null, cr: r.cr ? toAed(r.cr) : null, balance: toAed(r.balance) });
  await writeLedger(`${outDir}/ap/Our_AP_Ledger_Gulf_Supplies.xlsx`, {
    sheet: 'Supplier Ledger',
    titles: [OUR_COMPANY, `Supplier Ledger - S-0318 ${SUPP}`, 'Period: 01-Aug-2026 to 30-Sep-2026    Currency: AED    (balance = amount payable)'],
    columns: [
      { header: 'Date', key: 'date', width: 13, type: 'date' },
      { header: 'Voucher No', key: 'vno', width: 15 },
      { header: 'Type', key: 'type', width: 17 },
      { header: 'Supplier Inv / Ref', key: 'ref', width: 18 },
      { header: 'Narration', key: 'narr', width: 62 },
      { header: 'Debit', key: 'dr', width: 14, type: 'amount' },
      { header: 'Credit', key: 'cr', width: 14, type: 'amount' },
      { header: 'Balance', key: 'balance', width: 15, type: 'amount' },
    ],
    rows: [
      { date: d(2026, 8, 1), narr: 'Opening balance', balance: toAed(OPENING), _style: 'balance' },
      ...ours.map(map),
      { date: d(2026, 9, 30), narr: 'Closing balance', balance: toAed(oursClose), _style: 'balance' },
    ],
  });
  await writeLedger(`${outDir}/ap/Gulf_Supplies_SOA.xlsx`, {
    sheet: 'Statement',
    titles: ['GULF SUPPLIES LLC', 'Warehouse 7, Al Quoz Industrial Area 4, Dubai, UAE  |  TRN 100229384700003', 'CUSTOMER STATEMENT OF ACCOUNT', `Customer: ${OUR_COMPANY} (A/c DP-0441)    From 01-Aug-2026 to 30-Sep-2026`, ''],
    columns: [
      { header: 'Date', key: 'date', width: 13, type: 'date' },
      { header: 'Invoice / Doc No', key: 'doc', width: 17 },
      { header: 'Description', key: 'narr', width: 56 },
      { header: 'LPO No', key: 'lpo', width: 14 },
      { header: 'Debit', key: 'dr', width: 14, type: 'amount' },
      { header: 'Credit', key: 'cr', width: 14, type: 'amount' },
      { header: 'Balance', key: 'balance', width: 15, type: 'amount' },
    ],
    rows: [
      { date: d(2026, 8, 1), narr: 'Balance brought forward', balance: toAed(OPENING), _style: 'balance' },
      ...theirs.map(map),
      { date: d(2026, 9, 30), narr: 'Closing balance', balance: toAed(theirsClose), _style: 'balance' },
    ],
  });

  const dup = invoices[DUP];
  const rnd = invoices[ROUND];
  const roundDiff = P.roundTheirs - P.roundOurs;
  const result = oursClose + pit.amount + missing.amount + dup.amount + roundDiff;
  const statement = [
    ['Balance as per our books (Cr, 30-Sep-2026)', oursClose],
    [`Add: payment in transit in our books, not theirs - ${pit.ref} ${fmtDate(pit.date)}`, pit.amount],
    [`Add: invoice in supplier SOA not in our books - ${missing.no} (possible unrecorded liability)`, missing.amount],
    [`Add: duplicate line in supplier SOA - ${dup.no} listed twice`, dup.amount],
    [`Add: rounding difference on ${rnd.no} (ours ${fmtAmt(P.roundOurs)} vs theirs ${fmtAmt(P.roundTheirs)})`, roundDiff],
    ["Balance as per supplier's statement (Dr, 30-Sep-2026)", result],
    ["Balance per supplier's statement (file)", theirsClose],
    ['Unexplained difference', theirsClose - result],
  ];
  if (theirsClose - result !== 0) throw new Error('AP statement does not tie');

  const scenarios = [
    { s: 'Matching invoices', d: `${N - 2} supplier invoices; we book them 0-4 days after the supplier's invoice date`, e: 'Matched' },
    { s: 'Payments', d: `${payments.length} payments; cheques shown as "CHQ 004307" in the SOA vs "004307" in ours`, e: 'Matched (Normalised strips the CHQ prefix)' },
    { s: 'Debit note', d: `Our DN-0031 ${fmtAmt(P.dn)} (ours Debit 27-Aug, ref CN-0118) = supplier credit note CN-0118 (theirs Credit 25-Aug)`, e: 'Matched' },
    { s: 'Duplicate invoice line in SOA', d: `${dup.no} ${fmtAmt(dup.amount)} appears twice in the supplier SOA, once in ours`, e: 'Doubtful - "Multiple identical candidates" (1 line ours, 2 lines theirs)' },
    { s: 'Rounding difference', d: `${rnd.no}: ours ${fmtAmt(P.roundOurs)} vs theirs ${fmtAmt(P.roundTheirs)}`, e: 'Doubtful - "Reference and date agree; amount differs by 0.50" (small difference within 1%)' },
    { s: 'Supplier invoice missing from our books', d: `${missing.no} ${fmtDate(missing.date)} ${fmtAmt(missing.amount)}`, e: 'Unmatched - theirs, labelled "Possible unrecorded liability"' },
    { s: 'Payment in transit (ours only)', d: `${pit.ref} ${fmtDate(pit.date)} ${fmtAmt(pit.amount)}`, e: 'Unmatched - ours' },
  ];
  // The rounding invoice's dates are within tolerance; its doubtful is by amount.
  const matched = N - 2 + payments.length + 1;
  return {
    key: 'ap',
    files: ['ap/Our_AP_Ledger_Gulf_Supplies.xlsx', 'ap/Gulf_Supplies_SOA.xlsx'],
    rowsA: ours.length, rowsB: theirs.length, opening: OPENING, closeA: oursClose, closeB: theirsClose,
    tiers: { matched, doubtful: 2, doubtfulB: 3, likely: 0, unmatchedA: 1, unmatchedB: 1 },
    planted: { dupNo: dup.no, roundNo: rnd.no, missingNo: missing.no, pitRef: pit.ref },
    statement, scenarios,
  };
}
