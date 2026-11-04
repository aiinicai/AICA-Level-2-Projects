import {
  Purchase,
  RateRecord,
  AppSettings,
  HoldingValuation,
  MetalSummary,
  PortfolioSummary,
  MetalType,
  ChartDataPoint
} from '../types';
import { daysBetween, addDays } from './formatters';
import { calculateXIRR, CashFlow } from './xirr';

/**
 * Build index of rates by metal and date for fast lookup.
 */
export interface RateIndex {
  // Map key: `${date}_${metal}_${purity}` -> RateRecord
  exactMap: Map<string, RateRecord>;
  // Map key: `${metal}` -> sorted unique dates descending
  metalDatesDesc: Map<MetalType, string[]>;
  // Map key: `${date}_${metal}` -> array of purity records on that date
  dateMetalMap: Map<string, RateRecord[]>;
}

export function buildRateIndex(rates: RateRecord[]): RateIndex {
  const exactMap = new Map<string, RateRecord>();
  const dateMetalMap = new Map<string, RateRecord[]>();
  const goldDatesSet = new Set<string>();
  const silverDatesSet = new Set<string>();

  for (const r of rates) {
    const key = `${r.date}_${r.metal}_${r.purity}`;
    exactMap.set(key, r);

    const dmKey = `${r.date}_${r.metal}`;
    const list = dateMetalMap.get(dmKey) || [];
    list.push(r);
    dateMetalMap.set(dmKey, list);

    if (r.metal === 'GOLD') goldDatesSet.add(r.date);
    if (r.metal === 'SILVER') silverDatesSet.add(r.date);
  }

  const metalDatesDesc = new Map<MetalType, string[]>();
  metalDatesDesc.set('GOLD', Array.from(goldDatesSet).sort().reverse());
  metalDatesDesc.set('SILVER', Array.from(silverDatesSet).sort().reverse());

  return { exactMap, metalDatesDesc, dateMetalMap };
}

/**
 * Find the latest rate on or before target date D for a specific metal and purity.
 */
export function findApplicableRate(
  index: RateIndex,
  metal: MetalType,
  desiredPurity: number,
  targetDate: string
): {
  rateRecord?: RateRecord;
  actualRateDate?: string;
  ratePerGram: number;
  referenceFineness: number;
  isPurityAdjusted: boolean;
  purityAdjustmentRatio: number;
  isCarriedForward: boolean;
  isGap: boolean;
  sourceLabel: string;
} | null {
  const dates = index.metalDatesDesc.get(metal);
  if (!dates || dates.length === 0) return null;

  // Find the first date <= targetDate
  const applicableDate = dates.find(d => d <= targetDate);
  if (!applicableDate) return null;

  const isCarriedForward = applicableDate !== targetDate;
  const daysLag = isCarriedForward ? daysBetween(applicableDate, targetDate) : 0;
  // Gap is flagged if carried forward for more than 4 days (or known 2020-08-03 gap)
  const isGap = daysLag > 4 || (metal === 'SILVER' && targetDate === '2020-08-03');

  // 1. Try exact purity match on applicableDate
  const exactKey = `${applicableDate}_${metal}_${desiredPurity}`;
  const exactRecord = index.exactMap.get(exactKey);

  if (exactRecord) {
    return {
      rateRecord: exactRecord,
      actualRateDate: applicableDate,
      ratePerGram: exactRecord.pricePerGram,
      referenceFineness: desiredPurity,
      isPurityAdjusted: false,
      purityAdjustmentRatio: 1.0,
      isCarriedForward,
      isGap,
      sourceLabel: exactRecord.sourceType
    };
  }

  // 2. No exact purity match (e.g. 916 gold or 925 silver).
  // Prefer 999 reference rate, else 995
  const refKey999 = `${applicableDate}_${metal}_999`;
  const refRecord999 = index.exactMap.get(refKey999);
  const refKey995 = `${applicableDate}_${metal}_995`;
  const refRecord995 = index.exactMap.get(refKey995);

  const refRecord = refRecord999 || refRecord995;
  if (!refRecord) return null;

  const referenceFineness = refRecord.purity;
  const purityAdjustmentRatio = desiredPurity / referenceFineness;
  const adjustedRate = Math.round(refRecord.pricePerGram * purityAdjustmentRatio * 100) / 100;

  return {
    rateRecord: refRecord,
    actualRateDate: applicableDate,
    ratePerGram: adjustedRate,
    referenceFineness,
    isPurityAdjusted: true,
    purityAdjustmentRatio,
    isCarriedForward,
    isGap,
    sourceLabel: `${refRecord.sourceType} (Purity Adjusted)`
  };
}

/**
 * Value an individual holding lot as of selected date D.
 */
