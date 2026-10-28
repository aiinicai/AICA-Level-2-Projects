// Re-reads every generated sample file (xlsx via SheetJS, PDFs via pdf.js) and checks the key invariants.
// Prints a plain-English PASS/FAIL list. Run automatically at the end of index.mjs, or on its own:
//   node scripts/generate-samples/verify.mjs
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, resolve, join } from 'node:path';
import * as XLSX from 'xlsx';
import { reconcile } from './lib/engine.mjs';
import { ibanIsValid } from './lib/names.mjs';
import { fmtAmt } from './lib/util.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const serial = (y, m, d) => Date.UTC(y, m - 1, d) / 86400000 + 25569;
const c = (v) => (v == null || v === '' ? 0 : Math.round(Number(v) * 100));
const blank = (v) => v == null || String(v).trim() === '';

async function sheet(file, idx = 0) {
  const wb = XLSX.read(await readFile(file), { type: 'buffer' });
  const ws = wb.Sheets[wb.SheetNames[idx]];
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1, raw: true, defval: null, blankrows: true });
  return { ws, rows };
}
/** Rows below a 1-based header row as objects; fully blank rows dropped. */
async function table(file, headerRow) {
  const { ws, rows } = await sheet(file);
  const header = rows[headerRow - 1].map((h) => (h == null ? '' : String(h)));
  const data = rows
    .slice(headerRow)
    .filter((r) => r.some((v) => !blank(v)))
    .map((r) => Object.fromEntries(header.map((h, i) => [h, r[i]])));
  return { ws, rows, header, data };
}
const isBal = (r, key) => /opening balance|closing balance|brought forward/i.test(String(r[key] ?? ''));

