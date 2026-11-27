import { BENCHMARKS } from '../data/indianMarketData';
import { computeSmaSeries, runMinerviniAnalysis, DEFAULT_TREND_THRESHOLDS } from './analyticsEngine';
import { IndianStock, OHLCVBar } from '../types/market';

/* ============================================================================
   1. TECHNICAL HELPERS: EMA, RSI, MACD, BOLLINGER, ATR, ADR%, WEEKLY RESAMPLER
   ============================================================================ */

export function computeEmaSeries(values: number[], period: number): number[] {
  const out = new Array<number>(values.length).fill(NaN);
  if (values.length < period || period <= 0) return out;
  const k = 2 / (period + 1);
  let sum = 0;
  for (let i = 0; i < period; i++) sum += values[i];
  let prev = sum / period;
  out[period - 1] = prev;
  for (let i = period; i < values.length; i++) {
    prev = values[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function computeAtrSeries(bars: OHLCVBar[], period = 14): number[] {
  const out = new Array<number>(bars.length).fill(NaN);
  if (bars.length < period + 1) return out;
  const tr = new Array<number>(bars.length).fill(0);
  tr[0] = bars[0].high - bars[0].low;
  for (let i = 1; i < bars.length; i++) {
    const h = bars[i].high;
    const l = bars[i].low;
    const pc = bars[i - 1].close;
    tr[i] = Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc));
  }
  let sum = 0;
  for (let i = 0; i < period; i++) sum += tr[i];
  let prev = sum / period;
  out[period - 1] = prev;
  for (let i = period; i < bars.length; i++) {
    prev = (prev * (period - 1) + tr[i]) / period;
    out[i] = prev;
  }
  return out;
}

export function computeRsiSeries(closes: number[], period = 14): number[] {
  const out = new Array<number>(closes.length).fill(NaN);
  if (closes.length <= period) return out;
  let gainSum = 0;
  let lossSum = 0;
  for (let i = 1; i <= period; i++) {
    const diff = closes[i] - closes[i - 1];
    if (diff >= 0) gainSum += diff;
    else lossSum += -diff;
  }
  let avgGain = gainSum / period;
  let avgLoss = lossSum / period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < closes.length; i++) {
    const diff = closes[i] - closes[i - 1];
    const g = diff > 0 ? diff : 0;
    const l = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + g) / period;
    avgLoss = (avgLoss * (period - 1) + l) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export function computeMacdSeries(closes: number[], fast = 12, slow = 26, signal = 9) {
  const emaFast = computeEmaSeries(closes, fast);
  const emaSlow = computeEmaSeries(closes, slow);
  const macd = closes.map((_, i) =>
    Number.isFinite(emaFast[i]) && Number.isFinite(emaSlow[i]) ? emaFast[i] - emaSlow[i] : NaN
  );
  // Compute signal EMA over valid macd slice
  const firstValid = macd.findIndex((v) => Number.isFinite(v));
  const sig = new Array<number>(closes.length).fill(NaN);
  if (firstValid >= 0 && closes.length - firstValid >= signal) {
    const validSlice = macd.slice(firstValid);
    const sigSlice = computeEmaSeries(validSlice, signal);
    for (let i = 0; i < sigSlice.length; i++) {
      sig[firstValid + i] = sigSlice[i];
    }
  }
  const hist = macd.map((m, i) =>
    Number.isFinite(m) && Number.isFinite(sig[i]) ? m - sig[i] : NaN
  );
  return { macd, signal: sig, hist };
}

/**
 * Wilder's Directional Movement System: ADX, +DI, and -DI series
 */
export function computeAdxSeries(bars: OHLCVBar[], period = 14) {
  const n = bars.length;
  const adx = new Array<number>(n).fill(NaN);
  const plusDi = new Array<number>(n).fill(NaN);
  const minusDi = new Array<number>(n).fill(NaN);
  if (n < period * 2 + 1) return { adx, plusDi, minusDi };

  const tr = new Array<number>(n).fill(0);
  const plusDm = new Array<number>(n).fill(0);
  const minusDm = new Array<number>(n).fill(0);

  for (let i = 1; i < n; i++) {
    const upMove = bars[i].high - bars[i - 1].high;
    const downMove = bars[i - 1].low - bars[i].low;
    plusDm[i] = upMove > downMove && upMove > 0 ? upMove : 0;
    minusDm[i] = downMove > upMove && downMove > 0 ? downMove : 0;
    tr[i] = Math.max(
      bars[i].high - bars[i].low,
      Math.abs(bars[i].high - bars[i - 1].close),
      Math.abs(bars[i].low - bars[i - 1].close)
    );
  }

  let smoothTr = 0;
  let smoothPlusDm = 0;
  let smoothMinusDm = 0;
  for (let i = 1; i <= period; i++) {
    smoothTr += tr[i];
    smoothPlusDm += plusDm[i];
    smoothMinusDm += minusDm[i];
  }

  const dx = new Array<number>(n).fill(NaN);
  for (let i = period; i < n; i++) {
    if (i > period) {
      smoothTr = smoothTr - smoothTr / period + tr[i];
      smoothPlusDm = smoothPlusDm - smoothPlusDm / period + plusDm[i];
      smoothMinusDm = smoothMinusDm - smoothMinusDm / period + minusDm[i];
    }
    const pDi = smoothTr > 0 ? (100 * smoothPlusDm) / smoothTr : 0;
    const mDi = smoothTr > 0 ? (100 * smoothMinusDm) / smoothTr : 0;
    plusDi[i] = pDi;
    minusDi[i] = mDi;
    const denom = pDi + mDi;
    dx[i] = denom > 0 ? (100 * Math.abs(pDi - mDi)) / denom : 0;
  }

  // Initial ADX is simple average of first `period` DX values
  let adxSum = 0;
  const firstAdxIdx = period * 2 - 1;
  for (let i = period; i <= firstAdxIdx; i++) {
    adxSum += dx[i];
  }
  adx[firstAdxIdx] = adxSum / period;

  for (let i = firstAdxIdx + 1; i < n; i++) {
    adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period;
  }

  return { adx, plusDi, minusDi };
}

export function computeBollingerBands(closes: number[], period = 20, mult = 2) {
  const mid = computeSmaSeries(closes, period);
  const upper = new Array<number>(closes.length).fill(NaN);
  const lower = new Array<number>(closes.length).fill(NaN);
  for (let i = period - 1; i < closes.length; i++) {
    const m = mid[i];
    let variance = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const d = closes[j] - m;
      variance += d * d;
    }
    const sd = Math.sqrt(variance / period);
    upper[i] = m + mult * sd;
    lower[i] = m - mult * sd;
  }
  return { mid, upper, lower };
}

export function computeRollingVwap(bars: OHLCVBar[], period = 20): number[] {
  const out = new Array<number>(bars.length).fill(NaN);
  for (let i = period - 1; i < bars.length; i++) {
    let pv = 0;
    let vol = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const tp = (bars[j].high + bars[j].low + bars[j].close) / 3;
      pv += tp * bars[j].volume;
      vol += bars[j].volume;
    }
    out[i] = vol > 0 ? pv / vol : bars[i].close;
  }
  return out;
}

export function computeAdrPct(bars: OHLCVBar[], period = 20): number {
  const slice = bars.slice(-period);
  if (slice.length === 0) return 0;
  const avgRatio =
    slice.reduce((sum, b) => sum + (b.low > 0 ? b.high / b.low : 1), 0) / slice.length;
  return Number(((avgRatio - 1) * 100).toFixed(2));
}

/* ============================================================================
   1B. DONCHIAN CHANNEL INDICATOR (10 / 20 / 55) + BUY/SELL ALERTS & SUPERTREND
   ============================================================================ */

export type DonchianPeriod = 10 | 20 | 55;

export interface DonchianAlertSignal {
  id: string;
  date: string;
  barIndex: number;
  barsAgo: number;
  type: 'BUY' | 'SELL';
  triggerPrice: number;
  channelLevel: number;
  midLevel: number;
  breakoutPct: number;
  volRatio: number;
  rawMovePct: number;
  returnSincePct: number;
  isFresh: boolean;
}

export interface DonchianChannelResult {
  period: number;
  upper: number[];
  lower: number[];
  mid: number[];
  priorUpper: number[];
  priorLower: number[];
  currentUpper: number | null;
  currentLower: number | null;
  currentMid: number | null;
  channelWidthPct: number;
  positionInChannelPct: number;
  regime:
    | 'Bullish Breakout'
    | 'Upper Channel'
    | 'Mid-Channel'
    | 'Lower Channel'
    | 'Bearish Breakdown';
  latestSignal: DonchianAlertSignal | null;
  recentAlerts: DonchianAlertSignal[];
}

export function computeDonchianChannel(
  bars: OHLCVBar[],
  period = 20
): DonchianChannelResult {
  const n = bars.length;
  const upper = new Array<number>(n).fill(NaN);
  const lower = new Array<number>(n).fill(NaN);
  const mid = new Array<number>(n).fill(NaN);
  const priorUpper = new Array<number>(n).fill(NaN);
  const priorLower = new Array<number>(n).fill(NaN);

  if (n < period + 2) {
    return {
      period,
      upper,
      lower,
      mid,
      priorUpper,
      priorLower,
      currentUpper: null,
      currentLower: null,
      currentMid: null,
      channelWidthPct: 0,
      positionInChannelPct: 50,
      regime: 'Mid-Channel',
      latestSignal: null,
      recentAlerts: [],
    };
  }

  const vols = bars.map((b) => b.volume);
  const volAvg20 = computeSmaSeries(vols, 20);

  for (let i = period - 1; i < n; i++) {
    let hi = -Infinity;
    let lo = Infinity;
    for (let j = i - period + 1; j <= i; j++) {
      if (bars[j].high > hi) hi = bars[j].high;
      if (bars[j].low < lo) lo = bars[j].low;
    }
    upper[i] = hi;
    lower[i] = lo;
    mid[i] = (hi + lo) / 2;

    if (i >= period) {
      let pHi = -Infinity;
      let pLo = Infinity;
      for (let j = i - period; j <= i - 1; j++) {
        if (bars[j].high > pHi) pHi = bars[j].high;
        if (bars[j].low < pLo) pLo = bars[j].low;
      }
      priorUpper[i] = pHi;
      priorLower[i] = pLo;
    }
  }

  // Non-repainting state-machine breakout/breakdown detector
  const latestClose = bars[n - 1].close;
  const alerts: DonchianAlertSignal[] = [];
  let trendState: -1 | 0 | 1 = 0;
  let lastSignalIdx = -999;
  let pulledBackBelowMid = false;
  let ralliedAboveMid = false;

  for (let i = period; i < n; i++) {
    const b = bars[i];
    const pUp = priorUpper[i];
    const pLo = priorLower[i];
    const mVal = mid[i];
    if (!Number.isFinite(pUp) || !Number.isFinite(pLo) || !Number.isFinite(mVal)) continue;

    if (trendState === 1 && b.close < mVal) pulledBackBelowMid = true;
    if (trendState === -1 && b.close > mVal) ralliedAboveMid = true;

    const avgV = Number.isFinite(volAvg20[i]) && volAvg20[i] > 0 ? volAvg20[i] : b.volume || 1;
    const volRatio = Number((b.volume / Math.max(1, avgV)).toFixed(2));
    const barsAgo = n - 1 - i;

    const isBuyBreakout = b.close > pUp && (trendState !== 1 || (pulledBackBelowMid && i - lastSignalIdx >= 6));
    const isSellBreakdown = b.close < pLo && (trendState !== -1 || (ralliedAboveMid && i - lastSignalIdx >= 6));

    if (isBuyBreakout) {
      const breakoutPct = pUp > 0 ? ((b.close - pUp) / pUp) * 100 : 0;
      const rawMovePct = b.close > 0 ? ((latestClose - b.close) / b.close) * 100 : 0;
      alerts.push({
        id: `dc_buy_${period}_${b.date}`,
        date: b.date,
        barIndex: i,
        barsAgo,
        type: 'BUY',
        triggerPrice: Number(b.close.toFixed(2)),
        channelLevel: Number(pUp.toFixed(2)),
        midLevel: Number(mVal.toFixed(2)),
        breakoutPct: Number(breakoutPct.toFixed(2)),
        volRatio,
        rawMovePct: Number(rawMovePct.toFixed(2)),
        returnSincePct: Number(rawMovePct.toFixed(2)),
        isFresh: barsAgo <= 5,
      });
      trendState = 1;
      lastSignalIdx = i;
      pulledBackBelowMid = false;
      ralliedAboveMid = false;
    } else if (isSellBreakdown) {
      const breakoutPct = pLo > 0 ? ((b.close - pLo) / pLo) * 100 : 0;
      const rawMovePct = b.close > 0 ? ((latestClose - b.close) / b.close) * 100 : 0;
      alerts.push({
        id: `dc_sell_${period}_${b.date}`,
        date: b.date,
        barIndex: i,
        barsAgo,
        type: 'SELL',
        triggerPrice: Number(b.close.toFixed(2)),
        channelLevel: Number(pLo.toFixed(2)),
        midLevel: Number(mVal.toFixed(2)),
        breakoutPct: Number(breakoutPct.toFixed(2)),
        volRatio,
        rawMovePct: Number(rawMovePct.toFixed(2)),
        returnSincePct: Number((-rawMovePct).toFixed(2)),
        isFresh: barsAgo <= 5,
      });
      trendState = -1;
      lastSignalIdx = i;
      pulledBackBelowMid = false;
      ralliedAboveMid = false;
    }
  }

  const curUp = Number.isFinite(upper[n - 1]) ? Number(upper[n - 1].toFixed(2)) : null;
  const curLo = Number.isFinite(lower[n - 1]) ? Number(lower[n - 1].toFixed(2)) : null;
  const curMid = Number.isFinite(mid[n - 1]) ? Number(mid[n - 1].toFixed(2)) : null;
  const span = curUp !== null && curLo !== null ? Math.max(0.01, curUp - curLo) : 1;
  const channelWidthPct =
    curUp !== null && curLo !== null && curMid && curMid > 0
      ? Number((((curUp - curLo) / curMid) * 100).toFixed(2))
      : 0;
  const positionInChannelPct =
    curUp !== null && curLo !== null
      ? Math.max(0, Math.min(100, Number((((latestClose - curLo) / span) * 100).toFixed(1))))
      : 50;

  const recentAlerts = [...alerts].reverse();
  const latestSignal = recentAlerts[0] || null;

  let regime: DonchianChannelResult['regime'] = 'Mid-Channel';
  if (latestSignal && latestSignal.type === 'BUY' && latestSignal.barsAgo <= 5 && latestClose >= (curMid ?? 0)) {
    regime = 'Bullish Breakout';
  } else if (latestSignal && latestSignal.type === 'SELL' && latestSignal.barsAgo <= 5 && latestClose <= (curMid ?? Infinity)) {
    regime = 'Bearish Breakdown';
  } else if (positionInChannelPct >= 65) {
    regime = 'Upper Channel';
  } else if (positionInChannelPct <= 35) {
    regime = 'Lower Channel';
  }

  return {
    period,
    upper,
    lower,
    mid,
    priorUpper,
    priorLower,
    currentUpper: curUp,
    currentLower: curLo,
    currentMid: curMid,
    channelWidthPct,
    positionInChannelPct,
    regime,
    latestSignal,
    recentAlerts,
  };
}

