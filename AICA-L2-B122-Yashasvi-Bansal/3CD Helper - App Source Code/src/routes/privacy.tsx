import { createFileRoute } from "@tanstack/react-router";
import { Privacy } from "@/components/screens/Legal";

export const Route = createFileRoute("/privacy")({
  head: () => ({
    meta: [
      { title: "Privacy Policy · 3CD Helper" },
      { name: "description", content: "How 3CD Helper handles firm and client data." },
      { property: "og:title", content: "Privacy Policy · 3CD Helper" },
      { property: "og:description", content: "How 3CD Helper handles firm and client data." },
    ],
  }),
  component: Privacy,
});
