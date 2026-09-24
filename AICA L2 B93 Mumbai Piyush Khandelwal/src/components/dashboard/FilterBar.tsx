import { CalendarRange, Filter as FilterIcon, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DATE_RANGES, dateRangeLabel } from "@/lib/query/filters";
import { BRANCHES, CUSTOMERS, REGIONS, SALESPEOPLE } from "@/lib/data/demo-source";
import type { DashboardFilterDef } from "@/lib/types";

const OPTIONS: Record<string, string[]> = {
  branch: BRANCHES,
  region: REGIONS,
  salesperson: SALESPEOPLE,
  customer: CUSTOMERS,
  status: ["Paid", "Partially Paid", "Unpaid", "Overdue"],
};

export function FilterBar({
  filters,
  onChange,
  onAdd,
  onRemove,
}: {
  filters: DashboardFilterDef[];
  onChange: (id: string, value: string) => void;
  onAdd?: (filter: DashboardFilterDef) => void;
  onRemove?: (id: string) => void;
}) {
  const available = Object.keys(OPTIONS).filter((f) => !filters.some((x) => x.field === f));

  return (
    <div className="flex flex-wrap items-center gap-2">
      {filters.map((f) =>
        f.type === "date-range" ? (
          <div key={f.id} className="flex items-center gap-1">
            <Select value={f.value ?? "last_12m"} onValueChange={(v) => onChange(f.id, v)}>
              <SelectTrigger className="h-9 gap-1.5" aria-label="Date range">
                <CalendarRange className="size-3.5 text-muted-foreground" aria-hidden />
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {DATE_RANGES.map((r) => (
                  <SelectItem key={r.id} value={r.id}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="num hidden text-xs text-muted-foreground xl:inline">
              {dateRangeLabel(f.value ?? "last_12m")}
            </span>
          </div>
        ) : (
          <div key={f.id} className="flex items-center">
            <Select value={f.value ?? "All"} onValueChange={(v) => onChange(f.id, v)}>
              <SelectTrigger className="h-9" aria-label={f.label}>
                <span className="text-muted-foreground">{f.label}:</span>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All">All</SelectItem>
                {(f.options ?? OPTIONS[f.field] ?? []).map((o) => (
                  <SelectItem key={o} value={o}>
                    {o}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {onRemove && (
              <Button variant="ghost" size="icon" className="size-8" aria-label={`Remove ${f.label} filter`} onClick={() => onRemove(f.id)}>
                <X className="size-3.5" aria-hidden />
              </Button>
            )}
          </div>
        ),
      )}

      {onAdd && available.length > 0 && (
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="h-9 gap-1.5">
              <FilterIcon className="size-3.5" aria-hidden />
              Add filter
            </Button>
          </PopoverTrigger>
          <PopoverContent align="start" className="w-48 p-1">
            {available.map((field) => (
              <button
                key={field}
                type="button"
                className="w-full rounded-md px-2 py-1.5 text-left text-sm capitalize hover:bg-muted"
                onClick={() =>
                  onAdd({
                    id: `${field}-${Math.random().toString(36).slice(2, 6)}`,
                    label: field.charAt(0).toUpperCase() + field.slice(1),
                    field,
                    type: "select",
                    value: "All",
                  })
                }
              >
                {field}
              </button>
            ))}
          </PopoverContent>
        </Popover>
      )}
    </div>
  );
}
