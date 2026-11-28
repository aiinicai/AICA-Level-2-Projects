import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import PptxGenJS from 'pptxgenjs';
import {
  formatMoney,
  formatPct,
  roundOMR,
  type ExecutiveCommentaryBundle,
  type FinancialStatements,
  type ProjectKpiSummary,
  type ReconciliationResult,
} from '../engine/kpiEngine';
import type { Company, CurrencyCode, MisDataset, ReportingBasis, TrialBalanceRow } from '../types/mis';

export interface TemplateDefinition {
  id: string;
  name: string;
  description: string;
  columns: string[];
  sampleRows: (string | number)[][];
}

export const UPLOAD_TEMPLATES: TemplateDefinition[] = [
  {
    id: 'trial-balance',
    name: 'Trial Balance & General Ledger',
    description: 'ERP-agnostic GL Trial Balance with Opening, Period Debit/Credit, Closing, Project & Cost Centre.',
    columns: ['AccountCode', 'AccountName', 'CompanyCode', 'ProjectCode', 'CostCentre', 'Department', 'OpeningDebit', 'OpeningCredit', 'PeriodDebit', 'PeriodCredit', 'ClosingDebit', 'ClosingCredit'],
    sampleRows: [
      ['1010', 'Corporate Operating Bank', 'AMUD', 'PRJ-01', 'CC-TREASURY', 'Treasury', 8420000.0, 0, 450000.0, 0, 8870000.0, 0],
      ['4010', 'Development Revenue (IFRS 15)', 'AMUD', 'PRJ-01', 'CC-SALES', 'Commercial', 0, 0, 0, 1950000.0, 0, 1950000.0],
      ['5010', 'Cost of Development Sales', 'AMUD', 'PRJ-01', 'CC-DEV', 'Development', 0, 0, 1287000.0, 0, 1287000.0, 0],
      ['6010', 'Sales & G&A Expenses', 'AMUD', 'PRJ-01', 'CC-CORP', 'Corporate', 0, 0, 213000.0, 0, 213000.0, 0],
    ],
  },
  {
    id: 'project-unit-master',
    name: 'Project & Unit Master',
    description: 'Phases, buildings, floors, unit types, sellable sqm, and list prices.',
    columns: ['ProjectCode', 'UnitCode', 'Phase', 'Building', 'Floor', 'UnitType', 'AreaSqm', 'ListPriceOMR', 'Status'],
    sampleRows: [['PRJ-01', 'PRJ-01-B1-011', 'Phase 1', 'Tower A', 1, 'Apartment', 142, 126380.0, 'Available']],
  },
  {
    id: 'sales-register',
    name: 'Sales Register & Payment Schedules',
    description: 'Executed SPAs, customer names, discounts, contracted prices, and installment milestones.',
    columns: ['ProjectCode', 'UnitCode', 'CustomerName', 'SaleMonth', 'ListPriceOMR', 'DiscountOMR', 'ContractedPriceOMR', 'Status'],
    sampleRows: [['PRJ-01', 'PRJ-01-B1-024', 'Al Harthy Holdings', '2026-11', 135000.0, 4050.0, 130950.0, 'Sold']],
  },
  {
    id: 'collections-aging',
    name: 'Collections & Receivable Aging',
    description: 'Invoiced amounts, cash received, overdue aging buckets (0-30, 31-60, 61-90, 90+ days).',
    columns: ['ProjectCode', 'UnitCode', 'InvoicedOMR', 'CollectedOMR', 'OverdueOMR', 'Bucket0_30', 'Bucket31_60', 'Bucket61_90', 'Bucket90Plus'],
    sampleRows: [['PRJ-01', 'PRJ-01-B1-024', 78570.0, 72000.0, 6570.0, 2500.0, 4070.0, 0, 0]],
  },
  {
    id: 'construction-progress',
    name: 'Construction Progress & Planning',
    description: 'Planned vs Actual physical progress %, certified %, Earned Value (EV), Planned Value (PV), Actual Cost (AC).',
    columns: ['ProjectCode', 'Period', 'PlannedPhysicalPct', 'ActualPhysicalPct', 'CertifiedPct', 'PlannedValueOMR', 'EarnedValueOMR', 'ActualCostOMR'],
    sampleRows: [['PRJ-01', '2026-11', 68.5, 65.2, 62.8, 23865400.0, 22715680.0, 23418226.0]],
  },
  {
    id: 'project-budgets',
    name: 'Project Budgets & Forecasts',
    description: 'Original approved budget, revised budget, actuals, accruals, remaining commitments, and ETC.',
    columns: ['ProjectCode', 'CostCategory', 'OriginalBudgetOMR', 'RevisedBudgetOMR', 'ActualCostOMR', 'AccrualsOMR', 'CommittedRemainingOMR', 'EstimatedCostToCompleteOMR'],
    sampleRows: [['PRJ-01', 'Substructure & Superstructure', 10385000.0, 10800400.0, 5184192.0, 432016.0, 3672136.0, 1728064.0]],
  },
  {
    id: 'contractor-commitments',
    name: 'Contractor Commitments & IPCs',
    description: 'Main contractors, package values, IPCs certified, paid, and advance recoveries.',
    columns: ['ProjectCode', 'ContractorName', 'PackageTitle', 'OriginalContractOMR', 'ApprovedVariationsOMR', 'CertifiedToDateOMR', 'PaidToDateOMR'],
    sampleRows: [['PRJ-01', 'Al Ansari Civil Engineering LLC', 'Towers A-D Main Works', 18400000.0, 620000.0, 10920000.0, 9828000.0]],
  },
  {
    id: 'variations-retention',
    name: 'Variation Orders & Retention',
    description: 'Approved vs pending variation orders, contractor claims, retention held, and performance bonds.',
    columns: ['ProjectCode', 'ContractorName', 'ApprovedVariationsOMR', 'PendingClaimsOMR', 'RetentionHeldOMR', 'PerformanceBondOMR'],
    sampleRows: [['PRJ-04', 'Strabag Oman LLC', 940000.0, 1180000.0, 684000.0, 2150000.0]],
  },
  {
    id: 'bank-escrow-financing',
    name: 'Bank, Escrow & Financing Facilities',
    description: 'Unrestricted corporate cash, restricted RERA escrow balances, debt facilities, and covenant thresholds.',
    columns: ['CompanyCode', 'ProjectCode', 'LenderOrBank', 'AccountType', 'LimitOMR', 'BalanceOrDrawnOMR', 'InterestRatePct'],
    sampleRows: [['AMUD', 'PRJ-01', 'Bank Muscat Escrow', 'Restricted Escrow', 0, 12850000.0, 0]],
  },
  {
    id: 'feasibility-forecast',
    name: 'Project Feasibility & Cash Flow Forecast',
    description: 'Monthly projected sales inflows, construction capex, financing drawdowns, and discount rates.',
    columns: ['ProjectCode', 'MonthOffset', 'ProjectedInflowOMR', 'ProjectedCapexOMR', 'ProjectedFinanceOMR'],
    sampleRows: [['PRJ-01', 1, 1450000.0, 1120000.0, 82000.0]],
  },
  {
    id: 'risks-handover',
    name: 'Risks, Approvals & Handover Status',
    description: 'Risk register, likelihood/impact scores, financial exposure, completion certificates, and DLP warranty.',
    columns: ['ProjectCode', 'Category', 'Title', 'Likelihood1_5', 'Impact1_5', 'ExposureOMR', 'Owner', 'Status'],
    sampleRows: [['PRJ-04', 'Contractual', 'Soil stabilization claim', 4, 5, 1180000.0, 'QS Director', 'Escalated']],
  },
];

