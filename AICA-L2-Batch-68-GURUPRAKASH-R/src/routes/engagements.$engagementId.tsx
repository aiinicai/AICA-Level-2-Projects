import { createFileRoute } from "@tanstack/react-router";
import { EngagementDetailPage } from "@/pages/engagement-detail-page";

export const Route = createFileRoute("/engagements/$engagementId")({
  head: () => ({
    meta: [
      { title: "Engagement record — AuditFlow" },
      {
        name: "description",
        content:
          "Engagement overview, lifecycle stage, team, planned dates, workflow actions and the complete activity trail.",
      },
      { property: "og:title", content: "Engagement record — AuditFlow" },
      {
        property: "og:description",
        content: "Full audit engagement record with controlled lifecycle transitions.",
      },
    ],
  }),
  component: EngagementDetailPage,
});
