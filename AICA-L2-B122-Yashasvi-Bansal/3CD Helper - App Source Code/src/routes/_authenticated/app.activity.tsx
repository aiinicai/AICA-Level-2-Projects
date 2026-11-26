import { createFileRoute } from "@tanstack/react-router";
import Activity from "@/components/screens/Activity";

export const Route = createFileRoute("/_authenticated/app/activity")({
  head: () => ({ meta: [{ title: "Activity · 3CD Helper" }, { name: "description", content: "Activity in your 3CD Helper firm workspace." }] }),
  component: Activity,
});
