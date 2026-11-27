import { Transaction, TransactionType } from '../types/finance';

export interface DuplicateCheckResult {
  isDuplicate: boolean;
  matchedTransaction?: Transaction;
  confidence: 'exact' | 'high' | 'none';
  reason?: string;
}

export interface CandidateTransaction {
  amount: number;
  originalAmount?: number;
  originalCurrency?: string;
  currency?: string;
  merchant?: string;
  bankName?: string;
  date?: string;
  time?: string;
  cardMask?: string;
  type?: TransactionType;
  rawNotificationText?: string;
  source?: string;
}

/**
 * Normalizes merchant names for fuzzy matching across push notifications and SMS
 * e.g., "Amazon.ae", "AMAZON PAYMENTS", "Amazon" all normalize to "amazon"
 */
function normalizeForComparison(str: string): string {
  return str
    .toLowerCase()
    .replace(/\b(uae|ae|dubai|abu dhabi|com|online|payments|pos|store|llc)\b/g, '')
    .replace(/[^a-z0-9]/g, '')
    .trim();
}

/**
 * Parses time string (e.g. "12:05 PM", "14:30") into minutes since midnight
 */
function parseTimeToMinutes(timeStr?: string): number | null {
  if (!timeStr) return null;
  const match = timeStr.match(/(\d{1,2}):(\d{2})(?:\s*(AM|PM))?/i);
  if (!match) return null;
  let hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  const ampm = match[3]?.toUpperCase();

  if (ampm === 'PM' && hours < 12) hours += 12;
  if (ampm === 'AM' && hours === 12) hours = 0;

  return hours * 60 + minutes;
}

/**
 * Checks if incoming bank notification or SMS alert matches an existing transaction,
 * eliminating duplicate entries when banks dispatch both push notification and SMS.
 */
