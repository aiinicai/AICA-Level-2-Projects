import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo } from "react";
import { toast } from "sonner";
import { ArrowLeft, FileDown, FileText } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Dashboard } from "@/components/workspace/Dashboard";
import { ImportPanel } from "@/components/workspace/ImportPanel";
import { ReconTable } from "@/components/workspace/ReconTable";
import { ReviewPage } from "@/components/workspace/ReviewPage";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { DEFAULT_SETTINGS } from "@/lib/db";
import { exportExcel, exportPdf } from "@/lib/exporters";
import { reconcile } from "@/lib/recon";
import { useAudit, useClient, useReconItems, useSettings, useTxns } from "@/lib/useData";
import { DEMO_LABEL, isDemoClient } from "@/lib/demoData";

export const Route = createFileRoute("/clients/$id")({
  head: () => ({
    meta: [
      { title: "Client Reconciliation Workspace — GST Annual Return" },
      { name: "description", content: "Import Tally and GST return data, review mismatches and finalise GSTR-9 / GSTR-9C figures." },
      { property: "og:title", content: "Client Reconciliation Workspace" },
      { property: "og:description", content: "Import Tally and GST return data, review mismatches and finalise annual return figures." },
    ],
  }),
  component: ClientWorkspace,
});

function ClientWorkspace() {
  const { id } = Route.useParams();
  const client = useClient(id);
  const txns = useTxns(id);
  const items = useReconItems(id);
  const settings = useSettings();
  const audit = useAudit(id);

  const s = settings.data ?? DEFAULT_SETTINGS;
  const res = useMemo(() => reconcile(txns.data ?? [], s), [txns.data, s]);
  const saved = items.data ?? [];

  if (!client.data) {
    return (
      <AppShell>
        <p className="text-sm text-muted-foreground">Loading client…</p>
      </AppShell>
    );
  }
  const c = client.data;

  return (
    <AppShell>
      {isDemoClient(c.name) && (
        <div className="mb-4 rounded border border-amber-500/50 bg-amber-500/10 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-amber-700">
          {DEMO_LABEL}
        </div>
      )}
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <Link to="/"><Button variant="ghost" size="sm"><ArrowLeft className="mr-1 h-4 w-4" /> Clients</Button></Link>
        <div>
          <h1 className="text-lg font-semibold">{c.name}</h1>
          <p className="text-xs text-muted-foreground">
            {c.gstin} · FY {c.fy} · {c.state} · {c.reg_type}
          </p>
        </div>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={() => { exportExcel(c, res, saved, s.firmName); toast.success("Excel workbook exported."); }}>
            <FileDown className="mr-2 h-4 w-4" /> Export Excel
          </Button>
          <Button onClick={() => { exportPdf(c, res, saved, s.firmName); toast.success("PDF summary generated."); }}>
            <FileText className="mr-2 h-4 w-4" /> Client PDF summary
          </Button>
        </div>
      </div>

      <Tabs defaultValue="dashboard">
        <TabsList>
          <TabsTrigger value="dashboard">Dashboard &amp; summaries</TabsTrigger>
          <TabsTrigger value="imports">Imports &amp; column mapping</TabsTrigger>
          <TabsTrigger value="recon">Transaction reconciliation</TabsTrigger>
          <TabsTrigger value="review">Final review</TabsTrigger>
          <TabsTrigger value="audit">Audit trail</TabsTrigger>
        </TabsList>

        <TabsContent value="dashboard" className="mt-5"><Dashboard res={res} /></TabsContent>
        <TabsContent value="imports" className="mt-5"><ImportPanel clientId={id} /></TabsContent>
        <TabsContent value="recon" className="mt-5"><ReconTable clientId={id} res={res} saved={saved} /></TabsContent>
        <TabsContent value="review" className="mt-5"><ReviewPage clientId={id} res={res} saved={saved} /></TabsContent>
        <TabsContent value="audit" className="mt-5">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow><TableHead>Date &amp; time</TableHead><TableHead>Action</TableHead><TableHead>Details</TableHead></TableRow>
                </TableHeader>
                <TableBody>
                  {(audit.data ?? []).map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="whitespace-nowrap text-muted-foreground">{new Date(a.ts).toLocaleString("en-IN")}</TableCell>
                      <TableCell className="font-medium">{a.action}</TableCell>
                      <TableCell className="text-muted-foreground">{a.detail}</TableCell>
                    </TableRow>
                  ))}
                  {(audit.data ?? []).length === 0 && (
                    <TableRow><TableCell colSpan={3} className="py-10 text-center text-sm text-muted-foreground">No activity recorded yet.</TableCell></TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </AppShell>
  );
}