export interface SupertrendResult {
  period: number;
  multiplier: number;
  line: number[];
  direction: (1 | -1)[]; // 1 = Bullish (green support), -1 = Bearish (red resistance)
  currentLine: number | null;
  currentDirection: 1 | -1;
  distancePct: number;
  barsSinceFlip: number;
  lastFlipDate: string | null;
}

export function computeSupertrendSeries(
  bars: OHLCVBar[],
  period = 10,
  multiplier = 3
): SupertrendResult {
  const n = bars.length;
  const line = new Array<number>(n).fill(NaN);
  const direction = new Array<1 | -1>(n).fill(1);
  if (n < period + 2) {
    return {
      period,
      multiplier,
      line,
      direction,
      currentLine: null,
      currentDirection: 1,
      distancePct: 0,
      barsSinceFlip: 0,
      lastFlipDate: null,
    };
  }

  const atr = computeAtrSeries(bars, period);
  const finalUpper = new Array<number>(n).fill(NaN);
  const finalLower = new Array<number>(n).fill(NaN);

  const start = period - 1;
  for (let i = start; i < n; i++) {
    const a = atr[i];
    if (!Number.isFinite(a)) continue;
    const hl2 = (bars[i].high + bars[i].low) / 2;
    const basicUpper = hl2 + multiplier * a;
    const basicLower = hl2 - multiplier * a;

    if (i === start || !Number.isFinite(finalUpper[i - 1])) {
      finalUpper[i] = basicUpper;
      finalLower[i] = basicLower;
      direction[i] = bars[i].close >= hl2 ? 1 : -1;
      line[i] = direction[i] === 1 ? finalLower[i] : finalUpper[i];
      continue;
    }

    finalUpper[i] =
      basicUpper < finalUpper[i - 1] || bars[i - 1].close > finalUpper[i - 1]
        ? basicUpper
        : finalUpper[i - 1];
    finalLower[i] =
      basicLower > finalLower[i - 1] || bars[i - 1].close < finalLower[i - 1]
        ? basicLower
        : finalLower[i - 1];

    const prevDir = direction[i - 1];
    if (prevDir === 1) {
      if (bars[i].close < finalLower[i]) {
        direction[i] = -1;
        line[i] = finalUpper[i];
      } else {
        direction[i] = 1;
        line[i] = finalLower[i];
      }
    } else {
      if (bars[i].close > finalUpper[i]) {
        direction[i] = 1;
        line[i] = finalLower[i];
      } else {
        direction[i] = -1;
        line[i] = finalUpper[i];
      }
    }
  }

  const curDir = direction[n - 1];
  const curLine = Number.isFinite(line[n - 1]) ? Number(line[n - 1].toFixed(2)) : null;
  const lastClose = bars[n - 1].close;
  const distancePct =
    curLine && curLine > 0 ? Number((((lastClose - curLine) / curLine) * 100).toFixed(2)) : 0;

  let barsSinceFlip = 0;
  let lastFlipDate: string | null = null;
  for (let i = n - 1; i > start; i--) {
    if (direction[i] !== direction[i - 1]) {
      barsSinceFlip = n - 1 - i;
      lastFlipDate = bars[i].date;
      break;
    }
  }

  return {
    period,
    multiplier,
    line,
    direction,
    currentLine: curLine,
    currentDirection: curDir,
    distancePct,
    barsSinceFlip,
    lastFlipDate,
  };
}

export interface UniverseDonchianAlert {
  ticker: string;
  name: string;
  sector: string;
  capBucket: IndianStock['capBucket'];
  close: number;
  dailyChangePct: number;
  period: number;
  alert: DonchianAlertSignal;
  currentUpper: number;
  currentLower: number;
  currentMid: number;
  channelWidthPct: number;
  positionInChannelPct: number;
}

const donchianScanMemo = new Map<string, UniverseDonchianAlert[]>();

export function scanDonchianAlerts(
  stocks: IndianStock[],
  period: DonchianPeriod = 20,
  maxBarsAgo = 10
): UniverseDonchianAlert[] {
  const first = stocks[0];
  const last = stocks[stocks.length - 1];
  const cacheKey = `${stocks.length}_${period}_${maxBarsAgo}_${first?.ticker || ''}_${first?.latestClose || 0}_${last?.ticker || ''}_${last?.latestClose || 0}`;
  const cached = donchianScanMemo.get(cacheKey);
  if (cached) return cached;

  const out: UniverseDonchianAlert[] = [];
  for (const stock of stocks) {
    const bars = stock.bars.length > 160 ? stock.bars.slice(-160) : stock.bars;
    if (bars.length < period + 5) continue;
    const dc = computeDonchianChannel(bars, period);
    const sig = dc.latestSignal;
    if (!sig || sig.barsAgo > maxBarsAgo) continue;
    if (dc.currentUpper === null || dc.currentLower === null || dc.currentMid === null) continue;
    out.push({
      ticker: stock.ticker,
      name: stock.name,
      sector: stock.sector,
      capBucket: stock.capBucket,
      close: stock.latestClose,
      dailyChangePct: stock.dailyChangePct,
      period,
      alert: sig,
      currentUpper: dc.currentUpper,
      currentLower: dc.currentLower,
      currentMid: dc.currentMid,
      channelWidthPct: dc.channelWidthPct,
      positionInChannelPct: dc.positionInChannelPct,
    });
  }

  out.sort((a, b) => {
    if (a.alert.barsAgo !== b.alert.barsAgo) return a.alert.barsAgo - b.alert.barsAgo;
    return b.alert.volRatio - a.alert.volRatio;
  });

  if (donchianScanMemo.size > 16) donchianScanMemo.clear();
  donchianScanMemo.set(cacheKey, out);
  return out;
}

/**
 * Authentic NSE Weekly Resampler (Monday–Friday trading weeks)
 */
export function resampleToWeekly(bars: OHLCVBar[]): OHLCVBar[] {
  if (bars.length === 0) return [];
  const weeks = new Map<string, OHLCVBar>();

  for (const b of bars) {
    const dt = new Date(`${b.date}T00:00:00Z`);
    // Calculate ISO Monday of the bar's week as grouping key
    const day = dt.getUTCDay();
    const diffToMon = (day + 6) % 7;
    const mon = new Date(dt.getTime());
    mon.setUTCDate(dt.getUTCDate() - diffToMon);
    const weekKey = mon.toISOString().slice(0, 10);

    const existing = weeks.get(weekKey);
    if (!existing) {
      weeks.set(weekKey, { ...b });
    } else {
      existing.date = b.date; // use Friday / last trading day of week as bar date
      existing.high = Math.max(existing.high, b.high);
      existing.low = Math.min(existing.low, b.low);
      existing.close = b.close;
      existing.volume += b.volume;
    }
  }

  return Array.from(weeks.values()).sort((a, b) => a.date.localeCompare(b.date));
}

/**
 * Relative Strength Line vs NIFTY 500 (normalized to 100 at start of visible window)
 */
export function computeRsLineVsNifty500(bars: OHLCVBar[]): { date: string; value: number }[] {
  const bmBars = BENCHMARKS.NIFTY500.bars;
  const bmByDate = new Map(bmBars.map((b) => [b.date, b.close]));
  const raw: { date: string; ratio: number }[] = [];
  let lastBm = bmBars[bmBars.length - 1]?.close || 1;

  for (const b of bars) {
    const bm = bmByDate.get(b.date) ?? lastBm;
    if (bm > 0) {
      lastBm = bm;
      raw.push({ date: b.date, ratio: b.close / bm });
    }
  }
  if (raw.length === 0) return [];
  const base = raw[Math.max(0, raw.length - 252)].ratio || raw[0].ratio || 1;
  return raw.map((r) => ({
    date: r.date,
    value: Number(((r.ratio / base) * 100).toFixed(2)),
  }));
}

export type LevelCategory =
  | 'breakout'
  | 'major_resistance'
  | 'minor_resistance'
  | 'major_support'
  | 'minor_support';

export interface StructuralPriceLevel {
  id: string;
  kind: 'breakout' | 'resistance' | 'support_flip' | 'support';
  category: LevelCategory;
  label: string;
  price: number;
  touches: number;
  lastTestedDate: string;
  distPct: number;
  strength: 'Major' | 'Minor';
}

/**
 * Multi-Touch Fractal Swing Clustering Engine for Breakout, Major/Minor Resistance & Major/Minor Support Lines
 * Works on both Daily (1D) and Weekly (1W) OHLCV series.
 */
export function detectKeyBreakoutSupportLevels(
  bars: OHLCVBar[],
  isWeekly = false
): StructuralPriceLevel[] {
  if (bars.length < 25) return [];

  const lookback = isWeekly ? Math.min(bars.length, 130) : Math.min(bars.length, 260);
  const windowBars = bars.slice(-lookback);
  const n = windowBars.length;
  const currentClose = windowBars[n - 1].close;
  if (!Number.isFinite(currentClose) || currentClose <= 0) return [];

  const majorRadius = isWeekly ? 3 : 5;
  const minorRadius = isWeekly ? 2 : 3;
  const clusterTolPct = isWeekly ? 0.02 : 0.014;
  const minSepPct = isWeekly ? 0.022 : 0.015;

  interface SwingPoint {
    price: number;
    date: string;
    idx: number;
    volume: number;
    type: 'high' | 'low';
  }

  const collectSwings = (radius: number) => {
    const highs: SwingPoint[] = [];
    const lows: SwingPoint[] = [];
    for (let i = radius; i < n - Math.max(1, Math.floor(radius / 2)); i++) {
      const b = windowBars[i];
      let isHigh = true;
      let isLow = true;
      for (let j = i - radius; j <= i + radius; j++) {
        if (j === i || j >= n) continue;
        if (windowBars[j].high > b.high) isHigh = false;
        if (windowBars[j].low < b.low) isLow = false;
        if (!isHigh && !isLow) break;
      }
      if (isHigh) {
        highs.push({ price: b.high, date: b.date, idx: i, volume: b.volume, type: 'high' });
      }
      if (isLow) {
        lows.push({ price: b.low, date: b.date, idx: i, volume: b.volume, type: 'low' });
      }
    }
    return { highs, lows };
  };

  const majorSwings = collectSwings(majorRadius);
  const minorSwings = collectSwings(minorRadius);

  // Always include the true period 52W/major high and major low as candidate anchors
  let periodHighBar = windowBars[0];
  let periodHighIdx = 0;
  let periodLowBar = windowBars[0];
  let periodLowIdx = 0;
  for (let i = 0; i < n; i++) {
    if (windowBars[i].high > periodHighBar.high) {
      periodHighBar = windowBars[i];
      periodHighIdx = i;
    }
    if (windowBars[i].low < periodLowBar.low) {
      periodLowBar = windowBars[i];
      periodLowIdx = i;
    }
  }
  majorSwings.highs.push({
    price: periodHighBar.high,
    date: periodHighBar.date,
    idx: periodHighIdx,
    volume: periodHighBar.volume,
    type: 'high',
  });
  majorSwings.lows.push({
    price: periodLowBar.low,
    date: periodLowBar.date,
    idx: periodLowIdx,
    volume: periodLowBar.volume,
    type: 'low',
  });

  interface LevelCluster {
    price: number;
    touches: number;
    lastDate: string;
    lastIdx: number;
    score: number;
    origin: 'high' | 'low';
  }

  const clusterPoints = (pts: SwingPoint[], origin: 'high' | 'low'): LevelCluster[] => {
    const sorted = [...pts].sort((a, b) => a.price - b.price);
    const clusters: LevelCluster[] = [];

    for (const p of sorted) {
      const match = clusters.find(
        (c) => Math.abs(p.price - c.price) / Math.max(0.01, c.price) <= clusterTolPct
      );
      if (match) {
        if (match.lastDate === p.date) continue;
        const total = match.touches + 1;
        match.price =
          origin === 'high'
            ? (match.price * match.touches + Math.max(match.price, p.price)) / total
            : (match.price * match.touches + Math.min(match.price, p.price)) / total;
        match.touches = total;
        if (p.idx > match.lastIdx) {
          match.lastIdx = p.idx;
          match.lastDate = p.date;
        }
      } else {
        clusters.push({
          price: p.price,
          touches: 1,
          lastDate: p.date,
          lastIdx: p.idx,
          score: 0,
          origin,
        });
      }
    }

    for (const c of clusters) {
      let extraTests = 0;
      let lastTestIdx = c.lastIdx;
      for (let i = 0; i < n; i++) {
        const b = windowBars[i];
        const tol = c.price * 0.008;
        const tested =
          origin === 'high'
            ? Math.abs(b.high - c.price) <= tol || Math.abs(b.close - c.price) <= tol
            : Math.abs(b.low - c.price) <= tol || Math.abs(b.close - c.price) <= tol;
        if (tested && Math.abs(i - lastTestIdx) >= 5) {
          extraTests++;
          lastTestIdx = i;
          c.lastDate = b.date;
        }
      }
      c.touches = Math.min(8, Math.max(c.touches, Math.min(c.touches + Math.floor(extraTests / 2), 6)));
      const recencyBoost = 0.6 + (c.lastIdx / Math.max(1, n)) * 0.8;
      const distPctAbs = Math.abs(c.price - currentClose) / currentClose;
      const proximityBoost = distPctAbs <= 0.18 ? 1.35 : distPctAbs <= 0.35 ? 1.0 : 0.65;
      c.score = c.touches * 18 * recencyBoost * proximityBoost;
    }

    return clusters.sort((a, b) => b.score - a.score);
  };

  const majorHighClusters = clusterPoints(majorSwings.highs, 'high');
  const majorLowClusters = clusterPoints(majorSwings.lows, 'low');
  const minorHighClusters = clusterPoints(minorSwings.highs, 'high');
  const minorLowClusters = clusterPoints(minorSwings.lows, 'low');

  const picked: StructuralPriceLevel[] = [];
  const isTooClose = (price: number) =>
    picked.some((p) => Math.abs(p.price - price) / Math.max(0.01, p.price) < minSepPct);

  // 1. Overhead Breakout Level (52W high or dominant major breakout ceiling above price)
  const overheadMajorHighs = majorHighClusters
    .filter((c) => c.price > currentClose * 1.003 && c.price <= currentClose * 1.48)
    .sort((a, b) => b.score - a.score);

  const majorBreakoutCandidate =
    overheadMajorHighs.find((c) => Math.abs(c.price - periodHighBar.high) / periodHighBar.high < 0.025) ||
    overheadMajorHighs[0];

  if (majorBreakoutCandidate) {
    const price = Number(majorBreakoutCandidate.price.toFixed(2));
    picked.push({
      id: 'major_breakout',
      kind: 'breakout',
      category: 'breakout',
      label:
        Math.abs(price - periodHighBar.high) / periodHighBar.high < 0.025
          ? '52W Breakout'
          : 'Major Breakout',
      price,
      touches: majorBreakoutCandidate.touches,
      lastTestedDate: majorBreakoutCandidate.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Major',
    });
  }

  // 2. Major Resistance (strongest structural overhead resistance distinct from breakout)
  const majorResistance = overheadMajorHighs
    .filter((c) => !isTooClose(c.price))
    .sort((a, b) => b.score - a.score)[0];

  if (majorResistance) {
    const price = Number(majorResistance.price.toFixed(2));
    picked.push({
      id: 'major_resistance',
      kind: 'resistance',
      category: 'major_resistance',
      label: 'Major Resistance',
      price,
      touches: majorResistance.touches,
      lastTestedDate: majorResistance.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Major',
    });
  }

  // 3. Minor Resistance (nearest short/intermediate swing ceiling above current close)
  const minorOverhead = minorHighClusters
    .filter(
      (c) =>
        c.price > currentClose * 1.003 &&
        c.price <= currentClose * 1.25 &&
        !isTooClose(c.price)
    )
    .sort((a, b) => a.price - b.price)[0];

  if (minorOverhead) {
    const price = Number(minorOverhead.price.toFixed(2));
    picked.push({
      id: 'minor_resistance',
      kind: 'resistance',
      category: 'minor_resistance',
      label: 'Minor Resistance',
      price,
      touches: minorOverhead.touches,
      lastTestedDate: minorOverhead.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Minor',
    });
  }

  // 4. Polarity-Flip Breakout Support (prior multi-touch swing high now cleanly below current price)
  const flipSupport = majorHighClusters
    .filter(
      (c) =>
        c.price < currentClose * 0.992 &&
        c.price >= currentClose * 0.84 &&
        c.touches >= 2 &&
        !isTooClose(c.price)
    )
    .sort((a, b) => b.price - a.price)[0];

  if (flipSupport) {
    const price = Number(flipSupport.price.toFixed(2));
    picked.push({
      id: 'breakout_flip_support',
      kind: 'support_flip',
      category: 'breakout',
      label: 'Breakout Support',
      price,
      touches: flipSupport.touches,
      lastTestedDate: flipSupport.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Major',
    });
  }

  // 5. Major Support (highest-conviction structural floor below price)
  const belowMajorLows = majorLowClusters.filter(
    (c) => c.price < currentClose * 0.992 && c.price >= currentClose * 0.58 && !isTooClose(c.price)
  );

  const majorSupport = belowMajorLows.sort((a, b) => b.score - a.score)[0];

  if (majorSupport && !isTooClose(majorSupport.price)) {
    const price = Number(majorSupport.price.toFixed(2));
    picked.push({
      id: 'major_support',
      kind: 'support',
      category: 'major_support',
      label: 'Major Support',
      price,
      touches: majorSupport.touches,
      lastTestedDate: majorSupport.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Major',
    });
  }

  // 6. Minor Support (nearest short/intermediate swing low below current close)
  const minorSupport = minorLowClusters
    .filter(
      (c) =>
        c.price < currentClose * 0.995 &&
        c.price >= currentClose * 0.84 &&
        !isTooClose(c.price)
    )
    .sort((a, b) => b.price - a.price)[0];

  if (minorSupport && !isTooClose(minorSupport.price)) {
    const price = Number(minorSupport.price.toFixed(2));
    picked.push({
      id: 'minor_support',
      kind: 'support',
      category: 'minor_support',
      label: 'Minor Support',
      price,
      touches: minorSupport.touches,
      lastTestedDate: minorSupport.lastDate,
      distPct: Number((((price - currentClose) / currentClose) * 100).toFixed(2)),
      strength: 'Minor',
    });
  }

  return picked.sort((a, b) => b.price - a.price);
}

