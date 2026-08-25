import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export interface DetailCardProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}

export function DetailCard({
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
}: DetailCardProps) {
  return (
    <section
      className={cn("rounded-md border border-border bg-card shadow-panel", className)}
      aria-label={title}
    >
      <header className="flex items-start justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="shrink-0">{actions}</div>}
      </header>
      <div className={cn("px-4 py-4", bodyClassName)}>{children}</div>
    </section>
  );
}

export function DetailField({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="label-caps">{label}</dt>
      <dd className="mt-1 text-sm text-foreground">{value}</dd>
    </div>
  );
}
