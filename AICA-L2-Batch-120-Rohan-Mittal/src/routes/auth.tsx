import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Eye, EyeOff, Loader2, Mail, CheckCircle2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signInWithPopup,
  signInWithRedirect,
  getRedirectResult,
  GoogleAuthProvider,
  sendEmailVerification,
  sendSignInLinkToEmail,
  isSignInWithEmailLink,
  signInWithEmailLink,
  onAuthStateChanged,
  updateProfile,
  updatePassword,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { ensureUserProfile, getInviteTempPassword } from "@/lib/fairlyshareDb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { EqualSplitLogo, InstallAppButton } from "@/components/AppShell";
import { REDIRECT_KEY, safeRedirect } from "@/lib/redirect";
import { errMsg } from "@/lib/app";

const EMAIL_FOR_LINK_KEY = "fairshare_email_for_signin";

export const Route = createFileRoute("/auth")({
  ssr: false,
  validateSearch: (s: Record<string, unknown>) => ({
    redirect: typeof s["redirect"] === "string" ? s["redirect"] : undefined,
  }),
  head: () => ({
    meta: [
      { title: "Sign in — Fair Share" },
      {
        name: "description",
        content: "Sign in or create a Fair Share account to split expenses.",
      },
      { property: "og:title", content: "Sign in — Fair Share" },
      {
        property: "og:description",
        content: "Sign in or create a Fair Share account to split expenses.",
      },
    ],
  }),
  component: AuthPage,
});

