import { useMemo } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { ChevronRight, Download, FileText, Printer, Share2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { DemoBadge, EmptyState, PageHeader } from "@/components/common/states";
import { WidgetView } from "@/components/widgets/WidgetView";
import { DataTable } from "@/components/widgets/DataTable";
import { useFormatOpts, useWorkspace } from "@/lib/store";
import { headlineMetrics } from "@/lib/metrics";
import { formatValue, prettyDate } from "@/lib/format";
import { runQuery } from "@/lib/query/engine";
import { useLiveData } from "@/lib/live-data";
import type { Widget } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/reports/$reportId")({
  head: () => ({
    meta: [
      { title: "Report — The DASH" },
      { name: "description", content: "A shareable report with KPIs, charts, tables and commentary, ready to export." },
      { property: "og:title", content: "Report — The DASH" },
      { property: "og:description", content: "KPIs, charts, tables and commentary, ready to export." },
    ],
  }),
  component: ReportDetail,
});

const CHART: Widget = {
  id: "report-chart",
  type: "line",
  title: "Revenue trend",
  options: { format: "currency", showGrid: true },
  layout: { w: 12, h: 4 },
  query: {
    sourceId: "tally",
    dataset: "sales_invoices",
    grain: "month",
    dateField: "invoice_date",
    measures: [{ field: "invoice_amount", aggregation: "sum" }],
    limit: 12,
  },
};

function ReportDetail() {
  const { reportId } = Route.useParams();
  const { reports, upsertReport, hydrated } = useWorkspace();
  const fmt = useFormatOpts();
  const report = reports.find((r) => r.id === reportId);

  const { version: liveVersion } = useLiveData();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const metrics = useMemo(() => headlineMetrics().slice(0, 4), [liveVersion]);
  const table = useMemo(
    () =>
      runQuery({
        sourceId: "tally",
        dataset: "sales_invoices",
        groupBy: ["customer"],
        measures: [
          { field: "invoice_amount", aggregation: "sum" },
          { field: "profit", aggregation: "sum" },
        ],
        sort: [{ field: "invoice_amount", dir: "desc" }],
        limit: 10,
      }),
    [liveVersion],
  );

  if (!report) {
    return (
      <div className="p-6">
        <EmptyState
          icon={FileText}
          title="Report not found"
          description="This report may have been deleted."
          action={
            <Button asChild>
              <Link to="/reports">Back to reports</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const exportCsv = () => {
    const rows = [["Metric", "Value"], ...metrics.map((m) => [m.label, String(Math.round(m.value))])];
    const blob = new Blob([rows.map((r) => r.join(",")).join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.name.replace(/\s+/g, "-").toLowerCase()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("CSV downloaded");
  };

  return (
    <div className="pb-14">
      <PageHeader
        breadcrumb={
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
            <Link to="/reports" className="hover:text-foreground">Reports</Link>
            <ChevronRight className="size-3" aria-hidden />
            <span className="text-foreground">{report.name}</span>
          </nav>
        }
        title={report.name}
        description={`Reporting period: ${report.period}`}
        actions={
          <>
            <DemoBadge className="mr-1" />
            <Button variant="outline" onClick={exportCsv}>
              <Download className="size-4" aria-hidden /> CSV
            </Button>
            <Button variant="outline" onClick={() => window.print()}>
              <Printer className="size-4" aria-hidden /> Print / PDF
            </Button>
            <Button
              variant="outline"
              onClick={() => {
                navigator.clipboard
                  ?.writeText(window.location.href)
                  .then(() => toast.success("Share link copied"))
                  .catch(() => toast.error("Couldn't copy the link"));
              }}
            >
              <Share2 className="size-4" aria-hidden /> Share
            </Button>
          </>
        }
      />

      <div className="mx-auto max-w-4xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
        <header className="panel flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Acme Industries Pvt Ltd</p>
            <h2 className="text-lg font-semibold">{report.name}</h2>
            <p className="text-xs text-muted-foreground">{hydrated ? `Generated ${prettyDate(new Date())}` : "Generated report"}</p>
          </div>
          <span className="flex size-11 items-center justify-center rounded-xl bg-primary text-sm font-semibold text-primary-foreground">
            AI
          </span>
        </header>

        {report.sections.map((section) => (
          <section key={section.id} className="panel space-y-3 p-5">
            <h3 className="text-sm font-semibold">{section.title}</h3>

            {(section.kind === "summary" || section.kind === "commentary") && (
              <Textarea
                rows={4}
                defaultValue={section.body ?? ""}
                aria-label={section.title}
                onBlur={(e) =>
                  upsertReport({
                    ...report,
                    updatedAt: new Date().toISOString(),
                    sections: report.sections.map((s) =>
                      s.id === section.id ? { ...s, body: e.target.value } : s,
                    ),
                  })
                }
              />
            )}

            {section.kind === "kpis" && (
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {metrics.map((m) => (
                  <div key={m.id} className="rounded-lg border bg-surface p-3">
                    <p className="text-xs text-muted-foreground">{m.label}</p>
                    <p className="num mt-1 text-lg font-semibold">
                      {formatValue(m.value, m.format, { ...fmt, compact: true })}
                    </p>
                  </div>
                ))}
              </div>
            )}

            {section.kind === "chart" && (
              <div className="h-64">
                <WidgetView widget={CHART} />
              </div>
            )}

            {section.kind === "table" && <DataTable result={table} pageSize={5} title={report.name} />}
          </section>
        ))}
      </div>
    </div>
  );
}
