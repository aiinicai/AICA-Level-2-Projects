import { FormEvent, ReactNode, useEffect, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Eye, EyeOff, Mail, ShieldCheck, FileSpreadsheet, Users } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { lovable } from "@/integrations/lovable/index";
import { Alert, Button, Field, Input } from "@/components/ui";
import { Logo } from "@/components/Logo";
import { errMsg } from "@/lib/db";

function AuthShell({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-navy-950 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Link to="/"><Logo dark /></Link>
        <div className="space-y-6">
          <h2 className="text-3xl font-bold leading-tight">Form 3CD Clause 44 & 31,<br />prepared in minutes.</h2>
          <ul className="space-y-4 text-navy-100">
            <li className="flex gap-3"><FileSpreadsheet className="h-5 w-5 shrink-0 text-gold-400" /> Upload Tally, Busy, Excel, CSV, XML or GSTR-2B data</li>
            <li className="flex gap-3"><ShieldCheck className="h-5 w-5 shrink-0 text-gold-400" /> GSTIN checksum validation & smart classification</li>
            <li className="flex gap-3"><Users className="h-5 w-5 shrink-0 text-gold-400" /> Work with your team – see who prepared and reviewed what</li>
          </ul>
        </div>
        <p className="text-xs text-navy-300">Your client data is private to your firm and protected by row-level security.</p>
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-navy-700/40 blur-3xl" />
      </div>
      <div className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-md">
          <div className="mb-8 lg:hidden"><Link to="/"><Logo /></Link></div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">{title}</h1>
          {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </div>
  );
}

function PasswordInput(props: { value: string; onChange: (v: string) => void; autoComplete?: string }) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input type={show ? "text" : "password"} value={props.value} onChange={(e) => props.onChange(e.target.value)} autoComplete={props.autoComplete} required minLength={8} className="pr-10" />
      <button type="button" onClick={() => setShow((s) => !s)} className="absolute inset-y-0 right-0 px-3 text-slate-400 hover:text-slate-600" aria-label="Show password">
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

function GoogleButton() {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  return (
    <>
      <Button type="button" variant="outline" className="w-full" loading={loading}
        onClick={async () => {
          setLoading(true); setErr("");
          // Return to the public sign-in page; it forwards to /app once the session is ready.
          const result = await lovable.auth.signInWithOAuth("google", { redirect_uri: `${window.location.origin}/login` });
          if (result.error) { setErr(errMsg(result.error)); setLoading(false); return; }
          if (result.redirected) return;
          setLoading(false);
        }}
        icon={<svg viewBox="0 0 48 48" className="h-4 w-4"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-7.9l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>}>
        Continue with Google
      </Button>
      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}
      <div className="my-6 flex items-center gap-3 text-xs text-slate-400"><div className="h-px flex-1 bg-slate-200" />OR<div className="h-px flex-1 bg-slate-200" /></div>
    </>
  );
}

export function Login() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");   // email or username
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setLoading(true); setErr("");
    // a username is turned into its email first; the sign-in itself stays email + password
    let login = email.trim();
    if (!login.includes("@")) {
      const { data, error: le } = await (supabase as any).rpc("email_for_login", { p_login: login });
      if (le || !data) { setLoading(false); setErr("Incorrect username or password."); return; }
      login = data as string;
    }
    const { error } = await supabase.auth.signInWithPassword({ email: login, password });
    setLoading(false);
    if (error) {
      setErr(/confirm/i.test(error.message) ? "Please verify your email first – check your inbox for the confirmation link." : /invalid/i.test(error.message) ? "Incorrect email / username or password. Moved here from the earlier 3CD Helper? Use “Forgot password?” once to verify your email and set a new password." : errMsg(error));
      return;
    }
    nav({ to: "/app", replace: true });
  };
  return (
    <AuthShell title="Welcome back" subtitle="Sign in to your firm workspace">
      <GoogleButton />
      <form onSubmit={submit} className="space-y-4">
        <Field label="Email or username"><Input type="text" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" autoCapitalize="none" spellCheck={false} required /></Field>
        <Field label="Password"><PasswordInput value={password} onChange={setPassword} autoComplete="current-password" /></Field>
        <div className="flex justify-end"><Link to="/forgot-password" className="text-sm font-medium text-navy-700 hover:underline">Forgot password?</Link></div>
        {err && <Alert tone="error">{err}</Alert>}
        <Button type="submit" className="w-full" size="lg" loading={loading}>Sign in</Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">New to 3CD Helper? <Link to="/signup" className="font-semibold text-navy-700 hover:underline">Create an account</Link></p>
    </AuthShell>
  );
}

