import { createFileRoute, Link } from "@tanstack/react-router";
import { Button } from "@/components/ui/button";
import { PageHeader, Panel, StatusBadge } from "@/components/gst/common";
import { latestRun, useApp, useClients } from "@/lib/store";

export const Route = createFileRoute("/workspace/")({
  head: () => ({ meta: [{ title: "Client workspace — Complete GST Suite" }] }),
  component: WorkspacePicker,
});

function WorkspacePicker() {
  const clients = useClients();
  const runs = useApp((s) => s.runs);
  return (
    <div>
      <PageHeader title="Client workspace" subtitle="Choose a client to open its reconciliation, drafts, files and notices. You can also use the client switcher at the top." />
      {clients.length === 0 ? (
        <Panel><p className="text-sm text-muted-foreground">No clients yet.</p><Button asChild className="mt-3"><Link to="/">Load the demo firm</Link></Button></Panel>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {clients.map((c) => {
            const r = latestRun(runs, c.id);
            return (
              <Link key={c.id} to="/workspace/$clientId" params={{ clientId: c.id }} search={{ tab: "overview" }} className="rounded-lg border bg-card p-4 shadow-soft hover:border-primary/40">
                <div className="font-medium">{c.name}</div>
                <div className="font-mono text-xs text-muted-foreground">{c.gstin}</div>
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <StatusBadge status={!c.active ? "neutral" : r ? r.status : "neutral"} label={!c.active ? "Inactive" : r ? r.status : "Not run"} />
                  <span className="text-muted-foreground">{c.dataSource} · {c.staff || "unassigned"}</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
