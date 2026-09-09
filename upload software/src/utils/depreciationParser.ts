import * as XLSX from 'xlsx';
import ExcelJS from 'exceljs';
import { DepreciationAssetItem, EntityDetails, LedgerItem } from '../types/accounting';
import { parseNumber } from './excelParser';

export interface DepreciationColumnMapping {
  assetNameCol: string;
  categoryCol?: string;
  grossBlockCol: string;
  depreciationRateCol: string;
  accumulatedDepreciationCol: string;
  depreciationForTheYearCol: string;
  closingValueCol: string;
  previousYearClosingCol: string;
  notesCol?: string;
}

export interface ParsedDepreciationResult {
  sheetNames: string[];
  selectedSheet: string;
  headers: string[];
  rawRows: any[];
  detectedMapping: Partial<DepreciationColumnMapping>;
  parsedItems: DepreciationAssetItem[];
  totalGrossBlock: number;
  totalAccumulatedDepr: number;
  totalDeprForYear: number;
  totalClosingValue: number;
  totalPreviousYearClosing: number;
}

/**
 * Detect column matching from raw headers using CA standard synonyms
 */
export function detectDepreciationColumns(headers: string[]): Partial<DepreciationColumnMapping> {
  const mapping: Partial<DepreciationColumnMapping> = {};
  
  const clean = (str: string) => String(str || '').toLowerCase().replace(/[^a-z0-9]/g, '');

  headers.forEach(h => {
    const c = clean(h);
    
    // Asset Name
    if (!mapping.assetNameCol && (
      c.includes('assetname') || c.includes('particular') || c.includes('description') || 
      c.includes('nameofasset') || c.includes('blockofasset') || c === 'asset' || c === 'item' || c === 'assets'
    )) {
      mapping.assetNameCol = h;
    }
    // Category / Block
    else if (!mapping.categoryCol && (
      c.includes('category') || c.includes('block') || c.includes('assettype') || c.includes('class')
    )) {
      mapping.categoryCol = h;
    }
    // Gross Block
    else if (!mapping.grossBlockCol && (
      c.includes('grossblock') || c.includes('grosscost') || c.includes('originalcost') ||
      c.includes('grossvalue') || c.includes('purchasecost') || c === 'cost' || c === 'gross'
    )) {
      mapping.grossBlockCol = h;
    }
    // Rate of Depreciation
    else if (!mapping.depreciationRateCol && (
      c.includes('rateofdepr') || c.includes('depreciationrate') || c.includes('deprrate') ||
      c.includes('ratepercent') || c.includes('deprate') || c === 'rate' || c === 'rateofdepreciation' ||
      c === 'depr' || c === 'percent'
    )) {
      mapping.depreciationRateCol = h;
    }
    // Accumulated Depreciation
    else if (!mapping.accumulatedDepreciationCol && (
      c.includes('accumulateddepr') || c.includes('openingdepr') || c.includes('accdepr') ||
      c.includes('depreciationupto') || c.includes('uptoprevious') || c.includes('openingaccumulated') ||
      c.includes('uptolastyear')
    )) {
      mapping.accumulatedDepreciationCol = h;
    }
    // Depreciation of the Year
    else if (!mapping.depreciationForTheYearCol && (
      c.includes('depreciationoftheyear') || c.includes('depreciationfortheyear') || c.includes('deproftheyear') ||
      c.includes('deprfortheyear') || c.includes('currentyeardepr') || c.includes('deprforperiod') ||
      c.includes('cydepr') || c.includes('depreciationyear') || c === 'depreciation' || c === 'depr'
    )) {
      mapping.depreciationForTheYearCol = h;
    }
    // Closing Value
    else if (!mapping.closingValueCol && (
      c.includes('closingvalue') || c.includes('closingnetblock') || c.includes('closingwdv') ||
      c.includes('netblock') || c.includes('netcarrying') || c.includes('closingbalance') ||
      c.includes('netbookvalue') || c === 'closing' || c === 'wdv'
    )) {
      mapping.closingValueCol = h;
    }
    // Closing of Previous Year
    else if (!mapping.previousYearClosingCol && (
      c.includes('closingofprevious') || c.includes('previousyearclosing') || c.includes('closingprevyear') ||
      c.includes('previousyearwdv') || c.includes('openingwdv') || c.includes('pyclosing') ||
      c.includes('lastyearclosing') || c.includes('previousyearnet') || c.includes('prevyearclosing') ||
      c.includes('closinglastyear')
    )) {
      mapping.previousYearClosingCol = h;
    }
    // Notes / Remarks
    else if (!mapping.notesCol && (
      c.includes('remark') || c.includes('note') || c.includes('comment')
    )) {
      mapping.notesCol = h;
    }
  });

  return mapping;
}

