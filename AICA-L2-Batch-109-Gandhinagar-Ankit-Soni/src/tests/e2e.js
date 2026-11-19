const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const XLSX = require('/tmp/xlsx.full.min.js');

const APP = '/home/claude/app.html';
const TMP = '/home/claude/test/e2e';
fs.rmSync(TMP, { recursive: true, force: true });
fs.mkdirSync(TMP, { recursive: true });

/* A realistic workbook: two title rows, a blank row, then the header. */
const rows = [
  ['Example Manufacturing Private Limited'],
  ['Party-wise balances as at 30.09.2026'],
  [],
  ['Sr No', 'Party Name', 'Address 1', 'Address 2', 'Closing Bal.', 'CCY', 'Nature', 'Email ID'],
  [1, 'ABC Ltd', 'Mumbai', '', 125000, 'INR', 'Trade Receivable', 'ap@abc.example'],
  [2, 'XYZ Suppliers', 'Delhi', '', 80000, 'INR', 'Trade Payable', 'ar@xyz.example'],
  [3, 'Customer P Ltd', 'Pune', '', 50000, 'INR', 'Advance from Customers', 'fin@customerp.example'],
  [4, 'Vendor Q Ltd', 'Chennai', '', 30000, 'INR', 'Advance to Vendors', 'acc@vendorq.example']
];
const wb = XLSX.utils.book_new();
XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), 'Balances');
fs.writeFileSync(path.join(TMP, 'balances.xlsx'),
  Buffer.from(XLSX.write(wb, { type: 'base64', bookType: 'xlsx' }), 'base64'));

