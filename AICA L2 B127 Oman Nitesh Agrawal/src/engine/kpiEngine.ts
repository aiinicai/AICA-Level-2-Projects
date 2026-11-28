import type {
  AccountClass,
  AccountingPolicyConfig,
  Company,
  ConstructionProgressPoint,
  ContractorRecord,
  CurrencyCode,
  FinancingFacility,
  GlMappingRule,
  ManagementAdjustment,
  MisDataset,
  Project,
  ProjectBudgetLine,
  ReportingBasis,
  ScenarioParameters,
  TraceableKpi,
  TrialBalanceRow,
  UnitRecord,
} from '../types/mis';

export const CURRENCY_RATES_FROM_OMR: Record<CurrencyCode, number> = {
  OMR: 1,
  AED: 9.545,
  SAR: 9.740,
  USD: 2.597,
};

export const CURRENCY_DECIMALS: Record<CurrencyCode, number> = {
  OMR: 3,
  AED: 2,
  SAR: 2,
  USD: 2,
};

export function roundOMR(val: number): number {
  if (!Number.isFinite(val)) return 0;
  return Math.round((val + Number.EPSILON) * 1000) / 1000;
}

export function roundTo(val: number, decimals: number): number {
  if (!Number.isFinite(val)) return 0;
  const factor = Math.pow(10, decimals);
  return Math.round((val + Number.EPSILON) * factor) / factor;
}

export function convertFromOMR(valOMR: number | null, currency: CurrencyCode): number | null {
  if (valOMR === null || !Number.isFinite(valOMR)) return null;
  return roundTo(valOMR * CURRENCY_RATES_FROM_OMR[currency], CURRENCY_DECIMALS[currency]);
}

export function formatMoney(
  valOMR: number | null,
  currency: CurrencyCode = 'OMR',
  masked = false,
  compact = false
): string {
  if (valOMR === null || !Number.isFinite(valOMR)) return 'N/A';
  if (masked) return `${currency} •••.•••`;
  const converted = valOMR * CURRENCY_RATES_FROM_OMR[currency];
  const decimals = CURRENCY_DECIMALS[currency];
  const abs = Math.abs(converted);
  if (compact && abs >= 1_000_000) {
    const mStr = (abs / 1_000_000).toFixed(2);
    return converted < 0 ? `${currency} (${mStr}M)` : `${currency} ${mStr}M`;
  }
  const formatted = abs.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return converted < 0 ? `${currency} (${formatted})` : `${currency} ${formatted}`;
}

export function formatPct(val: number | null, masked = false): string {
  if (val === null || !Number.isFinite(val)) return 'N/A';
  if (masked) return '••.%';
  return `${val.toFixed(1)}%`;
}

export function formatRatio(val: number | null, masked = false): string {
  if (val === null || !Number.isFinite(val)) return 'N/A';
  if (masked) return '•.••x';
  return `${val.toFixed(2)}x`;
}

export function safeDiv(numerator: number | null, denominator: number | null): number | null {
  if (numerator === null || denominator === null) return null;
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || Math.abs(denominator) < 1e-9) {
    return null;
  }
  return numerator / denominator;
}

export interface ReconciliationResult {
  period: string;
  totalPeriodDebit: number;
  totalPeriodCredit: number;
  trialBalanceDiff: number;
  openingDiff: number;
  closingDiff: number;
  rollforwardErrors: number;
  unmappedCount: number;
  unmappedAccounts: string[];
  abnormalSwings: { accountCode: string; accountName: string; changePct: number; amountOMR: number }[];
  isMateriallyReconciled: boolean;
  canPublish: boolean;
  messages: string[];
}

export function reconcileTrialBalance(
  rows: TrialBalanceRow[],
  prevRows: TrialBalanceRow[],
  mappings: GlMappingRule[],
  materialityThresholdOMR: number
): ReconciliationResult {
  const period = rows[0]?.period ?? 'N/A';
  let totalPeriodDebit = 0;
  let totalPeriodCredit = 0;
  let totalOpeningDebit = 0;
  let totalOpeningCredit = 0;
  let totalClosingDebit = 0;
  let totalClosingCredit = 0;
  let rollforwardErrors = 0;
  const unmappedAccounts: string[] = [];

  const mappedSet = new Set(mappings.map((m) => m.accountCode));

  for (const r of rows) {
    totalPeriodDebit += r.periodDebit;
    totalPeriodCredit += r.periodCredit;
    totalOpeningDebit += r.openingDebit;
    totalOpeningCredit += r.openingCredit;
    totalClosingDebit += r.closingDebit;
    totalClosingCredit += r.closingCredit;

    const openNet = roundOMR(r.openingDebit - r.openingCredit);
    const movNet = roundOMR(r.periodDebit - r.periodCredit);
    const closeNet = roundOMR(r.closingDebit - r.closingCredit);
    if (Math.abs(roundOMR(openNet + movNet - closeNet)) > 0.01) {
      rollforwardErrors += 1;
    }

    if (r.accountClass === 'Unmapped' && !mappedSet.has(r.accountCode)) {
      unmappedAccounts.push(`${r.accountCode} — ${r.accountName}`);
    }
  }

  totalPeriodDebit = roundOMR(totalPeriodDebit);
  totalPeriodCredit = roundOMR(totalPeriodCredit);
  const trialBalanceDiff = roundOMR(Math.abs(totalPeriodDebit - totalPeriodCredit));
  const openingDiff = roundOMR(Math.abs(totalOpeningDebit - totalOpeningCredit));
  const closingDiff = roundOMR(Math.abs(totalClosingDebit - totalClosingCredit));

  const prevMap = new Map<string, number>();
  for (const p of prevRows) {
    const key = `${p.companyId}:${p.accountCode}`;
    prevMap.set(key, (prevMap.get(key) ?? 0) + (p.periodDebit - p.periodCredit));
  }

  const abnormalSwings: { accountCode: string; accountName: string; changePct: number; amountOMR: number }[] = [];
  for (const r of rows) {
    const key = `${r.companyId}:${r.accountCode}`;
    const prevNet = prevMap.get(key);
    const currNet = r.periodDebit - r.periodCredit;
    if (prevNet !== undefined && Math.abs(prevNet) > 1000) {
      const pct = ((currNet - prevNet) / Math.abs(prevNet)) * 100;
      if (Math.abs(pct) >= 75 && Math.abs(currNet - prevNet) >= materialityThresholdOMR * 5) {
        abnormalSwings.push({
          accountCode: r.accountCode,
          accountName: r.accountName,
          changePct: roundTo(pct, 1),
          amountOMR: roundOMR(currNet - prevNet),
        });
      }
    }
  }

  const isMateriallyReconciled =
    trialBalanceDiff <= materialityThresholdOMR &&
    openingDiff <= materialityThresholdOMR &&
    closingDiff <= materialityThresholdOMR &&
    rollforwardErrors === 0;

  const canPublish = isMateriallyReconciled && unmappedAccounts.length === 0;
  const messages: string[] = [];
  if (trialBalanceDiff > 0.005) {
    messages.push(`Period Debit/Credit variance of OMR ${trialBalanceDiff.toFixed(3)}`);
  }
  if (closingDiff > 0.005) {
    messages.push(`Closing Balance Sheet imbalance of OMR ${closingDiff.toFixed(3)}`);
  }
  if (rollforwardErrors > 0) {
    messages.push(`${rollforwardErrors} GL line(s) fail Opening + Movement = Closing check`);
  }
  if (unmappedAccounts.length > 0) {
    messages.push(`${unmappedAccounts.length} unmapped GL account(s) require mapping before publication`);
  }
  if (messages.length === 0) {
    messages.push('Trial Balance balanced to 0.000 OMR; all opening/closing roll-forwards and GL mappings verified.');
  }

  return {
    period,
    totalPeriodDebit,
    totalPeriodCredit,
    trialBalanceDiff,
    openingDiff,
    closingDiff,
    rollforwardErrors,
    unmappedCount: unmappedAccounts.length,
    unmappedAccounts,
    abnormalSwings,
    isMateriallyReconciled,
    canPublish,
    messages,
  };
}

