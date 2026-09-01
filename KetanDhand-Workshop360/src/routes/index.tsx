import { createFileRoute } from "@tanstack/react-router";
import { AppShell } from "@/components/AppShell";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Seth Auto Spares — Workshop Repair & Billing" },
      {
        name: "description",
        content:
          "Track motorcycle repairs, parts, mechanics and billing for Seth Auto Spares from any phone or desktop.",
      },
      { property: "og:title", content: "Seth Auto Spares — Workshop Repair & Billing" },
      {
        property: "og:description",
        content:
          "Track motorcycle repairs, parts, mechanics and billing for Seth Auto Spares from any phone or desktop.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return <AppShell />;
}
