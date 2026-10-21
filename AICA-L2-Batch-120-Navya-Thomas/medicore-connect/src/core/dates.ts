/**
 * Date utilities for MediCore Connect
 * Standard ERP Date Format: DD/MMM/YYYY (e.g., 19/Oct/2026)
 * Demo Anchor Date: 19/Oct/2026
 */

export const DEMO_TODAY = '2026-10-19'; // ISO format
export const CURRENT_OPEN_PERIOD = 'Oct-26';

const MONTH_NAMES = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
];

export function formatDate(dateInput: string | Date | undefined | null): string {
  if (!dateInput) return '—';
  
  let date: Date;
  if (typeof dateInput === 'string') {
    // If already in DD/MMM/YYYY format
    if (/^\d{2}\/[A-Za-z]{3}\/\d{4}$/.test(dateInput)) {
      return dateInput;
    }
    date = new Date(dateInput);
  } else {
    date = dateInput;
  }

  if (isNaN(date.getTime())) return String(dateInput);

  const day = String(date.getDate()).padStart(2, '0');
  const month = MONTH_NAMES[date.getMonth()];
  const year = date.getFullYear();

  return `${day}/${month}/${year}`;
}

export function toIsoDate(dateStr: string): string {
  if (!dateStr) return DEMO_TODAY;
  // If in DD/MMM/YYYY format
  const match = dateStr.match(/^(\d{2})\/([A-Za-z]{3})\/(\d{4})$/);
  if (match) {
    const day = match[1];
    const monthIndex = MONTH_NAMES.indexOf(match[2]);
    const month = String(monthIndex + 1).padStart(2, '0');
    const year = match[3];
    return `${year}-${month}-${day}`;
  }
  return dateStr;
}

export function getPeriodFromDate(dateInput: string | Date): string {
  const iso = typeof dateInput === 'string' ? toIsoDate(dateInput) : dateInput.toISOString().split('T')[0];
  const parts = iso.split('-');
  if (parts.length >= 2) {
    const monthIdx = parseInt(parts[1], 10) - 1;
    const yearShort = parts[0].slice(-2);
    return `${MONTH_NAMES[monthIdx]}-${yearShort}`;
  }
  return CURRENT_OPEN_PERIOD;
}

export function getFiscalPeriods2026() {
  return [
    { name: 'Jan-26', year: 2026, month: 1, startDate: '2026-01-01', endDate: '2026-01-31', status: 'Closed' as const },
    { name: 'Feb-26', year: 2026, month: 2, startDate: '2026-02-01', endDate: '2026-02-28', status: 'Closed' as const },
    { name: 'Mar-26', year: 2026, month: 3, startDate: '2026-03-01', endDate: '2026-03-31', status: 'Closed' as const },
    { name: 'Apr-26', year: 2026, month: 4, startDate: '2026-04-01', endDate: '2026-04-30', status: 'Closed' as const },
    { name: 'May-26', year: 2026, month: 5, startDate: '2026-05-01', endDate: '2026-05-31', status: 'Closed' as const },
    { name: 'Jun-26', year: 2026, month: 6, startDate: '2026-06-01', endDate: '2026-06-30', status: 'Closed' as const },
    { name: 'Jul-26', year: 2026, month: 7, startDate: '2026-07-01', endDate: '2026-07-31', status: 'Closed' as const },
    { name: 'Aug-26', year: 2026, month: 8, startDate: '2026-08-01', endDate: '2026-08-31', status: 'Closed' as const },
    { name: 'Sep-26', year: 2026, month: 9, startDate: '2026-09-01', endDate: '2026-09-30', status: 'Closed' as const },
    { name: 'Oct-26', year: 2026, month: 10, startDate: '2026-10-01', endDate: '2026-10-31', status: 'Open' as const },
    { name: 'Nov-26', year: 2026, month: 11, startDate: '2026-11-01', endDate: '2026-11-30', status: 'Future' as const },
    { name: 'Dec-26', year: 2026, month: 12, startDate: '2026-12-01', endDate: '2026-12-31', status: 'Future' as const }
  ];
}