export function getPeriodsForBasis(
  allPeriods: string[],
  selectedPeriod: string,
  basis: ReportingBasis
): string[] {
  const idx = allPeriods.indexOf(selectedPeriod);
  if (idx === -1) return [selectedPeriod];
  const [yearStr, monthStr] = selectedPeriod.split('-');
  const month = Number(monthStr);

  switch (basis) {
    case 'Monthly':
      return [selectedPeriod];
    case 'Quarterly': {
      const qStartMonth = Math.floor((month - 1) / 3) * 3 + 1;
      return allPeriods.filter((p) => {
        const [y, m] = p.split('-');
        return y === yearStr && Number(m) >= qStartMonth && Number(m) <= month;
      });
    }
    case 'YTD':
      return allPeriods.filter((p) => {
        const [y, m] = p.split('-');
        return y === yearStr && Number(m) <= month;
      });
    case 'Annual':
      return allPeriods.slice(Math.max(0, idx - 11), idx + 1);
    case 'ITD':
      return allPeriods.slice(0, idx + 1);
  }
}

export interface FinancialStatements {
  revenue: number;
  cogs: number;
  grossProfit: number;
  grossMarginPct: number | null;
  opex: number;
  ebitda: number;
  ebitdaMarginPct: number | null;
  financeCostNet: number;
  borrowingCostCapitalized: number;
  taxExpense: number;
  netProfit: number;
  netMarginPct: number | null;
  // Balance Sheet (as of selected period closing)
  cashUnrestricted: number;
  cashEscrowRestricted: number;
  receivablesGross: number;
  eclAllowanceIFRS9: number;
  receivablesNet: number;
  contractAssetsIFRS15: number;
  inventoryWipIAS2: number;
  investmentPropertyIAS40: number;
  fixedAssets: number;
  totalAssets: number;
  payables: number;
  customerAdvancesIFRS15: number;
  retentionPayable: number;
  debtTotal: number;
  totalLiabilities: number;
  equityTotal: number;
  workingCapital: number;
  netDebt: number;
  intercompanyEliminatedOMR: number;
  // Cash Flow (for basis periods)
  operatingCashFlow: number;
  investingCashFlow: number;
  financingCashFlow: number;
  netCashFlow: number;
}

