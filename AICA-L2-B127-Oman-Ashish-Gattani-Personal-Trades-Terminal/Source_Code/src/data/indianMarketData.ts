import {
  BenchmarkSeries,
  IndianStock,
  MarketCapBucket,
  OHLCVBar,
  SectorShockSensitivities,
  UniverseMembership,
  UniverseScope,
} from '../types/market';
import { NSE_HOLIDAYS_2026 } from '../utils/formatters';
import { EXPANDED_NSE_SPECS } from './expandedNseSpecs';
import {
  NSE_1100_CATALOG,
  NSE_FLAG_FNO,
  NSE_FLAG_MICROCAP,
  NSE_FLAG_MIDCAP,
  NSE_FLAG_NIFTY100,
  NSE_FLAG_NIFTY500,
  NSE_FLAG_SMALLCAP,
  NseCatalogTuple,
} from './nse1050Catalog';

// Deterministic Mulberry32 PRNG so every run has crisp, consistent OHLCV histories
function createRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Generate 780 NSE trading dates ending on 2026-11-20 (skipping weekends & holidays)
function generateNseTradingDates(count = 780): string[] {
  const holidaySet = new Set(NSE_HOLIDAYS_2026.map((h) => h.date));
  const dates: string[] = [];
  const d = new Date('2026-11-20T00:00:00Z');

  while (dates.length < count) {
    const day = d.getUTCDay();
    const iso = d.toISOString().slice(0, 10);
    if (day !== 0 && day !== 6 && !holidaySet.has(iso)) {
      dates.push(iso);
    }
    d.setUTCDate(d.getUTCDate() - 1);
  }
  return dates.reverse();
}

export const NSE_TRADING_DATES = generateNseTradingDates(780);

export type PatternArchetype =
  | 'vcp_breakout' // Stage 2 textbook VCP with pivot breakout + first 52W high in N months
  | 'vcp_tight_pivot' // Stage 2 tight VCP right near pivot, volume dry-up
  | 'fresh_breakout_long' // Multi-month base (12-24m) breaking out to 52W high on heavy vol
  | 'fresh_breakout_mid' // 4-10 month base breaking out to 52W high on volume
  | 'stage2_leader' // Strong Stage 2 uptrend, already extended slightly above pivot
  | 'stage1_base' // Flat Stage 1 accumulation base
  | 'stage3_top' // Choppy Stage 3 topping distribution
  | 'stage4_decline'; // Stage 4 downtrend below declining 200 SMA

export interface StockSeedSpec {
  ticker: string;
  bseCode: string;
  isin: string;
  name: string;
  sector: string;
  industry: string;
  capBucket: MarketCapBucket;
  marketCapCr: number;
  targetPrice: number;
  avgTurnoverCr: number;
  beta: number;
  archetype: PatternArchetype;
  baseMonths?: number; // months since prior 52W high for breakout archetypes
  breakoutVolMult?: number;
  qtrEpsYoY: number;
  prevQtrEpsYoY: number;
  qtrRevYoY: number;
  prevQtrRevYoY: number;
  opMarginPct: number;
  opMarginExpansionBps: number;
  earningsSurprisePct: number;
  annualEps3YCagr: number;
  roePct: number;
  rocePct: number;
  fiiHoldingPct: number;
  fiiQoQChangePct: number;
  diiHoldingPct: number;
  diiQoQChangePct: number;
  mfHoldingPct: number;
  promoterHoldingPct: number;
  promoterPledgePct: number;
  annualDpsInr: number;
  fcfPerShareInr: number;
  fcf5YCagrPct: number;
  epsInr: number;
  dps5YCagrPct: number;
  consecutiveYearsPaid: number;
  netDebtToEbitda: number;
  headline: string;
}

const SECTOR_SENSITIVITIES: Record<string, SectorShockSensitivities> = {
  'Information Technology': {
    inflationShock: -4.5,
    marketDrop10: -9.2,
    inrDepreciation10: +7.8,
    rbiRateHike100bps: -2.2,
    crudeSurge35: -1.8,
  },
  'Banking & Financial Services': {
    inflationShock: -8.8,
    marketDrop10: -11.8,
    inrDepreciation10: -3.5,
    rbiRateHike100bps: -6.4,
    crudeSurge35: -4.2,
  },
  'Capital Goods & Defence': {
    inflationShock: -5.2,
    marketDrop10: -11.5,
    inrDepreciation10: -1.2,
    rbiRateHike100bps: -4.8,
    crudeSurge35: -3.4,
  },
  'Energy & Power': {
    inflationShock: +3.2,
    marketDrop10: -8.6,
    inrDepreciation10: -2.6,
    rbiRateHike100bps: -3.5,
    crudeSurge35: +4.5,
  },
  'Pharma & Healthcare': {
    inflationShock: -2.1,
    marketDrop10: -6.8,
    inrDepreciation10: +6.4,
    rbiRateHike100bps: -1.4,
    crudeSurge35: -1.1,
  },
  'Automobiles & EV': {
    inflationShock: -7.6,
    marketDrop10: -11.2,
    inrDepreciation10: -2.9,
    rbiRateHike100bps: -7.1,
    crudeSurge35: -6.8,
  },
  'Consumer & Retail': {
    inflationShock: -6.4,
    marketDrop10: -8.4,
    inrDepreciation10: -1.8,
    rbiRateHike100bps: -3.2,
    crudeSurge35: -3.9,
  },
  'FMCG': {
    inflationShock: -4.1,
    marketDrop10: -5.8,
    inrDepreciation10: -0.9,
    rbiRateHike100bps: -1.8,
    crudeSurge35: -2.8,
  },
  'Capital Markets': {
    inflationShock: -6.8,
    marketDrop10: -14.2,
    inrDepreciation10: -2.4,
    rbiRateHike100bps: -5.9,
    crudeSurge35: -3.1,
  },
  'Telecom & Digital': {
    inflationShock: -3.4,
    marketDrop10: -9.5,
    inrDepreciation10: -2.1,
    rbiRateHike100bps: -4.4,
    crudeSurge35: -2.2,
  },
  'Chemicals & Materials': {
    inflationShock: -5.8,
    marketDrop10: -10.4,
    inrDepreciation10: +2.6,
    rbiRateHike100bps: -3.8,
    crudeSurge35: -6.2,
  },
  'Metals & Mining': {
    inflationShock: +4.6,
    marketDrop10: -12.4,
    inrDepreciation10: +3.8,
    rbiRateHike100bps: -4.6,
    crudeSurge35: +2.4,
  },
  'Real Estate & Infra': {
    inflationShock: -7.4,
    marketDrop10: -12.8,
    inrDepreciation10: -2.2,
    rbiRateHike100bps: -8.6,
    crudeSurge35: -3.8,
  },
  'Cement & Building Materials': {
    inflationShock: -6.2,
    marketDrop10: -9.8,
    inrDepreciation10: -1.6,
    rbiRateHike100bps: -5.4,
    crudeSurge35: -5.9,
  },
};

