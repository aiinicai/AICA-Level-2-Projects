import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { useEffect, useState } from "react";
import { Shell } from "@/components/Shell";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable/index";
import { useMirror } from "@/hooks/useMirror";
import { clearLocalTrace } from "@/lib/device";
import { ensureAccount } from "@/lib/billing.functions";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "Keep your reflections with you — MIRROR" },
      {
        name: "description",
        content:
          "Add your email to keep your reflections private and with you across devices. No password, no other questions — just a one-time link.",
      },
      { property: "og:title", content: "Keep your reflections with you — MIRROR" },
      {
        property: "og:description",
        content: "One email, no password. Your history stays yours, even on a shared device.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: AuthScreen,
});

function AuthScreen() {
  const navigate = useNavigate();
  const { session, refresh } = useMirror();
  const link = useServerFn(ensureAccount);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    void (async () => {
      try {
        await link({});
      } catch {
        /* linking is best effort */
      }
      // The device's anonymous callback belongs to whoever used it before —
      // never surface it inside a freshly signed-in account.
      clearLocalTrace();
      await refresh();
      void navigate({ to: "/" });
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  async function sendLink() {
    setBusy(true);
    setError(null);
    try {
      const { error: err } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: { emailRedirectTo: window.location.origin },
      });
      if (err) throw new Error(err.message);
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "That link could not be sent.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell
      eyebrow="Optional, always"
      title="Keep your reflections with you."
      lead="Your email is the only thing MIRROR ever asks for — no password, no age, no occupation. It's what lets your reflections and credit follow you across devices, and it's what keeps your history yours on a laptop other people use too."
    >
      {sent ? (
        <section className="panel space-y-2 p-6">
          <p className="font-display text-2xl">Check your inbox.</p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            We sent a one-time sign-in link to {email}. Open it on this device and you're in —
            nothing to remember, nothing to create.
          </p>
        </section>
      ) : (
        <section className="panel space-y-4 p-6">
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground" htmlFor="email">
              Your email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-xl border border-border bg-background/60 px-4 py-2.5 text-sm outline-none focus:border-primary"
            />
          </div>
          <button
            type="button"
            disabled={busy || !email.includes("@")}
            onClick={() => void sendLink()}
            className="rounded-full px-7 py-2.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
            style={{ background: "var(--gradient-brass)" }}
          >
            {busy ? "Sending…" : "Email me a sign-in link"}
          </button>

          <button
            type="button"
            onClick={() =>
              void lovable.auth.signInWithOAuth("google", { redirect_uri: window.location.origin })
            }
            className="block rounded-full border border-border px-7 py-2.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Or continue with Google
          </button>

          {error ? (
            <p className="text-sm" style={{ color: "var(--rust)" }}>
              {error}
            </p>
          ) : null}

          <p className="text-xs leading-relaxed text-muted-foreground">
            Prefer to stay anonymous? Just close this page — MIRROR keeps working, everything stays
            on this device, and no browsable history is kept.
          </p>
        </section>
      )}
    </Shell>
  );
}
