// ONE-OFF helper (not run by `npm run samples`): renders page 3 of Statement_with_scanned_page.pdf
// as an HTML table and screenshots it with headless Microsoft Edge into assets/scanned_page.png.
// The PNG is committed; the sample generator only embeds it and never needs Edge.
//
// Usage: node scripts/generate-samples/make-scanned-asset.mjs
import { writeFile, mkdtemp } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { scannedStatementData, SCANNED_PNG } from './tools.mjs';
import { fmtDate, fmtAmt } from './lib/util.mjs';
import { OUR_COMPANY } from './lib/names.mjs';

const EDGE = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const { scanned } = scannedStatementData();
const close = scanned[scanned.length - 1].bal;
const rows = scanned
  .map((l) => `<tr><td>${fmtDate(l.date)}</td><td>${l.desc.length > 46 ? l.desc.slice(0, 44) + '..' : l.desc}</td><td>${l.ref}</td><td class="n">${l.wd ? fmtAmt(l.wd) : ''}</td><td class="n">${l.dep ? fmtAmt(l.dep) : ''}</td><td class="n">${fmtAmt(l.bal)}</td></tr>`)
  .join('\n');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1240px;height:1754px;overflow:hidden;background:#e4e2dc}
.sheet{position:absolute;inset:0;padding:90px 70px;transform:rotate(0.35deg);transform-origin:center;
  font-family:Arial,Helvetica,sans-serif;color:#2b2b2b;filter:url(#grain) blur(0.35px) contrast(1.05)}
h1{font-size:27px;margin:0 0 8px;color:#1f2f55} .sub{font-size:17px;margin-bottom:34px}
table{border-collapse:collapse;width:100%;font-size:16.5px}
th{text-align:left;border-bottom:2px solid #444;padding:7px 6px} td{padding:9px 6px;border-bottom:1px solid #b9b6ae}
.n{text-align:right} th.n{text-align:right} .b td{font-weight:bold}
.foot{position:absolute;bottom:70px;left:0;right:0;text-align:center;font-size:15px}
.stain{position:absolute;right:110px;top:300px;width:260px;height:180px;border-radius:50%;background:rgba(150,130,90,.07)}
</style></head><body>
<svg width="0" height="0" style="position:absolute"><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed="7"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="table" tableValues="0 0.10"/></feComponentTransfer><feComposite in2="SourceGraphic" operator="in"/><feBlend in="SourceGraphic" mode="multiply"/></filter></svg>
<div class="sheet"><div class="stain"></div>
<h1>Al Safa Commercial Bank PJSC - Statement of Account</h1>
<div class="sub">${OUR_COMPANY} &nbsp;|&nbsp; Account 0450-7781-0021 &nbsp;|&nbsp; AED &nbsp;|&nbsp; 01-Aug-2026 to 31-Aug-2026</div>
<table><thead><tr><th>Date</th><th>Description</th><th>Reference</th><th class="n">Debit</th><th class="n">Credit</th><th class="n">Balance</th></tr></thead>
<tbody>${rows}
<tr class="b"><td>31-Aug-2026</td><td>CLOSING BALANCE</td><td></td><td></td><td></td><td class="n">${fmtAmt(close)}</td></tr></tbody></table>
<div class="foot">Page 3 of 3</div></div></body></html>`;

const dir = await mkdtemp(join(tmpdir(), 'reco-scan-'));
const htmlPath = join(dir, 'page3.html');
await writeFile(htmlPath, html);
execFileSync(EDGE, ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--force-device-scale-factor=1', `--screenshot=${SCANNED_PNG}`, '--window-size=1240,1754', pathToFileURL(htmlPath).href], { stdio: 'inherit' });
console.log(`Wrote ${SCANNED_PNG}`);
