import * as XLSX from 'xlsx';
import { FinancialStatement, BalanceSheet, ProfitAndLoss } from '../types/financial';

/**
 * Parses an Excel (.xlsx/.xls) or CSV file containing financial statements
 */
export async function parseFinancialFile(file: File, companyId: string): Promise<FinancialStatement[]> {
  const buffer = await file.arrayBuffer();
  const workbook = XLSX.read(buffer, { type: 'array' });

  // Use first sheet
  const firstSheetName = workbook.SheetNames[0];
  const worksheet = workbook.Sheets[firstSheetName];
  const rawRows: any[][] = XLSX.utils.sheet_to_json(worksheet, { header: 1 });

  if (rawRows.length < 3) {
    throw new Error('Spreadsheet does not contain enough data rows.');
  }

  // Find header row containing financial years (e.g. "Line Item", "FY 2023", "FY 2024", etc.)
  let headerRowIdx = -1;
  for (let i = 0; i < Math.min(10, rawRows.length); i++) {
    const row = rawRows[i];
    if (Array.isArray(row) && row.some(cell => typeof cell === 'string' && (cell.toLowerCase().includes('fy') || cell.toLowerCase().includes('202') || cell.toLowerCase().includes('year')))) {
      headerRowIdx = i;
      break;
    }
  }

  if (headerRowIdx === -1) {
    // Default to row 0 or 1
    headerRowIdx = rawRows.findIndex(r => Array.isArray(r) && r.length > 1);
  }

  const headerRow = rawRows[headerRowIdx] || [];
  const yearCols: { year: string; colIdx: number }[] = [];

  for (let c = 1; c < headerRow.length; c++) {
    const val = headerRow[c];
    if (val !== undefined && val !== null && String(val).trim().length > 0) {
      yearCols.push({
        year: String(val).trim(),
        colIdx: c
      });
    }
  }

  if (yearCols.length === 0) {
    throw new Error('Could not identify Financial Year columns. Please check that headers mention FY 2023, FY 2024, etc.');
  }

  // Map each year's column to a data store
  const parsedByYear: Record<string, { [key: string]: number }> = {};
  yearCols.forEach(yc => {
    parsedByYear[yc.year] = {};
  });

  // Helper to normalize item key
  const normalizeKey = (str: string): string => {
    return str.toLowerCase().replace(/[^a-z0-9]/g, '');
  };

  for (let r = headerRowIdx + 1; r < rawRows.length; r++) {
    const row = rawRows[r];
    if (!Array.isArray(row) || !row[0]) continue;
    const rawKey = String(row[0]).trim();
    const cleanKey = normalizeKey(rawKey);

    yearCols.forEach(yc => {
      const cellVal = row[yc.colIdx];
      const numVal = parseFloat(cellVal);
      if (!isNaN(numVal)) {
        parsedByYear[yc.year][cleanKey] = numVal;
      }
    });
  }

  // Helper to find value from possible aliases
  const getVal = (yearDict: { [key: string]: number }, aliases: string[]): number => {
    for (const alias of aliases) {
      const cleanAlias = normalizeKey(alias);
      if (yearDict[cleanAlias] !== undefined) {
        return yearDict[cleanAlias];
      }
      // Partial match
      for (const k of Object.keys(yearDict)) {
        if (k.includes(cleanAlias) || cleanAlias.includes(k)) {
          return yearDict[k];
        }
      }
    }
    return 0;
  };

  const results: FinancialStatement[] = [];

  yearCols.forEach(yc => {
    const dict = parsedByYear[yc.year];

    // P&L extraction
    const revenue = getVal(dict, ['revenue', 'sales', 'turnover', 'income', 'gross sales']);
    const otherIncome = getVal(dict, ['otherincome', 'other operating income']);
    const cogs = getVal(dict, ['cogs', 'cost of goods sold', 'cost of sales', 'raw materials']);
    let grossProfit = getVal(dict, ['grossprofit', 'gross margin']);
    if (!grossProfit && revenue && cogs) grossProfit = revenue - cogs;

    const operatingExpenses = getVal(dict, ['operatingexpenses', 'opex', 'operating costs', 'sga']);
    let ebitda = getVal(dict, ['ebitda', 'operating profit before depreciation']);
    if (!ebitda && grossProfit) ebitda = grossProfit - operatingExpenses;

    const depreciation = getVal(dict, ['depreciation', 'depreciationandamortization', 'dna']);
    let ebit = getVal(dict, ['ebit', 'operating profit', 'pbit']);
    if (!ebit && ebitda) ebit = ebitda - depreciation;

    const interestExpense = getVal(dict, ['interestexpense', 'interest', 'financecosts', 'finance expense']);
    let profitBeforeTax = getVal(dict, ['profitbeforetax', 'pbt', 'ebt']);
    if (!profitBeforeTax && ebit) profitBeforeTax = ebit - interestExpense;

    const taxExpense = getVal(dict, ['taxexpense', 'tax', 'incometax']);
    let netProfit = getVal(dict, ['netprofit', 'pat', 'profit after tax', 'net income']);
    if (!netProfit && profitBeforeTax) netProfit = profitBeforeTax - taxExpense;

    const pl: ProfitAndLoss = {
      revenue: revenue || 10,
      otherIncome,
      cogs: cogs || revenue * 0.6,
      grossProfit: grossProfit || revenue * 0.4,
      operatingExpenses: operatingExpenses || revenue * 0.2,
      ebitda: ebitda || revenue * 0.2,
      depreciation: depreciation || revenue * 0.03,
      ebit: ebit || revenue * 0.17,
      interestExpense: interestExpense || revenue * 0.02,
      profitBeforeTax: profitBeforeTax || revenue * 0.15,
      taxExpense: taxExpense || revenue * 0.035,
      netProfit: netProfit || revenue * 0.115
    };

    // Balance Sheet extraction
    const cash = getVal(dict, ['cash', 'cashequivalents']);
    const bank = getVal(dict, ['bank', 'bankbalance', 'bankbalances']);
    const receivables = getVal(dict, ['receivables', 'tradereceivables', 'debtors', 'accountsreceivable']);
    const inventory = getVal(dict, ['inventory', 'inventories', 'stock']);
    const otherCurrentAssets = getVal(dict, ['othercurrentassets', 'otherca']);

    const fixedAssets = getVal(dict, ['fixedassets', 'ppe', 'propertyplant']);
    const investments = getVal(dict, ['investments', 'noncurrentinvestments']);
    const otherNonCurrentAssets = getVal(dict, ['othernoncurrentassets', 'otherassets']);

    const payables = getVal(dict, ['payables', 'tradepayables', 'creditors', 'accountspayable']);
    const shortTermDebt = getVal(dict, ['shorttermdebt', 'stdebt', 'shorttermborrowings', 'workingcapitalfacility']);
    const otherCurrentLiabilities = getVal(dict, ['othercurrentliabilities', 'othercl']);

    const longTermDebt = getVal(dict, ['longtermdebt', 'ltdebt', 'termloans', 'longtermborrowings']);
    const otherNonCurrentLiabilities = getVal(dict, ['othernoncurrentliabilities']);

    const equity = getVal(dict, ['equity', 'sharecapital', 'paidupcapital']);
    const reserves = getVal(dict, ['reserves', 'reservesandsurplus', 'retainedearnings']);

    const totalCurrentAssets = cash + bank + receivables + inventory + otherCurrentAssets;
    const totalCurrentLiabilities = payables + shortTermDebt + otherCurrentLiabilities;
    const totalDebt = shortTermDebt + longTermDebt;
    const totalEquity = equity + reserves;
    const totalAssets = getVal(dict, ['totalassets']) || (totalCurrentAssets + fixedAssets + investments + otherNonCurrentAssets);
    const totalLiabilities = getVal(dict, ['totalliabilities']) || (totalCurrentLiabilities + longTermDebt + otherNonCurrentLiabilities + totalEquity);

    const bs: BalanceSheet = {
      cash,
      bank,
      receivables,
      inventory,
      otherCurrentAssets,
      fixedAssets,
      investments,
      otherNonCurrentAssets,
      payables,
      shortTermDebt,
      otherCurrentLiabilities,
      longTermDebt,
      otherNonCurrentLiabilities,
      equity: equity || 10,
      reserves: reserves || 20,
      totalCurrentAssets,
      totalCurrentLiabilities,
      totalDebt,
      totalEquity,
      totalAssets: totalAssets || 100,
      totalLiabilities: totalLiabilities || 100
    };

    results.push({
      id: `stmt-${companyId}-${yc.year.replace(/\s+/g, '_')}`,
      companyId,
      financialYear: yc.year,
      currency: 'INR',
      unit: 'Crores',
      balanceSheet: bs,
      profitAndLoss: pl
    });
  });

  return results;
}
