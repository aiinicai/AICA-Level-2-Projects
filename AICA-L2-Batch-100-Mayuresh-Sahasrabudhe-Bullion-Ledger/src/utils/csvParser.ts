import { RateRecord, RateSourceType } from '../types';

const MONTH_MAP: Record<string, string> = {
  jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
  jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
};

/**
 * Robust CSV Line Tokenizer that handles quotes, escaped quotes, and newlines inside quotes.
 */
export function parseCSVTokens(csvText: string): string[][] {
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentField = '';
  let insideQuotes = false;

  // Strip BOM if present
  let text = csvText;
  if (text.charCodeAt(0) === 0xFEFF) {
    text = text.slice(1);
  }

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (char === '"') {
      if (insideQuotes && nextChar === '"') {
        // Escaped double quote
        currentField += '"';
        i++;
      } else {
        // Toggle quotes
        insideQuotes = !insideQuotes;
      }
    } else if (char === ',' && !insideQuotes) {
      currentRow.push(currentField);
      currentField = '';
    } else if ((char === '\r' || char === '\n') && !insideQuotes) {
      if (char === '\r' && nextChar === '\n') {
        i++; // skip \n of \r\n
      }
      currentRow.push(currentField);
      currentField = '';
      // Only push non-empty rows
      if (currentRow.some(field => field.trim().length > 0)) {
        rows.push(currentRow);
      }
      currentRow = [];
    } else {
      currentField += char;
    }
  }

  if (currentField.length > 0 || currentRow.length > 0) {
    currentRow.push(currentField);
    if (currentRow.some(field => field.trim().length > 0)) {
      rows.push(currentRow);
    }
  }

  return rows;
}

/**
 * Parse date string from CSV (supports 01-Jan-19, 01-Jan-2019, 2019-01-01)
 */
export function parseCSVDate(rawDate: string): string | null {
  const trimmed = rawDate.trim();
  if (!trimmed) return null;

  // Format 1: 01-Jan-19 or 01-Jan-2019
  const dmyMatch = trimmed.match(/^(\d{1,2})-([A-Za-z]{3})-(\d{2}|\d{4})$/);
  if (dmyMatch) {
    const day = dmyMatch[1].padStart(2, '0');
    const monStr = dmyMatch[2].toLowerCase();
    const rawYear = dmyMatch[3];
    const month = MONTH_MAP[monStr];
    if (!month) return null;

    let year = rawYear;
    if (year.length === 2) {
      // 2000-2099 rule
      year = '20' + year;
    }
    return `${year}-${month}-${day}`;
  }

  // Format 2: YYYY-MM-DD
  const isoMatch = trimmed.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (isoMatch) {
    return trimmed;
  }

  // Format 3: DD/MM/YYYY
  const slashMatch = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (slashMatch) {
    const day = slashMatch[1].padStart(2, '0');
    const month = slashMatch[2].padStart(2, '0');
    const year = slashMatch[3];
    return `${year}-${month}-${day}`;
  }

  return null;
}

export interface ParseResult {
  sourceRowsCount: number;
  goldRowsCount: number;
  silverRowsCount: number;
  normalizedRecords: RateRecord[];
  skippedRows: { row: number; reason: string }[];
  dateRange: { start: string; end: string } | null;
  hasSilverGap20200803: boolean;
  nseMaxDate?: string;
  ibjaMinDate?: string;
}

/**
 * Parse the Price History CSV according to full domain requirements.
 */
