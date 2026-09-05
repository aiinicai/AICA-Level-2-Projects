import ExcelJS from 'exceljs';
import {
  BalanceSheetHeadConfig,
  BalanceSheetSummary,
  DepreciationAssetItem,
  EntityDetails,
  LedgerItem,
  ManualAdjustment,
  NoteToAccountItem,
  PLStatement,
  ReconciliationReport,
  ScheduleData,
} from '../types/accounting';
import { DEFAULT_DEPRECIATION_ASSETS, DEFAULT_STANDARD_NOTES } from './nonCorporateDefaults';

// Styling Constants for Professional ICAI Non-Corporate Entity Financial Statements
const COLORS = {
  HEADER_FILL: '1E3A8A', // Deep Navy Blue (Corporate Title)
  HEADER_TEXT: 'FFFFFF',
  SUBHEADER_FILL: 'F1F5F9', // Subtle Slate 100
  SUBHEADER_TEXT: '0F172A',
  SECTION_FILL: 'E2E8F0', // Slate 200
  SECTION_TEXT: '0F172A',
  ACCENT_FILL: 'E0E7FF', // Indigo 100
  ZEBRA_FILL: 'F8FAFC',
  TOTAL_FILL: 'F1F5F9',
  BORDER_COLOR: 'CBD5E1', // Slate 300
  SUCCESS_FILL: 'DCFCE7', // Emerald 100
  SUCCESS_TEXT: '166534',
  WARN_FILL: 'FEF3C7',
  WARN_TEXT: '92400E',
};

const BORDERS = {
  thin: {
    top: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
    left: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
    bottom: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
    right: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
  },
  subTotalRow: {
    top: { style: 'thin' as const, color: { argb: '334155' } },
    bottom: { style: 'thin' as const, color: { argb: '334155' } },
    left: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
    right: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
  },
  totalRow: {
    top: { style: 'thin' as const, color: { argb: '000000' } },
    bottom: { style: 'double' as const, color: { argb: '000000' } },
    left: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
    right: { style: 'thin' as const, color: { argb: COLORS.BORDER_COLOR } },
  },
  headerRow: {
    top: { style: 'medium' as const, color: { argb: '1E3A8A' } },
    bottom: { style: 'medium' as const, color: { argb: '1E3A8A' } },
  },
};

// Standard Indian Lakhs/Crores Number Format in Excel
const NUMBER_FORMAT = '#,##,##0.00;[Red](#,##,##0.00);"-";@';

function sanitizeSheetName(name: string): string {
  // Excel sheet names max 31 chars and no : \ / ? * [ ]
  const cleaned = name.replace(/[:\\/?*\[\]]/g, ' ').trim();
  return cleaned.length > 30 ? cleaned.substring(0, 30) : cleaned;
}

