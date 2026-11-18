import { useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard, Users, Bell, FileBarChart, History, Settings, ChevronsLeft, ChevronsRight,
  Moon, Sun, ChevronsUpDown, Check, ShieldCheck, Rocket, Briefcase,
} from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { autoRefreshSessions, useCurrentUser, resetAll, setState, switchUser, useApp, useClients } from "@/lib/store";
import { cn } from "@/lib/utils";
import { DrillSheet, StatusBadge } from "./common";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { fmtDateTime } from "@/lib/gst/format";

const LABELS: Record<string, string> = { clients: "Clients", notices: "Notices", reports: "Reports", activity: "Activity log", settings: "Settings", setup: "Guided setup", workspace: "Client workspace" };

function Breadcrumbs() {
  const path = useRouterState({ select: (s) => s.location.pathname });
  const clients = useApp((s) => s.clients);
  const parts = path.split("/").filter(Boolean);
  const client = parts[0] === "workspace" ? clients.find((c) => c.id === parts[1]) : undefined;
  if (parts[0] === "print") return null;
  return (
    <nav aria-label="Breadcrumb" className="mb-4 flex items-center gap-1.5 text-xs text-muted-foreground print:hidden">
      <Link to="/" className="hover:text-foreground">Dashboard</Link>
      {parts[0] && (
        <>
          <span>/</span>
          {parts[0] === "workspace" ? <Link to="/clients" className="hover:text-foreground">Clients</Link> : <span className="text-foreground">{LABELS[parts[0]] ?? parts[0]}</span>}
        </>
      )}
      {client && (<><span>/</span><span className="text-foreground">{client.name}</span></>)}
    </nav>
  );
}

const PROGRESS_LABEL = { queued: "Queued", running: "Checking…", done: "Done", failed: "Failed" } as const;

export function RunLogButton() {
  const [open, setOpen] = useState(false);
  const runs = useApp((s) => s.runs);
  const progress = useApp((s) => s.progress);
  const clients = useApp((s) => s.clients);
  const name = (id: string) => clients.find((c) => c.id === id)?.name ?? id;
  const active = Object.values(progress).filter((p) => p === "running" || p === "queued").length;
  return (
    <>
      <button onClick={() => setOpen(true)} className="flex h-9 items-center gap-2 rounded-md border px-3 text-sm hover:bg-accent">
        <History className="h-4 w-4" /> <span className="hidden sm:inline">Run log</span> {active > 0 && <StatusBadge status="running" label={`${active} running`} />}
      </button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent className="w-full overflow-y-auto sm:max-w-lg">
          <SheetHeader>
            <SheetTitle>Run log</SheetTitle>
            <SheetDescription>Every reconciliation run, newest first. One client failing never stops the others.</SheetDescription>
          </SheetHeader>
          <div className="space-y-4 px-4 pb-6">
            {Object.keys(progress).length > 0 && (
              <div className="rounded-md border p-3">
                <div className="mb-2 text-xs font-medium text-muted-foreground">Current batch</div>
                {Object.entries(progress).map(([id, p]) => (
                  <div key={id} className="flex justify-between py-1 text-sm"><span>{name(id)}</span><StatusBadge status={p} label={PROGRESS_LABEL[p]} /></div>
                ))}
              </div>
            )}
            {runs.length === 0 && <p className="text-sm text-muted-foreground">No runs yet.</p>}
            <ul className="divide-y">
              {runs.map((r) => (
                <li key={r.id} className="py-2 text-sm">
                  <div className="flex justify-between gap-2"><span className="font-medium">{name(r.clientId)}</span><StatusBadge status={r.status} /></div>
                  <div className="text-xs text-muted-foreground">{fmtDateTime(r.at)} · {r.by}{r.route && ` · ${r.route}`}</div>
                  <div className={cn("text-xs", r.error ? "text-destructive" : "text-muted-foreground")}>{r.error ?? r.message}</div>
                </li>
              ))}
            </ul>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

function UserMenu() {
  const firm = useApp((s) => s.firm);
  const users = useApp((s) => s.users);
  const uidNow = useApp((s) => s.currentUserId);
  const me = useCurrentUser();
  const navigate = useNavigate();
  const initials = me.name.replace(/^CA\s+/, "").split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex h-9 w-9 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground" aria-label="User menu">{initials}</button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuLabel>
          <div>{me.name} <span className="text-xs font-normal text-muted-foreground">· {me.role}</span></div>
          <div className="text-xs font-normal text-muted-foreground">{firm?.name ?? "No firm set up"}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">Switch user (Partner = all clients, Staff = assigned clients)</DropdownMenuLabel>
        {users.map((u) => (
          <DropdownMenuItem key={u.id} onSelect={() => { switchUser(u.id); navigate({ to: "/" }); }}>
            <Check className={cn("mr-2 h-4 w-4", u.id === uidNow ? "opacity-100" : "opacity-0")} /> {u.name} <span className="ml-auto text-xs text-muted-foreground">{u.role}</span>
          </DropdownMenuItem>
        ))}
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate({ to: "/settings" })}>Settings</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate({ to: "/setup" })}>Guided setup</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => { resetAll(); navigate({ to: "/" }); }}>Reset demo data</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/clients", label: "Clients", icon: Users },
  { to: "/workspace", label: "Client workspace", icon: Briefcase },
  { to: "/notices", label: "Notices", icon: Bell },
  { to: "/reports", label: "Reports", icon: FileBarChart },
  { to: "/activity", label: "Activity log", icon: History },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/setup", label: "Guided setup", icon: Rocket },
] as const;

