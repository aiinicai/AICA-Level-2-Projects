const BCG = require('/home/claude/test/core.js');
const fs = require('fs'), path = require('path');
let pass = 0, fail = 0;
const ok = (n, c, x) => { if (c) { pass++; console.log('  PASS  ' + n); }
  else { fail++; console.log('  FAIL  ' + n + (x ? '  ->  ' + String(x).slice(0, 220) : '')); } };

const base = {
  clientName: 'Example Manufacturing Private Limited',
  firmName: 'Ankit Soni and Associates',
  partnerName: 'CA Ankit Soni',
  firmDesignation: 'Statutory Auditor',
  signatoryName: 'Mr. R. Mehta', signatoryDesignation: 'Director / CFO',
  letterheadNote: true,
  letterDate: '2026-11-05', letterDateLabel: '5 November 2026',
  auditType: 'Statutory Audit', auditTypeOther: '',
  basis: 'year', asAt: '2026-03-31', yearEnd: '2026-03-31',
  yearEndLabel: '31 March 2026', currency: 'INR',
  auditors: [{ name: 'M. A', email: 'a@gmail.com' }, { name: 'B', email: 'b@gmail.com' }]
};
const make = (o) => Object.assign({}, base, o);

const cases = {
  'Trade Receivable': make({ partyName: 'ABC Ltd', addressLines: ['12 MG Road', 'Mumbai 400001'],
                             amount: 125000, category: 'Trade Receivable' }),
  'Trade Payable': make({ partyName: 'XYZ Suppliers', addressLines: ['Plot 9', 'Delhi 110001'],
                          amount: 80000, category: 'Trade Payable' }),
  'Advance from Customers': make({ partyName: 'Customer P Ltd', addressLines: ['Pune'],
                                   amount: 50000, category: 'Advance from Customers' }),
  'Advance to Vendors': make({ partyName: 'Vendor Q Ltd', addressLines: ['Chennai'],
                               amount: 30000, category: 'Advance to Vendors' })
};
const models = {};
Object.keys(cases).forEach(k => { models[k] = BCG.buildLetterModel(cases[k]); });

console.log('\n== 1. Titles match the attached formats ==');
ok('debtor title', models['Trade Receivable'].title === 'ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION', models['Trade Receivable'].title);
ok('creditor title', models['Trade Payable'].title === 'ACCOUNTS PAYABLE/CREDITOR CONFIRMATION', models['Trade Payable'].title);
ok('advance from customer title', models['Advance from Customers'].title === 'ADVANCE FROM CUSTOMER');
ok('advance to vendor title', models['Advance to Vendors'].title === 'ADVANCE PAID TO VENDOR');

console.log('\n== 2. Letterhead note, date and party block ==');
ok('letterhead note', models['Trade Receivable'].letterheadNote === '(on the letter head of the Company)');
ok('note omitted when switched off',
   BCG.buildLetterModel(make({ partyName: 'A', addressLines: [], amount: 1, category: 'Trade Payable', letterheadNote: false })).letterheadNote === '');
ok('date line', models['Trade Receivable'].dateLine === 'Date: 5 November 2026', models['Trade Receivable'].dateLine);
ok('party name first', models['Trade Receivable'].partyBlock[0].text === undefined || models['Trade Receivable'].partyBlock[0].t === 'ABC Ltd');
ok('address lines follow', models['Trade Receivable'].partyBlock.map(l => l.t).join('|') === 'ABC Ltd|12 MG Road|Mumbai 400001');
ok('salutation', models['Trade Receivable'].salutation === 'Dear Sir,');

console.log('\n== 3. Opening paragraph, per the attached wording ==');
const p0 = k => models[k].paras[0];
ok('debtor request clause',
   p0('Trade Receivable') === 'Our statutory auditors, Ankit Soni and Associates, are engaged in an audit of our financial statements. In connection therewith, they desire that you confirm directly to them the amount payable by you to us as at 31 March 2026 and a statement of our account in your books as at that date.',
   p0('Trade Receivable'));
ok('creditor request clause',
   p0('Trade Payable').includes('they desire that you furnish directly to them the amount of our liability to you (if any) as at 31 March 2026 and a statement of our account as at that date.'),
   p0('Trade Payable'));
