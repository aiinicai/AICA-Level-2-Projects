import {
  MonthlyFinancialRecord,
  ScenarioDrivers,
  ScenarioResult,
  FinancialModel,
  WeeklyCashForecastItem,
  MonthlyCashForecastItem,
  SensitivityMatrixData,
  SensitivityMatrixCell,
  BudgetForecastBasisConfig,
  ClientProfile,
} from '../types';

export class ForecastingEngine {
  /**
   * Generates tailored default budget/forecast basis configuration based on client industry & profile
   */
  static getDefaultBasisConfig(client: ClientProfile): BudgetForecastBasisConfig {
    const isMedical = client.industry === 'medical';
    const isRestaurant = client.industry === 'restaurant';
    const isSaas = client.industry === 'saas';

    return {
      name: `${client.name} Strategic Plan Basis`,
      description: 'Dynamic multi-driver driver-based forecast model with headcount, gross margin target, and working capital optimization.',
      revenueBasis: {
        method: isSaas ? 'mrr_waterfall' : isMedical ? 'headcount_capacity' : isRestaurant ? 'unit_economics' : 'growth_rate',
        growthRatePercent: isSaas ? 22.0 : isMedical ? 12.0 : 8.5,
        revenuePerFte: isMedical ? 210000 : isSaas ? 280000 : 125000,
        targetHeadcount: client.headcount || 24,
        unitVolumeMonthly: 1200,
        averageOrderValue: 450,
        startingMrr: 120000,
        mrrGrowthPercent: 3.5,
        mrrChurnPercent: 1.2,
        mrrExpansionPercent: 2.0,
      },
      grossMarginBasis: {
        method: 'target_margin_pct',
        targetGrossMarginPercent: isMedical ? 70.0 : isRestaurant ? 64.0 : 78.0,
        directLaborPercentOfRevenue: 18.0,
        directMaterialsPercentOfRevenue: 12.0,
        supplierVolumeDiscountPercent: 2.0,
      },
      opexBasis: {
        payrollCostOfLivingAdjustmentPercent: 3.5,
        payrollTaxBenefitLoadMultiplier: 1.22,
        plannedNewHires: [
          { id: 'hire_1', role: isMedical ? 'Lead Practitioner' : 'Senior Specialist', department: isMedical ? 'Clinical' : 'Operations', annualSalary: 110000, startMonth: 3 },
          { id: 'hire_2', role: 'Operations Associate', department: 'Operations', annualSalary: 65000, startMonth: 6 },
        ],
        marketingMethod: 'percent_of_revenue',
        marketingPercentOfRevenue: 5.5,
        marketingFixedMonthly: 25000,
        targetCac: 380,
        targetNewCustomersMonthly: 40,
        rentLeaseEscalationPercent: 3.0,
        generalAdminInflationPercent: 3.0,
        gnaRevenueScalingStepPercent: 1.5,
      },
      workingCapitalBasis: {
        targetDsoDays: 32,
        targetDpoDays: 28,
        targetDioDays: 20,
        minimumCashReserveMonths: 3.0,
      },
      seasonalityWeights: [0.94, 0.96, 1.02, 1.01, 1.05, 1.08, 0.98, 0.96, 1.02, 1.04, 1.00, 0.94], // 12-month curve
    };
  }

