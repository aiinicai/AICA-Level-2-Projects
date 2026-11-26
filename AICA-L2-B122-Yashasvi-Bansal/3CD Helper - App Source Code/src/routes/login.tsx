import { createFileRoute } from "@tanstack/react-router";
import { PublicOnly } from "@/components/PublicOnly";
import { Login } from "@/components/screens/Auth";

function Page() {
  return <PublicOnly><Login /></PublicOnly>;
}

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in · 3CD Helper" },
      { name: "description", content: "Sign in to your 3CD Helper firm workspace." },
      { property: "og:title", content: "Sign in · 3CD Helper" },
      { property: "og:description", content: "Sign in to your 3CD Helper firm workspace." },
    ],
  }),
  component: Page,
});
