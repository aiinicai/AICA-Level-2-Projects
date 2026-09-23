import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight, Download, Search, SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatValue } from "@/lib/format";
import { useFormatOpts } from "@/lib/store";
import type { DataResult } from "@/lib/types";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

interface Props {
  result: DataResult;
  format?: string;
  compact?: boolean;
  pageSize?: number;
  title?: string;
}

export function DataTable({ result, compact, pageSize = 8, title = "export" }: Props) {
  const fmt = useFormatOpts();
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<{ field: string; dir: "asc" | "desc" } | null>(null);
  const [page, setPage] = useState(0);
  const [hidden, setHidden] = useState<string[]>([]);

  const columns = result.columns.filter((c) => !c.name.startsWith("__"));
  const visible = columns.filter((c) => !hidden.includes(c.name));

  const rows = useMemo(() => {
    let out = result.rows;
    if (query.trim()) {
      const q = query.toLowerCase();
      out = out.filter((r) => visible.some((c) => String(r[c.name] ?? "").toLowerCase().includes(q)));
    }
    if (sort) {
      out = [...out].sort((a, b) => {
        const av = a[sort.field];
        const bv = b[sort.field];
        const cmp =
          typeof av === "number" && typeof bv === "number" ? av - bv : String(av ?? "").localeCompare(String(bv ?? ""));
        return sort.dir === "desc" ? -cmp : cmp;
      });
    }
    return out;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result.rows, query, sort, hidden.join(",")]);

  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  const current = Math.min(page, pages - 1);
  const slice = rows.slice(current * pageSize, current * pageSize + pageSize);

  const cellValue = (value: string | number | null, type: string) => {
    if (type === "currency") return formatValue(value, "currency", { ...fmt, compact: true });
    if (type === "percent") return formatValue(value, "percent", fmt);
    if (type === "date") return formatValue(value, "date");
    if (type === "number") return formatValue(value, "number", { ...fmt, compact: false });
    return String(value ?? "—");
  };

  const exportCsv = () => {
    const head = visible.map((c) => `"${c.label}"`).join(",");
    const body = rows
      .map((r) => visible.map((c) => `"${String(r[c.name] ?? "").replace(/"/g, '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([`${head}\n${body}`], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "-").toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${rows.length} rows to CSV`);
  };

  if (!result.rows.length) {
    return (
      <div className="flex h-full min-h-32 flex-col items-center justify-center gap-1 text-center">
        <p className="text-sm font-medium">No matching records</p>
        <p className="text-xs text-muted-foreground">Try widening the date range or clearing filters.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-40 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(0);
            }}
            placeholder="Search records"
            aria-label="Search records"
            className="h-8 pl-8 text-xs"
          />
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs">
              <SlidersHorizontal className="size-3.5" aria-hidden />
              Columns
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="max-h-72 overflow-auto">
            <DropdownMenuLabel>Visible columns</DropdownMenuLabel>
            {columns.map((c) => (
              <DropdownMenuCheckboxItem
                key={c.name}
                checked={!hidden.includes(c.name)}
                onCheckedChange={(checked) =>
                  setHidden((h) => (checked ? h.filter((x) => x !== c.name) : [...h, c.name]))
                }
              >
                {c.label}
              </DropdownMenuCheckboxItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <Button variant="outline" size="sm" className="h-8 gap-1.5 text-xs" onClick={exportCsv}>
          <Download className="size-3.5" aria-hidden />
          CSV
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-auto rounded-lg border">
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 bg-surface-muted">
            <tr>
              {visible.map((c) => (
                <th key={c.name} scope="col" className="border-b px-3 py-2 font-medium whitespace-nowrap">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 hover:text-primary"
                    onClick={() =>
                      setSort((s) =>
                        s?.field === c.name ? { field: c.name, dir: s.dir === "asc" ? "desc" : "asc" } : { field: c.name, dir: "desc" },
                      )
                    }
                  >
                    {c.label}
                    {sort?.field === c.name &&
                      (sort.dir === "asc" ? <ArrowUp className="size-3" aria-hidden /> : <ArrowDown className="size-3" aria-hidden />)}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {slice.map((r, i) => (
              <tr key={i} className="hover:bg-muted/50">
                {visible.map((c) => (
                  <td
                    key={c.name}
                    className={cn(
                      "border-b px-3 py-2 whitespace-nowrap",
                      c.role === "measure" && "num text-right tabular-nums",
                      compact && "py-1.5",
                    )}
                  >
                    {c.name === "status" ? <StatusPill value={String(r[c.name])} /> : cellValue(r[c.name], c.type)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="num">
          {rows.length.toLocaleString("en-IN")} rows{result.truncated ? " (truncated)" : ""}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            aria-label="Previous page"
            disabled={current === 0}
            onClick={() => setPage((p) => Math.max(0, p - 1))}
          >
            <ChevronLeft className="size-4" aria-hidden />
          </Button>
          <span className="num px-1">
            {current + 1} / {pages}
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="size-7"
            aria-label="Next page"
            disabled={current >= pages - 1}
            onClick={() => setPage((p) => Math.min(pages - 1, p + 1))}
          >
            <ChevronRight className="size-4" aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  );
}

export function StatusPill({ value }: { value: string }) {
  const tone =
    value === "Paid" || value === "Settled" || value === "Healthy"
      ? "bg-positive/12 text-positive"
      : value === "Overdue" || value === "Failed"
        ? "bg-negative/12 text-negative"
        : value === "Unpaid" || value === "Pending"
          ? "bg-warning/15 text-warning"
          : "bg-muted text-muted-foreground";
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium", tone)}>
      {value}
    </span>
  );
}