  /**
   * Project 12-Month Rolling Forecast using detailed mathematical driver basis
   */
  static project12MonthsWithBasis(
    model: FinancialModel,
    basisConfig?: BudgetForecastBasisConfig
  ): ScenarioResult {
    const historical = model.historicalMonthly;
    if (!historical || historical.length === 0) {
      return this.project12Months([], {
        name: 'Empty',
        revenueGrowthRateDelta: 0,
        grossMarginDelta: 0,
        priceAdjustmentPercent: 0,
        headcountDelta: 0,
        averageSalaryNewHires: 0,
        marketingBudgetDeltaMonthly: 0,
        opexInflationPercent: 0,
        dsoImprovementDays: 0,
        dpoExtensionDays: 0,
      });
    }

    const config = basisConfig || model.budgetBasisConfig || this.getDefaultBasisConfig(model.client);
    const latest = historical[historical.length - 1];
    let runningCash = latest.endingCash || latest.cashAndEquivalents || 500000;

    const monthNames = ['Sep 2026', 'Oct 2026', 'Nov 2026', 'Dec 2026', 'Jan 2027', 'Feb 2027', 'Mar 2027', 'Apr 2027', 'May 2027', 'Jun 2027', 'Jul 2027', 'Aug 2027'];
    const monthlyProjections = [];

    let projectedAnnualRev = 0;
    let projectedAnnualGp = 0;
    let projectedAnnualEbitda = 0;
    let projectedAnnualNetIncome = 0;

    const baseMonthlyRev = latest.revenue;
    let currentMrr = config.revenueBasis.startingMrr || (baseMonthlyRev * 0.7);

    for (let i = 0; i < 12; i++) {
      const monthIdx = i + 1;
      const seasonWeight = config.seasonalityWeights[i] || 1.0;

      // 1. Calculate Monthly Revenue based on Method
      let monthlyRevenue = baseMonthlyRev;
      if (config.revenueBasis.method === 'growth_rate') {
        const annualRate = config.revenueBasis.growthRatePercent / 100;
        monthlyRevenue = baseMonthlyRev * (1 + (annualRate * (monthIdx / 12))) * seasonWeight;
      } else if (config.revenueBasis.method === 'headcount_capacity') {
        // Capacity = (Base headcount + active new hires) * (rev per FTE / 12)
        const activeNewHires = config.opexBasis.plannedNewHires.filter(h => h.startMonth <= monthIdx).length;
        const totalHeadcount = (config.revenueBasis.targetHeadcount || 20) + activeNewHires;
        const baseCapacityRev = (totalHeadcount * config.revenueBasis.revenuePerFte) / 12;
        monthlyRevenue = baseCapacityRev * seasonWeight;
      } else if (config.revenueBasis.method === 'unit_economics') {
        const units = config.revenueBasis.unitVolumeMonthly * (1 + (0.015 * monthIdx));
        monthlyRevenue = units * config.revenueBasis.averageOrderValue * seasonWeight;
      } else if (config.revenueBasis.method === 'mrr_waterfall') {
        const netGrowthPct = (config.revenueBasis.mrrGrowthPercent + config.revenueBasis.mrrExpansionPercent - config.revenueBasis.mrrChurnPercent) / 100;
        currentMrr = currentMrr * (1 + netGrowthPct);
        monthlyRevenue = (currentMrr + (baseMonthlyRev * 0.3)) * seasonWeight;
      } else if (config.revenueBasis.method === 'custom_targets' && config.revenueBasis.monthlyTargetValues?.[i]) {
        monthlyRevenue = config.revenueBasis.monthlyTargetValues[i];
      } else {
        monthlyRevenue = baseMonthlyRev * (1 + ((config.revenueBasis.growthRatePercent || 8) / 100) * (monthIdx / 12));
      }

      // 2. Calculate Gross Profit & COGS based on Method
      let monthlyGrossProfit = 0;
      let monthlyCogs = 0;
      if (config.grossMarginBasis.method === 'target_margin_pct') {
        const targetMargin = Math.max(10, Math.min(95, config.grossMarginBasis.targetGrossMarginPercent)) / 100;
        monthlyGrossProfit = monthlyRevenue * targetMargin;
        monthlyCogs = monthlyRevenue - monthlyGrossProfit;
      } else if (config.grossMarginBasis.method === 'direct_cogs_breakdown') {
        const laborCost = monthlyRevenue * (config.grossMarginBasis.directLaborPercentOfRevenue / 100);
        const materialsCost = monthlyRevenue * (config.grossMarginBasis.directMaterialsPercentOfRevenue / 100);
        monthlyCogs = laborCost + materialsCost;
        monthlyGrossProfit = monthlyRevenue - monthlyCogs;
      } else {
        const baseMargin = latest.grossMarginPercent / 100;
        const volDiscount = (config.grossMarginBasis.supplierVolumeDiscountPercent / 100) * (monthIdx / 12);
        const effectiveMargin = Math.min(0.95, baseMargin + volDiscount);
        monthlyGrossProfit = monthlyRevenue * effectiveMargin;
        monthlyCogs = monthlyRevenue - monthlyGrossProfit;
      }

      // 3. Operating Expenses with Planned Hires and Drivers
      const colaFactor = 1 + ((config.opexBasis.payrollCostOfLivingAdjustmentPercent / 100) * (monthIdx / 12));
      
      // Calculate monthly payroll additions from new hires active in this month
      const activeHires = config.opexBasis.plannedNewHires.filter(h => h.startMonth <= monthIdx);
      const newHireMonthlyPayroll = activeHires.reduce((sum, h) => {
        const loadedMonthlySalary = (h.annualSalary * config.opexBasis.payrollTaxBenefitLoadMultiplier) / 12;
        return sum + loadedMonthlySalary;
      }, 0);

      const baseSalaries = (latest.salariesAndWages * colaFactor) + newHireMonthlyPayroll;

      // Marketing
      let monthlyMarketing = latest.salesAndMarketing;
      if (config.opexBasis.marketingMethod === 'percent_of_revenue') {
        monthlyMarketing = monthlyRevenue * (config.opexBasis.marketingPercentOfRevenue / 100);
      } else if (config.opexBasis.marketingMethod === 'cac_target') {
        monthlyMarketing = config.opexBasis.targetCac * config.opexBasis.targetNewCustomersMonthly;
      } else {
        monthlyMarketing = config.opexBasis.marketingFixedMonthly;
      }

      // Rent & Facilities with Lease Escalation
      const rentEscalationFactor = 1 + ((config.opexBasis.rentLeaseEscalationPercent / 100) * (monthIdx / 12));
      const monthlyRent = latest.rentAndFacilities * rentEscalationFactor;

      // G&A with Inflation & Scaling
      const gnaInflationFactor = 1 + ((config.opexBasis.generalAdminInflationPercent / 100) * (monthIdx / 12));
      const monthlyGna = latest.generalAndAdmin * gnaInflationFactor;

      const monthlyDepreciation = latest.depreciationAndAmort || 10000;
      const monthlyOpex = baseSalaries + monthlyMarketing + monthlyRent + monthlyGna + monthlyDepreciation;

      // 4. EBITDA, Net Income, Cash Flow
      const monthlyEbitda = monthlyGrossProfit - monthlyOpex;
      const monthlyTaxInterest = (latest.interestExpense || 2500) + (monthlyEbitda > 0 ? monthlyEbitda * 0.20 : 0);
      const monthlyNetIncome = monthlyEbitda - monthlyTaxInterest;

      // Working Capital Cash Inflow/Outflow conversion based on target DSO & DPO
      const dsoVariance = (latest.dso - config.workingCapitalBasis.targetDsoDays);
      const dsoCashShift = (monthlyRevenue / 30) * (dsoVariance * 0.1); // progressive collection acceleration
      const netCashFlow = monthlyNetIncome + dsoCashShift;
      runningCash += netCashFlow;

      projectedAnnualRev += monthlyRevenue;
      projectedAnnualGp += monthlyGrossProfit;
      projectedAnnualEbitda += monthlyEbitda;
      projectedAnnualNetIncome += monthlyNetIncome;

      monthlyProjections.push({
        month: monthNames[i] || `Month ${monthIdx}`,
        revenue: Math.round(monthlyRevenue),
        grossProfit: Math.round(monthlyGrossProfit),
        ebitda: Math.round(monthlyEbitda),
        netIncome: Math.round(monthlyNetIncome),
        cogs: Math.round(monthlyCogs),
        opex: Math.round(monthlyOpex),
        cashBalance: Math.max(10000, Math.round(runningCash)),
        netCashFlow: Math.round(netCashFlow),
        headcount: (model.client.headcount || 20) + activeHires.length,
      });
    }

    const avgMonthlyBurn = Math.max(1000, latest.totalOpex - (latest.grossProfit > 0 ? latest.grossProfit : 0));
    const cashRunway = runningCash > 0 && avgMonthlyBurn > 0 ? +(runningCash / avgMonthlyBurn).toFixed(1) : 99;

    return {
      driverConfig: {
        name: config.name,
        revenueGrowthRateDelta: config.revenueBasis.growthRatePercent,
        grossMarginDelta: config.grossMarginBasis.targetGrossMarginPercent - latest.grossMarginPercent,
        priceAdjustmentPercent: 0,
        headcountDelta: config.opexBasis.plannedNewHires.length,
        averageSalaryNewHires: 85000,
        marketingBudgetDeltaMonthly: 0,
        opexInflationPercent: config.opexBasis.generalAdminInflationPercent,
        dsoImprovementDays: latest.dso - config.workingCapitalBasis.targetDsoDays,
        dpoExtensionDays: 0,
      },
      annualRevenue: Math.round(projectedAnnualRev),
      annualGrossProfit: Math.round(projectedAnnualGp),
      annualEbitda: Math.round(projectedAnnualEbitda),
      annualNetIncome: Math.round(projectedAnnualNetIncome),
      endingCash: Math.round(runningCash),
      cashRunwayMonths: cashRunway,
      breakEvenMonthlyRevenue: Math.round((latest.totalOpex / (config.grossMarginBasis.targetGrossMarginPercent / 100))),
      monthlyProjections,
    };
  }

