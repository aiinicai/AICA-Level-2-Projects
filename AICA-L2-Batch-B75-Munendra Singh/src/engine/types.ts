import {
  ComplianceScore,
  RiskLevel,
  DisclosureStatus,
  DisclosureItem,
  InconsistencyItem,
  NoteProofreadingItem,
  ScheduleIIIGuidanceItem,
  AuditRecommendation,
  ExecutiveSummary,
  AuditReportData
} from '../types';

export interface ParsedLineItem {
  rawLine: string;
  name: string;
  noteRef?: string;
  currentAmount?: number;
  priorAmount?: number;
  currentRaw?: string;
  priorRaw?: string;
  section: 'assets' | 'equity' | 'liabilities' | 'income' | 'expenses' | 'cashflow' | 'other';
  subsection?: string;
}

export interface ParsedNoteBreakupRow {
  name: string;
  currentAmount?: number;
  priorAmount?: number;
  currentRaw?: string;
  priorRaw?: string;
  isDeduction?: boolean;
}

export interface ParsedNote {
  noteNumber: string;
  noteTitle: string;
  rawText: string;
  lines: string[];
  breakupRows: ParsedNoteBreakupRow[];
  totalReported?: number;
  totalComputed?: number;
  hasCastingDiscrepancy?: boolean;
  castingDifference?: number;
}

export interface ParsedRatio {
  name: string;
  currentValue?: number;
  priorValue?: number;
  currentRaw?: string;
  priorRaw?: string;
  variancePercent?: number;
  explanationProvided?: boolean;
  explanationText?: string;
}

export interface ParsedAgeingItem {
  category: string; // e.g. "Trade Receivables - Undisputed (Considered Good)"
  lessThan6m?: number;
  months6to1yr?: number;
  years1to2?: number;
  years2to3?: number;
  moreThan3yrs?: number;
  unbilledDues?: number;
  total?: number;
}

export interface ParsedFinancialDocument {
  title: string;
  entityName: string;
  cin?: string;
  reportingPeriod: string;
  reportingScale: string; // e.g., "₹ in Lakhs", "₹ in Crores"
  framework: string;
  rawText: string;
  balanceSheetItems: ParsedLineItem[];
  plItems: ParsedLineItem[];
  cashFlowItems: ParsedLineItem[];
  notes: Map<string, ParsedNote>;
  ratios: ParsedRatio[];
  tradeReceivablesAgeing: ParsedAgeingItem[];
  tradePayablesAgeing: ParsedAgeingItem[];
  cwipAgeing: ParsedAgeingItem[];
  commentarySnippets: Array<{ context: string; text: string }>;
  
  // High-level totals
  totalAssetsCurrent?: number;
  totalAssetsPrior?: number;
  totalEquityLiabCurrent?: number;
  totalEquityLiabPrior?: number;
  totalRevenueCurrent?: number;
  patCurrent?: number;
  pbtCurrent?: number;
  netWorthCurrent?: number;
  totalDebtCurrent?: number;
  
  // Specific detected clauses
  hasBenamiDisclosure: boolean;
  hasWilfulDefaulterDisclosure: boolean;
  hasStruckOffDisclosure: boolean;
  hasCSRDisclosure: boolean;
  hasCryptoDisclosure: boolean;
  hasTitleDeedsDisclosure: boolean;
  hasRegisteredValuerDisclosure: boolean;
  hasBankStockReconciliation: boolean;
  hasMSMEDisclosure: boolean;
}

export interface AuditOptions {
  strictTolerance?: boolean;
  checkCARO?: boolean;
  standardsFocus?: string[];
  framework?: string;
}
