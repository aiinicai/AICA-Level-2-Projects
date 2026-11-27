import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { STOCK_BY_TICKER } from '../data/indianMarketData';
import {
  IndianTransactionCost,
  PortfolioHolding,
  RebalanceOrder,
} from '../types/market';
import { formatINR, formatINRCompact, formatPct } from '../utils/formatters';

/**
 * Exact Indian NSE Equity Delivery Statutory Transaction Cost Schedule:
 * - Brokerage: Configurable (₹0 for Zerodha/Dhan delivery, or % brokerage)
 * - STT (Securities Transaction Tax): 0.1% on Buy & Sell delivery turnover
 * - NSE Exchange Transaction Charges: 0.00297%
 * - SEBI Turnover Fees: 0.0001% (₹10 per Crore)
 * - Stamp Duty: 0.015% on Buy side only
 * - GST: 18% on (Brokerage + Exchange Charges + SEBI Fees)
 * - DP Charges: ₹15.93 (₹13.50 + 18% GST) per ISIN sold
 */
export function calculateIndianDeliveryCost(
  tradeValueInr: number,
  side: 'BUY' | 'SELL',
  brokeragePct = 0 // 0% default for Indian discount delivery brokers
): IndianTransactionCost {
  if (tradeValueInr <= 0) {
    return {
      brokerage: 0,
      stt: 0,
      exchangeCharges: 0,
      sebiFees: 0,
      stampDuty: 0,
      gst: 0,
      dpCharges: 0,
      totalCost: 0,
      costBps: 0,
    };
  }

  const brokerage = (tradeValueInr * brokeragePct) / 100;
  const stt = tradeValueInr * 0.001; // 0.1%
  const exchangeCharges = tradeValueInr * 0.0000297; // 0.00297%
  const sebiFees = tradeValueInr * 0.000001; // 0.0001%
  const stampDuty = side === 'BUY' ? tradeValueInr * 0.00015 : 0; // 0.015% buy only
  const gst = (brokerage + exchangeCharges + sebiFees) * 0.18;
  const dpCharges = side === 'SELL' ? 15.93 : 0; // ₹13.50 + 18% GST per ISIN sell
  const totalCost = brokerage + stt + exchangeCharges + sebiFees + stampDuty + gst + dpCharges;
  const costBps = (totalCost / tradeValueInr) * 10000;

  return {
    brokerage: Number(brokerage.toFixed(2)),
    stt: Number(stt.toFixed(2)),
    exchangeCharges: Number(exchangeCharges.toFixed(2)),
    sebiFees: Number(sebiFees.toFixed(2)),
    stampDuty: Number(stampDuty.toFixed(2)),
    gst: Number(gst.toFixed(2)),
    dpCharges: Number(dpCharges.toFixed(2)),
    totalCost: Number(totalCost.toFixed(2)),
    costBps: Number(costBps.toFixed(1)),
  };
}

export interface EnrichedHolding {
  holding: PortfolioHolding;
  name: string;
  sector: string;
  priceInr: number;
  dailyChangePct: number;
  marketValueInr: number;
  investedValueInr: number;
  unrealizedPnlInr: number;
  unrealizedPnlPct: number;
  dailyPnlInr: number;
  currentWeightPct: number;
  beta: number;
}

export interface PortfolioSummary {
  enriched: EnrichedHolding[];
  totalMarketValueInr: number;
  totalInvestedInr: number;
  totalUnrealizedPnlInr: number;
  totalUnrealizedPnlPct: number;
  totalDailyPnlInr: number;
  totalDailyPnlPct: number;
  portfolioBeta: number;
  annualizedVolPct: number;
  sharpeRatio: number;
  var95DailyInr: number;
  maxDrawdownEstPct: number;
}

