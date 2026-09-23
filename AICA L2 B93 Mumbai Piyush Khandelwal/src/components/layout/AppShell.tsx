import { useState, type ReactNode } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  Building2,
  Check,
  ChevronsUpDown,
  Grid2x2,
  HelpCircle,
  LogOut,
  Menu,
  MoreHorizontal,
  Search,
  Settings,
  Sparkles,
  Sun,
  Moon,
  UsersRound,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { InstallAppButton } from "@/components/pwa/InstallAppButton";
import { OfflineBanner } from "@/components/pwa/OfflineBanner";
import { CommandPalette } from "./CommandPalette";
import { NotificationsPanel } from "./NotificationsPanel";
import { AssistantDialog } from "./AssistantDialog";
import { useWorkspace } from "@/lib/store";
import { MOBILE_NAV, NAV } from "./nav";
import { cn } from "@/lib/utils";


export function AppShell({ children }: { children: ReactNode }) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-background">
      <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r bg-sidebar lg:flex">
        <SidebarContent onNavigate={() => undefined} />
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <OfflineBanner />
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-surface/85 px-3 backdrop-blur sm:px-4 lg:px-6">
          <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
                <Menu className="size-5" aria-hidden />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-72 p-0">
              <SheetHeader className="sr-only">
                <SheetTitle>Navigation</SheetTitle>
              </SheetHeader>
              <SidebarContent onNavigate={() => setDrawerOpen(false)} />
            </SheetContent>
          </Sheet>

          <button
            type="button"
            onClick={() => setPaletteOpen(true)}
            className="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg border bg-surface-muted px-2.5 sm:px-3 text-sm text-muted-foreground transition hover:border-border-strong sm:max-w-sm"
          >
            <Search className="size-4 shrink-0" aria-hidden />
            <span className="truncate">Search dashboards, data, people…</span>
            <kbd className="ml-auto hidden items-center gap-0.5 rounded border bg-surface px-1.5 py-0.5 text-[10px] font-medium sm:inline-flex">
              ⌘K
            </kbd>
          </button>

          <div className="ml-auto flex shrink-0 items-center gap-0.5 sm:gap-1">
            <Button variant="ghost" size="sm" className="hidden gap-1.5 sm:inline-flex" onClick={() => setAssistantOpen(true)}>
              <Sparkles className="size-4 text-primary" aria-hidden />
              Ask your data
            </Button>
            <ThemeToggle />
            <NotificationsPanel />
            <UserMenu />
          </div>
        </header>

        <main className="min-w-0 flex-1 pb-20 lg:pb-0">{children}</main>
      </div>

      <MobileTabBar />
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} onAssistant={() => setAssistantOpen(true)} />
      <AssistantDialog open={assistantOpen} onOpenChange={setAssistantOpen} />
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate: () => void }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2.5 border-b px-4">
        <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Grid2x2 className="size-4" aria-hidden />
        </span>
        <span className="font-display text-[0.95rem] font-semibold tracking-tight">The DASH</span>
      </div>

      <WorkspaceSwitcher />

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2" aria-label="Main">
        {NAV.map((item) => {
          const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
          return (
            <Link
              key={item.to}
              to={item.to as never}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-sidebar-accent text-sidebar-accent-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent/60",
              )}
            >
              <item.icon className={cn("size-4 shrink-0", active && "text-primary")} aria-hidden />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="space-y-0.5 border-t px-3 py-3">
        <Link
          to="/help"
          onClick={onNavigate}
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent/60"
        >
          <HelpCircle className="size-4 shrink-0" aria-hidden />
          Help
        </Link>
        <InstallAppButton />
        <Link
          to="/settings"
          onClick={onNavigate}
          className="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-sidebar-foreground transition-colors hover:bg-sidebar-accent/60"
        >
          <Settings className="size-4 shrink-0" aria-hidden />
          Settings
        </Link>
      </div>
    </div>
  );
}

function WorkspaceSwitcher() {
  const { settings } = useWorkspace();
  return (
    <div className="px-3 pt-3">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex w-full items-center gap-2.5 rounded-lg border bg-surface px-2.5 py-2 text-left transition hover:border-border-strong"
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
              <Building2 className="size-3.5" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-xs font-semibold">{settings.workspaceName}</span>
              <span className="block truncate text-[11px] text-muted-foreground">Demo workspace</span>
            </span>
            <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground" aria-hidden />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          <DropdownMenuItem>
            <Check className="size-4 text-primary" aria-hidden /> {settings.workspaceName}
          </DropdownMenuItem>
          <DropdownMenuItem disabled>Acme Exports (invite pending)</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link to="/settings">Workspace settings</Link>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

function ThemeToggle() {
  const { settings, updateSettings } = useWorkspace();
  const next = settings.theme === "dark" ? "light" : "dark";
  return (
    <Button
      variant="ghost"
      size="icon"
      aria-label={`Switch to ${next} mode`}
      onClick={() => updateSettings({ theme: next })}
    >
      <Sun className="size-4 dark:hidden" aria-hidden />
      <Moon className="hidden size-4 dark:block" aria-hidden />
    </Button>
  );
}

function UserMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className="ml-1 rounded-full focus-visible:ring-2 focus-visible:ring-ring" aria-label="Account menu">
          <Avatar className="size-8">
            <AvatarFallback className="bg-primary-soft text-xs font-semibold text-primary">RM</AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <span className="block text-sm font-medium">Rahul Menon</span>
          <span className="block text-xs font-normal text-muted-foreground">rahul@acme.in · Owner</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/settings">
            <Settings className="size-4" aria-hidden /> Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <Link to="/team">
            <UsersRound className="size-4" aria-hidden /> Team
          </Link>
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/login">
            <LogOut className="size-4" aria-hidden /> Sign out
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function MobileTabBar() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const [open, setOpen] = useState(false);

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex items-stretch border-t bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
      aria-label="Primary"
    >
      {MOBILE_NAV.map((item) => {
        const active = item.to === "/" ? pathname === "/" : pathname.startsWith(item.to);
        return (
          <Link
            key={item.to}
            to={item.to as never}
            className={cn(
              "flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium",
              active ? "text-primary" : "text-muted-foreground",
            )}
          >
            <item.icon className="size-5" aria-hidden />
            {item.label}
          </Link>
        );
      })}
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetTrigger asChild>
          <button type="button" className="flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium text-muted-foreground">
            <MoreHorizontal className="size-5" aria-hidden />
            More
          </button>
        </SheetTrigger>
        <SheetContent side="bottom" className="rounded-t-2xl">
          <SheetHeader>
            <SheetTitle>More</SheetTitle>
          </SheetHeader>
          <div className="grid grid-cols-2 gap-2 p-4 pt-0">
            {[...NAV.slice(2), { to: "/settings", label: "Settings", icon: Settings }, { to: "/help", label: "Help", icon: HelpCircle }].map(
              (item) => (
                <Link
                  key={item.to}
                  to={item.to as never}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2.5 rounded-lg border bg-surface px-3 py-3 text-sm font-medium"
                >
                  <item.icon className="size-4 text-primary" aria-hidden />
                  {item.label}
                </Link>
              ),
            )}
          </div>
          <div className="border-t p-3">
            <InstallAppButton variant="menu" />
          </div>
        </SheetContent>
      </Sheet>
    </nav>
  );
}
