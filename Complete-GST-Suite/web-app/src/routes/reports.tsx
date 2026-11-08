import { createFileRoute, Link } from "@tanstack/react-router";
import { FileSpreadsheet, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, StatusBadge } from "@/components/gst/common";
import { DataTable } from "@/components/gst/DataTable";
import { fmtDateTime } from "@/lib/gst/format";
import { downloadTemplate, exportClientWorkbook, exportFirmWorkbook } from "@/lib/exports";
import { latestRun, useApp, useClients } from "@/lib/store";

export const Route = createFileRoute("/reports")({
  head: () => ({
    meta: [
      { title: "Reports — Complete GST Suite" },
      { name: "description", content: "Formatted Excel workbooks with live formulas, PDF summaries and templates for each client and the firm." },
      { property: "og:title", content: "Reports — Complete GST Suite" },
      { property: "og:description", content: "Excel workbooks, PDF summaries and templates." },
    ],
  }),
  component: ReportsPage,
});

const SHEETS = "Dashboard, Sales 3-Way, ITC 3-Way, R1–R6 (live difference formulas), Inv Match – Sales, Inv Match – ITC, Supplier Follow-up, GSTR-9, GSTR-9C, Notices";

function ReportsPage() {
  const clients = useClients();
  const runs = useApp((s) => s.runs);
  return (
    <div className="space-y-6">
      <PageHeader title="Reports" subtitle="Working papers for review or for the client file. Workbooks open in Excel with navy headers, red/green formatting, Indian number format, frozen panes, filters and A4 landscape print setup." />
      <Panel title="Client workbooks & PDF summaries">
        <p className="mb-3 text-xs text-muted-foreground">Sheets: {SHEETS}.</p>
        <DataTable
          rows={clients}
          rowKey={(c) => c.id}
          exportName="clients_reports"
          empty={{ message: "No clients yet.", action: <Button asChild size="sm"><Link to="/">Load the demo firm</Link></Button> }}
          columns={[
            { key: "name", title: "Client", header: "Client", value: (c) => c.name, cell: (c) => <span className="font-medium">{c.name}<div className="font-mono text-[11px] text-muted-foreground">{c.gstin}</div></span> },
            { key: "last", title: "Last run", header: "Last run", value: (c) => latestRun(runs, c.id)?.at ?? "", cell: (c) => { const r = latestRun(runs, c.id); return r ? <span className="text-xs">{fmtDateTime(r.at)} <StatusBadge status={r.status} /></span> : <span className="text-xs text-muted-foreground">Not run — figures are calculated fresh</span>; } },
            { key: "x", title: "", header: "Download", value: () => "", noExport: true, cell: (c) => (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => void exportClientWorkbook(c.id)}><FileSpreadsheet className="mr-1.5 h-3.5 w-3.5" /> Excel workbook</Button>
                <Button size="sm" variant="outline" asChild><Link to="/print/$clientId" params={{ clientId: c.id }} target="_blank"><FileText className="mr-1.5 h-3.5 w-3.5" /> PDF summary</Link></Button>
              </div>
            ) },
          ]}
        />
      </Panel>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Firm dashboard workbook">
          <p className="mb-3 text-sm text-muted-foreground">All your clients in one workbook: R1–R6 year differences, ITC at risk, DRC-03, notice counts, plus every notice.</p>
          <Button onClick={() => void exportFirmWorkbook()} disabled={!clients.length}><FileSpreadsheet className="mr-2 h-4 w-4" /> Download firm workbook</Button>
        </Panel>
        <Panel title="Templates">
          <p className="mb-3 text-sm text-muted-foreground">Fill these in Excel and upload them: client master (Clients › Import), GSTR-3B 12-month summary (Connect &amp; Data), manual notices (Notices › Upload).</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" onClick={() => void downloadTemplate("client-master")}>Client master</Button>
            <Button variant="outline" onClick={() => void downloadTemplate("gstr3b-summary")}>GSTR-3B summary</Button>
            <Button variant="outline" onClick={() => void downloadTemplate("notices")}>Manual notices</Button>
          </div>
        </Panel>
      </div>
    </div>
  );
}
