import { useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { THEMES, useTheme, type ThemeId } from "@/hooks/useTheme";

const nav = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/suppliers", label: "Suppliers" },
  { to: "/departments", label: "Departments" },
  { to: "/items", label: "Items" },
  { to: "/lpo", label: "LPO" },
  { to: "/grn", label: "GRN" },
  { to: "/invoices", label: "Invoices" },
  { to: "/reports", label: "Reports" },
  { to: "/insights", label: "AI Insights" },
  { to: "/motivation", label: "Daily Quote" },
  { to: "/install", label: "Install & Share" },
  { to: "/users", label: "Users" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { fullName, roles, signOut, user, supplierAccount } = useAuth();
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-background">
      <header className="no-print sticky top-0 z-30 border-b border-border bg-sidebar/95 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3">
          <Link to={supplierAccount ? "/supplier-portal" : "/dashboard"} className="flex items-center gap-2">
            <span className="grid size-8 place-items-center rounded bg-primary text-sm font-bold text-primary-foreground">
              P
            </span>
            <span className="text-sm font-semibold uppercase tracking-[0.18em] text-sidebar-foreground">
              Easy AI Procura
            </span>
          </Link>

          <nav className="order-3 flex w-full flex-wrap gap-1 md:order-none md:w-auto">
            {(supplierAccount ? [{to: "/supplier-portal" as const, label: "Supplier portal"}] : [...nav, {to: "/supplier-portal" as const, label: "Supplier portal"}]).map((n) => (
              <Link
                key={n.to}
                to={n.to}
                className="rounded px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                activeProps={{ className: "bg-sidebar-accent text-primary font-medium" }}
              >
                {n.label}
              </Link>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            <select
              aria-label="Screen theme"
              value={theme}
              onChange={(e) => setTheme(e.target.value as ThemeId)}
              className="h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground"
            >
              {THEMES.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
            <div className="hidden text-right sm:block">
              <p className="text-xs font-medium text-sidebar-foreground">{fullName || user?.email}</p>
              <p className="num text-[10px] uppercase tracking-wide text-muted-foreground">
                {roles.length ? roles.join(" · ") : "no roles"}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await qc.cancelQueries();
                qc.clear();
                await signOut();
                void navigate({ to: supplierAccount ? "/supplier-login" : "/auth", replace: true });
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1500px] px-4 py-8">{children}</main>
    </div>
  );
}
