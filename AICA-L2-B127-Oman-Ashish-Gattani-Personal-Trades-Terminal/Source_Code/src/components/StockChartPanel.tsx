import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AreaSeries,
  BarSeries,
  BaselineSeries,
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  IChartApi,
  ISeriesApi,
  LineSeries,
  LineStyle,
  PriceScaleMode,
  SeriesMarker,
  SeriesType,
  Time,
  createChart,
  createSeriesMarkers,
} from 'lightweight-charts';
import { BellPlus, BookmarkCheck, Check, Maximize2, RotateCcw } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS } from '../data/indianMarketData';
import { VolumeCandleData, VolumeCandlesSeries } from './VolumeCandlesSeries';
import { computeSmaSeries } from '../engine/analyticsEngine';
import { evaluateCustomIndicatorBars } from '../engine/customIndicatorEngine';
import { resolveStockSectorContext } from '../engine/sectorTrendEngine';
import {
  DonchianPeriod,
  LevelCategory,
  computeAdxSeries,
  computeBollingerBands,
  computeDonchianChannel,
  computeEmaSeries,
  computeMacdSeries,
  computeRollingVwap,
  computeRsiSeries,
  computeRsLineVsNifty500,
  computeSingleStockCallScore,
  computeSupertrendSeries,
  detectKeyBreakoutSupportLevels,
  diagnoseBarsForSetups,
  resampleToWeekly,
} from '../engine/tradeRadarEngine';
import { CustomIndicatorDefinition, IndianStock, OHLCVBar } from '../types/market';
import { formatINR, formatPct } from '../utils/formatters';

export type ChartStyleType =
  | 'volume_candles'
  | 'candlestick'
  | 'hollow'
  | 'ohlc'
  | 'heikin'
  | 'area'
  | 'line';
export type SmaPeriod = 21 | 50 | 100 | 150 | 200;
export type LevelVisibilityState = Record<LevelCategory, boolean>;
export type SubPaneKey = 'rs' | 'rsi' | 'macd' | 'adx';
type RangeKey = '1M' | '3M' | '6M' | '1Y' | '2Y' | '3Y';
type IntervalKey = '1D' | '1W';
type OscillatorPaneKey = 'off' | SubPaneKey;

export const DEFAULT_LEVEL_VISIBILITY: LevelVisibilityState = {
  breakout: true,
  major_resistance: true,
  minor_resistance: false,
  major_support: true,
  minor_support: false,
};

