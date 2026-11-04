import { Link, useNavigate } from "@tanstack/react-router";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  Bell,
  Check,
  CheckCheck,
  Download,
  ExternalLink,
  Home,
  LogOut,
  Monitor,
  PlusCircle,
  Share,
  Smartphone,
  User,
} from "lucide-react";
import { signOut as firebaseSignOut } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDay, initials, useNotifications, useUser } from "@/lib/app";
import { markAllNotificationsAsRead, markNotificationAsRead } from "@/lib/fairlyshareDb";

export function EqualSplitLogo({
  className = "h-10 w-10",
  withBackground = false,
}: {
  className?: string;
  withBackground?: boolean;
}) {
  return (
    <svg
      viewBox="0 0 120 120"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Fair Share — friends sharing expenses, by RM"
    >
      {withBackground && <rect width="120" height="120" rx="25" fill="#0F2744" />}
      <circle cx="38" cy="32" r="10" fill="#38BDF8" />
      <circle cx="82" cy="32" r="10" fill="#BAE6FD" />
      <path
        d="M37 57 C24 46 22 63 28 77 C33 89 42 96 52 98"
        stroke="#38BDF8"
        strokeWidth="15"
        strokeLinecap="round"
      />
      <path
        d="M83 57 C96 46 98 63 92 77 C87 89 78 96 68 98"
        stroke="#BAE6FD"
        strokeWidth="15"
        strokeLinecap="round"
      />
      <path d="M47 54 Q47 50 51 50 H69 Q73 50 73 54 V78 Q60 84 47 78 Z" fill="white" />
      <path d="M54 60 H66" stroke="#38BDF8" strokeWidth="4" strokeLinecap="round" />
      <path d="M54 70 H66" stroke="#BAE6FD" strokeWidth="4" strokeLinecap="round" />
      <g
        transform="translate(94 103)"
        stroke="white"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M0 8 V0 H3 Q6 0 6 2.5 Q6 5 3 5 H0 M3 5 L6.5 8" />
        <path d="M8 8 V0 L12 4 L16 0 V8" />
      </g>
    </svg>
  );
}

export function Logo({
  size = "md",
  variant = "light",
}: {
  size?: "sm" | "md" | "lg";
  variant?: "light" | "dark";
}) {
  const iconSize = size === "lg" ? "h-12 w-12" : size === "sm" ? "h-9 w-9" : "h-10 w-10";
  const textSize = size === "lg" ? "text-2xl" : size === "sm" ? "text-base" : "text-xl";
  const textColor = variant === "dark" ? "text-white" : "text-[#0F2744]";
  return (
    <Link to="/" className="flex items-center gap-2.5 group whitespace-nowrap shrink-0">
      <div className="flex items-center justify-center transition-transform group-hover:scale-105 shrink-0">
        <EqualSplitLogo className={iconSize} withBackground={variant !== "dark"} />
      </div>
      <span className={`font-display font-extrabold tracking-tight ${textColor} ${textSize}`}>
        Fair Share
      </span>
    </Link>
  );
}

type BIP = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
};

let globalDeferredPrompt: BIP | null = null;
if (typeof window !== "undefined") {
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    globalDeferredPrompt = e as BIP;
  });
}

