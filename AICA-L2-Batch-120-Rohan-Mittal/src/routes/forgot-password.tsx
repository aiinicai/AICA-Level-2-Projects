import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { sendPasswordResetEmail } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthCard } from "./auth";
import { errMsg } from "@/lib/app";

export const Route = createFileRoute("/forgot-password")({
  ssr: false,
  head: () => ({
    meta: [
      { title: "Forgot password — Fair Share" },
      { name: "description", content: "Reset your Fair Share password." },
      { property: "og:title", content: "Forgot password — Fair Share" },
      { property: "og:description", content: "Reset your Fair Share password." },
    ],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  return (
    <AuthCard title="Forgot password" subtitle="We'll email you a password reset link.">
      {sent ? (
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Check <b className="text-foreground">{email}</b> for instructions to reset your
            password.
          </p>
          <Button variant="outline" className="w-full" onClick={() => setSent(false)}>
            Send another email
          </Button>
        </div>
      ) : (
        <form
          className="space-y-4"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            try {
              await sendPasswordResetEmail(auth, email.trim());
              setSent(true);
              toast.success("Reset link sent. Check your inbox.");
            } catch (error) {
              toast.error(errMsg(error));
            } finally {
              setBusy(false);
            }
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="e">Email address</Label>
            <Input
              id="e"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              required
            />
          </div>
          <Button className="w-full" type="submit" disabled={busy}>
            {busy ? "Sending..." : "Send reset link"}
          </Button>
        </form>
      )}
      <Link
        to="/auth"
        search={{ redirect: undefined }}
        className="mt-4 block text-center text-sm font-medium text-primary hover:underline"
      >
        Back to sign in
      </Link>
    </AuthCard>
  );
}
