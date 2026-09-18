// CMA Pro Builder — Keygen (STAYS WITH THE SOFTWARE VENDOR ONLY)
// Usage:
//   node tools/keygen.cjs --init                                 (first time: create keypair)
//   node tools/keygen.cjs --fingerprint '<json>' --customer "ABC & Associates" --expiry 2027-03-31 --max-clients 10
// The --fingerprint JSON is copied by the customer from the app's activation screen
// (or from the server console via  node tools/fingerprint.cjs).
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const PRIV = path.join(__dirname, 'keygen-private.pem');       // NEVER ship this
const PUB_SERVER = path.join(__dirname, '..', 'server', 'license-public.pem'); // ships with server
const PUB_LOCAL = path.join(__dirname, 'license-public.pem');

function arg(name) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 ? process.argv[i + 1] : null;
}

if (arg('init') !== null || !fs.existsSync(PRIV)) {
  const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
  const privPem = privateKey.export({ type: 'pkcs1', format: 'pem' });
  const pubPem = publicKey.export({ type: 'pkcs1', format: 'pem' });
  fs.writeFileSync(PRIV, privPem);
  fs.writeFileSync(PUB_SERVER, pubPem);
  fs.writeFileSync(PUB_LOCAL, pubPem);
  console.log('Keypair created.');
  console.log('  Private key (KEEP SECRET):', PRIV);
  console.log('  Public key (ships with server):', PUB_SERVER);
  if (arg('init') !== null) process.exit(0);
}

const fpRaw = arg('fingerprint');
const customer = arg('customer') || 'Licensed Customer';
const expiry = arg('expiry'); // YYYY-MM-DD or omit for perpetual
const maxClients = Number(arg('max-clients') || 50);

if (!fpRaw) {
  console.log('Usage: node tools/keygen.cjs --fingerprint \'{"cpu":"...","board":"...","mac":"..."}\' --customer "Name" [--expiry YYYY-MM-DD] [--max-clients 10]');
  process.exit(1);
}

let machine;
try {
  machine = JSON.parse(fpRaw);
} catch {
  // maybe it's a path to a JSON file
  if (fs.existsSync(fpRaw)) machine = JSON.parse(fs.readFileSync(fpRaw, 'utf8'));
  else { console.error('Fingerprint must be a JSON string or a path to a JSON file.'); process.exit(1); }
}
if (!machine.cpu && !machine.board && !machine.mac) {
  console.error('Fingerprint JSON must contain cpu / board / mac hashes.');
  process.exit(1);
}

const payload = {
  product: 'cma-pro-builder',
  customer,
  machine,
  expiry: expiry || null,
  maxClients,
  issuedAt: new Date().toISOString(),
};
const payloadB64 = Buffer.from(JSON.stringify(payload), 'utf8').toString('base64url');
const signer = crypto.createSign('RSA-SHA256');
signer.update(payloadB64);
const sig = signer.sign(fs.readFileSync(PRIV, 'utf8')).toString('base64url');
const key = `${payloadB64}.${sig}`;

console.log('');
console.log('License key for:', customer, expiry ? `(expires ${expiry})` : '(perpetual)');
console.log('');
console.log(key);
console.log('');
const outFile = path.join(__dirname, `license-${customer.replace(/[^a-z0-9]+/gi, '_')}.txt`);
fs.writeFileSync(outFile, key, 'utf8');
console.log('Saved to:', outFile);