  /**
   * High-level helper for 12-month rolling forecast
   */
  static generateRolling12MonthForecast(model: FinancialModel, customDrivers?: ScenarioDrivers, customBasis?: BudgetForecastBasisConfig) {
    if (customBasis || model.budgetBasisConfig) {
      const basisResult = this.project12MonthsWithBasis(model, customBasis);
      return {
        ...basisResult,
        totalProjectedRevenue: basisResult.annualRevenue,
        totalProjectedGrossProfit: basisResult.annualGrossProfit,
        totalProjectedEbitda: basisResult.annualEbitda,
        totalProjectedCashFlow: basisResult.monthlyProjections.reduce((sum, m) => sum + m.netCashFlow, 0),
        endingCashBalance: basisResult.endingCash,
        runwayMonths: basisResult.cashRunwayMonths,
      };
    }

    const defaultDrivers: ScenarioDrivers = {
      name: 'Base Run-Rate Pro-Forma',
      revenueGrowthRateDelta: 8.0,
      grossMarginDelta: 0.0,
      priceAdjustmentPercent: 0.0,
      headcountDelta: 0,
      averageSalaryNewHires: 85000,
      marketingBudgetDeltaMonthly: 0,
      opexInflationPercent: 3.5,
      dsoImprovementDays: 0,
      dpoExtensionDays: 0,
    };

    const drivers = customDrivers || defaultDrivers;
    const result = this.project12Months(model.historicalMonthly, drivers);

    return {
      ...result,
      totalProjectedRevenue: result.annualRevenue,
      totalProjectedGrossProfit: result.annualGrossProfit,
      totalProjectedEbitda: result.annualEbitda,
      totalProjectedCashFlow: result.monthlyProjections.reduce((sum, m) => sum + m.netCashFlow, 0),
      endingCashBalance: result.endingCash,
      runwayMonths: result.cashRunwayMonths,
    };
  }

