/**
 * Local HTTPS certificates, created with Node's own crypto (no OpenSSL / mkcert needed).
 *
 * Phones and tablets only treat a web app as installable when it is served over https.
 * On the office network there is no public domain, so the app makes:
 *   certs/ca.crt      a private "GSTR-2B Recon Local CA" (valid 10 years) — install this once on
 *                     each phone / tablet / PC that should trust the app (see /install)
 *   certs/server.crt  the server certificate for this computer's name and network IPs, signed by
 *                     that CA (valid 397 days; renewed automatically when the IP changes or it nears expiry)
 * Private keys stay in certs/ on this computer and are never served.
 */
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/* ------------------------------ Minimal DER ------------------------------- */

const len = (n) => {
  if (n < 0x80) return Buffer.from([n]);
  const b = [];
  while (n > 0) {
    b.unshift(n & 0xff);
    n >>= 8;
  }
  return Buffer.from([0x80 | b.length, ...b]);
};
const tlv = (tag, content) => Buffer.concat([Buffer.from([tag]), len(content.length), content]);
const seq = (...items) => tlv(0x30, Buffer.concat(items));
const set = (...items) => tlv(0x31, Buffer.concat(items));
const ctx = (n, content) => tlv(0xa0 + n, content); // [n] EXPLICIT
const int = (buf) => tlv(0x02, buf[0] & 0x80 ? Buffer.concat([Buffer.from([0]), buf]) : buf);
const bool = (v) => tlv(0x01, Buffer.from([v ? 0xff : 0]));
const octet = (buf) => tlv(0x04, buf);
const bits = (buf, unused = 0) => tlv(0x03, Buffer.concat([Buffer.from([unused]), buf]));
const utf8 = (s) => tlv(0x0c, Buffer.from(s, 'utf8'));
const NULL = Buffer.from([0x05, 0x00]);

function oid(str) {
  const p = str.split('.').map(Number);
  const out = [40 * p[0] + p[1]];
  for (const v of p.slice(2)) {
    const b = [v & 0x7f];
    let x = v >>> 7;
    while (x > 0) {
      b.unshift((x & 0x7f) | 0x80);
      x >>>= 7;
    }
    out.push(...b);
  }
  return tlv(0x06, Buffer.from(out));
}

function time(d) {
  const p = (n) => String(n).padStart(2, '0');
  const s = `${p(d.getUTCMonth() + 1)}${p(d.getUTCDate())}${p(d.getUTCHours())}${p(d.getUTCMinutes())}${p(d.getUTCSeconds())}Z`;
  const y = d.getUTCFullYear();
  return y < 2050 ? tlv(0x17, Buffer.from(String(y).slice(2) + s)) : tlv(0x18, Buffer.from(String(y) + s));
}

const name = (cn, org = 'GSTR-2B Recon Suite') => seq(set(seq(oid('2.5.4.10'), utf8(org))), set(seq(oid('2.5.4.3'), utf8(cn))));
const ext = (id, critical, value) => seq(oid(id), ...(critical ? [bool(true)] : []), octet(value));
const SHA256_RSA = seq(oid('1.2.840.113549.1.1.11'), NULL);

function ipBytes(ip) {
  if (ip.includes(':')) {
    const [a, b = ''] = ip.split('::');
    const A = a ? a.split(':') : [];
    const B = b ? b.split(':') : [];
    const parts = [...A, ...Array(8 - A.length - B.length).fill('0'), ...B];
    return Buffer.from(parts.flatMap((h) => [parseInt(h, 16) >> 8, parseInt(h, 16) & 0xff]));
  }
  return Buffer.from(ip.split('.').map(Number));
}

