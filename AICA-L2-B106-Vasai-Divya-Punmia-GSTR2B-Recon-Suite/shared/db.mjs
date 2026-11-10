/**
 * SQLite persistence layer for GSTR-2B Recon Suite.
 *
 * - Creates the database file (and its folder) automatically if missing.
 * - Uses Node's built-in `node:sqlite` driver when available (Node 22.13+),
 *   otherwise falls back to `sql.js` (pure WebAssembly SQLite, works on any Node).
 *   Both drivers read/write the SAME standard SQLite file on disk.
 *
 * Imported registers (GSTR-2B, books, CDN, RCM) are stored as one JSON document per
 * engagement and register; reconciliation results are recomputed in the browser, so
 * they are never stale. User decisions (blocked credits, remarks, supplier MSME/email
 * details, audit trail) are stored as ordinary rows.
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);

export const DATASET_KINDS = [
  'g2b', // GSTR-2B invoices (B2B + amendments)
  'g2b_cdn', // credit/debit notes found inside the GSTR-2B file
  'g2b_excl', // GSTR-2B rows excluded at import (missing GSTIN / invoice no.)
  'bks', // purchase register invoices
  'bks_cdn', // credit/debit notes found inside the purchase register
  'bks_excl', // purchase register rows excluded at import
  'cdn_g2b', // separately uploaded GSTR-2B credit/debit notes
  'cdn_bks', // separately uploaded books credit/debit notes
  'rcm', // separately uploaded reverse-charge bills
];

const SCHEMA = `
CREATE TABLE IF NOT EXISTS engagements (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL,
  gstin       TEXT    NOT NULL DEFAULT '',
  period      TEXT    NOT NULL DEFAULT '',
  tolerance   REAL    NOT NULL DEFAULT 100,
  created_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS datasets (
  engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
  kind          TEXT    NOT NULL,
  file_name     TEXT    NOT NULL DEFAULT '',
  row_count     INTEGER NOT NULL DEFAULT 0,
  rows_json     TEXT    NOT NULL DEFAULT '[]',
  imported_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  PRIMARY KEY (engagement_id, kind)
);

CREATE TABLE IF NOT EXISTS blocked_credits (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
  gstin         TEXT    NOT NULL,
  inv_key       TEXT    NOT NULL,
  inv           TEXT    NOT NULL,
  name          TEXT    NOT NULL DEFAULT '',
  inv_date      TEXT    NOT NULL DEFAULT '',
  taxable       REAL    NOT NULL DEFAULT 0,
  igst          REAL    NOT NULL DEFAULT 0,
  cgst          REAL    NOT NULL DEFAULT 0,
  sgst          REAL    NOT NULL DEFAULT 0,
  cat_id        TEXT    NOT NULL DEFAULT 'ot',
  cat_lbl       TEXT    NOT NULL DEFAULT '',
  sec           TEXT    NOT NULL DEFAULT '17(5)',
  reason        TEXT    NOT NULL DEFAULT '',
  origin        TEXT    NOT NULL DEFAULT 'manual',
  active        INTEGER NOT NULL DEFAULT 1,
  blocked_on    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE (engagement_id, gstin, inv_key)
);

CREATE TABLE IF NOT EXISTS remarks (
  engagement_id INTEGER NOT NULL REFERENCES engagements(id) ON DELETE CASCADE,
  row_key       TEXT    NOT NULL,
  text          TEXT    NOT NULL,
  updated_at    TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
  PRIMARY KEY (engagement_id, row_key)
);

CREATE TABLE IF NOT EXISTS suppliers (
  gstin         TEXT PRIMARY KEY,
  email         TEXT NOT NULL DEFAULT '',
  msme_status   TEXT NOT NULL DEFAULT 'unverified',
  udyam_number  TEXT NOT NULL DEFAULT '',
  notes         TEXT NOT NULL DEFAULT '',
  verified_at   TEXT NOT NULL DEFAULT '',
  updated_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  engagement_id INTEGER REFERENCES engagements(id) ON DELETE CASCADE,
  tag           TEXT NOT NULL DEFAULT 'SYS',
  message       TEXT NOT NULL,
  created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS app_settings (
  key    TEXT PRIMARY KEY,
  value  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_blocked_eng ON blocked_credits (engagement_id);
CREATE INDEX IF NOT EXISTS idx_logs_eng ON audit_logs (engagement_id, id);
`;

/* ----------------------------- Driver adapters ----------------------------- */

