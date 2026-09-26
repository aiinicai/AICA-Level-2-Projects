import { Transaction } from '../types';

/**
 * Formats an amount into standard Indian Rupees (₹) notation.
 * e.g., 125000 -> ₹1,25,000
 */
export function formatINR(amount: number, includeFraction = false): string {
  if (isNaN(amount) || amount === null || amount === undefined) {
    return '₹0';
  }
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: includeFraction ? 2 : 0,
    minimumFractionDigits: includeFraction ? 2 : 0,
  }).format(amount);
}

/**
 * Format date string (YYYY-MM-DD) into readable format, e.g. "24 Sep 2026"
 */
export function formatDate(dateString: string): string {
  if (!dateString) return '';
  const date = new Date(dateString + 'T00:00:00');
  if (isNaN(date.getTime())) return dateString;
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

/**
 * Formats month-year, e.g. "September 2026"
 */
export function formatMonthYear(yearMonth: string): string {
  const [year, month] = yearMonth.split('-');
  const date = new Date(Number(year), Number(month) - 1, 1);
  return new Intl.DateTimeFormat('en-IN', {
    month: 'long',
    year: 'numeric',
  }).format(date);
}

/**
 * Exports transactions to CSV and triggers file download
 */
export function exportTransactionsToCSV(transactions: Transaction[], filename?: string): void {
  const headers = [
    'Date',
    'Merchant / Entity',
    'Description',
    'Category',
    'Amount (INR)',
    'Payment Mode',
    'Source',
    'Line Items',
  ];

  const escapeCSV = (str: string | number | undefined | null) => {
    if (str === null || str === undefined) return '""';
    const value = String(str).replace(/"/g, '""');
    return `"${value}"`;
  };

  const rows = transactions.map((t) => [
    escapeCSV(t.date),
    escapeCSV(t.merchantName || '-'),
    escapeCSV(t.description),
    escapeCSV(t.category),
    t.amount,
    escapeCSV(t.paymentMode),
    escapeCSV(t.source === 'image' ? 'Invoice Scan' : 'Manual Entry'),
    escapeCSV(t.lineItems ? t.lineItems.map((li) => `${li.item} (₹${li.amount})`).join('; ') : ''),
  ]);

  const csvContent = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute(
    'download',
    filename || `smart-expense-tracker-${new Date().toISOString().slice(0, 10)}.csv`
  );
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
