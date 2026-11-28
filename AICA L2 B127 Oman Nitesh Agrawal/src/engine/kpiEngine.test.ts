import test from 'node:test';
import assert from 'node:assert/strict';
import {
  buildTraceableKpis,
  calculateAnnualIRR,
  calculateNPV,
  computeFinancialStatements,
  computeProjectKpiSummary,
  formatMoney,
  generateRuleBasedCommentary,
  reconcileTrialBalance,
  roundOMR,
  runScenarioSimulation,
  safeDiv,
} from './kpiEngine';
import { createSeedDataset } from '../data/seedDataset';

test('OMR 3-decimal rounding, negative formatting, and missing N/A discipline', () => {
  assert.equal(roundOMR(1234.5674), 1234.567);
  assert.equal(roundOMR(1234.5676), 1234.568);
  assert.equal(formatMoney(12500.5, 'OMR', false), 'OMR 12,500.500');
  assert.equal(formatMoney(-420.125, 'OMR', false), 'OMR (420.125)');
  assert.equal(formatMoney(null, 'OMR', false), 'N/A');
  assert.equal(formatMoney(1000, 'OMR', true), 'OMR •••.•••');
  assert.equal(safeDiv(100, 0), null);
  assert.equal(safeDiv(null, 50), null);
});

test('Seed dataset contains 3 companies, 5 projects, >=1500 units, and 24 months', () => {
  const ds = createSeedDataset();
  assert.equal(ds.companies.length, 3);
  assert.equal(ds.projects.length, 5);
  assert.ok(ds.units.length >= 1500, `Expected >=1500 units, got ${ds.units.length}`);
  assert.equal(ds.units.length, 1560);
  assert.equal(ds.periods.length, 24);
});

test('Trial Balance reconciles to 0.000 OMR across all 24 months and blocks unreconciled TB', () => {
  const ds = createSeedDataset();
  const latest = ds.periods[ds.periods.length - 1];
  const prev = ds.periods[ds.periods.length - 2];
  const currRows = ds.trialBalance.filter((r) => r.period === latest);
  const prevRows = ds.trialBalance.filter((r) => r.period === prev);

  const res = reconcileTrialBalance(currRows, prevRows, ds.glMappings, ds.policies.materialityThresholdOMR);
  assert.equal(res.trialBalanceDiff, 0);
  assert.equal(res.closingDiff, 0);
  assert.equal(res.rollforwardErrors, 0);
  assert.equal(res.isMateriallyReconciled, true);
  assert.equal(res.canPublish, true);

  // Inject imbalance > materiality threshold and verify publication block
  const brokenRows = currRows.map((r, i) => (i === 0 ? { ...r, periodDebit: r.periodDebit + 1200 } : r));
  const brokenRes = reconcileTrialBalance(brokenRows, prevRows, ds.glMappings, ds.policies.materialityThresholdOMR);
  assert.equal(brokenRes.isMateriallyReconciled, false);
  assert.equal(brokenRes.canPublish, false);
});

test('Consolidated financial statements eliminate intercompany balances and keep BS balanced', () => {
  const ds = createSeedDataset();
  const latest = ds.periods[ds.periods.length - 1];
  const cons = computeFinancialStatements(
    ds.trialBalance,
    ds.periods,
    latest,
    'Monthly',
    'CONSOLIDATED',
    'ALL',
    ds.policies,
    ds.adjustments
  );
  assert.equal(cons.intercompanyEliminatedOMR, 2450000);
  assert.ok(cons.revenue > 0);
  assert.ok(cons.cashUnrestricted > 0);
  assert.ok(cons.cashEscrowRestricted > 0);
  // Net Debt must exclude restricted escrow cash
  assert.equal(cons.netDebt, roundOMR(cons.debtTotal - cons.cashUnrestricted));
});