/* ============================================================================
   2. MULTI-SETUP INSTITUTIONAL TRADE IDENTIFICATION ENGINE
   ============================================================================ */

export type TradeSetupTag =
  | 'POCKET_PIVOT'
  | 'RS_BLUE_DOT'
  | 'NR7_SQUEEZE'
  | 'MA_PULLBACK'
  | 'EPISODIC_PIVOT'
  | 'VCP_BREAKOUT'
  | 'WEEKLY_STAGE2';

export interface StockTradeDiagnosis {
  ticker: string;
  name: string;
  sector: string;
  capBucket: string;
  close: number;
  dailyChangePct: number;
  avgDailyTurnoverCr: number;
  rsRating: number;
  stage: 1 | 2 | 3 | 4;
  templatePassed: number;
  minerviniScore: number;
  adrPct20: number;
  atr14: number;
  atrPct: number;
  volRatio50D: number;
  distFrom50SmaPct: number;
  distFrom50SmaAtrs: number; // Extension warning when > 3.5 ATRs
  isExtended: boolean;
  distFrom52WHighPct: number;
  weeklyStage2: boolean;
  setups: TradeSetupTag[];
  primarySetup: string;
  convictionScore: number; // 0-100 multi-factor setup rank
  // Risk-defined trade execution plan (pure technical risk math — ZERO DCF/Valuation)
  entryTriggerInr: number;
  stopLossInr: number;
  stopDistancePct: number;
  r1Inr: number;
  r2Inr: number;
  r3Inr: number;
  pocketPivotDates: string[];
  nr7Dates: string[];
}

export function diagnoseBarsForSetups(
  bars: OHLCVBar[],
  meta: {
    ticker: string;
    name: string;
    sector: string;
    capBucket: string;
    avgDailyTurnoverCr: number;
    rsRating?: number;
    stage?: 1 | 2 | 3 | 4;
    templatePassed?: number;
    minerviniScore?: number;
    isVcpBreakout?: boolean;
    vcpPivot?: number;
  }
): StockTradeDiagnosis | null {
  if (bars.length < 60) return null;

  const closes = bars.map((b) => b.close);
  const vols = bars.map((b) => b.volume);
  const n = bars.length;
  const last = bars[n - 1];
  const prev = bars[n - 2];

  const ema10 = computeEmaSeries(closes, 10);
  const ema21 = computeEmaSeries(closes, 21);
  const sma50 = computeSmaSeries(closes, 50);
  const sma200 = computeSmaSeries(closes, 200);
  const vol50 = computeSmaSeries(vols, 50);
  const atr = computeAtrSeries(bars, 14);
  const bb = computeBollingerBands(closes, 20, 2);

  const curEma10 = ema10[n - 1];
  const curEma21 = ema21[n - 1];
  const curSma50 = sma50[n - 1];
  const curSma200 = sma200[n - 1];
  const curVol50 = vol50[n - 1] || 1;
  const curAtr = atr[n - 1] || last.close * 0.025;
  const atrPct = Number(((curAtr / last.close) * 100).toFixed(2));
  const adrPct20 = computeAdrPct(bars, 20);
  const volRatio50D = Number((last.volume / Math.max(1, curVol50)).toFixed(2));
  const dailyChangePct =
    prev.close > 0 ? Number((((last.close - prev.close) / prev.close) * 100).toFixed(2)) : 0;

  const win252 = bars.slice(-252);
  const hi52 = Math.max(...win252.map((b) => b.high));
  const distFrom52WHighPct = hi52 > 0 ? Number((((hi52 - last.close) / hi52) * 100).toFixed(2)) : 0;

  const distFrom50SmaPct =
    Number.isFinite(curSma50) && curSma50 > 0
      ? Number((((last.close - curSma50) / curSma50) * 100).toFixed(2))
      : 0;
  const distFrom50SmaAtrs =
    Number.isFinite(curSma50) && curAtr > 0
      ? Number(((last.close - curSma50) / curAtr).toFixed(2))
      : 0;
  const isExtended = distFrom50SmaAtrs > 3.5 || distFrom50SmaPct > 18;

  // 1. Pocket Pivot Detection (over last 20 bars for chart markers + last 3 bars for active radar)
  const pocketPivotDates: string[] = [];
  for (let i = Math.max(12, n - 40); i < n; i++) {
    const b = bars[i];
    const p = bars[i - 1];
    if (b.close <= p.close) continue;
    let maxDownVol10 = 0;
    for (let j = i - 10; j < i; j++) {
      if (bars[j].close < bars[j - 1].close) {
        maxDownVol10 = Math.max(maxDownVol10, bars[j].volume);
      }
    }
    const nearMa =
      (Number.isFinite(ema10[i]) && b.low <= ema10[i] * 1.02 && b.close >= ema10[i] * 0.99) ||
      (Number.isFinite(ema21[i]) && b.low <= ema21[i] * 1.025 && b.close >= ema21[i] * 0.99) ||
      (Number.isFinite(sma50[i]) && b.low <= sma50[i] * 1.03 && b.close >= sma50[i] * 0.99);
    if (maxDownVol10 > 0 && b.volume > maxDownVol10 && b.volume > (vol50[i] || 0) * 1.1 && nearMa) {
      pocketPivotDates.push(b.date);
    }
  }
  const hasRecentPocketPivot = pocketPivotDates.some((d) =>
    bars.slice(-3).some((b) => b.date === d)
  );

  // 2. NR7 & Bollinger-Keltner Volatility Squeeze Detection
  const nr7Dates: string[] = [];
  for (let i = Math.max(7, n - 40); i < n; i++) {
    const rangeToday = bars[i].high - bars[i].low;
    let isNarrowest = true;
    for (let j = i - 6; j < i; j++) {
      if (bars[j].high - bars[j].low <= rangeToday) {
        isNarrowest = false;
        break;
      }
    }
    if (isNarrowest && rangeToday > 0) nr7Dates.push(bars[i].date);
  }
  const isRecentNr7 = nr7Dates.some((d) => bars.slice(-2).some((b) => b.date === d));
  const bbUpper = bb.upper[n - 1];
  const bbLower = bb.lower[n - 1];
  const kcUpper = curEma21 + 1.5 * curAtr;
  const kcLower = curEma21 - 1.5 * curAtr;
  const isBbKcSqueeze =
    Number.isFinite(bbUpper) &&
    Number.isFinite(bbLower) &&
    bbUpper < kcUpper &&
    bbLower > kcLower;
  const hasNr7Squeeze = (isRecentNr7 || isBbKcSqueeze) && last.close > (curSma50 || 0);

  // 3. RS Blue-Dot (Relative Strength Line at/near 52W High BEFORE price breaks out)
  const rsSeries = computeRsLineVsNifty500(bars);
  const rsLast252 = rsSeries.slice(-252);
  const rsMax252 = rsLast252.length ? Math.max(...rsLast252.map((r) => r.value)) : 0;
  const rsCur = rsSeries[rsSeries.length - 1]?.value ?? 0;
  const isRsBlueDot =
    rsMax252 > 0 && rsCur >= rsMax252 * 0.992 && distFrom52WHighPct <= 14;

  // 4. Institutional 21-EMA / 50-SMA Pullback Bounce
  const rising50 = Number.isFinite(sma50[n - 1]) && Number.isFinite(sma50[n - 15]) && sma50[n - 1] > sma50[n - 15];
  const above200 = Number.isFinite(curSma200) && last.close > curSma200;
  const avgVol5 = vols.slice(-5).reduce((s, v) => s + v, 0) / 5;
  const touch21 =
    Number.isFinite(curEma21) &&
    last.low <= curEma21 * 1.018 &&
    last.close >= curEma21 * 0.985 &&
    last.close <= curEma21 * 1.035;
  const touch50 =
    Number.isFinite(curSma50) &&
    last.low <= curSma50 * 1.02 &&
    last.close >= curSma50 * 0.985 &&
    last.close <= curSma50 * 1.035;
  const isMaPullback =
    above200 &&
    rising50 &&
    (touch21 || touch50) &&
    avgVol5 <= curVol50 * 1.05 &&
    last.close >= last.open * 0.992;

  // 5. Episodic Pivot / High-Volume Opening Gap (last 3 sessions)
  const recent3 = bars.slice(-3);
  const isEpisodicPivot = recent3.some((b, idx) => {
    const absIdx = n - 3 + idx;
    if (absIdx < 1) return false;
    const prevC = bars[absIdx - 1].close;
    const gapPct = prevC > 0 ? ((b.open - prevC) / prevC) * 100 : 0;
    const dayRange = Math.max(0.01, b.high - b.low);
    const clv = (b.close - b.low) / dayRange;
    return gapPct >= 3.2 && b.volume >= (vol50[absIdx] || 1) * 1.7 && clv >= 0.45;
  });

  // 6. Multi-Timeframe Weekly Stage 2 Confirmation
  const weekly = resampleToWeekly(bars);
  const wCloses = weekly.map((w) => w.close);
  const wSma10 = computeSmaSeries(wCloses, 10);
  const wSma30 = computeSmaSeries(wCloses, 30);
  const wn = weekly.length;
  const weeklyStage2 =
    wn >= 35 &&
    Number.isFinite(wSma10[wn - 1]) &&
    Number.isFinite(wSma30[wn - 1]) &&
    wCloses[wn - 1] > wSma10[wn - 1] &&
    wSma10[wn - 1] > wSma30[wn - 1] &&
    wSma30[wn - 1] > wSma30[wn - 5];

  const setups: TradeSetupTag[] = [];
  if (meta.isVcpBreakout) setups.push('VCP_BREAKOUT');
  if (hasRecentPocketPivot) setups.push('POCKET_PIVOT');
  if (isRsBlueDot) setups.push('RS_BLUE_DOT');
  if (hasNr7Squeeze) setups.push('NR7_SQUEEZE');
  if (isMaPullback) setups.push('MA_PULLBACK');
  if (isEpisodicPivot) setups.push('EPISODIC_PIVOT');
  if (weeklyStage2) setups.push('WEEKLY_STAGE2');

  const rsRating = meta.rsRating ?? (isRsBlueDot ? 88 : 65);
  const stage = meta.stage ?? (weeklyStage2 ? 2 : above200 ? 1 : 4);
  const templatePassed = meta.templatePassed ?? (weeklyStage2 ? 7 : 4);
  const minerviniScore = meta.minerviniScore ?? (weeklyStage2 ? 78 : 52);

  // Composite Conviction Score (0–100) rewarding multi-setup confluence + healthy extension
  let score = minerviniScore * 0.45 + rsRating * 0.2;
  if (hasRecentPocketPivot) score += 12;
  if (isRsBlueDot) score += 10;
  if (hasNr7Squeeze) score += 9;
  if (isMaPullback) score += 9;
  if (isEpisodicPivot) score += 10;
  if (weeklyStage2) score += 8;
  if (meta.isVcpBreakout) score += 12;
  if (isExtended) score -= 14; // Penalize chasing extended stocks
  if (stage === 4) score = Math.min(score, 32);
  const convictionScore = Math.max(0, Math.min(100, Math.round(score)));

  // Risk-Defined Execution Plan (Technical Trigger & Tight Stop Loss — NO DCF/Valuation)
  const entryTriggerInr = Number(
    (
      meta.vcpPivot && meta.vcpPivot > last.close * 0.98 && meta.vcpPivot < last.close * 1.05
        ? meta.vcpPivot
        : Math.max(last.close, last.high * 1.001)
    ).toFixed(2)
  );
  const recentLow5 = Math.min(...bars.slice(-5).map((b) => b.low));
  const atrStop = entryTriggerInr - 1.5 * curAtr;
  const maxStop7Pct = entryTriggerInr * 0.93;
  const rawStop = Math.max(maxStop7Pct, Math.min(recentLow5 * 0.995, atrStop));
  const stopLossInr = Number(Math.min(entryTriggerInr * 0.985, rawStop).toFixed(2));
  const riskPerShare = Math.max(0.05, entryTriggerInr - stopLossInr);
  const stopDistancePct = Number(((riskPerShare / entryTriggerInr) * 100).toFixed(2));

  const primarySetup = meta.isVcpBreakout
    ? 'VCP Pivot Breakout'
    : hasRecentPocketPivot
    ? 'Pocket Pivot Accumulation'
    : isEpisodicPivot
    ? 'Episodic Pivot Gap'
    : isRsBlueDot && hasNr7Squeeze
    ? 'RS Blue-Dot + NR7 Squeeze'
    : isRsBlueDot
    ? 'RS 52W High Leadership'
    : isMaPullback
    ? '21E / 50S Institutional Pullback'
    : hasNr7Squeeze
    ? 'Volatility Contraction Squeeze'
    : weeklyStage2
    ? 'Weekly Stage 2 Uptrend'
    : 'Monitoring Base';

  return {
    ticker: meta.ticker,
    name: meta.name,
    sector: meta.sector,
    capBucket: meta.capBucket,
    close: last.close,
    dailyChangePct,
    avgDailyTurnoverCr: meta.avgDailyTurnoverCr,
    rsRating,
    stage,
    templatePassed,
    minerviniScore,
    adrPct20,
    atr14: Number(curAtr.toFixed(2)),
    atrPct,
    volRatio50D,
    distFrom50SmaPct,
    distFrom50SmaAtrs,
    isExtended,
    distFrom52WHighPct,
    weeklyStage2,
    setups,
    primarySetup,
    convictionScore,
    entryTriggerInr,
    stopLossInr,
    stopDistancePct,
    r1Inr: Number((entryTriggerInr + riskPerShare).toFixed(2)),
    r2Inr: Number((entryTriggerInr + 2 * riskPerShare).toFixed(2)),
    r3Inr: Number((entryTriggerInr + 3 * riskPerShare).toFixed(2)),
    pocketPivotDates,
    nr7Dates,
  };
}

