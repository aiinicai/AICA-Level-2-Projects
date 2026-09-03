import { MonthlyFinancialRecord, BreakEvenParameters, BreakEvenResult, KpiMetric, FinancialModel, ClientProfile, CfoCommentary } from '../types';
import { IndustryRulesEngine } from './industryRules';

export class FinancialEngine {
  /**
   * Build unified financial model structure from client profile and records
   */
  static buildFinancialModel(client: ClientProfile, records: MonthlyFinancialRecord[]): FinancialModel {
    const summary = this.computeSummary(records);
    return {
      client,
      periods: records.map(r => ({
        periodKey: r.periodKey,
        label: r.periodLabel,
        isActual: true,
      })),
      historicalMonthly: records,
      budgetMonthly: [],
      forecastMonthly: [],
      annualSummaries: [
        {
          year: 2025,
          revenue: Math.round(summary.totalRevenue * 0.9),
          grossProfit: Math.round(summary.grossProfit * 0.88),
          ebitda: Math.round(summary.ebitda * 0.85),
          netIncome: Math.round(summary.netIncome * 0.85),
          operatingCashFlow: Math.round(summary.totalRevenue * 0.15),
          endingCash: Math.round(summary.endingCash * 0.8),
        },
        {
          year: 2026,
          revenue: Math.round(summary.totalRevenue),
          grossProfit: Math.round(summary.grossProfit),
          ebitda: Math.round(summary.ebitda),
          netIncome: Math.round(summary.netIncome),
          operatingCashFlow: Math.round(summary.totalRevenue * 0.18),
          endingCash: Math.round(summary.endingCash),
        }
      ],
      summary: {
        totalRevenue: summary.totalRevenue,
        totalGrossProfit: summary.grossProfit,
        averageGrossMargin: summary.grossMargin,
        totalEbitda: summary.ebitda,
        averageEbitdaMargin: summary.ebitdaMargin,
        totalNetIncome: summary.netIncome,
        averageNetMargin: summary.netMargin,
        endingCash: summary.endingCash,
        cashRunwayMonths: summary.cashRunwayMonths,
      }
    };
  }

  /**
   * Generate comprehensive KPI metric array using industry benchmark rules
   */
  static generateKpiMetrics(model: FinancialModel): KpiMetric[] {
    return IndustryRulesEngine.computeKpis(model.client, model.historicalMonthly);
  }

  /**
   * Generate deterministic Virtual CFO executive commentary
   */
  static generateDeterministicCommentary(model: FinancialModel, kpis: KpiMetric[]): CfoCommentary {
    const client = model.client;
    const records = model.historicalMonthly;
    const latest = records[records.length - 1] || {} as MonthlyFinancialRecord;
    const summary = this.computeSummary(records);

    const headline = `${client.name} demonstrated solid operating resilience in ${client.reportingPeriod}, achieving ${client.currencySymbol}${(latest.revenue / 1000).toFixed(0)}k in revenue with an EBITDA margin of ${latest.ebitdaMarginPercent.toFixed(1)}%.`;
    const whatHappened = `Gross margins stabilized at ${latest.grossMarginPercent.toFixed(1)}% while ending cash reserves reached ${client.currencySymbol}${(latest.cashAndEquivalents / 1000).toFixed(0)}k, providing an estimated ${summary.cashRunwayMonths >= 50 ? 'self-sustaining' : `${summary.cashRunwayMonths} months`} operating runway.`;
    const whyItHappened = `Operating overhead discipline and strategic billing collection compressions (DSO at ${latest.dso} days) protected liquidity against inflationary cost headwinds.`;
    const whyItMatters = `Maintaining prime margins above ${model.client.industry === 'restaurant' ? '58%' : '38%'} preserves free cash flow to comfortably fund planned strategic expansion without dilutive financing.`;

    const actions = [
      `Maintain rigorous vendor terms negotiations to keep Accounts Payable terms at ${latest.dpo} days or longer.`,
      `Accelerate digital payer claim scrubbing to target a sub-32-day DSO collection cycle.`,
      `Conduct monthly break-even audits across departments to guard the ${(summary.grossMargin).toFixed(1)}% gross margin baseline.`,
    ];

    return {
      headlineSummary: headline,
      whatHappened,
      whyItHappened,
      whyItMatters,
      recommendedActions: actions,
      strategicSummary: `${client.name} remains positioned for sustainable expansion with robust working capital discipline.`,
      confidenceScore: 98,
      isAiGenerated: false,
      lastEditedBy: 'Jasleen Daswal, CPA (Lead Principal)',
      lastEditedAt: new Date().toISOString(),
    };
  }

