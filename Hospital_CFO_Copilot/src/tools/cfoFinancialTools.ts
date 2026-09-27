/**
 * Hospital CFO Copilot - Controlled Financial Tools
 *
 * Exposes server-side / application deterministic data-gathering functions for the
 * Agentic CFO Financial Review workflow.
 *
 * MANDATORY ARCHITECTURAL RULES:
 * 1. Read-Only: ZERO mutation parameters. Cannot resolve exceptions, alter billing,
 *    or modify financial records.
 * 2. Strictly Grounded: All numbers, percentages, IDs, and amounts originate from verified
 *    application state. Zero synthetic or invented data.
 * 3. Empty State Honesty: Explicitly reports empty / zero state when no material finding
 *    exists. Never manufactures observations.
 */

import {
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  ControlId,
  DashboardMetrics,
  DepartmentClearanceRecord,
  Encounter,
  ExceptionStatus,
  FinancialException,
  Service,
  Severity,
  TariffMasterItem,
} from '../types';
import { ControlRunResult } from '../engine/controlEngine';
import { DepartmentClearanceSummary } from '../engine/clearanceEngine';
import { calculateArAgeing, getClaimsPendingAdjudication } from '../utils/arCalculations';
import { BudgetExecutiveSummary } from '../engine/budgetEngine';
import { TariffIntelligenceSummary } from '../engine/tariffEngine';

// ============================================================================
// Tool 1: get_latest_control_run
// ============================================================================
export interface LatestControlRunPayload {
  runId: string;
  runDate: string;
  recordsProcessed: number;
  exceptionsGenerated: number;
  potentialFinancialImpact: number;
  c01ToC08Summary: Array<{
    controlId: ControlId;
    title: string;
    count: number;
    exposure: number;
  }>;
}

export function get_latest_control_run(controlResult: ControlRunResult): LatestControlRunPayload {
  return {
    runId: controlResult.runId,
    runDate: controlResult.auditTrail.Run_Date_Time,
    recordsProcessed: controlResult.auditTrail.Records_Processed,
    exceptionsGenerated: controlResult.auditTrail.Exceptions_Generated,
    potentialFinancialImpact: controlResult.metrics.potentialFinancialExposure,
    c01ToC08Summary: controlResult.metrics.exceptionsByControl.map(
      (c: { controlId: ControlId; title: string; count: number; exposure: number }) => ({
        controlId: c.controlId,
        title: c.title,
        count: c.count,
        exposure: c.exposure,
      })
    ),
  };
}

// ============================================================================
// Tool 2: get_open_exceptions
// ============================================================================
export interface OpenExceptionItem {
  exceptionId: string;
  encounterId: string;
  department: string;
  revenueCentre: string;
  controlId: ControlId;
  severity: Severity;
  potentialFinancialImpact: number;
  status: ExceptionStatus;
  ageDays: number;
  assignedOwner: string;
  description: string;
}

export function get_open_exceptions(
  exceptions: FinancialException[],
  encounters: Encounter[] = [],
  filter?: { severities?: Severity[]; limit?: number }
): OpenExceptionItem[] {
  const encMap = new Map<string, Encounter>();
  encounters.forEach((e) => encMap.set(e.Encounter_ID, e));

  const nowMs = Date.now();
  const openStatuses: ExceptionStatus[] = ['OPEN', 'UNDER_REVIEW'];

  let matched = exceptions.filter((e) => openStatuses.includes(e.Status));

  if (filter?.severities && filter.severities.length > 0) {
    matched = matched.filter((e) => filter.severities!.includes(e.Severity));
  }

  // Sort by severity (CRITICAL > HIGH > MEDIUM > LOW) then by exposure descending
  const sevScore: Record<Severity, number> = { CRITICAL: 4, HIGH: 3, MEDIUM: 2, LOW: 1 };
  matched.sort((a, b) => {
    const diff = sevScore[b.Severity] - sevScore[a.Severity];
    return diff !== 0 ? diff : b.Exposure_Amount - a.Exposure_Amount;
  });

  if (filter?.limit && filter.limit > 0) {
    matched = matched.slice(0, filter.limit);
  }

  return matched.map((e) => {
    const enc = encMap.get(e.Encounter_ID);
    const createdMs = e.Created_Date ? new Date(e.Created_Date).getTime() : nowMs;
    const ageDays = Math.max(0, Math.floor((nowMs - createdMs) / (1000 * 60 * 60 * 24)));

    return {
      exceptionId: e.Exception_ID,
      encounterId: e.Encounter_ID,
      department: enc?.Department || 'General',
      revenueCentre: e.Revenue_Centre,
      controlId: e.Control_ID,
      severity: e.Severity,
      potentialFinancialImpact: Number(e.Exposure_Amount.toFixed(2)),
      status: e.Status,
      ageDays,
      assignedOwner: e.Assigned_To || 'Unassigned',
      description: e.Description,
    };
  });
}

