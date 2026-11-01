import { Account, ExpenseCategory } from '../types/finance';

export interface VoiceParseResult {
  success: boolean;
  amount: number;
  merchant: string;
  category: ExpenseCategory;
  matchedAccountId: string | null;
  accountName: string;
  type: 'expense' | 'income';
  date: string;
  notes: string;
  source: 'js_rules' | 'gemini_fallback';
  confidence: 'high' | 'medium' | 'low';
  debugTimingMs?: number;
}

// Spoken numbers dictionary for English and Hindi / Hinglish
const WORD_NUMBERS: Record<string, number> = {
  // English single digits and teens
  zero: 0, one: 1, two: 2, three: 3, four: 4, five: 5, six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  eleven: 11, twelve: 12, thirteen: 13, fourteen: 14, fifteen: 15, sixteen: 16, seventeen: 17,
  eighteen: 18, nineteen: 19,
  // English tens
  twenty: 20, thirty: 30, forty: 40, fifty: 50, sixty: 60, seventy: 70, eighty: 80, ninety: 90,
  // English scales
  hundred: 100, thousand: 1000, million: 1000000,

  // Hindi / Hinglish spoken digits
  ek: 1, do: 2, teen: 3, chaar: 4, char: 4, paanch: 5, panch: 5, che: 6, chhah: 6, saat: 7,
  aath: 8, ath: 8, nau: 9, dus: 10, das: 10,
  gyarah: 11, barah: 12, terah: 13, chaudah: 14, pandrah: 15, solah: 16, satrah: 17,
  atharah: 18, unnis: 19,
  // Hindi tens
  bees: 20, bis: 20, tees: 30, tis: 30, chaalis: 40, chalis: 40, pachaas: 50, pachas: 50,
  saath: 60, sath: 60, sattar: 70, assi: 80, nabbe: 90, nave: 90,
  // Hindi compound phrases and scales
  sau: 100, so: 100,
  hazaar: 1000, hazar: 1000, hajar: 1000,
  lakh: 100000, lac: 100000, karor: 10000000, crore: 10000000,
  // Hindi special fractions
  dedh: 150, // "dedh sau" -> 150
  dhai: 250  // "dhai sau" -> 250
};

// Known UAE Banks and abbreviations for fast rule-based matching
const UAE_BANK_PATTERNS = [
  { key: 'adcb', names: ['adcb', 'abu dhabi commercial', 'abu dhabi commercial bank'] },
  { key: 'enbd', names: ['enbd', 'emirates nbd', 'emirates bank', 'emirates islamic', 'eib'] },
  { key: 'fab', names: ['fab', 'first abu dhabi', 'first abu dhabi bank'] },
  { key: 'mashreq', names: ['mashreq', 'mashreq neo', 'mashreq bank', 'neo'] },
  { key: 'dib', names: ['dib', 'dubai islamic', 'dubai islamic bank'] },
  { key: 'adib', names: ['adib', 'abu dhabi islamic', 'abu dhabi islamic bank'] },
  { key: 'rak', names: ['rak', 'rakbank', 'rak bank', 'national bank of ras al khaimah'] },
  { key: 'cbd', names: ['cbd', 'commercial bank of dubai'] },
  { key: 'citi', names: ['citi', 'citibank', 'citi bank'] },
  { key: 'hsbc', names: ['hsbc', 'hsbc uae'] },
  { key: 'sc', names: ['standard chartered', 'stanchart', 'sc bank'] },
  { key: 'wio', names: ['wio', 'wio bank'] },
  { key: 'liv', names: ['liv', 'liv.'] },
  { key: 'ajman', names: ['ajman', 'ajman bank'] },
  { key: 'sib', names: ['sib', 'sharjah islamic', 'sharjah islamic bank'] },
  { key: 'alhilal', names: ['al hilal', 'alhilal'] },
  { key: 'mbank', names: ['mbank', 'al maryah', 'al maryah community'] }
];

