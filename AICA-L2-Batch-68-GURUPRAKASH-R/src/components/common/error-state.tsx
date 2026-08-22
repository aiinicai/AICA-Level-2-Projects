import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export function ErrorState({
  title = "Unable to load this section",
  message = "The records could not be retrieved. Please retry, or contact the audit administrator if the issue persists.",
  onRetry,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        "flex flex-col items-start gap-3 rounded-md border border-critical-foreground/25 bg-critical px-5 py-5",
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-4 text-critical-foreground" aria-hidden />
        <div>
          <p className="text-sm font-semibold text-critical-foreground">{title}</p>
          <p className="mt-1 max-w-xl text-sm text-critical-foreground/85">{message}</p>
        </div>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Retry
        </Button>
      )}
    </div>
  );
}
