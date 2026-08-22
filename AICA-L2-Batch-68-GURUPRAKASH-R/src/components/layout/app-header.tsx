import { Menu } from "lucide-react";
import { useState } from "react";
import { useRouterState } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useRole } from "@/context/role-context";
import { findNavigationItem } from "@/data/navigation";
import type { UserRole } from "@/types/common";
import { AppNav } from "./app-nav";

export function AppHeader() {
  const { role, setRole, roles } = useRole();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const current = findNavigationItem(pathname);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border bg-card/95 px-4 backdrop-blur">
      <div className="flex min-w-0 items-center gap-3">
        <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation">
              <Menu className="size-4" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <SheetTitle className="sr-only">Primary navigation</SheetTitle>
            <AppNav onNavigate={() => setMobileNavOpen(false)} />
          </SheetContent>
        </Sheet>
        <p className="truncate text-sm font-medium text-foreground">
          {current?.label ?? "AuditFlow"}
        </p>
      </div>

      <div className="flex items-center gap-2.5">
        <span className="hidden text-[11px] tracking-wide text-muted-foreground uppercase sm:inline">
          Viewing as
        </span>
        <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
          <SelectTrigger className="h-8 w-[190px] text-xs" aria-label="Select role">
            <SelectValue />
          </SelectTrigger>
          <SelectContent align="end">
            {roles.map((option) => (
              <SelectItem key={option} value={option} className="text-xs">
                {option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </header>
  );
}
