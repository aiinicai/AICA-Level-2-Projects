import type { ReactNode } from "react";
import { AppHeader } from "./app-header";
import { AppNav } from "./app-nav";

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen w-full bg-background">
      <aside className="sticky top-0 hidden h-screen w-64 shrink-0 border-r border-sidebar-border lg:block">
        <AppNav />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader />
        <main className="flex-1">
          <div className="page-container">{children}</div>
        </main>
      </div>
    </div>
  );
}
