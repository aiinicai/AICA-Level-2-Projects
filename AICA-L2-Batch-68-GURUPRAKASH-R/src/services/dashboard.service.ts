import { DASHBOARD_SNAPSHOT, ENGAGEMENT_LIFECYCLE_SAMPLES } from "@/data/dashboard.mock";
import type { DashboardSnapshot, EngagementLifecycleSample } from "@/types/dashboard";
import { dueStatusFor } from "@/types/reporting";
import { delay } from "./mock.utils";
import { store } from "./store";
import { deriveRollUp } from "./reporting.support";

export interface DashboardService {
  getSnapshot(): Promise<DashboardSnapshot>;
  getEngagementLifecycleSamples(): Promise<EngagementLifecycleSample[]>;
}

/** Live Stage 4 figures computed from the in-memory store. */
function buildSnapshot(): DashboardSnapshot {
  const observations = store.observations.filter((row) => row.status !== "Dropped");
  const actions = store.managementActions;
  const responses = store.managementResponses;

  const draftObservations = observations.filter((row) =>
    ["Draft", "Under Auditor Review"].includes(row.status),
  ).length;
  const highRisk = observations.filter((row) => row.finalRiskRating === "High").length;
  const responsesPending = responses.filter((row) => row.status !== "Accepted by Auditor").length;
  const overdueActions = actions.filter(
    (row) => dueStatusFor(row.originalTargetDate, row.revisedTargetDate, row.implementationStatus) === "Overdue",
  ).length;
  const closedActions = actions.filter((row) => row.implementationStatus === "Closed").length;

  const riskCounts = { High: 0, Medium: 0, Low: 0 } as Record<"High" | "Medium" | "Low", number>;
  observations.forEach((row) => {
    if (row.finalRiskRating) riskCounts[row.finalRiskRating] += 1;
  });

  const upcoming = actions
    .filter((row) => row.implementationStatus !== "Closed")
    .map((row) => ({
      reference: row.reference,
      title: row.title,
      owner: row.actionOwner,
      dueOn: row.revisedTargetDate || row.originalTargetDate,
      status: row.implementationStatus as DashboardSnapshot["upcomingDueDates"][number]["status"],
    }))
    .sort((a, b) => (a.dueOn || "9999").localeCompare(b.dueOn || "9999"))
    .slice(0, 6);

  return {
    ...DASHBOARD_SNAPSHOT,
    metrics: DASHBOARD_SNAPSHOT.metrics.map((metric) => {
      switch (metric.key) {
        case "draft-observations":
          return { ...metric, value: draftObservations, hint: `${observations.length} observation(s) in total` };
        case "high-risk-observations":
          return { ...metric, value: highRisk, hint: "Requires committee attention" };
        case "responses-pending":
          return { ...metric, value: responsesPending, hint: `${responses.length} response record(s)` };
        case "overdue-actions":
          return { ...metric, value: overdueActions, hint: "Target date lapsed" };
        case "actions-closed":
          return { ...metric, value: closedActions, hint: `${actions.length} action(s) tracked` };
        default:
          return metric;
      }
    }),
    riskDistribution: (["High", "Medium", "Low"] as const).map((rating) => ({
      rating,
      count: riskCounts[rating],
    })),
    upcomingDueDates: upcoming.length ? upcoming : DASHBOARD_SNAPSHOT.upcomingDueDates,
    actionClosure: [
      { label: "Actions verified and closed", completed: closedActions, total: Math.max(actions.length, 1) },
      {
        label: "Observations with closed implementation",
        completed: observations.filter((row) => deriveRollUp(row.id) === "Closed").length,
        total: Math.max(observations.length, 1),
      },
    ],
    recentActivity: store.activity
      .slice()
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, 6)
      .map((entry) => ({
        id: entry.id,
        actor: entry.user,
        action: entry.action,
        reference: entry.recordReference,
        occurredAt: entry.timestamp,
      })),
  };
}

export const dashboardService: DashboardService = {
  getSnapshot: () => delay(buildSnapshot()),
  getEngagementLifecycleSamples: () => delay(ENGAGEMENT_LIFECYCLE_SAMPLES),
};
