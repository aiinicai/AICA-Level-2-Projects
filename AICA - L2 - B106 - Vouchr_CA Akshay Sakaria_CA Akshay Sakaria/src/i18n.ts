// Staff-facing screens are bilingual. Admin/CA screens stay English in v0.1.
import { HI } from './i18n-hi';
import { useStore } from './data/store';

const en = {
  hello: 'Hello',
  snap: 'Snap invoice',
  snapHint: 'Take a clear photo of the full bill',
  scanQr: 'Scan e-invoice QR',
  typeIt: 'Type it in',
  recent: 'Your recent entries',
  home: 'Home',
  entries: 'Entries',
  dues: 'Dues',
  alerts: 'Alerts',
  more: 'More',
  vendor: 'Shop / vendor name',
  vendorGstin: 'Vendor GSTIN (if on bill)',
  invoiceNo: 'Bill number',
  invoiceDate: 'Bill date',
  amount: 'Amount before GST',
  gstRate: 'GST on bill',
  noGst: 'No GST',
  discount: 'Discount',
  addDiscount: '+ Add discount',
  total: 'Bill total',
  whatFor: 'What was it for? (optional)',
  paid: 'Already paid?',
  notPaid: 'Not yet',
  cash: 'Cash',
  bank: 'Bank / UPI',
  paidOn: 'Paid on',
  save: 'Save',
  saved: 'Saved!',
  savedHint: 'Your CA team will check the tax details. Nothing more to do.',
  another: 'Snap another',
  done: 'Done',
  retake: 'Retake',
  status_submitted: 'With CA',
  status_approved: 'Checked',
  status_rejected: 'Returned',
  status_posted: 'Posted',
  status_draft: 'Draft',
  markPaid: 'Mark paid',
  nothingDue: 'Nothing pending. 🎉',
  offline: 'You are offline — entries will sync automatically',
  qrFound: 'e-Invoice QR read — details filled in',
  readingDemo: 'Demo mode: AI bill-reading switches on when the backend is connected. Please type the details.',
  logout: 'Sign out',
  language: 'भाषा: हिंदी',
  uploadFile: 'Upload photo / PDF',
  noBill: 'No bill photo? Tell us why',
  chooseReason: 'Choose a reason',
  otherReason: 'Type the reason',
  needPhotoOrReason: 'Add a bill photo, or choose why there is none',
  needVendor: 'Enter the vendor name',
  needAmount: 'Enter the bill total',
  badGstin: 'Fix the GSTIN or leave it blank',
  pastMonthStaff: 'Bills from earlier months can only be added by your admin.',
  monthLocked: 'This month is locked.',
  pastDatedAdmin: 'Past-dated entry — will be flagged in the audit trail.',
  gstNoGstin: 'GST is charged — please add the vendor GSTIN from the bill.',
  beforeDiscount: 'Before discount',
  taxable: 'Taxable value',
  earlierDate: 'Earlier date noted for audit.',
  moreDetails: 'More details (optional)',
  hsnLabel: 'HSN / SAC code (if printed on bill)',
  reading: 'Reading the bill…',
  photoDup: 'This photo was already saved',
  readOk: 'Details read from the bill — please check the amount.',
  readFail: 'Could not read this bill — please type the details.',
  fixResubmit: 'Fix & resubmit',
  caNote: 'CA note',
  resubmitted: 'Sent back to CA',
  savedVendor: 'Saved vendor',
  notRegistered: 'not GST registered',
  gstinOk: 'GSTIN looks correct',
  noEntries: 'No bills yet. Tap “Snap invoice” to add your first one.',
  confirmLogout: 'Sign out of the app?',
  attached: 'File attached',
  photo: 'Photo',
  fileTooBig: 'File is larger than 10 MB',
  discountTooBig: 'Discount cannot be more than the bill amount'
};

type Dict = typeof en;

