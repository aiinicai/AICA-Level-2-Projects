import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { Loader2, Plug, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DemoBadge, EmptyState, ErrorState, PageHeader } from "@/components/common/states";
import { StatusPill } from "@/components/widgets/DataTable";
import { useWorkspace } from "@/lib/store";
import { integrationById } from "@/lib/integrations/catalog";
import { getAdapter } from "@/lib/integrations/adapter";
import { prettyDate, relativeTime } from "@/lib/format";
import { TallyConnectCard } from "@/components/integrations/TallyConnectCard";
import { ExcelImportCard } from "@/components/integrations/ExcelImportCard";
import { useLiveData } from "@/lib/live-data";
import type { Connection } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/data-sources")({
  head: () => ({
    meta: [
      { title: "Data sources & sync status — The DASH" },
      {
        name: "description",
        content: "Monitor every connected system: sync status, last and next sync, record counts and sync errors.",
      },
      { property: "og:title", content: "Data sources — The DASH" },
      { property: "og:description", content: "Sync status, record counts and errors for every connected system." },
    ],
  }),
  component: DataSourcesPage,
});

const FREQUENCY_LABEL: Record<Connection["frequency"], string> = {
  manual: "Manual only",
  hourly: "Every hour",
  "6h": "Every 6 hours",
  daily: "Once a day",
};

function DataSourcesPage() {
  const { connections, updateConnection, removeConnection, notify, hydrated } = useWorkspace();
  const [busy, setBusy] = useState<string | null>(null);
  const { live } = useLiveData();

  const sync = async (c: Connection) => {
    setBusy(c.id);
    try {
      const adapter = getAdapter(c.providerId, c.datasets);
      const res = await adapter.sync();
      updateConnection(c.id, {
        status: "connected",
        lastSync: res.at,
        records: res.records,
        error: undefined,
      });
      notify({
        title: `${c.name} synced`,
        body: `${res.records.toLocaleString("en-IN")} records refreshed.`,
        category: "sync",
        level: "success",
      });
      toast.success(`${c.name} synced`);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Sync failed";
      updateConnection(c.id, { status: "error", error: message });
      toast.error(message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="pb-10">
      <PageHeader
        title="Data sources"
        description="Everything feeding your dashboards, and whether it's healthy."
        actions={
          <>
            <DemoBadge className="mr-1" />
            <Button asChild>
              <Link to="/integrations">
                <Plug className="size-4" aria-hidden /> Connect a source
              </Link>
            </Button>
          </>
        }
      />

      <div className="space-y-4 px-4 py-6 sm:px-6 lg:px-8">
        <TallyConnectCard />
        <ExcelImportCard />

        <div className="flex items-center gap-2 pt-2">
          <h2 className="text-sm font-semibold">Sample sources</h2>
          <DemoBadge />
          {live && <span className="text-xs text-muted-foreground">Dashboards are showing your own figures.</span>}
        </div>

        {connections.length === 0 ? (
          <EmptyState
            icon={Plug}
            title="No sources connected"
            description="Connect Tally, Zoho, QuickBooks, Razorpay or any REST API to start building dashboards on your own data."
            action={
              <Button asChild>
                <Link to="/integrations">Browse integrations</Link>
              </Button>
            }
          />
        ) : (
          <ul className="space-y-3">
            {connections.map((c) => {
              const def = integrationById(c.providerId);
              return (
                <li key={c.id} className="panel p-4">
                  <div className="flex flex-wrap items-start gap-3">
                    <span
                      className="flex size-10 shrink-0 items-center justify-center rounded-lg text-sm font-semibold text-white"
                      style={{ backgroundColor: def?.accent ?? "#334155" }}
                      aria-hidden
                    >
                      {def?.initials ?? c.name.slice(0, 2).toUpperCase()}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="truncate text-sm font-semibold">{c.name}</h2>
                        <StatusPill value={c.status === "connected" ? "Healthy" : c.status === "error" ? "Failed" : "Pending"} />
                      </div>
                      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-4">
                        <div>
                          <dt>Last sync</dt>
                          <dd className="num text-foreground">{hydrated ? (c.lastSync ? relativeTime(c.lastSync) : "Never") : "—"}</dd>
                        </div>
                        <div>
                          <dt>Next sync</dt>
                          <dd className="num text-foreground">
                            {c.frequency === "manual" ? "Manual" : c.nextSync ? prettyDate(c.nextSync) : FREQUENCY_LABEL[c.frequency]}
                          </dd>
                        </div>
                        <div>
                          <dt>Records</dt>
                          <dd className="num text-foreground">{c.records.toLocaleString("en-IN")}</dd>
                        </div>
                        <div>
                          <dt>Datasets</dt>
                          <dd className="num text-foreground">{c.datasets.length}</dd>
                        </div>
                      </dl>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Select
                        value={c.frequency}
                        onValueChange={(v) => updateConnection(c.id, { frequency: v as Connection["frequency"] })}
                      >
                        <SelectTrigger className="h-9 w-[150px]" aria-label={`${c.name} sync frequency`}>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {(Object.keys(FREQUENCY_LABEL) as Connection["frequency"][]).map((f) => (
                            <SelectItem key={f} value={f}>{FREQUENCY_LABEL[f]}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Button variant="outline" size="sm" onClick={() => sync(c)} disabled={busy === c.id}>
                        {busy === c.id ? (
                          <Loader2 className="size-4 animate-spin" aria-hidden />
                        ) : (
                          <RefreshCw className="size-4" aria-hidden />
                        )}
                        Sync now
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Disconnect ${c.name}`}
                        onClick={() => {
                          removeConnection(c.id);
                          toast.success(`${c.name} disconnected`);
                        }}
                      >
                        <Trash2 className="size-4" aria-hidden />
                      </Button>
                    </div>
                  </div>

                  {c.status === "error" && (
                    <div className="mt-3">
                      <ErrorState
                        title="Last sync failed"
                        description={c.error ?? "The provider rejected the credentials."}
                        onRetry={() => sync(c)}
                        secondary={
                          <Button size="sm" variant="outline" asChild>
                            <Link to="/integrations/$providerId" params={{ providerId: c.providerId }}>
                              Reconnect
                            </Link>
                          </Button>
                        }
                      />
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
