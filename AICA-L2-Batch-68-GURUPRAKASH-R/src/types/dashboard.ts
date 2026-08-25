import type { LifecycleStage, RiskRating, StatusTone, WorkflowStatus } from "./common";



export interface SummaryMetric {
  key: string;
  label: string;
  value: number | string;
  hint?: string;
  tone?: StatusTone;
}

export interface StageSummaryRow {
  stage: LifecycleStage;
  engagements: number;
}

export interface DepartmentPendingRow {
  department: string;
  dataRequirements: number;
  clarifications: number;
  responses: number;
}

export interface RiskDistributionRow {
  rating: RiskRating;
  count: number;
}

export interface DueDateRow {
  reference: string;
  title: string;
  owner: string;
  dueOn: string;
  status: WorkflowStatus;
}

export interface ActivityEntry {
  id: string;
  actor: string;
  action: string;
  reference?: string;
  occurredAt: string;
}

export interface CompletionMetric {
  label: string;
  completed: number;
  total: number;
}

export interface DashboardSnapshot {
  metrics: SummaryMetric[];
  stageSummary: StageSummaryRow[];
  departmentPending: DepartmentPendingRow[];
  riskDistribution: RiskDistributionRow[];
  upcomingDueDates: DueDateRow[];
  recentActivity: ActivityEntry[];
  auditExecution: CompletionMetric[];
  actionClosure: CompletionMetric[];
}

export interface EngagementLifecycleSample {
  engagementId: string;
  client: string;
  title: string;
  currentStage: LifecycleStage;
  leadAuditor: string;
  periodCovered: string;
}