export async function generateBalanceSheetExcelWorkbook(
  entity: EntityDetails,
  heads: BalanceSheetHeadConfig[],
  ledgers: LedgerItem[],
  plStatement: PLStatement,
  schedules: ScheduleData[],
  balanceSheet: BalanceSheetSummary,
  reconciliation: ReconciliationReport,
  adjustments: ManualAdjustment[] = [],
  depreciationAssets: DepreciationAssetItem[] = [],
  notesToAccounts: NoteToAccountItem[] = []
): Promise<Blob> {
  const workbook = new ExcelJS.Workbook();
  workbook.creator = entity.auditorName || 'Chartered Accountant / Auditor';
  workbook.lastModifiedBy = 'AccuSheet.Pro ICAI Financial Statement Engine';
  workbook.created = new Date();
  workbook.modified = new Date();

  const activeHeads = heads
    .filter(h => h.active)
    .sort((a, b) => Number(a.scheduleNo) - Number(b.scheduleNo));

  const getAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s ? s.totalAmount : 0;
  };

  const getPrevAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s?.previousYearTotal !== undefined ? s.previousYearTotal : 0;
  };

  // =========================================================================
  // SHEET 1: CONTROL SHEET (Central Configuration & Master Data)
  // =========================================================================
  const wsControl = workbook.addWorksheet('CONTROL', { views: [{ showGridLines: true }] });

  wsControl.mergeCells('A1:G1');
  const titleCell = wsControl.getCell('A1');
  titleCell.value = `${entity.name.toUpperCase()} — FINANCIAL STATEMENTS WORKING PAPERS`;
  titleCell.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  titleCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  titleCell.alignment = { vertical: 'middle', horizontal: 'center' };
  wsControl.getRow(1).height = 30;

  wsControl.mergeCells('A2:G2');
  const subTitleCell = wsControl.getCell('A2');
  subTitleCell.value = `CONTROL SHEET & CENTRAL CONFIGURATION | FY: ${entity.financialYear} | AS ON: ${entity.balanceSheetDate}`;
  subTitleCell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '334155' } };
  subTitleCell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E2E8F0' } };
  subTitleCell.alignment = { vertical: 'middle', horizontal: 'center' };
  wsControl.getRow(2).height = 20;

  // Section A: Entity Master Info
  wsControl.getCell('A4').value = 'A. ENTITY MASTER DETAILS';
  wsControl.getCell('A4').font = { name: 'Segoe UI', size: 11, bold: true, color: { argb: '1E3A8A' } };

  const entityInfo = [
    ['Entity Name:', entity.name, 'Entity Type:', entity.entityType],
    ['PAN:', entity.pan, 'GSTIN:', entity.gstin],
    ['Address:', entity.address, 'Financial Year:', entity.financialYear],
    ['Balance Sheet Date:', entity.balanceSheetDate, 'Previous Year Date:', entity.previousYearDate || '31-03-2024'],
    ['Auditor / CA Firm:', entity.auditorName || 'Chartered Accountants', 'Membership / FRN:', `${entity.membershipNumber || ''} / ${entity.firmRegistrationNo || ''}`],
    ['UDIN:', entity.udin || '25512948BGXYZW1234', 'Place of Signing:', entity.placeOfSigning || 'Navi Mumbai'],
  ];

  entityInfo.forEach((row, idx) => {
    const rowNum = 5 + idx;
    wsControl.getCell(`A${rowNum}`).value = row[0];
    wsControl.getCell(`A${rowNum}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '475569' } };
    wsControl.getCell(`B${rowNum}`).value = row[1];
    wsControl.getCell(`B${rowNum}`).font = { name: 'Segoe UI', size: 10 };

    wsControl.getCell(`D${rowNum}`).value = row[2];
    wsControl.getCell(`D${rowNum}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '475569' } };
    wsControl.getCell(`E${rowNum}`).value = row[3];
    wsControl.getCell(`E${rowNum}`).font = { name: 'Segoe UI', size: 10 };
  });

  // Section B: Balance Sheet Head Configuration Table
  const headConfigStartRow = 13;
  wsControl.getCell(`A${headConfigStartRow - 1}`).value = 'B. BALANCE SHEET HEAD CONFIGURATION & SCHEDULE MAPPING';
  wsControl.getCell(`A${headConfigStartRow - 1}`).font = { name: 'Segoe UI', size: 11, bold: true, color: { argb: '1E3A8A' } };

  const controlHeaders = ['Code', 'Main Head', 'Sub Head (Schedule Name)', 'Schedule No.', 'Nature', 'Display Order', 'Active'];
  controlHeaders.forEach((h, i) => {
    const cell = wsControl.getCell(headConfigStartRow, i + 1);
    cell.value = h;
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    cell.alignment = { vertical: 'middle', horizontal: i >= 3 ? 'center' : 'left' };
    cell.border = BORDERS.thin;
  });
  wsControl.getRow(headConfigStartRow).height = 24;

  heads.forEach((head, idx) => {
    const rowNum = headConfigStartRow + 1 + idx;
    const rowValues = [
      head.code,
      head.mainHead,
      head.subHead,
      head.scheduleNo,
      head.nature,
      head.displayOrder,
      head.active ? 'Yes' : 'No',
    ];

    rowValues.forEach((val, cIdx) => {
      const cell = wsControl.getCell(rowNum, cIdx + 1);
      cell.value = val;
      cell.font = { name: 'Segoe UI', size: 10 };
      cell.border = BORDERS.thin;
      if (cIdx >= 3) {
        cell.alignment = { vertical: 'middle', horizontal: 'center' };
      }
      if (idx % 2 === 1) {
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
      }
    });
  });

  wsControl.columns = [
    { width: 18 },
    { width: 34 },
    { width: 34 },
    { width: 16 },
    { width: 16 },
    { width: 16 },
    { width: 14 },
  ];

  // =========================================================================
  // SHEET 2: BALANCE SHEET (ICAI PRESCRIBED VERTICAL FORMAT)
  // =========================================================================
  const wsBS = workbook.addWorksheet('BALANCE SHEET', { views: [{ showGridLines: true }] });

  // Main Header
  wsBS.mergeCells('A1:D1');
  const bsHeader = wsBS.getCell('A1');
  bsHeader.value = `${entity.name.toUpperCase()}`;
  bsHeader.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  bsHeader.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  bsHeader.alignment = { vertical: 'middle', horizontal: 'center' };
  wsBS.getRow(1).height = 26;

  wsBS.mergeCells('A2:D2');
  const bsSubHeader = wsBS.getCell('A2');
  bsSubHeader.value = `BALANCE SHEET AS AT ${entity.balanceSheetDate.toUpperCase()}`;
  bsSubHeader.font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  bsSubHeader.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E2E8F0' } };
  bsSubHeader.alignment = { vertical: 'middle', horizontal: 'center' };
  wsBS.getRow(2).height = 20;

  wsBS.mergeCells('A3:D3');
  const bsFormatNote = wsBS.getCell('A3');
  bsFormatNote.value = `[Form of Balance Sheet for Non-Corporate Entities in accordance with ICAI Technical Guide]`;
  bsFormatNote.font = { name: 'Segoe UI', size: 9, italic: true, color: { argb: '475569' } };
  bsFormatNote.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F8FAFC' } };
  bsFormatNote.alignment = { vertical: 'middle', horizontal: 'center' };
  wsBS.getRow(3).height = 18;

  // Table Column Headers
  const bsColHeaders = [
    'Particulars',
    'Note No.',
    `Figures as at ${entity.balanceSheetDate} (₹)`,
    `Figures as at ${entity.previousYearDate || '31-03-2024'} (₹)`,
  ];
  wsBS.getRow(5).values = bsColHeaders;
  wsBS.getRow(5).height = 24;
  bsColHeaders.forEach((_, i) => {
    const cell = wsBS.getCell(5, i + 1);
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    cell.alignment = { vertical: 'middle', horizontal: i === 1 ? 'center' : i >= 2 ? 'right' : 'left' };
    cell.border = BORDERS.thin;
  });

  let bsRow = 6;

  // Categorize Active Heads
  const ownersHeads = activeHeads.filter(h => h.nature === 'Liability' && (h.icaiMajorCategory === 'OWNERS_FUNDS' || h.code === 'L01' || h.code === 'L02'));
  const nonCurLiabHeads = activeHeads.filter(h => h.nature === 'Liability' && (h.icaiMajorCategory === 'NON_CURRENT_LIABILITIES' || h.code === 'L03' || h.code === 'L04'));
  const curLiabHeads = activeHeads.filter(h => h.nature === 'Liability' && (h.icaiMajorCategory === 'CURRENT_LIABILITIES' || h.code === 'L05' || h.code === 'L06' || h.code === 'L07'));

  const nonCurAssetHeads = activeHeads.filter(h => h.nature === 'Asset' && (h.icaiMajorCategory === 'NON_CURRENT_ASSETS' || h.code === 'A01' || h.code === 'A02'));
  const curAssetHeads = activeHeads.filter(h => h.nature === 'Asset' && (h.icaiMajorCategory === 'CURRENT_ASSETS' || ['A03', 'A04', 'A05', 'A06', 'A07'].includes(h.code)));

  const subTotalOwners = ownersHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalNonCurLiab = nonCurLiabHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalCurLiab = curLiabHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalNonCurAssets = nonCurAssetHeads.reduce((acc, h) => acc + getAmount(h.code), 0);
  const subTotalCurAssets = curAssetHeads.reduce((acc, h) => acc + getAmount(h.code), 0);

  // SECTION I: EQUITY AND LIABILITIES
  wsBS.mergeCells(`A${bsRow}:D${bsRow}`);
  const sec1Cell = wsBS.getCell(`A${bsRow}`);
  sec1Cell.value = 'I. EQUITY AND LIABILITIES';
  sec1Cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
  sec1Cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SECTION_FILL } };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  // (1) Owners' Funds
  wsBS.getCell(`A${bsRow}`).value = "  (1) Owners' / Partners' Funds";
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  const ownersStartRow = bsRow;
  ownersHeads.forEach(h => {
    wsBS.getCell(`A${bsRow}`).value = `        ${h.subHead}`;
    wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).value = h.scheduleNo;
    wsBS.getCell(`B${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).alignment = { horizontal: 'center' };
    wsBS.getCell(`C${bsRow}`).value = getAmount(h.code);
    wsBS.getCell(`C${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`C${bsRow}`).numFmt = NUMBER_FORMAT;
    wsBS.getCell(`D${bsRow}`).value = getPrevAmount(h.code);
    wsBS.getCell(`D${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`D${bsRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
    bsRow++;
  });

  const ownersEndRow = bsRow - 1;
  const ownersSubTotalRow = bsRow;
  wsBS.getCell(`A${ownersSubTotalRow}`).value = "        Sub-Total: Owners' / Partners' Funds";
  wsBS.getCell(`A${ownersSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${ownersSubTotalRow}`).value = { formula: `SUM(C${ownersStartRow}:C${ownersEndRow})`, result: subTotalOwners };
  wsBS.getCell(`C${ownersSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${ownersSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${ownersSubTotalRow}`).value = { formula: `SUM(D${ownersStartRow}:D${ownersEndRow})`, result: ownersHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${ownersSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`D${ownersSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(ownersSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsBS.getCell(ownersSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  bsRow++;

  // (2) Non-Current Liabilities
  wsBS.getCell(`A${bsRow}`).value = '  (2) Non-Current Liabilities';
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  const nonCurLiabStartRow = bsRow;
  nonCurLiabHeads.forEach(h => {
    wsBS.getCell(`A${bsRow}`).value = `        ${h.subHead}`;
    wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).value = h.scheduleNo;
    wsBS.getCell(`B${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).alignment = { horizontal: 'center' };
    wsBS.getCell(`C${bsRow}`).value = getAmount(h.code);
    wsBS.getCell(`C${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`C${bsRow}`).numFmt = NUMBER_FORMAT;
    wsBS.getCell(`D${bsRow}`).value = getPrevAmount(h.code);
    wsBS.getCell(`D${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`D${bsRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
    bsRow++;
  });

  const nonCurLiabEndRow = bsRow - 1;
  const nonCurLiabSubTotalRow = bsRow;
  wsBS.getCell(`A${nonCurLiabSubTotalRow}`).value = '        Sub-Total: Non-Current Liabilities';
  wsBS.getCell(`A${nonCurLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${nonCurLiabSubTotalRow}`).value = { formula: `SUM(C${nonCurLiabStartRow}:C${nonCurLiabEndRow})`, result: subTotalNonCurLiab };
  wsBS.getCell(`C${nonCurLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${nonCurLiabSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${nonCurLiabSubTotalRow}`).value = { formula: `SUM(D${nonCurLiabStartRow}:D${nonCurLiabEndRow})`, result: nonCurLiabHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${nonCurLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`D${nonCurLiabSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(nonCurLiabSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsBS.getCell(nonCurLiabSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  bsRow++;

  // (3) Current Liabilities
  wsBS.getCell(`A${bsRow}`).value = '  (3) Current Liabilities';
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  const curLiabStartRow = bsRow;
  curLiabHeads.forEach(h => {
    wsBS.getCell(`A${bsRow}`).value = `        ${h.subHead}`;
    wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).value = h.scheduleNo;
    wsBS.getCell(`B${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).alignment = { horizontal: 'center' };
    wsBS.getCell(`C${bsRow}`).value = getAmount(h.code);
    wsBS.getCell(`C${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`C${bsRow}`).numFmt = NUMBER_FORMAT;
    wsBS.getCell(`D${bsRow}`).value = getPrevAmount(h.code);
    wsBS.getCell(`D${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`D${bsRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
    bsRow++;
  });

  const curLiabEndRow = bsRow - 1;
  const curLiabSubTotalRow = bsRow;
  wsBS.getCell(`A${curLiabSubTotalRow}`).value = '        Sub-Total: Current Liabilities';
  wsBS.getCell(`A${curLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${curLiabSubTotalRow}`).value = { formula: `SUM(C${curLiabStartRow}:C${curLiabEndRow})`, result: subTotalCurLiab };
  wsBS.getCell(`C${curLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${curLiabSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${curLiabSubTotalRow}`).value = { formula: `SUM(D${curLiabStartRow}:D${curLiabEndRow})`, result: curLiabHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${curLiabSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`D${curLiabSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(curLiabSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsBS.getCell(curLiabSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  bsRow++;

  // TOTAL EQUITY & LIABILITIES
  const totalLiabRow = bsRow;
  wsBS.getCell(`A${totalLiabRow}`).value = 'TOTAL EQUITY & LIABILITIES';
  wsBS.getCell(`A${totalLiabRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  wsBS.getCell(`C${totalLiabRow}`).value = { formula: `C${ownersSubTotalRow}+C${nonCurLiabSubTotalRow}+C${curLiabSubTotalRow}`, result: balanceSheet.totalLiabilities };
  wsBS.getCell(`C${totalLiabRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsBS.getCell(`C${totalLiabRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${totalLiabRow}`).value = { formula: `D${ownersSubTotalRow}+D${nonCurLiabSubTotalRow}+D${curLiabSubTotalRow}`, result: (ownersHeads.concat(nonCurLiabHeads, curLiabHeads)).reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${totalLiabRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsBS.getCell(`D${totalLiabRow}`).numFmt = NUMBER_FORMAT;

  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(totalLiabRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    wsBS.getCell(totalLiabRow, c).border = BORDERS.totalRow;
  }
  bsRow += 2;

  // SECTION II: ASSETS
  wsBS.mergeCells(`A${bsRow}:D${bsRow}`);
  const sec2Cell = wsBS.getCell(`A${bsRow}`);
  sec2Cell.value = 'II. ASSETS';
  sec2Cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
  sec2Cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SECTION_FILL } };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  // (1) Non-Current Assets
  wsBS.getCell(`A${bsRow}`).value = '  (1) Non-Current Assets';
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  const nonCurAssetStartRow = bsRow;
  nonCurAssetHeads.forEach(h => {
    wsBS.getCell(`A${bsRow}`).value = `        ${h.subHead}`;
    wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).value = h.scheduleNo;
    wsBS.getCell(`B${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).alignment = { horizontal: 'center' };
    wsBS.getCell(`C${bsRow}`).value = getAmount(h.code);
    wsBS.getCell(`C${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`C${bsRow}`).numFmt = NUMBER_FORMAT;
    wsBS.getCell(`D${bsRow}`).value = getPrevAmount(h.code);
    wsBS.getCell(`D${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`D${bsRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
    bsRow++;
  });

  const nonCurAssetEndRow = bsRow - 1;
  const nonCurAssetSubTotalRow = bsRow;
  wsBS.getCell(`A${nonCurAssetSubTotalRow}`).value = '        Sub-Total: Non-Current Assets';
  wsBS.getCell(`A${nonCurAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${nonCurAssetSubTotalRow}`).value = { formula: `SUM(C${nonCurAssetStartRow}:C${nonCurAssetEndRow})`, result: subTotalNonCurAssets };
  wsBS.getCell(`C${nonCurAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${nonCurAssetSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${nonCurAssetSubTotalRow}`).value = { formula: `SUM(D${nonCurAssetStartRow}:D${nonCurAssetEndRow})`, result: nonCurAssetHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${nonCurAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`D${nonCurAssetSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(nonCurAssetSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsBS.getCell(nonCurAssetSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  bsRow++;

  // (2) Current Assets
  wsBS.getCell(`A${bsRow}`).value = '  (2) Current Assets';
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
  bsRow++;

  const curAssetStartRow = bsRow;
  curAssetHeads.forEach(h => {
    wsBS.getCell(`A${bsRow}`).value = `        ${h.subHead}`;
    wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).value = h.scheduleNo;
    wsBS.getCell(`B${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`B${bsRow}`).alignment = { horizontal: 'center' };
    wsBS.getCell(`C${bsRow}`).value = getAmount(h.code);
    wsBS.getCell(`C${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`C${bsRow}`).numFmt = NUMBER_FORMAT;
    wsBS.getCell(`D${bsRow}`).value = getPrevAmount(h.code);
    wsBS.getCell(`D${bsRow}`).font = { name: 'Segoe UI', size: 10 };
    wsBS.getCell(`D${bsRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsBS.getCell(bsRow, c).border = BORDERS.thin;
    bsRow++;
  });

  const curAssetEndRow = bsRow - 1;
  const curAssetSubTotalRow = bsRow;
  wsBS.getCell(`A${curAssetSubTotalRow}`).value = '        Sub-Total: Current Assets';
  wsBS.getCell(`A${curAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${curAssetSubTotalRow}`).value = { formula: `SUM(C${curAssetStartRow}:C${curAssetEndRow})`, result: subTotalCurAssets };
  wsBS.getCell(`C${curAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`C${curAssetSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${curAssetSubTotalRow}`).value = { formula: `SUM(D${curAssetStartRow}:D${curAssetEndRow})`, result: curAssetHeads.reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${curAssetSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsBS.getCell(`D${curAssetSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(curAssetSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsBS.getCell(curAssetSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  bsRow++;

  // TOTAL ASSETS
  const totalAssetsRow = bsRow;
  wsBS.getCell(`A${totalAssetsRow}`).value = 'TOTAL ASSETS';
  wsBS.getCell(`A${totalAssetsRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  wsBS.getCell(`C${totalAssetsRow}`).value = { formula: `C${nonCurAssetSubTotalRow}+C${curAssetSubTotalRow}`, result: balanceSheet.totalAssets };
  wsBS.getCell(`C${totalAssetsRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsBS.getCell(`C${totalAssetsRow}`).numFmt = NUMBER_FORMAT;
  wsBS.getCell(`D${totalAssetsRow}`).value = { formula: `D${nonCurAssetSubTotalRow}+D${curAssetSubTotalRow}`, result: (nonCurAssetHeads.concat(curAssetHeads)).reduce((acc, h) => acc + getPrevAmount(h.code), 0) };
  wsBS.getCell(`D${totalAssetsRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsBS.getCell(`D${totalAssetsRow}`).numFmt = NUMBER_FORMAT;

  for (let c = 1; c <= 4; c++) {
    wsBS.getCell(totalAssetsRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    wsBS.getCell(totalAssetsRow, c).border = BORDERS.totalRow;
  }
  bsRow += 2;

  // Difference Check Row
  const diffRow = bsRow;
  wsBS.getCell(`A${diffRow}`).value = 'Balance Sheet Difference (Assets - Liabilities):';
  wsBS.getCell(`A${diffRow}`).font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: '64748B' } };
  wsBS.getCell(`C${diffRow}`).value = { formula: `C${totalAssetsRow}-C${totalLiabRow}`, result: balanceSheet.difference };
  wsBS.getCell(`C${diffRow}`).font = { name: 'Segoe UI', size: 9.5, bold: true };
  wsBS.getCell(`C${diffRow}`).numFmt = NUMBER_FORMAT;

  wsBS.getCell(`D${diffRow}`).value = Math.abs(balanceSheet.difference) < 0.01 ? 'BALANCED ✓' : 'NOT BALANCED ⚠';
  wsBS.getCell(`D${diffRow}`).font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: Math.abs(balanceSheet.difference) < 0.01 ? '166534' : 'DC2626' } };
  bsRow += 2;

  // Footnote
  wsBS.getCell(`A${bsRow}`).value = 'The accompanying Schedules 1 to 14 and Significant Accounting Policies (Note 15) form an integral part of these Financial Statements.';
  wsBS.getCell(`A${bsRow}`).font = { name: 'Segoe UI', size: 9, italic: true, color: { argb: '64748B' } };
  bsRow += 2;

  // Dual Signatures section
  const sigRow = bsRow;
  wsBS.getCell(`A${sigRow}`).value = 'For and on behalf of: ' + entity.name;
  wsBS.getCell(`A${sigRow}`).font = { bold: true, name: 'Segoe UI', size: 10 };
  wsBS.getCell(`C${sigRow}`).value = 'In terms of our audit report of even date attached:';
  wsBS.getCell(`C${sigRow}`).font = { bold: true, name: 'Segoe UI', size: 10 };

  wsBS.getCell(`A${sigRow + 2}`).value = entity.proprietorOrPartnerNames?.[0] || 'Proprietor / Authorized Partner';
  wsBS.getCell(`A${sigRow + 2}`).font = { name: 'Segoe UI', size: 9.5, bold: true };
  wsBS.getCell(`A${sigRow + 3}`).value = `Proprietor / Partner\nPlace: ${entity.placeOfSigning || 'Navi Mumbai'} | Date: ${entity.dateOfSigning || entity.balanceSheetDate}`;
  wsBS.getCell(`A${sigRow + 3}`).font = { name: 'Segoe UI', size: 9, color: { argb: '64748B' } };

  wsBS.getCell(`C${sigRow + 2}`).value = `For ${entity.auditorName || 'Chartered Accountants'}\nChartered Accountants | FRN: ${entity.firmRegistrationNo || '124982W'}`;
  wsBS.getCell(`C${sigRow + 2}`).font = { name: 'Segoe UI', size: 9.5, bold: true };
  wsBS.getCell(`C${sigRow + 3}`).value = `UDIN: ${entity.udin || '25512948BGXYZW1234'} | M.No: ${entity.membershipNumber || '512948'}\nPlace: ${entity.placeOfSigning || 'Navi Mumbai'} | Date: ${entity.dateOfSigning || entity.balanceSheetDate}`;
  wsBS.getCell(`C${sigRow + 3}`).font = { name: 'Segoe UI', size: 9, color: { argb: '166534' }, bold: true };

  wsBS.columns = [
    { width: 56 },
    { width: 14 },
    { width: 26 },
    { width: 26 },
  ];

  // =========================================================================
  // SHEET 3: PROFIT & LOSS (OFFICIAL ICAI VERTICAL STATEMENT OF P&L)
  // =========================================================================
  const wsPL = workbook.addWorksheet('PROFIT & LOSS', { views: [{ showGridLines: true }] });

  wsPL.mergeCells('A1:D1');
  const plTitle = wsPL.getCell('A1');
  plTitle.value = `${entity.name.toUpperCase()}`;
  plTitle.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  plTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  plTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsPL.getRow(1).height = 26;

  wsPL.mergeCells('A2:D2');
  const plSubTitle = wsPL.getCell('A2');
  plSubTitle.value = `STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED ${entity.balanceSheetDate.toUpperCase()}`;
  plSubTitle.font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  plSubTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E2E8F0' } };
  plSubTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsPL.getRow(2).height = 20;

  wsPL.mergeCells('A3:D3');
  const plFormatNote = wsPL.getCell('A3');
  plFormatNote.value = `[Form of Statement of Profit and Loss for Non-Corporate Entities as per ICAI Technical Guide]`;
  plFormatNote.font = { name: 'Segoe UI', size: 9, italic: true, color: { argb: '475569' } };
  plFormatNote.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F8FAFC' } };
  plFormatNote.alignment = { vertical: 'middle', horizontal: 'center' };
  wsPL.getRow(3).height = 18;

  // Table Column Headers
  const plColHeaders = [
    'Particulars',
    'Note No.',
    `Figures for the Year ended ${entity.balanceSheetDate} (₹)`,
    `Figures for Previous Year ended ${entity.previousYearDate || '31-03-2024'} (₹)`,
  ];
  wsPL.getRow(5).values = plColHeaders;
  wsPL.getRow(5).height = 24;
  plColHeaders.forEach((_, i) => {
    const cell = wsPL.getCell(5, i + 1);
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    cell.alignment = { vertical: 'middle', horizontal: i === 1 ? 'center' : i >= 2 ? 'right' : 'left' };
    cell.border = BORDERS.thin;
  });

  let plRow = 6;

  // I. REVENUE FROM OPERATIONS
  wsPL.mergeCells(`A${plRow}:D${plRow}`);
  wsPL.getCell(`A${plRow}`).value = 'I. REVENUE FROM OPERATIONS';
  wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
  wsPL.getCell(`A${plRow}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SECTION_FILL } };
  for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
  plRow++;

  const revStartRow = plRow;
  if (plStatement.directIncomes.length > 0) {
    plStatement.directIncomes.forEach(inc => {
      wsPL.getCell(`A${plRow}`).value = `        ${inc.name}`;
      wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
      wsPL.getCell(`B${plRow}`).value = '14';
      wsPL.getCell(`B${plRow}`).alignment = { horizontal: 'center' };
      wsPL.getCell(`C${plRow}`).value = inc.amount;
      wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
      wsPL.getCell(`D${plRow}`).value = 0;
      wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
      plRow++;
    });
  } else {
    wsPL.getCell(`A${plRow}`).value = `        Gross Sales / Operational Receipts`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`B${plRow}`).value = '14';
    wsPL.getCell(`B${plRow}`).alignment = { horizontal: 'center' };
    wsPL.getCell(`C${plRow}`).value = plStatement.totalDirectIncome;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  }
  const revEndRow = plRow - 1;
  const revSubTotalRow = plRow;
  wsPL.getCell(`A${revSubTotalRow}`).value = '        Total Revenue from Operations (I)';
  wsPL.getCell(`A${revSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsPL.getCell(`C${revSubTotalRow}`).value = { formula: `SUM(C${revStartRow}:C${revEndRow})`, result: plStatement.totalDirectIncome };
  wsPL.getCell(`C${revSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsPL.getCell(`C${revSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${revSubTotalRow}`).value = 0;
  wsPL.getCell(`D${revSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(revSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsPL.getCell(revSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  plRow++;

  // II. OTHER INCOME
  wsPL.mergeCells(`A${plRow}:D${plRow}`);
  wsPL.getCell(`A${plRow}`).value = 'II. OTHER INCOME';
  wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
  wsPL.getCell(`A${plRow}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SECTION_FILL } };
  for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
  plRow++;

  const otherIncStartRow = plRow;
  if (plStatement.indirectIncomes.length > 0) {
    plStatement.indirectIncomes.forEach(inc => {
      wsPL.getCell(`A${plRow}`).value = `        ${inc.name}`;
      wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
      wsPL.getCell(`C${plRow}`).value = inc.amount;
      wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
      wsPL.getCell(`D${plRow}`).value = 0;
      wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
      plRow++;
    });
  } else {
    wsPL.getCell(`A${plRow}`).value = `        Interest, Commission & Other Indirect Incomes`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`C${plRow}`).value = plStatement.totalIndirectIncome;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  }
  const otherIncEndRow = plRow - 1;
  const otherIncSubTotalRow = plRow;
  wsPL.getCell(`A${otherIncSubTotalRow}`).value = '        Total Other Income (II)';
  wsPL.getCell(`A${otherIncSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsPL.getCell(`C${otherIncSubTotalRow}`).value = { formula: `SUM(C${otherIncStartRow}:C${otherIncEndRow})`, result: plStatement.totalIndirectIncome };
  wsPL.getCell(`C${otherIncSubTotalRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  wsPL.getCell(`C${otherIncSubTotalRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${otherIncSubTotalRow}`).value = 0;
  wsPL.getCell(`D${otherIncSubTotalRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(otherIncSubTotalRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsPL.getCell(otherIncSubTotalRow, c).border = BORDERS.subTotalRow;
  }
  plRow++;

  // III. TOTAL REVENUE
  const totalRevRow = plRow;
  wsPL.getCell(`A${totalRevRow}`).value = 'III. TOTAL REVENUE / INCOME (I + II)';
  wsPL.getCell(`A${totalRevRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  wsPL.getCell(`C${totalRevRow}`).value = { formula: `C${revSubTotalRow}+C${otherIncSubTotalRow}`, result: plStatement.totalDirectIncome + plStatement.totalIndirectIncome };
  wsPL.getCell(`C${totalRevRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsPL.getCell(`C${totalRevRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${totalRevRow}`).value = { formula: `D${revSubTotalRow}+D${otherIncSubTotalRow}`, result: 0 };
  wsPL.getCell(`D${totalRevRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsPL.getCell(`D${totalRevRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(totalRevRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    wsPL.getCell(totalRevRow, c).border = BORDERS.totalRow;
  }
  plRow += 2;

  // IV. EXPENSES
  wsPL.mergeCells(`A${plRow}:D${plRow}`);
  wsPL.getCell(`A${plRow}`).value = 'IV. EXPENSES';
  wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
  wsPL.getCell(`A${plRow}`).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SECTION_FILL } };
  for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
  plRow++;

  // (a) Cost of Materials & Direct Expenses
  wsPL.getCell(`A${plRow}`).value = "  (a) Cost of Materials & Direct Trading Expenses";
  wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
  plRow++;

  const expDirectStartRow = plRow;
  if (plStatement.openingStock > 0) {
    wsPL.getCell(`A${plRow}`).value = `        To Opening Stock of Inventory`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`B${plRow}`).value = '10';
    wsPL.getCell(`B${plRow}`).alignment = { horizontal: 'center' };
    wsPL.getCell(`C${plRow}`).value = plStatement.openingStock;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  }

  plStatement.directExpenses.forEach(exp => {
    wsPL.getCell(`A${plRow}`).value = `        To ${exp.name}`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`C${plRow}`).value = exp.amount;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  });

  if (plStatement.closingStock > 0) {
    wsPL.getCell(`A${plRow}`).value = `        Less: Closing Stock of Inventory as at ${entity.balanceSheetDate}`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`B${plRow}`).value = '10';
    wsPL.getCell(`B${plRow}`).alignment = { horizontal: 'center' };
    wsPL.getCell(`C${plRow}`).value = -plStatement.closingStock;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  }
  const expDirectEndRow = plRow - 1;

  // Trading Gross Profit
  const gpRow = plRow;
  wsPL.getCell(`A${gpRow}`).value = '        GROSS PROFIT (Transferred to Operating Statement)';
  wsPL.getCell(`A${gpRow}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '166534' } };
  wsPL.getCell(`C${gpRow}`).value = { formula: `C${revSubTotalRow}-SUM(C${expDirectStartRow}:C${expDirectEndRow})`, result: plStatement.grossProfit };
  wsPL.getCell(`C${gpRow}`).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '166534' } };
  wsPL.getCell(`C${gpRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${gpRow}`).value = 0;
  wsPL.getCell(`D${gpRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(gpRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsPL.getCell(gpRow, c).border = BORDERS.subTotalRow;
  }
  plRow++;

  // (b) Indirect Operating & Administrative Expenses
  wsPL.getCell(`A${plRow}`).value = "  (b) Indirect Operating, Administrative & Finance Expenses";
  wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
  for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
  plRow++;

  const expIndirectStartRow = plRow;
  if (plStatement.indirectExpenses.length > 0) {
    plStatement.indirectExpenses.forEach(exp => {
      wsPL.getCell(`A${plRow}`).value = `        To ${exp.name}`;
      wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
      wsPL.getCell(`C${plRow}`).value = exp.amount;
      wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
      wsPL.getCell(`D${plRow}`).value = 0;
      wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
      plRow++;
    });
  } else {
    wsPL.getCell(`A${plRow}`).value = `        To Other Operating & Administrative Expenses`;
    wsPL.getCell(`A${plRow}`).font = { name: 'Segoe UI', size: 10 };
    wsPL.getCell(`C${plRow}`).value = 0;
    wsPL.getCell(`C${plRow}`).numFmt = NUMBER_FORMAT;
    wsPL.getCell(`D${plRow}`).value = 0;
    wsPL.getCell(`D${plRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 4; c++) wsPL.getCell(plRow, c).border = BORDERS.thin;
    plRow++;
  }
  const expIndirectEndRow = plRow - 1;

  // TOTAL EXPENSES (IV)
  const totalExpRow = plRow;
  wsPL.getCell(`A${totalExpRow}`).value = 'TOTAL EXPENSES (IV)';
  wsPL.getCell(`A${totalExpRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '0F172A' } };
  const calculatedTotalExpenses = (plStatement.openingStock + plStatement.totalDirectExpenses - plStatement.closingStock + plStatement.totalIndirectExpenses);
  wsPL.getCell(`C${totalExpRow}`).value = { formula: `SUM(C${expDirectStartRow}:C${expDirectEndRow})+SUM(C${expIndirectStartRow}:C${expIndirectEndRow})`, result: calculatedTotalExpenses };
  wsPL.getCell(`C${totalExpRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsPL.getCell(`C${totalExpRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${totalExpRow}`).value = 0;
  wsPL.getCell(`D${totalExpRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(totalExpRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    wsPL.getCell(totalExpRow, c).border = BORDERS.totalRow;
  }
  plRow += 2;

  // V. NET PROFIT BEFORE TAX
  const pbtRow = plRow;
  wsPL.getCell(`A${pbtRow}`).value = 'V. PROFIT / (LOSS) BEFORE TAX (III - IV)';
  wsPL.getCell(`A${pbtRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsPL.getCell(`C${pbtRow}`).value = { formula: `C${totalRevRow}-C${totalExpRow}`, result: plStatement.netProfitBeforeTax };
  wsPL.getCell(`C${pbtRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true };
  wsPL.getCell(`C${pbtRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${pbtRow}`).value = 0;
  wsPL.getCell(`D${pbtRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(pbtRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUBHEADER_FILL } };
    wsPL.getCell(pbtRow, c).border = BORDERS.subTotalRow;
  }
  plRow++;

  // VI. Tax Provision
  const taxRow = plRow;
  wsPL.getCell(`A${taxRow}`).value = `VI. Tax Expense (Current Tax Provision)`;
  wsPL.getCell(`A${taxRow}`).font = { name: 'Segoe UI', size: 10 };
  wsPL.getCell(`C${taxRow}`).value = plStatement.taxProvision;
  wsPL.getCell(`C${taxRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${taxRow}`).value = 0;
  wsPL.getCell(`D${taxRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) wsPL.getCell(taxRow, c).border = BORDERS.thin;
  plRow++;

  // VII. NET PROFIT TRANSFERRED TO CAPITAL ACCOUNT
  const netProfitRow = plRow;
  wsPL.getCell(`A${netProfitRow}`).value = 'VII. PROFIT / (LOSS) FOR THE YEAR TRANSFERRED TO CAPITAL A/C';
  wsPL.getCell(`A${netProfitRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '166534' } };
  wsPL.getCell(`B${netProfitRow}`).value = '1';
  wsPL.getCell(`B${netProfitRow}`).alignment = { horizontal: 'center' };
  wsPL.getCell(`C${netProfitRow}`).value = { formula: `C${pbtRow}-C${taxRow}`, result: plStatement.netProfitAfterTax };
  wsPL.getCell(`C${netProfitRow}`).font = { name: 'Segoe UI', size: 10.5, bold: true, color: { argb: '166534' } };
  wsPL.getCell(`C${netProfitRow}`).numFmt = NUMBER_FORMAT;
  wsPL.getCell(`D${netProfitRow}`).value = 0;
  wsPL.getCell(`D${netProfitRow}`).numFmt = NUMBER_FORMAT;
  for (let c = 1; c <= 4; c++) {
    wsPL.getCell(netProfitRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    wsPL.getCell(netProfitRow, c).border = BORDERS.totalRow;
  }
  plRow += 2;

  // Signatures at bottom of P&L
  const plSigRow = plRow;
  wsPL.getCell(`A${plSigRow}`).value = 'For and on behalf of: ' + entity.name;
  wsPL.getCell(`A${plSigRow}`).font = { bold: true, name: 'Segoe UI', size: 10 };
  wsPL.getCell(`C${plSigRow}`).value = 'In terms of our audit report of even date attached:';
  wsPL.getCell(`C${plSigRow}`).font = { bold: true, name: 'Segoe UI', size: 10 };

  wsPL.getCell(`A${plSigRow + 2}`).value = entity.proprietorOrPartnerNames?.[0] || 'Proprietor / Authorized Partner';
  wsPL.getCell(`A${plSigRow + 2}`).font = { name: 'Segoe UI', size: 9.5, bold: true };
  wsPL.getCell(`A${plSigRow + 3}`).value = `Proprietor / Partner\nPlace: ${entity.placeOfSigning || 'Navi Mumbai'} | Date: ${entity.dateOfSigning || entity.balanceSheetDate}`;
  wsPL.getCell(`A${plSigRow + 3}`).font = { name: 'Segoe UI', size: 9, color: { argb: '64748B' } };

  wsPL.getCell(`C${plSigRow + 2}`).value = `For ${entity.auditorName || 'Chartered Accountants'}\nChartered Accountants | FRN: ${entity.firmRegistrationNo || '124982W'}`;
  wsPL.getCell(`C${plSigRow + 2}`).font = { name: 'Segoe UI', size: 9.5, bold: true };
  wsPL.getCell(`C${plSigRow + 3}`).value = `UDIN: ${entity.udin || '25512948BGXYZW1234'} | M.No: ${entity.membershipNumber || '512948'}\nPlace: ${entity.placeOfSigning || 'Navi Mumbai'} | Date: ${entity.dateOfSigning || entity.balanceSheetDate}`;
  wsPL.getCell(`C${plSigRow + 3}`).font = { name: 'Segoe UI', size: 9, color: { argb: '166534' }, bold: true };

  wsPL.columns = [
    { width: 56 },
    { width: 14 },
    { width: 26 },
    { width: 26 },
  ];

  // =========================================================================
  // SHEET 4: CONSOLIDATED MASTER SCHEDULES SHEET (SCHEDULES 1 TO 14)
  // =========================================================================
  const wsMasterSched = workbook.addWorksheet('SCHEDULES (1-14)', { views: [{ showGridLines: true }] });

  wsMasterSched.mergeCells('A1:E1');
  const msTitle = wsMasterSched.getCell('A1');
  msTitle.value = `${entity.name.toUpperCase()} — CONSOLIDATED SCHEDULES & ANNEXURES`;
  msTitle.font = { name: 'Segoe UI', size: 13, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  msTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  msTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsMasterSched.getRow(1).height = 26;

  let msRow = 3;

  activeHeads.forEach(head => {
    const scheduleData = schedules.find(s => s.headConfig.code === head.code);
    const matchingLedgers = scheduleData ? scheduleData.ledgers : [];

    // Schedule Header
    wsMasterSched.mergeCells(`A${msRow}:E${msRow}`);
    const schHeader = wsMasterSched.getCell(`A${msRow}`);
    schHeader.value = `SCHEDULE ${head.scheduleNo}: ${head.subHead.toUpperCase()} [${head.code}]`;
    schHeader.font = { name: 'Segoe UI', size: 11, bold: true, color: { argb: 'FFFFFF' } };
    schHeader.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    for (let c = 1; c <= 5; c++) wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
    wsMasterSched.getRow(msRow).height = 22;
    msRow++;

    // Table Header
    const headers = ['Sr No.', 'Particulars / Account Name', 'ERP Group Classification', 'Nature', `Amount as on ${entity.balanceSheetDate} (₹)`];
    wsMasterSched.getRow(msRow).values = headers;
    headers.forEach((_, i) => {
      const cell = wsMasterSched.getCell(msRow, i + 1);
      cell.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: '334155' } };
      cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F1F5F9' } };
      cell.alignment = { vertical: 'middle', horizontal: i === 4 ? 'right' : i === 0 ? 'center' : 'left' };
      cell.border = BORDERS.thin;
    });
    wsMasterSched.getRow(msRow).height = 20;
    msRow++;

    const startItemsRow = msRow;
    if (head.isSpecialSchedule === 'CAPITAL' || head.code === 'L01') {
      matchingLedgers.forEach(l => {
        const isDrawing = l.ledgerName.toLowerCase().includes('drawing') || l.debit > l.credit;
        const amt = Math.abs(l.debit - l.credit);
        wsMasterSched.getCell(`A${msRow}`).value = msRow - startItemsRow + 1;
        wsMasterSched.getCell(`B${msRow}`).value = isDrawing ? `Less: ${l.ledgerName} (Drawings)` : `Opening Balance: ${l.ledgerName}`;
        wsMasterSched.getCell(`C${msRow}`).value = l.originalGroup;
        wsMasterSched.getCell(`D${msRow}`).value = isDrawing ? 'Debit (Drawing)' : 'Credit (Equity)';
        wsMasterSched.getCell(`E${msRow}`).value = isDrawing ? -amt : amt;
        wsMasterSched.getCell(`E${msRow}`).numFmt = NUMBER_FORMAT;
        for (let c = 1; c <= 5; c++) wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
        msRow++;
      });

      // Add Net Profit
      wsMasterSched.getCell(`A${msRow}`).value = msRow - startItemsRow + 1;
      wsMasterSched.getCell(`B${msRow}`).value = 'Add: Net Profit for the year as per Statement of Profit & Loss';
      wsMasterSched.getCell(`B${msRow}`).font = { bold: true, color: { argb: '166534' } };
      wsMasterSched.getCell(`C${msRow}`).value = 'Statement of Profit & Loss';
      wsMasterSched.getCell(`D${msRow}`).value = 'P&L Transfer';
      wsMasterSched.getCell(`E${msRow}`).value = plStatement.netProfitAfterTax;
      wsMasterSched.getCell(`E${msRow}`).font = { bold: true, color: { argb: '166534' } };
      wsMasterSched.getCell(`E${msRow}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 5; c++) wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
      msRow++;
    } else if (matchingLedgers.length === 0) {
      const closingStockAdj = (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03')
        ? adjustments.find(a => a.type === 'CLOSING_STOCK' || a.debitHead === head.code)
        : undefined;
      const isStockAdj = closingStockAdj && closingStockAdj.amount > 0;

      wsMasterSched.getCell(`A${msRow}`).value = 1;
      wsMasterSched.getCell(`B${msRow}`).value = isStockAdj ? 'Closing Stock of Inventory (as valued & certified by management)' : 'Nil Balance / Direct Adjustment Entry';
      wsMasterSched.getCell(`C${msRow}`).value = isStockAdj ? 'Management Valuation' : '-';
      wsMasterSched.getCell(`D${msRow}`).value = head.nature;
      wsMasterSched.getCell(`E${msRow}`).value = scheduleData?.totalAmount || 0;
      wsMasterSched.getCell(`E${msRow}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 5; c++) wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
      msRow++;
    } else {
      matchingLedgers.forEach((l, idx) => {
        const amt = head.nature === 'Liability'
          ? ((l.credit || 0) - (l.debit || 0))
          : ((l.debit || 0) - (l.credit || 0));
        wsMasterSched.getCell(`A${msRow}`).value = idx + 1;
        wsMasterSched.getCell(`B${msRow}`).value = l.ledgerName;
        wsMasterSched.getCell(`C${msRow}`).value = l.originalGroup;
        wsMasterSched.getCell(`D${msRow}`).value = l.debit >= l.credit ? 'Debit' : 'Credit';
        wsMasterSched.getCell(`E${msRow}`).value = amt;
        wsMasterSched.getCell(`E${msRow}`).numFmt = NUMBER_FORMAT;
        for (let c = 1; c <= 5; c++) {
          wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
          if (idx % 2 === 1) {
            wsMasterSched.getCell(msRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
          }
        }
        msRow++;
      });

      const closingStockAdj = (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03')
        ? adjustments.find(a => a.type === 'CLOSING_STOCK' || a.debitHead === head.code)
        : undefined;
      if (closingStockAdj && closingStockAdj.amount > 0) {
        wsMasterSched.getCell(`A${msRow}`).value = matchingLedgers.length + 1;
        wsMasterSched.getCell(`B${msRow}`).value = 'Closing Stock of Inventory (as valued & certified by management)';
        wsMasterSched.getCell(`C${msRow}`).value = 'Management Valuation';
        wsMasterSched.getCell(`D${msRow}`).value = 'Debit';
        wsMasterSched.getCell(`E${msRow}`).value = closingStockAdj.amount;
        wsMasterSched.getCell(`E${msRow}`).numFmt = NUMBER_FORMAT;
        for (let c = 1; c <= 5; c++) wsMasterSched.getCell(msRow, c).border = BORDERS.thin;
        msRow++;
      }
    }

    // Schedule Total Row
    const totRow = msRow;
    wsMasterSched.mergeCells(`A${totRow}:D${totRow}`);
    wsMasterSched.getCell(`A${totRow}`).value = `TOTAL ${head.subHead.toUpperCase()}`;
    wsMasterSched.getCell(`A${totRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
    wsMasterSched.getCell(`E${totRow}`).value = { formula: `SUM(E${startItemsRow}:E${totRow - 1})`, result: scheduleData?.totalAmount ?? 0 };
    wsMasterSched.getCell(`E${totRow}`).font = { name: 'Segoe UI', size: 10, bold: true };
    wsMasterSched.getCell(`E${totRow}`).numFmt = NUMBER_FORMAT;
    for (let c = 1; c <= 5; c++) {
      wsMasterSched.getCell(totRow, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
      wsMasterSched.getCell(totRow, c).border = BORDERS.totalRow;
    }
    msRow += 3;
  });

  wsMasterSched.columns = [
    { width: 8 },
    { width: 44 },
    { width: 30 },
    { width: 18 },
    { width: 24 },
  ];

  // =========================================================================
  // SUBSEQUENT SHEETS: INDIVIDUAL SCHEDULES (ONE SEPARATE WORKSHEET EACH)
  // =========================================================================
  activeHeads.forEach(head => {
    const rawSheetName = `Sch ${head.scheduleNo} - ${head.subHead}`;
    const sheetName = sanitizeSheetName(rawSheetName);
    const wsSched = workbook.addWorksheet(sheetName, { views: [{ showGridLines: true }] });

    const scheduleData = schedules.find(s => s.headConfig.code === head.code);
    const matchingLedgers = scheduleData ? scheduleData.ledgers : [];

    // Header Banner
    wsSched.mergeCells('A1:D1');
    const schHeader = wsSched.getCell('A1');
    schHeader.value = `${entity.name.toUpperCase()} — SCHEDULE ${head.scheduleNo}`;
    schHeader.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    schHeader.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
    schHeader.alignment = { vertical: 'middle', horizontal: 'center' };
    wsSched.getRow(1).height = 26;

    wsSched.mergeCells('A2:D2');
    const schSubHeader = wsSched.getCell('A2');
    schSubHeader.value = `${head.subHead.toUpperCase()} | ANNEXED TO AND FORMING PART OF BALANCE SHEET`;
    schSubHeader.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '0F172A' } };
    schSubHeader.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E2E8F0' } };
    schSubHeader.alignment = { vertical: 'middle', horizontal: 'center' };
    wsSched.getRow(2).height = 20;

    // Check Special Schedule 1: CAPITAL ACCOUNT
    if (head.isSpecialSchedule === 'CAPITAL' || head.code === 'L01') {
      const capitalHeaders = ['Sr No.', 'Particulars / Partner Details', 'Details (₹)', `As at ${entity.balanceSheetDate} (₹)`];
      wsSched.getRow(4).values = capitalHeaders;
      wsSched.getRow(4).height = 22;
      capitalHeaders.forEach((_, i) => {
        const cell = wsSched.getCell(4, i + 1);
        cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
        cell.alignment = { vertical: 'middle', horizontal: i >= 2 ? 'right' : 'left' };
        cell.border = BORDERS.thin;
      });

      let r = 5;
      matchingLedgers.forEach(l => {
        const isDrawing = l.ledgerName.toLowerCase().includes('drawing') || l.debit > l.credit;
        const amt = Math.abs(l.debit - l.credit);
        wsSched.getCell(`A${r}`).value = r - 4;
        wsSched.getCell(`B${r}`).value = isDrawing ? `Less: ${l.ledgerName} (Drawings)` : l.ledgerName;
        wsSched.getCell(`C${r}`).value = isDrawing ? -amt : amt;
        wsSched.getCell(`C${r}`).numFmt = NUMBER_FORMAT;
        wsSched.getCell(`D${r}`).value = isDrawing ? -amt : amt;
        wsSched.getCell(`D${r}`).numFmt = NUMBER_FORMAT;
        for (let c = 1; c <= 4; c++) wsSched.getCell(r, c).border = BORDERS.thin;
        r++;
      });

      // Add Net Profit linked to P&L sheet
      wsSched.getCell(`A${r}`).value = r - 4;
      wsSched.getCell(`B${r}`).value = `Add: Net Profit for the year as per P&L Statement`;
      wsSched.getCell(`B${r}`).font = { bold: true, color: { argb: '166534' } };
      wsSched.getCell(`C${r}`).value = { formula: `'PROFIT & LOSS'!C${netProfitRow}`, result: plStatement.netProfitAfterTax };
      wsSched.getCell(`C${r}`).numFmt = NUMBER_FORMAT;
      wsSched.getCell(`D${r}`).value = { formula: `C${r}`, result: plStatement.netProfitAfterTax };
      wsSched.getCell(`D${r}`).font = { bold: true, color: { argb: '166534' } };
      wsSched.getCell(`D${r}`).numFmt = NUMBER_FORMAT;
      for (let c = 1; c <= 4; c++) wsSched.getCell(r, c).border = BORDERS.thin;
      r++;

      // Total Row
      const totRow = r;
      wsSched.getCell(`B${totRow}`).value = `TOTAL ${head.subHead.toUpperCase()}`;
      wsSched.getCell(`D${totRow}`).value = { formula: `SUM(D5:D${totRow - 1})`, result: scheduleData?.totalAmount ?? 0 };
      for (let c = 1; c <= 4; c++) {
        const cell = wsSched.getCell(totRow, c);
        cell.font = { bold: true, name: 'Segoe UI', size: 10 };
        cell.border = BORDERS.totalRow;
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
        if (c === 4) cell.numFmt = NUMBER_FORMAT;
      }

      wsSched.columns = [{ width: 8 }, { width: 48 }, { width: 20 }, { width: 22 }];
    }
    // Check Special Schedule 8: PROPERTY, PLANT & EQUIPMENT (FIXED ASSETS BLOCK)
    else if (head.isSpecialSchedule === 'FIXED_ASSETS' || head.code === 'A01') {
      // Row 4: Multi-cell Category Headings
      wsSched.mergeCells('A4:A5');
      const cellA4 = wsSched.getCell('A4');
      cellA4.value = 'Particulars of Assets';
      cellA4.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: COLORS.HEADER_TEXT } };
      cellA4.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '1E293B' } };
      cellA4.alignment = { vertical: 'middle', horizontal: 'center' };

      wsSched.mergeCells('B4:F4');
      const cellB4 = wsSched.getCell('B4');
      cellB4.value = 'GROSS CARRYING AMOUNT / GROSS BLOCK (₹)';
      cellB4.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: COLORS.HEADER_TEXT } };
      cellB4.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '1E3A8A' } };
      cellB4.alignment = { vertical: 'middle', horizontal: 'center' };

      wsSched.mergeCells('G4:J4');
      const cellG4 = wsSched.getCell('G4');
      cellG4.value = 'ACCUMULATED DEPRECIATION & AMORTIZATION (₹)';
      cellG4.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: COLORS.HEADER_TEXT } };
      cellG4.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '854D0E' } };
      cellG4.alignment = { vertical: 'middle', horizontal: 'center' };

      wsSched.mergeCells('K4:L4');
      const cellK4 = wsSched.getCell('K4');
      cellK4.value = 'NET CARRYING AMOUNT (₹)';
      cellK4.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: COLORS.HEADER_TEXT } };
      cellK4.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '14532D' } };
      cellK4.alignment = { vertical: 'middle', horizontal: 'center' };

      wsSched.getRow(4).height = 22;

      // Row 5: Column Sub-headings
      const subHeaders = [
        '',
        `As at 01-04-${parseInt(entity.financialYear.slice(0, 4)) || 2024}`,
        'Additions (> 180 Days)',
        'Additions (< 180 Days)',
        'Deductions / Adj.',
        `Total as at ${entity.balanceSheetDate}`,
        `Up to 01-04-${parseInt(entity.financialYear.slice(0, 4)) || 2024}`,
        'For the Year (P&L)',
        'Deductions / Adj.',
        `Total up to ${entity.balanceSheetDate}`,
        `As at ${entity.balanceSheetDate}`,
        `As at ${entity.previousYearDate || '31-03-2024'}`,
      ];

      subHeaders.forEach((val, i) => {
        if (i === 0) return;
        const cell = wsSched.getCell(5, i + 1);
        cell.value = val;
        cell.font = { name: 'Segoe UI', size: 8.5, bold: true, color: { argb: '1E293B' } };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F1F5F9' } };
        cell.alignment = { vertical: 'middle', horizontal: 'center', wrapText: true };
        cell.border = BORDERS.thin;
      });

      for (let c = 1; c <= 12; c++) {
        wsSched.getCell(4, c).border = BORDERS.thin;
        wsSched.getCell(5, c).border = BORDERS.thin;
      }
      wsSched.getRow(5).height = 26;

      let r = 6;
      const faDetails = scheduleData?.fixedAssetDetails || [];

      if (faDetails.length > 0) {
        faDetails.forEach((asset, idx) => {
          const netClosingGross = (asset.openingGrossBlock || 0) + (asset.additionsMoreThan180Days || 0) + (asset.additionsLessThan180Days || 0) - (asset.deductionsGrossBlock || 0);
          const netClosingDepr = (asset.openingDepreciation || 0) + (asset.currentYearDepreciation || 0) - (asset.depreciationOnDeletions || 0);
          const netCarryingAmount = netClosingGross - netClosingDepr;
          const netPrevCarrying = (asset.openingGrossBlock || 0) - (asset.openingDepreciation || 0);

          wsSched.getCell(`A${r}`).value = asset.assetName;
          wsSched.getCell(`B${r}`).value = asset.openingGrossBlock;
          wsSched.getCell(`C${r}`).value = asset.additionsMoreThan180Days || 0;
          wsSched.getCell(`D${r}`).value = asset.additionsLessThan180Days || 0;
          wsSched.getCell(`E${r}`).value = asset.deductionsGrossBlock || 0;
          wsSched.getCell(`F${r}`).value = { formula: `B${r}+C${r}+D${r}-E${r}`, result: netClosingGross };
          wsSched.getCell(`G${r}`).value = asset.openingDepreciation || 0;
          wsSched.getCell(`H${r}`).value = asset.currentYearDepreciation || 0;
          wsSched.getCell(`I${r}`).value = asset.depreciationOnDeletions || 0;
          wsSched.getCell(`J${r}`).value = { formula: `G${r}+H${r}-I${r}`, result: netClosingDepr };
          wsSched.getCell(`K${r}`).value = { formula: `F${r}-J${r}`, result: netCarryingAmount };
          wsSched.getCell(`L${r}`).value = { formula: `B${r}-G${r}`, result: netPrevCarrying };

          for (let c = 1; c <= 12; c++) {
            const cell = wsSched.getCell(r, c);
            cell.border = BORDERS.thin;
            cell.font = { name: 'Segoe UI', size: 9 };
            if (c >= 2) cell.numFmt = NUMBER_FORMAT;
            if (idx % 2 === 1) {
              cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
            }
          }
          r++;
        });
      } else {
        // Fallback to ledgers if fixedAssetDetails empty
        const assetLedgers = matchingLedgers.filter(l => !l.ledgerName.toLowerCase().includes('depreciation'));
        const deprLedger = matchingLedgers.find(l => l.ledgerName.toLowerCase().includes('depreciation'));
        const totalDepr = deprLedger ? Math.abs(deprLedger.debit - deprLedger.credit) : 0;
        const totalGross = assetLedgers.reduce((acc, l) => acc + Math.abs(l.debit - l.credit), 0);

        assetLedgers.forEach((l, idx) => {
          const grossAmt = Math.abs(l.debit - l.credit);
          const allocatedDepr = totalGross > 0 ? (grossAmt / totalGross) * totalDepr : 0;

          wsSched.getCell(`A${r}`).value = l.ledgerName;
          wsSched.getCell(`B${r}`).value = grossAmt;
          wsSched.getCell(`C${r}`).value = 0;
          wsSched.getCell(`D${r}`).value = 0;
          wsSched.getCell(`E${r}`).value = 0;
          wsSched.getCell(`F${r}`).value = { formula: `B${r}+C${r}+D${r}-E${r}`, result: grossAmt };
          wsSched.getCell(`G${r}`).value = allocatedDepr;
          wsSched.getCell(`H${r}`).value = 0;
          wsSched.getCell(`I${r}`).value = 0;
          wsSched.getCell(`J${r}`).value = { formula: `G${r}+H${r}-I${r}`, result: allocatedDepr };
          wsSched.getCell(`K${r}`).value = { formula: `F${r}-J${r}`, result: grossAmt - allocatedDepr };
          wsSched.getCell(`L${r}`).value = { formula: `B${r}-G${r}`, result: grossAmt - allocatedDepr };

          for (let c = 1; c <= 12; c++) {
            const cell = wsSched.getCell(r, c);
            cell.border = BORDERS.thin;
            cell.font = { name: 'Segoe UI', size: 9 };
            if (c >= 2) cell.numFmt = NUMBER_FORMAT;
            if (idx % 2 === 1) {
              cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
            }
          }
          r++;
        });
      }

      // Fixed Asset Total Row
      const totRow = r;
      wsSched.getCell(`A${totRow}`).value = 'TOTAL PROPERTY, PLANT & EQUIPMENT';
      wsSched.getCell(`B${totRow}`).value = { formula: `SUM(B6:B${totRow - 1})` };
      wsSched.getCell(`C${totRow}`).value = { formula: `SUM(C6:C${totRow - 1})` };
      wsSched.getCell(`D${totRow}`).value = { formula: `SUM(D6:D${totRow - 1})` };
      wsSched.getCell(`E${totRow}`).value = { formula: `SUM(E6:E${totRow - 1})` };
      wsSched.getCell(`F${totRow}`).value = { formula: `SUM(F6:F${totRow - 1})` };
      wsSched.getCell(`G${totRow}`).value = { formula: `SUM(G6:G${totRow - 1})` };
      wsSched.getCell(`H${totRow}`).value = { formula: `SUM(H6:H${totRow - 1})` };
      wsSched.getCell(`I${totRow}`).value = { formula: `SUM(I6:I${totRow - 1})` };
      wsSched.getCell(`J${totRow}`).value = { formula: `SUM(J6:J${totRow - 1})` };
      wsSched.getCell(`K${totRow}`).value = { formula: `SUM(K6:K${totRow - 1})`, result: scheduleData?.totalAmount ?? 0 };
      wsSched.getCell(`L${totRow}`).value = { formula: `SUM(L6:L${totRow - 1})` };

      for (let c = 1; c <= 12; c++) {
        const cell = wsSched.getCell(totRow, c);
        cell.font = { bold: true, name: 'Segoe UI', size: 9.5 };
        cell.border = BORDERS.totalRow;
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
        if (c >= 2) cell.numFmt = NUMBER_FORMAT;
      }
      wsSched.getRow(totRow).height = 22;

      // Statutory Footnote
      r = totRow + 2;
      wsSched.mergeCells(`A${r}:L${r}`);
      const fnCell = wsSched.getCell(`A${r}`);
      fnCell.value = 'Note: Property, Plant and Equipment are stated at cost of acquisition less accumulated depreciation and impairment losses, if any, in compliance with Accounting Standard (AS) 10 / ICAI Technical Guide for Non-Corporate Entities. Depreciation is provided under WDV / SLM as applicable under Income Tax Act, 1961.';
      fnCell.font = { name: 'Segoe UI', size: 8.5, italic: true, color: { argb: '64748B' } };
      fnCell.alignment = { wrapText: true };

      wsSched.columns = [
        { width: 34 },
        { width: 18 },
        { width: 17 },
        { width: 17 },
        { width: 17 },
        { width: 20 },
        { width: 18 },
        { width: 18 },
        { width: 17 },
        { width: 20 },
        { width: 22 },
        { width: 22 },
      ];
    }
    // STANDARD SCHEDULE
    else {
      const stdHeaders = ['Sr No.', 'Particulars / Ledger Account', 'ERP Group', `Amount as on ${entity.balanceSheetDate} (₹)`];
      wsSched.getRow(4).values = stdHeaders;
      wsSched.getRow(4).height = 22;
      stdHeaders.forEach((_, i) => {
        const cell = wsSched.getCell(4, i + 1);
        cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
        cell.alignment = { vertical: 'middle', horizontal: i === 3 ? 'right' : 'left' };
        cell.border = BORDERS.thin;
      });

      let r = 5;
      if (matchingLedgers.length === 0) {
        const closingStockAdj = (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03')
          ? adjustments.find(a => a.type === 'CLOSING_STOCK' || a.debitHead === head.code)
          : undefined;
        const isStockAdj = closingStockAdj && closingStockAdj.amount > 0;

        wsSched.getCell(`A${r}`).value = 1;
        wsSched.getCell(`B${r}`).value = isStockAdj ? 'Closing Stock of Inventory (as valued & certified by management)' : 'No individual ledger items (Nil Balance / Direct Entry)';
        wsSched.getCell(`C${r}`).value = isStockAdj ? 'Management Valuation' : '-';
        wsSched.getCell(`D${r}`).value = scheduleData?.totalAmount || 0;
        wsSched.getCell(`D${r}`).numFmt = NUMBER_FORMAT;
        for (let c = 1; c <= 4; c++) wsSched.getCell(r, c).border = BORDERS.thin;
        r++;
      } else {
        matchingLedgers.forEach((l, idx) => {
          const amt = head.nature === 'Liability'
            ? ((l.credit || 0) - (l.debit || 0))
            : ((l.debit || 0) - (l.credit || 0));
          wsSched.getCell(`A${r}`).value = idx + 1;
          wsSched.getCell(`B${r}`).value = l.ledgerName;
          wsSched.getCell(`C${r}`).value = l.originalGroup;
          wsSched.getCell(`D${r}`).value = amt;
          wsSched.getCell(`D${r}`).numFmt = NUMBER_FORMAT;

          for (let c = 1; c <= 4; c++) {
            wsSched.getCell(r, c).border = BORDERS.thin;
            wsSched.getCell(r, c).font = { name: 'Segoe UI', size: 10 };
            if (idx % 2 === 1) {
              wsSched.getCell(r, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
            }
          }
          r++;
        });

        const closingStockAdj = (head.isSpecialSchedule === 'INVENTORIES' || head.code === 'A03')
          ? adjustments.find(a => a.type === 'CLOSING_STOCK' || a.debitHead === head.code)
          : undefined;
        if (closingStockAdj && closingStockAdj.amount > 0) {
          wsSched.getCell(`A${r}`).value = matchingLedgers.length + 1;
          wsSched.getCell(`B${r}`).value = 'Closing Stock of Inventory (as valued & certified by management)';
          wsSched.getCell(`C${r}`).value = 'Management Valuation';
          wsSched.getCell(`D${r}`).value = closingStockAdj.amount;
          wsSched.getCell(`D${r}`).numFmt = NUMBER_FORMAT;
          for (let c = 1; c <= 4; c++) wsSched.getCell(r, c).border = BORDERS.thin;
          r++;
        }
      }

      // Schedule Total Row
      const totRow = r;
      wsSched.getCell(`B${totRow}`).value = `TOTAL ${head.subHead.toUpperCase()}`;
      wsSched.getCell(`D${totRow}`).value = { formula: `SUM(D5:D${totRow - 1})`, result: scheduleData?.totalAmount ?? 0 };

      for (let c = 1; c <= 4; c++) {
        const cell = wsSched.getCell(totRow, c);
        cell.font = { bold: true, name: 'Segoe UI', size: 10 };
        cell.border = BORDERS.totalRow;
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
        if (c === 4) cell.numFmt = NUMBER_FORMAT;
      }

      wsSched.columns = [
        { width: 8 },
        { width: 44 },
        { width: 28 },
        { width: 24 },
      ];
    }
  });

  // =========================================================================
  // SHEET: DEPRECIATION SCHEDULE (PROPERTY, PLANT & EQUIPMENT)
  // =========================================================================
  const wsDepr = workbook.addWorksheet('DEPRECIATION SCHEDULE', { views: [{ showGridLines: true }] });

  wsDepr.mergeCells('A1:J1');
  const deprTitle = wsDepr.getCell('A1');
  deprTitle.value = `${entity.name.toUpperCase()} — DEPRECIATION SCHEDULE (FIXED ASSETS / PPE)`;
  deprTitle.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  deprTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  deprTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsDepr.getRow(1).height = 28;

  wsDepr.mergeCells('A2:J2');
  const deprSubTitle = wsDepr.getCell('A2');
  deprSubTitle.value = `Schedule of Fixed Assets as per Income Tax Act & AS 10 (Property, Plant & Equipment) | F.Y. ${entity.financialYear} | As on ${entity.balanceSheetDate}`;
  deprSubTitle.font = { name: 'Segoe UI', size: 9.5, italic: true, color: { argb: '334155' } };
  deprSubTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F1F5F9' } };
  deprSubTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsDepr.getRow(2).height = 20;

  const deprHeaders = [
    'S.No',
    'Particulars / Asset Description',
    'Category / Block',
    'Gross Block (₹)',
    'Rate of Depr (%)',
    'Accumulated Depr (₹)',
    'Depreciation of the Year (₹)',
    'Closing Value (₹)',
    'Closing of Previous Year (₹)',
    'Remarks / Notes',
  ];

  const deprHeaderRow = wsDepr.getRow(4);
  deprHeaders.forEach((h, idx) => {
    const cell = deprHeaderRow.getCell(idx + 1);
    cell.value = h;
    cell.font = { name: 'Segoe UI', size: 9.5, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '1E293B' } };
    cell.alignment = {
      vertical: 'middle',
      horizontal: idx >= 3 && idx <= 8 ? 'right' : idx === 0 || idx === 4 ? 'center' : 'left',
      wrapText: true,
    };
    cell.border = BORDERS.thin;
  });
  deprHeaderRow.height = 24;

  const activeDeprAssets = depreciationAssets.length > 0 ? depreciationAssets : DEFAULT_DEPRECIATION_ASSETS;

  let deprR = 5;
  activeDeprAssets.forEach((item, idx) => {
    const row = wsDepr.getRow(deprR);
    row.getCell(1).value = idx + 1;
    row.getCell(2).value = item.assetName;
    row.getCell(3).value = item.category || 'Fixed Assets';
    row.getCell(4).value = item.grossBlock;
    row.getCell(5).value = item.depreciationRate ? item.depreciationRate / 100 : 0;
    row.getCell(6).value = item.accumulatedDepreciation;
    row.getCell(7).value = item.depreciationForTheYear;
    // Formula for Closing Value: Gross Block - Accum Depr - Depr of Year
    row.getCell(8).value = { formula: `D${deprR}-F${deprR}-G${deprR}`, result: item.closingValue };
    // Formula for Closing of Previous Year: Gross Block - Accum Depr
    row.getCell(9).value = { formula: `D${deprR}-F${deprR}`, result: item.previousYearClosing };
    row.getCell(10).value = item.notes || '';

    row.getCell(1).alignment = { horizontal: 'center' };
    row.getCell(2).font = { bold: true };
    row.getCell(5).numFmt = '0.00%';
    row.getCell(5).alignment = { horizontal: 'center' };

    [4, 6, 7, 8, 9].forEach(colIdx => {
      const c = row.getCell(colIdx);
      c.numFmt = NUMBER_FORMAT;
      c.alignment = { horizontal: 'right' };
    });

    for (let c = 1; c <= 10; c++) {
      const cell = row.getCell(c);
      cell.border = BORDERS.thin;
      if (deprR % 2 === 1) {
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
      }
    }
    deprR++;
  });

  // Totals Row for Depreciation Schedule
  const deprTotalRow = wsDepr.getRow(deprR);
  deprTotalRow.getCell(2).value = 'TOTAL PROPERTY, PLANT & EQUIPMENT';
  deprTotalRow.getCell(2).font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '0F172A' } };

  const totGross = activeDeprAssets.reduce((sum, i) => sum + i.grossBlock, 0);
  const totAccum = activeDeprAssets.reduce((sum, i) => sum + i.accumulatedDepreciation, 0);
  const totDepr = activeDeprAssets.reduce((sum, i) => sum + i.depreciationForTheYear, 0);
  const totClosing = activeDeprAssets.reduce((sum, i) => sum + i.closingValue, 0);
  const totPrevClosing = activeDeprAssets.reduce((sum, i) => sum + i.previousYearClosing, 0);

  deprTotalRow.getCell(4).value = { formula: `SUM(D5:D${deprR - 1})`, result: totGross };
  deprTotalRow.getCell(6).value = { formula: `SUM(F5:F${deprR - 1})`, result: totAccum };
  deprTotalRow.getCell(7).value = { formula: `SUM(G5:G${deprR - 1})`, result: totDepr };
  deprTotalRow.getCell(8).value = { formula: `SUM(H5:H${deprR - 1})`, result: totClosing };
  deprTotalRow.getCell(9).value = { formula: `SUM(I5:I${deprR - 1})`, result: totPrevClosing };

  [4, 6, 7, 8, 9].forEach(colIdx => {
    const c = deprTotalRow.getCell(colIdx);
    c.numFmt = NUMBER_FORMAT;
    c.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '0F172A' } };
    c.alignment = { horizontal: 'right' };
  });

  for (let c = 1; c <= 10; c++) {
    const cell = deprTotalRow.getCell(c);
    cell.border = BORDERS.totalRow;
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
  }
  deprTotalRow.height = 24;

  wsDepr.columns = [
    { width: 6 },  // S.No
    { width: 38 }, // Particulars
    { width: 22 }, // Category
    { width: 20 }, // Gross Block
    { width: 16 }, // Rate
    { width: 22 }, // Accumulated Depr
    { width: 22 }, // Depreciation of Year
    { width: 22 }, // Closing Value
    { width: 22 }, // Closing of Previous Year
    { width: 30 }, // Remarks
  ];

  // =========================================================================
  // SHEET: NOTES TO ACCOUNTS & SIGNIFICANT ACCOUNTING POLICIES (NOTE 15)
  // =========================================================================
  const wsNotes = workbook.addWorksheet('NOTES TO ACCOUNTS', { views: [{ showGridLines: true }] });

  wsNotes.mergeCells('A1:C1');
  const noteTitle = wsNotes.getCell('A1');
  noteTitle.value = `${entity.name.toUpperCase()} — SCHEDULE 15: NOTES TO ACCOUNTS`;
  noteTitle.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  noteTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  noteTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsNotes.getRow(1).height = 28;

  wsNotes.mergeCells('A2:C2');
  const noteSubTitle = wsNotes.getCell('A2');
  noteSubTitle.value = `Notes Forming Integral Part of Financial Statements as per ICAI Guidelines for Non-Corporate Entities | FY ${entity.financialYear}`;
  noteSubTitle.font = { name: 'Segoe UI', size: 9.5, italic: true, color: { argb: '334155' } };
  noteSubTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'F1F5F9' } };
  noteSubTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsNotes.getRow(2).height = 20;

  const activeNotes = notesToAccounts.length > 0 
    ? notesToAccounts.filter(n => n.isActive)
    : DEFAULT_STANDARD_NOTES.filter(n => n.isActive);

  let nRow = 4;
  activeNotes.forEach((n, idx) => {
    // Note header bar
    wsNotes.mergeCells(`A${nRow}:C${nRow}`);
    const cellH = wsNotes.getCell(`A${nRow}`);
    cellH.value = `NOTE ${n.noteNumber || idx + 1}: ${n.title.toUpperCase()}`;
    cellH.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: '1E3A8A' } };
    cellH.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'E0E7FF' } };
    cellH.border = BORDERS.thin;
    wsNotes.getRow(nRow).height = 22;
    nRow++;

    // Note content
    wsNotes.mergeCells(`A${nRow}:C${nRow}`);
    const cellC = wsNotes.getCell(`A${nRow}`);
    cellC.value = n.content;
    cellC.font = { name: 'Segoe UI', size: 9.5 };
    cellC.alignment = { wrapText: true, vertical: 'top' };
    cellC.border = BORDERS.thin;

    // Estimate row height based on text length and line breaks
    const lineCount = (n.content.match(/\n/g) || []).length + Math.ceil(n.content.length / 110);
    wsNotes.getRow(nRow).height = Math.max(32, Math.min(300, lineCount * 17));
    nRow += 2;
  });

  wsNotes.columns = [{ width: 36 }, { width: 44 }, { width: 36 }];

  // =========================================================================
  // SHEET: TRIAL BALANCE
  // =========================================================================
  const wsTB = workbook.addWorksheet('TRIAL BALANCE', { views: [{ showGridLines: true }] });

  wsTB.mergeCells('A1:F1');
  const tbTitle = wsTB.getCell('A1');
  tbTitle.value = `${entity.name.toUpperCase()} — TRIAL BALANCE AS ON ${entity.balanceSheetDate.toUpperCase()}`;
  tbTitle.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  tbTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  tbTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsTB.getRow(1).height = 28;

  const tbHeaders = ['Particulars / Ledger Name', 'ERP Group', 'Debit (₹)', 'Credit (₹)', 'Net Balance (₹)', 'Classification Target'];
  wsTB.getRow(3).values = tbHeaders;
  wsTB.getRow(3).height = 22;
  tbHeaders.forEach((_, i) => {
    const cell = wsTB.getCell(3, i + 1);
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    cell.alignment = { vertical: 'middle', horizontal: i >= 2 && i <= 4 ? 'right' : 'left' };
    cell.border = BORDERS.thin;
  });

  ledgers.forEach((l, idx) => {
    const rowNum = 4 + idx;
    wsTB.getCell(`A${rowNum}`).value = l.ledgerName;
    wsTB.getCell(`B${rowNum}`).value = l.originalGroup;
    wsTB.getCell(`C${rowNum}`).value = l.debit;
    wsTB.getCell(`D${rowNum}`).value = l.credit;
    wsTB.getCell(`E${rowNum}`).value = { formula: `C${rowNum}-D${rowNum}` };
    wsTB.getCell(`F${rowNum}`).value = l.targetType === 'BALANCE_SHEET' ? `BS: ${l.subHead || l.mainHead}` : `P&L: ${l.plCategory || 'Operating'}`;

    for (let c = 1; c <= 6; c++) {
      const cell = wsTB.getCell(rowNum, c);
      cell.border = BORDERS.thin;
      cell.font = { name: 'Segoe UI', size: 9.5 };
      if (c >= 3 && c <= 5) cell.numFmt = NUMBER_FORMAT;
      if (idx % 2 === 1) cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ZEBRA_FILL } };
    }
  });

  const tbTotRow = 4 + ledgers.length;
  wsTB.getCell(`A${tbTotRow}`).value = 'TOTAL TRIAL BALANCE';
  wsTB.getCell(`C${tbTotRow}`).value = { formula: `SUM(C4:C${tbTotRow - 1})` };
  wsTB.getCell(`D${tbTotRow}`).value = { formula: `SUM(D4:D${tbTotRow - 1})` };
  wsTB.getCell(`E${tbTotRow}`).value = { formula: `C${tbTotRow}-D${tbTotRow}` };

  for (let c = 1; c <= 6; c++) {
    const cell = wsTB.getCell(tbTotRow, c);
    cell.font = { bold: true, name: 'Segoe UI', size: 10 };
    cell.border = BORDERS.totalRow;
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_FILL } };
    if (c >= 3 && c <= 5) cell.numFmt = NUMBER_FORMAT;
  }

  wsTB.columns = [
    { width: 44 },
    { width: 28 },
    { width: 20 },
    { width: 20 },
    { width: 20 },
    { width: 34 },
  ];

  // =========================================================================
  // SHEET: RECONCILIATION SHEET
  // =========================================================================
  const wsRecon = workbook.addWorksheet('RECONCILIATION', { views: [{ showGridLines: true }] });

  wsRecon.mergeCells('A1:C1');
  const reconTitle = wsRecon.getCell('A1');
  reconTitle.value = `${entity.name.toUpperCase()} — AUDIT RECONCILIATION STATEMENT`;
  reconTitle.font = { name: 'Segoe UI', size: 12, bold: true, color: { argb: COLORS.HEADER_TEXT } };
  reconTitle.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_FILL } };
  reconTitle.alignment = { vertical: 'middle', horizontal: 'center' };
  wsRecon.getRow(1).height = 28;

  const reconHeaders = ['Particulars', 'Amount (₹)', 'Verification Status'];
  wsRecon.getRow(3).values = reconHeaders;
  wsRecon.getRow(3).height = 22;
  reconHeaders.forEach((_, i) => {
    const cell = wsRecon.getCell(3, i + 1);
    cell.font = { name: 'Segoe UI', size: 10, bold: true, color: { argb: COLORS.HEADER_TEXT } };
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: '334155' } };
    cell.alignment = { vertical: 'middle', horizontal: i === 1 ? 'right' : 'left' };
    cell.border = BORDERS.thin;
  });

  const reconRows = [
    ['Total Trial Balance Debit', reconciliation.totalTrialBalanceDebit, 'Verified from General Ledger'],
    ['Total Trial Balance Credit', reconciliation.totalTrialBalanceCredit, 'Verified from General Ledger'],
    ['Trial Balance Difference', reconciliation.trialBalanceDifference, reconciliation.isTrialBalanceBalanced ? 'Balanced (0.00) ✓' : 'DIFFERENCE EXISTS ⚠'],
    ['Total Balance Sheet Assets', reconciliation.totalAssets, 'As per Schedule 8 to 14'],
    ['Total Capital & Liabilities', reconciliation.totalLiabilities, 'As per Schedule 1 to 7'],
    ['Balance Sheet Difference', reconciliation.balanceSheetDifference, reconciliation.isBalanceSheetBalanced ? 'Balanced (0.00) ✓' : 'DIFFERENCE EXISTS ⚠'],
    ['P&L Net Profit Transferred to Capital', reconciliation.plNetProfit, 'Reconciled with Schedule 1'],
    ['Unclassified / Low Confidence Ledgers', reconciliation.unclassifiedLedgersCount, reconciliation.unclassifiedLedgersCount === 0 ? '100% Mapped (Zero Unclassified) ✓' : 'Needs Review'],
  ];

  reconRows.forEach((row, idx) => {
    const rowNum = 4 + idx;
    wsRecon.getCell(`A${rowNum}`).value = row[0];
    wsRecon.getCell(`B${rowNum}`).value = row[1];
    wsRecon.getCell(`C${rowNum}`).value = row[2];

    for (let c = 1; c <= 3; c++) {
      const cell = wsRecon.getCell(rowNum, c);
      cell.border = BORDERS.thin;
      cell.font = { name: 'Segoe UI', size: 10 };
      if (c === 2 && typeof row[1] === 'number') {
        cell.numFmt = NUMBER_FORMAT;
        cell.alignment = { horizontal: 'right' };
      }
    }
  });

  wsRecon.columns = [
    { width: 44 },
    { width: 22 },
    { width: 34 },
  ];

  const buffer = await workbook.xlsx.writeBuffer();
  return new Blob([buffer], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
}
