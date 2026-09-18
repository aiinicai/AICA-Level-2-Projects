import * as XLSX from 'xlsx';
import { TrialBalanceItem, TrialBalanceSummary, TrialBalanceData, TBCategory } from '../types';
import { computeTBSummary } from '../data/sampleTrialBalance';

export interface ColumnMapping {
  accountCode: string;
  accountName: string;
  scheduleIIIGroup: string;
  category: string;
  debit: string;
  credit: string;
  net: string;
  priorYear: string;
}

export function detectHeaders(sheetData: any[][]): {
  headerRowIndex: number;
  headers: string[];
  suggestedMapping: ColumnMapping;
} {
  let headerRowIndex = 0;
  let bestScore = -1;

  // Scan first 15 rows to find the row with header-like keywords
  for (let r = 0; r < Math.min(15, sheetData.length); r++) {
    const row = sheetData[r];
    if (!Array.isArray(row)) continue;

    let score = 0;
    const rowTexts = row.map((c) => String(c || '').toLowerCase().trim());

    if (rowTexts.some((t) => t.includes('account') || t.includes('ledger') || t.includes('particular'))) score += 3;
    if (rowTexts.some((t) => t.includes('debit') || t === 'dr')) score += 3;
    if (rowTexts.some((t) => t.includes('credit') || t === 'cr')) score += 3;
    if (rowTexts.some((t) => t.includes('code') || t.includes('no') || t.includes('ac'))) score += 2;
    if (rowTexts.some((t) => t.includes('group') || t.includes('schedule') || t.includes('category'))) score += 2;
    if (rowTexts.some((t) => t.includes('balance') || t.includes('closing') || t.includes('amount'))) score += 2;

    if (score > bestScore) {
      bestScore = score;
      headerRowIndex = r;
    }
  }

  const rawHeaders = sheetData[headerRowIndex] || [];
  const headers = rawHeaders.map((h, i) => String(h || `Column_${i + 1}`).trim());

  const findHeaderMatch = (keywords: string[]): string => {
    for (const h of headers) {
      const lower = h.toLowerCase();
      if (keywords.some((k) => lower === k || lower.includes(k))) {
        return h;
      }
    }
    return '';
  };

  const suggestedMapping: ColumnMapping = {
    accountCode: findHeaderMatch(['account code', 'ac code', 'code', 'gl code', 'ledger code', 'ac no', 'account no']),
    accountName: findHeaderMatch(['account name', 'ledger name', 'account', 'ledger', 'particulars', 'description', 'head of account']),
    scheduleIIIGroup: findHeaderMatch(['schedule iii', 'group', 'schedule', 'fs head', 'classification', 'sub group']),
    category: findHeaderMatch(['category', 'type', 'nature', 'account type']),
    debit: findHeaderMatch(['debit (inr)', 'debit amount', 'debit', 'dr amount', 'dr']),
    credit: findHeaderMatch(['credit (inr)', 'credit amount', 'credit', 'cr amount', 'cr']),
    net: findHeaderMatch(['closing balance', 'net balance', 'net', 'balance', 'closing']),
    priorYear: findHeaderMatch(['prior year', 'previous year', 'py balance', 'py', 'fy 24-25', 'last year']),
  };

  return { headerRowIndex, headers, suggestedMapping };
}

