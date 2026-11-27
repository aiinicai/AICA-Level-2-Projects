import { BENCHMARKS } from '../data/indianMarketData';
import {
  computeSmaSeries,
  DEFAULT_TREND_THRESHOLDS,
  runMinerviniAnalysis,
} from './analyticsEngine';
import {
  computeAdxSeries,
  computeMacdSeries,
  computeRsiSeries,
} from './tradeRadarEngine';
import { IndianStock, OHLCVBar } from '../types/market';

export type RotationQuadrant = 'Leading' | 'Improving' | 'Weakening' | 'Lagging';

export type TrendRegimeLabel =
  | 'Strong Uptrend'
  | 'Trending Bullish'
  | 'Emerging / Base'
  | 'Neutral / Weakening'
  | 'Downtrend';

export type ScoringPresetId = 'balanced' | 'momentum_rs' | 'breadth_breakout' | 'trend_following';

export interface ScoringWeights {
  id: ScoringPresetId;
  label: string;
  description: string;
  trend: number;
  rs: number;
  momentum: number;
  breadth: number;
}

export const SCORING_PRESETS: Record<ScoringPresetId, ScoringWeights> = {
  balanced: {
    id: 'balanced',
    label: 'Balanced Institutional',
    description: 'Equal 25% weighting across SMA structure, RS vs NIFTY 500, RSI/MACD/ADX, and Breadth/Volume.',
    trend: 0.25,
    rs: 0.25,
    momentum: 0.25,
    breadth: 0.25,
  },
  momentum_rs: {
    id: 'momentum_rs',
    label: 'RS & Momentum Leader',
    description: 'Prioritizes benchmark outperformance (40% RS) and directional velocity (25% RSI/MACD/ADX).',
    trend: 0.20,
    rs: 0.40,
    momentum: 0.25,
    breadth: 0.15,
  },
  breadth_breakout: {
    id: 'breadth_breakout',
    label: 'Breadth & Breakout Thrust',
    description: 'Focuses on broad constituent participation, 52W high proximity, and volume accumulation (40%).',
    trend: 0.25,
    rs: 0.20,
    momentum: 0.15,
    breadth: 0.40,
  },
  trend_following: {
    id: 'trend_following',
    label: 'Pure Trend (SMA / ADX)',
    description: 'Weights clean 21/50/150/200 SMA alignment (40%) and ADX/MACD directional confirmation (30%).',
    trend: 0.40,
    rs: 0.20,
    momentum: 0.30,
    breadth: 0.10,
  },
};

export interface ConstituentTechSummary {
  ticker: string;
  name: string;
  sector: string;
  industry: string;
  latestClose: number;
  dailyChangePct: number;
  return1MPct: number;
  return3MPct: number;
  rsRating: number;
  rsi14: number;
  adx14: number;
  aboveSma50: boolean;
  aboveSma200: boolean;
  smaAlignedCount: number; // out of 4 (21, 50, 150, 200)
  stage2: boolean;
  near52WHigh: boolean;
  vcpDetected: boolean;
  volumeThrust: number;
  stockTechScore: number;
}

export interface TechnicalGroupScore {
  id: string;
  name: string;
  kind: 'sector' | 'subsector';
  parentSector: string;
  stockCount: number;
  totalMarketCapCr: number;

  // Composite Score (0 - 100) & 4 normalized sub-scores (each 0 - 100 before weighting, plus weighted points)
  compositeScore: number;
  regime: TrendRegimeLabel;
  quadrant: RotationQuadrant;

  subScores: {
    trend: number; // 0-100
    rs: number; // 0-100
    momentum: number; // 0-100
    breadth: number; // 0-100
  };
  weightedPoints: {
    trend: number;
    rs: number;
    momentum: number;
    breadth: number;
  };

  // Multi-horizon composite index returns (%)
  return1DPct: number;
  return1WPct: number;
  return1MPct: number;
  return3MPct: number;
  return6MPct: number;
  return1YPct: number;

