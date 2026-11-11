/**
 * GSTR-2B Recon Suite — application server
 *
 * One process serves both the React UI and the REST API (/api/*) on the same port,
 * so the browser only ever uses relative URLs — no hard-coded localhost anywhere.
 *
 *   Development (hot reload):   node server.mjs --dev
 *   Production / server host:   npm run build  &&  node server.mjs
 *
 * Environment variables (optional, can also be put in a .env file):
 *   PORT         Port to listen on                       (default 3100)
 *   HOST         Interface to bind                       (default 0.0.0.0 = all network cards)
 *   GSR_DB_PATH  Full path of the SQLite database file   (default <app folder>/data/gstr2b_recon.db)
 *   HTTPS        1 = also serve https (needed to install the app on phones / tablets over the network)
 *   HTTPS_PORT   Port for https                          (default 3443)
 */
import 'dotenv/config';
import express from 'express';
import http from 'node:http';
import https from 'node:https';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { openReconDatabase, DATASET_KINDS } from './shared/db.mjs';
import { ensureCerts } from './shared/certs.mjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';
const PORT = Number(process.env.PORT) || 3100;
const HOST = process.env.HOST || '0.0.0.0';
const USE_HTTPS = /^(1|on|true|yes)$/i.test(process.env.HTTPS || '');
const HTTPS_PORT = Number(process.env.HTTPS_PORT) || 3443;
const CERT_DIR = path.join(__dirname, 'certs');
const DB_PATH = path.resolve(process.env.GSR_DB_PATH || path.join(__dirname, 'data', 'gstr2b_recon.db'));

/* ------------------------------- Database -------------------------------- */
let db;
try {
  db = await openReconDatabase(DB_PATH);
} catch (err) {
  console.error('\n[ERROR] Could not open or create the SQLite database at:\n  ' + DB_PATH);
  console.error('  Reason: ' + err.message);
  console.error('  Check that the folder is writable, or set GSR_DB_PATH to another location.\n');
  process.exit(1);
}

/* --------------------------------- API ----------------------------------- */
const app = express();
app.disable('x-powered-by');
app.set('trust proxy', true);
// Large purchase registers are sent as JSON in one request.
app.use(express.json({ limit: '200mb' }));

const api = express.Router();

const engagementId = (req, res) => {
  const id = Number.parseInt(req.params.id, 10);
  if (!Number.isInteger(id) || id <= 0) {
    res.status(400).json({ error: 'Invalid engagement id' });
    return null;
  }
  if (!db.getEngagement(id)) {
    res.status(404).json({ error: 'Engagement not found' });
    return null;
  }
  return id;
};

api.get('/health', (_req, res) => {
  res.json({ ok: true, driver: db.driver, dbPath: db.file, mode: isDev ? 'development' : 'production' });
});

/* Engagements (one per client + period) */
api.get('/engagements', (_req, res) => res.json(db.listEngagements()));

api.post('/engagements', (req, res) => {
  const name = String(req.body?.name ?? '').trim();
  if (!name) return res.status(400).json({ error: 'Client / engagement name is required' });
  const id = db.createEngagement({ ...req.body, name });
  db.addLog(id, 'SYS', `Engagement "${name}" created.`);
  res.status(201).json(db.getEngagement(id));
});

api.put('/engagements/:id', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  if (req.body?.name != null && !String(req.body.name).trim()) {
    return res.status(400).json({ error: 'Client / engagement name cannot be empty' });
  }
  db.updateEngagement(id, req.body ?? {});
  res.json(db.getEngagement(id));
});

api.delete('/engagements/:id', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  db.deleteEngagement(id);
  res.json({ ok: true });
});

api.get('/engagements/:id/state', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  res.json(db.getState(id));
});

/* Imported registers: body = { fileName, sets: { g2b: [...], g2b_cdn: [...], ... } } */
api.put('/engagements/:id/datasets', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const sets = req.body?.sets;
  if (!sets || typeof sets !== 'object') return res.status(400).json({ error: 'No registers supplied' });
  const unknown = Object.keys(sets).filter((k) => !DATASET_KINDS.includes(k));
  if (unknown.length) return res.status(400).json({ error: `Unknown register type(s): ${unknown.join(', ')}` });
  db.replaceDatasets(id, String(req.body?.fileName ?? ''), sets);
  res.json({ ok: true });
});

