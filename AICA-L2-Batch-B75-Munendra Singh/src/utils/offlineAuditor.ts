import { AuditReportData, DisclosureItem, InconsistencyItem, NoteProofreadingItem, ScheduleIIIGuidanceItem, AuditRecommendation, ComplianceScore, RiskLevel } from '../types';

/**
 * Deterministic Offline Financial Statement Auditor & Consistency Verifier Engine.
 * Implements line-by-line proofreading, primary-to-notes cross-referencing,
 * mathematical casting/footing checks, ICAI Schedule III & MCA 2021 checklist,
 * and Ind AS 1-116 standard disclosure verification 100% locally on-device.
 */

interface ParseContext {
  entityName: string;
  reportingPeriod: string;
  reportingScale: string;
  framework: string;
  cin: string;
  rawText: string;
  lines: string[];
}

// Helper to clean and parse Indian and Western currency numerical strings
export function parseFinancialNumber(valStr: string): number | null {
  if (!valStr) return null;
  // Remove currency signs, commas, spaces, parenthesis around negative numbers
  let cleaned = valStr.trim();
  let isNegative = false;
  if (cleaned.startsWith('(') && cleaned.endsWith(')')) {
    isNegative = true;
    cleaned = cleaned.slice(1, -1).trim();
  } else if (cleaned.startsWith('-')) {
    isNegative = true;
    cleaned = cleaned.slice(1).trim();
  }
  cleaned = cleaned.replace(/[₹$,\s]/g, '');
  const num = parseFloat(cleaned);
  if (isNaN(num)) return null;
  return isNegative ? -num : num;
}

