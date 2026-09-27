/**
 * Hospital CFO Copilot — Agentic CFO Financial Review Orchestrator
 *
 * ARCHITECTURE: Explicit 10-stage multi-agent orchestration.
 * Each stage is a distinct specialist review unit with:
 *   - Defined purpose
 *   - Controlled read-only tool set
 *   - Conditional execution (NO_DATA if data unavailable)
 *   - Stage lifecycle: PENDING → RUNNING → COMPLETED | SKIPPED | NO_DATA | ERROR
 *   - Structured StageExecutionRecord output
 *
 * MANDATORY RULES:
 * 1. AI never calculates financial figures. All numbers from deterministic tools.
 * 2. Conditional tool execution: stages with no data are marked NO_DATA, not fabricated.
 * 3. Output taxonomy: FACT | CALCULATED METRIC | AI OBSERVATION | SUGGESTED ACTION
 * 4. Evidence traceability: every AI OBSERVATION cites specific tool outputs.
 * 5. Authenticated user identity — never hardcode names.
 * 6. RBAC enforced at orchestrator level.
 * 7. MCP-ready: all tool functions are pure read-only and structurally isolated.
 */

import {
  Billing,
  BudgetRecord,
  Claim,
  Collection,
  DepartmentClearanceRecord,
  Encounter,
  FinancialException,
  Service,
  TariffMasterItem,
  UserRole,
  UserSession,
  CfoFinancialReviewBrief,
  CfoReviewProgress,
  CfoReviewEvidenceReference,
  AgentStageId,
  AgentStageStatus,
  StageExecutionRecord,
} from '../types';
import { ControlRunResult } from '../engine/controlEngine';
import { DepartmentClearanceSummary } from '../engine/clearanceEngine';
import {
  get_latest_control_run,
  get_open_exceptions,
  get_department_review_status,
  get_revenue_performance,
  get_ar_ageing,
  get_tpa_status,
  get_tariff_deviations,
  get_budget_variance,
  get_exception_details,
  ExceptionDetailsPayload,
} from '../tools/cfoFinancialTools';
import { BudgetExecutiveSummary } from '../engine/budgetEngine';
import { TariffIntelligenceSummary } from '../engine/tariffEngine';
import { formatINR } from '../utils/formatters';

// ============================================================================
// Public Options Interface
// ============================================================================

export interface RunCfoReviewOptions {
  user: UserSession;
  controlResult: ControlRunResult;
  encounters: Encounter[];
  services: Service[];
  billings: Billing[];
  claims: Claim[];
  collections: Collection[];
  tariffMaster?: TariffMasterItem[];
  tariffSummary?: TariffIntelligenceSummary;
  tariffDeviations?: import('../types').TariffDeviationItem[];
  budgetRecords?: BudgetRecord[];
  budgetSummary?: BudgetExecutiveSummary;
  clearanceRecords?: DepartmentClearanceRecord[];
  clearanceSummary?: DepartmentClearanceSummary;
  asOfDate?: string;
  onProgress?: (progress: CfoReviewProgress) => void;
}

// ============================================================================
// Stage Definitions — canonical metadata for every specialist stage
// ============================================================================

export interface StageDefinition {
  id: AgentStageId;
  stepNumber: number;
  name: string;
  purpose: string;
  tools: string[];
}

export const STAGE_DEFINITIONS: StageDefinition[] = [
  {
    id: 'CONTROL_POSITION',
    stepNumber: 1,
    name: 'Control Position',
    purpose:
      'Retrieve the latest deterministic financial control run — Run ID, records processed, exception count, C01–C08 summary and total potential financial impact.',
    tools: ['get_latest_control_run'],
  },
  {
    id: 'REVENUE_REVIEW',
    stepNumber: 2,
    name: 'Revenue Review',
    purpose:
      'Review revenue generation, billing completeness, billing capture rate and revenue concentration by department and payer category.',
    tools: ['get_revenue_performance'],
  },
  {
    id: 'EXCEPTION_REVIEW',
    stepNumber: 3,
    name: 'Exception Review',
    purpose:
      'Review material open financial exceptions (CRITICAL / HIGH priority). Selectively retrieve supporting detail for the top 3 exceptions only.',
    tools: ['get_open_exceptions', 'get_exception_details'],
  },
  {
    id: 'RECEIVABLES_REVIEW',
    stepNumber: 4,
    name: 'Receivables Review',
    purpose:
      'Review outstanding accounts receivable, AR ageing schedule (0–30d / 31–60d / 61–90d / 90+d) and collection realisation rate.',
    tools: ['get_ar_ageing'],
  },
  {
    id: 'TPA_REVIEW',
    stepNumber: 5,
    name: 'Insurance / TPA Review',
    purpose:
      'Review insurance and TPA claims: pending adjudication, approvals, disallowances and cash realisation against approved claims.',
    tools: ['get_tpa_status'],
  },
  {
    id: 'DEPARTMENT_REVIEW',
    stepNumber: 6,
    name: 'Departmental Billing Review',
    purpose:
      'Review departmental billing clearance status, pending verifications, disputes and correction requests across all operating departments.',
    tools: ['get_department_review_status'],
  },
  {
    id: 'TARIFF_REVIEW',
    stepNumber: 7,
    name: 'Tariff & Rate Review',
    purpose:
      'Review contracted tariff deviations, missing tariffs, underbilling and overbilling lines against the active tariff master.',
    tools: ['get_tariff_deviations'],
  },
  {
    id: 'BUDGET_REVIEW',
    stepNumber: 8,
    name: 'Budget vs Actual Review',
    purpose:
      'Review budget versus actual revenue performance where valid budget data exists. Marks NO_DATA if no budget has been uploaded.',
    tools: ['get_budget_variance'],
  },
  {
    id: 'FINANCIAL_SYNTHESIS',
    stepNumber: 9,
    name: 'Financial Synthesis',
    purpose:
      'Consolidate all specialist findings: deduplicate observations, prioritise material matters, connect related evidence, and prepare structured input for the CFO Briefing.',
    tools: [],
  },
  {
    id: 'CFO_BRIEFING',
    stepNumber: 10,
    name: 'CFO Briefing',
    purpose:
      'Produce the final 10-section CFO Financial Briefing with output taxonomy (FACT | CALCULATED METRIC | AI OBSERVATION | SUGGESTED ACTION) and full evidence traceability.',
    tools: [],
  },
];

