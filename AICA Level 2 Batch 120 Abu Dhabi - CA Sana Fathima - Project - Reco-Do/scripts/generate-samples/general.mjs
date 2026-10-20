// General module samples: HR master vs WPS payroll register (no amount) and intercompany A vs B (with amount).
import { Rng, UniqueAmounts } from './lib/rng.mjs';
import { d, addDays, dayDiff, businessDays, fmtDate, fmtAmt, toAed, sum, pad } from './lib/util.mjs';
import { newWorkbook, writeTable, saveWorkbook } from './lib/excel.mjs';
import { writeLedger, bizFwd } from './lib/ledger.mjs';
import { FIRST_MALE, FIRST_FEMALE, MIDDLE, LAST, DEPARTMENTS, UAE_BANKS, makeIban, OUR_COMPANY } from './lib/names.mjs';

const normName = (s) => s.toUpperCase().replace(/[^A-Z]/g, '');

// ---------------------------------------------------------------- HR vs WPS
export async function generateHrPayroll(outDir) {
  const rng = new Rng(2026090404);
  const usedNames = new Set();
  const usedIbans = new Set();
  const newIban = () => {
    for (;;) {
      const bank = rng.pick(UAE_BANKS);
      const iban = makeIban(bank.code, `${rng.int(1, 9)}${rng.digits(15)}`);
      if (!usedIbans.has(iban)) {
        usedIbans.add(iban);
        return { iban, bank: bank.name };
      }
    }
  };
  const bankOf = (iban) => UAE_BANKS.find((b) => b.code === iban.slice(4, 7)).name;
  const uniqName = (forced) => {
    if (forced) return forced; // forced names are pre-reserved below
    for (;;) {
      const female = rng.chance(0.22);
      const first = rng.pick(female ? FIRST_FEMALE : FIRST_MALE);
      const mid = rng.chance(0.6) ? ` ${rng.pick(MIDDLE)}` : '';
      const n = `${first}${mid} ${rng.pick(LAST)}`;
      if (!usedNames.has(normName(n))) {
        usedNames.add(normName(n));
        return n;
      }
    }
  };

  // Planted name variants (HR name -> payroll name). The first 6 fail a Normalised text compare,
  // the last 3 pass it (case / spacing only).
  const nameVariants = [
    ['Mohammed Rafi Abdul Kareem', 'Mohd Rafi Abdul Kareem', 'fail'],
    ['Fatima Noor Al Hashimi', 'Fatima Al Hashimi', 'fail'],
    ['Mohammed Iqbal Qureshi', 'Muhammad Iqbal Qureshi', 'fail'],
    ['Abdullah Salem Al Marri', 'Abdulla Salem Al Marri', 'fail'],
    ['Yousef Jamal Haddad', 'Yusuf Jamal Haddad', 'fail'],
    ['Maria Cristina Santos Reyes', 'Maria Santos Reyes', 'fail'],
    ['Abdul Rahman Siddiqui', 'Abdulrahman Siddiqui', 'pass'],
    ['Priya Nair Menon', 'PRIYA NAIR MENON', 'pass'],
    ['John Paul Dela Cruz', 'John Paul  Dela Cruz ', 'pass'],
  ];
  for (const v of nameVariants) {
    usedNames.add(normName(v[0]));
    usedNames.add(normName(v[1]));
  }
  usedNames.add(normName('Sanjay Kumar Pillai'));
  const N_HR = 180;
  const employees = [];
  let idNo = 101;
  for (let i = 0; i < N_HR; i++) {
    idNo += rng.chance(0.15) ? 2 : 1; // occasional gaps in the ID sequence
    const variant = i % 19 === 7 && nameVariants.length > employees.filter((e) => e.variant).length ? nameVariants[employees.filter((e) => e.variant).length] : null;
    const name = uniqName(variant ? variant[0] : null);
    const { iban } = newIban();
    const join = d(rng.int(2014, 2026), rng.int(1, 12), rng.int(1, 28));
    employees.push({
      id: pad(idNo, 5), num: idNo, name, dept: rng.pick(DEPARTMENTS),
      join: join > d(2026, 8, 31) ? d(2026, 3, 15) : join,
      basic: rng.int(50, 560) * 50, iban, status: 'Active', variant,
    });
  }
  if (employees.filter((e) => e.variant).length !== nameVariants.length) throw new Error('not all name variants placed');

  // HR-only employees (not on the September payroll)
  const pickFree = (from) => {
    for (;;) {
      const e = from[rng.int(0, from.length - 1)];
      if (!e.variant && !e.special) return e;
    }
  };
  const joiner = employees[employees.length - 1];
  joiner.join = d(2026, 9, 28);
  joiner.special = 'New joiner (after payroll cut-off)';
  const hrOnly = [];
  for (const st of ['Terminated', 'Terminated', 'Terminated', 'Unpaid Leave', 'Unpaid Leave', 'Unpaid Leave']) {
    const e = pickFree(employees);
    e.status = st;
    e.special = st;
    hrOnly.push(e);
  }
  hrOnly.push(joiner);
  const ibanChange = pickFree(employees);
  ibanChange.special = 'IBAN mismatch';
  const dupEmp = pickFree(employees);
  dupEmp.special = 'Duplicate in payroll';
  const noZeros = [];
  while (noZeros.length < 15) {
    const e = pickFree(employees);
    if (!noZeros.includes(e)) noZeros.push(e);
  }
  noZeros.forEach((e) => (e.noZeros = true));

  // Payroll register
  const payDate = d(2026, 9, 28);
  const payroll = [];
  for (const e of employees) {
    if (hrOnly.includes(e)) continue;
    const net = Math.round(e.basic * (1.45 + rng.float() * 0.35) * 100 - rng.int(0, 45000));
    let iban = e.iban;
    if (e === ibanChange) iban = newIban().iban;
    const row = { empNo: e.noZeros ? e.num : e.id, name: e.variant ? e.variant[1] : e.name, bank: bankOf(iban), iban, net, payDate, emp: e };
    payroll.push(row);
  }
  // Employee only in payroll (final settlement of an ex-employee not in the master)
  const ghostIban = newIban().iban;
  const ghost = { empNo: pad(idNo + 37, 5), name: uniqName('Sanjay Kumar Pillai'), bank: bankOf(ghostIban), iban: ghostIban, net: 1874530, payDate };
  payroll.push(ghost);
  payroll.sort((a, b) => Number(a.empNo) - Number(b.empNo));
  const dupRow = payroll.find((p) => p.emp === dupEmp);
  payroll.push({ ...dupRow }); // paid twice: second line at the end of the register (supplementary batch)

  // ---- Write HR master: title row 1, header row 2 ----
  {
    const wb = newWorkbook();
    const ws = wb.addWorksheet('Employees');
    ws.getCell('A1').value = `${OUR_COMPANY} - HR Employee Master (as at 30-Sep-2026)`;
    ws.getCell('A1').font = { bold: true, size: 13 };
    writeTable(ws, {
      headerRow: 2, autoFilter: true,
      columns: [
        { header: 'Emp ID', key: 'id', width: 10 },
        { header: 'Employee Name', key: 'name', width: 32 },
        { header: 'Department', key: 'dept', width: 18 },
        { header: 'Join Date', key: 'join', width: 13, type: 'date' },
        { header: 'Basic Salary', key: 'basic', width: 14, type: 'amount' },
        { header: 'IBAN', key: 'iban', width: 27 },
        { header: 'Status', key: 'status', width: 14 },
      ],
      rows: employees,
    });
    await saveWorkbook(wb, `${outDir}/general/HR_Employee_Master.xlsx`);
  }
  {
    const wb = newWorkbook();
    const ws = wb.addWorksheet('WPS Register');
    writeTable(ws, {
      headerRow: 1, autoFilter: true,
      columns: [
        { header: 'Employee No', key: 'empNo', width: 13 },
        { header: 'Name', key: 'name', width: 32 },
        { header: 'Bank', key: 'bank', width: 26 },
        { header: 'IBAN', key: 'iban', width: 27 },
        { header: 'Net Pay', key: 'netAed', width: 14, type: 'amount' },
        { header: 'Pay Date', key: 'payDate', width: 13, type: 'date' },
      ],
      rows: payroll.map((p) => ({ ...p, netAed: toAed(p.net) })),
    });
    await saveWorkbook(wb, `${outDir}/general/WPS_Payroll_Register_Sep2026.xlsx`);
  }

  const failVariants = employees.filter((e) => e.variant && e.variant[2] === 'fail');
  const passVariants = employees.filter((e) => e.variant && e.variant[2] === 'pass');
  const matched = employees.length - hrOnly.length - failVariants.length - 2; // minus IBAN mismatch and duplicate
  const tiers = { matched, doubtful: failVariants.length + 2, doubtfulB: failVariants.length + 3, likely: 0, unmatchedA: hrOnly.length, unmatchedB: 1 };
  const scenarios = [
    { s: 'Clean matches', d: `${matched} employees with the same ID, name and IBAN on both sides`, e: 'Matched' },
    { s: 'IDs with / without leading zeros', d: `${noZeros.length} payroll rows store Employee No as a plain number, e.g. HR "${noZeros[0].id}" vs payroll ${noZeros[0].num}: ${noZeros.map((e) => e.id).join(', ')}`, e: 'Matched with ID rule = Normalised (leading zeros ignored); Doubtful with Exact' },
    { s: 'Name variants that fail Normalised', d: failVariants.map((e) => `${e.id} "${e.variant[0]}" vs "${e.variant[1]}"`).join('; '), e: 'Doubtful - "Employee ID and IBAN agree; name differs" (Smart Recon AI would confirm Mohd = Mohammed etc.)' },
    { s: 'Name variants that pass Normalised', d: passVariants.map((e) => `${e.id} "${e.variant[0]}" vs "${e.variant[1]}"`).join('; '), e: 'Matched (case and spaces ignored)' },
    { s: 'Only in HR', d: hrOnly.map((e) => `${e.id} ${e.name} (${e.special})`).join('; '), e: 'Unmatched - HR employee master' },
    { s: 'Only in payroll', d: `${ghost.empNo} ${ghost.name} ${fmtAmt(ghost.net)} - not in the HR master`, e: 'Unmatched - WPS payroll register' },
    { s: 'Duplicated Employee ID (paid twice)', d: `${dupEmp.id} ${dupEmp.name} appears twice in the payroll register (Net Pay ${fmtAmt(dupRow.net)} each)`, e: 'Doubtful - "Multiple identical candidates" (1 HR line, 2 payroll lines)' },
    { s: 'IBAN mismatch', d: `${ibanChange.id} ${ibanChange.name}: HR ${ibanChange.iban} vs payroll ${payroll.find((p) => p.emp === ibanChange).iban}`, e: 'Doubtful - "Employee ID and name agree; IBAN differs"' },
  ];
  const countStatement = [
    ['Records in HR employee master', employees.length],
    ['  = Matched', tiers.matched],
    ['  + Doubtful / Likely pending', tiers.doubtful],
    ['  + Only in HR', tiers.unmatchedA],
    ['Records in WPS payroll register', payroll.length],
    ['  = Matched', tiers.matched],
    ['  + Doubtful / Likely pending', tiers.doubtfulB],
    ['  + Only in payroll', tiers.unmatchedB],
    ['Count difference (HR)', employees.length - tiers.matched - tiers.doubtful - tiers.unmatchedA],
    ['Count difference (payroll)', payroll.length - tiers.matched - tiers.doubtfulB - tiers.unmatchedB],
  ];
  return {
    key: 'hr',
    files: ['general/HR_Employee_Master.xlsx', 'general/WPS_Payroll_Register_Sep2026.xlsx'],
    rowsA: employees.length, rowsB: payroll.length, tiers, scenarios, countStatement,
    planted: { dupId: dupEmp.id, ibanId: ibanChange.id, ghostId: ghost.empNo, hrOnly: hrOnly.map((e) => e.id), noZeros: noZeros.map((e) => e.num), failVariants: failVariants.map((e) => e.id) },
  };
}

