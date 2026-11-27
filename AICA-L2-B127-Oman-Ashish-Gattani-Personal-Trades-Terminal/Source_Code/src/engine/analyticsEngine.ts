import { BENCHMARKS } from '../data/indianMarketData';
import {
  BreakoutScanConfig,
  BreakoutScanResult,
  IndianStock,
  MarketStage,
  MinerviniAnalysis,
  OHLCVBar,
  TrendConditionCheck,
  TrendTemplateThresholds,
  VcpAnalysis,
  VcpContraction,
} from '../types/market';

export function computeSmaSeries(values: number[], period: number): number[] {
  const out = new Array<number>(values.length).fill(NaN);
  if (period <= 0) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function computeEmaSeries(values: number[], period: number): number[] {
  const out = new Array<number>(values.length).fill(NaN);
  if (period <= 0 || values.length === 0) return out;
  const k = 2 / (period + 1);
  let ema = values[0];
  out[0] = ema;
  for (let i = 1; i < values.length; i++) {
    ema = values[i] * k + ema * (1 - k);
    out[i] = ema;
  }
  return out;
}

export function computeRsiSeries(values: number[], period = 14): number[] {
  const out = new Array<number>(values.length).fill(NaN);
  if (values.length <= period) return out;
  let avgGain = 0;
  let avgLoss = 0;
  for (let i = 1; i <= period; i++) {
    const diff = values[i] - values[i - 1];
    if (diff >= 0) avgGain += diff;
    else avgLoss -= diff;
  }
  avgGain /= period;
  avgLoss /= period;
  out[period] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  for (let i = period + 1; i < values.length; i++) {
    const diff = values[i] - values[i - 1];
    const gain = diff > 0 ? diff : 0;
    const loss = diff < 0 ? -diff : 0;
    avgGain = (avgGain * (period - 1) + gain) / period;
    avgLoss = (avgLoss * (period - 1) + loss) / period;
    out[i] = avgLoss === 0 ? 100 : 100 - 100 / (1 + avgGain / avgLoss);
  }
  return out;
}

export function computeAtrSeries(bars: OHLCVBar[], period = 14): number[] {
  const out = new Array<number>(bars.length).fill(NaN);
  if (bars.length <= period) return out;
  const tr = bars.map((b, i) => {
    if (i === 0) return b.high - b.low;
    const prevClose = bars[i - 1].close;
    return Math.max(b.high - b.low, Math.abs(b.high - prevClose), Math.abs(b.low - prevClose));
  });
  let sum = 0;
  for (let i = 0; i < period; i++) sum += tr[i];
  let atr = sum / period;
  out[period - 1] = atr;
  for (let i = period; i < bars.length; i++) {
    atr = (atr * (period - 1) + tr[i]) / period;
    out[i] = atr;
  }
  return out;
}

export function computeStdevSeries(values: number[], period = 20): number[] {
  const out = new Array<number>(values.length).fill(NaN);
  for (let i = period - 1; i < values.length; i++) {
    let mean = 0;
    for (let j = i - period + 1; j <= i; j++) mean += values[j];
    mean /= period;
    let sq = 0;
    for (let j = i - period + 1; j <= i; j++) {
      const d = values[j] - mean;
      sq += d * d;
    }
    out[i] = Math.sqrt(sq / period);
  }
  return out;
}

/**
 * 1. 52-WEEK HIGH BREAKOUT SCANNER (Variable Lookback N months + Recent Breakout Window)
 * Condition:
 *   Within the recent breakout window (default last 5 trading sessions / This Week, configurable 1–20D),
 *   a session's close (or high) broke above the prior 52-week high (past ~252 trading sessions),
 *   AND the stock had NOT made a new 52-week high during the preceding N months (N * 21 sessions)
 *   before that breakout (or the prior 52W peak occurred at least N months earlier).
 */
export function run52WeekBreakoutScanner(
  stocks: IndianStock[],
  config: BreakoutScanConfig
): BreakoutScanResult[] {
  const lookbackBars = Math.max(21, Math.round(config.lookbackMonths * 21));
  const recentWindow = Math.max(1, Math.min(25, Math.round(config.recentBreakoutDays ?? 5)));
  const results: BreakoutScanResult[] = [];

  for (const stock of stocks) {
    if (stock.latestClose < config.minPriceInr) continue;
    if (stock.avgDailyTurnoverCr < config.minTurnoverCr) continue;
    if (config.capBucket !== 'All' && stock.capBucket !== config.capBucket) continue;
    if (config.sector !== 'All' && stock.sector !== config.sector) continue;

    const bars = stock.bars;
    const n = bars.length;
    // Allow stocks with ~1Y+ history (220+ sessions) so extended 18M NSE equities qualify cleanly
    if (n < 220) continue;

    // Scan backwards from the latest session across the recent window to locate the freshest qualifying 52W breakout
    let matched: BreakoutScanResult | null = null;
    const earliestCandidate = Math.max(210, n - recentWindow);

    for (let idx = n - 1; idx >= earliestCandidate; idx--) {
      const b = bars[idx];
      const metric = config.priceBasis === 'close' ? b.close : b.high;

      // Prior 52-week window strictly before breakout bar `idx`
      const winLen = Math.min(252, idx);
      const winStart = idx - winLen;
      let prior52WHigh = -Infinity;
      let prior52WHighIdx = winStart;
      for (let i = winStart; i < idx; i++) {
        const m = config.priceBasis === 'close' ? bars[i].close : bars[i].high;
        if (m > prior52WHigh) {
          prior52WHigh = m;
          prior52WHighIdx = i;
        }
      }

      if (!(prior52WHigh > 0) || metric <= prior52WHigh) continue;

      // Full-history prior All-Time High strictly before breakout bar `idx`
      let priorAllTimeHigh = prior52WHigh;
      let priorAthIdx = prior52WHighIdx;
      for (let i = 0; i < idx; i++) {
        const m = config.priceBasis === 'close' ? bars[i].close : bars[i].high;
        if (m > priorAllTimeHigh) {
          priorAllTimeHigh = m;
          priorAthIdx = i;
        }
      }
      const isAllTimeHighBreakout = priorAllTimeHigh > 0 && metric > priorAllTimeHigh;

      const breakoutType = config.breakoutType ?? 'all';
      if (breakoutType === 'ath_only' && !isAllTimeHighBreakout) continue;

      // Volume ratio on breakout bar vs prior 50-day average volume (falling back to available bars)
      const volLookStart = Math.max(0, idx - 50);
      const volCount = Math.max(1, idx - volLookStart);
      let volSum = 0;
      for (let i = volLookStart; i < idx; i++) volSum += bars[i].volume;
      const avgVol50 = volSum / volCount;
      const volumeRatio = avgVol50 > 0 ? b.volume / avgVol50 : 1;
      if (volumeRatio < config.minVolumeRatio) continue;

      // Confirm stock is still holding near or above the breakout zone (not failed >6% below prior 52W high)
      const latestBar = bars[n - 1];
      if (latestBar.close < prior52WHigh * 0.94) continue;

      // How long since the prior 52-week peak (and check if any earlier new 52W high occurred inside the lookback window)
      const barsSincePriorPeak = idx - prior52WHighIdx;
      const barsSincePriorAth = idx - priorAthIdx;
      let lastNew52WHighIdx = -1;
      // Only scan inside the preceding `lookbackBars` window for speed & accuracy
      const scanFloor = Math.max(200, idx - lookbackBars);
      for (let j = idx - 1; j >= scanFloor; j--) {
        const jm = config.priceBasis === 'close' ? bars[j].close : bars[j].high;
        const jWinStart = Math.max(0, j - Math.min(252, j));
        let prevMax = -Infinity;
        for (let k = jWinStart; k < j; k++) {
          const km = config.priceBasis === 'close' ? bars[k].close : bars[k].high;
          if (km > prevMax) prevMax = km;
        }
        if (jm > prevMax) {
          lastNew52WHighIdx = j;
          break;
        }
      }

      // If no new 52W high occurred inside the lookback window, distance is at least the prior peak distance
      const barsSinceLast52W =
        lastNew52WHighIdx >= 0
          ? idx - lastNew52WHighIdx
          : Math.max(barsSincePriorPeak, Math.min(lookbackBars, idx - 200));

      const isFirstInNMonths =
        lastNew52WHighIdx === -1
          ? barsSincePriorPeak >= Math.min(lookbackBars, 21)
          : barsSinceLast52W >= lookbackBars;

      const isFreshAthBreakout =
        isAllTimeHighBreakout && barsSincePriorAth >= Math.min(lookbackBars, 21);

      if (breakoutType === '52w_only' && !isFirstInNMonths) continue;
      if (breakoutType === 'all' && !isFirstInNMonths && !isFreshAthBreakout) continue;
      if (breakoutType === 'ath_only' && !isFreshAthBreakout && !isFirstInNMonths) continue;

      const monthsSinceLast52WHigh = Number(
        (Math.max(barsSincePriorPeak, barsSinceLast52W) / 21).toFixed(1)
      );

      // Base length & depth measured from prior 52W peak to breakout bar
      const baseStartIdx = Math.max(0, prior52WHighIdx);
      let baseLow = Infinity;
      for (let i = baseStartIdx; i < idx; i++) {
        if (bars[i].low < baseLow) baseLow = bars[i].low;
      }
      if (!Number.isFinite(baseLow) || baseLow <= 0) baseLow = prior52WHigh * 0.85;
      const baseDepthPct = Number((((prior52WHigh - baseLow) / prior52WHigh) * 100).toFixed(1));
      const baseLengthWeeks = Math.max(2, Math.round((idx - baseStartIdx) / 5));
      const pctAbovePriorHigh = Number(
        (((latestBar.close - prior52WHigh) / prior52WHigh) * 100).toFixed(2)
      );
      const pctAbovePriorAth = Number(
        (((latestBar.close - priorAllTimeHigh) / Math.max(0.01, priorAllTimeHigh)) * 100).toFixed(2)
      );
      const athHistoryYears = Number((n / 252).toFixed(1));

      matched = {
        stock,
        breakoutDate: b.date,
        barsAgo: n - 1 - idx,
        monthsSinceLast52WHigh,
        prior52WHigh: Number(prior52WHigh.toFixed(2)),
        pctAbovePriorHigh,
        isAllTimeHighBreakout,
        priorAllTimeHigh: Number(priorAllTimeHigh.toFixed(2)),
        pctAbovePriorAth,
        athHistoryYears,
        volumeRatio: Number(volumeRatio.toFixed(2)),
        baseLengthWeeks,
        baseDepthPct,
        isFirstInNMonths,
      };
      break;
    }

    if (matched) results.push(matched);
  }

  return results.sort((a, b) => {
    const recencyDiff = (a.barsAgo ?? 0) - (b.barsAgo ?? 0);
    if (recencyDiff !== 0) return recencyDiff;
    if (a.isAllTimeHighBreakout !== b.isAllTimeHighBreakout) {
      return a.isAllTimeHighBreakout ? -1 : 1;
    }
    if (b.monthsSinceLast52WHigh !== a.monthsSinceLast52WHigh) {
      return b.monthsSinceLast52WHigh - a.monthsSinceLast52WHigh;
    }
    return b.volumeRatio - a.volumeRatio;
  });
}

/**
 * 2. MARK MINERVINI SEPA ENGINE
 * - IBD-style Relative Strength Rating (1-99 percentile vs NIFTY 500 universe)
 * - 8-Point Trend Template Screener (all thresholds editable)
 * - Stage Analysis (Stage 1 - 4)
 * - VCP (Volatility Contraction Pattern) Detection
 * - SEPA Fundamentals & Composite Minervini Score
 */
function computeWeighted12MPerformance(bars: OHLCVBar[]): number {
  const n = bars.length;
  const c0 = bars[n - 1].close;
  const c3 = bars[Math.max(0, n - 1 - 63)].close;
  const c6 = bars[Math.max(0, n - 1 - 126)].close;
  const c9 = bars[Math.max(0, n - 1 - 189)].close;
  const c12 = bars[Math.max(0, n - 1 - 252)].close;
  const r3 = (c0 - c3) / c3;
  const r6 = (c0 - c6) / c6;
  const r9 = (c0 - c9) / c9;
  const r12 = (c0 - c12) / c12;
  return 0.4 * r3 + 0.2 * r6 + 0.2 * r9 + 0.2 * r12;
}

function detectVcpPattern(bars: OHLCVBar[]): VcpAnalysis {
  const n = bars.length;
  const lookback = Math.min(150, n - 1);
  const slice = bars.slice(n - lookback);
  const m = slice.length;

  // Identify up to 4 sequential contraction windows across the recent base (from left peak to right pivot)
  let basePeakIdx = 0;
  for (let i = 0; i < m - 10; i++) {
    if (slice[i].high > slice[basePeakIdx].high) basePeakIdx = i;
  }
  const baseSlice = slice.slice(basePeakIdx);
  const bLen = baseSlice.length;

  const contractions: VcpContraction[] = [];
  if (bLen >= 20) {
    // Partition base into 4 chronological segments and extract peak-to-trough depth per contraction
    const segments = bLen >= 60 ? 4 : bLen >= 38 ? 3 : 2;
    const weights =
      segments === 4
        ? [0.35, 0.28, 0.22, 0.15]
        : segments === 3
        ? [0.42, 0.34, 0.24]
        : [0.58, 0.42];
    let pos = 0;
    for (let s = 0; s < segments; s++) {
      const segLen =
        s === segments - 1
          ? Math.max(4, bLen - 2 - pos)
          : Math.max(5, Math.round((bLen - 2) * weights[s]));
      const segEnd = Math.min(bLen - 2, pos + segLen);
      if (segEnd - pos < 3) break;
      let peakIdx = pos;
      for (let k = pos; k <= segEnd; k++) {
        if (baseSlice[k].high > baseSlice[peakIdx].high) peakIdx = k;
      }
      let troughIdx = peakIdx;
      for (let k = peakIdx; k <= segEnd; k++) {
        if (baseSlice[k].low < baseSlice[troughIdx].low) troughIdx = k;
      }
      if (troughIdx === peakIdx && segEnd > pos) {
        // Fallback: peak before trough
        let maxDrop = 0;
        let pI = pos;
        let tI = pos;
        for (let a = pos; a <= segEnd; a++) {
          for (let b = a + 1; b <= segEnd; b++) {
            const drop = (baseSlice[a].high - baseSlice[b].low) / baseSlice[a].high;
            if (drop > maxDrop) {
              maxDrop = drop;
              pI = a;
              tI = b;
            }
          }
        }
        peakIdx = pI;
        troughIdx = tI;
      }
      const peakPrice = baseSlice[peakIdx].high;
      const troughPrice = baseSlice[troughIdx].low;
      const depthPct = Number((((peakPrice - troughPrice) / peakPrice) * 100).toFixed(1));
      if (depthPct >= 1.2) {
        contractions.push({
          index: contractions.length + 1,
          startDate: baseSlice[peakIdx].date,
          endDate: baseSlice[troughIdx].date,
          peakPrice: Number(peakPrice.toFixed(2)),
          troughPrice: Number(troughPrice.toFixed(2)),
          depthPct,
          durationDays: Math.max(2, segEnd - pos),
        });
      }
      pos = segEnd;
    }
  }

  // Check if contractions genuinely narrow from left to right
  let shrinkingSteps = 0;
  for (let i = 1; i < contractions.length; i++) {
    if (contractions[i].depthPct < contractions[i - 1].depthPct * 0.92) {
      shrinkingSteps++;
    }
  }

  // Volume dry-up near pivot (average of bars n-7..n-2 vs 50-day avg)
  let vol50 = 0;
  for (let i = n - 52; i < n - 2; i++) vol50 += bars[i].volume;
  vol50 /= 50;
  let volNearPivot = 0;
  for (let i = n - 7; i < n - 2; i++) volNearPivot += bars[i].volume;
  volNearPivot /= 5;
  const volumeDryUpRatio = Number((volNearPivot / Math.max(1, vol50)).toFixed(2));
  const isVolumeDryUp = volumeDryUpRatio <= 0.72;

  // Pivot buy point: highest high of the final contraction (or last 15 pre-breakout bars)
  let pivotPrice = 0;
  for (let i = Math.max(0, n - 18); i < n - 2; i++) {
    if (bars[i].high > pivotPrice) pivotPrice = bars[i].high;
  }
  if (pivotPrice === 0) pivotPrice = bars[n - 2].high;
  pivotPrice = Number(pivotPrice.toFixed(2));

  const today = bars[n - 1];
  const distanceToPivotPct = Number((((today.close - pivotPrice) / pivotPrice) * 100).toFixed(2));
  const breakoutVolumeRatio = Number((today.volume / Math.max(1, vol50)).toFixed(2));
  const isPivotBreakout =
    today.close > pivotPrice && distanceToPivotPct <= 8.5 && breakoutVolumeRatio >= 1.4;

  const lastDepth = contractions.length > 0 ? contractions[contractions.length - 1].depthPct : 99;
  const detected =
    contractions.length >= 2 &&
    shrinkingSteps >= Math.max(1, contractions.length - 2) &&
    lastDepth <= 10.5 &&
    distanceToPivotPct >= -12 &&
    distanceToPivotPct <= 10;

  return {
    detected,
    tCount: contractions.length,
    contractions,
    volumeDryUpRatio,
    isVolumeDryUp,
    pivotPrice,
    distanceToPivotPct,
    isPivotBreakout: detected && isPivotBreakout,
    breakoutVolumeRatio,
    baseWeeks: Math.max(3, Math.round(bLen / 5)),
  };
}

function classifyStage(
  price: number,
  sma50: number,
  sma150: number,
  sma200: number,
  sma200SlopePct: number
): { stage: MarketStage; label: string } {
  if (price > sma50 && sma50 > sma150 && sma150 > sma200 && sma200SlopePct > 0.35) {
    return { stage: 2, label: 'Stage 2 — Advancing' };
  }
  if (price < sma200 && sma50 < sma150 && sma200SlopePct < -0.3) {
    return { stage: 4, label: 'Stage 4 — Declining' };
  }
  if (price < sma50 && price >= sma200 * 0.96 && sma200SlopePct >= -0.4 && sma50 >= sma200 * 0.97) {
    return { stage: 3, label: 'Stage 3 — Topping' };
  }
  return { stage: 1, label: 'Stage 1 — Basing' };
}

function scoreSepaFundamentals(stock: IndianStock): number {
  const f = stock.fundamentals;
  let score = 0;
  // Quarterly EPS growth & acceleration (30 pts)
  if (f.qtrEpsYoY >= 25) score += 20;
  else if (f.qtrEpsYoY >= 15) score += 13;
  else if (f.qtrEpsYoY > 0) score += 6;
  if (f.qtrEpsYoY > f.prevQtrEpsYoY) score += 10;

  // Quarterly Revenue growth & acceleration (20 pts)
  if (f.qtrRevYoY >= 20) score += 13;
  else if (f.qtrRevYoY >= 12) score += 8;
  else if (f.qtrRevYoY > 0) score += 4;
  if (f.qtrRevYoY > f.prevQtrRevYoY) score += 7;

  // Margin expansion & Earnings surprise (20 pts)
  if (f.opMarginExpansionBps >= 100) score += 12;
  else if (f.opMarginExpansionBps > 0) score += 7;
  if (f.earningsSurprisePct >= 5) score += 8;
  else if (f.earningsSurprisePct > 0) score += 5;

  // 3Y Annual EPS CAGR & ROE (15 pts)
  if (f.annualEps3YCagr >= 20) score += 9;
  else if (f.annualEps3YCagr >= 12) score += 5;
  if (f.roePct >= 17) score += 6;
  else if (f.roePct >= 12) score += 3;

  // Institutional sponsorship (FII + DII accumulation) & zero promoter pledge (15 pts)
  if (f.fiiQoQChangePct + f.diiQoQChangePct > 0.5) score += 10;
  else if (f.fiiQoQChangePct + f.diiQoQChangePct > 0) score += 5;
  if (f.promoterPledgePct === 0) score += 5;

  return Math.min(100, Math.round(score));
}

export const DEFAULT_TREND_THRESHOLDS: TrendTemplateThresholds = {
  sma200TrendMonths: 1,
  minAbove52WLowPct: 30,
  maxBelow52WHighPct: 25,
  minRsRating: 70,
};

const minerviniMemoCache = new Map<string, MinerviniAnalysis[]>();

function computeUniverseSnapshotKey(stocks: IndianStock[]): string {
  const len = stocks.length;
  if (len === 0) return '0';
  const a = stocks[0];
  const b = stocks[Math.floor(len / 2)];
  const c = stocks[len - 1];
  let liveCount = 0;
  for (let i = 0; i < len; i++) {
    if (stocks[i].isLiveHydrated) liveCount++;
  }
  return `${len}:${liveCount}:${a.ticker}=${a.latestClose}:${b.ticker}=${b.latestClose}:${c.ticker}=${c.latestClose}:${BENCHMARKS.NIFTY500.latestClose}`;
}

export function runMinerviniAnalysis(
  stocks: IndianStock[],
  thresholds: TrendTemplateThresholds = DEFAULT_TREND_THRESHOLDS
): MinerviniAnalysis[] {
  const cacheKey = `${computeUniverseSnapshotKey(stocks)}|${thresholds.sma200TrendMonths}|${thresholds.minAbove52WLowPct}|${thresholds.maxBelow52WHighPct}|${thresholds.minRsRating}`;
  const cached = minerviniMemoCache.get(cacheKey);
  if (cached) return cached;

  const nifty500Perf = computeWeighted12MPerformance(BENCHMARKS.NIFTY500.bars);

  // Step 1: Compute IBD-style weighted 12M relative strength vs NIFTY 500 across the universe
  const rawScores = stocks.map((stock) => {
    const perf = computeWeighted12MPerformance(stock.bars);
    const relPerf = (1 + perf) / (1 + nifty500Perf) - 1;
    return { ticker: stock.ticker, relPerf };
  });

  const sortedRel = [...rawScores].sort((a, b) => a.relPerf - b.relPerf);
  const rsMap = new Map<string, { rating: number; raw: number }>();
  sortedRel.forEach((item, idx) => {
    // Map cleanly to 1-99 IBD percentile scale, anchored around NIFTY 500 = 50
    const pctRank = Math.round(12 + (idx / Math.max(1, sortedRel.length - 1)) * 87);
    rsMap.set(item.ticker, {
      rating: Math.max(1, Math.min(99, pctRank)),
      raw: Number((item.relPerf * 100).toFixed(2)),
    });
  });

  const trendLookbackBars = Math.max(21, Math.round(thresholds.sma200TrendMonths * 21));

  const computed = stocks
    .map((stock) => {
      const bars = stock.bars;
      const n = bars.length;
      const closes = bars.map((b) => b.close);
      const sma50Arr = computeSmaSeries(closes, 50);
      const sma150Arr = computeSmaSeries(closes, 150);
      const sma200Arr = computeSmaSeries(closes, 200);

      const price = closes[n - 1] ?? stock.latestClose;
      const safeNum = (v: number | undefined, fallback: number) =>
        typeof v === 'number' && Number.isFinite(v) ? Number(v.toFixed(2)) : fallback;
      const sma50 = safeNum(sma50Arr[n - 1], price);
      const sma150 = safeNum(sma150Arr[n - 1], sma50);
      const sma200 = safeNum(sma200Arr[n - 1], sma150);
      const prev200Idx = Math.min(n - 1, Math.max(0, n - 1 - trendLookbackBars));
      const sma200Prev = safeNum(sma200Arr[prev200Idx], sma200);
      const sma200SlopePct = ((sma200 - sma200Prev) / Math.max(1, sma200Prev)) * 100;

      // 52-week high & low
      const win252 = bars.slice(Math.max(0, n - 252));
      let high52W = -Infinity;
      let low52W = Infinity;
      for (const b of win252) {
        if (b.high > high52W) high52W = b.high;
        if (b.low < low52W) low52W = b.low;
      }
      high52W = Number(high52W.toFixed(2));
      low52W = Number(low52W.toFixed(2));

      const pctAbove52WLow = Number((((price - low52W) / low52W) * 100).toFixed(1));
      const pctBelow52WHigh = Number((((high52W - price) / high52W) * 100).toFixed(1));

      const rsObj = rsMap.get(stock.ticker) ?? { rating: 50, raw: 0 };
      const rsRating = rsObj.rating;

      const conditions: TrendConditionCheck[] = [
        {
          id: 1,
          label: 'Price > 150D & 200D SMA',
          detail: `₹${price.toFixed(0)} vs 150D ₹${sma150.toFixed(0)} / 200D ₹${sma200.toFixed(0)}`,
          passed: price > sma150 && price > sma200,
        },
        {
          id: 2,
          label: '150D SMA > 200D SMA',
          detail: `₹${sma150.toFixed(0)} vs ₹${sma200.toFixed(0)}`,
          passed: sma150 > sma200,
        },
        {
          id: 3,
          label: `200D SMA rising (${thresholds.sma200TrendMonths}M)`,
          detail: `₹${sma200Prev.toFixed(0)} → ₹${sma200.toFixed(0)} (${sma200SlopePct >= 0 ? '+' : ''}${sma200SlopePct.toFixed(1)}%)`,
          passed: sma200 > sma200Prev,
        },
        {
          id: 4,
          label: '50D SMA > 150D & 200D SMA',
          detail: `₹${sma50.toFixed(0)} vs ₹${sma150.toFixed(0)} / ₹${sma200.toFixed(0)}`,
          passed: sma50 > sma150 && sma50 > sma200,
        },
        {
          id: 5,
          label: 'Price > 50D SMA',
          detail: `₹${price.toFixed(0)} vs ₹${sma50.toFixed(0)}`,
          passed: price > sma50,
        },
        {
          id: 6,
          label: `Price ≥ ${thresholds.minAbove52WLowPct}% above 52W Low`,
          detail: `+${pctAbove52WLow.toFixed(1)}% above ₹${low52W.toFixed(0)}`,
          passed: pctAbove52WLow >= thresholds.minAbove52WLowPct,
        },
        {
          id: 7,
          label: `Within ${thresholds.maxBelow52WHighPct}% of 52W High`,
          detail: `${pctBelow52WHigh.toFixed(1)}% below ₹${high52W.toFixed(0)}`,
          passed: pctBelow52WHigh <= thresholds.maxBelow52WHighPct,
        },
        {
          id: 8,
          label: `RS Rating ≥ ${thresholds.minRsRating} (vs NIFTY 500)`,
          detail: `RS ${rsRating} (${rsObj.raw >= 0 ? '+' : ''}${rsObj.raw}% rel)`,
          passed: rsRating >= thresholds.minRsRating,
        },
      ];

      const passedCount = conditions.filter((c) => c.passed).length;
      const allPassed = passedCount === 8;

      const stageInfo = classifyStage(price, sma50, sma150, sma200, sma200SlopePct);
      const vcp = detectVcpPattern(bars);
      const sepaFundamentalScore = scoreSepaFundamentals(stock);

      // Composite Minervini SEPA Score (0-100):
      // 35% Trend Template + 25% VCP Structure + 20% RS Rating + 20% SEPA Fundamentals
      const ttPoints = (passedCount / 8) * 35;
      const vcpPoints = vcp.isPivotBreakout
        ? 25
        : vcp.detected && vcp.isVolumeDryUp
        ? 22
        : vcp.detected
        ? 17
        : stageInfo.stage === 2
        ? 10
        : 3;
      const rsPoints = (rsRating / 99) * 20;
      const fundPoints = (sepaFundamentalScore / 100) * 20;
      const minerviniScore = Math.min(100, Math.round(ttPoints + vcpPoints + rsPoints + fundPoints));

      const suggestedStopPct = vcp.detected && vcp.contractions.length > 0
        ? Math.min(8.0, Math.max(4.5, Number((vcp.contractions[vcp.contractions.length - 1].depthPct + 1.5).toFixed(1))))
        : 7.5;
      const suggestedStopLossInr = Number((price * (1 - suggestedStopPct / 100)).toFixed(2));

      return {
        stock,
        sma50,
        sma150,
        sma200,
        sma200Prev,
        high52W,
        low52W,
        pctAbove52WLow,
        pctBelow52WHigh,
        rsRating,
        rsRawScore: rsObj.raw,
        conditions,
        passedCount,
        allPassed,
        stage: stageInfo.stage,
        stageLabel: stageInfo.label,
        vcp,
        sepaFundamentalScore,
        minerviniScore,
        suggestedStopLossInr,
        suggestedStopPct,
      };
    })
    .sort((a, b) => b.minerviniScore - a.minerviniScore);

  if (minerviniMemoCache.size > 16) minerviniMemoCache.clear();
  minerviniMemoCache.set(cacheKey, computed);
  return computed;
}
