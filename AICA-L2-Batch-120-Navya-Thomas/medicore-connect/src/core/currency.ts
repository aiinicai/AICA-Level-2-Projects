import Decimal from 'decimal.js';

Decimal.set({ precision: 20, rounding: Decimal.ROUND_HALF_UP });

export function round2(value: number | string | Decimal): number {
  return new Decimal(value || 0).toDecimalPlaces(2, Decimal.ROUND_HALF_UP).toNumber();
}

export function toDecimal(value: number | string | Decimal): Decimal {
  return new Decimal(value || 0);
}

export function addMoney(a: number | string, b: number | string): number {
  return new Decimal(a || 0).plus(b || 0).toDecimalPlaces(2).toNumber();
}

export function subMoney(a: number | string, b: number | string): number {
  return new Decimal(a || 0).minus(b || 0).toDecimalPlaces(2).toNumber();
}

export function mulMoney(a: number | string, b: number | string): number {
  return new Decimal(a || 0).times(b || 0).toDecimalPlaces(2).toNumber();
}

export function divMoney(a: number | string, b: number | string): number {
  if (new Decimal(b || 0).isZero()) return 0;
  return new Decimal(a || 0).dividedBy(b).toDecimalPlaces(2).toNumber();
}

/**
 * Format currency in AED
 * Example: 1234567.89 -> "1,234,567.89"
 * If in brackets mode (for financial reports): negative -> "(1,234,567.89)"
 */
export function formatAED(
  amount: number | string | undefined | null,
  options?: { showCurrency?: boolean; useBracketsForNegative?: boolean; zeroAsDash?: boolean; decimals?: number }
): string {
  if (amount === undefined || amount === null || isNaN(Number(amount))) {
    return options?.zeroAsDash ? '—' : '0.00';
  }

  const num = round2(amount);
  if (options?.zeroAsDash && Math.abs(num) < 0.005) {
    return '—';
  }

  const isNeg = num < 0;
  const absVal = Math.abs(num);
  const decimals = options?.decimals ?? 2;

  const parts = absVal.toFixed(decimals).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const formattedAbs = parts.join('.');

  let result = formattedAbs;

  if (isNeg) {
    if (options?.useBracketsForNegative) {
      result = `(${formattedAbs})`;
    } else {
      result = `-${formattedAbs}`;
    }
  }

  if (options?.showCurrency) {
    return `AED ${result}`;
  }

  return result;
}

export function parseAED(input: string): number {
  if (!input) return 0;
  const cleaned = input.replace(/[^\d.-]/g, '');
  const parsed = parseFloat(cleaned);
  return isNaN(parsed) ? 0 : round2(parsed);
}