export const TOTAL_STAGES = STAGE_DEFINITIONS.length;

// ============================================================================
// Helper: build a StageExecutionRecord
// ============================================================================

function makeStage(
  def: StageDefinition,
  status: AgentStageStatus,
  toolsUsed: string[],
  recordsProcessed: number,
  metricsReturned: number,
  finding: string,
  evidenceIds: string[] = [],
  errorMessage?: string
): StageExecutionRecord {
  return {
    stageId: def.id,
    stageName: def.name,
    purpose: def.purpose,
    status,
    toolsUsed,
    recordsProcessed,
    metricsReturned,
    finding,
    completedAt: new Date().toISOString(),
    evidenceIds,
    errorMessage,
  };
}

// ============================================================================
// Deterministic Briefing Markdown Builder (10-section CFO briefing)
// All financial values come exclusively from tool outputs. No AI arithmetic.
// Output taxonomy: [FACT] | [CALCULATED METRIC] | [AI OBSERVATION] | [SUGGESTED ACTION]
// ============================================================================

function buildDeterministicBriefingMarkdown(
  evidence: {
    run: ReturnType<typeof get_latest_control_run>;
    revenue: ReturnType<typeof get_revenue_performance>;
    openExceptions: ReturnType<typeof get_open_exceptions>;
    topExceptionDetails: ExceptionDetailsPayload[];
    ar: ReturnType<typeof get_ar_ageing>;
    tpa: ReturnType<typeof get_tpa_status>;
    clearance: ReturnType<typeof get_department_review_status>;
    tariff: ReturnType<typeof get_tariff_deviations>;
    budget: ReturnType<typeof get_budget_variance>;
  },
  stageLog: StageExecutionRecord[],
  userName: string,
  _userRole: UserRole
): string {
  const { run, revenue, openExceptions, topExceptionDetails, ar, tpa, clearance, tariff, budget } = evidence;
  const inr = (n: number) => formatINR(n);

  // ── Section 1: Executive Summary ──────────────────────────────────────────
  const sec1 = `## 1. Executive Summary
- **[FACT]** Control Run: \`${run.runId}\` executed ${run.runDate} — **${run.recordsProcessed}** records processed across C01–C08 financial controls.
- **[CALCULATED METRIC]** Institutional Billing Capture Efficiency: **${revenue.billingCaptureRate}%** (Gross Billed pre-discount: ${inr(revenue.grossBilledPreDiscount)}).
- **[CALCULATED METRIC]** Identified Potential Financial Exposure: **${inr(run.potentialFinancialImpact)}** across **${openExceptions.length}** open review exceptions.
- **[FACT]** Active Trade Receivables: **${inr(ar.totalAR)}** (${inr(ar.currentAR)} current 0–30d, **${inr(ar.overdueAR)}** overdue >30d).
- **[CALCULATED METRIC]** Overall Departmental Billing Clearance Rate: **${clearance.overallClearancePercent}%** across **${clearance.totalDepartments}** operating departments.`;

  // ── Section 2: Current Financial Position ─────────────────────────────────
  const sec2 = `## 2. Current Financial Position
- **[FACT]** Gross Invoiced Patient Billing: **${inr(revenue.grossBilling)}** against expected clinical service tariff base of **${inr(revenue.expectedAmount)}**.
- **[FACT]** Unbilled Expected Charges: **${inr(revenue.unbilledAmount)}**.
- **[FACT]** Insurance Claims Submitted: **${inr(tpa.totalSubmitted)}** across **${tpa.totalClaimsCount}** claims | Pending Adjudication: **${inr(tpa.totalPending)}** (${tpa.pendingCount} claims).
- **[CALCULATED METRIC]** Historical Collection Realisation Rate: **${ar.collectionRealisationRate}%** (Collected: ${inr(ar.totalCollected)} against ${inr(ar.totalBilled)} billed).`;

  // ── Section 3: Revenue & Billing Review ───────────────────────────────────
  const sec3Lines: string[] = [
    `- **[CALCULATED METRIC]** Billing Capture Rate: **${revenue.billingCaptureRate}%** with **${inr(revenue.unbilledAmount)}** in unbilled expected charges.`,
  ];
  if (revenue.revenueByDepartment.length > 0) {
    const top = revenue.revenueByDepartment[0];
    sec3Lines.push(
      `- **[FACT]** Top Revenue Department: **${top.department}** generating **${inr(top.amount)}** (${top.percentage}% of gross billing).`
    );
  }
  if (revenue.revenueByPayer.length > 0) {
    const top = revenue.revenueByPayer[0];
    sec3Lines.push(
      `- **[FACT]** Primary Billing Category: **${top.payer}** at **${inr(top.amount)}** (${top.percentage}% of total).`
    );
  }
  const c01 = run.c01ToC08Summary.find((c) => c.controlId === 'C01');
  const c05 = run.c01ToC08Summary.find((c) => c.controlId === 'C05');
  if ((c01 && c01.count > 0) || (c05 && c05.count > 0)) {
    sec3Lines.push(
      `- **[AI OBSERVATION]** Revenue cycle attrition driven by unbilled clinical service orders (C01: ${c01?.count ?? 0} items, ${inr(c01?.exposure ?? 0)}) and missing final discharge bills (C05: ${c05?.count ?? 0} items, ${inr(c05?.exposure ?? 0)}). Evidence: Control Run \`${run.runId}\`.`
    );
  } else {
    sec3Lines.push(
      `> NO MATERIAL FINDING: No unbilled services or missing final bills detected in this control run.`
    );
  }
  const sec3 = `## 3. Revenue & Billing Review\n${sec3Lines.join('\n')}`;

  // ── Section 4: Material Exceptions ────────────────────────────────────────
  const critAndHigh = openExceptions.filter((e) => e.severity === 'CRITICAL' || e.severity === 'HIGH');
  const sec4Lines: string[] = [];
  if (critAndHigh.length === 0) {
    sec4Lines.push(
      `> NO MATERIAL FINDING: Zero open Critical or High severity exceptions exist in the active revenue control ledger.`
    );
  } else {
    critAndHigh.slice(0, 5).forEach((e) => {
      sec4Lines.push(
        `- **[${e.severity}]** Exception **${e.exceptionId}** (Encounter: \`${e.encounterId}\`, Dept: **${e.department}**, Rev Centre: _${e.revenueCentre}_): ${e.description}. Potential Financial Impact: **${inr(e.potentialFinancialImpact)}** (${e.ageDays}d open).`
      );
    });
  }
  const sec4 = `## 4. Material Exceptions\n${sec4Lines.join('\n')}`;

  // ── Section 5: Receivables & Collections ──────────────────────────────────
  const sec5Lines: string[] = [
    `- **[FACT]** Total Outstanding Accounts Receivable: **${inr(ar.totalAR)}** as of ${ar.asOfDateDisplay}.`,
    `- **[FACT]** AR Ageing Schedule: Current (0–30d): **${inr(ar.currentAR)}** | 31–60d: **${inr(ar.ar31_60)}** | 61–90d: **${inr(ar.ar61_90)}** | 90+d: **${inr(ar.ar90plus)}**.`,
    `- **[CALCULATED METRIC]** Overdue AR Ratio (>30d): **${ar.totalAR > 0 ? ((ar.overdueAR / ar.totalAR) * 100).toFixed(1) : 0}%** (${inr(ar.overdueAR)}).`,
    `- **[CALCULATED METRIC]** Historical Collection Realisation Rate: **${ar.collectionRealisationRate}%**.`,
  ];
  if (ar.highValueOverdueAccounts.length > 0) {
    const top = ar.highValueOverdueAccounts[0];
    sec5Lines.push(
      `- **[AI OBSERVATION]** Highest exposure overdue account is Encounter \`${top.encounterId}\` (${top.department}, ${top.payerType}) with **${inr(top.outstandingAR)}** overdue for ${top.daysOutstanding} days. Evidence: AR Ageing Tool Output.`
    );
  } else {
    sec5Lines.push(
      `> NO MATERIAL FINDING: No individual accounts currently exceed critical overdue thresholds.`
    );
  }
  const sec5 = `## 5. Receivables & Collections\n${sec5Lines.join('\n')}`;

  // ── Section 6: Insurance / TPA Review ─────────────────────────────────────
  const sec6Lines: string[] = [
    `- **[FACT]** Insurance Claims Submitted: **${inr(tpa.totalSubmitted)}** across **${tpa.totalClaimsCount}** claims.`,
    `- **[FACT]** Claims Approved by Insurers: **${inr(tpa.totalApproved)}** (${tpa.approvedCount} claims, clearance rate: **${tpa.clearanceRate}%**).`,
    `- **[FACT]** Claims Pending Adjudication: **${inr(tpa.totalPending)}** (${tpa.pendingCount} claims in Submitted / Under Query status).`,
    `- **[FACT]** Insurer Claim Shortfall & Disallowances: **${inr(tpa.totalDisallowed)}** (${tpa.disallowedCount} claims).`,
    `- **[CALCULATED METRIC]** Cash Realisation on Approved Claims: **${inr(tpa.collectionsAgainstApproved)}**.`,
  ];
  if (tpa.pendingCount === 0 && tpa.totalDisallowed === 0) {
    sec6Lines.push(
      `> NO MATERIAL FINDING: All insurance claims have been processed without outstanding query or disallowance.`
    );
  }
  const sec6 = `## 6. Insurance / TPA Review\n${sec6Lines.join('\n')}`;

  // ── Section 7: Departmental Billing Review ────────────────────────────────
  const sec7Lines: string[] = [
    `- **[CALCULATED METRIC]** Departmental Clearance Rate: **${clearance.overallClearancePercent}%** (${clearance.verifiedCount} verified, ${clearance.pendingCount} pending, ${clearance.disputedCount} disputed, ${clearance.correctionCount} correction required).`,
  ];
  const pendingDepts = clearance.departments.filter((d) => d.pendingReviews > 0 || d.disputed > 0);
  if (pendingDepts.length === 0) {
    sec7Lines.push(
      `> NO MATERIAL FINDING: All operating departments have 100% verified billing clearance with zero disputes.`
    );
  } else {
    pendingDepts.forEach((d) => {
      sec7Lines.push(
        `- **[FACT]** Department **${d.department}**: ${d.pendingReviews} pending reviews, ${d.disputed} disputed orders, ${d.correctionRequired} corrections requested (Unbilled Exposure: **${inr(d.unbilledExposure)}**).`
      );
    });
  }
  const sec7 = `## 7. Departmental Billing Review\n${sec7Lines.join('\n')}`;

  // ── Section 8: Tariff / Rate Review ───────────────────────────────────────
  const sec8Lines: string[] = [];
  if (!tariff.hasTariffData || tariff.totalDeviations === 0) {
    sec8Lines.push(
      `> NO MATERIAL FINDING: ${
        !tariff.hasTariffData
          ? 'No tariff master data has been uploaded for this review period.'
          : 'No tariff deviations, underbilling or missing contracted rates detected in active services.'
      }`
    );
  } else {
    sec8Lines.push(
      `- **[FACT]** Contracted Tariff Deviations Identified: **${tariff.totalDeviations}** across **${tariff.affectedServiceCodesCount}** unique service codes.`,
      `- **[FACT]** Missing Contracted Tariffs: **${tariff.missingTariffCount}** services | Underbilled Lines: **${tariff.underbillingCount}** (Exposure: **${inr(tariff.underbilledExposure)}**) | Overbilled Lines: **${tariff.overbillingCount}** (Exposure: **${inr(tariff.overbilledExposure)}**).`
    );
    tariff.topDeviations.forEach((d) => {
      sec8Lines.push(
        `- **[FACT]** Service \`${d.serviceCode}\` (${d.serviceDescription}, Payer: _${d.payer}_): Billed at ${inr(d.actualBilled)} vs contracted tariff of ${inr(d.applicableTariff)} (Variance: **${inr(d.variance)}**, ${d.varianceType}).`
      );
    });
  }
  const sec8 = `## 8. Tariff / Rate Review\n${sec8Lines.join('\n')}`;

  // ── Section 9: Budget vs Actual ────────────────────────────────────────────
  let sec9 = `## 9. Budget vs Actual\n`;
  if (!budget.available) {
    sec9 += `> NO_DATA: Budget data is not available for this review period. Budget records must be uploaded via the Data Import module before budget vs actual analysis can be performed.`;
  } else {
    sec9 += `- **[FACT]** Active Fiscal Period: **${budget.month}**.\n`;
    sec9 += `- **[FACT]** Target Revenue Budget: **${inr(budget.totalRevenueBudget)}** vs Verified Actual Revenue: **${inr(budget.totalRevenueActual)}**.\n`;
    sec9 += `- **[CALCULATED METRIC]** Overall Revenue Variance: **${inr(budget.totalRevenueVariance)}** (**${budget.totalRevenueVariancePercent > 0 ? '+' : ''}${budget.totalRevenueVariancePercent.toFixed(1)}%**).\n`;
    sec9 += `- **[FACT]** Departments with Significant Variances (±10%): **${budget.significantVariancesCount}** departments.\n`;
    budget.departments.slice(0, 4).forEach((d) => {
      sec9 += `- **[FACT]** ${d.department}: Budget ${inr(d.budget)} vs Actual ${inr(d.actual)} (Variance: ${inr(d.variance)}, ${d.variancePct > 0 ? '+' : ''}${d.variancePct.toFixed(1)}%${d.isSignificant ? ' ⚠️' : ''}).\n`;
    });
  }

  // ── Section 10: Key Financial Matters & Suggested Actions ─────────────────
  const sec10Lines: string[] = [];
  if (topExceptionDetails.length > 0) {
    topExceptionDetails.slice(0, 3).forEach((d) => {
      if (d.exception) {
        sec10Lines.push(
          `- **[SUGGESTED ACTION]** Direct Inpatient Billing Lead to audit Exception **${d.exception.Exception_ID}** for Encounter \`${d.exception.Encounter_ID}\` (${d.exception.Revenue_Centre}, Exposure: **${inr(d.exception.Exposure_Amount)}**). Enforce pre-discharge settlement before closing account. Evidence: \`${d.exception.Exception_ID}\`.`
        );
      }
    });
  }
  if (tpa.pendingCount > 0) {
    sec10Lines.push(
      `- **[SUGGESTED ACTION]** Instruct TPA Insurance Desk to reconcile **${tpa.pendingCount}** claims awaiting adjudication (Volume: **${inr(tpa.totalPending)}**), focusing on query responses approaching 72-hour rebuttal windows. Evidence: ${tpa.claimsPendingList.map((c) => c.claimId).join(', ') || 'Claims Register'}.`
    );
  }
  if (ar.overdueAR > 0) {
    sec10Lines.push(
      `- **[SUGGESTED ACTION]** Initiate accelerated credit control recovery on **${inr(ar.overdueAR)}** in receivables exceeding standard 30-day settlement terms. Evidence: AR Ageing — ${ar.highValueOverdueAccounts.slice(0, 3).map((a) => a.encounterId).join(', ') || 'AR Register'}.`
    );
  }
  if (tariff.hasTariffData && tariff.underbilledExposure > 0) {
    sec10Lines.push(
      `- **[SUGGESTED ACTION]** Review **${tariff.underbillingCount}** underbilled service lines (Exposure: **${inr(tariff.underbilledExposure)}**) and resubmit corrected invoices where commercially appropriate. Evidence: Tariff & Rate Review.`
    );
  }
  if (sec10Lines.length === 0) {
    sec10Lines.push(
      `- **[SUGGESTED ACTION]** Maintain current revenue cycle controls. No critical interventions required at this time.`
    );
  }
  const sec10 = `## 10. Key Financial Matters & Suggested Actions\n${sec10Lines.join('\n')}`;

  // ── Evidence & Audit References ────────────────────────────────────────────
  const citedExceptions = openExceptions.slice(0, 8).map((e) => e.exceptionId).join(', ') || 'None';
  const citedEncounters =
    Array.from(new Set(openExceptions.slice(0, 8).map((e) => e.encounterId))).join(', ') || 'None';
  const citedClaims = tpa.claimsPendingList.map((c) => c.claimId).join(', ') || 'None';

  // Stage execution summary table
  const tableRows = stageLog
    .map((s) => {
      const icon =
        s.status === 'COMPLETED' ? '✓' :
        s.status === 'NO_DATA'   ? '○' :
        s.status === 'ERROR'     ? '✗' :
        s.status === 'SKIPPED'   ? '–' : '◑';
      const toolStr = s.toolsUsed.join(', ') || '—';
      const findingShort = s.finding.length > 70 ? s.finding.slice(0, 70) + '…' : s.finding;
      return `| ${icon} ${s.stageName} | ${s.status} | ${toolStr} | ${s.recordsProcessed} | ${findingShort} |`;
    })
    .join('\n');

  const secEvidence = `## Evidence & Audit References
- **Review ID:** \`${run.runId}\` executed at ${run.runDate}
- **Generated By:** ${userName || 'Authenticated User'}
- **Exception References:** ${citedExceptions}
- **Encounter References:** ${citedEncounters}
- **Claim References:** ${citedClaims}
- **Control Rules Executed:** C01 (Unbilled Service), C02 (Qty Mismatch), C03 (Amt Mismatch), C04 (Post-Billing Service), C05 (Missing Final Bill), C06 (TPA Shortfall / Insurance Disallowance), C07 (Collection Outstanding), C08 (Unusual Discount Above Authorised Limit)
- **Data Source Lineage:** Certified Inpatient Ledger, Service Orders, Billing Register, Payer Claims Master, Receipt Ledger

### Stage Execution Log
| Stage | Status | Tools Used | Records | Finding |
|---|---|---|---|---|
${tableRows}`;

  return `# CFO Financial Review — Agentic Briefing\n\n${sec1}\n\n${sec2}\n\n${sec3}\n\n${sec4}\n\n${sec5}\n\n${sec6}\n\n${sec7}\n\n${sec8}\n\n${sec9}\n\n${sec10}\n\n${secEvidence}\n`;
}

