import { createFileRoute } from "@tanstack/react-router";
import Onboarding from "@/components/screens/Onboarding";

export const Route = createFileRoute("/_authenticated/app_/onboarding")({
  head: () => ({ meta: [{ title: "Set up your firm · 3CD Helper" }, { name: "description", content: "Set up your firm in your 3CD Helper firm workspace." }] }),
  component: Onboarding,
});
