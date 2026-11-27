import React, { useEffect, useMemo, useState } from 'react';
import {
  AlertTriangle,
  ArrowUpRight,
  BarChart3,
  CheckCircle2,
  Coins,
  Download,
  FileSpreadsheet,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react';
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { IndianTickerSearchInput } from '../components/IndianTickerSearchInput';
import { useAppData } from '../context/AppDataContext';
import { INDIAN_STOCKS, STOCK_BY_TICKER } from '../data/indianMarketData';
import { formatCr, formatINR, formatPct } from '../utils/formatters';

interface FundamentalLabViewProps {
  onInspectStock: (ticker: string) => void;
}

interface GrowthMetric {
  latestDate: string | null;
  latestValue: number | null;
  yoyPct: number | null;
  qoqPct: number | null;
  yoyBasis: string;
  qoqBasis: string;
}

interface IncomeStatementRow {
  date: string;
  salesCr: number | null;
  costOfRevCr: number | null;
  grossProfitCr: number | null;
  operatingExpenseCr: number | null;
  ebitdaCr: number | null;
  ebitdaMarginPct: number | null;
  depreciationCr: number | null;
  ebitCr: number | null;
  opMarginPct: number | null;
  interestExpenseCr: number | null;
  pretaxIncomeCr: number | null;
  taxCr: number | null;
  netProfitCr: number | null;
  netMarginPct: number | null;
  dilutedEps: number | null;
}

interface BalanceSheetRow {
  date: string;
  cashAndInvCr: number | null;
  receivablesCr: number | null;
  inventoryCr: number | null;
  currentAssetsCr: number | null;
  netPpeCr: number | null;
  totalAssetsCr: number | null;
  currentLiabilitiesCr: number | null;
  totalDebtCr: number | null;
  netDebtCr: number | null;
  totalLiabilitiesCr: number | null;
  shareholdersEquityCr: number | null;
  retainedEarningsCr: number | null;
}

interface CashFlowRow {
  date: string;
  operatingCfCr: number | null;
  capexCr: number | null;
  freeCfCr: number | null;
  investingCfCr: number | null;
  financingCfCr: number | null;
  dividendsPaidCr: number | null;
  netChangeInCashCr: number | null;
  cfoToPatPct: number | null;
}

interface LiveFundamentalsResponse {
  symbol: string;
  yahooSymbol: string;
  name: string;
  sector: string;
  industry: string;
  ratios: {
    marketCapCr: number | null;
    enterpriseValueCr: number | null;
    pe: number | null;
    forwardPe: number | null;
    evToEbitda: number | null;
    evToSales: number | null;
    pb: number | null;
    ps: number | null;
    roePct: number | null;
    roaPct: number | null;
    rocePct: number | null;
    dividendYieldPct: number | null;
    payoutRatioPct: number | null;
    fcfYieldPct: number | null;
    grossMarginPct: number | null;
    ebitdaMarginPct: number | null;
    opMarginPct: number | null;
    netMarginPct: number | null;
    debtToEquity: number | null;
    currentRatio: number | null;
    quickRatio: number | null;
    bookValuePerShare: number | null;
    trailingEps: number | null;
    beta: number | null;
  };
  growth: {
    sales: GrowthMetric;
    ebitda: GrowthMetric;
    netProfit: GrowthMetric;
    eps: GrowthMetric;
  };
  quarterlyHistory: {
    date: string;
    salesCr: number | null;
    ebitdaCr: number | null;
    ebitdaMarginPct: number | null;
    netProfitCr: number | null;
    eps: number | null;
  }[];
  statements?: {
    income: { annual: IncomeStatementRow[]; quarterly: IncomeStatementRow[] };
    balanceSheet: { annual: BalanceSheetRow[]; quarterly: BalanceSheetRow[] };
    cashFlow: { annual: CashFlowRow[]; quarterly: CashFlowRow[] };
  };
}

type LabTab = 'statements' | 'ratios' | 'dividend';
type StatementKind = 'income' | 'balanceSheet' | 'cashFlow';
type PeriodMode = 'annual' | 'quarterly';

interface StatementRowSpec<T> {
  label: string;
  accessor: (row: T) => number | null;
  kind: 'cr' | 'pct' | 'eps';
  emphasis?: 'total' | 'subtotal' | 'ratio' | 'normal';
}

function formatPeriodHeader(isoDate: string, mode: PeriodMode): string {
  const parts = isoDate.split('-');
  if (parts.length < 2) return isoDate;
  const year = Number(parts[0]);
  const month = Number(parts[1]);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return isoDate;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const monLabel = months[Math.max(0, Math.min(11, month - 1))];
  const yy = String(year).slice(-2);
  if (mode === 'annual') {
    // Indian fiscal years typically end in March (FY25 = Mar 2025)
    return month === 3 ? `FY${yy}` : `${monLabel} '${yy}`;
  }
  return `${monLabel} '${yy}`;
}

function formatCrCell(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '—';
  const abs = Math.abs(val);
  if (abs >= 1000) {
    return val.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }
  return val.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function formatMetricCell(val: number | null, kind: 'cr' | 'pct' | 'eps'): string {
  if (val === null || !Number.isFinite(val)) return '—';
  if (kind === 'pct') return `${val.toFixed(1)}%`;
  if (kind === 'eps') return `₹${val.toFixed(2)}`;
  return formatCrCell(val);
}

function computeDelta(curr: number | null, prev: number | null, kind: 'cr' | 'pct' | 'eps'): string {
  if (curr === null || prev === null || !Number.isFinite(curr) || !Number.isFinite(prev)) return '—';
  if (kind === 'pct') {
    const diff = curr - prev;
    return `${diff >= 0 ? '+' : ''}${diff.toFixed(1)} pp`;
  }
  if (Math.abs(prev) < 0.01) return '—';
  const pct = ((curr - prev) / Math.abs(prev)) * 100;
  return `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
}

function deltaTone(curr: number | null, prev: number | null): string {
  if (curr === null || prev === null || !Number.isFinite(curr) || !Number.isFinite(prev)) {
    return 'text-slate-400';
  }
  if (curr > prev) return 'text-emerald-600 dark:text-emerald-400';
  if (curr < prev) return 'text-red-600 dark:text-red-400';
  return 'text-slate-500';
}

function formatRatio(val: number | null | undefined, suffix = '×', decimals = 2): string {
  if (val === null || val === undefined || !Number.isFinite(val)) return '—';
  return `${val.toFixed(decimals)}${suffix}`;
}

function formatDebtToEquity(val: number | null | undefined): string {
  if (val === null || val === undefined || !Number.isFinite(val)) return '—';
  // Yahoo financialData.debtToEquity is returned as percentage (e.g. 42.5 => 0.43x)
  const ratio = val / 100;
  return `${ratio.toFixed(2)}×`;
}

const INCOME_SPECS: StatementRowSpec<IncomeStatementRow>[] = [
  { label: 'Revenue from Operations (Sales)', accessor: (r) => r.salesCr, kind: 'cr', emphasis: 'total' },
  { label: 'Cost of Revenue / Material Cost', accessor: (r) => r.costOfRevCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Gross Profit', accessor: (r) => r.grossProfitCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Operating Expenses', accessor: (r) => r.operatingExpenseCr, kind: 'cr', emphasis: 'normal' },
  { label: 'EBITDA', accessor: (r) => r.ebitdaCr, kind: 'cr', emphasis: 'total' },
  { label: 'EBITDA Margin %', accessor: (r) => r.ebitdaMarginPct, kind: 'pct', emphasis: 'ratio' },
  { label: 'Depreciation & Amortization', accessor: (r) => r.depreciationCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Operating Profit (EBIT)', accessor: (r) => r.ebitCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Operating Profit Margin (OPM %)', accessor: (r) => r.opMarginPct, kind: 'pct', emphasis: 'ratio' },
  { label: 'Finance Cost (Interest)', accessor: (r) => r.interestExpenseCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Profit Before Tax (PBT)', accessor: (r) => r.pretaxIncomeCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Tax Provision', accessor: (r) => r.taxCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Net Profit (PAT)', accessor: (r) => r.netProfitCr, kind: 'cr', emphasis: 'total' },
  { label: 'Net Profit Margin %', accessor: (r) => r.netMarginPct, kind: 'pct', emphasis: 'ratio' },
  { label: 'Diluted EPS (₹)', accessor: (r) => r.dilutedEps, kind: 'eps', emphasis: 'subtotal' },
];

const BALANCE_SHEET_SPECS: StatementRowSpec<BalanceSheetRow>[] = [
  { label: 'Cash & Short-Term Investments', accessor: (r) => r.cashAndInvCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Trade Receivables', accessor: (r) => r.receivablesCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Inventories', accessor: (r) => r.inventoryCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Total Current Assets', accessor: (r) => r.currentAssetsCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Net Fixed Assets (PPE)', accessor: (r) => r.netPpeCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Total Assets', accessor: (r) => r.totalAssetsCr, kind: 'cr', emphasis: 'total' },
  { label: 'Total Current Liabilities', accessor: (r) => r.currentLiabilitiesCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Total Borrowings (Debt)', accessor: (r) => r.totalDebtCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Net Debt (Debt − Cash)', accessor: (r) => r.netDebtCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Total Liabilities', accessor: (r) => r.totalLiabilitiesCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Retained Earnings / Reserves', accessor: (r) => r.retainedEarningsCr, kind: 'cr', emphasis: 'normal' },
  { label: "Shareholders' Equity (Net Worth)", accessor: (r) => r.shareholdersEquityCr, kind: 'cr', emphasis: 'total' },
];

const CASH_FLOW_SPECS: StatementRowSpec<CashFlowRow>[] = [
  { label: 'Cash from Operating Activities (CFO)', accessor: (r) => r.operatingCfCr, kind: 'cr', emphasis: 'total' },
  { label: 'Capital Expenditure (CapEx)', accessor: (r) => r.capexCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Free Cash Flow (FCF)', accessor: (r) => r.freeCfCr, kind: 'cr', emphasis: 'total' },
  { label: 'Cash from Investing Activities (CFI)', accessor: (r) => r.investingCfCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Cash from Financing Activities (CFF)', accessor: (r) => r.financingCfCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Cash Dividends Paid', accessor: (r) => r.dividendsPaidCr, kind: 'cr', emphasis: 'normal' },
  { label: 'Net Change in Cash', accessor: (r) => r.netChangeInCashCr, kind: 'cr', emphasis: 'subtotal' },
  { label: 'Cash Conversion (CFO / PAT %)', accessor: (r) => r.cfoToPatPct, kind: 'pct', emphasis: 'ratio' },
];

export const FundamentalLabView: React.FC<FundamentalLabViewProps> = ({ onInspectStock }) => {
  const { marketVersion } = useAppData();

  const sortedByCap = useMemo(
    () => [...INDIAN_STOCKS].sort((a, b) => b.marketCapCr - a.marketCapCr),
    [marketVersion]
  );

  const dividendStocks = useMemo(
    () =>
      [...INDIAN_STOCKS].sort(
        (a, b) => b.dividend.dividendYieldPct - a.dividend.dividendYieldPct
      ),
    [marketVersion]
  );

  const [activeTicker, setActiveTicker] = useState<string>('RELIANCE');
  const [activeTab, setActiveTab] = useState<LabTab>('statements');
  const [statementKind, setStatementKind] = useState<StatementKind>('income');
  const [periodMode, setPeriodMode] = useState<PeriodMode>('annual');

  // Live fundamentals API state
  const [liveData, setLiveData] = useState<LiveFundamentalsResponse | null>(null);
  const [loadingLive, setLoadingLive] = useState<boolean>(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState<number>(0);

  // Screener filter state (Tab 2)
  const [screenerSearch, setScreenerSearch] = useState<string>('');
  const [screenerSector, setScreenerSector] = useState<string>('All');

  // Dividend FCF stress-test overrides (Tab 3)
  const [fcfGrowthOverride, setFcfGrowthOverride] = useState<number | null>(null);
  const [targetFcfPayoutOverride, setTargetFcfPayoutOverride] = useState<number | null>(null);

  const coreStock = STOCK_BY_TICKER[activeTicker] ?? null;

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    setLoadingLive(true);
    setLiveError(null);

    fetch(`/api/market/fundamentals/${encodeURIComponent(activeTicker)}`, {
      signal: controller.signal,
    })
      .then(async (resp) => {
        if (!resp.ok) {
          throw new Error(`Fundamentals unavailable for ${activeTicker}`);
        }
        return (await resp.json()) as LiveFundamentalsResponse;
      })
      .then((json) => {
        if (!cancelled) {
          setLiveData(json);
          setLoadingLive(false);
        }
      })
      .catch((err) => {
        if (!cancelled && err.name !== 'AbortError') {
          setLiveData(null);
          setLiveError(err instanceof Error ? err.message : 'Unable to load audited statements');
          setLoadingLive(false);
        }
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activeTicker, refreshNonce]);

  const handleSelectTicker = (ticker: string) => {
    const clean = ticker.trim().toUpperCase();
    if (!clean) return;
    setActiveTicker(clean);
    setFcfGrowthOverride(null);
    setTargetFcfPayoutOverride(null);
  };

  // Resolved identity & merged ratios (live Yahoo primary, coreStock graceful fallback)
  const displayName = liveData?.name || coreStock?.name || activeTicker;
  const displaySector = liveData?.sector || coreStock?.sector || 'Indian Equity';
  const displayIndustry = liveData?.industry || coreStock?.industry || '';

  const mergedRatios = useMemo(() => {
    const r = liveData?.ratios;
    const estPe =
      coreStock && coreStock.dividend.epsInr > 0
        ? Number((coreStock.latestClose / coreStock.dividend.epsInr).toFixed(2))
        : null;
    return {
      marketCapCr: r?.marketCapCr ?? coreStock?.marketCapCr ?? null,
      enterpriseValueCr: r?.enterpriseValueCr ?? null,
      pe: r?.pe ?? estPe,
      forwardPe: r?.forwardPe ?? null,
      evToEbitda: r?.evToEbitda ?? null,
      evToSales: r?.evToSales ?? null,
      pb: r?.pb ?? null,
      ps: r?.ps ?? null,
      roePct: r?.roePct ?? coreStock?.fundamentals.roePct ?? null,
      rocePct: r?.rocePct ?? coreStock?.fundamentals.rocePct ?? null,
      roaPct: r?.roaPct ?? null,
      grossMarginPct: r?.grossMarginPct ?? null,
      ebitdaMarginPct: r?.ebitdaMarginPct ?? null,
      opMarginPct: r?.opMarginPct ?? coreStock?.fundamentals.opMarginPct ?? null,
      netMarginPct: r?.netMarginPct ?? null,
      trailingEps: r?.trailingEps ?? coreStock?.dividend.epsInr ?? null,
      dividendYieldPct: r?.dividendYieldPct ?? coreStock?.dividend.dividendYieldPct ?? null,
      fcfYieldPct: r?.fcfYieldPct ?? null,
      payoutRatioPct:
        r?.payoutRatioPct ??
        (coreStock && coreStock.dividend.epsInr > 0
          ? Number(((coreStock.dividend.annualDpsInr / coreStock.dividend.epsInr) * 100).toFixed(1))
          : null),
      debtToEquity: r?.debtToEquity ?? null,
      currentRatio: r?.currentRatio ?? null,
      quickRatio: r?.quickRatio ?? null,
      bookValuePerShare: r?.bookValuePerShare ?? null,
      beta: r?.beta ?? coreStock?.beta ?? null,
    };
  }, [liveData, coreStock]);

  // Active statement rows (with fallback for Quarterly Income if core stock is offline)
  const incomeRows: IncomeStatementRow[] = useMemo(() => {
    const liveRows = liveData?.statements?.income?.[periodMode] ?? [];
    if (liveRows.length > 0) return liveRows;
    if (periodMode === 'quarterly' && coreStock) {
      return coreStock.fundamentals.quarterlyHistory.map((q) => {
        const ebitCr = Number(((q.revenueCr * q.opmPct) / 100).toFixed(1));
        return {
          date: q.quarter,
          salesCr: q.revenueCr,
          costOfRevCr: null,
          grossProfitCr: null,
          operatingExpenseCr: null,
          ebitdaCr: ebitCr,
          ebitdaMarginPct: q.opmPct,
          depreciationCr: null,
          ebitCr,
          opMarginPct: q.opmPct,
          interestExpenseCr: null,
          pretaxIncomeCr: null,
          taxCr: null,
          netProfitCr: null,
          netMarginPct: null,
          dilutedEps: q.epsInr,
        };
      });
    }
    return [];
  }, [liveData, periodMode, coreStock]);

  const balanceSheetRows: BalanceSheetRow[] = useMemo(
    () => liveData?.statements?.balanceSheet?.[periodMode] ?? [],
    [liveData, periodMode]
  );

  const cashFlowRows: CashFlowRow[] = useMemo(
    () => liveData?.statements?.cashFlow?.[periodMode] ?? [],
    [liveData, periodMode]
  );

  // Derived institutional quality ratios from audited annual statements
  const auditedQuality = useMemo(() => {
    const annInc = liveData?.statements?.income?.annual ?? [];
    const annBs = liveData?.statements?.balanceSheet?.annual ?? [];
    const annCf = liveData?.statements?.cashFlow?.annual ?? [];
    const latestInc = annInc[annInc.length - 1];
    const latestBs = annBs[annBs.length - 1];
    const latestCf = annCf[annCf.length - 1];

    const interestCoverage =
      latestInc?.ebitCr !== null &&
      latestInc?.ebitCr !== undefined &&
      latestInc?.interestExpenseCr !== null &&
      latestInc?.interestExpenseCr !== undefined &&
      Math.abs(latestInc.interestExpenseCr) > 0.1
        ? Number((latestInc.ebitCr / Math.abs(latestInc.interestExpenseCr)).toFixed(1))
        : null;

    const assetTurnover =
      latestInc?.salesCr && latestBs?.totalAssetsCr && latestBs.totalAssetsCr > 0
        ? Number((latestInc.salesCr / latestBs.totalAssetsCr).toFixed(2))
        : null;

    const netDebtToEbitda =
      latestBs?.netDebtCr !== null &&
      latestBs?.netDebtCr !== undefined &&
      latestInc?.ebitdaCr &&
      latestInc.ebitdaCr > 0
        ? Number((latestBs.netDebtCr / latestInc.ebitdaCr).toFixed(2))
        : coreStock?.dividend.netDebtToEbitda ?? null;

    const cfoToPat = latestCf?.cfoToPatPct ?? null;

    return {
      interestCoverage,
      assetTurnover,
      netDebtToEbitda,
      cfoToPat,
      latestAnnualDate: latestInc?.date ?? latestBs?.date ?? null,
    };
  }, [liveData, coreStock]);

  // Statement trend chart data
  const statementChartData = useMemo<Record<string, string | number | null>[]>(() => {
    if (statementKind === 'income') {
      return incomeRows.map((r) => ({
        period: formatPeriodHeader(r.date, periodMode),
        salesCr: r.salesCr ?? 0,
        ebitdaCr: r.ebitdaCr ?? 0,
        netProfitCr: r.netProfitCr ?? 0,
        marginPct: r.ebitdaMarginPct ?? r.opMarginPct ?? null,
      }));
    }
    if (statementKind === 'balanceSheet') {
      return balanceSheetRows.map((r) => ({
        period: formatPeriodHeader(r.date, periodMode),
        totalAssetsCr: r.totalAssetsCr ?? 0,
        equityCr: r.shareholdersEquityCr ?? 0,
        totalDebtCr: r.totalDebtCr ?? 0,
        cashCr: r.cashAndInvCr ?? 0,
      }));
    }
    return cashFlowRows.map((r) => ({
      period: formatPeriodHeader(r.date, periodMode),
      cfoCr: r.operatingCfCr ?? 0,
      fcfCr: r.freeCfCr ?? 0,
      capexCr: r.capexCr !== null ? Math.abs(r.capexCr) : 0,
      cfoToPatPct: r.cfoToPatPct,
    }));
  }, [statementKind, periodMode, incomeRows, balanceSheetRows, cashFlowRows]);

  // Export CSV for active audited statement
  const handleExportCsv = () => {
    let headers: string[] = [];
    let csvRows: string[][] = [];

    if (statementKind === 'income' && incomeRows.length > 0) {
      headers = ['Line Item (INR Crores)', ...incomeRows.map((r) => formatPeriodHeader(r.date, periodMode))];
      csvRows = INCOME_SPECS.filter((spec) => incomeRows.some((r) => spec.accessor(r) !== null)).map((spec) => [
        spec.label,
        ...incomeRows.map((r) => {
          const v = spec.accessor(r);
          return v === null ? '' : String(v);
        }),
      ]);
    } else if (statementKind === 'balanceSheet' && balanceSheetRows.length > 0) {
      headers = ['Line Item (INR Crores)', ...balanceSheetRows.map((r) => formatPeriodHeader(r.date, periodMode))];
      csvRows = BALANCE_SHEET_SPECS.filter((spec) => balanceSheetRows.some((r) => spec.accessor(r) !== null)).map(
        (spec) => [
          spec.label,
          ...balanceSheetRows.map((r) => {
            const v = spec.accessor(r);
            return v === null ? '' : String(v);
          }),
        ]
      );
    } else if (statementKind === 'cashFlow' && cashFlowRows.length > 0) {
      headers = ['Line Item (INR Crores)', ...cashFlowRows.map((r) => formatPeriodHeader(r.date, periodMode))];
      csvRows = CASH_FLOW_SPECS.filter((spec) => cashFlowRows.some((r) => spec.accessor(r) !== null)).map((spec) => [
        spec.label,
        ...cashFlowRows.map((r) => {
          const v = spec.accessor(r);
          return v === null ? '' : String(v);
        }),
      ]);
    }

    if (headers.length === 0) return;
    const csv = [headers, ...csvRows]
      .map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeTicker}_${statementKind}_${periodMode}_INR_Cr.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Tab 2 Screener rows
  const sectors = useMemo(
    () => ['All', ...Array.from(new Set(INDIAN_STOCKS.map((s) => s.sector))).sort()],
    []
  );

  const screenerRows = useMemo(() => {
    const q = screenerSearch.trim().toLowerCase();
    return sortedByCap.filter((s) => {
      if (screenerSector !== 'All' && s.sector !== screenerSector) return false;
      if (q && !s.ticker.toLowerCase().includes(q) && !s.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [sortedByCap, screenerSearch, screenerSector]);

  // Tab 3 Dividend & FCF Sustainability computations (uses coreStock or fallback to top dividend stock)
  const divStock = coreStock ?? dividendStocks[0];
  const currentFcfPayoutPct =
    divStock.dividend.fcfPerShareInr > 0
      ? Number(((divStock.dividend.annualDpsInr / divStock.dividend.fcfPerShareInr) * 100).toFixed(1))
      : 0;
  const currentEpsPayoutPct =
    divStock.dividend.epsInr > 0
      ? Number(((divStock.dividend.annualDpsInr / divStock.dividend.epsInr) * 100).toFixed(1))
      : 0;
  const fcfCoverageRatio =
    divStock.dividend.annualDpsInr > 0
      ? Number((divStock.dividend.fcfPerShareInr / divStock.dividend.annualDpsInr).toFixed(2))
      : 0;

  const activeFcfGrowth = fcfGrowthOverride ?? divStock.dividend.fcf5YCagrPct;
  const activeTargetPayout =
    targetFcfPayoutOverride ?? Math.min(85, Math.max(15, currentFcfPayoutPct || 40));

  const projectionData = useMemo(() => {
    const hist = divStock.dividend.historicalDps.map((h) => ({
      year: h.year,
      dps: h.dps,
      fcfPerShare: h.fcfPerShare,
      yieldOnCostPct: Number(((h.dps / divStock.latestClose) * 100).toFixed(2)),
      payoutRatioPct: h.fcfPerShare > 0 ? Number(((h.dps / h.fcfPerShare) * 100).toFixed(1)) : 0,
      isProjected: false,
    }));

    const proj = [];
    let fcf = divStock.dividend.fcfPerShareInr;
    const g = activeFcfGrowth / 100;
    const fyLabels = ['FY27E', 'FY28E', 'FY29E', 'FY30E', 'FY31E'];

    for (let i = 0; i < fyLabels.length; i++) {
      fcf = Number((fcf * (1 + g)).toFixed(2));
      const dps =
        divStock.dividend.annualDpsInr > 0
          ? Number(Math.max(0, (fcf * activeTargetPayout) / 100).toFixed(2))
          : 0;
      const yieldOnCostPct = Number(((dps / divStock.latestClose) * 100).toFixed(2));
      const payoutRatioPct = fcf > 0 ? Number(((dps / fcf) * 100).toFixed(1)) : 0;
      proj.push({
        year: fyLabels[i],
        dps,
        fcfPerShare: fcf,
        yieldOnCostPct,
        payoutRatioPct,
        isProjected: true,
      });
    }
    return [...hist, ...proj];
  }, [divStock, activeFcfGrowth, activeTargetPayout]);

  const fy31 = projectionData[projectionData.length - 1];

  const sustainabilityStatus = useMemo(() => {
    if (divStock.dividend.annualDpsInr <= 0) {
      return {
        label: 'Reinvesting Growth (No Dividend)',
        tone: 'text-slate-600 dark:text-slate-400',
        note: 'Retains 100% of free cash flow for capital expenditure and expansion.',
      };
    }
    if (activeTargetPayout <= 65 && divStock.dividend.netDebtToEbitda <= 2.0 && activeFcfGrowth >= 6) {
      return {
        label: 'Safe & Sustainable Coverage',
        tone: 'text-emerald-600 dark:text-emerald-400',
        note: 'Free cash flow comfortably covers projected payouts with conservative leverage.',
      };
    }
    if (activeTargetPayout <= 85 && activeFcfGrowth >= 0) {
      return {
        label: 'Moderate Coverage — Watch FCF',
        tone: 'text-amber-600 dark:text-amber-400',
        note: 'Payout absorbs a large share of free cash flow; earnings cyclicality may constrain raises.',
      };
    }
    return {
      label: 'Stretched Payout — Cut Risk',
      tone: 'text-red-600 dark:text-red-400',
      note: 'Projected dividends approach or exceed free cash flow generation.',
    };
  }, [divStock, activeTargetPayout, activeFcfGrowth]);

  // Generic statement table renderer
  const renderStatementTable = <T extends { date: string }>(
    rows: T[],
    specs: StatementRowSpec<T>[]
  ) => {
    const visibleSpecs = specs.filter((spec) => rows.some((r) => spec.accessor(r) !== null));
    if (rows.length === 0 || visibleSpecs.length === 0) {
      return (
        <div className="p-10 text-center space-y-2.5 text-xs text-slate-500">
          <div>
            {loadingLive
              ? `Fetching live ${periodMode === 'annual' ? 'Annual (FY)' : 'Quarterly'} audited filings for ${activeTicker}…`
              : periodMode === 'quarterly' && statementKind === 'cashFlow'
              ? `Indian listed companies report audited Cash Flow Statements on an Annual / Half-Yearly basis under SEBI LODR norms; quarterly Cash Flow is not filed separately for ${activeTicker}.`
              : `No ${periodMode === 'annual' ? 'Annual' : 'Quarterly'} ${
                  statementKind === 'income'
                    ? 'Income Statement'
                    : statementKind === 'balanceSheet'
                    ? 'Balance Sheet'
                    : 'Cash Flow'
                } filings returned for ${activeTicker}.`}
          </div>
          {!loadingLive && periodMode === 'quarterly' && (
            <button
              onClick={() => setPeriodMode('annual')}
              className="inline-flex items-center px-3 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700"
            >
              Switch to Annual (FY)
            </button>
          )}
        </div>
      );
    }

    const deltaLabel = periodMode === 'annual' ? 'Latest YoY Δ' : 'Latest QoQ Δ';

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
            <tr>
              <th className="py-2.5 px-4 font-semibold min-w-[240px] sticky left-0 bg-slate-50 dark:bg-slate-900 z-10">
                Audited Line Item (₹ Crores)
              </th>
              {rows.map((r) => (
                <th
                  key={r.date}
                  className="py-2.5 px-3 text-right font-mono font-semibold whitespace-nowrap"
                >
                  {formatPeriodHeader(r.date, periodMode)}
                </th>
              ))}
              <th className="py-2.5 px-4 text-right font-semibold whitespace-nowrap">
                {deltaLabel}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
            {visibleSpecs.map((spec) => {
              const latestVal = rows.length >= 1 ? spec.accessor(rows[rows.length - 1]) : null;
              const prevVal = rows.length >= 2 ? spec.accessor(rows[rows.length - 2]) : null;
              const isTotal = spec.emphasis === 'total';
              const isSubtotal = spec.emphasis === 'subtotal';
              const isRatio = spec.emphasis === 'ratio';

              return (
                <tr
                  key={spec.label}
                  className={
                    isTotal
                      ? 'bg-slate-50/90 dark:bg-slate-800/40 font-semibold'
                      : isRatio
                      ? 'text-slate-500 dark:text-slate-400 italic'
                      : 'hover:bg-slate-50/60 dark:hover:bg-slate-800/25'
                  }
                >
                  <td
                    className={`py-2.5 px-4 sticky left-0 z-10 ${
                      isTotal
                        ? 'bg-slate-50 dark:bg-slate-900 text-slate-900 dark:text-slate-100 font-semibold'
                        : isSubtotal
                        ? 'bg-white dark:bg-[#111827] text-slate-800 dark:text-slate-200 font-medium'
                        : isRatio
                        ? 'bg-white dark:bg-[#111827] pl-7 text-slate-500 dark:text-slate-400'
                        : 'bg-white dark:bg-[#111827] pl-6 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    {spec.label}
                  </td>
                  {rows.map((r) => {
                    const v = spec.accessor(r);
                    return (
                      <td
                        key={`${spec.label}-${r.date}`}
                        className={`py-2.5 px-3 text-right font-mono tabular-nums whitespace-nowrap ${
                          isTotal
                            ? 'text-slate-900 dark:text-slate-100 font-semibold'
                            : v !== null && v < 0
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-slate-700 dark:text-slate-300'
                        }`}
                      >
                        {formatMetricCell(v, spec.kind)}
                      </td>
                    );
                  })}
                  <td
                    className={`py-2.5 px-4 text-right font-mono tabular-nums whitespace-nowrap font-medium ${deltaTone(
                      latestVal,
                      prevVal
                    )}`}
                  >
                    {computeDelta(latestVal, prevVal, spec.kind)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & Equity Selector */}
      <div className="flex flex-col xl:flex-row xl:items-end justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
            Fundamental Lab — Audited Financials, Multiples & FCF
          </h1>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
            Audited Profit & Loss, Balance Sheet, and Cash Flow Statements (₹ Crores) across Annual (FY) and Quarterly filings, trailing multiples, profitability ratios, and FCF dividend durability.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-xs">
          <IndianTickerSearchInput
            currentTicker={activeTicker}
            onSelectTicker={(t) => handleSelectTicker(t)}
            placeholder="Search any of 2,000+ NSE / BSE stocks..."
            className="w-72"
          />

          <button
            onClick={() => setRefreshNonce((n) => n + 1)}
            disabled={loadingLive}
            title="Refresh live filings"
            className="p-2 rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-slate-600 dark:text-slate-300 ${loadingLive ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={() => onInspectStock(activeTicker)}
            className="inline-flex items-center gap-1 px-3 py-2 text-xs font-semibold rounded-lg bg-blue-600 text-white hover:bg-blue-700 whitespace-nowrap"
          >
            <span>Open Ticker Page</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Active Company Identity Bar */}
      <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl px-5 py-3.5 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="text-lg font-bold font-mono text-slate-900 dark:text-slate-100">
            {activeTicker}
          </span>
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            {displayName}
          </span>
          <span className="text-xs text-slate-500">
            {displaySector}
            {displayIndustry ? ` · ${displayIndustry}` : ''}
          </span>
        </div>

        <div className="flex items-center gap-5 text-xs">
          {coreStock && (
            <div className="flex items-baseline gap-2">
              <span className="text-slate-500">LTP</span>
              <span className="text-sm font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100">
                {formatINR(coreStock.latestClose)}
              </span>
              <span
                className={`font-mono font-semibold tabular-nums ${
                  coreStock.dailyChangePct >= 0
                    ? 'text-emerald-600 dark:text-emerald-400'
                    : 'text-red-600 dark:text-red-400'
                }`}
              >
                {formatPct(coreStock.dailyChangePct)}
              </span>
            </div>
          )}
          <div className="flex items-baseline gap-1.5">
            <span className="text-slate-500">Market Cap</span>
            <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
              {mergedRatios.marketCapCr ? formatCr(mergedRatios.marketCapCr) : '—'}
            </span>
          </div>
          {liveData?.yahooSymbol && (
            <span className="font-mono text-[11px] text-slate-500 hidden sm:inline">
              {liveData.yahooSymbol}
            </span>
          )}
        </div>
      </div>

      {liveError && (
        <div className="border border-amber-300 dark:border-amber-800/70 bg-amber-50/70 dark:bg-amber-950/30 rounded-xl px-4 py-2.5 text-xs text-amber-800 dark:text-amber-300 flex items-center justify-between gap-2">
          <span>
            {liveError}. {coreStock ? 'Showing cached NSE institutional metrics where available.' : 'Verify the NSE/BSE symbol and retry.'}
          </span>
          <button
            onClick={() => setRefreshNonce((n) => n + 1)}
            className="font-semibold underline whitespace-nowrap"
          >
            Retry
          </button>
        </div>
      )}

      {/* Always-Visible Key Multiples & Ratios Overview (3 Grouped Institutional Cards — Zero DCF/Targets) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Card 1: Market Multiples */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 pb-2.5 mb-3 border-b border-slate-200 dark:border-slate-800">
            Key Market Multiples
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Market Cap</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {mergedRatios.marketCapCr ? formatCr(mergedRatios.marketCapCr) : '—'}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Enterprise Val</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {mergedRatios.enterpriseValueCr ? formatCr(mergedRatios.enterpriseValueCr) : '—'}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Trailing P/E</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.pe)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Forward P/E</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.forwardPe)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">EV / EBITDA</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.evToEbitda)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">EV / Sales</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.evToSales)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Price / Book</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.pb)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Price / Sales</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.ps)}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Profitability & Return Ratios */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 pb-2.5 mb-3 border-b border-slate-200 dark:border-slate-800">
            Profitability & Return Ratios
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">ROE</span>
              <span className="font-mono font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                {formatRatio(mergedRatios.roePct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">ROCE</span>
              <span className="font-mono font-semibold tabular-nums text-emerald-600 dark:text-emerald-400">
                {formatRatio(mergedRatios.rocePct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">ROA</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.roaPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Gross Margin</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.grossMarginPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">EBITDA Margin</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.ebitdaMarginPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Operating Margin</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.opMarginPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Net Margin</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.netMarginPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Trailing EPS</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {mergedRatios.trailingEps !== null ? formatINR(mergedRatios.trailingEps) : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Solvency, Yield & Per-Share Quality */}
        <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
          <div className="text-xs font-semibold text-slate-900 dark:text-slate-100 pb-2.5 mb-3 border-b border-slate-200 dark:border-slate-800">
            Solvency, Yield & Per-Share Metrics
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Dividend Yield</span>
              <span className="font-mono font-semibold tabular-nums text-blue-600 dark:text-blue-400">
                {formatRatio(mergedRatios.dividendYieldPct, '%', 2)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">FCF Yield</span>
              <span className="font-mono font-semibold tabular-nums text-blue-600 dark:text-blue-400">
                {formatRatio(mergedRatios.fcfYieldPct, '%', 2)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Payout Ratio</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.payoutRatioPct, '%', 1)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Debt / Equity</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatDebtToEquity(mergedRatios.debtToEquity)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Current Ratio</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.currentRatio)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Quick Ratio</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.quickRatio)}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Book Value / Sh</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {mergedRatios.bookValuePerShare !== null ? formatINR(mergedRatios.bookValuePerShare) : '—'}
              </span>
            </div>
            <div className="flex justify-between gap-2">
              <span className="text-slate-500">Beta (vs NSE)</span>
              <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                {formatRatio(mergedRatios.beta, '', 2)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Workspace Sub-Navigation Tabs */}
      <div className="flex flex-wrap items-center gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
        <button
          onClick={() => setActiveTab('statements')}
          className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
            activeTab === 'statements'
              ? 'bg-blue-600 text-white'
              : 'border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60'
          }`}
        >
          <FileSpreadsheet className="w-3.5 h-3.5" />
          <span>Audited Financial Statements (₹ Crores)</span>
        </button>
        <button
          onClick={() => setActiveTab('ratios')}
          className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
            activeTab === 'ratios'
              ? 'bg-blue-600 text-white'
              : 'border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60'
          }`}
        >
          <BarChart3 className="w-3.5 h-3.5" />
          <span>Key Multiples, Growth & Peer Matrix</span>
        </button>
        <button
          onClick={() => setActiveTab('dividend')}
          className={`inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
            activeTab === 'dividend'
              ? 'bg-blue-600 text-white'
              : 'border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60'
          }`}
        >
          <Coins className="w-3.5 h-3.5" />
          <span>Dividend & FCF Sustainability</span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* TAB 1: AUDITED FINANCIAL STATEMENTS (₹ CRORES)                        */}
      {/* ===================================================================== */}
      {activeTab === 'statements' && (
        <div className="space-y-6">
          {/* Controls Bar: Statement Type + Annual / Quarterly Switch + Export */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4 flex flex-wrap items-center justify-between gap-4">
            {/* Statement Selector */}
            <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
              {(
                [
                  { id: 'income', label: 'Profit & Loss' },
                  { id: 'balanceSheet', label: 'Balance Sheet' },
                  { id: 'cashFlow', label: 'Cash Flow' },
                ] as { id: StatementKind; label: string }[]
              ).map((item) => (
                <button
                  key={item.id}
                  onClick={() => setStatementKind(item.id)}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                    statementKind === item.id
                      ? 'bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>

            {/* Annual vs Quarterly Toggle + Export */}
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-900 p-1 rounded-lg">
                <button
                  onClick={() => setPeriodMode('annual')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                    periodMode === 'annual'
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  Annual (FY)
                </button>
                <button
                  onClick={() => setPeriodMode('quarterly')}
                  className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors whitespace-nowrap ${
                    periodMode === 'quarterly'
                      ? 'bg-blue-600 text-white'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  Quarterly (Q)
                </button>
              </div>

              <button
                onClick={handleExportCsv}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 hover:bg-slate-50 dark:hover:bg-slate-800 whitespace-nowrap"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export CSV</span>
              </button>
            </div>
          </div>

          {/* Visual Trend Chart for Selected Statement & Period */}
          {statementChartData.length > 0 && (
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {activeTicker} —{' '}
                    {statementKind === 'income'
                      ? 'Revenue, EBITDA & Net Profit Trend'
                      : statementKind === 'balanceSheet'
                      ? 'Total Assets, Net Worth & Borrowings Trend'
                      : 'Operating Cash Flow, Free Cash Flow & CapEx Trend'}{' '}
                    ({periodMode === 'annual' ? 'Annual FY' : 'Quarterly'}, ₹ Crores)
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {statementKind === 'income'
                      ? 'Bars in ₹ Crores (left axis) · EBITDA / Operating Margin % (right axis)'
                      : statementKind === 'balanceSheet'
                      ? 'Balance sheet structure across audited reporting dates (₹ Crores)'
                      : 'Cash generation vs capital outlay (₹ Crores) · CFO / PAT Conversion % (right axis)'}
                  </p>
                </div>
                {loadingLive && (
                  <span className="text-xs text-slate-500 font-mono">Syncing audited filings…</span>
                )}
              </div>

              <div style={{ width: '100%', height: 260 }}>
                <ResponsiveContainer>
                  <ComposedChart
                    data={statementChartData}
                    margin={{ top: 10, right: 16, left: 6, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" vertical={false} />
                    <XAxis
                      dataKey="period"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      yAxisId="cr"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) =>
                        Math.abs(Number(v)) >= 1000
                          ? `₹${(Number(v) / 1000).toFixed(0)}k`
                          : `₹${v}`
                      }
                      width={62}
                    />
                    {(statementKind === 'income' || statementKind === 'cashFlow') && (
                      <YAxis
                        yAxisId="pct"
                        orientation="right"
                        tick={{ fontSize: 11, fill: '#64748b' }}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(v) => `${v}%`}
                        width={46}
                      />
                    )}
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: '#f8fafc',
                      }}
                      formatter={(v: unknown, name: string | number | undefined) => {
                        const num = Number(v);
                        const label = String(name ?? '');
                        if (label.includes('%')) return [`${num.toFixed(1)}%`, label];
                        return [`₹${formatCrCell(num)} Cr`, label];
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: '11px' }} />

                    {statementKind === 'income' && (
                      <>
                        <Bar
                          yAxisId="cr"
                          dataKey="salesCr"
                          name="Sales (₹ Cr)"
                          fill="rgba(59,130,246,0.55)"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="ebitdaCr"
                          name="EBITDA (₹ Cr)"
                          fill="#10b981"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="netProfitCr"
                          name="Net Profit (₹ Cr)"
                          fill="#6366f1"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="pct"
                          type="monotone"
                          dataKey="marginPct"
                          name="EBITDA Margin %"
                          stroke="#f59e0b"
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          connectNulls
                          isAnimationActive={false}
                        />
                      </>
                    )}

                    {statementKind === 'balanceSheet' && (
                      <>
                        <Bar
                          yAxisId="cr"
                          dataKey="totalAssetsCr"
                          name="Total Assets (₹ Cr)"
                          fill="rgba(59,130,246,0.5)"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="equityCr"
                          name="Net Worth (₹ Cr)"
                          fill="#10b981"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="totalDebtCr"
                          name="Total Debt (₹ Cr)"
                          fill="#ef4444"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="cr"
                          type="monotone"
                          dataKey="cashCr"
                          name="Cash & Inv (₹ Cr)"
                          stroke="#f59e0b"
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          isAnimationActive={false}
                        />
                      </>
                    )}

                    {statementKind === 'cashFlow' && (
                      <>
                        <Bar
                          yAxisId="cr"
                          dataKey="cfoCr"
                          name="Operating CF (₹ Cr)"
                          fill="rgba(59,130,246,0.65)"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="fcfCr"
                          name="Free Cash Flow (₹ Cr)"
                          fill="#10b981"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Bar
                          yAxisId="cr"
                          dataKey="capexCr"
                          name="CapEx Outlay (₹ Cr)"
                          fill="#f97316"
                          radius={[4, 4, 0, 0]}
                          isAnimationActive={false}
                        />
                        <Line
                          yAxisId="pct"
                          type="monotone"
                          dataKey="cfoToPatPct"
                          name="CFO / PAT %"
                          stroke="#eab308"
                          strokeWidth={2}
                          dot={{ r: 3 }}
                          connectNulls
                          isAnimationActive={false}
                        />
                      </>
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Audited Financial Statement Table Card */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {activeTicker} — Audited{' '}
                  {statementKind === 'income'
                    ? 'Profit & Loss Statement'
                    : statementKind === 'balanceSheet'
                    ? 'Balance Sheet'
                    : 'Cash Flow Statement'}{' '}
                  ({periodMode === 'annual' ? 'Annual FY' : 'Quarterly'})
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Consolidated figures in ₹ Crores (except Diluted EPS in ₹ and margin ratios in %)
                </p>
              </div>
              <span className="text-xs font-mono text-slate-500">
                {statementKind === 'income'
                  ? `${incomeRows.length} periods`
                  : statementKind === 'balanceSheet'
                  ? `${balanceSheetRows.length} periods`
                  : `${cashFlowRows.length} periods`}
              </span>
            </div>

            {statementKind === 'income' && renderStatementTable(incomeRows, INCOME_SPECS)}
            {statementKind === 'balanceSheet' &&
              renderStatementTable(balanceSheetRows, BALANCE_SHEET_SPECS)}
            {statementKind === 'cashFlow' && renderStatementTable(cashFlowRows, CASH_FLOW_SPECS)}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 2: KEY MULTIPLES, GROWTH & NSE PEER MATRIX                        */}
      {/* ===================================================================== */}
      {activeTab === 'ratios' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
            {/* YoY & QoQ Earnings / Sales Growth Table */}
            <div className="xl:col-span-7 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
              <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  {activeTicker} — YoY & QoQ Fundamental Growth Momentum
                </h2>
                <span className="text-xs text-slate-500">Sales · EBITDA · PAT · EPS</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                    <tr>
                      <th className="py-2.5 px-4">Metric</th>
                      <th className="py-2.5 px-3 text-right">Latest Reported</th>
                      <th className="py-2.5 px-3 text-right">YoY Growth %</th>
                      <th className="py-2.5 px-3 text-right">QoQ Growth %</th>
                      <th className="py-2.5 px-4 text-right">Basis</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                    {[
                      {
                        label: 'Revenue (Sales)',
                        metric: liveData?.growth?.sales,
                        fallbackYoY: coreStock?.fundamentals.qtrRevYoY ?? null,
                        isEps: false,
                      },
                      {
                        label: 'EBITDA',
                        metric: liveData?.growth?.ebitda,
                        fallbackYoY: null,
                        isEps: false,
                      },
                      {
                        label: 'Net Profit (PAT)',
                        metric: liveData?.growth?.netProfit,
                        fallbackYoY: coreStock?.fundamentals.qtrEpsYoY ?? null,
                        isEps: false,
                      },
                      {
                        label: 'Diluted EPS',
                        metric: liveData?.growth?.eps,
                        fallbackYoY: coreStock?.fundamentals.qtrEpsYoY ?? null,
                        isEps: true,
                      },
                    ].map((item) => {
                      const yoy = item.metric?.yoyPct ?? item.fallbackYoY;
                      const qoq = item.metric?.qoqPct ?? null;
                      const latestVal = item.metric?.latestValue ?? null;
                      return (
                        <tr key={item.label} className="hover:bg-slate-50 dark:hover:bg-slate-800/30">
                          <td className="py-2.5 px-4 font-medium text-slate-900 dark:text-slate-100">
                            {item.label}
                          </td>
                          <td className="py-2.5 px-3 text-right font-mono tabular-nums text-slate-700 dark:text-slate-300">
                            {latestVal !== null
                              ? item.isEps
                                ? formatINR(latestVal)
                                : `₹${formatCrCell(latestVal)} Cr`
                              : '—'}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono tabular-nums font-semibold ${
                              yoy === null
                                ? 'text-slate-400'
                                : yoy >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {yoy !== null ? formatPct(yoy) : '—'}
                          </td>
                          <td
                            className={`py-2.5 px-3 text-right font-mono tabular-nums font-semibold ${
                              qoq === null
                                ? 'text-slate-400'
                                : qoq >= 0
                                ? 'text-emerald-600 dark:text-emerald-400'
                                : 'text-red-600 dark:text-red-400'
                            }`}
                          >
                            {qoq !== null ? formatPct(qoq) : '—'}
                          </td>
                          <td className="py-2.5 px-4 text-right font-mono text-[11px] text-slate-500">
                            {item.metric?.yoyBasis || (coreStock ? 'NSE Filing' : '—')}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Balance Sheet Quality & Institutional Ownership */}
            <div className="xl:col-span-5 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-2.5">
                <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  Capital Efficiency & Ownership Quality
                </h2>
                {auditedQuality.latestAnnualDate && (
                  <span className="text-[11px] font-mono text-slate-500">
                    {formatPeriodHeader(auditedQuality.latestAnnualDate, 'annual')} Audited
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <div className="text-slate-500">Interest Coverage (EBIT/Int)</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {formatRatio(auditedQuality.interestCoverage, '×', 1)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Net Debt / EBITDA</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {formatRatio(auditedQuality.netDebtToEbitda, '×', 2)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Asset Turnover</div>
                  <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                    {formatRatio(auditedQuality.assetTurnover, '×', 2)}
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">Cash Conversion (CFO/PAT)</div>
                  <div className="font-mono font-semibold tabular-nums text-emerald-600 dark:text-emerald-400 mt-0.5">
                    {formatRatio(auditedQuality.cfoToPat, '%', 1)}
                  </div>
                </div>

                {coreStock && (
                  <>
                    <div>
                      <div className="text-slate-500">Promoter Stake / Pledge</div>
                      <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                        {coreStock.fundamentals.promoterHoldingPct}% / {coreStock.fundamentals.promoterPledgePct}%
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">FII Stake (QoQ Δ)</div>
                      <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                        {coreStock.fundamentals.fiiHoldingPct}% ({formatPct(coreStock.fundamentals.fiiQoQChangePct)})
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">DII / Mutual Fund Stake</div>
                      <div className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100 mt-0.5">
                        {coreStock.fundamentals.diiHoldingPct}% / {coreStock.fundamentals.mfHoldingPct}%
                      </div>
                    </div>
                    <div>
                      <div className="text-slate-500">3Y Annual EPS CAGR</div>
                      <div className="font-mono font-semibold tabular-nums text-blue-600 dark:text-blue-400 mt-0.5">
                        {formatPct(coreStock.fundamentals.annualEps3YCagr)}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* NSE Universe Multiples & Quality Matrix */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  NSE Universe — Key Multiples, Return Ratios & Growth Matrix
                </h3>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Click any row to load its audited statements in Fundamental Lab · Click ticker to open full chart page
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <input
                  type="text"
                  value={screenerSearch}
                  onChange={(e) => setScreenerSearch(e.target.value)}
                  placeholder="Filter ticker or company..."
                  className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                />
                <select
                  value={screenerSector}
                  onChange={(e) => setScreenerSector(e.target.value)}
                  className="px-3 py-1.5 text-xs rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-950"
                >
                  {sectors.map((sec) => (
                    <option key={sec} value={sec}>
                      {sec === 'All' ? 'All Sectors' : sec}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-4">Ticker / Company</th>
                    <th className="py-2.5 px-3">Sector</th>
                    <th className="py-2.5 px-3 text-right">LTP (₹)</th>
                    <th className="py-2.5 px-3 text-right">MCap (₹ Cr)</th>
                    <th className="py-2.5 px-3 text-right">P/E</th>
                    <th className="py-2.5 px-3 text-right">ROE %</th>
                    <th className="py-2.5 px-3 text-right">ROCE %</th>
                    <th className="py-2.5 px-3 text-right">OPM %</th>
                    <th className="py-2.5 px-3 text-right">Rev YoY</th>
                    <th className="py-2.5 px-3 text-right">EPS YoY</th>
                    <th className="py-2.5 px-3 text-right">Div Yield</th>
                    <th className="py-2.5 px-4 text-right">Net Debt/EBITDA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {screenerRows.map((s) => {
                    const pe =
                      s.dividend.epsInr > 0 ? s.latestClose / s.dividend.epsInr : null;
                    const isSel = s.ticker === activeTicker;
                    return (
                      <tr
                        key={s.ticker}
                        onClick={() => handleSelectTicker(s.ticker)}
                        className={`cursor-pointer transition-colors ${
                          isSel
                            ? 'bg-blue-600/10 dark:bg-blue-500/15'
                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="py-2.5 px-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onInspectStock(s.ticker);
                            }}
                            className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 hover:underline text-left block"
                          >
                            {s.ticker}
                          </button>
                          <div className="text-[11px] text-slate-500 truncate max-w-[170px]">
                            {s.name}
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-slate-600 dark:text-slate-400 whitespace-nowrap">
                          {s.sector}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {formatINR(s.latestClose)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {formatCrCell(s.marketCapCr)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {pe !== null ? `${pe.toFixed(1)}×` : '—'}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-medium text-emerald-600 dark:text-emerald-400">
                          {s.fundamentals.roePct.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {s.fundamentals.rocePct.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {s.fundamentals.opMarginPct.toFixed(1)}%
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono tabular-nums ${
                            s.fundamentals.qtrRevYoY >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(s.fundamentals.qtrRevYoY)}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono tabular-nums ${
                            s.fundamentals.qtrEpsYoY >= 0
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-red-600 dark:text-red-400'
                          }`}
                        >
                          {formatPct(s.fundamentals.qtrEpsYoY)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-blue-600 dark:text-blue-400">
                          {s.dividend.dividendYieldPct.toFixed(2)}%
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono tabular-nums">
                          {s.dividend.netDebtToEbitda.toFixed(2)}×
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* TAB 3: DIVIDEND & FCF SUSTAINABILITY                                  */}
      {/* ===================================================================== */}
      {activeTab === 'dividend' && (
        <div className="space-y-6">
          {!coreStock && (
            <div className="border border-blue-200 dark:border-blue-800/60 bg-blue-50/70 dark:bg-blue-950/30 rounded-xl px-4 py-3 text-xs text-blue-800 dark:text-blue-300 flex flex-wrap items-center justify-between gap-2">
              <span>
                5-year per-share FCF dividend stress-testing uses our core NSE dividend coverage universe. Displaying{' '}
                <strong className="font-mono">{divStock.ticker}</strong> below (live dividend metrics for{' '}
                <strong className="font-mono">{activeTicker}</strong> are shown in the ratio cards above).
              </span>
              <button
                onClick={() => handleSelectTicker(divStock.ticker)}
                className="font-semibold underline whitespace-nowrap"
              >
                Switch active ticker to {divStock.ticker}
              </button>
            </div>
          )}

          {/* Selected Stock Dividend KPI Strip */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
              <div className="text-xs text-slate-500">Trailing Yield / DPS</div>
              <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
                {divStock.dividend.dividendYieldPct.toFixed(2)}%
              </div>
              <div className="text-xs font-mono text-slate-500 mt-0.5">
                {formatINR(divStock.dividend.annualDpsInr)} / share
              </div>
            </div>
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
              <div className="text-xs text-slate-500">FY31E Yield-on-Cost</div>
              <div className="text-xl font-bold font-mono tabular-nums text-emerald-600 dark:text-emerald-400 mt-1">
                {fy31.yieldOnCostPct.toFixed(2)}%
              </div>
              <div className="text-xs font-mono text-slate-500 mt-0.5">
                Proj. DPS {formatINR(fy31.dps)}
              </div>
            </div>
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
              <div className="text-xs text-slate-500">FCF Payout / Coverage</div>
              <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
                {currentFcfPayoutPct.toFixed(1)}%
              </div>
              <div className="text-xs font-mono text-slate-500 mt-0.5">
                {fcfCoverageRatio > 0 ? `${fcfCoverageRatio.toFixed(2)}× FCF cover` : 'No payout'}
              </div>
            </div>
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
              <div className="text-xs text-slate-500">5Y FCF / DPS CAGR</div>
              <div className="text-xl font-bold font-mono tabular-nums text-blue-600 dark:text-blue-400 mt-1">
                +{divStock.dividend.fcf5YCagrPct.toFixed(1)}%
              </div>
              <div className="text-xs font-mono text-slate-500 mt-0.5">
                DPS CAGR +{divStock.dividend.dps5YCagrPct.toFixed(1)}%
              </div>
            </div>
            <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-4">
              <div className="text-xs text-slate-500">Net Debt / EBITDA</div>
              <div className="text-xl font-bold font-mono tabular-nums text-slate-900 dark:text-slate-100 mt-1">
                {divStock.dividend.netDebtToEbitda.toFixed(2)}×
              </div>
              <div className="text-xs font-mono text-slate-500 mt-0.5">
                {divStock.dividend.consecutiveYearsPaid} yrs paid
              </div>
            </div>
          </div>

          {/* Main Split: FCF vs DPS Projection Chart + Stress-Test Controls */}
          <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
            <div className="xl:col-span-8 border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {divStock.ticker} — Historical & Projected Free Cash Flow vs Dividend per Share (₹)
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    FY22–FY26 Actuals · FY27E–FY31E FCF-Driven Projections
                  </p>
                </div>
                <div className={`inline-flex items-center gap-1.5 text-xs font-semibold ${sustainabilityStatus.tone}`}>
                  {sustainabilityStatus.label.includes('Safe') ? (
                    <ShieldCheck className="w-4 h-4" />
                  ) : sustainabilityStatus.label.includes('Stretched') ? (
                    <AlertTriangle className="w-4 h-4" />
                  ) : (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                  <span>{sustainabilityStatus.label}</span>
                </div>
              </div>

              <div style={{ width: '100%', height: 290 }}>
                <ResponsiveContainer>
                  <ComposedChart data={projectionData} margin={{ top: 10, right: 12, left: 4, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.14)" vertical={false} />
                    <XAxis
                      dataKey="year"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      yAxisId="inr"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₹${v}`}
                      width={56}
                    />
                    <YAxis
                      yAxisId="pct"
                      orientation="right"
                      tick={{ fontSize: 11, fill: '#64748b' }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `${v}%`}
                      width={44}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0f172a',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        fontSize: '12px',
                        color: '#f8fafc',
                      }}
                      formatter={(v: unknown, name: string | number | undefined) => {
                        const num = Number(v);
                        const key = String(name ?? '');
                        if (key === 'fcfPerShare') return [formatINR(num), 'FCF / Share'];
                        if (key === 'dps') return [formatINR(num), 'Dividend / Share'];
                        if (key === 'yieldOnCostPct') return [`${num.toFixed(2)}%`, 'Yield on Cost'];
                        return [String(v), key];
                      }}
                    />
                    <Bar
                      yAxisId="inr"
                      dataKey="fcfPerShare"
                      fill="rgba(59,130,246,0.35)"
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={false}
                    />
                    <Bar
                      yAxisId="inr"
                      dataKey="dps"
                      fill="#10b981"
                      radius={[4, 4, 0, 0]}
                      isAnimationActive={false}
                    />
                    <Line
                      yAxisId="pct"
                      type="monotone"
                      dataKey="yieldOnCostPct"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={{ r: 3 }}
                      isAnimationActive={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {sustainabilityStatus.note}
              </p>
            </div>

            {/* Right: FCF Stress-Test Controls & Quality Profile */}
            <div className="xl:col-span-4 space-y-5">
              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                    <Coins className="w-4 h-4 text-emerald-500" />
                    <span>FCF Payout Stress-Test</span>
                  </div>
                  <button
                    onClick={() => {
                      setFcfGrowthOverride(null);
                      setTargetFcfPayoutOverride(null);
                    }}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Reset to Base
                  </button>
                </div>

                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600 dark:text-slate-400">Projected FCF Annual Growth</span>
                      <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                        {formatPct(activeFcfGrowth)}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={-10}
                      max={30}
                      step={0.5}
                      value={activeFcfGrowth}
                      onChange={(e) => setFcfGrowthOverride(Number(e.target.value))}
                      className="w-full accent-blue-600"
                    />
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-slate-600 dark:text-slate-400">Target FCF Payout Ratio</span>
                      <span className="font-mono font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                        {activeTargetPayout.toFixed(0)}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={10}
                      max={110}
                      step={5}
                      value={activeTargetPayout}
                      onChange={(e) => setTargetFcfPayoutOverride(Number(e.target.value))}
                      className="w-full accent-emerald-600"
                    />
                  </div>
                </div>

                <div className="pt-3 border-t border-slate-200 dark:border-slate-800 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Earnings Payout Ratio (DPS / EPS)</span>
                    <span className="font-mono tabular-nums font-medium">
                      {currentEpsPayoutPct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Trailing FCF / Share</span>
                    <span className="font-mono tabular-nums font-medium">
                      {formatINR(divStock.dividend.fcfPerShareInr)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">FY31E Projected FCF / Share</span>
                    <span className="font-mono tabular-nums font-medium text-blue-600 dark:text-blue-400">
                      {formatINR(fy31.fcfPerShare)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">5-Yr Cumulative Dividends (per sh)</span>
                    <span className="font-mono tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">
                      {formatINR(
                        projectionData.filter((p) => p.isProjected).reduce((s, p) => s + p.dps, 0)
                      )}
                    </span>
                  </div>
                </div>
              </div>

              <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl p-5 space-y-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900 dark:text-slate-100">
                  <TrendingUp className="w-4 h-4 text-blue-500" />
                  <span>Operational & Ownership Quality</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <div className="text-slate-500">Return on Equity (ROE)</div>
                    <div className="font-mono font-semibold tabular-nums">{divStock.fundamentals.roePct}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500">ROCE</div>
                    <div className="font-mono font-semibold tabular-nums">{divStock.fundamentals.rocePct}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Operating Margin</div>
                    <div className="font-mono font-semibold tabular-nums">{divStock.fundamentals.opMarginPct}%</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Promoter Holding / Pledge</div>
                    <div className="font-mono font-semibold tabular-nums">
                      {divStock.fundamentals.promoterHoldingPct}% / {divStock.fundamentals.promoterPledgePct}%
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">FII Stake (QoQ)</div>
                    <div className="font-mono font-semibold tabular-nums">
                      {divStock.fundamentals.fiiHoldingPct}% ({formatPct(divStock.fundamentals.fiiQoQChangePct)})
                    </div>
                  </div>
                  <div>
                    <div className="text-slate-500">DII / MF Stake</div>
                    <div className="font-mono font-semibold tabular-nums">
                      {divStock.fundamentals.diiHoldingPct}% / {divStock.fundamentals.mfHoldingPct}%
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* NSE Dividend Sustainability Universe Table */}
          <div className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#111827] rounded-xl overflow-hidden">
            <div className="px-5 py-3.5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                NSE Dividend & Free Cash Flow Sustainability Leaderboard
              </h3>
              <span className="text-xs text-slate-500">Sorted by trailing dividend yield</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[11px] text-slate-500">
                  <tr>
                    <th className="py-2.5 px-4">Ticker / Company</th>
                    <th className="py-2.5 px-3 text-right">LTP (₹)</th>
                    <th className="py-2.5 px-3 text-right">Yield %</th>
                    <th className="py-2.5 px-3 text-right">Annual DPS</th>
                    <th className="py-2.5 px-3 text-right">FCF / Share</th>
                    <th className="py-2.5 px-3 text-right">FCF Payout %</th>
                    <th className="py-2.5 px-3 text-right">5Y FCF CAGR</th>
                    <th className="py-2.5 px-3 text-right">Net Debt/EBITDA</th>
                    <th className="py-2.5 px-4 text-right">Streak</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200/70 dark:divide-slate-800/70">
                  {dividendStocks.slice(0, 16).map((s) => {
                    const fcfPayout =
                      s.dividend.fcfPerShareInr > 0
                        ? (s.dividend.annualDpsInr / s.dividend.fcfPerShareInr) * 100
                        : 0;
                    const isSel = s.ticker === divStock.ticker;
                    return (
                      <tr
                        key={s.ticker}
                        onClick={() => handleSelectTicker(s.ticker)}
                        className={`cursor-pointer transition-colors ${
                          isSel
                            ? 'bg-blue-600/10 dark:bg-blue-500/15'
                            : 'hover:bg-slate-50 dark:hover:bg-slate-800/40'
                        }`}
                      >
                        <td className="py-2.5 px-4">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectTicker(s.ticker);
                              onInspectStock(s.ticker);
                            }}
                            className="font-mono font-semibold text-slate-900 dark:text-slate-100 hover:text-blue-500 hover:underline text-left block"
                            title={`Open ${s.ticker} full ticker page`}
                          >
                            {s.ticker}
                          </button>
                          <div className="text-[11px] text-slate-500 truncate max-w-[180px]">{s.name}</div>
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {formatINR(s.latestClose)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums font-semibold text-emerald-600 dark:text-emerald-400">
                          {s.dividend.dividendYieldPct.toFixed(2)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {formatINR(s.dividend.annualDpsInr)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {formatINR(s.dividend.fcfPerShareInr)}
                        </td>
                        <td
                          className={`py-2.5 px-3 text-right font-mono tabular-nums font-medium ${
                            fcfPayout > 85
                              ? 'text-red-600 dark:text-red-400'
                              : fcfPayout > 65
                              ? 'text-amber-600 dark:text-amber-400'
                              : 'text-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {fcfPayout.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums text-blue-600 dark:text-blue-400">
                          +{s.dividend.fcf5YCagrPct.toFixed(1)}%
                        </td>
                        <td className="py-2.5 px-3 text-right font-mono tabular-nums">
                          {s.dividend.netDebtToEbitda.toFixed(2)}×
                        </td>
                        <td className="py-2.5 px-4 text-right font-mono tabular-nums text-slate-500">
                          {s.dividend.consecutiveYearsPaid} yrs
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
