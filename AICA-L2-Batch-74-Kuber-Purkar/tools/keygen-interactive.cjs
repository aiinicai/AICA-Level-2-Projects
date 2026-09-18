// CMA Pro Builder — License Key Generator (Chronoflow style, VENDOR ONLY)
// Double-click CMA-Keygen.exe → enter Hardware ID → pick key type → done.
//
//   CMA-Keygen.exe --hwid                 print THIS machine's Hardware ID
//   CMA-Keygen.exe --id <HARDWARE-ID> --type A --year 2027   (non-interactive)
//   CMA-Keygen.exe --id <HARDWARE-ID> --type M               (master, perpetual)
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const { machineShortId, parseHardwareId } = require('../server/license.cjs');

const SIG_PREFIX_LEN = 11;

// Vendor private key → HMAC secret (same derivation as tools/build-exe.cjs)
let PRIV_PEM = '';
try { PRIV_PEM = require('./keygen-private-embedded.cjs') || ''; } catch { /* dev mode */ }
if (!PRIV_PEM) {
  try { PRIV_PEM = fs.readFileSync(path.join(__dirname, 'keygen-private.pem'), 'utf8'); } catch { /* none */ }
}
const SECRET = PRIV_PEM ? crypto.createHash('sha256').update(PRIV_PEM).digest('hex') : '';

const OUT_DIR = (() => {
  try {
    const sea = require('node:sea');
    if (sea.isSea && sea.isSea()) return path.dirname(process.execPath);
  } catch { /* not SEA */ }
  return __dirname;
})();

function generateKey(raw16, type, year) {
  const sig = crypto.createHmac('sha256', SECRET)
    .update(`CMA1|${raw16}|${type}${year}`)
    .digest('hex')
    .slice(0, SIG_PREFIX_LEN)
    .toUpperCase();
  const body = `${type}${year}${sig}`;
  return `CMA-${body.replace(/(.{4})(?=.)/g, '$1-')}`;
}

function arg(name) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : null;
}

function output(raw16, type, year, waitForEnter) {
  const key = generateKey(raw16, type, year);
  const idDisp = raw16.replace(/(.{4})(?=.)/g, '$1-');
  console.log('');
  console.log('  ────────────────────────────────────────────────');
  console.log(`   Hardware ID : ${idDisp}`);
  console.log(`   Key type    : ${type === 'M' ? 'Master (perpetual)' : `Annual (valid till 31-Dec-${year})`}`);
  console.log('  ────────────────────────────────────────────────');
  console.log('');
  console.log(`   LICENSE KEY :  ${key}`);
  console.log('');
  const outFile = path.join(OUT_DIR, `license-${raw16}-${type === 'M' ? 'MASTER' : year}.txt`);
  fs.writeFileSync(outFile, key + '\n', 'utf8');
  console.log(`   Saved to: ${outFile}`);
  console.log('');
  if (waitForEnter && process.stdin.isTTY) {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    rl.question('   Press Enter to close…', () => process.exit(0));
  }
}

async function interactive() {
  // IMPORTANT: always use cooked console mode (terminal:false).
  // In raw mode (terminal:true), Windows console paste (Ctrl+V / right-click)
  // is swallowed by readline — the user can type but CANNOT paste the Hardware ID.
  // Cooked mode lets conhost handle paste + echo natively, for both double-click
  // windows and piped input.
  const rl = readline.createInterface({ input: process.stdin, terminal: false });
  const it = rl[Symbol.asyncIterator]();
  const ask = async (q) => {
    process.stdout.write(q);
    const { value, done } = await it.next();
    return done ? '' : (value || '').trim();
  };
  console.log('');
  console.log('  ══════════════════════════════════════════════');
  console.log('   CMA Pro Builder — License Key Generator');
  console.log('  ══════════════════════════════════════════════');
  console.log('   (Ask the customer for the Hardware ID shown on');
  console.log('    the app\'s activation screen.)');
  console.log('');

  let raw16 = null;
  while (!raw16) {
    const idIn = await ask('  Enter Hardware ID (XXXX-XXXX-XXXX-XXXX): ');
    if (!idIn) { console.log('  (empty — please paste or type the ID)'); continue; }
    raw16 = parseHardwareId(idIn);
    if (!raw16) console.log('  Invalid ID — it must be 16 hex chars like B7BA-EAC3-21DD-CBC5 (checksum wrong?). Try again.');
  }

  let type = '';
  while (!type) {
    const t = await ask('  Key type — 1 = Annual, 2 = Master (perpetual): ');
    if (t === '1') type = 'A';
    else if (t === '2') type = 'M';
    else console.log('  Please enter 1 or 2.');
  }

  let year = '0000';
  if (type === 'A') {
    while (true) {
      const y = await ask('  License year (e.g. 2027 — valid till Dec 31): ');
      if (/^\d{4}$/.test(y) && Number(y) >= 2024) { year = y; break; }
      console.log('  Enter a valid 4-digit year.');
    }
  }
  rl.close();
  output(raw16, type, year, true);
}

// ── entry ──
if (!SECRET) {
  console.error('No vendor key found (embedded or keygen-private.pem). Cannot generate keys.');
  process.exit(1);
}
if (process.argv.includes('--hwid')) {
  const id = machineShortId();
  console.log('');
  console.log(`   This PC's Hardware ID:  ${id.id}`);
  console.log('');
  process.exit(0);
}
if (arg('id') || process.argv.slice(2).find(a => !a.startsWith('--') && parseHardwareId(a))) {
  const raw16 = parseHardwareId(arg('id') || process.argv.slice(2).find(a => !a.startsWith('--') && parseHardwareId(a)));
  if (!raw16) { console.error('Invalid Hardware ID.'); process.exit(1); }
  const type = (arg('type') || '').toUpperCase();
  if (type !== 'A' && type !== 'M') { console.error('--type must be A (annual) or M (master).'); process.exit(1); }
  const year = type === 'M' ? '0000' : (arg('year') || '');
  if (type === 'A' && !/^\d{4}$/.test(year)) { console.error('--year YYYY required for annual keys.'); process.exit(1); }
  output(raw16, type, year, false);
} else {
  interactive();
}