export function valueHoldingLot(
  holding: Purchase,
  selectedDate: string,
  rateIndex: RateIndex,
  settings: AppSettings
): HoldingValuation {
  const markdownPct = holding.metal === 'GOLD' ? settings.goldMarkdownPct : settings.silverMarkdownPct;
  const markdownRatio = markdownPct / 100.0;

  const rateInfo = findApplicableRate(rateIndex, holding.metal, holding.purity, selectedDate);

  if (!rateInfo) {
    return {
      holding,
      selectedDate,
      hasRate: false,
      ratePerGram: 0,
      referenceFineness: holding.purity,
      isPurityAdjusted: false,
      purityAdjustmentRatio: 1,
      isCarriedForward: false,
      rateSourceLabel: 'No Rate Available',
      referenceMetalValue: 0,
      markdownPct,
      estimatedResaleValue: 0,
      gainLossAmount: 0,
      gainLossPct: 0,
      holdingDays: daysBetween(holding.purchaseDate, selectedDate),
      annualizedXirr: null,
      xirrStatus: 'N/A: Rate unavailable on or before date'
    };
  }

  const referenceMetalValue = Math.round(holding.weightGrams * rateInfo.ratePerGram * 100) / 100;
  const estimatedResaleValue = Math.round(referenceMetalValue * (1.0 - markdownRatio) * 100) / 100;
  const gainLossAmount = Math.round((estimatedResaleValue - holding.investedAmount) * 100) / 100;
  const gainLossPct = holding.investedAmount > 0
    ? Math.round((gainLossAmount / holding.investedAmount) * 10000) / 100
    : 0;

  const holdingDays = daysBetween(holding.purchaseDate, selectedDate);

  // Holding-level XIRR:
  // Outflow: -investedAmount on purchaseDate
  // Inflow: +estimatedResaleValue on selectedDate D
  const flows: CashFlow[] = [
    { date: holding.purchaseDate, amount: -holding.investedAmount },
    { date: selectedDate, amount: estimatedResaleValue }
  ];
  const xirrRes = calculateXIRR(flows);

  return {
    holding,
    selectedDate,
    hasRate: true,
    rateRecord: rateInfo.rateRecord,
    actualRateDate: rateInfo.actualRateDate,
    ratePerGram: rateInfo.ratePerGram,
    referenceFineness: rateInfo.referenceFineness,
    isPurityAdjusted: rateInfo.isPurityAdjusted,
    purityAdjustmentRatio: rateInfo.purityAdjustmentRatio,
    isCarriedForward: rateInfo.isCarriedForward,
    rateSourceLabel: rateInfo.sourceLabel,
    referenceMetalValue,
    markdownPct,
    estimatedResaleValue,
    gainLossAmount,
    gainLossPct,
    holdingDays,
    annualizedXirr: xirrRes.xirr,
    xirrStatus: xirrRes.status === 'SUCCESS' ? 'Converged' : `N/A: ${xirrRes.reason}`
  };
}

/**
 * Value the full portfolio as of date D.
 */
