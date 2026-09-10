import {
  EngagementData,
  MatrixScale,
  RiskLevel,
  StageProgress,
  ComputedMateriality,
} from '../types';

/**
 * combineRisk(probability, magnitude)
 * Maps Low/Medium/High to 0/1/2, sums the two:
 * Sum 0-1 -> "Low"
 * Sum 2 -> "Moderate"
 * Sum 3-4 -> "Significant"
 */
export function combineRisk(probability: MatrixScale, magnitude: MatrixScale): RiskLevel {
  const scaleMap: Record<MatrixScale, number> = {
    Low: 0,
    Medium: 1,
    Moderate: 1,
    High: 2,
  };

  const pVal = scaleMap[probability] ?? 0;
  const mVal = scaleMap[magnitude] ?? 0;
  const sum = pVal + mVal;

  if (sum <= 1) return 'Low';
  if (sum === 2) return 'Moderate';
  return 'Significant';
}

/**
 * Materiality calculation under SA 320
 */
export function computeMateriality(
  configOrAmount: number | { benchmarkAmount: number; omPercent: number; pmPercent: number; ctPercent?: number; clearlyTrivialPercent?: number },
  omPercent?: number,
  pmPercent?: number,
  ctPercent?: number
): ComputedMateriality {
  let benchmarkAmount = 0;
  let omp = 0;
  let pmp = 0;
  let ctp = 0;

  if (typeof configOrAmount === 'object' && configOrAmount !== null) {
    benchmarkAmount = configOrAmount.benchmarkAmount;
    omp = configOrAmount.omPercent;
    pmp = configOrAmount.pmPercent;
    ctp = configOrAmount.clearlyTrivialPercent ?? configOrAmount.ctPercent ?? 5;
  } else {
    benchmarkAmount = Number(configOrAmount) || 0;
    omp = Number(omPercent) || 0;
    pmp = Number(pmPercent) || 0;
    ctp = Number(ctPercent) || 0;
  }

  const safeBenchmark = Math.max(0, Number(benchmarkAmount) || 0);
  const safeOMP = Math.max(0, Number(omp) || 0);
  const safePMP = Math.max(0, Number(pmp) || 0);
  const safeCTP = Math.max(0, Number(ctp) || 0);

  const overallMateriality = safeBenchmark * (safeOMP / 100);
  const performanceMateriality = overallMateriality * (safePMP / 100);
  const clearlyTrivialThreshold = overallMateriality * (safeCTP / 100);

  return {
    overallMateriality: Math.round(overallMateriality),
    performanceMateriality: Math.round(performanceMateriality),
    clearlyTrivialThreshold: Math.round(clearlyTrivialThreshold),
  };
}

/**
 * Indian Rupee formatter with Indian numbering system (Lakhs / Crores notation)
 */
export function formatINR(val: number, includeCurrency = true): string {
  if (val === undefined || val === null || isNaN(val)) return includeCurrency ? '₹ 0' : '0';
  const rounded = Math.round(val);
  const formatted = new Intl.NumberFormat('en-IN', {
    maximumFractionDigits: 0,
  }).format(rounded);
  return includeCurrency ? `₹ ${formatted}` : formatted;
}

/**
 * Indian Rupee compact reader (e.g. ₹ 8.50 Cr or ₹ 59.50 L)
 */
export function formatCompactINR(val: number): string {
  if (!val || isNaN(val)) return '₹ 0';
  const abs = Math.abs(val);
  if (abs >= 10000000) {
    return `₹ ${(val / 10000000).toFixed(2)} Cr`;
  }
  if (abs >= 100000) {
    return `₹ ${(val / 100000).toFixed(2)} L`;
  }
  return formatINR(val);
}

/**
 * Compute stage-by-stage and overall progress
 */
