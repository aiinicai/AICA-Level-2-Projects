'use strict';

/**
 * Kashyap & Co. - Assignment Profitability App
 * Zero-dependency Node.js server (uses only Node's built-in modules).
 *
 * Run:  node server.js
 * Then open http://localhost:3000 in your browser.
 */

const http = require('http');
const fs = require('fs');
const path = require('path');
const { URL } = require('url');

const { Db } = require('./lib/db');
const { computeAllocation } = require('./lib/allocation');

const PORT = process.env.PORT ? Number(process.env.PORT) : 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');

const db = new Db();

// ---------------------------------------------------------------------
// Small helpers
// ---------------------------------------------------------------------

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
  });
  res.end(body);
}

function sendError(res, status, message, details) {
  sendJson(res, status, { error: true, message, details: details || undefined });
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    let size = 0;
    const MAX = 2 * 1024 * 1024; // 2 MB safety cap
    req.on('data', chunk => {
      size += chunk.length;
      if (size > MAX) {
        reject(new Error('Request body too large'));
        req.destroy();
        return;
      }
      data += chunk;
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try {
        resolve(JSON.parse(data));
      } catch (e) {
        reject(new Error('Invalid JSON body'));
      }
    });
    req.on('error', reject);
  });
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function serveStatic(req, res, urlPath) {
  let relPath = urlPath === '/' ? '/index.html' : urlPath;
  // prevent path traversal
  const safePath = path.normalize(relPath).replace(/^(\.\.[/\\])+/, '');
  const filePath = path.join(PUBLIC_DIR, safePath);
  if (!filePath.startsWith(PUBLIC_DIR)) {
    sendError(res, 403, 'Forbidden');
    return;
  }
  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') {
        res.writeHead(404, { 'Content-Type': 'text/plain' });
        res.end('Not found');
      } else {
        res.writeHead(500, { 'Content-Type': 'text/plain' });
        res.end('Server error');
      }
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(content);
  });
}

// ---------------------------------------------------------------------
// Validation helpers
// ---------------------------------------------------------------------

function isValidManagerId(id) {
  return db.data.managers.some(m => m.id === id);
}

function isValidAssignmentId(id) {
  return db.data.assignments.some(a => a.id === id);
}

// ---------------------------------------------------------------------
// Route handlers
// ---------------------------------------------------------------------

