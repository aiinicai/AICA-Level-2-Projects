// server.js — Zero-dependency Node.js backend for the CA Task Delegation App.
// Uses only Node's built-in modules (http, node:sqlite, node:crypto) so it runs
// anywhere with `node server.js` — no npm install required.
'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { URL } = require('node:url');
const { db, hashPassword, verifyPassword } = require('./db');

const PORT = Number(process.env.PORT) || 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');
const SESSION_TTL_MS = 12 * 60 * 60 * 1000; // 12 hours

// ---------- Session helpers ----------
function createSession(userId) {
  const token = crypto.randomBytes(32).toString('hex');
  const expiresAt = Date.now() + SESSION_TTL_MS;
  db.prepare('INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)').run(token, userId, expiresAt);
  return token;
}

function getSessionUser(req) {
  const cookies = parseCookies(req);
  const token = cookies.session;
  if (!token) return null;
  const row = db.prepare('SELECT * FROM sessions WHERE token = ?').get(token);
  if (!row) return null;
  if (row.expires_at < Date.now()) {
    db.prepare('DELETE FROM sessions WHERE token = ?').run(token);
    return null;
  }
  const user = db.prepare('SELECT id, name, username, role, active FROM users WHERE id = ?').get(row.user_id);
  if (!user || !user.active) return null;
  return user;
}

function destroySession(req) {
  const cookies = parseCookies(req);
  if (cookies.session) db.prepare('DELETE FROM sessions WHERE token = ?').run(cookies.session);
}

function parseCookies(req) {
  const header = req.headers.cookie;
  const out = {};
  if (!header) return out;
  header.split(';').forEach((pair) => {
    const idx = pair.indexOf('=');
    if (idx === -1) return;
    const k = pair.slice(0, idx).trim();
    const v = pair.slice(idx + 1).trim();
    out[k] = decodeURIComponent(v);
  });
  return out;
}

// ---------- Response helpers ----------
function sendJSON(res, status, data, extraHeaders) {
  const body = JSON.stringify(data);
  res.writeHead(status, Object.assign({
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
  }, extraHeaders || {}));
  res.end(body);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let chunks = [];
    let size = 0;
    req.on('data', (c) => {
      size += c.length;
      if (size > 2 * 1024 * 1024) { reject(new Error('Body too large')); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8');
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch (e) { reject(e); }
    });
    req.on('error', reject);
  });
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

function serveStatic(req, res, pathname) {
  let filePath = path.join(PUBLIC_DIR, pathname === '/' ? '/login.html' : pathname);
  if (!filePath.startsWith(PUBLIC_DIR)) { res.writeHead(403); res.end('Forbidden'); return; }
  fs.readFile(filePath, (err, content) => {
    if (err) {
      if (err.code === 'ENOENT') { res.writeHead(404); res.end('Not found'); return; }
      res.writeHead(500); res.end('Server error'); return;
    }
    const ext = path.extname(filePath);
    res.writeHead(200, { 'Content-Type': MIME[ext] || 'application/octet-stream' });
    res.end(content);
  });
}

// ---------- App logic helpers ----------
function publicUser(u) {
  if (!u) return null;
  return { id: u.id, name: u.name, username: u.username, role: u.role, active: !!u.active };
}

function listUsers() {
  return db.prepare('SELECT id, name, username, role, active, created_at FROM users ORDER BY role DESC, name ASC').all();
}

function getAssignees(taskId) {
  return db.prepare(`
    SELECT u.id, u.name FROM task_assignees ta
    JOIN users u ON u.id = ta.user_id
    WHERE ta.task_id = ?
    ORDER BY u.name ASC
  `).all(taskId);
}

function setAssignees(taskId, userIds) {
  db.prepare('DELETE FROM task_assignees WHERE task_id = ?').run(taskId);
  const insert = db.prepare('INSERT OR IGNORE INTO task_assignees (task_id, user_id) VALUES (?, ?)');
  const uniqueIds = [...new Set(userIds.map(Number))];
  for (const uid of uniqueIds) insert.run(taskId, uid);
}

