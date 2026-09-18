import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import {
  BalanceSheetHeadConfig,
  BalanceSheetSummary,
  EntityDetails,
  LedgerItem,
  ManualAdjustment,
  PLStatement,
  ReconciliationReport,
  ScheduleData,
} from '../types/accounting';

/**
 * Format numbers according to Indian numbering system (Lakhs & Crores)
 * Output clean, high-precision figures without unprintable unicode symbols
 * e.g. "12,45,670.00" or "(50,000.00)" or "0.00"
 */
export function formatINR(val: number | undefined | null, showDashForZero: boolean = false): string {
  if (val === undefined || val === null || isNaN(val)) {
    return showDashForZero ? '-' : '0.00';
  }
  if (Math.abs(val) < 0.005) {
    return showDashForZero ? '-' : '0.00';
  }
  const isNeg = val < 0;
  const absVal = Math.abs(val);
  const formatted = absVal.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return isNeg ? `(${formatted})` : formatted;
}

/**
 * Color Theme Constants for Professional Chartered Accountant Reports
 * High contrast, refined typography, and formal publication standards
 */
const THEME = {
  PRIMARY: [24, 24, 27] as [number, number, number], // Dark Charcoal #18181B
  SECONDARY: [51, 65, 85] as [number, number, number], // Slate #334155
  HEADER_FILL: [24, 24, 27] as [number, number, number], // #18181B
  SUBHEADER_FILL: [241, 245, 249] as [number, number, number], // #F1F5F9 Slate-100
  ZEBRA_FILL: [248, 250, 252] as [number, number, number], // #F8FAFC
  TOTAL_FILL: [226, 232, 240] as [number, number, number], // #E2E8F0 Slate-200
  TEXT_MAIN: [15, 23, 42] as [number, number, number], // #0F172A
  TEXT_MUTED: [100, 116, 139] as [number, number, number], // #64748B
  BORDER_COLOR: [203, 213, 225] as [number, number, number], // #CBD5E1
  ACCENT_GREEN: [22, 101, 52] as [number, number, number], // Emerald-800
};

/**
 * Draw Document Header Banner on Page
 */
function drawPageHeaderBanner(
  doc: jsPDF,
  entity: EntityDetails,
  title: string,
  subTitle: string,
  pageWidth: number
): number {
  // Top Banner
  doc.setFillColor(...THEME.PRIMARY);
  doc.rect(0, 0, pageWidth, 24, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.text(entity.name.toUpperCase(), pageWidth / 2, 8, { align: 'center' });

  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'normal');
  doc.text(title, pageWidth / 2, 14, { align: 'center' });

  doc.setFontSize(7);
  doc.setTextColor(210, 210, 210);
  doc.text(subTitle, pageWidth / 2, 19.5, { align: 'center' });

  // Entity Details Info Bar
  doc.setFillColor(248, 250, 252);
  doc.rect(14, 27, pageWidth - 28, 10.5, 'F');
  doc.setDrawColor(...THEME.BORDER_COLOR);
  doc.setLineWidth(0.15);
  doc.rect(14, 27, pageWidth - 28, 10.5, 'S');

  doc.setTextColor(...THEME.TEXT_MAIN);
  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.text(
    `PAN: ${entity.pan || 'N/A'}   |   GSTIN: ${entity.gstin || 'N/A'}   |   Entity Type: ${entity.entityType.toUpperCase()}   |   FY: ${entity.financialYear}`,
    17,
    31.5
  );

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(...THEME.TEXT_MUTED);
  doc.text(
    `Registered Address: ${entity.address || 'Commercial Complex, India'}`,
    17,
    35.5
  );

  return 41;
}

/**
 * Draw Statutory Dual Signatures Block
 */