  // Relative Strength & RRG coordinates (centered at 100)
  rsVsNifty500_1M: number; // excess return % vs NIFTY 500
  rsVsNifty500_3M: number;
  rsRatio: number; // RRG X-axis (~90 to 112, 100 = benchmark)
  rsMomentum: number; // RRG Y-axis (~90 to 112, 100 = flat)
  avgRsRating: number; // 1-99 IBD RS avg

  // Technical indicator readings on composite index
  sma21Above: boolean;
  sma50Above: boolean;
  sma150Above: boolean;
  sma200Above: boolean;
  sma200Rising: boolean;
  smaStackScore: number; // 0 to 4
  smaStackLabel: string;
  distFrom50SmaPct: number;
  distFrom200SmaPct: number;

  rsi14: number;
  adx14: number;
  plusDi14: number;
  minusDi14: number;
  macdHist: number;
  macdSignalState: 'Bullish Expanding' | 'Bullish' | 'Weakening' | 'Bearish';

  // Breadth & institutional volume
  pctAbove50Sma: number;
  pctAbove200Sma: number;
  pctStage2: number;
  pctNear52WHigh: number;
  vcpCount: number;
  volumeThrustRatio: number;

  // Constituents ranked by technical strength
  constituents: ConstituentTechSummary[];
  topLeader: ConstituentTechSummary;
}

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

function pctChange(bars: OHLCVBar[], lookback: number): number {
  const n = bars.length;
  if (n < 2) return 0;
  const end = bars[n - 1].close;
  const start = bars[Math.max(0, n - 1 - lookback)].close;
  if (start <= 0) return 0;
  return Number((((end - start) / start) * 100).toFixed(2));
}

/**
 * Builds an equal-weight normalized composite OHLCV index from a group of stocks
 * so SMA, RSI, MACD, ADX, and RRG coordinates reflect true group technical structure.
 */
function buildCompositeIndex(stocks: IndianStock[]): OHLCVBar[] {
  if (stocks.length === 0) return [];
  const minLen = Math.min(...stocks.map((s) => s.bars.length));
  if (minLen < 30) return [];

  const aligned = stocks.map((s) => s.bars.slice(-minLen));
  const baseCloses = aligned.map((bars) => (bars[0].close > 0 ? bars[0].close : 1));
  const composite: OHLCVBar[] = [];

  for (let i = 0; i < minLen; i++) {
    let oSum = 0;
    let hSum = 0;
    let lSum = 0;
    let cSum = 0;
    let volRatioSum = 0;

    for (let sIdx = 0; sIdx < aligned.length; sIdx++) {
      const b = aligned[sIdx][i];
      const base = baseCloses[sIdx];
      oSum += (b.open / base) * 100;
      hSum += (b.high / base) * 100;
      lSum += (b.low / base) * 100;
      cSum += (b.close / base) * 100;
      volRatioSum += b.volume;
    }

    const k = aligned.length;
    const open = Number((oSum / k).toFixed(3));
    const close = Number((cSum / k).toFixed(3));
    const high = Number(Math.max(open, close, hSum / k).toFixed(3));
    const low = Number(Math.min(open, close, lSum / k).toFixed(3));

    composite.push({
      date: aligned[0][i].date,
      open,
      high,
      low,
      close,
      volume: Math.round(volRatioSum / k),
    });
  }

  return composite;
}

function classifyRegime(score: number): TrendRegimeLabel {
  if (score >= 78) return 'Strong Uptrend';
  if (score >= 64) return 'Trending Bullish';
  if (score >= 48) return 'Emerging / Base';
  if (score >= 35) return 'Neutral / Weakening';
  return 'Downtrend';
}

function classifyQuadrant(rsRatio: number, rsMomentum: number): RotationQuadrant {
  if (rsRatio >= 100 && rsMomentum >= 100) return 'Leading';
  if (rsRatio < 100 && rsMomentum >= 100) return 'Improving';
  if (rsRatio >= 100 && rsMomentum < 100) return 'Weakening';
  return 'Lagging';
}

