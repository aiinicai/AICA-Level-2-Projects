import { DATASETS, DATE_FIELD_BY_DATASET, datasetById, demoTables, type Row } from "../data/demo-source";
import type { DataQuery, DataResult, Field, Filter } from "../types";

/**
 * Dashboard query engine.
 * Widgets describe *what* they want (dimensions, measures, filters) and this
 * layer resolves it against whichever adapter owns the dataset. Today the demo
 * adapter answers in-memory; a server-backed adapter can replace it without
 * touching a single widget.
 */

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function grainKey(value: string, grain: DataQuery["grain"]): string {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  const y = d.getUTCFullYear();
  const m = d.getUTCMonth();
  switch (grain) {
    case "day":
      return d.toISOString().slice(0, 10);
    case "week": {
      const start = new Date(d);
      start.setUTCDate(d.getUTCDate() - d.getUTCDay());
      return start.toISOString().slice(0, 10);
    }
    case "quarter":
      return `Q${Math.floor(m / 3) + 1} ${y}`;
    case "year":
      return String(y);
    case "month":
    default:
      return `${MONTHS[m]} ${String(y).slice(2)}`;
  }
}

function sortableKey(value: string, grain: DataQuery["grain"]): number {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return 0;
  return Date.UTC(d.getUTCFullYear(), grain === "year" ? 0 : d.getUTCMonth(), grain === "day" || grain === "week" ? d.getUTCDate() : 1);
}

export function matchesFilter(row: Row, filter: Filter): boolean {
  const raw = row[filter.field];
  const v = filter.value;
  switch (filter.op) {
    case "eq":
      return String(raw) === String(v);
    case "neq":
      return String(raw) !== String(v);
    case "gt":
      return Number(raw) > Number(v);
    case "gte":
      return Number(raw) >= Number(v);
    case "lt":
      return Number(raw) < Number(v);
    case "lte":
      return Number(raw) <= Number(v);
    case "contains":
      return String(raw ?? "").toLowerCase().includes(String(v).toLowerCase());
    case "in":
      return Array.isArray(v) ? v.map(String).includes(String(raw)) : false;
    case "between": {
      const [a, b] = v as [string | number, string | number];
      if (typeof raw === "string" && Number.isNaN(Number(raw))) {
        return raw >= String(a) && raw <= String(b);
      }
      return Number(raw) >= Number(a) && Number(raw) <= Number(b);
    }
    default:
      return true;
  }
}

function aggregate(values: number[], agg: string): number {
  if (!values.length) return 0;
  switch (agg) {
    case "avg":
      return values.reduce((a, b) => a + b, 0) / values.length;
    case "min":
      return Math.min(...values);
    case "max":
      return Math.max(...values);
    case "count":
      return values.length;
    default:
      return values.reduce((a, b) => a + b, 0);
  }
}

/**
 * When a real accounting source is connected its normalised records replace the
 * demo tables everywhere — widgets, explorer, drill-downs and reports.
 */
let liveTables: Record<string, Row[]> | null = null;

export function setLiveTables(tables: Record<string, Row[]> | null) {
  liveTables = tables && Object.keys(tables).length ? tables : null;
}

export function hasLiveData() {
  return liveTables !== null;
}

export function activeTables(): Record<string, Row[]> {
  if (!liveTables) return demoTables();
  const base = Object.fromEntries(DATASETS.map((d) => [d.id, [] as Row[]]));
  return { ...base, ...liveTables };
}

