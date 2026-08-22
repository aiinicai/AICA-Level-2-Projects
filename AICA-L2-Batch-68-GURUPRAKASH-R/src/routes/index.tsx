import { createFileRoute } from "@tanstack/react-router";
import { DashboardPage } from "@/pages/dashboard-page";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Audit Dashboard — AuditFlow" },
      {
        name: "description",
        content:
          "Portfolio view of internal audit engagements: pending data requirements, evidence, clarifications, observations and management actions.",
      },
      { property: "og:title", content: "Audit Dashboard — AuditFlow" },
      {
        property: "og:description",
        content:
          "Portfolio view of internal audit engagements, pending items, risk ratings and action closure progress.",
      },
    ],
  }),
  component: DashboardPage,
});
