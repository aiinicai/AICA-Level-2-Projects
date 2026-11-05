import { ExpenseCategory, Transaction } from '../types/finance';
import { categorizeMerchant, cleanMerchantName, detectRedFlag, KNOWN_MERCHANTS } from './categorizer';

export interface ParsedBankNotification {
  success: boolean;
  bankName: string;
  amount: number;
  originalAmount?: number;
  originalCurrency?: string;
  exchangeRate?: number;
  currency: string;
  merchant: string;
  cleanedMerchant: string;
  category: ExpenseCategory;
  date: string;
  time?: string;
  cardMask?: string;
  isRedFlag: boolean;
  redFlagReason?: string;
  type: 'expense' | 'income';
  rawText: string;
}

export interface ParseOptions {
  pastMerchants?: string[];
  existingTransactions?: Transaction[];
}

export function extractDateAndTimeToISO(text: string): { date: string; time?: string } {
  const cleanText = sanitizeBankSMSText(text);
  const now = new Date();
  const currentYear = now.getFullYear();
  let foundDate: string | null = null;
  let foundTime: string | null = null;

  // 1. Time extraction: e.g. "at 14:32", "at 02:30 PM", "14:32:05", "10:15am", "at 18:22"
  const timeMatch = cleanText.match(/\b(?:at\s+)?([0-1]?[0-9]|2[0-3]):([0-5][0-9])(?::([0-5][0-9]))?\s*(am|pm)?\b/i);
  if (timeMatch) {
    let hours = parseInt(timeMatch[1], 10);
    const minutes = timeMatch[2];
    const meridian = timeMatch[4]?.toLowerCase();
    if (meridian === 'pm' && hours < 12) hours += 12;
    if (meridian === 'am' && hours === 12) hours = 0;
    foundTime = `${hours.toString().padStart(2, '0')}:${minutes}`;
  }

  // 2. Month mapping for short/full English names
  const MONTHS: Record<string, number> = {
    jan: 1, january: 1,
    feb: 2, february: 2,
    mar: 3, march: 3,
    apr: 4, april: 4,
    may: 5,
    jun: 6, june: 6,
    jul: 7, july: 7,
    aug: 8, august: 8,
    sep: 9, sept: 9, september: 9,
    oct: 10, october: 10,
    nov: 11, november: 11,
    dec: 12, december: 12
  };

  // Exact month names regex: avoids matching arbitrary words like "debited" or "spent"
  const MONTH_REGEX = '(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)';

  // Pattern 1: DD-MMM-YYYY or DD-MMM-YY or DD MMM YYYY or DD-MMM (e.g. "27-OCT-2026", "27-Oct-26", "27 Oct 2026", "27-Oct")
  // Common in Emirates NBD: "on 27-OCT-26 at 14:30" or ADCB: "on 26-OCT-2026"
  const pattern1 = text.match(new RegExp('\\b([0-3]?[0-9])[\\s\\-\\/.\\s]*(' + MONTH_REGEX + ')(?:[\\s\\-\\/.\\s]*([0-9]{2,4}))?\\b', 'i'));
  if (pattern1) {
    const day = parseInt(pattern1[1], 10);
    const monthKey = pattern1[2].toLowerCase();
    const month = MONTHS[monthKey];
    let year = pattern1[3] ? parseInt(pattern1[3], 10) : currentYear;
    if (year < 100) year += 2000;
    if (month && day >= 1 && day <= 31) {
      foundDate = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
    }
  }

  // Pattern 2: MMM DD, YYYY or MMM DD YYYY or MMM DD (e.g. "Oct 27, 2026", "October 26", "Oct 28")
  if (!foundDate) {
    const pattern2 = text.match(new RegExp('\\b(' + MONTH_REGEX + ')[\\s\\-\\/.\\s]*([0-3]?[0-9])(?:,?\\s*([0-9]{2,4}))?\\b', 'i'));
    if (pattern2) {
      const monthKey = pattern2[1].toLowerCase();
      const month = MONTHS[monthKey];
      const day = parseInt(pattern2[2], 10);
      let year = pattern2[3] ? parseInt(pattern2[3], 10) : currentYear;
      if (year < 100) year += 2000;
      if (month && day >= 1 && day <= 31) {
        foundDate = `${year}-${month.toString().padStart(2, '0')}-${day.toString().padStart(2, '0')}`;
      }
    }
  }

  // Pattern 3: YYYY-MM-DD or YYYY/MM/DD (ISO formatted dates, e.g. 2026-10-27)
  if (!foundDate) {
    const pattern3 = text.match(/\b(20[2-9][0-9])[\-\/\.](0?[1-9]|1[0-2])[\-\/\.](0?[1-9]|[12][0-9]|3[01])\b/);
    if (pattern3) {
      const year = pattern3[1];
      const month = pattern3[2].padStart(2, '0');
      const day = pattern3[3].padStart(2, '0');
      foundDate = `${year}-${month}-${day}`;
    }
  }

  // Pattern 4: DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY or DD/MM/YY or DD-MM-YY (e.g. "27/10/2026", "27-10-2026", "26/10/26", "27.10.26")
  if (!foundDate) {
    const pattern4 = text.match(/\b(0?[1-9]|[12][0-9]|3[01])[\-\/\.](0?[1-9]|1[0-2])[\-\/\.]([0-9]{2,4})\b/);
    if (pattern4) {
      const day = pattern4[1].padStart(2, '0');
      const month = pattern4[2].padStart(2, '0');
      let year = parseInt(pattern4[3], 10);
      if (year < 100) year += 2000;
      foundDate = `${year}-${month}-${day}`;
    }
  }

  // Pattern 5: DD/MM or DD-MM (e.g. "on 27/10 at 14:30" or "dated 26/10")
  if (!foundDate) {
    const pattern5 = text.match(/(?:on|dated|date|at)?\s*\b(0?[1-9]|[12][0-9]|3[01])[\-\/\.](0?[1-9]|1[0-2])\b/i);
    if (pattern5) {
      const day = pattern5[1].padStart(2, '0');
      const month = pattern5[2].padStart(2, '0');
      foundDate = `${currentYear}-${month}-${day}`;
    }
  }

  return {
    date: foundDate || now.toISOString().split('T')[0],
    time: foundTime || undefined
  };
}

