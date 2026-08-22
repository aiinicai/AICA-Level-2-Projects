import { createFileRoute } from "@tanstack/react-router";
import { ScopeProgrammePage } from "@/pages/scope-programme-page";

export const Route = createFileRoute("/scope-programme/")({
  head: () => ({
    meta: [
      { title: "Scope and Audit Programme — AuditFlow" },
      {
        name: "description",
        content:
          "Audit scope, objectives, identified risks and the linked testing procedures forming the audit programme.",
      },
      { property: "og:title", content: "Scope and Audit Programme — AuditFlow" },
      {
        property: "og:description",
        content: "Process-level audit scope and the test procedures that execute the audit programme.",
      },
    ],
  }),
  component: () => <ScopeProgrammePage />,
});