export function AuthCard({
  children,
  title,
  subtitle,
}: {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}) {
  const isMainBrandTitle = title.trim().toLowerCase() === "fair share";

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10 bg-[#F5FAFF]">
      <div className="w-full max-w-md overflow-hidden rounded-3xl border border-border bg-card shadow-soft">
        <div className="bg-[#17324D] px-6 py-7 text-white">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3.5">
              <div className="flex items-center justify-center shrink-0">
                <EqualSplitLogo className="h-14 w-14" withBackground={true} />
              </div>
              <div>
                <h1 className="text-2xl font-extrabold tracking-tight text-white">Fair Share</h1>
                {isMainBrandTitle && <p className="mt-0.5 text-sm text-slate-300">{subtitle}</p>}
              </div>
            </div>
            <InstallAppButton />
          </div>
          {!isMainBrandTitle && (
            <div className="mt-4 pt-3 border-t border-white/10">
              <h2 className="text-lg font-bold text-white">{title}</h2>
              <p className="mt-0.5 text-sm text-slate-300">{subtitle}</p>
            </div>
          )}
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}

function PasswordInput({
  value,
  onChange,
  id,
}: {
  value: string;
  onChange: (v: string) => void;
  id: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        id={id}
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="pr-10"
        required
        minLength={6}
      />
      <button
        type="button"
        onClick={() => setShow((s) => !s)}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground"
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </button>
    </div>
  );
}

function AuthPage() {
  const { redirect } = Route.useSearch();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [verificationSent, setVerificationSent] = useState(false);
  const [magicLinkSent, setMagicLinkSent] = useState(false);
  const [unverifiedUserEmail, setUnverifiedUserEmail] = useState<string | null>(null);

  // Prevents onAuthStateChanged from navigating away before profile setup & verification email dispatch complete
  const authFlowBusyRef = useRef(false);

  const go = () => {
    const stored = sessionStorage.getItem(REDIRECT_KEY);
    sessionStorage.removeItem(REDIRECT_KEY);
    navigate({ to: safeRedirect(redirect ?? stored ?? "/"), replace: true });
  };

  useEffect(() => {
    if (redirect) sessionStorage.setItem(REDIRECT_KEY, safeRedirect(redirect));

    // 1. Check if returning from Google OAuth redirect flow
    getRedirectResult(auth)
      .then(async (res) => {
        if (res?.user) {
          authFlowBusyRef.current = true;
          await ensureUserProfile(
            res.user.uid,
            res.user.email || "",
            res.user.displayName || undefined,
            res.user.photoURL,
          );
          authFlowBusyRef.current = false;
          toast.success("Signed in with Google");
          go();
        }
      })
      .catch(() => {
        // Non-fatal
      });

    // 2. Check if returning from an Email Sign-In Link (passwordless or email invite)
    if (typeof window !== "undefined" && isSignInWithEmailLink(auth, window.location.href)) {
      const urlParams = new URLSearchParams(window.location.search);
      const emailFromUrl = urlParams.get("inviteEmail") || urlParams.get("email");
      const storedEmail = window.localStorage.getItem(EMAIL_FOR_LINK_KEY);
      const targetEmail = emailFromUrl || storedEmail;
      if (targetEmail) {
        authFlowBusyRef.current = true;
        setBusy(true);
        signInWithEmailLink(auth, targetEmail, window.location.href)
          .then(async (cred) => {
            window.localStorage.removeItem(EMAIL_FOR_LINK_KEY);
            await ensureUserProfile(
              cred.user.uid,
              cred.user.email || targetEmail,
              cred.user.displayName || undefined,
            );
            toast.success("Signed in via email link!");
            authFlowBusyRef.current = false;
            go();
          })
          .catch((err) => {
            authFlowBusyRef.current = false;
            toast.error(errMsg(err));
          })
          .finally(() => setBusy(false));
      }
    }

    const unsub = onAuthStateChanged(auth, (user) => {
      if (user && !verificationSent && !authFlowBusyRef.current) {
        go();
      }
    });
    return () => unsub();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verificationSent]);

  const emailOk = /^\S+@\S+\.\S+$/.test(email.trim());

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    if (!emailOk) return toast.error("Enter a valid email");
    setBusy(true);
    authFlowBusyRef.current = true;
    try {
      const cred = await signInWithEmailAndPassword(auth, email.trim(), password);
      await ensureUserProfile(
        cred.user.uid,
        cred.user.email || email.trim(),
        cred.user.displayName || undefined,
      );

      if (!cred.user.emailVerified) {
        setUnverifiedUserEmail(cred.user.email);
      }
      authFlowBusyRef.current = false;
      go();
    } catch (err) {
      authFlowBusyRef.current = false;
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  async function signUp(e: React.FormEvent) {
    e.preventDefault();
    if (!emailOk) return toast.error("Enter a valid email");
    if (password.length < 6) return toast.error("Password must be at least 6 characters");
    if (!name.trim()) return toast.error("Enter your name");
    setBusy(true);
    authFlowBusyRef.current = true;
    try {
      const targetEmail = email.trim().toLowerCase();
      let cred;
      try {
        cred = await createUserWithEmailAndPassword(auth, targetEmail, password);
      } catch (createErr: unknown) {
        if ((createErr as { code?: string })?.code === "auth/email-already-in-use") {
          // If this user was invited by email, a provisional account with getInviteTempPassword was created to dispatch their invite email.
          // Claim it seamlessly and set their chosen password!
          try {
            cred = await signInWithEmailAndPassword(
              auth,
              targetEmail,
              getInviteTempPassword(targetEmail),
            );
            await updatePassword(cred.user, password);
          } catch {
            throw createErr;
          }
        } else {
          throw createErr;
        }
      }

      // Set verificationSent BEFORE awaiting further calls so onAuthStateChanged stays on the confirmation view
      setVerificationSent(true);

      await updateProfile(cred.user, { displayName: name.trim() });
      await ensureUserProfile(cred.user.uid, targetEmail, name.trim());

      // Send actual confirmation email with continue URL back to the app (with fallback without URL if domain is not whitelisted)
      const origin =
        typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio";
      try {
        try {
          await sendEmailVerification(cred.user, {
            url: origin,
            handleCodeInApp: false,
          });
        } catch {
          await sendEmailVerification(cred.user);
        }
        toast.success(
          `Verification email sent to ${targetEmail}! Please check your inbox (and spam folder).`,
        );
      } catch (emailErr) {
        console.warn("Email verification send note:", emailErr);
        toast.info("Account created! You can continue to Fair Share now.");
      }
    } catch (err: unknown) {
      setVerificationSent(false);
      if ((err as { code?: string })?.code === "auth/email-already-in-use") {
        toast.error("This email is already registered. Please sign in or use password reset.");
      } else {
        toast.error(errMsg(err));
      }
    } finally {
      authFlowBusyRef.current = false;
      setBusy(false);
    }
  }

  async function resendVerification() {
    if (!auth.currentUser) return toast.error("Please sign in to resend verification email.");
    setBusy(true);
    try {
      const origin =
        typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio";
      try {
        await sendEmailVerification(auth.currentUser, {
          url: origin,
          handleCodeInApp: false,
        });
      } catch {
        await sendEmailVerification(auth.currentUser);
      }
      toast.success("Verification email resent! Please check your inbox and spam folder.");
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  async function sendPasswordlessLink() {
    if (!emailOk) {
      return toast.error(
        "Enter your email address above first to receive an instant sign-in link.",
      );
    }
    setBusy(true);
    try {
      const targetEmail = email.trim().toLowerCase();
      const origin =
        typeof window !== "undefined" ? window.location.origin : "https://fairshare-rm.ai.studio";
      const continueUrl = `${origin}/auth?inviteEmail=${encodeURIComponent(targetEmail)}${
        redirect ? `&redirect=${encodeURIComponent(redirect)}` : ""
      }`;
      await sendSignInLinkToEmail(auth, targetEmail, {
        url: continueUrl,
        handleCodeInApp: true,
      });
      if (typeof window !== "undefined") {
        window.localStorage.setItem(EMAIL_FOR_LINK_KEY, targetEmail);
      }
      setMagicLinkSent(true);
      toast.success(`Instant sign-in link sent to ${targetEmail}!`);
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  }

  async function google() {
    setBusy(true);
    authFlowBusyRef.current = true;
    try {
      const provider = new GoogleAuthProvider();
      provider.setCustomParameters({ prompt: "select_account" });
      const cred = await signInWithPopup(auth, provider);
      await ensureUserProfile(
        cred.user.uid,
        cred.user.email || "",
        cred.user.displayName || undefined,
        cred.user.photoURL,
      );
      toast.success("Signed in with Google");
      authFlowBusyRef.current = false;
      go();
    } catch (err: unknown) {
      authFlowBusyRef.current = false;
      const code = (err as { code?: string })?.code;
      if (code === "auth/popup-blocked") {
        try {
          const provider = new GoogleAuthProvider();
          provider.setCustomParameters({ prompt: "select_account" });
          await signInWithRedirect(auth, provider);
          return;
        } catch (redirErr) {
          toast.error(errMsg(redirErr));
        }
      } else if (code !== "auth/popup-closed-by-user" && code !== "auth/cancelled-popup-request") {
        toast.error(errMsg(err));
      }
    } finally {
      setBusy(false);
    }
  }

  if (verificationSent) {
    return (
      <AuthCard
        title="Verify your email"
        subtitle="Your account is ready! We've sent a confirmation link to your email."
      >
        <div className="text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <Mail className="h-7 w-7" />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold text-foreground">Confirmation email sent to {email}</h3>
            <p className="text-sm text-muted-foreground">
              Click the verification link in your inbox (or spam/promotions folder) to verify your
              email, or continue straight to Fair Share now.
            </p>
          </div>
          <div className="pt-2 space-y-2">
            <Button onClick={go} className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]">
              <CheckCircle2 className="mr-2 h-4 w-4 text-[#38BDF8]" /> Continue to Fair Share
            </Button>
            <Button
              variant="outline"
              onClick={resendVerification}
              disabled={busy}
              className="w-full"
            >
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Resend verification email
            </Button>
          </div>
        </div>
      </AuthCard>
    );
  }

  if (magicLinkSent) {
    return (
      <AuthCard title="Check your email" subtitle="We sent a one-click sign-in link to your inbox.">
        <div className="text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#E0F2FE] text-[#0284C7]">
            <Mail className="h-7 w-7" />
          </div>
          <div className="space-y-1">
            <h3 className="font-semibold text-foreground">Sign-in link sent to {email}</h3>
            <p className="text-sm text-muted-foreground">
              Open the email from Fair Share and tap the sign-in link to log in automatically
              without a password.
            </p>
          </div>
          <Button variant="outline" className="w-full" onClick={() => setMagicLinkSent(false)}>
            Back to Sign In
          </Button>
        </div>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Fair Share" subtitle="Split group and personal expenses, fairly and fast.">
      {unverifiedUserEmail && (
        <div className="mb-4 rounded-xl bg-badge p-3 text-xs text-badge-foreground flex items-center justify-between">
          <span>Email not verified yet.</span>
          <button
            type="button"
            onClick={resendVerification}
            className="underline font-semibold ml-2"
          >
            Resend email
          </button>
        </div>
      )}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as "signin" | "signup")}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="signin">Sign In</TabsTrigger>
          <TabsTrigger value="signup">Sign Up</TabsTrigger>
        </TabsList>
        <TabsContent value="signin">
          <form onSubmit={signIn} className="mt-4 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="e1">Email</Label>
              <Input
                id="e1"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <Label htmlFor="p1">Password</Label>
                <Link to="/forgot-password" className="text-xs font-medium text-primary">
                  Forgot password?
                </Link>
              </div>
              <PasswordInput id="p1" value={password} onChange={setPassword} />
            </div>
            <Button
              type="submit"
              className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
              disabled={busy}
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Sign In
            </Button>
          </form>
        </TabsContent>
        <TabsContent value="signup">
          <form onSubmit={signUp} className="mt-4 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="n2">Full Name</Label>
              <Input
                id="n2"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Alex Morgan"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="e2">Email</Label>
              <Input
                id="e2"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@example.com"
                required
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="p2">Password</Label>
              <PasswordInput id="p2" value={password} onChange={setPassword} />
              <p className="text-xs text-muted-foreground">At least 6 characters</p>
            </div>
            <Button
              type="submit"
              className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
              disabled={busy}
            >
              {busy && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Create account
            </Button>
          </form>
        </TabsContent>
      </Tabs>

      <div className="my-5 flex items-center gap-3 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        or {activeTab === "signup" ? "sign up" : "sign in"} with
        <div className="h-px flex-1 bg-border" />
      </div>

      <div className="space-y-2.5">
        <Button
          variant="outline"
          className="w-full gap-2 font-semibold"
          onClick={google}
          disabled={busy}
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
            <path
              fill="currentColor"
              d="M21.35 11.1H12v2.98h5.35c-.23 1.4-1.66 4.1-5.35 4.1-3.22 0-5.85-2.67-5.85-5.96S8.78 6.26 12 6.26c1.83 0 3.06.78 3.76 1.45l2.57-2.47C16.68 3.7 14.55 2.75 12 2.75 6.89 2.75 2.75 6.9 2.75 12S6.89 21.25 12 21.25c5.33 0 8.87-3.75 8.87-9.02 0-.6-.07-1.06-.15-1.13z"
            />
          </svg>
          {activeTab === "signup" ? "Sign up with Google" : "Continue with Google"}
        </Button>

        <Button
          type="button"
          variant="ghost"
          className="w-full gap-2 text-xs text-[#0F2744] hover:bg-[#F0F8FF]"
          onClick={sendPasswordlessLink}
          disabled={busy}
        >
          <Sparkles className="h-3.5 w-3.5 text-[#0284C7]" />
          Send Instant Sign-In Link to Email (No Password)
        </Button>
      </div>
    </AuthCard>
  );
}
