import { Purchase, RateRecord, AppSettings, ImportBatch, RateCorrection } from '../types';
import { dbService } from './indexedDB';
import defaultRatesData from '../data/defaultRates.json';
import { isSupabaseConfigured } from '../services/supabaseClient';
export { isSupabaseConfigured };
import {
  supabasePurchases,
  supabaseRates,
  supabaseSettings,
  supabaseCorrections,
} from './supabaseRepository';

export const DEFAULT_SETTINGS: AppSettings = {
  goldMarkdownPct: 3.0,
  silverMarkdownPct: 3.0,
  rateProviderEnabled: false,
  rateProviderName: 'IBJA Official Benchmark (Free Daily PM Source)',
  confirmTaxTreatment: 'UNCONFIRMED',
  confirmSession: 'UNSPECIFIED',
  lastApiCheck: undefined,
  lastSuccessfulUpdate: undefined,
};

// Storage Keys for Dual Persistence (IndexedDB + LocalStorage fallback)
const LS_PURCHASES_KEY = 'bullion_ledger_purchases_v1';
const LS_SETTINGS_KEY = 'bullion_ledger_settings_v1';
const LS_CORRECTIONS_KEY = 'bullion_ledger_corrections_v1';
const LS_BATCHES_KEY = 'bullion_ledger_batches_v1';

function readLocalStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === 'undefined' || !window.localStorage) return defaultValue;
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) return defaultValue;
    return JSON.parse(raw) as T;
  } catch (err) {
    console.warn(`LocalStorage read error for "${key}":`, err);
    return defaultValue;
  }
}

function writeLocalStorage<T>(key: string, value: T): void {
  if (typeof window === 'undefined' || !window.localStorage) return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (err) {
    console.warn(`LocalStorage write error for "${key}":`, err);
  }
}

export interface IPurchaseRepository {
  getAll(): Promise<Purchase[]>;
  getById(id: string): Promise<Purchase | undefined>;
  save(purchase: Purchase): Promise<void>;
  saveBatch(purchases: Purchase[]): Promise<void>;
  softDelete(id: string): Promise<void>;
  restore(id: string): Promise<void>;
  permanentDelete(id: string): Promise<void>;
  undoBatch(batchId: string): Promise<number>;
  clearAll(): Promise<void>;
}

export interface IRateRepository {
  getAll(): Promise<RateRecord[]>;
  getById(id: string): Promise<RateRecord | undefined>;
  save(rate: RateRecord): Promise<void>;
  saveBatch(rates: RateRecord[]): Promise<number>;
  clearAll(): Promise<void>;
  seedDefaultsIfEmpty(): Promise<number>;
}

export interface ISettingsRepository {
  get(): Promise<AppSettings>;
  save(settings: AppSettings): Promise<void>;
}

export interface ICorrectionRepository {
  getAll(): Promise<RateCorrection[]>;
  save(correction: RateCorrection): Promise<void>;
}

export interface IImportBatchRepository {
  getAll(): Promise<ImportBatch[]>;
  save(batch: ImportBatch): Promise<void>;
  markUndone(batchId: string): Promise<void>;
}

// -------------------------------------------------------------
// Unified Hybrid Repository (Supabase Cloud + IndexedDB Cache + LocalStorage)
// -------------------------------------------------------------

export class PurchaseRepository implements IPurchaseRepository {
  async getAll(): Promise<Purchase[]> {
    // 1. If Supabase is configured, fetch cloud transactions (Public Read allows guests & superusers)
    if (isSupabaseConfigured()) {
      try {
        const cloudList = await supabasePurchases.getAll();
        if (cloudList && Array.isArray(cloudList) && cloudList.length > 0) {
          // Replicate into local cache for offline resilience
          writeLocalStorage(LS_PURCHASES_KEY, cloudList);
          try {
            await dbService.putBatch('purchases', cloudList);
          } catch {
            // cache write warning
          }
          return cloudList;
        }
      } catch (err) {
        console.warn('Supabase purchases fetch warning, checking local cache:', err);
      }
    }

    // 2. Try local IndexedDB
    try {
      const idbList = await dbService.getAll<Purchase>('purchases');
      if (Array.isArray(idbList) && idbList.length > 0) {
        writeLocalStorage(LS_PURCHASES_KEY, idbList);
        return idbList;
      }
    } catch (err) {
      console.warn('IndexedDB purchases getAll warning, checking LocalStorage fallback:', err);
    }

    // 3. Fallback to LocalStorage
    const lsList = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    return lsList;
  }