const STOCK_SPECS: StockSeedSpec[] = [
  {
    ticker: 'TRENT',
    bseCode: '500251',
    isin: 'INE849A01020',
    name: 'Trent Ltd',
    sector: 'Consumer & Retail',
    industry: 'Apparel & Specialty Retail',
    capBucket: 'Large',
    marketCapCr: 268400,
    targetPrice: 7540,
    avgTurnoverCr: 920,
    beta: 1.18,
    archetype: 'vcp_breakout',
    baseMonths: 7,
    breakoutVolMult: 2.35,
    qtrEpsYoY: 46.2,
    prevQtrEpsYoY: 38.4,
    qtrRevYoY: 39.8,
    prevQtrRevYoY: 34.1,
    opMarginPct: 16.4,
    opMarginExpansionBps: 185,
    earningsSurprisePct: 8.4,
    annualEps3YCagr: 64.5,
    roePct: 31.8,
    rocePct: 34.2,
    fiiHoldingPct: 27.6,
    fiiQoQChangePct: 1.4,
    diiHoldingPct: 15.8,
    diiQoQChangePct: 0.9,
    mfHoldingPct: 11.4,
    promoterHoldingPct: 37.0,
    promoterPledgePct: 0,
    annualDpsInr: 4.5,
    fcfPerShareInr: 36.2,
    fcf5YCagrPct: 31.4,
    epsInr: 48.6,
    dps5YCagrPct: 24.0,
    consecutiveYearsPaid: 18,
    netDebtToEbitda: 0.28,
    headline: 'Zudio store network crosses 680 outlets across Tier-2/3 cities; Q2 EBITDA margin expands 185 bps',
  },
  {
    ticker: 'HAL',
    bseCode: '541154',
    isin: 'INE066F01020',
    name: 'Hindustan Aeronautics Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Aerospace & Defence',
    capBucket: 'Large',
    marketCapCr: 326500,
    targetPrice: 4885,
    avgTurnoverCr: 1380,
    beta: 1.24,
    archetype: 'vcp_breakout',
    baseMonths: 11,
    breakoutVolMult: 2.65,
    qtrEpsYoY: 34.5,
    prevQtrEpsYoY: 26.8,
    qtrRevYoY: 24.6,
    prevQtrRevYoY: 18.2,
    opMarginPct: 28.4,
    opMarginExpansionBps: 210,
    earningsSurprisePct: 6.9,
    annualEps3YCagr: 31.2,
    roePct: 27.4,
    rocePct: 35.8,
    fiiHoldingPct: 12.9,
    fiiQoQChangePct: 0.85,
    diiHoldingPct: 8.9,
    diiQoQChangePct: 0.62,
    mfHoldingPct: 6.2,
    promoterHoldingPct: 71.6,
    promoterPledgePct: 0,
    annualDpsInr: 42.0,
    fcfPerShareInr: 138.4,
    fcf5YCagrPct: 22.8,
    epsInr: 124.2,
    dps5YCagrPct: 19.5,
    consecutiveYearsPaid: 10,
    netDebtToEbitda: -2.1,
    headline: 'HAL secures ₹26,000 Cr aero-engine contract; order book exceeds ₹1.24 lakh Cr',
  },
  {
    ticker: 'DIXON',
    bseCode: '540699',
    isin: 'INE935N01020',
    name: 'Dixon Technologies (India) Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Electronics Manufacturing (EMS)',
    capBucket: 'Mid',
    marketCapCr: 98400,
    targetPrice: 16420,
    avgTurnoverCr: 640,
    beta: 1.32,
    archetype: 'vcp_tight_pivot',
    baseMonths: 5,
    breakoutVolMult: 1.15,
    qtrEpsYoY: 68.4,
    prevQtrEpsYoY: 54.2,
    qtrRevYoY: 74.1,
    prevQtrRevYoY: 62.5,
    opMarginPct: 4.3,
    opMarginExpansionBps: 42,
    earningsSurprisePct: 11.2,
    annualEps3YCagr: 48.6,
    roePct: 28.9,
    rocePct: 33.4,
    fiiHoldingPct: 22.8,
    fiiQoQChangePct: 1.65,
    diiHoldingPct: 24.1,
    diiQoQChangePct: 1.1,
    mfHoldingPct: 19.5,
    promoterHoldingPct: 32.9,
    promoterPledgePct: 0,
    annualDpsInr: 8.0,
    fcfPerShareInr: 96.5,
    fcf5YCagrPct: 34.2,
    epsInr: 128.4,
    dps5YCagrPct: 21.0,
    consecutiveYearsPaid: 8,
    netDebtToEbitda: 0.14,
    headline: 'Mobile & IT hardware PLI ramp-up drives 74% YoY revenue surge; display module JV signed',
  },
  {
    ticker: 'PERSISTENT',
    bseCode: '533179',
    isin: 'INE262H01021',
    name: 'Persistent Systems Ltd',
    sector: 'Information Technology',
    industry: 'Digital Engineering & IT Services',
    capBucket: 'Mid',
    marketCapCr: 94200,
    targetPrice: 6120,
    avgTurnoverCr: 485,
    beta: 1.09,
    archetype: 'vcp_breakout',
    baseMonths: 14,
    breakoutVolMult: 2.18,
    qtrEpsYoY: 28.6,
    prevQtrEpsYoY: 22.1,
    qtrRevYoY: 21.4,
    prevQtrRevYoY: 17.8,
    opMarginPct: 17.6,
    opMarginExpansionBps: 95,
    earningsSurprisePct: 5.4,
    annualEps3YCagr: 29.4,
    roePct: 25.6,
    rocePct: 31.2,
    fiiHoldingPct: 24.2,
    fiiQoQChangePct: 1.12,
    diiHoldingPct: 28.4,
    diiQoQChangePct: 0.78,
    mfHoldingPct: 23.6,
    promoterHoldingPct: 30.8,
    promoterPledgePct: 0,
    annualDpsInr: 34.0,
    fcfPerShareInr: 94.8,
    fcf5YCagrPct: 24.5,
    epsInr: 91.2,
    dps5YCagrPct: 22.8,
    consecutiveYearsPaid: 15,
    netDebtToEbitda: -0.72,
    headline: '18th consecutive quarter of sequential revenue growth; TCV bookings touch $560M in Q2',
  },
  {
    ticker: 'BEL',
    bseCode: '500049',
    isin: 'INE263A01024',
    name: 'Bharat Electronics Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Defence Electronics',
    capBucket: 'Large',
    marketCapCr: 248600,
    targetPrice: 340,
    avgTurnoverCr: 1120,
    beta: 1.16,
    archetype: 'fresh_breakout_mid',
    baseMonths: 8,
    breakoutVolMult: 2.42,
    qtrEpsYoY: 31.4,
    prevQtrEpsYoY: 24.0,
    qtrRevYoY: 19.6,
    prevQtrRevYoY: 15.1,
    opMarginPct: 26.8,
    opMarginExpansionBps: 165,
    earningsSurprisePct: 7.2,
    annualEps3YCagr: 24.8,
    roePct: 26.4,
    rocePct: 34.6,
    fiiHoldingPct: 17.8,
    fiiQoQChangePct: 0.72,
    diiHoldingPct: 21.4,
    diiQoQChangePct: 0.54,
    mfHoldingPct: 16.8,
    promoterHoldingPct: 51.1,
    promoterPledgePct: 0,
    annualDpsInr: 2.6,
    fcfPerShareInr: 7.2,
    fcf5YCagrPct: 19.8,
    epsInr: 6.4,
    dps5YCagrPct: 16.4,
    consecutiveYearsPaid: 22,
    netDebtToEbitda: -1.85,
    headline: 'QRSAM radar subsystems order pushes backlog above ₹78,000 Cr; gross margins improve',
  },
  {
    ticker: 'CDSL',
    bseCode: '540000',
    isin: 'INE736A01011',
    name: 'Central Depository Services (India) Ltd',
    sector: 'Capital Markets',
    industry: 'Market Infrastructure',
    capBucket: 'Mid',
    marketCapCr: 37400,
    targetPrice: 1790,
    avgTurnoverCr: 520,
    beta: 1.38,
    archetype: 'vcp_tight_pivot',
    baseMonths: 6,
    breakoutVolMult: 1.05,
    qtrEpsYoY: 42.5,
    prevQtrEpsYoY: 36.1,
    qtrRevYoY: 44.8,
    prevQtrRevYoY: 38.2,
    opMarginPct: 61.4,
    opMarginExpansionBps: 240,
    earningsSurprisePct: 9.1,
    annualEps3YCagr: 34.2,
    roePct: 33.6,
    rocePct: 43.2,
    fiiHoldingPct: 16.4,
    fiiQoQChangePct: 1.85,
    diiHoldingPct: 14.2,
    diiQoQChangePct: 1.24,
    mfHoldingPct: 11.2,
    promoterHoldingPct: 15.0,
    promoterPledgePct: 0,
    annualDpsInr: 14.0,
    fcfPerShareInr: 29.8,
    fcf5YCagrPct: 28.4,
    epsInr: 28.6,
    dps5YCagrPct: 26.2,
    consecutiveYearsPaid: 9,
    netDebtToEbitda: -1.9,
    headline: 'Active demat accounts cross 15.2 Cr milestone; issuer and transaction revenue hit all-time high',
  },
  {
    ticker: 'BSE',
    bseCode: '540001',
    isin: 'INE118H01025',
    name: 'BSE Ltd',
    sector: 'Capital Markets',
    industry: 'Stock Exchange',
    capBucket: 'Mid',
    marketCapCr: 74200,
    targetPrice: 5480,
    avgTurnoverCr: 840,
    beta: 1.45,
    archetype: 'vcp_breakout',
    baseMonths: 9,
    breakoutVolMult: 2.85,
    qtrEpsYoY: 112.4,
    prevQtrEpsYoY: 88.2,
    qtrRevYoY: 86.5,
    prevQtrRevYoY: 71.4,
    opMarginPct: 54.2,
    opMarginExpansionBps: 620,
    earningsSurprisePct: 14.8,
    annualEps3YCagr: 58.4,
    roePct: 32.4,
    rocePct: 41.0,
    fiiHoldingPct: 15.6,
    fiiQoQChangePct: 2.2,
    diiHoldingPct: 13.8,
    diiQoQChangePct: 1.5,
    mfHoldingPct: 10.4,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 22.0,
    fcfPerShareInr: 72.5,
    fcf5YCagrPct: 42.0,
    epsInr: 68.4,
    dps5YCagrPct: 24.5,
    consecutiveYearsPaid: 10,
    netDebtToEbitda: -2.4,
    headline: 'Sensex & Bankex index options market share rises to 26.4%; StAR MF platform processes record SIPs',
  },
  {
    ticker: 'CGPOWER',
    bseCode: '500093',
    isin: 'INE067A01029',
    name: 'CG Power & Industrial Solutions Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Electrical Equipment & OSAT',
    capBucket: 'Large',
    marketCapCr: 122800,
    targetPrice: 804,
    avgTurnoverCr: 390,
    beta: 1.22,
    archetype: 'fresh_breakout_long',
    baseMonths: 16,
    breakoutVolMult: 2.08,
    qtrEpsYoY: 26.4,
    prevQtrEpsYoY: 19.5,
    qtrRevYoY: 23.8,
    prevQtrRevYoY: 18.4,
    opMarginPct: 15.2,
    opMarginExpansionBps: 110,
    earningsSurprisePct: 4.8,
    annualEps3YCagr: 36.2,
    roePct: 31.4,
    rocePct: 40.8,
    fiiHoldingPct: 15.4,
    fiiQoQChangePct: 0.64,
    diiHoldingPct: 12.1,
    diiQoQChangePct: 0.82,
    mfHoldingPct: 9.8,
    promoterHoldingPct: 58.1,
    promoterPledgePct: 0,
    annualDpsInr: 2.2,
    fcfPerShareInr: 8.6,
    fcf5YCagrPct: 29.0,
    epsInr: 7.4,
    dps5YCagrPct: 18.0,
    consecutiveYearsPaid: 5,
    netDebtToEbitda: -0.65,
    headline: 'Power systems transformer capacity expansion commissioned; Sanand OSAT plant ahead of schedule',
  },
  {
    ticker: 'CUMMINSIND',
    bseCode: '500480',
    isin: 'INE298A01020',
    name: 'Cummins India Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Power Generation & Engines',
    capBucket: 'Large',
    marketCapCr: 109400,
    targetPrice: 3945,
    avgTurnoverCr: 340,
    beta: 1.06,
    archetype: 'fresh_breakout_long',
    baseMonths: 19,
    breakoutVolMult: 1.94,
    qtrEpsYoY: 29.8,
    prevQtrEpsYoY: 24.2,
    qtrRevYoY: 22.1,
    prevQtrRevYoY: 17.6,
    opMarginPct: 20.6,
    opMarginExpansionBps: 145,
    earningsSurprisePct: 6.2,
    annualEps3YCagr: 28.4,
    roePct: 29.2,
    rocePct: 37.8,
    fiiHoldingPct: 18.2,
    fiiQoQChangePct: 0.9,
    diiHoldingPct: 20.4,
    diiQoQChangePct: 0.45,
    mfHoldingPct: 14.8,
    promoterHoldingPct: 51.0,
    promoterPledgePct: 0,
    annualDpsInr: 44.0,
    fcfPerShareInr: 78.4,
    fcf5YCagrPct: 21.4,
    epsInr: 68.5,
    dps5YCagrPct: 18.6,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: -1.35,
    headline: 'Data center backup genset orders surge 48% YoY; CPCB IV+ portfolio drives margin expansion',
  },
  {
    ticker: 'SOLARINDS',
    bseCode: '532725',
    isin: 'INE343H01029',
    name: 'Solar Industries India Ltd',
    sector: 'Chemicals & Materials',
    industry: 'Industrial Explosives & Defence',
    capBucket: 'Large',
    marketCapCr: 108200,
    targetPrice: 11960,
    avgTurnoverCr: 265,
    beta: 1.08,
    archetype: 'stage2_leader',
    baseMonths: 4,
    breakoutVolMult: 1.68,
    qtrEpsYoY: 38.2,
    prevQtrEpsYoY: 31.4,
    qtrRevYoY: 26.8,
    prevQtrRevYoY: 20.5,
    opMarginPct: 25.8,
    opMarginExpansionBps: 230,
    earningsSurprisePct: 7.8,
    annualEps3YCagr: 34.5,
    roePct: 30.8,
    rocePct: 35.4,
    fiiHoldingPct: 7.2,
    fiiQoQChangePct: 0.52,
    diiHoldingPct: 14.8,
    diiQoQChangePct: 0.48,
    mfHoldingPct: 13.6,
    promoterHoldingPct: 73.1,
    promoterPledgePct: 0,
    annualDpsInr: 12.0,
    fcfPerShareInr: 142.0,
    fcf5YCagrPct: 26.4,
    epsInr: 132.4,
    dps5YCagrPct: 14.2,
    consecutiveYearsPaid: 16,
    netDebtToEbitda: 0.42,
    headline: 'Pinaka rocket export contracts lift defence revenue share to 22% of consolidated sales',
  },
  {
    ticker: 'RELIANCE',
    bseCode: '500325',
    isin: 'INE002A01018',
    name: 'Reliance Industries Ltd',
    sector: 'Energy & Power',
    industry: 'Conglomerate / O2C / Jio / Retail',
    capBucket: 'Large',
    marketCapCr: 1984000,
    targetPrice: 1468,
    avgTurnoverCr: 2840,
    beta: 1.04,
    archetype: 'fresh_breakout_long',
    baseMonths: 15,
    breakoutVolMult: 1.88,
    qtrEpsYoY: 16.4,
    prevQtrEpsYoY: 11.2,
    qtrRevYoY: 13.8,
    prevQtrRevYoY: 10.4,
    opMarginPct: 18.2,
    opMarginExpansionBps: 75,
    earningsSurprisePct: 3.6,
    annualEps3YCagr: 14.2,
    roePct: 9.8,
    rocePct: 10.6,
    fiiHoldingPct: 21.8,
    fiiQoQChangePct: 0.45,
    diiHoldingPct: 17.6,
    diiQoQChangePct: 0.62,
    mfHoldingPct: 8.9,
    promoterHoldingPct: 50.3,
    promoterPledgePct: 0,
    annualDpsInr: 5.5,
    fcfPerShareInr: 42.8,
    fcf5YCagrPct: 16.2,
    epsInr: 56.4,
    dps5YCagrPct: 9.2,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: 0.78,
    headline: 'Jio ARPU rises to ₹212 following tariff revision; New Energy gigafactory commences module output',
  },
  {
    ticker: 'TCS',
    bseCode: '532540',
    isin: 'INE467B01029',
    name: 'Tata Consultancy Services Ltd',
    sector: 'Information Technology',
    industry: 'IT Consulting & Outsourcing',
    capBucket: 'Large',
    marketCapCr: 1568000,
    targetPrice: 4335,
    avgTurnoverCr: 1490,
    beta: 0.78,
    archetype: 'stage1_base',
    qtrEpsYoY: 10.4,
    prevQtrEpsYoY: 8.8,
    qtrRevYoY: 8.2,
    prevQtrRevYoY: 6.9,
    opMarginPct: 24.8,
    opMarginExpansionBps: 40,
    earningsSurprisePct: 1.8,
    annualEps3YCagr: 11.6,
    roePct: 51.4,
    rocePct: 64.2,
    fiiHoldingPct: 12.6,
    fiiQoQChangePct: 0.22,
    diiHoldingPct: 11.4,
    diiQoQChangePct: 0.35,
    mfHoldingPct: 4.8,
    promoterHoldingPct: 71.8,
    promoterPledgePct: 0,
    annualDpsInr: 126.0,
    fcfPerShareInr: 148.6,
    fcf5YCagrPct: 10.8,
    epsInr: 138.4,
    dps5YCagrPct: 13.4,
    consecutiveYearsPaid: 22,
    netDebtToEbitda: -0.92,
    headline: 'BFSI vertical returns to positive sequential growth in North America; ₹126/sh total FY payout',
  },
  {
    ticker: 'HDFCBANK',
    bseCode: '500180',
    isin: 'INE040A01034',
    name: 'HDFC Bank Ltd',
    sector: 'Banking & Financial Services',
    industry: 'Private Sector Bank',
    capBucket: 'Large',
    marketCapCr: 1412000,
    targetPrice: 1854,
    avgTurnoverCr: 2420,
    beta: 1.02,
    archetype: 'fresh_breakout_long',
    baseMonths: 22,
    breakoutVolMult: 2.04,
    qtrEpsYoY: 14.8,
    prevQtrEpsYoY: 11.4,
    qtrRevYoY: 15.2,
    prevQtrRevYoY: 12.8,
    opMarginPct: 35.6,
    opMarginExpansionBps: 55,
    earningsSurprisePct: 3.1,
    annualEps3YCagr: 16.4,
    roePct: 16.8,
    rocePct: 7.9,
    fiiHoldingPct: 48.2,
    fiiQoQChangePct: 0.94,
    diiHoldingPct: 35.4,
    diiQoQChangePct: 0.56,
    mfHoldingPct: 24.2,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 22.0,
    fcfPerShareInr: 86.4,
    fcf5YCagrPct: 14.6,
    epsInr: 91.2,
    dps5YCagrPct: 15.8,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: 1.4,
    headline: 'CD ratio normalizes below 96%; net interest margin stabilizes at 3.52% with benign credit costs',
  },
  {
    ticker: 'ICICIBANK',
    bseCode: '532174',
    isin: 'INE090A01021',
    name: 'ICICI Bank Ltd',
    sector: 'Banking & Financial Services',
    industry: 'Private Sector Bank',
    capBucket: 'Large',
    marketCapCr: 984000,
    targetPrice: 1396,
    avgTurnoverCr: 1850,
    beta: 1.05,
    archetype: 'stage2_leader',
    baseMonths: 5,
    breakoutVolMult: 1.62,
    qtrEpsYoY: 18.6,
    prevQtrEpsYoY: 16.2,
    qtrRevYoY: 17.4,
    prevQtrRevYoY: 15.9,
    opMarginPct: 38.2,
    opMarginExpansionBps: 80,
    earningsSurprisePct: 4.5,
    annualEps3YCagr: 23.4,
    roePct: 18.6,
    rocePct: 8.4,
    fiiHoldingPct: 45.8,
    fiiQoQChangePct: 0.68,
    diiHoldingPct: 44.2,
    diiQoQChangePct: 0.42,
    mfHoldingPct: 30.8,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 11.5,
    fcfPerShareInr: 62.4,
    fcf5YCagrPct: 21.8,
    epsInr: 64.2,
    dps5YCagrPct: 22.4,
    consecutiveYearsPaid: 24,
    netDebtToEbitda: 1.15,
    headline: 'Core RoA holds at 2.38%; retail & SME loan book grows 18% YoY with Gross NPA at 1.97%',
  },
  {
    ticker: 'INFY',
    bseCode: '500209',
    isin: 'INE009A01021',
    name: 'Infosys Ltd',
    sector: 'Information Technology',
    industry: 'IT Consulting & Digital',
    capBucket: 'Large',
    marketCapCr: 814000,
    targetPrice: 1962,
    avgTurnoverCr: 1320,
    beta: 0.86,
    archetype: 'fresh_breakout_mid',
    baseMonths: 10,
    breakoutVolMult: 1.78,
    qtrEpsYoY: 12.4,
    prevQtrEpsYoY: 9.2,
    qtrRevYoY: 9.6,
    prevQtrRevYoY: 7.4,
    opMarginPct: 21.4,
    opMarginExpansionBps: 60,
    earningsSurprisePct: 2.9,
    annualEps3YCagr: 11.2,
    roePct: 32.4,
    rocePct: 40.6,
    fiiHoldingPct: 33.8,
    fiiQoQChangePct: 0.54,
    diiHoldingPct: 37.6,
    diiQoQChangePct: 0.31,
    mfHoldingPct: 21.2,
    promoterHoldingPct: 14.6,
    promoterPledgePct: 0,
    annualDpsInr: 48.0,
    fcfPerShareInr: 68.2,
    fcf5YCagrPct: 11.6,
    epsInr: 65.8,
    dps5YCagrPct: 12.2,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: -0.84,
    headline: 'FY27 constant-currency revenue guidance raised by 100 bps; 85% FCF capital return policy reaffirmed',
  },
  {
    ticker: 'BHARTIARTL',
    bseCode: '532454',
    isin: 'INE397D01024',
    name: 'Bharti Airtel Ltd',
    sector: 'Telecom & Digital',
    industry: 'Telecom Services',
    capBucket: 'Large',
    marketCapCr: 1024000,
    targetPrice: 1798,
    avgTurnoverCr: 1180,
    beta: 0.88,
    archetype: 'stage2_leader',
    baseMonths: 4,
    breakoutVolMult: 1.54,
    qtrEpsYoY: 54.2,
    prevQtrEpsYoY: 42.6,
    qtrRevYoY: 18.4,
    prevQtrRevYoY: 14.8,
    opMarginPct: 53.6,
    opMarginExpansionBps: 190,
    earningsSurprisePct: 6.4,
    annualEps3YCagr: 38.4,
    roePct: 21.6,
    rocePct: 15.8,
    fiiHoldingPct: 25.4,
    fiiQoQChangePct: 0.76,
    diiHoldingPct: 18.8,
    diiQoQChangePct: 0.44,
    mfHoldingPct: 12.4,
    promoterHoldingPct: 53.1,
    promoterPledgePct: 0,
    annualDpsInr: 12.0,
    fcfPerShareInr: 58.2,
    fcf5YCagrPct: 32.4,
    epsInr: 36.4,
    dps5YCagrPct: 28.0,
    consecutiveYearsPaid: 8,
    netDebtToEbitda: 1.82,
    headline: 'India mobile ARPU crosses ₹242; free cash flow accelerates as 5G capex intensity tapers',
  },
  {
    ticker: 'M&M',
    bseCode: '500520',
    isin: 'INE101A01026',
    name: 'Mahindra & Mahindra Ltd',
    sector: 'Automobiles & EV',
    industry: 'SUVs, Tractors & EVs',
    capBucket: 'Large',
    marketCapCr: 404000,
    targetPrice: 3248,
    avgTurnoverCr: 1040,
    beta: 1.14,
    archetype: 'vcp_breakout',
    baseMonths: 6,
    breakoutVolMult: 2.24,
    qtrEpsYoY: 26.8,
    prevQtrEpsYoY: 21.4,
    qtrRevYoY: 18.9,
    prevQtrRevYoY: 15.2,
    opMarginPct: 14.8,
    opMarginExpansionBps: 125,
    earningsSurprisePct: 5.8,
    annualEps3YCagr: 29.6,
    roePct: 21.8,
    rocePct: 19.4,
    fiiHoldingPct: 41.2,
    fiiQoQChangePct: 0.88,
    diiHoldingPct: 26.4,
    diiQoQChangePct: 0.52,
    mfHoldingPct: 15.8,
    promoterHoldingPct: 18.6,
    promoterPledgePct: 0,
    annualDpsInr: 25.0,
    fcfPerShareInr: 92.4,
    fcf5YCagrPct: 22.6,
    epsInr: 104.6,
    dps5YCagrPct: 21.4,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: 0.35,
    headline: 'Born-Electric SUV order backlog crosses 1.15 lakh units; farm tractor market share climbs to 43.2%',
  },
  {
    ticker: 'SUNPHARMA',
    bseCode: '524715',
    isin: 'INE044A01036',
    name: 'Sun Pharmaceutical Industries Ltd',
    sector: 'Pharma & Healthcare',
    industry: 'Specialty Pharmaceuticals',
    capBucket: 'Large',
    marketCapCr: 468000,
    targetPrice: 1952,
    avgTurnoverCr: 620,
    beta: 0.68,
    archetype: 'fresh_breakout_mid',
    baseMonths: 9,
    breakoutVolMult: 1.84,
    qtrEpsYoY: 24.2,
    prevQtrEpsYoY: 19.6,
    qtrRevYoY: 14.6,
    prevQtrRevYoY: 11.8,
    opMarginPct: 28.9,
    opMarginExpansionBps: 150,
    earningsSurprisePct: 5.2,
    annualEps3YCagr: 19.4,
    roePct: 17.8,
    rocePct: 20.6,
    fiiHoldingPct: 18.4,
    fiiQoQChangePct: 0.61,
    diiHoldingPct: 18.6,
    diiQoQChangePct: 0.38,
    mfHoldingPct: 12.1,
    promoterHoldingPct: 54.5,
    promoterPledgePct: 0,
    annualDpsInr: 16.5,
    fcfPerShareInr: 52.4,
    fcf5YCagrPct: 18.2,
    epsInr: 49.2,
    dps5YCagrPct: 16.8,
    consecutiveYearsPaid: 24,
    netDebtToEbitda: -0.95,
    headline: 'Global specialty portfolio sales cross $1.2B annualized run-rate; US dermatology prescriptions rise',
  },
  {
    ticker: 'ITC',
    bseCode: '500875',
    isin: 'INE154A01025',
    name: 'ITC Ltd',
    sector: 'FMCG',
    industry: 'Diversified FMCG & Agri',
    capBucket: 'Large',
    marketCapCr: 632000,
    targetPrice: 506,
    avgTurnoverCr: 960,
    beta: 0.64,
    archetype: 'stage1_base',
    qtrEpsYoY: 8.6,
    prevQtrEpsYoY: 7.4,
    qtrRevYoY: 9.8,
    prevQtrRevYoY: 8.1,
    opMarginPct: 36.4,
    opMarginExpansionBps: 35,
    earningsSurprisePct: 1.4,
    annualEps3YCagr: 12.4,
    roePct: 29.2,
    rocePct: 37.8,
    fiiHoldingPct: 40.4,
    fiiQoQChangePct: 0.18,
    diiHoldingPct: 43.2,
    diiQoQChangePct: 0.28,
    mfHoldingPct: 11.4,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 15.25,
    fcfPerShareInr: 17.8,
    fcf5YCagrPct: 10.6,
    epsInr: 17.4,
    dps5YCagrPct: 8.8,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: -0.88,
    headline: 'FMCG-Others EBITDA margin crosses 11.4%; cash conversion remains above 96% of net profit',
  },
  {
    ticker: 'COALINDIA',
    bseCode: '533278',
    isin: 'INE522F01014',
    name: 'Coal India Ltd',
    sector: 'Energy & Power',
    industry: 'Thermal Coal Mining',
    capBucket: 'Large',
    marketCapCr: 302000,
    targetPrice: 490,
    avgTurnoverCr: 740,
    beta: 0.94,
    archetype: 'stage1_base',
    qtrEpsYoY: 11.2,
    prevQtrEpsYoY: 9.8,
    qtrRevYoY: 8.4,
    prevQtrRevYoY: 7.1,
    opMarginPct: 33.2,
    opMarginExpansionBps: 65,
    earningsSurprisePct: 2.4,
    annualEps3YCagr: 26.8,
    roePct: 44.2,
    rocePct: 54.6,
    fiiHoldingPct: 9.4,
    fiiQoQChangePct: 0.34,
    diiHoldingPct: 22.8,
    diiQoQChangePct: 0.41,
    mfHoldingPct: 11.8,
    promoterHoldingPct: 63.1,
    promoterPledgePct: 0,
    annualDpsInr: 28.5,
    fcfPerShareInr: 46.8,
    fcf5YCagrPct: 17.4,
    epsInr: 62.4,
    dps5YCagrPct: 14.6,
    consecutiveYearsPaid: 16,
    netDebtToEbitda: -0.94,
    headline: 'Dispatch volumes up 8.4% YoY on thermal power demand; interim dividend yield approaches 5.8%',
  },
  {
    ticker: 'POWERGRID',
    bseCode: '532898',
    isin: 'INE752E01010',
    name: 'Power Grid Corporation of India Ltd',
    sector: 'Energy & Power',
    industry: 'Power Transmission Utility',
    capBucket: 'Large',
    marketCapCr: 326000,
    targetPrice: 350,
    avgTurnoverCr: 610,
    beta: 0.72,
    archetype: 'fresh_breakout_mid',
    baseMonths: 7,
    breakoutVolMult: 1.72,
    qtrEpsYoY: 11.8,
    prevQtrEpsYoY: 9.4,
    qtrRevYoY: 10.2,
    prevQtrRevYoY: 8.4,
    opMarginPct: 84.6,
    opMarginExpansionBps: 50,
    earningsSurprisePct: 2.1,
    annualEps3YCagr: 9.8,
    roePct: 18.4,
    rocePct: 13.2,
    fiiHoldingPct: 29.4,
    fiiQoQChangePct: 0.42,
    diiHoldingPct: 15.6,
    diiQoQChangePct: 0.36,
    mfHoldingPct: 10.2,
    promoterHoldingPct: 51.3,
    promoterPledgePct: 0,
    annualDpsInr: 13.25,
    fcfPerShareInr: 19.6,
    fcf5YCagrPct: 9.2,
    epsInr: 17.8,
    dps5YCagrPct: 10.4,
    consecutiveYearsPaid: 18,
    netDebtToEbitda: 2.85,
    headline: 'Green energy corridor TBCB wins lift work-in-hand above ₹1.42 lakh Cr; regulated RoE intact',
  },
  {
    ticker: 'NTPC',
    bseCode: '532555',
    isin: 'INE733E01010',
    name: 'NTPC Ltd',
    sector: 'Energy & Power',
    industry: 'Power Generation & Renewables',
    capBucket: 'Large',
    marketCapCr: 412000,
    targetPrice: 425,
    avgTurnoverCr: 790,
    beta: 0.91,
    archetype: 'stage2_leader',
    baseMonths: 5,
    breakoutVolMult: 1.55,
    qtrEpsYoY: 16.4,
    prevQtrEpsYoY: 13.2,
    qtrRevYoY: 12.1,
    prevQtrRevYoY: 9.8,
    opMarginPct: 29.8,
    opMarginExpansionBps: 90,
    earningsSurprisePct: 3.4,
    annualEps3YCagr: 14.2,
    roePct: 13.8,
    rocePct: 10.8,
    fiiHoldingPct: 18.6,
    fiiQoQChangePct: 0.58,
    diiHoldingPct: 26.8,
    diiQoQChangePct: 0.49,
    mfHoldingPct: 18.4,
    promoterHoldingPct: 51.1,
    promoterPledgePct: 0,
    annualDpsInr: 9.5,
    fcfPerShareInr: 15.8,
    fcf5YCagrPct: 12.6,
    epsInr: 22.8,
    dps5YCagrPct: 11.2,
    consecutiveYearsPaid: 22,
    netDebtToEbitda: 3.6,
    headline: 'NTPC Green Energy commissions 3.2 GW solar-wind hybrid capacity; PLF leads national average',
  },
  {
    ticker: 'POLYCAB',
    bseCode: '542652',
    isin: 'INE455K01017',
    name: 'Polycab India Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Wires, Cables & FMEG',
    capBucket: 'Large',
    marketCapCr: 112600,
    targetPrice: 7490,
    avgTurnoverCr: 410,
    beta: 1.15,
    archetype: 'vcp_tight_pivot',
    baseMonths: 8,
    breakoutVolMult: 1.08,
    qtrEpsYoY: 27.4,
    prevQtrEpsYoY: 22.6,
    qtrRevYoY: 25.2,
    prevQtrRevYoY: 20.8,
    opMarginPct: 13.8,
    opMarginExpansionBps: 85,
    earningsSurprisePct: 4.9,
    annualEps3YCagr: 26.8,
    roePct: 22.8,
    rocePct: 30.4,
    fiiHoldingPct: 13.2,
    fiiQoQChangePct: 0.74,
    diiHoldingPct: 9.8,
    diiQoQChangePct: 0.58,
    mfHoldingPct: 8.1,
    promoterHoldingPct: 63.2,
    promoterPledgePct: 0,
    annualDpsInr: 35.0,
    fcfPerShareInr: 114.2,
    fcf5YCagrPct: 23.8,
    epsInr: 134.8,
    dps5YCagrPct: 25.4,
    consecutiveYearsPaid: 7,
    netDebtToEbitda: -0.78,
    headline: 'Extra-high-voltage cable exports jump 34% YoY; domestic infrastructure demand sustains margins',
  },
  {
    ticker: 'BAJFINANCE',
    bseCode: '500034',
    isin: 'INE296A01024',
    name: 'Bajaj Finance Ltd',
    sector: 'Banking & Financial Services',
    industry: 'Diversified NBFC',
    capBucket: 'Large',
    marketCapCr: 492000,
    targetPrice: 7945,
    avgTurnoverCr: 1160,
    beta: 1.24,
    archetype: 'fresh_breakout_long',
    baseMonths: 24,
    breakoutVolMult: 2.32,
    qtrEpsYoY: 19.4,
    prevQtrEpsYoY: 14.8,
    qtrRevYoY: 24.2,
    prevQtrRevYoY: 21.6,
    opMarginPct: 51.2,
    opMarginExpansionBps: 70,
    earningsSurprisePct: 4.2,
    annualEps3YCagr: 24.8,
    roePct: 21.4,
    rocePct: 12.2,
    fiiHoldingPct: 21.6,
    fiiQoQChangePct: 0.82,
    diiHoldingPct: 15.8,
    diiQoQChangePct: 0.64,
    mfHoldingPct: 11.4,
    promoterHoldingPct: 54.7,
    promoterPledgePct: 0,
    annualDpsInr: 40.0,
    fcfPerShareInr: 188.0,
    fcf5YCagrPct: 22.4,
    epsInr: 268.4,
    dps5YCagrPct: 28.2,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: 3.1,
    headline: 'AUM crosses ₹4.1 lakh Cr with 28% YoY growth; credit cost guidance lowered by 20 bps',
  },
  {
    ticker: 'LT',
    bseCode: '500510',
    isin: 'INE018A01030',
    name: 'Larsen & Toubro Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'EPC Infrastructure & Engineering',
    capBucket: 'Large',
    marketCapCr: 542000,
    targetPrice: 3942,
    avgTurnoverCr: 1080,
    beta: 1.12,
    archetype: 'fresh_breakout_mid',
    baseMonths: 10,
    breakoutVolMult: 1.82,
    qtrEpsYoY: 17.6,
    prevQtrEpsYoY: 14.1,
    qtrRevYoY: 16.8,
    prevQtrRevYoY: 14.2,
    opMarginPct: 11.2,
    opMarginExpansionBps: 55,
    earningsSurprisePct: 3.4,
    annualEps3YCagr: 18.6,
    roePct: 16.2,
    rocePct: 13.8,
    fiiHoldingPct: 23.4,
    fiiQoQChangePct: 0.48,
    diiHoldingPct: 40.2,
    diiQoQChangePct: 0.55,
    mfHoldingPct: 19.6,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 32.0,
    fcfPerShareInr: 98.4,
    fcf5YCagrPct: 15.8,
    epsInr: 108.6,
    dps5YCagrPct: 14.2,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: 1.45,
    headline: 'Order book surpasses ₹5.4 lakh Cr; international renewable & metro projects drive execution',
  },
  {
    ticker: 'KALYANKJIL',
    bseCode: '543278',
    isin: 'INE303R01014',
    name: 'Kalyan Jewellers India Ltd',
    sector: 'Consumer & Retail',
    industry: 'Jewellery Retail',
    capBucket: 'Mid',
    marketCapCr: 76400,
    targetPrice: 742,
    avgTurnoverCr: 430,
    beta: 1.36,
    archetype: 'vcp_breakout',
    baseMonths: 6,
    breakoutVolMult: 2.52,
    qtrEpsYoY: 41.2,
    prevQtrEpsYoY: 32.8,
    qtrRevYoY: 34.6,
    prevQtrRevYoY: 28.4,
    opMarginPct: 7.4,
    opMarginExpansionBps: 65,
    earningsSurprisePct: 8.6,
    annualEps3YCagr: 46.4,
    roePct: 19.4,
    rocePct: 17.8,
    fiiHoldingPct: 17.4,
    fiiQoQChangePct: 1.45,
    diiHoldingPct: 14.2,
    diiQoQChangePct: 0.92,
    mfHoldingPct: 12.1,
    promoterHoldingPct: 62.8,
    promoterPledgePct: 0,
    annualDpsInr: 1.8,
    fcfPerShareInr: 6.4,
    fcf5YCagrPct: 28.0,
    epsInr: 8.4,
    dps5YCagrPct: 22.0,
    consecutiveYearsPaid: 4,
    netDebtToEbitda: 0.62,
    headline: 'FOCO asset-light showroom expansion accelerates ROCE; same-store sales up 23% in festive quarter',
  },
  {
    ticker: 'INDIGO',
    bseCode: '539448',
    isin: 'INE646L01027',
    name: 'InterGlobe Aviation Ltd',
    sector: 'Consumer & Retail',
    industry: 'Aviation & Airlines',
    capBucket: 'Large',
    marketCapCr: 198000,
    targetPrice: 5120,
    avgTurnoverCr: 680,
    beta: 1.18,
    archetype: 'stage2_leader',
    baseMonths: 4,
    breakoutVolMult: 1.48,
    qtrEpsYoY: 29.4,
    prevQtrEpsYoY: 24.8,
    qtrRevYoY: 19.2,
    prevQtrRevYoY: 16.4,
    opMarginPct: 24.8,
    opMarginExpansionBps: 110,
    earningsSurprisePct: 5.4,
    annualEps3YCagr: 34.0,
    roePct: 68.4,
    rocePct: 24.2,
    fiiHoldingPct: 24.8,
    fiiQoQChangePct: 0.92,
    diiHoldingPct: 18.4,
    diiQoQChangePct: 0.64,
    mfHoldingPct: 14.6,
    promoterHoldingPct: 49.3,
    promoterPledgePct: 0,
    annualDpsInr: 0,
    fcfPerShareInr: 224.0,
    fcf5YCagrPct: 29.4,
    epsInr: 218.6,
    dps5YCagrPct: 0,
    consecutiveYearsPaid: 0,
    netDebtToEbitda: 1.9,
    headline: 'Domestic market share holds at 62.4%; international wide-body network expands to Europe & Central Asia',
  },
  {
    ticker: 'MCX',
    bseCode: '534091',
    isin: 'INE745G01035',
    name: 'Multi Commodity Exchange of India Ltd',
    sector: 'Capital Markets',
    industry: 'Commodity Exchange',
    capBucket: 'Small',
    marketCapCr: 34200,
    targetPrice: 6710,
    avgTurnoverCr: 440,
    beta: 1.34,
    archetype: 'vcp_breakout',
    baseMonths: 13,
    breakoutVolMult: 2.74,
    qtrEpsYoY: 74.6,
    prevQtrEpsYoY: 58.2,
    qtrRevYoY: 54.8,
    prevQtrRevYoY: 42.1,
    opMarginPct: 58.4,
    opMarginExpansionBps: 490,
    earningsSurprisePct: 12.1,
    annualEps3YCagr: 44.2,
    roePct: 34.8,
    rocePct: 42.6,
    fiiHoldingPct: 24.6,
    fiiQoQChangePct: 1.92,
    diiHoldingPct: 52.4,
    diiQoQChangePct: 0.84,
    mfHoldingPct: 34.8,
    promoterHoldingPct: 0,
    promoterPledgePct: 0,
    annualDpsInr: 36.0,
    fcfPerShareInr: 112.4,
    fcf5YCagrPct: 27.6,
    epsInr: 108.4,
    dps5YCagrPct: 16.5,
    consecutiveYearsPaid: 14,
    netDebtToEbitda: -2.2,
    headline: 'Bullion & crude options ADT hits ₹2.45 lakh Cr; new trading tech platform lowers software costs 62%',
  },
  {
    ticker: 'DRREDDY',
    bseCode: '500124',
    isin: 'INE089A01031',
    name: 'Dr. Reddy\'s Laboratories Ltd',
    sector: 'Pharma & Healthcare',
    industry: 'Generics & Biosimilars',
    capBucket: 'Large',
    marketCapCr: 116400,
    targetPrice: 1396,
    avgTurnoverCr: 420,
    beta: 0.66,
    archetype: 'stage3_top',
    qtrEpsYoY: 6.2,
    prevQtrEpsYoY: 14.8,
    qtrRevYoY: 9.4,
    prevQtrRevYoY: 13.6,
    opMarginPct: 26.2,
    opMarginExpansionBps: -85,
    earningsSurprisePct: -2.4,
    annualEps3YCagr: 15.8,
    roePct: 19.2,
    rocePct: 24.4,
    fiiHoldingPct: 27.8,
    fiiQoQChangePct: -0.65,
    diiHoldingPct: 24.2,
    diiQoQChangePct: 0.14,
    mfHoldingPct: 14.6,
    promoterHoldingPct: 26.6,
    promoterPledgePct: 0,
    annualDpsInr: 12.0,
    fcfPerShareInr: 44.2,
    fcf5YCagrPct: 14.2,
    epsInr: 68.4,
    dps5YCagrPct: 11.4,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: -0.64,
    headline: 'European consumer health acquisition integrates; US generic pricing pressure moderates EBITDA margin',
  },
  {
    ticker: 'TATAMOTORS',
    bseCode: '500570',
    isin: 'INE155A01022',
    name: 'Tata Motors Ltd',
    sector: 'Automobiles & EV',
    industry: 'Commercial, PV & JLR Luxury',
    capBucket: 'Large',
    marketCapCr: 318000,
    targetPrice: 864,
    avgTurnoverCr: 1420,
    beta: 1.38,
    archetype: 'stage4_decline',
    qtrEpsYoY: -11.4,
    prevQtrEpsYoY: 4.2,
    qtrRevYoY: -3.2,
    prevQtrRevYoY: 5.8,
    opMarginPct: 11.8,
    opMarginExpansionBps: -140,
    earningsSurprisePct: -6.8,
    annualEps3YCagr: 22.0,
    roePct: 24.6,
    rocePct: 17.8,
    fiiHoldingPct: 18.2,
    fiiQoQChangePct: -1.45,
    diiHoldingPct: 16.4,
    diiQoQChangePct: 0.22,
    mfHoldingPct: 10.6,
    promoterHoldingPct: 42.6,
    promoterPledgePct: 0,
    annualDpsInr: 6.0,
    fcfPerShareInr: 28.4,
    fcf5YCagrPct: 14.0,
    epsInr: 58.2,
    dps5YCagrPct: 12.0,
    consecutiveYearsPaid: 3,
    netDebtToEbitda: 0.92,
    headline: 'JLR China wholesale demand softens; domestic EV competition prompts dealer incentives',
  },
  {
    ticker: 'TATAELXSI',
    bseCode: '500408',
    isin: 'INE670A01012',
    name: 'Tata Elxsi Ltd',
    sector: 'Information Technology',
    industry: 'ER&D Design Services',
    capBucket: 'Mid',
    marketCapCr: 43800,
    targetPrice: 7030,
    avgTurnoverCr: 215,
    beta: 1.12,
    archetype: 'stage4_decline',
    qtrEpsYoY: -4.8,
    prevQtrEpsYoY: 2.1,
    qtrRevYoY: 1.8,
    prevQtrRevYoY: 5.4,
    opMarginPct: 25.4,
    opMarginExpansionBps: -195,
    earningsSurprisePct: -4.2,
    annualEps3YCagr: 14.2,
    roePct: 30.8,
    rocePct: 39.4,
    fiiHoldingPct: 13.4,
    fiiQoQChangePct: -0.94,
    diiHoldingPct: 6.8,
    diiQoQChangePct: -0.18,
    mfHoldingPct: 4.2,
    promoterHoldingPct: 43.9,
    promoterPledgePct: 0,
    annualDpsInr: 72.0,
    fcfPerShareInr: 126.4,
    fcf5YCagrPct: 15.6,
    epsInr: 128.8,
    dps5YCagrPct: 28.4,
    consecutiveYearsPaid: 22,
    netDebtToEbitda: -1.42,
    headline: 'European automotive OEM ER&D spend delayed; healthcare and media verticals show steady pipeline',
  },
  {
    ticker: 'DMART',
    bseCode: '540376',
    isin: 'INE192R01011',
    name: 'Avenue Supermarts Ltd',
    sector: 'Consumer & Retail',
    industry: 'Hypermarkets & Grocery',
    capBucket: 'Large',
    marketCapCr: 262000,
    targetPrice: 4025,
    avgTurnoverCr: 410,
    beta: 0.89,
    archetype: 'stage3_top',
    qtrEpsYoY: 5.8,
    prevQtrEpsYoY: 12.4,
    qtrRevYoY: 14.2,
    prevQtrRevYoY: 18.6,
    opMarginPct: 7.6,
    opMarginExpansionBps: -45,
    earningsSurprisePct: -3.6,
    annualEps3YCagr: 16.4,
    roePct: 14.2,
    rocePct: 19.6,
    fiiHoldingPct: 9.2,
    fiiQoQChangePct: -0.52,
    diiHoldingPct: 8.6,
    diiQoQChangePct: 0.14,
    mfHoldingPct: 6.9,
    promoterHoldingPct: 74.6,
    promoterPledgePct: 0,
    annualDpsInr: 0,
    fcfPerShareInr: 18.4,
    fcf5YCagrPct: 12.2,
    epsInr: 41.6,
    dps5YCagrPct: 0,
    consecutiveYearsPaid: 0,
    netDebtToEbitda: -0.22,
    headline: 'Quick-commerce competition weighs on metro SSSG; DMart Ready expands into 6 new Tier-1 cities',
  },
  {
    ticker: 'TITAN',
    bseCode: '500114',
    isin: 'INE280A01028',
    name: 'Titan Company Ltd',
    sector: 'Consumer & Retail',
    industry: 'Jewellery, Watches & Eyewear',
    capBucket: 'Large',
    marketCapCr: 334000,
    targetPrice: 3762,
    avgTurnoverCr: 640,
    beta: 0.92,
    archetype: 'fresh_breakout_long',
    baseMonths: 18,
    breakoutVolMult: 1.92,
    qtrEpsYoY: 22.8,
    prevQtrEpsYoY: 16.4,
    qtrRevYoY: 21.4,
    prevQtrRevYoY: 17.8,
    opMarginPct: 11.4,
    opMarginExpansionBps: 78,
    earningsSurprisePct: 4.1,
    annualEps3YCagr: 21.8,
    roePct: 32.6,
    rocePct: 24.8,
    fiiHoldingPct: 18.8,
    fiiQoQChangePct: 0.64,
    diiHoldingPct: 11.4,
    diiQoQChangePct: 0.42,
    mfHoldingPct: 7.8,
    promoterHoldingPct: 52.9,
    promoterPledgePct: 0,
    annualDpsInr: 13.0,
    fcfPerShareInr: 36.8,
    fcf5YCagrPct: 16.4,
    epsInr: 44.2,
    dps5YCagrPct: 18.2,
    consecutiveYearsPaid: 24,
    netDebtToEbitda: 0.84,
    headline: 'Tanishq studded jewellery share recovers to 31%; CaratLane posts 32% YoY top-line growth',
  },
  {
    ticker: 'PIDILITIND',
    bseCode: '500331',
    isin: 'INE318A01026',
    name: 'Pidilite Industries Ltd',
    sector: 'Chemicals & Materials',
    industry: 'Adhesives & Construction Chemicals',
    capBucket: 'Large',
    marketCapCr: 168400,
    targetPrice: 3312,
    avgTurnoverCr: 290,
    beta: 0.76,
    archetype: 'vcp_tight_pivot',
    baseMonths: 11,
    breakoutVolMult: 1.12,
    qtrEpsYoY: 19.6,
    prevQtrEpsYoY: 15.8,
    qtrRevYoY: 11.8,
    prevQtrRevYoY: 9.4,
    opMarginPct: 23.4,
    opMarginExpansionBps: 135,
    earningsSurprisePct: 3.8,
    annualEps3YCagr: 17.6,
    roePct: 23.4,
    rocePct: 29.8,
    fiiHoldingPct: 11.8,
    fiiQoQChangePct: 0.36,
    diiHoldingPct: 9.2,
    diiQoQChangePct: 0.28,
    mfHoldingPct: 5.4,
    promoterHoldingPct: 69.8,
    promoterPledgePct: 0,
    annualDpsInr: 18.0,
    fcfPerShareInr: 42.6,
    fcf5YCagrPct: 15.4,
    epsInr: 39.8,
    dps5YCagrPct: 15.8,
    consecutiveYearsPaid: 25,
    netDebtToEbitda: -0.34,
    headline: 'VAM input costs remain benign; rural distribution reach surpasses 1.35 lakh villages',
  },
  {
    ticker: 'ANGELONE',
    bseCode: '543235',
    isin: 'INE732I01013',
    name: 'Angel One Ltd',
    sector: 'Capital Markets',
    industry: 'Digital Broking & Wealth',
    capBucket: 'Small',
    marketCapCr: 28400,
    targetPrice: 3148,
    avgTurnoverCr: 480,
    beta: 1.52,
    archetype: 'fresh_breakout_mid',
    baseMonths: 9,
    breakoutVolMult: 2.48,
    qtrEpsYoY: 36.4,
    prevQtrEpsYoY: 28.2,
    qtrRevYoY: 41.2,
    prevQtrRevYoY: 34.8,
    opMarginPct: 44.6,
    opMarginExpansionBps: 165,
    earningsSurprisePct: 7.4,
    annualEps3YCagr: 42.6,
    roePct: 36.2,
    rocePct: 32.8,
    fiiHoldingPct: 17.2,
    fiiQoQChangePct: 1.35,
    diiHoldingPct: 14.6,
    diiQoQChangePct: 1.12,
    mfHoldingPct: 12.2,
    promoterHoldingPct: 35.6,
    promoterPledgePct: 0,
    annualDpsInr: 42.0,
    fcfPerShareInr: 118.4,
    fcf5YCagrPct: 36.2,
    epsInr: 146.2,
    dps5YCagrPct: 32.0,
    consecutiveYearsPaid: 6,
    netDebtToEbitda: -0.45,
    headline: 'Client base crosses 2.9 Cr; wealth management & mutual fund distribution AUM triples YoY',
  },
  {
    ticker: 'SUZLON',
    bseCode: '532667',
    isin: 'INE040H01021',
    name: 'Suzlon Energy Ltd',
    sector: 'Energy & Power',
    industry: 'Wind Turbine Equipment',
    capBucket: 'Mid',
    marketCapCr: 96400,
    targetPrice: 70.8,
    avgTurnoverCr: 690,
    beta: 1.58,
    archetype: 'vcp_tight_pivot',
    baseMonths: 5,
    breakoutVolMult: 1.24,
    qtrEpsYoY: 84.2,
    prevQtrEpsYoY: 62.4,
    qtrRevYoY: 56.4,
    prevQtrRevYoY: 44.2,
    opMarginPct: 16.4,
    opMarginExpansionBps: 210,
    earningsSurprisePct: 9.8,
    annualEps3YCagr: 54.0,
    roePct: 24.8,
    rocePct: 26.4,
    fiiHoldingPct: 22.8,
    fiiQoQChangePct: 1.72,
    diiHoldingPct: 10.4,
    diiQoQChangePct: 0.94,
    mfHoldingPct: 5.8,
    promoterHoldingPct: 13.3,
    promoterPledgePct: 0,
    annualDpsInr: 0,
    fcfPerShareInr: 0.86,
    fcf5YCagrPct: 38.0,
    epsInr: 0.98,
    dps5YCagrPct: 0,
    consecutiveYearsPaid: 0,
    netDebtToEbitda: -0.82,
    headline: 'Net-cash balance sheet achieved; S144 3MW wind turbine order book stands at 5.6 GW',
  },
  {
    ticker: 'SHAKTIPUMP',
    bseCode: '531431',
    isin: 'INE908D01010',
    name: 'Shakti Pumps (India) Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Solar Pumps & EV Motors',
    capBucket: 'Micro',
    marketCapCr: 11850,
    targetPrice: 984,
    avgTurnoverCr: 115,
    beta: 1.48,
    archetype: 'vcp_breakout',
    baseMonths: 7,
    breakoutVolMult: 3.12,
    qtrEpsYoY: 118.4,
    prevQtrEpsYoY: 94.2,
    qtrRevYoY: 88.6,
    prevQtrRevYoY: 71.4,
    opMarginPct: 22.4,
    opMarginExpansionBps: 540,
    earningsSurprisePct: 16.2,
    annualEps3YCagr: 68.4,
    roePct: 34.2,
    rocePct: 39.8,
    fiiHoldingPct: 4.8,
    fiiQoQChangePct: 1.42,
    diiHoldingPct: 6.4,
    diiQoQChangePct: 1.18,
    mfHoldingPct: 5.2,
    promoterHoldingPct: 51.6,
    promoterPledgePct: 0,
    annualDpsInr: 4.0,
    fcfPerShareInr: 18.6,
    fcf5YCagrPct: 44.2,
    epsInr: 34.2,
    dps5YCagrPct: 24.0,
    consecutiveYearsPaid: 12,
    netDebtToEbitda: 0.18,
    headline: 'PM-KUSUM solar pump orders surge across Maharashtra & Rajasthan; operating margins top 22%',
  },
  {
    ticker: 'ELECON',
    bseCode: '505700',
    isin: 'INE205B01031',
    name: 'Elecon Engineering Company Ltd',
    sector: 'Capital Goods & Defence',
    industry: 'Industrial Gears & Material Handling',
    capBucket: 'Micro',
    marketCapCr: 14600,
    targetPrice: 652,
    avgTurnoverCr: 94,
    beta: 1.32,
    archetype: 'fresh_breakout_long',
    baseMonths: 15,
    breakoutVolMult: 2.38,
    qtrEpsYoY: 32.4,
    prevQtrEpsYoY: 24.8,
    qtrRevYoY: 22.6,
    prevQtrRevYoY: 18.2,
    opMarginPct: 24.2,
    opMarginExpansionBps: 155,
    earningsSurprisePct: 6.4,
    annualEps3YCagr: 39.2,
    roePct: 24.6,
    rocePct: 30.8,
    fiiHoldingPct: 8.6,
    fiiQoQChangePct: 0.94,
    diiHoldingPct: 4.2,
    diiQoQChangePct: 0.62,
    mfHoldingPct: 3.4,
    promoterHoldingPct: 59.3,
    promoterPledgePct: 0,
    annualDpsInr: 2.5,
    fcfPerShareInr: 16.4,
    fcf5YCagrPct: 28.4,
    epsInr: 18.2,
    dps5YCagrPct: 26.8,
    consecutiveYearsPaid: 15,
    netDebtToEbitda: -0.74,
    headline: 'Marine & defence gear export orders expand 40%; debt-free balance sheet supports European expansion',
  },
];

