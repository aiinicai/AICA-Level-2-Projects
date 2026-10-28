import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import * as XLSX from 'xlsx';
import { Company, FinancialStatement, FinancialRatios, CreditAssessment, RedFlag, User } from '../types/financial';

/**
 * Generates an institutional-grade PDF Credit Assessment Report (Credit Appraisal Memo - CAM)
 * Implements Section 9: PDF Credit Assessment Report
 */
export function generatePdfReport(
  company: Company,
  statements: FinancialStatement[],
  ratios: FinancialRatios,
  assessment: CreditAssessment,
  redFlags: RedFlag[],
  analyst?: User
): jsPDF {
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;

  // Colors
  const primaryNavy: [number, number, number] = [15, 23, 42]; // #0f172a
  const accentBlue: [number, number, number] = [30, 58, 138]; // #1e3a8a
  const textDark: [number, number, number] = [30, 41, 59];
  const textMuted: [number, number, number] = [100, 116, 139];
  const bgLight: [number, number, number] = [248, 250, 252];

  // Grade color
  let gradeBg: [number, number, number] = [16, 185, 129]; // green
  if (assessment.recommendation === 'Conditional Approval') gradeBg = [217, 119, 6]; // amber
  else if (assessment.recommendation === 'Review Required') gradeBg = [234, 88, 12]; // orange
  else if (assessment.recommendation === 'Reject') gradeBg = [225, 29, 72]; // rose

  // Page 1: Header Banner
  doc.setFillColor(...primaryNavy);
  doc.rect(0, 0, pageWidth, 32, 'F');

  // Title
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(16);
  doc.text('CREDIT APPRAISAL MEMORANDUM (CAM)', margin, 14);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9);
  doc.setTextColor(203, 213, 225);
  doc.text(`CONFIDENTIAL LENDER REPORT | REFERENCE: ${assessment.id}`, margin, 20);
  doc.text(`ASSESSMENT DATE: ${assessment.assessmentDate} | FINANCIAL YEAR: ${assessment.financialYear}`, margin, 25);

  // Recommendation Badge on top right
  doc.setFillColor(...gradeBg);
  doc.roundedRect(pageWidth - margin - 50, 8, 50, 16, 2, 2, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(10);
  doc.text(assessment.recommendation.toUpperCase(), pageWidth - margin - 25, 18, { align: 'center' });

  let y = 40;

  // Section 1: Executive Summary & Company Overview
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('1. Executive Summary & Borrower Profile', margin + 6, y + 5.5);
  y += 11;

  // Borrower info table
  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    theme: 'grid',
    styles: { fontSize: 8.5, cellPadding: 3, textColor: textDark },
    headStyles: { fillColor: [241, 245, 249], textColor: textDark, fontStyle: 'bold' },
    body: [
      [
        { content: 'Borrower Name:', styles: { fontStyle: 'bold' as const } }, company.companyName,
        { content: 'Corporate ID (CIN):', styles: { fontStyle: 'bold' as const } }, company.cin
      ],
      [
        { content: 'Industry / Sector:', styles: { fontStyle: 'bold' as const } }, company.industry,
        { content: 'Income Tax PAN:', styles: { fontStyle: 'bold' as const } }, company.pan
      ],
      [
        { content: 'Established Year:', styles: { fontStyle: 'bold' as const } }, String(company.yearEstablished),
        { content: 'Annual Turnover:', styles: { fontStyle: 'bold' as const } }, `INR ${company.annualTurnover} Crores`
      ],
      [
        { content: 'Registered Office:', styles: { fontStyle: 'bold' as const }, colSpan: 3 }
      ]
    ]
  });

  y = (doc as any).lastAutoTable.finalY + 8;

  // Section 2: Credit Rating & Health Score Card
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('2. Credit Assessment & Health Score Matrix', margin + 6, y + 5.5);
  y += 11;

  // Summary Metrics Cards (Drawn visually)
  const cardWidth = (pageWidth - margin * 2 - 9) / 4;
  const metrics = [
    { label: 'HEALTH SCORE', val: `${assessment.healthScore.totalScore}/100`, sub: assessment.healthScore.rating },
    { label: 'CREDIT GRADE', val: assessment.creditGrade, sub: assessment.riskLevel },
    { label: 'RECOMMENDED LIMIT', val: `INR ${assessment.recommendedCreditLimit} Cr`, sub: 'Max Exposure' },
    { label: 'RECOMMENDED PRICING', val: assessment.recommendedInterestSpread.split(' ')[0] + ' ' + (assessment.recommendedInterestSpread.split(' ')[1] || ''), sub: 'Benchmark Spread' }
  ];

  metrics.forEach((m, idx) => {
    const cx = margin + idx * (cardWidth + 3);
    doc.setFillColor(...bgLight);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(cx, y, cardWidth, 20, 2, 2, 'FD');

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(...textMuted);
    doc.text(m.label, cx + cardWidth / 2, y + 5.5, { align: 'center' });

    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.setTextColor(...accentBlue);
    doc.text(m.val, cx + cardWidth / 2, y + 12, { align: 'center' });

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(...textDark);
    doc.text(m.sub, cx + cardWidth / 2, y + 17, { align: 'center' });
  });

  y += 24;

  // Scoring Breakdown Table
  const scoreRows = assessment.healthScore.categories.map(c => [
    c.category,
    `${c.weight}%`,
    `${c.score}/100`,
    `${c.weightedScore} / 25`,
    c.grade,
    c.keyDriver
  ]);

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    theme: 'striped',
    styles: { fontSize: 8, cellPadding: 2.5 },
    headStyles: { fillColor: accentBlue, textColor: [255, 255, 255], fontStyle: 'bold' },
    head: [['Scoring Category', 'Weight', 'Raw Score', 'Weighted Score', 'Health Grade', 'Key Indicator Drivers']],
    body: scoreRows
  });

  y = (doc as any).lastAutoTable.finalY + 8;

  // Section 3: Ratio Summary Table (Comparative)
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('3. Key Financial Ratios & Benchmark Comparison', margin + 6, y + 5.5);
  y += 11;

  const ratioData = ratios.items.map(r => [
    r.category,
    r.name,
    r.formula,
    r.formattedValue,
    r.benchmark,
    r.status.toUpperCase(),
    r.interpretation
  ]);

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    theme: 'grid',
    styles: { fontSize: 7.5, cellPadding: 2 },
    headStyles: { fillColor: primaryNavy, textColor: [255, 255, 255], fontStyle: 'bold' },
    head: [['Category', 'Ratio Name', 'Formula', 'Value', 'Benchmark', 'Status', 'Clinical Interpretation']],
    body: ratioData,
    didParseCell: function(data) {
      if (data.section === 'body' && data.column.index === 5) {
        if (data.cell.raw === 'HEALTHY') data.cell.styles.textColor = [16, 185, 129];
        else if (data.cell.raw === 'MODERATE') data.cell.styles.textColor = [217, 119, 6];
        else if (data.cell.raw === 'RISK') data.cell.styles.textColor = [225, 29, 72];
      }
    }
  });

  // PAGE 2: Red Flags, Covenants, Multi-Year Financials & Sign-off
  doc.addPage();
  y = 15;

  // Header Banner Page 2
  doc.setFillColor(...primaryNavy);
  doc.rect(0, 0, pageWidth, 16, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text(`CREDIT ASSESSMENT REPORT - ${company.companyName.toUpperCase()}`, margin, 11);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.text(`PAGE 2 | RATING: ${assessment.creditGrade} (${assessment.recommendation})`, pageWidth - margin, 11, { align: 'right' });

  y = 24;

  // Section 4: Red Flag Risk Analysis
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('4. Red Flag Detection & Risk Mitigation', margin + 6, y + 5.5);
  y += 11;

  if (redFlags.length === 0) {
    doc.setFillColor(240, 253, 244);
    doc.setDrawColor(187, 247, 208);
    doc.roundedRect(margin, y, pageWidth - margin * 2, 12, 2, 2, 'FD');
    doc.setTextColor(22, 101, 52);
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(9);
    doc.text('✓ ZERO CRITICAL RED FLAGS DETECTED', margin + 5, y + 7.5);
    y += 18;
  } else {
    const redFlagRows = redFlags.map(rf => [
      rf.severity.toUpperCase(),
      rf.category,
      rf.title,
      `${rf.metric}: ${rf.actualValue} (Rule: ${rf.threshold})`,
      rf.recommendation
    ]);

    autoTable(doc, {
      startY: y,
      margin: { left: margin, right: margin },
      theme: 'grid',
      styles: { fontSize: 7.5, cellPadding: 2.5 },
      headStyles: { fillColor: [185, 28, 28], textColor: [255, 255, 255], fontStyle: 'bold' },
      head: [['Severity', 'Category', 'Risk Flag', 'Trigger Condition', 'Mandatory Risk Mitigation']],
      body: redFlagRows
    });

    y = (doc as any).lastAutoTable.finalY + 8;
  }

  // Section 5: Strengths & Weaknesses
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('5. Financial Strengths & Weaknesses Assessment', margin + 6, y + 5.5);
  y += 11;

  const colW = (pageWidth - margin * 2 - 6) / 2;
  
  // Strengths column
  doc.setFillColor(240, 253, 244);
  doc.setDrawColor(187, 247, 208);
  doc.roundedRect(margin, y, colW, 32, 2, 2, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(22, 101, 52);
  doc.text('KEY FINANCIAL STRENGTHS', margin + 4, y + 6);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(30, 41, 59);
  let sy = y + 11;
  (assessment.strengths.length > 0 ? assessment.strengths : ['Adequate operating scale']).slice(0, 3).forEach(str => {
    doc.text(`• ${str}`, margin + 4, sy);
    sy += 6;
  });

  // Weaknesses column
  const wx = margin + colW + 6;
  doc.setFillColor(254, 242, 242);
  doc.setDrawColor(254, 202, 202);
  doc.roundedRect(wx, y, colW, 32, 2, 2, 'FD');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(9);
  doc.setTextColor(153, 27, 27);
  doc.text('KEY FINANCIAL WEAKNESSES', wx + 4, y + 6);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(30, 41, 59);
  let wy = y + 11;
  (assessment.weaknesses.length > 0 ? assessment.weaknesses : ['No significant structural impairment']).slice(0, 3).forEach(wk => {
    doc.text(`• ${wk}`, wx + 4, wy);
    wy += 6;
  });

  y += 38;

  // Section 6: Sanction Covenants & Recommendation
  doc.setFillColor(...accentBlue);
  doc.rect(margin, y, 3, 7, 'F');
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(12);
  doc.setTextColor(...textDark);
  doc.text('6. Recommended Sanction Covenants & Facility Terms', margin + 6, y + 5.5);
  y += 11;

  const covRows = [
    [{ content: 'Collateral & Margin Requirement:', styles: { fontStyle: 'bold' as const } }, assessment.collateralRequirement],
    [{ content: 'Pricing & Risk Spread:', styles: { fontStyle: 'bold' as const } }, assessment.recommendedInterestSpread],
    ...assessment.covenants.map(c => [{ content: 'Key Covenant:', styles: { fontStyle: 'bold' as const } }, c])
  ];

  autoTable(doc, {
    startY: y,
    margin: { left: margin, right: margin },
    theme: 'striped',
    styles: { fontSize: 8, cellPadding: 2.5 },
    headStyles: { fillColor: primaryNavy, textColor: [255, 255, 255], fontStyle: 'bold' },
    body: covRows
  });

  y = (doc as any).lastAutoTable.finalY + 12;

  // Sign-off signature block
  doc.setDrawColor(203, 213, 225);
  doc.line(margin, y, pageWidth - margin, y);
  y += 6;

  const signCol = (pageWidth - margin * 2) / 3;
  
  // Box 1
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(...textDark);
  doc.text('PREPARED BY', margin, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(...textMuted);
  doc.text(analyst ? `${analyst.name} (${analyst.role})` : 'Certified Credit Analyst', margin, y + 5);
  doc.text(analyst ? analyst.organization : 'Financial Analytics Division', margin, y + 9);
  doc.text('Signature: __________________', margin, y + 17);

  // Box 2
  const b2x = margin + signCol;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(...textDark);
  doc.text('RISK REVIEWED BY', b2x, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(...textMuted);
  doc.text('Chief Risk Officer / Lead CA', b2x, y + 5);
  doc.text('Credit Risk Management Dept', b2x, y + 9);
  doc.text('Signature: __________________', b2x, y + 17);

  // Box 3
  const b3x = margin + signCol * 2;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(8);
  doc.setTextColor(...textDark);
  doc.text('SANCTIONING AUTHORITY', b3x, y);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(7.5);
  doc.setTextColor(...textMuted);
  doc.text('Credit Approval Committee', b3x, y + 5);
  doc.text('Decision: ' + assessment.recommendation.toUpperCase(), b3x, y + 9);
  doc.text('Seal / Stamp: _______________', b3x, y + 17);

  // Page Numbers
  const totalPages = doc.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(7);
    doc.setTextColor(148, 163, 184);
    doc.text(`CrediMetrics Financial Intelligence System | Generated for Institutional Use Only`, margin, pageHeight - 6);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - margin, pageHeight - 6, { align: 'right' });
  }

  return doc;
}

/**
 * Downloads the PDF directly to the user's computer
 */
export function downloadPdfReport(
  company: Company,
  statements: FinancialStatement[],
  ratios: FinancialRatios,
  assessment: CreditAssessment,
  redFlags: RedFlag[],
  analyst?: User
): void {
  const doc = generatePdfReport(company, statements, ratios, assessment, redFlags, analyst);
  const fileName = `${company.companyName.replace(/[^a-zA-Z0-9]/g, '_')}_Credit_Assessment_Report_${ratios.financialYear.replace(/\s+/g, '_')}.pdf`;
  doc.save(fileName);
}

/**
 * Generates and downloads an Excel financial model with multiple sheets:
 * Sheet 1: Company Profile & Credit Assessment Summary
 * Sheet 2: Financial Statements (Balance Sheet & P&L)
 * Sheet 3: Financial Ratio Calculations & Benchmarks
 * Sheet 4: Red Flag Risk Analysis
 */
export function downloadExcelFinancialModel(
  company: Company,
  statements: FinancialStatement[],
  ratios: FinancialRatios,
  assessment: CreditAssessment,
  redFlags: RedFlag[]
): void {
  const wb = XLSX.utils.book_new();

  // 1. Summary Sheet
  const summaryData = [
    ['CREDIT APPRAISAL SUMMARY & RATING MEMORANDUM'],
    ['Company Name', company.companyName],
    ['Corporate ID (CIN)', company.cin],
    ['PAN', company.pan],
    ['Industry Sector', company.industry],
    ['Annual Turnover (INR Cr)', company.annualTurnover],
    ['Established Year', company.yearEstablished],
    ['Registered Office', company.address],
    [''],
    ['CREDIT UNDERWRITING DECISION'],
    ['Recommendation', assessment.recommendation],
    ['Credit Grade', assessment.creditGrade],
    ['Risk Level', assessment.riskLevel],
    ['Financial Health Score (out of 100)', assessment.healthScore.totalScore],
    ['Overall Rating', assessment.healthScore.rating],
    ['Recommended Max Credit Exposure (INR Cr)', assessment.recommendedCreditLimit],
    ['Recommended Interest Spread', assessment.recommendedInterestSpread],
    ['Collateral Requirement', assessment.collateralRequirement],
    [''],
    ['HEALTH SCORE COMPONENT BREAKDOWN (25% EACH)'],
    ['Category', 'Weight (%)', 'Raw Score (0-100)', 'Weighted Score', 'Health Grade', 'Key Indicator Drivers'],
    ...assessment.healthScore.categories.map(c => [
      c.category,
      c.weight,
      c.score,
      c.weightedScore,
      c.grade,
      c.keyDriver
    ]),
    [''],
    ['SANCTION COVENANTS'],
    ...assessment.covenants.map(c => ['Covenant Condition', c])
  ];
  const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
  XLSX.utils.book_append_sheet(wb, wsSummary, 'Credit Appraisal');

  // 2. Financial Statements Sheet (Multi-Year)
  const stmtHeaders = ['Financial Line Item (in INR Crores)', ...statements.map(s => s.financialYear)];
  const stmtRows = [
    stmtHeaders,
    ['--- BALANCE SHEET: ASSETS ---'],
    ['Cash & Cash Equivalents', ...statements.map(s => s.balanceSheet.cash)],
    ['Bank Balances', ...statements.map(s => s.balanceSheet.bank)],
    ['Trade Receivables (Debtors)', ...statements.map(s => s.balanceSheet.receivables)],
    ['Inventories / Stock', ...statements.map(s => s.balanceSheet.inventory)],
    ['Other Current Assets', ...statements.map(s => s.balanceSheet.otherCurrentAssets)],
    ['Total Current Assets', ...statements.map(s => s.balanceSheet.cash + s.balanceSheet.bank + s.balanceSheet.receivables + s.balanceSheet.inventory + s.balanceSheet.otherCurrentAssets)],
    ['Fixed Assets (Net Property, Plant & Equip)', ...statements.map(s => s.balanceSheet.fixedAssets)],
    ['Non-Current Investments', ...statements.map(s => s.balanceSheet.investments)],
    ['TOTAL ASSETS', ...statements.map(s => s.balanceSheet.totalAssets)],
    [''],
    ['--- BALANCE SHEET: LIABILITIES & EQUITY ---'],
    ['Trade Payables (Creditors)', ...statements.map(s => s.balanceSheet.payables)],
    ['Short-Term Debt & Bank Borrowings', ...statements.map(s => s.balanceSheet.shortTermDebt)],
    ['Other Current Liabilities', ...statements.map(s => s.balanceSheet.otherCurrentLiabilities)],
    ['Total Current Liabilities', ...statements.map(s => s.balanceSheet.payables + s.balanceSheet.shortTermDebt + s.balanceSheet.otherCurrentLiabilities)],
    ['Long-Term Borrowings / Debt', ...statements.map(s => s.balanceSheet.longTermDebt)],
    ['Share Capital (Equity)', ...statements.map(s => s.balanceSheet.equity)],
    ['Reserves & Surplus', ...statements.map(s => s.balanceSheet.reserves)],
    ['Total Net Worth (Equity + Reserves)', ...statements.map(s => s.balanceSheet.equity + s.balanceSheet.reserves)],
    ['TOTAL LIABILITIES & EQUITY', ...statements.map(s => s.balanceSheet.totalLiabilities)],
    [''],
    ['--- PROFIT & LOSS STATEMENT ---'],
    ['Revenue from Operations (Gross Sales)', ...statements.map(s => s.profitAndLoss.revenue)],
    ['Other Operating Income', ...statements.map(s => s.profitAndLoss.otherIncome)],
    ['Cost of Goods Sold (COGS)', ...statements.map(s => s.profitAndLoss.cogs)],
    ['Gross Profit', ...statements.map(s => s.profitAndLoss.grossProfit)],
    ['Operating Expenses (SG&A)', ...statements.map(s => s.profitAndLoss.operatingExpenses)],
    ['EBITDA', ...statements.map(s => s.profitAndLoss.ebitda)],
    ['Depreciation & Amortization', ...statements.map(s => s.profitAndLoss.depreciation)],
    ['Operating Profit (EBIT)', ...statements.map(s => s.profitAndLoss.ebit)],
    ['Interest & Finance Charges', ...statements.map(s => s.profitAndLoss.interestExpense)],
    ['Profit Before Tax (PBT)', ...statements.map(s => s.profitAndLoss.profitBeforeTax)],
    ['Tax Expense', ...statements.map(s => s.profitAndLoss.taxExpense)],
    ['Net Profit After Tax (PAT)', ...statements.map(s => s.profitAndLoss.netProfit)]
  ];
  const wsStatements = XLSX.utils.aoa_to_sheet(stmtRows);
  XLSX.utils.book_append_sheet(wb, wsStatements, 'Financial Statements');

  // 3. Ratios Sheet
  const ratioHeaders = ['Ratio Category', 'Ratio Name', 'Formula', 'Value', 'Benchmark Target', 'Status', 'Clinical Interpretation'];
  const ratioRows = [
    ratioHeaders,
    ...ratios.items.map(r => [
      r.category,
      r.name,
      r.formula,
      r.formattedValue,
      r.benchmark,
      r.status,
      r.interpretation
    ])
  ];
  const wsRatios = XLSX.utils.aoa_to_sheet(ratioRows);
  XLSX.utils.book_append_sheet(wb, wsRatios, 'Ratio Analysis');

  // 4. Red Flags Sheet
  const flagHeaders = ['Severity', 'Risk Category', 'Warning Title', 'Trigger Metric', 'Actual Value', 'Rule Threshold', 'Mandatory Mitigation'];
  const flagRows = [
    flagHeaders,
    ...redFlags.map(rf => [
      rf.severity,
      rf.category,
      rf.title,
      rf.metric,
      rf.actualValue,
      rf.threshold,
      rf.recommendation
    ])
  ];
  const wsFlags = XLSX.utils.aoa_to_sheet(flagRows);
  XLSX.utils.book_append_sheet(wb, wsFlags, 'Red Flag Matrix');

  const fileName = `${company.companyName.replace(/[^a-zA-Z0-9]/g, '_')}_Financial_Model_${ratios.financialYear.replace(/\s+/g, '_')}.xlsx`;
  XLSX.writeFile(wb, fileName);
}

/**
 * Downloads a standardized Blank Excel Template for financial uploads
 */
export function downloadSampleUploadTemplate(): void {
  const wb = XLSX.utils.book_new();

  const templateRows = [
    ['FINANCIAL STATEMENT DATA IMPORT TEMPLATE (IN INR CRORES)'],
    ['Instructions: Fill your data into the corresponding columns for each financial year. Do not rename the line items in column A.'],
    [''],
    ['Line Item', 'FY 2023', 'FY 2024', 'FY 2025'],
    ['Revenue', 120.50, 145.20, 168.80],
    ['COGS', 72.30, 84.10, 95.40],
    ['Gross Profit', 48.20, 61.10, 73.40],
    ['Operating Expenses', 24.10, 29.00, 32.50],
    ['EBITDA', 24.10, 32.10, 40.90],
    ['Depreciation', 4.50, 5.20, 6.00],
    ['EBIT', 19.60, 26.90, 34.90],
    ['Interest Expense', 3.20, 3.50, 3.80],
    ['Profit Before Tax', 16.40, 23.40, 31.10],
    ['Tax Expense', 4.10, 5.85, 7.78],
    ['Net Profit', 12.30, 17.55, 23.32],
    [''],
    ['Cash', 5.20, 6.40, 8.10],
    ['Bank', 12.50, 15.00, 18.50],
    ['Receivables', 22.00, 26.50, 29.80],
    ['Inventory', 18.40, 21.20, 24.00],
    ['Other Current Assets', 4.00, 4.80, 5.20],
    ['Fixed Assets', 45.00, 52.00, 58.00],
    ['Investments', 6.00, 8.00, 10.00],
    ['Total Assets', 113.10, 133.90, 153.60],
    [''],
    ['Payables', 14.50, 17.20, 19.50],
    ['Short Term Debt', 8.00, 9.50, 10.20],
    ['Other Current Liabilities', 3.50, 4.20, 4.80],
    ['Long Term Debt', 28.00, 31.00, 32.00],
    ['Equity', 20.00, 20.00, 20.00],
    ['Reserves', 39.10, 52.00, 67.10],
    ['Total Liabilities', 113.10, 133.90, 153.60]
  ];

  const ws = XLSX.utils.aoa_to_sheet(templateRows);
  XLSX.utils.book_append_sheet(wb, ws, 'Financial Statements');
  XLSX.writeFile(wb, 'CrediMetrics_Financial_Upload_Template.xlsx');
}

/**
 * Downloads a complete JSON data export
 */
export function downloadJsonAssessment(
  company: Company,
  statements: FinancialStatement[],
  ratios: FinancialRatios,
  assessment: CreditAssessment,
  redFlags: RedFlag[]
): void {
  const exportPayload = {
    metadata: {
      generator: 'CrediMetrics Credit Assessment Tool',
      version: '2.0.0',
      exportDate: new Date().toISOString()
    },
    company,
    assessment,
    financialStatements: statements,
    calculatedRatios: ratios,
    redFlags
  };

  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(exportPayload, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute('href', dataStr);
  downloadAnchor.setAttribute('download', `${company.companyName.replace(/[^a-zA-Z0-9]/g, '_')}_Assessment_Data.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
}