// ---------------------------------------------------------------- Intercompany
const IC_OPENING = 118423060; // 1,184,230.60 owed by Entity B to Entity A at 01-Aug-2026
const ENTITY_A = 'Desert Pearl Trading LLC (Dubai)';
const ENTITY_B = 'Desert Pearl Industries LLC (Abu Dhabi)';

export async function generateIntercompany(outDir) {
  const rng = new Rng(2026080505);
  const amts = new UniqueAmounts(rng);
  const mismatchA = amts.reserve(1530000);
  const mismatchB = amts.reserve(1500000);
  const days = [...businessDays(2026, 8), ...businessDays(2026, 9)].filter((x) => x <= d(2026, 9, 25));
  // Every amount is expressed as "+ = Entity B owes Entity A more" in BOTH files (same-sign convention).
  const kinds = [
    { n: 34, sign: 1, a: 'IC sale of goods to DPI Abu Dhabi', b: 'IC purchase of goods from DPT Dubai', min: 4000, max: 85000, docA: 'A-ICI', docB: 'B-PI' },
    { n: 10, sign: 1, a: 'Expenses paid on behalf of DPI (recharge)', b: 'Expenses paid by DPT on our behalf', min: 600, max: 9500, docA: 'A-JV', docB: 'B-JV' },
    { n: 21, sign: -1, a: 'Fund transfer received from DPI', b: 'Fund transfer to DPT Dubai', min: 15000, max: 85000, docA: 'A-BR', docB: 'B-BP' },
    { n: 26, sign: -1, a: 'IC purchase - fabricated goods from DPI', b: 'IC sale - fabricated goods to DPT', min: 3000, max: 60000, docA: 'A-PI', docB: 'B-ICI' },
    { n: 2, sign: -1, a: 'Warehouse rent recharge from DPI Mussafah', b: 'Warehouse rent recharged to DPT', min: 18000, max: 22000, docA: 'A-JV', docB: 'B-JV' },
    { n: 3, sign: 1, a: 'Shared staff cost recharge to DPI', b: 'Shared staff cost recharge from DPT', min: 22000, max: 41000, docA: 'A-JV', docB: 'B-JV' },
  ];
  const txns = [];
  for (const k of kinds) for (let i = 0; i < k.n; i++) txns.push({ k, date: rng.pick(days), amount: k.sign * amts.take(k.min, k.max) });
  // Management fee (August matched; September is the amount mismatch)
  txns.push({ k: { a: 'Management fee Aug 2026', b: 'Management fee Aug 2026 - DPT', docA: 'A-ICI', docB: 'B-PI' }, date: d(2026, 8, 31), amount: amts.take(15100, 15600) });
  txns.sort((x, y) => x.date - y.date || Math.abs(x.amount) - Math.abs(y.amount));
  let icSeq = { '08': 0, '09': 0 };
  const mm = (x) => pad(x.getUTCMonth() + 1, 2);
  const nextRef = (dt) => `IC-26${mm(dt)}-${pad(++icSeq[mm(dt)], 4)}`;
  const A = [], B = [];
  const docSeq = {};
  const doc = (prefix) => `${prefix}-${pad((docSeq[prefix] = (docSeq[prefix] ?? 0) + 1), 4)}`;
  for (const t of txns) {
    const ref = nextRef(t.date);
    const lag = rng.pick([0, 0, 0, 0, 1, 1, 2, 3]);
    const aFirst = t.amount > 0; // the entity that originates the entry books first
    let other = bizFwd(addDays(t.date, lag));
    if (dayDiff(t.date, other) > 3) other = t.date; // keep booking lags inside the +/-3 day tolerance
    const aDate = aFirst ? t.date : other;
    const bDate = aFirst ? other : t.date;
    A.push({ date: aDate, doc: doc(t.k.docA), ref, cp: 'DPI-AUH', desc: t.k.a, amount: t.amount, tag: 'matched' });
    B.push({ date: bDate, doc: doc(t.k.docB), ref, cp: 'DPT-DXB', desc: t.k.b, amount: t.amount, tag: 'matched' });
  }
  // Amount mismatch: September management fee
  const mmRef = nextRef(d(2026, 9, 30));
  A.push({ date: d(2026, 9, 30), doc: doc('A-ICI'), ref: mmRef, cp: 'DPI-AUH', desc: 'Management fee Sep 2026 (per revised agreement)', amount: mismatchA, tag: 'amount-mismatch' });
  B.push({ date: d(2026, 9, 30), doc: doc('B-PI'), ref: mmRef, cp: 'DPT-DXB', desc: 'Management fee Sep 2026 - DPT (budget rate)', amount: mismatchB, tag: 'amount-mismatch' });
  // Timing differences: A only (B books in October)
  const aOnly = [];
  for (const [day, desc] of [[28, 'IC sale of goods to DPI Abu Dhabi - shipped 28-Sep'], [29, 'IC sale of goods to DPI Abu Dhabi - shipped 29-Sep'], [30, 'Expenses paid on behalf of DPI (recharge) - Sep visas']]) {
    const r = { date: d(2026, 9, day), doc: doc(day === 30 ? 'A-JV' : 'A-ICI'), ref: nextRef(d(2026, 9, day)), cp: 'DPI-AUH', desc, amount: amts.take(3500, 42000), tag: 'timing-A-only' };
    A.push(r);
    aOnly.push(r);
  }
  // Timing differences: B only
  const bOnly = [];
  {
    const r1 = { date: d(2026, 9, 30), doc: doc('B-BP'), ref: nextRef(d(2026, 9, 30)), cp: 'DPT-DXB', desc: 'Fund transfer to DPT Dubai (value 01-Oct)', amount: -amts.take(60000, 95000), tag: 'timing-B-only' };
    const r2 = { date: d(2026, 9, 29), doc: doc('B-ICI'), ref: nextRef(d(2026, 9, 29)), cp: 'DPT-DXB', desc: 'IC sale - fabricated goods to DPT (delivered 29-Sep)', amount: -amts.take(8000, 20000), tag: 'timing-B-only' };
    B.push(r1, r2);
    bOnly.push(r1, r2);
  }
  A.sort((x, y) => x.date - y.date || x.ref.localeCompare(y.ref));
  B.sort((x, y) => x.date - y.date || x.ref.localeCompare(y.ref));
  let bal = IC_OPENING;
  for (const r of A) r.balance = bal += r.amount;
  const aClose = bal;
  bal = IC_OPENING;
  for (const r of B) r.balance = bal += r.amount;
  const bClose = bal;

  const cols = (refHeader) => [
    { header: 'Posting Date', key: 'date', width: 13, type: 'date' },
    { header: 'Document No', key: 'doc', width: 13 },
    { header: refHeader, key: 'ref', width: 15 },
    { header: 'Counterparty', key: 'cp', width: 13 },
    { header: 'Description', key: 'desc', width: 52 },
    { header: 'Amount (AED)', key: 'amt', width: 16, type: 'amount' },
    { header: 'Running Balance', key: 'bal', width: 17, type: 'amount' },
  ];
  const rowsOf = (arr, close) => [
    { date: d(2026, 8, 1), desc: 'Opening balance', bal: toAed(IC_OPENING), _style: 'balance' },
    ...arr.map((r) => ({ ...r, amt: toAed(r.amount), bal: toAed(r.balance) })),
    { date: d(2026, 9, 30), desc: 'Closing balance', bal: toAed(close), _style: 'balance' },
  ];
  await writeLedger(`${outDir}/general/Intercompany_EntityA_Dubai.xlsx`, {
    sheet: 'IC 1450 Due from DPI', columns: cols('IC Reference'), rows: rowsOf(A, aClose),
  });
  await writeLedger(`${outDir}/general/Intercompany_EntityB_AbuDhabi.xlsx`, {
    sheet: 'IC 2450 Due to DPT',
    titles: [ENTITY_B, 'Intercompany account 2450 - Due to Desert Pearl Trading LLC (Dubai) - group reporting pack', 'Sign convention: + = increases the amount we owe DPT Dubai (same sign as DPT\'s receivable)'],
    columns: cols('IC Ref'), rows: rowsOf(B, bClose),
  });

  const sumA = sum(aOnly, (r) => r.amount);
  const sumB = sum(bOnly, (r) => r.amount);
  const diff = mismatchA - mismatchB;
  const result = aClose - sumA + sumB - diff;
  const statement = [
    [`Balance per ${ENTITY_A} (A/c 1450 due from DPI)`, aClose],
    [`Less: items in A not in B (timing - booked by B in October): ${aOnly.map((r) => r.ref).join(', ')}`, -sumA],
    [`Add: items in B not in A (signed): ${bOnly.map((r) => r.ref).join(', ')}`, sumB],
    [`Less: amount difference on ${mmRef} (A ${fmtAmt(mismatchA)} vs B ${fmtAmt(mismatchB)})`, -diff],
    [`= Balance per ${ENTITY_B} (A/c 2450 due to DPT)`, result],
    ['Balance per Entity B file', bClose],
    ['Unexplained difference', bClose - result],
  ];
  if (bClose - result !== 0) throw new Error('IC statement does not tie');
  const lagged = A.filter((r) => r.tag === 'matched').filter((r) => {
    const b = B.find((x) => x.ref === r.ref);
    return b.date - r.date !== 0;
  }).length;
  const scenarios = [
    { s: 'Matched IC entries', d: `${txns.length} entries with the same IC reference and amount; ${lagged} of them booked 1-3 days apart by the two entities`, e: 'Matched (date +/-3 days)' },
    { s: 'Amount mismatch', d: `${mmRef} management fee Sep 2026: A ${fmtAmt(mismatchA)} vs B ${fmtAmt(mismatchB)}`, e: 'Doubtful - "Reference and date agree; amount differs by 300.00"' },
    { s: 'Timing differences - A only', d: aOnly.map((r) => `${r.ref} ${fmtDate(r.date)} ${fmtAmt(r.amount)}`).join('; '), e: 'Unmatched - Entity A' },
    { s: 'Timing differences - B only', d: bOnly.map((r) => `${r.ref} ${fmtDate(r.date)} ${fmtAmt(r.amount)}`).join('; '), e: 'Unmatched - Entity B' },
  ];
  return {
    key: 'ic',
    files: ['general/Intercompany_EntityA_Dubai.xlsx', 'general/Intercompany_EntityB_AbuDhabi.xlsx'],
    rowsA: A.length, rowsB: B.length, opening: IC_OPENING, closeA: aClose, closeB: bClose,
    tiers: { matched: txns.length, doubtful: 1, likely: 0, unmatchedA: aOnly.length, unmatchedB: bOnly.length },
    planted: { mmRef, aOnly: aOnly.map((r) => r.ref), bOnly: bOnly.map((r) => r.ref) },
    statement, scenarios,
  };
}