function buildOhlcvForSpec(spec: StockSeedSpec, index: number): OHLCVBar[] {
  const rng = createRng(104729 + index * 7919);
  const N = NSE_TRADING_DATES.length; // 780 bars
  const closes = new Array<number>(N);
  const volumes = new Array<number>(N);
  const avgVolBase = Math.max(
    120000,
    Math.round((spec.avgTurnoverCr * 1e7) / Math.max(spec.targetPrice, 10))
  );

  // Build normalized price trajectory ending near 1.0, then scale to spec.targetPrice
  const baseMonths = spec.baseMonths ?? 8;
  const baseBars = Math.min(N - 60, Math.max(45, Math.round(baseMonths * 21)));

  if (spec.archetype === 'vcp_breakout' || spec.archetype === 'vcp_tight_pivot') {
    // Stage 2 uptrend -> prior peak baseBars ago -> textbook shrinking VCP contractions -> pivot breakout or tight pivot
    const priorPeakIdx = N - 1 - baseBars;
    const pivotLevel = 1.0;

    // Pre-peak uptrend from ~0.46 to 1.00
    for (let i = 0; i <= priorPeakIdx; i++) {
      const t = i / Math.max(1, priorPeakIdx);
      const trend = 0.44 + 0.56 * Math.pow(t, 1.15);
      const wave = Math.sin(i * 0.09 + index) * 0.025 + (rng() - 0.5) * 0.012;
      closes[i] = Math.min(0.992, Math.max(0.35, trend + wave));
      volumes[i] = Math.round(avgVolBase * (0.78 + rng() * 0.48));
    }
    closes[priorPeakIdx] = pivotLevel * 0.998;
    volumes[priorPeakIdx] = Math.round(avgVolBase * 1.45);

    // Build 4 successive shrinking VCP contractions across the last baseBars
    const contractions = [
      { depth: 0.22 + (index % 4) * 0.015, frac: 0.36 },
      { depth: 0.125 + (index % 3) * 0.01, frac: 0.28 },
      { depth: 0.062 + (index % 2) * 0.008, frac: 0.21 },
      { depth: 0.026, frac: 0.15 },
    ];
    let cursor = priorPeakIdx + 1;
    const endIdx = spec.archetype === 'vcp_breakout' ? N - 3 : N - 1;
    const span = Math.max(24, endIdx - cursor);

    contractions.forEach((c, ci) => {
      const segLen =
        ci === contractions.length - 1
          ? endIdx - cursor + 1
          : Math.max(6, Math.round(span * c.frac));
      const mid = Math.floor(segLen * 0.52);
      for (let j = 0; j < segLen && cursor <= endIdx; j++, cursor++) {
        const halfT = j <= mid ? j / Math.max(1, mid) : (segLen - j) / Math.max(1, segLen - mid);
        const drop = c.depth * Math.sin((halfT * Math.PI) / 2);
        const jitter = (rng() - 0.5) * 0.005;
        closes[cursor] = Math.min(pivotLevel * 0.994, pivotLevel * (1 - drop) + jitter);
        // Volume dries up markedly in final contraction
        const volScale = ci === 3 ? 0.38 + rng() * 0.18 : 0.95 - ci * 0.14 + rng() * 0.28;
        volumes[cursor] = Math.round(avgVolBase * volScale);
      }
    });

    if (spec.archetype === 'vcp_breakout') {
      // Final 2 bars: decisive breakout above pivot on institutional volume
      closes[N - 2] = pivotLevel * 1.008;
      volumes[N - 2] = Math.round(avgVolBase * 1.65);
      closes[N - 1] = pivotLevel * (1.032 + (index % 3) * 0.007);
      volumes[N - 1] = Math.round(avgVolBase * (spec.breakoutVolMult ?? 2.3));
    } else {
      // Tight pivot ready to break out (within ~1.5% of pivot, super dry volume)
      closes[N - 2] = pivotLevel * 0.986;
      volumes[N - 2] = Math.round(avgVolBase * 0.44);
      closes[N - 1] = pivotLevel * 0.991;
      volumes[N - 1] = Math.round(avgVolBase * 0.48);
    }
  } else if (spec.archetype === 'fresh_breakout_long' || spec.archetype === 'fresh_breakout_mid') {
    // Prior 52W high happened baseBars ago, then multi-month saucer/cup base, breaking out TODAY
    const priorPeakIdx = N - 1 - baseBars;
    const priorHigh = 1.0;

    for (let i = 0; i < priorPeakIdx; i++) {
      const t = i / Math.max(1, priorPeakIdx);
      const val = 0.52 + 0.46 * t + Math.sin(i * 0.07) * 0.03 + (rng() - 0.5) * 0.014;
      closes[i] = Math.min(0.985, Math.max(0.42, val));
      volumes[i] = Math.round(avgVolBase * (0.8 + rng() * 0.45));
    }
    closes[priorPeakIdx] = priorHigh;
    volumes[priorPeakIdx] = Math.round(avgVolBase * 1.5);

    const cupDepth = spec.archetype === 'fresh_breakout_long' ? 0.24 : 0.18;
    for (let i = priorPeakIdx + 1; i < N - 1; i++) {
      const u = (i - priorPeakIdx) / Math.max(1, N - 1 - priorPeakIdx);
      // Smooth cup with small handle near the right side
      let shape = 1 - cupDepth * Math.sin(Math.PI * Math.pow(u, 0.85));
      if (u > 0.84) {
        const hu = (u - 0.84) / 0.16;
        shape = 0.982 - 0.045 * Math.sin(Math.PI * hu);
      }
      const jitter = (rng() - 0.5) * 0.008;
      closes[i] = Math.min(priorHigh * 0.992, Math.max(0.62, shape + jitter));
      const volMult = u > 0.84 ? 0.52 + rng() * 0.24 : 0.78 + rng() * 0.42;
      volumes[i] = Math.round(avgVolBase * volMult);
    }
    closes[N - 1] = priorHigh * (1.028 + (index % 4) * 0.006);
    volumes[N - 1] = Math.round(avgVolBase * (spec.breakoutVolMult ?? 2.0));
  } else if (spec.archetype === 'stage2_leader') {
    // Persistent Stage 2 uptrend making periodic new highs, currently slightly extended
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      const base = 0.48 + 0.52 * Math.pow(t, 1.08);
      const wave = Math.sin(i * 0.08 + index) * 0.028 + (rng() - 0.5) * 0.011;
      closes[i] = Math.max(0.4, base + wave);
      volumes[i] = Math.round(avgVolBase * (0.8 + rng() * 0.48));
    }
    closes[N - 1] = closes[N - 2] * 1.012;
  } else if (spec.archetype === 'stage1_base') {
    // Sideways Stage 1 consolidation around 200 SMA
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      const drift = t < 0.45 ? 0.84 + 0.2 * (t / 0.45) : 0.98 + Math.sin(i * 0.065) * 0.055;
      closes[i] = Math.max(0.7, drift + (rng() - 0.5) * 0.012);
      volumes[i] = Math.round(avgVolBase * (0.76 + rng() * 0.45));
    }
  } else if (spec.archetype === 'stage3_top') {
    // Run-up followed by choppy topping range losing 50 SMA, flattening 200 SMA
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      let val: number;
      if (t < 0.7) {
        val = 0.62 + 0.52 * (t / 0.7);
      } else {
        const u = (t - 0.7) / 0.3;
        val = 1.14 - 0.14 * u + Math.sin(i * 0.15) * 0.048;
      }
      closes[i] = Math.max(0.55, val + (rng() - 0.5) * 0.014);
      volumes[i] = Math.round(avgVolBase * (0.85 + rng() * 0.55));
    }
  } else {
    // Stage 4 decline: peaked ~10 months ago, falling steadily below declining 50/150/200 SMAs
    for (let i = 0; i < N; i++) {
      const t = i / (N - 1);
      let val: number;
      if (t < 0.58) {
        val = 0.85 + 0.58 * (t / 0.58);
      } else {
        const u = (t - 0.58) / 0.42;
        val = 1.43 - 0.44 * u + Math.sin(i * 0.11) * 0.025;
      }
      closes[i] = Math.max(0.5, val + (rng() - 0.5) * 0.014);
      volumes[i] = Math.round(avgVolBase * (0.85 + rng() * 0.6));
    }
  }

  // Scale so final close matches spec.targetPrice cleanly
  const scale = spec.targetPrice / closes[N - 1];
  const bars: OHLCVBar[] = [];

  for (let i = 0; i < N; i++) {
    const close = Number((closes[i] * scale).toFixed(2));
    const prev = i === 0 ? close * (1 + (rng() - 0.5) * 0.01) : bars[i - 1].close;
    const gap = (rng() - 0.49) * 0.007;
    const open = Number((prev * (1 + gap)).toFixed(2));
    const wickScale =
      (spec.archetype === 'vcp_breakout' || spec.archetype === 'vcp_tight_pivot') && i > N - 22 && i < N - 2
        ? 0.005
        : 0.012;
    const high = Number((Math.max(open, close) * (1 + rng() * wickScale)).toFixed(2));
    const low = Number((Math.min(open, close) * (1 - rng() * wickScale)).toFixed(2));
    bars.push({
      date: NSE_TRADING_DATES[i],
      open,
      high,
      low,
      close,
      volume: volumes[i],
    });
  }

  // Enforce exact prior-high cleanliness for breakout stocks so 52W scanner math is razor sharp
  if (
    spec.archetype === 'vcp_breakout' ||
    spec.archetype === 'fresh_breakout_long' ||
    spec.archetype === 'fresh_breakout_mid'
  ) {
    const priorPeakIdx = N - 1 - baseBars;
    const todayBar = bars[N - 1];
    // Cap highs strictly inside (priorPeakIdx, N - 2) below priorPeakIdx close/high
    const capVal = Number((todayBar.close * 0.968).toFixed(2));
    if (bars[priorPeakIdx].high < capVal) {
      bars[priorPeakIdx].high = Number((capVal * 1.004).toFixed(2));
      bars[priorPeakIdx].close = capVal;
    }
    const ceiling = Number((bars[priorPeakIdx].close * 0.993).toFixed(2));
    for (let i = priorPeakIdx + 1; i < N - 1; i++) {
      if (bars[i].high > ceiling) bars[i].high = ceiling;
      if (bars[i].close > ceiling) bars[i].close = Number((ceiling * 0.996).toFixed(2));
      if (bars[i].open > ceiling) bars[i].open = Number((ceiling * 0.995).toFixed(2));
      if (bars[i].low > bars[i].close) bars[i].low = Number((bars[i].close * 0.99).toFixed(2));
    }
    // Ensure today breaks above prior peak cleanly
    if (todayBar.close <= bars[priorPeakIdx].high) {
      todayBar.close = Number((bars[priorPeakIdx].high * 1.024).toFixed(2));
      todayBar.high = Number((todayBar.close * 1.008).toFixed(2));
    }
  }

  return bars;
}

