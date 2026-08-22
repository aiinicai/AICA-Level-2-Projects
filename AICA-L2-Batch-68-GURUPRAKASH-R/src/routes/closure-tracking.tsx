import { createFileRoute } from "@tanstack/react-router";
import { ClosureTrackingPage } from "@/pages/closure-tracking-page";

export const Route = createFileRoute("/closure-tracking")({
  head: () => ({
    meta: [
      { title: "Closure Tracking — AuditFlow" },
      { name: "description", content: "Follow-up updates, verification of implemented actions and formal closure of observations." },
      { property: "og:title", content: "Closure Tracking — AuditFlow" },
      { property: "og:description", content: "Follow-up updates, verification of implemented actions and formal closure of observations." },
    ],
  }),
  component: ClosureTrackingRoute,
});

function ClosureTrackingRoute() {
  return <ClosureTrackingPage />;
}
