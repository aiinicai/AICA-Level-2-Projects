/**
 * Format number to Indian Rupee (INR) currency representation
 * Uses Indian numbering format: 1,00,000 / 10,00,000
 */
export function formatINR(amount: number, compact = false): string {
  if (isNaN(amount) || amount === null || amount === undefined) return '₹0';
  
  if (compact) {
    if (Math.abs(amount) >= 10000000) {
      return `₹${(amount / 10000000).toFixed(2)} Cr`;
    }
    if (Math.abs(amount) >= 100000) {
      return `₹${(amount / 100000).toFixed(2)} L`;
    }
  }

  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format number to Australian Dollar (AUD)
 */
export function formatAUD(amount: number, compact = false): string {
  if (isNaN(amount) || amount === null || amount === undefined) return 'A$0';

  if (compact && Math.abs(amount) >= 1000000) {
    return `A$${(amount / 1000000).toFixed(2)}M`;
  }
  if (compact && Math.abs(amount) >= 1000) {
    return `A$${(amount / 1000).toFixed(1)}k`;
  }

  return new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: 'AUD',
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Convert INR to AUD using specified rate (e.g. 0.0182)
 */
export function convertInrToAud(inrAmount: number, rate: number): number {
  if (!inrAmount || !rate) return 0;
  return inrAmount * rate;
}

/**
 * Convert AUD to INR (inverse)
 */
export function convertAudToInr(audAmount: number, rate: number): number {
  if (!audAmount || !rate) return 0;
  return audAmount / rate;
}

/**
 * Format variance percentage
 */
export function formatVariance(current: number, prior: number): {
  percent: number;
  formatted: string;
  isPositive: boolean;
  isNeutral: boolean;
} {
  if (!prior || prior === 0) {
    if (current > 0) return { percent: 100, formatted: '+100%', isPositive: true, isNeutral: false };
    return { percent: 0, formatted: '0.0%', isPositive: false, isNeutral: true };
  }

  const diff = current - prior;
  const pct = (diff / prior) * 100;
  const formatted = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;

  return {
    percent: pct,
    formatted,
    isPositive: pct > 0,
    isNeutral: Math.abs(pct) < 0.01,
  };
}

/**
 * Format date in Indian Standard Time (IST)
 */
export function formatIST(dateString?: string, includeTime = true): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;

    const options: Intl.DateTimeFormatOptions = {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      ...(includeTime
        ? {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
          }
        : {}),
    };

    const formatted = new Intl.DateTimeFormat('en-GB', options).format(date);
    return includeTime ? `${formatted} IST` : formatted;
  } catch (e) {
    return dateString;
  }
}

/**
 * Format simple date YYYY-MM-DD to readable date
 */
export function formatDate(dateString?: string): string {
  if (!dateString) return '—';
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return dateString;
    return new Intl.DateTimeFormat('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    }).format(date);
  } catch {
    return dateString;
  }
}
