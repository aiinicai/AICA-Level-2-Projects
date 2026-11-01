import { ExpenseCategory, StandardExpenseCategory, MerchantRuleCorrection } from '../types/finance';

// Default UAE categorization rules
const BASE_RULES: Record<StandardExpenseCategory, string[]> = {
  'Rent & Housing': [
    'rent', 'rental', 'ejari', 'landlord', 'tenancy', 'cheque', 'housing', 'lease',
    'apartment', 'flat', 'villa', 'property', 'real estate', 'damac', 'emaar',
    'nakheel', 'al futtaim real estate', 'maintenance fee', 'building management', 'service charges'
  ],
  Petrol: [
    'enoc', 'adnoc', 'eppco', 'emarat', 'shell', 'petrol', 'fuel', 'autopro', 'tasjeel'
  ],
  Fuel: [
    'fuel', 'petrol', 'gasoline', 'diesel', 'special 95', 'super 98', 'e-plus 91', 'enoc', 'adnoc', 'emarat'
  ],
  Food: [
    'kfc', 'mcdonald', 'starbucks', 'tim hortons', 'al baik', 'subway', 'texas chicken',
    'hardees', 'costa coffee', 'paul cafe', 'shake shack', 'pizza hut', 'domino', 'papa john',
    'burger king', 'dunkin', 'baskin robbins', 'five guys', 'cheesecake factory', 'nando',
    'wagamama', 'carluccio', 'restaurant', 'cafe', 'cafeteria', 'bakery', 'kitchen', 'bistro', 'dining'
  ],
  Groceries: [
    'carrefour', 'lulu', 'nesto', 'spinneys', 'viva', 'choithrams', 'union coop',
    'grandiose', 'west zone', 'al maya', 'hypermarket', 'supermarket', 'mart', 'grocery'
  ],
  'Food & Groceries': [
    'milk', 'bread', 'rice', 'oil', 'flour', 'sugar', 'fruit', 'fruits', 'apple', 'banana', 'orange',
    'vegetable', 'vegetables', 'tomato', 'potato', 'onion', 'chicken', 'meat', 'beef', 'mutton',
    'fish', 'egg', 'eggs', 'cheese', 'yogurt', 'butter', 'snack', 'snacks', 'biscuit', 'biscuits',
    'chips', 'chocolate', 'water', 'juice', 'beverage', 'tea', 'coffee', 'grocery', 'groceries',
    'supermarket', 'hypermarket', 'nesto', 'lulu', 'carrefour', 'spinneys', 'viva', 'choithrams'
  ],
  Clothing: [
    'shirt', 't-shirt', 'pants', 'trousers', 'jeans', 'dress', 'skirt', 'jacket', 'coat',
    'suit', 'tie', 'shoes', 'sneakers', 'sandals', 'footwear', 'apparel', 'garment', 'garments',
    'clothing', 'socks', 'underwear', 'abaya', 'kandura', 'scarf', 'belt', 'cap', 'hat',
    'cotton', 'fabric', 'zara', 'h&m', 'max fashion', 'splash', 'centrepoint', 'redtag', 'brands for less'
  ],
  Utilities: [
    'dewa', 'sewa', 'fewa', 'aadc', 'addc', 'empower', 'tabreed', 'utility', 'electricity', 'water'
  ],
  Telecom: [
    'etisalat', 'e&', ' du ', 'du telecom', 'emirates integrated', 'virgin mobile'
  ],
  Shopping: [
    'amazon', 'noon', 'namshi', 'zara', 'h&m', 'apple store', 'sharaf dg', 'centrepoint',
    'max fashion', 'splash', 'sephora', 'ikea', 'shein', 'asos', 'bath & body works',
    'sun & sand', 'adidas', 'nike', 'virgin megastore', 'jumbo', 'fashion'
  ],
  Transport: [
    'rta', 'salik', 'careem', 'uber', 'dubai taxi', 'darb', 'm-parking', 'parkonic',
    'metro', 'tram', 'bus', 'toll'
  ],
  Healthcare: [
    'aster', 'life pharmacy', 'boots pharmacy', 'supercare', 'nmc', 'medcare',
    'aster hospital', 'prime medical', 'mediclinic', 'pharmacy', 'clinic', 'hospital',
    'medicine', 'panadol', 'paracetamol', 'vitamins', 'tablet', 'syrup', 'bandage'
  ],
  Entertainment: [
    'netflix', 'spotify', 'vox cinemas', 'reel cinemas', 'osn', 'youtube', 'anghami',
    'disney', 'playstation', 'steam', 'xbox', 'cinema', 'theatre', 'ski dubai', 'atlantis aquaventure'
  ],
  Travel: [
    'flydubai', 'emirates air', 'air arabia', 'etihad', 'booking.com', 'airbnb', 'agoda',
    'expedia', 'qatar airways', 'hotel', 'resort', 'flight'
  ],
  Education: [
    'gems education', 'taaleem', 'school', 'university', 'college', 'academy', 'coursera', 'udemy'
  ],
  Salary: [
    'salary', 'wps', 'payroll', 'stipend', 'allowance', 'wages', 'salary transfer', 'salary deposit'
  ],
  Other: []
};