export function findDuplicateTransaction(
  incoming: CandidateTransaction,
  existingTransactions: Transaction[]
): DuplicateCheckResult {
  if (!incoming || !incoming.amount || incoming.amount <= 0 || !existingTransactions || existingTransactions.length === 0) {
    return { isDuplicate: false, confidence: 'none' };
  }

  const incomingType = incoming.type || 'expense';
  const incomingDate = incoming.date || new Date().toISOString().split('T')[0];
  const incomingMerchantNorm = normalizeForComparison(incoming.merchant || '');
  const incomingTimeMin = parseTimeToMinutes(incoming.time);
  const incomingCardLast4 = (incoming.cardMask || incoming.rawNotificationText || '').match(/(?:ending|card|acct|no\.?)\s*(?:x+|\*+)?([0-9]{4})/i)?.[1];

  for (const existing of existingTransactions) {
    const existingType = existing.type || 'expense';

    // Rule 1: Type must match (an income/salary is not duplicate of an expense)
    if (existingType !== incomingType) continue;

    // Rule 2: Amount must match within 0.05 AED tolerance
    const amountDiff = Math.abs(existing.amount - incoming.amount);
    const amountsMatch = amountDiff < 0.05;

    // Check foreign original amount match if applicable (e.g. USD 50.00)
    const foreignAmountsMatch = Boolean(
      incoming.originalAmount &&
      existing.originalAmount &&
      Math.abs(incoming.originalAmount - existing.originalAmount) < 0.05 &&
      incoming.originalCurrency === existing.originalCurrency
    );

    if (!amountsMatch && !foreignAmountsMatch) {
      continue;
    }

    // Rule 3: Date proximity check (same date or within 1 calendar day due to midnight transactions)
    const sameDate = existing.date === incomingDate;
    let daysDiff = 0;
    try {
      const d1 = new Date(existing.date).getTime();
      const d2 = new Date(incomingDate).getTime();
      daysDiff = Math.abs((d1 - d2) / (1000 * 60 * 60 * 24));
    } catch {
      daysDiff = sameDate ? 0 : 999;
    }

    if (!sameDate && daysDiff > 1.1) {
      continue;
    }

    // Rule 4: Check if raw notification text is verbatim identical
    if (
      incoming.rawNotificationText &&
      existing.rawNotificationText &&
      incoming.rawNotificationText.trim().toLowerCase() === existing.rawNotificationText.trim().toLowerCase()
    ) {
      return {
        isDuplicate: true,
        matchedTransaction: existing,
        confidence: 'exact',
        reason: 'Identical alert notification text already recorded'
      };
    }

    // Rule 5: Card Number / Mask comparison
    const existingCardLast4 = (existing.notes || existing.rawNotificationText || '').match(/(?:ending|card|acct|no\.?)\s*(?:x+|\*+)?([0-9]{4})/i)?.[1];
    const sameCard = Boolean(
      incomingCardLast4 &&
      existingCardLast4 &&
      incomingCardLast4 === existingCardLast4
    );

    // Rule 6: Merchant comparison
    const existingMerchantNorm = normalizeForComparison(existing.merchant || '');
    const merchantsMatch =
      (incomingMerchantNorm && existingMerchantNorm && (
        incomingMerchantNorm === existingMerchantNorm ||
        incomingMerchantNorm.includes(existingMerchantNorm) ||
        existingMerchantNorm.includes(incomingMerchantNorm)
      )) ||
      (!incomingMerchantNorm || !existingMerchantNorm || incomingMerchantNorm === 'unknownmerchant' || existingMerchantNorm === 'unknownmerchant');

    // Rule 7: Bank match
    const banksMatch = Boolean(
      incoming.bankName &&
      existing.bankName &&
      (incoming.bankName.toLowerCase().includes(existing.bankName.toLowerCase()) ||
       existing.bankName.toLowerCase().includes(incoming.bankName.toLowerCase()))
    );

    // Rule 8: Time window check
    // SMS and Push Notifications arrive within 0 - 25 minutes of each other.
    const existingTimeMin = parseTimeToMinutes(existing.time);
    let withinTimeWindow = true;
    if (sameDate && incomingTimeMin !== null && existingTimeMin !== null) {
      const minutesDiff = Math.abs(incomingTimeMin - existingTimeMin);
      withinTimeWindow = minutesDiff <= 25; // within 25 minutes
    }

    // Distinct Merchant Guard:
    // If both merchants are known and clearly different, they are definitely NOT duplicates
    const bothKnownMerchants = Boolean(
      incomingMerchantNorm &&
      existingMerchantNorm &&
      incomingMerchantNorm !== 'unknownmerchant' &&
      existingMerchantNorm !== 'unknownmerchant'
    );
    const areDifferentMerchants =
      bothKnownMerchants &&
      incomingMerchantNorm !== existingMerchantNorm &&
      !incomingMerchantNorm.includes(existingMerchantNorm) &&
      !existingMerchantNorm.includes(incomingMerchantNorm);

    if (areDifferentMerchants) {
      continue;
    }

    // CRITERIA FOR DUPLICATE:
    // A. Same date, same amount, within time window, and merchant matches
    if (sameDate && withinTimeWindow && merchantsMatch) {
      return {
        isDuplicate: true,
        matchedTransaction: existing,
        confidence: 'high',
        reason: `Matched AED ${incoming.amount.toFixed(2)} at ${existing.merchant} (${existing.date}${existing.time ? ' ' + existing.time : ''})`
      };
    }

    // B. Same date, exact card and bank match
    if (sameDate && sameCard && banksMatch) {
      return {
        isDuplicate: true,
        matchedTransaction: existing,
        confidence: 'high',
        reason: `Matched AED ${incoming.amount.toFixed(2)} on card ending ${incomingCardLast4}`
      };
    }

    // C. Verbatim merchant and amount on same date
    if (sameDate && incomingMerchantNorm && existingMerchantNorm && incomingMerchantNorm === existingMerchantNorm && withinTimeWindow) {
      return {
        isDuplicate: true,
        matchedTransaction: existing,
        confidence: 'high',
        reason: `Duplicate transaction: AED ${incoming.amount.toFixed(2)} at ${existing.merchant}`
      };
    }
  }

  return { isDuplicate: false, confidence: 'none' };
}

/**
 * Scans a transaction list and cleans up any existing historical duplicates
 */
export function removeExistingDuplicates(transactions: Transaction[]): {
  cleaned: Transaction[];
  removedCount: number;
} {
  const seen: Transaction[] = [];
  let removedCount = 0;

  for (const tx of transactions) {
    const isDup = findDuplicateTransaction(tx, seen).isDuplicate;
    if (isDup) {
      removedCount++;
    } else {
      seen.push(tx);
    }
  }

  return { cleaned: seen, removedCount };
}
