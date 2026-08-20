import { AuditReportData } from '../types';

const VAULT_STORAGE_KEY = 'finaudit_offline_saved_audits_v1';
const VAULT_SETTINGS_KEY = 'finaudit_offline_settings_v1';

export interface AppSettings {
  useOfflineEngine: boolean; // Default true (100% offline)
  apiKey?: string; // Optional if user wants cloud
  strictTolerance: boolean;
  autoSaveReports: boolean;
}

export const DEFAULT_SETTINGS: AppSettings = {
  useOfflineEngine: true,
  strictTolerance: true,
  autoSaveReports: true,
};

export function getSavedSettings(): AppSettings {
  try {
    const raw = localStorage.getItem(VAULT_SETTINGS_KEY);
    if (raw) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
    }
  } catch (err) {
    console.error('Error reading settings:', err);
  }
  return DEFAULT_SETTINGS;
}

export function saveSettings(settings: AppSettings): void {
  try {
    localStorage.setItem(VAULT_SETTINGS_KEY, JSON.stringify(settings));
  } catch (err) {
    console.error('Error saving settings:', err);
  }
}

export function getSavedAudits(): AuditReportData[] {
  try {
    const raw = localStorage.getItem(VAULT_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (err) {
    console.error('Error reading saved audits vault:', err);
  }
  return [];
}

export function saveAuditToVault(report: AuditReportData): void {
  try {
    const existing = getSavedAudits();
    // Filter out duplicates by id
    const filtered = existing.filter((r) => r.id !== report.id);
    // Keep up to latest 50 audits locally
    const updated = [report, ...filtered].slice(0, 50);
    localStorage.setItem(VAULT_STORAGE_KEY, JSON.stringify(updated));
  } catch (err) {
    console.error('Error saving audit to vault:', err);
  }
}

export function deleteAuditFromVault(id: string): AuditReportData[] {
  try {
    const existing = getSavedAudits();
    const updated = existing.filter((r) => r.id !== id);
    localStorage.setItem(VAULT_STORAGE_KEY, JSON.stringify(updated));
    return updated;
  } catch (err) {
    console.error('Error deleting audit from vault:', err);
    return getSavedAudits();
  }
}

export function clearVault(): void {
  try {
    localStorage.removeItem(VAULT_STORAGE_KEY);
  } catch (err) {
    console.error('Error clearing vault:', err);
  }
}
