import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import type { StatusTone, WorkflowStatus } from "@/types/common";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-sm border px-2 py-0.5 text-xs font-medium whitespace-nowrap",
  {
    variants: {
      tone: {
        neutral: "border-border bg-neutral text-neutral-foreground",
        info: "border-info-foreground/20 bg-info text-info-foreground",
        success: "border-success-foreground/20 bg-success text-success-foreground",
        warning: "border-warning-foreground/20 bg-warning text-warning-foreground",
        critical: "border-critical-foreground/25 bg-critical text-critical-foreground",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

const STATUS_TONES: Record<WorkflowStatus, StatusTone> = {
  Draft: "neutral",
  Pending: "warning",
  "In Progress": "info",
  Submitted: "info",
  "Under Review": "info",
  "Clarification Raised": "warning",
  Accepted: "success",
  Rejected: "critical",
  Overdue: "critical",
  Closed: "success",
};

export interface StatusBadgeProps extends VariantProps<typeof badgeVariants> {
  status: WorkflowStatus | string;
  className?: string;
}

export function StatusBadge({ status, tone, className }: StatusBadgeProps) {
  const resolved = tone ?? STATUS_TONES[status as WorkflowStatus] ?? "neutral";
  return (
    <span className={cn(badgeVariants({ tone: resolved }), className)}>
      <span className="size-1.5 rounded-full bg-current opacity-70" aria-hidden />
      {status}
    </span>
  );
}

export { badgeVariants as statusBadgeVariants };