  /**
   * Helper for prebuilt scenario presets
   */
  static getPrebuiltScenarios(model: FinancialModel) {
    const presets = this.getPresetScenarios();
    return [
      {
        id: 'base',
        driverConfig: presets.base,
        result: this.project12Months(model.historicalMonthly, presets.base),
      },
      {
        id: 'conservative',
        driverConfig: presets.conservative,
        result: this.project12Months(model.historicalMonthly, presets.conservative),
      },
      {
        id: 'aggressive',
        driverConfig: presets.growth,
        result: this.project12Months(model.historicalMonthly, presets.growth),
      },
    ];
  }

  /**
   * Generate 12-month forecast given historical records and scenario drivers
   */
  static project12Months(
    historical: MonthlyFinancialRecord[],
    drivers: ScenarioDrivers,
    baseMonthIndex: number = 12
  ): ScenarioResult {
    if (!historical || historical.length === 0) {
      return {
        driverConfig: drivers,
        annualRevenue: 0,
        annualGrossProfit: 0,
        annualEbitda: 0,
        annualNetIncome: 0,
        endingCash: 0,
        cashRunwayMonths: 0,
        breakEvenMonthlyRevenue: 0,
        monthlyProjections: [],
      };
    }

    const latest = historical[historical.length - 1];
    let runningCash = latest.endingCash || latest.cashAndEquivalents || 500000;
    
    // Calculate baseline historical monthly averages
    const avgRevenue = historical.reduce((sum, r) => sum + r.revenue, 0) / historical.length;
    const avgGrossMargin = historical.reduce((sum, r) => sum + r.grossMarginPercent, 0) / historical.length;
    const avgOpex = historical.reduce((sum, r) => sum + r.totalOpex, 0) / historical.length;
    
    const monthlyProjections = [];
    const monthNames = ['Sep 2026', 'Oct 2026', 'Nov 2026', 'Dec 2026', 'Jan 2027', 'Feb 2027', 'Mar 2027', 'Apr 2027', 'May 2027', 'Jun 2027', 'Jul 2027', 'Aug 2027'];

    let projectedAnnualRev = 0;
    let projectedAnnualGp = 0;
    let projectedAnnualEbitda = 0;
    let projectedAnnualNetIncome = 0;

    const baseMonthlyRev = latest.revenue || avgRevenue;
    const effectiveGrossMargin = Math.max(5, Math.min(95, (latest.grossMarginPercent || avgGrossMargin) + drivers.grossMarginDelta));
    
    // Headcount addition cost monthly
    const additionalPayrollMonthly = (drivers.headcountDelta * (drivers.averageSalaryNewHires || 80000)) / 12;

    for (let i = 0; i < 12; i++) {
      // Compound monthly growth from baseline
      const growthFactor = 1 + ((drivers.revenueGrowthRateDelta + drivers.priceAdjustmentPercent) / 100) * ((i + 1) / 12);
      const monthlyRevenue = baseMonthlyRev * growthFactor;
      
      const monthlyGrossProfit = monthlyRevenue * (effectiveGrossMargin / 100);
      const monthlyCogs = monthlyRevenue - monthlyGrossProfit;

      // Base OPEX + inflation + marketing delta + new payroll additions
      const opexInflationFactor = 1 + (drivers.opexInflationPercent / 100) * ((i + 1) / 12);
      const monthlyOpex = (latest.totalOpex * opexInflationFactor) + drivers.marketingBudgetDeltaMonthly + additionalPayrollMonthly;

      const monthlyEbitda = monthlyGrossProfit - monthlyOpex;
      const monthlyInterestTax = (latest.interestExpense || 2000) + (monthlyEbitda > 0 ? monthlyEbitda * 0.20 : 0);
      const monthlyNetIncome = monthlyEbitda - monthlyInterestTax;

      // Working capital cash flow effect (DSO improvement speeds up cash; DPO extension preserves cash)
      const dsoCashEffect = (monthlyRevenue / 30) * (drivers.dsoImprovementDays || 0); // e.g. -5 days DSO brings in cash
      const netCashFlow = monthlyNetIncome + dsoCashEffect;
      runningCash += netCashFlow;

      projectedAnnualRev += monthlyRevenue;
      projectedAnnualGp += monthlyGrossProfit;
      projectedAnnualEbitda += monthlyEbitda;
      projectedAnnualNetIncome += monthlyNetIncome;

      monthlyProjections.push({
        month: monthNames[i] || `Month ${i + 1}`,
        revenue: Math.round(monthlyRevenue),
        cogs: Math.round(monthlyCogs),
        grossProfit: Math.round(monthlyGrossProfit),
        totalOpex: Math.round(monthlyOpex),
        ebitda: Math.round(monthlyEbitda),
        netIncome: Math.round(monthlyNetIncome),
        cashBalance: Math.round(runningCash),
        netCashFlow: Math.round(netCashFlow),
      });
    }

    // Monthly burn rate for runway calculation
    const negativeMonths = monthlyProjections.filter(m => m.netCashFlow < 0);
    const avgProjectedMonthlyBurn = negativeMonths.length > 0
      ? Math.abs(negativeMonths.reduce((s, m) => s + m.netCashFlow, 0) / negativeMonths.length)
      : 0;

    const cashRunwayMonths = avgProjectedMonthlyBurn > 0
      ? Math.round((runningCash / avgProjectedMonthlyBurn) * 10) / 10
      : 99;

    const avgMonthlyFixedCosts = (latest.totalOpex || avgOpex) + drivers.marketingBudgetDeltaMonthly + additionalPayrollMonthly;
    const breakEvenMonthlyRevenue = effectiveGrossMargin > 0
      ? Math.round(avgMonthlyFixedCosts / (effectiveGrossMargin / 100))
      : 0;

    return {
      driverConfig: drivers,
      annualRevenue: Math.round(projectedAnnualRev),
      annualGrossProfit: Math.round(projectedAnnualGp),
      annualEbitda: Math.round(projectedAnnualEbitda),
      annualNetIncome: Math.round(projectedAnnualNetIncome),
      endingCash: Math.round(runningCash),
      cashRunwayMonths,
      breakEvenMonthlyRevenue,
      monthlyProjections,
    };
  }

