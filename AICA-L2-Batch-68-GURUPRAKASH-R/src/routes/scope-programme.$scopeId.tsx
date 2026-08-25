import { createFileRoute } from "@tanstack/react-router";
import { ScopeDetailPage } from "@/pages/scope-detail-page";

export const Route = createFileRoute("/scope-programme/$scopeId")({
  head: () => ({
    meta: [
      { title: "Scope record — AuditFlow" },
      {
        name: "description",
        content: "Scope definition, key risk, expected control and the test procedures executed under it.",
      },
      { property: "og:title", content: "Scope record — AuditFlow" },
      {
        property: "og:description",
        content: "Scope definition and the linked audit programme procedures.",
      },
    ],
  }),
  component: ScopeDetailPage,
});
