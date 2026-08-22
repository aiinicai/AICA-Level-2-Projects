/**
 * Validation rules per placeholder type. Patterns are defined here as the
 * single source of truth but are intentionally simple to swap/extend -
 * for full configurability without code changes, patterns could instead be
 * loaded from the Setting table (key: "validation.<type>"); left as a
 * straightforward extension point for Phase 2.
 */
const PATTERNS: Record<string, RegExp> = {
  Email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PAN: /^[A-Z]{5}[0-9]{4}[A-Z]$/,
  GSTIN: /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/,
  Mobile: /^[6-9][0-9]{9}$/,
  PinCode: /^[1-9][0-9]{5}$/,
  Date: /^\d{2}\/\d{2}\/\d{4}$/, // DD/MM/YYYY, entered as-is, never auto-reformatted
};

export interface ValidationResult {
  valid: boolean;
  message?: string;
}

export function validatePlaceholderValue(validationType: string, value: string): ValidationResult {
  if (validationType === 'Text' || validationType === 'Image') return { valid: true };
  const pattern = PATTERNS[validationType];
  if (!pattern) return { valid: true };
  if (!value) return { valid: false, message: 'This field is required.' };
  if (!pattern.test(value.toUpperCase() === value ? value : value)) {
    // For PAN/GSTIN, compare case-insensitively but keep user's original casing in output
    if ((validationType === 'PAN' || validationType === 'GSTIN') && pattern.test(value.toUpperCase())) {
      return { valid: true };
    }
    return { valid: false, message: `Invalid ${validationType} format.` };
  }
  return { valid: true };
}