export function Signup() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agree, setAgree] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [sent, setSent] = useState(false);
  const nav = useNavigate();
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!agree) { setErr("Please accept the Terms and Privacy Policy."); return; }
    setLoading(true); setErr("");
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(), password,
      options: { emailRedirectTo: `${window.location.origin}/login`, data: { full_name: name.trim() } },
    });
    setLoading(false);
    if (error) { setErr(errMsg(error)); return; }
    if (data.session) nav({ to: "/app", replace: true }); else setSent(true);
  };
  if (sent) {
    return (
      <AuthShell title="Verify your email">
        <Alert tone="success"><div className="flex gap-3"><Mail className="h-5 w-5 shrink-0" /><div>We sent a confirmation link to <b>{email}</b>. Open it to activate your account, then sign in.</div></div></Alert>
        <Link to="/login"><Button variant="outline" className="mt-6 w-full">Back to sign in</Button></Link>
      </AuthShell>
    );
  }
  return (
    <AuthShell title="Create your account" subtitle="Start with a 14-day Pro trial. No card needed.">
      <GoogleButton />
      <form onSubmit={submit} className="space-y-4">
        <Field label="Full name" required><Input value={name} onChange={(e) => setName(e.target.value)} required autoComplete="name" placeholder="CA Rahul Sharma" /></Field>
        <Field label="Email" required><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoComplete="email" /></Field>
        <Field label="Password" hint="At least 8 characters" required><PasswordInput value={password} onChange={setPassword} autoComplete="new-password" /></Field>
        <label className="flex items-start gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={agree} onChange={(e) => setAgree(e.target.checked)} className="mt-0.5 h-4 w-4 rounded border-slate-300" />
          <span>I agree to the <Link to="/terms" className="text-navy-700 underline">Terms</Link> and <Link to="/privacy" className="text-navy-700 underline">Privacy Policy</Link>, and consent to processing of data as described (DPDP Act, 2023).</span>
        </label>
        {err && <Alert tone="error">{err}</Alert>}
        <Button type="submit" className="w-full" size="lg" loading={loading}>Create account</Button>
      </form>
      <p className="mt-6 text-center text-sm text-slate-600">Already have an account? <Link to="/login" className="font-semibold text-navy-700 hover:underline">Sign in</Link></p>
    </AuthShell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [err, setErr] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setLoading(true); setErr("");
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), { redirectTo: `${window.location.origin}/reset-password` });
    setLoading(false);
    if (error) setErr(errMsg(error)); else setDone(true);
  };
  return (
    <AuthShell title="Reset password" subtitle="We'll email you a secure link to set a new password.">
      {done ? (
        <Alert tone="success">If an account exists for <b>{email}</b>, a reset link is on its way.</Alert>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <Field label="Email"><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></Field>
          {err && <Alert tone="error">{err}</Alert>}
          <Button type="submit" className="w-full" size="lg" loading={loading}>Send reset link</Button>
        </form>
      )}
      <p className="mt-6 text-center text-sm"><Link to="/login" className="font-semibold text-navy-700 hover:underline">Back to sign in</Link></p>
    </AuthShell>
  );
}

export function ResetPassword() {
  const nav = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  useEffect(() => {
    const { data } = supabase.auth.onAuthStateChange((event) => { if (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") setReady(true); });
    supabase.auth.getSession().then(({ data: d }) => { if (d.session) setReady(true); });
    return () => data.subscription.unsubscribe();
  }, []);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) { setErr("Passwords do not match."); return; }
    setLoading(true); setErr("");
    const { error } = await supabase.auth.updateUser({ password });
    setLoading(false);
    if (error) setErr(errMsg(error)); else nav({ to: "/app", replace: true });
  };
  return (
    <AuthShell title="Set a new password">
      {!ready && <Alert tone="info" className="mb-4">Open this page from the link in your email. Waiting for a valid reset session…</Alert>}
      <form onSubmit={submit} className="space-y-4">
        <Field label="New password" hint="At least 8 characters"><PasswordInput value={password} onChange={setPassword} autoComplete="new-password" /></Field>
        <Field label="Confirm password"><PasswordInput value={confirm} onChange={setConfirm} autoComplete="new-password" /></Field>
        {err && <Alert tone="error">{err}</Alert>}
        <Button type="submit" className="w-full" size="lg" loading={loading} disabled={!ready}>Update password</Button>
      </form>
    </AuthShell>
  );
}
