import { createFileRoute } from "@tanstack/react-router";
import FirmSettings from "@/components/screens/FirmSettings";

export const Route = createFileRoute("/_authenticated/app/settings")({
  head: () => ({ meta: [{ title: "Firm settings · 3CD Helper" }, { name: "description", content: "Firm settings in your 3CD Helper firm workspace." }] }),
  component: FirmSettings,
});
