import { DatabaseSync } from 'node:sqlite';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { createSeedDataset } from '../data/seedDataset';
import type {
  AccountingPolicyConfig,
  AuditLogEntry,
  BackupMetadata,
  GlMappingRule,
  LicenseState,
  ManagementAdjustment,
  MisDataset,
  PeriodWorkflowState,
  TrialBalanceRow,
  UserRole,
} from '../types/mis';

const DATA_DIR = path.resolve(process.cwd(), 'data');
const BACKUP_DIR = path.resolve(DATA_DIR, 'backups');
const DB_PATH = path.resolve(DATA_DIR, 'realestate360.db');

export interface UserAccountRow {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  companyScope: string; // 'ALL' or companyId
  passwordHash: string;
  active: boolean;
}

export class MisDatabase {
  private db: DatabaseSync;

  constructor() {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    fs.mkdirSync(BACKUP_DIR, { recursive: true });
    this.db = new DatabaseSync(DB_PATH);
    this.db.exec('PRAGMA journal_mode = WAL;');
    this.db.exec('PRAGMA foreign_keys = ON;');
    this.initSchema();
    this.seedIfEmpty();
  }

  private initSchema() {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS app_state (
        key TEXT PRIMARY KEY,
        json_value TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        role TEXT NOT NULL,
        company_scope TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
      );
      CREATE TABLE IF NOT EXISTS audit_logs (
        id TEXT PRIMARY KEY,
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        role TEXT NOT NULL,
        action TEXT NOT NULL,
        entity TEXT NOT NULL,
        details TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS backups (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        created_at TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        type TEXT NOT NULL,
        checksum TEXT NOT NULL
      );
    `);
  }

  private hashPassword(password: string): string {
    const salt = crypto.randomBytes(16).toString('hex');
    const derived = crypto.scryptSync(password, salt, 64).toString('hex');
    return `${salt}:${derived}`;
  }

  public verifyPassword(password: string, storedHash: string): boolean {
    const [salt, key] = storedHash.split(':');
    if (!salt || !key) return false;
    const derived = crypto.scryptSync(password, salt, 64);
    const keyBuf = Buffer.from(key, 'hex');
    if (derived.length !== keyBuf.length) return false;
    return crypto.timingSafeEqual(derived, keyBuf);
  }

  private seedIfEmpty() {
    const existing = this.db.prepare('SELECT json_value FROM app_state WHERE key = ?').get('dataset') as
      | { json_value: string }
      | undefined;

    if (!existing) {
      const seed = createSeedDataset();
      this.saveDataset(seed);
      for (const log of seed.auditLogs) {
        this.insertAuditLog(log);
      }
      for (const bak of seed.backups) {
        this.insertBackupRecord(bak);
      }
    }

    const userCount = (this.db.prepare('SELECT COUNT(*) as cnt FROM users').get() as { cnt: number }).cnt;
    if (userCount === 0) {
      const defaultPass = process.env.ADMIN_PASSCODE || 'RealEstate360!2026';
      const defaultUsers: Omit<UserAccountRow, 'passwordHash'>[] = [
        {
          id: 'usr-cfo',
          name: 'Nasser Al Harthy',
          email: 'nasser.cfo@almajd.om',
          role: 'CFO_Admin',
          companyScope: 'ALL',
          active: true,
        },
        {
          id: 'usr-ctrl',
          name: 'Tariq Al Maskari',
          email: 'tariq.ctrl@almajd.om',
          role: 'Finance_Controller',
          companyScope: 'ALL',
          active: true,
        },
        {
          id: 'usr-pd',
          name: 'Khalid Al Riyami',
          email: 'khalid.pd@almajd.om',
          role: 'Project_Director',
          companyScope: 'ALL',
          active: true,
        },
        {
          id: 'usr-board',
          name: 'Sheikh Hamad Al Busaidi',
          email: 'hamad.board@almajd.om',
          role: 'Board_Viewer',
          companyScope: 'ALL',
          active: true,
        },
      ];
      const stmt = this.db.prepare(
        'INSERT INTO users (id, name, email, role, company_scope, password_hash, active) VALUES (?, ?, ?, ?, ?, ?, ?)'
      );
      for (const u of defaultUsers) {
        stmt.run(u.id, u.name, u.email, u.role, u.companyScope, this.hashPassword(defaultPass), u.active ? 1 : 0);
      }
    }
  }

  public getDataset(): MisDataset {
    const row = this.db.prepare('SELECT json_value FROM app_state WHERE key = ?').get('dataset') as
      | { json_value: string }
      | undefined;
    if (!row) {
      const fresh = createSeedDataset();
      this.saveDataset(fresh);
      return fresh;
    }
    const parsed = JSON.parse(row.json_value) as MisDataset;
    parsed.auditLogs = this.getAuditLogs();
    parsed.backups = this.getBackups();
    return parsed;
  }

  public saveDataset(dataset: MisDataset) {
    const now = new Date().toISOString();
    this.db
      .prepare(
        'INSERT INTO app_state (key, json_value, updated_at) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET json_value = excluded.json_value, updated_at = excluded.updated_at'
      )
      .run('dataset', JSON.stringify(dataset), now);
  }

  public getUsers(): Omit<UserAccountRow, 'passwordHash'>[] {
    const rows = this.db
      .prepare('SELECT id, name, email, role, company_scope as companyScope, active FROM users')
      .all() as { id: string; name: string; email: string; role: UserRole; companyScope: string; active: number }[];
    return rows.map((r) => ({ ...r, active: Boolean(r.active) }));
  }

  public findUserById(id: string): UserAccountRow | undefined {
    const r = this.db
      .prepare('SELECT id, name, email, role, company_scope as companyScope, password_hash as passwordHash, active FROM users WHERE id = ?')
      .get(id) as
      | { id: string; name: string; email: string; role: UserRole; companyScope: string; passwordHash: string; active: number }
      | undefined;
    if (!r) return undefined;
    return { ...r, active: Boolean(r.active) };
  }

  public insertAuditLog(entry: AuditLogEntry) {
    this.db
      .prepare('INSERT OR REPLACE INTO audit_logs (id, timestamp, actor, role, action, entity, details) VALUES (?, ?, ?, ?, ?, ?, ?)')
      .run(entry.id, entry.timestamp, entry.actor, entry.role, entry.action, entry.entity, entry.details);
  }

  public getAuditLogs(): AuditLogEntry[] {
    return this.db
      .prepare('SELECT id, timestamp, actor, role, action, entity, details FROM audit_logs ORDER BY timestamp DESC LIMIT 200')
      .all() as unknown as AuditLogEntry[];
  }

  public insertBackupRecord(bak: BackupMetadata) {
    this.db
      .prepare('INSERT OR REPLACE INTO backups (id, filename, created_at, size_bytes, type, checksum) VALUES (?, ?, ?, ?, ?, ?)')
      .run(bak.id, bak.filename, bak.createdAt, bak.sizeBytes, bak.type, bak.checksum);
  }

  public getBackups(): BackupMetadata[] {
    return this.db
      .prepare('SELECT id, filename, created_at as createdAt, size_bytes as sizeBytes, type, checksum FROM backups ORDER BY created_at DESC LIMIT 50')
      .all() as unknown as BackupMetadata[];
  }

  public createPhysicalBackup(type: 'Automatic' | 'Manual' = 'Manual'): BackupMetadata {
    const stamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `realestate360_${type.toLowerCase()}_${stamp}.db`;
    const destPath = path.resolve(BACKUP_DIR, filename);
    if (!destPath.startsWith(BACKUP_DIR + path.sep)) {
      throw new Error('Invalid backup target path');
    }
    fs.copyFileSync(DB_PATH, destPath);
    const buf = fs.readFileSync(destPath);
    const checksum = 'sha256:' + crypto.createHash('sha256').update(buf).digest('hex').slice(0, 12);
    const rec: BackupMetadata = {
      id: `bak-${Date.now()}`,
      filename,
      createdAt: new Date().toISOString(),
      sizeBytes: buf.length,
      type,
      checksum,
    };
    this.insertBackupRecord(rec);
    return rec;
  }

  public restoreBackup(filename: string): boolean {
    const safeName = path.basename(filename);
    const srcPath = path.resolve(BACKUP_DIR, safeName);
    if (!srcPath.startsWith(BACKUP_DIR + path.sep) || !fs.existsSync(srcPath)) {
      return false;
    }
    this.db.close();
    fs.copyFileSync(srcPath, DB_PATH);
    this.db = new DatabaseSync(DB_PATH);
    return true;
  }

  public runIntegrityCheck(): { ok: boolean; result: string; dbPath: string; sizeBytes: number } {
    const res = this.db.prepare('PRAGMA integrity_check').get() as { integrity_check: string };
    const stat = fs.statSync(DB_PATH);
    return {
      ok: res.integrity_check === 'ok',
      result: res.integrity_check,
      dbPath: DB_PATH,
      sizeBytes: stat.size,
    };
  }

  public upsertTrialBalanceRows(companyId: string, period: string, newRows: TrialBalanceRow[]): MisDataset {
    const ds = this.getDataset();
    const filtered = ds.trialBalance.filter((r) => !(r.companyId === companyId && r.period === period));
    ds.trialBalance = [...filtered, ...newRows];
    const wf = ds.workflows.find((w) => w.period === period);
    if (wf) {
      wf.tbUploaded = true;
      if (wf.stage === 'Open') wf.stage = 'Uploaded';
    }
    this.saveDataset(ds);
    return ds;
  }

  public saveGlMapping(rule: GlMappingRule): MisDataset {
    const ds = this.getDataset();
    const idx = ds.glMappings.findIndex((m) => m.accountCode === rule.accountCode);
    if (idx >= 0) ds.glMappings[idx] = rule;
    else ds.glMappings.push(rule);
    // Apply mapping retroactively to any matching unmapped TB lines
    for (const row of ds.trialBalance) {
      if (row.accountCode === rule.accountCode) {
        row.accountClass = rule.targetClass;
        if (rule.defaultProjectId) row.projectId = rule.defaultProjectId;
      }
    }
    this.saveDataset(ds);
    return ds;
  }

  public updateWorkflow(period: string, patch: Partial<PeriodWorkflowState>): MisDataset {
    const ds = this.getDataset();
    const wf = ds.workflows.find((w) => w.period === period);
    if (wf) {
      Object.assign(wf, patch);
    }
    this.saveDataset(ds);
    return ds;
  }

  public addAdjustment(adj: ManagementAdjustment): MisDataset {
    const ds = this.getDataset();
    ds.adjustments.unshift(adj);
    this.saveDataset(ds);
    return ds;
  }

  public approveAdjustment(id: string, approver: string): MisDataset {
    const ds = this.getDataset();
    const found = ds.adjustments.find((a) => a.id === id);
    if (found) {
      found.status = 'Approved';
      found.approvedBy = approver;
    }
    this.saveDataset(ds);
    return ds;
  }

  public updatePolicies(policies: AccountingPolicyConfig): MisDataset {
    const ds = this.getDataset();
    ds.policies = policies;
    this.saveDataset(ds);
    return ds;
  }

  public updateLicense(license: LicenseState): MisDataset {
    const ds = this.getDataset();
    ds.license = license;
    this.saveDataset(ds);
    return ds;
  }

  public resetToSeed(): MisDataset {
    const fresh = createSeedDataset();
    this.saveDataset(fresh);
    return fresh;
  }
}