/**
 * Parse an Excel file into raw sheets and extract rows
 */
export async function readDepreciationFile(file: File): Promise<{ sheetNames: string[]; workbook: XLSX.WorkBook }> {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: 'array', cellDates: true });
  return { sheetNames: workbook.SheetNames, workbook };
}

/**
 * Extract headers and items from a specific sheet with given or detected mapping
 */
export function extractDepreciationSheetData(
  workbook: XLSX.WorkBook,
  sheetName: string,
  customMapping?: Partial<DepreciationColumnMapping>
): ParsedDepreciationResult {
  const sheet = workbook.Sheets[sheetName];
  if (!sheet) {
    throw new Error(`Sheet ${sheetName} not found in workbook`);
  }

  const rawJson: any[] = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
  if (!rawJson || rawJson.length === 0) {
    return {
      sheetNames: workbook.SheetNames,
      selectedSheet: sheetName,
      headers: [],
      rawRows: [],
      detectedMapping: {},
      parsedItems: [],
      totalGrossBlock: 0,
      totalAccumulatedDepr: 0,
      totalDeprForYear: 0,
      totalClosingValue: 0,
      totalPreviousYearClosing: 0,
    };
  }

  // Find header row: look for a row with strings like 'asset', 'particular', 'gross', 'depreciation', 'rate'
  let headerRowIndex = 0;
  for (let r = 0; r < Math.min(10, rawJson.length); r++) {
    const row = rawJson[r];
    if (Array.isArray(row)) {
      const rowStr = row.map(c => String(c).toLowerCase()).join(' ');
      if (
        (rowStr.includes('asset') || rowStr.includes('particular') || rowStr.includes('description')) &&
        (rowStr.includes('gross') || rowStr.includes('cost') || rowStr.includes('depr') || rowStr.includes('rate'))
      ) {
        headerRowIndex = r;
        break;
      }
    }
  }

  const headerRow = rawJson[headerRowIndex] || [];
  const headers: string[] = headerRow.map((cell: any, idx: number) => {
    const str = String(cell || '').trim();
    return str || `Column_${idx + 1}`;
  });

  const mapping = customMapping || detectDepreciationColumns(headers);

  // Parse items from subsequent rows
  const parsedItems: DepreciationAssetItem[] = [];
  const rawRows: any[] = [];

  for (let r = headerRowIndex + 1; r < rawJson.length; r++) {
    const row = rawJson[r];
    if (!Array.isArray(row) || row.every(c => c === '' || c === null || c === undefined)) continue;

    // Convert row to object keyed by header
    const rowObj: Record<string, any> = {};
    headers.forEach((h, idx) => {
      rowObj[h] = row[idx];
    });

    rawRows.push(rowObj);

    // Extract asset name
    const assetNameVal = mapping.assetNameCol ? String(rowObj[mapping.assetNameCol] || '').trim() : '';
    if (!assetNameVal) continue;

    // Skip total or summary rows
    const lowName = assetNameVal.toLowerCase();
    if (lowName.startsWith('total') || lowName.startsWith('grand total') || lowName.includes('summary')) continue;

    const grossBlock = mapping.grossBlockCol ? parseNumber(rowObj[mapping.grossBlockCol]) : 0;
    const deprRate = mapping.depreciationRateCol ? parseNumber(rowObj[mapping.depreciationRateCol]) : 0;
    const accumDepr = mapping.accumulatedDepreciationCol ? parseNumber(rowObj[mapping.accumulatedDepreciationCol]) : 0;
    const deprForYear = mapping.depreciationForTheYearCol ? parseNumber(rowObj[mapping.depreciationForTheYearCol]) : 0;
    
    // If closing value is provided, use it. Otherwise calculate Gross Block - (Accum Depr + Depr For Year)
    let closingVal = mapping.closingValueCol ? parseNumber(rowObj[mapping.closingValueCol]) : 0;
    if (closingVal === 0 && grossBlock > 0) {
      closingVal = Math.max(0, grossBlock - (accumDepr + deprForYear));
    }

    // If previous year closing is provided, use it. Otherwise calculate Gross Block - Accum Depr
    let prevYearClosing = mapping.previousYearClosingCol ? parseNumber(rowObj[mapping.previousYearClosingCol]) : 0;
    if (prevYearClosing === 0 && grossBlock > 0) {
      prevYearClosing = Math.max(0, grossBlock - accumDepr);
    }

    const category = mapping.categoryCol ? String(rowObj[mapping.categoryCol] || '').trim() : undefined;
    const notes = mapping.notesCol ? String(rowObj[mapping.notesCol] || '').trim() : undefined;

    parsedItems.push({
      id: `depr-import-${r}-${Date.now()}`,
      assetName: assetNameVal,
      category: category || 'Fixed Assets',
      grossBlock: Math.round(grossBlock * 100) / 100,
      depreciationRate: deprRate,
      accumulatedDepreciation: Math.round(accumDepr * 100) / 100,
      depreciationForTheYear: Math.round(deprForYear * 100) / 100,
      closingValue: Math.round(closingVal * 100) / 100,
      previousYearClosing: Math.round(prevYearClosing * 100) / 100,
      notes,
    });
  }

  const totalGrossBlock = parsedItems.reduce((sum, item) => sum + item.grossBlock, 0);
  const totalAccumulatedDepr = parsedItems.reduce((sum, item) => sum + item.accumulatedDepreciation, 0);
  const totalDeprForYear = parsedItems.reduce((sum, item) => sum + item.depreciationForTheYear, 0);
  const totalClosingValue = parsedItems.reduce((sum, item) => sum + item.closingValue, 0);
  const totalPreviousYearClosing = parsedItems.reduce((sum, item) => sum + item.previousYearClosing, 0);

  return {
    sheetNames: workbook.SheetNames,
    selectedSheet: sheetName,
    headers,
    rawRows,
    detectedMapping: mapping,
    parsedItems,
    totalGrossBlock,
    totalAccumulatedDepr,
    totalDeprForYear,
    totalClosingValue,
    totalPreviousYearClosing,
  };
}