export function computeAllStageProgress(engagement: EngagementData): {
  stages: StageProgress[];
  overallPercent: number;
  totalDone: number;
  totalItems: number;
} {
  const stageDefs: Array<{
    stageNumber: number;
    title: string;
    shortTitle: string;
    saRef: string;
    calc: (e: EngagementData) => { done: number; total: number };
  }> = [
    {
      stageNumber: 1,
      title: 'Engagement & Client Acceptance / Continuance',
      shortTitle: 'Acceptance & Continuance',
      saRef: 'SQC 1 / SA 220',
      calc: (e) => {
        const total = e.acceptanceChecklist.length + 1;
        const doneChecklist = e.acceptanceChecklist.filter((c) => c.status !== 'N.A.' || c.rationale.trim().length > 0).length;
        const doneConclusion = e.acceptanceConclusion ? 1 : 0;
        return { done: Math.min(total, doneChecklist + doneConclusion), total };
      },
    },
    {
      stageNumber: 2,
      title: 'Understanding the Entity & Environment',
      shortTitle: 'Entity Understanding',
      saRef: 'SA 315',
      calc: (e) => {
        const u = e.entityUnderstanding;
        const fields = [
          u.natureOfBusiness,
          u.ownershipAndGovernance,
          u.objectivesAndStrategies,
          u.industryFactors,
          u.regulatoryFactors,
          u.otherExternalFactors,
          u.performanceMeasures,
          u.entityLevelRisks,
        ];
        const done = fields.filter((f) => f && f.trim().length > 15).length;
        return { done, total: fields.length };
      },
    },
    {
      stageNumber: 3,
      title: 'Control Environment Evaluation',
      shortTitle: 'Control Environment',
      saRef: 'SA 315',
      calc: (e) => {
        const factors = e.controlEnvironment.factors;
        const doneFactors = factors.filter((f) => Boolean(f.rating) && f.notes.trim().length > 5).length;
        const doneConclusion = e.controlEnvironment.overallConclusion ? 1 : 0;
        return { done: doneFactors + doneConclusion, total: factors.length + 1 };
      },
    },
    {
      stageNumber: 4,
      title: 'Information Systems & IT Environment',
      shortTitle: 'Information Systems',
      saRef: 'SA 315',
      calc: (e) => {
        const total = Math.max(1, e.itSystems.length) + 2;
        const doneSystems = e.itSystems.filter((s) => s.systemName.trim() && s.purpose.trim()).length;
        const doneReliance = e.itRelianceNotes?.trim().length > 10 ? 1 : 0;
        const doneItgc = e.itgcObservations?.trim().length > 10 ? 1 : 0;
        return { done: doneSystems + doneReliance + doneItgc, total };
      },
    },
    {
      stageNumber: 5,
      title: 'Process Identification & Scoping',
      shortTitle: 'Process Identification',
      saRef: 'SA 315',
      calc: (e) => {
        const total = Math.max(1, e.businessProcesses.length);
        const done = e.businessProcesses.filter((p) => p.processName.trim() && p.owner.trim()).length;
        return { done, total };
      },
    },
    {
      stageNumber: 6,
      title: 'Walkthroughs of Key Business Processes',
      shortTitle: 'Walkthroughs',
      saRef: 'SA 315',
      calc: (e) => {
        const total = Math.max(1, e.walkthroughs.length);
        const done = e.walkthroughs.filter((w) => w.performed && w.observations.trim().length > 5).length;
        return { done, total };
      },
    },
    {
      stageNumber: 7,
      title: 'Risk Assessment at FS Line-Item Level',
      shortTitle: 'FS Line-Item Risks',
      saRef: 'SA 315',
      calc: (e) => {
        const total = e.fsLineItemRisks.length;
        const done = e.fsLineItemRisks.filter((r) => r.inherentRisk !== '' && r.rationale.trim().length > 5).length;
        return { done, total };
      },
    },
    {
      stageNumber: 8,
      title: 'Fraud Risk Assessment',
      shortTitle: 'Fraud Risk Assessment',
      saRef: 'SA 240',
      calc: (e) => {
        const fraudObj = e.fraudRisks || (e as any).fraudRisk || {};
        const addRisks = fraudObj.additionalRisks || fraudObj.identifiedRisks || [];
        const total = 2 + addRisks.length;
        const revPres = fraudObj.revenuePresumption;
        const revRat = (typeof revPres === 'object' && revPres ? revPres.rationale : fraudObj.revenueRationale) || '';
        const doneRev = revRat.trim().length > 5 ? 1 : 0;
        const mgmtOver = fraudObj.managementOverride;
        const mgmtPlan = (typeof mgmtOver === 'object' && mgmtOver ? mgmtOver.plannedResponse : fraudObj.managementOverrideProcedures) || '';
        const doneMgmt = mgmtPlan.trim().length > 5 ? 1 : 0;
        const doneAdd = addRisks.filter((a: any) => (a.rationale || a.plannedProcedures || '').trim().length > 5).length;
        return { done: doneRev + doneMgmt + doneAdd, total };
      },
    },
    {
      stageNumber: 9,
      title: 'Control Risk & Risk Rating Register',
      shortTitle: 'Control Risk Matrix',
      saRef: 'SA 315',
      calc: (e) => {
        const total = Math.max(1, e.controlRiskRegister.length);
        const done = e.controlRiskRegister.filter((c) => c.finalRating && ((c.controlsIdentified || c.associatedControls || '').trim().length > 5)).length;
        return { done, total };
      },
    },
    {
      stageNumber: 10,
      title: 'Materiality Determination',
      shortTitle: 'Materiality (SA 320)',
      saRef: 'SA 320 / SA 450',
      calc: (e) => {
        const total = 5;
        let done = 0;
        if (e.materiality.benchmarkAmount > 0) done++;
        if (e.materiality.omPercent > 0) done++;
        if (e.materiality.pmPercent > 0) done++;
        if (e.materiality.ctPercent > 0) done++;
        if (e.materiality.rationale.trim().length > 15) done++;
        return { done, total };
      },
    },
    {
      stageNumber: 11,
      title: 'Audit Strategy & Responses to Assessed Risks',
      shortTitle: 'Audit Strategy (SA 330)',
      saRef: 'SA 330',
      calc: (e) => {
        const total = Math.max(1, e.auditStrategy.length);
        const done = e.auditStrategy.filter((s) => (s.testOfControls || s.testOfDetails || s.analyticalProcedures) && s.proceduresNotes.trim().length > 5).length;
        return { done, total };
      },
    },
    {
      stageNumber: 12,
      title: 'Audit Planning Memorandum',
      shortTitle: 'Planning Memorandum',
      saRef: 'SA 300',
      calc: (e) => {
        const sections = e.planningMemo.sections;
        const total = Math.max(1, sections.length);
        const done = sections.filter((s) => s.content && s.content.trim().length > 30).length;
        return { done, total };
      },
    },
    {
      stageNumber: 13,
      title: 'Sign-off, Review Notes & Approval',
      shortTitle: 'Sign-off & Review',
      saRef: 'SQC 1 / SA 220',
      calc: (e) => {
        const total = 3;
        let done = 0;
        if (e.signOffReview.preparer.declared && e.signOffReview.preparer.name.trim()) done++;
        if (e.signOffReview.reviewer.conclusion !== 'Pending Review') done++;
        const openNotes = e.signOffReview.reviewNotes.filter((n) => n.status === 'Open').length;
        if (openNotes === 0) done++;
        return { done, total };
      },
    },
  ];

  let sumPercents = 0;
  let totalDoneCount = 0;
  let totalItemCount = 0;

  const stages: StageProgress[] = stageDefs.map((def) => {
    const { done, total } = def.calc(engagement);
    const pct = total > 0 ? Math.round((done / total) * 100) : 0;
    sumPercents += pct;
    totalDoneCount += done;
    totalItemCount += total;
    return {
      stageNumber: def.stageNumber,
      title: def.title,
      shortTitle: def.shortTitle,
      saRef: def.saRef,
      doneCount: done,
      totalCount: total,
      percent: Math.min(100, Math.max(0, pct)),
    };
  });

  const overallPercent = Math.round(sumPercents / stageDefs.length);

  return {
    stages,
    overallPercent: Math.min(100, Math.max(0, overallPercent)),
    totalDone: totalDoneCount,
    totalItems: totalItemCount,
  };
}