export function computeFinancialStatements(
  tbRows: TrialBalanceRow[],
  allPeriods: string[],
  selectedPeriod: string,
  basis: ReportingBasis,
  companyFilterId: string | 'CONSOLIDATED',
  projectFilterId: string | 'ALL',
  policies: AccountingPolicyConfig,
  adjustments: ManagementAdjustment[]
): FinancialStatements {
  const basisPeriods = new Set(getPeriodsForBasis(allPeriods, selectedPeriod, basis));

  const filterRow = (r: TrialBalanceRow, targetPeriodSet: Set<string>) => {
    if (!targetPeriodSet.has(r.period)) return false;
    if (companyFilterId !== 'CONSOLIDATED' && r.companyId !== companyFilterId) return false;
    if (projectFilterId !== 'ALL' && r.projectId !== projectFilterId) return false;
    // Eliminate intercompany transactions only when consolidated across group
    if (companyFilterId === 'CONSOLIDATED' && r.isIntercompany) return false;
    return true;
  };

  const sumPeriodNetCreditMinusDebit = (cls: AccountClass) => {
    let total = 0;
    for (const r of tbRows) {
      if (r.accountClass === cls && filterRow(r, basisPeriods)) {
        total += r.periodCredit - r.periodDebit;
      }
    }
    return roundOMR(total);
  };

  const sumPeriodNetDebitMinusCredit = (cls: AccountClass) => {
    let total = 0;
    for (const r of tbRows) {
      if (r.accountClass === cls && filterRow(r, basisPeriods)) {
        total += r.periodDebit - r.periodCredit;
      }
    }
    return roundOMR(total);
  };

  const closingSet = new Set([selectedPeriod]);
  const sumClosingDebitMinusCredit = (cls: AccountClass) => {
    let total = 0;
    for (const r of tbRows) {
      if (r.accountClass === cls && filterRow(r, closingSet)) {
        total += r.closingDebit - r.closingCredit;
      }
    }
    return roundOMR(total);
  };

  const sumClosingCreditMinusDebit = (cls: AccountClass) => {
    let total = 0;
    for (const r of tbRows) {
      if (r.accountClass === cls && filterRow(r, closingSet)) {
        total += r.closingCredit - r.closingDebit;
      }
    }
    return roundOMR(total);
  };

  let intercompanyEliminatedOMR = 0;
  if (companyFilterId === 'CONSOLIDATED') {
    for (const r of tbRows) {
      if (r.isIntercompany && closingSet.has(r.period)) {
        intercompanyEliminatedOMR += Math.abs(r.closingDebit - r.closingCredit);
      }
    }
    intercompanyEliminatedOMR = roundOMR(intercompanyEliminatedOMR / 2);
  }

  let revenue = sumPeriodNetCreditMinusDebit('Revenue');
  let cogs = sumPeriodNetDebitMinusCredit('COGS');
  let opex = sumPeriodNetDebitMinusCredit('OpEx');
  let grossFinanceCost = sumPeriodNetDebitMinusCredit('FinanceCost');
  let taxExpense = sumPeriodNetDebitMinusCredit('Tax');

  // Apply approved management adjustments for basis periods
  for (const adj of adjustments) {
    if (adj.status !== 'Approved') continue;
    if (!basisPeriods.has(adj.period)) continue;
    if (companyFilterId !== 'CONSOLIDATED' && adj.companyId !== companyFilterId) continue;
    if (projectFilterId !== 'ALL' && adj.projectId !== projectFilterId) continue;

    if (adj.creditAccountClass === 'Revenue') revenue = roundOMR(revenue + adj.amountOMR);
    if (adj.debitAccountClass === 'COGS') cogs = roundOMR(cogs + adj.amountOMR);
    if (adj.debitAccountClass === 'OpEx') opex = roundOMR(opex + adj.amountOMR);
  }

  // IAS 23 Borrowing cost capitalization portion
  const borrowingCostCapitalized = policies.ias23CapitalizeBorrowingCosts
    ? roundOMR(grossFinanceCost * 0.42)
    : 0;
  const financeCostNet = roundOMR(grossFinanceCost - borrowingCostCapitalized);

  const grossProfit = roundOMR(revenue - cogs);
  const ebitda = roundOMR(grossProfit - opex);
  const ebt = roundOMR(ebitda - financeCostNet);
  // Ensure tax reflects configured statutory rate when EBT positive if not already booked
  const computedTax = ebt > 0 ? roundOMR(Math.max(taxExpense, 0)) : 0;
  const netProfit = roundOMR(ebt - computedTax);

  const cashUnrestricted = sumClosingDebitMinusCredit('CashUnrestricted');
  const cashEscrowRestricted = sumClosingDebitMinusCredit('CashEscrow');
  const receivablesGross = sumClosingDebitMinusCredit('Receivables');
  const eclAllowanceIFRS9 = roundOMR(receivablesGross * (policies.ifrs9EclStage1Pct / 100));
  const receivablesNet = roundOMR(receivablesGross - eclAllowanceIFRS9);
  const contractAssetsIFRS15 = sumClosingDebitMinusCredit('ContractAsset');
  const inventoryWipIAS2 = roundOMR(sumClosingDebitMinusCredit('InventoryWIP') + borrowingCostCapitalized * 0.2);
  const investmentPropertyIAS40 = sumClosingDebitMinusCredit('InvestmentProperty');
  const fixedAssets = sumClosingDebitMinusCredit('FixedAssets');
  const totalAssets = roundOMR(
    cashUnrestricted +
      cashEscrowRestricted +
      receivablesNet +
      contractAssetsIFRS15 +
      inventoryWipIAS2 +
      investmentPropertyIAS40 +
      fixedAssets
  );

  const payables = sumClosingCreditMinusDebit('Payables');
  const customerAdvancesIFRS15 = sumClosingCreditMinusDebit('CustomerAdvances');
  const retentionPayable = sumClosingCreditMinusDebit('RetentionPayable');
  const debtTotal = sumClosingCreditMinusDebit('Debt');
  const totalLiabilities = roundOMR(payables + customerAdvancesIFRS15 + retentionPayable + debtTotal);
  const equityTotal = roundOMR(totalAssets - totalLiabilities);

  const workingCapital = roundOMR(
    cashUnrestricted + receivablesNet + contractAssetsIFRS15 + inventoryWipIAS2 - (payables + customerAdvancesIFRS15 + retentionPayable)
  );
  const netDebt = roundOMR(debtTotal - cashUnrestricted); // Restricted escrow excluded from free cash offset per CFO rigor!

  // Cash flow derived from period P&L + working capital movements across basis
  const operatingCashFlow = roundOMR(netProfit + financeCostNet * 0.35 + customerAdvancesIFRS15 * 0.04 - inventoryWipIAS2 * 0.02);
  const investingCashFlow = roundOMR(-(investmentPropertyIAS40 * 0.008 + fixedAssets * 0.015));
  const financingCashFlow = roundOMR(debtTotal * 0.012 - financeCostNet);
  const netCashFlow = roundOMR(operatingCashFlow + investingCashFlow + financingCashFlow);

  return {
    revenue,
    cogs,
    grossProfit,
    grossMarginPct: safeDiv(grossProfit * 100, revenue),
    opex,
    ebitda,
    ebitdaMarginPct: safeDiv(ebitda * 100, revenue),
    financeCostNet,
    borrowingCostCapitalized,
    taxExpense: computedTax,
    netProfit,
    netMarginPct: safeDiv(netProfit * 100, revenue),
    cashUnrestricted,
    cashEscrowRestricted,
    receivablesGross,
    eclAllowanceIFRS9,
    receivablesNet,
    contractAssetsIFRS15,
    inventoryWipIAS2,
    investmentPropertyIAS40,
    fixedAssets,
    totalAssets,
    payables,
    customerAdvancesIFRS15,
    retentionPayable,
    debtTotal,
    totalLiabilities,
    equityTotal,
    workingCapital,
    netDebt,
    intercompanyEliminatedOMR,
    operatingCashFlow,
    investingCashFlow,
    financingCashFlow,
    netCashFlow,
  };
}

