export interface CurrencyInfo {
  code: string;
  name: string;
  symbol: string;
  decimals: number;
}

export const SUPPORTED_CURRENCIES: Record<string, CurrencyInfo> = {
  AED: { code: "AED", name: "UAE Dirham", symbol: "AED", decimals: 2 },
  USD: { code: "USD", name: "US Dollar", symbol: "$", decimals: 2 },
  EUR: { code: "EUR", name: "Euro", symbol: "€", decimals: 2 },
  GBP: { code: "GBP", name: "British Pound", symbol: "£", decimals: 2 },
  INR: { code: "INR", name: "Indian Rupee", symbol: "₹", decimals: 2 },
  SAR: { code: "SAR", name: "Saudi Riyal", symbol: "SAR", decimals: 2 },
  QAR: { code: "QAR", name: "Qatari Riyal", symbol: "QAR", decimals: 2 },
  KWD: { code: "KWD", name: "Kuwaiti Dinar", symbol: "KWD", decimals: 3 },
  BHD: { code: "BHD", name: "Bahraini Dinar", symbol: "BHD", decimals: 3 },
  OMR: { code: "OMR", name: "Omani Rial", symbol: "OMR", decimals: 3 },
  PKR: { code: "PKR", name: "Pakistani Rupee", symbol: "PKR", decimals: 2 },
  SGD: { code: "SGD", name: "Singapore Dollar", symbol: "S$", decimals: 2 },
  AUD: { code: "AUD", name: "Australian Dollar", symbol: "A$", decimals: 2 },
  CAD: { code: "CAD", name: "Canadian Dollar", symbol: "C$", decimals: 2 },
  JPY: { code: "JPY", name: "Japanese Yen", symbol: "¥", decimals: 0 },
  CHF: { code: "CHF", name: "Swiss Franc", symbol: "CHF", decimals: 2 },
};

export const DEFAULT_CURRENCY = "AED";

export function getCurrencyInfo(code?: string): CurrencyInfo {
  const upper = (code || DEFAULT_CURRENCY).toUpperCase();
  return (
    SUPPORTED_CURRENCIES[upper] ?? {
      code: upper,
      name: upper,
      symbol: upper,
      decimals: 2,
    }
  );
}

/**
 * Converts user-entered decimal/number to exact integer minor units (cents, fils, yen).
 * e.g. for USD (2 dec): 12.34 -> 1234
 * for JPY (0 dec): 500 -> 500
 * for KWD (3 dec): 1.500 -> 1500
 */
export function toMinorUnits(amount: number | string, currency: string = DEFAULT_CURRENCY): number {
  const info = getCurrencyInfo(currency);
  const factor = Math.pow(10, info.decimals);
  const clean = typeof amount === "string" ? parseFloat(amount.trim()) : amount;
  if (!Number.isFinite(clean) || Number.isNaN(clean)) return 0;
  return Math.round(clean * factor);
}

/**
 * Converts integer minor units back to standard float.
 */
export function fromMinorUnits(units: number, currency: string = DEFAULT_CURRENCY): number {
  const info = getCurrencyInfo(currency);
  const factor = Math.pow(10, info.decimals);
  return units / factor;
}

/**
 * Formats minor units into localized currency string.
 */
export function formatMoney(units: number, currency: string = DEFAULT_CURRENCY): string {
  const info = getCurrencyInfo(currency);
  const factor = Math.pow(10, info.decimals);
  const val = units / factor;
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: info.code,
      minimumFractionDigits: info.decimals,
      maximumFractionDigits: info.decimals,
    }).format(val);
  } catch {
    return `${info.symbol} ${val.toFixed(info.decimals)}`;
  }
}
