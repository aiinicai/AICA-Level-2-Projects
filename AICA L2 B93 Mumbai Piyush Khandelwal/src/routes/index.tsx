import { useEffect, useMemo, useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Compass,
  LayoutDashboard,
  Plug,
  RefreshCw,
  Sparkles,
} from "lucide-react";
import { Area, AreaChart, ResponsiveContainer } from "recharts";
import { Button } from "@/components/ui/button";
import { PageHeader, DemoBadge } from "@/components/common/states";
import { headlineMetrics } from "@/lib/metrics";
import { formatValue, relativeTime } from "@/lib/format";
import { useFormatOpts, useWorkspace } from "@/lib/store";
import { useLiveData } from "@/lib/live-data";
import { integrationById } from "@/lib/integrations/catalog";
import { WidgetView } from "@/components/widgets/WidgetView";
import { StatusPill } from "@/components/widgets/DataTable";
import { cn } from "@/lib/utils";
import type { Widget } from "@/lib/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Workspace home — The DASH" },
      {
        name: "description",
        content:
          "Your business at a glance: revenue, expenses, profit, receivables and sync health across every connected system.",
      },
      { property: "og:title", content: "Workspace home — The DASH" },
      {
        property: "og:description",
        content: "Revenue, expenses, profit and receivables across every connected business system.",
      },
    ],
  }),
  component: HomePage,
});

const TREND_WIDGET: Widget = {
  id: "home-revenue",
  type: "area",
  title: "Revenue trend",
  options: { format: "currency", showGrid: true, colorIndex: 0 },
  layout: { w: 8, h: 4 },
  query: {
    sourceId: "tally",
    dataset: "sales_invoices",
    grain: "month",
    dateField: "invoice_date",
    measures: [{ field: "invoice_amount", aggregation: "sum" }],
  },
};

const MIX_WIDGET: Widget = {
  id: "home-mix",
  type: "pie",
  title: "Revenue by region",
  options: { donut: true, format: "currency", showLegend: true },
  layout: { w: 4, h: 4 },
  query: {
    sourceId: "tally",
    dataset: "sales_invoices",
    groupBy: ["region"],
    measures: [{ field: "invoice_amount", aggregation: "sum" }],
  },
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function HomePage() {
  const fmt = useFormatOpts();
  const { dashboards, connections, hydrated } = useWorkspace();
  const [hello, setHello] = useState("Welcome back");
  useEffect(() => setHello(greeting()), []);
  const { version } = useLiveData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const metrics = useMemo(() => headlineMetrics(), [version]);

  return (
    <div className="pb-10">
      <PageHeader
        title={`${hello}, Rahul`}
        description="Here's what's happening across your business today."
        actions={
          <>
            <DemoBadge className="mr-1" />
            <Button variant="outline" asChild>
              <Link to="/explorer">
                <Compass className="size-4" aria-hidden /> Explore data
              </Link>
            </Button>
            <Button asChild>
              <Link to="/dashboards">
                <LayoutDashboard className="size-4" aria-hidden /> Dashboards
              </Link>
            </Button>
          </>
        }
      />

      <div className="space-y-6 px-4 py-6 sm:px-6 lg:px-8">
        <section aria-label="Headline metrics" className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          {metrics.map((m) => {
            const positive = (m.change ?? 0) >= 0;
            return (
              <article key={m.id} className="panel p-4">
                <p className="text-xs font-medium text-muted-foreground">{m.label}</p>
                <p className="num mt-1.5 text-xl font-semibold tracking-tight sm:text-2xl">
                  {formatValue(m.value, m.format, { ...fmt, compact: true })}
                </p>
                {m.change !== null ? (
                  <p
                    className={cn(
                      "mt-1 inline-flex items-center gap-1 text-xs font-medium",
                      positive ? "text-positive" : "text-negative",
                    )}
                  >
                    {positive ? <ArrowUpRight className="size-3.5" aria-hidden /> : <ArrowDownRight className="size-3.5" aria-hidden />}
                    <span className="num">{`${positive ? "+" : ""}${m.change.toFixed(1)}%`}</span>
                    <span className="hidden text-muted-foreground sm:inline">vs previous month</span>
                  </p>
                ) : (
                  <p className="mt-1 text-xs text-muted-foreground">Current position</p>
                )}
                {m.series.length > 1 && (
                  <div className="mt-2 h-8">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={m.series}>
                        <defs>
                          <linearGradient id={`home-${m.id}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.28} />
                            <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <Area type="monotone" dataKey="v" stroke="var(--color-primary)" strokeWidth={1.5} fill={`url(#home-${m.id})`} />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </article>
            );
          })}
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-12">
          <div className="panel h-[19rem] p-4 xl:col-span-8">
            <h2 className="mb-3 text-sm font-semibold">Revenue trend</h2>
            <div className="h-[15rem]">
              <WidgetView widget={TREND_WIDGET} />
            </div>
          </div>
          <div className="panel h-[19rem] p-4 xl:col-span-4">
            <h2 className="mb-3 text-sm font-semibold">Revenue by region</h2>
            <div className="h-[15rem]">
              <WidgetView widget={MIX_WIDGET} />
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="panel p-4 lg:col-span-2">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Your dashboards</h2>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/dashboards">
                  View all <ArrowRight className="size-3.5" aria-hidden />
                </Link>
              </Button>
            </div>
            <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
              {dashboards.slice(0, 4).map((d) => (
                <li key={d.id}>
                  <Link
                    to="/dashboards/$dashboardId"
                    params={{ dashboardId: d.id }}
                    className="block rounded-lg border bg-surface p-3 transition hover:border-border-strong"
                  >
                    <p className="truncate text-sm font-medium">{d.name}</p>
                    <p className="mt-0.5 truncate text-xs text-muted-foreground">
                      {d.widgets.length} widgets{hydrated ? ` · updated ${relativeTime(d.updatedAt)}` : ""}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div className="panel p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold">Sync health</h2>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/data-sources">
                  <RefreshCw className="size-3.5" aria-hidden /> Manage
                </Link>
              </Button>
            </div>
            <ul className="space-y-2">
              {connections.map((c) => (
                <li key={c.id} className="flex items-center justify-between gap-2 rounded-lg border bg-surface p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">{integrationById(c.providerId)?.name ?? c.providerId}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {hydrated && c.lastSync ? `Last sync ${relativeTime(c.lastSync)}` : "Sync status"}
                    </p>
                  </div>
                  <StatusPill value={c.status === "connected" ? "Healthy" : c.status === "error" ? "Failed" : "Pending"} />
                </li>
              ))}
              {connections.length === 0 && (
                <li className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">
                  No data sources connected yet.
                  <Button variant="link" size="sm" asChild>
                    <Link to="/integrations">
                      <Plug className="size-3.5" aria-hidden /> Connect one
                    </Link>
                  </Button>
                </li>
              )}
            </ul>
          </div>
        </section>

        <section className="panel flex flex-wrap items-center justify-between gap-3 p-4">
          <div className="flex items-start gap-3">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
              <Sparkles className="size-4" aria-hidden />
            </span>
            <div>
              <h2 className="text-sm font-semibold">Build a dashboard from a question</h2>
              <p className="text-xs text-muted-foreground">
                Start in Data Explorer, shape the query visually, then push it straight onto a dashboard.
              </p>
            </div>
          </div>
          <Button variant="outline" asChild>
            <Link to="/explorer">Open Data Explorer</Link>
          </Button>
        </section>
      </div>
    </div>
  );
}
