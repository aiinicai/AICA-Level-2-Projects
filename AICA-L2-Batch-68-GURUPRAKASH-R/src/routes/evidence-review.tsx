import { createFileRoute } from "@tanstack/react-router";
import { EvidenceReviewPage } from "@/pages/evidence-review-page";

export const Route = createFileRoute("/evidence-review")({
  head: () => ({
    meta: [
      { title: "Evidence Review — AuditFlow" },
      { name: "description", content: "Receipt, sufficiency assessment and reviewer sign-off of evidence submitted against each data requirement." },
      { property: "og:title", content: "Evidence Review — AuditFlow" },
      { property: "og:description", content: "Receipt, sufficiency assessment and reviewer sign-off of evidence submitted against each data requirement." },
    ],
  }),
  component: EvidenceReviewPage,
});