function evaluateGroup(
  id: string,
  name: string,
  kind: 'sector' | 'subsector',
  parentSector: string,
  groupStocks: IndianStock[],
  constituentMap: Map<string, ConstituentTechSummary>,
  weights: ScoringWeights
): TechnicalGroupScore {
  const compositeBars = buildCompositeIndex(groupStocks);
  const closes = compositeBars.map((b) => b.close);
  const n = closes.length;
  const lastClose = closes[n - 1] ?? 100;

  // Moving averages on composite index
  const sma21Arr = computeSmaSeries(closes, 21);
  const sma50Arr = computeSmaSeries(closes, 50);
  const sma150Arr = computeSmaSeries(closes, 150);
  const sma200Arr = computeSmaSeries(closes, 200);

  const sma21 = sma21Arr[n - 1];
  const sma50 = sma50Arr[n - 1];
  const sma150 = sma150Arr[n - 1];
  const sma200 = sma200Arr[n - 1];
  const sma200Prev = sma200Arr[Math.max(0, n - 22)];

  const sma21Above = Number.isFinite(sma21) && lastClose > sma21;
  const sma50Above = Number.isFinite(sma50) && lastClose > sma50;
  const sma150Above = Number.isFinite(sma150) && lastClose > sma150;
  const sma200Above = Number.isFinite(sma200) && lastClose > sma200;
  const sma200Rising = Number.isFinite(sma200) && Number.isFinite(sma200Prev) && sma200 > sma200Prev;
  const smaStackScore =
    (sma21Above ? 1 : 0) + (sma50Above ? 1 : 0) + (sma150Above ? 1 : 0) + (sma200Above ? 1 : 0);

  const bullRibbon =
    sma21Above &&
    sma50Above &&
    sma150Above &&
    sma200Above &&
    sma21 > sma50 &&
    sma50 > sma150 &&
    sma150 > sma200;

  const smaStackLabel = bullRibbon
    ? '4/4 Aligned'
    : smaStackScore === 4
    ? '4/4 Above'
    : smaStackScore >= 2
    ? `${smaStackScore}/4 Mixed`
    : `${smaStackScore}/4 Below`;

  const distFrom50SmaPct =
    Number.isFinite(sma50) && sma50 > 0 ? Number((((lastClose - sma50) / sma50) * 100).toFixed(2)) : 0;
  const distFrom200SmaPct =
    Number.isFinite(sma200) && sma200 > 0 ? Number((((lastClose - sma200) / sma200) * 100).toFixed(2)) : 0;

  // RSI, MACD, ADX on composite index
  const rsiArr = computeRsiSeries(closes, 14);
  const rsi14 = Number.isFinite(rsiArr[n - 1]) ? Number(rsiArr[n - 1].toFixed(1)) : 50;

  const macdObj = computeMacdSeries(closes, 12, 26, 9);
  const macdVal = Number.isFinite(macdObj.macd[n - 1]) ? macdObj.macd[n - 1] : 0;
  const macdSig = Number.isFinite(macdObj.signal[n - 1]) ? macdObj.signal[n - 1] : 0;
  const macdHist = Number.isFinite(macdObj.hist[n - 1]) ? Number(macdObj.hist[n - 1].toFixed(3)) : 0;
  const macdHistPrev = Number.isFinite(macdObj.hist[n - 4]) ? macdObj.hist[n - 4] : macdHist;

  let macdSignalState: TechnicalGroupScore['macdSignalState'] = 'Weakening';
  if (macdVal > macdSig && macdHist > 0 && macdHist >= macdHistPrev) {
    macdSignalState = 'Bullish Expanding';
  } else if (macdVal > macdSig) {
    macdSignalState = 'Bullish';
  } else if (macdVal < macdSig && macdHist < 0) {
    macdSignalState = 'Bearish';
  }

  const adxObj = computeAdxSeries(compositeBars, 14);
  const adx14 = Number.isFinite(adxObj.adx[n - 1]) ? Number(adxObj.adx[n - 1].toFixed(1)) : 18;
  const plusDi14 = Number.isFinite(adxObj.plusDi[n - 1]) ? Number(adxObj.plusDi[n - 1].toFixed(1)) : 20;
  const minusDi14 = Number.isFinite(adxObj.minusDi[n - 1]) ? Number(adxObj.minusDi[n - 1].toFixed(1)) : 20;

  // Returns vs NIFTY 500
  const bmBars = BENCHMARKS.NIFTY500.bars;
  const return1DPct = pctChange(compositeBars, 1);
  const return1WPct = pctChange(compositeBars, 5);
  const return1MPct = pctChange(compositeBars, 21);
  const return3MPct = pctChange(compositeBars, 63);
  const return6MPct = pctChange(compositeBars, 126);
  const return1YPct = pctChange(compositeBars, 252);

  const bm1M = pctChange(bmBars, 21);
  const bm3M = pctChange(bmBars, 63);
  const rsVsNifty500_1M = Number((return1MPct - bm1M).toFixed(2));
  const rsVsNifty500_3M = Number((return3MPct - bm3M).toFixed(2));

  // RRG Coordinates (RS-Ratio & RS-Momentum centered around 100)
  const bmByDate = new Map(bmBars.map((b) => [b.date, b.close]));
  const rawRs: number[] = [];
  let lastBm = bmBars[bmBars.length - 1]?.close || 1;
  for (const b of compositeBars) {
    const bm = bmByDate.get(b.date) ?? lastBm;
    if (bm > 0) lastBm = bm;
    rawRs.push(b.close / lastBm);
  }
  const rsSma10 = computeSmaSeries(rawRs, 10);
  const rsSma63 = computeSmaSeries(rawRs, 63);
  const rsRatioSeries = rawRs.map((_, idx) =>
    Number.isFinite(rsSma10[idx]) && Number.isFinite(rsSma63[idx]) && rsSma63[idx] > 0
      ? (rsSma10[idx] / rsSma63[idx]) * 100
      : 100
  );
  const rsRatio = Number(clamp(rsRatioSeries[n - 1] ?? 100, 86, 116).toFixed(2));
  const rsRatioPrev = rsRatioSeries[Math.max(0, n - 15)] ?? 100;
  const rsMomentum = Number(
    clamp(100 + ((rsRatio - rsRatioPrev) / Math.max(1, rsRatioPrev)) * 100 * 1.4, 86, 116).toFixed(2)
  );
  const quadrant = classifyQuadrant(rsRatio, rsMomentum);

  // Constituents & Breadth
  const constituents = groupStocks
    .map((s) => constituentMap.get(s.ticker)!)
    .filter(Boolean)
    .sort((a, b) => b.stockTechScore - a.stockTechScore);

  const count = Math.max(1, constituents.length);
  const pctAbove50Sma = Number(
    ((constituents.filter((c) => c.aboveSma50).length / count) * 100).toFixed(0)
  );
  const pctAbove200Sma = Number(
    ((constituents.filter((c) => c.aboveSma200).length / count) * 100).toFixed(0)
  );
  const pctStage2 = Number(
    ((constituents.filter((c) => c.stage2).length / count) * 100).toFixed(0)
  );
  const pctNear52WHigh = Number(
    ((constituents.filter((c) => c.near52WHigh).length / count) * 100).toFixed(0)
  );
  const vcpCount = constituents.filter((c) => c.vcpDetected).length;
  const avgRsRating = Number(
    (constituents.reduce((s, c) => s + c.rsRating, 0) / count).toFixed(0)
  );
  const volumeThrustRatio = Number(
    (constituents.reduce((s, c) => s + c.volumeThrust, 0) / count).toFixed(2)
  );
  const totalMarketCapCr = Math.round(groupStocks.reduce((s, st) => s + st.marketCapCr, 0));

  // --- 4 TECHNICAL PILLAR SUB-SCORES (each 0 to 100) ---

  // Pillar 1: Trend Structure & SMA Alignment (0-100)
  let trendScore = 0;
  if (sma21Above) trendScore += 18;
  if (sma50Above) trendScore += 22;
  if (sma150Above) trendScore += 18;
  if (sma200Above) trendScore += 18;
  if (sma200Rising) trendScore += 12;
  if (bullRibbon) trendScore += 12;
  trendScore = clamp(Math.round(trendScore), 0, 100);

  // Pillar 2: Relative Strength vs NIFTY 500 (0-100)
  const rsRatingComponent = clamp(avgRsRating, 0, 99) * 0.52;
  const rsRatioComponent = clamp((rsRatio - 92) * 3.0, 0, 30);
  const rsMomComponent = clamp((rsMomentum - 94) * 1.5, 0, 18);
  const rsScore = clamp(Math.round(rsRatingComponent + rsRatioComponent + rsMomComponent), 0, 100);

  // Pillar 3: Momentum & Directional Strength — RSI, MACD, ADX (0-100)
  let rsiPts = 12;
  if (rsi14 >= 55 && rsi14 <= 74) rsiPts = 36;
  else if (rsi14 > 74) rsiPts = 28; // slightly extended
  else if (rsi14 >= 48) rsiPts = 22;
  else if (rsi14 < 40) rsiPts = 6;

  let macdPts = 14;
  if (macdSignalState === 'Bullish Expanding') macdPts = 32;
  else if (macdSignalState === 'Bullish') macdPts = 25;
  else if (macdSignalState === 'Bearish') macdPts = 5;

  let adxPts = 12;
  if (plusDi14 > minusDi14) {
    if (adx14 >= 25) adxPts = 32;
    else if (adx14 >= 18) adxPts = 25;
    else adxPts = 19;
  } else {
    adxPts = adx14 >= 25 ? 4 : 10;
  }
  const momentumScore = clamp(Math.round(rsiPts + macdPts + adxPts), 0, 100);

  // Pillar 4: Breadth, 52W High Proximity & Institutional Volume Thrust (0-100)
  const breadth50Pts = (pctAbove50Sma / 100) * 28;
  const stage2Pts = (pctStage2 / 100) * 28;
  const nearHighPts = (pctNear52WHigh / 100) * 24;
  const volPts = clamp((volumeThrustRatio - 0.65) * 24, 0, 20);
  const breadthScore = clamp(Math.round(breadth50Pts + stage2Pts + nearHighPts + volPts), 0, 100);

  // Weighted Composite Score (0-100)
  const wTrend = Number((trendScore * weights.trend).toFixed(1));
  const wRs = Number((rsScore * weights.rs).toFixed(1));
  const wMomentum = Number((momentumScore * weights.momentum).toFixed(1));
  const wBreadth = Number((breadthScore * weights.breadth).toFixed(1));
  const compositeScore = clamp(Math.round(wTrend + wRs + wMomentum + wBreadth), 0, 100);

  return {
    id,
    name,
    kind,
    parentSector,
    stockCount: groupStocks.length,
    totalMarketCapCr,
    compositeScore,
    regime: classifyRegime(compositeScore),
    quadrant,
    subScores: {
      trend: trendScore,
      rs: rsScore,
      momentum: momentumScore,
      breadth: breadthScore,
    },
    weightedPoints: {
      trend: wTrend,
      rs: wRs,
      momentum: wMomentum,
      breadth: wBreadth,
    },
    return1DPct,
    return1WPct,
    return1MPct,
    return3MPct,
    return6MPct,
    return1YPct,
    rsVsNifty500_1M,
    rsVsNifty500_3M,
    rsRatio,
    rsMomentum,
    avgRsRating,
    sma21Above,
    sma50Above,
    sma150Above,
    sma200Above,
    sma200Rising,
    smaStackScore,
    smaStackLabel,
    distFrom50SmaPct,
    distFrom200SmaPct,
    rsi14,
    adx14,
    plusDi14,
    minusDi14,
    macdHist,
    macdSignalState,
    pctAbove50Sma,
    pctAbove200Sma,
    pctStage2,
    pctNear52WHigh,
    vcpCount,
    volumeThrustRatio,
    constituents,
    topLeader: constituents[0],
  };
}