export function computePortfolioSummary(holdings: PortfolioHolding[]): PortfolioSummary {
  const raw = holdings
    .map((h) => {
      const stock = STOCK_BY_TICKER[h.ticker];
      if (!stock) return null;
      const marketValueInr = h.shares * stock.latestClose;
      const investedValueInr = h.shares * h.avgCostInr;
      const unrealizedPnlInr = marketValueInr - investedValueInr;
      const unrealizedPnlPct = investedValueInr > 0 ? (unrealizedPnlInr / investedValueInr) * 100 : 0;
      const dailyPnlInr = h.shares * (stock.latestClose - stock.prevClose);
      return {
        holding: h,
        name: stock.name,
        sector: stock.sector,
        priceInr: stock.latestClose,
        dailyChangePct: stock.dailyChangePct,
        marketValueInr,
        investedValueInr,
        unrealizedPnlInr,
        unrealizedPnlPct,
        dailyPnlInr,
        currentWeightPct: 0,
        beta: stock.beta,
      };
    })
    .filter((x): x is EnrichedHolding => x !== null);

  const totalMarketValueInr = raw.reduce((s, r) => s + r.marketValueInr, 0);
  const totalInvestedInr = raw.reduce((s, r) => s + r.investedValueInr, 0);
  const totalUnrealizedPnlInr = totalMarketValueInr - totalInvestedInr;
  const totalUnrealizedPnlPct =
    totalInvestedInr > 0 ? (totalUnrealizedPnlInr / totalInvestedInr) * 100 : 0;
  const totalDailyPnlInr = raw.reduce((s, r) => s + r.dailyPnlInr, 0);
  const prevTotal = totalMarketValueInr - totalDailyPnlInr;
  const totalDailyPnlPct = prevTotal > 0 ? (totalDailyPnlInr / prevTotal) * 100 : 0;

  const enriched = raw.map((r) => ({
    ...r,
    currentWeightPct: totalMarketValueInr > 0 ? (r.marketValueInr / totalMarketValueInr) * 100 : 0,
  }));

  const portfolioBeta = enriched.reduce(
    (s, r) => s + (r.currentWeightPct / 100) * r.beta,
    0
  );

  // Compute realized 1Y portfolio daily return series from actual OHLCV bars for true Vol, Sharpe, VaR, MaxDD
  const lookback = 252;
  const portValues: number[] = [];
  if (enriched.length > 0) {
    const sampleBars = STOCK_BY_TICKER[enriched[0].holding.ticker]?.bars;
    const totalLen = sampleBars?.length ?? 0;
    const start = Math.max(0, totalLen - lookback);
    for (let i = start; i < totalLen; i++) {
      let val = 0;
      for (const e of enriched) {
        const b = STOCK_BY_TICKER[e.holding.ticker]?.bars[i];
        if (b) val += e.holding.shares * b.close;
      }
      portValues.push(val);
    }
  }

  const dailyRets: number[] = [];
  let peak = 0;
  let maxDd = 0;
  for (let i = 0; i < portValues.length; i++) {
    if (portValues[i] > peak) peak = portValues[i];
    if (peak > 0) {
      const dd = ((peak - portValues[i]) / peak) * 100;
      if (dd > maxDd) maxDd = dd;
    }
    if (i > 0 && portValues[i - 1] > 0) {
      dailyRets.push((portValues[i] - portValues[i - 1]) / portValues[i - 1]);
    }
  }

  const meanRet = dailyRets.length > 0 ? dailyRets.reduce((s, r) => s + r, 0) / dailyRets.length : 0;
  const variance =
    dailyRets.length > 1
      ? dailyRets.reduce((s, r) => s + Math.pow(r - meanRet, 2), 0) / (dailyRets.length - 1)
      : 0;
  const dailyStd = Math.sqrt(variance);
  const annualizedVolPct = dailyStd * Math.sqrt(252) * 100;
  const rfDaily = 0.065 / 252;
  const sharpeRatio = dailyStd > 0 ? ((meanRet - rfDaily) / dailyStd) * Math.sqrt(252) : 0;
  const var95DailyInr = totalMarketValueInr * (1.645 * dailyStd);

  return {
    enriched,
    totalMarketValueInr,
    totalInvestedInr,
    totalUnrealizedPnlInr,
    totalUnrealizedPnlPct,
    totalDailyPnlInr,
    totalDailyPnlPct,
    portfolioBeta: Number(portfolioBeta.toFixed(2)),
    annualizedVolPct: Number(annualizedVolPct.toFixed(2)),
    sharpeRatio: Number(sharpeRatio.toFixed(2)),
    var95DailyInr: Math.round(var95DailyInr),
    maxDrawdownEstPct: Number(maxDd.toFixed(2)),
  };
}

