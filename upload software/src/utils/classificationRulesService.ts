import {
  BalanceSheetHeadConfig,
  LedgerItem,
  PLCategory,
  SavedClassificationRule,
  TargetStatementType,
} from '../types/accounting';

const STORAGE_KEY = 'icai_saved_classification_rules';
const HEADS_STORAGE_KEY = 'icai_custom_heads_config';

/**
 * Normalizes ledger name for resilient matching across spelling / spacing / casing / suffixes
 */
export function normalizeRuleName(name: string): string {
  if (!name) return '';
  return name
    .toLowerCase()
    .trim()
    .replace(/\s+/g, ' ')
    .replace(/\b(a\/c|account|acct|acc)\b/gi, '')
    .replace(/[.,\-_#()]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Formats a clear human-readable classification nature string
 */
export function formatClassificationNature(
  targetType: TargetStatementType,
  head?: BalanceSheetHeadConfig,
  plCategory?: PLCategory
): string {
  if (targetType === 'BALANCE_SHEET' && head) {
    return `${head.nature}: Schedule ${head.scheduleNo} (${head.subHead})`;
  }
  if (targetType === 'PROFIT_AND_LOSS' && plCategory) {
    const formatted = plCategory.replace(/_/g, ' ');
    return `P&L ${formatted}`;
  }
  return 'Unclassified';
}

/**
 * Retrieves all saved classification rules from localStorage
 */
export function getSavedClassificationRules(): SavedClassificationRule[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) {
        return parsed;
      }
    }
  } catch (err) {
    console.error('Error loading saved classification rules:', err);
  }
  return [];
}

/**
 * Saves all classification rules back to localStorage
 */
export function persistClassificationRules(rules: SavedClassificationRule[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(rules));
  } catch (err) {
    console.error('Error saving classification rules:', err);
  }
}

/**
 * Creates or updates a classification rule for a specific ledger
 */
export function saveRuleFromLedger(
  ledger: LedgerItem,
  heads: BalanceSheetHeadConfig[]
): SavedClassificationRule {
  const currentRules = getSavedClassificationRules();
  const norm = normalizeRuleName(ledger.ledgerName);

  const matchedHead = heads.find(h => h.code === ledger.headCode);
  const natureStr = formatClassificationNature(ledger.targetType, matchedHead, ledger.plCategory);

  const newRule: SavedClassificationRule = {
    id: `rule-${norm.replace(/[^a-z0-9]/g, '-')}-${Date.now()}`,
    ledgerName: ledger.ledgerName,
    normalizedName: norm,
    originalGroup: ledger.originalGroup,
    targetType: ledger.targetType,
    headCode: ledger.headCode,
    subHead: matchedHead?.subHead || ledger.subHead,
    scheduleNo: matchedHead?.scheduleNo || ledger.scheduleNo,
    headNature: matchedHead?.nature,
    plCategory: ledger.plCategory,
    classificationNature: natureStr,
    savedAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  // Replace any existing rule for this normalized name or ledger name
  const existingIdx = currentRules.findIndex(
    r => r.normalizedName === norm || r.ledgerName.toLowerCase() === ledger.ledgerName.toLowerCase()
  );

  let updatedList: SavedClassificationRule[];
  if (existingIdx >= 0) {
    updatedList = [...currentRules];
    updatedList[existingIdx] = {
      ...updatedList[existingIdx],
      ...newRule,
      id: updatedList[existingIdx].id,
      savedAt: updatedList[existingIdx].savedAt,
      updatedAt: new Date().toISOString(),
    };
  } else {
    updatedList = [newRule, ...currentRules];
  }

  persistClassificationRules(updatedList);
  return newRule;
}

/**
 * Bulk saves classification rules for multiple ledgers
 */
export function bulkSaveRules(
  ledgersToSave: LedgerItem[],
  heads: BalanceSheetHeadConfig[]
): SavedClassificationRule[] {
  let currentRules = getSavedClassificationRules();

  ledgersToSave.forEach(l => {
    const norm = normalizeRuleName(l.ledgerName);
    const matchedHead = heads.find(h => h.code === l.headCode);
    const natureStr = formatClassificationNature(l.targetType, matchedHead, l.plCategory);

    const rule: SavedClassificationRule = {
      id: `rule-${norm.replace(/[^a-z0-9]/g, '-')}-${Date.now()}`,
      ledgerName: l.ledgerName,
      normalizedName: norm,
      originalGroup: l.originalGroup,
      targetType: l.targetType,
      headCode: l.headCode,
      subHead: matchedHead?.subHead || l.subHead,
      scheduleNo: matchedHead?.scheduleNo || l.scheduleNo,
      headNature: matchedHead?.nature,
      plCategory: l.plCategory,
      classificationNature: natureStr,
      savedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    const idx = currentRules.findIndex(
      r => r.normalizedName === norm || r.ledgerName.toLowerCase() === l.ledgerName.toLowerCase()
    );

    if (idx >= 0) {
      currentRules[idx] = {
        ...currentRules[idx],
        ...rule,
        id: currentRules[idx].id,
        savedAt: currentRules[idx].savedAt,
      };
    } else {
      currentRules.unshift(rule);
    }
  });

  persistClassificationRules(currentRules);
  return currentRules;
}

/**
 * Deletes a single rule by ID or normalized name
 */
export function deleteSavedClassificationRule(ruleId: string): SavedClassificationRule[] {
  const currentRules = getSavedClassificationRules();
  const updated = currentRules.filter(r => r.id !== ruleId && r.normalizedName !== ruleId);
  persistClassificationRules(updated);
  return updated;
}

/**
 * Clears all saved classification rules
 */
export function clearAllSavedClassificationRules(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch (err) {
    console.error('Error clearing saved rules:', err);
  }
}

/**
 * Builds a fast lookup map of saved rules indexed by normalized ledger name and exact name
 */
export function getSavedRulesMap(): Record<string, SavedClassificationRule> {
  const rules = getSavedClassificationRules();
  const map: Record<string, SavedClassificationRule> = {};

  rules.forEach(r => {
    map[r.normalizedName] = r;
    map[r.ledgerName.toLowerCase().trim()] = r;
  });

  return map;
}

/**
 * Finds a saved rule matching a ledger name
 */
export function findMatchingRule(
  ledgerName: string,
  rulesMap: Record<string, SavedClassificationRule>
): SavedClassificationRule | undefined {
  if (!ledgerName) return undefined;
  const exact = ledgerName.toLowerCase().trim();
  if (rulesMap[exact]) return rulesMap[exact];

  const norm = normalizeRuleName(ledgerName);
  if (rulesMap[norm]) return rulesMap[norm];

  return undefined;
}

/**
 * Persists customized heads configuration in localStorage
 */
export function saveCustomHeadsConfig(heads: BalanceSheetHeadConfig[]): void {
  try {
    localStorage.setItem(HEADS_STORAGE_KEY, JSON.stringify(heads));
  } catch (err) {
    console.error('Error saving heads config:', err);
  }
}

/**
 * Loads customized heads configuration if available
 */
export function getSavedCustomHeadsConfig(
  fallback: BalanceSheetHeadConfig[]
): BalanceSheetHeadConfig[] {
  try {
    const raw = localStorage.getItem(HEADS_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        return parsed;
      }
    }
  } catch (err) {
    console.error('Error loading saved heads config:', err);
  }
  return fallback;
}
