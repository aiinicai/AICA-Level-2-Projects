/**
 * Local SQLite database (sql.js / WebAssembly).
 * Data never leaves the machine: the database file is persisted to IndexedDB in
 * the browser and to a local file on disk when running inside Electron.
 */
import type { Database, SqlJsStatic } from "sql.js";

const IDB_NAME = "gst-recon-db";
const IDB_STORE = "files";
const IDB_KEY = "main.sqlite";

let SQL: SqlJsStatic | null = null;
let db: Database | null = null;
let ready: Promise<Database> | null = null;

const SCHEMA = `
CREATE TABLE IF NOT EXISTS clients (
  id TEXT PRIMARY KEY, name TEXT, gstin TEXT, fy TEXT, state TEXT, reg_type TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS imports (
  id TEXT PRIMARY KEY, client_id TEXT, source TEXT, filename TEXT, row_count INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS txns (
  id TEXT PRIMARY KEY, client_id TEXT, source TEXT, import_id TEXT,
  invoice_no TEXT, invoice_date TEXT, party_name TEXT, party_gstin TEXT,
  taxable_value REAL, gst_rate REAL, cgst REAL, sgst REAL, igst REAL, cess REAL,
  place_of_supply TEXT, voucher_type TEXT, reverse_charge INTEGER,
  doc_type TEXT, original_invoice_no TEXT, supply_type TEXT, hsn TEXT
);
CREATE TABLE IF NOT EXISTS mappings (
  client_id TEXT, source TEXT, map_json TEXT, PRIMARY KEY (client_id, source)
);
CREATE TABLE IF NOT EXISTS recon_items (
  id TEXT PRIMARY KEY, client_id TEXT, section TEXT, key_label TEXT, party TEXT,
  status TEXT, books_taxable REAL, books_tax REAL, gst_taxable REAL, gst_tax REAL,
  remarks TEXT, adjustment REAL, proposed_treatment TEXT, resolved INTEGER
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id TEXT PRIMARY KEY, client_id TEXT, ts TEXT, action TEXT, detail TEXT
);
`;

function idb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_NAME, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(IDB_STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

async function idbGet(): Promise<Uint8Array | null> {
  const d = await idb();
  return new Promise((resolve) => {
    const tx = d.transaction(IDB_STORE, "readonly").objectStore(IDB_STORE).get(IDB_KEY);
    tx.onsuccess = () => resolve((tx.result as Uint8Array) ?? null);
    tx.onerror = () => resolve(null);
  });
}

async function idbPut(bytes: Uint8Array) {
  const d = await idb();
  await new Promise<void>((resolve) => {
    const tx = d.transaction(IDB_STORE, "readwrite").objectStore(IDB_STORE).put(bytes, IDB_KEY);
    tx.onsuccess = () => resolve();
    tx.onerror = () => resolve();
  });
}

interface DesktopBridge {
  loadDb: () => Promise<Uint8Array | null>;
  saveDb: (bytes: Uint8Array) => Promise<void>;
}
function bridge(): DesktopBridge | null {
  return (globalThis as unknown as { gstDesktop?: DesktopBridge }).gstDesktop ?? null;
}

export async function getDb(): Promise<Database> {
  if (db) return db;
  if (ready) return ready;
  ready = (async () => {
    const initSqlJs = (await import("sql.js")).default;
    SQL = await initSqlJs({ locateFile: () => "/sql-wasm.wasm" });
    const existing = (await bridge()?.loadDb()) ?? (await idbGet());
    db = existing ? new SQL.Database(existing) : new SQL.Database();
    db.run(SCHEMA);
    return db;
  })();
  return ready;
}

let saveTimer: ReturnType<typeof setTimeout> | null = null;
export async function persist() {
  const d = await getDb();
  const bytes = d.export();
  await idbPut(bytes);
  await bridge()?.saveDb(bytes);
}
export function schedulePersist() {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => void persist(), 150);
}

export async function run(sql: string, params: unknown[] = []) {
  const d = await getDb();
  d.run(sql, params as never);
  schedulePersist();
}

export async function all<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T[]> {
  const d = await getDb();
  const stmt = d.prepare(sql);
  stmt.bind(params as never);
  const out: T[] = [];
  while (stmt.step()) out.push(stmt.getAsObject() as T);
  stmt.free();
  return out;
}

export async function one<T = Record<string, unknown>>(sql: string, params: unknown[] = []): Promise<T | null> {
  const rows = await all<T>(sql, params);
  return rows[0] ?? null;
}

export function uid() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export async function logAudit(clientId: string, action: string, detail: string) {
  await run("INSERT INTO audit (id, client_id, ts, action, detail) VALUES (?,?,?,?,?)", [
    uid(),
    clientId,
    new Date().toISOString(),
    action,
    detail,
  ]);
}

export async function exportBackup(): Promise<Blob> {
  const d = await getDb();
  return new Blob([d.export() as unknown as BlobPart], { type: "application/octet-stream" });
}

export async function restoreBackup(bytes: Uint8Array) {
  const initSqlJs = (await import("sql.js")).default;
  SQL = SQL ?? (await initSqlJs({ locateFile: () => "/sql-wasm.wasm" }));
  db = new SQL.Database(bytes);
  db.run(SCHEMA);
  ready = Promise.resolve(db);
  await persist();
}

/* ---------- settings ---------- */
export interface AppSettings {
  taxRates: number[];
  valueTolerance: number;
  taxTolerance: number;
  firmName: string;
  gstr9Tables: { table: string; description: string; sourceHint: string }[];
}

export const DEFAULT_SETTINGS: AppSettings = {
  taxRates: [0, 0.1, 0.25, 1, 1.5, 3, 5, 6, 7.5, 12, 18, 28],
  valueTolerance: 1,
  taxTolerance: 1,
  firmName: "Chartered Accountants",
  gstr9Tables: [
    { table: "4A", description: "Supplies to unregistered persons (B2C)", sourceHint: "B2C" },
    { table: "4B", description: "Supplies to registered persons (B2B)", sourceHint: "B2B" },
    { table: "4C", description: "Zero rated supply (Export) on payment of tax", sourceHint: "Export" },
    { table: "4D", description: "Supply to SEZ on payment of tax", sourceHint: "SEZ" },
    { table: "4I", description: "Credit notes issued", sourceHint: "Credit Note" },
    { table: "4J", description: "Debit notes issued", sourceHint: "Debit Note" },
    { table: "5D", description: "Exempted supplies", sourceHint: "Exempt" },
    { table: "5E", description: "Nil rated supplies", sourceHint: "Nil" },
    { table: "5F", description: "Non-GST supply", sourceHint: "Non-GST" },
    { table: "6A", description: "Total ITC availed in GSTR-3B", sourceHint: "ITC" },
    { table: "8A", description: "ITC as per GSTR-2B", sourceHint: "ITC 2B" },
  ],
};

export async function getSettings(): Promise<AppSettings> {
  const row = await one<{ value: string }>("SELECT value FROM settings WHERE key='app'");
  if (!row) return DEFAULT_SETTINGS;
  try {
    return { ...DEFAULT_SETTINGS, ...(JSON.parse(row.value) as Partial<AppSettings>) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export async function saveSettings(s: AppSettings) {
  await run("INSERT INTO settings (key,value) VALUES ('app',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [
    JSON.stringify(s),
  ]);
}
