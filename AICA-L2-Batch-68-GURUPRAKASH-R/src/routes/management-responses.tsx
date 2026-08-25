import { createFileRoute } from "@tanstack/react-router";
import { ManagementResponsesPage } from "@/pages/management-responses-page";

export const Route = createFileRoute("/management-responses")({
  head: () => ({
    meta: [
      { title: "Management Responses — AuditFlow" },
      { name: "description", content: "Auditee responses to each observation, including acceptance position and proposed remediation." },
      { property: "og:title", content: "Management Responses — AuditFlow" },
      { property: "og:description", content: "Auditee responses to each observation, including acceptance position and proposed remediation." },
    ],
  }),
  component: ManagementResponsesRoute,
});

function ManagementResponsesRoute() {
  return <ManagementResponsesPage />;
}
