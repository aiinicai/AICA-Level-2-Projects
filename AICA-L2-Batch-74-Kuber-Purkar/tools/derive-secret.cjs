// Derives the license HMAC secret from the vendor private key and writes
// server/license-secret.txt (development fallback; the executable embeds it).
// Run: node tools/derive-secret.cjs
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const pemPath = path.join(ROOT, 'tools', 'keygen-private.pem');
if (!fs.existsSync(pemPath)) {
  console.error('tools/keygen-private.pem not found - run keygen --init first');
  process.exit(1);
}
const secret = crypto.createHash('sha256').update(fs.readFileSync(pemPath, 'utf8')).digest('hex');
fs.writeFileSync(path.join(ROOT, 'server', 'license-secret.txt'), secret + '\n');
console.log('Secret derived: server/license-secret.txt');