export function autoCategorizeGroup(groupName: string, accountName: string): { group: string; category: TBCategory } {
  const combined = `${groupName} ${accountName}`.toLowerCase();

  // Revenue
  if (
    combined.includes('sale') ||
    combined.includes('revenue') ||
    combined.includes('turnover') ||
    combined.includes('export incentive') ||
    combined.includes('scrap') ||
    combined.includes('other income') ||
    combined.includes('interest income') ||
    combined.includes('dividend received')
  ) {
    const isOther = combined.includes('other income') || combined.includes('scrap') || combined.includes('interest income');
    return { group: isOther ? 'Other Income' : 'Revenue from Operations', category: 'Revenue' };
  }

  // Cost of Materials & Purchases
  if (
    combined.includes('raw material') ||
    combined.includes('cotton') ||
    combined.includes('yarn') ||
    combined.includes('fabric purchase') ||
    combined.includes('dyes') ||
    combined.includes('chemicals') ||
    combined.includes('packaging material') ||
    combined.includes('material consumed')
  ) {
    return { group: 'Cost of Materials Consumed', category: 'Expenses' };
  }

  // Changes in Inventory
  if (combined.includes('changes in inventor') || combined.includes('stock in trade') || combined.includes('opening stock') || combined.includes('closing stock')) {
    return { group: 'Changes in Inventories', category: 'Expenses' };
  }

  // Employee benefit
  if (
    combined.includes('salar') ||
    combined.includes('wage') ||
    combined.includes('provident fund') ||
    combined.includes('pf') ||
    combined.includes('esi') ||
    combined.includes('bonus') ||
    combined.includes('gratuity') ||
    combined.includes('staff welfare') ||
    combined.includes('payroll')
  ) {
    return { group: 'Employee Benefit Expenses', category: 'Expenses' };
  }

  // Finance cost
  if (combined.includes('interest on loan') || combined.includes('bank charge') || combined.includes('finance cost') || combined.includes('lc discount')) {
    return { group: 'Finance Costs', category: 'Expenses' };
  }

  // Depreciation
  if (combined.includes('depreciation') || combined.includes('amorti')) {
    return { group: 'Depreciation & Amortisation', category: 'Expenses' };
  }

  // Other Expenses
  if (
    combined.includes('power') ||
    combined.includes('electricity') ||
    combined.includes('fuel') ||
    combined.includes('freight') ||
    combined.includes('job work') ||
    combined.includes('rent') ||
    combined.includes('repair') ||
    combined.includes('legal') ||
    combined.includes('audit fee') ||
    combined.includes('rate') ||
    combined.includes('tax') ||
    combined.includes('insurance') ||
    combined.includes('expense')
  ) {
    return { group: 'Other Expenses', category: 'Expenses' };
  }

  // PPE & Fixed Assets
  if (
    combined.includes('plant') ||
    combined.includes('machiner') ||
    combined.includes('building') ||
    combined.includes('land') ||
    combined.includes('furniture') ||
    combined.includes('vehicle') ||
    combined.includes('computer') ||
    combined.includes('ppe') ||
    combined.includes('fixed asset')
  ) {
    return { group: 'Property, Plant & Equipment (PPE)', category: 'Assets' };
  }

  if (combined.includes('cwip') || combined.includes('capital work')) {
    return { group: 'Capital Work-in-Progress (CWIP)', category: 'Assets' };
  }

  // Inventories
  if (combined.includes('inventor') || combined.includes('stock') || combined.includes('finished good') || combined.includes('wip') || combined.includes('stores')) {
    return { group: 'Inventories', category: 'Assets' };
  }

  // Trade Receivables
  if (combined.includes('debtor') || combined.includes('receivable') || combined.includes('customer')) {
    return { group: 'Trade Receivables', category: 'Assets' };
  }

  // Cash & Bank
  if (combined.includes('cash') || combined.includes('bank') || combined.includes('fixed deposit') || combined.includes('fd') || combined.includes('cheque')) {
    return { group: 'Cash & Cash Equivalents', category: 'Assets' };
  }

  // Loans & Advances / Other current assets
  if (combined.includes('advance') || combined.includes('gst') || combined.includes('itc') || combined.includes('deposit') || combined.includes('prepaid')) {
    return { group: combined.includes('deposit') ? 'Other Non-Current Assets' : 'Other Current Assets', category: 'Assets' };
  }

  // Equity
  if (combined.includes('share capital') || combined.includes('equity') || combined.includes('reserve') || combined.includes('surplus') || combined.includes('retained earning')) {
    return { group: 'Equity Share Capital & Other Equity', category: 'Equity' };
  }

  // Borrowings
  if (combined.includes('borrowing') || combined.includes('term loan') || combined.includes('cash credit') || combined.includes('overdraft') || combined.includes('unsecured loan')) {
    return { group: 'Borrowings (Term Loans & Working Capital)', category: 'Liabilities' };
  }

  // Trade Payables
  if (combined.includes('creditor') || combined.includes('payable') || combined.includes('vendor') || combined.includes('supplier') || combined.includes('msme')) {
    return { group: 'Trade Payables (MSME & Others)', category: 'Liabilities' };
  }

  // Default fallback
  return { group: groupName || 'Other Items', category: 'Expenses' };
}

