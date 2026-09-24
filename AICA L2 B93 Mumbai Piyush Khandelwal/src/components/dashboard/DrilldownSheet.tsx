import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { DataTable } from "@/components/widgets/DataTable";
import { useWidgetData } from "@/components/widgets/useWidgetData";
import type { DashboardFilterDef, Widget } from "@/lib/types";

export function DrilldownSheet({
  widget,
  filters,
  onOpenChange,
}: {
  widget: Widget | null;
  filters: DashboardFilterDef[];
  onOpenChange: (open: boolean) => void;
}) {
  const query = widget?.query
    ? { ...widget.query, groupBy: [], dimensions: [], grain: undefined, limit: 300 }
    : undefined;
  const data = useWidgetData(query, filters);

  return (
    <Sheet open={Boolean(widget)} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 sm:max-w-3xl">
        <SheetHeader>
          <SheetTitle>{widget?.title} — underlying records</SheetTitle>
          <SheetDescription>
            Every record behind this figure. Search, sort and export the rows you need.
          </SheetDescription>
        </SheetHeader>
        <div className="min-h-0 flex-1 p-4 pt-0">
          {data ? (
            <DataTable result={data} pageSize={12} title={widget?.title ?? "records"} compact />
          ) : (
            <p className="text-sm text-muted-foreground">No records available for this widget.</p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