function ClientSwitcher() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const path = useRouterState({ select: (s) => s.location.pathname });
  const clients = useClients();
  const current = clients.find((c) => path.startsWith(`/workspace/${c.id}`));
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button className="flex h-9 w-44 items-center justify-between rounded-md border bg-background px-3 text-sm hover:bg-accent/50 sm:w-72" aria-label="Switch client">
          <span className="truncate">{current ? current.name : "Switch client…"}</span>
          <ChevronsUpDown className="h-4 w-4 text-muted-foreground" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search by name or GSTIN…" />
          <CommandList>
            <CommandEmpty>{clients.length ? "No client found." : "No clients yet — load the demo firm or add a client."}</CommandEmpty>
            <CommandGroup heading="Clients">
              {clients.map((c) => (
                <CommandItem key={c.id} value={`${c.name} ${c.gstin}`} onSelect={() => { setOpen(false); navigate({ to: "/workspace/$clientId", params: { clientId: c.id }, search: { tab: "overview" } }); }}>
                  <Check className={cn("mr-2 h-4 w-4", current?.id === c.id ? "opacity-100" : "opacity-0")} />
                  <div>
                    <div>{c.name}{!c.active && <span className="ml-1 text-xs text-muted-foreground">(inactive)</span>}</div>
                    <div className="font-mono text-[11px] text-muted-foreground">{c.gstin}</div>
                  </div>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const path = useRouterState({ select: (s) => s.location.pathname });
  const dark = useApp((s) => s.dark);
  const fy = useApp((s) => s.prefs.fy);
  // auto-refresh GSP tokens shortly before they expire
  useEffect(() => {
    const t = setInterval(() => autoRefreshSessions(), 60000);
    const first = setTimeout(() => autoRefreshSessions(), 3000);
    return () => { clearInterval(t); clearTimeout(first); };
  }, []);
  if (path.startsWith("/print/")) return <>{children}</>;
  return (
    <div className="flex min-h-screen bg-background">
      <aside className={cn("sticky top-0 hidden h-screen shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground transition-all md:flex", collapsed ? "w-16" : "w-60")}>
        <div className="flex h-14 items-center gap-2 border-b border-sidebar-border px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-sidebar-primary text-sm font-bold text-sidebar-primary-foreground">G</div>
          {!collapsed && (
            <div className="leading-tight">
              <div className="text-sm font-semibold">Complete GST Suite</div>
              <div className="text-[11px] text-sidebar-foreground/60">for CA firms</div>
            </div>
          )}
        </div>
        <nav className="flex-1 space-y-1 p-2" aria-label="Main">
          {NAV.map((n) => {
            const active = n.to === "/" ? path === "/" : path.startsWith(n.to);
            return (
              <Link key={n.to} to={n.to} title={n.label} className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors", active ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground" : "text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground")}>
                <n.icon className="h-4 w-4 shrink-0" />
                {!collapsed && n.label}
              </Link>
            );
          })}
        </nav>
        {!collapsed && (
          <div className="m-2 rounded-md border border-sidebar-border p-3 text-[11px] leading-relaxed text-sidebar-foreground/70">
            <ShieldCheck className="mb-1 h-4 w-4" />
            We never ask for GST portal passwords. Portal access is only through a GSP with the client's OTP, or files you download.
          </div>
        )}
        <button onClick={() => setCollapsed(!collapsed)} className="flex h-10 items-center justify-center border-t border-sidebar-border text-sidebar-foreground/60 hover:text-sidebar-foreground" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
        </button>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-14 items-center gap-2 border-b bg-background/95 px-3 backdrop-blur md:gap-3 md:px-6">
          <MobileNav />
          <ClientSwitcher />
          <Select value={fy} onValueChange={(v) => setState((s) => ({ prefs: { ...s.prefs, fy: v } }))}>
            <SelectTrigger className="h-9 w-32 sm:w-40" aria-label="Financial year"><SelectValue /></SelectTrigger>
            <SelectContent>
              {["2023-24", "2024-25", "2025-26", "2026-27"].map((y) => (
                <SelectItem key={y} value={y} disabled={y !== "2025-26"}>FY {y}{y !== "2025-26" ? " (no data)" : ""}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="ml-auto flex items-center gap-2 md:gap-3">
            <RunLogButton />
            <button onClick={() => setState({ dark: !dark })} className="flex h-9 w-9 items-center justify-center rounded-md border hover:bg-accent" aria-label="Toggle dark mode">
              {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </button>
            <UserMenu />
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1500px] flex-1 p-4 md:p-6"><Breadcrumbs />{children}</main>
      </div>
      <DrillSheet />
    </div>
  );
}

/** Tablet / small screens: the sidebar becomes a menu sheet. */
function MobileNav() {
  const [open, setOpen] = useState(false);
  const path = useRouterState({ select: (s) => s.location.pathname });
  return (
    <>
      <button className="flex h-9 w-9 items-center justify-center rounded-md border md:hidden" aria-label="Open menu" onClick={() => setOpen(true)}>
        <LayoutDashboard className="h-4 w-4" />
      </button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="left" className="w-64 bg-sidebar text-sidebar-foreground">
          <SheetHeader><SheetTitle className="text-sidebar-foreground">Complete GST Suite</SheetTitle><SheetDescription className="sr-only">Main menu</SheetDescription></SheetHeader>
          <nav className="space-y-1 p-2">
            {NAV.map((n) => (
              <Link key={n.to} to={n.to} onClick={() => setOpen(false)} className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-sm", (n.to === "/" ? path === "/" : path.startsWith(n.to)) ? "bg-sidebar-accent font-medium" : "text-sidebar-foreground/80")}>
                <n.icon className="h-4 w-4" /> {n.label}
              </Link>
            ))}
          </nav>
        </SheetContent>
      </Sheet>
    </>
  );
}
