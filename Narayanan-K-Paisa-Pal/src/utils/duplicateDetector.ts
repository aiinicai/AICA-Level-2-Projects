import { AppRow, Kind } from '../types';

export interface DuplicateCheckResult {
  isDuplicate: boolean;
  matchedRow?: AppRow;
  reason?: string;
  field?: string;
}

export function normalizeRef(s: any): string {
  if (s == null) return '';
  return String(s).replace(/[\s\-_./\\#:]+/g, '').toLowerCase().trim();
}

/**
 * Checks if a given item (draft or form entry) is a duplicate of an existing row.
 */
export function findDuplicate(
  existingRows: AppRow[],
  kind: Kind,
  data: Record<string, any>,
  excludeId?: string
): DuplicateCheckResult {
  if (!existingRows || !existingRows.length || !data) {
    return { isDuplicate: false };
  }

  // Filter candidates of same kind and not current row
  const candidates = existingRows.filter(
    (r) => r.kind === kind && (!excludeId || r.id !== excludeId)
  );

  // 1. For Records ('rec'):
  if (kind === 'rec') {
    const num = normalizeRef(data.number);
    const title = (data.title || '').trim().toLowerCase();
    const holder = (data.holder || '').trim().toLowerCase();

    // Check by document number (e.g. same Passport number, PAN number, DL number)
    if (num && num.length >= 4) {
      const match = candidates.find((r) => normalizeRef(r.data?.number) === num);
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'number',
          reason: `Document number "${data.number}" already exists in Records ("${match.data?.title || 'Record'}" for ${match.data?.holder || 'unspecified'}).`,
        };
      }
    }

    // Check by same title + same holder (e.g. Passport for Irin Joseph)
    if (title && holder) {
      const match = candidates.find(
        (r) =>
          (r.data?.title || '').trim().toLowerCase() === title &&
          (r.data?.holder || '').trim().toLowerCase() === holder
      );
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'holder_title',
          reason: `A record "${data.title}" for "${data.holder}" already exists in Records.`,
        };
      }
    }
  }

  // 2. For Investments ('inv'):
  if (kind === 'inv') {
    const ref = normalizeRef(data.ref);
    const name = (data.name || '').trim().toLowerCase();
    const invested = Number(data.invested) || 0;

    // Check by account / certificate / folio number
    if (ref && ref.length >= 4) {
      const match = candidates.find((r) => normalizeRef(r.data?.ref) === ref);
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'ref',
          reason: `Account/certificate number "${data.ref}" already exists in Investments ("${match.data?.name}").`,
        };
      }
    }

    // Check by exact name + invested amount
    if (name && invested > 0) {
      const match = candidates.find(
        (r) =>
          (r.data?.name || '').trim().toLowerCase() === name &&
          Number(r.data?.invested) === invested
      );
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'name_amount',
          reason: `An investment "${data.name}" with invested amount ₹${invested.toLocaleString('en-IN')} already exists.`,
        };
      }
    }
  }

  // 3. For Due Dates ('due'):
  if (kind === 'due') {
    const ref = normalizeRef(data.ref);
    const name = (data.name || '').trim().toLowerCase();
    const due = (data.due || '').trim();

    if (ref && ref.length >= 4) {
      const match = candidates.find((r) => normalizeRef(r.data?.ref) === ref);
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'ref',
          reason: `Account / consumer number "${data.ref}" already exists in Due Dates ("${match.data?.name}").`,
        };
      }
    }

    if (name && due) {
      const match = candidates.find(
        (r) =>
          (r.data?.name || '').trim().toLowerCase() === name &&
          (r.data?.due || '').trim() === due
      );
      if (match) {
        return {
          isDuplicate: true,
          matchedRow: match,
          field: 'name_due',
          reason: `A due item for "${data.name}" due on ${data.due} already exists.`,
        };
      }
    }
  }

  return { isDuplicate: false };
}
