"use client";

import { useState, Suspense } from "react";
import { signIn } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const callbackUrl = params.get("callbackUrl") || "/dashboard";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const result = await signIn("credentials", { email, password, redirect: false });
    setPending(false);
    if (result?.error) {
      setError("Incorrect email or password.");
      return;
    }
    router.push(callbackUrl);
    router.refresh();
  }

  function fillDemo(role: "admin" | "viewer" | "verifier" | "locationhead") {
    setEmail(`${role}@assettrace.demo`);
    setPassword("Passw0rd!");
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="pill bg-accent-soft text-accent font-mono">FA-QR</span>
            <span className="text-xl font-semibold">AssetTrace</span>
          </div>
          <p className="text-sm text-muted">Fixed Asset Verification &amp; QR Management</p>
        </div>

        <form onSubmit={onSubmit} className="card p-6 space-y-4">
          <div>
            <label className="label" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>
          {error && <p className="text-sm text-bad">{error}</p>}
          <button type="submit" disabled={pending} className="btn-primary w-full">
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="card p-4 mt-4 text-xs text-muted space-y-2">
          <p className="font-semibold text-foreground">Demo accounts (password: Passw0rd!)</p>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => fillDemo("admin")} className="btn-secondary text-xs px-2 py-1">Admin</button>
            <button type="button" onClick={() => fillDemo("locationhead")} className="btn-secondary text-xs px-2 py-1">Location Head</button>
            <button type="button" onClick={() => fillDemo("verifier")} className="btn-secondary text-xs px-2 py-1">Verifier</button>
            <button type="button" onClick={() => fillDemo("viewer")} className="btn-secondary text-xs px-2 py-1">Read-only</button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}
