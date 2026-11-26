import { createFileRoute } from "@tanstack/react-router";
import Dashboard from "@/components/screens/Dashboard";

export const Route = createFileRoute("/_authenticated/app/")({
  head: () => ({ meta: [{ title: "Dashboard · 3CD Helper" }, { name: "description", content: "Dashboard in your 3CD Helper firm workspace." }] }),
  component: Dashboard,
});