api.delete('/engagements/:id/datasets', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const kinds = String(req.query.kinds ?? '')
    .split(',')
    .filter((k) => DATASET_KINDS.includes(k));
  db.clearDatasets(id, kinds);
  res.json({ ok: true });
});

/* Section 17(5) blocked credits */
api.post('/engagements/:id/blocked', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const items = Array.isArray(req.body?.items) ? req.body.items : [];
  res.json({ added: db.addBlocked(id, items) });
});

api.put('/engagements/:id/blocked/:bid', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const bid = Number.parseInt(req.params.bid, 10);
  if (!db.setBlockedActive(id, bid, !!req.body?.active)) return res.status(404).json({ error: 'Blocked entry not found' });
  res.json({ ok: true });
});

/* Ledger remarks */
api.put('/engagements/:id/remarks', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const key = String(req.body?.key ?? '');
  if (!key) return res.status(400).json({ error: 'Remark key missing' });
  db.setRemark(id, key, req.body?.text ?? '');
  res.json({ ok: true });
});

/* Audit trail */
api.get('/engagements/:id/logs', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  res.json(db.listLogs(id));
});

api.post('/engagements/:id/logs', (req, res) => {
  const id = engagementId(req, res);
  if (id === null) return;
  const message = String(req.body?.message ?? '').trim();
  if (!message) return res.status(400).json({ error: 'Log message missing' });
  db.addLog(id, req.body?.tag ?? 'SYS', message);
  res.status(201).json({ ok: true });
});

/* Supplier master: e-mail, MSME classification, Udyam number (shared by all engagements) */
api.get('/suppliers', (_req, res) => res.json(db.listSuppliers()));

api.put('/suppliers/:gstin', (req, res) => {
  const gstin = String(req.params.gstin ?? '').trim().toUpperCase();
  if (!gstin) return res.status(400).json({ error: 'GSTIN missing' });
  res.json(db.saveSupplier(gstin, req.body ?? {}));
});

/* Firm / auditor details printed on notices and e-mails */
api.get('/settings/firm', (_req, res) => {
  try {
    res.json(JSON.parse(db.getSetting('firm') || '{}'));
  } catch {
    res.json({});
  }
});

api.put('/settings/firm', (req, res) => {
  const pick = (k, max = 200) => String(req.body?.[k] ?? '').slice(0, max);
  const firm = { name: pick('name'), ca: pick('ca'), memNo: pick('memNo', 40), email: pick('email'), phone: pick('phone', 40) };
  db.setSetting('firm', JSON.stringify(firm));
  res.json(firm);
});

/* Database backup download */
api.get('/backup', (_req, res, next) => {
  const stamp = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
  const tmp = path.join(os.tmpdir(), `gstr2b_recon_backup_${stamp}_${process.pid}.db`);
  try {
    if (fs.existsSync(tmp)) fs.rmSync(tmp);
    db.backupTo(tmp);
  } catch (err) {
    return next(err);
  }
  res.download(tmp, `gstr2b_recon_backup_${stamp}.db`, () => fs.rm(tmp, { force: true }, () => {}));
});

api.use((_req, res) => res.status(404).json({ error: 'Unknown API endpoint' }));

app.use('/api', api);

// Central API error handler (database errors, bad JSON, oversized uploads, etc.)
app.use('/api', (err, _req, res, _next) => {
  console.error('[api error]', err);
  if (err.type === 'entity.too.large') return res.status(413).json({ error: 'The file is too large to save in one go.' });
  const status = err.type === 'entity.parse.failed' ? 400 : 500;
  res.status(status).json({ error: status === 400 ? 'Malformed JSON body' : 'Database / server error: ' + err.message });
});

/* --------------------------- HTTPS / install help ------------------------- */
let tlsOptions = null;
if (USE_HTTPS) {
  try {
    tlsOptions = ensureCerts(CERT_DIR);
  } catch (err) {
    console.error('[https] Could not create certificates, continuing with http only:', err.message);
  }
}

