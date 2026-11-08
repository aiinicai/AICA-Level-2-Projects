import { createFileRoute, Link } from "@tanstack/react-router";
import { PageHeader, Panel } from "@/components/gst/common";
import { DataTable } from "@/components/gst/DataTable";
import { fmtDateTime } from "@/lib/gst/format";
import { useApp, useClients, useCurrentUser } from "@/lib/store";

export const Route = createFileRoute("/activity")({
  head: () => ({
    meta: [
      { title: "Activity log — Complete GST Suite" },
      { name: "description", content: "Audit log: who connected, fetched, uploaded, ran, exported or changed a notice, and when." },
      { property: "og:title", content: "Activity log — Complete GST Suite" },
      { property: "og:description", content: "A complete record of work done across your firm." },
    ],
  }),
  component: ActivityPage,
});

function ActivityPage() {
  const items = useApp((s) => s.activity);
  const clients = useClients();
  const ids = new Set(clients.map((c) => c.id));
  const partner = useCurrentUser().role === "Partner";
  const shown = items.filter((a) => (a.clientId ? ids.has(a.clientId) : partner));
  const name = (id?: string) => clients.find((c) => c.id === id)?.name ?? "Firm";
  return (
    <div>
      <PageHeader title="Activity log" subtitle="Who connected, fetched, uploaded, ran, exported or changed a notice — and when." />
      <Panel>
        <DataTable
          rows={shown}
          rowKey={(a) => a.id}
          exportName="activity_log"
          empty={{ message: "Nothing recorded yet." }}
          columns={[
            { key: "at", title: "When", header: "When", value: (a) => a.at, cell: (a) => <span className="whitespace-nowrap text-muted-foreground">{fmtDateTime(a.at)}</span> },
            { key: "client", title: "Client", header: "Client", value: (a) => name(a.clientId), filter: true, cell: (a) => (a.clientId && ids.has(a.clientId) ? <Link to="/workspace/$clientId" params={{ clientId: a.clientId }} search={{ tab: "activity" }} className="text-primary hover:underline">{name(a.clientId)}</Link> : "Firm") },
            { key: "action", title: "What happened", header: "What happened", value: (a) => a.action },
            { key: "by", title: "By", header: "By", value: (a) => a.by, filter: true },
          ]}
        />
      </Panel>
    </div>
  );
}