function isAssignee(taskId, userId) {
  const row = db.prepare('SELECT 1 FROM task_assignees WHERE task_id = ? AND user_id = ?').get(taskId, userId);
  return !!row;
}

function taskWithNames(t) {
  const assignedBy = db.prepare('SELECT id, name FROM users WHERE id = ?').get(t.assigned_by);
  const assignees = getAssignees(t.id);
  return Object.assign({}, t, {
    assignees,
    assignee_names: assignees.map((a) => a.name).join(', '),
    assigned_by_name: assignedBy ? assignedBy.name : 'Unknown',
  });
}

// ---------- Routes ----------
const routes = [];
function route(method, pattern, handler) { routes.push({ method, pattern, handler }); }

function matchRoute(method, pathname) {
  for (const r of routes) {
    if (r.method !== method) continue;
    const parts = r.pattern.split('/').filter(Boolean);
    const actual = pathname.split('/').filter(Boolean);
    if (parts.length !== actual.length) continue;
    const params = {};
    let ok = true;
    for (let i = 0; i < parts.length; i++) {
      if (parts[i].startsWith(':')) params[parts[i].slice(1)] = actual[i];
      else if (parts[i] !== actual[i]) { ok = false; break; }
    }
    if (ok) return { handler: r.handler, params };
  }
  return null;
}

// --- Auth ---
route('POST', '/api/login', async (req, res) => {
  const body = await readBody(req).catch(() => ({}));
  const { username, password } = body;
  if (!username || !password) return sendJSON(res, 400, { error: 'Username and password are required.' });
  const user = db.prepare('SELECT * FROM users WHERE username = ?').get(String(username).trim().toLowerCase());
  if (!user || !user.active || !verifyPassword(password, user.password_salt, user.password_hash)) {
    return sendJSON(res, 401, { error: 'Invalid username or password.' });
  }
  const token = createSession(user.id);
  sendJSON(res, 200, { user: publicUser(user) }, {
    'Set-Cookie': `session=${token}; HttpOnly; Path=/; Max-Age=${SESSION_TTL_MS / 1000}; SameSite=Lax`,
  });
});

route('POST', '/api/logout', async (req, res) => {
  destroySession(req);
  sendJSON(res, 200, { ok: true }, { 'Set-Cookie': 'session=; HttpOnly; Path=/; Max-Age=0' });
});

route('GET', '/api/session', async (req, res) => {
  const user = getSessionUser(req);
  sendJSON(res, 200, { user: publicUser(user) });
});

// --- Users (admin manages team members; any logged-in user can view names for assignment) ---
route('GET', '/api/users', async (req, res) => {
  const user = getSessionUser(req);
  if (!user) return sendJSON(res, 401, { error: 'Not logged in.' });
  sendJSON(res, 200, { users: listUsers() });
});

route('POST', '/api/users', async (req, res) => {
  const user = getSessionUser(req);
  if (!user || user.role !== 'admin') return sendJSON(res, 403, { error: 'Only admin/partner can create users.' });
  const body = await readBody(req).catch(() => ({}));
  const { name, username, password, role } = body;
  if (!name || !username || !password || !role) return sendJSON(res, 400, { error: 'All fields are required.' });
  if (!['admin', 'member'].includes(role)) return sendJSON(res, 400, { error: 'Invalid role.' });
  const uname = String(username).trim().toLowerCase();
  const existing = db.prepare('SELECT id FROM users WHERE username = ?').get(uname);
  if (existing) return sendJSON(res, 409, { error: 'Username already exists.' });
  const { hash, salt } = hashPassword(password);
  const info = db.prepare(`
    INSERT INTO users (name, username, password_hash, password_salt, role) VALUES (?, ?, ?, ?, ?)
  `).run(name.trim(), uname, hash, salt, role);
  sendJSON(res, 201, { user: publicUser(db.prepare('SELECT * FROM users WHERE id = ?').get(Number(info.lastInsertRowid))) });
});