function buildBenchmark(
  id: 'NIFTY50' | 'NIFTY500' | 'SENSEX',
  name: string,
  exchange: 'NSE' | 'BSE',
  targetLevel: number,
  seed: number,
  annualDrift: number
): BenchmarkSeries {
  const rng = createRng(seed);
  const N = NSE_TRADING_DATES.length;
  const raw = new Array<number>(N);
  raw[0] = 1;
  const dailyDrift = annualDrift / 252;
  for (let i = 1; i < N; i++) {
    const shock = (rng() - 0.485) * 0.0135 + Math.sin(i * 0.045) * 0.0014;
    raw[i] = raw[i - 1] * (1 + dailyDrift + shock);
  }
  const scale = targetLevel / raw[N - 1];
  const bars: OHLCVBar[] = raw.map((v, i) => {
    const close = Number((v * scale).toFixed(2));
    const open = i === 0 ? close : Number((raw[i - 1] * scale).toFixed(2));
    const high = Number((Math.max(open, close) * (1 + rng() * 0.005)).toFixed(2));
    const low = Number((Math.min(open, close) * (1 - rng() * 0.005)).toFixed(2));
    return {
      date: NSE_TRADING_DATES[i],
      open,
      high,
      low,
      close,
      volume: Math.round(250_000_000 * (0.8 + rng() * 0.4)),
    };
  });

  const latestClose = bars[N - 1].close;
  const prevClose = bars[N - 2].close;
  return {
    id,
    name,
    exchange,
    bars,
    latestClose,
    changePct: Number((((latestClose - prevClose) / prevClose) * 100).toFixed(2)),
  };
}