  async getById(id: string): Promise<Purchase | undefined> {
    try {
      const item = await dbService.get<Purchase>('purchases', id);
      if (item) return item;
    } catch {
      // ignore
    }
    const all = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    return all.find((p) => p.id === id);
  }

  async save(purchase: Purchase): Promise<void> {
    const updated: Purchase = {
      ...purchase,
      updatedAt: new Date().toISOString(),
    };

    // 1. Synchronously persist to LocalStorage immediately
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const idx = existing.findIndex((p) => p.id === updated.id);
    if (idx >= 0) {
      existing[idx] = updated;
    } else {
      existing.unshift(updated);
    }
    writeLocalStorage(LS_PURCHASES_KEY, existing);

    // 2. Persist to IndexedDB
    try {
      await dbService.put<Purchase>('purchases', updated);
    } catch (err) {
      console.warn('IndexedDB put failed (data preserved in LocalStorage):', err);
    }

    // 3. Persist to Supabase Cloud if configured
    if (isSupabaseConfigured()) {
      supabasePurchases.save(updated).catch((err) => {
        console.warn('Supabase cloud sync error (preserved in local storage):', err);
      });
    }
  }

  async saveBatch(newPurchases: Purchase[]): Promise<void> {
    if (!newPurchases || newPurchases.length === 0) return;

    // 1. LocalStorage
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const map = new Map<string, Purchase>();
    for (const p of existing) map.set(p.id, p);
    for (const p of newPurchases) map.set(p.id, p);
    const merged = Array.from(map.values());
    writeLocalStorage(LS_PURCHASES_KEY, merged);

    // 2. IndexedDB
    try {
      await dbService.putBatch<Purchase>('purchases', newPurchases);
    } catch (err) {
      console.warn('IndexedDB putBatch failed:', err);
    }

    // 3. Supabase Cloud
    if (isSupabaseConfigured()) {
      supabasePurchases.saveBatch(newPurchases).catch((err) => {
        console.warn('Supabase cloud batch sync error:', err);
      });
    }
  }

  async softDelete(id: string): Promise<void> {
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const item = existing.find((p) => p.id === id);
    if (item) {
      item.deleted = true;
      item.deletedAt = new Date().toISOString();
      writeLocalStorage(LS_PURCHASES_KEY, existing);
    }

    try {
      const idbItem = await this.getById(id);
      if (idbItem) {
        idbItem.deleted = true;
        idbItem.deletedAt = new Date().toISOString();
        await dbService.put<Purchase>('purchases', idbItem);
      }
    } catch (err) {
      console.warn('IndexedDB softDelete error:', err);
    }

    if (isSupabaseConfigured()) {
      supabasePurchases.softDelete(id).catch(console.warn);
    }
  }

  async restore(id: string): Promise<void> {
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const item = existing.find((p) => p.id === id);
    if (item) {
      item.deleted = false;
      item.deletedAt = undefined;
      writeLocalStorage(LS_PURCHASES_KEY, existing);
    }

    try {
      const idbItem = await this.getById(id);
      if (idbItem) {
        idbItem.deleted = false;
        idbItem.deletedAt = undefined;
        await dbService.put<Purchase>('purchases', idbItem);
      }
    } catch (err) {
      console.warn('IndexedDB restore error:', err);
    }

    if (isSupabaseConfigured()) {
      supabasePurchases.restore(id).catch(console.warn);
    }
  }

  async permanentDelete(id: string): Promise<void> {
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const filtered = existing.filter((p) => p.id !== id);
    writeLocalStorage(LS_PURCHASES_KEY, filtered);

    try {
      await dbService.delete('purchases', id);
    } catch (err) {
      console.warn('IndexedDB permanentDelete error:', err);
    }

    if (isSupabaseConfigured()) {
      supabasePurchases.permanentDelete(id).catch(console.warn);
    }
  }