/**
 * Determine dynamic outstanding action items from the engagement data
 */
export function getOutstandingItems(engagement: EngagementData): Array<{
  stageNumber: number;
  stageName: string;
  itemText: string;
  urgency: 'High' | 'Medium' | 'Low';
}> {
  const items: Array<{
    stageNumber: number;
    stageName: string;
    itemText: string;
    urgency: 'High' | 'Medium' | 'Low';
  }> = [];

  // Stage 1:
  if (!engagement.acceptanceConclusion || engagement.acceptanceConclusion === 'Declined') {
    items.push({
      stageNumber: 1,
      stageName: 'Client Acceptance',
      itemText: 'Finalize engagement acceptance conclusion and documentation',
      urgency: 'High',
    });
  }

  // Stage 6: Pending walkthroughs
  const pendingWalkthroughs = engagement.walkthroughs.filter((w) => !w.performed);
  if (pendingWalkthroughs.length > 0) {
    items.push({
      stageNumber: 6,
      stageName: 'Walkthroughs',
      itemText: `Complete process walkthrough for: ${pendingWalkthroughs.map((w) => w.processName).slice(0, 2).join(', ')}${pendingWalkthroughs.length > 2 ? ` and ${pendingWalkthroughs.length - 2} more` : ''}`,
      urgency: 'Medium',
    });
  }

  // Stage 7: FS Line items unassessed
  const unratedFS = engagement.fsLineItemRisks.filter((r) => !r.inherentRisk);
  if (unratedFS.length > 0) {
    items.push({
      stageNumber: 7,
      stageName: 'FS Risk Assessment',
      itemText: `Assess inherent risk for ${unratedFS.slice(0, 3).map((r) => r.lineItemName).join(', ')}${unratedFS.length > 3 ? ` (+${unratedFS.length - 3} more)` : ''}`,
      urgency: 'High',
    });
  }

  // Stage 10: Materiality
  if (engagement.materiality.benchmarkAmount <= 0 || engagement.materiality.omPercent <= 0) {
    items.push({
      stageNumber: 10,
      stageName: 'Materiality',
      itemText: 'Establish benchmark amount and overall materiality percentage under SA 320',
      urgency: 'High',
    });
  }

  // Stage 11: Significant risks missing Test of Details (SA 330 violation)
  const nonCompliantSignificant = engagement.auditStrategy.filter(
    (s) => s.riskLevel === 'Significant' && !s.testOfDetails
  );
  if (nonCompliantSignificant.length > 0) {
    items.push({
      stageNumber: 11,
      stageName: 'Audit Strategy',
      itemText: `SA 330 Non-Compliance: Significant risk "${nonCompliantSignificant[0].riskDescription}" requires mandatory Test of Details`,
      urgency: 'High',
    });
  }

  // Stage 13: Open Review Notes
  const openNotes = engagement.signOffReview.reviewNotes.filter((n) => n.status === 'Open');
  if (openNotes.length > 0) {
    items.push({
      stageNumber: 13,
      stageName: 'Review Notes',
      itemText: `${openNotes.length} open reviewer note${openNotes.length > 1 ? 's' : ''} awaiting preparer response / resolution`,
      urgency: 'Medium',
    });
  }

  // Stage 13: Preparer sign-off
  if (!engagement.signOffReview.preparer.declared) {
    items.push({
      stageNumber: 13,
      stageName: 'Sign-off',
      itemText: 'Engagement preparer declaration pending completion',
      urgency: 'Low',
    });
  }

  return items;
}