export interface TrendingSectorsReport {
  sectors: TechnicalGroupScore[];
  subsectors: TechnicalGroupScore[];
  universeBreadth: {
    totalStocks: number;
    pctAbove50Sma: number;
    pctAbove200Sma: number;
    pctStage2: number;
    avgRsRating: number;
    leadingSectorsCount: number;
    improvingSectorsCount: number;
    leadingSubsectorsCount: number;
    improvingSubsectorsCount: number;
  };
}

/**
 * Computes technical trend scores for every NSE sector and every NSE subsector (industry).
 */
export function computeTrendingSectorsAndSubsectors(
  stocks: IndianStock[],
  presetId: ScoringPresetId = 'balanced'
): TrendingSectorsReport {
  const weights = SCORING_PRESETS[presetId] ?? SCORING_PRESETS.balanced;
  const minerviniRows = runMinerviniAnalysis(stocks, DEFAULT_TREND_THRESHOLDS);
  const minerviniByTicker = new Map(minerviniRows.map((m) => [m.stock.ticker, m]));

  // Precompute constituent technical snapshots once
  const constituentMap = new Map<string, ConstituentTechSummary>();
  for (const s of stocks) {
    const bars = s.bars;
    const closes = bars.map((b) => b.close);
    const n = closes.length;
    const last = closes[n - 1] ?? s.latestClose;
    const sma21 = computeSmaSeries(closes, 21)[n - 1];
    const sma50 = computeSmaSeries(closes, 50)[n - 1];
    const sma150 = computeSmaSeries(closes, 150)[n - 1];
    const sma200 = computeSmaSeries(closes, 200)[n - 1];
    const rsi = computeRsiSeries(closes, 14)[n - 1];
    const adxObj = computeAdxSeries(bars, 14);
    const adx = adxObj.adx[n - 1];
    const pDi = adxObj.plusDi[n - 1];
    const mDi = adxObj.minusDi[n - 1];

    const smaAlignedCount =
      (last > sma21 ? 1 : 0) +
      (last > sma50 ? 1 : 0) +
      (last > sma150 ? 1 : 0) +
      (last > sma200 ? 1 : 0);

    // 52W high proximity
    const last252 = bars.slice(-252);
    const high52w = Math.max(...last252.map((b) => b.high));
    const near52WHigh = high52w > 0 && last >= high52w * 0.9;

    // 5-day avg volume vs 50-day avg volume
    const vol5 =
      bars.slice(-5).reduce((sum, b) => sum + b.volume, 0) / Math.max(1, Math.min(5, n));
    const vol50 =
      bars.slice(-50).reduce((sum, b) => sum + b.volume, 0) / Math.max(1, Math.min(50, n));
    const volumeThrust = vol50 > 0 ? Number((vol5 / vol50).toFixed(2)) : 1.0;

    const mRow = minerviniByTicker.get(s.ticker);
    const rsRating = mRow?.rsRating ?? 50;
    const stage2 = mRow?.stage === 2 || Boolean(mRow?.allPassed);
    const vcpDetected = Boolean(mRow?.vcp?.detected);

    const rsiVal = Number.isFinite(rsi) ? Number(rsi.toFixed(1)) : 50;
    const adxVal = Number.isFinite(adx) ? Number(adx.toFixed(1)) : 18;
    const stockTechScore = clamp(
      Math.round(
        smaAlignedCount * 8 +
          rsRating * 0.35 +
          (rsiVal >= 52 && rsiVal <= 75 ? 16 : rsiVal > 75 ? 11 : 6) +
          (pDi > mDi && adxVal >= 20 ? 12 : pDi > mDi ? 7 : 2) +
          (stage2 ? 8 : 0) +
          (near52WHigh ? 5 : 0)
      ),
      0,
      100
    );

    constituentMap.set(s.ticker, {
      ticker: s.ticker,
      name: s.name,
      sector: s.sector,
      industry: s.industry,
      latestClose: s.latestClose,
      dailyChangePct: s.dailyChangePct,
      return1MPct: pctChange(bars, 21),
      return3MPct: pctChange(bars, 63),
      rsRating,
      rsi14: rsiVal,
      adx14: adxVal,
      aboveSma50: Number.isFinite(sma50) && last > sma50,
      aboveSma200: Number.isFinite(sma200) && last > sma200,
      smaAlignedCount,
      stage2,
      near52WHigh,
      vcpDetected,
      volumeThrust,
      stockTechScore,
    });
  }

  // Group by Sector
  const sectorMap = new Map<string, IndianStock[]>();
  const subsectorMap = new Map<string, { sector: string; industry: string; stocks: IndianStock[] }>();

  for (const s of stocks) {
    const secList = sectorMap.get(s.sector) ?? [];
    secList.push(s);
    sectorMap.set(s.sector, secList);

    const subKey = `${s.sector}::${s.industry}`;
    const existingSub = subsectorMap.get(subKey);
    if (existingSub) {
      existingSub.stocks.push(s);
    } else {
      subsectorMap.set(subKey, { sector: s.sector, industry: s.industry, stocks: [s] });
    }
  }

  const sectors: TechnicalGroupScore[] = Array.from(sectorMap.entries())
    .map(([sectorName, list]) =>
      evaluateGroup(
        `sector:${sectorName}`,
        sectorName,
        'sector',
        sectorName,
        list,
        constituentMap,
        weights
      )
    )
    .sort((a, b) => b.compositeScore - a.compositeScore || b.rsRatio - a.rsRatio);

  const subsectors: TechnicalGroupScore[] = Array.from(subsectorMap.entries())
    .map(([subKey, entry]) =>
      evaluateGroup(
        `subsector:${subKey}`,
        entry.industry,
        'subsector',
        entry.sector,
        entry.stocks,
        constituentMap,
        weights
      )
    )
    .sort((a, b) => b.compositeScore - a.compositeScore || b.rsRatio - a.rsRatio);

  const allConstituents = Array.from(constituentMap.values());
  const total = Math.max(1, allConstituents.length);

  return {
    sectors,
    subsectors,
    universeBreadth: {
      totalStocks: allConstituents.length,
      pctAbove50Sma: Math.round(
        (allConstituents.filter((c) => c.aboveSma50).length / total) * 100
      ),
      pctAbove200Sma: Math.round(
        (allConstituents.filter((c) => c.aboveSma200).length / total) * 100
      ),
      pctStage2: Math.round((allConstituents.filter((c) => c.stage2).length / total) * 100),
      avgRsRating: Math.round(
        allConstituents.reduce((s, c) => s + c.rsRating, 0) / total
      ),
      leadingSectorsCount: sectors.filter((s) => s.quadrant === 'Leading').length,
      improvingSectorsCount: sectors.filter((s) => s.quadrant === 'Improving').length,
      leadingSubsectorsCount: subsectors.filter((s) => s.quadrant === 'Leading').length,
      improvingSubsectorsCount: subsectors.filter((s) => s.quadrant === 'Improving').length,
    },
  };
}

