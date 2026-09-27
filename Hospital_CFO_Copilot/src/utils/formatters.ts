/**
 * Indian Numbering System and Healthcare Currency & Date Formatters
 * Adheres strictly to Indian financial conventions (Lakhs, Crores, INR ₹ symbol, DD-MMM-YYYY dates).
 */

/**
 * Formats a numeric value into Indian Rupee (₹) currency format.
 * Examples:
 * - formatINR(1245000) => "₹12,45,000"
 * - formatINR(1245000, { compact: true }) => "₹12.45 L"
 * - formatINR(15000000, { compact: true }) => "₹1.50 Cr"
 */
export function formatINR(
  val: number | null | undefined,
  options?: { compact?: boolean; hideSymbol?: boolean }
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return options?.hideSymbol ? '0' : '₹0';
  }

  const sign = val < 0 ? '-' : '';
  const absVal = Math.abs(val);
  const symbol = options?.hideSymbol ? '' : '₹';

  if (options?.compact) {
    if (absVal >= 10000000) {
      // 1 Crore = 10,000,000 (100 Lakhs)
      const cr = absVal / 10000000;
      return `${sign}${symbol}${cr.toFixed(2)} Cr`;
    }
    if (absVal >= 100000) {
      // 1 Lakh = 100,000
      const lk = absVal / 100000;
      return `${sign}${symbol}${lk.toFixed(2)} L`;
    }
    if (absVal >= 1000) {
      const k = absVal / 1000;
      return `${sign}${symbol}${k.toFixed(1)} K`;
    }
    return `${sign}${symbol}${absVal.toLocaleString('en-IN')}`;
  }

  // Full Indian grouping (e.g. 12,34,567)
  const formatted = absVal.toLocaleString('en-IN', {
    maximumFractionDigits: 0,
  });

  return `${sign}${symbol}${formatted}`;
}

/**
 * Formats standard numbers using Indian grouping (e.g. 1,50,000 instead of 150,000)
 */
export function formatIndianNumber(val: number | null | undefined): string {
  if (val === null || val === undefined || isNaN(val)) return '0';
  return val.toLocaleString('en-IN');
}

/**
 * Formats ISO date or YYYY-MM-DD into Indian convention: DD-MMM-YYYY or DD/MM/YYYY
 * Example: "2026-09-23" => "23 Sep 2026"
 */
export function formatIndianDate(
  dateStr: string | null | undefined,
  format: 'short' | 'numeric' = 'short'
): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;

    if (format === 'numeric') {
      const day = String(d.getDate()).padStart(2, '0');
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const year = d.getFullYear();
      return `${day}/${month}/${year}`;
    }

    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    const day = String(d.getDate()).padStart(2, '0');
    const month = months[d.getMonth()];
    const year = d.getFullYear();
    return `${day} ${month} ${year}`;
  } catch {
    return dateStr;
  }
}

/**
 * Formats date-time into Indian convention: DD-MMM-YYYY, hh:mm AM/PM
 * Example: "2026-09-23 10:15:00" => "23 Sep 2026, 10:15 AM"
 */
export function formatIndianDateTime(dateTimeStr: string | null | undefined): string {
  if (!dateTimeStr) return '—';
  try {
    const d = new Date(dateTimeStr);
    if (isNaN(d.getTime())) return dateTimeStr;

    const datePart = formatIndianDate(dateTimeStr, 'short');
    const hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    const formattedHours = hours % 12 || 12;

    return `${datePart}, ${formattedHours}:${minutes} ${ampm}`;
  } catch {
    return dateTimeStr;
  }
}
