import { createFileRoute } from "@tanstack/react-router";
import Profile from "@/components/screens/Profile";

export const Route = createFileRoute("/_authenticated/app/profile")({
  head: () => ({ meta: [{ title: "My profile · 3CD Helper" }, { name: "description", content: "My profile in your 3CD Helper firm workspace." }] }),
  component: Profile,
});
