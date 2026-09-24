import { useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowDownRight, ArrowUpRight, Minus, TableIcon } from "lucide-react";
import { formatValue } from "@/lib/format";
import { useFormatOpts } from "@/lib/store";
import type { DashboardFilterDef, Widget } from "@/lib/types";
import { useWidgetData } from "./useWidgetData";
import { DataTable } from "./DataTable";
import { cn } from "@/lib/utils";

const PALETTE = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
  "var(--color-chart-6)",
];

interface Props {
  widget: Widget;
  filters?: DashboardFilterDef[];
  onDrilldown?: (widget: Widget) => void;
  compact?: boolean;
}

export function WidgetView({ widget, filters = [], onDrilldown, compact }: Props) {
  const fmt = useFormatOpts();
  const data = useWidgetData(widget.query, filters);

  if (widget.type === "text") {
    return (
      <div className="prose-sm h-full overflow-auto text-sm leading-relaxed text-muted-foreground">
        {(widget.options.body ?? "Add commentary for your readers.").split("\n").map((line, i) =>
          line.startsWith("## ") ? (
            <h3 key={i} className="mt-2 mb-1 text-sm font-semibold text-foreground">
              {line.slice(3)}
            </h3>
          ) : (
            <p key={i} className="mb-2">
              {line}
            </p>
          ),
        )}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
        <TableIcon className="size-5 text-muted-foreground" aria-hidden />
        <p className="text-sm text-muted-foreground">No data source configured for this widget.</p>
      </div>
    );
  }

  const measureKey = widget.query?.measures?.[0]?.alias ?? widget.query?.measures?.[0]?.field ?? "value";
  const dimensionKey = data.columns.find((c) => c.role === "dimension")?.name ?? "";
  const valueType = widget.options.format ?? "number";
  const fv = (v: number | string | null) =>
    formatValue(v, valueType === "compact" ? "compact" : valueType, { ...fmt, compact: true });

  const chartRows = data.rows.map((r) => ({
    ...r,
    __label: String(r[dimensionKey] ?? ""),
  }));

  const color = PALETTE[(widget.options.colorIndex ?? 0) % PALETTE.length];

  const axis = {
    stroke: "var(--color-muted-foreground)",
    fontSize: 11,
    tickLine: false,
    axisLine: false,
  } as const;

  const tooltip = (
    <Tooltip
      cursor={{ fill: "color-mix(in oklab, var(--color-muted) 60%, transparent)" }}
      contentStyle={{
        background: "var(--color-popover)",
        border: "1px solid var(--color-border)",
        borderRadius: 10,
        fontSize: 12,
        color: "var(--color-popover-foreground)",
        boxShadow: "var(--shadow-soft)",
      }}
      formatter={(value: number) => fv(value)}
    />
  );

  switch (widget.type) {
    case "kpi":
      return <KpiBody widget={widget} filters={filters} onDrilldown={onDrilldown} />;

    case "table":
      return <DataTable result={data} format={valueType} compact={compact} />;

    case "line":
    case "area": {
      const Chart = widget.type === "line" ? LineChart : AreaChart;
      return (
        <ResponsiveContainer width="100%" height="100%">
          <Chart data={chartRows} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={`grad-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            {widget.options.showGrid !== false && (
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            )}
            <XAxis dataKey="__label" {...axis} minTickGap={16} />
            <YAxis {...axis} width={54} tickFormatter={(v: number) => fv(v)} />
            {tooltip}
            {widget.options.showLegend && <Legend wrapperStyle={{ fontSize: 12 }} />}
            {widget.type === "line" ? (
              <Line
          isAnimationActive={false}
                type="monotone"
                dataKey={measureKey}
                stroke={color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ) : (
              <Area
          isAnimationActive={false}
                type="monotone"
                dataKey={measureKey}
                stroke={color}
                strokeWidth={2}
                fill={`url(#grad-${widget.id})`}
              />
            )}
          </Chart>
        </ResponsiveContainer>
      );
    }

    case "bar":
      return (
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={chartRows}
            layout={widget.options.horizontal ? "vertical" : "horizontal"}
            margin={{ top: 8, right: 12, left: widget.options.horizontal ? 8 : 0, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--color-border)" />
            {widget.options.horizontal ? (
              <XAxis type="number" {...axis} tickFormatter={(v: number) => fv(v)} />
            ) : (
              <XAxis dataKey="__label" {...axis} interval={0} angle={chartRows.length > 6 ? -18 : 0} height={chartRows.length > 6 ? 46 : 28} textAnchor={chartRows.length > 6 ? "end" : "middle"} />
            )}
            {widget.options.horizontal ? (
              <YAxis type="category" dataKey="__label" {...axis} width={112} />
            ) : (
              <YAxis {...axis} width={54} tickFormatter={(v: number) => fv(v)} />
            )}
            {tooltip}
            <Bar isAnimationActive={false} dataKey={measureKey} radius={widget.options.horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0]} fill={color} maxBarSize={38} />
          </BarChart>
        </ResponsiveContainer>
      );

    case "pie":
      return (
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
          isAnimationActive={false}
              data={chartRows}
              dataKey={measureKey}
              nameKey="__label"
              innerRadius={widget.options.donut === false ? 0 : "56%"}
              outerRadius="84%"
              paddingAngle={2}
              stroke="var(--color-card)"
            >
              {chartRows.map((_, i) => (
                <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            {tooltip}
            {widget.options.showLegend !== false && (
              <Legend wrapperStyle={{ fontSize: 12 }} iconType="circle" iconSize={8} />
            )}
          </PieChart>
        </ResponsiveContainer>
      );

    case "gauge": {
      const total = chartRows.reduce((s, r) => s + (Number((r as Record<string, unknown>)[measureKey]) || 0), 0);
      const target = widget.options.target ?? total * 1.2;
      const pct = Math.min(100, Math.round((total / target) * 100));
      return (
        <div className="flex h-full flex-col items-center justify-center">
          <ResponsiveContainer width="100%" height="70%">
            <RadialBarChart
              innerRadius="70%"
              outerRadius="100%"
              data={[{ name: "progress", value: pct, fill: color }]}
              startAngle={210}
              endAngle={-30}
            >
              <RadialBar isAnimationActive={false} background={{ fill: "var(--color-muted)" }} dataKey="value" cornerRadius={8} />
            </RadialBarChart>
          </ResponsiveContainer>
          <div className="-mt-6 text-center">
            <p className="num text-2xl font-semibold tracking-tight">{pct}%</p>
            <p className="num mt-1 text-xs text-muted-foreground">
              {fv(total)} of {fv(target)}
            </p>
          </div>
        </div>
      );
    }

    case "progress": {
      const total = chartRows.reduce((s, r) => s + (Number((r as Record<string, unknown>)[measureKey]) || 0), 0);
      const target = widget.options.target ?? total * 1.3;
      const pct = Math.min(100, Math.round((total / target) * 100));
      return (
        <div className="flex h-full flex-col justify-center gap-3">
          <div className="flex items-baseline justify-between">
            <span className="num text-xl font-semibold">{fv(total)}</span>
            <span className="num text-sm text-muted-foreground">of {fv(target)}</span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
            <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
          </div>
          <p className="num text-xs text-muted-foreground">{pct}% utilised</p>
        </div>
      );
    }

    default:
      return null;
  }
}

function KpiBody({ widget, filters, onDrilldown }: Props) {
  const fmt = useFormatOpts();
  const trendQuery = widget.query
    ? { ...widget.query, grain: "month" as const, limit: 24 }
    : undefined;
  const series = useWidgetData(trendQuery, filters);
  const measureKey = widget.query?.measures?.[0]?.alias ?? widget.query?.measures?.[0]?.field ?? "value";

  const { total, change, spark } = useMemo(() => {
    const rows = series?.rows ?? [];
    const values = rows.map((r) => Number(r[measureKey]) || 0);
    const sum = values.reduce((a, b) => a + b, 0);
    let delta: number | null = null;
    if (values.length >= 2) {
      const last = values[values.length - 1];
      const prev = values[values.length - 2];
      if (prev !== 0) delta = ((last - prev) / Math.abs(prev)) * 100;
    }
    return {
      total: rows.length ? sum : 0,
      change: delta,
      spark: values.map((v, i) => ({ i, v })),
    };
  }, [series, measureKey]);

  const type = widget.options.format ?? "currency";
  const display = formatValue(total, type === "compact" ? "compact" : type, { ...fmt, compact: true });
  const positive = (change ?? 0) >= 0;

  return (
    <button
      type="button"
      onClick={() => widget.options.drilldown !== false && onDrilldown?.(widget)}
      disabled={widget.options.drilldown === false || !onDrilldown}
      className={cn(
        "flex h-full w-full flex-col justify-between gap-2 rounded-lg text-left transition",
        onDrilldown && widget.options.drilldown !== false && "hover:bg-muted/40 focus-visible:bg-muted/40",
      )}
    >
      <div>
        <p className="num text-2xl font-semibold tracking-tight sm:text-[1.7rem]">{display}</p>
        {change !== null && (
          <p
            className={cn(
              "mt-1.5 inline-flex items-center gap-1 text-xs font-medium",
              positive ? "text-positive" : "text-negative",
            )}
          >
            {change === 0 ? (
              <Minus className="size-3.5" aria-hidden />
            ) : positive ? (
              <ArrowUpRight className="size-3.5" aria-hidden />
            ) : (
              <ArrowDownRight className="size-3.5" aria-hidden />
            )}
            <span className="num">{`${positive ? "+" : ""}${change.toFixed(1)}%`}</span>
            <span className="text-muted-foreground">vs previous month</span>
          </p>
        )}
      </div>
      {widget.options.sparkline !== false && spark.length > 1 && (
        <div className="h-9 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={spark} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id={`spark-${widget.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
          isAnimationActive={false}
                type="monotone"
                dataKey="v"
                stroke="var(--color-primary)"
                strokeWidth={1.5}
                fill={`url(#spark-${widget.id})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </button>
  );
}

export function WidgetSkeleton() {
  const [shown] = useState(true);
  if (!shown) return null;
  return <div className="h-full w-full animate-pulse rounded-lg bg-muted/60" />;
}
