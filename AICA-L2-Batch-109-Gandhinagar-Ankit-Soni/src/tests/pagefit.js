/* Builds the heaviest realistic letters and checks each stays on one page. */
const fs = require('fs'), path = require('path'), { execSync } = require('child_process');
const BCG = require('/home/claude/test/core.js');
const OUT = '/home/claude/test/fit';
fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT + '/docx', { recursive: true });

const cats = ['Trade Receivable', 'Trade Payable', 'Advance from Customers',
              'Advance to Vendors'];
const spans = [
  ['statutory-year', { auditType: 'Statutory Audit', basis: 'year',
                       asAt: '2027-03-31', periodStart: '' }],
  ['interim-period', { auditType: 'Interim Audit', basis: 'period',
                       asAt: '2026-09-30', periodStart: '2026-04-01' }],
  ['noamount', { auditType: 'Special Purpose Audit', basis: 'period',
                 asAt: '2026-06-30', periodStart: '', amount: null }]
];
const shapes = [
  ['light', {
    clientName: 'Example Manufacturing Private Limited',
    partyName: 'ABC Ltd', addressLines: ['Mumbai'], contactPerson: '',
    amount: 125000, partnerName: '', letterheadNote: false,
    signatoryName: 'Mr. R. Mehta', signatoryDesignation: 'Director / CFO',
    auditors: [{ name: 'M. A', email: 'a@gmail.com' }]
  }],
  ['heavy', {
    clientName: 'Example Manufacturing And Engineering Services Private Limited',
    partyName: 'Shree Balaji Industrial Components And Fabrication Private Limited',
    addressLines: ['Plot 42, MIDC Industrial Estate',
                   'Andheri East, Mumbai 400093', 'Maharashtra, India'],
    contactPerson: 'Mr. R. Krishnamurthy', amount: 123456789.55,
    partnerName: 'CA Chandrashekhar Iyer', letterheadNote: true,
    signatoryName: 'Mr. Rameshchandra Krishnamurthy Subramanian',
    signatoryDesignation: 'Whole-time Director and Chief Financial Officer',
    auditors: [{ name: 'M. A', email: 'a@gmail.com' },
               { name: 'B', email: 'b@gmail.com' },
               { name: 'C', email: 'chandrashekhar.iyer@ankitsoniassociates.example' }]
  }]
];

const cases = [];
shapes.forEach(([sk, shape]) => spans.forEach(([pk, span]) => cats.forEach(cat => {
  const conf = Object.assign({
    firmName: 'Ankit Soni and Associates', firmDesignation: 'Statutory Auditor',
    currency: 'INR', category: cat, auditTypeOther: '',
    letterDate: '2026-11-05', letterDateLabel: '5 November 2026'
  }, shape, span);
  conf.yearEnd = conf.asAt;
  conf.yearEndLabel = BCG.fmtDateLong(conf.asAt);
  cases.push([sk + '--' + pk + '--' + cat.replace(/\s/g, '_'), conf]);
})));

const partsDir = OUT + '/parts';
cases.forEach(([name, conf]) => {
  const parts = BCG.docxParts(BCG.buildLetterModel(conf), conf, '2026-11-05T00:00:00Z');
  const dir = path.join(partsDir, name);
  Object.keys(parts).forEach(p => {
    const full = path.join(dir, p);
    fs.mkdirSync(path.dirname(full), { recursive: true });
    fs.writeFileSync(full, parts[p], 'utf8');
  });
});

execSync(`python3 -I - <<'PY'
import os, zipfile
base = "${partsDir}"
order = ['[Content_Types].xml','_rels/.rels','word/document.xml','word/_rels/document.xml.rels','word/styles.xml','docProps/core.xml','docProps/app.xml']
for name in sorted(os.listdir(base)):
    src = os.path.join(base, name); files = []
    for root, _, fs_ in os.walk(src):
        for f in fs_:
            full = os.path.join(root, f)
            files.append((os.path.relpath(full, src).replace(os.sep, '/'), full))
    files.sort(key=lambda p: order.index(p[0]) if p[0] in order else 99)
    with zipfile.ZipFile(os.path.join("${OUT}/docx", name + ".docx"), 'w', zipfile.ZIP_DEFLATED) as z:
        for rel, full in files: z.write(full, rel)
PY`, { shell: '/bin/bash' });

execSync(`cd ${OUT}/docx && timeout 600 soffice --headless --convert-to pdf *.docx --outdir ${OUT}/pdf >/dev/null 2>&1`,
         { shell: '/bin/bash' });

let fail = 0;
fs.readdirSync(OUT + '/pdf').sort().forEach(f => {
  const pages = parseInt(/Pages:\s+(\d+)/.exec(
    execSync(`pdfinfo "${OUT}/pdf/${f}"`).toString())[1], 10);
  const good = pages === 1;
  if (!good) fail++;
  console.log((good ? '  PASS  ' : '  FAIL  ') + f.replace('.pdf', '') + ' -> ' + pages + ' page(s)');
});
console.log('\n' + (fail ? 'PAGE-FIT FAILURES: ' + fail
                         : 'PAGE FIT: every letter fits on one page'));
process.exit(fail ? 1 : 0);
