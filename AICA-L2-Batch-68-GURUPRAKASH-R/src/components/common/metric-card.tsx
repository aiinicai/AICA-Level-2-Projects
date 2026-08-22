import type { SummaryMetric } from "@/types/dashboard";
import { cn } from "@/lib/utils";

const TONE_ACCENT: Record<string, string> = {
  neutral: "bg-border",
  info: "bg-chart-2",
  success: "bg-chart-3",
  warning: "bg-chart-4",
  critical: "bg-chart-5",
};

export function MetricCard({ metric, className }: { metric: SummaryMetric; className?: string }) {
  return (
    <article
      className={cn(
        "relative overflow-hidden rounded-md border border-border bg-card px-4 py-3.5 shadow-panel",
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          "absolute inset-y-0 left-0 w-0.5",
          TONE_ACCENT[metric.tone ?? "neutral"] ?? TONE_ACCENT.neutral,
        )}
      />
      <p className="label-caps">{metric.label}</p>
      <p className="mt-2 font-serif text-2xl font-semibold text-foreground">{metric.value}</p>
      {metric.hint && <p className="mt-1 text-xs text-muted-foreground">{metric.hint}</p>}
    </article>
  );
}