  async undoBatch(batchId: string): Promise<number> {
    const existing = readLocalStorage<Purchase[]>(LS_PURCHASES_KEY, []);
    const kept = existing.filter((p) => p.batchId !== batchId);
    const removedCount = existing.length - kept.length;
    writeLocalStorage(LS_PURCHASES_KEY, kept);

    try {
      const all = await this.getAll();
      const batchItems = all.filter((p) => p.batchId === batchId);
      for (const item of batchItems) {
        await dbService.delete('purchases', item.id);
      }
    } catch (err) {
      console.warn('IndexedDB undoBatch error:', err);
    }

    if (isSupabaseConfigured()) {
      supabasePurchases.undoBatch(batchId).catch(console.warn);
    }

    return removedCount;
  }

  async clearAll(): Promise<void> {
    writeLocalStorage(LS_PURCHASES_KEY, []);
    try {
      await dbService.clear('purchases');
    } catch (err) {
      console.warn('IndexedDB clear purchases error:', err);
    }

    if (isSupabaseConfigured()) {
      supabasePurchases.clearAll().catch(console.warn);
    }
  }
}

export class RateRepository implements IRateRepository {
  async getAll(): Promise<RateRecord[]> {
    // 1. Try Supabase cloud rates if configured
    if (isSupabaseConfigured()) {
      try {
        const cloudRates = await supabaseRates.getAll();
        if (cloudRates && cloudRates.length > 0) {
          // Merge with default 5,666 historical rates so historical benchmarks are always intact
          const rateMap = new Map<string, RateRecord>();
          for (const r of (defaultRatesData as RateRecord[])) {
            rateMap.set(r.id, r);
          }
          for (const r of cloudRates) {
            rateMap.set(r.id, r);
          }
          const merged = Array.from(rateMap.values());
          // Cache in IndexedDB for offline resilience
          try {
            await dbService.putBatch('rates', merged);
          } catch {
            // cache warning
          }
          return merged;
        }
      } catch (err) {
        console.warn('Supabase rates fetch warning:', err);
      }
    }

    // 2. Try IndexedDB
    try {
      const list = await dbService.getAll<RateRecord>('rates');
      if (list && list.length > 0) return list;
    } catch (err) {
      console.warn('IndexedDB rates getAll failed, using bundled JSON fallback:', err);
    }

    return defaultRatesData as RateRecord[];
  }

  async getById(id: string): Promise<RateRecord | undefined> {
    try {
      return await dbService.get<RateRecord>('rates', id);
    } catch {
      return (defaultRatesData as RateRecord[]).find((r) => r.id === id);
    }
  }

  async save(rate: RateRecord): Promise<void> {
    try {
      await dbService.put<RateRecord>('rates', rate);
    } catch (err) {
      console.warn('IndexedDB save rate error:', err);
    }

    if (isSupabaseConfigured()) {
      supabaseRates.saveBatch([rate]).catch(console.warn);
    }
  }

  async saveBatch(rates: RateRecord[]): Promise<number> {
    try {
      await dbService.putBatch<RateRecord>('rates', rates);
    } catch (err) {
      console.warn('IndexedDB saveBatch rates error:', err);
    }

    if (isSupabaseConfigured()) {
      supabaseRates.saveBatch(rates).catch(console.warn);
    }

    return rates.length;
  }

  async clearAll(): Promise<void> {
    try {
      await dbService.clear('rates');
    } catch (err) {
      console.warn('IndexedDB clear rates error:', err);
    }
  }

  async seedDefaultsIfEmpty(): Promise<number> {
    try {
      const existing = await dbService.getAll<RateRecord>('rates');
      if (existing.length === 0) {
        const defaults = defaultRatesData as RateRecord[];
        await dbService.putBatch<RateRecord>('rates', defaults);
        return defaults.length;
      }
      return existing.length;
    } catch (err) {
      console.warn('IndexedDB seedDefaultsIfEmpty fallback to bundled rates:', err);
      return (defaultRatesData as RateRecord[]).length;
    }
  }
}