ok('advance from customers request clause',
   p0('Advance from Customers').includes('the amount of advance received from you (if any) as at 31 March 2026'),
   p0('Advance from Customers'));
ok('advance to vendors request clause',
   p0('Advance to Vendors').includes('the amount of advance paid to you (if any) as at 31 March 2026'),
   p0('Advance to Vendors'));

console.log('\n== 4. "According to our records" line, with amount in words ==');
const p1 = k => models[k].paras[1];
ok('debtor amount line',
   p1('Trade Receivable') === 'According to our records, the amount due from you as at 31 March 2026 is INR 1,25,000.00 (In Words: Rupees One Lakh Twenty Five Thousand only)',
   p1('Trade Receivable'));
ok('creditor amount line',
   p1('Trade Payable') === 'According to our records, the amount due to you as at 31 March 2026 is INR 80,000.00 (In Words: Rupees Eighty Thousand only)',
   p1('Trade Payable'));
ok('afc amount line',
   p1('Advance from Customers').startsWith('According to our records, the advance amount received from you as at 31 March 2026 is INR 50,000.00'),
   p1('Advance from Customers'));
ok('atv amount line',
   p1('Advance to Vendors').startsWith('According to our records, the advance amount paid to you as at 31 March 2026 is INR 30,000.00'),
   p1('Advance to Vendors'));

console.log('\n== 5. Auditor block ==');
const ab = models['Trade Receivable'].auditorBlock.map(l => l.t);
ok('partner first', ab[0] === 'CA Ankit Soni', ab);
ok('firm with chartered accountants', ab[1] === 'Ankit Soni and Associates (Chartered Accountants)', ab);
ok('email id line', ab[2] === 'Email ID: a@gmail.com; b@gmail.com', ab);
ok('instruction paragraph',
   models['Trade Receivable'].paras[2] === 'After signing your reply, please e-mail this letter directly to our auditors at the following e-mail address:');
const noPartner = BCG.buildLetterModel(make({ partyName: 'A', addressLines: [], amount: 1,
  category: 'Trade Payable', partnerName: '' }));
ok('partner line omitted when blank', noPartner.auditorBlock.length === 2, noPartner.auditorBlock.map(l => l.t));

console.log('\n== 6. Difference clause and the debtor-only payment clause ==');
ok('debtor difference clause wording',
   models['Trade Receivable'].closingParas[0].includes('please notify our auditors directly, with a copy to us, of the amount shown'),
   models['Trade Receivable'].closingParas[0]);
ok('other categories use the shorter clause',
   models['Trade Payable'].closingParas[0].includes('please notify our auditors directly, with a copy to us, of the amount shown'),
   models['Trade Payable'].closingParas[0]);
ok('debtor carries the no-payment clause',
   models['Trade Receivable'].closingParas.some(t => t.startsWith('This letter is not a request for payment')));
['Trade Payable', 'Advance from Customers', 'Advance to Vendors'].forEach(k =>
  ok(k + ' has no payment clause', !models[k].closingParas.some(t => t.includes('not a request for payment'))));
Object.keys(models).forEach(k =>
  ok(k + ' thanks paragraph last', models[k].closingParas[models[k].closingParas.length - 1] ===
     'We thank you in advance for your co-operation in complying with this request and apologise for any inconvenience caused.'));

console.log('\n== 7. Signature is the company, not the audit firm ==');
const sig = models['Trade Receivable'].signature.map(l => l.t);
ok('yours faithfully', sig[0] === 'Yours faithfully');
ok('company name', sig[1] === 'Example Manufacturing Private Limited', sig);
ok('company name not bold, as in the attached formats', models['Trade Receivable'].signature[1].b === false);
ok('officer name', sig[2] === 'Mr. R. Mehta', sig);
ok('officer designation', sig[3] === 'Director / CFO', sig);
ok('audit firm does not sign', !sig.some(t => t.indexOf('Ankit Soni') === 0 || t === 'For Ankit Soni and Associates'), sig);

console.log('\n== 8. Confirmation slip ==');
const slip = k => models[k].slip;
ok('debtor slip', slip('Trade Receivable').sentence ===
   'We hereby confirm that the amount payable by us to Example Manufacturing Private Limited as on 31 March 2026 is INR ______________',
   slip('Trade Receivable').sentence);
