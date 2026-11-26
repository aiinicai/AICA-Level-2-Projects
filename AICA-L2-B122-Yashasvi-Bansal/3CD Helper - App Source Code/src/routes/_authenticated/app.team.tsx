import { createFileRoute } from "@tanstack/react-router";
import Team from "@/components/screens/Team";

export const Route = createFileRoute("/_authenticated/app/team")({
  head: () => ({ meta: [{ title: "Team · 3CD Helper" }, { name: "description", content: "Team in your 3CD Helper firm workspace." }] }),
  component: Team,
});