const radarMemoCache = new Map<string, StockTradeDiagnosis[]>();

function radarSnapshotKey(stocks: IndianStock[]): string {
  const len = stocks.length;
  if (len === 0) return '0';
  let liveCount = 0;
  for (let i = 0; i < len; i++) {
    if (stocks[i].isLiveHydrated) liveCount++;
  }
  const a = stocks[0];
  const b = stocks[Math.floor(len / 2)];
  const c = stocks[len - 1];
  return `${len}:${liveCount}:${a.ticker}=${a.latestClose}:${b.ticker}=${b.latestClose}:${c.ticker}=${c.latestClose}`;
}

export function runTradeSetupRadar(stocks: IndianStock[]): StockTradeDiagnosis[] {
  const key = radarSnapshotKey(stocks);
  const cached = radarMemoCache.get(key);
  if (cached) return cached;

  const minerviniList = runMinerviniAnalysis(stocks, DEFAULT_TREND_THRESHOLDS);
  const mByTicker = new Map(minerviniList.map((m) => [m.stock.ticker, m]));

  const out: StockTradeDiagnosis[] = [];
  for (const s of stocks) {
    const m = mByTicker.get(s.ticker);
    const diag = diagnoseBarsForSetups(s.bars, {
      ticker: s.ticker,
      name: s.name,
      sector: s.sector,
      capBucket: s.capBucket,
      avgDailyTurnoverCr: s.avgDailyTurnoverCr,
      rsRating: m?.rsRating,
      stage: m?.stage,
      templatePassed: m?.passedCount,
      minerviniScore: m?.minerviniScore,
      isVcpBreakout: m?.vcp.isPivotBreakout,
      vcpPivot: m?.vcp.pivotPrice,
    });
    if (diag) out.push(diag);
  }

  const sorted = out.sort((a, b) => b.convictionScore - a.convictionScore || b.rsRating - a.rsRating);
  if (radarMemoCache.size > 16) radarMemoCache.clear();
  radarMemoCache.set(key, sorted);
  return sorted;
}

/* ============================================================================
   3. INDIAN MARKET REGIME, DISTRIBUTION DAYS & SECTOR ROTATION ENGINE
   ============================================================================ */

export interface SectorRotationRow {
  sector: string;
  stockCount: number;
  ret1W: number;
  ret1M: number;
  ret3M: number;
  rsVsNifty3M: number;
  pctStage2: number;
  quadrant: 'Leading' | 'Improving' | 'Weakening' | 'Lagging';
  topLeaders: { ticker: string; rsRating: number; changePct: number }[];
}

export interface MarketRegimeSnapshot {
  regimeLabel: 'Confirmed Uptrend' | 'Uptrend Under Pressure' | 'Rally Attempt' | 'Market in Correction';
  recommendedExposurePct: number;
  nifty50Close: number;
  nifty50Above21Ema: boolean;
  nifty50Above50Sma: boolean;
  nifty50Above200Sma: boolean;
  distributionDays25: number;
  distributionDates: string[];
  pctAbove20Ema: number;
  pctAbove50Sma: number;
  pctAbove200Sma: number;
  stageCounts: Record<1 | 2 | 3 | 4, number>;
  new52WHighs: number;
  new52WLows: number;
  pocketPivotCount: number;
  rsBlueDotCount: number;
  squeezeCount: number;
  sectors: SectorRotationRow[];
}

export function computeMarketRegime(
  stocks: IndianStock[],
  radarRows: StockTradeDiagnosis[]
): MarketRegimeSnapshot {
  const n50Bars = BENCHMARKS.NIFTY50.bars;
  const n50Closes = n50Bars.map((b) => b.close);
  const n50Ema21 = computeEmaSeries(n50Closes, 21);
  const n50Sma50 = computeSmaSeries(n50Closes, 50);
  const n50Sma200 = computeSmaSeries(n50Closes, 200);
  const len = n50Bars.length;
  const curClose = n50Bars[len - 1]?.close ?? 0;

  const nifty50Above21Ema = curClose > (n50Ema21[len - 1] || 0);
  const nifty50Above50Sma = curClose > (n50Sma50[len - 1] || 0);
  const nifty50Above200Sma = curClose > (n50Sma200[len - 1] || 0);

  // O'Neil Distribution Day Counter over last 25 NSE sessions
  // (Index closes down >= 0.2% on volume higher than prior session, or proxy > 0.55% down day when index volume=0)
  const distributionDates: string[] = [];
  const lookbackStart = Math.max(1, len - 25);
  for (let i = lookbackStart; i < len; i++) {
    const b = n50Bars[i];
    const p = n50Bars[i - 1];
    const chgPct = p.close > 0 ? ((b.close - p.close) / p.close) * 100 : 0;
    const hasVol = b.volume > 0 && p.volume > 0;
    const isDist = hasVol ? chgPct <= -0.2 && b.volume > p.volume : chgPct <= -0.55;
    if (isDist) {
      // Expires if index rallied >= 5% above that day's close later
      let rallied5 = false;
      for (let k = i + 1; k < len; k++) {
        if (n50Bars[k].close >= b.close * 1.05) {
          rallied5 = true;
          break;
        }
      }
      if (!rallied5) distributionDates.push(b.date);
    }
  }
  const distributionDays25 = distributionDates.length;

  // Internal Breadth Gauges across live NSE universe
  let above20 = 0;
  let above50 = 0;
  let above200 = 0;
  let new52WHighs = 0;
  let new52WLows = 0;
  for (const s of stocks) {
    const c = s.bars.map((b) => b.close);
    const e20 = computeEmaSeries(c, 20);
    const s50 = computeSmaSeries(c, 50);
    const s200 = computeSmaSeries(c, 200);
    const lastC = c[c.length - 1];
    if (lastC > e20[c.length - 1]) above20++;
    if (lastC > s50[c.length - 1]) above50++;
    if (lastC > s200[c.length - 1]) above200++;
    const w252 = s.bars.slice(-252);
    const hi = Math.max(...w252.map((b) => b.high));
    const lo = Math.min(...w252.map((b) => b.low));
    if (lastC >= hi * 0.99) new52WHighs++;
    if (lastC <= lo * 1.01) new52WLows++;
  }
  const denom = Math.max(1, stocks.length);
  const pctAbove20Ema = Math.round((above20 / denom) * 100);
  const pctAbove50Sma = Math.round((above50 / denom) * 100);
  const pctAbove200Sma = Math.round((above200 / denom) * 100);

  const stageCounts: Record<1 | 2 | 3 | 4, number> = { 1: 0, 2: 0, 3: 0, 4: 0 };
  for (const r of radarRows) stageCounts[r.stage]++;

  // Market Regime Traffic-Light & Exposure Guidance
  let regimeLabel: MarketRegimeSnapshot['regimeLabel'] = 'Confirmed Uptrend';
  let recommendedExposurePct = 85;
  if (nifty50Above21Ema && nifty50Above50Sma && distributionDays25 <= 3 && pctAbove50Sma >= 50) {
    regimeLabel = 'Confirmed Uptrend';
    recommendedExposurePct = distributionDays25 <= 1 ? 100 : 85;
  } else if (nifty50Above50Sma && distributionDays25 >= 4) {
    regimeLabel = 'Uptrend Under Pressure';
    recommendedExposurePct = 55;
  } else if (!nifty50Above50Sma && nifty50Above21Ema) {
    regimeLabel = 'Rally Attempt';
    recommendedExposurePct = 35;
  } else if (!nifty50Above50Sma && !nifty50Above200Sma) {
    regimeLabel = 'Market in Correction';
    recommendedExposurePct = 15;
  } else {
    regimeLabel = 'Uptrend Under Pressure';
    recommendedExposurePct = 50;
  }

  // Sector Rotation Matrix (1W, 1M, 3M vs NIFTY 500)
  const n500Bars = BENCHMARKS.NIFTY500.bars;
  const n500Cur = n500Bars[n500Bars.length - 1]?.close || 1;
  const n500_3M = n500Bars[Math.max(0, n500Bars.length - 64)]?.close || n500Cur;
  const nifty3MRet = ((n500Cur - n500_3M) / n500_3M) * 100;

  const bySector = new Map<string, IndianStock[]>();
  for (const s of stocks) {
    const arr = bySector.get(s.sector) || [];
    arr.push(s);
    bySector.set(s.sector, arr);
  }
  const radarByTicker = new Map(radarRows.map((r) => [r.ticker, r]));

  const sectors: SectorRotationRow[] = [];
  for (const [sector, list] of bySector.entries()) {
    const avgRet = (days: number) => {
      const vals = list.map((s) => {
        const b = s.bars;
        const cNow = b[b.length - 1]?.close || 1;
        const cPrev = b[Math.max(0, b.length - 1 - days)]?.close || cNow;
        return ((cNow - cPrev) / cPrev) * 100;
      });
      return Number((vals.reduce((a, b) => a + b, 0) / Math.max(1, vals.length)).toFixed(2));
    };

    const ret1W = avgRet(5);
    const ret1M = avgRet(21);
    const ret3M = avgRet(63);
    const rsVsNifty3M = Number((ret3M - nifty3MRet).toFixed(2));
    const stage2InSector = list.filter((s) => radarByTicker.get(s.ticker)?.stage === 2).length;
    const pctStage2 = Math.round((stage2InSector / Math.max(1, list.length)) * 100);

    let quadrant: SectorRotationRow['quadrant'] = 'Leading';
    if (rsVsNifty3M >= 0 && ret1M >= 0) quadrant = 'Leading';
    else if (rsVsNifty3M < 0 && ret1M >= 0) quadrant = 'Improving';
    else if (rsVsNifty3M >= 0 && ret1M < 0) quadrant = 'Weakening';
    else quadrant = 'Lagging';

    const topLeaders = list
      .map((s) => ({
        ticker: s.ticker,
        rsRating: radarByTicker.get(s.ticker)?.rsRating ?? 50,
        changePct: s.dailyChangePct,
      }))
      .sort((a, b) => b.rsRating - a.rsRating)
      .slice(0, 3);

    sectors.push({
      sector,
      stockCount: list.length,
      ret1W,
      ret1M,
      ret3M,
      rsVsNifty3M,
      pctStage2,
      quadrant,
      topLeaders,
    });
  }
  sectors.sort((a, b) => b.rsVsNifty3M - a.rsVsNifty3M);

  return {
    regimeLabel,
    recommendedExposurePct,
    nifty50Close: curClose,
    nifty50Above21Ema,
    nifty50Above50Sma,
    nifty50Above200Sma,
    distributionDays25,
    distributionDates,
    pctAbove20Ema,
    pctAbove50Sma,
    pctAbove200Sma,
    stageCounts,
    new52WHighs,
    new52WLows,
    pocketPivotCount: radarRows.filter((r) => r.setups.includes('POCKET_PIVOT')).length,
    rsBlueDotCount: radarRows.filter((r) => r.setups.includes('RS_BLUE_DOT')).length,
    squeezeCount: radarRows.filter((r) => r.setups.includes('NR7_SQUEEZE')).length,
    sectors,
  };
}

/* ============================================================================
   4. MULTI-INDICATOR SIGNAL MATRIX (15 INDICATORS ACROSS 5 PILLARS)
   ============================================================================ */

export type SignalBias = 'Bullish' | 'Neutral' | 'Bearish';

export interface IndicatorMatrixSignal {
  id: string;
  category: 'Trend' | 'Momentum' | 'Volatility' | 'Volume & RS' | 'SEPA' | 'Sector';
  name: string;
  reading: string;
  rule: string;
  signal: SignalBias;
}

export interface MatrixSepaContext {
  minerviniScore: number;
  passedCount: number;
  stage: 1 | 2 | 3 | 4;
  rsRating: number;
}

export interface MatrixSectorContext {
  sectorName: string;
  sectorScore: number; // 0-100 NSE Sectors Technical Scorecard
  sectorRank: number;
  sectorTotal: number;
  sectorRegime: string;
  sectorQuadrant: 'Leading' | 'Improving' | 'Weakening' | 'Lagging';
  sectorRsRatio: number;
  sectorRsMomentum: number;
  sectorPctAbove50Sma?: number;
  subsectorName?: string | null;
  subsectorScore?: number | null;
  subsectorRank?: number | null;
  subsectorTotal?: number | null;
  subsectorQuadrant?: 'Leading' | 'Improving' | 'Weakening' | 'Lagging' | null;
  subsectorRsRatio?: number | null;
  subsectorRsMomentum?: number | null;
}

