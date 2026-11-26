import { createFileRoute } from "@tanstack/react-router";
import ClientDetail from "@/components/screens/ClientDetail";

export const Route = createFileRoute("/_authenticated/app/clients/$clientId")({
  head: () => ({ meta: [{ title: "Client · 3CD Helper" }, { name: "description", content: "Client in your 3CD Helper firm workspace." }] }),
  component: ClientDetail,
});
