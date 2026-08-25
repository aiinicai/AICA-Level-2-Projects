import {
  ParsedFinancialDocument,
  ParsedLineItem,
  ParsedNote,
  ParsedNoteBreakupRow,
  ParsedRatio,
  ParsedAgeingItem,
} from './types';

// Helper to clean and parse Indian and Western formatted numbers (e.g. "1,45,200.00", "(2,400.00)", "₹ 1234.56")
export function parseNumberString(str: string | undefined | null): number | undefined {
  if (!str) return undefined;
  const trimmed = str.trim();
  if (!trimmed || trimmed === '-' || trimmed === '—' || trimmed === 'NIL' || trimmed === 'nil' || trimmed === 'NA') {
    return 0;
  }
  const isNegative = trimmed.startsWith('(') && trimmed.endsWith(')') || trimmed.startsWith('-');
  const cleaned = trimmed.replace(/[^0-9.]/g, '');
  if (!cleaned) return undefined;
  const val = parseFloat(cleaned);
  if (isNaN(val)) return undefined;
  return isNegative ? -val : val;
}

export function parseFinancialDocument(rawText: string, fileName?: string): ParsedFinancialDocument {
  const lines = rawText.split(/\r?\n/);
  
  // 1. Extract Entity Metadata
  let entityName = 'Client Financial Entity';
  let cin = '';
  let reportingPeriod = 'FY 2024-25';
  let reportingScale = '₹ in Lakhs';
  let framework = 'Ind AS (Schedule III Division II)';

  for (let i = 0; i < Math.min(lines.length, 30); i++) {
    const line = lines[i].trim();
    if (line.toUpperCase().includes('CIN:') || line.toUpperCase().includes('CORPORATE IDENTITY NUMBER')) {
      const match = line.match(/[LUlu][0-9]{5}[A-Za-z]{2}[0-9]{4}[A-Za-z]{3}[0-9]{6}/);
      if (match) cin = match[0];
    }
    if (line.toUpperCase().includes('LIMITED') || line.toUpperCase().includes('LTD.') || line.toUpperCase().includes('PVT') || line.toUpperCase().includes('CORPORATION') || line.toUpperCase().includes('INC.')) {
      if (!line.toUpperCase().includes('CIN') && !line.toUpperCase().includes('REPORT') && !line.toUpperCase().includes('AUDIT') && !line.toUpperCase().includes('STATEMENTS')) {
        entityName = line.replace(/^[=\-_*#\s]+|[=\-_*#\s]+$/g, '').trim();
      }
    }
    if (line.toLowerCase().includes('year ended') || line.toLowerCase().includes('as at')) {
      const periodMatch = line.match(/(?:ended|as at)\s+([0-9]{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+\s+[0-9]{4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2,4})/i);
      if (periodMatch) {
        reportingPeriod = periodMatch[0];
      }
    }
    if (line.toLowerCase().includes('in lakhs') || line.toLowerCase().includes('in lacs') || line.toLowerCase().includes('₹ in lakhs')) {
      reportingScale = '₹ in Lakhs';
    } else if (line.toLowerCase().includes('in crores') || line.toLowerCase().includes('₹ in crores')) {
      reportingScale = '₹ in Crores';
    } else if (line.toLowerCase().includes('in millions') || line.toLowerCase().includes('in thousands')) {
      reportingScale = line.match(/(?:in\s+[a-zA-Z]+)/i)?.[0] || '₹';
    }
  }

  // 2. Parse Line Items from Sections
  const balanceSheetItems: ParsedLineItem[] = [];
  const plItems: ParsedLineItem[] = [];
  const cashFlowItems: ParsedLineItem[] = [];
  const notesMap = new Map<string, ParsedNote>();
  const ratios: ParsedRatio[] = [];
  const tradeReceivablesAgeing: ParsedAgeingItem[] = [];
  const tradePayablesAgeing: ParsedAgeingItem[] = [];
  const cwipAgeing: ParsedAgeingItem[] = [];
  const commentarySnippets: Array<{ context: string; text: string }> = [];

  let currentSection: 'header' | 'bs' | 'pl' | 'cf' | 'socie' | 'notes' | 'ratios' | 'ageing' | 'commentary' = 'header';
  let activeNoteNumber = '';
  let activeNoteTitle = '';
  let activeNoteLines: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();
    if (!trimmed) continue;

    const upper = trimmed.toUpperCase();

    // Section detection
    if (upper.includes('BALANCE SHEET') || upper.includes('STATEMENT OF FINANCIAL POSITION')) {
      currentSection = 'bs';
      continue;
    } else if (upper.includes('STATEMENT OF PROFIT AND LOSS') || upper.includes('PROFIT & LOSS STATEMENT') || upper.includes('STATEMENT OF OPERATIONS')) {
      currentSection = 'pl';
      continue;
    } else if (upper.includes('CASH FLOW STATEMENT') || upper.includes('STATEMENT OF CASH FLOWS')) {
      currentSection = 'cf';
      continue;
    } else if (upper.includes('STATEMENT OF CHANGES IN EQUITY') || upper.includes('SOCIE')) {
      currentSection = 'socie';
      continue;
    } else if (upper.includes('STATUTORY FINANCIAL RATIOS') || upper.includes('ANALYTICAL RATIOS') || upper.includes('KEY FINANCIAL RATIOS') || upper.includes('SCHEDULE III RATIOS')) {
      currentSection = 'ratios';
      continue;
    } else if (upper.includes('DIRECTORS\' REPORT') || upper.includes('MANAGEMENT DISCUSSION') || upper.includes('MD&A') || upper.includes('AUDITORS\' REPORT') || upper.includes('CARO 2020')) {
      currentSection = 'commentary';
      commentarySnippets.push({ context: trimmed, text: '' });
      continue;
    } else if (/^(?:NOTE|NOTE NO\.?)\s*([0-9A-Za-z]+)\s*[:\-–—]?\s*(.*)/i.test(trimmed)) {
      // Finalize previous note if any
      if (activeNoteNumber && activeNoteLines.length > 0) {
        notesMap.set(activeNoteNumber, createParsedNote(activeNoteNumber, activeNoteTitle, activeNoteLines));
      }
      currentSection = 'notes';
      const match = trimmed.match(/^(?:NOTE|NOTE NO\.?)\s*([0-9A-Za-z]+)\s*[:\-–—]?\s*(.*)/i);
      if (match) {
        activeNoteNumber = match[1].trim();
        activeNoteTitle = match[2].trim() || `Note ${activeNoteNumber}`;
        activeNoteLines = [];
      }
      continue;
    }

    // Process depending on active section
    if (currentSection === 'notes') {
      activeNoteLines.push(trimmed);
    } else if (currentSection === 'bs') {
      const parsedItem = extractLineItem(trimmed, 'assets');
      if (parsedItem) balanceSheetItems.push(parsedItem);
    } else if (currentSection === 'pl') {
      const parsedItem = extractLineItem(trimmed, 'income');
      if (parsedItem) plItems.push(parsedItem);
    } else if (currentSection === 'cf') {
      const parsedItem = extractLineItem(trimmed, 'cashflow');
      if (parsedItem) cashFlowItems.push(parsedItem);
    } else if (currentSection === 'ratios') {
      const parsedRatio = extractRatioItem(trimmed);
      if (parsedRatio) ratios.push(parsedRatio);
    } else if (currentSection === 'commentary') {
      if (commentarySnippets.length > 0) {
        commentarySnippets[commentarySnippets.length - 1].text += ' ' + trimmed;
      }
    }
  }

  // Finalize last active note
  if (activeNoteNumber && activeNoteLines.length > 0) {
    notesMap.set(activeNoteNumber, createParsedNote(activeNoteNumber, activeNoteTitle, activeNoteLines));
  }

  // 3. Extract High-Level Metric Totals
  let totalAssetsCurrent: number | undefined;
  let totalAssetsPrior: number | undefined;
  let totalEquityLiabCurrent: number | undefined;
  let totalEquityLiabPrior: number | undefined;
  let totalRevenueCurrent: number | undefined;
  let patCurrent: number | undefined;
  let pbtCurrent: number | undefined;
  let netWorthCurrent: number | undefined;
  let totalDebtCurrent: number | undefined;

  for (const item of balanceSheetItems) {
    const nameLower = item.name.toLowerCase();
    if (nameLower.includes('total assets') || nameLower === 'total' && item.section === 'assets') {
      totalAssetsCurrent = item.currentAmount;
      totalAssetsPrior = item.priorAmount;
    }
    if (nameLower.includes('total equity and liabilities') || nameLower.includes('total liabilities and equity') || nameLower.includes('total equity & liabilities')) {
      totalEquityLiabCurrent = item.currentAmount;
      totalEquityLiabPrior = item.priorAmount;
    }
    if (nameLower.includes('total equity') || nameLower === 'equity' && item.currentAmount) {
      netWorthCurrent = item.currentAmount;
    }
    if ((nameLower.includes('borrowings') || nameLower.includes('total debt')) && item.currentAmount) {
      totalDebtCurrent = (totalDebtCurrent || 0) + item.currentAmount;
    }
  }

  for (const item of plItems) {
    const nameLower = item.name.toLowerCase();
    if (nameLower.includes('total income') || nameLower.includes('revenue from operations') || nameLower.includes('total revenue')) {
      if (!totalRevenueCurrent || nameLower.includes('total income')) {
        totalRevenueCurrent = item.currentAmount;
      }
    }
    if (nameLower.includes('profit for the year') || nameLower.includes('profit after tax') || nameLower.includes('pat') || nameLower.includes('net profit')) {
      patCurrent = item.currentAmount;
    }
    if (nameLower.includes('profit before tax') || nameLower.includes('pbt')) {
      pbtCurrent = item.currentAmount;
    }
  }

  // Fallback if not found in structured line items, search raw text regex
  if (totalAssetsCurrent === undefined) {
    const match = rawText.match(/TOTAL\s+ASSETS[^\d\n]*[:\-–—]?\s*₹?\s*([0-9,]+(?:\.[0-9]{2})?)/i);
    if (match) totalAssetsCurrent = parseNumberString(match[1]);
  }
  if (totalEquityLiabCurrent === undefined) {
    const match = rawText.match(/TOTAL\s+(?:EQUITY\s+AND\s+LIABILITIES|LIABILITIES)[^\d\n]*[:\-–—]?\s*₹?\s*([0-9,]+(?:\.[0-9]{2})?)/i);
    if (match) totalEquityLiabCurrent = parseNumberString(match[1]);
  }
  if (totalRevenueCurrent === undefined) {
    const match = rawText.match(/Total\s+(?:Income|Revenue)[^\d\n]*[:\-–—]?\s*₹?\s*([0-9,]+(?:\.[0-9]{2})?)/i);
    if (match) totalRevenueCurrent = parseNumberString(match[1]);
  }
  if (patCurrent === undefined) {
    const match = rawText.match(/(?:Profit\s+(?:for\s+the\s+year|after\s+tax)|PAT)[^\d\n]*[:\-–—]?\s*₹?\s*([0-9,]+(?:\.[0-9]{2})?)/i);
    if (match) patCurrent = parseNumberString(match[1]);
  }

  const rawLower = rawText.toLowerCase();

  return {
    title: fileName || entityName,
    entityName,
    cin,
    reportingPeriod,
    reportingScale,
    framework,
    rawText,
    balanceSheetItems,
    plItems,
    cashFlowItems,
    notes: notesMap,
    ratios,
    tradeReceivablesAgeing,
    tradePayablesAgeing,
    cwipAgeing,
    commentarySnippets,
    totalAssetsCurrent,
    totalAssetsPrior,
    totalEquityLiabCurrent,
    totalEquityLiabPrior,
    totalRevenueCurrent,
    patCurrent,
    pbtCurrent,
    netWorthCurrent,
    totalDebtCurrent,
    hasBenamiDisclosure: rawLower.includes('benami property') || rawLower.includes('prohibition of benami'),
    hasWilfulDefaulterDisclosure: rawLower.includes('wilful defaulter'),
    hasStruckOffDisclosure: rawLower.includes('struck off') || rawLower.includes('section 248'),
    hasCSRDisclosure: rawLower.includes('corporate social responsibility') || rawLower.includes('section 135') || rawLower.includes('csr expenditure'),
    hasCryptoDisclosure: rawLower.includes('crypto') || rawLower.includes('virtual currency'),
    hasTitleDeedsDisclosure: rawLower.includes('title deeds of immovable property') || rawLower.includes('title deeds not held'),
    hasRegisteredValuerDisclosure: rawLower.includes('registered valuer') || rawLower.includes('section 247'),
    hasBankStockReconciliation: rawLower.includes('quarterly returns') || rawLower.includes('stock statements') || rawLower.includes('statements submitted to bank'),
    hasMSMEDisclosure: rawLower.includes('msme') || rawLower.includes('micro, small and medium') || rawLower.includes('msmed act'),
  };
}

function extractLineItem(line: string, defaultSection: 'assets' | 'equity' | 'liabilities' | 'income' | 'expenses' | 'cashflow' | 'other'): ParsedLineItem | null {
  // Regex to extract: Name, optional Note No., current amount, optional prior amount
  // E.g.: "Property, Plant & Equipment              3            1,45,200.00         1,38,500.00"
  // E.g.: "(a) Inventories                             10               4,300.00            3,900.00"
  // E.g.: "TOTAL ASSETS                                                 2,10,970.00         2,02,770.00"
  
  if (line.startsWith('---') || line.startsWith('===') || line.startsWith('***') || line.startsWith('|---')) {
    return null;
  }
  
  const tokens = line.split(/\s{2,}|\t|\|/).map(t => t.trim()).filter(Boolean);
  if (tokens.length < 2) return null;

  // Check if first token is name
  const name = tokens[0].replace(/^[0-9IVX]+\.?\s*|\([a-z0-9]+\)\s*/i, '').trim();
  if (!name || name.toUpperCase() === 'PARTICULARS' || name.toUpperCase() === 'NOTE NO.' || name.toUpperCase() === 'ASSETS' || name.toUpperCase() === 'EQUITY AND LIABILITIES') {
    return null;
  }

  let noteRef: string | undefined;
  let currentRaw: string | undefined;
  let priorRaw: string | undefined;

  for (let i = 1; i < tokens.length; i++) {
    const token = tokens[i];
    // Check if token is simple note number (e.g. "3", "11", "Note 14")
    if (/^(?:Note\s*)?[0-9]{1,3}[a-z]?$/i.test(token) && !currentRaw) {
      noteRef = token.replace(/Note\s*/i, '');
      continue;
    }
    // Check if token is amount
    if (/[0-9]/.test(token) && (token.includes(',') || token.includes('.') || /^[0-9]+$/.test(token) || token.startsWith('('))) {
      if (!currentRaw) {
        currentRaw = token;
      } else if (!priorRaw) {
        priorRaw = token;
      }
    }
  }

  if (!currentRaw) return null;

  return {
    rawLine: line,
    name,
    noteRef,
    currentAmount: parseNumberString(currentRaw),
    priorAmount: parseNumberString(priorRaw),
    currentRaw,
    priorRaw,
    section: defaultSection,
  };
}

function extractRatioItem(line: string): ParsedRatio | null {
  // Regex to extract: Ratio Name | Current | Prior | Variance% | Explanation
  // E.g.: "1. Current Ratio | 1.82 | 1.35 | +34.8% | Due to prepayment of short term debt"
  const parts = line.split(/\||\t|\s{2,}/).map(p => p.trim()).filter(Boolean);
  if (parts.length < 3) return null;

  const name = parts[0].replace(/^[0-9]+\.?\s*/, '').trim();
  if (name.toUpperCase() === 'RATIO' || name.toUpperCase() === 'PARTICULARS') return null;

  const currentVal = parseNumberString(parts[1]);
  const priorVal = parseNumberString(parts[2]);
  let variancePercent: number | undefined;
  let explanationText: string | undefined;

  if (parts.length >= 4) {
    const varMatch = parts[3].match(/([+-]?[0-9]+(?:\.[0-9]+)?)\s*%/);
    if (varMatch) {
      variancePercent = parseFloat(varMatch[1]);
    } else {
      variancePercent = parseNumberString(parts[3]);
    }
  } else if (currentVal !== undefined && priorVal !== undefined && priorVal !== 0) {
    variancePercent = ((currentVal - priorVal) / priorVal) * 100;
  }

  if (parts.length >= 5) {
    explanationText = parts[4];
  }

  const explanationProvided = Boolean(explanationText && explanationText.length > 5 && !explanationText.toLowerCase().includes('nil') && !explanationText.toLowerCase().includes('na'));

  return {
    name,
    currentValue: currentVal,
    priorValue: priorVal,
    currentRaw: parts[1],
    priorRaw: parts[2],
    variancePercent,
    explanationProvided,
    explanationText,
  };
}

function createParsedNote(noteNumber: string, noteTitle: string, lines: string[]): ParsedNote {
  const breakupRows: ParsedNoteBreakupRow[] = [];
  let totalReported: number | undefined;

  for (const line of lines) {
    if (line.startsWith('---') || line.startsWith('===') || line.startsWith('***')) continue;
    const parts = line.split(/\||\t|\s{2,}/).map(p => p.trim()).filter(Boolean);
    if (parts.length >= 2) {
      const name = parts[0].replace(/^[-–—*•]\s*/, '').trim();
      const isTotal = name.toLowerCase().startsWith('total') || name.toLowerCase() === 'total';
      const amtStr = parts[1];
      const isDeduction = name.toLowerCase().includes('less:') || name.toLowerCase().includes('deductions') || name.toLowerCase().includes('allowance for') || amtStr.startsWith('(');
      const parsedAmt = parseNumberString(amtStr);

      if (isTotal) {
        totalReported = parsedAmt;
      } else if (parsedAmt !== undefined && name) {
        breakupRows.push({
          name,
          currentAmount: parsedAmt,
          currentRaw: amtStr,
          isDeduction,
        });
      }
    }
  }

  const totalComputed = breakupRows.reduce((acc, row) => {
    const val = row.currentAmount || 0;
    return row.isDeduction ? acc - val : acc + val;
  }, 0);

  let hasCastingDiscrepancy = false;
  let castingDifference = 0;

  if (totalReported !== undefined && breakupRows.length > 0) {
    castingDifference = Math.round((totalReported - totalComputed) * 100) / 100;
    if (Math.abs(castingDifference) > 0.5) {
      hasCastingDiscrepancy = true;
    }
  }

  return {
    noteNumber,
    noteTitle,
    rawText: lines.join('\n'),
    lines,
    breakupRows,
    totalReported,
    totalComputed,
    hasCastingDiscrepancy,
    castingDifference,
  };
}
