import { cn } from "@/lib/utils";
import type { RiskRating } from "@/types/common";

const RISK_STYLES: Record<RiskRating, string> = {
  High: "border-critical-foreground/25 bg-critical text-critical-foreground",
  Medium: "border-warning-foreground/20 bg-warning text-warning-foreground",
  Low: "border-success-foreground/20 bg-success text-success-foreground",
};

export function RiskBadge({ rating, className }: { rating: RiskRating; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border px-2 py-0.5 text-xs font-semibold tracking-wide uppercase",
        RISK_STYLES[rating],
        className,
      )}
    >
      {rating} risk
    </span>
  );
}