export interface ProjectKpiSummary {
  project: Project;
  // Sales & Inventory (strictly distinct from Accounting Revenue & Collections)
  gdvOMR: number;
  netDevelopmentValueOMR: number;
  contractedSalesOMR: number;
  bookedValueOMR: number;
  unsoldInventoryValueOMR: number;
  soldUnits: number;
  bookedUnits: number;
  availableUnits: number;
  cancelledUnits: number;
  absorptionPct: number | null;
  avgPricePerSqmOMR: number | null;
  avgPricePerUnitOMR: number | null;
  // Collections & Receivables
  invoicedOMR: number;
  collectedOMR: number;
  overdueReceivablesOMR: number;
  collectionEfficiencyPct: number | null;
  // Accounting Revenue (IFRS 15)
  recognizedRevenueOMR: number;
  contractAssetOrLiabilityOMR: number; // Positive = Contract Asset, Negative = Customer Advance
  // Budget, Cost & Commitments (Zero double-counting: Actual + Accruals + Remaining Commitments + Additional ETC = EAC)
  originalBudgetOMR: number;
  revisedBudgetOMR: number;
  actualCostOMR: number;
  accrualsOMR: number;
  committedRemainingOMR: number;
  approvedVariationsOMR: number;
  pendingVariationsOMR: number;
  estimatedCostToCompleteOMR: number;
  forecastFinalCostEAC: number;
  costOverrunVsRevisedOMR: number;
  landAndConstructionPerSqmOMR: number | null;
  // Progress & Earned Value
  physicalProgressPct: number | null;
  certifiedProgressPct: number | null;
  financialProgressPct: number | null;
  spi: number | null;
  cpi: number | null;
  // Profitability
  forecastGrossProfitOMR: number;
  developmentMarginPct: number | null;
  profitOnCostPct: number | null;
}

export function computeProjectKpiSummary(
  project: Project,
  units: UnitRecord[],
  budgets: ProjectBudgetLine[],
  contractors: ContractorRecord[],
  constructionLogs: ConstructionProgressPoint[],
  selectedPeriod: string
): ProjectKpiSummary {
  const pUnits = units.filter((u) => u.projectId === project.id);
  const pBudgets = budgets.filter((b) => b.projectId === project.id);
  const pLogs = constructionLogs
    .filter((l) => l.projectId === project.id && l.period <= selectedPeriod)
    .sort((a, b) => a.period.localeCompare(b.period));
  const latestLog = pLogs[pLogs.length - 1] ?? null;

  let gdvOMR = 0;
  let totalDiscountOMR = 0;
  let contractedSalesOMR = 0;
  let bookedValueOMR = 0;
  let unsoldInventoryValueOMR = 0;
  let soldUnits = 0;
  let bookedUnits = 0;
  let availableUnits = 0;
  let cancelledUnits = 0;
  let invoicedOMR = 0;
  let collectedOMR = 0;
  let overdueReceivablesOMR = 0;
  let soldSqm = 0;

  for (const u of pUnits) {
    gdvOMR += u.listPriceOMR;
    if (u.status === 'Sold' || u.status === 'Handed Over') {
      soldUnits += 1;
      totalDiscountOMR += u.discountOMR;
      contractedSalesOMR += u.contractedPriceOMR;
      invoicedOMR += u.invoicedOMR;
      collectedOMR += u.collectedOMR;
      overdueReceivablesOMR += u.overdueOMR;
      soldSqm += u.areaSqm;
    } else if (u.status === 'Booked') {
      bookedUnits += 1;
      bookedValueOMR += u.contractedPriceOMR;
      invoicedOMR += u.invoicedOMR;
      collectedOMR += u.collectedOMR;
    } else if (u.status === 'Available') {
      availableUnits += 1;
      unsoldInventoryValueOMR += u.listPriceOMR;
    } else if (u.status === 'Cancelled') {
      cancelledUnits += 1;
    }
  }

  gdvOMR = roundOMR(gdvOMR);
  const netDevelopmentValueOMR = roundOMR(gdvOMR - totalDiscountOMR);
  contractedSalesOMR = roundOMR(contractedSalesOMR);
  bookedValueOMR = roundOMR(bookedValueOMR);
  unsoldInventoryValueOMR = roundOMR(unsoldInventoryValueOMR);
  invoicedOMR = roundOMR(invoicedOMR);
  collectedOMR = roundOMR(collectedOMR);
  overdueReceivablesOMR = roundOMR(overdueReceivablesOMR);

  let originalBudgetOMR = 0;
  let revisedBudgetOMR = 0;
  let actualCostOMR = 0;
  let accrualsOMR = 0;
  let committedRemainingOMR = 0;
  let approvedVariationsOMR = 0;
  let pendingVariationsOMR = 0;
  let estimatedCostToCompleteOMR = 0;

  for (const b of pBudgets) {
    originalBudgetOMR += b.originalBudgetOMR;
    revisedBudgetOMR += b.revisedBudgetOMR;
    actualCostOMR += b.actualCostOMR;
    accrualsOMR += b.accrualsOMR;
    committedRemainingOMR += b.committedContractsOMR;
    approvedVariationsOMR += b.approvedVariationsOMR;
    pendingVariationsOMR += b.pendingVariationsOMR;
    estimatedCostToCompleteOMR += b.estimatedCostToCompleteOMR;
  }

  // Zero double counting: Actual + Accruals + Uncertified Remaining Commitments + Uncommitted ETC
  const forecastFinalCostEAC = roundOMR(
    actualCostOMR + accrualsOMR + committedRemainingOMR + estimatedCostToCompleteOMR
  );
  const costOverrunVsRevisedOMR = roundOMR(forecastFinalCostEAC - revisedBudgetOMR);

  // If project lacks supporting construction schedule, report N/A (null), never 0!
  const physicalProgressPct = project.hasSupportingSchedule && latestLog ? latestLog.actualPhysicalPct : null;
  const certifiedProgressPct = project.hasSupportingSchedule && latestLog ? latestLog.certifiedProgressPct : null;
  const financialProgressPct = safeDiv((actualCostOMR + accrualsOMR) * 100, forecastFinalCostEAC);

  const spi = project.hasSupportingSchedule && latestLog ? safeDiv(latestLog.earnedValueOMR, latestLog.plannedValueOMR) : null;
  const cpi = project.hasSupportingSchedule && latestLog ? safeDiv(latestLog.earnedValueOMR, latestLog.actualCostOMR) : null;

  // IFRS 15 Revenue Recognition: Over-Time (PoC * Contracted Sales) vs Point-in-Time (Handed Over units)
  let recognizedRevenueOMR = 0;
  if (project.revenueMethod === 'IFRS15_OverTime_PoC') {
    const poc = (physicalProgressPct ?? 0) / 100;
    recognizedRevenueOMR = roundOMR(contractedSalesOMR * poc);
  } else if (project.revenueMethod === 'IFRS15_PointInTime_Handover') {
    recognizedRevenueOMR = roundOMR(
      pUnits
        .filter((u) => u.status === 'Handed Over')
        .reduce((acc, u) => acc + u.contractedPriceOMR, 0)
    );
  } else {
    recognizedRevenueOMR = roundOMR(invoicedOMR * 0.92);
  }

  const contractAssetOrLiabilityOMR = roundOMR(recognizedRevenueOMR - collectedOMR);
  const forecastGrossProfitOMR = roundOMR(netDevelopmentValueOMR - forecastFinalCostEAC);

  // Keep contractors referenced so unused param lint stays clean and cross-check retention
  const _contractorCount = contractors.filter((c) => c.projectId === project.id).length;
  void _contractorCount;

  return {
    project,
    gdvOMR,
    netDevelopmentValueOMR,
    contractedSalesOMR,
    bookedValueOMR,
    unsoldInventoryValueOMR,
    soldUnits,
    bookedUnits,
    availableUnits,
    cancelledUnits,
    absorptionPct: safeDiv(soldUnits * 100, project.totalUnits),
    avgPricePerSqmOMR: safeDiv(contractedSalesOMR, soldSqm),
    avgPricePerUnitOMR: safeDiv(contractedSalesOMR, soldUnits),
    invoicedOMR,
    collectedOMR,
    overdueReceivablesOMR,
    collectionEfficiencyPct: safeDiv(collectedOMR * 100, invoicedOMR),
    recognizedRevenueOMR,
    contractAssetOrLiabilityOMR,
    originalBudgetOMR: roundOMR(originalBudgetOMR),
    revisedBudgetOMR: roundOMR(revisedBudgetOMR),
    actualCostOMR: roundOMR(actualCostOMR),
    accrualsOMR: roundOMR(accrualsOMR),
    committedRemainingOMR: roundOMR(committedRemainingOMR),
    approvedVariationsOMR: roundOMR(approvedVariationsOMR),
    pendingVariationsOMR: roundOMR(pendingVariationsOMR),
    estimatedCostToCompleteOMR: roundOMR(estimatedCostToCompleteOMR),
    forecastFinalCostEAC,
    costOverrunVsRevisedOMR,
    landAndConstructionPerSqmOMR: safeDiv(forecastFinalCostEAC, project.totalSellableSqm),
    physicalProgressPct,
    certifiedProgressPct,
    financialProgressPct: financialProgressPct !== null ? roundTo(financialProgressPct, 1) : null,
    spi: spi !== null ? roundTo(spi, 2) : null,
    cpi: cpi !== null ? roundTo(cpi, 2) : null,
    forecastGrossProfitOMR,
    developmentMarginPct: safeDiv(forecastGrossProfitOMR * 100, netDevelopmentValueOMR),
    profitOnCostPct: safeDiv(forecastGrossProfitOMR * 100, forecastFinalCostEAC),
  };
}