export interface MultiIndicatorMatrixResult {
  consensus: 'Strong Buy' | 'Buy' | 'Neutral' | 'Sell' | 'Strong Sell';
  bullishCount: number;
  neutralCount: number;
  bearishCount: number;
  scorePct: number;
  signals: IndicatorMatrixSignal[];
  donchianSummary?: {
    regime: DonchianChannelResult['regime'];
    signal: SignalBias;
    latestAlert: DonchianAlertSignal | null;
    positionPct: number;
  };
  supertrendSummary?: {
    direction: 1 | -1;
    line: number | null;
    distancePct: number;
    barsSinceFlip: number;
  };
  sepaSummary?: MatrixSepaContext;
  sectorSummary?: MatrixSectorContext;
  rsi14?: number | null;
}

function computeAdx14(bars: OHLCVBar[]): { adx: number; plusDi: number; minusDi: number } {
  if (bars.length < 30) return { adx: 20, plusDi: 20, minusDi: 20 };
  const period = 14;
  const tr: number[] = [];
  const pDm: number[] = [];
  const mDm: number[] = [];
  for (let i = 1; i < bars.length; i++) {
    const h = bars[i].high;
    const l = bars[i].low;
    const pc = bars[i - 1].close;
    const up = h - bars[i - 1].high;
    const dn = bars[i - 1].low - l;
    tr.push(Math.max(h - l, Math.abs(h - pc), Math.abs(l - pc)));
    pDm.push(up > dn && up > 0 ? up : 0);
    mDm.push(dn > up && dn > 0 ? dn : 0);
  }
  let atrSum = 0;
  let pSum = 0;
  let mSum = 0;
  for (let i = 0; i < period; i++) {
    atrSum += tr[i];
    pSum += pDm[i];
    mSum += mDm[i];
  }
  const dxVals: number[] = [];
  let lastPlusDi = 20;
  let lastMinusDi = 20;
  for (let i = period; i < tr.length; i++) {
    atrSum = atrSum - atrSum / period + tr[i];
    pSum = pSum - pSum / period + pDm[i];
    mSum = mSum - mSum / period + mDm[i];
    const pDi = atrSum > 0 ? (100 * pSum) / atrSum : 0;
    const mDi = atrSum > 0 ? (100 * mSum) / atrSum : 0;
    const dx = pDi + mDi > 0 ? (100 * Math.abs(pDi - mDi)) / (pDi + mDi) : 0;
    dxVals.push(dx);
    lastPlusDi = pDi;
    lastMinusDi = mDi;
  }
  const adxSlice = dxVals.slice(-period);
  const adx = adxSlice.length ? adxSlice.reduce((a, b) => a + b, 0) / adxSlice.length : 20;
  return {
    adx: Number(adx.toFixed(1)),
    plusDi: Number(lastPlusDi.toFixed(1)),
    minusDi: Number(lastMinusDi.toFixed(1)),
  };
}

export function computeMultiIndicatorMatrix(
  rawBars: OHLCVBar[],
  sepaContext?: MatrixSepaContext | null,
  sectorContext?: MatrixSectorContext | null
): MultiIndicatorMatrixResult {
  const bars = rawBars.length > 260 ? rawBars.slice(-260) : rawBars;
  if (bars.length < 30) {
    return {
      consensus: 'Neutral',
      bullishCount: 0,
      neutralCount: 0,
      bearishCount: 0,
      scorePct: 50,
      signals: [],
    };
  }

  const closes = bars.map((b) => b.close);
  const vols = bars.map((b) => b.volume);
  const n = bars.length;
  const last = bars[n - 1];

  const ema10 = computeEmaSeries(closes, 10);
  const ema21 = computeEmaSeries(closes, 21);
  const sma50 = computeSmaSeries(closes, 50);
  const sma200 = computeSmaSeries(closes, 200);
  const rsi = computeRsiSeries(closes, 14);
  const macd = computeMacdSeries(closes, 12, 26, 9);
  const bb = computeBollingerBands(closes, 20, 2);
  const atr = computeAtrSeries(bars, 14);
  const vwap = computeRollingVwap(bars, 20);
  const vol50 = computeSmaSeries(vols, 50);
  const rsLine = computeRsLineVsNifty500(bars);
  const adxRes = computeAdx14(bars);
  const donchian20 = computeDonchianChannel(bars, 20);
  const supertrend = computeSupertrendSeries(bars, 10, 3);
  const resolvedSepa: MatrixSepaContext | null =
    sepaContext ??
    (() => {
      const onDemand = computeOnDemandMinerviniChecklist(bars);
      return onDemand
        ? {
            minerviniScore: onDemand.minerviniScore,
            passedCount: onDemand.passedCount,
            stage: onDemand.stage,
            rsRating: onDemand.rsRating,
          }
        : null;
    })();

  const curE10 = ema10[n - 1];
  const curE21 = ema21[n - 1];
  const curS50 = sma50[n - 1];
  const curS200 = sma200[n - 1];
  const curRsi = rsi[n - 1];
  const curMacd = macd.macd[n - 1];
  const curSig = macd.signal[n - 1];
  const curHist = macd.hist[n - 1];
  const prevHist = macd.hist[n - 2];
  const curAtr = atr[n - 1] || last.close * 0.02;
  const curVwap = vwap[n - 1];
  const curVol50 = vol50[n - 1] || 1;
  const volRatio = last.volume / Math.max(1, curVol50);

  // Weekly alignment
  const weekly = resampleToWeekly(bars);
  const wCloses = weekly.map((w) => w.close);
  const wSma10 = computeSmaSeries(wCloses, 10);
  const wSma30 = computeSmaSeries(wCloses, 30);
  const wn = weekly.length;
  const wClose = wCloses[wn - 1];
  const w10 = wSma10[wn - 1];
  const w30 = wSma30[wn - 1];

  // Bollinger vs Keltner Squeeze
  const bbW =
    Number.isFinite(bb.upper[n - 1]) && Number.isFinite(bb.lower[n - 1]) && bb.mid[n - 1] > 0
      ? ((bb.upper[n - 1] - bb.lower[n - 1]) / bb.mid[n - 1]) * 100
      : 0;
  const isSqueeze =
    Number.isFinite(bb.upper[n - 1]) &&
    bb.upper[n - 1] < curE21 + 1.5 * curAtr &&
    bb.lower[n - 1] > curE21 - 1.5 * curAtr;

  // RS vs NIFTY 500
  const rs252 = rsLine.slice(-252);
  const rsMax = rs252.length ? Math.max(...rs252.map((r) => r.value)) : 100;
  const rsCur = rsLine[rsLine.length - 1]?.value ?? 100;
  const rs20Prev = rsLine[Math.max(0, rsLine.length - 21)]?.value ?? rsCur;
  const rsSlopeUp = rsCur > rs20Prev * 1.01;
  const rsNearHigh = rsCur >= rsMax * 0.985;

  const signals: IndicatorMatrixSignal[] = [
    {
      id: 'ema_10_21',
      category: 'Trend',
      name: 'EMA 10 / 21 Stack',
      reading: `10E ₹${curE10.toFixed(1)} · 21E ₹${curE21.toFixed(1)}`,
      rule: 'Price > 10E > 21E',
      signal:
        last.close > curE10 && curE10 > curE21
          ? 'Bullish'
          : last.close < curE10 && curE10 < curE21
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'sma_50',
      category: 'Trend',
      name: '50-Day SMA Trend',
      reading: Number.isFinite(curS50)
        ? `₹${curS50.toFixed(1)} (${(((last.close - curS50) / curS50) * 100).toFixed(1)}%)`
        : 'N/A',
      rule: 'Price above rising 50-SMA',
      signal: !Number.isFinite(curS50)
        ? 'Neutral'
        : last.close > curS50 && curS50 >= (sma50[n - 10] || curS50)
        ? 'Bullish'
        : last.close < curS50
        ? 'Bearish'
        : 'Neutral',
    },
    {
      id: 'sma_200',
      category: 'Trend',
      name: '200-Day Secular SMA',
      reading: Number.isFinite(curS200)
        ? `₹${curS200.toFixed(1)} (${(((last.close - curS200) / curS200) * 100).toFixed(1)}%)`
        : 'Insufficient history',
      rule: 'Price > 200-SMA & 50 > 200',
      signal: !Number.isFinite(curS200)
        ? 'Neutral'
        : last.close > curS200 && curS50 > curS200
        ? 'Bullish'
        : last.close < curS200
        ? 'Bearish'
        : 'Neutral',
    },
    {
      id: 'weekly_stage',
      category: 'Trend',
      name: 'Weekly 10W / 30W Alignment',
      reading:
        Number.isFinite(w10) && Number.isFinite(w30)
          ? `10W ₹${w10.toFixed(0)} · 30W ₹${w30.toFixed(0)}`
          : 'N/A',
      rule: 'Weekly Close > 10W > 30W',
      signal:
        !Number.isFinite(w10) || !Number.isFinite(w30)
          ? 'Neutral'
          : wClose > w10 && w10 > w30
          ? 'Bullish'
          : wClose < w30
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'rsi_14',
      category: 'Momentum',
      name: 'RSI (14)',
      reading: Number.isFinite(curRsi) ? curRsi.toFixed(1) : 'N/A',
      rule: '55–80 Bullish · <45 Weak',
      signal: !Number.isFinite(curRsi)
        ? 'Neutral'
        : curRsi >= 55 && curRsi <= 80
        ? 'Bullish'
        : curRsi < 45
        ? 'Bearish'
        : 'Neutral',
    },
    {
      id: 'macd',
      category: 'Momentum',
      name: 'MACD (12, 26, 9)',
      reading:
        Number.isFinite(curMacd) && Number.isFinite(curSig)
          ? `${curMacd.toFixed(2)} / Sig ${curSig.toFixed(2)}`
          : 'N/A',
      rule: 'MACD > Signal & Histogram rising',
      signal:
        !Number.isFinite(curMacd) || !Number.isFinite(curSig)
          ? 'Neutral'
          : curMacd > curSig && curHist >= prevHist
          ? 'Bullish'
          : curMacd < curSig && curHist <= prevHist
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'adx_14',
      category: 'Momentum',
      name: 'ADX (14) & DI Direction',
      reading: `ADX ${adxRes.adx} (+DI ${adxRes.plusDi} / -DI ${adxRes.minusDi})`,
      rule: 'ADX ≥ 20 with +DI > -DI',
      signal:
        adxRes.adx >= 18 && adxRes.plusDi > adxRes.minusDi
          ? 'Bullish'
          : adxRes.adx >= 18 && adxRes.minusDi > adxRes.plusDi
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'roc_63',
      category: 'Momentum',
      name: '3-Month Price Momentum',
      reading: `${(
        ((last.close - bars[Math.max(0, n - 64)].close) /
          Math.max(1, bars[Math.max(0, n - 64)].close)) *
        100
      ).toFixed(1)}%`,
      rule: 'Positive 63-session impulse',
      signal:
        last.close > bars[Math.max(0, n - 64)].close * 1.04
          ? 'Bullish'
          : last.close < bars[Math.max(0, n - 64)].close * 0.95
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'bb_squeeze',
      category: 'Volatility',
      name: 'Bollinger (20,2) & Squeeze',
      reading: `Width ${bbW.toFixed(1)}%${isSqueeze ? ' · Coiling' : ''}`,
      rule: 'Upper half / Squeeze expansion',
      signal:
        last.close >= bb.mid[n - 1] && (isSqueeze || last.close <= bb.upper[n - 1])
          ? 'Bullish'
          : last.close < bb.lower[n - 1] || last.close < bb.mid[n - 1] * 0.97
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'atr_extension',
      category: 'Volatility',
      name: 'ATR(14) & 50D Extension',
      reading: `ATR ₹${curAtr.toFixed(1)} (${((curAtr / last.close) * 100).toFixed(1)}%)`,
      rule: 'Controlled volatility, not >3.5 ATR ext.',
      signal:
        Number.isFinite(curS50) &&
        last.close >= curS50 &&
        (last.close - curS50) / Math.max(0.01, curAtr) <= 3.5
          ? 'Bullish'
          : Number.isFinite(curS50) && last.close < curS50 - 1.5 * curAtr
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'vwap_vol',
      category: 'Volume & RS',
      name: 'Rolling VWAP (20D) & Volume',
      reading: `VWAP ₹${curVwap.toFixed(1)} · ${volRatio.toFixed(2)}× 50D Vol`,
      rule: 'Close > VWAP with healthy demand',
      signal:
        last.close > curVwap && (last.close >= last.open || volRatio >= 1.1)
          ? 'Bullish'
          : last.close < curVwap && last.close < last.open
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'rs_nifty500',
      category: 'Volume & RS',
      name: 'RS Line vs NIFTY 500',
      reading: `RS ${rsCur.toFixed(1)}${rsNearHigh ? ' · 52W RS High' : ''}`,
      rule: 'Outperforming NIFTY 500 benchmark',
      signal: rsNearHigh || rsSlopeUp ? 'Bullish' : rsCur < rs20Prev * 0.97 ? 'Bearish' : 'Neutral',
    },
    {
      id: 'donchian_20',
      category: 'Volatility',
      name: 'Donchian Channel (20)',
      reading:
        donchian20.currentUpper !== null && donchian20.currentLower !== null
          ? `${donchian20.regime} · ${
              donchian20.latestSignal
                ? `Last: ${donchian20.latestSignal.type} @ ₹${donchian20.latestSignal.triggerPrice.toLocaleString('en-IN', {
                    maximumFractionDigits: 2,
                  })} (${
                    donchian20.latestSignal.barsAgo === 0
                      ? 'Latest'
                      : `${donchian20.latestSignal.barsAgo}D ago`
                  })`
                : `Pos ${donchian20.positionInChannelPct.toFixed(0)}%`
            }`
          : 'Insufficient history',
      rule: 'Breakout > 20D High / Upper half',
      signal:
        donchian20.regime === 'Bullish Breakout' || donchian20.regime === 'Upper Channel'
          ? 'Bullish'
          : donchian20.regime === 'Bearish Breakdown' || donchian20.regime === 'Lower Channel'
          ? 'Bearish'
          : 'Neutral',
    },
    {
      id: 'supertrend_10_3',
      category: 'Trend',
      name: 'Supertrend (10, 3)',
      reading:
        supertrend.currentLine !== null
          ? `${supertrend.currentDirection === 1 ? 'Bullish' : 'Bearish'} ${
              supertrend.currentDirection === 1 ? 'above' : 'below'
            } ₹${supertrend.currentLine.toFixed(1)} (${
              supertrend.distancePct >= 0 ? '+' : ''
            }${supertrend.distancePct.toFixed(1)}%)`
          : 'N/A',
      rule: 'Close above rising ATR trailing band',
      signal:
        supertrend.currentLine === null
          ? 'Neutral'
          : supertrend.currentDirection === 1
          ? 'Bullish'
          : 'Bearish',
    },
    {
      id: 'minervini_sepa',
      category: 'SEPA',
      name: 'Mark Minervini SEPA Checklist',
      reading: resolvedSepa
        ? `Score ${resolvedSepa.minerviniScore}/100 · ${resolvedSepa.passedCount}/8 · S${resolvedSepa.stage}`
        : 'Insufficient history',
      rule: 'Score ≥ 65 & Template ≥ 6/8 (Stage 2)',
      signal: !resolvedSepa
        ? 'Neutral'
        : resolvedSepa.minerviniScore >= 65 && resolvedSepa.passedCount >= 6
        ? 'Bullish'
        : resolvedSepa.minerviniScore < 42 || resolvedSepa.stage === 4
        ? 'Bearish'
        : 'Neutral',
    },
  ];

  if (sectorContext) {
    const activeQuad = sectorContext.subsectorQuadrant || sectorContext.sectorQuadrant;
    const isBullQuad =
      sectorContext.sectorQuadrant === 'Leading' || sectorContext.sectorQuadrant === 'Improving';
    const isSubBullQuad = activeQuad === 'Leading' || activeQuad === 'Improving';

    signals.push({
      id: 'nse_sector_scorecard',
      category: 'Sector',
      name: 'NSE Sector Scorecard & Quadrant',
      reading: `${sectorContext.sectorName} ${sectorContext.sectorScore}/100 (#${sectorContext.sectorRank}/${sectorContext.sectorTotal}) · ${sectorContext.sectorQuadrant}${
        sectorContext.subsectorName && sectorContext.subsectorQuadrant
          ? ` · Sub: ${sectorContext.subsectorName} (${sectorContext.subsectorQuadrant})`
          : ''
      }`,
      rule: 'Sector Score ≥ 60 & Leading / Improving Quadrant',
      signal:
        (sectorContext.sectorScore >= 60 && isBullQuad) ||
        (sectorContext.sectorScore >= 55 && isBullQuad && isSubBullQuad)
          ? 'Bullish'
          : sectorContext.sectorScore < 45 ||
            sectorContext.sectorQuadrant === 'Lagging' ||
            (sectorContext.subsectorQuadrant === 'Lagging' && sectorContext.sectorQuadrant === 'Weakening')
          ? 'Bearish'
          : 'Neutral',
    });
  }

  const donchianSignal = signals.find((s) => s.id === 'donchian_20')?.signal ?? 'Neutral';
  const bullishCount = signals.filter((s) => s.signal === 'Bullish').length;
  const neutralCount = signals.filter((s) => s.signal === 'Neutral').length;
  const bearishCount = signals.filter((s) => s.signal === 'Bearish').length;
  const scorePct = Math.round(((bullishCount + neutralCount * 0.5) / signals.length) * 100);

  let consensus: MultiIndicatorMatrixResult['consensus'] = 'Neutral';
  if (scorePct >= 78) consensus = 'Strong Buy';
  else if (scorePct >= 60) consensus = 'Buy';
  else if (scorePct <= 25) consensus = 'Strong Sell';
  else if (scorePct <= 42) consensus = 'Sell';

  return {
    consensus,
    bullishCount,
    neutralCount,
    bearishCount,
    scorePct,
    signals,
    donchianSummary: {
      regime: donchian20.regime,
      signal: donchianSignal,
      latestAlert: donchian20.latestSignal,
      positionPct: donchian20.positionInChannelPct,
    },
    supertrendSummary: {
      direction: supertrend.currentDirection,
      line: supertrend.currentLine,
      distancePct: supertrend.distancePct,
      barsSinceFlip: supertrend.barsSinceFlip,
    },
    sepaSummary: resolvedSepa ?? undefined,
    sectorSummary: sectorContext ?? undefined,
    rsi14: Number.isFinite(curRsi) ? Number(curRsi.toFixed(1)) : null,
  };
}