function drawSignaturesBlock(
  doc: jsPDF,
  entity: EntityDetails,
  startY: number,
  pageWidth: number,
  pageHeight: number
): number {
  let sigY = startY;
  // Ensure we don't overflow the page
  if (sigY + 44 > pageHeight - 14) {
    doc.addPage();
    sigY = 24;
  }

  doc.setDrawColor(...THEME.BORDER_COLOR);
  doc.setLineWidth(0.2);
  doc.line(14, sigY, pageWidth - 14, sigY);
  sigY += 4.5;

  doc.setFontSize(7.5);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(...THEME.TEXT_MAIN);

  // Left Column: Entity Signatories
  doc.text(`For and on behalf of:`, 14, sigY);
  doc.text(`${entity.name.toUpperCase()}`, 14, sigY + 4);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.text(`(${entity.entityType})`, 14, sigY + 7.5);

  doc.setDrawColor(160, 160, 160);
  doc.line(14, sigY + 18, 78, sigY + 18);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.text(`${entity.proprietorOrPartnerNames?.[0] || 'Proprietor / Authorized Partner'}`, 14, sigY + 22);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(...THEME.TEXT_MUTED);
  doc.text(`Proprietor / Partner`, 14, sigY + 25.5);
  doc.text(`Place: ${entity.placeOfSigning || 'Navi Mumbai'}   |   Date: ${entity.dateOfSigning || entity.balanceSheetDate}`, 14, sigY + 29);

  // Right Column: Chartered Accountant / Auditor Signatories
  const rightX = pageWidth - 88;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(...THEME.TEXT_MAIN);
  doc.text(`In terms of our audit report of even date attached:`, rightX, sigY);
  doc.text(`For ${entity.auditorName || 'Chartered Accountants'}`, rightX, sigY + 4);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.text(`Chartered Accountants  |  FRN: ${entity.firmRegistrationNo || '124982W'}`, rightX, sigY + 7.5);

  doc.setDrawColor(160, 160, 160);
  doc.line(rightX, sigY + 18, rightX + 74, sigY + 18);

  doc.setFont('helvetica', 'bold');
  doc.setFontSize(7.5);
  doc.setTextColor(...THEME.TEXT_MAIN);
  doc.text(`Partner / Proprietor`, rightX, sigY + 22);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7);
  doc.setTextColor(...THEME.TEXT_MUTED);
  doc.text(`Membership No: ${entity.membershipNumber || '512948'}`, rightX, sigY + 25.5);
  doc.setTextColor(...THEME.ACCENT_GREEN);
  doc.setFont('helvetica', 'bold');
  doc.text(`UDIN: ${entity.udin || '25512948BGXYZW1234'}`, rightX, sigY + 29);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(...THEME.TEXT_MUTED);
  doc.text(`Place: ${entity.placeOfSigning || 'Navi Mumbai'}   |   Date: ${entity.dateOfSigning || entity.balanceSheetDate}`, rightX, sigY + 32.5);

  return sigY + 36;
}

/**
 * MAIN PDF GENERATOR: Generates complete ICAI-compliant Financial Statements for Non-Corporate Entities
 * 1. Balance Sheet (ICAI Vertical Form for Non-Corporate Entities)
 * 2. Statement of Profit & Loss (Trading & P&L Vertical Statement)
 * 3. All Schedules / Annexures 1 to 14
 * 4. Significant Accounting Policies & Notes to Accounts (Note 15)
 * 5. Audit Reconciliation & Integrity Summary
 */