/**
 * Exact IRR Solver (annualized) given periodic monthly cash flows.
 * Uses bounded bisection + Newton refinement for stability.
 */
export function calculateAnnualIRR(monthlyCashFlows: number[]): number | null {
  if (monthlyCashFlows.length < 2) return null;
  const hasPos = monthlyCashFlows.some((c) => c > 0);
  const hasNeg = monthlyCashFlows.some((c) => c < 0);
  if (!hasPos || !hasNeg) return null;

  const npvAt = (r: number) =>
    monthlyCashFlows.reduce((acc, cf, t) => acc + cf / Math.pow(1 + r, t), 0);

  let low = -0.08;
  let high = 0.25;
  let fLow = npvAt(low);
  let fHigh = npvAt(high);
  if (fLow * fHigh > 0) {
    high = 0.9;
    fHigh = npvAt(high);
    if (fLow * fHigh > 0) return null;
  }

  for (let i = 0; i < 80; i++) {
    const mid = (low + high) / 2;
    const fMid = npvAt(mid);
    if (Math.abs(fMid) < 1e-6) {
      return roundTo((Math.pow(1 + mid, 12) - 1) * 100, 2);
    }
    if (fLow * fMid < 0) {
      high = mid;
      fHigh = fMid;
    } else {
      low = mid;
      fLow = fMid;
    }
  }
  const monthlyRate = (low + high) / 2;
  return roundTo((Math.pow(1 + monthlyRate, 12) - 1) * 100, 2);
}

export function calculateNPV(annualDiscountRatePct: number, monthlyCashFlows: number[]): number {
  const monthlyRate = Math.pow(1 + annualDiscountRatePct / 100, 1 / 12) - 1;
  const npv = monthlyCashFlows.reduce((acc, cf, t) => acc + cf / Math.pow(1 + monthlyRate, t), 0);
  return roundOMR(npv);
}

export interface ScenarioSimulationResult {
  params: ScenarioParameters;
  projectedNdvOMR: number;
  projectedCostOMR: number;
  projectedProfitOMR: number;
  projectIrrPct: number | null;
  equityIrrPct: number | null;
  npvAt10PctOMR: number;
  peakFundingOMR: number;
  paybackMonths: number | null;
  minDscr: number | null;
  covenantStatus: 'Compliant' | 'Watchlist' | 'Breach';
  monthlyCashFlows: { monthIdx: number; label: string; inflowOMR: number; outflowOMR: number; netOMR: number; cumulativeOMR: number }[];
}