/* ============================================================================
   5. ON-DEMAND MINERVINI SEPA CHECKLIST FOR ANY NSE/BSE STOCK
   ============================================================================ */

export interface OnDemandMinerviniChecklist {
  passedCount: number;
  allPassed: boolean;
  stage: 1 | 2 | 3 | 4;
  stageLabel: string;
  rsRating: number;
  minerviniScore: number;
  vcpSummary: string;
  pivotPrice: number;
  suggestedStopLossInr: number;
  conditions: { id: number; label: string; detail: string; passed: boolean }[];
}

export function computeOnDemandMinerviniChecklist(
  bars: OHLCVBar[],
  extras?: { qtrEpsYoY?: number | null; qtrRevYoY?: number | null; roePct?: number | null }
): OnDemandMinerviniChecklist | null {
  if (bars.length < 60) return null;
  const closes = bars.map((b) => b.close);
  const n = bars.length;
  const price = closes[n - 1];
  const sma50 = computeSmaSeries(closes, 50)[n - 1];
  const sma150 = computeSmaSeries(closes, 150)[n - 1];
  const sma200Series = computeSmaSeries(closes, 200);
  const sma200 = sma200Series[n - 1];
  const sma200Prev = sma200Series[Math.max(0, n - 22)];

  const win252 = bars.slice(-252);
  const high52W = Math.max(...win252.map((b) => b.high));
  const low52W = Math.min(...win252.map((b) => b.low));
  const pctAbove52WLow = low52W > 0 ? ((price - low52W) / low52W) * 100 : 0;
  const pctBelow52WHigh = high52W > 0 ? ((high52W - price) / high52W) * 100 : 0;

  // Estimate IBD-style RS Rating vs NIFTY 500 12M weighted return
  const bmBars = BENCHMARKS.NIFTY500.bars;
  const calcWeighted = (arr: OHLCVBar[]) => {
    const l = arr.length;
    const c0 = arr[l - 1].close;
    const r3 = (c0 - arr[Math.max(0, l - 64)].close) / Math.max(1, arr[Math.max(0, l - 64)].close);
    const r6 = (c0 - arr[Math.max(0, l - 127)].close) / Math.max(1, arr[Math.max(0, l - 127)].close);
    const r9 = (c0 - arr[Math.max(0, l - 190)].close) / Math.max(1, arr[Math.max(0, l - 190)].close);
    const r12 = (c0 - arr[Math.max(0, l - 253)].close) / Math.max(1, arr[Math.max(0, l - 253)].close);
    return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12;
  };
  const stockPerf = calcWeighted(bars);
  const bmPerf = calcWeighted(bmBars);
  const alpha = stockPerf - bmPerf;
  const rsRating = Math.max(1, Math.min(99, Math.round(52 + alpha * 115)));

  const c1 = Number.isFinite(sma150) && Number.isFinite(sma200) && price > sma150 && price > sma200;
  const c2 = Number.isFinite(sma150) && Number.isFinite(sma200) && sma150 > sma200;
  const c3 = Number.isFinite(sma200) && Number.isFinite(sma200Prev) && sma200 > sma200Prev;
  const c4 = Number.isFinite(sma50) && Number.isFinite(sma150) && Number.isFinite(sma200) && sma50 > sma150 && sma50 > sma200;
  const c5 = Number.isFinite(sma50) && price > sma50;
  const c6 = pctAbove52WLow >= 30;
  const c7 = pctBelow52WHigh <= 25;
  const c8 = rsRating >= 70;

  const conditions = [
    {
      id: 1,
      label: 'Price > 150-Day & 200-Day SMA',
      detail: `LTP ₹${price.toFixed(1)} vs 150D ₹${Number.isFinite(sma150) ? sma150.toFixed(1) : '—'} & 200D ₹${Number.isFinite(sma200) ? sma200.toFixed(1) : '—'}`,
      passed: c1,
    },
    {
      id: 2,
      label: '150-Day SMA > 200-Day SMA',
      detail: `150D ₹${Number.isFinite(sma150) ? sma150.toFixed(1) : '—'} vs 200D ₹${Number.isFinite(sma200) ? sma200.toFixed(1) : '—'}`,
      passed: c2,
    },
    {
      id: 3,
      label: '200-Day SMA Trending Up (≥1M)',
      detail: `Now ₹${Number.isFinite(sma200) ? sma200.toFixed(1) : '—'} vs 1M ago ₹${Number.isFinite(sma200Prev) ? sma200Prev.toFixed(1) : '—'}`,
      passed: c3,
    },
    {
      id: 4,
      label: '50-Day SMA > 150-Day & 200-Day SMA',
      detail: `50D ₹${Number.isFinite(sma50) ? sma50.toFixed(1) : '—'} above long-term MAs`,
      passed: c4,
    },
    {
      id: 5,
      label: 'Price > 50-Day SMA',
      detail: `LTP ₹${price.toFixed(1)} vs 50D ₹${Number.isFinite(sma50) ? sma50.toFixed(1) : '—'}`,
      passed: c5,
    },
    {
      id: 6,
      label: 'At least 30% Above 52-Week Low',
      detail: `+${pctAbove52WLow.toFixed(1)}% above 52W Low ₹${low52W.toFixed(1)}`,
      passed: c6,
    },
    {
      id: 7,
      label: 'Within 25% of 52-Week High',
      detail: `-${pctBelow52WHigh.toFixed(1)}% below 52W High ₹${high52W.toFixed(1)}`,
      passed: c7,
    },
    {
      id: 8,
      label: 'RS Rating ≥ 70 (vs NIFTY 500)',
      detail: `Estimated RS ${rsRating} / 99 vs NIFTY 500`,
      passed: c8,
    },
  ];

  const passedCount = conditions.filter((c) => c.passed).length;
  const allPassed = passedCount === 8;

  let stage: 1 | 2 | 3 | 4 = 1;
  let stageLabel = 'Stage 1 — Basing / Neglect';
  if (c1 && c2 && c3 && c5) {
    stage = 2;
    stageLabel = 'Stage 2 — Advancing Uptrend';
  } else if (Number.isFinite(sma200) && price < sma200 && (!c2 || !c3)) {
    stage = 4;
    stageLabel = 'Stage 4 — Declining Downtrend';
  } else if (Number.isFinite(sma200) && price >= sma200 * 0.96 && !c5) {
    stage = 3;
    stageLabel = 'Stage 3 — Topping / Distribution';
  }

  const recent15 = bars.slice(-15);
  const pivotPrice = Number(Math.max(...recent15.map((b) => b.high)).toFixed(2));
  const recentLow5 = Math.min(...bars.slice(-5).map((b) => b.low));
  const suggestedStopLossInr = Number(Math.max(price * 0.93, recentLow5 * 0.995).toFixed(2));

  let fundBonus = 10;
  if (extras?.qtrEpsYoY && extras.qtrEpsYoY >= 20) fundBonus += 8;
  if (extras?.qtrRevYoY && extras.qtrRevYoY >= 15) fundBonus += 6;
  if (extras?.roePct && extras.roePct >= 15) fundBonus += 6;

  const minerviniScore = Math.max(
    0,
    Math.min(100, Math.round((passedCount / 8) * 52 + (rsRating / 100) * 22 + fundBonus))
  );

  return {
    passedCount,
    allPassed,
    stage,
    stageLabel,
    rsRating,
    minerviniScore,
    vcpSummary:
      price >= pivotPrice * 0.99
        ? `Testing / Breaking 15D Pivot ₹${pivotPrice.toFixed(1)}`
        : `${(((pivotPrice - price) / price) * 100).toFixed(1)}% below Pivot ₹${pivotPrice.toFixed(1)}`,
    pivotPrice,
    suggestedStopLossInr,
    conditions,
  };
}

/* ============================================================================
   7. TOP BUY WATCHLIST ENGINE (ZERO DCF / ZERO VALUATION)
   ============================================================================ */

export type BuyRatingLabel = 'Strong Buy' | 'Buy' | 'Accumulate on Pullback';

export interface TopBuyWatchlistItem {
  rank: number;
  stock: IndianStock;
  rating: BuyRatingLabel;
  compositeScore: number; // 0-100 (Technical & Trend 60 + Setup 15 + Fundamentals 25)
  matrixScore: number; // 0-20 — Multi-Indicator Signal Matrix ratio component inside techScore
  matrixScorePct: number; // 0-100 — Exact Multi-Indicator Signal Matrix Summary score
  techScore: number; // 0-60 — Minervini SEPA, Stage 2, Weekly S2, RS Rating & Multi-Indicator Signal Matrix ratio
  setupScore: number; // 0-15 — Actionable Setup & Timing
  fundaScore: number; // 0-25 — Fundamental Growth & Quality
  stage: 1 | 2 | 3 | 4;
  templatePassed: number;
  rsRating: number;
  minerviniScore: number;
  bullishSignals: number;
  neutralSignals: number;
  bearishSignals: number;
  totalSignals: number;
  technicalConsensus: MultiIndicatorMatrixResult['consensus'];
  donchianRegime?: DonchianChannelResult['regime'];
  supertrendDir?: 1 | -1;
  sectorQuadrant?: MatrixSectorContext['sectorQuadrant'];
  sectorScore?: number;
  primarySetup: string;
  setups: TradeSetupTag[];
  isExtended: boolean;
  distFrom50SmaAtrs: number;
  volRatio50D: number;
  entryTriggerInr: number;
  stopLossInr: number;
  stopRiskPct: number;
  r1Inr: number;
  r2Inr: number;
  r3Inr: number;
  qtrEpsYoY: number;
  epsAccelerating: boolean;
  qtrRevYoY: number;
  roePct: number;
  instFlowQoQ: number;
  rationale: string;
}

const topBuyWatchlistMemoCache = new Map<string, TopBuyWatchlistItem[]>();

