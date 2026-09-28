// Builds the protected website copy of the tracker.
// The tracker's code plus embedded data are encrypted with a fresh AES-256-GCM data key;
// the first admin's password wraps that key (PBKDF2 SHA-256, 600,000 iterations), exactly
// as the sign in gate in index.html expects. More users are added later from the tracker's
// Users and access page.
//
// Usage: node protect.js <plain index.html> <protected index.html>
// Admin details come from environment variables (set by "Protect tracker for website.bat"):
//   DF_ADMIN_USER, DF_ADMIN_NAME, DF_ADMIN_PASS, optional DF_API (n8n address)
'use strict';
const fs = require('fs');
const crypto = require('crypto');

const [input, output] = process.argv.slice(2);
if (!input || !output) { console.error('Usage: node protect.js <plain index.html> <protected index.html>'); process.exit(1); }
const user = String(process.env.DF_ADMIN_USER || '').trim().toLowerCase();
const name = String(process.env.DF_ADMIN_NAME || '').trim() || user;
const pass = String(process.env.DF_ADMIN_PASS || '');
const api = String(process.env.DF_API || 'https://your-instance.app.n8n.cloud').replace(/\/+$/, '');
if (!/^[a-z0-9._-]{2,40}$/.test(user)) { console.error('Admin username: 2 to 40 letters, digits, dot, dash or underscore'); process.exit(1); }
if (pass.length < 10) { console.error('Admin password must be at least 10 characters'); process.exit(1); }

let html = fs.readFileSync(input, 'utf8');
if (html.includes('id="data-enc"')) { console.error('This file is already protected; start from the plain index.html'); process.exit(1); }

const dataRe = /<script id="data" type="application\/json">([\s\S]*?)<\/script>/;
const dm = html.match(dataRe);
if (!dm) { console.error('Embedded data block not found'); process.exit(1); }
const appStart = html.indexOf('<script>\n"use strict";\nconst DATA=');
const gateStart = html.indexOf('<script id="gate-js">');
if (appStart < 0 || gateStart < 0) { console.error('App or gate script not found'); process.exit(1); }
const appEnd = html.lastIndexOf('</script>', gateStart);
const appText = html.slice(appStart + '<script>'.length, appEnd);

const b64 = b => Buffer.from(b).toString('base64');
function gcm(key, plain) {
  const iv = crypto.randomBytes(12);
  const c = crypto.createCipheriv('aes-256-gcm', key, iv);
  const ct = Buffer.concat([c.update(plain), c.final(), c.getAuthTag()]);
  return { iv: b64(iv), ct: b64(ct) };
}

const dek = crypto.randomBytes(32);
const payload = gcm(dek, Buffer.from(JSON.stringify({ data: dm[1], app: appText }), 'utf8'));
const salt = crypto.randomBytes(16), it = 600000;
const kek = crypto.pbkdf2Sync(Buffer.from(pass, 'utf8'), salt, it, 32, 'sha256');
const wrapped = gcm(kek, dek);
const admin = { u: user, name, role: 'admin', it, salt: b64(salt), iv: wrapped.iv, wk: wrapped.ct, mustChange: false, disabled: false, updated: new Date().toISOString() };

// remove the readable app script, swap the readable data for the encrypted block, add the built in admin
html = html.slice(0, appStart) + html.slice(appEnd + '</script>'.length);
html = html.replace(dataRe, () => `<script id="data-enc" type="application/json">${JSON.stringify({ v: 1, iv: payload.iv, ct: payload.ct })}</script>`);
html = html.replace('<script id="gate-js">', () => `<script id="users-boot" type="application/json">${JSON.stringify({ api, users: [admin] })}</script>\n<script id="gate-js">`);

// refuse to write if anything readable from the data or the app survived
const probes = [];
try { const d = JSON.parse(dm[1]); (d.items || []).slice(0, 40).forEach(x => { if (x.mobile) probes.push(String(x.mobile).slice(0, 10)); if (x.email) probes.push(x.email); }); } catch (e) {}
probes.push('function renderPipeline', 'const ALIAS=');
const leaked = probes.filter(p => p && p.length > 5 && html.includes(p));
if (leaked.length) { console.error('Refusing to save: readable content found in the output (' + leaked.length + ' matches)'); process.exit(2); }

fs.writeFileSync(output, html, 'utf8');
console.log(JSON.stringify({ saved: output, admin: user, api, bytes: html.length }));
