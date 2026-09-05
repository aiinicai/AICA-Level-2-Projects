import {
  EntityDetails,
  LedgerItem,
  BalanceSheetHeadConfig,
  ManualAdjustment,
  DepreciationAssetItem,
  NoteToAccountItem,
  SavedEntitySummary,
  SavedEntityWorkspace,
} from '../types/accounting';
import {
  DEFAULT_ENTITIES,
  DEFAULT_HEAD_CONFIGS,
  SAMPLE_APEX_TRIAL_BALANCE,
  SAMPLE_KOTHARI_TRIAL_BALANCE,
} from './defaultData';
import { DEFAULT_DEPRECIATION_ASSETS, DEFAULT_STANDARD_NOTES } from './nonCorporateDefaults';
import { classifyLedgersWithRuleEngine } from './classificationEngine';

const ENTITY_VAULT_STORAGE_KEY = 'non_corp_entity_vault_data';

function getLocalVault(): SavedEntityWorkspace[] {
  try {
    const raw = localStorage.getItem(ENTITY_VAULT_STORAGE_KEY);
    if (raw) {
      return JSON.parse(raw);
    }
  } catch (e) {
    console.error('Failed to parse local vault:', e);
  }

  // Generate seed records for default demo entities so the vault has immediate review data
  const seedVault: SavedEntityWorkspace[] = [
    {
      id: 'ws-ent-apex-seed',
      entityId: 'ent-apex',
      entityName: 'Apex Industrial Tools',
      entityType: 'Proprietorship',
      financialYear: '2024-2025',
      balanceSheetDate: '31st March 2025',
      savedAt: '2025-04-10T11:45:00.000Z',
      savedBy: 'admin',
      versionTag: 'Verified / Audited',
      notes: 'Proprietorship manufacturing unit - Full ICAI compliant trial balance with completed adjustments.',
      summary: {
        totalAssets: 4835000,
        totalLiabilities: 4835000,
        netProfit: 1245000,
        isBalanced: true,
        difference: 0,
        ledgersCount: 42,
        adjustmentsCount: 2,
        assetsCount: 6,
      },
      data: {
        entity: DEFAULT_ENTITIES[0],
        ledgers: classifyLedgersWithRuleEngine(SAMPLE_APEX_TRIAL_BALANCE, DEFAULT_HEAD_CONFIGS),
        headConfigs: DEFAULT_HEAD_CONFIGS,
        adjustments: [
          {
            id: 'adj-stock-apex',
            date: '31st March 2025',
            type: 'CLOSING_STOCK',
            description: 'Closing Stock valuation as per physical count at cost',
            debitHead: 'A05',
            creditHead: 'TRADING_CLOSING_STOCK',
            amount: 980000,
          },
        ],
        depreciationAssets: DEFAULT_DEPRECIATION_ASSETS,
        notesToAccounts: DEFAULT_STANDARD_NOTES,
      },
    },
    {
      id: 'ws-ent-kothari-seed',
      entityId: 'ent-kothari',
      entityName: 'Kothari Trading Co.',
      entityType: 'Partnership Firm',
      financialYear: '2024-2025',
      balanceSheetDate: '31st March 2025',
      savedAt: '2025-04-12T16:20:00.000Z',
      savedBy: 'auditor',
      versionTag: 'Interim Review',
      notes: 'Wholesale partnership firm with 2 active partners. Profit sharing 60:40.',
      summary: {
        totalAssets: 3410000,
        totalLiabilities: 3410000,
        netProfit: 830000,
        isBalanced: true,
        difference: 0,
        ledgersCount: 36,
        adjustmentsCount: 1,
        assetsCount: 5,
      },
      data: {
        entity: DEFAULT_ENTITIES[1],
        ledgers: classifyLedgersWithRuleEngine(SAMPLE_KOTHARI_TRIAL_BALANCE, DEFAULT_HEAD_CONFIGS),
        headConfigs: DEFAULT_HEAD_CONFIGS,
        adjustments: [
          {
            id: 'adj-stock-kothari',
            date: '31st March 2025',
            type: 'CLOSING_STOCK',
            description: 'Closing Stock at Cost / NRV whichever is lower',
            debitHead: 'A05',
            creditHead: 'TRADING_CLOSING_STOCK',
            amount: 720000,
          },
        ],
        depreciationAssets: DEFAULT_DEPRECIATION_ASSETS,
        notesToAccounts: DEFAULT_STANDARD_NOTES,
      },
    },
  ];

  localStorage.setItem(ENTITY_VAULT_STORAGE_KEY, JSON.stringify(seedVault));
  return seedVault;
}

