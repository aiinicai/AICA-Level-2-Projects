/**
 * Hospital CFO Copilot - Data-Driven Department & Revenue Centre Mapping Utility
 *
 * Replaces static synthetic dataset dependencies with data-driven mapping
 * that dynamically discovers departments from uploaded masters / records
 * and provides robust, configurable categorisation.
 */

import { HospitalDepartment } from '../types';

/**
 * Standard fallbacks when no specific master configuration is supplied.
 * Note: The system does NOT assume these are the only departments.
 */
const DEFAULT_REVENUE_CENTRE_RULES: Array<{
  keywords: string[];
  department: string;
}> = [
  { keywords: ['lab', 'patholog', 'biochem', 'microbio', 'hematol'], department: 'Laboratory' },
  { keywords: ['pharm', 'med', 'dispensary', 'drug', 'inject'], department: 'Pharmacy' },
  { keywords: ['radio', 'imaging', 'scan', 'x-ray', 'xray', 'mri', 'ct scan', 'ultrasound', 'usg'], department: 'Radiology' },
  { keywords: ['ot', 'surg', 'operation theatre', 'anesthes', 'theatre'], department: 'OT/Surgery' },
  { keywords: ['icu', 'ccu', 'critical', 'nicu', 'picu', 'hight dependency', 'hight-dependency', 'micu'], department: 'ICU' },
  { keywords: ['room', 'nurs', 'ward', 'operat', 'bed', 'general ward', 'deluxe', 'private ward'], department: 'Operations' },
  { keywords: ['consum', 'implant', 'store', 'devices', 'prosthesis', 'mesh'], department: 'Stores' },
  { keywords: ['finance', 'admin', 'registration', 'consult', 'opd', 'admission'], department: 'Finance/Admin' },
];

/**
 * Dynamically maps a Revenue Centre name to a Department.
 * If knownDepartments is provided from active Firestore/imported records,
 * it attempts to match directly against the hospital's actual department master first.
 */
export function mapRevenueCentreToDepartment(
  revCentre: string | undefined | null,
  knownDepartments?: string[]
): string {
  if (!revCentre) return 'General';
  const norm = revCentre.trim().toLowerCase();

  // 1. Direct match with known departments from uploaded hospital data
  if (knownDepartments && knownDepartments.length > 0) {
    const directMatch = knownDepartments.find(
      (dept) => dept.toLowerCase() === norm || norm.includes(dept.toLowerCase())
    );
    if (directMatch) return directMatch;
  }

  // 2. Keyword heuristic mapping
  for (const rule of DEFAULT_REVENUE_CENTRE_RULES) {
    if (rule.keywords.some((kw) => norm.includes(kw))) {
      // If known departments has a matching standard department, return that exact string
      if (knownDepartments && knownDepartments.length > 0) {
        const matched = knownDepartments.find(
          (kd) => kd.toLowerCase() === rule.department.toLowerCase()
        );
        if (matched) return matched;
      }
      return rule.department;
    }
  }

  // 3. Fallback: If revenue centre itself looks like a department name, use it cleanly
  if (revCentre.length > 2 && revCentre.length < 35 && !revCentre.includes('/')) {
    return revCentre.trim();
  }

  return 'Finance/Admin';
}

/**
 * Extracts all unique active departments from an encounter or billing list.
 */
export function extractUniqueDepartments(
  encounters?: Array<{ Department?: string }>,
  budgetRecords?: Array<{ Department?: string }>
): string[] {
  const depts = new Set<string>();
  if (encounters) {
    encounters.forEach((e) => {
      if (e.Department && e.Department.trim()) depts.add(e.Department.trim());
    });
  }
  if (budgetRecords) {
    budgetRecords.forEach((b) => {
      if (b.Department && b.Department.trim()) depts.add(b.Department.trim());
    });
  }
  return Array.from(depts);
}