export function InstallAppButton({ variant = "header" }: { variant?: "header" | "card" }) {
  const [evt, setEvt] = useState<BIP | null>(globalDeferredPrompt);
  const [installed, setInstalled] = useState(false);
  const [guideOpen, setGuideOpen] = useState(false);
  const [inIframe, setInIframe] = useState(false);
  const [isIos, setIsIos] = useState(false);

  useEffect(() => {
    const standalone =
      window.matchMedia("(display-mode: standalone)").matches ||
      (navigator as { standalone?: boolean }).standalone === true;
    setInstalled(standalone);

    try {
      setInIframe(window.self !== window.top);
    } catch {
      setInIframe(true);
    }

    const ua = navigator.userAgent;
    setIsIos(/iphone|ipad|ipod/i.test(ua));

    if (globalDeferredPrompt) {
      setEvt(globalDeferredPrompt);
    }

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      globalDeferredPrompt = e as BIP;
      setEvt(e as BIP);
    };
    const handleInstalled = () => {
      setInstalled(true);
      globalDeferredPrompt = null;
      setEvt(null);
      setGuideOpen(false);
    };

    window.addEventListener("beforeinstallprompt", handleBeforeInstall);
    window.addEventListener("appinstalled", handleInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", handleBeforeInstall);
      window.removeEventListener("appinstalled", handleInstalled);
    };
  }, []);

  if (installed) return null;

  async function handleInstallClick() {
    if (evt) {
      try {
        await evt.prompt();
        const choice = await evt.userChoice;
        if (choice?.outcome === "accepted") {
          setInstalled(true);
          globalDeferredPrompt = null;
          setEvt(null);
        }
        return;
      } catch {
        // Fall through to guide modal
      }
    }
    setGuideOpen(true);
  }

  const appUrl = typeof window !== "undefined" ? window.location.origin : "/";

  return (
    <>
      {variant === "card" ? (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleInstallClick}
          className="gap-1.5 border-[#38BDF8]/40 bg-[#F0F8FF] text-[#0F2744] hover:bg-[#E0F2FE] text-xs font-semibold"
        >
          <Download className="h-3.5 w-3.5 text-[#0284C7]" />
          Install App (PWA)
        </Button>
      ) : (
        <button
          type="button"
          onClick={handleInstallClick}
          className="flex items-center gap-1.5 rounded-lg border border-[#38BDF8]/40 bg-[#38BDF8]/15 px-3 py-1.5 text-xs font-semibold text-[#38BDF8] hover:bg-[#38BDF8]/25 transition-colors whitespace-nowrap shrink-0"
          title="Install Fair Share on your device"
        >
          <Download className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Install App</span>
          <span className="sm:hidden">Install</span>
        </button>
      )}

      <Dialog open={guideOpen} onOpenChange={setGuideOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2.5 text-[#0F2744]">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-white p-0.5 ring-1 ring-[#38BDF8]/40">
                <EqualSplitLogo className="h-8 w-8" />
              </div>
              Install Fair Share on Your Device
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4 text-sm">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Add Fair Share directly to your home screen or desktop for instant 1-tap access,
              full-screen standalone view, and offline balance viewing.
            </p>

            {inIframe && (
              <div className="rounded-2xl border border-[#38BDF8]/40 bg-[#F0F8FF] p-3.5 space-y-2.5">
                <p className="text-xs font-semibold text-[#0F2744]">
                  Step 1: Open in a direct browser tab
                </p>
                <p className="text-xs text-muted-foreground">
                  Browsers require apps to be opened in their own tab before installing to your
                  device.
                </p>
                <Button
                  asChild
                  size="sm"
                  className="w-full bg-[#0F2744] text-white hover:bg-[#17324D]"
                >
                  <a href={appUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="mr-1.5 h-3.5 w-3.5 text-[#38BDF8]" />
                    Open Fair Share in New Tab to Install
                  </a>
                </Button>
              </div>
            )}

            <div className="space-y-2.5">
              <div className="rounded-2xl border bg-card p-3 space-y-1">
                <div className="flex items-center gap-2 font-semibold text-xs text-[#0F2744]">
                  <Smartphone className="h-4 w-4 text-[#0284C7]" />
                  {isIos ? "iPhone / iPad (Safari) — Recommended" : "iPhone / iPad (Safari)"}
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  1. Tap the <Share className="inline h-3.5 w-3.5 text-[#0284C7]" />{" "}
                  <b className="text-foreground">Share</b> button in the Safari toolbar.
                  <br />
                  2. Scroll down and tap <b className="text-foreground">Add to Home Screen</b>.
                </p>
              </div>

              <div className="rounded-2xl border bg-card p-3 space-y-1">
                <div className="flex items-center gap-2 font-semibold text-xs text-[#0F2744]">
                  <Smartphone className="h-4 w-4 text-[#0284C7]" />
                  Android (Chrome / Edge / Samsung Internet)
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  1. Tap the browser menu <b className="text-foreground">⋮</b> in the top-right
                  corner.
                  <br />
                  2. Tap <b className="text-foreground">Install app</b> or{" "}
                  <b className="text-foreground">Add to Home screen</b>.
                </p>
              </div>

              <div className="rounded-2xl border bg-card p-3 space-y-1">
                <div className="flex items-center gap-2 font-semibold text-xs text-[#0F2744]">
                  <Monitor className="h-4 w-4 text-[#0284C7]" />
                  Desktop (Chrome / Edge)
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Click the <Download className="inline h-3.5 w-3.5 text-[#0284C7]" />{" "}
                  <b className="text-foreground">Install Fair Share</b> icon on the right side of
                  your browser&apos;s address bar.
                </p>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" className="w-full" onClick={() => setGuideOpen(false)}>
              Got it
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function useSignOut() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  return async () => {
    await qc.cancelQueries();
    qc.clear();
    await firebaseSignOut(auth);
    navigate({ to: "/auth", search: { redirect: undefined }, replace: true });
  };
}

export function AppHeader() {
  const { data: me } = useUser();
  const { data: notifs } = useNotifications();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const signOut = useSignOut();
  const unreadNotifs = notifs?.filter((n) => !n.is_read) ?? [];
  const unreadCount = unreadNotifs.length;

  return (
    <header className="sticky top-0 z-40 border-b border-[#1E3A5F] bg-[#0F2744] text-white shadow-xs">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-4">
        <Logo variant="dark" />

        <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-200">
          <Link
            to="/"
            activeOptions={{ exact: true }}
            className="hover:text-[#38BDF8] transition-colors whitespace-nowrap shrink-0"
            activeProps={{ className: "text-[#38BDF8] font-semibold" }}
          >
            Dashboard
          </Link>
          <Link
            to="/add"
            className="hover:text-[#38BDF8] transition-colors whitespace-nowrap shrink-0"
            activeProps={{ className: "text-[#38BDF8] font-semibold" }}
          >
            Add Expense
          </Link>
          <Link
            to="/profile"
            className="hover:text-[#38BDF8] transition-colors whitespace-nowrap shrink-0"
            activeProps={{ className: "text-[#38BDF8] font-semibold" }}
          >
            Profile
          </Link>
        </nav>

        <div className="flex items-center gap-2.5 shrink-0">
          <InstallAppButton />

          {/* Dedicated Notifications Dropdown on the left side of Profile Picture */}
          <DropdownMenu>
            <DropdownMenuTrigger
              className="relative flex h-9 w-9 items-center justify-center rounded-full border border-[#38BDF8]/40 bg-[#17324D] text-[#38BDF8] hover:bg-[#38BDF8]/20 focus:outline-none focus:ring-2 focus:ring-[#38BDF8] transition-colors"
              aria-label="Notifications"
              title={unreadCount > 0 ? `${unreadCount} unread notifications` : "Notifications"}
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-[#38BDF8] px-1 text-[10px] font-extrabold text-[#0F2744]">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              )}
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80 p-0 overflow-hidden rounded-2xl">
              <div className="flex items-center justify-between border-b bg-[#0F2744] px-4 py-3 text-white">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-[#38BDF8]" />
                  <span className="text-sm font-bold">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="rounded-full bg-[#38BDF8] px-2 py-0.5 text-[10px] font-extrabold text-[#0F2744]">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={async (e) => {
                      e.preventDefault();
                      await markAllNotificationsAsRead(unreadNotifs.map((n) => n.id));
                      qc.invalidateQueries({ queryKey: ["notifications"] });
                    }}
                    className="flex items-center gap-1 text-[11px] font-semibold text-[#38BDF8] hover:underline"
                  >
                    <CheckCheck className="h-3.5 w-3.5" /> Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y">
                {!notifs?.length ? (
                  <div className="px-4 py-8 text-center">
                    <Bell className="mx-auto h-6 w-6 text-muted-foreground/50 mb-1.5" />
                    <p className="text-xs font-medium text-foreground">No notifications yet</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Friend invites, group updates, and reminders will appear here.
                    </p>
                  </div>
                ) : (
                  notifs.slice(0, 12).map((n) => (
                    <div
                      key={n.id}
                      className={`flex items-start justify-between gap-2.5 p-3 text-xs transition-colors ${
                        !n.is_read ? "bg-[#F0F8FF]" : "bg-card"
                      }`}
                    >
                      <button
                        type="button"
                        className="flex-1 text-left space-y-0.5"
                        onClick={async () => {
                          if (!n.is_read) {
                            await markNotificationAsRead(n.id);
                            qc.invalidateQueries({ queryKey: ["notifications"] });
                          }
                          if (n.target_type === "group" && n.target_id) {
                            navigate({
                              to: "/group/$groupId",
                              params: { groupId: n.target_id },
                              search: { add: undefined },
                            });
                          } else {
                            navigate({ to: "/" });
                          }
                        }}
                      >
                        <div className="font-semibold text-[#0F2744] flex items-center gap-1.5">
                          {!n.is_read && (
                            <span className="h-2 w-2 rounded-full bg-[#0284C7] shrink-0" />
                          )}
                          <span>{n.title}</span>
                        </div>
                        <p className="text-muted-foreground leading-snug">{n.message}</p>
                        <p className="text-[10px] text-muted-foreground/80">
                          {formatDay(n.created_at.slice(0, 10))}
                        </p>
                      </button>
                      {!n.is_read && (
                        <button
                          type="button"
                          onClick={async (e) => {
                            e.stopPropagation();
                            await markNotificationAsRead(n.id);
                            qc.invalidateQueries({ queryKey: ["notifications"] });
                          }}
                          className="rounded-md p-1 text-[#0284C7] hover:bg-[#E0F2FE] shrink-0"
                          title="Mark as read"
                        >
                          <Check className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  ))
                )}
              </div>

              <div className="border-t bg-muted/30 p-2 text-center">
                <Link
                  to="/profile"
                  className="block rounded-lg py-1.5 text-xs font-semibold text-[#0F2744] hover:bg-muted/60"
                >
                  View all in Profile &amp; Settings
                </Link>
              </div>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Profile Picture Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger className="rounded-full focus:outline-none focus:ring-2 focus:ring-[#38BDF8]">
              <Avatar className="h-9 w-9 border-2 border-[#38BDF8]/50">
                {me?.avatar && <AvatarImage src={me.avatar} alt={me.name} />}
                <AvatarFallback className="bg-[#38BDF8] text-xs font-bold text-[#0F2744]">
                  {initials(me?.name)}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div className="truncate font-semibold">{me?.name}</div>
                <div className="truncate text-xs font-normal text-muted-foreground">
                  {me?.email}
                </div>
                {!me?.email_verified && (
                  <span className="mt-1 inline-block rounded-md bg-owe-soft px-1.5 py-0.5 text-[10px] font-semibold text-owe">
                    Unverified
                  </span>
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link to="/profile">
                  <User className="mr-2 h-4 w-4" />
                  Profile &amp; Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={signOut}>
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}

export function BottomNav() {
  const items = [
    { to: "/", label: "Dashboard", icon: Home },
    { to: "/add", label: "Add expense", icon: PlusCircle },
    { to: "/profile", label: "Profile", icon: User },
  ] as const;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-card/95 backdrop-blur pb-[env(safe-area-inset-bottom)] md:hidden">
      <div className="grid grid-cols-3 py-1">
        {items.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: true }}
            className="flex flex-col items-center gap-1 py-1.5 text-[11px] font-medium text-muted-foreground transition-colors"
            activeProps={{
              className: "text-navy font-bold [&>div]:bg-[#38BDF8]/25 [&>div]:text-navy",
            }}
          >
            <div className="flex h-7 w-12 items-center justify-center rounded-full transition-colors">
              <Icon className="h-5 w-5" />
            </div>
            <span>{label}</span>
          </Link>
        ))}
      </div>
    </nav>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  text,
  children,
}: {
  icon: typeof Home;
  title: string;
  text: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed bg-card px-6 py-12 text-center">
      <div className="mb-3 rounded-2xl bg-badge p-4 text-badge-foreground">
        <Icon className="h-7 w-7" />
      </div>
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="mt-1 max-w-xs text-sm text-muted-foreground">{text}</p>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}

export function MemberAvatar({
  name,
  src,
  className = "h-8 w-8",
}: {
  name: string;
  src?: string | null | undefined;
  className?: string;
}) {
  return (
    <Avatar className={`${className} border-2 border-card`}>
      {src && <AvatarImage src={src} alt={name} />}
      <AvatarFallback className="bg-badge text-[10px] font-bold text-badge-foreground">
        {initials(name)}
      </AvatarFallback>
    </Avatar>
  );
}