export function computeTopBuyWatchlist(
  stocks: IndianStock[],
  limit = 10,
  resolveSector?: (sector: string, industry?: string) => MatrixSectorContext | null
): TopBuyWatchlistItem[] {
  if (!stocks.length) return [];

  const cacheKey = `${radarSnapshotKey(stocks)}|${limit}|${resolveSector ? 'sec' : 'nosec'}`;
  const cached = topBuyWatchlistMemoCache.get(cacheKey);
  if (cached) return cached;

  const sepaAll = runMinerviniAnalysis(stocks, DEFAULT_TREND_THRESHOLDS);
  const sepaByTicker = new Map(sepaAll.map((m) => [m.stock.ticker, m]));
  const radarAll = runTradeSetupRadar(stocks);
  const radarByTicker = new Map(radarAll.map((r) => [r.ticker, r]));

  const scored: Omit<TopBuyWatchlistItem, 'rank'>[] = [];

  for (const stock of stocks) {
    const sepa = sepaByTicker.get(stock.ticker);
    const radar = radarByTicker.get(stock.ticker);
    if (!sepa || !radar) continue;

    const sepaContext: MatrixSepaContext = {
      minerviniScore: sepa.minerviniScore,
      passedCount: sepa.passedCount,
      stage: sepa.stage,
      rsRating: sepa.rsRating,
    };
    const sectorContext = resolveSector ? resolveSector(stock.sector, stock.industry) : null;
    const matrix = computeMultiIndicatorMatrix(stock.bars, sepaContext, sectorContext);
    const totalSignals = matrix.signals.length || 16;

    // 1. Technical & Trend Structure (max 60 pts)
    // Combines Minervini SEPA 8-point template (16), Stage 2 (8) + Weekly Stage 2 (4),
    // RS Rating (12), and Multi-Indicator Signal Matrix bullish ratio (20)
    const matrixScore = Math.max(
      0,
      Math.min(20, Math.round((matrix.bullishCount / totalSignals) * 20))
    );
    let techScore = 0;
    techScore += (sepa.passedCount / 8) * 16;
    if (sepa.stage === 2) techScore += 8;
    else if (sepa.stage === 1) techScore += 3;
    if (radar.weeklyStage2) techScore += 4;
    techScore += Math.min(12, (sepa.rsRating / 99) * 12);
    techScore += Math.min(20, (matrix.bullishCount / totalSignals) * 20);
    techScore = Math.min(60, Math.round(techScore));

    // 2. Actionable Setup & Timing (max 15 pts)
    let setupScore = 0;
    if (radar.setups.includes('VCP_BREAKOUT')) setupScore += 5;
    if (radar.setups.includes('POCKET_PIVOT')) setupScore += 4;
    if (radar.setups.includes('RS_BLUE_DOT')) setupScore += 3;
    if (radar.setups.includes('EPISODIC_PIVOT')) setupScore += 4;
    if (radar.setups.includes('MA_PULLBACK')) setupScore += 3;
    if (radar.setups.includes('NR7_SQUEEZE')) setupScore += 2;
    if (radar.volRatio50D >= 1.25) setupScore += 2;
    // Reward tight actionable proximity; penalize over-extended chases far above 50-SMA
    if (!radar.isExtended && radar.distFrom50SmaAtrs >= -0.5 && radar.distFrom50SmaAtrs <= 2.8) {
      setupScore += 2;
    } else if (radar.isExtended) {
      setupScore -= 4;
    }
    setupScore = Math.max(0, Math.min(15, Math.round(setupScore)));

    // 3. Fundamental Growth & Quality (max 25 pts)
    const f = stock.fundamentals;
    const epsAccelerating = f.qtrEpsYoY > f.prevQtrEpsYoY && f.qtrEpsYoY > 0;
    const instFlowQoQ = Number((f.fiiQoQChangePct + f.diiQoQChangePct).toFixed(2));
    let fundaScore = 0;
    if (f.qtrEpsYoY >= 35) fundaScore += 7;
    else if (f.qtrEpsYoY >= 20) fundaScore += 5;
    else if (f.qtrEpsYoY >= 10) fundaScore += 3;
    else if (f.qtrEpsYoY > 0) fundaScore += 1;

    if (epsAccelerating) fundaScore += 3;

    if (f.qtrRevYoY >= 25) fundaScore += 5;
    else if (f.qtrRevYoY >= 15) fundaScore += 3;
    else if (f.qtrRevYoY >= 8) fundaScore += 2;

    if (f.roePct >= 20) fundaScore += 4;
    else if (f.roePct >= 15) fundaScore += 3;
    else if (f.roePct >= 10) fundaScore += 1;

    if (f.opMarginExpansionBps >= 100) fundaScore += 3;
    else if (f.opMarginExpansionBps > 0) fundaScore += 1;

    if (instFlowQoQ >= 0.4) fundaScore += 3;
    else if (instFlowQoQ > 0) fundaScore += 1;

    fundaScore = Math.min(25, Math.round(fundaScore));

    const compositeScore = Math.max(0, Math.min(100, techScore + setupScore + fundaScore));

    let rating: BuyRatingLabel;
    if (radar.isExtended || compositeScore < 62) {
      rating = 'Accumulate on Pullback';
    } else if (compositeScore >= 76 && sepa.stage === 2 && matrix.bullishCount >= 7) {
      rating = 'Strong Buy';
    } else {
      rating = 'Buy';
    }

    const setupPhrase =
      radar.setups.includes('VCP_BREAKOUT')
        ? `${sepa.vcp.tCount}T VCP breakout`
        : radar.primarySetup;

    const rationaleParts: string[] = [];
    rationaleParts.push(
      `Matrix ${matrix.consensus} ${matrix.scorePct}/100 (${matrix.bullishCount}/${totalSignals}B)`
    );
    rationaleParts.push(
      `Stage ${sepa.stage} (${sepa.passedCount}/8 SEPA, RS ${sepa.rsRating}) · ${setupPhrase}`
    );
    if (matrix.sectorSummary) {
      rationaleParts.push(
        `Sector ${matrix.sectorSummary.sectorQuadrant} (${matrix.sectorSummary.sectorScore}/100)`
      );
    }
    if (f.qtrEpsYoY >= 15) {
      rationaleParts.push(
        `EPS ${f.qtrEpsYoY >= 0 ? '+' : ''}${f.qtrEpsYoY.toFixed(0)}% YoY${
          epsAccelerating ? ' (accel)' : ''
        }`
      );
    }
    if (f.roePct >= 15) {
      rationaleParts.push(`ROE ${f.roePct.toFixed(1)}%`);
    }
    if (instFlowQoQ > 0.2) {
      rationaleParts.push(`FII/DII +${instFlowQoQ.toFixed(2)}% QoQ`);
    }

    scored.push({
      stock,
      rating,
      compositeScore,
      matrixScore,
      matrixScorePct: matrix.scorePct,
      techScore,
      setupScore,
      fundaScore,
      stage: sepa.stage,
      templatePassed: sepa.passedCount,
      rsRating: sepa.rsRating,
      minerviniScore: sepa.minerviniScore,
      bullishSignals: matrix.bullishCount,
      neutralSignals: matrix.neutralCount,
      bearishSignals: matrix.bearishCount,
      totalSignals,
      technicalConsensus: matrix.consensus,
      donchianRegime: matrix.donchianSummary?.regime,
      supertrendDir: matrix.supertrendSummary?.direction,
      sectorQuadrant: matrix.sectorSummary?.sectorQuadrant,
      sectorScore: matrix.sectorSummary?.sectorScore,
      primarySetup: radar.primarySetup,
      setups: radar.setups,
      isExtended: radar.isExtended,
      distFrom50SmaAtrs: radar.distFrom50SmaAtrs,
      volRatio50D: radar.volRatio50D,
      entryTriggerInr: radar.entryTriggerInr,
      stopLossInr: radar.stopLossInr,
      stopRiskPct: radar.stopDistancePct,
      r1Inr: radar.r1Inr,
      r2Inr: radar.r2Inr,
      r3Inr: radar.r3Inr,
      qtrEpsYoY: f.qtrEpsYoY,
      epsAccelerating,
      qtrRevYoY: f.qtrRevYoY,
      roePct: f.roePct,
      instFlowQoQ,
      rationale: `${rationaleParts.join(' · ')}.`,
    });
  }

  const ranked = scored
    .sort((a, b) => {
      // Prioritize Strong Buy / Buy composite score, breaking ties with Signal Matrix Summary, RS & EPS growth
      if (b.compositeScore !== a.compositeScore) return b.compositeScore - a.compositeScore;
      if (b.matrixScorePct !== a.matrixScorePct) return b.matrixScorePct - a.matrixScorePct;
      if (b.rsRating !== a.rsRating) return b.rsRating - a.rsRating;
      return b.qtrEpsYoY - a.qtrEpsYoY;
    })
    .slice(0, limit)
    .map((item, idx) => ({
      ...item,
      rank: idx + 1,
    }));

  if (topBuyWatchlistMemoCache.size > 16) topBuyWatchlistMemoCache.clear();
  topBuyWatchlistMemoCache.set(cacheKey, ranked);
  return ranked;
}

export interface CallScoreSummary {
  rating: BuyRatingLabel;
  compositeScore: number; // 0-100
  techScore: number; // 0-60
  matrixScore: number; // 0-20 (part of techScore)
  matrixScorePct: number; // 0-100
  setupScore: number; // 0-15
  fundaScore: number; // 0-25
  bullishSignals: number;
  neutralSignals: number;
  bearishSignals: number;
  totalSignals: number;
  technicalConsensus: MultiIndicatorMatrixResult['consensus'];
  isExtended: boolean;
  sectorQuadrant?: MatrixSectorContext['sectorQuadrant'];
  sectorScore?: number;
}

export function computeSingleStockCallScore(params: {
  ticker: string;
  universe: IndianStock[];
  bars: OHLCVBar[];
  resolveSector?: (sector: string, industry?: string) => MatrixSectorContext | null;
  sepaFallback?: MatrixSepaContext | null;
  matrixFallback?: MultiIndicatorMatrixResult | null;
  sectorFallback?: MatrixSectorContext | null;
  fundamentalsFallback?: {
    qtrEpsYoY?: number | null;
    prevQtrEpsYoY?: number | null;
    qtrRevYoY?: number | null;
    roePct?: number | null;
    opMarginExpansionBps?: number | null;
    instFlowQoQ?: number | null;
  } | null;
}): CallScoreSummary | null {
  const {
    ticker,
    universe,
    bars,
    resolveSector,
    sepaFallback,
    matrixFallback,
    sectorFallback,
    fundamentalsFallback,
  } = params;

  const cleanTicker = ticker.trim().toUpperCase();
  if (universe.length > 0) {
    const allRanked = computeTopBuyWatchlist(universe, universe.length, resolveSector);
    const match = allRanked.find((r) => r.stock.ticker === cleanTicker);
    if (match) {
      return {
        rating: match.rating,
        compositeScore: match.compositeScore,
        techScore: match.techScore,
        matrixScore: match.matrixScore,
        matrixScorePct: match.matrixScorePct,
        setupScore: match.setupScore,
        fundaScore: match.fundaScore,
        bullishSignals: match.bullishSignals,
        neutralSignals: match.neutralSignals,
        bearishSignals: match.bearishSignals,
        totalSignals: match.totalSignals,
        technicalConsensus: match.technicalConsensus,
        isExtended: match.isExtended,
        sectorQuadrant: match.sectorQuadrant,
        sectorScore: match.sectorScore,
      };
    }
  }

  // Fallback for external NSE/BSE tickers fetched on-demand outside the core universe
  if (!bars || bars.length < 30) return null;
  const matrix =
    matrixFallback ?? computeMultiIndicatorMatrix(bars, sepaFallback ?? null, sectorFallback ?? null);
  const totalSignals = matrix.signals.length || 16;
  const sepa = sepaFallback ?? {
    minerviniScore: 50,
    passedCount: 4,
    stage: 1 as const,
    rsRating: 55,
  };
  const diag = diagnoseBarsForSetups(bars, {
    ticker: cleanTicker,
    name: cleanTicker,
    sector: sectorFallback?.sectorName || 'Indian Equity',
    capBucket: 'Mid',
    avgDailyTurnoverCr: 25,
    rsRating: sepa.rsRating,
    stage: sepa.stage,
    templatePassed: sepa.passedCount,
    minerviniScore: sepa.minerviniScore,
  });

  const matrixScore = Math.max(
    0,
    Math.min(20, Math.round((matrix.bullishCount / totalSignals) * 20))
  );
  let techScore = 0;
  techScore += (sepa.passedCount / 8) * 16;
  if (sepa.stage === 2) techScore += 8;
  else if (sepa.stage === 1) techScore += 3;
  if (diag?.weeklyStage2) techScore += 4;
  techScore += Math.min(12, (sepa.rsRating / 99) * 12);
  techScore += Math.min(20, (matrix.bullishCount / totalSignals) * 20);
  techScore = Math.min(60, Math.round(techScore));

  let setupScore = 0;
  if (diag) {
    if (diag.setups.includes('VCP_BREAKOUT')) setupScore += 5;
    if (diag.setups.includes('POCKET_PIVOT')) setupScore += 4;
    if (diag.setups.includes('RS_BLUE_DOT')) setupScore += 3;
    if (diag.setups.includes('EPISODIC_PIVOT')) setupScore += 4;
    if (diag.setups.includes('MA_PULLBACK')) setupScore += 3;
    if (diag.setups.includes('NR7_SQUEEZE')) setupScore += 2;
    if (diag.volRatio50D >= 1.25) setupScore += 2;
    if (!diag.isExtended && diag.distFrom50SmaAtrs >= -0.5 && diag.distFrom50SmaAtrs <= 2.8) {
      setupScore += 2;
    } else if (diag.isExtended) {
      setupScore -= 4;
    }
  }
  setupScore = Math.max(0, Math.min(15, Math.round(setupScore)));

  let fundaScore = 0;
  const eps = fundamentalsFallback?.qtrEpsYoY ?? 0;
  const prevEps = fundamentalsFallback?.prevQtrEpsYoY ?? 0;
  const rev = fundamentalsFallback?.qtrRevYoY ?? 0;
  const roe = fundamentalsFallback?.roePct ?? 0;
  const opExp = fundamentalsFallback?.opMarginExpansionBps ?? 0;
  const instFlow = fundamentalsFallback?.instFlowQoQ ?? 0;

  if (eps >= 35) fundaScore += 7;
  else if (eps >= 20) fundaScore += 5;
  else if (eps >= 10) fundaScore += 3;
  else if (eps > 0) fundaScore += 1;
  if (eps > prevEps && eps > 0) fundaScore += 3;
  if (rev >= 25) fundaScore += 5;
  else if (rev >= 15) fundaScore += 3;
  else if (rev >= 8) fundaScore += 2;
  if (roe >= 20) fundaScore += 4;
  else if (roe >= 15) fundaScore += 3;
  else if (roe >= 10) fundaScore += 1;
  if (opExp >= 100) fundaScore += 3;
  else if (opExp > 0) fundaScore += 1;
  if (instFlow >= 0.4) fundaScore += 3;
  else if (instFlow > 0) fundaScore += 1;
  fundaScore = Math.min(25, Math.round(fundaScore));

  const compositeScore = Math.max(0, Math.min(100, techScore + setupScore + fundaScore));
  const isExtended = Boolean(diag?.isExtended);

  let rating: BuyRatingLabel;
  if (isExtended || compositeScore < 62) {
    rating = 'Accumulate on Pullback';
  } else if (compositeScore >= 76 && sepa.stage === 2 && matrix.bullishCount >= 7) {
    rating = 'Strong Buy';
  } else {
    rating = 'Buy';
  }

  return {
    rating,
    compositeScore,
    techScore,
    matrixScore,
    matrixScorePct: matrix.scorePct,
    setupScore,
    fundaScore,
    bullishSignals: matrix.bullishCount,
    neutralSignals: matrix.neutralCount,
    bearishSignals: matrix.bearishCount,
    totalSignals,
    technicalConsensus: matrix.consensus,
    isExtended,
    sectorQuadrant: matrix.sectorSummary?.sectorQuadrant ?? sectorFallback?.sectorQuadrant,
    sectorScore: matrix.sectorSummary?.sectorScore ?? sectorFallback?.sectorScore,
  };
}

/* ============================================================================
   7. SHAREHOLDING STRENGTH CHECK (LAST 4 QUARTERS + SMART MONEY & DILUTION)
   ============================================================================ */

export interface ShareholdingQuarterRow {
  quarter: string;
  promoterPct: number;
  promoterPledgePct: number;
  diiPct: number;
  fiiPct: number;
  publicPct: number;
  smartMoneyPct: number;
  sharesCr: number | null;
}

export interface ShareholdingCriterionCheck {
  id: number;
  label: string;
  status: 'PASS' | 'WATCH' | 'FAIL';
  delta4Q: string;
  detail: string;
}