export function downloadUploadTemplate(templateId: string) {
  const tpl = UPLOAD_TEMPLATES.find((t) => t.id === templateId);
  if (!tpl) return;
  const wb = XLSX.utils.book_new();
  const ws = XLSX.utils.aoa_to_sheet([tpl.columns, ...tpl.sampleRows]);
  XLSX.utils.book_append_sheet(wb, ws, 'Template');
  XLSX.writeFile(wb, `RealEstate360_Template_${tpl.id}.xlsx`);
}

export interface ParsedTbUploadResult {
  detectedColumns: Record<string, string>;
  rows: TrialBalanceRow[];
  warnings: string[];
}

/**
 * Parses uploaded Excel/CSV Trial Balance files and auto-detects ERP column headers.
 */
export async function parseTrialBalanceFile(
  file: File,
  companyId: string,
  period: string,
  existingMappings: Map<string, TrialBalanceRow['accountClass']>
): Promise<ParsedTbUploadResult> {
  const buffer = await file.arrayBuffer();
  const wb = XLSX.read(buffer, { type: 'array' });
  const firstSheet = wb.Sheets[wb.SheetNames[0]];
  const rawRecords = XLSX.utils.sheet_to_json<Record<string, unknown>>(firstSheet, { defval: '' });

  if (rawRecords.length === 0) {
    return { detectedColumns: {}, rows: [], warnings: ['Uploaded file contains zero data rows.'] };
  }

  const headers = Object.keys(rawRecords[0]);
  const findCol = (patterns: RegExp[]) =>
    headers.find((h) => patterns.some((rx) => rx.test(h.trim()))) ?? '';

  const colMap = {
    accountCode: findCol([/acc.*code/i, /gl.*code/i, /^code$/i, /^account$/i, /acct/i]),
    accountName: findCol([/acc.*name/i, /description/i, /title/i, /gl.*name/i]),
    projectId: findCol([/proj/i, /spv/i]),
    costCentre: findCol([/cost.*cent/i, /^cc$/i]),
    department: findCol([/dept/i, /department/i]),
    openDr: findCol([/open.*dr/i, /open.*debit/i, /op.*debit/i]),
    openCr: findCol([/open.*cr/i, /open.*credit/i, /op.*credit/i]),
    perDr: findCol([/per.*dr/i, /mov.*dr/i, /^debit$/i, /period.*debit/i]),
    perCr: findCol([/per.*cr/i, /mov.*cr/i, /^credit$/i, /period.*credit/i]),
    closeDr: findCol([/close.*dr/i, /closing.*debit/i, /end.*dr/i]),
    closeCr: findCol([/close.*cr/i, /closing.*credit/i, /end.*cr/i]),
  };

  const warnings: string[] = [];
  if (!colMap.accountCode) warnings.push('Could not auto-detect Account Code column; using row index.');
  if (!colMap.perDr || !colMap.perCr) warnings.push('Debit/Credit movement columns partially mapped.');

  const num = (v: unknown): number => {
    if (typeof v === 'number') return roundOMR(v);
    if (typeof v === 'string') {
      const cleaned = v.replace(/[,\sOMR]/gi, '');
      const parsed = Number(cleaned);
      return Number.isFinite(parsed) ? roundOMR(parsed) : 0;
    }
    return 0;
  };

  const rows: TrialBalanceRow[] = rawRecords.map((rec, idx) => {
    const accountCode = String(rec[colMap.accountCode] || `${9000 + idx}`).trim();
    const accountName = String(rec[colMap.accountName] || `GL Account ${accountCode}`).trim();
    const mappedClass = existingMappings.get(accountCode) ?? inferAccountClass(accountCode, accountName);

    const openDr = num(rec[colMap.openDr]);
    const openCr = num(rec[colMap.openCr]);
    const perDr = num(rec[colMap.perDr]);
    const perCr = num(rec[colMap.perCr]);
    let closeDr = num(rec[colMap.closeDr]);
    let closeCr = num(rec[colMap.closeCr]);

    if (!colMap.closeDr && !colMap.closeCr) {
      const net = roundOMR(openDr - openCr + perDr - perCr);
      closeDr = net >= 0 ? net : 0;
      closeCr = net < 0 ? Math.abs(net) : 0;
    }

    return {
      id: `tb-up-${period}-${companyId}-${accountCode}-${idx}`,
      companyId,
      projectId: rec[colMap.projectId] ? String(rec[colMap.projectId]) : null,
      period,
      accountCode,
      accountName,
      costCentre: String(rec[colMap.costCentre] || 'CC-GENERAL'),
      department: String(rec[colMap.department] || 'Finance'),
      accountClass: mappedClass,
      openingDebit: openDr,
      openingCredit: openCr,
      periodDebit: perDr,
      periodCredit: perCr,
      closingDebit: closeDr,
      closingCredit: closeCr,
      isIntercompany: /intercompany/i.test(accountName),
    };
  });

  return { detectedColumns: colMap, rows, warnings };
}

