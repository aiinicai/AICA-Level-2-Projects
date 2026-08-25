import { Check } from "lucide-react";
import { LIFECYCLE_STAGES, type LifecycleStage } from "@/types/common";
import { cn } from "@/lib/utils";

export interface LifecycleIndicatorProps {
  currentStage: LifecycleStage;
  stages?: readonly LifecycleStage[];
  className?: string;
  compact?: boolean;
}

/** Horizontal engagement lifecycle: Planning → Fieldwork → … → Closure. */
export function LifecycleIndicator({
  currentStage,
  stages = LIFECYCLE_STAGES,
  className,
  compact = false,
}: LifecycleIndicatorProps) {
  const currentIndex = stages.indexOf(currentStage);

  return (
    <ol
      aria-label="Engagement lifecycle"
      className={cn("flex w-full flex-wrap items-center gap-y-2 lg:flex-nowrap", className)}
    >
      {stages.map((stage, index) => {
        const isComplete = index < currentIndex;
        const isCurrent = index === currentIndex;
        return (
          <li key={stage} className="flex min-w-0 flex-1 items-center gap-2">
            <div className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full border text-[11px] font-semibold",
                  isComplete && "border-transparent bg-primary text-primary-foreground",
                  isCurrent && "border-primary bg-card text-primary ring-2 ring-primary/20",
                  !isComplete && !isCurrent && "border-border bg-surface text-muted-foreground",
                )}
              >
                {isComplete ? <Check className="size-3.5" /> : index + 1}
              </span>
              {!compact && (
                <span
                  className={cn(
                    "truncate text-xs",
                    isCurrent ? "font-semibold text-foreground" : "text-muted-foreground",
                  )}
                >
                  {stage}
                </span>
              )}
              <span className="sr-only">
                {stage}
                {isCurrent ? " (current stage)" : isComplete ? " (completed)" : " (not started)"}
              </span>
            </div>
            {index < stages.length - 1 && (
              <span
                aria-hidden
                className={cn(
                  "mx-1 hidden h-px flex-1 lg:block",
                  isComplete ? "bg-primary/60" : "bg-border",
                )}
              />
            )}
          </li>
        );
      })}
    </ol>
  );
}
