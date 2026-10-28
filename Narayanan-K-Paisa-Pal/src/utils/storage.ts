import { AppRow, UserProfile, StorageResult } from '../types';
import { fmtD, toDay, todayIST, DAY, uid } from './calculations';
import { getInitialTrialAppRows } from '../data/dummyDocuments';

export const STORAGE_KEY = 'due-dates-alert-v1';
export const STORAGE_BACKUP_KEY = 'due-dates-alert-v1-prev-backup';

export interface StoredPayload {
  rows: AppRow[] | string; // Plaintext array or encrypted string ciphertext
  profile: UserProfile;
  encrypted?: boolean;
  vaultIv?: string;
  vaultSalt?: string;
  version?: number;
}

export function loadStoredData(): {
  rows: AppRow[];
  profile: UserProfile;
  isEncrypted?: boolean;
  encryptedRowsCiphertext?: string;
  vaultIv?: string;
} {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return {
        rows: generateSampleData(),
        profile: { whatsapp: '', showUpload: true, theme: 'system' },
      };
    }

    const parsed = JSON.parse(raw);

    // Deeply preserve the full profile including all security, recovery, emergency and nominee settings
    const loadedProfile: UserProfile = {
      whatsapp: parsed.profile?.whatsapp || '',
      showUpload: parsed.profile?.showUpload !== false,
      theme: parsed.profile?.theme || 'system',
      pinEnabled: Boolean(parsed.profile?.pinEnabled),
      pinHash: parsed.profile?.pinHash || undefined,
      pinSalt: parsed.profile?.pinSalt || undefined,
      biometricEnabled: Boolean(parsed.profile?.biometricEnabled),
      emergencyNotes: parsed.profile?.emergencyNotes || undefined,
      emergencyContacts: Array.isArray(parsed.profile?.emergencyContacts)
        ? parsed.profile.emergencyContacts
        : undefined,
      primaryBank: parsed.profile?.primaryBank || undefined,
      nomineeNotes: parsed.profile?.nomineeNotes || undefined,
      vaultEncrypted: Boolean(parsed.profile?.vaultEncrypted || parsed.encrypted),
      vaultSalt: parsed.profile?.vaultSalt || parsed.vaultSalt || undefined,
      vaultVerification: parsed.profile?.vaultVerification || undefined,
      vaultIv: parsed.profile?.vaultIv || parsed.vaultIv || undefined,
      recoveryKeyHash: parsed.profile?.recoveryKeyHash || undefined,
      recoveryKeySalt: parsed.profile?.recoveryKeySalt || undefined,
      lastBackupAt: parsed.profile?.lastBackupAt || undefined,
    };

    // Check if the payload is encrypted
    if (parsed.encrypted && typeof parsed.rows === 'string') {
      return {
        rows: [],
        profile: loadedProfile,
        isEncrypted: true,
        encryptedRowsCiphertext: parsed.rows,
        vaultIv: parsed.vaultIv,
      };
    }

    return {
      rows: Array.isArray(parsed.rows) ? parsed.rows : generateSampleData(),
      profile: loadedProfile,
      isEncrypted: false,
    };
  } catch (e: any) {
    console.error('Error loading data from localStorage', e);
    return {
      rows: generateSampleData(),
      profile: { whatsapp: '', showUpload: true, theme: 'system' },
      isEncrypted: false,
    };
  }
}

export function saveStoredData(
  rows: AppRow[] | string,
  profile: UserProfile,
  options?: { isEncrypted?: boolean; vaultIv?: string; vaultSalt?: string }
): StorageResult {
  try {
    // Keep a pre-write backup in case of storage failure or corruption
    const current = localStorage.getItem(STORAGE_KEY);
    if (current) {
      try {
        localStorage.setItem(STORAGE_BACKUP_KEY, current);
      } catch {
        // Non-critical if backup cannot be stored
      }
    }

    const payload: StoredPayload = {
      rows,
      profile,
      encrypted: options?.isEncrypted ?? profile.vaultEncrypted ?? false,
      vaultIv: options?.vaultIv ?? profile.vaultIv,
      vaultSalt: options?.vaultSalt ?? profile.vaultSalt,
      version: 2,
    };

    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    return { success: true };
  } catch (e: any) {
    console.error('Error persisting data to localStorage', e);
    const isQuota =
      e?.name === 'QuotaExceededError' ||
      e?.name === 'NS_ERROR_DOM_QUOTA_REACHED' ||
      e?.code === 22 ||
      e?.code === 1014;
    return {
      success: false,
      error: isQuota
        ? 'Storage quota exceeded. Please export backup and clear old scans.'
        : e?.message || 'Storage failure in browser storage.',
    };
  }
}

export function clearStoredData(): boolean {
  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STORAGE_BACKUP_KEY);
    return true;
  } catch (e) {
    console.error('Error clearing localStorage', e);
    return false;
  }
}

export function generateSampleData(): AppRow[] {
  return getInitialTrialAppRows();
}
