import { createFileRoute } from "@tanstack/react-router";
import { Terms } from "@/components/screens/Legal";

export const Route = createFileRoute("/terms")({
  head: () => ({
    meta: [
      { title: "Terms of Service · 3CD Helper" },
      { name: "description", content: "Terms of Service for 3CD Helper, the tax audit assistant for Chartered Accountants." },
      { property: "og:title", content: "Terms of Service · 3CD Helper" },
      { property: "og:description", content: "Terms of Service for 3CD Helper, the tax audit assistant for Chartered Accountants." },
    ],
  }),
  component: Terms,
});