function parseNormalizedAmount(rawNum: string): number {
  let cleaned = rawNum.trim();
  if (cleaned.includes(',') && cleaned.includes('.')) {
    cleaned = cleaned.replace(/,/g, '');
  } else if (cleaned.includes(',')) {
    if (/,\d{3}\b/.test(cleaned)) {
      cleaned = cleaned.replace(/,/g, '');
    } else {
      cleaned = cleaned.replace(',', '.');
    }
  }
  const parsed = parseFloat(cleaned);
  return !isNaN(parsed) && parsed > 0 ? parsed : 0;
}

/**
 * Extracts a numeric amount from spoken English or Hindi text.
 * Handles both digits ("AED 200", "200 dirhams", "500.50", "18,000") and spoken number words ("two hundred", "paanch sau", "dedh sau").
 */
export function extractAmountFromVoiceText(text: string): number {
  const clean = text.trim();
  const lower = clean.toLowerCase();

  // 1. Try regex on digit amounts with currency markers: e.g. "AED 200", "200 AED", "200 dirhams", "₹500", "500 rupaye", "AED 18,000"
  const currencyDigitMatch = lower.match(
    /(?:(?:aed|dhs|dirhams?|dh|rs|inr|₹|\$)\s*([0-9]+(?:[.,][0-9]+)?))|(?:([0-9]+(?:[.,][0-9]+)?)\s*(?:aed|dhs|dirhams?|dh|rupees?|rupaye|rs|inr|rupya))/i
  );
  if (currencyDigitMatch) {
    const rawNum = currencyDigitMatch[1] || currencyDigitMatch[2];
    const val = parseNormalizedAmount(rawNum);
    if (val > 0) return val;
  }

  // 2. Look for action verbs + digit: "add 200", "spent 200", "paid 200", "200 petrol", "petrol 200", "kharcha 200"
  const verbDigitMatch = lower.match(
    /\b(?:add|paid|spent|spend|deducted|debited|transfer|put|dala|bhara|diya|kharcha|liya|kiya|of)\s+([0-9]+(?:[.,][0-9]+)?)\b/i
  );
  if (verbDigitMatch) {
    const val = parseNormalizedAmount(verbDigitMatch[1]);
    if (val > 0 && !(val >= 2024 && val <= 2030 && lower.includes('year'))) {
      return val;
    }
  }

  // 3. Any standalone number (guarding against card 4 digits or year)
  const tokens = lower.split(/[\s,]+/);
  for (let i = 0; i < tokens.length; i++) {
    const tok = tokens[i].replace(/[^\d.,]/g, '');
    if (tok && /^[0-9]+(?:[.,][0-9]+)?$/.test(tok)) {
      const val = parseNormalizedAmount(tok);
      const prevWord = i > 0 ? tokens[i - 1].toLowerCase() : '';
      const isCardNum = /card|ending|number|pin|otp|code/i.test(prevWord);
      const isYear = (val === 2025 || val === 2026 || val === 2027);
      if (!isCardNum && !isYear && val > 0) {
        return val;
      }
    }
  }

  // 4. Spoken word numbers (English and Hindi)
  // Check special compound Hindi cases first:
  if (/\b(dedh\s+sau|tedh\s+sau)\b/i.test(lower)) return 150;
  if (/\b(dhai\s+sau)\b/i.test(lower)) return 250;
  if (/\b(dedh\s+hazaar|dedh\s+hazar)\b/i.test(lower)) return 1500;
  if (/\b(dhai\s+hazaar|dhai\s+hazar)\b/i.test(lower)) return 2500;

  // Process word numbers sequentially:
  let totalAmount = 0;
  let currentGroup = 0;
  let foundAnyWord = false;

  for (const word of tokens) {
    const cleanWord = word.replace(/[^a-z]/g, '');
    const num = WORD_NUMBERS[cleanWord];

    if (num !== undefined) {
      foundAnyWord = true;
      if (num === 100) {
        currentGroup = (currentGroup === 0 ? 1 : currentGroup) * 100;
      } else if (num === 1000 || num === 100000 || num === 10000000) {
        currentGroup = (currentGroup === 0 ? 1 : currentGroup) * num;
        totalAmount += currentGroup;
        currentGroup = 0;
      } else {
        currentGroup += num;
      }
    } else {
      if (currentGroup > 0) {
        totalAmount += currentGroup;
        currentGroup = 0;
      }
    }
  }
  if (currentGroup > 0) {
    totalAmount += currentGroup;
  }

  if (foundAnyWord && totalAmount > 0) {
    return totalAmount;
  }

  return 0;
}

