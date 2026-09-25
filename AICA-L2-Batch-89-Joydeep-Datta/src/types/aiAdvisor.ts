export interface ActionableTip {
  section: string;
  title: string;
  maxLimit: string;
  currentDeclared: string;
  potentialSavings: string;
  actionRecommendation: string;
  priority: 'High' | 'Medium' | 'Low';
}

export interface HraDeepDive {
  annualHraReceived: number;
  exemptAmount: number;
  taxableHra: number;
  landlordPanRequired: boolean;
  complianceNote: string;
}

export interface RegimeSwitchGuidance {
  actionNeeded: string;
  deadline: string;
  impactOnMonthlyTds: string;
}

export interface PersonalizedFaq {
  question: string;
  answer: string;
}

export interface TaxOptimizationReport {
  recommendedRegime: 'Old' | 'New';
  annualTaxSavings: number;
  monthlyTakeHomeGain: number;
  headline: string;
  executiveSummary: string;
  keyDrivers: string[];
  actionableTips: ActionableTip[];
  hraDeepDive: HraDeepDive;
  regimeSwitchGuidance: RegimeSwitchGuidance;
  personalizedFaqs: PersonalizedFaq[];
}