  /**
   * Generates a 2D Multi-Variable Sensitivity Matrix & Heat Map Data
   * Allows simultaneous testing of Revenue Delta vs OpEx / COGS Delta
   */
  static generateSensitivityMatrix(
    model: FinancialModel,
    mode: 'rev_vs_opex' | 'rev_vs_cogs' | 'price_vs_volume' = 'rev_vs_opex',
    baseDrivers?: ScenarioDrivers
  ): SensitivityMatrixData {
    const historical = model.historicalMonthly;
    const latest = historical.length > 0 ? historical[historical.length - 1] : null;
    const baseRevenue = latest ? latest.revenue * 12 : 5000000;
    const baseMargin = latest ? latest.grossMarginPercent : 45;
    const baseOpex = latest ? latest.totalOpex * 12 : 1400000;

    let rowAxisName = 'Revenue Delta';
    let colAxisName = 'OpEx Delta';
    let rowUnit = '%';
    let colUnit = '%';
    let rowValues = [-15, -10, -5, 0, 5, 10, 15];
    let colValues = [-10, -5, 0, 5, 10, 15];

    if (mode === 'rev_vs_cogs') {
      rowAxisName = 'Revenue Growth';
      colAxisName = 'Gross Margin Shift';
      rowUnit = '%';
      colUnit = 'pts';
      rowValues = [-15, -10, -5, 0, 5, 10, 15];
      colValues = [-6, -3, 0, 3, 6];
    } else if (mode === 'price_vs_volume') {
      rowAxisName = 'Price Adjustment';
      colAxisName = 'Volume / Demand Growth';
      rowUnit = '%';
      colUnit = '%';
      rowValues = [-10, -5, 0, 5, 10];
      colValues = [-15, -10, -5, 0, 5, 10, 15];
    }

    let minNetIncome = Number.MAX_SAFE_INTEGER;
    let maxNetIncome = Number.MIN_SAFE_INTEGER;
    let baseNetIncome = 0;

    const grid: SensitivityMatrixCell[][] = [];

    for (let r = 0; r < rowValues.length; r++) {
      const rowVal = rowValues[r];
      const rowCells: SensitivityMatrixCell[] = [];

      for (let c = 0; c < colValues.length; c++) {
        const colVal = colValues[c];
        let calcRev = baseRevenue;
        let calcGrossMargin = baseMargin;
        let calcOpex = baseOpex;

        if (mode === 'rev_vs_opex') {
          calcRev = baseRevenue * (1 + rowVal / 100);
          calcOpex = baseOpex * (1 + colVal / 100);
        } else if (mode === 'rev_vs_cogs') {
          calcRev = baseRevenue * (1 + rowVal / 100);
          calcGrossMargin = Math.max(5, Math.min(95, baseMargin + colVal));
        } else if (mode === 'price_vs_volume') {
          // Price affects revenue 100% without increasing COGS; Volume affects revenue & COGS proportionally
          const priceMultiplier = 1 + rowVal / 100;
          const volumeMultiplier = 1 + colVal / 100;
          calcRev = baseRevenue * priceMultiplier * volumeMultiplier;
        }

        const calcGrossProfit = calcRev * (calcGrossMargin / 100);
        const calcCogs = calcRev - calcGrossProfit;
        const calcEbitda = calcGrossProfit - calcOpex;
        const taxAndInterest = calcEbitda > 0 ? calcEbitda * 0.22 + 25000 : 25000;
        const calcNetIncome = calcEbitda - taxAndInterest;
        const calcNetMargin = calcRev > 0 ? (calcNetIncome / calcRev) * 100 : 0;
        const endingCash = (latest?.endingCash || 400000) + calcNetIncome;

        const isBaseline = rowVal === 0 && colVal === 0;
        if (isBaseline) {
          baseNetIncome = calcNetIncome;
        }

        if (calcNetIncome < minNetIncome) minNetIncome = calcNetIncome;
        if (calcNetIncome > maxNetIncome) maxNetIncome = calcNetIncome;

        rowCells.push({
          rowValue: rowVal,
          colValue: colVal,
          revenue: Math.round(calcRev),
          grossProfit: Math.round(calcGrossProfit),
          cogs: Math.round(calcCogs),
          opex: Math.round(calcOpex),
          ebitda: Math.round(calcEbitda),
          netIncome: Math.round(calcNetIncome),
          netMarginPercent: Math.round(calcNetMargin * 10) / 10,
          endingCash: Math.round(endingCash),
          isBaseline,
          isActiveSelection: false,
        });
      }
      grid.push(rowCells);
    }

    return {
      rowAxisName,
      colAxisName,
      rowUnit,
      colUnit,
      rowValues,
      colValues,
      grid,
      minNetIncome: Math.round(minNetIncome),
      maxNetIncome: Math.round(maxNetIncome),
      baseNetIncome: Math.round(baseNetIncome),
    };
  }