// ============================================================================
// Tool 3: get_department_review_status
// ============================================================================
export interface DepartmentReviewStatusPayload {
  overallClearancePercent: number;
  totalDepartments: number;
  verifiedCount: number;
  pendingCount: number;
  disputedCount: number;
  correctionCount: number;
  departments: Array<{
    department: string;
    pendingReviews: number;
    verified: number;
    disputed: number;
    correctionRequired: number;
    clearancePercent: number;
    unbilledExposure: number;
  }>;
}

export function get_department_review_status(
  clearanceRecords: DepartmentClearanceRecord[] = [],
  clearanceSummary?: DepartmentClearanceSummary
): DepartmentReviewStatusPayload {
  const deptMap = new Map<
    string,
    {
      pendingReviews: number;
      verified: number;
      disputed: number;
      correctionRequired: number;
      unbilledExposure: number;
    }
  >();

  clearanceRecords.forEach((r) => {
    const d = r.department || 'General';
    const cur = deptMap.get(d) || {
      pendingReviews: 0,
      verified: 0,
      disputed: 0,
      correctionRequired: 0,
      unbilledExposure: 0,
    };
    if (r.status === 'PENDING_VERIFICATION') cur.pendingReviews++;
    else if (r.status === 'VERIFIED') cur.verified++;
    else if (r.status === 'DISPUTED') cur.disputed++;
    else if (r.status === 'CORRECTION_REQUIRED') cur.correctionRequired++;

    cur.unbilledExposure += r.unbilledExposure || 0;
    deptMap.set(d, cur);
  });

  const departments = Array.from(deptMap.entries()).map(([department, data]) => {
    const total = data.pendingReviews + data.verified + data.disputed + data.correctionRequired;
    const clearancePercent = total > 0 ? Number(((data.verified / total) * 100).toFixed(1)) : 100;
    return {
      department,
      pendingReviews: data.pendingReviews,
      verified: data.verified,
      disputed: data.disputed,
      correctionRequired: data.correctionRequired,
      clearancePercent,
      unbilledExposure: Number(data.unbilledExposure.toFixed(2)),
    };
  });

  return {
    overallClearancePercent: clearanceSummary?.clearancePercent ?? 100,
    totalDepartments: departments.length,
    verifiedCount: clearanceSummary?.verifiedCount ?? 0,
    pendingCount: clearanceSummary?.pendingCount ?? 0,
    disputedCount: clearanceSummary?.disputedCount ?? 0,
    correctionCount: clearanceSummary?.correctionRequiredCount ?? 0,
    departments,
  };
}

// ============================================================================
// Tool 4: get_revenue_performance
// ============================================================================
export interface RevenuePerformancePayload {
  grossBilling: number;
  expectedAmount: number;
  billingCaptureRate: number;
  grossBilledPreDiscount: number;
  unbilledAmount: number;
  revenueByDepartment: Array<{ department: string; amount: number; percentage: number }>;
  revenueByRevenueCentre: Array<{ revenueCentre: string; amount: number }>;
  revenueByPayer: Array<{ payer: string; amount: number; percentage: number }>;
  hasSufficientHistory: boolean;
  revenueTrendMonthsCount: number;
}