route('PUT', '/api/users/:id', async (req, res, params) => {
  const user = getSessionUser(req);
  if (!user || user.role !== 'admin') return sendJSON(res, 403, { error: 'Only admin/partner can edit users.' });
  const id = Number(params.id);
  const target = db.prepare('SELECT * FROM users WHERE id = ?').get(id);
  if (!target) return sendJSON(res, 404, { error: 'User not found.' });
  const body = await readBody(req).catch(() => ({}));
  const name = body.name !== undefined ? body.name.trim() : target.name;
  const active = body.active !== undefined ? (body.active ? 1 : 0) : target.active;
  const roleVal = body.role !== undefined ? body.role : target.role;
  let hash = target.password_hash, salt = target.password_salt;
  if (body.password) { const hp = hashPassword(body.password); hash = hp.hash; salt = hp.salt; }
  db.prepare('UPDATE users SET name = ?, active = ?, role = ?, password_hash = ?, password_salt = ? WHERE id = ?')
    .run(name, active, roleVal, hash, salt, id);
  sendJSON(res, 200, { user: publicUser(db.prepare('SELECT * FROM users WHERE id = ?').get(id)) });
});

// --- Tasks ---
route('GET', '/api/tasks', async (req, res) => {
  const user = getSessionUser(req);
  if (!user) return sendJSON(res, 401, { error: 'Not logged in.' });
  const rows = db.prepare('SELECT * FROM tasks ORDER BY CASE priority WHEN \'Urgent\' THEN 0 WHEN \'High\' THEN 1 WHEN \'Medium\' THEN 2 ELSE 3 END, due_date IS NULL, due_date ASC').all();
  sendJSON(res, 200, { tasks: rows.map(taskWithNames) });
});

route('POST', '/api/tasks', async (req, res) => {
  const user = getSessionUser(req);
  if (!user) return sendJSON(res, 401, { error: 'Not logged in.' });
  const body = await readBody(req).catch(() => ({}));
  const { client_name, task_type, due_date, priority, notes } = body;
  // Accept either assigned_to as an array (multi-assignee) or a single value, for compatibility.
  let assigneeIds = Array.isArray(body.assigned_to) ? body.assigned_to : (body.assigned_to ? [body.assigned_to] : []);
  assigneeIds = assigneeIds.map(Number).filter((n) => Number.isInteger(n) && n > 0);

  if (!client_name || !task_type || assigneeIds.length === 0) {
    return sendJSON(res, 400, { error: 'Client name, task type, and at least one assignee are required.' });
  }
  const placeholders = assigneeIds.map(() => '?').join(',');
  const validCount = db.prepare(`SELECT COUNT(*) AS c FROM users WHERE active = 1 AND id IN (${placeholders})`).get(...assigneeIds).c;
  if (validCount !== assigneeIds.length) return sendJSON(res, 400, { error: 'One or more assigned team members were not found.' });

  const prio = ['Low', 'Medium', 'High', 'Urgent'].includes(priority) ? priority : 'Medium';
  const assignedDate = body.assigned_date || new Date().toISOString().slice(0, 10);
  const info = db.prepare(`
    INSERT INTO tasks (client_name, task_type, due_date, priority, status, assigned_by, notes, assigned_date)
    VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?)
  `).run(client_name.trim(), task_type.trim(), due_date || null, prio, user.id, (notes || '').trim(), assignedDate);
  const taskId = Number(info.lastInsertRowid);
  setAssignees(taskId, assigneeIds);
  const row = db.prepare('SELECT * FROM tasks WHERE id = ?').get(taskId);
  sendJSON(res, 201, { task: taskWithNames(row) });
});