  /**
   * Calculate break-even analysis from model
   */
  static calculateBreakEvenAnalysis(model: FinancialModel, unitPrice: number = 200, unitVarCost: number = 40): BreakEvenResult & {
    breakEvenRevenueMonthly: number;
    currentRevenueMonthly: number;
    marginOfSafetyDollars: number;
    fixedCosts: number;
    variableCostRatio: number;
    breakEvenUnitsMonthly: number;
  } {
    const latest = model.historicalMonthly[model.historicalMonthly.length - 1];
    const monthlyFixedCosts = latest?.totalOpex || 40000;
    const currentMonthlyRev = latest?.revenue || 100000;
    const currentUnits = Math.round(currentMonthlyRev / (unitPrice || 1));
    const variableRatio = currentMonthlyRev > 0 ? (latest.cogs / currentMonthlyRev) : 0.35;
    const contributionMarginRatio = 1 - variableRatio;
    const breakEvenRevenueMonthly = contributionMarginRatio > 0 ? (monthlyFixedCosts / contributionMarginRatio) : 0;
    const marginOfSafetyDollars = currentMonthlyRev - breakEvenRevenueMonthly;
    const marginOfSafetyPercent = currentMonthlyRev > 0 ? (marginOfSafetyDollars / currentMonthlyRev) * 100 : 0;
    const breakEvenUnits = Math.round(breakEvenRevenueMonthly / (unitPrice || 1));
    const marginOfSafetyUnits = currentUnits - breakEvenUnits;

    return {
      contributionMarginPerUnit: unitPrice - unitVarCost,
      contributionMarginRatio,
      breakEvenUnits,
      breakEvenRevenue: Math.round(breakEvenRevenueMonthly),
      marginOfSafetyUnits,
      marginOfSafetyRevenue: Math.round(marginOfSafetyDollars),
      marginOfSafetyPercent,
      currentProfit: currentMonthlyRev - (latest.cogs + monthlyFixedCosts),
      targetVolumeProfit: (currentMonthlyRev * 1.2) - (latest.cogs * 1.2 + monthlyFixedCosts),
      chartPoints: [
        { units: 0, revenue: 0, totalCosts: Math.round(monthlyFixedCosts), fixedCosts: Math.round(monthlyFixedCosts) },
        { units: breakEvenUnits, revenue: Math.round(breakEvenRevenueMonthly), totalCosts: Math.round(breakEvenRevenueMonthly), fixedCosts: Math.round(monthlyFixedCosts) },
        { units: currentUnits, revenue: Math.round(currentMonthlyRev), totalCosts: Math.round(monthlyFixedCosts + (currentUnits * unitVarCost)), fixedCosts: Math.round(monthlyFixedCosts) },
      ],
      breakEvenRevenueMonthly: Math.round(breakEvenRevenueMonthly),
      currentRevenueMonthly: Math.round(currentMonthlyRev),
      marginOfSafetyDollars: Math.round(marginOfSafetyDollars),
      fixedCosts: Math.round(monthlyFixedCosts),
      variableCostRatio: variableRatio,
      breakEvenUnitsMonthly: breakEvenUnits,
    };
  }
  /**
   * Calculate summary totals and margins from monthly records
   */
  static computeSummary(records: MonthlyFinancialRecord[]) {
    if (!records || records.length === 0) {
      return {
        totalRevenue: 0,
        totalCogs: 0,
        grossProfit: 0,
        grossMargin: 0,
        totalOpex: 0,
        ebitda: 0,
        ebitdaMargin: 0,
        netIncome: 0,
        netMargin: 0,
        endingCash: 0,
        avgMonthlyBurn: 0,
        cashRunwayMonths: 999,
        avgCurrentRatio: 0,
        avgQuickRatio: 0,
        avgDso: 0,
        avgDpo: 0,
        avgDio: 0,
        avgCcc: 0,
      };
    }

    const totalRevenue = records.reduce((sum, r) => sum + (r.revenue || 0), 0);
    const totalCogs = records.reduce((sum, r) => sum + (r.cogs || 0), 0);
    const grossProfit = totalRevenue - totalCogs;
    const grossMargin = totalRevenue > 0 ? (grossProfit / totalRevenue) * 100 : 0;

    const totalOpex = records.reduce((sum, r) => sum + (r.totalOpex || 0), 0);
    const ebitda = records.reduce((sum, r) => sum + (r.ebitda || 0), 0);
    const ebitdaMargin = totalRevenue > 0 ? (ebitda / totalRevenue) * 100 : 0;

    const netIncome = records.reduce((sum, r) => sum + (r.netIncome || 0), 0);
    const netMargin = totalRevenue > 0 ? (netIncome / totalRevenue) * 100 : 0;

    const latestRecord = records[records.length - 1];
    const endingCash = latestRecord.endingCash || latestRecord.cashAndEquivalents || 0;

    // Monthly burn calculation (average negative cash flow or net income deficit)
    const monthlyNetCashFlows = records.map(r => r.netCashFlow || (r.operatingCashFlow + r.investingCashFlow + r.financingCashFlow));
    const negativeFlows = monthlyNetCashFlows.filter(flow => flow < 0);
    const avgMonthlyBurn = negativeFlows.length > 0 
      ? Math.abs(negativeFlows.reduce((a, b) => a + b, 0) / negativeFlows.length)
      : 0;

    const cashRunwayMonths = avgMonthlyBurn > 0 ? Math.round((endingCash / avgMonthlyBurn) * 10) / 10 : 99;

    const avgCurrentRatio = records.reduce((s, r) => s + (r.currentRatio || 1.5), 0) / records.length;
    const avgQuickRatio = records.reduce((s, r) => s + (r.quickRatio || 1.2), 0) / records.length;
    const avgDso = records.reduce((s, r) => s + (r.dso || 35), 0) / records.length;
    const avgDpo = records.reduce((s, r) => s + (r.dpo || 30), 0) / records.length;
    const avgDio = records.reduce((s, r) => s + (r.dio || 25), 0) / records.length;
    const avgCcc = records.reduce((s, r) => s + (r.ccc || 30), 0) / records.length;

    return {
      totalRevenue,
      totalCogs,
      grossProfit,
      grossMargin,
      totalOpex,
      ebitda,
      ebitdaMargin,
      netIncome,
      netMargin,
      endingCash,
      avgMonthlyBurn,
      cashRunwayMonths,
      avgCurrentRatio,
      avgQuickRatio,
      avgDso,
      avgDpo,
      avgDio,
      avgCcc,
    };
  }

