import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import { CompanyEntity, DeterministicMetrics, CurrencyUnit, PeriodId } from '../types/finance';
import { getAllCompanies } from '../data/companiesData';
import { calculateDeterministicMetrics, formatCurrency, formatMultiple, formatPercent } from './financialCalculations';

// Export complete 140+ enterprise dataset to multi-sheet Excel (.xlsx)
export const exportUniverseToExcel = (periodId: PeriodId = 'Q4 FY25') => {
  const allCompanies = getAllCompanies();
  const wb = XLSX.utils.book_new();

  // Sheet 1: Universe Master Data
  const masterData = allCompanies.map(c => {
    const m = calculateDeterministicMetrics(c, periodId);
    return {
      'Company Name': c.name,
      'Ticker': c.ticker,
      'BSE Code': c.bseCode,
      'Sector': c.sector,
      'Period': periodId,
      'Market Cap (₹ Cr)': m.marketCap,
      'Stock Price (₹)': c.periods[periodId]?.valuation.stockPrice || 0,
      'P/E Multiple': m.peRatio,
      'P/B Multiple': m.pbRatio,
      'EV/EBITDA': m.evEbitdaRatio,
      'Dividend Yield %': m.dividendYield,
      'Revenue from Operations (₹ Cr)': m.revenue,
      'Other Income (₹ Cr)': m.otherIncome,
      'Total Revenue (₹ Cr)': m.totalIncome,
      'Operating EBITDA (₹ Cr)': m.ebitda,
      'EBIT (₹ Cr)': m.ebit,
      'Finance Costs (₹ Cr)': m.financeCosts,
      'PBT (₹ Cr)': m.ebt,
      'PAT (₹ Cr)': m.pat,
      'OPM %': Number(m.opmPercent.toFixed(2)),
      'NPM %': Number(m.npmPercent.toFixed(2)),
      'Net Worth (₹ Cr)': m.netWorth,
      'Total Debt (₹ Cr)': m.totalDebt,
      'Debt-to-Equity (x)': Number(m.debtToEquity.toFixed(2)),
      'Interest Coverage (x)': Number(m.interestCoverage.toFixed(2)),
      'ROCE %': Number(m.rocePercent.toFixed(2)),
      'Economic Spread %': Number(m.economicSpread.toFixed(2)),
      'Sales YoY %': Number(m.salesYoYGrowth.toFixed(2)),
      'PAT YoY %': Number(m.patYoYGrowth.toFixed(2)),
      'Negative Scissors Flag': m.hasNegativeScissors ? 'YES' : 'NO',
      'Audit Health Score': m.overallRiskScore,
      'Risk Rating': m.riskRating
    };
  });

  const wsMaster = XLSX.utils.json_to_sheet(masterData);
  XLSX.utils.book_append_sheet(wb, wsMaster, '140+ Listed Universe');

  // Sheet 2: Sector Aggregates
  const sectorGroups: Record<string, typeof masterData> = {};
  masterData.forEach(row => {
    if (!sectorGroups[row.Sector]) sectorGroups[row.Sector] = [];
    sectorGroups[row.Sector].push(row);
  });

  const sectorSummary = Object.keys(sectorGroups).map(sector => {
    const items = sectorGroups[sector];
    const totalMCap = items.reduce((acc, i) => acc + i['Market Cap (₹ Cr)'], 0);
    const totalRev = items.reduce((acc, i) => acc + i['Revenue from Operations (₹ Cr)'], 0);
    const totalEbitda = items.reduce((acc, i) => acc + i['Operating EBITDA (₹ Cr)'], 0);
    const avgROCE = items.reduce((acc, i) => acc + i['ROCE %'], 0) / items.length;
    const avgDE = items.reduce((acc, i) => acc + i['Debt-to-Equity (x)'], 0) / items.length;

    return {
      'Sector': sector,
      'Enterprises Count': items.length,
      'Combined Market Cap (₹ Cr)': totalMCap,
      'Combined Revenue (₹ Cr)': totalRev,
      'Combined EBITDA (₹ Cr)': totalEbitda,
      'Sector OPM %': totalRev > 0 ? Number(((totalEbitda / totalRev) * 100).toFixed(2)) : 0,
      'Average ROCE %': Number(avgROCE.toFixed(2)),
      'Average D/E (x)': Number(avgDE.toFixed(2))
    };
  });

  const wsSectors = XLSX.utils.json_to_sheet(sectorSummary);
  XLSX.utils.book_append_sheet(wb, wsSectors, 'Sector Aggregates');

  // Download Excel
  XLSX.writeFile(wb, `CFO_Financial_Intelligence_140_Universe_${periodId.replace(' ', '_')}.xlsx`);
};

