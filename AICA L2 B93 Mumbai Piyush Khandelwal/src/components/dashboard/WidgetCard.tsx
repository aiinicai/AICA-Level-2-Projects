import { useState } from "react";
import {
  Copy,
  Download,
  GripVertical,
  Maximize2,
  Minimize2,
  MoreHorizontal,
  Pencil,
  RefreshCw,
  Table2,
  Trash2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { WidgetView } from "@/components/widgets/WidgetView";
import type { DashboardFilterDef, Widget } from "@/lib/types";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface Props {
  widget: Widget;
  filters?: DashboardFilterDef[];
  editing?: boolean;
  onEdit?: () => void;
  onDuplicate?: () => void;
  onDelete?: () => void;
  onResize?: (delta: 1 | -1) => void;
  onDrilldown?: (w: Widget) => void;
  dragHandlers?: React.HTMLAttributes<HTMLDivElement>;
}

export function WidgetCard({
  widget,
  filters = [],
  editing,
  onEdit,
  onDuplicate,
  onDelete,
  onResize,
  onDrilldown,
  dragHandlers,
}: Props) {
  const [refreshing, setRefreshing] = useState(false);

  const refresh = () => {
    setRefreshing(true);
    setTimeout(() => {
      setRefreshing(false);
      toast.success(`${widget.title} refreshed`);
    }, 600);
  };

  return (
    <section
      className={cn(
        "panel group flex h-full min-h-0 flex-col p-4 transition",
        editing && "ring-1 ring-border-strong hover:ring-primary/40",
      )}
      aria-label={widget.title}
      {...dragHandlers}
    >
      <header className="mb-3 flex items-start gap-2">
        {editing && (
          <GripVertical
            className="mt-0.5 size-4 shrink-0 cursor-grab text-muted-foreground active:cursor-grabbing"
            aria-hidden
          />
        )}
        <div className="min-w-0 flex-1">
          <h3 className="truncate text-sm font-semibold tracking-tight">{widget.title}</h3>
          {widget.subtitle && <p className="truncate text-xs text-muted-foreground">{widget.subtitle}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
          {editing && onResize && (
            <>
              <Button variant="ghost" size="icon" className="size-7" aria-label="Make narrower" onClick={() => onResize(-1)}>
                <Minimize2 className="size-3.5" aria-hidden />
              </Button>
              <Button variant="ghost" size="icon" className="size-7" aria-label="Make wider" onClick={() => onResize(1)}>
                <Maximize2 className="size-3.5" aria-hidden />
              </Button>
            </>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="size-7" aria-label={`${widget.title} options`}>
                <MoreHorizontal className="size-4" aria-hidden />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-44">
              {onEdit && (
                <DropdownMenuItem onSelect={onEdit}>
                  <Pencil className="size-4" aria-hidden /> Edit
                </DropdownMenuItem>
              )}
              {onDuplicate && (
                <DropdownMenuItem onSelect={onDuplicate}>
                  <Copy className="size-4" aria-hidden /> Duplicate
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onSelect={refresh}>
                <RefreshCw className={cn("size-4", refreshing && "animate-spin")} aria-hidden /> Refresh
              </DropdownMenuItem>
              {widget.query && onDrilldown && (
                <DropdownMenuItem onSelect={() => onDrilldown(widget)}>
                  <Table2 className="size-4" aria-hidden /> View records
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onSelect={() => toast("Export starts from the dashboard toolbar.")}>
                <Download className="size-4" aria-hidden /> Export
              </DropdownMenuItem>
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive" onSelect={onDelete}>
                    <Trash2 className="size-4" aria-hidden /> Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <div className={cn("min-h-0 flex-1", refreshing && "opacity-50")}>
        <WidgetView widget={widget} filters={filters} onDrilldown={onDrilldown} />
      </div>
    </section>
  );
}
