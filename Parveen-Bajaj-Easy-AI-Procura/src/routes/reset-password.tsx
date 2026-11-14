import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const Route = createFileRoute("/reset-password")({
  head: () => ({
    meta: [
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { title: "Reset password — Easy AI Procura" },
      { name: "description", content: "Choose a new password for your Easy AI Procura account." },
      { property: "og:title", content: "Reset password — Easy AI Procura" },
      { property: "og:description", content: "Choose a new password for your Easy AI Procura account." },
    ],
  }),
  component: ResetPassword,
});

function ResetPassword() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    const { error } = await supabase.auth.updateUser({ password });
    setBusy(false);
    if (error) {
      toast.error(error.message);
      return;
    }
    toast.success("Password updated.");
    void navigate({ to: "/dashboard" });
  };

  return (
    <div className="doc-grid flex min-h-screen items-center justify-center px-4 py-12">
      <form onSubmit={submit} className="w-full max-w-md space-y-4 rounded-lg border border-border bg-card p-6">
        <h1 className="text-lg font-semibold">Set a new password</h1>
        <div className="space-y-2">
          <Label htmlFor="newpw">New password</Label>
          <Input id="newpw" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <Button type="submit" className="w-full" disabled={busy}>
          {busy ? "Saving…" : "Update password"}
        </Button>
      </form>
    </div>
  );
}