export async function runVerify(OUT = resolve(HERE, '..', '..', 'sample-data')) {
  const results = [];
  const check = (section, name, ok, detail = '') => results.push({ section, name, ok: !!ok, detail });
  const exp = JSON.parse(await readFile(join(OUT, 'expected-results.json'), 'utf8'));
  const tierCheck = (section, got, want, keys) => {
    const diff = keys.filter((k) => got[k] !== want[k]);
    check(section, `Step 3 tier counts match README (${keys.map((k) => `${k} ${want[k]}`).join(', ')})`, diff.length === 0, diff.map((k) => `${k}: got ${got[k]}, expected ${want[k]}`).join('; '));
  };
  /** Sum of the README "Less/Add" lines must equal the engine's reconciling items, and the statement must tie to 0.00. */
  const statementCheck = (section, statement, engine, A, B, a, b) => {
    const items = statement.filter((l) => /^(Less|Add)/.test(l.line)).reduce((s, l) => s + Math.round(l.amount * 100), 0);
    let eng = 0;
    for (const i of engine.unmatchedA) eng -= a(A[i]);
    for (const j of engine.unmatchedB) eng += b(B[j]);
    for (const r of engine.results) if (r.tier !== 'M') eng += r.b.reduce((s, j) => s + b(B[j]), 0) - r.a.reduce((s, i) => s + a(A[i]), 0);
    check(section, 'Reconciling items in the README statement equal the items left by the reconciliation', items === eng, `README ${fmtAmt(items)} vs engine ${fmtAmt(eng)}`);
    const unexplained = statement.find((l) => /Unexplained/.test(l.line)).amount;
    check(section, 'Reconciliation statement ties: unexplained difference is 0.00', unexplained === 0, `unexplained ${unexplained}`);
  };
  const roundShare = (amounts) => amounts.filter((x) => x % 100 === 0).length / Math.max(1, amounts.length);

  // ================================================================== BANK
  {
    const S = 'bank';
    const bankF = join(OUT, 'bank/ENBD_Current_Statement_Sep2026.xlsx');
    const glF = join(OUT, 'bank/GL_101200_Cash_Sep2026.xlsx');
    const bk = await table(bankF, 7);
    const gl = await table(glF, 1);
    check(S, 'Bank statement has 6 junk rows above the header on row 7', bk.rows.slice(0, 5).every((r) => !blank(r[0])) && bk.rows[5].every(blank) && bk.header.join('|') === 'Txn Date|Value Date|Description|Reference No|Debit|Credit|Balance');
    check(S, 'GL header is on row 1 with the expected columns', gl.header.join('|') === 'Posting Date|Doc No|Voucher Type|Remarks|Party|Debit|Credit|Cheque No');
    const bOpen = bk.data[0], bClose = bk.data[bk.data.length - 1];
    check(S, 'Bank statement starts with "Opening balance" and ends with "Closing balance"', /^Opening balance$/i.test(bOpen.Description) && /^Closing balance$/i.test(bClose.Description));
    const bank = bk.data.slice(1, -1);
    let bal = c(bOpen.Balance), balOk = true;
    for (const r of bank) {
      bal += c(r.Credit) - c(r.Debit);
      if (bal !== c(r.Balance)) balOk = false;
    }
    check(S, 'Bank running balance = opening + credits - debits on every row', balOk && bal === c(bClose.Balance), `closing ${fmtAmt(c(bClose.Balance))}`);
    check(S, 'Bank rows are in date order and all dated Sep 2026', bank.every((r, i) => r['Txn Date'] >= serial(2026, 9, 1) && r['Txn Date'] <= serial(2026, 9, 30) && (i === 0 || r['Txn Date'] >= bank[i - 1]['Txn Date'])));
    const gOpen = gl.data[0], gClose = gl.data[gl.data.length - 1];
    check(S, 'GL has Opening Balance and Closing Balance rows; openings equal', isBal(gOpen, 'Remarks') && isBal(gClose, 'Remarks') && c(gOpen.Debit) === c(bOpen.Balance));
    const ledger = gl.data.slice(1, -1);
    const glClose = c(gOpen.Debit) + ledger.reduce((s, r) => s + c(r.Debit) - c(r.Credit), 0);
    check(S, 'GL closing balance = opening + debits - credits', glClose === c(gClose.Debit), `GL closing ${fmtAmt(glClose)}`);
    check(S, `Row counts in range (bank ${bank.length} ~300, GL ${ledger.length} ~290)`, bank.length >= 280 && bank.length <= 320 && ledger.length >= 270 && ledger.length <= 310 && ledger.length < bank.length);
    const a = (r) => c(r.Credit) - c(r.Debit);
    const b = (r) => c(r.Debit) - c(r.Credit);
    const eng = reconcile(bank, ledger, [
      { name: 'Reference', kind: 'ref', identifies: true, a: (r) => r['Reference No'], b: (r) => r['Cheque No'] },
      { name: 'Date', kind: 'date', tol: 3, a: (r) => r['Txn Date'], b: (r) => r['Posting Date'] },
      { name: 'Amount', kind: 'amount', identifies: true, tol: 0, a, b },
    ]);
    tierCheck(S, eng.counts, exp.bank.tiers, ['matched', 'doubtful', 'likely', 'unmatchedA', 'unmatchedB']);
    statementCheck(S, exp.bank.statement, eng, bank, ledger, a, b);
    // planted scenarios
    const dupB = bank.filter((r) => c(r.Debit) === 100000);
    const dupG = ledger.filter((r) => c(r.Credit) === 100000);
    const dupRes = eng.results.find((r) => r.dup && r.a.length === 3 && r.b.length === 3);
    check(S, 'Three identical 1,000.00 payments on the same day on both sides, flagged "Multiple identical candidates"', dupB.length === 3 && new Set(dupB.map((r) => r['Txn Date'])).size === 1 && dupG.length === 3 && !!dupRes);
    const ti = bank.findIndex((r) => r['Reference No'] === '004512' && exp.bank.planted.transChq === '004512');
    const tr = eng.usedA.get(ti);
    check(S, 'Transposition: CHQ 004512 bank 8,450.00 vs GL 8,540.00 is Doubtful (diff 90, divisible by 9)', ti >= 0 && c(bank[ti].Debit) === 845000 && tr?.tier === 'D' && tr.ad === 9000 && (tr.ad / 100) % 9 === 0);
    const split = bank.findIndex((r) => c(r.Credit) === exp.bank.planted.split);
    const parts = ledger.map((r, j) => [r, j]).filter(([r]) => c(r.Debit) === exp.bank.planted.splitPart);
    check(S, 'Split: one bank credit 36,750.00 = three GL receipts of 12,250.00 for the same party, all unmatched in Step 3', split >= 0 && parts.length === 3 && new Set(parts.map(([r]) => r.Party)).size === 1 && eng.unmatchedA.includes(split) && parts.every(([, j]) => eng.unmatchedB.includes(j)));
    const cA = bank.findIndex((r) => c(r.Credit) === exp.bank.planted.comboA), cB = bank.findIndex((r) => c(r.Credit) === exp.bank.planted.comboB);
    const cG = ledger.findIndex((r) => c(r.Debit) === exp.bank.planted.comboTotal);
    check(S, '2-bank-to-1-GL combination exists and sums exactly', cA >= 0 && cB >= 0 && cG >= 0 && exp.bank.planted.comboA + exp.bank.planted.comboB === exp.bank.planted.comboTotal && [cA, cB].every((i) => eng.unmatchedA.includes(i)) && eng.unmatchedB.includes(cG));
    const posOk = exp.bank.planted.posBatches.every((p) => p.parts.every((x) => bank.some((r) => c(r.Credit) === x)) && ledger.some((r) => c(r.Debit) === p.total) && p.parts.reduce((s, x) => s + x, 0) === p.total);
    check(S, 'Six 3-bank-to-1-GL card settlement batches exist and sum exactly', posOk);
    const ft = bank.find((r) => r['Reference No'] === 'FT2609ABC');
    const ftG = ledger.find((r) => String(r.Remarks).includes('Rcpt FT2609ABC'));
    check(S, 'Reference written differently: bank FT2609ABC vs GL remarks "Rcpt FT2609ABC" (Cheque No blank)', ft && ftG && blank(ftG['Cheque No']));
    check(S, 'Missing references: 4 bank rows without a reference are Doubtful', bank.filter((r, i) => blank(r['Reference No']) && eng.usedA.get(i)?.tier === 'D' && !eng.usedA.get(i).dup).length === 4);
    const shiftOk = eng.results.filter((r) => r.tier === 'M' && r.dd >= 1 && r.dd <= 3).length;
    const shiftBad = eng.results.filter((r) => r.tier === 'D' && !r.dup && r.dd >= 4 && r.dd <= 5).length;
    check(S, `Date shifts of 1-5 days present (${shiftOk} within tolerance, ${shiftBad} beyond)`, shiftOk >= 6 && shiftBad >= 2);
    const onlyBank = eng.unmatchedA.map((i) => bank[i].Description);
    check(S, 'Bank-only charges, VAT on charges and interest are unmatched', onlyBank.filter((d) => /^CHARGES/.test(d)).length >= 3 && onlyBank.some((d) => /^VAT/.test(d)) && onlyBank.some((d) => /^INTEREST/.test(d)));
    const unp = exp.bank.planted.unpresentedChqs.every((q) => { const j = ledger.findIndex((r) => r['Cheque No'] === q); return j >= 0 && eng.unmatchedB.includes(j) && c(ledger[j].Credit) > 0; });
    check(S, 'Unpresented cheques (GL only) are unmatched', unp);
    check(S, 'Uncredited deposits (GL only) are unmatched', eng.unmatchedB.filter((j) => /deposited|advised|CDM/i.test(ledger[j].Remarks) && c(ledger[j].Debit) > 0).length >= 3);
    const dB = bank.findIndex((r) => r['Reference No'] === 'TT26093077'), dG = ledger.findIndex((r) => r['Cheque No'] === 'CDM300926');
    check(S, 'Date-only coincidence (same date, different amount and ref) stays Unmatched', dB >= 0 && dG >= 0 && bank[dB]['Txn Date'] === ledger[dG]['Posting Date'] && eng.unmatchedA.includes(dB) && eng.unmatchedB.includes(dG));
    const narr = bank.map((r) => r.Description).join('\n');
    check(S, 'Narration patterns FT, TT, CHQ, POS, SALARY/WPS, CHARGES, INTEREST all present', ['FT', 'TT', 'CHQ', 'POS', 'SALARY', 'WPS', 'CHARGES', 'INTEREST'].every((p) => new RegExp(`\\b${p}\\b`).test(narr)));
    const amts = bank.map((r) => c(r.Debit) || c(r.Credit));
    check(S, `Amounts look real (only ${(roundShare(amts) * 100).toFixed(0)}% are whole dirhams) with 2-decimal values`, roundShare(amts) < 0.4 && amts.every((x) => Number.isInteger(x)));
  }

  // ================================================================== AR / AP (shared shape)
  const sub = async (S, fA, hA, fB, hB, refA, refB, a, b, ex, balA, balB) => {
    const A = await table(join(OUT, fA), hA);
    const B = await table(join(OUT, fB), hB);
    const descA = A.header.find((h) => /Narration|Particulars|Description/.test(h));
    const descB = B.header.find((h) => /Narration|Particulars|Description/.test(h));
    const ok = (t, desc, f) => {
      const open = t.data[0], close = t.data[t.data.length - 1];
      let bal = c(open.Balance ?? open['Balance (Cr)']);
      let good = isBal(open, desc) && isBal(close, desc);
      for (const r of t.data.slice(1, -1)) {
        bal += f(r);
        if (bal !== c(r.Balance ?? r['Balance (Cr)'])) good = false;
      }
      return good && bal === c(close.Balance ?? close['Balance (Cr)']) ? bal : null;
    };
    const closeA = ok(A, descA, a), closeB = ok(B, descB, b);
    check(S, 'Both files have opening/closing balance rows and consistent running balances', closeA !== null && closeB !== null, `ours ${fmtAmt(closeA ?? 0)}, theirs ${fmtAmt(closeB ?? 0)}`);
    check(S, 'Equal opening balances on both sides', c(A.data[0].Balance ?? A.data[0]['Balance (Cr)']) === c(B.data[0].Balance ?? B.data[0]['Balance (Cr)']));
    const rA = A.data.slice(1, -1), rB = B.data.slice(1, -1);
    check(S, `Row counts in range (ours ${rA.length}, theirs ${rB.length}, ~60 each)`, [rA.length, rB.length].every((n) => n >= 50 && n <= 70));
    const dateA = A.header[0], dateB = B.header[0];
    check(S, 'All dates fall in Aug-Sep 2026', [...rA.map((r) => r[dateA]), ...rB.map((r) => r[dateB])].every((s) => s >= serial(2026, 8, 1) && s <= serial(2026, 9, 30)));
    const eng = reconcile(rA, rB, [
      { name: 'Reference', kind: 'ref', identifies: true, a: (r) => r[refA], b: (r) => r[refB] },
      { name: 'Date', kind: 'date', tol: 7, a: (r) => r[dateA], b: (r) => r[dateB] },
      { name: 'Amount', kind: 'amount', identifies: true, a, b },
    ]);
    tierCheck(S, eng.counts, ex.tiers, ['matched', 'doubtful', ...(ex.tiers.doubtfulB != null ? ['doubtfulB'] : []), 'likely', 'unmatchedA', 'unmatchedB']);
    statementCheck(S, ex.statement, eng, rA, rB, a, b);
    return { rA, rB, eng };
  };
  {
    const S = 'ar';
    const a = (r) => c(r.Debit) - c(r.Credit);
    const b = (r) => c(r.Credit) - c(r.Debit);
    const { rA, rB, eng } = await sub(S, 'ar/Our_AR_Ledger_AlNoor_Trading.xlsx', 4, 'ar/AlNoor_Trading_SOA.xlsx', 7, 'Invoice / Ref No', 'Supplier Inv / Ref', a, b, exp.ar);
    const i123 = rA.findIndex((r) => r['Invoice / Ref No'] === 'INV-00123');
    check(S, 'Invoice number written differently: ours "INV-00123" vs theirs "123", Matched under Normalised', i123 >= 0 && rB.some((r) => String(r['Supplier Inv / Ref']) === '123') && eng.usedA.get(i123)?.tier === 'M');
    check(S, 'Credit note present on both sides and matched', rA.some((r, i) => r.Type === 'Credit Note' && eng.usedA.get(i)?.tier === 'M'));
    check(S, 'Payment on account present and matched', rA.some((r, i) => /on account/i.test(r.Narration) && eng.usedA.get(i)?.tier === 'M'));
    check(S, 'Payment in transit (ours only) is unmatched', eng.unmatchedA.some((i) => rA[i].Type === 'Receipt'));
    check(S, 'Invoice not booked by the customer is unmatched', eng.unmatchedA.some((i) => rA[i].Type === 'Sales Invoice'));
    check(S, 'Disputed invoice differs by exactly 90.00 and is Doubtful', eng.results.some((r) => r.tier === 'D' && r.ad === 9000));
  }
  {
    const S = 'ap';
    const a = (r) => c(r.Credit) - c(r.Debit);
    const b = (r) => c(r.Debit) - c(r.Credit);
    const { rA, rB, eng } = await sub(S, 'ap/Our_AP_Ledger_Gulf_Supplies.xlsx', 4, 'ap/Gulf_Supplies_SOA.xlsx', 6, 'Supplier Inv / Ref', 'Invoice / Doc No', a, b, exp.ap);
    const dupNo = exp.ap.planted.dupNo;
    check(S, `Duplicate invoice line in the SOA (${dupNo}) flagged "Multiple identical candidates"`, rB.filter((r) => r['Invoice / Doc No'] === dupNo).length === 2 && eng.results.some((r) => r.dup && r.b.length === 2));
    check(S, '0.50 rounding difference is Doubtful', eng.results.some((r) => r.tier === 'D' && r.ad === 50));
    check(S, `Supplier invoice missing from our books (${exp.ap.planted.missingNo}) is unmatched on their side`, eng.unmatchedB.some((j) => rB[j]['Invoice / Doc No'] === exp.ap.planted.missingNo));
    check(S, 'Debit note present and matched', rA.some((r, i) => r.Type === 'Debit Note' && eng.usedA.get(i)?.tier === 'M'));
    check(S, 'Payment in transit (ours only) is unmatched', eng.unmatchedA.some((i) => rA[i].Type === 'Payment'));
  }

  // ================================================================== GENERAL: HR vs WPS
  {
    const S = 'general/HR';
    const hr = await table(join(OUT, 'general/HR_Employee_Master.xlsx'), 2);
    const py = await table(join(OUT, 'general/WPS_Payroll_Register_Sep2026.xlsx'), 1);
    check(S, 'HR master has a title row and the header on row 2', !blank(hr.rows[0][0]) && hr.header.join('|') === 'Emp ID|Employee Name|Department|Join Date|Basic Salary|IBAN|Status');
    check(S, 'Payroll header is Employee No, Name, Bank, IBAN, Net Pay, Pay Date', py.header.join('|') === 'Employee No|Name|Bank|IBAN|Net Pay|Pay Date');
    check(S, `Row counts in range (HR ${hr.data.length} ~180, payroll ${py.data.length} ~175)`, hr.data.length >= 170 && hr.data.length <= 190 && py.data.length >= 165 && py.data.length <= 185);
    check(S, 'Every IBAN is a correctly shaped AE IBAN with valid check digits', [...hr.data, ...py.data].every((r) => ibanIsValid(r.IBAN)));
    const eng = reconcile(hr.data, py.data, [
      { name: 'Emp ID', kind: 'id', identifies: true, a: (r) => r['Emp ID'], b: (r) => r['Employee No'] },
      { name: 'IBAN', kind: 'id', identifies: true, a: (r) => r.IBAN, b: (r) => r.IBAN },
      { name: 'Name', kind: 'text', identifies: false, a: (r) => r['Employee Name'], b: (r) => r.Name },
    ]);
    tierCheck(S, eng.counts, exp.hr.tiers, ['matched', 'doubtful', 'doubtfulB', 'likely', 'unmatchedA', 'unmatchedB']);
    const k = eng.counts;
    check(S, 'Record-count statement: HR = matched + pending + only-in-HR, payroll = matched + pending + only-in-payroll (difference 0)', hr.data.length - k.matched - k.doubtful - k.likely - k.unmatchedA === 0 && py.data.length - k.matched - k.doubtfulB - k.likely - k.unmatchedB === 0);
    check(S, 'IDs with and without leading zeros (numeric Employee No cells present)', py.data.filter((r) => typeof r['Employee No'] === 'number').length >= 10 && hr.data.every((r) => /^0\d{4}$/.test(r['Emp ID'])));
    const ids = py.data.map((r) => String(Number(r['Employee No'])));
    check(S, 'A duplicated Employee ID exists in the payroll and is flagged "Multiple identical candidates"', ids.length - new Set(ids).size === 1 && eng.results.some((r) => r.dup && r.a.length === 1 && r.b.length === 2));
    check(S, 'Employees only in HR include Terminated and Unpaid Leave staff', eng.unmatchedA.some((i) => hr.data[i].Status === 'Terminated') && eng.unmatchedA.some((i) => hr.data[i].Status === 'Unpaid Leave'));
    check(S, 'One employee only in payroll', eng.unmatchedB.length === 1);
    const idbanD = eng.results.filter((r) => r.tier === 'D' && !r.dup);
    check(S, 'Name variants (ID + IBAN agree, name differs) and an IBAN mismatch are Doubtful', idbanD.filter((r) => r.pass[0] && r.pass[1] && !r.pass[2]).length >= 5 && idbanD.filter((r) => r.pass[0] && !r.pass[1] && r.pass[2]).length === 1);
    check(S, 'Mohd vs Mohammed variant present', py.data.some((r) => /^Mohd /.test(r.Name)) && hr.data.some((r) => r['Employee Name'] === 'Mohammed Rafi Abdul Kareem'));
  }

  // ================================================================== GENERAL: Intercompany
  {
    const S = 'general/IC';
    const A = await table(join(OUT, 'general/Intercompany_EntityA_Dubai.xlsx'), 1);
    const B = await table(join(OUT, 'general/Intercompany_EntityB_AbuDhabi.xlsx'), 4);
    const run = (t) => {
      let bal = c(t.data[0]['Running Balance']), ok = isBal(t.data[0], 'Description') && isBal(t.data[t.data.length - 1], 'Description');
      for (const r of t.data.slice(1, -1)) { bal += c(r['Amount (AED)']); if (bal !== c(r['Running Balance'])) ok = false; }
      return ok && bal === c(t.data[t.data.length - 1]['Running Balance']);
    };
    check(S, 'Both entities have opening/closing rows and consistent running balances', run(A) && run(B));
    const rA = A.data.slice(1, -1), rB = B.data.slice(1, -1);
    check(S, `Row counts in range (A ${rA.length}, B ${rB.length}, ~100 each)`, [rA.length, rB.length].every((n) => n >= 90 && n <= 110));
    const amt = (r) => c(r['Amount (AED)']);
    const eng = reconcile(rA, rB, [
      { name: 'IC Ref', kind: 'id', identifies: true, a: (r) => r['IC Reference'], b: (r) => r['IC Ref'] },
      { name: 'Date', kind: 'date', tol: 3, a: (r) => r['Posting Date'], b: (r) => r['Posting Date'] },
      { name: 'Amount', kind: 'amount', identifies: true, a: amt, b: amt },
    ]);
    tierCheck(S, eng.counts, exp.intercompany.tiers, ['matched', 'doubtful', 'likely', 'unmatchedA', 'unmatchedB']);
    const opp = eng.results.filter((r) => r.tier === 'M' && amt(rA[r.a[0]]) === -amt(rB[r.b[0]])).length;
    check(S, 'Same-sign convention: matched pairs carry the same sign in both files (none opposite)', opp === 0 && eng.counts.matched > 80);
    statementCheck(S, exp.intercompany.statement, eng, rA, rB, amt, amt);
    check(S, 'One amount mismatch (Doubtful) and timing differences on both sides', eng.counts.doubtful === 1 && eng.counts.unmatchedA >= 2 && eng.counts.unmatchedB >= 1);
  }

  // ================================================================== TOOLS
  {
    const S = 'tools';
    const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs');
    const open = async (f, password) => pdfjs.getDocument({ data: new Uint8Array(await readFile(join(OUT, 'tools', f))), password, disableFontFace: true, isEvalSupported: false, verbosity: 0 }).promise;
    const pageText = async (doc, n) => (await (await doc.getPage(n)).getTextContent()).items.map((i) => i.str).join(' ');
    {
      const doc = await open('Bank_Statement_6_pages_digital.pdf');
      let ok = doc.numPages === 6;
      for (let p = 1; p <= doc.numPages; p++) {
        const t = await pageText(doc, p);
        if (!t.includes(`Page ${p} of 6`) || !t.includes('Emirates NBD Bank PJSC') || !t.includes('Withdrawals')) ok = false;
      }
      const all = (await pageText(doc, 1)) + (await pageText(doc, 6));
      check(S, '6-page statement PDF: 6 pages, bank header + column header + "Page x of 6" on every page, opening/closing rows', ok && all.includes('OPENING BALANCE') && all.includes('CLOSING BALANCE'));
    }
    {
      const doc = await open('Price_List_digital.pdf');
      check(S, 'Price list PDF has 2 pages with Item Code / Unit Price AED / VAT % columns', doc.numPages === 2 && /Unit Price AED/.test(await pageText(doc, 2)));
    }
    {
      const doc = await open('Statement_with_scanned_page.pdf');
      const t1 = (await (await doc.getPage(1)).getTextContent()).items.length;
      const t3 = (await (await doc.getPage(3)).getTextContent()).items.length;
      const ops = await (await doc.getPage(3)).getOperatorList();
      const hasImg = ops.fnArray.includes(pdfjs.OPS.paintImageXObject);
      check(S, 'Scanned-page PDF: 3 pages, pages 1-2 have text, page 3 is image-only (no text layer)', doc.numPages === 3 && t1 > 50 && t3 === 0 && hasImg);
    }
    {
      let refused = false;
      try { await open('Password_protected.pdf'); } catch (e) { refused = /password/i.test(e.name + e.message); }
      let opens = false;
      try { opens = (await open('Password_protected.pdf', 'reco123')).numPages === 1; } catch { opens = false; }
      check(S, 'Password_protected.pdf refuses to open without a password and opens with "reco123"', refused && opens);
    }
    {
      const p1 = await open('Merge_Part1.pdf'), p2 = await open('Merge_Part2.pdf'), sp = await open('Split_Me_12_pages.pdf');
      let splitOk = sp.numPages === 12;
      for (let p = 1; p <= 12; p++) if (!(await pageText(sp, p)).includes(`Page ${p} of 12`)) splitOk = false;
      check(S, 'Merge parts have 3 and 2 labelled pages', p1.numPages === 3 && p2.numPages === 2 && (await pageText(p1, 3)).includes('Merge Part 1') && (await pageText(p2, 2)).includes('Merge Part 2'));
      check(S, 'Split_Me_12_pages.pdf has 12 pages each saying "Page N of 12"', splitOk);
    }
    {
      const jul = await table(join(OUT, 'tools/Statement_Jul2026.xlsx'), 5);
      const aug = await table(join(OUT, 'tools/Statement_Aug2026.xlsx'), 1);
      const sep = await table(join(OUT, 'tools/Statement_Sep2026.xlsx'), 3);
      check(S, 'Monthly statements have different headers (Txn Date / Transaction Date / Date; Narration / Description / Details)', jul.header[0] === 'Txn Date' && aug.header[0] === 'Transaction Date' && sep.header[0] === 'Date' && jul.header[1] === 'Narration' && aug.header[1] === 'Description');
      const last = (t) => c(t.data[t.data.length - 1][t.header[5]]);
      check(S, 'Monthly balances chain: Jul closing = Aug opening, Aug closing = Sep opening', last(jul) === c(aug.data[0].Balance) && last(aug) === c(sep.data[0]['Running Balance']));
      check(S, 'Aug has a repeated header row and Sep has a Total row (to be excluded)', aug.data.some((r) => r.Description === 'Description') && sep.data.some((r) => r.Details === 'Total'));
    }
    {
      const tb = await table(join(OUT, 'tools/Sheet_to_print.xlsx'), 3);
      const body = tb.data.filter((r) => r['Account Name'] !== 'Total');
      const tot = tb.data.find((r) => r['Account Name'] === 'Total');
      const dr = body.reduce((s, r) => s + c(r['Debit (AED)']), 0), cr = body.reduce((s, r) => s + c(r['Credit (AED)']), 0);
      check(S, `Trial balance has ~120 rows (${body.length}) and debits = credits = Total row`, body.length >= 110 && body.length <= 130 && dr === cr && dr === c(tot['Debit (AED)']));
    }
    {
      const { ws, rows } = await sheet(join(OUT, 'tools/Messy_Data_for_Cleaner.xlsx'));
      const merges = (ws['!merges'] ?? []).filter((m) => m.s.c === 0 && m.e.r > m.s.r);
      const amounts = rows.slice(4).map((r) => r[4]).filter((v) => v != null);
      const s = amounts.filter((v) => typeof v === 'string');
      const dates = rows.slice(4).map((r) => r[1]).filter((v) => typeof v === 'string');
      const ambiguous = dates.filter((x) => { const [dd, mm] = x.split('/').map(Number); return dd <= 12 && mm <= 12 && dd !== mm; });
      const dataRows = rows.slice(4).filter((r) => !blank(r[3]));
      const keys = dataRows.map((r) => JSON.stringify(r.slice(1)));
      check(S, 'Messy file: text numbers, CR/DR, bracket negatives, trailing minus', s.some((v) => /^\d{1,3}(,\d{3})*\.\d{2}$/.test(v)) && s.some((v) => / CR$/.test(v)) && s.some((v) => / DR$/.test(v)) && s.some((v) => /^\(.*\)$/.test(v)) && s.some((v) => /\d-$/.test(v)));
      check(S, `Messy file: DD/MM/YYYY text dates incl. ambiguous ones (${ambiguous.length})`, dates.every((x) => /^\d{2}\/\d{2}\/2026$/.test(x)) && ambiguous.length >= 3);
      check(S, `Messy file: merged Category cells (${merges.length}), blank rows, subtotal and TOTAL rows`, merges.length >= 3 && rows.slice(4).some((r) => r.every(blank)) && rows.some((r) => /^Subtotal/.test(r[2] ?? '')) && rows.some((r) => r[2] === 'TOTAL'));
      check(S, 'Messy file: exact duplicate rows and extra spaces', keys.length - new Set(keys).size >= 2 && rows.some((r) => typeof r[2] === 'string' && /^\s|\s$|\s{2,}| /.test(r[2])));
    }
  }

  // ------------------------------------------------------------------ report
  let pass = 0;
  let section = '';
  console.log('Verification');
  for (const r of results) {
    if (r.section !== section) {
      section = r.section;
      console.log(`\n  [${section}]`);
    }
    console.log(`  ${r.ok ? 'PASS' : 'FAIL'}  ${r.name}${!r.ok && r.detail ? `  -> ${r.detail}` : ''}`);
    if (r.ok) pass++;
  }
  const all = pass === results.length;
  console.log(`\n${all ? 'ALL CHECKS PASSED' : 'SOME CHECKS FAILED'}: ${pass}/${results.length}`);
  return all;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  runVerify().then((ok) => {
    if (!ok) process.exitCode = 1;
  });
}
