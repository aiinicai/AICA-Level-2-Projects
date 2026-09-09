import * as XLSX from 'xlsx';
import { LedgerItem, EntityDetails, EntityType } from '../types/accounting';

export interface ParsedTrialBalanceResult {
  sheetNames: string[];
  selectedSheet: string;
  headers: string[];
  rawRows: any[];
  mappedColumns: {
    ledgerNameCol: string;
    groupCol: string;
    debitCol: string;
    creditCol: string;
    netBalanceCol?: string;
    drCrIndicatorCol?: string;
    importSourceDescription?: string;
  };
  ledgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[];
  totalDebit: number;
  totalCredit: number;
  difference: number;
  detectedEntity?: Partial<EntityDetails>;
  ignoredMetadataRowsCount: number;
  isMultiColumnTrialBalance?: boolean;
}

export function parseNumber(val: any): number {
  if (val === null || val === undefined || val === '') return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : Math.round(val * 100) / 100;
  
  let str = String(val).trim().replace(/,/g, '').replace(/₹/g, '').replace(/\$/g, '').replace(/\s+/g, '');
  
  // Handle empty or dash
  if (str === '' || str === '-' || str === '--' || str === 'nil' || str === 'null') return 0;

  // Handle parenthesis for negative like (1500) or (1,500.00)
  if (str.startsWith('(') && str.endsWith(')')) {
    const num = parseFloat(str.slice(1, -1));
    return isNaN(num) ? 0 : -num;
  }

  // Handle Dr / Cr prefixes like Dr. 15000 or Cr 15000
  if (/^dr\.?/i.test(str)) {
    const num = parseFloat(str.replace(/^dr\.?/i, '').trim());
    return isNaN(num) ? 0 : num;
  }
  if (/^cr\.?/i.test(str)) {
    const num = parseFloat(str.replace(/^cr\.?/i, '').trim());
    return isNaN(num) ? 0 : -num;
  }

  // Handle Dr / Cr suffixes like 15000 Dr or 15000.00 Cr or 15000 (Dr) or 15000 Dr.
  if (/dr\.?$/i.test(str) || /\(dr\)$/i.test(str)) {
    const cleanStr = str.replace(/dr\.?$/i, '').replace(/\(dr\)$/i, '').trim();
    const num = parseFloat(cleanStr);
    return isNaN(num) ? 0 : num;
  }
  if (/cr\.?$/i.test(str) || /\(cr\)$/i.test(str)) {
    const cleanStr = str.replace(/cr\.?$/i, '').replace(/\(cr\)$/i, '').trim();
    const num = parseFloat(cleanStr);
    return isNaN(num) ? 0 : -num;
  }

  const parsed = parseFloat(str);
  return isNaN(parsed) ? 0 : Math.round(parsed * 100) / 100;
}

/**
 * Extracts numeric amount and explicit Dr/Cr nature from a cell and optional indicator column.
 */
export function extractAmountWithDrCr(
  val: any, 
  indicatorVal?: any
): { amount: number; isDebit: boolean; isCredit: boolean } {
  if (val === null || val === undefined || val === '') {
    return { amount: 0, isDebit: false, isCredit: false };
  }

  const rawStr = String(val).trim();
  const lowerStr = rawStr.toLowerCase();
  const indStr = String(indicatorVal || '').trim().toLowerCase();

  const numVal = parseNumber(val);
  const absVal = Math.abs(numVal);

  if (absVal === 0) {
    return { amount: 0, isDebit: false, isCredit: false };
  }

  // 1. Check explicit indicator argument (e.g. from a Dr/Cr or Type column)
  if (indStr === 'cr' || indStr === 'c' || indStr.includes('cr') || indStr === 'credit') {
    return { amount: absVal, isDebit: false, isCredit: true };
  }
  if (indStr === 'dr' || indStr === 'd' || indStr.includes('dr') || indStr === 'debit') {
    return { amount: absVal, isDebit: true, isCredit: false };
  }

  // 2. Check within the value string itself
  if (lowerStr.includes('cr') || lowerStr.endsWith('cr') || lowerStr.startsWith('cr') || lowerStr.includes('(cr)') || (lowerStr.startsWith('(') && lowerStr.endsWith(')'))) {
    return { amount: absVal, isDebit: false, isCredit: true };
  }
  if (lowerStr.includes('dr') || lowerStr.endsWith('dr') || lowerStr.startsWith('dr') || lowerStr.includes('(dr)')) {
    return { amount: absVal, isDebit: true, isCredit: false };
  }

  // 3. Check if number is negative (commonly denotes Credit in single-column TB exports)
  if (numVal < 0) {
    return { amount: absVal, isDebit: false, isCredit: true };
  }

  // 4. Default: positive number without Cr indicator is treated as Debit
  return { amount: absVal, isDebit: true, isCredit: false };
}