export function parseRawTableToTB(
  sheetData: any[][],
  mapping: ColumnMapping,
  headerRowIndex: number,
  overallMateriality: number = 5950000,
  performanceMateriality: number = 4165000,
  clearlyTrivial: number = 297500
): TrialBalanceItem[] {
  const headers = (sheetData[headerRowIndex] || []).map((h) => String(h || '').trim());
  const rows = sheetData.slice(headerRowIndex + 1);

  const getIdx = (colName: string): number => {
    if (!colName) return -1;
    return headers.indexOf(colName);
  };

  const codeIdx = getIdx(mapping.accountCode);
  const nameIdx = getIdx(mapping.accountName);
  const groupIdx = getIdx(mapping.scheduleIIIGroup);
  const catIdx = getIdx(mapping.category);
  const drIdx = getIdx(mapping.debit);
  const crIdx = getIdx(mapping.credit);
  const netIdx = getIdx(mapping.net);
  const pyIdx = getIdx(mapping.priorYear);

  const cleanNum = (val: any): number => {
    if (val === null || val === undefined || val === '') return 0;
    if (typeof val === 'number') return isNaN(val) ? 0 : val;
    const str = String(val).replace(/,/g, '').replace(/[^\d.-]/g, '').trim();
    const num = parseFloat(str);
    return isNaN(num) ? 0 : num;
  };

  const items: TrialBalanceItem[] = [];

  rows.forEach((row, i) => {
    if (!Array.isArray(row) || row.length === 0) return;

    const rawName = nameIdx >= 0 ? String(row[nameIdx] || '').trim() : '';
    const rawCode = codeIdx >= 0 ? String(row[codeIdx] || '').trim() : '';
    const rawGroup = groupIdx >= 0 ? String(row[groupIdx] || '').trim() : '';
    const rawCat = catIdx >= 0 ? String(row[catIdx] || '').trim() : '';

    // Ignore empty lines or total rows
    if (!rawName && !rawCode) return;
    const lowerName = rawName.toLowerCase();
    if (lowerName.includes('total') || lowerName.includes('grand total') || lowerName === 'sum') return;

    let dr = drIdx >= 0 ? cleanNum(row[drIdx]) : 0;
    let cr = crIdx >= 0 ? cleanNum(row[crIdx]) : 0;
    let net = netIdx >= 0 ? cleanNum(row[netIdx]) : 0;
    const py = pyIdx >= 0 ? cleanNum(row[pyIdx]) : undefined;

    // If net is given but not dr/cr
    if (net !== 0 && dr === 0 && cr === 0) {
      if (net > 0) dr = net;
      else cr = Math.abs(net);
    } else if (net === 0 && (dr !== 0 || cr !== 0)) {
      net = dr - cr;
    }

    const { group: autoGroup, category: autoCat } = autoCategorizeGroup(rawGroup, rawName);

    const finalGroup = rawGroup || autoGroup;
    let finalCategory: TBCategory = autoCat;
    if (['Assets', 'Liabilities', 'Equity', 'Revenue', 'Expenses'].includes(rawCat)) {
      finalCategory = rawCat as TBCategory;
    }

    const absAmount = Math.max(Math.abs(dr), Math.abs(cr), Math.abs(net));
    let matFlag: TrialBalanceItem['materialityFlag'] = 'Normal';
    if (absAmount >= overallMateriality) {
      matFlag = 'Material (>OM)';
    } else if (absAmount >= performanceMateriality) {
      matFlag = 'Significant (>PM)';
    } else if (absAmount <= clearlyTrivial && absAmount > 0) {
      matFlag = 'Clearly Trivial';
    }

    let varianceAmount: number | undefined = undefined;
    let variancePercent: number | undefined = undefined;
    if (py !== undefined && py !== 0) {
      varianceAmount = Math.abs(net) - Math.abs(py);
      variancePercent = Number(((varianceAmount / Math.abs(py)) * 100).toFixed(2));
    }

    items.push({
      id: `tb-item-${i + 1}-${Date.now().toString(36)}`,
      accountCode: rawCode || String(1000 + i),
      accountName: rawName || `Account ${i + 1}`,
      scheduleIIIGroup: finalGroup,
      category: finalCategory,
      currentYearDebit: dr,
      currentYearCredit: cr,
      currentYearNet: net,
      priorYearBalance: py,
      varianceAmount,
      variancePercent,
      materialityFlag: matFlag,
      notes: '',
    });
  });

  return items;
}

