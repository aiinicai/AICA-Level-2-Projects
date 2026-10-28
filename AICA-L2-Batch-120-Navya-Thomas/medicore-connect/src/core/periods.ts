import { FiscalPeriod } from './types';
import { getFiscalPeriods2026, getPeriodFromDate } from './dates';

const PERIODS_KEY = 'medicore_fiscal_periods';

export function getFiscalPeriods(): FiscalPeriod[] {
  try {
    const raw = localStorage.getItem(PERIODS_KEY);
    if (raw) return JSON.parse(raw);
  } catch {
    // fallback
  }
  const defaults = getFiscalPeriods2026();
  saveFiscalPeriods(defaults);
  return defaults;
}

export function saveFiscalPeriods(periods: FiscalPeriod[]): void {
  localStorage.setItem(PERIODS_KEY, JSON.stringify(periods));
}

export function getPeriod(periodName: string): FiscalPeriod | undefined {
  const periods = getFiscalPeriods();
  return periods.find((p) => p.name === periodName);
}

export function isPeriodOpen(periodName: string): boolean {
  const p = getPeriod(periodName);
  return p?.status === 'Open';
}

export function checkDatePeriodStatus(dateStr: string): { isOpen: boolean; periodName: string; error?: string } {
  const periodName = getPeriodFromDate(dateStr);
  const p = getPeriod(periodName);
  if (!p) {
    return { isOpen: false, periodName, error: `Period ${periodName} does not exist in fiscal calendar` };
  }
  if (p.status === 'Closed') {
    return { isOpen: false, periodName, error: `Period ${periodName} is CLOSED. Posting to closed periods is strictly prohibited.` };
  }
  if (p.status === 'Future') {
    return { isOpen: false, periodName, error: `Period ${periodName} is FUTURE. Open the period prior to posting transactions.` };
  }
  return { isOpen: true, periodName };
}

export function setPeriodStatus(periodName: string, status: 'Open' | 'Closed' | 'Future'): boolean {
  const periods = getFiscalPeriods();
  const idx = periods.findIndex((p) => p.name === periodName);
  if (idx >= 0) {
    periods[idx].status = status;
    saveFiscalPeriods(periods);
    window.dispatchEvent(new Event('medicore-period-changed'));
    return true;
  }
  return false;
}