function makeCert({ subject, issuer, publicKey, signKey, days, ca, hosts = [], issuerKeyId }) {
  const spki = publicKey.export({ type: 'spki', format: 'der' });
  const keyId = crypto.createHash('sha1').update(spki).digest();
  const notBefore = new Date(Date.now() - 864e5);
  const notAfter = new Date(Date.now() + days * 864e5);
  const exts = [
    ext('2.5.29.19', true, ca ? seq(bool(true)) : seq()), // basicConstraints
    // keyUsage: CA = digitalSignature + keyCertSign + cRLSign; server = digitalSignature + keyEncipherment
    ext('2.5.29.15', true, ca ? bits(Buffer.from([0x86]), 1) : bits(Buffer.from([0xa0]), 5)),
    ext('2.5.29.14', false, octet(keyId)), // subjectKeyIdentifier
  ];
  if (!ca) {
    exts.push(ext('2.5.29.37', false, seq(oid('1.3.6.1.5.5.7.3.1')))); // extKeyUsage: serverAuth
    const san = hosts.map((h) => (/^[\d.]+$|:/.test(h) ? tlv(0x87, ipBytes(h)) : tlv(0x82, Buffer.from(h, 'ascii'))));
    exts.push(ext('2.5.29.17', false, seq(...san))); // subjectAltName
    if (issuerKeyId) exts.push(ext('2.5.29.35', false, seq(tlv(0x80, issuerKeyId)))); // authorityKeyIdentifier
  }
  const serial = crypto.randomBytes(16);
  serial[0] &= 0x7f;
  const tbs = seq(ctx(0, int(Buffer.from([2]))), int(serial), SHA256_RSA, issuer, seq(time(notBefore), time(notAfter)), subject, spki, ctx(3, seq(...exts)));
  const sig = crypto.sign('sha256', tbs, signKey);
  const der = seq(tbs, SHA256_RSA, bits(sig));
  return `-----BEGIN CERTIFICATE-----\n${der.toString('base64').match(/.{1,64}/g).join('\n')}\n-----END CERTIFICATE-----\n`;
}

/* ------------------------------- Public API -------------------------------- */

/** Names and addresses this computer can be reached at on the network. */
export function localHosts() {
  const hosts = new Set(['localhost', '127.0.0.1', os.hostname().toLowerCase(), `${os.hostname().toLowerCase()}.local`]);
  for (const list of Object.values(os.networkInterfaces())) {
    for (const ni of list || []) if (ni.family === 'IPv4' && !ni.internal) hosts.add(ni.address);
  }
  return [...hosts];
}

/** Creates (or renews) the CA and server certificate in `dir`; returns what https.createServer needs. */
export function ensureCerts(dir) {
  fs.mkdirSync(dir, { recursive: true });
  const f = (n) => path.join(dir, n);
  const caName = name('GSTR-2B Recon Local CA');

  if (!fs.existsSync(f('ca.key')) || !fs.existsSync(f('ca.crt'))) {
    const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
    fs.writeFileSync(f('ca.key'), privateKey.export({ type: 'pkcs8', format: 'pem' }), { mode: 0o600 });
    fs.writeFileSync(f('ca.crt'), makeCert({ subject: caName, issuer: caName, publicKey, signKey: privateKey, days: 3650, ca: true }));
    for (const n of ['server.key', 'server.crt', 'server.json']) fs.rmSync(f(n), { force: true });
  }
  const caKey = crypto.createPrivateKey(fs.readFileSync(f('ca.key')));
  const caCert = new crypto.X509Certificate(fs.readFileSync(f('ca.crt')));
  const caKeyId = crypto.createHash('sha1').update(caCert.publicKey.export({ type: 'spki', format: 'der' })).digest();

  const hosts = localHosts();
  let renew = !fs.existsSync(f('server.crt')) || !fs.existsSync(f('server.key'));
  if (!renew) {
    try {
      const meta = JSON.parse(fs.readFileSync(f('server.json'), 'utf8'));
      const cert = new crypto.X509Certificate(fs.readFileSync(f('server.crt')));
      const daysLeft = (new Date(cert.validTo).getTime() - Date.now()) / 864e5;
      renew = daysLeft < 30 || hosts.some((h) => !meta.hosts.includes(h)) || !cert.verify(caCert.publicKey);
    } catch {
      renew = true;
    }
  }
  if (renew) {
    const { privateKey, publicKey } = crypto.generateKeyPairSync('rsa', { modulusLength: 2048 });
    fs.writeFileSync(f('server.key'), privateKey.export({ type: 'pkcs8', format: 'pem' }), { mode: 0o600 });
    fs.writeFileSync(
      f('server.crt'),
      makeCert({ subject: name(os.hostname()), issuer: caName, publicKey, signKey: caKey, days: 397, ca: false, hosts, issuerKeyId: caKeyId })
    );
    fs.writeFileSync(f('server.json'), JSON.stringify({ hosts, created: new Date().toISOString() }, null, 2));
  }
  const serverCert = fs.readFileSync(f('server.crt'));
  return {
    key: fs.readFileSync(f('server.key')),
    // Send the CA too, so devices only need to trust ca.crt
    cert: Buffer.concat([serverCert, fs.readFileSync(f('ca.crt'))]),
    caFile: f('ca.crt'),
    hosts,
    renewed: renew,
  };
}