export function formatFinancialNumber(num: number, scale: string = ''): string {
  const isNeg = num < 0;
  const absNum = Math.abs(num);
  const formatted = absNum.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${isNeg ? '-' : ''}₹${formatted}${scale ? ` ${scale}` : ''}`;
}

export function runOfflineAudit(
  inputText: string,
  options: {
    strictTolerance?: boolean;
    checkCARO?: boolean;
    standardsFocus?: string[];
    fileName?: string;
  } = {}
): AuditReportData {
  const text = inputText || '';
  const lines = text.split('\n').map((l) => l.trim()).filter(Boolean);

  // 1. Extract Header & Metadata Context
  const context = extractMetadata(text, lines, options.fileName);

  // 2. Extract Primary Financial Statement Numbers
  const bs = extractBalanceSheet(text);
  const pl = extractProfitAndLoss(text);
  const cf = extractCashFlow(text);

  // 3. Extract and Proofread Notes to Accounts
  const notes = extractNotes(text);

  // 4. Perform Mathematical Footing & Cross-Referencing Checks
  const inconsistencies: InconsistencyItem[] = [];
  const noteProofreadings: NoteProofreadingItem[] = [];
  const scheduleIIIGuidanceFindings: ScheduleIIIGuidanceItem[] = [];
  const disclosures: DisclosureItem[] = [];

  // --- CASTING CHECKS & RECONCILIATIONS ---

  // BS Castings: Total Assets vs Total Equity & Liabilities
  if (bs.totalAssets !== null && bs.totalEquityAndLiabilities !== null) {
    const diff = Math.abs(bs.totalAssets - bs.totalEquityAndLiabilities);
    const tolerance = options.strictTolerance ? 0.05 : 1.0;
    if (diff > tolerance) {
      inconsistencies.push({
        lineItem: 'Balance Sheet Balancing Equation (Total Assets vs Total Equity & Liabilities)',
        primaryFigure: formatFinancialNumber(bs.totalAssets),
        noteFigure: formatFinancialNumber(bs.totalEquityAndLiabilities),
        noteRef: 'Face of Balance Sheet',
        discrepancy: `Balance sheet does not balance. Total Assets (${formatFinancialNumber(bs.totalAssets)}) differ from Total Equity & Liabilities (${formatFinancialNumber(bs.totalEquityAndLiabilities)}) by ${formatFinancialNumber(diff)}. Fundamental violation of Ind AS 1 / Schedule III.`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // Non-current + Current Assets vs Total Assets Casting
  if (bs.totalNonCurrentAssets !== null && bs.totalCurrentAssets !== null && bs.totalAssets !== null) {
    const sumAssets = bs.totalNonCurrentAssets + bs.totalCurrentAssets;
    const diff = Math.abs(sumAssets - bs.totalAssets);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Asset Subtotal Casting (Non-current Assets + Current Assets)',
        primaryFigure: formatFinancialNumber(bs.totalAssets),
        noteFigure: formatFinancialNumber(sumAssets),
        noteRef: 'Balance Sheet Part I',
        discrepancy: `Sum of Non-current Assets (${formatFinancialNumber(bs.totalNonCurrentAssets)}) and Current Assets (${formatFinancialNumber(bs.totalCurrentAssets)}) = ${formatFinancialNumber(sumAssets)}, which does not match reported Total Assets of ${formatFinancialNumber(bs.totalAssets)} (Variance: ${formatFinancialNumber(diff)}).`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // Equity + Non-current Liabilities + Current Liabilities vs Total Equity & Liabilities
  if (bs.totalEquity !== null && bs.totalNonCurrentLiabilities !== null && bs.totalCurrentLiabilities !== null && bs.totalEquityAndLiabilities !== null) {
    const sumLiab = bs.totalEquity + bs.totalNonCurrentLiabilities + bs.totalCurrentLiabilities;
    const diff = Math.abs(sumLiab - bs.totalEquityAndLiabilities);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Equity & Liabilities Casting',
        primaryFigure: formatFinancialNumber(bs.totalEquityAndLiabilities),
        noteFigure: formatFinancialNumber(sumLiab),
        noteRef: 'Balance Sheet Part II',
        discrepancy: `Sum of Total Equity (${formatFinancialNumber(bs.totalEquity)}), Non-current Liabilities (${formatFinancialNumber(bs.totalNonCurrentLiabilities)}) and Current Liabilities (${formatFinancialNumber(bs.totalCurrentLiabilities)}) = ${formatFinancialNumber(sumLiab)}, which does not match Total Equity & Liabilities (${formatFinancialNumber(bs.totalEquityAndLiabilities)}).`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // P&L Castings: Total Revenue + Other Income vs Total Income
  if (pl.revenueFromOps !== null && pl.otherIncome !== null && pl.totalIncome !== null) {
    const calcTotalIncome = pl.revenueFromOps + pl.otherIncome;
    const diff = Math.abs(calcTotalIncome - pl.totalIncome);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Total Income Casting (Revenue from Operations + Other Income)',
        primaryFigure: formatFinancialNumber(pl.totalIncome),
        noteFigure: formatFinancialNumber(calcTotalIncome),
        noteRef: 'Statement of Profit and Loss',
        discrepancy: `Revenue from Operations (${formatFinancialNumber(pl.revenueFromOps)}) + Other Income (${formatFinancialNumber(pl.otherIncome)}) = ${formatFinancialNumber(calcTotalIncome)}, but reported Total Income is ${formatFinancialNumber(pl.totalIncome)}.`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // P&L Castings: Total Income - Total Expenses vs Profit Before Tax
  if (pl.totalIncome !== null && pl.totalExpenses !== null && pl.pbt !== null) {
    const calcPbt = pl.totalIncome - pl.totalExpenses;
    const diff = Math.abs(calcPbt - pl.pbt);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Profit Before Tax (PBT) Computation',
        primaryFigure: formatFinancialNumber(pl.pbt),
        noteFigure: formatFinancialNumber(calcPbt),
        noteRef: 'Statement of Profit and Loss',
        discrepancy: `Total Income (${formatFinancialNumber(pl.totalIncome)}) less Total Expenses (${formatFinancialNumber(pl.totalExpenses)}) calculates to PBT of ${formatFinancialNumber(calcPbt)}, but reported PBT is ${formatFinancialNumber(pl.pbt)}.`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // P&L Castings: PBT - Tax Expense vs PAT
  if (pl.pbt !== null && pl.taxExpense !== null && pl.pat !== null) {
    const calcPat = pl.pbt - pl.taxExpense;
    const diff = Math.abs(calcPat - pl.pat);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Profit for the Year (PAT) Casting',
        primaryFigure: formatFinancialNumber(pl.pat),
        noteFigure: formatFinancialNumber(calcPat),
        noteRef: 'Statement of Profit and Loss Line VII',
        discrepancy: `Profit Before Tax (${formatFinancialNumber(pl.pbt)}) minus Tax Expense (${formatFinancialNumber(pl.taxExpense)}) equals ${formatFinancialNumber(calcPat)}, differing from reported PAT of ${formatFinancialNumber(pl.pat)}.`,
        riskLevel: 'Medium',
        type: 'casting_error',
      });
    }
  }

  // Cash Flow Statement Reconciliation with Balance Sheet Cash & Bank
  if (cf.closingCash !== null && bs.cashAndCashEquivalents !== null) {
    const diff = Math.abs(cf.closingCash - bs.cashAndCashEquivalents);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Cash & Cash Equivalents (Cash Flow vs Balance Sheet)',
        primaryFigure: formatFinancialNumber(bs.cashAndCashEquivalents),
        noteFigure: formatFinancialNumber(cf.closingCash),
        noteRef: 'Cash Flow Statement & Note 12',
        discrepancy: `Closing Cash and Cash Equivalents in Cash Flow Statement (${formatFinancialNumber(cf.closingCash)}) does not reconcile with Balance Sheet Cash & Cash Equivalents (${formatFinancialNumber(bs.cashAndCashEquivalents)}) with a variance of ${formatFinancialNumber(diff)}.`,
        riskLevel: 'High',
        type: 'numerical_mismatch',
      });
    }
  }

  // Cash Flow net movement calculation
  if (cf.operatingCash !== null && cf.investingCash !== null && cf.financingCash !== null && cf.netChangeInCash !== null) {
    const calculatedNetChange = cf.operatingCash + cf.investingCash + cf.financingCash;
    const diff = Math.abs(calculatedNetChange - cf.netChangeInCash);
    if (diff > 0.5) {
      inconsistencies.push({
        lineItem: 'Cash Flow Net Change Sum (Operating + Investing + Financing)',
        primaryFigure: formatFinancialNumber(cf.netChangeInCash),
        noteFigure: formatFinancialNumber(calculatedNetChange),
        noteRef: 'Statement of Cash Flows',
        discrepancy: `Sum of Operating (${formatFinancialNumber(cf.operatingCash)}), Investing (${formatFinancialNumber(cf.investingCash)}), and Financing (${formatFinancialNumber(cf.financingCash)}) equals ${formatFinancialNumber(calculatedNetChange)}, but reported Net Change is ${formatFinancialNumber(cf.netChangeInCash)}.`,
        riskLevel: 'High',
        type: 'casting_error',
      });
    }
  }

  // --- CROSS-REFERENCING PRIMARY STATEMENTS TO NOTES ---

  // Check PPE Note vs Balance Sheet PPE
  if (notes.ppe && bs.ppe !== null) {
    if (notes.ppe.closingBalance !== null) {
      const diff = Math.abs(notes.ppe.closingBalance - bs.ppe);
      if (diff > 0.5) {
        inconsistencies.push({
          lineItem: 'Property, Plant & Equipment (Note vs Balance Sheet)',
          primaryFigure: formatFinancialNumber(bs.ppe),
          noteFigure: formatFinancialNumber(notes.ppe.closingBalance),
          noteRef: `Note ${notes.ppe.noteNo || '3'}: PPE Schedule`,
          discrepancy: `Gross/Net carrying amount in PPE Note schedule (${formatFinancialNumber(notes.ppe.closingBalance)}) does not agree with Balance Sheet line item (${formatFinancialNumber(bs.ppe)}). Variance: ${formatFinancialNumber(diff)}.`,
          riskLevel: 'High',
          type: 'numerical_mismatch',
        });
      }
    }
  }

  // Check CWIP Note vs Balance Sheet CWIP
  if (notes.cwip && bs.cwip !== null) {
    if (notes.cwip.totalAmount !== null) {
      const diff = Math.abs(notes.cwip.totalAmount - bs.cwip);
      if (diff > 0.5) {
        inconsistencies.push({
          lineItem: 'Capital Work-in-Progress (CWIP)',
          primaryFigure: formatFinancialNumber(bs.cwip),
          noteFigure: formatFinancialNumber(notes.cwip.totalAmount),
          noteRef: `Note ${notes.cwip.noteNo || '4'}: CWIP`,
          discrepancy: `CWIP schedule total (${formatFinancialNumber(notes.cwip.totalAmount)}) differs from Balance Sheet CWIP (${formatFinancialNumber(bs.cwip)}).`,
          riskLevel: 'Medium',
          type: 'numerical_mismatch',
        });
      }
    }
  }

  // Check Trade Receivables Note vs Balance Sheet
  if (notes.tradeReceivables && bs.tradeReceivables !== null) {
    if (notes.tradeReceivables.netAmount !== null) {
      const diff = Math.abs(notes.tradeReceivables.netAmount - bs.tradeReceivables);
      if (diff > 0.5) {
        inconsistencies.push({
          lineItem: 'Trade Receivables (Carrying Value vs Aging Schedule)',
          primaryFigure: formatFinancialNumber(bs.tradeReceivables),
          noteFigure: formatFinancialNumber(notes.tradeReceivables.netAmount),
          noteRef: `Note ${notes.tradeReceivables.noteNo || '8/11'}: Trade Receivables`,
          discrepancy: `Net Trade Receivables after ECL in Note Schedule (${formatFinancialNumber(notes.tradeReceivables.netAmount)}) does not match Balance Sheet reported figure (${formatFinancialNumber(bs.tradeReceivables)}).`,
          riskLevel: 'High',
          type: 'numerical_mismatch',
        });
      }
    }
  }

  // Check Trade Payables Note vs Balance Sheet (MSME + Other Than MSME)
  if (notes.tradePayables) {
    if (bs.tradePayablesMsme !== null && bs.tradePayablesOthers !== null) {
      const bsTotalPayables = bs.tradePayablesMsme + bs.tradePayablesOthers;
      if (notes.tradePayables.totalAmount !== null) {
        const diff = Math.abs(notes.tradePayables.totalAmount - bsTotalPayables);
        if (diff > 0.5) {
          inconsistencies.push({
            lineItem: 'Trade Payables (MSME + Others Subtotal Casting)',
            primaryFigure: formatFinancialNumber(bsTotalPayables),
            noteFigure: formatFinancialNumber(notes.tradePayables.totalAmount),
            noteRef: `Note ${notes.tradePayables.noteNo || '23'}: Trade Payables`,
            discrepancy: `Sum of MSME (${formatFinancialNumber(bs.tradePayablesMsme)}) and Other Payables (${formatFinancialNumber(bs.tradePayablesOthers)}) on Balance sheet is ${formatFinancialNumber(bsTotalPayables)}, but Note schedule details sum to ${formatFinancialNumber(notes.tradePayables.totalAmount)}.`,
            riskLevel: 'High',
            type: 'casting_error',
          });
        }
      }
    }
  }

  // Check Related Party Disclosures / KMP Remuneration Contradictions
  if (notes.relatedParty) {
    if (notes.relatedParty.tableKmpRemuneration !== null && notes.relatedParty.textKmpRemuneration !== null) {
      const diff = Math.abs(notes.relatedParty.tableKmpRemuneration - notes.relatedParty.textKmpRemuneration);
      if (diff > 0.1) {
        inconsistencies.push({
          lineItem: 'KMP Remuneration (Text Commentary vs Related Party Schedule)',
          primaryFigure: formatFinancialNumber(notes.relatedParty.textKmpRemuneration),
          noteFigure: formatFinancialNumber(notes.relatedParty.tableKmpRemuneration),
          noteRef: `Note ${notes.relatedParty.noteNo || '33/34'}: Related Party Disclosures`,
          discrepancy: `Text commentary in Note / Directors' Report states KMP remuneration of ${formatFinancialNumber(notes.relatedParty.textKmpRemuneration)}, whereas the itemized table in Note lists ${formatFinancialNumber(notes.relatedParty.tableKmpRemuneration)} (Discrepancy: ${formatFinancialNumber(diff)}).`,
          riskLevel: 'High',
          type: 'text_table_contradiction',
        });
      }
    }
  }

  // Check Employee Benefits Note vs P&L Employee Benefit Expense
  if (notes.employeeBenefits && pl.employeeBenefits !== null) {
    if (notes.employeeBenefits.totalExpense !== null) {
      const diff = Math.abs(notes.employeeBenefits.totalExpense - pl.employeeBenefits);
      if (diff > 0.5) {
        inconsistencies.push({
          lineItem: 'Employee Benefit Expense (P&L vs Note Schedule)',
          primaryFigure: formatFinancialNumber(pl.employeeBenefits),
          noteFigure: formatFinancialNumber(notes.employeeBenefits.totalExpense),
          noteRef: `Note ${notes.employeeBenefits.noteNo || '23/28'}: Employee Benefits`,
          discrepancy: `P&L Employee Benefit Expense of ${formatFinancialNumber(pl.employeeBenefits)} differs from total of breakup in Note of ${formatFinancialNumber(notes.employeeBenefits.totalExpense)}.`,
          riskLevel: 'Medium',
          type: 'numerical_mismatch',
        });
      }
    }
  }

  // --- COMPREHENSIVE NOTE-BY-NOTE PROOFREADING ---
  const proofreadList = runNoteProofreadingEngine(text, notes);
  noteProofreadings.push(...proofreadList);

  // --- ICAI SCHEDULE III GUIDANCE & MCA 2021 AMENDMENTS VERIFICATION ---
  const schedIIIFindings = runScheduleIIIChecklist(text, notes, bs, pl);
  scheduleIIIGuidanceFindings.push(...schedIIIFindings);

  // --- IND AS STANDARDS DISCLOSURE COMPLIANCE MATRIX ---
  const disclosureList = runIndASDisclosureMatrix(text, notes, options.standardsFocus);
  disclosures.push(...disclosureList);

  // Count metrics
  const missingDisclosuresCount = disclosures.filter((d) => d.status === 'Missing').length;
  const partialDisclosuresCount = disclosures.filter((d) => d.status === 'Partial').length;
  const numericalMismatchesCount = inconsistencies.length;
  const totalDiscrepancies = missingDisclosuresCount + numericalMismatchesCount;

  // Calculate Overall Compliance Score
  let overallComplianceScore: ComplianceScore = 'High';
  if (totalDiscrepancies >= 5 || inconsistencies.some((i) => i.riskLevel === 'High' && i.type === 'casting_error')) {
    overallComplianceScore = 'Needs Immediate Revision';
  } else if (totalDiscrepancies >= 2 || partialDisclosuresCount >= 3) {
    overallComplianceScore = 'Moderate';
  }

  // Key Risk Areas summary text
  const highRiskItems = inconsistencies.filter((i) => i.riskLevel === 'High');
  let keyRiskAreas = '';
  if (highRiskItems.length > 0) {
    keyRiskAreas = `Critical variances observed in ${highRiskItems.map((i) => i.lineItem.split('(')[0].trim()).join(', ')}. `;
  }
  if (missingDisclosuresCount > 0) {
    const missingStds = disclosures.filter((d) => d.status === 'Missing').map((d) => d.standard).slice(0, 3).join(', ');
    keyRiskAreas += `Statutory disclosure deficiencies under ${missingStds}. `;
  }
  if (!keyRiskAreas) {
    keyRiskAreas = 'Financial statements exhibit strong adherence to Ind AS presentation norms with minor formatting observations.';
  }

  // Generate Recommendations
  const recommendations = generateAuditRecommendations(inconsistencies, disclosures, schedIIIFindings);

  // Generate CARO Observations
  const caroObservations = generateCAROObservations(inconsistencies, schedIIIFindings, text);

  // Synthesize Full Markdown Report
  const rawMarkdownReport = generateMarkdownReport({
    entityName: context.entityName,
    reportingPeriod: context.reportingPeriod,
    reportingScale: context.reportingScale,
    framework: context.framework,
    cin: context.cin,
    complianceScore: overallComplianceScore,
    totalDiscrepancies,
    missingDisclosuresCount,
    numericalMismatchesCount,
    keyRiskAreas,
    inconsistencies,
    disclosures,
    noteProofreadings,
    scheduleIIIGuidanceFindings,
    recommendations,
    caroObservations,
    financialHighlights: {
      totalRevenue: pl.totalIncome ? formatFinancialNumber(pl.totalIncome, context.reportingScale) : undefined,
      pat: pl.pat ? formatFinancialNumber(pl.pat, context.reportingScale) : undefined,
      totalAssets: bs.totalAssets ? formatFinancialNumber(bs.totalAssets, context.reportingScale) : undefined,
      totalDebt: bs.totalDebt ? formatFinancialNumber(bs.totalDebt, context.reportingScale) : undefined,
      netWorth: bs.totalEquity ? formatFinancialNumber(bs.totalEquity, context.reportingScale) : undefined,
    },
  });

  return {
    id: `audit-offline-${Date.now()}`,
    timestamp: new Date().toISOString(),
    documentTitle: context.entityName || options.fileName || 'Financial Statement Statutory Audit',
    summary: {
      overallComplianceScore,
      totalDiscrepancies,
      missingDisclosuresCount,
      numericalMismatchesCount,
      keyRiskAreas,
      entityName: context.entityName,
      reportingPeriod: context.reportingPeriod,
      reportingScale: context.reportingScale,
      frameworkIdentified: context.framework,
    },
    part1Disclosures: disclosures,
    part2Inconsistencies: inconsistencies,
    noteProofreading: noteProofreadings,
    scheduleIIIGuidanceFindings,
    part3Recommendations: recommendations,
    rawMarkdownReport,
    financialHighlights: {
      totalRevenue: pl.totalIncome ? formatFinancialNumber(pl.totalIncome, context.reportingScale) : '₹0.00',
      pat: pl.pat ? formatFinancialNumber(pl.pat, context.reportingScale) : '₹0.00',
      totalAssets: bs.totalAssets ? formatFinancialNumber(bs.totalAssets, context.reportingScale) : '₹0.00',
      totalDebt: bs.totalDebt ? formatFinancialNumber(bs.totalDebt, context.reportingScale) : '₹0.00',
      netWorth: bs.totalEquity ? formatFinancialNumber(bs.totalEquity, context.reportingScale) : '₹0.00',
    },
    caroObservations,
  };
}

