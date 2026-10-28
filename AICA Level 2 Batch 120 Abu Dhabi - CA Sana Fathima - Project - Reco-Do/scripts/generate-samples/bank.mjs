// Bank module samples: ENBD current account statement vs GL 101200 cash account (Sep 2026).
import { Rng, UniqueAmounts } from './lib/rng.mjs';
import { d, addDays, businessDays, isWeekend, fmtDate, fmtAmt, toAed, sum, pad } from './lib/util.mjs';
import { newWorkbook, writeTable, saveWorkbook } from './lib/excel.mjs';
import { OUR_COMPANY, CUSTOMERS, SUPPLIERS, POS_MERCHANTS } from './lib/names.mjs';

export const BANK_OPENING = 124567835; // 1,245,678.35 (cents), same on both sides
const ACCOUNT_NO = '1012-4587-001';
const POS_CATEGORY = {
  'PETRO STAR SERVICE STN 214': 'Fuel - delivery vans', 'DUNE FUEL 1187 AL QUOZ': 'Fuel - delivery vans',
  'SAND CITY HYPERMARKET': 'Staff welfare - pantry', 'GREEN BASKET HYPERMARKET QUSAIS': 'Staff welfare - pantry',
  'TOOLMART HARDWARE FESTIVAL': 'Repairs & maintenance', 'PAPERLINE STATIONERY AL BARSHA': 'Office supplies',
  'TOLL GATE TOP UP': 'Vehicle tolls', 'CITY PARKING ONLINE': 'Parking', 'SOUQ CART ONLINE': 'Office supplies - online order',
  'DESERT COURIER EXPRESS': 'Courier charges',
};
const IBAN = 'AE070260001012458700100';