/**
 * Parses date references from voice commands.
 * Handles: "today", "yesterday", "kal", "aaj", "parso", days of the week, or explicit dates.
 */
export function extractDateFromVoiceText(text: string): string {
  const lower = text.toLowerCase();
  const now = new Date();

  // Yesterday / kal
  if (/\b(yesterday|kal|beeta\s*kal|kal\s*ka|last\s*night)\b/i.test(lower)) {
    const d = new Date(now);
    d.setDate(now.getDate() - 1);
    return d.toISOString().split('T')[0];
  }

  // Day before yesterday / parso
  if (/\b(day\s+before\s+yesterday|parso|parson)\b/i.test(lower)) {
    const d = new Date(now);
    d.setDate(now.getDate() - 2);
    return d.toISOString().split('T')[0];
  }

  // Specific ISO date if typed / spoken: e.g. 2026-10-25
  const isoMatch = lower.match(/\b(202[4-9]-\d{2}-\d{2})\b/);
  if (isoMatch) {
    return isoMatch[1];
  }

  // Days of week (e.g. "on monday", "somwar ko", etc.) -> nearest past day
  const daysOfWeek = [
    { names: ['sunday', 'itwar', 'ravivar'], dayIndex: 0 },
    { names: ['monday', 'somwar'], dayIndex: 1 },
    { names: ['tuesday', 'mangalwar'], dayIndex: 2 },
    { names: ['wednesday', 'budhwar'], dayIndex: 3 },
    { names: ['thursday', 'guruwar', 'veewar'], dayIndex: 4 },
    { names: ['friday', 'jumma', 'shukrawar'], dayIndex: 5 },
    { names: ['saturday', 'shanivar', 'sanichar'], dayIndex: 6 }
  ];

  for (const item of daysOfWeek) {
    const regex = new RegExp(`\\b(${item.names.join('|')})\\b`, 'i');
    if (regex.test(lower)) {
      const currentDay = now.getDay();
      let diff = currentDay - item.dayIndex;
      if (diff <= 0) diff += 7; // past day
      const past = new Date(now);
      past.setDate(now.getDate() - diff);
      return past.toISOString().split('T')[0];
    }
  }

  // Default to today
  return now.toISOString().split('T')[0];
}

/**
 * Matches bank, credit card, or cash from user's active accounts database.
 */
