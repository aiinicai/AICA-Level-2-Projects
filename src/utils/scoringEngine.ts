import { PerformanceTier, ActionPlanStatus } from '../types';

export interface ScoreBreakdown {
  serviceDeliveryPoints: number;
  taskSLAPunctuality: number;
  officeAttendancePunctuality: number;
  growthDeltaPct: number;
  growthDeltaScore: number;
  weightedServicePoints: number;
  weightedTaskSLA: number;
  weightedAttendance: number;
  weightedGrowth: number;
  baseScore: number;
  tenureYears: number;
  loyaltyMultiplier: number;
  finalWeightedScore: number;
  performanceTier: PerformanceTier;
  actionPlanStatus: ActionPlanStatus;
}

/**
 * Calculates Tenure Loyalty Multiplier according to Abu Dhabi Enterprise Policy:
 * 0 - 2 Years: 1.00x
 * 2 - 5 Years: 1.05x (+5% boost)
 * 5 - 8 Years: 1.10x (+10% boost + Annual Loyalty Bonus)
 * 8+ Years: 1.15x (+15% boost + Senior Merit Recognition)
 */
export function getLoyaltyMultiplier(tenureYears: number): number {
  if (tenureYears >= 8) return 1.15;
  if (tenureYears >= 5) return 1.10;
  if (tenureYears >= 2) return 1.05;
  return 1.00;
}

export function getLoyaltyTierInfo(tenureYears: number) {
  if (tenureYears >= 8) {
    return {
      tierName: 'Senior Merit Circle',
      multiplier: 1.15,
      boostPct: '+15%',
      perks: ['Senior Merit Recognition', 'Priority Strategic Mobility', 'Tier-1 Retention Allowance', 'ADGM Executive Fellowship'],
      badgeColor: 'teal',
    };
  }
  if (tenureYears >= 5) {
    return {
      tierName: 'Tenure Distinction Tier',
      multiplier: 1.10,
      boostPct: '+10%',
      perks: ['Annual Loyalty Bonus Eligibility', 'Pay-Grade Step Increment Fast-Track', 'Executive Health Coverage Upgrade'],
      badgeColor: 'teal',
    };
  }
  if (tenureYears >= 2) {
    return {
      tierName: 'Growth Contributor Tier',
      multiplier: 1.05,
      boostPct: '+5%',
      perks: ['Loyalty Retention Multiplier', 'Specialized Professional Certifications AED 15,000 allowance'],
      badgeColor: 'blue',
    };
  }
  return {
    tierName: 'Foundation Onboarding Tier',
    multiplier: 1.00,
    boostPct: 'Base 1.0x',
    perks: ['Standard Annual Review', 'Foundational L&D Academy Access'],
    badgeColor: 'slate',
  };
}

/**
 * Normalized growth delta score (0-100) based on % improvement compared to previous appraisal
 */
export function normalizeGrowthScore(growthDeltaPct: number): number {
  // Baseline 0% improvement corresponds to 75 points.
  // +10% improvement gives ~95 points; -10% gives ~55 points.
  const calculated = 75 + (growthDeltaPct * 2.0);
  return Math.min(100, Math.max(20, Math.round(calculated * 10) / 10));
}

/**
 * Core Scoring Formula:
 * Total Score = (Service Delivery Points * 0.50) + (Task SLA Punctuality * 0.25)
 *             + (Office Attendance Punctuality * 0.15) + (Growth Delta Score * 0.10)
 * Final Score = Total Score * Loyalty Multiplier
 */
