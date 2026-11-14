import type { BlockedRule, ExpenseHead, RcmRule, TdsRate } from './types';

// IMPORTANT: every rate/rule below is a STARTING POINT taken from secondary sources and is shipped
// with verified=false. The Compliance panel keeps flagging them until a CA verifies each one against
// the Income-tax Act 2025 / Income-tax Rules 2026 and CGST notifications. Nothing here is final.

const SRC = 'Secondary tax sites (Oct 2026) — verify against Income-tax Act 2025, Sec 393 table';

export const TDS_RATES: TdsRate[] = [
  { code: 'CONTRACT_IND', description: 'Payment to contractor — Individual / HUF', ratePct: 1, thresholdSingle: 30000, thresholdAggregate: 100000, appliesToEntity: ['P', 'H'], noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC },
  { code: 'CONTRACT_OTH', description: 'Payment to contractor — Others', ratePct: 2, thresholdSingle: 30000, thresholdAggregate: 100000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC },
  { code: 'PROF_FEES', description: 'Fees for professional services', ratePct: 10, thresholdAggregate: 50000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC },
  { code: 'TECH_FEES', description: 'Fees for technical services', ratePct: 2, thresholdAggregate: 50000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC },
  { code: 'RENT_LB', description: 'Rent — land, building, furniture', ratePct: 10, thresholdSingle: 50000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC + ' (threshold is per month; sources differ)' },
  { code: 'RENT_PM', description: 'Rent — plant, machinery, equipment', ratePct: 2, thresholdSingle: 50000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC + ' (sources differ)' },
  { code: 'COMMISSION', description: 'Commission or brokerage', ratePct: 2, thresholdAggregate: 20000, noPanRatePct: 20, effectiveFrom: '2026-04-01', verified: false, sourceNote: SRC }
];

// RCM on services: Notification 13/2017-Central Tax (Rate) as amended. Purchases from unregistered
// suppliers attract RCM ONLY for notified categories — it is not a blanket rule on every non-GST bill.
export const RCM_RULES: RcmRule[] = [
  { code: 'GTA', description: 'Goods Transport Agency (where GTA has not opted for forward charge)', supplierCondition: 'any', notificationRef: 'N 13/2017-CT(R)', defaultRatePct: 5, supply: 'services', verified: false },
  { code: 'ADVOCATE', description: 'Legal services by advocate / firm of advocates', supplierCondition: 'any', notificationRef: 'N 13/2017-CT(R)', defaultRatePct: 18, supply: 'services', verified: false },
  { code: 'SECURITY', description: 'Security services by a non-body-corporate supplier', supplierCondition: 'non_body_corporate', notificationRef: 'N 13/2017-CT(R)', defaultRatePct: 18, supply: 'services', verified: false },
  { code: 'SPONSORSHIP', description: 'Sponsorship services', supplierCondition: 'any', notificationRef: 'N 13/2017-CT(R)', defaultRatePct: 18, supply: 'services', verified: false },
  { code: 'DIRECTOR', description: 'Services by a director to the company', supplierCondition: 'any', notificationRef: 'N 13/2017-CT(R)', defaultRatePct: 18, supply: 'services', verified: false },
  { code: 'RENT_UNREG', description: 'Renting of commercial property by an unregistered person', supplierCondition: 'unregistered', notificationRef: 'N 13/2017-CT(R) as amended (2024)', defaultRatePct: 18, supply: 'services', verified: false }
];

// Section 17(5) CGST Act — blocked input tax credit (summary; exceptions apply).
export const BLOCKED_RULES: BlockedRule[] = [
  { code: 'MOTOR_VEHICLE', description: 'Motor vehicles & related repairs/insurance (exceptions apply)', keywords: ['car', 'vehicle', 'petrol', 'diesel', 'fuel', 'tyre'] },
  { code: 'FOOD', description: 'Food & beverages, outdoor catering', keywords: ['food', 'restaurant', 'catering', 'meal', 'snacks', 'lunch', 'dinner', 'tea'] },
  { code: 'CLUB', description: 'Club, health & fitness centre membership', keywords: ['club', 'gym', 'fitness', 'membership'] },
  { code: 'BEAUTY_HEALTH', description: 'Beauty treatment, health services, cosmetic surgery', keywords: ['salon', 'spa', 'beauty', 'hospital', 'clinic'] },
  { code: 'INSURANCE_LIFE', description: 'Life / health insurance (unless obligatory under law)', keywords: ['life insurance', 'health insurance', 'mediclaim'] },
  { code: 'RENT_A_CAB', description: 'Rent-a-cab (exceptions apply)', keywords: ['cab', 'taxi', 'uber', 'ola'] },
  { code: 'CONSTRUCTION', description: 'Construction / works contract for immovable property', keywords: ['construction', 'civil work', 'building work'] },
  { code: 'GIFTS', description: 'Gifts, free samples, personal consumption', keywords: ['gift', 'diwali gift', 'sample'] }
];