export const BENCHMARKS: Record<'NIFTY50' | 'NIFTY500' | 'SENSEX', BenchmarkSeries> = {
  NIFTY50: buildBenchmark('NIFTY50', 'NIFTY 50', 'NSE', 25842.65, 9001, 0.138),
  NIFTY500: buildBenchmark('NIFTY500', 'NIFTY 500', 'NSE', 23914.3, 9002, 0.162),
  SENSEX: buildBenchmark('SENSEX', 'S&P BSE SENSEX', 'BSE', 84912.4, 9003, 0.134),
};

const ALL_STOCK_SPECS: StockSeedSpec[] = [...STOCK_SPECS, ...EXPANDED_NSE_SPECS];

const CATALOG_FLAGS_BY_TICKER = new Map<string, number>();
for (const row of NSE_1100_CATALOG) {
  CATALOG_FLAGS_BY_TICKER.set(row[0], row[6]);
}

function decodeMembership(flags: number, capBucket: MarketCapBucket): UniverseMembership {
  return {
    nifty100: Boolean(flags & NSE_FLAG_NIFTY100) || (flags === 0 && capBucket === 'Large'),
    nifty500: Boolean(flags & NSE_FLAG_NIFTY500) || (flags === 0 && capBucket !== 'Micro'),
    fno: Boolean(flags & NSE_FLAG_FNO),
    midcap: Boolean(flags & NSE_FLAG_MIDCAP) || (flags === 0 && capBucket === 'Mid'),
    smallcap: Boolean(flags & NSE_FLAG_SMALLCAP) || (flags === 0 && capBucket === 'Small'),
    microcap: Boolean(flags & NSE_FLAG_MICROCAP) || (flags === 0 && capBucket === 'Micro'),
  };
}