// Only the public CA certificate is served; the private keys never leave certs/.
app.get('/install/ca.crt', (_req, res) => {
  const ca = path.join(CERT_DIR, 'ca.crt');
  if (!fs.existsSync(ca)) return res.status(404).send('HTTPS is not switched on. Start the app with 2-Start-Server-Host.bat.');
  res.set('Content-Type', 'application/x-x509-ca-cert');
  res.set('Content-Disposition', 'attachment; filename="GSTR-2B-Recon-Local-CA.crt"');
  res.sendFile(ca);
});

app.get('/install', (_req, res) => {
  const ips = lanAddresses();
  const httpsLinks = tlsOptions ? [...ips, os.hostname()].map((h) => `https://${h}:${HTTPS_PORT}`) : [];
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
  res.set('Cache-Control', 'no-cache');
  res.send(`<!doctype html><html lang="en-IN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Install GSTR-2B Recon</title><link rel="icon" href="./icons/favicon-32.png">
<style>body{font-family:system-ui,'Segoe UI',sans-serif;margin:0;background:#f1f5f9;color:#1e293b}main{max-width:720px;margin:0 auto;padding:16px}
h1{font-size:1.3rem}h2{font-size:1rem;margin-top:1.5rem}.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;margin:12px 0}
a.btn{display:inline-block;background:#0d9488;color:#fff;padding:10px 14px;border-radius:8px;text-decoration:none;font-weight:600}
code{background:#f1f5f9;padding:2px 5px;border-radius:4px;word-break:break-all}li{margin:6px 0;line-height:1.45}.warn{background:#fffbeb;border-color:#fde68a}</style></head><body><main>
<h1>Install GSTR-2B Recon Suite</h1>
<div class="card"><b>On this computer</b> (Chrome or Edge): open <code>http://localhost:${PORT}</code> and click <b>Install app</b> in the app's top bar, or the install icon at the right of the address bar.</div>
${
  tlsOptions
    ? `<div class="card"><b>Phones, tablets and other computers</b> must use the <b>https</b> link — browsers only install apps from secure addresses:<ul>${httpsLinks
        .map((l) => `<li><a href="${esc(l)}">${esc(l)}</a></li>`)
        .join('')}</ul>First, do step 1 below once on each device so it trusts this computer.</div>
<h2>Step 1 — trust this computer (once per device)</h2>
<p><a class="btn" href="./install/ca.crt">Download certificate</a></p>
<div class="card"><b>Android</b><ol><li>Tap <b>Download certificate</b> above.</li><li>Open <b>Settings → Security (or Security &amp; privacy) → More security settings → Encryption &amp; credentials → Install a certificate → CA certificate</b>.</li><li>Choose <b>GSTR-2B-Recon-Local-CA.crt</b> from Downloads and confirm.</li></ol></div>
<div class="card"><b>iPhone / iPad</b> (use Safari)<ol><li>Tap <b>Download certificate</b> above, then <b>Allow</b>.</li><li>Open <b>Settings → Profile Downloaded → Install</b> and enter your passcode.</li><li>Open <b>Settings → General → About → Certificate Trust Settings</b> and switch on <b>GSTR-2B Recon Local CA</b>.</li></ol></div>
<div class="card"><b>Another Windows PC</b><ol><li>Download the certificate and double-click it → <b>Install Certificate</b> → <b>Current User</b>.</li><li>Choose <b>Place all certificates in the following store → Trusted Root Certification Authorities</b> → Finish → Yes.</li><li>Restart Chrome / Edge.</li></ol></div>
<h2>Step 2 — install the app</h2>
<div class="card"><b>Android (Chrome):</b> open the https link → menu <b>⋮ → Install app</b> (or <b>Add to Home screen</b>), or tap <b>Install</b> in the app's banner.<br><br>
<b>iPhone / iPad (Safari):</b> open the https link → <b>Share</b> → <b>Add to Home Screen</b>.<br><br>
<b>Computer (Chrome / Edge):</b> open the https link → <b>Install app</b> in the address bar or the app's top bar.</div>
<div class="card warn">The certificate only lets your devices recognise this computer. It was created by the app on this computer and is not shared with anyone else. If the computer's network address changes, the app renews its certificate automatically — devices do not need step 1 again.</div>`
    : `<div class="card warn"><b>HTTPS is off.</b> To install on phones and tablets, start the app with <b>2-Start-Server-Host.bat</b> (it switches HTTPS on), then open this page again.</div>`
}
<p><a href="./">← Back to the app</a></p></main></body></html>`);
});

/* ------------------------------ Front end -------------------------------- */
const httpServer = http.createServer(app);
const httpsServer = tlsOptions ? https.createServer({ key: tlsOptions.key, cert: tlsOptions.cert }, app) : null;

if (isDev) {
  const { createServer: createViteServer } = await import('vite');
  const vite = await createViteServer({
    root: __dirname,
    server: { middlewareMode: true, hmr: { server: httpServer } },
    appType: 'spa',
  });
  app.use(vite.middlewares);
} else {
  const distDir = path.join(__dirname, 'dist');
  if (!fs.existsSync(path.join(distDir, 'index.html'))) {
    console.error('\n[ERROR] Production build not found (dist/index.html).');
    console.error('  Run:  npm run build   and then start again.\n');
    process.exit(1);
  }
  // The service worker must never be served stale, or app updates would not reach installed copies.
  app.get('/sw.js', (_req, res) => {
    res.set('Cache-Control', 'no-cache');
    res.sendFile(path.join(distDir, 'sw.js'));
  });
  app.use(express.static(distDir, { index: false, maxAge: '1h' }));
  app.get('*', (_req, res) => {
    res.set('Cache-Control', 'no-cache');
    res.sendFile(path.join(distDir, 'index.html'));
  });
}

/* -------------------------------- Start ---------------------------------- */
function lanAddresses() {
  const out = [];
  for (const list of Object.values(os.networkInterfaces())) {
    for (const ni of list || []) {
      if (ni.family === 'IPv4' && !ni.internal) out.push(ni.address);
    }
  }
  return out;
}

const onListenError = (port) => (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\n[ERROR] Port ${port} is already in use. Close the other window running the app,`);
    console.error(`  or start on another port, e.g.:  set PORT=3101 && npm start\n`);
  } else {
    console.error('[server error]', err);
  }
  process.exit(1);
};
httpServer.on('error', onListenError(PORT));
httpsServer?.on('error', onListenError(HTTPS_PORT));
httpsServer?.listen(HTTPS_PORT, HOST);

