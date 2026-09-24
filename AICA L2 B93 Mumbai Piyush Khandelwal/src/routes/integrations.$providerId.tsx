import { useState } from "react";
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { Check, ChevronRight, Loader2, Plug, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { EmptyState, ErrorState, PageHeader } from "@/components/common/states";
import { integrationById } from "@/lib/integrations/catalog";
import { getAdapter } from "@/lib/integrations/adapter";
import { useWorkspace } from "@/lib/store";
import { uid } from "@/lib/data/seed";
import { cn } from "@/lib/utils";
import type { Connection } from "@/lib/types";
import { toast } from "sonner";

export const Route = createFileRoute("/integrations/$providerId")({
  head: () => ({
    meta: [
      { title: "Connect a data source — The DASH" },
      { name: "description", content: "Authenticate, test the connection, pick datasets and choose a sync schedule." },
      { property: "og:title", content: "Connect a data source — The DASH" },
      { property: "og:description", content: "A guided five-step flow for connecting any business system." },
    ],
  }),
  component: ConnectPage,
});

const STEPS = ["Authenticate", "Test connection", "Select datasets", "Sync settings", "Finish"];
const FREQUENCIES: Connection["frequency"][] = ["manual", "hourly", "6h", "daily"];
const FREQUENCY_LABEL: Record<string, string> = {
  manual: "Manual only",
  hourly: "Every hour",
  "6h": "Every 6 hours",
  daily: "Once a day",
};

function ConnectPage() {
  const { providerId } = Route.useParams();
  const provider = integrationById(providerId);
  const navigate = useNavigate();
  const { addConnection, notify } = useWorkspace();

  const [step, setStep] = useState(0);
  const [creds, setCreds] = useState<Record<string, string>>({});
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null);
  const [selected, setSelected] = useState<string[]>(
    (provider?.datasets ?? []).filter((d) => d.default !== false).map((d) => d.id),
  );
  const [frequency, setFrequency] = useState<Connection["frequency"]>("6h");
  const [syncing, setSyncing] = useState(false);
  const [records, setRecords] = useState(0);

  if (!provider) {
    return (
      <div className="p-6">
        <EmptyState
          icon={Plug}
          title="Integration not found"
          description="This connector isn't in the marketplace."
          action={
            <Button asChild>
              <Link to="/integrations">Back to marketplace</Link>
            </Button>
          }
        />
      </div>
    );
  }

  const adapter = getAdapter(provider.id, selected);
  const missing = provider.credentials.filter((c) => !c.optional && !creds[c.key]?.trim());

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      await adapter.connect(creds);
      const res = await adapter.testConnection();
      setTestResult(res);
      if (res.ok) setStep(2);
    } catch (e) {
      setTestResult({ ok: false, message: e instanceof Error ? e.message : "Connection failed" });
    } finally {
      setTesting(false);
    }
  };

  const finish = async () => {
    setSyncing(true);
    try {
      const res = await adapter.sync();
      setRecords(res.records);
      const connection: Connection = {
        id: uid(),
        providerId: provider.id,
        name: provider.name,
        status: "connected",
        datasets: selected,
        frequency,
        lastSync: new Date().toISOString(),
        records: res.records,
      };
      addConnection(connection);
      notify({
        title: `${provider.name} connected`,
        body: `${res.records.toLocaleString("en-IN")} demo records synced across ${selected.length} datasets.`,
        category: "sync",
        level: "success",
      });
      setStep(4);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="pb-10">
      <PageHeader
        breadcrumb={
          <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-xs text-muted-foreground">
            <Link to="/integrations" className="hover:text-foreground">
              Integrations
            </Link>
            <ChevronRight className="size-3" aria-hidden />
            <span className="text-foreground">{provider.name}</span>
          </nav>
        }
        title={provider.name}
        description={provider.description}
      />

      <div className="mx-auto max-w-3xl space-y-5 px-4 py-6 sm:px-6 lg:px-8">
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs" aria-label="Connection steps">
          {STEPS.map((s, i) => (
            <li key={s} className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-5 items-center justify-center rounded-full border text-[10px] font-semibold",
                  i < step && "border-positive bg-positive-soft text-positive",
                  i === step && "border-primary bg-primary text-primary-foreground",
                  i > step && "text-muted-foreground",
                )}
              >
                {i < step ? <Check className="size-3" aria-hidden /> : i + 1}
              </span>
              <span className={cn(i === step ? "font-medium text-foreground" : "text-muted-foreground")}>{s}</span>
              {i < STEPS.length - 1 && <ChevronRight className="size-3 text-muted-foreground" aria-hidden />}
            </li>
          ))}
        </ol>

        <div className="panel space-y-4 p-5">
          {step === 0 && (
            <>
              <h2 className="text-sm font-semibold">Authenticate with {provider.name}</h2>
              <p className="flex items-start gap-2 rounded-lg bg-surface-muted p-3 text-xs text-muted-foreground">
                <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                Credentials are only ever stored server-side. This workspace is running in demo mode, so nothing is sent
                to {provider.name} and no live records are fetched.
              </p>
              {provider.credentials.map((c) => (
                <div key={c.key} className="space-y-1.5">
                  <Label htmlFor={c.key}>
                    {c.label}
                    {!c.optional && <span className="text-destructive"> *</span>}
                  </Label>
                  <Input
                    id={c.key}
                    type={c.secret ? "password" : "text"}
                    placeholder={c.placeholder}
                    value={creds[c.key] ?? ""}
                    onChange={(e) => setCreds((v) => ({ ...v, [c.key]: e.target.value }))}
                  />
                  {c.help && <p className="text-xs text-muted-foreground">{c.help}</p>}
                </div>
              ))}
              <div className="flex justify-end gap-2">
                <Button variant="ghost" asChild>
                  <Link to="/integrations">Cancel</Link>
                </Button>
                <Button
                  onClick={() => {
                    setStep(1);
                    void runTest();
                  }}
                  disabled={missing.length > 0}
                >
                  Continue
                </Button>
              </div>
              {missing.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  Fill in: {missing.map((m) => m.label).join(", ")}
                </p>
              )}
            </>
          )}

          {step === 1 && (
            <>
              <h2 className="text-sm font-semibold">Testing the connection</h2>
              {testing && (
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" aria-hidden /> Contacting {provider.name}…
                </p>
              )}
              {testResult && !testResult.ok && (
                <ErrorState
                  title="Connection test failed"
                  description={testResult.message}
                  onRetry={runTest}
                  secondary={
                    <Button size="sm" variant="outline" onClick={() => setStep(0)}>
                      Edit credentials
                    </Button>
                  }
                />
              )}
              {testResult?.ok && <p className="text-sm text-positive">{testResult.message}</p>}
            </>
          )}

          {step === 2 && (
            <>
              <h2 className="text-sm font-semibold">Select the datasets to sync</h2>
              <ul className="space-y-2">
                {provider.datasets.map((d) => (
                  <li key={d.id} className="flex items-center gap-3 rounded-lg border bg-surface p-3">
                    <Checkbox
                      id={`ds-${d.id}`}
                      checked={selected.includes(d.id)}
                      onCheckedChange={(v) =>
                        setSelected((s) => (v ? [...new Set([...s, d.id])] : s.filter((x) => x !== d.id)))
                      }
                    />
                    <Label htmlFor={`ds-${d.id}`} className="flex-1 cursor-pointer text-sm font-normal">
                      {d.label}
                    </Label>
                  </li>
                ))}
              </ul>
              <div className="flex justify-between gap-2">
                <Button variant="ghost" onClick={() => setStep(0)}>Back</Button>
                <Button onClick={() => setStep(3)} disabled={selected.length === 0}>
                  Continue
                </Button>
              </div>
            </>
          )}

          {step === 3 && (
            <>
              <h2 className="text-sm font-semibold">Sync settings</h2>
              <div className="space-y-1.5">
                <Label>Sync frequency</Label>
                <Select value={frequency} onValueChange={(v) => setFrequency(v as Connection["frequency"])}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {FREQUENCIES.map((f) => (
                      <SelectItem key={f} value={f}>{FREQUENCY_LABEL[f]}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  You can run a manual sync at any time from the data sources screen.
                </p>
              </div>
              <div className="flex justify-between gap-2">
                <Button variant="ghost" onClick={() => setStep(2)}>Back</Button>
                <Button onClick={finish} disabled={syncing}>
                  {syncing && <Loader2 className="size-4 animate-spin" aria-hidden />}
                  {syncing ? "Syncing…" : "Connect and sync"}
                </Button>
              </div>
            </>
          )}

          {step === 4 && (
            <div className="space-y-3 text-center">
              <span className="mx-auto flex size-11 items-center justify-center rounded-full bg-positive-soft text-positive">
                <Check className="size-5" aria-hidden />
              </span>
              <h2 className="text-base font-semibold">{provider.name} is connected</h2>
              <p className="text-sm text-muted-foreground">
                {records.toLocaleString("en-IN")} demo records synced across {selected.length} datasets. Data in this
                workspace is clearly labelled as demo data.
              </p>
              <div className="flex flex-wrap justify-center gap-2 pt-2">
                <Button onClick={() => navigate({ to: "/data-sources" })}>View sync status</Button>
                <Button variant="outline" onClick={() => navigate({ to: "/explorer" })}>
                  Explore the data
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
