import { cn } from "@/lib/utils";

const tone: Record<string, string> = {
  DRAFT: "bg-muted text-muted-foreground border-border",
  PENDING: "bg-warning/15 text-warning border-warning/30",
  APPROVED: "bg-success/15 text-success border-success/30",
  ACTIVE: "bg-success/15 text-success border-success/30",
  ACCEPTED: "bg-success/15 text-success border-success/30",
  PARTIAL: "bg-info/15 text-info border-info/30",
  REJECTED: "bg-destructive/15 text-destructive border-destructive/30",
  CANCELLED: "bg-destructive/15 text-destructive border-destructive/30",
  INACTIVE: "bg-muted text-muted-foreground border-border",
  OK: "bg-success/15 text-success border-success/30",
  DAMAGED: "bg-destructive/15 text-destructive border-destructive/30",
  WRONG_ITEM: "bg-destructive/15 text-destructive border-destructive/30",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        tone[status] ?? "bg-muted text-muted-foreground border-border",
        className,
      )}
    >
      {status.replace("_", " ")}
    </span>
  );
}