route('PUT', '/api/tasks/:id', async (req, res, params) => {
  const user = getSessionUser(req);
  if (!user) return sendJSON(res, 401, { error: 'Not logged in.' });
  const id = Number(params.id);
  const task = db.prepare('SELECT * FROM tasks WHERE id = ?').get(id);
  if (!task) return sendJSON(res, 404, { error: 'Task not found.' });

  const canManage = user.role === 'admin' || task.assigned_by === user.id || isAssignee(id, user.id);
  if (!canManage) return sendJSON(res, 403, { error: 'You cannot edit this task.' });

  const body = await readBody(req).catch(() => ({}));
  const fields = {
    client_name: body.client_name !== undefined ? body.client_name.trim() : task.client_name,
    task_type: body.task_type !== undefined ? body.task_type.trim() : task.task_type,
    due_date: body.due_date !== undefined ? body.due_date : task.due_date,
    priority: body.priority !== undefined && ['Low', 'Medium', 'High', 'Urgent'].includes(body.priority) ? body.priority : task.priority,
    status: body.status !== undefined && ['Pending', 'In Progress', 'Completed'].includes(body.status) ? body.status : task.status,
    notes: body.notes !== undefined ? body.notes : task.notes,
    assigned_date: body.assigned_date !== undefined ? body.assigned_date : task.assigned_date,
  };
  const completedAt = fields.status === 'Completed'
    ? (task.completed_at || new Date().toISOString())
    : null;

  db.prepare(`
    UPDATE tasks SET client_name=?, task_type=?, due_date=?, priority=?, status=?, notes=?, assigned_date=?, updated_at=datetime('now'), completed_at=?
    WHERE id=?
  `).run(fields.client_name, fields.task_type, fields.due_date, fields.priority, fields.status, fields.notes, fields.assigned_date, completedAt, id);

  // Only admin, or the person who originally assigned the task, may change who it's assigned to.
  let assigneeIds = Array.isArray(body.assigned_to) ? body.assigned_to : (body.assigned_to !== undefined ? [body.assigned_to] : null);
  if (assigneeIds !== null) {
    if (user.role !== 'admin' && task.assigned_by !== user.id) {
      return sendJSON(res, 403, { error: 'Only the admin or the person who assigned this task can change its assignees.' });
    }
    assigneeIds = assigneeIds.map(Number).filter((n) => Number.isInteger(n) && n > 0);
    if (assigneeIds.length === 0) return sendJSON(res, 400, { error: 'A task must have at least one assignee.' });
    const placeholders = assigneeIds.map(() => '?').join(',');
    const validCount = db.prepare(`SELECT COUNT(*) AS c FROM users WHERE active = 1 AND id IN (${placeholders})`).get(...assigneeIds).c;
    if (validCount !== assigneeIds.length) return sendJSON(res, 400, { error: 'One or more assigned team members were not found.' });
    setAssignees(id, assigneeIds);
  }

  const row = db.prepare('SELECT * FROM tasks WHERE id = ?').get(id);
  sendJSON(res, 200, { task: taskWithNames(row) });
});

route('DELETE', '/api/tasks/:id', async (req, res, params) => {
  const user = getSessionUser(req);
  if (!user || user.role !== 'admin') return sendJSON(res, 403, { error: 'Only admin/partner can delete tasks.' });
  const id = Number(params.id);
  db.prepare('DELETE FROM tasks WHERE id = ?').run(id);
  sendJSON(res, 200, { ok: true });
});