// Known popular UAE & Global Merchants dictionary
export const KNOWN_MERCHANTS: { name: string; keywords: string[]; category: ExpenseCategory }[] = [
  { name: 'Amazon Prime', keywords: ['amazon prime', 'prime video', 'amzn prime'], category: 'Entertainment' },
  { name: 'Amazon', keywords: ['amazon', 'amzn', 'amazon.ae', 'amazon.com', 'amazon payments'], category: 'Shopping' },
  { name: 'Noon', keywords: ['noon', 'noon.com', 'noon payments', 'noon daily', 'now now'], category: 'Shopping' },
  { name: 'Carrefour', keywords: ['carrefour', 'carrefouruae', 'crf'], category: 'Groceries' },
  { name: 'Lulu Hypermarket', keywords: ['lulu', 'lulu hypermarket', 'lulu webstore', 'lulu express'], category: 'Groceries' },
  { name: 'Nesto', keywords: ['nesto', 'nesto hypermarket'], category: 'Groceries' },
  { name: 'Spinneys', keywords: ['spinneys'], category: 'Groceries' },
  { name: 'Viva Supermarket', keywords: ['viva', 'viva supermarket'], category: 'Groceries' },
  { name: 'Union Coop', keywords: ['union coop', 'union cooperative'], category: 'Groceries' },
  { name: 'Choithrams', keywords: ['choithrams'], category: 'Groceries' },
  { name: 'Talabat', keywords: ['talabat'], category: 'Food' },
  { name: 'Deliveroo', keywords: ['deliveroo'], category: 'Food' },
  { name: 'Careem', keywords: ['careem', 'careem pay', 'careem box', 'careem food'], category: 'Transport' },
  { name: 'Uber', keywords: ['uber', 'uber eats'], category: 'Transport' },
  { name: 'Dubai Taxi / RTA', keywords: ['rta', 'dubai taxi', 'salik', 'darb', 'm-parking', 'parkonic', 'metro'], category: 'Transport' },
  { name: 'ENOC', keywords: ['enoc', 'eppco', 'autopro', 'tasjeel'], category: 'Petrol' },
  { name: 'ADNOC', keywords: ['adnoc', 'adnoc distribution'], category: 'Petrol' },
  { name: 'Emarat', keywords: ['emarat'], category: 'Petrol' },
  { name: 'DEWA', keywords: ['dewa', 'dubai electricity'], category: 'Utilities' },
  { name: 'SEWA', keywords: ['sewa', 'sharjah electricity'], category: 'Utilities' },
  { name: 'Etisalat', keywords: ['etisalat', 'e&', 'etisalat by e&'], category: 'Telecom' },
  { name: 'Du', keywords: ['du telecom', 'du recharge', 'du mobile', 'du postpaid', 'du prepaid', 'du bill', 'emirates integrated'], category: 'Telecom' },
  { name: 'McDonald\'s', keywords: ['mcdonald', 'mcdonalds'], category: 'Food' },
  { name: 'KFC', keywords: ['kfc'], category: 'Food' },
  { name: 'Starbucks', keywords: ['starbucks'], category: 'Food' },
  { name: 'Tim Hortons', keywords: ['tim hortons'], category: 'Food' },
  { name: 'Subway', keywords: ['subway'], category: 'Food' },
  { name: 'Al Baik', keywords: ['al baik', 'albaik'], category: 'Food' },
  { name: 'Apple', keywords: ['apple.com/bill', 'itunes', 'apple store', 'apple services'], category: 'Shopping' },
  { name: 'Netflix', keywords: ['netflix'], category: 'Entertainment' },
  { name: 'Spotify', keywords: ['spotify'], category: 'Entertainment' },
  { name: 'Steam', keywords: ['steam', 'steampowered'], category: 'Entertainment' },
  { name: 'PlayStation', keywords: ['playstation', 'psn'], category: 'Entertainment' },
  { name: 'YouTube', keywords: ['youtube', 'google *youtube'], category: 'Entertainment' },
  { name: 'IKEA', keywords: ['ikea'], category: 'Shopping' },
  { name: 'Zara', keywords: ['zara'], category: 'Shopping' },
  { name: 'H&M', keywords: ['h&m', 'hm.com'], category: 'Shopping' },
  { name: 'Sharaf DG', keywords: ['sharaf dg', 'sharafdg'], category: 'Shopping' },
  { name: 'Life Pharmacy', keywords: ['life pharmacy'], category: 'Healthcare' },
  { name: 'Aster Pharmacy', keywords: ['aster pharmacy', 'aster clinic', 'aster hospital'], category: 'Healthcare' },
  { name: 'Ejari / Tenancy Rent', keywords: ['ejari', 'tenancy contract', 'rental cheque', 'rent payment', 'dubai rest'], category: 'Rent & Housing' },
  { name: 'Emaar Properties', keywords: ['emaar', 'emaar properties', 'emaar community'], category: 'Rent & Housing' },
  { name: 'Damac Properties', keywords: ['damac'], category: 'Rent & Housing' },
  { name: 'Aldar Properties', keywords: ['aldar'], category: 'Rent & Housing' },
  { name: 'Nakheel', keywords: ['nakheel'], category: 'Rent & Housing' }
];

