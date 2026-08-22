import { createFileRoute } from "@tanstack/react-router";
import { ModulePlaceholder } from "@/components/common/module-placeholder";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Settings — AuditFlow" },
      { name: "description", content: "Reference data, entity numbering conventions, departments and future integration configuration." },
      { property: "og:title", content: "Settings — AuditFlow" },
      { property: "og:description", content: "Reference data, entity numbering conventions, departments and future integration configuration." },
    ],
  }),
  component: SettingsRoute,
});

function SettingsRoute() {
  return (
    <ModulePlaceholder
      title="Settings"
      description="Reference data, entity numbering conventions, departments and future integration configuration."
    />
  );
}