let cachedScorecardSig = '';
let cachedScorecardResult: TrendingSectorsReport | null = null;

const YAHOO_TO_NSE_SECTOR_MAP: Record<string, string> = {
  technology: 'Information Technology',
  'information technology': 'Information Technology',
  'financial services': 'Banking & Financial Services',
  financials: 'Banking & Financial Services',
  healthcare: 'Pharma & Healthcare',
  'consumer defensive': 'FMCG',
  'consumer staples': 'FMCG',
  'consumer cyclical': 'Consumer & Retail',
  'consumer discretionary': 'Consumer & Retail',
  'basic materials': 'Chemicals & Materials',
  materials: 'Chemicals & Materials',
  energy: 'Energy & Power',
  utilities: 'Energy & Power',
  industrials: 'Capital Goods & Defence',
  'real estate': 'Real Estate & Infra',
  'communication services': 'Telecom & Digital',
  telecommunication: 'Telecom & Digital',
  automobiles: 'Automobiles & EV',
};

export interface StockSectorScorecardLookup {
  sectorName: string;
  sectorScore: number;
  sectorRank: number;
  sectorTotal: number;
  sectorRegime: TrendRegimeLabel;
  sectorQuadrant: RotationQuadrant;
  sectorRsRatio: number;
  sectorRsMomentum: number;
  sectorPctAbove50Sma: number;
  subsectorName: string | null;
  subsectorScore: number | null;
  subsectorRank: number | null;
  subsectorTotal: number | null;
  subsectorQuadrant: RotationQuadrant | null;
  subsectorRsRatio: number | null;
  subsectorRsMomentum: number | null;
}

