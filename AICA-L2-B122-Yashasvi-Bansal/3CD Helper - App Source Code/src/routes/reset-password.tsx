import { createFileRoute } from "@tanstack/react-router";
import { ResetPassword } from "@/components/screens/Auth";

export const Route = createFileRoute("/reset-password")({
  head: () => ({
    meta: [
      { title: "Set a new password · 3CD Helper" },
      { name: "description", content: "Choose a new password for your 3CD Helper account." },
      { property: "og:title", content: "Set a new password · 3CD Helper" },
      { property: "og:description", content: "Choose a new password for your 3CD Helper account." },
    ],
  }),
  component: ResetPassword,
});
