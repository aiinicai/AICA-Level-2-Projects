import * as XLSX from 'xlsx';
import { Purchase, MetalType, FormType } from '../types/index';

export interface PurchaseValidationResult {
  validPurchases: Purchase[];
  errors: { row: number; field: string; message: string; rawData: Record<string, string> }[];
  warnings: { row: number; field: string; message: string }[];
  batchId: string;
}

/**
 * Universal Date Parser for Excel, CSV, ISO, Indian, and alphanumeric formats.
 */
export function parseAnyDate(raw: any): string | null {
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

  const MONTH_MAP: Record<string, string> = {
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
    jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
  };

  // 2. DD-MMM-YY or DD-MMM-YYYY or DD MMM YYYY (e.g. 16-Apr-2024 or 16 Apr 2024)
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

/**
 * Generate a clean Excel (.xlsx) template for purchase entries.
 */
export function generatePurchaseTemplateXLSX(): Uint8Array {
  const wb = XLSX.utils.book_new();

  // Template columns
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
    'Other Charges (₹)*',
    'Notes / Remarks'
  ];

  const sampleRows = [
    [
      'HLD-20240416-001',
      '16-Apr-2024',
      'Tanishq',
      '004921',
      'Gold',
      'Coin',
      999,
      10.0,
      7224.90,
      2167.47,
      350.00,
      'Akshaya Tritiya purchase'
    ],
    [
      'HLD-20240725-002',
      '25-Jul-2024',
      'MMTC-PAMP',
      'INV-00812',
      'Silver',
      'Bar',
      999,
      500.0,
      81.48,
      1222.20,
      150.00,
      '500g fine silver bar'
    ]
  ];

  const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleRows]);

  ws['!cols'] = [
    { wch: 22 }, // Holding ID
    { wch: 30 }, // Date
    { wch: 24 }, // Jeweller
    { wch: 25 }, // Invoice #
    { wch: 15 }, // Metal
    { wch: 15 }, // Form
    { wch: 14 }, // Purity
    { wch: 18 }, // Weight
    { wch: 22 }, // Purchase Rate
    { wch: 22 }, // Taxes Paid
    { wch: 18 }, // Other Charges
    { wch: 30 }  // Notes
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Purchases Template');

  // Instructions sheet
  const instructions = [
    ['Bullion Ledger - Purchase Import Guide'],
    [''],
    ['Field', 'Required', 'Description', 'Allowed Values / Examples'],
    ['Holding ID', 'No', 'Unique ID. If blank, auto-generated.', 'HLD-20240416-001'],
    ['Purchase Date', 'Yes', 'Actual invoice purchase date.', '16-Apr-2024 or 2024-04-16'],
    ['Jeweller / Seller', 'Yes', 'Name of jeweller or refinery.', 'Tanishq, MMTC-PAMP, BRPL'],
    ['Invoice Number', 'Yes', 'Text with leading zeros preserved.', '004921, INV-1002'],
    ['Metal', 'Yes', 'Bullion metal.', 'Gold, Silver'],
    ['Form', 'Yes', 'Physical holding form.', 'Vedhani, Coin, Bar'],
    ['Purity', 'Yes', 'Fineness number (not karats).', '999, 995, 916, 750, etc.'],
    ['Weight in Grams', 'Yes', 'Positive decimal weight in grams.', '10.0, 50.0, 1000.0'],
    ['Purchase Rate', 'Yes', 'Rupees per gram before tax.', '7224.90, 81.48'],
    ['Taxes Paid', 'Yes', 'Total tax / GST paid on invoice in ₹.', '2167.47'],
    ['Other Charges', 'No', 'Making charges, hallmarking, delivery.', '0, 350.00'],
    ['Notes', 'No', 'Freeform remarks / serial numbers.', 'Any text']
  ];
  const wsGuide = XLSX.utils.aoa_to_sheet(instructions);
  wsGuide['!cols'] = [{ wch: 20 }, { wch: 10 }, { wch: 35 }, { wch: 30 }];
  XLSX.utils.book_append_sheet(wb, wsGuide, 'Guide & Rules');

  return XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
}

