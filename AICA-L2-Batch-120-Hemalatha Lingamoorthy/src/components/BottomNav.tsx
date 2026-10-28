import { Link } from "@tanstack/react-router";
import { Mic, LineChart, Wind, Shield } from "lucide-react";

const items = [
  { to: "/", label: "Practice", icon: Mic },
  { to: "/progress", label: "Progress", icon: LineChart },
  { to: "/warmup", label: "Warm-up", icon: Wind },
  { to: "/privacy", label: "Privacy", icon: Shield },
] as const;

export function BottomNav() {
  return (
    <nav className="no-print fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/90 backdrop-blur safe-bottom">
      <div className="mx-auto flex max-w-md justify-around pt-2">
        {items.map(({ to, label, icon: Icon }) => (
          <Link
            key={to}
            to={to}
            activeOptions={{ exact: to === "/" }}
            className="flex min-h-12 min-w-16 flex-col items-center gap-1 rounded-xl px-3 py-1 text-xs text-muted-foreground"
            activeProps={{ className: "text-primary" }}
          >
            <Icon className="h-5 w-5" />
            {label}
          </Link>
        ))}
      </div>
    </nav>
  );
}
