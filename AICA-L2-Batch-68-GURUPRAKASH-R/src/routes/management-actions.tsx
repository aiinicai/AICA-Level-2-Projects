import { createFileRoute } from "@tanstack/react-router";
import { ManagementActionsPage } from "@/pages/management-actions-page";

export const Route = createFileRoute("/management-actions")({
  head: () => ({
    meta: [
      { title: "Management Actions — AuditFlow" },
      { name: "description", content: "Agreed corrective actions with action owner, target date, revised dates and current status." },
      { property: "og:title", content: "Management Actions — AuditFlow" },
      { property: "og:description", content: "Agreed corrective actions with action owner, target date, revised dates and current status." },
    ],
  }),
  component: ManagementActionsRoute,
});

function ManagementActionsRoute() {
  return <ManagementActionsPage />;
}