export function valuePortfolio(
  allPurchases: Purchase[],
  selectedDate: string,
  rateIndex: RateIndex,
  settings: AppSettings
): {
  summary: PortfolioSummary;
  lotValuations: HoldingValuation[];
} {
  // Only active purchases with purchaseDate <= selectedDate
  const eligiblePurchases = allPurchases.filter(
    p => !p.deleted && p.purchaseDate <= selectedDate
  );

  const lotValuations = eligiblePurchases.map(p =>
    valueHoldingLot(p, selectedDate, rateIndex, settings)
  );

  const goldLots = lotValuations.filter(v => v.holding.metal === 'GOLD');
  const silverLots = lotValuations.filter(v => v.holding.metal === 'SILVER');

  function summarizeMetal(metal: MetalType, lots: HoldingValuation[]): MetalSummary {
    const totalGrams = lots.reduce((acc, l) => acc + l.holding.weightGrams, 0);
    const investedAmount = lots.reduce((acc, l) => acc + l.holding.investedAmount, 0);
    const referenceValue = lots.reduce((acc, l) => acc + l.referenceMetalValue, 0);
    const resaleValue = lots.reduce((acc, l) => acc + l.estimatedResaleValue, 0);
    const gainLossAmount = resaleValue - investedAmount;
    const gainLossPct = investedAmount > 0 ? (gainLossAmount / investedAmount) * 100 : 0;
    const unvaluedCount = lots.filter(l => !l.hasRate).length;

    // Metal-level XIRR:
    // Outflows: all purchases of this metal; Inflow: total resale value on selectedDate
    let metalXirr: number | null = null;
    let metalXirrStatus = 'No transactions';

    if (lots.length > 0 && unvaluedCount === 0) {
      const metalFlows: CashFlow[] = lots.map(l => ({
        date: l.holding.purchaseDate,
        amount: -l.holding.investedAmount
      }));
      metalFlows.push({ date: selectedDate, amount: resaleValue });
      const res = calculateXIRR(metalFlows);
      metalXirr = res.xirr;
      metalXirrStatus = res.status === 'SUCCESS' ? 'Converged' : `N/A: ${res.reason}`;
    } else if (unvaluedCount > 0) {
      metalXirrStatus = 'N/A: Partial valuation (missing rates for some holdings)';
    }

    return {
      metal,
      totalGrams,
      investedAmount,
      referenceValue,
      resaleValue,
      gainLossAmount,
      gainLossPct,
      annualizedXirr: metalXirr,
      xirrStatus: metalXirrStatus,
      holdingsCount: lots.length,
      unvaluedCount
    };
  }

  const goldSummary = summarizeMetal('GOLD', goldLots);
  const silverSummary = summarizeMetal('SILVER', silverLots);

  const totalInvested = goldSummary.investedAmount + silverSummary.investedAmount;
  const totalReference = goldSummary.referenceValue + silverSummary.referenceValue;
  const totalResale = goldSummary.resaleValue + silverSummary.resaleValue;
  const totalGainLoss = totalResale - totalInvested;
  const totalGainLossPct = totalInvested > 0 ? (totalGainLoss / totalInvested) * 100 : 0;
  const totalUnvalued = goldSummary.unvaluedCount + silverSummary.unvaluedCount;
  const isPartialValuation = totalUnvalued > 0;

  // Portfolio-level XIRR:
  // Combined cash flows of all purchases + total terminal resale value on selectedDate
  let portfolioXirr: number | null = null;
  let portfolioXirrStatus = 'No transactions';

  if (lotValuations.length > 0 && !isPartialValuation) {
    const portFlows: CashFlow[] = lotValuations.map(l => ({
      date: l.holding.purchaseDate,
      amount: -l.holding.investedAmount
    }));
    portFlows.push({ date: selectedDate, amount: totalResale });
    const res = calculateXIRR(portFlows);
    portfolioXirr = res.xirr;
    portfolioXirrStatus = res.status === 'SUCCESS' ? 'Converged' : `N/A: ${res.reason}`;
  } else if (isPartialValuation) {
    portfolioXirrStatus = 'N/A: Partial valuation (some holdings lack benchmark rates)';
  }

  const summary: PortfolioSummary = {
    selectedDate,
    investedAmount: totalInvested,
    referenceValue: totalReference,
    resaleValue: totalResale,
    gainLossAmount: totalGainLoss,
    gainLossPct: totalGainLossPct,
    annualizedXirr: portfolioXirr,
    xirrStatus: portfolioXirrStatus,
    totalHoldingsCount: lotValuations.length,
    unvaluedCount: totalUnvalued,
    gold: goldSummary,
    silver: silverSummary,
    isPartialValuation
  };

  return { summary, lotValuations };
}

/**
 * Generate historical chart series from earliest purchase date to selectedDate D.
 * Later purchases strictly do not affect earlier historical valuation dates.
 */
export function generateChartSeries(
  allPurchases: Purchase[],
  selectedDate: string,
  rateIndex: RateIndex,
  settings: AppSettings
): ChartDataPoint[] {
  const activePurchases = allPurchases.filter(p => !p.deleted && p.purchaseDate <= selectedDate);
  if (activePurchases.length === 0) return [];

  const earliestDate = activePurchases.map(p => p.purchaseDate).sort()[0];
  const totalDays = daysBetween(earliestDate, selectedDate);
  if (totalDays < 0) return [];

  // Determine step size to maintain snappy performance:
  // < 90 days: daily; < 365 days: every 2 days; < 3 years: weekly; > 3 years: semi-monthly
  let step = 1;
  if (totalDays > 1000) step = 7;
  else if (totalDays > 365) step = 3;
  else if (totalDays > 90) step = 2;

  const points: ChartDataPoint[] = [];
  let currDate = earliestDate;

  while (currDate <= selectedDate) {
    const { summary } = valuePortfolio(activePurchases, currDate, rateIndex, settings);

    // Identify if this date is near the NSE -> IBJA transition (2026-06-16)
    const isSourceTransition = currDate === '2026-06-16' ||
      (daysBetween(currDate, '2026-06-16') >= 0 && daysBetween(currDate, '2026-06-16') < step);

    points.push({
      date: currDate,
      investedCost: summary.investedAmount,
      resaleValue: summary.resaleValue,
      goldResaleValue: summary.gold.resaleValue,
      silverResaleValue: summary.silver.resaleValue,
      activeHoldings: summary.totalHoldingsCount,
      isSourceTransition,
      sourceNote: isSourceTransition ? 'NSE Spot -> IBJA Closing' : undefined
    });

    if (currDate === selectedDate) break;
    currDate = addDays(currDate, step);
    if (currDate > selectedDate) {
      currDate = selectedDate; // Ensure selectedDate is always the last point
    }
  }

  return points;
}