ok('creditor slip', slip('Trade Payable').sentence.startsWith('We hereby confirm that the amount receivable by us from Example Manufacturing Private Limited'),
   slip('Trade Payable').sentence);
ok('afc slip', slip('Advance from Customers').sentence.startsWith('We hereby confirm that the advance amount paid by us to'),
   slip('Advance from Customers').sentence);
ok('atv slip', slip('Advance to Vendors').sentence.startsWith('We hereby confirm that the advance amount received by us from'),
   slip('Advance to Vendors').sentence);
ok('slip rows', JSON.stringify(slip('Trade Receivable').rows) ===
   JSON.stringify(['Name and Title', 'Company / Firm', 'Signature', 'Date']));

console.log('\n== 9. Audit type drives the auditors phrase ==');
const t = (type, other) => BCG.buildLetterModel(make({ partyName: 'A', addressLines: [], amount: 1,
  category: 'Trade Payable', auditType: type, auditTypeOther: other || '' })).paras[0];
ok('statutory', t('Statutory Audit').startsWith('Our statutory auditors, Ankit Soni and Associates, are engaged in an audit of our financial statements.'), t('Statutory Audit'));
ok('interim', t('Interim Audit').startsWith('Our auditors, Ankit Soni and Associates, are engaged in an interim audit of our financial statements.'), t('Interim Audit'));
ok('special purpose', t('Special Purpose Audit').includes('are engaged in a special purpose audit of our financial statements.'), t('Special Purpose Audit'));
ok('limited review', t('Limited Review').includes('are engaged in a limited review of our financial statements.'), t('Limited Review'));
ok('tax audit', t('Tax Audit').startsWith('Our tax auditors,') && t('Tax Audit').includes('a tax audit'), t('Tax Audit'));
ok('other free text', t('Other', 'Agreed-upon procedures engagement').includes('are engaged in an agreed-upon procedures engagement of our financial statements.'), t('Other', 'Agreed-upon procedures engagement'));

console.log('\n== 10. Period basis still drives the date ==');
const per = BCG.buildLetterModel(make({ partyName: 'A', addressLines: [], amount: 1000,
  category: 'Trade Receivable', basis: 'period', asAt: '2026-09-30',
  periodStart: '2026-04-01', yearEnd: '2026-09-30', yearEndLabel: '30 September 2026' }));
ok('period end used as the as-of date', per.paras[0].includes('as at 30 September 2026'), per.paras[0]);
ok('period end used in the amount line', per.paras[1].includes('as at 30 September 2026'));
ok('period end used in the slip', per.slip.sentence.includes('as on 30 September 2026'));

console.log('\n== 11. Missing balance ==');
const noAmt = BCG.buildLetterModel(make({ partyName: 'A', addressLines: [], amount: null,
  category: 'Trade Receivable' }));
ok('no invented figure', !/INR\s*[\d,]/.test(noAmt.paras[1]), noAmt.paras[1]);
ok('asks the party to state it', noAmt.paras[1].includes('Kindly confirm the balance appearing in your books'), noAmt.paras[1]);

console.log('\n== 12. DOCX parts ==');
const out = '/home/claude/test/fmtout';
fs.rmSync(out, { recursive: true, force: true });
Object.keys(cases).forEach(k => {
  const parts = BCG.docxParts(models[k], cases[k], '2026-11-05T00:00:00Z');
  const dir = path.join(out, k.replace(/\s/g, '_'));
  Object.keys(parts).forEach(p => {
    const full = path.join(dir, p);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, parts[p], 'utf8');
  });
  const xml = parts['word/document.xml'];
  ok(k + ' xml has the title', xml.includes(models[k].title.replace(/&/g, '&amp;')));
  ok(k + ' xml has no bordered form table', !xml.includes('w:val="single" w:sz="6" w:space="0" w:color="808080"'));
  ok(k + ' xml keeps the slip rows', xml.includes('Name and Title'));
});

console.log('\n---------------------------------------');
console.log('PASSED ' + pass + '   FAILED ' + fail);
process.exit(fail ? 1 : 0);