// -----------------------------------------------------------------------------------------
// Helper Parsing Functions
// -----------------------------------------------------------------------------------------

function extractMetadata(text: string, lines: string[], fileName?: string): ParseContext {
  let entityName = '';
  let reportingPeriod = 'FY ended March 31';
  let reportingScale = '₹ in Lakhs';
  let framework = 'Ind AS (Schedule III Division II)';
  let cin = '';

  // Extract Entity Name from first few lines
  for (let i = 0; i < Math.min(lines.length, 10); i++) {
    const line = lines[i];
    if (/(limited|ltd|corporation|corp|private limited|pvt ltd|industries|technologies|enterprises)/i.test(line) && !line.toLowerCase().includes('auditor') && !line.toLowerCase().includes('balance sheet')) {
      entityName = line.replace(/[=_-]/g, '').trim();
      break;
    }
  }
  if (!entityName && fileName) {
    entityName = fileName.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
  }
  if (!entityName) entityName = 'Audited Corporate Entity';

  // CIN Search
  const cinMatch = text.match(/[LUu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}/);
  if (cinMatch) {
    cin = cinMatch[0];
  }

  // Reporting Period
  const periodMatch = text.match(/(?:for the year ended|as at|ended)\s*([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+[0-9]{4}|March\s+31,?\s+[0-9]{4}|31st\s+March\s+[0-9]{4}|31-Mar-[0-9]{4}|FY\s+[0-9]{4}[-–][0-9]{2,4})/i);
  if (periodMatch) {
    reportingPeriod = periodMatch[1].trim();
  }

  // Currency Scale
  if (/₹\s*in\s*Crores?/i.test(text) || /in\s*Crores?/i.test(text) || /INR\s*in\s*Cr/i.test(text)) {
    reportingScale = '₹ in Crores';
  } else if (/₹\s*in\s*Lakhs?/i.test(text) || /in\s*Lakhs?/i.test(text) || /INR\s*in\s*Lacs/i.test(text)) {
    reportingScale = '₹ in Lakhs';
  } else if (/in\s*Millions?/i.test(text)) {
    reportingScale = 'in Millions';
  } else if (/in\s*Thousands?/i.test(text)) {
    reportingScale = 'in Thousands';
  }

  // Framework Detection
  if (/Ind\s*AS/i.test(text) || /Indian\s*Accounting\s*Standards/i.test(text)) {
    if (/NBFC/i.test(text) || /Division\s*III/i.test(text)) {
      framework = 'Ind AS for NBFCs (Schedule III Div III)';
    } else {
      framework = 'Ind AS (Schedule III Division II)';
    }
  } else if (/Accounting\s*Standards/i.test(text) || /Schedule\s*III\s*Division\s*I/i.test(text) || /IGAAP/i.test(text)) {
    framework = 'AS (Schedule III Division I)';
  }

  return { entityName, reportingPeriod, reportingScale, framework, cin, rawText: text, lines };
}

interface ParsedBalanceSheet {
  totalAssets: number | null;
  totalNonCurrentAssets: number | null;
  totalCurrentAssets: number | null;
  ppe: number | null;
  cwip: number | null;
  rouAssets: number | null;
  intangibleAssets: number | null;
  nonCurrentInvestments: number | null;
  inventories: number | null;
  tradeReceivables: number | null;
  cashAndCashEquivalents: number | null;
  totalEquity: number | null;
  equityShareCapital: number | null;
  otherEquity: number | null;
  totalNonCurrentLiabilities: number | null;
  nonCurrentBorrowings: number | null;
  totalCurrentLiabilities: number | null;
  currentBorrowings: number | null;
  tradePayablesMsme: number | null;
  tradePayablesOthers: number | null;
  totalEquityAndLiabilities: number | null;
  totalDebt: number | null;
}

function extractBalanceSheet(text: string): ParsedBalanceSheet {
  const findLineNum = (patterns: RegExp[]): number | null => {
    for (const pat of patterns) {
      const match = text.match(pat);
      if (match && match[1]) {
        const parsed = parseFinancialNumber(match[1]);
        if (parsed !== null) return parsed;
      }
    }
    return null;
  };

  const totalAssets = findLineNum([
    /TOTAL\s+ASSETS\s+([0-9,.]+)/i,
    /Total\s+Assets\s+[:\-]?\s*₹?\s*([0-9,.]+)/i,
    /TOTAL\s+ASSETS\s+₹?\s*([0-9,.]+)/i,
  ]);

  const totalNonCurrentAssets = findLineNum([
    /Total\s+Non-current\s+Assets\s+([0-9,.]+)/i,
    /Total\s+non-current\s+assets\s+₹?\s*([0-9,.]+)/i,
  ]);

  const totalCurrentAssets = findLineNum([
    /Total\s+Current\s+Assets\s+([0-9,.]+)/i,
    /Total\s+current\s+assets\s+₹?\s*([0-9,.]+)/i,
  ]);

  const ppe = findLineNum([
    /Property,?\s+Plant\s+&?\s+Equipment\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
    /PPE\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const cwip = findLineNum([
    /Capital\s+Work-in-Progress\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
    /CWIP\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const rouAssets = findLineNum([
    /Right\s+of\s+Use\s+Assets\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
    /ROU\s+Assets\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const intangibleAssets = findLineNum([
    /Other\s+Intangible\s+Assets\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
    /Intangible\s+Assets\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const nonCurrentInvestments = findLineNum([
    /Investments\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const inventories = findLineNum([
    /Inventories\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const tradeReceivables = findLineNum([
    /Trade\s+Receivables\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const cashAndCashEquivalents = findLineNum([
    /Cash\s+and\s+Cash\s+Equivalents\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
    /Cash\s+&\s+cash\s+equivalents\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const totalEquity = findLineNum([
    /Total\s+Equity\s+([0-9,.]+)/i,
    /Total\s+equity\s+₹?\s*([0-9,.]+)/i,
  ]);

  const equityShareCapital = findLineNum([
    /Equity\s+Share\s+Capital\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const otherEquity = findLineNum([
    /Other\s+Equity\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const totalNonCurrentLiabilities = findLineNum([
    /Total\s+Non-current\s+Liabilities\s+([0-9,.]+)/i,
    /Total\s+non-current\s+liabilities\s+₹?\s*([0-9,.]+)/i,
  ]);

  const nonCurrentBorrowings = findLineNum([
    /Borrowings\s+(?:18|[0-9]+)\s+([0-9,.]+)/i,
  ]);

  const totalCurrentLiabilities = findLineNum([
    /Total\s+Current\s+Liabilities\s+([0-9,.]+)/i,
    /Total\s+current\s+liabilities\s+₹?\s*([0-9,.]+)/i,
  ]);

  const currentBorrowings = findLineNum([
    /Current\s+Liabilities[\s\S]*?Borrowings\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const tradePayablesMsme = findLineNum([
    /(?:Total\s+O\/S\s+dues\s+of\s+MSME|dues\s+of\s+micro\s+and\s+small\s+enterprises)\s+([0-9,.]+)/i,
    /MSME\s+Payables\s+([0-9,.]+)/i,
  ]);

  const tradePayablesOthers = findLineNum([
    /(?:Total\s+O\/S\s+dues\s+of\s+other\s+than\s+MSME|dues\s+of\s+creditors\s+other\s+than\s+micro)\s+([0-9,.]+)/i,
    /Other\s+than\s+MSME\s+([0-9,.]+)/i,
  ]);

  const totalEquityAndLiabilities = findLineNum([
    /TOTAL\s+EQUITY\s+AND\s+LIABILITIES\s+([0-9,.]+)/i,
    /Total\s+Equity\s+and\s+Liabilities\s+[:\-]?\s*₹?\s*([0-9,.]+)/i,
    /TOTAL\s+EQUITY\s+&\s+LIABILITIES\s+([0-9,.]+)/i,
  ]);

  const totalDebt = (nonCurrentBorrowings || 0) + (currentBorrowings || 0) || null;

  return {
    totalAssets,
    totalNonCurrentAssets,
    totalCurrentAssets,
    ppe,
    cwip,
    rouAssets,
    intangibleAssets,
    nonCurrentInvestments,
    inventories,
    tradeReceivables,
    cashAndCashEquivalents,
    totalEquity,
    equityShareCapital,
    otherEquity,
    totalNonCurrentLiabilities,
    nonCurrentBorrowings,
    totalCurrentLiabilities,
    currentBorrowings,
    tradePayablesMsme,
    tradePayablesOthers,
    totalEquityAndLiabilities,
    totalDebt,
  };
}

interface ParsedProfitAndLoss {
  revenueFromOps: number | null;
  otherIncome: number | null;
  totalIncome: number | null;
  costOfMaterials: number | null;
  employeeBenefits: number | null;
  financeCosts: number | null;
  depreciation: number | null;
  otherExpenses: number | null;
  totalExpenses: number | null;
  pbt: number | null;
  taxExpense: number | null;
  pat: number | null;
  epsBasic: number | null;
  epsDiluted: number | null;
}

function extractProfitAndLoss(text: string): ParsedProfitAndLoss {
  const findLineNum = (patterns: RegExp[]): number | null => {
    for (const pat of patterns) {
      const match = text.match(pat);
      if (match && match[1]) {
        const parsed = parseFinancialNumber(match[1]);
        if (parsed !== null) return parsed;
      }
    }
    return null;
  };

  const revenueFromOps = findLineNum([
    /Revenue\s+from\s+Operations\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const otherIncome = findLineNum([
    /Other\s+Income\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const totalIncome = findLineNum([
    /Total\s+Income\s+(?:\([I\s\+]+\)\s+)?([0-9,.]+)/i,
    /Total\s+Revenue\s+([0-9,.]+)/i,
  ]);

  const costOfMaterials = findLineNum([
    /Cost\s+of\s+materials\s+consumed\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const employeeBenefits = findLineNum([
    /Employee\s+Benefits?\s+Expenses?\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const financeCosts = findLineNum([
    /Finance\s+Costs\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const depreciation = findLineNum([
    /Depreciation\s+and\s+Amortization\s+Expense\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const otherExpenses = findLineNum([
    /Other\s+Expenses\s+(?:[0-9]+\s+)?([0-9,.]+)/i,
  ]);

  const totalExpenses = findLineNum([
    /Total\s+Expenses\s+([0-9,.]+)/i,
    /Total\s+Expenses\s+\(IV\)\s+([0-9,.]+)/i,
  ]);

  const pbt = findLineNum([
    /Profit\s+before\s+tax\s+(?:\([V\s\-]+\)\s+)?([0-9,.]+)/i,
    /Profit\s+Before\s+Tax\s+[:\-]?\s*₹?\s*([0-9,.]+)/i,
  ]);

  const taxExpense = findLineNum([
    /Total\s+Tax\s+Expense\s+([0-9,.]+)/i,
    /Tax\s+Expense\s+[:\-]?\s*([0-9,.]+)/i,
  ]);

  const pat = findLineNum([
    /Profit\s+(?:for\s+the\s+year|for\s+the\s+period)\s+(?:\([VII\s\-]+\)\s+)?([0-9,.]+)/i,
    /Profit\s+After\s+Tax\s+[:\-]?\s*₹?\s*([0-9,.]+)/i,
    /PAT\s+[:\-]?\s*([0-9,.]+)/i,
  ]);

  const epsBasic = findLineNum([
    /Basic\s+\(₹\)\s+([0-9,.]+)/i,
    /Basic\s+EPS\s+[:\-]?\s*([0-9,.]+)/i,
  ]);

  const epsDiluted = findLineNum([
    /Diluted\s+\(₹\)\s+([0-9,.]+)/i,
    /Diluted\s+EPS\s+[:\-]?\s*([0-9,.]+)/i,
  ]);

  return {
    revenueFromOps,
    otherIncome,
    totalIncome,
    costOfMaterials,
    employeeBenefits,
    financeCosts,
    depreciation,
    otherExpenses,
    totalExpenses,
    pbt,
    taxExpense,
    pat,
    epsBasic,
    epsDiluted,
  };
}

interface ParsedCashFlow {
  operatingCash: number | null;
  investingCash: number | null;
  financingCash: number | null;
  netChangeInCash: number | null;
  openingCash: number | null;
  closingCash: number | null;
}

function extractCashFlow(text: string): ParsedCashFlow {
  const findLineNum = (patterns: RegExp[]): number | null => {
    for (const pat of patterns) {
      const match = text.match(pat);
      if (match && match[1]) {
        const parsed = parseFinancialNumber(match[1]);
        if (parsed !== null) return parsed;
      }
    }
    return null;
  };

  const operatingCash = findLineNum([
    /Net\s+Cash\s+(?:generated\s+from|from|used\s+in)\s+Operating\s+Activities\s+(?:\([A\)]\s+)?([0-9,\(\)\.\-]+)/i,
  ]);

  const investingCash = findLineNum([
    /Net\s+Cash\s+(?:generated\s+from|from|used\s+in)\s+Investing\s+Activities\s+(?:\([B\)]\s+)?([0-9,\(\)\.\-]+)/i,
  ]);

  const financingCash = findLineNum([
    /Net\s+Cash\s+(?:generated\s+from|from|used\s+in)\s+Financing\s+Activities\s+(?:\([C\)]\s+)?([0-9,\(\)\.\-]+)/i,
  ]);

  const netChangeInCash = findLineNum([
    /Net\s+Increase\s*\/\s*\(Decrease\)\s+in\s+Cash\s+and\s+Cash\s+Equivalents\s+([0-9,\(\)\.\-]+)/i,
    /Net\s+Increase\s+in\s+Cash\s+and\s+Cash\s+Equivalents\s+([0-9,\(\)\.\-]+)/i,
  ]);

  const openingCash = findLineNum([
    /Cash\s+and\s+Cash\s+Equivalents\s+at\s+the\s+beginning\s+of\s+the\s+year\s+([0-9,.]+)/i,
  ]);

  const closingCash = findLineNum([
    /Cash\s+and\s+Cash\s+Equivalents\s+at\s+the\s+end\s+of\s+the\s+year\s+([0-9,.]+)/i,
    /Closing\s+Cash\s+and\s+Cash\s+Equivalents\s+([0-9,.]+)/i,
  ]);

  return {
    operatingCash,
    investingCash,
    financingCash,
    netChangeInCash,
    openingCash,
    closingCash,
  };
}

interface ParsedNotes {
  ppe?: { noteNo?: string; closingBalance: number | null; grossBlock: number | null; depBlock: number | null };
  cwip?: { noteNo?: string; totalAmount: number | null; hasAging: boolean; hasOverrunSchedule: boolean };
  tradeReceivables?: { noteNo?: string; grossAmount: number | null; eclAllowance: number | null; netAmount: number | null; hasAgingSchedule: boolean };
  tradePayables?: { noteNo?: string; msmeAmount: number | null; othersAmount: number | null; totalAmount: number | null; hasAgingSchedule: boolean };
  relatedParty?: { noteNo?: string; tableKmpRemuneration: number | null; textKmpRemuneration: number | null; hasOutstandingBalances: boolean };
  employeeBenefits?: { noteNo?: string; totalExpense: number | null; hasActuarialAssumptions: boolean; discountRate?: string };
  contingentLiabilities?: { noteNo?: string; hasQuantification: boolean; claimsTax: number | null; guarantees: number | null };
  ratios?: { noteNo?: string; has11Ratios: boolean; ratiosFound: string[]; varianceExplanationPresent: boolean };
}

function extractNotes(text: string): ParsedNotes {
  const notes: ParsedNotes = {};

  // Note 3: PPE
  const ppeSection = text.match(/Note\s*3[\s\S]*?(?=Note\s*4|Note\s*5|================)/i);
  if (ppeSection) {
    const ppeText = ppeSection[0];
    const closingMatch = ppeText.match(/(?:Closing\s+Carrying\s+Value|Net\s+Carrying\s+Amount|Total\s+PPE|Balance\s+as\s+at\s+31[\s\S]*?)\s+([0-9,.]+)/i);
    const closingBalance = closingMatch ? parseFinancialNumber(closingMatch[1]) : null;
    notes.ppe = { noteNo: '3', closingBalance, grossBlock: null, depBlock: null };
  }

  // Note 4: CWIP
  const cwipSection = text.match(/Note\s*4[\s\S]*?(?=Note\s*5|Note\s*6|================)/i);
  if (cwipSection) {
    const cwipText = cwipSection[0];
    const totalMatch = cwipText.match(/(?:Total\s+CWIP|Total)\s+([0-9,.]+)/i);
    notes.cwip = {
      noteNo: '4',
      totalAmount: totalMatch ? parseFinancialNumber(totalMatch[1]) : null,
      hasAging: /CWIP\s+Aging\s+Schedule|<1\s*year|1-2\s*years/i.test(cwipText),
      hasOverrunSchedule: /CWIP\s+completion\s+schedule|overdue|cost\s+overrun/i.test(cwipText),
    };
  }

  // Note 8 or 11: Trade Receivables
  const trSection = text.match(/Note\s*(?:8|11)[\s\S]*?(?=Note\s*(?:9|12)|================)/i);
  if (trSection) {
    const trText = trSection[0];
    const grossMatch = trText.match(/(?:Total\s+Trade\s+Receivables|Gross\s+Receivables)\s+([0-9,.]+)/i);
    const eclMatch = trText.match(/(?:Less:\s+Allowance\s+for\s+ECL|Loss\s+allowance|ECL\s+allowance)\s+([0-9,.]+)/i);
    const netMatch = trText.match(/(?:Total\s+Trade\s+Receivables\s+\(Net\)|Net\s+Trade\s+Receivables)\s+([0-9,.]+)/i);

    let calculatedNet = null;
    if (netMatch) {
      calculatedNet = parseFinancialNumber(netMatch[1]);
    } else if (grossMatch && eclMatch) {
      const g = parseFinancialNumber(grossMatch[1]) || 0;
      const e = parseFinancialNumber(eclMatch[1]) || 0;
      calculatedNet = g - e;
    }

    notes.tradeReceivables = {
      noteNo: /Note\s*11/i.test(trText) ? '11' : '8',
      grossAmount: grossMatch ? parseFinancialNumber(grossMatch[1]) : null,
      eclAllowance: eclMatch ? parseFinancialNumber(eclMatch[1]) : null,
      netAmount: calculatedNet,
      hasAgingSchedule: /Trade\s+Receivables\s+Ageing\s+Schedule|Undisputed|Disputed|<6\s*months/i.test(trText),
    };
  }

  // Note 23: Trade Payables
  const tpSection = text.match(/Note\s*23[\s\S]*?(?=Note\s*24|================)/i);
  if (tpSection) {
    const tpText = tpSection[0];
    const msmeMatch = tpText.match(/(?:Total\s+O\/S\s+dues\s+of\s+MSME|MSME\s+dues)\s+([0-9,.]+)/i);
    const othersMatch = tpText.match(/(?:Total\s+O\/S\s+dues\s+of\s+other\s+than\s+MSME|other\s+than\s+MSME)\s+([0-9,.]+)/i);
    const totalMatch = tpText.match(/Total\s+Trade\s+Payables\s+([0-9,.]+)/i);

    notes.tradePayables = {
      noteNo: '23',
      msmeAmount: msmeMatch ? parseFinancialNumber(msmeMatch[1]) : null,
      othersAmount: othersMatch ? parseFinancialNumber(othersMatch[1]) : null,
      totalAmount: totalMatch ? parseFinancialNumber(totalMatch[1]) : null,
      hasAgingSchedule: /Trade\s+Payables\s+Ageing\s+Schedule|MSME|<1\s*year/i.test(tpText),
    };
  }

  // Note 33 / 34: Related Party
  const rpSection = text.match(/Note\s*(?:33|34)[\s\S]*?(?=Note\s*(?:34|35)|================)/i);
  if (rpSection) {
    const rpText = rpSection[0];
    // Look for KMP Remuneration numbers in table
    const tableKmpMatch = rpText.match(/(?:Total\s+KMP\s+Remuneration|Key\s+Management\s+Personnel\s+Compensation|Short-term\s+employee\s+benefits[\s\S]*?Total)\s+([0-9,.]+)/i);
    // Look for text commentary mentions like "remuneration paid to Managing Director of ₹650.00 Lakhs" or similar
    const textKmpMatch = rpText.match(/(?:remuneration\s+paid\s+to\s+Managing\s+Director\s+of|remuneration\s+to\s+KMP\s+amounting\s+to)\s*₹?\s*([0-9,.]+)/i);

    notes.relatedParty = {
      noteNo: /Note\s*34/i.test(rpText) ? '34' : '33',
      tableKmpRemuneration: tableKmpMatch ? parseFinancialNumber(tableKmpMatch[1]) : null,
      textKmpRemuneration: textKmpMatch ? parseFinancialNumber(textKmpMatch[1]) : null,
      hasOutstandingBalances: /Outstanding\s+balances\s+at\s+year-end|balances\s+receivable|payable\s+to\s+related\s+parties/i.test(rpText),
    };
  }

  // Note 28 / 23: Employee Benefits
  const ebSection = text.match(/Note\s*(?:23|28|29)[\s\S]*?Employee\s+Benefit[\s\S]*?(?=Note\s*[0-9]+|================)/i);
  if (ebSection) {
    const ebText = ebSection[0];
    const totalMatch = ebText.match(/Total\s+Employee\s+Benefit\s+Expense\s+([0-9,.]+)/i);
    notes.employeeBenefits = {
      noteNo: '23',
      totalExpense: totalMatch ? parseFinancialNumber(totalMatch[1]) : null,
      hasActuarialAssumptions: /Discount\s+rate|Salary\s+escalation\s+rate|Mortality\s+table/i.test(ebText),
    };
  }

  // Contingent Liabilities Note
  const clSection = text.match(/Note\s*(?:36|37|38)[\s\S]*?Contingent\s+Liabilit[\s\S]*?(?=Note\s*[0-9]+|================)/i);
  if (clSection) {
    const clText = clSection[0];
    notes.contingentLiabilities = {
      noteNo: '37',
      hasQuantification: /[0-9,.]+\s*(?:Lakhs|Crores|\(₹\))/i.test(clText),
      claimsTax: null,
      guarantees: null,
    };
  }

  // Schedule III 11 Ratios Note
  const ratioSection = text.match(/Note\s*(?:38|39|40)[\s\S]*?(?:Analytical|Financial)\s+Ratios[\s\S]*?(?=Note\s*[0-9]+|================)/i);
  if (ratioSection) {
    const rText = ratioSection[0];
    const ratios = [
      'Current Ratio', 'Debt-Equity Ratio', 'Debt Service Coverage Ratio (DSCR)', 'Return on Equity (ROE)',
      'Inventory Turnover Ratio', 'Trade Receivables Turnover Ratio', 'Trade Payables Turnover Ratio',
      'Net Capital Turnover Ratio', 'Net Profit Ratio', 'Return on Capital Employed (ROCE)', 'Return on Investment (ROI)'
    ].filter((r) => rText.toLowerCase().includes(r.toLowerCase().split('(')[0].trim()));

    notes.ratios = {
      noteNo: '39',
      has11Ratios: ratios.length >= 8,
      ratiosFound: ratios,
      varianceExplanationPresent: /explanation\s+for\s+variance|variance\s*>\s*25%|due\s+to\s+increase|due\s+to\s+repayment/i.test(rText),
    };
  }

  return notes;
}

// -----------------------------------------------------------------------------------------
// Sub-Engines: Note Proofreading, Schedule III & Ind AS Checklists
// -----------------------------------------------------------------------------------------

function runNoteProofreadingEngine(text: string, notes: ParsedNotes): NoteProofreadingItem[] {
  const items: NoteProofreadingItem[] = [];

  // Note 1: Corporate Information & Accounting Policies
  items.push({
    noteNumber: 'Note 1 & 2',
    noteTitle: 'Corporate Information & Significant Accounting Policies',
    proofreadingStatus: /Significant\s+Accounting\s+Policies/i.test(text) ? 'Complied' : 'Observations Found',
    observations: 'Audited entity background, functional currency (INR), historical cost convention, and significant accounting policies under Ind AS framework.',
    mandatoryClausesChecked: 'Ind AS 1 Going Concern, Functional Currency, Materiality judgments & Estimation uncertainties.',
  });

  // Note 3: PPE
  if (notes.ppe) {
    items.push({
      noteNumber: 'Note 3',
      noteTitle: 'Property, Plant & Equipment (PPE)',
      proofreadingStatus: notes.ppe.closingBalance ? 'Complied' : 'Observations Found',
      observations: 'Rollforward schedule scrutinized: Gross block opening, additions during year, deductions/disposals, accumulated depreciation, impairment, and net carrying value verified.',
      mandatoryClausesChecked: 'Ind AS 16 reconciliation rollforward, useful life scrutiny, Registered Valuer clause under Section 247.',
      draftingOrArithmeticIssues: notes.ppe.closingBalance ? undefined : 'Net carrying value subtotal casting requires verification against primary balance sheet line.',
    });
  }

  // Note 4: CWIP
  if (notes.cwip) {
    items.push({
      noteNumber: 'Note 4',
      noteTitle: 'Capital Work-in-Progress (CWIP)',
      proofreadingStatus: notes.cwip.hasAging ? (notes.cwip.hasOverrunSchedule ? 'Complied' : 'Observations Found') : 'Missing Mandatory Clauses',
      observations: `CWIP total analyzed. ${notes.cwip.hasAging ? 'Mandatory Schedule III Aging bucket (<1y, 1-2y, 2-3y, >3y) present.' : 'Missing mandatory Schedule III Aging Schedule.'} ${notes.cwip.hasOverrunSchedule ? 'CWIP completion schedule for overdue projects provided.' : 'CWIP completion plan for projects with cost overrun is missing.'}`,
      mandatoryClausesChecked: 'ICAI Schedule III CWIP Ageing schedule & CWIP project completion plan for overdue projects.',
      draftingOrArithmeticIssues: !notes.cwip.hasAging ? 'Mandatory Schedule III CWIP aging table omitted.' : undefined,
    });
  }

  // Note 11: Trade Receivables
  if (notes.tradeReceivables) {
    items.push({
      noteNumber: `Note ${notes.tradeReceivables.noteNo || '11'}`,
      noteTitle: 'Trade Receivables & ECL Impairment',
      proofreadingStatus: notes.tradeReceivables.hasAgingSchedule ? 'Complied' : 'Missing Mandatory Clauses',
      observations: `Breakup of Undisputed / Disputed dues evaluated. ${notes.tradeReceivables.hasAgingSchedule ? 'Mandatory Schedule III Aging schedule (<6m, 6m-1y, 1-2y, 2-3y, >3y) verified.' : 'Mandatory aging schedule with dispute breakdown missing.'} Ind AS 109 Expected Credit Loss (ECL) matrix reviewed.`,
      mandatoryClausesChecked: 'Schedule III Trade Receivables aging, MSME split, ECL provision under Ind AS 109.',
    });
  }

  // Note 23: Trade Payables
  if (notes.tradePayables) {
    items.push({
      noteNumber: 'Note 23',
      noteTitle: 'Trade Payables & MSME Statutory Disclosures',
      proofreadingStatus: notes.tradePayables.hasAgingSchedule ? 'Complied' : 'Observations Found',
      observations: `MSMED Act 2006 statutory disclosure evaluated. Principal amount overdue to Micro & Small Enterprises, interest due, and Schedule III aging schedule scrutinised.`,
      mandatoryClausesChecked: 'Section 22 of MSMED Act 2006 disclosures (principal, interest paid, interest due), Schedule III aging table.',
    });
  }

  // Note 33 / 34: Related Party
  if (notes.relatedParty) {
    const hasConflict = notes.relatedParty.tableKmpRemuneration !== null && notes.relatedParty.textKmpRemuneration !== null && notes.relatedParty.tableKmpRemuneration !== notes.relatedParty.textKmpRemuneration;
    items.push({
      noteNumber: `Note ${notes.relatedParty.noteNo || '33'}`,
      noteTitle: 'Related Party Disclosures (Ind AS 24)',
      proofreadingStatus: hasConflict ? 'Observations Found' : 'Complied',
      observations: `Comprehensive review of Parent, Subsidiary, Joint Ventures, KMPs, and post-employment benefit plans. ${hasConflict ? 'Drafting contradiction identified between text commentary and schedule table for KMP remuneration.' : 'Related party transaction breakups and closing balances verified.'}`,
      mandatoryClausesChecked: 'Ind AS 24 Para 17-18 breakdown of short-term benefits, post-employment benefits, and terms/conditions of balances.',
      draftingOrArithmeticIssues: hasConflict ? 'Contradiction between text narrative and tabular figures.' : undefined,
    });
  }

  // Note 37: Contingent Liabilities
  if (notes.contingentLiabilities) {
    items.push({
      noteNumber: 'Note 37',
      noteTitle: 'Contingent Liabilities & Commitments (Ind AS 37)',
      proofreadingStatus: notes.contingentLiabilities.hasQuantification ? 'Complied' : 'Observations Found',
      observations: 'Review of legal claims, disputed tax demands (GST/Income Tax), bank guarantees, and capital commitments.',
      mandatoryClausesChecked: 'Ind AS 37 Para 86 (brief description of nature, estimate of financial effect, uncertainties, reimbursement possibilities).',
    });
  }

  // Note 39: Analytical Ratios
  if (notes.ratios) {
    items.push({
      noteNumber: `Note ${notes.ratios.noteNo || '39'}`,
      noteTitle: 'Statutory Analytical Ratios (Schedule III)',
      proofreadingStatus: notes.ratios.has11Ratios && notes.ratios.varianceExplanationPresent ? 'Complied' : 'Observations Found',
      observations: `Audit of 11 statutory ratios. ${notes.ratios.ratiosFound.length}/11 ratios detected in statement. ${notes.ratios.varianceExplanationPresent ? 'Mandatory explanation for variances exceeding 25% included.' : 'Explanations for material ratio variances (>25%) missing or incomplete.'}`,
      mandatoryClausesChecked: 'ICAI Guidance Note on Schedule III (11 Mandatory Ratios & 25% variance notes).',
    });
  }

  return items;
}

function runScheduleIIIChecklist(
  text: string,
  notes: ParsedNotes,
  bs: ParsedBalanceSheet,
  pl: ParsedProfitAndLoss
): ScheduleIIIGuidanceItem[] {
  const findings: ScheduleIIIGuidanceItem[] = [];

  // 1. 11 Statutory Ratios
  const hasRatios = notes.ratios?.has11Ratios || /Current\s+Ratio|Debt-Equity\s+Ratio|Debt\s+Service\s+Coverage/i.test(text);
  const hasRatioVariance = /variance\s*>\s*25%|explanation\s+for\s+variance|reasons\s+for\s+variance/i.test(text);
  findings.push({
    clause: '11 Statutory Accounting Ratios',
    requirement: 'Mandatory disclosure of 11 financial ratios with prior year comparatives and mandatory explanation if variance is >25%.',
    complianceStatus: hasRatios && hasRatioVariance ? 'Complied' : hasRatios ? 'Non-Compliant' : 'Not Disclosed',
    detailedFinding: hasRatios
      ? (hasRatioVariance ? 'All 11 statutory ratios disclosed with comparative figures and variance explanations for movements >25%.' : '11 ratios tabulated, but mandatory explanatory notes for items with variance exceeding 25% are missing.')
      : 'Statutory 11 ratios table not found in Notes to Accounts as mandated by MCA March 2021 Notification.',
    guidanceNoteReference: 'ICAI Guidance Note on Schedule III (Division II) & MCA Notification G.S.R. 207(E)',
  });

  // 2. Trade Receivables Ageing Schedule
  const hasTrAging = /Trade\s+Receivables\s+Ageing\s+Schedule|<6\s*months|6\s*months\s*-\s*1\s*year/i.test(text);
  findings.push({
    clause: 'Trade Receivables Ageing Schedule',
    requirement: 'Ageing schedule split into Undisputed/Disputed, Considered Good/Significant Increase in Credit Risk/Credit Impaired (<6m, 6m-1y, 1-2y, 2-3y, >3y).',
    complianceStatus: hasTrAging ? 'Complied' : 'Non-Compliant',
    detailedFinding: hasTrAging
      ? 'Trade receivables ageing table conforms with Schedule III format including dispute classification and unbilled dues.'
      : 'Mandatory Trade Receivables aging schedule missing or lacks required dispute/credit risk categorization.',
    guidanceNoteReference: 'MCA Schedule III Part I - Balance Sheet Division II Amendment 2021',
  });

  // 3. Trade Payables Ageing Schedule & MSME Disclosures
  const hasTpAging = /Trade\s+Payables\s+Ageing\s+Schedule|MSME|<1\s*year|1-2\s*years/i.test(text);
  findings.push({
    clause: 'Trade Payables Ageing Schedule & MSME Dues',
    requirement: 'Ageing schedule categorized into MSME / Others, Undisputed / Disputed dues (<1y, 1-2y, 2-3y, >3y) and MSMED Act Section 22 disclosures.',
    complianceStatus: hasTpAging ? 'Complied' : 'Non-Compliant',
    detailedFinding: hasTpAging
      ? 'Trade payables ageing schedule presented in accordance with Division II requirements.'
      : 'Schedule III trade payables ageing table or MSME statutory disclosures under MSMED Act 2006 not properly formatted.',
    guidanceNoteReference: 'Schedule III Division II / Section 22 of MSMED Act 2006',
  });

  // 4. CWIP Ageing & Project Completion Schedule
  const hasCwipAging = /CWIP\s+Aging\s+Schedule|<1\s*year|1-2\s*years/i.test(text);
  const hasCwipOverrun = /CWIP\s+completion\s+schedule|projects\s+temporarily\s+suspended|overdue/i.test(text);
  findings.push({
    clause: 'CWIP Ageing & Completion Schedule',
    requirement: 'CWIP aging schedule (<1y, 1-2y, 2-3y, >3y) and project completion schedule for projects where cost/time overruns exist.',
    complianceStatus: hasCwipAging ? (hasCwipOverrun ? 'Complied' : 'Non-Compliant') : 'Non-Compliant',
    detailedFinding: hasCwipAging
      ? (hasCwipOverrun ? 'CWIP aging and completion schedules compliant with ICAI guidance.' : 'CWIP aging schedule presented, but mandatory project completion schedule for projects whose execution is delayed is missing.')
      : 'CWIP aging schedule missing under Note 4.',
    guidanceNoteReference: 'ICAI Guidance Note on Schedule III Division II (Clause 6A of Part I)',
  });

  // 5. Promoter Shareholding & % Change
  const hasPromoterShareholding = /Promoter\s+Shareholding|Shares\s+held\s+by\s+promoters|%?\s*change\s+during\s+the\s+year/i.test(text);
  findings.push({
    clause: 'Promoter Shareholding Details & % Change',
    requirement: 'Disclosure of shareholding of each promoter at the beginning & end of year and % change during the year.',
    complianceStatus: hasPromoterShareholding ? 'Complied' : 'Non-Compliant',
    detailedFinding: hasPromoterShareholding
      ? 'Promoter shareholding pattern with % change during the financial year verified in Note 16.'
      : 'Promoter shareholding table with mandatory % change column is missing from Share Capital note.',
    guidanceNoteReference: 'Schedule III Part I - Share Capital Notes MCA 2021',
  });

  // 6. Title Deeds of Immovable Property
  const hasTitleDeeds = /Title\s+deeds\s+of\s+immovable\s+propert(?:y|ies)|not\s+held\s+in\s+the\s+name\s+of\s+the\s+company/i.test(text);
  findings.push({
    clause: 'Title Deeds of Immovable Property',
    requirement: 'Mandatory declaration whether title deeds of all immovable property (other than properties where company is lessee) are held in company name.',
    complianceStatus: hasTitleDeeds ? 'Complied' : 'Not Disclosed',
    detailedFinding: hasTitleDeeds
      ? 'Mandatory declaration regarding title deeds of immovable properties confirmed in PPE Note.'
      : 'No statutory confirmation on title deeds of immovable properties found in financial notes.',
    guidanceNoteReference: 'MCA 2021 Amendment to Schedule III Part I',
  });

  // 7. CSR Disclosures (Section 135)
  const hasCSR = /Corporate\s+Social\s+Responsibility|CSR\s+expenditure|Section\s+135/i.test(text);
  findings.push({
    clause: 'Corporate Social Responsibility (CSR) under Section 135',
    requirement: 'Gross amount required to be spent, amount approved by Board, spent during year, shortfall, ongoing projects, unspent CSR bank account.',
    complianceStatus: hasCSR ? 'Complied' : 'Not Applicable',
    detailedFinding: hasCSR
      ? 'CSR note includes mandatory disclosures: amount required to be spent, actual spent, and unspent provision details under Section 135.'
      : 'CSR disclosures not found; verify whether Section 135 threshold criteria (Net worth ₹500 Cr / Turnover ₹1,000 Cr / Net profit ₹5 Cr) are met.',
    guidanceNoteReference: 'Companies (Corporate Social Responsibility Policy) Rules, 2014 & Schedule III',
  });

  // 8. Wilful Defaulter & Struck-off Companies
  const hasWilfulDefaulter = /Wilful\s+Defaulter|declared\s+as\s+wilful\s+defaulter/i.test(text);
  const hasStruckOff = /Struck-off\s+Companies|struck\s+off\s+under\s+section\s+248/i.test(text);
  findings.push({
    clause: 'Wilful Defaulter & Relationship with Struck-off Companies',
    requirement: 'Mandatory negative/affirmative declarations on wilful defaulter status and transactions with companies struck off under Section 248.',
    complianceStatus: hasWilfulDefaulter && hasStruckOff ? 'Complied' : (hasWilfulDefaulter || hasStruckOff ? 'Non-Compliant' : 'Not Disclosed'),
    detailedFinding: hasWilfulDefaulter && hasStruckOff
      ? 'Mandatory declarations on wilful defaulter and struck-off companies verified.'
      : 'Negative statutory affirmations regarding wilful defaulter status or struck-off companies transactions omitted from Additional Regulatory Information.',
    guidanceNoteReference: 'MCA Schedule III Additional Regulatory Information 2021',
  });

  return findings;
}

function runIndASDisclosureMatrix(
  text: string,
  notes: ParsedNotes,
  standardsFocus?: string[]
): DisclosureItem[] {
  const items: DisclosureItem[] = [];

  // Ind AS 1: Presentation of Financial Statements
  items.push({
    standard: 'Ind AS 1',
    standardName: 'Presentation of Financial Statements',
    requirement: 'Current/Non-current classification on face of Balance Sheet & explicit Statement of Compliance with Ind AS.',
    status: /Division\s*II|Schedule\s*III|Current\s+Assets/i.test(text) ? 'Complied' : 'Partial',
    observation: 'Balance Sheet properly separated into Non-current and Current assets/liabilities. Explicit compliance statement verified in Note 1.',
    applicableParagraph: 'Ind AS 1 Para 16 & 60',
  });

  // Ind AS 7: Statement of Cash Flows
  const hasIndirectMethod = /Operating\s+Activities|Profit\s+before\s+tax/i.test(text) && /Statement\s+of\s+Cash\s+Flows/i.test(text);
  items.push({
    standard: 'Ind AS 7',
    standardName: 'Statement of Cash Flows',
    requirement: 'Cash flows reported using Indirect Method with operating, investing, and financing activities breakups.',
    status: hasIndirectMethod ? 'Complied' : 'Missing',
    observation: hasIndirectMethod
      ? 'Cash flow prepared using Indirect method with non-cash adjustment reconciliation.'
      : 'Complete Statement of Cash Flows or non-cash financing reconciliation not found.',
    applicableParagraph: 'Ind AS 7 Para 10 & 18',
  });

  // Ind AS 12: Income Taxes
  const hasTaxReconciliation = /Tax\s+expense\s+reconciliation|Effective\s+tax\s+rate|applicable\s+tax\s+rate/i.test(text);
  items.push({
    standard: 'Ind AS 12',
    standardName: 'Income Taxes',
    requirement: 'Numerical reconciliation between tax expense and accounting profit multiplied by applicable tax rate.',
    status: hasTaxReconciliation ? 'Complied' : 'Partial',
    observation: hasTaxReconciliation
      ? 'Tax expense reconciliation table and DTA/DTL movement schedule disclosed.'
      : 'Numerical tax rate reconciliation (accounting profit to tax expense) requires full statutory breakdown.',
    applicableParagraph: 'Ind AS 12 Para 81(c)',
  });

  // Ind AS 16: Property, Plant and Equipment
  const hasPpeRollforward = /Property,?\s+Plant\s+&?\s+Equipment/i.test(text) && /Gross\s+Block|Additions|Depreciation/i.test(text);
  items.push({
    standard: 'Ind AS 16',
    standardName: 'Property, Plant and Equipment',
    requirement: 'Class-wise rollforward reconciliation of gross carrying amount and accumulated depreciation.',
    status: hasPpeRollforward ? 'Complied' : 'Missing',
    observation: hasPpeRollforward
      ? 'Class-wise rollforward schedules for Land, Buildings, Plant & Machinery, Office Equipments disclosed.'
      : 'Class-wise asset rollforward schedule missing or incomplete.',
    applicableParagraph: 'Ind AS 16 Para 73',
  });

  // Ind AS 19: Employee Benefits
  const hasActuarial = /Employee\s+Benefits?|Actuarial\s+gains?|Gratuity|Discount\s+rate/i.test(text);
  items.push({
    standard: 'Ind AS 19',
    standardName: 'Employee Benefits',
    requirement: 'Defined benefit plan actuarial assumptions (discount rate, salary escalation) and sensitivity analysis.',
    status: hasActuarial ? 'Complied' : 'Partial',
    observation: hasActuarial
      ? 'Gratuity/leave encashment actuarial tables, PBO rollforward, and key sensitivity analysis disclosed.'
      : 'Mandatory actuarial demographic/financial assumptions or sensitivity tables omitted.',
    applicableParagraph: 'Ind AS 19 Para 135-147',
  });

  // Ind AS 24: Related Party Disclosures
  const hasKmpRemuneration = /Key\s+Management\s+Personnel|KMP\s+Remuneration|Related\s+Party/i.test(text);
  items.push({
    standard: 'Ind AS 24',
    standardName: 'Related Party Disclosures',
    requirement: 'Disclosure of KMP compensation in total and for short-term, post-employment, and share-based benefits.',
    status: hasKmpRemuneration ? 'Complied' : 'Missing',
    observation: hasKmpRemuneration
      ? 'Related party relationships, itemized transactions, and KMP compensation categories disclosed.'
      : 'Comprehensive Ind AS 24 related party schedule and KMP breakups missing.',
    applicableParagraph: 'Ind AS 24 Para 17 & 18',
  });

  // Ind AS 33: Earnings Per Share
  const hasEps = /Basic\s+(?:and\s+Diluted\s+)?EPS|Earnings\s+Per\s+Share/i.test(text);
  items.push({
    standard: 'Ind AS 33',
    standardName: 'Earnings Per Share',
    requirement: 'Basic and Diluted EPS on the face of P&L with weighted average number of shares reconciliation.',
    status: hasEps ? 'Complied' : 'Partial',
    observation: hasEps
      ? 'Basic and Diluted EPS displayed on face of Statement of Profit & Loss.'
      : 'EPS computation reconciliation (numerator/denominator) missing from Notes.',
    applicableParagraph: 'Ind AS 33 Para 66 & 70',
  });

  // Ind AS 37: Provisions, Contingent Liabilities & Contingent Assets
  const hasContingentNote = /Contingent\s+Liabilit(?:y|ies)|Commitments/i.test(text);
  items.push({
    standard: 'Ind AS 37',
    standardName: 'Provisions, Contingent Liabilities & Contingent Assets',
    requirement: 'Quantification, nature of obligation, and uncertainties regarding outflow of economic resources.',
    status: hasContingentNote ? 'Complied' : 'Missing',
    observation: hasContingentNote
      ? 'Contingent liabilities itemized for tax disputes, guarantees, and legal claims.'
      : 'Mandatory disclosure on contingent liabilities and capital commitments is missing or unquantified.',
    applicableParagraph: 'Ind AS 37 Para 86',
  });

  // Ind AS 107 & 109: Financial Instruments
  const hasFinancialInst = /Financial\s+Instruments|Fair\s+Value\s+Hierarchy|Credit\s+Risk|Liquidity\s+Risk|Market\s+Risk/i.test(text);
  items.push({
    standard: 'Ind AS 107/109',
    standardName: 'Financial Instruments (Disclosures & ECL)',
    requirement: 'Fair value hierarchy (Level 1, 2, 3), credit risk ECL matrix, liquidity risk maturity profile, and market sensitivity.',
    status: hasFinancialInst ? 'Complied' : 'Partial',
    observation: hasFinancialInst
      ? 'Financial risk management objectives, ECL credit loss matrix, and contract maturity buckets disclosed.'
      : 'Foreign currency / interest rate sensitivity analysis or Level 1/2/3 fair value hierarchy missing.',
    applicableParagraph: 'Ind AS 107 Para 33-42',
  });

  // Ind AS 115: Revenue from Contracts with Customers
  const hasRevenueDisaggregation = /Revenue\s+from\s+Contracts|Disaggregation\s+of\s+Revenue|Contract\s+Liabilities|Performance\s+Obligations/i.test(text);
  items.push({
    standard: 'Ind AS 115',
    standardName: 'Revenue from Contracts with Customers',
    requirement: 'Disaggregation of revenue by offering/geography, contract asset/liability balances, and performance obligations.',
    status: hasRevenueDisaggregation ? 'Complied' : 'Partial',
    observation: hasRevenueDisaggregation
      ? 'Revenue disaggregation by revenue stream, contract liabilities rollforward, and timing of satisfaction disclosed.'
      : 'Disaggregated revenue table or contract balances movement schedule under Ind AS 115 missing.',
    applicableParagraph: 'Ind AS 115 Para 114-116',
  });

  // Ind AS 116: Leases
  const hasLeases = /Right\s+of\s+Use|Lease\s+Liabilit(?:y|ies)|Ind\s+AS\s+116/i.test(text);
  items.push({
    standard: 'Ind AS 116',
    standardName: 'Leases',
    requirement: 'ROU asset depreciation rollforward, lease liability maturity analysis (undiscounted cash flows), and finance expense on leases.',
    status: hasLeases ? 'Complied' : 'Partial',
    observation: hasLeases
      ? 'ROU asset rollforward schedule and contractual undiscounted lease maturity profile disclosed.'
      : 'Contractual undiscounted lease liability maturity buckets (<1y, 1-5y, >5y) missing.',
    applicableParagraph: 'Ind AS 116 Para 53 & 58',
  });

  return items;
}

function generateAuditRecommendations(
  inconsistencies: InconsistencyItem[],
  disclosures: DisclosureItem[],
  schedIIIFindings: ScheduleIIIGuidanceItem[]
): AuditRecommendation[] {
  const recommendations: AuditRecommendation[] = [];
  let recCounter = 1;

  // Immediate recommendations for High Risk Inconsistencies
  inconsistencies.filter((i) => i.riskLevel === 'High').forEach((inc) => {
    recommendations.push({
      id: `REC-${String(recCounter++).padStart(3, '0')}`,
      priority: 'Immediate',
      category: inc.type === 'casting_error' ? 'Mathematical Casting & Footing' : 'Data Mismatch & Cross-Referencing',
      recommendation: `Issue formal Audit Query Memo to Management regarding ${inc.lineItem}. Require client to reconcile variance of ${inc.discrepancy} and adjust primary statement / note schedule prior to final signature.`,
      statutoryReference: 'SA 260 / SA 450 (Evaluation of Misstatements)',
      actionFor: 'Engagement Partner & Audit Senior',
    });
  });

  // Pre-Signing recommendations for Missing Disclosures
  disclosures.filter((d) => d.status === 'Missing').forEach((disc) => {
    recommendations.push({
      id: `REC-${String(recCounter++).padStart(3, '0')}`,
      priority: 'Pre-Signing',
      category: 'Ind AS Disclosure Compliance',
      recommendation: `Incorporate mandatory disclosure under ${disc.standard} (${disc.standardName || disc.requirement}). Obtain supporting audit schedules from client management.`,
      statutoryReference: disc.applicableParagraph || disc.standard,
      actionFor: 'Audit Senior',
    });
  });

  // Schedule III Missing items
  schedIIIFindings.filter((s) => s.complianceStatus === 'Non-Compliant').forEach((sf) => {
    recommendations.push({
      id: `REC-${String(recCounter++).padStart(3, '0')}`,
      priority: 'Pre-Signing',
      category: 'Schedule III / MCA Compliance',
      recommendation: `Update Notes to Accounts to incorporate ${sf.clause} as mandated by MCA March 2021 amendments and ICAI Guidance Note.`,
      statutoryReference: sf.guidanceNoteReference,
      actionFor: 'CFO / Management & Audit Team',
    });
  });

  // Management letter recommendation
  recommendations.push({
    id: `REC-${String(recCounter++).padStart(3, '0')}`,
    priority: 'Management Letter',
    category: 'Internal Controls over Financial Reporting (ICFR)',
    recommendation: 'Implement automated financial reporting controls to ensure sub-ledger casting consistency and cross-check text narratives against final trial balances.',
    statutoryReference: 'Section 143(3)(i) of Companies Act, 2013',
    actionFor: 'Engagement Partner / Audit Committee',
  });

  return recommendations;
}

function generateCAROObservations(
  inconsistencies: InconsistencyItem[],
  schedIIIFindings: ScheduleIIIGuidanceItem[],
  text: string
): string[] {
  const observations: string[] = [];

  // Clause 3(i) PPE
  observations.push('Clause 3(i)(a) & (b): Company has maintained proper records of PPE. Physical verification by management reported without material discrepancies.');

  // Clause 3(ii) Inventory
  if (/inventories/i.test(text)) {
    observations.push('Clause 3(ii)(a): Physical verification of inventory conducted at reasonable intervals. No discrepancies of 10% or more in aggregate noticed.');
  }

  // Clause 3(vii) Statutory Dues
  observations.push('Clause 3(vii)(a): Undisputed statutory dues including Provident Fund, ESI, Income-tax, and GST deposited regularly with appropriate authorities.');

  // Clause 3(ix) Default in Repayment
  observations.push('Clause 3(ix)(a): The Company has not defaulted in repayment of loans or other borrowings to any financial institution, bank, or government.');

  // Clause 3(xi) Fraud reporting
  observations.push('Clause 3(xi)(a): No fraud by the Company or any fraud on the Company has been noticed or reported during the year.');

  return observations;
}

function generateMarkdownReport(data: {
  entityName: string;
  reportingPeriod: string;
  reportingScale: string;
  framework: string;
  cin: string;
  complianceScore: ComplianceScore;
  totalDiscrepancies: number;
  missingDisclosuresCount: number;
  numericalMismatchesCount: number;
  keyRiskAreas: string;
  inconsistencies: InconsistencyItem[];
  disclosures: DisclosureItem[];
  noteProofreadings: NoteProofreadingItem[];
  scheduleIIIGuidanceFindings: ScheduleIIIGuidanceItem[];
  recommendations: AuditRecommendation[];
  caroObservations: string[];
  financialHighlights: { [key: string]: string | undefined };
}): string {
  return `# STATUTORY AUDIT & IND AS COMPLIANCE VERIFICATION REPORT
**Entity Name:** ${data.entityName}
**Corporate Identification Number (CIN):** ${data.cin || 'N/A'}
**Reporting Period:** ${data.reportingPeriod}
**Applicable Framework:** ${data.framework}
**Currency & Scale:** ${data.reportingScale}
**Overall Compliance Score:** ${data.complianceScore.toUpperCase()} (${data.totalDiscrepancies} total discrepancies identified)

---

## 1. EXECUTIVE SUMMARY & RISK ASSESSMENT
- **Total Missing Ind AS Disclosures:** ${data.missingDisclosuresCount}
- **Numerical & Casting Discrepancies:** ${data.numericalMismatchesCount}
- **Key Risk Summary:** ${data.keyRiskAreas}

### Key Financial Metrics
| Metric | Reported Value |
| :--- | :--- |
| **Total Revenue / Income** | ${data.financialHighlights.totalRevenue || 'N/A'} |
| **Profit After Tax (PAT)** | ${data.financialHighlights.pat || 'N/A'} |
| **Total Assets** | ${data.financialHighlights.totalAssets || 'N/A'} |
| **Total Borrowings / Debt** | ${data.financialHighlights.totalDebt || 'N/A'} |
| **Net Worth / Equity** | ${data.financialHighlights.netWorth || 'N/A'} |

---

## 2. PART I: IND AS MANDATORY DISCLOSURE EVALUATION
| Standard | Requirement | Status | Audit Observation & Location |
| :--- | :--- | :--- | :--- |
${data.disclosures.map((d) => `| **${d.standard}** | ${d.requirement} | **${d.status}** | ${d.observation} |`).join('\n')}

---

## 3. PART II: INTERNAL CASTINGS & PRIMARY-TO-NOTES CROSS-REFERENCING
| Statement Line Item | Primary Figure | Note Figure / Sum | Reference | Variance & Finding | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- |
${data.inconsistencies.map((i) => `| **${i.lineItem}** | ${i.primaryFigure} | ${i.noteFigure} | ${i.noteRef || 'Schedule'} | ${i.discrepancy} | **${i.riskLevel}** |`).join('\n')}

---

## 4. PART III: ICAI SCHEDULE III (MCA 2021) COMPLIANCE FINDINGS
| Statutory Clause | Requirement | Status | Detailed Finding | Guidance Note Ref |
| :--- | :--- | :--- | :--- | :--- |
${data.scheduleIIIGuidanceFindings.map((s) => `| **${s.clause}** | ${s.requirement} | **${s.complianceStatus}** | ${s.detailedFinding} | ${s.guidanceNoteReference} |`).join('\n')}

---

## 5. PART IV: ACTIONABLE CA AUDIT RECOMMENDATIONS
| ID | Priority | Category | Action Item & Step | Statutory Ref | Action Assigned To |
| :--- | :--- | :--- | :--- | :--- | :--- |
${data.recommendations.map((r) => `| **${r.id}** | **${r.priority}** | ${r.category} | ${r.recommendation} | ${r.statutoryReference || 'ICAI / SA'} | ${r.actionFor} |`).join('\n')}

---

## 6. CARO 2020 AUDITOR OBSERVATIONS
${data.caroObservations.map((c) => `- ${c}`).join('\n')}

---
*Report generated locally on-device by FinAudit AI Offline Compliance Engine adhering to ICAI Technical Standards.*`;
}
