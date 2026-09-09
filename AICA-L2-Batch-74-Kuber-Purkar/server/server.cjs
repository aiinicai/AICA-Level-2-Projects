// CMA Pro Builder — LAN server
// Serves the built frontend + multi-client API (node:sqlite) + license gate.
const express = require('express');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { DatabaseSync } = require('node:sqlite');
const { machineIdentity, licenseStatus, activate } = require('./license.cjs');

const ROOT = path.resolve(__dirname, '..');
let sea = null;
try { sea = require('node:sea'); } catch { /* older node without SEA */ }
const IS_SEA = !!(sea && typeof sea.isSea === 'function' && sea.isSea());
// In exe mode, data lives next to the .exe so it survives moves/updates.
const BASE_DIR = IS_SEA ? path.dirname(process.execPath) : ROOT;
const DATA_DIR = process.env.CMA_DATA_DIR || path.join(BASE_DIR, 'data');
const DIST_DIR = path.join(ROOT, 'dist');
const PORT = Number(process.env.PORT || 8080);

fs.mkdirSync(DATA_DIR, { recursive: true });
const db = new DatabaseSync(path.join(DATA_DIR, 'cma.db'));
db.exec(`
  CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )
`);

const app = express();
app.use(express.json({ limit: '20mb' }));

// ── License / health ──
app.get('/api/health', (req, res) => {
  const st = licenseStatus(DATA_DIR);
  res.json({ ok: true, ...st });
});

app.get('/api/license/status', (req, res) => {
  res.json(licenseStatus(DATA_DIR));
});

app.post('/api/license/activate', (req, res) => {
  const r = activate(req.body?.key, DATA_DIR);
  if (!r.ok) return res.status(400).json({ ok: false, reason: r.reason });
  res.json({ ok: true, keyType: r.keyType, year: r.year, expiry: r.expiry });
});

// ── License gate for client-data writes ──
function requireLicense(req, res, next) {
  const st = licenseStatus(DATA_DIR);
  if (!st.licensed) return res.status(402).json({ ok: false, reason: st.reason || 'unlicensed', machineCode: st.machineCode });
  next();
}

// ── Clients API ──
app.get('/api/clients', (req, res) => {
  const rows = db.prepare('SELECT id, name, data, updated_at FROM clients ORDER BY updated_at DESC').all();
  res.json(rows.map(r => ({ ...JSON.parse(r.data), updatedAt: r.updated_at })));
});

app.put('/api/clients/:id', requireLicense, (req, res) => {
  const rec = req.body;
  if (!rec || !rec.id || rec.id !== req.params.id) return res.status(400).json({ ok: false, reason: 'bad-record' });
  const updatedAt = rec.updatedAt || new Date().toISOString();
  db.prepare('INSERT INTO clients (id, name, data, updated_at) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, data=excluded.data, updated_at=excluded.updated_at')
    .run(rec.id, rec.name || rec.id, JSON.stringify(rec), updatedAt);
  res.json({ ok: true });
});

app.delete('/api/clients/:id', requireLicense, (req, res) => {
  db.prepare('DELETE FROM clients WHERE id = ?').run(req.params.id);
  res.json({ ok: true });
});

// ── Static frontend (SPA) ──
if (IS_SEA) {
  // Serve the embedded dist/ assets straight from the exe — nothing on disk needed.
  const MIME = {
    '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.json': 'application/json',
    '.woff': 'font/woff', '.woff2': 'font/woff2', '.map': 'application/json',
  };
  const assets = new Map();
  for (const key of sea.getAssetKeys()) {
    if (key.startsWith('dist/')) assets.set(key.slice(5), Buffer.from(sea.getAsset(key)));
  }
  app.get(/^\/(?!api\/).*/, (req, res) => {
    let p = decodeURIComponent(req.path.split('?')[0]);
    if (p === '/' || p === '') p = '/index.html';
    let buf = assets.get(p.replace(/^\/+/, ''));
    let ext = path.extname(p).toLowerCase();
    if (!buf) { buf = assets.get('index.html'); ext = '.html'; } // SPA fallback
    if (!buf) return res.status(404).end('not found');
    res.setHeader('Content-Type', MIME[ext] || 'application/octet-stream');
    res.setHeader('Cache-Control', ext === '.html' ? 'no-cache' : 'public, max-age=31536000, immutable');
    res.end(buf);
  });
} else if (fs.existsSync(DIST_DIR)) {
  app.use(express.static(DIST_DIR));
  app.get(/^\/(?!api\/).*/, (req, res) => res.sendFile(path.join(DIST_DIR, 'index.html')));
}

const server = app.listen(PORT, '0.0.0.0', () => {
  const st = licenseStatus(DATA_DIR);
  const nets = os.networkInterfaces();
  const addrs = [];
  for (const list of Object.values(nets)) {
    for (const ni of list || []) {
      if (ni.family === 'IPv4' && !ni.internal) addrs.push(ni.address);
    }
  }
  console.log('');
  console.log('  ══════════════════════════════════════════════════');
  console.log('   CMA Pro Builder server running');
  console.log('  ══════════════════════════════════════════════════');
  console.log(`   Local:   http://localhost:${PORT}`);
  addrs.forEach(a => console.log(`   LAN:     http://${a}:${PORT}   ← open this on any office PC`));
  console.log(`   Data:    ${DATA_DIR}`);
  if (st.licensed) {
    console.log(`   License: ACTIVE (${st.keyType || 'licensed'}${st.expiry ? ', expires ' + st.expiry : ''})`);
  } else {
    console.log('   License: NOT ACTIVATED — Hardware ID:');
    console.log(`            ${st.hardwareId}`);
  }
  console.log('');
  console.log('   (Keep this window open while using the app. Close it to stop the server.)');
  console.log('');

  // Auto-open the browser (also in hidden mode — there is no console to read)
  if (process.platform === 'win32' && !process.env.CMA_NO_BROWSER) {
    try { require('child_process').exec(`start http://localhost:${PORT}`); } catch { /* ignore */ }
  }
});

// Friendly message instead of a crash when the port is already in use
server.on('error', (err) => {
  if (err && err.code === 'EADDRINUSE') {
    console.log('');
    console.log('  ══════════════════════════════════════════════════');
    console.log('   CMA Pro Builder is ALREADY RUNNING on this PC.');
    console.log('  ══════════════════════════════════════════════════');
    console.log(`   Open in your browser:  http://localhost:${PORT}`);
    console.log('');
    console.log('   (Only one instance can run at a time. If the app is not');
    console.log('    opening, close the other CMA window or restart the PC.)');
    console.log('');
    if (process.platform === 'win32') {
      try { require('child_process').exec(`start http://localhost:${PORT}`); } catch { /* ignore */ }
    }
    if (process.stdout.isTTY) {
      require('readline').createInterface({ input: process.stdin, output: process.stdout })
        .question('   Press Enter to close…', () => process.exit(1));
    } else {
      process.exit(1); // hidden mode: browser opened, exit silently
    }
  } else {
    throw err;
  }
});
