import { Link } from "@tanstack/react-router";
import { FileSpreadsheet, LayoutDashboard, Settings } from "lucide-react";
import type { ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="bg-sidebar text-sidebar-foreground">
        <div className="mx-auto flex max-w-[1400px] items-center gap-6 px-6 py-3">
          <Link to="/" className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" />
            <div className="leading-tight">
              <div className="text-sm font-semibold tracking-wide">GST Annual Return Reconciliation</div>
              <div className="text-[11px] opacity-70">Offline working papers · data stays on this computer</div>
            </div>
          </Link>
          <nav className="ml-auto flex items-center gap-1 text-sm">
            <Link
              to="/"
              className="flex items-center gap-1.5 rounded px-3 py-1.5 hover:bg-sidebar-accent"
              activeOptions={{ exact: true }}
              activeProps={{ className: "bg-sidebar-accent" }}
            >
              <LayoutDashboard className="h-4 w-4" /> Clients
            </Link>
            <Link
              to="/settings"
              className="flex items-center gap-1.5 rounded px-3 py-1.5 hover:bg-sidebar-accent"
              activeProps={{ className: "bg-sidebar-accent" }}
            >
              <Settings className="h-4 w-4" /> Settings
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-6 py-6">{children}</main>
      <footer className="mx-auto max-w-[1400px] px-6 pb-8 text-xs text-muted-foreground">
        This software performs reconciliation only. It does not file GST returns with the GST portal.
      </footer>
    </div>
  );
}
