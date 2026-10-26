/**
 * Document Validity & Expiry Rules Engine
 * 
 * Implements statutory Indian validity requirements under:
 * - Passports Act, 1967: Adult passports valid for 10 years; minor passports valid for 5 years.
 *   Passports ALWAYS require an expiry date and can NEVER be classified as "Permanent".
 * - Motor Vehicles Act, 1988 (Sec 14) & Central Motor Vehicles Rules: Driving Licences require validity
 *   (historically up to age 50 or 20 years for non-transport; 3/5 years for transport/commercial).
 * - Insurance Act, 1938 & IRDAI Regulations: Requires separate tracking for Policy Renewal / Expiry
 *   and Premium Payment Due Date.
 * - Income-tax Act, 1961 (Sec 139A): Permanent Account Number (PAN) is a lifelong statutory identifier.
 * - Aadhaar (Targeted Delivery of Financial and Other Subsidies, Benefits and Services) Act, 2016:
 *   Aadhaar is a lifelong biometric identifier with no statutory expiry.
 * - Other documents: Birth certificates, academic degrees, property deeds have no prescribed expiry.
 *   Visas, PUC certificates, trade licences require explicit expiry dates.
 */

import { toDay, todayIST } from './calculations';

export type DocumentValidityStatus =
  | 'valid'
  | 'expiring_soon'
  | 'expired'
  | 'no_prescribed_expiry'
  | 'date_missing';

export interface ValidityRule {
  type: string;
  hasPrescribedExpiry: boolean;
  standardValidityYears?: number;
  label: string;
  statutoryNote: string;
  requiresIssueDate?: boolean;
}

export const DOCUMENT_VALIDITY_RULES: Record<string, ValidityRule> = {
  passport: {
    type: 'passport',
    hasPrescribedExpiry: true,
    standardValidityYears: 10,
    label: 'Passport',
    statutoryNote: 'Passports Act 1967 prescribes 10-year validity for adults (5 years for minors). Expiry date is mandatory.',
    requiresIssueDate: true,
  },
  licence: {
    type: 'licence',
    hasPrescribedExpiry: true,
    standardValidityYears: 20,
    label: 'Driving Licence',
    statutoryNote: 'Motor Vehicles Act 1988 prescribes fixed validity periods for non-transport and transport vehicles.',
    requiresIssueDate: true,
  },
  insurance: {
    type: 'insurance',
    hasPrescribedExpiry: true,
    label: 'Insurance Policy',
    statutoryNote: 'Insurance Act 1938 requires tracking policy coverage term and premium due dates separately.',
    requiresIssueDate: true,
  },
  policy: {
    type: 'policy',
    hasPrescribedExpiry: true,
    label: 'Insurance Policy',
    statutoryNote: 'Insurance Act 1938 requires tracking policy coverage term and premium due dates separately.',
    requiresIssueDate: true,
  },
  pan: {
    type: 'pan',
    hasPrescribedExpiry: false,
    label: 'PAN Card',
    statutoryNote: 'Section 139A Income-tax Act 1961: Permanent Account Number is a lifelong statutory identifier with no expiry date.',
    requiresIssueDate: false,
  },
  aadhaar: {
    type: 'aadhaar',
    hasPrescribedExpiry: false,
    label: 'Aadhaar Card',
    statutoryNote: 'Aadhaar Act 2016: 12-digit lifelong biometric identity with no statutory expiration date.',
    requiresIssueDate: false,
  },
  voter: {
    type: 'voter',
    hasPrescribedExpiry: false,
    label: 'Voter ID (EPIC)',
    statutoryNote: 'Election Commission of India: Electors Photo Identity Card is permanent lifelong photo ID.',
    requiresIssueDate: false,
  },
  ration: {
    type: 'ration',
    hasPrescribedExpiry: false,
    label: 'Ration Card',
    statutoryNote: 'National Food Security Act: Household ration card remains active subject to periodic verification.',
    requiresIssueDate: false,
  },
  degree: {
    type: 'degree',
    hasPrescribedExpiry: false,
    label: 'Educational Degree / Certificate',
    statutoryNote: 'Academic credentials and certificates are permanent records with no expiration.',
    requiresIssueDate: false,
  },
  birth_certificate: {
    type: 'birth_certificate',
    hasPrescribedExpiry: false,
    label: 'Birth Certificate',
    statutoryNote: 'Registration of Births and Deaths Act 1969: Permanent civil record.',
    requiresIssueDate: false,
  },
  property: {
    type: 'property',
    hasPrescribedExpiry: false,
    label: 'Property Title / Deed',
    statutoryNote: 'Registered ownership title remains permanent until conveyance.',
    requiresIssueDate: false,
  },
  puc: {
    type: 'puc',
    hasPrescribedExpiry: true,
    standardValidityYears: 1,
    label: 'Pollution Under Control (PUC)',
    statutoryNote: 'Central Motor Vehicles Rules prescribe 6-month or 1-year validity for PUC certificates.',
    requiresIssueDate: true,
  },
  visa: {
    type: 'visa',
    hasPrescribedExpiry: true,
    label: 'Visa / Travel Permit',
    statutoryNote: 'Immigration regulations prescribe fixed visa validity and stay duration.',
    requiresIssueDate: true,
  },
  other: {
    type: 'other',
    hasPrescribedExpiry: false,
    label: 'General Record',
    statutoryNote: 'General record: expiry tracking is optional depending on document requirements.',
    requiresIssueDate: false,
  },
};

