import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLiveData } from "@/lib/live-data";

export function PageHeader({
  title,
  description,
  actions,
  breadcrumb,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  breadcrumb?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-3 border-b bg-surface px-4 py-4 sm:px-6 lg:px-8">
      {breadcrumb}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-tight sm:text-2xl">{title}</h1>
          {description && <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </header>
  );
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-surface px-6 py-14 text-center">
      <span className="flex size-11 items-center justify-center rounded-full bg-primary-soft text-primary">
        <Icon className="size-5" aria-hidden />
      </span>
      <div>
        <h3 className="text-base font-semibold">{title}</h3>
        <p className="mx-auto mt-1 max-w-sm text-sm text-muted-foreground">{description}</p>
      </div>
      {action}
    </div>
  );
}

export function ErrorState({
  title,
  description,
  onRetry,
  secondary,
}: {
  title: string;
  description: string;
  onRetry?: () => void;
  secondary?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/5 p-5">
      <span className="flex items-center gap-2 text-sm font-semibold text-destructive">
        <AlertTriangle className="size-4" aria-hidden />
        {title}
      </span>
      <p className="text-sm text-muted-foreground">{description}</p>
      <div className="flex flex-wrap gap-2">
        {onRetry && (
          <Button size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
        {secondary}
      </div>
    </div>
  );
}

export function DemoBadge({ className }: { className?: string }) {
  const { live } = useLiveData();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${
        live
          ? "border-positive/30 bg-positive/10 text-positive"
          : "border-border bg-surface-muted text-muted-foreground"
      } ${className ?? ""}`}
    >
      {live ? "Your data" : "Demo data"}
    </span>
  );
}
