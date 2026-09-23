import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "@/components/auth/AuthLayout";

export const Route = createFileRoute("/forgot-password")({
  head: () => ({
    meta: [
      { title: "Reset your password — The DASH" },
      { name: "description", content: "Request a password reset link for your The DASH workspace." },
      { property: "og:title", content: "Reset your password — The DASH" },
      { property: "og:description", content: "Request a password reset link." },
    ],
  }),
  component: ForgotPasswordPage,
});

function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="We'll send a reset link to your work email."
      footer={
        <>
          Remembered it?{" "}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Back to sign in
          </Link>
        </>
      }
    >
      {submitted ? (
        <div className="rounded-lg border bg-surface p-4 text-sm">
          <p className="font-medium">Nothing was sent</p>
          <p className="mt-1 text-muted-foreground">
            Password resets need authentication and email enabled on this workspace. We never pretend an email went out.
          </p>
        </div>
      ) : (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            setSubmitted(true);
          }}
        >
          <div className="space-y-1.5">
            <Label htmlFor="email">Work email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <Button type="submit" className="w-full">
            Send reset link
          </Button>
        </form>
      )}
    </AuthLayout>
  );
}