export const SMA_OVERLAY_CONFIGS: {
  period: SmaPeriod;
  shortLabel: string;
  color: string;
  textClass: string;
  activeClass: string;
}[] = [
  {
    period: 21,
    shortLabel: '21',
    color: '#22d3ee',
    textClass: 'text-cyan-600 dark:text-cyan-400',
    activeClass: 'border-cyan-500/50 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300',
  },
  {
    period: 50,
    shortLabel: '50',
    color: '#38bdf8',
    textClass: 'text-sky-600 dark:text-sky-400',
    activeClass: 'border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  },
  {
    period: 100,
    shortLabel: '100',
    color: '#ec4899',
    textClass: 'text-pink-600 dark:text-pink-400',
    activeClass: 'border-pink-500/50 bg-pink-500/10 text-pink-700 dark:text-pink-300',
  },
  {
    period: 150,
    shortLabel: '150',
    color: '#f59e0b',
    textClass: 'text-amber-600 dark:text-amber-400',
    activeClass: 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  },
  {
    period: 200,
    shortLabel: '200',
    color: '#a855f7',
    textClass: 'text-purple-600 dark:text-purple-400',
    activeClass: 'border-purple-500/50 bg-purple-500/10 text-purple-700 dark:text-purple-300',
  },
];

export const LEVEL_TOGGLE_CONFIGS: {
  key: LevelCategory;
  label: string;
  color: string;
  activeClass: string;
}[] = [
  {
    key: 'breakout',
    label: 'Breakout',
    color: '#10b981',
    activeClass: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
  },
  {
    key: 'major_resistance',
    label: 'Major Res',
    color: '#f59e0b',
    activeClass: 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  },
  {
    key: 'minor_resistance',
    label: 'Minor Res',
    color: '#fbbf24',
    activeClass: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
  },
  {
    key: 'major_support',
    label: 'Major Sup',
    color: '#ef4444',
    activeClass: 'border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-300',
  },
  {
    key: 'minor_support',
    label: 'Minor Sup',
    color: '#fb923c',
    activeClass: 'border-orange-500/50 bg-orange-500/10 text-orange-700 dark:text-orange-300',
  },
];

const RANGE_DAYS: Record<RangeKey, number> = {
  '1M': 22,
  '3M': 65,
  '6M': 130,
  '1Y': 252,
  '2Y': 504,
  '3Y': 780,
};

const CHART_STYLE_OPTIONS: { id: ChartStyleType; label: string }[] = [
  { id: 'volume_candles', label: 'Vol Candles' },
  { id: 'candlestick', label: 'Candles' },
  { id: 'hollow', label: 'Hollow' },
  { id: 'ohlc', label: 'OHLC Bars' },
  { id: 'heikin', label: 'Heikin-Ashi' },
  { id: 'area', label: 'Area' },
  { id: 'line', label: 'Line' },
];

const SUB_PANE_OPTIONS: {
  id: SubPaneKey;
  label: string;
  color: string;
  activeClass: string;
}[] = [
  {
    id: 'rs',
    label: 'RS vs N500',
    color: '#2563eb',
    activeClass: 'border-blue-500/50 bg-blue-500/10 text-blue-700 dark:text-blue-300',
  },
  {
    id: 'rsi',
    label: 'RSI (14)',
    color: '#8b5cf6',
    activeClass: 'border-violet-500/50 bg-violet-500/10 text-violet-700 dark:text-violet-300',
  },
  {
    id: 'macd',
    label: 'MACD',
    color: '#38bdf8',
    activeClass: 'border-sky-500/50 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  },
  {
    id: 'adx',
    label: 'ADX (14)',
    color: '#f59e0b',
    activeClass: 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  },
];

interface StockChartPanelProps {
  stock?: IndianStock;
  barsOverride?: OHLCVBar[];
  symbolLabel?: string;
  pivotPrice?: number;
  prior52WHigh?: number;
  stopLossPrice?: number;
  customIndicator?: CustomIndicatorDefinition | null;
  height?: number;
  defaultStyle?: ChartStyleType;
  defaultRange?: RangeKey;
  defaultOscillator?: OscillatorPaneKey;
  defaultSubPanes?: SubPaneKey[];
  defaultShowDonchian?: boolean;
  defaultShowSupertrend?: boolean;
  levelVisibility?: LevelVisibilityState;
  onToggleLevelCategory?: (category: LevelCategory) => void;
  onResetTemplateLevels?: () => void;
  hidePreChartSummary?: boolean;
}

export const CHART_TEMPLATE_STORAGE_KEY = 'tf_chart_default_template_v2';
const LEGACY_CHART_TEMPLATE_STORAGE_KEY = 'tf_chart_default_template_v1';

export interface SavedChartTemplate {
  chartStyle: ChartStyleType;
  interval: IntervalKey;
  range: RangeKey;
  enabledSmas: Record<SmaPeriod, boolean>;
  showEmas: boolean;
  showBollinger: boolean;
  showDonchian: boolean;
  donchianPeriod: DonchianPeriod;
  showSupertrend: boolean;
  showStMarkers?: boolean;
  showDcMarkers?: boolean;
  showHvMarkers?: boolean;
  showAthLine?: boolean;
  showVwap: boolean;
  showSetupMarkers: boolean;
  showVolume: boolean;
  logScale: boolean;
  enabledSubPanes: Record<SubPaneKey, boolean>;
  levelVisibility: LevelVisibilityState;
}

interface ChartSignalEvent {
  id: string;
  date: string;
  source: 'ST' | 'DC' | 'HV';
  type: 'BUY' | 'SELL' | 'VOL';
  badge: 'ST B' | 'ST S' | 'DC B' | 'DC S' | 'HVE' | 'HVY' | 'HVQ';
  triggerPrice: number;
  indicatorLabel: string;
  indicatorValue: number;
  dcUpper?: number | null;
  dcLower?: number | null;
  volRatio?: number | null;
  volumeRaw?: number | null;
  hvFullLabel?: string;
  barsAgo: number;
}

export function loadSavedChartTemplate(): SavedChartTemplate | null {
  try {
    const rawV2 = localStorage.getItem(CHART_TEMPLATE_STORAGE_KEY);
    if (rawV2) {
      const parsed = JSON.parse(rawV2) as Partial<SavedChartTemplate>;
      if (parsed && typeof parsed === 'object' && parsed.chartStyle) {
        return parsed as SavedChartTemplate;
      }
    }
    // Migrate v1 template cleanly while ensuring DC/ST lines start OFF (only signal markers enabled)
    const rawV1 = localStorage.getItem(LEGACY_CHART_TEMPLATE_STORAGE_KEY);
    if (rawV1) {
      const parsed = JSON.parse(rawV1) as Partial<SavedChartTemplate>;
      if (parsed && typeof parsed === 'object' && parsed.chartStyle) {
        return {
          ...(parsed as SavedChartTemplate),
          showDonchian: false,
          showSupertrend: false,
          showStMarkers: parsed.showStMarkers ?? true,
          showDcMarkers: parsed.showDcMarkers ?? true,
        };
      }
    }
    return null;
  } catch {
    return null;
  }
}

interface CrosshairReadout {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  prevClose: number;
  changePct: number;
  volume: number;
  volRatio20: number | null;
  smas: Record<SmaPeriod, number | null>;
  ema10: number | null;
  ema21: number | null;
  vwap20: number | null;
  dcUpper: number | null;
  dcMid: number | null;
  dcLower: number | null;
  supertrendVal: number | null;
  supertrendDir: 1 | -1 | null;
  rsi14: number | null;
  macdVal: number | null;
  macdSig: number | null;
  macdHist: number | null;
  adx14: number | null;
  plusDi14: number | null;
  minusDi14: number | null;
  rsVal: number | null;
  indVal: number | null;
}

function computeHeikinAshi(bars: OHLCVBar[]) {
  const out: { time: Time; open: number; high: number; low: number; close: number }[] = [];
  let prevHaOpen = bars[0]?.open ?? 0;
  let prevHaClose = bars[0]?.close ?? 0;

  for (let i = 0; i < bars.length; i++) {
    const b = bars[i];
    const haClose = (b.open + b.high + b.low + b.close) / 4;
    const haOpen = i === 0 ? (b.open + b.close) / 2 : (prevHaOpen + prevHaClose) / 2;
    const haHigh = Math.max(b.high, haOpen, haClose);
    const haLow = Math.min(b.low, haOpen, haClose);
    out.push({
      time: b.date as Time,
      open: Number(haOpen.toFixed(2)),
      high: Number(haHigh.toFixed(2)),
      low: Number(haLow.toFixed(2)),
      close: Number(haClose.toFixed(2)),
    });
    prevHaOpen = haOpen;
    prevHaClose = haClose;
  }
  return out;
}

export const StockChartPanel: React.FC<StockChartPanelProps> = ({
  stock,
  barsOverride,
  symbolLabel,
  pivotPrice,
  prior52WHigh,
  stopLossPrice,
  customIndicator,
  height = 360,
  defaultStyle = 'volume_candles',
  defaultRange = '6M',
  defaultOscillator = 'rs',
  defaultSubPanes,
  defaultShowDonchian = false,
  defaultShowSupertrend = false,
  levelVisibility: controlledLevelVisibility,
  onToggleLevelCategory,
  onResetTemplateLevels,
  hidePreChartSummary = false,
}) => {
  const { theme, marketVersion, addAlert } = useAppData();

  const preChartSummary = useMemo(() => {
    if (hidePreChartSummary) return null;
    const ticker = stock?.ticker || symbolLabel;
    const raw = barsOverride && barsOverride.length > 0 ? barsOverride : stock?.bars || [];
    if (!ticker || raw.length < 30) return null;
    return computeSingleStockCallScore({
      ticker,
      universe: INDIAN_STOCKS,
      bars: raw,
      resolveSector: (sec, ind) => resolveStockSectorContext(INDIAN_STOCKS, sec, ind, marketVersion),
      sectorFallback: stock
        ? resolveStockSectorContext(INDIAN_STOCKS, stock.sector, stock.industry, marketVersion)
        : null,
    });
  }, [hidePreChartSummary, stock, symbolLabel, barsOverride, marketVersion]);

  const savedTpl = useMemo(() => loadSavedChartTemplate(), []);
  const [hasSavedTemplate, setHasSavedTemplate] = useState<boolean>(() => savedTpl !== null);
  const [templateToast, setTemplateToast] = useState<'saved' | 'reset' | null>(null);

  const [chartStyle, setChartStyle] = useState<ChartStyleType>(
    () => savedTpl?.chartStyle ?? defaultStyle
  );
  const [interval, setIntervalMode] = useState<IntervalKey>(() => savedTpl?.interval ?? '1D');
  const [range, setRange] = useState<RangeKey>(() => savedTpl?.range ?? defaultRange);
  const [enabledSmas, setEnabledSmas] = useState<Record<SmaPeriod, boolean>>(
    () =>
      savedTpl?.enabledSmas ?? {
        21: false,
        50: true,
        100: false,
        150: true,
        200: true,
      }
  );
  const [internalLevelVisibility, setInternalLevelVisibility] = useState<LevelVisibilityState>(
    () => savedTpl?.levelVisibility ?? DEFAULT_LEVEL_VISIBILITY
  );
  const [showEmas, setShowEmas] = useState<boolean>(() => savedTpl?.showEmas ?? false);
  const [showBollinger, setShowBollinger] = useState<boolean>(
    () => savedTpl?.showBollinger ?? false
  );
  const [showDonchian, setShowDonchian] = useState<boolean>(
    () => savedTpl?.showDonchian ?? defaultShowDonchian
  );
  const [donchianPeriod, setDonchianPeriod] = useState<DonchianPeriod>(
    () => savedTpl?.donchianPeriod ?? 20
  );
  const [donchianAlertFilter, setDonchianAlertFilter] = useState<'ALL' | 'BUY' | 'SELL'>('ALL');
  const [pushedAlertId, setPushedAlertId] = useState<string | null>(null);
  const [showSupertrend, setShowSupertrend] = useState<boolean>(
    () => savedTpl?.showSupertrend ?? defaultShowSupertrend
  );
  const [showStMarkers, setShowStMarkers] = useState<boolean>(
    () => savedTpl?.showStMarkers ?? true
  );
  const [showDcMarkers, setShowDcMarkers] = useState<boolean>(
    () => savedTpl?.showDcMarkers ?? true
  );
  const [showHvMarkers, setShowHvMarkers] = useState<boolean>(
    () => savedTpl?.showHvMarkers ?? true
  );
  const [showAthLine, setShowAthLine] = useState<boolean>(
    () => savedTpl?.showAthLine ?? true
  );
  const [showVwap, setShowVwap] = useState<boolean>(() => savedTpl?.showVwap ?? false);
  const [showSetupMarkers, setShowSetupMarkers] = useState<boolean>(
    () => savedTpl?.showSetupMarkers ?? false
  );
  const [showVolume, setShowVolume] = useState<boolean>(() => savedTpl?.showVolume ?? true);
  const [logScale, setLogScale] = useState<boolean>(() => savedTpl?.logScale ?? false);
  const [enabledSubPanes, setEnabledSubPanes] = useState<Record<SubPaneKey, boolean>>(() => {
    if (savedTpl?.enabledSubPanes) {
      return {
        rs: Boolean(savedTpl.enabledSubPanes.rs),
        rsi: Boolean(savedTpl.enabledSubPanes.rsi),
        macd: Boolean(savedTpl.enabledSubPanes.macd),
        adx: Boolean(savedTpl.enabledSubPanes.adx),
      };
    }
    const initial: Record<SubPaneKey, boolean> = {
      rs: false,
      rsi: false,
      macd: false,
      adx: false,
    };
    if (defaultSubPanes && defaultSubPanes.length > 0) {
      for (const pane of defaultSubPanes) initial[pane] = true;
    } else if (defaultOscillator !== 'off') {
      initial[defaultOscillator] = true;
    }
    return initial;
  });

  const activeLevelVisibility = controlledLevelVisibility ?? internalLevelVisibility;

  const handleSaveDefaultTemplate = () => {
    const payload: SavedChartTemplate = {
      chartStyle,
      interval,
      range,
      enabledSmas,
      showEmas,
      showBollinger,
      showDonchian,
      donchianPeriod,
      showSupertrend,
      showStMarkers,
      showDcMarkers,
      showHvMarkers,
      showAthLine,
      showVwap,
      showSetupMarkers,
      showVolume,
      logScale,
      enabledSubPanes,
      levelVisibility: activeLevelVisibility,
    };
    try {
      localStorage.setItem(CHART_TEMPLATE_STORAGE_KEY, JSON.stringify(payload));
      setHasSavedTemplate(true);
      setTemplateToast('saved');
      setTimeout(() => setTemplateToast(null), 2400);
    } catch {
      // ignore storage quota errors
    }
  };

  const handleResetDefaultTemplate = () => {
    try {
      localStorage.removeItem(CHART_TEMPLATE_STORAGE_KEY);
      localStorage.removeItem(LEGACY_CHART_TEMPLATE_STORAGE_KEY);
    } catch {
      // ignore
    }
    setHasSavedTemplate(false);
    setChartStyle(defaultStyle);
    setIntervalMode('1D');
    setRange(defaultRange);
    setEnabledSmas({ 21: false, 50: true, 100: false, 150: true, 200: true });
    setInternalLevelVisibility(DEFAULT_LEVEL_VISIBILITY);
    onResetTemplateLevels?.();
    setShowEmas(false);
    setShowBollinger(false);
    setShowDonchian(false);
    setDonchianPeriod(20);
    setShowSupertrend(false);
    setShowStMarkers(true);
    setShowDcMarkers(true);
    setShowHvMarkers(true);
    setShowAthLine(true);
    setShowVwap(false);
    setShowSetupMarkers(false);
    setShowVolume(true);
    setLogScale(false);
    const resetPanes: Record<SubPaneKey, boolean> = {
      rs: false,
      rsi: false,
      macd: false,
      adx: false,
    };
    if (defaultSubPanes && defaultSubPanes.length > 0) {
      for (const pane of defaultSubPanes) resetPanes[pane] = true;
    } else if (defaultOscillator !== 'off') {
      resetPanes[defaultOscillator] = true;
    }
    setEnabledSubPanes(resetPanes);
    setTemplateToast('reset');
    setTimeout(() => setTemplateToast(null), 2400);
  };
  const toggleLevelCategory = (cat: LevelCategory) => {
    if (onToggleLevelCategory) {
      onToggleLevelCategory(cat);
    } else {
      setInternalLevelVisibility((prev) => ({ ...prev, [cat]: !prev[cat] }));
    }
  };
  const toggleSma = (period: SmaPeriod) => {
    setEnabledSmas((prev) => ({ ...prev, [period]: !prev[period] }));
  };
  const toggleSubPane = (pane: SubPaneKey) => {
    setEnabledSubPanes((prev) => ({ ...prev, [pane]: !prev[pane] }));
  };

  const mainContainerRef = useRef<HTMLDivElement | null>(null);
  const subContainersRef = useRef<Map<string, HTMLDivElement>>(new Map());
  const chartRef = useRef<IChartApi | null>(null);
  const subChartsRef = useRef<Map<string, IChartApi>>(new Map());
  const isSyncingRangeRef = useRef(false);

  const dailyBars = useMemo(() => {
    const raw = barsOverride || stock?.bars || [];
    const map = new Map<string, OHLCVBar>();
    for (const b of raw) {
      if (b && b.date && Number.isFinite(b.close) && b.close > 0) {
        map.set(b.date, b);
      }
    }
    return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
  }, [barsOverride, stock, marketVersion]);

  const activeBars = useMemo(() => {
    if (interval === '1W') return resampleToWeekly(dailyBars);
    return dailyBars;
  }, [dailyBars, interval]);

  const computed = useMemo(() => {
    const closes = activeBars.map((b) => b.close);
    const isWeekly = interval === '1W';
    const smaSeries: Record<SmaPeriod, number[]> = {
      21: computeSmaSeries(closes, 21),
      50: computeSmaSeries(closes, 50),
      100: computeSmaSeries(closes, 100),
      150: computeSmaSeries(closes, 150),
      200: computeSmaSeries(closes, 200),
    };
    const ema10 = computeEmaSeries(closes, 10);
    const ema21 = computeEmaSeries(closes, 21);
    const bb = computeBollingerBands(closes, 20, 2);
    const donchian = computeDonchianChannel(activeBars, donchianPeriod);
    const supertrend = computeSupertrendSeries(activeBars, 10, 3);
    const vwap20 = computeRollingVwap(activeBars, 20);
    const rsi14 = computeRsiSeries(closes, 14);
    const macd = computeMacdSeries(closes, 12, 26, 9);
    const adx14 = computeAdxSeries(activeBars, 14);
    const rsLine = computeRsLineVsNifty500(activeBars);
    const rsByDate = new Map(rsLine.map((r) => [r.date, r.value]));

    const evalInd =
      !isWeekly && customIndicator && dailyBars.length > 0
        ? evaluateCustomIndicatorBars(dailyBars, customIndicator)
        : null;

    // Setup signal markers (Pocket Pivots + NR7 contractions) on daily timeframe
    const setupDiag =
      !isWeekly && dailyBars.length >= 60
        ? diagnoseBarsForSetups(dailyBars, {
            ticker: symbolLabel || stock?.ticker || 'NSE',
            name: stock?.name || symbolLabel || 'NSE',
            sector: stock?.sector || 'Equity',
            capBucket: stock?.capBucket || 'Large',
            avgDailyTurnoverCr: stock?.avgDailyTurnoverCr || 0,
          })
        : null;

    const volSma20 = computeSmaSeries(
      activeBars.map((b) => b.volume),
      20
    );

    const byDate = new Map<string, CrosshairReadout>();
    for (let i = 0; i < activeBars.length; i++) {
      const b = activeBars[i];
      const prevC = i > 0 ? activeBars[i - 1].close : b.open;
      const chg = prevC > 0 ? ((b.close - prevC) / prevC) * 100 : 0;
      const avgV20 = volSma20[i];
      const volRatio20 =
        b.volume > 0 && Number.isFinite(avgV20) && avgV20 > 0
          ? Number((b.volume / avgV20).toFixed(2))
          : null;
      byDate.set(b.date, {
        date: b.date,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
        prevClose: prevC,
        changePct: chg,
        volume: b.volume,
        volRatio20,
        smas: {
          21: Number.isFinite(smaSeries[21][i]) ? Number(smaSeries[21][i].toFixed(2)) : null,
          50: Number.isFinite(smaSeries[50][i]) ? Number(smaSeries[50][i].toFixed(2)) : null,
          100: Number.isFinite(smaSeries[100][i]) ? Number(smaSeries[100][i].toFixed(2)) : null,
          150: Number.isFinite(smaSeries[150][i]) ? Number(smaSeries[150][i].toFixed(2)) : null,
          200: Number.isFinite(smaSeries[200][i]) ? Number(smaSeries[200][i].toFixed(2)) : null,
        },
        ema10: Number.isFinite(ema10[i]) ? Number(ema10[i].toFixed(2)) : null,
        ema21: Number.isFinite(ema21[i]) ? Number(ema21[i].toFixed(2)) : null,
        vwap20: Number.isFinite(vwap20[i]) ? Number(vwap20[i].toFixed(2)) : null,
        dcUpper: Number.isFinite(donchian.upper[i]) ? Number(donchian.upper[i].toFixed(2)) : null,
        dcMid: Number.isFinite(donchian.mid[i]) ? Number(donchian.mid[i].toFixed(2)) : null,
        dcLower: Number.isFinite(donchian.lower[i]) ? Number(donchian.lower[i].toFixed(2)) : null,
        supertrendVal: Number.isFinite(supertrend.line[i])
          ? Number(supertrend.line[i].toFixed(2))
          : null,
        supertrendDir: Number.isFinite(supertrend.line[i]) ? supertrend.direction[i] : null,
        rsi14: Number.isFinite(rsi14[i]) ? Number(rsi14[i].toFixed(1)) : null,
        macdVal: Number.isFinite(macd.macd[i]) ? Number(macd.macd[i].toFixed(2)) : null,
        macdSig: Number.isFinite(macd.signal[i]) ? Number(macd.signal[i].toFixed(2)) : null,
        macdHist: Number.isFinite(macd.hist[i]) ? Number(macd.hist[i].toFixed(2)) : null,
        adx14: Number.isFinite(adx14.adx[i]) ? Number(adx14.adx[i].toFixed(1)) : null,
        plusDi14: Number.isFinite(adx14.plusDi[i]) ? Number(adx14.plusDi[i].toFixed(1)) : null,
        minusDi14: Number.isFinite(adx14.minusDi[i]) ? Number(adx14.minusDi[i].toFixed(1)) : null,
        rsVal: rsByDate.get(b.date) ?? null,
        indVal:
          evalInd && Number.isFinite(evalInd.values[i])
            ? Number(evalInd.values[i].toFixed(3))
            : null,
      });
    }

    const keyLevels = detectKeyBreakoutSupportLevels(activeBars, isWeekly);

    // Background Supertrend (10,3) Buy/Sell flip events + Donchian Channel Buy/Sell events
    // Computed regardless of overlay visibility so Signal Markers Only mode stays instant.
    const stSignals: ChartSignalEvent[] = [];
    for (let i = 1; i < activeBars.length; i++) {
      const prevDir = supertrend.direction[i - 1];
      const curDir = supertrend.direction[i];
      const stVal = supertrend.line[i];
      if (!Number.isFinite(stVal) || !Number.isFinite(supertrend.line[i - 1])) continue;
      if (prevDir !== curDir && (curDir === 1 || curDir === -1)) {
        const b = activeBars[i];
        const avgV = volSma20[i];
        const vr =
          b.volume > 0 && Number.isFinite(avgV) && avgV > 0
            ? Number((b.volume / avgV).toFixed(2))
            : null;
        const type = curDir === 1 ? 'BUY' : 'SELL';
        stSignals.push({
          id: `st_${b.date}_${type}`,
          date: b.date,
          source: 'ST',
          type,
          badge: type === 'BUY' ? 'ST B' : 'ST S',
          triggerPrice: b.close,
          indicatorLabel: 'Supertrend (10,3)',
          indicatorValue: Number(stVal.toFixed(2)),
          volRatio: vr,
          barsAgo: activeBars.length - 1 - i,
        });
      }
    }

    const dcSignals: ChartSignalEvent[] = donchian.recentAlerts.map((sig) => {
      const barReadout = byDate.get(sig.date);
      return {
        id: sig.id,
        date: sig.date,
        source: 'DC',
        type: sig.type,
        badge: sig.type === 'BUY' ? 'DC B' : 'DC S',
        triggerPrice: sig.triggerPrice,
        indicatorLabel: `DC(${donchianPeriod}) ${sig.type === 'BUY' ? 'Upper' : 'Lower'}`,
        indicatorValue: sig.channelLevel,
        dcUpper: barReadout?.dcUpper ?? null,
        dcLower: barReadout?.dcLower ?? null,
        volRatio: Number(sig.volRatio.toFixed(2)),
        barsAgo: sig.barsAgo,
      };
    });

    // Institutional High-Volume Milestone Markers:
    // HVE = Highest Volume Ever, HVY = Highest Volume in Over a Year, HVQ = Highest Volume in a Quarter
    const hvSignals: ChartSignalEvent[] = [];
    const hvByDate = new Map<string, 'HVE' | 'HVY' | 'HVQ'>();
    const quarterBars = isWeekly ? 13 : 63;
    const yearBars = isWeekly ? 52 : 252;

    let globalMaxVol = 0;
    let globalMaxIdx = -1;
    for (let i = 0; i < activeBars.length; i++) {
      const v = activeBars[i].volume;
      if (Number.isFinite(v) && v > globalMaxVol) {
        globalMaxVol = v;
        globalMaxIdx = i;
      }
    }

    let runningMaxVol = 0;
    const minHveIdx = Math.min(yearBars, Math.max(quarterBars, Math.floor(activeBars.length * 0.35)));
    for (let i = 0; i < activeBars.length; i++) {
      const b = activeBars[i];
      const v = b.volume;
      if (!Number.isFinite(v) || v <= 0) continue;

      let badge: 'HVE' | 'HVY' | 'HVQ' | null = null;
      let hvFullLabel = '';

      if (i === globalMaxIdx && globalMaxVol > 0) {
        badge = 'HVE';
        hvFullLabel = 'Highest Volume Ever';
      } else if (i >= minHveIdx && runningMaxVol > 0 && v > runningMaxVol) {
        badge = 'HVE';
        hvFullLabel = 'Highest Volume Ever';
      } else if (i >= yearBars) {
        let maxYear = 0;
        for (let j = i - yearBars; j < i; j++) {
          if (activeBars[j].volume > maxYear) maxYear = activeBars[j].volume;
        }
        if (maxYear > 0 && v > maxYear) {
          badge = 'HVY';
          hvFullLabel = 'Highest Volume in Over a Year';
        }
      }

      if (!badge && i >= quarterBars) {
        let maxQuarter = 0;
        for (let j = i - quarterBars; j < i; j++) {
          if (activeBars[j].volume > maxQuarter) maxQuarter = activeBars[j].volume;
        }
        if (maxQuarter > 0 && v > maxQuarter) {
          badge = 'HVQ';
          hvFullLabel = 'Highest Volume in a Quarter';
        }
      }

      if (v > runningMaxVol) runningMaxVol = v;

      if (badge) {
        const avgV = volSma20[i];
        const vr =
          Number.isFinite(avgV) && avgV > 0 ? Number((v / avgV).toFixed(2)) : null;
        hvByDate.set(b.date, badge);
        hvSignals.push({
          id: `hv_${b.date}_${badge}`,
          date: b.date,
          source: 'HV',
          type: 'VOL',
          badge,
          triggerPrice: b.close,
          indicatorLabel: hvFullLabel,
          indicatorValue: b.high,
          volRatio: vr,
          volumeRaw: v,
          hvFullLabel,
          barsAgo: activeBars.length - 1 - i,
        });
      }
    }

    const signalsByDate = new Map<string, ChartSignalEvent[]>();
    for (const ev of [...stSignals, ...dcSignals, ...hvSignals]) {
      const list = signalsByDate.get(ev.date);
      if (list) list.push(ev);
      else signalsByDate.set(ev.date, [ev]);
    }

    // All-Time High (ATH) line & years elapsed since last ATH touch (e.g. "ATH 2.4 Yrs" when >= 6 months)
    const athInfo = (() => {
      if (dailyBars.length < 10) return null;
      const n = dailyBars.length;
      const lastIdx = n - 1;
      const latestBar = dailyBars[lastIdx];
      const toMs = (d: string) => Date.parse(d);
      const diffCalendarDays = (fromDate: string, toDate: string) => {
        const a = toMs(fromDate);
        const b = toMs(toDate);
        if (!Number.isFinite(a) || !Number.isFinite(b)) return 0;
        return Math.max(0, (b - a) / (1000 * 60 * 60 * 24));
      };

      let globalAthPrice = -Infinity;
      let globalAthIdx = 0;
      for (let i = 0; i < n; i++) {
        if (dailyBars[i].high >= globalAthPrice) {
          globalAthPrice = dailyBars[i].high;
          globalAthIdx = i;
        }
      }
      if (!(globalAthPrice > 0)) return null;

      const globalAthDate = dailyBars[globalAthIdx].date;
      const daysSinceGlobal = diffCalendarDays(globalAthDate, latestBar.date);

      let linePrice = globalAthPrice;
      let touchedDate = globalAthDate;
      let elapsedDays = daysSinceGlobal;

      // If price recently touched/broke ATH (< 6 months ago), check whether it just returned
      // to a prior ATH that had stood untouched for >= 6 months (e.g., 6M / 12M / 24M+ base).
      if (daysSinceGlobal < 180 && n > 60) {
        const recentWindowStart = Math.max(0, lastIdx - 42);
        let priorAthPrice = -Infinity;
        let priorAthIdx = -1;
        for (let i = 0; i < recentWindowStart; i++) {
          if (dailyBars[i].high >= priorAthPrice) {
            priorAthPrice = dailyBars[i].high;
            priorAthIdx = i;
          }
        }
        if (priorAthIdx >= 0 && priorAthPrice > 0) {
          let reclaimIdx = lastIdx;
          for (let i = recentWindowStart; i <= lastIdx; i++) {
            if (dailyBars[i].high >= priorAthPrice * 0.995) {
              reclaimIdx = i;
              break;
            }
          }
          const priorGapDays = diffCalendarDays(
            dailyBars[priorAthIdx].date,
            dailyBars[reclaimIdx].date
          );
          if (
            priorGapDays >= 180 &&
            latestBar.close >= priorAthPrice * 0.9 &&
            latestBar.close <= priorAthPrice * 1.18
          ) {
            linePrice = priorAthPrice;
            touchedDate = dailyBars[priorAthIdx].date;
            elapsedDays = priorGapDays;
          }
        }
      }

      const yearsSince = elapsedDays / 365.25;
      const showYears = elapsedDays >= 180; // >= 6 months (~0.5 Yrs, 1.0 Yrs, 2.0 Yrs, 2.4 Yrs...)
      const lineTitle = showYears ? `ATH ${yearsSince.toFixed(1)} Yrs` : 'ATH';
      const distPct = ((latestBar.close - linePrice) / linePrice) * 100;

      return {
        price: Number(linePrice.toFixed(2)),
        touchedDate,
        elapsedDays: Math.round(elapsedDays),
        yearsSince: Number(yearsSince.toFixed(1)),
        showYears,
        lineTitle,
        distPct,
      };
    })();

    return {
      smaSeries,
      volSma20,
      ema10,
      ema21,
      bb,
      donchian,
      supertrend,
      stSignals,
      dcSignals,
      hvSignals,
      hvByDate,
      signalsByDate,
      vwap20,
      rsi14,
      macd,
      adx14,
      rsLine,
      rsByDate,
      evalInd,
      setupDiag,
      keyLevels,
      athInfo,
      byDate,
    };
  }, [activeBars, dailyBars, interval, stock, customIndicator, symbolLabel, donchianPeriod]);

  const visibleKeyLevels = useMemo(
    () => computed.keyLevels.filter((lvl) => activeLevelVisibility[lvl.category]),
    [computed.keyLevels, activeLevelVisibility]
  );

  const latestReadout = useMemo(() => {
    if (!activeBars.length) return null;
    const lastDate = activeBars[activeBars.length - 1].date;
    return computed.byDate.get(lastDate) || null;
  }, [activeBars, computed]);

  const [hoveredReadout, setHoveredReadout] = useState<CrosshairReadout | null>(null);
  const [hoveredSignalTip, setHoveredSignalTip] = useState<{
    x: number;
    y: number;
    containerWidth: number;
    date: string;
    signals: ChartSignalEvent[];
  } | null>(null);
  const activeReadout = hoveredReadout || latestReadout;

  const isDark = theme === 'dark';
  const showCustomSubchart =
    interval === '1D' &&
    Boolean(
      customIndicator &&
        customIndicator.plotType === 'subchart' &&
        computed.evalInd &&
        !computed.evalInd.error
    );
  const activePaneKeys = useMemo(() => {
    const keys: ('custom' | SubPaneKey)[] = [];
    if (showCustomSubchart) keys.push('custom');
    for (const opt of SUB_PANE_OPTIONS) {
      if (enabledSubPanes[opt.id]) keys.push(opt.id);
    }
    return keys;
  }, [showCustomSubchart, enabledSubPanes]);

  const getVisibleBarsCount = () => {
    const days = RANGE_DAYS[range];
    return interval === '1W' ? Math.max(12, Math.ceil(days / 5)) : days;
  };

  // Main TradingView Lightweight Chart Lifecycle
  useEffect(() => {
    const el = mainContainerRef.current;
    if (!el || activeBars.length < 2) return;

    const bg = isDark ? '#0f172a' : '#ffffff';
    const textColor = isDark ? '#94a3b8' : '#475569';
    const gridColor = isDark ? 'rgba(148, 163, 184, 0.08)' : 'rgba(15, 23, 42, 0.07)';
    const borderColor = isDark ? '#1e293b' : '#e2e8f0';

    const chart = createChart(el, {
      width: el.clientWidth || 640,
      height,
      layout: {
        background: { type: ColorType.Solid, color: bg },
        textColor,
        fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: gridColor },
        horzLines: { color: gridColor },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: isDark ? 'rgba(148,163,184,0.4)' : 'rgba(15,23,42,0.35)',
          style: LineStyle.Dashed,
          labelBackgroundColor: isDark ? '#1e293b' : '#0f172a',
        },
        horzLine: {
          color: isDark ? 'rgba(148,163,184,0.4)' : 'rgba(15,23,42,0.35)',
          style: LineStyle.Dashed,
          labelBackgroundColor: isDark ? '#1e293b' : '#0f172a',
        },
      },
      rightPriceScale: {
        borderColor,
        mode: logScale ? PriceScaleMode.Logarithmic : PriceScaleMode.Normal,
        scaleMargins: {
          top: 0.08,
          bottom: showVolume ? 0.24 : 0.08,
        },
      },
      timeScale: {
        borderColor,
        timeVisible: false,
        rightOffset: 6,
        barSpacing:
          chartStyle === 'volume_candles'
            ? interval === '1W'
              ? 13
              : 10.5
            : interval === '1W'
            ? 9
            : 7,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    });
    chartRef.current = chart;

    // 1. Primary Price Series (TradingView-Style Dynamic-Width Volume Candles / Candlestick / Hollow / OHLC / Heikin-Ashi / Area / Line)
    // priceLineVisible: false removes the default dashed current-price horizontal line across the canvas
    let mainSeries: ISeriesApi<SeriesType, Time>;

    if (chartStyle === 'volume_candles') {
      const s = chart.addCustomSeries(new VolumeCandlesSeries(), {
        upColor: '#10b981',
        downColor: '#ef4444',
        wideUpColor: isDark ? 'rgba(16, 185, 129, 0.72)' : 'rgba(16, 185, 129, 0.74)',
        wideDownColor: isDark ? 'rgba(239, 68, 68, 0.72)' : 'rgba(239, 68, 68, 0.74)',
        borderUpColor: isDark ? '#34d399' : '#047857',
        borderDownColor: isDark ? '#f87171' : '#b91c1c',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
        minWidthScale: 0.82,
        maxWidthScale: 2.8,
        priceLineVisible: false,
      });
      const volData: VolumeCandleData[] = activeBars.map((b, i) => {
        const avgV = computed.volSma20[i];
        const volRatio20 =
          b.volume > 0 && Number.isFinite(avgV) && avgV > 0 ? b.volume / avgV : 1;
        return {
          time: b.date as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
          volume: b.volume,
          volRatio20,
        };
      });
      s.setData(volData);
      mainSeries = s;
    } else if (chartStyle === 'candlestick') {
      const s = chart.addSeries(CandlestickSeries, {
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
        priceLineVisible: false,
      });
      s.setData(
        activeBars.map((b) => ({
          time: b.date as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
      );
      mainSeries = s;
    } else if (chartStyle === 'hollow') {
      const s = chart.addSeries(CandlestickSeries, {
        upColor: 'rgba(16, 185, 129, 0)',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
        priceLineVisible: false,
      });
      s.setData(
        activeBars.map((b) => ({
          time: b.date as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
      );
      mainSeries = s;
    } else if (chartStyle === 'heikin') {
      const s = chart.addSeries(CandlestickSeries, {
        upColor: '#10b981',
        downColor: '#ef4444',
        borderUpColor: '#10b981',
        borderDownColor: '#ef4444',
        wickUpColor: '#10b981',
        wickDownColor: '#ef4444',
        priceLineVisible: false,
      });
      s.setData(computeHeikinAshi(activeBars));
      mainSeries = s;
    } else if (chartStyle === 'ohlc') {
      const s = chart.addSeries(BarSeries, {
        upColor: '#10b981',
        downColor: '#ef4444',
        thinBars: false,
        priceLineVisible: false,
      });
      s.setData(
        activeBars.map((b) => ({
          time: b.date as Time,
          open: b.open,
          high: b.high,
          low: b.low,
          close: b.close,
        }))
      );
      mainSeries = s;
    } else if (chartStyle === 'area') {
      const s = chart.addSeries(AreaSeries, {
        lineColor: '#2563eb',
        topColor: 'rgba(37, 99, 235, 0.28)',
        bottomColor: 'rgba(37, 99, 235, 0.0)',
        lineWidth: 2,
        priceLineVisible: false,
      });
      s.setData(activeBars.map((b) => ({ time: b.date as Time, value: b.close })));
      mainSeries = s;
    } else {
      const s = chart.addSeries(LineSeries, {
        color: '#2563eb',
        lineWidth: 2,
        priceLineVisible: false,
      });
      s.setData(activeBars.map((b) => ({ time: b.date as Time, value: b.close })));
      mainSeries = s;
    }

    // 2. Price Reference Lines (ATH High Line, Pivot, Prior 52W High, Stop-Loss + Filtered Breakout, Major/Minor Support & Resistance)
    const drawnPrices: number[] = [];
    const registerLine = (price: number) => drawnPrices.push(price);
    const hasNearbyLine = (price: number) =>
      drawnPrices.some((p) => Math.abs(p - price) / Math.max(0.01, p) < 0.008);

    if (showAthLine && computed.athInfo && computed.athInfo.price > 0) {
      registerLine(computed.athInfo.price);
      mainSeries.createPriceLine({
        price: computed.athInfo.price,
        color: '#d946ef',
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: computed.athInfo.lineTitle,
      });
    }

    if (activeLevelVisibility.breakout && pivotPrice && pivotPrice > 0) {
      registerLine(pivotPrice);
      mainSeries.createPriceLine({
        price: pivotPrice,
        color: '#10b981',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '',
      });
    }
    if (activeLevelVisibility.breakout && prior52WHigh && prior52WHigh > 0 && !hasNearbyLine(prior52WHigh)) {
      registerLine(prior52WHigh);
      mainSeries.createPriceLine({
        price: prior52WHigh,
        color: '#0ea5e9',
        lineWidth: 1,
        lineStyle: LineStyle.Dotted,
        axisLabelVisible: true,
        title: '',
      });
    }
    if (activeLevelVisibility.major_support && stopLossPrice && stopLossPrice > 0 && !hasNearbyLine(stopLossPrice)) {
      registerLine(stopLossPrice);
      mainSeries.createPriceLine({
        price: stopLossPrice,
        color: '#ef4444',
        lineWidth: 1,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: '',
      });
    }

    if (visibleKeyLevels.length > 0) {
      for (const lvl of visibleKeyLevels) {
        if (hasNearbyLine(lvl.price)) continue;
        registerLine(lvl.price);
        const color =
          lvl.kind === 'breakout'
            ? '#10b981'
            : lvl.kind === 'support_flip'
            ? '#0ea5e9'
            : lvl.category === 'major_resistance'
            ? '#f59e0b'
            : lvl.category === 'minor_resistance'
            ? '#fbbf24'
            : lvl.category === 'major_support'
            ? '#ef4444'
            : '#fb923c';
        const isMajorLine = lvl.strength === 'Major';
        mainSeries.createPriceLine({
          price: lvl.price,
          color,
          lineWidth: isMajorLine ? 2 : 1,
          lineStyle: isMajorLine ? LineStyle.Solid : LineStyle.Dashed,
          axisLabelVisible: true,
          title: '',
        });
      }
    }

    const addLineOverlay = (
      vals: number[],
      color: string,
      lineStyle: LineStyle = LineStyle.Solid,
      lineWidth: 1 | 2 = 1
    ) => {
      const pts = activeBars
        .map((b, i) =>
          Number.isFinite(vals[i]) ? { time: b.date as Time, value: Number(vals[i].toFixed(2)) } : null
        )
        .filter((x): x is { time: Time; value: number } => x !== null);
      if (pts.length > 2) {
        const line = chart.addSeries(LineSeries, {
          color,
          lineWidth,
          lineStyle,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        });
        line.setData(pts);
      }
    };

    // 3. Individual Simple Moving Averages (SMA 21 / 50 / 100 / 150 / 200)
    for (const cfg of SMA_OVERLAY_CONFIGS) {
      if (enabledSmas[cfg.period]) {
        addLineOverlay(computed.smaSeries[cfg.period], cfg.color);
      }
    }

    // 4. Institutional Swing EMAs (10 EMA / 21 EMA)
    if (showEmas) {
      addLineOverlay(computed.ema10, '#14b8a6');
      addLineOverlay(computed.ema21, '#ec4899');
    }

    // 5. Bollinger Bands (20, 2)
    if (showBollinger) {
      addLineOverlay(computed.bb.upper, 'rgba(99, 102, 241, 0.7)', LineStyle.Dashed);
      addLineOverlay(computed.bb.lower, 'rgba(99, 102, 241, 0.7)', LineStyle.Dashed);
    }

    // 5B. Donchian Channel (Upper / Mid / Lower)
    if (showDonchian) {
      addLineOverlay(computed.donchian.upper, '#06b6d4', LineStyle.Solid, 2);
      addLineOverlay(computed.donchian.mid, 'rgba(6, 182, 212, 0.48)', LineStyle.Dashed, 1);
      addLineOverlay(computed.donchian.lower, '#f43f5e', LineStyle.Solid, 2);
    }

    // 5C. Supertrend (10, 3) Bullish / Bearish Trailing Band
    if (showSupertrend) {
      const bullPts = activeBars.map((b, i) =>
        Number.isFinite(computed.supertrend.line[i]) && computed.supertrend.direction[i] === 1
          ? { time: b.date as Time, value: Number(computed.supertrend.line[i].toFixed(2)) }
          : { time: b.date as Time }
      );
      const bearPts = activeBars.map((b, i) =>
        Number.isFinite(computed.supertrend.line[i]) && computed.supertrend.direction[i] === -1
          ? { time: b.date as Time, value: Number(computed.supertrend.line[i].toFixed(2)) }
          : { time: b.date as Time }
      );
      const stBull = chart.addSeries(LineSeries, {
        color: '#10b981',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      stBull.setData(bullPts);
      const stBear = chart.addSeries(LineSeries, {
        color: '#ef4444',
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      stBear.setData(bearPts);
    }

    // 6. Rolling 20-bar VWAP
    if (showVwap) {
      addLineOverlay(computed.vwap20, '#eab308', LineStyle.Dotted, 2);
    }

    // 7. Custom Indicator Overlay & Decoupled Signal Markers (ST B/S, DC B/S, PP / NR7)
    // ST and DC signal markers plot independently even when ST (10,3) and DC (20) lines are hidden.
    // Indicator lines ONLY render when showDonchian / showSupertrend are explicitly selected.
    const markers: SeriesMarker<Time>[] = [];
    const plotStMarkers = showStMarkers;
    const plotDcMarkers = showDcMarkers;
    const plotHvMarkers = showHvMarkers;

    if (customIndicator && computed.evalInd && !computed.evalInd.error) {
      if (customIndicator.plotType === 'overlay') {
        addLineOverlay(computed.evalInd.values, customIndicator.color, LineStyle.Solid, 2);
      }
      for (let i = 0; i < activeBars.length; i++) {
        if (computed.evalInd.buySignals[i]) {
          markers.push({
            time: activeBars[i].date as Time,
            position: 'belowBar',
            color: '#10b981',
            shape: 'arrowUp',
            text: 'B',
          });
        } else if (computed.evalInd.sellSignals[i]) {
          markers.push({
            time: activeBars[i].date as Time,
            position: 'aboveBar',
            color: '#ef4444',
            shape: 'arrowDown',
            text: 'S',
          });
        }
      }
    } else {
      const priorityDates = new Set<string>();
      if (plotHvMarkers && computed.hvSignals.length > 0) {
        for (const sig of computed.hvSignals.slice(-40)) {
          markers.push({
            time: sig.date as Time,
            position: 'aboveBar',
            color:
              sig.badge === 'HVE'
                ? '#f59e0b'
                : sig.badge === 'HVY'
                ? '#0ea5e9'
                : '#a855f7',
            shape: 'circle',
            text: sig.badge,
          });
        }
      }
      if (plotStMarkers && computed.stSignals.length > 0) {
        for (const sig of computed.stSignals.slice(-24)) {
          priorityDates.add(sig.date);
          markers.push({
            time: sig.date as Time,
            position: sig.type === 'BUY' ? 'belowBar' : 'aboveBar',
            color: sig.type === 'BUY' ? '#10b981' : '#ef4444',
            shape: sig.type === 'BUY' ? 'arrowUp' : 'arrowDown',
            text: sig.badge,
          });
        }
      }
      if (plotDcMarkers && computed.dcSignals.length > 0) {
        for (const sig of computed.dcSignals.slice(0, 24)) {
          priorityDates.add(sig.date);
          markers.push({
            time: sig.date as Time,
            position: sig.type === 'BUY' ? 'belowBar' : 'aboveBar',
            color: sig.type === 'BUY' ? '#06b6d4' : '#f43f5e',
            shape: sig.type === 'BUY' ? 'arrowUp' : 'arrowDown',
            text: sig.badge,
          });
        }
      }
      if (showSetupMarkers && computed.setupDiag) {
        const ppSet = new Set(computed.setupDiag.pocketPivotDates);
        const nr7Set = new Set(computed.setupDiag.nr7Dates);
        for (const b of activeBars) {
          if (priorityDates.has(b.date)) continue;
          if (ppSet.has(b.date)) {
            markers.push({
              time: b.date as Time,
              position: 'belowBar',
              color: '#10b981',
              shape: 'arrowUp',
              text: 'PP',
            });
          } else if (nr7Set.has(b.date) && !computed.hvByDate.has(b.date)) {
            markers.push({
              time: b.date as Time,
              position: 'aboveBar',
              color: '#f59e0b',
              shape: 'circle',
              text: 'NR7',
            });
          }
        }
      }
    }

    if (markers.length > 0) {
      markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
      createSeriesMarkers(mainSeries, markers.slice(-110));
    }

    // 8. Color-Coded Volume Histogram Pane (highlights HVE / HVY / HVQ spikes cleanly)
    const hasVolume = activeBars.some((b) => b.volume > 0);
    if (showVolume && hasVolume) {
      const volSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: 'volume' },
        priceScaleId: 'volume',
        priceLineVisible: false,
        lastValueVisible: false,
      });
      chart.priceScale('volume').applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });
      volSeries.setData(
        activeBars.map((b) => {
          const hvTag = plotHvMarkers ? computed.hvByDate.get(b.date) : undefined;
          const color =
            hvTag === 'HVE'
              ? isDark
                ? 'rgba(245, 158, 11, 0.78)'
                : 'rgba(217, 119, 6, 0.78)'
              : hvTag === 'HVY'
              ? isDark
                ? 'rgba(14, 165, 233, 0.72)'
                : 'rgba(2, 132, 199, 0.72)'
              : hvTag === 'HVQ'
              ? isDark
                ? 'rgba(168, 85, 247, 0.68)'
                : 'rgba(147, 51, 234, 0.68)'
              : b.close >= b.open
              ? isDark
                ? 'rgba(16, 185, 129, 0.38)'
                : 'rgba(16, 185, 129, 0.42)'
              : isDark
              ? 'rgba(239, 68, 68, 0.38)'
              : 'rgba(239, 68, 68, 0.42)';
          return {
            time: b.date as Time,
            value: b.volume,
            color,
          };
        })
      );
    }

    // 9. Set visible range cleanly
    const visibleBars = getVisibleBarsCount();
    const total = activeBars.length;
    if (total > visibleBars) {
      chart.timeScale().setVisibleLogicalRange({
        from: total - visibleBars,
        to: total + 4,
      });
    } else {
      chart.timeScale().fitContent();
    }

    // 10. Sync time scale from main chart to all active stacked indicator panes
    chart.timeScale().subscribeVisibleLogicalRangeChange((logicalRange) => {
      if (!logicalRange || isSyncingRangeRef.current) return;
      isSyncingRangeRef.current = true;
      subChartsRef.current.forEach((subChart) => {
        try {
          subChart.timeScale().setVisibleLogicalRange(logicalRange);
        } catch {
          // ignore range sync mismatch during unmount
        }
      });
      isSyncingRangeRef.current = false;
    });

    // 11. Live Crosshair OHLCV HUD & Signal Badge Hover Tooltip Subscription
    chart.subscribeCrosshairMove((param) => {
      if (!param.time) {
        setHoveredReadout(null);
        setHoveredSignalTip(null);
        return;
      }
      const dateKey = String(param.time);
      const hit = computed.byDate.get(dateKey);
      setHoveredReadout(hit || null);

      const rawSigs = computed.signalsByDate.get(dateKey);
      const activeSigs = rawSigs
        ? rawSigs.filter(
            (s) =>
              (s.source === 'ST' && plotStMarkers) ||
              (s.source === 'DC' && plotDcMarkers) ||
              (s.source === 'HV' && plotHvMarkers)
          )
        : [];
      if (activeSigs.length > 0 && param.point && param.point.x >= 0 && param.point.y >= 0) {
        setHoveredSignalTip({
          x: param.point.x,
          y: param.point.y,
          containerWidth: el.clientWidth || 640,
          date: dateKey,
          signals: activeSigs,
        });
      } else {
        setHoveredSignalTip(null);
      }
    });

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.floor(entry.contentRect.width);
        if (w > 50) chart.applyOptions({ width: w });
      }
    });
    ro.observe(el);

    return () => {
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [
    activeBars,
    computed,
    visibleKeyLevels,
    activeLevelVisibility,
    chartStyle,
    interval,
    range,
    enabledSmas,
    showEmas,
    showBollinger,
    showDonchian,
    donchianPeriod,
    showSupertrend,
    showStMarkers,
    showDcMarkers,
    showHvMarkers,
    showAthLine,
    showVwap,
    showSetupMarkers,
    showVolume,
    logScale,
    isDark,
    height,
    pivotPrice,
    prior52WHigh,
    stopLossPrice,
    customIndicator,
  ]);

  // Multi-Indicator Stacked Synchronized Sub-Chart Panes (Custom, RS vs NIFTY 500, RSI 14, MACD, ADX 14)
  useEffect(() => {
    if (activePaneKeys.length === 0 || activeBars.length < 2) {
      subChartsRef.current.clear();
      return;
    }

    const bg = isDark ? '#0f172a' : '#ffffff';
    const textColor = isDark ? '#94a3b8' : '#475569';
    const gridColor = isDark ? 'rgba(148, 163, 184, 0.08)' : 'rgba(15, 23, 42, 0.07)';
    const borderColor = isDark ? '#1e293b' : '#e2e8f0';

    const createdCharts: { key: string; chart: IChartApi; ro: ResizeObserver }[] = [];

    // Whitespace-padded series builder ensures 1:1 logical bar index alignment with main price chart
    const alignLineData = (values: number[], decimals = 2) =>
      activeBars.map((b, i) =>
        Number.isFinite(values[i])
          ? { time: b.date as Time, value: Number(values[i].toFixed(decimals)) }
          : { time: b.date as Time }
      );

    const initialRange =
      chartRef.current?.timeScale().getVisibleLogicalRange() ??
      (() => {
        const visibleBars = getVisibleBarsCount();
        const total = activeBars.length;
        return total > visibleBars ? { from: total - visibleBars, to: total + 4 } : null;
      })();

    for (const paneKey of activePaneKeys) {
      const el = subContainersRef.current.get(paneKey);
      if (!el) continue;

      const subChart = createChart(el, {
        width: el.clientWidth || 640,
        height: 112,
        layout: {
          background: { type: ColorType.Solid, color: bg },
          textColor,
          fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, monospace",
          fontSize: 10,
        },
        grid: {
          vertLines: { color: gridColor },
          horzLines: { color: gridColor },
        },
        crosshair: {
          mode: CrosshairMode.Normal,
          vertLine: {
            color: isDark ? 'rgba(148,163,184,0.35)' : 'rgba(15,23,42,0.3)',
            style: LineStyle.Dashed,
            labelBackgroundColor: isDark ? '#1e293b' : '#0f172a',
          },
          horzLine: {
            color: isDark ? 'rgba(148,163,184,0.35)' : 'rgba(15,23,42,0.3)',
            style: LineStyle.Dashed,
            labelBackgroundColor: isDark ? '#1e293b' : '#0f172a',
          },
        },
        rightPriceScale: { borderColor },
        timeScale: { borderColor, timeVisible: false, rightOffset: 6 },
      });

      if (paneKey === 'custom' && customIndicator && computed.evalInd) {
        const line = subChart.addSeries(LineSeries, {
          color: customIndicator.color,
          lineWidth: 2,
        });
        line.setData(alignLineData(computed.evalInd.values, 3));
        line.createPriceLine({
          price: 0,
          color: isDark ? 'rgba(148,163,184,0.35)' : 'rgba(100,116,139,0.4)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: false,
          title: '',
        });
      } else if (paneKey === 'rs') {
        // Green zone fill when outperforming NIFTY 500 (RS >= 100), Red zone fill when underperforming (RS < 100)
        const rsSeries = subChart.addSeries(BaselineSeries, {
          baseValue: { type: 'price', price: 100 },
          topLineColor: '#10b981',
          topFillColor1: isDark ? 'rgba(16, 185, 129, 0.36)' : 'rgba(16, 185, 129, 0.28)',
          topFillColor2: 'rgba(16, 185, 129, 0.03)',
          bottomLineColor: '#ef4444',
          bottomFillColor1: 'rgba(239, 68, 68, 0.03)',
          bottomFillColor2: isDark ? 'rgba(239, 68, 68, 0.36)' : 'rgba(239, 68, 68, 0.28)',
          lineWidth: 2,
          priceLineVisible: false,
        });
        const rsData = activeBars.map((b) => {
          const val = computed.rsByDate.get(b.date);
          return val !== undefined ? { time: b.date as Time, value: val } : { time: b.date as Time };
        });
        rsSeries.setData(rsData);
        rsSeries.createPriceLine({
          price: 100,
          color: isDark ? 'rgba(148, 163, 184, 0.45)' : 'rgba(100, 116, 139, 0.5)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: '100',
        });
        const rsWin = computed.rsLine.slice(-252);
        const maxRs = rsWin.length ? Math.max(...rsWin.map((p) => p.value)) : 100;
        rsSeries.createPriceLine({
          price: maxRs,
          color: '#10b981',
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          axisLabelVisible: true,
          title: '52W RS H',
        });

        // Mark RS outperformance breakouts (crossing above 100 or breaking rolling 60-bar RS high above 100)
        const rsMarkers: SeriesMarker<Time>[] = [];
        let lastRsMarkIdx = -20;
        for (let i = 20; i < computed.rsLine.length; i++) {
          const cur = computed.rsLine[i].value;
          const prev = computed.rsLine[i - 1].value;
          const lookStart = Math.max(0, i - 60);
          let priorMax = 0;
          for (let j = lookStart; j < i; j++) {
            if (computed.rsLine[j].value > priorMax) priorMax = computed.rsLine[j].value;
          }
          const crossedAboveParity = prev < 100 && cur >= 100;
          const brokeOutHigh = cur > 100 && cur > priorMax * 1.005;
          if ((crossedAboveParity || brokeOutHigh) && i - lastRsMarkIdx >= 12) {
            rsMarkers.push({
              time: computed.rsLine[i].date as Time,
              position: 'aboveBar',
              color: '#10b981',
              shape: 'arrowUp',
              text: crossedAboveParity ? 'RS>100' : 'RS BO',
            });
            lastRsMarkIdx = i;
          }
        }
        if (rsMarkers.length > 0) {
          createSeriesMarkers(rsSeries, rsMarkers.slice(-14));
        }
      } else if (paneKey === 'rsi') {
        const rsiSeries = subChart.addSeries(LineSeries, {
          color: '#8b5cf6',
          lineWidth: 2,
          priceLineVisible: false,
        });
        const rsiColoredData = activeBars.map((b, i) => {
          const val = computed.rsi14[i];
          if (!Number.isFinite(val)) return { time: b.date as Time };
          return {
            time: b.date as Time,
            value: Number(val.toFixed(2)),
            color: val > 60 ? '#10b981' : '#8b5cf6',
          };
        });
        rsiSeries.setData(rsiColoredData);
        rsiSeries.createPriceLine({
          price: 70,
          color: 'rgba(239, 68, 68, 0.55)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: '70',
        });
        rsiSeries.createPriceLine({
          price: 60,
          color: 'rgba(16, 185, 129, 0.55)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: '60',
        });
        rsiSeries.createPriceLine({
          price: 30,
          color: 'rgba(148, 163, 184, 0.5)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: '30',
        });
      } else if (paneKey === 'macd') {
        const histSeries = subChart.addSeries(HistogramSeries, {
          priceLineVisible: false,
          lastValueVisible: false,
        });
        histSeries.setData(
          activeBars.map((b, i) =>
            Number.isFinite(computed.macd.hist[i])
              ? {
                  time: b.date as Time,
                  value: Number(computed.macd.hist[i].toFixed(2)),
                  color:
                    computed.macd.hist[i] >= 0
                      ? 'rgba(16, 185, 129, 0.55)'
                      : 'rgba(239, 68, 68, 0.55)',
                }
              : { time: b.date as Time }
          )
        );
        const mLine = subChart.addSeries(LineSeries, { color: '#38bdf8', lineWidth: 2 });
        mLine.setData(alignLineData(computed.macd.macd, 2));
        const sLine = subChart.addSeries(LineSeries, { color: '#f59e0b', lineWidth: 1 });
        sLine.setData(alignLineData(computed.macd.signal, 2));
      } else if (paneKey === 'adx') {
        const adxLine = subChart.addSeries(LineSeries, {
          color: '#10b981',
          lineWidth: 2,
          priceLineVisible: false,
        });
        const adxColoredData = activeBars.map((b, i) => {
          const adxVal = computed.adx14.adx[i];
          const pDi = computed.adx14.plusDi[i];
          const mDi = computed.adx14.minusDi[i];
          if (!Number.isFinite(adxVal)) return { time: b.date as Time };
          const isBuySignal =
            Number.isFinite(pDi) && Number.isFinite(mDi) ? pDi >= mDi : true;
          return {
            time: b.date as Time,
            value: Number(adxVal.toFixed(2)),
            color: isBuySignal ? '#10b981' : '#ef4444',
          };
        });
        adxLine.setData(adxColoredData);
        adxLine.createPriceLine({
          price: 25,
          color: isDark ? 'rgba(148, 163, 184, 0.45)' : 'rgba(100, 116, 139, 0.5)',
          lineWidth: 1,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: '25',
        });
        const plusLine = subChart.addSeries(LineSeries, {
          color: isDark ? 'rgba(16, 185, 129, 0.42)' : 'rgba(16, 185, 129, 0.48)',
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        plusLine.setData(alignLineData(computed.adx14.plusDi, 2));
        const minusLine = subChart.addSeries(LineSeries, {
          color: isDark ? 'rgba(239, 68, 68, 0.42)' : 'rgba(239, 68, 68, 0.48)',
          lineWidth: 1,
          lineStyle: LineStyle.Dotted,
          priceLineVisible: false,
          lastValueVisible: false,
        });
        minusLine.setData(alignLineData(computed.adx14.minusDi, 2));
      }

      if (initialRange) {
        try {
          subChart.timeScale().setVisibleLogicalRange(initialRange);
        } catch {
          subChart.timeScale().fitContent();
        }
      } else {
        subChart.timeScale().fitContent();
      }

      // Sync pan/zoom from this indicator pane back to main chart and sibling panes
      subChart.timeScale().subscribeVisibleLogicalRangeChange((logicalRange) => {
        if (!logicalRange || isSyncingRangeRef.current) return;
        isSyncingRangeRef.current = true;
        if (chartRef.current) {
          try {
            chartRef.current.timeScale().setVisibleLogicalRange(logicalRange);
          } catch {
            // ignore
          }
        }
        subChartsRef.current.forEach((otherChart, otherKey) => {
          if (otherKey === paneKey) return;
          try {
            otherChart.timeScale().setVisibleLogicalRange(logicalRange);
          } catch {
            // ignore
          }
        });
        isSyncingRangeRef.current = false;
      });

      // Sync crosshair readout when hovering on any indicator pane
      subChart.subscribeCrosshairMove((param) => {
        if (!param.time) {
          setHoveredReadout(null);
          return;
        }
        const hit = computed.byDate.get(String(param.time));
        setHoveredReadout(hit || null);
      });

      const ro = new ResizeObserver((entries) => {
        for (const entry of entries) {
          const w = Math.floor(entry.contentRect.width);
          if (w > 50) subChart.applyOptions({ width: w });
        }
      });
      ro.observe(el);

      subChartsRef.current.set(paneKey, subChart);
      createdCharts.push({ key: paneKey, chart: subChart, ro });
    }

    return () => {
      for (const item of createdCharts) {
        item.ro.disconnect();
        item.chart.remove();
        subChartsRef.current.delete(item.key);
      }
    };
  }, [activeBars, computed, activePaneKeys, customIndicator, range, interval, isDark]);

  const handleResetZoom = () => {
    if (!chartRef.current) return;
    const visibleBars = getVisibleBarsCount();
    const total = activeBars.length;
    if (total > visibleBars) {
      chartRef.current.timeScale().setVisibleLogicalRange({
        from: total - visibleBars,
        to: total + 4,
      });
    } else {
      chartRef.current.timeScale().fitContent();
    }
  };

  const titleSymbol = symbolLabel || stock?.ticker || 'NSE';
  const unitSuffix = interval === '1W' ? 'W' : 'D';

  return (
    <div className="space-y-2">
      {/* Compact Pre-Chart Call / Score + Multi-Indicator Signal Matrix Summary Strip */}
      {preChartSummary && (
        <div
          className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/60 flex flex-wrap items-center justify-between gap-x-4 gap-y-1 text-xs"
          title={`Call / Score (${preChartSummary.compositeScore}/100): Technical & Trend ${preChartSummary.techScore}/60 (incl. Matrix ${preChartSummary.matrixScore}/20) · Setup ${preChartSummary.setupScore}/15 · Fundamentals ${preChartSummary.fundaScore}/25`}
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="inline-flex items-baseline gap-1.5">
              <span className="text-[11px] font-semibold text-slate-500">Call / Score:</span>
              <strong
                className={
                  preChartSummary.rating === 'Strong Buy'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : preChartSummary.rating === 'Buy'
                    ? 'text-blue-600 dark:text-blue-400'
                    : 'text-amber-600 dark:text-amber-400'
                }
              >
                {preChartSummary.rating}
              </strong>
              <span className="font-mono font-bold tabular-nums text-slate-900 dark:text-slate-100">
                {preChartSummary.compositeScore}/100
              </span>
            </span>

            <span className="text-slate-300 dark:text-slate-700">|</span>

            <span className="inline-flex items-baseline gap-1.5">
              <span className="text-[11px] font-semibold text-slate-500">Indicators Matrix Summary:</span>
              <strong
                className={`font-mono tabular-nums ${
                  preChartSummary.technicalConsensus === 'Strong Buy' ||
                  preChartSummary.technicalConsensus === 'Buy'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : preChartSummary.technicalConsensus === 'Neutral'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {preChartSummary.technicalConsensus} · {preChartSummary.matrixScorePct}/100
              </strong>
              <span className="font-mono text-[10px] tabular-nums text-slate-500">
                ({preChartSummary.bullishSignals}/{preChartSummary.totalSignals}B)
              </span>
            </span>
          </div>

          {preChartSummary.sectorQuadrant && (
            <span className="inline-flex items-baseline gap-1 text-[11px] font-mono tabular-nums">
              <span className="font-sans text-slate-500">Sector:</span>
              <strong className="text-slate-800 dark:text-slate-200">
                {preChartSummary.sectorScore ?? '—'}/100
              </strong>
              <span
                className={`font-sans font-semibold ${
                  preChartSummary.sectorQuadrant === 'Leading'
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : preChartSummary.sectorQuadrant === 'Improving'
                    ? 'text-blue-600 dark:text-blue-400'
                    : preChartSummary.sectorQuadrant === 'Weakening'
                    ? 'text-amber-600 dark:text-amber-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                · {preChartSummary.sectorQuadrant}
              </span>
            </span>
          )}
        </div>
      )}

      {/* Row 1: Chart Style + Interval (1D/1W) + Range + Scale */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <div className="flex flex-wrap items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
            {CHART_STYLE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setChartStyle(opt.id)}
                className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors whitespace-nowrap ${
                  chartStyle === opt.id
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
            {(['1D', '1W'] as IntervalKey[]).map((iv) => (
              <button
                key={iv}
                onClick={() => setIntervalMode(iv)}
                className={`px-2 py-1 text-[11px] font-mono font-semibold rounded-md transition-colors whitespace-nowrap ${
                  interval === iv
                    ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
                title={iv === '1D' ? 'Daily NSE Candles' : 'Weekly Aggregated Candles'}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <div className="flex items-center gap-0.5 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800">
            {(['1M', '3M', '6M', '1Y', '2Y', '3Y'] as RangeKey[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-2 py-1 text-[11px] font-mono font-medium rounded-md transition-colors ${
                  range === r
                    ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                    : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                {r}
              </button>
            ))}
          </div>

          <button
            onClick={() => setLogScale((l) => !l)}
            className={`px-2 py-1 text-[11px] font-mono font-medium rounded-md border transition-colors ${
              logScale
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-500'
            }`}
            title="Toggle Logarithmic / Linear Price Scale"
          >
            {logScale ? 'LOG' : 'LIN'}
          </button>

          <button
            onClick={handleResetZoom}
            className="p-1.5 rounded-md border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100"
            title="Fit / Reset Zoom"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={handleSaveDefaultTemplate}
            className={`inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium rounded-md border transition-colors whitespace-nowrap ${
              templateToast === 'saved'
                ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                : hasSavedTemplate
                ? 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300 hover:bg-blue-500/20'
                : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-300 hover:border-blue-500/50 hover:text-blue-600 dark:hover:text-blue-400'
            }`}
            title="Save currently selected indicators, style, and sub-panes as your default chart template"
          >
            {templateToast === 'saved' ? (
              <Check className="w-3.5 h-3.5 text-emerald-500" />
            ) : (
              <BookmarkCheck className="w-3.5 h-3.5" />
            )}
            <span>
              {templateToast === 'saved'
                ? 'Template Saved'
                : hasSavedTemplate
                ? 'Update Default'
                : 'Save Default'}
            </span>
          </button>

          {hasSavedTemplate && (
            <button
              onClick={handleResetDefaultTemplate}
              className="p-1.5 rounded-md border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-red-500 hover:border-red-500/40 transition-colors"
              title="Clear saved default chart template and restore factory indicators"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Row 2A: Individual SMA (21/50/100/150/200) + Technical Overlays + Oscillator Pane */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px]">
        <div className="flex flex-wrap items-center gap-1.5">
          {/* Individual Selectable SMAs: 21, 50, 100, 150, 200 */}
          <div
            className="inline-flex flex-wrap items-center gap-1 px-1.5 py-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/70"
            role="group"
            aria-label="Simple Moving Averages"
          >
            <span className="text-[10px] font-semibold text-slate-500 px-1 whitespace-nowrap">
              SMA:
            </span>
            {SMA_OVERLAY_CONFIGS.map((cfg) => {
              const active = enabledSmas[cfg.period];
              return (
                <button
                  key={cfg.period}
                  onClick={() => toggleSma(cfg.period)}
                  className={`inline-flex items-center gap-1 px-1.5 py-0.5 font-mono font-semibold rounded border transition-colors whitespace-nowrap ${
                    active
                      ? cfg.activeClass
                      : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                  title={`Toggle ${cfg.period}${unitSuffix} Simple Moving Average`}
                >
                  <span
                    className="w-2 h-0.5 rounded-full inline-block"
                    style={{ backgroundColor: active ? cfg.color : '#64748b' }}
                  />
                  {cfg.shortLabel}
                </button>
              );
            })}
          </div>

          <button
            onClick={() => setShowEmas((v) => !v)}
            className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
              showEmas
                ? 'border-teal-500/40 bg-teal-500/10 text-teal-700 dark:text-teal-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-500'
            }`}
          >
            EMA 10/21
          </button>
          <button
            onClick={() => setShowBollinger((v) => !v)}
            className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
              showBollinger
                ? 'border-indigo-500/40 bg-indigo-500/10 text-indigo-700 dark:text-indigo-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-500'
            }`}
          >
            BB (20,2)
          </button>
          <div className="inline-flex items-center gap-0.5">
            <button
              onClick={() => setShowDonchian((v) => !v)}
              className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
                showDonchian
                  ? 'border-cyan-500 bg-cyan-600 text-white shadow-xs'
                  : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
              title="Toggle Donchian Channel upper/mid/lower lines on chart (signal markers work independently)"
            >
              DC ({donchianPeriod}) Lines
            </button>
            {(showDonchian || showDcMarkers) && (
              <div className="inline-flex items-center p-0.5 rounded-md border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900">
                {([10, 20, 55] as DonchianPeriod[]).map((p) => (
                  <button
                    key={p}
                    onClick={() => setDonchianPeriod(p)}
                    className={`px-1.5 py-0.5 font-mono text-[10px] rounded transition-colors ${
                      donchianPeriod === p
                        ? 'bg-cyan-600 text-white font-semibold'
                        : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={() => setShowSupertrend((v) => !v)}
            className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
              showSupertrend
                ? 'border-emerald-500 bg-emerald-600 text-white shadow-xs'
                : 'border-slate-200 dark:border-slate-800 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
            title="Toggle Supertrend (10, 3) trailing line on chart (signal markers work independently)"
          >
            ST (10,3) Line
          </button>
          <button
            onClick={() => setShowVwap((v) => !v)}
            className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
              showVwap
                ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-500'
            }`}
          >
            VWAP 20
          </button>

          {/* Independent Decoupled Signal Markers Only: ST / DC / PP-NR7 (work even when ST & DC lines are OFF) */}
          <div
            className="inline-flex flex-wrap items-center gap-1 px-1.5 py-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/70"
            role="group"
            aria-label="Signal Markers Only"
          >
            <span className="text-[10px] font-semibold text-slate-500 px-1 whitespace-nowrap">
              Signal Markers:
            </span>
            <button
              onClick={() => setShowStMarkers((v) => !v)}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 font-mono font-semibold rounded border transition-colors whitespace-nowrap ${
                showStMarkers
                  ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Show Supertrend (ST B / ST S) alert markers on candles even when ST line is hidden"
            >
              <span
                className="w-1.5 h-1.5 rounded-full inline-block"
                style={{ backgroundColor: showStMarkers ? '#10b981' : '#64748b' }}
              />
              ST
            </button>
            <button
              onClick={() => setShowDcMarkers((v) => !v)}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 font-mono font-semibold rounded border transition-colors whitespace-nowrap ${
                showDcMarkers
                  ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Show Donchian Channel (DC B / DC S) alert markers on candles even when DC lines are hidden"
            >
              <span
                className="w-1.5 h-1.5 rounded-full inline-block"
                style={{ backgroundColor: showDcMarkers ? '#06b6d4' : '#64748b' }}
              />
              DC
            </button>
            <button
              onClick={() => setShowHvMarkers((v) => !v)}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 font-mono font-semibold rounded border transition-colors whitespace-nowrap ${
                showHvMarkers
                  ? 'border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Show Highest Volume Ever (HVE), Highest Volume in Over a Year (HVY), and Highest Volume in a Quarter (HVQ) on top of relevant bars"
            >
              <span
                className="w-1.5 h-1.5 rounded-full inline-block"
                style={{ backgroundColor: showHvMarkers ? '#f59e0b' : '#64748b' }}
              />
              HVE/HVY/HVQ
            </button>
            <button
              onClick={() => setShowSetupMarkers((v) => !v)}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 font-mono font-semibold rounded border transition-colors whitespace-nowrap ${
                showSetupMarkers
                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300'
                  : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Show Pocket Pivot (PP) & Narrow Range 7 (NR7) markers"
            >
              PP/NR7
            </button>
          </div>

          <button
            onClick={() => setShowVolume((v) => !v)}
            className={`px-2 py-1 font-medium rounded-md border transition-colors whitespace-nowrap ${
              showVolume
                ? 'border-blue-500/40 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                : 'border-slate-200 dark:border-slate-800 text-slate-500'
            }`}
          >
            Vol
          </button>
        </div>

        {/* Multi-Select Indicator Sub-Panes (can enable any combination simultaneously) */}
        <div
          className="inline-flex flex-wrap items-center gap-1 px-1.5 py-0.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/70"
          role="group"
          aria-label="Indicator Sub-Panes"
        >
          <span className="text-[10px] font-semibold text-slate-500 px-1 whitespace-nowrap">
            Panes:
          </span>
          {SUB_PANE_OPTIONS.map((o) => {
            const active = enabledSubPanes[o.id];
            return (
              <button
                key={o.id}
                onClick={() => toggleSubPane(o.id)}
                className={`inline-flex items-center gap-1 px-2 py-0.5 font-medium rounded border transition-colors whitespace-nowrap ${
                  active
                    ? o.activeClass
                    : 'border-transparent text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
                title={`Toggle ${o.label} sub-pane below chart`}
              >
                <span
                  className="w-1.5 h-1.5 rounded-full inline-block"
                  style={{ backgroundColor: active ? o.color : '#64748b' }}
                />
                {o.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Row 2B: Individual Select/Deselect for ATH High Line, Breakout, Major & Minor Resistance, Major & Minor Support */}
      <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
        <span className="text-[10px] font-semibold text-slate-500 whitespace-nowrap">
          Price Levels:
        </span>
        <button
          onClick={() => setShowAthLine((v) => !v)}
          className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-medium rounded-md border transition-colors whitespace-nowrap ${
            showAthLine
              ? 'border-fuchsia-500/50 bg-fuchsia-500/10 text-fuchsia-700 dark:text-fuchsia-300'
              : 'border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
          title={
            computed.athInfo
              ? `Toggle All-Time High line (${formatINR(computed.athInfo.price)}, last touched ${computed.athInfo.touchedDate}${
                  computed.athInfo.showYears ? ` · ${computed.athInfo.yearsSince.toFixed(1)} Yrs ago` : ''
                })`
              : 'Toggle All-Time High (ATH) line on chart'
          }
        >
          <span
            className="w-2.5 inline-block"
            style={{
              borderTop: `2px dashed ${showAthLine ? '#d946ef' : '#64748b'}`,
            }}
          />
          {computed.athInfo ? computed.athInfo.lineTitle : 'ATH'}
        </button>
        {LEVEL_TOGGLE_CONFIGS.map((cfg) => {
          const active = activeLevelVisibility[cfg.key];
          const isMinor = cfg.key.startsWith('minor_');
          return (
            <button
              key={cfg.key}
              onClick={() => toggleLevelCategory(cfg.key)}
              className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-medium rounded-md border transition-colors whitespace-nowrap ${
                active
                  ? cfg.activeClass
                  : 'border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
              }`}
              title={`Toggle ${cfg.label} lines on chart`}
            >
              <span
                className="w-2.5 inline-block"
                style={{
                  borderTop: `${isMinor ? '1.5px dashed' : '2px solid'} ${
                    active ? cfg.color : '#64748b'
                  }`,
                }}
              />
              {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Row 3: Live Interactive Crosshair OHLCV Readout Strip */}
      {activeReadout && (
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900/80 border border-slate-200/80 dark:border-slate-800 text-[11px] font-mono tabular-nums">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5">
            <span className="font-bold text-slate-900 dark:text-slate-100">
              {titleSymbol} · {interval}
            </span>
            <span className="text-slate-500">{activeReadout.date}</span>
            <span>
              <span className="text-slate-400">O </span>
              {formatINR(activeReadout.open)}
            </span>
            <span>
              <span className="text-slate-400">H </span>
              <span className="text-emerald-600 dark:text-emerald-400">
                {formatINR(activeReadout.high)}
              </span>
            </span>
            <span>
              <span className="text-slate-400">L </span>
              <span className="text-red-600 dark:text-red-400">
                {formatINR(activeReadout.low)}
              </span>
            </span>
            <span>
              <span className="text-slate-400">C </span>
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                {formatINR(activeReadout.close)}
              </span>
            </span>
            <span
              className={
                activeReadout.changePct >= 0
                  ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                  : 'text-red-600 dark:text-red-400 font-semibold'
              }
            >
              {formatPct(activeReadout.changePct)}
            </span>
            {activeReadout.volume > 0 && (
              <span className="text-slate-500">
                Vol {(activeReadout.volume / 1e6).toFixed(2)}M
                {activeReadout.volRatio20 !== null ? (
                  <strong
                    className={`ml-1 ${
                      activeReadout.volRatio20 >= 1.5
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : activeReadout.volRatio20 < 0.65
                        ? 'text-slate-400'
                        : 'text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    ({activeReadout.volRatio20.toFixed(2)}×)
                  </strong>
                ) : null}
              </span>
            )}
            {chartStyle === 'volume_candles' && (
              <span
                className="hidden xl:inline-flex items-center gap-1.5 text-[10px] font-sans text-slate-400 ml-1"
                title="Candle width scales proportionally to relative volume (25% to 250%)"
              >
                <span>· Vol Width:</span>
                <span className="inline-block w-1 h-2.5 rounded-xs bg-emerald-500" />
                <span>Low</span>
                <span className="inline-block w-2 h-2.5 rounded-xs bg-emerald-500" />
                <span>Avg</span>
                <span className="inline-block w-3.5 h-2.5 rounded-xs bg-emerald-500" />
                <span>High</span>
              </span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {SMA_OVERLAY_CONFIGS.map((cfg) => {
              const val = activeReadout.smas[cfg.period];
              if (!enabledSmas[cfg.period] || val === null) return null;
              return (
                <span key={cfg.period} className={cfg.textClass}>
                  SMA{cfg.period} {formatINR(val, 0)}
                </span>
              );
            })}
            {showEmas && activeReadout.ema21 !== null && (
              <span className="text-teal-500">21E {formatINR(activeReadout.ema21, 0)}</span>
            )}
            {showDonchian &&
              activeReadout.dcUpper !== null &&
              activeReadout.dcLower !== null && (
                <span className="text-cyan-600 dark:text-cyan-400">
                  DC{donchianPeriod} U {formatINR(activeReadout.dcUpper, 0)} · L{' '}
                  {formatINR(activeReadout.dcLower, 0)}
                </span>
              )}
            {showSupertrend && activeReadout.supertrendVal !== null && (
              <span
                className={
                  activeReadout.supertrendDir === 1
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }
              >
                ST {formatINR(activeReadout.supertrendVal, 0)}
              </span>
            )}
            {showVwap && activeReadout.vwap20 !== null && (
              <span className="text-yellow-600 dark:text-yellow-400">
                VWAP {formatINR(activeReadout.vwap20, 0)}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Row 4: Selected ATH, Breakout, Major/Minor Support & Resistance Levels Strip */}
      {(visibleKeyLevels.length > 0 || (showAthLine && computed.athInfo)) && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5 rounded-lg bg-slate-50/70 dark:bg-slate-900/50 border border-slate-200/70 dark:border-slate-800/80 text-[11px] font-mono tabular-nums">
          <span className="font-sans font-semibold text-slate-600 dark:text-slate-400">
            Active Levels ({interval}):
          </span>
          {showAthLine && computed.athInfo && (
            <span
              className="inline-flex items-center gap-1 whitespace-nowrap"
              title={`Last touched on ${computed.athInfo.touchedDate}`}
            >
              <span className="font-semibold text-fuchsia-600 dark:text-fuchsia-400">
                {computed.athInfo.lineTitle}
              </span>
              <span className="text-slate-900 dark:text-slate-100 font-semibold">
                {formatINR(computed.athInfo.price)}
              </span>
              <span className="text-slate-500">
                ({computed.athInfo.distPct >= 0 ? '+' : ''}
                {computed.athInfo.distPct.toFixed(1)}% · {computed.athInfo.touchedDate})
              </span>
            </span>
          )}
          {visibleKeyLevels.map((lvl) => {
            const tone =
              lvl.kind === 'breakout'
                ? 'text-emerald-600 dark:text-emerald-400'
                : lvl.kind === 'support_flip'
                ? 'text-sky-600 dark:text-sky-400'
                : lvl.category === 'major_resistance'
                ? 'text-amber-600 dark:text-amber-400'
                : lvl.category === 'minor_resistance'
                ? 'text-yellow-600 dark:text-yellow-400'
                : lvl.category === 'major_support'
                ? 'text-red-600 dark:text-red-400'
                : 'text-orange-600 dark:text-orange-400';
            return (
              <span key={lvl.id} className="inline-flex items-center gap-1 whitespace-nowrap">
                <span className={`font-semibold ${tone}`}>{lvl.label}</span>
                <span className="text-slate-900 dark:text-slate-100 font-semibold">
                  {formatINR(lvl.price)}
                </span>
                <span className="text-slate-500">
                  ({lvl.distPct >= 0 ? '+' : ''}
                  {lvl.distPct.toFixed(1)}%
                  {lvl.touches > 1 ? ` · ${lvl.touches}T` : ''})
                </span>
              </span>
            );
          })}
        </div>
      )}

      {/* Main TradingView Lightweight Canvas Container + Floating Signal Badge Hover Tooltip */}
      <div className="relative rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800">
        <div ref={mainContainerRef} style={{ width: '100%', height }} />
        {hoveredSignalTip && hoveredSignalTip.signals.length > 0 && (
          <div
            className="pointer-events-none absolute z-20 w-56 rounded-lg border border-slate-200 dark:border-slate-700 bg-white/95 dark:bg-slate-900/95 shadow-lg backdrop-blur-xs px-2.5 py-2 text-[11px]"
            style={{
              left:
                hoveredSignalTip.x > hoveredSignalTip.containerWidth - 245
                  ? Math.max(8, hoveredSignalTip.x - 236)
                  : Math.min(hoveredSignalTip.containerWidth - 232, hoveredSignalTip.x + 14),
              top: Math.max(8, Math.min(height - 110, hoveredSignalTip.y - 16)),
            }}
          >
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-500 pb-1 mb-1 border-b border-slate-200/80 dark:border-slate-800">
              <span>Signal Alert</span>
              <span>{hoveredSignalTip.date}</span>
            </div>
            <div className="space-y-1.5">
              {hoveredSignalTip.signals.map((sig) => (
                <div key={sig.id} className="space-y-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`font-mono font-bold text-[11px] ${
                        sig.source === 'HV'
                          ? sig.badge === 'HVE'
                            ? 'text-amber-600 dark:text-amber-400'
                            : sig.badge === 'HVY'
                            ? 'text-sky-600 dark:text-sky-400'
                            : 'text-purple-600 dark:text-purple-400'
                          : sig.source === 'DC'
                          ? sig.type === 'BUY'
                            ? 'text-cyan-600 dark:text-cyan-400'
                            : 'text-rose-600 dark:text-rose-400'
                          : sig.type === 'BUY'
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {sig.source === 'HV'
                        ? `${sig.badge} · Volume Milestone`
                        : `${sig.badge} · ${sig.type === 'BUY' ? 'Buy Signal' : 'Sell Signal'}`}
                    </span>
                    <span className="font-mono tabular-nums font-semibold text-slate-900 dark:text-slate-100">
                      {formatINR(sig.triggerPrice)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] font-mono tabular-nums text-slate-500">
                    <span>{sig.indicatorLabel}</span>
                    <span className="text-slate-700 dark:text-slate-300">
                      {sig.source === 'HV'
                        ? (() => {
                            const v = sig.volumeRaw ?? 0;
                            return v >= 1e7
                              ? `${(v / 1e7).toFixed(2)} Cr`
                              : v >= 1e5
                              ? `${(v / 1e5).toFixed(2)} L`
                              : v.toLocaleString('en-IN');
                          })()
                        : formatINR(sig.indicatorValue)}
                    </span>
                  </div>
                  {sig.source === 'HV' && sig.volRatio ? (
                    <div className="text-[10px] font-mono tabular-nums text-slate-400">
                      {sig.volRatio.toFixed(2)}× 20D avg vol · High {formatINR(sig.indicatorValue)}
                    </div>
                  ) : null}
                  {sig.source === 'DC' && sig.dcUpper !== null && sig.dcLower !== null && (
                    <div className="text-[10px] font-mono tabular-nums text-slate-400">
                      U {formatINR(sig.dcUpper ?? 0, 0)} · L {formatINR(sig.dcLower ?? 0, 0)}
                      {sig.volRatio ? ` · ${sig.volRatio.toFixed(2)}× vol` : ''}
                    </div>
                  )}
                  {sig.source === 'ST' && sig.volRatio ? (
                    <div className="text-[10px] font-mono tabular-nums text-slate-400">
                      Vol {sig.volRatio.toFixed(2)}× 20D avg
                    </div>
                  ) : null}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Multi-Indicator Stacked Synchronized Sub-Panes (RS vs N500, RSI 14, MACD, ADX 14) */}
      {activePaneKeys.length > 0 && (
        <div className="space-y-2 pt-0.5">
          {activePaneKeys.map((paneKey, idx) => (
            <div key={paneKey} className="space-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono tabular-nums">
                <div className="flex flex-wrap items-center gap-2.5">
                  {paneKey === 'custom' && customIndicator ? (
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      {customIndicator.code} · {customIndicator.name}
                      {activeReadout?.indVal !== null && activeReadout?.indVal !== undefined
                        ? ` = ${activeReadout.indVal}`
                        : ''}
                    </span>
                  ) : paneKey === 'rs' ? (
                    <span
                      className={`font-semibold ${
                        (activeReadout?.rsVal ?? 100) >= 100
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      RS vs NIFTY 500
                      {activeReadout?.rsVal !== null && activeReadout?.rsVal !== undefined
                        ? ` = ${activeReadout.rsVal} (${
                            activeReadout.rsVal >= 100 ? 'Outperforming' : 'Underperforming'
                          } ${activeReadout.rsVal >= 100 ? '+' : ''}${(
                            activeReadout.rsVal - 100
                          ).toFixed(1)}%)`
                        : ''}
                    </span>
                  ) : paneKey === 'rsi' ? (
                    <span
                      className={`font-semibold ${
                        activeReadout?.rsi14 !== null &&
                        activeReadout?.rsi14 !== undefined &&
                        activeReadout.rsi14 > 60
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : 'text-violet-600 dark:text-violet-400'
                      }`}
                    >
                      RSI (14)
                      {activeReadout?.rsi14 !== null && activeReadout?.rsi14 !== undefined
                        ? ` = ${activeReadout.rsi14}${activeReadout.rsi14 > 60 ? ' · Strong (>60)' : ''}`
                        : ''}
                    </span>
                  ) : paneKey === 'macd' ? (
                    <>
                      <span className="font-semibold text-sky-600 dark:text-sky-400">
                        MACD (12, 26, 9)
                        {activeReadout?.macdVal !== null && activeReadout?.macdVal !== undefined
                          ? ` ${activeReadout.macdVal}`
                          : ''}
                      </span>
                      {activeReadout?.macdSig !== null && activeReadout?.macdSig !== undefined && (
                        <span className="text-amber-600 dark:text-amber-400">
                          Sig {activeReadout.macdSig}
                        </span>
                      )}
                      {activeReadout?.macdHist !== null && activeReadout?.macdHist !== undefined && (
                        <span
                          className={
                            activeReadout.macdHist >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }
                        >
                          Hist {activeReadout.macdHist >= 0 ? '+' : ''}
                          {activeReadout.macdHist}
                        </span>
                      )}
                    </>
                  ) : (
                    <>
                      {(() => {
                        const pDi = activeReadout?.plusDi14;
                        const mDi = activeReadout?.minusDi14;
                        const hasDi = pDi !== null && pDi !== undefined && mDi !== null && mDi !== undefined;
                        const isBuy = hasDi ? pDi >= mDi : true;
                        return (
                          <span
                            className={`font-semibold ${
                              hasDi
                                ? isBuy
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                                : 'text-amber-600 dark:text-amber-400'
                            }`}
                          >
                            ADX (14)
                            {activeReadout?.adx14 !== null && activeReadout?.adx14 !== undefined
                              ? ` ${activeReadout.adx14}`
                              : ''}
                            {hasDi ? (isBuy ? ' · BUY' : ' · SELL') : ''}
                          </span>
                        );
                      })()}
                      {activeReadout?.plusDi14 !== null && activeReadout?.plusDi14 !== undefined && (
                        <span className="text-emerald-600/80 dark:text-emerald-400/80">
                          +DI {activeReadout.plusDi14}
                        </span>
                      )}
                      {activeReadout?.minusDi14 !== null && activeReadout?.minusDi14 !== undefined && (
                        <span className="text-red-600/80 dark:text-red-400/80">
                          -DI {activeReadout.minusDi14}
                        </span>
                      )}
                    </>
                  )}
                </div>

                {idx === 0 && (
                  <span className="text-slate-500 font-sans">
                    Synced time-axis · Scroll to zoom · Drag to pan
                  </span>
                )}
              </div>

              <div className="rounded-lg overflow-hidden border border-slate-200 dark:border-slate-800">
                <div
                  ref={(node) => {
                    if (node) subContainersRef.current.set(paneKey, node);
                    else subContainersRef.current.delete(paneKey);
                  }}
                  style={{ width: '100%', height: 112 }}
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Donchian Channel Recent Buy & Sell Alerts (Always shown at the bottom · Last 2 rows only) */}
      {computed.donchian.currentUpper !== null && (
        <div className="rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/50 overflow-hidden">
          <div className="px-3 py-2 border-b border-slate-200/80 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-[11px]">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-0.5">
              <span className="font-semibold text-slate-900 dark:text-slate-100">
                Donchian Channel ({donchianPeriod}
                {unitSuffix}) · Recent Buy &amp; Sell Alerts (Last 2)
              </span>
              <span className="font-mono tabular-nums text-slate-500">
                U <strong className="text-cyan-600 dark:text-cyan-400">{formatINR(computed.donchian.currentUpper)}</strong> · M{' '}
                <span>{formatINR(computed.donchian.currentMid ?? 0)}</span> · L{' '}
                <strong className="text-rose-600 dark:text-rose-400">{formatINR(computed.donchian.currentLower ?? 0)}</strong> · Width{' '}
                {computed.donchian.channelWidthPct.toFixed(1)}%
              </span>
            </div>

            <div className="flex items-center gap-2">
              <div className="inline-flex items-center p-0.5 rounded-md bg-white dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                {(['ALL', 'BUY', 'SELL'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setDonchianAlertFilter(f)}
                    className={`px-2 py-0.5 text-[10px] font-medium rounded transition-colors ${
                      donchianAlertFilter === f
                        ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                        : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                    }`}
                  >
                    {f === 'ALL' ? 'All' : f === 'BUY' ? 'Buy' : 'Sell'}
                  </button>
                ))}
              </div>
              {computed.donchian.latestSignal && (
                <button
                  onClick={() => {
                    const s = computed.donchian.latestSignal!;
                    void addAlert({
                      ticker: titleSymbol,
                      category: 'price',
                      title: `${titleSymbol} — Donchian (${donchianPeriod}${unitSuffix}) ${s.type} Alert at ${formatINR(s.triggerPrice)}`,
                      message: `${s.type === 'BUY' ? 'Closed above' : 'Closed below'} prior ${donchianPeriod}-bar ${s.type === 'BUY' ? 'high' : 'low'} (${formatINR(s.channelLevel)}) on ${s.date} (${s.volRatio.toFixed(1)}× vol).`,
                    });
                    setPushedAlertId(s.id);
                    setTimeout(() => setPushedAlertId(null), 2400);
                  }}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium rounded-md border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 hover:border-blue-500 whitespace-nowrap"
                >
                  {pushedAlertId === computed.donchian.latestSignal.id ? (
                    <Check className="w-3 h-3 text-emerald-500" />
                  ) : (
                    <BellPlus className="w-3 h-3 text-blue-500" />
                  )}
                  {pushedAlertId === computed.donchian.latestSignal.id ? 'Alert Saved' : 'Push Latest'}
                </button>
              )}
            </div>
          </div>

          {(() => {
            const visibleAlerts = computed.donchian.recentAlerts
              .filter((a) => donchianAlertFilter === 'ALL' || a.type === donchianAlertFilter)
              .slice(0, 2);
            if (visibleAlerts.length === 0) {
              return (
                <div className="px-3 py-3 text-[11px] text-slate-500">
                  No recent Donchian ({donchianPeriod}
                  {unitSuffix}) {donchianAlertFilter === 'ALL' ? 'buy or sell' : donchianAlertFilter.toLowerCase()} alerts triggered in this chart window.
                </div>
              );
            }
            return (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-[11px] font-mono tabular-nums">
                  <thead className="border-b border-slate-200/70 dark:border-slate-800 text-[10px] font-sans text-slate-500">
                    <tr>
                      <th className="py-1.5 px-3">Signal</th>
                      <th className="py-1.5 px-2.5">Alert Date</th>
                      <th className="py-1.5 px-2.5 text-right">Channel Trigger</th>
                      <th className="py-1.5 px-2.5 text-right">DC Signal Price</th>
                      <th className="py-1.5 px-2.5 text-right">Break %</th>
                      <th className="py-1.5 px-2.5 text-right">Vol Ratio</th>
                      <th className="py-1.5 px-3 text-right">Move Since Alert</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/60 dark:divide-slate-800/60">
                    {visibleAlerts.map((a) => (
                      <tr key={a.id} className="hover:bg-white/70 dark:hover:bg-slate-800/40">
                        <td className="py-1.5 px-3 font-sans font-bold whitespace-nowrap">
                          <span
                            className={
                              a.type === 'BUY'
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }
                          >
                            {a.type === 'BUY' ? '▲ BUY Breakout' : '▼ SELL Breakdown'}
                          </span>
                        </td>
                        <td className="py-1.5 px-2.5 text-slate-600 dark:text-slate-300 whitespace-nowrap">
                          {a.date}{' '}
                          <span className="text-slate-400">
                            ({a.barsAgo === 0 ? 'Latest' : `${a.barsAgo}${unitSuffix} ago`})
                          </span>
                        </td>
                        <td className="py-1.5 px-2.5 text-right text-slate-600 dark:text-slate-300">
                          {formatINR(a.channelLevel)}
                        </td>
                        <td className="py-1.5 px-2.5 text-right font-semibold text-slate-900 dark:text-slate-100">
                          {formatINR(a.triggerPrice)}
                        </td>
                        <td
                          className={`py-1.5 px-2.5 text-right ${
                            a.type === 'BUY'
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {a.breakoutPct >= 0 ? '+' : ''}
                          {a.breakoutPct.toFixed(2)}%
                        </td>
                        <td className="py-1.5 px-2.5 text-right text-slate-700 dark:text-slate-300">
                          {a.volRatio.toFixed(2)}×
                        </td>
                        <td
                          className={`py-1.5 px-3 text-right font-semibold ${
                            a.rawMovePct >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(a.rawMovePct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
};
