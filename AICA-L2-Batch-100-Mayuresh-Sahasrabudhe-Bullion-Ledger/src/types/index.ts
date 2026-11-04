export type MetalType = 'GOLD' | 'SILVER';

export type FormType = 'VEDHANI' | 'COIN' | 'BAR';
export type BullionForm = FormType;


export interface Purchase {
  id: string; // generated, e.g. HLD-20230510-001, editable
  purchaseDate: string; // YYYY-MM-DD
  seller: string; // Jeweller/seller
  invoiceNumber: string; // Text preserving leading zeros
  metal: MetalType;
  form: FormType;
  purity: number; // e.g. 995, 999, 916, 750
  weightGrams: number; // > 0
  purchaseRate: number; // ₹/gram > 0
  taxesPaid: number; // Rupee amount (actual invoice GST/tax)
  otherCharges: number; // default 0
  notes?: string;
  
  // Calculated stored convenience
  bullionValue: number; // weightGrams * purchaseRate
  investedAmount: number; // bullionValue + taxesPaid + otherCharges

  // Audit and lifecycle
  batchId?: string; // For undoing imports
  isDemo?: boolean; // For demo data removal
  deleted?: boolean; // For soft delete / trash
  deletedAt?: string;
  createdAt: string;
  updatedAt: string;
}

export type RateSourceType = 'NSE' | 'IBJA' | 'MANUAL' | 'API' | 'SUPPLEMENTAL';

export interface RateRecord {
  id: string; // e.g. 2026-10-30_GOLD_999
  date: string; // YYYY-MM-DD
  metal: MetalType;
  purity: number; // 995, 999
  pricePerGram: number; // Normalised ₹/gram
  source: string; // URL or provider name
  sourceType: RateSourceType;
  originalUnit: string; // '10 Grams' | '1 Kg'
  originalPrice: number; // Quotation
  session: string; // 'UNSPECIFIED' | 'AM' | 'PM'
  gstIncluded: boolean; // false / unconfirmed
  notes?: string;
  provenance: string; // 'Price History.csv' | 'Manual Correction' etc.
  importedAt?: string;
}

export interface RateCorrection {
  id: string;
  rateId: string;
  date: string;
  metal: MetalType;
  purity: number;
  originalPricePerGram: number;
  correctedPricePerGram: number;
  reason: string;
  correctedAt: string;
}

export interface AppSettings {
  goldMarkdownPct: number; // Default 3.0
  silverMarkdownPct: number; // Default 3.0
  rateProviderEnabled: boolean; // false
  rateProviderName: string; // 'Metals.Dev (Simulated)'
  confirmTaxTreatment: 'UNCONFIRMED' | 'TAX_EXCLUSIVE' | 'TAX_INCLUSIVE';
  confirmSession: 'UNSPECIFIED' | 'PM_CLOSING' | 'AM_OPENING';
  lastApiCheck?: string;
  lastSuccessfulUpdate?: string;
}

export interface HoldingValuation {
  holding: Purchase;
  selectedDate: string;
  hasRate: boolean;
  rateRecord?: RateRecord;
  actualRateDate?: string;
  ratePerGram: number;
  referenceFineness: number;
  isPurityAdjusted: boolean;
  purityAdjustmentRatio: number;
  isCarriedForward: boolean;
  rateSourceLabel: string;
  referenceMetalValue: number; // grams * applicableRatePerGram
  markdownPct: number;
  estimatedResaleValue: number; // referenceMetalValue * (1 - markdown)
  gainLossAmount: number; // resale - invested
  gainLossPct: number; // gainLoss / invested * 100
  holdingDays: number;
  annualizedXirr: number | null; // null if 0 days or failure
  xirrStatus: string;
}

export interface MetalSummary {
  metal: MetalType;
  totalGrams: number;
  investedAmount: number;
  referenceValue: number;
  resaleValue: number;
  gainLossAmount: number;
  gainLossPct: number;
  annualizedXirr: number | null;
  xirrStatus: string;
  holdingsCount: number;
  unvaluedCount: number;
}

export interface PortfolioSummary {
  selectedDate: string;
  investedAmount: number;
  referenceValue: number;
  resaleValue: number;
  gainLossAmount: number;
  gainLossPct: number;
  annualizedXirr: number | null;
  xirrStatus: string;
  totalHoldingsCount: number;
  unvaluedCount: number;
  gold: MetalSummary;
  silver: MetalSummary;
  isPartialValuation: boolean;
}

export interface ChartDataPoint {
  date: string; // YYYY-MM-DD
  investedCost: number;
  resaleValue: number;
  goldResaleValue: number;
  silverResaleValue: number;
  activeHoldings: number;
  actualRateDateGold?: string;
  actualRateDateSilver?: string;
  isSourceTransition?: boolean;
  sourceNote?: string;
}

export interface ImportBatch {
  id: string;
  timestamp: string;
  filename: string;
  recordCount: number;
  metalCounts: { gold: number; silver: number };
  undone: boolean;
}
