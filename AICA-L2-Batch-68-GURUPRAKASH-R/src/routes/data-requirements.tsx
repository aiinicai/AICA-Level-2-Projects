import { createFileRoute } from "@tanstack/react-router";
import { DataRequirementsPage } from "@/pages/data-requirements-page";

export const Route = createFileRoute("/data-requirements")({
  head: () => ({
    meta: [
      { title: "Data Requirements — AuditFlow" },
      { name: "description", content: "Information and records requested from auditees, with responsible owner, due date and receipt status." },
      { property: "og:title", content: "Data Requirements — AuditFlow" },
      { property: "og:description", content: "Information and records requested from auditees, with responsible owner, due date and receipt status." },
    ],
  }),
  component: DataRequirementsPage,
});
