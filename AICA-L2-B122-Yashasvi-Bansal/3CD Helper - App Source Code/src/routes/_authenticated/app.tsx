import { createFileRoute, Navigate } from "@tanstack/react-router";
import AppLayout from "@/components/AppLayout";
import { PageLoader } from "@/components/ui";
import { useFirm } from "@/contexts/FirmContext";

export const Route = createFileRoute("/_authenticated/app")({
  head: () => ({ meta: [{ title: "3CD Helper" }, { name: "description", content: "Your 3CD Helper firm workspace." }] }),
  component: RequireFirm,
});

function RequireFirm() {
  const { firm, loading } = useFirm();
  if (loading) return <PageLoader />;
  if (!firm) return <Navigate to="/app/onboarding" replace />;
  return <AppLayout />;
}
