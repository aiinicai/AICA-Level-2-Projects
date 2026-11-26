import { createFileRoute } from "@tanstack/react-router";
import Engagement from "@/components/screens/Engagement";

export const Route = createFileRoute("/_authenticated/app/engagements/$engagementId")({
  head: () => ({ meta: [{ title: "Assessment year · 3CD Helper" }, { name: "description", content: "Assessment year in your 3CD Helper firm workspace." }] }),
  validateSearch: (s: Record<string, unknown>): { tab?: string; m?: string } => ({
    ...(typeof s["tab"] === "string" ? { tab: s["tab"] } : {}),
    ...(typeof s["m"] === "string" ? { m: s["m"] } : {}),
  }),
  component: Engagement,
});
