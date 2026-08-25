import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

export interface FilterDefinition {
  key: string;
  label: string;
  options: { value: string; label: string }[];
}

export interface FilterPanelProps {
  filters: FilterDefinition[];
  values: Record<string, string>;
  onChange: (key: string, value: string) => void;
  onReset?: () => void;
  className?: string;
}

export function FilterPanel({ filters, values, onChange, onReset, className }: FilterPanelProps) {
  return (
    <section
      aria-label="Filters"
      className={cn("rounded-md border border-border bg-surface px-4 py-3", className)}
    >
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="size-3.5 text-muted-foreground" aria-hidden />
          <span className="label-caps">Filters</span>
        </div>
        {onReset && (
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={onReset}>
            Reset
          </Button>
        )}
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {filters.map((filter) => (
          <div key={filter.key} className="space-y-1.5">
            <Label htmlFor={`filter-${filter.key}`} className="text-xs text-muted-foreground">
              {filter.label}
            </Label>
            <Select
              value={values[filter.key] ?? "all"}
              onValueChange={(value) => onChange(filter.key, value)}
            >
              <SelectTrigger id={`filter-${filter.key}`} className="h-9 bg-card">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                {filter.options.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        ))}
      </div>
    </section>
  );
}