httpServer.listen(PORT, HOST, () => {
  const line = '='.repeat(68);
  console.log(`\n${line}`);
  console.log('  GSTR-2B Recon Suite');
  console.log(line);
  console.log(`  Mode            : ${isDev ? 'Development (hot reload)' : 'Production'}`);
  console.log(`  Localhost link  : http://localhost:${PORT}`);
  if (HOST === '0.0.0.0' || HOST === '::') {
    for (const ip of lanAddresses()) console.log(`  Network link    : http://${ip}:${PORT}   (share with your network)`);
    console.log(`  Computer name   : http://${os.hostname()}:${PORT}`);
  } else {
    console.log(`  Bound to        : ${HOST} (only reachable from this address)`);
  }
  if (httpsServer) {
    console.log(`  HTTPS (install) : https://localhost:${HTTPS_PORT}`);
    if (HOST === '0.0.0.0' || HOST === '::') for (const ip of lanAddresses()) console.log(`  Phones/tablets  : https://${ip}:${HTTPS_PORT}`);
    console.log(`  Install help    : http://localhost:${PORT}/install   (open on each phone / tablet once)`);
  }
  console.log(`  SQLite database : ${db.file}${db.isNew ? '  (newly created)' : ''}`);
  console.log(`  SQLite driver   : ${db.driver}`);
  console.log(`${line}\n  Keep this window open while using the app. Press Ctrl+C to stop.\n`);
});

const shutdown = () => {
  console.log('\nShutting down, saving database...');
  try {
    db.close();
  } catch {
    /* ignore */
  }
  process.exit(0);
};
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