function cleanHeader(header: string): string {
  return header
    .toLowerCase()
    .replace(/\(.*?\)/g, '') // remove parenthesized descriptions
    .replace(/[*#_]/g, '')
    .replace(/[\r\n\t]+/g, ' ')
    .trim();
}

function getFieldValue(row: Record<string, any>, possibleKeys: string[]): string {
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

/**
 * Parse and validate purchases from XLSX or CSV data buffer.
 */
export function parsePurchasesFile(
  fileData: ArrayBuffer | string,
  fileName: string,
  existingPurchases: Purchase[] = []
): PurchaseValidationResult {
  const batchId = `BATCH-${Date.now()}`;
  let rawRows: Record<string, any>[] = [];

  try {
    const wb = XLSX.read(fileData, {
      type: typeof fileData === 'string' ? 'string' : 'array',
      cellDates: true,
      raw: false
    });

    // Detect which sheet contains the purchases
    let targetSheet = wb.Sheets[wb.SheetNames[0]];
    for (const name of wb.SheetNames) {
      const candidate = wb.Sheets[name];
      const rows = XLSX.utils.sheet_to_json<Record<string, any>>(candidate, { defval: '', raw: false });
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

    rawRows = XLSX.utils.sheet_to_json(targetSheet, { defval: '', raw: false });
  } catch (err: any) {
    return {
      validPurchases: [],
      errors: [{ row: 0, field: 'file', message: `Failed to parse file: ${err.message}`, rawData: {} }],
      warnings: [],
      batchId
    };
  }

  const validPurchases: Purchase[] = [];
  const errors: PurchaseValidationResult['errors'] = [];
  const warnings: PurchaseValidationResult['warnings'] = [];

  for (let i = 0; i < rawRows.length; i++) {
    const row = rawRows[i];
    const rowNum = i + 2; // 1-based, assuming row 1 is header

    // Map columns flexibly
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
    const rawNotes = getFieldValue(row, ['notes / remarks', 'notes', 'remarks']);

    // Check required fields
    if (!rawDate) {
      errors.push({ row: rowNum, field: 'purchaseDate', message: 'Purchase Date is required', rawData: row });
      continue;
    }
    const isoDate = parseAnyDate(rawDate);
    if (!isoDate) {
      errors.push({ row: rowNum, field: 'purchaseDate', message: `Invalid date format: "${rawDate}". Use DD-MMM-YYYY or YYYY-MM-DD.`, rawData: row });
      continue;
    }

    if (!rawSeller) {
      errors.push({ row: rowNum, field: 'seller', message: 'Jeweller / Seller is required', rawData: row });
      continue;
    }

    if (!rawInvoice) {
      errors.push({ row: rowNum, field: 'invoiceNumber', message: 'Invoice Number is required', rawData: row });
      continue;
    }

    // Metal
    const metalUpper = (rawMetal || '').toUpperCase().trim();
    if (metalUpper !== 'GOLD' && metalUpper !== 'SILVER') {
      errors.push({ row: rowNum, field: 'metal', message: `Metal must be Gold or Silver (got: "${rawMetal}")`, rawData: row });
      continue;
    }
    const metal: MetalType = metalUpper as MetalType;

    // Form
    const formUpper = (rawForm || '').toUpperCase().trim();
    let form: FormType = 'COIN';
    if (formUpper === 'VEDHANI' || formUpper.includes('VED')) form = 'VEDHANI';
    else if (formUpper === 'BAR' || formUpper.includes('BAR') || formUpper.includes('INGOT')) form = 'BAR';
    else if (formUpper === 'COIN' || formUpper.includes('COIN') || formUpper.includes('ROUND')) form = 'COIN';
    else {
      warnings.push({ row: rowNum, field: 'form', message: `Unrecognized form "${rawForm}", defaulted to Coin.` });
    }

    // Purity
    const purityNum = parseInt((rawPurity || '').toString().replace(/[^\d]/g, ''), 10);
    if (isNaN(purityNum) || purityNum <= 0) {
      errors.push({ row: rowNum, field: 'purity', message: `Invalid purity: "${rawPurity}"`, rawData: row });
      continue;
    }

    // Weight
    const weightNum = parseFloat((rawWeight || '').toString().replace(/,/g, ''));
    if (isNaN(weightNum) || weightNum <= 0) {
      errors.push({ row: rowNum, field: 'weightGrams', message: `Weight must be greater than 0 (got: "${rawWeight}")`, rawData: row });
      continue;
    }

    // Rate
    const rateNum = parseFloat((rawRate || '').toString().replace(/,/g, ''));
    if (isNaN(rateNum) || rateNum <= 0) {
      errors.push({ row: rowNum, field: 'purchaseRate', message: `Purchase Rate must be greater than 0 (got: "${rawRate}")`, rawData: row });
      continue;
    }

    // Taxes
    let taxesNum = parseFloat((rawTaxes || '0').toString().replace(/,/g, ''));
    if (isNaN(taxesNum) || taxesNum < 0) {
      taxesNum = 0;
    }

    // Other Charges
    let otherNum = parseFloat((rawOther || '0').toString().replace(/,/g, ''));
    if (isNaN(otherNum) || otherNum < 0) {
      otherNum = 0;
    }

    const bullionValue = Math.round(weightNum * rateNum * 100) / 100;
    const investedAmount = Math.round((bullionValue + taxesNum + otherNum) * 100) / 100;

    // Holding ID
    const holdingId = rawHoldingId && rawHoldingId.trim().length > 0
      ? rawHoldingId.trim()
      : `HLD-${isoDate.replace(/-/g, '')}-${String(validPurchases.length + 1).padStart(3, '0')}`;

    // Duplicate detection check
    const isDuplicate = existingPurchases.some(
      p => !p.deleted &&
        p.purchaseDate === isoDate &&
        p.seller.toLowerCase() === rawSeller.toLowerCase() &&
        p.invoiceNumber === rawInvoice &&
        p.metal === metal &&
        p.form === form &&
        Math.abs(p.weightGrams - weightNum) < 1e-4
    );

    if (isDuplicate) {
      warnings.push({
        row: rowNum,
        field: 'duplicate',
        message: `Possible duplicate purchase detected for invoice ${rawInvoice} on ${isoDate}.`
      });
    }

    validPurchases.push({
      id: holdingId,
      purchaseDate: isoDate,
      seller: rawSeller,
      invoiceNumber: String(rawInvoice), // Preserves leading zeros as string
      metal,
      form,
      purity: purityNum,
      weightGrams: weightNum,
      purchaseRate: rateNum,
      taxesPaid: taxesNum,
      otherCharges: otherNum,
      notes: rawNotes ? String(rawNotes).trim() : undefined,
      bullionValue,
      investedAmount,
      batchId,
      deleted: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    });
  }

  return { validPurchases, errors, warnings, batchId };
}

/**
 * Export purchases to Excel (.xlsx) buffer.
 */
export function exportPurchasesToXLSX(purchases: Purchase[]): Uint8Array {
  const wb = XLSX.utils.book_new();

  const headers = [
    'Holding ID',
    'Purchase Date',
    'Jeweller / Seller',
    'Invoice Number',
    'Metal',
    'Form',
    'Purity',
    'Weight (g)',
    'Purchase Rate (₹/g)',
    'Bullion Value (₹)',
    'Taxes Paid (₹)',
    'Other Charges (₹)',
    'Total Invested Cost (₹)',
    'Notes'
  ];

  const rows = purchases.map(p => [
    p.id,
    p.purchaseDate,
    p.seller,
    p.invoiceNumber,
    p.metal,
    p.form,
    p.purity,
    p.weightGrams,
    p.purchaseRate,
    p.bullionValue,
    p.taxesPaid,
    p.otherCharges,
    p.investedAmount,
    p.notes || ''
  ]);

  const ws = XLSX.utils.aoa_to_sheet([headers, ...rows]);
  ws['!cols'] = [
    { wch: 22 }, { wch: 15 }, { wch: 24 }, { wch: 18 },
    { wch: 10 }, { wch: 12 }, { wch: 10 }, { wch: 14 },
    { wch: 18 }, { wch: 18 }, { wch: 15 }, { wch: 16 },
    { wch: 22 }, { wch: 30 }
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Purchases');
  return XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
}
