import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { BellRing, CalendarClock, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { EmptyState, PageHeader } from "@/components/common/states";
import { useFormatOpts, useWorkspace } from "@/lib/store";
import { formatCurrency } from "@/lib/format";
import { uid } from "@/lib/data/seed";
import type { AlertRule, ScheduledReport } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/automations")({
  head: () => ({
    meta: [
      { title: "Scheduled reports & alerts — The DASH" },
      {
        name: "description",
        content: "Send reports on a schedule and get alerted the moment a metric crosses the line you set.",
      },
      { property: "og:title", content: "Scheduled reports & alerts — The DASH" },
      { property: "og:description", content: "Automate delivery and get alerted when metrics move." },
    ],
  }),
  component: AutomationsPage,
});

const CONDITIONS: { id: AlertRule["condition"]; label: string }[] = [
  { id: "drops_below", label: "Drops below" },
  { id: "rises_above", label: "Rises above" },
  { id: "decreases_by", label: "Decreases by" },
  { id: "increases_by", label: "Increases by" },
];

const METRICS = ["Revenue", "Expenses", "Net Profit", "Receivables", "Payables", "Collections", "Units Sold"];

function AutomationsPage() {
  const { alerts, schedules, reports, upsertAlert, removeAlert, upsertSchedule, removeSchedule } = useWorkspace();
  const fmt = useFormatOpts();
  const [alertOpen, setAlertOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);

  const [draftAlert, setDraftAlert] = useState<AlertRule>({
    id: "",
    name: "",
    metric: "Revenue",
    condition: "drops_below",
    value: 10,
    unit: "percent",
    comparison: "previous_month",
    channels: ["Email", "In-app"],
    enabled: true,
  });

  const [draftSchedule, setDraftSchedule] = useState<ScheduledReport>({
    id: "",
    reportName: reports[0]?.name ?? "Monthly Financial Review",
    cadence: "monthly",
    time: "09:00",
    recipients: [],
    format: "pdf",
    enabled: true,
    nextRun: "1st of each month",
  });
  const [recipients, setRecipients] = useState("");

  return (
    <div className="pb-10">
      <PageHeader
        title="Automations"
        description="Scheduled reports and metric alerts, so the numbers find you."
      />

      <div className="px-4 py-6 sm:px-6 lg:px-8">
        <Tabs defaultValue="schedules">
          <TabsList>
            <TabsTrigger value="schedules">Scheduled reports</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
          </TabsList>

          <TabsContent value="schedules" className="mt-4 space-y-3">
            <div className="flex justify-end">
              <Button onClick={() => setScheduleOpen(true)}>
                <Plus className="size-4" aria-hidden /> New schedule
              </Button>
            </div>
            {schedules.length === 0 ? (
              <EmptyState
                icon={CalendarClock}
                title="No scheduled reports"
                description="Schedule a report and it will be generated and emailed automatically."
                action={<Button onClick={() => setScheduleOpen(true)}>Create schedule</Button>}
              />
            ) : (
              <ul className="space-y-3">
                {schedules.map((s) => (
                  <li key={s.id} className="panel flex flex-wrap items-center gap-3 p-4">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-primary-soft text-primary">
                      <CalendarClock className="size-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{s.reportName}</p>
                      <p className="text-xs text-muted-foreground">
                        <span className="capitalize">{s.cadence}</span> at {s.time} · {s.format.toUpperCase()} · next run{" "}
                        {s.nextRun}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">
                        {s.recipients.length ? `To ${s.recipients.join(", ")}` : "No recipients yet"}
                      </p>
                    </div>
                    <Switch
                      checked={s.enabled}
                      aria-label={`Enable ${s.reportName}`}
                      onCheckedChange={(v) => upsertSchedule({ ...s, enabled: v })}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${s.reportName} schedule`}
                      onClick={() => {
                        removeSchedule(s.id);
                        toast.success("Schedule deleted");
                      }}
                    >
                      <Trash2 className="size-4" aria-hidden />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-xs text-muted-foreground">
              Email delivery needs a mail sender on your workspace. Nothing is sent while the workspace is in demo mode.
            </p>
          </TabsContent>

          <TabsContent value="alerts" className="mt-4 space-y-3">
            <div className="flex justify-end">
              <Button onClick={() => setAlertOpen(true)}>
                <Plus className="size-4" aria-hidden /> New alert
              </Button>
            </div>
            {alerts.length === 0 ? (
              <EmptyState
                icon={BellRing}
                title="No alerts configured"
                description="Get notified in-app and by email when a metric crosses your threshold."
                action={<Button onClick={() => setAlertOpen(true)}>Create alert</Button>}
              />
            ) : (
              <ul className="space-y-3">
                {alerts.map((a) => (
                  <li key={a.id} className="panel flex flex-wrap items-center gap-3 p-4">
                    <span className="flex size-9 items-center justify-center rounded-lg bg-warning-soft text-warning">
                      <BellRing className="size-4" aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-semibold">{a.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {a.metric} {CONDITIONS.find((c) => c.id === a.condition)?.label.toLowerCase()}{" "}
                        <span className="num">
                          {a.unit === "percent" ? `${a.value}%` : formatCurrency(a.value, { ...fmt, compact: true })}
                        </span>{" "}
                        vs {a.comparison.replace(/_/g, " ")} · {a.channels.join(" + ")}
                      </p>
                    </div>
                    <Switch
                      checked={a.enabled}
                      aria-label={`Enable ${a.name}`}
                      onCheckedChange={(v) => upsertAlert({ ...a, enabled: v })}
                    />
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Delete ${a.name}`}
                      onClick={() => {
                        removeAlert(a.id);
                        toast.success("Alert deleted");
                      }}
                    >
                      <Trash2 className="size-4" aria-hidden />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <Dialog open={alertOpen} onOpenChange={setAlertOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New alert</DialogTitle>
            <DialogDescription>Watch a metric and get told when it moves.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="alert-name">Alert name</Label>
              <Input
                id="alert-name"
                value={draftAlert.name}
                placeholder="Revenue drop"
                onChange={(e) => setDraftAlert({ ...draftAlert, name: e.target.value })}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Metric</Label>
              <Select value={draftAlert.metric} onValueChange={(v) => setDraftAlert({ ...draftAlert, metric: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {METRICS.map((m) => (
                    <SelectItem key={m} value={m}>{m}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Condition</Label>
                <Select
                  value={draftAlert.condition}
                  onValueChange={(v) => setDraftAlert({ ...draftAlert, condition: v as AlertRule["condition"] })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CONDITIONS.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="alert-value">Value</Label>
                <Input
                  id="alert-value"
                  type="number"
                  value={draftAlert.value}
                  onChange={(e) => setDraftAlert({ ...draftAlert, value: Number(e.target.value) })}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Unit</Label>
                <Select
                  value={draftAlert.unit}
                  onValueChange={(v) => setDraftAlert({ ...draftAlert, unit: v as AlertRule["unit"] })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percent">Percent</SelectItem>
                    <SelectItem value="amount">Amount</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Compared to</Label>
                <Select
                  value={draftAlert.comparison}
                  onValueChange={(v) => setDraftAlert({ ...draftAlert, comparison: v as AlertRule["comparison"] })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="previous_month">Previous month</SelectItem>
                    <SelectItem value="previous_quarter">Previous quarter</SelectItem>
                    <SelectItem value="absolute">Absolute value</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setAlertOpen(false)}>Cancel</Button>
            <Button
              onClick={() => {
                upsertAlert({ ...draftAlert, id: uid(), name: draftAlert.name.trim() || `${draftAlert.metric} alert` });
                setAlertOpen(false);
                toast.success("Alert created");
              }}
            >
              Create alert
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={scheduleOpen} onOpenChange={setScheduleOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>New scheduled report</DialogTitle>
            <DialogDescription>Pick a report, a cadence and who receives it.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Report</Label>
              <Select
                value={draftSchedule.reportName}
                onValueChange={(v) => setDraftSchedule({ ...draftSchedule, reportName: v })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {reports.map((r) => (
                    <SelectItem key={r.id} value={r.name}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Cadence</Label>
                <Select
                  value={draftSchedule.cadence}
                  onValueChange={(v) => setDraftSchedule({ ...draftSchedule, cadence: v as ScheduledReport["cadence"] })}
                >
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["daily", "weekly", "monthly", "quarterly"].map((c) => (
                      <SelectItem key={c} value={c} className="capitalize">{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="sched-time">Time</Label>
                <Input
                  id="sched-time"
                  type="time"
                  value={draftSchedule.time}
                  onChange={(e) => setDraftSchedule({ ...draftSchedule, time: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sched-to">Recipients</Label>
              <Input
                id="sched-to"
                value={recipients}
                placeholder="finance@acme.in, rahul@acme.in"
                onChange={(e) => setRecipients(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label>Format</Label>
              <Select
                value={draftSchedule.format}
                onValueChange={(v) => setDraftSchedule({ ...draftSchedule, format: v as ScheduledReport["format"] })}
              >
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="pdf">PDF</SelectItem>
                  <SelectItem value="csv">CSV</SelectItem>
                  <SelectItem value="excel">Excel</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setScheduleOpen(false)}>Cancel</Button>
            <Button
              onClick={() => {
                upsertSchedule({
                  ...draftSchedule,
                  id: uid(),
                  recipients: recipients.split(",").map((r) => r.trim()).filter(Boolean),
                  nextRun: `Next ${draftSchedule.cadence} run at ${draftSchedule.time}`,
                });
                setScheduleOpen(false);
                setRecipients("");
                toast.success("Schedule created");
              }}
            >
              Create schedule
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