function inferAccountClass(code: string, name: string): TrialBalanceRow['accountClass'] {
  const n = name.toLowerCase();
  if (n.includes('escrow')) return 'CashEscrow';
  if (n.includes('bank') || n.includes('cash')) return 'CashUnrestricted';
  if (n.includes('receivable')) return 'Receivables';
  if (n.includes('contract asset')) return 'ContractAsset';
  if (n.includes('wip') || n.includes('inventory')) return 'InventoryWIP';
  if (n.includes('revenue') || code.startsWith('4')) return 'Revenue';
  if (n.includes('cost of sales') || n.includes('cogs') || code.startsWith('5')) return 'COGS';
  if (n.includes('expense') || n.includes('g&a') || code.startsWith('6')) return 'OpEx';
  if (n.includes('interest') || n.includes('finance')) return 'FinanceCost';
  if (n.includes('tax')) return 'Tax';
  if (n.includes('advance')) return 'CustomerAdvances';
  if (n.includes('retention')) return 'RetentionPayable';
  if (n.includes('payable')) return 'Payables';
  if (n.includes('loan') || n.includes('debt') || n.includes('murabaha')) return 'Debt';
  if (n.includes('equity') || n.includes('capital')) return 'Equity';
  return 'Unmapped';
}

export function exportMisExcelPack(
  dataset: MisDataset,
  statements: FinancialStatements,
  projectKpis: ProjectKpiSummary[],
  reconciliation: ReconciliationResult,
  selectedPeriod: string,
  basis: ReportingBasis,
  currency: CurrencyCode,
  companyLabel: string
) {
  const wb = XLSX.utils.book_new();

  // Sheet 1: Executive Financial Statements (with live Excel formulas)
  const fsRows: (string | number | { f: string })[][] = [
    ['RealEstate 360 — Monthly MIS Financial Statements', '', '', ''],
    [`Entity: ${companyLabel}`, `Period: ${selectedPeriod}`, `Basis: ${basis}`, `Currency: ${currency}`],
    [],
    ['Income Statement Line Item', 'Amount (OMR)', 'Notes / IFRS Basis', ''],
    ['Recognized Revenue (IFRS 15)', statements.revenue, 'PoC Over-Time & Point-in-Time Handover', ''],
    ['Cost of Development Sales', -statements.cogs, 'Matched Cost of Sales', ''],
    ['Gross Profit', { f: 'B5+B6' }, 'Formula: Revenue - COGS', ''],
    ['Operating & G&A Expenses', -statements.opex, 'Sales, Marketing & Corporate Overhead', ''],
    ['EBITDA', { f: 'B7+B8' }, 'Formula: Gross Profit - OpEx', ''],
    ['Net Finance Cost (post IAS 23)', -statements.financeCostNet, `Capitalized: ${statements.borrowingCostCapitalized.toFixed(3)}`, ''],
    ['Oman Corporate Tax', -statements.taxExpense, `${dataset.policies.omanCorporateTaxRatePct}% Statutory Rate`, ''],
    ['Net Profit After Tax', { f: 'B9+B10+B11' }, 'Formula: EBITDA - Net Finance - Tax', ''],
    [],
    ['Balance Sheet Line Item', 'Closing Balance (OMR)', 'Classification', ''],
    ['Unrestricted Cash & Bank', statements.cashUnrestricted, 'Current Asset', ''],
    ['Restricted Escrow Cash', statements.cashEscrowRestricted, 'Restricted Statutory Cash', ''],
    ['Trade Receivables (Net of IFRS 9 ECL)', statements.receivablesNet, `ECL Allowance: ${statements.eclAllowanceIFRS9.toFixed(3)}`, ''],
    ['Contract Assets (IFRS 15)', statements.contractAssetsIFRS15, 'Unbilled PoC Revenue', ''],
    ['Development Inventory & WIP (IAS 2)', statements.inventoryWipIAS2, 'Land & Construction WIP', ''],
    ['Investment Property (IAS 40)', statements.investmentPropertyIAS40, 'Rental Portfolio', ''],
    ['Fixed Assets', statements.fixedAssets, 'PPE', ''],
    ['Total Assets', { f: 'SUM(B15:B21)' }, 'Formula: Sum of Assets', ''],
    ['Trade & Contractor Payables', statements.payables, 'Current Liability', ''],
    ['Customer Advances (IFRS 15)', statements.customerAdvancesIFRS15, 'Contract Liability', ''],
    ['Retention Payable', statements.retentionPayable, 'Contractor Retentions', ''],
    ['Debt & Development Facilities', statements.debtTotal, 'Murabaha / Term Loans', ''],
    ['Total Liabilities', { f: 'SUM(B23:B26)' }, 'Formula: Sum of Liabilities', ''],
    ['Total Equity', { f: 'B22-B27' }, 'Formula: Assets - Liabilities', ''],
  ];
  const wsFs = XLSX.utils.aoa_to_sheet(fsRows);
  XLSX.utils.book_append_sheet(wb, wsFs, 'Financial Statements');

  // Sheet 2: Project Performance & Validation Workbook
  const prjHeader = [
    'Project Code',
    'Project Name',
    'Category',
    'Total Units',
    'Sold Units',
    'GDV (OMR)',
    'Contracted Sales (OMR)',
    'Recognized Revenue (OMR)',
    'Collected (OMR)',
    'Actual Cost (OMR)',
    'Accruals (OMR)',
    'Remaining Commitments (OMR)',
    'Additional ETC (OMR)',
    'Forecast Final Cost EAC (OMR)',
    'EAC Formula Check',
    'Physical %',
    'SPI',
    'CPI',
  ];
  const prjRows = projectKpis.map((p, idx) => {
    const r = idx + 2;
    return [
      p.project.code,
      p.project.name,
      p.project.category,
      p.project.totalUnits,
      p.soldUnits,
      p.gdvOMR,
      p.contractedSalesOMR,
      p.recognizedRevenueOMR,
      p.collectedOMR,
      p.actualCostOMR,
      p.accrualsOMR,
      p.committedRemainingOMR,
      p.estimatedCostToCompleteOMR,
      p.forecastFinalCostEAC,
      { f: `J${r}+K${r}+L${r}+M${r}` },
      p.physicalProgressPct ?? 'N/A',
      p.spi ?? 'N/A',
      p.cpi ?? 'N/A',
    ];
  });
  const wsPrj = XLSX.utils.aoa_to_sheet([prjHeader, ...prjRows]);
  XLSX.utils.book_append_sheet(wb, wsPrj, 'Project Validation');

  // Sheet 3: Trial Balance Reconciliation
  const tbHeader = [
    'Company ID',
    'Account Code',
    'Account Name',
    'Class',
    'Opening Debit',
    'Opening Credit',
    'Period Debit',
    'Period Credit',
    'Closing Debit',
    'Closing Credit',
  ];
  const tbPeriodRows = dataset.trialBalance
    .filter((r) => r.period === selectedPeriod)
    .map((r) => [
      r.companyId,
      r.accountCode,
      r.accountName,
      r.accountClass,
      r.openingDebit,
      r.openingCredit,
      r.periodDebit,
      r.periodCredit,
      r.closingDebit,
      r.closingCredit,
    ]);
  tbPeriodRows.push([
    'TOTAL',
    '',
    `Reconciled: ${reconciliation.isMateriallyReconciled ? 'YES' : 'NO'}`,
    '',
    0,
    0,
    reconciliation.totalPeriodDebit,
    reconciliation.totalPeriodCredit,
    0,
    0,
  ]);
  const wsTb = XLSX.utils.aoa_to_sheet([tbHeader, ...tbPeriodRows]);
  XLSX.utils.book_append_sheet(wb, wsTb, 'TB Reconciliation');

  XLSX.writeFile(wb, `RealEstate360_MIS_Pack_${selectedPeriod}.xlsx`);
}

