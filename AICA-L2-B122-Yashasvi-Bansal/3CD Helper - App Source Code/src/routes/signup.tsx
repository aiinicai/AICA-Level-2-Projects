import { createFileRoute } from "@tanstack/react-router";
import { PublicOnly } from "@/components/PublicOnly";
import { Signup } from "@/components/screens/Auth";

function Page() {
  return <PublicOnly><Signup /></PublicOnly>;
}

export const Route = createFileRoute("/signup")({
  head: () => ({
    meta: [
      { title: "Create your account · 3CD Helper" },
      { name: "description", content: "Create a 3CD Helper account and start a 14-day Pro trial." },
      { property: "og:title", content: "Create your account · 3CD Helper" },
      { property: "og:description", content: "Create a 3CD Helper account and start a 14-day Pro trial." },
    ],
  }),
  component: Page,
});