export class SettingsRepository implements ISettingsRepository {
  async get(): Promise<AppSettings> {
    // 1. If Supabase configured, check cloud settings
    if (isSupabaseConfigured()) {
      try {
        const cloudSettings = await supabaseSettings.get();
        if (cloudSettings) {
          writeLocalStorage(LS_SETTINGS_KEY, cloudSettings);
          return cloudSettings;
        }
      } catch (err) {
        console.warn('Supabase settings get warning:', err);
      }
    }

    // 2. Check LocalStorage
    const lsSettings = readLocalStorage<AppSettings | null>(LS_SETTINGS_KEY, null);

    // 3. Check IndexedDB
    try {
      const record = await dbService.get<{ key: string; value: AppSettings }>('settings', 'app_settings');
      if (record && record.value) {
        const merged = { ...DEFAULT_SETTINGS, ...record.value };
        writeLocalStorage(LS_SETTINGS_KEY, merged);
        return merged;
      }
    } catch {
      // ignore
    }

    if (lsSettings) {
      return { ...DEFAULT_SETTINGS, ...lsSettings };
    }

    return DEFAULT_SETTINGS;
  }

  async save(settings: AppSettings): Promise<void> {
    writeLocalStorage(LS_SETTINGS_KEY, settings);
    try {
      await dbService.put('settings', { key: 'app_settings', value: settings });
    } catch (err) {
      console.warn('IndexedDB save settings error:', err);
    }

    if (isSupabaseConfigured()) {
      supabaseSettings.save(settings).catch(console.warn);
    }
  }
}

export class CorrectionRepository implements ICorrectionRepository {
  async getAll(): Promise<RateCorrection[]> {
    if (isSupabaseConfigured()) {
      try {
        const cloud = await supabaseCorrections.getAll();
        if (cloud && cloud.length > 0) return cloud;
      } catch {
        // ignore
      }
    }

    try {
      const list = await dbService.getAll<RateCorrection>('corrections');
      if (list && list.length > 0) return list;
    } catch {
      // ignore
    }
    return readLocalStorage<RateCorrection[]>(LS_CORRECTIONS_KEY, []);
  }

  async save(correction: RateCorrection): Promise<void> {
    const list = readLocalStorage<RateCorrection[]>(LS_CORRECTIONS_KEY, []);
    list.unshift(correction);
    writeLocalStorage(LS_CORRECTIONS_KEY, list);
    try {
      await dbService.put<RateCorrection>('corrections', correction);
    } catch (err) {
      console.warn('IndexedDB save correction error:', err);
    }

    if (isSupabaseConfigured()) {
      supabaseCorrections.save(correction).catch(console.warn);
    }
  }
}

export class ImportBatchRepository implements IImportBatchRepository {
  async getAll(): Promise<ImportBatch[]> {
    try {
      const list = await dbService.getAll<ImportBatch>('importBatches');
      if (list && list.length > 0) return list;
    } catch {
      // ignore
    }
    return readLocalStorage<ImportBatch[]>(LS_BATCHES_KEY, []);
  }

  async save(batch: ImportBatch): Promise<void> {
    const list = readLocalStorage<ImportBatch[]>(LS_BATCHES_KEY, []);
    list.unshift(batch);
    writeLocalStorage(LS_BATCHES_KEY, list);
    try {
      await dbService.put<ImportBatch>('importBatches', batch);
    } catch (err) {
      console.warn('IndexedDB save batch error:', err);
    }
  }

  async markUndone(batchId: string): Promise<void> {
    const list = readLocalStorage<ImportBatch[]>(LS_BATCHES_KEY, []);
    const batch = list.find((b) => b.id === batchId);
    if (batch) {
      batch.undone = true;
      writeLocalStorage(LS_BATCHES_KEY, list);
    }
    try {
      const idbBatch = await dbService.get<ImportBatch>('importBatches', batchId);
      if (idbBatch) {
        idbBatch.undone = true;
        await dbService.put<ImportBatch>('importBatches', idbBatch);
      }
    } catch (err) {
      console.warn('IndexedDB markUndone error:', err);
    }
  }
}

// Single instance repositories
export const purchaseRepo = new PurchaseRepository();
export const rateRepo = new RateRepository();
export const settingsRepo = new SettingsRepository();
export const correctionRepo = new CorrectionRepository();
export const batchRepo = new ImportBatchRepository();

/**
 * 1-Click Upload: Sync all local purchases & settings to Supabase cloud database
 */
