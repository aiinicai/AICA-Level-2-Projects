'use strict';
/* SQLite storage shared by the desktop app and the team server.
   Uses sql.js (SQLite compiled to WebAssembly) so no native build is needed. */
const fs = require('fs');
const path = require('path');
const initSqlJs = require('sql.js');

const SCHEMA = `
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, company TEXT, associate TEXT, data TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS lead_edits (lead_id INTEGER PRIMARY KEY, status TEXT, priority TEXT, owner TEXT, follow TEXT, details TEXT);
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER NOT NULL, date TEXT NOT NULL, text TEXT NOT NULL, seq INTEGER);
CREATE TABLE IF NOT EXISTS meetings (id INTEGER PRIMARY KEY, lead_id INTEGER, date TEXT, time TEXT, status TEXT, data TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS meeting_edits (key TEXT PRIMARY KEY, data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS investors (id TEXT PRIMARY KEY, name TEXT, company TEXT, data TEXT NOT NULL, created TEXT);
CREATE TABLE IF NOT EXISTS gcal_map (meeting_key TEXT PRIMARY KEY, event_id TEXT NOT NULL, synced_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT, summary TEXT);
CREATE INDEX IF NOT EXISTS notes_lead ON notes(lead_id);
`;

class ConflictError extends Error { constructor(version) { super('Version conflict'); this.code = 'CONFLICT'; this.version = version; } }

