import XLSX from 'xlsx';

export function parseAnyDate(raw) {
  if (raw === null || raw === undefined) return null;
  if (raw instanceof Date) {
    if (isNaN(raw.getTime())) return null;
    const y = raw.getFullYear();
    const m = String(raw.getMonth() + 1).padStart(2, '0');
    const d = String(raw.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  const str = String(raw).trim();
  if (!str) return null;

  // 1. Number / Excel serial date (e.g. 45400)
  if (/^\d{4,6}(\.\d+)?$/.test(str)) {
    const serial = parseFloat(str);
    const utcDays = Math.floor(serial - 25569);
    const date = new Date(utcDays * 86400 * 1000);
    if (!isNaN(date.getTime())) {
      const y = date.getUTCFullYear();
      const m = String(date.getUTCMonth() + 1).padStart(2, '0');
      const d = String(date.getUTCDate()).padStart(2, '0');
      return `${y}-${m}-${d}`;
    }
  }

  const MONTH_MAP = {
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
    jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
  };

  // 2. DD-MMM-YY or DD-MMM-YYYY or DD MMM YYYY
  const dmyAlpha = str.match(/^(\d{1,2})[-\s/]([A-Za-z]{3})[-\s/](\d{2}|\d{4})$/);
  if (dmyAlpha) {
    const day = dmyAlpha[1].padStart(2, '0');
    const mon = MONTH_MAP[dmyAlpha[2].toLowerCase()];
    if (!mon) return null;
    let yr = dmyAlpha[3];
    if (yr.length === 2) yr = '20' + yr;
    return `${yr}-${mon}-${day}`;
  }

  // 3. ISO YYYY-MM-DD or YYYY/MM/DD
  const isoMatch = str.match(/^(\d{4})[-\/](\d{1,2})[-\/](\d{1,2})$/);
  if (isoMatch) {
    const yr = isoMatch[1];
    const mon = isoMatch[2].padStart(2, '0');
    const day = isoMatch[3].padStart(2, '0');
    return `${yr}-${mon}-${day}`;
  }

  // 4. DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
  const dmyMatch = str.match(/^(\d{1,2})[-\/. ](\d{1,2})[-\/. ](\d{2}|\d{4})$/);
  if (dmyMatch) {
    let p1 = parseInt(dmyMatch[1], 10);
    let p2 = parseInt(dmyMatch[2], 10);
    let yr = dmyMatch[3];
    if (yr.length === 2) yr = '20' + yr;

    let day = p1;
    let mon = p2;
    if (p1 <= 12 && p2 > 12) {
      day = p2;
      mon = p1;
    }

    if (mon >= 1 && mon <= 12 && day >= 1 && day <= 31) {
      return `${yr}-${String(mon).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }
  }

  return null;
}

function cleanHeader(header) {
  return header
    .toLowerCase()
    .replace(/\(.*?\)/g, '')
    .replace(/[*#_]/g, '')
    .replace(/[\r\n\t]+/g, ' ')
    .trim();
}

function getFieldValue(row, possibleKeys) {
  for (const key of Object.keys(row)) {
    const cleanKey = cleanHeader(key);
    for (const target of possibleKeys) {
      const cleanTarget = cleanHeader(target);
      if (cleanKey === cleanTarget || cleanKey.startsWith(cleanTarget) || cleanKey.includes(cleanTarget)) {
        const val = row[key];
        if (val === null || val === undefined) return '';
        if (val instanceof Date) {
          return val.toISOString().split('T')[0];
        }
        return String(val).trim();
      }
    }
  }
  return '';
}

export function parsePurchasesFileJS(fileData) {
  const wb = XLSX.read(fileData, {
    type: typeof fileData === 'string' ? 'string' : 'array',
    cellDates: true,
    raw: false
  });

  let targetSheet = wb.Sheets[wb.SheetNames[0]];
  for (const name of wb.SheetNames) {
    const candidate = wb.Sheets[name];
    const rows = XLSX.utils.sheet_to_json(candidate, { defval: '', raw: false });
    if (rows.length > 0) {
      const headerStr = Object.keys(rows[0]).join(' ').toLowerCase();
      if (
        headerStr.includes('metal') ||
        headerStr.includes('seller') ||
        headerStr.includes('jeweller') ||
        headerStr.includes('weight') ||
        headerStr.includes('invoice') ||
        headerStr.includes('rate')
      ) {
        targetSheet = candidate;
        break;
      }
    }
  }

  const rawRows = XLSX.utils.sheet_to_json(targetSheet, { defval: '', raw: false });
  const validPurchases = [];
  const errors = [];

  for (let i = 0; i < rawRows.length; i++) {
    const row = rawRows[i];
    const rowNum = i + 2;

    const rawHoldingId = getFieldValue(row, ['holding id', 'id', 'lot id']);
    const rawDate = getFieldValue(row, ['purchase date', 'invoice date', 'date']);
    const rawSeller = getFieldValue(row, ['jeweller / seller', 'jeweller', 'seller', 'vendor']);
    const rawInvoice = getFieldValue(row, ['invoice number', 'invoice #', 'invoice', 'bill no']);
    const rawMetal = getFieldValue(row, ['metal', 'bullion', 'type']);
    const rawForm = getFieldValue(row, ['form', 'shape', 'item form']);
    const rawPurity = getFieldValue(row, ['purity', 'fineness', 'karat']);
    const rawWeight = getFieldValue(row, ['weight in grams', 'weight (g)', 'weight', 'grams']);
    const rawRate = getFieldValue(row, ['purchase rate', 'rate (₹/g)', 'rate per gram', 'rate']);
    const rawTaxes = getFieldValue(row, ['taxes paid', 'tax', 'gst', 'taxes']);
    const rawOther = getFieldValue(row, ['other charges', 'charges', 'making charges']);

    if (!rawDate) {
      errors.push({ row: rowNum, message: 'Missing date' });
      continue;
    }
    const isoDate = parseAnyDate(rawDate);
    if (!isoDate) {
      errors.push({ row: rowNum, message: `Invalid date: ${rawDate}` });
      continue;
    }
    if (!rawSeller) {
      errors.push({ row: rowNum, message: 'Missing seller' });
      continue;
    }
    if (!rawInvoice) {
      errors.push({ row: rowNum, message: 'Missing invoice' });
      continue;
    }

    const metalUpper = (rawMetal || '').toUpperCase().trim();
    if (metalUpper !== 'GOLD' && metalUpper !== 'SILVER') {
      errors.push({ row: rowNum, message: `Invalid metal: ${rawMetal}` });
      continue;
    }

    const weightNum = parseFloat((rawWeight || '').toString().replace(/,/g, ''));
    const rateNum = parseFloat((rawRate || '').toString().replace(/,/g, ''));
    if (isNaN(weightNum) || weightNum <= 0 || isNaN(rateNum) || rateNum <= 0) {
      errors.push({ row: rowNum, message: `Invalid weight or rate` });
      continue;
    }

    const taxesNum = parseFloat((rawTaxes || '0').toString().replace(/,/g, '')) || 0;
    const otherNum = parseFloat((rawOther || '0').toString().replace(/,/g, '')) || 0;
    const bullionValue = Math.round(weightNum * rateNum * 100) / 100;
    const investedAmount = Math.round((bullionValue + taxesNum + otherNum) * 100) / 100;

    validPurchases.push({
      id: rawHoldingId || `HLD-${isoDate}-${validPurchases.length + 1}`,
      purchaseDate: isoDate,
      seller: rawSeller,
      invoiceNumber: rawInvoice,
      metal: metalUpper,
      weightGrams: weightNum,
      purchaseRate: rateNum,
      taxesPaid: taxesNum,
      investedAmount
    });
  }

  return { validPurchases, errors };
}

// Run test on diverse dates
const testRows = [
  ['HLD-D01', '16-Apr-2024', 'Tanishq', 'INV-001', 'Gold', 'Coin', 999, 10, 7200, 216, 0],
  ['HLD-D02', '16/04/2024', 'Malabar', 'INV-002', 'Gold', 'Bar', 999, 20, 7250, 435, 0],
  ['HLD-D03', '16-04-2024', 'Kalyan', 'INV-003', 'Silver', 'Bar', 999, 1000, 85, 255, 0],
  ['HLD-D04', '2024-04-16', 'MMTC', 'INV-004', 'Gold', 'Vedhani', 995, 5, 7150, 107, 0],
  ['HLD-D05', 45400, 'Zaveri', 'INV-005', 'Silver', 'Coin', 999, 100, 85, 25, 0]
];
const headers = [
  'Holding ID (Optional)',
  'Purchase Date (DD-MMM-YYYY or YYYY-MM-DD)*',
  'Jeweller / Seller*',
  'Invoice Number (Text, leading zeros preserved)*',
  'Metal (Gold / Silver)*',
  'Form (Vedhani / Coin / Bar)*',
  'Purity (999, 995, 916, 750, etc.)*',
  'Weight in Grams*',
  'Purchase Rate (₹/Gram)*',
  'Taxes Paid (₹ Rupee Amount)*',
  'Other Charges (₹)*'
];

const wb = XLSX.utils.book_new();
const ws = XLSX.utils.aoa_to_sheet([headers, ...testRows]);
XLSX.utils.book_append_sheet(wb, ws, 'Purchases');
const buf = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });

const res = parsePurchasesFileJS(buf);
console.log(`Parsed ${res.validPurchases.length} of ${testRows.length} rows.`);
console.log(`Errors: ${res.errors.length}`);
for (const p of res.validPurchases) {
  console.log(`✅ ${p.id}: Date=${p.purchaseDate}, Seller=${p.seller}, ${p.metal} ${p.weightGrams}g, Cost=₹${p.investedAmount}`);
}
if (res.validPurchases.length === 5 && res.errors.length === 0) {
  console.log('🎉 EXCEL TEMPLATE PARSER VERIFIED 100% WORKING!');
} else {
  process.exit(1);
}