/**
 * Automatic Rebalancing Engine with Indian statutory transaction costs
 */
export function computeRebalancePlan(
  summary: PortfolioSummary,
  cashFlowInr = 0,
  driftTolerancePct = 0.5,
  brokeragePct = 0
): {
  orders: RebalanceOrder[];
  totalBuyValue: number;
  totalSellValue: number;
  totalStatutoryCost: number;
  costSummary: IndianTransactionCost;
} {
  const targetTotalValue = Math.max(0, summary.totalMarketValueInr + cashFlowInr);
  const sumTargetWeights = summary.enriched.reduce(
    (s, e) => s + e.holding.targetWeightPct,
    0
  );
  const normFactor = sumTargetWeights > 0 ? 100 / sumTargetWeights : 1;

  const orders: RebalanceOrder[] = summary.enriched.map((e) => {
    const normalizedTargetPct = e.holding.targetWeightPct * normFactor;
    const driftPct = e.currentWeightPct - normalizedTargetPct;
    const targetVal = (normalizedTargetPct / 100) * targetTotalValue;
    const rawTargetShares = Math.round(targetVal / e.priceInr);
    const isWithinTolerance = Math.abs(driftPct) < driftTolerancePct && cashFlowInr === 0;
    const targetShares = isWithinTolerance ? e.holding.shares : rawTargetShares;
    const deltaShares = targetShares - e.holding.shares;
    const action: 'BUY' | 'SELL' | 'HOLD' =
      deltaShares > 0 ? 'BUY' : deltaShares < 0 ? 'SELL' : 'HOLD';
    const tradeValueInr = Math.abs(deltaShares) * e.priceInr;
    const costs =
      action === 'HOLD'
        ? calculateIndianDeliveryCost(0, 'BUY', brokeragePct)
        : calculateIndianDeliveryCost(tradeValueInr, action, brokeragePct);

    return {
      ticker: e.holding.ticker,
      name: e.name,
      action,
      currentShares: e.holding.shares,
      targetShares,
      deltaShares,
      priceInr: e.priceInr,
      tradeValueInr: Number(tradeValueInr.toFixed(2)),
      currentWeightPct: Number(e.currentWeightPct.toFixed(2)),
      targetWeightPct: Number(normalizedTargetPct.toFixed(2)),
      driftPct: Number(driftPct.toFixed(2)),
      costs,
    };
  });

  const totalBuyValue = orders
    .filter((o) => o.action === 'BUY')
    .reduce((s, o) => s + o.tradeValueInr, 0);
  const totalSellValue = orders
    .filter((o) => o.action === 'SELL')
    .reduce((s, o) => s + o.tradeValueInr, 0);

  const costSummary = orders.reduce<IndianTransactionCost>(
    (acc, o) => ({
      brokerage: Number((acc.brokerage + o.costs.brokerage).toFixed(2)),
      stt: Number((acc.stt + o.costs.stt).toFixed(2)),
      exchangeCharges: Number((acc.exchangeCharges + o.costs.exchangeCharges).toFixed(2)),
      sebiFees: Number((acc.sebiFees + o.costs.sebiFees).toFixed(2)),
      stampDuty: Number((acc.stampDuty + o.costs.stampDuty).toFixed(2)),
      gst: Number((acc.gst + o.costs.gst).toFixed(2)),
      dpCharges: Number((acc.dpCharges + o.costs.dpCharges).toFixed(2)),
      totalCost: Number((acc.totalCost + o.costs.totalCost).toFixed(2)),
      costBps: 0,
    }),
    {
      brokerage: 0,
      stt: 0,
      exchangeCharges: 0,
      sebiFees: 0,
      stampDuty: 0,
      gst: 0,
      dpCharges: 0,
      totalCost: 0,
      costBps: 0,
    }
  );
  const totalTurnover = totalBuyValue + totalSellValue;
  costSummary.costBps =
    totalTurnover > 0 ? Number(((costSummary.totalCost / totalTurnover) * 10000).toFixed(1)) : 0;

  return {
    orders: orders.sort((a, b) => Math.abs(b.tradeValueInr) - Math.abs(a.tradeValueInr)),
    totalBuyValue,
    totalSellValue,
    totalStatutoryCost: costSummary.totalCost,
    costSummary,
  };
}