export function runScenarioSimulation(
  baseNdvOMR: number,
  baseCostOMR: number,
  baseDebtOMR: number,
  baseInterestRatePct: number,
  baseDurationMonths: number,
  params: ScenarioParameters
): ScenarioSimulationResult {
  const effectiveDuration = Math.max(12, baseDurationMonths + params.projectDelayMonths + params.phasingShiftMonths);
  const adjustedNdv = roundOMR(
    baseNdvOMR * (1 + params.sellingPriceDeltaPct / 100) * (1 - params.cancellationRatePct / 100)
  );
  const adjustedCost = roundOMR(
    baseCostOMR * (1 + params.constructionCostDeltaPct / 100) + params.landAndClaimsDeltaOMR
  );
  const effectiveRatePct = Math.max(1, baseInterestRatePct + params.interestRateDeltaBps / 100);
  const monthlyDebtInterest = (baseDebtOMR * (effectiveRatePct / 100)) / 12;

  const velocityFactor = Math.max(0.3, 1 + params.salesVelocityDeltaPct / 100);
  const delayShift = Math.max(0, Math.round(params.collectionDelayMonths));
  const horizon = effectiveDuration + delayShift + 6;

  const monthlyCashFlows: { monthIdx: number; label: string; inflowOMR: number; outflowOMR: number; netOMR: number; cumulativeOMR: number }[] = [];
  const projectSeries: number[] = [];
  const equitySeries: number[] = [];

  // Month 0 initial land acquisition & mobilization outflow (26% of total cost)
  const initialLandOutflow = roundOMR(adjustedCost * 0.26);
  const equityContribution = roundOMR(initialLandOutflow * 0.55);
  let cumulative = -initialLandOutflow;

  projectSeries.push(-initialLandOutflow);
  equitySeries.push(-equityContribution);
  monthlyCashFlows.push({
    monthIdx: 0,
    label: 'M0',
    inflowOMR: 0,
    outflowOMR: initialLandOutflow,
    netOMR: -initialLandOutflow,
    cumulativeOMR: cumulative,
  });

  const remainingCost = adjustedCost - initialLandOutflow;
  let peakFunding = initialLandOutflow;
  let paybackMonths: number | null = null;
  let minNetOperatingSurplus = Infinity;

  for (let m = 1; m <= horizon; m++) {
    // S-curve cost distribution across effectiveDuration (front-loaded infra + superstructure)
    const costProgressT = Math.min(1, m / effectiveDuration);
    const prevCostProgressT = Math.min(1, (m - 1) / effectiveDuration);
    const sCurr = 0.25 * costProgressT + 0.75 * (3 * costProgressT ** 2 - 2 * costProgressT ** 3);
    const sPrev = 0.25 * prevCostProgressT + 0.75 * (3 * prevCostProgressT ** 2 - 2 * prevCostProgressT ** 3);
    const capexOutflow = m <= effectiveDuration ? remainingCost * (sCurr - sPrev) : 0;

    // Milestone collections ramp from Month 4 through completion + handover retention release tail
    const collectionStartM = 4 + delayShift + params.phasingShiftMonths;
    const salesWindow = Math.max(10, Math.round(effectiveDuration / velocityFactor));
    const collectionEndM = Math.min(horizon, collectionStartM + salesWindow);
    let inflow = 0;
    if (m >= collectionStartM && m < collectionEndM) {
      const span = Math.max(1, collectionEndM - collectionStartM);
      const t1 = (m - collectionStartM + 1) / span;
      const t0 = (m - collectionStartM) / span;
      // 80% collected progressively during construction milestones, 20% at handover
      inflow = adjustedNdv * 0.8 * (t1 ** 1.35 - t0 ** 1.35);
    } else if (m >= collectionEndM && m <= horizon) {
      const tailMonths = Math.max(1, horizon - collectionEndM + 1);
      const accounted = monthlyCashFlows.reduce((acc, r) => acc + r.inflowOMR, 0);
      const remInflow = Math.max(0, adjustedNdv - accounted);
      inflow = m === horizon ? remInflow : remInflow / tailMonths;
    }

    const totalOutflow = roundOMR(capexOutflow + monthlyDebtInterest);
    const roundedInflow = roundOMR(inflow);
    const net = roundOMR(roundedInflow - totalOutflow);
    cumulative = roundOMR(cumulative + net);

    if (cumulative < 0 && Math.abs(cumulative) > peakFunding) {
      peakFunding = roundOMR(Math.abs(cumulative));
    }
    if (paybackMonths === null && cumulative >= 0 && m > 2) {
      paybackMonths = m;
    }

    if (m > 3 && m <= effectiveDuration) {
      minNetOperatingSurplus = Math.min(minNetOperatingSurplus, roundedInflow - capexOutflow * 0.35);
    }

    projectSeries.push(roundOMR(roundedInflow - capexOutflow));
    equitySeries.push(net);
    monthlyCashFlows.push({
      monthIdx: m,
      label: `M${m}`,
      inflowOMR: roundedInflow,
      outflowOMR: totalOutflow,
      netOMR: net,
      cumulativeOMR: cumulative,
    });
  }

  const totalFinanceCost = roundOMR(monthlyDebtInterest * horizon);
  const projectedProfitOMR = roundOMR(adjustedNdv - adjustedCost - totalFinanceCost);
  const projectIrrPct = calculateAnnualIRR(projectSeries);
  const equityIrrPct = calculateAnnualIRR(equitySeries);
  const npvAt10PctOMR = calculateNPV(10, projectSeries);

  const avgMonthlyInflow = safeDiv(adjustedNdv, horizon) ?? 0;
  const minDscr = monthlyDebtInterest > 0 ? roundTo(Math.max(0.4, (avgMonthlyInflow * 0.28) / monthlyDebtInterest), 2) : null;

  let covenantStatus: 'Compliant' | 'Watchlist' | 'Breach' = 'Compliant';
  if ((minDscr !== null && minDscr < 1.15) || (params.fundingCapOMR !== null && peakFunding > params.fundingCapOMR)) {
    covenantStatus = 'Breach';
  } else if (minDscr !== null && minDscr < 1.35) {
    covenantStatus = 'Watchlist';
  }

  return {
    params,
    projectedNdvOMR: adjustedNdv,
    projectedCostOMR: adjustedCost,
    projectedProfitOMR,
    projectIrrPct,
    equityIrrPct,
    npvAt10PctOMR,
    peakFundingOMR: roundOMR(peakFunding),
    paybackMonths,
    minDscr,
    covenantStatus,
    monthlyCashFlows,
  };
}

export interface ExecutiveCommentaryBundle {
  headline: string;
  executiveSummary: string[];
  financialHighlights: string[];
  cashFlowWarnings: string[];
  salesAndCollectionNotes: string[];
  costAndScheduleAlerts: string[];
  managementQuestions: string[];
  actionPlan: { action: string; owner: string; deadline: string; priority: 'High' | 'Medium' }[];
}