/**
 * Checks whether a given text is metadata / general particulars / headers / totals
 * rather than an actual accounting ledger.
 */
export function isNonLedgerText(text: string): boolean {
  if (!text) return true;
  const t = text.trim().toLowerCase();
  
  // Empty or pure punctuation/symbols
  if (t.length === 0 || /^[-_=*#.()/\\]+$/.test(t)) return true;

  // Common metadata, totals, and structural section headers
  const blacklist = [
    'general particulars',
    'general particular',
    'entity details',
    'company details',
    'trial balance',
    'trial balance as at',
    'trial balance as on',
    'trial balance for the period',
    'trial balance for the year',
    'period from',
    'for the year ended',
    'financial year',
    'assessment year',
    'f.y.',
    'a.y.',
    'pan no',
    'pan number',
    'gstin',
    'gst no',
    'name of the assessee',
    'name of assessee',
    'name of company',
    'name of the firm',
    'name of entity',
    'client name',
    'proprietor name',
    'partner name',
    'status: ',
    'status : ',
    'constitution: ',
    'address: ',
    'address :',
    'regd office',
    'registered office',
    'head office',
    'branch office',
    'place:',
    'date:',
    'chartered accountants',
    'for and on behalf',
    'for & on behalf',
    'partner/proprietor',
    'authorised signatory',
    'authorized signatory',
    'membership no',
    'firm reg no',
    'frn:',
    'udin:',
    'total',
    'grand total',
    'gross total',
    'difference',
    'diff in tb',
    'difference in trial balance',
    'diff. in trial balance',
    'sub total',
    'subtotal',
    'page no',
    'page 1 of',
    'page 2 of',
    'report generated',
    'tally prime',
    'tally erp',
    'busy win',
    'particulars',
    'ledger name',
    'name of account',
    'account head',
    'head of account',
    'dr amount',
    'cr amount',
    'debit amount',
    'credit amount',
    'debit (rs)',
    'credit (rs)',
    'debit (in rs)',
    'credit (in rs)',
    'closing balance',
    'closing balances',
    'opening balance',
    'opening balances',
    'transactions',
    'period movement',
    'total opening',
    'total closing',
    'current balance',
  ];

  // Direct match or starting match
  for (const item of blacklist) {
    if (t === item || t.startsWith(item + ':') || t.startsWith(item + ' -') || t.startsWith(item + ' :')) {
      return true;
    }
  }

  // Exact header line patterns
  if (t === 'particulars' || t === 'ledger' || t === 'account' || t === 'group' || t === 'debit' || t === 'credit') {
    return true;
  }

  return false;
}

export async function parseExcelTrialBalanceFile(file: File): Promise<ParsedTrialBalanceResult> {
  const data = await file.arrayBuffer();
  const workbook = XLSX.read(data, { type: 'array' });
  const sheetNames = workbook.SheetNames;
  if (sheetNames.length === 0) {
    throw new Error('The uploaded workbook contains no sheets.');
  }

  const selectedSheet = sheetNames[0];
  const worksheet = workbook.Sheets[selectedSheet];
  if (!worksheet) {
    throw new Error('Unable to read the first worksheet.');
  }

  // Convert worksheet into a 2D matrix (array of rows)
  const matrix: any[][] = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: '' });
  if (matrix.length === 0) {
    throw new Error('The uploaded sheet is completely empty.');
  }

  // 1. Scan Top Rows for General Particulars / Metadata
  const detectedEntity: Partial<EntityDetails> = {};
  let headerRowIndex = -1;
  let bestHeaderScore = -1;

  // Keyword weights for detecting table header row
  const headerKeywords = [
    { words: ['particular', 'particulars', 'ledger', 'account', 'name of account', 'head of account', 'description'], weight: 5 },
    { words: ['debit', 'dr', 'dr amount', 'debit amount', 'dr (rs)', 'debit (in rs)', 'debit (₹)'], weight: 5 },
    { words: ['credit', 'cr', 'cr amount', 'credit amount', 'cr (rs)', 'credit (in rs)', 'credit (₹)'], weight: 5 },
    { words: ['group', 'parent', 'under', 'category', 'type', 'head'], weight: 3 },
    { words: ['opening', 'closing', 'net balance', 'balance', 'transactions', 'closing balance'], weight: 3 },
  ];

  // Scan the first 30 rows to identify the actual table header
  const maxScanRows = Math.min(matrix.length, 30);
  for (let r = 0; r < maxScanRows; r++) {
    const row = matrix[r];
    if (!Array.isArray(row) || row.length === 0) continue;

    let score = 0;
    const rowString = row.map(c => String(c || '').toLowerCase().trim());
    
    // Check keyword matches
    headerKeywords.forEach(kw => {
      if (rowString.some(cell => kw.words.some(w => cell === w || cell.includes(w)))) {
        score += kw.weight;
      }
    });

    // Check if row has multiple non-empty text strings
    const textCells = rowString.filter(c => c.length > 0);
    if (textCells.length >= 2 && score > bestHeaderScore) {
      bestHeaderScore = score;
      headerRowIndex = r;
    }

    // Extract metadata from early rows if present
    const fullRowText = row.map(c => String(c || '').trim()).filter(Boolean).join(' ');
    
    // Detect Entity Name
    if (!detectedEntity.name) {
      if (/^(m\/s|m\/s\.|shri|smt|messrs)\b/i.test(fullRowText)) {
        detectedEntity.name = fullRowText.replace(/^name\s*(of\s*assessee|of\s*the\s*assessee|of\s*entity)?\s*[:\-]\s*/i, '').trim();
      } else if (/name\s*(of\s*assessee|of\s*the\s*assessee|of\s*entity|of\s*company|of\s*firm)\s*[:\-]\s*(.+)/i.test(fullRowText)) {
        const match = fullRowText.match(/name\s*(of\s*assessee|of\s*the\s*assessee|of\s*entity|of\s*company|of\s*firm)\s*[:\-]\s*(.+)/i);
        if (match && match[2]) detectedEntity.name = match[2].trim();
      } else if (r === 0 && textCells.length === 1 && !isNonLedgerText(fullRowText) && fullRowText.length > 3) {
        detectedEntity.name = fullRowText;
      }
    }

    // Detect PAN (5 letters, 4 digits, 1 letter)
    if (!detectedEntity.pan) {
      const panMatch = fullRowText.match(/\b([A-Z]{5}[0-9]{4}[A-Z])\b/i);
      if (panMatch && panMatch[1]) {
        detectedEntity.pan = panMatch[1].toUpperCase();
      }
    }

    // Detect GSTIN (2 digits, 5 letters, 4 digits, 1 letter, 1 digit/letter, Z, 1 digit/letter)
    if (!detectedEntity.gstin) {
      const gstinMatch = fullRowText.match(/\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z])\b/i);
      if (gstinMatch && gstinMatch[1]) {
        detectedEntity.gstin = gstinMatch[1].toUpperCase();
      }
    }

    // Detect Financial Year / Date
    if (!detectedEntity.financialYear) {
      const fyMatch = fullRowText.match(/(?:f\.?y\.?|financial\s*year|period)[\s:\-]*(\d{4}[-\/]\d{2,4})/i) ||
                      fullRowText.match(/\b(20\d{2}[-\/](?:20)?\d{2})\b/);
      if (fyMatch && fyMatch[1]) {
        detectedEntity.financialYear = fyMatch[1].replace('/', '-');
      }
    }

    if (!detectedEntity.balanceSheetDate) {
      const dateMatch = fullRowText.match(/(?:as\s*on|as\s*at|ended\s*on)[\s:\-]*(\d{1,2}[-\/.]\d{1,2}[-\/.]\d{2,4})/i) ||
                        fullRowText.match(/(\d{1,2}(?:st|nd|rd|th)?\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)[,\s]+\d{4})/i);
      if (dateMatch && dateMatch[1]) {
        detectedEntity.balanceSheetDate = dateMatch[1];
      }
    }

    // Detect Entity Type
    if (!detectedEntity.entityType) {
      if (/partnership\s*firm/i.test(fullRowText)) detectedEntity.entityType = 'Partnership Firm';
      else if (/limited\s*liability\s*partnership|llp/i.test(fullRowText)) detectedEntity.entityType = 'Limited Liability Partnership (LLP)';
      else if (/proprietorship|proprietor/i.test(fullRowText)) detectedEntity.entityType = 'Proprietorship';
      else if (/huf|hindu\s*undivided\s*family/i.test(fullRowText)) detectedEntity.entityType = 'Hindu Undivided Family (HUF)';
      else if (/trust|society/i.test(fullRowText)) detectedEntity.entityType = 'Trust / Society';
      else if (/aop|boi/i.test(fullRowText)) detectedEntity.entityType = 'Association of Persons (AOP / BOI)';
    }

    // Detect Address
    if (!detectedEntity.address && /address|regd\.\s*office|plot|street|road|nagar|complex|enclave/i.test(fullRowText)) {
      detectedEntity.address = fullRowText.replace(/^address\s*[:\-]\s*/i, '').trim();
    }
  }

  // Fallback: If no good header row detected, default to row 0
  if (headerRowIndex === -1 || bestHeaderScore < 4) {
    headerRowIndex = 0;
  }

  // 2. Identify Hierarchical / Multi-Row Table Headers (e.g. Tally / Busy merged headers)
  // Check if headerRowIndex has super-headers ("Opening Balance", "Transactions", "Closing Balance")
  // and headerRowIndex + 1 has sub-headers ("Debit", "Credit", "Debit", "Credit"...)
  let dataStartRow = headerRowIndex + 1;
  let headers: string[] = [];

  const row1 = matrix[headerRowIndex] || [];
  const row2 = matrix[headerRowIndex + 1] || [];
  const row1Str = row1.map(c => String(c || '').toLowerCase().trim());
  const row2Str = row2.map(c => String(c || '').toLowerCase().trim());

  const isTwoTierHeader = (
    (row1Str.some(c => c.includes('opening') || c.includes('transaction') || c.includes('closing')) ||
     row1Str.some(c => c.includes('particular') || c.includes('ledger'))) &&
    (row2Str.filter(c => c === 'debit' || c === 'credit' || c === 'dr' || c === 'cr').length >= 2)
  );

  if (isTwoTierHeader && headerRowIndex + 1 < matrix.length) {
    dataStartRow = headerRowIndex + 2;

    // Forward-fill merged section labels in row 1
    const filledRow1: string[] = [];
    let currentSection = '';
    const maxCols = Math.max(row1.length, row2.length);

    for (let c = 0; c < maxCols; c++) {
      const cell = String(row1[c] || '').trim();
      if (cell) {
        currentSection = cell;
      }
      filledRow1[c] = currentSection;
    }

    // Combine row 1 and row 2 headers
    for (let c = 0; c < maxCols; c++) {
      const h1 = String(filledRow1[c] || '').trim();
      const h2 = String(row2[c] || '').trim();
      if (h1 && h2 && !h1.toLowerCase().includes(h2.toLowerCase())) {
        headers.push(`${h1} ${h2}`);
      } else {
        headers.push(h2 || h1 || `Col_${c + 1}`);
      }
    }
  } else {
    // Single header row
    headers = row1.map((c, i) => String(c || `Col_${i + 1}`).trim());
  }

  // 3. Detect and Map Column Indices with Strict Closing Balance Prioritization
  let nameColIdx = -1;
  let groupColIdx = -1;
  let closingDrColIdx = -1;
  let closingCrColIdx = -1;
  let closingNetColIdx = -1;
  let drCrIndicatorColIdx = -1;
  
  const allDebitCols: number[] = [];
  const allCreditCols: number[] = [];
  const nonClosingDebitCols: number[] = [];
  const nonClosingCreditCols: number[] = [];

  headers.forEach((h, idx) => {
    const norm = h.toLowerCase().trim();
    if (norm === '') return;

    // Check Ledger Name / Particulars
    if (nameColIdx === -1 && (
      norm.includes('particular') || 
      norm.includes('ledger') || 
      norm.includes('account') || 
      norm.includes('name of') || 
      norm.includes('head') ||
      norm.includes('item') ||
      norm.includes('description')
    )) {
      nameColIdx = idx;
      return;
    }

    // Check Group / Parent
    if (groupColIdx === -1 && (
      norm.includes('group') || 
      norm.includes('parent') || 
      norm.includes('under') || 
      norm.includes('category') || 
      (norm.includes('type') && !norm.includes('dr') && !norm.includes('cr'))
    )) {
      groupColIdx = idx;
      return;
    }

    // Check Dr/Cr Indicator column
    if (drCrIndicatorColIdx === -1 && (
      norm === 'dr/cr' ||
      norm === 'dr / cr' ||
      norm === 'd/c' ||
      norm === 'nature' ||
      norm === 'dr or cr' ||
      norm === 'balance type' ||
      norm === 'type (dr/cr)'
    )) {
      drCrIndicatorColIdx = idx;
      return;
    }

    // Check Closing Debit / Dr
    const isClosingDr = (
      (norm.includes('closing') || norm.includes('cl.') || norm.includes('cl ') || norm.includes('end') || norm.includes('balance c/f') || norm.includes('balance c/d')) &&
      (norm.includes('dr') || norm.includes('debit'))
    ) || (
      norm === 'closing dr' || norm === 'closing debit' || norm === 'cl dr' || norm === 'cl. dr' ||
      norm === 'closing balance (dr)' || norm === 'closing balance dr' || norm === 'closing (dr)'
    );

    // Check Closing Credit / Cr
    const isClosingCr = (
      (norm.includes('closing') || norm.includes('cl.') || norm.includes('cl ') || norm.includes('end') || norm.includes('balance c/f') || norm.includes('balance c/d')) &&
      (norm.includes('cr') || norm.includes('credit'))
    ) || (
      norm === 'closing cr' || norm === 'closing credit' || norm === 'cl cr' || norm === 'cl. cr' ||
      norm === 'closing balance (cr)' || norm === 'closing balance cr' || norm === 'closing (cr)'
    );

    if (isClosingDr) {
      closingDrColIdx = idx;
      allDebitCols.push(idx);
      return;
    }

    if (isClosingCr) {
      closingCrColIdx = idx;
      allCreditCols.push(idx);
      return;
    }

    // Check Single Closing Balance column (e.g. "Closing Balance", "Net Balance as on...")
    if (closingNetColIdx === -1 && (
      norm.includes('closing balance') ||
      norm.includes('closing bal') ||
      norm.includes('cl balance') ||
      norm.includes('cl. balance') ||
      norm.includes('closing amount') ||
      norm.includes('balance as on') ||
      norm.includes('balance as at') ||
      norm === 'closing'
    ) && !norm.includes('opening') && !norm.includes('transaction')) {
      closingNetColIdx = idx;
      return;
    }

    // Check General / Transaction Debit
    const isDebitMatch = (
      norm === 'dr' ||
      norm === 'debit' ||
      norm === 'dr amount' ||
      norm === 'debit amount' ||
      norm.includes('debit (rs)') ||
      norm.includes('dr (rs)') ||
      norm.includes('debit(in rs)') ||
      norm.includes('debit (₹)') ||
      norm.includes('debit') ||
      (norm.includes('dr') && !norm.includes('particular') && !norm.includes('address') && !norm.includes('under'))
    );

    // Check General / Transaction Credit
    const isCreditMatch = (
      norm === 'cr' ||
      norm === 'credit' ||
      norm === 'cr amount' ||
      norm === 'credit amount' ||
      norm.includes('credit (rs)') ||
      norm.includes('cr (rs)') ||
      norm.includes('credit(in rs)') ||
      norm.includes('credit (₹)') ||
      norm.includes('credit') ||
      (norm.includes('cr') && !norm.includes('particular') && !norm.includes('description') && !norm.includes('screen'))
    );

    if (isDebitMatch) {
      allDebitCols.push(idx);
      if (!norm.includes('closing')) nonClosingDebitCols.push(idx);
    } else if (isCreditMatch) {
      allCreditCols.push(idx);
      if (!norm.includes('closing')) nonClosingCreditCols.push(idx);
    }
  });

  // Verify if subsequent column after Closing Net is a Dr/Cr indicator (even if header was generic like "Type" or blank)
  if (closingNetColIdx !== -1 && drCrIndicatorColIdx === -1) {
    const candidateCol = closingNetColIdx + 1;
    if (candidateCol < headers.length) {
      // Check first 10 data rows in candidateCol
      let drCrMatches = 0;
      const testRows = Math.min(matrix.length, dataStartRow + 10);
      for (let r = dataStartRow; r < testRows; r++) {
        const val = String(matrix[r]?.[candidateCol] || '').trim().toLowerCase();
        if (val === 'dr' || val === 'cr' || val === 'd' || val === 'c') {
          drCrMatches++;
        }
      }
      if (drCrMatches >= 2) {
        drCrIndicatorColIdx = candidateCol;
      }
    }
  }

  // 4. Resolve Final Columns to Import Strictly the Closing Balance
  let debitColIdx = -1;
  let creditColIdx = -1;
  let isMultiColumnTrialBalance = false;
  let importSourceDescription = '';

  // Rule 1: Explicit Closing Dr and Closing Cr columns exist
  if (closingDrColIdx !== -1 && closingCrColIdx !== -1) {
    debitColIdx = closingDrColIdx;
    creditColIdx = closingCrColIdx;
    isMultiColumnTrialBalance = true;
    importSourceDescription = `Imported Closing Balance Dr (${headers[closingDrColIdx]}) & Cr (${headers[closingCrColIdx]}). Opening and Transaction movement columns were bypassed.`;
  }
  // Rule 2: Multi-pair columnar TB (e.g. Opening Dr/Cr, Trans Dr/Cr, Closing Dr/Cr)
  // In standard accounting TBs, the LAST pair of Debit/Credit columns is ALWAYS the Closing Balance!
  else if (allDebitCols.length >= 2 && allCreditCols.length >= 2) {
    debitColIdx = allDebitCols[allDebitCols.length - 1];
    creditColIdx = allCreditCols[allCreditCols.length - 1];
    isMultiColumnTrialBalance = true;
    importSourceDescription = `Multi-column TB detected (${allDebitCols.length} Debit & ${allCreditCols.length} Credit columns). Imported final Closing Balance columns: Dr (${headers[debitColIdx]}) & Cr (${headers[creditColIdx]}).`;
  }
  // Rule 3: Single Closing Balance column detected (with Dr/Cr indicators or signs)
  else if (closingNetColIdx !== -1) {
    isMultiColumnTrialBalance = true;
    importSourceDescription = `Imported Closing Balance column (${headers[closingNetColIdx]}) with Dr/Cr nature indicators.`;
  }
  // Rule 4: Standard TB (Single pair of Debit and Credit columns)
  else {
    debitColIdx = allDebitCols.length > 0 ? allDebitCols[0] : -1;
    creditColIdx = allCreditCols.length > 0 ? allCreditCols[0] : -1;
    importSourceDescription = `Imported standard Debit (${headers[debitColIdx] || 'Dr'}) and Credit (${headers[creditColIdx] || 'Cr'}) columns.`;
  }

  // Fallback defaults if name column was not identified
  if (nameColIdx === -1) nameColIdx = 0;

  // Fallback if still no debit/credit column found
  if (debitColIdx === -1 && closingNetColIdx === -1) {
    for (let c = 0; c < headers.length; c++) {
      if (c !== nameColIdx && c !== groupColIdx) {
        debitColIdx = c;
        break;
      }
    }
  }
  if (creditColIdx === -1 && closingNetColIdx === -1 && debitColIdx !== -1) {
    for (let c = debitColIdx + 1; c < headers.length; c++) {
      if (c !== nameColIdx && c !== groupColIdx) {
        creditColIdx = c;
        break;
      }
    }
  }

  const mappedColumns = {
    ledgerNameCol: headers[nameColIdx] || 'Particulars',
    groupCol: groupColIdx !== -1 ? headers[groupColIdx] : 'Group',
    debitCol: debitColIdx !== -1 ? headers[debitColIdx] : (closingNetColIdx !== -1 ? `${headers[closingNetColIdx]} (Dr)` : 'Debit'),
    creditCol: creditColIdx !== -1 ? headers[creditColIdx] : (closingNetColIdx !== -1 ? `${headers[closingNetColIdx]} (Cr)` : 'Credit'),
    netBalanceCol: closingNetColIdx !== -1 ? headers[closingNetColIdx] : undefined,
    drCrIndicatorCol: drCrIndicatorColIdx !== -1 ? headers[drCrIndicatorColIdx] : undefined,
    importSourceDescription,
  };

  // 5. Process Data Rows (Strictly starting from row AFTER table header)
  const ledgers: Omit<LedgerItem, 'targetType' | 'status' | 'confidence'>[] = [];
  let totalDebit = 0;
  let totalCredit = 0;
  let ignoredMetadataRowsCount = dataStartRow;

  for (let r = dataStartRow; r < matrix.length; r++) {
    const row = matrix[r];
    if (!Array.isArray(row) || row.length === 0) continue;

    const rawName = String(row[nameColIdx] || '').trim();
    if (!rawName) continue;

    // Clean ledger name (remove leading numbering like "1. ", "01. ", tabs, bullets)
    const cleanedName = rawName.replace(/^[\d\s.\-_)\]]+(?=[A-Za-z])/, '').trim();

    // Check if this row is metadata, header repetition, total, or subtotal
    if (isNonLedgerText(cleanedName)) {
      ignoredMetadataRowsCount++;
      continue;
    }

    let debit = 0;
    let credit = 0;

    // Case A: Explicit Closing Dr and Closing Cr columns, or resolved last pair of Debit/Credit columns
    if (debitColIdx !== -1 && creditColIdx !== -1) {
      debit = parseNumber(row[debitColIdx]);
      credit = parseNumber(row[creditColIdx]);

      // Normalize any negative figures
      if (debit < 0) {
        credit += Math.abs(debit);
        debit = 0;
      }
      if (credit < 0) {
        debit += Math.abs(credit);
        credit = 0;
      }
    }
    // Case B: Single Closing Balance column (with Dr/Cr indicators)
    else if (closingNetColIdx !== -1) {
      const netValRaw = row[closingNetColIdx];
      const indicatorVal = drCrIndicatorColIdx !== -1 ? row[drCrIndicatorColIdx] : undefined;
      const res = extractAmountWithDrCr(netValRaw, indicatorVal);

      if (res.isCredit) {
        credit = res.amount;
        debit = 0;
      } else {
        debit = res.amount;
        credit = 0;
      }
    }

    // If both debit and credit are 0, check if this is an empty row or section banner
    if (debit === 0 && credit === 0) {
      const hasAnyAmount = row.some((c, cIdx) => cIdx !== nameColIdx && parseNumber(c) !== 0);
      if (!hasAnyAmount) {
        ignoredMetadataRowsCount++;
        continue;
      }
    }

    const group = groupColIdx !== -1 ? String(row[groupColIdx] || '').trim() : 'General';
    const netBalance = Math.round((debit - credit) * 100) / 100;
    const natureDrCr: 'Dr' | 'Cr' = debit >= credit ? 'Dr' : 'Cr';

    totalDebit += debit;
    totalCredit += credit;

    ledgers.push({
      id: `imp-led-${r + 1}`,
      ledgerName: cleanedName,
      originalGroup: group || 'General',
      debit: Math.round(debit * 100) / 100,
      credit: Math.round(credit * 100) / 100,
      netBalance,
      natureDrCr,
    });
  }

  return {
    sheetNames,
    selectedSheet,
    headers,
    rawRows: matrix,
    mappedColumns,
    ledgers,
    totalDebit: Math.round(totalDebit * 100) / 100,
    totalCredit: Math.round(totalCredit * 100) / 100,
    difference: Math.round((totalDebit - totalCredit) * 100) / 100,
    detectedEntity,
    ignoredMetadataRowsCount,
    isMultiColumnTrialBalance,
  };
}

