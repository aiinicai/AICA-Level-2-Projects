import type { ActivityEntry } from "@/types/dashboard";
import { cn } from "@/lib/utils";
import { formatDateTime } from "@/lib/format";

export function ActivityTimeline({
  entries,
  className,
}: {
  entries: ActivityEntry[];
  className?: string;
}) {
  return (
    <ol className={cn("relative space-y-4 border-l border-border pl-5", className)}>
      {entries.map((entry) => (
        <li key={entry.id} className="relative">
          <span
            aria-hidden
            className="absolute top-1.5 -left-[23px] size-2 rounded-full border border-card bg-muted-foreground/60"
          />
          <p className="text-sm text-foreground">
            <span className="font-medium">{entry.actor}</span> {entry.action}
            {entry.reference && (
              <span className="ml-1 font-mono text-xs text-muted-foreground">
                ({entry.reference})
              </span>
            )}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">{formatDateTime(entry.occurredAt)}</p>
        </li>
      ))}
    </ol>
  );
}