export interface ScenarioDefinition {
  id: string;
  name: string;
  category: 'Macro Shock' | 'Historical Indian Event';
  description: string;
  nifty50ShockPct: number;
  sensitivityKey?: keyof typeof STOCK_BY_TICKER['RELIANCE']['sensitivities'];
  sectorOverrides?: Record<string, number>;
}

export const PREDEFINED_SCENARIOS: ScenarioDefinition[] = [
  {
    id: 'market_drop_10',
    name: '-10% Broad NIFTY Market Drop',
    category: 'Macro Shock',
    description: 'Synchronized FII outflow pulling NIFTY 50 down 10% across beta-weighted sectors.',
    nifty50ShockPct: -10.0,
    sensitivityKey: 'marketDrop10',
  },
  {
    id: 'inflation_20',
    name: '+20% Inflation Spike',
    category: 'Macro Shock',
    description: 'Sharp CPI & WPI spike squeezing input margins across autos, financials, and retail while energy hedges.',
    nifty50ShockPct: -6.2,
    sensitivityKey: 'inflationShock',
  },
  {
    id: 'inr_dep_10',
    name: 'INR Depreciation (-10% vs USD)',
    category: 'Macro Shock',
    description: 'Rupee slides 10% against USD; export-heavy IT and Pharma rally while import-dependent sectors soften.',
    nifty50ShockPct: -1.8,
    sensitivityKey: 'inrDepreciation10',
  },
  {
    id: 'rbi_hike_100',
    name: 'RBI Repo Rate Hike (+100 bps)',
    category: 'Macro Shock',
    description: 'Tightening liquidity cycle pressuring NBFCs, rate-sensitive autos, and capex valuations.',
    nifty50ShockPct: -4.8,
    sensitivityKey: 'rbiRateHike100bps',
  },
  {
    id: 'crude_35',
    name: 'Brent Crude Oil Surge (+35%)',
    category: 'Macro Shock',
    description: 'Geopolitical oil supply shock widening India CAD and pressuring chemicals, autos, and aviation.',
    nifty50ShockPct: -4.1,
    sensitivityKey: 'crudeSurge35',
  },
  {
    id: 'gfc_2008',
    name: '2008 Global Financial Crisis (Jan–Oct 2008)',
    category: 'Historical Indian Event',
    description: 'Peak-to-trough NIFTY 50 drawdown of -59.8% driven by global deleveraging and ₹52,000 Cr FII exit.',
    nifty50ShockPct: -59.8,
    sectorOverrides: {
      'Banking & Financial Services': -64.0,
      'Capital Goods & Defence': -68.5,
      'Capital Markets': -71.0,
      'Automobiles & EV': -58.0,
      'Energy & Power': -54.0,
      'Information Technology': -48.0,
      'FMCG': -28.0,
      'Pharma & Healthcare': -32.0,
      'Consumer & Retail': -51.0,
      'Telecom & Digital': -49.0,
      'Chemicals & Materials': -56.0,
    },
  },
  {
    id: 'demonetisation_2016',
    name: '2016 Demonetisation (Nov–Dec 2016)',
    category: 'Historical Indian Event',
    description: 'High-value currency withdrawal hitting cash-intensive consumer retail, jewellery, and NBFC collections.',
    nifty50ShockPct: -7.9,
    sectorOverrides: {
      'Consumer & Retail': -18.4,
      'Automobiles & EV': -14.2,
      'Banking & Financial Services': -9.6,
      'FMCG': -8.2,
      'Capital Goods & Defence': -10.5,
      'Information Technology': +2.4,
      'Pharma & Healthcare': -3.8,
      'Energy & Power': -2.1,
      'Capital Markets': -11.4,
      'Telecom & Digital': -5.6,
      'Chemicals & Materials': -9.2,
    },
  },
  {
    id: 'ilfs_2018',
    name: '2018 IL&FS NBFC Liquidity Crisis (Sep–Oct 2018)',
    category: 'Historical Indian Event',
    description: 'Commercial paper freeze triggering sharp NBFC, auto, and midcap selloff.',
    nifty50ShockPct: -14.6,
    sectorOverrides: {
      'Banking & Financial Services': -22.8,
      'Automobiles & EV': -21.4,
      'Capital Markets': -24.5,
      'Consumer & Retail': -15.2,
      'Capital Goods & Defence': -16.8,
      'Information Technology': -4.2,
      'Pharma & Healthcare': -8.6,
      'FMCG': -9.4,
      'Energy & Power': -11.2,
      'Telecom & Digital': -13.8,
      'Chemicals & Materials': -15.6,
    },
  },
  {
    id: 'covid_2020',
    name: '2020 COVID-19 Crash (Feb–Mar 2020)',
    category: 'Historical Indian Event',
    description: 'Nationwide lockdown shock pulling NIFTY 50 down -38.4% in 33 sessions; Pharma & FMCG cushioned losses.',
    nifty50ShockPct: -38.4,
    sectorOverrides: {
      'Banking & Financial Services': -44.2,
      'Automobiles & EV': -42.6,
      'Consumer & Retail': -39.4,
      'Capital Goods & Defence': -41.0,
      'Capital Markets': -37.8,
      'Energy & Power': -34.2,
      'Information Technology': -26.4,
      'Telecom & Digital': -21.8,
      'FMCG': -19.2,
      'Pharma & Healthcare': -14.5,
      'Chemicals & Materials': -32.6,
    },
  },
  {
    id: 'election_2024',
    name: '2024 Election Counting Day (June 4, 2024)',
    category: 'Historical Indian Event',
    description: 'Single-day coalition surprise triggering -5.9% NIFTY 50 drop and sharp PSU/Defence pullback while FMCG rallied.',
    nifty50ShockPct: -5.9,
    sectorOverrides: {
      'Energy & Power': -14.8,
      'Capital Goods & Defence': -15.4,
      'Banking & Financial Services': -8.2,
      'Capital Markets': -11.6,
      'Automobiles & EV': -4.8,
      'Consumer & Retail': -2.6,
      'Telecom & Digital': -5.4,
      'Chemicals & Materials': -5.2,
      'Information Technology': -0.8,
      'Pharma & Healthcare': -1.2,
      'FMCG': +2.4,
    },
  },
];

