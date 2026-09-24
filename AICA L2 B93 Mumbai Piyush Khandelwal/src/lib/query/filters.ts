import { DATE_FIELD_BY_DATASET, datasetById } from "../data/demo-source";
import type { DashboardFilterDef, DataQuery, Filter } from "../types";

/** Demo data runs to 30 Sep 2026; relative ranges anchor there. */
export const DATA_TODAY = new Date(Date.UTC(2026, 8, 30));

export const DATE_RANGES = [
  { id: "last_3m", label: "Last 3 months", months: 3 },
  { id: "last_6m", label: "Last 6 months", months: 6 },
  { id: "last_12m", label: "Last 12 months", months: 12 },
  { id: "ytd", label: "Financial year to date", months: 0 },
  { id: "all", label: "All time", months: 999 },
];

export function dateRangeBounds(id: string): [string, string] {
  const end = DATA_TODAY.toISOString().slice(0, 10);
  if (id === "all") return ["1900-01-01", end];
  if (id === "ytd") {
    const y = DATA_TODAY.getUTCMonth() >= 3 ? DATA_TODAY.getUTCFullYear() : DATA_TODAY.getUTCFullYear() - 1;
    return [`${y}-04-01`, end];
  }
  const months = DATE_RANGES.find((r) => r.id === id)?.months ?? 12;
  const start = new Date(Date.UTC(DATA_TODAY.getUTCFullYear(), DATA_TODAY.getUTCMonth() - months + 1, 1));
  return [start.toISOString().slice(0, 10), end];
}

export function dateRangeLabel(id: string) {
  const [a, b] = dateRangeBounds(id);
  if (id === "all") return "All time";
  const fmt = (s: string) => {
    const d = new Date(s);
    return `${String(d.getUTCDate()).padStart(2, "0")} ${
      ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][d.getUTCMonth()]
    } ${d.getUTCFullYear()}`;
  };
  return `${fmt(a)} → ${fmt(b)}`;
}

/** Only applies a filter when the target dataset actually exposes that field. */
export function applyDashboardFilters(query: DataQuery, filters: DashboardFilterDef[] = []): DataQuery {
  const ds = datasetById(query.dataset);
  if (!ds) return query;
  const extra: Filter[] = [];

  for (const f of filters) {
    if (!f.value || f.value === "All") continue;
    if (f.type === "date-range") {
      const dateField = query.dateField ?? DATE_FIELD_BY_DATASET[query.dataset];
      if (!dateField) continue;
      extra.push({ field: dateField, op: "between", value: dateRangeBounds(f.value) });
    } else if (ds.fields.some((fd) => fd.name === f.field)) {
      extra.push({ field: f.field, op: "eq", value: f.value });
    }
  }

  if (!extra.length) return query;
  return { ...query, filters: [...(query.filters ?? []), ...extra] };
}
