import React, { useMemo, useRef, useState } from 'react';
import * as XLSX from 'xlsx';
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BellPlus,
  Check,
  Download,
  FileDown,
  FileSpreadsheet,
  LineChart,
  ListPlus,
  Plus,
  RefreshCw,
  Scale,
  ShieldAlert,
  Sparkles,
  Star,
  Trash2,
  Upload,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { renderStructuredAiLines } from '../components/AiDeskDrawer';
import { PortfolioTreemap } from '../components/PortfolioTreemap';
import { WatchlistAnalysisSection } from '../components/WatchlistAnalysisSection';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import { DEFAULT_TREND_THRESHOLDS, runMinerviniAnalysis } from '../engine/analyticsEngine';
import {
  PREDEFINED_SCENARIOS,
  computePortfolioSummary,
  computeRebalancePlan,
  generatePortfolioPdfReport,
  simulateScenario,
} from '../engine/portfolioRiskEngine';
import { computeMultiIndicatorMatrix } from '../engine/tradeRadarEngine';
import { postAiJson } from '../utils/aiClient';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

interface PortfolioRiskViewProps {
  onInspectStock: (ticker: string) => void;
}

type PortfolioTab = 'overview' | 'watchlists' | 'rebalance' | 'scenarios';
type ImportTab = 'file' | 'tickers';
type ImportMode = 'overwrite' | 'merge';

interface ParsedImportRow {
  ticker: string;
  shares: number;
  avgCostInr: number;
  stopLossInr?: number;
  knownInUniverse: boolean;
}

interface PortfolioExitDiagnostic {
  ticker: string;
  name: string;
  sector: string;
  priceInr: number;
  marketValueInr: number;
  weightPct: number;
  unrealizedPnlPct: number;
  stopLossInr?: number;
  severity: 'HIGH_EXIT' | 'CAUTION' | 'HEALTHY';
  exitTriggers: string[];
  consensus: string;
  scorePct: number;
  bullishCount: number;
  bearishCount: number;
  totalSignals: number;
  sma200Signal: 'Bullish' | 'Neutral' | 'Bearish';
  sma200Reading: string;
  sma50Signal: 'Bullish' | 'Neutral' | 'Bearish';
  dcSignal: 'Bullish' | 'Neutral' | 'Bearish';
  dcReading: string;
  stSignal: 'Bullish' | 'Neutral' | 'Bearish';
  stReading: string;
  rsi14: number | null;
  stage: number | null;
}

function normalizeTickerToken(raw: string): string {
  return raw
    .trim()
    .toUpperCase()
    .replace(/^(NSE|BSE|NS|BO)[:.\-\s]+/i, '')
    .replace(/\.(NS|BO)$/i, '')
    .replace(/[^A-Z0-9&\-]/g, '');
}

function parseNumericCell(val: unknown): number | undefined {
  if (val === null || val === undefined || val === '') return undefined;
  if (typeof val === 'number') return Number.isFinite(val) ? val : undefined;
  const cleaned = String(val).replace(/[₹,\s]/g, '');
  const n = Number(cleaned);
  return Number.isFinite(n) ? n : undefined;
}

function findColumnKey(keys: string[], patterns: RegExp[]): string | undefined {
  for (const pat of patterns) {
    const hit = keys.find((k) => pat.test(k.trim().toLowerCase()));
    if (hit) return hit;
  }
  return undefined;
}