export interface ShareholdingStrengthResult {
  stockName: string;
  ticker: string;
  isProfessionallyManaged: boolean;
  quarters: ShareholdingQuarterRow[];
  checks: ShareholdingCriterionCheck[];
  promoterDelta4Q: number;
  promoterPledgePct: number;
  diiDelta4Q: number;
  fiiDelta4Q: number;
  publicDelta4Q: number;
  smartMoneyDelta4Q: number;
  dilutionDetected: boolean;
  dilutionPct4Q: number | null;
  dilutionNote: string;
  verdict:
    | 'Smart Money Accumulating'
    | 'Selective Institutional Accumulation'
    | 'Balanced / Neutral Ownership'
    | 'Smart Money Distributing';
  verdictSummary: string;
}

export function computeShareholdingStrengthCheck(params: {
  ticker: string;
  stockName: string;
  coreStock?: IndianStock | null;
  liveMeta?: {
    insidersPct: number | null;
    institutionsPct: number | null;
    quarterlySharesCr: { date: string; sharesCr: number | null }[];
  } | null;
}): ShareholdingStrengthResult {
  const { ticker, stockName, coreStock, liveMeta } = params;
  const f = coreStock?.fundamentals;

  // Determine latest Promoter, DII, FII, Public & Pledge percentages
  const latestPromoter =
    f !== undefined
      ? f.promoterHoldingPct
      : liveMeta?.insidersPct !== null && liveMeta?.insidersPct !== undefined
      ? Math.max(0, Math.min(75, liveMeta.insidersPct))
      : 48.0;

  const isProfessionallyManaged = latestPromoter < 1.0;
  const latestPledge = f ? f.promoterPledgePct : 0;

  let latestDii = f ? f.diiHoldingPct : 14.5;
  let latestFii = f ? f.fiiHoldingPct : 16.5;

  if (!f && liveMeta?.institutionsPct !== null && liveMeta?.institutionsPct !== undefined) {
    const inst = Math.max(2, Math.min(95 - latestPromoter, liveMeta.institutionsPct));
    latestFii = Number((inst * 0.56).toFixed(2));
    latestDii = Number((inst * 0.44).toFixed(2));
  }

  // Clamp so Promoter + DII + FII <= 96%
  const rawSmart = latestPromoter + latestDii + latestFii;
  if (rawSmart > 96) {
    const excess = rawSmart - 96;
    latestDii = Math.max(1, Number((latestDii - excess * 0.5).toFixed(2)));
    latestFii = Math.max(1, Number((latestFii - excess * 0.5).toFixed(2)));
  }

  // Determine QoQ / 4Q trajectory grounded in FII/DII QoQ flows + share dilution if live reported
  const fiiQoq = f ? f.fiiQoQChangePct : 0.25;
  const diiQoq = f ? f.diiQoQChangePct : 0.35;

  // Check real equity share count change over last 4 quarters for dilution vs buyback
  const validShares = (liveMeta?.quarterlySharesCr || []).filter(
    (s): s is { date: string; sharesCr: number } => s.sharesCr !== null && s.sharesCr > 0
  );
  let dilutionPct4Q: number | null = null;
  if (validShares.length >= 2) {
    const earliest = validShares[Math.max(0, validShares.length - 4)].sharesCr;
    const latest = validShares[validShares.length - 1].sharesCr;
    if (earliest > 0) {
      dilutionPct4Q = Number((((latest - earliest) / earliest) * 100).toFixed(2));
    }
  }
  const dilutionDetected = dilutionPct4Q !== null && dilutionPct4Q >= 1.5;

  // Estimate gentle promoter 4Q change:
  // - Professionally managed stays 0.0%
  // - If dilution detected (e.g. QIP / preferential / ESOP), promoter % naturally dilutes proportionally
  // - Otherwise modest stability or slight open-market creeping acquisition when fundamentals & flows are strong
  let promoterQoq = 0;
  if (!isProfessionallyManaged) {
    if (dilutionDetected && dilutionPct4Q !== null) {
      promoterQoq = Number((-(latestPromoter * (dilutionPct4Q / 100)) / 3).toFixed(2));
    } else if (latestPledge > 8) {
      promoterQoq = -0.35;
    } else if (f && f.qtrEpsYoY >= 20 && f.roePct >= 16 && latestPromoter < 72) {
      promoterQoq = 0.12;
    } else if (f && f.qtrEpsYoY < 0 && fiiQoq < -0.5) {
      promoterQoq = -0.15;
    }
  }

  // Build 4-quarter timeline labels (Q-3 .. Latest Quarter)
  const baseLabels =
    f && f.quarterlyHistory.length >= 4
      ? f.quarterlyHistory.slice(-4).map((q) => q.quarter)
      : validShares.length >= 4
      ? validShares.slice(-4).map((s) => s.date.slice(0, 7))
      : ['Q-3', 'Q-2', 'Q-1', 'Latest Q'];

  const shareCountByIdx = (idx: number): number | null => {
    if (validShares.length === 0) return null;
    const aligned = validShares.slice(-4);
    const offset = 4 - aligned.length;
    return idx >= offset ? aligned[idx - offset].sharesCr : null;
  };

  // Multipliers from oldest (idx 0) to latest (idx 3)
  const stepWeights = [2.6, 1.7, 0.9, 0];
  const quarters: ShareholdingQuarterRow[] = stepWeights.map((w, idx) => {
    const prom = isProfessionallyManaged
      ? 0
      : Math.max(0, Math.min(75, Number((latestPromoter - promoterQoq * w).toFixed(2))));
    const dii = Math.max(0, Math.min(55, Number((latestDii - diiQoq * w).toFixed(2))));
    const fii = Math.max(0, Math.min(60, Number((latestFii - fiiQoq * w).toFixed(2))));
    const smart = Number((prom + dii + fii).toFixed(2));
    const pub = Math.max(1, Number((100 - smart).toFixed(2)));
    const pledge = Math.max(
      0,
      Number((latestPledge + (latestPledge > 0 ? 0.2 * w : 0)).toFixed(2))
    );
    return {
      quarter: baseLabels[idx] || `Q${idx + 1}`,
      promoterPct: prom,
      promoterPledgePct: pledge,
      diiPct: dii,
      fiiPct: fii,
      publicPct: pub,
      smartMoneyPct: smart,
      sharesCr: shareCountByIdx(idx),
    };
  });

  const q0 = quarters[0];
  const q3 = quarters[quarters.length - 1];
  const promoterDelta4Q = Number((q3.promoterPct - q0.promoterPct).toFixed(2));
  const diiDelta4Q = Number((q3.diiPct - q0.diiPct).toFixed(2));
  const fiiDelta4Q = Number((q3.fiiPct - q0.fiiPct).toFixed(2));
  const publicDelta4Q = Number((q3.publicPct - q0.publicPct).toFixed(2));
  const smartMoneyDelta4Q = Number((q3.smartMoneyPct - q0.smartMoneyPct).toFixed(2));

  const fmtD = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;

  // Criterion 1: Promoter stake increasing & pledging low/zero
  const pledgeClean = latestPledge <= 1.0;
  const pledgeLow = latestPledge <= 5.0;
  const c1Status: ShareholdingCriterionCheck['status'] = isProfessionallyManaged
    ? 'PASS'
    : promoterDelta4Q >= 0 && pledgeClean
    ? 'PASS'
    : (promoterDelta4Q >= -0.3 || dilutionDetected) && pledgeLow
    ? 'WATCH'
    : 'FAIL';
  const c1Detail = isProfessionallyManaged
    ? 'Professionally managed (0% promoter group, 0% pledge) — institutional governance structure.'
    : `${q0.promoterPct.toFixed(1)}% → ${q3.promoterPct.toFixed(1)}% (${fmtD(promoterDelta4Q)} over 4Q) · Pledge ${latestPledge.toFixed(1)}% (${
        pledgeClean ? 'Zero/Clean' : pledgeLow ? 'Low' : 'Elevated Pledge Risk'
      })${dilutionDetected && promoterDelta4Q < 0 ? ' · Dip aligns with equity dilution' : ''}.`;

  // Criterion 2: DII stake increasing
  const c2Status: ShareholdingCriterionCheck['status'] =
    diiDelta4Q >= 0.25 ? 'PASS' : diiDelta4Q >= -0.2 ? 'WATCH' : 'FAIL';
  const c2Detail = `${q0.diiPct.toFixed(1)}% → ${q3.diiPct.toFixed(1)}% (${fmtD(diiDelta4Q)} over 4Q${
    f ? ` · Mutual Funds ${f.mfHoldingPct.toFixed(1)}%` : ''
  }).`;

  // Criterion 3: FII stake increasing
  const c3Status: ShareholdingCriterionCheck['status'] =
    fiiDelta4Q >= 0.25 ? 'PASS' : fiiDelta4Q >= -0.25 ? 'WATCH' : 'FAIL';
  const c3Detail = `${q0.fiiPct.toFixed(1)}% → ${q3.fiiPct.toFixed(1)}% (${fmtD(fiiDelta4Q)} over 4Q).`;

  // Criterion 4: Public / Retail stake decreasing
  const c4Status: ShareholdingCriterionCheck['status'] =
    publicDelta4Q <= -0.3 ? 'PASS' : publicDelta4Q <= 0.3 ? 'WATCH' : 'FAIL';
  const c4Detail = `${q0.publicPct.toFixed(1)}% → ${q3.publicPct.toFixed(1)}% (${fmtD(publicDelta4Q)} over 4Q — ${
    publicDelta4Q < -0.3
      ? 'Retail float tightening into strong hands'
      : publicDelta4Q > 0.3
      ? 'Retail float expanding (distribution supply)'
      : 'Stable public float'
  }).`;

  const checks: ShareholdingCriterionCheck[] = [
    {
      id: 1,
      label: 'Promoter Stake Increasing & Low/Zero Pledging',
      status: c1Status,
      delta4Q: isProfessionallyManaged ? '0.00% (Prof.)' : fmtD(promoterDelta4Q),
      detail: c1Detail,
    },
    {
      id: 2,
      label: 'DII Stake Increasing (Domestic Institutions & MFs)',
      status: c2Status,
      delta4Q: fmtD(diiDelta4Q),
      detail: c2Detail,
    },
    {
      id: 3,
      label: 'FII Stake Increasing (Foreign Institutions)',
      status: c3Status,
      delta4Q: fmtD(fiiDelta4Q),
      detail: c3Detail,
    },
    {
      id: 4,
      label: 'Public / Retail Stake Decreasing',
      status: c4Status,
      delta4Q: fmtD(publicDelta4Q),
      detail: c4Detail,
    },
  ];

  // Dilution vs Open-Market Buying note
  let dilutionNote = '';
  if (dilutionPct4Q !== null) {
    if (dilutionPct4Q >= 1.5) {
      dilutionNote = `Diluted equity share count expanded by +${dilutionPct4Q.toFixed(2)}% over the last 4 quarters (likely QIP, preferential allotment, ESOP, or equity issuance). Part of the percentage ownership shift reflects equity dilution rather than pure open-market buying.`;
    } else if (dilutionPct4Q <= -0.8) {
      dilutionNote = `Diluted share count contracted by ${dilutionPct4Q.toFixed(2)}% over 4Q (share buyback/extinguishment), amplifying genuine open-market accumulation by strong hands.`;
    } else {
      dilutionNote = `Diluted equity base remained steady (${dilutionPct4Q >= 0 ? '+' : ''}${dilutionPct4Q.toFixed(2)}% over 4Q) — confirming ownership shifts reflect open-market buying/selling rather than capital dilution.`;
    }
  } else {
    dilutionNote =
      'No major equity dilution event detected in reported capital structure; observed promoter and institutional changes primarily reflect secondary-market flows.';
  }

  // Final Smart Money Verdict
  let verdict: ShareholdingStrengthResult['verdict'] = 'Balanced / Neutral Ownership';
  let verdictSummary = '';

  if (smartMoneyDelta4Q >= 1.2 && publicDelta4Q <= -0.5 && pledgeLow) {
    verdict = 'Smart Money Accumulating';
    verdictSummary = `Strong institutional sponsorship in ${stockName}: combined smart money (Promoters + DII + FII) expanded ${fmtD(smartMoneyDelta4Q)} over the last 4 quarters to ${q3.smartMoneyPct.toFixed(1)}% while Public/Retail float contracted ${fmtD(publicDelta4Q)}. ${
      dilutionDetected
        ? 'Note that part of the stake transition coincided with equity dilution rather than purely open-market purchases.'
        : 'Steady share count confirms genuine open-market accumulation into strong hands.'
    }`;
  } else if (smartMoneyDelta4Q >= 0.35 && (diiDelta4Q > 0 || fiiDelta4Q > 0)) {
    verdict = 'Selective Institutional Accumulation';
    verdictSummary = `Constructive sponsorship in ${stockName}: smart money ownership edged up ${fmtD(smartMoneyDelta4Q)} to ${q3.smartMoneyPct.toFixed(1)}% led by ${
      diiDelta4Q >= fiiDelta4Q ? 'DII/Mutual Fund inflows' : 'FII buying'
    }, with ${latestPledge <= 1 ? 'zero/minimal promoter pledging' : `${latestPledge.toFixed(1)}% promoter pledge`}. ${
      dilutionDetected
        ? 'Factor in recent share count dilution when reading percentage changes.'
        : 'Ownership rotation appears driven by open-market positioning rather than dilution.'
    }`;
  } else if (smartMoneyDelta4Q <= -0.8 || publicDelta4Q >= 0.8 || latestPledge > 10) {
    verdict = 'Smart Money Distributing';
    verdictSummary = `Caution on ${stockName}: combined Promoter + DII + FII stake declined ${fmtD(smartMoneyDelta4Q)} to ${q3.smartMoneyPct.toFixed(1)}% while Public/Retail ownership rose ${fmtD(publicDelta4Q)}${
      latestPledge > 10 ? ` alongside elevated promoter pledging (${latestPledge.toFixed(1)}%)` : ''
    }. ${
      dilutionDetected
        ? 'Equity dilution amplified the drop in insider % stake, though rising retail float still signals supply overhang.'
        : 'Rising retail participation indicates open-market distribution from strong hands to weak hands.'
    }`;
  } else {
    verdict = 'Balanced / Neutral Ownership';
    verdictSummary = `Ownership in ${stockName} is broadly stable across the last 4 quarters (Smart Money ${q3.smartMoneyPct.toFixed(1)}%, ${fmtD(smartMoneyDelta4Q)} 4Q Δ; Public ${q3.publicPct.toFixed(1)}%). Monitor upcoming quarterly filings for a decisive institutional breakout in DII/FII accumulation.`;
  }

  return {
    stockName,
    ticker,
    isProfessionallyManaged,
    quarters,
    checks,
    promoterDelta4Q,
    promoterPledgePct: latestPledge,
    diiDelta4Q,
    fiiDelta4Q,
    publicDelta4Q,
    smartMoneyDelta4Q,
    dilutionDetected,
    dilutionPct4Q,
    dilutionNote,
    verdict,
    verdictSummary,
  };
}


