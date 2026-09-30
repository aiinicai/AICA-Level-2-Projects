/**
 * Formatting and Validation Utilities for Indian Accounting & Receivables
 */

/**
 * Formats a number as Indian Rupees (INR) with standard Indian comma grouping:
 * e.g., 100000 -> ₹1,00,000.00
 */
export function formatINR(amount: number | null | undefined, includeDecimals = true): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0.00';
  }
  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);
  
  const parts = absAmount.toFixed(includeDecimals ? 2 : 0).split('.');
  let integerPart = parts[0];
  const decimalPart = parts[1] ? `.${parts[1]}` : '';

  // Indian numbering system formatting: last 3 digits, then groups of 2
  if (integerPart.length > 3) {
    const lastThree = integerPart.substring(integerPart.length - 3);
    const otherNumbers = integerPart.substring(0, integerPart.length - 3);
    const formattedOther = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    integerPart = `${formattedOther},${lastThree}`;
  }

  return `${isNegative ? '-' : ''}₹${integerPart}${decimalPart}`;
}

/**
 * Compact Indian Currency Notation:
 * 1,00,00,000 -> ₹1.00 Cr
 * 1,00,000 -> ₹1.00 L
 * 1,000 -> ₹1 K
 */
export function formatINRCompact(amount: number | null | undefined): string {
  if (amount === null || amount === undefined || isNaN(amount)) {
    return '₹0';
  }
  const isNegative = amount < 0;
  const abs = Math.abs(amount);

  let formatted = '';
  if (abs >= 10000000) {
    formatted = `${(abs / 10000000).toFixed(2)} Cr`;
  } else if (abs >= 100000) {
    formatted = `${(abs / 100000).toFixed(2)} L`;
  } else if (abs >= 1000) {
    formatted = `${(abs / 1000).toFixed(1)} K`;
  } else {
    formatted = abs.toFixed(0);
  }

  return `${isNegative ? '-' : ''}₹${formatted}`;
}

/**
 * Formats standard ISO date to DD MMM YYYY (e.g. 15 Apr 2026)
 */
export function formatDate(dateString: string | null | undefined): string {
  if (!dateString) return '-';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return date.toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric'
    });
  } catch {
    return dateString;
  }
}

/**
 * Calculate difference in days between two dates (positive if date2 is after date1)
 */
export function daysBetween(date1Str: string, date2Str: string): number {
  const d1 = new Date(date1Str);
  const d2 = new Date(date2Str);
  const diffTime = d2.getTime() - d1.getTime();
  return Math.floor(diffTime / (1000 * 60 * 60 * 24));
}

/**
 * Validates Indian GSTIN (15 alphanumeric characters)
 * 2 digits state code + 10 digits PAN + 1 entity code + 'Z' + 1 check digit
 */
export function isValidGSTIN(gstin: string): boolean {
  if (!gstin) return false;
  const regex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
  return regex.test(gstin.trim().toUpperCase());
}

/**
 * Validates Indian PAN (10 alphanumeric characters)
 */
export function isValidPAN(pan: string): boolean {
  if (!pan) return false;
  const regex = /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/;
  return regex.test(pan.trim().toUpperCase());
}

/**
 * Extract PAN from GSTIN if valid
 */
export function extractPANFromGSTIN(gstin: string): string {
  if (!gstin || gstin.length < 12) return '';
  return gstin.substring(2, 12).toUpperCase();
}

/**
 * Calculates due date based on invoice date and credit payment terms
 */
export function calculateDueDate(invoiceDateStr: string, paymentTermsDays: number): string {
  try {
    const parts = invoiceDateStr.split('-');
    const year = parseInt(parts[0], 10);
    const month = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    const d = new Date(year, month, day);
    d.setDate(d.getDate() + paymentTermsDays);
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const dayStr = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${dayStr}`;
  } catch {
    return invoiceDateStr;
  }
}