export async function generateBank(outDir) {
  const rng = new Rng(2026090101);
  const amts = new UniqueAmounts(rng);
  const usedRefs = new Set();
  const uref = (fn) => {
    for (;;) {
      const r = fn();
      if (!usedRefs.has(r)) {
        usedRefs.add(r);
        return r;
      }
    }
  };
  const biz = businessDays(2026, 9);
  const bizBefore = (last) => biz.filter((x) => x <= last);
  let seq = 0;
  const bank = []; // {date, valueDate, desc, ref, dr, cr, tag, k}
  const gl = []; // {date, vtype, remarks, party, dr, cr, chq, tag, k}
  const addBank = (r) => bank.push({ valueDate: r.date, ref: '', dr: 0, cr: 0, k: rng.float(), seq: seq++, ...r });
  const addGl = (r) => gl.push({ chq: '', dr: 0, cr: 0, k: rng.float(), seq: seq++, ...r });
  const scenarios = [];
  // Fixed references used by planted scenarios are reserved up front so random refs never collide.
  for (const r of ['TT26092201', 'TT26093077', 'FT2609ABC', 'FT2609KLM', 'FT2609XRT', 'WPS2609280001']) usedRefs.add(r);
  const ourCheques = []; // GL/bank rows needing an issued cheque number (assigned in date order later)

  // ---- Reserve every planted amount first so random amounts never collide with them ----
  const P = {
    transBank: amts.reserve(845000),
    transGl: amts.reserve(854000),
    chgGl: amts.reserve(1850000),
    chgBank: amts.reserve(1847500),
    dup: amts.reserve(100000),
    split: amts.reserve(3675000),
    splitPart: amts.reserve(1225000),
    comboA: amts.reserve(941235),
    comboB: amts.reserve(618790),
    comboTotal: amts.reserve(1560025),
    feeChqBook: amts.reserve(3500),
    vatChqBook: amts.reserve(175),
    feeTt: amts.reserve(7500),
    vatTt: amts.reserve(375),
    feeMonthly: amts.reserve(5000),
    vatMonthly: amts.reserve(250),
    interest: amts.reserve(41237),
    unknownTt: amts.reserve(421560),
    cdmUncredited: amts.reserve(678025),
    likely: amts.reserve(2341860),
  };

  const UP = (s) => s.toUpperCase();
  const inv = () => `INV-2026-${rng.int(700, 980)}`;
  const bill = () => `${rng.letters(2)}/${rng.int(1000, 9999)}`;

  // ---- Exact-match transaction makers ----
  const makers = {
    ttIn: () => {
      const party = rng.pick(CUSTOMERS);
      const ref = uref(() => `TT2609${rng.digits(4)}`);
      return { dir: 'in', amount: amts.take(2500, 95000), party, ref, chq: ref, vtype: 'Bank Receipt',
        desc: `INWARD TT ${ref} FROM ${UP(party)}`, remarks: `Receipt from ${party} against ${inv()}` };
    },
    ftIn: () => {
      const party = rng.pick(CUSTOMERS);
      const ref = uref(() => `FT2609${rng.letters(3)}`);
      return { dir: 'in', amount: amts.take(1200, 60000), party, ref, chq: ref, vtype: 'Bank Receipt',
        desc: `IPP CREDIT ${ref} ${UP(party)} INV PAYMENT`, remarks: `Receipt from ${party} - ${inv()}` };
    },
    chqIn: () => {
      const party = rng.pick(CUSTOMERS);
      const ref = uref(() => `${rng.int(1, 9)}${rng.digits(5)}`);
      return { dir: 'in', amount: amts.take(1500, 48000), party, ref, chq: ref, vtype: 'Bank Receipt', valueLag: 1,
        desc: `CHQ DEPOSIT ${ref} ${UP(party)} - CLEARING`, remarks: `Cheque ${ref} received from ${party}` };
    },
    chqOut: () => {
      const party = rng.pick(SUPPLIERS);
      return { dir: 'out', amount: amts.take(900, 42000), party, ref: null, chq: null, vtype: 'Bank Payment', ourCheque: true,
        desc: 'CHEQUE NO {CHQ} PRESENTED - INWARD CLEARING', remarks: `Paid to ${party} - bill ${bill()}` };
    },
    ftOut: () => {
      const party = rng.pick(SUPPLIERS);
      const ref = uref(() => `FT2609${rng.letters(3)}`);
      const b = bill();
      return { dir: 'out', amount: amts.take(650, 55000), party, ref, chq: ref, vtype: 'Bank Payment',
        desc: `FT OUT ${ref} TO ${UP(party)} BILL ${b}`, remarks: `Payment to ${party} - bill ${b}` };
    },
    ttOut: () => {
      const party = rng.pick(SUPPLIERS);
      const ref = uref(() => `TT2609${rng.digits(4)}`);
      return { dir: 'out', amount: amts.take(8000, 120000), party, ref, chq: ref, vtype: 'Bank Payment',
        desc: `OUTWARD TT ${ref} BENEF ${UP(party)}`, remarks: `TT to ${party} - import shipment ${rng.letters(3)}${rng.digits(4)}` };
    },
    pos: () => {
      const m = rng.pick(POS_MERCHANTS);
      const ref = uref(() => `6${rng.digits(11)}`);
      const cat = POS_CATEGORY[m] ?? 'Sundry expenses';
      return { dir: 'out', amount: amts.take(45, 2800), party: m.replace(/\b\w+/g, (w) => w[0] + w.slice(1).toLowerCase()), ref, chq: ref,
        vtype: 'Bank Payment', desc: `POS PURCHASE ${m} AE CARD ****2231`, remarks: cat };
    },
    dd: () => {
      const u = rng.pick([
        ['UTILITIES ELEC & WATER', 'Electricity & water - warehouse', 'Utility Authority'],
        ['TELECOM MOBILE & INTERNET', 'Telephone & internet', 'Telecom Provider'],
        ['MEDICAL INSURANCE PREMIUM', 'Staff medical insurance', 'Al Safa Insurance Co'],
        ['VEHICLE LEASE INSTALMENT', 'Vehicle lease - delivery fleet', 'Fleet Lease Finance'],
      ]);
      const ref = uref(() => `DD2609${rng.digits(5)}`);
      return { dir: 'out', amount: amts.take(1200, 18000), party: u[2], ref, chq: ref, vtype: 'Bank Payment',
        desc: `DIRECT DEBIT ${u[0]} A/C ${rng.digits(8)}`, remarks: u[1] };
    },
  };
  const mix = [
    ['ttIn', 45], ['ftIn', 40], ['chqIn', 30], ['chqOut', 45], ['ftOut', 46], ['ttOut', 12], ['pos', 20], ['dd', 8],
  ];

  function emitPair(t, glDate, bankDate, opts = {}) {
    const bRow = {
      date: bankDate, valueDate: t.valueLag ? nextBizDay(bankDate) : bankDate,
      desc: t.desc, ref: opts.bankRef !== undefined ? opts.bankRef : t.ref, tag: opts.tag ?? 'exact',
      [t.dir === 'in' ? 'cr' : 'dr']: opts.bankAmount ?? t.amount,
    };
    const gRow = {
      date: glDate, vtype: t.vtype, remarks: opts.remarks ?? t.remarks, party: t.party,
      chq: opts.glChq !== undefined ? opts.glChq : t.chq, tag: opts.tag ?? 'exact',
      [t.dir === 'in' ? 'dr' : 'cr']: opts.glAmount ?? t.amount,
    };
    addBank(bRow);
    addGl(gRow);
    if (t.ourCheque) ourCheques.push({ b: bank[bank.length - 1], g: gl[gl.length - 1], noZeros: !!opts.noZeros });
    return { b: bank[bank.length - 1], g: gl[gl.length - 1] };
  }
  function nextBizDay(x) {
    let y = addDays(x, 1);
    while (isWeekend(y)) y = addDays(y, 1);
    return y;
  }

  // ---- 1. Exact matches (247 pairs) ----
  const exactDays = biz.filter((x) => x.getUTCDate() <= 28);
  let noZeroCount = 0;
  for (const [kind, n] of mix) {
    for (let i = 0; i < n; i++) {
      const t = makers[kind]();
      const dt = rng.pick(exactDays);
      const noZeros = kind === 'chqOut' && noZeroCount < 5 && i % 9 === 4;
      if (noZeros) noZeroCount++;
      emitPair(t, dt, dt, { noZeros });
    }
  }
  // Payroll via WPS (exact match)
  const salaryAmt = amts.take(405000, 420000);
  emitPair({ dir: 'out', amount: salaryAmt, party: 'Employees - WPS', ref: 'WPS2609280001', chq: 'WPS2609280001', vtype: 'Bank Payment',
    desc: 'SALARY TRANSFER WPS SEP 2026 MOL EST 1123456', remarks: 'Payroll September 2026 - WPS transfer' }, d(2026, 9, 28), d(2026, 9, 28));
  const exactCount = sum(mix, (m) => m[1]) + 1;

  // ---- 2. Date shifts ----
  const shifts = [1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 5, 5];
  const shiftRows = [];
  for (const [i, s] of shifts.entries()) {
    const t = i % 2 === 0 ? makers.chqOut() : makers.chqIn();
    let g;
    for (;;) {
      g = rng.pick(bizBefore(d(2026, 9, 25)));
      if (!isWeekend(addDays(g, s))) break;
    }
    const pr = emitPair(t, g, addDays(g, s), { tag: s <= 3 ? 'shift-ok' : 'shift-doubtful' });
    shiftRows.push({ ...pr, s, t });
  }

  // ---- 3. Likely: amount only (bank has no ref, GL booked 12 days earlier) ----
  addGl({ date: d(2026, 9, 16), vtype: 'Bank Receipt', remarks: 'Cash sales deposited - showroom (week 37)', party: 'Cash Sales', chq: 'DEP-160926', dr: P.likely, tag: 'likely' });
  addBank({ date: d(2026, 9, 28), desc: 'CASH DEPOSIT CDM AL BARSHA BR', ref: '', cr: P.likely, tag: 'likely' });

  // ---- 4. Missing references on the bank side ----
  const missing = [
    { dir: 'in', amount: amts.take(3000, 20000), party: 'Cash Sales', chq: 'DEP-0907', vtype: 'Bank Receipt', desc: 'CASH DEPOSIT - DEIRA BRANCH', remarks: 'Cash sales deposited - Deira showroom', day: 7 },
    { dir: 'in', amount: amts.take(5000, 40000), party: 'Sahara Star Foodstuff Trading', chq: uref(() => `TT2609${rng.digits(4)}`), vtype: 'Bank Receipt', desc: 'INWARD REMITTANCE - SAHARA STAR FOODSTUFF', remarks: 'Receipt from Sahara Star Foodstuff Trading - INV-2026-0861', day: 11 },
    { dir: 'in', amount: amts.take(50000, 90000), party: 'Desert Pearl Trading LLC - Call A/c', chq: 'TRF-0915', vtype: 'Contra', desc: 'TRANSFER FROM A/C 1012-4587-002', remarks: 'Transfer from call account to current account', day: 15 },
    { dir: 'out', amount: amts.take(20000, 35000), party: 'Al Barsha Properties LLC', chq: 'SO-2609', vtype: 'Bank Payment', desc: 'STANDING ORDER - WAREHOUSE 14 RENT', remarks: 'Warehouse 14 rent - Sep 2026 instalment', day: 21 },
  ];
  for (const m of missing) emitPair({ ...m, ref: m.chq }, d(2026, 9, m.day), d(2026, 9, m.day), { bankRef: '', tag: 'missing-ref' });

  // ---- 5. References written differently (bank FT ref; GL cheque no blank, ref inside remarks) ----
  const diffRefs = [['FT2609ABC', 'Al Noor Trading LLC', 4], ['FT2609KLM', 'Hatta Fresh Dairy LLC', 14], ['FT2609XRT', 'Silver Dune Events LLC', 23]];
  const diffRows = [];
  for (const [ref, party, day] of diffRefs) {
    const amount = amts.take(4000, 30000);
    emitPair({ dir: 'in', amount, party, ref, chq: '', vtype: 'Bank Receipt', desc: `IPP CREDIT ${ref} ${UP(party)}`, remarks: `Rcpt ${ref} - ${party}` },
      d(2026, 9, day), d(2026, 9, day), { tag: 'ref-written-differently' });
    diffRows.push({ ref, party, amount, day });
  }

  // ---- 6. Transposition (our cheque, bank 8,450.00 vs GL 8,540.00) ----
  const trans = emitPair({ dir: 'out', amount: 0, party: 'Creek Side Electricals LLC', vtype: 'Bank Payment', ourCheque: true,
    desc: 'CHEQUE NO {CHQ} PRESENTED - INWARD CLEARING', remarks: 'Paid to Creek Side Electricals LLC - bill CE/4471' },
  d(2026, 9, 17), d(2026, 9, 17), { bankAmount: P.transBank, glAmount: P.transGl, tag: 'transposition' });

  // ---- 7. Bank-charge style difference (correspondent charge deducted from TT receipt) ----
  const chgRef = uref(() => `TT2609${rng.digits(4)}`);
  addBank({ date: d(2026, 9, 9), desc: `INWARD TT ${chgRef} FROM CORNICHE HOSPITALITY SERVICES NET OF CORR CHGS`, ref: chgRef, cr: P.chgBank, tag: 'charge-diff' });
  addGl({ date: d(2026, 9, 9), vtype: 'Bank Receipt', remarks: 'Receipt from Corniche Hospitality Services - INV-2026-0802', party: 'Corniche Hospitality Services', chq: chgRef, dr: P.chgGl, tag: 'charge-diff' });

  // ---- 8. Three identical 1,000.00 ATM withdrawals on the same day (duplicate rule) ----
  for (let i = 0; i < 3; i++) {
    addBank({ date: d(2026, 9, 15), desc: 'ATM CASH WITHDRAWAL DEIRA CITY CENTRE CARD ****2231', ref: '', dr: P.dup, tag: 'duplicate' });
    addGl({ date: d(2026, 9, 15), vtype: 'Bank Payment', remarks: 'Petty cash replenishment (ATM withdrawal)', party: 'Petty Cash', chq: '', cr: P.dup, tag: 'duplicate' });
  }

  // ---- 9. 1 bank : 3 GL split ----
  const splitRef = 'TT26092201';
  addBank({ date: d(2026, 9, 22), desc: `INWARD TT ${splitRef} FROM BIN HAMDAN BUILDING MATERIALS LLC`, ref: splitRef, cr: P.split, tag: 'split-1-3' });
  for (const n of ['0811', '0812', '0813'])
    addGl({ date: d(2026, 9, 22), vtype: 'Bank Receipt', remarks: `Receipt from Bin Hamdan Building Materials LLC - INV-2026-${n}`, party: 'Bin Hamdan Building Materials LLC', chq: '', dr: P.splitPart, tag: 'split-1-3' });

  // ---- 10. 2 bank : 1 GL combination ----
  const cRefA = uref(() => `TT2609${rng.digits(4)}`);
  const cRefB = uref(() => `TT2609${rng.digits(4)}`);
  addBank({ date: d(2026, 9, 10), desc: `INWARD TT ${cRefA} FROM FALCON CREST LOGISTICS FZE`, ref: cRefA, cr: P.comboA, tag: 'combo-2-1' });
  addBank({ date: d(2026, 9, 10), desc: `INWARD TT ${cRefB} FROM FALCON CREST LOGISTICS FZE`, ref: cRefB, cr: P.comboB, tag: 'combo-2-1' });
  addGl({ date: d(2026, 9, 10), vtype: 'Bank Receipt', remarks: 'Receipt from Falcon Crest Logistics FZE - INV-2026-0790 & 0794 (2 TTs)', party: 'Falcon Crest Logistics FZE', chq: '', dr: P.comboTotal, tag: 'combo-2-1' });

  // ---- 11. Card-sales settlements: GL books the daily total, bank credits each of 3 terminals ----
  const posDays = [3, 8, 11, 18, 24, 25].map((x) => d(2026, 9, x));
  const posBatches = [];
  for (const pd of posDays) {
    let parts, total;
    for (;;) {
      parts = [rng.cents(1800, 9500), rng.cents(1800, 9500), rng.cents(900, 6000)];
      total = sum(parts);
      if (new Set(parts).size === 3 && ![...parts, total].some((c) => amts.used.has(c))) break;
    }
    parts.forEach((c) => amts.reserve(c));
    amts.reserve(total);
    const dd = pad(pd.getUTCDate(), 2);
    parts.forEach((c, i) => {
      const ref = uref(() => `MS2609${dd}0${i + 1}`);
      addBank({ date: pd, desc: `POS SETTLEMENT MID 200456710 TID 0${i + 1} BATCH ${dd}09`, ref, cr: c, tag: 'pos-batch' });
    });
    addGl({ date: pd, vtype: 'Bank Receipt', remarks: `Card sales settlement ${fmtDate(pd)} (3 terminals)`, party: 'Card Sales - Merchant Account', chq: '', dr: total, tag: 'pos-batch' });
    posBatches.push({ date: pd, parts, total });
  }

  // ---- 12. Bank-only items (charges, VAT, interest, unidentified credit) ----
  const bankOnly = [
    { date: d(2026, 9, 3), desc: 'CHARGES - CHEQUE BOOK ISSUANCE 50 LVS', dr: P.feeChqBook },
    { date: d(2026, 9, 3), desc: 'VAT 5% ON CHARGES', dr: P.vatChqBook },
    { date: d(2026, 9, 16), desc: 'CHARGES - OUTWARD TT COMMISSION', dr: P.feeTt },
    { date: d(2026, 9, 16), desc: 'VAT 5% ON CHARGES', dr: P.vatTt },
    { date: d(2026, 9, 30), desc: 'CHARGES - MONTHLY ACCOUNT MAINTENANCE FEE', dr: P.feeMonthly, late: true },
    { date: d(2026, 9, 30), desc: 'VAT 5% ON CHARGES', dr: P.vatMonthly, late: true },
    { date: d(2026, 9, 30), desc: 'INTEREST CREDIT - SEP 2026', cr: P.interest, late: true },
    { date: d(2026, 9, 30), desc: 'INWARD TT TT26093077 UNIDENTIFIED REMITTER REF SDT/88213', cr: P.unknownTt, ref: 'TT26093077' },
  ];
  bankOnly.forEach((b, i) => {
    const ref = b.ref ?? uref(() => `SC2609${rng.digits(5)}`);
    // `late` items (month-end charges and interest) sort to the end of the last day
    addBank({ ...b, ref, tag: 'bank-only', k: b.late ? 2 + i / 100 : rng.float() });
  });

  // ---- 13. GL-only: unpresented cheques ----
  const unpresented = [];
  for (const day of [24, 25, 28, 29, 30, 30]) {
    const party = rng.pick(SUPPLIERS);
    const amount = amts.take(2000, 28000);
    addGl({ date: d(2026, 9, day), vtype: 'Bank Payment', remarks: `Paid to ${party} - bill ${bill()}`, party, chq: null, cr: amount, tag: 'unpresented' });
    const g = gl[gl.length - 1];
    ourCheques.push({ b: null, g, noZeros: false });
    unpresented.push(g);
  }

  // ---- 14. GL-only: uncredited deposits (one is the date-only coincidence with the unidentified bank TT) ----
  const uncredited = [];
  const ucChq = uref(() => `11${rng.digits(4)}`);
  addGl({ date: d(2026, 9, 29), vtype: 'Bank Receipt', remarks: `Cheque ${ucChq} received from Palm Horizon Contracting LLC - deposited 29-Sep`, party: 'Palm Horizon Contracting LLC', chq: ucChq, dr: amts.take(9000, 26000), tag: 'uncredited' });
  uncredited.push(gl[gl.length - 1]);
  addGl({ date: d(2026, 9, 30), vtype: 'Bank Receipt', remarks: 'Cash sales deposited via CDM - 30 Sep collections', party: 'Cash Sales', chq: 'CDM300926', dr: P.cdmUncredited, tag: 'uncredited' });
  uncredited.push(gl[gl.length - 1]);
  const ucTt = uref(() => `TT260930${rng.digits(2)}`);
  addGl({ date: d(2026, 9, 30), vtype: 'Bank Receipt', remarks: `Receipt from Marina Bay Yacht Supplies FZCO - TT advised (${ucTt})`, party: 'Marina Bay Yacht Supplies FZCO', chq: ucTt, dr: amts.take(12000, 30000), tag: 'uncredited' });
  uncredited.push(gl[gl.length - 1]);

  // ---- Assign our cheque numbers in GL date order ----
  ourCheques.sort((a, b) => a.g.date - b.g.date || a.g.seq - b.g.seq);
  let chqNo = 4478;
  for (const oc of ourCheques) oc.no = pad(chqNo++, 6);
  // The planted transposition always uses cheque 004512 (swap with whichever cheque drew that number).
  const tOc = ourCheques.find((oc) => oc.b === trans.b);
  const other = ourCheques.find((oc) => oc.no === '004512');
  [tOc.no, other.no] = [other.no, tOc.no];
  for (const oc of ourCheques) {
    usedRefs.add(oc.no);
    oc.g.chq = oc.noZeros ? String(Number(oc.no)) : oc.no;
    if (oc.b) {
      oc.b.ref = oc.no;
      oc.b.desc = oc.b.desc.replace('{CHQ}', oc.no);
    }
  }
  const transChq = trans.b.ref;
  const noZeroChqs = ourCheques.filter((oc) => oc.noZeros).map((oc) => `bank "${oc.no}" vs GL "${oc.g.chq}"`);

  // ---- Sort, number and balance ----
  bank.sort((a, b) => a.date - b.date || a.k - b.k);
  gl.sort((a, b) => a.date - b.date || a.k - b.k);
  let bal = BANK_OPENING;
  let minBal = bal;
  for (const r of bank) {
    bal += r.cr - r.dr;
    r.balance = bal;
    minBal = Math.min(minBal, bal);
  }
  const bankClose = bal;
  const vtCodes = { 'Bank Receipt': 'BR', 'Bank Payment': 'BP', Contra: 'CV', Journal: 'JV' };
  const vtSeq = {};
  for (const r of gl) {
    const c = vtCodes[r.vtype];
    vtSeq[c] = (vtSeq[c] ?? 0) + 1;
    r.docNo = `${c}-2609-${pad(vtSeq[c], 4)}`;
  }
  const glClose = BANK_OPENING + sum(gl, (r) => r.dr) - sum(gl, (r) => r.cr);
  if (minBal < 0) throw new Error('Bank balance went negative');

  // ---- Write bank statement (6 junk rows above the header) ----
  {
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Statement');
    const junk = [
      'Emirates NBD Bank PJSC',
      'Deira Main Branch, Baniyas Road, P.O. Box 777, Dubai, United Arab Emirates',
      `Account Name: ${UP(OUR_COMPANY)}    Account No: ${ACCOUNT_NO}    Currency: AED`,
      `IBAN: ${IBAN}    Account Type: Current Account - Business`,
      'Statement Period: 01-Sep-2026 to 30-Sep-2026',
      '',
    ];
    junk.forEach((t, i) => {
      if (t) ws.getCell(i + 1, 1).value = t;
    });
    ws.getCell(1, 1).font = { bold: true, size: 14 };
    const rows = [
      { txn: d(2026, 9, 1), desc: 'Opening balance', balance: toAed(BANK_OPENING), _style: 'balance' },
      ...bank.map((r) => ({ txn: r.date, val: r.valueDate, desc: r.desc, ref: r.ref, dr: r.dr ? toAed(r.dr) : null, cr: r.cr ? toAed(r.cr) : null, balance: toAed(r.balance) })),
      { txn: d(2026, 9, 30), desc: 'Closing balance', balance: toAed(bankClose), _style: 'balance' },
    ];
    writeTable(ws, {
      headerRow: 7,
      columns: [
        { header: 'Txn Date', key: 'txn', width: 13, type: 'date' },
        { header: 'Value Date', key: 'val', width: 13, type: 'date' },
        { header: 'Description', key: 'desc', width: 62 },
        { header: 'Reference No', key: 'ref', width: 16 },
        { header: 'Debit', key: 'dr', width: 15, type: 'amount' },
        { header: 'Credit', key: 'cr', width: 15, type: 'amount' },
        { header: 'Balance', key: 'balance', width: 17, type: 'amount' },
      ],
      rows,
    });
    await saveWorkbook(wb, `${outDir}/bank/ENBD_Current_Statement_Sep2026.xlsx`);
  }
  // ---- Write GL extract (header on row 1) ----
  {
    const wb = newWorkbook();
    const ws = wb.addWorksheet('GL 101200');
    const rows = [
      { date: d(2026, 9, 1), vtype: 'Opening', remarks: 'Opening Balance', dr: toAed(BANK_OPENING), _style: 'balance' },
      ...gl.map((r) => ({ date: r.date, doc: r.docNo, vtype: r.vtype, remarks: r.remarks, party: r.party, dr: r.dr ? toAed(r.dr) : null, cr: r.cr ? toAed(r.cr) : null, chq: r.chq })),
      { date: d(2026, 9, 30), vtype: 'Closing', remarks: 'Closing Balance', dr: toAed(glClose), _style: 'balance' },
    ];
    writeTable(ws, {
      headerRow: 1,
      autoFilter: true,
      columns: [
        { header: 'Posting Date', key: 'date', width: 13, type: 'date' },
        { header: 'Doc No', key: 'doc', width: 14 },
        { header: 'Voucher Type', key: 'vtype', width: 14 },
        { header: 'Remarks', key: 'remarks', width: 62 },
        { header: 'Party', key: 'party', width: 36 },
        { header: 'Debit', key: 'dr', width: 15, type: 'amount' },
        { header: 'Credit', key: 'cr', width: 15, type: 'amount' },
        { header: 'Cheque No', key: 'chq', width: 15 },
      ],
      rows,
    });
    await saveWorkbook(wb, `${outDir}/bank/GL_101200_Cash_Sep2026.xlsx`);
  }

  // ---- Expected results ----
  const U = sum(unpresented, (r) => r.cr);
  const D = sum(uncredited, (r) => r.dr);
  const bankOnlyCr = sum(bankOnly.filter((b) => b.cr), (b) => b.cr);
  const bankOnlyDr = sum(bankOnly.filter((b) => b.dr), (b) => b.dr);
  const chargeDiff = P.chgGl - P.chgBank; // bank received 25.00 less than GL
  const transDiff = P.transGl - P.transBank; // GL overstated the payment by 90.00
  const adjusted = bankClose - U + D - bankOnlyCr + bankOnlyDr + chargeDiff - transDiff;
  const statement = [
    ['Balance as per bank statement (30-Sep-2026)', bankClose],
    [`Less: unpresented cheques (in GL, not in bank) - ${unpresented.length} cheques ${unpresented.map((r) => r.chq).join(', ')}`, -U],
    [`Add: uncredited deposits (in GL, not in bank) - ${uncredited.length} items`, D],
    ['Less: bank credits not in GL (interest 412.37; unidentified TT TT26093077 4,215.60)', -bankOnlyCr],
    ['Add: bank debits not in GL (bank charges and VAT on charges)', bankOnlyDr],
    [`Add: correspondent charge deducted from TT ${chgRef} (bank ${fmtAmt(P.chgBank)} vs GL ${fmtAmt(P.chgGl)})`, chargeDiff],
    [`Less: GL error - cheque ${transChq} booked ${fmtAmt(P.transGl)}, cleared ${fmtAmt(P.transBank)}`, -transDiff],
    ['Adjusted balance', adjusted],
    ['Balance as per GL 101200 (30-Sep-2026)', glClose],
    ['Unexplained difference', glClose - adjusted],
  ];
  if (glClose - adjusted !== 0) throw new Error(`Bank statement does not tie: ${glClose - adjusted}`);

  const shiftOk = shiftRows.filter((x) => x.s <= 3);
  const shiftBad = shiftRows.filter((x) => x.s > 3);
  scenarios.push(
    { s: 'Exact matches', d: `${exactCount} pairs: same date, same reference, same amount (TT/FT/IPP receipts, cheque deposits, our cheques, FT/TT payments, POS card spend, direct debits, WPS salary ${fmtAmt(salaryAmt)} on 28-Sep). ${noZeroChqs.length} of our cheques are written without leading zeros in the GL: ${noZeroChqs.join(', ')}.`, e: 'Matched (with Reference rule = Normalised; with Exact the 5 no-leading-zero cheques become Doubtful)' },
    { s: 'Date shifts within tolerance', d: shiftOk.map((x) => `${x.b.ref} ${fmtAmt(x.t.amount)} +${x.s}d`).join('; '), e: 'Matched (date within +/-3 days); reason notes the day difference' },
    { s: 'Date shifts beyond tolerance', d: shiftBad.map((x) => `${x.b.ref} ${fmtAmt(x.t.amount)} GL ${fmtDate(x.g.date)} vs bank ${fmtDate(x.b.date)} (+${x.s}d)`).join('; '), e: 'Doubtful - "Reference and amount agree; date differs by 4/5 days"' },
    { s: 'Amount only (Likely)', d: `Cash deposit ${fmtAmt(P.likely)}: GL 16-Sep ref DEP-160926, bank 28-Sep CDM deposit with no reference`, e: 'Likely - only the amount agrees (date 12 days apart, bank reference blank)' },
    { s: 'Missing references (bank side blank)', d: missing.map((m) => `${fmtDate(d(2026, 9, m.day))} ${m.desc} ${fmtAmt(m.amount)} (GL ref ${m.chq})`).join('; '), e: 'Doubtful - "Amount and date agree; reference missing on bank side" (4 pairs)' },
    { s: 'References written differently', d: diffRows.map((x) => `bank ref ${x.ref} vs GL Cheque No blank + remarks "Rcpt ${x.ref} - ${x.party}" ${fmtAmt(x.amount)}`).join('; '), e: 'Doubtful with Reference No <-> Cheque No (amount + date agree). Becomes Matched if Reference is mapped to GL Remarks with rule "Contains"; Smart Recon partial-reference also finds it' },
    { s: 'Amount transposition', d: `CHQ ${transChq} (Creek Side Electricals LLC) 17-Sep: bank ${fmtAmt(P.transBank)} vs GL ${fmtAmt(P.transGl)}, reference + date agree`, e: 'Doubtful - "Reference and date agree; amount differs by 90.00 (possible transposition 8,450 vs 8,540)" (90 divisible by 9)' },
    { s: 'Bank-charge style difference', d: `TT ${chgRef} 09-Sep Corniche Hospitality: bank ${fmtAmt(P.chgBank)} vs GL ${fmtAmt(P.chgGl)}`, e: 'Doubtful - amount differs by 25.00, within 1% ("possible bank charge")' },
    { s: 'Duplicates (same amount, same day)', d: '3 x ATM withdrawals of 1,000.00 on 15-Sep in bank, 3 x petty-cash vouchers of 1,000.00 on 15-Sep in GL; references blank on both sides', e: 'Doubtful - "Multiple identical candidates" (3 bank lines, 3 GL lines); not auto-assigned' },
    { s: '1 bank : 3 GL split', d: `Bank TT ${splitRef} 22-Sep ${fmtAmt(P.split)} = 3 GL receipts of ${fmtAmt(P.splitPart)} (Bin Hamdan Building Materials LLC, INV-2026-0811/0812/0813)`, e: 'Unmatched in Step 3; Smart Recon sum-matching proposes the 1:3 group' },
    { s: '2 bank : 1 GL combination', d: `Bank TTs ${cRefA} ${fmtAmt(P.comboA)} + ${cRefB} ${fmtAmt(P.comboB)} on 10-Sep = GL receipt ${fmtAmt(P.comboTotal)} (Falcon Crest Logistics FZE)`, e: 'Unmatched in Step 3; Smart Recon proposes the 2:1 group' },
    { s: 'Card settlements 3 bank : 1 GL', d: posBatches.map((p) => `${fmtDate(p.date)}: ${p.parts.map(fmtAmt).join(' + ')} = ${fmtAmt(p.total)}`).join('; '), e: 'Unmatched in Step 3; Smart Recon proposes six 3:1 groups' },
    { s: 'Bank-only items', d: bankOnly.map((b) => `${fmtDate(b.date)} ${b.desc} ${fmtAmt(b.dr || b.cr)}${b.cr ? ' Cr' : ' Dr'}`).join('; '), e: 'Unmatched - bank (charges/VAT labelled "Probable bank charge - post JV"; interest and unidentified credit need a JV / investigation)' },
    { s: 'Unpresented cheques (GL only)', d: unpresented.map((r) => `${r.chq} ${fmtDate(r.date)} ${fmtAmt(r.cr)}`).join('; '), e: 'Unmatched - GL' },
    { s: 'Uncredited deposits (GL only)', d: uncredited.map((r) => `${r.chq} ${fmtDate(r.date)} ${fmtAmt(r.dr)}`).join('; '), e: 'Unmatched - GL' },
    { s: 'Date-only coincidence', d: `30-Sep: bank TT26093077 ${fmtAmt(P.unknownTt)} vs GL CDM300926 ${fmtAmt(P.cdmUncredited)} (same date, different amount and reference)`, e: 'Both stay Unmatched (date-only is never a match)' },
  );

  const tiers = {
    matched: exactCount + shiftOk.length,
    doubtful: shiftBad.length + missing.length + diffRows.length + 1 + 1 + 3,
    likely: 1,
    unmatchedA: 1 + 2 + posBatches.length * 3 + bankOnly.length,
    unmatchedB: 3 + 1 + posBatches.length + unpresented.length + uncredited.length,
  };
  return {
    key: 'bank',
    files: ['bank/ENBD_Current_Statement_Sep2026.xlsx', 'bank/GL_101200_Cash_Sep2026.xlsx'],
    rowsA: bank.length,
    rowsB: gl.length,
    opening: BANK_OPENING,
    closeA: bankClose,
    closeB: glClose,
    tiers,
    groups: { count: 2 + posBatches.length, bankLines: 3 + posBatches.length * 3, glLines: 4 + posBatches.length },
    totals: { unpresented: U, uncredited: D, bankOnlyCr, bankOnlyDr, chargeDiff, transDiff },
    planted: {
      transChq, transBank: P.transBank, transGl: P.transGl, dup: P.dup, split: P.split, splitPart: P.splitPart,
      comboA: P.comboA, comboB: P.comboB, comboTotal: P.comboTotal, diffRefs: diffRefs.map((x) => x[0]),
      unpresentedChqs: unpresented.map((r) => r.chq), posBatches: posBatches.map((p) => ({ parts: p.parts, total: p.total })),
    },
    statement,
    scenarios,
  };
}
