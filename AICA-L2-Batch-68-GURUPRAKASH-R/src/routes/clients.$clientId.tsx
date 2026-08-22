import { createFileRoute } from "@tanstack/react-router";
import { ClientDetailPage } from "@/pages/client-detail-page";

export const Route = createFileRoute("/clients/$clientId")({
  head: () => ({
    meta: [
      { title: "Client record — AuditFlow" },
      {
        name: "description",
        content:
          "Client overview, contacts, locations, linked engagements and the complete activity trail for the selected client.",
      },
      { property: "og:title", content: "Client record — AuditFlow" },
      {
        property: "og:description",
        content: "Full client master record with engagements and audit trail.",
      },
    ],
  }),
  component: ClientDetailPage,
});
