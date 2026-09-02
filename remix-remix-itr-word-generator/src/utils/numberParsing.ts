/**
 * Utility for parsing and formatting numbers according to Indian Income Tax conventions.
 * Includes Indian Currency formatting (₹ 12,34,567), Number to Words conversion (Lakhs & Crores),
 * and Income Tax Act rounding rules (Section 288A & 288B).
 */

/**
 * Parses raw text or messy OCR/PDF string into a clean numeric value.
 * Handles: ₹, INR, Rs., commas, whitespace, and bracketed negative numbers like (50,000).
 */
export function parseIndianNumber(val: string | number | null | undefined): number {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;

  let str = String(val).trim();
  if (!str) return 0;

  // Check for negative in parenthesis e.g. (1,23,456)
  let isNegative = false;
  if (str.startsWith('(') && str.endsWith(')')) {
    isNegative = true;
    str = str.slice(1, -1);
  } else if (str.startsWith('-')) {
    isNegative = true;
    str = str.slice(1);
  }

  // Remove currency words, symbols, commas, spaces, dashes
  str = str.replace(/[₹Rs\.\s,INRinr/\\-]/g, '').trim();

  // If decimal point exists, preserve it
  const num = parseFloat(str);
  if (isNaN(num)) return 0;
  return isNegative ? -Math.abs(num) : num;
}

/**
 * Formats a number according to the Indian numbering system (Lakhs and Crores).
 * Example: 1234567 -> "12,34,567" or "₹ 12,34,567.00"
 */
export function formatIndianCurrency(
  val: number | undefined | null,
  options: { showSymbol?: boolean; showDecimals?: boolean; symbol?: string } = {}
): string {
  const { showSymbol = true, showDecimals = false, symbol = '₹' } = options;
  const num = typeof val === 'number' && !isNaN(val) ? val : 0;
  const isNegative = num < 0;
  const absNum = Math.abs(num);

  const rounded = showDecimals ? absNum.toFixed(2) : Math.round(absNum).toString();
  const parts = rounded.split('.');
  let intPart = parts[0];
  const decPart = parts.length > 1 ? '.' + parts[1] : '';

  // Indian format: last 3 digits, then groups of 2 digits
  let result = '';
  if (intPart.length > 3) {
    const lastThree = intPart.substring(intPart.length - 3);
    const otherNumbers = intPart.substring(0, intPart.length - 3);
    const formattedOthers = otherNumbers.replace(/\B(?=(\d{2})+(?!\d))/g, ',');
    result = formattedOthers + ',' + lastThree;
  } else {
    result = intPart;
  }

  result = result + decPart;
  if (isNegative) {
    result = '-' + result;
  }

  return showSymbol ? `${symbol} ${result}` : result;
}

/**
 * Converts a positive number to Indian Rupees in Words (English).
 * Handles Ones, Tens, Hundreds, Thousands, Lakhs, Crores.
 * Example: 1534500 -> "Rupees Fifteen Lakh Thirty-Four Thousand Five Hundred Only"
 */
export function numberToIndianRupeesWords(num: number | undefined | null): string {
  const n = Math.round(Math.abs(parseIndianNumber(num)));
  if (n === 0) return 'Rupees Zero Only';

  const ones = [
    '',
    'One',
    'Two',
    'Three',
    'Four',
    'Five',
    'Six',
    'Seven',
    'Eight',
    'Nine',
    'Ten',
    'Eleven',
    'Twelve',
    'Thirteen',
    'Fourteen',
    'Fifteen',
    'Sixteen',
    'Seventeen',
    'Eighteen',
    'Nineteen',
  ];

  const tens = [
    '',
    '',
    'Twenty',
    'Thirty',
    'Forty',
    'Fifty',
    'Sixty',
    'Seventy',
    'Eighty',
    'Ninety',
  ];

  function convertBelowThousand(val: number): string {
    let str = '';
    if (val >= 100) {
      str += ones[Math.floor(val / 100)] + ' Hundred ';
      val %= 100;
    }
    if (val >= 20) {
      str += tens[Math.floor(val / 10)] + ' ';
      val %= 10;
    }
    if (val > 0) {
      str += ones[val] + ' ';
    }
    return str.trim();
  }

  const crore = Math.floor(n / 10000000);
  const lakh = Math.floor((n % 10000000) / 100000);
  const thousand = Math.floor((n % 100000) / 1000);
  const remainder = n % 1000;

  let words = '';

  if (crore > 0) {
    words += convertBelowThousand(crore) + ' Crore ';
  }
  if (lakh > 0) {
    words += convertBelowThousand(lakh) + ' Lakh ';
  }
  if (thousand > 0) {
    words += convertBelowThousand(thousand) + ' Thousand ';
  }
  if (remainder > 0) {
    words += convertBelowThousand(remainder) + ' ';
  }

  const result = `Rupees ${words.trim().replace(/\s+/g, ' ')} Only`;
  return result;
}

/**
 * Section 288A of Income Tax Act:
 * Taxable Total Income is rounded off to the nearest multiple of ten rupees.
 * If the last digit is 5 or more, rounded up; otherwise rounded down.
 */
export function roundOff288A(income: number): number {
  return Math.round(income / 10) * 10;
}

/**
 * Section 288B of Income Tax Act:
 * Net Tax Payable or Refund Due is rounded off to the nearest multiple of ten rupees.
 */
export function roundOff288B(tax: number): number {
  return Math.round(tax / 10) * 10;
}