  /**
   * Generates a 13-Week Rolling Direct Cash Flow Forecast
   */
  static generate13WeekCashForecast(
    model: FinancialModel,
    drivers?: {
      revenueGrowthDelta?: number;
      dsoCollectionSpeed?: number;
      plannedCapexWeek?: number;
      plannedCapexAmount?: number;
      minCashBuffer?: number;
    }
  ): {
    weeks: WeeklyCashForecastItem[];
    summary: {
      initialCash: number;
      endingCash: number;
      troughCash: number;
      troughWeekIndex: number;
      totalInflows13W: number;
      totalOutflows13W: number;
      netCashGeneration13W: number;
      averageWeeklyBurn: number;
      weeksBelowThreshold: number;
      minCashThreshold: number;
    };
  } {
    const historical = model.historicalMonthly;
    const latest = historical.length > 0 ? historical[historical.length - 1] : null;
    
    const initialCash = latest?.cashAndEquivalents || latest?.endingCash || 450000;
    const monthlyRev = latest?.revenue || 400000;
    const monthlyOpex = latest?.totalOpex || 120000;
    const monthlyCogs = latest ? latest.revenue - latest.grossProfit : 180000;
    
    const minThreshold = drivers?.minCashBuffer || Math.round(monthlyOpex * 1.5); // 1.5 months safe buffer
    
    // Average weekly base flows
    const weeklyRevBase = (monthlyRev / 4.33) * (1 + (drivers?.revenueGrowthDelta || 0) / 100);
    const weeklyCogsBase = monthlyCogs / 4.33;
    const weeklyOpexBase = monthlyOpex / 4.33;
    const weeklyPayrollBase = weeklyOpexBase * 0.65; // 65% of OPEX is payroll
    const weeklyGnA = weeklyOpexBase * 0.35;

    let currentCash = initialCash;
    const weeks: WeeklyCashForecastItem[] = [];
    
    let troughCash = initialCash;
    let troughWeekIndex = 1;
    let totalInflows13W = 0;
    let totalOutflows13W = 0;
    let weeksBelowCount = 0;

    // Generate 13 weeks starting from current date
    const baseDate = new Date();

    for (let w = 1; w <= 13; w++) {
      const weekStartDate = new Date(baseDate.getTime() + (w - 1) * 7 * 24 * 60 * 60 * 1000);
      const dateString = weekStartDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      
      const begCash = currentCash;

      // Seasonal / cadence weighting
      // Bi-weekly payroll spike on even weeks (Weeks 2, 4, 6, 8, 10, 12)
      const isPayrollWeek = w % 2 === 0;
      const payrollAndBenefits = isPayrollWeek ? Math.round(weeklyPayrollBase * 2.05) : Math.round(weeklyPayrollBase * 0.15);

      // Monthly Rent & Facility overhead on Weeks 1, 5, 9, 13
      const isRentWeek = w === 1 || w === 5 || w === 9 || w === 13;
      const rentAndFacilities = isRentWeek ? Math.round(weeklyGnA * 1.8) : 0;

      // Quarterly Tax / Statutory payment in Week 7 or 8
      const isTaxWeek = w === 8;
      const taxAndStatutory = isTaxWeek ? Math.round(monthlyRev * 0.08) : Math.round(weeklyRevBase * 0.015);

      // Debt service / Loan installments in Week 3, 7, 11
      const isDebtWeek = w === 3 || w === 7 || w === 11;
      const debtService = isDebtWeek ? Math.round(monthlyOpex * 0.08) : 0;

      // CapEx Outlay (default or user specified)
      const capexOutlays = (drivers?.plannedCapexWeek === w && drivers?.plannedCapexAmount) ? drivers.plannedCapexAmount : (w === 6 ? 25000 : 0);

      // AR Collections & Inflow timing (with random natural variance + DSO accelerator)
      const dsoSpeedFactor = 1 + (drivers?.dsoCollectionSpeed || 0) * 0.02;
      const arCollections = Math.round(weeklyRevBase * 0.78 * (0.92 + (w % 4) * 0.05) * dsoSpeedFactor);
      const cashSales = Math.round(weeklyRevBase * 0.22);
      const otherInflows = w === 4 || w === 10 ? Math.round(weeklyRevBase * 0.05) : 0;
      const totalInflows = arCollections + cashSales + otherInflows;

      // Supplier / COGS Payments (extended term rhythm)
      const cogsSupplierPayments = Math.round(weeklyCogsBase * (0.85 + ((w + 1) % 3) * 0.12));
      const operatingExpenses = Math.round(weeklyGnA * (isRentWeek ? 0.4 : 1.0));

      const totalOutflows = payrollAndBenefits + cogsSupplierPayments + rentAndFacilities + operatingExpenses + taxAndStatutory + debtService + capexOutlays;

      const netCashFlow = totalInflows - totalOutflows;
      currentCash += netCashFlow;

      if (currentCash < troughCash) {
        troughCash = currentCash;
        troughWeekIndex = w;
      }

      const isBelowThreshold = currentCash < minThreshold;
      if (isBelowThreshold) {
        weeksBelowCount++;
      }

      totalInflows13W += totalInflows;
      totalOutflows13W += totalOutflows;

      // Estimated runway in weeks based on current week outflow
      const runwayWeeks = totalOutflows > 0 ? Math.round((currentCash / totalOutflows) * 10) / 10 : 99;

      weeks.push({
        weekNumber: w,
        weekLabel: `W${w} (${dateString})`,
        startDate: dateString,
        beginningCash: Math.round(begCash),
        arCollections,
        cashSales,
        otherInflows,
        totalInflows,
        payrollAndBenefits,
        cogsSupplierPayments,
        rentAndFacilities,
        operatingExpenses,
        taxAndStatutory,
        debtService,
        capexOutlays,
        totalOutflows,
        netCashFlow,
        endingCash: Math.round(currentCash),
        minCashThreshold: minThreshold,
        isBelowThreshold,
        runwayWeeks,
      });
    }

    const netCashGeneration13W = totalInflows13W - totalOutflows13W;
    const averageWeeklyBurn = (totalOutflows13W - totalInflows13W) > 0 ? Math.round((totalOutflows13W - totalInflows13W) / 13) : 0;

    return {
      weeks,
      summary: {
        initialCash: Math.round(initialCash),
        endingCash: Math.round(currentCash),
        troughCash: Math.round(troughCash),
        troughWeekIndex,
        totalInflows13W: Math.round(totalInflows13W),
        totalOutflows13W: Math.round(totalOutflows13W),
        netCashGeneration13W: Math.round(netCashGeneration13W),
        averageWeeklyBurn,
        weeksBelowThreshold: weeksBelowCount,
        minCashThreshold: minThreshold,
      },
    };
  }

