const BCG = require('/home/claude/test/core.js');
const fs = require('fs'), path = require('path');
let pass = 0, fail = 0;
const ok = (n, c, x) => { if (c) { pass++; console.log('  PASS  ' + n); } else { fail++; console.log('  FAIL  ' + n + (x ? ' -> ' + x : '')); } };
const eq = (n, a, b) => ok(n, a === b, JSON.stringify(a) + ' !== ' + JSON.stringify(b));

const base = {
  clientName: 'Example Manufacturing Private Limited',
  firmName: 'Ankit Soni and Associates', firmDesignation: 'Statutory Auditor',
  currency: 'INR', amount: 125000, category: 'Trade Receivable',
  partyName: 'ABC Ltd', addressLines: ['Mumbai'],
  auditors: [{ name: 'M. A', email: 'a@gmail.com' }, { name: 'B', email: 'b@gmail.com' }]
};
const withSpan = (o) => Object.assign({}, base, o, {
  yearEndLabel: BCG.fmtDateLong(o.asAt), yearEnd: o.asAt
});

console.log('\n== 1. Audit-type phrases ==');
eq('statutory', BCG.auditPhrase('Statutory Audit'), 'statutory audit');
eq('interim', BCG.auditPhrase('Interim Audit'), 'interim audit');
eq('special purpose', BCG.auditPhrase('Special Purpose Audit'), 'special purpose audit');
eq('limited review', BCG.auditPhrase('Limited Review'), 'limited review');
eq('tax audit', BCG.auditPhrase('Tax Audit'), 'tax audit');
eq('other free text', BCG.auditPhrase('Other', 'Agreed-upon procedures engagement'), 'agreed-upon procedures engagement');
eq('other strips leading "the"', BCG.auditPhrase('Other', 'the quarterly review'), 'quarterly review');
eq('other blank falls back', BCG.auditPhrase('Other', '   '), 'audit');
eq('unknown falls back', BCG.auditPhrase('Nonsense'), 'statutory audit');
eq('designation statutory', BCG.auditDesignation('Statutory Audit'), 'Statutory Auditor');
eq('designation special', BCG.auditDesignation('Special Purpose Audit'), 'Auditor');
eq('designation tax', BCG.auditDesignation('Tax Audit'), 'Tax Auditor');

console.log('\n== 2. Period phrases ==');
eq('year basis', BCG.periodPhrase('year', '2026-03-31'), 'for the year ended 31 March 2026');
eq('period, no start', BCG.periodPhrase('period', '2026-09-30'), 'for the period ended 30 September 2026');
eq('period with start', BCG.periodPhrase('period', '2026-09-30', '2026-04-01'), 'for the period from 1 April 2026 to 30 September 2026');
eq('no date', BCG.periodPhrase('year', ''), '');
eq('label year', BCG.periodLabel('year', '2026-03-31'), 'Year ended 31 March 2026');
eq('label period', BCG.periodLabel('period', '2026-09-30', '2026-04-01'), 'Period from 1 April 2026 to 30 September 2026');

console.log('\n== 3. Opening sentence across combinations ==');
const combos = [
  ['Statutory Audit', '', 'year', '2026-03-31', '', 'As part of the statutory audit of Example Manufacturing Private Limited for the year ended 31 March 2026,'],
  ['Interim Audit', '', 'period', '2026-09-30', '2026-04-01', 'As part of the interim audit of Example Manufacturing Private Limited for the period from 1 April 2026 to 30 September 2026,'],
  ['Special Purpose Audit', '', 'period', '2026-06-30', '', 'As part of the special purpose audit of Example Manufacturing Private Limited for the period ended 30 June 2026,'],
  ['Other', 'agreed-upon procedures engagement', 'year', '2026-03-31', '', 'As part of the agreed-upon procedures engagement of Example Manufacturing Private Limited for the year ended 31 March 2026,']
];
combos.forEach(([t, o, b, at, st, expect]) => {
  const m = BCG.buildLetterModel(withSpan({ auditType: t, auditTypeOther: o, basis: b, asAt: at, periodStart: st }));
  ok(t + ' / ' + b + ' opening', m.paras[1].startsWith(expect), m.paras[1].slice(0, 130));
  ok(t + ' / ' + b + ' as-on date', m.paras[1].includes('as on ' + BCG.fmtDateLong(at) + '.'));
  ok(t + ' / ' + b + ' subject', m.subject === 'Subject: Confirmation of balance as at ' + BCG.fmtDateLong(at) + ' — Trade Receivable', m.subject);
});