export interface ScenarioSimulationResult {
  scenarioName: string;
  nifty50ShockPct: number;
  portfolioImpactPct: number;
  portfolioImpactInr: number;
  postShockValueInr: number;
  relativeAlphaPct: number;
  stockImpacts: {
    ticker: string;
    name: string;
    sector: string;
    currentValueInr: number;
    impactPct: number;
    impactInr: number;
    postValueInr: number;
  }[];
}

export function simulateScenario(
  summary: PortfolioSummary,
  scenario: ScenarioDefinition,
  customOverrides?: { equityShockPct: number; inrShockPct: number; rateBps: number }
): ScenarioSimulationResult {
  const stockImpacts = summary.enriched.map((e) => {
    const stock = STOCK_BY_TICKER[e.holding.ticker];
    let impactPct = 0;

    if (customOverrides) {
      const betaPart = customOverrides.equityShockPct * e.beta;
      const inrPart =
        (stock.sensitivities.inrDepreciation10 / 10) * customOverrides.inrShockPct;
      const ratePart =
        (stock.sensitivities.rbiRateHike100bps / 100) * customOverrides.rateBps;
      impactPct = betaPart + inrPart + ratePart;
    } else if (scenario.sectorOverrides) {
      const baseSector = scenario.sectorOverrides[e.sector] ?? scenario.nifty50ShockPct;
      impactPct = baseSector * (0.7 + 0.3 * e.beta);
    } else if (scenario.sensitivityKey) {
      impactPct = stock.sensitivities[scenario.sensitivityKey] * (0.75 + 0.25 * e.beta);
    }

    impactPct = Math.max(-92, Math.min(60, Number(impactPct.toFixed(2))));
    const impactInr = (e.marketValueInr * impactPct) / 100;
    return {
      ticker: e.holding.ticker,
      name: e.name,
      sector: e.sector,
      currentValueInr: e.marketValueInr,
      impactPct,
      impactInr: Number(impactInr.toFixed(2)),
      postValueInr: Number((e.marketValueInr + impactInr).toFixed(2)),
    };
  });

  const portfolioImpactInr = stockImpacts.reduce((s, x) => s + x.impactInr, 0);
  const postShockValueInr = summary.totalMarketValueInr + portfolioImpactInr;
  const portfolioImpactPct =
    summary.totalMarketValueInr > 0
      ? Number(((portfolioImpactInr / summary.totalMarketValueInr) * 100).toFixed(2))
      : 0;
  const benchShock = customOverrides ? customOverrides.equityShockPct : scenario.nifty50ShockPct;

  return {
    scenarioName: customOverrides ? 'Custom Macro Stress Test' : scenario.name,
    nifty50ShockPct: benchShock,
    portfolioImpactPct,
    portfolioImpactInr: Number(portfolioImpactInr.toFixed(2)),
    postShockValueInr: Number(postShockValueInr.toFixed(2)),
    relativeAlphaPct: Number((portfolioImpactPct - benchShock).toFixed(2)),
    stockImpacts: stockImpacts.sort((a, b) => a.impactInr - b.impactInr),
  };
}