  /**
   * Generates a 12-Month Pro-Forma Direct & Indirect Monthly Cash Flow Schedule
   */
  static generate12MonthCashForecast(
    model: FinancialModel,
    drivers?: ScenarioDrivers
  ): {
    months: MonthlyCashForecastItem[];
    summary: {
      beginningCash: number;
      endingCash: number;
      minCashMonth: string;
      minCashValue: number;
      totalNetCashFlow: number;
      averageMonthlyBurn: number;
      cashRunwayMonths: number;
    };
  } {
    const historical = model.historicalMonthly;
    const latest = historical.length > 0 ? historical[historical.length - 1] : null;
    let runningCash = latest?.cashAndEquivalents || latest?.endingCash || 450000;
    const initialCash = runningCash;

    const rolling12M = this.generateRolling12MonthForecast(model, drivers);
    const months: MonthlyCashForecastItem[] = [];

    let minCashValue = runningCash;
    let minCashMonth = 'Month 1';
    let totalBurn = 0;
    let burnMonthsCount = 0;

    rolling12M.monthlyProjections.forEach((m, idx) => {
      const begCash = runningCash;
      const operatingInflows = Math.round(m.revenue * 0.98);
      const operatingOutflows = Math.round((m.cogs || m.revenue * 0.55) + (m.totalOpex || m.revenue * 0.30));
      const netOperating = operatingInflows - operatingOutflows;
      
      const capex = idx === 3 || idx === 8 ? 35000 : 5000;
      const debtFinancing = 8000;
      const tax = m.ebitda > 0 ? Math.round(m.ebitda * 0.20) : 2000;

      const netCash = netOperating - capex - debtFinancing - tax;
      runningCash += netCash;

      if (runningCash < minCashValue) {
        minCashValue = runningCash;
        minCashMonth = m.month;
      }

      if (netCash < 0) {
        totalBurn += Math.abs(netCash);
        burnMonthsCount++;
      }

      const burnRate = netCash < 0 ? Math.abs(netCash) : 0;
      const runway = burnRate > 0 ? Math.round((runningCash / burnRate) * 10) / 10 : 99;

      months.push({
        monthIndex: idx + 1,
        monthLabel: m.month,
        beginningCash: Math.round(begCash),
        operatingCashInflows: operatingInflows,
        operatingCashOutflows: operatingOutflows,
        netOperatingCash: netOperating,
        capexAndInvesting: capex,
        financingAndDebt: debtFinancing,
        taxPayments: tax,
        netCashFlow: netCash,
        endingCash: Math.round(runningCash),
        burnRate,
        cashRunwayMonths: runway,
        isNegative: netCash < 0,
      });
    });

    const avgMonthlyBurn = burnMonthsCount > 0 ? Math.round(totalBurn / burnMonthsCount) : 0;
    const finalRunway = avgMonthlyBurn > 0 ? Math.round((runningCash / avgMonthlyBurn) * 10) / 10 : 99;

    return {
      months,
      summary: {
        beginningCash: Math.round(initialCash),
        endingCash: Math.round(runningCash),
        minCashMonth,
        minCashValue: Math.round(minCashValue),
        totalNetCashFlow: Math.round(runningCash - initialCash),
        averageMonthlyBurn: avgMonthlyBurn,
        cashRunwayMonths: finalRunway,
      },
    };
  }

