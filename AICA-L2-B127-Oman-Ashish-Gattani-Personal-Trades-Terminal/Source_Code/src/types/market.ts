export type MarketCapBucket = 'Large' | 'Mid' | 'Small' | 'Micro';

export interface OHLCVBar {
  date: string; // YYYY-MM-DD (NSE trading day)
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BenchmarkSeries {
  id: 'NIFTY50' | 'NIFTY500' | 'SENSEX';
  name: string;
  exchange: 'NSE' | 'BSE';
  bars: OHLCVBar[];
  latestClose: number;
  changePct: number;
}

export interface SepaFundamentals {
  qtrEpsYoY: number; // % latest quarter EPS growth YoY
  prevQtrEpsYoY: number; // % prior quarter EPS growth YoY (for acceleration)
  qtrRevYoY: number; // % latest quarter revenue growth YoY
  prevQtrRevYoY: number; // % prior quarter revenue growth YoY
  opMarginPct: number; // current operating profit margin %
  opMarginExpansionBps: number; // YoY margin expansion in bps
  earningsSurprisePct: number; // latest earnings beat/miss %
  annualEps3YCagr: number; // 3-year annual EPS growth %
  roePct: number;
  rocePct: number;
  fiiHoldingPct: number;
  fiiQoQChangePct: number; // QoQ change in FII stake
  diiHoldingPct: number;
  diiQoQChangePct: number; // QoQ change in DII/MF stake
  mfHoldingPct: number;
  promoterHoldingPct: number;
  promoterPledgePct: number;
  quarterlyHistory: {
    quarter: string;
    epsInr: number;
    epsYoY: number;
    revenueCr: number;
    revYoY: number;
    opmPct: number;
  }[];
}

export interface DividendMetrics {
  annualDpsInr: number; // Trailing 12M Dividend per Share in INR
  dividendYieldPct: number; // Current yield %
  fcfPerShareInr: number; // Trailing Free Cash Flow per share in INR
  fcf5YCagrPct: number; // 5-year FCF growth rate %
  epsInr: number; // Trailing EPS in INR
  dps5YCagrPct: number; // 5-year Dividend CAGR %
  consecutiveYearsPaid: number;
  netDebtToEbitda: number;
  historicalDps: { year: string; dps: number; fcfPerShare: number }[];
}

export interface SectorShockSensitivities {
  inflationShock: number; // % move per +20% inflation shock
  marketDrop10: number; // % move per -10% Nifty drop
  inrDepreciation10: number; // % move per -10% INR depreciation vs USD
  rbiRateHike100bps: number; // % move per +100bps RBI repo hike
  crudeSurge35: number; // % move per +35% Brent crude spike
}

export type UniverseScope = 'all' | 'nifty500' | 'fno' | 'midcap' | 'smallcap';

export interface UniverseMembership {
  nifty100: boolean;
  nifty500: boolean;
  fno: boolean;
  midcap: boolean;
  smallcap: boolean;
  microcap: boolean;
}

export interface IndianStock {
  ticker: string; // NSE symbol e.g. RELIANCE, M&M
  bseCode: string; // BSE 6-digit scrip code
  isin: string;
  name: string;
  sector: string;
  industry: string;
  capBucket: MarketCapBucket;
  marketCapCr: number; // ₹ Crore
  beta: number;
  bars: OHLCVBar[];
  latestClose: number;
  prevClose: number;
  dailyChangePct: number;
  avgDailyTurnoverCr: number;
  fundamentals: SepaFundamentals;
  dividend: DividendMetrics;
  sensitivities: SectorShockSensitivities;
  recentNews: { date: string; headline: string; source: string }[];
  universe?: UniverseMembership;
  isLiveHydrated?: boolean;
}

export interface BreakoutScanConfig {
  id?: string;
  name: string;
  lookbackMonths: number;
  recentBreakoutDays?: number; // Window of recent sessions to scan (default 5 = This Week)
  breakoutType?: 'all' | '52w_only' | 'ath_only';
  priceBasis: 'close' | 'high';
  minVolumeRatio: number;
  minPriceInr: number;
  minTurnoverCr: number;
  capBucket: 'All' | MarketCapBucket;
  sector: string;
  scheduleEnabled: boolean;
  scheduleTimeIst: string;
}

export interface BreakoutScanResult {
  stock: IndianStock;
  breakoutDate: string;
  barsAgo?: number;
  monthsSinceLast52WHigh: number;
  prior52WHigh: number;
  pctAbovePriorHigh: number;
  isAllTimeHighBreakout: boolean;
  priorAllTimeHigh: number;
  pctAbovePriorAth: number;
  athHistoryYears: number;
  volumeRatio: number;
  baseLengthWeeks: number;
  baseDepthPct: number;
  isFirstInNMonths: boolean;
}

export interface TrendTemplateThresholds {
  sma200TrendMonths: number; // default 1 (configurable 1-5)
  minAbove52WLowPct: number; // default 30
  maxBelow52WHighPct: number; // default 25
  minRsRating: number; // default 70
}

export interface TrendConditionCheck {
  id: number;
  label: string;
  detail: string;
  passed: boolean;
}

export interface VcpContraction {
  index: number;
  startDate: string;
  endDate: string;
  peakPrice: number;
  troughPrice: number;
  depthPct: number;
  durationDays: number;
}

export interface VcpAnalysis {
  detected: boolean;
  tCount: number;
  contractions: VcpContraction[];
  volumeDryUpRatio: number; // recent 5D avg vol / 50D avg vol
  isVolumeDryUp: boolean;
  pivotPrice: number;
  distanceToPivotPct: number;
  isPivotBreakout: boolean;
  breakoutVolumeRatio: number;
  baseWeeks: number;
}

export type MarketStage = 1 | 2 | 3 | 4;

export interface MinerviniAnalysis {
  stock: IndianStock;
  sma50: number;
  sma150: number;
  sma200: number;
  sma200Prev: number;
  high52W: number;
  low52W: number;
  pctAbove52WLow: number;
  pctBelow52WHigh: number;
  rsRating: number; // 1–99 IBD-style percentile vs NIFTY 500 universe
  rsRawScore: number;
  conditions: TrendConditionCheck[];
  passedCount: number;
  allPassed: boolean;
  stage: MarketStage;
  stageLabel: string;
  vcp: VcpAnalysis;
  sepaFundamentalScore: number; // 0-100
  minerviniScore: number; // 0-100 composite
  suggestedStopLossInr: number;
  suggestedStopPct: number;
}

export interface CustomIndicatorDefinition {
  id: string;
  code: string;
  name: string;
  description: string;
  formula: string;
  buyRule: string;
  sellRule: string;
  plotType: 'overlay' | 'subchart';
  color: string;
  param1Name: string;
  param1Value: number;
  param2Name: string;
  param2Value: number;
  isBuiltIn?: boolean;
}

export interface BacktestTrade {
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  shares: number;
  grossPnlInr: number;
  costsInr: number;
  netPnlInr: number;
  returnPct: number;
  holdingDays: number;
}

export interface BacktestResult {
  ticker: string;
  initialCapitalInr: number;
  finalEquityInr: number;
  totalReturnPct: number;
  benchmarkReturnPct: number;
  cagrPct: number;
  winRatePct: number;
  profitFactor: number;
  maxDrawdownPct: number;
  sharpeRatio: number;
  totalTrades: number;
  totalCostsInr: number;
  trades: BacktestTrade[];
  equityCurve: { date: string; strategyEquity: number; benchmarkEquity: number }[];
}

export interface PortfolioHolding {
  id: string;
  ticker: string;
  shares: number;
  avgCostInr: number;
  targetWeightPct: number;
  stopLossInr?: number;
}

export interface CustomWatchlist {
  id: string;
  name: string;
  slotIndex: number; // 1..5
  notes: string;
  tickers: string[];
}

export interface IndianTransactionCost {
  brokerage: number;
  stt: number;
  exchangeCharges: number;
  sebiFees: number;
  stampDuty: number;
  gst: number;
  dpCharges: number;
  totalCost: number;
  costBps: number;
}

export interface RebalanceOrder {
  ticker: string;
  name: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  currentShares: number;
  targetShares: number;
  deltaShares: number;
  priceInr: number;
  tradeValueInr: number;
  currentWeightPct: number;
  targetWeightPct: number;
  driftPct: number;
  costs: IndianTransactionCost;
}

export type AlertCategory =
  | 'breakout_52w'
  | 'trend_template'
  | 'vcp_pivot'
  | 'custom_indicator'
  | 'price'
  | 'news';

export interface AlertItem {
  id: string;
  ticker: string;
  category: AlertCategory;
  title: string;
  message: string;
  read: boolean;
  createdAtIso: string;
}

export interface ConnectorState {
  nseConnectorEnabled: boolean;
  bseConnectorEnabled: boolean;
  brokerConnectorName: 'Zerodha Kite' | 'Dhan HQ' | 'Upstox Pro' | 'Disconnected';
}

export interface TradeJournalEntry {
  id: string;
  ticker: string;
  setup: string;
  entryDate: string;
  entryPrice: number;
  stopLoss: number;
  shares: number;
  status: 'OPEN' | 'CLOSED';
  exitDate?: string;
  exitPrice?: number;
  notes?: string;
}

export type ActiveWorkspace =
  | 'overview'
  | 'sectors'
  | 'radar'
  | 'donchian'
  | 'hv_scanner'
  | 'breakout'
  | 'minervini'
  | 'portfolio'
  | 'fundamental'
  | 'closingbell'
  | 'connectors';