export function parsePriceHistoryCSV(csvText: string, provenanceLabel = 'Price History.csv'): ParseResult {
  const rows = parseCSVTokens(csvText);
  if (rows.length === 0) {
    return {
      sourceRowsCount: 0,
      goldRowsCount: 0,
      silverRowsCount: 0,
      normalizedRecords: [],
      skippedRows: [],
      dateRange: null,
      hasSilverGap20200803: false
    };
  }

  // Header row - sanitize whitespace and embedded newlines
  const rawHeaders = rows[0];
  const cleanHeaders = rawHeaders.map(h => h.replace(/[\r\n]+/g, ' ').trim());

  // Locate column indices
  let bullionIdx = cleanHeaders.findIndex(h => /bullion/i.test(h));
  let unitIdx = cleanHeaders.findIndex(h => /quotation\s*value/i.test(h));
  let dateIdx = cleanHeaders.findIndex(h => /updated\s*date/i.test(h));
  let k995Idx = cleanHeaders.findIndex(h => /995k?/i.test(h));
  let k999Idx = cleanHeaders.findIndex(h => /999k?/i.test(h));
  let sourceIdx = cleanHeaders.findIndex(h => /source/i.test(h));

  // Fallbacks if header naming slightly differs
  if (bullionIdx === -1) bullionIdx = 0;
  if (unitIdx === -1) unitIdx = 1;
  if (dateIdx === -1) dateIdx = 2;
  if (k995Idx === -1) k995Idx = 3;
  if (k999Idx === -1) k999Idx = 4;
  if (sourceIdx === -1) sourceIdx = 5;

  const dataRows = rows.slice(1);
  const normalizedRecords: RateRecord[] = [];
  const skippedRows: { row: number; reason: string }[] = [];
  let goldRowsCount = 0;
  let silverRowsCount = 0;

  const seenKeys = new Set<string>();
  const datesFound: string[] = [];
  const nseDates: string[] = [];
  const ibjaDates: string[] = [];

  for (let idx = 0; idx < dataRows.length; idx++) {
    const row = dataRows[idx];
    const rowNum = idx + 2; // 1-based, including header

    if (row.length < 3) {
      skippedRows.push({ row: rowNum, reason: 'Insufficient columns' });
      continue;
    }

    const rawMetal = (row[bullionIdx] || '').trim().toUpperCase();
    const rawUnit = (row[unitIdx] || '').trim();
    const rawDate = (row[dateIdx] || '').trim();
    const raw995 = (row[k995Idx] || '').replace(/,/g, '').trim();
    const raw999 = (row[k999Idx] || '').replace(/,/g, '').trim();
    const rawSource = (row[sourceIdx] || '').trim();

    if (!rawMetal || (rawMetal !== 'GOLD' && rawMetal !== 'SILVER')) {
      skippedRows.push({ row: rowNum, reason: `Unknown metal: "${rawMetal}"` });
      continue;
    }

    const isoDate = parseCSVDate(rawDate);
    if (!isoDate) {
      skippedRows.push({ row: rowNum, reason: `Invalid date format: "${rawDate}"` });
      continue;
    }

    datesFound.push(isoDate);

    if (rawMetal === 'GOLD') goldRowsCount++;
    if (rawMetal === 'SILVER') silverRowsCount++;

    // Quotation unit conversion:
    // Gold "10 Grams": divide quotation by 10 to obtain ₹/gram
    // Silver "1 Kg": divide quotation by 1,000 to obtain ₹/gram
    let divisor = 1.0;
    if (rawMetal === 'GOLD' && /10\s*gram/i.test(rawUnit)) {
      divisor = 10.0;
    } else if (rawMetal === 'SILVER' && /1\s*kg/i.test(rawUnit)) {
      divisor = 1000.0;
    }

    let sourceType: RateSourceType = 'NSE';
    if (/ibja/i.test(rawSource)) {
      sourceType = 'IBJA';
      ibjaDates.push(isoDate);
    } else if (/nse/i.test(rawSource)) {
      sourceType = 'NSE';
      nseDates.push(isoDate);
    } else {
      sourceType = 'SUPPLEMENTAL';
    }

    // Unpivot 995
    if (raw995 && raw995 !== '0' && !isNaN(Number(raw995))) {
      const origPrice = parseFloat(raw995);
      const pricePerGram = Math.round((origPrice / divisor) * 10000) / 10000;
      const key = `${isoDate}_${rawMetal}_995`;

      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        normalizedRecords.push({
          id: key,
          date: isoDate,
          metal: rawMetal as 'GOLD' | 'SILVER',
          purity: 995,
          pricePerGram,
          source: rawSource,
          sourceType,
          originalUnit: rawUnit,
          originalPrice: origPrice,
          session: 'UNSPECIFIED',
          gstIncluded: false,
          provenance: provenanceLabel,
          importedAt: new Date().toISOString()
        });
      }
    }

    // Unpivot 999
    if (raw999 && raw999 !== '0' && !isNaN(Number(raw999))) {
      const origPrice = parseFloat(raw999);
      const pricePerGram = Math.round((origPrice / divisor) * 10000) / 10000;
      const key = `${isoDate}_${rawMetal}_999`;

      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        normalizedRecords.push({
          id: key,
          date: isoDate,
          metal: rawMetal as 'GOLD' | 'SILVER',
          purity: 999,
          pricePerGram,
          source: rawSource,
          sourceType,
          originalUnit: rawUnit,
          originalPrice: origPrice,
          session: 'UNSPECIFIED',
          gstIncluded: false,
          provenance: provenanceLabel,
          importedAt: new Date().toISOString()
        });
      }
    }
  }

  // Check known gap: Silver missing on 2020-08-03
  const hasSilverGap20200803 = normalizedRecords.some(r => r.date === '2020-08-03' && r.metal === 'GOLD') &&
    !normalizedRecords.some(r => r.date === '2020-08-03' && r.metal === 'SILVER');

  datesFound.sort();
  const dateRange = datesFound.length > 0 ? { start: datesFound[0], end: datesFound[datesFound.length - 1] } : null;

  nseDates.sort();
  ibjaDates.sort();

  return {
    sourceRowsCount: dataRows.length,
    goldRowsCount,
    silverRowsCount,
    normalizedRecords,
    skippedRows,
    dateRange,
    hasSilverGap20200803,
    nseMaxDate: nseDates.length > 0 ? nseDates[nseDates.length - 1] : undefined,
    ibjaMinDate: ibjaDates.length > 0 ? ibjaDates[0] : undefined
  };
}