export function get_revenue_performance(
  billings: Billing[],
  services: Service[],
  encounters: Encounter[],
  metrics: DashboardMetrics
): RevenuePerformancePayload {
  const encMap = new Map<string, Encounter>();
  encounters.forEach((e) => encMap.set(e.Encounter_ID, e));

  const svcMap = new Map<string, Service>();
  services.forEach((s) => svcMap.set(s.Service_ID, s));

  // Department revenue aggregation
  const deptMap = new Map<string, number>();
  // Revenue centre revenue aggregation
  const revCenterMap = new Map<string, number>();
  // Payer revenue aggregation
  const payerMap = new Map<string, number>();

  billings.forEach((b) => {
    const amt = Number(b.Billed_Amount) || 0;
    const enc = encMap.get(b.Encounter_ID);
    const svc = svcMap.get(b.Service_ID);

    const dept = enc?.Department || 'General';
    deptMap.set(dept, (deptMap.get(dept) || 0) + amt);

    const rc = svc?.Revenue_Centre || 'General';
    revCenterMap.set(rc, (revCenterMap.get(rc) || 0) + amt);

    const payer = enc?.Payer_Type || 'Self Pay';
    payerMap.set(payer, (payerMap.get(payer) || 0) + amt);
  });

  const totalBilled = metrics.grossBilling > 0 ? metrics.grossBilling : 1;

  const revenueByDepartment = Array.from(deptMap.entries())
    .map(([department, amount]) => ({
      department,
      amount: Number(amount.toFixed(2)),
      percentage: Number(((amount / totalBilled) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.amount - a.amount);

  const revenueByRevenueCentre = Array.from(revCenterMap.entries())
    .map(([revenueCentre, amount]) => ({
      revenueCentre,
      amount: Number(amount.toFixed(2)),
    }))
    .sort((a, b) => b.amount - a.amount);

  const revenueByPayer = Array.from(payerMap.entries())
    .map(([payer, amount]) => ({
      payer,
      amount: Number(amount.toFixed(2)),
      percentage: Number(((amount / totalBilled) * 100).toFixed(1)),
    }))
    .sort((a, b) => b.amount - a.amount);

  // Check unique months in billing records
  const uniqueMonths = new Set<string>();
  billings.forEach((b) => {
    const m = (b.Bill_Date || b.Bill_DateTime || '').slice(0, 7);
    if (m && m.length === 7) uniqueMonths.add(m);
  });

  return {
    grossBilling: metrics.grossBilling,
    expectedAmount: metrics.totalExpectedAmount,
    billingCaptureRate: metrics.billingCaptureRate,
    grossBilledPreDiscount: metrics.grossBilledPreDiscount,
    unbilledAmount: Math.max(0, metrics.totalExpectedAmount - metrics.grossBilling),
    revenueByDepartment,
    revenueByRevenueCentre,
    revenueByPayer,
    hasSufficientHistory: uniqueMonths.size > 1,
    revenueTrendMonthsCount: uniqueMonths.size,
  };
}

// ============================================================================
// Tool 5: get_ar_ageing
// ============================================================================
export interface ArAgeingPayload {
  totalAR: number;
  currentAR: number; // 0-30 days
  ar31_60: number;
  ar61_90: number;
  ar90plus: number;
  overdueAR: number; // >30 days
  collectionRealisationRate: number;
  totalBilled: number;
  totalCollected: number;
  asOfDateDisplay: string;
  payerBreakdown: Array<{ payer: string; ar: number; percentage: number }>;
  highValueOverdueAccountsCount: number;
  highValueOverdueAccounts: Array<{
    encounterId: string;
    department: string;
    payerType: string;
    outstandingAR: number;
    daysOutstanding: number;
    bucket: string;
  }>;
}

export function get_ar_ageing(
  encounters: Encounter[],
  billings: Billing[],
  collections: Collection[],
  claims: Claim[],
  asOfDate?: string
): ArAgeingPayload {
  const arSummary = calculateArAgeing(encounters, billings, collections, claims, asOfDate);

  return {
    totalAR: arSummary.totalAR,
    currentAR: arSummary.currentAR,
    ar31_60: arSummary.ar31_60,
    ar61_90: arSummary.ar61_90,
    ar90plus: arSummary.ar90plus,
    overdueAR: arSummary.overdueAR,
    collectionRealisationRate: arSummary.collectionRate,
    totalBilled: arSummary.totalBilled,
    totalCollected: arSummary.totalCollected,
    asOfDateDisplay: arSummary.asOfDateDisplay,
    payerBreakdown: arSummary.payerBreakdown.map((p) => ({
      payer: p.payer,
      ar: p.ar,
      percentage: p.percentage,
    })),
    highValueOverdueAccountsCount: arSummary.highValueOverdueAccounts.length,
    highValueOverdueAccounts: arSummary.highValueOverdueAccounts.slice(0, 5).map((a) => ({
      encounterId: a.encounterId,
      department: a.department,
      payerType: a.payerType,
      outstandingAR: a.outstandingAR,
      daysOutstanding: a.daysOutstanding,
      bucket: a.bucket,
    })),
  };
}

// ============================================================================
// Tool 6: get_tpa_status
// ============================================================================
export interface TpaStatusPayload {
  totalSubmitted: number;
  totalApproved: number;
  totalPending: number;
  totalDisallowed: number;
  clearanceRate: number;
  pendingCount: number;
  approvedCount: number;
  disallowedCount: number;
  totalClaimsCount: number;
  collectionsAgainstApproved: number;
  claimsPendingList: Array<{
    claimId: string;
    encounterId: string;
    claimAmount: number;
    status: string;
    submissionDate: string;
  }>;
}

export function get_tpa_status(claims: Claim[], collections: Collection[]): TpaStatusPayload {
  const totalSubmitted = claims.reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);
  const totalApproved = claims.reduce((s, c) => s + (Number(c.Approved_Amount) || 0), 0);
  const totalDisallowed = claims.reduce((s, c) => s + (Number(c.Rejected_Amount) || 0), 0);

  const pendingClaims = getClaimsPendingAdjudication(claims);
  const totalPending = pendingClaims.reduce((s, c) => s + (Number(c.Claim_Amount) || 0), 0);

  const clearanceRate = totalSubmitted > 0 ? Number(((totalApproved / totalSubmitted) * 100).toFixed(1)) : 0;

  // Collections against approved claims
  const approvedEncounters = new Set(
    claims.filter((c) => (Number(c.Approved_Amount) || 0) > 0).map((c) => c.Encounter_ID)
  );
  const collectionsAgainstApproved = collections
    .filter((c) => approvedEncounters.has(c.Encounter_ID))
    .reduce((s, c) => s + (Number(c.Amount) || 0), 0);

  return {
    totalSubmitted: Number(totalSubmitted.toFixed(2)),
    totalApproved: Number(totalApproved.toFixed(2)),
    totalPending: Number(totalPending.toFixed(2)),
    totalDisallowed: Number(totalDisallowed.toFixed(2)),
    clearanceRate,
    pendingCount: pendingClaims.length,
    approvedCount: claims.filter((c) => c.Claim_Status === 'Approved').length,
    disallowedCount: claims.filter((c) => c.Claim_Status === 'Rejected' || (Number(c.Rejected_Amount) || 0) > 0).length,
    totalClaimsCount: claims.length,
    collectionsAgainstApproved: Number(collectionsAgainstApproved.toFixed(2)),
    claimsPendingList: pendingClaims.slice(0, 5).map((c) => ({
      claimId: c.Claim_ID,
      encounterId: c.Encounter_ID,
      claimAmount: c.Claim_Amount,
      status: c.Claim_Status,
      submissionDate: c.Submission_Date,
    })),
  };
}

// ============================================================================
// Tool 7: get_tariff_deviations
// ============================================================================
export interface TariffDeviationsPayload {
  hasTariffData: boolean;
  totalDeviations: number;
  missingTariffCount: number;
  underbillingCount: number;
  overbillingCount: number;
  underbilledExposure: number;
  overbilledExposure: number;
  affectedServiceCodesCount: number;
  topDeviations: Array<{
    serviceCode: string;
    serviceDescription: string;
    payer: string;
    actualBilled: number;
    applicableTariff: number;
    variance: number;
    varianceType: string;
  }>;
}

export function get_tariff_deviations(
  tariffSummary?: TariffIntelligenceSummary,
  deviations: import('../types').TariffDeviationItem[] = []
): TariffDeviationsPayload {
  if (!tariffSummary || tariffSummary.totalServicesAnalyzed === 0) {
    return {
      hasTariffData: false,
      totalDeviations: 0,
      missingTariffCount: 0,
      underbillingCount: 0,
      overbillingCount: 0,
      underbilledExposure: 0,
      overbilledExposure: 0,
      affectedServiceCodesCount: 0,
      topDeviations: [],
    };
  }

  const topDeviations = deviations.slice(0, 5).map((d) => ({
    serviceCode: d.serviceCode,
    serviceDescription: d.serviceDescription,
    payer: d.payer,
    actualBilled: d.actualBilled,
    applicableTariff: d.applicableTariff,
    variance: d.variance,
    varianceType: d.varianceType,
  }));

  return {
    hasTariffData: true,
    totalDeviations: tariffSummary.deviationsCount,
    missingTariffCount: tariffSummary.missingTariffCount,
    underbillingCount: tariffSummary.underbillingCount,
    overbillingCount: tariffSummary.overbillingCount,
    underbilledExposure: tariffSummary.underbilledExposure,
    overbilledExposure: tariffSummary.overbilledExposure,
    affectedServiceCodesCount: new Set(deviations.map((d) => d.serviceCode)).size,
    topDeviations,
  };
}

// ============================================================================
// Tool 8: get_budget_variance
// ============================================================================
export type BudgetVariancePayload =
  | {
      available: true;
      month: string;
      totalRevenueBudget: number;
      totalRevenueActual: number;
      totalRevenueVariance: number;
      totalRevenueVariancePercent: number;
      significantVariancesCount: number;
      hasExpenseActuals: boolean;
      totalExpenseBudget: number;
      totalExpenseActual: number | null;
      departments: Array<{
        department: string;
        budget: number;
        actual: number;
        variance: number;
        variancePct: number;
        isSignificant: boolean;
      }>;
    }
  | {
      available: false;
      reason: string;
    };

export function get_budget_variance(
  budgetRecords: BudgetRecord[] = [],
  budgetSummary?: BudgetExecutiveSummary
): BudgetVariancePayload {
  // Strict rule: Only return budget analysis if budget records actually exist
  if (!budgetRecords || budgetRecords.length === 0 || !budgetSummary) {
    return {
      available: false,
      reason: 'Budget data has not been uploaded for this reporting period.',
    };
  }

  return {
    available: true,
    month: budgetSummary.month,
    totalRevenueBudget: budgetSummary.totalRevenueBudget,
    totalRevenueActual: budgetSummary.totalRevenueActual,
    totalRevenueVariance: budgetSummary.totalRevenueVariance,
    totalRevenueVariancePercent: budgetSummary.totalRevenueVariancePercent,
    significantVariancesCount: budgetSummary.significantVariancesCount,
    hasExpenseActuals: budgetSummary.hasExpenseActuals,
    totalExpenseBudget: budgetSummary.totalExpenseBudget,
    totalExpenseActual: budgetSummary.totalExpenseActual,
    departments: budgetSummary.departmentSummaries.map((d) => ({
      department: d.department,
      budget: d.revenueBudget,
      actual: d.revenueActual,
      variance: d.revenueVariance,
      variancePct: d.revenueVariancePercent,
      isSignificant: d.isSignificant,
    })),
  };
}

// ============================================================================
// Tool 9: get_exception_details
// ============================================================================
export interface ExceptionDetailsPayload {
  exception: FinancialException | null;
  encounter: Encounter | null;
  relatedServices: Service[];
  relatedBillings: Billing[];
  relatedClaims: Claim[];
  relatedCollections: Collection[];
  calculatedAuditExposure: number;
}

export function get_exception_details(
  exceptionId: string,
  exceptions: FinancialException[],
  encounters: Encounter[],
  services: Service[],
  billings: Billing[],
  claims: Claim[],
  collections: Collection[]
): ExceptionDetailsPayload {
  const matchExc = exceptions.find((e) => e.Exception_ID === exceptionId) || null;
  if (!matchExc) {
    return {
      exception: null,
      encounter: null,
      relatedServices: [],
      relatedBillings: [],
      relatedClaims: [],
      relatedCollections: [],
      calculatedAuditExposure: 0,
    };
  }

  const encId = matchExc.Encounter_ID;
  const matchEnc = encounters.find((e) => e.Encounter_ID === encId) || null;
  const relatedServices = services.filter((s) => s.Encounter_ID === encId);
  const relatedBillings = billings.filter((b) => b.Encounter_ID === encId);
  const relatedClaims = claims.filter((c) => c.Encounter_ID === encId);
  const relatedCollections = collections.filter((c) => c.Encounter_ID === encId);

  return {
    exception: matchExc,
    encounter: matchEnc,
    relatedServices,
    relatedBillings,
    relatedClaims,
    relatedCollections,
    calculatedAuditExposure: matchExc.Exposure_Amount,
  };
}