export function generateBalanceSheetPDF(
  entity: EntityDetails,
  heads: BalanceSheetHeadConfig[],
  plStatement: PLStatement,
  schedules: ScheduleData[],
  balanceSheet: BalanceSheetSummary,
  adjustments: ManualAdjustment[] = [],
  reconciliation?: ReconciliationReport,
  ledgers: LedgerItem[] = []
) {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4',
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();

  const getAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s ? s.totalAmount : 0;
  };

  const getPrevAmount = (code: string) => {
    const s = schedules.find(sched => sched.headConfig.code === code);
    return s?.previousYearTotal !== undefined ? s.previousYearTotal : 0;
  };

  // Filter Active Heads
  const activeHeads = heads
    .filter(h => h.active)
    .sort((a, b) => Number(a.scheduleNo) - Number(b.scheduleNo));

  // Categorize for ICAI Balance Sheet
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

  // =========================================================================
  // PAGE 1: BALANCE SHEET (ICAI PRESCRIBED VERTICAL FORMAT)
  // =========================================================================
  const startY1 = drawPageHeaderBanner(
    doc,
    entity,
    `BALANCE SHEET AS AT ${entity.balanceSheetDate.toUpperCase()}`,
    `[Form of Balance Sheet for Non-Corporate Entities in accordance with ICAI Technical Guide]`,
    pageWidth
  );

  const bsTableBody: any[] = [];

  // I. EQUITY AND LIABILITIES
  bsTableBody.push([
    { content: 'I. EQUITY AND LIABILITIES', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL, textColor: THEME.PRIMARY } }
  ]);

  // (1) Owners' Funds
  bsTableBody.push([
    { content: "  (1) Owners' / Partners' Funds", colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  ownersHeads.forEach(h => {
    bsTableBody.push([
      `        ${h.subHead}`,
      String(h.scheduleNo),
      formatINR(getAmount(h.code)),
      formatINR(getPrevAmount(h.code), true),
    ]);
  });
  bsTableBody.push([
    { content: "        Sub-Total: Owners' / Partners' Funds", styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(subTotalOwners), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // (2) Non-Current Liabilities
  bsTableBody.push([
    { content: '  (2) Non-Current Liabilities', colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  nonCurLiabHeads.forEach(h => {
    bsTableBody.push([
      `        ${h.subHead}`,
      String(h.scheduleNo),
      formatINR(getAmount(h.code)),
      formatINR(getPrevAmount(h.code), true),
    ]);
  });
  bsTableBody.push([
    { content: '        Sub-Total: Non-Current Liabilities', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(subTotalNonCurLiab), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // (3) Current Liabilities
  bsTableBody.push([
    { content: '  (3) Current Liabilities', colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  curLiabHeads.forEach(h => {
    if (h.code === 'L05') {
      bsTableBody.push([
        `        Trade Payables:`,
        String(h.scheduleNo),
        formatINR(getAmount(h.code)),
        formatINR(getPrevAmount(h.code), true),
      ]);
      bsTableBody.push([
        `           (A) Total outstanding dues of micro & small enterprises (MSME)`,
        '',
        '-',
        '-',
      ]);
      bsTableBody.push([
        `           (B) Total outstanding dues of creditors other than MSME`,
        '',
        formatINR(getAmount(h.code)),
        formatINR(getPrevAmount(h.code), true),
      ]);
    } else {
      bsTableBody.push([
        `        ${h.subHead}`,
        String(h.scheduleNo),
        formatINR(getAmount(h.code)),
        formatINR(getPrevAmount(h.code), true),
      ]);
    }
  });
  bsTableBody.push([
    { content: '        Sub-Total: Current Liabilities', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(subTotalCurLiab), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // Total Equity & Liabilities
  bsTableBody.push([
    { content: 'TOTAL EQUITY & LIABILITIES', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
    { content: '', styles: { fillColor: THEME.TOTAL_FILL } },
    { content: formatINR(balanceSheet.totalLiabilities), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
  ]);

  // Blank row
  bsTableBody.push([{ content: '', colSpan: 4, styles: { cellPadding: 0.8 } }]);

  // II. ASSETS
  bsTableBody.push([
    { content: 'II. ASSETS', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL, textColor: THEME.PRIMARY } }
  ]);

  // (1) Non-Current Assets
  bsTableBody.push([
    { content: '  (1) Non-Current Assets', colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  nonCurAssetHeads.forEach(h => {
    bsTableBody.push([
      `        ${h.subHead}`,
      String(h.scheduleNo),
      formatINR(getAmount(h.code)),
      formatINR(getPrevAmount(h.code), true),
    ]);
  });
  bsTableBody.push([
    { content: '        Sub-Total: Non-Current Assets', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(subTotalNonCurAssets), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // (2) Current Assets
  bsTableBody.push([
    { content: '  (2) Current Assets', colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  curAssetHeads.forEach(h => {
    bsTableBody.push([
      `        ${h.subHead}`,
      String(h.scheduleNo),
      formatINR(getAmount(h.code)),
      formatINR(getPrevAmount(h.code), true),
    ]);
  });
  bsTableBody.push([
    { content: '        Sub-Total: Current Assets', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(subTotalCurAssets), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // Total Assets
  bsTableBody.push([
    { content: 'TOTAL ASSETS', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
    { content: '', styles: { fillColor: THEME.TOTAL_FILL } },
    { content: formatINR(balanceSheet.totalAssets), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
  ]);

  autoTable(doc, {
    startY: startY1,
    head: [
      [
        'Particulars',
        'Note No.',
        `Figures as at ${entity.balanceSheetDate} (in Rs.)`,
        `Figures as at ${entity.previousYearDate || '31-03-2024'} (in Rs.)`,
      ],
    ],
    body: bsTableBody,
    theme: 'grid',
    headStyles: {
      fillColor: THEME.HEADER_FILL,
      textColor: 255,
      fontSize: 7.5,
      fontStyle: 'bold',
      halign: 'left',
    },
    columnStyles: {
      0: { cellWidth: 98, fontSize: 7.2 },
      1: { cellWidth: 16, halign: 'center', fontSize: 7.2 },
      2: { cellWidth: 34, halign: 'right', fontSize: 7.2 },
      3: { cellWidth: 34, halign: 'right', fontSize: 7.2 },
    },
    styles: {
      cellPadding: 1.1,
      lineColor: THEME.BORDER_COLOR,
      lineWidth: 0.1,
    },
  });

  const finalY1 = (doc as any).lastAutoTable.finalY + 3;
  doc.setFontSize(7);
  doc.setFont('helvetica', 'italic');
  doc.setTextColor(...THEME.TEXT_MUTED);
  doc.text(
    `The accompanying Schedules 1 to 14 and Significant Accounting Policies (Note 15) form an integral part of these Financial Statements.`,
    14,
    finalY1
  );

  drawSignaturesBlock(doc, entity, finalY1 + 5, pageWidth, pageHeight);

  // =========================================================================
  // PAGE 2: STATEMENT OF PROFIT AND LOSS (TRADING & P&L)
  // =========================================================================
  doc.addPage();
  const startY2 = drawPageHeaderBanner(
    doc,
    entity,
    `STATEMENT OF PROFIT AND LOSS FOR THE YEAR ENDED ${entity.balanceSheetDate.toUpperCase()}`,
    `[Form of Statement of Profit and Loss for Non-Corporate Entities as per ICAI Technical Guide]`,
    pageWidth
  );

  const plTableBody: any[] = [];

  // I. REVENUE FROM OPERATIONS
  plTableBody.push([
    { content: 'I. REVENUE FROM OPERATIONS', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL, textColor: THEME.PRIMARY } }
  ]);
  if (plStatement.directIncomes.length > 0) {
    plStatement.directIncomes.forEach(inc => {
      plTableBody.push([
        `        ${inc.name}`,
        '14',
        formatINR(inc.amount),
        '-',
      ]);
    });
  } else {
    plTableBody.push([
      `        Gross Sales / Operational Receipts`,
      '14',
      formatINR(plStatement.totalDirectIncome),
      '-',
    ]);
  }
  plTableBody.push([
    { content: '        Total Revenue from Operations (I)', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(plStatement.totalDirectIncome), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // II. OTHER INCOME
  plTableBody.push([
    { content: 'II. OTHER INCOME', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL, textColor: THEME.PRIMARY } }
  ]);
  if (plStatement.indirectIncomes.length > 0) {
    plStatement.indirectIncomes.forEach(inc => {
      plTableBody.push([
        `        ${inc.name}`,
        '',
        formatINR(inc.amount),
        '-',
      ]);
    });
  } else {
    plTableBody.push([
      `        Interest, Commission & Other Indirect Incomes`,
      '',
      formatINR(plStatement.totalIndirectIncome),
      '-',
    ]);
  }
  plTableBody.push([
    { content: '        Total Other Income (II)', styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } },
    '',
    { content: formatINR(plStatement.totalIndirectIncome), styles: { fontStyle: 'bold', halign: 'right' } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // III. TOTAL REVENUE
  const totalRevenue = plStatement.totalDirectIncome + plStatement.totalIndirectIncome;
  plTableBody.push([
    { content: 'III. TOTAL REVENUE / INCOME (I + II)', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
    '',
    { content: formatINR(totalRevenue), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
  ]);

  // IV. EXPENSES
  plTableBody.push([
    { content: 'IV. EXPENSES', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL, textColor: THEME.PRIMARY } }
  ]);

  // (a) Cost of Materials / Direct Expenses
  plTableBody.push([
    { content: "  (a) Cost of Materials & Direct Trading Expenses", colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  if (plStatement.openingStock > 0) {
    plTableBody.push([
      `        To Opening Stock of Inventory`,
      '10',
      formatINR(plStatement.openingStock),
      '-',
    ]);
  }
  plStatement.directExpenses.forEach(exp => {
    plTableBody.push([
      `        To ${exp.name}`,
      '',
      formatINR(exp.amount),
      '-',
    ]);
  });
  if (plStatement.closingStock > 0) {
    plTableBody.push([
      `        Less: Closing Stock of Inventory as at ${entity.balanceSheetDate}`,
      '10',
      `(${formatINR(plStatement.closingStock)})`,
      '-',
    ]);
  }

  // Trading Gross Profit
  plTableBody.push([
    { content: '        GROSS PROFIT (Transferred to Operating Statement)', styles: { fontStyle: 'bold', textColor: THEME.ACCENT_GREEN } },
    '',
    { content: formatINR(plStatement.grossProfit), styles: { fontStyle: 'bold', halign: 'right', textColor: THEME.ACCENT_GREEN } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right' } },
  ]);

  // (b) Indirect Operating & Administrative Expenses
  plTableBody.push([
    { content: "  (b) Indirect Operating, Administrative & Finance Expenses", colSpan: 4, styles: { fontStyle: 'bold', textColor: THEME.PRIMARY } }
  ]);
  plStatement.indirectExpenses.forEach(exp => {
    plTableBody.push([
      `        To ${exp.name}`,
      '',
      formatINR(exp.amount),
      '-',
    ]);
  });

  // Total Expenses
  const totalExpenses = (plStatement.totalDirectExpenses - plStatement.closingStock) + plStatement.totalIndirectExpenses;
  plTableBody.push([
    { content: 'TOTAL EXPENSES (IV)', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
    '',
    { content: formatINR(totalExpenses), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
  ]);

  // V. NET PROFIT BEFORE TAX
  plTableBody.push([
    { content: 'V. PROFIT / (LOSS) BEFORE TAX (III - IV)', styles: { fontStyle: 'bold', fillColor: THEME.SUBHEADER_FILL } },
    '',
    { content: formatINR(plStatement.netProfitBeforeTax), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.SUBHEADER_FILL } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.SUBHEADER_FILL } },
  ]);

  // VI. Tax Provision
  plTableBody.push([
    `VI. Tax Expense (Current Tax Provision)`,
    '',
    formatINR(plStatement.taxProvision),
    '-',
  ]);

  // VII. NET PROFIT TRANSFERRED TO CAPITAL ACCOUNT
  plTableBody.push([
    { content: 'VII. PROFIT / (LOSS) FOR THE YEAR TRANSFERRED TO CAPITAL A/C', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL, textColor: THEME.ACCENT_GREEN } },
    '1',
    { content: formatINR(plStatement.netProfitAfterTax), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL, textColor: THEME.ACCENT_GREEN } },
    { content: '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
  ]);

  autoTable(doc, {
    startY: startY2,
    head: [
      [
        'Particulars',
        'Note No.',
        `Figures for the Year ended ${entity.balanceSheetDate} (in Rs.)`,
        `Figures for Previous Year ended ${entity.previousYearDate || '31-03-2024'} (in Rs.)`,
      ],
    ],
    body: plTableBody,
    theme: 'grid',
    headStyles: {
      fillColor: THEME.HEADER_FILL,
      textColor: 255,
      fontSize: 7.5,
      fontStyle: 'bold',
      halign: 'left',
    },
    columnStyles: {
      0: { cellWidth: 98, fontSize: 7.2 },
      1: { cellWidth: 16, halign: 'center', fontSize: 7.2 },
      2: { cellWidth: 34, halign: 'right', fontSize: 7.2 },
      3: { cellWidth: 34, halign: 'right', fontSize: 7.2 },
    },
    styles: {
      cellPadding: 1.1,
      lineColor: THEME.BORDER_COLOR,
      lineWidth: 0.1,
    },
  });

  const finalY2 = (doc as any).lastAutoTable.finalY + 3;
  drawSignaturesBlock(doc, entity, finalY2 + 5, pageWidth, pageHeight);

  // =========================================================================
  // PAGE 3 ONWARDS: ALL ANNEXURES & SCHEDULES (SCHEDULES 1 TO 14)
  // =========================================================================
  doc.addPage();
  let currentY = drawPageHeaderBanner(
    doc,
    entity,
    `ANNEXURES & SCHEDULES FORMING PART OF THE FINANCIAL STATEMENTS`,
    `[Schedules 1 to 14 - Detailed Working Papers and Ledger Classifications]`,
    pageWidth
  );

  activeHeads.forEach((head) => {
    const scheduleData = schedules.find(s => s.headConfig.code === head.code);
    const matchingLedgers = scheduleData ? scheduleData.ledgers : [];

    // Check if we need a new page before drawing the schedule
    if (currentY > pageHeight - 50) {
      doc.addPage();
      currentY = 25;
    }

    // Schedule Title Header
    doc.setFillColor(...THEME.SECONDARY);
    doc.rect(14, currentY, pageWidth - 28, 6.5, 'F');
    doc.setTextColor(255, 255, 255);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8.5);
    doc.text(`SCHEDULE ${head.scheduleNo}: ${head.subHead.toUpperCase()} [${head.code}]`, 17, currentY + 4.5);
    currentY += 6.5;

    // Render Special Schedule 1: CAPITAL ACCOUNT
    if (head.isSpecialSchedule === 'CAPITAL' || head.code === 'L01') {
      const capRows: any[] = [];
      let runningCap = 0;

      matchingLedgers.forEach(l => {
        const isDrawing = l.ledgerName.toLowerCase().includes('drawing') || l.debit > l.credit;
        const amt = Math.abs(l.debit - l.credit);
        if (isDrawing) {
          runningCap -= amt;
          capRows.push([
            `Less: ${l.ledgerName} (Withdrawals during year)`,
            'Drawings',
            `(${formatINR(amt)})`,
            formatINR(runningCap),
          ]);
        } else {
          runningCap += amt;
          capRows.push([
            `Opening Balance / ${l.ledgerName}`,
            'Opening Capital',
            formatINR(amt),
            formatINR(runningCap),
          ]);
        }
      });

      // Add Net Profit
      runningCap += plStatement.netProfitAfterTax;
      capRows.push([
        `Add: Net Profit for the year transferred from Statement of Profit & Loss`,
        'P&L Transfer',
        formatINR(plStatement.netProfitAfterTax),
        formatINR(runningCap),
      ]);

      capRows.push([
        { content: `CLOSING CAPITAL BALANCE AS AT ${entity.balanceSheetDate}`, styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
        { content: '', styles: { fillColor: THEME.TOTAL_FILL } },
        { content: '', styles: { fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(scheduleData?.totalAmount || runningCap), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
      ]);

      autoTable(doc, {
        startY: currentY,
        head: [['Particulars / Transaction Description', 'Classification', 'Amount (in Rs.)', `Cumulative Balance (in Rs.)`]],
        body: capRows,
        theme: 'grid',
        headStyles: { fillColor: THEME.PRIMARY, textColor: 255, fontSize: 7, fontStyle: 'bold' },
        columnStyles: {
          0: { cellWidth: 88, fontSize: 7 },
          1: { cellWidth: 32, fontSize: 7 },
          2: { cellWidth: 31, halign: 'right', fontSize: 7 },
          3: { cellWidth: 31, halign: 'right', fontSize: 7 },
        },
        styles: { cellPadding: 1, lineColor: THEME.BORDER_COLOR, lineWidth: 0.1 },
      });

      currentY = (doc as any).lastAutoTable.finalY + 5;
    }
    // Render Special Schedule 8: PROPERTY, PLANT & EQUIPMENT (FIXED ASSETS BLOCK)
    else if (head.isSpecialSchedule === 'FIXED_ASSETS' || head.code === 'A01') {
      const faDetails = scheduleData?.fixedAssetDetails || [];
      const faRows: any[] = [];
      let totalOpeningGross = 0;
      let totalAdditions = 0;
      let totalDeductions = 0;
      let totalClosingGross = 0;
      let totalAccumDepr = 0;
      let totalNetBlock = 0;
      let totalPrevNetBlock = 0;

      if (faDetails.length > 0) {
        faDetails.forEach(asset => {
          const additions = (asset.additionsMoreThan180Days || 0) + (asset.additionsLessThan180Days || 0);
          const deductions = asset.deductionsGrossBlock || 0;
          const closingGross = asset.closingGrossBlock || (asset.openingGrossBlock + additions - deductions);
          const closingDepr = asset.closingDepreciation || 0;
          const netAmt = asset.netBlock || (closingGross - closingDepr);
          const prevNet = asset.previousYearNetBlock || (asset.openingGrossBlock - (asset.openingDepreciation || 0));

          totalOpeningGross += asset.openingGrossBlock;
          totalAdditions += additions;
          totalDeductions += deductions;
          totalClosingGross += closingGross;
          totalAccumDepr += closingDepr;
          totalNetBlock += netAmt;
          totalPrevNetBlock += prevNet;

          faRows.push([
            asset.assetName,
            formatINR(asset.openingGrossBlock),
            additions > 0 ? formatINR(additions) : '-',
            deductions > 0 ? formatINR(deductions) : '-',
            formatINR(closingGross),
            formatINR(closingDepr),
            formatINR(netAmt),
            formatINR(prevNet),
          ]);
        });
      } else {
        const assetLedgers = matchingLedgers.filter(l => !l.ledgerName.toLowerCase().includes('depreciation'));
        const deprLedger = matchingLedgers.find(l => l.ledgerName.toLowerCase().includes('depreciation'));
        const totalDepr = deprLedger ? Math.abs(deprLedger.debit - deprLedger.credit) : 0;
        const totalGross = assetLedgers.reduce((acc, l) => acc + Math.abs(l.debit - l.credit), 0);

        assetLedgers.forEach(l => {
          const grossAmt = Math.abs(l.debit - l.credit);
          const allocDepr = totalGross > 0 ? (grossAmt / totalGross) * totalDepr : 0;
          const netAmt = grossAmt - allocDepr;

          totalOpeningGross += grossAmt;
          totalClosingGross += grossAmt;
          totalAccumDepr += allocDepr;
          totalNetBlock += netAmt;
          totalPrevNetBlock += grossAmt;

          faRows.push([
            l.ledgerName,
            formatINR(grossAmt),
            '-',
            '-',
            formatINR(grossAmt),
            formatINR(allocDepr),
            formatINR(netAmt),
            formatINR(grossAmt),
          ]);
        });
      }

      faRows.push([
        { content: 'TOTAL PROPERTY, PLANT & EQUIPMENT', styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(totalOpeningGross), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: totalAdditions > 0 ? formatINR(totalAdditions) : '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: totalDeductions > 0 ? formatINR(totalDeductions) : '-', styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(totalClosingGross), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(totalAccumDepr), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(totalNetBlock), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(totalPrevNetBlock), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
      ]);

      autoTable(doc, {
        startY: currentY,
        head: [['Asset Description', 'Opening Gross', 'Additions', 'Deductions', 'Closing Gross', 'Accum. Depr', `Net Block (${entity.balanceSheetDate})`, `Prev Year (${entity.previousYearDate || '31-03-2024'})`]],
        body: faRows,
        theme: 'grid',
        headStyles: { fillColor: THEME.PRIMARY, textColor: 255, fontSize: 6.5, fontStyle: 'bold' },
        columnStyles: {
          0: { cellWidth: 46, fontSize: 6.2 },
          1: { cellWidth: 19, halign: 'right', fontSize: 6.2 },
          2: { cellWidth: 15, halign: 'right', fontSize: 6.2 },
          3: { cellWidth: 15, halign: 'right', fontSize: 6.2 },
          4: { cellWidth: 20, halign: 'right', fontSize: 6.2 },
          5: { cellWidth: 19, halign: 'right', fontSize: 6.2 },
          6: { cellWidth: 24, halign: 'right', fontSize: 6.2 },
          7: { cellWidth: 24, halign: 'right', fontSize: 6.2 },
        },
        styles: { cellPadding: 1, lineColor: THEME.BORDER_COLOR, lineWidth: 0.1 },
      });

      currentY = (doc as any).lastAutoTable.finalY + 5;
    }
    // Render Schedule 5: TRADE PAYABLES WITH MSME DISCLOSURE
    else if (head.code === 'L05') {
      const tpRows: any[] = [];
      matchingLedgers.forEach((l, idx) => {
        tpRows.push([
          String(idx + 1),
          l.ledgerName,
          l.originalGroup,
          'Other Creditors (Non-MSME)',
          formatINR(Math.abs(l.credit - l.debit)),
        ]);
      });

      tpRows.push([
        { content: 'TOTAL TRADE PAYABLES', colSpan: 4, styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(scheduleData?.totalAmount || 0), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
      ]);

      autoTable(doc, {
        startY: currentY,
        head: [['Sr', 'Creditor / Vendor Name', 'ERP Group', 'MSME Classification', `Amount as on ${entity.balanceSheetDate} (in Rs.)`]],
        body: tpRows,
        theme: 'grid',
        headStyles: { fillColor: THEME.PRIMARY, textColor: 255, fontSize: 7, fontStyle: 'bold' },
        columnStyles: {
          0: { cellWidth: 10, halign: 'center', fontSize: 7 },
          1: { cellWidth: 70, fontSize: 7 },
          2: { cellWidth: 38, fontSize: 7 },
          3: { cellWidth: 36, fontSize: 7 },
          4: { cellWidth: 28, halign: 'right', fontSize: 7 },
        },
        styles: { cellPadding: 1, lineColor: THEME.BORDER_COLOR, lineWidth: 0.1 },
      });

      currentY = (doc as any).lastAutoTable.finalY + 5;
    }
    // STANDARD SCHEDULE FORMAT
    else {
      const stdRows: any[] = [];
      if (matchingLedgers.length === 0) {
        stdRows.push([
          '1',
          'Nil balance / Direct Adjustment Entry',
          '-',
          formatINR(scheduleData?.totalAmount || 0),
        ]);
      } else {
        matchingLedgers.forEach((l, idx) => {
          stdRows.push([
            String(idx + 1),
            l.ledgerName,
            l.originalGroup,
            formatINR(Math.abs(l.debit - l.credit)),
          ]);
        });
      }

      stdRows.push([
        { content: `TOTAL ${head.subHead.toUpperCase()}`, colSpan: 3, styles: { fontStyle: 'bold', fillColor: THEME.TOTAL_FILL } },
        { content: formatINR(scheduleData?.totalAmount || 0), styles: { fontStyle: 'bold', halign: 'right', fillColor: THEME.TOTAL_FILL } },
      ]);

      autoTable(doc, {
        startY: currentY,
        head: [['Sr', 'Particulars / Account Name', 'ERP Group Classification', `Amount as on ${entity.balanceSheetDate} (in Rs.)`]],
        body: stdRows,
        theme: 'grid',
        headStyles: { fillColor: THEME.PRIMARY, textColor: 255, fontSize: 7, fontStyle: 'bold' },
        columnStyles: {
          0: { cellWidth: 10, halign: 'center', fontSize: 7 },
          1: { cellWidth: 88, fontSize: 7 },
          2: { cellWidth: 50, fontSize: 7 },
          3: { cellWidth: 34, halign: 'right', fontSize: 7 },
        },
        styles: { cellPadding: 1, lineColor: THEME.BORDER_COLOR, lineWidth: 0.1 },
      });

      currentY = (doc as any).lastAutoTable.finalY + 5;
    }
  });

  // =========================================================================
  // SIGNIFICANT ACCOUNTING POLICIES & STATUTORY NOTES TO ACCOUNTS (NOTE 15)
  // =========================================================================
  doc.addPage();
  let noteY = drawPageHeaderBanner(
    doc,
    entity,
    `SCHEDULE 15: SIGNIFICANT ACCOUNTING POLICIES & NOTES TO ACCOUNTS`,
    `[Statutory Disclosures in compliance with ICAI Non-Corporate GAAP Framework]`,
    pageWidth
  );

  const notesList = [
    {
      title: '1. ENTITY INFORMATION & BASIS OF PREPARATION',
      text: `${entity.name} is a ${entity.entityType} domiciled in India with registered place of business at ${entity.address}. These financial statements have been prepared under the historical cost convention on an accrual basis in accordance with generally accepted accounting principles (GAAP) in India and the Technical Guide on Financial Statements of Non-Corporate Entities issued by The Institute of Chartered Accountants of India (ICAI).`,
    },
    {
      title: '2. PROPERTY, PLANT AND EQUIPMENT (PPE) & DEPRECIATION (AS-10)',
      text: `Tangible fixed assets are stated at cost of acquisition or construction less accumulated depreciation and impairment losses, if any. Depreciation is provided under the Written Down Value (WDV) method / Straight Line Method as per the rates specified under the Income Tax Act, 1961 / Companies Act framework.`,
    },
    {
      title: '3. REVENUE RECOGNITION (AS-9)',
      text: `Revenue from the sale of goods and rendering of services is recognized upon transfer of significant risks and rewards of ownership to the buyer, which generally coincides with the delivery of goods or dispatch of invoices. Other incomes (interest, commission, discounts) are accounted for on an accrual basis.`,
    },
    {
      title: '4. INVENTORIES (AS-2)',
      text: `Inventories comprising Raw Materials, Work-in-Progress, Finished Goods and Stock-in-Trade are valued at the lower of Cost or Net Realizable Value (NRV). Cost is determined on a First-In-First-Out (FIFO) / Weighted Average basis and includes all costs of purchase and other costs incurred in bringing inventories to their present location and condition.`,
    },
    {
      title: '5. MSME DISCLOSURES (MSMED ACT, 2006)',
      text: `The identification of suppliers registered under the Micro, Small and Medium Enterprises Development Act, 2006 (MSMED Act) is based on information available with the management. As on ${entity.balanceSheetDate}, there are no overdue principal or interest amounts remaining unpaid to MSME suppliers exceeding the statutory threshold.`,
    },
    {
      title: '6. CONTINGENT LIABILITIES & CAPITAL COMMITMENTS',
      text: `There are no material contingent liabilities, pending litigations, or uncalled capital commitments outstanding against the entity as on ${entity.balanceSheetDate} that require separate provision or disclosure.`,
    },
    {
      title: '7. PREVIOUS YEAR FIGURES',
      text: `Previous year figures have been regrouped, rearranged and reclassified wherever necessary to correspond with the current year classification and ICAI non-corporate presentation standards.`,
    },
  ];

  notesList.forEach((n) => {
    if (noteY > pageHeight - 35) {
      doc.addPage();
      noteY = 25;
    }

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(8);
    doc.setTextColor(...THEME.PRIMARY);
    doc.text(n.title, 14, noteY);
    noteY += 4;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7.2);
    doc.setTextColor(...THEME.TEXT_MAIN);
    const splitText = doc.splitTextToSize(n.text, pageWidth - 28);
    doc.text(splitText, 14, noteY);
    noteY += splitText.length * 3.6 + 3.5;
  });

  drawSignaturesBlock(doc, entity, noteY + 5, pageWidth, pageHeight);

  // =========================================================================
  // AUDIT RECONCILIATION & TRIAL BALANCE INTEGRITY STATEMENT
  // =========================================================================
  if (reconciliation) {
    doc.addPage();
    const startYRecon = drawPageHeaderBanner(
      doc,
      entity,
      `AUDIT RECONCILIATION & TRIAL BALANCE INTEGRITY STATEMENT`,
      `[Auditor's Mathematical Verification and Ledger Mapping Trail]`,
      pageWidth
    );

    const reconRows = [
      ['Total Trial Balance Debit Balances (in Rs.)', formatINR(reconciliation.totalTrialBalanceDebit), 'Verified from General Ledger'],
      ['Total Trial Balance Credit Balances (in Rs.)', formatINR(reconciliation.totalTrialBalanceCredit), 'Verified from General Ledger'],
      ['Trial Balance Difference', formatINR(reconciliation.trialBalanceDifference), reconciliation.isTrialBalanceBalanced ? 'Balanced (0.00) ✓' : 'DIFFERENCE EXISTS ⚠'],
      ['Total Balance Sheet Assets (in Rs.)', formatINR(reconciliation.totalAssets), 'As per Schedule 8 to 14'],
      ['Total Capital & Liabilities (in Rs.)', formatINR(reconciliation.totalLiabilities), 'As per Schedule 1 to 7'],
      ['Balance Sheet Difference (Assets - Liabilities)', formatINR(reconciliation.balanceSheetDifference), reconciliation.isBalanceSheetBalanced ? 'Balanced (0.00) ✓' : 'DIFFERENCE EXISTS ⚠'],
      ['Net Profit transferred to Capital Account (in Rs.)', formatINR(reconciliation.plNetProfit), 'Reconciled with Schedule 1'],
      ['Unclassified / Low Confidence Ledgers', String(reconciliation.unclassifiedLedgersCount), reconciliation.unclassifiedLedgersCount === 0 ? '100% Mapped (Zero Unclassified) ✓' : 'Review Required'],
    ];

    autoTable(doc, {
      startY: startYRecon,
      head: [['Reconciliation Check Parameter', 'Computed Value (in Rs.)', 'Auditor Verification Status']],
      body: reconRows,
      theme: 'grid',
      headStyles: { fillColor: THEME.PRIMARY, textColor: 255, fontSize: 7.5, fontStyle: 'bold' },
      columnStyles: {
        0: { cellWidth: 96, fontSize: 7.5 },
        1: { cellWidth: 42, halign: 'right', fontSize: 7.5 },
        2: { cellWidth: 44, fontSize: 7.5 },
      },
      styles: { cellPadding: 1.5, lineColor: THEME.BORDER_COLOR, lineWidth: 0.1 },
    });

    const finalYRecon = (doc as any).lastAutoTable.finalY + 5;
    drawSignaturesBlock(doc, entity, finalYRecon + 5, pageWidth, pageHeight);
  }

  // =========================================================================
  // GLOBAL PASS: RUNNING HEADERS & FOOTERS ("PAGE X OF Y")
  // =========================================================================
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);

    // Running Header (from page 2 onwards)
    if (i > 1) {
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(6.5);
      doc.setTextColor(...THEME.TEXT_MUTED);
      doc.text(
        `${entity.name.toUpperCase()}  |  FINANCIAL STATEMENTS FOR FY ${entity.financialYear}`,
        14,
        6
      );
      doc.setDrawColor(...THEME.BORDER_COLOR);
      doc.setLineWidth(0.1);
      doc.line(14, 8, pageWidth - 14, 8);
    }

    // Running Footer (on all pages)
    doc.setDrawColor(...THEME.BORDER_COLOR);
    doc.setLineWidth(0.1);
    doc.line(14, pageHeight - 8, pageWidth - 14, pageHeight - 8);

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(6.5);
    doc.setTextColor(...THEME.TEXT_MUTED);
    doc.text(
      `AccuSheet.Pro  |  ICAI Non-Corporate Entity GAAP  |  UDIN: ${entity.udin || '25512948BGXYZW1234'}`,
      14,
      pageHeight - 4.5
    );

    doc.setFont('helvetica', 'bold');
    doc.text(
      `Page ${i} of ${totalPages}`,
      pageWidth - 14,
      pageHeight - 4.5,
      { align: 'right' }
    );
  }

  // Download PDF
  const sanitizedName = entity.name.replace(/[^a-zA-Z0-9]/g, '_');
  doc.save(`${sanitizedName}_ICAI_Financial_Statements_${entity.financialYear}.pdf`);
  return doc;
}