/**
 * Generate a downloadable Excel template (.xlsx) with pre-filled columns and sample non-corporate assets
 */
export async function generateDepreciationExcelTemplate(entityName: string = 'Apex Textiles'): Promise<Blob> {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Non-Corporate Financial Working Papers';
  wb.lastModifiedBy = 'Chartered Accountant';
  wb.created = new Date();

  const ws = wb.addWorksheet('Depreciation Schedule', {
    views: [{ showGridLines: true }],
  });

  // Column widths
  ws.columns = [
    { width: 6 },  // A: S.No
    { width: 38 }, // B: Asset Description
    { width: 22 }, // C: Asset Category / Block
    { width: 18 }, // D: Gross Block (₹)
    { width: 16 }, // E: Rate of Depr (%)
    { width: 22 }, // F: Accumulated Depr (₹)
    { width: 22 }, // G: Depreciation of Year (₹)
    { width: 20 }, // H: Closing Value (₹)
    { width: 22 }, // I: Closing Previous Year (₹)
    { width: 30 }, // J: Remarks / Notes
  ];

  // Header Title
  ws.mergeCells('A1:J1');
  const titleCell = ws.getCell('A1');
  titleCell.value = `${entityName.toUpperCase()} - DEPRECIATION SCHEDULE (FIXED ASSETS)`;
  titleCell.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: 'FFFFFFFF' } };
  titleCell.alignment = { horizontal: 'center', vertical: 'middle' };
  titleCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF141414' } };
  ws.getRow(1).height = 28;

  // Subtitle
  ws.mergeCells('A2:J2');
  const subCell = ws.getCell('A2');
  subCell.value = 'Depreciation Schedule under Income Tax Rules / Accounting Standard 10 (Property, Plant & Equipment)';
  subCell.font = { name: 'Segoe UI', size: 9.5, italic: true, color: { argb: 'FF5E5E5E' } };
  subCell.alignment = { horizontal: 'center', vertical: 'middle' };
  ws.getRow(2).height = 18;

  // Guidance Row
  ws.mergeCells('A3:J3');
  const guideCell = ws.getCell('A3');
  guideCell.value = 'INSTRUCTIONS: Fill your fixed assets into this template. Required columns: Gross Block, Rate of Depr, Accumulated Depr, Depr of the Year, Closing Value, and Closing of Previous Year.';
  guideCell.font = { name: 'Segoe UI', size: 8.5, color: { argb: 'FF1E3A8A' }, italic: true };
  guideCell.alignment = { horizontal: 'center', vertical: 'middle' };
  guideCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFEBF5FF' } };
  ws.getRow(3).height = 20;

  // Column Headers (Row 5)
  const headers = [
    'S.No',
    'Asset Name / Description',
    'Asset Category',
    'Gross Block (₹)',
    'Rate of Depr (%)',
    'Accumulated Depr (₹)',
    'Depreciation of the Year (₹)',
    'Closing Value (₹)',
    'Closing of Previous Year (₹)',
    'Remarks / Notes'
  ];

  const headerRow = ws.getRow(5);
  headers.forEach((h, idx) => {
    const cell = headerRow.getCell(idx + 1);
    cell.value = h;
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E293B' } };
    cell.alignment = {
      horizontal: idx >= 3 && idx <= 8 ? 'right' : idx === 0 ? 'center' : 'left',
      vertical: 'middle',
      wrapText: true
    };
    cell.border = {
      top: { style: 'medium', color: { argb: 'FF141414' } },
      bottom: { style: 'medium', color: { argb: 'FF141414' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
  });
  headerRow.height = 26;

  // Sample Asset Rows
  const sampleData = [
    {
      sno: 1,
      name: 'Commercial Shop Premises & Showroom',
      cat: 'Building / Premises',
      gross: 2400000,
      rate: 10,
      accum: 240000,
      cyDepr: 216000,
      closing: 1944000,
      prevClosing: 2160000,
      notes: 'Immovable commercial showroom property; WDV @ 10%'
    },
    {
      sno: 2,
      name: 'Plant & Packaging Machinery',
      cat: 'Plant & Machinery',
      gross: 1200000,
      rate: 15,
      accum: 250000,
      cyDepr: 142500,
      closing: 807500,
      prevClosing: 950000,
      notes: 'Textile processing and packaging machinery; WDV @ 15%'
    },
    {
      sno: 3,
      name: 'Delivery Commercial Van (Tata Ace)',
      cat: 'Vehicles',
      gross: 700000,
      rate: 15,
      accum: 150000,
      cyDepr: 82500,
      closing: 467500,
      prevClosing: 550000,
      notes: 'Commercial delivery vehicle; WDV @ 15%'
    },
    {
      sno: 4,
      name: 'Computer Systems, Servers & Printers',
      cat: 'Computers & IT',
      gross: 250000,
      rate: 40,
      accum: 105000,
      cyDepr: 58000,
      closing: 87000,
      prevClosing: 145000,
      notes: 'Office computing hardware; WDV @ 40%'
    },
    {
      sno: 5,
      name: 'Furniture, Fittings & Office Fixtures',
      cat: 'Furniture & Fixtures',
      gross: 180000,
      rate: 10,
      accum: 30000,
      cyDepr: 15000,
      closing: 135000,
      prevClosing: 150000,
      notes: 'Showroom interior racks, counters and air conditioning; WDV @ 10%'
    }
  ];

  let r = 6;
  sampleData.forEach(item => {
    const row = ws.getRow(r);
    row.getCell(1).value = item.sno;
    row.getCell(2).value = item.name;
    row.getCell(3).value = item.cat;
    row.getCell(4).value = item.gross;
    row.getCell(5).value = item.rate;
    row.getCell(6).value = item.accum;
    row.getCell(7).value = item.cyDepr;
    // Closing value formula: Gross Block - Accum Depr - Cy Depr
    row.getCell(8).value = { formula: `D${r}-F${r}-G${r}`, result: item.closing };
    // Prev year closing formula: Gross Block - Accum Depr
    row.getCell(9).value = { formula: `D${r}-F${r}`, result: item.prevClosing };
    row.getCell(10).value = item.notes;

    row.getCell(1).alignment = { horizontal: 'center' };
    row.getCell(2).font = { bold: true };
    row.getCell(5).numFmt = '0.00"%"';

    [4, 6, 7, 8, 9].forEach(c => {
      row.getCell(c).numFmt = '₹#,##0.00';
      row.getCell(c).alignment = { horizontal: 'right' };
    });

    for (let col = 1; col <= 10; col++) {
      row.getCell(col).border = {
        top: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        left: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        right: { style: 'thin', color: { argb: 'FFE2E8F0' } }
      };
      if (r % 2 === 0) {
        row.getCell(col).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
      }
    }
    r++;
  });

  // Total Summary Row
  const totalRow = ws.getRow(r);
  totalRow.getCell(2).value = 'TOTAL PROPERTY, PLANT & EQUIPMENT';
  totalRow.getCell(2).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FF141414' } };

  totalRow.getCell(4).value = { formula: `SUM(D6:D${r - 1})`, result: 4730000 };
  totalRow.getCell(6).value = { formula: `SUM(F6:F${r - 1})`, result: 775000 };
  totalRow.getCell(7).value = { formula: `SUM(G6:G${r - 1})`, result: 514000 };
  totalRow.getCell(8).value = { formula: `SUM(H6:H${r - 1})`, result: 3441000 };
  totalRow.getCell(9).value = { formula: `SUM(I6:I${r - 1})`, result: 3955000 };

  [4, 6, 7, 8, 9].forEach(c => {
    totalRow.getCell(c).numFmt = '₹#,##0.00';
    totalRow.getCell(c).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FF141414' } };
    totalRow.getCell(c).alignment = { horizontal: 'right' };
  });

  for (let col = 1; col <= 10; col++) {
    totalRow.getCell(col).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE2E8F0' } };
    totalRow.getCell(col).border = {
      top: { style: 'medium', color: { argb: 'FF141414' } },
      bottom: { style: 'double', color: { argb: 'FF141414' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
  }
  totalRow.height = 24;

  const uint8 = await wb.xlsx.writeBuffer();
  return new Blob([uint8], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

/**
 * Export current depreciation schedule into formatted Excel workbook (.xlsx)
 */
export async function exportDepreciationScheduleExcel(
  entity: EntityDetails,
  items: DepreciationAssetItem[]
): Promise<Blob> {
  const wb = new ExcelJS.Workbook();
  wb.creator = 'Non-Corporate Balance Sheet & Working Papers';
  wb.created = new Date();

  const ws = wb.addWorksheet('Depreciation Schedule', {
    views: [{ showGridLines: true }],
  });

  ws.columns = [
    { width: 6 },
    { width: 38 },
    { width: 22 },
    { width: 18 },
    { width: 16 },
    { width: 22 },
    { width: 22 },
    { width: 20 },
    { width: 22 },
    { width: 30 },
  ];

  // Header Title
  ws.mergeCells('A1:J1');
  const titleCell = ws.getCell('A1');
  titleCell.value = `${entity.name.toUpperCase()} - DEPRECIATION SCHEDULE`;
  titleCell.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: 'FFFFFFFF' } };
  titleCell.alignment = { horizontal: 'center', vertical: 'middle' };
  titleCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF141414' } };
  ws.getRow(1).height = 26;

  // Subtitle
  ws.mergeCells('A2:J2');
  const subCell = ws.getCell('A2');
  subCell.value = `Schedule of Fixed Assets & Depreciation for the Year Ended ${entity.balanceSheetDate} (F.Y. ${entity.financialYear})`;
  subCell.font = { name: 'Segoe UI', size: 10, italic: true, color: { argb: 'FF5E5E5E' } };
  subCell.alignment = { horizontal: 'center', vertical: 'middle' };
  ws.getRow(2).height = 18;

  // Headers (Row 4)
  const headers = [
    'S.No',
    'Asset Description',
    'Category / Block',
    'Gross Block (₹)',
    'Rate of Depr (%)',
    'Accumulated Depr (₹)',
    'Depreciation of the Year (₹)',
    'Closing Value (₹)',
    'Closing of Previous Year (₹)',
    'Remarks / Notes'
  ];

  const headerRow = ws.getRow(4);
  headers.forEach((h, idx) => {
    const cell = headerRow.getCell(idx + 1);
    cell.value = h;
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FFFFFFFF' } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FF1E293B' } };
    cell.alignment = {
      horizontal: idx >= 3 && idx <= 8 ? 'right' : idx === 0 ? 'center' : 'left',
      vertical: 'middle'
    };
    cell.border = {
      top: { style: 'medium', color: { argb: 'FF141414' } },
      bottom: { style: 'medium', color: { argb: 'FF141414' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
  });
  headerRow.height = 24;

  let r = 5;
  items.forEach((item, idx) => {
    const row = ws.getRow(r);
    row.getCell(1).value = idx + 1;
    row.getCell(2).value = item.assetName;
    row.getCell(3).value = item.category || 'Fixed Assets';
    row.getCell(4).value = item.grossBlock;
    row.getCell(5).value = item.depreciationRate;
    row.getCell(6).value = item.accumulatedDepreciation;
    row.getCell(7).value = item.depreciationForTheYear;
    row.getCell(8).value = item.closingValue;
    row.getCell(9).value = item.previousYearClosing;
    row.getCell(10).value = item.notes || '';

    row.getCell(1).alignment = { horizontal: 'center' };
    row.getCell(2).font = { bold: true };
    row.getCell(5).numFmt = '0.00"%"';

    [4, 6, 7, 8, 9].forEach(c => {
      row.getCell(c).numFmt = '₹#,##0.00';
      row.getCell(c).alignment = { horizontal: 'right' };
    });

    for (let col = 1; col <= 10; col++) {
      row.getCell(col).border = {
        top: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        bottom: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        left: { style: 'thin', color: { argb: 'FFE2E8F0' } },
        right: { style: 'thin', color: { argb: 'FFE2E8F0' } }
      };
      if (r % 2 === 1) {
        row.getCell(col).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF8FAFC' } };
      }
    }
    r++;
  });

  // Total Row
  const totalRow = ws.getRow(r);
  totalRow.getCell(2).value = 'TOTAL FIXED ASSETS / PPE';
  totalRow.getCell(2).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FF141414' } };

  const totGross = items.reduce((sum, i) => sum + i.grossBlock, 0);
  const totAccum = items.reduce((sum, i) => sum + i.accumulatedDepreciation, 0);
  const totDepr = items.reduce((sum, i) => sum + i.depreciationForTheYear, 0);
  const totClosing = items.reduce((sum, i) => sum + i.closingValue, 0);
  const totPrevClosing = items.reduce((sum, i) => sum + i.previousYearClosing, 0);

  totalRow.getCell(4).value = { formula: `SUM(D5:D${r - 1})`, result: totGross };
  totalRow.getCell(6).value = { formula: `SUM(F5:F${r - 1})`, result: totAccum };
  totalRow.getCell(7).value = { formula: `SUM(G5:G${r - 1})`, result: totDepr };
  totalRow.getCell(8).value = { formula: `SUM(H5:H${r - 1})`, result: totClosing };
  totalRow.getCell(9).value = { formula: `SUM(I5:I${r - 1})`, result: totPrevClosing };

  [4, 6, 7, 8, 9].forEach(c => {
    totalRow.getCell(c).numFmt = '₹#,##0.00';
    totalRow.getCell(c).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: 'FF141414' } };
    totalRow.getCell(c).alignment = { horizontal: 'right' };
  });

  for (let col = 1; col <= 10; col++) {
    totalRow.getCell(col).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFE2E8F0' } };
    totalRow.getCell(col).border = {
      top: { style: 'medium', color: { argb: 'FF141414' } },
      bottom: { style: 'double', color: { argb: 'FF141414' } },
      left: { style: 'thin', color: { argb: 'FFCBD5E1' } },
      right: { style: 'thin', color: { argb: 'FFCBD5E1' } }
    };
  }
  totalRow.height = 24;

  const uint8 = await wb.xlsx.writeBuffer();
  return new Blob([uint8], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}

/**
 * Intelligently extracts Depreciation Assets directly from Trial Balance ledgers.
 * Scans for Fixed Assets / PPE (Head A01 or keywords like machinery, furniture, computers, vehicles, etc.)
 * and detects any matching accumulated depreciation or depreciation expense ledgers in the TB.
 */
export function extractAssetsFromTrialBalance(ledgers: LedgerItem[]): DepreciationAssetItem[] {
  if (!ledgers || ledgers.length === 0) return [];

  // Keywords that identify Property, Plant & Equipment / Fixed Assets
  const fixedAssetKeywords = [
    'machinery', 'plant', 'equipment', 'furniture', 'fixture', 'fitting',
    'computer', 'laptop', 'printer', 'scanner', 'server', 'vehicle', 'car',
    'motor', 'truck', 'bike', 'van', 'tempo', 'building', 'premises', 'shed',
    'factory', 'land', 'air conditioner', 'ac ', 'refrigerator', 'generator',
    'inverter', 'ups', 'cctv', 'camera', 'tool', 'die', 'mould', 'intangible',
    'software', 'trademark', 'patent', 'fixed asset', 'capital asset', 'office equipment'
  ];

  // Helper to identify contra accounts or P&L depreciation expenses
  const isDeprContraOrExpense = (name: string) => {
    const n = name.toLowerCase();
    return (
      n.includes('accumulated depr') ||
      n.includes('provision for depr') ||
      n.includes('acc depr') ||
      n.includes('depreciation on') ||
      n.includes('depreciation a/c') ||
      n.includes('depreciation account') ||
      n.includes('depreciation expense')
    );
  };

  // Find accumulated depreciation ledgers in TB
  const accumDeprLedgers = ledgers.filter(l => {
    const n = l.ledgerName.toLowerCase();
    const g = (l.originalGroup || '').toLowerCase();
    return (
      n.includes('accumulated depr') ||
      n.includes('provision for depr') ||
      n.includes('acc depr') ||
      (l.headCode === 'A01' && l.credit > l.debit && n.includes('depr')) ||
      (g.includes('fixed') && n.includes('depr') && l.credit > l.debit)
    );
  });

  // Find current year depreciation expense ledgers in P&L
  const deprExpenseLedgers = ledgers.filter(l => {
    const n = l.ledgerName.toLowerCase();
    return l.targetType === 'PROFIT_AND_LOSS' && (n.includes('depreciation') || n.includes('amortization'));
  });

  const ppeLedgers: LedgerItem[] = [];
  const visitedNames = new Set<string>();

  // Priority 1: Ledgers explicitly assigned headCode 'A01' (Property, Plant & Equipment)
  ledgers.forEach(l => {
    const n = l.ledgerName.trim().toLowerCase();
    if (isDeprContraOrExpense(n)) return;
    if (visitedNames.has(n)) return;

    if (l.headCode === 'A01') {
      visitedNames.add(n);
      ppeLedgers.push(l);
    }
  });

  // Priority 2: Ledgers under group containing "Fixed Asset", "PPE", "Capital Asset"
  ledgers.forEach(l => {
    const n = l.ledgerName.trim().toLowerCase();
    const g = (l.originalGroup || '').toLowerCase();
    if (isDeprContraOrExpense(n)) return;
    if (visitedNames.has(n)) return;

    if (g.includes('fixed asset') || g.includes('fixed assets') || g.includes('property, plant') || g.includes('capital asset')) {
      visitedNames.add(n);
      ppeLedgers.push(l);
    }
  });

  // Priority 3: Asset-like name with debit / net balance in Balance Sheet
  ledgers.forEach(l => {
    const n = l.ledgerName.trim().toLowerCase();
    if (isDeprContraOrExpense(n)) return;
    if (visitedNames.has(n)) return;

    const hasKeyword = fixedAssetKeywords.some(kw => n.includes(kw));
    const isDebit = l.debit > 0 || l.netBalance > 0 || l.natureDrCr === 'Dr';
    const notExpense = l.targetType !== 'PROFIT_AND_LOSS' || n.includes('fixed asset') || n.includes('plant') || n.includes('machinery');

    if (hasKeyword && isDebit && notExpense) {
      visitedNames.add(n);
      ppeLedgers.push(l);
    }
  });

  // Map each matched TB Fixed Asset ledger to a DepreciationAssetItem
  return ppeLedgers.map((l, index) => {
    const name = l.ledgerName.trim();
    const n = name.toLowerCase();

    // Determine category & default IT Act depreciation rate
    let category = 'Plant & Machinery';
    let rate = 15;

    if (n.includes('computer') || n.includes('laptop') || n.includes('printer') || n.includes('scanner') || n.includes('server') || n.includes('it equipment') || n.includes('software')) {
      category = 'Computers & IT Hardware';
      rate = 40;
    } else if (n.includes('furniture') || n.includes('fixture') || n.includes('fitting') || n.includes('interior') || n.includes('chair') || n.includes('table') || n.includes('cabin')) {
      category = 'Furniture & Fixtures';
      rate = 10;
    } else if (n.includes('lorry') || n.includes('bus') || n.includes('truck') || n.includes('tempo') || n.includes('taxi') || n.includes('commercial vehicle')) {
      category = 'Commercial Motor Vehicles';
      rate = 30;
    } else if (n.includes('car') || n.includes('vehicle') || n.includes('motor') || n.includes('bike') || n.includes('van') || n.includes('scooter')) {
      category = 'Vehicles & Automobiles';
      rate = 15;
    } else if (n.includes('building') || n.includes('premises') || n.includes('factory') || n.includes('shed') || n.includes('office premises')) {
      category = 'Buildings & Civil Works';
      rate = 10;
    } else if (n.includes('land') && !n.includes('building')) {
      category = 'Land (Freehold / Leasehold)';
      rate = 0;
    } else if (n.includes('air conditioner') || n.includes('ac ') || n.includes('cooler') || n.includes('office equip') || n.includes('cctv') || n.includes('phone') || n.includes('mobile')) {
      category = 'Office Equipment';
      rate = 15;
    } else if (n.includes('electrical') || n.includes('generator') || n.includes('inverter') || n.includes('transformer') || n.includes('ups')) {
      category = 'Electrical Installations & Power Equipment';
      rate = 15;
    } else {
      category = 'Plant & Machinery';
      rate = 15;
    }

    // Amount from TB closing balance
    const netBal = l.debit > 0 ? l.debit : (l.netBalance > 0 ? l.netBalance : Math.abs(l.netBalance));
    const grossBlock = Math.round(netBal * 100) / 100;

    // Check if there is a matching accumulated depreciation ledger in TB
    const matchingAccum = accumDeprLedgers.find(al => {
      const an = al.ledgerName.toLowerCase();
      if (category.includes('Machinery') && (an.includes('machinery') || an.includes('plant'))) return true;
      if (category.includes('Furniture') && an.includes('furniture')) return true;
      if (category.includes('Computers') && (an.includes('computer') || an.includes('laptop'))) return true;
      if (category.includes('Vehicles') && (an.includes('vehicle') || an.includes('car') || an.includes('motor'))) return true;
      if (category.includes('Building') && an.includes('building')) return true;
      return false;
    });

    const accumDepr = matchingAccum ? Math.round(Math.max(0, (matchingAccum.credit || 0) - (matchingAccum.debit || 0)) * 100) / 100 : 0;

    // Check if there is a specific depreciation expense ledger in P&L for this asset
    const matchingExpense = deprExpenseLedgers.find(el => {
      const en = el.ledgerName.toLowerCase();
      if (category.includes('Machinery') && (en.includes('machinery') || en.includes('plant'))) return true;
      if (category.includes('Furniture') && en.includes('furniture')) return true;
      if (category.includes('Computers') && (en.includes('computer') || en.includes('laptop'))) return true;
      if (category.includes('Vehicles') && (en.includes('vehicle') || en.includes('car'))) return true;
      if (category.includes('Building') && en.includes('building')) return true;
      return false;
    });

    let deprForYear = 0;
    if (matchingExpense) {
      deprForYear = Math.round(Math.abs((matchingExpense.debit || 0) - (matchingExpense.credit || 0)) * 100) / 100;
    } else if (rate > 0) {
      // In standard Income Tax Act computation: Depreciation = Opening WDV * Rate%
      const openingWdv = Math.max(0, grossBlock - accumDepr);
      deprForYear = Math.round((openingWdv * (rate / 100)) * 100) / 100;
    }

    const closingValue = Math.round(Math.max(0, grossBlock - accumDepr - deprForYear) * 100) / 100;
    const previousYearClosing = Math.round(Math.max(0, grossBlock - accumDepr) * 100) / 100;

    return {
      id: `depr-tb-${l.id || index + 1}`,
      assetName: name,
      category,
      grossBlock,
      depreciationRate: rate,
      accumulatedDepreciation: accumDepr,
      depreciationForTheYear: deprForYear,
      closingValue,
      previousYearClosing,
      notes: `Imported from TB Closing Balance: ${name} (Head A01)`,
    };
  });
}

