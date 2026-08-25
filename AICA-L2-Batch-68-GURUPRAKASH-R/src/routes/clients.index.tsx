import { createFileRoute } from "@tanstack/react-router";
import { ClientsPage } from "@/pages/clients-page";

export const Route = createFileRoute("/clients/")({
  head: () => ({
    meta: [
      { title: "Clients — AuditFlow" },
      {
        name: "description",
        content:
          "Client master with entity details, audit coordinators, locations, status control and linked engagement counts.",
      },
      { property: "og:title", content: "Clients — AuditFlow" },
      {
        property: "og:description",
        content: "Maintain the audit client master with controlled status changes and full activity history.",
      },
    ],
  }),
  component: ClientsPage,
});
