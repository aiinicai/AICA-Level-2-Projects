'use strict';
/* Team server: serves the tracker as an installable web app (PWA) and keeps one
   shared SQLite database for everyone on the office network.
   Start:  node server/server.js      Options via environment variables:
   PORT (default 8080), HOST (default 0.0.0.0), DATA_DIR (default server/data),
   TRACKER_USER plus TRACKER_PASS to require a login. */
const http = require('http');
const fs = require('fs');
const path = require('path');
const DB = require('../src/db');

const PORT = Number(process.env.PORT || 8080);
const HOST = process.env.HOST || '0.0.0.0';
const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const APP_DIR = path.join(__dirname, '..', 'app');
const USER = process.env.TRACKER_USER, PASS = process.env.TRACKER_PASS;
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json', '.webmanifest': 'application/manifest+json', '.png': 'image/png', '.ico': 'image/x-icon', '.svg': 'image/svg+xml' };

function send(res, code, body, type = 'application/json') {
  res.writeHead(code, { 'Content-Type': type, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body));
}
function authorised(req) {
  if (!USER) return true;
  const h = req.headers.authorization || '';
  const [u, p] = Buffer.from(h.replace(/^Basic /, ''), 'base64').toString().split(':');
  return u === USER && p === PASS;
}
function readBody(req, limit = 20 * 1024 * 1024) {
  return new Promise((resolve, reject) => { let n = 0; const chunks = [];
    req.on('data', c => { n += c.length; if (n > limit) { reject(new Error('Too large')); req.destroy(); } else chunks.push(c); });
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8'))); req.on('error', reject); });
}

(async () => {
  const db = await DB.open(path.join(DATA_DIR, 'dealflow-tracker.sqlite'));
  const backupDir = path.join(DATA_DIR, 'backups');
  const daily = () => { const d = new Date().toISOString().slice(0, 10).replace(/-/g, ''); if (db.lastBackupDay(backupDir) !== d) db.backup(backupDir, 60); };
  daily(); setInterval(daily, 60 * 60 * 1000);

  http.createServer(async (req, res) => {
    try {
      if (!authorised(req)) { res.writeHead(401, { 'WWW-Authenticate': 'Basic realm="Sample Advisory Tracker"' }); return res.end('Login required'); }
      const url = new URL(req.url, 'http://x');
      const p = url.pathname;
      if (p === '/api/health') return send(res, 200, { ok: true, version: db.version() });
      if (p === '/api/version') return send(res, 200, { version: db.version() });
      if (p === '/api/audit') return send(res, 200, db.audit(200));
      if (p === '/api/store' && req.method === 'GET') { const s = db.loadStore(); return send(res, 200, { store: s.store, version: s.version, info: { server: true } }); }
      if (p === '/api/store' && req.method === 'PUT') {
        const { store, baseVersion, actor } = JSON.parse(await readBody(req));
        try { const r = db.saveStore(store, { baseVersion, actor: actor || req.socket.remoteAddress }); return send(res, 200, r); }
        catch (e) { if (e.code === 'CONFLICT') { const s = db.loadStore(); return send(res, 409, { store: s.store, version: s.version }); } throw e; }
      }
      if (p === '/api/backup') { const f = db.backup(backupDir, 60); res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Disposition': `attachment; filename="${path.basename(f)}"` }); return res.end(fs.readFileSync(f)); }
      if (p.startsWith('/api/')) return send(res, 404, { error: 'Not found' });
      // static app files
      let file = path.normalize(path.join(APP_DIR, p === '/' ? 'index.html' : decodeURIComponent(p)));
      if (!file.startsWith(APP_DIR) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(APP_DIR, 'index.html');
      const type = TYPES[path.extname(file)] || 'application/octet-stream';
      res.writeHead(200, { 'Content-Type': type, 'Cache-Control': path.basename(file) === 'sw.js' ? 'no-cache' : 'public, max-age=300' });
      fs.createReadStream(file).pipe(res);
    } catch (e) { console.error(e); send(res, 500, { error: e.message }); }
  }).listen(PORT, HOST, () => console.log(`Sample Advisory tracker server on http://${HOST === '0.0.0.0' ? 'localhost' : HOST}:${PORT}  data: ${DATA_DIR}`));
})();