export async function syncLocalDataToSupabase(): Promise<{
  success: boolean;
  purchasesCount: number;
  message: string;
}> {
  if (!isSupabaseConfigured()) {
    return {
      success: false,
      purchasesCount: 0,
      message: 'Supabase credentials are not configured. Please enter your Supabase URL & Anon Key.',
    };
  }

  try {
    const [purchases, settings] = await Promise.all([
      purchaseRepo.getAll(),
      settingsRepo.get(),
    ]);

    if (purchases.length > 0) {
      const res = await supabasePurchases.saveBatch(purchases);
      if (!res.success) {
        const detail = res.error || 'Permission denied';
        const isRls = detail.toLowerCase().includes('row-level security') || detail.toLowerCase().includes('policy');
        return {
          success: false,
          purchasesCount: 0,
          message: isRls
            ? `Supabase RLS Blocked: ${detail}. Either sign in as kosamgo@gmail.com or run the 1-line SQL policy in Supabase SQL Editor.`
            : `Failed to upload purchases: ${detail}`,
        };
      }
    }

    const setRes = await supabaseSettings.save(settings);
    if (!setRes.success) {
      console.warn('Settings upload warning:', setRes.error);
    }

    return {
      success: true,
      purchasesCount: purchases.length,
      message: `Successfully synchronized ${purchases.length} purchases and settings to Supabase cloud!`,
    };
  } catch (err: any) {
    return {
      success: false,
      purchasesCount: 0,
      message: `Sync error: ${err.message}`,
    };
  }
}

/**
 * Upload all bundled historical rates (5,666 records) to Supabase cloud database
 */
export async function uploadRatesToSupabase(): Promise<{
  success: boolean;
  ratesCount: number;
  message: string;
}> {
  if (!isSupabaseConfigured()) {
    return {
      success: false,
      ratesCount: 0,
      message: 'Supabase credentials are not configured.',
    };
  }

  try {
    const allRates = (defaultRatesData as RateRecord[]);
    const res = await supabaseRates.saveBatch(allRates);
    if (!res.success) {
      const detail = res.error || 'Permission denied';
      const isRls = detail.toLowerCase().includes('row-level security') || detail.toLowerCase().includes('policy');
      return {
        success: false,
        ratesCount: res.count,
        message: isRls
          ? `Supabase RLS Blocked Rates: ${detail}. Please run: CREATE POLICY "Allow Initial Rates Upload" ON public.rates FOR ALL TO anon USING (true) WITH CHECK (true); in Supabase SQL Editor.`
          : `Failed to upload rates: ${detail}`,
      };
    }

    return {
      success: true,
      ratesCount: allRates.length,
      message: `Successfully uploaded all ${allRates.length} historical price records (Gold 995/999 & Silver 999) to Supabase cloud!`,
    };
  } catch (err: any) {
    return {
      success: false,
      ratesCount: 0,
      message: `Error uploading rates: ${err.message}`,
    };
  }
}

/**
 * Full JSON Backup and Restore Helpers
 */
export async function createFullBackup(includeRates = false): Promise<any> {
  const [purchases, settings, corrections, batches, rates] = await Promise.all([
    purchaseRepo.getAll(),
    settingsRepo.get(),
    correctionRepo.getAll(),
    batchRepo.getAll(),
    includeRates ? rateRepo.getAll() : Promise.resolve([]),
  ]);

  return {
    version: '1.0.0',
    exportedAt: new Date().toISOString(),
    settings,
    purchases,
    corrections,
    batches,
    customRates: includeRates ? rates : [],
  };
}

export async function restoreFromBackup(backupData: any): Promise<{
  purchasesRestored: number;
  settingsRestored: boolean;
}> {
  if (!backupData || typeof backupData !== 'object') {
    throw new Error('Invalid backup file: not a JSON object.');
  }

  let purchasesRestored = 0;
  if (Array.isArray(backupData.purchases)) {
    await purchaseRepo.saveBatch(backupData.purchases);
    purchasesRestored = backupData.purchases.length;
  }

  let settingsRestored = false;
  if (backupData.settings && typeof backupData.settings === 'object') {
    await settingsRepo.save({
      ...DEFAULT_SETTINGS,
      ...backupData.settings,
    });
    settingsRestored = true;
  }

  return { purchasesRestored, settingsRestored };
}
