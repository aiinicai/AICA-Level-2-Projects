import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  ArrowDown,
  ArrowLeft,
  Bell,
  Check,
  CheckCircle2,
  Compass,
  Layers,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Star,
  TrendingUp,
  Users,
  XCircle,
} from 'lucide-react';
import { renderStructuredAiLines } from '../components/AiDeskDrawer';
import { IndianTickerSearchInput } from '../components/IndianTickerSearchInput';
import {
  DEFAULT_LEVEL_VISIBILITY,
  LEVEL_TOGGLE_CONFIGS,
  LevelVisibilityState,
  StockChartPanel,
  loadSavedChartTemplate,
} from '../components/StockChartPanel';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, LiveQuotePayload, STOCK_BY_TICKER } from '../data/indianMarketData';
import { DEFAULT_TREND_THRESHOLDS, runMinerviniAnalysis } from '../engine/analyticsEngine';
import { resolveStockSectorContext } from '../engine/sectorTrendEngine';
import {
  LevelCategory,
  computeMultiIndicatorMatrix,
  computeOnDemandMinerviniChecklist,
  computeShareholdingStrengthCheck,
  computeSingleStockCallScore,
  detectKeyBreakoutSupportLevels,
  diagnoseBarsForSetups,
  resampleToWeekly,
} from '../engine/tradeRadarEngine';
import { TradeJournalEntry } from '../types/market';
import { postAiJson } from '../utils/aiClient';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

interface LiveMetricGrowth {
  latestQuarterDate: string | null;
  latestQuarterVal: number | null;
  qoqPct: number | null;
  yoyPct: number | null;
  yoyBasis: string;
  latestAnnualDate: string | null;
  latestAnnualVal: number | null;
  annualYoYPct: number | null;
}

interface LiveFundamentalsPayload {
  symbol: string;
  yahooSymbol: string;
  name: string;
  sector: string;
  industry: string;
  ratios: {
    marketCapCr: number | null;
    pe: number | null;
    evToEbitda: number | null;
    pb: number | null;
    roePct: number | null;
    dividendYieldPct: number | null;
    opMarginPct: number | null;
    netMarginPct: number | null;
    debtToEquity: number | null;
  };
  growth: {
    sales: LiveMetricGrowth;
    ebitda: LiveMetricGrowth;
    netProfit: LiveMetricGrowth;
    eps: LiveMetricGrowth;
  };
  quarterlyHistory: {
    date: string;
    salesCr: number | null;
    ebitdaCr: number | null;
    ebitdaMarginPct: number | null;
    netProfitCr: number | null;
    eps: number | null;
  }[];
  shareholdingMeta?: {
    insidersPct: number | null;
    institutionsPct: number | null;
    quarterlySharesCr: { date: string; sharesCr: number | null }[];
  };
}

interface StockDetailViewProps {
  ticker: string;
  prior52WHigh?: number;
  backLabel: string;
  onBack: () => void;
  onSelectTicker: (ticker: string) => void;
}

const SETUP_NAME_MAP: Record<string, string> = {
  POCKET_PIVOT: 'Pocket Pivot',
  RS_BLUE_DOT: 'RS Blue-Dot',
  NR7_SQUEEZE: 'NR7 Squeeze',
  MA_PULLBACK: '21E/50S Pullback',
  EPISODIC_PIVOT: 'Episodic Pivot',
  VCP_BREAKOUT: 'VCP Breakout',
  WEEKLY_STAGE2: 'Weekly Stage 2',
};

function fmtRatio(val: number | null | undefined, suffix = '×'): string {
  if (val === null || val === undefined || !Number.isFinite(val)) return '—';
  return `${val.toFixed(2)}${suffix}`;
}

function fmtGrowthCell(val: number | null | undefined): { text: string; tone: string } {
  if (val === null || val === undefined || !Number.isFinite(val)) {
    return { text: '—', tone: 'text-slate-400' };
  }
  return {
    text: `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`,
    tone:
      val >= 15
        ? 'text-emerald-600 dark:text-emerald-400 font-bold'
        : val >= 0
        ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
        : 'text-red-600 dark:text-red-400 font-semibold',
  };
}