// Exchange rates to AED for common foreign currencies (used to compute approx AED amount when foreign currency is detected)
const FX_TO_AED: Record<string, number> = {
  USD: 3.6725,
  EUR: 3.98,
  GBP: 4.65,
  INR: 0.044,
  SAR: 0.98,
  OMR: 9.54,
  QAR: 1.01,
  KWD: 11.95,
  CAD: 2.70,
  AUD: 2.40,
  SGD: 2.75,
  JPY: 0.024,
  CHF: 4.10,
  THB: 0.10
};

/**
 * Robust sanitizer for iOS / iPhone SMS, WhatsApp forwards, and bilingual bank messages.
 * Strips invisible Unicode marks (LTR/RTL marks, zero-width chars) and normalizes spaces/quotes.
 */
export function sanitizeBankSMSText(raw: string): string {
  if (!raw) return '';
  return raw
    // Remove zero-width characters and directional marks (u200E LTR, u200F RTL, uFEFF BOM, etc.)
    .replace(/[\u200B-\u200F\uFEFF\u061C\u202A-\u202E]/g, '')
    // Normalize all Unicode space variants (non-breaking space, thin space, etc.) to single ASCII space
    .replace(/[\u00A0\u2000-\u200A\u202F\u205F\u3000]/g, ' ')
    // Normalize curly and smart quotes
    .replace(/[“”«»]/g, '"')
    .replace(/[‘’`]/g, "'")
    // Normalize newlines
    .replace(/\r\n|\r/g, '\n')
    .trim();
}

export function parseBankNotificationText(
  text: string,
  options?: ParseOptions
): ParsedBankNotification {
  const clean = sanitizeBankSMSText(text);
  const lower = clean.toLowerCase();

  // 1. Identify Bank
  let bankName = 'UAE Bank';
  if (/emirates\s*nbd|enbd/i.test(clean)) bankName = 'Emirates NBD';
  else if (/adcb|abu\s*dhabi\s*commercial/i.test(clean)) bankName = 'ADCB';
  else if (/dib|dubai\s*islamic\s*bank/i.test(clean)) bankName = 'Dubai Islamic Bank (DIB)';
  else if (/fab|first\s*abu\s*dhabi/i.test(clean)) bankName = 'FAB';
  else if (/mashreq|neo/i.test(clean)) bankName = 'Mashreq';
  else if (/citi(?:bank)?/i.test(clean)) bankName = 'Citi';
  else if (/adib|abu\s*dhabi\s*islamic/i.test(clean)) bankName = 'ADIB';
  else if (/cbd|commercial\s*bank\s*of\s*dubai/i.test(clean)) bankName = 'CBD';
  else if (/rakbank/i.test(clean)) bankName = 'RAKBANK';
  else if (/hsbc/i.test(clean)) bankName = 'HSBC UAE';
  else if (/standard\s*chartered|sc\s*mobile/i.test(clean)) bankName = 'Standard Chartered UAE';
  else if (/wio\s*bank|wio/i.test(clean)) bankName = 'Wio Bank';
  else if (/liv(?:\.|\s+by\s+enbd)/i.test(clean)) bankName = 'Liv. by ENBD';
  else if (/sharjah\s*islamic|sib/i.test(clean)) bankName = 'Sharjah Islamic Bank (SIB)';
  else if (/al\s*hilal/i.test(clean)) bankName = 'Al Hilal Bank';
  else if (/ajman\s*bank/i.test(clean)) bankName = 'Ajman Bank';
  else if (/al\s*maryah|mbank/i.test(clean)) bankName = 'Al Maryah Community Bank (Mbank)';
  else if (/fujairah|nbf/i.test(clean)) bankName = 'National Bank of Fujairah (NBF)';
  else if (/ruya/i.test(clean)) bankName = 'Ruya Islamic Bank';
  else if (/zand/i.test(clean)) bankName = 'Zand Digital Bank';

  // 2. Identify if Income / Salary Deposit or Expense / Debit
  const isSalary = /salary|wps|payroll|stipend|wages/i.test(clean);
  const isCredit = isSalary || (/credited|deposit|refund|transfer in|received/i.test(clean) && !/debited|spent|purchase|used for|paid to/i.test(clean));
  const type: 'expense' | 'income' = isCredit ? 'income' : 'expense';

  // 3. Extract Card / Account Mask
  let cardMask = '';
  const cardMatch = clean.match(/(?:ending|card|account|acct|no\.?|a\/c)\s*(?:in|ending\s*in|ending)?\s*(?:x+|\*+)?([0-9]{4})/i);
  if (cardMatch) {
    cardMask = `•••• ${cardMatch[1]}`;
  }

  // 4. Extract Currency and Amount
  let currency = 'AED';
  let originalCurrency: string | undefined = undefined;
  let amount = 0;
  let originalAmount: number | undefined = undefined;
  let exchangeRate: number | undefined = undefined;

  // Check for foreign currency pattern: e.g., "USD 84.50", "$85.00", "84.50 USD", "EUR 120"
  const foreignMatch = clean.match(/\b(USD|EUR|GBP|INR|SAR|OMR|QAR|KWD|CAD|AUD|SGD|JPY|CHF|THB)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/i) ||
    clean.match(/([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)\s*(USD|EUR|GBP|INR|SAR|OMR|QAR|KWD|CAD|AUD|SGD|JPY|CHF|THB)\b/i) ||
    clean.match(/(\$)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/i);

  // Specific credit or salary deposit amount match (takes priority over available balance)
  const creditAmountMatch = clean.match(/(?:credited(?:\s+with)?|salary(?:\s+deposit)?(?:\s+of)?|deposit(?:\s+of)?|transfer(?:\s+of)?)\s*(?:AED|DHS|DIRHAM)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/i);
  // Specific spend amount match
  const spendAmountMatch = clean.match(/(?:spent|purchase(?:\s+of)?|debited(?:\s+by)?|used for|transaction(?:\s+of)?)\s*(?:AED|DHS|DIRHAM)?\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/i);
  // General AED match
  const aedMatch = clean.match(/\b(?:AED|DHS|DIRHAM)\s*([0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?)/i);

  if (foreignMatch && (!aedMatch || clean.indexOf(foreignMatch[0]) < clean.indexOf(aedMatch[0]))) {
    let currCode = foreignMatch[1].toUpperCase();
    let amtStr = foreignMatch[2];
    if (currCode === '$') {
      currCode = 'USD';
    } else if (!isNaN(Number(currCode))) {
      // Swapped format: amount was in group 1, currency code in group 2
      amtStr = foreignMatch[1];
      currCode = foreignMatch[2].toUpperCase();
    }

    originalCurrency = currCode;
    originalAmount = parseFloat(amtStr.replace(/,/g, ''));
    currency = 'AED';

    // USD default conversion rate is 3.6725 AED/USD
    exchangeRate = FX_TO_AED[originalCurrency] || 3.6725;

    // Check if SMS mentions approx AED amount, e.g. "USD 65.00 (approx AED 238.80)"
    if (aedMatch) {
      amount = parseFloat(aedMatch[1].replace(/,/g, ''));
      // Calculate effective exchange rate from SMS if both are given
      if (originalAmount > 0) {
        exchangeRate = parseFloat((amount / originalAmount).toFixed(4));
      }
    } else {
      amount = parseFloat((originalAmount * exchangeRate).toFixed(2));
    }
  } else if (type === 'income' && creditAmountMatch) {
    currency = 'AED';
    amount = parseFloat(creditAmountMatch[1].replace(/,/g, ''));
  } else if (type === 'expense' && spendAmountMatch) {
    currency = 'AED';
    amount = parseFloat(spendAmountMatch[1].replace(/,/g, ''));
  } else if (aedMatch) {
    currency = 'AED';
    amount = parseFloat(aedMatch[1].replace(/,/g, ''));
  } else {
    // Fallback any number with 2 decimals
    const numMatch = clean.match(/([0-9]+(?:\.[0-9]{2}))/);
    if (numMatch) {
      amount = parseFloat(numMatch[1]);
    }
  }

  // 5. Extract Merchant & Category
  let rawMerchant = 'Unknown Merchant';
  let category: ExpenseCategory = 'Other';

  if (isSalary) {
    category = 'Salary';
    // Check if employer name is specified
    const employerMatch = clean.match(/(?:from|by)\s+([A-Z0-9\s&.\-]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|avl|balance|with|towards)|\.|\,|$)/i);
    const employer = employerMatch && employerMatch[1] && !/account|card|bank/i.test(employerMatch[1]) ? employerMatch[1].trim() : null;
    if (bankName === 'Mashreq') {
      rawMerchant = employer ? `Mashreq Salary (${employer})` : 'Mashreq Salary Deposit';
    } else {
      rawMerchant = employer ? `Salary Deposit (${employer})` : 'Salary Deposit';
    }
  } else if (type === 'income') {
    category = 'Other';
    rawMerchant = bankName === 'Mashreq' ? 'Mashreq Credit Deposit' : 'Bank Credit Transfer';
  } else {
    // 5a. First Priority: Check explicit merchant pattern extraction from SMS (e.g. "at ...", "purchase at ...", "paid to ...")
    let foundMerchant: string | null = null;
    let foundCategory: ExpenseCategory | null = null;

    const merchantMatch =
      clean.match(/\b(?:purchase\s+at|paid\s+to|spent\s+at|trx\s+at|transaction\s+at|used\s+at)\s+([A-Za-z0-9\s&.\-'\/\*]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|avl|balance|with|from|card|\d{1,2}[\/\-]\d{1,2})|\.|\,|$|\n)/i) ||
      clean.match(/\b(?:at)\s+([A-Za-z0-9\s&.\-'\/\*]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|avl|balance|with|from|card|\d{1,2}[\/\-]\d{1,2})|\.|\,|$|\n)/i) ||
      clean.match(/\b(?:to)\s+([A-Za-z0-9\s&.\-'\/\*]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|avl|balance|with|from|card|\d{1,2}[\/\-]\d{1,2})|\.|\,|$|\n)/i) ||
      clean.match(/\b(?:merchant|info)(?:\s*:|\s*-)\s*([A-Za-z0-9\s&.\-'\/\*]+?)(?:\s+(?:on|dated|ref|avail|avbl|limit|avl|balance|with|from|card)|\.|\,|$|\n)/i);

    const explicitCandidate = merchantMatch && merchantMatch[1] ? merchantMatch[1].trim() : '';

    if (explicitCandidate) {
      const explicitLower = explicitCandidate.toLowerCase();
      for (const km of KNOWN_MERCHANTS) {
        for (const kw of km.keywords) {
          const kwLow = kw.toLowerCase().trim();
          if (explicitLower === kwLow || explicitLower.includes(kwLow)) {
            foundMerchant = km.name;
            foundCategory = km.category;
            break;
          }
        }
        if (foundMerchant) break;
      }
      if (!foundMerchant) {
        foundMerchant = explicitCandidate;
      }
    }

    // 5b. Second Priority: Check if message contains any past merchant previously added by user
    if (!foundMerchant) {
      const pastList: string[] = [];
      if (options?.pastMerchants) {
        pastList.push(...options.pastMerchants);
      }
      if (options?.existingTransactions) {
        for (const t of options.existingTransactions) {
          if (t.merchant && t.merchant !== 'Unknown Merchant' && !pastList.includes(t.merchant)) {
            pastList.push(t.merchant);
          }
        }
      }

      pastList.sort((a, b) => b.length - a.length);

      for (const pm of pastList) {
        const pmClean = pm.trim();
        if (pmClean.length >= 2 && lower.includes(pmClean.toLowerCase())) {
          foundMerchant = pmClean;
          const matchTx = options?.existingTransactions?.find(
            t => t.merchant.toLowerCase() === pmClean.toLowerCase() && t.category !== 'Other'
          );
          if (matchTx) {
            foundCategory = matchTx.category;
          }
          break;
        }
      }
    }

    // 5c. Third Priority: Check known UAE / global merchants dictionary with word boundary safety
    if (!foundMerchant) {
      for (const km of KNOWN_MERCHANTS) {
        for (const kw of km.keywords) {
          const kwLow = kw.toLowerCase().trim();
          const regex = new RegExp(`\\b${kwLow.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i');
          if (regex.test(lower)) {
            foundMerchant = km.name;
            foundCategory = km.category;
            break;
          }
        }
        if (foundMerchant) break;
      }
    }

    rawMerchant = foundMerchant || 'Unknown Merchant';
    if (foundCategory) {
      category = foundCategory;
    }
  }

  const cleanedMerchant = cleanMerchantName(rawMerchant);
  if (type === 'expense' && category === 'Other') {
    category = categorizeMerchant(cleanedMerchant);
  }

  // 6. Red Flag Assessment (only for expenses; salary deposits are never flagged)
  let isRedFlag = false;
  let redFlagReason: string | undefined = undefined;

  if (type === 'expense') {
    if (originalCurrency && originalCurrency !== 'AED') {
      isRedFlag = true;
      redFlagReason = `International transaction (${originalCurrency} ${originalAmount?.toFixed(2)}) - pending confirmation`;
    } else {
      const redFlagCheck = detectRedFlag({
        currency: originalCurrency || currency,
        amount,
        merchant: cleanedMerchant,
        highThresholdAED: 1500
      });
      isRedFlag = redFlagCheck.isRedFlag;
      redFlagReason = redFlagCheck.reason;
    }
  }

  // Extract accurate Date & Time from SMS text
  const { date: dateStr, time: timeStr } = extractDateAndTimeToISO(clean);

  return {
    success: amount > 0,
    bankName,
    amount,
    originalAmount,
    originalCurrency,
    exchangeRate,
    currency,
    merchant: rawMerchant,
    cleanedMerchant,
    category,
    date: dateStr,
    time: timeStr,
    cardMask,
    isRedFlag,
    redFlagReason,
    type,
    rawText: clean
  };
}