export function matchAccountFromVoiceText(
  text: string,
  accounts: Account[]
): { account: Account | null; recognizedBankName: string } {
  const lower = text.toLowerCase();

  // 1. Explicit Cash check: "cash", "in cash", "paid cash", "naqad", "rokr", "haath me"
  const isCash = /\b(cash|naqad|rokr|haath\s*me|cash\s*wallet)\b/i.test(lower);
  if (isCash) {
    const cashAcc = accounts.find(a => a.type === 'cash');
    if (cashAcc) return { account: cashAcc, recognizedBankName: 'Cash Wallet' };
  }

  // 2. Identify mentioned bank keywords in speech
  let detectedBankKey = '';
  let detectedBankLabel = '';
  for (const item of UAE_BANK_PATTERNS) {
    for (const name of item.names) {
      const reg = new RegExp(`\\b${name.replace(/\s+/g, '\\s+')}\\b`, 'i');
      if (reg.test(lower)) {
        detectedBankKey = item.key;
        detectedBankLabel = item.names[0].toUpperCase();
        break;
      }
    }
    if (detectedBankKey) break;
  }

  // 3. Detect payment instrument type in speech
  const wantsCreditCard = /\b(credit\s*card|cc|credit)\b/i.test(lower);
  const wantsDebitOrBank = /\b(debit\s*card|debit|checking|current\s*account|savings|bank\s*account)\b/i.test(lower);

  // 4. Score accounts in user's database
  let bestAccount: Account | null = null;
  let highestScore = -1;

  for (const acc of accounts) {
    let score = 0;
    const accName = acc.name.toLowerCase();
    const bankName = (acc.bankName || '').toLowerCase();
    const last4 = acc.accountNumberMasked ? acc.accountNumberMasked.replace(/[^0-9]/g, '') : '';

    // Bank match
    if (detectedBankKey) {
      if (
        accName.includes(detectedBankKey) ||
        bankName.includes(detectedBankKey) ||
        (detectedBankKey === 'adcb' && (accName.includes('adcb') || bankName.includes('abu dhabi commercial'))) ||
        (detectedBankKey === 'enbd' && (accName.includes('enbd') || accName.includes('emirates') || bankName.includes('emirates'))) ||
        (detectedBankKey === 'fab' && (accName.includes('fab') || bankName.includes('first abu dhabi'))) ||
        (detectedBankKey === 'mashreq' && (accName.includes('mashreq') || bankName.includes('mashreq'))) ||
        (detectedBankKey === 'dib' && (accName.includes('dib') || bankName.includes('dubai islamic')))
      ) {
        score += 10;
      }
    }

    // Direct account name match in user voice
    if (accName.length >= 3 && lower.includes(accName)) {
      score += 15;
    }

    // Card last 4 digits match
    if (last4.length === 4 && lower.includes(last4)) {
      score += 20;
    }

    // Type match
    if (wantsCreditCard && acc.type === 'credit_card') {
      score += 5;
    } else if (wantsDebitOrBank && acc.type === 'bank') {
      score += 5;
    }

    if (score > highestScore && score > 0) {
      highestScore = score;
      bestAccount = acc;
    }
  }

  if (bestAccount) {
    return {
      account: bestAccount,
      recognizedBankName: bestAccount.name
    };
  }

  // Fallbacks:
  // If user asked for credit card specifically and has one
  if (wantsCreditCard) {
    const cc = accounts.find(a => a.type === 'credit_card');
    if (cc) return { account: cc, recognizedBankName: cc.name };
  }

  // If detected bank name was recognized (e.g. ADCB) but user hasn't created that account yet
  if (detectedBankLabel) {
    const fallbackAcc = accounts.length > 0 ? accounts[0] : null;
    return {
      account: fallbackAcc,
      recognizedBankName: `${detectedBankLabel} ${wantsCreditCard ? 'Credit Card' : 'Account'}`
    };
  }

  // Default to first account or Cash Wallet
  const defaultAcc = accounts.find(a => a.type === 'cash') || accounts[0] || null;
  return {
    account: defaultAcc,
    recognizedBankName: defaultAcc?.name || 'Default Account'
  };
}

/**
 * Fast client-side JavaScript rules engine for voice expense parsing.
 * Executes instantly (< 1ms) without any network latency.
 */
