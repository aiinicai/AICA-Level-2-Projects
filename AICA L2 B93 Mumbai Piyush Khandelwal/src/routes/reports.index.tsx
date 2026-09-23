import { createFileRoute, Link } from "@tanstack/react-router";
import { FileText, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState, PageHeader } from "@/components/common/states";
import { useWorkspace } from "@/lib/store";
import { relativeTime } from "@/lib/format";
import { uid } from "@/lib/data/seed";
import { toast } from "sonner";

export const Route = createFileRoute("/reports/")({
  head: () => ({
    meta: [
      { title: "Reports — The DASH" },
      { name: "description", content: "Board-ready financial and sales reports with KPIs, charts, tables and commentary." },
      { property: "og:title", content: "Reports — The DASH" },
      { property: "og:description", content: "Board-ready reports you can export to PDF, CSV or Excel." },
    ],
  }),
  component: ReportsPage,
});

function ReportsPage() {
  const { reports, upsertReport, hydrated } = useWorkspace();

  const create = () => {
    const id = uid();
    upsertReport({
      id,
      name: "Untitled report",
      period: "This month",
      updatedAt: new Date().toISOString(),
      sections: [
        { id: uid(), kind: "summary", title: "Executive summary", body: "Add your commentary here." },
        { id: uid(), kind: "kpis", title: "Headline metrics" },
        { id: uid(), kind: "chart", title: "Revenue trend" },
      ],
    });
    toast.success("Report created");
  };

  return (
    <div className="pb-10">
      <PageHeader
        title="Reports"
        description="Turn a period of data into something you can send to a board or a bank."
        actions={
          <>
            <Button variant="outline" asChild>
              <Link to="/automations">Scheduled reports</Link>
            </Button>
            <Button onClick={create}>
              <Plus className="size-4" aria-hidden /> New report
            </Button>
          </>
        }
      />

      <div className="px-4 py-6 sm:px-6 lg:px-8">
        {reports.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports yet"
            description="Create a report to combine KPIs, charts, tables and written commentary in one document."
            action={<Button onClick={create}>Create report</Button>}
          />
        ) : (
          <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {reports.map((r) => (
              <li key={r.id}>
                <Link
                  to="/reports/$reportId"
                  params={{ reportId: r.id }}
                  className="panel flex h-full flex-col p-4 transition hover:border-border-strong hover:shadow-soft"
                >
                  <span className="flex size-9 items-center justify-center rounded-lg bg-primary-soft text-primary">
                    <FileText className="size-4" aria-hidden />
                  </span>
                  <h2 className="mt-3 truncate text-sm font-semibold">{r.name}</h2>
                  <p className="text-xs text-muted-foreground">{r.period}</p>
                  <p className="mt-3 text-xs text-muted-foreground">
                    {r.sections.length} sections{hydrated ? ` · updated ${relativeTime(r.updatedAt)}` : ""}
                  </p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