export const EXPENSE_HEADS: ExpenseHead[] = [
  { id: 'h-rent', name: 'Office Rent', tallyLedger: 'Rent', keywords: ['rent', 'lease', 'premises'], sacHsnPrefixes: ['9972'], defaultTdsCode: 'RENT_LB' },
  { id: 'h-prof', name: 'Professional Fees', tallyLedger: 'Professional Fees', keywords: ['consult', 'professional', 'audit', 'ca fees', 'advisory', 'architect'], sacHsnPrefixes: ['9982', '9983'], defaultTdsCode: 'PROF_FEES' },
  { id: 'h-legal', name: 'Legal Fees', tallyLedger: 'Legal Fees', keywords: ['advocate', 'legal', 'lawyer', 'court'], sacHsnPrefixes: ['998211', '998212', '998213', '998214', '998215', '998216'], defaultTdsCode: 'PROF_FEES', rcmCode: 'ADVOCATE' },
  { id: 'h-contract', name: 'Contract Labour / Job Work', tallyLedger: 'Contract Labour', keywords: ['labour', 'contract', 'job work', 'manpower', 'housekeeping'], sacHsnPrefixes: ['9985', '9988'], defaultTdsCode: 'CONTRACT_OTH' },
  { id: 'h-security', name: 'Security Charges', tallyLedger: 'Security Charges', keywords: ['security', 'guard', 'watchman'], sacHsnPrefixes: ['998521', '998522', '998523', '998524', '998525'], defaultTdsCode: 'CONTRACT_OTH', rcmCode: 'SECURITY' },
  { id: 'h-repair', name: 'Repairs & Maintenance', tallyLedger: 'Repairs & Maintenance', keywords: ['repair', 'maintenance', 'service charge', 'amc', 'plumb', 'electrician'], sacHsnPrefixes: ['9987'], defaultTdsCode: 'CONTRACT_OTH' },
  { id: 'h-freight', name: 'Freight & Cartage', tallyLedger: 'Freight Inward', keywords: ['freight', 'transport', 'cartage', 'lorry', 'truck', 'logistics'], sacHsnPrefixes: ['9965'], defaultTdsCode: 'CONTRACT_OTH', rcmCode: 'GTA' },
  { id: 'h-courier', name: 'Courier & Postage', tallyLedger: 'Courier Charges', keywords: ['courier', 'post', 'speed post', 'dtdc', 'bluedart', 'delhivery'], sacHsnPrefixes: ['9968'] },
  { id: 'h-travel', name: 'Travelling & Conveyance', tallyLedger: 'Travelling Expenses', keywords: ['travel', 'flight', 'train', 'hotel', 'irctc', 'airline', 'conveyance'], sacHsnPrefixes: ['9964', '9963'] },
  { id: 'h-staff', name: 'Staff Welfare', tallyLedger: 'Staff Welfare', keywords: ['tea', 'snacks', 'food', 'refreshment', 'lunch', 'canteen'], sacHsnPrefixes: ['9963'], blocked175: 'FOOD' },
  { id: 'h-vehicle', name: 'Vehicle Running & Maintenance', tallyLedger: 'Vehicle Expenses', keywords: ['petrol', 'diesel', 'fuel', 'car wash', 'tyre'], sacHsnPrefixes: ['2710', '4011'], blocked175: 'MOTOR_VEHICLE' },
  { id: 'h-print', name: 'Printing & Stationery', tallyLedger: 'Printing & Stationery', keywords: ['stationery', 'printing', 'paper', 'pen', 'toner', 'cartridge'], sacHsnPrefixes: ['4802', '4820', '4817', '9608', '8443'] },
  { id: 'h-phone', name: 'Telephone & Internet', tallyLedger: 'Telephone & Internet', keywords: ['airtel', 'jio', 'vodafone', 'broadband', 'internet', 'mobile bill', 'bsnl'], sacHsnPrefixes: ['9984'] },
  { id: 'h-power', name: 'Electricity', tallyLedger: 'Electricity Charges', keywords: ['electricity', 'power', 'discom', 'bescom', 'msedcl', 'tata power'], sacHsnPrefixes: ['2716'] },
  { id: 'h-software', name: 'Software & Subscriptions', tallyLedger: 'Software Expenses', keywords: ['software', 'subscription', 'license', 'saas', 'cloud', 'google workspace', 'microsoft'], sacHsnPrefixes: ['9973', '9983'] },
  { id: 'h-advt', name: 'Advertisement & Marketing', tallyLedger: 'Advertisement', keywords: ['advertis', 'marketing', 'promotion', 'hoarding', 'facebook ads', 'google ads'], sacHsnPrefixes: ['9983'], defaultTdsCode: 'CONTRACT_OTH' },
  { id: 'h-commission', name: 'Commission & Brokerage', tallyLedger: 'Commission', keywords: ['commission', 'brokerage'], sacHsnPrefixes: ['9961', '9962'], defaultTdsCode: 'COMMISSION' },
  { id: 'h-bank', name: 'Bank Charges', tallyLedger: 'Bank Charges', keywords: ['bank charges', 'processing fee', 'neft', 'rtgs'], sacHsnPrefixes: ['9971'] },
  { id: 'h-misc', name: 'Miscellaneous Expenses', tallyLedger: 'Miscellaneous Expenses', keywords: [], sacHsnPrefixes: [] }
];