export function parseVoiceExpenseRules(
  rawTranscript: string,
  accounts: Account[],
  allCategories?: ExpenseCategory[]
): VoiceParseResult {
  const startTime = typeof performance !== 'undefined' ? performance.now() : Date.now();
  const clean = rawTranscript.trim();
  const lower = clean.toLowerCase();

  // 1. Detect Type: Income vs Expense
  const isIncome =
    /\b(salary|credited|income|received|deposit|refund|tankhwah|vetan|aaya|jama|mile|mil\s*gaya|came)\b/i.test(lower) &&
    !/\b(paid|spent|spend|deducted|debited|kharcha|diya|dala|bharwaya|bhara)\b/i.test(lower);
  const type: 'expense' | 'income' = isIncome ? 'income' : 'expense';

  // 2. Extract Amount
  const amount = extractAmountFromVoiceText(clean);

  // 3. Match Bank or Card from existing user accounts database
  const accountMatch = matchAccountFromVoiceText(clean, accounts);
  const matchedAccount = accountMatch.account;
  const accountName = accountMatch.recognizedBankName;

  // 4. Category & Merchant Recognition (English & Hindi)
  // Default category depends on whether user's budget list contains "Petrol" or "Fuel"
  const hasPetrolCategory = !allCategories || allCategories.includes('Petrol');

  let category: ExpenseCategory = 'Other';
  let merchant = 'Expense';

  if (isIncome) {
    category = 'Salary';
    merchant = 'Monthly Salary';
  } else if (/\b(petrol|fuel|diesel|gas|enoc|emarat|adnoc|eppco|cng)\b/i.test(lower)) {
    category = hasPetrolCategory ? 'Petrol' : 'Fuel';
    if (/enoc/i.test(lower)) merchant = 'ENOC Petrol Station';
    else if (/emarat/i.test(lower)) merchant = 'Emarat Petrol Station';
    else if (/adnoc/i.test(lower)) merchant = 'ADNOC Petrol Station';
    else if (/eppco/i.test(lower)) merchant = 'EPPCO Petrol Station';
    else merchant = 'Petrol Station';
  } else if (
    /\b(grocery|groceries|rashan|supermarket|carrefour|lulu|nesto|spinneys|viva|choithrams|al\s*maya|sabzi|fal|milk|dudh|eggs|bread|vegetables|fruits)\b/i.test(
      lower
    )
  ) {
    category = 'Groceries';
    if (/carrefour/i.test(lower)) merchant = 'Carrefour';
    else if (/lulu/i.test(lower)) merchant = 'LuLu Hypermarket';
    else if (/nesto/i.test(lower)) merchant = 'Nesto Hypermarket';
    else if (/spinneys/i.test(lower)) merchant = 'Spinneys';
    else if (/viva/i.test(lower)) merchant = 'VIVA Supermarket';
    else if (/choithrams/i.test(lower)) merchant = 'Choithrams';
    else merchant = 'Supermarket / Groceries';
  } else if (
    /\b(food|khana|lunch|dinner|breakfast|nashta|restaurant|cafe|coffee|starbucks|costa|mcdonalds|mcdonald|kfc|burger|pizza|biryani|chai|tea|talabat|deliveroo|noon\s*food|zomato|dining|eat|shawarma)\b/i.test(
      lower
    )
  ) {
    category = 'Food';
    if (/starbucks/i.test(lower)) merchant = 'Starbucks';
    else if (/costa/i.test(lower)) merchant = 'Costa Coffee';
    else if (/mcdonald/i.test(lower)) merchant = "McDonald's";
    else if (/kfc/i.test(lower)) merchant = 'KFC';
    else if (/talabat/i.test(lower)) merchant = 'Talabat';
    else if (/deliveroo/i.test(lower)) merchant = 'Deliveroo';
    else if (/zomato/i.test(lower)) merchant = 'Zomato';
    else merchant = 'Food & Dining';
  } else if (
    /\b(taxi|cab|careem|uber|metro|nol|bus|salik|toll|parking|transport|gaadi|rickshaw|rta)\b/i.test(lower)
  ) {
    category = 'Transport';
    if (/careem/i.test(lower)) merchant = 'Careem';
    else if (/uber/i.test(lower)) merchant = 'Uber';
    else if (/salik/i.test(lower)) merchant = 'Salik Toll Recharge';
    else if (/metro|nol/i.test(lower)) merchant = 'RTA Dubai Metro (Nol)';
    else if (/parking/i.test(lower)) merchant = 'RTA Parking';
    else merchant = 'Taxi / Transport';
  } else if (
    /\b(clothes?|clothing|kapde|kapda|dress|shirt|pants|shoes|juta|zara|h&m|max|splash|centerpoint|centrepoint|nike|adidas)\b/i.test(
      lower
    )
  ) {
    category = 'Clothing';
    if (/zara/i.test(lower)) merchant = 'Zara';
    else if (/h&m/i.test(lower)) merchant = 'H&M';
    else if (/nike/i.test(lower)) merchant = 'Nike Store';
    else if (/max/i.test(lower)) merchant = 'Max Fashion';
    else merchant = 'Clothing & Apparel';
  } else if (
    /\b(doctor|medicine|dawa|dawai|pharmacy|medical|hospital|clinic|aster|life\s*pharmacy|medcare|boots|health)\b/i.test(
      lower
    )
  ) {
    category = 'Healthcare';
    if (/aster/i.test(lower)) merchant = 'Aster Pharmacy';
    else if (/life\s*pharmacy/i.test(lower)) merchant = 'Life Pharmacy';
    else if (/boots/i.test(lower)) merchant = 'Boots Pharmacy';
    else merchant = 'Pharmacy / Healthcare';
  } else if (
    /\b(dewa|electricity|water|bijli|paani|sewa|aadc|fewa|utility|utilities|bill)\b/i.test(lower) &&
    !/mobile|phone|wifi/i.test(lower)
  ) {
    category = 'Utilities';
    if (/sewa/i.test(lower)) merchant = 'SEWA Electricity & Water';
    else if (/aadc/i.test(lower)) merchant = 'AADC Water & Electricity';
    else merchant = 'DEWA Electricity & Water';
  } else if (
    /\b(du|etisalat|e&|recharge|phone\s*bill|mobile\s*bill|wifi|internet|virgin|sim\s*card)\b/i.test(lower)
  ) {
    category = 'Telecom';
    if (/etisalat|e&/i.test(lower)) merchant = 'e& (Etisalat)';
    else if (/du/i.test(lower)) merchant = 'du Telecom';
    else if (/virgin/i.test(lower)) merchant = 'Virgin Mobile UAE';
    else merchant = 'Mobile & Internet Recharge';
  } else if (
    /\b(shopping|amazon|noon|mall|electronics|gadget|sharaf\s*dg|dubai\s*mall|mall\s*of\s*the\s*emirates)\b/i.test(
      lower
    )
  ) {
    category = 'Shopping';
    if (/amazon/i.test(lower)) merchant = 'Amazon.ae';
    else if (/noon/i.test(lower)) merchant = 'Noon.com';
    else if (/sharaf/i.test(lower)) merchant = 'Sharaf DG';
    else merchant = 'Shopping';
  } else if (/\b(cinema|movie|film|netflix|spotify|entertainment|fun|game|vox|reel)\b/i.test(lower)) {
    category = 'Entertainment';
    if (/vox/i.test(lower)) merchant = 'VOX Cinemas';
    else if (/netflix/i.test(lower)) merchant = 'Netflix';
    else if (/spotify/i.test(lower)) merchant = 'Spotify';
    else merchant = 'Entertainment';
  } else if (/\b(rent|housing|flat|apartment|kiraya|makani|ejari)\b/i.test(lower)) {
    category = 'Rent & Housing';
    merchant = 'Home Rent';
  } else if (/\b(school|college|tuition|fees|education|books|padhai|course)\b/i.test(lower)) {
    category = 'Education';
    merchant = 'Education Fees';
  }

  // 5. Date parsing
  const dateStr = extractDateFromVoiceText(clean);

  // Measure execution duration
  const endTime = typeof performance !== 'undefined' ? performance.now() : Date.now();
  const duration = Math.round((endTime - startTime) * 100) / 100;

  const success = amount > 0;
  const confidence = success && category !== 'Other' ? 'high' : success ? 'medium' : 'low';

  return {
    success,
    amount,
    merchant,
    category,
    matchedAccountId: matchedAccount?.id || null,
    accountName: matchedAccount ? matchedAccount.name : accountName,
    type,
    date: dateStr,
    notes: `Voice Entry: "${clean}"`,
    source: 'js_rules',
    confidence,
    debugTimingMs: duration
  };
}