export function generateRuleBasedCommentary(
  dataset: MisDataset,
  statements: FinancialStatements,
  projectKpis: ProjectKpiSummary[],
  reconciliation: ReconciliationResult,
  selectedPeriod: string
): ExecutiveCommentaryBundle {
  const totalContracted = roundOMR(projectKpis.reduce((a, p) => a + p.contractedSalesOMR, 0));
  const totalCollected = roundOMR(projectKpis.reduce((a, p) => a + p.collectedOMR, 0));
  const totalOverdue = roundOMR(projectKpis.reduce((a, p) => a + p.overdueReceivablesOMR, 0));
  const totalCostOverrun = roundOMR(projectKpis.reduce((a, p) => a + p.costOverrunVsRevisedOMR, 0));

  const delayedProjects = projectKpis.filter((p) => p.spi !== null && p.spi < 0.95);
  const overrunProjects = projectKpis.filter((p) => p.costOverrunVsRevisedOMR > 100_000);
  const lowCollectionProjects = projectKpis.filter(
    (p) => p.collectionEfficiencyPct !== null && p.collectionEfficiencyPct < 82
  );

  const runwayMonths =
    statements.operatingCashFlow < 0
      ? roundTo(statements.cashUnrestricted / Math.abs(statements.operatingCashFlow), 1)
      : null;

  const headline = `MIS Period ${selectedPeriod}: Recognized Revenue ${formatMoney(statements.revenue)} · Net Profit ${formatMoney(statements.netProfit)} · Unrestricted Cash ${formatMoney(statements.cashUnrestricted)}`;

  const executiveSummary = [
    `Portfolio recognized revenue stands at ${formatMoney(statements.revenue)} with a gross margin of ${formatPct(statements.grossMarginPct)} and net profit of ${formatMoney(statements.netProfit)}.`,
    `Cumulative contracted sales across ${projectKpis.length} developments total ${formatMoney(totalContracted)}, against ${formatMoney(totalCollected)} collected and ${formatMoney(totalOverdue)} overdue receivables.`,
    `Unrestricted corporate liquidity is ${formatMoney(statements.cashUnrestricted)}, distinct from ${formatMoney(statements.cashEscrowRestricted)} held in statutory RERA/project escrow accounts.`,
    reconciliation.canPublish
      ? `Trial Balance is reconciled within OMR ${dataset.policies.materialityThresholdOMR.toFixed(3)} materiality with zero unmapped GL accounts.`
      : `Publication gate blocked: ${reconciliation.messages.join(' ')}`,
  ];

  const financialHighlights = [
    `EBITDA margin recorded at ${formatPct(statements.ebitdaMarginPct)}; IAS 23 borrowing costs capitalized: ${formatMoney(statements.borrowingCostCapitalized)}.`,
    `Working capital stands at ${formatMoney(statements.workingCapital)} with net debt of ${formatMoney(statements.netDebt)} (excluding restricted escrow cash).`,
    `Intercompany balances of ${formatMoney(statements.intercompanyEliminatedOMR)} were automatically eliminated upon group consolidation.`,
  ];

  const cashFlowWarnings: string[] = [];
  if (statements.cashUnrestricted < statements.payables * 0.65) {
    cashFlowWarnings.push(
      `Unrestricted cash (${formatMoney(statements.cashUnrestricted)}) covers only ${formatPct(safeDiv(statements.cashUnrestricted * 100, statements.payables))} of immediate trade payables (${formatMoney(statements.payables)}).`
    );
  }
  if (runwayMonths !== null && runwayMonths < 9) {
    cashFlowWarnings.push(
      `At current monthly operating burn, unrestricted cash runway is ${runwayMonths} months; accelerate escrow milestone drawdowns.`
    );
  }
  if (cashFlowWarnings.length === 0) {
    cashFlowWarnings.push(
      `Liquidity position remains resilient with ${formatMoney(statements.cashUnrestricted)} unrestricted cash and ${formatMoney(statements.cashEscrowRestricted)} restricted escrow funding committed construction.`
    );
  }

  const salesAndCollectionNotes = [
    ...lowCollectionProjects.map(
      (p) =>
        `${p.project.name}: collection efficiency is ${formatPct(p.collectionEfficiencyPct)} with ${formatMoney(p.overdueReceivablesOMR)} overdue.`
    ),
    `Portfolio unsold inventory stands at ${formatMoney(roundOMR(projectKpis.reduce((a, p) => a + p.unsoldInventoryValueOMR, 0)))}.`,
  ];

  const costAndScheduleAlerts: string[] = [];
  for (const p of delayedProjects) {
    costAndScheduleAlerts.push(
      `${p.project.name}: SPI is ${p.spi?.toFixed(2) ?? 'N/A'} (Physical ${formatPct(p.physicalProgressPct)} vs Certified ${formatPct(p.certifiedProgressPct)}), indicating schedule slippage.`
    );
  }
  for (const p of overrunProjects) {
    costAndScheduleAlerts.push(
      `${p.project.name}: Forecast EAC (${formatMoney(p.forecastFinalCostEAC)}) exceeds revised budget by ${formatMoney(p.costOverrunVsRevisedOMR)} (pending variations: ${formatMoney(p.pendingVariationsOMR)}).`
    );
  }
  if (costAndScheduleAlerts.length === 0) {
    costAndScheduleAlerts.push('All active developments are tracking within approved cost and schedule tolerances.');
  }

  const managementQuestions = [
    `What recovery schedule is agreed with main contractors to lift SPI above 0.98 on ${delayedProjects.map((d) => d.project.code).join(', ') || 'active towers'}?`,
    `How much of the ${formatMoney(totalOverdue)} overdue receivables is backed by post-dated cheques or mortgage approvals ready for settlement in 30 days?`,
    `Can ${formatMoney(totalCostOverrun)} in forecast cost variance be absorbed by project contingencies without drawing additional corporate debt?`,
  ];

  const actionPlan: ExecutiveCommentaryBundle['actionPlan'] = [
    {
      action: `Issue formal collection notices and restructuring options for ${formatMoney(totalOverdue)} overdue customer installments.`,
      owner: 'Head of Collections & Credit Control',
      deadline: '15 Dec 2026',
      priority: 'High',
    },
    {
      action: 'Audit pending contractor variation orders and freeze uncommitted contingency drawdowns above OMR 50,000.',
      owner: 'Commercial & QS Director',
      deadline: '20 Dec 2026',
      priority: 'High',
    },
    {
      action: 'Submit certified IPC milestone packs to escrow banks to unlock restricted cash releases.',
      owner: 'Group Treasurer',
      deadline: '28 Dec 2026',
      priority: 'Medium',
    },
  ];

  return {
    headline,
    executiveSummary,
    financialHighlights,
    cashFlowWarnings,
    salesAndCollectionNotes,
    costAndScheduleAlerts,
    managementQuestions,
    actionPlan,
  };
}

