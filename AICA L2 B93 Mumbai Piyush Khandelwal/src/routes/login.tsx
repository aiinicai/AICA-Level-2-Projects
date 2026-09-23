import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable/index";
import { toast } from "sonner";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — The DASH" },
      { name: "description", content: "Sign in to The DASH to open your business dashboards, reports and alerts." },
      { property: "og:title", content: "Sign in — The DASH" },
      { property: "og:description", content: "Open your business dashboards, reports and alerts." },
    ],
  }),
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  return (
    <AuthLayout
      title="Sign in to The DASH"
      subtitle="Your dashboards, reports and alerts in one place."
      footer={
        <>
          New here?{" "}
          <Link to="/signup" className="font-medium text-primary hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form
        className="space-y-3"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const { error } = await supabase.auth.signInWithPassword({ email, password });
          setBusy(false);
          if (error) {
            toast.error(error.message);
            return;
          }
          toast.success("Signed in");
          navigate({ to: "/" });
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
            placeholder="you@company.in"
          />
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label htmlFor="password">Password</Label>
            <Link to="/forgot-password" className="text-xs text-primary hover:underline">
              Forgot password?
            </Link>
          </div>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>

      <div className="flex items-center gap-3 py-1 text-xs text-muted-foreground">
        <span className="h-px flex-1 bg-border" />
        or
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="space-y-2">
        <Button
          variant="outline"
          className="w-full"
          onClick={async () => {
            const result = await lovable.auth.signInWithOAuth("google", {
              redirect_uri: window.location.origin,
            });
            if (result.error) {
              toast.error("Google sign-in failed");
              return;
            }
            if (result.redirected) return;
            navigate({ to: "/" });
          }}
        >
          Continue with Google
        </Button>
        <Button
          variant="outline"
          className="w-full"
          onClick={async () => {
            if (!email) {
              toast.error("Enter your email first");
              return;
            }
            const { error } = await supabase.auth.signInWithOtp({
              email,
              options: { emailRedirectTo: window.location.origin },
            });
            if (error) toast.error(error.message);
            else toast.success("Magic link sent — check your inbox");
          }}
        >
          Email me a magic link
        </Button>
        <Button variant="ghost" className="w-full" onClick={() => navigate({ to: "/" })}>
          Explore the demo workspace
        </Button>
      </div>
    </AuthLayout>
  );
}
