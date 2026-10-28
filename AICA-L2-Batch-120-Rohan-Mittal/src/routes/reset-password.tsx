import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { updatePassword, confirmPasswordReset } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard } from "./auth";
import { errMsg } from "@/lib/app";

export const Route = createFileRoute("/reset-password")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>) => ({
    oobCode: typeof s["oobCode"] === "string" ? s["oobCode"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Set new password — Fair Share" },
      { name: "description", content: "Choose a new password for Fair Share." },
      { property: "og:title", content: "Set new password — Fair Share" },
      { property: "og:description", content: "Choose a new password for Fair Share." },
    ],
  }),
  component: ResetPasswordPage,
});

function ResetPasswordPage() {
  const { oobCode } = Route.useSearch();
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  return (
    <AuthCard
      title="Set a new password"
      subtitle="Choose something secure (at least 6 characters)."
    >
      <form
        className="space-y-4"
        onSubmit={async (e) => {
          e.preventDefault();
          if (pw.length < 6) return toast.error("Password must be at least 6 characters");
          if (pw !== pw2) return toast.error("Passwords don't match");
          setBusy(true);
          try {
            if (oobCode) {
              await confirmPasswordReset(auth, oobCode, pw);
              toast.success("Password updated successfully. Please sign in.");
              navigate({ to: "/auth", search: { redirect: undefined } });
            } else if (auth.currentUser) {
              await updatePassword(auth.currentUser, pw);
              toast.success("Password updated successfully");
              navigate({ to: "/" });
            } else {
              toast.error("Please request a password reset link first.");
              navigate({ to: "/forgot-password" });
            }
          } catch (error) {
            toast.error(errMsg(error));
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="a">New password</Label>
          <Input
            id="a"
            type="password"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            required
            minLength={6}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="b">Confirm password</Label>
          <Input
            id="b"
            type="password"
            value={pw2}
            onChange={(e) => setPw2(e.target.value)}
            required
            minLength={6}
          />
        </div>
        <Button className="w-full" type="submit" disabled={busy}>
          {busy ? "Updating..." : "Update password"}
        </Button>
      </form>
    </AuthCard>
  );
}