async function openNodeSqlite(file) {
  // Silence the one-time "SQLite is an experimental feature" warning on Node 22.
  const originalEmit = process.emitWarning;
  process.emitWarning = function (warning, ...args) {
    if (String(warning?.message ?? warning).includes('SQLite')) return;
    return originalEmit.call(process, warning, ...args);
  };
  const { DatabaseSync } = await import('node:sqlite');
  const db = new DatabaseSync(file);
  return {
    driver: 'node:sqlite (built-in)',
    exec: (sql) => db.exec(sql),
    run: (sql, params = []) => {
      const r = db.prepare(sql).run(...params);
      return { changes: Number(r.changes), lastInsertRowid: Number(r.lastInsertRowid) };
    },
    all: (sql, params = []) => db.prepare(sql).all(...params).map((r) => ({ ...r })),
    get: (sql, params = []) => {
      const r = db.prepare(sql).get(...params);
      return r ? { ...r } : undefined;
    },
    persist: () => {},
    close: () => db.close(),
  };
}

async function openSqlJs(file) {
  const { default: initSqlJs } = await import('sql.js');
  const wasmPath = require.resolve('sql.js/dist/sql-wasm.wasm');
  const SQL = await initSqlJs({ locateFile: () => wasmPath });
  const db = fs.existsSync(file) ? new SQL.Database(fs.readFileSync(file)) : new SQL.Database();

  const persist = () => {
    const tmp = `${file}.tmp`;
    fs.writeFileSync(tmp, Buffer.from(db.export()));
    fs.renameSync(tmp, file);
  };

  const all = (sql, params = []) => {
    const stmt = db.prepare(sql);
    try {
      stmt.bind(params);
      const rows = [];
      while (stmt.step()) rows.push(stmt.getAsObject());
      return rows;
    } finally {
      stmt.free();
    }
  };

  return {
    driver: 'sql.js (WebAssembly fallback)',
    exec: (sql) => db.exec(sql),
    run: (sql, params = []) => {
      db.run(sql, params);
      const changes = db.getRowsModified();
      const lastInsertRowid = Number(all('SELECT last_insert_rowid() AS id')[0]?.id ?? 0);
      return { changes, lastInsertRowid };
    },
    all,
    get: (sql, params = []) => all(sql, params)[0],
    persist,
    close: () => {
      persist();
      db.close();
    },
  };
}

/* ------------------------------ Public factory ----------------------------- */

const num = (v) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};
const str = (v, max = 500) => String(v ?? '').slice(0, max);