export const PortfolioRiskView: React.FC<PortfolioRiskViewProps> = ({
  onInspectStock,
}) => {
  const {
    user,
    holdings,
    upsertHolding,
    removeHolding,
    importHoldings,
    addManyToWatchlist,
    customWatchlists,
    addAlert,
    applyRebalanceShares,
    connectors,
    marketVersion,
  } = useAppData();

  const [activeTab, setActiveTab] = useState<PortfolioTab>('overview');
  const [cashFlowInr, setCashFlowInr] = useState<number>(0);
  const [driftTolerancePct, setDriftTolerancePct] = useState<number>(0.5);
  const [brokeragePct, setBrokeragePct] = useState<number>(0);

  // Add holding form state
  const [newTicker, setNewTicker] = useState<string>('BEL');
  const [newShares, setNewShares] = useState<number>(100);
  const [newAvgCost, setNewAvgCost] = useState<number>(310);
  const [newStopLoss, setNewStopLoss] = useState<string>('');
  const [newTargetWeight, setNewTargetWeight] = useState<number>(5);

  // Quick Import & Periodic Update state
  const [showImportPanel, setShowImportPanel] = useState<boolean>(false);
  const [importTab, setImportTab] = useState<ImportTab>('file');
  const [importMode, setImportMode] = useState<ImportMode>('overwrite');
  const [parsedFileRows, setParsedFileRows] = useState<ParsedImportRow[]>([]);
  const [fileName, setFileName] = useState<string>('');
  const [fileError, setFileError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [tickerCsvInput, setTickerCsvInput] = useState<string>(
    'NSE:RELIANCE, NSE:TCS, NSE:INFY, NSE:HDFCBANK, NSE:BEL'
  );
  const [perStockAllocInr, setPerStockAllocInr] = useState<number>(100000);
  const [alertedHoldings, setAlertedHoldings] = useState<Record<string, boolean>>({});
  const [showOnlyAlerts, setShowOnlyAlerts] = useState<boolean>(true);

  // Scenario Analysis state
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('market_drop_10');
  const [useCustomShock, setUseCustomShock] = useState<boolean>(false);
  const [customEquityShock, setCustomEquityShock] = useState<number>(-15);
  const [customInrShock, setCustomInrShock] = useState<number>(8);
  const [customRateBps, setCustomRateBps] = useState<number>(75);

  const [toast, setToast] = useState<string | null>(null);

  const summary = useMemo(() => computePortfolioSummary(holdings), [holdings, marketVersion]);

  // Sector concentration summary (auto-updates immediately on import/edit)
  const sectorConcentration = useMemo(() => {
    const map = new Map<string, { sector: string; valueInr: number; weightPct: number; count: number }>();
    for (const row of summary.enriched) {
      const prev = map.get(row.sector) || {
        sector: row.sector,
        valueInr: 0,
        weightPct: 0,
        count: 0,
      };
      prev.valueInr += row.marketValueInr;
      prev.weightPct += row.currentWeightPct;
      prev.count += 1;
      map.set(row.sector, prev);
    }
    return Array.from(map.values()).sort((a, b) => b.weightPct - a.weightPct);
  }, [summary]);

  // Live Multi-Indicator Exit & Negative Trend Diagnostics across ALL portfolio holdings
  const exitDiagnostics = useMemo<PortfolioExitDiagnostic[]>(() => {
    void marketVersion;
    const heldStocks = summary.enriched
      .map((r) => STOCK_BY_TICKER[r.holding.ticker])
      .filter((s): s is NonNullable<typeof s> => Boolean(s));
    const sepaByTicker = new Map(
      runMinerviniAnalysis(heldStocks, DEFAULT_TREND_THRESHOLDS).map((m) => [m.stock.ticker, m])
    );

    return summary.enriched
      .map((row) => {
        const stock = STOCK_BY_TICKER[row.holding.ticker];
        const sepa = sepaByTicker.get(row.holding.ticker) || null;
        const matrix = stock
          ? computeMultiIndicatorMatrix(
              stock.bars,
              sepa
                ? {
                    minerviniScore: sepa.minerviniScore,
                    passedCount: sepa.passedCount,
                    stage: sepa.stage,
                    rsRating: sepa.rsRating,
                  }
                : null
            )
          : null;

        const sma200Sig = matrix?.signals.find((s) => s.id === 'sma_200');
        const sma50Sig = matrix?.signals.find((s) => s.id === 'sma_50');
        const dcSig = matrix?.signals.find((s) => s.id === 'donchian_20');
        const stSig = matrix?.signals.find((s) => s.id === 'supertrend_10_3');
        const rsiVal = matrix?.rsi14 ?? null;

        const exitTriggers: string[] = [];
        let highAlertPoints = 0;

        if (row.holding.stopLossInr && row.priceInr <= row.holding.stopLossInr) {
          exitTriggers.push(`Stop-Loss Breached (≤ ${formatINR(row.holding.stopLossInr)})`);
          highAlertPoints += 3;
        }
        if (sma200Sig?.signal === 'Bearish') {
          exitTriggers.push('Below 200-Day SMA');
          highAlertPoints += 2;
        }
        if (stSig?.signal === 'Bearish') {
          exitTriggers.push('Supertrend (10,3) SELL');
          highAlertPoints += 2;
        }
        if (dcSig?.signal === 'Bearish') {
          const lastDc = matrix?.donchianSummary?.latestAlert;
          exitTriggers.push(
            lastDc?.type === 'SELL'
              ? `DC(20) SELL @ ${formatINR(lastDc.triggerPrice)}`
              : 'DC(20) Lower Channel'
          );
          highAlertPoints += 2;
        }
        if (matrix && (matrix.consensus === 'Strong Sell' || matrix.consensus === 'Sell')) {
          exitTriggers.push(`Matrix ${matrix.consensus} (${matrix.bearishCount}/${matrix.signals.length} Bear)`);
          highAlertPoints += 2;
        }
        if (sepa?.stage === 4) {
          exitTriggers.push('Stage 4 Downtrend');
          highAlertPoints += 2;
        }
        if (sma50Sig?.signal === 'Bearish') {
          exitTriggers.push('Below 50-Day SMA');
          highAlertPoints += 1;
        }
        if (rsiVal !== null && rsiVal < 45) {
          exitTriggers.push(`Weak RSI (${rsiVal.toFixed(1)} < 45)`);
          highAlertPoints += 1;
        }

        const severity: PortfolioExitDiagnostic['severity'] =
          highAlertPoints >= 3 ||
          (row.holding.stopLossInr !== undefined && row.priceInr <= row.holding.stopLossInr) ||
          matrix?.consensus === 'Strong Sell' ||
          matrix?.consensus === 'Sell'
            ? 'HIGH_EXIT'
            : highAlertPoints >= 1
            ? 'CAUTION'
            : 'HEALTHY';

        return {
          ticker: row.holding.ticker,
          name: row.name,
          sector: row.sector,
          priceInr: row.priceInr,
          marketValueInr: row.marketValueInr,
          weightPct: row.currentWeightPct,
          unrealizedPnlPct: row.unrealizedPnlPct,
          stopLossInr: row.holding.stopLossInr,
          severity,
          exitTriggers,
          consensus: matrix?.consensus ?? 'Neutral',
          scorePct: matrix?.scorePct ?? 50,
          bullishCount: matrix?.bullishCount ?? 0,
          bearishCount: matrix?.bearishCount ?? 0,
          totalSignals: matrix?.signals.length ?? 15,
          sma200Signal: sma200Sig?.signal ?? 'Neutral',
          sma200Reading: sma200Sig?.reading ?? 'N/A',
          sma50Signal: sma50Sig?.signal ?? 'Neutral',
          dcSignal: dcSig?.signal ?? 'Neutral',
          dcReading: dcSig?.reading ?? 'N/A',
          stSignal: stSig?.signal ?? 'Neutral',
          stReading: stSig?.reading ?? 'N/A',
          rsi14: rsiVal,
          stage: sepa?.stage ?? null,
        };
      })
      .sort((a, b) => {
        const sevRank = (s: PortfolioExitDiagnostic['severity']) =>
          s === 'HIGH_EXIT' ? 0 : s === 'CAUTION' ? 1 : 2;
        if (sevRank(a.severity) !== sevRank(b.severity)) {
          return sevRank(a.severity) - sevRank(b.severity);
        }
        return b.bearishCount - a.bearishCount || a.scorePct - b.scorePct;
      });
  }, [summary, marketVersion]);

  const exitByTicker = useMemo(
    () => new Map(exitDiagnostics.map((d) => [d.ticker, d])),
    [exitDiagnostics]
  );

  const highExitCount = exitDiagnostics.filter((d) => d.severity === 'HIGH_EXIT').length;
  const cautionCount = exitDiagnostics.filter((d) => d.severity === 'CAUTION').length;

  const [aiRiskReview, setAiRiskReview] = useState<string | null>(null);
  const [aiRiskLoading, setAiRiskLoading] = useState(false);
  const [aiRiskError, setAiRiskError] = useState<string | null>(null);
  const [aiRiskMeta, setAiRiskMeta] = useState<string | null>(null);
  const totalCapitalAtRisk = useMemo(() => {
    return summary.enriched.reduce((sum, row) => {
      const sl = row.holding.stopLossInr;
      if (sl && sl > 0 && row.priceInr > sl) {
        return sum + (row.priceInr - sl) * row.holding.shares;
      }
      return sum;
    }, 0);
  }, [summary]);

  const rebalance = useMemo(
    () => computeRebalancePlan(summary, cashFlowInr, driftTolerancePct, brokeragePct),
    [summary, cashFlowInr, driftTolerancePct, brokeragePct]
  );

  const selectedScenario = useMemo(
    () =>
      PREDEFINED_SCENARIOS.find((s) => s.id === selectedScenarioId) ?? PREDEFINED_SCENARIOS[0],
    [selectedScenarioId]
  );

  const scenarioResult = useMemo(
    () =>
      simulateScenario(
        summary,
        selectedScenario,
        useCustomShock
          ? {
              equityShockPct: customEquityShock,
              inrShockPct: customInrShock,
              rateBps: customRateBps,
            }
          : undefined
      ),
    [summary, selectedScenario, useCustomShock, customEquityShock, customInrShock, customRateBps]
  );

  const totalTargetWeight = useMemo(
    () => Number(holdings.reduce((s, h) => s + h.targetWeightPct, 0).toFixed(1)),
    [holdings]
  );

  const notify = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3500);
  };

  const handleAddHolding = async () => {
    const stock = STOCK_BY_TICKER[newTicker];
    if (!stock) return;
    const slVal = parseNumericCell(newStopLoss);
    await upsertHolding({
      ticker: newTicker,
      shares: Math.max(1, newShares),
      avgCostInr: Math.max(1, newAvgCost || stock.latestClose),
      targetWeightPct: Math.max(0, Math.min(100, newTargetWeight)),
      stopLossInr: slVal && slVal > 0 ? slVal : undefined,
    });
    setNewStopLoss('');
    notify(`Updated ${newTicker} in portfolio holdings.`);
  };

  // Excel / CSV File Upload Handler
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setFileError(null);
    setFileName(file.name);

    try {
      const buf = await file.arrayBuffer();
      const wb = XLSX.read(buf, { type: 'array' });
      const sheetName = wb.SheetNames[0];
      if (!sheetName) {
        setFileError('No sheets found in uploaded file.');
        setParsedFileRows([]);
        return;
      }
      const ws = wb.Sheets[sheetName];
      const rawRows = XLSX.utils.sheet_to_json<Record<string, unknown>>(ws, { defval: '' });
      if (rawRows.length === 0) {
        setFileError('Uploaded file contains no data rows.');
        setParsedFileRows([]);
        return;
      }

      const keys = Object.keys(rawRows[0]);
      const tickerKey = findColumnKey(keys, [
        /^ticker$/i,
        /^symbol$/i,
        /trading.*symbol/i,
        /^stock$/i,
        /^scrip$/i,
        /^instrument$/i,
      ]);
      const qtyKey = findColumnKey(keys, [
        /^qty$/i,
        /^quantity$/i,
        /^shares$/i,
        /^units$/i,
        /net.*qty/i,
      ]);
      const avgKey = findColumnKey(keys, [
        /avg.*buy/i,
        /avg.*cost/i,
        /avg.*price/i,
        /buy.*price/i,
        /^cost$/i,
        /^price$/i,
      ]);
      const slKey = findColumnKey(keys, [/stop.*loss/i, /^sl$/i, /^stop$/i]);

      if (!tickerKey) {
        setFileError(
          'Could not find a Ticker / Symbol column. Expected columns: Ticker, Quantity, Avg. Buy Price, optional Stop-Loss.'
        );
        setParsedFileRows([]);
        return;
      }

      const parsed: ParsedImportRow[] = [];
      for (const row of rawRows) {
        const rawSym = String(row[tickerKey] ?? '');
        const cleanTicker = normalizeTickerToken(rawSym);
        if (!cleanTicker) continue;

        const stock = STOCK_BY_TICKER[cleanTicker];
        const qty = qtyKey ? parseNumericCell(row[qtyKey]) : undefined;
        const avg = avgKey ? parseNumericCell(row[avgKey]) : undefined;
        const sl = slKey ? parseNumericCell(row[slKey]) : undefined;

        const resolvedCost = avg && avg > 0 ? avg : stock?.latestClose ?? 100;
        const resolvedQty = qty && qty > 0 ? Math.round(qty) : 10;

        parsed.push({
          ticker: cleanTicker,
          shares: resolvedQty,
          avgCostInr: Number(resolvedCost.toFixed(2)),
          stopLossInr: sl && sl > 0 ? Number(sl.toFixed(2)) : undefined,
          knownInUniverse: Boolean(stock),
        });
      }

      if (parsed.length === 0) {
        setFileError('No valid ticker rows were parsed from this file.');
      }
      setParsedFileRows(parsed);
    } catch (err) {
      setFileError(
        err instanceof Error ? err.message : 'Failed to parse Excel/CSV file. Please check format.'
      );
      setParsedFileRows([]);
    }
  };

  const handleConfirmFileImport = async () => {
    if (parsedFileRows.length === 0) return;
    const res = await importHoldings(
      parsedFileRows.map((r) => ({
        ticker: r.ticker,
        shares: r.shares,
        avgCostInr: r.avgCostInr,
        stopLossInr: r.stopLossInr,
      })),
      importMode
    );
    setParsedFileRows([]);
    setFileName('');
    if (fileInputRef.current) fileInputRef.current.value = '';
    notify(
      `${importMode === 'overwrite' ? 'Replaced' : 'Merged'} portfolio with ${res.importedCount} holding(s) (${res.totalCount} total). Weights, sector concentration & exit alerts recalculated.`
    );
  };

  const handleDownloadSampleCsv = () => {
    const sample = [
      'Ticker,Quantity,Avg. Buy Price,Stop-Loss',
      'RELIANCE,45,1290.50,1195.00',
      'TCS,20,3820.00,3550.00',
      'HDFCBANK,70,1640.00,1540.00',
      'BEL,220,285.00,262.00',
      'INFY,50,1740.00,1610.00',
    ].join('\n');
    const blob = new Blob([sample], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'personal-trades-portfolio-template.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  // Parsed Comma-Separated Tickers Preview
  const parsedTickerList = useMemo<ParsedImportRow[]>(() => {
    const tokens = tickerCsvInput
      .split(/[\s,;\n]+/)
      .map(normalizeTickerToken)
      .filter(Boolean);
    const unique = Array.from(new Set(tokens));
    const safeAlloc = Math.max(5000, perStockAllocInr || 100000);
    return unique.map((ticker) => {
      const stock = STOCK_BY_TICKER[ticker];
      const ltp = stock?.latestClose ?? 500;
      const shares = Math.max(1, Math.round(safeAlloc / Math.max(1, ltp)));
      return {
        ticker,
        shares,
        avgCostInr: Number(ltp.toFixed(2)),
        knownInUniverse: Boolean(stock),
      };
    });
  }, [tickerCsvInput, perStockAllocInr]);

  const handleImportTickerListToPortfolio = async () => {
    if (parsedTickerList.length === 0) return;
    const res = await importHoldings(
      parsedTickerList.map((r) => ({
        ticker: r.ticker,
        shares: r.shares,
        avgCostInr: r.avgCostInr,
      })),
      importMode
    );
    notify(
      `${importMode === 'overwrite' ? 'Replaced' : 'Merged'} portfolio with ${res.importedCount} tickers (${res.totalCount} total) at ₹${perStockAllocInr.toLocaleString('en-IN')}/stock allocation.`
    );
  };

  const handleAddTickerListToWatchlist = async () => {
    if (parsedTickerList.length === 0) return;
    await addManyToWatchlist(parsedTickerList.map((r) => r.ticker));
    notify(`Added ${parsedTickerList.length} ticker(s) to your Watchlist.`);
  };

  const handlePushExitAlert = async (diag: PortfolioExitDiagnostic) => {
    await addAlert({
      ticker: diag.ticker,
      category: 'price',
      title: `EXIT ALERT: ${diag.ticker} — ${diag.consensus} (${diag.scorePct}/100)`,
      message: `Portfolio trend turned negative: ${diag.exitTriggers.join(' · ')}. LTP ${formatINR(diag.priceInr)} (${formatPct(diag.unrealizedPnlPct)} P&L).`,
    });
    setAlertedHoldings((prev) => ({ ...prev, [diag.ticker]: true }));
    notify(`Exit alert logged for ${diag.ticker} in Notifications.`);
  };

  const handleNormalizeWeights = async () => {
    if (holdings.length === 0 || totalTargetWeight <= 0) return;
    for (const h of holdings) {
      const normalized = Number(((h.targetWeightPct / totalTargetWeight) * 100).toFixed(1));
      await upsertHolding({ ...h, targetWeightPct: normalized });
    }
    notify('Normalized all target allocation weights to sum to 100%.');
  };

  const handleApplyRebalance = async () => {
    const updates = rebalance.orders
      .filter((o) => o.action !== 'HOLD')
      .map((o) => ({ ticker: o.ticker, targetShares: o.targetShares }));
    if (updates.length === 0) return;
    await applyRebalanceShares(updates);
    setCashFlowInr(0);
    notify(
      `Executed ${updates.length} rebalancing order(s) via ${connectors.brokerConnectorName} simulation.`
    );
  };

  const handleGeneratePdf = () => {
    generatePortfolioPdfReport(
      summary,
      rebalance,
      scenarioResult,
      user?.displayName || 'NSE Institutional Desk'
    );
    notify('Generated & downloaded Portfolio & Risk PDF Snapshot Report.');
  };

  const visibleDiagnostics = showOnlyAlerts
    ? exitDiagnostics.filter((d) => d.severity !== 'HEALTHY')
    : exitDiagnostics;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Portfolio &amp; Risk Management
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Real-time negative-trend &amp; exit monitoring (200 SMA, Donchian, Supertrend, Indicators Matrix Summary), Excel/CSV &amp; TradingView ticker import, D3 allocation treemap, tax-aware rebalancing, and macro stress testing.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 self-start lg:self-auto">
          <button
            onClick={() => {
              setActiveTab('overview');
              setShowImportPanel((v) => !v);
            }}
            className={`inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold rounded-lg border transition-colors whitespace-nowrap ${
              showImportPanel
                ? 'border-blue-600 bg-blue-600/10 text-blue-700 dark:text-blue-300'
                : 'border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            Import / Update Holdings
          </button>

          <button
            onClick={handleGeneratePdf}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
          >
            <FileDown className="w-4 h-4" />
            Generate PDF Report
          </button>
        </div>
      </div>

      {toast && (
        <div className="flex items-center gap-2 px-4 py-2.5 text-xs font-medium rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300">
          <Check className="w-4 h-4 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* Portfolio KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Market Value</div>
          <div className="text-lg font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
            {formatINRCompact(summary.totalMarketValueInr)}
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            Inv {formatINRCompact(summary.totalInvestedInr)}
          </div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Unrealized P&amp;L</div>
          <div
            className={`text-lg font-bold font-mono tabular-nums mt-1 ${
              summary.totalUnrealizedPnlInr >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {formatINRCompact(summary.totalUnrealizedPnlInr)}
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            {formatPct(summary.totalUnrealizedPnlPct)}
          </div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Day&apos;s P&amp;L</div>
          <div
            className={`text-lg font-bold font-mono tabular-nums mt-1 ${
              summary.totalDailyPnlInr >= 0
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-red-600 dark:text-red-400'
            }`}
          >
            {formatINRCompact(summary.totalDailyPnlInr)}
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            {formatPct(summary.totalDailyPnlPct)}
          </div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Exit / Trend Alerts</div>
          <div
            className={`text-lg font-bold font-mono tabular-nums mt-1 ${
              highExitCount > 0
                ? 'text-red-600 dark:text-red-400'
                : cautionCount > 0
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-emerald-600 dark:text-emerald-400'
            }`}
          >
            {highExitCount} High · {cautionCount} Watch
          </div>
          <div className="text-[11px] text-slate-500 truncate">
            {highExitCount > 0 ? 'Negative trend / sell triggers' : 'All holdings intact'}
          </div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">Beta / Sharpe</div>
          <div className="text-lg font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
            {summary.portfolioBeta.toFixed(2)} / {summary.sharpeRatio.toFixed(2)}
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            Vol {summary.annualizedVolPct.toFixed(1)}% · DD -{summary.maxDrawdownEstPct.toFixed(1)}%
          </div>
        </div>
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs text-slate-500">
            {totalCapitalAtRisk > 0 ? 'Risk to Stops / 1D VaR' : '95% 1-Day VaR'}
          </div>
          <div className="text-lg font-bold font-mono tabular-nums text-amber-600 dark:text-amber-400 mt-1">
            {formatINRCompact(totalCapitalAtRisk > 0 ? totalCapitalAtRisk : summary.var95DailyInr)}
          </div>
          <div className="text-[11px] font-mono text-slate-500">
            {totalCapitalAtRisk > 0
              ? `1D VaR ${formatINRCompact(summary.var95DailyInr)}`
              : 'Parametric 1.65σ'}
          </div>
        </div>
      </div>

      {/* Sub-navigation Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 w-fit">
          {(
            [
              { id: 'overview', label: 'Exit Alerts, Import & Holdings' },
              { id: 'watchlists', label: `Watchlist Analysis (${customWatchlists.length}/5)` },
              { id: 'rebalance', label: 'Automatic Rebalancing' },
              { id: 'scenarios', label: 'Scenario & Shock Analysis' },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3.5 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {sectorConcentration.length > 0 && (
          <div className="text-xs text-slate-500 font-mono tabular-nums flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-sans font-semibold text-slate-600 dark:text-slate-300">
              Top Sector Concentration:
            </span>
            {sectorConcentration.slice(0, 3).map((s) => (
              <span key={s.sector}>
                {s.sector}{' '}
                <strong
                  className={
                    s.weightPct >= 35
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-slate-900 dark:text-slate-100'
                  }
                >
                  {s.weightPct.toFixed(1)}%
                </strong>
              </span>
            ))}
          </div>
        )}
      </div>

      {/* TAB 1: Exit Alerts, Quick Import, D3 Treemap & Holdings Editor */}
      {activeTab === 'watchlists' && (
        <WatchlistAnalysisSection onInspectStock={onInspectStock} />
      )}

      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* QUICK PORTFOLIO IMPORT & PERIODIC UPDATE PANEL */}
          {showImportPanel && (
            <section className="border border-blue-500/30 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3 bg-slate-50/70 dark:bg-slate-900/50">
                <div>
                  <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                    Portfolio Quick Import &amp; Periodic Update
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Upload broker holdings (Excel/CSV) or paste TradingView-style tickers — weights, sector concentration, VaR &amp; exit alerts update automatically.
                  </p>
                </div>

                {/* Overwrite vs Merge Mode Switcher */}
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-slate-500 font-medium">On Import:</span>
                  <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                    <button
                      type="button"
                      onClick={() => setImportMode('overwrite')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap ${
                        importMode === 'overwrite'
                          ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      Overwrite Existing
                    </button>
                    <button
                      type="button"
                      onClick={() => setImportMode('merge')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap ${
                        importMode === 'merge'
                          ? 'bg-blue-600 text-white font-semibold'
                          : 'text-slate-600 dark:text-slate-400'
                      }`}
                    >
                      Merge with Existing
                    </button>
                  </div>
                </div>
              </div>

              {/* Import Option Selector */}
              <div className="px-5 pt-4 flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
                <button
                  type="button"
                  onClick={() => setImportTab('file')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors whitespace-nowrap ${
                    importTab === 'file'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  <FileSpreadsheet className="w-3.5 h-3.5" />
                  1. Excel / CSV Upload (.xlsx, .xls, .csv)
                </button>
                <button
                  type="button"
                  onClick={() => setImportTab('tickers')}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors whitespace-nowrap ${
                    importTab === 'tickers'
                      ? 'border-blue-500 bg-blue-500/10 text-blue-700 dark:text-blue-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
                  }`}
                >
                  <ListPlus className="w-3.5 h-3.5" />
                  2. Comma-Separated Tickers (TradingView Style)
                </button>
              </div>

              <div className="p-5">
                {importTab === 'file' ? (
                  <div className="space-y-4">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-xs text-slate-600 dark:text-slate-400">
                        Supported columns:{' '}
                        <span className="font-mono text-slate-900 dark:text-slate-100">
                          Ticker, Quantity, Avg. Buy Price
                        </span>{' '}
                        and optional{' '}
                        <span className="font-mono text-slate-900 dark:text-slate-100">Stop-Loss</span>{' '}
                        (also accepts Zerodha/Dhan column names like Symbol, Qty, Avg Cost).
                      </div>
                      <button
                        type="button"
                        onClick={handleDownloadSampleCsv}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
                      >
                        <Download className="w-3.5 h-3.5" />
                        Sample CSV Template
                      </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".xlsx,.xls,.csv"
                        onChange={handleFileChange}
                        className="block text-xs text-slate-600 dark:text-slate-300 file:mr-3 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
                      />
                      {fileName && (
                        <span className="text-xs font-mono text-slate-500">
                          Loaded: {fileName} ({parsedFileRows.length} rows)
                        </span>
                      )}
                    </div>

                    {fileError && (
                      <div className="text-xs text-red-600 dark:text-red-400 font-medium">
                        {fileError}
                      </div>
                    )}

                    {parsedFileRows.length > 0 && (
                      <div className="space-y-3">
                        <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg max-h-48 overflow-y-auto">
                          <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                            <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] font-sans text-slate-500">
                              <tr>
                                <th className="py-2 px-3">Ticker</th>
                                <th className="py-2 px-3 text-right">Qty</th>
                                <th className="py-2 px-3 text-right">Avg Buy Price</th>
                                <th className="py-2 px-3 text-right">Stop-Loss</th>
                                <th className="py-2 px-3">NSE Status</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                              {parsedFileRows.map((r, i) => (
                                <tr key={`${r.ticker}-${i}`}>
                                  <td className="py-1.5 px-3 font-semibold text-slate-900 dark:text-slate-100">
                                    {r.ticker}
                                  </td>
                                  <td className="py-1.5 px-3 text-right">{r.shares}</td>
                                  <td className="py-1.5 px-3 text-right">
                                    {formatINR(r.avgCostInr)}
                                  </td>
                                  <td className="py-1.5 px-3 text-right text-red-600 dark:text-red-400">
                                    {r.stopLossInr ? formatINR(r.stopLossInr) : '—'}
                                  </td>
                                  <td className="py-1.5 px-3 font-sans text-[11px]">
                                    {r.knownInUniverse ? (
                                      <span className="text-emerald-600 dark:text-emerald-400">
                                        Matched NSE Live
                                      </span>
                                    ) : (
                                      <span className="text-amber-600 dark:text-amber-400">
                                        Custom / External
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>

                        <div className="flex items-center justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              setParsedFileRows([]);
                              setFileName('');
                              if (fileInputRef.current) fileInputRef.current.value = '';
                            }}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300"
                          >
                            Clear
                          </button>
                          <button
                            type="button"
                            onClick={handleConfirmFileImport}
                            className="inline-flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 whitespace-nowrap"
                          >
                            <Check className="w-3.5 h-3.5" />
                            {importMode === 'overwrite'
                              ? `Overwrite Portfolio (${parsedFileRows.length} Stocks)`
                              : `Merge ${parsedFileRows.length} Stocks into Portfolio`}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
                      <div className="lg:col-span-8 space-y-1.5">
                        <label className="block text-xs font-medium text-slate-600 dark:text-slate-400">
                          Paste Comma-Separated Tickers (TradingView format supported, e.g.{' '}
                          <span className="font-mono">NSE:RELIANCE, NSE:TCS, NSE:INFY</span>)
                        </label>
                        <textarea
                          rows={3}
                          value={tickerCsvInput}
                          onChange={(e) => setTickerCsvInput(e.target.value)}
                          placeholder="NSE:RELIANCE, NSE:TCS, NSE:INFY, NSE:HAL, NSE:TRENT"
                          className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                        />
                      </div>

                      <div className="lg:col-span-4 space-y-2 text-xs">
                        <label className="block font-medium text-slate-600 dark:text-slate-400">
                          Default Equal Allocation per Stock (₹)
                        </label>
                        <input
                          type="number"
                          min={5000}
                          step={25000}
                          value={perStockAllocInr}
                          onChange={(e) => setPerStockAllocInr(Math.max(5000, Number(e.target.value) || 100000))}
                          className="w-full px-3 py-2 font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 text-slate-900 dark:text-slate-100"
                        />
                        <p className="text-[11px] text-slate-500">
                          Auto-sizes shares at live NSE LTP ({parsedTickerList.length} unique tickers detected ·{' '}
                          {parsedTickerList.filter((t) => t.knownInUniverse).length} matched in live NSE universe).
                        </p>
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={handleAddTickerListToWatchlist}
                        disabled={parsedTickerList.length === 0}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 whitespace-nowrap"
                      >
                        <Star className="w-3.5 h-3.5 text-amber-500" />
                        Add {parsedTickerList.length} to Watchlist
                      </button>
                      <button
                        type="button"
                        onClick={handleImportTickerListToPortfolio}
                        disabled={parsedTickerList.length === 0}
                        className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40 whitespace-nowrap"
                      >
                        <Upload className="w-3.5 h-3.5" />
                        {importMode === 'overwrite'
                          ? `Overwrite Portfolio (${parsedTickerList.length})`
                          : `Merge into Portfolio (${parsedTickerList.length})`}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </section>
          )}

          {/* PORTFOLIO EXIT & NEGATIVE TREND ALERTS (200 SMA, DONCHIAN, SUPERTREND, MULTI-INDICATOR MATRIX) */}
          <section className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-2.5">
                <AlertTriangle
                  className={`w-4 h-4 shrink-0 ${
                    highExitCount > 0
                      ? 'text-red-500'
                      : cautionCount > 0
                      ? 'text-amber-500'
                      : 'text-emerald-500'
                  }`}
                />
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                  Portfolio Exit &amp; Negative Trend Monitor
                </h2>
                <span className="text-xs font-mono tabular-nums text-slate-500">
                  <strong className="text-red-600 dark:text-red-400">{highExitCount} High Exit</strong> ·{' '}
                  <strong className="text-amber-600 dark:text-amber-400">{cautionCount} Caution</strong> ·{' '}
                  <strong className="text-emerald-600 dark:text-emerald-400">
                    {exitDiagnostics.length - highExitCount - cautionCount} Healthy
                  </strong>
                </span>
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={aiRiskLoading || exitDiagnostics.length === 0}
                  onClick={async () => {
                    setAiRiskLoading(true);
                    setAiRiskError(null);
                    try {
                      const sectorMap = new Map<string, number>();
                      for (const row of summary.enriched) {
                        sectorMap.set(row.sector, (sectorMap.get(row.sector) ?? 0) + row.currentWeightPct);
                      }
                      const topSectors = Array.from(sectorMap.entries())
                        .sort((a, b) => b[1] - a[1])
                        .slice(0, 5)
                        .map(([sector, weightPct]) => ({ sector, weightPct: Number(weightPct.toFixed(1)) }));
                      const portfolioSnapshot = {
                        totalMarketValueInr: Math.round(summary.totalMarketValueInr),
                        totalUnrealizedPnlPct: Number(summary.totalUnrealizedPnlPct.toFixed(2)),
                        holdingCount: exitDiagnostics.length,
                        highExitCount,
                        cautionCount,
                        healthyCount: exitDiagnostics.length - highExitCount - cautionCount,
                        topSectors,
                        flaggedHoldings: exitDiagnostics
                          .filter((d) => d.severity !== 'HEALTHY')
                          .slice(0, 12)
                          .map((d) => ({
                            ticker: d.ticker,
                            sector: d.sector,
                            weightPct: Number(d.weightPct.toFixed(1)),
                            pnlPct: Number(d.unrealizedPnlPct.toFixed(1)),
                            severity: d.severity,
                            consensus: d.consensus,
                            rsi14: d.rsi14 !== null ? Number(d.rsi14.toFixed(1)) : null,
                            triggers: d.exitTriggers,
                          })),
                      };
                      const data = await postAiJson<{ review?: string; generatedAtIst?: string }>(
                        '/api/ai/portfolio-review',
                        { portfolioSnapshot }
                      );
                      setAiRiskReview(String(data.review || ''));
                      setAiRiskMeta(data.generatedAtIst ? `Generated ${data.generatedAtIst}` : null);
                    } catch (err) {
                      setAiRiskError(
                        err instanceof Error ? err.message : 'Unable to generate AI risk review.'
                      );
                    } finally {
                      setAiRiskLoading(false);
                    }
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white transition-colors whitespace-nowrap"
                >
                  {aiRiskLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Reviewing…</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>{aiRiskReview ? 'Refresh AI Risk Review' : 'AI Risk Review'}</span>
                    </>
                  )}
                </button>

                <div className="inline-flex items-center p-0.5 rounded-lg bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-[11px]">
                  <button
                    type="button"
                    onClick={() => setShowOnlyAlerts(true)}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap ${
                      showOnlyAlerts
                        ? 'bg-red-600 text-white font-semibold'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    Flagged Alerts ({highExitCount + cautionCount})
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowOnlyAlerts(false)}
                    className={`px-2.5 py-1 rounded-md font-medium transition-colors whitespace-nowrap ${
                      !showOnlyAlerts
                        ? 'bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 font-semibold'
                        : 'text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    All Holdings ({exitDiagnostics.length})
                  </button>
                </div>
              </div>
            </div>

            {aiRiskError && (
              <div className="px-5 py-3 text-xs text-red-600 dark:text-red-400 bg-red-50/70 dark:bg-red-950/30 border-b border-red-200 dark:border-red-900/50">
                {aiRiskError}
              </div>
            )}

            {aiRiskReview && (
              <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-800 bg-blue-50/40 dark:bg-blue-950/20">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5 text-xs font-bold text-blue-700 dark:text-blue-300">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>AI Portfolio Risk &amp; Exit Review</span>
                    {aiRiskMeta && (
                      <span className="font-normal font-mono text-[10px] text-slate-500">
                        · {aiRiskMeta}
                      </span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setAiRiskReview(null)}
                    className="text-[11px] font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200"
                  >
                    Dismiss
                  </button>
                </div>
                <div className="text-xs leading-relaxed text-slate-700 dark:text-slate-200 space-y-1.5">
                  {renderStructuredAiLines(aiRiskReview)}
                </div>
              </div>
            )}

            {visibleDiagnostics.length === 0 ? (
              <div className="px-5 py-6 text-xs text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                <Check className="w-4 h-4 shrink-0" />
                <span>
                  No holdings currently show High Exit or Negative Trend breakdowns (all positions above key 200 SMA, Supertrend &amp; Donchian supports).
                </span>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Holding &amp; Alert Level</th>
                      <th className="py-2.5 px-3">Triggered Exit Signals</th>
                      <th className="py-2.5 px-3">Indicators Matrix Summary</th>
                      <th className="py-2.5 px-3">200-Day SMA</th>
                      <th className="py-2.5 px-3">Donchian (20)</th>
                      <th className="py-2.5 px-3">Supertrend (10,3)</th>
                      <th className="py-2.5 px-3 text-right">RSI (14)</th>
                      <th className="py-2.5 px-3 text-right">Pos / P&amp;L</th>
                      <th className="py-2.5 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {visibleDiagnostics.map((d) => {
                      const isHigh = d.severity === 'HIGH_EXIT';
                      const isCaution = d.severity === 'CAUTION';
                      const sigColor = (sig: 'Bullish' | 'Neutral' | 'Bearish') =>
                        sig === 'Bearish'
                          ? 'text-red-600 dark:text-red-400 font-semibold'
                          : sig === 'Bullish'
                          ? 'text-emerald-600 dark:text-emerald-400 font-medium'
                          : 'text-amber-600 dark:text-amber-400';

                      return (
                        <tr
                          key={d.ticker}
                          className={
                            isHigh
                              ? 'bg-red-500/[0.04] dark:bg-red-500/[0.07] hover:bg-red-500/[0.08]'
                              : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                          }
                        >
                          <td className="py-3 px-4 whitespace-nowrap">
                            <button
                              onClick={() => onInspectStock(d.ticker)}
                              className="font-mono font-bold text-slate-900 dark:text-slate-100 hover:text-blue-500 text-left"
                            >
                              {d.ticker}
                            </button>
                            <div
                              className={`text-[10px] font-bold uppercase tracking-wide mt-0.5 ${
                                isHigh
                                  ? 'text-red-600 dark:text-red-400'
                                  : isCaution
                                  ? 'text-amber-600 dark:text-amber-400'
                                  : 'text-emerald-600 dark:text-emerald-400'
                              }`}
                            >
                              {isHigh
                                ? 'HIGH EXIT ALERT'
                                : isCaution
                                ? 'WATCH / CAUTION'
                                : 'TREND INTACT'}
                            </div>
                          </td>
                          <td className="py-3 px-3 max-w-[230px]">
                            {d.exitTriggers.length > 0 ? (
                              <div className="text-[11px] font-medium text-red-700 dark:text-red-300 leading-snug">
                                {d.exitTriggers.join(' · ')}
                              </div>
                            ) : (
                              <span className="text-[11px] text-slate-500">No sell breakdowns</span>
                            )}
                          </td>
                          <td className="py-3 px-3 font-mono tabular-nums whitespace-nowrap">
                            <div
                              className={`font-bold ${
                                d.consensus === 'Strong Sell' || d.consensus === 'Sell'
                                  ? 'text-red-600 dark:text-red-400'
                                  : d.consensus === 'Strong Buy' || d.consensus === 'Buy'
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-amber-600 dark:text-amber-400'
                              }`}
                            >
                              {d.consensus} · {d.scorePct}/100
                            </div>
                            <div className="text-[10px] text-slate-500">
                              <span className="text-red-500 font-semibold">{d.bearishCount} Bear</span> ·{' '}
                              <span className="text-emerald-600 dark:text-emerald-400">{d.bullishCount} Bull</span> /{' '}
                              {d.totalSignals}
                            </div>
                          </td>
                          <td className="py-3 px-3 font-mono tabular-nums whitespace-nowrap">
                            <div className={sigColor(d.sma200Signal)}>
                              {d.sma200Signal === 'Bearish'
                                ? 'BELOW 200D'
                                : d.sma200Signal === 'Bullish'
                                ? 'Above 200D'
                                : 'Near 200D'}
                            </div>
                            <div className="text-[10px] text-slate-500 truncate max-w-[130px]">
                              {d.sma200Reading}
                            </div>
                          </td>
                          <td className="py-3 px-3 font-mono tabular-nums whitespace-nowrap">
                            <div className={sigColor(d.dcSignal)}>
                              {d.dcSignal === 'Bearish'
                                ? 'DC SELL / Lower'
                                : d.dcSignal === 'Bullish'
                                ? 'DC Bullish'
                                : 'Mid-Channel'}
                            </div>
                            <div className="text-[10px] text-slate-500 truncate max-w-[170px]" title={d.dcReading}>
                              {d.dcReading}
                            </div>
                          </td>
                          <td className="py-3 px-3 font-mono tabular-nums whitespace-nowrap">
                            <div className={sigColor(d.stSignal)}>
                              {d.stSignal === 'Bearish' ? 'SELL (Bearish)' : 'BUY (Bullish)'}
                            </div>
                            <div className="text-[10px] text-slate-500 truncate max-w-[140px]">
                              {d.stReading}
                            </div>
                          </td>
                          <td
                            className={`py-3 px-3 text-right font-mono tabular-nums font-semibold whitespace-nowrap ${
                              d.rsi14 !== null && d.rsi14 < 45
                                ? 'text-red-600 dark:text-red-400'
                                : d.rsi14 !== null && d.rsi14 >= 55 && d.rsi14 <= 80
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-amber-600 dark:text-amber-400'
                            }`}
                          >
                            {d.rsi14 !== null ? d.rsi14.toFixed(1) : '—'}
                          </td>
                          <td className="py-3 px-3 text-right font-mono tabular-nums whitespace-nowrap">
                            <div className="font-semibold text-slate-900 dark:text-slate-100">
                              {formatINRCompact(d.marketValueInr)}
                            </div>
                            <div
                              className={`text-[10px] ${
                                d.unrealizedPnlPct >= 0
                                  ? 'text-emerald-600 dark:text-emerald-400'
                                  : 'text-red-600 dark:text-red-400'
                              }`}
                            >
                              {formatPct(d.unrealizedPnlPct)} · {d.weightPct.toFixed(1)}%
                            </div>
                          </td>
                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            <div className="inline-flex items-center gap-1.5">
                              {d.severity !== 'HEALTHY' && (
                                <button
                                  type="button"
                                  onClick={() => void handlePushExitAlert(d)}
                                  className={`p-1.5 rounded border transition-colors ${
                                    alertedHoldings[d.ticker]
                                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
                                      : 'border-red-500/40 bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20'
                                  }`}
                                  title="Push Exit Alert to Notifications"
                                >
                                  {alertedHoldings[d.ticker] ? (
                                    <Check className="w-3.5 h-3.5" />
                                  ) : (
                                    <BellPlus className="w-3.5 h-3.5" />
                                  )}
                                </button>
                              )}
                              <button
                                type="button"
                                onClick={() => onInspectStock(d.ticker)}
                                className="p-1.5 rounded border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:text-blue-500"
                                title={`Inspect ${d.ticker} chart`}
                              >
                                <LineChart className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Portfolio Allocation Treemap (D3.js)
                </h2>
                <p className="text-xs text-slate-500">
                  Tile area reflects INR market value · Tile color encodes daily return % · Click any tile to inspect chart
                </p>
              </div>
            </div>
            <PortfolioTreemap holdings={summary.enriched} onSelectTicker={onInspectStock} />
          </div>

          {/* Holdings Table & Target Allocation Editor */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Holdings &amp; Target Allocations ({holdings.length})
                </h3>
                <span
                  className={`text-xs font-mono font-semibold ${
                    Math.abs(totalTargetWeight - 100) < 0.2
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-amber-600 dark:text-amber-400'
                  }`}
                >
                  Target Sum: {totalTargetWeight.toFixed(1)}%
                </span>
              </div>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setShowImportPanel(true)}
                  className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
                >
                  Bulk Import / Refresh CSV
                </button>
                {Math.abs(totalTargetWeight - 100) >= 0.2 && (
                  <button
                    onClick={handleNormalizeWeights}
                    className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Normalize Targets to 100%
                  </button>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-4">Ticker / Sector</th>
                    <th className="py-2.5 px-3 text-right">Shares</th>
                    <th className="py-2.5 px-3 text-right">Avg Cost (₹)</th>
                    <th className="py-2.5 px-3 text-right">Stop-Loss (₹)</th>
                    <th className="py-2.5 px-3 text-right">LTP (₹)</th>
                    <th className="py-2.5 px-3 text-right">Market Value</th>
                    <th className="py-2.5 px-3 text-right">P&amp;L %</th>
                    <th className="py-2.5 px-3 text-right">Actual Wt</th>
                    <th className="py-2.5 px-3 text-right">Target Wt %</th>
                    <th className="py-2.5 px-4 text-right">Remove</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {summary.enriched.map((row) => {
                    const diag = exitByTicker.get(row.holding.ticker);
                    const stopBreached =
                      row.holding.stopLossInr !== undefined &&
                      row.priceInr <= row.holding.stopLossInr;
                    return (
                      <tr
                        key={row.holding.id}
                        className="hover:bg-slate-50 dark:hover:bg-slate-800/40"
                      >
                        <td className="py-2.5 px-4">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => onInspectStock(row.holding.ticker)}
                              className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 text-left"
                            >
                              {row.holding.ticker}
                            </button>
                            {diag?.severity === 'HIGH_EXIT' && (
                              <span className="text-[10px] font-bold text-red-600 dark:text-red-400">
                                EXIT
                              </span>
                            )}
                          </div>
                          <div className="text-[11px] text-slate-500">{row.sector}</div>
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <input
                            type="number"
                            min={0}
                            value={row.holding.shares}
                            onChange={(e) =>
                              upsertHolding({
                                ...row.holding,
                                shares: Math.max(0, Number(e.target.value) || 0),
                              })
                            }
                            className="w-20 px-2 py-1 text-right font-mono tabular-nums rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                          />
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-600 dark:text-slate-300">
                          {formatINR(row.holding.avgCostInr)}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <input
                            type="number"
                            min={0}
                            step={1}
                            placeholder="—"
                            value={row.holding.stopLossInr ?? ''}
                            onChange={(e) => {
                              const v = Number(e.target.value);
                              upsertHolding({
                                ...row.holding,
                                stopLossInr: v > 0 ? v : undefined,
                              });
                            }}
                            className={`w-24 px-2 py-1 text-right font-mono tabular-nums rounded border bg-white dark:bg-slate-950 ${
                              stopBreached
                                ? 'border-red-500 text-red-600 dark:text-red-400 font-semibold'
                                : 'border-slate-300 dark:border-slate-700'
                            }`}
                          />
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-900 dark:text-slate-100">
                          {formatINR(row.priceInr)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium">
                          {formatINR(row.marketValueInr, 0)}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono tabular-nums font-medium ${
                            row.unrealizedPnlPct >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(row.unrealizedPnlPct)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {row.currentWeightPct.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <input
                            type="number"
                            step={0.5}
                            min={0}
                            max={100}
                            value={row.holding.targetWeightPct}
                            onChange={(e) =>
                              upsertHolding({
                                ...row.holding,
                                targetWeightPct: Math.max(
                                  0,
                                  Math.min(100, Number(e.target.value) || 0)
                                ),
                              })
                            }
                            className="w-16 px-2 py-1 text-right font-mono tabular-nums rounded border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                          />
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          <button
                            onClick={() => removeHolding(row.holding.id)}
                            className="p-1 text-slate-400 hover:text-red-500"
                            title="Remove holding"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Add Position Bar */}
            <div className="p-4 bg-slate-50/70 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800 flex flex-wrap items-end gap-3 text-xs">
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Add NSE Equity</label>
                <select
                  value={newTicker}
                  onChange={(e) => {
                    const t = e.target.value;
                    setNewTicker(t);
                    const s = STOCK_BY_TICKER[t];
                    if (s) setNewAvgCost(Math.round(s.latestClose));
                  }}
                  className="px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950 max-w-[200px]"
                >
                  {INDIAN_STOCKS.map((s) => (
                    <option key={s.ticker} value={s.ticker}>
                      {s.ticker} (₹{Math.round(s.latestClose)})
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Shares</label>
                <input
                  type="number"
                  min={1}
                  value={newShares}
                  onChange={(e) => setNewShares(Number(e.target.value) || 1)}
                  className="w-24 px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Avg Cost (₹)</label>
                <input
                  type="number"
                  min={1}
                  value={newAvgCost}
                  onChange={(e) => setNewAvgCost(Number(e.target.value) || 1)}
                  className="w-28 px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Stop-Loss (Opt.)</label>
                <input
                  type="number"
                  min={0}
                  placeholder="Optional"
                  value={newStopLoss}
                  onChange={(e) => setNewStopLoss(e.target.value)}
                  className="w-28 px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-[11px] text-slate-500">Target Wt %</label>
                <input
                  type="number"
                  step={0.5}
                  min={0}
                  max={100}
                  value={newTargetWeight}
                  onChange={(e) => setNewTargetWeight(Number(e.target.value) || 0)}
                  className="w-20 px-2.5 py-1.5 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <button
                onClick={handleAddHolding}
                className="inline-flex items-center gap-1.5 px-3.5 py-1.5 font-medium rounded-lg bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 hover:opacity-90"
              >
                <Plus className="w-3.5 h-3.5" />
                Add / Update Holding
              </button>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Automatic Rebalancing Engine with Indian Statutory Costs */}
      {activeTab === 'rebalance' && (
        <div className="space-y-5">
          {/* Controls */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 flex flex-wrap items-end justify-between gap-4">
            <div className="flex flex-wrap items-end gap-4 text-xs">
              <div className="space-y-1">
                <label className="block text-slate-500">Fresh Capital / Withdrawal (₹)</label>
                <input
                  type="number"
                  step={50000}
                  value={cashFlowInr}
                  onChange={(e) => setCashFlowInr(Number(e.target.value) || 0)}
                  className="w-40 px-3 py-2 font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-slate-500">Drift Tolerance (%)</label>
                <input
                  type="number"
                  step={0.25}
                  min={0}
                  max={10}
                  value={driftTolerancePct}
                  onChange={(e) => setDriftTolerancePct(Math.max(0, Number(e.target.value) || 0))}
                  className="w-28 px-3 py-2 font-mono tabular-nums rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
              </div>
              <div className="space-y-1">
                <label className="block text-slate-500">Brokerage Rate (%)</label>
                <select
                  value={brokeragePct}
                  onChange={(e) => setBrokeragePct(Number(e.target.value))}
                  className="px-3 py-2 font-mono rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                >
                  <option value={0}>0.00% (Zerodha / Dhan Delivery)</option>
                  <option value={0.1}>0.10% (Hybrid Broker)</option>
                  <option value={0.3}>0.30% (Full-Service Broker)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleApplyRebalance}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-600 text-white hover:bg-emerald-700 whitespace-nowrap"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Apply Suggested Orders
            </button>
          </div>

          {/* Statutory Cost Breakdown Card */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <Scale className="w-4 h-4 text-blue-500" />
                <span>Estimated Indian Equity Delivery Transaction Costs</span>
              </div>
              <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400">
                Total Friction: {formatINR(rebalance.totalStatutoryCost)} ({rebalance.costSummary.costBps} bps)
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3 pt-2 border-t border-slate-200 dark:border-slate-800 text-xs font-mono tabular-nums">
              <div>
                <div className="font-sans text-[11px] text-slate-500">Brokerage</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.brokerage)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">STT (0.1%)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.stt)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">NSE Exch (0.00297%)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.exchangeCharges)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">SEBI (₹10/Cr)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.sebiFees)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">Stamp (0.015% Buy)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.stampDuty)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">GST (18%)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.gst)}</div>
              </div>
              <div>
                <div className="font-sans text-[11px] text-slate-500">DP Chg (₹15.93/Sell)</div>
                <div className="font-semibold mt-0.5">{formatINR(rebalance.costSummary.dpCharges)}</div>
              </div>
            </div>
          </div>

          {/* Orders Table */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                Suggested NSE Delivery Orders
              </span>
              <span className="font-mono text-slate-500">
                Total Buy: {formatINRCompact(rebalance.totalBuyValue)} · Total Sell:{' '}
                {formatINRCompact(rebalance.totalSellValue)}
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-4">Ticker</th>
                    <th className="py-2.5 px-3">Action</th>
                    <th className="py-2.5 px-3 text-right">Current → Target Wt</th>
                    <th className="py-2.5 px-3 text-right">Drift</th>
                    <th className="py-2.5 px-3 text-right">Order Qty</th>
                    <th className="py-2.5 px-3 text-right">Order Value</th>
                    <th className="py-2.5 px-3 text-right">STT + Stamp + DP</th>
                    <th className="py-2.5 px-4 text-right">Total Charges</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                  {rebalance.orders.map((o) => (
                    <tr key={o.ticker} className="hover:bg-slate-50 dark:hover:bg-slate-800/40">
                      <td className="py-2.5 px-4 font-semibold text-slate-900 dark:text-slate-100">
                        <button
                          onClick={() => onInspectStock(o.ticker)}
                          className="hover:text-blue-500 hover:underline text-left"
                          title={`Open ${o.ticker} candlestick chart`}
                        >
                          {o.ticker}
                        </button>
                      </td>
                      <td className="py-2.5 px-3 font-semibold">
                        {o.action === 'BUY' ? (
                          <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
                            <ArrowUpRight className="w-3.5 h-3.5" /> BUY
                          </span>
                        ) : o.action === 'SELL' ? (
                          <span className="inline-flex items-center gap-1 text-red-600 dark:text-red-400">
                            <ArrowDownRight className="w-3.5 h-3.5" /> SELL
                          </span>
                        ) : (
                          <span className="text-slate-400">HOLD</span>
                        )}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-600 dark:text-slate-300">
                        {o.currentWeightPct.toFixed(1)}% → {o.targetWeightPct.toFixed(1)}%
                      </td>
                      <td
                        className={`py-2.5 px-3 text-right ${
                          Math.abs(o.driftPct) >= driftTolerancePct
                            ? 'text-amber-600 dark:text-amber-400 font-semibold'
                            : 'text-slate-500'
                        }`}
                      >
                        {formatPct(o.driftPct)}
                      </td>
                      <td className="py-2.5 px-3 text-right font-semibold">
                        {o.deltaShares === 0
                          ? '0'
                          : `${o.deltaShares > 0 ? '+' : ''}${o.deltaShares}`}
                      </td>
                      <td className="py-2.5 px-3 text-right">
                        {o.tradeValueInr > 0 ? formatINR(o.tradeValueInr, 0) : '—'}
                      </td>
                      <td className="py-2.5 px-3 text-right text-slate-500">
                        {o.tradeValueInr > 0
                          ? formatINR(o.costs.stt + o.costs.stampDuty + o.costs.dpCharges)
                          : '—'}
                      </td>
                      <td className="py-2.5 px-4 text-right font-semibold">
                        {o.costs.totalCost > 0 ? formatINR(o.costs.totalCost) : '₹0.00'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Scenario Analysis & Historical Indian Events */}
      {activeTab === 'scenarios' && (
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
          {/* Left: Scenario Selector */}
          <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                <ShieldAlert className="w-4 h-4 text-amber-500" />
                <span>Macro Shocks &amp; Indian Crises</span>
              </div>
              <button
                onClick={() => setUseCustomShock((v) => !v)}
                className={`px-2.5 py-1 text-xs font-medium rounded-md border ${
                  useCustomShock
                    ? 'border-blue-600 bg-blue-600 text-white'
                    : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                }`}
              >
                {useCustomShock ? 'Custom Active' : 'Custom Sliders'}
              </button>
            </div>

            {useCustomShock ? (
              <div className="space-y-4 pt-2">
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600 dark:text-slate-400">NIFTY 50 Equity Shock</span>
                    <span className="font-mono font-semibold">{formatPct(customEquityShock)}</span>
                  </div>
                  <input
                    type="range"
                    min={-50}
                    max={25}
                    step={1}
                    value={customEquityShock}
                    onChange={(e) => setCustomEquityShock(Number(e.target.value))}
                    className="w-full accent-blue-600"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600 dark:text-slate-400">INR Depreciation vs USD</span>
                    <span className="font-mono font-semibold">+{customInrShock}%</span>
                  </div>
                  <input
                    type="range"
                    min={-10}
                    max={20}
                    step={1}
                    value={customInrShock}
                    onChange={(e) => setCustomInrShock(Number(e.target.value))}
                    className="w-full accent-emerald-600"
                  />
                </div>
                <div>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-600 dark:text-slate-400">RBI Repo Rate Change</span>
                    <span className="font-mono font-semibold">
                      {customRateBps >= 0 ? '+' : ''}
                      {customRateBps} bps
                    </span>
                  </div>
                  <input
                    type="range"
                    min={-150}
                    max={250}
                    step={25}
                    value={customRateBps}
                    onChange={(e) => setCustomRateBps(Number(e.target.value))}
                    className="w-full accent-amber-600"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                {(['Macro Shock', 'Historical Indian Event'] as const).map((cat) => (
                  <div key={cat} className="space-y-1.5 pt-1">
                    <div className="text-[11px] font-semibold text-slate-500">{cat}s</div>
                    {PREDEFINED_SCENARIOS.filter((s) => s.category === cat).map((sc) => {
                      const active = sc.id === selectedScenarioId;
                      return (
                        <button
                          key={sc.id}
                          onClick={() => setSelectedScenarioId(sc.id)}
                          className={`w-full text-left p-3 rounded-lg border transition-colors ${
                            active
                              ? 'border-blue-500 bg-blue-500/10'
                              : 'border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-900'
                          }`}
                        >
                          <div className="flex items-center justify-between gap-2 text-xs font-semibold text-slate-900 dark:text-slate-100">
                            <span>{sc.name}</span>
                            <span className="font-mono text-red-600 dark:text-red-400 shrink-0">
                              NIFTY {formatPct(sc.nifty50ShockPct)}
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                            {sc.description}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: Simulation Output & Per-Stock Impact */}
          <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-5">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-slate-100">
                {scenarioResult.scenarioName}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Sector-sensitive &amp; beta-weighted stress simulation across all {summary.enriched.length} holdings
              </p>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs border-y border-slate-200 dark:border-slate-800 py-3">
              <div>
                <div className="text-slate-500">Portfolio Impact</div>
                <div
                  className={`font-mono text-lg font-bold tabular-nums ${
                    scenarioResult.portfolioImpactPct >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPct(scenarioResult.portfolioImpactPct)}
                </div>
                <div className="font-mono text-[11px] text-slate-500">
                  {formatINRCompact(scenarioResult.portfolioImpactInr)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">NIFTY 50 Benchmark</div>
                <div className="font-mono text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatPct(scenarioResult.nifty50ShockPct)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Relative Cushion</div>
                <div
                  className={`font-mono text-lg font-bold tabular-nums ${
                    scenarioResult.relativeAlphaPct >= 0
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}
                >
                  {formatPct(scenarioResult.relativeAlphaPct)}
                </div>
              </div>
              <div>
                <div className="text-slate-500">Post-Shock Value</div>
                <div className="font-mono text-lg font-bold tabular-nums text-slate-900 dark:text-slate-100">
                  {formatINRCompact(scenarioResult.postShockValueInr)}
                </div>
              </div>
            </div>

            {/* Per-Stock Simulated Impact Bar Chart */}
            <div style={{ width: '100%', height: 220 }}>
              <ResponsiveContainer>
                <BarChart
                  data={scenarioResult.stockImpacts}
                  margin={{ top: 8, right: 12, left: 4, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" vertical={false} />
                  <XAxis
                    dataKey="ticker"
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 10, fill: '#64748b' }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => `${v}%`}
                    width={42}
                  />
                  <ReferenceLine y={0} stroke="rgba(148,163,184,0.4)" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#f8fafc',
                    }}
                    formatter={(v: unknown) => [`${Number(v).toFixed(2)}%`, 'Simulated Impact']}
                  />
                  <Bar dataKey="impactPct" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                    {scenarioResult.stockImpacts.map((entry) => (
                      <Cell
                        key={entry.ticker}
                        fill={entry.impactPct >= 0 ? '#10b981' : '#ef4444'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Detailed Table */}
            <div className="overflow-x-auto border border-slate-200 dark:border-slate-800 rounded-lg">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2 px-3">Ticker</th>
                    <th className="py-2 px-3">Sector</th>
                    <th className="py-2 px-3 text-right">Current Value</th>
                    <th className="py-2 px-3 text-right">Shock %</th>
                    <th className="py-2 px-3 text-right">Impact (₹)</th>
                    <th className="py-2 px-3 text-right">Post-Shock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70 font-mono tabular-nums">
                  {scenarioResult.stockImpacts.map((row) => (
                    <tr key={row.ticker}>
                      <td className="py-2 px-3 font-semibold text-slate-900 dark:text-slate-100">
                        <button
                          onClick={() => onInspectStock(row.ticker)}
                          className="hover:text-blue-500 hover:underline text-left"
                          title={`Open ${row.ticker} candlestick chart`}
                        >
                          {row.ticker}
                        </button>
                      </td>
                      <td className="py-2 px-3 font-sans text-slate-500">{row.sector}</td>
                      <td className="py-2 px-3 text-right">{formatINR(row.currentValueInr, 0)}</td>
                      <td
                        className={`py-2 px-3 text-right font-semibold ${
                          row.impactPct >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatPct(row.impactPct)}
                      </td>
                      <td
                        className={`py-2 px-3 text-right ${
                          row.impactInr >= 0
                            ? 'text-emerald-600 dark:text-emerald-400'
                            : 'text-red-600 dark:text-red-400'
                        }`}
                      >
                        {formatINR(row.impactInr, 0)}
                      </td>
                      <td className="py-2 px-3 text-right">{formatINR(row.postValueInr, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