export function resolveStockSectorContext(
  stocks: IndianStock[],
  sectorName: string,
  industryName?: string | null,
  marketVersion = 0
): StockSectorScorecardLookup | null {
  if (!stocks || stocks.length === 0) return null;

  const lastStock = stocks[stocks.length - 1];
  const sig = `${marketVersion}:${stocks.length}:${stocks[0]?.latestClose ?? 0}:${lastStock?.latestClose ?? 0}`;
  if (!cachedScorecardResult || cachedScorecardSig !== sig) {
    cachedScorecardResult = computeTrendingSectorsAndSubsectors(stocks, 'balanced');
    cachedScorecardSig = sig;
  }

  const { sectors, subsectors } = cachedScorecardResult;
  if (sectors.length === 0) return null;

  const norm = (v?: string | null) => (v || '').trim().toLowerCase();
  const rawSec = norm(sectorName);
  const rawInd = norm(industryName);
  const mappedSec = norm(YAHOO_TO_NSE_SECTOR_MAP[rawSec] || '');

  let secIdx = sectors.findIndex((s) => norm(s.name) === rawSec);
  if (secIdx < 0 && mappedSec) {
    secIdx = sectors.findIndex((s) => norm(s.name) === mappedSec);
  }
  if (secIdx < 0 && rawSec) {
    secIdx = sectors.findIndex(
      (s) => norm(s.name).includes(rawSec) || rawSec.includes(norm(s.name))
    );
  }
  // Try inferring parent sector from matched subsector if Yahoo sector was generic ("NSE Equity")
  let subIdx = -1;
  if (rawInd) {
    subIdx = subsectors.findIndex(
      (sub) =>
        norm(sub.name) === rawInd && (secIdx < 0 || norm(sub.parentSector) === norm(sectors[secIdx].name))
    );
    if (subIdx < 0) {
      subIdx = subsectors.findIndex(
        (sub) =>
          (norm(sub.name).includes(rawInd) || rawInd.includes(norm(sub.name))) &&
          (secIdx < 0 || norm(sub.parentSector) === norm(sectors[secIdx].name))
      );
    }
    if (secIdx < 0 && subIdx >= 0) {
      secIdx = sectors.findIndex((s) => norm(s.name) === norm(subsectors[subIdx].parentSector));
    }
  }

  if (secIdx < 0) return null;

  const sec = sectors[secIdx];
  const sub = subIdx >= 0 ? subsectors[subIdx] : null;

  return {
    sectorName: sec.name,
    sectorScore: sec.compositeScore,
    sectorRank: secIdx + 1,
    sectorTotal: sectors.length,
    sectorRegime: sec.regime,
    sectorQuadrant: sec.quadrant,
    sectorRsRatio: sec.rsRatio,
    sectorRsMomentum: sec.rsMomentum,
    sectorPctAbove50Sma: sec.pctAbove50Sma,
    subsectorName: sub ? sub.name : null,
    subsectorScore: sub ? sub.compositeScore : null,
    subsectorRank: sub ? subIdx + 1 : null,
    subsectorTotal: sub ? subsectors.length : null,
    subsectorQuadrant: sub ? sub.quadrant : null,
    subsectorRsRatio: sub ? sub.rsRatio : null,
    subsectorRsMomentum: sub ? sub.rsMomentum : null,
  };
}