export const StockDetailView: React.FC<StockDetailViewProps> = ({
  ticker,
  prior52WHigh,
  backLabel,
  onBack,
  onSelectTicker,
}) => {
  const { watchlist, toggleWatchlist, addAlert, marketVersion } = useAppData();

  const coreStock = STOCK_BY_TICKER[ticker] || null;
  const coreSepa = useMemo(() => {
    if (!coreStock) return null;
    const all = runMinerviniAnalysis(INDIAN_STOCKS, DEFAULT_TREND_THRESHOLDS);
    return all.find((x) => x.stock.ticker === coreStock.ticker) ?? null;
  }, [coreStock, marketVersion]);

  // On-demand OHLCV quote for non-core symbols
  const [liveQuote, setLiveQuote] = useState<LiveQuotePayload | null>(null);
  const [loadingQuote, setLoadingQuote] = useState(false);
  const [quoteError, setQuoteError] = useState<string | null>(null);

  // Live Yahoo Finance fundamentals (for BOTH core stocks and any on-demand NSE/BSE stock)
  const [liveFund, setLiveFund] = useState<LiveFundamentalsPayload | null>(null);
  const [loadingFund, setLoadingFund] = useState(false);

  // Local UI state
  const [srTimeframe, setSrTimeframe] = useState<'1D' | '1W'>('1D');
  const [levelVisibility, setLevelVisibility] = useState<LevelVisibilityState>(
    () => loadSavedChartTemplate()?.levelVisibility ?? DEFAULT_LEVEL_VISIBILITY
  );
  const [capitalInr, setCapitalInr] = useState<number>(1000000);
  const [riskPct, setRiskPct] = useState<number>(1.0);
  const [journalSaved, setJournalSaved] = useState(false);
  const [alertSaved, setAlertSaved] = useState(false);

  // On-demand free-tier AI TechnoFunda Brief state (never auto-fired on navigation)
  const [aiBrief, setAiBrief] = useState<string | null>(null);
  const [aiBriefLoading, setAiBriefLoading] = useState(false);
  const [aiBriefError, setAiBriefError] = useState<string | null>(null);
  const [aiBriefMeta, setAiBriefMeta] = useState<string | null>(null);

  const handleToggleLevelCategory = (category: LevelCategory) => {
    setLevelVisibility((prev) => ({ ...prev, [category]: !prev[category] }));
  };

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior });
    setAiBrief(null);
    setAiBriefError(null);
    setAiBriefMeta(null);
  }, [ticker]);

  // Fetch on-demand OHLCV candles if not in core universe
  useEffect(() => {
    if (coreStock) {
      setLiveQuote(null);
      setLoadingQuote(false);
      setQuoteError(null);
      return;
    }
    let cancelled = false;
    setLoadingQuote(true);
    setQuoteError(null);
    setLiveQuote(null);

    fetch(`/api/market/quote/${encodeURIComponent(ticker)}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Live NSE/BSE OHLCV feed unavailable for ${ticker}`);
        return (await res.json()) as LiveQuotePayload;
      })
      .then((data) => {
        if (!cancelled) {
          setLiveQuote(data);
          setLoadingQuote(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setQuoteError(err instanceof Error ? err.message : `Failed to load ${ticker}`);
          setLoadingQuote(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ticker, coreStock]);

  // Fetch live fundamentals (Market Cap, P/E, EV/EBITDA, P/B, ROE, Div Yield, YoY & QoQ Sales/EBITDA/Net Profit/EPS)
  useEffect(() => {
    let cancelled = false;
    setLoadingFund(true);
    setLiveFund(null);

    fetch(`/api/market/fundamentals/${encodeURIComponent(ticker)}`)
      .then(async (res) => {
        if (!res.ok) return null;
        return (await res.json()) as LiveFundamentalsPayload;
      })
      .then((data) => {
        if (!cancelled) {
          setLiveFund(data);
          setLoadingFund(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setLiveFund(null);
          setLoadingFund(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const activeBars = coreStock ? coreStock.bars : liveQuote?.bars || [];
  const latestClose = coreStock ? coreStock.latestClose : liveQuote?.latestClose ?? 0;
  const dailyChangePct = coreStock ? coreStock.dailyChangePct : liveQuote?.dailyChangePct ?? 0;
  const avgTurnoverCr = coreStock
    ? coreStock.avgDailyTurnoverCr
    : liveQuote?.avgDailyTurnoverCr ?? 0;

  const companyName = liveFund?.name || coreStock?.name || ticker;
  const sectorName =
    coreStock?.sector || (liveFund?.sector && liveFund.sector !== 'Indian Equity' ? liveFund.sector : 'NSE Equity');
  const industryName = coreStock?.industry || liveFund?.industry || '';

  // Support & Resistance Breakouts (Daily & Weekly)
  const srLevels = useMemo(() => {
    if (activeBars.length < 25) return [];
    const barsForSr = srTimeframe === '1W' ? resampleToWeekly(activeBars) : activeBars;
    return detectKeyBreakoutSupportLevels(barsForSr, srTimeframe === '1W');
  }, [activeBars, srTimeframe]);

  const filteredSrLevels = useMemo(
    () => srLevels.filter((lvl) => levelVisibility[lvl.category]),
    [srLevels, levelVisibility]
  );

  // Setup Diagnosis (Pocket Pivot, RS Blue-Dot, NR7 Squeeze, Trigger, Stop, 1R/2R/3R)
  const setupDiag = useMemo(() => {
    if (activeBars.length < 60) return null;
    return diagnoseBarsForSetups(activeBars, {
      ticker,
      name: companyName,
      sector: sectorName,
      capBucket: coreStock?.capBucket || 'NSE',
      avgDailyTurnoverCr: avgTurnoverCr,
      rsRating: coreSepa?.rsRating,
      stage: coreSepa?.stage,
      templatePassed: coreSepa?.passedCount,
      minerviniScore: coreSepa?.minerviniScore,
      isVcpBreakout: coreSepa?.vcp.isPivotBreakout,
      vcpPivot: coreSepa?.vcp.pivotPrice,
    });
  }, [activeBars, ticker, companyName, sectorName, coreStock, avgTurnoverCr, coreSepa]);

  // Minervini SEPA Checklist (Uses full engine for core stocks OR on-demand SEPA engine for any NSE/BSE stock)
  const onDemandSepa = useMemo(() => {
    if (coreSepa || activeBars.length < 60) return null;
    return computeOnDemandMinerviniChecklist(activeBars, {
      qtrEpsYoY: liveFund?.growth.eps.yoyPct,
      qtrRevYoY: liveFund?.growth.sales.yoyPct,
      roePct: liveFund?.ratios.roePct,
    });
  }, [coreSepa, activeBars, liveFund]);

  const sepaSummary = useMemo(() => {
    if (coreSepa) {
      return {
        passedCount: coreSepa.passedCount,
        allPassed: coreSepa.allPassed,
        stage: coreSepa.stage,
        stageLabel: coreSepa.stageLabel,
        rsRating: coreSepa.rsRating,
        minerviniScore: coreSepa.minerviniScore,
        pivotPrice: coreSepa.vcp.pivotPrice,
        stopLossInr: coreSepa.suggestedStopLossInr,
        vcpDetail: coreSepa.vcp.isPivotBreakout
          ? `${coreSepa.vcp.tCount}T VCP Pivot Breakout (${coreSepa.vcp.breakoutVolumeRatio}× Vol)`
          : `${coreSepa.vcp.tCount}T VCP Base (${coreSepa.vcp.baseWeeks}W) · Pivot ${formatINR(coreSepa.vcp.pivotPrice)} · Vol Dry-Up ${coreSepa.vcp.volumeDryUpRatio}×`,
        conditions: coreSepa.conditions,
      };
    }
    if (onDemandSepa) {
      return {
        passedCount: onDemandSepa.passedCount,
        allPassed: onDemandSepa.allPassed,
        stage: onDemandSepa.stage,
        stageLabel: onDemandSepa.stageLabel,
        rsRating: onDemandSepa.rsRating,
        minerviniScore: onDemandSepa.minerviniScore,
        pivotPrice: onDemandSepa.pivotPrice,
        stopLossInr: onDemandSepa.suggestedStopLossInr,
        vcpDetail: onDemandSepa.vcpSummary,
        conditions: onDemandSepa.conditions,
      };
    }
    return null;
  }, [coreSepa, onDemandSepa]);

  // NSE Sectors Technical Scorecard & Sector / Sub-Sector RRG Quadrant lookup (O(1) cached)
  const sectorScorecard = useMemo(
    () => resolveStockSectorContext(INDIAN_STOCKS, sectorName, industryName, marketVersion),
    [sectorName, industryName, marketVersion]
  );

  // Multi-Indicator Signal Matrix (16 indicators including Donchian Channel, Supertrend, SEPA Checklist, RSI 55-80, NSE Sector Scorecard & Quadrant)
  const signalMatrix = useMemo(
    () =>
      computeMultiIndicatorMatrix(
        activeBars,
        sepaSummary
          ? {
              minerviniScore: sepaSummary.minerviniScore,
              passedCount: sepaSummary.passedCount,
              stage: sepaSummary.stage,
              rsRating: sepaSummary.rsRating,
            }
          : null,
        sectorScorecard
      ),
    [activeBars, sepaSummary, sectorScorecard]
  );

  // Call / Score (60 Technical & Trend Structure + 15 Actionable Setup & Timing + 25 Fundamental Growth & Quality)
  const callScore = useMemo(
    () =>
      computeSingleStockCallScore({
        ticker,
        universe: INDIAN_STOCKS,
        bars: activeBars,
        resolveSector: (sec, ind) => resolveStockSectorContext(INDIAN_STOCKS, sec, ind, marketVersion),
        sepaFallback: sepaSummary
          ? {
              minerviniScore: sepaSummary.minerviniScore,
              passedCount: sepaSummary.passedCount,
              stage: sepaSummary.stage,
              rsRating: sepaSummary.rsRating,
            }
          : null,
        matrixFallback: signalMatrix,
        sectorFallback: sectorScorecard,
        fundamentalsFallback: liveFund
          ? {
              qtrEpsYoY: liveFund.growth.eps.yoyPct ?? liveFund.growth.netProfit.yoyPct,
              qtrRevYoY: liveFund.growth.sales.yoyPct,
              roePct: liveFund.ratios.roePct,
            }
          : null,
      }),
    [ticker, activeBars, marketVersion, sepaSummary, signalMatrix, sectorScorecard, liveFund]
  );

  // Shareholding Strength Check (last 4 quarters: Promoter & Pledge, DII, FII, Public/Retail + Dilution Check)
  const shareholdingCheck = useMemo(
    () =>
      computeShareholdingStrengthCheck({
        ticker,
        stockName: companyName,
        coreStock,
        liveMeta: liveFund?.shareholdingMeta ?? null,
      }),
    [ticker, companyName, coreStock, liveFund]
  );

  // Consolidated Fundamental Ratios (prefer live Yahoo Finance; fall back to core universe where available)
  const ratios = useMemo(() => {
    const coreMktCap = coreStock?.marketCapCr ?? null;
    const coreEps = coreStock?.dividend.epsInr ?? null;
    const corePe =
      coreEps && coreEps > 0 && latestClose > 0 ? Number((latestClose / coreEps).toFixed(2)) : null;
    const coreRoe = coreStock?.fundamentals.roePct ?? null;
    const coreDivYield = coreStock?.dividend.dividendYieldPct ?? null;
    const coreOpMargin = coreStock?.fundamentals.opMarginPct ?? null;

    return {
      marketCapCr: liveFund?.ratios.marketCapCr ?? coreMktCap,
      pe: liveFund?.ratios.pe ?? corePe,
      evToEbitda: liveFund?.ratios.evToEbitda ?? null,
      pb: liveFund?.ratios.pb ?? null,
      roePct: liveFund?.ratios.roePct ?? coreRoe,
      dividendYieldPct: liveFund?.ratios.dividendYieldPct ?? coreDivYield,
      opMarginPct: liveFund?.ratios.opMarginPct ?? coreOpMargin,
      netMarginPct: liveFund?.ratios.netMarginPct ?? null,
      debtToEquity: liveFund?.ratios.debtToEquity ?? null,
    };
  }, [liveFund, coreStock, latestClose]);

  // Consolidated YoY & QoQ Growth Rows for Sales, EBITDA, Net Profit, EPS
  const growthRows = useMemo(() => {
    const coreHist = coreStock?.fundamentals.quarterlyHistory || [];
    const lastCoreQ = coreHist[coreHist.length - 1];
    const prevCoreQ = coreHist.length >= 2 ? coreHist[coreHist.length - 2] : null;
    const pct = (a?: number, b?: number) =>
      a !== undefined && b !== undefined && Math.abs(b) > 0.001
        ? Number((((a - b) / Math.abs(b)) * 100).toFixed(2))
        : null;

    const coreSalesQoq = pct(lastCoreQ?.revenueCr, prevCoreQ?.revenueCr);
    const coreEpsQoq = pct(lastCoreQ?.epsInr, prevCoreQ?.epsInr);
    const coreEbitdaLast =
      lastCoreQ ? Number(((lastCoreQ.revenueCr * lastCoreQ.opmPct) / 100).toFixed(1)) : null;
    const coreEbitdaPrev =
      prevCoreQ ? Number(((prevCoreQ.revenueCr * prevCoreQ.opmPct) / 100).toFixed(1)) : null;
    const coreEbitdaQoq = pct(coreEbitdaLast ?? undefined, coreEbitdaPrev ?? undefined);

    return [
      {
        label: 'Sales (Revenue)',
        unit: 'Cr',
        latestQVal: liveFund?.growth.sales.latestQuarterVal ?? lastCoreQ?.revenueCr ?? null,
        qoqPct: liveFund?.growth.sales.qoqPct ?? coreSalesQoq,
        yoyPct: liveFund?.growth.sales.yoyPct ?? coreStock?.fundamentals.qtrRevYoY ?? null,
        yoyBasis: liveFund?.growth.sales.yoyBasis || 'Quarterly YoY',
        annualVal: liveFund?.growth.sales.latestAnnualVal ?? null,
        annualYoYPct: liveFund?.growth.sales.annualYoYPct ?? null,
      },
      {
        label: 'EBITDA',
        unit: 'Cr',
        latestQVal: liveFund?.growth.ebitda.latestQuarterVal ?? coreEbitdaLast,
        qoqPct: liveFund?.growth.ebitda.qoqPct ?? coreEbitdaQoq,
        yoyPct:
          liveFund?.growth.ebitda.yoyPct ??
          (coreStock
            ? Number(
                (
                  coreStock.fundamentals.qtrRevYoY +
                  coreStock.fundamentals.opMarginExpansionBps / 100
                ).toFixed(1)
              )
            : null),
        yoyBasis: liveFund?.growth.ebitda.yoyBasis || 'Quarterly YoY',
        annualVal: liveFund?.growth.ebitda.latestAnnualVal ?? null,
        annualYoYPct: liveFund?.growth.ebitda.annualYoYPct ?? null,
      },
      {
        label: 'Net Profit (PAT)',
        unit: 'Cr',
        latestQVal: liveFund?.growth.netProfit.latestQuarterVal ?? null,
        qoqPct: liveFund?.growth.netProfit.qoqPct ?? coreEpsQoq,
        yoyPct: liveFund?.growth.netProfit.yoyPct ?? coreStock?.fundamentals.qtrEpsYoY ?? null,
        yoyBasis: liveFund?.growth.netProfit.yoyBasis || 'Quarterly YoY',
        annualVal: liveFund?.growth.netProfit.latestAnnualVal ?? null,
        annualYoYPct: liveFund?.growth.netProfit.annualYoYPct ?? null,
      },
      {
        label: 'EPS (Diluted)',
        unit: 'INR',
        latestQVal: liveFund?.growth.eps.latestQuarterVal ?? lastCoreQ?.epsInr ?? null,
        qoqPct: liveFund?.growth.eps.qoqPct ?? coreEpsQoq,
        yoyPct: liveFund?.growth.eps.yoyPct ?? coreStock?.fundamentals.qtrEpsYoY ?? null,
        yoyBasis: liveFund?.growth.eps.yoyBasis || 'Quarterly YoY',
        annualVal: liveFund?.growth.eps.latestAnnualVal ?? coreStock?.dividend.epsInr ?? null,
        annualYoYPct:
          liveFund?.growth.eps.annualYoYPct ?? coreStock?.fundamentals.annualEps3YCagr ?? null,
      },
    ];
  }, [liveFund, coreStock]);

  // SEPA Fundamental Verification Checklist
  const sepaFundamentalChecks = useMemo(() => {
    const salesYoY = growthRows[0].yoyPct;
    const ebitdaYoY = growthRows[1].yoyPct;
    const netProfitYoY = growthRows[2].yoyPct;
    const epsYoY = growthRows[3].yoyPct;
    const roe = ratios.roePct;

    return [
      {
        label: 'Quarterly EPS YoY Growth ≥ 20%',
        detail: epsYoY !== null ? `${epsYoY >= 0 ? '+' : ''}${epsYoY.toFixed(1)}% YoY` : 'Pending',
        passed: epsYoY !== null && epsYoY >= 20,
      },
      {
        label: 'Quarterly Sales YoY Growth ≥ 15%',
        detail: salesYoY !== null ? `${salesYoY >= 0 ? '+' : ''}${salesYoY.toFixed(1)}% YoY` : 'Pending',
        passed: salesYoY !== null && salesYoY >= 15,
      },
      {
        label: 'EBITDA & Profit Operating Leverage',
        detail:
          ebitdaYoY !== null && netProfitYoY !== null
            ? `EBITDA ${ebitdaYoY >= 0 ? '+' : ''}${ebitdaYoY.toFixed(1)}% · PAT ${netProfitYoY >= 0 ? '+' : ''}${netProfitYoY.toFixed(1)}%`
            : 'Pending',
        passed: (ebitdaYoY !== null && ebitdaYoY >= 15) || (netProfitYoY !== null && netProfitYoY >= 20),
      },
      {
        label: 'Return on Equity (ROE) ≥ 15%',
        detail: roe !== null ? `ROE ${roe.toFixed(1)}%` : 'Pending',
        passed: roe !== null && roe >= 15,
      },
    ];
  }, [growthRows, ratios]);

  const watched = watchlist.includes(ticker);

  // Position Sizer math
  const triggerPrice = setupDiag?.entryTriggerInr || latestClose || 100;
  const stopPrice = setupDiag?.stopLossInr || triggerPrice * 0.94;
  const riskPerShare = Math.max(0.05, triggerPrice - stopPrice);
  const shareQty = Math.max(
    0,
    Math.min(
      Math.floor(((capitalInr * riskPct) / 100) / riskPerShare),
      Math.floor(capitalInr / Math.max(1, triggerPrice))
    )
  );

  const handleLogToJournal = () => {
    if (!setupDiag || shareQty <= 0) return;
    try {
      const key = 'artha_trade_journal_v1';
      const existing: TradeJournalEntry[] = JSON.parse(localStorage.getItem(key) || '[]');
      const entry: TradeJournalEntry = {
        id: `tr_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
        ticker,
        setup: setupDiag.primarySetup,
        entryDate: new Date().toISOString().slice(0, 10),
        entryPrice: setupDiag.entryTriggerInr,
        stopLoss: setupDiag.stopLossInr,
        shares: shareQty,
        status: 'OPEN',
        notes: `${setupDiag.primarySetup} · Consensus ${signalMatrix.consensus}`,
      };
      localStorage.setItem(key, JSON.stringify([entry, ...(Array.isArray(existing) ? existing : [])]));
      setJournalSaved(true);
      setTimeout(() => setJournalSaved(false), 2600);
    } catch {
      // ignore storage quota errors
    }
  };

  const handleCreateAlert = () => {
    void addAlert({
      ticker,
      category: 'price',
      title: `${ticker} Watch Alert at ${formatINR(latestClose)}`,
      message: `Monitoring ${ticker} · Technical ${signalMatrix.consensus} · SEPA ${sepaSummary?.passedCount ?? 0}/8.`,
    });
    setAlertSaved(true);
    setTimeout(() => setAlertSaved(false), 2500);
  };

  const consensusColor =
    signalMatrix.consensus === 'Strong Buy' || signalMatrix.consensus === 'Buy'
      ? 'text-emerald-600 dark:text-emerald-400'
      : signalMatrix.consensus === 'Strong Sell' || signalMatrix.consensus === 'Sell'
      ? 'text-red-600 dark:text-red-400'
      : 'text-amber-600 dark:text-amber-400';

  return (
    <div className="space-y-6">
      {/* Top Full-Page Ticker Header Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div className="space-y-1.5">
          <button
            onClick={onBack}
            className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to {backLabel}
          </button>

          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 className="text-2xl font-extrabold font-mono tracking-tight text-slate-900 dark:text-white">
              {ticker}
            </h1>
            <span className="text-base font-semibold text-slate-700 dark:text-slate-300">
              {companyName}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
            <span>NSE{coreStock ? ` · BSE ${coreStock.bseCode}` : ''}</span>
            <span aria-hidden="true">·</span>
            <span>{sectorName}</span>
            {industryName && (
              <>
                <span aria-hidden="true">·</span>
                <span>{industryName}</span>
              </>
            )}
            {coreStock && (
              <>
                <span aria-hidden="true">·</span>
                <span>{coreStock.capBucket} Cap</span>
              </>
            )}
            {avgTurnoverCr > 0 && (
              <>
                <span aria-hidden="true">·</span>
                <span className="font-mono tabular-nums">50D Avg Turnover {formatCr(avgTurnoverCr)}</span>
              </>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          {latestClose > 0 && (
            <div className="text-left lg:text-right font-mono tabular-nums">
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-100">
                {formatINR(latestClose)}
              </div>
              <div
                className={`text-xs font-semibold ${
                  dailyChangePct >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {formatPct(dailyChangePct)} 1D
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <IndianTickerSearchInput
              currentTicker={ticker}
              onSelectTicker={(next) => onSelectTicker(next)}
              placeholder="Switch any NSE / BSE stock..."
              className="w-60"
            />

            <button
              onClick={() => toggleWatchlist(ticker)}
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg border transition-colors whitespace-nowrap ${
                watched
                  ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                  : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'
              }`}
            >
              <Star className="w-3.5 h-3.5" fill={watched ? 'currentColor' : 'none'} />
              {watched ? 'Watched' : 'Watchlist'}
            </button>

            <button
              onClick={handleCreateAlert}
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
            >
              {alertSaved ? <Check className="w-3.5 h-3.5" /> : <Bell className="w-3.5 h-3.5" />}
              {alertSaved ? 'Alert Created' : 'Create Alert'}
            </button>
          </div>
        </div>
      </div>

      {/* Loading / Error Handling for On-Demand Tickers */}
      {loadingQuote ? (
        <div className="py-20 text-center text-sm text-slate-500 flex flex-col items-center gap-3 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          <span>Loading live 3-year NSE/BSE candlesticks, breakout levels &amp; fundamentals for {ticker}…</span>
        </div>
      ) : quoteError && activeBars.length === 0 ? (
        <div className="p-8 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl text-sm text-slate-500 space-y-2">
          <div className="font-bold text-slate-900 dark:text-slate-100">
            Live NSE/BSE market data unavailable for {ticker}
          </div>
          <div>{quoteError}</div>
        </div>
      ) : (
        <>
          {/* PRE-CHART SUMMARY: MULTI-INDICATOR SIGNAL MATRIX SCORE SNAPSHOT */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                {callScore && (
                  <>
                    <div
                      className="flex flex-wrap items-baseline gap-2"
                      title={`Call / Score (${callScore.compositeScore}/100): Technical & Trend Structure ${callScore.techScore}/60 (SEPA, Stage 2, RS & Indicators Matrix Summary ${callScore.matrixScore}/20) · Actionable Setup & Timing ${callScore.setupScore}/15 · Fundamental Growth & Quality ${callScore.fundaScore}/25`}
                    >
                      <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                        Call / Score
                      </span>
                      <span
                        className={`font-bold text-sm ${
                          callScore.rating === 'Strong Buy'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : callScore.rating === 'Buy'
                            ? 'text-blue-600 dark:text-blue-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {callScore.rating}
                      </span>
                      <span className="font-mono font-bold text-sm tabular-nums text-slate-900 dark:text-slate-100">
                        {callScore.compositeScore}/100
                      </span>
                    </div>
                    <span className="text-slate-300 dark:text-slate-700">|</span>
                  </>
                )}
                <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span>Indicators Matrix Summary</span>
                </div>
                <span className={`font-mono font-bold text-sm tabular-nums ${consensusColor}`}>
                  {signalMatrix.consensus} · {signalMatrix.scorePct}/100
                </span>
                <span className="font-mono text-xs tabular-nums text-slate-500">
                  <span className="text-emerald-600 dark:text-emerald-400 font-semibold">
                    {signalMatrix.bullishCount} Bull
                  </span>
                  {' · '}
                  <span>{signalMatrix.neutralCount} Neut</span>
                  {' · '}
                  <span className="text-red-600 dark:text-red-400 font-semibold">
                    {signalMatrix.bearishCount} Bear
                  </span>
                  {' / '}
                  {signalMatrix.signals.length}
                </span>
              </div>

              <button
                onClick={() =>
                  document
                    .getElementById('multi-indicator-matrix')
                    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }
                className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
              >
                Full {signalMatrix.signals.length}-Signal Breakdown
                <ArrowDown className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 divide-y xl:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800 text-xs">
              {/* NSE Sector Technical Scorecard & Sector / Sub-Sector Quadrant */}
              <div className="px-4 py-3">
                <div className="text-[11px] text-slate-500">NSE Sector Scorecard</div>
                {sectorScorecard ? (
                  <>
                    <div className="mt-0.5 flex flex-wrap items-baseline gap-1.5">
                      <span
                        className={`font-mono font-bold tabular-nums ${
                          sectorScorecard.sectorScore >= 65
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : sectorScorecard.sectorScore < 45
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {sectorScorecard.sectorScore}/100
                      </span>
                      <span className="font-mono text-[10px] text-slate-500 tabular-nums">
                        #{sectorScorecard.sectorRank}/{sectorScorecard.sectorTotal}
                      </span>
                      <span
                        className={`font-semibold text-[11px] ${
                          sectorScorecard.sectorQuadrant === 'Leading'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : sectorScorecard.sectorQuadrant === 'Improving'
                            ? 'text-blue-600 dark:text-blue-400'
                            : sectorScorecard.sectorQuadrant === 'Weakening'
                            ? 'text-amber-600 dark:text-amber-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        · {sectorScorecard.sectorQuadrant}
                      </span>
                    </div>
                    <div
                      className="text-[11px] text-slate-500 mt-0.5 truncate"
                      title={
                        sectorScorecard.subsectorName && sectorScorecard.subsectorQuadrant
                          ? `${sectorScorecard.sectorName} (${sectorScorecard.sectorQuadrant}) | Sub-Sector: ${sectorScorecard.subsectorName} ${sectorScorecard.subsectorScore}/100 (${sectorScorecard.subsectorQuadrant})`
                          : `${sectorScorecard.sectorName} · RS-R ${sectorScorecard.sectorRsRatio.toFixed(1)} · RS-M ${sectorScorecard.sectorRsMomentum.toFixed(1)}`
                      }
                    >
                      {sectorScorecard.subsectorName && sectorScorecard.subsectorQuadrant ? (
                        <>
                          Sub:{' '}
                          <span className="font-medium text-slate-700 dark:text-slate-300">
                            {sectorScorecard.subsectorName}
                          </span>{' '}
                          <span
                            className={`font-semibold ${
                              sectorScorecard.subsectorQuadrant === 'Leading'
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : sectorScorecard.subsectorQuadrant === 'Improving'
                                ? 'text-blue-600 dark:text-blue-400'
                                : sectorScorecard.subsectorQuadrant === 'Weakening'
                                ? 'text-amber-600 dark:text-amber-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            ({sectorScorecard.subsectorQuadrant}
                            {sectorScorecard.subsectorScore !== null ? ` ${sectorScorecard.subsectorScore}` : ''})
                          </span>
                        </>
                      ) : (
                        <span className="font-mono tabular-nums">
                          {sectorScorecard.sectorName} · RS {sectorScorecard.sectorRsRatio.toFixed(1)}
                        </span>
                      )}
                    </div>
                  </>
                ) : (
                  <>
                    <div className="font-semibold text-slate-500 mt-0.5">—</div>
                    <div className="text-[11px] text-slate-500 mt-0.5 truncate">{sectorName}</div>
                  </>
                )}
              </div>

              {/* Donchian Channel (20) */}
              <div className="px-4 py-3">
                <div className="text-[11px] text-slate-500">Donchian Channel (20)</div>
                <div
                  className={`font-semibold mt-0.5 ${
                    signalMatrix.donchianSummary?.signal === 'Bullish'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : signalMatrix.donchianSummary?.signal === 'Bearish'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {signalMatrix.donchianSummary?.regime || 'Mid-Channel'}
                </div>
                <div className="font-mono text-[11px] text-slate-500 tabular-nums mt-0.5 truncate">
                  {signalMatrix.donchianSummary?.latestAlert
                    ? `Last: ${signalMatrix.donchianSummary.latestAlert.type} @ ${formatINR(
                        signalMatrix.donchianSummary.latestAlert.triggerPrice
                      )} (${
                        signalMatrix.donchianSummary.latestAlert.barsAgo === 0
                          ? 'Latest'
                          : `${signalMatrix.donchianSummary.latestAlert.barsAgo}D ago`
                      })`
                    : `Channel Pos ${signalMatrix.donchianSummary?.positionPct.toFixed(0) ?? 50}%`}
                </div>
              </div>

              {/* Supertrend (10, 3) */}
              <div className="px-5 py-3">
                <div className="text-[11px] text-slate-500">Supertrend (10, 3)</div>
                <div
                  className={`font-semibold mt-0.5 ${
                    signalMatrix.supertrendSummary?.direction === 1
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {signalMatrix.supertrendSummary?.direction === 1 ? 'Bullish Trend' : 'Bearish Trend'}
                </div>
                <div className="font-mono text-[11px] text-slate-500 tabular-nums mt-0.5 truncate">
                  {signalMatrix.supertrendSummary?.line
                    ? `Band ${formatINR(signalMatrix.supertrendSummary.line)} (${
                        signalMatrix.supertrendSummary.distancePct >= 0 ? '+' : ''
                      }${signalMatrix.supertrendSummary.distancePct.toFixed(1)}%)`
                    : 'Computing…'}
                </div>
              </div>

              {/* Mark Minervini SEPA Checklist */}
              <div className="px-5 py-3">
                <div className="text-[11px] text-slate-500">Minervini SEPA Checklist</div>
                <div
                  className={`font-mono font-bold tabular-nums mt-0.5 ${
                    (sepaSummary?.minerviniScore ?? 0) >= 65
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : (sepaSummary?.minerviniScore ?? 0) < 42
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {sepaSummary ? `${sepaSummary.minerviniScore}/100 · ${sepaSummary.passedCount}/8` : '—'}
                </div>
                <div className="font-mono text-[11px] text-slate-500 tabular-nums mt-0.5 truncate">
                  {sepaSummary ? `Stage ${sepaSummary.stage} · RS ${sepaSummary.rsRating}/99` : 'Need 60D history'}
                </div>
              </div>

              {/* RSI (14) 55-80 Bullish Zone */}
              <div className="px-5 py-3">
                <div className="text-[11px] text-slate-500">RSI (14) Momentum</div>
                <div
                  className={`font-mono font-bold tabular-nums mt-0.5 ${
                    signalMatrix.rsi14 !== null &&
                    signalMatrix.rsi14 !== undefined &&
                    signalMatrix.rsi14 >= 55 &&
                    signalMatrix.rsi14 <= 80
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : signalMatrix.rsi14 !== null &&
                        signalMatrix.rsi14 !== undefined &&
                        signalMatrix.rsi14 < 45
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {signalMatrix.rsi14 !== null && signalMatrix.rsi14 !== undefined
                    ? signalMatrix.rsi14.toFixed(1)
                    : '—'}{' '}
                  <span className="font-sans font-semibold text-[11px]">
                    {signalMatrix.rsi14 !== null &&
                    signalMatrix.rsi14 !== undefined &&
                    signalMatrix.rsi14 >= 55 &&
                    signalMatrix.rsi14 <= 80
                      ? 'Bullish (55–80)'
                      : signalMatrix.rsi14 !== null &&
                        signalMatrix.rsi14 !== undefined &&
                        signalMatrix.rsi14 < 45
                      ? 'Weak (<45)'
                      : 'Neutral'}
                  </span>
                </div>
                <div className="text-[11px] text-slate-500 mt-0.5">Rule: 55–80 Bullish · &lt;45 Weak</div>
              </div>

              {/* Smart Money (Prom + DII + FII) Verdict + 4Q Δ % */}
              <button
                type="button"
                onClick={() =>
                  document
                    .getElementById('shareholding-strength-check')
                    ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }
                className="px-4 py-3 text-left hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors"
                title="Jump to 4-Quarter Shareholding Strength Check"
              >
                <div className="text-[11px] text-slate-500">Smart Money (Prom+DII+FII)</div>
                <div
                  className={`font-semibold mt-0.5 truncate ${
                    shareholdingCheck.verdict === 'Smart Money Accumulating' ||
                    shareholdingCheck.verdict === 'Selective Institutional Accumulation'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : shareholdingCheck.verdict === 'Smart Money Distributing'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {shareholdingCheck.verdict}
                </div>
                <div className="font-mono text-[11px] tabular-nums mt-0.5 flex items-center gap-1.5 text-slate-500">
                  <span className="text-slate-700 dark:text-slate-300 font-semibold">
                    {shareholdingCheck.quarters[shareholdingCheck.quarters.length - 1]?.smartMoneyPct.toFixed(1)}%
                  </span>
                  <span>·</span>
                  <span>
                    4Q Δ{' '}
                    <strong
                      className={
                        shareholdingCheck.smartMoneyDelta4Q > 0.05
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : shareholdingCheck.smartMoneyDelta4Q < -0.05
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-slate-600 dark:text-slate-300'
                      }
                    >
                      {shareholdingCheck.smartMoneyDelta4Q >= 0 ? '+' : ''}
                      {shareholdingCheck.smartMoneyDelta4Q.toFixed(2)}%
                    </strong>
                  </span>
                </div>
              </button>
            </div>
          </section>

          {/* SECTION 1: FULL-WIDTH INSTITUTIONAL VOLUME CANDLESTICK CHART */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
            <StockChartPanel
              stock={coreStock || undefined}
              barsOverride={coreStock ? undefined : liveQuote?.bars}
              symbolLabel={ticker}
              pivotPrice={sepaSummary?.pivotPrice}
              prior52WHigh={prior52WHigh}
              stopLossPrice={sepaSummary?.stopLossInr}
              height={430}
              defaultStyle="volume_candles"
              defaultRange="6M"
              defaultSubPanes={['rs', 'rsi', 'macd', 'adx']}
              defaultShowDonchian={false}
              defaultShowSupertrend={false}
              levelVisibility={levelVisibility}
              onToggleLevelCategory={handleToggleLevelCategory}
              onResetTemplateLevels={() => setLevelVisibility(DEFAULT_LEVEL_VISIBILITY)}
              hidePreChartSummary
            />
          </div>

          {/* ON-DEMAND AI TECHNOFUNDA BRIEF (Free-Tier Gemini) */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Sparkles className="w-4 h-4 text-blue-500" />
                <span>AI TechnoFunda Brief</span>
                {aiBriefMeta && (
                  <span className="text-[11px] font-normal text-slate-500 font-mono">
                    · {aiBriefMeta}
                  </span>
                )}
              </div>
              <button
                type="button"
                disabled={aiBriefLoading || activeBars.length < 20}
                onClick={async () => {
                  setAiBriefLoading(true);
                  setAiBriefError(null);
                  try {
                    const stSig = signalMatrix.signals.find((s) => s.name.includes('Supertrend'));
                    const dcSig = signalMatrix.signals.find((s) => s.name.includes('Donchian'));
                    const rsiSig = signalMatrix.signals.find((s) => s.name.includes('RSI'));
                    const adxSig = signalMatrix.signals.find((s) => s.name.includes('ADX'));
                    const latestSh =
                      shareholdingCheck.quarters[shareholdingCheck.quarters.length - 1] ?? null;
                    const snapshot = {
                      ticker,
                      name: companyName,
                      sector: sectorName,
                      cmpInr: latestClose,
                      dailyChangePct,
                      sepa: sepaSummary
                        ? {
                            stage: sepaSummary.stage,
                            stageLabel: sepaSummary.stageLabel,
                            rsRating: sepaSummary.rsRating,
                            passedCount: sepaSummary.passedCount,
                            minerviniScore: sepaSummary.minerviniScore,
                            pivotPrice: sepaSummary.pivotPrice,
                            stopLossInr: sepaSummary.stopLossInr,
                            vcpDetail: sepaSummary.vcpDetail,
                          }
                        : null,
                      technicalMatrix: {
                        consensus: signalMatrix.consensus,
                        bullishCount: signalMatrix.bullishCount,
                        bearishCount: signalMatrix.bearishCount,
                        scorePct: signalMatrix.scorePct,
                        supertrend: stSig ? `${stSig.signal} (${stSig.reading})` : 'N/A',
                        donchian: dcSig ? `${dcSig.signal} (${dcSig.reading})` : 'N/A',
                        rsi14: rsiSig ? `${rsiSig.signal} (${rsiSig.reading})` : 'N/A',
                        adx14: adxSig ? `${adxSig.signal} (${adxSig.reading})` : 'N/A',
                        nseSectorScorecard: sectorScorecard
                          ? `${sectorScorecard.sectorName} ${sectorScorecard.sectorScore}/100 (#${sectorScorecard.sectorRank}/${sectorScorecard.sectorTotal}, ${sectorScorecard.sectorQuadrant})${
                              sectorScorecard.subsectorName && sectorScorecard.subsectorQuadrant
                                ? ` · Sub: ${sectorScorecard.subsectorName} (${sectorScorecard.subsectorQuadrant})`
                                : ''
                            }`
                          : 'N/A',
                      },
                      setupDiagnosis: setupDiag
                        ? {
                            primarySetup: setupDiag.primarySetup,
                            entryTriggerInr: setupDiag.entryTriggerInr,
                            stopLossInr: setupDiag.stopLossInr,
                          }
                        : null,
                      fundamentals: {
                        pe: ratios.pe,
                        roePct: ratios.roePct,
                        marketCapCr: ratios.marketCapCr,
                        salesYoYPct: growthRows[0]?.yoyPct ?? null,
                        patYoYPct: growthRows[2]?.yoyPct ?? null,
                        epsYoYPct: growthRows[3]?.yoyPct ?? null,
                      },
                      smartMoney: {
                        verdict: shareholdingCheck.verdict,
                        smartMoneyPct: latestSh
                          ? Number(
                              (latestSh.promoterPct + latestSh.diiPct + latestSh.fiiPct).toFixed(2)
                            )
                          : null,
                        smartMoney4QDeltaPct: shareholdingCheck.smartMoneyDelta4Q,
                        promoterPct: latestSh?.promoterPct ?? null,
                        pledgePct: shareholdingCheck.promoterPledgePct,
                      },
                    };
                    const data = await postAiJson<{ summary?: string; generatedAtIst?: string }>(
                      '/api/ai/stock-brief',
                      { ticker, snapshot }
                    );
                    setAiBrief(String(data.summary || ''));
                    setAiBriefMeta(data.generatedAtIst ? `Generated ${data.generatedAtIst}` : null);
                  } catch (err) {
                    setAiBriefError(
                      err instanceof Error ? err.message : 'Unable to generate AI brief right now.'
                    );
                  } finally {
                    setAiBriefLoading(false);
                  }
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white transition-colors"
              >
                {aiBriefLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Analyzing {ticker}…</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{aiBrief ? 'Regenerate AI Brief' : 'Generate AI Brief'}</span>
                  </>
                )}
              </button>
            </div>

            {aiBriefError && (
              <div className="px-5 py-3 text-xs text-red-600 dark:text-red-400 bg-red-50/70 dark:bg-red-950/30 border-b border-red-200 dark:border-red-900/50">
                {aiBriefError}
              </div>
            )}

            {aiBrief ? (
              <div className="px-5 py-4 text-xs leading-relaxed text-slate-700 dark:text-slate-200 space-y-1.5">
                {renderStructuredAiLines(aiBrief)}
              </div>
            ) : (
              <div className="px-5 py-3.5 text-xs text-slate-500 dark:text-slate-400">
                Click <strong className="text-slate-700 dark:text-slate-200">Generate AI Brief</strong> for an on-demand synthesis of {ticker}&apos;s Stage/SEPA setup, Donchian &amp; Supertrend posture, RSI/ADX momentum, earnings trajectory, and Smart Money shareholding trend.
              </div>
            )}
          </section>

          {/* SECTION 2: FUNDAMENTAL PROFILE — MARKET CAP, P/E, EV/EBITDA, P/B, ROE, DIV YIELD + YoY & QoQ GROWTH */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Layers className="w-4 h-4 text-blue-500" />
                <span>Fundamental Financial Profile &amp; Growth Matrix</span>
              </div>
              <div className="text-xs text-slate-500 flex items-center gap-2">
                {loadingFund ? (
                  <span className="inline-flex items-center gap-1 text-blue-500">
                    <RefreshCw className="w-3 h-3 animate-spin" /> Syncing live reported financials…
                  </span>
                ) : liveFund ? (
                  <span>Live Reported Ratios &amp; Financials ({liveFund.yahooSymbol})</span>
                ) : (
                  <span>NSE Fundamental Profile</span>
                )}
              </div>
            </div>

            {/* 6 Core Fundamental Multiples Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 divide-y sm:divide-y-0 sm:divide-x divide-slate-200 dark:divide-slate-800 border-b border-slate-200 dark:border-slate-800">
              {[
                {
                  label: 'Market Cap',
                  value: ratios.marketCapCr ? formatCr(ratios.marketCapCr) : '—',
                  sub: coreStock ? `${coreStock.capBucket} Cap` : 'NSE Market Cap',
                },
                {
                  label: 'P/E Ratio (TTM)',
                  value: fmtRatio(ratios.pe, '×'),
                  sub: 'Price / Trailing EPS',
                },
                {
                  label: 'EV / EBITDA',
                  value: fmtRatio(ratios.evToEbitda, '×'),
                  sub: 'Enterprise Multiple',
                },
                {
                  label: 'P/B Ratio',
                  value: fmtRatio(ratios.pb, '×'),
                  sub: 'Price / Book Value',
                },
                {
                  label: 'ROE',
                  value: ratios.roePct !== null ? `${ratios.roePct.toFixed(2)}%` : '—',
                  sub:
                    ratios.opMarginPct !== null
                      ? `OPM ${ratios.opMarginPct.toFixed(1)}%`
                      : 'Return on Equity',
                },
                {
                  label: 'Dividend Yield',
                  value:
                    ratios.dividendYieldPct !== null
                      ? `${ratios.dividendYieldPct.toFixed(2)}%`
                      : '—',
                  sub:
                    ratios.netMarginPct !== null
                      ? `Net Margin ${ratios.netMarginPct.toFixed(1)}%`
                      : 'Trailing 12M Yield',
                },
              ].map((item) => (
                <div key={item.label} className="p-4">
                  <div className="text-[11px] text-slate-500">{item.label}</div>
                  <div className="text-lg font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
                    {item.value}
                  </div>
                  <div className="text-[11px] text-slate-500 mt-0.5 truncate">{item.sub}</div>
                </div>
              ))}
            </div>

            {/* YoY & QoQ Growth Table on Sales, EBITDA, Net Profit, EPS */}
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-5">Financial Line Item</th>
                    <th className="py-2.5 px-4 text-right">Latest Quarter</th>
                    <th className="py-2.5 px-4 text-right">QoQ Growth</th>
                    <th className="py-2.5 px-4 text-right">YoY Growth</th>
                    <th className="py-2.5 px-4 text-right">Latest FY Annual</th>
                    <th className="py-2.5 px-5 text-right">Annual FY YoY</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                  {growthRows.map((row) => {
                    const qoq = fmtGrowthCell(row.qoqPct);
                    const yoy = fmtGrowthCell(row.yoyPct);
                    const annYoy = fmtGrowthCell(row.annualYoYPct);
                    const fmtVal = (v: number | null) =>
                      v === null ? '—' : row.unit === 'INR' ? formatINR(v) : formatCr(v);
                    return (
                      <tr
                        key={row.label}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      >
                        <td className="py-3 px-5 font-sans font-semibold text-slate-900 dark:text-slate-100">
                          {row.label}
                        </td>
                        <td className="py-3 px-4 text-right font-semibold text-slate-900 dark:text-slate-100">
                          {fmtVal(row.latestQVal)}
                        </td>
                        <td className={`py-3 px-4 text-right ${qoq.tone}`}>{qoq.text}</td>
                        <td className={`py-3 px-4 text-right ${yoy.tone}`}>
                          {yoy.text}
                          <div className="font-sans text-[10px] font-normal text-slate-400">
                            {row.yoyBasis}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right text-slate-700 dark:text-slate-300">
                          {fmtVal(row.annualVal)}
                        </td>
                        <td className={`py-3 px-5 text-right ${annYoy.tone}`}>{annYoy.text}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Recent Reported Quarters Breakdown (if live quarterly history returned) */}
            {liveFund && liveFund.quarterlyHistory.length > 0 && (
              <div className="border-t border-slate-200 dark:border-slate-800">
                <div className="px-5 py-2.5 bg-slate-50/70 dark:bg-slate-900/60 text-[11px] font-semibold text-slate-600 dark:text-slate-400">
                  Recent Reported Quarterly Statements (₹ Crore / Per Share)
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                    <thead className="border-b border-slate-200 dark:border-slate-800 text-[11px] font-sans text-slate-500">
                      <tr>
                        <th className="py-2 px-5">Quarter Ended</th>
                        <th className="py-2 px-4 text-right">Sales (₹ Cr)</th>
                        <th className="py-2 px-4 text-right">EBITDA (₹ Cr)</th>
                        <th className="py-2 px-4 text-right">EBITDA Margin</th>
                        <th className="py-2 px-4 text-right">Net Profit (₹ Cr)</th>
                        <th className="py-2 px-5 text-right">Diluted EPS (₹)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200/60 dark:divide-slate-800/60">
                      {[...liveFund.quarterlyHistory].reverse().map((q) => (
                        <tr key={q.date} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                          <td className="py-2 px-5 text-slate-700 dark:text-slate-300">{q.date}</td>
                          <td className="py-2 px-4 text-right">
                            {q.salesCr !== null ? q.salesCr.toLocaleString('en-IN') : '—'}
                          </td>
                          <td className="py-2 px-4 text-right">
                            {q.ebitdaCr !== null ? q.ebitdaCr.toLocaleString('en-IN') : '—'}
                          </td>
                          <td className="py-2 px-4 text-right text-slate-600 dark:text-slate-400">
                            {q.ebitdaMarginPct !== null ? `${q.ebitdaMarginPct.toFixed(1)}%` : '—'}
                          </td>
                          <td className="py-2 px-4 text-right">
                            {q.netProfitCr !== null ? q.netProfitCr.toLocaleString('en-IN') : '—'}
                          </td>
                          <td className="py-2 px-5 text-right font-semibold">
                            {q.eps !== null ? formatINR(q.eps) : '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>

          {/* SECTION 3: SUPPORT & RESISTANCE BREAKOUTS + RISK-DEFINED EXECUTION SIZER */}
          <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 space-y-2.5">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                    <TrendingUp className="w-4 h-4 text-emerald-500" />
                    <span>Support &amp; Resistance Breakouts</span>
                  </div>
                  <div className="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 text-[11px] font-mono">
                    {(['1D', '1W'] as const).map((tf) => (
                      <button
                        key={tf}
                        onClick={() => setSrTimeframe(tf)}
                        className={`px-2 py-0.5 rounded font-semibold ${
                          srTimeframe === tf
                            ? 'bg-white dark:bg-slate-800 text-blue-600 dark:text-blue-400'
                            : 'text-slate-500'
                        }`}
                      >
                        {tf} Levels
                      </button>
                    ))}
                  </div>
                </div>

                {/* Synchronized Filter Toggles (mirrors Price Chart Breakout / Major & Minor S&R Lines) */}
                <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
                  {LEVEL_TOGGLE_CONFIGS.map((cfg) => {
                    const active = levelVisibility[cfg.key];
                    const isMinor = cfg.key.startsWith('minor_');
                    return (
                      <button
                        key={cfg.key}
                        onClick={() => handleToggleLevelCategory(cfg.key)}
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 font-medium rounded-md border transition-colors whitespace-nowrap ${
                          active
                            ? cfg.activeClass
                            : 'border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                        }`}
                        title={`Select/deselect ${cfg.label} on chart and table`}
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
              </div>

              {filteredSrLevels.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  {srLevels.length === 0
                    ? 'Insufficient bar history to cluster structural support and resistance zones.'
                    : 'No levels selected — enable any Breakout, Resistance, or Support toggle above.'}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                      <tr>
                        <th className="py-2.5 px-5">Zone</th>
                        <th className="py-2.5 px-3 text-right">Level (₹)</th>
                        <th className="py-2.5 px-3 text-right">Distance vs LTP</th>
                        <th className="py-2.5 px-3 text-right">Tests</th>
                        <th className="py-2.5 px-3">Last Tested</th>
                        <th className="py-2.5 px-5 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                      {filteredSrLevels.map((lvl) => {
                        const isAbove = lvl.distPct > 0;
                        const statusText =
                          lvl.kind === 'breakout'
                            ? lvl.distPct <= 2.5
                              ? 'At Breakout Pivot'
                              : 'Overhead Breakout'
                            : lvl.kind === 'resistance'
                            ? lvl.distPct <= 2.0
                              ? 'Testing Supply'
                              : lvl.strength === 'Major'
                              ? 'Major Supply Ceiling'
                              : 'Minor Overhead Ceiling'
                            : lvl.kind === 'support_flip'
                            ? 'Breakout Retest Floor'
                            : Math.abs(lvl.distPct) <= 2.5
                            ? 'Testing Demand'
                            : lvl.strength === 'Major'
                            ? 'Major Structural Floor'
                            : 'Minor Swing Floor';

                        const labelColor =
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
                          <tr
                            key={lvl.id}
                            className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                          >
                            <td className={`py-2.5 px-5 font-sans font-semibold ${labelColor}`}>
                              {lvl.label}
                            </td>
                            <td className="py-2.5 px-3 text-right font-bold text-slate-900 dark:text-slate-100">
                              {formatINR(lvl.price)}
                            </td>
                            <td
                              className={`py-2.5 px-3 text-right font-semibold ${
                                isAbove
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              {isAbove ? '+' : ''}
                              {lvl.distPct.toFixed(2)}%
                            </td>
                            <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-400">
                              {lvl.touches}T
                            </td>
                            <td className="py-2.5 px-3 text-slate-500">{lvl.lastTestedDate}</td>
                            <td className="py-2.5 px-5 text-right font-sans text-slate-600 dark:text-slate-300">
                              {statusText}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Right: Setup Diagnosis & Risk-Defined Position Sizer */}
            <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Active Setup &amp; Risk Execution Plan
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {setupDiag
                      ? `${setupDiag.primarySetup} · Conviction ${setupDiag.convictionScore}/100`
                      : 'Analyzing setup structure'}
                  </div>
                </div>
                {setupDiag && (
                  <button
                    onClick={handleLogToJournal}
                    disabled={shareQty <= 0}
                    className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {journalSaved ? 'Logged to Journal' : '+ Log Trade'}
                  </button>
                )}
              </div>

              {setupDiag && (
                <>
                  <div className="text-xs text-slate-600 dark:text-slate-400">
                    Active signals:{' '}
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      {setupDiag.setups.length > 0
                        ? setupDiag.setups.map((s) => SETUP_NAME_MAP[s] || s).join(' · ')
                        : 'Base monitoring'}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs font-mono tabular-nums pt-2 border-t border-slate-200 dark:border-slate-800">
                    <div>
                      <div className="font-sans text-[11px] text-slate-500">Entry Trigger</div>
                      <div className="font-bold text-sm text-slate-900 dark:text-slate-100">
                        {formatINR(setupDiag.entryTriggerInr)}
                      </div>
                    </div>
                    <div>
                      <div className="font-sans text-[11px] text-slate-500">Hard Stop-Loss</div>
                      <div className="font-bold text-sm text-red-600 dark:text-red-400">
                        {formatINR(setupDiag.stopLossInr)} (-{setupDiag.stopDistancePct.toFixed(1)}%)
                      </div>
                    </div>
                    <div>
                      <div className="font-sans text-[11px] text-slate-500">ADR(20) / Ext 50D</div>
                      <div
                        className={`font-bold text-sm ${
                          setupDiag.isExtended
                            ? 'text-amber-600 dark:text-amber-400'
                            : 'text-slate-900 dark:text-slate-100'
                        }`}
                      >
                        {setupDiag.adrPct20.toFixed(1)}% · {setupDiag.distFrom50SmaAtrs >= 0 ? '+' : ''}
                        {setupDiag.distFrom50SmaAtrs.toFixed(1)} ATR
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs font-mono tabular-nums">
                    <div>
                      <div className="font-sans text-[10px] text-slate-500">1R Milestone</div>
                      <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {formatINR(setupDiag.r1Inr)}
                      </div>
                    </div>
                    <div>
                      <div className="font-sans text-[10px] text-slate-500">2R Milestone</div>
                      <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {formatINR(setupDiag.r2Inr)}
                      </div>
                    </div>
                    <div>
                      <div className="font-sans text-[10px] text-slate-500">3R Milestone</div>
                      <div className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {formatINR(setupDiag.r3Inr)}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-200 dark:border-slate-800 text-xs font-mono">
                    <div className="flex items-center gap-2">
                      <label className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                        <span>Capital ₹</span>
                        <input
                          type="number"
                          min={50000}
                          step={50000}
                          value={capitalInr}
                          onChange={(e) => setCapitalInr(Math.max(0, Number(e.target.value)))}
                          className="w-24 px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                        />
                      </label>
                      <label className="inline-flex items-center gap-1 text-[11px] text-slate-500">
                        <span>Risk %</span>
                        <input
                          type="number"
                          min={0.25}
                          max={5}
                          step={0.25}
                          value={riskPct}
                          onChange={(e) => setRiskPct(Math.max(0.1, Number(e.target.value)))}
                          className="w-16 px-2 py-1 rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                        />
                      </label>
                    </div>
                    <div className="tabular-nums text-slate-800 dark:text-slate-200">
                      Qty <span className="font-bold text-blue-600 dark:text-blue-400">{shareQty}</span> ·{' '}
                      {formatINR(shareQty * setupDiag.entryTriggerInr, 0)}
                    </div>
                  </div>
                </>
              )}
            </div>
          </section>

          {/* SECTION 4 & 5: MULTI-INDICATOR SIGNAL MATRIX + MARK MINERVINI SEPA CHECKLIST */}
          <section className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            {/* Multi-Indicator Signal Matrix */}
            <div
              id="multi-indicator-matrix"
              className="xl:col-span-6 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden scroll-mt-20"
            >
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span>
                    Indicators Matrix Summary ({signalMatrix.signals.length} Signals)
                  </span>
                </div>
                <div className="text-xs font-mono tabular-nums flex items-center gap-2">
                  <span className={`font-bold ${consensusColor}`}>{signalMatrix.consensus}</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-emerald-600 dark:text-emerald-400">
                    {signalMatrix.bullishCount} Bull
                  </span>
                  <span className="text-slate-400">·</span>
                  <span className="text-slate-500">{signalMatrix.neutralCount} Neut</span>
                  <span className="text-slate-400">·</span>
                  <span className="text-red-600 dark:text-red-400">
                    {signalMatrix.bearishCount} Bear
                  </span>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Indicator</th>
                      <th className="py-2.5 px-3">Live Reading</th>
                      <th className="py-2.5 px-4 text-right">Signal</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {signalMatrix.signals.map((sig) => (
                      <tr
                        key={sig.id}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      >
                        <td className="py-2.5 px-4">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {sig.name}
                          </div>
                          <div className="text-[11px] text-slate-500">
                            {sig.category} · {sig.rule}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 font-mono tabular-nums text-[11px] text-slate-700 dark:text-slate-300">
                          {sig.reading}
                        </td>
                        <td
                          className={`py-2.5 px-4 text-right font-semibold whitespace-nowrap ${
                            sig.signal === 'Bullish'
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : sig.signal === 'Bearish'
                              ? 'text-red-600 dark:text-red-400'
                              : 'text-amber-600 dark:text-amber-400'
                          }`}
                        >
                          {sig.signal}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mark Minervini SEPA Checklist */}
            <div className="xl:col-span-6 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                  <Compass className="w-4 h-4 text-emerald-500" />
                  <span>Mark Minervini SEPA Checklist</span>
                </div>
                {sepaSummary && (
                  <div className="text-xs font-mono tabular-nums flex items-center gap-2">
                    <span className="font-bold text-blue-600 dark:text-blue-400">
                      Score {sepaSummary.minerviniScore}/100
                    </span>
                    <span className="text-slate-400">·</span>
                    <span className="font-semibold text-slate-700 dark:text-slate-300">
                      Template {sepaSummary.passedCount}/8
                    </span>
                    <span className="text-slate-400">·</span>
                    <span>RS {sepaSummary.rsRating}</span>
                  </div>
                )}
              </div>

              {sepaSummary ? (
                <div className="p-5 space-y-4">
                  {/* Stage & VCP Summary Strip */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs pb-3 border-b border-slate-200 dark:border-slate-800">
                    <div>
                      <div className="text-[11px] text-slate-500">Stage Analysis</div>
                      <div
                        className={`font-bold mt-0.5 ${
                          sepaSummary.stage === 2
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : sepaSummary.stage === 4
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-amber-600 dark:text-amber-400'
                        }`}
                      >
                        {sepaSummary.stageLabel}
                      </div>
                    </div>
                    <div>
                      <div className="text-[11px] text-slate-500">VCP Structure &amp; Pivot</div>
                      <div className="font-mono text-slate-800 dark:text-slate-200 mt-0.5">
                        {sepaSummary.vcpDetail}
                      </div>
                    </div>
                  </div>

                  {/* 8-Point Minervini Trend Template */}
                  <div className="space-y-1.5">
                    <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      8-Point Trend Template Criteria
                    </div>
                    <div className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                      {sepaSummary.conditions.map((cond) => (
                        <div
                          key={cond.id}
                          className="py-2 flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="flex items-start gap-2 min-w-0">
                            {cond.passed ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                            )}
                            <div className="min-w-0">
                              <div className="font-medium text-slate-900 dark:text-slate-100">
                                {cond.id}. {cond.label}
                              </div>
                              <div className="text-[11px] font-mono text-slate-500">
                                {cond.detail}
                              </div>
                            </div>
                          </div>
                          <span
                            className={`text-[11px] font-mono font-semibold shrink-0 ${
                              cond.passed
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {cond.passed ? 'PASS' : 'FAIL'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* SEPA Fundamental Growth Checks */}
                  <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
                    <div className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                      SEPA Fundamental Acceleration Checks
                    </div>
                    <div className="divide-y divide-slate-200/60 dark:divide-slate-800/60">
                      {sepaFundamentalChecks.map((fc) => (
                        <div
                          key={fc.label}
                          className="py-2 flex items-center justify-between gap-3 text-xs"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            {fc.passed ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                            ) : (
                              <XCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            )}
                            <span className="text-slate-800 dark:text-slate-200 truncate">
                              {fc.label}
                            </span>
                          </div>
                          <span className="font-mono text-[11px] text-slate-600 dark:text-slate-400 shrink-0">
                            {fc.detail}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-slate-500">
                  Need at least 60 trading sessions to compute the Minervini SEPA checklist.
                </div>
              )}
            </div>
          </section>

          {/* SECTION 6: SHAREHOLDING STRENGTH CHECK (LAST 4 QUARTERS + SMART MONEY & DILUTION VERDICT) */}
          <section
            id="shareholding-strength-check"
            className="scroll-mt-20 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden"
          >
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-bold text-slate-900 dark:text-slate-100">
                <Users className="w-4 h-4 text-blue-500" />
                <span>Shareholding Strength Check — {companyName} (Last 4 Quarters)</span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono tabular-nums">
                <span
                  className={`font-bold ${
                    shareholdingCheck.verdict === 'Smart Money Accumulating' ||
                    shareholdingCheck.verdict === 'Selective Institutional Accumulation'
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : shareholdingCheck.verdict === 'Smart Money Distributing'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  {shareholdingCheck.verdict}
                </span>
                <span className="text-slate-400">·</span>
                <span className="text-slate-500">
                  4Q Smart Money Δ{' '}
                  <strong
                    className={
                      shareholdingCheck.smartMoneyDelta4Q >= 0
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-red-600 dark:text-red-400'
                    }
                  >
                    {shareholdingCheck.smartMoneyDelta4Q >= 0 ? '+' : ''}
                    {shareholdingCheck.smartMoneyDelta4Q.toFixed(2)}%
                  </strong>
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 xl:grid-cols-12 divide-y xl:divide-y-0 xl:divide-x divide-slate-200 dark:divide-slate-800">
              {/* Left: Last 4 Quarters Ownership Trend Table with QoQ % Δ and YoY Δ */}
              <div className="xl:col-span-7 overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-sans text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Holder Category</th>
                      {shareholdingCheck.quarters.map((q) => (
                        <th key={q.quarter} className="py-2.5 px-2.5 text-right whitespace-nowrap">
                          {q.quarter}
                        </th>
                      ))}
                      <th
                        className="py-2.5 px-2.5 text-right whitespace-nowrap"
                        title="Quarter-over-Quarter change (Latest Quarter vs Prior Quarter)"
                      >
                        QoQ Δ %
                      </th>
                      <th
                        className="py-2.5 px-4 text-right whitespace-nowrap"
                        title="Year-over-Year 4-Quarter change (Latest Quarter vs 4Q Ago)"
                      >
                        YoY Δ %
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {(() => {
                      const qs = shareholdingCheck.quarters;
                      const latestIdx = qs.length - 1;
                      const prevIdx = Math.max(0, qs.length - 2);
                      const firstIdx = 0;
                      const calcDelta = (getter: (q: (typeof qs)[number]) => number) => {
                        const latest = getter(qs[latestIdx]);
                        const prev = getter(qs[prevIdx]);
                        const first = getter(qs[firstIdx]);
                        return {
                          qoqDelta: Number((latest - prev).toFixed(2)),
                          yoyDelta: Number((latest - first).toFixed(2)),
                        };
                      };
                      const rows: {
                        label: string;
                        vals: string[];
                        qoqDelta: number;
                        yoyDelta: number;
                        goodUp: boolean;
                        bold?: boolean;
                      }[] = [
                        {
                          label: 'Promoters',
                          vals: qs.map((q) => `${q.promoterPct.toFixed(2)}%`),
                          ...calcDelta((q) => q.promoterPct),
                          goodUp: true,
                        },
                        {
                          label: 'Promoter Pledge (% of Prom.)',
                          vals: qs.map((q) => `${q.promoterPledgePct.toFixed(1)}%`),
                          ...calcDelta((q) => q.promoterPledgePct),
                          goodUp: false,
                        },
                        {
                          label: 'DII (Domestic Inst. & MFs)',
                          vals: qs.map((q) => `${q.diiPct.toFixed(2)}%`),
                          ...calcDelta((q) => q.diiPct),
                          goodUp: true,
                        },
                        {
                          label: 'FII (Foreign Institutions)',
                          vals: qs.map((q) => `${q.fiiPct.toFixed(2)}%`),
                          ...calcDelta((q) => q.fiiPct),
                          goodUp: true,
                        },
                        {
                          label: 'Public / Retail Float',
                          vals: qs.map((q) => `${q.publicPct.toFixed(2)}%`),
                          ...calcDelta((q) => q.publicPct),
                          goodUp: false,
                        },
                        {
                          label: 'Smart Money (Prom + DII + FII)',
                          vals: qs.map((q) => `${q.smartMoneyPct.toFixed(2)}%`),
                          ...calcDelta((q) => q.smartMoneyPct),
                          goodUp: true,
                          bold: true,
                        },
                      ];
                      const toneClass = (delta: number, goodUp: boolean) => {
                        const pos = goodUp ? delta > 0.05 : delta < -0.05;
                        const neg = goodUp ? delta < -0.05 : delta > 0.05;
                        return pos
                          ? 'text-emerald-600 dark:text-emerald-400'
                          : neg
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-slate-500';
                      };
                      return rows.map((row) => (
                        <tr
                          key={row.label}
                          className={
                            row.bold
                              ? 'bg-slate-50/70 dark:bg-slate-900/60 font-semibold'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                          }
                        >
                          <td className="py-2.5 px-4 font-sans font-medium text-slate-900 dark:text-slate-100 whitespace-nowrap">
                            {row.label}
                          </td>
                          {row.vals.map((v, i) => (
                            <td
                              key={i}
                              className="py-2.5 px-2.5 text-right text-slate-700 dark:text-slate-300 whitespace-nowrap"
                            >
                              {v}
                            </td>
                          ))}
                          <td
                            className={`py-2.5 px-2.5 text-right font-semibold whitespace-nowrap ${toneClass(
                              row.qoqDelta,
                              row.goodUp
                            )}`}
                          >
                            {row.qoqDelta >= 0 ? '+' : ''}
                            {row.qoqDelta.toFixed(2)}%
                          </td>
                          <td
                            className={`py-2.5 px-4 text-right font-semibold whitespace-nowrap ${toneClass(
                              row.yoyDelta,
                              row.goodUp
                            )}`}
                          >
                            {row.yoyDelta >= 0 ? '+' : ''}
                            {row.yoyDelta.toFixed(2)}%
                          </td>
                        </tr>
                      ));
                    })()}
                    {shareholdingCheck.quarters.some((q) => q.sharesCr !== null) &&
                      (() => {
                        const qs = shareholdingCheck.quarters;
                        const latestShares = qs[qs.length - 1]?.sharesCr;
                        const prevShares = qs[Math.max(0, qs.length - 2)]?.sharesCr;
                        const qoqSharesPct =
                          latestShares !== null &&
                          prevShares !== null &&
                          prevShares > 0
                            ? Number((((latestShares - prevShares) / prevShares) * 100).toFixed(2))
                            : null;
                        return (
                          <tr className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                            <td className="py-2.5 px-4 font-sans font-medium text-slate-600 dark:text-slate-400 whitespace-nowrap">
                              Diluted Equity Shares (Cr)
                            </td>
                            {qs.map((q, i) => (
                              <td
                                key={i}
                                className="py-2.5 px-2.5 text-right text-slate-600 dark:text-slate-400 whitespace-nowrap"
                              >
                                {q.sharesCr !== null ? q.sharesCr.toFixed(2) : '—'}
                              </td>
                            ))}
                            <td
                              className={`py-2.5 px-2.5 text-right font-semibold whitespace-nowrap ${
                                qoqSharesPct !== null && qoqSharesPct > 1.0
                                  ? 'text-amber-600 dark:text-amber-400'
                                  : 'text-slate-500'
                              }`}
                            >
                              {qoqSharesPct !== null
                                ? `${qoqSharesPct >= 0 ? '+' : ''}${qoqSharesPct.toFixed(2)}%`
                                : '—'}
                            </td>
                            <td
                              className={`py-2.5 px-4 text-right font-semibold whitespace-nowrap ${
                                shareholdingCheck.dilutionDetected
                                  ? 'text-amber-600 dark:text-amber-400'
                                  : 'text-slate-500'
                              }`}
                            >
                              {shareholdingCheck.dilutionPct4Q !== null
                                ? `${shareholdingCheck.dilutionPct4Q >= 0 ? '+' : ''}${shareholdingCheck.dilutionPct4Q.toFixed(1)}%`
                                : '—'}
                            </td>
                          </tr>
                        );
                      })()}
                  </tbody>
                </table>
              </div>

              {/* Right: 4-Point Institutional Checklist + Dilution Check + Smart Money Verdict */}
              <div className="xl:col-span-5 p-5 space-y-4">
                <div className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {shareholdingCheck.checks.map((chk) => (
                    <div
                      key={chk.id}
                      className="py-2.5 first:pt-0 flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="flex items-start gap-2 min-w-0">
                        {chk.status === 'PASS' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                        ) : chk.status === 'WATCH' ? (
                          <ShieldCheck className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                        )}
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900 dark:text-slate-100">
                            {chk.id}. {chk.label}
                          </div>
                          <div className="text-[11px] text-slate-600 dark:text-slate-400 mt-0.5">
                            {chk.detail}
                          </div>
                        </div>
                      </div>
                      <span
                        className={`font-mono text-[11px] font-semibold shrink-0 tabular-nums ${
                          chk.status === 'PASS'
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : chk.status === 'WATCH'
                            ? 'text-amber-600 dark:text-amber-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {chk.status} · {chk.delta4Q}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Dilution vs Open-Market Buying Note */}
                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-900 dark:text-slate-100">
                      Smart Money Verdict: {shareholdingCheck.verdict}
                    </span>
                    <span className="font-mono text-[11px] text-slate-500">
                      {shareholdingCheck.dilutionDetected
                        ? `Dilution Flag (+${shareholdingCheck.dilutionPct4Q?.toFixed(1)}% shares)`
                        : 'No Material Dilution'}
                    </span>
                  </div>
                  <p className="text-slate-700 dark:text-slate-300 leading-relaxed">
                    {shareholdingCheck.verdictSummary}
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    <strong>Dilution Check:</strong> {shareholdingCheck.dilutionNote}
                  </p>
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
};