export function runQuery(query: DataQuery): DataResult {
  const tables = activeTables();
  const ds = datasetById(query.dataset);
  const source = tables[query.dataset] ?? [];
  const generatedAt = new Date().toISOString();

  let rows = source;
  for (const filter of query.filters ?? []) {
    rows = rows.filter((r) => matchesFilter(r, filter));
  }

  const dateField = query.dateField ?? DATE_FIELD_BY_DATASET[query.dataset];
  const groupBy = query.groupBy ?? query.dimensions ?? [];
  const measures = query.measures ?? [];

  // No grouping: return raw records (drill-down / table widget).
  if (!groupBy.length && !query.grain) {
    let out = rows;
    for (const s of [...(query.sort ?? [])].reverse()) {
      out = [...out].sort((a, b) => {
        const av = a[s.field];
        const bv = b[s.field];
        const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
        return s.dir === "desc" ? -cmp : cmp;
      });
    }
    const limit = query.limit ?? 500;
    const columns = (query.dimensions?.length
      ? (ds?.fields ?? []).filter((fd) => query.dimensions!.includes(fd.name))
      : (ds?.fields ?? [])) as Field[];
    return {
      columns,
      rows: out.slice(0, limit),
      truncated: out.length > limit,
      generatedAt,
    };
  }

  const keyFields = [...groupBy];
  if (query.grain && dateField && !keyFields.includes(dateField)) keyFields.unshift(dateField);

  const buckets = new Map<string, { key: Record<string, string>; sort: number; rows: Row[] }>();
  for (const row of rows) {
    const key: Record<string, string> = {};
    let sort = 0;
    for (const field of keyFields) {
      if (field === dateField && query.grain) {
        key[field] = grainKey(String(row[field]), query.grain);
        sort = sortableKey(String(row[field]), query.grain);
      } else {
        key[field] = String(row[field] ?? "—");
      }
    }
    const id = keyFields.map((k) => key[k]).join("§");
    const bucket = buckets.get(id) ?? { key, sort, rows: [] };
    bucket.rows.push(row);
    buckets.set(id, bucket);
  }

  let result = [...buckets.values()].map((b) => {
    const out: Record<string, string | number | null> = { ...b.key };
    for (const m of measures) {
      const alias = m.alias ?? m.field;
      out[alias] = Math.round(aggregate(b.rows.map((r) => Number(r[m.field]) || 0), m.aggregation));
    }
    out.__sort = b.sort;
    out.__count = b.rows.length;
    return out;
  });

  if (query.grain) {
    result.sort((a, b) => Number(a.__sort) - Number(b.__sort));
  } else if (query.sort?.length) {
    const s = query.sort[0];
    result.sort((a, b) => {
      const av = a[s.field];
      const bv = b[s.field];
      const cmp = typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv));
      return s.dir === "desc" ? -cmp : cmp;
    });
  } else if (measures.length) {
    const alias = measures[0].alias ?? measures[0].field;
    result.sort((a, b) => Number(b[alias]) - Number(a[alias]));
  }

  const limit = query.limit ?? 100;
  const truncated = result.length > limit;
  result = result.slice(0, limit);

  const columns: Field[] = [
    ...keyFields.map(
      (name) =>
        (ds?.fields.find((fd) => fd.name === name) ?? {
          name,
          label: name,
          type: "string" as const,
          role: "dimension" as const,
        }),
    ),
    ...measures.map((m) => {
      const base = ds?.fields.find((fd) => fd.name === m.field);
      return {
        name: m.alias ?? m.field,
        label: `${m.aggregation === "count" ? "Count of" : m.aggregation === "avg" ? "Avg" : m.aggregation === "sum" ? "" : m.aggregation} ${base?.label ?? m.field}`.trim(),
        type: m.aggregation === "count" ? ("number" as const) : (base?.type ?? ("number" as const)),
        role: "measure" as const,
      };
    }),
  ];

  return { columns, rows: result, truncated, generatedAt };
}

/** Single aggregated number, used by KPI cards, gauges and alerts. */
export function runScalar(query: DataQuery): number {
  const res = runQuery({ ...query, groupBy: [], dimensions: [], grain: undefined, limit: 1_000_000 });
  const measure = query.measures?.[0];
  if (!measure) return res.rows.length;
  if (measure.aggregation === "count") return res.rows.length;
  const values = res.rows.map((r) => Number(r[measure.field]) || 0);
  return Math.round(aggregate(values, measure.aggregation));
}

export function listDatasets() {
  const tables = activeTables();
  return DATASETS.map((d) => ({ ...d, recordCount: tables[d.id]?.length ?? 0 }));
}