async function handleApi(req, res, url) {
  const segments = url.pathname.split('/').filter(Boolean); // ['api', 'assignments', ':id']
  const [, resource, id, sub] = segments;

  try {
    // ---------------- meta ----------------
    if (resource === 'meta' && req.method === 'GET') {
      return sendJson(res, 200, db.data.meta);
    }

    // ---------------- dashboard ----------------
    if (resource === 'dashboard' && req.method === 'GET') {
      const result = computeAllocation(db.data);
      return sendJson(res, 200, result);
    }

    // ---------------- managers ----------------
    if (resource === 'managers' && req.method === 'GET' && !id) {
      const result = computeAllocation(db.data);
      return sendJson(res, 200, result.managers);
    }

    // ---------------- assignments ----------------
    if (resource === 'assignments') {
      if (req.method === 'GET' && !id) {
        const result = computeAllocation(db.data);
        let list = result.assignments;
        const managerId = url.searchParams.get('managerId');
        const status = url.searchParams.get('status');
        if (managerId) list = list.filter(a => a.managerId === managerId);
        if (status) list = list.filter(a => a.status === status);
        return sendJson(res, 200, list);
      }
      if (req.method === 'GET' && id) {
        const result = computeAllocation(db.data);
        const a = result.assignmentsById[id];
        if (!a) return sendError(res, 404, 'Assignment not found');
        const staff = db.listStaff().filter(s => s.assignmentId === id);
        const revenue = db.listRevenue().filter(r => r.assignmentId === id)
          .sort((x, y) => (x.date < y.date ? -1 : 1));
        return sendJson(res, 200, { ...a, staff, revenue });
      }
      if (req.method === 'POST') {
        const body = await readJsonBody(req);
        if (!body.name || !String(body.name).trim()) {
          return sendError(res, 400, 'Assignment name is required');
        }
        if (body.managerId && !isValidManagerId(body.managerId)) {
          return sendError(res, 400, 'Unknown managerId');
        }
        const a = db.addAssignment(body);
        return sendJson(res, 201, a);
      }
      if (req.method === 'PUT' && id) {
        if (!isValidAssignmentId(id)) return sendError(res, 404, 'Assignment not found');
        const body = await readJsonBody(req);
        if (body.managerId && !isValidManagerId(body.managerId)) {
          return sendError(res, 400, 'Unknown managerId');
        }
        const a = db.updateAssignment(id, body);
        return sendJson(res, 200, a);
      }
      if (req.method === 'DELETE' && id) {
        const ok = db.deleteAssignment(id);
        if (!ok) return sendError(res, 404, 'Assignment not found');
        return sendJson(res, 200, { deleted: true });
      }
    }

    // ---------------- staff ----------------
    if (resource === 'staff') {
      if (req.method === 'GET' && !id) {
        let list = db.listStaff();
        const managerId = url.searchParams.get('managerId');
        const assignmentId = url.searchParams.get('assignmentId');
        const scope = url.searchParams.get('scope');
        if (managerId) list = list.filter(s => s.managerId === managerId);
        if (assignmentId) list = list.filter(s => s.assignmentId === assignmentId);
        if (scope) list = list.filter(s => s.scope === scope);
        return sendJson(res, 200, list);
      }
      if (req.method === 'POST') {
        const body = await readJsonBody(req);
        if (!body.managerId || !isValidManagerId(body.managerId)) {
          return sendError(res, 400, 'A valid managerId is required');
        }
        if (!body.cost && body.cost !== 0) {
          return sendError(res, 400, 'cost is required');
        }
        if (body.scope === 'dedicated' && (!body.assignmentId || !isValidAssignmentId(body.assignmentId))) {
          return sendError(res, 400, 'A valid assignmentId is required for dedicated staff');
        }
        const s = db.addStaff(body);
        return sendJson(res, 201, s);
      }
      if (req.method === 'PUT' && id) {
        const body = await readJsonBody(req);
        if (body.managerId && !isValidManagerId(body.managerId)) {
          return sendError(res, 400, 'Unknown managerId');
        }
        if (body.assignmentId && !isValidAssignmentId(body.assignmentId)) {
          return sendError(res, 400, 'Unknown assignmentId');
        }
        const s = db.updateStaff(id, body);
        if (!s) return sendError(res, 404, 'Staff entry not found');
        return sendJson(res, 200, s);
      }
      if (req.method === 'DELETE' && id) {
        const ok = db.deleteStaff(id);
        if (!ok) return sendError(res, 404, 'Staff entry not found');
        return sendJson(res, 200, { deleted: true });
      }
    }

    // ---------------- revenue ----------------
    if (resource === 'revenue') {
      if (req.method === 'GET' && !id) {
        let list = db.listRevenue();
        const assignmentId = url.searchParams.get('assignmentId');
        const type = url.searchParams.get('type');
        if (assignmentId) list = list.filter(r => r.assignmentId === assignmentId);
        if (type) list = list.filter(r => r.type === type);
        return sendJson(res, 200, list);
      }
      if (req.method === 'POST') {
        const body = await readJsonBody(req);
        if (!body.assignmentId || !isValidAssignmentId(body.assignmentId)) {
          return sendError(res, 400, 'A valid assignmentId is required');
        }
        if (body.amount === undefined || Number.isNaN(Number(body.amount))) {
          return sendError(res, 400, 'A numeric amount is required');
        }
        const r = db.addRevenue(body);
        return sendJson(res, 201, r);
      }
      if (req.method === 'PUT' && id) {
        const body = await readJsonBody(req);
        if (body.assignmentId && !isValidAssignmentId(body.assignmentId)) {
          return sendError(res, 400, 'Unknown assignmentId');
        }
        const r = db.updateRevenue(id, body);
        if (!r) return sendError(res, 404, 'Revenue entry not found');
        return sendJson(res, 200, r);
      }
      if (req.method === 'DELETE' && id) {
        const ok = db.deleteRevenue(id);
        if (!ok) return sendError(res, 404, 'Revenue entry not found');
        return sendJson(res, 200, { deleted: true });
      }
    }

    return sendError(res, 404, `No such API route: ${req.method} ${url.pathname}`);
  } catch (err) {
    const clientFault = err && (err.message === 'Invalid JSON body' || err.message === 'Request body too large');
    if (!clientFault) {
      // eslint-disable-next-line no-console
      console.error('API error:', err);
    }
    return sendError(res, clientFault ? 400 : 500, clientFault ? err.message : 'Internal server error', clientFault ? undefined : err.message);
  }
}

// ---------------------------------------------------------------------
// HTTP server
// ---------------------------------------------------------------------

const server = http.createServer((req, res) => {
  let url;
  try {
    url = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
  } catch (e) {
    res.writeHead(400);
    res.end('Bad request');
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    handleApi(req, res, url);
    return;
  }

  if (req.method !== 'GET' && req.method !== 'HEAD') {
    sendError(res, 405, 'Method not allowed');
    return;
  }

  serveStatic(req, res, url.pathname);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    // eslint-disable-next-line no-console
    console.error(`\nPort ${PORT} is already in use.`);
    console.error(`Close whatever is using it, or run with a different port:`);
    console.error(`  PORT=4000 node server.js\n`);
    process.exit(1);
  }
  throw err;
});

server.listen(PORT, () => {
  // eslint-disable-next-line no-console
  console.log('=======================================================');
  console.log(' Kashyap & Co. - Assignment Profitability App');
  console.log('=======================================================');
  console.log(` Server running at: http://localhost:${PORT}`);
  console.log(' Press Ctrl+C to stop.');
  console.log('=======================================================');
});