  static getPresetScenarios(): Record<string, ScenarioDrivers> {
    return {
      base: {
        name: 'Base Case (Status Quo)',
        revenueGrowthRateDelta: 5.0,
        grossMarginDelta: 0.0,
        priceAdjustmentPercent: 0.0,
        headcountDelta: 0,
        averageSalaryNewHires: 85000,
        marketingBudgetDeltaMonthly: 0,
        opexInflationPercent: 3.0,
        dsoImprovementDays: 0,
        dpoExtensionDays: 0,
      },
      conservative: {
        name: 'Conservative (Downside)',
        revenueGrowthRateDelta: -6.0,
        grossMarginDelta: -2.5,
        priceAdjustmentPercent: -2.0,
        headcountDelta: -1,
        averageSalaryNewHires: 75000,
        marketingBudgetDeltaMonthly: -3000,
        opexInflationPercent: 5.0,
        dsoImprovementDays: -5, // collections drag
        dpoExtensionDays: 0,
      },
      growth: {
        name: 'Aggressive Growth (Upside)',
        revenueGrowthRateDelta: 16.0,
        grossMarginDelta: 2.0,
        priceAdjustmentPercent: 5.0,
        headcountDelta: 3,
        averageSalaryNewHires: 90000,
        marketingBudgetDeltaMonthly: 12000,
        opexInflationPercent: 4.0,
        dsoImprovementDays: 8, // faster collection
        dpoExtensionDays: 5,
      },
      hiringPlan: {
        name: 'Expansion & Capacity Hiring',
        revenueGrowthRateDelta: 12.0,
        grossMarginDelta: 1.0,
        priceAdjustmentPercent: 3.0,
        headcountDelta: 5,
        averageSalaryNewHires: 85000,
        marketingBudgetDeltaMonthly: 8000,
        opexInflationPercent: 3.5,
        dsoImprovementDays: 3,
        dpoExtensionDays: 2,
      },
    };
  }
}

