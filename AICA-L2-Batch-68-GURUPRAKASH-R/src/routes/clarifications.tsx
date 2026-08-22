import { createFileRoute } from "@tanstack/react-router";
import { ClarificationsPage } from "@/pages/clarifications-page";

export const Route = createFileRoute("/clarifications")({
  head: () => ({
    meta: [
      { title: "Audit Clarifications — AuditFlow" },
      { name: "description", content: "Queries raised with process owners during fieldwork and the clarifications received in response." },
      { property: "og:title", content: "Audit Clarifications — AuditFlow" },
      { property: "og:description", content: "Queries raised with process owners during fieldwork and the clarifications received in response." },
    ],
  }),
  component: ClarificationsPage,
});