const hi: Dict = {
  hello: 'नमस्ते',
  snap: 'बिल की फोटो लें',
  snapHint: 'पूरे बिल की साफ़ फोटो लें',
  scanQr: 'ई-इनवॉइस QR स्कैन करें',
  typeIt: 'खुद लिखें',
  recent: 'आपकी हाल की एंट्री',
  home: 'होम',
  entries: 'एंट्री',
  dues: 'बकाया',
  alerts: 'सूचनाएँ',
  more: 'और',
  vendor: 'दुकान / विक्रेता का नाम',
  vendorGstin: 'विक्रेता GSTIN (अगर बिल पर हो)',
  invoiceNo: 'बिल नंबर',
  invoiceDate: 'बिल की तारीख',
  amount: 'GST से पहले राशि',
  gstRate: 'बिल पर GST',
  noGst: 'GST नहीं',
  discount: 'छूट',
  addDiscount: '+ छूट जोड़ें',
  total: 'बिल कुल',
  whatFor: 'किस लिए था? (वैकल्पिक)',
  paid: 'भुगतान हो गया?',
  notPaid: 'अभी नहीं',
  cash: 'नकद',
  bank: 'बैंक / UPI',
  paidOn: 'भुगतान की तारीख',
  save: 'सेव करें',
  saved: 'सेव हो गया!',
  savedHint: 'टैक्स की जाँच आपकी CA टीम करेगी। आपको और कुछ नहीं करना है।',
  another: 'एक और बिल',
  done: 'हो गया',
  retake: 'फिर से लें',
  status_submitted: 'CA के पास',
  status_approved: 'जाँचा गया',
  status_rejected: 'वापस भेजा',
  status_posted: 'पोस्ट हुआ',
  status_draft: 'ड्राफ्ट',
  markPaid: 'भुगतान दर्ज करें',
  nothingDue: 'कुछ बकाया नहीं। 🎉',
  offline: 'आप ऑफ़लाइन हैं — एंट्री अपने आप सिंक होंगी',
  qrFound: 'ई-इनवॉइस QR पढ़ लिया — जानकारी भर दी गई',
  readingDemo: 'डेमो मोड: बैकएंड जुड़ने पर AI बिल पढ़ेगा। कृपया जानकारी लिखें।',
  logout: 'साइन आउट',
  language: 'Language: English',
  uploadFile: 'फोटो / PDF अपलोड करें',
  noBill: 'बिल की फोटो नहीं है? कारण बताएँ',
  chooseReason: 'कारण चुनें',
  otherReason: 'कारण लिखें',
  needPhotoOrReason: 'बिल की फोटो लगाएँ, या कारण चुनें',
  needVendor: 'विक्रेता का नाम लिखें',
  needAmount: 'बिल कुल राशि लिखें',
  badGstin: 'GSTIN ठीक करें या खाली छोड़ें',
  pastMonthStaff: 'पिछले महीनों के बिल केवल आपके एडमिन जोड़ सकते हैं।',
  monthLocked: 'यह महीना लॉक है।',
  pastDatedAdmin: 'पुरानी तारीख की एंट्री — ऑडिट में दर्ज होगी।',
  gstNoGstin: 'GST लगा है — कृपया बिल से विक्रेता का GSTIN डालें।',
  beforeDiscount: 'छूट से पहले',
  taxable: 'कर योग्य राशि',
  earlierDate: 'पुरानी तारीख ऑडिट में दर्ज होगी।',
  moreDetails: 'और जानकारी (वैकल्पिक)',
  hsnLabel: 'HSN / SAC कोड (अगर बिल पर हो)',
  reading: 'बिल पढ़ा जा रहा है…',
  photoDup: 'यह फोटो पहले ही सेव है',
  readOk: 'बिल से जानकारी पढ़ ली — राशि जाँच लें।',
  readFail: 'बिल नहीं पढ़ पाए — कृपया जानकारी लिखें।',
  fixResubmit: 'ठीक करके फिर भेजें',
  caNote: 'CA की टिप्पणी',
  resubmitted: 'CA को फिर भेजा गया',
  savedVendor: 'सेव विक्रेता',
  notRegistered: 'GST में पंजीकृत नहीं',
  gstinOk: 'GSTIN सही लग रहा है',
  noEntries: 'अभी कोई बिल नहीं। पहला बिल जोड़ने के लिए “बिल की फोटो लें” दबाएँ।',
  confirmLogout: 'ऐप से साइन आउट करें?',
  attached: 'फ़ाइल लगी है',
  photo: 'फोटो',
  fileTooBig: 'फ़ाइल 10 MB से बड़ी है',
  discountTooBig: 'छूट बिल राशि से ज़्यादा नहीं हो सकती'
};

export type TKey = keyof Dict;

export function useLang() {
  return useStore().s.lang;
}

export function useT() {
  const { s } = useStore();
  const d = s.lang === 'hi' ? hi : en;
  return (k: TKey) => d[k];
}

/**
 * Whole-platform translation: the English text is the key (`tr('Review queue')`), with {placeholders}.
 * src/i18n.test.ts fails the build if any tr('…') literal in the app has no Hindi entry.
 */
export function useTr() {
  const lang = useStore().s.lang;
  return (en: string, vars?: Record<string, string | number>) => {
    let out = lang === 'hi' ? HI[en] ?? en : en;
    if (vars) for (const [k, v] of Object.entries(vars)) out = out.split(`{${k}}`).join(String(v));
    return out;
  };
}
