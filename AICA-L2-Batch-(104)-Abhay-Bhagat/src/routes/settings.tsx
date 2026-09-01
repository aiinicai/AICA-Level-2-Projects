import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Save } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DEFAULT_SETTINGS, saveSettings, type AppSettings } from "@/lib/db";
import { useRefresh, useSettings } from "@/lib/useData";

export const Route = createFileRoute("/settings")({
  head: () => ({
    meta: [
      { title: "Reconciliation Settings — GST Annual Return" },
      { name: "description", content: "Set firm name, matching tolerances and applicable GST rates used across all client reconciliations." },
      { property: "og:title", content: "Reconciliation Settings" },
      { property: "og:description", content: "Firm name, matching tolerances and GST rates for annual return reconciliation." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: SettingsPage,
});

function SettingsPage() {
  const settings = useSettings();
  const refresh = useRefresh();
  const [form, setForm] = useState<AppSettings>(DEFAULT_SETTINGS);

  useEffect(() => {
    if (settings.data) setForm(settings.data);
  }, [settings.data]);

  async function save() {
    await saveSettings(form);
    refresh(["settings", "recon"]);
    toast.success("Settings saved.");
  }

  return (
    <AppShell>
      <div className="max-w-2xl space-y-6">
        <Card>
          <CardHeader><CardTitle className="text-base">Firm details</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Firm name (used on exported reports)</Label>
              <Input value={form.firmName} onChange={(e) => setForm({ ...form, firmName: e.target.value })} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Matching tolerances</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <Label>Taxable value tolerance (₹)</Label>
              <Input
                type="number"
                value={form.valueTolerance}
                onChange={(e) => setForm({ ...form, valueTolerance: Number(e.target.value) || 0 })}
              />
            </div>
            <div className="space-y-1">
              <Label>Tax amount tolerance (₹)</Label>
              <Input
                type="number"
                value={form.taxTolerance}
                onChange={(e) => setForm({ ...form, taxTolerance: Number(e.target.value) || 0 })}
              />
            </div>
            <p className="text-xs text-muted-foreground sm:col-span-2">
              Differences within these limits are treated as matched rather than mismatches.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">Applicable GST rates</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label>Rates (%) separated by commas</Label>
              <Input
                value={form.taxRates.join(", ")}
                onChange={(e) =>
                  setForm({
                    ...form,
                    taxRates: e.target.value
                      .split(",")
                      .map((v) => Number(v.trim()))
                      .filter((v) => !isNaN(v)),
                  })
                }
              />
            </div>
          </CardContent>
        </Card>

        <Button onClick={save}><Save className="mr-2 h-4 w-4" /> Save settings</Button>
      </div>
    </AppShell>
  );
}
