import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { Check, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PageHeader, Panel, StatusBadge, Term } from "@/components/gst/common";
import { FirmForm } from "@/components/gst/FirmForm";
import { CLIENTS } from "@/lib/gst/demo";
import { validateGstin } from "@/lib/gst/gstin";
import { DEMO_FIRM, getState, loadDemoFirm, log, runAll, setState, useApp, type Firm } from "@/lib/store";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/setup")({
  head: () => ({
    meta: [
      { title: "Guided setup — Complete GST Suite" },
      { name: "description", content: "Set up your firm, choose preferences, load the demo firm and run your first reconciliation in four steps." },
      { property: "og:title", content: "Guided setup — Complete GST Suite" },
      { property: "og:description", content: "Get started in four short steps." },
    ],
  }),
  component: SetupPage,
});

const STEPS = ["Firm", "Preferences", "Load demo firm", "Finish & run all clients"];

function SetupPage() {
  const navigate = useNavigate();
  const existing = useApp((s) => s.firm);
  const demo = useApp((s) => s.demoLoaded);
  const progress = useApp((s) => s.progress);
  const prefs = useApp((s) => s.prefs);
  const [step, setStep] = useState(0);
  const [firm, setFirm] = useState<Firm>(existing ?? DEMO_FIRM);
  const [busy, setBusy] = useState(false);

  const firmOk = firm.name.trim() && firm.partner.trim() && (!firm.gstin || validateGstin(firm.gstin).valid);

  const next = () => {
    if (step === 0) {
      setState({ firm });
      log("Saved firm details in guided setup");
    }
    setStep(step + 1);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Guided setup" subtitle="Four short steps — about a minute." />
      <ol className="mb-6 grid grid-cols-4 gap-2">
        {STEPS.map((s, i) => (
          <li key={s} className="flex flex-col gap-2">
            <div className={cn("h-1.5 rounded-full", i <= step ? "bg-primary" : "bg-muted")} />
            <div className="flex items-center gap-2 text-xs">
              <span className={cn("flex h-5 w-5 items-center justify-center rounded-full border text-[11px]", i < step ? "border-primary bg-primary text-primary-foreground" : i === step ? "border-primary text-primary" : "text-muted-foreground")}>
                {i < step ? <Check className="h-3 w-3" /> : i + 1}
              </span>
              <span className={i === step ? "font-medium text-foreground" : "text-muted-foreground"}>{s}</span>
            </div>
          </li>
        ))}
      </ol>

      <Panel title={`Step ${step + 1} of 4 · ${STEPS[step]}`}>
        {step === 0 && (
          <>
            <p className="mb-4 text-sm text-muted-foreground">Tell us about your firm. This appears on reports and in the activity log.</p>
            <FirmForm value={firm} onChange={setFirm} />
          </>
        )}
        {step === 1 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">These defaults suit most firms. You can change them later in Settings.</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="tol"><Term k="Tolerance">Rounding tolerance (₹)</Term></Label>
                <Input id="tol" type="number" min={0} value={prefs.tolerance} onChange={(e) => setState((s) => ({ prefs: { ...s.prefs, tolerance: Math.max(0, Number(e.target.value) || 0) } }))} />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="rem">Notice reminder (days before due date)</Label>
                <Input id="rem" type="number" min={1} value={prefs.reminderDays} onChange={(e) => setState((s) => ({ prefs: { ...s.prefs, reminderDays: Math.max(1, Number(e.target.value) || 7) } }))} />
              </div>
              <div className="space-y-1.5">
                <Label>Financial year</Label>
                <Input value="FY 2025-26" disabled />
              </div>
            </div>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">The demo firm has 4 clients with a full year of books and returns, and 6 GST notices — including a few deliberate differences so you can see how they are found.</p>
            <ul className="space-y-2 text-sm">
              {CLIENTS.map((c) => (
                <li key={c.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                  <span>{c.name}</span>
                  <span className="text-xs text-muted-foreground">{c.note}</span>
                </li>
              ))}
            </ul>
            {demo ? <StatusBadge status="Matched" label="Demo firm loaded" /> : <Button onClick={() => { loadDemoFirm(); toast.success("Demo firm loaded"); }}>Load demo firm</Button>}
          </div>
        )}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">We'll reconcile every client now. If one client has a problem, the others still run.</p>
            <ul className="space-y-2 text-sm">
              {CLIENTS.map((c) => {
                const p = progress[c.id];
                return (
                  <li key={c.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                    <span>{c.name}</span>
                    {p ? <StatusBadge status={p} label={{ queued: "Queued", running: "Checking…", done: "Done", failed: "Failed" }[p]} /> : <span className="text-xs text-muted-foreground">Waiting</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <div className="mt-6 flex justify-between border-t pt-4">
          <Button variant="ghost" disabled={step === 0 || busy} onClick={() => setStep(step - 1)}>Back</Button>
          {step < 3 ? (
            <Button disabled={(step === 0 && !firmOk) || (step === 2 && !demo)} onClick={next}>Continue</Button>
          ) : (
            <Button
              disabled={busy}
              onClick={async () => {
                setBusy(true);
                if (!getState().demoLoaded) loadDemoFirm();
                await runAll();
                setBusy(false);
                toast.success("All clients reconciled — here's your dashboard");
                navigate({ to: "/" });
              }}
            >
              {busy && <Loader2 className="mr-2 h-4 w-4 animate-spin" />} Finish & run all clients
            </Button>
          )}
        </div>
      </Panel>
    </div>
  );
}
