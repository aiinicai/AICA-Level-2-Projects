import { useState } from "react";
import { Sheet, SheetContent, SheetDescription, SheetFooter, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { listDatasets } from "@/lib/query/engine";
import { DATE_FIELD_BY_DATASET } from "@/lib/data/demo-source";
import type { Aggregation, DateGrain, Widget, WidgetType } from "@/lib/types";
import { WidgetView } from "@/components/widgets/WidgetView";

const TYPES: { id: WidgetType; label: string }[] = [
  { id: "kpi", label: "KPI card" },
  { id: "line", label: "Line chart" },
  { id: "bar", label: "Bar chart" },
  { id: "area", label: "Area chart" },
  { id: "pie", label: "Pie / donut" },
  { id: "table", label: "Table" },
  { id: "gauge", label: "Gauge" },
  { id: "progress", label: "Progress bar" },
  { id: "text", label: "Text / notes" },
];

const AGGREGATIONS: Aggregation[] = ["sum", "avg", "min", "max", "count"];
const GRAINS: DateGrain[] = ["day", "week", "month", "quarter", "year"];

export function WidgetConfigPanel({
  widget,
  open,
  onOpenChange,
  onSave,
  title = "Configure widget",
}: {
  widget: Widget;
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onSave: (w: Widget) => void;
  title?: string;
}) {
  const [draft, setDraft] = useState<Widget>(widget);
  const datasets = listDatasets();
  const dataset = datasets.find((d) => d.id === draft.query?.dataset) ?? datasets[0];
  const measures = dataset.fields.filter((f) => f.role === "measure");
  const dimensions = dataset.fields.filter((f) => f.role === "dimension" && f.type !== "date");

  const set = (patch: Partial<Widget>) => setDraft((d) => ({ ...d, ...patch }));
  const setQuery = (patch: Partial<NonNullable<Widget["query"]>>) =>
    setDraft((d) => ({
      ...d,
      query: {
        sourceId: d.query?.sourceId ?? "tally",
        dataset: d.query?.dataset ?? dataset.id,
        ...d.query,
        ...patch,
      },
    }));
  const setOptions = (patch: Partial<Widget["options"]>) => setDraft((d) => ({ ...d, options: { ...d.options, ...patch } }));

  const isChart = ["line", "bar", "area", "pie"].includes(draft.type);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex w-full flex-col gap-0 overflow-y-auto sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{title}</SheetTitle>
          <SheetDescription>Data, visualisation, formatting and behaviour.</SheetDescription>
        </SheetHeader>

        <div className="flex-1 space-y-4 px-4 pb-4">
          <div className="panel h-52 p-3">
            <p className="mb-2 truncate text-xs font-medium text-muted-foreground">Preview</p>
            <div className="h-36">
              <WidgetView widget={draft} />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="w-title">Title</Label>
            <Input id="w-title" value={draft.title} onChange={(e) => set({ title: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="w-subtitle">Subtitle</Label>
            <Input
              id="w-subtitle"
              value={draft.subtitle ?? ""}
              placeholder="Optional"
              onChange={(e) => set({ subtitle: e.target.value })}
            />
          </div>

          <Accordion type="multiple" defaultValue={["data", "viz"]}>
            <AccordionItem value="data">
              <AccordionTrigger>Data</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <Field label="Widget type">
                  <Select value={draft.type} onValueChange={(v) => set({ type: v as WidgetType })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {TYPES.map((t) => (
                        <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>

                {draft.type === "text" ? (
                  <Field label="Body (markdown-ish)">
                    <Textarea
                      rows={5}
                      value={draft.options.body ?? ""}
                      onChange={(e) => setOptions({ body: e.target.value })}
                      placeholder={"## Heading\nYour commentary here."}
                    />
                  </Field>
                ) : (
                  <>
                    <Field label="Dataset">
                      <Select
                        value={dataset.id}
                        onValueChange={(v) =>
                          setQuery({
                            dataset: v,
                            groupBy: [],
                            measures: [],
                            dateField: DATE_FIELD_BY_DATASET[v],
                          })
                        }
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {datasets.map((d) => (
                            <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>

                    <Field label="Measure">
                      <Select
                        value={draft.query?.measures?.[0]?.field ?? measures[0]?.name}
                        onValueChange={(v) =>
                          setQuery({
                            measures: [{ field: v, aggregation: draft.query?.measures?.[0]?.aggregation ?? "sum" }],
                          })
                        }
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {measures.map((m) => (
                            <SelectItem key={m.name} value={m.name}>{m.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>

                    <Field label="Aggregation">
                      <Select
                        value={draft.query?.measures?.[0]?.aggregation ?? "sum"}
                        onValueChange={(v) =>
                          setQuery({
                            measures: [
                              {
                                field: draft.query?.measures?.[0]?.field ?? measures[0].name,
                                aggregation: v as Aggregation,
                              },
                            ],
                          })
                        }
                      >
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {AGGREGATIONS.map((a) => (
                            <SelectItem key={a} value={a} className="capitalize">{a}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </Field>

                    {isChart && (
                      <Field label="Group by">
                        <Select
                          value={draft.query?.grain ? "__time" : (draft.query?.groupBy?.[0] ?? "__time")}
                          onValueChange={(v) =>
                            v === "__time"
                              ? setQuery({ groupBy: [], grain: "month", dateField: DATE_FIELD_BY_DATASET[dataset.id] })
                              : setQuery({ groupBy: [v], grain: undefined })
                          }
                        >
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {DATE_FIELD_BY_DATASET[dataset.id] && <SelectItem value="__time">Time period</SelectItem>}
                            {dimensions.map((d) => (
                              <SelectItem key={d.name} value={d.name}>{d.label}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                    )}

                    {draft.query?.grain && (
                      <Field label="Date aggregation">
                        <Select value={draft.query.grain} onValueChange={(v) => setQuery({ grain: v as DateGrain })}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            {GRAINS.map((g) => (
                              <SelectItem key={g} value={g} className="capitalize">{g}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </Field>
                    )}

                    <Field label="Row limit">
                      <Input
                        type="number"
                        min={1}
                        value={draft.query?.limit ?? 12}
                        onChange={(e) => setQuery({ limit: Number(e.target.value) || 12 })}
                      />
                    </Field>
                  </>
                )}
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="viz">
              <AccordionTrigger>Visualisation</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <Field label="Colour">
                  <Select
                    value={String(draft.options.colorIndex ?? 0)}
                    onValueChange={(v) => setOptions({ colorIndex: Number(v) })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {["Indigo", "Teal", "Green", "Amber", "Red", "Violet"].map((c, i) => (
                        <SelectItem key={c} value={String(i)}>{c}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Toggle label="Show legend" checked={draft.options.showLegend ?? false} onChange={(v) => setOptions({ showLegend: v })} />
                <Toggle label="Show grid lines" checked={draft.options.showGrid ?? true} onChange={(v) => setOptions({ showGrid: v })} />
                {draft.type === "bar" && (
                  <Toggle label="Horizontal bars" checked={draft.options.horizontal ?? false} onChange={(v) => setOptions({ horizontal: v })} />
                )}
                {draft.type === "pie" && (
                  <Toggle label="Donut" checked={draft.options.donut ?? true} onChange={(v) => setOptions({ donut: v })} />
                )}
                {draft.type === "kpi" && (
                  <Toggle label="Sparkline" checked={draft.options.sparkline ?? true} onChange={(v) => setOptions({ sparkline: v })} />
                )}
                {(draft.type === "gauge" || draft.type === "progress") && (
                  <Field label="Target value">
                    <Input
                      type="number"
                      value={draft.options.target ?? 0}
                      onChange={(e) => setOptions({ target: Number(e.target.value) })}
                    />
                  </Field>
                )}
                <Field label="Width (of 12 columns)">
                  <Select value={String(draft.layout.w)} onValueChange={(v) => set({ layout: { ...draft.layout, w: Number(v) } })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {[3, 4, 6, 8, 12].map((w) => (
                        <SelectItem key={w} value={String(w)}>{w} / 12</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Height">
                  <Select value={String(draft.layout.h)} onValueChange={(v) => set({ layout: { ...draft.layout, h: Number(v) } })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {[2, 3, 4, 5, 6].map((h) => (
                        <SelectItem key={h} value={String(h)}>{h} rows</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="format">
              <AccordionTrigger>Formatting</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <Field label="Value format">
                  <Select
                    value={draft.options.format ?? "currency"}
                    onValueChange={(v) => setOptions({ format: v as Widget["options"]["format"] })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="currency">Currency</SelectItem>
                      <SelectItem value="number">Number</SelectItem>
                      <SelectItem value="compact">Compact (L / Cr)</SelectItem>
                      <SelectItem value="percent">Percentage</SelectItem>
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="Decimals">
                  <Input
                    type="number"
                    min={0}
                    max={4}
                    value={draft.options.decimals ?? 1}
                    onChange={(e) => setOptions({ decimals: Number(e.target.value) })}
                  />
                </Field>
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="behaviour">
              <AccordionTrigger>Behaviour</AccordionTrigger>
              <AccordionContent className="space-y-3">
                <Toggle
                  label="Allow drill-down to records"
                  checked={draft.options.drilldown ?? true}
                  onChange={(v) => setOptions({ drilldown: v })}
                />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>

        <SheetFooter className="border-t">
          <Button
            onClick={() => {
              onSave(draft);
              onOpenChange(false);
            }}
          >
            Save widget
          </Button>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <Label className="text-sm font-normal">{label}</Label>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}