export function exportMisPdfPack(
  company: Company | null,
  statements: FinancialStatements,
  projectKpis: ProjectKpiSummary[],
  commentary: ExecutiveCommentaryBundle,
  selectedPeriod: string,
  basis: ReportingBasis,
  currency: CurrencyCode,
  confidentialMode: boolean
) {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'pt', format: 'a4' });
  const entityTitle = company ? company.name : 'Consolidated Real Estate Group (3 Entities)';

  doc.setFillColor(11, 25, 44);
  doc.rect(0, 0, 842, 68, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18);
  doc.text('RealEstate 360 — Monthly Management Information Pack', 32, 32);
  doc.setFontSize(10);
  doc.setTextColor(212, 175, 55);
  doc.text(
    `${entityTitle}  |  Period: ${selectedPeriod}  |  Basis: ${basis}  |  Reporting Currency: ${currency}${confidentialMode ? '  |  CONFIDENTIAL MASKED' : ''}`,
    32,
    50
  );

  doc.setTextColor(15, 23, 42);
  doc.setFontSize(12);
  doc.text('1. Executive Summary & Financial Highlights', 32, 96);

  autoTable(doc, {
    startY: 106,
    head: [['Metric', 'Amount', 'Metric', 'Amount']],
    body: [
      [
        'Recognized Revenue (IFRS 15)',
        formatMoney(statements.revenue, currency, confidentialMode),
        'Unrestricted Corporate Cash',
        formatMoney(statements.cashUnrestricted, currency, confidentialMode),
      ],
      [
        'Gross Profit & Margin',
        `${formatMoney(statements.grossProfit, currency, confidentialMode)} (${formatPct(statements.grossMarginPct, confidentialMode)})`,
        'Restricted Escrow Cash',
        formatMoney(statements.cashEscrowRestricted, currency, confidentialMode),
      ],
      [
        'Net Profit After Tax',
        formatMoney(statements.netProfit, currency, confidentialMode),
        'Net Debt (Excl. Escrow)',
        formatMoney(statements.netDebt, currency, confidentialMode),
      ],
    ],
    theme: 'grid',
    headStyles: { fillColor: [16, 42, 67] },
    styles: { fontSize: 9 },
  });

  const afterFsY = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 20;
  doc.setFontSize(12);
  doc.text('2. Project Portfolio Performance & Cost Control', 32, afterFsY);

  autoTable(doc, {
    startY: afterFsY + 10,
    head: [['Code', 'Project Name', 'GDV', 'Contracted Sales', 'Collected', 'Forecast EAC', 'Physical %', 'SPI', 'CPI']],
    body: projectKpis.map((p) => [
      p.project.code,
      p.project.name,
      formatMoney(p.gdvOMR, currency, confidentialMode, true),
      formatMoney(p.contractedSalesOMR, currency, confidentialMode, true),
      formatMoney(p.collectedOMR, currency, confidentialMode, true),
      formatMoney(p.forecastFinalCostEAC, currency, confidentialMode, true),
      formatPct(p.physicalProgressPct, confidentialMode),
      p.spi !== null ? p.spi.toFixed(2) : 'N/A',
      p.cpi !== null ? p.cpi.toFixed(2) : 'N/A',
    ]),
    theme: 'striped',
    headStyles: { fillColor: [16, 42, 67] },
    styles: { fontSize: 8.5 },
  });

  const afterPrjY = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 20;
  doc.setFontSize(12);
  doc.text('3. Management Commentary & Action Items', 32, afterPrjY);
  doc.setFontSize(9);
  let yCursor = afterPrjY + 16;
  for (const line of commentary.executiveSummary.slice(0, 3)) {
    doc.text(`• ${line}`, 36, yCursor, { maxWidth: 770 });
    yCursor += 18;
  }

  doc.save(`RealEstate360_Board_MIS_${selectedPeriod}.pdf`);
}

