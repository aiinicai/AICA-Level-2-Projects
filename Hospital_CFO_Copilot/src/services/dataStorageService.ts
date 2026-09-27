/**
 * Hospital CFO Copilot - Data Storage Service (Production Architecture)
 *
 * ARCHITECTURAL RULE:
 * Firestore is the sole authoritative data store for all hospital financial data
 * (encounters, clinical services, billing records, claims, collections, tariffs, and budgets).
 *
 * LocalStorage is NOT used as a source or fallback for financial records.
 * All functions below ensure a clean empty state on startup and clean up any legacy
 * browser storage keys to guarantee that old cached data never re-emerges after a workspace reset.
 */

import {
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  Encounter,
  Service,
  TariffMasterItem,
} from '../types';

const STORAGE_KEY_PREFIX = 'cfo_hospital_data_v2_';

export interface PersistentHospitalDatasets {
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  tariffMaster: TariffMasterItem[];
  budgetRecords: BudgetRecord[];
}

const EMPTY_DATASETS: PersistentHospitalDatasets = {
  encounters: [],
  services: [],
  billings: [],
  claims: [],
  collections: [],
  tariffMaster: [],
  budgetRecords: [],
};

/**
 * Clean initial dataset getter. Always returns empty datasets.
 * Firestore real-time listeners provide the authoritative data state.
 */
export function getImportedDatasets(): PersistentHospitalDatasets {
  return { ...EMPTY_DATASETS };
}

/**
 * No-op: Financial datasets are persisted exclusively to Firestore.
 */
export function saveImportedDatasets(_data: Partial<PersistentHospitalDatasets>): void {
  // Production rule: Firestore is the authoritative store. Financial data is never written to localStorage.
}

/**
 * Completely purges any legacy cached hospital data keys from browser localStorage
 * to ensure that stale datasets never re-emerge after a workspace clear or logout.
 */
export function clearImportedDatasets(): void {
  try {
    const keys = [
      'encounters',
      'services',
      'billings',
      'claims',
      'collections',
      'tariffMaster',
      'budgetRecords',
    ];
    for (const k of keys) {
      localStorage.removeItem(`${STORAGE_KEY_PREFIX}${k}`);
    }
  } catch (err) {
    console.warn('[Storage] Could not clear legacy storage keys:', err);
  }
}