// Normalize and clean merchant name for robust matching
export function cleanMerchantName(raw: string): string {
  if (!raw || !raw.trim()) return 'Unknown Merchant';

  let cleaned = raw
    // Strip common bank alert prefixes
    .replace(/^(?:POS PURCHASE|PURCHASE AT|PAYMENT TO|TRX AT|DEBIT:?|CARD TRX AT|USED FOR|SPENT AT|CHARGE AT|TRANSACTION AT|DEBITED AT|INFO:?|MERCHANT:?)\s+/i, '')
    // Strip "AED ... at " or "USD ... at " patterns that might be accidentally captured
    .replace(/^(?:AED|DHS|DIRHAM|USD|\$)\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?\s*(?:AT|FOR|TO)?\s+/i, '')
    // Strip "card ending in XXXX was used for ... at"
    .replace(/^.*?\b(?:was used for|was charged|spent|purchase of)\s+(?:AED|DHS|DIRHAM|USD|\$)?\s*[0-9.]*\s*(?:at|to)?\s+/i, '')
    // Strip card mask prefixes like "0032 was used for AED 26.14 at"
    .replace(/^[0-9*x•]{3,6}\s+(?:was used for|spent|purchase of|debited).*?\b(?:at|to)\s+/i, '')
    // Strip leading "at " or "to "
    .replace(/^(?:at|to|in)\s+/i, '')
    // Strip mall and branch suffixes
    .replace(/\s+(MALL OF THE EMIRATES|DUBAI MALL|MIRDIF|DEIRA|ABU DHABI|SHARJAH|BRANCH \d+|STORE \d+|DXB|UAE|AE|LLC|FZCO|ME)\b/gi, '')
    // Replace punctuation with space
    .replace(/[*#\-_]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  // If after cleaning it's just numbers, symbols, or empty, return Unknown Merchant
  if (!cleaned || /^[0-9\s.,]+$/.test(cleaned) || cleaned.length < 2) {
    return 'Unknown Merchant';
  }

  // Capitalize nicely if all uppercase
  if (cleaned === cleaned.toUpperCase() && cleaned.length > 3) {
    cleaned = cleaned
      .toLowerCase()
      .split(' ')
      .map(w => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }

  return cleaned;
}

/**
 * Categorize a merchant name, consulting learned user corrections first,
 * then fuzzy substring rules.
 */
export function categorizeMerchant(
  merchantRaw: string,
  userCorrections: MerchantRuleCorrection[] = []
): ExpenseCategory {
  const normalized = merchantRaw.toLowerCase().trim();

  // 1. First check user custom corrections (highest priority)
  for (const correction of userCorrections) {
    const keyword = correction.merchantKeyword.toLowerCase().trim();
    if (keyword && normalized.includes(keyword)) {
      return correction.category;
    }
  }

  // 2. Check predefined UAE base rules
  for (const [category, keywords] of Object.entries(BASE_RULES) as [ExpenseCategory, string[]][]) {
    for (const keyword of keywords) {
      if (normalized.includes(keyword)) {
        return category;
      }
    }
  }

  return 'Other';
}

/**
 * Detects red flags such as foreign currency, overseas purchases, unusually high amounts.
 */
export function detectRedFlag(params: {
  currency: string;
  amount: number;
  merchant: string;
  highThresholdAED?: number;
}): { isRedFlag: boolean; reason?: string } {
  const { currency, amount, merchant, highThresholdAED = 1500 } = params;
  const curr = currency.toUpperCase().trim();
  const lowerMerchant = merchant.toLowerCase();

  // 1. Foreign Currency Flag
  if (curr && curr !== 'AED' && curr !== 'DIRHAM' && curr !== 'DHS') {
    return {
      isRedFlag: true,
      reason: `Foreign currency transaction (${curr}) outside UAE standard.`
    };
  }

  // 2. Foreign / International Merchant indicator
  const foreignIndicators = ['steam', 'apple.com/bill', 'google *temp', 'amazon us', 'alibaba', 'aliexpress', 'paypal *uk', 'stripe *ca', 'hotel booking intl'];
  for (const ind of foreignIndicators) {
    if (lowerMerchant.includes(ind)) {
      return {
        isRedFlag: true,
        reason: 'International online service detected outside UAE domestic network.'
      };
    }
  }

  // 3. Unusually High Amount Flag
  if (amount > highThresholdAED) {
    return {
      isRedFlag: true,
      reason: `Unusually high transaction (> AED ${highThresholdAED.toLocaleString()}).`
    };
  }

  return { isRedFlag: false };
}

/**
 * Categorizes an individual item line extracted from a receipt or bill.
 */
export function categorizeReceiptItem(itemName: string): ExpenseCategory {
  if (!itemName || !itemName.trim()) return 'Food & Groceries';
  const clean = itemName.toLowerCase().trim();

  // Check Clothing
  const clothingKeywords = [
    'shirt', 't-shirt', 'pants', 'trousers', 'jeans', 'dress', 'skirt', 'jacket', 'coat',
    'suit', 'tie', 'shoes', 'sneakers', 'sandals', 'footwear', 'apparel', 'garment', 'garments',
    'clothing', 'socks', 'underwear', 'abaya', 'kandura', 'scarf', 'belt', 'cap', 'hat',
    'cotton', 'linen', 'polo', 'denim', 'blazer', 'hoodie', 'shorts'
  ];
  for (const kw of clothingKeywords) {
    if (clean.includes(kw)) return 'Clothing';
  }

  // Check Fuel
  const fuelKeywords = ['petrol', 'fuel', 'special 95', 'super 98', 'e-plus 91', 'diesel', 'gasoline'];
  for (const kw of fuelKeywords) {
    if (clean.includes(kw)) return 'Fuel';
  }

  // Check Healthcare
  const healthKeywords = ['panadol', 'paracetamol', 'medicine', 'pharmacy', 'vitamin', 'syrup', 'tablet', 'bandage', 'mask', 'ointment', 'drops', 'antiseptic', 'dettol', 'plaster'];
  for (const kw of healthKeywords) {
    if (clean.includes(kw)) return 'Healthcare';
  }

  // Check Transport
  const transportKeywords = ['taxi', 'careem', 'uber', 'metro', 'parking', 'salik', 'toll', 'bus'];
  for (const kw of transportKeywords) {
    if (clean.includes(kw)) return 'Transport';
  }

  // Check Utilities & Telecom
  const utilKeywords = ['electricity', 'water', 'gas', 'dewa', 'recharge', 'sim', 'du', 'etisalat'];
  for (const kw of utilKeywords) {
    if (clean.includes(kw)) return 'Utilities';
  }

  // Check Electronics / Shopping
  const shoppingKeywords = ['cable', 'charger', 'usb', 'headphones', 'battery', 'plug', 'case', 'lamp', 'towel', 'bedsheet', 'pillow'];
  for (const kw of shoppingKeywords) {
    if (clean.includes(kw)) return 'Shopping';
  }

  // Check Food & Groceries
  const foodKeywords = [
    'milk', 'bread', 'rice', 'oil', 'flour', 'sugar', 'fruit', 'apple', 'banana', 'orange',
    'vegetable', 'tomato', 'potato', 'onion', 'chicken', 'meat', 'beef', 'mutton', 'fish',
    'egg', 'eggs', 'cheese', 'yogurt', 'butter', 'snack', 'biscuit', 'chips', 'chocolate',
    'water', 'juice', 'beverage', 'tea', 'coffee', 'grocery', 'produce', 'curry', 'rice',
    'biryani', 'sandwich', 'burger', 'pizza', 'salad', 'pasta', 'sauce', 'spices', 'salt'
  ];
  for (const kw of foodKeywords) {
    if (clean.includes(kw)) return 'Food & Groceries';
  }

  return 'Food & Groceries';
}
