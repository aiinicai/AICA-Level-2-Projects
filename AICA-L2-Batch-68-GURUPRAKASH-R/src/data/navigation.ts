import type { NavigationItem } from "@/types/navigation";

export const NAVIGATION_ITEMS: NavigationItem[] = [
  {
    label: "Dashboard",
    to: "/",
    group: "Overview",
    description: "Portfolio-level view of audit progress, pending items and due dates.",
  },
  {
    label: "Clients",
    to: "/clients",
    group: "Planning",
    description: "Client master containing entity details, departments and key contacts.",
  },
  {
    label: "Audit Engagements",
    to: "/engagements",
    group: "Planning",
    description: "Audit assignments, periods covered, teams and lifecycle stage.",
  },
  {
    label: "Scope and Audit Programme",
    to: "/scope-programme",
    group: "Planning",
    description: "Audit scope, objectives, risks and the linked testing procedures.",
  },
  {
    label: "Data Requirements",
    to: "/data-requirements",
    group: "Execution",
    description: "Information requested from auditees, with ownership and due dates.",
  },
  {
    label: "Evidence Review",
    to: "/evidence-review",
    group: "Execution",
    description: "Receipt, sufficiency assessment and review of audit evidence.",
  },
  {
    label: "Audit Clarifications",
    to: "/clarifications",
    group: "Execution",
    description: "Queries raised to process owners and the clarifications received.",
  },
  {
    label: "Audit Observations",
    to: "/observations",
    group: "Resolution",
    description: "Draft and finalised observations with risk ratings and implications.",
  },
  {
    label: "Management Responses",
    to: "/management-responses",
    group: "Resolution",
    description: "Auditee responses, acceptance position and agreed remediation intent.",
  },
  {
    label: "Management Actions",
    to: "/management-actions",
    group: "Resolution",
    description: "Agreed corrective actions with owners, target dates and status.",
  },
  {
    label: "Final Reporting",
    to: "/final-reporting",
    group: "Resolution",
    description: "Draft and final audit reports issued to management and the committee.",
  },
  {
    label: "Closure Tracking",
    to: "/closure-tracking",
    group: "Resolution",
    description: "Follow-up updates, verification of actions and formal closure.",
  },
  {
    label: "Activity Log",
    to: "/activity-log",
    group: "Administration",
    description: "Chronological record of changes across all audit records.",
  },
  {
    label: "Settings",
    to: "/settings",
    group: "Administration",
    description: "Reference data, numbering conventions and integration configuration.",
  },
];

export const NAVIGATION_GROUP_ORDER: NavigationItem["group"][] = [
  "Overview",
  "Planning",
  "Execution",
  "Resolution",
  "Administration",
];

export function findNavigationItem(pathname: string): NavigationItem | undefined {
  if (pathname === "/") return NAVIGATION_ITEMS[0];
  return NAVIGATION_ITEMS.find((item) => item.to !== "/" && pathname.startsWith(item.to));
}
