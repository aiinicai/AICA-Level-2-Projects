import { createFileRoute } from "@tanstack/react-router";
import { ModulePlaceholder } from "@/components/common/module-placeholder";

export const Route = createFileRoute("/activity-log")({
  head: () => ({
    meta: [
      { title: "Activity Log — AuditFlow" },
      { name: "description", content: "Chronological record of additions, changes and approvals across all audit records." },
      { property: "og:title", content: "Activity Log — AuditFlow" },
      { property: "og:description", content: "Chronological record of additions, changes and approvals across all audit records." },
    ],
  }),
  component: ActivityLogRoute,
});

function ActivityLogRoute() {
  return (
    <ModulePlaceholder
      title="Activity Log"
      description="Chronological record of additions, changes and approvals across all audit records."
    />
  );
}
