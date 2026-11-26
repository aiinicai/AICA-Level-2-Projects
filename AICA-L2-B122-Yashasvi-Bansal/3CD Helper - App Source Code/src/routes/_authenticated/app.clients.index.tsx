import { createFileRoute } from "@tanstack/react-router";
import Clients from "@/components/screens/Clients";

export const Route = createFileRoute("/_authenticated/app/clients/")({
  head: () => ({ meta: [{ title: "Clients · 3CD Helper" }, { name: "description", content: "Clients in your 3CD Helper firm workspace." }] }),
  validateSearch: (s: Record<string, unknown>): { new?: string } => (s["new"] ? { new: String(s["new"]) } : {}),
  component: Clients,
});
