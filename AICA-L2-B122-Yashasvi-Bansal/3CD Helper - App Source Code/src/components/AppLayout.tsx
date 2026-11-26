import { useState } from "react";
import { Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { LayoutDashboard, Users, UserCog, Settings, Activity, LogOut, ChevronDown, User, Building2, Download } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useFirm } from "@/contexts/FirmContext";
import { Logo } from "./Logo";
import { Avatar, Badge, cn } from "./ui";
import { ROLE_LABEL } from "@/lib/db";
import { useInstallPrompt } from "@/hooks/useInstallPrompt";

const NAV = [
  { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/app/clients", label: "Clients", icon: Users },
  { to: "/app/team", label: "Team", icon: UserCog },
  { to: "/app/activity", label: "Activity", icon: Activity },
  { to: "/app/settings", label: "Settings", icon: Settings },
] as const;

function useIsActive() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (n: { to: string; end?: boolean }) => (n.end ? pathname === n.to || pathname === `${n.to}/` : pathname === n.to || pathname.startsWith(`${n.to}/`));
}

export default function AppLayout() {
  const { profile, user, signOut } = useAuth();
  const { firm, firms, role, switchFirm } = useFirm();
  const [menu, setMenu] = useState(false);
  const nav = useNavigate();
  const { canInstall, install } = useInstallPrompt();
  const isActive = useIsActive();

  const trialDays = firm ? Math.ceil((new Date(firm.trial_ends_at).getTime() - Date.now()) / 86400000) : 0;

  return (
    <div className="min-h-screen lg:pl-64">
      {/* Desktop sidebar */}
      <aside className="no-print fixed inset-y-0 left-0 hidden w-64 flex-col bg-navy-950 text-white lg:flex">
        <div className="px-5 py-5"><Logo dark /></div>
        <div className="mx-3 mb-4 rounded-xl bg-white/5 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-widest text-navy-300">Firm</div>
          {firms.length > 1 ? (
            <select value={firm?.id} onChange={(e) => switchFirm(e.target.value)} className="mt-1 w-full rounded-md border-0 bg-transparent text-sm font-semibold text-white focus:ring-0">
              {firms.map((f) => <option key={f.id} value={f.id} className="text-slate-900">{f.name}</option>)}
            </select>
          ) : (
            <div className="mt-1 truncate text-sm font-semibold">{firm?.name}</div>
          )}
          <div className="mt-1 text-xs text-navy-300">{role && ROLE_LABEL[role]}</div>
        </div>
        <nav className="flex-1 space-y-1 px-3">
          {NAV.map((n) => (
            <Link key={n.to} to={n.to}
              className={cn("flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive(n) ? "bg-white text-navy-950" : "text-navy-100 hover:bg-white/10")}>
              <n.icon className="h-5 w-5" />{n.label}
            </Link>
          ))}
        </nav>
        {firm?.plan === "trial" && (
          <div className="mx-3 mb-3 rounded-xl border border-gold-400/40 bg-gold-400/10 p-3 text-xs text-gold-400">
            Pro trial · {Math.max(trialDays, 0)} days left
          </div>
        )}
        {canInstall && (
          <button onClick={install} className="mx-3 mb-3 flex items-center gap-2 rounded-lg bg-white/10 px-3 py-2 text-sm hover:bg-white/20">
            <Download className="h-4 w-4" /> Install app
          </button>
        )}
        <div className="border-t border-white/10 p-3">
          <button onClick={() => nav({ to: "/app/profile" })} className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left hover:bg-white/10">
            <Avatar name={profile?.full_name || user?.email} className="bg-navy-700 text-white" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-semibold">{profile?.full_name || "My profile"}</div>
              <div className="truncate text-xs text-navy-300">{user?.email}</div>
            </div>
          </button>
          <button onClick={async () => { await signOut(); nav({ to: "/login" }); }} className="mt-1 flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-navy-200 hover:bg-white/10">
            <LogOut className="h-4 w-4" /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="no-print sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur lg:hidden" style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}>
        <Logo />
        <div className="relative">
          <button onClick={() => setMenu((m) => !m)} className="flex items-center gap-1 rounded-full p-1 hover:bg-slate-100">
            <Avatar name={profile?.full_name || user?.email} /><ChevronDown className="h-4 w-4 text-slate-500" />
          </button>
          {menu && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-2 shadow-xl" onMouseLeave={() => setMenu(false)}>
              <div className="px-3 py-2">
                <div className="truncate text-sm font-semibold">{profile?.full_name}</div>
                <div className="truncate text-xs text-slate-500">{user?.email}</div>
                {role && <Badge className="mt-1 bg-navy-50 text-navy-800">{ROLE_LABEL[role]}</Badge>}
              </div>
              {firms.length > 1 && (
                <div className="border-t border-slate-100 px-3 py-2">
                  <div className="mb-1 text-xs text-slate-500">Switch firm</div>
                  {firms.map((f) => (
                    <button key={f.id} onClick={() => { switchFirm(f.id); setMenu(false); }} className={cn("flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-slate-50", f.id === firm?.id && "font-semibold text-navy-800")}>
                      <Building2 className="h-4 w-4" />{f.name}
                    </button>
                  ))}
                </div>
              )}
              <div className="border-t border-slate-100 pt-1">
                <button onClick={() => { setMenu(false); nav({ to: "/app/profile" }); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-50"><User className="h-4 w-4" />Profile</button>
                <button onClick={() => { setMenu(false); nav({ to: "/app/activity" }); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-50"><Activity className="h-4 w-4" />Activity</button>
                {canInstall && <button onClick={() => { setMenu(false); install(); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-slate-50"><Download className="h-4 w-4" />Install app</button>}
                <button onClick={async () => { await signOut(); nav({ to: "/login" }); }} className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-red-600 hover:bg-red-50"><LogOut className="h-4 w-4" />Sign out</button>
              </div>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 pb-28 pt-5 sm:px-6 lg:px-8 lg:pb-10 lg:pt-8">
        <Outlet />
      </main>

      {/* Mobile bottom navigation */}
      <nav className="no-print safe-bottom fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-slate-200 bg-white lg:hidden">
        {NAV.filter((n) => n.to !== "/app/activity").map((n) => (
          <Link key={n.to} to={n.to}
            className={cn("flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium", isActive(n) ? "text-navy-900" : "text-slate-500")}>
            <n.icon className="h-5 w-5" />{n.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
