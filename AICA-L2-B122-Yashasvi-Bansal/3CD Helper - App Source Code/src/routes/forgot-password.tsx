import { createFileRoute } from "@tanstack/react-router";
import { ForgotPassword } from "@/components/screens/Auth";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset password · 3CD Helper" },
      { name: "description", content: "Get a secure link to set a new 3CD Helper password." },
      { property: "og:title", content: "Reset password · 3CD Helper" },
      { property: "og:description", content: "Get a secure link to set a new 3CD Helper password." },
    ],
  }),
  component: ForgotPassword,
});