export async function openReconDatabase(dbFile) {
  const file = path.resolve(dbFile);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const isNew = !fs.existsSync(file);

  let conn;
  try {
    if (process.env.GSR_DB_DRIVER === 'sqljs') throw new Error('sql.js driver forced by GSR_DB_DRIVER');
    conn = await openNodeSqlite(file);
  } catch (err) {
    if (process.env.DEBUG_DB) console.warn('[db] node:sqlite unavailable, using sql.js:', err.message);
    conn = await openSqlJs(file);
  }

  conn.exec('PRAGMA busy_timeout = 5000;');
  conn.exec('PRAGMA foreign_keys = ON;');
  // Classic rollback journal keeps everything in ONE .db file (easy to copy, back up and inspect).
  conn.exec('PRAGMA journal_mode = DELETE;');
  conn.exec(SCHEMA);
  conn.persist();

  /** Runs fn inside a transaction; rolls back on error and persists on success. */
  const transaction = (fn) => {
    conn.exec('BEGIN');
    try {
      const result = fn();
      conn.exec('COMMIT');
      conn.persist();
      return result;
    } catch (err) {
      try {
        conn.exec('ROLLBACK');
      } catch {
        /* ignore */
      }
      throw err;
    }
  };

  /* ------------------------------ Engagements ------------------------------ */

  const ENG_COLS = `id, name, gstin, period, tolerance, created_at AS createdAt, updated_at AS updatedAt`;

  const listEngagements = () =>
    conn.all(`
      SELECT ${ENG_COLS},
             (SELECT COALESCE(SUM(row_count),0) FROM datasets d WHERE d.engagement_id = e.id AND d.kind = 'g2b') AS g2bCount,
             (SELECT COALESCE(SUM(row_count),0) FROM datasets d WHERE d.engagement_id = e.id AND d.kind = 'bks') AS bksCount
      FROM engagements e ORDER BY e.updated_at DESC, e.id DESC`);

  const getEngagement = (id) => conn.get(`SELECT ${ENG_COLS} FROM engagements WHERE id = ?`, [id]) ?? null;

  const createEngagement = ({ name, gstin, period, tolerance }) =>
    transaction(() => {
      const { lastInsertRowid } = conn.run(
        `INSERT INTO engagements (name, gstin, period, tolerance) VALUES (?, ?, ?, ?)`,
        [str(name, 200), str(gstin, 15).toUpperCase(), str(period, 60), tolerance == null ? 100 : num(tolerance)]
      );
      return lastInsertRowid;
    });

  const updateEngagement = (id, { name, gstin, period, tolerance }) =>
    transaction(() => {
      const cur = getEngagement(id);
      if (!cur) return false;
      conn.run(
        `UPDATE engagements SET name = ?, gstin = ?, period = ?, tolerance = ?, updated_at = datetime('now','localtime') WHERE id = ?`,
        [
          name == null ? cur.name : str(name, 200),
          gstin == null ? cur.gstin : str(gstin, 15).toUpperCase(),
          period == null ? cur.period : str(period, 60),
          tolerance == null ? cur.tolerance : Math.max(0, num(tolerance)),
          id,
        ]
      );
      return true;
    });

  const deleteEngagement = (id) =>
    transaction(() => {
      for (const t of ['datasets', 'blocked_credits', 'remarks', 'audit_logs']) {
        conn.run(`DELETE FROM ${t} WHERE engagement_id = ?`, [id]);
      }
      return conn.run('DELETE FROM engagements WHERE id = ?', [id]).changes > 0;
    });

  const touch = (id) => conn.run(`UPDATE engagements SET updated_at = datetime('now','localtime') WHERE id = ?`, [id]);

  /* -------------------------------- State ---------------------------------- */

  const BLOCK_COLS = `id, gstin, inv_key AS invKey, inv, name, inv_date AS date, taxable, igst, cgst, sgst,
    cat_id AS catId, cat_lbl AS catLbl, sec, reason, origin, active, blocked_on AS blockedOn`;

  const getState = (id) => {
    const engagement = getEngagement(id);
    if (!engagement) return null;
    const datasets = {};
    const datasetInfo = {};
    for (const k of DATASET_KINDS) datasets[k] = [];
    for (const r of conn.all(
      `SELECT kind, file_name AS fileName, row_count AS rowCount, rows_json AS rowsJson, imported_at AS importedAt
       FROM datasets WHERE engagement_id = ?`,
      [id]
    )) {
      try {
        datasets[r.kind] = JSON.parse(r.rowsJson);
      } catch {
        datasets[r.kind] = [];
      }
      datasetInfo[r.kind] = { fileName: r.fileName, rowCount: r.rowCount, importedAt: r.importedAt };
    }
    const blocked = conn
      .all(`SELECT ${BLOCK_COLS} FROM blocked_credits WHERE engagement_id = ? ORDER BY id DESC`, [id])
      .map((b) => ({ ...b, active: !!b.active }));
    const remarks = {};
    for (const r of conn.all(`SELECT row_key AS k, text FROM remarks WHERE engagement_id = ?`, [id])) remarks[r.k] = r.text;
    return { engagement, datasets, datasetInfo, blocked, remarks };
  };

  /** Replaces one or more registers of an engagement in a single transaction. */
  const replaceDatasets = (id, fileName, sets) =>
    transaction(() => {
      if (!getEngagement(id)) return false;
      for (const [kind, rows] of Object.entries(sets)) {
        if (!DATASET_KINDS.includes(kind)) throw new Error(`Unknown register type: ${kind}`);
        const list = Array.isArray(rows) ? rows : [];
        conn.run(
          `INSERT INTO datasets (engagement_id, kind, file_name, row_count, rows_json, imported_at)
           VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))
           ON CONFLICT(engagement_id, kind) DO UPDATE SET file_name = excluded.file_name, row_count = excluded.row_count,
             rows_json = excluded.rows_json, imported_at = excluded.imported_at`,
          [id, kind, str(fileName, 260), list.length, JSON.stringify(list)]
        );
      }
      touch(id);
      return true;
    });

  const clearDatasets = (id, kinds) =>
    transaction(() => {
      for (const k of kinds) conn.run(`DELETE FROM datasets WHERE engagement_id = ? AND kind = ?`, [id, k]);
      touch(id);
      return true;
    });

  /* ---------------------------- Blocked credits ---------------------------- */

  /**
   * Adds blocked-credit entries. Existing entries are kept as they are, except that a
   * manual block re-activates an entry the user had released. Auto-detected entries never
   * re-block an invoice the user released, so a re-import does not undo the user's decision.
   */
  const addBlocked = (id, items) =>
    transaction(() => {
      let added = 0;
      for (const b of items) {
        const gstin = str(b.gstin, 15).toUpperCase();
        const invKey = str(b.invKey, 120);
        if (!gstin || !invKey) continue;
        const existing = conn.get(`SELECT id, active FROM blocked_credits WHERE engagement_id = ? AND gstin = ? AND inv_key = ?`, [
          id,
          gstin,
          invKey,
        ]);
        const origin = b.origin === 'auto' ? 'auto' : 'manual';
        if (existing) {
          if (origin === 'manual') {
            conn.run(
              `UPDATE blocked_credits SET active = 1, cat_id = ?, cat_lbl = ?, sec = ?, reason = ?, origin = 'manual',
                 blocked_on = datetime('now','localtime') WHERE id = ?`,
              [str(b.catId, 10), str(b.catLbl, 200), str(b.sec, 30), str(b.reason, 300), existing.id]
            );
            if (!existing.active) added++;
          }
          continue;
        }
        conn.run(
          `INSERT INTO blocked_credits (engagement_id, gstin, inv_key, inv, name, inv_date, taxable, igst, cgst, sgst,
             cat_id, cat_lbl, sec, reason, origin)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            id,
            gstin,
            invKey,
            str(b.inv, 120),
            str(b.name, 200),
            str(b.date, 20),
            num(b.taxable),
            num(b.igst),
            num(b.cgst),
            num(b.sgst),
            str(b.catId, 10) || 'ot',
            str(b.catLbl, 200),
            str(b.sec, 30) || '17(5)',
            str(b.reason, 300),
            origin,
          ]
        );
        added++;
      }
      return added;
    });

  const setBlockedActive = (id, blockedId, active) =>
    transaction(
      () =>
        conn.run(`UPDATE blocked_credits SET active = ? WHERE engagement_id = ? AND id = ?`, [active ? 1 : 0, id, blockedId])
          .changes > 0
    );

  /* -------------------------------- Remarks -------------------------------- */

  const setRemark = (id, rowKey, text) =>
    transaction(() => {
      const t = str(text, 2000).trim();
      if (!t) {
        conn.run(`DELETE FROM remarks WHERE engagement_id = ? AND row_key = ?`, [id, str(rowKey, 200)]);
      } else {
        conn.run(
          `INSERT INTO remarks (engagement_id, row_key, text) VALUES (?, ?, ?)
           ON CONFLICT(engagement_id, row_key) DO UPDATE SET text = excluded.text, updated_at = datetime('now','localtime')`,
          [id, str(rowKey, 200), t]
        );
      }
      return true;
    });

  /* ------------------------------- Suppliers ------------------------------- */

  const SUP_COLS = `gstin, email, msme_status AS msmeStatus, udyam_number AS udyamNumber, notes, verified_at AS verifiedAt, updated_at AS updatedAt`;
  const MSME = ['unverified', 'unregistered', 'micro', 'small', 'medium'];

  const listSuppliers = () => conn.all(`SELECT ${SUP_COLS} FROM suppliers ORDER BY gstin`);

  const saveSupplier = (gstin, { email, msmeStatus, udyamNumber, notes }) =>
    transaction(() => {
      const g = str(gstin, 15).toUpperCase();
      const status = MSME.includes(msmeStatus) ? msmeStatus : 'unverified';
      conn.run(
        `INSERT INTO suppliers (gstin, email, msme_status, udyam_number, notes, verified_at)
         VALUES (?, ?, ?, ?, ?, CASE WHEN ? = 'unverified' THEN '' ELSE datetime('now','localtime') END)
         ON CONFLICT(gstin) DO UPDATE SET email = excluded.email, msme_status = excluded.msme_status,
           udyam_number = excluded.udyam_number, notes = excluded.notes,
           verified_at = CASE WHEN excluded.msme_status = 'unverified' THEN ''
                              WHEN suppliers.msme_status = excluded.msme_status AND suppliers.udyam_number = excluded.udyam_number
                                THEN suppliers.verified_at
                              ELSE datetime('now','localtime') END,
           updated_at = datetime('now','localtime')`,
        [g, str(email, 200).trim(), status, str(udyamNumber, 40).trim().toUpperCase(), str(notes, 1000).trim(), status]
      );
      return conn.get(`SELECT ${SUP_COLS} FROM suppliers WHERE gstin = ?`, [g]);
    });

  /* ------------------------------- Audit log -------------------------------- */

  const addLog = (id, tag, message) =>
    transaction(() => {
      conn.run(`INSERT INTO audit_logs (engagement_id, tag, message) VALUES (?, ?, ?)`, [
        id ?? null,
        str(tag, 20).toUpperCase() || 'SYS',
        str(message, 1000),
      ]);
      return true;
    });

  const listLogs = (id, limit = 500) =>
    conn.all(
      `SELECT id, tag, message, created_at AS createdAt FROM audit_logs
       WHERE engagement_id = ? OR engagement_id IS NULL ORDER BY id DESC LIMIT ?`,
      [id, limit]
    );

  /* ------------------------------- Settings -------------------------------- */

  const getSetting = (key) => conn.get('SELECT value FROM app_settings WHERE key = ?', [key])?.value ?? null;
  const setSetting = (key, value) =>
    transaction(() => {
      conn.run(
        `INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value`,
        [key, String(value)]
      );
      return true;
    });

  return {
    file,
    isNew,
    driver: conn.driver,
    listEngagements,
    getEngagement,
    createEngagement,
    updateEngagement,
    deleteEngagement,
    getState,
    replaceDatasets,
    clearDatasets,
    addBlocked,
    setBlockedActive,
    setRemark,
    listSuppliers,
    saveSupplier,
    addLog,
    listLogs,
    getSetting,
    setSetting,
    /** Writes a consistent copy of the database to `dest` (used for the Backup download). */
    backupTo: (dest) => {
      conn.persist();
      // sql.js keeps the database in memory and persist() has just written it to disk.
      if (conn.driver.startsWith('sql.js')) return fs.copyFileSync(file, dest);
      conn.exec(`VACUUM INTO '${dest.replace(/'/g, "''")}'`);
    },
    close: () => conn.close(),
  };
}
