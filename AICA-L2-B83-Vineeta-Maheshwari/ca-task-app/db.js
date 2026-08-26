// db.js — SQLite setup using Node's built-in node:sqlite module (no external deps needed).
'use strict';

const path = require('node:path');
const fs = require('node:fs');
const crypto = require('node:crypto');
const { DatabaseSync } = require('node:sqlite');

// When this is running inside the packaged Electron desktop app (in "host"
// mode), store the database in the OS's per-app data folder instead of next
// to the program files, since installed programs usually can't write next
// to themselves. Plain `node server.js` usage (no Electron) is unaffected
// and keeps using the local `data/` folder as before.
let dbDir = null;
try {
  const electron = require('electron');
  if (electron && electron.app && typeof electron.app.getPath === 'function') {
    dbDir = path.join(electron.app.getPath('userData'), 'data');
  }
} catch (e) {
  // 'electron' isn't installed / this isn't running inside Electron — fine.
}
if (!dbDir) dbDir = path.join(__dirname, 'data');
fs.mkdirSync(dbDir, { recursive: true });

const DB_PATH = path.join(dbDir, 'app.db');
const db = new DatabaseSync(DB_PATH);

db.exec('PRAGMA foreign_keys = ON;');

db.exec(`
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  password_salt TEXT NOT NULL,
  role TEXT NOT NULL CHECK(role IN ('admin','member')),
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
`);

db.exec(`
CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client_name TEXT NOT NULL,
  task_type TEXT NOT NULL,
  due_date TEXT,
  priority TEXT NOT NULL CHECK(priority IN ('Low','Medium','High','Urgent')) DEFAULT 'Medium',
  status TEXT NOT NULL CHECK(status IN ('Pending','In Progress','Completed')) DEFAULT 'Pending',
  assigned_by INTEGER NOT NULL REFERENCES users(id),
  notes TEXT,
  assigned_date TEXT NOT NULL DEFAULT (date('now')),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  completed_at TEXT
);
`);

// --- One-time migration: older versions of this app stored a single
// `assigned_to` column directly on `tasks`. If we find that column, move
// the data into a proper many-to-many table (task_assignees) so a task can
// have several people assigned, without losing any existing tasks.
const taskColumns = db.prepare(`PRAGMA table_info(tasks)`).all().map((c) => c.name);
if (taskColumns.includes('assigned_to')) {
  console.log('Upgrading database: moving single task assignees into multi-assignee format...');
  db.exec('BEGIN TRANSACTION');
  try {
    db.exec(`
      CREATE TABLE tasks_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT NOT NULL,
        task_type TEXT NOT NULL,
        due_date TEXT,
        priority TEXT NOT NULL CHECK(priority IN ('Low','Medium','High','Urgent')) DEFAULT 'Medium',
        status TEXT NOT NULL CHECK(status IN ('Pending','In Progress','Completed')) DEFAULT 'Pending',
        assigned_by INTEGER NOT NULL REFERENCES users(id),
        notes TEXT,
        assigned_date TEXT NOT NULL DEFAULT (date('now')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT
      );
    `);
    db.exec(`
      INSERT INTO tasks_new (id, client_name, task_type, due_date, priority, status, assigned_by, notes, assigned_date, created_at, updated_at, completed_at)
      SELECT id, client_name, task_type, due_date, priority, status, assigned_by, notes, date(created_at), created_at, updated_at, completed_at
      FROM tasks;
    `);
    db.exec('CREATE TEMP TABLE old_assignees AS SELECT id AS task_id, assigned_to AS user_id FROM tasks;');
    db.exec('DROP TABLE tasks;');
    db.exec('ALTER TABLE tasks_new RENAME TO tasks;');
    db.exec(`
      CREATE TABLE IF NOT EXISTS task_assignees (
        task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id),
        PRIMARY KEY (task_id, user_id)
      );
    `);
    db.exec('INSERT INTO task_assignees (task_id, user_id) SELECT task_id, user_id FROM old_assignees;');
    db.exec('DROP TABLE old_assignees;');
    db.exec('COMMIT');
    console.log('Database upgrade complete — existing tasks kept their original assignee.');
  } catch (err) {
    db.exec('ROLLBACK');
    throw err;
  }
}

db.exec(`
CREATE TABLE IF NOT EXISTS task_assignees (
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id),
  PRIMARY KEY (task_id, user_id)
);
`);

db.exec(`
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  expires_at INTEGER NOT NULL
);
`);

function hashPassword(password, salt) {
  salt = salt || crypto.randomBytes(16).toString('hex');
  const hash = crypto.scryptSync(password, salt, 64).toString('hex');
  return { hash, salt };
}

function verifyPassword(password, salt, hash) {
  const check = crypto.scryptSync(password, salt, 64).toString('hex');
  return crypto.timingSafeEqual(Buffer.from(check, 'hex'), Buffer.from(hash, 'hex'));
}

// Seed a default admin account on first run.
const adminCount = db.prepare(`SELECT COUNT(*) AS c FROM users WHERE role = 'admin'`).get().c;
if (adminCount === 0) {
  const { hash, salt } = hashPassword('admin123');
  db.prepare(`
    INSERT INTO users (name, username, password_hash, password_salt, role)
    VALUES (?, ?, ?, ?, 'admin')
  `).run('Admin / Partner', 'admin', hash, salt);
  console.log('Seeded default admin account -> username: admin / password: admin123 (please change after first login)');
}

module.exports = { db, hashPassword, verifyPassword };