/** Common GST rates the user can pick from in one tap. */
export const GST_RATES = [0, 5, 12, 18, 28];
/** GST 2.0 (CBIC rate notifications effective 22-09-2025): 12% and 28% slabs abolished; main rates 5 / 18 / 40.
 *  Bills dated earlier keep the old slabs. 3% (bullion/jewellery) and 0.25% (rough diamonds) are rare and typed in Review. */
export const GST2_FROM = '2025-09-22';
export const GST_RATES_GST2 = [0, 5, 18, 40];
export const gstRatesOn = (isoDate: string) => (isoDate >= GST2_FROM ? GST_RATES_GST2 : GST_RATES);
/** Every slab a bill can legitimately carry, either regime (used when reading OCR / QR / imports). */
export const ALL_GST_RATES = [0, 0.25, 3, 5, 12, 18, 28, 40];

/** Shown when a bill is saved without a photo or file. Reason is stored, shown to the CA and flagged. */
export const NO_IMAGE_REASONS: { code: string; en: string; hi: string }[] = [
  { code: 'not_received', en: 'Bill not received yet', hi: 'बिल अभी नहीं मिला' },
  { code: 'lost', en: 'Bill lost / damaged', hi: 'बिल खो गया / खराब हो गया' },
  { code: 'with_someone', en: 'Bill is with someone else', hi: 'बिल किसी और के पास है' },
  { code: 'emailed', en: 'Bill came by e-mail / WhatsApp — will upload later', hi: 'बिल ई-मेल / व्हाट्सऐप पर आया — बाद में अपलोड करेंगे' },
  { code: 'no_bill_issued', en: 'Vendor does not give bills (auto, porter, etc.)', hi: 'विक्रेता बिल नहीं देता (ऑटो, कुली आदि)' },
  { code: 'self_voucher', en: 'Internal voucher / petty cash slip', hi: 'आंतरिक वाउचर / पेटी कैश पर्ची' },
  { code: 'other', en: 'Other reason', hi: 'अन्य कारण' },
  // set only by the Excel import of old bills (admins) — not offered on the capture screen
  { code: 'imported', en: 'Old bill imported from Excel — paper copy with client', hi: 'पुराना बिल Excel से आयात — काग़ज़ी कॉपी क्लाइंट के पास' }
];