const JSZIP_SRC = fs.readFileSync('/tmp/jszip.min.js', 'utf8');
const XLSX_SRC = fs.readFileSync('/tmp/xlsx.full.min.js', 'utf8');

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1050 }, acceptDownloads: true });
  const page = await ctx.newPage();
  await page.route('**/xlsx.full.min.js', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: XLSX_SRC }));
  await page.route('**/jszip.min.js', r => r.fulfill({ status: 200, contentType: 'application/javascript', body: JSZIP_SRC }));

  const errors = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });

  let failures = 0;
  const check = (k, v, x) => { console.log((v ? '  PASS  ' : '  FAIL  ') + k + (v || !x ? '' : ' -> ' + x)); if (!v) failures++; };

  await page.goto('file://' + APP);
  await page.waitForTimeout(900);
  check('libraries loaded', await page.evaluate(() => typeof XLSX !== 'undefined' && typeof JSZip !== 'undefined'));

  /* ---- client + financial year ---- */
  await page.click('.nav button[data-view="clients"]');
  await page.fill('#cl-name', 'Example Manufacturing Private Limited');
  await page.fill('#cl-signatory', 'Mr. R. Mehta');
  await page.click('#cl-add');
  await page.fill('#fy-year', '2026-27');
  await page.fill('#fy-end', '2027-03-31');
  await page.click('#fy-add');
  await page.waitForTimeout(250);
  check('new FY defaults to Statutory Audit', (await page.textContent('#chip-audittype')).includes('Statutory Audit'));
  check('new FY defaults to Year end basis', (await page.textContent('#chip-fy')).includes('Year end: 31 March 2027'),
        await page.textContent('#chip-fy'));
  check('FY table shows type and as-at', (await page.textContent('#fy-list')).includes('Statutory Audit'));

  /* ---- audit team ---- */
  await page.click('.nav button[data-view="settings"]');
  await page.fill('#aud-name', 'M. A'); await page.fill('#aud-email', 'a@gmail.com'); await page.click('#aud-add');
  await page.fill('#aud-name', 'B'); await page.fill('#aud-email', 'b@gmail.com'); await page.click('#aud-add');
  await page.waitForTimeout(200);

  /* ---- import a real .xlsx ---- */
  await page.click('.nav button[data-view="import"]');
  await page.setInputFiles('#file-input', path.join(TMP, 'balances.xlsx'));
  await page.waitForTimeout(900);
  check('header row 4 found below the title rows', (await page.textContent('#hdr-note')).includes('row 4'));
  check('4 data rows', (await page.textContent('#prev-note')).includes('of 4 rows'));
  await page.click('.nav button[data-view="review"]');
  await page.waitForTimeout(400);
  check('no row needs review', (await page.textContent('#nav-review')) === '0');

  /* ---- 1. STATUTORY AUDIT / YEAR END ---- */
  await page.click('.nav button[data-view="preview"]');
  await page.waitForTimeout(350);
  let p = await page.textContent('#pv-paper');
  check('debtor title', p.includes('ACCOUNTS RECEIVABLE/DEBTOR CONFIRMATION'));
  check('letterhead note', p.includes('(on the letter head of the Company)'));
  check('statutory + year end opening',
        p.includes('Our statutory auditors, Ankit Soni and Associates, are engaged in an audit of our financial statements.') &&
        p.includes('the amount payable by you to us as at 31 March 2027'),
        p.slice(p.indexOf('Our Statutory'), p.indexOf('Our Statutory') + 220));
  check('amount in words', p.includes('(In Words: Rupees One Lakh Twenty Five Thousand only)'),
        p.slice(p.indexOf('According to'), p.indexOf('According to') + 170));
  check('auditor email block', p.includes('Ankit Soni and Associates (Chartered Accountants)') &&
        p.includes('Email ID: a@gmail.com; b@gmail.com'));
  check('signed by the company officer', p.includes('Mr. R. Mehta') && p.includes('Director / CFO'));
  check('audit firm does not sign the letter', !p.includes('For Ankit Soni and Associates'));
  check('confirmation slip', p.includes('We hereby confirm that the amount payable by us to Example Manufacturing Private Limited as on 31 March 2027'));
  check('slip rows', p.includes('Name and Title') && p.includes('Company / Firm') && p.includes('Signature'));
  await page.screenshot({ path: TMP + '/01-statutory-yearend.png', fullPage: true });

  /* ---- 2. INTERIM AUDIT / PERIOD END with start date ---- */
  await page.click('.nav button[data-view="settings"]');
  await page.waitForTimeout(250);
  await page.selectOption('#set-audittype', 'Interim Audit');
  await page.waitForTimeout(200);
  await page.selectOption('#set-basis', 'period');
  await page.waitForTimeout(200);
  check('period fields revealed', await page.isVisible('#set-period-fields'));
  check('year-end field hidden', !(await page.isVisible('#set-yearend-field')));
  await page.fill('#set-periodstart', '2026-04-01');
  await page.dispatchEvent('#set-periodstart', 'change');
  await page.waitForTimeout(150);
  await page.fill('#set-periodend', '2026-09-30');
  await page.dispatchEvent('#set-periodend', 'change');
  await page.waitForTimeout(350);
  check('chip switches to Period end', (await page.textContent('#chip-fy')).includes('Period end: 30 September 2026'),
        await page.textContent('#chip-fy'));
  check('chip shows Interim Audit', (await page.textContent('#chip-audittype')).includes('Interim Audit'));
  check('live sentence preview in settings',
        (await page.textContent('#set-period-txt')).includes(
          'Our auditors, Ankit Soni and Associates, are engaged in an interim audit'),
        await page.textContent('#set-period-txt'));
  check('settings shows the as-at date',
        (await page.textContent('#set-yearend-txt')) === '30 September 2026',
        await page.textContent('#set-yearend-txt'));
  await page.screenshot({ path: TMP + '/02-settings-interim.png', fullPage: true });

  await page.click('.nav button[data-view="preview"]');
  await page.waitForTimeout(350);
  p = await page.textContent('#pv-paper');
  check('interim opening', p.includes('Our auditors, Ankit Soni and Associates, are engaged in an interim audit of our financial statements.'),
        p.slice(p.indexOf('Our auditors'), p.indexOf('Our auditors') + 180));
  check('interim: period end used as the as-of date', p.includes('as at 30 September 2026'));
  check('interim: no stale year-end date', !p.includes('31 March 2027'));
  check('interim: debtor wording intact', p.includes('the amount payable by you to us as at'));
  await page.screenshot({ path: TMP + '/03-preview-interim.png', fullPage: true });

  /* ---- 3. SPECIAL PURPOSE AUDIT / PERIOD END without start date ---- */
  await page.click('.nav button[data-view="settings"]');
  await page.waitForTimeout(250);
  await page.selectOption('#set-audittype', 'Special Purpose Audit');
  await page.waitForTimeout(200);
  check('designation follows audit type', (await page.inputValue('#set-desig')) === 'Auditor',
        await page.inputValue('#set-desig'));
  await page.fill('#set-periodstart', '');
  await page.dispatchEvent('#set-periodstart', 'change');
  await page.waitForTimeout(300);
  await page.click('.nav button[data-view="preview"]');
  await page.waitForTimeout(350);
  p = await page.textContent('#pv-paper');
  check('special purpose opening', p.includes('are engaged in a special purpose audit of our financial statements.'),
        p.slice(p.indexOf('Our auditors'), p.indexOf('Our auditors') + 180));
  check('still confirms as on the period end', p.includes('as at 30 September 2026'));

  /* ---- 4. OTHER (free text) + validation gate ---- */
  await page.click('.nav button[data-view="settings"]');
  await page.waitForTimeout(250);
  await page.selectOption('#set-audittype', 'Other');
  await page.waitForTimeout(300);
  check('free-text field appears', await page.isVisible('#set-auditother-field'));
  check('blank Other blocks generation', (await page.textContent('#chip-status')).includes('need attention'),
        await page.textContent('#chip-status'));
  await page.fill('#set-auditother', 'Agreed-upon procedures engagement');
  await page.dispatchEvent('#set-auditother', 'input');
  await page.waitForTimeout(300);
  check('free text clears the gate', (await page.textContent('#chip-status')).includes('Ready to Generate'),
        await page.textContent('#chip-status'));
  await page.click('.nav button[data-view="preview"]');
  await page.waitForTimeout(350);
  p = await page.textContent('#pv-paper');
  check('free text folded into the engagement phrase',
        p.includes('are engaged in an agreed-upon procedures engagement of our financial statements.'),
        p.slice(p.indexOf('Our auditors'), p.indexOf('Our auditors') + 180));

  /* ---- back to Interim for the generation run ---- */
  await page.click('.nav button[data-view="settings"]');
  await page.waitForTimeout(250);
  await page.selectOption('#set-audittype', 'Interim Audit');
  await page.waitForTimeout(200);
  await page.fill('#set-periodstart', '2026-04-01');
  await page.dispatchEvent('#set-periodstart', 'change');
  await page.waitForTimeout(300);

  /* ---- generate ---- */
  await page.click('.nav button[data-view="generate"]');
  await page.waitForTimeout(300);
  check('checklist names the period basis', (await page.textContent('#gen-check')).includes('Period end set'),
        (await page.textContent('#gen-check')).slice(0, 200));
  check('checklist names the audit type', (await page.textContent('#gen-check')).includes('Type of audit chosen'));
  check('checklist names the company signatory', (await page.textContent('#gen-check')).includes('Company signatory named'));
  check('generate enabled', !(await page.isDisabled('#btn-generate')));
  await page.click('#btn-generate');
  await page.waitForFunction(() => document.querySelector('#gen-prog').textContent.startsWith('Done'), null, { timeout: 25000 });
  check('4 documents generated', (await page.textContent('#gen-count')).startsWith('4 of 4'));
  await page.screenshot({ path: TMP + '/04-generate.png', fullPage: true });

  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#btn-zip')]);
  await dl.saveAs(path.join(TMP, 'out.zip'));
  check('zip downloaded', fs.statSync(path.join(TMP, 'out.zip')).size > 2000);

  /* ---- email body picks up the engagement ---- */
  await page.click('.nav button[data-view="email"]');
  await page.waitForTimeout(400);
  const body = await page.inputValue('#mail-body');
  check('email template keeps placeholders', body.includes('{audittype_article}') && body.includes('{period}'),
        body.split('\n')[2]);
  check('email says the letter is the client\'s own',
        body.includes('issued by {client}'), body);
  await page.screenshot({ path: TMP + '/05-email.png', fullPage: true });

  /* ---- saved run records the engagement ---- */
  await page.click('.nav button[data-view="runs"]');
  await page.waitForTimeout(350);
  const runs = await page.textContent('#runs-table');
  check('run records audit type', runs.includes('Interim Audit'));
  check('run records the period', runs.includes('Period from 1 April 2026 to 30 September 2026'), runs.slice(0, 400));
  await page.screenshot({ path: TMP + '/06-runs.png', fullPage: true });

  /* ---- persistence across reload ---- */
  await page.reload();
  await page.waitForTimeout(1200);
  check('engagement restored after reload', (await page.textContent('#chip-audittype')).includes('Interim Audit') &&
        (await page.textContent('#chip-fy')).includes('Period end: 30 September 2026'),
        (await page.textContent('#chip-audittype')) + ' / ' + (await page.textContent('#chip-fy')));

  console.log(errors.length ? '\n  JS errors:\n   ' + errors.join('\n   ') : '\n  No JavaScript errors.');
  failures += errors.length;
  await browser.close();
  console.log('\n---------------------------------------');
  console.log(failures ? 'E2E FAILURES: ' + failures : 'E2E: ALL CHECKS PASSED');
  process.exit(failures ? 1 : 0);
})();