export function calculatePerformanceScore(params: {
  serviceDeliveryPoints: number;
  taskSLAPunctuality: number;
  officeAttendancePunctuality: number;
  growthDeltaPct: number;
  tenureYears: number;
  consecutiveUnderperformingCycles?: number;
}): ScoreBreakdown {
  const {
    serviceDeliveryPoints,
    taskSLAPunctuality,
    officeAttendancePunctuality,
    growthDeltaPct,
    tenureYears,
    consecutiveUnderperformingCycles = 0,
  } = params;

  const growthDeltaScore = normalizeGrowthScore(growthDeltaPct);

  const weightedServicePoints = serviceDeliveryPoints * 0.50;
  const weightedTaskSLA = taskSLAPunctuality * 0.25;
  const weightedAttendance = officeAttendancePunctuality * 0.15;
  const weightedGrowth = growthDeltaScore * 0.10;

  const rawBase = weightedServicePoints + weightedTaskSLA + weightedAttendance + weightedGrowth;
  const baseScore = Math.min(100, Math.max(0, Math.round(rawBase * 10) / 10));

  const loyaltyMultiplier = getLoyaltyMultiplier(tenureYears);
  const finalRaw = baseScore * loyaltyMultiplier;
  const finalWeightedScore = Math.min(115, Math.round(finalRaw * 10) / 10);

  // Determine Performance Tier
  let performanceTier: PerformanceTier = 'Meets';
  if (finalWeightedScore >= 90) {
    performanceTier = 'Exceeds';
  } else if (finalWeightedScore >= 75) {
    performanceTier = 'Meets';
  } else if (finalWeightedScore >= 60) {
    performanceTier = 'Needs_Support';
  } else {
    performanceTier = 'Underperforming';
  }

  // Determine Action Plan Status based on Progressive Escalation Pathway
  let actionPlanStatus: ActionPlanStatus = 'Standard';
  if (performanceTier === 'Needs_Support') {
    actionPlanStatus = 'Coaching';
  } else if (performanceTier === 'Underperforming') {
    if (consecutiveUnderperformingCycles >= 3) {
      actionPlanStatus = 'Escalation_Review';
    } else if (consecutiveUnderperformingCycles === 2) {
      actionPlanStatus = 'PIP_Level_2';
    } else {
      actionPlanStatus = 'PIP_Level_1';
    }
  }

  return {
    serviceDeliveryPoints,
    taskSLAPunctuality,
    officeAttendancePunctuality,
    growthDeltaPct,
    growthDeltaScore,
    weightedServicePoints: Math.round(weightedServicePoints * 10) / 10,
    weightedTaskSLA: Math.round(weightedTaskSLA * 10) / 10,
    weightedAttendance: Math.round(weightedAttendance * 10) / 10,
    weightedGrowth: Math.round(weightedGrowth * 10) / 10,
    baseScore,
    tenureYears,
    loyaltyMultiplier,
    finalWeightedScore,
    performanceTier,
    actionPlanStatus,
  };
}

export function getTierMetadata(tier: PerformanceTier) {
  switch (tier) {
    case 'Exceeds':
      return {
        label: 'Exceeds Expectations',
        sublabel: 'Strategic Contributor & Merit Recognition Track',
        colorClass: 'text-teal-700 bg-teal-50 border-teal-200',
        badgeBg: 'bg-teal-500',
        colorText: 'text-teal-700',
      };
    case 'Meets':
      return {
        label: 'Meets Expectations',
        sublabel: 'Consistent Target Achievement & Growth Track',
        colorClass: 'text-blue-700 bg-blue-50 border-blue-200',
        badgeBg: 'bg-blue-600',
        colorText: 'text-blue-700',
      };
    case 'Needs_Support':
      return {
        label: 'Development Opportunity',
        sublabel: 'Tier 1: Skill Upgrade Action Plan (Non-Financial)',
        colorClass: 'text-amber-700 bg-amber-50 border-amber-200',
        badgeBg: 'bg-amber-500',
        colorText: 'text-amber-700',
      };
    case 'Underperforming':
      return {
        label: 'Accelerated Intervention',
        sublabel: 'Progressive Support & Mentorship Governance',
        colorClass: 'text-rose-700 bg-rose-50 border-rose-200',
        badgeBg: 'bg-rose-600',
        colorText: 'text-rose-700',
      };
  }
}