export async function exportBoardPowerPoint(
  companyLabel: string,
  statements: FinancialStatements,
  projectKpis: ProjectKpiSummary[],
  commentary: ExecutiveCommentaryBundle,
  selectedPeriod: string,
  basis: ReportingBasis,
  currency: CurrencyCode,
  confidentialMode: boolean
) {
  const pptx = new PptxGenJS();
  pptx.layout = 'LAYOUT_WIDE';

  // Slide 1: Title
  const s1 = pptx.addSlide();
  s1.background = { color: '0B192C' };
  s1.addText('RealEstate 360 — Board MIS Presentation', {
    x: 0.7,
    y: 1.8,
    w: 11.5,
    fontSize: 32,
    bold: true,
    color: 'FFFFFF',
  });
  s1.addText(`${companyLabel}  |  Period ${selectedPeriod}  |  ${basis}  |  ${currency}`, {
    x: 0.7,
    y: 2.6,
    w: 11.5,
    fontSize: 16,
    color: 'D4AF37',
  });
  s1.addText(commentary.headline, {
    x: 0.7,
    y: 3.5,
    w: 11.5,
    fontSize: 14,
    color: 'CBD5E1',
  });

  // Slide 2: Financial Highlights
  const s2 = pptx.addSlide();
  s2.addText(`Consolidated Financial Performance (${selectedPeriod})`, {
    x: 0.5,
    y: 0.4,
    w: 12,
    fontSize: 22,
    bold: true,
    color: '0F172A',
  });
  const finTable: PptxGenJS.TableRow[] = [
    [
      { text: 'Financial Metric', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: `Value (${currency})`, options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'Balance Sheet / Cash Metric', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: `Value (${currency})`, options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
    ],
    [
      { text: 'Recognized Revenue (IFRS 15)' },
      { text: formatMoney(statements.revenue, currency, confidentialMode) },
      { text: 'Unrestricted Cash' },
      { text: formatMoney(statements.cashUnrestricted, currency, confidentialMode) },
    ],
    [
      { text: 'Gross Profit' },
      { text: formatMoney(statements.grossProfit, currency, confidentialMode) },
      { text: 'Restricted Escrow Cash' },
      { text: formatMoney(statements.cashEscrowRestricted, currency, confidentialMode) },
    ],
    [
      { text: 'EBITDA' },
      { text: formatMoney(statements.ebitda, currency, confidentialMode) },
      { text: 'Inventory & WIP (IAS 2)' },
      { text: formatMoney(statements.inventoryWipIAS2, currency, confidentialMode) },
    ],
    [
      { text: 'Net Profit After Tax' },
      { text: formatMoney(statements.netProfit, currency, confidentialMode) },
      { text: 'Net Debt (Excl. Escrow)' },
      { text: formatMoney(statements.netDebt, currency, confidentialMode) },
    ],
  ];
  s2.addTable(finTable, { x: 0.5, y: 1.1, w: 12.2, fontSize: 12, border: { pt: 1, color: 'CBD5E1' } });

  // Slide 3: Project Portfolio
  const s3 = pptx.addSlide();
  s3.addText('Project Portfolio & Delivery Status', {
    x: 0.5,
    y: 0.4,
    w: 12,
    fontSize: 22,
    bold: true,
    color: '0F172A',
  });
  const prjTable: PptxGenJS.TableRow[] = [
    [
      { text: 'Project', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'GDV', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'Contracted', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'Collected', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'Forecast EAC', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'Physical %', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
      { text: 'SPI / CPI', options: { bold: true, fill: { color: '0B192C' }, color: 'FFFFFF' } },
    ],
    ...projectKpis.map((p) => [
      { text: p.project.name },
      { text: formatMoney(p.gdvOMR, currency, confidentialMode, true) },
      { text: formatMoney(p.contractedSalesOMR, currency, confidentialMode, true) },
      { text: formatMoney(p.collectedOMR, currency, confidentialMode, true) },
      { text: formatMoney(p.forecastFinalCostEAC, currency, confidentialMode, true) },
      { text: formatPct(p.physicalProgressPct, confidentialMode) },
      { text: `${p.spi?.toFixed(2) ?? 'N/A'} / ${p.cpi?.toFixed(2) ?? 'N/A'}` },
    ]),
  ];
  s3.addTable(prjTable, { x: 0.5, y: 1.1, w: 12.2, fontSize: 10.5, border: { pt: 1, color: 'CBD5E1' } });

  // Slide 4: Executive Commentary & Action Plan
  const s4 = pptx.addSlide();
  s4.addText('Management Commentary & Priority Actions', {
    x: 0.5,
    y: 0.4,
    w: 12,
    fontSize: 22,
    bold: true,
    color: '0F172A',
  });
  s4.addText(
    commentary.executiveSummary.map((line) => `• ${line}`).join('\n\n'),
    { x: 0.5, y: 1.1, w: 12.2, h: 2.8, fontSize: 12, color: '1E293B', valign: 'top' }
  );
  s4.addText(
    'Action Plan:\n' +
      commentary.actionPlan.map((a) => `• [${a.priority}] ${a.action} — ${a.owner} (${a.deadline})`).join('\n'),
    { x: 0.5, y: 4.1, w: 12.2, h: 2.5, fontSize: 11, color: '334155', valign: 'top' }
  );

  await pptx.writeFile({ fileName: `RealEstate360_Board_Deck_${selectedPeriod}.pptx` });
}

export function exportRowsToCsv(filename: string, headers: string[], rows: (string | number | null)[][]) {
  const escape = (val: string | number | null) => {
    const s = val === null ? 'N/A' : String(val);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [headers.map(escape).join(','), ...rows.map((r) => r.map(escape).join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