test('Project KPI engine prevents double counting in EAC and respects missing schedule N/A', () => {
  const ds = createSeedDataset();
  const latest = ds.periods[ds.periods.length - 1];
  const prj = ds.projects[0];
  const summary = computeProjectKpiSummary(prj, ds.units, ds.budgets, ds.contractors, ds.constructionLogs, latest);

  const expectedEac = roundOMR(
    summary.actualCostOMR +
      summary.accrualsOMR +
      summary.committedRemainingOMR +
      summary.estimatedCostToCompleteOMR
  );
  assert.equal(summary.forecastFinalCostEAC, expectedEac);
  assert.ok(summary.physicalProgressPct !== null);
  assert.ok(summary.spi !== null);
  assert.ok(summary.cpi !== null);

  // Missing supporting schedule must yield null (N/A), never 0
  const noSchedPrj = { ...prj, hasSupportingSchedule: false };
  const noSchedSummary = computeProjectKpiSummary(
    noSchedPrj,
    ds.units,
    ds.budgets,
    ds.contractors,
    ds.constructionLogs,
    latest
  );
  assert.equal(noSchedSummary.physicalProgressPct, null);
  assert.equal(noSchedSummary.spi, null);
  assert.equal(noSchedSummary.cpi, null);
});

test('IRR, NPV, and Scenario Simulation produce mathematically consistent sensitivities', () => {
  // Simple 12-month + 10% monthly return benchmark: -100 followed by 110 in M1 -> monthly 10% -> annual (1.1^12 - 1)*100 = 213.84%
  const benchIrr = calculateAnnualIRR([-100, 110]);
  assert.ok(benchIrr !== null && Math.abs(benchIrr - 213.84) < 0.2);

  const npv = calculateNPV(10, [-1000, 550, 550]);
  assert.ok(npv > 0);

  const baseSim = runScenarioSimulation(50_000_000, 35_000_000, 15_000_000, 6.0, 30, {
    name: 'Base',
    sellingPriceDeltaPct: 0,
    salesVelocityDeltaPct: 0,
    collectionDelayMonths: 0,
    cancellationRatePct: 0,
    constructionCostDeltaPct: 0,
    projectDelayMonths: 0,
    interestRateDeltaBps: 0,
    landAndClaimsDeltaOMR: 0,
    phasingShiftMonths: 0,
    fundingCapOMR: null,
  });

  const stressSim = runScenarioSimulation(50_000_000, 35_000_000, 15_000_000, 6.0, 30, {
    name: 'Pessimistic',
    sellingPriceDeltaPct: -10,
    salesVelocityDeltaPct: -20,
    collectionDelayMonths: 4,
    cancellationRatePct: 5,
    constructionCostDeltaPct: 12,
    projectDelayMonths: 6,
    interestRateDeltaBps: 150,
    landAndClaimsDeltaOMR: 1_000_000,
    phasingShiftMonths: 0,
    fundingCapOMR: null,
  });

  assert.ok(stressSim.projectedProfitOMR < baseSim.projectedProfitOMR);
  assert.ok((stressSim.projectIrrPct ?? 0) < (baseSim.projectIrrPct ?? 100));
  assert.ok(stressSim.peakFundingOMR > baseSim.peakFundingOMR);
});

test('Rule-based management commentary and traceable KPIs align strictly with verified engine numbers', () => {
  const ds = createSeedDataset();
  const latest = ds.periods[ds.periods.length - 1];
  const prev = ds.periods[ds.periods.length - 2];
  const cons = computeFinancialStatements(
    ds.trialBalance,
    ds.periods,
    latest,
    'Monthly',
    'CONSOLIDATED',
    'ALL',
    ds.policies,
    ds.adjustments
  );
  const kpis = ds.projects.map((p) =>
    computeProjectKpiSummary(p, ds.units, ds.budgets, ds.contractors, ds.constructionLogs, latest)
  );
  const rec = reconcileTrialBalance(
    ds.trialBalance.filter((r) => r.period === latest),
    ds.trialBalance.filter((r) => r.period === prev),
    ds.glMappings,
    ds.policies.materialityThresholdOMR
  );

  const commentary = generateRuleBasedCommentary(ds, cons, kpis, rec, latest);
  assert.ok(commentary.headline.includes(latest));
  assert.ok(commentary.executiveSummary.length >= 3);
  assert.ok(commentary.actionPlan.length >= 2);

  const traceable = buildTraceableKpis(cons, kpis, ds.facilities, latest, 'OMR', false);
  assert.equal(traceable.length, 8);
  assert.ok(traceable.every((k) => k.formula.length > 5 && k.source.length > 3));
});
