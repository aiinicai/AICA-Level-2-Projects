import { useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, Download, Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { inr } from "@/lib/gst/format";
import { useHydrated } from "@/lib/store";

export interface Column<T> {
  key: string;
  header: ReactNode;
  /** plain text title for exports and filter labels */
  title: string;
  /** value used for sorting, filtering, search and export */
  value: (r: T) => string | number | null | undefined;
  cell?: ((r: T) => ReactNode) | undefined;
  align?: "right" | "center" | undefined;
  /** show a column filter (distinct values) */
  filter?: boolean | undefined;
  money?: boolean | undefined;
  className?: string | undefined;
  /** leave out of exports (e.g. action buttons) */
  noExport?: boolean | undefined;
}

interface Props<T> {
  rows: T[];
  columns: Column<T>[];
  rowKey: (r: T) => string;
  exportName: string;
  empty: { message: ReactNode; action?: ReactNode | undefined };
  loading?: boolean | undefined;
  onRowClick?: ((r: T) => void) | undefined;
  toolbar?: ReactNode | undefined;
  selection?: { selected: Set<string>; onChange: (s: Set<string>) => void } | undefined;
  rowClassName?: ((r: T) => string) | undefined;
  maxHeight?: string | undefined;
  initialSort?: { key: string; dir: "asc" | "desc" } | undefined;
  footer?: ReactNode | undefined;
  searchPlaceholder?: string | undefined;
}

const ALL = "__all__";

export function DataTable<T>({ rows, columns, rowKey, exportName, empty, loading: loadingProp, onRowClick, toolbar, selection, rowClassName, maxHeight = "70vh", initialSort, footer, searchPlaceholder }: Props<T>) {
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [sort, setSort] = useState<{ key: string; dir: "asc" | "desc" } | null>(initialSort ?? null);
  const [limit, setLimit] = useState(200);
  // until saved data is read from the browser, show skeleton rows instead of an empty state
  const hydrated = useHydrated();
  const loading = loadingProp || !hydrated;

  const filterCols = columns.filter((c) => c.filter);
  const options = useMemo(
    () => Object.fromEntries(filterCols.map((c) => [c.key, [...new Set(rows.map((r) => String(c.value(r) ?? "")))].filter(Boolean).sort()])),
    [rows, filterCols],
  );

  const shown = useMemo(() => {
    const t = q.trim().toLowerCase();
    let out = rows.filter((r) => {
      for (const c of filterCols) {
        const f = filters[c.key];
        if (f && f !== ALL && String(c.value(r) ?? "") !== f) return false;
      }
      if (!t) return true;
      return columns.some((c) => String(c.value(r) ?? "").toLowerCase().includes(t));
    });
    if (sort) {
      const c = columns.find((x) => x.key === sort.key);
      if (c) {
        out = [...out].sort((a, b) => {
          const va = c.value(a), vb = c.value(b);
          const cmp = typeof va === "number" && typeof vb === "number" ? va - vb : String(va ?? "").localeCompare(String(vb ?? ""), "en-IN", { numeric: true });
          return sort.dir === "asc" ? cmp : -cmp;
        });
      }
    }
    return out;
  }, [rows, q, filters, sort, columns, filterCols]);

  const toggleSort = (key: string) => setSort((s) => (s?.key === key ? (s.dir === "asc" ? { key, dir: "desc" } : null) : { key, dir: "asc" }));
  const exportCols = columns.filter((c) => !c.noExport);
  const exportRows = () => shown.map((r) => exportCols.map((c) => { const v = c.value(r); return v === undefined ? null : v; }));

  async function doExport(kind: "csv" | "xlsx") {
    try {
      const x = await import("@/lib/gst/excel");
      const file = `${exportName}.${kind}`;
      if (kind === "csv") x.downloadCsv(file, exportCols.map((c) => c.title), exportRows());
      else x.downloadBlob(file, await x.buildTableWorkbook(exportName, exportCols.map((c) => c.title), exportRows(), exportCols.map((c) => (c.money ? "money" : "text"))));
      const { log } = await import("@/lib/store");
      log(`Exported ${file}`);
    } catch (e) {
      toast.error(`Export failed: ${e instanceof Error ? e.message : e}`);
    }
  }

  const allSel = selection && shown.length > 0 && shown.every((r) => selection.selected.has(rowKey(r)));
  const active = Object.values(filters).filter((f) => f && f !== ALL).length;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input aria-label="Search table" className="h-9 w-56 pl-8" placeholder={searchPlaceholder ?? "Search…"} value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        {filterCols.map((c) => (
          <label key={c.key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            {c.title}
            <select
              aria-label={`Filter by ${c.title}`}
              className="h-9 max-w-44 rounded-md border bg-background px-2 text-sm text-foreground"
              value={filters[c.key] ?? ALL}
              onChange={(e) => setFilters({ ...filters, [c.key]: e.target.value })}
            >
              <option value={ALL}>All</option>
              {(options[c.key] ?? []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
        ))}
        {active > 0 && <Button size="sm" variant="ghost" onClick={() => setFilters({})}>Clear filters</Button>}
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {toolbar}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="outline" disabled={!shown.length}><Download className="mr-1.5 h-3.5 w-3.5" /> Export</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => void doExport("xlsx")}>Excel (.xlsx)</DropdownMenuItem>
              <DropdownMenuItem onSelect={() => void doExport("csv")}>CSV</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <div className="overflow-auto rounded-md border" style={{ maxHeight }}>
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-muted/95 text-left text-xs text-muted-foreground backdrop-blur">
            <tr>
              {selection && (
                <th className="w-8 px-2 py-2">
                  <input type="checkbox" aria-label="Select all rows" checked={!!allSel} onChange={(e) => selection.onChange(new Set(e.target.checked ? shown.map(rowKey) : []))} />
                </th>
              )}
              {columns.map((c) => (
                <th key={c.key} aria-sort={sort?.key === c.key ? (sort.dir === "asc" ? "ascending" : "descending") : undefined} className={cn("whitespace-nowrap px-2 py-2 font-medium", c.align === "right" && "text-right", c.align === "center" && "text-center")}>
                  <span className={cn("inline-flex items-center gap-1", c.align === "right" && "flex-row-reverse")}>
                    <span className="cursor-pointer hover:text-foreground" onClick={() => toggleSort(c.key)}>{c.header}</span>
                    {c.title && (
                      <button type="button" onClick={() => toggleSort(c.key)} className="rounded hover:text-foreground" aria-label={`Sort by ${c.title}`}>
                        {sort?.key === c.key ? (sort.dir === "asc" ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />) : <ArrowUpDown className="h-3 w-3 opacity-40" />}
                      </button>
                    )}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 6 }, (_, i) => (
                  <tr key={i} className="border-t">
                    {selection && <td className="px-2 py-3" />}
                    {columns.map((c) => <td key={c.key} className="px-2 py-3"><Skeleton className="h-4 w-full max-w-32" /></td>)}
                  </tr>
                ))
              : shown.slice(0, limit).map((r) => {
                  const k = rowKey(r);
                  return (
                    <tr
                      key={k}
                      className={cn("border-t align-top", onRowClick && "cursor-pointer hover:bg-accent/40", rowClassName?.(r))}
                      onClick={onRowClick ? () => onRowClick(r) : undefined}
                      onKeyDown={onRowClick ? (e) => { if (e.key === "Enter") onRowClick(r); } : undefined}
                      tabIndex={onRowClick ? 0 : undefined}
                    >
                      {selection && (
                        <td className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
                          <input type="checkbox" aria-label="Select row" checked={selection.selected.has(k)} onChange={(e) => { const s = new Set(selection.selected); if (e.target.checked) s.add(k); else s.delete(k); selection.onChange(s); }} />
                        </td>
                      )}
                      {columns.map((c) => (
                        <td key={c.key} className={cn("px-2 py-2", c.align === "right" && "whitespace-nowrap text-right tabular-nums", c.align === "center" && "text-center", c.className)}>
                          {c.cell ? c.cell(r) : c.money ? inr(Number(c.value(r) ?? 0)) : String(c.value(r) ?? "—")}
                        </td>
                      ))}
                    </tr>
                  );
                })}
            {!loading && shown.length === 0 && (
              <tr>
                <td colSpan={columns.length + (selection ? 1 : 0)} className="px-4 py-10 text-center">
                  <div className="text-sm text-muted-foreground">{rows.length ? "No rows match your search or filters." : empty.message}</div>
                  {!rows.length && empty.action && <div className="mt-3 flex justify-center">{empty.action}</div>}
                  {rows.length > 0 && <Button className="mt-3" size="sm" variant="outline" onClick={() => { setQ(""); setFilters({}); }}>Clear search and filters</Button>}
                </td>
              </tr>
            )}
          </tbody>
          {footer && !loading && shown.length > 0 && <tfoot className="sticky bottom-0 border-t-2 bg-card font-semibold">{footer}</tfoot>}
        </table>
      </div>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{shown.length} of {rows.length} row(s){selection && selection.selected.size ? ` · ${selection.selected.size} selected` : ""}</span>
        {shown.length > limit && <Button size="sm" variant="ghost" onClick={() => setLimit(limit + 500)}>Show more</Button>}
      </div>
    </div>
  );
}