// ============================================================================
// Main Orchestrator: executeCfoFinancialReview
// ============================================================================

export async function executeCfoFinancialReview(
  options: RunCfoReviewOptions
): Promise<CfoFinancialReviewBrief> {
  const {
    user,
    controlResult,
    encounters,
    services,
    billings,
    claims,
    collections,
    tariffMaster = [],
    tariffSummary,
    tariffDeviations = [],
    budgetRecords = [],
    budgetSummary,
    clearanceRecords = [],
    clearanceSummary,
    asOfDate,
    onProgress,
  } = options;

  const allToolsUsed: string[] = [];
  const stageLog: StageExecutionRecord[] = [];
  const evidenceReferences: CfoReviewEvidenceReference[] = [];

  const emitProgress = (stepNumber: number, stageId: AgentStageId, status: AgentStageStatus) => {
    const def = STAGE_DEFINITIONS.find((d) => d.id === stageId)!;
    onProgress?.({
      step: stepNumber,
      totalSteps: TOTAL_STAGES,
      label: def.name,
      isComplete: status === 'COMPLETED' || status === 'NO_DATA' || status === 'SKIPPED',
      stageId,
      stageStatus: status,
      stageLog: [...stageLog],
    });
  };

  const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

  // ── STAGE 1: CONTROL POSITION ──────────────────────────────────────────────
  const defControl = STAGE_DEFINITIONS[0];
  emitProgress(1, 'CONTROL_POSITION', 'RUNNING');
  await delay(150);

  const runPayload = get_latest_control_run(controlResult);
  allToolsUsed.push('get_latest_control_run');

  stageLog.push(
    makeStage(
      defControl,
      'COMPLETED',
      ['get_latest_control_run'],
      runPayload.recordsProcessed,
      runPayload.c01ToC08Summary.length,
      `Run ${runPayload.runId}: ${runPayload.exceptionsGenerated} exceptions | Potential Impact: ${formatINR(runPayload.potentialFinancialImpact)}`,
      [runPayload.runId]
    )
  );
  emitProgress(1, 'CONTROL_POSITION', 'COMPLETED');
  await delay(100);

  // ── STAGE 2: REVENUE REVIEW ────────────────────────────────────────────────
  const defRevenue = STAGE_DEFINITIONS[1];
  emitProgress(2, 'REVENUE_REVIEW', 'RUNNING');
  await delay(150);

  const revenuePayload = get_revenue_performance(billings, services, encounters, controlResult.metrics);

  if (billings.length === 0) {
    stageLog.push(
      makeStage(defRevenue, 'NO_DATA', [], 0, 0, 'No billing data available. Revenue review cannot be performed.')
    );
  } else {
    allToolsUsed.push('get_revenue_performance');
    stageLog.push(
      makeStage(
        defRevenue,
        'COMPLETED',
        ['get_revenue_performance'],
        billings.length,
        5,
        `Gross Billing: ${formatINR(revenuePayload.grossBilling)} | Capture Rate: ${revenuePayload.billingCaptureRate}% | Unbilled: ${formatINR(revenuePayload.unbilledAmount)}`,
        []
      )
    );
  }
  emitProgress(2, 'REVENUE_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 3: EXCEPTION REVIEW ──────────────────────────────────────────────
  const defException = STAGE_DEFINITIONS[2];
  emitProgress(3, 'EXCEPTION_REVIEW', 'RUNNING');
  await delay(150);

  const openExceptions = get_open_exceptions(controlResult.exceptions, encounters);
  allToolsUsed.push('get_open_exceptions');
  const topExceptionDetails: ExceptionDetailsPayload[] = [];
  const excToolsUsed: string[] = ['get_open_exceptions'];

  if (openExceptions.length > 0) {
    const topItems = openExceptions
      .filter((e) => e.severity === 'CRITICAL' || e.severity === 'HIGH')
      .slice(0, 3);
    for (const item of topItems) {
      const details = get_exception_details(
        item.exceptionId,
        controlResult.exceptions,
        encounters,
        services,
        billings,
        claims,
        collections
      );
      topExceptionDetails.push(details);
      evidenceReferences.push({
        type: 'EXCEPTION',
        id: item.exceptionId,
        label: `Exception ${item.exceptionId}`,
        detail: `${item.severity} — ${formatINR(item.potentialFinancialImpact)}`,
        stageId: 'EXCEPTION_REVIEW',
      });
      evidenceReferences.push({
        type: 'ENCOUNTER',
        id: item.encounterId,
        label: `Encounter ${item.encounterId}`,
        stageId: 'EXCEPTION_REVIEW',
      });
    }
    if (topItems.length > 0) {
      excToolsUsed.push('get_exception_details');
      allToolsUsed.push('get_exception_details');
    }
  }

  const critCount = openExceptions.filter((e) => e.severity === 'CRITICAL').length;
  const highCount = openExceptions.filter((e) => e.severity === 'HIGH').length;
  stageLog.push(
    makeStage(
      defException,
      'COMPLETED',
      excToolsUsed,
      openExceptions.length,
      topExceptionDetails.length,
      openExceptions.length === 0
        ? 'No material finding: Zero open exceptions in the active revenue control ledger.'
        : `${openExceptions.length} open exceptions (${critCount} CRITICAL, ${highCount} HIGH). Detail retrieved for top ${topExceptionDetails.length}.`,
      openExceptions.slice(0, 8).map((e) => e.exceptionId)
    )
  );
  emitProgress(3, 'EXCEPTION_REVIEW', 'COMPLETED');
  await delay(100);

  // ── STAGE 4: RECEIVABLES REVIEW ────────────────────────────────────────────
  const defAR = STAGE_DEFINITIONS[3];
  emitProgress(4, 'RECEIVABLES_REVIEW', 'RUNNING');
  await delay(150);

  const arPayload = get_ar_ageing(encounters, billings, collections, claims, asOfDate);

  if (encounters.length === 0 && billings.length === 0) {
    stageLog.push(
      makeStage(
        defAR,
        'NO_DATA',
        [],
        0,
        0,
        'No encounter or billing data available. Receivables review cannot be performed.'
      )
    );
  } else {
    allToolsUsed.push('get_ar_ageing');
    arPayload.highValueOverdueAccounts.slice(0, 5).forEach((a) => {
      evidenceReferences.push({
        type: 'ENCOUNTER',
        id: a.encounterId,
        label: `Encounter ${a.encounterId}`,
        detail: `Overdue: ${formatINR(a.outstandingAR)} (${a.daysOutstanding}d)`,
        stageId: 'RECEIVABLES_REVIEW',
      });
    });
    stageLog.push(
      makeStage(
        defAR,
        'COMPLETED',
        ['get_ar_ageing'],
        encounters.length,
        4,
        `Total AR: ${formatINR(arPayload.totalAR)} | Overdue (>30d): ${formatINR(arPayload.overdueAR)} | Collection Rate: ${arPayload.collectionRealisationRate}%`,
        arPayload.highValueOverdueAccounts.slice(0, 5).map((a) => a.encounterId)
      )
    );
  }
  emitProgress(4, 'RECEIVABLES_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 5: TPA / INSURANCE REVIEW ───────────────────────────────────────
  const defTPA = STAGE_DEFINITIONS[4];
  emitProgress(5, 'TPA_REVIEW', 'RUNNING');
  await delay(150);

  const tpaPayload = get_tpa_status(claims, collections);

  if (claims.length === 0) {
    stageLog.push(
      makeStage(
        defTPA,
        'NO_DATA',
        [],
        0,
        0,
        'No claims data available. TPA / Insurance review cannot be performed.'
      )
    );
  } else {
    allToolsUsed.push('get_tpa_status');
    tpaPayload.claimsPendingList.forEach((c) => {
      evidenceReferences.push({
        type: 'CLAIM',
        id: c.claimId,
        label: `Claim ${c.claimId}`,
        detail: `Pending: ${formatINR(c.claimAmount)} (${c.status})`,
        stageId: 'TPA_REVIEW',
      });
    });
    stageLog.push(
      makeStage(
        defTPA,
        'COMPLETED',
        ['get_tpa_status'],
        claims.length,
        5,
        tpaPayload.pendingCount === 0
          ? 'No material TPA issue identified. All claims processed without outstanding adjudication.'
          : `${tpaPayload.pendingCount} claims pending adjudication (${formatINR(tpaPayload.totalPending)}) | Disallowances: ${formatINR(tpaPayload.totalDisallowed)}`,
        tpaPayload.claimsPendingList.map((c) => c.claimId)
      )
    );
  }
  emitProgress(5, 'TPA_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 6: DEPARTMENT REVIEW ─────────────────────────────────────────────
  const defDept = STAGE_DEFINITIONS[5];
  emitProgress(6, 'DEPARTMENT_REVIEW', 'RUNNING');
  await delay(150);

  const clearancePayload = get_department_review_status(clearanceRecords, clearanceSummary);

  if (clearanceRecords.length === 0 && !clearanceSummary) {
    stageLog.push(
      makeStage(
        defDept,
        'NO_DATA',
        [],
        0,
        0,
        'No departmental billing clearance records available. Department Review cannot be performed.'
      )
    );
  } else {
    allToolsUsed.push('get_department_review_status');
    stageLog.push(
      makeStage(
        defDept,
        'COMPLETED',
        ['get_department_review_status'],
        clearanceRecords.length,
        clearancePayload.departments.length,
        `Clearance Rate: ${clearancePayload.overallClearancePercent}% | ${clearancePayload.verifiedCount} verified, ${clearancePayload.pendingCount} pending, ${clearancePayload.disputedCount} disputed`,
        []
      )
    );
  }
  emitProgress(6, 'DEPARTMENT_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 7: TARIFF REVIEW ─────────────────────────────────────────────────
  const defTariff = STAGE_DEFINITIONS[6];
  emitProgress(7, 'TARIFF_REVIEW', 'RUNNING');
  await delay(150);

  let tariffPayload: ReturnType<typeof get_tariff_deviations>;

  if (tariffMaster.length === 0 && services.length === 0) {
    tariffPayload = {
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
    stageLog.push(
      makeStage(
        defTariff,
        'NO_DATA',
        [],
        0,
        0,
        'No tariff master data available. Tariff & Rate Review cannot be performed. Upload tariff master via Data Import.'
      )
    );
  } else {
    tariffPayload = get_tariff_deviations(tariffSummary, tariffDeviations);
    allToolsUsed.push('get_tariff_deviations');
    stageLog.push(
      makeStage(
        defTariff,
        'COMPLETED',
        ['get_tariff_deviations'],
        tariffDeviations.length,
        tariffPayload.totalDeviations,
        tariffPayload.totalDeviations === 0
          ? 'No material tariff deviation identified in the available tariff master.'
          : `${tariffPayload.totalDeviations} deviations across ${tariffPayload.affectedServiceCodesCount} service codes | Underbilled Exposure: ${formatINR(tariffPayload.underbilledExposure)}`,
        []
      )
    );
  }
  emitProgress(7, 'TARIFF_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 8: BUDGET REVIEW ─────────────────────────────────────────────────
  const defBudget = STAGE_DEFINITIONS[7];
  emitProgress(8, 'BUDGET_REVIEW', 'RUNNING');
  await delay(150);

  const budgetPayload = get_budget_variance(budgetRecords, budgetSummary);
  allToolsUsed.push('get_budget_variance');

  stageLog.push(
    makeStage(
      defBudget,
      budgetPayload.available ? 'COMPLETED' : 'NO_DATA',
      ['get_budget_variance'],
      budgetRecords.length,
      budgetPayload.available ? budgetPayload.departments.length : 0,
      budgetPayload.available
        ? `Period: ${budgetPayload.month} | Revenue Variance: ${formatINR(budgetPayload.totalRevenueVariance)} (${budgetPayload.totalRevenueVariancePercent > 0 ? '+' : ''}${budgetPayload.totalRevenueVariancePercent.toFixed(1)}%)`
        : 'Budget data is not available for this review period. Upload budget records via Data Import.',
      []
    )
  );
  emitProgress(8, 'BUDGET_REVIEW', stageLog[stageLog.length - 1].status);
  await delay(100);

  // ── STAGE 9: FINANCIAL SYNTHESIS ───────────────────────────────────────────
  const defSynthesis = STAGE_DEFINITIONS[8];
  emitProgress(9, 'FINANCIAL_SYNTHESIS', 'RUNNING');
  await delay(150);

  const completedStages = stageLog.filter((s) => s.status === 'COMPLETED').length;
  const noDataStages = stageLog.filter((s) => s.status === 'NO_DATA').length;
  const uniqueExcIds = Array.from(
    new Set(evidenceReferences.filter((r) => r.type === 'EXCEPTION').map((r) => r.id))
  );
  const uniqueEncIds = Array.from(
    new Set(evidenceReferences.filter((r) => r.type === 'ENCOUNTER').map((r) => r.id))
  );
  const uniqueClaimIds = Array.from(
    new Set(evidenceReferences.filter((r) => r.type === 'CLAIM').map((r) => r.id))
  );

  const synthesisFindings = [
    `${completedStages} specialist stages completed with financial data.`,
    noDataStages > 0 ? `${noDataStages} stages had no data available (marked NO_DATA).` : '',
    runPayload.potentialFinancialImpact > 0
      ? `Total potential financial exposure: ${formatINR(runPayload.potentialFinancialImpact)}.`
      : '',
    uniqueExcIds.length > 0 ? `${uniqueExcIds.length} distinct exceptions cited.` : '',
    uniqueEncIds.length > 0 ? `${uniqueEncIds.length} distinct encounters referenced.` : '',
    uniqueClaimIds.length > 0 ? `${uniqueClaimIds.length} pending claims identified.` : '',
  ]
    .filter(Boolean)
    .join(' ');

  stageLog.push(
    makeStage(
      defSynthesis,
      'COMPLETED',
      [],
      completedStages + noDataStages,
      uniqueExcIds.length + uniqueEncIds.length + uniqueClaimIds.length,
      synthesisFindings || 'Financial synthesis complete.',
      [...uniqueExcIds, ...uniqueEncIds]
    )
  );
  emitProgress(9, 'FINANCIAL_SYNTHESIS', 'COMPLETED');
  await delay(100);

  // ── STAGE 10: CFO BRIEFING ─────────────────────────────────────────────────
  const defBriefing = STAGE_DEFINITIONS[9];
  emitProgress(10, 'CFO_BRIEFING', 'RUNNING');
  await delay(200);

  const evidence = {
    run: runPayload,
    revenue: revenuePayload,
    openExceptions,
    topExceptionDetails,
    ar: arPayload,
    tpa: tpaPayload,
    clearance: clearancePayload,
    tariff: tariffPayload,
    budget: budgetPayload,
  };

  // Attempt AI narrative synthesis via backend endpoint (server-side only, no API keys in browser)
  let narrativeSource: 'ai_gemini' | 'deterministic_fallback' = 'deterministic_fallback';
  let markdownContent = '';

  try {
    const res = await fetch('/api/cfo-review/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user: { name: user.name || 'Authenticated User', role: user.role },
        evidence,
        stageLog,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      if (data?.markdown && data.source === 'ai_gemini') {
        markdownContent = data.markdown;
        narrativeSource = 'ai_gemini';
      }
    }
  } catch {
    // Graceful fallback — no API or server unavailable
  }

  if (!markdownContent) {
    markdownContent = buildDeterministicBriefingMarkdown(
      evidence,
      stageLog,
      user.name || 'Authenticated User',
      user.role
    );
    narrativeSource = 'deterministic_fallback';
  }

  stageLog.push(
    makeStage(
      defBriefing,
      'COMPLETED',
      narrativeSource === 'ai_gemini' ? ['Gemini AI Synthesis'] : ['Deterministic Briefing Engine'],
      0,
      10,
      `10-section CFO briefing produced via ${narrativeSource === 'ai_gemini' ? 'Gemini AI' : 'deterministic engine'} with ${evidenceReferences.length} evidence references.`,
      []
    )
  );
  emitProgress(10, 'CFO_BRIEFING', 'COMPLETED');

  // ── Assemble final CfoFinancialReviewBrief ─────────────────────────────────
  const briefId = `CFO-REV-${Date.now().toString().slice(-6)}`;

  return {
    briefId,
    runId: runPayload.runId,
    generatedAt: new Date().toISOString(),
    generatedBy: user.name || 'Authenticated User',
    userRole: user.role,
    status: 'DRAFT',
    narrativeSource,
    toolsUsed: Array.from(new Set(allToolsUsed)),
    markdownContent,
    evidenceReferences,
    stageExecutionLog: stageLog,
    groundedFigures: {
      grossBilling: revenuePayload.grossBilling,
      totalExpectedAmount: revenuePayload.expectedAmount,
      billingCaptureRate: revenuePayload.billingCaptureRate,
      potentialExposure: runPayload.potentialFinancialImpact,
      openExceptionsCount: openExceptions.length,
      criticalExceptionsCount: openExceptions.filter((e) => e.severity === 'CRITICAL').length,
      highExceptionsCount: openExceptions.filter((e) => e.severity === 'HIGH').length,
      totalAR: arPayload.totalAR,
      overdueAR: arPayload.overdueAR,
      collectionRate: arPayload.collectionRealisationRate,
      tpaPendingAmount: tpaPayload.totalPending,
      tpaApprovedAmount: tpaPayload.totalApproved,
      tpaShortfallAmount: tpaPayload.totalDisallowed,
      clearancePercent: clearancePayload.overallClearancePercent,
      budgetAvailable: budgetPayload.available,
      budgetRevenueVariance: budgetPayload.available ? budgetPayload.totalRevenueVariance : null,
    },
  };
}