route('GET', '/api/dashboard/stats', async (req, res) => {
  const user = getSessionUser(req);
  if (!user) return sendJSON(res, 401, { error: 'Not logged in.' });

  // ?mine=1 scopes every figure to tasks the current user is assigned to —
  // used for the personal dashboard team members see. Without it, stats are
  // firm-wide (what the admin/partner sees, and unchanged from before).
  const parsedUrl = new URL(req.url, 'http://internal');
  const mineOnly = parsedUrl.searchParams.get('mine') === '1';
  const mineJoin = mineOnly ? 'JOIN task_assignees ta_scope ON ta_scope.task_id = t.id AND ta_scope.user_id = ?' : '';
  const mineParams = mineOnly ? [user.id] : [];

  const byStatus = db.prepare(`
    SELECT t.status AS status, COUNT(*) AS count FROM tasks t ${mineJoin} GROUP BY t.status
  `).all(...mineParams);
  const byPriority = db.prepare(`
    SELECT t.priority AS priority, COUNT(*) AS count FROM tasks t ${mineJoin} GROUP BY t.priority
  `).all(...mineParams);
  const overdue = db.prepare(`
    SELECT COUNT(*) AS c FROM tasks t ${mineJoin}
    WHERE t.status != 'Completed' AND t.due_date IS NOT NULL AND t.due_date < date('now')
  `).get(...mineParams).c;
  const total = db.prepare(`SELECT COUNT(*) AS c FROM tasks t ${mineJoin}`).get(...mineParams).c;

  // The cross-team workload chart only makes sense firm-wide — omit it
  // entirely from the personal (mine=1) response rather than send a
  // one-row version of it.
  let byMember = [];
  if (!mineOnly) {
    byMember = db.prepare(`
      SELECT u.id, u.name,
        SUM(CASE WHEN t.status = 'Pending' THEN 1 ELSE 0 END) AS pending,
        SUM(CASE WHEN t.status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
        SUM(CASE WHEN t.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
        COUNT(t.id) AS total
      FROM users u
      LEFT JOIN task_assignees ta ON ta.user_id = u.id
      LEFT JOIN tasks t ON t.id = ta.task_id
      WHERE u.active = 1
      GROUP BY u.id, u.name
      ORDER BY u.name ASC
    `).all();
  }

  sendJSON(res, 200, { byStatus, byPriority, byMember, overdue, total, mineOnly });
});

// ---------- Server ----------
const server = http.createServer(async (req, res) => {
  const parsed = new URL(req.url, `http://${req.headers.host}`);
  const pathname = parsed.pathname;

  if (pathname.startsWith('/api/')) {
    const match = matchRoute(req.method, pathname);
    if (!match) return sendJSON(res, 404, { error: 'Not found.' });
    try {
      await match.handler(req, res, match.params);
    } catch (err) {
      console.error(err);
      sendJSON(res, 500, { error: 'Server error.' });
    }
    return;
  }

  serveStatic(req, res, pathname);
});

// Starts listening, trying a few ports upward if the preferred one is busy
// (e.g. a previous copy is still running). Resolves with the port actually
// used. Used both by the CLI entry point below and by the Electron desktop
// app (main.js), which embeds this same server in "host" mode.
function startServer(preferredPort, attemptsLeft) {
  preferredPort = Number(preferredPort) || 3000;
  attemptsLeft = attemptsLeft === undefined ? 10 : attemptsLeft;
  return new Promise((resolve, reject) => {
    const onError = (err) => {
      server.removeListener('listening', onListening);
      if (err.code === 'EADDRINUSE' && attemptsLeft > 0) {
        resolve(startServer(preferredPort + 1, attemptsLeft - 1));
      } else {
        reject(err);
      }
    };
    const onListening = () => {
      server.removeListener('error', onError);
      resolve(preferredPort);
    };
    server.once('error', onError);
    server.once('listening', onListening);
    server.listen(preferredPort);
  });
}

if (require.main === module) {
  startServer(PORT).then((port) => {
    console.log(`\nCA Task Delegation App running at: http://localhost:${port}`);
    console.log('Default admin login -> username: admin / password: admin123\n');
  }).catch((err) => {
    console.error('Failed to start server:', err);
    process.exit(1);
  });
}

module.exports = { startServer, server };