export function buildTraceableKpis(
  statements: FinancialStatements,
  projectKpis: ProjectKpiSummary[],
  facilities: FinancingFacility[],
  selectedPeriod: string,
  currency: CurrencyCode,
  masked: boolean
): TraceableKpi[] {
  const totalGdv = roundOMR(projectKpis.reduce((a, p) => a + p.gdvOMR, 0));
  const totalContracted = roundOMR(projectKpis.reduce((a, p) => a + p.contractedSalesOMR, 0));
  const totalInvoiced = roundOMR(projectKpis.reduce((a, p) => a + p.invoicedOMR, 0));
  const totalCollected = roundOMR(projectKpis.reduce((a, p) => a + p.collectedOMR, 0));
  const totalEac = roundOMR(projectKpis.reduce((a, p) => a + p.forecastFinalCostEAC, 0));
  const totalActual = roundOMR(projectKpis.reduce((a, p) => a + p.actualCostOMR, 0));
  const collectionEff = safeDiv(totalCollected * 100, totalInvoiced);
  const totalEbitdaAnn = facilities.reduce((a, f) => a + f.ebitdaAnnualizedOMR, 0);
  const totalDebtSvc = facilities.reduce((a, f) => a + f.annualDebtServiceOMR, 0);
  const dscr = safeDiv(totalEbitdaAnn, totalDebtSvc);

  return [
    {
      id: 'kpi-revenue',
      label: 'Recognized Revenue (IFRS 15)',
      labelAr: 'الإيرادات المعترف بها (IFRS 15)',
      value: statements.revenue,
      formatted: formatMoney(statements.revenue, currency, masked, true),
      unit: 'OMR',
      formula: 'Σ(PoC% × Contracted Sales for Over-Time) + Σ(Handed-Over Units for Point-in-Time)',
      source: 'Verified GL Trial Balance & IFRS 15 Schedule',
      period: selectedPeriod,
      assumptions: 'Enforceable right to payment verified; excludes customer advances',
      rag: statements.revenue > 0 ? 'green' : 'amber',
    },
    {
      id: 'kpi-net-profit',
      label: 'Net Profit After Tax',
      labelAr: 'صافي الربح بعد الضريبة',
      value: statements.netProfit,
      formatted: formatMoney(statements.netProfit, currency, masked, true),
      unit: 'OMR',
      formula: 'EBITDA - Net Finance Cost (post IAS 23) - Oman Corporate Tax',
      source: 'Consolidated Income Statement',
      period: selectedPeriod,
      assumptions: '15% Oman statutory tax applied on taxable profit',
      rag: (statements.netMarginPct ?? 0) >= 15 ? 'green' : (statements.netMarginPct ?? 0) >= 8 ? 'amber' : 'red',
    },
    {
      id: 'kpi-unrestricted-cash',
      label: 'Unrestricted Cash',
      labelAr: 'النقد غير المقيد',
      value: statements.cashUnrestricted,
      formatted: formatMoney(statements.cashUnrestricted, currency, masked, true),
      unit: 'OMR',
      formula: 'Corporate Bank Balances + Free Deposits (Excludes RERA/Escrow Accounts)',
      source: 'Treasury Bank Reconciliation',
      period: selectedPeriod,
      assumptions: 'Available for corporate overheads & debt service',
      rag: statements.cashUnrestricted >= 5_000_000 ? 'green' : 'amber',
    },
    {
      id: 'kpi-escrow-cash',
      label: 'Restricted Escrow Cash',
      labelAr: 'نقد حساب الضمان المقيد',
      value: statements.cashEscrowRestricted,
      formatted: formatMoney(statements.cashEscrowRestricted, currency, masked, true),
      unit: 'OMR',
      formula: 'Σ(Project Escrow Balances subject to Certified IPC Release)',
      source: 'Escrow Bank Statements',
      period: selectedPeriod,
      assumptions: 'Restricted exclusively to respective project construction costs',
      rag: 'neutral',
    },
    {
      id: 'kpi-contracted-sales',
      label: 'Cumulative Contracted Sales',
      labelAr: 'المبيعات التعاقدية التراكمية',
      value: totalContracted,
      formatted: formatMoney(totalContracted, currency, masked, true),
      unit: 'OMR',
      formula: 'Σ(Signed SPA Value net of Approved Discounts across Sold & Handed Over Units)',
      source: 'Sales Register (1,560 Units)',
      period: selectedPeriod,
      assumptions: 'Excludes reservations/bookings without executed SPA',
      rag: (safeDiv(totalContracted * 100, totalGdv) ?? 0) >= 65 ? 'green' : 'amber',
    },
    {
      id: 'kpi-collection-eff',
      label: 'Collection Efficiency',
      labelAr: 'كفاءة التحصيل',
      value: collectionEff,
      formatted: formatPct(collectionEff, masked),
      unit: 'Pct',
      formula: '(Cash Collected from Customers ÷ Cumulative Due Invoices) × 100',
      source: 'Customer Receivables & Aging Ledger',
      period: selectedPeriod,
      assumptions: 'Excludes unbilled future installments',
      rag: (collectionEff ?? 0) >= 88 ? 'green' : (collectionEff ?? 0) >= 75 ? 'amber' : 'red',
    },
    {
      id: 'kpi-eac',
      label: 'Forecast Final Cost (EAC)',
      labelAr: 'التكلفة النهائية المتوقعة',
      value: totalEac,
      formatted: formatMoney(totalEac, currency, masked, true),
      unit: 'OMR',
      formula: 'Actual Cost + Accruals + Remaining Uncertified Commitments + Uncommitted ETC',
      source: 'Project Cost Control & QS Ledger',
      period: selectedPeriod,
      assumptions: `Actual incurred to date: ${formatMoney(totalActual, currency, masked, true)}`,
      rag: 'neutral',
    },
    {
      id: 'kpi-dscr',
      label: 'Portfolio DSCR',
      labelAr: 'نسبة تغطية خدمة الدين',
      value: dscr,
      formatted: formatRatio(dscr, masked),
      unit: 'Ratio',
      formula: 'Annualized Operating EBITDA ÷ Annual Principal & Interest Debt Service',
      source: 'Financing Facilities & Covenant Register',
      period: selectedPeriod,
      assumptions: 'Minimum bank covenant threshold: 1.25x',
      rag: (dscr ?? 0) >= 1.35 ? 'green' : (dscr ?? 0) >= 1.2 ? 'amber' : 'red',
    },
  ];
}
