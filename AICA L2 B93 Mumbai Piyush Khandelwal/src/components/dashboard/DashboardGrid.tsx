import { useRef } from "react";
import type { DashboardFilterDef, Widget } from "@/lib/types";
import { WidgetCard } from "./WidgetCard";
import { cn } from "@/lib/utils";

const SPAN: Record<number, string> = {
  3: "md:col-span-6 xl:col-span-3",
  4: "md:col-span-6 xl:col-span-4",
  6: "md:col-span-12 xl:col-span-6",
  7: "md:col-span-12 xl:col-span-7",
  8: "md:col-span-12 xl:col-span-8",
  12: "md:col-span-12",
};

const HEIGHT: Record<number, string> = {
  2: "h-44",
  3: "h-60",
  4: "h-[19rem]",
  5: "h-[23rem]",
  6: "h-[27rem]",
};

export const WIDTH_STEPS = [3, 4, 6, 8, 12];

export function DashboardGrid({
  widgets,
  filters,
  editing,
  onEdit,
  onDuplicate,
  onDelete,
  onResize,
  onReorder,
  onDrilldown,
}: {
  widgets: Widget[];
  filters: DashboardFilterDef[];
  editing?: boolean;
  onEdit?: (w: Widget) => void;
  onDuplicate?: (w: Widget) => void;
  onDelete?: (w: Widget) => void;
  onResize?: (w: Widget, delta: 1 | -1) => void;
  onReorder?: (from: number, to: number) => void;
  onDrilldown?: (w: Widget) => void;
}) {
  const dragIndex = useRef<number | null>(null);

  return (
    <div className={cn("grid grid-cols-1 gap-4 md:grid-cols-12", editing && "grid-paper rounded-xl p-2")}>
      {widgets.map((w, index) => (
        <div
          key={w.id}
          className={cn("min-w-0", SPAN[w.layout.w] ?? SPAN[6], HEIGHT[w.layout.h] ?? HEIGHT[4])}
          draggable={editing}
          onDragStart={() => (dragIndex.current = index)}
          onDragOver={(e) => editing && e.preventDefault()}
          onDrop={(e) => {
            if (!editing) return;
            e.preventDefault();
            if (dragIndex.current !== null && dragIndex.current !== index) onReorder?.(dragIndex.current, index);
            dragIndex.current = null;
          }}
        >
          <WidgetCard
            widget={w}
            filters={filters}
            editing={editing}
            onEdit={onEdit ? () => onEdit(w) : undefined}
            onDuplicate={onDuplicate ? () => onDuplicate(w) : undefined}
            onDelete={onDelete ? () => onDelete(w) : undefined}
            onResize={onResize ? (delta) => onResize(w, delta) : undefined}
            onDrilldown={onDrilldown}
          />
        </div>
      ))}
    </div>
  );
}