export function generateTrialBalanceTemplate(): Uint8Array {
  const wb = XLSX.utils.book_new();

  const headers = [
    'Account Code',
    'Account Name / Ledger',
    'Schedule III Group',
    'Category',
    'Debit (INR)',
    'Credit (INR)',
    'Prior Year Balance (INR)',
    'Notes / Remarks',
  ];

  const sampleRows = [
    ['1010', 'Factory Land & Freehold Property', 'Property, Plant & Equipment (PPE)', 'Assets', 180000000, 0, 180000000, 'Title verified'],
    ['1030', 'Plant & Machinery - Production Looms', 'Property, Plant & Equipment (PPE)', 'Assets', 289000000, 0, 295000000, 'Net block after depreciation'],
    ['1210', 'Raw Cotton Inventory at Godown', 'Inventories', 'Assets', 145000000, 0, 125000000, 'Physical count attended'],
    ['1310', 'Domestic Trade Receivables', 'Trade Receivables', 'Assets', 156000000, 0, 135000000, 'SA 505 confirmations circularized'],
    ['1410', 'SBI Operational Current Account', 'Cash & Cash Equivalents', 'Assets', 28000000, 0, 18000000, 'Bank reconciliation verified'],
    ['2010', 'Equity Share Capital', 'Equity Share Capital & Other Equity', 'Equity', 0, 150000000, 150000000, '1.5 Cr shares of ₹10 each'],
    ['2020', 'Reserves & Retained Earnings', 'Equity Share Capital & Other Equity', 'Equity', 0, 235000000, 195000000, 'General reserves'],
    ['2110', 'SBI Consortium Term Loan', 'Borrowings (Term Loans & Working Capital)', 'Liabilities', 0, 180000000, 220000000, 'Secured mortgage'],
    ['2120', 'SBI Working Capital Cash Credit', 'Borrowings (Term Loans & Working Capital)', 'Liabilities', 0, 240000000, 210000000, 'Hypothecation of stocks'],
    ['2210', 'Trade Payables - Cotton Ginners', 'Trade Payables (MSME & Others)', 'Liabilities', 0, 156000000, 136000000, 'Under Section 43B(h) compliance'],
    ['3010', 'Domestic Fabric Sales', 'Revenue from Operations', 'Revenue', 0, 1185000000, 1050000000, 'GST returns reconciled'],
    ['3020', 'Export Fabric Sales (FOB/CIF)', 'Revenue from Operations', 'Revenue', 0, 665000000, 580000000, 'ICEGATE bills matched'],
    ['4010', 'Raw Cotton Purchases', 'Cost of Materials Consumed', 'Expenses', 885000000, 0, 790000000, 'Mandis direct procurement'],
    ['5010', 'Factory Salaries & Wages', 'Employee Benefit Expenses', 'Expenses', 124000000, 0, 110000000, 'Biometric attendance matched'],
    ['5030', 'Bank Interest & Financing Costs', 'Finance Costs', 'Expenses', 56000000, 0, 52000000, 'Tied to sanction letters'],
    ['5050', 'Power, Fuel & Electricity', 'Other Expenses', 'Expenses', 215000000, 0, 190000000, 'DGVCL power bills'],
  ];

  const ws = XLSX.utils.aoa_to_sheet([headers, ...sampleRows]);

  // Set column widths
  ws['!cols'] = [
    { wch: 15 },
    { wch: 38 },
    { wch: 35 },
    { wch: 14 },
    { wch: 18 },
    { wch: 18 },
    { wch: 22 },
    { wch: 30 },
  ];

  XLSX.utils.book_append_sheet(wb, ws, 'Trial_Balance_Template');

  // Add Instructions Sheet
  const instructions = [
    ['AUDIT WORKBENCH - TRIAL BALANCE IMPORT INSTRUCTIONS'],
    [''],
    ['1. File Formats: .xlsx, .xls, and .csv are supported.'],
    ['2. The system auto-detects column headers even if column names differ.'],
    ['3. Mandatory columns: Account Name / Ledger Name, and Debit & Credit amounts (or Net Closing Balance).'],
    ['4. Categories must be one of: Assets, Liabilities, Equity, Revenue, Expenses.'],
    ['5. Total Debits must equal Total Credits for a balanced Trial Balance.'],
    ['6. Once imported, the workbench automatically computes Turnover, PBT, Total Assets, and Net Worth.'],
    ['7. You can sync any benchmark figure with SA 320 Materiality with a single click.'],
  ];
  const wsInst = XLSX.utils.aoa_to_sheet(instructions);
  XLSX.utils.book_append_sheet(wb, wsInst, 'Import_Instructions');

  return XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
}