function saveLocalVault(vault: SavedEntityWorkspace[]) {
  try {
    localStorage.setItem(ENTITY_VAULT_STORAGE_KEY, JSON.stringify(vault));
  } catch (e) {
    console.error('Failed to write local vault:', e);
  }
}

export const entityVaultService = {
  async saveEntityWorkspace(workspace: SavedEntityWorkspace): Promise<{ success: boolean; id?: string; error?: string }> {
    // 1. Try server API
    try {
      const res = await fetch('/api/entities/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ workspace }),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        // Also update local cache
        const local = getLocalVault();
        const idx = local.findIndex(e => e.entityId === workspace.entityId || e.id === workspace.id);
        if (idx >= 0) {
          local[idx] = { ...workspace, savedAt: data.savedAt || new Date().toISOString() };
        } else {
          local.unshift({ ...workspace, savedAt: data.savedAt || new Date().toISOString() });
        }
        saveLocalVault(local);
        return { success: true, id: data.id };
      }
    } catch (e) {
      console.warn('Server entity save failed, falling back to local storage:', e);
    }

    // 2. Local fallback
    const local = getLocalVault();
    const idx = local.findIndex(e => e.entityId === workspace.entityId || e.id === workspace.id);
    const updatedRecord = {
      ...workspace,
      savedAt: new Date().toISOString(),
    };
    if (idx >= 0) {
      local[idx] = updatedRecord;
    } else {
      local.unshift(updatedRecord);
    }
    saveLocalVault(local);
    return { success: true, id: updatedRecord.id };
  },

  async listSavedEntities(): Promise<SavedEntitySummary[]> {
    // 1. Try server API
    try {
      const res = await fetch('/api/entities/list');
      const data = await res.json();
      if (res.ok && data.success && Array.isArray(data.entities)) {
        return data.entities.map((e: any) => ({
          id: e.id,
          entityId: e.entityId,
          entityName: e.entityName,
          entityType: e.entityType,
          financialYear: e.financialYear,
          balanceSheetDate: e.balanceSheetDate,
          savedAt: e.savedAt,
          savedBy: e.savedBy || 'Staff',
          versionTag: e.versionTag,
          totalAssets: e.summary?.totalAssets ?? 0,
          totalLiabilities: e.summary?.totalLiabilities ?? 0,
          netProfit: e.summary?.netProfit ?? 0,
          isBalanced: e.summary?.isBalanced ?? true,
          difference: e.summary?.difference ?? 0,
          ledgersCount: e.summary?.ledgersCount ?? 0,
        }));
      }
    } catch (e) {
      console.warn('Server list entities failed, using local vault:', e);
    }

    // 2. Local fallback
    const local = getLocalVault();
    return local.map(e => ({
      id: e.id,
      entityId: e.entityId,
      entityName: e.entityName,
      entityType: e.entityType,
      financialYear: e.financialYear,
      balanceSheetDate: e.balanceSheetDate,
      savedAt: e.savedAt,
      savedBy: e.savedBy || 'Staff',
      versionTag: e.versionTag,
      totalAssets: e.summary?.totalAssets ?? 0,
      totalLiabilities: e.summary?.totalLiabilities ?? 0,
      netProfit: e.summary?.netProfit ?? 0,
      isBalanced: e.summary?.isBalanced ?? true,
      difference: e.summary?.difference ?? 0,
      ledgersCount: e.summary?.ledgersCount ?? 0,
    }));
  },

  async fetchEntityWorkspace(idOrEntityId: string): Promise<SavedEntityWorkspace | null> {
    // 1. Try server API
    try {
      const res = await fetch(`/api/entities/${encodeURIComponent(idOrEntityId)}`);
      const data = await res.json();
      if (res.ok && data.success && data.workspace) {
        return data.workspace;
      }
    } catch (e) {
      console.warn('Server fetch entity failed, checking local vault:', e);
    }

    // 2. Local fallback
    const local = getLocalVault();
    const found = local.find(e => e.id === idOrEntityId || e.entityId === idOrEntityId);
    return found || null;
  },

  async deleteEntityWorkspace(idOrEntityId: string): Promise<boolean> {
    try {
      await fetch(`/api/entities/${encodeURIComponent(idOrEntityId)}`, {
        method: 'DELETE',
      });
    } catch (e) {
      console.warn('Server delete entity failed:', e);
    }

    const local = getLocalVault();
    const filtered = local.filter(e => e.id !== idOrEntityId && e.entityId !== idOrEntityId);
    saveLocalVault(filtered);
    return true;
  },
};
