import type { ReactNode } from "react";
import { Table, TableBody, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { EmptyState } from "./empty-state";
import { ErrorState } from "./error-state";
import { LoadingState } from "./loading-state";

export interface DataTableColumn {
  key: string;
  header: string;
  align?: "left" | "right" | "center";
  width?: string;
}

export interface DataTableShellProps {
  columns: DataTableColumn[];
  toolbar?: ReactNode;
  caption?: string;
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  isEmpty?: boolean;
  emptyTitle?: string;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  footer?: ReactNode;
  children?: ReactNode;
  className?: string;
}

/**
 * Presentational shell for every register in AuditFlow: toolbar, header row and
 * loading / error / empty handling. Rows are supplied by the calling module.
 */
export function DataTableShell({
  columns,
  toolbar,
  caption,
  isLoading = false,
  error = null,
  onRetry,
  isEmpty = false,
  emptyTitle = "No records yet",
  emptyMessage,
  emptyAction,
  footer,
  children,
  className,
}: DataTableShellProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {toolbar && (
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          {toolbar}
        </div>
      )}

      {error ? (
        <ErrorState message={error} onRetry={onRetry} />
      ) : isLoading ? (
        <LoadingState />
      ) : isEmpty ? (
        <EmptyState title={emptyTitle} message={emptyMessage} action={emptyAction} />
      ) : (
        <div className="overflow-x-auto rounded-md border border-border bg-card shadow-panel">
          <Table>
            {caption && <caption className="sr-only">{caption}</caption>}
            <TableHeader>
              <TableRow className="bg-surface hover:bg-surface">
                {columns.map((column) => (
                  <TableHead
                    key={column.key}
                    style={column.width ? { width: column.width } : undefined}
                    className={cn(
                      "label-caps h-9",
                      column.align === "right" && "text-right",
                      column.align === "center" && "text-center",
                    )}
                  >
                    {column.header}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>{children}</TableBody>
          </Table>
        </div>
      )}

      {footer && <div className="text-xs text-muted-foreground">{footer}</div>}
    </div>
  );
}
