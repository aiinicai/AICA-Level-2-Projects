import { DocumentPrefix } from './types';

interface SequenceStore {
  [key: string]: number; // e.g. "PINV-2026": 12
}

const SEQUENCE_KEY = 'medicore_sequences';

function getSequenceStore(): SequenceStore {
  try {
    const raw = localStorage.getItem(SEQUENCE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // fallback
  }
  return {};
}

function saveSequenceStore(store: SequenceStore): void {
  localStorage.setItem(SEQUENCE_KEY, JSON.stringify(store));
}

/**
 * Get next gapless sequential number
 * Example: getNextSequenceNumber('PINV', 2026) -> "PINV-2026-000042"
 */
export function getNextSequenceNumber(prefix: DocumentPrefix, year: number = 2026): string {
  const store = getSequenceStore();
  const key = `${prefix}-${year}`;
  const current = store[key] || 0;
  const next = current + 1;
  store[key] = next;
  saveSequenceStore(store);
  return `${prefix}-${year}-${String(next).padStart(6, '0')}`;
}

/**
 * Preview next sequence without incrementing
 */
export function peekNextSequenceNumber(prefix: DocumentPrefix, year: number = 2026): string {
  const store = getSequenceStore();
  const key = `${prefix}-${year}`;
  const current = store[key] || 0;
  return `${prefix}-${year}-${String(current + 1).padStart(6, '0')}`;
}

/**
 * Get next Asset Tag: FA-000001
 */
export function getNextAssetTag(): string {
  const store = getSequenceStore();
  const key = 'FA-TAG';
  const current = store[key] || 0;
  const next = current + 1;
  store[key] = next;
  saveSequenceStore(store);
  return `FA-${String(next).padStart(6, '0')}`;
}

export function getAllCurrentSequences(): { prefix: string; year: number; current: number }[] {
  const store = getSequenceStore();
  const result: { prefix: string; year: number; current: number }[] = [];
  for (const [key, val] of Object.entries(store)) {
    const parts = key.split('-');
    result.push({
      prefix: parts[0],
      year: parseInt(parts[1], 10) || 2026,
      current: val,
    });
  }
  return result;
}

export function resetSequences(initialCounts?: Record<string, number>): void {
  if (initialCounts) {
    saveSequenceStore(initialCounts);
  } else {
    localStorage.removeItem(SEQUENCE_KEY);
  }
}