/**
 * Institutional PDF Snapshot Report Generator (jsPDF + jspdf-autotable)
 */
export function generatePortfolioPdfReport(
  summary: PortfolioSummary,
  rebalance: ReturnType<typeof computeRebalancePlan>,
  activeScenario: ScenarioSimulationResult,
  investorName: string
): void {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
  const dateStr = new Date().toISOString().slice(0, 10);

  // Header
  doc.setFillColor(11, 15, 23);
  doc.rect(0, 0, 595, 76, 'F');
  doc.setTextColor(255, 255, 255);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(18);
  doc.text('Personal Trades Terminal — Portfolio & Risk Snapshot', 36, 36);
  doc.setFont('helvetica', 'normal');
  doc.setFontSize(9.5);
  doc.setTextColor(180, 195, 215);
  doc.text(
    `NSE / BSE Equity Analytics  |  Prepared for: ${investorName || 'Portfolio Desk'}  |  Date: ${dateStr} (IST)`,
    36,
    56
  );

  // Executive KPI Strip
  doc.setTextColor(15, 23, 42);
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text('1. Portfolio & Risk Metrics Summary', 36, 102);

  autoTable(doc, {
    startY: 112,
    head: [['Market Value', 'Invested Capital', 'Unrealized P&L', 'Portfolio Beta', 'Ann. Volatility', 'Sharpe (6.5% Rf)', '95% 1D VaR']],
    body: [[
      formatINRCompact(summary.totalMarketValueInr),
      formatINRCompact(summary.totalInvestedInr),
      `${formatINRCompact(summary.totalUnrealizedPnlInr)} (${formatPct(summary.totalUnrealizedPnlPct)})`,
      summary.portfolioBeta.toFixed(2),
      `${summary.annualizedVolPct.toFixed(1)}%`,
      summary.sharpeRatio.toFixed(2),
      formatINRCompact(summary.var95DailyInr),
    ]],
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59], fontSize: 8 },
    bodyStyles: { fontSize: 8.5, fontStyle: 'bold' },
    margin: { left: 36, right: 36 },
  });

  // Current Holdings Table
  const yAfterKpi = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 22;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text('2. Current NSE/BSE Equity Holdings', 36, yAfterKpi);

  autoTable(doc, {
    startY: yAfterKpi + 10,
    head: [['Ticker', 'Sector', 'Shares', 'LTP (INR)', 'Value (INR)', 'Wt %', 'Target %', 'P&L %']],
    body: summary.enriched.map((e) => [
      e.holding.ticker,
      e.sector,
      String(e.holding.shares),
      formatINR(e.priceInr),
      formatINR(e.marketValueInr, 0),
      `${e.currentWeightPct.toFixed(1)}%`,
      `${e.holding.targetWeightPct.toFixed(1)}%`,
      formatPct(e.unrealizedPnlPct),
    ]),
    theme: 'striped',
    headStyles: { fillColor: [30, 41, 59], fontSize: 8 },
    bodyStyles: { fontSize: 8 },
    margin: { left: 36, right: 36 },
  });

  // Rebalancing Orders & Statutory Cost Table
  const yAfterHoldings = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 22;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text('3. Automatic Rebalancing Recommendations & Indian Statutory Costs', 36, yAfterHoldings);

  const activeOrders = rebalance.orders.filter((o) => o.action !== 'HOLD');
  autoTable(doc, {
    startY: yAfterHoldings + 10,
    head: [['Ticker', 'Action', 'Qty', 'Order Value', 'STT (0.1%)', 'Stamp/Exch/GST', 'DP Chg', 'Total Cost']],
    body:
      activeOrders.length > 0
        ? activeOrders.map((o) => [
            o.ticker,
            o.action,
            String(Math.abs(o.deltaShares)),
            formatINR(o.tradeValueInr, 0),
            formatINR(o.costs.stt),
            formatINR(o.costs.stampDuty + o.costs.exchangeCharges + o.costs.sebiFees + o.costs.gst),
            formatINR(o.costs.dpCharges),
            formatINR(o.costs.totalCost),
          ])
        : [['All positions within drift tolerance', '-', '-', '-', '-', '-', '-', '₹0.00']],
    foot: [[
      'TOTAL',
      `Buy ${formatINRCompact(rebalance.totalBuyValue)} / Sell ${formatINRCompact(rebalance.totalSellValue)}`,
      '',
      '',
      formatINR(rebalance.costSummary.stt),
      formatINR(
        rebalance.costSummary.stampDuty +
          rebalance.costSummary.exchangeCharges +
          rebalance.costSummary.sebiFees +
          rebalance.costSummary.gst
      ),
      formatINR(rebalance.costSummary.dpCharges),
      `${formatINR(rebalance.totalStatutoryCost)} (${rebalance.costSummary.costBps} bps)`,
    ]],
    theme: 'grid',
    headStyles: { fillColor: [15, 23, 42], fontSize: 8 },
    bodyStyles: { fontSize: 8 },
    footStyles: { fillColor: [241, 245, 249], textColor: [15, 23, 42], fontStyle: 'bold', fontSize: 8 },
    margin: { left: 36, right: 36 },
  });

  // Scenario Analysis Summary
  const yAfterRebal = (doc as unknown as { lastAutoTable: { finalY: number } }).lastAutoTable.finalY + 22;
  if (yAfterRebal > 720) doc.addPage();
  const scenY = yAfterRebal > 720 ? 48 : yAfterRebal;
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(11);
  doc.text(`4. Stress Test Snapshot — ${activeScenario.scenarioName}`, 36, scenY);

  autoTable(doc, {
    startY: scenY + 10,
    head: [['Scenario', 'NIFTY 50 Shock', 'Portfolio Impact %', 'Portfolio Impact (INR)', 'Post-Shock Value', 'Relative Alpha']],
    body: [[
      activeScenario.scenarioName,
      formatPct(activeScenario.nifty50ShockPct),
      formatPct(activeScenario.portfolioImpactPct),
      formatINRCompact(activeScenario.portfolioImpactInr),
      formatINRCompact(activeScenario.postShockValueInr),
      formatPct(activeScenario.relativeAlphaPct),
    ]],
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59], fontSize: 8 },
    bodyStyles: { fontSize: 8.5, fontStyle: 'bold' },
    margin: { left: 36, right: 36 },
  });

  doc.save(`Personal_Trades_Terminal_Portfolio_Risk_Report_${dateStr}.pdf`);
}
