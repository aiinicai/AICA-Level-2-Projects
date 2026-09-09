import { BalanceSheetHeadConfig, DepreciationAssetItem, LedgerItem } from '../types/accounting';
import { classifyLedgersWithRuleEngine } from './classificationEngine';
import { getSavedRulesMap } from './classificationRulesService';

export interface PreviousYearMatchResult {
  mergedLedgers: LedgerItem[];
  stats: {
    totalPyLedgers: number;
    matchedCount: number;
    addedCount: number;
    totalPyDebit: number;
    totalPyCredit: number;
    pyDifference: number;
    isPyBalanced: boolean;
  };
  extractedPyAssets: Partial<DepreciationAssetItem>[];
}

/**
 * Normalizes ledger names for comparison by trimming, lowercasing,
 * and stripping standard ERP suffixes like a/c, account, dr, cr, etc.
 */
export function normalizeLedgerName(name: string): string {
  if (!name) return '';
  return name
    .toLowerCase()
    .replace(/[\(\)\[\]\{\}\.,\-_\\\/]/g, ' ')
    .replace(/\b(a\s*\/\s*c|a\s*c|acc|acct|account|dr|cr|ltd|pvt|private|limited|m\/s|messrs)\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Calculates similarity score between two ledger names (0 to 1).
 */
function calculateSimilarity(str1: string, str2: string): number {
  const norm1 = normalizeLedgerName(str1);
  const norm2 = normalizeLedgerName(str2);

  if (norm1 === norm2) return 1.0;
  if (!norm1 || !norm2) return 0;

  // Direct containment
  if (norm1.includes(norm2) || norm2.includes(norm1)) {
    const minLen = Math.min(norm1.length, norm2.length);
    const maxLen = Math.max(norm1.length, norm2.length);
    return minLen / maxLen;
  }

  // Token overlap (Jaccard similarity of words)
  const words1 = new Set(norm1.split(' ').filter(w => w.length > 1));
  const words2 = new Set(norm2.split(' ').filter(w => w.length > 1));

  if (words1.size === 0 || words2.size === 0) return 0;

  let intersection = 0;
  words1.forEach(w => {
    if (words2.has(w)) intersection++;
  });

  const union = new Set([...words1, ...words2]).size;
  return union > 0 ? intersection / union : 0;
}

/**
 * Merges previous year trial balance ledgers into current year ledgers.
 * Matched current year ledgers receive `previousYearDebit`, `previousYearCredit`, and `previousYearAmount`.
 * Previous-year-only ledgers (closed/zero in current year) are appended with CY=0 and classified.
 */
export function matchAndMergePreviousYearTrialBalance(
  currentLedgers: LedgerItem[],
  previousYearRawLedgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[],
  headConfigs: BalanceSheetHeadConfig[],
  savedRulesMap?: Record<string, any>
): PreviousYearMatchResult {
  let matchedCount = 0;
  let addedCount = 0;

  let totalPyDebit = 0;
  let totalPyCredit = 0;

  // Track which current ledgers were matched
  const matchedCurrentIndices = new Set<number>();
  const unmatchedPyLedgers: typeof previousYearRawLedgers = [];

  // Deep clone current ledgers
  const resultLedgers: LedgerItem[] = currentLedgers.map(l => ({
    ...l,
    // Preserve any existing PY values unless overwritten
  }));

  // Build lookup maps for current ledgers
  const normalizedCurrentMap = new Map<string, number>();
  const codeCurrentMap = new Map<string, number>();

  resultLedgers.forEach((l, idx) => {
    const norm = normalizeLedgerName(l.ledgerName);
    if (norm) normalizedCurrentMap.set(norm, idx);
    if (l.ledgerCode) codeCurrentMap.set(l.ledgerCode.trim().toLowerCase(), idx);
  });

  // Process each previous year ledger
  previousYearRawLedgers.forEach(py => {
    const pyDr = Math.round((py.debit || 0) * 100) / 100;
    const pyCr = Math.round((py.credit || 0) * 100) / 100;
    totalPyDebit += pyDr;
    totalPyCredit += pyCr;

    const normPyName = normalizeLedgerName(py.ledgerName);
    const pyCode = py.ledgerCode ? py.ledgerCode.trim().toLowerCase() : '';

    let matchedIdx: number | undefined = undefined;

    // 1. Match by code if available
    if (pyCode && codeCurrentMap.has(pyCode)) {
      matchedIdx = codeCurrentMap.get(pyCode);
    }

    // 2. Match by exact normalized name
    if (matchedIdx === undefined && normPyName && normalizedCurrentMap.has(normPyName)) {
      matchedIdx = normalizedCurrentMap.get(normPyName);
    }

    // 3. Match by best token similarity if score >= 0.75
    if (matchedIdx === undefined && normPyName) {
      let bestScore = 0;
      let bestIdx = -1;

      resultLedgers.forEach((cl, cIdx) => {
        if (matchedCurrentIndices.has(cIdx)) return;
        const score = calculateSimilarity(py.ledgerName, cl.ledgerName);
        if (score > bestScore && score >= 0.75) {
          bestScore = score;
          bestIdx = cIdx;
        }
      });

      if (bestIdx !== -1) {
        matchedIdx = bestIdx;
      }
    }

    if (matchedIdx !== undefined) {
      matchedCurrentIndices.add(matchedIdx);
      matchedCount++;

      const target = resultLedgers[matchedIdx];
      target.previousYearDebit = pyDr;
      target.previousYearCredit = pyCr;
      // Signed amount: net balance (Dr positive, Cr negative)
      target.previousYearAmount = pyDr - pyCr;
    } else {
      unmatchedPyLedgers.push(py);
    }
  });

  // 4. Handle unmatched previous year ledgers (accounts closed/zero in Current Year)
  if (unmatchedPyLedgers.length > 0) {
    // Classify unmatched PY ledgers using standard ICAI classification engine
    const rulesMap = savedRulesMap || getSavedRulesMap();
    const classifiedPyOnly = classifyLedgersWithRuleEngine(
      unmatchedPyLedgers.map(py => ({
        ...py,
        // For classification engine purposes:
        debit: py.debit,
        credit: py.credit,
      })),
      headConfigs,
      rulesMap
    );

    classifiedPyOnly.forEach(item => {
      addedCount++;
      const pyDr = Math.round((item.debit || 0) * 100) / 100;
      const pyCr = Math.round((item.credit || 0) * 100) / 100;

      resultLedgers.push({
        ...item,
        id: `py-prior-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        // In Current Year, this ledger has 0 balance:
        debit: 0,
        credit: 0,
        netBalance: 0,
        natureDrCr: pyDr >= pyCr ? 'Dr' : 'Cr',
        // In Previous Year, it holds the imported balance:
        previousYearDebit: pyDr,
        previousYearCredit: pyCr,
        previousYearAmount: pyDr - pyCr,
        userNotes: 'Prior-year ledger (closed or zero balance in current year)',
      });
    });
  }

  // Calculate Fixed Assets for Depreciation Schedule sync
  const extractedPyAssets: Partial<DepreciationAssetItem>[] = [];
  resultLedgers.forEach(l => {
    if (l.targetType === 'BALANCE_SHEET' && (l.headCode === 'A01' || l.scheduleNo === 8 || l.scheduleNo === '8')) {
      const isDeprContra = l.ledgerName.toLowerCase().includes('depreciation') || ((l.previousYearCredit || 0) > (l.previousYearDebit || 0));
      if (!isDeprContra && ((l.previousYearDebit || 0) > 0 || (l.previousYearCredit || 0) > 0)) {
        const netVal = Math.max(0, (l.previousYearDebit || 0) - (l.previousYearCredit || 0));
        extractedPyAssets.push({
          assetName: l.ledgerName,
          previousYearClosing: netVal,
        });
      }
    }
  });

  const pyDiff = Math.abs(totalPyDebit - totalPyCredit);
  const isPyBalanced = pyDiff < 0.01;

  return {
    mergedLedgers: resultLedgers,
    stats: {
      totalPyLedgers: previousYearRawLedgers.length,
      matchedCount,
      addedCount,
      totalPyDebit: Math.round(totalPyDebit * 100) / 100,
      totalPyCredit: Math.round(totalPyCredit * 100) / 100,
      pyDifference: Math.round(pyDiff * 100) / 100,
      isPyBalanced,
    },
    extractedPyAssets,
  };
}

/**
 * Clears all previous year balances from the ledgers list.
 * Removes any ledgers that were solely added for the previous year (where CY debit and credit are both 0).
 */
export function clearPreviousYearBalances(ledgers: LedgerItem[]): LedgerItem[] {
  return ledgers
    .filter(l => !(l.id.startsWith('py-prior-') && (l.debit === 0 && l.credit === 0)))
    .map(l => {
      const { previousYearDebit, previousYearCredit, previousYearAmount, ...rest } = l;
      return rest;
    });
}