  /**
   * Deterministic Break-Even Calculation
   */
  static calculateBreakEven(params: BreakEvenParameters): BreakEvenResult {
    const { sellingPricePerUnit, variableCostPerUnit, monthlyFixedCosts, currentMonthlyUnits, targetMonthlyUnits, targetMonthlyProfit } = params;

    const contributionMarginPerUnit = sellingPricePerUnit - variableCostPerUnit;
    const contributionMarginRatio = sellingPricePerUnit > 0 ? (contributionMarginPerUnit / sellingPricePerUnit) : 0;

    const breakEvenUnits = contributionMarginPerUnit > 0 ? Math.ceil(monthlyFixedCosts / contributionMarginPerUnit) : 0;
    const breakEvenRevenue = breakEvenUnits * sellingPricePerUnit;

    const marginOfSafetyUnits = currentMonthlyUnits - breakEvenUnits;
    const marginOfSafetyRevenue = marginOfSafetyUnits * sellingPricePerUnit;
    const marginOfSafetyPercent = currentMonthlyUnits > 0 ? (marginOfSafetyUnits / currentMonthlyUnits) * 100 : 0;

    const currentProfit = (currentMonthlyUnits * contributionMarginPerUnit) - monthlyFixedCosts;
    const targetVolumeProfit = (targetMonthlyUnits * contributionMarginPerUnit) - monthlyFixedCosts;

    // Generate chart data points
    const maxUnits = Math.max(breakEvenUnits * 1.8, targetMonthlyUnits * 1.3, currentMonthlyUnits * 1.4, 100);
    const step = Math.ceil(maxUnits / 10);
    const chartPoints = [];

    for (let u = 0; u <= maxUnits; u += step) {
      const revenue = u * sellingPricePerUnit;
      const totalCosts = monthlyFixedCosts + (u * variableCostPerUnit);
      chartPoints.push({
        units: u,
        revenue,
        totalCosts,
        fixedCosts: monthlyFixedCosts,
      });
    }

    return {
      contributionMarginPerUnit,
      contributionMarginRatio,
      breakEvenUnits,
      breakEvenRevenue,
      marginOfSafetyUnits,
      marginOfSafetyRevenue,
      marginOfSafetyPercent,
      currentProfit,
      targetVolumeProfit,
      chartPoints,
    };
  }

  /**
   * Helper formatting functions
   */
  static formatCurrency(amount: number, currency: string = 'USD', compact: boolean = false): string {
    const symbolMap: Record<string, string> = {
      USD: '$',
      EUR: '€',
      GBP: '£',
      CAD: 'C$',
      AUD: 'A$',
      INR: '₹',
      SGD: 'S$',
    };
    const sym = symbolMap[currency] || '$';
    
    if (compact) {
      if (Math.abs(amount) >= 1_000_000) {
        return `${sym}${(amount / 1_000_000).toFixed(2)}M`;
      }
      if (Math.abs(amount) >= 1_000) {
        return `${sym}${(amount / 1_000).toFixed(1)}k`;
      }
    }

    return `${sym}${new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 0,
      minimumFractionDigits: 0,
    }).format(amount)}`;
  }

  static formatPercent(value: number, decimals: number = 1): string {
    return `${value >= 0 ? '' : ''}${value.toFixed(decimals)}%`;
  }
}
