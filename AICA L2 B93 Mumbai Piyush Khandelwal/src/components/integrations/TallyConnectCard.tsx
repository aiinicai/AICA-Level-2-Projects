import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Check, Copy, Download, Loader2, RefreshCw, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { StatusPill } from "@/components/widgets/DataTable";
import { EmptyState } from "@/components/common/states";
import { relativeTime } from "@/lib/format";
import { useAuth } from "@/lib/auth";
import { useLiveData } from "@/lib/live-data";
import { createSource, deleteSource } from "@/lib/accounting.functions";
import { toast } from "sonner";

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <div className="space-y-1.5">
      <Label>{label}</Label>
      <div className="flex gap-2">
        <Input readOnly value={value} className="font-mono text-xs" onFocus={(e) => e.currentTarget.select()} />
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label={`Copy ${label}`}
          onClick={async () => {
            await navigator.clipboard.writeText(value);
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          }}
        >
          {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
        </Button>
      </div>
    </div>
  );
}

export function TallyConnectCard() {
  const { user, loading } = useAuth();
  const { sources: allSources, loading: syncing, refresh } = useLiveData();
  const sources = allSources.filter((s) => s.provider !== "excel");
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("TallyPrime — Head office");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [issued, setIssued] = useState<string | null>(null);

  const ingestUrl = typeof window === "undefined" ? "" : `${window.location.origin}/api/public/tally/ingest`;
  const bridgeUrl = typeof window === "undefined" ? "" : `${window.location.origin}/api/public/tally/bridge`;

  if (loading) return null;

  if (!user) {
    return (
      <EmptyState
        icon={RefreshCw}
        title="Sign in to connect your own books"
        description="Your Tally figures are stored against your account, so you need to sign in before connecting. The demo figures below stay available either way."
        action={
          <Button asChild>
            <Link to="/login">Sign in</Link>
          </Button>
        }
      />
    );
  }

  return (
    <section className="panel p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold">Your books</h2>
          <p className="text-xs text-muted-foreground">
            Live figures pushed in from TallyPrime running on your own machine.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => void refresh()} disabled={syncing}>
            {syncing ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <RefreshCw className="size-4" aria-hidden />}
            Refresh
          </Button>
          <Dialog
            open={open}
            onOpenChange={(v) => {
              setOpen(v);
              if (!v) setIssued(null);
            }}
          >
            <DialogTrigger asChild>
              <Button size="sm">Connect Tally</Button>
            </DialogTrigger>
            <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>Connect TallyPrime</DialogTitle>
                <DialogDescription>
                  Tally runs on your own computer, so a small helper reads it there and sends the figures here. Nothing
                  else can reach your machine.
                </DialogDescription>
              </DialogHeader>

              {issued ? (
                <div className="space-y-4 text-sm">
                  <ol className="list-decimal space-y-2 pl-5 text-muted-foreground">
                    <li>In TallyPrime press F1 → Settings → Connectivity and set it to act as <strong>Both</strong>.</li>
                    <li>Download the helper below onto that same computer.</li>
                    <li>
                      Open a command window there and run it with the token and address below, e.g.
                      <code className="mt-1 block rounded bg-muted px-2 py-1 font-mono text-xs break-all">
                        DASH_TOKEN=… DASH_URL={ingestUrl} node dash-tally-bridge.mjs
                      </code>
                    </li>
                  </ol>
                  <CopyField label="Sync token (shown only once)" value={issued} />
                  <CopyField label="Address to send data to" value={ingestUrl} />
                  <Button asChild variant="outline" className="w-full">
                    <a href={bridgeUrl} download="dash-tally-bridge.mjs">
                      <Download className="size-4" aria-hidden /> Download the helper
                    </a>
                  </Button>
                  <DialogFooter>
                    <Button
                      onClick={() => {
                        setOpen(false);
                        setIssued(null);
                        void refresh();
                      }}
                    >
                      Done
                    </Button>
                  </DialogFooter>
                </div>
              ) : (
                <form
                  className="space-y-3"
                  onSubmit={async (e) => {
                    e.preventDefault();
                    setBusy(true);
                    try {
                      const res = await createSource({ data: { provider: "tally", name, company: company || undefined } });
                      setIssued(res.token);
                      await refresh();
                    } catch (err) {
                      toast.error(err instanceof Error ? err.message : "Could not create the connection");
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <div className="space-y-1.5">
                    <Label htmlFor="src-name">Name this connection</Label>
                    <Input id="src-name" required value={name} onChange={(e) => setName(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="src-company">Company in Tally (optional)</Label>
                    <Input
                      id="src-company"
                      value={company}
                      onChange={(e) => setCompany(e.target.value)}
                      placeholder="Acme Industries Pvt Ltd"
                    />
                  </div>
                  <DialogFooter>
                    <Button type="submit" disabled={busy}>
                      {busy ? "Creating…" : "Create connection"}
                    </Button>
                  </DialogFooter>
                </form>
              )}
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {sources.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">
          No books connected yet. Connect TallyPrime and your dashboards switch from the sample figures to your own.
        </p>
      ) : (
        <ul className="mt-4 space-y-2">
          {sources.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-border p-3">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-semibold">{s.name}</span>
                  <StatusPill value={s.status === "connected" ? "Healthy" : "Pending"} />
                </div>
                <p className="mt-1 text-xs text-muted-foreground">
                  {s.company ? `${s.company} · ` : ""}
                  {s.records.toLocaleString("en-IN")} records ·{" "}
                  {s.lastSync ? `last updated ${relativeTime(s.lastSync)}` : "waiting for the first sync"}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${s.name}`}
                onClick={async () => {
                  await deleteSource({ data: { id: s.id } });
                  await refresh();
                  toast.success(`${s.name} removed`);
                }}
              >
                <Trash2 className="size-4" aria-hidden />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
