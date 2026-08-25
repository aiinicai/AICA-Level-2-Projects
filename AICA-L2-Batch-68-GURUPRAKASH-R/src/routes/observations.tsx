import { createFileRoute } from "@tanstack/react-router";
import { ObservationsPage } from "@/pages/observations-page";

export const Route = createFileRoute("/observations")({
  head: () => ({
    meta: [
      { title: "Audit Observations — AuditFlow" },
      { name: "description", content: "Draft and finalised audit observations with condition, criteria, cause, effect and risk rating." },
      { property: "og:title", content: "Audit Observations — AuditFlow" },
      { property: "og:description", content: "Draft and finalised audit observations with condition, criteria, cause, effect and risk rating." },
    ],
  }),
  component: AuditObservationsRoute,
});

function AuditObservationsRoute() {
  return <ObservationsPage />;
}
