import { CurrencyCode, UnitScale } from '../types/financial';

export function formatFinancialValue(
  valInCrores: number,
  currency: CurrencyCode = 'INR',
  scale: UnitScale = 'crores'
): string {
  // 1 Crore = 10 Millions in Indian Rupees (₹)
  if (scale === 'millions') {
    const inMillions = valInCrores * 10;
    return `₹ ${inMillions.toLocaleString('en-IN', { maximumFractionDigits: 1 })} M`;
  }

  if (scale === 'lakhs') {
    return `₹ ${(valInCrores * 100).toLocaleString('en-IN')} L`;
  }

  return `₹ ${valInCrores.toLocaleString('en-IN')} Cr`;
}

export function getCurrencyUnitLabel(currency: CurrencyCode = 'INR', scale: UnitScale = 'crores'): string {
  if (scale === 'millions') {
    return 'INR (₹ Millions)';
  }
  if (scale === 'lakhs') {
    return 'INR (₹ Lakhs)';
  }
  return 'INR (₹ Crores)';
}