// Export Single-Company Comprehensive Financial Statement to Excel
export const exportCompanyToExcel = (company: CompanyEntity, periodId: PeriodId, metrics: DeterministicMetrics) => {
  const wb = XLSX.utils.book_new();

  // Multi-Period P&L History
  const periods: PeriodId[] = ['Q4 FY25', 'Q3 FY25', 'Q2 FY25', 'FY24', 'FY23'];
  const plHistory = periods.map(p => {
    const m = calculateDeterministicMetrics(company, p);
    return {
      'Reporting Period': p,
      'Revenue from Operations (₹ Cr)': m.revenue,
      'Other Income (₹ Cr)': m.otherIncome,
      'Total Income (₹ Cr)': m.totalIncome,
      'Raw Materials & COGS (₹ Cr)': m.rawMaterialCost,
      'Employee Expenses (₹ Cr)': m.employeeCost,
      'Other Operating Expenses (₹ Cr)': m.otherOperatingExpenses,
      'Operating EBITDA (₹ Cr)': m.ebitda,
      'OPM %': Number(m.opmPercent.toFixed(2)),
      'Depreciation & Amortization (₹ Cr)': m.depreciation,
      'EBIT (₹ Cr)': m.ebit,
      'Finance Costs (₹ Cr)': m.financeCosts,
      'PBT (₹ Cr)': m.ebt,
      'Tax (₹ Cr)': m.tax,
      'PAT (₹ Cr)': m.pat,
      'NPM %': Number(m.npmPercent.toFixed(2)),
      'Net Worth (₹ Cr)': m.netWorth,
      'Total Debt (₹ Cr)': m.totalDebt,
      'D/E Ratio (x)': Number(m.debtToEquity.toFixed(2)),
      'Interest Coverage (x)': Number(m.interestCoverage.toFixed(2)),
      'ROCE %': Number(m.rocePercent.toFixed(2))
    };
  });

  const wsPL = XLSX.utils.json_to_sheet(plHistory);
  XLSX.utils.book_append_sheet(wb, wsPL, 'P&L & Solvency History');

  XLSX.writeFile(wb, `${company.ticker}_Financial_Model_${periodId.replace(' ', '_')}.xlsx`);
};

// Export Executive CFO Board Memo to PDF using jsPDF + autoTable
export const exportBoardMemoToPdf = (
  company: CompanyEntity,
  metrics: DeterministicMetrics,
  periodId: PeriodId,
  memoText: string
) => {
  const doc = new jsPDF();

  // Header styling
  doc.setFillColor(11, 15, 25);
  doc.rect(0, 0, 210, 35, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text('CFO FINANCIAL INTELLIGENCE & ENTERPRISE ANALYTICS', 14, 15);

  doc.setFontSize(10);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(147, 197, 253);
  doc.text(`CONFIDENTIAL BOARD MEMORANDUM | ${company.name.toUpperCase()} (${company.ticker})`, 14, 23);
  doc.text(`Reporting Period: ${periodId} | Currency: INR Crores`, 14, 29);

  // Core KPI Table in PDF
  autoTable(doc, {
    startY: 42,
    head: [['Metric', 'Value', '% of Operations / Ratio', 'Benchmarking Status']],
    body: [
      ['Revenue from Operations', `₹ ${metrics.revenue.toLocaleString('en-IN')} Cr`, `${formatPercent(metrics.salesYoYGrowth, 1, true)} YoY`, 'Topline Volume'],
      ['Operating EBITDA', `₹ ${metrics.ebitda.toLocaleString('en-IN')} Cr`, `OPM: ${formatPercent(metrics.opmPercent, 1)}`, metrics.opmPercent >= 15 ? 'Healthy Margin' : 'Moderate'],
      ['Net Profit After Tax (PAT)', `₹ ${metrics.pat.toLocaleString('en-IN')} Cr`, `NPM: ${formatPercent(metrics.npmPercent, 1)}`, metrics.pat >= 0 ? 'Profitable' : 'Loss Quarter'],
      ['Debt-to-Equity (D/E)', `${formatMultiple(metrics.debtToEquity)}`, `Total Debt: ₹ ${metrics.totalDebt.toLocaleString('en-IN')} Cr`, metrics.debtToEquity <= 1.0 ? 'Low Gearing' : 'Elevated Leverage'],
      ['Interest Coverage Ratio', `${formatMultiple(metrics.interestCoverage)}`, `EBIT: ₹ ${metrics.ebit.toLocaleString('en-IN')} Cr`, metrics.interestCoverage >= 3.0 ? 'Safe Buffer' : 'Watchlist'],
      ['ROCE % (Return on Capital)', `${formatPercent(metrics.rocePercent, 1)}`, `Economic Spread: ${formatPercent(metrics.economicSpread, 1, true)}`, metrics.economicSpread >= 0 ? 'Value Accretive' : 'Sub-Hurdle']
    ],
    theme: 'grid',
    headStyles: { fillColor: [37, 99, 235], textColor: [255, 255, 255], fontStyle: 'bold', fontSize: 9 },
    bodyStyles: { fontSize: 8.5, textColor: [30, 41, 59] },
    alternateRowStyles: { fillColor: [248, 250, 252] }
  });

  // Executive Memo Body text
  const finalY = (doc as any).lastAutoTable.finalY || 100;
  doc.setFontSize(11);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(15, 23, 42);
  doc.text('Executive CFO Commentary & Strategic Board Recommendations:', 14, finalY + 10);

  doc.setFontSize(8.5);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(51, 65, 85);

  const splitText = doc.splitTextToSize(memoText, 180);
  doc.text(splitText, 14, finalY + 17);

  // Footer
  doc.setFontSize(8);
  doc.setTextColor(148, 163, 184);
  doc.text('Generated by CFO Financial Intelligence & Enterprise Analytics Platform | Confidential & Proprietary', 14, 285);

  doc.save(`${company.ticker}_Board_Memo_${periodId.replace(' ', '_')}.pdf`);
};
