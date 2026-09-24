import { useMemo, useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { BarChart3, Compass, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { PageHeader, DemoBadge } from "@/components/common/states";
import { DataTable } from "@/components/widgets/DataTable";
import { WidgetView } from "@/components/widgets/WidgetView";
import { listDatasets, runQuery } from "@/lib/query/engine";
import { DATE_FIELD_BY_DATASET } from "@/lib/data/demo-source";
import { useWorkspace } from "@/lib/store";
import { useLiveData } from "@/lib/live-data";
import { uid } from "@/lib/data/seed";
import type { Aggregation, DateGrain, Widget, WidgetType } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/explorer")({
  head: () => ({
    meta: [
      { title: "Data Explorer — The DASH" },
      {
        name: "description",
        content: "Pick a dataset, choose dimensions and measures, and turn any question into a dashboard widget.",
      },
      { property: "og:title", content: "Data Explorer — The DASH" },
      { property: "og:description", content: "Build queries visually and push them onto a dashboard." },
    ],
  }),
  component: ExplorerPage,
});

const CHART_TYPES: WidgetType[] = ["bar", "line", "area", "pie", "table", "kpi"];
const AGGS: Aggregation[] = ["sum", "avg", "min", "max", "count"];

function ExplorerPage() {
  const { version: liveVersion } = useLiveData();
  const datasets = useMemo(() => listDatasets(), [liveVersion]);
  const { dashboards, addWidget } = useWorkspace();

  const [datasetId, setDatasetId] = useState(datasets[0].id);
  const [dimension, setDimension] = useState<string>("__time");
  const [grain, setGrain] = useState<DateGrain>("month");
  const [measureField, setMeasureField] = useState<string>("");
  const [aggregation, setAggregation] = useState<Aggregation>("sum");
  const [limit, setLimit] = useState(12);
  const [chart, setChart] = useState<WidgetType>("bar");
  const [addOpen, setAddOpen] = useState(false);
  const [target, setTarget] = useState(dashboards[0]?.id ?? "");
  const [widgetTitle, setWidgetTitle] = useState("");

  const dataset = datasets.find((d) => d.id === datasetId)!;
  const measures = dataset.fields.filter((f) => f.role === "measure");
  const dimensions = dataset.fields.filter((f) => f.role === "dimension" && f.type !== "date");
  const dateField = DATE_FIELD_BY_DATASET[dataset.id];
  const field = measureField && measures.some((m) => m.name === measureField) ? measureField : measures[0]?.name;

  const query = useMemo(
    () => ({
      sourceId: "tally",
      dataset: dataset.id,
      groupBy: dimension === "__time" ? [] : [dimension],
      grain: dimension === "__time" ? grain : undefined,
      dateField: dimension === "__time" ? dateField : undefined,
      measures: field ? [{ field, aggregation }] : [],
      limit,
    }),
    [dataset.id, dimension, grain, dateField, field, aggregation, limit],
  );

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const result = useMemo(() => runQuery(query), [query, liveVersion]);

  const previewWidget: Widget = {
    id: "explorer-preview",
    type: chart,
    title: widgetTitle || `${measures.find((m) => m.name === field)?.label ?? "Value"} by ${
      dimension === "__time" ? grain : dimensions.find((d) => d.name === dimension)?.label ?? dimension
    }`,
    options: { format: "currency", showGrid: true, showLegend: chart === "pie", donut: true, colorIndex: 0, drilldown: true },
    layout: { w: 6, h: 4 },
    query,
  };

  return (
    <div className="pb-10">
      <PageHeader
        title="Data Explorer"
        description="Build a query visually across any connected dataset, then save it as a widget."
        actions={
          <>
            <DemoBadge className="mr-1" />
            <Button onClick={() => setAddOpen(true)} disabled={!dashboards.length}>
              <Plus className="size-4" aria-hidden /> Add to dashboard
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 px-4 py-6 sm:px-6 lg:grid-cols-12 lg:px-8">
        <aside className="panel space-y-4 p-4 lg:col-span-3" aria-label="Query builder">
          <h2 className="flex items-center gap-2 text-sm font-semibold">
            <Compass className="size-4 text-primary" aria-hidden /> Query
          </h2>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Dataset</Label>
            <Select
              value={datasetId}
              onValueChange={(v) => {
                setDatasetId(v);
                setDimension(DATE_FIELD_BY_DATASET[v] ? "__time" : "");
                setMeasureField("");
              }}
            >
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Dimension</Label>
            <Select value={dimension || dimensions[0]?.name} onValueChange={setDimension}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {dateField && <SelectItem value="__time">Time period</SelectItem>}
                {dimensions.map((d) => (
                  <SelectItem key={d.name} value={d.name}>{d.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {dimension === "__time" && (
            <div className="space-y-1.5">
              <Label className="text-xs text-muted-foreground">Period</Label>
              <Select value={grain} onValueChange={(v) => setGrain(v as DateGrain)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {(["day", "week", "month", "quarter", "year"] as DateGrain[]).map((g) => (
                    <SelectItem key={g} value={g} className="capitalize">{g}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Measure</Label>
            <Select value={field} onValueChange={setMeasureField}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {measures.map((m) => (
                  <SelectItem key={m.name} value={m.name}>{m.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Aggregation</Label>
            <Select value={aggregation} onValueChange={(v) => setAggregation(v as Aggregation)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                {AGGS.map((a) => (
                  <SelectItem key={a} value={a} className="capitalize">{a}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground" htmlFor="limit">Row limit</Label>
            <Input
              id="limit"
              type="number"
              min={1}
              max={200}
              value={limit}
              onChange={(e) => setLimit(Math.max(1, Number(e.target.value) || 12))}
            />
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Visualisation</Label>
            <div className="flex flex-wrap gap-1.5">
              {CHART_TYPES.map((t) => (
                <Button
                  key={t}
                  size="sm"
                  variant={chart === t ? "default" : "outline"}
                  className="capitalize"
                  onClick={() => setChart(t)}
                >
                  {t}
                </Button>
              ))}
            </div>
          </div>
        </aside>

        <div className="space-y-4 lg:col-span-9">
          <div className="panel h-[22rem] p-4">
            <div className="mb-3 flex items-center gap-2">
              <BarChart3 className="size-4 text-primary" aria-hidden />
              <h2 className="truncate text-sm font-semibold">{previewWidget.title}</h2>
            </div>
            <div className="h-[17rem]">
              <WidgetView widget={previewWidget} />
            </div>
          </div>

          <div className="panel p-4">
            <h2 className="mb-3 text-sm font-semibold">Results</h2>
            <DataTable result={result} title="explorer-results" />
          </div>
        </div>
      </div>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Add to dashboard</DialogTitle>
            <DialogDescription>This query becomes a live widget on the dashboard you choose.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="widget-title">Widget title</Label>
              <Input
                id="widget-title"
                value={widgetTitle}
                placeholder={previewWidget.title}
                onChange={(e) => setWidgetTitle(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Dashboard</Label>
              <Select value={target} onValueChange={setTarget}>
                <SelectTrigger><SelectValue placeholder="Choose a dashboard" /></SelectTrigger>
                <SelectContent>
                  {dashboards.map((d) => (
                    <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button
              disabled={!target}
              onClick={() => {
                addWidget(target, { ...previewWidget, id: uid(), title: widgetTitle || previewWidget.title });
                setAddOpen(false);
                toast.success("Widget added to dashboard");
              }}
            >
              Add widget
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
