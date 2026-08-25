import { createFileRoute } from "@tanstack/react-router";
import { EngagementsPage } from "@/pages/engagements-page";

export const Route = createFileRoute("/engagements/")({
  head: () => ({
    meta: [
      { title: "Audit Engagements — AuditFlow" },
      {
        name: "description",
        content:
          "Audit engagement register with client, audit period, planned dates, lifecycle stage and controlled status transitions.",
      },
      { property: "og:title", content: "Audit Engagements — AuditFlow" },
      {
        property: "og:description",
        content: "Track each internal audit engagement through its full lifecycle.",
      },
    ],
  }),
  component: EngagementsPage,
});