function hashTicker(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

const EXTENDED_SEED_DATES = NSE_TRADING_DATES.slice(-275);

/**
 * Lightweight neutral seed builder for extended NSE catalog equities (~980 stocks)
 * prior to Tier-2 live NSE OHLCV hydration. Designed for <25ms startup across 1,000+ stocks
 * and neutral baseline metrics so unhydrated placeholders never outrank real live setups.
 */
function buildExtendedCatalogStock(tuple: NseCatalogTuple): IndianStock {
  const [ticker, name, sector, industry, capBucket, isin, flags] = tuple;
  const rng = createRng(hashTicker(ticker));
  const membership = decodeMembership(flags, capBucket);

  const mcapCr =
    capBucket === 'Large'
      ? Math.round(42000 + rng() * 140000)
      : capBucket === 'Mid'
      ? Math.round(14000 + rng() * 38000)
      : capBucket === 'Small'
      ? Math.round(2800 + rng() * 13500)
      : Math.round(650 + rng() * 3800);

  const basePrice = Number((95 + rng() * 1650).toFixed(2));
  const avgTurnoverCr = Number(
    (capBucket === 'Large'
      ? 140 + rng() * 280
      : capBucket === 'Mid'
      ? 45 + rng() * 140
      : capBucket === 'Small'
      ? 14 + rng() * 55
      : 5 + rng() * 24
    ).toFixed(2)
  );
  const avgDailyVol = Math.max(15000, Math.round((avgTurnoverCr * 1e7) / Math.max(10, basePrice)));

  // Neutral range-bound baseline candles until real live NSE candles replace them
  const bars: OHLCVBar[] = new Array(EXTENDED_SEED_DATES.length);
  let p = basePrice * (0.94 + rng() * 0.12);
  for (let i = 0; i < EXTENDED_SEED_DATES.length; i++) {
    const drift = (basePrice - p) * 0.015 + (rng() - 0.5) * basePrice * 0.018;
    const open = Number(Math.max(5, p).toFixed(2));
    const close = Number(Math.max(5, p + drift).toFixed(2));
    const spread = Math.max(0.2, Math.abs(close - open) + basePrice * (0.004 + rng() * 0.008));
    const high = Number((Math.max(open, close) + spread * 0.5).toFixed(2));
    const low = Number(Math.max(1, Math.min(open, close) - spread * 0.5).toFixed(2));
    const volume = Math.round(avgDailyVol * (0.65 + rng() * 0.7));
    bars[i] = { date: EXTENDED_SEED_DATES[i], open, high, low, close, volume };
    p = close;
  }

  const latestClose = bars[bars.length - 1].close;
  const prevClose = bars[bars.length - 2].close;
  const dailyChangePct = Number((((latestClose - prevClose) / Math.max(0.01, prevClose)) * 100).toFixed(2));

  // Calibrated baseline fundamental profile (moderate band; live Fundamentals API fetches audited XBRL on inspect)
  const qtrEpsYoY = Number((6 + rng() * 20).toFixed(1));
  const prevQtrEpsYoY = Number((qtrEpsYoY - 1.5 + rng() * 3.5).toFixed(1));
  const qtrRevYoY = Number((5 + rng() * 16).toFixed(1));
  const prevQtrRevYoY = Number((qtrRevYoY - 1.2 + rng() * 2.8).toFixed(1));
  const opMarginPct = Number((10 + rng() * 14).toFixed(1));
  const opMarginExpansionBps = Math.round(-25 + rng() * 115);
  const roePct = Number((10 + rng() * 13).toFixed(1));
  const rocePct = Number((roePct + 1.2 + rng() * 4).toFixed(1));
  const fiiHoldingPct = Number((capBucket === 'Large' ? 14 + rng() * 16 : 4 + rng() * 14).toFixed(1));
  const fiiQoQChangePct = Number((-0.25 + rng() * 0.75).toFixed(2));
  const diiHoldingPct = Number((capBucket === 'Large' ? 12 + rng() * 14 : 4 + rng() * 13).toFixed(1));
  const diiQoQChangePct = Number((-0.15 + rng() * 0.65).toFixed(2));
  const epsInr = Number(Math.max(2, latestClose / (18 + rng() * 20)).toFixed(2));
  const annualDpsInr = Number((epsInr * (0.08 + rng() * 0.16)).toFixed(2));
  const fcfPerShareInr = Number((epsInr * (0.72 + rng() * 0.35)).toFixed(2));

  const qEpsBase = epsInr / 4;
  const qRevBase = Math.round(mcapCr * 0.055);
  const sensitivities =
    SECTOR_SENSITIVITIES[sector] ?? SECTOR_SENSITIVITIES['Capital Goods & Defence'];

  return {
    ticker,
    bseCode: String(500000 + (hashTicker(ticker) % 45000)),
    isin,
    name,
    sector,
    industry,
    capBucket,
    marketCapCr: mcapCr,
    beta: Number((0.82 + rng() * 0.56).toFixed(2)),
    bars,
    latestClose,
    prevClose,
    dailyChangePct,
    avgDailyTurnoverCr: avgTurnoverCr,
    universe: membership,
    isLiveHydrated: false,
    fundamentals: {
      qtrEpsYoY,
      prevQtrEpsYoY,
      qtrRevYoY,
      prevQtrRevYoY,
      opMarginPct,
      opMarginExpansionBps,
      earningsSurprisePct: Number((-1 + rng() * 6).toFixed(1)),
      annualEps3YCagr: Number((8 + rng() * 16).toFixed(1)),
      roePct,
      rocePct,
      fiiHoldingPct,
      fiiQoQChangePct,
      diiHoldingPct,
      diiQoQChangePct,
      mfHoldingPct: Number((diiHoldingPct * 0.68).toFixed(1)),
      promoterHoldingPct: Number((42 + rng() * 28).toFixed(1)),
      promoterPledgePct: 0,
      quarterlyHistory: [
        { quarter: 'Q3 FY26', epsInr: Number((qEpsBase * 0.88).toFixed(2)), epsYoY: Number((prevQtrEpsYoY - 1.5).toFixed(1)), revenueCr: Math.round(qRevBase * 0.91), revYoY: Number((prevQtrRevYoY - 1.2).toFixed(1)), opmPct: Number((opMarginPct - 0.4).toFixed(1)) },
        { quarter: 'Q4 FY26', epsInr: Number((qEpsBase * 0.93).toFixed(2)), epsYoY: Number((prevQtrEpsYoY - 0.6).toFixed(1)), revenueCr: Math.round(qRevBase * 0.95), revYoY: Number((prevQtrRevYoY - 0.5).toFixed(1)), opmPct: Number((opMarginPct - 0.2).toFixed(1)) },
        { quarter: 'Q1 FY27', epsInr: Number((qEpsBase * 0.98).toFixed(2)), epsYoY: prevQtrEpsYoY, revenueCr: Math.round(qRevBase * 0.98), revYoY: prevQtrRevYoY, opmPct: Number((opMarginPct - 0.1).toFixed(1)) },
        { quarter: 'Q2 FY27', epsInr: Number((qEpsBase * 1.04).toFixed(2)), epsYoY: qtrEpsYoY, revenueCr: Math.round(qRevBase * 1.03), revYoY: qtrRevYoY, opmPct: opMarginPct },
      ],
    },
    dividend: {
      annualDpsInr,
      dividendYieldPct: Number(((annualDpsInr / Math.max(1, latestClose)) * 100).toFixed(2)),
      fcfPerShareInr,
      fcf5YCagrPct: Number((8 + rng() * 12).toFixed(1)),
      epsInr,
      dps5YCagrPct: Number((6 + rng() * 10).toFixed(1)),
      consecutiveYearsPaid: Math.round(4 + rng() * 14),
      netDebtToEbitda: Number((-0.4 + rng() * 1.8).toFixed(2)),
      historicalDps: [
        { year: 'FY22', dps: Number((annualDpsInr * 0.72).toFixed(2)), fcfPerShare: Number((fcfPerShareInr * 0.74).toFixed(2)) },
        { year: 'FY23', dps: Number((annualDpsInr * 0.8).toFixed(2)), fcfPerShare: Number((fcfPerShareInr * 0.81).toFixed(2)) },
        { year: 'FY24', dps: Number((annualDpsInr * 0.88).toFixed(2)), fcfPerShare: Number((fcfPerShareInr * 0.88).toFixed(2)) },
        { year: 'FY25', dps: Number((annualDpsInr * 0.94).toFixed(2)), fcfPerShare: Number((fcfPerShareInr * 0.94).toFixed(2)) },
        { year: 'FY26', dps: annualDpsInr, fcfPerShare: fcfPerShareInr },
      ],
    },
    sensitivities,
    recentNews: [
      {
        date: '2026-11-19',
        headline: `${name} (${ticker}) tracked in live NSE ${membership.nifty500 ? 'NIFTY 500' : membership.smallcap ? 'NIFTY Smallcap' : 'Mainboard'}${membership.fno ? ' & F&O' : ''} universe`,
        source: 'NSE India Directory',
      },
    ],
  };
}

const CORE_BUILT_STOCKS: IndianStock[] = ALL_STOCK_SPECS.map((spec, idx) => {
  const bars = buildOhlcvForSpec(spec, idx);
  const latestClose = bars[bars.length - 1].close;
  const prevClose = bars[bars.length - 2].close;
  const dailyChangePct = Number((((latestClose - prevClose) / prevClose) * 100).toFixed(2));
  const flags = CATALOG_FLAGS_BY_TICKER.get(spec.ticker) ?? 0;

  const qEpsBase = spec.epsInr / 4;
  const qRevBase = Math.round(spec.marketCapCr * 0.055);
  const quarterlyHistory = [
    {
      quarter: 'Q3 FY26',
      epsInr: Number((qEpsBase * 0.84).toFixed(2)),
      epsYoY: Number((spec.prevQtrEpsYoY - 4.2).toFixed(1)),
      revenueCr: Math.round(qRevBase * 0.88),
      revYoY: Number((spec.prevQtrRevYoY - 3.1).toFixed(1)),
      opmPct: Number((spec.opMarginPct - (spec.opMarginExpansionBps / 100) * 0.9).toFixed(1)),
    },
    {
      quarter: 'Q4 FY26',
      epsInr: Number((qEpsBase * 0.91).toFixed(2)),
      epsYoY: Number((spec.prevQtrEpsYoY - 1.8).toFixed(1)),
      revenueCr: Math.round(qRevBase * 0.94),
      revYoY: Number((spec.prevQtrRevYoY - 1.2).toFixed(1)),
      opmPct: Number((spec.opMarginPct - (spec.opMarginExpansionBps / 100) * 0.55).toFixed(1)),
    },
    {
      quarter: 'Q1 FY27',
      epsInr: Number((qEpsBase * 0.96).toFixed(2)),
      epsYoY: spec.prevQtrEpsYoY,
      revenueCr: Math.round(qRevBase * 0.97),
      revYoY: spec.prevQtrRevYoY,
      opmPct: Number((spec.opMarginPct - (spec.opMarginExpansionBps / 100) * 0.25).toFixed(1)),
    },
    {
      quarter: 'Q2 FY27',
      epsInr: Number((qEpsBase * 1.06).toFixed(2)),
      epsYoY: spec.qtrEpsYoY,
      revenueCr: Math.round(qRevBase * 1.04),
      revYoY: spec.qtrRevYoY,
      opmPct: spec.opMarginPct,
    },
  ];

  const fyYears = ['FY22', 'FY23', 'FY24', 'FY25', 'FY26'];
  const dpsGrowthFactor = Math.max(0.02, spec.dps5YCagrPct / 100);
  const fcfGrowthFactor = Math.max(0.03, spec.fcf5YCagrPct / 100);
  const historicalDps = fyYears.map((year, yi) => {
    const back = 4 - yi;
    const dps =
      spec.annualDpsInr > 0
        ? Number((spec.annualDpsInr / Math.pow(1 + dpsGrowthFactor, back)).toFixed(2))
        : 0;
    const fcfPerShare = Number(
      (spec.fcfPerShareInr / Math.pow(1 + fcfGrowthFactor, back)).toFixed(2)
    );
    return { year, dps, fcfPerShare };
  });

  const sensitivities =
    SECTOR_SENSITIVITIES[spec.sector] ?? SECTOR_SENSITIVITIES['Capital Goods & Defence'];

  return {
    ticker: spec.ticker,
    bseCode: spec.bseCode,
    isin: spec.isin,
    name: spec.name,
    sector: spec.sector,
    industry: spec.industry,
    capBucket: spec.capBucket,
    marketCapCr: spec.marketCapCr,
    beta: spec.beta,
    bars,
    latestClose,
    prevClose,
    dailyChangePct,
    avgDailyTurnoverCr: spec.avgTurnoverCr,
    universe: decodeMembership(flags, spec.capBucket),
    isLiveHydrated: false,
    fundamentals: {
      qtrEpsYoY: spec.qtrEpsYoY,
      prevQtrEpsYoY: spec.prevQtrEpsYoY,
      qtrRevYoY: spec.qtrRevYoY,
      prevQtrRevYoY: spec.prevQtrRevYoY,
      opMarginPct: spec.opMarginPct,
      opMarginExpansionBps: spec.opMarginExpansionBps,
      earningsSurprisePct: spec.earningsSurprisePct,
      annualEps3YCagr: spec.annualEps3YCagr,
      roePct: spec.roePct,
      rocePct: spec.rocePct,
      fiiHoldingPct: spec.fiiHoldingPct,
      fiiQoQChangePct: spec.fiiQoQChangePct,
      diiHoldingPct: spec.diiHoldingPct,
      diiQoQChangePct: spec.diiQoQChangePct,
      mfHoldingPct: spec.mfHoldingPct,
      promoterHoldingPct: spec.promoterHoldingPct,
      promoterPledgePct: spec.promoterPledgePct,
      quarterlyHistory,
    },
    dividend: {
      annualDpsInr: spec.annualDpsInr,
      dividendYieldPct: Number(((spec.annualDpsInr / latestClose) * 100).toFixed(2)),
      fcfPerShareInr: spec.fcfPerShareInr,
      fcf5YCagrPct: spec.fcf5YCagrPct,
      epsInr: spec.epsInr,
      dps5YCagrPct: spec.dps5YCagrPct,
      consecutiveYearsPaid: spec.consecutiveYearsPaid,
      netDebtToEbitda: spec.netDebtToEbitda,
      historicalDps,
    },
    sensitivities,
    recentNews: [
      {
        date: '2026-11-19',
        headline: spec.headline,
        source: 'NSE Corporate Filings',
      },
      {
        date: '2026-11-12',
        headline: `Institutional shareholding update: FII ${spec.fiiQoQChangePct >= 0 ? '+' : ''}${spec.fiiQoQChangePct.toFixed(2)}% QoQ, DII ${spec.diiQoQChangePct >= 0 ? '+' : ''}${spec.diiQoQChangePct.toFixed(2)}% QoQ`,
        source: 'BSE XBRL Disclosure',
      },
    ],
  };
});

const CORE_TICKER_SET = new Set(CORE_BUILT_STOCKS.map((s) => s.ticker));
const EXTENDED_BUILT_STOCKS: IndianStock[] = NSE_1100_CATALOG.filter(
  (row) => !CORE_TICKER_SET.has(row[0])
).map(buildExtendedCatalogStock);

export const INDIAN_STOCKS: IndianStock[] = [...CORE_BUILT_STOCKS, ...EXTENDED_BUILT_STOCKS];

export const STOCK_BY_TICKER: Record<string, IndianStock> = Object.fromEntries(
  INDIAN_STOCKS.map((s) => [s.ticker, s])
);

export const ALL_SECTORS: string[] = Array.from(new Set(INDIAN_STOCKS.map((s) => s.sector))).sort();

export function matchesUniverseScope(stock: IndianStock, scope: UniverseScope): boolean {
  if (scope === 'all') return true;
  const u = stock.universe;
  if (!u) return true;
  if (scope === 'nifty500') return u.nifty500;
  if (scope === 'fno') return u.fno;
  if (scope === 'midcap') return u.midcap;
  if (scope === 'smallcap') return u.smallcap;
  return true;
}

export const UNIVERSE_COUNTS = {
  total: INDIAN_STOCKS.length,
  nifty500: INDIAN_STOCKS.filter((s) => s.universe?.nifty500).length,
  fno: INDIAN_STOCKS.filter((s) => s.universe?.fno).length,
  midcap: INDIAN_STOCKS.filter((s) => s.universe?.midcap).length,
  smallcap: INDIAN_STOCKS.filter((s) => s.universe?.smallcap).length,
  microcap: INDIAN_STOCKS.filter((s) => s.universe?.microcap).length,
};

export const DEFAULT_WATCHLIST = [
  'TRENT',
  'HAL',
  'DIXON',
  'PERSISTENT',
  'BEL',
  'BSE',
  'HDFCBANK',
  'RELIANCE',
  'M&M',
  'COALINDIA',
];

export const DEFAULT_PORTFOLIO_HOLDINGS = [
  { id: 'hold_HDFCBANK', ticker: 'HDFCBANK', shares: 160, avgCostInr: 865, targetWeightPct: 16 },
  { id: 'hold_RELIANCE', ticker: 'RELIANCE', shares: 185, avgCostInr: 1295, targetWeightPct: 14 },
  { id: 'hold_HAL', ticker: 'HAL', shares: 54, avgCostInr: 4120, targetWeightPct: 12 },
  { id: 'hold_TRENT', ticker: 'TRENT', shares: 60, avgCostInr: 2980, targetWeightPct: 11 },
  { id: 'hold_PERSISTENT', ticker: 'PERSISTENT', shares: 34, avgCostInr: 4940, targetWeightPct: 11 },
  { id: 'hold_M_M', ticker: 'M&M', shares: 60, avgCostInr: 2920, targetWeightPct: 10 },
  { id: 'hold_SUNPHARMA', ticker: 'SUNPHARMA', shares: 92, avgCostInr: 1680, targetWeightPct: 10 },
  { id: 'hold_ITC', ticker: 'ITC', shares: 310, avgCostInr: 425, targetWeightPct: 8 },
  { id: 'hold_COALINDIA', ticker: 'COALINDIA', shares: 290, avgCostInr: 398, targetWeightPct: 8 },
];

export interface LiveQuotePayload {
  symbol: string;
  yahooSymbol: string;
  bars: OHLCVBar[];
  latestClose: number;
  prevClose: number;
  dailyChangePct: number;
  avgDailyTurnoverCr: number;
}

export interface LiveUniverseResponse {
  fetchedAtIst: string;
  source: string;
  liveCount: number;
  benchmarks: Record<'NIFTY50' | 'NIFTY500' | 'SENSEX', LiveQuotePayload | null>;
  stocks: Record<string, LiveQuotePayload>;
}

export interface CompactLiveQuote {
  s: string;
  lc: number;
  pc: number;
  dc: number;
  tc: number;
  d: string[];
  o: number[];
  h: number[];
  l: number[];
  c: number[];
  v: number[];
}

export interface ExtendedLiveUniverseChunkResponse {
  totalExtended: number;
  hydratedCount: number;
  isHydrating: boolean;
  completed: boolean;
  fetchedAtIst: string;
  offset: number;
  limit: number;
  nextOffset: number | null;
  stocks: Record<string, CompactLiveQuote>;
}

/**
 * Hydrates BENCHMARKS and core INDIAN_STOCKS / STOCK_BY_TICKER in place with live
 * NSE & BSE daily OHLCV candles and real market prices from /api/market/live-universe.
 */
export function applyLiveMarketData(payload: LiveUniverseResponse): number {
  let updated = 0;

  (['NIFTY50', 'NIFTY500', 'SENSEX'] as const).forEach((bmId) => {
    const liveBm = payload.benchmarks?.[bmId];
    if (liveBm && liveBm.bars.length >= 20) {
      BENCHMARKS[bmId].bars = liveBm.bars;
      BENCHMARKS[bmId].latestClose = liveBm.latestClose;
      BENCHMARKS[bmId].changePct = liveBm.dailyChangePct;
    }
  });

  for (const stock of INDIAN_STOCKS) {
    const live = payload.stocks?.[stock.ticker];
    if (!live || !Array.isArray(live.bars) || live.bars.length < 20) continue;

    stock.bars = live.bars;
    stock.latestClose = live.latestClose;
    stock.prevClose = live.prevClose;
    stock.dailyChangePct = live.dailyChangePct;
    stock.isLiveHydrated = true;
    if (live.avgDailyTurnoverCr > 0) {
      stock.avgDailyTurnoverCr = live.avgDailyTurnoverCr;
    }
    if (stock.latestClose > 0 && stock.dividend.annualDpsInr >= 0) {
      stock.dividend.dividendYieldPct = Number(
        ((stock.dividend.annualDpsInr / stock.latestClose) * 100).toFixed(2)
      );
    }
    updated++;
  }

  return updated;
}

/**
 * Hydrates extended 1,000+ NSE stocks in place from compact parallel-array chunks
 * delivered by /api/market/live-universe-extended.
 */
export function applyExtendedLiveMarketData(payload: ExtendedLiveUniverseChunkResponse): number {
  if (!payload?.stocks) return 0;
  let updated = 0;
  for (const [ticker, q] of Object.entries(payload.stocks)) {
    const stock = STOCK_BY_TICKER[ticker];
    if (!stock || !q || !Array.isArray(q.d) || q.d.length < 20) continue;

    const len = q.d.length;
    const bars: OHLCVBar[] = new Array(len);
    for (let i = 0; i < len; i++) {
      bars[i] = {
        date: q.d[i],
        open: q.o[i],
        high: q.h[i],
        low: q.l[i],
        close: q.c[i],
        volume: q.v[i],
      };
    }

    stock.bars = bars;
    stock.latestClose = q.lc;
    stock.prevClose = q.pc;
    stock.dailyChangePct = q.dc;
    stock.isLiveHydrated = true;
    if (q.tc > 0) {
      stock.avgDailyTurnoverCr = q.tc;
    }
    if (stock.latestClose > 0 && stock.dividend.annualDpsInr >= 0) {
      stock.dividend.dividendYieldPct = Number(
        ((stock.dividend.annualDpsInr / stock.latestClose) * 100).toFixed(2)
      );
    }
    updated++;
  }
  return updated;
}