async function open(file) {
  const SQL = await initSqlJs({ locateFile: f => path.join(path.dirname(require.resolve('sql.js/dist/sql-wasm.js')), f) });
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const fresh = !fs.existsSync(file);
  const db = fresh ? new SQL.Database() : new SQL.Database(fs.readFileSync(file));
  db.exec(SCHEMA);

  const all = (sql, p = []) => { const st = db.prepare(sql); st.bind(p); const out = []; while (st.step()) out.push(st.getAsObject()); st.free(); return out; };
  const one = (sql, p = []) => all(sql, p)[0];
  const run = (sql, p = []) => { const st = db.prepare(sql); st.run(p); st.free(); };
  const getMeta = (k, d) => { const r = one('SELECT value FROM meta WHERE key=?', [k]); return r ? r.value : d; };
  const setMeta = (k, v) => run('INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', [k, String(v)]);

  function flush() {
    const tmp = file + '.tmp';
    fs.writeFileSync(tmp, Buffer.from(db.export()));
    fs.renameSync(tmp, file);
  }
  if (fresh) { setMeta('created', new Date().toISOString()); setMeta('version', 0); flush(); }

  function version() { return Number(getMeta('version', 0)); }

  function loadStore() {
    const store = { edits: {}, newItems: [], newMeetings: [], newInvestors: [], meetEdits: {},
      seq: Number(getMeta('seq', 100000)), mseq: Number(getMeta('mseq', 50000)) };
    for (const r of all('SELECT * FROM leads ORDER BY id')) store.newItems.push(JSON.parse(r.data));
    for (const r of all('SELECT * FROM lead_edits')) {
      const e = {};
      if (r.status) e.status = r.status; if (r.priority) e.priority = r.priority;
      if (r.owner) e.owner = r.owner; if (r.follow) e.follow = r.follow;
      if (r.details) e.details = JSON.parse(r.details);
      store.edits[r.lead_id] = e;
    }
    for (const r of all('SELECT lead_id,date,text FROM notes ORDER BY lead_id,seq,id')) {
      const e = store.edits[r.lead_id] = store.edits[r.lead_id] || {};
      (e.notes = e.notes || []).push({ d: r.date, t: r.text });
    }
    for (const r of all('SELECT data FROM meetings ORDER BY id')) store.newMeetings.push(JSON.parse(r.data));
    for (const r of all('SELECT key,data FROM meeting_edits')) store.meetEdits[r.key] = JSON.parse(r.data);
    for (const r of all('SELECT data FROM investors ORDER BY created,id')) store.newInvestors.push(JSON.parse(r.data));
    return { store, version: version(), fresh: version() === 0 };
  }

  function counts() {
    const c = t => one(`SELECT COUNT(*) n FROM ${t}`).n;
    return { leads: c('leads'), notes: c('notes'), meetings: c('meetings'), investors: c('investors'), edits: c('lead_edits'), meetEdits: c('meeting_edits') };
  }

  function saveStore(store, { baseVersion = null, actor = '' } = {}) {
    const cur = version();
    if (baseVersion !== null && baseVersion !== undefined && Number(baseVersion) !== cur) throw new ConflictError(cur);
    const before = counts();
    db.exec('BEGIN');
    try {
      for (const t of ['leads', 'lead_edits', 'notes', 'meetings', 'meeting_edits', 'investors']) db.exec(`DELETE FROM ${t}`);
      for (const n of store.newItems || []) run('INSERT INTO leads(id,company,associate,data,created) VALUES(?,?,?,?,?)', [n.id, n.company || '', n.associate || '', JSON.stringify(n), n.created || null]);
      for (const [id, e] of Object.entries(store.edits || {})) {
        const has = e.status || e.priority || e.owner || e.follow || e.details;
        if (has) run('INSERT INTO lead_edits(lead_id,status,priority,owner,follow,details) VALUES(?,?,?,?,?,?)', [Number(id), e.status || null, e.priority || null, e.owner || null, e.follow || null, e.details ? JSON.stringify(e.details) : null]);
        (e.notes || []).forEach((n, i) => run('INSERT INTO notes(lead_id,date,text,seq) VALUES(?,?,?,?)', [Number(id), n.d, n.t, i]));
      }
      for (const m of store.newMeetings || []) run('INSERT INTO meetings(id,lead_id,date,time,status,data,created) VALUES(?,?,?,?,?,?,?)', [m.i, m.leadId ?? null, m.date || null, m.time || null, m.status || null, JSON.stringify(m), m.created || null]);
      for (const [k, v] of Object.entries(store.meetEdits || {})) run('INSERT INTO meeting_edits(key,data) VALUES(?,?)', [k, JSON.stringify(v)]);
      for (const c of store.newInvestors || []) run('INSERT INTO investors(id,name,company,data,created) VALUES(?,?,?,?,?)', [String(c.id), c.name || '', c.company || '', JSON.stringify(c), c.created || null]);
      setMeta('seq', store.seq || 100000); setMeta('mseq', store.mseq || 50000);
      const v = cur + 1; setMeta('version', v); setMeta('updated', new Date().toISOString());
      const after = counts();
      const diff = Object.keys(after).map(k => after[k] !== before[k] ? `${k} ${before[k]} to ${after[k]}` : null).filter(Boolean);
      run('INSERT INTO audit(at,actor,summary) VALUES(?,?,?)', [new Date().toISOString(), actor || '', diff.length ? diff.join(', ') : 'Edited existing entries']);
      db.exec('COMMIT');
      flush();
      return { version: v };
    } catch (e) { db.exec('ROLLBACK'); throw e; }
  }

  function audit(limit = 200) { return all('SELECT at,actor,summary FROM audit ORDER BY id DESC LIMIT ?', [limit]); }
  function getSetting(k) { const r = one('SELECT value FROM settings WHERE key=?', [k]); return r ? r.value : null; }
  function setSetting(k, v) { if (v === null) run('DELETE FROM settings WHERE key=?', [k]); else run('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', [k, v]); flush(); }
  function gcalMap(key) { const r = one('SELECT event_id FROM gcal_map WHERE meeting_key=?', [key]); return r ? r.event_id : null; }
  function setGcalMap(key, id) { run('INSERT INTO gcal_map(meeting_key,event_id,synced_at) VALUES(?,?,?) ON CONFLICT(meeting_key) DO UPDATE SET event_id=excluded.event_id, synced_at=excluded.synced_at', [key, id, new Date().toISOString()]); }
  function gcalCount() { return one('SELECT COUNT(*) n FROM gcal_map').n; }
  function clearGcalMap() { db.exec('DELETE FROM gcal_map'); flush(); }

  function backup(dir, keep = 30) {
    fs.mkdirSync(dir, { recursive: true });
    const stamp = new Date().toISOString().replace(/[-:.]/g, '').slice(0, 15);
    const out = path.join(dir, `dealflow-tracker_${stamp}.sqlite`);
    fs.writeFileSync(out, Buffer.from(db.export()));
    const files = fs.readdirSync(dir).filter(f => f.startsWith('dealflow-tracker_') && f.endsWith('.sqlite')).sort();
    while (files.length > keep) fs.unlinkSync(path.join(dir, files.shift()));
    return out;
  }
  function lastBackupDay(dir) {
    if (!fs.existsSync(dir)) return null;
    const f = fs.readdirSync(dir).filter(f => f.endsWith('.sqlite')).sort().pop();
    return f ? f.slice(18, 26) : null;
  }

  return { file, loadStore, saveStore, version, audit, getSetting, setSetting, gcalMap, setGcalMap, gcalCount, clearGcalMap, backup, lastBackupDay, flush, close: () => db.close() };
}

async function openFromBackup(file, backupFile) {
  // validate the backup opens, then copy it over the live file
  const SQL = await initSqlJs({ locateFile: f => path.join(path.dirname(require.resolve('sql.js/dist/sql-wasm.js')), f) });
  const test = new SQL.Database(fs.readFileSync(backupFile));
  test.exec('SELECT COUNT(*) FROM leads'); test.close();
  fs.copyFileSync(backupFile, file);
  return open(file);
}

module.exports = { open, openFromBackup, ConflictError };
