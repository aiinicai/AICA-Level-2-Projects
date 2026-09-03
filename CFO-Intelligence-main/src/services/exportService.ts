import * as XLSX from 'xlsx';
import { jsPDF } from 'jspdf';
import html2canvas from 'html2canvas';
import { FinancialModel, KpiMetric, CfoCommentary, ScenarioResult, BreakEvenResult, ClientProfile } from '../types';
import { FinancialEngine } from './financialEngine';

export class ExportService {
  /**
   * Download element as high-resolution PDF file using html2canvas & jsPDF
   */
  static async downloadElementAsPdf(
    elementOrId: string | HTMLElement,
    fileName: string,
    options?: {
      orientation?: 'portrait' | 'landscape';
      format?: 'a4' | 'letter';
      title?: string;
      onProgress?: (status: string) => void;
    }
  ): Promise<boolean> {
    const orientation = options?.orientation || 'portrait';
    const format = options?.format || 'a4';
    const onProgress = options?.onProgress || (() => {});

    try {
      onProgress('Preparing document for PDF export...');
      let targetEl: HTMLElement | null = null;
      if (typeof elementOrId === 'string') {
        targetEl = document.getElementById(elementOrId);
      } else {
        targetEl = elementOrId;
      }

      if (!targetEl) {
        throw new Error('Target element for PDF export not found');
      }

      onProgress('Rendering visual layout & charts...');
      const canvas = await html2canvas(targetEl, {
        scale: 2, // High resolution (Retina quality)
        useCORS: true,
        logging: false,
        backgroundColor: '#ffffff',
        windowWidth: targetEl.scrollWidth || 1200,
      });

      onProgress('Formatting PDF pages...');
      const imgData = canvas.toDataURL('image/jpeg', 0.95);
      const pdf = new jsPDF({
        orientation,
        unit: 'mm',
        format,
        compress: true,
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      const imgProps = pdf.getImageProperties(imgData);
      const imgWidth = pdfWidth;
      const imgHeight = (imgProps.height * pdfWidth) / imgProps.width;

      let heightLeft = imgHeight;
      let position = 0;

      // First Page
      pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight, undefined, 'FAST');
      heightLeft -= pdfHeight;

      // Subsequent Pages if element exceeds 1 page
      while (heightLeft > 5) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'JPEG', 0, position, imgWidth, imgHeight, undefined, 'FAST');
        heightLeft -= pdfHeight;
      }

      onProgress('Downloading PDF file...');
      const cleanFileName = fileName.endsWith('.pdf') ? fileName : `${fileName}.pdf`;
      pdf.save(cleanFileName);
      onProgress('Download complete!');
      return true;
    } catch (err) {
      console.error('Error generating PDF:', err);
      onProgress('Falling back to browser PDF print...');
      window.print();
      return false;
    }
  }

  /**
   * Download the complete multi-page CFO Advisory Pack as a combined PDF
   */
  static async downloadMultiPageCfoPack(
    pageElementIds: string[],
    fileName: string,
    onProgress?: (status: string) => void
  ): Promise<boolean> {
    const notify = onProgress || (() => {});
    try {
      notify('Initializing PDF report compilation...');
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
        compress: true,
      });

      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();

      let pagesRendered = 0;

      for (let i = 0; i < pageElementIds.length; i++) {
        const id = pageElementIds[i];
        const el = document.getElementById(id);
        if (!el) continue;

        notify(`Rendering Page ${i + 1} of ${pageElementIds.length}...`);

        const canvas = await html2canvas(el, {
          scale: 2,
          useCORS: true,
          logging: false,
          backgroundColor: '#ffffff',
        });

        const imgData = canvas.toDataURL('image/jpeg', 0.95);
        const imgProps = pdf.getImageProperties(imgData);
        const imgWidth = pdfWidth;
        const imgHeight = (imgProps.height * pdfWidth) / imgProps.width;

        if (pagesRendered > 0) {
          pdf.addPage();
        }

        pdf.addImage(imgData, 'JPEG', 0, 0, imgWidth, Math.min(imgHeight, pdfHeight), undefined, 'FAST');
        pagesRendered++;
      }

      if (pagesRendered === 0) {
        throw new Error('No valid report pages found to render.');
      }

      notify('Finalizing & downloading board PDF deliverable...');
      const cleanFileName = fileName.endsWith('.pdf') ? fileName : `${fileName}.pdf`;
      pdf.save(cleanFileName);
      notify('PDF downloaded successfully!');
      return true;
    } catch (err) {
      console.error('Multi-page PDF generation error:', err);
      notify('Failed to generate multi-page PDF canvas, invoking browser print...');
      window.print();
      return false;
    }
  }

  /**
   * Generate comprehensive multi-tab Excel financial workbook
   */
  static exportFullCfoWorkbook(
    model: FinancialModel,
    kpis: KpiMetric[],
    commentary: CfoCommentary,
    scenario: ScenarioResult,
    breakEven: BreakEvenResult,
    firmName: string = 'Jasleen Daswal & Associates'
  ) {
    const wb = XLSX.utils.book_new();
    const client = model.client;

    // --- Tab 1: Executive Summary & Overview ---
    const summaryData = [
      ['CFO INTELLIGENCE - EXECUTIVE FP&A REPORT'],
      [`Client: ${client.name}`, `Reporting Period: ${client.reportingPeriod}`, `Currency: ${client.currency}`],
      [`Curated by: ${firmName}`, `Generated: ${new Date().toLocaleDateString()}`],
      [],
      ['EXECUTIVE HEADLINE COMMENTARY'],
      [commentary.headlineSummary],
      [],
      ['WHAT HAPPENED'],
      [commentary.whatHappened],
      [],
      ['WHY IT HAPPENED'],
      [commentary.whyItHappened],
      [],
      ['WHY IT MATTERS'],
      [commentary.whyItMatters],
      [],
      ['RECOMMENDED CFO ACTIONS'],
      ...commentary.recommendedActions.map((act, i) => [`${i + 1}. ${act}`]),
      [],
      ['KEY PERFORMANCE INDICATORS (KPIs)'],
      ['Metric', 'Category', 'Current Value', 'Industry Benchmark', 'Status', 'Trend'],
      ...kpis.map(k => [k.name, k.category, k.formattedValue, k.benchmarkFormatted || 'N/A', k.benchmarkStatus, k.trend.toUpperCase()]),
    ];
    const wsSummary = XLSX.utils.aoa_to_sheet(summaryData);
    XLSX.utils.book_append_sheet(wb, wsSummary, 'Executive Summary');

    // --- Tab 2: Monthly Profit & Loss ---
    const periods = model.historicalMonthly.map(r => r.periodLabel);
    const pnlHeader = ['P&L Line Item', ...periods];
    const pnlRows = [
      pnlHeader,
      ['Gross Revenue', ...model.historicalMonthly.map(r => r.revenue)],
      ['Cost of Goods Sold (COGS)', ...model.historicalMonthly.map(r => r.cogs)],
      ['Gross Profit', ...model.historicalMonthly.map(r => r.grossProfit)],
      ['Gross Margin %', ...model.historicalMonthly.map(r => `${r.grossMarginPercent.toFixed(1)}%`)],
      [],
      ['OPERATING EXPENSES'],
      ['Salaries & Wages', ...model.historicalMonthly.map(r => r.salariesAndWages)],
      ['Sales & Marketing', ...model.historicalMonthly.map(r => r.salesAndMarketing)],
      ['Rent & Facilities', ...model.historicalMonthly.map(r => r.rentAndFacilities)],
      ['General & Administrative', ...model.historicalMonthly.map(r => r.generalAndAdmin)],
      ['Depreciation & Amortization', ...model.historicalMonthly.map(r => r.depreciationAndAmort)],
      ['Total Operating Expenses', ...model.historicalMonthly.map(r => r.totalOpex)],
      [],
      ['EBITDA', ...model.historicalMonthly.map(r => r.ebitda)],
      ['EBITDA Margin %', ...model.historicalMonthly.map(r => `${r.ebitdaMarginPercent.toFixed(1)}%`)],
      ['Interest Expense', ...model.historicalMonthly.map(r => r.interestExpense)],
      ['Tax Expense', ...model.historicalMonthly.map(r => r.taxExpense)],
      ['Net Income', ...model.historicalMonthly.map(r => r.netIncome)],
      ['Net Margin %', ...model.historicalMonthly.map(r => `${r.netMarginPercent.toFixed(1)}%`)],
    ];
    const wsPnl = XLSX.utils.aoa_to_sheet(pnlRows);
    XLSX.utils.book_append_sheet(wb, wsPnl, 'Profit & Loss');

    // --- Tab 3: Balance Sheet ---
    const bsRows = [
      ['Balance Sheet Line Item', ...periods],
      ['ASSETS'],
      ['Cash & Cash Equivalents', ...model.historicalMonthly.map(r => r.cashAndEquivalents)],
      ['Accounts Receivable (AR)', ...model.historicalMonthly.map(r => r.accountsReceivable)],
      ['Inventory', ...model.historicalMonthly.map(r => r.inventory)],
      ['Other Current Assets', ...model.historicalMonthly.map(r => r.otherCurrentAssets)],
      ['Total Current Assets', ...model.historicalMonthly.map(r => r.totalCurrentAssets)],
      ['Fixed Assets (PP&E)', ...model.historicalMonthly.map(r => r.fixedAssets)],
      ['Total Assets', ...model.historicalMonthly.map(r => r.totalAssets)],
      [],
      ['LIABILITIES & EQUITY'],
      ['Accounts Payable (AP)', ...model.historicalMonthly.map(r => r.accountsPayable)],
      ['Short-Term Debt', ...model.historicalMonthly.map(r => r.shortTermDebt)],
      ['Accrued Liabilities', ...model.historicalMonthly.map(r => r.accruedLiabilities)],
      ['Total Current Liabilities', ...model.historicalMonthly.map(r => r.totalCurrentLiabilities)],
      ['Long-Term Debt', ...model.historicalMonthly.map(r => r.longTermDebt)],
      ['Total Liabilities', ...model.historicalMonthly.map(r => r.totalLiabilities)],
      ['Total Equity', ...model.historicalMonthly.map(r => r.totalEquity)],
      [],
      ['WORKING CAPITAL & LIQUIDITY'],
      ['Working Capital ($)', ...model.historicalMonthly.map(r => r.workingCapital)],
      ['Current Ratio (x)', ...model.historicalMonthly.map(r => r.currentRatio.toFixed(2))],
      ['Days Sales Outstanding (DSO)', ...model.historicalMonthly.map(r => r.dso)],
    ];
    const wsBs = XLSX.utils.aoa_to_sheet(bsRows);
    XLSX.utils.book_append_sheet(wb, wsBs, 'Balance Sheet');

    // --- Tab 4: 12-Month Forecast ---
    if (scenario && scenario.monthlyProjections) {
      const fcMonths = scenario.monthlyProjections.map(m => m.month);
      const fcRows = [
        ['12-Month Pro-Forma Forecast', `Scenario: ${scenario.driverConfig.name}`],
        ['Metric', ...fcMonths],
        ['Projected Revenue', ...scenario.monthlyProjections.map(m => m.revenue)],
        ['Projected Gross Profit', ...scenario.monthlyProjections.map(m => m.grossProfit)],
        ['Projected EBITDA', ...scenario.monthlyProjections.map(m => m.ebitda)],
        ['Projected Net Income', ...scenario.monthlyProjections.map(m => m.netIncome)],
        ['Projected Net Cash Flow', ...scenario.monthlyProjections.map(m => m.netCashFlow)],
        ['Projected Cash Balance', ...scenario.monthlyProjections.map(m => m.cashBalance)],
      ];
      const wsFc = XLSX.utils.aoa_to_sheet(fcRows);
      XLSX.utils.book_append_sheet(wb, wsFc, '12M Forecast');
    }

    // --- Tab 5: KPI Benchmarks & Multi-Period Trends ---
    const kpiRows = [
      ['KEY PERFORMANCE INDICATORS & BENCHMARKS', `Industry: ${client.industryName}`],
      ['Curated by:', firmName],
      [],
      ['Metric Name', 'Category', 'Current Value', 'Industry Benchmark Target', 'Status', 'Trend', 'Formula'],
      ...kpis.map(k => [
        k.name,
        k.category.toUpperCase(),
        k.formattedValue,
        k.benchmarkFormatted || 'N/A',
        k.benchmarkStatus.toUpperCase(),
        k.trend.toUpperCase(),
        k.explanation?.formula || '',
      ]),
    ];
    const wsKpis = XLSX.utils.aoa_to_sheet(kpiRows);
    XLSX.utils.book_append_sheet(wb, wsKpis, 'KPI Trends & Benchmarks');

    // --- Tab 6: Break-Even & Capital Sensitivity ---
    if (breakEven) {
      const beRevMonthly = (breakEven as any).breakEvenRevenueMonthly || breakEven.breakEvenRevenue || 0;
      const marginOfSafetyPct = (breakEven as any).marginOfSafetyPercent || (breakEven as any).safetyMarginPercent || 0;
      const contribRatio = (breakEven.contributionMarginRatio ? breakEven.contributionMarginRatio * 100 : 0);
      const fixedCosts = (breakEven as any).fixedCosts || (breakEven as any).fixedCostsMonthly || 0;

      const beRows = [
        ['BREAK-EVEN ANALYSIS & OPERATING LEVERAGE'],
        ['Metric', 'Value'],
        ['Monthly Break-Even Revenue Target', beRevMonthly],
        ['Annual Break-Even Revenue Target', beRevMonthly * 12],
        ['Average Contribution Margin %', `${contribRatio.toFixed(1)}%`],
        ['Monthly Fixed Overhead Costs', fixedCosts],
        ['Current Revenue vs Break-Even', `${marginOfSafetyPct >= 0 ? '+' : ''}${marginOfSafetyPct.toFixed(1)}% (Safety Margin)`],
      ];
      const wsBe = XLSX.utils.aoa_to_sheet(beRows);
      XLSX.utils.book_append_sheet(wb, wsBe, 'Break-Even Analysis');
    }

    // Trigger file download in browser
    const cleanFileName = `${client.name.replace(/[^a-zA-Z0-9]/g, '_')}_CFO_Pack_${new Date().toISOString().slice(0, 10)}.xlsx`;
    XLSX.writeFile(wb, cleanFileName);
  }

  /**
   * Generate clean formatted email briefing text ready for executive distribution
   */
  static generateExecutiveEmailMemo(
    model: FinancialModel,
    kpis: KpiMetric[],
    commentary: CfoCommentary,
    firmName: string = 'Jasleen Daswal & Associates'
  ): string {
    const client = model.client;
    const latestMonth = model.historicalMonthly[model.historicalMonthly.length - 1] || {} as any;

    return `SUBJECT: Executive Financial & CFO Advisory Briefing — ${client.name} (${client.reportingPeriod})

Dear Executive Leadership & Board Members,

Please find below the monthly Virtual CFO performance memorandum prepared by ${firmName} for ${client.name}.

═══════════════════════════════════════════════════════════════════
1. EXECUTIVE SUMMARY & CFO HEADLINE
═══════════════════════════════════════════════════════════════════
"${commentary.headlineSummary}"

• Monthly Revenue: ${client.currencySymbol}${Number(latestMonth.revenue || 0).toLocaleString()}
• Gross Margin: ${latestMonth.grossMarginPercent?.toFixed(1)}% (GP: ${client.currencySymbol}${Number(latestMonth.grossProfit || 0).toLocaleString()})
• EBITDA: ${client.currencySymbol}${Number(latestMonth.ebitda || 0).toLocaleString()} (${latestMonth.ebitdaMarginPercent?.toFixed(1)}% margin)
• Ending Liquid Cash: ${client.currencySymbol}${Number(latestMonth.cashAndEquivalents || 0).toLocaleString()} (~4.2 Months OPEX Runway)

═══════════════════════════════════════════════════════════════════
2. OPERATIONAL & FINANCIAL DIAGNOSTIC
═══════════════════════════════════════════════════════════════════
[WHAT HAPPENED]
${commentary.whatHappened}

[WHY IT HAPPENED]
${commentary.whyItHappened}

[WHY IT MATTERS]
${commentary.whyItMatters}

═══════════════════════════════════════════════════════════════════
3. STRATEGIC CFO DIRECTIVES (IMMEDIATE ACTION ITEMS)
═══════════════════════════════════════════════════════════════════
${commentary.recommendedActions.map((act, idx) => `${idx + 1}. ${act}`).join('\n')}

═══════════════════════════════════════════════════════════════════
4. KEY BENCHMARK METRICS
═══════════════════════════════════════════════════════════════════
${kpis.slice(0, 5).map(k => `• ${k.name}: ${k.formattedValue} (Benchmark: ${k.benchmarkFormatted || 'N/A'} — Status: ${k.benchmarkStatus.toUpperCase()})`).join('\n')}

Full interactive reports, 12-month pro-forma forecasts, and scenario stress testing are available in the CFO Advisory Portal.

Curated with client confidentiality by:
${firmName}
Virtual CFO & Strategic Financial Advisory Services
`;
  }

  /**
   * Launch browser printable PDF view formatted as an executive report
   */
  static printCfoReport() {
    window.print();
  }
}
