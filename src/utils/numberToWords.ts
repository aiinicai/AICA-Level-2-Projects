import { CurrencyCode } from '../types';

/**
 * Utility to convert numbers into official English words for commercial invoices
 * Supports TZS, USD, INR, CNY, ZAR, GBP, and EUR
 */

const CURRENCY_CONFIGS: Record<
  CurrencyCode,
  { major: string; minor: string; majorSingular?: string }
> = {
  TZS: { major: 'Tanzania Shillings', minor: 'Cents', majorSingular: 'Tanzania Shilling' },
  USD: { major: 'US Dollars', minor: 'Cents', majorSingular: 'US Dollar' },
  INR: { major: 'Indian Rupees', minor: 'Paise', majorSingular: 'Indian Rupee' },
  CNY: { major: 'Chinese Yuan', minor: 'Fen', majorSingular: 'Chinese Yuan' },
  ZAR: { major: 'South African Rand', minor: 'Cents', majorSingular: 'South African Rand' },
  GBP: { major: 'Pounds Sterling', minor: 'Pence', majorSingular: 'Pound Sterling' },
  EUR: { major: 'Euros', minor: 'Cents', majorSingular: 'Euro' },
};

const ONES = [
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

const TENS = [
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

const SCALES = ['', 'Thousand', 'Million', 'Billion', 'Trillion'];

function convertLessThanThousand(n: number): string {
  let result = '';

  if (n >= 100) {
    result += ONES[Math.floor(n / 100)] + ' Hundred';
    n %= 100;
    if (n > 0) result += ' ';
  }

  if (n >= 20) {
    result += TENS[Math.floor(n / 10)];
    n %= 10;
    if (n > 0) result += '-' + ONES[n];
  } else if (n > 0) {
    result += ONES[n];
  }

  return result;
}

export function convertNumberToWords(amount: number, currency: CurrencyCode = 'TZS'): string {
  const config = CURRENCY_CONFIGS[currency] || CURRENCY_CONFIGS.TZS;

  if (isNaN(amount) || amount === 0) {
    return `${config.major} Zero Only`;
  }

  const isNegative = amount < 0;
  const absoluteAmount = Math.abs(amount);

  const integerPart = Math.floor(absoluteAmount);
  const decimalPart = Math.round((absoluteAmount - integerPart) * 100);

  let words = '';

  if (integerPart === 0) {
    words = 'Zero';
  } else {
    let currentNumber = integerPart;
    let scaleIndex = 0;
    const parts: string[] = [];

    while (currentNumber > 0) {
      const chunk = currentNumber % 1000;
      if (chunk !== 0) {
        const chunkWords = convertLessThanThousand(chunk);
        const scale = SCALES[scaleIndex];
        parts.unshift(scale ? `${chunkWords} ${scale}` : chunkWords);
      }
      currentNumber = Math.floor(currentNumber / 1000);
      scaleIndex++;
    }

    words = parts.join(' ');
  }

  const prefix = integerPart === 1 && config.majorSingular ? config.majorSingular : config.major;
  let formattedResult = `${prefix} ${words}`;

  if (decimalPart > 0) {
    const decimalWords = convertLessThanThousand(decimalPart);
    formattedResult += ` and ${decimalWords} ${config.minor}`;
  }

  formattedResult += ' Only';

  return (isNegative ? 'Negative ' : '') + formattedResult;
}

