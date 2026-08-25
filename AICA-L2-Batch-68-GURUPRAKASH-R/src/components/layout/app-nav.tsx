import { Link, useRouterState } from "@tanstack/react-router";
import { ShieldCheck } from "lucide-react";
import { APP_CONFIG } from "@/config/app";
import { NAVIGATION_GROUP_ORDER, NAVIGATION_ITEMS } from "@/data/navigation";
import { cn } from "@/lib/utils";

export function AppNav({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  const isActive = (to: string) => (to === "/" ? pathname === "/" : pathname.startsWith(to));

  return (
    <div className="flex h-full flex-col bg-sidebar text-sidebar-foreground">
      <div className="flex items-center gap-2.5 border-b border-sidebar-border px-4 py-4">
        <span className="flex size-8 items-center justify-center rounded-sm border border-sidebar-border bg-sidebar-accent">
          <ShieldCheck className="size-4" aria-hidden />
        </span>
        <div className="leading-tight">
          <p className="font-serif text-base font-semibold">{APP_CONFIG.name}</p>
          <p className="text-[11px] text-sidebar-foreground/60">{APP_CONFIG.shortDescription}</p>
        </div>
      </div>

      <nav aria-label="Primary" className="flex-1 overflow-y-auto px-2 py-3">
        {NAVIGATION_GROUP_ORDER.map((group) => {
          const items = NAVIGATION_ITEMS.filter((item) => item.group === group);
          if (items.length === 0) return null;
          return (
            <div key={group} className="mb-4 last:mb-0">
              <p className="px-2 pb-1.5 text-[10px] font-semibold tracking-[0.12em] text-sidebar-foreground/45 uppercase">
                {group}
              </p>
              <ul className="space-y-0.5">
                {items.map((item) => (
                  <li key={item.to}>
                    <Link
                      to={item.to}
                      onClick={onNavigate}
                      className={cn(
                        "block rounded-sm px-2.5 py-1.5 text-[13px] transition-colors",
                        isActive(item.to)
                          ? "bg-sidebar-accent font-medium text-sidebar-accent-foreground"
                          : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground",
                      )}
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </nav>

      <div className="border-t border-sidebar-border px-4 py-3 text-[11px] text-sidebar-foreground/55">
        {APP_CONFIG.stage}
      </div>
    </div>
  );
}
