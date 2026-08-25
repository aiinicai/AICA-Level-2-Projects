import { createFileRoute } from "@tanstack/react-router";
import { FinalReportingPage } from "@/pages/final-reporting-page";

export const Route = createFileRoute("/final-reporting")({
  head: () => ({
    meta: [
      { title: "Final Reporting — AuditFlow" },
      { name: "description", content: "Draft and final internal audit reports issued to management and the audit committee." },
      { property: "og:title", content: "Final Reporting — AuditFlow" },
      { property: "og:description", content: "Draft and final internal audit reports issued to management and the audit committee." },
    ],
  }),
  component: FinalReportingRoute,
});

function FinalReportingRoute() {
  return <FinalReportingPage />;
}
