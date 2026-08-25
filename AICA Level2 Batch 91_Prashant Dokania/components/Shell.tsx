import { Link, useRouterState } from "@tanstack/react-router";
import { useEffect, useState, type ReactNode } from "react";
import { ArrowLeft, Menu, PenLine, X } from "lucide-react";
import logo from "@/assets/itruetalk-logo.png";
import { InstallButton } from "@/components/InstallButton";
import { RecordingIndicator } from "@/components/RecordingIndicator";
import { useMirror } from "@/hooks/useMirror";
import { getLastReflection } from "@/lib/device";

/**
 * Structure borrowed from a familiar chat layout — a quiet left rail for
 * history and navigation, one centred column for the thing you came to do.
 * Everything visual stays MIRROR's: charcoal-indigo, brass, serif display.
 */
export function Shell({
  eyebrow,
  title,
  lead,
  children,
}: {
  eyebrow?: string;
  title: string;
  lead?: string;
  children: ReactNode;
}) {
  const { state, session, isAdmin, signOut } = useMirror();
  const pathname = useRouterState({ select: (r) => r.location.pathname });
  const [open, setOpen] = useState(false);
  const [last, setLast] = useState<{ summary: string } | null>(null);
  const onLanding = pathname === "/";
  const hasEmail = Boolean(state?.identity.email);

  useEffect(() => setLast(getLastReflection()), []);
  // A drawer left open across a navigation would cover the new screen.
  useEffect(() => setOpen(false), [pathname]);

  const navLink =
    "block rounded-lg px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/50 hover:text-foreground";

  const rail = (
    <div className="flex h-full flex-col gap-6 p-4">
      <div className="flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5">
          <img
            src={logo}
            alt="iTrueTalk logo"
            className="h-8 w-8 rounded-md object-contain"
            loading="eager"
          />
          <span className="font-display text-base tracking-[0.28em] brass-text">MIRROR</span>
        </Link>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-muted-foreground hover:text-foreground lg:hidden"
          aria-label="Close menu"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <Link
        to="/"
        className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm text-foreground transition-colors hover:border-primary"
      >
        <PenLine className="h-3.5 w-3.5" style={{ color: "var(--brass)" }} />
        New reflection
      </Link>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <p className="eyebrow px-3">Recent</p>
        <div className="mt-2 space-y-1">
          {hasEmail && (state?.sessions?.length ?? 0) > 0 ? (
            state!.sessions.slice(0, 20).map((s) => (
              <p
                key={s.id}
                className="truncate rounded-lg px-3 py-2 text-sm text-muted-foreground"
                title={s.label}
              >
                {s.label}
              </p>
            ))
          ) : hasEmail ? (
            <p className="px-3 text-xs leading-relaxed text-muted-foreground">
              Nothing here yet. Your reflections will collect quietly as you go.
            </p>
          ) : (
            <div className="space-y-2 px-3">
              {last ? (
                <p className="line-clamp-3 text-xs leading-relaxed text-muted-foreground">
                  {last.summary}
                </p>
              ) : null}
              <p className="text-xs leading-relaxed text-muted-foreground">
                You're anonymous, so nothing is kept beyond this device.{" "}
                <Link to="/auth" className="underline hover:text-foreground">
                  Add your email
                </Link>{" "}
                to keep your history.
              </p>
            </div>
          )}
        </div>
      </div>

      <nav className="space-y-1 border-t border-border/60 pt-4">
        {hasEmail ? (
          <Link to="/dashboard" className={navLink} activeProps={{ className: "text-primary" }}>
            This week
          </Link>
        ) : null}
        <Link to="/blog" className={navLink} activeProps={{ className: "text-primary" }}>
          Journal
        </Link>
        <Link to="/settings" className={navLink} activeProps={{ className: "text-primary" }}>
          Settings
        </Link>
        {isAdmin ? (
          <Link to="/admin" className={navLink} activeProps={{ className: "text-primary" }}>
            Approvals
          </Link>
        ) : null}
        <div className="flex items-center justify-between px-3 pt-2 text-xs text-muted-foreground">
          <InstallButton />
          {session ? (
            <button type="button" onClick={() => void signOut()} className="hover:text-foreground">
              Sign out
            </button>
          ) : null}
        </div>
      </nav>
    </div>
  );

  return (
    <div className="flex min-h-screen">
      <RecordingIndicator />

      <aside className="hidden w-[17rem] shrink-0 border-r border-border/60 lg:block">
        <div className="sticky top-0 h-screen">{rail}</div>
      </aside>

      {open ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
            className="absolute inset-0 bg-background/80 backdrop-blur-sm"
          />
          <div className="absolute inset-y-0 left-0 w-[17rem] border-r border-border/60 bg-card">
            {rail}
          </div>
        </div>
      ) : null}

      <div className="min-w-0 flex-1">
        <header className="border-b border-border/60 backdrop-blur-sm">
          <div className="mx-auto flex max-w-3xl items-center gap-4 px-6 py-4">
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="text-muted-foreground hover:text-foreground lg:hidden"
              aria-label="Open menu"
            >
              <Menu className="h-5 w-5" />
            </button>

            {onLanding ? (
              <Link to="/" className="flex items-center gap-2.5 lg:hidden">
                <img src={logo} alt="iTrueTalk logo" className="h-7 w-7 rounded-md object-contain" />
                <span className="font-display text-sm tracking-[0.28em] brass-text">MIRROR</span>
              </Link>
            ) : (
              <Link
                to="/"
                className="flex items-center gap-2 text-sm transition-colors hover:opacity-80"
                style={{ color: "var(--brass)" }}
              >
                <ArrowLeft className="h-4 w-4" />
                Back
              </Link>
            )}

            <div className="ml-auto text-xs text-muted-foreground">
              {state ? (
                <Link
                  to="/settings"
                  className="rounded-full border border-border px-3 py-1 transition-colors hover:text-foreground"
                  style={
                    state.credit.tone === "empty" || state.credit.tone === "low"
                      ? { borderColor: "var(--rust)" }
                      : undefined
                  }
                >
                  {state.credit.label}
                </Link>
              ) : null}
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-3xl px-6 py-14">
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h1 className="mt-3 font-display text-4xl leading-tight sm:text-5xl">{title}</h1>
          {lead ? (
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-muted-foreground">{lead}</p>
          ) : null}
          <div className="mt-10 space-y-8">{children}</div>
        </main>
      </div>
    </div>
  );
}