console.log('\n== 4. Category wording unchanged by audit type ==');
['Trade Receivable', 'Trade Payable', 'Advance from Customers', 'Advance to Vendors'].forEach(cat => {
  const a = BCG.buildLetterModel(withSpan({ category: cat, auditType: 'Statutory Audit', basis: 'year', asAt: '2026-03-31' }));
  const b = BCG.buildLetterModel(withSpan({ category: cat, auditType: 'Interim Audit', basis: 'period', asAt: '2026-09-30', periodStart: '2026-04-01' }));
  const subA = a.rows.filter(r => r.sub).map(r => r.sub).join('|');
  const subB = b.rows.filter(r => r.sub).map(r => r.sub).join('|');
  ok(cat + ' table wording identical across audit types', subA === subB, subA + ' vs ' + subB);
  ok(cat + ' responding date blank', a.rows.find(r => r.label === 'Date').value === '');
});
const direction = ['Trade Receivable', 'Trade Payable', 'Advance from Customers', 'Advance to Vendors']
  .map(c => BCG.buildLetterModel(withSpan({ category: c, auditType: 'Interim Audit', basis: 'period', asAt: '2026-09-30' })).paras[1]);
ok('TR still receivable from you', direction[0].includes('balance outstanding receivable from you'));
ok('TP still payable to you', direction[1].includes('balance outstanding payable to you'));
ok('AFC still advance received from you', direction[2].includes('advance received from you'));
ok('ATV still advance paid to you', direction[3].includes('advance paid to you'));

console.log('\n== 5. Backwards compatibility (old confirmation shape) ==');
const legacy = Object.assign({}, base, { yearEnd: '2026-03-31', yearEndLabel: '31 March 2026' });
const lm = BCG.buildLetterModel(legacy);
ok('defaults to statutory audit', lm.paras[1].startsWith('As part of the statutory audit of'));
ok('defaults to year ended', lm.paras[1].includes('for the year ended 31 March 2026'));

console.log('\n== 6. Email template ==');
ok('default body uses placeholders', BCG.DEFAULT_BODY.includes('{audittype}') && BCG.DEFAULT_BODY.includes('{period}'));
const d1 = BCG.buildEmailDraft(withSpan({ auditType: 'Interim Audit', basis: 'period', asAt: '2026-09-30', periodStart: '2026-04-01', partyEmail: 'ap@abc.example' }), {});
ok('interim in body', d1.body.includes('We are conducting the interim audit of Example Manufacturing Private Limited for the period from 1 April 2026 to 30 September 2026.'), d1.body.split('\n')[2]);
ok('no unresolved placeholders', !/\{[a-z]+\}/.test(d1.body) && !/\{[a-z]+\}/.test(d1.subject));
const d2 = BCG.buildEmailDraft(withSpan({ auditType: 'Special Purpose Audit', basis: 'period', asAt: '2026-06-30', partyEmail: 'x@y.example' }), {});
ok('special purpose in body', d2.body.includes('the special purpose audit of'));
ok('period ended form', d2.body.includes('for the period ended 30 June 2026'));

console.log('\n== 7. DOCX parts build and stay well formed ==');
const outDir = '/home/claude/test/out';
fs.rmSync(outDir, { recursive: true, force: true });
const cases = [
  ['Statutory year end', { auditType: 'Statutory Audit', basis: 'year', asAt: '2026-03-31', category: 'Trade Receivable', partyName: 'ABC Ltd' }],
  ['Interim period', { auditType: 'Interim Audit', basis: 'period', asAt: '2026-09-30', periodStart: '2026-04-01', category: 'Trade Payable', partyName: 'XYZ Suppliers', amount: 80000 }],
  ['Special purpose', { auditType: 'Special Purpose Audit', basis: 'period', asAt: '2026-06-30', category: 'Advance from Customers', partyName: 'Customer P Ltd', amount: 50000 }]
];
cases.forEach(([name, o]) => {
  const conf = withSpan(o);
  const parts = BCG.docxParts(BCG.buildLetterModel(conf), conf, '2026-11-03T00:00:00Z');
  const dir = path.join(outDir, name.replace(/\s/g, '_'));
  Object.keys(parts).forEach(p => {
    const full = path.join(dir, p);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, parts[p], 'utf8');
  });
  ok(name + ' core.xml carries the engagement', parts['docProps/core.xml'].includes(o.auditType));
  ok(name + ' document.xml non-trivial', parts['word/document.xml'].length > 3000);
});

console.log('\n---------------------------------------');
console.log('PASSED ' + pass + '   FAILED ' + fail);
process.exit(fail ? 1 : 0);