/**
 * Returns whether a document category has a statutory prescribed expiry date
 */
export function hasPrescribedExpiry(docType?: string, title?: string): boolean {
  const normType = (docType || '').toLowerCase().trim();
  const normTitle = (title || '').toLowerCase().trim();

  // PAN and Aadhaar NEVER have prescribed expiry
  if (
    normType === 'pan' ||
    normType === 'aadhaar' ||
    /pan|aadhaar|aadhar/i.test(normTitle)
  ) {
    return false;
  }

  // Passports, Driving Licences, Insurance ALWAYS have prescribed expiry
  if (
    normType === 'passport' ||
    normType === 'licence' ||
    normType === 'insurance' ||
    normType === 'policy' ||
    normType === 'puc' ||
    normType === 'visa' ||
    /passport|driving licence|\bdl\b|insurance|mediclaim|puc|visa/i.test(normTitle)
  ) {
    return true;
  }

  const rule = DOCUMENT_VALIDITY_RULES[normType];
  return rule ? rule.hasPrescribedExpiry : false;
}

/**
 * Determines the comprehensive validity status for any document
 */
export function getDocumentValidityStatus(
  docType?: string,
  expires?: string,
  issueDate?: string,
  alertOffsets: number[] = [60, 30, 7]
): {
  status: DocumentValidityStatus;
  label: string;
  description: string;
  daysRemaining?: number;
} {
  const isExpiringDoc = hasPrescribedExpiry(docType);

  // If the document has NO prescribed expiry (e.g. PAN, Aadhaar)
  if (!isExpiringDoc) {
    return {
      status: 'no_prescribed_expiry',
      label: 'No Prescribed Expiry',
      description: 'Lifelong statutory document with no expiration date.',
    };
  }

  // If it requires an expiry date, but none is recorded (or was incorrectly set as "Permanent")
  if (!expires || !expires.trim() || /permanent|no expiry|na|n\/a|lifetime/i.test(expires)) {
    return {
      status: 'date_missing',
      label: 'Expiry Date Required',
      description: 'Mandatory expiry date has not been recorded for this document.',
    };
  }

  // ISO date evaluation
  const today = todayIST();
  const todayMs = toDay(today);
  const expiryMs = toDay(expires);
  const DAY = 86400000;
  const daysDiff = Math.round((expiryMs - todayMs) / DAY);

  if (daysDiff < 0) {
    return {
      status: 'expired',
      label: 'Expired',
      description: `Expired ${Math.abs(daysDiff)} day${Math.abs(daysDiff) === 1 ? '' : 's'} ago. Renewal required.`,
      daysRemaining: daysDiff,
    };
  }

  const maxAlert = Math.max(...alertOffsets, 30);
  if (daysDiff <= maxAlert) {
    return {
      status: 'expiring_soon',
      label: daysDiff === 0 ? 'Expires Today' : `Expires in ${daysDiff} Days`,
      description: `Document expires on ${expires}. Advance renewal recommended.`,
      daysRemaining: daysDiff,
    };
  }

  return {
    status: 'valid',
    label: 'Valid',
    description: `Document is active and valid until ${expires}.`,
    daysRemaining: daysDiff,
  };
}

/**
 * Validates date relationships (e.g., expiry must not precede issue date)
 */
export function validateDocumentDates(
  issueDate?: string,
  expiryDate?: string
): { isValid: boolean; warning?: string; error?: string } {
  if (!issueDate || !expiryDate) {
    return { isValid: true };
  }

  const issueMs = toDay(issueDate);
  const expiryMs = toDay(expiryDate);

  if (expiryMs < issueMs) {
    return {
      isValid: false,
      error: `Expiry date (${expiryDate}) cannot be earlier than issue date (${issueDate}).`,
    };
  }

  if (expiryMs === issueMs) {
    return {
      isValid: false,
      warning: 'Expiry date is the same as issue date. Please verify.',
    };
  }

  return { isValid: true };
}

/**
 * Computes a suggested expiry date for user confirmation based on Indian statutory conventions.
 * Never silently applies; always returns a proposed date and rationale for user confirmation.
 */
export function suggestExpiryDate(
  docType: string,
  issueDate: string
): { suggestedExpiry?: string; rationale?: string } | null {
  if (!issueDate || !/^\d{4}-\d{2}-\d{2}$/.test(issueDate)) return null;

  const rule = DOCUMENT_VALIDITY_RULES[docType.toLowerCase()];
  if (!rule || !rule.standardValidityYears) return null;

  const y = +issueDate.slice(0, 4);
  const m = issueDate.slice(5, 7);
  const d = issueDate.slice(8, 10);

  // Passports typically expire exactly 10 years minus 1 day, or 10 years from issue date
  const targetYear = y + rule.standardValidityYears;
  const suggestedExpiry = `${targetYear}-${m}-${d}`;

  return {
    suggestedExpiry,
    rationale: `Standard ${rule.standardValidityYears}-year validity from issue date (${rule.statutoryNote})`,
  };
}
